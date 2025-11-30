"""
Servidor API RESTful - Backend RAG para Chatbots Empresariales

Backend RAG que permite a empresas conectar sus chatbots existentes
y usar RAG con su data privada.

Flujo:
1. Cliente pregunta → En el chatbot de la empresa (en su app)
2. Chatbot de la empresa consulta → DocChat Enterprise por API
3. DocChat Enterprise busca → En documentos privados de la empresa
4. DocChat Enterprise responde → Al chatbot de la empresa
5. Chatbot de la empresa muestra → Respuesta al cliente en su app

Uso:
    python api_server.py

Endpoints disponibles:
- POST /api/chatbot/register - Registrar chatbot
- POST /api/chatbot/{chatbot_id}/upload - Subir documentos
- POST /api/chatbot/{chatbot_id}/query - Consultar RAG (PRINCIPAL)
- GET /api/chatbot/{chatbot_id}/info - Info del chatbot
- GET /api/chatbot/list - Listar chatbots
- GET /api/chatbot/health - Health check
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Agregar el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from docchat import AppConfig, load_config
from docchat.chatbot_mode import ChatbotMode
from docchat.chatbot_api import create_chatbot_api

# Cargar configuración
config = load_config()

# Inicializar ChatbotMode
chatbot_mode = ChatbotMode(config)

# Crear aplicación FastAPI
app = FastAPI(
    title="DocChat Enterprise - Backend RAG para Chatbots",
    description="Backend RAG que permite a empresas conectar sus chatbots existentes y usar RAG con su data privada",
    version="1.0.0"
)

# Crear endpoints de chatbot
create_chatbot_api(app, chatbot_mode)

@app.get("/")
async def root():
    """Endpoint raíz con información de la API."""
    return {
        "service": "DocChat Enterprise - Backend RAG para Chatbots",
        "version": "1.0.0",
        "description": "Backend RAG que permite a empresas conectar sus chatbots existentes y usar RAG con su data privada",
        "flow": {
            "1": "Cliente pregunta → En el chatbot de la empresa (en su app)",
            "2": "Chatbot de la empresa consulta → DocChat Enterprise por API",
            "3": "DocChat Enterprise busca → En documentos privados de la empresa",
            "4": "DocChat Enterprise responde → Al chatbot de la empresa",
            "5": "Chatbot de la empresa muestra → Respuesta al cliente en su app"
        },
        "endpoints": {
            "register": "POST /api/chatbot/register",
            "upload": "POST /api/chatbot/{chatbot_id}/upload",
            "query": "POST /api/chatbot/{chatbot_id}/query",
            "info": "GET /api/chatbot/{chatbot_id}/info",
            "list": "GET /api/chatbot/list",
            "health": "GET /api/chatbot/health"
        },
        "documentation": "/docs"
    }

if __name__ == "__main__":
    # Obtener puerto de variable de entorno o usar 8000 por defecto
    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "0.0.0.0")
    
    print(f"🚀 Iniciando Chatbot Mode API en http://{host}:{port}")
    print(f"📚 Documentación disponible en http://{host}:{port}/docs")
    print(f"🔍 Health check: http://{host}:{port}/api/chatbot/health")
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info"
    )
