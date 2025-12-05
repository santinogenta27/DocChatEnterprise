"""Arquitectura de alto nivel del Research & Action Agent.

Incluye:
- InputParser
- TaskClassifier
- Planner (usa ServiceScheduler + ExecutionGraph)
- Agentes: ResearchAgent, RiskAssessmentAgent, ActionExecutorAgent, ReportGenerator
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

from .service_scheduler import ExecutionGraph, ExecutionNode


@dataclass
class ParsedInput:
    query: str
    context: Dict[str, Any]


class InputParser:
    """Normaliza inputs a una estructura interna homogénea."""

    def parse(self, query: str, extra: Dict[str, Any] | None = None) -> ParsedInput:
        return ParsedInput(query=query, context=extra or {})


@dataclass
class TaskIntent:
    intent: str  # research | risk_assessment | auto_ticketing | action | deep_search | neuro_symbolic | self_improve
    requires_action: bool
    risk_level: str  # low | medium | high | critical


class TaskClassifier:
    """Clasificador muy ligero basado en heurísticas."""

    def classify(self, parsed: ParsedInput) -> TaskIntent:
        q = parsed.query.lower()
        if "riesgo" in q or "risk" in q:
            return TaskIntent(intent="risk_assessment", requires_action=False, risk_level="high")
        if "ticket" in q or "incidente" in q:
            return TaskIntent(intent="auto_ticketing", requires_action=True, risk_level="medium")
        if "profundo" in q or "deep search" in q:
            return TaskIntent(intent="deep_search", requires_action=False, risk_level="medium")
        if "optimizar" in q or "mejorar modelo" in q:
            return TaskIntent(intent="self_improve", requires_action=False, risk_level="low")
        # Por defecto, research
        return TaskIntent(intent="research", requires_action=False, risk_level="low")


class Planner:
    """Planner jerárquico que genera un ExecutionGraph simple."""

    def build_plan(self, intent: TaskIntent, parsed: ParsedInput) -> ExecutionGraph:
        graph = ExecutionGraph()
        q = parsed.query

        if intent.intent == "research":
            graph.add_node(
                ExecutionNode(
                    node_id="research",
                    service_name="mdp_research",
                    params={"query": q},
                )
            )
        elif intent.intent == "risk_assessment":
            graph.add_node(
                ExecutionNode(
                    node_id="risk_research",
                    service_name="mdp_research",
                    params={"query": q},
                )
            )
            graph.add_node(
                ExecutionNode(
                    node_id="risk_analysis",
                    service_name="legal_graph_query",
                    params={"query": q},
                    depends_on=["risk_research"],
                )
            )
        elif intent.intent == "auto_ticketing":
            graph.add_node(
                ExecutionNode(
                    node_id="ticket_graph",
                    service_name="legal_graph_query",
                    params={"query": q},
                )
            )
        elif intent.intent == "deep_search":
            graph.add_node(
                ExecutionNode(
                    node_id="deep_graph",
                    service_name="legal_graph_query",
                    params={"query": q},
                )
            )
        else:
            # Fallback: simple research
            graph.add_node(
                ExecutionNode(
                    node_id="research_default",
                    service_name="mdp_research",
                    params={"query": q},
                )
            )

        return graph


__all__ = ["InputParser", "TaskClassifier", "Planner", "ParsedInput", "TaskIntent"]


