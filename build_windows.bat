@echo off
cd /d "%~dp0"
echo === Installing dependencies ===
pip install -r requirements.txt
pip install pyinstaller

echo.
echo === Building .exe ===
python -m PyInstaller --onefile --name transcribe --windowed transcribe.py

echo.
echo === Done! ===
echo Your .exe is in: dist\transcribe.exe
pause
