"""
Data Provenance - Procedencia de datos
Rastrea el origen de cada información para compliance y confianza
Crítico para empresas con 500+ PDFs
"""

from __future__ import annotations

import json
import time
import hashlib
import uuid
from typing import List, Dict, Optional, Any, Set
from dataclasses import dataclass, field, asdict
from pathlib import Path
from enum import Enum

from langchain_core.documents import Document

from .config import AppConfig


class DataSourceType(str, Enum):
    """Tipo de fuente de datos."""
    DOCUMENT = "document"
    CHUNK = "chunk"
    QUERY = "query"
    RESPONSE = "response"
    EXTERNAL_API = "external_api"
    DATABASE = "database"
    CALCULATION = "calculation"


@dataclass
class DataProvenance:
    """Información de procedencia de un dato."""
    provenance_id: str
    data_hash: str  # Hash del dato para verificación
    source_type: DataSourceType
    source_id: str  # ID de la fuente
    source_name: str  # Nombre legible de la fuente
    source_path: Optional[str] = None  # Ruta del archivo
    chunk_id: Optional[str] = None  # ID del chunk si aplica
    page_number: Optional[int] = None  # Número de página si aplica
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0  # Confianza en la procedencia
    lineage: List[str] = field(default_factory=list)  # Linaje del dato (transformaciones)


@dataclass
class ProvenanceRecord:
    """Registro completo de procedencia."""
    record_id: str
    query: str  # Consulta original
    response: str  # Respuesta generada
    sources: List[DataProvenance]  # Fuentes usadas
    processing_steps: List[Dict[str, Any]] = field(default_factory=list)  # Pasos de procesamiento
    timestamp: float = field(default_factory=time.time)
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class DataProvenanceTracker:
    """
    Sistema de rastreo de procedencia de datos.
    
    Características:
    - Rastrea el origen de cada información
    - Mantiene linaje completo de transformaciones
    - Permite verificación de fuentes
    - Crítico para compliance y auditoría
    - Previene datos alterados
    """
    
    def __init__(self, config: AppConfig):
        self.config = config
        
        # Registros de procedencia
        self.provenance_records: Dict[str, ProvenanceRecord] = {}
        
        # Índice de datos por hash
        self.data_index: Dict[str, List[str]] = {}  # hash -> [record_ids]
        
        # Índice de fuentes
        self.source_index: Dict[str, List[str]] = {}  # source_id -> [record_ids]
        
        # Directorio para persistencia
        self.storage_dir = Path(config.memory_dir) / "data_provenance"
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        # Cargar registros existentes
        self._load_records()
    
    def _load_records(self):
        """Carga registros de procedencia guardados."""
        records_file = self.storage_dir / "provenance_records.json"
        if records_file.exists():
            try:
                with open(records_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for record_data in data.get("records", [])[-1000:]:  # Últimos 1000
                        record = ProvenanceRecord(**record_data)
                        # Reconstruir sources
                        record.sources = [
                            DataProvenance(**s_data) for s_data in record_data.get("sources", [])
                        ]
                        self.provenance_records[record.record_id] = record
                        
                        # Reconstruir índices
                        self._index_record(record)
                    
                    print(f"✅ [Data Provenance] {len(self.provenance_records)} registros cargados")
            except Exception as e:
                print(f"⚠️ [Data Provenance] Error cargando registros: {e}")
    
    def _save_records(self):
        """Guarda registros de procedencia."""
        records_file = self.storage_dir / "provenance_records.json"
        try:
            with open(records_file, "w", encoding="utf-8") as f:
                json.dump({
                    "records": [
                        {
                            **asdict(record),
                            "sources": [asdict(s) for s in record.sources]
                        }
                        for record in self.provenance_records.values()
                    ]
                }, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"⚠️ [Data Provenance] Error guardando registros: {e}")
    
    def _index_record(self, record: ProvenanceRecord):
        """Indexa un registro para búsqueda rápida."""
        # Indexar por hash de datos
        for source in record.sources:
            if source.data_hash not in self.data_index:
                self.data_index[source.data_hash] = []
            if record.record_id not in self.data_index[source.data_hash]:
                self.data_index[source.data_hash].append(record.record_id)
            
            # Indexar por fuente
            if source.source_id not in self.source_index:
                self.source_index[source.source_id] = []
            if record.record_id not in self.source_index[source.source_id]:
                self.source_index[source.source_id].append(record.record_id)
    
    def _hash_data(self, data: str) -> str:
        """Genera hash de un dato."""
        return hashlib.sha256(data.encode('utf-8')).hexdigest()
    
    def track_document_source(
        self,
        document: Document,
        chunk_id: Optional[str] = None
    ) -> DataProvenance:
        """
        Rastrea un documento como fuente.
        
        Returns:
            DataProvenance del documento
        """
        source_name = document.metadata.get("source", "Unknown")
        source_path = document.metadata.get("source", "")
        
        # Extraer número de página si está disponible
        page_number = document.metadata.get("page", None)
        if page_number is None:
            page_number = document.metadata.get("page_number", None)
        
        # Generar hash del contenido
        content = document.page_content
        data_hash = self._hash_data(content)
        
        provenance = DataProvenance(
            provenance_id=str(uuid.uuid4()),
            data_hash=data_hash,
            source_type=DataSourceType.DOCUMENT,
            source_id=source_path,
            source_name=Path(source_name).name if source_name else "Unknown",
            source_path=source_path,
            chunk_id=chunk_id,
            page_number=page_number,
            metadata=document.metadata.copy()
        )
        
        return provenance
    
    def track_query_response(
        self,
        query: str,
        response: str,
        sources: List[DataProvenance],
        processing_steps: Optional[List[Dict[str, Any]]] = None,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Rastrea una consulta y su respuesta con todas sus fuentes.
        
        Returns:
            record_id: ID del registro creado
        """
        record_id = str(uuid.uuid4())
        
        record = ProvenanceRecord(
            record_id=record_id,
            query=query,
            response=response,
            sources=sources,
            processing_steps=processing_steps or [],
            session_id=session_id,
            user_id=user_id,
            metadata=metadata or {}
        )
        
        self.provenance_records[record_id] = record
        self._index_record(record)
        
        # Guardar periódicamente (cada 10 registros)
        if len(self.provenance_records) % 10 == 0:
            self._save_records()
        
        return record_id
    
    def get_provenance(self, record_id: str) -> Optional[ProvenanceRecord]:
        """Obtiene el registro de procedencia por ID."""
        return self.provenance_records.get(record_id)
    
    def find_by_source(self, source_id: str) -> List[ProvenanceRecord]:
        """Encuentra todos los registros que usaron una fuente específica."""
        record_ids = self.source_index.get(source_id, [])
        return [
            self.provenance_records[rid]
            for rid in record_ids
            if rid in self.provenance_records
        ]
    
    def find_by_data_hash(self, data_hash: str) -> List[ProvenanceRecord]:
        """Encuentra todos los registros que usaron un dato específico."""
        record_ids = self.data_index.get(data_hash, [])
        return [
            self.provenance_records[rid]
            for rid in record_ids
            if rid in self.provenance_records
        ]
    
    def verify_source_integrity(self, source_id: str) -> Dict[str, Any]:
        """
        Verifica la integridad de una fuente.
        
        Returns:
            Dict con información de verificación
        """
        records = self.find_by_source(source_id)
        
        if not records:
            return {
                "source_id": source_id,
                "verified": False,
                "error": "Fuente no encontrada en registros"
            }
        
        # Verificar que todos los hashes sean consistentes
        hashes = set()
        for record in records:
            for source in record.sources:
                if source.source_id == source_id:
                    hashes.add(source.data_hash)
        
        # Si hay múltiples hashes diferentes, puede indicar alteración
        hash_count = len(hashes)
        
        return {
            "source_id": source_id,
            "verified": hash_count <= 1,  # Un solo hash = consistente
            "hash_count": hash_count,
            "unique_hashes": list(hashes),
            "usage_count": len(records),
            "warning": "Múltiples hashes detectados" if hash_count > 1 else None
        }
    
    def get_source_lineage(self, source_id: str) -> List[Dict[str, Any]]:
        """
        Obtiene el linaje completo de una fuente (cómo se usó y transformó).
        
        Returns:
            Lista de transformaciones y usos
        """
        records = self.find_by_source(source_id)
        
        lineage = []
        for record in records:
            lineage.append({
                "record_id": record.record_id,
                "query": record.query,
                "timestamp": record.timestamp,
                "processing_steps": record.processing_steps,
                "transformed_to": record.response[:200] if record.response else None
            })
        
        return sorted(lineage, key=lambda x: x["timestamp"])
    
    def format_provenance_report(
        self,
        record_id: str,
        include_content: bool = False
    ) -> str:
        """
        Formatea un reporte de procedencia legible.
        
        Returns:
            Reporte formateado
        """
        record = self.get_provenance(record_id)
        if not record:
            return f"Registro {record_id} no encontrado"
        
        report = f"📋 REPORTE DE PROCEDENCIA\n"
        report += f"{'='*60}\n\n"
        report += f"ID del Registro: {record_id}\n"
        report += f"Consulta: {record.query}\n"
        report += f"Fecha: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(record.timestamp))}\n\n"
        
        report += f"📚 FUENTES ({len(record.sources)}):\n"
        report += f"{'-'*60}\n"
        
        for i, source in enumerate(record.sources, 1):
            report += f"\n{i}. {source.source_name}\n"
            report += f"   Tipo: {source.source_type.value}\n"
            if source.source_path:
                report += f"   Ruta: {source.source_path}\n"
            if source.page_number:
                report += f"   Página: {source.page_number}\n"
            if source.chunk_id:
                report += f"   Chunk ID: {source.chunk_id}\n"
            report += f"   Hash: {source.data_hash[:16]}...\n"
            report += f"   Confianza: {source.confidence*100:.1f}%\n"
            
            if include_content and source.metadata:
                report += f"   Metadatos: {json.dumps(source.metadata, indent=2)}\n"
        
        if record.processing_steps:
            report += f"\n\n⚙️ PASOS DE PROCESAMIENTO:\n"
            report += f"{'-'*60}\n"
            for i, step in enumerate(record.processing_steps, 1):
                report += f"{i}. {step.get('step', 'Unknown')}\n"
                if step.get('details'):
                    report += f"   {step['details']}\n"
        
        return report
    
    def get_statistics(self) -> Dict[str, Any]:
        """Obtiene estadísticas de procedencia."""
        unique_sources = len(self.source_index)
        total_records = len(self.provenance_records)
        
        # Contar por tipo de fuente
        source_types = {}
        for record in self.provenance_records.values():
            for source in record.sources:
                source_type = source.source_type.value
                source_types[source_type] = source_types.get(source_type, 0) + 1
        
        return {
            "total_records": total_records,
            "unique_sources": unique_sources,
            "source_types": source_types,
            "indexed_data_hashes": len(self.data_index),
            "average_sources_per_record": (
                sum(len(r.sources) for r in self.provenance_records.values()) / total_records
                if total_records > 0 else 0
            )
        }

