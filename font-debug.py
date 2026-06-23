from PIL import ImageFont
import pypdfium2 as pdfium

# Kiểm tra font nào đang được pick
def _pick_font_debug(font_h_px):
    size = max(8, int(font_h_px * 0.78))
    candidates = [
        "arial.ttf", "Arial.ttf",
        "calibri.ttf", "Calibri.ttf",
        "C:/Windows/Fonts/arial.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for c in candidates:
        try:
            f = ImageFont.truetype(c, size)
            print(f"✓ Dùng font: {c}, size={size}px")
            return f
        except:
            print(f"  ✗ Không có: {c}")
    print("⚠ Fallback PIL default — đây là nguyên nhân font nhỏ!")
    return ImageFont.load_default()

# font_h_px tại RENDER_SCALE=3: bbox height 11.45pt * 3 = 34.35px
_pick_font_debug(34.35)
