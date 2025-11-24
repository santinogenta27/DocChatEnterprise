"""WhatsApp tool for customer service automation."""

from __future__ import annotations

import requests
from typing import Any, Dict, List, Optional
import os
import json

from .base_tool import BaseTool, ToolResult


class WhatsAppTool(BaseTool):
    """Tool for sending WhatsApp messages via API (Twilio, WhatsApp Business API, etc.)."""
    
    def __init__(self, config: Any):
        super().__init__(config)
        # Configuración para WhatsApp Business API (gratis con Twilio trial)
        self.twilio_account_sid = os.getenv("TWILIO_ACCOUNT_SID", "")
        self.twilio_auth_token = os.getenv("TWILIO_AUTH_TOKEN", "")
        self.whatsapp_from = os.getenv("WHATSAPP_FROM", "")  # Formato: whatsapp:+14155238886
        
        # Alternativa: WhatsApp Business API directa
        self.whatsapp_api_key = os.getenv("WHATSAPP_API_KEY", "")
        self.whatsapp_api_url = os.getenv("WHATSAPP_API_URL", "")
    
    def get_name(self) -> str:
        return "whatsapp_sender"
    
    def get_description(self) -> str:
        return "Send WhatsApp messages to customers for support, notifications, or responses"
    
    def get_keywords(self) -> List[str]:
        return ["whatsapp", "wa", "mensaje whatsapp", "enviar whatsapp", "whatsapp business"]
    
    def execute(
        self,
        to: str,
        message: str,
        media_url: Optional[str] = None,
        **kwargs
    ) -> ToolResult:
        """Send a WhatsApp message."""
        try:
            # Validar destinatario (formato: whatsapp:+1234567890)
            if not to.startswith("whatsapp:+"):
                to = f"whatsapp:+{to.lstrip('+')}"
            
            # Intentar con Twilio primero (gratis en trial)
            if self.twilio_account_sid and self.twilio_auth_token:
                return self._send_via_twilio(to, message, media_url)
            
            # Intentar con WhatsApp Business API directa
            if self.whatsapp_api_key and self.whatsapp_api_url:
                return self._send_via_api(to, message, media_url)
            
            # Si no hay configuración, simular envío (para desarrollo)
            return ToolResult(
                success=True,
                data={"to": to, "message": message[:50] + "..."},
                message=f"WhatsApp message prepared (simulated - configure Twilio or WhatsApp API)",
                metadata={"simulated": True, "note": "Configure TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN for real sending"}
            )
        
        except Exception as e:
            return ToolResult(
                success=False,
                data=None,
                message=f"Failed to send WhatsApp message: {str(e)}",
                metadata={"error": str(e)}
            )
    
    def _send_via_twilio(self, to: str, message: str, media_url: Optional[str] = None) -> ToolResult:
        """Send via Twilio WhatsApp API."""
        try:
            url = f"https://api.twilio.com/2010-04-01/Accounts/{self.twilio_account_sid}/Messages.json"
            
            data = {
                "From": self.whatsapp_from or f"whatsapp:+14155238886",  # Twilio sandbox
                "To": to,
                "Body": message
            }
            
            if media_url:
                data["MediaUrl"] = media_url
            
            response = requests.post(
                url,
                auth=(self.twilio_account_sid, self.twilio_auth_token),
                data=data,
                timeout=10
            )
            
            if response.status_code == 201:
                return ToolResult(
                    success=True,
                    data=response.json(),
                    message=f"WhatsApp message sent successfully to {to}",
                    metadata={"provider": "twilio", "status": "sent"}
                )
            else:
                return ToolResult(
                    success=False,
                    data=None,
                    message=f"Twilio API error: {response.status_code} - {response.text}",
                    metadata={"provider": "twilio", "status_code": response.status_code}
                )
        
        except Exception as e:
            return ToolResult(
                success=False,
                data=None,
                message=f"Twilio API error: {str(e)}",
                metadata={"provider": "twilio", "error": str(e)}
            )
    
    def _send_via_api(self, to: str, message: str, media_url: Optional[str] = None) -> ToolResult:
        """Send via WhatsApp Business API directa."""
        try:
            headers = {
                "Authorization": f"Bearer {self.whatsapp_api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "to": to,
                "message": message,
                "type": "text"
            }
            
            if media_url:
                payload["media_url"] = media_url
                payload["type"] = "media"
            
            response = requests.post(
                self.whatsapp_api_url,
                headers=headers,
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                return ToolResult(
                    success=True,
                    data=response.json(),
                    message=f"WhatsApp message sent successfully to {to}",
                    metadata={"provider": "whatsapp_api", "status": "sent"}
                )
            else:
                return ToolResult(
                    success=False,
                    data=None,
                    message=f"WhatsApp API error: {response.status_code} - {response.text}",
                    metadata={"provider": "whatsapp_api", "status_code": response.status_code}
                )
        
        except Exception as e:
            return ToolResult(
                success=False,
                data=None,
                message=f"WhatsApp API error: {str(e)}",
                metadata={"provider": "whatsapp_api", "error": str(e)}
            )

