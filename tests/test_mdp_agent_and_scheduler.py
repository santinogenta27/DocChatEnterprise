from typing import Any, Dict

from docchat.research_action_agent.mdp_agent import MDPAgent, GistMemory
from docchat.research_action_agent.service_scheduler import (
    ServiceScheduler,
    ServiceDescriptor,
    ExecutionGraph,
    ExecutionNode,
)


class DummySemanticEngine:
    """Minimal stub to avoid hitting real OpenAI / vector stores in tests."""

    class DummyConfig:
        def __init__(self):
            import pathlib

            self.base_path = pathlib.Path(".")

    def __init__(self):
        self.config = self.DummyConfig()
        self.llm = None
        self.documents = {}
        self.vector_store = None


def test_mdp_agent_build_gist_without_llm():
    engine = DummySemanticEngine()

    # Fake SemanticDocument
    from docchat.semantic_data_engine import SemanticDocument, DataModality

    doc = SemanticDocument(
        doc_id="doc1",
        content="Este es un documento de prueba sobre contratos y proveedores.",
        modality=DataModality.TEXT,
        embedding_model="test",
        metadata={},
        created_at="",
        updated_at="",
        lineage=[],
        embedding_version="v1",
        source_path="test.txt",
        file_hash="hash",
    )
    engine.documents[doc.doc_id] = doc

    mdp = MDPAgent(engine)  # type: ignore[arg-type]
    gist = mdp.build_gist_for_document(doc)
    assert isinstance(gist, GistMemory)
    assert gist.doc_id == "doc1"
    assert gist.summary


def test_service_scheduler_execution_graph():
    scheduler = ServiceScheduler()

    def echo_service(payload: Dict[str, Any]) -> Dict[str, Any]:
        msg = payload.get("msg", "")
        return {"echo": msg}

    scheduler.register_service(
        ServiceDescriptor(
            name="echo",
            description="Echo service for tests",
            handler=echo_service,
        )
    )

    graph = ExecutionGraph()
    graph.add_node(ExecutionNode(node_id="step1", service_name="echo", params={"msg": "hola"}))

    result = scheduler.run_graph(graph)
    assert result["completed"] is True
    assert "step1" in result["context"]
    assert result["context"]["step1"]["echo"] == "hola"



