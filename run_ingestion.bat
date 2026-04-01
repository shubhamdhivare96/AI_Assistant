@echo off
echo ================================================================================
echo Python 3.14 Documentation Ingestion
echo ================================================================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8+ and try again
    pause
    exit /b 1
)

echo Step 1: Installing dependencies...
echo --------------------------------------------------------------------------------
python setup_ingestion.py
if errorlevel 1 (
    echo.
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)

echo.
echo.
echo Step 2: Running ingestion...
echo --------------------------------------------------------------------------------
python ingest_docs_simple.py

echo.
echo.
echo ================================================================================
echo Ingestion Complete!
echo ================================================================================
echo Check ingestion.log for details
echo.
pause
