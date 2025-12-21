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
from fastapi.staticfiles import StaticFiles
import uvicorn

from docchat import AppConfig, load_config
from docchat.chatbot_mode import ChatbotMode
from docchat.chatbot_api import create_chatbot_api
from docchat.deep_research_api import create_deep_research_api
from typing import Dict, Any

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
# IMPORTANTE: Para file:// (origen null), necesitamos configuración especial
from fastapi.middleware.cors import CORSMiddleware

# Configuración CORS más permisiva para file:// y localhost
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permite cualquier origen (incluyendo null y localhost:8080)
    allow_credentials=False,  # CRÍTICO: False para permitir origen null y diferentes puertos
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600,
)

# Crear endpoints de chatbot (modo existente)
create_chatbot_api(app, chatbot_mode)

# Crear endpoints de Deep Research (nuevo modo)
create_deep_research_api(app, config)

# Montar archivos estáticos (para servir el widget.js)
static_dir = Path(__file__).parent / "docchat" / "static"
if static_dir.exists():
    try:
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
        print(f"✅ Archivos estáticos montados desde: {static_dir}")
    except Exception as e:
        print(f"⚠️ Error montando archivos estáticos: {e}")
        # Fallback: endpoint manual
        @app.get("/static/business-ai-widget.js")
        async def serve_widget_js():
            widget_path = static_dir / "business-ai-widget.js"
            if widget_path.exists():
                from fastapi.responses import FileResponse
                return FileResponse(
                    widget_path,
                    media_type="application/javascript",
                    headers={"Cache-Control": "public, max-age=3600"}
                )
            else:
                from fastapi import HTTPException
                raise HTTPException(status_code=404, detail=f"Widget file not found at: {widget_path}")
else:
    print(f"⚠️ Directorio estático no encontrado: {static_dir}")
    # Crear endpoint manual como fallback
    @app.get("/static/business-ai-widget.js")
    async def serve_widget_js_fallback():
        from fastapi import HTTPException
        raise HTTPException(
            status_code=404, 
            detail=f"Static directory not found. Expected at: {static_dir}"
        )

# Inicializar OmnicanalBridge (para integración real con WhatsApp/Facebook/Instagram)
omnicanal_bridge = None
if business_ai_mode:
    try:
        from docchat.business_ai_omnicanal.integrations.omnicanal_bridge import OmnicanalBridge, Channel, IncomingMessage, OutgoingMessage
        omnicanal_bridge = OmnicanalBridge()
        
        # Cargar configuración desde variables de entorno
        import os
        
        # Configurar WhatsApp (Twilio o Meta)
        whatsapp_provider = os.getenv("WHATSAPP_PROVIDER", "twilio")
        if whatsapp_provider == "twilio":
            account_sid = os.getenv("TWILIO_ACCOUNT_SID")
            auth_token = os.getenv("TWILIO_AUTH_TOKEN")
            from_number = os.getenv("TWILIO_WHATSAPP_NUMBER")
            if account_sid and auth_token and from_number:
                omnicanal_bridge.configure_whatsapp(
                    provider="twilio",
                    account_sid=account_sid,
                    auth_token=auth_token,
                    from_number=from_number
                )
        elif whatsapp_provider == "meta":
            phone_number_id = os.getenv("META_WHATSAPP_PHONE_NUMBER_ID")
            access_token = os.getenv("META_WHATSAPP_ACCESS_TOKEN")
            if phone_number_id and access_token:
                omnicanal_bridge.configure_whatsapp(
                    provider="meta",
                    phone_number_id=phone_number_id,
                    access_token=access_token
                )
        
        # Configurar Facebook Messenger
        facebook_token = os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN")
        facebook_verify_token = os.getenv("FACEBOOK_VERIFY_TOKEN", "verify_token")
        if facebook_token:
            omnicanal_bridge.configure_facebook(
                page_access_token=facebook_token,
                verify_token=facebook_verify_token
            )
        
        # Configurar Instagram Direct
        instagram_token = os.getenv("INSTAGRAM_ACCESS_TOKEN")
        instagram_user_id = os.getenv("INSTAGRAM_USER_ID")
        if instagram_token:
            omnicanal_bridge.configure_instagram(
                access_token=instagram_token,
                ig_user_id=instagram_user_id
            )
        
        print("✅ OmnicanalBridge inicializado y configurado")
    except Exception as e:
        print(f"⚠️ Error inicializando OmnicanalBridge: {e}")

# Endpoints para Business AI Omnicanal Widget
if business_ai_mode:
    # Incluir router de Business AI
    app.include_router(business_ai_mode.get_api_router())
    
    # ==================== WEBHOOKS OMNICANALES ====================
    
    # WhatsApp Webhook (Twilio)
    @app.post("/webhook/whatsapp/twilio")
    async def whatsapp_twilio_webhook(payload: Dict[str, Any]):
        """Webhook de Twilio para WhatsApp Business.
        
        Configura en Twilio Console: https://console.twilio.com
        Webhook URL: https://tu-servidor.com/webhook/whatsapp/twilio
        """
        if not omnicanal_bridge or not business_ai_mode:
            return {"error": "OmnicanalBridge o BusinessAIMode no inicializado"}
        
        try:
            incoming = omnicanal_bridge.process_webhook(Channel.WHATSAPP, payload)
            if not incoming:
                return {"status": "ignored"}
            
            # Procesar con Business AI
            result = business_ai_mode.handle_omnicanal_message(incoming)
            
            # Enviar respuesta por WhatsApp
            if result and result.get("text"):
                outgoing = OutgoingMessage(
                    channel=Channel.WHATSAPP,
                    recipient_id=incoming.sender_id,
                    message_text=result["text"]
                )
                omnicanal_bridge.send_message(outgoing)
            
            return {"status": "processed"}
        except Exception as e:
            import traceback
            print(f"❌ Error procesando webhook de WhatsApp/Twilio: {e}")
            print(traceback.format_exc())
            return {"error": str(e)}
    
    # WhatsApp Webhook (Meta) - Verificación
    @app.get("/webhook/whatsapp/meta")
    async def whatsapp_meta_webhook_verify(
        hub_mode: str = None,
        hub_verify_token: str = None,
        hub_challenge: str = None
    ):
        """Verificación de webhook de Meta WhatsApp (GET request)."""
        verify_token = os.getenv("META_WHATSAPP_VERIFY_TOKEN", "verify_token")
        if hub_mode == "subscribe" and hub_verify_token == verify_token:
            return int(hub_challenge)
        return {"error": "Invalid verification"}
    
    # WhatsApp Webhook (Meta) - Mensajes
    @app.post("/webhook/whatsapp/meta")
    async def whatsapp_meta_webhook(payload: Dict[str, Any]):
        """Webhook de Meta para WhatsApp Business API.
        
        Configura en Meta Developers: https://developers.facebook.com
        Webhook URL: https://tu-servidor.com/webhook/whatsapp/meta
        """
        if not omnicanal_bridge or not business_ai_mode:
            return {"error": "OmnicanalBridge o BusinessAIMode no inicializado"}
        
        try:
            incoming = omnicanal_bridge.process_webhook(Channel.WHATSAPP, payload)
            if not incoming:
                return {"status": "ignored"}
            
            # Procesar con Business AI
            result = business_ai_mode.handle_omnicanal_message(incoming)
            
            # Enviar respuesta por WhatsApp
            if result and result.get("text"):
                outgoing = OutgoingMessage(
                    channel=Channel.WHATSAPP,
                    recipient_id=incoming.sender_id,
                    message_text=result["text"]
                )
                omnicanal_bridge.send_message(outgoing)
            
            return {"status": "processed"}
        except Exception as e:
            import traceback
            print(f"❌ Error procesando webhook de WhatsApp/Meta: {e}")
            print(traceback.format_exc())
            return {"error": str(e)}
    
    # Facebook Messenger Webhook - Verificación
    @app.get("/webhook/facebook")
    async def facebook_webhook_verify(mode: str = None, token: str = None, challenge: str = None):
        """Verificación de webhook de Facebook Messenger (GET request).
        
        Configura en Meta Developers: https://developers.facebook.com
        Webhook URL: https://tu-servidor.com/webhook/facebook
        """
        verify_token = os.getenv("FACEBOOK_VERIFY_TOKEN", "verify_token")
        if mode == "subscribe" and token == verify_token:
            return int(challenge)
        return {"error": "Invalid verification"}
    
    # Facebook Messenger Webhook - Mensajes
    @app.post("/webhook/facebook")
    async def facebook_webhook(payload: Dict[str, Any]):
        """Webhook de Facebook Messenger.
        
        Configura en Meta Developers: https://developers.facebook.com
        """
        if not omnicanal_bridge or not business_ai_mode:
            return {"error": "OmnicanalBridge o BusinessAIMode no inicializado"}
        
        try:
            incoming = omnicanal_bridge.process_webhook(Channel.FACEBOOK, payload)
            if not incoming:
                return {"status": "ignored"}
            
            # Procesar con Business AI
            result = business_ai_mode.handle_omnicanal_message(incoming)
            
            # Enviar respuesta por Facebook Messenger
            if result and result.get("text"):
                outgoing = OutgoingMessage(
                    channel=Channel.FACEBOOK,
                    recipient_id=incoming.sender_id,
                    message_text=result["text"]
                )
                omnicanal_bridge.send_message(outgoing)
            
            return {"status": "processed"}
        except Exception as e:
            import traceback
            print(f"❌ Error procesando webhook de Facebook: {e}")
            print(traceback.format_exc())
            return {"error": str(e)}
    
    # Instagram Direct Webhook - Verificación
    @app.get("/webhook/instagram")
    async def instagram_webhook_verify(mode: str = None, token: str = None, challenge: str = None):
        """Verificación de webhook de Instagram Direct (GET request).
        
        Configura en Meta Developers: https://developers.facebook.com
        Webhook URL: https://tu-servidor.com/webhook/instagram
        """
        verify_token = os.getenv("INSTAGRAM_VERIFY_TOKEN", "verify_token")
        if mode == "subscribe" and token == verify_token:
            return int(challenge)
        return {"error": "Invalid verification"}
    
    # Instagram Direct Webhook - Mensajes
    @app.post("/webhook/instagram")
    async def instagram_webhook(payload: Dict[str, Any]):
        """Webhook de Instagram Direct Messages.
        
        Configura en Meta Developers: https://developers.facebook.com
        """
        if not omnicanal_bridge or not business_ai_mode:
            return {"error": "OmnicanalBridge o BusinessAIMode no inicializado"}
        
        try:
            incoming = omnicanal_bridge.process_webhook(Channel.INSTAGRAM, payload)
            if not incoming:
                return {"status": "ignored"}
            
            # Procesar con Business AI
            result = business_ai_mode.handle_omnicanal_message(incoming)
            
            # Enviar respuesta por Instagram
            if result and result.get("text"):
                outgoing = OutgoingMessage(
                    channel=Channel.INSTAGRAM,
                    recipient_id=incoming.sender_id,
                    message_text=result["text"]
                )
                omnicanal_bridge.send_message(outgoing)
            
            return {"status": "processed"}
        except Exception as e:
            import traceback
            print(f"❌ Error procesando webhook de Instagram: {e}")
            print(traceback.format_exc())
            return {"error": str(e)}
    
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
    # Obtener puerto de variable de entorno o usar 7864 por defecto (mismo que Gradio/widget)
    port = int(os.environ.get("PORT", 7864))
    host = os.environ.get("HOST", "0.0.0.0")
    
    print(f"🚀 Iniciando Chatbot Mode API en http://{host}:{port}")
    print(f"📚 Documentación disponible en http://{host}:{port}/docs")
    print(f"🔍 Health check: http://{host}:{port}/api/chatbot/health")
    print(f"📦 Widget JS disponible en http://{host}:{port}/static/business-ai-widget.js")
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info"
    )
