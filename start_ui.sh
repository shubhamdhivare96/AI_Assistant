#!/bin/bash
# Start the AI Assistant UI

echo "🎓 Starting AI Assistant Frontend..."
echo ""
echo "Make sure the API server is running first:"
echo "  uvicorn app.main:app --reload"
echo ""
echo "Starting Streamlit UI..."
echo ""

# Start simple UI
streamlit run frontend_app.py --server.port 8501

# Or start advanced UI with:
# streamlit run frontend_advanced.py --server.port 8501
