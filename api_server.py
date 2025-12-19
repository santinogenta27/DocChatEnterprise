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

# FIX PARA WINDOWS: Configurar codificación UTF-8 para evitar errores con emojis
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except AttributeError:
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    os.environ["PYTHONIOENCODING"] = "utf-8"

# Agregar el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from docchat import AppConfig, load_config
from docchat.chatbot_mode import ChatbotMode
from docchat.chatbot_api import create_chatbot_api
from docchat.deep_research_api import create_deep_research_api

# Cargar configuración
config = load_config()

# Inicializar modos principales
chatbot_mode = ChatbotMode(config)

# Inicializar Business AI Omnicanal (para widget embeddable)
business_ai_mode = None
try:
    from docchat.business_ai_omnicanal import BusinessAIMode
    business_ai_mode = BusinessAIMode(config=config)
    print("✅ Business AI Omnicanal inicializado para widget embeddable")
except Exception as e:
    print(f"⚠️ Business AI Omnicanal no disponible: {e}")

# Crear aplicación FastAPI
app = FastAPI(
    title="DocChat Enterprise - Backend RAG + Deep Research + Business AI Widget",
    description=(
        "Backend Enterprise que expone:\n"
        "- Modo Chatbot (RAG sobre data privada)\n"
        "- Modo Deep Research (multi-agente, inspirado en Enterprise Deep Research)\n"
        "- Business AI Omnicanal Widget (chatbot embeddable para websites)"
    ),
    version="1.2.0",
)

# CORS middleware para permitir requests desde cualquier dominio (necesario para widget)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, especifica dominios permitidos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Crear endpoints de chatbot (modo existente)
create_chatbot_api(app, chatbot_mode)

# Crear endpoints de Deep Research (nuevo modo)
create_deep_research_api(app, config)

# Endpoints para Business AI Omnicanal Widget
if business_ai_mode:
    # Incluir router de Business AI
    app.include_router(business_ai_mode.get_api_router())
    
    # Endpoint para servir el widget.js estático
    @app.get("/static/business-ai-widget.js")
    async def serve_widget_js():
        """Sirve el archivo JavaScript del widget embeddable"""
        widget_path = Path(__file__).parent / "docchat" / "static" / "business-ai-widget.js"
        if widget_path.exists():
            from fastapi.responses import FileResponse
            return FileResponse(
                widget_path,
                media_type="application/javascript",
                headers={"Cache-Control": "public, max-age=3600"}
            )
        else:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Widget file not found")
    
    # Endpoint específico para n8n webhooks (WhatsApp/Instagram)
    @app.post("/business-ai/n8n/webhook")
    async def n8n_webhook(payload: Dict[str, Any]):
        """Endpoint para recibir webhooks de n8n (WhatsApp/Instagram).
        
        n8n envía mensajes aquí cuando llegan por WhatsApp/Instagram.
        """
        try:
            # Extraer datos del webhook de n8n
            message = payload.get("message") or payload.get("text") or ""
            from_number = payload.get("from") or payload.get("phone_number") or payload.get("wa_id")
            channel = payload.get("channel", "whatsapp")  # whatsapp, instagram, messenger
            
            # Crear payload para Business AI
            business_ai_payload = {
                "session_id": f"{channel}_{from_number}",
                "user_id": from_number,
                "message": message,
                "channel": channel,
                "metadata": {
                    "from": from_number,
                    "channel": channel,
                    "n8n_webhook": True,
                    "raw_payload": payload
                }
            }
            
            # Procesar con Business AI
            result = business_ai_mode.process_message(business_ai_payload, channel=channel)
            
            # Retornar respuesta para que n8n la envíe de vuelta
            return {
                "success": True,
                "response": result.get("text", ""),
                "metadata": {
                    "intent": result.get("intent"),
                    "sentiment": result.get("sentiment"),
                    "needs_handoff": result.get("needs_handoff", False),
                    "cart": result.get("cart"),
                    "tools": result.get("tools")
                }
            }
        except Exception as e:
            import traceback
            return {
                "success": False,
                "error": str(e),
                "traceback": traceback.format_exc()
            }
    
    # Endpoint para n8n: obtener historial de usuario (memoria de largo plazo)
    @app.get("/business-ai/n8n/user-history/{user_id}")
    async def get_user_history_n8n(user_id: str, days: int = 180):
        """Obtiene historial de usuario para n8n (últimos N días)."""
        try:
            if hasattr(business_ai_mode.session_manager, 'get_user_history'):
                history = business_ai_mode.session_manager.get_user_history(user_id=user_id, days=days)
                return {
                    "success": True,
                    "history": history
                }
            else:
                return {
                    "success": False,
                    "error": "PostgreSQL no está habilitado. Configura DATABASE_URL y DOCCHAT_POSTGRESQL_ENABLED=true"
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

@app.get("/")
async def root():
    """Endpoint raíz con información de la API y modos disponibles."""
    return {
        "service": "DocChat Enterprise - Backend RAG + Deep Research",
        "version": "1.1.0",
        "description": "Backend que permite conectar chatbots existentes y ejecutar Deep Research empresarial multi-agente.",
        "chatbot_flow": {
            "1": "Cliente pregunta → En el chatbot de la empresa (en su app)",
            "2": "Chatbot de la empresa consulta → DocChat Enterprise por API",
            "3": "DocChat Enterprise busca → En documentos privados de la empresa",
            "4": "DocChat Enterprise responde → Al chatbot de la empresa",
            "5": "Chatbot de la empresa muestra → Respuesta al cliente en su app"
        },
        "deep_research_flow": {
            "1": "Usuario envía una consulta de investigación empresarial a /deep-research",
            "2": "El Master Research Agent descompone la query en tareas en todo.md",
            "3": "Agentes de búsqueda ejecutan búsquedas web (general, académica, código, perfiles)",
            "4": "El sistema sintetiza, reflexiona sobre knowledge gaps y actualiza el plan",
            "5": "Se genera un informe en Markdown con fuentes y trazabilidad",
        },
        "endpoints": {
            "register": "POST /api/chatbot/register",
            "upload": "POST /api/chatbot/{chatbot_id}/upload",
            "query": "POST /api/chatbot/{chatbot_id}/query",
            "info": "GET /api/chatbot/{chatbot_id}/info",
            "list": "GET /api/chatbot/list",
            "health": "GET /api/chatbot/health",
            "deep_research": "POST /deep-research",
            "steering_message": "POST /steering/message",
            "steering_plan": "GET /steering/plan/{session_id}",
            "steering_status": "GET /steering/status/{session_id}",
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
