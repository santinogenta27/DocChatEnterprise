"""
Customer Service 24/7 - Standalone App for Hugging Face Spaces
Production-ready autonomous resolution agent
"""
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dotenv import load_dotenv
load_dotenv()

from docchat.customer_service_24_7 import CustomerService247Mode
import gradio as gr

# Initialize service
print("🔄 Inicializando Customer Service 24/7...")
try:
    # Create minimal config
    class Config:
        memory_dir = "./data"
    
    config = Config()
    service = CustomerService247Mode(config, provider="grok")
    
    if service.agent is None:
        print("⚠️ Agent no inicializado, usando fallback")
        raise Exception("Agent initialization failed")
    
    print("✅ Customer Service 24/7 inicializado")
    
    # Get Gradio interface
    interface = service.get_gradio_interface()
    
    # Launch
    if __name__ == "__main__":
        interface.launch(
            server_name="0.0.0.0",
            server_port=7860,
            share=False
        )
        
except Exception as e:
    print(f"❌ Error inicializando: {e}")
    
    # Fallback: Create simple error interface
    def error_fn(message, history):
        return "I apologize, but the service is currently unavailable. Please try again later or contact support."
    
    interface = gr.ChatInterface(
        fn=error_fn,
        title="Customer Service 24/7",
        description="Service temporarily unavailable"
    )
    interface.launch()
