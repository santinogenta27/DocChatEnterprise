"""
Manejador de Webhooks para nuevos posts de Instagram/Facebook.

Según especificaciones:
- Webhooks para IG/FB nuevos posts
- Actualización automática en tiempo real
"""

from __future__ import annotations

import os
from typing import Dict, Any, Optional
from fastapi import APIRouter, Request, HTTPException

from .multi_source_ingester import MultiSourceIngester


def create_webhook_router(ingester: Optional[MultiSourceIngester]) -> APIRouter:
    """
    Crea router de FastAPI para webhooks de Instagram/Facebook.
    
    Args:
        ingester: Instancia de MultiSourceIngester
        
    Returns:
        APIRouter con endpoints de webhooks
    """
    router = APIRouter(prefix="/webhooks", tags=["Webhooks"])
    
    if not ingester:
        # Si no hay ingester, retornar router vacío con mensaje
        @router.post("/instagram")
        @router.post("/facebook")
        async def webhook_disabled():
            return {"message": "Ingesta automática no está habilitada"}
        return router
    
    @router.post("/instagram")
    async def instagram_webhook(request: Request):
        """
        Webhook para nuevos posts de Instagram.
        
        Formato esperado (según Instagram Graph API):
        {
            "object": "instagram",
            "entry": [{
                "id": "page_id",
                "messaging": [{
                    "sender": {"id": "user_id"},
                    "recipient": {"id": "page_id"},
                    "timestamp": 1234567890,
                    "message": {...}
                }]
            }]
        }
        """
        try:
            payload = await request.json()
            
            # Procesar según formato de Instagram Graph API
            entries = payload.get("entry", [])
            
            for entry in entries:
                # Extraer datos del post
                post_data = {
                    "id": entry.get("id", ""),
                    "timestamp": entry.get("time", ""),
                    "caption": entry.get("caption", ""),
                    "permalink": entry.get("permalink", ""),
                    "media_type": entry.get("media_type", ""),
                }
                
                # Procesar con ingester
                success = ingester.handle_webhook_new_post("instagram", post_data)
                
                if success:
                    return {"status": "success", "message": "Post procesado"}
            
            return {"status": "success", "message": "Webhook recibido"}
            
        except Exception as e:
            print(f"⚠️ Error procesando webhook de Instagram: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @router.post("/facebook")
    async def facebook_webhook(request: Request):
        """
        Webhook para nuevos posts de Facebook.
        
        Formato esperado (según Facebook Graph API):
        {
            "object": "page",
            "entry": [{
                "id": "page_id",
                "time": 1234567890,
                "messaging": [{
                    "sender": {"id": "user_id"},
                    "recipient": {"id": "page_id"},
                    "timestamp": 1234567890,
                    "message": {...}
                }]
            }]
        }
        """
        try:
            payload = await request.json()
            
            # Verificar si es verificación de webhook (Facebook requiere esto)
            if payload.get("object") == "page" and "entry" not in payload:
                # Verificación de webhook
                mode = request.query_params.get("hub.mode")
                token = request.query_params.get("hub.verify_token")
                challenge = request.query_params.get("hub.challenge")
                
                verify_token = os.getenv("FACEBOOK_VERIFY_TOKEN", "your_verify_token")
                
                if mode == "subscribe" and token == verify_token:
                    return int(challenge)
                else:
                    raise HTTPException(status_code=403, detail="Verification failed")
            
            # Procesar posts
            entries = payload.get("entry", [])
            
            for entry in entries:
                post_data = {
                    "id": entry.get("id", ""),
                    "created_time": entry.get("time", ""),
                    "message": entry.get("message", {}).get("text", ""),
                    "permalink_url": f"https://facebook.com/{entry.get('id', '')}",
                }
                
                # Procesar con ingester
                success = ingester.handle_webhook_new_post("facebook", post_data)
                
                if success:
                    return {"status": "success", "message": "Post procesado"}
            
            return {"status": "success", "message": "Webhook recibido"}
            
        except Exception as e:
            print(f"⚠️ Error procesando webhook de Facebook: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @router.get("/health")
    async def webhook_health():
        """Health check para webhooks."""
        return {
            "status": "healthy",
            "ingester_enabled": ingester is not None,
            "scheduler_running": ingester.scheduler_running if ingester else False,
        }
    
    return router

