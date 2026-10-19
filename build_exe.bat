@echo off
setlocal
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
    echo ERROR: Python was not found on PATH.
    goto :failed
)

python -m PyInstaller --version >nul 2>nul
if errorlevel 1 (
    echo ERROR: PyInstaller is not installed for the active Python.
    echo Install it with: python -m pip install pyinstaller
    goto :failed
)

if not exist "main.py" (
    echo ERROR: main.py was not found in %CD%.
    goto :failed
)
if not exist "icon.ico" (
    echo ERROR: icon.ico was not found in %CD%.
    goto :failed
)
if not exist "icon.png" (
    echo ERROR: icon.png was not found in %CD%.
    goto :failed
)

python -m PyInstaller --clean --noconfirm --onefile --windowed ^
    --name "SmoothScrollGUI" ^
    --icon "icon.ico" ^
    --add-data "icon.ico;." ^
    --add-data "icon.png;." ^
    "main.py"
if errorlevel 1 goto :failed

echo.
echo Build complete: %CD%\dist\SmoothScrollGUI.exe
pause
exit /b 0

:failed
echo.
echo Build failed. Review the error above.
pause
exit /b 1
