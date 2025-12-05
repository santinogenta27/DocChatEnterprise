"""Connections Manager - Gestión de conexiones y sincronización de documentos.

Sistema centralizado para conectar fuentes externas (Gmail, Drive, Outlook, etc.)
y sincronizar documentos automáticamente organizados por fuente.
"""

from __future__ import annotations

import os
import json
import shutil
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field, asdict
from enum import Enum

from .config import AppConfig


class ConnectionStatus(Enum):
    """Estado de una conexión."""
    DISCONNECTED = "disconnected"
    CONNECTED = "connected"
    SYNCING = "syncing"
    ERROR = "error"


class SyncMode(Enum):
    """Modo de sincronización."""
    MANUAL = "manual"  # Solo guardar, usuario decide qué analizar
    AUTO_ALL = "auto_all"  # Analizar todo automáticamente
    AUTO_FILTERED = "auto_filtered"  # Analizar solo de remitentes/carpetas específicas


@dataclass
class ConnectionConfig:
    """Configuración de una conexión."""
    source_id: str
    source_type: str  # gmail, drive, outlook, onedrive, dropbox, slack
    display_name: str
    status: str = "disconnected"
    sync_mode: str = "manual"
    filters: List[str] = field(default_factory=list)  # Remitentes o carpetas a filtrar
    last_sync: Optional[str] = None
    total_documents: int = 0
    credentials: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class SyncedDocument:
    """Documento sincronizado."""
    doc_id: str
    filename: str
    source_type: str
    source_id: str
    file_path: str
    file_size: int
    synced_at: str
    analyzed: bool = False
    analysis_result: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    category: str = "otros"  # facturas, contratos, reportes, otros


class ConnectionsManager:
    """
    Gestor de conexiones y documentos sincronizados.
    
    Funcionalidades:
    - Conectar/desconectar fuentes (Gmail, Drive, etc.)
    - Sincronizar documentos automáticamente
    - Organizar por fuente y categoría
    - Analizar documentos bajo demanda o automáticamente
    """
    
    # Tipos de fuentes soportadas
    SUPPORTED_SOURCES = {
        "gmail": {
            "name": "Gmail",
            "icon": "📧",
            "description": "Sincroniza PDFs adjuntos de tu correo Gmail",
            "oauth_url": "https://accounts.google.com/o/oauth2/auth",
            "scopes": ["https://www.googleapis.com/auth/gmail.readonly"]
        },
        "google_drive": {
            "name": "Google Drive",
            "icon": "📁",
            "description": "Sincroniza PDFs de tu Google Drive",
            "oauth_url": "https://accounts.google.com/o/oauth2/auth",
            "scopes": ["https://www.googleapis.com/auth/drive.readonly"]
        },
        "outlook": {
            "name": "Outlook",
            "icon": "📨",
            "description": "Sincroniza PDFs adjuntos de tu correo Outlook",
            "oauth_url": "https://login.microsoftonline.com/common/oauth2/v2.0/authorize",
            "scopes": ["Mail.Read"]
        },
        "onedrive": {
            "name": "OneDrive",
            "icon": "💼",
            "description": "Sincroniza PDFs de tu OneDrive",
            "oauth_url": "https://login.microsoftonline.com/common/oauth2/v2.0/authorize",
            "scopes": ["Files.Read"]
        },
        "dropbox": {
            "name": "Dropbox",
            "icon": "📦",
            "description": "Sincroniza PDFs de tu Dropbox",
            "oauth_url": "https://www.dropbox.com/oauth2/authorize",
            "scopes": []
        },
        "slack": {
            "name": "Slack",
            "icon": "💬",
            "description": "Sincroniza PDFs compartidos en Slack",
            "oauth_url": "https://slack.com/oauth/v2/authorize",
            "scopes": ["files:read"]
        }
    }
    
    def __init__(self, config: AppConfig):
        self.config = config
        
        # Directorio base para documentos sincronizados
        self.sync_dir = Path(config.memory_dir) / "synced_documents"
        self.sync_dir.mkdir(parents=True, exist_ok=True)
        
        # Archivo de configuración de conexiones
        self.connections_file = self.sync_dir / "connections.json"
        
        # Archivo de índice de documentos
        self.documents_index_file = self.sync_dir / "documents_index.json"
        
        # Cargar datos
        self.connections: Dict[str, ConnectionConfig] = self._load_connections()
        self.documents_index: Dict[str, SyncedDocument] = self._load_documents_index()
        
        # Crear carpetas por fuente
        self._ensure_source_folders()
    
    def _load_connections(self) -> Dict[str, ConnectionConfig]:
        """Carga las conexiones guardadas."""
        try:
            if self.connections_file.exists():
                with open(self.connections_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return {
                        k: ConnectionConfig(**v) for k, v in data.items()
                    }
        except Exception as e:
            print(f"Error cargando conexiones: {e}")
        return {}
    
    def _save_connections(self):
        """Guarda las conexiones."""
        try:
            data = {k: asdict(v) for k, v in self.connections.items()}
            with open(self.connections_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error guardando conexiones: {e}")
    
    def _load_documents_index(self) -> Dict[str, SyncedDocument]:
        """Carga el índice de documentos."""
        try:
            if self.documents_index_file.exists():
                with open(self.documents_index_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return {
                        k: SyncedDocument(**v) for k, v in data.items()
                    }
        except Exception as e:
            print(f"Error cargando índice de documentos: {e}")
        return {}
    
    def _save_documents_index(self):
        """Guarda el índice de documentos."""
        try:
            data = {k: asdict(v) for k, v in self.documents_index.items()}
            with open(self.documents_index_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error guardando índice de documentos: {e}")
    
    def _ensure_source_folders(self):
        """Crea carpetas para cada fuente soportada."""
        for source_type in self.SUPPORTED_SOURCES.keys():
            folder = self.sync_dir / source_type
            folder.mkdir(parents=True, exist_ok=True)
    
    def get_source_folder(self, source_type: str) -> Path:
        """Obtiene la carpeta de una fuente."""
        return self.sync_dir / source_type
    
    # ==================== GESTIÓN DE CONEXIONES ====================
    
    def connect_source(
        self,
        source_type: str,
        credentials: Dict[str, Any],
        sync_mode: str = "manual",
        filters: List[str] = None
    ) -> Dict[str, Any]:
        """
        Conecta una nueva fuente.
        
        Args:
            source_type: Tipo de fuente (gmail, drive, etc.)
            credentials: Credenciales OAuth
            sync_mode: manual, auto_all, auto_filtered
            filters: Lista de filtros (remitentes, carpetas)
        
        Returns:
            Resultado de la conexión
        """
        if source_type not in self.SUPPORTED_SOURCES:
            return {"success": False, "error": f"Fuente no soportada: {source_type}"}
        
        source_info = self.SUPPORTED_SOURCES[source_type]
        source_id = f"{source_type}_{hashlib.md5(json.dumps(credentials, sort_keys=True).encode()).hexdigest()[:8]}"
        
        # Crear configuración de conexión
        connection = ConnectionConfig(
            source_id=source_id,
            source_type=source_type,
            display_name=source_info["name"],
            status="connected",
            sync_mode=sync_mode,
            filters=filters or [],
            credentials=credentials
        )
        
        self.connections[source_id] = connection
        self._save_connections()
        
        return {
            "success": True,
            "source_id": source_id,
            "message": f"{source_info['icon']} {source_info['name']} conectado exitosamente"
        }
    
    def disconnect_source(self, source_id: str) -> Dict[str, Any]:
        """Desconecta una fuente."""
        if source_id not in self.connections:
            return {"success": False, "error": "Conexión no encontrada"}
        
        connection = self.connections[source_id]
        connection.status = "disconnected"
        connection.credentials = {}
        self._save_connections()
        
        return {
            "success": True,
            "message": f"Conexión {connection.display_name} desconectada"
        }
    
    def get_connection_status(self, source_id: str) -> Dict[str, Any]:
        """Obtiene el estado de una conexión."""
        if source_id not in self.connections:
            return {"status": "not_found"}
        
        conn = self.connections[source_id]
        return {
            "status": conn.status,
            "source_type": conn.source_type,
            "display_name": conn.display_name,
            "sync_mode": conn.sync_mode,
            "last_sync": conn.last_sync,
            "total_documents": conn.total_documents
        }
    
    def list_connections(self) -> List[Dict[str, Any]]:
        """Lista todas las conexiones."""
        result = []
        for source_id, conn in self.connections.items():
            source_info = self.SUPPORTED_SOURCES.get(conn.source_type, {})
            result.append({
                "source_id": source_id,
                "source_type": conn.source_type,
                "display_name": conn.display_name,
                "icon": source_info.get("icon", "📄"),
                "status": conn.status,
                "sync_mode": conn.sync_mode,
                "last_sync": conn.last_sync,
                "total_documents": conn.total_documents
            })
        return result
    
    def update_sync_mode(self, source_id: str, sync_mode: str, filters: List[str] = None) -> Dict[str, Any]:
        """Actualiza el modo de sincronización de una conexión."""
        if source_id not in self.connections:
            return {"success": False, "error": "Conexión no encontrada"}
        
        self.connections[source_id].sync_mode = sync_mode
        if filters is not None:
            self.connections[source_id].filters = filters
        self._save_connections()
        
        return {"success": True, "message": "Configuración actualizada"}
    
    # ==================== GESTIÓN DE DOCUMENTOS ====================
    
    def add_document(
        self,
        source_type: str,
        source_id: str,
        filename: str,
        file_content: bytes,
        metadata: Dict[str, Any] = None,
        category: str = "otros"
    ) -> Dict[str, Any]:
        """
        Agrega un documento sincronizado.
        
        Args:
            source_type: Tipo de fuente
            source_id: ID de la conexión
            filename: Nombre del archivo
            file_content: Contenido del archivo en bytes
            metadata: Metadatos adicionales
            category: Categoría del documento
        
        Returns:
            Resultado de la operación
        """
        # Generar ID único para el documento
        content_hash = hashlib.md5(file_content).hexdigest()[:12]
        doc_id = f"{source_type}_{content_hash}"
        
        # Verificar si ya existe
        if doc_id in self.documents_index:
            return {
                "success": False,
                "error": "Documento ya existe",
                "doc_id": doc_id
            }
        
        # Guardar archivo en la carpeta correspondiente
        source_folder = self.get_source_folder(source_type)
        
        # Crear subcarpeta por categoría
        category_folder = source_folder / category
        category_folder.mkdir(parents=True, exist_ok=True)
        
        # Guardar archivo
        file_path = category_folder / filename
        
        # Si ya existe un archivo con ese nombre, agregar sufijo
        counter = 1
        original_stem = file_path.stem
        while file_path.exists():
            file_path = category_folder / f"{original_stem}_{counter}{file_path.suffix}"
            counter += 1
        
        with open(file_path, 'wb') as f:
            f.write(file_content)
        
        # Crear registro del documento
        doc = SyncedDocument(
            doc_id=doc_id,
            filename=file_path.name,
            source_type=source_type,
            source_id=source_id,
            file_path=str(file_path),
            file_size=len(file_content),
            synced_at=datetime.now().isoformat(),
            metadata=metadata or {},
            category=category
        )
        
        self.documents_index[doc_id] = doc
        self._save_documents_index()
        
        # Actualizar contador en la conexión
        if source_id in self.connections:
            self.connections[source_id].total_documents += 1
            self._save_connections()
        
        return {
            "success": True,
            "doc_id": doc_id,
            "file_path": str(file_path),
            "message": f"Documento guardado: {filename}"
        }
    
    def get_documents_by_source(self, source_type: str = None) -> Dict[str, List[Dict[str, Any]]]:
        """
        Obtiene documentos organizados por fuente.
        
        Args:
            source_type: Filtrar por tipo de fuente (opcional)
        
        Returns:
            Diccionario con documentos por fuente y categoría
        """
        result = {}
        
        for doc_id, doc in self.documents_index.items():
            if source_type and doc.source_type != source_type:
                continue
            
            if doc.source_type not in result:
                result[doc.source_type] = {
                    "info": self.SUPPORTED_SOURCES.get(doc.source_type, {}),
                    "total": 0,
                    "categories": {}
                }
            
            if doc.category not in result[doc.source_type]["categories"]:
                result[doc.source_type]["categories"][doc.category] = []
            
            result[doc.source_type]["categories"][doc.category].append({
                "doc_id": doc.doc_id,
                "filename": doc.filename,
                "file_path": doc.file_path,
                "file_size": doc.file_size,
                "synced_at": doc.synced_at,
                "analyzed": doc.analyzed,
                "category": doc.category
            })
            result[doc.source_type]["total"] += 1
        
        return result
    
    def get_dashboard_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas para el dashboard."""
        stats = {
            "total_connections": len([c for c in self.connections.values() if c.status == "connected"]),
            "total_documents": len(self.documents_index),
            "analyzed_documents": len([d for d in self.documents_index.values() if d.analyzed]),
            "pending_analysis": len([d for d in self.documents_index.values() if not d.analyzed]),
            "by_source": {},
            "by_category": {},
            "storage_used_mb": 0
        }
        
        for doc in self.documents_index.values():
            # Por fuente
            if doc.source_type not in stats["by_source"]:
                stats["by_source"][doc.source_type] = 0
            stats["by_source"][doc.source_type] += 1
            
            # Por categoría
            if doc.category not in stats["by_category"]:
                stats["by_category"][doc.category] = 0
            stats["by_category"][doc.category] += 1
            
            # Tamaño
            stats["storage_used_mb"] += doc.file_size / (1024 * 1024)
        
        stats["storage_used_mb"] = round(stats["storage_used_mb"], 2)
        
        return stats
    
    def mark_as_analyzed(self, doc_id: str, analysis_result: Dict[str, Any] = None) -> Dict[str, Any]:
        """Marca un documento como analizado."""
        if doc_id not in self.documents_index:
            return {"success": False, "error": "Documento no encontrado"}
        
        self.documents_index[doc_id].analyzed = True
        self.documents_index[doc_id].analysis_result = analysis_result
        self._save_documents_index()
        
        return {"success": True}
    
    def get_documents_for_analysis(self, source_type: str = None, limit: int = 100) -> List[str]:
        """Obtiene rutas de documentos pendientes de análisis."""
        docs = []
        for doc in self.documents_index.values():
            if not doc.analyzed:
                if source_type is None or doc.source_type == source_type:
                    docs.append(doc.file_path)
                    if len(docs) >= limit:
                        break
        return docs
    
    def delete_document(self, doc_id: str) -> Dict[str, Any]:
        """Elimina un documento."""
        if doc_id not in self.documents_index:
            return {"success": False, "error": "Documento no encontrado"}
        
        doc = self.documents_index[doc_id]
        
        # Eliminar archivo físico
        try:
            file_path = Path(doc.file_path)
            if file_path.exists():
                file_path.unlink()
        except Exception as e:
            print(f"Error eliminando archivo: {e}")
        
        # Actualizar contador en conexión
        if doc.source_id in self.connections:
            self.connections[doc.source_id].total_documents -= 1
            self._save_connections()
        
        # Eliminar del índice
        del self.documents_index[doc_id]
        self._save_documents_index()
        
        return {"success": True, "message": "Documento eliminado"}
    
    # ==================== SIMULACIÓN DE SYNC (para demo) ====================
    
    def simulate_sync(self, source_type: str, num_docs: int = 5) -> Dict[str, Any]:
        """
        Simula una sincronización para demostración.
        Crea documentos de ejemplo.
        """
        import random
        
        categories = ["facturas", "contratos", "reportes", "otros"]
        
        source_info = self.SUPPORTED_SOURCES.get(source_type, {})
        if not source_info:
            return {"success": False, "error": "Fuente no soportada"}
        
        # Buscar conexión existente o crear una temporal
        source_id = None
        for sid, conn in self.connections.items():
            if conn.source_type == source_type and conn.status == "connected":
                source_id = sid
                break
        
        if not source_id:
            # Crear conexión de demo
            result = self.connect_source(source_type, {"demo": True})
            source_id = result.get("source_id")
        
        # Crear documentos de ejemplo
        created = []
        for i in range(num_docs):
            category = random.choice(categories)
            filename = f"documento_ejemplo_{i+1}_{category}.pdf"
            
            # Contenido de ejemplo (texto simple convertido a bytes)
            content = f"""
            Documento de ejemplo #{i+1}
            Fuente: {source_info.get('name', source_type)}
            Categoría: {category}
            Fecha: {datetime.now().isoformat()}
            
            Este es un documento de demostración para probar
            el sistema de sincronización de documentos.
            """.encode('utf-8')
            
            result = self.add_document(
                source_type=source_type,
                source_id=source_id,
                filename=filename,
                file_content=content,
                category=category,
                metadata={"demo": True, "index": i+1}
            )
            
            if result.get("success"):
                created.append(result.get("doc_id"))
        
        # Actualizar última sincronización
        if source_id in self.connections:
            self.connections[source_id].last_sync = datetime.now().isoformat()
            self._save_connections()
        
        return {
            "success": True,
            "documents_created": len(created),
            "doc_ids": created,
            "message": f"Sincronización simulada: {len(created)} documentos creados"
        }

