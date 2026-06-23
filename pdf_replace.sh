#!/bin/bash
# PDF Batch Text Replacer - Linux/macOS launcher
# Đặt cùng thư mục với pdf_replace.py

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Kiểm tra Python
if ! command -v python3 &>/dev/null; then
    echo "[ERROR] Không tìm thấy python3."
    exit 1
fi

# Kiểm tra dependencies
python3 -c "import pypdfium2, PIL" 2>/dev/null || {
    echo "[INFO] Đang cài dependencies..."
    pip install pypdfium2 Pillow --break-system-packages
}

python3 "$SCRIPT_DIR/pdf_replace.py" "$@"
