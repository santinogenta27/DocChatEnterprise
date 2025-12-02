"""
Sistema de Almacenamiento Persistente para DocChat Enterprise
Guarda todos los documentos, queries, respuestas y datos de JARVIS permanentemente
Usa SQLite + sistema de archivos para almacenamiento on-premise local
"""

from __future__ import annotations

import os
import sqlite3
import json
import shutil
import hashlib
from pathlib import Path
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime
from dataclasses import dataclass, asdict
import uuid

from langchain_core.documents import Document


@dataclass
class DocumentRecord:
    """Registro de documento en la base de datos."""
    doc_id: str
    file_name: str
    file_path: str
    file_type: str
    content_hash: str
    metadata: Dict[str, Any]
    session_id: str
    source: str  # guia_experto, chatbot, integraciones, etc.
    uploaded_at: str
    processed_at: Optional[str] = None
    tokens: Optional[int] = None


@dataclass
class QueryRecord:
    """Registro de query en la base de datos."""
    query_id: str
    session_id: str
    query_text: str
    source: str
    mode: str  # guia_experto, chatbot, etc.
    provider: str
    timestamp: str
    response_text: Optional[str] = None
    processing_time: Optional[float] = None
    components_used: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class JarvisDataRecord:
    """Registro de data absorbida por JARVIS."""
    record_id: str
    session_id: str
    data: str
    data_type: str  # query, response, document, insight, alert, task
    source: str
    metadata: Dict[str, Any]
    timestamp: str


class PersistentStorage:
    """
    Sistema de almacenamiento persistente usando SQLite + sistema de archivos.
    
    Estructura:
    - data/database.db: SQLite con toda la metadata
    - data/documents/: Documentos originales guardados
    - data/vectorstores/: Índices vectoriales persistentes
    - data/jarvis_data/: Datos adicionales de JARVIS
    """
    
    def __init__(self, base_dir: Optional[str] = None):
        """
        Inicializa el sistema de almacenamiento persistente.
        
        Args:
            base_dir: Directorio base para almacenamiento (default: ./data)
        """
        if base_dir is None:
            # Usar directorio relativo al proyecto
            base_dir = Path(__file__).parent.parent / "data"
        else:
            base_dir = Path(base_dir)
        
        self.base_dir = base_dir
        self.db_path = self.base_dir / "database.db"
        self.documents_dir = self.base_dir / "documents"
        self.vectorstores_dir = self.base_dir / "vectorstores"
        self.jarvis_data_dir = self.base_dir / "jarvis_data"
        
        # Crear directorios si no existen
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.documents_dir.mkdir(parents=True, exist_ok=True)
        self.vectorstores_dir.mkdir(parents=True, exist_ok=True)
        self.jarvis_data_dir.mkdir(parents=True, exist_ok=True)
        
        # Inicializar base de datos
        self._init_database()
        
        print(f"✅ Sistema de almacenamiento persistente inicializado en: {self.base_dir}")
    
    def _init_database(self):
        """Inicializa las tablas de SQLite."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        # Tabla de documentos
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                doc_id TEXT PRIMARY KEY,
                file_name TEXT NOT NULL,
                file_path TEXT NOT NULL,
                file_type TEXT NOT NULL,
                content_hash TEXT NOT NULL UNIQUE,
                metadata TEXT NOT NULL,
                session_id TEXT NOT NULL,
                source TEXT NOT NULL,
                uploaded_at TEXT NOT NULL,
                processed_at TEXT,
                tokens INTEGER
            )
        """)
        
        # Índice para búsqueda rápida
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_documents_session 
            ON documents(session_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_documents_source 
            ON documents(source)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_documents_hash 
            ON documents(content_hash)
        """)
        
        # Tabla de queries y respuestas
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS queries (
                query_id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                query_text TEXT NOT NULL,
                source TEXT NOT NULL,
                mode TEXT NOT NULL,
                provider TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                response_text TEXT,
                processing_time REAL,
                components_used TEXT,
                metadata TEXT
            )
        """)
        
        # Índices para queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_queries_session 
            ON queries(session_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_queries_source 
            ON queries(source)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_queries_timestamp 
            ON queries(timestamp)
        """)
        
        # Tabla de datos de JARVIS
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS jarvis_data (
                record_id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                data TEXT NOT NULL,
                data_type TEXT NOT NULL,
                source TEXT NOT NULL,
                metadata TEXT NOT NULL,
                timestamp TEXT NOT NULL
            )
        """)
        
        # Índices para JARVIS
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_jarvis_session 
            ON jarvis_data(session_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_jarvis_type 
            ON jarvis_data(data_type)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_jarvis_source 
            ON jarvis_data(source)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_jarvis_timestamp 
            ON jarvis_data(timestamp)
        """)
        
        # Tabla de insights de JARVIS
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS jarvis_insights (
                insight_id TEXT PRIMARY KEY,
                session_id TEXT,
                insight_text TEXT NOT NULL,
                confidence REAL,
                source_data TEXT,
                discovered_at TEXT NOT NULL,
                metadata TEXT
            )
        """)
        
        # Tabla de alertas de JARVIS
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS jarvis_alerts (
                alert_id TEXT PRIMARY KEY,
                session_id TEXT,
                alert_text TEXT NOT NULL,
                severity TEXT NOT NULL,
                source_data TEXT,
                created_at TEXT NOT NULL,
                resolved_at TEXT,
                metadata TEXT
            )
        """)
        
        # Tabla de tareas autónomas de JARVIS
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS jarvis_tasks (
                task_id TEXT PRIMARY KEY,
                session_id TEXT,
                task_description TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                completed_at TEXT,
                result TEXT,
                metadata TEXT
            )
        """)
        
        conn.commit()
        conn.close()
        
        print(f"✅ Base de datos inicializada: {self.db_path}")
    
    def save_document(
        self,
        document: Document,
        session_id: str,
        source: str,
        file_obj: Optional[Any] = None
    ) -> str:
        """
        Guarda un documento permanentemente.
        
        Args:
            document: Documento de LangChain
            session_id: ID de sesión
            source: Fuente del documento (guia_experto, chatbot, etc.)
            file_obj: Objeto de archivo original (opcional)
        
        Returns:
            doc_id: ID único del documento guardado
        """
        # Calcular hash del contenido
        content_hash = hashlib.sha256(
            document.page_content.encode('utf-8')
        ).hexdigest()
        
        # Verificar si ya existe (evitar duplicados)
        existing = self.get_document_by_hash(content_hash)
        if existing:
            print(f"📄 Documento ya existe (hash: {content_hash[:8]}...), reutilizando")
            return existing.doc_id
        
        # Generar ID único
        doc_id = str(uuid.uuid4())
        
        # Obtener metadata del documento
        metadata = document.metadata.copy()
        file_name = metadata.get("source", f"document_{doc_id}.txt")
        file_type = Path(file_name).suffix.lower() if file_name else ".txt"
        
        # Guardar archivo físico si hay file_obj
        file_path = None
        if file_obj and hasattr(file_obj, 'name'):
            # Crear subdirectorio por fecha para organización
            date_dir = datetime.now().strftime("%Y-%m")
            date_path = self.documents_dir / date_dir
            date_path.mkdir(parents=True, exist_ok=True)
            
            # Guardar archivo
            file_path = date_path / f"{doc_id}{file_type}"
            try:
                if hasattr(file_obj, 'read'):
                    # Es un objeto de archivo
                    with open(file_path, 'wb') as f:
                        shutil.copyfileobj(file_obj, f)
                else:
                    # Es una ruta
                    shutil.copy2(file_obj, file_path)
            except Exception as e:
                print(f"⚠️ Error guardando archivo físico: {e}")
                file_path = None
        
        # Si no hay file_obj, guardar contenido como texto
        if file_path is None:
            date_dir = datetime.now().strftime("%Y-%m")
            date_path = self.documents_dir / date_dir
            date_path.mkdir(parents=True, exist_ok=True)
            file_path = date_path / f"{doc_id}.txt"
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(document.page_content)
        
        # Calcular tokens aproximados
        tokens = len(document.page_content) // 4
        
        # Crear registro
        record = DocumentRecord(
            doc_id=doc_id,
            file_name=file_name,
            file_path=str(file_path.relative_to(self.base_dir)),
            file_type=file_type,
            content_hash=content_hash,
            metadata=metadata,
            session_id=session_id,
            source=source,
            uploaded_at=datetime.now().isoformat(),
            processed_at=datetime.now().isoformat(),
            tokens=tokens
        )
        
        # Guardar en base de datos
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO documents 
            (doc_id, file_name, file_path, file_type, content_hash, metadata, 
             session_id, source, uploaded_at, processed_at, tokens)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            record.doc_id,
            record.file_name,
            record.file_path,
            record.file_type,
            record.content_hash,
            json.dumps(record.metadata),
            record.session_id,
            record.source,
            record.uploaded_at,
            record.processed_at,
            record.tokens
        ))
        conn.commit()
        conn.close()
        
        print(f"💾 Documento guardado permanentemente: {file_name} (ID: {doc_id[:8]}...)")
        return doc_id
    
    def get_document_by_hash(self, content_hash: str) -> Optional[DocumentRecord]:
        """Obtiene un documento por su hash de contenido."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM documents WHERE content_hash = ?
        """, (content_hash,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return DocumentRecord(
                doc_id=row['doc_id'],
                file_name=row['file_name'],
                file_path=row['file_path'],
                file_type=row['file_type'],
                content_hash=row['content_hash'],
                metadata=json.loads(row['metadata']),
                session_id=row['session_id'],
                source=row['source'],
                uploaded_at=row['uploaded_at'],
                processed_at=row['processed_at'],
                tokens=row['tokens']
            )
        return None
    
    def get_all_documents(
        self,
        session_id: Optional[str] = None,
        source: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[DocumentRecord]:
        """Obtiene todos los documentos guardados."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        query = "SELECT * FROM documents WHERE 1=1"
        params = []
        
        if session_id:
            query += " AND session_id = ?"
            params.append(session_id)
        
        if source:
            query += " AND source = ?"
            params.append(source)
        
        query += " ORDER BY uploaded_at DESC"
        
        if limit:
            query += " LIMIT ?"
            params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        documents = []
        for row in rows:
            documents.append(DocumentRecord(
                doc_id=row['doc_id'],
                file_name=row['file_name'],
                file_path=row['file_path'],
                file_type=row['file_type'],
                content_hash=row['content_hash'],
                metadata=json.loads(row['metadata']),
                session_id=row['session_id'],
                source=row['source'],
                uploaded_at=row['uploaded_at'],
                processed_at=row['processed_at'],
                tokens=row['tokens']
            ))
        
        return documents
    
    def load_document_as_langchain(self, doc_id: str) -> Optional[Document]:
        """Carga un documento guardado como Document de LangChain."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM documents WHERE doc_id = ?", (doc_id,))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        # Leer contenido del archivo
        file_path = self.base_dir / row['file_path']
        if not file_path.exists():
            return None
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception:
            # Intentar como binario si falla
            with open(file_path, 'rb') as f:
                content = f.read().decode('utf-8', errors='ignore')
        
        metadata = json.loads(row['metadata'])
        metadata['doc_id'] = doc_id
        metadata['stored_at'] = row['uploaded_at']
        
        return Document(page_content=content, metadata=metadata)
    
    def save_query(
        self,
        session_id: str,
        query_text: str,
        source: str,
        mode: str,
        provider: str,
        response_text: Optional[str] = None,
        processing_time: Optional[float] = None,
        components_used: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Guarda una query y su respuesta permanentemente."""
        query_id = str(uuid.uuid4())
        
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO queries 
            (query_id, session_id, query_text, source, mode, provider, timestamp,
             response_text, processing_time, components_used, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            query_id,
            session_id,
            query_text,
            source,
            mode,
            provider,
            datetime.now().isoformat(),
            response_text,
            processing_time,
            json.dumps(components_used) if components_used else None,
            json.dumps(metadata) if metadata else None
        ))
        conn.commit()
        conn.close()
        
        return query_id
    
    def get_all_queries(
        self,
        session_id: Optional[str] = None,
        source: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[QueryRecord]:
        """Obtiene todas las queries guardadas."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        query = "SELECT * FROM queries WHERE 1=1"
        params = []
        
        if session_id:
            query += " AND session_id = ?"
            params.append(session_id)
        
        if source:
            query += " AND source = ?"
            params.append(source)
        
        query += " ORDER BY timestamp DESC"
        
        if limit:
            query += " LIMIT ?"
            params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        queries = []
        for row in rows:
            queries.append(QueryRecord(
                query_id=row['query_id'],
                session_id=row['session_id'],
                query_text=row['query_text'],
                source=row['source'],
                mode=row['mode'],
                provider=row['provider'],
                timestamp=row['timestamp'],
                response_text=row['response_text'],
                processing_time=row['processing_time'],
                components_used=json.loads(row['components_used']) if row['components_used'] else None,
                metadata=json.loads(row['metadata']) if row['metadata'] else None
            ))
        
        return queries
    
    def save_jarvis_data(
        self,
        session_id: str,
        data: Any,
        data_type: str,
        source: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Guarda data absorbida por JARVIS."""
        record_id = str(uuid.uuid4())
        
        # Convertir data a string si es necesario
        if isinstance(data, (dict, list)):
            data_str = json.dumps(data, ensure_ascii=False)
        elif isinstance(data, Document):
            data_str = json.dumps({
                "page_content": data.page_content,
                "metadata": data.metadata
            }, ensure_ascii=False)
        else:
            data_str = str(data)
        
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO jarvis_data 
            (record_id, session_id, data, data_type, source, metadata, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            record_id,
            session_id,
            data_str,
            data_type,
            source,
            json.dumps(metadata or {}),
            datetime.now().isoformat()
        ))
        conn.commit()
        conn.close()
        
        return record_id
    
    def get_all_jarvis_data(
        self,
        session_id: Optional[str] = None,
        data_type: Optional[str] = None,
        source: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[JarvisDataRecord]:
        """Obtiene toda la data de JARVIS."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        query = "SELECT * FROM jarvis_data WHERE 1=1"
        params = []
        
        if session_id:
            query += " AND session_id = ?"
            params.append(session_id)
        
        if data_type:
            query += " AND data_type = ?"
            params.append(data_type)
        
        if source:
            query += " AND source = ?"
            params.append(source)
        
        query += " ORDER BY timestamp DESC"
        
        if limit:
            query += " LIMIT ?"
            params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        records = []
        for row in rows:
            records.append(JarvisDataRecord(
                record_id=row['record_id'],
                session_id=row['session_id'],
                data=row['data'],
                data_type=row['data_type'],
                source=row['source'],
                metadata=json.loads(row['metadata']),
                timestamp=row['timestamp']
            ))
        
        return records
    
    def get_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas del almacenamiento."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        stats = {}
        
        # Contar documentos
        cursor.execute("SELECT COUNT(*) FROM documents")
        stats['total_documents'] = cursor.fetchone()[0]
        
        # Contar queries
        cursor.execute("SELECT COUNT(*) FROM queries")
        stats['total_queries'] = cursor.fetchone()[0]
        
        # Contar datos de JARVIS
        cursor.execute("SELECT COUNT(*) FROM jarvis_data")
        stats['total_jarvis_records'] = cursor.fetchone()[0]
        
        # Tamaño de base de datos
        db_size = self.db_path.stat().st_size if self.db_path.exists() else 0
        stats['database_size_mb'] = db_size / (1024 * 1024)
        
        # Tamaño de documentos
        total_docs_size = sum(
            f.stat().st_size 
            for f in self.documents_dir.rglob('*') 
            if f.is_file()
        )
        stats['documents_size_mb'] = total_docs_size / (1024 * 1024)
        
        conn.close()
        
        return stats

