"""
Servidor simple para servir el widget Business AI Support

Uso:
    python serve_widget.py

Esto servirá el widget en http://localhost:8000/widget/business-ai-widget.js
"""

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import uvicorn

app = FastAPI(title="Business AI Support Widget Server")

# Directorio del widget
WIDGET_DIR = Path(__file__).parent

@app.get("/widget/business-ai-widget.js")
async def serve_widget_js():
    """Sirve el archivo JavaScript del widget."""
    widget_path = WIDGET_DIR / "business-ai-widget.js"
    if widget_path.exists():
        return FileResponse(
            widget_path,
            media_type="application/javascript",
            headers={
                "Access-Control-Allow-Origin": "*",
                "Cache-Control": "public, max-age=3600"
            }
        )
    return {"error": "Widget file not found"}, 404

@app.get("/widget/embed-example.html")
async def serve_example():
    """Sirve la página de ejemplo."""
    example_path = WIDGET_DIR / "embed-example.html"
    if example_path.exists():
        return FileResponse(example_path, media_type="text/html")
    return {"error": "Example file not found"}, 404

@app.get("/widget/quick-start.html")
async def serve_quick_start():
    """Sirve la página de quick start."""
    quick_start_path = WIDGET_DIR / "quick-start.html"
    if quick_start_path.exists():
        return FileResponse(quick_start_path, media_type="text/html")
    return {"error": "Quick start file not found"}, 404

if __name__ == "__main__":
    print("🚀 Servidor de Widget iniciado en http://localhost:8000")
    print("📦 Widget disponible en: http://localhost:8000/widget/business-ai-widget.js")
    print("📄 Ejemplo disponible en: http://localhost:8000/widget/embed-example.html")
    uvicorn.run(app, host="0.0.0.0", port=8000)

