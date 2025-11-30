"""
Gestor de Integraciones

Maneja todas las integraciones con apps externas.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Any
from enum import Enum

from langchain_core.documents import Document


class IntegrationType(str, Enum):
    """Tipos de integraciones disponibles."""
    GOOGLE_DRIVE = "google_drive"
    GMAIL = "gmail"
    MICROSOFT_TEAMS = "microsoft_teams"
    OUTLOOK = "outlook"
    ONEDRIVE = "onedrive"
    SLACK = "slack"
    SALESFORCE = "salesforce"
    JIRA = "jira"
    GITHUB = "github"
    NOTION = "notion"
    CONFLUENCE = "confluence"
    ZENDESK = "zendesk"
    SERVICENOW = "servicenow"
    # Nuevas integraciones
    HUBSPOT = "hubspot"
    ASANA = "asana"
    TRELLO = "trello"
    QUICKBOOKS = "quickbooks"
    WORKDAY = "workday"
    POWERBI = "powerbi"
    SHAREPOINT = "sharepoint"
    MONDAY = "monday"
    PIPEDRIVE = "pipedrive"
    ZOHO_CRM = "zoho_crm"
    BAMBOOHR = "bamboohr"
    FRESHBOOKS = "freshbooks"
    WAVE = "wave"
    ZOOM = "zoom"


@dataclass
class IntegrationConnection:
    """Conexión de una integración."""
    integration_id: str
    integration_type: IntegrationType
    user_id: str
    access_token: str
    refresh_token: Optional[str] = None
    expires_at: Optional[float] = None
    connected_at: str = field(default_factory=lambda: time.strftime("%Y-%m-%d %H:%M:%S"))
    status: str = "active"
    last_sync: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class IntegrationManager:
    """
    Gestor de integraciones con apps externas.
    
    Maneja:
    - Conexiones OAuth
    - Sincronización de datos
    - Búsqueda unificada
    """
    
    def __init__(self, config):
        self.config = config
        
        # Directorio para datos de integraciones
        self.data_dir = Path(config.memory_dir) / "integrations"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Archivo de conexiones
        self.connections_file = self.data_dir / "connections.json"
        
        # Cargar conexiones existentes
        self.connections: Dict[str, IntegrationConnection] = self._load_connections()
        
        # Importar handlers de cada integración
        self._load_integration_handlers()
    
    def _load_connections(self) -> Dict[str, IntegrationConnection]:
        """Carga conexiones desde archivo."""
        try:
            if self.connections_file.exists():
                with open(self.connections_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    connections = {}
                    for conn_id, conn_data in data.items():
                        # Convertir integration_type de string a enum
                        integration_type_str = conn_data.get("integration_type", "")
                        try:
                            if isinstance(integration_type_str, str):
                                integration_type_enum = IntegrationType(integration_type_str)
                            else:
                                integration_type_enum = integration_type_str
                        except (ValueError, KeyError):
                            # Si no se puede convertir, intentar usar el valor directamente
                            print(f"⚠️ Tipo de integración desconocido: {integration_type_str}, intentando usar como enum")
                            integration_type_enum = IntegrationType.GMAIL  # Default fallback
                        
                        connections[conn_id] = IntegrationConnection(
                            integration_id=conn_data.get("integration_id", conn_id),
                            integration_type=integration_type_enum,
                            user_id=conn_data.get("user_id", "user"),
                            access_token=conn_data.get("access_token", ""),
                            refresh_token=conn_data.get("refresh_token"),
                            expires_at=conn_data.get("expires_at"),
                            connected_at=conn_data.get("connected_at", ""),
                            status=conn_data.get("status", "active"),
                            last_sync=conn_data.get("last_sync"),
                            metadata=conn_data.get("metadata", {})
                        )
                    return connections
            return {}
        except Exception as e:
            print(f"Error cargando conexiones: {e}")
            import traceback
            traceback.print_exc()
            return {}
    
    def _save_connections(self):
        """Guarda conexiones."""
        try:
            data = {}
            for conn_id, conn in self.connections.items():
                # Asegurar que integration_type sea string
                integration_type_str = conn.integration_type.value if hasattr(conn.integration_type, 'value') else str(conn.integration_type)
                
                data[conn_id] = {
                    "integration_id": conn.integration_id,
                    "integration_type": integration_type_str,
                    "user_id": conn.user_id,
                    "access_token": conn.access_token,
                    "refresh_token": conn.refresh_token,
                    "expires_at": conn.expires_at,
                    "connected_at": conn.connected_at,
                    "status": conn.status,
                    "last_sync": conn.last_sync,
                    "metadata": conn.metadata
                }
            with open(self.connections_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error guardando conexiones: {e}")
            import traceback
            traceback.print_exc()
    
    def _load_integration_handlers(self):
        """Carga handlers de cada integración."""
        self.handlers = {}
        
        # Importar handlers dinámicamente
        try:
            from .handlers.google_handler import GoogleHandler
            self.handlers[IntegrationType.GOOGLE_DRIVE] = GoogleHandler(self.config)
            self.handlers[IntegrationType.GMAIL] = GoogleHandler(self.config)
        except ImportError:
            pass
        
        try:
            from .handlers.microsoft_handler import MicrosoftHandler
            self.handlers[IntegrationType.MICROSOFT_TEAMS] = MicrosoftHandler(self.config)
            self.handlers[IntegrationType.OUTLOOK] = MicrosoftHandler(self.config)
            self.handlers[IntegrationType.ONEDRIVE] = MicrosoftHandler(self.config)
        except ImportError:
            pass
        
        try:
            from .handlers.slack_handler import SlackHandler
            self.handlers[IntegrationType.SLACK] = SlackHandler(self.config)
        except ImportError:
            pass
        
        try:
            from .handlers.github_handler import GitHubHandler
            self.handlers[IntegrationType.GITHUB] = GitHubHandler(self.config)
        except ImportError:
            pass
        
        try:
            from .handlers.jira_handler import JiraHandler
            self.handlers[IntegrationType.JIRA] = JiraHandler(self.config)
        except ImportError:
            pass
        
        try:
            from .handlers.salesforce_handler import SalesforceHandler
            self.handlers[IntegrationType.SALESFORCE] = SalesforceHandler(self.config)
        except ImportError:
            pass
        
        try:
            from .handlers.zendesk_handler import ZendeskHandler
            self.handlers[IntegrationType.ZENDESK] = ZendeskHandler(self.config)
        except ImportError:
            pass
        
        try:
            from .handlers.servicenow_handler import ServiceNowHandler
            self.handlers[IntegrationType.SERVICENOW] = ServiceNowHandler(self.config)
        except ImportError:
            pass
        
        try:
            from .handlers.notion_handler import NotionHandler
            self.handlers[IntegrationType.NOTION] = NotionHandler(self.config)
        except ImportError:
            pass
        
        try:
            from .handlers.confluence_handler import ConfluenceHandler
            self.handlers[IntegrationType.CONFLUENCE] = ConfluenceHandler(self.config)
        except ImportError:
            pass
        
        try:
            from .handlers.hubspot_handler import HubSpotHandler
            self.handlers[IntegrationType.HUBSPOT] = HubSpotHandler(self.config)
        except ImportError:
            pass
        
        try:
            from .handlers.asana_handler import AsanaHandler
            self.handlers[IntegrationType.ASANA] = AsanaHandler(self.config)
        except ImportError:
            pass
        
        try:
            from .handlers.trello_handler import TrelloHandler
            self.handlers[IntegrationType.TRELLO] = TrelloHandler(self.config)
        except ImportError:
            pass
        
        try:
            from .handlers.quickbooks_handler import QuickBooksHandler
            self.handlers[IntegrationType.QUICKBOOKS] = QuickBooksHandler(self.config)
        except ImportError:
            pass
        
        try:
            from .handlers.workday_handler import WorkdayHandler
            self.handlers[IntegrationType.WORKDAY] = WorkdayHandler(self.config)
        except ImportError:
            pass
        
        try:
            from .handlers.powerbi_handler import PowerBIHandler
            self.handlers[IntegrationType.POWERBI] = PowerBIHandler(self.config)
        except ImportError:
            pass
        
        try:
            from .handlers.sharepoint_handler import SharePointHandler
            self.handlers[IntegrationType.SHAREPOINT] = SharePointHandler(self.config)
        except ImportError:
            pass
    
    def connect_integration(
        self,
        integration_type: IntegrationType,
        user_id: str,
        access_token: str,
        refresh_token: Optional[str] = None,
        expires_at: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> IntegrationConnection:
        """
        Conecta una integración.
        
        Args:
            integration_type: Tipo de integración
            user_id: ID del usuario
            access_token: Token de acceso OAuth
            refresh_token: Token de refresco (opcional)
            expires_at: Timestamp de expiración (opcional)
            metadata: Metadatos adicionales
        
        Returns:
            IntegrationConnection creada
        """
        import uuid
        integration_id = str(uuid.uuid4())
        
        connection = IntegrationConnection(
            integration_id=integration_id,
            integration_type=integration_type,
            user_id=user_id,
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=expires_at,
            metadata=metadata or {}
        )
        
        self.connections[integration_id] = connection
        self._save_connections()
        
        print(f"✅ Integración '{integration_type.value}' conectada: {integration_id}")
        return connection
    
    def disconnect_integration(self, integration_id: str):
        """Desconecta una integración."""
        if integration_id in self.connections:
            self.connections[integration_id].status = "disconnected"
            self._save_connections()
            print(f"✅ Integración desconectada: {integration_id}")
    
    def list_connections(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Lista conexiones."""
        connections = self.connections.values()
        if user_id:
            connections = [c for c in connections if c.user_id == user_id]
        
        result = []
        for conn in connections:
            # Manejar tanto enum como string
            if hasattr(conn.integration_type, 'value'):
                integration_type_str = conn.integration_type.value
            else:
                integration_type_str = str(conn.integration_type)
            
            result.append({
                "integration_id": conn.integration_id,
                "integration_type": integration_type_str,
                "status": conn.status,
                "connected_at": conn.connected_at,
                "last_sync": conn.last_sync
            })
        return result
    
    def get_connection(self, integration_id: str) -> Optional[IntegrationConnection]:
        """Obtiene una conexión."""
        return self.connections.get(integration_id)
    
    def search_integration(
        self,
        integration_id: str,
        query: str,
        max_results: int = 10
    ) -> List[Document]:
        """
        Busca en una integración específica.
        
        Args:
            integration_id: ID de la integración
            query: Consulta de búsqueda
            max_results: Máximo de resultados
        
        Returns:
            Lista de documentos encontrados
        """
        connection = self.get_connection(integration_id)
        if not connection or connection.status != "active":
            print(f"⚠️ Conexión {integration_id} no encontrada o inactiva")
            return []
        
        # Asegurar que integration_type sea un enum
        integration_type_key = connection.integration_type
        if isinstance(integration_type_key, str):
            try:
                integration_type_key = IntegrationType(integration_type_key)
            except (ValueError, KeyError):
                print(f"⚠️ Tipo de integración inválido: {integration_type_key}")
                return []
        
        handler = self.handlers.get(integration_type_key)
        if not handler:
            print(f"⚠️ Handler no disponible para {integration_type_key}")
            return []
        
        try:
            # Verificar si el token expiró
            if connection.expires_at and time.time() > connection.expires_at:
                print(f"⚠️ Token expirado para {integration_id}, intentando refrescar...")
                # Refrescar token si es posible
                if connection.refresh_token and hasattr(handler, 'refresh_token') and handler.refresh_token:
                    new_token = handler.refresh_token(connection.refresh_token)
                    if new_token:
                        connection.access_token = new_token
                        self._save_connections()
                        print(f"✅ Token refrescado para {integration_id}")
                    else:
                        print(f"⚠️ No se pudo refrescar token para {integration_id}, desconectando...")
                        connection.status = "disconnected"
                        self._save_connections()
                        return []  # Token expirado y no se pudo refrescar
                else:
                    print(f"⚠️ No se puede refrescar token para {integration_id} (sin refresh_token), desconectando...")
                    connection.status = "disconnected"
                    self._save_connections()
                    return []  # Token expirado y no se puede refrescar
            
            # Buscar en la integración
            integration_type_str = integration_type_key.value if hasattr(integration_type_key, 'value') else str(integration_type_key)
            print(f"🔍 Buscando en {integration_type_str} (ID: {integration_id[:8]}...) con query: {query[:50]}...")
            
            # Verificar que el token no esté vacío
            if not connection.access_token or not connection.access_token.strip():
                print(f"⚠️ Token vacío para {integration_id}, desconectando...")
                connection.status = "disconnected"
                self._save_connections()
                return []
            
            results = handler.search(query, connection.access_token, max_results)
            
            # Si el handler devuelve lista vacía y hubo error 401, desconectar
            if len(results) == 0 and hasattr(handler, '_last_error') and '401' in str(handler._last_error):
                print(f"⚠️ Token inválido detectado, desconectando {integration_id}...")
                connection.status = "disconnected"
                self._save_connections()
            
            print(f"✅ Encontrados {len(results)} resultados en {integration_type_str}")
            return results
        except Exception as e:
            error_str = str(e)
            print(f"❌ Error buscando en {integration_id}: {error_str}")
            
            # Si es error 401, desconectar
            if "401" in error_str or "unauthorized" in error_str.lower():
                print(f"⚠️ Error 401 detectado, desconectando {integration_id}...")
                connection.status = "disconnected"
                self._save_connections()
            
            import traceback
            traceback.print_exc()
            return []

