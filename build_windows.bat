
@echo off
py -m pip install --upgrade pip
py -m pip install requests pyinstaller
py -m PyInstaller --onefile --windowed --name RATKA_Receiver receiver.py
echo.
echo EXE is ready in the dist folder.
pause
