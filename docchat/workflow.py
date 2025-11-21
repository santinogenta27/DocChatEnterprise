from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Literal, TypedDict

from langchain_core.retrievers import BaseRetriever
from langchain_core.documents import Document
from langgraph.graph import END, START, StateGraph

from .agents import RelevanceChecker, ResearchAgent, VerificationAgent
from .agents.relevance_checker import RelevanceLabel
from .agents.verification_agent import VerificationResult
from .config import AppConfig


class AgentState(TypedDict, total=False):
    question: str
    retriever: BaseRetriever
    all_documents: List[Document]  # Todos los documentos procesados
    relevance_label: str
    context_docs: List
    draft_answer: str
    verification: VerificationResult
    answer: str
    should_continue: Literal["re_research", "end"]


@dataclass
class AgentWorkflow:
    config: AppConfig
    relevance_checker: RelevanceChecker = field(init=False)
    research_agent: ResearchAgent = field(init=False)
    verification_agent: VerificationAgent = field(init=False)

    def __post_init__(self) -> None:
        self.relevance_checker = RelevanceChecker(
            model_name=self.config.relevance_model, temperature=0.0
        )
        self.research_agent = ResearchAgent(
            model_name=self.config.research_model, temperature=self.config.temperature
        )
        self.verification_agent = VerificationAgent(
            model_name=self.config.verification_model, temperature=0.0
        )
        self.graph = self._build_graph()

    def _build_graph(self):
        graph = StateGraph(AgentState)
        graph.add_node("check_relevance", self._check_relevance_step)
        graph.add_node("research", self._research_step)
        graph.add_node("verify", self._verification_step)

        graph.set_entry_point("check_relevance")
        graph.add_edge("research", "verify")

        graph.add_conditional_edges(
            "check_relevance",
            self._decide_after_relevance,
            {
                "relevant": "research",
                "irrelevant": END,
            },
        )

        graph.add_conditional_edges(
            "verify",
            self._decide_after_verification,
            {
                "re_research": "research",
                "end": END,
            },
        )
        return graph.compile()

    def _check_relevance_step(self, state: AgentState) -> AgentState:
        result = self.relevance_checker.check(state["question"], state["retriever"])
        context_docs = result.documents
        
        # Si la pregunta es general (analizar todos los documentos), asegurar chunks de todos
        question_lower = state["question"].lower()
        is_general_query = any(word in question_lower for word in [
            "todos", "cada", "todos los", "all", "each", "every", 
            "analiza", "analyze", "analizar", "resumen", "summary", "información más valiosa"
        ])
        
        if is_general_query:
            # Para preguntas generales, usar TODOS los documentos procesados
            all_docs = state.get("all_documents", [])
            if all_docs:
                # Agrupar todos los documentos por fuente
                docs_by_source = {}
                for doc in all_docs:
                    source = doc.metadata.get("source", "unknown")
                    if source not in docs_by_source:
                        docs_by_source[source] = []
                    docs_by_source[source].append(doc)
                
                # Asegurar al menos 5-10 chunks de cada fuente para análisis completo
                enhanced_docs = []
                seen_content = set()
                
                # Agregar chunks de TODAS las fuentes, pero limitar el tamaño total
                # Calcular límite basado en número de documentos (máximo ~20,000 tokens de contexto)
                # Para muchos documentos (>50), reducir chunks por documento para evitar rate limits
                if len(docs_by_source) > 50:
                    # Para 100+ documentos, usar menos chunks por documento
                    max_chunks_per_doc = max(2, min(5, 80 // len(docs_by_source)))
                else:
                    max_chunks_per_doc = max(3, min(8, 100 // len(docs_by_source)))
                
                for source, docs in docs_by_source.items():
                    # Tomar chunks limitados de cada documento
                    chunks_to_take = min(max_chunks_per_doc, len(docs))
                    for doc in docs[:chunks_to_take]:
                        content_hash = hash(doc.page_content)
                        if content_hash not in seen_content:
                            seen_content.add(content_hash)
                            enhanced_docs.append(doc)
                
                # Limitar chunks según número de documentos para evitar rate limits
                # Para muchos documentos, usar menos chunks totales
                if len(docs_by_source) > 50:
                    max_total_chunks = min(80, len(enhanced_docs))  # Máximo 80 chunks para 50+ documentos
                else:
                    max_total_chunks = min(100, len(enhanced_docs))  # Máximo 100 chunks para <50 documentos
                
                context_docs = enhanced_docs[:max_total_chunks]
                print(f"\n📊 Modo 'Analizar Todos': Usando {len(context_docs)} chunks de {len(docs_by_source)} documentos")
                print(f"   (Optimizado para evitar rate limits con {len(docs_by_source)} documentos)\n")
            else:
                # Fallback: intentar obtener más del retriever
                try:
                    all_retrieved = state["retriever"].invoke(state["question"])
                    docs_by_source = {}
                    for doc in all_retrieved:
                        source = doc.metadata.get("source", "unknown")
                        if source not in docs_by_source:
                            docs_by_source[source] = []
                        docs_by_source[source].append(doc)
                    
                    enhanced_docs = []
                    seen_content = set()
                    for doc in context_docs:
                        content_hash = hash(doc.page_content)
                        if content_hash not in seen_content:
                            seen_content.add(content_hash)
                            enhanced_docs.append(doc)
                    
                    for source, docs in docs_by_source.items():
                        source_count = sum(1 for d in enhanced_docs if d.metadata.get("source") == source)
                        if source_count < 5:
                            needed = 5 - source_count
                            for doc in docs:
                                if needed <= 0:
                                    break
                                content_hash = hash(doc.page_content)
                                if content_hash not in seen_content:
                                    seen_content.add(content_hash)
                                    enhanced_docs.append(doc)
                                    needed -= 1
                    
                    context_docs = enhanced_docs[:200]
                except Exception:
                    pass
        
        return {
            **state,
            "relevance_label": result.label,
            "context_docs": context_docs,
        }

    def _decide_after_relevance(self, state: AgentState) -> str:
        label = state.get("relevance_label", RelevanceLabel.NO_MATCH)
        return "relevant" if label != RelevanceLabel.NO_MATCH else "irrelevant"

    def _research_step(self, state: AgentState) -> AgentState:
        context_docs = state.get("context_docs", [])
        # Log para debugging: mostrar cuántos documentos de cada fuente
        if context_docs:
            sources_count = {}
            for doc in context_docs:
                source = doc.metadata.get("source", "desconocido")
                sources_count[source] = sources_count.get(source, 0) + 1
            print(f"\n📊 Documentos recuperados para análisis:")
            for source, count in sources_count.items():
                print(f"   - {source}: {count} chunks")
            print(f"   Total: {len(context_docs)} chunks de {len(sources_count)} documentos\n")
        research = self.research_agent.run(state["question"], context_docs)
        return {**state, "draft_answer": research.answer}

    def _verification_step(self, state: AgentState) -> AgentState:
        verification = self.verification_agent.verify(
            answer=state.get("draft_answer", ""),
            question=state["question"],
            documents=state.get("context_docs", []),
        )
        # Always end after verification to prevent infinite loops
        # The answer is returned even if verification fails
        return {
            **state,
            "verification": verification,
            "should_continue": "end",  # Always end, no re-research
            "answer": state.get("draft_answer", ""),
        }

    @staticmethod
    def _decide_after_verification(state: AgentState) -> str:
        return state.get("should_continue", "end")

    def run(self, question: str, retriever: BaseRetriever, all_documents: List[Document] = None) -> Dict:
        """Execute the LangGraph workflow and return structured result."""
        # Set recursion limit to prevent infinite loops
        config = {"recursion_limit": 10}
        # Initialize state
        initial_state = {
            "question": question, 
            "retriever": retriever,
            "all_documents": all_documents or [],
        }
        result = self.graph.invoke(initial_state, config=config)
        verification: VerificationResult | None = result.get("verification")
        # Obtener fuentes únicas de todos los documentos recuperados
        seen_sources = set()
        sources = []
        for doc in result.get("context_docs", []):
            source = doc.metadata.get("source", "documento")
            if source not in seen_sources:
                seen_sources.add(source)
                sources.append({
                    "source": source,
                    "preview": doc.page_content[:280] + ("..." if len(doc.page_content) > 280 else ""),
                })
                if len(sources) >= 10:  # Mostrar hasta 10 fuentes únicas
                    break
        return {
            "relevance": result.get("relevance_label", RelevanceLabel.NO_MATCH),
            "answer": result.get("answer", "No pude generar una respuesta."),
            "sources": sources,
            "verification_report": verification.report() if verification else "Sin verificación.",
        }

