"""A2A Protocol (Agent-to-Agent): Estándar de comunicación entre agents.

Implementa el protocolo A2A de Google para comunicación estandarizada:
- Agent Cards (metadata JSON)
- Mensajes estandarizados
- Task management
- Artifacts (resultados)
- Capability discovery
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Union
from datetime import datetime
from enum import Enum


class TaskStatus(str, Enum):
    """Estado de una tarea A2A."""
    CREATED = "created"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class MessageType(str, Enum):
    """Tipo de mensaje A2A."""
    TASK_REQUEST = "task_request"
    TASK_RESPONSE = "task_response"
    CAPABILITY_DISCOVERY = "capability_discovery"
    STATUS_UPDATE = "status_update"
    ARTIFACT = "artifact"


@dataclass
class AgentCard:
    """Agent Card: Metadata de un agent en formato A2A."""
    agent_id: str
    name: str
    description: str
    version: str = "1.0.0"
    capabilities: List[Dict[str, Any]] = field(default_factory=list)  # Lista de funciones soportadas
    input_formats: List[str] = field(default_factory=lambda: ["text", "json"])
    output_formats: List[str] = field(default_factory=lambda: ["text", "json"])
    authentication_required: bool = False
    auth_type: Optional[str] = None  # "oauth", "api_key", "mcp", etc.
    endpoint: Optional[str] = None  # URL del agent si es remoto
    tags: List[str] = field(default_factory=list)
    category: Optional[str] = None  # "ticket", "notification", "data", etc.
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class A2AMessage:
    """Mensaje A2A estandarizado."""
    message_id: str
    message_type: MessageType
    from_agent_id: str
    to_agent_id: Optional[str] = None  # None para broadcast
    task_id: Optional[str] = None
    headers: Dict[str, Any] = field(default_factory=dict)
    body: Dict[str, Any] = field(default_factory=dict)
    parts: List[Dict[str, Any]] = field(default_factory=list)  # Contenido multimodal
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class A2ATask:
    """Tarea A2A con lifecycle completo."""
    task_id: str
    task_type: str
    status: TaskStatus
    from_agent_id: str
    to_agent_id: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    result: Optional[Any] = None
    artifacts: List[Dict[str, Any]] = field(default_factory=list)
    error: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    completed_at: Optional[str] = None


@dataclass
class A2AArtifact:
    """Artifact: Resultado estandarizado de una tarea."""
    artifact_id: str
    task_id: str
    artifact_type: str  # "document", "code", "image", "data", etc.
    content: Any
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


class A2AProtocol:
    """Implementación del protocolo A2A para comunicación entre agents."""
    
    def __init__(self, config: Any):
        self.config = config
        self.agent_registry: Dict[str, AgentCard] = {}  # agent_id -> AgentCard
        self.active_tasks: Dict[str, A2ATask] = {}  # task_id -> A2ATask
        self.message_queue: List[A2AMessage] = []
        
        # Persistencia
        self.registry_path = config.cache_dir / "a2a_agent_registry.json"
        self.tasks_path = config.cache_dir / "a2a_tasks.json"
        self._load_registry()
    
    def _load_registry(self):
        """Carga agent registry desde disco."""
        if self.registry_path.exists():
            try:
                with open(self.registry_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for agent_id, card_data in data.get("agents", {}).items():
                        self.agent_registry[agent_id] = AgentCard(**card_data)
                print(f"✅ A2A Registry cargado: {len(self.agent_registry)} agents")
            except Exception as e:
                print(f"⚠️ Error cargando A2A Registry: {e}")
    
    def _save_registry(self):
        """Guarda agent registry en disco."""
        try:
            data = {
                "agents": {
                    agent_id: asdict(card)
                    for agent_id, card in self.agent_registry.items()
                }
            }
            with open(self.registry_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"⚠️ Error guardando A2A Registry: {e}")
    
    def register_agent(
        self,
        agent_id: str,
        name: str,
        description: str,
        capabilities: Optional[List[Dict[str, Any]]] = None,
        input_formats: Optional[List[str]] = None,
        output_formats: Optional[List[str]] = None,
        authentication_required: bool = False,
        auth_type: Optional[str] = None,
        endpoint: Optional[str] = None,
        tags: Optional[List[str]] = None,
        category: Optional[str] = None,
    ) -> AgentCard:
        """Registra un agent con su Agent Card."""
        card = AgentCard(
            agent_id=agent_id,
            name=name,
            description=description,
            capabilities=capabilities or [],
            input_formats=input_formats or ["text", "json"],
            output_formats=output_formats or ["text", "json"],
            authentication_required=authentication_required,
            auth_type=auth_type,
            endpoint=endpoint,
            tags=tags or [],
            category=category,
        )
        
        self.agent_registry[agent_id] = card
        self._save_registry()
        print(f"✅ Agent registrado en A2A: {agent_id}")
        return card
    
    def discover_agents(
        self,
        query: Optional[str] = None,
        category: Optional[str] = None,
        capability: Optional[str] = None,
    ) -> List[AgentCard]:
        """Descubre agents por query, categoría o capacidad."""
        results = []
        
        for agent_id, card in self.agent_registry.items():
            # Filtrar por categoría
            if category and card.category != category:
                continue
            
            # Filtrar por capacidad
            if capability:
                has_capability = any(
                    capability.lower() in str(cap).lower()
                    for cap in card.capabilities
                )
                if not has_capability:
                    continue
            
            # Filtrar por query (búsqueda en nombre, descripción, tags)
            if query:
                query_lower = query.lower()
                matches = (
                    query_lower in card.name.lower() or
                    query_lower in card.description.lower() or
                    any(query_lower in tag.lower() for tag in card.tags)
                )
                if not matches:
                    continue
            
            results.append(card)
        
        return results
    
    def get_agent_card(self, agent_id: str) -> Optional[AgentCard]:
        """Obtiene Agent Card de un agent."""
        return self.agent_registry.get(agent_id)
    
    def create_task(
        self,
        task_type: str,
        from_agent_id: str,
        to_agent_id: str,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> A2ATask:
        """Crea una nueva tarea A2A."""
        task_id = str(uuid.uuid4())
        
        task = A2ATask(
            task_id=task_id,
            task_type=task_type,
            status=TaskStatus.CREATED,
            from_agent_id=from_agent_id,
            to_agent_id=to_agent_id,
            parameters=parameters or {},
        )
        
        self.active_tasks[task_id] = task
        return task
    
    def update_task_status(
        self,
        task_id: str,
        status: TaskStatus,
        result: Optional[Any] = None,
        error: Optional[str] = None,
        artifacts: Optional[List[Dict[str, Any]]] = None,
    ) -> bool:
        """Actualiza el estado de una tarea."""
        if task_id not in self.active_tasks:
            return False
        
        task = self.active_tasks[task_id]
        task.status = status
        task.updated_at = datetime.now().isoformat()
        
        if result is not None:
            task.result = result
        
        if error:
            task.error = error
        
        if artifacts:
            task.artifacts.extend(artifacts)
        
        if status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
            task.completed_at = datetime.now().isoformat()
        
        return True
    
    def send_message(
        self,
        message_type: MessageType,
        from_agent_id: str,
        to_agent_id: Optional[str],
        body: Optional[Dict[str, Any]] = None,
        parts: Optional[List[Dict[str, Any]]] = None,
        task_id: Optional[str] = None,
    ) -> A2AMessage:
        """Envía un mensaje A2A estandarizado."""
        message = A2AMessage(
            message_id=str(uuid.uuid4()),
            message_type=message_type,
            from_agent_id=from_agent_id,
            to_agent_id=to_agent_id,
            task_id=task_id,
            body=body or {},
            parts=parts or [],
        )
        
        self.message_queue.append(message)
        return message
    
    def get_messages(
        self,
        agent_id: Optional[str] = None,
        message_type: Optional[MessageType] = None,
        limit: int = 100,
    ) -> List[A2AMessage]:
        """Obtiene mensajes de la cola."""
        results = []
        
        for msg in self.message_queue:
            # Filtrar por agent
            if agent_id and msg.to_agent_id != agent_id:
                continue
            
            # Filtrar por tipo
            if message_type and msg.message_type != message_type:
                continue
            
            results.append(msg)
        
        return results[:limit]
    
    def create_artifact(
        self,
        task_id: str,
        artifact_type: str,
        content: Any,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> A2AArtifact:
        """Crea un artifact (resultado estandarizado)."""
        artifact = A2AArtifact(
            artifact_id=str(uuid.uuid4()),
            task_id=task_id,
            artifact_type=artifact_type,
            content=content,
            metadata=metadata or {},
        )
        
        # Agregar artifact a la tarea
        if task_id in self.active_tasks:
            self.active_tasks[task_id].artifacts.append(asdict(artifact))
        
        return artifact
    
    def list_agents(self) -> List[Dict[str, Any]]:
        """Lista todos los agents registrados."""
        return [
            {
                "agent_id": card.agent_id,
                "name": card.name,
                "description": card.description,
                "category": card.category,
                "capabilities_count": len(card.capabilities),
                "tags": card.tags,
            }
            for card in self.agent_registry.values()
        ]

