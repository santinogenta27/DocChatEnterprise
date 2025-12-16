"""
ReAct Agent - Reasoning and Acting AI Agents
Implementación del framework ReAct (Reasoning + Acting) para agentes inteligentes.

Basado en: Build a Simple ReAct Agent from Scratch
Características:
- Razonamiento estructurado paso a paso
- Uso de herramientas externas
- Transparencia en el proceso de decisión
- Adaptación basada en resultados
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional, Sequence, Annotated, TypedDict
from datetime import datetime

try:
    from langgraph.graph import StateGraph, END
    from langgraph.graph.message import add_messages
    from langgraph.checkpoint.memory import MemorySaver
    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False
    print("⚠️ LangGraph no está instalado. Instala con: pip install langgraph")

from langchain_core.messages import (
    BaseMessage, HumanMessage, AIMessage, ToolMessage, SystemMessage
)
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.tools import tool
from langchain_core.language_models import BaseLanguageModel
from langchain_openai import ChatOpenAI

from .config import AppConfig


class AgentState(TypedDict):
    """Estado del agente ReAct."""
    messages: Annotated[Sequence[BaseMessage], add_messages]


class ReActAgent:
    """
    Agente ReAct (Reasoning + Acting).
    
    Características:
    - Razonamiento estructurado paso a paso
    - Uso de herramientas externas
    - Transparencia en decisiones
    - Adaptación basada en resultados
    """
    
    def __init__(
        self,
        config: AppConfig,
        llm: Optional[BaseLanguageModel] = None,
        tools: Optional[List[Any]] = None,
        system_prompt: Optional[str] = None
    ):
        self.config = config
        
        if not LANGGRAPH_AVAILABLE:
            raise ImportError("LangGraph no está instalado. Instala con: pip install langgraph")
        
        # LLM
        if llm:
            self.llm = llm
        else:
            if not config.openai_api_key:
                raise ValueError("OPENAI_API_KEY requerida para ReAct Agent")
            self.llm = ChatOpenAI(
                model=config.agentic_model or "gpt-4o-mini",
                temperature=0.3,
                api_key=config.openai_api_key,
                max_tokens=2000
            )
        
        # Herramientas
        self.raw_tools = tools or []
        # Convertir BaseTool a funciones LangChain
        self.tools = self._convert_tools_to_langchain(self.raw_tools)
        # Crear diccionario de herramientas LangChain por nombre
        self.tools_by_name = {}
        for tool in self.tools:
            if hasattr(tool, 'name'):
                self.tools_by_name[tool.name] = tool
        # También mantener referencia a herramientas originales por si acaso
        self.raw_tools_by_name = {}
        for tool in self.raw_tools:
            if hasattr(tool, 'name'):
                self.raw_tools_by_name[tool.name] = tool
        
        # System prompt
        self.system_prompt = system_prompt or """
You are a helpful AI assistant that thinks step-by-step and uses tools when needed.

When responding to queries:

1. First, think about what information you need
2. Use available tools if you need current data or specific capabilities
3. Provide clear, helpful responses based on your reasoning and any tool results

Always explain your thinking process to help users understand your approach.
"""
        
        # Crear prompt template
        self.chat_prompt = ChatPromptTemplate.from_messages([
            ("system", self.system_prompt),
            MessagesPlaceholder(variable_name="scratch_pad")
        ])
        
        # Bind tools to model
        if self.tools:
            self.model_react = self.chat_prompt | self.llm.bind_tools(self.tools)
        else:
            self.model_react = self.chat_prompt | self.llm
        
        # Memory para checkpointing
        self.memory = MemorySaver()
        
        # Compilar grafo
        self.graph = self._build_graph()
    
    def _convert_tools_to_langchain(self, tools: List[Any]) -> List[Any]:
        """
        Convierte instancias de BaseTool a funciones LangChain compatibles.
        
        Args:
            tools: Lista de herramientas (pueden ser BaseTool o funciones LangChain)
        
        Returns:
            Lista de herramientas en formato LangChain
        """
        langchain_tools = []
        
        for tool_obj in tools:
            # Si ya es una herramienta LangChain, usarla directamente
            if hasattr(tool_obj, 'name') and hasattr(tool_obj, 'invoke'):
                # Ya es una herramienta LangChain
                langchain_tools.append(tool_obj)
                continue
            
            # Si es una instancia de BaseTool, convertirla
            if hasattr(tool_obj, 'get_name') and hasattr(tool_obj, 'execute'):
                tool_name = tool_obj.get_name()
                tool_description = tool_obj.get_description()
                
                # Crear función wrapper con closure correcto
                def tool_func(**kwargs):
                    """Tool function wrapper."""
                    try:
                        result = tool_obj.execute(**kwargs)
                        # Convertir ToolResult a string/dict
                        if hasattr(result, 'success'):
                            if result.success:
                                return result.data if result.data else result.message
                            else:
                                return f"Error: {result.message}"
                        return str(result)
                    except Exception as e:
                        return f"Error ejecutando herramienta: {str(e)}"
                
                # Usar StructuredTool para crear la herramienta con nombre y descripción
                from langchain_core.tools import StructuredTool
                langchain_tool = StructuredTool.from_function(
                    func=tool_func,
                    name=tool_name,
                    description=tool_description
                )
                
                langchain_tools.append(langchain_tool)
            else:
                # Si no es BaseTool ni LangChain tool, intentar usarlo directamente
                # (puede ser una función ya decorada)
                langchain_tools.append(tool_obj)
        
        return langchain_tools
    
    def _build_graph(self) -> StateGraph:
        """Construye el grafo de LangGraph para ReAct."""
        
        def call_model(state: AgentState):
            """Invoca el modelo con el estado actual."""
            response = self.model_react.invoke({"scratch_pad": state["messages"]})
            return {"messages": [response]}
        
        def tool_node(state: AgentState):
            """Ejecuta todas las llamadas a herramientas del último mensaje."""
            if not self.tools:
                return {"messages": []}
            
            outputs = []
            last_message = state["messages"][-1]
            
            if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
                for tool_call in last_message.tool_calls:
                    try:
                        tool_name = tool_call["name"]
                        tool_args = tool_call.get("args", {})
                        
                        # Buscar herramienta LangChain
                        if tool_name in self.tools_by_name:
                            langchain_tool = self.tools_by_name[tool_name]
                            tool_result = langchain_tool.invoke(tool_args)
                        else:
                            # Fallback: usar herramienta original si existe
                            if tool_name in self.raw_tools_by_name:
                                raw_tool = self.raw_tools_by_name[tool_name]
                                result = raw_tool.execute(**tool_args)
                                tool_result = result.data if hasattr(result, 'data') and result.success else result.message
                            else:
                                tool_result = f"Error: Herramienta '{tool_name}' no encontrada"
                        
                        outputs.append(
                            ToolMessage(
                                content=json.dumps(tool_result) if not isinstance(tool_result, str) else tool_result,
                                name=tool_call["name"],
                                tool_call_id=tool_call["id"],
                            )
                        )
                    except Exception as e:
                        outputs.append(
                            ToolMessage(
                                content=f"Error ejecutando herramienta: {str(e)}",
                                name=tool_call["name"],
                                tool_call_id=tool_call["id"],
                            )
                        )
            
            return {"messages": outputs}
        
        def should_continue(state: AgentState):
            """Determina si continuar con herramientas o terminar."""
            messages = state["messages"]
            if not messages:
                return "end"
            
            last_message = messages[-1]
            
            # Si no hay tool calls, terminar
            if not hasattr(last_message, 'tool_calls') or not last_message.tool_calls:
                return "end"
            
            # Si hay tool calls, continuar
            return "continue"
        
        # Crear grafo
        workflow = StateGraph(AgentState)
        
        # Agregar nodos
        workflow.add_node("agent", call_model)
        if self.tools:
            workflow.add_node("tools", tool_node)
        
        # Agregar edges
        if self.tools:
            workflow.add_edge("tools", "agent")  # Después de tools, volver a agent
            
            # Edge condicional desde agent
            workflow.add_conditional_edges(
                "agent",
                should_continue,
                {
                    "continue": "tools",
                    "end": END,
                },
            )
        else:
            # Sin herramientas, solo agent → end
            workflow.add_edge("agent", END)
        
        # Entry point
        workflow.set_entry_point("agent")
        
        # Compilar
        return workflow.compile(checkpointer=self.memory)
    
    def run(
        self,
        query: str,
        stream: bool = False,
        config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Ejecuta el agente ReAct con una consulta.
        
        Args:
            query: Consulta del usuario
            stream: Si retornar stream o resultado final
            config: Configuración de ejecución
        """
        inputs = {"messages": [HumanMessage(content=query)]}
        run_config = config or {"configurable": {"thread_id": f"react_{datetime.now().timestamp()}"}}
        
        if stream:
            return {
                "stream": self.graph.stream(inputs, config=run_config, stream_mode="values"),
                "success": True
            }
        else:
            result = self.graph.invoke(inputs, config=run_config)
            
            # Extraer respuesta final
            final_message = result["messages"][-1]
            response_text = final_message.content if hasattr(final_message, 'content') else str(final_message)
            
            # Extraer reasoning steps (mensajes del agente)
            reasoning_steps = [
                {
                    "type": "reasoning",
                    "content": msg.content if hasattr(msg, 'content') else str(msg),
                    "tool_calls": msg.tool_calls if hasattr(msg, 'tool_calls') else []
                }
                for msg in result["messages"]
                if isinstance(msg, AIMessage)
            ]
            
            # Extraer tool executions
            tool_executions = [
                {
                    "tool": msg.name,
                    "result": msg.content
                }
                for msg in result["messages"]
                if isinstance(msg, ToolMessage)
            ]
            
            return {
                "success": True,
                "response": response_text,
                "reasoning_steps": reasoning_steps,
                "tool_executions": tool_executions,
                "messages": result["messages"]
            }
    
    def add_tool(self, tool_func: Any):
        """Agrega una herramienta al agente."""
        self.tools.append(tool_func)
        self.tools_by_name[tool_func.name] = tool_func
        # Reconstruir grafo con nueva herramienta
        self.graph = self._build_graph()
    
    def get_reasoning_explanation(self, result: Dict[str, Any]) -> str:
        """
        Genera una explicación del proceso de razonamiento.
        
        Args:
            result: Resultado de run()
        """
        explanation = "## Proceso de Razonamiento\n\n"
        
        for i, step in enumerate(result.get("reasoning_steps", []), 1):
            explanation += f"### Paso {i}: Razonamiento\n"
            explanation += f"{step['content']}\n\n"
            
            if step.get("tool_calls"):
                explanation += "**Herramientas usadas:**\n"
                for tool_call in step["tool_calls"]:
                    explanation += f"- {tool_call.get('name', 'Unknown')}\n"
                explanation += "\n"
        
        if result.get("tool_executions"):
            explanation += "### Ejecuciones de Herramientas\n\n"
            for i, exec in enumerate(result.get("tool_executions", []), 1):
                explanation += f"**{i}. {exec['tool']}**\n"
                explanation += f"Resultado: {exec['result'][:200]}...\n\n"
        
        return explanation

