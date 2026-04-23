@echo off
cd /d "%~dp0"
where python >nul 2>&1 || (echo Python not found. Please install Python 3.8+. && pause & exit /b 1)
python -c "import flask" >nul 2>&1 || (echo Installing Flask... && pip install -r requirements.txt)
echo.
echo Starting Food Diary...
echo Open http://localhost:5000 in your browser
echo Press Ctrl+C to stop.
echo.
python app.py
pause
