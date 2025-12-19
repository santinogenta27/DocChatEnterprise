from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any, List
from langchain_core.language_models import BaseLanguageModel
from langchain_core.messages import SystemMessage, HumanMessage

from ..state.customer_session import CustomerSessionState, SentimentLabel


@dataclass
class SentimentResult:
    label: SentimentLabel
    frustration_delta: float
    reasons: str


class SentimentAnalyzer:
    """Analizador simple de sentimiento y frustración.

    Combina reglas ligeras con un posible LLM para mayor precisión.
    """

    def __init__(self, llm: BaseLanguageModel | None = None) -> None:
        self.llm = llm

    def analyze(self, message: str, session: CustomerSessionState) -> SentimentResult:
        text = message.lower()

        # Reglas rápidas
        negative_keywords = [
            "esto es una mierda",
            "quiero hablar con un humano",
            "estoy cansado",
            "no funciona",
            "muy mal servicio",
            "decepcionado",
            "estafa",
        ]
        critical_keywords = [
            "denuncia",
            "reclamo formal",
            "demanda",
        ]

        frustration_delta = 0.0
        label = SentimentLabel.NEUTRAL
        reasons = ""

        if any(k in text for k in critical_keywords):
            label = SentimentLabel.CRITICAL
            frustration_delta = 0.7
            reasons = "Palabras de escalamiento crítico detectadas"
        elif any(k in text for k in negative_keywords):
            label = SentimentLabel.NEGATIVE
            frustration_delta = 0.4
            reasons = "Lenguaje claramente negativo detectado"

        # Opcional: refinar con LLM si está disponible
        if self.llm is not None:
            try:
                prompt = (
                    "Clasifica el siguiente mensaje de cliente en positivo, neutral, negativo o crítico. "
                    "Responde solo una palabra: positivo, neutral, negativo o crítico. Mensaje: "
                    f"{message[:2000]}"
                )
                resp = self.llm.invoke([
                    SystemMessage(content="Eres un clasificador de sentimiento de atención al cliente."),
                    HumanMessage(content=prompt),
                ])
                content = getattr(resp, "content", str(resp)).strip().lower()
                if "crítico" in content or "critico" in content:
                    label = SentimentLabel.CRITICAL
                    frustration_delta = max(frustration_delta, 0.7)
                elif "negativo" in content:
                    label = SentimentLabel.NEGATIVE
                    frustration_delta = max(frustration_delta, 0.4)
                elif "positivo" in content:
                    label = SentimentLabel.POSITIVE
                    frustration_delta = min(frustration_delta, -0.1)
                else:
                    label = SentimentLabel.NEUTRAL
            except Exception:
                # Si falla el LLM, mantenemos la clasificación por reglas
                pass

        return SentimentResult(label=label, frustration_delta=frustration_delta, reasons=reasons)

    def update_session_sentiment(self, session: CustomerSessionState, result: SentimentResult) -> None:
        # Actualizar score acumulado con clipping
        session.frustration_score = max(0.0, min(1.0, session.frustration_score + result.frustration_delta))
        session.sentiment = result.label

        # Decidir si necesita handoff
        if session.frustration_score >= 0.8 or result.label == SentimentLabel.CRITICAL:
            session.needs_handoff = True
        elif session.frustration_score <= 0.2 and result.label in (SentimentLabel.POSITIVE, SentimentLabel.NEUTRAL):
            session.needs_handoff = False


