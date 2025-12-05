"""Data Ingestion Engine para DocChat Enterprise.

Responsable de:
- Ingesta batch y streaming
- Parsing y normalización
- Extracción de texto (PDF/OCR, Office, HTML, etc.)
- Enriquecimiento de metadatos
- Chunking semántico
- Generación de embeddings
- Construcción de grafos (Graph Builder)
- Publicación en Vector Store y Graph Store
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
import os
from pathlib import Path

from .semantic_data_engine import SemanticDataEngine, SemanticDocument, DataModality
from .research_action_agent.graphrag_engine import GraphRAGEngine
from .utils import sha256_bytes


@dataclass
class IngestionConfig:
    base_path: Path


class DataPipelineMonitor:
    """Monitorea ingestiones, errores y métricas básicas."""

    def __init__(self):
        self.events: List[Dict[str, Any]] = []

    def record(self, event: Dict[str, Any]) -> None:
        self.events.append(event)
        if len(self.events) > 1000:
            self.events = self.events[-1000:]


class DataIngestionEngine:
    """Motor de ingesta de datos empresarial."""

    def __init__(self, semantic_engine: SemanticDataEngine, graph_engine: Optional[GraphRAGEngine] = None):
        self.semantic_engine = semantic_engine
        self.graph_engine = graph_engine or GraphRAGEngine()
        self.config = IngestionConfig(base_path=semantic_engine.config.base_path)
        self.monitor = DataPipelineMonitor()

    # ------------------------------------------------------------------
    # Rails de ingestión
    # ------------------------------------------------------------------

    def ingest_file(self, path: str, metadata: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """Ingesta manual de un archivo individual."""
        file_path = Path(path)
        if not file_path.exists():
            self.monitor.record({"event": "ingest_file_not_found", "path": path})
            return None
        try:
            content = file_path.read_bytes()
            parsed = self.parse_document(content, file_path.suffix.lower(), metadata or {})
            doc = self._embed_and_store(parsed["text"], str(file_path), parsed["metadata"])
            self._push_to_graphstore(doc, parsed)
            self.monitor.record({"event": "ingest_file_ok", "path": path, "doc_id": doc.doc_id})
            return doc.doc_id
        except Exception as e:
            self.monitor.record({"event": "ingest_file_error", "path": path, "error": str(e)})
            return None

    def ingest_folder(self, folder: str, recursive: bool = True) -> List[str]:
        """Ingesta completa de una carpeta."""
        base = Path(folder)
        if not base.exists():
            self.monitor.record({"event": "ingest_folder_not_found", "path": folder})
            return []
        doc_ids: List[str] = []
        pattern = "**/*" if recursive else "*"
        for fp in base.glob(pattern):
            if fp.is_file():
                doc_id = self.ingest_file(str(fp))
                if doc_id:
                    doc_ids.append(doc_id)
        return doc_ids

    def ingest_files_from_gradio(self, files: List[Any]) -> List[str]:
        """Convenience: ingesta de archivos tal como los entrega Gradio (con atributo .name)."""
        doc_ids: List[str] = []
        for f in files or []:
            try:
                path = getattr(f, "name", None)
                if not path:
                    continue
                doc_id = self.ingest_file(path)
                if doc_id:
                    doc_ids.append(doc_id)
            except Exception as e:
                self.monitor.record({"event": "ingest_gradio_error", "path": getattr(f, "name", ""), "error": str(e)})
        return doc_ids

    def ingest_api_source(self, source_name: str, config: Dict[str, Any]) -> List[str]:
        """Stub de ingestión desde APIs externas (Confluence, Jira, ServiceNow, etc.)."""
        # En producción, aquí se llamarían a las APIs y se crearía contenido normalizado
        self.monitor.record({"event": "ingest_api_source_stub", "source": source_name, "config": config})
        return []

    # ------------------------------------------------------------------
    # Parsing y normalización
    # ------------------------------------------------------------------

    def parse_document(self, raw_bytes: bytes, extension: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Parsing universal simplificado.

        Importante: para PDFs usamos el DocumentProcessor interno que NO fuerza OCR,
        solo extracción de texto nativo (PyPDF2). Para otros formatos usamos
        MultiFormatProcessor (Docling) con soporte amplio.
        """
        suffix = (extension or "").lower()
        file_name = f"uploaded{suffix or '.dat'}"
        file_hash = sha256_bytes(raw_bytes)

        # PDFs → usar pipeline rápido sin OCR (DocumentProcessor)
        if suffix == ".pdf":
            from .document_processor import DocumentProcessor

            dp = DocumentProcessor(self.semantic_engine.config)
            chunks = dp._process_pdf_with_fallback(raw_bytes, file_name, file_hash)  # type: ignore[attr-defined]
        else:
            from .multi_format_processor import MultiFormatProcessor

            processor = MultiFormatProcessor(self.semantic_engine.config)
            chunks = processor._process_file(raw_bytes, file_name, file_hash, suffix)  # type: ignore[attr-defined]

        # Concatenar contenido de chunks como texto base
        text_parts = [getattr(doc, "page_content", "") for doc in (chunks or [])]
        text = "\n\n".join(t for t in text_parts if t)

        # Metadatos básicos
        meta = dict(metadata)
        meta.setdefault("source_name", file_name)
        meta.setdefault("size_bytes", len(raw_bytes))

        return {"text": text, "metadata": meta}

    # ------------------------------------------------------------------
    # Vector Store & Graph Store
    # ------------------------------------------------------------------

    def _embed_and_store(self, text: str, source_path: str, metadata: Dict[str, Any]) -> SemanticDocument:
        """Genera embedding y almacena en SemanticDataEngine."""
        doc = self.semantic_engine.embed_document(
            content=text,
            source_path=source_path,
            modality=DataModality.TEXT,
            metadata=metadata,
        )
        # Guardar vector store/metadata
        self.semantic_engine._save_data()
        self.semantic_engine._save_vector_store()
        return doc

    def _push_to_graphstore(self, doc: SemanticDocument, parsed: Dict[str, Any]) -> None:
        """Stub de Graph Builder -> Graph Store."""
        # En producción, aquí se parsearía el texto a un grafo enriquecido.
        # Para ahora, sólo registramos el evento.
        self.monitor.record(
            {
                "event": "graph_builder_stub",
                "doc_id": doc.doc_id,
                "source_path": doc.source_path,
            }
        )


__all__ = ["DataIngestionEngine", "DataPipelineMonitor", "IngestionConfig"]


