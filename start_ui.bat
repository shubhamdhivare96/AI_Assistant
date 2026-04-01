@echo off
REM Start the AI Assistant UI (Windows)

echo 🎓 Starting AI Assistant Frontend...
echo.
echo Make sure the API server is running first:
echo   uvicorn app.main:app --reload
echo.
echo Starting Streamlit UI...
echo.

REM Start simple UI
streamlit run frontend_app.py --server.port 8501

REM Or start advanced UI with:
REM streamlit run frontend_advanced.py --server.port 8501
