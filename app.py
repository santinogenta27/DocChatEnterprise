"""
DocChat Enterprise - Main Application
Compatible with Render deployment (uvicorn + /healthz)
"""
import os

# Import demo from chatbot_dashboard
from chatbot_dashboard import demo

# Export demo for render_start.py
__all__ = ['demo']

# Get the underlying FastAPI app from Gradio and add /healthz for Render
app = demo.app

@app.get("/healthz")
def healthz():
    """Health check endpoint required by Render."""
    return {"status": "ok"}

# If running directly, use uvicorn (faster port binding for Render)
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 7860))
    print(f"🚀 Starting DocChat Enterprise on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)

