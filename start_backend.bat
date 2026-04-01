@echo off
echo ========================================
echo   Starting AI Assistant Backend
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

REM Check if .env file exists
if not exist ".env" (
    echo .env file not found!
    echo Please copy .env.example to .env and configure it
    pause
    exit /b 1
)

echo Starting backend server...
echo Backend will be available at: http://localhost:8000
echo API docs at: http://localhost:8000/docs
echo.
echo Press Ctrl+C to stop the server
echo.

python app/main.py

pause
