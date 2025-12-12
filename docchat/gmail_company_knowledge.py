"""
Gmail Company Knowledge - Sistema de consulta y respuestas masivas de emails
Extiende Company Knowledge para trabajar específicamente con emails de Gmail.

Funcionalidades:
- Cargar emails de Gmail como documentos en Company Knowledge
- Hacer preguntas sobre emails recibidos
- Responder automáticamente a múltiples emails con respuestas personalizadas
"""

from __future__ import annotations

import json
import time
import base64
import re
from typing import List, Dict, Optional, Any, Tuple
from pathlib import Path
from datetime import datetime
import requests

from langchain_core.documents import Document

from .config import AppConfig
from .company_knowledge import CompanyKnowledge
from .company_knowledge_integrations import CompanyKnowledgeIntegrations, IntegrationType


class GmailCompanyKnowledge:
    """
    Sistema de conocimiento empresarial especializado en emails de Gmail.
    
    Permite:
    1. Cargar emails de Gmail como documentos consultables
    2. Hacer preguntas sobre emails recibidos
    3. Responder automáticamente a múltiples emails con respuestas personalizadas
    """
    
    def __init__(
        self,
        company_knowledge: CompanyKnowledge,
        integrations: CompanyKnowledgeIntegrations,
        config: AppConfig
    ):
        self.company_knowledge = company_knowledge
        self.integrations = integrations
        self.config = config
        
        # Directorio para almacenar emails indexados
        self.data_dir = Path(config.memory_dir) / "gmail_knowledge"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Cache de emails indexados por sesión
        self.indexed_emails: Dict[str, List[str]] = {}  # session_id -> [email_ids]
        
        # Configuración de respuestas masivas
        self.mass_response_templates: Dict[str, Dict[str, Any]] = {}
        self.mass_response_history_file = self.data_dir / "mass_response_history.json"
        
        # Cargar plantillas guardadas
        self._load_templates()
    
    def get_gmail_connection(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Obtiene la conexión activa de Gmail."""
        connected_apps = self.integrations.get_connected_apps()
        gmail_apps = [app for app in connected_apps if app.app_type == IntegrationType.GMAIL]
        
        if not gmail_apps:
            return None
        
        # Obtener token del cache
        latest_app = sorted(gmail_apps, key=lambda x: x.connected_at or "", reverse=True)[0]
        access_token = self.integrations.get_access_token_for_app(latest_app.connection_id)
        
        if not access_token:
            return None
        
        return {
            "connection_id": latest_app.connection_id,
            "access_token": access_token,
            "app_name": latest_app.app_name
        }
    
    def load_emails_from_gmail(
        self,
        session_id: str,
        query: str = "in:inbox",
        max_results: int = 50,
        mark_as_read: bool = False
    ) -> Dict[str, Any]:
        """
        Carga emails de Gmail y los convierte en documentos para Company Knowledge.
        
        Args:
            session_id: ID de sesión de Company Knowledge
            query: Query de búsqueda de Gmail (ej: "is:unread", "from:juan@example.com", etc.)
            max_results: Máximo de emails a cargar
            mark_as_read: Si True, marca los emails como leídos después de cargarlos
        
        Returns:
            Dict con status y estadísticas
        """
        # Obtener conexión de Gmail
        gmail_conn = self.get_gmail_connection(session_id)
        if not gmail_conn:
            return {
                "status": "error",
                "error": "No hay conexión activa de Gmail. Conecta Gmail primero en el tab 'Conectar Apps'"
            }
        
        access_token = gmail_conn["access_token"]
        
        try:
            print(f"📧 [Gmail Knowledge] Cargando emails con query: '{query}'")
            
            # Buscar mensajes
            search_url = "https://www.googleapis.com/gmail/v1/users/me/messages"
            headers = {"Authorization": f"Bearer {access_token}"}
            params = {"q": query, "maxResults": max_results}
            
            response = requests.get(search_url, headers=headers, params=params, timeout=15)
            
            if response.status_code == 401:
                return {
                    "status": "error",
                    "error": "Token de Gmail inválido o expirado. Re-conecta Gmail."
                }
            elif response.status_code != 200:
                return {
                    "status": "error",
                    "error": f"Error buscando emails: {response.status_code} - {response.text[:200]}"
                }
            
            data = response.json()
            messages = data.get("messages", [])
            
            if not messages:
                return {
                    "status": "success",
                    "loaded": 0,
                    "message": f"No se encontraron emails con la query: '{query}'"
                }
            
            print(f"📧 [Gmail Knowledge] {len(messages)} emails encontrados, procesando...")
            
            # Procesar cada email
            documents = []
            email_metadata = []
            
            for msg in messages[:max_results]:
                try:
                    msg_id = msg["id"]
                    
                    # Obtener mensaje completo
                    msg_url = f"https://www.googleapis.com/gmail/v1/users/me/messages/{msg_id}"
                    msg_response = requests.get(
                        msg_url,
                        headers=headers,
                        params={"format": "full"},
                        timeout=10
                    )
                    
                    if msg_response.status_code != 200:
                        continue
                    
                    msg_data = msg_response.json()
                    payload = msg_data.get("payload", {})
                    headers_list = payload.get("headers", [])
                    
                    # Extraer información básica
                    subject = next((h.get("value", "") for h in headers_list if h.get("name", "").lower() == "subject"), "Sin asunto")
                    from_email = next((h.get("value", "") for h in headers_list if h.get("name", "").lower() == "from"), "Desconocido")
                    to_email = next((h.get("value", "") for h in headers_list if h.get("name", "").lower() == "to"), "")
                    date_header = next((h.get("value", "") for h in headers_list if h.get("name", "").lower() == "date"), "")
                    
                    # Extraer cuerpo del email
                    body_text = self._extract_email_body(payload)
                    
                    # Crear documento para Company Knowledge
                    email_content = f"""EMAIL DE GMAIL
                    
ASUNTO: {subject}
DE: {from_email}
PARA: {to_email}
FECHA: {date_header}
MESSAGE_ID: {msg_id}

CONTENIDO:
{body_text}"""
                    
                    doc = Document(
                        page_content=email_content[:50000],  # Limitar tamaño
                        metadata={
                            "source": f"📧 Gmail: {subject}",
                            "email_id": msg_id,
                            "subject": subject,
                            "from": from_email,
                            "to": to_email,
                            "date": date_header,
                            "integration": "gmail",
                            "thread_id": msg_data.get("threadId", ""),
                            "snippet": msg_data.get("snippet", "")[:500]
                        }
                    )
                    
                    documents.append(doc)
                    
                    email_metadata.append({
                        "id": msg_id,
                        "subject": subject,
                        "from": from_email,
                        "date": date_header,
                        "thread_id": msg_data.get("threadId", "")
                    })
                    
                    # Marcar como leído si se solicita
                    if mark_as_read:
                        try:
                            modify_url = f"https://www.googleapis.com/gmail/v1/users/me/messages/{msg_id}/modify"
                            requests.post(
                                modify_url,
                                headers=headers,
                                json={"removeLabelIds": ["UNREAD"]},
                                timeout=5
                            )
                        except Exception:
                            pass  # No crítico si falla
                    
                except Exception as e:
                    print(f"⚠️ [Gmail Knowledge] Error procesando email {msg.get('id', 'unknown')}: {e}")
                    continue
            
            # Cargar documentos en Company Knowledge
            if documents:
                # Crear archivos temporales simulados para procesar
                # Company Knowledge espera archivos, pero podemos agregar directamente a la sesión
                session = self.company_knowledge.initialize_session(session_id)
                
                # Agregar documentos directamente a la sesión
                session["docs"].extend(documents)
                
                # Reconstruir retriever
                if session["docs"]:
                    session["retriever"] = self.company_knowledge.retriever_builder.build_hybrid_retriever(session["docs"])
                
                # Registrar emails indexados
                if session_id not in self.indexed_emails:
                    self.indexed_emails[session_id] = []
                self.indexed_emails[session_id].extend([e["id"] for e in email_metadata])
                
                print(f"✅ [Gmail Knowledge] {len(documents)} emails cargados como documentos")
            
            return {
                "status": "success",
                "loaded": len(documents),
                "total_found": len(messages),
                "emails": email_metadata,
                "message": f"✅ {len(documents)} emails cargados exitosamente"
            }
            
        except Exception as e:
            print(f"❌ [Gmail Knowledge] Error cargando emails: {e}")
            import traceback
            traceback.print_exc()
            return {
                "status": "error",
                "error": str(e)
            }
    
    def _extract_email_body(self, payload: Dict) -> str:
        """Extrae el cuerpo del email desde payload de Gmail."""
        body = ""
        
        # Si tiene partes (multipart)
        parts = payload.get("parts", [])
        if parts:
            text = ""
            html_text = ""
            
            for part in parts:
                mime_type = part.get("mimeType", "")
                body_data = part.get("body", {})
                data = body_data.get("data", "")
                
                if data:
                    try:
                        decoded = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
                        
                        if mime_type == "text/plain":
                            text += decoded + "\n\n"
                        elif mime_type == "text/html":
                            html_text += decoded
                    except Exception:
                        continue
                
                # Si hay sub-partes (nested)
                sub_parts = part.get("parts", [])
                for sub_part in sub_parts:
                    sub_mime = sub_part.get("mimeType", "")
                    sub_body = sub_part.get("body", {})
                    sub_data = sub_body.get("data", "")
                    
                    if sub_data:
                        try:
                            decoded = base64.urlsafe_b64decode(sub_data).decode('utf-8', errors='ignore')
                            if sub_mime == "text/plain":
                                text += decoded + "\n\n"
                            elif sub_mime == "text/html":
                                html_text += decoded
                        except Exception:
                            continue
            
            # Preferir texto plano, pero si no hay, usar HTML (sin tags)
            if text.strip():
                body = text.strip()
            elif html_text:
                # Extraer texto básico de HTML (simple)
                text_only = re.sub(r'<[^>]+>', ' ', html_text)
                text_only = re.sub(r'\s+', ' ', text_only)
                body = text_only.strip()
        
        # Si no tiene partes, buscar directamente en body
        if not body:
            body_data = payload.get("body", {})
            data = body_data.get("data", "")
            if data:
                try:
                    body = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
                except Exception:
                    pass
        
        return body
    
    async def query_emails(
        self,
        session_id: str,
        question: str,
        history: List[Tuple[str, str]] = None
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Hace una pregunta sobre los emails cargados en Company Knowledge.
        
        Args:
            session_id: ID de sesión
            question: Pregunta sobre los emails
            history: Historial de conversación
        
        Returns:
            (answer, metadata): Respuesta y metadatos
        """
        if history is None:
            history = []
        
        # Verificar que hay emails cargados
        session = self.company_knowledge.initialize_session(session_id)
        if not session.get("docs"):
            return (
                "⚠️ No hay emails cargados. Primero carga emails usando 'Cargar Emails de Gmail'.",
                {}
            )
        
        # Construir pregunta enriquecida
        enriched_question = f"""PREGUNTA SOBRE EMAILS DE GMAIL:

{question}

NOTA: Los documentos disponibles son emails de Gmail cargados previamente. 
Responde basándote en el contenido de esos emails."""
        
        # Procesar query usando Company Knowledge
        try:
            new_history, error, metadata = await self.company_knowledge.process_query_async(
                session_id=session_id,
                message=enriched_question,
                history=history,
                speed_mode="balanced",
                provider="openai"
            )
            
            if error:
                return error, metadata
            
            # Obtener la última respuesta
            if new_history and len(new_history) > 0:
                answer = new_history[-1][1]  # (user, assistant)
                return answer, metadata
            else:
                return "No se pudo generar respuesta.", {}
                
        except Exception as e:
            return f"Error procesando pregunta: {str(e)}", {}
    
    def create_mass_response_template(
        self,
        template_name: str,
        subject_template: str,
        body_template: str,
        conditions: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Crea una plantilla de respuesta masiva.
        
        Args:
            template_name: Nombre de la plantilla
            subject_template: Plantilla del asunto (puede usar {subject}, {from}, {date})
            body_template: Plantilla del cuerpo (puede usar {subject}, {from}, {date}, {body})
            conditions: Condiciones para aplicar la respuesta (query de Gmail)
        
        Returns:
            Dict con status
        """
        template = {
            "name": template_name,
            "subject_template": subject_template,
            "body_template": body_template,
            "conditions": conditions or {},
            "created_at": datetime.now().isoformat(),
            "used_count": 0
        }
        
        self.mass_response_templates[template_name] = template
        
        # Guardar en disco
        self._save_templates()
        
        return {
            "status": "success",
            "message": f"✅ Plantilla '{template_name}' creada exitosamente",
            "template": template
        }
    
    def send_mass_responses(
        self,
        session_id: str,
        template_name: str,
        query: str = "in:inbox is:unread",
        max_emails: int = 50,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        Envía respuestas masivas usando una plantilla.
        
        Args:
            session_id: ID de sesión
            template_name: Nombre de la plantilla a usar
            query: Query de Gmail para buscar emails
            max_emails: Máximo de emails a procesar
            dry_run: Si True, no envía realmente, solo muestra qué se enviaría
        
        Returns:
            Dict con resultados
        """
        # Verificar plantilla
        template = self.mass_response_templates.get(template_name)
        if not template:
            return {
                "status": "error",
                "error": f"Plantilla '{template_name}' no encontrada"
            }
        
        # Obtener conexión de Gmail
        gmail_conn = self.get_gmail_connection(session_id)
        if not gmail_conn:
            return {
                "status": "error",
                "error": "No hay conexión activa de Gmail"
            }
        
        access_token = gmail_conn["access_token"]
        
        try:
            # Buscar emails
            search_url = "https://www.googleapis.com/gmail/v1/users/me/messages"
            headers = {"Authorization": f"Bearer {access_token}"}
            params = {"q": query, "maxResults": max_emails}
            
            response = requests.get(search_url, headers=headers, params=params, timeout=15)
            
            if response.status_code != 200:
                return {
                    "status": "error",
                    "error": f"Error buscando emails: {response.status_code}"
                }
            
            messages = response.json().get("messages", [])
            
            if not messages:
                return {
                    "status": "success",
                    "sent": 0,
                    "message": f"No se encontraron emails con la query: '{query}'"
                }
            
            results = []
            sent_count = 0
            error_count = 0
            
            for msg in messages[:max_emails]:
                try:
                    msg_id = msg["id"]
                    
                    # Obtener mensaje completo
                    msg_url = f"https://www.googleapis.com/gmail/v1/users/me/messages/{msg_id}"
                    msg_response = requests.get(
                        msg_url,
                        headers=headers,
                        params={"format": "full"},
                        timeout=10
                    )
                    
                    if msg_response.status_code != 200:
                        error_count += 1
                        continue
                    
                    msg_data = msg_response.json()
                    payload = msg_data.get("payload", {})
                    headers_list = payload.get("headers", [])
                    
                    # Extraer información
                    subject = next((h.get("value", "") for h in headers_list if h.get("name", "").lower() == "subject"), "Sin asunto")
                    from_email = next((h.get("value", "") for h in headers_list if h.get("name", "").lower() == "from"), "Desconocido")
                    date_header = next((h.get("value", "") for h in headers_list if h.get("name", "").lower() == "date"), "")
                    body_text = self._extract_email_body(payload)
                    
                    # Extraer dirección de email del remitente
                    sender_email = self._extract_email_address(from_email)
                    if not sender_email:
                        error_count += 1
                        results.append({
                            "email_id": msg_id,
                            "status": "error",
                            "reason": "No se pudo extraer dirección de email"
                        })
                        continue
                    
                    # Aplicar plantilla
                    reply_subject = template["subject_template"].format(
                        subject=subject,
                        from_email=from_email,
                        sender=sender_email,
                        date=date_header
                    )
                    
                    reply_body = template["body_template"].format(
                        subject=subject,
                        from_email=from_email,
                        sender=sender_email,
                        date=date_header,
                        body=body_text[:1000]  # Limitar para plantilla
                    )
                    
                    if dry_run:
                        results.append({
                            "email_id": msg_id,
                            "status": "dry_run",
                            "to": sender_email,
                            "subject": reply_subject,
                            "body_preview": reply_body[:200]
                        })
                    else:
                        # Obtener threadId del mensaje original
                        thread_id = msg_data.get("threadId")
                        
                        # Enviar respuesta
                        success = self._send_gmail_reply(
                            access_token=access_token,
                            to=sender_email,
                            subject=reply_subject,
                            body=reply_body,
                            thread_id=thread_id,
                            reply_to_message_id=msg_id
                        )
                        
                        if success:
                            sent_count += 1
                            results.append({
                                "email_id": msg_id,
                                "status": "sent",
                                "to": sender_email,
                                "subject": reply_subject
                            })
                            
                            # Actualizar contador de uso
                            template["used_count"] += 1
                        else:
                            error_count += 1
                            results.append({
                                "email_id": msg_id,
                                "status": "error",
                                "reason": "Error enviando email"
                            })
                    
                except Exception as e:
                    error_count += 1
                    results.append({
                        "email_id": msg.get("id", "unknown"),
                        "status": "error",
                        "reason": str(e)
                    })
                    continue
            
            # Guardar historial
            self._save_mass_response_history(template_name, query, results, dry_run)
            
            # Guardar templates actualizados
            self._save_templates()
            
            action = "simuladas" if dry_run else "enviadas"
            return {
                "status": "success",
                "sent": sent_count if not dry_run else 0,
                "simulated": len(results) if dry_run else 0,
                "errors": error_count,
                "total_processed": len(results),
                "results": results,
                "message": f"✅ {sent_count if not dry_run else len(results)} respuestas {action} exitosamente"
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    def _send_gmail_reply(
        self,
        access_token: str,
        to: str,
        subject: str,
        body: str,
        thread_id: Optional[str] = None,
        reply_to_message_id: Optional[str] = None
    ) -> bool:
        """Envía una respuesta por Gmail."""
        headers = {"Authorization": f"Bearer {access_token}"}
        
        # Construir mensaje con headers de respuesta
        message = f"To: {to}\r\n"
        message += f"Subject: {subject}\r\n"
        if reply_to_message_id:
            message += f"In-Reply-To: <{reply_to_message_id}>\r\n"
            message += f"References: <{reply_to_message_id}>\r\n"
        message += "\r\n" + body
        
        # Codificar en base64url
        message_bytes = message.encode('utf-8')
        message_b64 = base64.urlsafe_b64encode(message_bytes).decode('utf-8')
        
        # Preparar payload
        payload = {"raw": message_b64}
        if thread_id:
            payload["threadId"] = thread_id
        
        try:
            send_url = "https://www.googleapis.com/gmail/v1/users/me/messages/send"
            response = requests.post(
                send_url,
                headers=headers,
                json=payload,
                timeout=10
            )
            
            return response.status_code == 200
            
        except Exception:
            return False
    
    def _extract_email_address(self, email_string: str) -> Optional[str]:
        """Extrae dirección de email de un string."""
        pattern = r'[\w\.-]+@[\w\.-]+\.\w+'
        match = re.search(pattern, email_string)
        if match:
            return match.group(0)
        return None
    
    def _save_templates(self):
        """Guarda plantillas en disco."""
        templates_file = self.data_dir / "mass_response_templates.json"
        try:
            with open(templates_file, 'w', encoding='utf-8') as f:
                json.dump(self.mass_response_templates, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error guardando plantillas: {e}")
    
    def _load_templates(self):
        """Carga plantillas de disco."""
        templates_file = self.data_dir / "mass_response_templates.json"
        if templates_file.exists():
            try:
                with open(templates_file, 'r', encoding='utf-8') as f:
                    self.mass_response_templates = json.load(f)
            except Exception as e:
                print(f"Error cargando plantillas: {e}")
                self.mass_response_templates = {}
    
    def _save_mass_response_history(self, template_name: str, query: str, results: List[Dict], dry_run: bool):
        """Guarda historial de respuestas masivas."""
        history_entry = {
            "timestamp": datetime.now().isoformat(),
            "template_name": template_name,
            "query": query,
            "dry_run": dry_run,
            "results": results,
            "total": len(results)
        }
        
        history = []
        if self.mass_response_history_file.exists():
            try:
                with open(self.mass_response_history_file, 'r', encoding='utf-8') as f:
                    history = json.load(f)
            except Exception:
                pass
        
        history.append(history_entry)
        
        # Mantener solo últimas 100 entradas
        if len(history) > 100:
            history = history[-100:]
        
        try:
            with open(self.mass_response_history_file, 'w', encoding='utf-8') as f:
                json.dump(history, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error guardando historial: {e}")
    
    def get_templates(self) -> List[Dict[str, Any]]:
        """Obtiene lista de plantillas disponibles."""
        return list(self.mass_response_templates.values())
    
    def get_indexed_emails_count(self, session_id: str) -> int:
        """Obtiene cantidad de emails indexados en una sesión."""
        return len(self.indexed_emails.get(session_id, []))

