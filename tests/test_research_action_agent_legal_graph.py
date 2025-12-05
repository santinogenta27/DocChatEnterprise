from typing import Any, Dict

from docchat.research_action_agent.agent import ResearchActionAgent
from docchat.research_action_agent.graphrag_engine import GraphRAGEngine, GraphConnectionConfig


class FakeLLM:
    """Very small fake LLM for unit tests."""

    def invoke(self, messages):
        from types import SimpleNamespace

        last = messages[-1]
        content = getattr(last, "content", "")
        if "expert Cypher query generator" in content:
            # Return a trivial MATCH that works with GraphRAGEngine mock
            return SimpleNamespace(content="MATCH (a:Article) RETURN a")
        if "critic for Cypher queries" in content:
            return SimpleNamespace(content='{"decision": "accept", "reason": "Mock accept."}')
        # Fallback generic JSON
        return SimpleNamespace(content='{"summary": "ok"}')


def test_research_action_agent_legal_graph_mode_uses_mock_backend(monkeypatch):
    # Create a minimal AppConfig stub
    from docchat.config import AppConfig

    config = AppConfig()
    # Avoid real OpenAI calls by faking api key; we will monkeypatch llm after init
    config.openai_api_key = "test-key"

    agent = ResearchActionAgent(config=config, provider="openai", semantic_engine=None)

    # Patch internal llm and text_to_cypher to use FakeLLM and mock graph engine
    fake_llm = FakeLLM()
    agent.llm = fake_llm  # type: ignore[assignment]
    agent.graph_engine = GraphRAGEngine(GraphConnectionConfig(uri="", backend="mock"))
    agent.text_to_cypher.llm = fake_llm  # type: ignore[assignment]
    agent.text_to_cypher.graph_engine = agent.graph_engine

    result = agent.run_query("¿Qué dice el artículo 6 sobre vivienda?", mode="legal_graph")
    assert "graph_rows" in result
    assert "cypher" in result
    # In mock mode we expect at least one row from the Article stub
    assert isinstance(result["graph_rows"], list)
    assert result["cypher"]



