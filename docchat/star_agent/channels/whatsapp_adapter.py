"""
WhatsApp Business API Adapter para STAR AGENT.

Integración nativa con WhatsApp Business API usando la API oficial de Meta.
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


class WhatsAppBusinessAdapter(BaseChannelAdapter):
    """
    Adapter para WhatsApp Business API.
    
    Usa la API oficial de Meta para:
    - Recibir mensajes (via webhooks)
    - Enviar mensajes (via API)
    - Gestionar conversaciones
    """
    
    channel_name = "whatsapp"
    
    def __init__(
        self,
        phone_number_id: Optional[str] = None,
        access_token: Optional[str] = None,
        verify_token: Optional[str] = None,
        api_version: str = "v18.0"
    ):
        """
        Inicializa el adapter de WhatsApp Business.
        
        Args:
            phone_number_id: ID del número de teléfono de WhatsApp Business
            access_token: Access token de WhatsApp Business API
            verify_token: Token de verificación para webhooks
            api_version: Versión de la API (default: v18.0)
        """
        self.phone_number_id = phone_number_id or os.getenv("WHATSAPP_PHONE_NUMBER_ID")
        self.access_token = access_token or os.getenv("WHATSAPP_ACCESS_TOKEN")
        self.verify_token = verify_token or os.getenv("WHATSAPP_VERIFY_TOKEN", "star_agent_verify_token")
        self.api_version = api_version
        self.base_url = f"https://graph.facebook.com/{api_version}"
        
        if not self.phone_number_id or not self.access_token:
            print("⚠️ WhatsApp Business API no configurado. Configura WHATSAPP_PHONE_NUMBER_ID y WHATSAPP_ACCESS_TOKEN")
    
    def to_internal(self, raw_payload: Dict[str, Any]) -> ChannelMessage:
        """
        Convierte payload de WhatsApp a formato interno.
        
        Formato de webhook de WhatsApp:
        {
            "object": "whatsapp_business_account",
            "entry": [{
                "id": "WHATSAPP_BUSINESS_ACCOUNT_ID",
                "changes": [{
                    "value": {
                        "messaging_product": "whatsapp",
                        "metadata": {
                            "display_phone_number": "...",
                            "phone_number_id": "..."
                        },
                        "contacts": [{
                            "profile": {"name": "..."},
                            "wa_id": "1234567890"
                        }],
                        "messages": [{
                            "from": "1234567890",
                            "id": "wamid.xxx",
                            "timestamp": "1234567890",
                            "text": {"body": "Hola"},
                            "type": "text"
                        }]
                    }
                }]
            }]
        }
        """
        try:
            # Extraer datos del webhook
            entry = raw_payload.get("entry", [{}])[0]
            change = entry.get("changes", [{}])[0]
            value = change.get("value", {})
            
            # Extraer mensaje
            messages = value.get("messages", [])
            if not messages:
                # Puede ser un status update, no un mensaje
                return None
            
            message = messages[0]
            contacts = value.get("contacts", [])
            contact = contacts[0] if contacts else {}
            
            # Construir ChannelMessage
            from_number = message.get("from", "")
            message_id = message.get("id", "")
            timestamp = message.get("timestamp", "")
            text_content = message.get("text", {}).get("body", "")
            message_type = message.get("type", "text")
            
            # Usar número de teléfono como session_id y user_id
            session_id = f"whatsapp_{from_number}"
            user_id = from_number
            
            return ChannelMessage(
                session_id=session_id,
                channel=self.channel_name,
                user_id=user_id,
                content=text_content,
                message_id=message_id,
                metadata={
                    "phone_number": from_number,
                    "contact_name": contact.get("profile", {}).get("name", ""),
                    "message_type": message_type,
                    "timestamp": timestamp,
                    "phone_number_id": value.get("metadata", {}).get("phone_number_id", ""),
                }
            )
        except Exception as e:
            print(f"⚠️ Error parseando mensaje de WhatsApp: {e}")
            return None
    
    def send_message(
        self,
        to: str,
        message: str,
        message_type: str = "text"
    ) -> Dict[str, Any]:
        """
        Envía mensaje a través de WhatsApp Business API.
        
        Args:
            to: Número de teléfono del destinatario (formato: 1234567890)
            message: Contenido del mensaje
            message_type: Tipo de mensaje (text, template, etc.)
            
        Returns:
            Dict con respuesta de la API
        """
        if not self.phone_number_id or not self.access_token:
            return {
                "success": False,
                "error": "WhatsApp Business API no configurado"
            }
        
        if not REQUESTS_AVAILABLE:
            return {
                "success": False,
                "error": "requests no disponible"
            }
        
        # Formatear número (debe incluir código de país sin +)
        # Ejemplo: 5491123456789 (Argentina)
        to_formatted = to.replace("+", "").replace(" ", "").replace("-", "")
        
        url = f"{self.base_url}/{self.phone_number_id}/messages"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        # Construir payload según tipo de mensaje
        if message_type == "text":
            payload = {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": to_formatted,
                "type": "text",
                "text": {
                    "preview_url": False,
                    "body": message
                }
            }
        else:
            # Para otros tipos (template, media, etc.)
            payload = {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": to_formatted,
                "type": message_type,
                "text": {
                    "body": message
                }
            }
        
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=10)
            response.raise_for_status()
            
            result = response.json()
            
            return {
                "success": True,
                "message_id": result.get("messages", [{}])[0].get("id", ""),
                "response": result
            }
        except requests.exceptions.RequestException as e:
            print(f"⚠️ Error enviando mensaje de WhatsApp: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def send_template_message(
        self,
        to: str,
        template_name: str,
        language_code: str = "es",
        parameters: Optional[list] = None
    ) -> Dict[str, Any]:
        """
        Envía mensaje de plantilla (template) de WhatsApp.
        
        Args:
            to: Número de teléfono del destinatario
            template_name: Nombre de la plantilla aprobada
            language_code: Código de idioma (es, en, etc.)
            parameters: Lista de parámetros para la plantilla
            
        Returns:
            Dict con respuesta de la API
        """
        if not self.phone_number_id or not self.access_token:
            return {
                "success": False,
                "error": "WhatsApp Business API no configurado"
            }
        
        url = f"{self.base_url}/{self.phone_number_id}/messages"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        to_formatted = to.replace("+", "").replace(" ", "").replace("-", "")
        
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to_formatted,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {
                    "code": language_code
                }
            }
        }
        
        # Agregar parámetros si existen
        if parameters:
            payload["template"]["components"] = [{
                "type": "body",
                "parameters": [
                    {"type": "text", "text": param} for param in parameters
                ]
            }]
        
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=10)
            response.raise_for_status()
            
            result = response.json()
            return {
                "success": True,
                "message_id": result.get("messages", [{}])[0].get("id", ""),
                "response": result
            }
        except requests.exceptions.RequestException as e:
            print(f"⚠️ Error enviando template de WhatsApp: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def mark_as_read(self, message_id: str) -> Dict[str, Any]:
        """
        Marca mensaje como leído.
        
        Args:
            message_id: ID del mensaje a marcar como leído
            
        Returns:
            Dict con respuesta de la API
        """
        if not self.phone_number_id or not self.access_token:
            return {"success": False, "error": "WhatsApp Business API no configurado"}
        
        url = f"{self.base_url}/{self.phone_number_id}/messages"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "messaging_product": "whatsapp",
            "status": "read",
            "message_id": message_id
        }
        
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=10)
            response.raise_for_status()
            return {"success": True, "response": response.json()}
        except requests.exceptions.RequestException as e:
            print(f"⚠️ Error marcando mensaje como leído: {e}")
            return {"success": False, "error": str(e)}


