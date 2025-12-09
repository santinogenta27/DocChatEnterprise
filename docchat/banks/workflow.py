"""
Workflow LangGraph para orquestar los 6 agentes del modo BANKS.
"""

from __future__ import annotations

import logging
from typing import Dict, Any, TypedDict, Annotated
from datetime import datetime

try:
    from langgraph.graph import StateGraph, END
    from langgraph.graph.message import add_messages
    LANGRAPH_AVAILABLE = True
except ImportError:
    LANGRAPH_AVAILABLE = False
    logging.warning("langgraph no disponible")

from docchat.config import AppConfig
from .agents import (
    IngestorAgent,
    ExtractorAgent,
    ScreenerAgent,
    RiskEngineAgent,
    SteeringManagerAgent,
    ReportGeneratorAgent,
    ActionExecutorAgent
)

logger = logging.getLogger(__name__)


class BanksState(TypedDict):
    """Estado del workflow BANKS."""
    input_path: str
    documents: list
    processed_documents: list
    extracted_entities: list
    sanction_hits: list
    pep_hits: list
    adverse_media_hits: list
    risk_scores: list
    steering_commands: list
    steering_applied: list
    generated_reports: list
    actions_executed: list
    action_config: dict
    jurisdiction: str
    errors: list
    workflow_updated: bool
    needs_reprocessing: bool
    batch_mode: bool
    client_id: str


class BanksWorkflow:
    """Workflow multi-agente para compliance KYC/AML."""
    
    def __init__(self, config: AppConfig):
        self.config = config
        
        # Inicializar agentes
        self.ingestor = IngestorAgent(config)
        self.extractor = ExtractorAgent(config)
        self.screener = ScreenerAgent(config)
        self.risk_engine = RiskEngineAgent(config)
        self.steering_manager = SteeringManagerAgent(config)
        self.report_generator = ReportGeneratorAgent(config)
        self.action_executor = ActionExecutorAgent(config)
        
        # Construir grafo
        if LANGRAPH_AVAILABLE:
            self.graph = self._build_graph()
        else:
            self.graph = None
            logger.warning("LangGraph no disponible, usando ejecución secuencial")
    
    def _build_graph(self) -> StateGraph:
        """Construye el grafo de LangGraph."""
        workflow = StateGraph(BanksState)
        
        # Nodos
        workflow.add_node("ingestor", self._ingestor_node)
        workflow.add_node("extractor", self._extractor_node)
        workflow.add_node("screener", self._screener_node)
        workflow.add_node("risk_engine", self._risk_engine_node)
        workflow.add_node("steering_manager", self._steering_manager_node)
        workflow.add_node("report_generator", self._report_generator_node)
        workflow.add_node("action_executor", self._action_executor_node)
        
        # Flujo principal
        workflow.set_entry_point("ingestor")
        workflow.add_edge("ingestor", "extractor")
        workflow.add_edge("extractor", "screener")
        workflow.add_edge("screener", "risk_engine")
        
        # Steering puede interrumpir en cualquier punto
        workflow.add_conditional_edges(
            "risk_engine",
            self._should_apply_steering,
            {
                "steering": "steering_manager",
                "continue": "report_generator"
            }
        )
        
        workflow.add_edge("steering_manager", "extractor")  # Re-procesar después de steering
        workflow.add_edge("report_generator", "action_executor")
        workflow.add_edge("action_executor", END)
        
        return workflow.compile()
    
    def _ingestor_node(self, state: BanksState) -> BanksState:
        """Nodo del Ingestor."""
        try:
            result = self.ingestor.process(dict(state))
            state.update(result)
        except Exception as e:
            logger.error(f"Error en ingestor: {e}")
            if "errors" not in state:
                state["errors"] = []
            state["errors"].append(f"Ingestor error: {str(e)}")
        return state
    
    def _extractor_node(self, state: BanksState) -> BanksState:
        """Nodo del Extractor."""
        try:
            result = self.extractor.process(dict(state))
            state.update(result)
        except Exception as e:
            logger.error(f"Error en extractor: {e}")
            if "errors" not in state:
                state["errors"] = []
            state["errors"].append(f"Extractor error: {str(e)}")
        return state
    
    def _screener_node(self, state: BanksState) -> BanksState:
        """Nodo del Screener."""
        try:
            result = self.screener.process(dict(state))
            state.update(result)
        except Exception as e:
            logger.error(f"Error en screener: {e}")
            if "errors" not in state:
                state["errors"] = []
            state["errors"].append(f"Screener error: {str(e)}")
        return state
    
    def _risk_engine_node(self, state: BanksState) -> BanksState:
        """Nodo del Risk Engine."""
        try:
            result = self.risk_engine.process(dict(state))
            state.update(result)
        except Exception as e:
            logger.error(f"Error en risk engine: {e}")
            if "errors" not in state:
                state["errors"] = []
            state["errors"].append(f"Risk engine error: {str(e)}")
        return state
    
    def _steering_manager_node(self, state: BanksState) -> BanksState:
        """Nodo del Steering Manager."""
        try:
            result = self.steering_manager.process(dict(state))
            state.update(result)
        except Exception as e:
            logger.error(f"Error en steering manager: {e}")
            if "errors" not in state:
                state["errors"] = []
            state["errors"].append(f"Steering manager error: {str(e)}")
        return state
    
    def _report_generator_node(self, state: BanksState) -> BanksState:
        """Nodo del Report Generator."""
        try:
            result = self.report_generator.process(dict(state))
            state.update(result)
        except Exception as e:
            logger.error(f"Error en report generator: {e}")
            if "errors" not in state:
                state["errors"] = []
            state["errors"].append(f"Report generator error: {str(e)}")
        return state
    
    def _action_executor_node(self, state: BanksState) -> BanksState:
        """Nodo del Action Executor."""
        try:
            result = self.action_executor.process(dict(state))
            state.update(result)
        except Exception as e:
            logger.error(f"Error en action executor: {e}")
            if "errors" not in state:
                state["errors"] = []
            state["errors"].append(f"Action executor error: {str(e)}")
        return state
    
    def _should_apply_steering(self, state: BanksState) -> str:
        """Decide si aplicar steering."""
        if state.get("steering_commands") and len(state["steering_commands"]) > 0:
            return "steering"
        return "continue"
    
    def run(
        self,
        input_path: str,
        jurisdiction: str = "US",
        steering_commands: list = None,
        action_config: dict = None,
        batch_mode: bool = False,
        client_id: str = None
    ) -> Dict[str, Any]:
        """
        Ejecuta el workflow completo.
        
        Args:
            input_path: Ruta a carpeta/ZIP/archivo
            jurisdiction: Jurisdicción (US, EU, MX, CO, etc.)
            steering_commands: Lista de comandos de steering en lenguaje natural
            action_config: Configuración de acciones a ejecutar (Salesforce, Jira, Slack, etc.)
            batch_mode: Si es True, procesa múltiples clientes
            client_id: ID del cliente para tracking
        
        Returns:
            Estado final del workflow
        """
        # Estado inicial
        initial_state: BanksState = {
            "input_path": input_path,
            "documents": [],
            "processed_documents": [],
            "extracted_entities": [],
            "sanction_hits": [],
            "pep_hits": [],
            "adverse_media_hits": [],
            "risk_scores": [],
            "steering_commands": steering_commands or [],
            "steering_applied": [],
            "generated_reports": [],
            "actions_executed": [],
            "action_config": action_config or {},
            "jurisdiction": jurisdiction,
            "errors": [],
            "workflow_updated": False,
            "needs_reprocessing": False,
            "batch_mode": batch_mode,
            "client_id": client_id or ""
        }
        
        # Ejecutar workflow
        if self.graph:
            # Con LangGraph
            final_state = self.graph.invoke(initial_state)
        else:
            # Ejecución secuencial sin LangGraph
            final_state = self._run_sequential(initial_state)
        
        return dict(final_state)
    
    def _run_sequential(self, state: BanksState) -> BanksState:
        """Ejecuta el workflow secuencialmente sin LangGraph."""
        try:
            # Ingestor
            logger.info("🔄 Ejecutando Ingestor...")
            state = self._ingestor_node(state)
            
            if not state.get("processed_documents"):
                logger.warning("⚠️ No se procesaron documentos. Verifica la ruta de entrada.")
                if "errors" not in state:
                    state["errors"] = []
                state["errors"].append("No se encontraron documentos para procesar")
                return state
            
            # Extractor
            logger.info("🔄 Ejecutando Extractor...")
            state = self._extractor_node(state)
            
            # Screener
            logger.info("🔄 Ejecutando Screener...")
            state = self._screener_node(state)
            
            # Risk Engine
            logger.info("🔄 Ejecutando Risk Engine...")
            state = self._risk_engine_node(state)
            
            # Steering (si hay comandos)
            if state.get("steering_commands"):
                logger.info("🔄 Aplicando comandos de steering...")
                state = self._steering_manager_node(state)
                # Re-procesar si es necesario
                if state.get("needs_reprocessing"):
                    logger.info("🔄 Re-procesando después de steering...")
                    state = self._extractor_node(state)
                    state = self._screener_node(state)
                    state = self._risk_engine_node(state)
            
            # Report Generator
            logger.info("🔄 Generando reportes...")
            state = self._report_generator_node(state)
            
            # Action Executor
            if state.get("action_config"):
                logger.info("🔄 Ejecutando acciones automáticas...")
                state = self._action_executor_node(state)
            
            logger.info("✅ Workflow completado exitosamente")
            return state
        
        except Exception as e:
            logger.error(f"❌ Error en workflow secuencial: {e}", exc_info=True)
            if "errors" not in state:
                state["errors"] = []
            state["errors"].append(f"Error crítico en workflow: {str(e)}")
            return state

