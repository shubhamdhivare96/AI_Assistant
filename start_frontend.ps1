# PowerShell script to start frontend
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   Starting AI Assistant Frontend" -ForegroundColor Cyan
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

Write-Host "Starting frontend..." -ForegroundColor Green
Write-Host "Frontend will open in your browser at: http://localhost:8501" -ForegroundColor Cyan
Write-Host ""
Write-Host "Press Ctrl+C to stop the frontend" -ForegroundColor Yellow
Write-Host ""

# Start frontend
streamlit run frontend_simple.py
