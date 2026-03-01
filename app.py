"""
DocChat Enterprise - Main Application
Compatible with Render deployment (uvicorn + /healthz)
"""
import os
from chatbot_dashboard import demo  # tu app Gradio

# Export demo for render_start.py
__all__ = ['demo']

# Get the underlying FastAPI app from Gradio
app = demo.app

# Health check endpoint required by Render
@app.get("/healthz")
def healthz():
    return {"status": "ok"}

# Run with uvicorn if script is executed directly
if __name__ == "__main__":
    import uvicorn
    # Render asigna el puerto en la variable de entorno PORT
    port = int(os.environ.get("PORT", 7860))
    print(f"🚀 Starting DocChat Enterprise on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
