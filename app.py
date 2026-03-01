"""
DocChat Enterprise - Main Application
Compatible con Render deployment (uvicorn + /healthz)
"""

import os
from fastapi import FastAPI
from chatbot_dashboard import demo  # tu app Gradio

# Crear un FastAPI wrapper
app = FastAPI()

# Health check rápido requerido por Render
@app.get("/healthz")
def healthz():
    return {"status": "ok"}

# Montar tu app Gradio en la raíz
app.mount("/", demo.app)

# Ejecutar con uvicorn si corremos app.py directamente
if __name__ == "__main__":
    import uvicorn
    # Render asigna el puerto dinámicamente vía la variable de entorno PORT
    port = int(os.environ["PORT"])
    print(f"🚀 Starting DocChat Enterprise on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
