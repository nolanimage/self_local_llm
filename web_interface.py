#!/usr/bin/env python3
"""
Web Interface for LLM System
Run with: streamlit run web_interface.py
"""
import streamlit as st
import pika
import json
import uuid
import time
from typing import Dict, Any, Optional


class LLMClient:
    """Client for sending requests to LLM via RabbitMQ"""
    
    def __init__(self, 
                 host='localhost',
                 port=5672,
                 user='admin',
                 password='admin123'):
        """Initialize RabbitMQ connection"""
        self.connection = pika.BlockingConnection(
            pika.ConnectionParameters(
                host=host,
                port=port,
                credentials=pika.PlainCredentials(user, password)
            )
        )
        self.channel = self.connection.channel()
        
        # Declare queues
        self.channel.queue_declare(queue='llm_requests', durable=True)
        self.channel.queue_declare(queue='llm_responses', durable=True)
    
    def generate(self, 
                 prompt: str,
                 max_tokens: int = 100,
                 temperature: float = 0.7,
                 timeout: int = 120) -> Optional[Dict[str, Any]]:
        """Send a prompt and get response"""
        request_id = str(uuid.uuid4())
        
        # Send request first
        message = {
            'request_id': request_id,
            'prompt': prompt,
            'max_tokens': max_tokens,
            'temperature': temperature
        }
        
        self.channel.basic_publish(
            exchange='',
            routing_key='llm_requests',
            body=json.dumps(message),
            properties=pika.BasicProperties(delivery_mode=2)
        )
        
        # Use basic_get with frequent polling - more reliable with Streamlit
        start_time = time.time()
        response_data = None
        checked_messages = 0
        
        while (time.time() - start_time) < timeout:
            try:
                method, properties, body = self.channel.basic_get(queue='llm_responses', auto_ack=False)
                
                if method:
                    checked_messages += 1
                    try:
                        data = json.loads(body)
                        resp_id = data.get('request_id', '')
                        
                        # Only process if it's our request
                        if resp_id == request_id:
                            # Filter out old llama3 errors
                            response_text = data.get('response', '')
                            if 'llama3' in response_text.lower() and 'not found' in response_text.lower():
                                # Old error - reject and continue looking
                                self.channel.basic_nack(method.delivery_tag, requeue=False)
                                continue
                            # Valid response!
                            response_data = data
                            self.channel.basic_ack(method.delivery_tag)
                            break
                        else:
                            # Not our message - reject and don't requeue
                            self.channel.basic_nack(method.delivery_tag, requeue=False)
                    except Exception as e:
                        # Invalid message - reject
                        self.channel.basic_nack(method.delivery_tag, requeue=False)
                else:
                    # No message available - wait a bit
                    time.sleep(0.05)  # Reduced wait time for faster response
            except Exception as e:
                # On error, wait and retry
                time.sleep(0.1)
        
        return response_data
    
    def close(self):
        """Close the connection"""
        if self.connection and not self.connection.is_closed:
            self.connection.close()

st.set_page_config(
    page_title="AI Chat Assistant",
    page_icon="✨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for modern design
st.markdown("""
<style>
    .main {
        padding-top: 2rem;
    }
    .stChatMessage {
        padding: 1rem;
        border-radius: 15px;
        margin-bottom: 1rem;
    }
    .stChatMessage[data-testid="user-message"] {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
    }
    .stChatMessage[data-testid="assistant-message"] {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        color: white;
    }
    h1 {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 3rem;
        font-weight: 800;
        margin-bottom: 0.5rem;
    }
    .subtitle {
        color: #666;
        font-size: 1.1rem;
        margin-bottom: 2rem;
    }
    .status-badge {
        display: inline-block;
        padding: 0.3rem 0.8rem;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 600;
        margin: 0.2rem;
    }
    .status-online {
        background: #10b981;
        color: white;
    }
    .status-offline {
        background: #ef4444;
        color: white;
    }
</style>
""", unsafe_allow_html=True)

# Header with gradient
import datetime
version_timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
st.markdown(f"""
<div style='text-align: center; padding: 2rem 0;'>
    <h1>✨ AI Chat Assistant</h1>
    <p class='subtitle'>Powered by Qwen2.5 via RabbitMQ + Ollama with RAG</p>
    <p style='font-size: 0.8rem; color: #999; margin-top: 0.5rem;'>Version: {version_timestamp}</p>
</div>
""", unsafe_allow_html=True)

# Initialize session state
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'client' not in st.session_state:
    try:
        st.session_state.client = LLMClient()
        st.session_state.client_connected = True
    except Exception as e:
        st.session_state.client_connected = False
        st.session_state.client_error = str(e)

# Sidebar for settings
with st.sidebar:
    st.markdown("### ⚙️ Settings")
    st.markdown("---")
    
    max_tokens = st.slider("Max Tokens", 50, 500, 250, 25, help="Maximum number of tokens to generate (higher = longer responses)")
    temperature = st.slider("Temperature", 0.0, 2.0, 0.7, 0.1, help="Controls randomness (0 = deterministic, 2 = creative)")
    timeout = st.slider("Timeout (seconds)", 30, 180, 120, 10, help="Maximum wait time for response (longer responses need more time)")
    
    st.markdown("---")
    st.markdown("### 📊 System Status")
    
    # Status indicators
    col1, col2 = st.columns(2)
    with col1:
        if st.session_state.client_connected:
            st.markdown('<span class="status-badge status-online">🟢 Online</span>', unsafe_allow_html=True)
        else:
            st.markdown('<span class="status-badge status-offline">🔴 Offline</span>', unsafe_allow_html=True)
    
    with col2:
        if st.session_state.client_connected:
            st.markdown('<span class="status-badge" style="background: #3b82f6; color: white;">RabbitMQ ✓</span>', unsafe_allow_html=True)
    
    if not st.session_state.client_connected:
        st.error(f"Connection Error: {st.session_state.client_error}")
    
    st.markdown("---")
    if st.button("🔄 Refresh Connection", use_container_width=True):
        try:
            if 'client' in st.session_state:
                st.session_state.client.close()
            st.session_state.client = LLMClient()
            st.session_state.client_connected = True
            st.success("Connected!")
            st.rerun()
        except Exception as e:
            st.session_state.client_connected = False
            st.session_state.client_error = str(e)
            st.error(f"Connection failed: {e}")
    
    st.markdown("---")
    st.markdown("### ℹ️ About")
    st.markdown("""
    **Model:** Qwen2.5:1.5b  
    **Backend:** RabbitMQ + Ollama  
    **RAG:** BAAI/bge-m3 with Hybrid Search & Reranking
    """)

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if "metadata" in message:
            with st.expander("📋 Details"):
                st.json(message["metadata"])

# Chat input
if prompt := st.chat_input("Type your message here..."):
    if not st.session_state.client_connected:
        st.error("Not connected to RabbitMQ. Please check the connection in the sidebar.")
        st.stop()
    
    # Add user message to chat
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Get response
    with st.chat_message("assistant"):
        try:
            # Use placeholder to show progress
            placeholder = st.empty()
            placeholder.info("🤔 Processing your request...")
            
            start_time = time.time()
            response = st.session_state.client.generate(
                prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                timeout=timeout,
                use_rag=True  # Enable RAG by default
            )
            elapsed_time = time.time() - start_time
            
            # Clear placeholder
            placeholder.empty()
            
            if response:
                if response.get("status") == "success":
                    response_text = response.get("response", "No response received")
                    st.markdown(response_text)
                    
                    # Add metadata
                    metadata = {
                        "request_id": response.get("request_id"),
                        "status": response.get("status"),
                        "response_time": f"{elapsed_time:.2f}s",
                        "max_tokens": max_tokens,
                        "temperature": temperature
                    }
                    
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": response_text,
                        "metadata": metadata
                    })
                    
                    with st.expander("📋 Details"):
                        st.json(metadata)
                else:
                    # Response received but status is not success
                    error_msg = response.get("response", "Unknown error")
                    st.error(f"Error: {error_msg}")
                    if response.get("request_id"):
                        with st.expander("📋 Details"):
                            st.json(response)
            else:
                # No response received - timeout or connection issue
                st.error("❌ No response received. Possible causes:")
                st.markdown("""
                - Request timed out (try increasing timeout in settings)
                - Worker is busy processing other requests
                - Connection issue with RabbitMQ
                
                **Try:** Refresh the page and try again with a longer timeout.
                """)
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": "❌ No response received. Please try again."
                })
        except Exception as e:
            error_msg = f"Error: {str(e)}"
            st.error(error_msg)
            st.session_state.messages.append({
                "role": "assistant",
                "content": error_msg
            })

# Clear chat button with better styling
col1, col2, col3 = st.columns([1, 1, 1])
with col2:
    if st.button("🗑️ Clear Chat History", use_container_width=True, type="secondary"):
        st.session_state.messages = []
        st.rerun()

# Footer with modern design
st.markdown("---")
st.markdown("""
<div style='text-align: center; padding: 1rem; color: #666; font-size: 0.9rem;'>
    <p>🚀 <strong>System Architecture:</strong> RabbitMQ → Worker → Ollama (Metal GPU)</p>
    <p>💡 Powered by <strong>Qwen2.5</strong> • Fast & Efficient AI with RAG</p>
</div>
""", unsafe_allow_html=True)
