import json

from docchat.research_action_agent.graphrag_engine import GraphRAGEngine, GraphConnectionConfig
from docchat.research_action_agent.sat_graph_api import SATGraphAPI


def test_graphrag_engine_mock_basic():
    config = GraphConnectionConfig(uri="", backend="mock")
    engine = GraphRAGEngine(config=config)
    assert engine.is_mock is True
    assert engine.ping() is True

    rows = engine.execute_cypher("MATCH (a:Article) RETURN a")
    assert isinstance(rows, list)


def test_sat_graph_api_mock_primitives():
    engine = GraphRAGEngine(GraphConnectionConfig(uri="", backend="mock"))
    api = SATGraphAPI(graph_engine=engine)

    cands = api.resolve_item_reference("Artículo 6 de la Constitución")
    assert cands
    item_id = cands[0]["item_id"]

    ver = api.get_valid_version(item_id, "2001-05-20T00:00:00Z")
    assert ver is not None
    text = api.get_text_for_version(ver.version_id)
    assert text and "derecho" in text.lower()

    history = api.get_item_history(item_id)
    assert isinstance(history, list)

    causality = api.trace_causality(ver.version_id)
    assert "creating_action" in causality

    diff = api.compare_versions(ver.version_id, ver.version_id)
    assert diff["status"] == "ok"



