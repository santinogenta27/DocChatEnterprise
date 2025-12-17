"""
FastAPI Backend para Business AI Agent
======================================

API REST para:
- Procesar mensajes del widget web
- Webhooks de WhatsApp
- Dashboard de configuración
- Analytics
"""

from __future__ import annotations

import os
import json
from typing import Optional, Dict, Any
from datetime import datetime

try:
    from fastapi import FastAPI, HTTPException, Depends, Request, Header
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import JSONResponse, HTMLResponse, FileResponse
    from fastapi.staticfiles import StaticFiles
    from pydantic import BaseModel, Field
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False
    FastAPI = None

from .business_ai_agent_mode import BusinessAIAgentMode, ChannelType


# ==================== PYDANTIC MODELS ====================

class MessageRequest(BaseModel):
    """Request para procesar un mensaje."""
    message: str = Field(..., description="Mensaje del usuario")
    user_id: Optional[str] = Field(None, description="ID del usuario (opcional)")
    conversation_id: Optional[str] = Field(None, description="ID de conversación existente")


class MessageResponse(BaseModel):
    """Response con la respuesta del agente."""
    response: str
    conversation_id: str
    intent: str
    escalate: bool
    lead_captured: bool = False


class WhatsAppWebhook(BaseModel):
    """Webhook de WhatsApp."""
    object: str
    entry: list


class CompanyConfigRequest(BaseModel):
    """Request para crear/actualizar empresa."""
    name: str
    description: str
    products: list
    faqs: Optional[list] = None
    business_rules: Optional[dict] = None
    whatsapp_config: Optional[dict] = None


# ==================== FASTAPI APP ====================

class BusinessAIAgentAPI:
    """API FastAPI para Business AI Agent."""
    
    def __init__(self, agent_mode: BusinessAIAgentMode):
        """
        Inicializa la API.
        
        Args:
            agent_mode: Instancia de BusinessAIAgentMode
        """
        if not FASTAPI_AVAILABLE:
            raise RuntimeError("FastAPI no está disponible. Instala: pip install fastapi uvicorn")
        
        self.agent = agent_mode
        
        # Crear app FastAPI
        self.app = FastAPI(
            title="Business AI Agent API",
            description="API para Business AI Agent - Sales & Customer Support",
            version="1.0.0"
        )
        
        # CORS middleware
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],  # En producción, especificar dominios
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # Registrar rutas
        self._register_routes()
    
    def _register_routes(self):
        """Registra todas las rutas de la API."""
        
        @self.app.get("/")
        async def root():
            return {"message": "Business AI Agent API", "status": "running"}
        
        @self.app.post("/api/v1/chat", response_model=MessageResponse)
        async def chat(
            request: MessageRequest,
            x_widget_key: Optional[str] = Header(None, alias="X-Widget-Key")
        ):
            """
            Endpoint para procesar mensajes del widget web.
            """
            if not x_widget_key:
                raise HTTPException(status_code=401, detail="Widget key requerida")
            
            # Obtener empresa por widget key
            company = self.agent.get_company_by_widget_key(x_widget_key)
            if not company:
                raise HTTPException(status_code=404, detail="Empresa no encontrada")
            
            company_id = company["company_id"]
            user_id = request.user_id or f"web_{hash(request.message)}"
            
            # Procesar mensaje
            result = self.agent.process_message(
                company_id=company_id,
                user_message=request.message,
                user_id=user_id,
                channel=ChannelType.WEB,
                conversation_id=request.conversation_id
            )
            
            return MessageResponse(**result)
        
        @self.app.post("/api/v1/whatsapp/webhook")
        async def whatsapp_webhook(
            request: Request,
            x_widget_key: Optional[str] = Header(None, alias="X-Widget-Key")
        ):
            """
            Webhook para recibir mensajes de WhatsApp Business API.
            """
            try:
                body = await request.json()
                
                # Verificación de webhook (Meta requiere esto)
                if body.get("hub.verify_token"):
                    # Obtener empresa
                    if not x_widget_key:
                        raise HTTPException(status_code=401, detail="Widget key requerida")
                    
                    company = self.agent.get_company_by_widget_key(x_widget_key)
                    if not company:
                        raise HTTPException(status_code=404, detail="Empresa no encontrada")
                    
                    # Verificar token
                    verify_token = body.get("hub.verify_token")
                    # Aquí deberías verificar contra el token configurado de WhatsApp
                    # Por ahora retornamos el challenge
                    challenge = body.get("hub.challenge")
                    return int(challenge) if challenge else {"status": "error"}
                
                # Procesar mensajes entrantes
                if body.get("object") == "whatsapp_business_account":
                    for entry in body.get("entry", []):
                        changes = entry.get("changes", [])
                        for change in changes:
                            value = change.get("value", {})
                            messages = value.get("messages", [])
                            
                            for message in messages:
                                # Obtener empresa (debería venir del phone_number_id)
                                phone_id = value.get("metadata", {}).get("phone_number_id")
                                # Por ahora usamos widget_key del header
                                if not x_widget_key:
                                    continue
                                
                                company = self.agent.get_company_by_widget_key(x_widget_key)
                                if not company:
                                    continue
                                
                                company_id = company["company_id"]
                                
                                # Extraer información del mensaje
                                from_number = message.get("from")
                                message_text = message.get("text", {}).get("body", "")
                                
                                if not message_text:
                                    continue
                                
                                # Procesar mensaje
                                result = self.agent.process_message(
                                    company_id=company_id,
                                    user_message=message_text,
                                    user_id=from_number,
                                    channel=ChannelType.WHATSAPP
                                )
                                
                                # Enviar respuesta por WhatsApp
                                self.agent.send_whatsapp_message(
                                    company_id=company_id,
                                    to=from_number,
                                    message=result['response']
                                )
                
                return {"status": "success"}
                
            except Exception as e:
                print(f"Error en webhook WhatsApp: {e}")
                return {"status": "error", "message": str(e)}
        
        @self.app.post("/api/v1/companies", status_code=201)
        async def create_company(request: CompanyConfigRequest):
            """
            Crea una nueva empresa.
            """
            try:
                company_id = self.agent.create_company(
                    name=request.name,
                    description=request.description,
                    products=request.products,
                    faqs=request.faqs or [],
                    business_rules=request.business_rules or {},
                    whatsapp_config=request.whatsapp_config
                )
                
                company = self.agent.get_company(company_id)
                
                return {
                    "status": "success",
                    "company_id": company_id,
                    "company": company
                }
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))
        
        @self.app.get("/api/v1/companies/{company_id}")
        async def get_company(company_id: str):
            """
            Obtiene información de una empresa.
            """
            company = self.agent.get_company(company_id)
            if not company:
                raise HTTPException(status_code=404, detail="Empresa no encontrada")
            
            return company
        
        @self.app.get("/api/v1/companies/{company_id}/analytics")
        async def get_analytics(company_id: str):
            """
            Obtiene analytics de una empresa.
            """
            analytics = self.agent.get_analytics(company_id)
            return analytics
        
        @self.app.get("/api/v1/companies/{company_id}/widget-script")
        async def get_widget_script(company_id: str):
            """
            Obtiene el script del widget para insertar en la página web.
            """
            script = self.agent.get_widget_script(company_id)
            if not script:
                raise HTTPException(status_code=404, detail="Empresa no encontrada")
            
            return HTMLResponse(content=script)
        
        @self.app.get("/api/v1/widget.js")
        async def widget_js(request: Request):
            """
            Servir el archivo JavaScript del widget.
            """
            widget_key = request.query_params.get("key")
            if not widget_key:
                raise HTTPException(status_code=400, detail="Widget key requerida")
            
            # Verificar que la empresa existe
            company = self.agent.get_company_by_widget_key(widget_key)
            if not company:
                raise HTTPException(status_code=404, detail="Empresa no encontrada")
            
            # Generar código JavaScript del widget
            api_base_url = os.getenv(
                "BUSINESS_AI_API_BASE_URL",
                "http://localhost:8000"
            )
            
            widget_code = f"""
(function() {{
    'use strict';
    
    var widgetKey = '{widget_key}';
    var apiBaseUrl = '{api_base_url}';
    var conversationId = null;
    
    // Crear contenedor del widget
    var widgetContainer = document.createElement('div');
    widgetContainer.id = 'business-ai-widget';
    widgetContainer.style.cssText = `
        position: fixed;
        bottom: 20px;
        right: 20px;
        width: 350px;
        height: 500px;
        background: white;
        border-radius: 10px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.15);
        display: flex;
        flex-direction: column;
        z-index: 10000;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    `;
    
    // Header
    var header = document.createElement('div');
    header.style.cssText = `
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 15px;
        border-radius: 10px 10px 0 0;
        display: flex;
        justify-content: space-between;
        align-items: center;
    `;
    header.innerHTML = '<h3 style="margin:0;font-size:16px;">💬 ¿En qué podemos ayudarte?</h3>';
    
    var closeBtn = document.createElement('button');
    closeBtn.innerHTML = '×';
    closeBtn.style.cssText = `
        background: none;
        border: none;
        color: white;
        font-size: 24px;
        cursor: pointer;
        padding: 0;
        width: 30px;
        height: 30px;
    `;
    closeBtn.onclick = function() {{
        widgetContainer.style.display = 'none';
    }};
    header.appendChild(closeBtn);
    
    // Messages container
    var messagesContainer = document.createElement('div');
    messagesContainer.id = 'widget-messages';
    messagesContainer.style.cssText = `
        flex: 1;
        overflow-y: auto;
        padding: 15px;
        background: #f5f5f5;
    `;
    
    // Input area
    var inputArea = document.createElement('div');
    inputArea.style.cssText = `
        padding: 15px;
        border-top: 1px solid #e0e0e0;
        display: flex;
        gap: 10px;
    `;
    
    var input = document.createElement('input');
    input.type = 'text';
    input.placeholder = 'Escribe tu mensaje...';
    input.style.cssText = `
        flex: 1;
        padding: 10px;
        border: 1px solid #e0e0e0;
        border-radius: 20px;
        outline: none;
    `;
    
    var sendBtn = document.createElement('button');
    sendBtn.innerHTML = '→';
    sendBtn.style.cssText = `
        background: #667eea;
        color: white;
        border: none;
        border-radius: 50%;
        width: 40px;
        height: 40px;
        cursor: pointer;
        font-size: 18px;
    `;
    
    // Función para agregar mensaje
    function addMessage(text, isUser) {{
        var msgDiv = document.createElement('div');
        var styleText = 'margin-bottom: 10px; padding: 10px 15px; border-radius: 18px; max-width: 80%; word-wrap: break-word; ';
        if (isUser) {{
            styleText += 'background: #667eea; color: white; margin-left: auto;';
        }} else {{
            styleText += 'background: white; color: #333;';
        }}
        msgDiv.style.cssText = styleText;
        msgDiv.textContent = text;
        messagesContainer.appendChild(msgDiv);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }}
    
    // Función para enviar mensaje
    async function sendMessage() {{
        var message = input.value.trim();
        if (!message) return;
        
        addMessage(message, true);
        input.value = '';
        
        // Mostrar "escribiendo..."
        var typingDiv = document.createElement('div');
        typingDiv.id = 'typing-indicator';
        typingDiv.style.cssText = `
            margin-bottom: 10px;
            padding: 10px 15px;
            background: white;
            border-radius: 18px;
            color: #999;
            font-style: italic;
        `;
        typingDiv.textContent = 'Escribiendo...';
        messagesContainer.appendChild(typingDiv);
        
        try {{
            var response = await fetch(apiBaseUrl + '/api/v1/chat', {{
                method: 'POST',
                headers: {{
                    'Content-Type': 'application/json',
                    'X-Widget-Key': widgetKey
                }},
                body: JSON.stringify({{
                    message: message,
                    conversation_id: conversationId
                }})
            }});
            
            var data = await response.json();
            
            // Remover indicador de escritura
            var typing = document.getElementById('typing-indicator');
            if (typing) typing.remove();
            
            // Agregar respuesta
            addMessage(data.response, false);
            
            // Guardar conversation_id
            if (data.conversation_id) {{
                conversationId = data.conversation_id;
            }}
            
        }} catch (error) {{
            var typing = document.getElementById('typing-indicator');
            if (typing) typing.remove();
            addMessage('Lo siento, hubo un error. Por favor intenta de nuevo.', false);
        }}
    }}
    
    sendBtn.onclick = sendMessage;
    input.onkeypress = function(e) {{
        if (e.key === 'Enter') {{
            sendMessage();
        }}
    }};
    
    inputArea.appendChild(input);
    inputArea.appendChild(sendBtn);
    
    // Agregar mensaje inicial
    addMessage('¡Hola! Soy un asistente de IA. ¿En qué puedo ayudarte?', false);
    
    // Ensamblar widget
    widgetContainer.appendChild(header);
    widgetContainer.appendChild(messagesContainer);
    widgetContainer.appendChild(inputArea);
    
    // Agregar al DOM
    document.body.appendChild(widgetContainer);
    
    // Botón flotante para abrir widget
    var floatingBtn = document.createElement('button');
    floatingBtn.innerHTML = '💬';
    floatingBtn.style.cssText = `
        position: fixed;
        bottom: 20px;
        right: 20px;
        width: 60px;
        height: 60px;
        border-radius: 50%;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        font-size: 24px;
        cursor: pointer;
        box-shadow: 0 4px 20px rgba(0,0,0,0.3);
        z-index: 9999;
        display: none;
    `;
    floatingBtn.onclick = function() {{
        widgetContainer.style.display = widgetContainer.style.display === 'none' ? 'flex' : 'none';
    }};
    
    // Inicialmente ocultar widget
    widgetContainer.style.display = 'none';
    
    document.body.appendChild(floatingBtn);
    
    // Mostrar widget después de 3 segundos
    setTimeout(function() {{
        widgetContainer.style.display = 'flex';
    }}, 3000);
    
}})();
"""
            
            return HTMLResponse(
                content=widget_code,
                media_type="application/javascript"
            )
        
        @self.app.get("/api/v1/companies")
        async def list_companies():
            """Lista todas las empresas."""
            companies = self.agent.list_companies()
            return {"companies": companies}
        
        @self.app.put("/api/v1/companies/{company_id}")
        async def update_company(company_id: str, request: CompanyConfigRequest):
            """Actualiza una empresa."""
            success = self.agent.update_company_config(
                company_id=company_id,
                name=request.name,
                description=request.description,
                products=request.products,
                faqs=request.faqs,
                business_rules=request.business_rules,
                whatsapp_config=request.whatsapp_config
            )
            if not success:
                raise HTTPException(status_code=404, detail="Empresa no encontrada")
            
            company = self.agent.get_company(company_id)
            return {"status": "success", "company": company}
        
        @self.app.get("/api/v1/companies/{company_id}/leads")
        async def get_leads(company_id: str, status: Optional[str] = None):
            """Obtiene leads de una empresa."""
            leads = self.agent.get_leads(company_id, status)
            return {"leads": leads}
        
        @self.app.put("/api/v1/leads/{lead_id}/status")
        async def update_lead_status(lead_id: str, new_status: str):
            """Actualiza el estado de un lead."""
            success = self.agent.update_lead_status(lead_id, new_status)
            if not success:
                raise HTTPException(status_code=404, detail="Lead no encontrado")
            return {"status": "success"}
        
        @self.app.post("/api/v1/whatsapp/send")
        async def send_whatsapp(
            company_id: str,
            to: str,
            message: str,
            x_widget_key: Optional[str] = Header(None, alias="X-Widget-Key")
        ):
            """Envía un mensaje por WhatsApp."""
            if not x_widget_key:
                raise HTTPException(status_code=401, detail="Widget key requerida")
            
            company = self.agent.get_company_by_widget_key(x_widget_key)
            if not company:
                raise HTTPException(status_code=404, detail="Empresa no encontrada")
            
            success = self.agent.send_whatsapp_message(
                company_id=company["company_id"],
                to=to,
                message=message
            )
            
            if not success:
                raise HTTPException(status_code=400, detail="Error enviando mensaje")
            
            return {"status": "success", "message": "Mensaje enviado"}
        
        @self.app.get("/health")
        async def health():
            """Health check endpoint."""
            return {
                "status": "healthy",
                "service": "Business AI Agent API",
                "database": "connected" if self.agent.engine else "disconnected",
                "llm": "configured" if self.agent.llm else "not configured"
            }

