"""
Agent Orchestration Studio - Estudio de Orquestación de Agentes
Modo completamente nuevo e innovador que permite crear, orquestar y gestionar
múltiples agentes especializados que colaboran en tiempo real.

Características:
- Crear agentes especializados visualmente
- Definir workflows complejos con Goal Decomposition
- Orquestar colaboración entre agentes
- Ver ejecución en tiempo real
- Aprendizaje automático con Test Time Training
- Reinforcement Planning para encontrar mejores caminos
- Path-dependent Reasoning para probar diferentes enfoques
- Person in the Loop para control humano
"""

from __future__ import annotations

import json
import time
import uuid
import asyncio
from typing import List, Dict, Optional, Any, Callable, Set
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from datetime import datetime

from langchain_core.language_models import BaseLanguageModel
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.documents import Document

from .config import AppConfig
from .reinforcement_planning import ReinforcementPlanner
from .test_time_training import TestTimeTrainer
from .path_dependent_reasoning import PathDependentReasoner
from .goal_decomposition import GoalDecomposer
from .mcp_manager import MCPManager


class AgentRole(str, Enum):
    """Roles de agentes especializados."""
    ANALYZER = "analyzer"  # Analiza datos y documentos
    RESEARCHER = "researcher"  # Investiga y busca información
    CODER = "coder"  # Escribe y ejecuta código
    WRITER = "writer"  # Genera documentos y reportes
    INTEGRATOR = "integrator"  # Integra con sistemas externos
    VALIDATOR = "validator"  # Valida resultados y calidad
    COORDINATOR = "coordinator"  # Coordina otros agentes
    EXECUTOR = "executor"  # Ejecuta acciones específicas


class AgentStatus(str, Enum):
    """Estado de un agente."""
    IDLE = "idle"
    WORKING = "working"
    WAITING = "waiting"  # Esperando input de otro agente
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"


class WorkflowStatus(str, Enum):
    """Estado de un workflow."""
    DRAFT = "draft"
    ACTIVE = "active"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"


@dataclass
class SpecializedAgent:
    """Agente especializado con un rol específico."""
    agent_id: str
    name: str
    role: AgentRole
    description: str
    system_prompt: str
    capabilities: List[str] = field(default_factory=list)  # Qué puede hacer
    tools: List[str] = field(default_factory=list)  # Herramientas disponibles
    status: AgentStatus = AgentStatus.IDLE
    current_task: Optional[str] = None
    performance_stats: Dict[str, Any] = field(default_factory=lambda: {
        "tasks_completed": 0,
        "tasks_failed": 0,
        "avg_execution_time": 0.0,
        "success_rate": 0.0
    })
    created_at: float = field(default_factory=time.time)
    last_used: float = field(default_factory=time.time)


@dataclass
class AgentConnection:
    """Conexión entre agentes (quién se comunica con quién)."""
    connection_id: str
    from_agent_id: str
    to_agent_id: str
    connection_type: str  # "data", "validation", "coordination", "sequential"
    data_format: Optional[str] = None  # Formato de datos que pasan
    conditions: Dict[str, Any] = field(default_factory=dict)  # Condiciones para activar


@dataclass
class WorkflowStep:
    """Un paso en un workflow."""
    step_id: str
    agent_id: str  # Qué agente ejecuta este paso
    description: str
    input_requirements: List[str] = field(default_factory=list)  # Qué necesita
    output_provides: List[str] = field(default_factory=list)  # Qué produce
    dependencies: List[str] = field(default_factory=list)  # IDs de pasos de los que depende
    timeout: float = 300.0  # Timeout en segundos
    retry_count: int = 0
    max_retries: int = 3
    status: str = "pending"  # "pending", "running", "completed", "failed"
    result: Optional[Any] = None
    error: Optional[str] = None
    execution_time: float = 0.0
    started_at: Optional[float] = None
    completed_at: Optional[float] = None


@dataclass
class Workflow:
    """Workflow completo con múltiples agentes."""
    workflow_id: str
    name: str
    description: str
    goal: str  # Objetivo de alto nivel
    agents: List[SpecializedAgent] = field(default_factory=list)
    connections: List[AgentConnection] = field(default_factory=list)
    steps: List[WorkflowStep] = field(default_factory=list)
    status: WorkflowStatus = WorkflowStatus.DRAFT
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    progress: float = 0.0  # 0.0 - 1.0
    result: Optional[Any] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentMessage:
    """Mensaje entre agentes (Agent-to-Agent Communication)."""
    message_id: str
    from_agent_id: str
    to_agent_id: str
    message_type: str  # "request", "response", "data", "validation", "coordination"
    content: Any
    timestamp: float = field(default_factory=time.time)
    requires_response: bool = False
    responded: bool = False


class AgentOrchestrationStudio:
    """
    Estudio de Orquestación de Agentes.
    
    Permite crear, gestionar y ejecutar workflows complejos con múltiples agentes
    especializados que colaboran en tiempo real.
    
    Características innovadoras:
    - Creación visual de agentes especializados
    - Workflows complejos con Goal Decomposition
    - Agent-to-Agent Communication en tiempo real
    - Reinforcement Planning para optimizar workflows
    - Path-dependent Reasoning para probar diferentes enfoques
    - Test Time Training para mejorar continuamente
    - Person in the Loop para control humano
    """
    
    def __init__(
        self,
        config: AppConfig,
        llm: Optional[BaseLanguageModel] = None,
        mcp_manager: Optional[MCPManager] = None
    ):
        self.config = config
        self.llm = llm
        self.mcp_manager = mcp_manager
        
        # Workflows y agentes
        self.workflows: Dict[str, Workflow] = {}
        self.agents: Dict[str, SpecializedAgent] = {}  # Agentes reutilizables
        
        # Comunicación entre agentes
        self.agent_messages: List[AgentMessage] = []
        self.message_queue: Dict[str, List[AgentMessage]] = {}  # Por agente
        
        # Sistemas avanzados
        self.reinforcement_planner = ReinforcementPlanner(
            config=config,
            llm=llm,
            max_depth=15,
            max_branches=8,
            learning_enabled=True
        )
        
        self.test_time_trainer = TestTimeTrainer(
            config=config,
            llm=llm,
            learning_rate=0.15,
            min_confidence=0.65
        )
        
        self.path_reasoner = PathDependentReasoner(
            config=config,
            llm=llm,
            max_paths=7
        )
        
        self.goal_decomposer = GoalDecomposer(
            config=config,
            llm=llm
        )
        
        # Directorio para persistencia
        self.storage_dir = Path(config.memory_dir) / "agent_orchestration_studio"
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        # Cargar workflows y agentes guardados
        self._load_data()
        
        # Inicializar agentes predefinidos
        self._initialize_predefined_agents()
    
    def _load_data(self):
        """Carga workflows y agentes guardados."""
        # Cargar workflows
        workflows_file = self.storage_dir / "workflows.json"
        if workflows_file.exists():
            try:
                with open(workflows_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for wf_data in data.get("workflows", []):
                        workflow = Workflow(**wf_data)
                        # Reconstruir agentes, conexiones y pasos
                        workflow.agents = [SpecializedAgent(**a) for a in wf_data.get("agents", [])]
                        workflow.connections = [AgentConnection(**c) for c in wf_data.get("connections", [])]
                        workflow.steps = [WorkflowStep(**s) for s in wf_data.get("steps", [])]
                        self.workflows[workflow.workflow_id] = workflow
                print(f"✅ [Agent Studio] {len(self.workflows)} workflows cargados")
            except Exception as e:
                print(f"⚠️ [Agent Studio] Error cargando workflows: {e}")
        
        # Cargar agentes reutilizables
        agents_file = self.storage_dir / "agents.json"
        if agents_file.exists():
            try:
                with open(agents_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for agent_data in data.get("agents", []):
                        agent = SpecializedAgent(**agent_data)
                        self.agents[agent.agent_id] = agent
                print(f"✅ [Agent Studio] {len(self.agents)} agentes cargados")
            except Exception as e:
                print(f"⚠️ [Agent Studio] Error cargando agentes: {e}")
    
    def _save_data(self):
        """Guarda workflows y agentes."""
        # Guardar workflows
        workflows_file = self.storage_dir / "workflows.json"
        try:
            data = {
                "workflows": [
                    {
                        **asdict(wf),
                        "agents": [asdict(a) for a in wf.agents],
                        "connections": [asdict(c) for c in wf.connections],
                        "steps": [asdict(s) for s in wf.steps]
                    }
                    for wf in self.workflows.values()
                ]
            }
            with open(workflows_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"⚠️ [Agent Studio] Error guardando workflows: {e}")
        
        # Guardar agentes
        agents_file = self.storage_dir / "agents.json"
        try:
            data = {
                "agents": [asdict(agent) for agent in self.agents.values()]
            }
            with open(agents_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"⚠️ [Agent Studio] Error guardando agentes: {e}")
    
    def _initialize_predefined_agents(self):
        """Inicializa agentes predefinidos especializados."""
        predefined_agents = [
            {
                "name": "Analizador de Datos",
                "role": AgentRole.ANALYZER,
                "description": "Especialista en analizar datos, documentos y encontrar patrones",
                "system_prompt": """Eres un analizador experto de datos y documentos.
Tu trabajo es analizar información, encontrar patrones, tendencias y insights.
Eres preciso, detallado y siempre proporcionas evidencia para tus conclusiones.""",
                "capabilities": ["análisis de datos", "detección de patrones", "generación de insights"],
                "tools": ["database", "analytics", "table_analysis"]
            },
            {
                "name": "Investigador",
                "role": AgentRole.RESEARCHER,
                "description": "Especialista en investigar y buscar información",
                "system_prompt": """Eres un investigador experto.
Tu trabajo es buscar información, verificar fuentes y proporcionar datos precisos.
Eres meticuloso y siempre verificas la información antes de presentarla.""",
                "capabilities": ["búsqueda de información", "verificación de fuentes", "síntesis"],
                "tools": ["web_search", "database", "integrations"]
            },
            {
                "name": "Desarrollador",
                "role": AgentRole.CODER,
                "description": "Especialista en escribir y ejecutar código",
                "system_prompt": """Eres un desarrollador experto.
Tu trabajo es escribir código limpio, eficiente y bien documentado.
Siempre pruebas tu código y manejas errores apropiadamente.""",
                "capabilities": ["programación", "ejecución de código", "debugging"],
                "tools": ["code_execution", "database", "integrations"]
            },
            {
                "name": "Escritor",
                "role": AgentRole.WRITER,
                "description": "Especialista en generar documentos y reportes",
                "system_prompt": """Eres un escritor profesional experto.
Tu trabajo es crear documentos claros, bien estructurados y profesionales.
Adaptas tu estilo según la audiencia y el propósito del documento.""",
                "capabilities": ["generación de documentos", "reportes", "presentaciones"],
                "tools": ["report", "presentation", "email"]
            },
            {
                "name": "Integrador",
                "role": AgentRole.INTEGRATOR,
                "description": "Especialista en integrar con sistemas externos",
                "system_prompt": """Eres un integrador experto de sistemas.
Tu trabajo es conectar y sincronizar datos entre diferentes sistemas.
Eres cuidadoso con la seguridad y siempre validas las integraciones.""",
                "capabilities": ["integración de sistemas", "sincronización", "APIs"],
                "tools": ["mcp", "integrations", "database"]
            },
            {
                "name": "Validador",
                "role": AgentRole.VALIDATOR,
                "description": "Especialista en validar resultados y calidad",
                "system_prompt": """Eres un validador experto de calidad.
Tu trabajo es verificar que los resultados sean correctos, completos y de alta calidad.
Eres riguroso y siempre reportas problemas que encuentres.""",
                "capabilities": ["validación", "control de calidad", "verificación"],
                "tools": ["adversarial_testing", "analytics"]
            },
            {
                "name": "Coordinador",
                "role": AgentRole.COORDINATOR,
                "description": "Especialista en coordinar otros agentes",
                "system_prompt": """Eres un coordinador experto de equipos de agentes.
Tu trabajo es coordinar, asignar tareas y asegurar que todos trabajen eficientemente.
Eres organizado y siempre mantienes la visión general del proyecto.""",
                "capabilities": ["coordinación", "asignación de tareas", "gestión de proyectos"],
                "tools": ["scheduler", "workflow"]
            },
            {
                "name": "Ejecutor",
                "role": AgentRole.EXECUTOR,
                "description": "Especialista en ejecutar acciones específicas",
                "system_prompt": """Eres un ejecutor experto de acciones.
Tu trabajo es ejecutar tareas específicas de forma eficiente y precisa.
Siempre verificas que las acciones se completaron correctamente.""",
                "capabilities": ["ejecución de acciones", "automatización", "RPA"],
                "tools": ["text_to_action", "rpa", "integrations"]
            }
        ]
        
        for agent_data in predefined_agents:
            agent_id = f"predefined_{agent_data['role'].value}"
            if agent_id not in self.agents:
                agent = SpecializedAgent(
                    agent_id=agent_id,
                    name=agent_data["name"],
                    role=agent_data["role"],
                    description=agent_data["description"],
                    system_prompt=agent_data["system_prompt"],
                    capabilities=agent_data["capabilities"],
                    tools=agent_data["tools"]
                )
                self.agents[agent_id] = agent
    
    def create_specialized_agent(
        self,
        name: str,
        role: str,
        description: str,
        system_prompt: Optional[str] = None,
        capabilities: Optional[List[str]] = None,
        tools: Optional[List[str]] = None
    ) -> str:
        """
        Crea un nuevo agente especializado (versión síncrona).
        
        Returns:
            agent_id: ID del agente creado
        """
        agent_id = str(uuid.uuid4())
        
        # Si no hay system prompt y hay LLM, usar uno básico (sin async para compatibilidad)
        if not system_prompt:
            system_prompt = f"Eres {name}, un agente especializado en {description}. Tu rol es {role}."
        
        agent = SpecializedAgent(
            agent_id=agent_id,
            name=name,
            role=AgentRole(role),
            description=description,
            system_prompt=system_prompt,
            capabilities=capabilities or [],
            tools=tools or []
        )
        
        self.agents[agent_id] = agent
        self._save_data()
        
        print(f"✅ [Agent Studio] Agente creado: {name} ({agent_id})")
        return agent_id
    
    async def create_specialized_agent_async(
        self,
        name: str,
        role: str,
        description: str,
        system_prompt: Optional[str] = None,
        capabilities: Optional[List[str]] = None,
        tools: Optional[List[str]] = None
    ) -> str:
        """
        Crea un nuevo agente especializado (versión async con generación de prompt).
        
        Returns:
            agent_id: ID del agente creado
        """
        agent_id = str(uuid.uuid4())
        
        # Generar system prompt si no se proporciona
        if not system_prompt and self.llm:
            system_prompt = await self._generate_agent_prompt(name, role, description)
        
        agent = SpecializedAgent(
            agent_id=agent_id,
            name=name,
            role=AgentRole(role),
            description=description,
            system_prompt=system_prompt or f"Eres {name}, un agente especializado en {description}",
            capabilities=capabilities or [],
            tools=tools or []
        )
        
        self.agents[agent_id] = agent
        self._save_data()
        
        print(f"✅ [Agent Studio] Agente creado: {name} ({agent_id})")
        return agent_id
    
    async def _generate_agent_prompt(self, name: str, role: str, description: str) -> str:
        """Genera un system prompt para un agente usando LLM."""
        if not self.llm:
            return f"Eres {name}, un agente especializado en {description}"
        
        prompt = f"""Genera un system prompt profesional para un agente especializado.

Nombre: {name}
Rol: {role}
Descripción: {description}

El prompt debe:
1. Definir claramente el rol y responsabilidades
2. Establecer el tono y estilo de trabajo
3. Incluir mejores prácticas
4. Ser conciso pero completo

Responde SOLO con el system prompt, sin explicaciones adicionales."""
        
        try:
            response = await self.llm.ainvoke(prompt)
            return response.content if hasattr(response, 'content') else str(response)
        except:
            return f"Eres {name}, un agente especializado en {description}"
    
    async def create_workflow(
        self,
        name: str,
        description: str,
        goal: str,
        agent_ids: Optional[List[str]] = None,
        use_goal_decomposition: bool = True
    ) -> str:
        """
        Crea un nuevo workflow.
        
        Si use_goal_decomposition es True, descompone el objetivo automáticamente
        y crea los pasos del workflow basándose en la descomposición.
        
        Returns:
            workflow_id: ID del workflow creado
        """
        workflow_id = str(uuid.uuid4())
        print(f"🎬 [Agent Studio] Creando workflow: {name}...")
        
        # Crear workflow base
        workflow = Workflow(
            workflow_id=workflow_id,
            name=name,
            description=description,
            goal=goal,
            status=WorkflowStatus.DRAFT
        )
        
        # Agregar agentes al workflow
        if agent_ids:
            for agent_id in agent_ids:
                if agent_id in self.agents:
                    workflow.agents.append(self.agents[agent_id])
        else:
            # Si no se especifican, usar agentes predefinidos relevantes
            workflow.agents = list(self.agents.values())[:5]  # Primeros 5
        
        # Descomponer objetivo si se solicita
        if use_goal_decomposition and self.llm:
            try:
                goal_id = await self.goal_decomposer.decompose_goal(
                    goal_description=goal,
                    context=f"Workflow: {name}\n{description}"
                )
                
                goal_obj = self.goal_decomposer.get_goal(goal_id)
                if goal_obj:
                    # Crear pasos del workflow basados en subtareas
                    for i, subtask in enumerate(goal_obj.subtasks):
                        # Asignar agente apropiado para cada subtarea
                        assigned_agent = self._assign_agent_to_subtask(subtask, workflow.agents)
                        
                        step = WorkflowStep(
                            step_id=str(uuid.uuid4()),
                            agent_id=assigned_agent.agent_id if assigned_agent else workflow.agents[0].agent_id,
                            description=subtask.description,
                            input_requirements=subtask.dependencies,
                            output_provides=[f"result_{i}"],
                            dependencies=[],  # Se resolverán después
                            timeout=subtask.estimated_time * 60  # Convertir minutos a segundos
                        )
                        workflow.steps.append(step)
                    
                    # Resolver dependencias entre pasos
                    self._resolve_step_dependencies(workflow, goal_obj)
                    
                    workflow.metadata["goal_id"] = goal_id
                    print(f"✅ [Agent Studio] Objetivo descompuesto en {len(workflow.steps)} pasos")
            except Exception as e:
                print(f"⚠️ [Agent Studio] Error descomponiendo objetivo: {e}")
        
        # Si no hay pasos, crear uno genérico
        if not workflow.steps:
            step = WorkflowStep(
                step_id=str(uuid.uuid4()),
                agent_id=workflow.agents[0].agent_id if workflow.agents else "",
                description=goal,
                output_provides=["final_result"]
            )
            workflow.steps.append(step)
        
        # Crear conexiones entre agentes basadas en los pasos
        self._create_agent_connections(workflow)
        
        self.workflows[workflow_id] = workflow
        self._save_data()
        
        print(f"✅ [Agent Studio] Workflow creado: {name} ({workflow_id})")
        return workflow_id
    
    def _assign_agent_to_subtask(self, subtask: Any, available_agents: List[SpecializedAgent]) -> Optional[SpecializedAgent]:
        """Asigna el agente más apropiado para una subtarea."""
        if not available_agents:
            return None
        
        # Análisis simple de qué agente es más apropiado
        description_lower = subtask.description.lower()
        
        # Buscar por palabras clave
        if any(word in description_lower for word in ["analizar", "analizar", "patrón", "insight"]):
            for agent in available_agents:
                if agent.role == AgentRole.ANALYZER:
                    return agent
        
        if any(word in description_lower for word in ["investigar", "buscar", "encontrar", "información"]):
            for agent in available_agents:
                if agent.role == AgentRole.RESEARCHER:
                    return agent
        
        if any(word in description_lower for word in ["código", "programar", "ejecutar", "script"]):
            for agent in available_agents:
                if agent.role == AgentRole.CODER:
                    return agent
        
        if any(word in description_lower for word in ["escribir", "documento", "reporte", "generar"]):
            for agent in available_agents:
                if agent.role == AgentRole.WRITER:
                    return agent
        
        if any(word in description_lower for word in ["integrar", "conectar", "sincronizar", "api"]):
            for agent in available_agents:
                if agent.role == AgentRole.INTEGRATOR:
                    return agent
        
        if any(word in description_lower for word in ["validar", "verificar", "revisar", "calidad"]):
            for agent in available_agents:
                if agent.role == AgentRole.VALIDATOR:
                    return agent
        
        # Default: primer agente disponible
        return available_agents[0]
    
    def _resolve_step_dependencies(self, workflow: Workflow, goal_obj: Any):
        """Resuelve dependencias entre pasos del workflow."""
        # Crear mapa de subtask_id -> step_id
        subtask_to_step = {}
        for i, step in enumerate(workflow.steps):
            if i < len(goal_obj.subtasks):
                subtask = goal_obj.subtasks[i]
                subtask_to_step[subtask.subtask_id] = step.step_id
        
        # Asignar dependencias
        for i, step in enumerate(workflow.steps):
            if i < len(goal_obj.subtasks):
                subtask = goal_obj.subtasks[i]
                for dep_id in subtask.dependencies:
                    if dep_id in subtask_to_step:
                        step.dependencies.append(subtask_to_step[dep_id])
    
    def _create_agent_connections(self, workflow: Workflow):
        """Crea conexiones entre agentes basadas en los pasos del workflow."""
        # Crear conexiones secuenciales entre pasos
        for i in range(len(workflow.steps) - 1):
            current_step = workflow.steps[i]
            next_step = workflow.steps[i + 1]
            
            # Si hay dependencia, crear conexión
            if next_step.step_id in current_step.dependencies or i == 0:
                connection = AgentConnection(
                    connection_id=str(uuid.uuid4()),
                    from_agent_id=current_step.agent_id,
                    to_agent_id=next_step.agent_id,
                    connection_type="sequential",
                    data_format="json"
                )
                workflow.connections.append(connection)
    
    async def execute_workflow(
        self,
        workflow_id: str,
        input_data: Optional[Dict[str, Any]] = None,
        require_human_approval: bool = True
    ) -> Dict[str, Any]:
        """
        Ejecuta un workflow completo.
        
        Usa Reinforcement Planning para optimizar la ejecución,
        Path-dependent Reasoning para probar diferentes enfoques,
        y Test Time Training para aprender de cada ejecución.
        
        Args:
            workflow_id: ID del workflow a ejecutar
            input_data: Datos de entrada para el workflow
            require_human_approval: Si True, requiere aprobación humana para acciones críticas
        
        Returns:
            Resultado de la ejecución del workflow
        """
        if workflow_id not in self.workflows:
            return {"success": False, "error": "Workflow no encontrado"}
        
        workflow = self.workflows[workflow_id]
        workflow.status = WorkflowStatus.RUNNING
        workflow.started_at = time.time()
        
        print(f"🚀 [Agent Studio] Ejecutando workflow: {workflow.name}...")
        
        # Usar Reinforcement Planning para planificar la ejecución
        planning_result = await self.reinforcement_planner.plan_and_execute(
            goal=workflow.goal,
            context=f"Workflow: {workflow.name}\n{workflow.description}",
            executor=self._create_workflow_executor(workflow, input_data, require_human_approval)
        )
        
        # Ejecutar pasos del workflow
        execution_results = {}
        workflow_data = input_data or {}
        
        # Ordenar pasos por dependencias (topological sort)
        execution_order = self._calculate_execution_order(workflow.steps)
        
        for step_id in execution_order:
            step = next(s for s in workflow.steps if s.step_id == step_id)
            agent = next(a for a in workflow.agents if a.agent_id == step.agent_id)
            
            # Verificar dependencias
            if not all(dep_id in execution_results for dep_id in step.dependencies):
                step.status = "blocked"
                continue
            
            # Ejecutar paso
            step.status = "running"
            step.started_at = time.time()
            agent.status = AgentStatus.WORKING
            agent.current_task = step.description
            
            try:
                # Preparar input para el agente
                step_input = {
                    "description": step.description,
                    "workflow_data": workflow_data,
                    "dependencies": {dep_id: execution_results[dep_id] for dep_id in step.dependencies}
                }
                
                # Ejecutar usando Path-dependent Reasoning
                reasoning_result = await self.path_reasoner.reason_with_multiple_paths(
                    problem=step.description,
                    context=f"Workflow: {workflow.name}\nDatos: {json.dumps(step_input, indent=2)}",
                    task_type=f"workflow_step_{agent.role.value}",
                    executor=self._create_step_executor(agent, step, require_human_approval)
                )
                
                best_result = reasoning_result.get("best_path", {}).get("result")
                
                # Si requiere aprobación humana y es acción crítica
                if require_human_approval and self._is_critical_action(step, agent):
                    # En producción, aquí se pausaría y esperaría aprobación
                    # Por ahora, continuamos pero registramos
                    print(f"⚠️ [Agent Studio] Acción crítica requiere aprobación: {step.description}")
                
                step.result = best_result
                step.status = "completed"
                step.completed_at = time.time()
                step.execution_time = step.completed_at - step.started_at
                
                execution_results[step_id] = best_result
                workflow_data.update({output: best_result for output in step.output_provides})
                
                # Actualizar estadísticas del agente
                agent.performance_stats["tasks_completed"] += 1
                agent.performance_stats["last_used"] = time.time()
                
                # Registrar en Test Time Training
                self.test_time_trainer.record_episode(
                    task_type=f"workflow_{workflow_id}",
                    input_data=step_input,
                    output_data=best_result,
                    success=True,
                    execution_time=step.execution_time,
                    metadata={
                        "workflow_id": workflow_id,
                        "step_id": step_id,
                        "agent_role": agent.role.value
                    }
                )
                
                # Enviar mensaje a otros agentes si es necesario
                await self._send_agent_messages(workflow, step, best_result)
                
            except Exception as e:
                step.status = "failed"
                step.error = str(e)
                step.completed_at = time.time()
                step.execution_time = step.completed_at - (step.started_at or time.time())
                
                agent.performance_stats["tasks_failed"] += 1
                
                # Registrar error en Test Time Training
                self.test_time_trainer.record_episode(
                    task_type=f"workflow_{workflow_id}",
                    input_data=step_input,
                    output_data=None,
                    success=False,
                    feedback=str(e),
                    execution_time=step.execution_time
                )
            
            finally:
                agent.status = AgentStatus.IDLE
                agent.current_task = None
        
        # Actualizar progreso
        completed_steps = sum(1 for s in workflow.steps if s.status == "completed")
        workflow.progress = completed_steps / len(workflow.steps) if workflow.steps else 0.0
        
        # Determinar estado final
        if all(s.status == "completed" for s in workflow.steps):
            workflow.status = WorkflowStatus.COMPLETED
            workflow.result = execution_results
        elif any(s.status == "failed" for s in workflow.steps):
            workflow.status = WorkflowStatus.FAILED
        else:
            workflow.status = WorkflowStatus.RUNNING
        
        workflow.completed_at = time.time()
        self._save_data()
        
        return {
            "workflow_id": workflow_id,
            "status": workflow.status.value,
            "progress": workflow.progress,
            "result": workflow.result,
            "execution_time": workflow.completed_at - workflow.started_at,
            "steps_completed": completed_steps,
            "total_steps": len(workflow.steps)
        }
    
    def _calculate_execution_order(self, steps: List[WorkflowStep]) -> List[str]:
        """Calcula el orden de ejecución respetando dependencias."""
        # Topological sort
        in_degree = {s.step_id: len(s.dependencies) for s in steps}
        queue = [s.step_id for s in steps if in_degree[s.step_id] == 0]
        order = []
        
        while queue:
            current = queue.pop(0)
            order.append(current)
            
            # Reducir grado de entrada de dependientes
            for step in steps:
                if current in step.dependencies:
                    in_degree[step.step_id] -= 1
                    if in_degree[step.step_id] == 0:
                        queue.append(step.step_id)
        
        # Agregar pasos restantes
        remaining = [s.step_id for s in steps if s.step_id not in order]
        order.extend(remaining)
        
        return order
    
    def _is_critical_action(self, step: WorkflowStep, agent: SpecializedAgent) -> bool:
        """Determina si una acción es crítica y requiere aprobación humana."""
        # Acciones críticas: ejecutar código, modificar datos, integraciones externas
        critical_keywords = ["ejecutar", "modificar", "eliminar", "actualizar", "enviar", "publicar"]
        description_lower = step.description.lower()
        
        return any(keyword in description_lower for keyword in critical_keywords) or \
               agent.role in [AgentRole.EXECUTOR, AgentRole.INTEGRATOR]
    
    def _create_workflow_executor(self, workflow: Workflow, input_data: Optional[Dict[str, Any]], require_human_approval: bool):
        """Crea un executor para Reinforcement Planning del workflow."""
        async def executor(action: str, context: str) -> Any:
            """Ejecuta una acción como parte del planning del workflow."""
            # Simular ejecución del workflow
            return f"Workflow '{workflow.name}' ejecutado: {action}"
        
        return executor
    
    def _create_step_executor(self, agent: SpecializedAgent, step: WorkflowStep, require_human_approval: bool):
        """Crea un executor para Path-dependent Reasoning de un paso."""
        async def executor(approach: str, strategy: str, steps_list: List[str], context: str) -> Any:
            """Ejecuta un enfoque para un paso del workflow."""
            if not self.llm:
                return f"Resultado simulado: {approach}"
            
            # Construir prompt para el agente
            prompt = f"""{agent.system_prompt}

Tarea asignada: {step.description}

Enfoque a usar: {approach}
Estrategia: {strategy}
Pasos: {', '.join(steps_list)}

Contexto adicional:
{context}

Ejecuta esta tarea siguiendo el enfoque especificado.
Proporciona un resultado detallado y completo."""
            
            try:
                response = await self.llm.ainvoke(prompt)
                result = response.content if hasattr(response, 'content') else str(response)
                
                # Si requiere aprobación humana y es crítica
                if require_human_approval and self._is_critical_action(step, agent):
                    # En producción, aquí se pausaría
                    result = f"[REQUIERE APROBACIÓN HUMANA]\n{result}"
                
                return result
            except Exception as e:
                raise Exception(f"Error ejecutando paso: {e}")
        
        return executor
    
    async def _send_agent_messages(self, workflow: Workflow, step: WorkflowStep, result: Any):
        """Envía mensajes a otros agentes (Agent-to-Agent Communication)."""
        # Encontrar agentes que necesitan este resultado
        for connection in workflow.connections:
            if connection.from_agent_id == step.agent_id:
                message = AgentMessage(
                    message_id=str(uuid.uuid4()),
                    from_agent_id=step.agent_id,
                    to_agent_id=connection.to_agent_id,
                    message_type=connection.connection_type,
                    content=result,
                    requires_response=False
                )
                
                self.agent_messages.append(message)
                
                # Agregar a cola del agente receptor
                if connection.to_agent_id not in self.message_queue:
                    self.message_queue[connection.to_agent_id] = []
                self.message_queue[connection.to_agent_id].append(message)
    
    def get_workflow(self, workflow_id: str) -> Optional[Workflow]:
        """Obtiene un workflow por ID."""
        return self.workflows.get(workflow_id)
    
    def list_workflows(self, status_filter: Optional[str] = None) -> List[Workflow]:
        """Lista workflows."""
        workflows = list(self.workflows.values())
        
        if status_filter:
            workflows = [w for w in workflows if w.status.value == status_filter]
        
        return sorted(workflows, key=lambda w: w.created_at, reverse=True)
    
    def list_agents(self, role_filter: Optional[str] = None) -> List[SpecializedAgent]:
        """Lista agentes disponibles."""
        agents = list(self.agents.values())
        
        if role_filter:
            agents = [a for a in agents if a.role.value == role_filter]
        
        return sorted(agents, key=lambda a: a.last_used, reverse=True)
    
    def get_agent_messages(self, agent_id: Optional[str] = None) -> List[AgentMessage]:
        """Obtiene mensajes entre agentes."""
        messages = self.agent_messages
        
        if agent_id:
            messages = [m for m in messages if m.from_agent_id == agent_id or m.to_agent_id == agent_id]
        
        return sorted(messages, key=lambda m: m.timestamp, reverse=True)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Obtiene estadísticas del estudio."""
        total_workflows = len(self.workflows)
        active_workflows = sum(1 for w in self.workflows.values() if w.status == WorkflowStatus.ACTIVE)
        completed_workflows = sum(1 for w in self.workflows.values() if w.status == WorkflowStatus.COMPLETED)
        
        total_agents = len(self.agents)
        active_agents = sum(1 for a in self.agents.values() if a.status == AgentStatus.WORKING)
        
        total_messages = len(self.agent_messages)
        
        return {
            "total_workflows": total_workflows,
            "active_workflows": active_workflows,
            "completed_workflows": completed_workflows,
            "total_agents": total_agents,
            "active_agents": active_agents,
            "total_messages": total_messages,
            "reinforcement_planning": self.reinforcement_planner.get_statistics(),
            "test_time_training": self.test_time_trainer.get_statistics(),
            "path_dependent_reasoning": self.path_reasoner.get_statistics(),
            "goal_decomposition": self.goal_decomposer.get_statistics()
        }

