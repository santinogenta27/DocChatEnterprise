"""
Facebook Messenger Adapter para STAR AGENT.

Integración nativa con Facebook Messenger usando Graph API.
"""

from __future__ import annotations

import os
import json
import requests
from typing import Dict, Any, Optional
from datetime import datetime

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    print("⚠️ requests no disponible. Instala con: pip install requests")

from .base import BaseChannelAdapter, ChannelMessage


class MessengerAdapter(BaseChannelAdapter):
    """
    Adapter para Facebook Messenger.
    
    Usa Graph API de Meta para:
    - Recibir mensajes (via webhooks)
    - Enviar mensajes (via API)
    - Gestionar conversaciones
    """
    
    channel_name = "messenger"
    
    def __init__(
        self,
        page_id: Optional[str] = None,
        access_token: Optional[str] = None,
        verify_token: Optional[str] = None,
        api_version: str = "v18.0"
    ):
        """
        Inicializa el adapter de Messenger.
        
        Args:
            page_id: ID de la página de Facebook
            access_token: Access token de la página (Page Access Token)
            verify_token: Token de verificación para webhooks
            api_version: Versión de la API (default: v18.0)
        """
        self.page_id = page_id or os.getenv("FACEBOOK_PAGE_ID")
        self.access_token = access_token or os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN")
        self.verify_token = verify_token or os.getenv("FACEBOOK_VERIFY_TOKEN", "star_agent_verify_token")
        self.api_version = api_version
        self.base_url = f"https://graph.facebook.com/{api_version}"
        
        if not self.page_id or not self.access_token:
            print("⚠️ Facebook Messenger no configurado. Configura FACEBOOK_PAGE_ID y FACEBOOK_PAGE_ACCESS_TOKEN")
    
    def to_internal(self, raw_payload: Dict[str, Any]) -> ChannelMessage:
        """
        Convierte payload de Messenger a formato interno.
        
        Formato de webhook de Messenger:
        {
            "object": "page",
            "entry": [{
                "id": "PAGE_ID",
                "time": 1234567890,
                "messaging": [{
                    "sender": {"id": "USER_ID"},
                    "recipient": {"id": "PAGE_ID"},
                    "timestamp": 1234567890,
                    "message": {
                        "mid": "message_id",
                        "text": "Hola"
                    }
                }]
            }]
        }
        """
        try:
            # Extraer datos del webhook
            entry = raw_payload.get("entry", [{}])[0]
            messaging = entry.get("messaging", [])
            
            if not messaging:
                return None
            
            message_event = messaging[0]
            sender = message_event.get("sender", {})
            recipient = message_event.get("recipient", {})
            message = message_event.get("message", {})
            
            # Construir ChannelMessage
            sender_id = sender.get("id", "")
            message_id = message.get("mid", "")
            text_content = message.get("text", "")
            timestamp = message_event.get("timestamp", "")
            
            # Usar sender_id como session_id y user_id
            session_id = f"messenger_{sender_id}"
            user_id = sender_id
            
            return ChannelMessage(
                session_id=session_id,
                channel=self.channel_name,
                user_id=user_id,
                content=text_content,
                message_id=message_id,
                metadata={
                    "sender_id": sender_id,
                    "recipient_id": recipient.get("id", ""),
                    "timestamp": timestamp,
                    "page_id": self.page_id,
                }
            )
        except Exception as e:
            print(f"⚠️ Error parseando mensaje de Messenger: {e}")
            return None
    
    def send_message(
        self,
        recipient_id: str,
        message: str,
        message_type: str = "text"
    ) -> Dict[str, Any]:
        """
        Envía mensaje a través de Messenger API.
        
        Args:
            recipient_id: ID del usuario de Facebook (PSID)
            message: Contenido del mensaje
            message_type: Tipo de mensaje (text, etc.)
            
        Returns:
            Dict con respuesta de la API
        """
        if not self.page_id or not self.access_token:
            return {
                "success": False,
                "error": "Facebook Messenger no configurado"
            }
        
        if not REQUESTS_AVAILABLE:
            return {
                "success": False,
                "error": "requests no disponible"
            }
        
        url = f"{self.base_url}/me/messages"
        headers = {
            "Content-Type": "application/json"
        }
        
        # Construir payload según tipo de mensaje
        if message_type == "text":
            payload = {
                "recipient": {
                    "id": recipient_id
                },
                "message": {
                    "text": message
                },
                "messaging_type": "RESPONSE"
            }
        else:
            payload = {
                "recipient": {
                    "id": recipient_id
                },
                "message": {
                    "text": message
                },
                "messaging_type": "RESPONSE"
            }
        
        # Agregar access token como query parameter
        params = {
            "access_token": self.access_token
        }
        
        try:
            response = requests.post(url, headers=headers, json=payload, params=params, timeout=10)
            response.raise_for_status()
            
            result = response.json()
            
            return {
                "success": True,
                "message_id": result.get("message_id", ""),
                "recipient_id": result.get("recipient_id", ""),
                "response": result
            }
        except requests.exceptions.RequestException as e:
            print(f"⚠️ Error enviando mensaje de Messenger: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def send_quick_replies(
        self,
        recipient_id: str,
        message: str,
        quick_replies: list
    ) -> Dict[str, Any]:
        """
        Envía mensaje con quick replies (botones rápidos).
        
        Args:
            recipient_id: ID del usuario
            message: Texto del mensaje
            quick_replies: Lista de quick replies [{"content_type": "text", "title": "...", "payload": "..."}]
            
        Returns:
            Dict con respuesta de la API
        """
        if not self.page_id or not self.access_token:
            return {"success": False, "error": "Facebook Messenger no configurado"}
        
        url = f"{self.base_url}/me/messages"
        headers = {"Content-Type": "application/json"}
        params = {"access_token": self.access_token}
        
        payload = {
            "recipient": {"id": recipient_id},
            "message": {
                "text": message,
                "quick_replies": quick_replies
            },
            "messaging_type": "RESPONSE"
        }
        
        try:
            response = requests.post(url, headers=headers, json=payload, params=params, timeout=10)
            response.raise_for_status()
            return {"success": True, "response": response.json()}
        except requests.exceptions.RequestException as e:
            print(f"⚠️ Error enviando quick replies: {e}")
            return {"success": False, "error": str(e)}
    
    def send_typing_indicator(self, recipient_id: str, action: str = "typing_on") -> Dict[str, Any]:
        """
        Envía indicador de escritura (typing indicator).
        
        Args:
            recipient_id: ID del usuario
            action: "typing_on" o "typing_off"
            
        Returns:
            Dict con respuesta de la API
        """
        if not self.page_id or not self.access_token:
            return {"success": False, "error": "Facebook Messenger no configurado"}
        
        url = f"{self.base_url}/me/messages"
        headers = {"Content-Type": "application/json"}
        params = {"access_token": self.access_token}
        
        payload = {
            "recipient": {"id": recipient_id},
            "sender_action": action
        }
        
        try:
            response = requests.post(url, headers=headers, json=payload, params=params, timeout=10)
            response.raise_for_status()
            return {"success": True, "response": response.json()}
        except requests.exceptions.RequestException as e:
            print(f"⚠️ Error enviando typing indicator: {e}")
            return {"success": False, "error": str(e)}
    
    def get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """
        Obtiene perfil del usuario.
        
        Args:
            user_id: ID del usuario (PSID)
            
        Returns:
            Dict con información del perfil
        """
        if not self.access_token:
            return {"success": False, "error": "Access token no configurado"}
        
        url = f"{self.base_url}/{user_id}"
        params = {
            "access_token": self.access_token,
            "fields": "first_name,last_name,profile_pic"
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            return {"success": True, "profile": response.json()}
        except requests.exceptions.RequestException as e:
            print(f"⚠️ Error obteniendo perfil: {e}")
            return {"success": False, "error": str(e)}


