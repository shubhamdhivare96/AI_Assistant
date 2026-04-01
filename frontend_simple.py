"""
AI Assistant - Simple Chat Interface
Clean chat interface without RBAC or complex features
"""
import streamlit as st
import requests
import json
from datetime import datetime
import time

# Configuration
API_BASE_URL = "http://localhost:8000/api/v1"

# Page config
st.set_page_config(
    page_title="AI Assistant",
    page_icon="🤖",
    layout="centered"
)

# Custom CSS for clean chat interface
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        text-align: center;
        color: #666;
        margin-bottom: 2rem;
        font-size: 1rem;
    }
    .stChatMessage {
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
    }
    .metric-container {
        background-color: #f8f9fa;
        padding: 0.5rem;
        border-radius: 0.3rem;
        margin-top: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'conversation_id' not in st.session_state:
    st.session_state.conversation_id = None

# Header
st.markdown('<div class="main-header">🤖 AI Assistant</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Ask questions about your knowledge base</div>', unsafe_allow_html=True)

# System status indicator
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    try:
        health_response = requests.get(f"http://localhost:8000/health", timeout=2)
        if health_response.status_code == 200:
            st.success("✅ System Online", icon="✅")
        else:
            st.error("❌ System Offline", icon="❌")
    except:
        st.error("❌ Cannot connect to backend. Make sure it's running on port 8000", icon="❌")

st.divider()

# Clear chat button
col1, col2, col3 = st.columns([1, 1, 1])
with col2:
    if st.button("🗑️ Clear Chat", use_container_width=True):
        st.session_state.messages = []
        st.session_state.conversation_id = None
        st.rerun()

# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        
        # Show metadata for assistant messages
        if message["role"] == "assistant" and "metadata" in message:
            metadata = message["metadata"]
            
            # Show metrics in a compact way
            cols = st.columns(3)
            with cols[0]:
                st.caption(f"⏱️ {metadata.get('latency', 0):.2f}s")
            with cols[1]:
                st.caption(f"🎯 {metadata.get('tokens_used', 0)} tokens")
            with cols[2]:
                if metadata.get('cache_hit'):
                    st.caption("💾 Cached")
                else:
                    st.caption("🔍 Retrieved")
            
            # Show sources if available
            sources = metadata.get('sources', [])
            if sources:
                with st.expander(f"📚 View {len(sources)} source(s)"):
                    for i, source in enumerate(sources[:3], 1):
                        st.markdown(f"**Source {i}** (Relevance: {source.get('score', 0):.2f})")
                        st.text(source.get('text', '')[:150] + "...")
                        if i < len(sources[:3]):
                            st.divider()

# Chat input
if prompt := st.chat_input("Type your question here..."):
    # Add user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Display user message
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Get AI response
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        
        with st.spinner("Thinking..."):
            try:
                start_time = time.time()
                
                # Call API
                payload = {
                    "message": prompt,
                    "conversation_id": st.session_state.conversation_id,
                    "user_id": "demo_user"
                }
                
                response = requests.post(
                    f"{API_BASE_URL}/chat/chat",
                    json=payload,
                    timeout=30
                )
                
                elapsed_time = time.time() - start_time
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Update conversation ID
                    if not st.session_state.conversation_id:
                        st.session_state.conversation_id = data.get('conversation_id')
                    
                    # Get response text
                    ai_response = data.get('response', 'No response received')
                    
                    # Display response
                    message_placeholder.markdown(ai_response)
                    
                    # Get metadata
                    metadata = data.get('metadata', {})
                    metadata['latency'] = elapsed_time
                    
                    # Show metrics
                    cols = st.columns(3)
                    with cols[0]:
                        st.caption(f"⏱️ {elapsed_time:.2f}s")
                    with cols[1]:
                        st.caption(f"🎯 {metadata.get('tokens_used', 0)} tokens")
                    with cols[2]:
                        if metadata.get('cache_hit'):
                            st.caption("💾 Cached")
                        else:
                            st.caption("🔍 Retrieved")
                    
                    # Show sources if available
                    sources = metadata.get('sources', [])
                    if sources:
                        with st.expander(f"📚 View {len(sources)} source(s)"):
                            for i, source in enumerate(sources[:3], 1):
                                st.markdown(f"**Source {i}** (Relevance: {source.get('score', 0):.2f})")
                                st.text(source.get('text', '')[:150] + "...")
                                if i < len(sources[:3]):
                                    st.divider()
                    
                    # Add to history
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": ai_response,
                        "metadata": metadata
                    })
                
                elif response.status_code == 403:
                    # Security block (prompt injection or out-of-domain)
                    error_data = response.json()
                    error_msg = f"🚫 {error_data.get('detail', 'Request blocked by security')}"
                    message_placeholder.error(error_msg)
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": error_msg
                    })
                
                else:
                    # Other errors
                    try:
                        error_data = response.json()
                        error_msg = f"❌ Error: {error_data.get('detail', 'Unknown error')}"
                    except:
                        error_msg = f"❌ Error: {response.text}"
                    
                    message_placeholder.error(error_msg)
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": error_msg
                    })
            
            except requests.exceptions.Timeout:
                error_msg = "⏱️ Request timed out. Please try again."
                message_placeholder.error(error_msg)
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": error_msg
                })
            
            except requests.exceptions.ConnectionError:
                error_msg = "❌ Cannot connect to backend. Make sure it's running:\n\n`python app/main.py`"
                message_placeholder.error(error_msg)
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": error_msg
                })
            
            except Exception as e:
                error_msg = f"❌ Unexpected error: {str(e)}"
                message_placeholder.error(error_msg)
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": error_msg
                })

# Footer
st.divider()
st.markdown("""
<div style='text-align: center; color: #888; font-size: 0.85rem; padding: 1rem;'>
    <p>🔒 Secure • 🎯 Domain-Restricted • ⚡ Fast</p>
    <p style='font-size: 0.75rem;'>
        API Docs: <a href='http://localhost:8000/docs' target='_blank'>localhost:8000/docs</a>
    </p>
</div>
""", unsafe_allow_html=True)
