# RAG Assistant Architecture

This system implements an Advanced Retrieval-Augmented Generation (RAG) backend utilizing FastAPI for service orchestration.

## 1. Request Flow

1.  **Frontend → FastAPI:** Client (e.g., Streamlit) sends a chat query.
2.  **Adaptive Routing:** Complexity analysis dictates whether the query demands deep retrieval or simple lookups.
3.  **Reformulation:** The original query is transformed to match vector space embeddings (e.g., removing ambiguity or using conversation history).
4.  **Hybrid RAG Search:**
    *   **Vector Search:** Text query is embedded into a dense vector via `sentence-transformers` and queried against Qdrant.
    *   **BM25 (Sparse) Search:** If instantiated during server start, token frequencies are matched against the corpus to complement vector matching.
    *   **Score Fusion:** Dense and sparse matches are combined and top K documents are reranked.
5.  **Context Optimization:** Extracted text is heavily truncated/formatted based on LLM token budgets to prevent window explosion.
6.  **3-Tier LLM Generation:**
    *   The prompt + context is dispatched to the LLM.
    *   **Tier 1 (Gemini):** Fast and accurate. If `429 Too Many Requests` or `Open Circuit Error` hits:
    *   **Tier 2 (Groq):** Lightning-fast Llama-3 based API.
    *   **Tier 3 (AWS Nova Pro):** Amazon Bedrock Converse API for absolute resilience.
7.  **Response Format:** The sanitized output string bounds are pushed back to the client.

## 2. Infrastructure
*   **Vector Database:** Qdrant Cloud (Cosine distance, 384/1024 dimensional embedding limits map to configured model).
*   **Models:** 
    *   Embeddings: `all-MiniLM-L6-v2` (Fallback) or `amazon.nova-2-multimodal-embeddings` (Primary).
    *   LLMs: `gemini-2.0-flash`, `llama-3.3-70b-versatile`, `amazon.nova-pro-v1:0`.
*   **Resilience (Circuit Breaker):** Custom decorators track error states (`llm_breaker`, `groq_breaker`, `nova_breaker`). Rate limits dynamically sidestep the threshold penalty.

## 3. Strict Domain Specificity 
Any generic questions are actively intercepted and declined using the `DOMAIN_DESCRIPTION` instructions pre-injected into the AI's internal system prompt layout.
