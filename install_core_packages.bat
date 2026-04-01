@echo off
echo Installing core packages for AI Assistant...
echo.

echo Installing FastAPI and Uvicorn...
pip install fastapi uvicorn --quiet

echo Installing LLM providers...
pip install google-genai groq openai --quiet

echo Installing AWS Bedrock...
pip install boto3 --quiet

echo Installing Vector Database...
pip install qdrant-client --quiet

echo Installing Search...
pip install rank-bm25 --quiet

echo Installing Streamlit...
pip install streamlit --quiet

echo.
echo Core packages installed!
echo.
echo To install remaining packages, run:
echo pip install -r requirements.txt
pause
