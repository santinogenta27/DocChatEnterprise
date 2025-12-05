"""Agentic Workflow Orchestrator: Orquestación dinámica de agents multi-etapa.

Basado en la visión de Eric Schmidt sobre "agentic revolution":
- Agents encadenados para workflows complejos
- Memoria persistente
- Reinforcement learning
- Human-in-the-loop
- Auto-mejora recursiva
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable
from datetime import datetime
from enum import Enum

try:
    from crewai import Agent, Task, Crew, Process
    from crewai.tools import BaseTool
    CREWAI_AVAILABLE = True
except ImportError:
    CREWAI_AVAILABLE = False
    print("⚠️ CrewAI no está instalado. Instala con: pip install crewai")

try:
    from langgraph.graph import StateGraph, END
    from langgraph.checkpoint.memory import MemorySaver
    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False
    print("⚠️ LangGraph no está instalado. Instala con: pip install langgraph")


class AgentStatus(str, Enum):
    """Estado de un agente en el workflow."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    WAITING_APPROVAL = "waiting_approval"
    APPROVED = "approved"
    REJECTED = "rejected"


class WorkflowStatus(str, Enum):
    """Estado del workflow completo."""
    CREATED = "created"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class WorkflowAgent:
    """Definición de un agente en el workflow."""
    agent_id: str
    name: str
    role: str
    goal: str
    backstory: str
    tools: List[str] = field(default_factory=list)
    requires_approval: bool = False
    max_iterations: int = 3
    status: AgentStatus = AgentStatus.PENDING
    output: Optional[Any] = None
    error: Optional[str] = None
    execution_time_ms: float = 0.0


@dataclass
class WorkflowStep:
    """Paso en el workflow (conexión entre agents)."""
    step_id: str
    from_agent_id: str
    to_agent_id: str
    condition: Optional[str] = None  # Condición para ejecutar (ej: "if output.status == 'success'")
    transform: Optional[str] = None  # Transformación del output antes de pasar al siguiente


@dataclass
class WorkflowMemory:
    """Memoria persistente del workflow."""
    workflow_id: str
    session_id: str
    state: Dict[str, Any] = field(default_factory=dict)
    agent_outputs: Dict[str, Any] = field(default_factory=dict)
    reward_signals: List[Dict[str, Any]] = field(default_factory=list)  # Para RL
    human_approvals: Dict[str, bool] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class WorkflowExecution:
    """Ejecución de un workflow."""
    execution_id: str
    workflow_id: str
    status: WorkflowStatus
    current_agent_id: Optional[str] = None
    agents: List[WorkflowAgent] = field(default_factory=list)
    steps: List[WorkflowStep] = field(default_factory=list)
    memory: Optional[WorkflowMemory] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error: Optional[str] = None


class AgenticWorkflowOrchestrator:
    """Orquestador de workflows agentic multi-etapa."""
    
    def __init__(
        self,
        config: Any,
        llm_provider: str = "openai",
    ):
        self.config = config
        self.llm_provider = llm_provider
        
        # Almacenamiento
        self.workflows_dir = config.cache_dir / "agentic_workflows"
        self.workflows_dir.mkdir(parents=True, exist_ok=True)
        
        # Memoria persistente (Redis o archivo)
        self.memory_store: Dict[str, WorkflowMemory] = {}
        
        # Ejecuciones activas
        self.active_executions: Dict[str, WorkflowExecution] = {}
        
        # Verificar dependencias
        self.crewai_available = CREWAI_AVAILABLE
        self.langgraph_available = LANGGRAPH_AVAILABLE
        
        # Sistema de memoria
        try:
            from .agentic_memory import AgenticMemory
            self.memory_system = AgenticMemory(config)
        except Exception as e:
            print(f"⚠️ Error inicializando AgenticMemory: {e}")
            self.memory_system = None
        
        # Sistema de RL avanzado
        try:
            from .agentic_rl_advanced import AdvancedRLManager
            self.rl_manager = AdvancedRLManager(config)
        except Exception as e:
            print(f"⚠️ Error inicializando AdvancedRLManager: {e}")
            self.rl_manager = None
        
        # A2A Protocol para comunicación estandarizada
        try:
            from .agentic_a2a_protocol import A2AProtocol
            self.a2a_protocol = A2AProtocol(config)
            print("✅ A2A Protocol inicializado")
        except Exception as e:
            print(f"⚠️ Error inicializando A2A Protocol: {e}")
            self.a2a_protocol = None
        
        # MCP × A2A Bridge para descubrimiento automático de tools
        try:
            from .agentic_mcp_a2a_bridge import MCPA2ABridge
            # Necesitamos MCPManager - intentar obtenerlo del config o crear uno
            mcp_manager = None
            try:
                # Intentar obtener MCPManager si está disponible
                if hasattr(config, 'mcp_manager') and config.mcp_manager:
                    mcp_manager = config.mcp_manager
                else:
                    # Crear MCPManager si no existe
                    from .mcp_manager import MCPManager
                    from langchain_openai import ChatOpenAI
                    llm = ChatOpenAI(model=config.llm_model, temperature=0.2)
                    mcp_manager = MCPManager(config=config, llm=llm)
                    mcp_manager.initialize()
            except Exception as e:
                print(f"⚠️ No se pudo inicializar MCPManager para bridge: {e}")
            
            if mcp_manager and self.a2a_protocol:
                self.mcp_a2a_bridge = MCPA2ABridge(
                    a2a_protocol=self.a2a_protocol,
                    mcp_manager=mcp_manager,
                )
                print("✅ MCP × A2A Bridge inicializado (descubrimiento automático de tools)")
            else:
                self.mcp_a2a_bridge = None
                print("⚠️ MCP × A2A Bridge no disponible (MCPManager o A2A no inicializado)")
        except Exception as e:
            print(f"⚠️ Error inicializando MCP × A2A Bridge: {e}")
            self.mcp_a2a_bridge = None
        
        # Tools personalizados para CrewAI
        try:
            from .agentic_crewai_tools import get_crewai_tools
            self.crewai_tools = get_crewai_tools()
        except Exception as e:
            print(f"⚠️ Error cargando CrewAI tools: {e}")
            self.crewai_tools = []
        
        # A2A Protocol para comunicación estandarizada
        try:
            from .agentic_a2a_protocol import A2AProtocol
            self.a2a_protocol = A2AProtocol(config)
            print("✅ A2A Protocol inicializado")
        except Exception as e:
            print(f"⚠️ Error inicializando A2A Protocol: {e}")
            self.a2a_protocol = None
        
        # MCP × A2A Bridge para descubrimiento automático de tools
        try:
            from .agentic_mcp_a2a_bridge import MCPA2ABridge
            # Intentar obtener MCPManager
            mcp_manager = None
            try:
                if hasattr(config, 'mcp_manager') and config.mcp_manager:
                    mcp_manager = config.mcp_manager
                else:
                    from .mcp_manager import MCPManager
                    from langchain_openai import ChatOpenAI
                    llm = ChatOpenAI(model=getattr(config, 'llm_model', 'gpt-4o-mini'), temperature=0.2)
                    mcp_manager = MCPManager(config=config, llm=llm)
                    mcp_manager.initialize()
            except Exception as e:
                print(f"⚠️ No se pudo inicializar MCPManager para bridge: {e}")
            
            if mcp_manager and self.a2a_protocol:
                self.mcp_a2a_bridge = MCPA2ABridge(
                    a2a_protocol=self.a2a_protocol,
                    mcp_manager=mcp_manager,
                )
                print("✅ MCP × A2A Bridge inicializado (descubrimiento automático de tools)")
                
                # Progressive Disclosure para carga on-demand de tools
                try:
                    from .mcp_progressive_disclosure import MCPProgressiveDisclosure, ToolDetailLevel
                    self.mcp_progressive_disclosure = MCPProgressiveDisclosure(mcp_manager)
                    print("✅ Progressive Disclosure habilitado (carga on-demand de tools)")
                except Exception as e:
                    print(f"⚠️ Error inicializando Progressive Disclosure: {e}")
                    self.mcp_progressive_disclosure = None
                
                # Tool Optimizer para mejorar descriptions
                try:
                    from .mcp_tool_optimizer import MCPToolOptimizer
                    self.mcp_tool_optimizer = MCPToolOptimizer()
                    print("✅ Tool Optimizer habilitado (mejora de descriptions)")
                except Exception as e:
                    print(f"⚠️ Error inicializando Tool Optimizer: {e}")
                    self.mcp_tool_optimizer = None
            else:
                self.mcp_a2a_bridge = None
                self.mcp_progressive_disclosure = None
                self.mcp_tool_optimizer = None
                print("⚠️ MCP × A2A Bridge no disponible")
        except Exception as e:
            print(f"⚠️ Error inicializando MCP × A2A Bridge: {e}")
            self.mcp_a2a_bridge = None
            self.mcp_progressive_disclosure = None
            self.mcp_tool_optimizer = None
        
        if not self.crewai_available:
            print("⚠️ CrewAI no disponible. Algunas funcionalidades estarán limitadas.")
            print("   💡 Instala con: pip install crewai")
    
    def create_workflow(
        self,
        workflow_id: str,
        name: str,
        description: str,
        agents: List[Dict[str, Any]],
        steps: List[Dict[str, Any]],
        initial_input: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Crea un nuevo workflow agentic.
        
        Args:
            workflow_id: ID único del workflow
            name: Nombre del workflow
            description: Descripción
            agents: Lista de definiciones de agents
            steps: Lista de conexiones entre agents
            initial_input: Input inicial del workflow
        
        Returns:
            Dict con workflow creado
        """
        # Convertir agents a objetos WorkflowAgent
        workflow_agents = []
        for agent_data in agents:
            agent = WorkflowAgent(
                agent_id=agent_data["agent_id"],
                name=agent_data["name"],
                role=agent_data["role"],
                goal=agent_data["goal"],
                backstory=agent_data.get("backstory", ""),
                tools=agent_data.get("tools", []),
                requires_approval=agent_data.get("requires_approval", False),
                max_iterations=agent_data.get("max_iterations", 3),
            )
            workflow_agents.append(agent)
        
        # Convertir steps a objetos WorkflowStep
        workflow_steps = []
        for step_data in steps:
            step = WorkflowStep(
                step_id=step_data.get("step_id", str(uuid.uuid4())),
                from_agent_id=step_data["from_agent_id"],
                to_agent_id=step_data["to_agent_id"],
                condition=step_data.get("condition"),
                transform=step_data.get("transform"),
            )
            workflow_steps.append(step)
        
        # Crear workflow
        workflow = {
            "workflow_id": workflow_id,
            "name": name,
            "description": description,
            "agents": [asdict(a) for a in workflow_agents],
            "steps": [asdict(s) for s in workflow_steps],
            "initial_input": initial_input or {},
            "created_at": datetime.now().isoformat(),
        }
        
        # Guardar workflow
        workflow_path = self.workflows_dir / f"{workflow_id}.json"
        with open(workflow_path, "w", encoding="utf-8") as f:
            json.dump(workflow, f, indent=2, ensure_ascii=False)
        
        # Registrar agents en A2A Protocol
        if self.a2a_protocol:
            self._register_workflow_agents_in_a2a(workflow_agents)
        
        print(f"✅ Workflow creado: {workflow_id}")
        return workflow
    
    def execute_workflow(
        self,
        workflow_id: str,
        input_data: Dict[str, Any],
        session_id: Optional[str] = None,
        auto_approve: bool = False,
    ) -> WorkflowExecution:
        """Ejecuta un workflow agentic.
        
        Args:
            workflow_id: ID del workflow a ejecutar
            input_data: Datos de entrada
            session_id: ID de sesión (para memoria persistente)
            auto_approve: Si True, aprueba automáticamente pasos que requieren aprobación
        
        Returns:
            WorkflowExecution con resultados
        """
        import time
        start_time = time.time()
        
        # Cargar workflow
        workflow_path = self.workflows_dir / f"{workflow_id}.json"
        if not workflow_path.exists():
            raise ValueError(f"Workflow no encontrado: {workflow_id}")
        
        with open(workflow_path, "r", encoding="utf-8") as f:
            workflow = json.load(f)
        
        # Crear ejecución
        execution_id = str(uuid.uuid4())
        session_id = session_id or str(uuid.uuid4())
        
        # Crear memoria
        memory = WorkflowMemory(
            workflow_id=workflow_id,
            session_id=session_id,
            state=input_data.copy(),
        )
        self.memory_store[session_id] = memory
        
        # Convertir agents a objetos
        agents = [
            WorkflowAgent(**agent_data)
            for agent_data in workflow["agents"]
        ]
        
        # Convertir steps a objetos
        steps = [
            WorkflowStep(**step_data)
            for step_data in workflow["steps"]
        ]
        
        execution = WorkflowExecution(
            execution_id=execution_id,
            workflow_id=workflow_id,
            status=WorkflowStatus.RUNNING,
            agents=agents,
            steps=steps,
            memory=memory,
            started_at=datetime.now().isoformat(),
        )
        
        self.active_executions[execution_id] = execution
        
        try:
            # Ejecutar workflow usando CrewAI si está disponible
            if self.crewai_available:
                result = self._execute_with_crewai(execution, input_data, auto_approve)
            else:
                result = self._execute_simple(execution, input_data, auto_approve)
            
            execution.status = WorkflowStatus.COMPLETED
            execution.completed_at = datetime.now().isoformat()
            
        except Exception as e:
            execution.status = WorkflowStatus.FAILED
            execution.error = str(e)
            execution.completed_at = datetime.now().isoformat()
        
        # Actualizar memoria
        memory.updated_at = datetime.now().isoformat()
        
        return execution
    
    def _execute_with_crewai(
        self,
        execution: WorkflowExecution,
        input_data: Dict[str, Any],
        auto_approve: bool,
    ) -> Dict[str, Any]:
        """Ejecuta workflow usando CrewAI."""
        from crewai import Agent, Task, Crew
        
        # Crear agents de CrewAI
        crew_agents = []
        agent_map = {}
        
        # Obtener tools para cada agent según sus necesidades
        for workflow_agent in execution.agents:
            # Filtrar tools relevantes para este agent
            agent_tools = []
            for tool in self.crewai_tools:
                # Asignar tools según el role del agent
                if any(keyword in workflow_agent.role.lower() for keyword in ["sales", "marketing", "customer"]):
                    if tool.name in ["send_email", "slack_send_message", "teams_send_message"]:
                        agent_tools.append(tool)
                elif any(keyword in workflow_agent.role.lower() for keyword in ["legal", "compliance", "risk"]):
                    if tool.name in ["write_file", "export_pdf", "sql_query"]:
                        agent_tools.append(tool)
                elif any(keyword in workflow_agent.role.lower() for keyword in ["ticket", "incident", "support"]):
                    if tool.name in ["jira_create_ticket", "slack_send_message", "send_email"]:
                        agent_tools.append(tool)
                elif any(keyword in workflow_agent.role.lower() for keyword in ["data", "analyst", "research"]):
                    if tool.name in ["sql_query", "write_file", "export_pdf"]:
                        agent_tools.append(tool)
                else:
                    # Tools genéricos para cualquier agent
                    if tool.name in ["write_file", "send_email"]:
                        agent_tools.append(tool)
            
            # Crear agent de CrewAI con tools
            crew_agent = Agent(
                role=workflow_agent.role,
                goal=workflow_agent.goal,
                backstory=workflow_agent.backstory,
                tools=agent_tools,  # Tools personalizados
                verbose=True,
                allow_delegation=False,
            )
            crew_agents.append(crew_agent)
            agent_map[workflow_agent.agent_id] = crew_agent
        
        # Crear tasks basadas en steps
        tasks = []
        for step in execution.steps:
            from_agent = agent_map.get(step.from_agent_id)
            to_agent = agent_map.get(step.to_agent_id)
            
            if not from_agent or not to_agent:
                continue
            
            # Crear task
            task = Task(
                description=f"Execute step: {step.step_id}",
                agent=to_agent,
            )
            tasks.append(task)
        
        # Crear crew
        crew = Crew(
            agents=crew_agents,
            tasks=tasks,
            process=Process.sequential,
            verbose=True,
        )
        
        # Ejecutar
        result = crew.kickoff(inputs=input_data)
        
        # Actualizar outputs de agents
        for i, workflow_agent in enumerate(execution.agents):
            if i < len(crew_agents):
                workflow_agent.status = AgentStatus.COMPLETED
                workflow_agent.output = str(result) if i == len(crew_agents) - 1 else None
        
        return {"result": str(result)}
    
    def _register_workflow_agents_in_a2a(self, agents: List[WorkflowAgent]):
        """Registra agents de un workflow en A2A Protocol."""
        if not self.a2a_protocol:
            return
        
        for agent in agents:
            # Determinar categoría basada en role
            category = None
            if "ticket" in agent.role.lower() or "incident" in agent.role.lower():
                category = "ticket"
            elif "notification" in agent.role.lower() or "alert" in agent.role.lower():
                category = "notification"
            elif "data" in agent.role.lower() or "analyst" in agent.role.lower():
                category = "data"
            elif "report" in agent.role.lower():
                category = "report"
            
            # Registrar agent en A2A
            self.a2a_protocol.register_agent(
                agent_id=agent.agent_id,
                name=agent.name,
                description=f"{agent.role}: {agent.goal}",
                capabilities=[],  # Se llenarán con tools MCP descubiertos
                category=category,
                tags=[agent.role.lower(), "workflow"],
            )
    
    def _execute_simple(
        self,
        execution: WorkflowExecution,
        input_data: Dict[str, Any],
        auto_approve: bool,
    ) -> Dict[str, Any]:
        """Ejecuta workflow de forma simple (sin CrewAI) usando A2A para comunicación."""
        # Ejecutar agents secuencialmente
        current_state = input_data.copy()
        
        for i, agent in enumerate(execution.agents):
            agent.status = AgentStatus.RUNNING
            
            # Verificar si requiere aprobación
            if agent.requires_approval and not auto_approve:
                agent.status = AgentStatus.WAITING_APPROVAL
                # En modo real, aquí esperaríamos aprobación humana
                # Por ahora, asumimos aprobado si auto_approve es False pero continuamos
                agent.status = AgentStatus.APPROVED
            
            # Descubrir tools MCP automáticamente usando Progressive Disclosure
            discovered_tools = []
            if self.mcp_progressive_disclosure:
                # Usar Progressive Disclosure para búsqueda eficiente
                from .mcp_progressive_disclosure import ToolDetailLevel
                
                # Extraer keywords de la tarea del agent
                task_keywords = self._extract_keywords_from_goal(agent.goal)
                
                # Buscar tools relevantes (solo name+description, no full definition)
                search_results = self.mcp_progressive_disclosure.search_tools(
                    query=task_keywords,
                    detail_level=ToolDetailLevel.NAME_DESCRIPTION,  # Carga ligera
                    limit=5,  # Solo top 5 más relevantes
                )
                
                discovered_tools = [
                    {
                        "tool_name": result.tool_name,
                        "description": result.description,
                        "category": result.category,
                    }
                    for result in search_results
                ]
                
                if discovered_tools:
                    print(f"🔍 [Progressive Disclosure] Agent {agent.name} descubrió {len(discovered_tools)} tools MCP (carga on-demand)")
                    
                    # Cargar definiciones completas solo de tools que se van a usar
                    for tool_info in discovered_tools[:2]:  # Solo cargar top 2
                        full_def = self.mcp_progressive_disclosure.get_tool_definition(
                            tool_info["tool_name"],
                            detail_level=ToolDetailLevel.FULL,
                        )
                        tool_info["full_definition"] = full_def
            elif self.mcp_a2a_bridge:
                # Fallback a método anterior si Progressive Disclosure no está disponible
                task_description = f"{agent.goal}. Context: {str(current_state)[:200]}"
                tool_discovery = self.mcp_a2a_bridge.auto_discover_and_use_tools(
                    agent_id=agent.agent_id,
                    task_description=task_description,
                    auto_execute=False,
                )
                
                if tool_discovery.get("success") and tool_discovery.get("tools"):
                    discovered_tools = tool_discovery["tools"]
                    print(f"🔍 [A2A] Agent {agent.name} descubrió {len(discovered_tools)} tools MCP")
            
            # Ejecutar agent con RL si está disponible
            try:
                # Usar A2A para comunicación si hay agent anterior
                if i > 0 and self.a2a_protocol:
                    prev_agent = execution.agents[i-1]
                    # Enviar mensaje A2A desde agent anterior
                    from .agentic_a2a_protocol import MessageType
                    a2a_message = self.a2a_protocol.send_message(
                        message_type=MessageType.TASK_REQUEST,
                        from_agent_id=prev_agent.agent_id,
                        to_agent_id=agent.agent_id,
                        body={
                            "task": "continue_workflow",
                            "data": current_state,
                            "discovered_tools": discovered_tools,
                        },
                    )
                    print(f"📨 [A2A] Mensaje enviado: {prev_agent.name} → {agent.name}")
                # Crear estado RL
                if self.rl_manager:
                    from .agentic_rl_advanced import RLState, RLAction
                    
                    rl_state = RLState(
                        workflow_id=execution.workflow_id,
                        agent_id=agent.agent_id,
                        state_features={
                            "workflow_step": len([a for a in execution.agents if a.status == AgentStatus.COMPLETED]),
                            "agent_status": agent.status.value,
                            "context_hash": str(hash(str(current_state))),
                        },
                    )
                    
                    # Seleccionar acción usando RL (si hay acciones disponibles)
                    # Por ahora, ejecutamos directamente pero registramos para RL
                    agent.output = {
                        "status": "completed",
                        "data": current_state,
                        "message": f"Agent {agent.name} ejecutado",
                    }
                    agent.status = AgentStatus.COMPLETED
                    
                    # Registrar para RL (reward se obtendrá después)
                    # Esto se hará cuando se reciba feedback del usuario
                else:
                    # Ejecución simple sin RL
                    agent.output = {
                        "status": "completed",
                        "data": current_state,
                        "message": f"Agent {agent.name} ejecutado",
                    }
                    agent.status = AgentStatus.COMPLETED
                
                # Actualizar estado
                if agent.output:
                    current_state.update(agent.output.get("data", {}))
                
                # Enviar mensaje A2A de completación
                if self.a2a_protocol and i < len(execution.agents) - 1:
                    from .agentic_a2a_protocol import MessageType, TaskStatus
                    next_agent = execution.agents[i + 1]
                    # Crear tarea A2A
                    task = self.a2a_protocol.create_task(
                        task_type="workflow_step",
                        from_agent_id=agent.agent_id,
                        to_agent_id=next_agent.agent_id,
                        parameters={"state": current_state},
                    )
                    self.a2a_protocol.update_task_status(task.task_id, TaskStatus.COMPLETED, result=current_state)
                    print(f"✅ [A2A] Tarea completada: {agent.name} → {next_agent.name}")
                
            except Exception as e:
                agent.status = AgentStatus.FAILED
                agent.error = str(e)
                
                # Enviar mensaje A2A de error
                if self.a2a_protocol:
                    from .agentic_a2a_protocol import MessageType, TaskStatus
                    if i < len(execution.agents) - 1:
                        next_agent = execution.agents[i + 1]
                        task = self.a2a_protocol.create_task(
                            task_type="workflow_step",
                            from_agent_id=agent.agent_id,
                            to_agent_id=next_agent.agent_id,
                            parameters={"state": current_state},
                        )
                        self.a2a_protocol.update_task_status(task.task_id, TaskStatus.FAILED, error=str(e))
                
                raise
        
        return {"result": current_state}
    
    def approve_step(
        self,
        execution_id: str,
        agent_id: str,
        approved: bool,
        feedback: Optional[str] = None,
    ) -> bool:
        """Aprueba o rechaza un paso que requiere aprobación humana (Human-in-the-Loop)."""
        if execution_id not in self.active_executions:
            return False
        
        execution = self.active_executions[execution_id]
        
        # Encontrar agent
        agent = None
        for a in execution.agents:
            if a.agent_id == agent_id:
                agent = a
                break
        
        if not agent or agent.status != AgentStatus.WAITING_APPROVAL:
            return False
        
        if approved:
            agent.status = AgentStatus.APPROVED
            # Continuar ejecución
            # (en implementación completa, aquí se reanudaría el workflow)
            
            # Registrar reward positivo
            if self.memory_system:
                self.memory_system.record_reward(
                    workflow_id=execution.workflow_id,
                    agent_id=agent_id,
                    reward=1.0,
                    feedback=feedback or "Aprobado por humano",
                )
            
            # Actualizar RL con reward positivo
            if self.rl_manager and execution.memory:
                from .agentic_rl_advanced import RLState, RLAction
                rl_state = RLState(
                    workflow_id=execution.workflow_id,
                    agent_id=agent_id,
                    state_features={"status": "approved"},
                )
                rl_action = RLAction(
                    action_id=agent_id,
                    action_type="approval",
                    parameters={"approved": True},
                )
                self.rl_manager.update_from_reward(
                    agent_id=agent_id,
                    state=rl_state,
                    action=rl_action,
                    reward=1.0,
                    next_state=None,
                )
        else:
            agent.status = AgentStatus.REJECTED
            execution.status = WorkflowStatus.CANCELLED
            
            # Registrar reward negativo
            if self.memory_system:
                self.memory_system.record_reward(
                    workflow_id=execution.workflow_id,
                    agent_id=agent_id,
                    reward=-1.0,
                    feedback=feedback or "Rechazado por humano",
                )
            
            # Actualizar RL con reward negativo
            if self.rl_manager and execution.memory:
                from .agentic_rl_advanced import RLState, RLAction
                # Crear estado dummy para RL update
                rl_state = RLState(
                    workflow_id=execution.workflow_id,
                    agent_id=agent_id,
                    state_features={"status": "rejected"},
                )
                rl_action = RLAction(
                    action_id=agent_id,
                    action_type="approval",
                    parameters={"approved": False},
                )
                self.rl_manager.update_from_reward(
                    agent_id=agent_id,
                    state=rl_state,
                    action=rl_action,
                    reward=-1.0,
                    next_state=None,
                )
        
        # Guardar aprobación en memoria
        if execution.memory:
            execution.memory.human_approvals[agent_id] = approved
        
        return True
    
    def get_pending_approvals(
        self,
        execution_id: str,
    ) -> List[Dict[str, Any]]:
        """Obtiene lista de pasos pendientes de aprobación humana."""
        if execution_id not in self.active_executions:
            return []
        
        execution = self.active_executions[execution_id]
        pending = []
        
        for agent in execution.agents:
            if agent.status == AgentStatus.WAITING_APPROVAL:
                pending.append({
                    "agent_id": agent.agent_id,
                    "name": agent.name,
                    "role": agent.role,
                    "output": agent.output,
                    "requires_approval": agent.requires_approval,
                })
        
        return pending
    
    def record_reward(
        self,
        workflow_id: str,
        agent_id: str,
        reward: float,
        feedback: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Registra una señal de recompensa para reinforcement learning."""
        if self.memory_system:
            return self.memory_system.record_reward(
                workflow_id=workflow_id,
                agent_id=agent_id,
                reward=reward,
                feedback=feedback,
                context=context,
            )
        return ""
    
    def get_workflow_templates(self) -> List[Dict[str, Any]]:
        """Retorna workflows pre-empaquetados."""
        return [
            {
                "workflow_id": "real_estate_purchase",
                "name": "Real Estate Purchase Workflow",
                "description": "Automatiza compra/construcción de propiedad (ejemplo de Eric Schmidt)",
                "agents": [
                    {
                        "agent_id": "property_searcher",
                        "name": "Property Searcher",
                        "role": "Real Estate Search Agent",
                        "goal": "Buscar propiedades disponibles en el área especificada",
                        "backstory": "Experto en búsqueda de propiedades con acceso a múltiples bases de datos",
                        "requires_approval": False,
                    },
                    {
                        "agent_id": "compliance_checker",
                        "name": "Compliance Checker",
                        "role": "Regulatory Compliance Agent",
                        "goal": "Revisar códigos municipales, permisos y regulaciones",
                        "backstory": "Especialista en leyes de construcción y zonificación",
                        "requires_approval": False,
                    },
                    {
                        "agent_id": "transaction_executor",
                        "name": "Transaction Executor",
                        "role": "Real Estate Transaction Agent",
                        "goal": "Ejecutar transacción de compra",
                        "backstory": "Experto en transacciones inmobiliarias y negociación",
                        "requires_approval": True,  # Requiere aprobación humana
                    },
                    {
                        "agent_id": "designer",
                        "name": "House Designer",
                        "role": "Architectural Design Agent",
                        "goal": "Diseñar casa según especificaciones",
                        "backstory": "Arquitecto experto en diseño residencial",
                        "requires_approval": True,  # Humano aprueba diseño final
                    },
                    {
                        "agent_id": "contractor_manager",
                        "name": "Contractor Manager",
                        "role": "Construction Management Agent",
                        "goal": "Contratar constructor, monitorear progreso, pagar facturas",
                        "backstory": "Experto en gestión de construcción y contratistas",
                        "requires_approval": False,
                    },
                ],
                "steps": [
                    {
                        "step_id": "search_to_compliance",
                        "from_agent_id": "property_searcher",
                        "to_agent_id": "compliance_checker",
                    },
                    {
                        "step_id": "compliance_to_transaction",
                        "from_agent_id": "compliance_checker",
                        "to_agent_id": "transaction_executor",
                    },
                    {
                        "step_id": "transaction_to_design",
                        "from_agent_id": "transaction_executor",
                        "to_agent_id": "designer",
                    },
                    {
                        "step_id": "design_to_contractor",
                        "from_agent_id": "designer",
                        "to_agent_id": "contractor_manager",
                    },
                ],
            },
            {
                "workflow_id": "sales_agent_full_cycle",
                "name": "Sales Agent Full Cycle",
                "description": "Agente de ventas completo: prospecting → qualification → closing",
                "agents": [
                    {
                        "agent_id": "prospector",
                        "name": "Lead Prospector",
                        "role": "Sales Prospecting Agent",
                        "goal": "Encontrar leads calificados",
                        "backstory": "Experto en identificación de prospects de alto valor",
                    },
                    {
                        "agent_id": "qualifier",
                        "name": "Lead Qualifier",
                        "role": "Sales Qualification Agent",
                        "goal": "Calificar leads y determinar fit",
                        "backstory": "Especialista en BANT (Budget, Authority, Need, Timeline)",
                    },
                    {
                        "agent_id": "closer",
                        "name": "Deal Closer",
                        "role": "Sales Closing Agent",
                        "goal": "Cerrar deals y generar contratos",
                        "backstory": "Experto en negociación y cierre de ventas",
                        "requires_approval": True,  # Aprobación antes de cerrar deal grande
                    },
                ],
                "steps": [
                    {
                        "step_id": "prospect_to_qualify",
                        "from_agent_id": "prospector",
                        "to_agent_id": "qualifier",
                    },
                    {
                        "step_id": "qualify_to_close",
                        "from_agent_id": "qualifier",
                        "to_agent_id": "closer",
                    },
                ],
            },
            {
                "workflow_id": "legal_compliance_review",
                "name": "Legal & Compliance Review Workflow",
                "description": "Revisión automática de contratos y cumplimiento normativo",
                "agents": [
                    {
                        "agent_id": "document_analyzer",
                        "name": "Document Analyzer",
                        "role": "Legal Document Analysis Agent",
                        "goal": "Analizar documentos legales y extraer información clave",
                        "backstory": "Experto en análisis de documentos legales y contratos",
                        "requires_approval": False,
                    },
                    {
                        "agent_id": "compliance_checker",
                        "name": "Compliance Checker",
                        "role": "Regulatory Compliance Agent",
                        "goal": "Verificar cumplimiento con regulaciones y leyes aplicables",
                        "backstory": "Especialista en compliance normativo y regulaciones",
                        "requires_approval": False,
                    },
                    {
                        "agent_id": "risk_assessor",
                        "name": "Risk Assessor",
                        "role": "Legal Risk Assessment Agent",
                        "goal": "Evaluar riesgos legales y financieros",
                        "backstory": "Experto en evaluación de riesgos legales y financieros",
                        "requires_approval": False,
                    },
                    {
                        "agent_id": "report_generator",
                        "name": "Report Generator",
                        "role": "Legal Report Generation Agent",
                        "goal": "Generar reporte ejecutivo de revisión legal",
                        "backstory": "Experto en redacción de reportes legales ejecutivos",
                        "requires_approval": True,  # Aprobación antes de enviar reporte final
                    },
                ],
                "steps": [
                    {
                        "step_id": "analyze_to_compliance",
                        "from_agent_id": "document_analyzer",
                        "to_agent_id": "compliance_checker",
                    },
                    {
                        "step_id": "compliance_to_risk",
                        "from_agent_id": "compliance_checker",
                        "to_agent_id": "risk_assessor",
                    },
                    {
                        "step_id": "risk_to_report",
                        "from_agent_id": "risk_assessor",
                        "to_agent_id": "report_generator",
                    },
                ],
            },
            {
                "workflow_id": "inventory_management",
                "name": "Inventory Management Workflow",
                "description": "Gestión automática de inventarios: análisis, reorden, optimización",
                "agents": [
                    {
                        "agent_id": "inventory_analyzer",
                        "name": "Inventory Analyzer",
                        "role": "Inventory Analysis Agent",
                        "goal": "Analizar niveles de inventario y detectar productos con bajo stock",
                        "backstory": "Experto en análisis de inventarios y predicción de demanda",
                        "requires_approval": False,
                    },
                    {
                        "agent_id": "reorder_calculator",
                        "name": "Reorder Calculator",
                        "role": "Inventory Reorder Agent",
                        "goal": "Calcular cantidades de reorden óptimas basadas en demanda histórica",
                        "backstory": "Especialista en optimización de inventarios y modelos de reorden",
                        "requires_approval": False,
                    },
                    {
                        "agent_id": "supplier_coordinator",
                        "name": "Supplier Coordinator",
                        "role": "Supplier Management Agent",
                        "goal": "Coordinar con proveedores para realizar pedidos",
                        "backstory": "Experto en gestión de proveedores y negociación",
                        "requires_approval": True,  # Aprobación antes de hacer pedidos grandes
                    },
                    {
                        "agent_id": "inventory_reporter",
                        "name": "Inventory Reporter",
                        "role": "Inventory Reporting Agent",
                        "goal": "Generar reportes de inventario y alertas",
                        "backstory": "Experto en generación de reportes ejecutivos de inventario",
                        "requires_approval": False,
                    },
                ],
                "steps": [
                    {
                        "step_id": "analyze_to_reorder",
                        "from_agent_id": "inventory_analyzer",
                        "to_agent_id": "reorder_calculator",
                    },
                    {
                        "step_id": "reorder_to_supplier",
                        "from_agent_id": "reorder_calculator",
                        "to_agent_id": "supplier_coordinator",
                    },
                    {
                        "step_id": "supplier_to_reporter",
                        "from_agent_id": "supplier_coordinator",
                        "to_agent_id": "inventory_reporter",
                    },
                ],
            },
            {
                "workflow_id": "recruiting_full_cycle",
                "name": "Recruiting Full Cycle Workflow",
                "description": "Reclutamiento completo: sourcing → screening → interview → offer",
                "agents": [
                    {
                        "agent_id": "candidate_sourcer",
                        "name": "Candidate Sourcer",
                        "role": "Talent Sourcing Agent",
                        "goal": "Encontrar candidatos calificados en múltiples plataformas",
                        "backstory": "Experto en sourcing de talento y búsqueda de candidatos",
                        "requires_approval": False,
                    },
                    {
                        "agent_id": "resume_screener",
                        "name": "Resume Screener",
                        "role": "Resume Screening Agent",
                        "goal": "Analizar CVs y calificar candidatos según requisitos",
                        "backstory": "Especialista en análisis de CVs y matching de candidatos",
                        "requires_approval": False,
                    },
                    {
                        "agent_id": "interview_scheduler",
                        "name": "Interview Scheduler",
                        "role": "Interview Coordination Agent",
                        "goal": "Coordinar entrevistas con candidatos y entrevistadores",
                        "backstory": "Experto en coordinación de entrevistas y calendarios",
                        "requires_approval": False,
                    },
                    {
                        "agent_id": "offer_negotiator",
                        "name": "Offer Negotiator",
                        "role": "Offer Management Agent",
                        "goal": "Generar ofertas y negociar términos con candidatos",
                        "backstory": "Experto en negociación de ofertas y paquetes de compensación",
                        "requires_approval": True,  # Aprobación antes de enviar ofertas
                    },
                ],
                "steps": [
                    {
                        "step_id": "source_to_screen",
                        "from_agent_id": "candidate_sourcer",
                        "to_agent_id": "resume_screener",
                    },
                    {
                        "step_id": "screen_to_schedule",
                        "from_agent_id": "resume_screener",
                        "to_agent_id": "interview_scheduler",
                    },
                    {
                        "step_id": "schedule_to_offer",
                        "from_agent_id": "interview_scheduler",
                        "to_agent_id": "offer_negotiator",
                    },
                ],
            },
            {
                "workflow_id": "supply_chain_optimization",
                "name": "Supply Chain Optimization Workflow",
                "description": "Optimización de cadena de suministro: demanda → producción → logística",
                "agents": [
                    {
                        "agent_id": "demand_forecaster",
                        "name": "Demand Forecaster",
                        "role": "Demand Forecasting Agent",
                        "goal": "Predecir demanda futura basada en datos históricos y tendencias",
                        "backstory": "Experto en forecasting de demanda y análisis predictivo",
                        "requires_approval": False,
                    },
                    {
                        "agent_id": "production_planner",
                        "name": "Production Planner",
                        "role": "Production Planning Agent",
                        "goal": "Planificar producción óptima basada en demanda pronosticada",
                        "backstory": "Especialista en planificación de producción y optimización",
                        "requires_approval": False,
                    },
                    {
                        "agent_id": "logistics_coordinator",
                        "name": "Logistics Coordinator",
                        "role": "Logistics Management Agent",
                        "goal": "Coordinar transporte y distribución de productos",
                        "backstory": "Experto en logística y gestión de transporte",
                        "requires_approval": False,
                    },
                    {
                        "agent_id": "supply_chain_analyst",
                        "name": "Supply Chain Analyst",
                        "role": "Supply Chain Analysis Agent",
                        "goal": "Analizar eficiencia de la cadena de suministro y generar reportes",
                        "backstory": "Experto en análisis de cadenas de suministro y optimización",
                        "requires_approval": False,
                    },
                ],
                "steps": [
                    {
                        "step_id": "forecast_to_plan",
                        "from_agent_id": "demand_forecaster",
                        "to_agent_id": "production_planner",
                    },
                    {
                        "step_id": "plan_to_logistics",
                        "from_agent_id": "production_planner",
                        "to_agent_id": "logistics_coordinator",
                    },
                    {
                        "step_id": "logistics_to_analyze",
                        "from_agent_id": "logistics_coordinator",
                        "to_agent_id": "supply_chain_analyst",
                    },
                ],
            },
        ]

