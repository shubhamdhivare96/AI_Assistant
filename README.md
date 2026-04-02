# AI RAG Assistant

A scalable Retrieval-Augmented Generation (RAG) backend utilizing a highly resilient 3-tier Large Language Model (LLM) fallback architecture and a hybrid vector search using Qdrant.

## Key Features
*   **3-Tier LLM Fallback (Zero Downtime):** Route failures gracefully through Google Gemini (Primary API) → Groq (Tier 2 fast fallback) → AWS Bedrock Nova Pro (Tier 3 enterprise fallback) whenever quota limits or service outages occur.
*   **Vector Database Integration:** Implements Qdrant for storing and searching dense vectors.
*   **Hybrid Search Fallback:** Automatically switches to pure vector search if BM25 text keyword search is uninitialized, guaranteeing context retrieval.
*   **Session Management & Token Optimization:** Accurately fits top retrieved documents into token budget without surpassing context window.
*   **Domain Specific Constraint:** Strictly adheres to domain instruction in `.env`, politely declining out-of-domain answers instead of hallucinating.

## Prerequisites
* Python 3.10+
* Qdrant DB Instance (API Key + Cloud URL)
* API Keys for LLM Providers (Google GenAI, Groq, AWS Credentials)

## Installation & Usage
1. Clone the repository.
2. Run `python -m venv venv` and activate it (e.g. `venv\Scripts\activate` on Windows).
3. Install dependencies: `pip install -r requirements.txt`.
4. Copy `.env.example` to `.env` and fill in your secrets.
5. Ingest data using the ingestion script (e.g., `python ingest_python_docs.py`).
6. Start the API with `python app/main.py`.
7. (Optional) Run Streamlit Frontend testing: `streamlit run frontend_simple.py`.

## Directory Structure
*   `app/core/`: Application settings, connections, and Circuit Breaker logic over external calls.
*   `app/api/`: FastAPI routers and endpoints.
*   `app/services/`: LLM orchestration, Qdrant search, Token management.
*   `app/schemas/`: Pydantic validation boundaries.

## Warning: Never commit `.env`!
Ensure your `.gitignore` is active and successfully ignoring the `.env` file before pushing code.
