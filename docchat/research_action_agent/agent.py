"""Research & Action Agent - Main agent class."""

from __future__ import annotations

import json
import time
from typing import Dict, Any, Optional, List
from pathlib import Path

try:
    from langchain_openai import ChatOpenAI
    from langchain_anthropic import ChatAnthropic
except ImportError:
    ChatOpenAI = None
    ChatAnthropic = None

from langchain_core.messages import HumanMessage, AIMessage

from ..config import AppConfig
from .workflows.react_graph import build_react_graph, AgentState
from .utils.audit import AuditLogger, save_audit_log
from .graphrag_engine import GraphRAGEngine, GraphConnectionConfig
from .text_to_cypher import TextToCypherPipeline
from .mdp_agent import MDPAgent
from .sat_graph_api import SATGraphAPI
from .service_scheduler import (
    ServiceScheduler,
    ServiceDescriptor,
    ExecutionGraph,
    ExecutionNode,
)
from .multi_agent_graphrag import MultiAgentGraphRAGEngine
from .agentic_kgr import AgenticKGR
from .graph_search import GraphSearch
from .clause_reasoning import CLAUSEReasoner
from .graph_r1 import GraphR1
from .architecture import InputParser, TaskClassifier, Planner, ParsedInput, TaskIntent


class ResearchActionAgent:
    """
    Research & Action Agent - Enterprise ReAct Agent for DocChat.
    
    This agent follows the ReAct pattern:
    - THINK: Reason about the task
    - ACT: Use tools to gather information or execute actions
    - OBSERVE: Process tool results
    - LOOP: Continue until ready to respond
    
    Features:
    - RAG integration for internal documents
    - Web search for current information
    - Calculator for mathematical operations
    - Action executor for enterprise actions (tickets, emails, ERP, RPA)
    - Full audit logging
    - Risk assessment capabilities
    - Auto-ticketing
    - Research briefs
    """
    
    def __init__(
        self,
        config: Optional[AppConfig] = None,
        provider: str = "openai",
        model_name: Optional[str] = None,
        semantic_engine: Optional[Any] = None
    ):
        """
        Initialize the Research & Action Agent.
        
        Args:
            config: AppConfig instance
            provider: LLM provider ("openai" or "anthropic")
            model_name: Specific model name (default: from config)
            semantic_engine: Optional SemanticDataEngine instance for RAG queries
        """
        self.config = config or AppConfig()
        self.provider = provider
        self.audit_logger = AuditLogger()
        self.semantic_engine = semantic_engine

        # Store semantic engine globally for RAG tool access
        if semantic_engine:
            try:
                import docchat.semantic_data_engine as sde_module

                sde_module._global_engine = semantic_engine
            except Exception:
                pass
        
        # Initialize LLM
        if provider == "openai":
            if not ChatOpenAI:
                raise ImportError("langchain_openai no está instalado")
            
            api_key = self.config.openai_api_key
            if not api_key:
                raise ValueError("OPENAI_API_KEY no configurada")
            
            model = model_name or self.config.agentic_model or "gpt-4o-mini"
            self.llm = ChatOpenAI(
                model=model,
                temperature=0.3,  # Lower temperature for more deterministic reasoning
                api_key=api_key
            )
        
        elif provider == "anthropic":
            if not ChatAnthropic:
                raise ImportError("langchain_anthropic no está instalado")
            
            api_key = self.config.anthropic_api_key
            if not api_key:
                raise ValueError("ANTHROPIC_API_KEY no configurada")
            
            model = model_name or "claude-3-5-sonnet-20241022"
            self.llm = ChatAnthropic(
                model=model,
                temperature=0.3,
                api_key=api_key
            )
        else:
            raise ValueError(f"Provider no soportado: {provider}")
        
        # Load system prompt
        try:
            prompt_path = Path(__file__).parent / "prompts" / "react_prompt.txt"
            with open(prompt_path, "r", encoding="utf-8") as f:
                self.system_prompt = f.read()
        except Exception as e:
            print(f"⚠️ Error cargando prompt: {e}")
            self.system_prompt = "You are a helpful AI assistant that uses tools when needed."
        
        # Build the ReAct graph
        try:
            self.graph = build_react_graph(
                model=self.llm,
                tools=None,  # Will use TOOLS_REGISTRY
                system_prompt=self.system_prompt,
            )
            print("✅ Research & Action Agent inicializado")
        except Exception as e:
            print(f"⚠️ Error inicializando ReAct graph: {e}")
            self.graph = None

        # Initialize GraphRAG / Text-to-Cypher / SAT-Graph / MDP-Agent
        try:
            graph_config = GraphConnectionConfig(
                uri=self.config.graph_db_uri if hasattr(self.config, "graph_db_uri") else "",
                username=getattr(self.config, "graph_db_username", None),
                password=getattr(self.config, "graph_db_password", None),
                database=getattr(self.config, "graph_db_database", None),
            )
        except Exception:
            graph_config = GraphConnectionConfig(uri="")

        self.graph_engine = GraphRAGEngine(config=graph_config)
        self.text_to_cypher = TextToCypherPipeline(llm=self.llm, graph_engine=self.graph_engine)
        self.sat_graph_api = SATGraphAPI(graph_engine=self.graph_engine)
        self.mdp_agent = MDPAgent(semantic_engine) if semantic_engine is not None else None

        # Initialize basic service scheduler (AaaS-style)
        self.scheduler = ServiceScheduler()
        self._register_core_services()

        # Advanced components
        self.multi_agent_graphrag = MultiAgentGraphRAGEngine(llm=self.llm, graph_engine=self.graph_engine)
        self.agentic_kgr = AgenticKGR(llm=self.llm, graph_engine=self.graph_engine)
        self.graph_search = GraphSearch(graph_engine=self.graph_engine)
        self.clause_reasoner = CLAUSEReasoner(llm=self.llm)
        self.graph_r1 = GraphR1()
        self.input_parser = InputParser()
        self.task_classifier = TaskClassifier()
        self.planner = Planner()
    
    def run_query(
        self,
        query: str,
        mode: str = "manual",
        stream: bool = False,
    ) -> Dict[str, Any]:
        """
        Run a query through the ReAct agent.
        
        Args:
            query: User query or task
            mode: "manual" (require confirmation) or "auto" (execute when safe)
            stream: Whether to stream results (not implemented yet)
        
        Returns:
            Dict with final result, sources, actions, etc.
        """
        # Advanced "enterprise" pipeline para modos especiales
        if mode in {"advanced", "deep_search", "neuro_symbolic", "self_improve"}:
            return self._run_advanced_pipeline(query=query, mode=mode)

        # Special modes for GraphRAG / SAT-Graph
        if mode in {"graph", "legal_graph"}:
            return self._run_legal_graph_query(query=query, mode=mode)

        if self.graph is None:
            return {
                "error": "Agent not initialized",
                "summary": "The ReAct graph could not be initialized. Check logs.",
            }

        start_time = time.time()
        
        try:
            # Initialize state with goal and cycle limits
            from .workflows.react_graph import initialize_state
            inputs = initialize_state(query, max_cycles=6)
            
            # Run the graph
            # LangGraph con checkpointer requiere un 'configurable.thread_id'
            run_config = {"configurable": {"thread_id": f"ra-{int(start_time * 1000)}"}}
            if stream:
                # Stream mode (for future implementation)
                final_state = None
                for state in self.graph.stream(inputs, stream_mode="values", config=run_config):
                    final_state = state
                result_state = final_state
            else:
                # Invoke mode (single call)
                result_state = self.graph.invoke(inputs, config=run_config)
            
            # Extract final message
            messages = result_state.get("messages", [])
            if not messages:
                return {
                    "error": "No response generated",
                    "summary": "The agent did not generate a response."
                }
            
            final_message = messages[-1]
            content = getattr(final_message, "content", str(final_message))
            
            # Try to parse as JSON
            try:
                parsed_result = json.loads(content)
            except json.JSONDecodeError:
                # If not JSON, wrap in a result structure
                parsed_result = {
                    "summary": content,
                    "score": 0.5,
                    "sources": [],
                    "actions_recommended": [],
                    "actions_executed": [],
                    "log": [],
                    "confidence": 0.5
                }
            
            # Calculate execution time
            execution_time_ms = int((time.time() - start_time) * 1000)
            
            # Build log
            log = {
                "query": query,
                "mode": mode,
                "steps": len(messages),
                "execution_time_ms": execution_time_ms,
                "messages": [
                    {
                        "role": getattr(msg, "role", type(msg).__name__),
                        "content": getattr(msg, "content", str(msg))[:200]
                    }
                    for msg in messages
                ]
            }
            
            # Save audit log
            save_audit_log(
                query=query,
                mode=mode,
                log=log,
                final_result=parsed_result,
                execution_time_ms=execution_time_ms
            )
            
            # Add execution metadata
            parsed_result["execution_time_ms"] = execution_time_ms
            parsed_result["steps_count"] = len(messages)
            
            return parsed_result
            
        except Exception as e:
            error_result = {
                "error": str(e),
                "summary": f"Error during agent execution: {str(e)}",
                "score": 0.0,
                "sources": [],
                "actions_recommended": [],
                "actions_executed": [],
                "log": [],
                "confidence": 0.0
            }
            
            # Save error to audit
            save_audit_log(
                query=query,
                mode=mode,
                log={"error": str(e)},
                final_result=error_result,
                execution_time_ms=int((time.time() - start_time) * 1000)
            )
            
            return error_result

    # ------------------------------------------------------------------
    # Specialized pipelines
    # ------------------------------------------------------------------

    def _run_advanced_pipeline(self, query: str, mode: str) -> Dict[str, Any]:
        """Pipeline completo: Input → Intent → Plan → GraphRAG → Evidencia → (opcional acciones)."""
        start_time = time.time()

        parsed: ParsedInput = self.input_parser.parse(query, extra={})
        intent: TaskIntent = self.task_classifier.classify(parsed)
        plan: ExecutionGraph = self.planner.build_plan(intent, parsed)

        # Ejecutar plan con ServiceScheduler
        graph_result = self.scheduler.run_graph(plan, initial_context={"query": query})
        context = graph_result.get("context", {})

        # Opcional: usar Multi-Agent GraphRAG para deep search si el intent lo sugiere
        graphrag_info = None
        if intent.intent in {"research", "risk_assessment", "deep_search"}:
            graphrag_info = self.multi_agent_graphrag.deep_search(query)

        # Construir explicación (CLAUSE)
        evidences = graphrag_info.get("evidences", []) if graphrag_info else []
        explanation = self.clause_reasoner.build_explanation_tree(question=query, evidences=evidences)

        execution_time_ms = int((time.time() - start_time) * 1000)

        result_payload: Dict[str, Any] = {
            "summary": context.get("research", context.get("research_default", {})).get("summary", ""),
            "score": 0.0,
            "sources": context.get("research", context.get("research_default", {})).get("sources", []),
            "actions_recommended": [],
            "actions_executed": [],
            "log": graph_result.get("log", []),
            "graphrag": graphrag_info,
            "explanation_tree": explanation.description,
            "mode": mode,
            "intent": intent.intent,
            "execution_time_ms": execution_time_ms,
        }

        save_audit_log(
            query=query,
            mode=mode,
            log={"pipeline": "advanced", "intent": intent.intent, "plan_nodes": list(plan.nodes.keys())},
            final_result=result_payload,
            execution_time_ms=execution_time_ms,
        )

        return result_payload

    def _run_legal_graph_query(self, query: str, mode: str = "legal_graph") -> Dict[str, Any]:
        """Run a legal/graph-oriented query using SAT-Graph + Text-to-Cypher.

        This is a minimal end-to-end demo path:
        - Resolve a legal item reference (SAT-Graph primitive).
        - Run a Text→Cypher pipeline against the graph.
        - Build an auditable JSON result.
        """
        start_time = time.time()

        # 1) Resolve item (mock-friendly)
        candidates = self.sat_graph_api.resolve_item_reference(query, top_k=1)
        item = candidates[0] if candidates else None

        # 2) Run Text-to-Cypher over the question directly
        cypher_result = self.text_to_cypher.run(question=query)

        # 3) Build response
        execution_time_ms = int((time.time() - start_time) * 1000)
        summary = ""
        sources: List[Dict[str, Any]] = []

        # Use MDP-Agent if available to enrich context (optional)
        if self.mdp_agent is not None:
            try:
                mdp_result = self.mdp_agent.synthesize_answer(query, k=5)
                summary = mdp_result.get("summary", "")
                sources = mdp_result.get("sources", [])
            except Exception as e:
                summary = f"Resultado de Cypher, pero MDP-Agent falló: {e}"
        else:
            summary = "Consulta ejecutada sobre grafo (ver resultados crudos en 'graph_rows')."

        result_payload: Dict[str, Any] = {
            "summary": summary,
            "score": 0.0,
            "sources": sources,
            "actions_recommended": [],
            "actions_executed": [],
            "log": [
                {
                    "step": "resolve_item_reference",
                    "tool_used": "SATGraphAPI.resolve_item_reference",
                    "result": item,
                },
                {
                    "step": "text_to_cypher",
                    "tool_used": "TextToCypherPipeline.run",
                    "result": {
                        "success": cypher_result.success,
                        "iterations": cypher_result.iterations,
                        "cypher": cypher_result.cypher,
                    },
                },
            ],
            "graph_rows": cypher_result.rows,
            "cypher": cypher_result.cypher,
            "confidence": 0.0,
            "execution_time_ms": execution_time_ms,
            "steps_count": cypher_result.iterations,
            "mode": mode,
        }

        # Persist audit log
        save_audit_log(
            query=query,
            mode=mode,
            log={
                "pipeline": "legal_graph",
                "item_candidate": item,
                "cypher_feedback_log": cypher_result.feedback_log,
            },
            final_result=result_payload,
            execution_time_ms=execution_time_ms,
        )

        return result_payload
    
    def risk_assessment(self, entity: str, context: Optional[str] = None) -> Dict[str, Any]:
        """
        Perform a risk assessment on an entity (supplier, employee, contract, etc.).
        
        Args:
            entity: Entity to assess (e.g., "proveedor ACME")
            context: Additional context
        
        Returns:
            Risk assessment result
        """
        query = f"Evaluar riesgo de {entity}"
        if context:
            query += f". Contexto: {context}"
        
        return self.run_query(query, mode="manual")
    
    def auto_ticket(self, problem_description: str) -> Dict[str, Any]:
        """
        Automatically create a ticket based on problem description.
        
        Args:
            problem_description: Description of the problem
        
        Returns:
            Ticket creation result
        """
        query = f"Detectar problemas en: {problem_description}. Crear ticket si hay inconsistencias o problemas detectados."
        
        return self.run_query(query, mode="auto")
    
    def research_brief(self, topic: str, depth: str = "standard") -> Dict[str, Any]:
        """
        Generate a research brief on a topic.
        
        Args:
            topic: Research topic
            depth: "quick", "standard", or "deep"
        
        Returns:
            Research brief result
        """
        query = f"Generar informe de investigación sobre: {topic}"
        if depth == "deep":
            query += ". Profundizar en todos los aspectos relevantes."
        elif depth == "quick":
            query += ". Resumen ejecutivo rápido."
        
        return self.run_query(query, mode="manual")

    # ------------------------------------------------------------------
    # AaaS-style service registration
    # ------------------------------------------------------------------

    def _register_core_services(self) -> None:
        """Register core internal services in the scheduler."""

        # Service: legal_graph_query
        def _svc_legal_graph(payload: Dict[str, Any]) -> Dict[str, Any]:
            question = payload.get("query") or payload.get("question", "")
            mode = payload.get("mode", "legal_graph")
            return self._run_legal_graph_query(question, mode=mode)

        self.scheduler.register_service(
            ServiceDescriptor(
                name="legal_graph_query",
                description="Run legal GraphRAG + SAT-Graph pipeline for a question.",
                handler=_svc_legal_graph,
                input_schema={"type": "object", "properties": {"query": {"type": "string"}}},
                output_schema={"type": "object"},
            )
        )

        # Service: mdp_research
        def _svc_mdp_research(payload: Dict[str, Any]) -> Dict[str, Any]:
            question = payload.get("query") or payload.get("question", "")
            if not self.mdp_agent:
                return {
                    "summary": "MDP-Agent no está disponible (sin SemanticDataEngine).",
                    "sources": [],
                }
            return self.mdp_agent.synthesize_answer(question, k=5)

        self.scheduler.register_service(
            ServiceDescriptor(
                name="mdp_research",
                description="Run MDP-Agent style document research + synthesis.",
                handler=_svc_mdp_research,
                input_schema={"type": "object", "properties": {"query": {"type": "string"}}},
                output_schema={"type": "object"},
            )
        )

    def run_execution_graph(self, graph: ExecutionGraph, initial_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Public helper to execute an ExecutionGraph via the internal scheduler."""
        return self.scheduler.run_graph(graph, initial_context=initial_context)


