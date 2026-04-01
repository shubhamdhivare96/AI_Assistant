@echo off
echo ========================================
echo   Testing AI Assistant Backend
echo ========================================
echo.

REM Check if virtual environment exists
if not exist "venv\" (
    echo Virtual environment not found!
    echo Please run: python -m venv venv
    pause
    exit /b 1
)

REM Activate virtual environment
call venv\Scripts\activate

echo Running system tests...
echo.

python test_system.py

echo.
pause
