"""
Render entry point for Gradio app.
Gradio needs to be launched to create the FastAPI app.
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Get port from environment (Render sets this)
PORT = int(os.environ.get("PORT", 10000))

try:
    # Import the Gradio demo
    from app import demo
    
    # Launch Gradio in a way that exposes the FastAPI app
    # We need to launch it but not block, so we get the app object
    # For Gradio 6.0+, we can access the app after queue() is called
    demo.queue()
    
    # Get the FastAPI app from Gradio
    # In Gradio 6.0+, the app is available via demo.app after queue()
    if hasattr(demo, 'app'):
        app = demo.app
    else:
        # Try to get it from the queue
        if hasattr(demo, '_queue') and hasattr(demo._queue, 'app'):
            app = demo._queue.app
        else:
            # Launch and get the app
            # This is a workaround: we'll launch on the correct port
            # But uvicorn will handle the actual serving
            import gradio as gr
            # Create app by launching (but we'll override with uvicorn)
            demo.launch(server_name="0.0.0.0", server_port=PORT, share=False, show_api=False, prevent_thread_lock=True)
            app = demo.app if hasattr(demo, 'app') else demo
    
except Exception as e:
    # Fallback: create a simple error handler
    from fastapi import FastAPI
    import traceback
    app = FastAPI()
    
    @app.get("/")
    def error():
        return {
            "error": "Failed to load Gradio app",
            "message": str(e),
            "traceback": traceback.format_exc()
        }

