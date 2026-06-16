@echo off
cd /d "%~dp0"

echo === Installing dependencies ===
pip install -r requirements.txt
pip install pyinstaller

echo.
echo === Building Release .exe ===
python -m PyInstaller ^
    --onefile ^
    --name Transform ^
    --windowed ^
    --additional-hooks-dir . ^
    --optimize 2 ^
    --strip ^
    --noupx ^
    --exclude-module matplotlib ^
    --exclude-module pandas ^
    --exclude-module scipy ^
    --exclude-module PIL ^
    --exclude-module cv2 ^
    --exclude-module IPython ^
    --exclude-module notebook ^
    --exclude-module pytest ^
    transcribe.py

echo.
echo === Done! ===
echo Your .exe is in: dist\Transform.exe
pause
