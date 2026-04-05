"""
AI Assistant - Streaming Frontend UI
A modern Streamlit interface with full SSE streaming support
"""
import streamlit as st
import requests
import json
import time
from datetime import datetime

# Configuration
API_BASE_URL = "http://localhost:8000/api/v1"

# Page config
st.set_page_config(
    page_title="AI Assistant | Streaming",
    page_icon="⚡",
    layout="centered"
)

st.title("⚡ AI Assistant (Streaming)")
st.markdown("---")

# Initialize session state
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'conversation_id' not in st.session_state:
    st.session_state.conversation_id = None

# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat input
if prompt := st.chat_input("Ask me something..."):
    # Add user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Stream AI response
    with st.chat_message("assistant"):
        placeholder = st.empty()
        full_response = ""
        
        try:
            payload = {
                "message": prompt,
                "conversation_id": st.session_state.conversation_id,
                "user_id": "streaming_user",
                "stream": True # Enable SSE
            }
            
            with requests.post(
                f"{API_BASE_URL}/chat/chat",
                json=payload,
                stream=True,
                timeout=60
            ) as response:
                if response.status_code == 200:
                    for line in response.iter_lines():
                        if line:
                            decoded_line = line.decode('utf-8')
                            if decoded_line.startswith('data: '):
                                data = json.loads(decoded_line[6:])
                                chunk = data.get('chunk', '')
                                full_response += chunk
                                placeholder.markdown(full_response + "▌")
                                
                    placeholder.markdown(full_response)
                    
                    # Update message history
                    st.session_state.messages.append({
                        "role": "assistant", 
                        "content": full_response
                    })
                    
                    # Note: We can't easily get the metadata (conv_id) from the SSE stream 
                    # unless we include it in the stream chunks or send a final metadata chunk.
                    # Our current backend process_chat_stream doesn't send metadata yet.
                else:
                    st.error(f"Error: {response.status_code}")
        except Exception as e:
            st.error(f"Connection Error: {str(e)}")

# Sidebar
with st.sidebar:
    st.header("Status")
    try:
        r = requests.get(f"{API_BASE_URL}/health/")
        if r.status_code == 200:
            st.success("API Online")
        else:
            st.error("API Issues")
    except:
        st.error("API Offline")
    
    if st.button("Clear Chat"):
        st.session_state.messages = []
        st.session_state.conversation_id = None
        st.rerun()
