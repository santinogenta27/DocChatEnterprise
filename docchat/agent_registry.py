"""Agent Registry: Registro centralizado de agentes y APIs empresariales.

Este módulo mantiene metadata de agentes, APIs, y herramientas
para habilitar descubrimiento dinámico y planificación de workflows.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime

try:
    from langchain_openai import OpenAIEmbeddings
    EMBEDDINGS_AVAILABLE = True
except ImportError:
    EMBEDDINGS_AVAILABLE = False


@dataclass
class AgentParameter:
    """Parámetro de entrada o salida de un agente."""
    name: str
    type: str  # "string", "number", "boolean", "object", "array"
    description: Optional[str] = None
    required: bool = False
    default: Optional[Any] = None
    enum: Optional[List[str]] = None  # Valores permitidos


@dataclass
class AgentMetadata:
    """Metadata de un agente/API."""
    agent_id: str
    name: str
    description: str
    category: str  # "ticket", "notification", "crm", "erp", "storage", "email", etc.
    input_parameters: List[AgentParameter] = field(default_factory=list)
    output_parameters: List[AgentParameter] = field(default_factory=list)
    deployment_info: Optional[Dict[str, Any]] = None  # Docker image, API endpoint, etc.
    stream_tags: List[str] = field(default_factory=list)  # Tags para activación por streams
    cost_per_call: Optional[float] = None  # Costo estimado por llamada
    latency_ms: Optional[float] = None  # Latencia estimada
    requires_approval: bool = False  # Si requiere aprobación humana
    tenant_id: Optional[str] = None
    registered_at: str = field(default_factory=lambda: datetime.now().isoformat())


class AgentRegistry:
    """Registro centralizado de agentes y APIs empresariales."""
    
    def __init__(self, config: Any, registry_path: Optional[Path] = None):
        self.config = config
        self.registry_path = registry_path or (config.cache_dir / "agent_registry.json")
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Almacenamiento en memoria
        self.agents: Dict[str, AgentMetadata] = {}  # agent_id -> AgentMetadata
        
        # Embeddings para búsqueda semántica (opcional)
        self.embeddings = None
        if EMBEDDINGS_AVAILABLE:
            try:
                self.embeddings = OpenAIEmbeddings(model=self.config.embedding_model)
            except Exception as e:
                print(f"⚠️ No se pudo inicializar embeddings para Agent Registry: {e}")
        
        # Cargar registry existente
        self._load_registry()
        
        # Registrar agentes predefinidos
        self._register_default_agents()
    
    def _load_registry(self):
        """Carga el registry desde disco."""
        if self.registry_path.exists():
            try:
                with open(self.registry_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for agent_id, agent_data in data.get("agents", {}).items():
                        agent = self._dict_to_agent(agent_data)
                        self.agents[agent_id] = agent
                print(f"✅ Agent Registry cargado: {len(self.agents)} agentes")
            except Exception as e:
                print(f"⚠️ Error cargando Agent Registry: {e}")
    
    def _save_registry(self):
        """Guarda el registry en disco."""
        try:
            data = {
                "agents": {
                    agent_id: self._agent_to_dict(agent)
                    for agent_id, agent in self.agents.items()
                }
            }
            with open(self.registry_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"⚠️ Error guardando Agent Registry: {e}")
    
    def _agent_to_dict(self, agent: AgentMetadata) -> Dict[str, Any]:
        """Convierte AgentMetadata a dict para serialización."""
        return {
            "agent_id": agent.agent_id,
            "name": agent.name,
            "description": agent.description,
            "category": agent.category,
            "input_parameters": [asdict(p) for p in agent.input_parameters],
            "output_parameters": [asdict(p) for p in agent.output_parameters],
            "deployment_info": agent.deployment_info,
            "stream_tags": agent.stream_tags,
            "cost_per_call": agent.cost_per_call,
            "latency_ms": agent.latency_ms,
            "requires_approval": agent.requires_approval,
            "tenant_id": agent.tenant_id,
            "registered_at": agent.registered_at,
        }
    
    def _dict_to_agent(self, data: Dict[str, Any]) -> AgentMetadata:
        """Reconstruye AgentMetadata desde dict."""
        return AgentMetadata(
            agent_id=data["agent_id"],
            name=data["name"],
            description=data["description"],
            category=data["category"],
            input_parameters=[
                AgentParameter(**p) if isinstance(p, dict) else p
                for p in data.get("input_parameters", [])
            ],
            output_parameters=[
                AgentParameter(**p) if isinstance(p, dict) else p
                for p in data.get("output_parameters", [])
            ],
            deployment_info=data.get("deployment_info"),
            stream_tags=data.get("stream_tags", []),
            cost_per_call=data.get("cost_per_call"),
            latency_ms=data.get("latency_ms"),
            requires_approval=data.get("requires_approval", False),
            tenant_id=data.get("tenant_id"),
            registered_at=data.get("registered_at", datetime.now().isoformat()),
        )
    
    def _register_default_agents(self):
        """Registra agentes predefinidos del sistema."""
        default_agents = [
            {
                "agent_id": "jira_create_ticket",
                "name": "Jira Ticket Creator",
                "description": "Crea tickets en Jira automáticamente",
                "category": "ticket",
                "input_parameters": [
                    AgentParameter("project", "string", "Proyecto de Jira", required=True),
                    AgentParameter("summary", "string", "Resumen del ticket", required=True),
                    AgentParameter("description", "string", "Descripción detallada", required=True),
                    AgentParameter("priority", "string", "Prioridad (Low, Medium, High, Critical)", default="Medium"),
                ],
                "output_parameters": [
                    AgentParameter("ticket_id", "string", "ID del ticket creado"),
                    AgentParameter("url", "string", "URL del ticket"),
                ],
                "stream_tags": ["jira", "ticket", "create"],
                "requires_approval": True,
            },
            {
                "agent_id": "slack_send_message",
                "name": "Slack Message Sender",
                "description": "Envía mensajes a canales de Slack",
                "category": "notification",
                "input_parameters": [
                    AgentParameter("channel", "string", "Canal de Slack", required=True),
                    AgentParameter("text", "string", "Mensaje a enviar", required=True),
                ],
                "output_parameters": [
                    AgentParameter("status", "string", "Estado del envío"),
                    AgentParameter("message_id", "string", "ID del mensaje"),
                ],
                "stream_tags": ["slack", "notification", "alert"],
            },
            {
                "agent_id": "teams_send_message",
                "name": "Microsoft Teams Message Sender",
                "description": "Envía mensajes a Microsoft Teams",
                "category": "notification",
                "input_parameters": [
                    AgentParameter("text", "string", "Mensaje a enviar", required=True),
                ],
                "output_parameters": [
                    AgentParameter("status", "string", "Estado del envío"),
                ],
                "stream_tags": ["teams", "notification", "alert"],
            },
            {
                "agent_id": "send_email_smtp",
                "name": "Email Sender",
                "description": "Envía emails vía SMTP",
                "category": "email",
                "input_parameters": [
                    AgentParameter("to", "array", "Lista de destinatarios", required=True),
                    AgentParameter("subject", "string", "Asunto del email", required=True),
                    AgentParameter("body", "string", "Cuerpo del email", required=True),
                    AgentParameter("from_email", "string", "Remitente"),
                ],
                "output_parameters": [
                    AgentParameter("status", "string", "Estado del envío"),
                    AgentParameter("message_id", "string", "ID del mensaje"),
                ],
                "stream_tags": ["email", "notification"],
            },
            {
                "agent_id": "sql_executor",
                "name": "SQL Executor",
                "description": "Ejecuta queries SQL en bases de datos",
                "category": "database",
                "input_parameters": [
                    AgentParameter("query", "string", "Query SQL a ejecutar", required=True),
                    AgentParameter("mode", "string", "Modo (read/write)", default="read"),
                ],
                "output_parameters": [
                    AgentParameter("rows", "array", "Filas retornadas"),
                    AgentParameter("row_count", "number", "Número de filas"),
                ],
                "stream_tags": ["sql", "database", "query"],
            },
        ]
        
        # Registrar solo si no existen
        for agent_data in default_agents:
            if agent_data["agent_id"] not in self.agents:
                agent = AgentMetadata(**agent_data)
                self.agents[agent.agent_id] = agent
        
        if default_agents:
            self._save_registry()
    
    def register_agent(
        self,
        agent_id: str,
        name: str,
        description: str,
        category: str,
        input_parameters: Optional[List[Dict[str, Any]]] = None,
        output_parameters: Optional[List[Dict[str, Any]]] = None,
        deployment_info: Optional[Dict[str, Any]] = None,
        stream_tags: Optional[List[str]] = None,
        cost_per_call: Optional[float] = None,
        latency_ms: Optional[float] = None,
        requires_approval: bool = False,
        tenant_id: Optional[str] = None,
    ) -> bool:
        """Registra un nuevo agente en el registry.
        
        Returns:
            True si se registró exitosamente
        """
        # Convertir parámetros a objetos AgentParameter
        input_params = [
            AgentParameter(**p) if isinstance(p, dict) else p
            for p in (input_parameters or [])
        ]
        output_params = [
            AgentParameter(**p) if isinstance(p, dict) else p
            for p in (output_parameters or [])
        ]
        
        agent = AgentMetadata(
            agent_id=agent_id,
            name=name,
            description=description,
            category=category,
            input_parameters=input_params,
            output_parameters=output_params,
            deployment_info=deployment_info,
            stream_tags=stream_tags or [],
            cost_per_call=cost_per_call,
            latency_ms=latency_ms,
            requires_approval=requires_approval,
            tenant_id=tenant_id,
        )
        
        self.agents[agent_id] = agent
        self._save_registry()
        print(f"✅ Agente registrado: {agent_id}")
        return True
    
    def search_agents(
        self,
        query: str,
        category: Optional[str] = None,
        tenant_id: Optional[str] = None,
        limit: int = 10,
    ) -> List[AgentMetadata]:
        """Busca agentes relevantes usando búsqueda semántica/keyword.
        
        Args:
            query: Query en lenguaje natural
            category: Filtrar por categoría (opcional)
            tenant_id: Filtrar por tenant (opcional)
            limit: Número máximo de resultados
        
        Returns:
            Lista de agentes ordenados por relevancia
        """
        results = []
        query_lower = query.lower()
        
        for agent in self.agents.values():
            # Filtrar por tenant
            if tenant_id and agent.tenant_id != tenant_id:
                continue
            
            # Filtrar por categoría
            if category and agent.category != category:
                continue
            
            score = 0.0
            
            # Match en nombre
            if query_lower in agent.name.lower():
                score += 2.0
            
            # Match en descripción
            if query_lower in agent.description.lower():
                score += 1.5
            
            # Match en categoría
            if query_lower in agent.category.lower():
                score += 1.0
            
            # Match en stream tags
            for tag in agent.stream_tags:
                if query_lower in tag.lower():
                    score += 0.5
            
            if score > 0:
                results.append((score, agent))
        
        # Ordenar por score y retornar top N
        results.sort(key=lambda x: x[0], reverse=True)
        return [agent for _, agent in results[:limit]]
    
    def get_agent(self, agent_id: str) -> Optional[AgentMetadata]:
        """Obtiene un agente por ID."""
        return self.agents.get(agent_id)
    
    def list_agents(
        self,
        category: Optional[str] = None,
        tenant_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Lista todos los agentes registrados."""
        agents = []
        for agent in self.agents.values():
            if category and agent.category != category:
                continue
            if tenant_id and agent.tenant_id != tenant_id:
                continue
            agents.append({
                "agent_id": agent.agent_id,
                "name": agent.name,
                "description": agent.description,
                "category": agent.category,
                "input_params_count": len(agent.input_parameters),
                "output_params_count": len(agent.output_parameters),
                "requires_approval": agent.requires_approval,
            })
        return agents

