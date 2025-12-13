"""
Enterprise Connector Manager - Gestiona todos los conectores enterprise.

Coordina:
- Inicialización de conectores
- Webhooks y polling
- Procesamiento automático de PDFs
- Integración con Event Storage Mode
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable

from .base_connector import BaseEnterpriseConnector, ConnectorConfig, ConnectorStatus
from .sharepoint_connector import SharePointConnector
from .aws_s3_connector import AWSS3Connector
from .google_drive_connector import GoogleDriveConnector
from .salesforce_connector import SalesforceConnector
from .servicenow_connector import ServiceNowConnector


class EnterpriseConnectorManager:
    """Gestiona todos los conectores enterprise."""
    
    def __init__(
        self,
        config_dir: Optional[Path] = None,
        process_pdf_callback: Optional[Callable[[str, Dict[str, Any]], None]] = None
    ):
        """
        Inicializa el manager.
        
        Args:
            config_dir: Directorio donde guardar configuraciones de conectores
            process_pdf_callback: Función a llamar cuando se detecta un PDF nuevo
        """
        self.config_dir = config_dir or Path.home() / ".docchat" / "connectors"
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        self.process_pdf_callback = process_pdf_callback
        self.connectors: Dict[str, BaseEnterpriseConnector] = {}
        self._running = False
    
    def _create_connector(self, config: ConnectorConfig) -> Optional[BaseEnterpriseConnector]:
        """Crea un conector basado en su tipo."""
        connector_type = config.connector_type.lower()
        
        if connector_type == "sharepoint" or connector_type == "onedrive":
            return SharePointConnector(config, self.process_pdf_callback)
        elif connector_type == "aws_s3" or connector_type == "s3":
            return AWSS3Connector(config, self.process_pdf_callback)
        elif connector_type == "google_drive" or connector_type == "gdrive":
            return GoogleDriveConnector(config, self.process_pdf_callback)
        elif connector_type == "salesforce":
            return SalesforceConnector(config, self.process_pdf_callback)
        elif connector_type == "servicenow":
            return ServiceNowConnector(config, self.process_pdf_callback)
        else:
            print(f"❌ [ConnectorManager] Tipo de conector desconocido: {connector_type}")
            return None
    
    def add_connector(self, config: ConnectorConfig) -> bool:
        """
        Agrega un conector al manager.
        
        Args:
            config: Configuración del conector
            
        Returns:
            True si el conector fue agregado exitosamente
        """
        try:
            connector = self._create_connector(config)
            if not connector:
                return False
            
            self.connectors[config.connector_id] = connector
            self._save_connector_config(config)
            
            print(f"✅ [ConnectorManager] Conector agregado: {config.display_name}")
            return True
            
        except Exception as e:
            print(f"❌ [ConnectorManager] Error agregando conector: {e}")
            return False
    
    def remove_connector(self, connector_id: str) -> bool:
        """Elimina un conector."""
        try:
            if connector_id in self.connectors:
                connector = self.connectors[connector_id]
                asyncio.create_task(connector.disconnect())
                del self.connectors[connector_id]
                
                # Eliminar archivo de configuración
                config_file = self.config_dir / f"{connector_id}.json"
                if config_file.exists():
                    config_file.unlink()
                
                print(f"✅ [ConnectorManager] Conector eliminado: {connector_id}")
                return True
            return False
            
        except Exception as e:
            print(f"❌ [ConnectorManager] Error eliminando conector: {e}")
            return False
    
    async def connect_all(self) -> Dict[str, bool]:
        """Conecta todos los conectores."""
        results = {}
        
        for connector_id, connector in self.connectors.items():
            try:
                success = await connector.connect()
                results[connector_id] = success
            except Exception as e:
                print(f"❌ [ConnectorManager] Error conectando {connector_id}: {e}")
                results[connector_id] = False
        
        return results
    
    async def disconnect_all(self):
        """Desconecta todos los conectores."""
        for connector in self.connectors.values():
            try:
                await connector.disconnect()
            except Exception as e:
                print(f"⚠️ [ConnectorManager] Error desconectando: {e}")
    
    def get_connector(self, connector_id: str) -> Optional[BaseEnterpriseConnector]:
        """Obtiene un conector por ID."""
        return self.connectors.get(connector_id)
    
    def get_all_status(self) -> Dict[str, Dict[str, Any]]:
        """Obtiene el estado de todos los conectores."""
        return {
            connector_id: connector.get_status()
            for connector_id, connector in self.connectors.items()
        }
    
    def _save_connector_config(self, config: ConnectorConfig):
        """Guarda la configuración de un conector en disco."""
        try:
            config_file = self.config_dir / f"{config.connector_id}.json"
            
            # Convertir a dict (excluyendo tokens sensibles en el log)
            config_dict = {
                "connector_id": config.connector_id,
                "connector_type": config.connector_type,
                "display_name": config.display_name,
                "status": config.status.value,
                "client_id": config.client_id,
                "tenant_id": config.tenant_id,
                "redirect_uri": config.redirect_uri,
                "access_token": config.access_token,  # Guardar para persistencia
                "refresh_token": config.refresh_token,
                "token_expires_at": config.token_expires_at.isoformat() if config.token_expires_at else None,
                "webhook_url": config.webhook_url,
                "webhook_secret": config.webhook_secret,
                "polling_interval": config.polling_interval,
                "use_webhooks": config.use_webhooks,
                "folder_paths": config.folder_paths,
                "file_extensions": config.file_extensions,
                "exclude_patterns": config.exclude_patterns,
                "last_sync": config.last_sync.isoformat() if config.last_sync else None,
                "last_poll": config.last_poll.isoformat() if config.last_poll else None,
                "total_files_detected": config.total_files_detected,
                "total_files_processed": config.total_files_processed,
                "extra_config": config.extra_config,
                "created_at": config.created_at.isoformat(),
                "updated_at": config.updated_at.isoformat()
            }
            
            config_file.write_text(json.dumps(config_dict, indent=2), encoding="utf-8")
            
        except Exception as e:
            print(f"⚠️ [ConnectorManager] Error guardando configuración: {e}")
    
    def load_connector_config(self, connector_id: str) -> Optional[ConnectorConfig]:
        """Carga la configuración de un conector desde disco."""
        try:
            config_file = self.config_dir / f"{connector_id}.json"
            if not config_file.exists():
                return None
            
            config_dict = json.loads(config_file.read_text(encoding="utf-8"))
            
            # Reconstruir ConnectorConfig
            config = ConnectorConfig(
                connector_id=config_dict["connector_id"],
                connector_type=config_dict["connector_type"],
                display_name=config_dict["display_name"],
                status=ConnectorStatus(config_dict.get("status", "disconnected")),
                client_id=config_dict.get("client_id"),
                client_secret=config_dict.get("client_secret"),  # Puede no estar en el archivo por seguridad
                tenant_id=config_dict.get("tenant_id"),
                redirect_uri=config_dict.get("redirect_uri"),
                access_token=config_dict.get("access_token"),
                refresh_token=config_dict.get("refresh_token"),
                token_expires_at=datetime.fromisoformat(config_dict["token_expires_at"]) if config_dict.get("token_expires_at") else None,
                webhook_url=config_dict.get("webhook_url"),
                webhook_secret=config_dict.get("webhook_secret"),
                polling_interval=config_dict.get("polling_interval", 300),
                use_webhooks=config_dict.get("use_webhooks", True),
                folder_paths=config_dict.get("folder_paths", []),
                file_extensions=config_dict.get("file_extensions", [".pdf"]),
                exclude_patterns=config_dict.get("exclude_patterns", []),
                last_sync=datetime.fromisoformat(config_dict["last_sync"]) if config_dict.get("last_sync") else None,
                last_poll=datetime.fromisoformat(config_dict["last_poll"]) if config_dict.get("last_poll") else None,
                total_files_detected=config_dict.get("total_files_detected", 0),
                total_files_processed=config_dict.get("total_files_processed", 0),
                extra_config=config_dict.get("extra_config", {}),
                created_at=datetime.fromisoformat(config_dict.get("created_at", datetime.now().isoformat())),
                updated_at=datetime.fromisoformat(config_dict.get("updated_at", datetime.now().isoformat()))
            )
            
            return config
            
        except Exception as e:
            print(f"❌ [ConnectorManager] Error cargando configuración: {e}")
            return None
    
    def load_all_connectors(self):
        """Carga todos los conectores guardados desde disco."""
        try:
            for config_file in self.config_dir.glob("*.json"):
                connector_id = config_file.stem
                config = self.load_connector_config(connector_id)
                if config:
                    self.add_connector(config)
                    
        except Exception as e:
            print(f"❌ [ConnectorManager] Error cargando conectores: {e}")
    
    def handle_webhook(self, connector_id: str, notification: Dict[str, Any]) -> bool:
        """
        Maneja una notificación de webhook para un conector específico.
        
        Debe ser llamado desde el endpoint de webhook.
        """
        connector = self.get_connector(connector_id)
        if not connector:
            print(f"⚠️ [ConnectorManager] Conector no encontrado: {connector_id}")
            return False
        
        # Delegar al conector específico
        if hasattr(connector, "handle_webhook_notification"):
            return connector.handle_webhook_notification(notification)
        else:
            print(f"⚠️ [ConnectorManager] Conector {connector_id} no soporta webhooks")
            return False

