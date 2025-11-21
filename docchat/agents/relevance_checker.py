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
        docs: Sequence[Document] = retriever.invoke(question)
        docs = list(docs)[: self.top_k]
        if not docs:
            return RelevanceResult(label=RelevanceLabel.NO_MATCH, documents=[])

        context = "\n\n".join(doc.page_content for doc in docs)
        prompt = (
            "Eres un analista de relevancia. Clasifica qué tan bien el CONTEXTO responde la PREGUNTA. "
            "Devuelve únicamente uno de los siguientes labels: CAN_ANSWER, PARTIAL, NO_MATCH.\n\n"
            f"PREGUNTA:\n{question}\n\n"
            f"CONTEXTO:\n{context}"
        )

        # LangChain 1.0+ uses invoke() instead of predict()
        response = self.llm.invoke(prompt).content.strip().upper()
        valid = {RelevanceLabel.CAN_ANSWER, RelevanceLabel.PARTIAL, RelevanceLabel.NO_MATCH}
        label = response if response in valid else RelevanceLabel.NO_MATCH
        return RelevanceResult(label=label, documents=list(docs))

