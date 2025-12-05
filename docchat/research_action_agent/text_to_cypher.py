"""Multi-Agent Text-to-Cypher pipeline for GraphRAG.

This module implements a lightweight, LLM-driven workflow inspired by
Multi-Agent GraphRAG:

- QueryGenerator: genera un primer Cypher basado en la pregunta + esquema.
- GraphExecutor: ejecuta el Cypher contra GraphRAGEngine.
- QueryEvaluator: evalúa si la query responde a la intención.
- EntityExtractor / Verifier: detecta y corrige entidades de esquema.
- Refinement loop: hasta 4 iteraciones máximo.

El objetivo aquí NO es replicar toda la complejidad académica, sino
proveer un flujo práctico y extensible que:
- Sea fácil de testear (usa GraphRAGEngine con backend mock por defecto).
- Sea invocable desde ResearchActionAgent.
- Devuelva un resultado estructurado y auditable.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import json

from langchain_core.language_models import BaseLanguageModel
from langchain_core.messages import HumanMessage

from .graphrag_engine import GraphRAGEngine


@dataclass
class CypherQueryResult:
    """Structured result of the Text-to-Cypher pipeline."""

    success: bool
    cypher: str
    rows: List[Dict[str, Any]] = field(default_factory=list)
    iterations: int = 0
    feedback_log: List[Dict[str, Any]] = field(default_factory=list)
    error: Optional[str] = None


class TextToCypherPipeline:
    """Minimal multi-agent style Text→Cypher pipeline."""

    def __init__(
        self,
        llm: BaseLanguageModel,
        graph_engine: Optional[GraphRAGEngine] = None,
        max_iterations: int = 4,
    ):
        self.llm = llm
        self.graph_engine = graph_engine or GraphRAGEngine()
        self.max_iterations = max_iterations

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self, question: str, schema_hint: Optional[str] = None) -> CypherQueryResult:
        """Run the full Text→Cypher refinement loop."""
        feedback_log: List[Dict[str, Any]] = []
        cypher = ""
        rows: List[Dict[str, Any]] = []
        error: Optional[str] = None

        for iteration in range(1, self.max_iterations + 1):
            # 1. Generate / refine query
            cypher = self._generate_cypher(question, schema_hint, feedback_log, previous_cypher=cypher)

            # 2. Execute
            try:
                rows = self.graph_engine.execute_cypher(cypher)
                exec_error = None
            except Exception as e:  # pragma: no cover - driver errors
                rows = []
                exec_error = str(e)

            # 3. Evaluate
            eval_feedback = self._evaluate_query(question, cypher, rows, exec_error)
            feedback_log.append(
                {
                    "iteration": iteration,
                    "cypher": cypher,
                    "rows_preview": rows[:3],
                    "evaluation": eval_feedback,
                }
            )

            decision = eval_feedback.get("decision", "end")
            if decision == "accept":
                return CypherQueryResult(
                    success=True,
                    cypher=cypher,
                    rows=rows,
                    iterations=iteration,
                    feedback_log=feedback_log,
                    error=None,
                )

            if exec_error:
                error = exec_error

            # If evaluator says we can continue, loop; otherwise stop
            if decision != "continue":
                break

        return CypherQueryResult(
            success=False,
            cypher=cypher,
            rows=rows,
            iterations=len(feedback_log),
            feedback_log=feedback_log,
            error=error or "Query could not be accepted after refinement loop",
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _generate_cypher(
        self,
        question: str,
        schema_hint: Optional[str],
        feedback_log: List[Dict[str, Any]],
        previous_cypher: str = "",
    ) -> str:
        """Use the LLM to generate or refine a Cypher query."""
        # Basic schema text from engine if not provided
        if not schema_hint:
            try:
                schema = self.graph_engine.get_schema()
                schema_hint = f"Labels: {schema.get('labels', [])}, Relationships: {schema.get('relationship_types', [])}"
            except Exception:
                schema_hint = ""

        feedback_text = ""
        if feedback_log:
            last_fb = feedback_log[-1].get("evaluation", {})
            feedback_text = f"Previous evaluation: {last_fb}"

        prompt = (
            "You are an expert Cypher query generator for property graphs.\n"
            "You receive a natural language question and MUST output ONLY a Cypher query, no explanations.\n"
            "Database schema (approximate):\n"
            f"{schema_hint}\n\n"
            f"User question: {question}\n"
        )
        if previous_cypher:
            prompt += f"Previous Cypher attempt:\n{previous_cypher}\n\n"
        if feedback_text:
            prompt += f"Feedback about the previous attempt:\n{feedback_text}\n\n"

        prompt += (
            "Generate an improved Cypher query that better answers the question.\n"
            "Return ONLY the Cypher, no markdown, no commentary.\n"
        )

        response = self.llm.invoke([HumanMessage(content=prompt)])
        cypher = getattr(response, "content", "").strip()
        # Very basic sanitization: remove backticks / code fences if present
        if "```" in cypher:
            parts = cypher.split("```")
            if len(parts) >= 2:
                cypher = parts[1].strip()
        return cypher

    def _evaluate_query(
        self,
        question: str,
        cypher: str,
        rows: List[Dict[str, Any]],
        execution_error: Optional[str],
    ) -> Dict[str, Any]:
        """Ask the LLM to evaluate whether the query is good enough."""
        if execution_error:
            # Directly request refinement
            decision = "continue"
            reason = f"Execution error: {execution_error}"
        else:
            sample_rows = rows[:3]
            eval_prompt = (
                "You are a critic for Cypher queries.\n"
                "You must decide if the query correctly answers the question.\n\n"
                f"Question: {question}\n"
                f"Cypher query:\n{cypher}\n\n"
                f"Sample results (JSON): {sample_rows}\n\n"
                "Answer in JSON ONLY with keys: decision, reason.\n"
                "decision must be one of: accept, continue, end.\n"
            )
            response = self.llm.invoke([HumanMessage(content=eval_prompt)])
            content = getattr(response, "content", "").strip()
            try:
                parsed = json.loads(content)  # type: ignore[name-defined]
            except Exception:
                # Fallback: approximate decision
                parsed = {"decision": "end", "reason": f"Could not parse evaluation: {content[:200]}"}

            decision = parsed.get("decision", "end")
            reason = parsed.get("reason", "")

        return {"decision": decision, "reason": reason, "execution_error": execution_error}


__all__ = ["TextToCypherPipeline", "CypherQueryResult"]


