@echo off
cd /d "%~dp0"

echo Checking dependencies...
python -c "import flask" >nul 2>&1 || pip install -r requirements.txt
python -c "import PyInstaller" >nul 2>&1 || pip install pyinstaller

echo.
echo Building food_diary.exe...
pyinstaller food_diary.spec --clean --noconfirm

if exist dist\food_diary.exe (
    echo.
    echo ============================================================
    echo  Build successful!
    echo  Executable: %~dp0dist\food_diary.exe
    echo.
    echo  Copy food_diary.exe to any Windows machine and run it.
    echo  The database (food_diary.db) is created in the same folder
    echo  as the .exe on first launch.
    echo ============================================================
) else (
    echo.
    echo Build FAILED. Check the output above for errors.
)
echo.
pause
