"""
PDF Agent Memory System - Sistema de Memoria Avanzado
Basado en los frameworks: Memoria, PersonaMem-v2, y Forgetful but Faithful

Implementa:
- Memoria Semántica: Embeddings de documentos y triplets KG
- Memoria Episódica: Historial de conversaciones con resúmenes dinámicos
- Memoria Procedural: Preferencias de formato y tono
- Memoria de Metadatos: Fechas, versiones, autores
- Weighted Knowledge Graph: Triplets con exponential decay
- Session Summarization: Resúmenes dinámicos de sesión
"""

from __future__ import annotations

import json
import sqlite3
import time
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict
import math

try:
    import chromadb
    from chromadb.config import Settings
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False
    print("⚠️ ChromaDB no disponible. Instala con: pip install chromadb")

try:
    from langchain_openai import OpenAIEmbeddings
    from langchain_core.embeddings import Embeddings
    EMBEDDINGS_AVAILABLE = True
except ImportError:
    EMBEDDINGS_AVAILABLE = False
    print("⚠️ LangChain embeddings no disponible")


@dataclass
class MemoryTriplet:
    """Knowledge Graph Triplet (Subject, Predicate, Object)."""
    subject: str
    predicate: str
    object: str
    timestamp: str
    source_message: str
    weight: float = 1.0
    user_name: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> MemoryTriplet:
        return cls(**data)


@dataclass
class SessionSummary:
    """Resumen dinámico de una sesión."""
    session_id: str
    summary: str
    created_at: str
    updated_at: str
    conversation_count: int
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> SessionSummary:
        return cls(**data)


@dataclass
class UserPreference:
    """Preferencias del usuario (Memoria Procedural)."""
    preference_type: str  # "format", "tone", "style", etc.
    preference_value: str
    created_at: str
    updated_at: str
    usage_count: int = 0
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> UserPreference:
        return cls(**data)


class PDFAgentMemory:
    """
    Sistema de Memoria Avanzado para PDF Agent Mode.
    
    Basado en los frameworks:
    - Memoria: A Scalable Agentic Memory Framework
    - PersonaMem-v2: Implicit Personas
    - Forgetful but Faithful: MaRS framework
    
    Características:
    1. Memoria Semántica: Embeddings de documentos y triplets KG
    2. Memoria Episódica: Historial de conversaciones con resúmenes
    3. Memoria Procedural: Preferencias de formato y tono
    4. Memoria de Metadatos: Fechas, versiones, autores
    5. Weighted Knowledge Graph: Triplets con exponential decay
    6. Session Summarization: Resúmenes dinámicos de sesión
    """
    
    def __init__(
        self,
        memory_dir: Path,
        config: Any,
        llm: Optional[Any] = None,
        embedding_model: Optional[Any] = None
    ):
        """
        Inicializa el sistema de memoria.
        
        Args:
            memory_dir: Directorio para almacenar memoria
            config: Configuración de la aplicación
            llm: Modelo de lenguaje para resúmenes
            embedding_model: Modelo de embeddings
        """
        self.memory_dir = Path(memory_dir)
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        self.config = config
        self.llm = llm
        
        # Inicializar embedding model
        if embedding_model:
            self.embedding_model = embedding_model
        elif EMBEDDINGS_AVAILABLE and config.openai_api_key:
            try:
                self.embedding_model = OpenAIEmbeddings(
                    model=config.embedding_model or "text-embedding-3-small",
                    api_key=config.openai_api_key
                )
                print("✅ [PDF Agent Memory] Embedding model inicializado")
            except Exception as e:
                self.embedding_model = None
                print(f"⚠️ [PDF Agent Memory] Error inicializando embedding model: {e}")
        else:
            self.embedding_model = None
            print("⚠️ [PDF Agent Memory] Embedding model no disponible (falta OPENAI_API_KEY)")
        
        # Base de datos SQLite para memoria estructurada
        self.db_path = self.memory_dir / "pdf_agent_memory.db"
        self._init_database()
        
        # ChromaDB para embeddings de triplets
        self.chroma_client = None
        self.chroma_collection = None
        if CHROMADB_AVAILABLE:
            try:
                chroma_dir = self.memory_dir / "chroma_db"
                chroma_dir.mkdir(parents=True, exist_ok=True)
                self.chroma_client = chromadb.PersistentClient(
                    path=str(chroma_dir),
                    settings=Settings(anonymized_telemetry=False)
                )
                self.chroma_collection = self.chroma_client.get_or_create_collection(
                    name="pdf_agent_triplets",
                    metadata={"hnsw:space": "cosine"}
                )
                print("✅ [PDF Agent Memory] ChromaDB inicializado")
            except Exception as e:
                print(f"⚠️ [PDF Agent Memory] Error inicializando ChromaDB: {e}")
        
        # Parámetros de exponential decay
        self.decay_rate = 0.02  # α = 0.02 (del paper Memoria)
        self.top_k_triplets = 20  # K = 20 (del paper Memoria)
        
        # Cache de resúmenes de sesión
        self._session_summaries: Dict[str, SessionSummary] = {}
        self._load_session_summaries()
    
    def _init_database(self):
        """Inicializa la base de datos SQLite."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Tabla de conversaciones (Memoria Episódica)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                user_message TEXT NOT NULL,
                assistant_message TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                metadata TEXT
            )
        """)
        
        # Índices para conversaciones
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_session_timestamp 
            ON conversations(session_id, timestamp)
        """)
        
        # Tabla de triplets (Memoria Semántica - KG)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS triplets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject TEXT NOT NULL,
                predicate TEXT NOT NULL,
                object TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                source_message TEXT,
                user_name TEXT,
                weight REAL DEFAULT 1.0
            )
        """)
        
        # Índices para triplets
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_user_timestamp 
            ON triplets(user_name, timestamp)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_subject 
            ON triplets(subject)
        """)
        
        # Tabla de resúmenes de sesión
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS session_summaries (
                session_id TEXT PRIMARY KEY,
                summary TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                conversation_count INTEGER DEFAULT 0
            )
        """)
        
        # Tabla de preferencias del usuario (Memoria Procedural)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_preferences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_name TEXT,
                preference_type TEXT NOT NULL,
                preference_value TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                usage_count INTEGER DEFAULT 0,
                UNIQUE(user_name, preference_type)
            )
        """)
        
        # Índice para user_preferences
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_user_type 
            ON user_preferences(user_name, preference_type)
        """)
        
        # Tabla de metadatos de documentos
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS document_metadata (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_name TEXT NOT NULL,
                file_path TEXT,
                file_size INTEGER,
                created_at TEXT,
                modified_at TEXT,
                author TEXT,
                version TEXT,
                indexed_at TEXT NOT NULL,
                UNIQUE(file_name)
            )
        """)
        
        # Índice para document_metadata
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_file_name 
            ON document_metadata(file_name)
        """)
        
        conn.commit()
        conn.close()
        print("✅ [PDF Agent Memory] Base de datos SQLite inicializada")
    
    def add_conversation(
        self,
        session_id: str,
        user_message: str,
        assistant_message: str,
        metadata: Optional[Dict] = None
    ):
        """Agrega una conversación a la memoria episódica."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        timestamp = datetime.now().isoformat()
        metadata_json = json.dumps(metadata or {})
        
        cursor.execute("""
            INSERT INTO conversations (session_id, user_message, assistant_message, timestamp, metadata)
            VALUES (?, ?, ?, ?, ?)
        """, (session_id, user_message, assistant_message, timestamp, metadata_json))
        
        conn.commit()
        conn.close()
        
        # Actualizar resumen de sesión
        self._update_session_summary(session_id, user_message, assistant_message)
        
        # Extraer triplets del mensaje del usuario
        self._extract_and_store_triplets(user_message, session_id)
    
    def _extract_and_store_triplets(
        self,
        user_message: str,
        session_id: str,
        user_name: Optional[str] = None
    ):
        """
        Extrae triplets (Subject, Predicate, Object) del mensaje del usuario.
        Usa LLM para extracción si está disponible.
        """
        if not self.llm:
            return
        
        try:
            # Prompt para extraer triplets
            extraction_prompt = f"""Extrae triplets de conocimiento (Subject, Predicate, Object) del siguiente mensaje del usuario.
            
Mensaje: {user_message}

Formato de salida (JSON array):
[
    {{"subject": "...", "predicate": "...", "object": "..."}},
    ...
]

Solo extrae información factual y relevante. Si no hay información extraíble, retorna []."""

            response = self.llm.invoke(extraction_prompt)
            content = response.content if hasattr(response, 'content') else str(response)
            
            # Parsear JSON
            import re
            json_match = re.search(r'\[.*\]', content, re.DOTALL)
            if json_match:
                triplets_data = json.loads(json_match.group())
                
                timestamp = datetime.now().isoformat()
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                for triplet_data in triplets_data:
                    subject = triplet_data.get("subject", "").strip()
                    predicate = triplet_data.get("predicate", "").strip()
                    obj = triplet_data.get("object", "").strip()
                    
                    if subject and predicate and obj:
                        # Guardar en SQLite
                        cursor.execute("""
                            INSERT INTO triplets (subject, predicate, object, timestamp, source_message, user_name, weight)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        """, (subject, predicate, obj, timestamp, user_message, user_name, 1.0))
                        
                        # Guardar embedding en ChromaDB
                        if self.chroma_collection and self.embedding_model:
                            try:
                                triplet_text = f"{subject} {predicate} {obj}"
                                embedding = self.embedding_model.embed_query(triplet_text)
                                
                                triplet_id = f"{session_id}_{hashlib.md5(triplet_text.encode()).hexdigest()[:8]}"
                                
                                self.chroma_collection.add(
                                    ids=[triplet_id],
                                    embeddings=[embedding],
                                    metadatas=[{
                                        "subject": subject,
                                        "predicate": predicate,
                                        "object": obj,
                                        "timestamp": timestamp,
                                        "user_name": user_name or "",
                                        "source_message": user_message[:500]
                                    }],
                                    documents=[triplet_text]
                                )
                            except Exception as e:
                                print(f"⚠️ [PDF Agent Memory] Error guardando embedding: {e}")
                
                conn.commit()
                conn.close()
                
        except Exception as e:
            print(f"⚠️ [PDF Agent Memory] Error extrayendo triplets: {e}")
    
    def get_weighted_triplets(
        self,
        query: str,
        user_name: Optional[str] = None,
        top_k: Optional[int] = None
    ) -> List[Tuple[MemoryTriplet, float]]:
        """
        Recupera triplets relevantes con pesos basados en exponential decay.
        
        Basado en el paper Memoria:
        - Recupera top-K triplets por similitud semántica
        - Aplica exponential decay: w_i = e^(-α * x_i)
        - Normaliza pesos: w̃_i = w_i / Σw_j
        """
        k = top_k or self.top_k_triplets
        
        # 1. Recuperar triplets por similitud semántica (ChromaDB)
        relevant_triplets = []
        
        if self.chroma_collection and self.embedding_model:
            try:
                query_embedding = self.embedding_model.embed_query(query)
                
                # Filtrar por user_name si se proporciona
                where_clause = {"user_name": user_name} if user_name else None
                
                results = self.chroma_collection.query(
                    query_embeddings=[query_embedding],
                    n_results=k,
                    where=where_clause if where_clause else None
                )
                
                # Obtener triplets de la base de datos SQLite
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                current_time = datetime.now()
                
                for i, triplet_id in enumerate(results.get("ids", [])[0] if results.get("ids") else []):
                    # Obtener metadata del triplet
                    metadatas = results.get("metadatas", [[]])[0] if results.get("metadatas") else []
                    if i < len(metadatas):
                        metadata = metadatas[i]
                        subject = metadata.get("subject", "")
                        predicate = metadata.get("predicate", "")
                        obj = metadata.get("object", "")
                        timestamp_str = metadata.get("timestamp", "")
                        
                        if subject and predicate and obj and timestamp_str:
                            # Calcular peso con exponential decay
                            try:
                                triplet_time = datetime.fromisoformat(timestamp_str)
                                minutes_ago = (current_time - triplet_time).total_seconds() / 60.0
                                
                                # Normalizar minutos (0-1)
                                # Asumimos que el triplet más antiguo tiene 30 días
                                max_minutes = 30 * 24 * 60  # 30 días en minutos
                                x_normalized = min(minutes_ago / max_minutes, 1.0)
                                
                                # Exponential decay: w_i = e^(-α * x_i)
                                raw_weight = math.exp(-self.decay_rate * x_normalized)
                                
                                triplet = MemoryTriplet(
                                    subject=subject,
                                    predicate=predicate,
                                    object=obj,
                                    timestamp=timestamp_str,
                                    source_message=metadata.get("source_message", ""),
                                    weight=raw_weight,
                                    user_name=metadata.get("user_name")
                                )
                                
                                relevant_triplets.append((triplet, raw_weight))
                            except Exception as e:
                                print(f"⚠️ [PDF Agent Memory] Error procesando triplet: {e}")
                                continue
                
                conn.close()
            except Exception as e:
                print(f"⚠️ [PDF Agent Memory] Error recuperando triplets: {e}")
        
        # Si no hay triplets de ChromaDB, buscar en SQLite directamente
        if not relevant_triplets:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            current_time = datetime.now()
            
            # Buscar triplets recientes
            query_params = []
            sql = "SELECT subject, predicate, object, timestamp, source_message, user_name FROM triplets WHERE 1=1"
            
            if user_name:
                sql += " AND user_name = ?"
                query_params.append(user_name)
            
            sql += " ORDER BY timestamp DESC LIMIT ?"
            query_params.append(k)
            
            cursor.execute(sql, query_params)
            rows = cursor.fetchall()
            
            for row in rows:
                subject, predicate, obj, timestamp_str, source_message, user_name_val = row
                
                try:
                    triplet_time = datetime.fromisoformat(timestamp_str)
                    minutes_ago = (current_time - triplet_time).total_seconds() / 60.0
                    
                    # Normalizar y calcular peso
                    max_minutes = 30 * 24 * 60
                    x_normalized = min(minutes_ago / max_minutes, 1.0)
                    raw_weight = math.exp(-self.decay_rate * x_normalized)
                    
                    triplet = MemoryTriplet(
                        subject=subject,
                        predicate=predicate,
                        object=obj,
                        timestamp=timestamp_str,
                        source_message=source_message or "",
                        weight=raw_weight,
                        user_name=user_name_val
                    )
                    
                    relevant_triplets.append((triplet, raw_weight))
                except Exception as e:
                    continue
            
            conn.close()
        
        # Normalizar pesos: w̃_i = w_i / Σw_j
        if relevant_triplets:
            total_weight = sum(weight for _, weight in relevant_triplets)
            if total_weight > 0:
                normalized_triplets = [
                    (triplet, weight / total_weight)
                    for triplet, weight in relevant_triplets
                ]
                return normalized_triplets
        
        return []
    
    def _update_session_summary(
        self,
        session_id: str,
        user_message: str,
        assistant_message: str
    ):
        """
        Actualiza el resumen de sesión usando LLM.
        Basado en el paper Memoria: Session Level Memory for Real Time Context
        """
        if not self.llm:
            return
        
        try:
            # Obtener resumen existente
            existing_summary = self._session_summaries.get(session_id)
            
            # Obtener conversaciones recientes
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT user_message, assistant_message 
                FROM conversations 
                WHERE session_id = ? 
                ORDER BY timestamp DESC 
                LIMIT 10
            """, (session_id,))
            recent_conversations = cursor.fetchall()
            conn.close()
            
            # Construir prompt para resumen
            if existing_summary:
                # Actualizar resumen existente
                summary_prompt = f"""Actualiza el siguiente resumen de conversación con los nuevos mensajes.

RESUMEN ACTUAL:
{existing_summary.summary}

NUEVOS MENSAJES:
Usuario: {user_message}
Asistente: {assistant_message}

Genera un resumen actualizado que capture:
1. Los puntos principales de la conversación
2. Preferencias del usuario mencionadas
3. Información importante discutida
4. Contexto relevante para futuras interacciones

Resumen actualizado (máximo 300 palabras):"""
            else:
                # Crear nuevo resumen
                conversation_text = "\n".join([
                    f"Usuario: {user_msg}\nAsistente: {assistant_msg}\n"
                    for user_msg, assistant_msg in reversed(recent_conversations)
                ])
                
                summary_prompt = f"""Crea un resumen de la siguiente conversación.

CONVERSACIÓN:
{conversation_text}

Genera un resumen que capture:
1. Los puntos principales de la conversación
2. Preferencias del usuario mencionadas
3. Información importante discutida
4. Contexto relevante para futuras interacciones

Resumen (máximo 300 palabras):"""
            
            # Generar resumen con LLM
            try:
                response = self.llm.invoke(summary_prompt)
                new_summary = response.content if hasattr(response, 'content') else str(response)
                # Limpiar el resumen (remover markdown si existe)
                new_summary = new_summary.strip()
                if new_summary.startswith("```"):
                    # Remover code blocks
                    lines = new_summary.split("\n")
                    new_summary = "\n".join([l for l in lines if not l.strip().startswith("```")])
            except Exception as e:
                print(f"⚠️ [PDF Agent Memory] Error generando resumen: {e}")
                # Fallback: crear resumen simple
                new_summary = f"Resumen de conversación con {len(recent_conversations)} mensajes. Tema principal: {user_message[:100]}..."
            
            # Guardar resumen
            now = datetime.now().isoformat()
            
            if existing_summary:
                summary = SessionSummary(
                    session_id=session_id,
                    summary=new_summary,
                    created_at=existing_summary.created_at,
                    updated_at=now,
                    conversation_count=existing_summary.conversation_count + 1
                )
            else:
                summary = SessionSummary(
                    session_id=session_id,
                    summary=new_summary,
                    created_at=now,
                    updated_at=now,
                    conversation_count=len(recent_conversations)
                )
            
            self._session_summaries[session_id] = summary
            self._save_session_summary(summary)
            
        except Exception as e:
            print(f"⚠️ [PDF Agent Memory] Error actualizando resumen de sesión: {e}")
    
    def get_session_summary(self, session_id: str) -> Optional[str]:
        """Obtiene el resumen de sesión."""
        summary = self._session_summaries.get(session_id)
        if summary:
            return summary.summary
        
        # Intentar cargar de la base de datos
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT summary FROM session_summaries WHERE session_id = ?
        """, (session_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return row[0]
        
        return None
    
    def _save_session_summary(self, summary: SessionSummary):
        """Guarda el resumen de sesión en la base de datos."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO session_summaries 
            (session_id, summary, created_at, updated_at, conversation_count)
            VALUES (?, ?, ?, ?, ?)
        """, (
            summary.session_id,
            summary.summary,
            summary.created_at,
            summary.updated_at,
            summary.conversation_count
        ))
        
        conn.commit()
        conn.close()
    
    def _load_session_summaries(self):
        """Carga resúmenes de sesión de la base de datos."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM session_summaries")
        rows = cursor.fetchall()
        
        for row in rows:
            session_id, summary, created_at, updated_at, conversation_count = row
            self._session_summaries[session_id] = SessionSummary(
                session_id=session_id,
                summary=summary,
                created_at=created_at,
                updated_at=updated_at,
                conversation_count=conversation_count
            )
        
        conn.close()
    
    def add_user_preference(
        self,
        preference_type: str,
        preference_value: str,
        user_name: Optional[str] = None
    ):
        """
        Agrega o actualiza una preferencia del usuario (Memoria Procedural).
        
        Tipos de preferencias:
        - "format": Formato de respuesta (tabla, lista, párrafo, etc.)
        - "tone": Tono de respuesta (formal, casual, técnico, etc.)
        - "style": Estilo de respuesta (breve, detallado, etc.)
        - "language": Idioma preferido
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        now = datetime.now().isoformat()
        
        # Verificar si existe
        cursor.execute("""
            SELECT id, usage_count FROM user_preferences 
            WHERE user_name = ? AND preference_type = ?
        """, (user_name, preference_type))
        existing = cursor.fetchone()
        
        if existing:
            # Actualizar existente
            pref_id, usage_count = existing
            cursor.execute("""
                UPDATE user_preferences 
                SET preference_value = ?, updated_at = ?, usage_count = usage_count + 1
                WHERE id = ?
            """, (preference_value, now, pref_id))
        else:
            # Crear nuevo
            cursor.execute("""
                INSERT INTO user_preferences 
                (user_name, preference_type, preference_value, created_at, updated_at, usage_count)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (user_name, preference_type, preference_value, now, now, 1))
        
        conn.commit()
        conn.close()
    
    def get_user_preferences(
        self,
        user_name: Optional[str] = None
    ) -> Dict[str, str]:
        """Obtiene las preferencias del usuario."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if user_name:
            cursor.execute("""
                SELECT preference_type, preference_value 
                FROM user_preferences 
                WHERE user_name = ?
                ORDER BY usage_count DESC
            """, (user_name,))
        else:
            cursor.execute("""
                SELECT preference_type, preference_value 
                FROM user_preferences 
                WHERE user_name IS NULL
                ORDER BY usage_count DESC
            """)
        
        rows = cursor.fetchall()
        conn.close()
        
        preferences = {pref_type: pref_value for pref_type, pref_value in rows}
        return preferences
    
    def add_document_metadata(
        self,
        file_name: str,
        file_path: Optional[str] = None,
        file_size: Optional[int] = None,
        author: Optional[str] = None,
        version: Optional[str] = None
    ):
        """Agrega metadatos de un documento."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        now = datetime.now().isoformat()
        
        # Obtener información del archivo si existe
        if file_path and Path(file_path).exists():
            stat = Path(file_path).stat()
            created_at = datetime.fromtimestamp(stat.st_ctime).isoformat()
            modified_at = datetime.fromtimestamp(stat.st_mtime).isoformat()
            if not file_size:
                file_size = stat.st_size
        else:
            created_at = now
            modified_at = now
        
        cursor.execute("""
            INSERT OR REPLACE INTO document_metadata 
            (file_name, file_path, file_size, created_at, modified_at, author, version, indexed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (file_name, file_path, file_size, created_at, modified_at, author, version, now))
        
        conn.commit()
        conn.close()
    
    def get_document_metadata(self, file_name: str) -> Optional[Dict[str, Any]]:
        """Obtiene metadatos de un documento."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT file_name, file_path, file_size, created_at, modified_at, author, version, indexed_at
            FROM document_metadata 
            WHERE file_name = ?
        """, (file_name,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                "file_name": row[0],
                "file_path": row[1],
                "file_size": row[2],
                "created_at": row[3],
                "modified_at": row[4],
                "author": row[5],
                "version": row[6],
                "indexed_at": row[7]
            }
        
        return None
    
    def get_memory_context(
        self,
        query: str,
        session_id: str,
        user_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Obtiene contexto completo de memoria para una consulta.
        
        Combina:
        - Resumen de sesión (Memoria Episódica)
        - Triplets relevantes con pesos (Memoria Semántica)
        - Preferencias del usuario (Memoria Procedural)
        """
        context = {
            "session_summary": None,
            "weighted_triplets": [],
            "user_preferences": {},
            "relevant_conversations": []
        }
        
        # 1. Resumen de sesión
        session_summary = self.get_session_summary(session_id)
        if session_summary:
            context["session_summary"] = session_summary
        
        # 2. Triplets relevantes con pesos
        weighted_triplets = self.get_weighted_triplets(query, user_name=user_name)
        context["weighted_triplets"] = [
            {
                "triplet": triplet.to_dict(),
                "normalized_weight": weight
            }
            for triplet, weight in weighted_triplets
        ]
        
        # 3. Preferencias del usuario
        user_preferences = self.get_user_preferences(user_name=user_name)
        context["user_preferences"] = user_preferences
        
        # 4. Conversaciones relevantes recientes
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT user_message, assistant_message, timestamp
            FROM conversations
            WHERE session_id = ?
            ORDER BY timestamp DESC
            LIMIT 5
        """, (session_id,))
        recent_conversations = cursor.fetchall()
        conn.close()
        
        context["relevant_conversations"] = [
            {
                "user_message": user_msg,
                "assistant_message": assistant_msg,
                "timestamp": timestamp
            }
            for user_msg, assistant_msg, timestamp in recent_conversations
        ]
        
        return context
    
    def format_memory_context_for_prompt(
        self,
        memory_context: Dict[str, Any]
    ) -> str:
        """
        Formatea el contexto de memoria para incluir en el prompt del LLM.
        """
        formatted_parts = []
        
        # Resumen de sesión
        if memory_context.get("session_summary"):
            formatted_parts.append("## 📝 Resumen de Sesión Anterior")
            formatted_parts.append(memory_context["session_summary"])
            formatted_parts.append("")
        
        # Triplets relevantes (solo los más importantes)
        weighted_triplets = memory_context.get("weighted_triplets", [])
        if weighted_triplets:
            formatted_parts.append("## 🧠 Conocimiento Relevante del Usuario")
            # Mostrar solo los top 5 triplets más importantes
            top_triplets = sorted(
                weighted_triplets,
                key=lambda x: x["normalized_weight"],
                reverse=True
            )[:5]
            
            for item in top_triplets:
                triplet = item["triplet"]
                weight = item["normalized_weight"]
                formatted_parts.append(
                    f"- {triplet['subject']} {triplet['predicate']} {triplet['object']} "
                    f"(relevancia: {weight:.2%})"
                )
            formatted_parts.append("")
        
        # Preferencias del usuario
        user_preferences = memory_context.get("user_preferences", {})
        if user_preferences:
            formatted_parts.append("## ⚙️ Preferencias del Usuario")
            for pref_type, pref_value in user_preferences.items():
                formatted_parts.append(f"- **{pref_type}**: {pref_value}")
            formatted_parts.append("")
        
        return "\n".join(formatted_parts)
    
    def cleanup_old_memories(self, days: int = 90):
        """
        Limpia memorias antiguas (Forgetful but Faithful).
        
        Args:
            days: Días de retención (por defecto 90 días)
        """
        cutoff_date = datetime.now() - timedelta(days=days)
        cutoff_str = cutoff_date.isoformat()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Limpiar conversaciones antiguas
        cursor.execute("DELETE FROM conversations WHERE timestamp < ?", (cutoff_str,))
        conversations_deleted = cursor.rowcount
        
        # Limpiar triplets antiguos (mantener los más importantes)
        # Primero, obtener triplets antiguos con bajo peso
        cursor.execute("""
            SELECT id FROM triplets 
            WHERE timestamp < ? AND weight < 0.1
        """, (cutoff_str,))
        old_triplet_ids = [row[0] for row in cursor.fetchall()]
        
        if old_triplet_ids:
            placeholders = ','.join(['?'] * len(old_triplet_ids))
            cursor.execute(f"DELETE FROM triplets WHERE id IN ({placeholders})", old_triplet_ids)
            triplets_deleted = cursor.rowcount
        else:
            triplets_deleted = 0
        
        # Limpiar resúmenes de sesiones sin conversaciones recientes
        cursor.execute("""
            DELETE FROM session_summaries 
            WHERE session_id NOT IN (
                SELECT DISTINCT session_id FROM conversations 
                WHERE timestamp > ?
            )
        """, (cutoff_str,))
        summaries_deleted = cursor.rowcount
        
        conn.commit()
        conn.close()
        
        print(f"✅ [PDF Agent Memory] Limpieza completada: {conversations_deleted} conversaciones, {triplets_deleted} triplets, {summaries_deleted} resúmenes eliminados")
        
        return {
            "conversations_deleted": conversations_deleted,
            "triplets_deleted": triplets_deleted,
            "summaries_deleted": summaries_deleted
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """Obtiene estadísticas del sistema de memoria."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Contar conversaciones
        cursor.execute("SELECT COUNT(*) FROM conversations")
        conversation_count = cursor.fetchone()[0]
        
        # Contar triplets
        cursor.execute("SELECT COUNT(*) FROM triplets")
        triplet_count = cursor.fetchone()[0]
        
        # Contar sesiones
        cursor.execute("SELECT COUNT(*) FROM session_summaries")
        session_count = cursor.fetchone()[0]
        
        # Contar preferencias
        cursor.execute("SELECT COUNT(*) FROM user_preferences")
        preference_count = cursor.fetchone()[0]
        
        # Contar documentos
        cursor.execute("SELECT COUNT(*) FROM document_metadata")
        document_count = cursor.fetchone()[0]
        
        conn.close()
        
        # Estadísticas de ChromaDB
        chroma_stats = {}
        if self.chroma_collection:
            try:
                chroma_stats = {
                    "triplet_embeddings": self.chroma_collection.count()
                }
            except:
                chroma_stats = {"triplet_embeddings": 0}
        
        return {
            "conversations": conversation_count,
            "triplets": triplet_count,
            "sessions": session_count,
            "user_preferences": preference_count,
            "documents": document_count,
            "chromadb": chroma_stats,
            "decay_rate": self.decay_rate,
            "top_k_triplets": self.top_k_triplets
        }



































