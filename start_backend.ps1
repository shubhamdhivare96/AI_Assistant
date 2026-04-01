# PowerShell script to start backend
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   Starting AI Assistant Backend" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if virtual environment exists
if (-not (Test-Path "venv\Scripts\Activate.ps1")) {
    Write-Host "Virtual environment not found!" -ForegroundColor Red
    Write-Host "Please run: python -m venv venv" -ForegroundColor Yellow
    Write-Host "Then: .\venv\Scripts\Activate.ps1" -ForegroundColor Yellow
    Write-Host "Then: pip install -r requirements.txt" -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

# Activate virtual environment
Write-Host "Activating virtual environment..." -ForegroundColor Green
& ".\venv\Scripts\Activate.ps1"

# Check if .env file exists
if (-not (Test-Path ".env")) {
    Write-Host ".env file not found!" -ForegroundColor Red
    Write-Host "Please copy .env.example to .env and configure it" -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "Starting backend server..." -ForegroundColor Green
Write-Host "Backend will be available at: http://localhost:8000" -ForegroundColor Cyan
Write-Host "API docs at: http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host ""
Write-Host "Press Ctrl+C to stop the server" -ForegroundColor Yellow
Write-Host ""

# Start backend
python app/main.py
