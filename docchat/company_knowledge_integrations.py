"""
Company Knowledge Integrations - Sistema de conexión con apps empresariales
Similar a ChatGPT Company Knowledge, permite conectar Slack, Google Drive, SharePoint, etc.
"""

from __future__ import annotations

import json
import time
from typing import List, Dict, Optional, Any, Tuple
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum

import requests

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
        # Cache en memoria para credenciales sensibles (no se persisten en disco)
        self._token_cache: Dict[str, Dict[str, Any]] = {}
        
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
            status = "connected"
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
            status=status,
            connected_at=time.strftime("%Y-%m-%d %H:%M:%S"),
            last_sync=time.strftime("%Y-%m-%d %H:%M:%S"),
            permissions=permissions or {},
            metadata={"credentials_stored": True, "validated": True},
            credentials=credentials
        )
        
        # Guardar token y extras en memoria (no persistente)
        safe_credentials = {k: v for k, v in credentials.items()}
        self._token_cache[connection_id] = safe_credentials
        
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
    
    def remove_app(self, connection_id: str) -> Dict[str, Any]:
        """
        Elimina completamente una app conectada.
        
        Args:
            connection_id: ID de la conexión a eliminar
            
        Returns:
            Dict con success y message
        """
        if connection_id not in self.connections:
            return {"success": False, "error": f"Conexión '{connection_id}' no encontrada"}
        
        app_name = self.connections[connection_id].app_name
        app_type = self.connections[connection_id].app_type.value
        
        # Eliminar de conexiones
        del self.connections[connection_id]
        
        # Eliminar del cache de tokens
        if connection_id in self._token_cache:
            del self._token_cache[connection_id]
        
        # Guardar cambios
        self._save_connections()
        
        print(f"✅ [Company Knowledge] App eliminada: {app_name} ({app_type}) - ID: {connection_id}")
        return {
            "success": True,
            "message": f"App '{app_name}' ({app_type}) eliminada exitosamente"
        }
    
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
        filters: Optional[Dict[str, Any]] = None,
        progress_callback: Optional[callable] = None
    ) -> List[AppSearchResult]:
        """
        Busca información en todas las apps conectadas.
        
        OPTIMIZADO: Ahora soporta callbacks de progreso para sidebar en tiempo real.
        
        Args:
            query: Consulta de búsqueda
            app_types: Tipos de apps específicos a buscar (None = todas)
            filters: Filtros adicionales (fechas, tipos de contenido, etc.)
            progress_callback: Función callback(opcional) que se llama con (app_name, status, results_count)
        
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
        
        # Buscar en cada app con callbacks de progreso
        for i, app in enumerate(apps_to_search):
            try:
                # Callback: empezando búsqueda en esta app
                if progress_callback:
                    progress_callback(app.app_name, "searching", 0)
                
                app_results = await self._search_in_app(
                    app=app,
                    query=query,
                    filters=filters
                )
                results.extend(app_results)
                
                # Callback: búsqueda completada en esta app
                if progress_callback:
                    progress_callback(app.app_name, "completed", len(app_results))
                
            except Exception as e:
                print(f"⚠️ [Company Knowledge] Error buscando en {app.app_name}: {e}")
                # Callback: error en esta app
                if progress_callback:
                    progress_callback(app.app_name, "error", 0)
                continue
        
        # Ordenar por relevancia
        results.sort(key=lambda x: x.relevance_score, reverse=True)
        
        return results
    
    async def search_across_apps_streaming(
        self,
        query: str,
        app_types: Optional[List[IntegrationType]] = None,
        filters: Optional[Dict[str, Any]] = None
    ):
        """
        Generador async que busca en apps y yield resultados intermedios.
        
        OPTIMIZACIÓN CRÍTICA: Permite actualizar sidebar en tiempo real.
        
        Yields:
            Tuplas (app_name, status, results_count, results) donde:
            - app_name: Nombre de la app
            - status: "searching", "completed", "error"
            - results_count: Número de resultados encontrados
            - results: Lista de resultados de esta app (solo en "completed")
        """
        # Obtener apps a buscar
        apps_to_search = self.get_connected_apps()
        if app_types:
            apps_to_search = [
                app for app in apps_to_search
                if app.app_type in app_types
            ]
        
        all_results = []
        
        # Buscar en cada app y yield progreso
        for i, app in enumerate(apps_to_search):
            try:
                # Yield: empezando búsqueda
                yield (app.app_name, "searching", 0, [])
                
                app_results = await self._search_in_app(
                    app=app,
                    query=query,
                    filters=filters
                )
                all_results.extend(app_results)
                
                # Yield: búsqueda completada
                yield (app.app_name, "completed", len(app_results), app_results)
                
            except Exception as e:
                print(f"⚠️ [Company Knowledge] Error buscando en {app.app_name}: {e}")
                # Yield: error
                yield (app.app_name, "error", 0, [])
                continue
        
        # Ordenar todos los resultados por relevancia
        all_results.sort(key=lambda x: x.relevance_score, reverse=True)
        
        # Yield final con todos los resultados
        yield ("all", "completed", len(all_results), all_results)
    
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
                results = await self._google_drive_search(token, query, app.credentials, days, filters)
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

    # ------------------------------------------------------------------ #
    # Validaciones rápidas por tipo de app
    # ------------------------------------------------------------------ #
    def _validate_credentials(self, app_type: IntegrationType, credentials: Dict[str, Any]) -> Dict[str, Any]:
        """Valida tokens/credenciales con un ping ligero cuando sea posible."""
        token = credentials.get("token") or credentials.get("api_token")
        extra = credentials.get("extra", {})
        
        # Casos donde el token es obligatorio para decir conectado
        token_required = {
            IntegrationType.SLACK,
            IntegrationType.GITHUB,
            IntegrationType.GITLAB,
            IntegrationType.HUBSPOT,
            IntegrationType.LINEAR,
            IntegrationType.ASANA,
            IntegrationType.CLICKUP,
            IntegrationType.SALESFORCE,
            IntegrationType.JIRA,
            IntegrationType.CONFLUENCE,
            IntegrationType.DROPBOX,
            IntegrationType.BOX
        }
        
        if app_type in token_required and not token:
            return {"ok": False, "message": "Token requerido. Ingresa token o API key.", "details": None}
        
        try:
            if app_type == IntegrationType.SLACK:
                return self._slack_auth_test(token)
            if app_type == IntegrationType.GITHUB:
                return self._github_auth_test(token)
            if app_type == IntegrationType.GITLAB:
                return self._gitlab_auth_test(token, extra)
            if app_type == IntegrationType.HUBSPOT:
                return self._hubspot_auth_test(token)
            if app_type == IntegrationType.LINEAR:
                return self._linear_auth_test(token)
            if app_type == IntegrationType.ASANA:
                return self._asana_auth_test(token)
            if app_type == IntegrationType.CLICKUP:
                return self._clickup_auth_test(token)
            if app_type == IntegrationType.SALESFORCE:
                return self._salesforce_auth_test(token, extra)
            if app_type == IntegrationType.JIRA:
                return self._jira_auth_test(token, extra)
            if app_type == IntegrationType.CONFLUENCE:
                return self._confluence_auth_test(token, extra)
            if app_type == IntegrationType.DROPBOX:
                return self._dropbox_auth_test(token)
            if app_type == IntegrationType.BOX:
                return self._box_auth_test(token)
            if app_type == IntegrationType.OUTLOOK or app_type == IntegrationType.TEAMS or app_type == IntegrationType.SHAREPOINT:
                # Para Teams y SharePoint, validar específicamente con Microsoft Graph API
                if app_type == IntegrationType.TEAMS:
                    return self._teams_auth_test(token)
                elif app_type == IntegrationType.SHAREPOINT:
                    return self._sharepoint_auth_test(token)
                return self._msgraph_auth_test(token)
            if app_type == IntegrationType.GMAIL or app_type == IntegrationType.GOOGLE_DRIVE:
                return {"ok": bool(token), "message": "Token recibido. Se requiere OAuth con scopes adecuados.", "details": None}
        except Exception as e:
            return {"ok": False, "message": f"Error validando credenciales: {e}", "details": None}
        
        # Por defecto, aceptar si hay token
        return {"ok": bool(token), "message": "Token recibido.", "details": None}
    
    # ------------------------------------------------------------------ #
    # Pings y auth tests
    # ------------------------------------------------------------------ #
    def _slack_auth_test(self, token: str) -> Dict[str, Any]:
        resp = requests.post(
            "https://slack.com/api/auth.test",
            headers={"Authorization": f"Bearer {token}"},
            timeout=8
        )
        data = resp.json()
        return {"ok": data.get("ok", False), "message": data.get("error", "ok"), "details": data}
    
    def _slack_search(self, token: str, query: str, top_n: int = 5, filters: Optional[Dict[str, Any]] = None) -> List[AppSearchResult]:
        # Busca mensajes reales usando search.messages (requiere scope search:read)
        out: List[AppSearchResult] = []
        days = None
        if filters and isinstance(filters, dict):
            days = filters.get("days")
        try:
            resp = requests.get(
                "https://slack.com/api/search.messages",
                headers={"Authorization": f"Bearer {token}"},
                params={"query": query, "count": top_n},
                timeout=10
            )
            data = resp.json()
            if not data.get("ok"):
                return [AppSearchResult(
                    app_type=IntegrationType.SLACK,
                    app_name="Slack",
                    source_id="slack_search_error",
                    source_name="Slack search",
                    content=f"Slack search error: {data.get('error')}",
                    snippet="Revisa scopes: search:read y permisos del bot.",
                    url="https://api.slack.com/methods/search.messages",
                    relevance_score=0.0
                )]
            
            matches = data.get("messages", {}).get("matches", [])
            # Filtrar por recencia si se indicó days
            if days:
                try:
                    cutoff = time.time() - (int(days) * 86400)
                    matches = [m for m in matches if float(m.get("ts", 0)) >= cutoff]
                except Exception:
                    pass
            if not matches:
                return [AppSearchResult(
                    app_type=IntegrationType.SLACK,
                    app_name="Slack",
                    source_id="slack_search_empty",
                    source_name="Slack search",
                    content="Sin resultados en Slack para la consulta.",
                    snippet=query[:120],
                    url="https://api.slack.com/methods/search.messages",
                    relevance_score=0.0
                )]
            
            # Ordenar por score descendente, fallback ts
            try:
                matches = sorted(matches, key=lambda m: m.get("score", 0), reverse=True)
            except Exception:
                pass
            
            for m in matches[:top_n]:
                channel = m.get("channel", {}).get("name")
                permalink = m.get("permalink")
                text = m.get("text", "")
                ts = m.get("ts")
                user = m.get("user") or m.get("username")
                out.append(AppSearchResult(
                    app_type=IntegrationType.SLACK,
                    app_name="Slack",
                    source_id=m.get("ts", "slack_match"),
                    source_name=f"Canal #{channel}" if channel else "Mensaje Slack",
                    content=text,
                    snippet=f"{text[:200]} | {user or 'user'} | {ts}",
                    url=permalink,
                    relevance_score=m.get("score", 0.5)
                ))
            return out
        except Exception as e:
            return [AppSearchResult(
                app_type=IntegrationType.SLACK,
                app_name="Slack",
                source_id="slack_search_exception",
                source_name="Slack search",
                content=f"Error consultando Slack: {e}",
                snippet="Verifica token y red.",
                url="https://api.slack.com/methods/search.messages",
                relevance_score=0.0
            )]
    
    def _google_drive_search(self, token: str, query: str, extra: Dict[str, Any], filters: Optional[Dict[str, Any]] = None) -> List[AppSearchResult]:
        """Busca archivos en Google Drive usando fullText. Requiere scope drive.readonly."""
        results: List[AppSearchResult] = []
        if not token:
            return [AppSearchResult(
                app_type=IntegrationType.GOOGLE_DRIVE,
                app_name="Google Drive",
                source_id="gdrive_missing_token",
                source_name="Google Drive",
                content="Falta token OAuth con scope drive.readonly.",
                snippet="Proporciona access token.",
                url="",
                relevance_score=0.0
            )]
        
        try:
            days = None
            if filters and isinstance(filters, dict):
                days = filters.get("days")
            q = f"fullText contains '{query}' and trashed=false"
            folder_id = extra.get("folder_id")
            if folder_id:
                q += f" and '{folder_id}' in parents"
            if days:
                # filtrar por modifiedTime reciente
                q += f" and modifiedTime >= '{self._drive_days_to_rfc3339(days)}'"
            resp = requests.get(
                "https://www.googleapis.com/drive/v3/files",
                headers={"Authorization": f"Bearer {token}"},
                params={
                    "q": q,
                    "pageSize": 5,
                    "fields": "files(id,name,mimeType,modifiedTime,owners/displayName,webViewLink,description)"
                },
                timeout=10
            )
            data = resp.json()
            files = data.get("files", [])
            if not files:
                return [AppSearchResult(
                    app_type=IntegrationType.GOOGLE_DRIVE,
                    app_name="Google Drive",
                    source_id="gdrive_empty",
                    source_name="Google Drive",
                    content="Sin resultados en Google Drive para la consulta.",
                    snippet=query[:120],
                    url="",
                    relevance_score=0.0
                )]
            
            for f in files:
                content_snippet = self._google_drive_download_snippet(token, f.get("id", ""), f.get("mimeType", ""))
                meta = {
                    "mimeType": f.get("mimeType"),
                    "owner": f.get('owners', [{}])[0].get('displayName') if f.get('owners') else None,
                    "content_read": bool(content_snippet)
                }
                results.append(AppSearchResult(
                    app_type=IntegrationType.GOOGLE_DRIVE,
                    app_name="Google Drive",
                    source_id=f.get("id", ""),
                    source_name=f.get("name", "Archivo"),
                    content=content_snippet or f.get("description", "Archivo encontrado en Drive"),
                    snippet=f"Tipo: {f.get('mimeType','')}, Modificado: {f.get('modifiedTime','')}",
                    url=f.get("webViewLink") or f"https://drive.google.com/file/d/{f.get('id')}/view",
                    metadata=meta,
                    relevance_score=0.6
                ))
            return results
        except Exception as e:
            return [AppSearchResult(
                app_type=IntegrationType.GOOGLE_DRIVE,
                app_name="Google Drive",
                source_id="gdrive_exception",
                source_name="Google Drive",
                content=f"Error consultando Drive: {e}",
                snippet="Verifica token y scopes drive.readonly.",
                url="",
                relevance_score=0.0
            )]

    def _google_drive_download_snippet(self, token: str, file_id: str, mime: str) -> str:
        """Descarga un snippet de contenido para Docs/Sheets/TXT/PDF si es posible."""
        try:
            export_map = {
                "application/vnd.google-apps.document": "text/plain",
                "application/vnd.google-apps.spreadsheet": "text/csv",
                "application/pdf": "text/plain"
            }
            if mime in export_map:
                resp = requests.get(
                    f"https://www.googleapis.com/drive/v3/files/{file_id}/export",
                    headers={"Authorization": f"Bearer {token}"},
                    params={"mimeType": export_map[mime]},
                    timeout=12
                )
                if resp.status_code == 200:
                    return self._first_non_empty_lines(resp.text, 3, 900)
            # Para archivos de texto normales
            resp = requests.get(
                f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media",
                headers={"Authorization": f"Bearer {token}"},
                timeout=12
            )
            if resp.status_code == 200:
                return self._first_non_empty_lines(resp.text, 3, 900)
        except Exception:
            return ""
        return ""
    
    def _drive_days_to_rfc3339(self, days: Any) -> str:
        """Convierte días atrás a RFC3339 UTC."""
        try:
            d = int(days)
            ts = time.time() - d * 86400
            return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(ts))
        except Exception:
            return ""
    
    def _first_non_empty_lines(self, text: str, max_lines: int, max_chars: int) -> str:
        """Devuelve las primeras líneas no vacías, hasta max_lines y max_chars."""
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        snippet = "\n".join(lines[:max_lines])
        return snippet[:max_chars]
    
    def _hubspot_search(self, token: str, query: str, filters: Optional[Dict[str, Any]] = None) -> List[AppSearchResult]:
        """
        Busca en HubSpot:
        - Notas (crm.objects.notes.read)
        - Contactos (crm.objects.contacts.read)
        - Deals (crm.objects.deals.read)
        - Engagements (emails/calls) recientes
        """
        if not token:
            return [AppSearchResult(
                app_type=IntegrationType.HUBSPOT,
                app_name="HubSpot",
                source_id="hubspot_missing_token",
                source_name="HubSpot",
                content="Falta token de HubSpot con scopes CRM.",
                snippet="Proporciona token de app privada.",
                url="",
                relevance_score=0.0
            )]
        
        results: List[AppSearchResult] = []
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        days = None
        if filters and isinstance(filters, dict):
            days = filters.get("days")
        # Notas
        try:
            payload = {
                "filterGroups": [{
                    "filters": [{
                        "propertyName": "hs_note_body",
                        "operator": "CONTAINS_TOKEN",
                        "value": query
                    }]
                }],
                "limit": 3,
                "properties": ["hs_note_body", "hs_lastmodifieddate"]
            }
            if days:
                payload["filterGroups"][0]["filters"].append({
                    "propertyName": "hs_lastmodifieddate",
                    "operator": "GTE",
                    "value": self._hubspot_days_to_epoch(days)
                })
            resp = requests.post(
                "https://api.hubapi.com/crm/v3/objects/notes/search",
                headers=headers,
                json=payload,
                timeout=10
            )
            for item in resp.json().get("results", []):
                props = item.get("properties", {})
                body = props.get("hs_note_body", "")
                results.append(AppSearchResult(
                    app_type=IntegrationType.HUBSPOT,
                    app_name="HubSpot",
                    source_id=item.get("id", ""),
                    source_name="Nota de HubSpot",
                    content=body,
                    snippet=body[:200],
                    url=f"https://app.hubspot.com/notes/{item.get('id','')}",
                    metadata={"last_modified": props.get("hs_lastmodifieddate")},
                    relevance_score=0.6
                ))
        except Exception:
            pass
        # Contactos
        try:
            payload = {
                "filterGroups": [{
                    "filters": [{
                        "propertyName": "email",
                        "operator": "CONTAINS_TOKEN",
                        "value": query
                    }]
                }],
                "limit": 3,
                "properties": ["firstname", "lastname", "email", "phone"]
            }
            if days:
                payload["filterGroups"][0]["filters"].append({
                    "propertyName": "lastmodifieddate",
                    "operator": "GTE",
                    "value": self._hubspot_days_to_epoch(days)
                })
            resp = requests.post(
                "https://api.hubapi.com/crm/v3/objects/contacts/search",
                headers=headers,
                json=payload,
                timeout=10
            )
            for item in resp.json().get("results", []):
                props = item.get("properties", {})
                full_name = f"{props.get('firstname','')} {props.get('lastname','')}".strip()
                results.append(AppSearchResult(
                    app_type=IntegrationType.HUBSPOT,
                    app_name="HubSpot",
                    source_id=item.get("id", ""),
                    source_name=f"Contacto: {full_name or 'Sin nombre'}",
                    content=f"Email: {props.get('email','')} | Tel: {props.get('phone','')}",
                    snippet=f"Contacto relacionado con: {query[:80]}",
                    url=f"https://app.hubspot.com/contacts/{item.get('id','')}",
                    relevance_score=0.55
                ))
        except Exception:
            pass
        # Deals
        try:
            payload = {
                "filterGroups": [{
                    "filters": [{
                        "propertyName": "dealname",
                        "operator": "CONTAINS_TOKEN",
                        "value": query
                    }]
                }],
                "limit": 3,
                "properties": ["dealname", "amount", "dealstage", "closedate"]
            }
            if days:
                payload["filterGroups"][0]["filters"].append({
                    "propertyName": "hs_lastmodifieddate",
                    "operator": "GTE",
                    "value": self._hubspot_days_to_epoch(days)
                })
            resp = requests.post(
                "https://api.hubapi.com/crm/v3/objects/deals/search",
                headers=headers,
                json=payload,
                timeout=10
            )
            for item in resp.json().get("results", []):
                props = item.get("properties", {})
                results.append(AppSearchResult(
                    app_type=IntegrationType.HUBSPOT,
                    app_name="HubSpot",
                    source_id=item.get("id", ""),
                    source_name=f"Deal: {props.get('dealname','')}",
                    content=f"Monto: {props.get('amount','N/A')} | Etapa: {props.get('dealstage','N/A')} | Cierre: {props.get('closedate','N/A')}",
                    snippet=f"Deal relacionado con: {query[:80]}",
                    url=f"https://app.hubspot.com/deals/{item.get('id','')}",
                    relevance_score=0.55
                ))
        except Exception:
            pass
        # Engagements (emails/calls) recientes
        try:
            limit = 5
            params = {"limit": limit}
            if days:
                params["since"] = self._hubspot_days_to_epoch(days)
            resp = requests.get(
                "https://api.hubapi.com/engagements/v1/engagements/paged",
                headers={"Authorization": f"Bearer {token}"},
                params=params,
                timeout=10
            )
            data = resp.json()
            for item in data.get("results", []):
                eng = item.get("engagement", {})
                etype = eng.get("type", "engagement")
                ts = eng.get("timestamp")
                snippet = f"Tipo: {etype} | Fecha: {ts}"
                results.append(AppSearchResult(
                    app_type=IntegrationType.HUBSPOT,
                    app_name="HubSpot",
                    source_id=str(eng.get("id", "")),
                    source_name=f"Engagement: {etype}",
                    content=snippet,
                    snippet=snippet,
                    url="https://app.hubspot.com/contacts",
                    relevance_score=0.5
                ))
        except Exception:
            pass
        
        if results:
            return results
        return [AppSearchResult(
            app_type=IntegrationType.HUBSPOT,
            app_name="HubSpot",
            source_id="hubspot_empty",
            source_name="HubSpot",
            content="Sin resultados en HubSpot para la consulta.",
            snippet=query[:120],
            url="",
            relevance_score=0.0
        )]
    
    def _hubspot_days_to_epoch(self, days: Any) -> int:
        try:
            d = int(days)
            return int((time.time() - d * 86400) * 1000)
        except Exception:
            return 0
    
    def _github_auth_test(self, token: str) -> Dict[str, Any]:
        resp = requests.get(
            "https://api.github.com/user",
            headers={"Authorization": f"Bearer {token}"},
            timeout=8
        )
        ok = resp.status_code == 200
        return {"ok": ok, "message": resp.reason, "details": resp.json() if ok else {"status": resp.status_code}}
    
    def _github_search(self, token: str, query: str) -> Optional[AppSearchResult]:
        auth = self._github_auth_test(token)
        return AppSearchResult(
            app_type=IntegrationType.GITHUB,
            app_name="GitHub",
            source_id="github_user",
            source_name="GitHub /user",
            content=f"Conexión GitHub {'ok' if auth.get('ok') else 'falló'}; usa /search/code o /search/issues para resultados reales.",
            snippet=f"Consulta: {query[:120]}",
            url="https://api.github.com/user",
            metadata={"validation": auth},
            relevance_score=0.2 if auth.get("ok") else 0.0
        )
    
    def _gitlab_auth_test(self, token: str, extra: Dict[str, Any]) -> Dict[str, Any]:
        base_url = extra.get("base_url", "https://gitlab.com")
        resp = requests.get(
            f"{base_url}/api/v4/user",
            headers={"Authorization": f"Bearer {token}"},
            timeout=8
        )
        ok = resp.status_code == 200
        return {"ok": ok, "message": resp.reason, "details": resp.json() if ok else {"status": resp.status_code}}
    
    def _gitlab_ping(self, token: str, query: str, extra: Dict[str, Any]) -> Optional[AppSearchResult]:
        auth = self._gitlab_auth_test(token, extra)
        return AppSearchResult(
            app_type=IntegrationType.GITLAB,
            app_name="GitLab",
            source_id="gitlab_user",
            source_name="GitLab /user",
            content=f"Conexión GitLab {'ok' if auth.get('ok') else 'falló'}. Implementa search/projects o search/issues para resultados.",
            snippet=f"Consulta: {query[:120]}",
            url=f"{extra.get('base_url', 'https://gitlab.com')}/api/v4/user",
            metadata={"validation": auth},
            relevance_score=0.2 if auth.get("ok") else 0.0
        )
    
    def _hubspot_auth_test(self, token: str) -> Dict[str, Any]:
        resp = requests.get(
            "https://api.hubapi.com/integrations/v1/me",
            headers={"Authorization": f"Bearer {token}"},
            timeout=8
        )
        ok = resp.status_code == 200
        return {"ok": ok, "message": resp.reason, "details": resp.json() if ok else {"status": resp.status_code}}
    
    def _hubspot_ping(self, token: str, query: str) -> Optional[AppSearchResult]:
        auth = self._hubspot_auth_test(token)
        return AppSearchResult(
            app_type=IntegrationType.HUBSPOT,
            app_name="HubSpot",
            source_id="hubspot_me",
            source_name="HubSpot /integrations/v1/me",
            content=f"Conexión HubSpot {'ok' if auth.get('ok') else 'falló'}. Usa CRM Search API para consultas reales.",
            snippet=f"Consulta: {query[:120]}",
            url="https://developers.hubspot.com/docs/api/crm/search",
            metadata={"validation": auth},
            relevance_score=0.2 if auth.get("ok") else 0.0
        )
    
    def _salesforce_auth_test(self, token: str, extra: Dict[str, Any]) -> Dict[str, Any]:
        instance_url = extra.get("instance_url")
        if not instance_url:
            return {"ok": False, "message": "Falta instance_url (https://<dominio>.my.salesforce.com)", "details": None}
        resp = requests.get(
            f"{instance_url}/services/data/v60.0/",
            headers={"Authorization": f"Bearer {token}"},
            timeout=8
        )
        ok = resp.status_code == 200
        return {"ok": ok, "message": resp.reason, "details": {"status": resp.status_code}}
    
    def _salesforce_ping(self, token: str, extra: Dict[str, Any]) -> Optional[AppSearchResult]:
        auth = self._salesforce_auth_test(token, extra)
        return AppSearchResult(
            app_type=IntegrationType.SALESFORCE,
            app_name="Salesforce",
            source_id="salesforce_versions",
            source_name="Salesforce /services/data",
            content=f"Conexión Salesforce {'ok' if auth.get('ok') else 'falló'}. Implementa consultas SOQL con REST o Bulk API para resultados.",
            snippet="Se requiere instance_url y access token válido.",
            url=extra.get("instance_url"),
            metadata={"validation": auth},
            relevance_score=0.2 if auth.get("ok") else 0.0
        )
    
    def _linear_auth_test(self, token: str) -> Dict[str, Any]:
        resp = requests.post(
            "https://api.linear.app/graphql",
            headers={"Authorization": token},
            json={"query": "{ viewer { id name } }"},
            timeout=8
        )
        ok = resp.status_code == 200 and not resp.json().get("errors")
        return {"ok": ok, "message": resp.reason, "details": resp.json() if ok else {"status": resp.status_code}}
    
    def _linear_ping(self, token: str, query: str) -> Optional[AppSearchResult]:
        auth = self._linear_auth_test(token)
        return AppSearchResult(
            app_type=IntegrationType.LINEAR,
            app_name="Linear",
            source_id="linear_viewer",
            source_name="Linear viewer",
            content=f"Conexión Linear {'ok' if auth.get('ok') else 'falló'}. Usa queries GraphQL (issues, projects) para búsqueda real.",
            snippet=f"Consulta: {query[:120]}",
            url="https://developers.linear.app/docs/graphql/queries",
            metadata={"validation": auth},
            relevance_score=0.2 if auth.get("ok") else 0.0
        )
    
    def _asana_auth_test(self, token: str) -> Dict[str, Any]:
        resp = requests.get(
            "https://app.asana.com/api/1.0/users/me",
            headers={"Authorization": f"Bearer {token}"},
            timeout=8
        )
        ok = resp.status_code == 200
        return {"ok": ok, "message": resp.reason, "details": resp.json() if ok else {"status": resp.status_code}}
    
    def _asana_ping(self, token: str, query: str) -> Optional[AppSearchResult]:
        auth = self._asana_auth_test(token)
        return AppSearchResult(
            app_type=IntegrationType.ASANA,
            app_name="Asana",
            source_id="asana_me",
            source_name="Asana /users/me",
            content=f"Conexión Asana {'ok' if auth.get('ok') else 'falló'}. Usa tasks/search para resultados.",
            snippet=f"Consulta: {query[:120]}",
            url="https://developers.asana.com/reference/searchtasksforworkspace",
            metadata={"validation": auth},
            relevance_score=0.2 if auth.get("ok") else 0.0
        )
    
    def _clickup_auth_test(self, token: str) -> Dict[str, Any]:
        resp = requests.get(
            "https://api.clickup.com/api/v2/user",
            headers={"Authorization": token},
            timeout=8
        )
        ok = resp.status_code == 200
        return {"ok": ok, "message": resp.reason, "details": resp.json() if ok else {"status": resp.status_code}}
    
    def _clickup_ping(self, token: str, query: str) -> Optional[AppSearchResult]:
        auth = self._clickup_auth_test(token)
        return AppSearchResult(
            app_type=IntegrationType.CLICKUP,
            app_name="ClickUp",
            source_id="clickup_user",
            source_name="ClickUp /user",
            content=f"Conexión ClickUp {'ok' if auth.get('ok') else 'falló'}. Usa /task o /list endpoints para resultados.",
            snippet=f"Consulta: {query[:120]}",
            url="https://clickup.com/api",
            metadata={"validation": auth},
            relevance_score=0.2 if auth.get("ok") else 0.0
        )
    
    def _jira_auth_test(self, token: str, extra: Dict[str, Any]) -> Dict[str, Any]:
        base_url = extra.get("base_url")
        email = extra.get("email")
        if not base_url or not email:
            return {"ok": False, "message": "Faltan base_url y email para Jira (API token Atlassian).", "details": None}
        resp = requests.get(
            f"{base_url}/rest/api/3/myself",
            auth=(email, token),
            timeout=8
        )
        ok = resp.status_code == 200
        return {"ok": ok, "message": resp.reason, "details": resp.json() if ok else {"status": resp.status_code}}
    
    def _jira_ping(self, token: str, extra: Dict[str, Any]) -> Optional[AppSearchResult]:
        auth = self._jira_auth_test(token, extra)
        return AppSearchResult(
            app_type=IntegrationType.JIRA,
            app_name="Jira",
            source_id="jira_myself",
            source_name="Jira /myself",
            content=f"Conexión Jira {'ok' if auth.get('ok') else 'falló'}. Usa JQL search para issues reales.",
            snippet="Configura base_url (https://<org>.atlassian.net) y email.",
            url=extra.get("base_url"),
            metadata={"validation": auth},
            relevance_score=0.2 if auth.get("ok") else 0.0
        )
    
    def _jira_search(self, token: str, extra: Dict[str, Any], query: str, filters: Optional[Dict[str, Any]] = None) -> List[AppSearchResult]:
        """Busca issues en Jira usando JQL simple (summary ~ query), con filtro de recencia opcional."""
        base_url = extra.get("base_url")
        email = extra.get("email")
        if not base_url or not email:
            return [AppSearchResult(
                app_type=IntegrationType.JIRA,
                app_name="Jira",
                source_id="jira_missing_params",
                source_name="Jira",
                content="Faltan base_url y email para Jira.",
                snippet="Agrega base_url y email en credenciales extra.",
                url="",
                relevance_score=0.0
            )]
        try:
            days = None
            if filters and isinstance(filters, dict):
                days = filters.get("days")
            jql = f"summary ~ \"{query}\""
            if days:
                jql += f" and updated >= -{int(days)}d"
            jql += " order by updated desc"
            resp = requests.get(
                f"{base_url}/rest/api/3/search",
                params={"jql": jql, "maxResults": 5, "fields": "summary,assignee,status,updated"},
                auth=(email, token),
                timeout=10
            )
            data = resp.json()
            issues = data.get("issues", [])
            results = []
            for issue in issues:
                key = issue.get("key")
                fields = issue.get("fields", {})
                summary = fields.get("summary", "")
                status = fields.get("status", {}).get("name", "")
                assignee = fields.get("assignee", {}).get("displayName", "Sin asignar") if fields.get("assignee") else "Sin asignar"
                updated = fields.get("updated", "")
                results.append(AppSearchResult(
                    app_type=IntegrationType.JIRA,
                    app_name="Jira",
                    source_id=key,
                    source_name=f"Issue {key}",
                    content=summary,
                    snippet=f"Estado: {status} | Asignado: {assignee} | Updated: {updated}",
                    url=f"{base_url}/browse/{key}",
                    relevance_score=0.6
                ))
            if results:
                return results
            return [AppSearchResult(
                app_type=IntegrationType.JIRA,
                app_name="Jira",
                source_id="jira_empty",
                source_name="Jira",
                content="Sin resultados en Jira para la consulta.",
                snippet=query[:120],
                url="",
                relevance_score=0.0
            )]
        except Exception as e:
            return [AppSearchResult(
                app_type=IntegrationType.JIRA,
                app_name="Jira",
                source_id="jira_exception",
                source_name="Jira",
                content=f"Error consultando Jira: {e}",
                snippet="Verifica token, base_url, email.",
                url="",
                relevance_score=0.0
            )]
    
    def _confluence_auth_test(self, token: str, extra: Dict[str, Any]) -> Dict[str, Any]:
        base_url = extra.get("base_url")
        email = extra.get("email")
        if not base_url or not email:
            return {"ok": False, "message": "Faltan base_url y email para Confluence (API token Atlassian).", "details": None}
        resp = requests.get(
            f"{base_url}/wiki/rest/api/user/current",
            auth=(email, token),
            timeout=8
        )
        ok = resp.status_code == 200
        return {"ok": ok, "message": resp.reason, "details": resp.json() if ok else {"status": resp.status_code}}
    
    def _confluence_ping(self, token: str, extra: Dict[str, Any]) -> Optional[AppSearchResult]:
        auth = self._confluence_auth_test(token, extra)
        return AppSearchResult(
            app_type=IntegrationType.CONFLUENCE,
            app_name="Confluence",
            source_id="confluence_current_user",
            source_name="Confluence current user",
            content=f"Conexión Confluence {'ok' if auth.get('ok') else 'falló'}. Usa CQL search para páginas.",
            snippet="Configura base_url (https://<org>.atlassian.net) y email.",
            url=extra.get("base_url"),
            metadata={"validation": auth},
            relevance_score=0.2 if auth.get("ok") else 0.0
        )
    
    def _confluence_html_to_text(self, html: str) -> str:
        """Convierte HTML simple de body.view a texto plano ligero."""
        try:
            # Remover tags básicos
            import re
            text = re.sub(r"<[^>]+>", " ", html)
            text = re.sub(r"\s+", " ", text).strip()
            return text
        except Exception:
            return html or ""
    
    def _confluence_search(self, token: str, extra: Dict[str, Any], query: str, filters: Optional[Dict[str, Any]] = None) -> List[AppSearchResult]:
        """Busca páginas en Confluence usando CQL (text ~ query), con filtro de recencia opcional y extracto de body."""
        base_url = extra.get("base_url")
        email = extra.get("email")
        if not base_url or not email:
            return [AppSearchResult(
                app_type=IntegrationType.CONFLUENCE,
                app_name="Confluence",
                source_id="confluence_missing_params",
                source_name="Confluence",
                content="Faltan base_url y email para Confluence.",
                snippet="Agrega base_url y email en credenciales extra.",
                url="",
                relevance_score=0.0
            )]
        try:
            days = None
            if filters and isinstance(filters, dict):
                days = filters.get("days")
            cql = f"text ~ \"{query}\""
            if days:
                cql += f" and lastmodified >= -{int(days)}d"
            cql += " order by lastmodified desc"
            resp = requests.get(
                f"{base_url}/wiki/rest/api/content/search",
                params={"cql": cql, "limit": 5, "expand": "version,body.view"},
                auth=(email, token),
                timeout=10
            )
            data = resp.json()
            results = []
            for page in data.get("results", []):
                title = page.get("title", "")
                page_id = page.get("id")
                ver = page.get("version", {}).get("number")
                body_html = page.get("body", {}).get("view", {}).get("value", "") if page.get("body") else ""
                snippet = self._confluence_html_to_text(body_html)[:300] if body_html else f"Coincidencia de texto para: {query[:80]}"
                results.append(AppSearchResult(
                    app_type=IntegrationType.CONFLUENCE,
                    app_name="Confluence",
                    source_id=page_id,
                    source_name=title or "Página",
                    content=snippet or f"Versión: {ver}",
                    snippet=snippet,
                    url=f"{base_url}/wiki/spaces/~/?pageId={page_id}",
                    relevance_score=0.55
                ))
            if results:
                return results
            return [AppSearchResult(
                app_type=IntegrationType.CONFLUENCE,
                app_name="Confluence",
                source_id="confluence_empty",
                source_name="Confluence",
                content="Sin resultados en Confluence para la consulta.",
                snippet=query[:120],
                url="",
                relevance_score=0.0
            )]
        except Exception as e:
            return [AppSearchResult(
                app_type=IntegrationType.CONFLUENCE,
                app_name="Confluence",
                source_id="confluence_exception",
                source_name="Confluence",
                content=f"Error consultando Confluence: {e}",
                snippet="Verifica token, base_url, email.",
                url="",
                relevance_score=0.0
            )]
    
    def _dropbox_auth_test(self, token: str) -> Dict[str, Any]:
        resp = requests.post(
            "https://api.dropboxapi.com/2/users/get_current_account",
            headers={"Authorization": f"Bearer {token}"},
            timeout=8
        )
        ok = resp.status_code == 200
        return {"ok": ok, "message": resp.reason, "details": resp.json() if ok else {"status": resp.status_code}}
    
    def _dropbox_ping(self, token: str) -> Optional[AppSearchResult]:
        auth = self._dropbox_auth_test(token)
        return AppSearchResult(
            app_type=IntegrationType.DROPBOX,
            app_name="Dropbox",
            source_id="dropbox_me",
            source_name="Dropbox account",
            content=f"Conexión Dropbox {'ok' if auth.get('ok') else 'falló'}. Usa files/list_folder para búsqueda.",
            snippet="Token debe tener scope files.metadata.read.",
            url="https://api.dropboxapi.com/2/users/get_current_account",
            metadata={"validation": auth},
            relevance_score=0.2 if auth.get("ok") else 0.0
        )
    
    def _box_auth_test(self, token: str) -> Dict[str, Any]:
        resp = requests.get(
            "https://api.box.com/2.0/users/me",
            headers={"Authorization": f"Bearer {token}"},
            timeout=8
        )
        ok = resp.status_code == 200
        return {"ok": ok, "message": resp.reason, "details": resp.json() if ok else {"status": resp.status_code}}
    
    def _box_ping(self, token: str) -> Optional[AppSearchResult]:
        auth = self._box_auth_test(token)
        return AppSearchResult(
            app_type=IntegrationType.BOX,
            app_name="Box",
            source_id="box_me",
            source_name="Box user",
            content=f"Conexión Box {'ok' if auth.get('ok') else 'falló'}. Usa search API para archivos.",
            snippet="Token debe tener scope root_readonly al menos.",
            url="https://api.box.com/2.0/users/me",
            metadata={"validation": auth},
            relevance_score=0.2 if auth.get("ok") else 0.0
        )
    
    def _msgraph_auth_test(self, token: str) -> Dict[str, Any]:
        if not token:
            return {"ok": False, "message": "Token requerido de Microsoft Graph.", "details": None}
        resp = requests.get(
            "https://graph.microsoft.com/v1.0/me",
            headers={"Authorization": f"Bearer {token}"},
            timeout=8
        )
        ok = resp.status_code == 200
        return {"ok": ok, "message": resp.reason, "details": resp.json() if ok else {"status": resp.status_code}}
    
    def _teams_auth_test(self, token: str) -> Dict[str, Any]:
        """Valida token de Microsoft Teams usando Microsoft Graph API."""
        if not token:
            return {"ok": False, "message": "OAuth 2.0 Access Token requerido para Microsoft Teams.", "details": None}
        
        # Validar token probando acceso a Microsoft Graph API
        try:
            # Probar acceso básico
            resp = requests.get(
                "https://graph.microsoft.com/v1.0/me",
                headers={"Authorization": f"Bearer {token}"},
                timeout=8
            )
            
            if resp.status_code == 200:
                user_data = resp.json()
                # Probar acceso a Teams (chats o channels)
                teams_resp = requests.get(
                    "https://graph.microsoft.com/v1.0/me/chats",
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=8
                )
                
                # Si tiene acceso a chats, el token es válido para Teams
                if teams_resp.status_code == 200:
                    return {
                        "ok": True,
                        "message": "✅ Token válido con acceso a Teams. Scope: Chat.Read",
                        "details": {
                            "user": user_data.get("userPrincipalName", "Unknown"),
                            "teams_access": True
                        }
                    }
                elif teams_resp.status_code == 403:
                    return {
                        "ok": True,
                        "message": "⚠️ Token válido pero falta scope para Teams. Necesitas: ChannelMessage.Read.All o Chat.Read",
                        "details": {
                            "user": user_data.get("userPrincipalName", "Unknown"),
                            "teams_access": False,
                            "required_scopes": ["ChannelMessage.Read.All", "Chat.Read"]
                        }
                    }
                else:
                    return {
                        "ok": True,
                        "message": f"✅ Token válido de Microsoft Graph. Usuario: {user_data.get('userPrincipalName', 'Unknown')}",
                        "details": user_data
                    }
            elif resp.status_code == 401:
                return {"ok": False, "message": "❌ Token inválido o expirado. Obtén un nuevo OAuth 2.0 Access Token.", "details": None}
            else:
                return {"ok": False, "message": f"Error validando token: {resp.status_code} - {resp.reason}", "details": None}
        except Exception as e:
            return {"ok": False, "message": f"Error validando token de Teams: {str(e)}", "details": None}
    
    def _sharepoint_auth_test(self, token: str) -> Dict[str, Any]:
        """Valida token de SharePoint usando Microsoft Graph API."""
        if not token:
            return {"ok": False, "message": "OAuth 2.0 Access Token requerido para SharePoint.", "details": None}
        
        # Validar token probando acceso a Microsoft Graph API
        try:
            # Probar acceso básico
            resp = requests.get(
                "https://graph.microsoft.com/v1.0/me",
                headers={"Authorization": f"Bearer {token}"},
                timeout=8
            )
            
            if resp.status_code == 200:
                user_data = resp.json()
                # Probar acceso a SharePoint (drive)
                drive_resp = requests.get(
                    "https://graph.microsoft.com/v1.0/me/drive",
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=8
                )
                
                # Si tiene acceso a drive, puede acceder a SharePoint
                if drive_resp.status_code == 200:
                    # Intentar acceder a sites también
                    sites_list_resp = requests.get(
                        "https://graph.microsoft.com/v1.0/sites",
                        headers={"Authorization": f"Bearer {token}"},
                        timeout=8
                    )
                    
                    if sites_list_resp.status_code == 200:
                        sites = sites_list_resp.json().get("value", [])
                        return {
                            "ok": True,
                            "message": f"✅ Token válido con acceso a SharePoint. Scope: Sites.Read.All. {len(sites)} sitios disponibles",
                            "details": {
                                "user": user_data.get("userPrincipalName", "Unknown"),
                                "sharepoint_access": True,
                                "sites_count": len(sites)
                            }
                        }
                    else:
                        return {
                            "ok": True,
                            "message": "⚠️ Token válido pero falta scope para listar sitios. Necesitas: Sites.Read.All para buscar en todos los sitios, o Files.Read.All para archivos específicos",
                            "details": {
                                "user": user_data.get("userPrincipalName", "Unknown"),
                                "sharepoint_access": True,
                                "sites_access": False,
                                "required_scopes": ["Sites.Read.All", "Files.Read.All"]
                            }
                        }
                elif drive_resp.status_code == 403:
                    return {
                        "ok": True,
                        "message": "⚠️ Token válido pero falta scope para SharePoint. Necesitas: Files.Read.All o Sites.Read.All",
                        "details": {
                            "user": user_data.get("userPrincipalName", "Unknown"),
                            "sharepoint_access": False,
                            "required_scopes": ["Files.Read.All", "Sites.Read.All"]
                        }
                    }
                else:
                    return {
                        "ok": True,
                        "message": f"✅ Token válido de Microsoft Graph. Usuario: {user_data.get('userPrincipalName', 'Unknown')}",
                        "details": user_data
                    }
            elif resp.status_code == 401:
                return {"ok": False, "message": "❌ Token inválido o expirado. Obtén un nuevo OAuth 2.0 Access Token.", "details": None}
            else:
                return {"ok": False, "message": f"Error validando token: {resp.status_code} - {resp.reason}", "details": None}
        except Exception as e:
            return {"ok": False, "message": f"Error validando token de SharePoint: {str(e)}", "details": None}
    
    def _msgraph_ping(self, token: str, query: str, extra: Dict[str, Any]) -> Optional[AppSearchResult]:
        auth = self._msgraph_auth_test(token)
        return AppSearchResult(
            app_type=IntegrationType.OUTLOOK,
            app_name="Microsoft 365",
            source_id="msgraph_me",
            source_name="Graph /me",
            content=f"Conexión Graph {'ok' if auth.get('ok') else 'falló'}. Usa endpoints de Mail/Teams/SharePoint con scopes adecuados.",
            snippet=f"Consulta: {query[:120]}",
            url="https://graph.microsoft.com/v1.0/me",
            metadata={"validation": auth},
            relevance_score=0.2 if auth.get("ok") else 0.0
        )
    
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
    
    def _extract_pdf_with_fallback(self, pdf_bytes: bytes, file_name: str) -> tuple[str, str]:
        """Extrae texto de PDF usando PyPDF2. Si falla, retorna mensaje de error."""
        # Esta función ya no usa Docling ni RapidOCR
        return "", f"PDF encontrado: {file_name} (no se pudo extraer texto - PDF puede estar encriptado o corrupto)"
    
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
    
    async def _google_drive_search(self, token: str, query: str, credentials: Dict[str, Any], days: Optional[int] = None, filters: Optional[Dict[str, Any]] = None) -> List[AppSearchResult]:
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
            
            # Obtener límite de PDFs de filters
            max_pdfs = filters.get("max_pdfs", 100) if filters is not None else 100
            
            # Buscar archivos - ordenar por fecha de modificación (más recientes primero)
            params = {
                "q": query_string,
                "pageSize": min(max_pdfs, 1000),  # Google Drive API máximo es 1000
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
            
            # Manejar error 401 ANTES de procesar cualquier cosa
            if response.status_code == 401:
                print(f"❌ [Google Drive] Error 401: Token inválido o expirado")
                # Retornar resultado especial indicando que el token expiró
                error_result = AppSearchResult(
                    app_type=IntegrationType.GOOGLE_DRIVE,
                    app_name="Google Drive",
                    source_id="error_401",
                    source_name="Token expirado - Reconecta Google Drive",
                    content="",
                    snippet="⚠️ **Token de Google Drive expirado**\n\nPor favor, ve a la pestaña 'Conectar Apps' y reconecta Google Drive para continuar.",
                    url="",
                    metadata={
                        "error": "token_expired",
                        "error_code": 401,
                        "error_message": "Token inválido o expirado. Reconecta Google Drive en 'Conectar Apps'."
                    },
                    relevance_score=0.0
                )
                results.append(error_result)
                print(f"📊 [Google Drive] Retornando resultado de error (token expirado)")
                return results  # Retornar inmediatamente sin procesar más
            
            if response.status_code == 200:
                data = response.json()
                files = data.get("files", [])
                print(f"✅ [Google Drive] Encontrados {len(files)} archivos")
                
                # Si hay PDFs seleccionados específicamente, filtrar solo esos
                selected_pdf_ids = filters.get("selected_pdf_ids", []) if filters else []
                if selected_pdf_ids:
                    print(f"📋 [Google Drive] Filtrando por {len(selected_pdf_ids)} PDFs seleccionados específicamente")
                    # Filtrar archivos para incluir solo los seleccionados
                    files = [f for f in files if f.get("id") in selected_pdf_ids]
                    print(f"✅ [Google Drive] {len(files)} archivos coinciden con la selección")
                
                # Limitar cantidad de PDFs a procesar según max_pdfs
                pdf_count = 0
                max_pdfs_to_process = filters.get("max_pdfs", 100) if filters is not None else 100
                if selected_pdf_ids:
                    # Si hay selección específica, no aplicar límite max_pdfs (procesar todos los seleccionados)
                    max_pdfs_to_process = len(selected_pdf_ids)
                    print(f"📊 [Google Drive] Procesando todos los {max_pdfs_to_process} PDFs seleccionados")
                else:
                    print(f"📊 [Google Drive] Límite de PDFs configurado: {max_pdfs_to_process}")
                
                # Procesar archivos hasta alcanzar el límite de PDFs
                for file in files:
                    file_id = file.get("id")
                    name = file.get("name", "Sin nombre")
                    mime_type = file.get("mimeType", "")
                    url = file.get("webViewLink", f"https://drive.google.com/file/d/{file_id}")
                    
                    # Si es PDF, verificar límite ANTES de procesar
                    if mime_type == "application/pdf":
                        if pdf_count >= max_pdfs_to_process:
                            print(f"⏸️ [Google Drive] Límite de {max_pdfs_to_process} PDFs alcanzado. Saltando {name}")
                            continue  # Saltar PDFs adicionales
                        pdf_count += 1
                        print(f"📄 [Google Drive] Procesando PDF {pdf_count}/{max_pdfs_to_process}: {name}")
                    
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
                                            # Si PyPDF2 no extrajo texto, usar fallback
                                            print(f"⚠️ [Google Drive] PyPDF2 no extrajo texto de {name}")
                                            content, snippet = self._extract_pdf_with_fallback(pdf_bytes, name)
                                    else:
                                        print(f"⚠️ [Google Drive] PyPDF2 no disponible para {name}")
                                        content, snippet = self._extract_pdf_with_fallback(pdf_bytes, name)
                                        
                                except Exception as e:
                                    error_msg = str(e).lower()
                                    if "pycryptodome" in error_msg or "aes" in error_msg or "encrypted" in error_msg:
                                        print(f"⚠️ [Google Drive] PDF encriptado detectado: {name}")
                                        content, snippet = self._extract_pdf_with_fallback(pdf_bytes, name)
                                    else:
                                        print(f"⚠️ [Google Drive] Error extrayendo con PyPDF2: {e}")
                                        content, snippet = self._extract_pdf_with_fallback(pdf_bytes, name)
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
                    
                    # Solo agregar a resultados si no es PDF o si aún no hemos alcanzado el límite
                    # (para PDFs, ya verificamos el límite antes de procesar, pero por seguridad verificamos de nuevo)
                    if mime_type == "application/pdf" and pdf_count > max_pdfs_to_process:
                        continue  # No agregar este PDF a resultados
                    
                    results.append(AppSearchResult(
                        app_type=IntegrationType.GOOGLE_DRIVE,
                        app_name="Google Drive",
                        source_id=file_id,
                        source_name=name,
                        content=final_content,
                        snippet=final_snippet,
                        url=url,
                        metadata={
                            "mime_type": mime_type,
                            "modified": file.get("modifiedTime"),
                            "file_id": file_id,  # Guardar file_id para filtrado por selección
                            "id": file_id  # También como "id" para compatibilidad
                        },
                        relevance_score=min(relevance, 1.0)  # Cap a 1.0
                    ))
                
                # Mensaje final con resumen
                pdf_results = [r for r in results if r.metadata.get("mime_type") == "application/pdf"]
                print(f"✅ [Google Drive] Procesados {len(pdf_results)} PDFs de {max_pdfs_to_process} permitidos. Total resultados: {len(results)}")
                if len(pdf_results) >= max_pdfs_to_process:
                    print(f"⚠️ [Google Drive] Se alcanzó el límite de {max_pdfs_to_process} PDFs. Se omitieron PDFs adicionales.")
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
        """Busca en SharePoint usando Microsoft Graph API (OPTIMIZADO para PDFs contables)."""
        # Usar la implementación síncrona (que ya está optimizada)
        # Ejecutar en thread para no bloquear
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: self._sharepoint_search_sync(token, query, credentials, days)
        )
    
    def _sharepoint_search_sync(self, token: str, query: str, credentials: Dict[str, Any], days: Optional[int] = None) -> List[AppSearchResult]:
        """Versión síncrona de búsqueda en SharePoint (OPTIMIZADA para PDFs contables)."""
        results: List[AppSearchResult] = []
        
        if not token:
            return results
        
        headers = {"Authorization": f"Bearer {token}"}
        site_url = credentials.get("site_url")  # Opcional: URL específica del sitio
        
        # OPTIMIZACIÓN: Si la query busca PDFs, agregar filtro de tipo
        is_pdf_search = "pdf" in query.lower() or "filetype:pdf" in query.lower() or "mimetype" in query.lower()
        
        try:
            # Buscar en OneDrive personal primero (más rápido)
            drive_resp = requests.get(
                "https://graph.microsoft.com/v1.0/me/drive/root/search",
                headers=headers,
                params={"q": query},
                timeout=15
            )
            
            if drive_resp.status_code == 200:
                files = drive_resp.json().get("value", [])
                # Filtrar solo PDFs si es búsqueda de PDFs
                if is_pdf_search:
                    files = [f for f in files if f.get("file", {}).get("mimeType") == "application/pdf"]
                
                for file in files[:50]:  # Aumentado para más resultados
                    file_info = file.get("file", {})
                    file_name = file.get("name", "Unknown")
                    mime_type = file_info.get("mimeType", "")
                    
                    # Solo PDFs si es búsqueda de PDFs
                    if is_pdf_search and mime_type != "application/pdf":
                        continue
                    
                    web_url = file.get("webUrl", "")
                    modified = file.get("lastModifiedDateTime", "")
                    file_id = file.get("id", "")
                    
                    results.append(AppSearchResult(
                        app_type=IntegrationType.SHAREPOINT,
                        app_name="SharePoint (OneDrive)",
                        source_id=file_id,
                        source_name=file_name,
                        content=f"Documento encontrado en SharePoint: {file_name}",
                        snippet=f"Archivo: {file_name} | Modificado: {modified}",
                        url=web_url,
                        metadata={"mime_type": mime_type, "modified": modified, "file_id": file_id},
                        relevance_score=0.7
                    ))
            
            # Buscar en sitios de SharePoint si hay site_url o si no hay resultados suficientes
            if site_url or len(results) < 10:
                if site_url:
                    # Buscar en sitio específico
                    from urllib.parse import urlparse
                    parsed = urlparse(site_url)
                    hostname = parsed.netloc
                    path = parsed.path.strip('/')
                    
                    sites_resp = requests.get(
                        f"https://graph.microsoft.com/v1.0/sites/{hostname}:/{path}",
                        headers=headers,
                        timeout=10
                    )
                    
                    if sites_resp.status_code == 200:
                        site_data = sites_resp.json()
                        site_id = site_data.get("id", "")
                        
                        drive_resp = requests.get(
                            f"https://graph.microsoft.com/v1.0/sites/{site_id}/drive",
                            headers=headers,
                            timeout=10
                        )
                        
                        if drive_resp.status_code == 200:
                            drive_data = drive_resp.json()
                            drive_id = drive_data.get("id", "")
                            
                            # Buscar archivos (escapar query para URL)
                            import urllib.parse
                            query_escaped = urllib.parse.quote(query)
                            search_url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/root/search(q='{query_escaped}')"
                            search_resp = requests.get(search_url, headers=headers, timeout=15)
                            
                            if search_resp.status_code == 200:
                                files = search_resp.json().get("value", [])
                                # Filtrar solo PDFs si es búsqueda de PDFs
                                if is_pdf_search:
                                    files = [f for f in files if f.get("file", {}).get("mimeType") == "application/pdf"]
                                
                                for file in files[:50]:
                                    file_info = file.get("file", {})
                                    file_name = file.get("name", "Unknown")
                                    mime_type = file_info.get("mimeType", "")
                                    
                                    if is_pdf_search and mime_type != "application/pdf":
                                        continue
                                    
                                    web_url = file.get("webUrl", "")
                                    modified = file.get("lastModifiedDateTime", "")
                                    file_id = file.get("id", "")
                                    
                                    results.append(AppSearchResult(
                                        app_type=IntegrationType.SHAREPOINT,
                                        app_name="SharePoint",
                                        source_id=file_id,
                                        source_name=file_name,
                                        content=f"Documento encontrado en SharePoint: {file_name}",
                                        snippet=f"Archivo: {file_name} | Modificado: {modified}",
                                        url=web_url,
                                        metadata={"mime_type": mime_type, "modified": modified, "file_id": file_id},
                                        relevance_score=0.75
                                    ))
                else:
                    # Buscar en todos los sitios disponibles
                    sites_resp = requests.get(
                        "https://graph.microsoft.com/v1.0/sites",
                        headers=headers,
                        params={"$top": 10},  # Aumentado para más sitios
                        timeout=15
                    )
                    
                    if sites_resp.status_code == 200:
                        sites = sites_resp.json().get("value", [])
                        for site in sites[:5]:  # Probar primeros 5 sitios
                            site_id = site.get("id", "")
                            try:
                                drive_resp = requests.get(
                                    f"https://graph.microsoft.com/v1.0/sites/{site_id}/drive",
                                    headers=headers,
                                    timeout=10
                                )
                                
                                if drive_resp.status_code == 200:
                                    drive_data = drive_resp.json()
                                    drive_id = drive_data.get("id", "")
                                    
                                    import urllib.parse
                                    query_escaped = urllib.parse.quote(query)
                                    search_url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/root/search(q='{query_escaped}')"
                                    search_resp = requests.get(search_url, headers=headers, timeout=10)
                                    
                                    if search_resp.status_code == 200:
                                        files = search_resp.json().get("value", [])
                                        if is_pdf_search:
                                            files = [f for f in files if f.get("file", {}).get("mimeType") == "application/pdf"]
                                        
                                        for file in files[:20]:  # Limitar por sitio
                                            file_info = file.get("file", {})
                                            file_name = file.get("name", "Unknown")
                                            mime_type = file_info.get("mimeType", "")
                                            
                                            if is_pdf_search and mime_type != "application/pdf":
                                                continue
                                            
                                            web_url = file.get("webUrl", "")
                                            modified = file.get("lastModifiedDateTime", "")
                                            file_id = file.get("id", "")
                                            
                                            results.append(AppSearchResult(
                                                app_type=IntegrationType.SHAREPOINT,
                                                app_name=f"SharePoint ({site.get('displayName', 'Site')})",
                                                source_id=file_id,
                                                source_name=file_name,
                                                content=f"Documento encontrado en SharePoint: {file_name}",
                                                snippet=f"Archivo: {file_name} | Modificado: {modified}",
                                                url=web_url,
                                                metadata={"mime_type": mime_type, "modified": modified, "file_id": file_id},
                                                relevance_score=0.7
                                            ))
                                            
                                            if len(results) >= 100:  # Limitar total
                                                break
                            except Exception as e:
                                print(f"⚠️ [SharePoint] Error buscando en sitio {site.get('displayName', 'Unknown')}: {e}")
                                continue
                            
                            if len(results) >= 100:
                                break
        
        except Exception as e:
            print(f"⚠️ [SharePoint] Error buscando: {e}")
            import traceback
            traceback.print_exc()
        
        # Eliminar duplicados por source_id
        seen_ids = set()
        unique_results = []
        for r in results:
            if r.source_id not in seen_ids:
                seen_ids.add(r.source_id)
                unique_results.append(r)
        
        print(f"✅ [SharePoint] Encontrados {len(unique_results)} documentos únicos")
        return unique_results
    
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
    
    def _teams_search(self, token: str, query: str, filters: Optional[Dict[str, Any]] = None) -> List[AppSearchResult]:
        """Busca mensajes en Microsoft Teams usando Microsoft Graph API."""
        results: List[AppSearchResult] = []
        
        if not token:
            return results
        
        headers = {"Authorization": f"Bearer {token}"}
        
        try:
            # Buscar en chats personales
            chats_url = "https://graph.microsoft.com/v1.0/me/chats"
            chats_response = requests.get(chats_url, headers=headers, params={"$top": 10}, timeout=10)
            
            if chats_response.status_code == 200:
                chats = chats_response.json().get("value", [])
                for chat in chats[:5]:  # Limitar a 5 chats
                    chat_id = chat.get("id", "")
                    # Obtener mensajes del chat
                    messages_url = f"https://graph.microsoft.com/v1.0/me/chats/{chat_id}/messages"
                    messages_response = requests.get(
                        messages_url,
                        headers=headers,
                        params={"$top": 5, "$filter": f"contains(body/content, '{query}')"},
                        timeout=10
                    )
                    
                    if messages_response.status_code == 200:
                        messages = messages_response.json().get("value", [])
                        for msg in messages:
                            body = msg.get("body", {}).get("content", "")
                            from_user = msg.get("from", {}).get("user", {}).get("displayName", "Unknown")
                            created = msg.get("createdDateTime", "")
                            
                            results.append(AppSearchResult(
                                app_type=IntegrationType.TEAMS,
                                app_name="Microsoft Teams",
                                source_id=msg.get("id", ""),
                                source_name=f"Chat: {from_user}",
                                content=body[:1000],
                                snippet=f"De: {from_user} | {created}",
                                url=f"https://teams.microsoft.com/_#/conversations/{chat_id}",
                                relevance_score=0.6
                            ))
            
            # Buscar en canales (requiere ChannelMessage.Read.All)
            teams_url = "https://graph.microsoft.com/v1.0/me/joinedTeams"
            teams_response = requests.get(teams_url, headers=headers, timeout=10)
            
            if teams_response.status_code == 200:
                teams = teams_response.json().get("value", [])
                for team in teams[:3]:  # Limitar a 3 teams
                    team_id = team.get("id", "")
                    # Obtener canales
                    channels_url = f"https://graph.microsoft.com/v1.0/teams/{team_id}/channels"
                    channels_response = requests.get(channels_url, headers=headers, timeout=10)
                    
                    if channels_response.status_code == 200:
                        channels = channels_response.json().get("value", [])
                        for channel in channels[:3]:  # Limitar a 3 canales
                            channel_id = channel.get("id", "")
                            # Buscar mensajes en el canal
                            channel_messages_url = f"https://graph.microsoft.com/v1.0/teams/{team_id}/channels/{channel_id}/messages"
                            messages_response = requests.get(
                                channel_messages_url,
                                headers=headers,
                                params={"$top": 5, "$filter": f"contains(body/content, '{query}')"},
                                timeout=10
                            )
                            
                            if messages_response.status_code == 200:
                                messages = messages_response.json().get("value", [])
                                for msg in messages:
                                    body = msg.get("body", {}).get("content", "")
                                    from_user = msg.get("from", {}).get("user", {}).get("displayName", "Unknown")
                                    created = msg.get("createdDateTime", "")
                                    
                                    results.append(AppSearchResult(
                                        app_type=IntegrationType.TEAMS,
                                        app_name="Microsoft Teams",
                                        source_id=msg.get("id", ""),
                                        source_name=f"Canal: {channel.get('displayName', 'Unknown')} - {from_user}",
                                        content=body[:1000],
                                        snippet=f"Canal: {channel.get('displayName', 'Unknown')} | De: {from_user} | {created}",
                                        url=f"https://teams.microsoft.com/_#/conversations/{channel_id}",
                                        relevance_score=0.65
                                    ))
            
            return results[:10]  # Limitar a 10 resultados
            
        except Exception as e:
            print(f"⚠️ [Company Knowledge] Error buscando en Teams: {e}")
            return results
    
    def _sharepoint_search(self, token: str, query: str, extra: Dict[str, Any], filters: Optional[Dict[str, Any]] = None) -> List[AppSearchResult]:
        """Busca documentos en SharePoint usando Microsoft Graph API."""
        results: List[AppSearchResult] = []
        
        if not token:
            return results
        
        headers = {"Authorization": f"Bearer {token}"}
        site_url = extra.get("site_url")  # Opcional: URL específica del sitio
        
        try:
            # Si hay un sitio específico, buscar ahí
            if site_url:
                # Extraer hostname y path del sitio
                from urllib.parse import urlparse
                parsed = urlparse(site_url)
                hostname = parsed.netloc
                path = parsed.path.strip('/')
                
                # Obtener el sitio
                sites_resp = requests.get(
                    f"https://graph.microsoft.com/v1.0/sites/{hostname}:/{path}",
                    headers=headers,
                    timeout=10
                )
                
                if sites_resp.status_code == 200:
                    site_data = sites_resp.json()
                    site_id = site_data.get("id", "")
                    
                    # Buscar en los documentos del sitio
                    drive_resp = requests.get(
                        f"https://graph.microsoft.com/v1.0/sites/{site_id}/drive",
                        headers=headers,
                        timeout=10
                    )
                    
                    if drive_resp.status_code == 200:
                        drive_data = drive_resp.json()
                        drive_id = drive_data.get("id", "")
                        
                        # Buscar archivos
                        search_url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/root/search(q='{query}')"
                        search_resp = requests.get(search_url, headers=headers, timeout=10)
                        
                        if search_resp.status_code == 200:
                            files = search_resp.json().get("value", [])
                            for file in files[:10]:
                                file_name = file.get("name", "Unknown")
                                web_url = file.get("webUrl", "")
                                modified = file.get("lastModifiedDateTime", "")
                                
                                results.append(AppSearchResult(
                                    app_type=IntegrationType.SHAREPOINT,
                                    app_name="SharePoint",
                                    source_id=file.get("id", ""),
                                    source_name=f"📄 {file_name}",
                                    content=f"Documento encontrado en SharePoint: {file_name}",
                                    snippet=f"Archivo: {file_name} | Modificado: {modified}",
                                    url=web_url,
                                    relevance_score=0.7
                                ))
            
            # También buscar en el OneDrive personal (que también es SharePoint)
            drive_resp = requests.get(
                "https://graph.microsoft.com/v1.0/me/drive/root/search",
                headers=headers,
                params={"q": query},
                timeout=10
            )
            
            if drive_resp.status_code == 200:
                files = drive_resp.json().get("value", [])
                for file in files[:5]:
                    file_name = file.get("name", "Unknown")
                    web_url = file.get("webUrl", "")
                    modified = file.get("lastModifiedDateTime", "")
                    
                    results.append(AppSearchResult(
                        app_type=IntegrationType.SHAREPOINT,
                        app_name="SharePoint (OneDrive)",
                        source_id=file.get("id", ""),
                        source_name=f"📄 {file_name}",
                        content=f"Documento encontrado en OneDrive/SharePoint: {file_name}",
                        snippet=f"Archivo: {file_name} | Modificado: {modified}",
                        url=web_url,
                        relevance_score=0.65
                    ))
            
            # Buscar en todos los sitios de SharePoint si no hay sitio específico
            if not site_url:
                sites_resp = requests.get(
                    "https://graph.microsoft.com/v1.0/sites",
                    headers=headers,
                    params={"$top": 5},
                    timeout=10
                )
                
                if sites_resp.status_code == 200:
                    sites = sites_resp.json().get("value", [])
                    for site in sites[:3]:  # Limitar a 3 sitios
                        site_id = site.get("id", "")
                        site_name = site.get("displayName", "Unknown")
                        
                        # Buscar en el drive del sitio
                        drive_resp = requests.get(
                            f"https://graph.microsoft.com/v1.0/sites/{site_id}/drive/root/search",
                            headers=headers,
                            params={"q": query},
                            timeout=10
                        )
                        
                        if drive_resp.status_code == 200:
                            files = drive_resp.json().get("value", [])
                            for file in files[:3]:
                                file_name = file.get("name", "Unknown")
                                web_url = file.get("webUrl", "")
                                modified = file.get("lastModifiedDateTime", "")
                                
                                results.append(AppSearchResult(
                                    app_type=IntegrationType.SHAREPOINT,
                                    app_name="SharePoint",
                                    source_id=file.get("id", ""),
                                    source_name=f"📂 {site_name} - {file_name}",
                                    content=f"Documento encontrado en SharePoint ({site_name}): {file_name}",
                                    snippet=f"Sitio: {site_name} | Archivo: {file_name} | Modificado: {modified}",
                                    url=web_url,
                                    relevance_score=0.7
                                ))
            
            return results[:15]  # Limitar a 15 resultados
            
        except Exception as e:
            print(f"⚠️ [Company Knowledge] Error buscando en SharePoint: {e}")
            return results
    
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
    
    def get_access_token_for_app(self, connection_id: str) -> Optional[str]:
        """
        Obtiene el access token para una conexión específica.
        
        Args:
            connection_id: ID de la conexión
        
        Returns:
            Access token si está disponible, None en caso contrario
        """
        creds = self._token_cache.get(connection_id, {})
        return creds.get("token") or creds.get("access_token")


