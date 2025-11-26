"""
Render startup script for Gradio app.
Uses uvicorn to run Gradio's FastAPI app for better Render compatibility.
"""
import os
import sys
import uvicorn

# Get port from environment (Render sets this)
PORT = int(os.environ.get("PORT", 10000))

# Import the Gradio demo
from app import demo

# Queue the demo to prepare it
demo.queue()

# Get the FastAPI app from Gradio
# In Gradio 6.0+, the app is available after queue()
if hasattr(demo, 'app'):
    app = demo.app
elif hasattr(demo, '_queue') and hasattr(demo._queue, 'app'):
    app = demo._queue.app
else:
    # Fallback: launch and get app
    # But we'll use uvicorn instead
    print("⚠️  Could not get FastAPI app directly, using launch method")
    demo.launch(server_name="0.0.0.0", server_port=PORT, share=False, show_api=False, prevent_thread_lock=True)
    app = demo.app if hasattr(demo, 'app') else None

if app:
    print(f"🚀 Starting DocChat Enterprise on port {PORT}")
    print(f"🌐 Server will be available at http://0.0.0.0:{PORT}")
    # Run with uvicorn (more reliable for Render)
    uvicorn.run(app, host="0.0.0.0", port=PORT, log_level="info")
else:
    # Fallback: use Gradio's launch directly
    print(f"🚀 Starting DocChat Enterprise on port {PORT} (using Gradio launch)")
    demo.launch(
        server_name="0.0.0.0",
        server_port=PORT,
        share=False,
        show_api=False
    )

