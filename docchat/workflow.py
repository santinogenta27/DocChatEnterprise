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
    conversational_mode: bool  # Modo conversacional (solo para Chat Conversacional)


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
            model_name=self.config.research_model, 
            temperature=self.config.temperature,
            speed_mode=self.config.speed_mode
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
        print("🔍 Verificando relevancia de la pregunta...")
        result = self.relevance_checker.check(state["question"], state["retriever"])
        context_docs = result.documents
        print(f"   Label de relevancia: {result.label}")
        print(f"   Documentos recuperados inicialmente: {len(context_docs)}")
        
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
                
                # Limitar chunks según número de documentos y modo de velocidad
                # Fast mode: menos chunks, más rápido
                # Balanced: chunks moderados
                # Quality: más chunks, mejor análisis
                speed_mode = getattr(self.config, 'speed_mode', 'balanced')
                if speed_mode == "fast":
                    if len(docs_by_source) > 50:
                        max_total_chunks = min(50, len(enhanced_docs))  # 50 chunks para modo rápido
                    else:
                        max_total_chunks = min(60, len(enhanced_docs))
                elif speed_mode == "balanced":
                    if len(docs_by_source) > 50:
                        max_total_chunks = min(80, len(enhanced_docs))  # 80 chunks para modo balanceado
                    else:
                        max_total_chunks = min(100, len(enhanced_docs))
                else:  # quality mode
                    if len(docs_by_source) > 50:
                        max_total_chunks = min(100, len(enhanced_docs))  # 100 chunks para máxima calidad
                    else:
                        max_total_chunks = min(120, len(enhanced_docs))
                
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
        question = state.get("question", "").lower()
        
        # Si es una pregunta general (analizar todos), SIEMPRE ejecutar research
        is_general_query = any(word in question for word in [
            "todos", "cada", "todos los", "all", "each", "every", 
            "analiza", "analyze", "analizar", "resumen", "summary", 
            "información más valiosa", "informacion mas valiosa",
            "información valiosa", "informacion valiosa",
            "puntos clave", "insights", "insights principales"
        ])
        
        if is_general_query:
            print(f"🔍 Pregunta general detectada - Forzando ejecución de ResearchAgent")
            print(f"   (Label de relevancia: {label}, pero es pregunta general)")
            return "relevant"  # Forzar ejecución
        
        decision = "relevant" if label != RelevanceLabel.NO_MATCH else "irrelevant"
        print(f"🔍 Decisión después de relevancia: {decision} (label: {label})")
        return decision

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
        
        print("🔍 Generando respuesta con Research Agent...")
        print("   (Esto puede tardar varios minutos con muchos documentos)\n")
        try:
            # Pasar modo conversacional al ResearchAgent
            conversational_mode = state.get("conversational_mode", False)
            research = self.research_agent.run(state["question"], context_docs, conversational_mode=conversational_mode)
            if research and research.answer:
                print(f"✅ Respuesta generada exitosamente ({len(research.answer)} caracteres)\n")
                return {**state, "draft_answer": research.answer}
            else:
                print("⚠️ ADVERTENCIA: ResearchAgent no generó respuesta")
                return {**state, "draft_answer": "No se pudo generar una respuesta. Intenta reformular la pregunta."}
        except Exception as e:
            print(f"❌ ERROR en ResearchAgent: {str(e)}")
            import traceback
            traceback.print_exc()
            return {**state, "draft_answer": f"Error al generar respuesta: {str(e)}"}

    def _verification_step(self, state: AgentState) -> AgentState:
        print("🔎 Verificando respuesta...")
        verification = self.verification_agent.verify(
            answer=state.get("draft_answer", ""),
            question=state["question"],
            documents=state.get("context_docs", []),
        )
        print("✅ Verificación completada\n")
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

    def run(self, question: str, retriever: BaseRetriever, all_documents: List[Document] = None, conversational_mode: bool = False) -> Dict:
        """Execute the LangGraph workflow and return structured result.
        
        Args:
            question: Pregunta del usuario
            retriever: Retriever para buscar documentos relevantes
            all_documents: Lista de todos los documentos procesados
            conversational_mode: Si True, usa formato conversacional libre (solo para Chat Conversacional)
        """
        print("\n" + "="*60)
        print("🚀 INICIANDO WORKFLOW DE ANÁLISIS")
        print("="*60 + "\n")
        # Set recursion limit to prevent infinite loops
        config = {"recursion_limit": 10}
        # Initialize state
        initial_state = {
            "question": question, 
            "retriever": retriever,
            "all_documents": all_documents or [],
            "conversational_mode": conversational_mode,
        }
        result = self.graph.invoke(initial_state, config=config)
        print("\n" + "="*60)
        print("✅ WORKFLOW COMPLETADO - Preparando respuesta final...")
        print("="*60 + "\n")
        
        # Debug: verificar qué contiene el resultado
        print(f"🔍 Debug - Estado del resultado:")
        print(f"   - Tiene 'answer': {'answer' in result}")
        print(f"   - Tiene 'draft_answer': {'draft_answer' in result}")
        print(f"   - Tiene 'context_docs': {'context_docs' in result}")
        if 'answer' in result:
            answer_len = len(result.get('answer', ''))
            print(f"   - Longitud de respuesta: {answer_len} caracteres")
        if 'draft_answer' in result:
            draft_len = len(result.get('draft_answer', ''))
            print(f"   - Longitud de draft_answer: {draft_len} caracteres")
        print()
        
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
        # Obtener respuesta (puede estar en 'answer' o 'draft_answer')
        final_answer = result.get("answer") or result.get("draft_answer", "")
        if not final_answer:
            final_answer = "No pude generar una respuesta. El workflow se completó pero no se generó contenido."
            print("⚠️ ADVERTENCIA: No se encontró respuesta en el resultado del workflow")
        
        print(f"📝 Respuesta final preparada: {len(final_answer)} caracteres")
        print(f"📚 Fuentes encontradas: {len(sources)}")
        print()
        
        return {
            "relevance": result.get("relevance_label", RelevanceLabel.NO_MATCH),
            "answer": final_answer,
            "sources": sources,
            "verification_report": verification.report() if verification else "Sin verificación.",
        }

