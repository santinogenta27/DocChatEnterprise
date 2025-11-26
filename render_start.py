"""
Render startup script for Gradio app.
Simple direct launch for Render compatibility.
"""
import os

# Get port from environment (Render sets this)
PORT = int(os.environ.get("PORT", 10000))

# Import the Gradio demo
from app import demo

print(f"🚀 Starting DocChat Enterprise on port {PORT}")
print(f"🌐 Binding to 0.0.0.0:{PORT}")

# Launch Gradio directly - this is the simplest and most reliable method
# server_name="0.0.0.0" is REQUIRED for Render to detect the port
demo.queue().launch(
    server_name="0.0.0.0",  # CRITICAL: Must be 0.0.0.0, not 127.0.0.1
    server_port=PORT,        # Use Render's PORT environment variable
    share=False,
    show_api=False,
    inbrowser=False
)

