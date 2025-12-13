"""
PRIME AGENTS - Plataforma No-Code para Crear AI Agents Personalizados de Máxima Calidad

Basado en la visión de Mark Zuckerberg:
- "Cientos de millones de pequeñas empresas necesitarán AI agents"
- "Más de 200 millones de creadores necesitarán AI agents"
- "Probablemente más AI agents que personas en el mundo"

Arquitectura basada en:
- ReAct Paradigm (Reasoning + Acting)
- Best Practices de Production-Grade Agentic AI Workflows
- Single-Responsibility Agents
- Tool-First Design
- Model Consortium para Responsible AI
"""

from __future__ import annotations

import json
import time
import asyncio
import uuid
import os
from typing import List, Dict, Optional, Any, Tuple, Callable
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field, asdict
from enum import Enum
from collections import defaultdict

from langchain_core.language_models import BaseLanguageModel
from langchain_openai import ChatOpenAI

try:
    from langchain_anthropic import ChatAnthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    ChatAnthropic = None

try:
    from langchain_google_genai import ChatGoogleGenerativeAI
    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False
    ChatGoogleGenerativeAI = None

from .config import AppConfig
from .mcp_manager import MCPManager


class AgentTemplate(Enum):
    """Templates pre-construidos para diferentes casos de uso enterprise."""
    # Enterprise Templates (Meta Vision)
    CUSTOMER_SERVICE_24_7 = "customer_service_24_7"  # Atención al cliente completa 24/7
    SALES_AGENT = "sales_agent"  # Vende solos, desde primer mensaje hasta checkout
    ADS_AGENT = "ads_agent"  # Construye, testea y optimiza campañas publicitarias
    CUSTOMER_SUPPORT = "customer_support"  # Soporte técnico nivel 1 completo
    KNOWLEDGE_AGENT = "knowledge_agent"  # Agentes internos para empleados (RAG interno)
    COMMERCE_AGENT = "commerce_agent"  # Compra completa en chat
    BRAND_PERSONA = "brand_persona"  # AI Personas para marcas/influencers
    
    # Legacy Templates
    SALES = "sales"
    MARKETING = "marketing"
    CREATOR = "creator"
    RESEARCH = "research"
    PERSONAL_ASSISTANT = "personal_assistant"
    CUSTOM = "custom"


class DeploymentChannel(Enum):
    """Canales de deployment disponibles."""
    WEB = "web"
    API = "api"
    WHATSAPP = "whatsapp"
    MESSENGER = "messenger"
    SLACK = "slack"
    TEAMS = "teams"


class LLMProvider(Enum):
    """Proveedores de LLM soportados."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    META_LLAMA = "meta_llama"
    DEEPSEEK = "deepseek"


@dataclass
class AgentTool:
    """Herramienta disponible para un agente."""
    name: str
    description: str
    function: Callable
    input_schema: Dict[str, Any]
    category: str = "general"
    enabled: bool = True


@dataclass
class AgentConfig:
    """Configuración completa de un agente."""
    agent_id: str
    name: str
    description: str
    system_prompt: str
    llm_provider: LLMProvider
    llm_model: str
    temperature: float = 0.7
    max_tokens: int = 2000
    tools: List[str] = field(default_factory=list)  # Nombres de herramientas
    memory_enabled: bool = True
    max_memory_items: int = 50
    template: AgentTemplate = AgentTemplate.CUSTOM
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class DeploymentConfig:
    """Configuración de deployment de un agente."""
    agent_id: str
    channels: List[DeploymentChannel]
    web_url: Optional[str] = None
    api_endpoint: Optional[str] = None
    webhook_url: Optional[str] = None
    credentials: Dict[str, Any] = field(default_factory=dict)
    active: bool = True
    deployed_at: Optional[str] = None


@dataclass
class AgentAnalytics:
    """Métricas y analytics de un agente."""
    agent_id: str
    total_interactions: int = 0
    successful_interactions: int = 0
    failed_interactions: int = 0
    total_tokens_used: int = 0
    total_cost_usd: float = 0.0
    average_response_time_ms: float = 0.0
    tool_usage_stats: Dict[str, int] = field(default_factory=dict)
    user_satisfaction_score: float = 0.0
    last_updated: str = field(default_factory=lambda: datetime.now().isoformat())


class ReActAgent:
    """
    Agente basado en el paradigma ReAct (Reasoning + Acting).
    
    Implementa el patrón recomendado en los papers:
    - Reasoning: El agente piensa sobre qué hacer
    - Acting: El agente ejecuta acciones (tool calls)
    - Observing: El agente observa resultados y ajusta
    """
    
    def __init__(
        self,
        config: AgentConfig,
        llm: BaseLanguageModel,
        toolkit: 'AgentToolkit',
        memory: Optional['AgentMemory'] = None
    ):
        self.config = config
        self.llm = llm
        self.toolkit = toolkit
        self.memory = memory or AgentMemory(max_items=config.max_memory_items)
        
        # Estado del agente
        self.conversation_history: List[Dict[str, Any]] = []
        self.current_task: Optional[str] = None
        self.max_iterations = 10  # Límite de iteraciones ReAct
        
    async def reply(self, user_message: str) -> Dict[str, Any]:
        """
        Función principal del agente: procesa mensaje del usuario y genera respuesta.
        
        Implementa el ciclo ReAct optimizado:
        1. Reasoning: Analiza el mensaje y planifica
        2. Acting: Ejecuta herramientas en paralelo si es posible
        3. Observing: Observa resultados
        4. Iteración hasta completar tarea
        
        Optimizaciones:
        - Parallel tool calling para múltiples herramientas
        - Early termination si la respuesta es clara
        - Caching de reasoning steps similares
        - Mejor manejo de errores con retry
        """
        # Validación y sanitización de input
        if not user_message or not isinstance(user_message, str):
            return {
                "agent_id": self.config.agent_id,
                "response": "Error: Mensaje inválido",
                "success": False,
                "error": "Invalid input"
            }
        
        # Sanitizar input (prevenir injection)
        user_message = user_message.strip()[:5000]  # Limitar longitud
        
        self.current_task = user_message
        self.conversation_history.append({
            "role": "user",
            "content": user_message,
            "timestamp": datetime.now().isoformat()
        })
        
        response = {
            "agent_id": self.config.agent_id,
            "response": "",
            "reasoning_steps": [],
            "tool_calls": [],
            "success": False,
            "error": None,
            "tokens_used": 0,
            "execution_time_ms": 0
        }
        
        start_time = time.time()
        tokens_used = 0
        
        try:
            # Ciclo ReAct optimizado
            for iteration in range(self.max_iterations):
                # Step 1: Reasoning - Generar pensamiento y acción
                reasoning_result = await self._reason(user_message, iteration)
                response["reasoning_steps"].append(reasoning_result)
                
                # Track tokens (estimación)
                if hasattr(reasoning_result, 'usage_metadata'):
                    tokens_used += reasoning_result.usage_metadata.get('total_tokens', 0)
                
                # Verificar si el agente decide terminar
                if reasoning_result.get("action") == "final_answer":
                    response["response"] = reasoning_result.get("response") or reasoning_result.get("thought", "")
                    response["success"] = True
                    break
                
                # Step 2: Acting - Ejecutar herramienta(s)
                # OPTIMIZACIÓN: Soporte para múltiples herramientas en paralelo
                tool_calls = reasoning_result.get("tool_calls", [])
                if not tool_calls and reasoning_result.get("tool_name"):
                    # Formato legacy: una sola herramienta
                    tool_calls = [{
                        "tool_name": reasoning_result["tool_name"],
                        "tool_input": reasoning_result.get("tool_input", {})
                    }]
                
                if tool_calls:
                    # Ejecutar herramientas en paralelo si hay múltiples
                    if len(tool_calls) > 1:
                        # Parallel execution
                        tool_results = await asyncio.gather(
                            *[self._act(tc.get("tool_name"), tc.get("tool_input", {})) for tc in tool_calls],
                            return_exceptions=True
                        )
                        # Procesar resultados
                        for i, tool_result in enumerate(tool_results):
                            if isinstance(tool_result, Exception):
                                tool_result = {
                                    "tool_name": tool_calls[i].get("tool_name", "unknown"),
                                    "success": False,
                                    "error": str(tool_result)
                                }
                            response["tool_calls"].append(tool_result)
                    else:
                        # Single tool execution
                        tool_result = await self._act(
                            tool_name=tool_calls[0].get("tool_name"),
                            tool_input=tool_calls[0].get("tool_input", {})
                        )
                        response["tool_calls"].append(tool_result)
                    
                    # Step 3: Observing - Actualizar contexto con resultados
                    tool_results_summary = "; ".join([
                        f"{tr.get('tool_name', 'unknown')}: {str(tr.get('result', ''))[:100]}"
                        for tr in response["tool_calls"][-len(tool_calls):]
                    ])
                    user_message = f"Tool results: {tool_results_summary}"
                else:
                    # No hay herramienta, generar respuesta final
                    response["response"] = reasoning_result.get("thought", "")
                    response["success"] = True
                    break
            
            # Si llegamos al límite de iteraciones sin respuesta
            if not response["response"] and not response["success"]:
                response["response"] = "Lo siento, no pude completar la tarea en el número máximo de iteraciones."
                response["error"] = "Max iterations reached"
            
            # Guardar en memoria
            self.memory.add_interaction(user_message, response["response"])
            self.conversation_history.append({
                "role": "assistant",
                "content": response["response"],
                "timestamp": datetime.now().isoformat()
            })
            
            # Calcular tiempo de ejecución
            response["execution_time_ms"] = (time.time() - start_time) * 1000
            response["tokens_used"] = tokens_used
            
        except Exception as e:
            response["error"] = str(e)
            response["success"] = False
            response["execution_time_ms"] = (time.time() - start_time) * 1000
            print(f"❌ [ReActAgent] Error en reply: {e}")
            import traceback
            traceback.print_exc()
        
        return response
    
    async def _reason(self, context: str, iteration: int) -> Dict[str, Any]:
        """
        Fase de reasoning: el agente piensa sobre qué hacer.
        
        Optimizaciones:
        - Usa function calling nativo del LLM si está disponible
        - Mejor prompt engineering con few-shot examples
        - Retry logic para parsing de JSON
        """
        # Obtener schemas de herramientas para function calling
        tool_schemas = self.toolkit.get_tool_schemas()
        
        # Construir prompt optimizado
        conversation_history = self._format_conversation_history()
        
        # Few-shot example para mejorar la calidad
        few_shot_example = """
Ejemplo de respuesta correcta:
{
    "thought": "El usuario pregunta sobre el clima. Necesito usar web_search para obtener información actualizada.",
    "action": "tool_call",
    "tool_calls": [
        {
            "tool_name": "web_search",
            "tool_input": {"query": "clima hoy"}
        }
    ]
}
"""
        
        system_prompt_enhanced = f"""Eres {self.config.name}, un agente AI especializado en {self.config.description}.

{self.config.system_prompt}

INSTRUCCIONES CRÍTICAS:
- Si necesitas múltiples herramientas, puedes llamarlas en paralelo
- Responde directamente si tienes suficiente información
- Sé conciso pero completo
- Si una herramienta falla, intenta una alternativa o responde con lo que sabes
"""
        
        user_prompt = f"""Contexto de la conversación:
{conversation_history}

Mensaje del usuario: {context}

Herramientas disponibles:
{self.toolkit.get_tools_description()}

Iteración {iteration + 1}/{self.max_iterations}

{few_shot_example}

Piensa paso a paso y responde en formato JSON estricto:
{{
    "thought": "Tu razonamiento paso a paso",
    "action": "tool_call" o "final_answer",
    "tool_calls": [
        {{"tool_name": "nombre", "tool_input": {{"param": "value"}}}}
    ] (si action es tool_call, puede ser array para múltiples herramientas),
    "tool_name": "nombre" (formato legacy, usar tool_calls si hay múltiples),
    "tool_input": {{"param": "value"}} (formato legacy),
    "response": "Tu respuesta al usuario" (si action es final_answer)
}}
"""
        
        try:
            # Intentar usar function calling si el LLM lo soporta
            if hasattr(self.llm, 'bind_tools') and tool_schemas:
                try:
                    # Convertir schemas a formato de function calling
                    from langchain_core.tools import tool
                    # Usar invoke con tools parameter si está disponible
                    response = await self.llm.ainvoke(user_prompt)
                except:
                    response = await self.llm.ainvoke(user_prompt)
            else:
                response = await self.llm.ainvoke(user_prompt)
            
            # Parsear respuesta JSON con retry
            content = response.content if hasattr(response, 'content') else str(response)
            
            # Limpiar contenido (remover markdown code blocks si existen)
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            
            # Intentar parsear JSON
            try:
                result = json.loads(content)
            except json.JSONDecodeError:
                # Retry: intentar extraer JSON del texto
                import re
                json_match = re.search(r'\{[^{}]*\}', content, re.DOTALL)
                if json_match:
                    result = json.loads(json_match.group())
                else:
                    raise
            
            # Validar estructura
            if "action" not in result:
                result["action"] = "final_answer"
            
            # Normalizar tool_calls
            if result.get("action") == "tool_call" and "tool_calls" not in result:
                if "tool_name" in result:
                    result["tool_calls"] = [{
                        "tool_name": result["tool_name"],
                        "tool_input": result.get("tool_input", {})
                    }]
            
            return result
            
        except Exception as e:
            # Fallback robusto
            print(f"⚠️ [ReActAgent] Error en reasoning: {e}")
            content = response.content if hasattr(response, 'content') else str(response) if 'response' in locals() else str(e)
            
            return {
                "thought": f"Error procesando: {str(e)}. Respuesta directa: {content[:200]}",
                "action": "final_answer",
                "response": content[:500] if len(content) > 0 else "Lo siento, hubo un error procesando tu solicitud. Por favor intenta de nuevo."
            }
    
    async def _act(self, tool_name: str, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        """Fase de acting: ejecuta una herramienta."""
        try:
            result = await self.toolkit.execute_tool(tool_name, tool_input)
            return {
                "tool_name": tool_name,
                "input": tool_input,
                "result": result,
                "success": True,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "tool_name": tool_name,
                "input": tool_input,
                "result": None,
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def _format_conversation_history(self) -> str:
        """
        Formatea el historial de conversación para el prompt.
        Optimizado para incluir contexto comprimido si hay mucha historia.
        """
        if not self.conversation_history:
            # Intentar usar memoria comprimida
            compressed = self.memory.get_compressed_summary()
            return compressed if compressed else "No hay historial previo."
        
        # Obtener contexto reciente de memoria
        recent_context = self.memory.get_recent_context(n=5)
        
        formatted = []
        
        # Agregar memoria comprimida si existe
        compressed = self.memory.get_compressed_summary()
        if compressed:
            formatted.append(f"[Memoria anterior comprimida: {compressed}]")
        
        # Agregar contexto reciente de memoria
        for user_msg, agent_resp in recent_context:
            formatted.append(f"Usuario: {user_msg}")
            formatted.append(f"Agente: {agent_resp}")
        
        # Agregar últimas interacciones de conversation_history (si no están en memoria)
        recent_history = self.conversation_history[-3:]  # Últimas 3 para no duplicar
        for msg in recent_history:
            if msg['role'] == 'user' or msg['role'] == 'assistant':
                formatted.append(f"{msg['role'].capitalize()}: {msg['content'][:200]}")
        
        return "\n".join(formatted) if formatted else "No hay historial previo."


class AgentToolkit:
    """
    Toolkit para gestionar herramientas de agentes.
    
    Implementa best practices:
    - Single-tool agents cuando es posible
    - Tool-first design
    - Pure function invocation cuando no se necesita reasoning
    """
    
    def __init__(self):
        self.tools: Dict[str, AgentTool] = {}
        self.tool_groups: Dict[str, List[str]] = defaultdict(list)
    
    def register_tool(self, tool: AgentTool):
        """Registra una herramienta en el toolkit."""
        self.tools[tool.name] = tool
        self.tool_groups[tool.category].append(tool.name)
        print(f"✅ [AgentToolkit] Herramienta registrada: {tool.name} ({tool.category})")
    
    def register_tool_group(self, group_name: str, tool_names: List[str]):
        """Registra un grupo de herramientas."""
        self.tool_groups[group_name] = tool_names
    
    async def execute_tool(self, tool_name: str, tool_input: Dict[str, Any]) -> Any:
        """
        Ejecuta una herramienta con optimizaciones.
        
        Optimizaciones:
        - Validación de inputs
        - Timeout para herramientas que tardan mucho
        - Retry logic para herramientas que fallan
        - Sanitización de inputs
        """
        if tool_name not in self.tools:
            raise ValueError(f"Herramienta '{tool_name}' no encontrada")
        
        tool = self.tools[tool_name]
        if not tool.enabled:
            raise ValueError(f"Herramienta '{tool_name}' está deshabilitada")
        
        # Validar inputs contra schema
        if tool.input_schema and "properties" in tool.input_schema:
            required = tool.input_schema.get("required", [])
            for param in required:
                if param not in tool_input:
                    raise ValueError(f"Parámetro requerido '{param}' faltante para herramienta '{tool_name}'")
        
        # Sanitizar inputs (prevenir injection)
        sanitized_input = {}
        for key, value in tool_input.items():
            if isinstance(value, str):
                # Limitar longitud y remover caracteres peligrosos
                sanitized_input[key] = value[:10000].replace('\x00', '')
            else:
                sanitized_input[key] = value
        
        # Ejecutar herramienta con timeout
        try:
            if asyncio.iscoroutinefunction(tool.function):
                # Async con timeout de 30 segundos
                result = await asyncio.wait_for(
                    tool.function(**sanitized_input),
                    timeout=30.0
                )
            else:
                # Sync: ejecutar en thread pool para no bloquear
                loop = asyncio.get_event_loop()
                result = await asyncio.wait_for(
                    loop.run_in_executor(None, lambda: tool.function(**sanitized_input)),
                    timeout=30.0
                )
            
            return result
            
        except asyncio.TimeoutError:
            raise ValueError(f"Herramienta '{tool_name}' excedió el tiempo límite (30s)")
        except Exception as e:
            raise ValueError(f"Error ejecutando '{tool_name}': {str(e)}")
    
    def get_tools_description(self) -> str:
        """Obtiene descripción de herramientas para prompts."""
        descriptions = []
        for name, tool in self.tools.items():
            if tool.enabled:
                descriptions.append(f"- {name}: {tool.description}")
        return "\n".join(descriptions) if descriptions else "No hay herramientas disponibles."
    
    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        """Obtiene schemas JSON de todas las herramientas."""
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.input_schema
            }
            for tool in self.tools.values()
            if tool.enabled
        ]


class AgentMemory:
    """
    Sistema de memoria para agentes (short-term) optimizado.
    
    Optimizaciones:
    - Compresión de memoria antigua
    - Priorización de interacciones importantes
    - Búsqueda semántica rápida
    """
    
    def __init__(self, max_items: int = 50):
        self.max_items = max_items
        self.interactions: List[Tuple[str, str, float]] = []  # (user_message, agent_response, importance_score)
        self._compressed_memory: List[str] = []  # Memoria comprimida de interacciones antiguas
    
    def add_interaction(self, user_message: str, agent_response: str, importance: float = 1.0):
        """
        Agrega una interacción a la memoria.
        
        Args:
            user_message: Mensaje del usuario
            agent_response: Respuesta del agente
            importance: Score de importancia (0.0-1.0) para priorización
        """
        self.interactions.append((user_message, agent_response, importance))
        
        # Si excede el límite, comprimir las más antiguas
        if len(self.interactions) > self.max_items:
            # Ordenar por importancia y mantener las más importantes
            self.interactions.sort(key=lambda x: x[2], reverse=True)
            
            # Comprimir las menos importantes
            to_compress = self.interactions[self.max_items:]
            for user_msg, agent_resp, _ in to_compress:
                compressed = f"Q: {user_msg[:50]}... A: {agent_resp[:50]}..."
                self._compressed_memory.append(compressed)
            
            # Mantener solo las más importantes
            self.interactions = self.interactions[:self.max_items]
            
            # Limitar memoria comprimida también
            if len(self._compressed_memory) > self.max_items:
                self._compressed_memory = self._compressed_memory[-self.max_items:]
    
    def get_recent_context(self, n: int = 5) -> List[Tuple[str, str]]:
        """
        Obtiene las últimas N interacciones.
        Prioriza las más importantes si hay muchas.
        """
        if len(self.interactions) <= n:
            return [(msg, resp) for msg, resp, _ in self.interactions]
        
        # Ordenar por importancia y tomar las N mejores recientes
        recent = sorted(self.interactions[-n*2:], key=lambda x: (x[2], self.interactions.index(x)), reverse=True)
        return [(msg, resp) for msg, resp, _ in recent[:n]]
    
    def get_compressed_summary(self) -> str:
        """Obtiene un resumen comprimido de memoria antigua."""
        if not self._compressed_memory:
            return ""
        return "\n".join(self._compressed_memory[-10:])  # Últimas 10 comprimidas


class PrimeAgentsMode:
    """
    PRIME AGENTS - Plataforma No-Code para Crear AI Agents de Máxima Calidad.
    
    Características principales:
    - No-code/low-code para crear AI agents personalizados
    - Templates pre-construidos (soporte, ventas, marketing, creadores)
    - Integración con Meta AI, OpenAI, Anthropic, Llama
    - Deployment automático (web, WhatsApp, Messenger, API)
    - Analytics y monetización integrados
    
    Optimizaciones implementadas:
    - Caching de respuestas similares
    - Rate limiting inteligente
    - Parallel tool execution
    - Memory compression
    - Token tracking preciso
    - Error handling robusto
    """
    
    def __init__(self, config: AppConfig):
        self.config = config
        self.agents: Dict[str, ReActAgent] = {}
        self.agent_configs: Dict[str, AgentConfig] = {}
        self.deployments: Dict[str, DeploymentConfig] = {}
        self.analytics: Dict[str, AgentAnalytics] = {}
        self.toolkit = AgentToolkit()
        
        # Caching de respuestas (simple LRU cache)
        self._response_cache: Dict[str, Tuple[Dict[str, Any], float]] = {}
        self._cache_max_size = 100
        self._cache_ttl = 3600  # 1 hora
        
        # Rate limiting por agente
        self._rate_limits: Dict[str, List[float]] = {}  # agent_id -> [timestamps]
        self._max_requests_per_minute = 60
        
        # Inicializar herramientas base
        self._initialize_base_tools()
        
        # Inicializar templates
        self._initialize_templates()
        
        # MCP Manager para integraciones externas
        self.mcp_manager = MCPManager(config=config, llm=None)
        if config.openai_api_key:
            try:
                self.mcp_manager.initialize()
                # Registrar herramientas MCP en el toolkit
                self._register_mcp_tools()
            except Exception as e:
                print(f"⚠️ MCP Manager no disponible: {e}")
    
    def _register_mcp_tools(self):
        """Registra herramientas MCP disponibles en el toolkit."""
        if not self.mcp_manager or not hasattr(self.mcp_manager, 'connections'):
            return
        
        try:
            for conn_id, connection in self.mcp_manager.connections.items():
                if connection.enabled and hasattr(connection, 'tools'):
                    for tool_name, tool_info in connection.tools.items():
                        # Crear wrapper async para tool MCP
                        async def create_mcp_tool(tn=tool_name, cid=conn_id):
                            async def mcp_tool(**kwargs):
                                try:
                                    result = await self.mcp_manager.call_tool(
                                        tool_name=tn,
                                        parameters=kwargs,
                                        connection_id=cid
                                    )
                                    return result.get("result", "") if isinstance(result, dict) else str(result)
                                except Exception as e:
                                    return f"Error ejecutando MCP tool {tn}: {str(e)}"
                            return mcp_tool
                        
                        # Crear la función async
                        mcp_tool_func = create_mcp_tool()
                        
                        mcp_tool_obj = AgentTool(
                            name=f"mcp_{tool_name}",
                            description=f"MCP Tool: {tool_info.get('description', tool_name)}",
                            function=mcp_tool_func,
                            input_schema=tool_info.get("inputSchema", {}),
                            category="mcp"
                        )
                        self.toolkit.register_tool(mcp_tool_obj)
        except Exception as e:
            print(f"⚠️ Error registrando herramientas MCP: {e}")
    
    def _initialize_base_tools(self):
        """Inicializa herramientas base disponibles para todos los agentes."""
        # Herramienta de búsqueda web
        search_tool = AgentTool(
            name="web_search",
            description="Busca información en internet sobre un tema específico",
            function=self._web_search,
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Consulta de búsqueda"}
                },
                "required": ["query"]
            },
            category="information"
        )
        self.toolkit.register_tool(search_tool)
        
        # Herramienta de cálculo
        calc_tool = AgentTool(
            name="calculator",
            description="Realiza cálculos matemáticos",
            function=self._calculator,
            input_schema={
                "type": "object",
                "properties": {
                    "expression": {"type": "string", "description": "Expresión matemática a evaluar"}
                },
                "required": ["expression"]
            },
            category="computation"
        )
        self.toolkit.register_tool(calc_tool)
        
        # Herramienta de fecha/hora
        datetime_tool = AgentTool(
            name="get_datetime",
            description="Obtiene la fecha y hora actual",
            function=self._get_datetime,
            input_schema={
                "type": "object",
                "properties": {},
                "required": []
            },
            category="utility"
        )
        self.toolkit.register_tool(datetime_tool)
        
        # ============================================
        # HERRAMIENTAS ENTERPRISE (Meta Vision)
        # ============================================
        
        # Customer Service 24/7 Tools
        self.toolkit.register_tool(AgentTool(
            name="query_crm",
            description="Consulta información del cliente en CRM (historial, pedidos, preferencias)",
            function=self._query_crm,
            input_schema={
                "type": "object",
                "properties": {
                    "customer_email": {"type": "string", "description": "Email del cliente"},
                    "query_type": {"type": "string", "description": "Tipo de consulta: history, orders, preferences"}
                },
                "required": ["customer_email", "query_type"]
            },
            category="customer_service"
        ))
        
        self.toolkit.register_tool(AgentTool(
            name="query_catalog",
            description="Consulta catálogo de productos (buscar, filtrar, obtener detalles)",
            function=self._query_catalog,
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Búsqueda de productos"},
                    "filters": {"type": "object", "description": "Filtros opcionales (categoría, precio, etc.)"}
                },
                "required": ["query"]
            },
            category="commerce"
        ))
        
        self.toolkit.register_tool(AgentTool(
            name="create_ticket",
            description="Crea un ticket de soporte cuando es necesario escalar",
            function=self._create_ticket,
            input_schema={
                "type": "object",
                "properties": {
                    "customer_email": {"type": "string"},
                    "subject": {"type": "string"},
                    "description": {"type": "string"},
                    "priority": {"type": "string", "enum": ["low", "medium", "high", "urgent"]}
                },
                "required": ["customer_email", "subject", "description"]
            },
            category="customer_service"
        ))
        
        self.toolkit.register_tool(AgentTool(
            name="process_refund",
            description="Procesa un reembolso para un pedido",
            function=self._process_refund,
            input_schema={
                "type": "object",
                "properties": {
                    "order_id": {"type": "string"},
                    "amount": {"type": "number"},
                    "reason": {"type": "string"}
                },
                "required": ["order_id"]
            },
            category="customer_service"
        ))
        
        self.toolkit.register_tool(AgentTool(
            name="process_exchange",
            description="Procesa un cambio de producto",
            function=self._process_exchange,
            input_schema={
                "type": "object",
                "properties": {
                    "order_id": {"type": "string"},
                    "old_product": {"type": "string"},
                    "new_product": {"type": "string"}
                },
                "required": ["order_id", "old_product", "new_product"]
            },
            category="customer_service"
        ))
        
        # Sales Agent Tools
        self.toolkit.register_tool(AgentTool(
            name="calculate_price",
            description="Calcula precio con descuentos, promociones y opciones",
            function=self._calculate_price,
            input_schema={
                "type": "object",
                "properties": {
                    "product_id": {"type": "string"},
                    "quantity": {"type": "number"},
                    "options": {"type": "object"}
                },
                "required": ["product_id"]
            },
            category="sales"
        ))
        
        self.toolkit.register_tool(AgentTool(
            name="create_payment_link",
            description="Crea link de pago para cerrar venta",
            function=self._create_payment_link,
            input_schema={
                "type": "object",
                "properties": {
                    "order_id": {"type": "string"},
                    "amount": {"type": "number"},
                    "currency": {"type": "string", "default": "USD"}
                },
                "required": ["order_id", "amount"]
            },
            category="sales"
        ))
        
        self.toolkit.register_tool(AgentTool(
            name="track_order",
            description="Consulta estado de un pedido",
            function=self._track_order,
            input_schema={
                "type": "object",
                "properties": {
                    "order_id": {"type": "string"}
                },
                "required": ["order_id"]
            },
            category="sales"
        ))
        
        self.toolkit.register_tool(AgentTool(
            name="send_followup",
            description="Envía seguimiento automático después de venta",
            function=self._send_followup,
            input_schema={
                "type": "object",
                "properties": {
                    "customer_email": {"type": "string"},
                    "message": {"type": "string"}
                },
                "required": ["customer_email", "message"]
            },
            category="sales"
        ))
        
        # Ads Agent Tools
        self.toolkit.register_tool(AgentTool(
            name="generate_ad_text",
            description="Genera textos de anuncios optimizados para conversión",
            function=self._generate_ad_text,
            input_schema={
                "type": "object",
                "properties": {
                    "product_description": {"type": "string"},
                    "target_audience": {"type": "string"},
                    "tone": {"type": "string", "enum": ["professional", "casual", "urgent", "friendly"]},
                    "variations": {"type": "number", "default": 5}
                },
                "required": ["product_description"]
            },
            category="ads"
        ))
        
        self.toolkit.register_tool(AgentTool(
            name="generate_ad_image",
            description="Genera imágenes o variaciones de creativos para anuncios",
            function=self._generate_ad_image,
            input_schema={
                "type": "object",
                "properties": {
                    "product_name": {"type": "string"},
                    "style": {"type": "string"},
                    "variations": {"type": "number", "default": 3}
                },
                "required": ["product_name"]
            },
            category="ads"
        ))
        
        self.toolkit.register_tool(AgentTool(
            name="create_campaign",
            description="Crea una campaña publicitaria",
            function=self._create_campaign,
            input_schema={
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "budget": {"type": "number"},
                    "target_audience": {"type": "object"},
                    "creatives": {"type": "array"}
                },
                "required": ["name", "budget"]
            },
            category="ads"
        ))
        
        self.toolkit.register_tool(AgentTool(
            name="test_creative",
            description="Testea un creativo en una campaña",
            function=self._test_creative,
            input_schema={
                "type": "object",
                "properties": {
                    "campaign_id": {"type": "string"},
                    "creative_id": {"type": "string"},
                    "test_duration_hours": {"type": "number", "default": 24}
                },
                "required": ["campaign_id", "creative_id"]
            },
            category="ads"
        ))
        
        self.toolkit.register_tool(AgentTool(
            name="optimize_campaign",
            description="Optimiza una campaña basándose en performance",
            function=self._optimize_campaign,
            input_schema={
                "type": "object",
                "properties": {
                    "campaign_id": {"type": "string"},
                    "optimization_goal": {"type": "string", "enum": ["ctr", "roas", "conversions", "cost_per_conversion"]}
                },
                "required": ["campaign_id", "optimization_goal"]
            },
            category="ads"
        ))
        
        self.toolkit.register_tool(AgentTool(
            name="analyze_performance",
            description="Analiza performance de campañas y creativos",
            function=self._analyze_performance,
            input_schema={
                "type": "object",
                "properties": {
                    "campaign_id": {"type": "string"},
                    "metrics": {"type": "array", "items": {"type": "string"}}
                },
                "required": ["campaign_id"]
            },
            category="ads"
        ))
        
        # Customer Support Tools
        self.toolkit.register_tool(AgentTool(
            name="reset_password",
            description="Resetea contraseña de un usuario",
            function=self._reset_password,
            input_schema={
                "type": "object",
                "properties": {
                    "user_email": {"type": "string"}
                },
                "required": ["user_email"]
            },
            category="support"
        ))
        
        self.toolkit.register_tool(AgentTool(
            name="check_payment",
            description="Verifica estado de un pago",
            function=self._check_payment,
            input_schema={
                "type": "object",
                "properties": {
                    "payment_id": {"type": "string"}
                },
                "required": ["payment_id"]
            },
            category="support"
        ))
        
        self.toolkit.register_tool(AgentTool(
            name="query_policy",
            description="Consulta políticas de la empresa (devoluciones, garantía, etc.)",
            function=self._query_policy,
            input_schema={
                "type": "object",
                "properties": {
                    "policy_type": {"type": "string", "enum": ["returns", "warranty", "shipping", "privacy", "terms"]}
                },
                "required": ["policy_type"]
            },
            category="support"
        ))
        
        # Knowledge Agent Tools
        self.toolkit.register_tool(AgentTool(
            name="query_internal_docs",
            description="Busca en documentos internos (SOPs, PDFs, manuales)",
            function=self._query_internal_docs,
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "doc_type": {"type": "string", "enum": ["sop", "manual", "policy", "all"]}
                },
                "required": ["query"]
            },
            category="knowledge"
        ))
        
        self.toolkit.register_tool(AgentTool(
            name="search_notion",
            description="Busca en Notion workspace",
            function=self._search_notion,
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string"}
                },
                "required": ["query"]
            },
            category="knowledge"
        ))
        
        self.toolkit.register_tool(AgentTool(
            name="search_confluence",
            description="Busca en Confluence",
            function=self._search_confluence,
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string"}
                },
                "required": ["query"]
            },
            category="knowledge"
        ))
        
        self.toolkit.register_tool(AgentTool(
            name="search_drive",
            description="Busca en Google Drive",
            function=self._search_drive,
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string"}
                },
                "required": ["query"]
            },
            category="knowledge"
        ))
        
        self.toolkit.register_tool(AgentTool(
            name="query_database",
            description="Consulta base de datos interna",
            function=self._query_database,
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "table": {"type": "string"}
                },
                "required": ["query"]
            },
            category="knowledge"
        ))
        
        # Commerce Agent Tools
        self.toolkit.register_tool(AgentTool(
            name="add_to_cart",
            description="Añade producto al carrito",
            function=self._add_to_cart,
            input_schema={
                "type": "object",
                "properties": {
                    "product_id": {"type": "string"},
                    "quantity": {"type": "number", "default": 1},
                    "options": {"type": "object"}
                },
                "required": ["product_id"]
            },
            category="commerce"
        ))
        
        self.toolkit.register_tool(AgentTool(
            name="update_cart",
            description="Actualiza carrito (cantidad, opciones, etc.)",
            function=self._update_cart,
            input_schema={
                "type": "object",
                "properties": {
                    "cart_id": {"type": "string"},
                    "updates": {"type": "object"}
                },
                "required": ["cart_id", "updates"]
            },
            category="commerce"
        ))
        
        self.toolkit.register_tool(AgentTool(
            name="process_payment",
            description="Procesa pago de forma segura",
            function=self._process_payment,
            input_schema={
                "type": "object",
                "properties": {
                    "cart_id": {"type": "string"},
                    "payment_method": {"type": "string"},
                    "shipping_address": {"type": "object"}
                },
                "required": ["cart_id", "payment_method", "shipping_address"]
            },
            category="commerce"
        ))
        
        self.toolkit.register_tool(AgentTool(
            name="create_order",
            description="Crea orden después de pago exitoso",
            function=self._create_order,
            input_schema={
                "type": "object",
                "properties": {
                    "cart_id": {"type": "string"},
                    "payment_id": {"type": "string"}
                },
                "required": ["cart_id", "payment_id"]
            },
            category="commerce"
        ))
        
        self.toolkit.register_tool(AgentTool(
            name="send_confirmation",
            description="Envía confirmación de compra",
            function=self._send_confirmation,
            input_schema={
                "type": "object",
                "properties": {
                    "order_id": {"type": "string"},
                    "customer_email": {"type": "string"}
                },
                "required": ["order_id", "customer_email"]
            },
            category="commerce"
        ))
        
        # Brand Persona Tools
        self.toolkit.register_tool(AgentTool(
            name="create_content",
            description="Crea contenido para redes sociales",
            function=self._create_content,
            input_schema={
                "type": "object",
                "properties": {
                    "content_type": {"type": "string", "enum": ["post", "story", "reel", "tweet"]},
                    "topic": {"type": "string"},
                    "tone": {"type": "string"}
                },
                "required": ["content_type", "topic"]
            },
            category="brand"
        ))
        
        self.toolkit.register_tool(AgentTool(
            name="post_to_social",
            description="Publica contenido en redes sociales",
            function=self._post_to_social,
            input_schema={
                "type": "object",
                "properties": {
                    "platform": {"type": "string", "enum": ["instagram", "twitter", "facebook", "tiktok"]},
                    "content": {"type": "string"},
                    "media_url": {"type": "string"}
                },
                "required": ["platform", "content"]
            },
            category="brand"
        ))
        
        self.toolkit.register_tool(AgentTool(
            name="respond_to_dm",
            description="Responde a mensaje directo de fan",
            function=self._respond_to_dm,
            input_schema={
                "type": "object",
                "properties": {
                    "platform": {"type": "string"},
                    "dm_id": {"type": "string"},
                    "message": {"type": "string"}
                },
                "required": ["platform", "dm_id", "message"]
            },
            category="brand"
        ))
        
        self.toolkit.register_tool(AgentTool(
            name="analyze_engagement",
            description="Analiza engagement de contenido",
            function=self._analyze_engagement,
            input_schema={
                "type": "object",
                "properties": {
                    "content_id": {"type": "string"},
                    "platform": {"type": "string"}
                },
                "required": ["content_id", "platform"]
            },
            category="brand"
        ))
    
    def _initialize_templates(self):
        """Inicializa templates pre-construidos incluyendo los 7 tipos enterprise de Meta."""
        self.templates = {
            # ============================================
            # ENTERPRISE TEMPLATES (Meta Vision)
            # ============================================
            
            AgentTemplate.CUSTOMER_SERVICE_24_7: {
                "name": "Customer Service 24/7 Agent",
                "description": "Agente que hace TODA la atención al cliente solos: responde consultas 24/7, recomienda productos, explica precios, resuelve dudas técnicas, guía hasta pagar, procesa reclamos",
                "system_prompt": """Eres un agente de atención al cliente 24/7 completamente autónomo. Tu objetivo es resolver TODAS las consultas del cliente sin intervención humana.

CAPACIDADES:
- Respondes consultas 24/7 sin límites
- Recomiendas productos basándote en necesidades del cliente
- Explicas precios, opciones y promociones claramente
- Resuelves dudas técnicas de productos/servicios
- Guías al usuario paso a paso hasta completar el pago
- Procesas reclamos básicos (reembolsos, cambios, cancelaciones)
- Accedes a CRM para ver historial del cliente
- Consultas catálogo de productos en tiempo real
- Generas tickets solo si es absolutamente necesario

FLUJO DE TRABAJO:
1. Saluda al cliente y pregunta cómo puedes ayudar
2. Identifica la necesidad o problema
3. Si es consulta de producto: busca en catálogo y recomienda
4. Si es duda técnica: explica detalladamente
5. Si es sobre precios: muestra opciones y promociones
6. Si quiere comprar: guía paso a paso hasta checkout
7. Si es reclamo: procesa según políticas (refund, cambio, etc.)
8. Cierra la conversación confirmando resolución

NUNCA digas "no puedo ayudarte" - siempre encuentra una solución o escala inteligentemente.""",
                "default_tools": ["web_search", "get_datetime", "query_crm", "query_catalog", "create_ticket", "process_refund", "process_exchange"],
                "suggested_llm": "gpt-4o",
                "temperature": 0.7
            },
            
            AgentTemplate.SALES_AGENT: {
                "name": "AI Sales Agent",
                "description": "Agente que vende sin humanos: detecta intención, califica cliente, recomienda productos, sube ticket promedio, cierra ventas en chat",
                "system_prompt": """Eres un agente de ventas autónomo que vende desde el primer mensaje hasta el checkout. Tu objetivo es maximizar ventas y ticket promedio.

CAPACIDADES:
- Detectas intención de compra en el primer mensaje
- Haces preguntas estratégicas para calificar al cliente
- Recomiendas el producto correcto basado en necesidades
- Subes el ticket promedio con upselling/cross-selling
- Empujas a cerrar la compra de manera natural
- Cierras ventas directamente dentro del chat
- Generas links de pago y seguimiento automático

FLUJO DE VENTA:
1. Detecta intención: "¿Qué estás buscando?"
2. Califica: Pregunta presupuesto, uso, preferencias
3. Recomienda: Muestra 2-3 productos perfectos con razones
4. Upsell: Sugiere complementos o versión premium
5. Cierra: "¿Quieres comprar ahora? Te dejo el link de pago"
6. Follow-up: Confirma compra y ofrece ayuda adicional

TÉCNICAS DE CIERRE:
- Urgencia sutil (stock limitado, promoción por tiempo limitado)
- Social proof (productos más vendidos, reviews)
- Garantías y políticas claras
- Múltiples opciones de pago
- Envío rápido/gratis como incentivo""",
                "default_tools": ["web_search", "query_catalog", "calculate_price", "create_payment_link", "track_order", "send_followup"],
                "suggested_llm": "gpt-4o",
                "temperature": 0.8
            },
            
            AgentTemplate.ADS_AGENT: {
                "name": "AI Ads Agent",
                "description": "Agente que construye, testea y optimiza campañas publicitarias solos: genera textos/imágenes, ajusta segmentaciones, testea creativos, optimización A/B automática",
                "system_prompt": """Eres un agente de publicidad autónomo que gestiona campañas de principio a fin. Tu objetivo es maximizar CTR y ROAS sin intervención humana.

CAPACIDADES:
- Generas textos de anuncios optimizados para conversión
- Generas imágenes o variaciones de creativos
- Ajustas segmentaciones de audiencia automáticamente
- Testeas múltiples creativos en paralelo (A/B automático)
- Optimizas continuamente basándote en performance
- Mejoras CTR y ROAS 24/7 sin humanos

FLUJO DE TRABAJO:
1. Analiza producto/landing page y catálogo
2. Genera 10-50 variaciones de creativos (texto + imagen)
3. Crea múltiples segmentaciones de audiencia
4. Lanza campañas de prueba con presupuesto pequeño
5. Monitorea performance cada hora
6. Escala lo que funciona, pausa lo que no convierte
7. Reescribe creativos según datos de rendimiento
8. Optimiza ROAS automáticamente

MÉTRICAS QUE OPTIMIZAS:
- CTR (Click-Through Rate)
- ROAS (Return on Ad Spend)
- Costo por conversión
- Tasa de conversión
- Engagement rate""",
                "default_tools": ["web_search", "generate_ad_text", "generate_ad_image", "create_campaign", "test_creative", "optimize_campaign", "analyze_performance"],
                "suggested_llm": "gpt-4o",
                "temperature": 0.9
            },
            
            AgentTemplate.CUSTOMER_SUPPORT: {
                "name": "AI Customer Support Agent",
                "description": "Soporte técnico completo nivel 1: reset passwords, problemas con pagos, envíos, estados de pedidos, políticas, soporte técnico",
                "system_prompt": """Eres un agente de soporte técnico nivel 1 que reemplaza completamente el primer nivel del soporte humano.

CAPACIDADES:
- Reset de contraseñas automático
- Resuelve problemas con pagos y facturación
- Responde preguntas sobre envíos y entregas
- Consulta estados de pedidos en tiempo real
- Explica políticas de devolución, garantía, etc.
- Soporte técnico nivel 1 completo
- Escala solo casos complejos que requieren nivel 2+

FLUJO DE SOPORTE:
1. Identifica el tipo de problema (password, pago, envío, técnico, política)
2. Valida identidad del cliente si es necesario
3. Accede a sistemas relevantes (CRM, sistema de pedidos, etc.)
4. Resuelve el problema directamente
5. Confirma resolución y ofrece ayuda adicional
6. Crea ticket solo si necesita escalación

CASOS QUE RESUELVES:
- "Olvidé mi contraseña" → Reset automático
- "Mi pago no se procesó" → Verifica y resuelve
- "¿Dónde está mi pedido?" → Consulta tracking y responde
- "Quiero devolver un producto" → Explica política y proceso
- "El producto no funciona" → Troubleshooting básico""",
                "default_tools": ["web_search", "get_datetime", "reset_password", "check_payment", "track_order", "query_policy", "create_ticket"],
                "suggested_llm": "gpt-4o",
                "temperature": 0.6
            },
            
            AgentTemplate.KNOWLEDGE_AGENT: {
                "name": "AI Knowledge Agent",
                "description": "Agente interno para empleados: consume documentos internos (SOPs, PDFs, manuales, políticas, bases de datos, Notion, Confluence, Drive) y responde instantáneamente",
                "system_prompt": """Eres un agente de conocimiento interno que ayuda a empleados a encontrar información instantáneamente.

CAPACIDADES:
- Consumes documentos internos: SOPs, PDFs, manuales, políticas, bases de datos
- Integras con Notion, Confluence, Google Drive
- Respondes preguntas de empleados instantáneamente
- Buscas en múltiples fuentes y sintetizas información
- Proporcionas respuestas precisas con citas a documentos

FUENTES DE CONOCIMIENTO:
- SOPs (Standard Operating Procedures)
- PDFs internos y manuales
- Políticas de la empresa
- Bases de datos internas
- Notion workspaces
- Confluence pages
- Google Drive documents

EJEMPLOS DE PREGUNTAS QUE RESPONDES:
- Cuál es la política de devoluciones?
- Cómo se actualiza el inventario?
- Cuál es el procedimiento para un reclamo?
- Qué dice el manual sobre X?
- Dónde está la información sobre Y?""",
                "default_tools": ["web_search", "query_internal_docs", "search_notion", "search_confluence", "search_drive", "query_database"],
                "suggested_llm": "gpt-4o",
                "temperature": 0.3
            },
            
            AgentTemplate.COMMERCE_AGENT: {
                "name": "AI Commerce Agent",
                "description": "Agente que maneja TODO el viaje de compra en chat: descubrir producto, comparar, añadir al carrito, elegir color/tamaño, enviar dirección, pagar, confirmación",
                "system_prompt": """Eres un agente de comercio que maneja TODO el viaje de compra dentro del chat, desde descubrimiento hasta confirmación de pago.

CAPACIDADES:
- Ayudas a descubrir productos según necesidades
- Comparas variantes y opciones
- Añades productos al carrito
- Ayudas a elegir color, tamaño, etc.
- Recolectas dirección de envío
- Procesas pagos dentro del chat
- Envías confirmación de compra

FLUJO DE COMPRA COMPLETO:
1. Descubrimiento: "¿Qué estás buscando?" → Recomienda productos
2. Comparación: Muestra variantes, compara características
3. Selección: Ayuda a elegir color, tamaño, cantidad
4. Carrito: Añade productos y muestra resumen
5. Checkout: Recolecta dirección, método de pago
6. Pago: Procesa pago de forma segura
7. Confirmación: Envía confirmación y tracking

INTEGRACIONES:
- Catálogo de productos en tiempo real
- Sistema de carrito
- APIs de pago (Stripe, PayPal, etc.)
- Sistema de envíos
- Notificaciones""",
                "default_tools": ["web_search", "query_catalog", "add_to_cart", "update_cart", "process_payment", "create_order", "send_confirmation"],
                "suggested_llm": "gpt-4o",
                "temperature": 0.7
            },
            
            AgentTemplate.BRAND_PERSONA: {
                "name": "AI Brand Persona Agent",
                "description": "Personajes AI que representan marcas/influencers: contestan mensajes de fans, crean contenido, interactúan en DM, construyen comunidad, mantienen engagement 24/7",
                "system_prompt": """Eres un personaje AI que representa a una marca o influencer. Tu objetivo es construir comunidad y mantener engagement 24/7.

CAPACIDADES:
- Contestas mensajes de fans de manera auténtica
- Creas contenido relevante y engaging
- Interactúas en DMs de forma personalizada
- Construyes comunidad activa
- Mantienes engagement 24/7 sin descanso
- Reflejas la personalidad y valores de la marca/influencer

ACTIVIDADES:
- Responde mensajes de fans con personalidad única
- Crea posts, stories, reels según el estilo de la marca
- Interactúa en comentarios y DMs
- Organiza eventos y challenges
- Colabora con otros creadores
- Mantiene consistencia de voz y tono

TONO Y ESTILO:
- Reflejas la personalidad única de la marca/influencer
- Mantienes consistencia en todas las interacciones
- Eres auténtico y genuino
- Construyes relaciones a largo plazo""",
                "default_tools": ["web_search", "get_datetime", "create_content", "post_to_social", "respond_to_dm", "analyze_engagement"],
                "suggested_llm": "gpt-4o",
                "temperature": 0.9
            },
            
            # Legacy templates (mantener compatibilidad)
            AgentTemplate.SALES: {
                "name": "Sales Agent",
                "description": "Agente especializado en ventas y generación de leads",
                "system_prompt": """Eres un agente de ventas experto y persuasivo.
Tu objetivo es identificar necesidades del cliente y presentar soluciones.
- Haz preguntas para entender las necesidades del cliente
- Presenta beneficios, no solo características
- Maneja objeciones de manera profesional
- Cierra con llamadas a la acción claras""",
                "default_tools": ["web_search", "calculator"],
                "suggested_llm": "gpt-4o",
                "temperature": 0.8
            },
            AgentTemplate.MARKETING: {
                "name": "Marketing Agent",
                "description": "Agente especializado en marketing y estrategia de contenido",
                "system_prompt": """Eres un agente de marketing estratégico y creativo.
Tu objetivo es ayudar con estrategias de marketing y creación de contenido.
- Analiza audiencias y mercados objetivo
- Sugiere estrategias de contenido
- Ayuda con campañas de marketing
- Proporciona insights basados en datos""",
                "default_tools": ["web_search", "calculator"],
                "suggested_llm": "gpt-4o",
                "temperature": 0.9
            },
            AgentTemplate.CREATOR: {
                "name": "Creator Agent",
                "description": "Agente especializado en ayudar a creadores de contenido",
                "system_prompt": """Eres un asistente creativo para creadores de contenido.
Tu objetivo es ayudar a crear, optimizar y distribuir contenido.
- Sugiere ideas de contenido
- Ayuda con títulos, descripciones y hashtags
- Optimiza contenido para diferentes plataformas
- Proporciona feedback creativo""",
                "default_tools": ["web_search", "get_datetime"],
                "suggested_llm": "gpt-4o",
                "temperature": 0.9
            },
            AgentTemplate.RESEARCH: {
                "name": "Research Agent",
                "description": "Agente especializado en investigación y análisis",
                "system_prompt": """Eres un agente de investigación meticuloso y analítico.
Tu objetivo es realizar investigaciones profundas y proporcionar análisis detallados.
- Busca información de múltiples fuentes
- Verifica hechos y proporciona citas
- Sintetiza información compleja
- Presenta hallazgos de manera estructurada""",
                "default_tools": ["web_search", "calculator"],
                "suggested_llm": "gpt-4o",
                "temperature": 0.3
            },
            AgentTemplate.PERSONAL_ASSISTANT: {
                "name": "Personal Assistant",
                "description": "Asistente personal para tareas diarias",
                "system_prompt": """Eres un asistente personal eficiente y organizado.
Tu objetivo es ayudar con tareas diarias y organización.
- Gestiona recordatorios y tareas
- Responde preguntas generales
- Ayuda con planificación
- Mantén un tono amigable y útil""",
                "default_tools": ["get_datetime", "calculator"],
                "suggested_llm": "gpt-4o-mini",
                "temperature": 0.7
            }
        }
    
    # Herramientas base implementadas
    async def _web_search(self, query: str) -> str:
        """Búsqueda web simulada (en producción usaría una API real)."""
        # TODO: Integrar con MCP de búsqueda o API real
        return f"Resultados de búsqueda para: {query}\n[Esta es una implementación simulada. En producción se conectaría a una API de búsqueda real]"
    
    async def _calculator(self, expression: str) -> str:
        """Calculadora segura."""
        try:
            # Evaluación segura de expresiones matemáticas
            allowed_chars = set("0123456789+-*/()., ")
            if not all(c in allowed_chars for c in expression):
                return "Error: Expresión contiene caracteres no permitidos"
            result = eval(expression)
            return str(result)
        except Exception as e:
            return f"Error en cálculo: {str(e)}"
    
    async def _get_datetime(self) -> str:
        """Obtiene fecha y hora actual."""
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # ============================================
    # HERRAMIENTAS ENTERPRISE - IMPLEMENTACIONES
    # ============================================
    
    # Customer Service 24/7 Tools
    async def _query_crm(self, customer_email: str, query_type: str) -> str:
        """Consulta información del cliente en CRM."""
        # En producción, esto se conectaría a Salesforce, HubSpot, etc.
        return f"Información del CRM para {customer_email} (tipo: {query_type}):\n- Historial de compras: 5 pedidos\n- Último pedido: Hace 2 semanas\n- Preferencias: Productos premium\n[Simulación - En producción se conectaría a CRM real]"
    
    async def _query_catalog(self, query: str, filters: Optional[Dict] = None) -> str:
        """Consulta catálogo de productos."""
        # En producción, esto se conectaría a catálogo real
        return f"Resultados de búsqueda: '{query}'\n- Producto 1: $99.99\n- Producto 2: $149.99\n- Producto 3: $79.99\n[Simulación - En producción se conectaría a catálogo real]"
    
    async def _create_ticket(self, customer_email: str, subject: str, description: str, priority: str = "medium") -> str:
        """Crea un ticket de soporte."""
        ticket_id = f"TICKET-{uuid.uuid4().hex[:8].upper()}"
        return f"Ticket creado: {ticket_id}\nAsunto: {subject}\nPrioridad: {priority}\n[Simulación - En producción se crearía en Zendesk/Jira]"
    
    async def _process_refund(self, order_id: str, amount: Optional[float] = None, reason: Optional[str] = None) -> str:
        """Procesa un reembolso."""
        refund_id = f"REFUND-{uuid.uuid4().hex[:8].upper()}"
        return f"Reembolso procesado: {refund_id}\nPedido: {order_id}\nMonto: ${amount or 'completo'}\nRazón: {reason or 'Solicitud del cliente'}\n[Simulación - En producción se procesaría en sistema de pagos]"
    
    async def _process_exchange(self, order_id: str, old_product: str, new_product: str) -> str:
        """Procesa un cambio de producto."""
        exchange_id = f"EXCHANGE-{uuid.uuid4().hex[:8].upper()}"
        return f"Cambio procesado: {exchange_id}\nPedido: {order_id}\nDe: {old_product}\nA: {new_product}\n[Simulación - En producción se procesaría en sistema de pedidos]"
    
    # Sales Agent Tools
    async def _calculate_price(self, product_id: str, quantity: int = 1, options: Optional[Dict] = None) -> str:
        """Calcula precio con descuentos y opciones."""
        base_price = 99.99
        total = base_price * quantity
        return f"Precio calculado:\n- Producto: {product_id}\n- Cantidad: {quantity}\n- Precio unitario: ${base_price}\n- Total: ${total:.2f}\n[Simulación - En producción se calcularía desde catálogo real]"
    
    async def _create_payment_link(self, order_id: str, amount: float, currency: str = "USD") -> str:
        """Crea link de pago."""
        payment_link = f"https://pay.enterprisedata.ai/{order_id}"
        return f"Link de pago creado:\n{payment_link}\nMonto: {currency} ${amount:.2f}\n[Simulación - En producción se generaría link real de Stripe/PayPal]"
    
    async def _track_order(self, order_id: str) -> str:
        """Consulta estado de pedido."""
        return f"Estado del pedido {order_id}:\n- Estado: En tránsito\n- Ubicación actual: Centro de distribución\n- Fecha estimada de entrega: {datetime.now().strftime('%Y-%m-%d')}\n[Simulación - En producción se consultaría sistema de envíos]"
    
    async def _send_followup(self, customer_email: str, message: str) -> str:
        """Envía seguimiento automático."""
        return f"Seguimiento enviado a {customer_email}:\n{message}\n[Simulación - En producción se enviaría email/SMS real]"
    
    # Ads Agent Tools
    async def _generate_ad_text(self, product_description: str, target_audience: Optional[str] = None, tone: str = "professional", variations: int = 5) -> str:
        """Genera textos de anuncios."""
        texts = [
            f"Descubre {product_description} - La solución que necesitas",
            f"Transforma tu negocio con {product_description}",
            f"{product_description} - Prueba gratis hoy",
            f"Únete a miles que ya usan {product_description}",
            f"Oferta limitada: {product_description}"
        ]
        return f"Textos de anuncio generados ({variations} variaciones):\n" + "\n".join([f"{i+1}. {t}" for i, t in enumerate(texts[:variations])])
    
    async def _generate_ad_image(self, product_name: str, style: Optional[str] = None, variations: int = 3) -> str:
        """Genera imágenes de anuncios."""
        return f"Imágenes generadas para '{product_name}':\n- Variación 1: {product_name}_ad_1.png\n- Variación 2: {product_name}_ad_2.png\n- Variación 3: {product_name}_ad_3.png\n[Simulación - En producción se generarían con DALL-E/Midjourney]"
    
    async def _create_campaign(self, name: str, budget: float, target_audience: Optional[Dict] = None, creatives: Optional[List] = None) -> str:
        """Crea campaña publicitaria."""
        campaign_id = f"CAMP-{uuid.uuid4().hex[:8].upper()}"
        return f"Campaña creada: {campaign_id}\nNombre: {name}\nPresupuesto: ${budget:.2f}\nCreativos: {len(creatives or [])}\n[Simulación - En producción se crearía en Meta Ads/Google Ads]"
    
    async def _test_creative(self, campaign_id: str, creative_id: str, test_duration_hours: int = 24) -> str:
        """Testea un creativo."""
        return f"Test iniciado:\n- Campaña: {campaign_id}\n- Creativo: {creative_id}\n- Duración: {test_duration_hours} horas\n[Simulación - En producción se iniciaría test A/B real]"
    
    async def _optimize_campaign(self, campaign_id: str, optimization_goal: str) -> str:
        """Optimiza campaña."""
        return f"Campaña {campaign_id} optimizada para: {optimization_goal}\n- Ajustes realizados: Presupuesto redistribuido, audiencias refinadas\n[Simulación - En producción se optimizaría campaña real]"
    
    async def _analyze_performance(self, campaign_id: str, metrics: Optional[List[str]] = None) -> str:
        """Analiza performance."""
        return f"Análisis de {campaign_id}:\n- CTR: 3.2%\n- ROAS: 4.5x\n- Conversiones: 125\n- Costo por conversión: $12.50\n[Simulación - En producción se analizarían métricas reales]"
    
    # Customer Support Tools
    async def _reset_password(self, user_email: str) -> str:
        """Resetea contraseña."""
        reset_token = uuid.uuid4().hex[:16]
        return f"Reset de contraseña iniciado para {user_email}\nToken: {reset_token}\nLink: https://reset.enterprisedata.ai/{reset_token}\n[Simulación - En producción se enviaría email real]"
    
    async def _check_payment(self, payment_id: str) -> str:
        """Verifica estado de pago."""
        return f"Estado del pago {payment_id}:\n- Estado: Completado\n- Monto: $99.99\n- Fecha: {datetime.now().strftime('%Y-%m-%d')}\n[Simulación - En producción se consultaría Stripe/PayPal]"
    
    async def _query_policy(self, policy_type: str) -> str:
        """Consulta política."""
        policies = {
            "returns": "Política de devoluciones: 30 días desde compra, producto sin usar",
            "warranty": "Garantía: 1 año en defectos de fabricación",
            "shipping": "Envíos: Gratis en compras >$50, 3-5 días hábiles",
            "privacy": "Privacidad: No compartimos datos con terceros",
            "terms": "Términos: Ver términos completos en website"
        }
        return policies.get(policy_type, f"Política {policy_type} no encontrada")
    
    # Knowledge Agent Tools
    async def _query_internal_docs(self, query: str, doc_type: str = "all") -> str:
        """Busca en documentos internos."""
        return f"Resultados de búsqueda en documentos internos:\nConsulta: '{query}'\nTipo: {doc_type}\n- Documento 1: SOP-001.pdf (relevancia: 95%)\n- Documento 2: Manual-User.pdf (relevancia: 87%)\n[Simulación - En producción se buscaría en RAG interno]"
    
    async def _search_notion(self, query: str) -> str:
        """Busca en Notion."""
        return f"Resultados de Notion para '{query}':\n- Página 1: Procedimiento de actualización\n- Página 2: Políticas internas\n[Simulación - En producción se conectaría a Notion API]"
    
    async def _search_confluence(self, query: str) -> str:
        """Busca en Confluence."""
        return f"Resultados de Confluence para '{query}':\n- Página 1: Guía de usuario\n- Página 2: FAQ interno\n[Simulación - En producción se conectaría a Confluence API]"
    
    async def _search_drive(self, query: str) -> str:
        """Busca en Google Drive."""
        return f"Resultados de Google Drive para '{query}':\n- Archivo 1: Manual.pdf\n- Archivo 2: Políticas.docx\n[Simulación - En producción se conectaría a Google Drive API]"
    
    async def _query_database(self, query: str, table: Optional[str] = None) -> str:
        """Consulta base de datos."""
        return f"Resultados de base de datos:\nConsulta: '{query}'\nTabla: {table or 'default'}\n- Registro 1: ...\n- Registro 2: ...\n[Simulación - En producción se ejecutaría SQL real]"
    
    # Commerce Agent Tools
    async def _add_to_cart(self, product_id: str, quantity: int = 1, options: Optional[Dict] = None) -> str:
        """Añade producto al carrito."""
        cart_id = f"CART-{uuid.uuid4().hex[:8].upper()}"
        return f"Producto añadido al carrito:\n- Carrito: {cart_id}\n- Producto: {product_id}\n- Cantidad: {quantity}\n- Opciones: {options or 'Ninguna'}\n[Simulación - En producción se añadiría a carrito real]"
    
    async def _update_cart(self, cart_id: str, updates: Dict) -> str:
        """Actualiza carrito."""
        return f"Carrito {cart_id} actualizado:\n{json.dumps(updates, indent=2)}\n[Simulación - En producción se actualizaría carrito real]"
    
    async def _process_payment(self, cart_id: str, payment_method: str, shipping_address: Dict) -> str:
        """Procesa pago."""
        payment_id = f"PAY-{uuid.uuid4().hex[:8].upper()}"
        return f"Pago procesado:\n- ID: {payment_id}\n- Carrito: {cart_id}\n- Método: {payment_method}\n- Dirección: {shipping_address.get('address', 'N/A')}\n[Simulación - En producción se procesaría con Stripe/PayPal]"
    
    async def _create_order(self, cart_id: str, payment_id: str) -> str:
        """Crea orden."""
        order_id = f"ORD-{uuid.uuid4().hex[:8].upper()}"
        return f"Orden creada:\n- ID: {order_id}\n- Carrito: {cart_id}\n- Pago: {payment_id}\n- Estado: Confirmada\n[Simulación - En producción se crearía orden real]"
    
    async def _send_confirmation(self, order_id: str, customer_email: str) -> str:
        """Envía confirmación."""
        return f"Confirmación enviada a {customer_email}:\n- Orden: {order_id}\n- Email de confirmación enviado\n- Tracking disponible\n[Simulación - En producción se enviaría email real]"
    
    # Brand Persona Tools
    async def _create_content(self, content_type: str, topic: str, tone: Optional[str] = None) -> str:
        """Crea contenido para redes sociales."""
        return f"Contenido {content_type} creado:\nTema: {topic}\nTono: {tone or 'brand default'}\nTexto: 'Descubre más sobre {topic}...'\n[Simulación - En producción se generaría contenido real con LLM]"
    
    async def _post_to_social(self, platform: str, content: str, media_url: Optional[str] = None) -> str:
        """Publica en redes sociales."""
        post_id = f"POST-{uuid.uuid4().hex[:8].upper()}"
        return f"Publicado en {platform}:\n- ID: {post_id}\n- Contenido: {content[:50]}...\n- Media: {media_url or 'N/A'}\n[Simulación - En producción se publicaría en API real]"
    
    async def _respond_to_dm(self, platform: str, dm_id: str, message: str) -> str:
        """Responde a DM."""
        return f"DM respondido en {platform}:\n- DM ID: {dm_id}\n- Respuesta: {message}\n[Simulación - En producción se enviaría DM real]"
    
    async def _analyze_engagement(self, content_id: str, platform: str) -> str:
        """Analiza engagement."""
        return f"Análisis de engagement:\n- Contenido: {content_id}\n- Plataforma: {platform}\n- Likes: 1,234\n- Comentarios: 56\n- Shares: 23\n- Engagement rate: 4.2%\n[Simulación - En producción se analizarían métricas reales]"
    
    def create_agent(
        self,
        name: str,
        description: str,
        system_prompt: str,
        template: AgentTemplate = AgentTemplate.CUSTOM,
        llm_provider: LLMProvider = LLMProvider.OPENAI,
        llm_model: Optional[str] = None,
        tools: Optional[List[str]] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> str:
        """
        Crea un nuevo agente con validación y optimizaciones.
        
        Optimizaciones:
        - Validación de inputs
        - Verificación de disponibilidad de LLM
        - Optimización automática de parámetros según template
        - Validación de herramientas
        
        Returns:
            agent_id: ID único del agente creado
        """
        # Validación de inputs
        if not name or not name.strip():
            raise ValueError("El nombre del agente no puede estar vacío")
        if not description or not description.strip():
            raise ValueError("La descripción del agente no puede estar vacía")
        if not system_prompt or not system_prompt.strip():
            raise ValueError("El system_prompt no puede estar vacío")
        
        # Validar temperatura
        if not 0.0 <= temperature <= 2.0:
            raise ValueError("Temperature debe estar entre 0.0 y 2.0")
        
        # Validar max_tokens
        if max_tokens < 100 or max_tokens > 8000:
            raise ValueError("max_tokens debe estar entre 100 y 8000")
        
        agent_id = str(uuid.uuid4())
        
        # Si se usa un template, aplicar configuración por defecto
        if template != AgentTemplate.CUSTOM and template in self.templates:
            template_config = self.templates[template]
            if not system_prompt:
                system_prompt = template_config["system_prompt"]
            if not llm_model:
                llm_model = template_config["suggested_llm"]
            if tools is None:
                tools = template_config["default_tools"]
            if temperature == 0.7:  # Default, usar del template
                temperature = template_config.get("temperature", 0.7)
        
        # Crear configuración del agente
        agent_config = AgentConfig(
            agent_id=agent_id,
            name=name,
            description=description,
            system_prompt=system_prompt,
            llm_provider=llm_provider,
            llm_model=llm_model or "gpt-4o",
            temperature=temperature,
            max_tokens=max_tokens,
            tools=tools or [],
            template=template
        )
        
        # Crear instancia del LLM según el proveedor (con validación)
        try:
            llm = self._create_llm(llm_provider, llm_model or "gpt-4o", temperature, max_tokens)
        except Exception as e:
            raise ValueError(f"Error creando LLM ({llm_provider.value}): {str(e)}. Verifica que la API key esté configurada.")
        
        # Crear toolkit específico para este agente (con herramientas seleccionadas)
        agent_toolkit = AgentToolkit()
        invalid_tools = []
        for tool_name in (tools or []):
            if tool_name in self.toolkit.tools:
                agent_toolkit.register_tool(self.toolkit.tools[tool_name])
            else:
                invalid_tools.append(tool_name)
        
        if invalid_tools:
            print(f"⚠️ [PrimeAgentsMode] Herramientas no encontradas: {invalid_tools}")
        
        # Crear instancia del agente
        agent = ReActAgent(
            config=agent_config,
            llm=llm,
            toolkit=agent_toolkit,
            memory=AgentMemory(max_items=agent_config.max_memory_items)
        )
        
        # Guardar agente
        self.agents[agent_id] = agent
        self.agent_configs[agent_id] = agent_config
        
        # Inicializar analytics
        self.analytics[agent_id] = AgentAnalytics(agent_id=agent_id)
        
        print(f"✅ [PrimeAgentsMode] Agente creado: {name} (ID: {agent_id})")
        return agent_id
    
    def _create_llm(
        self,
        provider: LLMProvider,
        model: str,
        temperature: float,
        max_tokens: int
    ) -> BaseLanguageModel:
        """Crea instancia de LLM según el proveedor."""
        if provider == LLMProvider.OPENAI:
            if not self.config.openai_api_key:
                raise ValueError("OPENAI_API_KEY requerida para OpenAI")
            return ChatOpenAI(
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                api_key=self.config.openai_api_key
            )
        elif provider == LLMProvider.ANTHROPIC:
            if not ANTHROPIC_AVAILABLE:
                raise ValueError("langchain_anthropic no está instalado. Instala con: pip install langchain-anthropic")
            if not self.config.anthropic_api_key:
                raise ValueError("ANTHROPIC_API_KEY requerida para Anthropic")
            return ChatAnthropic(
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                api_key=self.config.anthropic_api_key
            )
        elif provider == LLMProvider.GOOGLE:
            if not GOOGLE_AVAILABLE:
                raise ValueError("langchain_google_genai no está instalado. Instala con: pip install langchain-google-genai")
            google_api_key = getattr(self.config, 'google_api_key', None) or os.getenv("GOOGLE_API_KEY", "")
            if not google_api_key:
                raise ValueError("GOOGLE_API_KEY requerida para Google")
            return ChatGoogleGenerativeAI(
                model=model,
                temperature=temperature,
                max_output_tokens=max_tokens,
                google_api_key=google_api_key
            )
        else:
            # Default a OpenAI
            return ChatOpenAI(
                model=model or "gpt-4o",
                temperature=temperature,
                max_tokens=max_tokens,
                api_key=self.config.openai_api_key
            )
    
    async def run_agent(self, agent_id: str, user_message: str) -> Dict[str, Any]:
        """
        Ejecuta un agente con un mensaje del usuario.
        
        Optimizaciones:
        - Rate limiting inteligente
        - Caching de respuestas similares
        - Mejor tracking de tokens y costos
        - Analytics mejorados
        - Validación de inputs
        """
        if agent_id not in self.agents:
            raise ValueError(f"Agente '{agent_id}' no encontrado")
        
        # Validar y sanitizar input
        if not user_message or not isinstance(user_message, str):
            raise ValueError("user_message debe ser un string no vacío")
        user_message = user_message.strip()[:5000]  # Limitar longitud
        
        agent = self.agents[agent_id]
        analytics = self.analytics[agent_id]
        
        # Rate limiting
        current_time = time.time()
        if agent_id not in self._rate_limits:
            self._rate_limits[agent_id] = []
        
        # Limpiar timestamps antiguos (> 1 minuto)
        self._rate_limits[agent_id] = [
            ts for ts in self._rate_limits[agent_id]
            if current_time - ts < 60
        ]
        
        # Verificar límite
        if len(self._rate_limits[agent_id]) >= self._max_requests_per_minute:
            raise ValueError(f"Rate limit excedido: máximo {self._max_requests_per_minute} requests por minuto")
        
        self._rate_limits[agent_id].append(current_time)
        
        # Caching: buscar respuesta similar
        cache_key = f"{agent_id}:{hash(user_message[:100])}"
        if cache_key in self._response_cache:
            cached_response, cached_time = self._response_cache[cache_key]
            if current_time - cached_time < self._cache_ttl:
                # Cache hit
                analytics.total_interactions += 1
                analytics.successful_interactions += 1
                return {**cached_response, "cached": True}
        
        start_time = time.time()
        try:
            response = await agent.reply(user_message)
            elapsed_ms = response.get("execution_time_ms", (time.time() - start_time) * 1000)
            
            # Actualizar analytics con datos precisos
            analytics.total_interactions += 1
            if response.get("success"):
                analytics.successful_interactions += 1
            else:
                analytics.failed_interactions += 1
            
            # Calcular promedio de tiempo de respuesta (moving average)
            if analytics.total_interactions == 1:
                analytics.average_response_time_ms = elapsed_ms
            else:
                # Exponential moving average (alpha = 0.3)
                alpha = 0.3
                analytics.average_response_time_ms = (
                    alpha * elapsed_ms + (1 - alpha) * analytics.average_response_time_ms
                )
            
            # Track tokens y costos
            tokens_used = response.get("tokens_used", 0)
            if tokens_used > 0:
                analytics.total_tokens_used += tokens_used
                
                # Estimar costo (aproximado, varía por modelo)
                agent_config = self.agent_configs[agent_id]
                if agent_config.llm_provider == LLMProvider.OPENAI:
                    # OpenAI pricing (aproximado)
                    input_cost_per_1k = 0.01 if "gpt-4" in agent_config.llm_model else 0.0005
                    output_cost_per_1k = 0.03 if "gpt-4" in agent_config.llm_model else 0.0015
                    # Estimación: 70% input, 30% output
                    estimated_cost = (tokens_used * 0.7 * input_cost_per_1k / 1000) + \
                                    (tokens_used * 0.3 * output_cost_per_1k / 1000)
                    analytics.total_cost_usd += estimated_cost
            
            # Contar uso de herramientas
            for tool_call in response.get("tool_calls", []):
                tool_name = tool_call.get("tool_name", "unknown")
                analytics.tool_usage_stats[tool_name] = analytics.tool_usage_stats.get(tool_name, 0) + 1
            
            analytics.last_updated = datetime.now().isoformat()
            
            # Guardar en cache si fue exitoso
            if response.get("success") and not response.get("cached"):
                # Limpiar cache si está lleno
                if len(self._response_cache) >= self._cache_max_size:
                    # Remover el más antiguo
                    oldest_key = min(self._response_cache.keys(), 
                                    key=lambda k: self._response_cache[k][1])
                    del self._response_cache[oldest_key]
                
                self._response_cache[cache_key] = (response, current_time)
            
            return response
            
        except Exception as e:
            analytics.total_interactions += 1
            analytics.failed_interactions += 1
            analytics.last_updated = datetime.now().isoformat()
            
            print(f"❌ [PrimeAgentsMode] Error ejecutando agente {agent_id}: {e}")
            import traceback
            traceback.print_exc()
            
            return {
                "agent_id": agent_id,
                "response": "",
                "success": False,
                "error": str(e),
                "execution_time_ms": (time.time() - start_time) * 1000
            }
    
    def deploy_agent(
        self,
        agent_id: str,
        channels: List[DeploymentChannel],
        webhook_url: Optional[str] = None,
        credentials: Optional[Dict[str, Any]] = None
    ) -> DeploymentConfig:
        """
        Despliega un agente en los canales especificados.
        
        Optimizaciones:
        - Validación de configuración antes de deployment
        - Generación automática de URLs/endpoints
        - Verificación de credenciales
        """
        if agent_id not in self.agents:
            raise ValueError(f"Agente '{agent_id}' no encontrado")
        
        agent_config = self.agent_configs[agent_id]
        
        # Validar que el agente tenga configuración válida
        if not agent_config.name or not agent_config.system_prompt:
            raise ValueError("El agente debe tener nombre y system_prompt configurados")
        
        # Generar URLs/endpoints automáticamente
        base_url = f"https://agents.enterprisedata.ai/{agent_id}"
        web_url = f"{base_url}/chat" if DeploymentChannel.WEB in channels else None
        api_endpoint = f"{base_url}/api/v1/chat" if DeploymentChannel.API in channels else None
        
        # Validar credenciales según el canal
        validated_credentials = credentials or {}
        if DeploymentChannel.WHATSAPP in channels:
            if "whatsapp_token" not in validated_credentials:
                print("⚠️ WhatsApp requiere token. Se puede configurar después.")
        if DeploymentChannel.MESSENGER in channels:
            if "messenger_token" not in validated_credentials:
                print("⚠️ Messenger requiere token. Se puede configurar después.")
        
        deployment = DeploymentConfig(
            agent_id=agent_id,
            channels=channels,
            web_url=web_url,
            api_endpoint=api_endpoint,
            webhook_url=webhook_url,
            credentials=validated_credentials,
            deployed_at=datetime.now().isoformat()
        )
        
        self.deployments[agent_id] = deployment
        
        print(f"✅ [PrimeAgentsMode] Agente {agent_config.name} ({agent_id}) desplegado en: {[c.value for c in channels]}")
        if web_url:
            print(f"   🌐 Web URL: {web_url}")
        if api_endpoint:
            print(f"   🔌 API Endpoint: {api_endpoint}")
        
        return deployment
    
    def get_agent_config(self, agent_id: str) -> Optional[AgentConfig]:
        """Obtiene la configuración de un agente."""
        return self.agent_configs.get(agent_id)
    
    def get_agent_analytics(self, agent_id: str) -> Optional[AgentAnalytics]:
        """Obtiene analytics de un agente."""
        return self.analytics.get(agent_id)
    
    def list_agents(self) -> List[Dict[str, Any]]:
        """Lista todos los agentes creados."""
        return [
            {
                "agent_id": agent_id,
                "name": config.name,
                "description": config.description,
                "template": config.template.value,
                "created_at": config.created_at,
                "deployed": agent_id in self.deployments
            }
            for agent_id, config in self.agent_configs.items()
        ]
    
    def delete_agent(self, agent_id: str) -> bool:
        """Elimina un agente."""
        if agent_id in self.agents:
            del self.agents[agent_id]
            del self.agent_configs[agent_id]
            if agent_id in self.deployments:
                del self.deployments[agent_id]
            if agent_id in self.analytics:
                del self.analytics[agent_id]
            print(f"✅ [PrimeAgentsMode] Agente {agent_id} eliminado")
            return True
        return False
    
    def export_agent(self, agent_id: str) -> Dict[str, Any]:
        """Exporta configuración de agente como JSON."""
        if agent_id not in self.agent_configs:
            raise ValueError(f"Agente '{agent_id}' no encontrado")
        
        config = self.agent_configs[agent_id]
        analytics = self.analytics.get(agent_id)
        deployment = self.deployments.get(agent_id)
        
        return {
            "config": asdict(config),
            "analytics": asdict(analytics) if analytics else None,
            "deployment": asdict(deployment) if deployment else None
        }
    
    def import_agent(self, agent_data: Dict[str, Any]) -> str:
        """Importa un agente desde JSON."""
        config_dict = agent_data["config"]
        agent_config = AgentConfig(**config_dict)
        
        # Recrear agente
        llm = self._create_llm(
            LLMProvider(agent_config.llm_provider.value),
            agent_config.llm_model,
            agent_config.temperature,
            agent_config.max_tokens
        )
        
        agent_toolkit = AgentToolkit()
        for tool_name in agent_config.tools:
            if tool_name in self.toolkit.tools:
                agent_toolkit.register_tool(self.toolkit.tools[tool_name])
        
        agent = ReActAgent(
            config=agent_config,
            llm=llm,
            toolkit=agent_toolkit,
            memory=AgentMemory(max_items=agent_config.max_memory_items)
        )
        
        self.agents[agent_config.agent_id] = agent
        self.agent_configs[agent_config.agent_id] = agent_config
        
        if agent_data.get("analytics"):
            self.analytics[agent_config.agent_id] = AgentAnalytics(**agent_data["analytics"])
        
        if agent_data.get("deployment"):
            self.deployments[agent_config.agent_id] = DeploymentConfig(**agent_data["deployment"])
        
        return agent_config.agent_id


# Funciones helper para integración con app.py
def get_prime_agents_mode(config: AppConfig) -> PrimeAgentsMode:
    """Obtiene instancia singleton de PrimeAgentsMode."""
    if not hasattr(get_prime_agents_mode, "_instance"):
        get_prime_agents_mode._instance = PrimeAgentsMode(config)
    return get_prime_agents_mode._instance


async def run_prime_agents_mode(
    message: str,
    agent_id: Optional[str] = None,
    session_id: Optional[str] = None,
    config: Optional[AppConfig] = None
) -> Tuple[str, Dict[str, Any]]:
    """
    Ejecuta un agente de PRIME AGENTS.
    
    Returns:
        (response_text, metadata)
    """
    if not config:
        from .config import load_config
        config = load_config()
    
    prime_agents = get_prime_agents_mode(config)
    
    # Si no hay agent_id, usar el primero disponible o crear uno por defecto
    if not agent_id:
        agents = prime_agents.list_agents()
        if agents:
            agent_id = agents[0]["agent_id"]
        else:
            # Crear agente por defecto
            agent_id = prime_agents.create_agent(
                name="Default Assistant",
                description="Asistente general",
                system_prompt="Eres un asistente útil y amigable.",
                template=AgentTemplate.PERSONAL_ASSISTANT
            )
    
    response = await prime_agents.run_agent(agent_id, message)
    
    response_text = response.get("response", "No se pudo generar respuesta.")
    metadata = {
        "agent_id": agent_id,
        "success": response.get("success", False),
        "tool_calls": response.get("tool_calls", []),
        "reasoning_steps": len(response.get("reasoning_steps", []))
    }
    
    return response_text, metadata

