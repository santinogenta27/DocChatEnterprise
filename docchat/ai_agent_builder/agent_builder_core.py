"""
AI Agent Builder Core - Núcleo del constructor de agentes
Basado en los principios de RAG, Multimodal AI, y Agentic AI
"""

from __future__ import annotations

import json
import os
import uuid
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from enum import Enum

try:
    from langchain_core.language_models import BaseLanguageModel
    from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
    from langchain_core.output_parsers import StrOutputParser, JsonOutputParser
    from langchain_core.runnables import Runnable, RunnableLambda
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    print("⚠️ LangChain no disponible. Instala con: pip install langchain langchain-core")


class AgentType(str, Enum):
    """Tipos de agentes disponibles"""
    SIMPLE = "simple"  # Agente básico con prompt
    RAG = "rag"  # Agente con RAG
    MULTIMODAL = "multimodal"  # Agente multimodal
    AGENTIC = "agentic"  # Agente con capacidades agentic
    HYBRID = "hybrid"  # Combinación de todas las capacidades


class AgentCapability(str, Enum):
    """Capacidades de agentes"""
    TEXT_PROCESSING = "text_processing"
    IMAGE_PROCESSING = "image_processing"
    AUDIO_PROCESSING = "audio_processing"
    VIDEO_PROCESSING = "video_processing"
    DOCUMENT_RETRIEVAL = "document_retrieval"
    CODE_EXECUTION = "code_execution"
    WEB_SEARCH = "web_search"
    DATABASE_QUERY = "database_query"
    API_INTEGRATION = "api_integration"
    MULTI_AGENT_COLLABORATION = "multi_agent_collaboration"


@dataclass
class AgentDefinition:
    """Definición completa de un agente"""
    agent_id: str = field(default_factory=lambda: f"agent_{uuid.uuid4().hex[:8]}")
    name: str = ""
    description: str = ""
    agent_type: AgentType = AgentType.SIMPLE
    capabilities: List[AgentCapability] = field(default_factory=list)
    
    # Prompt Engineering
    system_prompt: str = ""
    prompt_template: Optional[str] = None
    few_shot_examples: List[Dict[str, str]] = field(default_factory=list)
    use_chain_of_thought: bool = False
    use_self_consistency: bool = False
    
    # RAG Configuration
    rag_enabled: bool = False
    vector_databases: List[str] = field(default_factory=list)  # ["chroma", "faiss", "pinecone"]
    retriever_type: str = "hybrid"  # "semantic", "keyword", "hybrid"
    top_k: int = 5
    rerank_enabled: bool = False
    
    # Multimodal Configuration
    multimodal_enabled: bool = False
    supported_media_types: List[str] = field(default_factory=list)  # ["text", "image", "audio", "video"]
    
    # Agentic Framework
    framework: str = "langchain"  # "langchain", "langgraph", "crewai", "ag2", "bai"
    workflow_definition: Optional[Dict[str, Any]] = None
    
    # Model Configuration
    primary_model: str = "gpt-4o"
    fallback_models: List[str] = field(default_factory=list)
    temperature: float = 0.7
    max_tokens: int = 2000
    
    # Tools and Integrations
    tools: List[Dict[str, Any]] = field(default_factory=list)
    api_integrations: List[Dict[str, Any]] = field(default_factory=list)
    
    # Memory and Context
    memory_enabled: bool = True
    context_window: int = 4000
    conversation_history_limit: int = 10
    
    # Output Configuration
    output_format: str = "text"  # "text", "json", "structured"
    output_schema: Optional[Dict[str, Any]] = None
    
    # Metadata
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    version: str = "1.0.0"
    tags: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte a diccionario"""
        data = asdict(self)
        # Convertir enums a strings
        data["agent_type"] = self.agent_type.value
        data["capabilities"] = [c.value for c in self.capabilities]
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> AgentDefinition:
        """Crea desde diccionario"""
        # Convertir strings a enums
        if isinstance(data.get("agent_type"), str):
            data["agent_type"] = AgentType(data["agent_type"])
        if isinstance(data.get("capabilities"), list):
            data["capabilities"] = [AgentCapability(c) if isinstance(c, str) else c 
                                   for c in data["capabilities"]]
        return cls(**data)


@dataclass
class AgentTemplate:
    """Template pre-construido de agente"""
    template_id: str
    name: str
    description: str
    category: str  # "customer_support", "data_analysis", "content_generation", etc.
    agent_definition: AgentDefinition
    use_cases: List[str] = field(default_factory=list)
    estimated_cost_per_1k_requests: float = 0.0
    complexity_level: str = "beginner"  # "beginner", "intermediate", "advanced"


class AgentBuilderCore:
    """
    Núcleo del constructor de agentes AI
    Combina RAG, Multimodal AI, y Agentic AI
    """
    
    def __init__(self, config: Any, retriever_builder: Any = None):
        self.config = config
        self.retriever_builder = retriever_builder  # Retriever builder del sistema
        self.agents: Dict[str, AgentDefinition] = {}
        self.agent_instances: Dict[str, Any] = {}  # Instancias ejecutables
        
        # Inicializar componentes
        self._initialize_components()
    
    def _initialize_components(self):
        """Inicializa componentes necesarios"""
        try:
            from .rag_engine import AdvancedRAGEngine
            from .multimodal_processor import MultimodalProcessor
            from .model_orchestrator import ModelOrchestrator
            from .agentic_frameworks import LangGraphOrchestrator, CrewAIOrchestrator
            
            self.rag_engine = AdvancedRAGEngine(self.config)
            self.multimodal_processor = MultimodalProcessor(self.config)
            self.model_orchestrator = ModelOrchestrator(self.config)
            
            # Inicializar orchestrators agentic
            try:
                self.langgraph_orchestrator = LangGraphOrchestrator(self.config)
            except Exception as e:
                print(f"⚠️ LangGraph orchestrator no disponible: {e}")
                self.langgraph_orchestrator = None
            
            try:
                self.crewai_orchestrator = CrewAIOrchestrator(self.config)
            except Exception as e:
                print(f"⚠️ CrewAI orchestrator no disponible: {e}")
                self.crewai_orchestrator = None
        except Exception as e:
            print(f"⚠️ Error inicializando componentes: {e}")
            self.rag_engine = None
            self.multimodal_processor = None
            self.model_orchestrator = None
            self.langgraph_orchestrator = None
            self.crewai_orchestrator = None
    
    def create_agent(self, definition: AgentDefinition) -> str:
        """
        Crea un nuevo agente basado en la definición
        
        Args:
            definition: Definición del agente
            
        Returns:
            agent_id: ID del agente creado
        """
        # Validar definición
        self._validate_definition(definition)
        
        # Guardar definición
        self.agents[definition.agent_id] = definition
        
        # Construir instancia ejecutable
        agent_instance = self._build_agent_instance(definition)
        self.agent_instances[definition.agent_id] = agent_instance
        
        # Guardar en persistencia
        self._save_agent(definition)
        
        return definition.agent_id
    
    def _validate_definition(self, definition: AgentDefinition):
        """Valida la definición del agente"""
        if not definition.name:
            raise ValueError("El agente debe tener un nombre")
        if not definition.system_prompt and not definition.prompt_template:
            raise ValueError("El agente debe tener un system_prompt o prompt_template")
        if definition.rag_enabled and not definition.vector_databases:
            raise ValueError("RAG habilitado requiere al menos una base de datos vectorial")
        if definition.multimodal_enabled and not definition.supported_media_types:
            raise ValueError("Multimodal habilitado requiere al menos un tipo de media")
    
    def _build_agent_instance(self, definition: AgentDefinition) -> Any:
        """
        Construye la instancia ejecutable del agente
        Basado en LangChain, LangGraph, CrewAI, etc.
        """
        if not LANGCHAIN_AVAILABLE:
            raise ImportError("LangChain es requerido para construir agentes")
        
        # Si el agente usa framework agentic, construir workflow
        framework = getattr(definition, 'framework', 'langchain')
        if framework in ["langgraph", "crewai"]:
            if framework == "langgraph" and self.langgraph_orchestrator:
                return self._build_langgraph_agent(definition)
            elif framework == "crewai" and self.crewai_orchestrator:
                return self._build_crewai_agent(definition)
        
        # Construir chain básico de LangChain
        return self._build_langchain_chain(definition)
    
    def _build_langchain_chain(self, definition: AgentDefinition) -> Any:
        """Construye un chain básico de LangChain"""
        # Construir prompt
        prompt = self._build_prompt(definition)
        
        # Construir LLM
        llm = self._build_llm(definition)
        
        # Construir chain básico
        chain = prompt | llm
        
        # Agregar RAG si está habilitado
        if definition.rag_enabled:
            chain = self._add_rag_to_chain(chain, definition)
        
        # Agregar multimodal si está habilitado
        if definition.multimodal_enabled:
            chain = self._add_multimodal_to_chain(chain, definition)
        
        # Agregar output parser
        if definition.output_format == "json":
            parser = JsonOutputParser()
            chain = chain | parser
        else:
            parser = StrOutputParser()
            chain = chain | parser
        
        return chain
    
    def _build_langgraph_agent(self, definition: AgentDefinition) -> Any:
        """Construye un agente con LangGraph workflow"""
        if not self.langgraph_orchestrator:
            # Fallback a chain básico
            return self._build_langchain_chain(definition)
        
        try:
            from langgraph.graph import StateGraph, END
            from langchain_core.messages import HumanMessage, AIMessage
            
            # Construir LLM
            llm = self._build_llm(definition)
            
            # Crear nodos del workflow
            def agent_node(state):
                """Nodo del agente que procesa mensajes"""
                messages = state.get("messages", [])
                if not messages:
                    return {"messages": []}
                
                # Obtener último mensaje
                last_message = messages[-1]
                query = last_message.content if hasattr(last_message, 'content') else str(last_message)
                
                # Construir prompt
                prompt = self._build_prompt(definition)
                
                # Ejecutar con LLM
                if definition.rag_enabled:
                    # Si tiene RAG, usar chain con RAG
                    chain = self._build_langchain_chain(definition)
                    result = chain.invoke({"input": query, "context": ""})
                else:
                    chain = prompt | llm
                    if definition.output_format == "json":
                        from langchain_core.output_parsers import JsonOutputParser
                        parser = JsonOutputParser()
                        chain = chain | parser
                    else:
                        from langchain_core.output_parsers import StrOutputParser
                        parser = StrOutputParser()
                        chain = chain | parser
                    result = chain.invoke({"input": query})
                
                # Crear mensaje de respuesta
                response = AIMessage(content=str(result))
                return {"messages": [response]}
            
            # Crear workflow
            workflow = StateGraph(dict)
            workflow.add_node("agent", agent_node)
            workflow.set_entry_point("agent")
            workflow.add_edge("agent", END)
            
            # Compilar
            app = workflow.compile()
            
            # Guardar workflow
            workflow_id = f"langgraph_{definition.agent_id}"
            if hasattr(self.langgraph_orchestrator, 'graphs'):
                self.langgraph_orchestrator.graphs[workflow_id] = app
            
            return app
        except Exception as e:
            print(f"⚠️ Error construyendo LangGraph agent: {e}")
            # Fallback a chain básico
            return self._build_langchain_chain(definition)
    
    def _build_crewai_agent(self, definition: AgentDefinition) -> Any:
        """Construye un agente con CrewAI"""
        if not self.crewai_orchestrator:
            # Fallback a chain básico
            return self._build_langchain_chain(definition)
        
        try:
            from crewai import Agent, Task, Crew
            from crewai.process import Process
            
            # Crear agente de CrewAI
            crew_agent = Agent(
                role=definition.name or "AI Assistant",
                goal=definition.description or "Help the user",
                backstory=definition.system_prompt or "You are a helpful AI assistant.",
                verbose=True,
                allow_delegation=False
            )
            
            # Crear tarea simple
            task = Task(
                description="Process the user's request and provide a helpful response.",
                agent=crew_agent
            )
            
            # Crear crew
            crew = Crew(
                agents=[crew_agent],
                tasks=[task],
                process=Process.sequential,
                verbose=True
            )
            
            # Guardar crew
            crew_id = f"crewai_{definition.agent_id}"
            if hasattr(self.crewai_orchestrator, 'crews'):
                self.crewai_orchestrator.crews[crew_id] = crew
            
            # Crear wrapper para ejecutar
            class CrewWrapper:
                def __init__(self, crew_instance):
                    self.crew = crew_instance
                
                def invoke(self, input_dict):
                    query = input_dict.get("input", input_dict.get("question", ""))
                    result = self.crew.kickoff(inputs={"query": query})
                    return {"output": str(result)}
            
            return CrewWrapper(crew)
        except Exception as e:
            print(f"⚠️ Error construyendo CrewAI agent: {e}")
            # Fallback a chain básico
            return self._build_langchain_chain(definition)
    
    def _build_prompt(self, definition: AgentDefinition) -> Any:
        """Construye el prompt del agente"""
        messages = []
        
        # System message
        if definition.system_prompt:
            messages.append(("system", definition.system_prompt))
        
        # Few-shot examples
        if definition.few_shot_examples:
            for example in definition.few_shot_examples:
                if "input" in example:
                    messages.append(("human", example["input"]))
                if "output" in example:
                    messages.append(("ai", example["output"]))
        
        # User message template
        if definition.prompt_template:
            user_template = definition.prompt_template
        else:
            # Si RAG está habilitado, incluir contexto en el template
            if definition.rag_enabled:
                user_template = """Contexto relevante:
{context}

Pregunta del usuario: {input}

Responde basándote en el contexto proporcionado. Si el contexto no contiene información relevante, indica que no tienes esa información."""
            else:
                user_template = "{input}"
        
        messages.append(("human", user_template))
        
        return ChatPromptTemplate.from_messages(messages)
    
    def _build_llm(self, definition: AgentDefinition) -> Any:
        """Construye el LLM según la configuración"""
        # Esto se implementará con ModelOrchestrator
        # Por ahora, placeholder
        from langchain_openai import ChatOpenAI
        
        api_key = getattr(self.config, 'openai_api_key', None) or None
        
        return ChatOpenAI(
            model=definition.primary_model,
            temperature=definition.temperature,
            max_tokens=definition.max_tokens,
            api_key=api_key
        )
    
    def _add_rag_to_chain(self, chain: Any, definition: AgentDefinition) -> Any:
        """Agrega RAG al chain usando AdvancedRAGEngine"""
        if not self.rag_engine or not definition.rag_enabled:
            return chain
        
        try:
            # Obtener retriever del RAG engine
            rag_id = f"rag_{definition.agent_id}"
            
            # Si no existe retriever, intentar usar retriever del sistema existente
            if rag_id not in self.rag_engine.retrievers:
                # Intentar usar retriever del sistema si existe
                if hasattr(self, 'retriever_builder') and self.retriever_builder:
                    try:
                        # Usar el retriever builder existente del sistema
                        retriever = self.retriever_builder.build_hybrid_retriever(
                            documents=[],  # Se agregarán después
                            k=definition.top_k
                        )
                        if retriever:
                            self.rag_engine.retrievers[rag_id] = retriever
                    except Exception as e:
                        print(f"⚠️ Error usando retriever del sistema: {e}")
                
                # Si aún no hay retriever, crear uno básico
                if rag_id not in self.rag_engine.retrievers:
                    # Crear configuración de base de datos
                    from .rag_engine import VectorDatabaseConfig
                    
                    if definition.vector_databases:
                        db_configs = []
                        for db_type in definition.vector_databases:
                            db_config = VectorDatabaseConfig(
                                db_type=db_type.lower(),
                                name=f"{definition.agent_id}_{db_type}",
                                embedding_model="text-embedding-3-small"
                            )
                            db_configs.append(db_config)
                        
                        # Setup RAG
                        try:
                            rag_id = self.rag_engine.setup_rag(
                                db_configs,
                                retriever_type=definition.retriever_type,
                                top_k=definition.top_k,
                                rerank_enabled=definition.rerank_enabled
                            )
                        except Exception as e:
                            print(f"⚠️ Error configurando RAG: {e}")
                            return chain
            
            # Obtener retriever
            retriever = self.rag_engine.retrievers.get(rag_id)
            if not retriever:
                print(f"⚠️ No se pudo obtener retriever para {rag_id}")
                return chain
            
            # Crear RAG chain con LangChain
            from langchain_core.runnables import RunnablePassthrough
            
            def format_docs(docs):
                """Formatea documentos para el contexto"""
                if not docs:
                    return "No hay documentos relevantes disponibles."
                return "\n\n".join([
                    f"Documento {i+1}:\n{doc.page_content if hasattr(doc, 'page_content') else str(doc)}"
                    for i, doc in enumerate(docs)
                ])
            
            # Crear chain RAG: input -> retriever -> format -> prompt (con context) -> llm
            def rag_chain_func(input_dict):
                """Función que ejecuta RAG y luego el chain original"""
                query = input_dict.get("input", input_dict.get("question", ""))
                
                # Obtener documentos relevantes
                try:
                    if hasattr(retriever, 'invoke'):
                        docs = retriever.invoke(query)
                    else:
                        docs = retriever.get_relevant_documents(query, k=definition.top_k)
                except Exception as e:
                    print(f"⚠️ Error en retrieval: {e}")
                    docs = []
                
                # Formatear contexto
                context = format_docs(docs)
                
                # Agregar contexto al input
                input_dict["context"] = context
                input_dict["question"] = query
                
                # Ejecutar chain original con contexto
                return chain.invoke(input_dict)
            
            # Crear RunnableLambda para el RAG chain
            from langchain_core.runnables import RunnableLambda
            rag_chain = RunnableLambda(rag_chain_func)
            
            return rag_chain
        except Exception as e:
            print(f"⚠️ Error agregando RAG al chain: {e}")
            import traceback
            traceback.print_exc()
            return chain
    
    def _add_multimodal_to_chain(self, chain: Any, definition: AgentDefinition) -> Any:
        """Agrega capacidades multimodales al chain"""
        if not self.multimodal_processor or not definition.multimodal_enabled:
            return chain
        
        try:
            # Para multimodal, el chain ya soporta imágenes si usamos ChatOpenAI con visión
            # El procesamiento se hace en el input antes de llegar al chain
            # Por ahora, retornamos el chain (el procesamiento multimodal se hace en execute_agent)
            return chain
        except Exception as e:
            print(f"⚠️ Error agregando multimodal al chain: {e}")
            return chain
    
    def execute_agent(
        self,
        agent_id: str,
        input_data: Union[str, Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None
    ) -> Any:
        """
        Ejecuta un agente con input dado
        
        Args:
            agent_id: ID del agente
            input_data: Input para el agente (texto o dict multimodal)
            context: Contexto adicional
            
        Returns:
            Resultado de la ejecución del agente
        """
        if agent_id not in self.agent_instances:
            raise ValueError(f"Agente {agent_id} no encontrado")
        
        agent = self.agent_instances[agent_id]
        definition = self.agents[agent_id]
        
        # Preparar input
        if isinstance(input_data, str):
            agent_input = {"input": input_data}
        else:
            agent_input = input_data
        
        # Agregar contexto si existe
        if context:
            agent_input.update(context)
        
        # Ejecutar agente
        try:
            # Si es un workflow de LangGraph
            if hasattr(agent, 'invoke') and hasattr(agent, 'get_graph'):
                # Es un LangGraph workflow
                state = agent.invoke({"messages": [{"role": "user", "content": agent_input.get("input", "")}]})
                messages = state.get("messages", [])
                if messages:
                    last_message = messages[-1]
                    if hasattr(last_message, 'content'):
                        return last_message.content
                    return str(last_message)
                return str(state)
            # Si es un wrapper de CrewAI
            elif hasattr(agent, 'crew'):
                result = agent.invoke(agent_input)
                return result.get('output', str(result))
            # Si el chain es un RunnableLambda (RAG), ejecutar directamente
            elif hasattr(agent, '_func'):
                result = agent.invoke(agent_input)
            else:
                result = agent.invoke(agent_input)
            
            # Extraer contenido si es un mensaje de LangChain
            if hasattr(result, 'content'):
                return result.content
            elif isinstance(result, dict):
                # Si es dict, buscar 'output', 'answer', o 'result'
                return result.get('output', result.get('answer', result.get('result', str(result))))
            elif isinstance(result, str):
                return result
            else:
                return str(result)
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"❌ Error detallado ejecutando agente: {error_details}")
            raise RuntimeError(f"Error ejecutando agente {agent_id}: {str(e)}")
    
    def update_agent(self, agent_id: str, updates: Dict[str, Any]) -> bool:
        """Actualiza un agente existente"""
        if agent_id not in self.agents:
            raise ValueError(f"Agente {agent_id} no encontrado")
        
        definition = self.agents[agent_id]
        definition_dict = definition.to_dict()
        definition_dict.update(updates)
        definition_dict["updated_at"] = datetime.now().isoformat()
        
        # Recrear definición
        new_definition = AgentDefinition.from_dict(definition_dict)
        new_definition.agent_id = agent_id  # Mantener mismo ID
        
        # Reconstruir instancia
        self.agents[agent_id] = new_definition
        self.agent_instances[agent_id] = self._build_agent_instance(new_definition)
        
        # Guardar
        self._save_agent(new_definition)
        
        return True
    
    def delete_agent(self, agent_id: str) -> bool:
        """Elimina un agente"""
        if agent_id not in self.agents:
            return False
        
        del self.agents[agent_id]
        if agent_id in self.agent_instances:
            del self.agent_instances[agent_id]
        
        # Eliminar de persistencia
        self._delete_agent_file(agent_id)
        
        return True
    
    def list_agents(self) -> List[Dict[str, Any]]:
        """Lista todos los agentes"""
        return [
            {
                "agent_id": agent_id,
                "name": definition.name,
                "description": definition.description,
                "agent_type": definition.agent_type.value,
                "capabilities": [c.value for c in definition.capabilities],
                "created_at": definition.created_at,
                "updated_at": definition.updated_at
            }
            for agent_id, definition in self.agents.items()
        ]
    
    def get_agent(self, agent_id: str) -> Optional[AgentDefinition]:
        """Obtiene la definición de un agente"""
        return self.agents.get(agent_id)
    
    def _save_agent(self, definition: AgentDefinition):
        """Guarda agente en persistencia"""
        agents_dir = Path(self.config.memory_dir) / "ai_agents" if self.config.memory_dir else Path("data/ai_agents")
        agents_dir.mkdir(parents=True, exist_ok=True)
        
        agent_file = agents_dir / f"{definition.agent_id}.json"
        with open(agent_file, 'w', encoding='utf-8') as f:
            json.dump(definition.to_dict(), f, indent=2, ensure_ascii=False)
    
    def _delete_agent_file(self, agent_id: str):
        """Elimina archivo de agente"""
        agents_dir = Path(self.config.memory_dir) / "ai_agents" if self.config.memory_dir else Path("data/ai_agents")
        agent_file = agents_dir / f"{agent_id}.json"
        if agent_file.exists():
            agent_file.unlink()
    
    def load_agents(self):
        """Carga agentes desde persistencia"""
        agents_dir = Path(self.config.memory_dir) / "ai_agents" if self.config.memory_dir else Path("data/ai_agents")
        if not agents_dir.exists():
            return
        
        for agent_file in agents_dir.glob("*.json"):
            try:
                with open(agent_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    definition = AgentDefinition.from_dict(data)
                    self.agents[definition.agent_id] = definition
                    # Reconstruir instancia
                    self.agent_instances[definition.agent_id] = self._build_agent_instance(definition)
            except Exception as e:
                print(f"⚠️ Error cargando agente {agent_file}: {e}")
