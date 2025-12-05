"""
Composio Integration - 250+ integraciones pre-construidas
Integración de Composio para acceso a múltiples herramientas y APIs.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional
from datetime import datetime

try:
    # Intentar diferentes formas de importar Composio
    try:
        from composio import ComposioToolSet, Action, App
        from composio.client import ComposioClient
    except ImportError:
        # Intentar con composio_core
        from composio_core import ComposioToolSet, Action, App
        from composio_core.client import ComposioClient
    COMPOSIO_AVAILABLE = True
except ImportError:
    COMPOSIO_AVAILABLE = False
    # Nota: Composio no está instalado. Instala con: py -3.12 -m pip install composio-core

from ..config import AppConfig


class ComposioIntegration:
    """
    Integración de Composio para 250+ herramientas.
    
    Características:
    - 250+ integraciones pre-construidas
    - Autenticación automática
    - Function calling simplificado
    - APIs listas para usar
    """
    
    def __init__(self, config: AppConfig):
        self.config = config
        
        if not COMPOSIO_AVAILABLE:
            raise ImportError("Composio no está instalado. Instala con: pip install composio-core")
        
        # API key de Composio (opcional, puede usar sin API key para algunas funciones)
        self.api_key = os.getenv("COMPOSIO_API_KEY", "")
        
        # Inicializar cliente
        if self.api_key:
            self.client = ComposioClient(api_key=self.api_key)
        else:
            self.client = None
            print("⚠️ COMPOSIO_API_KEY no configurada. Algunas funciones pueden estar limitadas.")
        
        # Toolset para acciones (opcional)
        try:
            self.toolset = ComposioToolSet() if COMPOSIO_AVAILABLE else None
        except:
            self.toolset = None
        self.connected_apps: Dict[str, Any] = {}
    
    def get_available_apps(self) -> List[Dict[str, Any]]:
        """
        Obtiene lista de apps disponibles.
        
        Returns:
            Lista de apps con sus acciones disponibles
        """
        try:
            if self.client:
                apps = self.client.apps.list()
                return [
                    {
                        "name": app.name,
                        "display_name": app.display_name,
                        "description": app.description,
                        "actions_count": len(app.actions) if hasattr(app, 'actions') else 0
                    }
                    for app in apps
                ]
            else:
                # Lista básica de apps populares
                return [
                    {"name": "gmail", "display_name": "Gmail", "description": "Email management"},
                    {"name": "slack", "display_name": "Slack", "description": "Team communication"},
                    {"name": "salesforce", "display_name": "Salesforce", "description": "CRM"},
                    {"name": "hubspot", "display_name": "HubSpot", "description": "Marketing & CRM"},
                    {"name": "mailchimp", "display_name": "Mailchimp", "description": "Email marketing"},
                    {"name": "linkedin", "display_name": "LinkedIn", "description": "Professional network"},
                    {"name": "github", "display_name": "GitHub", "description": "Code repository"},
                    {"name": "jira", "display_name": "Jira", "description": "Project management"},
                    {"name": "zendesk", "display_name": "Zendesk", "description": "Customer support"},
                    {"name": "notion", "display_name": "Notion", "description": "Workspace"},
                ]
        except Exception as e:
            print(f"Error obteniendo apps: {e}")
            return []
    
    def connect_app(
        self,
        app_name: str,
        credentials: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Conecta una app de Composio.
        
        Args:
            app_name: Nombre de la app (ej: "gmail", "slack", "salesforce")
            credentials: Credenciales (opcional, puede usar OAuth)
        """
        try:
            if self.client:
                # Conectar usando OAuth o credenciales
                app = self.client.apps.get(app_name)
                if credentials:
                    # Conectar con credenciales
                    connection = app.connect(credentials=credentials)
                else:
                    # Iniciar OAuth flow
                    connection = app.connect()
                
                self.connected_apps[app_name] = app
                
                return {
                    "success": True,
                    "app_name": app_name,
                    "connected": True,
                    "connection_id": connection.id if hasattr(connection, 'id') else None
                }
            else:
                # Modo simulado sin API key
                self.connected_apps[app_name] = {"name": app_name, "simulated": True}
                return {
                    "success": True,
                    "app_name": app_name,
                    "connected": True,
                    "simulated": True,
                    "message": "Modo simulado (configura COMPOSIO_API_KEY para conexión real)"
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def execute_action(
        self,
        app_name: str,
        action_name: str,
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Ejecuta una acción en una app conectada.
        
        Args:
            app_name: Nombre de la app
            action_name: Nombre de la acción
            parameters: Parámetros de la acción
        """
        try:
            if app_name not in self.connected_apps:
                # Intentar conectar automáticamente
                connect_result = self.connect_app(app_name)
                if not connect_result.get("success"):
                    return {
                        "success": False,
                        "error": f"App {app_name} no está conectada y no se pudo conectar"
                    }
            
            app = self.connected_apps[app_name]
            
            if self.client and not (isinstance(app, dict) and app.get("simulated")):
                # Ejecutar acción real
                try:
                    if hasattr(app, 'get_action'):
                        action = app.get_action(action_name)
                        result = action.execute(parameters=parameters)
                    elif hasattr(app, 'actions'):
                        # Buscar acción en lista de acciones
                        action = next((a for a in app.actions if a.name == action_name), None)
                        if action:
                            result = action.execute(parameters=parameters)
                        else:
                            raise ValueError(f"Action {action_name} not found")
                    else:
                        raise ValueError("App does not support actions")
                except Exception as e:
                    return {
                        "success": False,
                        "error": f"Error ejecutando acción: {str(e)}"
                    }
                
                return {
                    "success": True,
                    "app_name": app_name,
                    "action": action_name,
                    "result": result
                }
            else:
                # Modo simulado
                return {
                    "success": True,
                    "app_name": app_name,
                    "action": action_name,
                    "result": {
                        "simulated": True,
                        "message": f"Acción {action_name} simulada en {app_name}",
                        "parameters": parameters
                    },
                    "note": "Configura COMPOSIO_API_KEY para ejecución real"
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_app_actions(self, app_name: str) -> List[Dict[str, Any]]:
        """
        Obtiene acciones disponibles para una app.
        
        Args:
            app_name: Nombre de la app
        """
        try:
            if self.client:
                app = self.client.apps.get(app_name)
                return [
                    {
                        "name": action.name,
                        "description": action.description,
                        "parameters": action.parameters_schema if hasattr(action, 'parameters_schema') else {}
                    }
                    for action in app.actions
                ]
            else:
                # Acciones comunes por app (simulado)
                common_actions = {
                    "gmail": ["send_email", "read_emails", "search_emails"],
                    "slack": ["send_message", "create_channel", "list_channels"],
                    "salesforce": ["create_lead", "update_lead", "get_lead"],
                    "hubspot": ["create_contact", "update_contact", "create_deal"],
                    "mailchimp": ["create_campaign", "send_campaign", "list_audiences"]
                }
                return [
                    {"name": action, "description": f"Action: {action}"}
                    for action in common_actions.get(app_name, [])
                ]
        except Exception as e:
            return []

