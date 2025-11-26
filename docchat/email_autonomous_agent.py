"""
Email Autonomous Agent - Sistema de respuestas automáticas de emails en tiempo real.

Este módulo permite a las empresas:
- Conectar sus cuentas de email (Gmail, IMAP, etc.)
- Recibir emails en tiempo real
- Responder automáticamente usando Agentic AI
- Seguir las reglas de Eric Schmidt para emails profesionales
"""

from __future__ import annotations

import json
import time
import threading
import imaplib
import email
from email.header import decode_header
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
import re

from langchain_core.messages import HumanMessage, SystemMessage

from .config import AppConfig
from .integrations.gmail_integration import GmailIntegration
from .utils.llm_factory import create_llm


class EmailAutonomousAgent:
    """
    Agente autónomo que monitorea y responde emails automáticamente en tiempo real.
    
    Sigue las reglas de Eric Schmidt para emails profesionales:
    1. Responder rápidamente
    2. Ser conciso y claro
    3. Limpiar inbox constantemente
    4. Manejar emails en orden LIFO
    5. Actuar como router de información
    6. Evitar BCC innecesario
    7. No gritar (evitar mayúsculas)
    8. Facilitar seguimiento
    9. Ayudar a búsquedas futuras
    """
    
    # Reglas de Eric Schmidt integradas en el prompt
    ERIC_SCHMIDT_EMAIL_RULES = """
    REGLAS PARA EMAILS PROFESIONALES (Eric Schmidt - Google):
    
    1. RESPONDER RÁPIDAMENTE: Responde lo antes posible, incluso con respuestas cortas como "got it".
       Esto establece un ciclo de comunicación positivo y demuestra responsabilidad.
    
    2. SER CONCISO: Cada palabra importa. Elimina palabras innecesarias. Piensa en Elmore Leonard:
       "I leave out the parts that people skip." La mayoría de emails tienen contenido que se puede saltar.
    
    3. LIMPIAR INBOX CONSTANTEMENTE: Decide inmediatamente qué hacer con cada email:
       - Leer lo suficiente para saber que no necesitas leerlo
       - Leer y actuar inmediatamente
       - Leer y actuar después
       - Leer después (si vale la pena pero no es urgente)
       Usa el acrónimo OHIO: Only Hold It Once. Si lees y sabes qué hacer, hazlo de inmediato.
    
    4. MANEJAR EMAILS EN ORDEN LIFO (Last In First Out): A veces lo más antiguo se resuelve solo.
    
    5. ACTUAR COMO ROUTER: Cuando recibes información útil, considera quién más la encontraría útil.
       Al final del día, pregunta: "¿Qué debería haber reenviado pero no lo hice?"
    
    6. EVITAR BCC INNECESARIO: Solo usa BCC cuando estás removiendo a alguien de un thread largo.
       La transparencia es clave en una cultura abierta.
    
    7. NO GRITAR: Si necesitas ser enfático, hazlo en persona. Es MUY FÁCIL gritar electrónicamente.
    
    8. FACILITAR SEGUIMIENTO: Si envías una nota con un action item, cópiate a ti mismo y etiquétala
       "follow up" para facilitar el seguimiento.
    
    9. AYUDAR A BÚSQUEDAS FUTURAS: Si recibes algo que quieres recordar después, reenvíatelo a ti mismo
       con palabras clave descriptivas. Piensa: "¿Cómo buscaré esto después?"
    """
    
    def __init__(self, config: AppConfig, provider: str = "openai"):
        self.config = config
        self.provider = provider
        
        # LLM para generar respuestas automáticas
        self.llm = create_llm(
            provider=provider,
            model=config.agentic_model or "gpt-4o",
            temperature=0.3,  # Balance entre creatividad y consistencia
            api_key=config.openai_api_key if provider == "openai" else config.anthropic_api_key,
            max_tokens=4000,  # Respuestas concisas pero completas
            request_timeout=60  # Respuestas rápidas
        )
        
        # Integración Gmail
        self.gmail_integration = GmailIntegration()
        
        # Estado del monitoreo
        self.is_monitoring = False
        self.monitoring_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        
        # Configuración de email
        self.email_config: Dict[str, Any] = {}
        self.processed_emails: set = set()  # IDs de emails ya procesados
        
        # Directorio para almacenar datos
        self.data_dir = Path(config.memory_dir) / "email_autonomous"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Archivos de datos
        self.responses_file = self.data_dir / "email_responses.json"
        self.settings_file = self.data_dir / "email_settings.json"
        
        # Cargar configuración
        self._load_settings()
    
    def _load_settings(self):
        """Carga configuración guardada."""
        try:
            if self.settings_file.exists():
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    self.email_config = json.load(f)
        except Exception as e:
            print(f"Error cargando configuración: {e}")
            self.email_config = {}
    
    def _save_settings(self):
        """Guarda configuración."""
        try:
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(self.email_config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error guardando configuración: {e}")
    
    def connect_gmail(self, credentials_json: Dict[str, Any]) -> Dict[str, Any]:
        """
        Conecta cuenta de Gmail para monitoreo.
        
        Args:
            credentials_json: Credenciales de OAuth2 de Gmail
        
        Returns:
            Dict con status de conexión
        """
        try:
            success = self.gmail_integration.authenticate(credentials_json)
            if success:
                self.email_config['provider'] = 'gmail'
                self.email_config['connected'] = True
                self.email_config['connected_at'] = datetime.now().isoformat()
                self._save_settings()
                return {
                    'success': True,
                    'message': '✅ Gmail conectado exitosamente',
                    'provider': 'gmail'
                }
            else:
                return {
                    'success': False,
                    'message': '❌ Error al autenticar con Gmail'
                }
        except Exception as e:
            return {
                'success': False,
                'message': f'❌ Error conectando Gmail: {str(e)}'
            }
    
    def connect_imap(
        self,
        server: str,
        port: int,
        username: str,
        password: str,
        use_ssl: bool = True
    ) -> Dict[str, Any]:
        """
        Conecta cuenta de email vía IMAP.
        
        Args:
            server: Servidor IMAP (ej: imap.gmail.com)
            port: Puerto IMAP (ej: 993)
            username: Usuario/email
            password: Contraseña o app password
            use_ssl: Usar SSL
        
        Returns:
            Dict con status de conexión
        """
        try:
            if use_ssl:
                mail = imaplib.IMAP4_SSL(server, port)
            else:
                mail = imaplib.IMAP4(server, port)
            
            mail.login(username, password)
            mail.select('INBOX')
            
            self.email_config['provider'] = 'imap'
            self.email_config['imap_server'] = server
            self.email_config['imap_port'] = port
            self.email_config['imap_username'] = username
            # No guardar password en texto plano (en producción usar encriptación)
            self.email_config['connected'] = True
            self.email_config['connected_at'] = datetime.now().isoformat()
            self._save_settings()
            
            mail.logout()
            
            return {
                'success': True,
                'message': f'✅ Email IMAP conectado exitosamente ({server})',
                'provider': 'imap'
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'❌ Error conectando IMAP: {str(e)}'
            }
    
    def start_monitoring(
        self,
        poll_interval: int = 30,
        auto_respond: bool = True,
        response_rules: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Inicia monitoreo de emails en tiempo real.
        
        Args:
            poll_interval: Intervalo de polling en segundos (default: 30)
            auto_respond: Si True, responde automáticamente
            response_rules: Reglas personalizadas para respuestas
        
        Returns:
            Dict con status del monitoreo
        """
        if self.is_monitoring:
            return {
                'success': False,
                'message': '⚠️ El monitoreo ya está activo'
            }
        
        if not self.email_config.get('connected'):
            return {
                'success': False,
                'message': '❌ No hay email conectado. Conecta Gmail o IMAP primero.'
            }
        
        self.email_config['poll_interval'] = poll_interval
        self.email_config['auto_respond'] = auto_respond
        self.email_config['response_rules'] = response_rules or {}
        self._save_settings()
        
        self.is_monitoring = True
        self.stop_event.clear()
        
        # Iniciar thread de monitoreo
        self.monitoring_thread = threading.Thread(
            target=self._monitoring_loop,
            args=(poll_interval, auto_respond),
            daemon=True
        )
        self.monitoring_thread.start()
        
        return {
            'success': True,
            'message': f'✅ Monitoreo iniciado (polling cada {poll_interval}s)',
            'poll_interval': poll_interval,
            'auto_respond': auto_respond
        }
    
    def stop_monitoring(self) -> Dict[str, Any]:
        """Detiene el monitoreo de emails."""
        if not self.is_monitoring:
            return {
                'success': False,
                'message': '⚠️ El monitoreo no está activo'
            }
        
        self.is_monitoring = False
        self.stop_event.set()
        
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5)
        
        return {
            'success': True,
            'message': '✅ Monitoreo detenido'
        }
    
    def _monitoring_loop(self, poll_interval: int, auto_respond: bool):
        """Loop principal de monitoreo de emails."""
        print(f"[Email Agent] 🚀 Iniciando monitoreo de emails (cada {poll_interval}s)")
        
        while self.is_monitoring and not self.stop_event.is_set():
            try:
                # Obtener nuevos emails
                new_emails = self._get_new_emails()
                
                if new_emails:
                    print(f"[Email Agent] 📧 {len(new_emails)} nuevo(s) email(s) recibido(s)")
                    
                    # Procesar emails en orden LIFO (más recientes primero)
                    for email_data in reversed(new_emails):
                        if auto_respond:
                            self._process_and_respond_email(email_data)
                        else:
                            self._process_email(email_data)
                
                # Esperar antes del siguiente poll
                self.stop_event.wait(poll_interval)
                
            except Exception as e:
                print(f"[Email Agent] ❌ Error en monitoreo: {e}")
                time.sleep(poll_interval)
        
        print("[Email Agent] ⏹️ Monitoreo detenido")
    
    def _get_new_emails(self) -> List[Dict[str, Any]]:
        """Obtiene nuevos emails según el proveedor configurado."""
        provider = self.email_config.get('provider')
        
        if provider == 'gmail':
            return self._get_gmail_emails()
        elif provider == 'imap':
            return self._get_imap_emails()
        else:
            return []
    
    def _get_gmail_emails(self) -> List[Dict[str, Any]]:
        """Obtiene nuevos emails de Gmail."""
        try:
            # Obtener emails no leídos de las últimas 24 horas
            query = "is:unread newer_than:1d"
            emails = self.gmail_integration.get_emails(query=query, max_results=50)
            
            # Filtrar emails ya procesados
            new_emails = []
            for email_data in emails:
                email_id = email_data.get('id')
                if email_id and email_id not in self.processed_emails:
                    # Obtener cuerpo completo del email
                    full_email = self._get_gmail_full_email(email_id)
                    if full_email:
                        email_data.update(full_email)
                        new_emails.append(email_data)
            
            return new_emails
        except Exception as e:
            print(f"Error obteniendo emails de Gmail: {e}")
            return []
    
    def _get_gmail_full_email(self, message_id: str) -> Optional[Dict[str, Any]]:
        """Obtiene el cuerpo completo de un email de Gmail."""
        try:
            message = self.gmail_integration.service.users().messages().get(
                userId='me',
                id=message_id,
                format='full'
            ).execute()
            
            payload = message.get('payload', {})
            body = self._extract_email_body(payload)
            
            headers = payload.get('headers', [])
            return {
                'body': body,
                'to': self._get_header(headers, 'To'),
                'cc': self._get_header(headers, 'Cc'),
                'reply_to': self._get_header(headers, 'Reply-To')
            }
        except Exception as e:
            print(f"Error obteniendo email completo: {e}")
            return None
    
    def _get_imap_emails(self) -> List[Dict[str, Any]]:
        """Obtiene nuevos emails vía IMAP."""
        try:
            server = self.email_config.get('imap_server')
            port = self.email_config.get('imap_port', 993)
            username = self.email_config.get('imap_username')
            # La contraseña se guarda en connect_imap
            password = self.email_config.get('imap_password', '')
            
            if not all([server, username]):
                return []
            
            # Si no hay password guardada, no podemos conectar
            if not password:
                print("[Email Agent] ⚠️ Contraseña IMAP no disponible")
                return []
            
            mail = imaplib.IMAP4_SSL(server, port)
            mail.login(username, password)
            mail.select('INBOX')
            
            # Buscar emails no leídos
            status, messages = mail.search(None, 'UNSEEN')
            
            new_emails = []
            if status == 'OK':
                email_ids = messages[0].split()
                
                for email_id in email_ids[-10:]:  # Últimos 10 emails (LIFO)
                    status, msg_data = mail.fetch(email_id, '(RFC822)')
                    
                    if status == 'OK':
                        email_body = msg_data[0][1]
                        email_message = email.message_from_bytes(email_body)
                        
                        email_id_str = email_id.decode('utf-8')
                        if email_id_str not in self.processed_emails:
                            email_data = {
                                'id': email_id_str,
                                'subject': self._decode_header(email_message['Subject']),
                                'from': self._decode_header(email_message['From']),
                                'date': email_message['Date'],
                                'body': self._extract_imap_body(email_message),
                                'to': email_message.get('To', ''),
                                'cc': email_message.get('Cc', ''),
                                'reply_to': email_message.get('Reply-To', '')
                            }
                            new_emails.append(email_data)
            
            mail.logout()
            return new_emails
            
        except Exception as e:
            print(f"Error obteniendo emails IMAP: {e}")
            return []
    
    def _extract_email_body(self, payload: Dict) -> str:
        """Extrae el cuerpo del email desde payload de Gmail."""
        body = ""
        
        if 'parts' in payload:
            for part in payload['parts']:
                mime_type = part.get('mimeType', '')
                if mime_type == 'text/plain':
                    data = part.get('body', {}).get('data', '')
                    if data:
                        import base64
                        body = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
                        break
                elif mime_type == 'text/html' and not body:
                    data = part.get('body', {}).get('data', '')
                    if data:
                        import base64
                        html_body = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
                        # Convertir HTML a texto simple (básico)
                        body = re.sub(r'<[^>]+>', '', html_body)
        else:
            mime_type = payload.get('mimeType', '')
            if mime_type == 'text/plain':
                data = payload.get('body', {}).get('data', '')
                if data:
                    import base64
                    body = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
        
        return body
    
    def _extract_imap_body(self, email_message) -> str:
        """Extrae el cuerpo del email desde mensaje IMAP."""
        body = ""
        
        if email_message.is_multipart():
            for part in email_message.walk():
                content_type = part.get_content_type()
                if content_type == 'text/plain':
                    body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                    break
        else:
            body = email_message.get_payload(decode=True).decode('utf-8', errors='ignore')
        
        return body
    
    def _decode_header(self, header_value: Optional[str]) -> str:
        """Decodifica header de email."""
        if not header_value:
            return ""
        
        decoded_parts = decode_header(header_value)
        decoded_str = ""
        for part, encoding in decoded_parts:
            if isinstance(part, bytes):
                decoded_str += part.decode(encoding or 'utf-8', errors='ignore')
            else:
                decoded_str += part
        return decoded_str
    
    def _get_header(self, headers: List[Dict], name: str) -> str:
        """Obtiene valor de header por nombre."""
        for header in headers:
            if header.get('name') == name:
                return header.get('value', '')
        return ""
    
    def _process_email(self, email_data: Dict[str, Any]):
        """Procesa un email sin responder (solo logging)."""
        email_id = email_data.get('id')
        subject = email_data.get('subject', 'Sin asunto')
        from_email = email_data.get('from', 'Desconocido')
        
        print(f"[Email Agent] 📧 Email recibido: '{subject}' de {from_email}")
        
        # Marcar como procesado
        if email_id:
            self.processed_emails.add(email_id)
    
    def _process_and_respond_email(self, email_data: Dict[str, Any]):
        """Procesa un email y genera respuesta automática."""
        email_id = email_data.get('id')
        subject = email_data.get('subject', 'Sin asunto')
        from_email = email_data.get('from', 'Desconocido')
        body = email_data.get('body', '')
        to_email = email_data.get('to', '')
        
        print(f"[Email Agent] 📧 Procesando email: '{subject}' de {from_email}")
        
        # Generar respuesta usando Agentic AI
        response = self._generate_automatic_response(email_data)
        
        if response and response.get('should_respond', True):
            # Enviar respuesta
            reply_subject = response.get('subject', f"Re: {subject}")
            reply_body = response.get('body', '')
            
            # Extraer email del remitente
            sender_email = self._extract_email_address(from_email)
            
            if sender_email:
                success = self._send_response(sender_email, reply_subject, reply_body)
                
                if success:
                    print(f"[Email Agent] ✅ Respuesta enviada a {sender_email}")
                    
                    # Guardar respuesta
                    self._save_response(email_data, response)
                else:
                    print(f"[Email Agent] ❌ Error enviando respuesta a {sender_email}")
            else:
                print(f"[Email Agent] ⚠️ No se pudo extraer email del remitente")
        
        # Marcar como procesado
        if email_id:
            self.processed_emails.add(email_id)
    
    def _generate_automatic_response(self, email_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Genera respuesta automática usando Agentic AI siguiendo las reglas de Eric Schmidt.
        """
        subject = email_data.get('subject', 'Sin asunto')
        from_email = email_data.get('from', 'Desconocido')
        body = email_data.get('body', '')
        
        # Construir prompt con reglas de Eric Schmidt
        prompt = f"""Eres un asistente de email profesional que responde emails automáticamente siguiendo las mejores prácticas de comunicación empresarial.

{self.ERIC_SCHMIDT_EMAIL_RULES}

EMAIL RECIBIDO:
De: {from_email}
Asunto: {subject}
Cuerpo:
{body[:2000]}  # Limitar para contexto

INSTRUCCIONES:
1. Analiza el email recibido
2. Determina si requiere respuesta (algunos emails no la requieren: spam, notificaciones automáticas, etc.)
3. Si requiere respuesta, genera una respuesta profesional, concisa y útil
4. Sigue TODAS las reglas de Eric Schmidt:
   - Responde rápidamente (tu respuesta debe ser inmediata)
   - Sé conciso: elimina palabras innecesarias
   - Si el email tiene una pregunta clara, respóndela directamente
   - Si el email requiere acción, confirma que la tomarás o explica cómo procederás
   - Si el email es solo informativo, responde brevemente con "got it" o similar
   - NO uses mayúsculas excesivas (no grites)
   - Sé profesional pero amigable

FORMATO DE RESPUESTA (JSON):
{{
    "should_respond": true/false,
    "subject": "Re: [asunto original] o nuevo asunto si es necesario",
    "body": "Cuerpo de la respuesta, conciso y profesional",
    "reasoning": "Breve explicación de por qué esta respuesta"
}}

IMPORTANTE:
- Si el email es spam, notificación automática, o no requiere respuesta, establece "should_respond": false
- La respuesta debe ser en el mismo idioma que el email recibido
- Sé breve pero completo
- Si no estás seguro de algo, sé honesto y ofrece seguir investigando

Genera la respuesta ahora:"""
        
        try:
            response = self.llm.invoke(prompt).content.strip()
            
            # Extraer JSON de la respuesta
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                response_data = json.loads(json_match.group())
                return response_data
            else:
                # Si no hay JSON, crear respuesta básica
                return {
                    'should_respond': True,
                    'subject': f"Re: {subject}",
                    'body': response[:500],  # Limitar longitud
                    'reasoning': 'Respuesta generada automáticamente'
                }
        except Exception as e:
            print(f"Error generando respuesta: {e}")
            return {
                'should_respond': False,
                'subject': '',
                'body': '',
                'reasoning': f'Error: {str(e)}'
            }
    
    def _extract_email_address(self, email_string: str) -> Optional[str]:
        """Extrae dirección de email de un string."""
        # Patrón para extraer email
        pattern = r'[\w\.-]+@[\w\.-]+\.\w+'
        match = re.search(pattern, email_string)
        if match:
            return match.group(0)
        return None
    
    def _send_response(self, to_email: str, subject: str, body: str) -> bool:
        """Envía respuesta de email."""
        provider = self.email_config.get('provider')
        
        if provider == 'gmail':
            return self.gmail_integration.send_email(to_email, subject, body)
        elif provider == 'imap':
            # Implementar envío vía SMTP para IMAP
            return self._send_imap_email(to_email, subject, body)
        else:
            return False
    
    def _send_imap_email(self, to_email: str, subject: str, body: str) -> bool:
        """Envía email vía SMTP (para IMAP)."""
        try:
            import smtplib
            from email.mime.text import MIMEText
            
            smtp_server = self.email_config.get('smtp_server', '')
            smtp_port = self.email_config.get('smtp_port', 587)
            smtp_username = self.email_config.get('imap_username', '')
            smtp_password = self.email_config.get('smtp_password', '')
            
            if not all([smtp_server, smtp_username, smtp_password]):
                return False
            
            msg = MIMEText(body)
            msg['Subject'] = subject
            msg['From'] = smtp_username
            msg['To'] = to_email
            
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(smtp_username, smtp_password)
                server.send_message(msg)
            
            return True
        except Exception as e:
            print(f"Error enviando email SMTP: {e}")
            return False
    
    def _save_response(self, original_email: Dict, response: Dict):
        """Guarda respuesta para historial."""
        try:
            responses = []
            if self.responses_file.exists():
                with open(self.responses_file, 'r', encoding='utf-8') as f:
                    responses = json.load(f)
            
            responses.append({
                'timestamp': datetime.now().isoformat(),
                'original_email': {
                    'id': original_email.get('id'),
                    'from': original_email.get('from'),
                    'subject': original_email.get('subject')
                },
                'response': response
            })
            
            # Mantener solo últimas 1000 respuestas
            if len(responses) > 1000:
                responses = responses[-1000:]
            
            with open(self.responses_file, 'w', encoding='utf-8') as f:
                json.dump(responses, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error guardando respuesta: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """Obtiene estado actual del agente."""
        return {
            'is_monitoring': self.is_monitoring,
            'is_connected': self.email_config.get('connected', False),
            'provider': self.email_config.get('provider'),
            'poll_interval': self.email_config.get('poll_interval', 30),
            'auto_respond': self.email_config.get('auto_respond', True),
            'processed_count': len(self.processed_emails),
            'connected_at': self.email_config.get('connected_at')
        }
    
    def get_response_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Obtiene historial de respuestas."""
        try:
            if self.responses_file.exists():
                with open(self.responses_file, 'r', encoding='utf-8') as f:
                    responses = json.load(f)
                    return responses[-limit:]
            return []
        except Exception as e:
            print(f"Error obteniendo historial: {e}")
            return []

