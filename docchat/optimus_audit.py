"""
Optimus Audit Logging - Compliance / Governance / Audit para Optimus Prime Mode.

Objetivo:
- Log estructurado de todas las acciones importantes realizadas por Optimus:
  - user_id, tenant_id, session_id
  - document_id, acción (view/query/export/download/ingest)
  - timestamp
  - query
  - respuesta_generada (opcional, puede ser parcial o resumida)
  - referencias exactas (PDF, página, párrafo) serializadas como JSON
  - metadatos adicionales (JSON)

Diseño:
- Implementado sobre SQLite usando sqlite3 estándar (sin nuevas dependencias).
- Base de datos ubicada en: config.audit_log_dir / "optimus_audit.db"
- Pensado solo para Optimus Prime Mode (no toca el core de procesamiento de PDFs).
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class AuditReference:
    """Referencia a una fuente específica dentro de un PDF."""

    document_id: str
    source_name: str
    page_number: Optional[int] = None
    paragraph: Optional[str] = None


class OptimusAuditLogger:
    """
    Logger de auditoría para Optimus Prime.

    Características:
    - Log de eventos estructurados (acciones sobre documentos y consultas).
    - Exportación sencilla a listas de dicts (para CSV / reportes).
    """

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_schema()

    # ----------------- Infra interna -----------------

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_schema(self) -> None:
        conn = self._get_conn()
        cur = conn.cursor()

        # Tabla principal de eventos de auditoría
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS optimus_audit_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tenant_id TEXT,
                user_id TEXT,
                session_id TEXT,
                document_id TEXT,
                action TEXT,
                timestamp TEXT,
                query TEXT,
                response TEXT,
                sources_json TEXT,
                metadata_json TEXT
            )
            """
        )

        # Índices útiles para filtros típicos enterprise
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_optimus_audit_tenant ON optimus_audit_events(tenant_id)"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_optimus_audit_user ON optimus_audit_events(user_id)"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_optimus_audit_document ON optimus_audit_events(document_id)"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_optimus_audit_timestamp ON optimus_audit_events(timestamp)"
        )

        conn.commit()
        conn.close()

    # ----------------- API pública -----------------

    def log_event(
        self,
        tenant_id: str,
        user_id: str,
        session_id: str,
        action: str,
        document_id: Optional[str] = None,
        query: Optional[str] = None,
        response: Optional[str] = None,
        sources: Optional[List[AuditReference]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Registra un evento genérico de auditoría.
        """
        conn = self._get_conn()
        cur = conn.cursor()

        # Serializar referencias y metadatos
        sources_payload: List[Dict[str, Any]] = []
        if sources:
            for ref in sources:
                sources_payload.append(
                    {
                        "document_id": ref.document_id,
                        "source_name": ref.source_name,
                        "page_number": ref.page_number,
                        "paragraph": ref.paragraph,
                    }
                )

        cur.execute(
            """
            INSERT INTO optimus_audit_events (
                tenant_id,
                user_id,
                session_id,
                document_id,
                action,
                timestamp,
                query,
                response,
                sources_json,
                metadata_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                tenant_id,
                user_id,
                session_id,
                document_id or "",
                action,
                datetime.utcnow().isoformat(),
                query or "",
                response or "",
                json.dumps(sources_payload, ensure_ascii=False),
                json.dumps(metadata or {}, ensure_ascii=False),
            ),
        )

        conn.commit()
        conn.close()

    def log_query_with_provenance(
        self,
        tenant_id: str,
        user_id: str,
        session_id: str,
        query: str,
        response: str,
        provenance_record_id: Optional[str],
        source_provenances: List[Any],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Helper específico para queries de Optimus con procedencia.

        source_provenances: lista de objetos DataProvenance (o similares)
        """
        references: List[AuditReference] = []
        for prov in source_provenances or []:
            # DataProvenance suele tener: source_name, page_number, metadata, etc.
            doc_id = getattr(prov, "source_name", "") or ""
            page_number = getattr(prov, "page_number", None)
            paragraph = None
            if hasattr(prov, "metadata") and isinstance(prov.metadata, dict):
                paragraph = prov.metadata.get("excerpt") or prov.metadata.get("text_snippet")
            references.append(
                AuditReference(
                    document_id=doc_id,
                    source_name=doc_id,
                    page_number=page_number,
                    paragraph=paragraph,
                )
            )

        meta = dict(metadata or {})
        if provenance_record_id is not None:
            meta["provenance_record_id"] = provenance_record_id

        self.log_event(
            tenant_id=tenant_id,
            user_id=user_id,
            session_id=session_id,
            action="query",
            document_id=None,
            query=query,
            response=response,
            sources=references,
            metadata=meta,
        )

    # ----------------- Export helpers (para reportes) -----------------

    def export_events(
        self,
        tenant_id: Optional[str] = None,
        user_id: Optional[str] = None,
        document_id: Optional[str] = None,
        start_ts: Optional[str] = None,
        end_ts: Optional[str] = None,
        limit: int = 1000,
    ) -> List[Dict[str, Any]]:
        """
        Devuelve eventos como lista de dicts para ser exportados (CSV, etc.).
        Filtro por tenant, usuario, documento y rango de fechas ISO.
        """
        conn = self._get_conn()
        cur = conn.cursor()

        conditions = []
        params: List[Any] = []

        if tenant_id:
            conditions.append("tenant_id = ?")
            params.append(tenant_id)
        if user_id:
            conditions.append("user_id = ?")
            params.append(user_id)
        if document_id:
            conditions.append("document_id = ?")
            params.append(document_id)
        if start_ts:
            conditions.append("timestamp >= ?")
            params.append(start_ts)
        if end_ts:
            conditions.append("timestamp <= ?")
            params.append(end_ts)

        where_clause = ""
        if conditions:
            where_clause = "WHERE " + " AND ".join(conditions)

        query = f"""
        SELECT
            id,
            tenant_id,
            user_id,
            session_id,
            document_id,
            action,
            timestamp,
            query,
            response,
            sources_json,
            metadata_json
        FROM optimus_audit_events
        {where_clause}
        ORDER BY timestamp DESC
        LIMIT ?
        """
        params.append(limit)

        cur.execute(query, params)
        rows = cur.fetchall()
        conn.close()

        results: List[Dict[str, Any]] = []
        for row in rows:
            item = dict(row)
            # Parsear JSONs
            try:
                item["sources"] = json.loads(item.pop("sources_json") or "[]")
            except Exception:
                item["sources"] = []
            try:
                item["metadata"] = json.loads(item.pop("metadata_json") or "{}")
            except Exception:
                item["metadata"] = {}
            results.append(item)

        return results



