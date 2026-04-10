@echo off
echo === Installing dependencies ===
pip install -r requirements.txt

echo.
echo === Building .exe ===
pyinstaller --onefile --name transcribe --console transcribe.py

echo.
echo === Done! ===
echo Your .exe is in: dist\transcribe.exe
pause
