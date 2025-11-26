"""
Render startup script for Gradio app.
This script launches Gradio on the port specified by Render.
"""
import os
import sys

# Get port from environment (Render sets this)
PORT = int(os.environ.get("PORT", 10000))

# Import and launch the Gradio app
from app import demo

print(f"🚀 Starting DocChat Enterprise on port {PORT}")
demo.queue().launch(
    server_name="0.0.0.0",
    server_port=PORT,
    share=False,
    show_api=False
)

