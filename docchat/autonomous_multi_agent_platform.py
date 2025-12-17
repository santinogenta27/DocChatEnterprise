"""
Enterprise Autonomous Multi-Agent Workflow Platform
Plataforma que combina todos los patrones avanzados de Agentic AI:
- Orchestrator-Worker Pattern (LangGraph)
- Reflection Pattern (iterative improvement)
- Routing Pattern (intelligent task routing)
- Parallelization (multiple agents simultaneously)
- HandoffTool coordination (AG2/BeeAI style)
- Requirements-based control (BeeAI style)
- Human-in-the-loop (production security)
"""

from __future__ import annotations

import json
import uuid
import asyncio
from typing import Dict, Any, List, Optional, TypedDict, Annotated, Literal
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from enum import Enum
import operator

try:
    from langgraph.graph import StateGraph, END, START
    from langgraph.types import Send
    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False
    print("⚠️ LangGraph no disponible. Instala con: pip install langgraph")

try:
    from crewai import Agent, Task, Crew, Process
    CREWAI_AVAILABLE = True
except ImportError:
    CREWAI_AVAILABLE = False
    print("⚠️ CrewAI no disponible. Instala con: pip install crewai")

try:
    from autogen import ConversableAgent, GroupChat, GroupChatManager
    AG2_AVAILABLE = True
except ImportError:
    AG2_AVAILABLE = False
    print("⚠️ AG2 (AutoGen) no disponible. Instala con: pip install ag2[openai]")

from .config import AppConfig
from .ai_agent_builder.rag_engine import AdvancedRAGEngine
from .ai_agent_builder.multimodal_processor import MultimodalProcessor
from .ai_agent_builder.agentic_frameworks import LangGraphOrchestrator, CrewAIOrchestrator


class WorkflowPattern(str, Enum):
    """Patrones de workflow disponibles"""
    SEQUENTIAL = "sequential"  # Prompt Chaining
    ROUTING = "routing"  # Intent-based routing
    PARALLEL = "parallel"  # Parallel execution
    ORCHESTRATOR_WORKER = "orchestrator_worker"  # LangGraph pattern
    REFLECTION = "reflection"  # Iterative improvement
    MULTI_AGENT = "multi_agent"  # CrewAI/AG2 coordination


class AgentRole(str, Enum):
    """Roles de agentes especializados"""
    ORCHESTRATOR = "orchestrator"
    WORKER = "worker"
    ROUTER = "router"
    EVALUATOR = "evaluator"
    GENERATOR = "generator"
    RESEARCHER = "researcher"
    ANALYZER = "analyzer"
    SYNTHESIZER = "synthesizer"
    DECISION_MAKER = "decision_maker"


@dataclass
class MultiAgentState(TypedDict):
    """Estado compartido para workflows multi-agente"""
    user_input: str
    workflow_id: str
    current_step: int
    task_type: str
    agent_outputs: Annotated[Dict[str, Any], operator.add]  # Agregación automática
    context: Dict[str, Any]
    decisions: List[Dict[str, Any]]
    final_output: str
    iteration_count: int
    optimization_data: Dict[str, Any]


@dataclass
class WorkflowAgent:
    """Definición de un agente en el workflow"""
    agent_id: str
    name: str
    role: AgentRole
    goal: str
    backstory: str
    tools: List[str] = field(default_factory=list)
    system_prompt: str = ""
    requires_approval: bool = False
    max_iterations: int = 3


@dataclass
class WorkflowNode:
    """Nodo en el workflow"""
    node_id: str
    node_type: str  # "agent", "router", "parallel", "reflection", "orchestrator"
    agent_id: Optional[str] = None
    condition: Optional[str] = None
    parallel_agents: List[str] = field(default_factory=list)


@dataclass
class WorkflowEdge:
    """Conexión entre nodos"""
    from_node: str
    to_node: str
    condition: Optional[str] = None


@dataclass
class WorkflowTemplate:
    """Template pre-construido de workflow"""
    template_id: str
    name: str
    description: str
    pattern: WorkflowPattern
    agents: List[WorkflowAgent]
    nodes: List[WorkflowNode]
    edges: List[WorkflowEdge]
    use_cases: List[str] = field(default_factory=list)


class AutonomousMultiAgentWorkflowPlatform:
    """
    Plataforma Enterprise de Workflows Multi-Agente Autónomos
    
    Combina todos los patrones avanzados:
    - Orchestrator-Worker (LangGraph)
    - Reflection (iterative improvement)
    - Routing (intelligent task routing)
    - Parallelization (multiple agents simultaneously)
    - HandoffTool coordination (AG2/BeeAI style)
    - Requirements-based control (BeeAI style)
    - Human-in-the-loop (production security)
    """
    
    def __init__(self, config: AppConfig):
        self.config = config
        self.workflows: Dict[str, Any] = {}
        self.agents: Dict[str, WorkflowAgent] = {}
        self.templates: Dict[str, WorkflowTemplate] = {}
        
        # Inicializar componentes
        try:
            from .ai_agent_builder.rag_engine import AdvancedRAGEngine
            from .ai_agent_builder.multimodal_processor import MultimodalProcessor
            from .ai_agent_builder.agentic_frameworks import LangGraphOrchestrator, CrewAIOrchestrator
            
            self.rag_engine = AdvancedRAGEngine(config)
            self.multimodal_processor = MultimodalProcessor(config)
            self.langgraph_orchestrator = LangGraphOrchestrator(config) if LANGGRAPH_AVAILABLE else None
            self.crewai_orchestrator = CrewAIOrchestrator(config) if CREWAI_AVAILABLE else None
        except Exception as e:
            print(f"⚠️ Error inicializando componentes: {e}")
            self.rag_engine = None
            self.multimodal_processor = None
            self.langgraph_orchestrator = None
            self.crewai_orchestrator = None
        
        # Cargar templates
        self._load_workflow_templates()
        
        print("✅ Enterprise Autonomous Multi-Agent Workflow Platform inicializado")
    
    def _load_workflow_templates(self):
        """Carga templates pre-construidos de workflows"""
        # Customer Support Automation
        self.templates["customer_support"] = WorkflowTemplate(
            template_id="customer_support",
            name="Customer Support Automation",
            description="Multi-agente que analiza tickets, busca en KB, genera respuestas y escala a humano",
            pattern=WorkflowPattern.ORCHESTRATOR_WORKER,
            agents=[
                WorkflowAgent(
                    agent_id="analyst",
                    name="Ticket Analyst",
                    role=AgentRole.ANALYZER,
                    goal="Analizar tickets de soporte y clasificar urgencia",
                    backstory="Experto en análisis de tickets y clasificación de prioridades"
                ),
                WorkflowAgent(
                    agent_id="rag_researcher",
                    name="Knowledge Base Researcher",
                    role=AgentRole.RESEARCHER,
                    goal="Buscar información relevante en la base de conocimiento",
                    backstory="Especialista en búsqueda semántica y recuperación de información"
                ),
                WorkflowAgent(
                    agent_id="response_generator",
                    name="Response Generator",
                    role=AgentRole.GENERATOR,
                    goal="Generar respuestas personalizadas basadas en análisis y conocimiento",
                    backstory="Experto en redacción de respuestas de soporte claras y útiles"
                ),
                WorkflowAgent(
                    agent_id="decision_maker",
                    name="Escalation Decision Maker",
                    role=AgentRole.DECISION_MAKER,
                    goal="Decidir si escalar a humano o responder automáticamente",
                    backstory="Experto en evaluación de complejidad y necesidad de intervención humana"
                )
            ],
            nodes=[
                WorkflowNode(node_id="start", node_type="start"),
                WorkflowNode(node_id="router", node_type="router"),
                WorkflowNode(node_id="analyst", node_type="agent", agent_id="analyst"),
                WorkflowNode(node_id="rag_researcher", node_type="agent", agent_id="rag_researcher"),
                WorkflowNode(node_id="response_generator", node_type="agent", agent_id="response_generator"),
                WorkflowNode(node_id="decision_maker", node_type="agent", agent_id="decision_maker"),
                WorkflowNode(node_id="end", node_type="end")
            ],
            edges=[
                WorkflowEdge("start", "router"),
                WorkflowEdge("router", "analyst"),
                WorkflowEdge("analyst", "rag_researcher"),
                WorkflowEdge("rag_researcher", "response_generator"),
                WorkflowEdge("response_generator", "decision_maker"),
                WorkflowEdge("decision_maker", "end")
            ],
            use_cases=["Customer Support", "Help Desk", "Ticket Management"]
        )
        
        # Content Creation Pipeline
        self.templates["content_creation"] = WorkflowTemplate(
            template_id="content_creation",
            name="Content Creation Pipeline",
            description="Multi-agente que investiga, genera contenido, crea imágenes y optimiza SEO",
            pattern=WorkflowPattern.PARALLEL,
            agents=[
                WorkflowAgent(
                    agent_id="researcher",
                    name="Content Researcher",
                    role=AgentRole.RESEARCHER,
                    goal="Investigar temas y recopilar información relevante",
                    backstory="Experto en investigación de contenido y tendencias"
                ),
                WorkflowAgent(
                    agent_id="writer",
                    name="Content Writer",
                    role=AgentRole.GENERATOR,
                    goal="Generar contenido escrito de alta calidad",
                    backstory="Escritor profesional especializado en contenido digital"
                ),
                WorkflowAgent(
                    agent_id="image_creator",
                    name="Image Creator",
                    role=AgentRole.GENERATOR,
                    goal="Crear imágenes complementarias usando DALL-E",
                    backstory="Diseñador gráfico especializado en generación de imágenes con IA"
                ),
                WorkflowAgent(
                    agent_id="seo_optimizer",
                    name="SEO Optimizer",
                    role=AgentRole.ANALYZER,
                    goal="Optimizar contenido para SEO",
                    backstory="Especialista en SEO y optimización de contenido"
                )
            ],
            nodes=[
                WorkflowNode(node_id="start", node_type="start"),
                WorkflowNode(node_id="researcher", node_type="agent", agent_id="researcher"),
                WorkflowNode(node_id="writer", node_type="agent", agent_id="writer"),
                WorkflowNode(node_id="image_creator", node_type="agent", agent_id="image_creator"),
                WorkflowNode(node_id="seo_optimizer", node_type="agent", agent_id="seo_optimizer"),
                WorkflowNode(node_id="synthesizer", node_type="agent", agent_id="synthesizer"),
                WorkflowNode(node_id="end", node_type="end")
            ],
            edges=[
                WorkflowEdge("start", "researcher"),
                WorkflowEdge("researcher", "writer"),
                WorkflowEdge("researcher", "image_creator"),
                WorkflowEdge("writer", "seo_optimizer"),
                WorkflowEdge("image_creator", "synthesizer"),
                WorkflowEdge("seo_optimizer", "synthesizer"),
                WorkflowEdge("synthesizer", "end")
            ],
            use_cases=["Content Marketing", "Blog Writing", "Social Media Content"]
        )
        
        # Data Analysis & Reporting
        self.templates["data_analysis"] = WorkflowTemplate(
            template_id="data_analysis",
            name="Data Analysis & Reporting",
            description="Multi-agente que extrae datos, analiza patrones, genera reportes e identifica insights",
            pattern=WorkflowPattern.ORCHESTRATOR_WORKER,
            agents=[
                WorkflowAgent(
                    agent_id="data_extractor",
                    name="Data Extractor",
                    role=AgentRole.RESEARCHER,
                    goal="Extraer datos relevantes de fuentes diversas",
                    backstory="Especialista en extracción y limpieza de datos"
                ),
                WorkflowAgent(
                    agent_id="pattern_analyst",
                    name="Pattern Analyst",
                    role=AgentRole.ANALYZER,
                    goal="Analizar patrones y tendencias en los datos",
                    backstory="Analista de datos experto en identificación de patrones"
                ),
                WorkflowAgent(
                    agent_id="report_generator",
                    name="Report Generator",
                    role=AgentRole.GENERATOR,
                    goal="Generar reportes estructurados y visualizaciones",
                    backstory="Especialista en generación de reportes ejecutivos"
                ),
                WorkflowAgent(
                    agent_id="insights_identifier",
                    name="Insights Identifier",
                    role=AgentRole.ANALYZER,
                    goal="Identificar insights accionables",
                    backstory="Estratega de datos especializado en insights de negocio"
                )
            ],
            nodes=[
                WorkflowNode(node_id="start", node_type="start"),
                WorkflowNode(node_id="data_extractor", node_type="agent", agent_id="data_extractor"),
                WorkflowNode(node_id="pattern_analyst", node_type="agent", agent_id="pattern_analyst"),
                WorkflowNode(node_id="report_generator", node_type="agent", agent_id="report_generator"),
                WorkflowNode(node_id="insights_identifier", node_type="agent", agent_id="insights_identifier"),
                WorkflowNode(node_id="end", node_type="end")
            ],
            edges=[
                WorkflowEdge("start", "data_extractor"),
                WorkflowEdge("data_extractor", "pattern_analyst"),
                WorkflowEdge("pattern_analyst", "report_generator"),
                WorkflowEdge("pattern_analyst", "insights_identifier"),
                WorkflowEdge("report_generator", "end"),
                WorkflowEdge("insights_identifier", "end")
            ],
            use_cases=["Business Intelligence", "Data Analytics", "Executive Reporting"]
        )
        
        # Sales & Marketing Automation
        self.templates["sales_marketing"] = WorkflowTemplate(
            template_id="sales_marketing",
            name="Sales & Marketing Automation",
            description="Multi-agente que identifica leads, personaliza outreach, programa follow-ups y analiza conversiones",
            pattern=WorkflowPattern.ROUTING,
            agents=[
                WorkflowAgent(
                    agent_id="lead_finder",
                    name="Lead Finder",
                    role=AgentRole.RESEARCHER,
                    goal="Identificar leads potenciales",
                    backstory="Especialista en prospección y generación de leads"
                ),
                WorkflowAgent(
                    agent_id="personalizer",
                    name="Outreach Personalizer",
                    role=AgentRole.GENERATOR,
                    goal="Personalizar mensajes de outreach",
                    backstory="Especialista en personalización de mensajes de ventas"
                ),
                WorkflowAgent(
                    agent_id="scheduler",
                    name="Follow-up Scheduler",
                    role=AgentRole.DECISION_MAKER,
                    goal="Programar y gestionar follow-ups",
                    backstory="Coordinador de secuencias de seguimiento"
                ),
                WorkflowAgent(
                    agent_id="conversion_analyst",
                    name="Conversion Analyst",
                    role=AgentRole.ANALYZER,
                    goal="Analizar conversiones y optimizar estrategias",
                    backstory="Analista de conversión y optimización de ventas"
                )
            ],
            nodes=[
                WorkflowNode(node_id="start", node_type="start"),
                WorkflowNode(node_id="router", node_type="router"),
                WorkflowNode(node_id="lead_finder", node_type="agent", agent_id="lead_finder"),
                WorkflowNode(node_id="personalizer", node_type="agent", agent_id="personalizer"),
                WorkflowNode(node_id="scheduler", node_type="agent", agent_id="scheduler"),
                WorkflowNode(node_id="conversion_analyst", node_type="agent", agent_id="conversion_analyst"),
                WorkflowNode(node_id="end", node_type="end")
            ],
            edges=[
                WorkflowEdge("start", "router"),
                WorkflowEdge("router", "lead_finder"),
                WorkflowEdge("lead_finder", "personalizer"),
                WorkflowEdge("personalizer", "scheduler"),
                WorkflowEdge("scheduler", "conversion_analyst"),
                WorkflowEdge("conversion_analyst", "end")
            ],
            use_cases=["Sales Automation", "Marketing Campaigns", "Lead Generation"]
        )
        
        # Compliance & Risk Management
        self.templates["compliance_risk"] = WorkflowTemplate(
            template_id="compliance_risk",
            name="Compliance & Risk Management",
            description="Multi-agente que monitorea transacciones, detecta anomalías, genera reportes y alerta riesgos",
            pattern=WorkflowPattern.REFLECTION,
            agents=[
                WorkflowAgent(
                    agent_id="monitor",
                    name="Transaction Monitor",
                    role=AgentRole.ANALYZER,
                    goal="Monitorear transacciones en tiempo real",
                    backstory="Especialista en monitoreo de transacciones financieras"
                ),
                WorkflowAgent(
                    agent_id="anomaly_detector",
                    name="Anomaly Detector",
                    role=AgentRole.ANALYZER,
                    goal="Detectar anomalías y patrones sospechosos",
                    backstory="Experto en detección de fraudes y anomalías"
                ),
                WorkflowAgent(
                    agent_id="risk_evaluator",
                    name="Risk Evaluator",
                    role=AgentRole.EVALUATOR,
                    goal="Evaluar nivel de riesgo y generar feedback",
                    backstory="Evaluador de riesgo con experiencia en compliance"
                ),
                WorkflowAgent(
                    agent_id="report_generator",
                    name="Compliance Reporter",
                    role=AgentRole.GENERATOR,
                    goal="Generar reportes de compliance",
                    backstory="Especialista en reportes regulatorios"
                ),
                WorkflowAgent(
                    agent_id="alert_manager",
                    name="Alert Manager",
                    role=AgentRole.DECISION_MAKER,
                    goal="Gestionar alertas de riesgo",
                    backstory="Gestor de alertas y notificaciones de riesgo"
                )
            ],
            nodes=[
                WorkflowNode(node_id="start", node_type="start"),
                WorkflowNode(node_id="monitor", node_type="agent", agent_id="monitor"),
                WorkflowNode(node_id="anomaly_detector", node_type="agent", agent_id="anomaly_detector"),
                WorkflowNode(node_id="risk_evaluator", node_type="agent", agent_id="risk_evaluator"),
                WorkflowNode(node_id="report_generator", node_type="agent", agent_id="report_generator"),
                WorkflowNode(node_id="alert_manager", node_type="agent", agent_id="alert_manager"),
                WorkflowNode(node_id="end", node_type="end")
            ],
            edges=[
                WorkflowEdge("start", "monitor"),
                WorkflowEdge("monitor", "anomaly_detector"),
                WorkflowEdge("anomaly_detector", "risk_evaluator"),
                WorkflowEdge("risk_evaluator", "report_generator"),
                WorkflowEdge("risk_evaluator", "alert_manager"),
                WorkflowEdge("report_generator", "end"),
                WorkflowEdge("alert_manager", "end")
            ],
            use_cases=["Banking", "Fintech", "Compliance", "Risk Management"]
        )
    
    def create_workflow_from_template(
        self,
        template_id: str,
        workflow_name: str,
        customizations: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Crea un workflow desde un template
        
        Args:
            template_id: ID del template
            workflow_name: Nombre del workflow
            customizations: Personalizaciones opcionales
            
        Returns:
            workflow_id
        """
        if template_id not in self.templates:
            raise ValueError(f"Template {template_id} no encontrado")
        
        template = self.templates[template_id]
        workflow_id = f"workflow_{uuid.uuid4().hex[:8]}"
        
        # Construir workflow según el patrón
        if template.pattern == WorkflowPattern.ORCHESTRATOR_WORKER:
            workflow = self._build_orchestrator_worker_workflow(workflow_id, workflow_name, template)
        elif template.pattern == WorkflowPattern.REFLECTION:
            workflow = self._build_reflection_workflow(workflow_id, workflow_name, template)
        elif template.pattern == WorkflowPattern.ROUTING:
            workflow = self._build_routing_workflow(workflow_id, workflow_name, template)
        elif template.pattern == WorkflowPattern.PARALLEL:
            workflow = self._build_parallel_workflow(workflow_id, workflow_name, template)
        else:
            workflow = self._build_sequential_workflow(workflow_id, workflow_name, template)
        
        self.workflows[workflow_id] = {
            "workflow_id": workflow_id,
            "name": workflow_name,
            "template_id": template_id,
            "pattern": template.pattern.value,
            "workflow": workflow,
            "created_at": datetime.now().isoformat()
        }
        
        return workflow_id
    
    def _build_orchestrator_worker_workflow(
        self,
        workflow_id: str,
        workflow_name: str,
        template: WorkflowTemplate
    ) -> Any:
        """Construye workflow Orchestrator-Worker usando LangGraph - SIGUIENDO EXACTAMENTE EL LAB"""
        if not LANGGRAPH_AVAILABLE:
            raise ImportError("LangGraph requerido para Orchestrator-Worker pattern")
        
        from langgraph.graph import StateGraph, END, START
        from langgraph.types import Send
        from langchain_openai import ChatOpenAI
        from langchain_core.prompts import ChatPromptTemplate
        from pydantic import BaseModel, Field
        
        # Definir estado siguiendo el patrón del lab
        class OrchestratorState(TypedDict):
            user_input: str
            sections: List[Dict[str, Any]]
            completed_outputs: Annotated[List[str], operator.add]
            final_output: str
        
        # Inicializar LLM
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.7)
        
        # Nodo orchestrator - SIGUIENDO EL LAB EXACTO
        def orchestrator_node(state: OrchestratorState) -> Dict[str, Any]:
            """Orchestrator que descompone la tarea en secciones estructuradas"""
            # Prompt para descomponer la tarea
            orchestrator_prompt = ChatPromptTemplate.from_messages([
                ("system", 
                 "Eres un orquestador experto que descompone tareas complejas en subtareas estructuradas.\n"
                 "Analiza la tarea del usuario y descomponla en secciones claras y manejables."),
                ("human", "Tarea a descomponer: {input}")
            ])
            
            chain = orchestrator_prompt | llm
            response = chain.invoke({"input": state["user_input"]})
            
            # Crear secciones basadas en los agentes del template
            sections = []
            for i, agent in enumerate(template.agents):
                sections.append({
                    "task": f"{agent.goal}: {state['user_input']}",
                    "agent_id": agent.agent_id,
                    "agent_name": agent.name
                })
            
            return {"sections": sections}
        
        # Función para asignar workers usando Send() - SIGUIENDO EL LAB
        def assign_workers(state: OrchestratorState):
            """Asigna workers en paralelo usando Send() API"""
            workers = []
            for section in state.get("sections", []):
                agent_id = section.get("agent_id")
                if agent_id:
                    workers.append(Send(agent_id, {"section": section}))
            return workers
        
        # Construir el grafo PRIMERO
        graph = StateGraph(OrchestratorState)
        graph.add_node("orchestrator", orchestrator_node)
        
        # Nodos worker - SIGUIENDO EL PATRÓN DEL LAB
        worker_nodes = {}
        for agent in template.agents:
            def create_worker(agent_def: WorkflowAgent):
                class WorkerState(TypedDict):
                    section: Dict[str, Any]
                    completed_outputs: Annotated[List[str], operator.add]
                
                def worker_node(state: WorkerState) -> Dict[str, Any]:
                    """Worker que procesa una sección"""
                    section = state.get("section", {})
                    task = section.get("task", "")
                    
                    # Prompt específico para este worker
                    worker_prompt = ChatPromptTemplate.from_messages([
                        ("system", agent_def.backstory),
                        ("human", "Procesa esta tarea:\n\n{task}")
                    ])
                    
                    chain = worker_prompt | llm
                    response = chain.invoke({"task": task})
                    
                    return {"completed_outputs": [response.content]}
                
                return worker_node
            
            worker_nodes[agent.agent_id] = create_worker(agent)
            graph.add_node(agent.agent_id, worker_nodes[agent.agent_id])
        
        # Nodo synthesizer - SIGUIENDO EL LAB
        def synthesizer_node(state: OrchestratorState) -> Dict[str, Any]:
            """Sintetiza todas las salidas de los workers"""
            completed = state.get("completed_outputs", [])
            final = "\n\n---\n\n".join(completed)
            return {"final_output": final}
        
        # Construir el grafo
        graph = StateGraph(OrchestratorState)
        graph.add_node("synthesizer", synthesizer_node)
        
        # Edges siguiendo el patrón del lab
        graph.add_edge(START, "orchestrator")
        
        # Conditional edge para fan-out a workers usando Send()
        graph.add_conditional_edges(
            "orchestrator",
            assign_workers,
            [agent.agent_id for agent in template.agents]
        )
        
        # Todos los workers van al synthesizer
        for agent_id in worker_nodes.keys():
            graph.add_edge(agent_id, "synthesizer")
        
        graph.add_edge("synthesizer", END)
        
        return graph.compile()
    
    def _build_reflection_workflow(
        self,
        workflow_id: str,
        workflow_name: str,
        template: WorkflowTemplate
    ) -> Any:
        """Construye workflow Reflection usando LangGraph - SIGUIENDO EXACTAMENTE EL LAB"""
        if not LANGGRAPH_AVAILABLE:
            raise ImportError("LangGraph requerido para Reflection pattern")
        
        from langgraph.graph import StateGraph, END, START
        from langchain_openai import ChatOpenAI
        from langchain_core.prompts import ChatPromptTemplate
        from pydantic import BaseModel, Field
        from typing import Literal
        
        # Definir grades como en el lab
        grades = Literal["ultra-conservative", "conservative", "moderate", "aggressive", "high risk"]
        
        class ReflectionState(TypedDict):
            user_input: str
            generated_output: str
            evaluation: str
            grade: str
            target_grade: str
            iteration: int
            final_output: str
        
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.7)
        
        # Nodo setup - determina target_grade
        def determine_target_grade(state: ReflectionState) -> Dict[str, Any]:
            """Determina el target_grade basado en el input"""
            grade_prompt = ChatPromptTemplate.from_messages([
                ("system",
                 "Eres un evaluador experto. Dado el input del usuario, "
                 "elige exactamente una clasificación de riesgo: ultra-conservative, conservative, moderate, aggressive, high risk. "
                 "Retorna SOLO el grade."),
                ("user", "Input del usuario:\n\n{input}")
            ])
            
            chain = grade_prompt | llm
            response = chain.invoke({"input": state["user_input"]})
            target_grade = response.content.lower().strip()
            
            # Validar que sea uno de los grades válidos
            valid_grades = ["ultra-conservative", "conservative", "moderate", "aggressive", "high risk"]
            if target_grade not in valid_grades:
                target_grade = "moderate"  # Default
            
            return {"target_grade": target_grade}
        
        # Nodo generador - Fase 1: Cathie Wood style (inicial)
        cathie_wood_prompt = ChatPromptTemplate.from_messages([
            ("system",
             """Eres un asesor de inversiones audaz e innovador inspirado en Cathie Wood.
             Tu objetivo es generar un plan de alta convicción, orientado al futuro que abrace tecnologías disruptivas,
             mercados emergentes y potencial de crecimiento a largo plazo. No temes la volatilidad a corto plazo 
             siempre que el potencial alcista sea transformacional.
             
             Crea una estrategia de inversión adaptada al perfil del usuario. Prioriza innovación y oportunidades 
             de alta recompensa, como inteligencia artificial, biotecnología, blockchain o energía renovable.
             
             Responde con un plan de inversión conciso en forma de párrafo."""),
            ("human", "Input del usuario:\n\n{input}")
        ])
        cathie_wood_pipe = cathie_wood_prompt | llm
        
        # Nodo generador - Fase 2: Ray Dalio style (refinamiento)
        ray_dalio_prompt = ChatPromptTemplate.from_messages([
            ("system",
             """Eres un asesor de inversiones inspirado en los principios de Ray Dalio pero con generación de estrategia adaptativa.
             Tu objetivo es crear planes de inversión variados y conscientes del escenario que respondan dinámicamente a condiciones económicas,
             feedback y necesidades evolutivas del inversor. Adaptas tus recomendaciones basándote en evaluaciones previas.
             
             REGLAS DE ADAPTACIÓN basadas en feedback:
             - Si se considera "demasiado conservador" → Aumenta asignación de equity de crecimiento, agrega mercados emergentes
             - Si se considera "demasiado agresivo" → Agrega activos defensivos, aumenta asignación de bonos
             - Si "carece de protección contra inflación" → Enfatiza TIPS, commodities, REITs
             - Si "demasiado complejo" → Simplifica a estrategia ETF central con racional claro
             
             Responde con un plan de inversión claro y accionable que refleje condiciones económicas actuales
             y se adapte al feedback específico proporcionado."""),
            ("human",
             """Input del usuario:
{input}

Grade de estrategia anterior: {grade}

Feedback del evaluador: {feedback}

Basándote en este feedback, crea una NUEVA estrategia de inversión que aborde las preocupaciones planteadas.
Haz ajustes significativos de cualquier enfoque anterior.""")
        ])
        ray_dalio_pipe = ray_dalio_prompt | llm
        
        # Nodo generador
        def generator_node(state: ReflectionState) -> Dict[str, Any]:
            """Genera o mejora el output basado en feedback"""
            if state.get("evaluation"):
                # Fase de refinamiento (Ray Dalio)
                response = ray_dalio_pipe.invoke({
                    "input": state["user_input"],
                    "grade": state.get("grade", ""),
                    "feedback": state.get("evaluation", "")
                })
            else:
                # Fase inicial (Cathie Wood)
                response = cathie_wood_pipe.invoke({
                    "input": state["user_input"]
                })
            
            return {
                "generated_output": response.content,
                "iteration": state.get("iteration", 0) + 1
            }
        
        # Schema de evaluación
        class Feedback(BaseModel):
            grade: str = Field(description="Clasifica la inversión basado en nivel de riesgo: ultra-conservative, conservative, moderate, aggressive, high risk")
            feedback: str = Field(description="Proporciona razonamiento para la clasificación de riesgo asignada")
        
        # Nodo evaluador - Warren Buffett style
        evaluator_prompt = ChatPromptTemplate.from_messages([
            ("system",
             """Eres un evaluador de riesgo de inversión inspirado en la filosofía de inversión en valor de Warren Buffett.
             
             Tu tarea es evaluar si una estrategia de inversión propuesta se alinea con principios conservadores y orientados al valor
             que enfatizan preservación de capital, estabilidad a largo plazo y fundamentos sólidos del negocio. Debes ser escéptico
             de inversiones especulativas, activos de alta volatilidad y tendencias de mercado a corto plazo.
             
             NIVELES DE CLASIFICACIÓN DE RIESGO:
             - ultra-conservative: Extremadamente seguro, riesgo mínimo de pérdida
             - conservative: Bajo riesgo, prioriza preservación de capital
             - moderate: Enfoque balanceado con ratio riesgo-recompensa aceptable
             - aggressive: Mayor riesgo para retornos potencialmente mayores
             - high risk: Inversiones especulativas con potencial significativo de pérdida
             
             Retorna tu evaluación en el siguiente formato:
             {{
               "grade": "<nivel de riesgo de inversión>",
               "feedback": "<explicación concisa del nivel de riesgo asignado y razonamiento clave>"
             }}"""),
            ("human",
             "Evalúa este plan de inversión:\n\n{plan}\n\nPara este input:\n\n{input}\n\nY proporciona feedback que coincida con este nivel de riesgo objetivo: {target}")
        ])
        buffett_evaluator_pipe = evaluator_prompt | llm.with_structured_output(Feedback)
        
        def evaluator_node(state: ReflectionState) -> Dict[str, Any]:
            """Evalúa el plan generado"""
            current_count = state.get("iteration", 0) + 1
            
            evaluation_result = buffett_evaluator_pipe.invoke({
                "plan": state.get("generated_output", ""),
                "input": state["user_input"],
                "target": state.get("target_grade", "moderate")
            })
            
            return {
                "grade": evaluation_result.grade,
                "evaluation": evaluation_result.feedback,
                "iteration": current_count
            }
        
        # Nodo router - SIGUIENDO EL LAB EXACTO
        def route_investment(state: ReflectionState, iteration_limit: int = 5) -> str:
            """Rutea basado en evaluación de riesgo"""
            current_grade = state.get("grade", "MISSING")
            target_grade = state.get("target_grade", "MISSING")
            match = current_grade == target_grade
            iteration = state.get("iteration", 0)
            
            if match:
                return "Accepted"
            elif iteration > iteration_limit:
                return "Accepted"  # Demasiadas iteraciones, aceptar
            else:
                return "Rejected + Feedback"
        
        # Construir grafo
        graph = StateGraph(ReflectionState)
        graph.add_node("determine_target_grade", determine_target_grade)
        graph.add_node("generator", generator_node)
        graph.add_node("evaluator", evaluator_node)
        
        # Edges siguiendo el lab
        graph.add_edge(START, "determine_target_grade")
        graph.add_edge("determine_target_grade", "generator")
        graph.add_edge("generator", "evaluator")
        
        # Conditional edge para reflection loop
        graph.add_conditional_edges(
            "evaluator",
            lambda state: route_investment(state),
            {
                "Accepted": END,
                "Rejected + Feedback": "generator"
            }
        )
        
        return graph.compile()
    
    def _build_routing_workflow(
        self,
        workflow_id: str,
        workflow_name: str,
        template: WorkflowTemplate
    ) -> Any:
        """Construye workflow Routing usando LangGraph - SIGUIENDO EXACTAMENTE EL LAB"""
        if not LANGGRAPH_AVAILABLE:
            raise ImportError("LangGraph requerido para Routing pattern")
        
        from langgraph.graph import StateGraph, END, START
        from langchain_openai import ChatOpenAI
        from langchain_core.prompts import ChatPromptTemplate
        from pydantic import BaseModel, Field
        
        class RouterState(TypedDict):
            user_input: str
            task_type: str
            output: str
        
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.7)
        
        # Definir Router tool como en el lab
        class Router(BaseModel):
            role: str = Field(
                ...,
                description=f"Clasifica la solicitud del usuario. Retorna exactamente uno de: {', '.join([a.agent_id for a in template.agents])}. Si no sabes, retorna 'default_handler'"
            )
        
        llm_router = llm.bind_tools([Router])
        
        # Nodo router - SIGUIENDO EL LAB EXACTO
        def router_node(state: RouterState) -> Dict[str, Any]:
            """Clasifica el input usando tool binding"""
            routing_prompt = f"""
            Eres un clasificador de tareas AI.
            
            Decide qué tipo de tarea es esta solicitud del usuario.
            Opciones: {', '.join([a.agent_id for a in template.agents])}
            
            Retorna SOLO el tipo de tarea.
            
            Input del usuario: "{state['user_input']}"
            """
            
            response = llm_router.invoke(routing_prompt)
            
            if response.tool_calls:
                task_type = response.tool_calls[0]['args']['role']
            else:
                task_type = "default_handler"
            
            return {"task_type": task_type}
        
        def router_decision(state: RouterState) -> str:
            """Función de decisión para conditional edges"""
            return state["task_type"]
        
        # Nodos de procesamiento - SIGUIENDO EL LAB
        processing_nodes = {}
        for agent in template.agents:
            def create_processor(agent_def: WorkflowAgent):
                def processor_node(state: RouterState) -> Dict[str, Any]:
                    """Procesa la tarea según el tipo"""
                    prompt = ChatPromptTemplate.from_messages([
                        ("system", agent_def.backstory),
                        ("human", "Procesa esta solicitud:\n\n{input}")
                    ])
                    
                    chain = prompt | llm
                    response = chain.invoke({"input": state["user_input"]})
                    
                    return {
                        "output": response.content,
                        "task_type": agent_def.agent_id
                    }
                
                return processor_node
            
            processing_nodes[agent.agent_id] = create_processor(agent)
            graph.add_node(agent.agent_id, processing_nodes[agent.agent_id])
        
        # Nodo default handler
        def default_handler_node(state: RouterState) -> Dict[str, Any]:
            """Maneja solicitudes no clasificadas"""
            prompt = ChatPromptTemplate.from_messages([
                ("system", "Eres un asistente útil. No pudiste clasificar esta solicitud en una categoría específica."),
                ("human", "Solicitud: {input}\n\nPuedo ayudarte con: {options}")
            ])
            
            options = ", ".join([a.name for a in template.agents])
            chain = prompt | llm
            response = chain.invoke({
                "input": state["user_input"],
                "options": options
            })
            
            return {
                "output": response.content,
                "task_type": "default_handler"
            }
        
        # Construir grafo PRIMERO
        graph = StateGraph(RouterState)
        graph.add_node("router", router_node)
        graph.add_node("default_handler", default_handler_node)
        
        # Agregar nodos de procesamiento
        for agent_id, processor_func in processing_nodes.items():
            graph.add_node(agent_id, processor_func)
        
        # Edges
        graph.set_entry_point("router")
        
        # Conditional edges - SIGUIENDO EL LAB
        routing_map = {agent.agent_id: agent.agent_id for agent in template.agents}
        routing_map["default_handler"] = "default_handler"
        
        graph.add_conditional_edges(
            "router",
            router_decision,
            routing_map
        )
        
        # Finish points
        for agent in template.agents:
            graph.add_edge(agent.agent_id, END)
        graph.add_edge("default_handler", END)
        
        return graph.compile()
    
    def _build_parallel_workflow(
        self,
        workflow_id: str,
        workflow_name: str,
        template: WorkflowTemplate
    ) -> Any:
        """Construye workflow Parallel usando LangGraph - SIGUIENDO EXACTAMENTE EL LAB"""
        if not LANGGRAPH_AVAILABLE:
            raise ImportError("LangGraph requerido para Parallel pattern")
        
        from langgraph.graph import StateGraph, END, START
        from langgraph.types import Send
        from langchain_openai import ChatOpenAI
        from langchain_core.prompts import ChatPromptTemplate
        
        class ParallelState(TypedDict):
            user_input: str
            parallel_outputs: Annotated[Dict[str, str], operator.add]
            final_output: str
        
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.7)
        
        # Construir grafo PRIMERO
        graph = StateGraph(ParallelState)
        
        # Nodos worker - SIGUIENDO EL LAB EXACTO
        worker_nodes = {}
        for agent in template.agents:
            def create_parallel_worker(agent_def: WorkflowAgent):
                def parallel_worker(state: Dict[str, Any]) -> Dict[str, str]:
                    """Worker que procesa en paralelo"""
                    input_text = state.get("input", state.get("user_input", ""))
                    
                    prompt = ChatPromptTemplate.from_messages([
                        ("system", agent_def.backstory),
                        ("human", "Procesa esta tarea:\n\n{input}")
                    ])
                    
                    chain = prompt | llm
                    response = chain.invoke({"input": input_text})
                    
                    return {agent_def.agent_id: response.content.strip()}
                
                return parallel_worker
            
            worker_nodes[agent.agent_id] = create_parallel_worker(agent)
            graph.add_node(agent.agent_id, worker_nodes[agent.agent_id])
        
        # Nodo aggregator - SIGUIENDO EL LAB
        def aggregator_node(state: ParallelState) -> Dict[str, Any]:
            """Combina todos los outputs paralelos"""
            outputs = state.get("parallel_outputs", {})
            
            combined = f"Input Original: {state['user_input']}\n\n"
            for agent_id, output in outputs.items():
                agent_name = next((a.name for a in template.agents if a.agent_id == agent_id), agent_id)
                combined += f"**{agent_name}:**\n{output}\n\n---\n\n"
            
            return {"final_output": combined}
        
        graph.add_node("aggregator", aggregator_node)
        
        # Edges - SIGUIENDO EL LAB EXACTO
        # Conectar todos los workers desde START (paralelo)
        for agent_id in worker_nodes.keys():
            graph.add_edge(START, agent_id)
        
        # Todos los workers van al aggregator
        for agent_id in worker_nodes.keys():
            graph.add_edge(agent_id, "aggregator")
        
        # Aggregator va a END
        graph.add_edge("aggregator", END)
        
        return graph.compile()
    
    def _build_sequential_workflow(
        self,
        workflow_id: str,
        workflow_name: str,
        template: WorkflowTemplate
    ) -> Any:
        """Construye workflow Sequential (Prompt Chaining) - SIGUIENDO EXACTAMENTE EL LAB"""
        if not LANGGRAPH_AVAILABLE:
            raise ImportError("LangGraph requerido")
        
        from langgraph.graph import StateGraph, END, START
        from langchain_openai import ChatOpenAI
        from langchain_core.prompts import ChatPromptTemplate
        
        # Definir estado como en el lab (ejemplo: Job Application Assistant)
        class SequentialState(TypedDict):
            user_input: str
            step1_output: str
            step2_output: str
            final_output: str
        
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.7)
        
        graph = StateGraph(SequentialState)
        
        # Crear nodos secuenciales - SIGUIENDO EL PATRÓN DEL LAB
        for i, agent in enumerate(template.agents):
            def create_sequential_node(agent_def: WorkflowAgent, step_num: int, is_last: bool):
                def sequential_node(state: SequentialState) -> Dict[str, Any]:
                    """Nodo secuencial que procesa un paso"""
                    # Construir contexto desde pasos anteriores
                    context_parts = []
                    for j in range(step_num):
                        prev_output = state.get(f"step{j+1}_output", "")
                        if prev_output:
                            context_parts.append(f"Paso {j+1}: {prev_output}")
                    
                    context = "\n".join(context_parts) if context_parts else "Ningún paso previo"
                    
                    prompt = ChatPromptTemplate.from_messages([
                        ("system", agent_def.backstory),
                        ("human", "Input original: {input}\n\nContexto de pasos anteriores:\n{context}\n\nProcesa este paso.")
                    ])
                    
                    chain = prompt | llm
                    response = chain.invoke({
                        "input": state["user_input"],
                        "context": context
                    })
                    
                    output_key = f"step{step_num+1}_output"
                    result = {output_key: response.content}
                    
                    if is_last:
                        result["final_output"] = response.content
                    
                    return result
                
                return sequential_node
            
            is_last = (i == len(template.agents) - 1)
            graph.add_node(agent.agent_id, create_sequential_node(agent, i, is_last))
        
        # Edges secuenciales - SIGUIENDO EL LAB
        graph.set_entry_point(template.agents[0].agent_id)
        
        for i in range(len(template.agents) - 1):
            graph.add_edge(template.agents[i].agent_id, template.agents[i + 1].agent_id)
        
        graph.add_edge(template.agents[-1].agent_id, END)
        
        return graph.compile()
    
    def execute_workflow(
        self,
        workflow_id: str,
        input_data: Dict[str, Any],
        auto_approve: bool = False
    ) -> Dict[str, Any]:
        """
        Ejecuta un workflow
        
        Args:
            workflow_id: ID del workflow
            input_data: Datos de entrada
            auto_approve: Si True, aprueba automáticamente (sin human-in-the-loop)
            
        Returns:
            Resultado de la ejecución
        """
        if workflow_id not in self.workflows:
            raise ValueError(f"Workflow {workflow_id} no encontrado")
        
        workflow_info = self.workflows[workflow_id]
        workflow = workflow_info["workflow"]
        
        try:
            # Ejecutar workflow
            result = workflow.invoke(input_data)
            
            return {
                "success": True,
                "workflow_id": workflow_id,
                "result": result,
                "final_output": result.get("final_output", str(result))
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "workflow_id": workflow_id
            }
    
    def list_workflow_templates(self) -> List[Dict[str, Any]]:
        """Lista todos los templates disponibles"""
        return [
            {
                "template_id": template.template_id,
                "name": template.name,
                "description": template.description,
                "pattern": template.pattern.value,
                "agents_count": len(template.agents),
                "use_cases": template.use_cases
            }
            for template in self.templates.values()
        ]
    
    def get_workflow_template(self, template_id: str) -> Optional[WorkflowTemplate]:
        """Obtiene un template"""
        return self.templates.get(template_id)
    
    def list_workflows(self) -> List[Dict[str, Any]]:
        """Lista todos los workflows creados"""
        return [
            {
                "workflow_id": wf["workflow_id"],
                "name": wf["name"],
                "template_id": wf["template_id"],
                "pattern": wf["pattern"],
                "created_at": wf["created_at"]
            }
            for wf in self.workflows.values()
        ]
