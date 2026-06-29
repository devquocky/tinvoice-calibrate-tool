# PDF Text Replacer

Tool thay thế text hàng loạt trong các file PDF — hỗ trợ giao diện đồ họa (UI) và command line (CLI).

---

## Yêu cầu hệ thống

- Windows 10 / 11 (64-bit)
- Python **3.10 trở lên**
- Không cần cài Office, Acrobat hay bất kỳ phần mềm PDF nào

---

## Cài đặt

### Bước 1 — Cài Python

Tải Python tại **https://www.python.org/downloads/**

> ⚠️ Trong màn hình cài đặt, **tick vào ô "Add Python to PATH"** trước khi nhấn Install.

Kiểm tra sau khi cài:

```
python --version
```

Kết quả mong đợi: `Python 3.10.x` hoặc cao hơn.

---

### Bước 2 — Tải source code

**Cách A — Tải ZIP (không cần Git):**

1. Vào trang GitHub của project
2. Nhấn nút **Code → Download ZIP**
3. Giải nén vào thư mục tùy chọn, ví dụ `C:\pdf-replacer`

**Cách B — Clone bằng Git:**

```
git clone https://github.com/<your-repo>/pdf-replacer.git
cd pdf-replacer
```

---

### Bước 3 — Cài thư viện

Mở **Command Prompt** hoặc **PowerShell**, `cd` vào thư mục vừa giải nén, rồi chạy:

```
pip install pypdfium2 Pillow
```

Kiểm tra:

```
python -c "import pypdfium2, PIL; print('OK')"
```

Kết quả mong đợi: `OK`

---

## Sử dụng — Giao diện đồ họa (UI)

Double-click vào `tinvoice-calibrate-tool.bat`, hoặc chạy:

```
python pdf_replace_ui.py
```

### Các bước thao tác

1. **Input folder** — chọn thư mục chứa các file PDF cần xử lý
2. **Output folder** — chọn thư mục lưu kết quả (để trống = ghi đè file gốc)
3. **Suffix** — hậu tố thêm vào tên file output, ví dụ `_replaced` → `INVOICE_001_replaced.pdf`
4. **Replacements** — nhập các cặp text cần thay:
   - Cột trái: text cần tìm (phân biệt hoa/thường)
   - Cột phải: text thay thế
   - Nhấn **+ Thêm dòng** để thêm cặp mới
5. Tick **Dry-run** nếu muốn kiểm tra kết quả trước (không ghi file)
6. Nhấn **▶ Chạy**

### Import / Export JSON

Để tái sử dụng cấu hình replacements, dùng nút **Export JSON** để lưu, **Import JSON** để tải lại lần sau.

Format file JSON:

```json
[
  { "old": "MEGA DIGITAL LLC",                        "new": "Tên công ty mới" },
  { "old": "18630 SANTA ISADORA ST FOUNTAIN VALLEY,", "new": "Địa chỉ dòng 1," },
  { "old": "CA, Fountain Valley, California 92708",   "new": "Địa chỉ dòng 2" }
]
```

---

## Sử dụng — Command Line (CLI)

### Thay thế cơ bản

```bat
pdf_replace.bat --input C:\invoices --old "MEGA DIGITAL LLC" --new "Acme Corp" --output C:\output
```

### Nhiều replacements cùng lúc (khuyến nghị)

```bat
pdf_replace.bat --input C:\invoices --config replacements.json --output C:\output
```

### Thêm suffix vào tên file

```bat
pdf_replace.bat --input C:\invoices --config replacements.json --output C:\output --suffix "_Acme"
```

### Kiểm tra trước khi chạy thật (dry-run)

```bat
pdf_replace.bat --input C:\invoices --old "MEGA DIGITAL LLC" --new "Acme Corp" --dry-run --verbose
```

### Toàn bộ tham số

| Tham số | Mô tả |
|---|---|
| `--input` | Thư mục hoặc file PDF đầu vào |
| `--old` | Text cần tìm |
| `--new` | Text thay thế |
| `--config` | File JSON chứa nhiều cặp replacement |
| `--output` | Thư mục output (mặc định: ghi đè file gốc) |
| `--suffix` | Hậu tố thêm vào tên file output |
| `--no-backup` | Không tạo file backup `.bak` |
| `--dry-run` | Chỉ scan, không ghi file |
| `--verbose` | In chi tiết từng match |
| `--log` | Đường dẫn file log JSON (mặc định: `pdf_replace_log.json`) |

---

## Giới hạn kỹ thuật

### Output là PDF ảnh (image PDF)

Tool hoạt động bằng cách render PDF thành ảnh, chỉnh sửa, rồi export lại. File output **không có selectable text**. Đây là đánh đổi để đảm bảo layout gốc được giữ nguyên.

**Hệ quả quan trọng:** Không được dùng file output làm input cho lần chạy tiếp theo. Luôn dùng file PDF gốc (text PDF) làm input, gộp tất cả replacements vào một lần chạy duy nhất qua `--config` hoặc UI.

### Chỉ hoạt động với text PDF

PDF dạng scan (image PDF, không có text layer) sẽ báo `no_match`. Mở file trong trình đọc PDF, nếu không bôi đen chọn text được → tool không xử lý được file đó.

### Search phân biệt hoa/thường

`"mega digital llc"` ≠ `"MEGA DIGITAL LLC"`. Nhập chính xác text xuất hiện trong PDF.

### Font thay thế

Text mới sẽ dùng Arial thay cho font gốc của PDF. Với các trường hợp thông thường trông gần như không phân biệt được.

---

## Các lỗi thường gặp

### `python` không được nhận diện

```
'python' is not recognized as an internal or external command
```

**Nguyên nhân:** Python chưa được thêm vào PATH.

**Cách khắc phục:**

1. Mở **Start → tìm kiếm "Environment Variables"**
2. Chọn **Edit the system environment variables**
3. Nhấn **Environment Variables…**
4. Trong phần **User variables**, chọn `Path` → **Edit**
5. Thêm đường dẫn đến Python, ví dụ: `C:\Users\TenBan\AppData\Local\Programs\Python\Python311\`
6. Thêm cả Scripts: `C:\Users\TenBan\AppData\Local\Programs\Python\Python311\Scripts\`
7. Nhấn OK, đóng và mở lại Command Prompt

Hoặc đơn giản hơn: cài lại Python và tick **"Add Python to PATH"**.

---

### `No module named 'pypdfium2'`

```
[ERROR] Thiếu pypdfium2. Chạy: pip install pypdfium2
```

**Cách khắc phục:**

```
pip install pypdfium2 Pillow
```

Nếu vẫn lỗi, thử:

```
python -m pip install pypdfium2 Pillow
```

---

### `pip` không được nhận diện

```
'pip' is not recognized...
```

**Cách khắc phục:**

```
python -m pip install pypdfium2 Pillow
```

---

### Không tìm thấy `pdf_replace.py`

```
[ERROR] Không tìm thấy pdf_replace.py tại ...
```

**Nguyên nhân:** `pdf_replace_ui.py` và `pdf_replace.py` không cùng thư mục.

**Cách khắc phục:** Đảm bảo cả hai file nằm cùng một thư mục.

---

### `no_match` — không tìm thấy text

```
– INVOICE_001.pdf  (không match)
```

**Các nguyên nhân thường gặp:**

1. **Text gõ sai hoa/thường** — mở PDF, copy text rồi paste vào ô "Text cần tìm"
2. **File PDF là image PDF** — mở file trong trình đọc PDF, thử bôi đen text; nếu không chọn được → đây là PDF ảnh, tool không xử lý được
3. **Dùng file output làm input** — file output của tool là image PDF, không còn text layer; phải luôn dùng file PDF gốc

---

### File output bị lệch layout

**Nguyên nhân thường gặp:** Text mới dài hơn đáng kể so với text gốc, tràn ra ngoài vùng che.

**Cách khắc phục:** Rút gọn text mới để xấp xỉ độ dài text gốc. Dùng `--dry-run --verbose` để xem tọa độ match trước khi chạy thật.

---

### UI không mở được

```
ModuleNotFoundError: No module named 'tkinter'
```

**Nguyên nhân:** Bản Python từ Microsoft Store không đi kèm tkinter.

**Cách khắc phục:** Cài Python từ **https://www.python.org/downloads/** (chọn bản **Windows installer 64-bit**), không dùng bản Microsoft Store.

---

### `PermissionError` khi ghi file

```
PermissionError: [Errno 13] Permission denied
```

**Nguyên nhân:** File PDF đang được mở trong Acrobat, Edge, hoặc trình đọc PDF khác.

**Cách khắc phục:** Đóng tất cả chương trình đang mở file đó, rồi chạy lại.

---

## Đọc file log

Sau mỗi lần chạy, tool tự động tạo `pdf_replace_log.json`:

```json
{
  "timestamp": "2026-06-28T10:30:00",
  "summary": { "ok": 8, "no_match": 1, "error": 0, "total_replacements": 32 },
  "files": [
    { "file": "INVOICE_001.pdf", "status": "ok", "total_replacements": 4 },
    { "file": "INVOICE_002.pdf", "status": "no_match", "total_replacements": 0 }
  ]
}
```

Dùng file log để kiểm tra file nào cần xem lại sau mỗi batch.

---

## Workflow khuyến nghị

```
File PDF gốc (text PDF)
        │
        ▼
  Gộp TẤT CẢ replacements vào 1 lần chạy
  (dùng --config hoặc thêm nhiều dòng trong UI)
        │
        ▼
  File PDF output (image PDF)
        │
        ├─→ Gửi client ✓
        │
        └─→ KHÔNG dùng làm input lần tiếp theo ✗
```

---

## Tùy chỉnh font

### Các font hỗ trợ

| Font | Ghi chú |
|---|---|
| `arial` | Mặc định, có sẵn trên mọi Windows |
| `carlito` | Metric tương đương Calibri, cần cài hoặc đặt vào `fonts/` |
| `lato` | Font hiện đại, đi kèm sẵn trong thư mục `fonts/` của project |

**Để dùng Carlito trên Windows:** Tải tại https://fonts.google.com/specimen/Carlito, đặt `Carlito-Regular.ttf` vào thư mục `fonts/` cạnh script, hoặc cài vào hệ thống.

**Lato** đã được đóng gói sẵn trong thư mục `fonts/` — không cần cài thêm.

### CLI

```bat
:: Dùng Lato, giữ nguyên size
pdf_replace.bat --input C:\invoices --config rep.json --output C:\output --font lato

:: Dùng Carlito, to hơn 5%
pdf_replace.bat --input C:\invoices --config rep.json --output C:\output --font carlito --font-size-scale 1.05

:: Nhỏ hơn 10%
pdf_replace.bat --input C:\invoices --config rep.json --output C:\output --font-size-scale 0.9
```

### UI

Bổ sung trong phiên bản UI tiếp theo — hiện tại chỉnh font qua CLI hoặc sửa trực tiếp hai dòng đầu trong `pdf_replace.py`:

```python
FONT_NAME       = "lato"   # arial | carlito | lato
FONT_SIZE_SCALE = 1.0      # 1.0 = giữ nguyên
```
