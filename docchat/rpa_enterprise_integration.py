"""
Sistema de Integración Enterprise para Automatización RPA.
Permite que empresas conecten sus sistemas por API y los Agentic AI procesen datos en tiempo real.
"""

from __future__ import annotations

import json
import time
import secrets
import asyncio
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime
from pathlib import Path
from threading import Thread
import queue

from .config import AppConfig
from .rpa_automation import RPAAutomationEngine


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


class RPAEnterpriseIntegration:
    """
    Sistema de integración Enterprise para RPA.
    
    Permite que empresas:
    - Se registren y obtengan API keys
    - Envíen datos en tiempo real vía webhooks
    - Los Agentic AI procesen automáticamente los datos recibidos
    - Reciban resultados y notificaciones
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
        
        # Almacenamiento en memoria
        self.connections: Dict[str, EnterpriseConnection] = {}
        self.realtime_events: List[RealtimeDataEvent] = []
        
        # Cola para procesamiento en tiempo real
        self.event_queue: queue.Queue = queue.Queue()
        
        # Thread para procesar eventos en tiempo real
        self.processing_thread: Optional[Thread] = None
        self.processing_active = False
        
        # Cargar datos existentes
        self._load_data()
        
        # Iniciar procesamiento en tiempo real
        self.start_realtime_processing()
    
    def _load_data(self):
        """Carga conexiones y eventos guardados."""
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
                        event = RealtimeDataEvent(**event_data)
                        self.realtime_events.append(event)
        except Exception as e:
            print(f"Error cargando datos enterprise: {e}")
    
    def _save_data(self):
        """Guarda conexiones y eventos."""
        try:
            # Guardar conexiones
            connections_data = [self._connection_to_dict(conn) for conn in self.connections.values()]
            with open(self.connections_file, 'w', encoding='utf-8') as f:
                json.dump(connections_data, f, indent=2, ensure_ascii=False)
            
            # Guardar últimos 1000 eventos
            events_data = [self._event_to_dict(e) for e in self.realtime_events[-1000:]]
            with open(self.events_file, 'w', encoding='utf-8') as f:
                json.dump(events_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error guardando datos enterprise: {e}")
    
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
            "result": event.result
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
        
        print(f"✅ Conexión Enterprise registrada: {name} (ID: {enterprise_id})")
        
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
        data: Dict[str, Any]
    ) -> RealtimeDataEvent:
        """
        Recibe datos en tiempo real de una empresa y los agrega a la cola de procesamiento.
        
        Args:
            enterprise_id: ID de la empresa
            category: Categoría de automatización
            task_type: Tipo de tarea
            data: Datos para procesar
        
        Returns:
            RealtimeDataEvent creado
        """
        # Verificar que la conexión existe y está activa
        connection = self.connections.get(enterprise_id)
        if not connection:
            raise ValueError(f"Conexión enterprise no encontrada: {enterprise_id}")
        
        if connection.status != "active":
            raise ValueError(f"Conexión enterprise no está activa: {enterprise_id}")
        
        # Crear evento
        event = RealtimeDataEvent(
            event_id=f"EVT-{int(time.time())}-{len(self.realtime_events)}",
            enterprise_id=enterprise_id,
            category=category,
            task_type=task_type,
            data=data
        )
        
        # Agregar a cola de procesamiento
        self.event_queue.put(event)
        
        # Agregar a historial
        self.realtime_events.append(event)
        
        # Actualizar estadísticas de conexión
        connection.total_requests += 1
        connection.last_activity = datetime.now().isoformat()
        
        self._save_data()
        
        print(f"📡 Datos recibidos de {connection.name}: {category}/{task_type}")
        
        return event
    
    def start_realtime_processing(self):
        """Inicia el procesamiento en tiempo real de eventos."""
        if self.processing_active:
            return
        
        self.processing_active = True
        self.processing_thread = Thread(target=self._process_events_loop, daemon=True)
        self.processing_thread.start()
        print("🚀 Procesamiento en tiempo real iniciado")
    
    def stop_realtime_processing(self):
        """Detiene el procesamiento en tiempo real."""
        self.processing_active = False
        if self.processing_thread:
            self.processing_thread.join(timeout=5)
        print("⏹️ Procesamiento en tiempo real detenido")
    
    def _process_events_loop(self):
        """Loop principal para procesar eventos en tiempo real."""
        while self.processing_active:
            try:
                # Obtener evento de la cola (timeout de 1 segundo)
                try:
                    event = self.event_queue.get(timeout=1)
                except queue.Empty:
                    continue
                
                # Procesar evento
                self._process_event(event)
                
            except Exception as e:
                print(f"Error procesando evento: {e}")
                import traceback
                traceback.print_exc()
    
    def _process_event(self, event: RealtimeDataEvent):
        """
        Procesa un evento automáticamente con Agentic AI.
        
        Args:
            event: Evento a procesar
        """
        print(f"\n{'='*60}")
        print(f"🤖 PROCESANDO EVENTO EN TIEMPO REAL")
        print(f"{'='*60}")
        print(f"Event ID: {event.event_id}")
        print(f"Enterprise: {self.connections.get(event.enterprise_id, {}).name}")
        print(f"Categoría: {event.category}")
        print(f"Tarea: {event.task_type}")
        print()
        
        try:
            # Ejecutar automatización con RPA Engine
            result = self.rpa_engine.execute_automation(
                category=event.category,
                task_type=event.task_type,
                parameters=event.data,
                documents=None
            )
            
            # Marcar como procesado
            event.processed = True
            event.result = {
                "success": result.success,
                "automation_id": result.automation_id,
                "data": result.data,
                "message": result.message,
                "execution_time": result.execution_time
            }
            
            # Actualizar estadísticas de conexión
            connection = self.connections.get(event.enterprise_id)
            if connection:
                if result.success:
                    connection.successful_automations += 1
                else:
                    connection.failed_automations += 1
            
            # Enviar notificación a webhook si está configurado
            if connection and connection.webhook_url:
                self._send_webhook_notification(connection, event, result)
            
            self._save_data()
            
            print(f"✅ Evento procesado exitosamente")
            print()
        
        except Exception as e:
            error_msg = str(e)
            print(f"❌ Error procesando evento: {error_msg}")
            print()
            
            event.processed = True
            event.result = {
                "success": False,
                "error": error_msg
            }
            
            # Actualizar estadísticas
            connection = self.connections.get(event.enterprise_id)
            if connection:
                connection.failed_automations += 1
            
            self._save_data()
    
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
                print(f"✅ Notificación enviada a webhook de {connection.name}")
            else:
                print(f"⚠️ Error enviando webhook: {response.status_code}")
        
        except Exception as e:
            print(f"⚠️ Error enviando webhook: {e}")
    
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
        return [self._event_to_dict(e) for e in self.realtime_events[-limit:]]

