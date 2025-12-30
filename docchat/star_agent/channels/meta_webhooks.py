"""
Webhook Handlers para WhatsApp Business y Facebook Messenger.

Maneja webhooks de Meta para recibir mensajes y enviar respuestas.
"""

from __future__ import annotations

import os
from typing import Dict, Any, Optional
from fastapi import APIRouter, Request, HTTPException, Query

from .whatsapp_adapter import WhatsAppBusinessAdapter
from .messenger_adapter import MessengerAdapter


def create_meta_webhooks_router(
    whatsapp_adapter: Optional[WhatsAppBusinessAdapter] = None,
    messenger_adapter: Optional[MessengerAdapter] = None,
    star_agent_mode = None
) -> APIRouter:
    """
    Crea router de FastAPI para webhooks de Meta (WhatsApp y Messenger).
    
    Args:
        whatsapp_adapter: Instancia de WhatsAppBusinessAdapter
        messenger_adapter: Instancia de MessengerAdapter
        star_agent_mode: Instancia de StarAgentMode para procesar mensajes
        
    Returns:
        APIRouter con endpoints de webhooks
    """
    router = APIRouter(prefix="/webhooks/meta", tags=["Meta Webhooks"])
    
    # WhatsApp Webhook
    @router.get("/whatsapp")
    async def whatsapp_webhook_verify(
        hub_mode: str = Query(..., alias="hub.mode"),
        hub_verify_token: str = Query(..., alias="hub.verify_token"),
        hub_challenge: str = Query(..., alias="hub.challenge")
    ):
        """
        Verificación de webhook de WhatsApp (GET).
        
        Meta requiere verificación antes de enviar webhooks.
        """
        if not whatsapp_adapter:
            raise HTTPException(status_code=503, detail="WhatsApp adapter no configurado")
        
        verify_token = whatsapp_adapter.verify_token
        
        if hub_mode == "subscribe" and hub_verify_token == verify_token:
            return int(hub_challenge)
        else:
            raise HTTPException(status_code=403, detail="Verification failed")
    
    @router.post("/whatsapp")
    async def whatsapp_webhook(request: Request):
        """
        Webhook para recibir mensajes de WhatsApp (POST).
        
        Procesa mensajes entrantes y envía respuestas automáticas.
        """
        if not whatsapp_adapter or not star_agent_mode:
            return {"status": "ok", "message": "WhatsApp no configurado"}
        
        try:
            payload = await request.json()
            
            # Convertir a formato interno
            channel_message = whatsapp_adapter.to_internal(payload)
            
            if not channel_message:
                # Puede ser un status update, no un mensaje
                return {"status": "ok"}
            
            # Procesar mensaje con STAR AGENT
            internal_payload = {
                "session_id": channel_message.session_id,
                "user_id": channel_message.user_id,
                "message": channel_message.content,
                "channel": "whatsapp"
            }
            
            # Obtener respuesta del agente
            response = star_agent_mode.process_message(internal_payload, channel="whatsapp")
            
            # Enviar respuesta por WhatsApp
            phone_number = channel_message.metadata.get("phone_number", "")
            response_text = response.get("text", "")
            
            if phone_number and response_text:
                send_result = whatsapp_adapter.send_message(
                    to=phone_number,
                    message=response_text
                )
                
                # Marcar mensaje original como leído
                message_id = channel_message.message_id
                if message_id:
                    whatsapp_adapter.mark_as_read(message_id)
            
            return {"status": "ok", "message": "Processed"}
            
        except Exception as e:
            print(f"⚠️ Error procesando webhook de WhatsApp: {e}")
            return {"status": "error", "message": str(e)}
    
    # Messenger Webhook
    @router.get("/messenger")
    async def messenger_webhook_verify(
        hub_mode: str = Query(..., alias="hub.mode"),
        hub_verify_token: str = Query(..., alias="hub.verify_token"),
        hub_challenge: str = Query(..., alias="hub.challenge")
    ):
        """
        Verificación de webhook de Messenger (GET).
        """
        if not messenger_adapter:
            raise HTTPException(status_code=503, detail="Messenger adapter no configurado")
        
        verify_token = messenger_adapter.verify_token
        
        if hub_mode == "subscribe" and hub_verify_token == verify_token:
            return int(hub_challenge)
        else:
            raise HTTPException(status_code=403, detail="Verification failed")
    
    @router.post("/messenger")
    async def messenger_webhook(request: Request):
        """
        Webhook para recibir mensajes de Messenger (POST).
        
        Procesa mensajes entrantes y envía respuestas automáticas.
        """
        if not messenger_adapter or not star_agent_mode:
            return {"status": "ok", "message": "Messenger no configurado"}
        
        try:
            payload = await request.json()
            
            # Verificar si es verificación de webhook
            if payload.get("object") == "page" and "entry" not in payload:
                return {"status": "ok"}
            
            # Convertir a formato interno
            channel_message = messenger_adapter.to_internal(payload)
            
            if not channel_message:
                return {"status": "ok"}
            
            # Enviar indicador de escritura
            sender_id = channel_message.metadata.get("sender_id", "")
            if sender_id:
                messenger_adapter.send_typing_indicator(sender_id, "typing_on")
            
            # Procesar mensaje con STAR AGENT
            # Determinar si es Instagram o Messenger (Instagram usa la misma API que Messenger)
            # Por ahora, usamos "messenger" para ambos, pero podríamos detectar basado en payload
            channel_type = "instagram" if hasattr(messenger_adapter, 'channel_name') and messenger_adapter.channel_name == "instagram" else "messenger"
            
            internal_payload = {
                "session_id": channel_message.session_id,
                "user_id": channel_message.user_id,
                "message": channel_message.content,
                "channel": channel_type  # Usar "instagram" si es Instagram, "messenger" si es Messenger
            }
            
            # Obtener respuesta del agente
            response = star_agent_mode.process_message(internal_payload, channel=channel_type)
            
            # Enviar respuesta por Messenger
            response_text = response.get("text", "")
            
            if sender_id and response_text:
                send_result = messenger_adapter.send_message(
                    recipient_id=sender_id,
                    message=response_text
                )
                
                # Apagar indicador de escritura
                messenger_adapter.send_typing_indicator(sender_id, "typing_off")
            
            return {"status": "ok", "message": "Processed"}
            
        except Exception as e:
            print(f"⚠️ Error procesando webhook de Messenger: {e}")
            return {"status": "error", "message": str(e)}
    
    @router.get("/health")
    async def webhooks_health():
        """Health check para webhooks."""
        return {
            "status": "healthy",
            "whatsapp_enabled": whatsapp_adapter is not None,
            "messenger_enabled": messenger_adapter is not None,
        }
    
    return router

