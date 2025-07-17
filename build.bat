@echo off
REM ============================================================================
REM  Build script for Edge TTS GUI
REM
REM  This script uses PyInstaller to package the Python application into a
REM  single standalone executable file (.exe).
REM ============================================================================

echo [1/3] Installing PyInstaller...
pip install pyinstaller

echo [2/3] Building the executable...
REM --onefile      : Bundles everything into a single executable.
REM --windowed     : Prevents a console window from appearing.
REM --name         : Specifies the name of the output file.
REM --icon         : Specifies the icon for the executable.
REM --hidden-import: Informs PyInstaller of modules that are not easily found.
REM tts_gui.py     : Your main application script.

pyinstaller --onefile --windowed --name "СϦTTS" --icon="icon.ico" ^
    --hidden-import "PyQt6.QtMultimedia" ^
    --hidden-import "PyQt6.QtSvg" ^
    --hidden-import "asyncio" ^
    tts_gui.py

echo [3/3] Build process completed.
echo The executable can be found in the 'dist' folder.
echo.
pause
