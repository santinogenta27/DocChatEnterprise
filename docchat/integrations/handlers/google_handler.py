"""
Handler para Google (Drive y Gmail)
"""

from __future__ import annotations

from typing import List, Optional
from langchain_core.documents import Document
import requests
import json

from .base_handler import BaseIntegrationHandler


class GoogleHandler(BaseIntegrationHandler):
    """Handler para Google Drive y Gmail."""
    
    def search(self, query: str, access_token: str, max_results: int = 10) -> List[Document]:
        """Busca en Google Drive y Gmail."""
        documents = []
        
        # Buscar en Gmail
        try:
            gmail_docs = self._search_gmail(query, access_token, max_results // 2)
            documents.extend(gmail_docs)
        except Exception as e:
            print(f"Error buscando en Gmail: {e}")
        
        # Buscar en Google Drive
        try:
            drive_docs = self._search_drive(query, access_token, max_results // 2)
            documents.extend(drive_docs)
        except Exception as e:
            print(f"Error buscando en Drive: {e}")
        
        return documents[:max_results]
    
    def _parse_natural_query(self, query: str) -> str:
        """Convierte queries naturales a búsquedas de Gmail."""
        query_lower = query.lower().strip()
        
        # Búsquedas genéricas
        if query_lower in ["que mails tengo", "qué mails tengo", "mails", "emails", "correos", "que correos tengo", "mis emails"]:
            return "in:inbox"
        
        # Búsquedas por tiempo
        from datetime import datetime, timedelta
        today = datetime.now().date()
        
        if any(word in query_lower for word in ["hoy", "today", "de hoy"]):
            return f"after:{today.strftime('%Y/%m/%d')}"
        if any(word in query_lower for word in ["ayer", "yesterday"]):
            yesterday = today - timedelta(days=1)
            return f"after:{yesterday.strftime('%Y/%m/%d')} before:{today.strftime('%Y/%m/%d')}"
        if any(word in query_lower for word in ["esta semana", "this week", "semana"]):
            week_ago = today - timedelta(days=7)
            return f"after:{week_ago.strftime('%Y/%m/%d')}"
        if any(word in query_lower for word in ["este mes", "this month", "mes"]):
            month_ago = today - timedelta(days=30)
            return f"after:{month_ago.strftime('%Y/%m/%d')}"
        
        # Búsquedas por estado
        if any(word in query_lower for word in ["no leídos", "unread", "sin leer"]):
            return "is:unread"
        if any(word in query_lower for word in ["importantes", "important", "importante"]):
            return "is:important"
        if any(word in query_lower for word in ["con adjuntos", "attachments", "archivos adjuntos"]):
            return "has:attachment"
        
        # Búsqueda por remitente (ej: "emails de juan")
        if "de " in query_lower or "from " in query_lower:
            # Extraer nombre después de "de" o "from"
            parts = query_lower.split("de " if "de " in query_lower else "from ")
            if len(parts) > 1:
                sender = parts[-1].strip()
                return f"from:{sender}"
        
        # Si no coincide con ningún patrón, usar búsqueda de texto libre (Gmail busca en todo)
        return query
    
    def _search_gmail(self, query: str, access_token: str, max_results: int) -> List[Document]:
        """Busca en Gmail con búsqueda inteligente."""
        # Validar token primero
        if not access_token or not access_token.strip():
            print("❌ Token de Gmail vacío")
            return []
        
        headers = {"Authorization": f"Bearer {access_token.strip()}"}
        
        # Primero verificar que el token sea válido haciendo una llamada simple
        try:
            profile_url = "https://www.googleapis.com/gmail/v1/users/me/profile"
            profile_response = requests.get(profile_url, headers=headers, timeout=5)
            
            if profile_response.status_code == 401:
                print(f"❌ Token de Gmail inválido o expirado (401 Unauthorized)")
                print(f"💡 Necesitás un token nuevo con scope 'gmail.readonly'")
                return []
            elif profile_response.status_code != 200:
                print(f"⚠️ Error validando token Gmail: {profile_response.status_code}")
                return []
            
            # Token válido, continuar con la búsqueda
            print(f"✅ Token de Gmail válido, buscando mensajes...")
        except Exception as e:
            print(f"⚠️ Error validando token: {e}")
            return []
        
        # Convertir query natural a búsqueda de Gmail
        gmail_query = self._parse_natural_query(query)
        print(f"🔍 Query original: '{query}' → Búsqueda Gmail: '{gmail_query}'")
        
        # Buscar mensajes usando la API de búsqueda de Gmail
        search_url = "https://www.googleapis.com/gmail/v1/users/me/messages"
        params = {"q": gmail_query, "maxResults": max_results}
        
        try:
            print(f"🔍 Gmail API: Buscando '{gmail_query}'...")
            response = requests.get(search_url, headers=headers, params=params, timeout=10)
            
            if response.status_code == 401:
                print(f"❌ Token de Gmail inválido o expirado durante búsqueda (401 Unauthorized)")
                return []
            elif response.status_code != 200:
                error_text = response.text[:500]
                print(f"⚠️ Error en Gmail API: {response.status_code} - {error_text}")
                return []
            
            data = response.json()
            messages = data.get("messages", [])
            if not messages:
                print(f"ℹ️ No se encontraron mensajes en Gmail para: '{gmail_query}'")
                print(f"💡 Tip: Probá con una búsqueda más específica o verifica que tengas emails en tu inbox")
                return []
            
            print(f"📧 Gmail: {len(messages)} mensajes encontrados, procesando...")
            
            documents = []
            
            for msg in messages[:max_results]:
                try:
                    # Obtener mensaje completo
                    msg_url = f"https://www.googleapis.com/gmail/v1/users/me/messages/{msg['id']}"
                    msg_response = requests.get(msg_url, headers=headers, timeout=10)
                    if msg_response.status_code == 200:
                        msg_data = msg_response.json()
                        # Extraer texto del mensaje
                        text = self._extract_gmail_text(msg_data)
                        if text:
                            # Extraer subject y from de headers
                            headers_list = msg_data.get("payload", {}).get("headers", [])
                            subject = next((h.get("value", "") for h in headers_list if h.get("name", "").lower() == "subject"), "Sin asunto")
                            from_email = next((h.get("value", "") for h in headers_list if h.get("name", "").lower() == "from"), "Desconocido")
                            
                            # Extraer fecha
                            date_header = next((h.get("value", "") for h in headers_list if h.get("name", "").lower() == "date"), "")
                            
                            # Crear contenido completo del email para mostrar
                            email_content = f"""ASUNTO: {subject}
DE: {from_email}
FECHA: {date_header}

CONTENIDO:
{text}"""
                            
                            documents.append(Document(
                                page_content=email_content[:10000],  # Aumentar límite para contenido completo
                                metadata={
                                    "source": f"📧 Gmail: {subject}",
                                    "message_id": msg['id'],
                                    "subject": subject,
                                    "from": from_email,
                                    "date": date_header,
                                    "integration": "gmail",
                                    "full_content": text[:5000]  # Contenido completo para respuestas
                                }
                            ))
                except Exception as e:
                    print(f"⚠️ Error procesando mensaje Gmail {msg.get('id', 'unknown')}: {e}")
                    continue
            
            print(f"✅ Gmail: {len(documents)} mensajes encontrados para '{query}'")
            return documents
        except requests.exceptions.RequestException as e:
            print(f"❌ Error de conexión con Gmail API: {e}")
            return []
        except Exception as e:
            print(f"❌ Error inesperado en Gmail: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def _search_drive(self, query: str, access_token: str, max_results: int) -> List[Document]:
        """Busca en Google Drive."""
        headers = {"Authorization": f"Bearer {access_token}"}
        
        search_url = "https://www.googleapis.com/drive/v3/files"
        params = {"q": f"fullText contains '{query}'", "pageSize": max_results}
        
        response = requests.get(search_url, headers=headers, params=params)
        if response.status_code != 200:
            return []
        
        files = response.json().get("files", [])
        documents = []
        
        for file in files[:max_results]:
            try:
                # Obtener contenido del archivo
                file_id = file["id"]
                export_url = f"https://www.googleapis.com/drive/v3/files/{file_id}/export?mimeType=text/plain"
                content_response = requests.get(export_url, headers=headers)
                
                if content_response.status_code == 200:
                    documents.append(Document(
                        page_content=content_response.text[:5000],  # Limitar tamaño
                        metadata={
                            "source": "google_drive",
                            "file_id": file_id,
                            "file_name": file.get("name", ""),
                            "integration": "google_drive"
                        }
                    ))
            except Exception as e:
                print(f"Error procesando archivo Drive: {e}")
        
        return documents
    
    def _extract_gmail_text(self, msg_data: dict) -> str:
        """Extrae texto completo de un mensaje de Gmail."""
        payload = msg_data.get("payload", {})
        
        # Si tiene partes (multipart)
        parts = payload.get("parts", [])
        if parts:
            text = ""
            html_text = ""
            
            for part in parts:
                mime_type = part.get("mimeType", "")
                body = part.get("body", {})
                data = body.get("data", "")
                
                if data:
                    import base64
                    try:
                        decoded = base64.b64decode(data).decode('utf-8', errors='ignore')
                        
                        if mime_type == "text/plain":
                            text += decoded + "\n\n"
                        elif mime_type == "text/html":
                            html_text += decoded
                    except Exception as e:
                        print(f"⚠️ Error decodificando parte del email: {e}")
                        continue
                
                # Si hay sub-partes (nested)
                sub_parts = part.get("parts", [])
                for sub_part in sub_parts:
                    sub_mime = sub_part.get("mimeType", "")
                    sub_body = sub_part.get("body", {})
                    sub_data = sub_body.get("data", "")
                    
                    if sub_data:
                        try:
                            decoded = base64.b64decode(sub_data).decode('utf-8', errors='ignore')
                            if sub_mime == "text/plain":
                                text += decoded + "\n\n"
                            elif sub_mime == "text/html":
                                html_text += decoded
                        except Exception:
                            continue
            
            # Preferir texto plano, pero si no hay, usar HTML (sin tags)
            if text.strip():
                return text.strip()
            elif html_text:
                # Extraer texto básico de HTML (simple)
                import re
                text_only = re.sub(r'<[^>]+>', ' ', html_text)
                text_only = re.sub(r'\s+', ' ', text_only)
                return text_only.strip()
        
        # Si no tiene partes, buscar directamente en body
        body = payload.get("body", {})
        data = body.get("data", "")
        if data:
            try:
                import base64
                return base64.b64decode(data).decode('utf-8', errors='ignore')
            except Exception:
                pass
        
        return ""
    
    def refresh_token(self, refresh_token: str) -> Optional[str]:
        """Refresca token de Google."""
        client_id = getattr(self.config, 'google_client_id', '')
        client_secret = getattr(self.config, 'google_client_secret', '')
        
        data = {
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token"
        }
        
        response = requests.post("https://oauth2.googleapis.com/token", data=data)
        if response.status_code == 200:
            return response.json().get("access_token")
        return None
    
    def send_email(
        self,
        access_token: str,
        to: str,
        subject: str,
        body: str,
        reply_to_message_id: Optional[str] = None
    ) -> bool:
        """
        Envía un email o responde a uno existente.
        
        Args:
            access_token: Token de acceso
            to: Email del destinatario
            subject: Asunto
            body: Cuerpo del mensaje
            reply_to_message_id: ID del mensaje al que se responde (opcional)
        
        Returns:
            True si se envió correctamente
        """
        headers = {"Authorization": f"Bearer {access_token.strip()}"}
        
        # Construir mensaje
        message = f"To: {to}\r\n"
        message += f"Subject: {subject}\r\n"
        if reply_to_message_id:
            message += f"In-Reply-To: {reply_to_message_id}\r\n"
            message += f"References: {reply_to_message_id}\r\n"
        message += "\r\n" + body
        
        # Codificar en base64url (no base64 estándar)
        import base64
        message_bytes = message.encode('utf-8')
        message_b64 = base64.urlsafe_b64encode(message_bytes).decode('utf-8')
        
        # Preparar payload
        payload = {
            "raw": message_b64
        }
        
        if reply_to_message_id:
            payload["threadId"] = reply_to_message_id  # Gmail usa threadId para respuestas
        
        try:
            send_url = "https://www.googleapis.com/gmail/v1/users/me/messages/send"
            response = requests.post(
                send_url,
                headers=headers,
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                print(f"✅ Email enviado correctamente a {to}")
                return True
            else:
                print(f"❌ Error enviando email: {response.status_code} - {response.text[:200]}")
                return False
        except Exception as e:
            print(f"❌ Error enviando email: {e}")
            return False

