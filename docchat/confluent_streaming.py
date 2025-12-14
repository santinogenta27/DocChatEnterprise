"""
Confluent Streaming Integration - Real-Time Data Streaming para SNIPE SHOT

Integra Confluent Cloud/Kafka para streaming de datos en tiempo real:
- Producer: Publica eventos y datos en tiempo real
- Consumer: Consume y procesa datos en tiempo real
- Stream Processing: Procesa eventos y actualiza el Knowledge Graph
- Glitch Detection: Detecta anomalías y eventos en tiempo real
- Real-Time RAG: Actualiza el sistema RAG con datos en streaming

Basado en:
- Confluent Cloud Platform
- Apache Kafka
- Real-time data streaming patterns
"""

from __future__ import annotations

import json
import asyncio
import threading
import time
from typing import Optional, Dict, Any, List, Callable, Union
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict
from enum import Enum

try:
    from confluent_kafka import Producer, Consumer, KafkaError, KafkaException
    from confluent_kafka.admin import AdminClient, NewTopic
    CONFLUENT_AVAILABLE = True
except ImportError:
    Producer = None  # type: ignore
    Consumer = None  # type: ignore
    KafkaError = None  # type: ignore
    KafkaException = None  # type: ignore
    AdminClient = None  # type: ignore
    NewTopic = None  # type: ignore
    CONFLUENT_AVAILABLE = False
    print("⚠️ confluent-kafka no instalado. Instala con: pip install confluent-kafka")


class EventType(str, Enum):
    """Tipos de eventos en tiempo real."""
    DOCUMENT_UPDATED = "document_updated"
    DOCUMENT_DELETED = "document_deleted"
    QUERY_PROCESSED = "query_processed"
    KNOWLEDGE_GRAPH_UPDATED = "knowledge_graph_updated"
    GLITCH_DETECTED = "glitch_detected"
    ANOMALY_DETECTED = "anomaly_detected"
    REAL_TIME_UPDATE = "real_time_update"
    STREAMING_DATA = "streaming_data"
    ENTITY_DETECTED = "entity_detected"
    RELATIONSHIP_DETECTED = "relationship_detected"


@dataclass
class StreamingEvent:
    """Evento de streaming en tiempo real."""
    event_id: str
    event_type: EventType
    timestamp: datetime
    data: Dict[str, Any]
    source: str = "snipe_shot"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GlitchEvent:
    """Evento de glitch/anomalía detectado."""
    glitch_id: str
    glitch_type: str
    severity: str  # "low", "medium", "high", "critical"
    timestamp: datetime
    description: str
    data: Dict[str, Any]
    context: Dict[str, Any] = field(default_factory=dict)


class ConfluentStreamingProducer:
    """Producer de Confluent para publicar eventos en tiempo real."""
    
    def __init__(
        self,
        bootstrap_servers: str,
        security_config: Optional[Dict[str, Any]] = None,
        enabled: bool = True
    ):
        self.enabled = enabled and CONFLUENT_AVAILABLE
        self.bootstrap_servers = bootstrap_servers
        self.security_config = security_config or {}
        self._producer: Optional[Producer] = None
        
        if self.enabled:
            self._initialize_producer()
    
    def _initialize_producer(self):
        """Inicializa el producer de Confluent."""
        try:
            config = {
                "bootstrap.servers": self.bootstrap_servers,
                "client.id": "snipe_shot_producer",
                "acks": "all",  # Esperar confirmación de todos los replicas
                "retries": 3,
                "max.in.flight.requests.per.connection": 1,
                "enable.idempotence": True,  # Garantizar exactamente una vez
            }
            config.update(self.security_config)
            
            self._producer = Producer(config)
            print("✅ [Confluent Producer] Inicializado correctamente")
        except Exception as e:
            print(f"❌ [Confluent Producer] Error inicializando: {e}")
            self.enabled = False
    
    def produce_event(
        self,
        topic: str,
        event: StreamingEvent,
        callback: Optional[Callable] = None
    ) -> bool:
        """Publica un evento en el topic de Kafka."""
        if not self.enabled or not self._producer:
            return False
        
        try:
            # Serializar evento
            payload = {
                "event_id": event.event_id,
                "event_type": event.event_type.value,
                "timestamp": event.timestamp.isoformat(),
                "data": event.data,
                "source": event.source,
                "metadata": event.metadata
            }
            
            message = json.dumps(payload, ensure_ascii=False, default=str)
            
            # Publicar con callback para manejo de errores
            def delivery_callback(err, msg):
                if err:
                    print(f"❌ [Confluent Producer] Error entregando mensaje: {err}")
                elif callback:
                    callback(err, msg)
            
            self._producer.produce(
                topic,
                value=message.encode("utf-8"),
                key=event.event_id.encode("utf-8"),
                callback=delivery_callback
            )
            
            # Poll para procesar callbacks
            self._producer.poll(0)
            return True
            
        except Exception as e:
            print(f"❌ [Confluent Producer] Error publicando evento: {e}")
            return False
    
    def produce_glitch(
        self,
        topic: str,
        glitch: GlitchEvent,
        callback: Optional[Callable] = None
    ) -> bool:
        """Publica un evento de glitch/anomalía."""
        if not self.enabled or not self._producer:
            return False
        
        try:
            payload = {
                "glitch_id": glitch.glitch_id,
                "glitch_type": glitch.glitch_type,
                "severity": glitch.severity,
                "timestamp": glitch.timestamp.isoformat(),
                "description": glitch.description,
                "data": glitch.data,
                "context": glitch.context
            }
            
            message = json.dumps(payload, ensure_ascii=False, default=str)
            
            def delivery_callback(err, msg):
                if err:
                    print(f"❌ [Confluent Producer] Error entregando glitch: {err}")
                elif callback:
                    callback(err, msg)
            
            self._producer.produce(
                topic,
                value=message.encode("utf-8"),
                key=glitch.glitch_id.encode("utf-8"),
                callback=delivery_callback
            )
            
            self._producer.poll(0)
            return True
            
        except Exception as e:
            print(f"❌ [Confluent Producer] Error publicando glitch: {e}")
            return False
    
    def flush(self, timeout: float = 5.0) -> None:
        """Flush de todos los mensajes pendientes."""
        if self.enabled and self._producer:
            try:
                self._producer.flush(timeout)
            except Exception as e:
                print(f"⚠️ [Confluent Producer] Error en flush: {e}")


class ConfluentStreamingConsumer:
    """Consumer de Confluent para consumir eventos en tiempo real."""
    
    def __init__(
        self,
        bootstrap_servers: str,
        group_id: str = "snipe_shot_consumer",
        topics: List[str] = None,
        security_config: Optional[Dict[str, Any]] = None,
        enabled: bool = True
    ):
        self.enabled = enabled and CONFLUENT_AVAILABLE
        self.bootstrap_servers = bootstrap_servers
        self.group_id = group_id
        self.topics = topics or []
        self.security_config = security_config or {}
        self._consumer: Optional[Consumer] = None
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._event_handlers: Dict[str, List[Callable]] = defaultdict(list)
        
        if self.enabled:
            self._initialize_consumer()
    
    def _initialize_consumer(self):
        """Inicializa el consumer de Confluent."""
        try:
            config = {
                "bootstrap.servers": self.bootstrap_servers,
                "group.id": self.group_id,
                "auto.offset.reset": "latest",  # "earliest" para procesar desde el inicio
                "enable.auto.commit": True,
                "auto.commit.interval.ms": 1000,
            }
            config.update(self.security_config)
            
            self._consumer = Consumer(config)
            if self.topics:
                self._consumer.subscribe(self.topics)
            print(f"✅ [Confluent Consumer] Inicializado para topics: {self.topics}")
        except Exception as e:
            print(f"❌ [Confluent Consumer] Error inicializando: {e}")
            self.enabled = False
    
    def register_handler(self, event_type: str, handler: Callable):
        """Registra un handler para un tipo de evento."""
        self._event_handlers[event_type].append(handler)
    
    def start_consuming(self, timeout: float = 1.0):
        """Inicia el consumo de mensajes en un thread separado."""
        if not self.enabled or not self._consumer or self._running:
            return
        
        self._running = True
        self._thread = threading.Thread(
            target=self._consume_loop,
            args=(timeout,),
            daemon=True
        )
        self._thread.start()
        print(f"✅ [Confluent Consumer] Iniciado consumo en background")
    
    def _consume_loop(self, timeout: float):
        """Loop principal de consumo de mensajes."""
        while self._running:
            try:
                msg = self._consumer.poll(timeout=timeout)
                
                if msg is None:
                    continue
                
                if msg.error():
                    if msg.error().code() == KafkaError._PARTITION_EOF:
                        # Fin de partición, continuar
                        continue
                    else:
                        print(f"❌ [Confluent Consumer] Error: {msg.error()}")
                        continue
                
                # Procesar mensaje
                try:
                    payload = json.loads(msg.value().decode("utf-8"))
                    event_type = payload.get("event_type") or payload.get("glitch_type")
                    
                    # Llamar handlers registrados
                    if event_type in self._event_handlers:
                        for handler in self._event_handlers[event_type]:
                            try:
                                handler(payload)
                            except Exception as e:
                                print(f"⚠️ [Confluent Consumer] Error en handler: {e}")
                    
                except json.JSONDecodeError as e:
                    print(f"⚠️ [Confluent Consumer] Error decodificando JSON: {e}")
                    
            except Exception as e:
                if self._running:
                    print(f"⚠️ [Confluent Consumer] Error en consume loop: {e}")
                time.sleep(0.1)
    
    def stop_consuming(self):
        """Detiene el consumo de mensajes."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5.0)
        if self._consumer:
            try:
                self._consumer.close()
            except Exception:
                pass
        print("✅ [Confluent Consumer] Detenido")


class ConfluentStreamingManager:
    """
    Manager completo para streaming en tiempo real con Confluent.
    
    Integra Producer y Consumer para:
    - Publicar eventos en tiempo real
    - Consumir y procesar datos en streaming
    - Detectar glitches/anomalías
    - Actualizar Knowledge Graph en tiempo real
    """
    
    def __init__(
        self,
        bootstrap_servers: str,
        security_config: Optional[Dict[str, Any]] = None,
        enabled: bool = True
    ):
        self.bootstrap_servers = bootstrap_servers
        self.security_config = security_config or {}
        self.enabled = enabled and CONFLUENT_AVAILABLE
        
        # Producer y Consumer
        self.producer = ConfluentStreamingProducer(
            bootstrap_servers=bootstrap_servers,
            security_config=security_config,
            enabled=enabled
        )
        
        self.consumer = ConfluentStreamingConsumer(
            bootstrap_servers=bootstrap_servers,
            group_id="snipe_shot_streaming",
            topics=["snipe_shot_events", "snipe_shot_glitches", "snipe_shot_updates"],
            security_config=security_config,
            enabled=enabled
        )
        
        # Callbacks para integración con SNIPE SHOT
        self.on_document_update: Optional[Callable] = None
        self.on_knowledge_graph_update: Optional[Callable] = None
        self.on_glitch_detected: Optional[Callable] = None
        self.on_streaming_data: Optional[Callable] = None
        
        # Estadísticas
        self.stats = {
            "events_produced": 0,
            "events_consumed": 0,
            "glitches_detected": 0,
            "errors": 0
        }
        
        if self.enabled:
            self._setup_consumer_handlers()
    
    def _setup_consumer_handlers(self):
        """Configura handlers para eventos consumidos."""
        # Handler para actualizaciones de documentos
        def handle_document_update(payload: Dict[str, Any]):
            self.stats["events_consumed"] += 1
            if self.on_document_update:
                try:
                    self.on_document_update(payload)
                except Exception as e:
                    print(f"⚠️ [Streaming Manager] Error en on_document_update: {e}")
        
        # Handler para actualizaciones del Knowledge Graph
        def handle_kg_update(payload: Dict[str, Any]):
            self.stats["events_consumed"] += 1
            if self.on_knowledge_graph_update:
                try:
                    self.on_knowledge_graph_update(payload)
                except Exception as e:
                    print(f"⚠️ [Streaming Manager] Error en on_knowledge_graph_update: {e}")
        
        # Handler para glitches
        def handle_glitch(payload: Dict[str, Any]):
            self.stats["glitches_detected"] += 1
            if self.on_glitch_detected:
                try:
                    self.on_glitch_detected(payload)
                except Exception as e:
                    print(f"⚠️ [Streaming Manager] Error en on_glitch_detected: {e}")
        
        # Handler para datos en streaming
        def handle_streaming_data(payload: Dict[str, Any]):
            self.stats["events_consumed"] += 1
            if self.on_streaming_data:
                try:
                    self.on_streaming_data(payload)
                except Exception as e:
                    print(f"⚠️ [Streaming Manager] Error en on_streaming_data: {e}")
        
        # Registrar handlers
        self.consumer.register_handler(EventType.DOCUMENT_UPDATED.value, handle_document_update)
        self.consumer.register_handler(EventType.KNOWLEDGE_GRAPH_UPDATED.value, handle_kg_update)
        self.consumer.register_handler(EventType.GLITCH_DETECTED.value, handle_glitch)
        self.consumer.register_handler(EventType.STREAMING_DATA.value, handle_streaming_data)
    
    def start_streaming(self):
        """Inicia el streaming (consumer en background)."""
        if self.enabled:
            self.consumer.start_consuming()
            print("✅ [Streaming Manager] Streaming iniciado")
    
    def stop_streaming(self):
        """Detiene el streaming."""
        if self.enabled:
            self.consumer.stop_consuming()
            self.producer.flush()
            print("✅ [Streaming Manager] Streaming detenido")
    
    def publish_document_update(
        self,
        document_id: str,
        action: str,
        data: Dict[str, Any]
    ) -> bool:
        """Publica una actualización de documento."""
        if not self.enabled:
            return False
        
        event = StreamingEvent(
            event_id=f"doc_update_{document_id}_{int(time.time())}",
            event_type=EventType.DOCUMENT_UPDATED,
            timestamp=datetime.now(),
            data={
                "document_id": document_id,
                "action": action,
                **data
            },
            source="snipe_shot"
        )
        
        success = self.producer.produce_event("snipe_shot_events", event)
        if success:
            self.stats["events_produced"] += 1
        return success
    
    def publish_knowledge_graph_update(
        self,
        entities: List[str],
        relationships: List[Dict[str, Any]],
        action: str = "updated"
    ) -> bool:
        """Publica una actualización del Knowledge Graph."""
        if not self.enabled:
            return False
        
        event = StreamingEvent(
            event_id=f"kg_update_{int(time.time())}",
            event_type=EventType.KNOWLEDGE_GRAPH_UPDATED,
            timestamp=datetime.now(),
            data={
                "entities": entities,
                "relationships": relationships,
                "action": action
            },
            source="snipe_shot"
        )
        
        success = self.producer.produce_event("snipe_shot_updates", event)
        if success:
            self.stats["events_produced"] += 1
        return success
    
    def publish_glitch(
        self,
        glitch_type: str,
        severity: str,
        description: str,
        data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Publica un evento de glitch/anomalía."""
        if not self.enabled:
            return False
        
        glitch = GlitchEvent(
            glitch_id=f"glitch_{int(time.time())}_{glitch_type}",
            glitch_type=glitch_type,
            severity=severity,
            timestamp=datetime.now(),
            description=description,
            data=data,
            context=context or {}
        )
        
        success = self.producer.produce_glitch("snipe_shot_glitches", glitch)
        if success:
            self.stats["glitches_detected"] += 1
        return success
    
    def publish_streaming_data(
        self,
        data_type: str,
        data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Publica datos en streaming."""
        if not self.enabled:
            return False
        
        event = StreamingEvent(
            event_id=f"stream_{data_type}_{int(time.time())}",
            event_type=EventType.STREAMING_DATA,
            timestamp=datetime.now(),
            data={
                "data_type": data_type,
                **data
            },
            metadata=metadata or {}
        )
        
        success = self.producer.produce_event("snipe_shot_updates", event)
        if success:
            self.stats["events_produced"] += 1
        return success
    
    def get_statistics(self) -> Dict[str, Any]:
        """Obtiene estadísticas del streaming."""
        return {
            **self.stats,
            "enabled": self.enabled,
            "producer_enabled": self.producer.enabled,
            "consumer_enabled": self.consumer.enabled,
            "consumer_running": self.consumer._running if self.consumer else False
        }


__all__ = [
    "ConfluentStreamingManager",
    "ConfluentStreamingProducer",
    "ConfluentStreamingConsumer",
    "StreamingEvent",
    "GlitchEvent",
    "EventType",
    "CONFLUENT_AVAILABLE"
]

