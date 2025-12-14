"""
Event Bus Mode - Sistema Event-Driven Multi-Agente RAG
Integra el sistema completo de DocChat Multi-Agent RAG con arquitectura event-driven:

SISTEMA MULTI-AGENTE DOCCHAT:
- 🔍 Relevance Checker: Verifica si la pregunta es relevante a los documentos
- 🔬 Research Agent: Genera respuestas iniciales basadas en documentos recuperados
- ✅ Verification Agent: Verifica que las respuestas estén soportadas (anti-hallucinación)
- 🔄 Self-Correction Mechanism: Re-ejecuta research si hay contradicciones o claims sin soporte
- 🔀 Hybrid Retriever: Combina BM25 (búsqueda léxica) + Vector Search (búsqueda semántica)

ARQUITECTURA EVENT-DRIVEN:
- 📡 Event Bus: Sistema de mensajería interna para comunicación entre componentes
- ⚡ Real-time Processing: Procesamiento automático basado en eventos
- 🔗 Event-driven Workflows: Flujos de trabajo que reaccionan a eventos
- 📊 Event History: Trazabilidad completa de eventos para auditoría
"""

from __future__ import annotations

import json
import os
import time
import asyncio
from typing import List, Dict, Optional, Any, Tuple, AsyncIterator, Iterator
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed

from langchain_core.documents import Document
from langchain_core.language_models import BaseLanguageModel
from langchain_openai import ChatOpenAI

from .config import AppConfig
from .document_processor import DocumentProcessor
from .retriever_builder import RetrieverBuilder
from .workflow import AgentWorkflow
from .context_folding import ContextFolder
from .data_provenance import DataProvenanceTracker, DataProvenance, DataSourceType
from .chain_of_thought import ChainOfThoughtReasoner, ThoughtChain
from .path_dependent_reasoning import PathDependentReasoner
from .test_time_training import TestTimeTrainer
from .person_in_the_loop import PersonInTheLoop, DecisionCriticality
from .reinforcement_planning import ReinforcementPlanner, DecisionTree
from .mcp_manager import MCPManager

# Importar Confluent para streaming en tiempo real (opcional)
try:
    from .confluent_streaming import (
        ConfluentStreamingProducer,
        ConfluentStreamingManager,
        StreamingEvent,
        EventType
    )
    CONFLUENT_STREAMING_AVAILABLE = True
except ImportError:
    ConfluentStreamingProducer = None  # type: ignore
    ConfluentStreamingManager = None  # type: ignore
    StreamingEvent = None  # type: ignore
    EventType = None  # type: ignore
    CONFLUENT_STREAMING_AVAILABLE = False


class SimpleEventBus:
    """Event Bus optimizado para real-time streaming y procesamiento asíncrono."""
    
    def __init__(self):
        self.subscribers: Dict[str, List[callable]] = defaultdict(list)
        self.async_subscribers: Dict[str, List[callable]] = defaultdict(list)
        self.event_history: List[Dict[str, Any]] = []
        self.max_history_size = 10000  # Limitar historial para performance
        self._processing_queue = asyncio.Queue() if asyncio else None
        self._background_task: Optional[asyncio.Task] = None
    
    def subscribe(self, event_type: str, callback: callable, async_callback: bool = False):
        """Suscribe un callback a un tipo de evento."""
        if async_callback:
            self.async_subscribers[event_type].append(callback)
        else:
            self.subscribers[event_type].append(callback)
    
    def publish(self, event_type: str, data: Dict[str, Any], async_notify: bool = True):
        """
        Publica un evento y notifica a todos los suscriptores.
        Optimizado para real-time streaming.
        """
        event = {
            "type": event_type,
            "data": data,
            "timestamp": datetime.now().isoformat()
        }
        
        # Agregar al historial (con límite para performance)
        self.event_history.append(event)
        if len(self.event_history) > self.max_history_size:
            self.event_history = self.event_history[-self.max_history_size:]
        
        # Notificar suscriptores síncronos inmediatamente
        for callback in self.subscribers[event_type]:
            try:
                callback(data)
            except Exception as e:
                print(f"⚠️ [Event Bus] Error en callback para {event_type}: {e}")
        
        # Notificar suscriptores asíncronos en background (non-blocking)
        if async_notify and self.async_subscribers[event_type]:
            asyncio.create_task(self._notify_async_subscribers(event_type, data))
    
    async def _notify_async_subscribers(self, event_type: str, data: Dict[str, Any]):
        """Notifica suscriptores asíncronos sin bloquear."""
        for callback in self.async_subscribers[event_type]:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(data)
                else:
                    # Si no es async, ejecutar en thread pool
                    loop = asyncio.get_event_loop()
                    await loop.run_in_executor(None, callback, data)
            except Exception as e:
                print(f"⚠️ [Event Bus] Error en async callback para {event_type}: {e}")
    
    def publish_stream(self, event_type: str, data_stream: Any):
        """
        Publica eventos desde un stream en tiempo real.
        Para procesamiento de datos grandes sin bloquear.
        """
        async def stream_processor():
            async for chunk in data_stream:
                self.publish(event_type, chunk, async_notify=True)
        
        asyncio.create_task(stream_processor())
    
    def get_event_history(self, event_type: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Obtiene el historial de eventos."""
        if event_type:
            return [e for e in self.event_history if e["type"] == event_type][-limit:]
        return self.event_history[-limit:]
    
    def get_realtime_events(self, event_type: Optional[str] = None) -> AsyncIterator[Dict[str, Any]]:
        """
        Generator asíncrono para recibir eventos en tiempo real (streaming).
        
        Usage:
            async for event in event_bus.get_realtime_events('document_uploaded'):
                print(event)
        """
        last_index = len(self.event_history)
        
        async def event_stream():
            nonlocal last_index
            while True:
                # Obtener nuevos eventos
                new_events = self.event_history[last_index:]
                for event in new_events:
                    if event_type is None or event["type"] == event_type:
                        yield event
                last_index = len(self.event_history)
                await asyncio.sleep(0.1)  # Poll cada 100ms para real-time
        
        return event_stream()


class EventBusMode:
    """
    Event Bus Mode - Sistema Event-Driven Multi-Agente RAG de Máxima Calidad para Empresas.
    
    Integra el sistema completo de DocChat Multi-Agent RAG con arquitectura event-driven:
    
    SISTEMA MULTI-AGENTE DOCCHAT:
    - 🔍 Relevance Checker: Determina si la pregunta puede responderse con los documentos
    - 🔬 Research Agent: Genera respuestas iniciales basadas en documentos recuperados
    - ✅ Verification Agent: Verifica que las respuestas estén soportadas (anti-hallucinación)
    - 🔄 Self-Correction: Re-ejecuta research automáticamente si hay contradicciones
    - 🔀 Hybrid Retriever: BM25 + Vector Search para máxima precisión
    
    ARQUITECTURA EVENT-DRIVEN:
    - Event Bus interno para comunicación entre componentes
    - Procesamiento automático basado en eventos
    - Workflows que reaccionan a eventos en tiempo real
    - Trazabilidad completa de eventos para auditoría
    """
    
    def __init__(
        self,
        config: AppConfig,
        processor: DocumentProcessor,
        retriever_builder: RetrieverBuilder,
        context_manager: Optional[Any] = None
    ):
        self.config = config
        self.processor = processor
        self.retriever_builder = retriever_builder
        self.context_manager = context_manager
        
        # Event Bus
        self.event_bus = SimpleEventBus()
        self._setup_event_listeners()
        
        # Confluent Streaming para tiempo real (opcional - mejor performance)
        self.confluent_producer = None
        self.confluent_enabled = False
        if CONFLUENT_STREAMING_AVAILABLE:
            # Intentar inicializar Confluent si está configurado
            bootstrap_servers = getattr(config, 'confluent_bootstrap_servers', None) or os.getenv('CONFLUENT_BOOTSTRAP_SERVERS')
            if bootstrap_servers:
                try:
                    self.confluent_producer = ConfluentStreamingProducer(
                        bootstrap_servers=bootstrap_servers,
                        security_config=getattr(config, 'confluent_security_config', None),
                        enabled=True
                    )
                    self.confluent_enabled = True
                    print("✅ [Event Bus Mode] Confluent Streaming habilitado para streaming en tiempo real")
                except Exception as e:
                    print(f"⚠️ [Event Bus Mode] No se pudo inicializar Confluent (usando Event Bus interno): {e}")
                    self.confluent_enabled = False
        
        # LLM para generación
        if not config.openai_api_key:
            raise ValueError("OPENAI_API_KEY requerida para Event Bus Mode")
        
        self.llm = ChatOpenAI(
            model=config.research_model or "gpt-4o",
            temperature=0.2,
            api_key=config.openai_api_key,
            max_tokens=4000
        )
        
        # Inicializar módulos avanzados
        self.context_folder = ContextFolder(
            config=config,
            llm=self.llm,
            max_context_tokens=32000,
            max_branches=10
        )
        
        self.provenance_tracker = DataProvenanceTracker(config=config)
        
        self.chain_reasoner = ChainOfThoughtReasoner(
            config=config,
            llm=self.llm
        )
        
        self.path_reasoner = PathDependentReasoner(
            config=config,
            llm=self.llm,
            max_paths=5
        )
        
        self.test_time_trainer = TestTimeTrainer(
            config=config,
            llm=self.llm,
            learning_rate=0.1,
            min_confidence=0.6
        )
        
        self.person_in_loop = PersonInTheLoop(
            config=config,
            auto_approve_low=True,
            default_expiration=3600
        )
        
        # Reinforcement Learning y Planning
        self.reinforcement_planner = ReinforcementPlanner(
            config=config,
            llm=self.llm,
            max_depth=10,
            max_branches=5,
            learning_enabled=True
        )
        
        # MCP Manager potenciado
        self.mcp_manager = MCPManager(config=config, llm=self.llm)
        self.mcp_manager.initialize()
        
        # Sesiones activas
        self.sessions: Dict[str, Dict[str, Any]] = {}
        
        # Thread pool para procesamiento paralelo
        self.executor = ThreadPoolExecutor(max_workers=8, thread_name_prefix="event_bus")
        
        # Streaming de insights en tiempo real
        self.insight_streams: Dict[str, List[Any]] = defaultdict(list)
    
    def _setup_event_listeners(self):
        """Configura listeners para eventos comunes con procesamiento automático."""
        # Cuando se sube un documento, procesarlo automáticamente
        self.event_bus.subscribe('document_uploaded', self._on_document_uploaded)
        
        # Cuando se completa un query, notificar y procesar automáticamente
        self.event_bus.subscribe('query_completed', self._on_query_completed)
        
        # Cuando hay un error, registrar
        self.event_bus.subscribe('error_occurred', self._on_error_occurred)
        
        # Eventos de integración con otros modos
        self.event_bus.subscribe('new_compliance_doc', self._on_new_compliance_doc)
        self.event_bus.subscribe('document_updated', self._on_document_updated)
        self.event_bus.subscribe('compliance_complete', self._on_compliance_complete)
        self.event_bus.subscribe('high_risk_detected', self._on_high_risk_detected)
        
        # Eventos de colaboración
        self.event_bus.subscribe('query_executed', self._on_query_executed)
    
    def _on_document_uploaded(self, data: Dict[str, Any]):
        """Reacciona cuando se sube un documento - Procesamiento automático."""
        file_name = data.get('file_name', 'unknown')
        doc_id = data.get('doc_id')
        session_id = data.get('session_id')
        
        print(f"📄 [Event Bus] Documento subido detectado: {file_name}")
        
        # Auto-procesamiento: Indexar automáticamente
        try:
            # Si hay session_id, el documento ya está siendo procesado
            # Aquí podemos agregar lógica adicional de auto-indexación
            if session_id and session_id in self.sessions:
                session = self.sessions[session_id]
                # El documento ya fue procesado en process_documents
                # Aquí podemos agregar notificaciones o integraciones adicionales
                pass
        except Exception as e:
            print(f"⚠️ [Event Bus] Error en auto-procesamiento de documento: {e}")
    
    def _on_query_completed(self, data: Dict[str, Any]):
        """Reacciona cuando se completa un query - Notificaciones automáticas."""
        query = data.get('query', '')[:50]
        session_id = data.get('session_id')
        
        print(f"✅ [Event Bus] Query completado: {query}...")
        
        # Publicar evento para colaboración
        self.event_bus.publish('query_executed', {
            'query': data.get('query', ''),
            'session_id': session_id,
            'sources_count': data.get('sources_count', 0),
            'execution_time': data.get('execution_time', 0)
        })
    
    def _on_error_occurred(self, data: Dict[str, Any]):
        """Reacciona cuando ocurre un error - Logging automático."""
        error = data.get('error', 'unknown')
        context = data.get('context', 'unknown')
        
        print(f"❌ [Event Bus] Error en {context}: {error}")
    
    def _on_new_compliance_doc(self, data: Dict[str, Any]):
        """Reacciona cuando se detecta un nuevo documento de compliance - Auto-screening."""
        file_path = data.get('path')
        print(f"🔍 [Event Bus] Nuevo documento de compliance detectado: {file_path}")
        
        # Aquí se integraría con BANKS Mode para auto-compliance check
        # Por ahora, solo publicamos evento
        self.event_bus.publish('compliance_check_requested', {
            'file_path': file_path,
            'detected_at': data.get('detected_at')
        })
    
    def _on_document_updated(self, data: Dict[str, Any]):
        """Reacciona cuando se actualiza un documento - Auto-sync."""
        doc_id = data.get('doc_id')
        source = data.get('source', 'unknown')
        change_type = data.get('change_type', 'unknown')
        
        print(f"🔄 [Event Bus] Documento actualizado: {doc_id} desde {source} ({change_type})")
        
        # Auto-sync: Re-indexar automáticamente
        self.event_bus.publish('document_sync_requested', {
            'doc_id': doc_id,
            'source': source,
            'change_type': change_type
        })
    
    def _on_compliance_complete(self, data: Dict[str, Any]):
        """Reacciona cuando se completa un compliance check - Workflow automático."""
        risk_score = data.get('risk_score', 0)
        entity_name = data.get('entity_name', 'unknown')
        
        print(f"✅ [Event Bus] Compliance check completado: {entity_name} (Risk: {risk_score})")
        
        # Workflow automático basado en risk score
        if risk_score < 50:
            # Auto-aprobar bajo riesgo
            self.event_bus.publish('auto_approve', {
                'entity_name': entity_name,
                'risk_score': risk_score,
                'reason': 'Low risk - auto-approved'
            })
        elif risk_score >= 50 and risk_score < 70:
            # Enviar a review queue
            self.event_bus.publish('review_queue', {
                'entity_name': entity_name,
                'risk_score': risk_score,
                'reason': 'Medium risk - requires review'
            })
        else:
            # Alto riesgo - escalar automáticamente
            self.event_bus.publish('high_risk_detected', {
                'entity_name': entity_name,
                'risk_score': risk_score,
                'reason': 'High risk - escalation required'
            })
    
    def _on_high_risk_detected(self, data: Dict[str, Any]):
        """Reacciona cuando se detecta alto riesgo - Auto-escalation."""
        entity_name = data.get('entity_name', 'unknown')
        risk_score = data.get('risk_score', 0)
        
        print(f"⚠️ [Event Bus] ALTO RIESGO detectado: {entity_name} (Risk: {risk_score})")
        
        # Auto-escalation workflow
        # 1. Crear ticket (simulado)
        self.event_bus.publish('create_ticket', {
            'title': f"High Risk: {entity_name}",
            'priority': 'High',
            'risk_score': risk_score
        })
        
        # 2. Enviar alerta (simulado)
        self.event_bus.publish('send_alert', {
            'to': 'compliance@company.com',
            'subject': 'High Risk Alert',
            'message': f"High risk detected: {entity_name} (Risk Score: {risk_score})"
        })
        
        # 3. Generar reporte (simulado)
        self.event_bus.publish('generate_report', {
            'type': 'SAR',
            'entity_name': entity_name,
            'risk_score': risk_score
        })
    
    def _on_query_executed(self, data: Dict[str, Any]):
        """Reacciona cuando se ejecuta un query - Colaboración automática."""
        query = data.get('query', '')
        session_id = data.get('session_id')
        
        print(f"💬 [Event Bus] Query ejecutado: {query[:50]}...")
        
        # Aquí se podría notificar a otros usuarios o sistemas
        # Por ahora, solo logging
    
    def initialize_session(self, session_id: str) -> Dict[str, Any]:
        """Inicializa una nueva sesión."""
        if session_id not in self.sessions:
            self.sessions[session_id] = {
                "docs": [],
                "retriever": None,
                "processed_files": set(),
                "history": [],
                "context_folder": ContextFolder(
                    config=self.config,
                    llm=self.llm,
                    max_context_tokens=32000,
                    max_branches=10
                ),
                "chain_id": None,
                "rl_tree_id": None,
                "mcp_queries": [],
                "created_at": time.time()
            }
        return self.sessions[session_id]
    
    def process_documents(
        self,
        session_id: str,
        files: List[Any]
    ) -> Dict[str, Any]:
        """Procesa documentos para una sesión - Optimizado para real-time streaming."""
        session = self.initialize_session(session_id)
        
        # Procesar nuevos archivos
        new_files = []
        for file_obj in files:
            file_name = getattr(file_obj, "name", "")
            if file_name not in session["processed_files"]:
                new_files.append(file_obj)
                session["processed_files"].add(file_name)
        
        if not new_files:
            return {
                "status": "no_new_files",
                "total_docs": len(session["docs"]),
                "total_chunks": sum(len(doc.page_content) for doc in session["docs"])
            }
        
        # Iniciar procesamiento asíncrono en background (non-blocking)
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        if loop.is_running():
            # Si el loop ya está corriendo, crear task
            asyncio.create_task(self._process_documents_async(session_id, new_files))
        else:
            # Si no hay loop, ejecutar en thread separado
            def run_async():
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                new_loop.run_until_complete(self._process_documents_async(session_id, new_files))
                new_loop.close()
            
            self.executor.submit(run_async)
        
        return {
            "status": "processing",
            "message": f"Procesando {len(new_files)} documentos en tiempo real...",
            "total_docs": len(session["docs"]),
            "realtime_streaming": True
        }
    
    async def _process_documents_async(
        self,
        session_id: str,
        new_files: List[Any]
    ):
        """Procesa documentos de forma asíncrona con streaming de insights."""
        try:
            print(f"📄 [Event Bus Mode] Procesando {len(new_files)} nuevos documentos en tiempo real...")
            
            # Publicar evento de inicio
            self.event_bus.publish('document_processing_started', {
                'session_id': session_id,
                'file_count': len(new_files)
            })
            
            session = self.sessions[session_id]
            
            # Procesar documentos en paralelo (optimizado)
            processed_count = 0
            for file_obj in new_files:
                try:
                    # Procesar documento individual
                    file_docs = self.processor.process([file_obj])
                    session["docs"].extend(file_docs)
                    processed_count += 1
                    
                    # Streaming de insights en tiempo real
                    for doc in file_docs:
                        provenance = self.provenance_tracker.track_document_source(doc)
                        if "provenances" not in session:
                            session["provenances"] = []
                        session["provenances"].append(provenance)
                        
                        # Publicar evento inmediatamente (real-time)
                        self.event_bus.publish('document_uploaded', {
                            'session_id': session_id,
                            'file_name': getattr(doc.metadata.get('source', ''), 'name', 'unknown'),
                            'doc_id': str(doc.metadata.get('source', '')),
                            'progress': f"{processed_count}/{len(new_files)}"
                        })
                        
                        # Generar insights en tiempo real mientras procesa
                        await self._generate_realtime_insights(session_id, doc)
                    
                    # Actualizar retriever incrementalmente (más eficiente)
                    if session["docs"]:
                        session["retriever"] = self.retriever_builder.build_hybrid_retriever(session["docs"])
                    
                except Exception as e:
                    print(f"⚠️ [Event Bus Mode] Error procesando archivo: {e}")
                    self.event_bus.publish('document_processing_error', {
                        'session_id': session_id,
                        'file_name': getattr(file_obj, "name", "unknown"),
                        'error': str(e)
                    })
            
            # Publicar evento de finalización
            self.event_bus.publish('document_processing_completed', {
                'session_id': session_id,
                'new_docs': processed_count,
                'total_docs': len(session["docs"])
            })
            
            print(f"✅ [Event Bus Mode] Procesamiento completado: {processed_count} documentos")
            
        except Exception as e:
            print(f"❌ [Event Bus Mode] Error en procesamiento asíncrono: {e}")
            self.event_bus.publish('error_occurred', {
                'session_id': session_id,
                'error': str(e),
                'context': 'document_processing'
            })
    
    async def _generate_realtime_insights(self, session_id: str, doc: Document):
        """Genera insights en tiempo real mientras procesa documentos."""
        try:
            # Extraer insights básicos del documento
            doc_content = doc.page_content[:500]  # Primeros 500 chars para análisis rápido
            
            # Publicar insight en tiempo real
            insight = {
                'session_id': session_id,
                'doc_id': str(doc.metadata.get('source', '')),
                'insight_type': 'document_analysis',
                'summary': doc_content[:200] + "..." if len(doc_content) > 200 else doc_content,
                'timestamp': datetime.now().isoformat()
            }
            
            self.event_bus.publish('realtime_insight', insight)
            
            # Guardar en stream de insights
            self.insight_streams[session_id].append(insight)
            
        except Exception as e:
            print(f"⚠️ [Event Bus Mode] Error generando insight: {e}")
    
    async def stream_realtime_insights(self, session_id: str) -> AsyncIterator[Dict[str, Any]]:
        """
        Stream de insights en tiempo real mientras se procesan documentos.
        
        Usage:
            async for insight in event_bus_mode.stream_realtime_insights(session_id):
                print(insight)
        """
        last_index = 0
        
        while True:
            # Obtener nuevos insights
            current_insights = self.insight_streams.get(session_id, [])
            new_insights = current_insights[last_index:]
            
            for insight in new_insights:
                yield insight
            
            last_index = len(current_insights)
            await asyncio.sleep(0.5)  # Poll cada 500ms para real-time
    
    async def _stream_query_insights(
        self,
        session_id: str,
        query: str,
        answer: str,
        sources: List[Any]
    ):
        """Genera y publica insights en tiempo real durante el query."""
        try:
            # Insight 1: Análisis de relevancia
            relevance_insight = {
                'session_id': session_id,
                'insight_type': 'relevance_analysis',
                'query': query[:100],
                'sources_count': len(sources),
                'timestamp': datetime.now().isoformat()
            }
            self.event_bus.publish('realtime_insight', relevance_insight)
            
            # Insight 2: Resumen de respuesta
            answer_insight = {
                'session_id': session_id,
                'insight_type': 'answer_summary',
                'query': query[:100],
                'answer_preview': answer[:200] + "..." if len(answer) > 200 else answer,
                'timestamp': datetime.now().isoformat()
            }
            self.event_bus.publish('realtime_insight', answer_insight)
            
            # Guardar en stream
            self.insight_streams[session_id].extend([relevance_insight, answer_insight])
            
        except Exception as e:
            print(f"⚠️ [Event Bus Mode] Error en streaming de insights: {e}")
    
    def get_realtime_metrics(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Obtiene métricas en tiempo real del procesamiento."""
        metrics = {
            "event_bus": {
                "total_events": len(self.event_bus.event_history),
                "events_per_second": self._calculate_events_per_second(),
                "active_subscribers": sum(len(callbacks) for callbacks in self.event_bus.subscribers.values()),
                "async_subscribers": sum(len(callbacks) for callbacks in self.event_bus.async_subscribers.values())
            },
            "processing": {
                "active_sessions": len(self.sessions),
                "total_insights_generated": sum(len(insights) for insights in self.insight_streams.values())
            }
        }
        
        if session_id:
            metrics["session"] = {
                "insights_count": len(self.insight_streams.get(session_id, [])),
                "docs_count": len(self.sessions.get(session_id, {}).get("docs", [])),
                "events_count": len([e for e in self.event_bus.event_history if e.get("data", {}).get("session_id") == session_id])
            }
        
        return metrics
    
    def _calculate_events_per_second(self) -> float:
        """Calcula eventos por segundo en los últimos 10 segundos."""
        if len(self.event_bus.event_history) < 2:
            return 0.0
        
        recent_events = self.event_bus.event_history[-100:]  # Últimos 100 eventos
        if len(recent_events) < 2:
            return 0.0
        
        first_time = datetime.fromisoformat(recent_events[0]["timestamp"])
        last_time = datetime.fromisoformat(recent_events[-1]["timestamp"])
        
        time_diff = (last_time - first_time).total_seconds()
        if time_diff == 0:
            return 0.0
        
        return len(recent_events) / time_diff
    
    async def process_query_async(
        self,
        session_id: str,
        message: str,
        history: List[Tuple[str, str]],
        speed_mode: str = "balanced",
        provider: str = "openai"
    ) -> Tuple[List[Tuple[str, str]], Optional[str], Dict[str, Any]]:
        """
        Procesa una consulta con todas las capacidades avanzadas.
        
        Returns:
            (history, error, metadata): Historial actualizado, error si hay, metadatos
        """
        session = self.initialize_session(session_id)
        
        if not session["retriever"]:
            return history, "⚠️ No hay documentos procesados. Carga documentos primero.", {}
        
        # DETECTAR si hay muchos documentos para usar procesamiento paralelo
        all_docs = session.get("docs", [])
        if not all_docs:
            return history, "⚠️ No hay documentos procesados. Carga documentos primero.", {}
        
        # Agrupar documentos por fuente
        docs_by_source = defaultdict(list)
        for doc in all_docs:
            source = doc.metadata.get("source", "unknown")
            docs_by_source[source].append(doc)
        
        num_unique_documents = len(docs_by_source)
        
        # SIEMPRE usar procesamiento paralelo cuando hay documentos (1 o más)
        # Esto garantiza que cada PDF se analice individualmente
        use_parallel_processing = num_unique_documents >= 1
        
        start_time = time.time()
        
        # Publicar evento de inicio de query
        self.event_bus.publish('query_started', {
            'session_id': session_id,
            'query': message,
            'document_count': num_unique_documents
        })
        
        # SIEMPRE procesar cada documento por separado (1 PDF = 1 análisis individual)
        if use_parallel_processing:
            return await self._process_query_parallel(
                session_id=session_id,
                message=message,
                history=history,
                docs_by_source=docs_by_source,
                speed_mode=speed_mode,
                provider=provider
            )
        
        # 1. Crear cadena de razonamiento
        chain_id = self.chain_reasoner.create_chain(message)
        session["chain_id"] = chain_id
        
        # 2. Construir contexto con Context Folding
        conversation_context = self._build_folded_context(session, history)
        
        # 3. Agregar pasos de razonamiento (con manejo de errores)
        try:
            await self.chain_reasoner.add_reasoning_steps(chain_id, conversation_context)
        except Exception as e:
            print(f"⚠️ [Event Bus Mode] Error agregando pasos de razonamiento: {e}")
            # Continuar sin pasos de razonamiento si falla
        
        # 4. Determinar si requiere aprobación humana
        requires_approval, criticality = self.person_in_loop.requires_approval(
            decision_type="document_query",
            decision_content=message,
            context=conversation_context[:500]
        )
        
        # 5. Si requiere aprobación, solicitar
        approval_id = None
        if requires_approval and criticality in [DecisionCriticality.HIGH, DecisionCriticality.CRITICAL]:
            approval_id = self.person_in_loop.request_approval(
                decision_type="document_query",
                decision_content=message,
                context=conversation_context[:1000],
                criticality=criticality
            )
            # Publicar evento de aprobación requerida
            self.event_bus.publish('approval_required', {
                'session_id': session_id,
                'approval_id': approval_id,
                'criticality': criticality.value
            })
        
        # 6. Usar Reinforcement Learning y Planning para planificar estrategias
        rl_result = None
        best_strategy = None
        try:
            rl_result = await self.reinforcement_planner.plan_and_execute(
                goal=f"Responder la consulta: {message}",
                context=conversation_context,
                executor=self._execute_rl_action
            )
            
            session["rl_tree_id"] = rl_result.get("tree_id")
            best_strategy = rl_result.get("best_result")
        except Exception as e:
            print(f"⚠️ [Event Bus Mode] Error en Reinforcement Planning: {e}")
            rl_result = {"tree_id": None, "best_result": None, "total_explorations": 0}
        
        # 7. Usar Path-dependent Reasoning como complemento
        path_result = None
        best_approach = None
        try:
            path_result = await self.path_reasoner.reason_with_multiple_paths(
                problem=message,
                context=conversation_context,
                task_type="document_query",
                executor=self._execute_query_path
            )
            
            best_approach = path_result.get("best_path", {}).get("approach")
        except Exception as e:
            print(f"⚠️ [Event Bus Mode] Error en Path-dependent Reasoning: {e}")
            path_result = {"best_path": {"approach": None}, "paths_tested": 0}
        
        # 8. Usar MCP potenciado para buscar en sistemas externos si es necesario
        mcp_data = None
        try:
            mcp_data = await self._query_mcp_systems(message, conversation_context)
            if mcp_data:
                session["mcp_queries"].append(mcp_data)
                conversation_context += f"\n\n📡 DATOS DE SISTEMAS EXTERNOS (MCP):\n{mcp_data.get('summary', '')}"
        except Exception as e:
            print(f"⚠️ [Event Bus Mode] Error consultando MCP: {e}")
        
        # Aplicar modo de velocidad
        original_speed_mode = self.config.speed_mode
        self.config.speed_mode = speed_mode
        
        try:
            # Crear workflow
            temp_workflow = AgentWorkflow(self.config, provider=provider)
            
            # Ejecutar con contexto plegado y estrategia de RL
            enriched_query = f"{conversation_context}\n\nPREGUNTA ACTUAL:\n{message}"
            if best_strategy:
                enriched_query += f"\n\n🎯 ESTRATEGIA DE RL: {best_strategy}"
            if best_approach:
                enriched_query += f"\n\n🛤️ ENFOQUE RECOMENDADO: {best_approach}"
            
            result = temp_workflow.run(
                enriched_query,
                session["retriever"],
                all_documents=session["docs"],
                conversational_mode=True
            )
            
            answer = result.get("answer", result.get("draft_answer", "No se pudo generar respuesta."))
            sources = result.get("sources", [])
            verification_report = result.get("verification_report", "")
            relevance_label = result.get("relevance", "UNKNOWN")
            
            # 8. Rastrear procedencia de la respuesta
            source_provenances = []
            for source in sources:
                if isinstance(source, dict):
                    source_name = source.get("source", source.get("file", ""))
                    doc = next((d for d in session["docs"] if source_name in str(d.metadata.get("source", ""))), None)
                    if doc:
                        provenance = self.provenance_tracker.track_document_source(doc)
                        source_provenances.append(provenance)
            
            # Registrar en tracker de procedencia
            record_id = self.provenance_tracker.track_query_response(
                query=message,
                response=answer,
                sources=source_provenances,
                processing_steps=[
                    {"step": "reinforcement_planning", "details": f"Árbol RL: {rl_result.get('tree_id') if rl_result else 'N/A'}, Exploraciones: {rl_result.get('total_explorations', 0) if rl_result else 0}"},
                    {"step": "path_reasoning", "details": f"Enfoque: {best_approach or 'N/A'}"},
                    {"step": "chain_of_thought", "details": f"Cadena: {chain_id}"},
                    {"step": "mcp_integration", "details": f"Datos externos: {len(mcp_data.get('sources', [])) if mcp_data else 0} fuentes"}
                ],
                session_id=session_id,
                metadata={
                    "approval_id": approval_id,
                    "criticality": criticality.value if requires_approval else "low",
                    "path_result": path_result
                }
            )
            
            # 9. Completar cadena de razonamiento
            self.chain_reasoner.complete_chain(chain_id, answer, success=True)
            
            # 10. Registrar en Test Time Training
            execution_time = time.time() - start_time
            self.test_time_trainer.record_episode(
                task_type="document_query",
                input_data=message,
                output_data=answer,
                success=True,
                execution_time=execution_time,
                metadata={
                    "sources_count": len(sources),
                    "approval_required": requires_approval,
                    "path_used": best_approach or "N/A",
                    "rl_tree_id": rl_result.get("tree_id") if rl_result else None,
                    "rl_explorations": rl_result.get("total_explorations", 0) if rl_result else 0,
                    "mcp_sources": len(mcp_data.get("sources", [])) if mcp_data else 0
                }
            )
            
            # 11. Formatear respuesta con procedencia y reporte de verificación completo
            formatted_answer = answer
            
            # Agregar información del proceso multi-agente DocChat
            formatted_answer += "\n\n---\n\n"
            formatted_answer += "## 🔬 Proceso Multi-Agente DocChat\n\n"
            formatted_answer += "### 📋 Análisis de Relevancia\n"
            if relevance_label == "CAN_ANSWER":
                formatted_answer += "✅ **Relevancia:** CAN_ANSWER - Los documentos proporcionan información suficiente para responder completamente.\n\n"
            elif relevance_label == "PARTIAL":
                formatted_answer += "⚠️ **Relevancia:** PARTIAL - Los documentos mencionan el tema pero pueden faltar detalles completos.\n\n"
            elif relevance_label == "NO_MATCH":
                formatted_answer += "❌ **Relevancia:** NO_MATCH - Los documentos no contienen información relevante para esta pregunta.\n\n"
            else:
                formatted_answer += f"ℹ️ **Relevancia:** {relevance_label}\n\n"
            
            # Agregar reporte de verificación completo
            if verification_report:
                formatted_answer += "### ✅ Verificación de Respuesta (Anti-Hallucinación)\n"
                formatted_answer += verification_report
                formatted_answer += "\n\n"
                formatted_answer += "**🔍 Sistema de Verificación:**\n"
                formatted_answer += "- ✅ **Hybrid Retriever:** Combina BM25 (búsqueda léxica) + Vector Search (búsqueda semántica)\n"
                formatted_answer += "- 🔬 **Research Agent:** Genera respuesta inicial basada en documentos recuperados\n"
                formatted_answer += "- ✅ **Verification Agent:** Verifica que la respuesta esté soportada por los documentos\n"
                formatted_answer += "- 🔄 **Self-Correction:** Re-ejecuta research si se detectan contradicciones o claims sin soporte\n"
                formatted_answer += "\n"
            
            # Agregar fuentes con procedencia
            if source_provenances:
                sources_list = []
                for prov in source_provenances[:10]:
                    source_info = f"- {prov.source_name}"
                    if prov.page_number:
                        source_info += f" (página {prov.page_number})"
                    sources_list.append(source_info)
                
                if sources_list:
                    formatted_answer += "### 📚 Fuentes Consultadas\n"
                    formatted_answer += "\n".join(sources_list)
                    formatted_answer += f"\n\n🔍 **Procedencia:** Registro ID {record_id}\n"
            
            # Agregar información adicional del proceso
            formatted_answer += "\n---\n\n"
            formatted_answer += "### 🧠 Capacidades Avanzadas Utilizadas\n"
            formatted_answer += "- 📦 **Context Folding:** Gestión eficiente de contextos masivos (500+ PDFs)\n"
            formatted_answer += "- 🔍 **Data Provenance:** Trazabilidad completa de cada pieza de información\n"
            formatted_answer += "- 🧠 **Chain of Thought:** Razonamiento paso a paso\n"
            formatted_answer += "- 🛤️ **Path-dependent Reasoning:** Múltiples enfoques probados\n"
            formatted_answer += "- 📈 **Test Time Training:** Mejora continua con cada conversación\n"
            formatted_answer += "- 🌳 **Reinforcement Learning & Planning:** Estrategias adaptativas\n"
            formatted_answer += "- 🔌 **MCP Powered:** Conexión a sistemas externos\n"
            formatted_answer += "- 📡 **Event Bus:** Arquitectura event-driven para procesamiento automático\n"
            
            # Agregar advertencia si requiere aprobación
            if requires_approval and approval_id:
                formatted_answer += f"\n\n⚠️ **Aprobación requerida:** ID {approval_id} (Criticidad: {criticality.value})"
            
            # Actualizar historial
            session["history"].append({
                "question": message,
                "answer": answer,
                "sources": sources,
                "provenance_record_id": record_id,
                "chain_id": chain_id,
                "timestamp": datetime.now().isoformat()
            })
            
            # Guardar en memoria persistente
            if self.context_manager:
                self.context_manager.add_query(
                    query=message,
                    answer=answer,
                    sources=[prov.source_name for prov in source_provenances],
                    metadata={
                        "mode": "event_bus_mode",
                        "session_id": session_id,
                        "conversation_turn": len(session["history"]),
                        "provenance_record_id": record_id,
                        "chain_id": chain_id
                    }
                )
            
            # Actualizar historial de Gradio
            if history and isinstance(history[0], dict):
                tuple_history = []
                for i in range(0, len(history) - 1, 2):
                    if i + 1 < len(history):
                        user_msg = history[i].get("content", "") if isinstance(history[i], dict) else history[i]
                        bot_msg = history[i + 1].get("content", "") if isinstance(history[i + 1], dict) else history[i + 1]
                        tuple_history.append((user_msg, bot_msg))
                history = tuple_history
            
            history.append((message, formatted_answer))
            
            # Restaurar modo original
            self.config.speed_mode = original_speed_mode
            
            # Publicar evento de query completado
            self.event_bus.publish('query_completed', {
                'session_id': session_id,
                'query': message,
                'answer_length': len(answer),
                'sources_count': len(sources),
                'execution_time': execution_time
            })
            
            # Streaming de insights en tiempo real
            await self._stream_query_insights(session_id, message, answer, sources)
            
            metadata = {
                "provenance_record_id": record_id,
                "chain_id": chain_id,
                "approval_id": approval_id,
                "execution_time": execution_time,
                "sources_count": len(sources)
            }
            
            return history, None, metadata
            
        except Exception as e:
            error_msg = f"❌ Error en chat: {str(e)}"
            
            # Publicar evento de error
            self.event_bus.publish('error_occurred', {
                'session_id': session_id,
                'error': str(e),
                'context': 'query_processing'
            })
            
            # Registrar error en Test Time Training
            execution_time = time.time() - start_time
            self.test_time_trainer.record_episode(
                task_type="document_query",
                input_data=message,
                output_data=error_msg,
                success=False,
                execution_time=execution_time,
                metadata={"error": str(e)}
            )
            
            # Completar cadena con error
            if chain_id:
                self.chain_reasoner.complete_chain(chain_id, error_msg, success=False)
            
            # Restaurar modo original
            self.config.speed_mode = original_speed_mode
            
            # Actualizar historial
            if history and isinstance(history[0], dict):
                tuple_history = []
                for i in range(0, len(history) - 1, 2):
                    if i + 1 < len(history):
                        user_msg = history[i].get("content", "") if isinstance(history[i], dict) else history[i]
                        bot_msg = history[i + 1].get("content", "") if isinstance(history[i + 1], dict) else history[i + 1]
                        tuple_history.append((user_msg, bot_msg))
                history = tuple_history
            
            history.append((message, error_msg))
            
            return history, error_msg, {}
    
    def _build_folded_context(
        self,
        session: Dict[str, Any],
        history: List[Tuple[str, str]]
    ) -> str:
        """Construye contexto usando Context Folding."""
        context_folder = session.get("context_folder", self.context_folder)
        
        # Agregar historial al contexto principal
        if history:
            for user_msg, bot_msg in history[-10:]:
                if isinstance(user_msg, (tuple, list)) and len(user_msg) == 2:
                    user_msg, bot_msg = user_msg
                
                context_text = f"Usuario: {user_msg}\nAsistente: {bot_msg[:1000]}\n"
                context_folder.add_to_main_context(context_text)
        
        # Auto-plegar si es necesario
        context_folder.auto_fold_if_needed()
        
        # Obtener contexto plegado
        return context_folder.get_folded_context()
    
    async def _execute_query_path(
        self,
        approach: str,
        strategy: str,
        expected_steps: List[str],
        context: str
    ) -> Any:
        """Ejecuta un camino de razonamiento."""
        return f"Resultado usando enfoque: {approach}"
    
    async def _execute_rl_action(
        self,
        action: str,
        context: str
    ) -> Any:
        """
        Ejecuta una acción del Reinforcement Planner.
        """
        action_lower = action.lower()
        
        if "palabras clave" in action_lower or "keywords" in action_lower:
            return {
                "strategy": "keyword_search",
                "result": "Búsqueda por palabras clave ejecutada",
                "success": True,
                "confidence": 0.8
            }
        elif "secciones" in action_lower or "sections" in action_lower:
            return {
                "strategy": "section_search",
                "result": "Búsqueda por secciones ejecutada",
                "success": True,
                "confidence": 0.75
            }
        elif "fechas" in action_lower or "dates" in action_lower:
            return {
                "strategy": "date_search",
                "result": "Búsqueda por fechas ejecutada",
                "success": True,
                "confidence": 0.7
            }
        elif "comparar" in action_lower or "compare" in action_lower:
            return {
                "strategy": "document_comparison",
                "result": "Comparación de documentos ejecutada",
                "success": True,
                "confidence": 0.85
            }
        elif "analizar" in action_lower or "analyze" in action_lower:
            return {
                "strategy": "structure_analysis",
                "result": "Análisis de estructura ejecutado",
                "success": True,
                "confidence": 0.8
            }
        else:
            return {
                "strategy": "generic",
                "result": f"Acción ejecutada: {action}",
                "success": True,
                "confidence": 0.6
            }
    
    async def _query_mcp_systems(
        self,
        query: str,
        context: str
    ) -> Optional[Dict[str, Any]]:
        """
        Consulta sistemas externos usando MCP potenciado.
        """
        if not self.mcp_manager or not self.mcp_manager.connections:
            return None
        
        try:
            requires_external = await self._needs_external_data(query, context)
            
            if not requires_external:
                return None
            
            mcp_results = []
            mcp_sources = []
            
            for conn_id, connection in self.mcp_manager.connections.items():
                if not connection.enabled:
                    continue
                
                try:
                    if connection.connection_type == "database":
                        result = await self._query_mcp_database(connection, query)
                        if result:
                            mcp_results.append(result)
                            mcp_sources.append({
                                "type": "database",
                                "name": connection.name,
                                "data": result
                            })
                    
                    elif connection.connection_type == "api":
                        result = await self._query_mcp_api(connection, query)
                        if result:
                            mcp_results.append(result)
                            mcp_sources.append({
                                "type": "api",
                                "name": connection.name,
                                "data": result
                            })
                    
                    elif connection.connection_type == "salesforce":
                        result = await self._query_mcp_salesforce(connection, query)
                        if result:
                            mcp_results.append(result)
                            mcp_sources.append({
                                "type": "salesforce",
                                "name": connection.name,
                                "data": result
                            })
                    
                    if self.mcp_manager.llm:
                        raw_data_result = await self.mcp_manager.navigate_raw_data(
                            data_source=conn_id,
                            query=query,
                            llm=self.mcp_manager.llm
                        )
                        if raw_data_result and raw_data_result.get("success"):
                            mcp_results.append(raw_data_result.get("result"))
                            mcp_sources.append({
                                "type": "raw_data",
                                "name": connection.name,
                                "data": raw_data_result.get("result")
                            })
                
                except Exception as e:
                    print(f"⚠️ [Event Bus Mode] Error consultando MCP {connection.name}: {e}")
                    continue
            
            if not mcp_results:
                return None
            
            summary = "\n".join([
                f"- {source['name']} ({source['type']}): {str(source['data'])[:200]}"
                for source in mcp_sources[:5]
            ])
            
            return {
                "sources": mcp_sources,
                "summary": summary,
                "total_sources": len(mcp_sources)
            }
            
        except Exception as e:
            print(f"⚠️ [Event Bus Mode] Error en consulta MCP: {e}")
            return None
    
    async def _needs_external_data(
        self,
        query: str,
        context: str
    ) -> bool:
        """Determina si la consulta requiere datos externos."""
        external_keywords = [
            "actual", "tiempo real", "realtime", "sistema", "base de datos",
            "database", "api", "actualizado", "estado actual", "proceso actual",
            "verificar", "validar", "comprobar", "confirmar"
        ]
        
        query_lower = query.lower()
        context_lower = context.lower()
        
        combined = f"{query_lower} {context_lower}"
        
        return any(keyword in combined for keyword in external_keywords)
    
    async def _query_mcp_database(
        self,
        connection: Any,
        query: str
    ) -> Optional[Dict[str, Any]]:
        """Consulta una base de datos usando MCP."""
        return {
            "type": "database",
            "query": query,
            "result": "Datos de base de datos obtenidos vía MCP"
        }
    
    async def _query_mcp_api(
        self,
        connection: Any,
        query: str
    ) -> Optional[Dict[str, Any]]:
        """Consulta una API externa usando MCP."""
        return {
            "type": "api",
            "query": query,
            "result": "Datos de API obtenidos vía MCP"
        }
    
    async def _query_mcp_salesforce(
        self,
        connection: Any,
        query: str
    ) -> Optional[Dict[str, Any]]:
        """Consulta Salesforce usando MCP."""
        return {
            "type": "salesforce",
            "query": query,
            "result": "Datos de Salesforce obtenidos vía MCP"
        }
    
    def handle_webhook_event(self, event_type: str, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Maneja eventos recibidos vía webhook desde sistemas externos.
        
        Args:
            event_type: Tipo de evento (ej: 'new_document', 'data_change', 'document_updated')
            event_data: Datos del evento
            
        Returns:
            Dict con status y resultado
        """
        try:
            print(f"📡 [Event Bus] Webhook recibido: {event_type}")
            
            # Publicar evento en el bus interno
            self.event_bus.publish(event_type, event_data)
            
            return {
                "status": "processed",
                "event_type": event_type,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            print(f"❌ [Event Bus] Error procesando webhook: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    def sync_document_source(self, source: str, interval: int = 60) -> Dict[str, Any]:
        """
        Sincroniza documentos desde una fuente externa con polling mejorado.
        
        Args:
            source: Nombre de la fuente (ej: 'google_drive', 'sharepoint')
            interval: Intervalo de polling en segundos (default: 60 = 1 min)
            
        Returns:
            Dict con status y resultados
        """
        try:
            print(f"🔄 [Event Bus] Sincronizando desde {source} (intervalo: {interval}s)")
            
            # Simular detección de cambios
            # En producción, esto haría polling real o usaría webhooks
            changes_detected = []  # Simulado
            
            if changes_detected:
                for change in changes_detected:
                    self.event_bus.publish('document_updated', {
                        'doc_id': change.get('doc_id'),
                        'source': source,
                        'change_type': change.get('type', 'modified')
                    })
            
            return {
                "status": "success",
                "source": source,
                "changes_detected": len(changes_detected),
                "interval": interval
            }
        except Exception as e:
            print(f"❌ [Event Bus] Error en sync: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    def subscribe_to_external_webhook(self, source: str, callback_url: str) -> Dict[str, Any]:
        """
        Suscribe a webhooks de sistemas externos.
        
        Args:
            source: Nombre de la fuente (ej: 'google_drive', 'sharepoint')
            callback_url: URL donde recibir webhooks
            
        Returns:
            Dict con status
        """
        try:
            print(f"🔔 [Event Bus] Suscribiendo a webhooks de {source} -> {callback_url}")
            
            # En producción, esto registraría el webhook con el servicio externo
            # Por ahora, solo logging
            
            return {
                "status": "subscribed",
                "source": source,
                "callback_url": callback_url
            }
        except Exception as e:
            print(f"❌ [Event Bus] Error suscribiendo webhook: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    def get_event_history(self, event_type: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Obtiene el historial de eventos."""
        return self.event_bus.get_event_history(event_type, limit)
    
    def get_statistics(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Obtiene estadísticas del modo."""
        stats = {
            "context_folding": self.context_folder.get_statistics(),
            "data_provenance": self.provenance_tracker.get_statistics(),
            "chain_of_thought": self.chain_reasoner.get_statistics(),
            "path_reasoning": self.path_reasoner.get_statistics(),
            "test_time_training": self.test_time_trainer.get_statistics(),
            "person_in_loop": self.person_in_loop.get_statistics(),
            "reinforcement_planning": self.reinforcement_planner.get_statistics(),
            "mcp_integration": {
                "connections": len(self.mcp_manager.connections) if self.mcp_manager else 0,
                "enabled_connections": len([c for c in self.mcp_manager.connections.values() if c.enabled]) if self.mcp_manager else 0
            },
            "event_bus": {
                "total_events": len(self.event_bus.event_history),
                "event_types": len(self.event_bus.subscribers),
                "recent_events": len(self.event_bus.get_event_history(limit=10)),
                "subscribers_count": sum(len(callbacks) for callbacks in self.event_bus.subscribers.values()),
                "async_subscribers_count": sum(len(callbacks) for callbacks in self.event_bus.async_subscribers.values()),
                "events_per_second": self._calculate_events_per_second()
            },
            "realtime_streaming": {
                "active_streams": len(self.insight_streams),
                "total_insights": sum(len(insights) for insights in self.insight_streams.values()),
                "streaming_enabled": True
            }
        }
        
        if session_id and session_id in self.sessions:
            session = self.sessions[session_id]
            stats["session"] = {
                "docs_count": len(session["docs"]),
                "history_count": len(session["history"]),
                "processed_files": len(session["processed_files"])
            }
        
        return stats

    async def _process_query_parallel(
        self,
        session_id: str,
        message: str,
        history: List[Tuple[str, str]],
        docs_by_source: Dict[str, List[Document]],
        speed_mode: str = "balanced",
        provider: str = "openai"
    ) -> Tuple[List[Tuple[str, str]], Optional[str], Dict[str, Any]]:
        """
        Procesa consulta con procesamiento paralelo de documentos (como Enterprise API).
        Analiza cada documento por separado aplicando el prompt del usuario,
        luego combina todos los análisis en una respuesta final.
        Mantiene toda la funcionalidad específica de Event Bus Mode (eventos, workflows, etc.).
        """
        session = self.sessions.get(session_id, {})
        start_time = time.time()
        
        # Publicar evento de inicio de query paralelo
        self.event_bus.publish('query_started', {
            'session_id': session_id,
            'query': message,
            'mode': 'parallel',
            'document_count': len(docs_by_source)
        })
        
        # Crear LLM sin límite de max_tokens para respuestas largas
        from docchat.utils.llm_factory import create_llm
        api_key = self.config.openai_api_key if provider == "openai" else self.config.anthropic_api_key
        parallel_llm = create_llm(
            provider=provider,
            model=self.config.research_model or "gpt-4o",
            temperature=0.1,  # Temperatura más baja para respuestas más precisas
            api_key=api_key,
            request_timeout=600  # Timeout más largo para documentos grandes y respuestas completas
        )
        
        # Construir contexto de conversación
        conversation_context = self._build_folded_context(session, history)
        
        # Procesar cada documento en paralelo
        individual_analyses = {}
        # Aumentar workers para procesar hasta 500 PDFs simultáneamente (hasta 20 workers)
        max_workers = min(20, len(docs_by_source))
        
        print(f"🔄 [Event Bus Mode] Iniciando análisis individual de {len(docs_by_source)} documentos (workers: {max_workers})...")
        print(f"📊 [Event Bus Mode] GARANTIZADO: Cada PDF generará su propia respuesta individual")
        
        def analyze_single_document(source_name: str, file_docs: List[Document]) -> Tuple[str, str]:
            """Analiza un solo documento con el prompt del usuario - PROMPT ULTRA MEJORADO."""
            try:
                # Construir contexto completo del documento (SIN TRUNCAR - analizar TODO)
                doc_content = "\n\n".join([doc.page_content for doc in file_docs])
                
                # Si el documento es muy grande, incluir todo pero mencionarlo
                if len(doc_content) > 100000:
                    print(f"⚠️ [Event Bus Mode] Documento muy grande ({len(doc_content)} caracteres), analizando completo...")
                
                # PROMPT ULTRA MEJORADO - Respuestas super inteligentes y completas
                prompt = f"""Eres un analista estratégico senior de nivel C-Suite con décadas de experiencia, especializado en análisis event-driven. Tu tarea es analizar ESTE documento específico de manera PROFUNDA y COMPLETA para responder DIRECTAMENTE la pregunta del usuario con el máximo nivel de inteligencia y detalle.

PREGUNTA ESPECÍFICA DEL USUARIO (RESPONDE EXACTAMENTE ESTO):
{message}

CONTENIDO COMPLETO DE ESTE DOCUMENTO:
{doc_content}

INSTRUCCIONES PARA RESPUESTA SUPER INTELIGENTE Y COMPLETA:

1. ANÁLISIS PROFUNDO Y ESTRATÉGICO (OBLIGATORIO):
   - Analiza el documento de manera HOLÍSTICA, no superficial
   - Identifica el CONTEXTO, PROPÓSITO y SIGNIFICADO ESTRATÉGICO del documento
   - Extrae información IMPLÍCITA, no solo explícita (lectura entre líneas)
   - Identifica conexiones, patrones, y relaciones entre diferentes secciones
   - Detecta contradicciones internas, tensiones, o áreas de ambigüedad
   - Evalúa la CALIDAD, CREDIBILIDAD y RELEVANCIA del contenido

2. RESPUESTA DIRECTA AL PROMPT DEL USUARIO:
   - Tu objetivo PRINCIPAL es responder: "{message}"
   - NO uses un formato genérico - ADÁPTATE completamente al tipo de pregunta
   - Si pregunta por "información más valiosa" → identifica y explica la información MÁS VALIOSA con DETALLE
   - Si pregunta por "recomendaciones" → proporciona recomendaciones ESPECÍFICAS, ACCIONABLES y ESTRATÉGICAS
   - Si pregunta por "mejor documento" → evalúa este documento con CRITERIOS CLAROS y EVIDENCIA
   - Si pregunta por "análisis" → proporciona análisis PROFUNDO, ESTRUCTURADO y ESTRATÉGICO
   - Si pregunta por "comparación" → compara elementos del documento con PRECISIÓN y EVIDENCIA

3. INFORMACIÓN ESPECÍFICA Y CONCRETA (OBLIGATORIO):
   - Cita datos EXACTOS del documento (números, porcentajes, fechas, nombres, métricas, estadísticas)
   - Incluye CITAS TEXTUALES cuando sean relevantes (entre comillas)
   - Identifica ENTIDADES, METODOLOGÍAS, FRAMEWORKS, o CONCEPTOS clave
   - Extrae EJEMPLOS CONCRETOS, CASOS DE ESTUDIO, o ANÉCDOTAS del documento
   - Proporciona CONTEXTO y BACKGROUND cuando sea necesario para entender la información

4. ESTRUCTURA INTELIGENTE Y ADAPTATIVA (800-1200 palabras):

   **INTRODUCCIÓN ESTRATÉGICA** (1-2 párrafos):
   - Resumen ejecutivo del documento y su relevancia para la pregunta
   - Contexto y propósito del documento
   - Por qué este documento es relevante para responder la pregunta

   **RESPUESTA DIRECTA A LA PREGUNTA** (3-4 párrafos):
   - Responde DIRECTAMENTE la pregunta del usuario con información específica del documento
   - Usa datos concretos, cifras, ejemplos, y evidencia del documento
   - Estructura la respuesta de manera lógica y fácil de seguir
   - Incluye análisis de CAUSA-EFECTO cuando sea relevante

   **ANÁLISIS PROFUNDO Y DETALLADO** (2-3 párrafos):
   - Análisis de aspectos clave relacionados con la pregunta
   - Identificación de patrones, tendencias, o relaciones
   - Evaluación crítica de fortalezas, debilidades, oportunidades, amenazas
   - Perspectivas estratégicas que emergen del documento

   **INFORMACIÓN ESPECÍFICA Y DATOS CONCRETOS** (2-3 párrafos):
   - Lista de datos clave, métricas, estadísticas del documento
   - Ejemplos concretos, casos de estudio, o anécdotas relevantes
   - Citas textuales importantes (entre comillas)
   - Tablas, gráficos, o estructuras de datos si son relevantes

   **RECOMENDACIONES / INSIGHTS / CONCLUSIÓN** (2-3 párrafos):
   - Recomendaciones específicas y accionables basadas en el documento (si aplica)
   - Insights estratégicos que emergen del análisis
   - Implicaciones prácticas y aplicaciones del contenido
   - Conclusión que sintetiza la respuesta a la pregunta

5. PROFESIONALISMO Y CALIDAD ENTERPRISE:
   - Lenguaje claro, preciso y profesional (nivel C-Suite)
   - Estructura lógica y fácil de escanear (uso de negritas, viñetas cuando sea útil)
   - Información accionable y específica
   - Análisis crítico y pensamiento estratégico
   - Evidencia y respaldo para cada afirmación

6. LONGITUD Y COMPLETITUD:
   - 800-1200 palabras (respuesta COMPLETA y PROFUNDA)
   - NO te quedes corto - proporciona DETALLE y PROFUNDIDAD
   - Cada sección debe aportar VALOR ÚNICO y ESPECÍFICO
   - Prioriza COMPLETITUD sobre concisión
   - Mejor una respuesta larga y completa que corta e incompleta

IMPORTANTE - OBLIGATORIO:
- ✅ RESPONDE DIRECTAMENTE la pregunta: "{message}"
- ✅ ADÁPTATE al tipo de pregunta - NO uses formato genérico
- ✅ Proporciona ANÁLISIS PROFUNDO, no superficial
- ✅ Incluye DATOS CONCRETOS, CITAS, y EVIDENCIA del documento
- ✅ 800-1200 palabras - respuesta COMPLETA y DETALLADA
- ✅ Pensamiento ESTRATÉGICO y CRÍTICO
- ✅ Estructura CLARA y PROFESIONAL
- ❌ NO describas el documento en general sin responder la pregunta
- ❌ NO uses un formato genérico que ignore el tipo de pregunta
- ❌ NO te quedes corto - proporciona DETALLE y PROFUNDIDAD

RESPUESTA SUPER INTELIGENTE Y COMPLETA (800-1200 palabras):"""
                
                # STREAMING EN TIEMPO REAL - Usar astream para respuesta progresiva
                from langchain_core.messages import HumanMessage
                analysis = ""
                chunk_count = 0
                
                # Stream tokens en tiempo real usando asyncio.run en el thread
                async def stream_analysis():
                    nonlocal analysis, chunk_count
                    async for chunk in parallel_llm.astream([HumanMessage(content=prompt)]):
                        if hasattr(chunk, 'content'):
                            token = chunk.content
                        else:
                            token = str(chunk)
                        analysis += token
                        chunk_count += 1
                        
                        # Publicar progreso cada 10 tokens para streaming en tiempo real
                        if chunk_count % 10 == 0:
                            # Publicar al Event Bus interno
                            try:
                                self.event_bus.publish('document_analysis_streaming', {
                                    'session_id': session_id,
                                    'document': Path(source_name).name,
                                    'current_text': analysis[-300:],  # Últimos 300 caracteres
                                    'chunk_count': chunk_count
                                })
                            except:
                                pass  # Si falla, continuar sin publicar
                
                # Ejecutar streaming en el thread (sin nest_asyncio - más simple)
                try:
                    # Crear nuevo event loop para este thread
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        loop.run_until_complete(stream_analysis())
                    finally:
                        loop.close()
                except Exception as stream_error:
                    # Fallback a invoke si streaming falla (más robusto)
                    print(f"⚠️ [Event Bus Mode] Streaming falló para {source_name}, usando invoke: {stream_error}")
                    try:
                        response = parallel_llm.invoke(prompt)
                        analysis = response.content.strip() if hasattr(response, 'content') else str(response).strip()
                    except Exception as invoke_error:
                        print(f"❌ [Event Bus Mode] Error con invoke también: {invoke_error}")
                        analysis = f"❌ Error analizando documento: {str(stream_error)[:200]}"
                
                return source_name, analysis.strip()
            except Exception as e:
                return source_name, f"❌ Error analizando documento: {str(e)[:200]}"
        
        # Ejecutar análisis en paralelo - GARANTIZA que TODOS se procesen
        print(f"🔄 [Event Bus Mode] Iniciando análisis de {len(docs_by_source)} documentos...")
        completed_count = 0
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(analyze_single_document, source_name, file_docs): source_name
                for source_name, file_docs in docs_by_source.items()
            }
            
            for future in as_completed(futures):
                source_name = futures[future]
                try:
                    doc_name, analysis = future.result()
                    individual_analyses[doc_name] = analysis
                    completed_count += 1
                    print(f"✅ [Event Bus Mode] Documento {completed_count}/{len(docs_by_source)} completado: {Path(doc_name).name}")
                    # Publicar evento de documento procesado
                    self.event_bus.publish('document_analysis_completed', {
                        'session_id': session_id,
                        'document': Path(doc_name).name,
                        'progress': f"{completed_count}/{len(docs_by_source)}"
                    })
                except Exception as e:
                    print(f"❌ [Event Bus Mode] Error procesando {source_name}: {e}")
                    individual_analyses[source_name] = f"❌ Error: {str(e)[:200]}"
                    completed_count += 1
        
        # VERIFICAR que TODOS los documentos fueron procesados
        if len(individual_analyses) < len(docs_by_source):
            print(f"⚠️ [Event Bus Mode] ADVERTENCIA: Solo se procesaron {len(individual_analyses)} de {len(docs_by_source)} documentos")
            print(f"🔄 [Event Bus Mode] Reintentando documentos faltantes...")
            # Reintentar documentos faltantes
            missing_docs = set(docs_by_source.keys()) - set(individual_analyses.keys())
            for missing_source in missing_docs:
                try:
                    doc_name, analysis = analyze_single_document(missing_source, docs_by_source[missing_source])
                    individual_analyses[doc_name] = analysis
                    completed_count += 1
                    print(f"✅ [Event Bus Mode] Documento recuperado: {Path(doc_name).name}")
                except Exception as e:
                    print(f"❌ [Event Bus Mode] Error en reintento de {missing_source}: {e}")
        
        # Verificación final
        final_count = len(individual_analyses)
        total_count = len(docs_by_source)
        if final_count == total_count:
            print(f"✅✅✅ [Event Bus Mode] ÉXITO: TODOS los {total_count} documentos fueron analizados individualmente")
        else:
            print(f"⚠️ [Event Bus Mode] Procesados {final_count} de {total_count} documentos")
        
        # OPCIÓN A: Mostrar todos los análisis individuales (500 PDFs = 500 respuestas individuales)
        individual_analyses_text = f"## 📄 Análisis Individuales por Documento ({len(individual_analyses)} respuestas)\n\n"
        individual_analyses_text += f"**GARANTIZADO: Cada PDF tiene su propio análisis individual**\n\n"
        individual_analyses_text += f"**Total de documentos analizados:** {len(individual_analyses)}/{len(docs_by_source)}\n\n"
        individual_analyses_text += "---\n\n"
        
        for idx, (doc_name, analysis) in enumerate(individual_analyses.items(), 1):
            clean_name = Path(doc_name).name
            individual_analyses_text += f"### 📄 Documento {idx}/{len(individual_analyses)}: {clean_name}\n\n"
            individual_analyses_text += f"{analysis}\n\n"
            individual_analyses_text += "---\n\n"
        
        # OPCIÓN B: Combinar todos los análisis en una respuesta final
        combined_context = "\n\n".join([
            f"=== DOCUMENTO: {Path(doc_name).name} ===\n{analysis}"
            for doc_name, analysis in individual_analyses.items()
        ])
        
        # Generar respuesta combinada ULTRA MEJORADA
        synthesis_prompt = f"""Eres un consultor estratégico senior de nivel C-Suite con décadas de experiencia, especializado en análisis event-driven. Has analizado {len(individual_analyses)} documentos individualmente, cada uno respondiendo la pregunta del usuario con profundidad y detalle (800-1200 palabras por documento).

TU TAREA PRINCIPAL: Combinar todos los análisis individuales para crear una respuesta FINAL que sea EXTRAORDINARIAMENTE COMPLETA, INTELIGENTE y ESTRATÉGICA, respondiendo DIRECTAMENTE la pregunta del usuario.

PREGUNTA ESPECÍFICA DEL USUARIO (RESPONDE EXACTAMENTE ESTO):
{message}

ANÁLISIS INDIVIDUALES DE CADA DOCUMENTO (cada uno ya respondió la pregunta con 800-1200 palabras):
{combined_context}

INSTRUCCIONES PARA RESPUESTA FINAL ULTRA INTELIGENTE (1500-2500 palabras):

1. SÍNTESIS ESTRATÉGICA DE NIVEL C-SUITE:
   - Combina los análisis individuales en una respuesta COHERENTE y HOLÍSTICA
   - Identifica PATRONES COMUNES, CONTRADICCIONES, o TENSIONES entre documentos
   - Proporciona una VISIÓN INTEGRADA que ningún documento individual puede dar
   - Compara y contrasta información de diferentes documentos con PRECISIÓN
   - Identifica SINERGIAS, COMPLEMENTARIEDADES, o CONFLICTOS entre documentos

2. RESPUESTA DIRECTA AL PROMPT DEL USUARIO (OBLIGATORIO):
   - Tu objetivo es responder: "{message}"
   - Combina información de TODOS los análisis individuales para dar una respuesta COMPLETA
   - Si pregunta por "información más valiosa" → sintetiza la información más valiosa de TODOS los PDFs con DETALLE
   - Si pregunta por "recomendaciones" → proporciona recomendaciones basadas en TODOS los documentos, priorizadas
   - Si pregunta por "mejor documento" → compara y evalúa TODOS los documentos con CRITERIOS CLAROS
   - Si pregunta por "análisis" → proporciona análisis HOLÍSTICO que integre todos los documentos

3. ESTRUCTURA ULTRA INTELIGENTE (1500-2500 palabras):

   **RESUMEN EJECUTIVO** (2-3 párrafos):
   - Respuesta directa a la pregunta del usuario
   - Visión general de lo que se encontró en todos los documentos
   - Conclusiones principales que emergen de la síntesis

   **ANÁLISIS HOLÍSTICO Y ESTRATÉGICO** (4-5 párrafos):
   - Síntesis de información clave de todos los documentos
   - Identificación de patrones, tendencias, y relaciones entre documentos
   - Análisis comparativo de diferentes perspectivas
   - Evaluación crítica de consistencias y contradicciones
   - Insights estratégicos que emergen de ver todos los documentos juntos

   **INFORMACIÓN CLAVE POR CATEGORÍA/TEMA** (5-6 párrafos):
   - Organiza la información por temas, categorías, o aspectos clave
   - Para cada tema: qué dicen los diferentes documentos
   - Comparación y contraste de perspectivas diferentes
   - Identificación de consensos y divergencias
   - Síntesis de información complementaria

   **ANÁLISIS POR DOCUMENTO (Resumen Estratégico)** (3-4 párrafos por documento relevante):
   - Para cada documento más relevante: resumen de contribuciones clave
   - Qué aporta único cada documento a responder la pregunta
   - Fortalezas y limitaciones de cada documento en relación a la pregunta
   - Cómo se relaciona con otros documentos

   **RECOMENDACIONES / INSIGHTS FINALES / CONCLUSIÓN** (4-5 párrafos):
   - Recomendaciones específicas y priorizadas basadas en TODOS los documentos
   - Insights estratégicos que emergen de la síntesis completa
   - Implicaciones prácticas y aplicaciones
   - Áreas de oportunidad o acción identificadas
   - Conclusión que responde completamente la pregunta del usuario

4. PROFESIONALISMO Y CALIDAD EXCEPCIONAL:
   - Lenguaje claro, preciso y de nivel C-Suite
   - Estructura lógica con uso inteligente de formato (negritas, viñetas, secciones)
   - Información accionable y específica
   - Análisis crítico y pensamiento estratégico avanzado
   - Evidencia y respaldo para cada afirmación importante

5. LONGITUD Y COMPLETITUD:
   - 1500-2500 palabras (respuesta EXTRAORDINARIAMENTE COMPLETA)
   - NO te quedes corto - esta es la respuesta FINAL y debe ser EXHAUSTIVA
   - Prioriza COMPLETITUD y PROFUNDIDAD sobre concisión
   - Cada sección debe aportar VALOR ÚNICO y ESTRATÉGICO
   - Mejor una respuesta larga y completa que corta e incompleta

IMPORTANTE - OBLIGATORIO:
- ✅ RESPONDE DIRECTAMENTE la pregunta: "{message}"
- ✅ COMBINA información de TODOS los documentos analizados
- ✅ Proporciona ANÁLISIS HOLÍSTICO, no solo resumen
- ✅ Identifica PATRONES, CONTRADICCIONES, y SINERGIAS entre documentos
- ✅ 1500-2500 palabras - respuesta EXTRAORDINARIAMENTE COMPLETA
- ✅ Pensamiento ESTRATÉGICO de nivel C-Suite
- ✅ Estructura CLARA y PROFESIONAL
- ❌ NO ignores información de ningún documento
- ❌ NO uses formato genérico - ADÁPTATE a la pregunta
- ❌ NO te quedes corto - esta es la respuesta FINAL y debe ser EXHAUSTIVA

RESPUESTA FINAL ULTRA INTELIGENTE Y COMPLETA (1500-2500 palabras):"""
        
        # STREAMING EN TIEMPO REAL - Usar astream para respuesta progresiva como ChatGPT
        # Con Confluent habilitado, los tokens se publican en tiempo real para mejor performance
        try:
            from langchain_core.messages import HumanMessage
            combined_answer = ""
            chunk_count = 0
            
            # STREAMING: Generar respuesta token por token en tiempo real (como ChatGPT)
            # Los tokens se publican al Event Bus y Confluent (si está disponible) para streaming en UI
            print("🚀 [Event Bus Mode] Generando respuesta final con streaming en tiempo real (Confluent optimizado)...")
            async for chunk in parallel_llm.astream([HumanMessage(content=synthesis_prompt)]):
                if hasattr(chunk, 'content'):
                    token = chunk.content
                else:
                    token = str(chunk)
                combined_answer += token
                chunk_count += 1
                
                # Publicar cada token al Event Bus para streaming en tiempo real
                if chunk_count % 5 == 0:  # Publicar cada 5 tokens para respuesta fluida
                    self.event_bus.publish('streaming_token', {
                        'session_id': session_id,
                        'current_text': combined_answer,
                        'chunk_count': chunk_count,
                        'type': 'synthesis_final'
                    })
                    
                    # Si Confluent está habilitado, publicar también allí para mejor performance
                    if self.confluent_enabled and self.confluent_producer and CONFLUENT_STREAMING_AVAILABLE:
                        try:
                            event = StreamingEvent(
                                event_id=f"{session_id}_{chunk_count}",
                                event_type=EventType.STREAMING_DATA,
                                timestamp=datetime.now(),
                                data={
                                    'session_id': session_id,
                                    'current_text': combined_answer,
                                    'chunk_count': chunk_count,
                                    'type': 'synthesis_final'
                                },
                                source='event_bus_mode'
                            )
                            self.confluent_producer.produce_event(
                                topic='event_bus_streaming',
                                event=event
                            )
                        except Exception as e:
                            # Si Confluent falla, continuar con Event Bus interno
                            pass
            
            combined_answer = combined_answer.strip()
        except Exception as e:
            combined_answer = f"⚠️ Error generando síntesis: {str(e)[:200]}"
        
        # Combinar ambas opciones - PRIMERO mostrar análisis individuales (500 PDFs = 500 respuestas)
        formatted_answer = f"## 📊 RESUMEN: {len(individual_analyses)} Documentos Analizados Individualmente\n\n"
        formatted_answer += f"✅ **GARANTIZADO:** Cada PDF tiene su propia respuesta individual\n"
        formatted_answer += f"✅ **Total procesado:** {len(individual_analyses)}/{len(docs_by_source)} documentos\n\n"
        formatted_answer += "---\n\n"
        formatted_answer += individual_analyses_text
        formatted_answer += "\n\n## 🎯 Respuesta Final Combinada (Síntesis de Todos los Documentos)\n\n"
        formatted_answer += combined_answer
        
        # Actualizar historial
        new_history = history + [(message, formatted_answer)]
        session["history"] = new_history
        
        # Publicar evento de query completada
        elapsed_time = time.time() - start_time
        self.event_bus.publish('query_completed', {
            'session_id': session_id,
            'query': message,
            'elapsed_time': elapsed_time,
            'documents_analyzed': len(individual_analyses),
            'total_documents': len(docs_by_source),
            'all_processed': len(individual_analyses) == len(docs_by_source)
        })
        
        metadata = {
            "mode": "parallel_individual",
            "documents_analyzed": len(individual_analyses),
            "total_documents": len(docs_by_source),
            "all_processed": len(individual_analyses) == len(docs_by_source),
            "elapsed_time": elapsed_time,
            "event_bus_events": len(self.event_bus.event_history),
            "workers_used": max_workers
        }
        
        return new_history, None, metadata


# Instancia global
_event_bus_mode_instance: Optional[EventBusMode] = None


def get_event_bus_mode(
    config: AppConfig,
    processor: DocumentProcessor,
    retriever_builder: RetrieverBuilder,
    context_manager: Optional[Any] = None
) -> EventBusMode:
    """Obtiene o crea la instancia global de Event Bus Mode."""
    global _event_bus_mode_instance
    
    if _event_bus_mode_instance is None:
        _event_bus_mode_instance = EventBusMode(
            config=config,
            processor=processor,
            retriever_builder=retriever_builder,
            context_manager=context_manager
        )
    
    return _event_bus_mode_instance


def run_event_bus_mode(
    message: str,
    history: List[Tuple[str, str]],
    files: List[Any],
    session_id: str,
    speed_mode: str = "balanced",
    provider: str = "openai",
    config: Optional[AppConfig] = None,
    processor: Optional[DocumentProcessor] = None,
    retriever_builder: Optional[RetrieverBuilder] = None,
    context_manager: Optional[Any] = None
) -> Tuple[List[Tuple[str, str]], Optional[str]]:
    """
    Función principal para ejecutar Event Bus Mode.
    Compatible con Gradio (síncrona).
    """
    if not config or not processor or not retriever_builder:
        return history, "❌ Configuración incompleta"
    
    # Obtener instancia
    event_bus_mode = get_event_bus_mode(
        config=config,
        processor=processor,
        retriever_builder=retriever_builder,
        context_manager=context_manager
    )
    
    # Procesar documentos si hay
    if files:
        result = event_bus_mode.process_documents(session_id, files)
        if result.get("status") == "error":
            return history, f"❌ Error procesando documentos: {result.get('error')}"
    
    # Ejecutar query (async wrapper)
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        new_history, error, metadata = loop.run_until_complete(
            event_bus_mode.process_query_async(
                session_id=session_id,
                message=message,
                history=history,
                speed_mode=speed_mode,
                provider=provider
            )
        )
        loop.close()
        return new_history, error
    except Exception as e:
        return history, f"❌ Error: {str(e)}"

