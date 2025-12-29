"""ReAct Agent - Implementación completa de Reasoning + Acting."""

from typing import Dict, Any, List, Optional
from langchain_core.language_models import BaseLanguageModel
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
from langchain_core.tools import BaseTool
import json


class ReActAgent:
    """Agente ReAct completo - Reasoning + Acting."""
    
    def __init__(self, llm: BaseLanguageModel, tools: Dict[str, BaseTool]):
        self.llm = llm
        self.tools = tools
        self.tools_by_name = {name: tool for name, tool in tools.items()}
        
        self.system_prompt = """You are a helpful AI assistant that thinks step-by-step and uses tools when needed.

When responding to queries:
1. First, think about what information you need (Thought)
2. Use available tools if you need current data or specific capabilities (Action)
3. Process the tool results (Observation)
4. Continue reasoning if needed, or provide the final answer

Format your reasoning as:
Thought: [your reasoning]
Action: [tool_name] or None
Action Input: [parameters] or None
Observation: [tool result] or None
Final Answer: [complete response]

Always explain your thinking process."""
    
    def reason_and_act(
        self,
        query: str,
        conversation_history: List = None,
        max_iterations: int = 5
    ) -> Dict[str, Any]:
        """Ejecuta ciclo ReAct completo.
        
        Returns:
            {
                "final_answer": str,
                "thoughts": List[str],
                "actions_taken": List[Dict],
                "observations": List[str]
            }
        """
        thoughts = []
        actions_taken = []
        observations = []
        
        current_query = query
        iteration = 0
        
        while iteration < max_iterations:
            iteration += 1
            
            # Construir mensajes
            messages = [SystemMessage(content=self.system_prompt)]
            
            if conversation_history:
                messages.extend(conversation_history[-5:])  # Últimos 5 mensajes
            
            # Agregar historial de reasoning si existe
            if thoughts:
                reasoning_context = "\n\n".join([
                    f"Thought {i+1}: {thought}\nAction: {actions_taken[i].get('tool', 'None')}\nObservation: {observations[i] if i < len(observations) else 'None'}"
                    for i, thought in enumerate(thoughts)
                ])
                messages.append(HumanMessage(content=f"Previous reasoning:\n{reasoning_context}\n\nCurrent query: {current_query}"))
            else:
                messages.append(HumanMessage(content=current_query))
            
            # Llamar LLM
            try:
                response = self.llm.invoke(messages)
                response_text = response.content if hasattr(response, 'content') else str(response)
            except Exception as e:
                return {
                    "final_answer": f"Error procesando: {str(e)}",
                    "thoughts": thoughts,
                    "actions_taken": actions_taken,
                    "observations": observations,
                    "error": str(e)
                }
            
            # Parsear respuesta (buscar Thought, Action, Action Input, Observation, Final Answer)
            parsed = self._parse_react_response(response_text)
            
            # Agregar thought
            if parsed.get("thought"):
                thoughts.append(parsed["thought"])
            
            # Si hay acción, ejecutarla
            if parsed.get("action") and parsed.get("action") != "None":
                tool_name = parsed["action"]
                action_input = parsed.get("action_input", "")
                
                if tool_name in self.tools_by_name:
                    try:
                        tool_result = self.tools_by_name[tool_name].invoke(action_input)
                        observation = json.dumps(tool_result) if isinstance(tool_result, (dict, list)) else str(tool_result)
                        observations.append(observation)
                        actions_taken.append({
                            "tool": tool_name,
                            "input": action_input,
                            "result": observation
                        })
                        
                        # Actualizar query con la observación
                        current_query = f"Based on this observation: {observation}\n\nContinue reasoning or provide final answer."
                    except Exception as e:
                        observation = f"Error ejecutando tool {tool_name}: {str(e)}"
                        observations.append(observation)
                        actions_taken.append({
                            "tool": tool_name,
                            "input": action_input,
                            "error": str(e)
                        })
                else:
                    observation = f"Tool {tool_name} no encontrado"
                    observations.append(observation)
            else:
                # No hay más acciones, extraer respuesta final
                final_answer = parsed.get("final_answer") or response_text
                return {
                    "final_answer": final_answer,
                    "thoughts": thoughts,
                    "actions_taken": actions_taken,
                    "observations": observations
                }
        
        # Si llegamos al máximo de iteraciones, devolver lo que tengamos
        return {
            "final_answer": f"Procesado en {max_iterations} iteraciones. Última respuesta: {thoughts[-1] if thoughts else 'No se pudo completar'}",
            "thoughts": thoughts,
            "actions_taken": actions_taken,
            "observations": observations,
            "max_iterations_reached": True
        }
    
    def _parse_react_response(self, response_text: str) -> Dict[str, Any]:
        """Parsea respuesta del LLM buscando formato ReAct."""
        parsed = {
            "thought": None,
            "action": None,
            "action_input": None,
            "observation": None,
            "final_answer": None
        }
        
        lines = response_text.split("\n")
        current_section = None
        
        for line in lines:
            line_lower = line.lower().strip()
            
            if line_lower.startswith("thought:"):
                parsed["thought"] = line.split(":", 1)[1].strip() if ":" in line else ""
                current_section = "thought"
            elif line_lower.startswith("action:"):
                parsed["action"] = line.split(":", 1)[1].strip() if ":" in line else ""
                current_section = "action"
            elif line_lower.startswith("action input:") or line_lower.startswith("action_input:"):
                parsed["action_input"] = line.split(":", 1)[1].strip() if ":" in line else ""
                current_section = "action_input"
            elif line_lower.startswith("observation:"):
                parsed["observation"] = line.split(":", 1)[1].strip() if ":" in line else ""
                current_section = "observation"
            elif line_lower.startswith("final answer:") or line_lower.startswith("final_answer:"):
                parsed["final_answer"] = line.split(":", 1)[1].strip() if ":" in line else ""
                current_section = "final_answer"
            elif current_section and line.strip():
                # Continuar agregando a la sección actual
                if current_section == "thought" and parsed["thought"]:
                    parsed["thought"] += " " + line.strip()
                elif current_section == "final_answer" and parsed["final_answer"]:
                    parsed["final_answer"] += " " + line.strip()
        
        return parsed

