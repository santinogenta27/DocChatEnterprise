"""
Sistema de Integración Enterprise para Automatización RPA con Agentic AI en Tiempo Real.
Permite que empresas conecten sus sistemas por API y los Agentic AI procesen datos en tiempo real.

Características:
- Procesamiento en tiempo real sin interrupciones
- Observabilidad completa (logging, tracing, metrics)
- Context Engineering y Memory Management para agentes
- Streaming de datos continuos
- Recuperación automática de errores
- Soporte para múltiples conexiones concurrentes
"""

from __future__ import annotations

import json
import time
import secrets
import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable
from datetime import datetime, timedelta
from pathlib import Path
from threading import Thread, Lock
import threading
from collections import deque
import queue

from .config import AppConfig
from .rpa_automation import RPAAutomationEngine

# Configurar logging
logger = logging.getLogger(__name__)


@dataclass
class EnterpriseConnection:
    """Conexión de una empresa al sistema RPA."""
    enterprise_id: str
    name: str
    api_key: str
    webhook_url: Optional[str] = None
    categories: List[str] = field(default_factory=list)
    status: str = "active"  # active, paused, suspended
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    last_activity: Optional[str] = None
    total_requests: int = 0
    successful_automations: int = 0
    failed_automations: int = 0


@dataclass
class RealtimeDataEvent:
    """Evento de datos en tiempo real desde una empresa."""
    event_id: str
    enterprise_id: str
    category: str
    task_type: str
    data: Dict[str, Any]
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    processed: bool = False
    result: Optional[Dict[str, Any]] = None
    processing_started: Optional[str] = None
    processing_completed: Optional[str] = None
    retry_count: int = 0
    error: Optional[str] = None
    trace_id: Optional[str] = None  # Para observabilidad


@dataclass
class AgentContext:
    """Contexto y memoria para un agente procesando datos enterprise."""
    agent_id: str
    enterprise_id: str
    session_id: str
    short_term_memory: deque = field(default_factory=lambda: deque(maxlen=50))  # Últimas 50 interacciones
    long_term_memory: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    last_activity: str = field(default_factory=lambda: datetime.now().isoformat())
    total_actions: int = 0
    successful_actions: int = 0


@dataclass
class ProcessingMetrics:
    """Métricas de procesamiento en tiempo real."""
    total_events_received: int = 0
    total_events_processed: int = 0
    total_events_failed: int = 0
    average_processing_time: float = 0.0
    events_per_second: float = 0.0
    active_connections: int = 0
    queue_size: int = 0
    last_updated: str = field(default_factory=lambda: datetime.now().isoformat())


class RPAEnterpriseIntegration:
    """
    Sistema de integración Enterprise para RPA con Agentic AI en Tiempo Real.
    
    Permite que empresas:
    - Se registren y obtengan API keys
    - Envíen datos en tiempo real vía webhooks o streaming
    - Los Agentic AI procesen automáticamente los datos recibidos SIN FRENAR
    - Reciban resultados y notificaciones en tiempo real
    - Tengan observabilidad completa de las operaciones
    
    Características avanzadas:
    - Procesamiento continuo sin interrupciones
    - Context Engineering para agentes inteligentes
    - Memory Management (short-term y long-term)
    - Observabilidad (logging, tracing, metrics)
    - Recuperación automática de errores
    - Soporte para streaming de datos
    """
    
    def __init__(self, config: AppConfig, rpa_engine: RPAAutomationEngine):
        self.config = config
        self.rpa_engine = rpa_engine
        
        # Directorio para almacenar conexiones
        self.data_dir = Path(config.memory_dir) / "rpa_enterprise"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Archivos de almacenamiento
        self.connections_file = self.data_dir / "enterprise_connections.json"
        self.events_file = self.data_dir / "realtime_events.json"
        self.agents_file = self.data_dir / "agent_contexts.json"
        self.metrics_file = self.data_dir / "processing_metrics.json"
        
        # Almacenamiento en memoria
        self.connections: Dict[str, EnterpriseConnection] = {}
        self.realtime_events: List[RealtimeDataEvent] = []
        self.agent_contexts: Dict[str, AgentContext] = {}  # Por enterprise_id
        self.metrics = ProcessingMetrics()
        
        # Cola para procesamiento en tiempo real (prioridad alta)
        self.event_queue: queue.PriorityQueue = queue.PriorityQueue()
        
        # Threads para procesar eventos en tiempo real (múltiples workers)
        self.processing_threads: List[Thread] = []
        self.processing_active = False
        self.num_workers = 3  # Múltiples workers para procesamiento paralelo
        
        # Locks para thread-safety
        self.connections_lock = Lock()
        self.events_lock = Lock()
        self.metrics_lock = Lock()
        
        # Streaming support
        self.streaming_connections: Dict[str, Callable] = {}  # enterprise_id -> callback
        
        # Cargar datos existentes
        self._load_data()
        
        # Iniciar procesamiento en tiempo real
        self.start_realtime_processing()
        
        logger.info("RPA Enterprise Integration inicializado con procesamiento en tiempo real")
    
    def _load_data(self):
        """Carga conexiones, eventos, contextos de agentes y métricas guardados."""
        try:
            if self.connections_file.exists():
                with open(self.connections_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for conn_data in data:
                        conn = EnterpriseConnection(**conn_data)
                        self.connections[conn.enterprise_id] = conn
            
            if self.events_file.exists():
                with open(self.events_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for event_data in data:
                        # Asegurar campos opcionales
                        event_data.setdefault('processing_started', None)
                        event_data.setdefault('processing_completed', None)
                        event_data.setdefault('retry_count', 0)
                        event_data.setdefault('error', None)
                        event_data.setdefault('trace_id', None)
                        event = RealtimeDataEvent(**event_data)
                        self.realtime_events.append(event)
            
            if self.agents_file.exists():
                with open(self.agents_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for agent_id, agent_data in data.items():
                        # Convertir short_term_memory de lista a deque
                        if 'short_term_memory' in agent_data:
                            agent_data['short_term_memory'] = deque(
                                agent_data['short_term_memory'],
                                maxlen=50
                            )
                        agent = AgentContext(**agent_data)
                        self.agent_contexts[agent_id] = agent
            
            if self.metrics_file.exists():
                with open(self.metrics_file, 'r', encoding='utf-8') as f:
                    metrics_data = json.load(f)
                    self.metrics = ProcessingMetrics(**metrics_data)
            
            logger.info(f"Cargados {len(self.connections)} conexiones, {len(self.realtime_events)} eventos")
        except Exception as e:
            logger.error(f"Error cargando datos enterprise: {e}", exc_info=True)
    
    def _save_data(self):
        """Guarda conexiones, eventos, contextos de agentes y métricas."""
        try:
            with self.connections_lock:
                # Guardar conexiones
                connections_data = [self._connection_to_dict(conn) for conn in self.connections.values()]
                with open(self.connections_file, 'w', encoding='utf-8') as f:
                    json.dump(connections_data, f, indent=2, ensure_ascii=False)
            
            with self.events_lock:
                # Guardar últimos 1000 eventos
                events_data = [self._event_to_dict(e) for e in self.realtime_events[-1000:]]
                with open(self.events_file, 'w', encoding='utf-8') as f:
                    json.dump(events_data, f, indent=2, ensure_ascii=False)
            
            # Guardar contextos de agentes
            agents_data = {}
            for agent_id, agent in self.agent_contexts.items():
                agent_dict = {
                    "agent_id": agent.agent_id,
                    "enterprise_id": agent.enterprise_id,
                    "session_id": agent.session_id,
                    "short_term_memory": list(agent.short_term_memory),
                    "long_term_memory": agent.long_term_memory,
                    "created_at": agent.created_at,
                    "last_activity": agent.last_activity,
                    "total_actions": agent.total_actions,
                    "successful_actions": agent.successful_actions
                }
                agents_data[agent_id] = agent_dict
            
            with open(self.agents_file, 'w', encoding='utf-8') as f:
                json.dump(agents_data, f, indent=2, ensure_ascii=False)
            
            # Guardar métricas
            with self.metrics_lock:
                metrics_dict = {
                    "total_events_received": self.metrics.total_events_received,
                    "total_events_processed": self.metrics.total_events_processed,
                    "total_events_failed": self.metrics.total_events_failed,
                    "average_processing_time": self.metrics.average_processing_time,
                    "events_per_second": self.metrics.events_per_second,
                    "active_connections": self.metrics.active_connections,
                    "queue_size": self.metrics.queue_size,
                    "last_updated": self.metrics.last_updated
                }
                with open(self.metrics_file, 'w', encoding='utf-8') as f:
                    json.dump(metrics_dict, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error guardando datos enterprise: {e}", exc_info=True)
    
    def _connection_to_dict(self, conn: EnterpriseConnection) -> Dict[str, Any]:
        """Convierte conexión a diccionario."""
        return {
            "enterprise_id": conn.enterprise_id,
            "name": conn.name,
            "api_key": conn.api_key,
            "webhook_url": conn.webhook_url,
            "categories": conn.categories,
            "status": conn.status,
            "created_at": conn.created_at,
            "last_activity": conn.last_activity,
            "total_requests": conn.total_requests,
            "successful_automations": conn.successful_automations,
            "failed_automations": conn.failed_automations
        }
    
    def _event_to_dict(self, event: RealtimeDataEvent) -> Dict[str, Any]:
        """Convierte evento a diccionario."""
        return {
            "event_id": event.event_id,
            "enterprise_id": event.enterprise_id,
            "category": event.category,
            "task_type": event.task_type,
            "data": event.data,
            "timestamp": event.timestamp,
            "processed": event.processed,
            "result": event.result,
            "processing_started": event.processing_started,
            "processing_completed": event.processing_completed,
            "retry_count": event.retry_count,
            "error": event.error,
            "trace_id": event.trace_id
        }
    
    def register_enterprise_connection(
        self,
        name: str,
        webhook_url: Optional[str] = None,
        categories: Optional[List[str]] = None
    ) -> EnterpriseConnection:
        """
        Registra una nueva conexión enterprise.
        
        Args:
            name: Nombre de la empresa/app
            webhook_url: URL donde se enviarán notificaciones (opcional)
            categories: Categorías de automatización que usará (opcional)
        
        Returns:
            EnterpriseConnection con API key generada
        """
        enterprise_id = f"ENT-{int(time.time())}-{len(self.connections)}"
        api_key = f"RPA-{secrets.token_urlsafe(32)}"
        
        connection = EnterpriseConnection(
            enterprise_id=enterprise_id,
            name=name,
            api_key=api_key,
            webhook_url=webhook_url,
            categories=categories or [],
            status="active"
        )
        
        self.connections[enterprise_id] = connection
        self._save_data()
        
        print(f"[RPA] Conexion Enterprise registrada: {name} (ID: {enterprise_id})")
        
        return connection
    
    def get_connection_by_api_key(self, api_key: str) -> Optional[EnterpriseConnection]:
        """Obtiene conexión por API key."""
        for conn in self.connections.values():
            if conn.api_key == api_key:
                return conn
        return None
    
    def receive_realtime_data(
        self,
        enterprise_id: str,
        category: str,
        task_type: str,
        data: Dict[str, Any],
        priority: int = 5  # Prioridad: 1=alta, 10=baja
    ) -> RealtimeDataEvent:
        """
        Recibe datos en tiempo real de una empresa y los agrega a la cola de procesamiento.
        Los Agentic AI procesarán automáticamente SIN FRENAR.
        
        Args:
            enterprise_id: ID de la empresa
            category: Categoría de automatización
            task_type: Tipo de tarea
            data: Datos para procesar
            priority: Prioridad del evento (1=alta, 10=baja)
        
        Returns:
            RealtimeDataEvent creado
        """
        # Verificar que la conexión existe y está activa
        with self.connections_lock:
            connection = self.connections.get(enterprise_id)
            if not connection:
                raise ValueError(f"Conexión enterprise no encontrada: {enterprise_id}")
            
            if connection.status != "active":
                raise ValueError(f"Conexión enterprise no está activa: {enterprise_id}")
        
        # Generar trace_id para observabilidad
        trace_id = f"TRACE-{uuid.uuid4().hex[:16]}"
        
        # Crear evento
        event = RealtimeDataEvent(
            event_id=f"EVT-{int(time.time() * 1000)}-{uuid.uuid4().hex[:8]}",
            enterprise_id=enterprise_id,
            category=category,
            task_type=task_type,
            data=data,
            trace_id=trace_id
        )
        
        # Agregar a cola de procesamiento con prioridad (menor número = mayor prioridad)
        self.event_queue.put((priority, time.time(), event))
        
        # Agregar a historial
        with self.events_lock:
            self.realtime_events.append(event)
            # Mantener solo últimos 10000 eventos en memoria
            if len(self.realtime_events) > 10000:
                self.realtime_events = self.realtime_events[-10000:]
        
        # Actualizar estadísticas de conexión
        with self.connections_lock:
            connection.total_requests += 1
            connection.last_activity = datetime.now().isoformat()
        
        # Actualizar métricas
        with self.metrics_lock:
            self.metrics.total_events_received += 1
            self.metrics.queue_size = self.event_queue.qsize()
            self.metrics.last_updated = datetime.now().isoformat()
        
        # Logging para observabilidad
        logger.info(
            f"[RPA] Datos recibidos de {connection.name}: {category}/{task_type} | "
            f"TraceID: {trace_id} | EventID: {event.event_id}"
        )
        
        # Guardar datos (async, no bloquea)
        try:
            self._save_data()
        except Exception as e:
            logger.warning(f"Error guardando datos (no crítico): {e}")
        
        return event
    
    def start_realtime_processing(self):
        """Inicia el procesamiento en tiempo real de eventos con múltiples workers."""
        if self.processing_active:
            return
        
        self.processing_active = True
        
        # Iniciar múltiples workers para procesamiento paralelo
        for i in range(self.num_workers):
            thread = Thread(
                target=self._process_events_loop,
                daemon=True,
                name=f"RPA-Worker-{i+1}"
            )
            thread.start()
            self.processing_threads.append(thread)
        
        # Thread para actualizar métricas periódicamente
        metrics_thread = Thread(
            target=self._update_metrics_loop,
            daemon=True,
            name="RPA-Metrics"
        )
        metrics_thread.start()
        self.processing_threads.append(metrics_thread)
        
        logger.info(f"[RPA] Procesamiento en tiempo real iniciado con {self.num_workers} workers")
    
    def stop_realtime_processing(self):
        """Detiene el procesamiento en tiempo real."""
        self.processing_active = False
        for thread in self.processing_threads:
            thread.join(timeout=5)
        self.processing_threads.clear()
        logger.info("[RPA] Procesamiento en tiempo real detenido")
    
    def _process_events_loop(self):
        """Loop principal para procesar eventos en tiempo real (worker thread)."""
        worker_name = threading.current_thread().name
        logger.info(f"[RPA] Worker {worker_name} iniciado")
        
        while self.processing_active:
            try:
                # Obtener evento de la cola (timeout de 1 segundo)
                try:
                    priority, timestamp, event = self.event_queue.get(timeout=1)
                except queue.Empty:
                    continue
                
                # Procesar evento
                self._process_event(event)
                
                # Marcar tarea como completada
                self.event_queue.task_done()
                
            except Exception as e:
                logger.error(f"Error en worker {worker_name}: {e}", exc_info=True)
        
        logger.info(f"[RPA] Worker {worker_name} detenido")
    
    def _update_metrics_loop(self):
        """Loop para actualizar métricas periódicamente."""
        while self.processing_active:
            try:
                time.sleep(5)  # Actualizar cada 5 segundos
                self._calculate_metrics()
            except Exception as e:
                logger.error(f"Error actualizando métricas: {e}", exc_info=True)
    
    def _calculate_metrics(self):
        """Calcula métricas de procesamiento."""
        with self.metrics_lock:
            # Calcular eventos por segundo (últimos 60 segundos)
            now = datetime.now()
            recent_events = [
                e for e in self.realtime_events
                if e.processed and e.processing_completed
            ]
            recent_events = [
                e for e in recent_events
                if (now - datetime.fromisoformat(e.processing_completed)).total_seconds() < 60
            ]
            
            if recent_events:
                total_time = sum(
                    (datetime.fromisoformat(e.processing_completed) - 
                     datetime.fromisoformat(e.processing_started)).total_seconds()
                    for e in recent_events
                    if e.processing_started and e.processing_completed
                )
                self.metrics.average_processing_time = (
                    total_time / len(recent_events) if recent_events else 0.0
                )
                self.metrics.events_per_second = len(recent_events) / 60.0
            
            self.metrics.active_connections = len([
                c for c in self.connections.values()
                if c.status == "active"
            ])
            self.metrics.queue_size = self.event_queue.qsize()
            self.metrics.last_updated = datetime.now().isoformat()
    
    def _process_event(self, event: RealtimeDataEvent):
        """
        Procesa un evento automáticamente con Agentic AI en tiempo real.
        NO FRENA - procesamiento continuo.
        
        Args:
            event: Evento a procesar
        """
        processing_start = datetime.now()
        event.processing_started = processing_start.isoformat()
        
        # Obtener o crear contexto de agente para esta empresa
        agent_context = self._get_or_create_agent_context(event.enterprise_id)
        
        logger.info(
            f"[RPA] PROCESANDO EVENTO EN TIEMPO REAL | "
            f"EventID: {event.event_id} | TraceID: {event.trace_id} | "
            f"Enterprise: {self.connections.get(event.enterprise_id, {}).name} | "
            f"Categoría: {event.category} | Tarea: {event.task_type}"
        )
        
        try:
            # Agregar a memoria de corto plazo del agente
            agent_context.short_term_memory.append({
                "timestamp": event.timestamp,
                "category": event.category,
                "task_type": event.task_type,
                "action": "processing_started"
            })
            
            # Ejecutar automatización con RPA Engine
            result = self.rpa_engine.execute_automation(
                category=event.category,
                task_type=event.task_type,
                parameters=event.data,
                documents=None
            )
            
            processing_end = datetime.now()
            processing_time = (processing_end - processing_start).total_seconds()
            
            # Marcar como procesado
            event.processed = True
            event.processing_completed = processing_end.isoformat()
            event.result = {
                "success": result.success,
                "automation_id": result.automation_id,
                "data": result.data,
                "message": result.message,
                "execution_time": result.execution_time,
                "processing_time": processing_time
            }
            
            # Actualizar contexto del agente
            agent_context.total_actions += 1
            agent_context.last_activity = processing_end.isoformat()
            if result.success:
                agent_context.successful_actions += 1
                agent_context.short_term_memory.append({
                    "timestamp": processing_end.isoformat(),
                    "category": event.category,
                    "task_type": event.task_type,
                    "action": "completed_successfully",
                    "result": result.data
                })
            else:
                agent_context.short_term_memory.append({
                    "timestamp": processing_end.isoformat(),
                    "category": event.category,
                    "task_type": event.task_type,
                    "action": "completed_with_error",
                    "error": result.message
                })
            
            # Actualizar estadísticas de conexión
            with self.connections_lock:
                connection = self.connections.get(event.enterprise_id)
                if connection:
                    if result.success:
                        connection.successful_automations += 1
                    else:
                        connection.failed_automations += 1
            
            # Actualizar métricas
            with self.metrics_lock:
                if result.success:
                    self.metrics.total_events_processed += 1
                else:
                    self.metrics.total_events_failed += 1
            
            # Enviar notificación a webhook si está configurado (async, no bloquea)
            if connection and connection.webhook_url:
                Thread(
                    target=self._send_webhook_notification,
                    args=(connection, event, result),
                    daemon=True
                ).start()
            
            # Streaming callback si está configurado
            if event.enterprise_id in self.streaming_connections:
                try:
                    callback = self.streaming_connections[event.enterprise_id]
                    callback(event, result)
                except Exception as e:
                    logger.warning(f"Error en streaming callback: {e}")
            
            logger.info(
                f"[RPA] Evento procesado exitosamente | "
                f"EventID: {event.event_id} | "
                f"Tiempo: {processing_time:.2f}s | "
                f"Success: {result.success}"
            )
        
        except Exception as e:
            error_msg = str(e)
            processing_end = datetime.now()
            processing_time = (processing_end - processing_start).total_seconds()
            
            logger.error(
                f"[RPA] Error procesando evento | "
                f"EventID: {event.event_id} | TraceID: {event.trace_id} | "
                f"Error: {error_msg}",
                exc_info=True
            )
            
            event.processed = True
            event.processing_completed = processing_end.isoformat()
            event.error = error_msg
            event.result = {
                "success": False,
                "error": error_msg,
                "processing_time": processing_time
            }
            
            # Actualizar contexto del agente
            agent_context.total_actions += 1
            agent_context.last_activity = processing_end.isoformat()
            agent_context.short_term_memory.append({
                "timestamp": processing_end.isoformat(),
                "category": event.category,
                "task_type": event.task_type,
                "action": "failed",
                "error": error_msg
            })
            
            # Actualizar estadísticas
            with self.connections_lock:
                connection = self.connections.get(event.enterprise_id)
                if connection:
                    connection.failed_automations += 1
            
            with self.metrics_lock:
                self.metrics.total_events_failed += 1
            
            # Reintentar si es posible (máximo 3 intentos)
            if event.retry_count < 3:
                event.retry_count += 1
                logger.info(f"[RPA] Reintentando evento {event.event_id} (intento {event.retry_count})")
                # Re-agregar a la cola con menor prioridad
                self.event_queue.put((10, time.time(), event))
        
        # Guardar datos periódicamente (no en cada evento para mejor performance)
        if len(self.realtime_events) % 10 == 0:
            try:
                self._save_data()
            except Exception as e:
                logger.warning(f"Error guardando datos (no crítico): {e}")
    
    def _get_or_create_agent_context(self, enterprise_id: str) -> AgentContext:
        """Obtiene o crea un contexto de agente para una empresa."""
        if enterprise_id not in self.agent_contexts:
            agent_context = AgentContext(
                agent_id=f"AGENT-{enterprise_id}",
                enterprise_id=enterprise_id,
                session_id=f"SESSION-{uuid.uuid4().hex[:16]}"
            )
            self.agent_contexts[enterprise_id] = agent_context
            logger.info(f"[RPA] Contexto de agente creado para {enterprise_id}")
        return self.agent_contexts[enterprise_id]
    
    def _send_webhook_notification(
        self,
        connection: EnterpriseConnection,
        event: RealtimeDataEvent,
        result: Any
    ):
        """Envía notificación a webhook de la empresa."""
        try:
            import requests
            
            payload = {
                "event_id": event.event_id,
                "category": event.category,
                "task_type": event.task_type,
                "success": result.success,
                "result": result.data,
                "message": result.message,
                "execution_time": result.execution_time,
                "timestamp": datetime.now().isoformat()
            }
            
            response = requests.post(
                connection.webhook_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if response.status_code == 200:
                print(f"[RPA] Notificacion enviada a webhook de {connection.name}")
            else:
                print(f"[RPA] Error enviando webhook: {response.status_code}")
        
        except Exception as e:
            print(f"[RPA] Error enviando webhook: {e}")
    
    def get_connection_stats(self, enterprise_id: str) -> Optional[Dict[str, Any]]:
        """Obtiene estadísticas de una conexión."""
        connection = self.connections.get(enterprise_id)
        if not connection:
            return None
        
        return {
            "enterprise_id": connection.enterprise_id,
            "name": connection.name,
            "status": connection.status,
            "total_requests": connection.total_requests,
            "successful_automations": connection.successful_automations,
            "failed_automations": connection.failed_automations,
            "success_rate": (
                (connection.successful_automations / connection.total_requests * 100)
                if connection.total_requests > 0 else 0
            ),
            "last_activity": connection.last_activity,
            "created_at": connection.created_at
        }
    
    def get_all_connections(self) -> List[Dict[str, Any]]:
        """Obtiene todas las conexiones."""
        return [self._connection_to_dict(conn) for conn in self.connections.values()]
    
    def get_recent_events(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Obtiene eventos recientes."""
        with self.events_lock:
            return [self._event_to_dict(e) for e in self.realtime_events[-limit:]]
    
    def get_processing_metrics(self) -> Dict[str, Any]:
        """Obtiene métricas de procesamiento en tiempo real."""
        with self.metrics_lock:
            return {
                "total_events_received": self.metrics.total_events_received,
                "total_events_processed": self.metrics.total_events_processed,
                "total_events_failed": self.metrics.total_events_failed,
                "average_processing_time": self.metrics.average_processing_time,
                "events_per_second": self.metrics.events_per_second,
                "active_connections": self.metrics.active_connections,
                "queue_size": self.metrics.queue_size,
                "success_rate": (
                    (self.metrics.total_events_processed / self.metrics.total_events_received * 100)
                    if self.metrics.total_events_received > 0 else 0.0
                ),
                "last_updated": self.metrics.last_updated
            }
    
    def get_agent_context(self, enterprise_id: str) -> Optional[Dict[str, Any]]:
        """Obtiene el contexto de un agente para una empresa."""
        agent = self.agent_contexts.get(enterprise_id)
        if not agent:
            return None
        
        return {
            "agent_id": agent.agent_id,
            "enterprise_id": agent.enterprise_id,
            "session_id": agent.session_id,
            "short_term_memory_size": len(agent.short_term_memory),
            "long_term_memory_keys": list(agent.long_term_memory.keys()),
            "total_actions": agent.total_actions,
            "successful_actions": agent.successful_actions,
            "success_rate": (
                (agent.successful_actions / agent.total_actions * 100)
                if agent.total_actions > 0 else 0.0
            ),
            "created_at": agent.created_at,
            "last_activity": agent.last_activity
        }
    
    def register_streaming_callback(
        self,
        enterprise_id: str,
        callback: Callable[[RealtimeDataEvent, Any], None]
    ):
        """
        Registra un callback para recibir actualizaciones en tiempo real vía streaming.
        
        Args:
            enterprise_id: ID de la empresa
            callback: Función que recibirá (event, result) cuando se procese un evento
        """
        self.streaming_connections[enterprise_id] = callback
        logger.info(f"[RPA] Callback de streaming registrado para {enterprise_id}")
    
    def unregister_streaming_callback(self, enterprise_id: str):
        """Elimina el callback de streaming para una empresa."""
        if enterprise_id in self.streaming_connections:
            del self.streaming_connections[enterprise_id]
            logger.info(f"[RPA] Callback de streaming eliminado para {enterprise_id}")


        
        # Iniciar múltiples workers para procesamiento paralelo
        for i in range(self.num_workers):
            thread = Thread(
                target=self._process_events_loop,
                daemon=True,
                name=f"RPA-Worker-{i+1}"
            )
            thread.start()
            self.processing_threads.append(thread)
        
        # Thread para actualizar métricas periódicamente
        metrics_thread = Thread(
            target=self._update_metrics_loop,
            daemon=True,
            name="RPA-Metrics"
        )
        metrics_thread.start()
        self.processing_threads.append(metrics_thread)
        
        logger.info(f"[RPA] Procesamiento en tiempo real iniciado con {self.num_workers} workers")
    
    def stop_realtime_processing(self):
        """Detiene el procesamiento en tiempo real."""
        self.processing_active = False
        for thread in self.processing_threads:
            thread.join(timeout=5)
        self.processing_threads.clear()
        logger.info("[RPA] Procesamiento en tiempo real detenido")
    
    def _process_events_loop(self):
        """Loop principal para procesar eventos en tiempo real (worker thread)."""
        worker_name = threading.current_thread().name
        logger.info(f"[RPA] Worker {worker_name} iniciado")
        
        while self.processing_active:
            try:
                # Obtener evento de la cola (timeout de 1 segundo)
                try:
                    priority, timestamp, event = self.event_queue.get(timeout=1)
                except queue.Empty:
                    continue
                
                # Procesar evento
                self._process_event(event)
                
                # Marcar tarea como completada
                self.event_queue.task_done()
                
            except Exception as e:
                logger.error(f"Error en worker {worker_name}: {e}", exc_info=True)
        
        logger.info(f"[RPA] Worker {worker_name} detenido")
    
    def _update_metrics_loop(self):
        """Loop para actualizar métricas periódicamente."""
        while self.processing_active:
            try:
                time.sleep(5)  # Actualizar cada 5 segundos
                self._calculate_metrics()
            except Exception as e:
                logger.error(f"Error actualizando métricas: {e}", exc_info=True)
    
    def _calculate_metrics(self):
        """Calcula métricas de procesamiento."""
        with self.metrics_lock:
            # Calcular eventos por segundo (últimos 60 segundos)
            now = datetime.now()
            recent_events = [
                e for e in self.realtime_events
                if e.processed and e.processing_completed
            ]
            recent_events = [
                e for e in recent_events
                if (now - datetime.fromisoformat(e.processing_completed)).total_seconds() < 60
            ]
            
            if recent_events:
                total_time = sum(
                    (datetime.fromisoformat(e.processing_completed) - 
                     datetime.fromisoformat(e.processing_started)).total_seconds()
                    for e in recent_events
                    if e.processing_started and e.processing_completed
                )
                self.metrics.average_processing_time = (
                    total_time / len(recent_events) if recent_events else 0.0
                )
                self.metrics.events_per_second = len(recent_events) / 60.0
            
            self.metrics.active_connections = len([
                c for c in self.connections.values()
                if c.status == "active"
            ])
            self.metrics.queue_size = self.event_queue.qsize()
            self.metrics.last_updated = datetime.now().isoformat()
    
    def _process_event(self, event: RealtimeDataEvent):
        """
        Procesa un evento automáticamente con Agentic AI en tiempo real.
        NO FRENA - procesamiento continuo.
        
        Args:
            event: Evento a procesar
        """
        processing_start = datetime.now()
        event.processing_started = processing_start.isoformat()
        
        # Obtener o crear contexto de agente para esta empresa
        agent_context = self._get_or_create_agent_context(event.enterprise_id)
        
        logger.info(
            f"[RPA] PROCESANDO EVENTO EN TIEMPO REAL | "
            f"EventID: {event.event_id} | TraceID: {event.trace_id} | "
            f"Enterprise: {self.connections.get(event.enterprise_id, {}).name} | "
            f"Categoría: {event.category} | Tarea: {event.task_type}"
        )
        
        try:
            # Agregar a memoria de corto plazo del agente
            agent_context.short_term_memory.append({
                "timestamp": event.timestamp,
                "category": event.category,
                "task_type": event.task_type,
                "action": "processing_started"
            })
            
            # Ejecutar automatización con RPA Engine
            result = self.rpa_engine.execute_automation(
                category=event.category,
                task_type=event.task_type,
                parameters=event.data,
                documents=None
            )
            
            processing_end = datetime.now()
            processing_time = (processing_end - processing_start).total_seconds()
            
            # Marcar como procesado
            event.processed = True
            event.processing_completed = processing_end.isoformat()
            event.result = {
                "success": result.success,
                "automation_id": result.automation_id,
                "data": result.data,
                "message": result.message,
                "execution_time": result.execution_time,
                "processing_time": processing_time
            }
            
            # Actualizar contexto del agente
            agent_context.total_actions += 1
            agent_context.last_activity = processing_end.isoformat()
            if result.success:
                agent_context.successful_actions += 1
                agent_context.short_term_memory.append({
                    "timestamp": processing_end.isoformat(),
                    "category": event.category,
                    "task_type": event.task_type,
                    "action": "completed_successfully",
                    "result": result.data
                })
            else:
                agent_context.short_term_memory.append({
                    "timestamp": processing_end.isoformat(),
                    "category": event.category,
                    "task_type": event.task_type,
                    "action": "completed_with_error",
                    "error": result.message
                })
            
            # Actualizar estadísticas de conexión
            with self.connections_lock:
                connection = self.connections.get(event.enterprise_id)
                if connection:
                    if result.success:
                        connection.successful_automations += 1
                    else:
                        connection.failed_automations += 1
            
            # Actualizar métricas
            with self.metrics_lock:
                if result.success:
                    self.metrics.total_events_processed += 1
                else:
                    self.metrics.total_events_failed += 1
            
            # Enviar notificación a webhook si está configurado (async, no bloquea)
            if connection and connection.webhook_url:
                Thread(
                    target=self._send_webhook_notification,
                    args=(connection, event, result),
                    daemon=True
                ).start()
            
            # Streaming callback si está configurado
            if event.enterprise_id in self.streaming_connections:
                try:
                    callback = self.streaming_connections[event.enterprise_id]
                    callback(event, result)
                except Exception as e:
                    logger.warning(f"Error en streaming callback: {e}")
            
            logger.info(
                f"[RPA] Evento procesado exitosamente | "
                f"EventID: {event.event_id} | "
                f"Tiempo: {processing_time:.2f}s | "
                f"Success: {result.success}"
            )
        
        except Exception as e:
            error_msg = str(e)
            processing_end = datetime.now()
            processing_time = (processing_end - processing_start).total_seconds()
            
            logger.error(
                f"[RPA] Error procesando evento | "
                f"EventID: {event.event_id} | TraceID: {event.trace_id} | "
                f"Error: {error_msg}",
                exc_info=True
            )
            
            event.processed = True
            event.processing_completed = processing_end.isoformat()
            event.error = error_msg
            event.result = {
                "success": False,
                "error": error_msg,
                "processing_time": processing_time
            }
            
            # Actualizar contexto del agente
            agent_context.total_actions += 1
            agent_context.last_activity = processing_end.isoformat()
            agent_context.short_term_memory.append({
                "timestamp": processing_end.isoformat(),
                "category": event.category,
                "task_type": event.task_type,
                "action": "failed",
                "error": error_msg
            })
            
            # Actualizar estadísticas
            with self.connections_lock:
                connection = self.connections.get(event.enterprise_id)
                if connection:
                    connection.failed_automations += 1
            
            with self.metrics_lock:
                self.metrics.total_events_failed += 1
            
            # Reintentar si es posible (máximo 3 intentos)
            if event.retry_count < 3:
                event.retry_count += 1
                logger.info(f"[RPA] Reintentando evento {event.event_id} (intento {event.retry_count})")
                # Re-agregar a la cola con menor prioridad
                self.event_queue.put((10, time.time(), event))
        
        # Guardar datos periódicamente (no en cada evento para mejor performance)
        if len(self.realtime_events) % 10 == 0:
            try:
                self._save_data()
            except Exception as e:
                logger.warning(f"Error guardando datos (no crítico): {e}")
    
    def _get_or_create_agent_context(self, enterprise_id: str) -> AgentContext:
        """Obtiene o crea un contexto de agente para una empresa."""
        if enterprise_id not in self.agent_contexts:
            agent_context = AgentContext(
                agent_id=f"AGENT-{enterprise_id}",
                enterprise_id=enterprise_id,
                session_id=f"SESSION-{uuid.uuid4().hex[:16]}"
            )
            self.agent_contexts[enterprise_id] = agent_context
            logger.info(f"[RPA] Contexto de agente creado para {enterprise_id}")
        return self.agent_contexts[enterprise_id]
    
    def _send_webhook_notification(
        self,
        connection: EnterpriseConnection,
        event: RealtimeDataEvent,
        result: Any
    ):
        """Envía notificación a webhook de la empresa."""
        try:
            import requests
            
            payload = {
                "event_id": event.event_id,
                "category": event.category,
                "task_type": event.task_type,
                "success": result.success,
                "result": result.data,
                "message": result.message,
                "execution_time": result.execution_time,
                "timestamp": datetime.now().isoformat()
            }
            
            response = requests.post(
                connection.webhook_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if response.status_code == 200:
                print(f"[RPA] Notificacion enviada a webhook de {connection.name}")
            else:
                print(f"[RPA] Error enviando webhook: {response.status_code}")
        
        except Exception as e:
            print(f"[RPA] Error enviando webhook: {e}")
    
    def get_connection_stats(self, enterprise_id: str) -> Optional[Dict[str, Any]]:
        """Obtiene estadísticas de una conexión."""
        connection = self.connections.get(enterprise_id)
        if not connection:
            return None
        
        return {
            "enterprise_id": connection.enterprise_id,
            "name": connection.name,
            "status": connection.status,
            "total_requests": connection.total_requests,
            "successful_automations": connection.successful_automations,
            "failed_automations": connection.failed_automations,
            "success_rate": (
                (connection.successful_automations / connection.total_requests * 100)
                if connection.total_requests > 0 else 0
            ),
            "last_activity": connection.last_activity,
            "created_at": connection.created_at
        }
    
    def get_all_connections(self) -> List[Dict[str, Any]]:
        """Obtiene todas las conexiones."""
        return [self._connection_to_dict(conn) for conn in self.connections.values()]
    
    def get_recent_events(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Obtiene eventos recientes."""
        with self.events_lock:
            return [self._event_to_dict(e) for e in self.realtime_events[-limit:]]
    
    def get_processing_metrics(self) -> Dict[str, Any]:
        """Obtiene métricas de procesamiento en tiempo real."""
        with self.metrics_lock:
            return {
                "total_events_received": self.metrics.total_events_received,
                "total_events_processed": self.metrics.total_events_processed,
                "total_events_failed": self.metrics.total_events_failed,
                "average_processing_time": self.metrics.average_processing_time,
                "events_per_second": self.metrics.events_per_second,
                "active_connections": self.metrics.active_connections,
                "queue_size": self.metrics.queue_size,
                "success_rate": (
                    (self.metrics.total_events_processed / self.metrics.total_events_received * 100)
                    if self.metrics.total_events_received > 0 else 0.0
                ),
                "last_updated": self.metrics.last_updated
            }
    
    def get_agent_context(self, enterprise_id: str) -> Optional[Dict[str, Any]]:
        """Obtiene el contexto de un agente para una empresa."""
        agent = self.agent_contexts.get(enterprise_id)
        if not agent:
            return None
        
        return {
            "agent_id": agent.agent_id,
            "enterprise_id": agent.enterprise_id,
            "session_id": agent.session_id,
            "short_term_memory_size": len(agent.short_term_memory),
            "long_term_memory_keys": list(agent.long_term_memory.keys()),
            "total_actions": agent.total_actions,
            "successful_actions": agent.successful_actions,
            "success_rate": (
                (agent.successful_actions / agent.total_actions * 100)
                if agent.total_actions > 0 else 0.0
            ),
            "created_at": agent.created_at,
            "last_activity": agent.last_activity
        }
    
    def register_streaming_callback(
        self,
        enterprise_id: str,
        callback: Callable[[RealtimeDataEvent, Any], None]
    ):
        """
        Registra un callback para recibir actualizaciones en tiempo real vía streaming.
        
        Args:
            enterprise_id: ID de la empresa
            callback: Función que recibirá (event, result) cuando se procese un evento
        """
        self.streaming_connections[enterprise_id] = callback
        logger.info(f"[RPA] Callback de streaming registrado para {enterprise_id}")
    
    def unregister_streaming_callback(self, enterprise_id: str):
        """Elimina el callback de streaming para una empresa."""
        if enterprise_id in self.streaming_connections:
            del self.streaming_connections[enterprise_id]
            logger.info(f"[RPA] Callback de streaming eliminado para {enterprise_id}")

