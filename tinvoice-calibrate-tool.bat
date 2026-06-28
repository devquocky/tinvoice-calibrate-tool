@echo off
setlocal
cd /d "%~dp0"

:: 1. Kiểm tra Python
where python >nul 2>nul
if errorlevel 1 (
    echo [LOI] Python khong duoc tim thay trong PATH.
    echo Vui long cai Python 3.10+ va dam bao da them vao PATH.
    pause
    exit /b 1
)

:: 2. Kiểm tra file UI
if not exist "pdf_replace_ui.py" (
    echo [LOI] Khong tim thay pdf_replace_ui.py trong thu muc nay.
    echo Hay dam bao file nay cung thu muc voi run_ui.bat.
    pause
    exit /b 1
)

:: 3. Kiểm tra thư viện pypdfium2 và Pillow
python -c "import pypdfium2, PIL" 2>nul
if errorlevel 1 (
    echo [LOI] Thieu thu vien pypdfium2 hoac Pillow.
    echo Vui long chay: pip install pypdfium2 Pillow
    pause
    exit /b 1
)

:: 4. Mọi thứ OK → chạy UI âm thầm (không console)
start "" pythonw.exe pdf_replace_ui.py
exit /b 0
