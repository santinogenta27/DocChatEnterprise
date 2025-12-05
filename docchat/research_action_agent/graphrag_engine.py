"""GraphRAGEngine - Minimal Graph RAG backend for Research & Action Agent.

This module provides a thin abstraction over a property graph database
(Neo4j / Memgraph compatible with Cypher) so that higher level agents
can:

- Execute Cypher queries
- Inspect basic schema (labels, relationship types, property keys)
- Run health checks

The design is intentionally minimal and defensive:
- If the Python driver is not available or the database is not reachable,
  the engine degrades gracefully and exposes a `mock` backend that can be
  used in unit tests.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
import os

try:
    # Prefer official Neo4j driver; Memgraph is protocol compatible in Bolt mode.
    from neo4j import GraphDatabase, Driver, basic_auth  # type: ignore

    NEO4J_AVAILABLE = True
except Exception:  # pragma: no cover - optional dependency
    GraphDatabase = None  # type: ignore
    Driver = None  # type: ignore
    basic_auth = None  # type: ignore
    NEO4J_AVAILABLE = False


@dataclass
class GraphConnectionConfig:
    """Configuration for connecting to a property graph backend."""

    uri: str
    username: Optional[str] = None
    password: Optional[str] = None
    database: Optional[str] = None
    backend: str = "auto"  # "auto", "neo4j", "memgraph", "mock"


class GraphRAGEngine:
    """Minimal Graph RAG backend.

    This engine is intentionally simple:
    - It hides driver / connection details from higher level agents.
    - It provides a small, well defined surface:
        - execute_cypher
        - get_schema
        - ping
    - It supports a `mock` backend for tests.
    """

    def __init__(self, config: Optional[GraphConnectionConfig] = None):
        # Load from environment if not provided
        if config is None:
            uri = os.getenv("GRAPH_DB_URI", "").strip()
            backend = os.getenv("GRAPH_DB_BACKEND", "auto").strip() or "auto"
            username = os.getenv("GRAPH_DB_USERNAME", "").strip() or None
            password = os.getenv("GRAPH_DB_PASSWORD", "").strip() or None
            database = os.getenv("GRAPH_DB_DATABASE", "").strip() or None
            config = GraphConnectionConfig(
                uri=uri, username=username, password=password, database=database, backend=backend
            )

        self.config = config
        self._driver: Optional[Driver] = None
        self._mock_mode: bool = False

        # Decide backend
        if config.backend == "mock" or not config.uri:
            # Explicit mock or no URI configured
            self._mock_mode = True
            return

        if not NEO4J_AVAILABLE:
            # Driver not installed - fallback to mock
            print(
                "⚠️ GraphRAGEngine: neo4j driver no está instalado. "
                "Usando backend 'mock'. Instala con: pip install neo4j"
            )
            self._mock_mode = True
            return

        try:
            auth = None
            if config.username and config.password and basic_auth:
                auth = basic_auth(config.username, config.password)

            self._driver = GraphDatabase.driver(config.uri, auth=auth)  # type: ignore[arg-type]
        except Exception as e:  # pragma: no cover - network / driver errors
            print(f"⚠️ GraphRAGEngine: No se pudo conectar al grafo: {e}. Usando backend 'mock'.")
            self._mock_mode = True

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def is_mock(self) -> bool:
        """Return True if engine is running in mock mode."""
        return self._mock_mode

    def close(self) -> None:
        """Close underlying driver if any."""
        if self._driver is not None:
            try:
                self._driver.close()
            except Exception:
                pass

    # Cypher execution -------------------------------------------------

    def execute_cypher(
        self,
        query: str,
        parameters: Optional[Dict[str, Any]] = None,
        database: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Execute a Cypher query and return list of dict rows.

        In `mock` mode this returns a deterministic, hardcoded response that
        is useful for unit tests and end-to-end demos without a live graph.
        """
        if self._mock_mode:
            # Very small deterministic stub – enough for tests and demo.
            return self._execute_cypher_mock(query, parameters or {})

        if not self._driver:
            raise RuntimeError("GraphRAGEngine no está inicializado (sin driver y sin modo mock).")

        params = parameters or {}

        def _run_tx(tx):
            result = tx.run(query, **params)
            return [dict(record) for record in result]

        with self._driver.session(database=database or self.config.database) as session:
            return session.execute_read(_run_tx)

    def _execute_cypher_mock(self, query: str, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Very small deterministic mock implementation."""
        q_lower = query.lower()
        # Simulate a simple legal article node
        if "match (a:article" in q_lower or "match (a:articulo" in q_lower:
            return [
                {
                    "id": "art_6_2001",
                    "text": "Todos tienen derecho a la educación, la salud, el trabajo, la vivienda y el ocio.",
                    "effective_from": "2000-02-14",
                    "effective_to": None,
                }
            ]
        # Default empty
        return []

    # Schema inspection ------------------------------------------------

    def get_schema(self) -> Dict[str, List[str]]:
        """Return a minimal view of graph schema: labels and relationship types.

        In mock mode returns a fixed, small schema.
        """
        if self._mock_mode:
            return {
                "labels": ["Article", "Law", "Theme"],
                "relationship_types": ["CONTAINS", "AMENDS", "HAS_THEME"],
            }

        if not self._driver:
            raise RuntimeError("GraphRAGEngine no está inicializado.")

        labels_query = "CALL db.labels() YIELD label RETURN label"
        rels_query = "CALL db.relationshipTypes() YIELD relationshipType RETURN relationshipType"

        labels = [row["label"] for row in self.execute_cypher(labels_query)]
        rels = [row["relationshipType"] for row in self.execute_cypher(rels_query)]
        return {"labels": labels, "relationship_types": rels}

    # Health -----------------------------------------------------------

    def ping(self) -> bool:
        """Check if the graph backend is reachable.

        Always returns True in mock mode.
        """
        if self._mock_mode:
            return True

        try:
            _ = self.get_schema()
            return True
        except Exception:
            return False


__all__ = ["GraphConnectionConfig", "GraphRAGEngine"]


