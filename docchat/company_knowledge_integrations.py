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
                        "app_type": conn.app_type.value,
                        "app_name": conn.app_name,
                        "status": conn.status,
                        "connected_at": conn.connected_at,
                        "last_sync": conn.last_sync,
                        "permissions": conn.permissions,
                        "metadata": conn.metadata,
                        "enabled": conn.enabled
                    }
                    for conn in self.connections.values()
                ]
            }
            with open(self.connections_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"⚠️ [Company Knowledge] Error guardando conexiones: {e}")
    
    def connect_app(
        self,
        app_type: IntegrationType,
        app_name: str,
        credentials: Dict[str, Any],
        permissions: Optional[Dict[str, Any]] = None
    ) -> AppConnection:
        """
        Conecta una app externa.
        
        Args:
            app_type: Tipo de app (SLACK, GOOGLE_DRIVE, etc.)
            app_name: Nombre descriptivo de la conexión
            credentials: Credenciales para autenticación
            permissions: Permisos específicos de la conexión
        
        Returns:
            AppConnection: Conexión creada
        """
        connection_id = f"{app_type.value}_{int(time.time())}"
        
        # Validar credenciales/token con un ping ligero cuando sea posible
        validation = self._validate_credentials(app_type, credentials)
        status = "connected" if validation.get("ok") else "error"
        
        connection = AppConnection(
            connection_id=connection_id,
            app_type=app_type,
            app_name=app_name,
            status=status,
            connected_at=time.strftime("%Y-%m-%d %H:%M:%S"),
            last_sync=time.strftime("%Y-%m-%d %H:%M:%S"),
            permissions=permissions or {},
            metadata={
                "credentials_stored": False,  # Tokens no se persisten en disco
                "validation": validation
            }
        )
        
        # Guardar token y extras en memoria (no persistente)
        safe_credentials = {k: v for k, v in credentials.items()}
        self._token_cache[connection_id] = safe_credentials
        
        self.connections[connection_id] = connection
        self._save_connections()
        
        if validation.get("ok"):
            print(f"✅ [Company Knowledge] App conectada: {app_name} ({app_type.value})")
        else:
            print(f"⚠️ [Company Knowledge] Conexión con advertencias: {app_name} ({app_type.value}) -> {validation.get('message')}")
        return connection
    
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
        Busca en una app específica. Se apoya en el token almacenado en memoria.
        En producción, esto debería implementar las APIs reales de cada app.
        """
        results = []
        creds = self._token_cache.get(app.connection_id, {})
        token = creds.get("token") or creds.get("api_token")
        extra = creds.get("extra", {})
        
        # Si no hay token, devolver aviso
        if not token and app.app_type not in [IntegrationType.SHAREPOINT, IntegrationType.TEAMS]:
            results.append(AppSearchResult(
                app_type=app.app_type,
                app_name=app.app_name,
                source_id=f"{app.connection_id}_missing_token",
                source_name=f"{app.app_name} - Falta token",
                content="No hay token disponible en memoria. Re-conecta la app con credenciales.",
                snippet="Conecta la app nuevamente incluyendo el token/API key.",
                relevance_score=0.0
            ))
            return results
        
        # Simulación/búsqueda ligera según tipo de app
        if app.app_type == IntegrationType.SLACK:
            slack_results = self._slack_search(token, query, top_n=5, filters=filters)
            results.extend(slack_results)
        
        elif app.app_type == IntegrationType.GOOGLE_DRIVE:
            drive_results = self._google_drive_search(token, query, extra, filters=filters)
            results.extend(drive_results)
        
        elif app.app_type == IntegrationType.SHAREPOINT:
            # Buscar en SharePoint usando Microsoft Graph API
            sharepoint_results = self._sharepoint_search(token, query, extra, filters=filters)
            if sharepoint_results:
                results.extend(sharepoint_results)
            else:
                results.append(AppSearchResult(
                    app_type=app.app_type,
                    app_name=app.app_name,
                    source_id=f"sharepoint_{app.connection_id}",
                    source_name="SharePoint - Sin resultados",
                    content=f"No se encontraron documentos en SharePoint para: {query}",
                    snippet="Verifica que el token tenga scope Files.Read.All o Sites.Read.All",
                    relevance_score=0.0
                ))
        
        elif app.app_type == IntegrationType.GITHUB:
            gh_result = self._github_search(token, query)
            if gh_result:
                results.append(gh_result)
        
        elif app.app_type == IntegrationType.GMAIL:
            results.append(AppSearchResult(
                app_type=app.app_type,
                app_name=app.app_name,
                source_id=f"gmail_{app.connection_id}",
                source_name="Gmail (pendiente)",
                content="Se requiere token OAuth de Gmail API (scope gmail.readonly).",
                snippet="Proporciona access token y refresco para habilitar búsqueda real.",
                relevance_score=0.05
            ))
        
        elif app.app_type == IntegrationType.OUTLOOK:
            ms_result = self._msgraph_ping(token, query, extra)
            if ms_result:
                results.append(ms_result)
        
        elif app.app_type == IntegrationType.HUBSPOT:
            hs_results = self._hubspot_search(token, query, filters=filters)
            results.extend(hs_results)
        
        elif app.app_type == IntegrationType.SALESFORCE:
            sf_result = self._salesforce_ping(token, extra)
            if sf_result:
                results.append(sf_result)
        
        elif app.app_type == IntegrationType.LINEAR:
            linear_result = self._linear_ping(token, query)
            if linear_result:
                results.append(linear_result)
        
        elif app.app_type == IntegrationType.ASANA:
            asana_result = self._asana_ping(token, query)
            if asana_result:
                results.append(asana_result)
        
        elif app.app_type == IntegrationType.GITLAB:
            gl_result = self._gitlab_ping(token, query, extra)
            if gl_result:
                results.append(gl_result)
        
        elif app.app_type == IntegrationType.CLICKUP:
            cu_result = self._clickup_ping(token, query)
            if cu_result:
                results.append(cu_result)
        
        elif app.app_type == IntegrationType.INTERCOM:
            results.append(AppSearchResult(
                app_type=app.app_type,
                app_name=app.app_name,
                source_id=f"intercom_{app.connection_id}",
                source_name="Intercom (pendiente)",
                content="Intercom requiere access token con scope read:conversations. Implementar búsqueda de conversaciones.",
                snippet="Configura el token de Intercom (personal access token).",
                relevance_score=0.05
            ))
        
        elif app.app_type == IntegrationType.JIRA:
            jira_results = self._jira_search(token, extra, query, filters=filters)
            results.extend(jira_results)
        
        elif app.app_type == IntegrationType.CONFLUENCE:
            conf_results = self._confluence_search(token, extra, query, filters=filters)
            results.extend(conf_results)
        
        elif app.app_type == IntegrationType.DROPBOX:
            dbx = self._dropbox_ping(token)
            if dbx:
                results.append(dbx)
        
        elif app.app_type == IntegrationType.BOX:
            box_res = self._box_ping(token)
            if box_res:
                results.append(box_res)
        
        elif app.app_type == IntegrationType.TEAMS:
            # Buscar en Microsoft Teams usando Microsoft Graph API
            teams_results = self._teams_search(token, query, filters=filters)
            if teams_results:
                results.extend(teams_results)
            else:
                results.append(AppSearchResult(
                    app_type=app.app_type,
                    app_name=app.app_name,
                    source_id=f"teams_{app.connection_id}",
                    source_name="Teams - Sin resultados",
                    content=f"No se encontraron mensajes en Teams para: {query}",
                    snippet="Verifica que el token tenga scope ChannelMessage.Read.All o Chat.Read",
                    relevance_score=0.0
                ))
        
        # Actualizar última sincronización
        app.last_sync = time.strftime("%Y-%m-%d %H:%M:%S")
        self._save_connections()
        
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
        return {
            "success": True,
            "task_type": "analyze",
            "analysis": f"Análisis de {len(app_results)} fuentes relacionadas con: {task_description}",
            "insights": [
                f"Insight 1: Patrón encontrado en {result.app_name}",
                f"Insight 2: Tendencia identificada en {result.source_name}"
                for result in app_results[:5]
            ],
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


