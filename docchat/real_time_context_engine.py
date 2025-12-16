"""
Real-Time Context Engine - Similar al Real-Time Context Engine de Confluent
Materializa datos enriquecidos en cache en memoria y sirve contexto en tiempo real a través de MCP

Basado en:
- Confluent Real-Time Context Engine
- Model Context Protocol (MCP)
- Streaming data processing con Kafka/Flink
"""

from __future__ import annotations

import json
import time
import asyncio
from typing import Dict, Any, Optional, List, AsyncIterator
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict
import threading
import queue as thread_queue

try:
    from confluent_kafka import Producer, Consumer
    CONFLUENT_AVAILABLE = True
except ImportError:
    CONFLUENT_AVAILABLE = False


@dataclass
class ContextEntry:
    """Entrada de contexto en tiempo real."""
    context_id: str
    data: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    enriched: bool = False
    source: str = "chatpdf_mode"


class RealTimeContextEngine:
    """
    Real-Time Context Engine - Materializa datos enriquecidos en cache en memoria
    y sirve contexto en tiempo real a través de MCP.
    
    Similar al Real-Time Context Engine de Confluent:
    - Materializa datos enriquecidos en cache en memoria
    - Sirve contexto en tiempo real a través de MCP
    - Unifica procesamiento histórico, continuo y serving en tiempo real
    - Governance, seguridad y auditabilidad integrados
    """
    
    def __init__(
        self,
        bootstrap_servers: Optional[str] = None,
        enabled: bool = True
    ):
        self.enabled = enabled
        self.bootstrap_servers = bootstrap_servers
        
        # Cache en memoria para contexto en tiempo real (similar a Confluent)
        self.context_cache: Dict[str, ContextEntry] = {}
        self.cache_lock = threading.Lock()
        
        # Streaming producer para Confluent/Kafka
        self.producer = None
        if CONFLUENT_AVAILABLE and bootstrap_servers:
            try:
                config = {"bootstrap.servers": bootstrap_servers}
                self.producer = Producer(config)
                print("✅ [Real-Time Context Engine] Confluent/Kafka habilitado")
            except Exception as e:
                print(f"⚠️ [Real-Time Context Engine] Error inicializando Confluent: {e}")
        
        # Queue para streaming de contexto en tiempo real
        self.context_queue = thread_queue.Queue()
        self.streaming_active = False
        
        # Auditabilidad y governance
        self.audit_log: List[Dict[str, Any]] = []
        self.access_control: Dict[str, List[str]] = {}  # session_id -> allowed_operations
        
    def materialize_context(
        self,
        context_id: str,
        data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
        source: str = "chatpdf_mode"
    ) -> ContextEntry:
        """
        Materializa contexto enriquecido en cache en memoria.
        Similar a cómo Confluent materializa datos enriquecidos.
        """
        entry = ContextEntry(
            context_id=context_id,
            data=data,
            metadata=metadata or {},
            timestamp=datetime.now(),
            enriched=True,
            source=source
        )
        
        with self.cache_lock:
            self.context_cache[context_id] = entry
        
        # Publicar a Confluent/Kafka si está disponible
        if self.producer:
            try:
                event = {
                    "context_id": context_id,
                    "data": data,
                    "metadata": metadata or {},
                    "timestamp": datetime.now().isoformat(),
                    "source": source,
                    "type": "context_materialized"
                }
                self.producer.produce(
                    "real_time_context_events",
                    json.dumps(event).encode('utf-8')
                )
                self.producer.poll(0)
            except Exception as e:
                print(f"⚠️ [Real-Time Context Engine] Error publicando a Kafka: {e}")
        
        # Registrar en audit log
        self.audit_log.append({
            "timestamp": datetime.now().isoformat(),
            "operation": "materialize_context",
            "context_id": context_id,
            "source": source
        })
        
        return entry
    
    def get_context(
        self,
        context_id: str,
        session_id: Optional[str] = None
    ) -> Optional[ContextEntry]:
        """
        Obtiene contexto materializado del cache en memoria.
        Similar a cómo Confluent sirve contexto a través de MCP.
        """
        with self.cache_lock:
            entry = self.context_cache.get(context_id)
        
        if entry:
            # Registrar acceso en audit log
            self.audit_log.append({
                "timestamp": datetime.now().isoformat(),
                "operation": "get_context",
                "context_id": context_id,
                "session_id": session_id
            })
        
        return entry
    
    def stream_context_realtime(
        self,
        context_id: str,
        session_id: str
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Stream de contexto en tiempo real (similar a MCP).
        Emite actualizaciones inmediatas cuando el contexto cambia.
        """
        last_update = None
        
        async def context_stream():
            nonlocal last_update
            while True:
                entry = self.get_context(context_id, session_id)
                
                if entry and entry != last_update:
                    yield {
                        "context_id": context_id,
                        "data": entry.data,
                        "metadata": entry.metadata,
                        "timestamp": entry.timestamp.isoformat(),
                        "enriched": entry.enriched,
                        "source": entry.source
                    }
                    last_update = entry
                
                await asyncio.sleep(0.01)  # Poll cada 10ms para real-time
        
        return context_stream()
    
    def update_context_streaming(
        self,
        context_id: str,
        token: str,
        session_id: str
    ):
        """
        Actualiza contexto en tiempo real durante streaming.
        Materializa cada token inmediatamente en el cache.
        """
        with self.cache_lock:
            if context_id not in self.context_cache:
                self.context_cache[context_id] = ContextEntry(
                    context_id=context_id,
                    data={"text": "", "tokens": []},
                    metadata={"session_id": session_id},
                    timestamp=datetime.now()
                )
            
            entry = self.context_cache[context_id]
            entry.data["text"] += token
            entry.data["tokens"].append(token)
            entry.timestamp = datetime.now()
        
        # Publicar actualización a queue para streaming inmediato
        self.context_queue.put({
            "type": "context_update",
            "context_id": context_id,
            "token": token,
            "current_text": entry.data["text"],
            "timestamp": datetime.now().isoformat()
        })
        
        # Publicar a Confluent/Kafka si está disponible
        if self.producer:
            try:
                event = {
                    "context_id": context_id,
                    "token": token,
                    "current_text": entry.data["text"],
                    "timestamp": datetime.now().isoformat(),
                    "type": "context_streaming_update"
                }
                self.producer.produce(
                    "real_time_context_streaming",
                    json.dumps(event).encode('utf-8')
                )
                self.producer.poll(0)
            except Exception as e:
                print(f"⚠️ [Real-Time Context Engine] Error publicando streaming a Kafka: {e}")
    
    def get_audit_log(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Obtiene log de auditoría para governance."""
        return self.audit_log[-limit:]
    
    def flush(self):
        """Flush producer para asegurar que todos los mensajes se envíen."""
        if self.producer:
            self.producer.flush()


# Instancia global
_real_time_context_engine: Optional[RealTimeContextEngine] = None


def get_real_time_context_engine(
    bootstrap_servers: Optional[str] = None,
    enabled: bool = True
) -> RealTimeContextEngine:
    """Obtiene o crea la instancia global del Real-Time Context Engine."""
    global _real_time_context_engine
    
    if _real_time_context_engine is None:
        _real_time_context_engine = RealTimeContextEngine(
            bootstrap_servers=bootstrap_servers,
            enabled=enabled
        )
    
    return _real_time_context_engine


