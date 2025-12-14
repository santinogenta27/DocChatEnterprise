"""
Base Connector - Clase base para todos los conectores enterprise.

Maneja:
- Autenticación OAuth2/SSO
- Refresh de tokens
- Webhooks y polling
- Detección de nuevos PDFs
"""

from __future__ import annotations

import asyncio
import json
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable, Tuple
from urllib.parse import urlparse

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class ConnectorStatus(Enum):
    """Estado del conector."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"
    REFRESHING_TOKEN = "refreshing_token"


@dataclass
class ConnectorConfig:
    """Configuración base de un conector."""
    connector_id: str
    connector_type: str  # sharepoint, aws_s3, google_drive, salesforce, servicenow
    display_name: str
    status: ConnectorStatus = ConnectorStatus.DISCONNECTED
    
    # OAuth2 / SSO
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    tenant_id: Optional[str] = None  # Para SharePoint/Azure AD
    redirect_uri: Optional[str] = None
    
    # Tokens
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    token_expires_at: Optional[datetime] = None
    
    # Webhook / Polling
    webhook_url: Optional[str] = None
    webhook_secret: Optional[str] = None
    polling_interval: int = 300  # 5 minutos por defecto
    use_webhooks: bool = True  # Preferir webhooks si están disponibles
    
    # Filtros
    folder_paths: List[str] = field(default_factory=list)  # Carpetas específicas a monitorear
    file_extensions: List[str] = field(default_factory=lambda: [".pdf"])
    exclude_patterns: List[str] = field(default_factory=list)
    
    # Metadata
    last_sync: Optional[datetime] = None
    last_poll: Optional[datetime] = None
    total_files_detected: int = 0
    total_files_processed: int = 0
    
    # Configuración adicional específica del conector
    extra_config: Dict[str, Any] = field(default_factory=dict)
    
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


class BaseEnterpriseConnector(ABC):
    """Clase base para todos los conectores enterprise."""
    
    def __init__(
        self,
        config: ConnectorConfig,
        process_pdf_callback: Optional[Callable[[str, Dict[str, Any]], None]] = None
    ):
        """
        Inicializa el conector.
        
        Args:
            config: Configuración del conector
            process_pdf_callback: Función a llamar cuando se detecta un PDF nuevo
                                Signature: process_pdf(file_url: str, metadata: Dict[str, Any]) -> None
        """
        self.config = config
        self.process_pdf_callback = process_pdf_callback
        
        # Session HTTP con retry
        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Tracking de archivos procesados (para evitar duplicados)
        self.processed_files: Dict[str, datetime] = {}
        
        # Estado de polling/webhooks
        self._polling_task: Optional[asyncio.Task] = None
        self._webhook_running = False
    
    # ==================== MÉTODOS ABSTRACTOS ====================
    
    @abstractmethod
    async def authenticate(self) -> bool:
        """
        Autentica el conector usando OAuth2/SSO.
        
        Returns:
            True si la autenticación fue exitosa
        """
        pass
    
    @abstractmethod
    async def refresh_access_token(self) -> bool:
        """
        Refresca el access token usando el refresh token.
        
        Returns:
            True si el refresh fue exitoso
        """
        pass
    
    @abstractmethod
    async def list_new_files(self, since: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """
        Lista archivos nuevos desde la última sincronización.
        
        Args:
            since: Fecha desde la cual buscar archivos nuevos
            
        Returns:
            Lista de diccionarios con metadata de archivos:
            [
                {
                    "file_id": "unique_id",
                    "file_name": "document.pdf",
                    "file_url": "https://...",
                    "file_size": 12345,
                    "modified_at": datetime,
                    "metadata": {...}
                },
                ...
            ]
        """
        pass
    
    @abstractmethod
    async def download_file(self, file_url: str, file_id: str) -> Tuple[bytes, Dict[str, Any]]:
        """
        Descarga un archivo desde la URL.
        
        Args:
            file_url: URL del archivo
            file_id: ID único del archivo
            
        Returns:
            Tupla (contenido_bytes, metadata_dict)
        """
        pass
    
    @abstractmethod
    async def setup_webhook(self, webhook_url: str) -> bool:
        """
        Configura un webhook para recibir notificaciones de archivos nuevos.
        
        Args:
            webhook_url: URL donde recibir las notificaciones
            
        Returns:
            True si el webhook fue configurado exitosamente
        """
        pass
    
    @abstractmethod
    async def delete_webhook(self) -> bool:
        """
        Elimina el webhook configurado.
        
        Returns:
            True si fue eliminado exitosamente
        """
        pass
    
    # ==================== MÉTODOS COMUNES ====================
    
    def _is_token_expired(self) -> bool:
        """Verifica si el token está expirado o próximo a expirar (5 min buffer)."""
        if not self.config.token_expires_at:
            return True
        buffer = timedelta(minutes=5)
        return datetime.now() >= (self.config.token_expires_at - buffer)
    
    async def _ensure_authenticated(self) -> bool:
        """Asegura que el conector esté autenticado (refresca token si es necesario)."""
        if not self.config.access_token:
            return await self.authenticate()
        
        if self._is_token_expired():
            if self.config.refresh_token:
                return await self.refresh_access_token()
            else:
                return await self.authenticate()
        
        return True
    
    def _should_process_file(self, file_info: Dict[str, Any]) -> bool:
        """
        Determina si un archivo debe ser procesado.
        
        Args:
            file_info: Metadata del archivo
            
        Returns:
            True si el archivo debe ser procesado
        """
        file_name = file_info.get("file_name", "").lower()
        file_id = file_info.get("file_id", "")
        
        # Verificar extensión
        if not any(file_name.endswith(ext) for ext in self.config.file_extensions):
            return False
        
        # Verificar patrones de exclusión
        for pattern in self.config.exclude_patterns:
            if pattern.lower() in file_name:
                return False
        
        # Verificar si ya fue procesado (últimas 24 horas)
        if file_id in self.processed_files:
            last_processed = self.processed_files[file_id]
            if datetime.now() - last_processed < timedelta(hours=24):
                return False
        
        return True
    
    async def process_new_file(self, file_info: Dict[str, Any]) -> bool:
        """
        Procesa un archivo nuevo llamando al callback.
        
        Args:
            file_info: Metadata del archivo
            
        Returns:
            True si el archivo fue procesado exitosamente
        """
        try:
            file_id = file_info.get("file_id")
            file_url = file_info.get("file_url")
            file_name = file_info.get("file_name", "unknown")
            
            if not file_id or not file_url:
                print(f"⚠️ [{self.config.display_name}] Archivo sin ID o URL: {file_name}")
                return False
            
            # Verificar si debe procesarse
            if not self._should_process_file(file_info):
                return False
            
            # Llamar al callback
            if self.process_pdf_callback:
                metadata = {
                    "connector_type": self.config.connector_type,
                    "connector_id": self.config.connector_id,
                    "file_id": file_id,
                    "file_name": file_name,
                    "file_size": file_info.get("file_size", 0),
                    "modified_at": file_info.get("modified_at"),
                    "source_url": file_url,
                    **file_info.get("metadata", {})
                }
                
                self.process_pdf_callback(file_url, metadata)
                
                # Marcar como procesado
                self.processed_files[file_id] = datetime.now()
                self.config.total_files_processed += 1
                
                print(f"✅ [{self.config.display_name}] PDF procesado: {file_name}")
                return True
            else:
                print(f"⚠️ [{self.config.display_name}] No hay callback configurado para procesar: {file_name}")
                return False
                
        except Exception as e:
            print(f"❌ [{self.config.display_name}] Error procesando archivo {file_info.get('file_name', 'unknown')}: {e}")
            return False
    
    async def start_polling(self):
        """Inicia el polling automático de archivos nuevos."""
        if self._polling_task and not self._polling_task.done():
            print(f"⚠️ [{self.config.display_name}] Polling ya está corriendo")
            return
        
        self._polling_task = asyncio.create_task(self._polling_loop())
        print(f"✅ [{self.config.display_name}] Polling iniciado (intervalo: {self.config.polling_interval}s)")
    
    async def stop_polling(self):
        """Detiene el polling automático."""
        if self._polling_task:
            self._polling_task.cancel()
            try:
                await self._polling_task
            except asyncio.CancelledError:
                pass
            self._polling_task = None
            print(f"✅ [{self.config.display_name}] Polling detenido")
    
    async def _polling_loop(self):
        """Loop principal de polling."""
        while True:
            try:
                await self._ensure_authenticated()
                
                # Obtener archivos nuevos desde la última sincronización
                since = self.config.last_poll or self.config.last_sync
                new_files = await self.list_new_files(since=since)
                
                print(f"🔍 [{self.config.display_name}] Polling: {len(new_files)} archivos nuevos detectados")
                
                # Procesar cada archivo nuevo
                for file_info in new_files:
                    await self.process_new_file(file_info)
                
                # Actualizar última sincronización
                self.config.last_poll = datetime.now()
                self.config.total_files_detected += len(new_files)
                
                # Esperar antes del siguiente poll
                await asyncio.sleep(self.config.polling_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"❌ [{self.config.display_name}] Error en polling loop: {e}")
                await asyncio.sleep(60)  # Esperar 1 minuto antes de reintentar
    
    async def connect(self, use_webhooks: Optional[bool] = None) -> bool:
        """
        Conecta el conector y configura webhooks o polling.
        
        Args:
            use_webhooks: Si usar webhooks (None = usar config por defecto)
            
        Returns:
            True si la conexión fue exitosa
        """
        try:
            self.config.status = ConnectorStatus.CONNECTING
            
            # Autenticar
            if not await self._ensure_authenticated():
                self.config.status = ConnectorStatus.ERROR
                return False
            
            # Intentar configurar webhook si está disponible y habilitado
            use_webhooks = use_webhooks if use_webhooks is not None else self.config.use_webhooks
            if use_webhooks and self.config.webhook_url:
                if await self.setup_webhook(self.config.webhook_url):
                    self._webhook_running = True
                    print(f"✅ [{self.config.display_name}] Webhook configurado")
                else:
                    print(f"⚠️ [{self.config.display_name}] No se pudo configurar webhook, usando polling")
                    await self.start_polling()
            else:
                # Usar polling como fallback
                await self.start_polling()
            
            self.config.status = ConnectorStatus.CONNECTED
            self.config.updated_at = datetime.now()
            return True
            
        except Exception as e:
            print(f"❌ [{self.config.display_name}] Error conectando: {e}")
            self.config.status = ConnectorStatus.ERROR
            return False
    
    async def disconnect(self):
        """Desconecta el conector y limpia recursos."""
        try:
            await self.stop_polling()
            
            if self._webhook_running:
                await self.delete_webhook()
                self._webhook_running = False
            
            self.config.status = ConnectorStatus.DISCONNECTED
            self.config.updated_at = datetime.now()
            print(f"✅ [{self.config.display_name}] Desconectado")
            
        except Exception as e:
            print(f"⚠️ [{self.config.display_name}] Error desconectando: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """Obtiene el estado actual del conector."""
        return {
            "connector_id": self.config.connector_id,
            "connector_type": self.config.connector_type,
            "display_name": self.config.display_name,
            "status": self.config.status.value,
            "last_sync": self.config.last_sync.isoformat() if self.config.last_sync else None,
            "last_poll": self.config.last_poll.isoformat() if self.config.last_poll else None,
            "total_files_detected": self.config.total_files_detected,
            "total_files_processed": self.config.total_files_processed,
            "webhook_active": self._webhook_running,
            "polling_active": self._polling_task is not None and not self._polling_task.done(),
        }

