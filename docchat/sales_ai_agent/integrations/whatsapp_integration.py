"""
WhatsApp Integration - Integración opcional con WhatsApp Business API

Este módulo es OPCIONAL y se configura por separado.
No afecta el funcionamiento del agente principal si no está configurado.

Funcionalidades:
- Recibe mensajes de WhatsApp
- Envía respuestas a WhatsApp
- Integración con WhatsApp Business API
"""

from __future__ import annotations

import os
import json
from typing import Dict, Any, Optional
from dataclasses import dataclass

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    requests = None


@dataclass
class WhatsAppMessage:
    """Mensaje de WhatsApp."""
    message_id: str
    from_number: str
    message_text: str
    timestamp: str
    media_url: Optional[str] = None
    metadata: Dict[str, Any] = None


class WhatsAppIntegration:
    """
    Integración opcional con WhatsApp Business API.
    
    Características:
    - Recibe mensajes de WhatsApp
    - Envía respuestas a WhatsApp
    - Soporte para texto y media
    """
    
    def __init__(
        self,
        whatsapp_phone_number_id: Optional[str] = None,
        whatsapp_access_token: Optional[str] = None,
        whatsapp_verify_token: Optional[str] = None,
    ):
        """
        Inicializa la integración con WhatsApp.
        
        Args:
            whatsapp_phone_number_id: ID del número de teléfono de WhatsApp Business (opcional)
            whatsapp_access_token: Token de acceso de WhatsApp Business API (opcional)
            whatsapp_verify_token: Token de verificación para webhook (opcional)
        """
        # Cargar desde variables de entorno si no se proporcionan
        self.phone_number_id = whatsapp_phone_number_id or os.getenv("WHATSAPP_PHONE_NUMBER_ID")
        self.access_token = whatsapp_access_token or os.getenv("WHATSAPP_ACCESS_TOKEN")
        self.verify_token = whatsapp_verify_token or os.getenv("WHATSAPP_VERIFY_TOKEN")
        
        # Verificar si está configurado
        self.is_configured = bool(self.phone_number_id and self.access_token)
        
        if not REQUESTS_AVAILABLE:
            print("⚠️ requests no está instalado. Instala con: pip install requests")
            self.is_configured = False
        
        if self.is_configured:
            print("✅ WhatsApp Integration configurada")
        else:
            print("⚠️ WhatsApp Integration NO configurada (opcional - no afecta funcionamiento principal)")
    
    def parse_webhook_message(self, webhook_data: Dict[str, Any]) -> Optional[WhatsAppMessage]:
        """
        Parsea un mensaje recibido del webhook de WhatsApp.
        
        Args:
            webhook_data: Datos del webhook de WhatsApp
            
        Returns:
            WhatsAppMessage o None si no es un mensaje válido
        """
        try:
            entry = webhook_data.get("entry", [{}])[0]
            changes = entry.get("changes", [{}])[0]
            value = changes.get("value", {})
            messages = value.get("messages", [])
            
            if not messages:
                return None
            
            message_data = messages[0]
            
            # Extraer información
            message_id = message_data.get("id", "")
            from_number = message_data.get("from", "")
            timestamp = message_data.get("timestamp", "")
            
            # Extraer texto o media
            message_text = ""
            media_url = None
            
            if "text" in message_data:
                message_text = message_data["text"].get("body", "")
            elif "image" in message_data:
                media_url = message_data["image"].get("url", "")
                message_text = f"[Imagen recibida]"
            elif "video" in message_data:
                media_url = message_data["video"].get("url", "")
                message_text = f"[Video recibido]"
            elif "document" in message_data:
                media_url = message_data["document"].get("url", "")
                message_text = f"[Documento recibido]"
            
            return WhatsAppMessage(
                message_id=message_id,
                from_number=from_number,
                message_text=message_text,
                timestamp=timestamp,
                media_url=media_url,
                metadata=message_data
            )
            
        except Exception as e:
            print(f"⚠️ Error parseando mensaje de WhatsApp: {e}")
            return None
    
    def send_message(
        self,
        to_number: str,
        message_text: str,
        media_url: Optional[str] = None,
        media_type: Optional[str] = None
    ) -> bool:
        """
        Envía un mensaje a WhatsApp.
        
        Args:
            to_number: Número de teléfono destino (formato: 1234567890)
            message_text: Texto del mensaje
            media_url: URL de media (opcional)
            media_type: Tipo de media (image, video, document) (opcional)
            
        Returns:
            True si se envió correctamente, False en caso contrario
        """
        if not self.is_configured:
            print("⚠️ WhatsApp no está configurado. No se puede enviar mensaje.")
            return False
        
        if not REQUESTS_AVAILABLE:
            return False
        
        try:
            url = f"https://graph.facebook.com/v18.0/{self.phone_number_id}/messages"
            
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }
            
            # Construir payload
            payload = {
                "messaging_product": "whatsapp",
                "to": to_number,
            }
            
            if media_url and media_type:
                # Mensaje con media
                payload["type"] = media_type
                payload[media_type] = {
                    "link": media_url
                }
                if message_text:
                    payload[media_type]["caption"] = message_text
            else:
                # Mensaje de texto
                payload["type"] = "text"
                payload["text"] = {
                    "body": message_text
                }
            
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            response.raise_for_status()
            
            print(f"✅ Mensaje enviado a WhatsApp: {to_number}")
            return True
            
        except Exception as e:
            print(f"⚠️ Error enviando mensaje a WhatsApp: {e}")
            return False
    
    def verify_webhook(self, mode: str, token: str, challenge: str) -> Optional[str]:
        """
        Verifica el webhook de WhatsApp (para configuración inicial).
        
        Args:
            mode: Modo de verificación (debe ser "subscribe")
            token: Token recibido
            challenge: Challenge recibido
            
        Returns:
            Challenge si la verificación es exitosa, None en caso contrario
        """
        if mode == "subscribe" and token == self.verify_token:
            return challenge
        return None

