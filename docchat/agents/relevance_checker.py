from __future__ import annotations

from dataclasses import dataclass
from typing import List, Sequence

from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from langchain_openai import ChatOpenAI


class RelevanceLabel:
    CAN_ANSWER = "CAN_ANSWER"
    PARTIAL = "PARTIAL"
    NO_MATCH = "NO_MATCH"


@dataclass(slots=True)
class RelevanceResult:
    label: str
    documents: List[Document]


class RelevanceChecker:
    def __init__(self, model_name: str, temperature: float = 0.0, top_k: int = 5):
        self.llm = ChatOpenAI(model=model_name, temperature=temperature)
        self.top_k = top_k

    def check(self, question: str, retriever: BaseRetriever) -> RelevanceResult:
        # Detectar preguntas generales (analizar todos los documentos)
        question_lower = question.lower()
        is_general_query = any(word in question_lower for word in [
            "todos", "cada", "todos los", "all", "each", "every", 
            "analiza", "analyze", "analizar", "resumen", "summary", 
            "información más valiosa", "informacion mas valiosa",
            "información valiosa", "informacion valiosa",
            "puntos clave", "insights", "insights principales"
        ])
        
        # Para preguntas generales, siempre marcar como relevante
        if is_general_query:
            docs: Sequence[Document] = retriever.invoke(question)
            docs = list(docs)[: self.top_k]
            return RelevanceResult(label=RelevanceLabel.CAN_ANSWER, documents=list(docs) if docs else [])
        
        docs: Sequence[Document] = retriever.invoke(question)
        docs = list(docs)[: self.top_k]
        if not docs:
            return RelevanceResult(label=RelevanceLabel.NO_MATCH, documents=[])

        context = "\n\n".join(doc.page_content for doc in docs)
        prompt = (
            "Eres un analista de relevancia. Clasifica qué tan bien el CONTEXTO responde la PREGUNTA. "
            "IMPORTANTE: Si la pregunta es general (analizar, resumir, información valiosa de documentos), "
            "siempre devuelve CAN_ANSWER o PARTIAL, nunca NO_MATCH.\n\n"
            "Devuelve únicamente uno de los siguientes labels: CAN_ANSWER, PARTIAL, NO_MATCH.\n\n"
            f"PREGUNTA:\n{question}\n\n"
            f"CONTEXTO:\n{context}"
        )

        # LangChain 1.0+ uses invoke() instead of predict()
        response = self.llm.invoke(prompt).content.strip().upper()
        valid = {RelevanceLabel.CAN_ANSWER, RelevanceLabel.PARTIAL, RelevanceLabel.NO_MATCH}
        label = response if response in valid else RelevanceLabel.NO_MATCH
        return RelevanceResult(label=label, documents=list(docs))

