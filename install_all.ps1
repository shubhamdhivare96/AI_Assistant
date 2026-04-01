# PowerShell script to install all required packages
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   Installing All Required Packages" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Activate virtual environment
if (Test-Path "venv\Scripts\Activate.ps1") {
    Write-Host "Activating virtual environment..." -ForegroundColor Green
    & ".\venv\Scripts\Activate.ps1"
} else {
    Write-Host "Virtual environment not found!" -ForegroundColor Red
    Write-Host "Please create it first: python -m venv venv" -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "Upgrading pip..." -ForegroundColor Green
python -m pip install --upgrade pip

Write-Host ""
Write-Host "Installing core packages..." -ForegroundColor Green
pip install fastapi uvicorn[standard] pydantic pydantic-settings python-dotenv python-multipart

Write-Host ""
Write-Host "Installing LLM providers..." -ForegroundColor Green
pip install google-genai groq openai boto3

Write-Host ""
Write-Host "Installing embeddings..." -ForegroundColor Green
pip install sentence-transformers torch

Write-Host ""
Write-Host "Installing vector database..." -ForegroundColor Green
pip install qdrant-client

Write-Host ""
Write-Host "Installing search and ranking..." -ForegroundColor Green
pip install rank-bm25 faiss-cpu

Write-Host ""
Write-Host "Installing document processing..." -ForegroundColor Green
pip install pypdf python-docx Pillow beautifulsoup4 lxml markdown

Write-Host ""
Write-Host "Installing text processing..." -ForegroundColor Green
pip install nltk spacy tiktoken

Write-Host ""
Write-Host "Installing data science..." -ForegroundColor Green
pip install numpy pandas scikit-learn

Write-Host ""
Write-Host "Installing HTTP and async..." -ForegroundColor Green
pip install httpx aiohttp requests

Write-Host ""
Write-Host "Installing utilities..." -ForegroundColor Green
pip install python-jose[cryptography] passlib[bcrypt] psutil

Write-Host ""
Write-Host "Installing frontend..." -ForegroundColor Green
pip install streamlit plotly

Write-Host ""
Write-Host "Installing additional dependencies..." -ForegroundColor Green
pip install pyyaml jinja2

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   Installation Complete!" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Downloading NLP models..." -ForegroundColor Green
python -m spacy download en_core_web_sm
python -c "import nltk; nltk.download('punkt'); nltk.download('stopwords')"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   All Done!" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "You can now start the backend:" -ForegroundColor Green
Write-Host "  python app/main.py" -ForegroundColor Yellow
Write-Host ""
