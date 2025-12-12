"""
Agent Orchestrator - Sistema de orquestación de agentes
Basado en principios de Google: "El trabajo del agente es curar el context window"
"""

from __future__ import annotations

import time
import uuid
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

from ..config import AppConfig
from ..utils.llm_factory import create_llm


class AgentStatus(Enum):
    """Estados de salud del agente (no solo up/down)"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"  # Funciona pero con calidad reducida
    PARTIAL = "partial"  # Parcialmente funcional
    FAILED = "failed"
    UNKNOWN = "unknown"


class TaskComplexity(Enum):
    """Complejidad de tarea para capability-based routing"""
    LOW = "low"  # < 100 tokens
    MEDIUM = "medium"  # 100-1000 tokens
    HIGH = "high"  # 1000-10000 tokens
    VERY_HIGH = "very_high"  # > 10000 tokens


@dataclass
class AgentIdentity:
    """Identidad del agente (tratado como empleado semi-autónomo)"""
    agent_id: str
    name: str
    role: str
    persona: str
    budget: float  # Presupuesto de tokens/costos
    policies: List[str] = field(default_factory=list)
    privileges: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class AgentNode:
    """Nodo de agente en el workflow"""
    node_id: str
    agent_id: str
    task_description: str
    input_sources: List[str] = field(default_factory=list)  # IDs de otros nodos o documentos
    output_targets: List[str] = field(default_factory=list)
    tools: List[str] = field(default_factory=list)  # MCP servers o herramientas
    validation_rules: Dict[str, Any] = field(default_factory=dict)
    quality_checks: List[str] = field(default_factory=list)
    temperature: float = 0.0  # "Dumb agent" - mínimo necesario
    max_tokens: int = 2000
    status: AgentStatus = AgentStatus.UNKNOWN
    last_run: Optional[str] = None
    run_count: int = 0
    success_count: int = 0
    failure_count: int = 0


@dataclass
class AgentWorkflow:
    """Workflow completo de agentes"""
    workflow_id: str
    name: str
    description: str
    nodes: List[AgentNode] = field(default_factory=list)
    state: Dict[str, Any] = field(default_factory=dict)  # Stateful intelligence
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    last_run: Optional[str] = None
    total_runs: int = 0


@dataclass
class AgentRunTrace:
    """Traza completa de ejecución (auditabilidad)"""
    trace_id: str
    workflow_id: str
    start_time: float
    end_time: Optional[float] = None
    nodes_executed: List[str] = field(default_factory=list)
    node_results: Dict[str, Any] = field(default_factory=dict)
    errors: List[Dict[str, Any]] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    token_usage: Dict[str, int] = field(default_factory=dict)
    cost: float = 0.0
    quality_score: Optional[float] = None


class AgentOrchestrator:
    """
    Orquestador de agentes
    Principios:
    1. Stateful intelligence - preserva contexto
    2. Bounded uncertainty - determinismo sobre núcleos probabilísticos
    3. Fail fast design - detección inteligente de fallos
    4. Capability-based routing - enrutar por complejidad
    5. Binary health state - estados complejos de salud
    6. Continuous validation - validar en cada paso
    """
    
    def __init__(self, config: AppConfig):
        self.config = config
        
        # Agentes registrados
        self.agents: Dict[str, AgentIdentity] = {}
        
        # Workflows
        self.workflows: Dict[str, AgentWorkflow] = {}
        
        # Stateful intelligence - preservar contexto
        self.workflow_states: Dict[str, Dict[str, Any]] = {}
        
        # Trazas de ejecución (auditabilidad)
        self.traces: Dict[str, AgentRunTrace] = {}
        
        # Monitoring
        self.health_monitor: Dict[str, AgentStatus] = {}
        
        # LLM factory para crear agentes
        self.llm_factory = create_llm
    
    def register_agent(
        self,
        name: str,
        role: str,
        persona: str,
        budget: float = 1000.0,
        policies: Optional[List[str]] = None,
        privileges: Optional[List[str]] = None
    ) -> AgentIdentity:
        """Registra un nuevo agente (tratado como identidad de primera clase)"""
        agent_id = f"agent_{uuid.uuid4().hex[:8]}"
        
        agent = AgentIdentity(
            agent_id=agent_id,
            name=name,
            role=role,
            persona=persona,
            budget=budget,
            policies=policies or [],
            privileges=privileges or []
        )
        
        self.agents[agent_id] = agent
        self.health_monitor[agent_id] = AgentStatus.UNKNOWN
        
        return agent
    
    def create_workflow(
        self,
        name: str,
        description: str
    ) -> AgentWorkflow:
        """Crea un nuevo workflow de agentes"""
        workflow_id = f"workflow_{uuid.uuid4().hex[:8]}"
        
        workflow = AgentWorkflow(
            workflow_id=workflow_id,
            name=name,
            description=description
        )
        
        self.workflows[workflow_id] = workflow
        self.workflow_states[workflow_id] = {}
        
        return workflow
    
    def add_node(
        self,
        workflow_id: str,
        agent_id: str,
        task_description: str,
        input_sources: Optional[List[str]] = None,
        output_targets: Optional[List[str]] = None,
        tools: Optional[List[str]] = None,
        validation_rules: Optional[Dict[str, Any]] = None,
        quality_checks: Optional[List[str]] = None,
        temperature: float = 0.0,  # "Dumb agent" por defecto
        max_tokens: int = 2000
    ) -> AgentNode:
        """Añade un nodo al workflow (agente "tonto" con contexto claro)"""
        if workflow_id not in self.workflows:
            raise ValueError(f"Workflow {workflow_id} no existe")
        
        if agent_id not in self.agents:
            raise ValueError(f"Agente {agent_id} no registrado")
        
        node_id = f"node_{uuid.uuid4().hex[:8]}"
        
        node = AgentNode(
            node_id=node_id,
            agent_id=agent_id,
            task_description=task_description,
            input_sources=input_sources or [],
            output_targets=output_targets or [],
            tools=tools or [],
            validation_rules=validation_rules or {},
            quality_checks=quality_checks or [],
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        self.workflows[workflow_id].nodes.append(node)
        
        return node
    
    def _estimate_complexity(self, task: str, context_size: int) -> TaskComplexity:
        """Estima complejidad de tarea para capability-based routing"""
        estimated_tokens = len(task.split()) * 1.3 + context_size
        
        if estimated_tokens < 100:
            return TaskComplexity.LOW
        elif estimated_tokens < 1000:
            return TaskComplexity.MEDIUM
        elif estimated_tokens < 10000:
            return TaskComplexity.HIGH
        else:
            return TaskComplexity.VERY_HIGH
    
    def _route_by_capability(
        self,
        complexity: TaskComplexity,
        available_agents: List[str]
    ) -> Optional[str]:
        """Enruta tarea según complejidad (capability-based routing)"""
        # Para tareas simples, usar agentes con menos capacidad
        # Para tareas complejas, usar agentes más potentes
        
        if complexity == TaskComplexity.LOW:
            # Usar agente más simple disponible
            return available_agents[0] if available_agents else None
        elif complexity == TaskComplexity.MEDIUM:
            # Usar agente medio
            return available_agents[0] if available_agents else None
        else:
            # Usar agente más potente (puede requerir más tokens)
            return available_agents[-1] if available_agents else None
    
    async def execute_workflow(
        self,
        workflow_id: str,
        initial_input: Dict[str, Any],
        validate_continuously: bool = True
    ) -> AgentRunTrace:
        """
        Ejecuta workflow completo
        Principios aplicados:
        - Stateful intelligence: preserva estado entre ejecuciones
        - Continuous validation: valida en cada paso
        - Fail fast: detecta fallos temprano
        - Auditabilidad: traza completa
        """
        if workflow_id not in self.workflows:
            raise ValueError(f"Workflow {workflow_id} no existe")
        
        workflow = self.workflows[workflow_id]
        
        # Crear traza
        trace = AgentRunTrace(
            trace_id=f"trace_{uuid.uuid4().hex[:8]}",
            workflow_id=workflow_id,
            start_time=time.time()
        )
        
        # Cargar estado previo (stateful intelligence)
        state = self.workflow_states.get(workflow_id, {})
        state.update(initial_input)
        
        try:
            # Ejecutar nodos en orden
            for node in workflow.nodes:
                trace.nodes_executed.append(node.node_id)
                
                # 1. Validar inputs (continuous validation)
                if validate_continuously:
                    validation_result = self._validate_inputs(node, state)
                    if not validation_result["valid"]:
                        error = {
                            "node_id": node.node_id,
                            "type": "validation_error",
                            "message": validation_result["message"]
                        }
                        trace.errors.append(error)
                        node.status = AgentStatus.FAILED
                        continue
                
                # 2. Preparar contexto (bounded uncertainty)
                context = self._prepare_context(node, state)
                
                # 3. Estimar complejidad y enrutar
                complexity = self._estimate_complexity(
                    node.task_description,
                    len(str(context))
                )
                
                # 4. Ejecutar nodo
                result = await self._execute_node(node, context, state)
                
                # 5. Validar output (continuous validation)
                if validate_continuously:
                    output_validation = self._validate_output(node, result)
                    if not output_validation["valid"]:
                        warning = f"Node {node.node_id}: {output_validation['message']}"
                        trace.warnings.append(warning)
                        node.status = AgentStatus.DEGRADED
                    else:
                        node.status = AgentStatus.HEALTHY
                        node.success_count += 1
                
                # 6. Actualizar estado (stateful intelligence)
                state[node.node_id] = result
                trace.node_results[node.node_id] = result
                
                node.last_run = datetime.now().isoformat()
                node.run_count += 1
            
            # Guardar estado
            self.workflow_states[workflow_id] = state
            
            trace.end_time = time.time()
            workflow.last_run = datetime.now().isoformat()
            workflow.total_runs += 1
            
            # Calcular calidad general
            trace.quality_score = self._calculate_quality_score(workflow, trace)
        
        except Exception as e:
            trace.end_time = time.time()
            trace.errors.append({
                "type": "execution_error",
                "message": str(e)
            })
            raise
        
        finally:
            # Guardar traza
            self.traces[trace.trace_id] = trace
        
        return trace
    
    def _validate_inputs(self, node: AgentNode, state: Dict[str, Any]) -> Dict[str, Any]:
        """Valida inputs del nodo (continuous validation)"""
        # Verificar que todos los inputs requeridos estén presentes
        for input_source in node.input_sources:
            if input_source not in state:
                return {
                    "valid": False,
                    "message": f"Input source {input_source} no encontrado en estado"
                }
        
        # Aplicar reglas de validación personalizadas
        for rule_name, rule_check in node.validation_rules.items():
            # Implementar validaciones específicas
            pass
        
        return {"valid": True}
    
    def _validate_output(self, node: AgentNode, output: Any) -> Dict[str, Any]:
        """Valida output del nodo (continuous validation)"""
        # Ejecutar quality checks
        for check in node.quality_checks:
            # Implementar checks específicos
            pass
        
        return {"valid": True}
    
    def _prepare_context(self, node: AgentNode, state: Dict[str, Any]) -> str:
        """Prepara contexto para el nodo (bounded uncertainty)"""
        # Agregar inputs al contexto
        context_parts = [node.task_description]
        
        for input_source in node.input_sources:
            if input_source in state:
                context_parts.append(f"Input from {input_source}: {state[input_source]}")
        
        # Agregar estado previo relevante (stateful intelligence)
        if node.node_id in state:
            context_parts.append(f"Previous state: {state[node.node_id]}")
        
        return "\n".join(context_parts)
    
    async def _execute_node(
        self,
        node: AgentNode,
        context: str,
        state: Dict[str, Any]
    ) -> Any:
        """Ejecuta un nodo individual"""
        agent = self.agents[node.agent_id]
        
        # Crear LLM con configuración "dumb" (bounded uncertainty)
        llm = self.llm_factory(
            self.config,
            provider="openai",
            temperature=node.temperature,  # 0.0 para determinismo
            max_tokens=node.max_tokens
        )
        
        # Construir prompt sin ambigüedad
        prompt = f"""Eres {agent.name}, {agent.role}.

PERSONA: {agent.persona}

TAREA ESPECÍFICA:
{node.task_description}

CONTEXTO:
{context}

INSTRUCCIONES:
1. Realiza SOLO la tarea especificada
2. No hagas suposiciones
3. Si falta información, indica claramente qué falta
4. Responde en formato estructurado

HERRAMIENTAS DISPONIBLES: {', '.join(node.tools) if node.tools else 'Ninguna'}

Responde ahora:"""
        
        try:
            response = await llm.ainvoke(prompt)
            return response.content
        except Exception as e:
            node.failure_count += 1
            raise
    
    def _calculate_quality_score(
        self,
        workflow: AgentWorkflow,
        trace: AgentRunTrace
    ) -> float:
        """Calcula score de calidad del workflow"""
        if not trace.nodes_executed:
            return 0.0
        
        # Ratio de éxito
        success_ratio = len([n for n in workflow.nodes if n.status == AgentStatus.HEALTHY]) / len(workflow.nodes)
        
        # Penalizar errores
        error_penalty = len(trace.errors) * 0.1
        
        # Penalizar warnings
        warning_penalty = len(trace.warnings) * 0.05
        
        score = success_ratio - error_penalty - warning_penalty
        return max(0.0, min(1.0, score))
    
    def get_workflow_health(self, workflow_id: str) -> Dict[str, Any]:
        """Obtiene estado de salud del workflow (binary health state)"""
        if workflow_id not in self.workflows:
            return {"status": "not_found"}
        
        workflow = self.workflows[workflow_id]
        
        # Calcular estado agregado
        node_statuses = [node.status for node in workflow.nodes]
        
        if all(s == AgentStatus.HEALTHY for s in node_statuses):
            overall_status = "healthy"
        elif any(s == AgentStatus.FAILED for s in node_statuses):
            overall_status = "failed"
        elif any(s == AgentStatus.DEGRADED for s in node_statuses):
            overall_status = "degraded"
        elif any(s == AgentStatus.PARTIAL for s in node_statuses):
            overall_status = "partial"
        else:
            overall_status = "unknown"
        
        return {
            "workflow_id": workflow_id,
            "overall_status": overall_status,
            "node_statuses": {n.node_id: n.status.value for n in workflow.nodes},
            "total_runs": workflow.total_runs,
            "last_run": workflow.last_run
        }
    
    def get_audit_trace(self, trace_id: str) -> Optional[AgentRunTrace]:
        """Obtiene traza completa para auditoría"""
        return self.traces.get(trace_id)

