"""
Omnicanal Bridge - ConexiÃ³n real con WhatsApp, Facebook, Instagram
Prepara la estructura para integraciÃ³n omnicanal real
"""

from __future__ import annotations

from typing import Dict, Optional, Any, List
from enum import Enum
from dataclasses import dataclass
from datetime import datetime


class Channel(Enum):
    """Canales omnicanales soportados."""
    WEB = "web"  # Widget web (ya implementado)
    WHATSAPP = "whatsapp"
    FACEBOOK = "facebook"
    INSTAGRAM = "instagram"
    MESSENGER = "messenger"  # Facebook Messenger


@dataclass
class IncomingMessage:
    """Mensaje entrante desde cualquier canal."""
    channel: Channel
    sender_id: str  # ID del remitente en el canal especÃ­fico
    message_text: str
    timestamp: datetime
    metadata: Dict[str, Any] = None


@dataclass
class OutgoingMessage:
    """Mensaje saliente a cualquier canal."""
    channel: Channel
    recipient_id: str
    message_text: str
    metadata: Dict[str, Any] = None


class OmnicanalBridge:
    """
    Puente omnicanal para conectar con WhatsApp, Facebook, Instagram.
    
    Esta clase prepara la estructura para integraciÃ³n real con:
    - WhatsApp Business API (via Twilio o Meta)
    - Facebook Messenger Platform
    - Instagram Direct Messages
    """
    
    def __init__(self):
        """Inicializa el puente omnicanal."""
        self.whatsapp_config = None
        self.facebook_config = None
        self.instagram_config = None
    
    def configure_whatsapp(self, provider: str = "twilio", **kwargs):
        """
        Configura WhatsApp Business API.
        
        Args:
            provider: "twilio" o "meta"
            **kwargs: ConfiguraciÃ³n especÃ­fica del proveedor
        """
        self.whatsapp_config = {
            "provider": provider,
            **kwargs
        }
        print(f"âœ… WhatsApp configurado: {provider}")
    
    def configure_facebook(self, page_access_token: str, verify_token: str):
        """
        Configura Facebook Messenger Platform.
        
        Args:
            page_access_token: Token de acceso de la pÃ¡gina de Facebook
            verify_token: Token de verificaciÃ³n para webhook
        """
        self.facebook_config = {
            "page_access_token": page_access_token,
            "verify_token": verify_token
        }
        print("âœ… Facebook Messenger configurado")
    
    def configure_instagram(self, access_token: str, ig_user_id: Optional[str] = None):
        """
        Configura Instagram Direct Messages.
        
        Args:
            access_token: Token de acceso de Instagram
            ig_user_id: ID de usuario de Instagram Business Account (opcional)
        """
        self.instagram_config = {
            "access_token": access_token,
            "ig_user_id": ig_user_id
        }
        print(f"âœ… Instagram Direct configurado (User ID: {ig_user_id or 'N/A'})")
    
    def send_message(self, message: OutgoingMessage) -> bool:
        """
        EnvÃ­a un mensaje a travÃ©s del canal especificado.
        
        Args:
            message: Mensaje a enviar
            
        Returns:
            True si se enviÃ³ correctamente
        """
        try:
            if message.channel == Channel.WHATSAPP:
                return self._send_whatsapp(message)
            elif message.channel == Channel.FACEBOOK or message.channel == Channel.MESSENGER:
                return self._send_facebook(message)
            elif message.channel == Channel.INSTAGRAM:
                return self._send_instagram(message)
            elif message.channel == Channel.WEB:
                # Web ya estÃ¡ implementado en api_server.py
                return True
            else:
                print(f"âš ï¸ Canal no soportado: {message.channel}")
                return False
        except Exception as e:
            print(f"âŒ Error enviando mensaje: {e}")
            return False
    
    def _send_whatsapp(self, message: OutgoingMessage) -> bool:
        """EnvÃ­a mensaje por WhatsApp."""
        if not self.whatsapp_config:
            print("âš ï¸ WhatsApp no configurado")
            return False
        
        provider = self.whatsapp_config.get("provider", "twilio")
        
        if provider == "twilio":
            try:
                from twilio.rest import Client
                account_sid = self.whatsapp_config.get("account_sid")
                auth_token = self.whatsapp_config.get("auth_token")
                from_number = self.whatsapp_config.get("from_number")
                
                if not all([account_sid, auth_token, from_number]):
                    print("âš ï¸ Credenciales de Twilio incompletas")
                    return False
                
                client = Client(account_sid, auth_token)
                twilio_message = client.messages.create(
                    from_=f'whatsapp:{from_number}',
                    to=f'whatsapp:{message.recipient_id}',
                    body=message.message_text
                )
                print(f"âœ… [WhatsApp/Twilio] Mensaje enviado (SID: {twilio_message.sid}) a {message.recipient_id}")
                return True
            except ImportError:
                print("âš ï¸ Twilio no instalado. Instala con: pip install twilio")
                return False
            except Exception as e:
                print(f"âŒ Error enviando WhatsApp/Twilio: {e}")
                return False
        elif provider == "meta":
            try:
                import requests
                phone_number_id = self.whatsapp_config.get("phone_number_id")
                access_token = self.whatsapp_config.get("access_token")
                
                if not all([phone_number_id, access_token]):
                    print("âš ï¸ Credenciales de Meta WhatsApp incompletas")
                    return False
                
                url = f"https://graph.facebook.com/v18.0/{phone_number_id}/messages"
                headers = {
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json"
                }
                payload = {
                    "messaging_product": "whatsapp",
                    "to": message.recipient_id,
                    "type": "text",
                    "text": {"body": message.message_text}
                }
                
                response = requests.post(url, json=payload, headers=headers, timeout=10)
                response.raise_for_status()
                result = response.json()
                print(f"âœ… [WhatsApp/Meta] Mensaje enviado a {message.recipient_id} (Message ID: {result.get('messages', [{}])[0].get('id')})")
                return True
            except ImportError:
                print("âš ï¸ requests no instalado. Instala con: pip install requests")
                return False
            except Exception as e:
                print(f"âŒ Error enviando WhatsApp/Meta: {e}")
                return False
        
        return False
    
    def _send_facebook(self, message: OutgoingMessage) -> bool:
        """EnvÃ­a mensaje por Facebook Messenger."""
        if not self.facebook_config:
            print("âš ï¸ Facebook Messenger no configurado")
            return False
        
        try:
            import requests
            page_access_token = self.facebook_config.get("page_access_token")
            
            if not page_access_token:
                print("âš ï¸ Token de acceso de Facebook Messenger no configurado")
                return False
            
            url = "https://graph.facebook.com/v18.0/me/messages"
            params = {"access_token": page_access_token}
            payload = {
                "recipient": {"id": message.recipient_id},
                "message": {"text": message.message_text}
            }
            
            response = requests.post(url, params=params, json=payload, timeout=10)
            response.raise_for_status()
            result = response.json()
            print(f"âœ… [Facebook Messenger] Mensaje enviado a {message.recipient_id} (Message ID: {result.get('message_id')})")
            return True
        except ImportError:
            print("âš ï¸ requests no instalado. Instala con: pip install requests")
            return False
        except Exception as e:
            print(f"âŒ Error enviando Facebook Messenger: {e}")
            return False
    
    def _send_instagram(self, message: OutgoingMessage) -> bool:
        """EnvÃ­a mensaje por Instagram Direct."""
        if not self.instagram_config:
            print("âš ï¸ Instagram no configurado")
            return False
        
        try:
            import requests
            access_token = self.instagram_config.get("access_token")
            ig_user_id = self.instagram_config.get("ig_user_id")  # Instagram Business Account ID
            
            if not access_token:
                print("âš ï¸ Token de acceso de Instagram no configurado")
                return False
            
            # Instagram usa el mismo endpoint que Messenger pero con el ID de usuario de Instagram
            url = f"https://graph.facebook.com/v18.0/{ig_user_id or message.recipient_id}/messages"
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            payload = {
                "recipient": {"id": message.recipient_id},
                "message": {"text": message.message_text}
            }
            
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            response.raise_for_status()
            result = response.json()
            print(f"âœ… [Instagram Direct] Mensaje enviado a {message.recipient_id} (Message ID: {result.get('message_id')})")
            return True
        except ImportError:
            print("âš ï¸ requests no instalado. Instala con: pip install requests")
            return False
        except Exception as e:
            print(f"âŒ Error enviando Instagram Direct: {e}")
            return False
    
    def process_webhook(self, channel: Channel, payload: Dict[str, Any]) -> Optional[IncomingMessage]:
        """
        Procesa un webhook entrante desde un canal externo.
        
        Args:
            channel: Canal de origen
            payload: Datos del webhook
            
        Returns:
            IncomingMessage si se procesa correctamente, None si hay error
        """
        try:
            if channel == Channel.WHATSAPP:
                return self._process_whatsapp_webhook(payload)
            elif channel == Channel.FACEBOOK or channel == Channel.MESSENGER:
                return self._process_facebook_webhook(payload)
            elif channel == Channel.INSTAGRAM:
                return self._process_instagram_webhook(payload)
            else:
                print(f"âš ï¸ Canal no soportado: {channel}")
                return None
        except Exception as e:
            print(f"âŒ Error procesando webhook: {e}")
            return None
    
    def _process_whatsapp_webhook(self, payload: Dict[str, Any]) -> Optional[IncomingMessage]:
        """Procesa webhook de WhatsApp."""
        provider = self.whatsapp_config.get("provider", "twilio") if self.whatsapp_config else "twilio"
        
        try:
            if provider == "twilio":
                # Formato Twilio
                sender_id = payload.get("From", "").replace("whatsapp:", "")
                message_text = payload.get("Body", "")
                
                if sender_id and message_text:
                    return IncomingMessage(
                        channel=Channel.WHATSAPP,
                        sender_id=sender_id,
                        message_text=message_text,
                        timestamp=datetime.now(),
                        metadata={"provider": "twilio", "message_sid": payload.get("MessageSid")}
                    )
            elif provider == "meta":
                # Formato Meta WhatsApp Business API
                entry = payload.get("entry", [{}])[0]
                changes = entry.get("changes", [{}])[0]
                value = changes.get("value", {})
                messages = value.get("messages", [{}])
                
                if messages:
                    message_data = messages[0]
                    sender_id = value.get("contacts", [{}])[0].get("wa_id", "") or message_data.get("from", "")
                    message_text = message_data.get("text", {}).get("body", "")
                    
                    if sender_id and message_text:
                        return IncomingMessage(
                            channel=Channel.WHATSAPP,
                            sender_id=sender_id,
                            message_text=message_text,
                            timestamp=datetime.now(),
                            metadata={
                                "provider": "meta",
                                "message_id": message_data.get("id"),
                                "timestamp": message_data.get("timestamp")
                            }
                        )
            
            print(f"âš ï¸ [WhatsApp Webhook] No se pudo parsear mensaje: {payload}")
            return None
        except Exception as e:
            print(f"âŒ Error procesando webhook de WhatsApp: {e}")
            return None
    
    def _process_facebook_webhook(self, payload: Dict[str, Any]) -> Optional[IncomingMessage]:
        """Procesa webhook de Facebook Messenger."""
        try:
            # Formato Facebook Messenger Platform
            entry = payload.get("entry", [{}])[0]
            messaging = entry.get("messaging", [{}])[0]
            
            # Verificar que sea un mensaje de texto (no postback, delivery, etc.)
            if "message" not in messaging:
                return None
            
            sender_id = messaging.get("sender", {}).get("id")
            message_data = messaging.get("message", {})
            message_text = message_data.get("text", "")
            
            if sender_id and message_text:
                return IncomingMessage(
                    channel=Channel.FACEBOOK,
                    sender_id=sender_id,
                    message_text=message_text,
                    timestamp=datetime.now(),
                    metadata={
                        "message_id": message_data.get("mid"),
                        "timestamp": messaging.get("timestamp")
                    }
                )
            
            print(f"âš ï¸ [Facebook Webhook] No se pudo parsear mensaje: {payload}")
            return None
        except Exception as e:
            print(f"âŒ Error procesando webhook de Facebook: {e}")
            return None
    
    def _process_instagram_webhook(self, payload: Dict[str, Any]) -> Optional[IncomingMessage]:
        """Procesa webhook de Instagram Direct."""
        try:
            # Instagram usa formato similar a Facebook Messenger
            entry = payload.get("entry", [{}])[0]
            messaging = entry.get("messaging", [{}])[0]
            
            if "message" not in messaging:
                return None
            
            sender_id = messaging.get("sender", {}).get("id")
            message_data = messaging.get("message", {})
            message_text = message_data.get("text", "")
            
            if sender_id and message_text:
                return IncomingMessage(
                    channel=Channel.INSTAGRAM,
                    sender_id=sender_id,
                    message_text=message_text,
                    timestamp=datetime.now(),
                    metadata={
                        "message_id": message_data.get("mid"),
                        "timestamp": messaging.get("timestamp")
                    }
                )
            
            print(f"âš ï¸ [Instagram Webhook] No se pudo parsear mensaje: {payload}")
            return None
        except Exception as e:
            print(f"âŒ Error procesando webhook de Instagram: {e}")
            return None


