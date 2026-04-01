#!/usr/bin/env python3
"""
Configuration Setup Script
Helps verify that all required API keys and services are configured
"""
import os
import sys
from pathlib import Path

def check_env_file():
    """Check if .env file exists"""
    if not Path('.env').exists():
        print("❌ .env file not found!")
        print("   Copy .env.example to .env and update with your API keys")
        return False
    print("✅ .env file found")
    return True

def check_api_keys():
    """Check if required API keys are set"""
    from dotenv import load_dotenv
    load_dotenv()
    
    required_keys = {
        'GOOGLE_API_KEY': 'Google Gemini (Primary LLM)',
        'GROQ_API_KEY': 'Groq (Fallback LLM)',
        'AWS_ACCESS_KEY_ID': 'AWS Bedrock (Nova Embeddings)',
        'AWS_SECRET_ACCESS_KEY': 'AWS Bedrock (Nova Embeddings)',
        'QDRANT_URL': 'Qdrant Vector Database',
        'DATABASE_URL': 'PostgreSQL Database'
    }
    
    missing = []
    for key, description in required_keys.items():
        value = os.getenv(key)
        if not value or value.startswith('your_'):
            print(f"❌ {key} not set ({description})")
            missing.append(key)
        else:
            print(f"✅ {key} configured")
    
    return len(missing) == 0

def check_dependencies():
    """Check if required Python packages are installed"""
    required_packages = [
        ('google.generativeai', 'google-generativeai'),
        ('groq', 'groq'),
        ('boto3', 'boto3'),
        ('qdrant_client', 'qdrant-client'),
        ('sentence_transformers', 'sentence-transformers'),
        ('fastapi', 'fastapi'),
        ('sqlalchemy', 'sqlalchemy')
    ]
    
    missing = []
    for module, package in required_packages:
        try:
            __import__(module)
            print(f"✅ {package} installed")
        except ImportError:
            print(f"❌ {package} not installed")
            missing.append(package)
    
    if missing:
        print(f"\n📦 Install missing packages:")
        print(f"   pip install {' '.join(missing)}")
        return False
    
    return True

def test_llm_connection():
    """Test LLM connection"""
    try:
        from app.services.llm_service import LLMService
        print("\n🔄 Testing LLM service initialization...")
        llm = LLMService()
        print("✅ LLM service initialized successfully")
        return True
    except Exception as e:
        print(f"❌ LLM service failed: {str(e)}")
        return False

def test_rag_connection():
    """Test RAG service connection"""
    try:
        from app.services.rag_service import RAGService
        print("\n🔄 Testing RAG service initialization...")
        rag = RAGService()
        print("✅ RAG service initialized successfully")
        return True
    except Exception as e:
        print(f"❌ RAG service failed: {str(e)}")
        return False

def main():
    """Main setup verification"""
    print("=" * 60)
    print("AI ASSISTANT CONFIGURATION SETUP")
    print("=" * 60)
    
    print("\n1️⃣  Checking .env file...")
    if not check_env_file():
        sys.exit(1)
    
    print("\n2️⃣  Checking API keys...")
    if not check_api_keys():
        print("\n⚠️  Some API keys are missing. Update .env file with your keys.")
        print("\n📝 Get your API keys from:")
        print("   • Google Gemini: https://makersuite.google.com/app/apikey")
        print("   • Groq: https://console.groq.com/keys")
        print("   • AWS: AWS IAM Console (requires bedrock:InvokeModel permission)")
        print("   • Qdrant: https://cloud.qdrant.io/ (or use local)")
        sys.exit(1)
    
    print("\n3️⃣  Checking dependencies...")
    if not check_dependencies():
        sys.exit(1)
    
    print("\n4️⃣  Testing service connections...")
    llm_ok = test_llm_connection()
    rag_ok = test_rag_connection()
    
    print("\n" + "=" * 60)
    if llm_ok and rag_ok:
        print("✅ ALL CHECKS PASSED!")
        print("=" * 60)
        print("\n🚀 You're ready to start the server:")
        print("   uvicorn app.main:app --reload")
        print("\n📚 API Documentation will be available at:")
        print("   http://localhost:8000/docs")
    else:
        print("⚠️  SOME CHECKS FAILED")
        print("=" * 60)
        print("\n🔧 Fix the issues above and run this script again.")
        sys.exit(1)

if __name__ == "__main__":
    main()
