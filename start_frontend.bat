@echo off
echo ========================================
echo   Starting AI Assistant Frontend
echo ========================================
echo.

REM Check if virtual environment exists
if not exist "venv\" (
    echo Virtual environment not found!
    echo Please run: python -m venv venv
    echo Then: venv\Scripts\activate
    echo Then: pip install -r requirements.txt
    pause
    exit /b 1
)

REM Activate virtual environment
call venv\Scripts\activate

echo Starting frontend...
echo Frontend will open in your browser at: http://localhost:8501
echo.
echo Press Ctrl+C to stop the frontend
echo.

streamlit run frontend_simple.py

pause
