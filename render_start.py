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
print(f"🌐 Server will be available at http://0.0.0.0:{PORT}")

# Launch Gradio with explicit configuration for Render
# prevent_thread_lock=False ensures the server runs in the main thread
# which helps Render detect the port
demo.queue().launch(
    server_name="0.0.0.0",  # Must be 0.0.0.0 for Render
    server_port=PORT,        # Use Render's PORT variable
    share=False,
    show_api=False,
    prevent_thread_lock=False  # Keep in main thread so Render can detect port
)

