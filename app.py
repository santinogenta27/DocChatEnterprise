"""
DocChat Enterprise - Main Application
Compatible with Render deployment
"""
import os
import gradio as gr

# Import demo from chatbot_dashboard
from chatbot_dashboard import demo

# Export demo for render_start.py
__all__ = ['demo']

# If running directly (not via render_start.py), launch with Render-compatible settings
if __name__ == "__main__":
    # Get port from environment (Render sets this)
    port = int(os.environ.get("PORT", 7860))
    
    print(f"🚀 Starting DocChat Enterprise on port {port}")
    demo.queue().launch(
        server_name="0.0.0.0",  # CRITICAL: Must be 0.0.0.0 for Render
        server_port=port,        # Use Render's PORT environment variable
        share=False,
        show_api=False,
        inbrowser=False
    )

