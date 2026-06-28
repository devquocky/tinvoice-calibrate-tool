"""
PDF Batch Text Replacer — Tkinter UI
Đặt file này cùng thư mục với pdf_replace.py
Chạy: python pdf_replace_ui.py
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import json
import sys
import io
from pathlib import Path
from datetime import datetime

# ── Màu sắc & font ────────────────────────────────────────────────────────────
BG          = "#F7F7F8"
PANEL       = "#FFFFFF"
BORDER      = "#E2E2E5"
ACCENT      = "#2563EB"        # xanh dương chính
ACCENT_HOV  = "#1D4ED8"
DANGER      = "#DC2626"
SUCCESS     = "#16A34A"
WARN        = "#D97706"
TEXT        = "#111827"
TEXT_SUB    = "#6B7280"
FONT_UI     = ("Segoe UI", 9)
FONT_LABEL  = ("Segoe UI", 9, "bold")
FONT_MONO   = ("Consolas", 8)
FONT_TITLE  = ("Segoe UI", 11, "bold")
FONT_HEAD   = ("Segoe UI", 9, "bold")
ROW_ODD     = "#FAFAFA"
ROW_EVEN    = "#FFFFFF"
ROW_SEL     = "#DBEAFE"


def styled_btn(parent, text, command, style="primary", **kw):
    colors = {
        "primary": (ACCENT,  "#FFFFFF", ACCENT_HOV),
        "ghost":   (BORDER,  TEXT,      "#D1D5DB"),
        "danger":  (DANGER,  "#FFFFFF", "#B91C1C"),
    }
    bg, fg, hov = colors.get(style, colors["primary"])
    btn = tk.Button(parent, text=text, command=command,
                    bg=bg, fg=fg, relief="flat", cursor="hand2",
                    font=FONT_UI, padx=10, pady=5,
                    activebackground=hov, activeforeground=fg, **kw)
    return btn


class ReplacementRow:
    """Một hàng old → new trong bảng replacement."""
    def __init__(self, parent, idx, on_delete):
        self.frame = tk.Frame(parent, bg=ROW_ODD if idx % 2 else ROW_EVEN,
                              pady=3, padx=6)
        self.frame.pack(fill="x", pady=1)

        tk.Label(self.frame, text=f"{idx+1:02d}", bg=self.frame["bg"],
                 fg=TEXT_SUB, font=FONT_MONO, width=3).pack(side="left")

        self.old_var = tk.StringVar()
        self.new_var = tk.StringVar()

        e_old = tk.Entry(self.frame, textvariable=self.old_var,
                         font=FONT_UI, relief="solid", bd=1,
                         highlightthickness=0)
        e_old.pack(side="left", fill="x", expand=True, padx=(4, 4))

        tk.Label(self.frame, text="→", bg=self.frame["bg"],
                 fg=TEXT_SUB, font=FONT_UI).pack(side="left")

        e_new = tk.Entry(self.frame, textvariable=self.new_var,
                         font=FONT_UI, relief="solid", bd=1,
                         highlightthickness=0)
        e_new.pack(side="left", fill="x", expand=True, padx=(4, 4))

        tk.Button(self.frame, text="✕", command=on_delete,
                  bg=self.frame["bg"], fg=DANGER, relief="flat",
                  font=("Segoe UI", 9, "bold"), cursor="hand2",
                  activebackground="#FEE2E2", bd=0, padx=4).pack(side="left")

    def get(self):
        return self.old_var.get().strip(), self.new_var.get().strip()

    def set(self, old, new):
        self.old_var.set(old)
        self.new_var.set(new)

    def destroy(self):
        self.frame.destroy()


class PDFReplaceUI:
    def __init__(self, root):
        self.root = root
        self.root.title("PDF Text Replacer")
        self.root.geometry("780x680")
        self.root.minsize(680, 560)
        self.root.configure(bg=BG)
        self.root.resizable(True, True)

        self._rows: list[ReplacementRow] = []
        self._running = False

        self._build_ui()
        self._check_engine()

    # ── Check engine ──────────────────────────────────────────────────────────
    def _check_engine(self):
        try:
            import pypdfium2
            from PIL import Image
        except ImportError as e:
            self._log(f"[ERROR] Thiếu thư viện: {e}", "error")
            self._log("Chạy:  pip install pypdfium2 Pillow", "warn")

    # ── Build UI ──────────────────────────────────────────────────────────────
    def _build_ui(self):
        # Header
        hdr = tk.Frame(self.root, bg=PANEL, relief="flat", bd=0)
        hdr.pack(fill="x")
        tk.Frame(hdr, bg=ACCENT, width=4).pack(side="left", fill="y")
        tk.Label(hdr, text="PDF Text Replacer", bg=PANEL,
                 fg=TEXT, font=FONT_TITLE, pady=12, padx=14).pack(side="left")
        tk.Frame(self.root, bg=BORDER, height=1).pack(fill="x")

        # Body
        body = tk.Frame(self.root, bg=BG)
        body.pack(fill="both", expand=True, padx=16, pady=12)
        body.columnconfigure(0, weight=1)
        body.rowconfigure(1, weight=1)

        # ── Row 0: IO Section ─────────────────────────────────────────────────
        io_frame = tk.LabelFrame(body, text=" Input / Output ", bg=PANEL,
                                 fg=TEXT_SUB, font=FONT_UI,
                                 relief="solid", bd=1, padx=10, pady=8)
        io_frame.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        io_frame.columnconfigure(1, weight=1)

        # Input folder
        tk.Label(io_frame, text="Input folder", bg=PANEL,
                 fg=TEXT, font=FONT_HEAD).grid(row=0, column=0, sticky="w", pady=3)
        self.input_var = tk.StringVar()
        tk.Entry(io_frame, textvariable=self.input_var, font=FONT_UI,
                 relief="solid", bd=1).grid(row=0, column=1, sticky="ew",
                                            padx=(8, 6), pady=3)
        styled_btn(io_frame, "Browse…",
                   self._browse_input, "ghost").grid(row=0, column=2, pady=3)

        # Output folder
        tk.Label(io_frame, text="Output folder", bg=PANEL,
                 fg=TEXT, font=FONT_HEAD).grid(row=1, column=0, sticky="w", pady=3)
        self.output_var = tk.StringVar()
        tk.Entry(io_frame, textvariable=self.output_var, font=FONT_UI,
                 relief="solid", bd=1).grid(row=1, column=1, sticky="ew",
                                            padx=(8, 6), pady=3)
        styled_btn(io_frame, "Browse…",
                   self._browse_output, "ghost").grid(row=1, column=2, pady=3)

        # Suffix + options row
        opt_row = tk.Frame(io_frame, bg=PANEL)
        opt_row.grid(row=2, column=0, columnspan=3, sticky="w", pady=(6, 0))

        tk.Label(opt_row, text="Suffix:", bg=PANEL,
                 fg=TEXT, font=FONT_HEAD).pack(side="left")
        self.suffix_var = tk.StringVar()
        tk.Entry(opt_row, textvariable=self.suffix_var, font=FONT_UI,
                 relief="solid", bd=1, width=16).pack(side="left", padx=(6, 16))

        self.backup_var = tk.BooleanVar(value=True)
        tk.Checkbutton(opt_row, text="Tạo file backup (.bak)",
                       variable=self.backup_var, bg=PANEL,
                       fg=TEXT, font=FONT_UI,
                       activebackground=PANEL).pack(side="left", padx=(0, 12))

        self.dryrun_var = tk.BooleanVar(value=False)
        tk.Checkbutton(opt_row, text="Dry-run (không ghi file)",
                       variable=self.dryrun_var, bg=PANEL,
                       fg=TEXT, font=FONT_UI,
                       activebackground=PANEL).pack(side="left")

        # ── Row 1: Replacements Section ───────────────────────────────────────
        rep_outer = tk.LabelFrame(body, text=" Replacements ", bg=PANEL,
                                  fg=TEXT_SUB, font=FONT_UI,
                                  relief="solid", bd=1, padx=10, pady=8)
        rep_outer.grid(row=1, column=0, sticky="nsew", pady=(0, 8))
        rep_outer.columnconfigure(0, weight=1)
        rep_outer.rowconfigure(1, weight=1)

        # Column headers
        hdr_row = tk.Frame(rep_outer, bg=PANEL)
        hdr_row.grid(row=0, column=0, sticky="ew", pady=(0, 4))
        tk.Label(hdr_row, text="   ", bg=PANEL, font=FONT_MONO, width=3).pack(side="left")
        tk.Label(hdr_row, text="Text cần tìm (old)", bg=PANEL,
                 fg=TEXT_SUB, font=FONT_UI).pack(side="left", expand=True)
        tk.Label(hdr_row, text="Text thay thế (new)", bg=PANEL,
                 fg=TEXT_SUB, font=FONT_UI).pack(side="left", expand=True)

        # Scrollable rows container
        canvas_frame = tk.Frame(rep_outer, bg=PANEL)
        canvas_frame.grid(row=1, column=0, sticky="nsew")
        canvas_frame.columnconfigure(0, weight=1)
        canvas_frame.rowconfigure(0, weight=1)

        self.canvas = tk.Canvas(canvas_frame, bg=PANEL,
                                highlightthickness=0, bd=0)
        scrollbar = tk.Scrollbar(canvas_frame, orient="vertical",
                                 command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=scrollbar.set)

        self.canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        self.rows_frame = tk.Frame(self.canvas, bg=PANEL)
        self.canvas_window = self.canvas.create_window(
            (0, 0), window=self.rows_frame, anchor="nw")

        self.rows_frame.bind("<Configure>", self._on_rows_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

        # Toolbar dưới bảng
        btn_row = tk.Frame(rep_outer, bg=PANEL)
        btn_row.grid(row=2, column=0, sticky="ew", pady=(8, 0))

        styled_btn(btn_row, "+ Thêm dòng",
                   self._add_row, "ghost").pack(side="left", padx=(0, 6))
        styled_btn(btn_row, "Import JSON",
                   self._import_json, "ghost").pack(side="left", padx=(0, 6))
        styled_btn(btn_row, "Export JSON",
                   self._export_json, "ghost").pack(side="left")
        styled_btn(btn_row, "Xóa tất cả",
                   self._clear_rows, "danger").pack(side="right")

        # ── Row 2: Run button ─────────────────────────────────────────────────
        run_row = tk.Frame(body, bg=BG)
        run_row.grid(row=2, column=0, sticky="ew", pady=(0, 8))

        self.run_btn = styled_btn(run_row, "▶  Chạy",
                                  self._run, "primary", width=14)
        self.run_btn.pack(side="left")

        self.progress = ttk.Progressbar(run_row, mode="indeterminate", length=200)
        self.progress.pack(side="left", padx=(12, 0))

        self.status_lbl = tk.Label(run_row, text="", bg=BG,
                                   fg=TEXT_SUB, font=FONT_UI)
        self.status_lbl.pack(side="left", padx=10)

        # ── Row 3: Log ────────────────────────────────────────────────────────
        log_frame = tk.LabelFrame(body, text=" Log ", bg=PANEL,
                                  fg=TEXT_SUB, font=FONT_UI,
                                  relief="solid", bd=1, padx=6, pady=6)
        log_frame.grid(row=3, column=0, sticky="ew")

        self.log_text = tk.Text(log_frame, height=6, font=FONT_MONO,
                                bg="#1E1E2E", fg="#CDD6F4",
                                relief="flat", bd=0, state="disabled",
                                wrap="word", selectbackground=ACCENT)
        self.log_text.pack(fill="x")

        # Tag màu cho log
        self.log_text.tag_config("ok",    foreground="#A6E3A1")
        self.log_text.tag_config("error", foreground="#F38BA8")
        self.log_text.tag_config("warn",  foreground="#FAB387")
        self.log_text.tag_config("info",  foreground="#89DCEB")

        # Thêm 3 dòng mặc định
        self._add_row()
        self._add_row()
        self._add_row()

    # ── Canvas scroll ─────────────────────────────────────────────────────────
    def _on_rows_configure(self, e=None):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, e):
        self.canvas.itemconfig(self.canvas_window, width=e.width)

    def _on_mousewheel(self, e):
        self.canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")

    # ── Row management ────────────────────────────────────────────────────────
    def _add_row(self, old="", new=""):
        idx = len(self._rows)
        row = ReplacementRow(self.rows_frame, idx,
                             on_delete=lambda r=None: self._delete_row(row))
        row.set(old, new)
        self._rows.append(row)
        self.root.after(50, self._on_rows_configure)

    def _delete_row(self, row):
        row.destroy()
        self._rows.remove(row)
        self._reindex()

    def _reindex(self):
        for i, row in enumerate(self._rows):
            bg = ROW_ODD if i % 2 else ROW_EVEN
            row.frame.configure(bg=bg)
            for child in row.frame.winfo_children():
                try:
                    child.configure(bg=bg)
                except Exception:
                    pass

    def _clear_rows(self):
        if not self._rows:
            return
        if messagebox.askyesno("Xác nhận", "Xóa tất cả dòng?"):
            for row in self._rows:
                row.destroy()
            self._rows.clear()

    def _get_replacements(self) -> list[dict]:
        reps = []
        for row in self._rows:
            old, new = row.get()
            if old:
                reps.append({"old": old, "new": new})
        return reps

    # ── File operations ───────────────────────────────────────────────────────
    def _browse_input(self):
        path = filedialog.askdirectory(title="Chọn folder PDF đầu vào")
        if path:
            self.input_var.set(path)

    def _browse_output(self):
        path = filedialog.askdirectory(title="Chọn folder output")
        if path:
            self.output_var.set(path)

    def _import_json(self):
        path = filedialog.askopenfilename(
            title="Import replacements JSON",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")])
        if not path:
            return
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
            if not isinstance(data, list):
                raise ValueError("JSON phải là array")
            for row in self._rows:
                row.destroy()
            self._rows.clear()
            for item in data:
                self._add_row(item.get("old", ""), item.get("new", ""))
            self._log(f"Imported {len(data)} replacements từ {Path(path).name}", "ok")
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không đọc được JSON:\n{e}")

    def _export_json(self):
        reps = self._get_replacements()
        if not reps:
            messagebox.showwarning("Trống", "Không có replacement nào để export.")
            return
        path = filedialog.asksaveasfilename(
            title="Lưu replacements JSON",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")])
        if not path:
            return
        Path(path).write_text(json.dumps(reps, ensure_ascii=False, indent=2),
                              encoding="utf-8")
        self._log(f"Exported {len(reps)} replacements → {Path(path).name}", "ok")

    # ── Log ───────────────────────────────────────────────────────────────────
    def _log(self, msg: str, level: str = "info"):
        self.log_text.configure(state="normal")
        ts = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert("end", f"[{ts}] {msg}\n", level)
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _set_status(self, msg, color=TEXT_SUB):
        self.status_lbl.configure(text=msg, fg=color)

    # ── Run ───────────────────────────────────────────────────────────────────
    def _run(self):
        if self._running:
            return

        # Validate
        input_dir = self.input_var.get().strip()
        output_dir = self.output_var.get().strip()
        reps = self._get_replacements()

        if not input_dir:
            messagebox.showerror("Thiếu thông tin", "Chọn input folder.")
            return
        if not Path(input_dir).exists():
            messagebox.showerror("Lỗi", f"Không tìm thấy:\n{input_dir}")
            return
        if not reps:
            messagebox.showerror("Thiếu thông tin",
                                 "Thêm ít nhất một cặp replacement.")
            return

        self._running = True
        self.run_btn.configure(state="disabled", text="Đang chạy…")
        self.progress.start(12)
        self._set_status("Đang xử lý…", ACCENT)
        self._log(f"Bắt đầu — input: {input_dir}", "info")

        thread = threading.Thread(target=self._run_worker,
                                  args=(input_dir, output_dir, reps),
                                  daemon=True)
        thread.start()

    def _run_worker(self, input_dir, output_dir, reps):
        try:
            # Import engine
            engine_path = Path(__file__).parent / "pdf_replace.py"
            if not engine_path.exists():
                self.root.after(0, self._log,
                                f"Không tìm thấy pdf_replace.py tại {engine_path}", "error")
                self.root.after(0, self._finish_run, 0, 0, 1)
                return

            import importlib.util
            spec = importlib.util.spec_from_file_location("pdf_replace", engine_path)
            engine = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(engine)

            # Collect files
            pdf_files = sorted(Path(input_dir).rglob("*.pdf"))
            if not pdf_files:
                self.root.after(0, self._log, "Không có file PDF nào trong folder.", "warn")
                self.root.after(0, self._finish_run, 0, 0, 0)
                return

            self.root.after(0, self._log,
                            f"Tìm thấy {len(pdf_files)} file PDF", "info")

            ok = no_match = errors = 0
            suffix = self.suffix_var.get().strip()
            dry_run = self.dryrun_var.get()
            backup = self.backup_var.get()

            for pdf_path in pdf_files:
                # Tính output path
                if output_dir:
                    try:
                        rel = pdf_path.relative_to(input_dir)
                    except ValueError:
                        rel = Path(pdf_path.name)
                    if suffix:
                        rel = rel.with_name(rel.stem + suffix + rel.suffix)
                    out_path = Path(output_dir) / rel
                else:
                    if suffix:
                        out_path = pdf_path.with_name(
                            pdf_path.stem + suffix + pdf_path.suffix)
                    else:
                        out_path = pdf_path

                result = engine.replace_in_pdf(
                    pdf_path, reps, out_path,
                    backup=backup,
                    dry_run=dry_run,
                    verbose=False,
                )

                status = result["status"]
                n = result["total_replacements"]

                if status == "ok":
                    ok += 1
                    msg = f"✓ {pdf_path.name}  ({n} chỗ thay)"
                    lvl = "ok"
                elif status == "no_match":
                    no_match += 1
                    msg = f"–  {pdf_path.name}  (không match)"
                    lvl = "warn"
                else:
                    errors += 1
                    msg = f"✗ {pdf_path.name}  {result['error']}"
                    lvl = "error"

                self.root.after(0, self._log, msg, lvl)

            self.root.after(0, self._finish_run, ok, no_match, errors)

        except Exception as e:
            import traceback
            self.root.after(0, self._log, f"Lỗi nghiêm trọng: {e}", "error")
            self.root.after(0, self._log, traceback.format_exc(), "error")
            self.root.after(0, self._finish_run, 0, 0, 1)

    def _finish_run(self, ok, no_match, errors):
        self._running = False
        self.run_btn.configure(state="normal", text="▶  Chạy")
        self.progress.stop()

        total = ok + no_match + errors
        if errors:
            color = DANGER
            status = f"{ok}/{total} OK  •  {errors} lỗi"
        elif no_match == total:
            color = WARN
            status = "Không match file nào"
        else:
            color = SUCCESS
            status = f"{ok}/{total} OK  •  {no_match} không match"

        self._set_status(status, color)
        self._log(f"Hoàn tất — {status}", "ok" if not errors else "error")


# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    root = tk.Tk()
    root.tk_setPalette(background=BG)

    # Windows DPI aware
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass

    app = PDFReplaceUI(root)
    root.mainloop()
