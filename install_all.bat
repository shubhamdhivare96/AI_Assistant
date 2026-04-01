@echo off
echo ========================================
echo   Installing All Required Packages
echo ========================================
echo.

REM Activate virtual environment
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
) else (
    echo Virtual environment not found!
    echo Please create it first: python -m venv venv
    pause
    exit /b 1
)

echo Upgrading pip...
python -m pip install --upgrade pip

echo.
echo Installing core packages...
pip install fastapi uvicorn[standard] pydantic pydantic-settings python-dotenv python-multipart

echo.
echo Installing LLM providers...
pip install google-genai groq openai boto3

echo.
echo Installing embeddings...
pip install sentence-transformers torch

echo.
echo Installing vector database...
pip install qdrant-client

echo.
echo Installing search and ranking...
pip install rank-bm25 faiss-cpu

echo.
echo Installing document processing...
pip install pypdf python-docx Pillow beautifulsoup4 lxml markdown

echo.
echo Installing text processing...
pip install nltk spacy tiktoken

echo.
echo Installing data science...
pip install numpy pandas scikit-learn

echo.
echo Installing HTTP and async...
pip install httpx aiohttp requests

echo.
echo Installing utilities...
pip install python-jose[cryptography] passlib[bcrypt] psutil

echo.
echo Installing frontend...
pip install streamlit plotly

echo.
echo Installing additional dependencies...
pip install pyyaml jinja2

echo.
echo ========================================
echo   Installation Complete!
echo ========================================
echo.
echo Downloading NLP models...
python -m spacy download en_core_web_sm
python -c "import nltk; nltk.download('punkt'); nltk.download('stopwords')"

echo.
echo ========================================
echo   All Done!
echo ========================================
echo.
echo You can now start the backend:
echo   python app/main.py
echo.
pause
