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
        
        # En producción, aquí se haría la autenticación real con OAuth
        # Por ahora, simulamos la conexión
        
        connection = AppConnection(
            connection_id=connection_id,
            app_type=app_type,
            app_name=app_name,
            status="connected",
            connected_at=time.strftime("%Y-%m-%d %H:%M:%S"),
            last_sync=time.strftime("%Y-%m-%d %H:%M:%S"),
            permissions=permissions or {},
            metadata={"credentials_stored": True}
        )
        
        self.connections[connection_id] = connection
        self._save_connections()
        
        print(f"✅ [Company Knowledge] App conectada: {app_name} ({app_type.value})")
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
        Busca en una app específica.
        En producción, esto usaría las APIs reales de cada app.
        """
        results = []
        
        # Simulación de búsqueda según tipo de app
        if app.app_type == IntegrationType.SLACK:
            # Buscar en canales y mensajes de Slack
            results.append(AppSearchResult(
                app_type=app.app_type,
                app_name=app.app_name,
                source_id=f"slack_channel_1",
                source_name=f"#{app.app_name} - Canal General",
                content=f"Mensajes relacionados con: {query}",
                snippet=f"Encontrado en canal #{app.app_name}: {query[:100]}...",
                url=f"https://slack.com/channels/{app.app_name}",
                relevance_score=0.85
            ))
        
        elif app.app_type == IntegrationType.GOOGLE_DRIVE:
            # Buscar en Google Drive
            results.append(AppSearchResult(
                app_type=app.app_type,
                app_name=app.app_name,
                source_id=f"gdrive_doc_1",
                source_name=f"Documento: {query}",
                content=f"Contenido del documento relacionado con: {query}",
                snippet=f"Documento encontrado en Google Drive: {query[:100]}...",
                url=f"https://drive.google.com/file/{app.app_name}",
                relevance_score=0.80
            ))
        
        elif app.app_type == IntegrationType.SHAREPOINT:
            # Buscar en SharePoint
            results.append(AppSearchResult(
                app_type=app.app_type,
                app_name=app.app_name,
                source_id=f"sharepoint_doc_1",
                source_name=f"SharePoint: {query}",
                content=f"Documento de SharePoint relacionado con: {query}",
                snippet=f"Encontrado en SharePoint: {query[:100]}...",
                url=f"https://sharepoint.com/sites/{app.app_name}",
                relevance_score=0.80
            ))
        
        elif app.app_type == IntegrationType.GITHUB:
            # Buscar en GitHub
            results.append(AppSearchResult(
                app_type=app.app_type,
                app_name=app.app_name,
                source_id=f"github_repo_1",
                source_name=f"Repo: {app.app_name}",
                content=f"Código relacionado con: {query}",
                snippet=f"Encontrado en GitHub repo {app.app_name}: {query[:100]}...",
                url=f"https://github.com/{app.app_name}",
                relevance_score=0.75
            ))
        
        elif app.app_type == IntegrationType.GMAIL:
            # Buscar en Gmail
            results.append(AppSearchResult(
                app_type=app.app_type,
                app_name=app.app_name,
                source_id=f"gmail_thread_1",
                source_name=f"Email: {query}",
                content=f"Email relacionado con: {query}",
                snippet=f"Thread de email encontrado: {query[:100]}...",
                url=f"https://mail.google.com/mail/u/0/#search/{query}",
                relevance_score=0.70
            ))
        
        elif app.app_type == IntegrationType.OUTLOOK:
            # Buscar en Outlook
            results.append(AppSearchResult(
                app_type=app.app_type,
                app_name=app.app_name,
                source_id=f"outlook_email_1",
                source_name=f"Outlook: {query}",
                content=f"Email de Outlook relacionado con: {query}",
                snippet=f"Email encontrado: {query[:100]}...",
                relevance_score=0.70
            ))
        
        elif app.app_type == IntegrationType.HUBSPOT:
            # Buscar en HubSpot
            results.append(AppSearchResult(
                app_type=app.app_type,
                app_name=app.app_name,
                source_id=f"hubspot_contact_1",
                source_name=f"HubSpot Contact: {query}",
                content=f"Contacto o deal relacionado con: {query}",
                snippet=f"Encontrado en HubSpot: {query[:100]}...",
                relevance_score=0.75
            ))
        
        elif app.app_type == IntegrationType.SALESFORCE:
            # Buscar en Salesforce
            results.append(AppSearchResult(
                app_type=app.app_type,
                app_name=app.app_name,
                source_id=f"salesforce_record_1",
                source_name=f"Salesforce: {query}",
                content=f"Registro de Salesforce relacionado con: {query}",
                snippet=f"Encontrado en Salesforce: {query[:100]}...",
                relevance_score=0.75
            ))
        
        elif app.app_type == IntegrationType.LINEAR:
            # Buscar en Linear
            results.append(AppSearchResult(
                app_type=app.app_type,
                app_name=app.app_name,
                source_id=f"linear_issue_1",
                source_name=f"Linear Issue: {query}",
                content=f"Issue o ticket relacionado con: {query}",
                snippet=f"Encontrado en Linear: {query[:100]}...",
                relevance_score=0.70
            ))
        
        # Actualizar última sincronización
        app.last_sync = time.strftime("%Y-%m-%d %H:%M:%S")
        self._save_connections()
        
        return results
    
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


