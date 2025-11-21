"""
Orquestador de Agentes Autónomos
Coordina múltiples agentes para realizar tareas complejas de forma autónoma
"""

from typing import Dict, List, Any, Optional
from autonomous_agent import AutonomousAgent, Task, TaskStatus, AgentCapability
from tools import AgentTool, DataRetrievalTool, DataAnalysisTool, ReportGenerationTool, ComparisonTool
from openai import OpenAI
import chromadb
import uuid
import json


class AgentOrchestrator:
    """
    Orquestador que coordina múltiples agentes autónomos para realizar tareas complejas
    """
    
    def __init__(self, 
                 llm_client: OpenAI,
                 chroma_client: chromadb.Client,
                 collection_name: str = None):
        self.llm_client = llm_client
        self.chroma_client = chroma_client
        self.collection_name = collection_name
        
        # Inicializar herramientas compartidas
        self.shared_tools = self._initialize_tools()
        
        # Inicializar agentes especializados
        self.agents = self._initialize_agents()
        
        # Historial de tareas
        self.task_queue: List[Task] = []
        self.completed_tasks: List[Task] = []
    
    def _initialize_tools(self) -> List[AgentTool]:
        """Inicializa las herramientas disponibles"""
        return [
            DataRetrievalTool(self.chroma_client, self.collection_name),
            DataAnalysisTool(),
            ReportGenerationTool(self.llm_client),
            ComparisonTool()
        ]
    
    def _initialize_agents(self) -> Dict[str, AutonomousAgent]:
        """Inicializa agentes especializados"""
        agents = {}
        
        # Agente de Análisis de Datos
        agents["data_analyst"] = AutonomousAgent(
            agent_id="data_analyst",
            capabilities=[
                AgentCapability.DATA_ANALYSIS,
                AgentCapability.DATA_EXTRACTION,
                AgentCapability.TREND_ANALYSIS
            ],
            llm_client=self.llm_client,
            retriever=None,
            tools=[tool for tool in self.shared_tools if tool.name() in ["data_retrieval", "data_analysis"]]
        )
        
        # Agente de Resumen de Documentos
        agents["document_summarizer"] = AutonomousAgent(
            agent_id="document_summarizer",
            capabilities=[
                AgentCapability.DOCUMENT_SUMMARIZATION,
                AgentCapability.DATA_EXTRACTION
            ],
            llm_client=self.llm_client,
            retriever=None,
            tools=[tool for tool in self.shared_tools if tool.name() in ["data_retrieval", "report_generation"]]
        )
        
        # Agente de Comparación
        agents["comparison_agent"] = AutonomousAgent(
            agent_id="comparison_agent",
            capabilities=[
                AgentCapability.COMPARISON,
                AgentCapability.DATA_ANALYSIS
            ],
            llm_client=self.llm_client,
            retriever=None,
            tools=[tool for tool in self.shared_tools if tool.name() in ["data_retrieval", "comparison", "data_analysis"]]
        )
        
        # Agente de Generación de Reportes
        agents["report_generator"] = AutonomousAgent(
            agent_id="report_generator",
            capabilities=[
                AgentCapability.REPORT_GENERATION,
                AgentCapability.DATA_ANALYSIS
            ],
            llm_client=self.llm_client,
            retriever=None,
            tools=self.shared_tools  # Tiene acceso a todas las herramientas
        )
        
        return agents
    
    def assign_task(self, task_description: str, context: Dict[str, Any] = None) -> Task:
        """
        Asigna una tarea al agente más apropiado
        """
        context = context or {}
        
        # Determinar qué agente puede manejar la tarea
        selected_agent = self._select_agent_for_task(task_description)
        
        if not selected_agent:
            raise ValueError("No se encontró un agente capaz de manejar esta tarea")
        
        # Crear la tarea
        task = Task(
            task_id=str(uuid.uuid4()),
            description=task_description,
            status=TaskStatus.PENDING,
            agent_type=selected_agent.agent_id,
            required_capabilities=self._extract_required_capabilities(task_description),
            input_data=context
        )
        
        self.task_queue.append(task)
        return task
    
    def _select_agent_for_task(self, task_description: str) -> Optional[AutonomousAgent]:
        """
        Selecciona el agente más apropiado para una tarea
        """
        # Usar el LLM para determinar el tipo de tarea
        prompt = f"""
        Analiza esta tarea y determina qué tipo de agente la debería manejar:
        
        Tarea: {task_description}
        
        Opciones de agentes:
        1. data_analyst - Para análisis de datos, extracción de información, análisis de tendencias
        2. document_summarizer - Para resumir documentos, extraer información clave
        3. comparison_agent - Para comparar diferentes conjuntos de datos o documentos
        4. report_generator - Para generar reportes estructurados completos
        
        Responde solo con el nombre del agente (ej: "data_analyst").
        """
        
        try:
            response = self.llm_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0
            )
            agent_name = response.choices[0].message.content.strip().lower()
            
            # Validar que el agente existe
            if agent_name in self.agents:
                return self.agents[agent_name]
            
            # Si no se encuentra, usar el agente más general
            return self.agents["report_generator"]
            
        except Exception as e:
            # En caso de error, usar el agente más general
            return self.agents["report_generator"]
    
    def _extract_required_capabilities(self, task_description: str) -> List[AgentCapability]:
        """
        Extrae las capacidades requeridas de una descripción de tarea
        """
        capabilities = []
        desc_lower = task_description.lower()
        
        if any(word in desc_lower for word in ["analizar", "análisis", "tendencia", "patrón"]):
            capabilities.append(AgentCapability.DATA_ANALYSIS)
        
        if any(word in desc_lower for word in ["resumir", "resumen", "extraer información"]):
            capabilities.append(AgentCapability.DOCUMENT_SUMMARIZATION)
        
        if any(word in desc_lower for word in ["comparar", "diferencias", "similitudes"]):
            capabilities.append(AgentCapability.COMPARISON)
        
        if any(word in desc_lower for word in ["reporte", "generar", "crear documento"]):
            capabilities.append(AgentCapability.REPORT_GENERATION)
        
        if not capabilities:
            # Capacidad por defecto
            capabilities.append(AgentCapability.DATA_EXTRACTION)
        
        return capabilities
    
    def execute_task(self, task: Task) -> Task:
        """
        Ejecuta una tarea usando el agente asignado
        """
        agent = self.agents.get(task.agent_type)
        
        if not agent:
            task.status = TaskStatus.FAILED
            task.error_message = f"Agente {task.agent_type} no encontrado"
            return task
        
        # Ejecutar la tarea
        completed_task = agent.execute_task(task)
        
        # Mover a completadas
        if completed_task.status == TaskStatus.COMPLETED:
            self.completed_tasks.append(completed_task)
            if completed_task in self.task_queue:
                self.task_queue.remove(completed_task)
        
        return completed_task
    
    def execute_task_autonomously(self, task_description: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Método de alto nivel que asigna y ejecuta una tarea de forma completamente autónoma
        """
        # Asignar tarea
        task = self.assign_task(task_description, context)
        
        # Ejecutar
        completed_task = self.execute_task(task)
        
        # Retornar resultado
        return {
            "task_id": completed_task.task_id,
            "status": completed_task.status.value,
            "agent_used": completed_task.agent_type,
            "output": completed_task.output_data,
            "error": completed_task.error_message,
            "steps_executed": completed_task.steps or []
        }
    
    def execute_multi_agent_workflow(self, 
                                    main_task: str,
                                    subtasks: List[str] = None,
                                    context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Ejecuta un flujo de trabajo que involucra múltiples agentes trabajando en conjunto
        """
        context = context or {}
        
        # Si no se proporcionan subtareas, el orquestador las genera
        if not subtasks:
            subtasks = self._decompose_task(main_task, context)
        
        # Ejecutar cada subtarea
        subtask_results = []
        for subtask in subtasks:
            result = self.execute_task_autonomously(subtask, context)
            subtask_results.append(result)
            # Actualizar contexto con resultados previos
            context["previous_results"] = subtask_results
        
        # Compilar resultados finales
        final_result = self._compile_multi_agent_results(main_task, subtask_results)
        
        return {
            "main_task": main_task,
            "subtasks": subtasks,
            "subtask_results": subtask_results,
            "final_result": final_result
        }
    
    def _decompose_task(self, main_task: str, context: Dict[str, Any]) -> List[str]:
        """
        Descompone una tarea compleja en subtareas más manejables
        """
        prompt = f"""
        Descompón esta tarea compleja en subtareas más pequeñas y manejables:
        
        Tarea principal: {main_task}
        Contexto disponible: {json.dumps(context, indent=2)}
        
        Crea una lista de subtareas que:
        1. Sean específicas y accionables
        2. Puedan ejecutarse de forma independiente o en secuencia
        3. Juntas completen la tarea principal
        
        Responde en formato JSON:
        {{"subtasks": ["subtarea 1", "subtarea 2", "subtarea 3"]}}
        """
        
        try:
            response = self.llm_client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3
            )
            result = json.loads(response.choices[0].message.content)
            return result.get("subtasks", [main_task])
        except:
            return [main_task]
    
    def _compile_multi_agent_results(self, main_task: str, subtask_results: List[Dict]) -> Dict[str, Any]:
        """
        Compila los resultados de múltiples agentes en un resultado final coherente
        """
        prompt = f"""
        Compila los siguientes resultados de múltiples agentes en una respuesta final coherente:
        
        Tarea principal: {main_task}
        Resultados de subtareas: {json.dumps(subtask_results, indent=2)}
        
        Crea una respuesta final que:
        1. Integre todos los hallazgos de las subtareas
        2. Presente una visión completa y coherente
        3. Sea clara y estructurada
        4. Incluya conclusiones y recomendaciones si es apropiado
        """
        
        try:
            response = self.llm_client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3
            )
            compiled_result = response.choices[0].message.content
            
            return {
                "compiled_response": compiled_result,
                "subtasks_completed": len(subtask_results),
                "successful_subtasks": sum(1 for r in subtask_results if r["status"] == "completed")
            }
        except Exception as e:
            return {
                "error": f"Error compilando resultados: {str(e)}",
                "subtasks_completed": len(subtask_results)
            }
    
    def get_system_status(self) -> Dict[str, Any]:
        """
        Obtiene el estado actual del sistema de agentes
        """
        return {
            "total_agents": len(self.agents),
            "agents": {agent_id: agent.get_task_summary() 
                      for agent_id, agent in self.agents.items()},
            "tasks_queued": len(self.task_queue),
            "tasks_completed": len(self.completed_tasks),
            "available_tools": [tool.name() for tool in self.shared_tools]
        }


