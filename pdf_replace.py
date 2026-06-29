"""
PDF Batch Text Replacer — pypdfium2 + Pillow
Render-based approach: giữ visual gốc, overlay text mới lên ảnh render.
Output là PDF ảnh (không có selectable text).

Usage:
    python pdf_replace.py --input ./pdfs --old "MEGA DIGITAL LLC" --new "Acme Corp"
    python pdf_replace.py --input ./pdfs --config replacements.json --output ./output
    python pdf_replace.py --input ./pdfs --old "Old Name" --new "New Name" --dry-run --verbose
"""

import argparse
import json
import shutil
import sys
from pathlib import Path
from datetime import datetime

try:
    import pypdfium2 as pdfium
except ImportError:
    print("[ERROR] Thiếu pypdfium2. Chạy: pip install pypdfium2")
    sys.exit(1)

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("[ERROR] Thiếu Pillow. Chạy: pip install Pillow")
    sys.exit(1)


# ─── Config ───────────────────────────────────────────────────────────────────

RENDER_SCALE = 3          # 216 DPI — đủ sharp cho in ấn, không quá nặng
PDF_DPI      = 72         # PDF coordinate space
PADDING_X    = 2          # px padding ngang khi vẽ rect che
PADDING_Y    = 2          # px padding dọc

# Font tùy chỉnh — override bằng --font, --font-bold, --font-size-scale khi chạy
FONT_NAME         = "arial"   # arial | carlito | lato
FONT_BOLD         = False     # True = dùng Bold variant
FONT_SIZE_SCALE   = 1.0       # nhân thêm vào font size đọc từ PDF (1.0 = giữ nguyên)


# ─── Core ─────────────────────────────────────────────────────────────────────

def _get_matches(textpage, search_text: str) -> list[dict]:
    """Tìm tất cả matches, trả về bounding box theo PDF coords, sắp xếp top→bottom."""
    searcher = textpage.search(search_text, match_case=True, match_whole_word=False)
    matches = []
    result = searcher.get_next()
    while result:
        char_idx, count = result
        rects = [textpage.get_charbox(i, loose=True) for i in range(char_idx, char_idx + count)]
        if rects:
            matches.append({
                "x0": min(r[0] for r in rects),
                "y0": min(r[1] for r in rects),
                "x1": max(r[2] for r in rects),
                "y1": max(r[3] for r in rects),
            })
        result = searcher.get_next()
    searcher.close()
    # Sắp xếp top→bottom (y1 lớn = cao hơn trong PDF coords = xuất hiện trước)
    matches.sort(key=lambda m: -m["y1"])
    return matches


def _build_match_plan(textpage, replacements: list[dict]) -> list[dict]:
    """
    Xây dựng danh sách (match_bbox, new_text) theo đúng thứ tự từ trên xuống.

    Hai mode:
    - replace_all (default): tất cả instances của old → new
    - sequential: mỗi record dùng cho instance tiếp theo theo thứ tự xuất hiện

    Sequential grouping: các records cùng old string được nhóm lại,
    dispatch lần lượt cho từng instance từ trên xuống.
    """
    # Tách replacements thành 2 nhóm
    replace_all = [r for r in replacements if r.get("mode", "replace_all") == "replace_all"]
    sequential  = [r for r in replacements if r.get("mode") == "sequential"]

    plan = []  # list of {x0,y0,x1,y1, old, new}

    # ── Replace All: mỗi old → tất cả instances ──
    seen_all = {}
    for rep in replace_all:
        old = rep["old"]
        if old in seen_all:
            continue  # đã xử lý
        seen_all[old] = True
        matches = _get_matches(textpage, old)
        for m in matches:
            plan.append({**m, "old": old, "new": rep["new"]})

    # ── Sequential: group theo old, dispatch theo thứ tự ──
    # Nhóm tất cả sequential records theo old string, giữ thứ tự
    seq_groups: dict[str, list[str]] = {}
    for rep in sequential:
        old = rep["old"]
        if old not in seq_groups:
            seq_groups[old] = []
        seq_groups[old].append(rep["new"])

    for old, new_list in seq_groups.items():
        matches = _get_matches(textpage, old)
        for i, m in enumerate(matches):
            if i < len(new_list):
                plan.append({**m, "old": old, "new": new_list[i]})
            # instances vượt quá số records → bỏ qua (không replace)

    # Sắp xếp toàn bộ plan theo thứ tự top→bottom để vẽ đúng thứ tự
    plan.sort(key=lambda m: -m["y1"])
    return plan


def _pdf_to_px(x, y, w_pt, h_pt, img_w, img_h):
    """Convert PDF coords (origin bottom-left) → pixel coords (origin top-left)."""
    px = x / w_pt * img_w
    py = (h_pt - y) / h_pt * img_h
    return px, py


def _sample_bg_color(img: Image.Image, px0, py0, px1, py1) -> tuple:
    """Sample màu nền: lấy pixel ngay trên vùng match."""
    sample_y = max(0, int(py0) - 3)
    sample_x = int((px0 + px1) / 2)
    sample_x = max(0, min(sample_x, img.width - 1))
    sample_y = max(0, min(sample_y, img.height - 1))
    color = img.getpixel((sample_x, sample_y))
    # Đảm bảo trả về RGB tuple
    if isinstance(color, int):
        return (color, color, color)
    return color[:3]


# Cache font objects để không load lại mỗi lần
_font_cache: dict = {}

# Thư mục fonts/ bundle cạnh script
_FONTS_DIR = Path(__file__).parent / "fonts"

# Map (font_name, bold) → danh sách path ưu tiên
# Bundle trước, hệ thống sau, fallback cuối
_FONT_PATHS: dict[tuple, list] = {
    ("arial",   False): [
        "C:/Windows/Fonts/arial.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ],
    ("arial",   True): [
        "C:/Windows/Fonts/arialbd.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ],
    ("carlito", False): [
        str(_FONTS_DIR / "Carlito-Regular.ttf"),
        "C:/Windows/Fonts/Carlito-Regular.ttf",
        "/usr/share/fonts/truetype/crosextra/Carlito-Regular.ttf",
        # fallback
        "C:/Windows/Fonts/arial.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ],
    ("carlito", True): [
        str(_FONTS_DIR / "Carlito-Bold.ttf"),
        "C:/Windows/Fonts/Carlito-Bold.ttf",
        "/usr/share/fonts/truetype/crosextra/Carlito-Bold.ttf",
        # fallback
        "C:/Windows/Fonts/arialbd.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    ],
    ("lato",    False): [
        str(_FONTS_DIR / "Lato-Regular.ttf"),
        "C:/Windows/Fonts/Lato-Regular.ttf",
        "/usr/share/fonts/truetype/lato/Lato-Regular.ttf",
        # fallback
        "/usr/share/fonts/truetype/crosextra/Carlito-Regular.ttf",
        "C:/Windows/Fonts/arial.ttf",
    ],
    ("lato",    True): [
        str(_FONTS_DIR / "Lato-Bold.ttf"),
        "C:/Windows/Fonts/Lato-Bold.ttf",
        "/usr/share/fonts/truetype/lato/Lato-Bold.ttf",
        # fallback
        "/usr/share/fonts/truetype/crosextra/Carlito-Bold.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
    ],
}


def resolve_font_path(font_name: str, bold: bool = False) -> str | None:
    """Trả về path font đầu tiên tìm thấy, hoặc None nếu không có."""
    key = (font_name.lower(), bold)
    candidates = _FONT_PATHS.get(key, _FONT_PATHS[("arial", False)])
    for path in candidates:
        if Path(path).exists():
            return path
    return None


def _pick_font(font_size_pt: float, render_scale: float,
               font_name: str = "arial", font_size_scale: float = 1.0,
               bold: bool = False):
    """
    Chọn font theo tên (arial/carlito/lato), variant (regular/bold),
    và size từ PDF metadata × scale.
    """
    size = max(6, int(font_size_pt * render_scale * font_size_scale))
    cache_key = (font_name.lower(), bold, size)
    if cache_key in _font_cache:
        return _font_cache[cache_key]

    path = resolve_font_path(font_name, bold)
    if path:
        try:
            font = ImageFont.truetype(path, size, encoding="unic")
            _font_cache[cache_key] = font
            return font
        except (IOError, OSError):
            pass

    # Hard fallback
    font = ImageFont.load_default()
    _font_cache[cache_key] = font
    return font


def _get_font_size_for_match(page, match: dict) -> float:
    """
    Đọc font size (pt) trực tiếp từ text object của PDF tại vùng match.
    Trả về font size pt, fallback về 9.0 nếu không tìm thấy.
    """
    for obj in page.get_objects():
        if obj.type != 1:
            continue
        b = obj.get_bounds()  # x0, y0, x1, y1 trong PDF coords
        overlap_x = max(0, min(match["x1"], b[2]) - max(match["x0"], b[0]))
        overlap_y = max(0, min(match["y1"], b[3]) - max(match["y0"], b[1]))
        if overlap_x > 0 and overlap_y > 0:
            return obj.get_font_size()
    return 9.0  # fallback


def _get_row_py_top(page, match: dict, h_pt: float, img_h: float,
                     row_tolerance_pt: float = 5.0) -> float:
    """
    Tìm py_top (pixel) cao nhất — nhỏ nhất trong pixel space —
    của tất cả text objects cùng dòng với match.
    Align theo TOP (ascender) của dòng vì đây là điểm chung nhất
    giữa các font khác nhau trong cùng row.
    """
    match_y0 = match["y0"]
    # py_top = (h_pt - y1) / h_pt * img_h  với y1 = top trong PDF coords
    # Lấy py_top nhỏ nhất (cao nhất trong ảnh) của cả dòng
    min_py_top = None

    for obj in page.get_objects():
        if obj.type != 1:
            continue
        b = obj.get_bounds()  # x0, y0, x1, y1
        if abs(b[1] - match_y0) <= row_tolerance_pt:
            py_top = (h_pt - b[3]) / h_pt * img_h  # b[3] = y1 = ascender
            if min_py_top is None or py_top < min_py_top:
                min_py_top = py_top

    if min_py_top is None:
        # fallback: dùng y1 của chính match
        min_py_top = (h_pt - match["y1"]) / h_pt * img_h

    return min_py_top


def process_page(page, replacements: list[dict], verbose: bool, dry_run: bool) -> tuple[Image.Image | None, list]:
    """
    Xử lý 1 page: render → tìm matches → overlay.
    Trả về (image_đã_edit, match_log). Image là None nếu không có match hoặc dry_run.
    """
    w_pt = page.get_width()
    h_pt = page.get_height()
    match_log = []

    # Build match plan: xử lý cả replace_all và sequential
    textpage = page.get_textpage()
    all_matches = _build_match_plan(textpage, replacements)
    textpage.close()

    for m in all_matches:
        match_log.append({
            "old": m["old"],
            "new": m["new"],
            "mode": next(
                (r.get("mode", "replace_all") for r in replacements
                 if r["old"] == m["old"] and r["new"] == m["new"]),
                "replace_all"
            ),
            "pdf_coords": {k: round(m[k], 2) for k in ("x0","y0","x1","y1")},
        })
        if verbose:
            print(f"    Found '{m['old']}' → '{m['new']}' at "
                  f"({m['x0']:.1f},{m['y0']:.1f})-({m['x1']:.1f},{m['y1']:.1f})")

    if not all_matches or dry_run:
        return None, match_log

    # Render page → PIL image
    bitmap = page.render(scale=RENDER_SCALE, rotation=0)
    img = bitmap.to_pil().convert("RGB")
    img_w, img_h = img.size
    draw = ImageDraw.Draw(img)

    for m in all_matches:
        # Convert PDF coords → pixels
        px0, py1 = _pdf_to_px(m["x0"], m["y0"], w_pt, h_pt, img_w, img_h)
        px1, py0 = _pdf_to_px(m["x1"], m["y1"], w_pt, h_pt, img_w, img_h)

        # Padding: mở rộng trái/phải và phía trên, KHÔNG pad phía dưới
        # tránh rect che đè vào table border ngay bên dưới text
        px0 -= PADDING_X
        px1 += PADDING_X
        py0 -= PADDING_Y   # top: pad lên
        # py1 giữ nguyên — không mở rộng xuống

        # Detect và fill màu nền
        bg_color = _sample_bg_color(img, px0, py0, px1, py1)
        draw.rectangle([px0, py0, px1, py1], fill=bg_color)

        # Đọc font size pt trực tiếp từ PDF text object — không đoán qua bbox
        font_size_pt = _get_font_size_for_match(page, m)
        font = _pick_font(font_size_pt, RENDER_SCALE,
                          font_name=FONT_NAME,
                          font_size_scale=FONT_SIZE_SCALE,
                          bold=FONT_BOLD)

        # Vertical alignment: dùng py_top cao nhất (nhỏ nhất) của cả dòng
        # Các font khác nhau trong cùng row có ascender đồng đều hơn descender
        # nên align theo top cho kết quả ổn định hơn
        py_row_top = _get_row_py_top(page, m, h_pt, img_h)

        # font.getbbox() trả về (left, top, right, bottom) từ draw-point
        # top thường âm (ascender lên trên draw-point)
        # → py_draw = py_row_top - font_top_offset
        try:
            _bbox = font.getbbox(m["new"])
            font_top_offset = _bbox[1]  # thường âm hoặc 0
        except AttributeError:
            font_top_offset = 0

        py_draw = py_row_top - font_top_offset
        draw.text((px0 + PADDING_X, py_draw), m["new"], fill=(0, 0, 0), font=font)

    return img, match_log


def page_to_pdf_bytes(img: Image.Image, orig_w_pt: float, orig_h_pt: float) -> bytes:
    """Convert PIL image → PDF bytes với kích thước page gốc."""
    import io
    buf = io.BytesIO()
    # Resize về đúng kích thước PDF gốc khi save (DPI mapping)
    dpi = RENDER_SCALE * PDF_DPI
    img.save(buf, format="PDF", resolution=dpi)
    return buf.getvalue()


def replace_in_pdf(pdf_path: Path, replacements: list[dict], output_path: Path,
                   backup: bool, dry_run: bool, verbose: bool) -> dict:
    result = {
        "file": str(pdf_path),
        "status": "ok",
        "pages": [],
        "total_replacements": 0,
        "error": None,
    }

    try:
        doc = pdfium.PdfDocument(str(pdf_path))
    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)
        return result

    total = 0
    page_images = []
    page_sizes = []

    for page_idx in range(len(doc)):
        page = doc[page_idx]
        img, match_log = process_page(page, replacements, verbose, dry_run)
        count = len(match_log)
        total += count
        result["pages"].append({"page": page_idx + 1, "matches": match_log})

        if img is not None:
            page_images.append(img)
        else:
            # Render nguyên xi nếu không có match hoặc dry_run
            if not dry_run:
                bitmap = page.render(scale=RENDER_SCALE, rotation=0)
                page_images.append(bitmap.to_pil().convert("RGB"))
        page_sizes.append((page.get_width(), page.get_height()))

    doc.close()
    result["total_replacements"] = total

    if total == 0:
        result["status"] = "no_match"

    if dry_run:
        return result

    # Ghi output PDF từ images
    if backup and output_path == pdf_path:
        shutil.copy2(pdf_path, pdf_path.with_suffix(f".bak{pdf_path.suffix}"))
        result["backup"] = str(pdf_path.with_suffix(f".bak{pdf_path.suffix}"))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    dpi = RENDER_SCALE * PDF_DPI
    if len(page_images) == 1:
        page_images[0].save(str(output_path), format="PDF", resolution=dpi)
    else:
        page_images[0].save(
            str(output_path), format="PDF", resolution=dpi,
            save_all=True, append_images=page_images[1:]
        )

    return result


# ─── Batch ────────────────────────────────────────────────────────────────────

def run_batch(args):
    input_path = Path(args.input)
    output_dir = Path(args.output) if args.output else None

    if args.config:
        replacements = json.loads(Path(args.config).read_text(encoding="utf-8"))
    else:
        if not args.old or not args.new:
            print("[ERROR] Cần --old và --new, hoặc --config")
            sys.exit(1)
        replacements = [{"old": args.old, "new": args.new}]

    if input_path.is_file():
        pdf_files = [input_path]
    elif input_path.is_dir():
        pdf_files = sorted(input_path.rglob("*.pdf"))
    else:
        print(f"[ERROR] Không tìm thấy '{input_path}'")
        sys.exit(1)

    if not pdf_files:
        print("[INFO] Không có file PDF nào.")
        return

    print(f"\n{'[DRY RUN] ' if args.dry_run else ''}Xử lý {len(pdf_files)} file...")
    print(f"Replace: {replacements}\n{'─'*60}")

    summary = {"ok": 0, "no_match": 0, "error": 0, "total_replacements": 0}
    log_entries = []

    for pdf_path in pdf_files:
        if output_dir:
            try:
                rel = pdf_path.relative_to(input_path if input_path.is_dir() else input_path.parent)
            except ValueError:
                rel = pdf_path.name
            out_path = output_dir / rel
        else:
            out_path = pdf_path

        print(f"  {pdf_path.name}", end=" ... ", flush=True)

        result = replace_in_pdf(
            pdf_path, replacements, out_path,
            backup=not args.no_backup,
            dry_run=args.dry_run,
            verbose=args.verbose,
        )
        log_entries.append(result)
        summary[result["status"]] = summary.get(result["status"], 0) + 1
        summary["total_replacements"] += result["total_replacements"]

        label = {
            "ok":       f"✓ {result['total_replacements']} chỗ thay",
            "no_match": "- không tìm thấy match",
            "error":    f"✗ {result['error']}",
        }.get(result["status"], result["status"])
        print(label)

    print(f"\n{'─'*60}")
    print(f"Kết quả: {summary['ok']} OK | {summary['no_match']} no match | {summary['error']} lỗi")
    print(f"Tổng chỗ thay: {summary['total_replacements']}")

    if not args.dry_run:
        log_path = Path(args.log)
        log_data = {
            "timestamp": datetime.now().isoformat(),
            "replacements": replacements,
            "summary": summary,
            "files": log_entries,
        }
        log_path.write_text(json.dumps(log_data, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Log: {log_path}")


# ─── CLI ──────────────────────────────────────────────────────────────────────

def main():
    p = argparse.ArgumentParser(description="Batch replace text trong PDF (render-based)")
    p.add_argument("--input",     required=True, help="Folder hoặc file PDF")
    p.add_argument("--old",       help="Text cần tìm")
    p.add_argument("--new",       help="Text thay thế")
    p.add_argument("--config",    help="File JSON: [{\"old\":\"...\",\"new\":\"...\"}]")
    p.add_argument("--output",    help="Folder output (mặc định: ghi đè)")
    p.add_argument("--no-backup", action="store_true")
    p.add_argument("--dry-run",   action="store_true")
    p.add_argument("--verbose",   action="store_true")
    p.add_argument("--log",       default="pdf_replace_log.json")
    p.add_argument("--font",      default="arial",
                   choices=["arial", "carlito", "lato"],
                   help="Font chữ cho text thay thế (mặc định: arial)")
    p.add_argument("--font-bold", action="store_true", dest="font_bold",
                   help="Dùng Bold variant của font")
    p.add_argument("--font-size-scale", type=float, default=1.0,
                   dest="font_size_scale",
                   help="Hệ số nhân font size (mặc định: 1.0, to hơn: 1.1, nhỏ hơn: 0.9)")
    main_args = p.parse_args()

    # Apply font settings vào global config
    import sys as _sys
    _mod = _sys.modules[__name__]
    _mod.FONT_NAME       = main_args.font
    _mod.FONT_BOLD       = main_args.font_bold
    _mod.FONT_SIZE_SCALE = main_args.font_size_scale

    run_batch(main_args)


if __name__ == "__main__":
    main()
