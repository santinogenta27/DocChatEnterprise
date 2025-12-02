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

# Importar integraciones avanzadas
try:
    from .langgraph_integration import LangGraphIntegration
    from .crewai_integration import CrewAIIntegration
    from .composio_integration import ComposioIntegration
    ADVANCED_INTEGRATIONS_AVAILABLE = True
except ImportError:
    ADVANCED_INTEGRATIONS_AVAILABLE = False
    LangGraphIntegration = None
    CrewAIIntegration = None
    ComposioIntegration = None


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
        
        # Integraciones avanzadas
        if ADVANCED_INTEGRATIONS_AVAILABLE:
            try:
                from ..utils.llm_factory import create_llm
                llm = create_llm(
                    provider="openai",
                    model=config.agentic_model or "gpt-4o",
                    api_key=config.openai_api_key
                )
                self.langgraph = LangGraphIntegration(config, llm=llm)
                print("✅ LangGraph integrado en Integration Manager")
            except Exception as e:
                print(f"⚠️ LangGraph no disponible: {e}")
                self.langgraph = None
            
            try:
                self.crewai = CrewAIIntegration(config)
                print("✅ CrewAI integrado en Integration Manager")
            except Exception as e:
                print(f"⚠️ CrewAI no disponible: {e}")
                self.crewai = None
            
            try:
                self.composio = ComposioIntegration(config)
                print("✅ Composio integrado en Integration Manager")
            except Exception as e:
                print(f"⚠️ Composio no disponible: {e}")
                self.composio = None
        else:
            self.langgraph = None
            self.crewai = None
            self.composio = None
    
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
    
    # ============================================
    # MÉTODOS CON LANGRAPH - Workflows Avanzados
    # ============================================
    
    def create_integration_sync_workflow(self, integration_id: str) -> Dict[str, Any]:
        """
        Crea un workflow LangGraph para sincronización de integraciones.
        
        Workflow:
        1. Verificar conexión
        2. Obtener datos
        3. Procesar datos
        4. Sincronizar
        """
        if not self.langgraph:
            return {"success": False, "error": "LangGraph no está disponible"}
        
        try:
            def verify_connection_node(state: Dict[str, Any]) -> Dict[str, Any]:
                """Nodo: Verificar conexión"""
                connection = self.get_connection(state["data"]["integration_id"])
                state["data"]["connected"] = connection is not None and connection.status == "active"
                return state
            
            def fetch_data_node(state: Dict[str, Any]) -> Dict[str, Any]:
                """Nodo: Obtener datos"""
                if state["data"].get("connected"):
                    # Simular obtención de datos
                    state["data"]["data_fetched"] = True
                return state
            
            def process_data_node(state: Dict[str, Any]) -> Dict[str, Any]:
                """Nodo: Procesar datos"""
                if state["data"].get("data_fetched"):
                    state["data"]["data_processed"] = True
                return state
            
            def sync_node(state: Dict[str, Any]) -> Dict[str, Any]:
                """Nodo: Sincronizar"""
                if state["data"].get("data_processed"):
                    # Actualizar last_sync
                    connection = self.get_connection(state["data"]["integration_id"])
                    if connection:
                        connection.last_sync = time.strftime("%Y-%m-%d %H:%M:%S")
                        self._save_connections()
                    state["data"]["synced"] = True
                return state
            
            # Crear workflow
            nodes = {
                "verify": verify_connection_node,
                "fetch": fetch_data_node,
                "process": process_data_node,
                "sync": sync_node
            }
            
            edges = [
                ("verify", "fetch"),
                ("fetch", "process"),
                ("process", "sync")
            ]
            
            workflow_id = f"sync_{integration_id}"
            workflow = self.langgraph.create_workflow(
                workflow_id=workflow_id,
                nodes=nodes,
                edges=edges,
                entry_point="verify",
                exit_point="sync"
            )
            
            # Ejecutar workflow
            result = self.langgraph.execute_workflow(
                workflow_id=workflow_id,
                initial_data={"integration_id": integration_id}
            )
            
            return result
        
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    # ============================================
    # MÉTODOS CON CREWAI - Multi-Agent Collaboration
    # ============================================
    
    def create_integration_crew(self) -> Dict[str, Any]:
        """
        Crea un crew de agentes CrewAI para gestión de integraciones.
        
        Agentes:
        - Integration Specialist: Especialista en conectar sistemas
        - Data Synchronizer: Sincroniza datos entre sistemas
        - Security Validator: Valida seguridad de conexiones
        """
        if not self.crewai:
            return {"success": False, "error": "CrewAI no está disponible"}
        
        try:
            # Crear agentes especializados
            integration_specialist = self.crewai.create_agent(
                agent_id="integration_specialist",
                role="Integration Specialist",
                goal="Connect and configure integrations with external systems",
                backstory="""You are an expert at integrating different systems. You understand 
                APIs, OAuth flows, authentication, and how to connect systems securely.""",
                verbose=True
            )
            
            data_synchronizer = self.crewai.create_agent(
                agent_id="data_synchronizer",
                role="Data Synchronization Specialist",
                goal="Synchronize data between integrated systems efficiently",
                backstory="""You are an expert at data synchronization. You understand how to 
                map data between systems, handle conflicts, and ensure data consistency.""",
                verbose=True
            )
            
            security_validator = self.crewai.create_agent(
                agent_id="security_validator",
                role="Security Validation Specialist",
                goal="Validate that integrations are secure and compliant",
                backstory="""You are an expert at security and compliance. You validate that 
                integrations follow security best practices and meet compliance requirements.""",
                verbose=True
            )
            
            # Crear tareas
            connection_task = self.crewai.create_task(
                description="Connect and configure a new integration",
                agent=integration_specialist,
                expected_output="Integration connected and configured successfully"
            )
            
            sync_task = self.crewai.create_task(
                description="Synchronize data between integrated systems",
                agent=data_synchronizer,
                expected_output="Data synchronized successfully"
            )
            
            validation_task = self.crewai.create_task(
                description="Validate security and compliance of integration",
                agent=security_validator,
                expected_output="Security validation report"
            )
            
            # Crear crew
            crew = self.crewai.create_crew(
                crew_id="integration_crew",
                agents=[integration_specialist, data_synchronizer, security_validator],
                tasks=[connection_task, sync_task, validation_task],
                process="sequential",
                verbose=True
            )
            
            return {
                "success": True,
                "crew_id": "integration_crew",
                "agents": ["integration_specialist", "data_synchronizer", "security_validator"],
                "message": "Integration crew creado exitosamente"
            }
        
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    # ============================================
    # MÉTODOS CON COMPOSIO - 250+ Integraciones
    # ============================================
    
    def connect_via_composio(self, app_name: str) -> Dict[str, Any]:
        """
        Conecta una app usando Composio (250+ apps disponibles).
        
        Args:
            app_name: Nombre de la app (gmail, slack, salesforce, hubspot, etc.)
        """
        if not self.composio:
            return {"success": False, "error": "Composio no está disponible"}
        
        try:
            result = self.composio.connect_app(app_name)
            
            if result.get("success"):
                # Crear conexión en IntegrationManager
                integration_id = f"composio_{app_name}_{int(time.time())}"
                connection = IntegrationConnection(
                    integration_id=integration_id,
                    integration_type=IntegrationType.SLACK,  # Default, se puede mejorar
                    user_id="user",
                    access_token=result.get("connection_id", ""),
                    status="active",
                    metadata={"composio_app": app_name, "composio_connection": True}
                )
                self.connections[integration_id] = connection
                self._save_connections()
            
            return result
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_composio_apps(self) -> List[Dict[str, Any]]:
        """Obtiene todas las apps disponibles en Composio."""
        if not self.composio:
            return []
        
        try:
            return self.composio.get_available_apps()
        except Exception as e:
            print(f"Error obteniendo apps de Composio: {e}")
            return []
    
    def execute_composio_action(
        self,
        app_name: str,
        action_name: str,
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Ejecuta una acción en una app de Composio.
        
        Args:
            app_name: Nombre de la app
            action_name: Nombre de la acción
            parameters: Parámetros de la acción
        """
        if not self.composio:
            return {"success": False, "error": "Composio no está disponible"}
        
        try:
            # Conectar app si no está conectada
            if app_name not in self.composio.connected_apps:
                connect_result = self.composio.connect_app(app_name)
                if not connect_result.get("success"):
                    return connect_result
            
            # Ejecutar acción
            result = self.composio.execute_action(
                app_name=app_name,
                action_name=action_name,
                parameters=parameters
            )
            
            return result
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_composio_app_actions(self, app_name: str) -> List[Dict[str, Any]]:
        """Obtiene acciones disponibles para una app de Composio."""
        if not self.composio:
            return []
        
        try:
            return self.composio.get_app_actions(app_name)
        except Exception as e:
            print(f"Error obteniendo acciones de {app_name}: {e}")
            return []

