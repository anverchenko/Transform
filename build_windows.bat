@echo off
cd /d "%~dp0"
echo === Installing dependencies ===
pip install -r requirements.txt
pip install pyinstaller

echo.
echo === Building .exe ===
python -m PyInstaller --onefile --name transcribe --windowed --exclude-module torch.cuda --add-data "%LOCALAPPDATA%\Python\pythoncore-3.14-64\Lib\site-packages\whisper;whisper" transcribe.py

echo.
echo === Done! ===
echo Your .exe is in: dist\transcribe.exe
pause
