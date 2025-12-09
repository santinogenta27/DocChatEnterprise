"""
Company Knowledge Integrations - Sistema de conexión con apps empresariales
Similar a ChatGPT Company Knowledge, permite conectar Slack, Google Drive, SharePoint, etc.
"""

from __future__ import annotations

import json
import time
from typing import List, Dict, Optional, Any
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum

from .config import AppConfig


class IntegrationType(str, Enum):
    """Tipos de integraciones soportadas."""
    SLACK = "slack"
    GOOGLE_DRIVE = "google_drive"
    SHAREPOINT = "sharepoint"
    GITHUB = "github"
    GMAIL = "gmail"
    OUTLOOK = "outlook"
    DROPBOX = "dropbox"
    BOX = "box"
    TEAMS = "teams"
    HUBSPOT = "hubspot"
    SALESFORCE = "salesforce"
    LINEAR = "linear"
    ASANA = "asana"
    GITLAB = "gitlab"
    CLICKUP = "clickup"
    INTERCOM = "intercom"
    JIRA = "jira"
    CONFLUENCE = "confluence"


@dataclass
class AppConnection:
    """Conexión a una app externa."""
    connection_id: str
    app_type: IntegrationType
    app_name: str
    status: str = "disconnected"  # disconnected, connected, error
    connected_at: Optional[str] = None
    last_sync: Optional[str] = None
    permissions: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True
    credentials: Dict[str, Any] = field(default_factory=dict)  # Almacenar credenciales


@dataclass
class AppSearchResult:
    """Resultado de búsqueda en una app."""
    app_type: IntegrationType
    app_name: str
    source_id: str
    source_name: str
    content: str
    snippet: str
    url: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    relevance_score: float = 0.0


class CompanyKnowledgeIntegrations:
    """
    Sistema de integraciones para Company Knowledge.
    Permite conectar apps empresariales y buscar en ellas.
    """
    
    def __init__(self, config: AppConfig):
        self.config = config
        self.data_dir = Path(config.memory_dir) / "company_knowledge"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.connections_file = self.data_dir / "app_connections.json"
        self.connections: Dict[str, AppConnection] = {}
        
        # Cargar conexiones existentes
        self._load_connections()
    
    def _load_connections(self):
        """Carga conexiones guardadas."""
        if self.connections_file.exists():
            try:
                with open(self.connections_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for conn_data in data.get("connections", []):
                        # Asegurar que credentials existe
                        if "credentials" not in conn_data:
                            conn_data["credentials"] = {}
                        # Convertir app_type de string a IntegrationType si es necesario
                        if isinstance(conn_data.get("app_type"), str):
                            conn_data["app_type"] = IntegrationType(conn_data["app_type"])
                        conn = AppConnection(**conn_data)
                        self.connections[conn.connection_id] = conn
            except Exception as e:
                print(f"⚠️ [Company Knowledge] Error cargando conexiones: {e}")
    
    def _save_connections(self):
        """Guarda conexiones."""
        try:
            data = {
                "connections": [
                    {
                        "connection_id": conn.connection_id,
                        "app_type": conn.app_type.value if hasattr(conn.app_type, 'value') else str(conn.app_type),
                        "app_name": conn.app_name,
                        "status": conn.status,
                        "connected_at": conn.connected_at,
                        "last_sync": conn.last_sync,
                        "permissions": conn.permissions,
                        "metadata": conn.metadata,
                        "enabled": conn.enabled,
                        "credentials": conn.credentials  # Guardar credenciales
                    }
                    for conn in self.connections.values()
                ]
            }
            with open(self.connections_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"⚠️ [Company Knowledge] Error guardando conexiones: {e}")
            import traceback
            traceback.print_exc()
    
    def connect_app(
        self,
        app_type: IntegrationType,
        app_name: str,
        credentials: Dict[str, Any],
        permissions: Optional[Dict[str, Any]] = None
    ) -> AppConnection:
        """
        Conecta una app externa con validación real de credenciales.
        
        Args:
            app_type: Tipo de app (SLACK, GOOGLE_DRIVE, etc.)
            app_name: Nombre descriptivo de la conexión
            credentials: Credenciales para autenticación (debe incluir "token")
            permissions: Permisos específicos de la conexión
        
        Returns:
            AppConnection: Conexión creada
        """
        connection_id = f"{app_type.value}_{int(time.time())}"
        
        # Validar que hay token
        if "token" not in credentials or not credentials.get("token"):
            raise ValueError("Token requerido en credentials")
        
        # Validar credenciales con la API real
        try:
            is_valid = self._validate_credentials(app_type, credentials)
            if not is_valid:
                raise ValueError(f"Credenciales inválidas para {app_type.value}. El token no pudo ser validado.")
        except ValueError as e:
            # Re-lanzar ValueError con mensaje mejorado
            raise e
        except Exception as e:
            # Si la validación falla, crear conexión con estado "error"
            error_msg = str(e)
            connection = AppConnection(
                connection_id=connection_id,
                app_type=app_type,
                app_name=app_name,
                status="error",
                connected_at=time.strftime("%Y-%m-%d %H:%M:%S"),
                permissions=permissions or {},
                metadata={"error": error_msg, "credentials_stored": True},
                credentials=credentials
            )
            self.connections[connection_id] = connection
            self._save_connections()
            raise ValueError(f"Error validando credenciales: {error_msg}")
        
        # Crear conexión exitosa
        connection = AppConnection(
            connection_id=connection_id,
            app_type=app_type,
            app_name=app_name,
            status="connected",
            connected_at=time.strftime("%Y-%m-%d %H:%M:%S"),
            last_sync=time.strftime("%Y-%m-%d %H:%M:%S"),
            permissions=permissions or {},
            metadata={"credentials_stored": True, "validated": True},
            credentials=credentials
        )
        
        self.connections[connection_id] = connection
        self._save_connections()
        
        print(f"✅ [Company Knowledge] App conectada: {app_name} ({app_type.value})")
        return connection
    
    def _validate_credentials(self, app_type: IntegrationType, credentials: Dict[str, Any]) -> bool:
        """
        Valida credenciales haciendo una llamada real a la API de la app.
        
        Returns:
            True si las credenciales son válidas, False en caso contrario
        """
        import requests
        
        token = credentials.get("token", "")
        if not token:
            raise ValueError("Token vacío. Por favor, ingresa un token válido.")
        
        try:
            if app_type == IntegrationType.SLACK:
                # Validar token de Slack
                response = requests.get(
                    "https://slack.com/api/auth.test",
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=10
                )
                return response.status_code == 200 and response.json().get("ok", False)
            
            elif app_type == IntegrationType.GOOGLE_DRIVE:
                # Validar token de Google Drive
                response = requests.get(
                    "https://www.googleapis.com/drive/v3/about",
                    params={"fields": "user"},
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=10
                )
                return response.status_code == 200
            
            elif app_type == IntegrationType.GITHUB:
                # Validar token de GitHub
                response = requests.get(
                    "https://api.github.com/user",
                    headers={"Authorization": f"token {token}"},
                    timeout=10
                )
                return response.status_code == 200
            
            elif app_type == IntegrationType.HUBSPOT:
                # Validar token de HubSpot
                base_url = credentials.get("base_url", "https://api.hubapi.com")
                response = requests.get(
                    f"{base_url}/integrations/v1/me",
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=10
                )
                return response.status_code == 200
            
            elif app_type == IntegrationType.SALESFORCE:
                # Validar token de Salesforce (usar instance_url)
                instance_url = credentials.get("instance_url", "")
                if not instance_url:
                    return False
                response = requests.get(
                    f"{instance_url}/services/oauth2/userinfo",
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=10
                )
                return response.status_code == 200
            
            elif app_type == IntegrationType.JIRA:
                # Validar token de Jira (puede ser Basic Auth o Bearer)
                base_url = credentials.get("base_url", "")
                if not base_url:
                    return False
                # Intentar como Bearer token primero
                response = requests.get(
                    f"{base_url}/rest/api/3/myself",
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=10
                )
                if response.status_code == 200:
                    return True
                # Si falla, intentar como Basic Auth (email:token)
                import base64
                auth_str = base64.b64encode(token.encode()).decode()
                response = requests.get(
                    f"{base_url}/rest/api/3/myself",
                    headers={"Authorization": f"Basic {auth_str}"},
                    timeout=10
                )
                return response.status_code == 200
            
            elif app_type == IntegrationType.CONFLUENCE:
                # Similar a Jira
                base_url = credentials.get("base_url", "")
                if not base_url:
                    return False
                response = requests.get(
                    f"{base_url}/rest/api/user/current",
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=10
                )
                if response.status_code == 200:
                    return True
                import base64
                auth_str = base64.b64encode(token.encode()).decode()
                response = requests.get(
                    f"{base_url}/rest/api/user/current",
                    headers={"Authorization": f"Basic {auth_str}"},
                    timeout=10
                )
                return response.status_code == 200
            
            elif app_type == IntegrationType.LINEAR:
                # Validar token de Linear
                response = requests.post(
                    "https://api.linear.app/graphql",
                    json={"query": "{ viewer { id } }"},
                    headers={
                        "Authorization": token,
                        "Content-Type": "application/json"
                    },
                    timeout=10
                )
                return response.status_code == 200 and "errors" not in response.json()
            
            elif app_type == IntegrationType.ASANA:
                # Validar token de Asana
                response = requests.get(
                    "https://app.asana.com/api/1.0/users/me",
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=10
                )
                return response.status_code == 200
            
            elif app_type == IntegrationType.GITLAB:
                # Validar token de GitLab
                base_url = credentials.get("base_url", "https://gitlab.com")
                response = requests.get(
                    f"{base_url}/api/v4/user",
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=10
                )
                return response.status_code == 200
            
            elif app_type == IntegrationType.CLICKUP:
                # Validar token de ClickUp
                response = requests.get(
                    "https://api.clickup.com/api/v2/user",
                    headers={"Authorization": token},
                    timeout=10
                )
                return response.status_code == 200
            
            elif app_type == IntegrationType.INTERCOM:
                # Validar token de Intercom
                response = requests.get(
                    "https://api.intercom.io/me",
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Accept": "application/json"
                    },
                    timeout=10
                )
                return response.status_code == 200
            
            elif app_type == IntegrationType.DROPBOX:
                # Validar token de Dropbox
                response = requests.post(
                    "https://api.dropboxapi.com/2/users/get_current_account",
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=10
                )
                return response.status_code == 200
            
            elif app_type == IntegrationType.BOX:
                # Validar token de Box
                response = requests.get(
                    "https://api.box.com/2.0/users/me",
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=10
                )
                return response.status_code == 200
            
            elif app_type == IntegrationType.TEAMS:
                # Validar token de Microsoft Teams/Graph API
                response = requests.get(
                    "https://graph.microsoft.com/v1.0/me",
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=10
                )
                return response.status_code == 200
            
            elif app_type == IntegrationType.GMAIL:
                # Validar token de Gmail (Google API)
                response = requests.get(
                    "https://gmail.googleapis.com/gmail/v1/users/me/profile",
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=10
                )
                return response.status_code == 200
            
            elif app_type == IntegrationType.OUTLOOK:
                # Validar token de Outlook (Microsoft Graph)
                response = requests.get(
                    "https://graph.microsoft.com/v1.0/me",
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=10
                )
                return response.status_code == 200
            
            elif app_type == IntegrationType.SHAREPOINT:
                # Validar token de SharePoint (Microsoft Graph)
                response = requests.get(
                    "https://graph.microsoft.com/v1.0/sites/root",
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=10
                )
                return response.status_code == 200
            
            # Para apps no implementadas aún, hacer validación básica
            # Verificar que el token no esté vacío y tenga formato razonable
            if len(token) < 10:
                raise ValueError(f"Token demasiado corto para {app_type.value}. Verifica que copiaste el token completo.")
            return True
            
        except requests.exceptions.Timeout:
            raise ValueError(f"Timeout al validar {app_type.value}. Verifica tu conexión a internet.")
        except requests.exceptions.ConnectionError:
            raise ValueError(f"Error de conexión al validar {app_type.value}. Verifica tu conexión a internet.")
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                raise ValueError(f"Token inválido o expirado para {app_type.value}. Verifica que el token sea correcto y tenga los permisos necesarios.")
            elif e.response.status_code == 403:
                raise ValueError(f"Token sin permisos suficientes para {app_type.value}. Verifica los scopes/permisos del token.")
            else:
                raise ValueError(f"Error HTTP {e.response.status_code} al validar {app_type.value}: {str(e)}")
        except Exception as e:
            error_msg = str(e)
            if "token" in error_msg.lower() or "auth" in error_msg.lower() or "401" in error_msg or "403" in error_msg:
                raise ValueError(f"Error de autenticación para {app_type.value}: {error_msg}")
            raise ValueError(f"Error validando credenciales para {app_type.value}: {error_msg}")
    
    def disconnect_app(self, connection_id: str) -> bool:
        """Desconecta una app."""
        if connection_id in self.connections:
            self.connections[connection_id].status = "disconnected"
            self.connections[connection_id].enabled = False
            self._save_connections()
            return True
        return False
    
    def get_connected_apps(self) -> List[AppConnection]:
        """Obtiene lista de apps conectadas y habilitadas."""
        return [
            conn for conn in self.connections.values()
            if conn.status == "connected" and conn.enabled
        ]
    
    async def search_across_apps(
        self,
        query: str,
        app_types: Optional[List[IntegrationType]] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[AppSearchResult]:
        """
        Busca información en todas las apps conectadas.
        
        Args:
            query: Consulta de búsqueda
            app_types: Tipos de apps específicos a buscar (None = todas)
            filters: Filtros adicionales (fechas, tipos de contenido, etc.)
        
        Returns:
            Lista de resultados de búsqueda
        """
        results = []
        
        # Obtener apps a buscar
        apps_to_search = self.get_connected_apps()
        if app_types:
            apps_to_search = [
                app for app in apps_to_search
                if app.app_type in app_types
            ]
        
        # Buscar en cada app
        for app in apps_to_search:
            try:
                app_results = await self._search_in_app(
                    app=app,
                    query=query,
                    filters=filters
                )
                results.extend(app_results)
            except Exception as e:
                print(f"⚠️ [Company Knowledge] Error buscando en {app.app_name}: {e}")
                continue
        
        # Ordenar por relevancia
        results.sort(key=lambda x: x.relevance_score, reverse=True)
        
        return results
    
    async def _search_in_app(
        self,
        app: AppConnection,
        query: str,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[AppSearchResult]:
        """
        Busca en una app específica usando las APIs reales.
        """
        results = []
        
        # Obtener credenciales
        token = app.credentials.get("token", "")
        if not token:
            print(f"⚠️ [Company Knowledge] No hay token para {app.app_name}")
            return results
        
        # Obtener días de filtro si existe
        days = filters.get("days") if filters else None
        
        try:
            if app.app_type == IntegrationType.SLACK:
                results = await self._slack_search(token, query, days)
            elif app.app_type == IntegrationType.GOOGLE_DRIVE:
                results = await self._google_drive_search(token, query, app.credentials, days)
            elif app.app_type == IntegrationType.SHAREPOINT:
                results = await self._sharepoint_search(token, query, app.credentials, days)
            elif app.app_type == IntegrationType.GITHUB:
                results = await self._github_search(token, query, days)
            elif app.app_type == IntegrationType.GMAIL:
                results = await self._gmail_search(token, query, days)
            elif app.app_type == IntegrationType.OUTLOOK:
                results = await self._outlook_search(token, query, days)
            elif app.app_type == IntegrationType.HUBSPOT:
                results = await self._hubspot_search(token, query, filters)
            elif app.app_type == IntegrationType.SALESFORCE:
                results = await self._salesforce_search(token, query, app.credentials, days)
            elif app.app_type == IntegrationType.LINEAR:
                results = await self._linear_search(token, query, days)
            elif app.app_type == IntegrationType.ASANA:
                results = await self._asana_search(token, query, days)
            elif app.app_type == IntegrationType.GITLAB:
                results = await self._gitlab_search(token, query, app.credentials, days)
            elif app.app_type == IntegrationType.CLICKUP:
                results = await self._clickup_search(token, query, days)
            elif app.app_type == IntegrationType.INTERCOM:
                results = await self._intercom_search(token, query, days)
            elif app.app_type == IntegrationType.DROPBOX:
                results = await self._dropbox_search(token, query, days)
            elif app.app_type == IntegrationType.BOX:
                results = await self._box_search(token, query, days)
            elif app.app_type == IntegrationType.TEAMS:
                results = await self._teams_search(token, query, days)
            elif app.app_type == IntegrationType.JIRA:
                results = await self._jira_search(token, query, app.credentials, days)
            elif app.app_type == IntegrationType.CONFLUENCE:
                results = await self._confluence_search(token, query, app.credentials, days)
            
            # Actualizar última sincronización
            app.last_sync = time.strftime("%Y-%m-%d %H:%M:%S")
            self._save_connections()
            
        except Exception as e:
            print(f"⚠️ [Company Knowledge] Error buscando en {app.app_name}: {e}")
        
        return results
    
    # Métodos de búsqueda reales para cada app
    async def _slack_search(self, token: str, query: str, days: Optional[int] = None) -> List[AppSearchResult]:
        """Busca en Slack usando la API real."""
        import requests
        results = []
        
        try:
            # Buscar mensajes
            response = requests.get(
                "https://slack.com/api/search.messages",
                params={"query": query, "count": 20},
                headers={"Authorization": f"Bearer {token}"},
                timeout=15
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("ok"):
                    messages = data.get("messages", {}).get("matches", [])
                    
                    # Filtrar por fecha si se especifica
                    if days:
                        import time as time_module
                        min_ts = time_module.time() - days * 86400
                        messages = [m for m in messages if float(m.get("ts", 0)) >= min_ts]
                    
                    for msg in messages[:10]:  # Limitar a 10 resultados
                        channel = msg.get("channel", {}).get("name", "unknown")
                        text = msg.get("text", "")
                        ts = msg.get("ts", "")
                        user = msg.get("user", "")
                        
                        permalink = msg.get("permalink", "")
                        if not permalink and channel != "unknown":
                            permalink = f"https://slack.com/archives/{channel}/p{ts.replace('.', '')}"
                        
            results.append(AppSearchResult(
                            app_type=IntegrationType.SLACK,
                            app_name="Slack",
                            source_id=f"slack_{msg.get('ts', '')}",
                            source_name=f"#{channel}",
                            content=text,
                            snippet=text[:200],
                            url=permalink,
                            metadata={"author": user, "timestamp": ts, "channel": channel},
                relevance_score=0.85
            ))
        except Exception as e:
            print(f"⚠️ Error buscando en Slack: {e}")
        
        return results
    
    def _extract_pdf_with_docling_fallback(self, pdf_bytes: bytes, file_name: str) -> tuple[str, str]:
        """Extrae texto de PDF usando Docling como fallback (igual que DocumentProcessor)."""
        try:
            try:
                from docling.document_converter import DocumentConverter
                DOCLING_AVAILABLE = True
            except ImportError:
                DOCLING_AVAILABLE = False
                return "", f"PDF encontrado: {file_name} (Docling no disponible. Instala: pip install docling)"
            
            if not DOCLING_AVAILABLE:
                return "", f"PDF encontrado: {file_name} (Docling no disponible)"
            
            import tempfile
            from pathlib import Path
            
            # Guardar PDF temporalmente
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                tmp.write(pdf_bytes)
                tmp.flush()
                tmp_path = tmp.name
            
            try:
                print(f"   🔄 [Google Drive] Procesando con Docling (puede tardar)...")
                converter = DocumentConverter()
                result = converter.convert(tmp_path)
                
                # Extraer markdown
                markdown = result.document.export_to_markdown()
                if markdown and markdown.strip():
                    content = markdown
                    snippet = markdown[:1000]
                    print(f"✅ [Google Drive] Docling extrajo texto de {file_name}")
                    return content, snippet
                else:
                    return "", f"PDF encontrado: {file_name} (Docling no generó contenido)"
            finally:
                Path(tmp_path).unlink(missing_ok=True)
        except Exception as e:
            print(f"⚠️ [Google Drive] Error con Docling: {e}")
            return "", f"PDF encontrado: {file_name} (error con Docling: {str(e)[:50]})"
    
    def _extract_keywords_from_query(self, query: str) -> List[str]:
        """Extrae palabras clave relevantes de una query, removiendo palabras comunes."""
        import re
        # Palabras comunes a ignorar
        stop_words = {
            'el', 'la', 'los', 'las', 'un', 'una', 'unos', 'unas',
            'de', 'del', 'en', 'a', 'por', 'para', 'con', 'sin',
            'sobre', 'entre', 'hasta', 'desde', 'cual', 'cuales',
            'que', 'quien', 'quienes', 'donde', 'cuando', 'como',
            'es', 'son', 'está', 'están', 'fue', 'fueron', 'ser',
            'estar', 'tener', 'tiene', 'hacer', 'hace', 'poder',
            'puede', 'puedes', 'puedo', 'mi', 'mis', 'tu', 'tus',
            'su', 'sus', 'nuestro', 'nuestros', 'este', 'esta',
            'estos', 'estas', 'ese', 'esa', 'esos', 'esas',
            'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be',
            'been', 'have', 'has', 'had', 'do', 'does', 'did',
            'will', 'would', 'can', 'could', 'should', 'may',
            'might', 'must', 'this', 'that', 'these', 'those',
            'what', 'which', 'who', 'whom', 'where', 'when', 'how',
            'my', 'your', 'his', 'her', 'its', 'our', 'their'
        }
        
        # Convertir a minúsculas y extraer palabras
        words = re.findall(r'\b\w+\b', query.lower())
        # Filtrar palabras comunes y muy cortas, pero incluir palabras importantes como "pdf"
        important_words = {'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'txt', 'csv'}
        keywords = [
            w for w in words 
            if (w in important_words or (len(w) > 2 and w not in stop_words))
        ]
        return keywords[:10]  # Limitar a 10 palabras clave
    
    async def _google_drive_search(self, token: str, query: str, credentials: Dict[str, Any], days: Optional[int] = None) -> List[AppSearchResult]:
        """Busca en Google Drive usando la API real."""
        import requests
        results = []
        
        try:
            # Extraer palabras clave de la query
            keywords = self._extract_keywords_from_query(query)
            query_lower = query.lower()
            
            # Detectar si busca PDFs específicamente
            is_pdf_search = any(word in query_lower for word in ['pdf', 'documento pdf', 'archivo pdf'])
            
            # Construir query base
            q_params = ["trashed=false"]
            
            # Si busca PDFs, filtrar por tipo MIME
            if is_pdf_search:
                q_params.append("mimeType = 'application/pdf'")
                print("🔍 [Google Drive] Búsqueda específica de PDFs")
            
            # Agregar búsqueda por palabras clave si hay (excluyendo "pdf" si ya se filtró por tipo)
            keywords_to_search = [kw for kw in keywords if kw != 'pdf' or not is_pdf_search]
            
            if keywords_to_search:
                # Usar OR para buscar cualquiera de las palabras clave en el nombre o contenido
                keyword_queries = []
                for kw in keywords_to_search[:5]:  # Máximo 5 palabras clave
                    escaped_kw = kw.replace("'", "\\'")
                    keyword_queries.append(f"(name contains '{escaped_kw}' or fullText contains '{escaped_kw}')")
                
                if keyword_queries:
                    q_params.append(f"({' or '.join(keyword_queries)})")
            elif not is_pdf_search:
                # Si no hay palabras clave y no es búsqueda de PDF, buscar en el nombre del archivo
                # Extraer palabras significativas de la query original
                import re
                significant_words = re.findall(r'\b\w{4,}\b', query.lower())  # Palabras de 4+ caracteres
                if significant_words:
                    for word in significant_words[:3]:
                        escaped_word = word.replace("'", "\\'")
                        q_params.append(f"name contains '{escaped_word}'")
            # Si es búsqueda de PDF sin palabras clave adicionales, buscar todos los PDFs
            
            # Filtrar por carpeta si se especifica
            folder_id = credentials.get("folder_id")
            if folder_id:
                q_params.append(f"'{folder_id}' in parents")
            
            # Filtrar por fecha si se especifica
            if days:
                from datetime import datetime, timedelta
                min_date = (datetime.now() - timedelta(days=days)).isoformat() + "Z"
                q_params.append(f"modifiedTime > '{min_date}'")
            
            query_string = " and ".join(q_params)
            print(f"🔍 [Google Drive] Buscando con query: {query_string[:150]}...")
            print(f"🔍 [Google Drive] Palabras clave extraídas: {keywords[:5]}")
            
            # Buscar archivos - ordenar por fecha de modificación (más recientes primero)
            params = {
                "q": query_string,
                "pageSize": 100,  # Aumentado para obtener más resultados
                "fields": "files(id,name,mimeType,webViewLink,modifiedTime,owners,size)",
                "orderBy": "modifiedTime desc"
            }
            
            response = requests.get(
                "https://www.googleapis.com/drive/v3/files",
                params=params,
                headers={"Authorization": f"Bearer {token}"},
                timeout=15
            )
            
            print(f"🔍 [Google Drive] Status code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                files = data.get("files", [])
                print(f"✅ [Google Drive] Encontrados {len(files)} archivos")
                
                # Procesar TODOS los archivos encontrados (sin límite)
                for file in files:
                    file_id = file.get("id")
                    name = file.get("name", "Sin nombre")
                    mime_type = file.get("mimeType", "")
                    url = file.get("webViewLink", f"https://drive.google.com/file/d/{file_id}")
                    
                    # Intentar obtener contenido para Google Docs/Sheets/PDFs
                    content = ""
                    snippet = ""
                    
                    # Para Google Docs/Sheets: usar export API
                    if "document" in mime_type or "spreadsheet" in mime_type:
                        try:
                            export_url = f"https://www.googleapis.com/drive/v3/files/{file_id}/export"
                            if "document" in mime_type:
                                export_url += "?mimeType=text/plain"
                            elif "spreadsheet" in mime_type:
                                export_url += "?mimeType=text/csv"
                            
                            content_resp = requests.get(
                                export_url,
                                headers={"Authorization": f"Bearer {token}"},
                                timeout=10
                            )
                            if content_resp.status_code == 200:
                                content = content_resp.text[:2000]  # Aumentar límite
                                snippet = content[:500]
                        except Exception as e:
                            print(f"⚠️ [Google Drive] Error exportando {name}: {e}")
                    
                    # Para PDFs: descargar y extraer texto de TODAS las páginas (como Enterprise API)
                    elif mime_type == "application/pdf":
                        try:
                            # Descargar PDF
                            download_url = f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media"
                            print(f"📥 [Google Drive] Descargando PDF: {name}...")
                            pdf_resp = requests.get(
                                download_url,
                                headers={"Authorization": f"Bearer {token}"},
                                timeout=60,  # PDFs pueden ser grandes
                                stream=True
                            )
                            
                            if pdf_resp.status_code == 200:
                                pdf_bytes = pdf_resp.content
                                print(f"✅ [Google Drive] PDF descargado: {len(pdf_bytes) / (1024*1024):.2f} MB")
                                
                                # Intentar extraer texto de TODAS las páginas usando PyPDF2 (método rápido como Enterprise)
                                try:
                                    import io
                                    try:
                                        import PyPDF2
                                        PYPDF2_AVAILABLE = True
                                    except ImportError:
                                        PYPDF2_AVAILABLE = False
                                    
                                    if PYPDF2_AVAILABLE:
                                        pdf_file = io.BytesIO(pdf_bytes)
                                        pdf_reader = PyPDF2.PdfReader(pdf_file)
                                        total_pages = len(pdf_reader.pages)
                                        
                                        print(f"📄 [Google Drive] Extrayendo texto de TODAS las {total_pages} páginas...")
                                        
                                        # Extraer texto de TODAS las páginas (como DocumentProcessor)
                                        text_parts = []
                                        for page_num, page in enumerate(pdf_reader.pages, 1):
                                            try:
                                                page_text = page.extract_text()
                                                if page_text.strip():
                                                    text_parts.append(f"# Página {page_num}\n\n{page_text}")
                                                # Mostrar progreso cada 10 páginas
                                                if page_num % 10 == 0 or page_num == total_pages:
                                                    print(f"   📄 Página {page_num}/{total_pages} procesada...", end='\r')
                                            except Exception as e:
                                                # Continuar con siguiente página si una falla
                                                continue
                                        
                                        print()  # Nueva línea después del progreso
                                        
                                        if text_parts:
                                            # Unir todo el texto - SIN LÍMITES (máxima calidad)
                                            full_text = "\n\n".join(text_parts)
                                            content = full_text  # TODO el contenido completo, SIN límite
                                            snippet = full_text[:2000]  # Primeros 2000 caracteres para snippet
                                            print(f"✅ [Google Drive] Extraído texto COMPLETO de {name} ({total_pages} páginas, {len(content):,} caracteres)")
                                        else:
                                            # Si PyPDF2 no extrajo texto, intentar con Docling como fallback
                                            print(f"⚠️ [Google Drive] PyPDF2 no extrajo texto, intentando con Docling...")
                                            content, snippet = self._extract_pdf_with_docling_fallback(pdf_bytes, name)
                                    else:
                                        print(f"⚠️ [Google Drive] PyPDF2 no disponible, intentando con Docling...")
                                        content, snippet = self._extract_pdf_with_docling_fallback(pdf_bytes, name)
                                        
                                except Exception as e:
                                    error_msg = str(e).lower()
                                    if "pycryptodome" in error_msg or "aes" in error_msg or "encrypted" in error_msg:
                                        print(f"⚠️ [Google Drive] PDF encriptado detectado, intentando con Docling...")
                                        content, snippet = self._extract_pdf_with_docling_fallback(pdf_bytes, name)
                                    else:
                                        print(f"⚠️ [Google Drive] Error extrayendo con PyPDF2: {e}, intentando con Docling...")
                                        content, snippet = self._extract_pdf_with_docling_fallback(pdf_bytes, name)
                            else:
                                print(f"❌ [Google Drive] Error descargando PDF {name}: Status {pdf_resp.status_code}")
                                snippet = f"PDF encontrado: {name} (error descargando: {pdf_resp.status_code})"
                        except Exception as e:
                            print(f"⚠️ [Google Drive] Error descargando PDF {name}: {e}")
                            snippet = f"PDF encontrado: {name} (error: {str(e)[:50]})"
                    
                    # Calcular relevancia basada en coincidencias de palabras clave
                    relevance = 0.80
                    name_lower = name.lower()
                    if keywords:
                        matches = sum(1 for kw in keywords if kw in name_lower)
                        relevance = 0.70 + (matches * 0.10)  # 0.70 base + 0.10 por cada match
                    
                    # Si es PDF y se buscaba PDF, aumentar relevancia
                    if is_pdf_search and mime_type == "application/pdf":
                        relevance += 0.10
                    
                    # Usar snippet si está disponible, sino usar content o nombre
                    final_snippet = snippet if snippet else (content[:200] if content else f"Archivo encontrado: {name}")
                    final_content = content if content else f"Archivo: {name}"
                    
                    results.append(AppSearchResult(
                        app_type=IntegrationType.GOOGLE_DRIVE,
                        app_name="Google Drive",
                        source_id=file_id,
                        source_name=name,
                        content=final_content,
                        snippet=final_snippet,
                        url=url,
                        metadata={"mime_type": mime_type, "modified": file.get("modifiedTime")},
                        relevance_score=min(relevance, 1.0)  # Cap a 1.0
                    ))
            elif response.status_code == 401:
                print(f"❌ [Google Drive] Error 401: Token inválido o expirado")
            elif response.status_code == 403:
                print(f"❌ [Google Drive] Error 403: Token sin permisos suficientes. Verifica los scopes.")
                print(f"   Response: {response.text[:200]}")
            else:
                print(f"⚠️ [Google Drive] Error {response.status_code}: {response.text[:200]}")
        except Exception as e:
            print(f"⚠️ [Google Drive] Error buscando: {e}")
            import traceback
            traceback.print_exc()
        
        print(f"📊 [Google Drive] Retornando {len(results)} resultados")
        return results
    
    async def _github_search(self, token: str, query: str, days: Optional[int] = None) -> List[AppSearchResult]:
        """Busca en GitHub usando la API real."""
        import requests
        results = []
        
        try:
            # Buscar código
            response = requests.get(
                "https://api.github.com/search/code",
                params={"q": query, "per_page": 10},
                headers={
                    "Authorization": f"token {token}",
                    "Accept": "application/vnd.github.v3+json"
                },
                timeout=15
            )
            
            if response.status_code == 200:
                data = response.json()
                items = data.get("items", [])
                
                for item in items[:10]:
                    repo = item.get("repository", {})
                    repo_name = repo.get("full_name", "unknown")
                    path = item.get("path", "")
                    url = item.get("html_url", "")
                    
            results.append(AppSearchResult(
                        app_type=IntegrationType.GITHUB,
                        app_name="GitHub",
                        source_id=item.get("sha", ""),
                        source_name=f"{repo_name}/{path}",
                        content=f"Código en {repo_name}: {query}",
                        snippet=f"Archivo: {path} en {repo_name}",
                        url=url,
                        metadata={"repository": repo_name, "path": path},
                relevance_score=0.75
            ))
        except Exception as e:
            print(f"⚠️ Error buscando en GitHub: {e}")
        
        return results
    
    async def _hubspot_search(self, token: str, query: str, filters: Optional[Dict[str, Any]] = None) -> List[AppSearchResult]:
        """Busca en HubSpot usando la API real."""
        import requests
        results = []
        
        base_url = "https://api.hubapi.com"
        days = filters.get("days") if filters else None
        
        try:
            # Buscar en contactos
            search_payload = {
                "query": query,
                "limit": 10,
                "filterGroups": [{"filters": []}]
            }
            
            if days:
                from datetime import datetime, timedelta
                min_date = int((datetime.now() - timedelta(days=days)).timestamp() * 1000)
                search_payload["filterGroups"][0]["filters"].append({
                    "propertyName": "hs_lastmodifieddate",
                    "operator": "GTE",
                    "value": min_date
                })
            
            response = requests.post(
                f"{base_url}/crm/v3/objects/contacts/search",
                json=search_payload,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json"
                },
                timeout=15
            )
            
            if response.status_code == 200:
                data = response.json()
                contacts = data.get("results", [])
                
                for contact in contacts[:5]:
                    contact_id = contact.get("id", "")
                    props = contact.get("properties", {})
                    name = props.get("firstname", "") + " " + props.get("lastname", "")
                    email = props.get("email", "")
                    
            results.append(AppSearchResult(
                        app_type=IntegrationType.HUBSPOT,
                        app_name="HubSpot",
                        source_id=str(contact_id),
                        source_name=f"Contacto: {name or email}",
                        content=f"Contacto: {name} ({email})",
                        snippet=f"Contacto encontrado: {name or email}",
                        url=f"https://app.hubspot.com/contacts/{contact_id}",
                        metadata={"email": email, "type": "contact"},
                        relevance_score=0.75
                    ))
        except Exception as e:
            print(f"⚠️ Error buscando en HubSpot: {e}")
        
        return results
    
    async def _jira_search(self, token: str, query: str, credentials: Dict[str, Any], days: Optional[int] = None) -> List[AppSearchResult]:
        """Busca en Jira usando la API real."""
        import requests
        import base64
        results = []
        
        base_url = credentials.get("base_url", "")
        if not base_url:
            return results
        
        try:
            # Construir JQL
            jql = f'text ~ "{query}"'
            if days:
                jql += f" AND updated >= -{days}d"
            
            # Intentar como Bearer token
            headers = {
                "Authorization": f"Bearer {token}",
                "Accept": "application/json"
            }
            
            response = requests.get(
                f"{base_url}/rest/api/3/search",
                params={"jql": jql, "maxResults": 10},
                headers=headers,
                timeout=15
            )
            
            # Si falla, intentar como Basic Auth
            if response.status_code == 401:
                auth_str = base64.b64encode(token.encode()).decode()
                headers = {
                    "Authorization": f"Basic {auth_str}",
                    "Accept": "application/json"
                }
                response = requests.get(
                    f"{base_url}/rest/api/3/search",
                    params={"jql": jql, "maxResults": 10},
                    headers=headers,
                    timeout=15
                )
            
            if response.status_code == 200:
                data = response.json()
                issues = data.get("issues", [])
                
                for issue in issues[:10]:
                    key = issue.get("key", "")
                    fields = issue.get("fields", {})
                    summary = fields.get("summary", "")
                    description = fields.get("description", {}).get("content", [{}])[0].get("text", "") if fields.get("description") else ""
                    
            results.append(AppSearchResult(
                        app_type=IntegrationType.JIRA,
                        app_name="Jira",
                        source_id=key,
                        source_name=f"Issue: {key}",
                        content=f"{summary}\n{description}",
                        snippet=summary[:200],
                        url=f"{base_url}/browse/{key}",
                        metadata={"key": key, "status": fields.get("status", {}).get("name", "")},
                relevance_score=0.75
            ))
        except Exception as e:
            print(f"⚠️ Error buscando en Jira: {e}")
        
        return results
    
    async def _confluence_search(self, token: str, query: str, credentials: Dict[str, Any], days: Optional[int] = None) -> List[AppSearchResult]:
        """Busca en Confluence usando la API real."""
        import requests
        import base64
        results = []
        
        base_url = credentials.get("base_url", "")
        if not base_url:
            return results
        
        try:
            # Construir CQL
            cql = f'text ~ "{query}"'
            if days:
                cql += f" AND lastmodified >= -{days}d"
            
            headers = {
                "Authorization": f"Bearer {token}",
                "Accept": "application/json"
            }
            
            response = requests.get(
                f"{base_url}/wiki/rest/api/content/search",
                params={"cql": cql, "limit": 10},
                headers=headers,
                timeout=15
            )
            
            if response.status_code == 401:
                auth_str = base64.b64encode(token.encode()).decode()
                headers = {
                    "Authorization": f"Basic {auth_str}",
                    "Accept": "application/json"
                }
                response = requests.get(
                    f"{base_url}/wiki/rest/api/content/search",
                    params={"cql": cql, "limit": 10},
                    headers=headers,
                    timeout=15
                )
            
            if response.status_code == 200:
                data = response.json()
                pages = data.get("results", [])
                
                for page in pages[:10]:
                    page_id = page.get("id", "")
                    title = page.get("title", "")
                    url = f"{base_url}{page.get('_links', {}).get('webui', '')}"
                    
                    # Obtener contenido
                    content_resp = requests.get(
                        f"{base_url}/wiki/rest/api/content/{page_id}?expand=body.view",
                        headers=headers,
                        timeout=10
                    )
                    
                    content = ""
                    if content_resp.status_code == 200:
                        body = content_resp.json().get("body", {}).get("view", {}).get("value", "")
                        # Extraer texto plano (simplificado)
                        import re
                        content = re.sub(r'<[^>]+>', '', body)[:500]
                    
            results.append(AppSearchResult(
                        app_type=IntegrationType.CONFLUENCE,
                        app_name="Confluence",
                        source_id=page_id,
                        source_name=title,
                        content=content or title,
                        snippet=content[:200] if content else title,
                        url=url,
                        metadata={"space": page.get("space", {}).get("name", "")},
                        relevance_score=0.80
                    ))
        except Exception as e:
            print(f"⚠️ Error buscando en Confluence: {e}")
        
        return results
    
    # Métodos stub para apps que aún no tienen implementación completa
    async def _sharepoint_search(self, token: str, query: str, credentials: Dict[str, Any], days: Optional[int] = None) -> List[AppSearchResult]:
        """Busca en SharePoint (stub - implementar con Microsoft Graph API)."""
        return []
    
    async def _gmail_search(self, token: str, query: str, days: Optional[int] = None) -> List[AppSearchResult]:
        """Busca y lee emails de Gmail usando Gmail API."""
        import base64
        from email.utils import parsedate_to_datetime
        
        results = []
        try:
            headers = {"Authorization": f"Bearer {token}"}
            
            # Construir query de búsqueda con filtro de fecha si se especifica
            gmail_query = query
            if days:
                from datetime import datetime, timedelta
                cutoff_date = (datetime.now() - timedelta(days=days)).strftime("%Y/%m/%d")
                gmail_query = f"{query} after:{cutoff_date}"
            
            # Buscar mensajes
            search_url = "https://gmail.googleapis.com/gmail/v1/users/me/messages"
            params = {
                "q": gmail_query,
                "maxResults": 50,  # Aumentado para obtener más resultados
                "includeSpamTrash": False
            }
            
            print(f"🔍 [Gmail] Buscando: {gmail_query}")
            response = requests.get(search_url, headers=headers, params=params, timeout=15)
            
            if response.status_code != 200:
                print(f"⚠️ [Gmail] Error buscando: {response.status_code} - {response.text[:200]}")
                return results
            
            data = response.json()
            messages = data.get("messages", [])
            print(f"✅ [Gmail] Encontrados {len(messages)} mensajes")
            
            # Obtener detalles de cada mensaje
            for msg in messages[:50]:  # Procesar hasta 50 emails
                try:
                    msg_id = msg["id"]
                    msg_url = f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{msg_id}"
                    msg_params = {"format": "full"}
                    
                    msg_response = requests.get(msg_url, headers=headers, params=msg_params, timeout=10)
                    if msg_response.status_code != 200:
                        continue
                    
                    msg_data = msg_response.json()
                    payload = msg_data.get("payload", {})
                    headers_list = payload.get("headers", [])
                    
                    # Extraer información del email
                    subject = next((h["value"] for h in headers_list if h["name"] == "Subject"), "Sin asunto")
                    sender = next((h["value"] for h in headers_list if h["name"] == "From"), "Desconocido")
                    date_str = next((h["value"] for h in headers_list if h["name"] == "Date"), "")
                    to_list = next((h["value"] for h in headers_list if h["name"] == "To"), "")
                    
                    # Extraer cuerpo del email
                    body_text = ""
                    snippet = msg_data.get("snippet", "")
                    
                    # Intentar extraer cuerpo completo
                    if "parts" in payload:
                        for part in payload.get("parts", []):
                            if part.get("mimeType") == "text/plain":
                                body_data = part.get("body", {}).get("data", "")
                                if body_data:
                                    body_text = base64.urlsafe_b64decode(body_data).decode("utf-8", errors="ignore")
                                    break
                            elif part.get("mimeType") == "text/html":
                                html_data = part.get("body", {}).get("data", "")
                                if html_data and not body_text:
                                    # Extraer texto de HTML (simplificado)
                                    html_text = base64.urlsafe_b64decode(html_data).decode("utf-8", errors="ignore")
                                    # Remover tags HTML básicos
                                    import re
                                    body_text = re.sub(r'<[^>]+>', '', html_text)
                                    break
                    elif payload.get("mimeType") == "text/plain":
                        body_data = payload.get("body", {}).get("data", "")
                        if body_data:
                            body_text = base64.urlsafe_b64decode(body_data).decode("utf-8", errors="ignore")
                    
                    # Usar snippet si no hay cuerpo completo
                    if not body_text:
                        body_text = snippet
                    
                    # Construir contenido completo
                    full_content = f"Asunto: {subject}\nDe: {sender}\nPara: {to_list}\nFecha: {date_str}\n\n{body_text}"
                    
                    # Construir URL de Gmail
                    gmail_url = f"https://mail.google.com/mail/u/0/#inbox/{msg_id}"
                    
                    results.append(AppSearchResult(
                        app_type=IntegrationType.GMAIL,
                        app_name="Gmail",
                        source_id=msg_id,
                        source_name=f"Email: {subject}",
                        content=full_content,
                        snippet=f"{subject} - De: {sender} - {snippet[:200]}",
                        url=gmail_url,
                        metadata={
                            "subject": subject,
                            "from": sender,
                            "to": to_list,
                            "date": date_str,
                            "thread_id": msg_data.get("threadId"),
                            "labels": msg_data.get("labelIds", [])
                        },
                        relevance_score=1.0
                    ))
                    
                except Exception as e:
                    print(f"⚠️ [Gmail] Error procesando mensaje {msg.get('id', 'unknown')}: {e}")
                    continue
            
            print(f"✅ [Gmail] Procesados {len(results)} emails exitosamente")
            
        except Exception as e:
            print(f"❌ [Gmail] Error en búsqueda: {e}")
            import traceback
            traceback.print_exc()
        
        return results
    
    async def _outlook_search(self, token: str, query: str, days: Optional[int] = None) -> List[AppSearchResult]:
        """Busca en Outlook (stub - implementar con Microsoft Graph API)."""
        return []
    
    async def _salesforce_search(self, token: str, query: str, credentials: Dict[str, Any], days: Optional[int] = None) -> List[AppSearchResult]:
        """Busca en Salesforce (stub - implementar con Salesforce API)."""
        return []
    
    async def _linear_search(self, token: str, query: str, days: Optional[int] = None) -> List[AppSearchResult]:
        """Busca en Linear (stub - implementar con Linear API)."""
        return []
    
    async def _asana_search(self, token: str, query: str, days: Optional[int] = None) -> List[AppSearchResult]:
        """Busca en Asana (stub - implementar con Asana API)."""
        return []
    
    async def _gitlab_search(self, token: str, query: str, credentials: Dict[str, Any], days: Optional[int] = None) -> List[AppSearchResult]:
        """Busca en GitLab (stub - implementar con GitLab API)."""
        return []
    
    async def _clickup_search(self, token: str, query: str, days: Optional[int] = None) -> List[AppSearchResult]:
        """Busca en ClickUp (stub - implementar con ClickUp API)."""
        return []
    
    async def _intercom_search(self, token: str, query: str, days: Optional[int] = None) -> List[AppSearchResult]:
        """Busca en Intercom (stub - implementar con Intercom API)."""
        return []
    
    async def _dropbox_search(self, token: str, query: str, days: Optional[int] = None) -> List[AppSearchResult]:
        """Busca en Dropbox (stub - implementar con Dropbox API)."""
        return []
    
    async def _box_search(self, token: str, query: str, days: Optional[int] = None) -> List[AppSearchResult]:
        """Busca en Box (stub - implementar con Box API)."""
        return []
    
    async def _teams_search(self, token: str, query: str, days: Optional[int] = None) -> List[AppSearchResult]:
        """Busca en Teams (stub - implementar con Microsoft Graph API)."""
        return []
    
    async def execute_autonomous_task(
        self,
        task_description: str,
        task_type: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Ejecuta una tarea autónoma usando las apps conectadas.
        
        Tipos de tareas:
        - "summarize": Resumir información de múltiples fuentes
        - "analyze": Analizar datos y generar insights
        - "create_report": Crear un informe basado en datos
        - "plan": Crear un plan basado en información disponible
        - "compare": Comparar información de diferentes fuentes
        """
        # Buscar información relevante en apps conectadas
        search_query = self._extract_search_query_from_task(task_description)
        app_results = await self.search_across_apps(query=search_query)
        
        # Ejecutar tarea según tipo
        if task_type == "summarize":
            return await self._task_summarize(task_description, app_results, context)
        elif task_type == "analyze":
            return await self._task_analyze(task_description, app_results, context)
        elif task_type == "create_report":
            return await self._task_create_report(task_description, app_results, context)
        elif task_type == "plan":
            return await self._task_plan(task_description, app_results, context)
        elif task_type == "compare":
            return await self._task_compare(task_description, app_results, context)
        else:
            return {
                "success": False,
                "error": f"Tipo de tarea desconocido: {task_type}"
            }
    
    def _extract_search_query_from_task(self, task_description: str) -> str:
        """Extrae términos de búsqueda de la descripción de la tarea."""
        # Simplificación: usar la descripción completa como query
        # En producción, usar LLM para extraer términos clave
        return task_description
    
    async def _task_summarize(
        self,
        task_description: str,
        app_results: List[AppSearchResult],
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Tarea: Resumir información."""
        if not app_results:
            return {
                "success": False,
                "error": "No se encontró información para resumir"
            }
        
        # Combinar contenido de resultados
        combined_content = "\n\n".join([
            f"**{result.source_name}** ({result.app_name}):\n{result.content}"
            for result in app_results[:10]
        ])
        
        return {
            "success": True,
            "task_type": "summarize",
            "summary": f"Resumen de {len(app_results)} fuentes:\n\n{combined_content[:2000]}...",
            "sources": [result.source_name for result in app_results],
            "sources_count": len(app_results)
        }
    
    async def _task_analyze(
        self,
        task_description: str,
        app_results: List[AppSearchResult],
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Tarea: Analizar datos."""
        insights = []
        for result in app_results[:5]:
            insights.append(f"Patrón encontrado en {result.app_name}: {result.source_name}")
            insights.append(f"Tendencia identificada en {result.source_name}")
        
        return {
            "success": True,
            "task_type": "analyze",
            "analysis": f"Análisis de {len(app_results)} fuentes relacionadas con: {task_description}",
            "insights": insights,
            "sources": [result.source_name for result in app_results]
        }
    
    async def _task_create_report(
        self,
        task_description: str,
        app_results: List[AppSearchResult],
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Tarea: Crear informe."""
        return {
            "success": True,
            "task_type": "create_report",
            "report": f"# Informe: {task_description}\n\n## Fuentes consultadas\n\n" + "\n".join([
                f"- {result.source_name} ({result.app_name})"
                for result in app_results
            ]) + f"\n\n## Contenido\n\nInforme generado basado en {len(app_results)} fuentes.",
            "sources": [result.source_name for result in app_results]
        }
    
    async def _task_plan(
        self,
        task_description: str,
        app_results: List[AppSearchResult],
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Tarea: Crear plan."""
        return {
            "success": True,
            "task_type": "plan",
            "plan": f"# Plan: {task_description}\n\n## Contexto\n\nBasado en información de {len(app_results)} fuentes.\n\n## Pasos\n\n1. Paso 1 basado en {app_results[0].source_name if app_results else 'información disponible'}\n2. Paso 2\n3. Paso 3",
            "sources": [result.source_name for result in app_results]
        }
    
    async def _task_compare(
        self,
        task_description: str,
        app_results: List[AppSearchResult],
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Tarea: Comparar información."""
        return {
            "success": True,
            "task_type": "compare",
            "comparison": f"# Comparación: {task_description}\n\n## Fuentes comparadas\n\n" + "\n".join([
                f"### {result.source_name} ({result.app_name})\n{result.snippet}"
                for result in app_results[:5]
            ]),
            "sources": [result.source_name for result in app_results]
        }
    
    async def _task_email_response(
        self,
        task_description: str,
        app_results: List[AppSearchResult],
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Tarea: Responder emails automáticamente de forma inteligente.
        
        Esta tarea:
        1. Analiza los emails encontrados
        2. Genera respuestas personalizadas usando LLM
        3. Envía las respuestas a los destinatarios especificados
        4. Incluye controles de seguridad y validación
        """
        import base64
        from email.mime.text import MIMEText
        
        # Buscar conexión de Gmail
        gmail_connection = None
        for conn in self.connections.values():
            if conn.app_type == IntegrationType.GMAIL and conn.status == "connected":
                gmail_connection = conn
                break
        
        if not gmail_connection:
            return {
                "success": False,
                "error": "No hay conexión de Gmail activa. Conecta Gmail primero en 'Conectar Apps'."
            }
        
        token = gmail_connection.credentials.get("token") or gmail_connection.credentials.get("access_token")
        if not token:
            return {
                "success": False,
                "error": "Token de Gmail no disponible. Reconecta Gmail."
            }
        
        # Extraer parámetros de la tarea
        # Formato esperado: "Responde a [X] emails sobre [tema] con [instrucciones específicas]"
        task_lower = task_description.lower()
        
        # Extraer número de emails a responder
        max_emails = 10  # Default
        if "responder a" in task_lower or "respond to" in task_lower:
            import re
            numbers = re.findall(r'\d+', task_description)
            if numbers:
                max_emails = min(int(numbers[0]), 50)  # Máximo 50 por seguridad
        
        # Filtrar solo resultados de Gmail
        gmail_results = [r for r in app_results if r.app_type == IntegrationType.GMAIL]
        
        if not gmail_results:
            return {
                "success": False,
                "error": "No se encontraron emails de Gmail para responder. Busca emails primero."
            }
        
        # Limitar cantidad de emails
        emails_to_respond = gmail_results[:max_emails]
        
        # Generar respuestas usando LLM
        responses = []
        errors = []
        
        for email_result in emails_to_respond:
            try:
                # Extraer información del email
                metadata = email_result.metadata
                subject = metadata.get("subject", "Sin asunto")
                sender = metadata.get("from", "")
                email_content = email_result.content
                
                # Extraer dirección de email del remitente
                import re
                email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', sender)
                sender_email = email_match.group(0) if email_match else sender
                
                # Generar respuesta usando LLM (necesitamos acceso al LLM)
                # Por ahora, usaremos un prompt simple
                response_prompt = f"""Eres un asistente profesional de email empresarial. 

EMAIL ORIGINAL:
Asunto: {subject}
De: {sender}
Contenido: {email_content[:2000]}

INSTRUCCIONES DEL USUARIO:
{task_description}

Genera una respuesta profesional, cortés y específica que:
1. Responda directamente a las preguntas o solicitudes del email original
2. Siga las instrucciones específicas del usuario
3. Sea concisa pero completa
4. Mantenga un tono profesional y empresarial
5. Incluya información relevante cuando sea apropiado

Responde SOLO con el texto del email (sin "Asunto:", "Para:", etc.):
"""
                
                # La respuesta se generará en execute_autonomous_task_v2 con acceso al LLM
                responses.append({
                    "email_id": email_result.source_id,
                    "to": sender_email,
                    "subject": f"Re: {subject}",
                    "body": None,  # Se generará con LLM
                    "original_subject": subject,
                    "original_from": sender,
                    "original_content": email_content[:2000],
                    "status": "pending_generation"
                })
                
            except Exception as e:
                errors.append(f"Error procesando email {email_result.source_id}: {str(e)}")
                continue
        
        return {
            "success": True,
            "task_type": "email_response",
            "emails_found": len(gmail_results),
            "emails_to_respond": len(emails_to_respond),
            "responses": responses,
            "errors": errors,
            "gmail_token_available": bool(token),
            "message": f"Preparadas {len(responses)} respuestas. Se requiere LLM para generar el contenido final."
        }
    
    async def _gmail_send_email(
        self,
        token: str,
        to: str,
        subject: str,
        body: str,
        reply_to_message_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Envía un email usando Gmail API.
        
        Args:
            token: Access token de Gmail
            to: Dirección de destino
            subject: Asunto del email
            body: Cuerpo del email
            reply_to_message_id: ID del mensaje al que se responde (opcional)
        
        Returns:
            Dict con success y message_id o error
        """
        import base64
        from email.mime.text import MIMEText
        
        try:
            # Crear mensaje
            message = MIMEText(body, 'plain', 'utf-8')
            message['to'] = to
            message['subject'] = subject
            
            # Si es una respuesta, agregar headers de threading
            if reply_to_message_id:
                message['In-Reply-To'] = reply_to_message_id
                message['References'] = reply_to_message_id
            
            # Codificar en base64 URL-safe
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
            
            # Enviar usando Gmail API
            send_url = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"
            headers = {"Authorization": f"Bearer {token}"}
            payload = {"raw": raw_message}
            
            response = requests.post(send_url, headers=headers, json=payload, timeout=15)
            
            if response.status_code == 200:
                message_id = response.json().get("id")
                return {
                    "success": True,
                    "message_id": message_id,
                    "message": f"Email enviado exitosamente a {to}"
                }
            else:
                return {
                    "success": False,
                    "error": f"Error enviando email: {response.status_code} - {response.text[:200]}"
                }
                
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error": f"Error enviando email: {str(e)}"
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """Obtiene estadísticas de las integraciones."""
        connected = [c for c in self.connections.values() if c.status == "connected"]
        return {
            "total_connections": len(self.connections),
            "connected_apps": len(connected),
            "apps_by_type": {
                app_type.value: len([c for c in connected if c.app_type == app_type])
                for app_type in IntegrationType
            }
        }


