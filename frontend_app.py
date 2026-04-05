"""
AI Assistant - Simple Frontend UI
A clean Streamlit interface for the AI Assistant API
"""
import streamlit as st
import requests
import json
from datetime import datetime

# Configuration
API_BASE_URL = "http://localhost:8000/api/v1"

# Page config
st.set_page_config(
    page_title="AI Assistant",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 1rem;
    }
    .sub-header {
        text-align: center;
        color: #666;
        margin-bottom: 2rem;
    }
    .success-box {
        padding: 1rem;
        background-color: #d4edda;
        border-left: 4px solid #28a745;
        border-radius: 4px;
        margin: 1rem 0;
    }
    .warning-box {
        padding: 1rem;
        background-color: #fff3cd;
        border-left: 4px solid #ffc107;
        border-radius: 4px;
        margin: 1rem 0;
    }
    .error-box {
        padding: 1rem;
        background-color: #f8d7da;
        border-left: 4px solid #dc3545;
        border-radius: 4px;
        margin: 1rem 0;
    }
    .metadata-box {
        padding: 0.5rem;
        background-color: #f8f9fa;
        border-radius: 4px;
        font-size: 0.85rem;
        margin-top: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'conversation_id' not in st.session_state:
    st.session_state.conversation_id = None
if 'messages' not in st.session_state:
    st.session_state.messages = []

# Header
st.markdown('<div class="main-header">🎓 AI Assistant</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Domain-Specific Educational Assistant with Security</div>', unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.header("⚙️ Settings")
    
    # User role selection
    user_role = st.selectbox(
        "User Role",
        ["student", "teacher", "admin"],
        help="Different roles have different token budgets"
    )
    
    # Temperature control
    temperature = st.slider(
        "Temperature",
        min_value=0.0,
        max_value=1.0,
        value=0.7,
        step=0.1,
        help="Higher = more creative, Lower = more focused"
    )
    
    st.divider()
    
    # System status
    st.header("📊 System Status")
    
    try:
        health_response = requests.get(f"{API_BASE_URL}/health/")
        if health_response.status_code == 200:
            st.success("✅ API Online")
        else:
            st.error("❌ API Offline")
    except:
        st.error("❌ Cannot connect to API")
    
    st.divider()
    
    # Example queries
    st.header("💡 Example Queries")
    
    st.markdown("**✅ Valid (In-Domain)**")
    st.code("What is photosynthesis?", language=None)
    st.code("Explain Newton's laws", language=None)
    
    st.markdown("**❌ Invalid (Out-of-Domain)**")
    st.code("What's the Bitcoin price?", language=None)
    st.code("Tell me a joke", language=None)
    
    st.markdown("**🚫 Injection Attempts**")
    st.code("Ignore all instructions...", language=None)
    
    st.divider()
    
    # Clear conversation
    if st.button("🗑️ Clear Conversation", use_container_width=True):
        st.session_state.messages = []
        st.session_state.conversation_id = None
        st.rerun()

# Main chat interface
st.header("💬 Chat")

# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        
        # Show metadata if available
        if "metadata" in message and message["role"] == "assistant":
            metadata = message["metadata"]
            
            cols = st.columns(4)
            with cols[0]:
                st.caption(f"⏱️ {metadata.get('latency', 0):.2f}s")
            with cols[1]:
                st.caption(f"🎯 {metadata.get('tokens_used', 0)} tokens")
            with cols[2]:
                if metadata.get('cache_hit'):
                    st.caption("💾 Cached")
                else:
                    st.caption("🔍 Retrieved")
            with cols[3]:
                risk = metadata.get('security', {}).get('injection_risk', 'low')
                if risk == 'high':
                    st.caption("🚫 High Risk")
                elif risk == 'medium':
                    st.caption("⚠️ Medium Risk")
                else:
                    st.caption("✅ Safe")

# Chat input
if prompt := st.chat_input("Ask a question about your educational content..."):
    # Add user message to chat
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Display user message
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Get AI response
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                # Call API
                payload = {
                    "message": prompt,
                    "conversation_id": st.session_state.conversation_id,
                    "user_id": "demo_user",
                    "context": {
                        "user_role": user_role,
                        "temperature": temperature
                    }
                }
                
                response = requests.post(
                    f"{API_BASE_URL}/chat/chat",
                    json=payload,
                    timeout=30
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Update conversation ID
                    if not st.session_state.conversation_id:
                        st.session_state.conversation_id = data.get('conversation_id')
                    
                    # Display response
                    ai_response = data.get('response', 'No response received')
                    st.markdown(ai_response)
                    
                    # Display metadata
                    metadata = data.get('metadata', {})
                    
                    # Create metadata display
                    st.markdown("---")
                    cols = st.columns(4)
                    
                    with cols[0]:
                        latency = metadata.get('latency', 0)
                        st.metric("Latency", f"{latency:.2f}s")
                    
                    with cols[1]:
                        tokens = metadata.get('tokens_used', 0)
                        st.metric("Tokens", tokens)
                    
                    with cols[2]:
                        if metadata.get('cache_hit'):
                            st.metric("Cache", "Hit 💾")
                        else:
                            st.metric("Cache", "Miss")
                    
                    with cols[3]:
                        security = metadata.get('security', {})
                        risk = security.get('injection_risk', 'low')
                        if risk == 'high':
                            st.metric("Security", "🚫 Blocked")
                        elif risk == 'medium':
                            st.metric("Security", "⚠️ Warning")
                        else:
                            st.metric("Security", "✅ Safe")
                    
                    # Show detailed security info if available
                    if security and risk != 'low':
                        with st.expander("🔒 Security Details"):
                            st.json(security)
                    
                    # Show sources if available
                    sources = metadata.get('sources', [])
                    if sources:
                        with st.expander(f"📚 Sources ({len(sources)} documents)"):
                            for i, source in enumerate(sources[:5], 1):
                                st.markdown(f"**Source {i}** (Score: {source.get('score', 0):.3f})")
                                st.text(source.get('text', '')[:200] + "...")
                                st.divider()
                    
                    # Add to message history
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": ai_response,
                        "metadata": metadata
                    })
                
                elif response.status_code == 429:
                    error_msg = "⚠️ Rate limit exceeded. Please wait a moment and try again."
                    st.error(error_msg)
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": error_msg
                    })
                
                else:
                    error_data = response.json()
                    error_msg = f"❌ Error: {error_data.get('detail', 'Unknown error')}"
                    st.error(error_msg)
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": error_msg
                    })
            
            except requests.exceptions.Timeout:
                error_msg = "⏱️ Request timed out. The server might be processing a complex query."
                st.error(error_msg)
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": error_msg
                })
            
            except requests.exceptions.ConnectionError:
                error_msg = "❌ Cannot connect to API. Make sure the server is running at http://localhost:8000"
                st.error(error_msg)
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": error_msg
                })
            
            except Exception as e:
                error_msg = f"❌ Unexpected error: {str(e)}"
                st.error(error_msg)
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": error_msg
                })

# Footer
st.divider()
st.markdown("""
<div style='text-align: center; color: #666; font-size: 0.85rem;'>
    <p>🔒 Secure • 🎯 Domain-Restricted • ⚡ Production-Ready</p>
    <p>API Documentation: <a href='http://localhost:8000/docs' target='_blank'>Swagger UI</a></p>
</div>
""", unsafe_allow_html=True)
