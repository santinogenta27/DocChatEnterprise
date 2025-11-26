"""
Sistema Agentic AI Autónomo para DocChat
Permite que los agentes realicen tareas de forma independiente con los datos subidos
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum
import json
from openai import OpenAI


class TaskStatus(Enum):
    """Estados de una tarea"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    NEEDS_HUMAN_INPUT = "needs_human_input"


class AgentCapability(Enum):
    """Capacidades de los agentes"""
    DATA_ANALYSIS = "data_analysis"
    DOCUMENT_SUMMARIZATION = "document_summarization"
    DATA_EXTRACTION = "data_extraction"
    COMPARISON = "comparison"
    TREND_ANALYSIS = "trend_analysis"
    REPORT_GENERATION = "report_generation"


@dataclass
class Task:
    """Representa una tarea autónoma"""
    task_id: str
    description: str
    status: TaskStatus
    agent_type: str
    required_capabilities: List[AgentCapability]
    input_data: Dict[str, Any]
    output_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    steps: List[str] = None


class AutonomousAgent:
    """
    Agente autónomo que puede planificar y ejecutar tareas de forma independiente
    """
    
    def __init__(self, 
                 agent_id: str,
                 capabilities: List[AgentCapability],
                 llm_client: OpenAI,
                 retriever=None,
                 tools: List = None):
        self.agent_id = agent_id
        self.capabilities = capabilities
        self.llm_client = llm_client
        self.retriever = retriever
        self.tools = tools or []
        self.task_history: List[Task] = []
        self.current_task: Optional[Task] = None
        
    def can_handle_task(self, task_description: str) -> bool:
        """
        Determina si este agente puede manejar una tarea específica
        """
        # Usa el LLM para determinar si las capacidades del agente son suficientes
        prompt = f"""
        Evalúa si un agente con las siguientes capacidades puede realizar esta tarea:
        
        Capacidades del agente: {[cap.value for cap in self.capabilities]}
        Tarea: {task_description}
        
        Responde solo con "SI" o "NO".
        """
        
        try:
            response = self.llm_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0
            )
            result = response.choices[0].message.content.strip().upper()
            return result == "SI"
        except:
            return False
    
    def plan_task(self, task_description: str, context: Dict[str, Any]) -> List[str]:
        """
        Planifica los pasos necesarios para completar una tarea
        """
        prompt = f"""
        Como agente autónomo, necesito planificar cómo completar esta tarea:
        
        Tarea: {task_description}
        Contexto disponible: {json.dumps(context, indent=2)}
        Capacidades disponibles: {[cap.value for cap in self.capabilities]}
        Herramientas disponibles: {[tool.name if hasattr(tool, 'name') else str(tool) for tool in self.tools]}
        
        Crea un plan paso a paso detallado. Cada paso debe ser:
        1. Específico y accionable
        2. Usar las herramientas y capacidades disponibles
        3. Indicar qué datos necesita recuperar o procesar
        
        Responde en formato JSON con una lista de pasos:
        {{"steps": ["paso 1", "paso 2", "paso 3"]}}
        """
        
        try:
            response = self.llm_client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3
            )
            result = json.loads(response.choices[0].message.content)
            return result.get("steps", [])
        except Exception as e:
            return [f"Error en planificación: {str(e)}"]
    
    def execute_task(self, task: Task) -> Task:
        """
        Ejecuta una tarea de forma autónoma
        """
        task.status = TaskStatus.IN_PROGRESS
        self.current_task = task
        
        try:
            # Planificar la tarea
            steps = self.plan_task(task.description, task.input_data)
            task.steps = steps
            
            # Ejecutar cada paso
            results = []
            for i, step in enumerate(steps, 1):
                try:
                    result = self._execute_step(step, task.input_data, results)
                    results.append({
                        "step": i,
                        "description": step,
                        "result": result,
                        "status": "success"
                    })
                except Exception as e:
                    results.append({
                        "step": i,
                        "description": step,
                        "error": str(e),
                        "status": "failed"
                    })
                    # Decidir si continuar o detenerse
                    if not self._should_continue_after_error(e, step):
                        task.status = TaskStatus.FAILED
                        task.error_message = f"Error en paso {i}: {str(e)}"
                        return task
            
            # Compilar resultados finales
            task.output_data = {
                "steps_executed": len(steps),
                "results": results,
                "final_output": self._compile_final_output(results, task.description)
            }
            task.status = TaskStatus.COMPLETED
            
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error_message = str(e)
        
        finally:
            self.task_history.append(task)
            self.current_task = None
        
        return task
    
    def _execute_step(self, step_description: str, context: Dict, previous_results: List) -> Any:
        """
        Ejecuta un paso individual del plan
        """
        # Determinar qué herramienta usar
        tool_to_use = self._select_tool_for_step(step_description)
        
        if tool_to_use:
            return tool_to_use.execute(step_description, context, previous_results)
        else:
            # Si no hay herramienta específica, usar el LLM directamente
            return self._execute_with_llm(step_description, context, previous_results)
    
    def _select_tool_for_step(self, step_description: str):
        """
        Selecciona la herramienta apropiada para un paso
        """
        for tool in self.tools:
            if hasattr(tool, 'can_handle') and tool.can_handle(step_description):
                return tool
        return None
    
    def _execute_with_llm(self, step_description: str, context: Dict, previous_results: List) -> str:
        """
        Ejecuta un paso usando el LLM cuando no hay herramienta específica
        """
        prompt = f"""
        Como agente autónomo, ejecuta este paso:
        
        Paso: {step_description}
        Contexto: {json.dumps(context, indent=2)}
        Resultados previos: {json.dumps(previous_results, indent=2)}
        
        Proporciona el resultado de ejecutar este paso de forma clara y estructurada.
        """
        
        response = self.llm_client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )
        
        return response.choices[0].message.content
    
    def _should_continue_after_error(self, error: Exception, step: str) -> bool:
        """
        Decide si continuar después de un error
        """
        # Errores críticos que detienen la ejecución
        critical_errors = ["authentication", "permission", "not found", "invalid"]
        error_str = str(error).lower()
        
        if any(crit in error_str for crit in critical_errors):
            return False
        
        # Para otros errores, el agente puede intentar continuar
        return True
    
    def _compile_final_output(self, results: List, task_description: str) -> str:
        """
        Compila los resultados de todos los pasos en una respuesta final
        """
        prompt = f"""
        Compila los siguientes resultados de pasos ejecutados en una respuesta final coherente:
        
        Tarea original: {task_description}
        Resultados de pasos: {json.dumps(results, indent=2)}
        
        Crea una respuesta final que:
        1. Resuma lo que se logró
        2. Presente los hallazgos clave
        3. Incluya cualquier dato importante extraído
        4. Sea clara y estructurada
        """
        
        response = self.llm_client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )
        
        return response.choices[0].message.content
    
    def get_task_summary(self) -> Dict[str, Any]:
        """
        Obtiene un resumen de las tareas realizadas
        """
        completed = sum(1 for t in self.task_history if t.status == TaskStatus.COMPLETED)
        failed = sum(1 for t in self.task_history if t.status == TaskStatus.FAILED)
        
        return {
            "agent_id": self.agent_id,
            "total_tasks": len(self.task_history),
            "completed": completed,
            "failed": failed,
            "success_rate": completed / len(self.task_history) if self.task_history else 0,
            "capabilities": [cap.value for cap in self.capabilities]
        }


