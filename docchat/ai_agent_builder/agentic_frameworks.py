"""
Agentic Frameworks Orchestrators
Orquestadores para LangGraph, CrewAI, AG2, y BAI Framework
Basado en: Agentic AI with Langgraph, Crew AI, AG2, and BAI Framework
"""

from __future__ import annotations

from typing import Dict, Any, List, Optional
from dataclasses import dataclass

try:
    from langgraph.graph import StateGraph, END
    from langgraph.graph.message import add_messages
    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False
    print("⚠️ LangGraph no disponible. Instala con: pip install langgraph")

try:
    from crewai import Agent, Task, Crew
    CREWAI_AVAILABLE = True
except ImportError:
    CREWAI_AVAILABLE = False
    print("⚠️ CrewAI no disponible. Instala con: pip install crewai")


@dataclass
class WorkflowState:
    """Estado para workflows de LangGraph"""
    messages: List[Any] = None
    context: Dict[str, Any] = None
    next_action: Optional[str] = None


class LangGraphOrchestrator:
    """
    Orquestador para LangGraph
    Crea workflows stateful con agentes y React agents
    """
    
    def __init__(self, config: Any):
        self.config = config
        self.graphs: Dict[str, Any] = {}
    
    def create_workflow(
        self,
        workflow_id: str,
        nodes: Dict[str, Any],
        edges: List[Dict[str, str]],
        initial_state: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Crea un workflow de LangGraph
        
        Args:
            workflow_id: ID del workflow
            nodes: Dict de nodos {node_name: node_function}
            edges: Lista de edges [{"from": "node1", "to": "node2"}]
            initial_state: Estado inicial
            
        Returns:
            workflow_id
        """
        if not LANGGRAPH_AVAILABLE:
            raise ImportError("LangGraph requerido")
        
        # Crear grafo
        workflow = StateGraph(WorkflowState)
        
        # Agregar nodos
        for node_name, node_func in nodes.items():
            workflow.add_node(node_name, node_func)
        
        # Agregar edges
        workflow.set_entry_point(edges[0]["from"] if edges else list(nodes.keys())[0])
        
        for edge in edges:
            if edge.get("condition"):
                workflow.add_conditional_edges(
                    edge["from"],
                    edge["condition"],
                    {edge["to"]: edge["to"]}
                )
            else:
                workflow.add_edge(edge["from"], edge["to"])
        
        # Agregar edge final
        last_node = edges[-1]["to"] if edges else list(nodes.keys())[-1]
        workflow.add_edge(last_node, END)
        
        # Compilar
        app = workflow.compile()
        self.graphs[workflow_id] = app
        
        return workflow_id
    
    def execute_workflow(self, workflow_id: str, input_data: Dict[str, Any]) -> Any:
        """Ejecuta un workflow"""
        if workflow_id not in self.graphs:
            raise ValueError(f"Workflow {workflow_id} no encontrado")
        
        app = self.graphs[workflow_id]
        return app.invoke(input_data)


class CrewAIOrchestrator:
    """
    Orquestador para CrewAI
    Crea sistemas multi-agente con roles y tareas
    """
    
    def __init__(self, config: Any):
        self.config = config
        self.crews: Dict[str, Any] = {}
    
    def create_crew(
        self,
        crew_id: str,
        agents: List[Dict[str, Any]],
        tasks: List[Dict[str, Any]],
        process: str = "sequential"
    ) -> str:
        """
        Crea un crew de CrewAI
        
        Args:
            crew_id: ID del crew
            agents: Lista de agentes [{"role": "...", "goal": "...", "backstory": "..."}]
            tasks: Lista de tareas [{"description": "...", "agent": "agent_name"}]
            process: "sequential" o "hierarchical"
        """
        if not CREWAI_AVAILABLE:
            raise ImportError("CrewAI requerido")
        
        # Crear agentes
        crew_agents = []
        for agent_def in agents:
            agent = Agent(
                role=agent_def["role"],
                goal=agent_def["goal"],
                backstory=agent_def.get("backstory", ""),
                verbose=agent_def.get("verbose", True),
                allow_delegation=agent_def.get("allow_delegation", False)
            )
            crew_agents.append(agent)
        
        # Crear tareas
        crew_tasks = []
        agent_map = {agent_def["role"]: agent for agent_def, agent in zip(agents, crew_agents)}
        
        for task_def in tasks:
            task = Task(
                description=task_def["description"],
                agent=agent_map.get(task_def.get("agent", agents[0]["role"])),
                expected_output=task_def.get("expected_output", "")
            )
            crew_tasks.append(task)
        
        # Crear crew
        crew = Crew(
            agents=crew_agents,
            tasks=crew_tasks,
            process=process,
            verbose=True
        )
        
        self.crews[crew_id] = crew
        return crew_id
    
    def execute_crew(self, crew_id: str, inputs: Optional[Dict[str, Any]] = None) -> Any:
        """Ejecuta un crew"""
        if crew_id not in self.crews:
            raise ValueError(f"Crew {crew_id} no encontrado")
        
        crew = self.crews[crew_id]
        return crew.kickoff(inputs=inputs)


class AG2Orchestrator:
    """
    Orquestador para AG2 (Autogen)
    Implementación futura
    """
    
    def __init__(self, config: Any):
        self.config = config
    
    def create_multi_agent_system(self, config: Dict[str, Any]) -> str:
        """Crea sistema multi-agente con AG2"""
        # Implementación futura
        raise NotImplementedError("AG2 será implementado próximamente")


class BAIOrchestrator:
    """
    Orquestador para IBM BAI Framework
    Implementación futura
    """
    
    def __init__(self, config: Any):
        self.config = config
    
    def create_agentic_system(self, config: Dict[str, Any]) -> str:
        """Crea sistema agentic con BAI Framework"""
        # Implementación futura
        raise NotImplementedError("BAI Framework será implementado próximamente")
