from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from langchain_core.documents import Document
from langchain_openai import ChatOpenAI

from ..utils.llm_factory import create_llm


@dataclass(slots=True)
class VerificationResult:
    supported: bool
    relevant: bool
    unsupported_claims: List[str]
    contradictions: List[str]
    details: str

    def report(self) -> str:
        unsupported = ", ".join(self.unsupported_claims) if self.unsupported_claims else "Ninguna"
        contradictions = ", ".join(self.contradictions) if self.contradictions else "Ninguna"
        return (
            f"**Soportado:** {'Sí' if self.supported else 'No'}\n"
            f"**Relevante:** {'Sí' if self.relevant else 'No'}\n"
            f"**Claims sin soporte:** {unsupported}\n"
            f"**Contradicciones:** {contradictions}\n"
            f"**Notas:** {self.details or 'Sin comentarios adicionales.'}"
        )


class VerificationAgent:
    def __init__(self, model_name: str, temperature: float = 0.0, max_tokens: int = 400, provider: str = "openai", config=None):
        self.provider = provider
        self.config = config
        
        # Usar create_llm para soportar ambos proveedores
        if config:
            api_key = config.openai_api_key if provider == "openai" else config.anthropic_api_key
            self.llm = create_llm(
                provider=provider,
                model=model_name,
                temperature=temperature,
                max_tokens=max_tokens,
                api_key=api_key
            )
        else:
            # Fallback a OpenAI si no hay config
            self.llm = ChatOpenAI(model=model_name, temperature=temperature, max_tokens=max_tokens)

    def verify(self, answer: str, question: str, documents: List[Document]) -> VerificationResult:
        if not documents:
            return VerificationResult(False, False, [], [], "Sin contexto recuperado.")
        context = "\n\n".join(doc.page_content for doc in documents)
        prompt = (
            "Eres un verificador crítico. Revisa si la RESPUESTA está respaldada por el CONTEXTO y si responde la PREGUNTA. "
            "Debes devolver un bloque JSON con la forma:\n"
            "{"
            '"supported": "YES/NO", '
            '"relevant": "YES/NO", '
            '"unsupported_claims": ["..."], '
            '"contradictions": ["..."], '
            '"details": "texto"'
            "}\n\n"
            f"PREGUNTA:\n{question}\n\n"
            f"RESPUESTA:\n{answer}\n\n"
            f"CONTEXTO:\n{context}\n"
        )

        # LangChain 1.0+ uses invoke() instead of predict()
        raw = self.llm.invoke(prompt).content.strip()
        parsed = self._safe_parse(raw)
        return VerificationResult(
            supported=parsed.get("supported", "NO") == "YES",
            relevant=parsed.get("relevant", "NO") == "YES",
            unsupported_claims=parsed.get("unsupported_claims", []),
            contradictions=parsed.get("contradictions", []),
            details=parsed.get("details", ""),
        )

    @staticmethod
    def _safe_parse(raw: str) -> Dict:
        import json
        import re

        # Remove markdown code blocks if present
        cleaned = raw.strip()
        # Remove ```json and ``` markers
        cleaned = re.sub(r'^```json\s*', '', cleaned, flags=re.MULTILINE)
        cleaned = re.sub(r'^```\s*', '', cleaned, flags=re.MULTILINE)
        cleaned = cleaned.strip()
        
        # Try to extract JSON from the text
        json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', cleaned, re.DOTALL)
        if json_match:
            cleaned = json_match.group(0)

        try:
            return json.loads(cleaned)
        except (json.JSONDecodeError, AttributeError):
            # Fallback: try to parse key-value pairs manually
            result = {
                "supported": "NO",
                "relevant": "NO",
                "unsupported_claims": [],
                "contradictions": [],
                "details": "",
            }
            # Try to extract YES/NO values
            if '"supported":' in cleaned or "'supported':" in cleaned:
                if '"YES"' in cleaned or "'YES'" in cleaned:
                    result["supported"] = "YES"
            if '"relevant":' in cleaned or "'relevant':" in cleaned:
                if '"YES"' in cleaned or "'YES'" in cleaned:
                    result["relevant"] = "YES"
            result["details"] = f"Parsed from: {cleaned[:200]}"
            return result

