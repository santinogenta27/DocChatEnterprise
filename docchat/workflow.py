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
    iteration_count: int  # Contador de iteraciones para self-correction


@dataclass
class AgentWorkflow:
    config: AppConfig
    provider: str = "openai"  # "openai" o "claude"
    relevance_checker: RelevanceChecker = field(init=False)
    research_agent: ResearchAgent = field(init=False)
    verification_agent: VerificationAgent = field(init=False)

    def __post_init__(self) -> None:
        self.relevance_checker = RelevanceChecker(
            model_name=self.config.relevance_model, 
            temperature=0.0,
            provider=self.provider,
            config=self.config
        )
        self.research_agent = ResearchAgent(
            model_name=self.config.research_model, 
            temperature=self.config.temperature,
            speed_mode=self.config.speed_mode,
            provider=self.provider,
            config=self.config
        )
        self.verification_agent = VerificationAgent(
            model_name=self.config.verification_model, 
            temperature=0.0,
            provider=self.provider,
            config=self.config
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
        
        # TRUNCAR contenido de chunks recuperados para evitar 429
        MAX_CHUNK_CHARS = 1500  # ~375 tokens por chunk
        truncated_docs = []
        for doc in context_docs[:30]:  # Máximo 30 chunks iniciales
            if len(doc.page_content) > MAX_CHUNK_CHARS:
                from langchain_core.documents import Document
                truncated_docs.append(Document(
                    page_content=doc.page_content[:MAX_CHUNK_CHARS] + "...",
                    metadata=doc.metadata
                ))
            else:
                truncated_docs.append(doc)
        context_docs = truncated_docs
        
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
                # ESTRATEGIA: Asegurar que TODOS los documentos tengan al menos 1 chunk representativo
                # Luego distribuir el resto de chunks equitativamente
                speed_mode = getattr(self.config, 'speed_mode', 'balanced')
                
                # Calcular límite basado en tokens estimados (1 token ≈ 4 caracteres)
                # AUMENTADO: máximo 15,000 tokens para documentos (dejando 12,000 para prompt + respuesta)
                # Total: 27,000 tokens (dentro del límite de 30,000 TPM)
                MAX_DOCS_TOKENS = 15000
                num_sources = len(docs_by_source)
                
                # ESTRATEGIA ADAPTATIVA: Ajustar tamaño de chunk según número de documentos
                # Para muchos documentos, usar chunks más pequeños para incluir TODOS
                if num_sources > 50:
                    # Para 50+ documentos: chunks pequeños (~250 tokens) para incluir todos
                    avg_chunk_chars = 1000  # ~250 tokens por chunk (aumentado para más contenido)
                    max_chunks_by_tokens = MAX_DOCS_TOKENS * 4 // avg_chunk_chars  # ~60 chunks máximo
                    MAX_CHUNK_CHARS = 1000  # Chunks más grandes para mejor análisis
                elif num_sources > 30:
                    # Para 30-50 documentos: chunks medianos (~300 tokens)
                    avg_chunk_chars = 1200  # ~300 tokens por chunk (aumentado)
                    max_chunks_by_tokens = MAX_DOCS_TOKENS * 4 // avg_chunk_chars  # ~50 chunks máximo
                    MAX_CHUNK_CHARS = 1200
                elif num_sources > 20:
                    # Para 20-30 documentos: chunks grandes (~350 tokens)
                    avg_chunk_chars = 1400  # ~350 tokens por chunk (aumentado)
                    max_chunks_by_tokens = MAX_DOCS_TOKENS * 4 // avg_chunk_chars  # ~42 chunks máximo
                    MAX_CHUNK_CHARS = 1400
                else:
                    # Para <20 documentos: chunks muy grandes (~400 tokens)
                    avg_chunk_chars = 1600  # ~400 tokens por chunk (aumentado)
                    max_chunks_by_tokens = MAX_DOCS_TOKENS * 4 // avg_chunk_chars  # ~37 chunks máximo
                    MAX_CHUNK_CHARS = 1600
                
                if speed_mode == "fast":
                    max_total_chunks = min(50, max_chunks_by_tokens)  # 50 chunks máximo (aumentado)
                elif speed_mode == "balanced":
                    max_total_chunks = min(60, max_chunks_by_tokens)  # 60 chunks máximo (aumentado)
                else:  # quality mode
                    max_total_chunks = min(75, max_chunks_by_tokens)  # 75 chunks máximo (aumentado)
                
                # ESTRATEGIA: Asegurar al menos 1 chunk de cada documento
                # Si hay espacio, agregar más chunks de documentos más grandes
                enhanced_docs = []
                seen_content = set()
                
                # FASE 1: Asegurar 1 chunk representativo de cada documento (PRIORIDAD MÁXIMA)
                for source, docs in docs_by_source.items():
                    if docs:
                        # Tomar el primer chunk (generalmente el más representativo)
                        doc = docs[0]
                        # Truncar si es necesario
                        if len(doc.page_content) > MAX_CHUNK_CHARS:
                            from langchain_core.documents import Document
                            doc = Document(
                                page_content=doc.page_content[:MAX_CHUNK_CHARS] + "...",
                                metadata=doc.metadata
                            )
                        content_hash = hash(doc.page_content)
                        if content_hash not in seen_content:
                            seen_content.add(content_hash)
                            enhanced_docs.append(doc)
                
                # FASE 2: Si hay espacio, agregar más chunks distribuyendo equitativamente
                remaining_slots = max_total_chunks - len(enhanced_docs)
                if remaining_slots > 0 and num_sources > 0:
                    # Calcular cuántos chunks adicionales por documento
                    additional_chunks_per_doc = max(1, remaining_slots // num_sources)
                    
                    for source, docs in docs_by_source.items():
                        if len(enhanced_docs) >= max_total_chunks:
                            break
                        # Agregar chunks adicionales (empezando desde el índice 1)
                        for i in range(1, min(additional_chunks_per_doc + 1, len(docs))):
                            if len(enhanced_docs) >= max_total_chunks:
                                break
                            doc = docs[i]
                            # Truncar si es necesario
                            if len(doc.page_content) > MAX_CHUNK_CHARS:
                                from langchain_core.documents import Document
                                doc = Document(
                                    page_content=doc.page_content[:MAX_CHUNK_CHARS] + "...",
                                    metadata=doc.metadata
                                )
                            content_hash = hash(doc.page_content)
                            if content_hash not in seen_content:
                                seen_content.add(content_hash)
                                enhanced_docs.append(doc)
                
                # Los chunks ya están truncados en las fases anteriores
                # Solo asegurar que no excedamos el límite final
                context_docs = enhanced_docs[:max_total_chunks]
                print(f"\n📊 Modo 'Analizar Todos': Usando {len(context_docs)} chunks de {len(docs_by_source)} documentos")
                print(f"   (Optimizado para evitar rate limits con {len(docs_by_source)} documentos)\n")
            else:
                # Fallback: intentar obtener más del retriever (con límites estrictos)
                try:
                    all_retrieved = state["retriever"].invoke(state["question"])
                    # Limitar a máximo 50 chunks para evitar 429
                    all_retrieved = all_retrieved[:50]
                    
                    docs_by_source = {}
                    for doc in all_retrieved:
                        source = doc.metadata.get("source", "unknown")
                        if source not in docs_by_source:
                            docs_by_source[source] = []
                        docs_by_source[source].append(doc)
                    
                    enhanced_docs = []
                    seen_content = set()
                    MAX_CHUNK_CHARS = 1500  # ~375 tokens por chunk
                    
                    for doc in context_docs:
                        # Truncar contenido si es muy grande
                        content = doc.page_content[:MAX_CHUNK_CHARS] if len(doc.page_content) > MAX_CHUNK_CHARS else doc.page_content
                        content_hash = hash(content)
                        if content_hash not in seen_content:
                            seen_content.add(content_hash)
                            if len(doc.page_content) > MAX_CHUNK_CHARS:
                                from langchain_core.documents import Document
                                enhanced_docs.append(Document(page_content=content + "...", metadata=doc.metadata))
                            else:
                                enhanced_docs.append(doc)
                    
                    for source, docs in docs_by_source.items():
                        source_count = sum(1 for d in enhanced_docs if d.metadata.get("source") == source)
                        if source_count < 2:  # Reducido a 2
                            needed = 2 - source_count
                            for doc in docs:
                                if needed <= 0 or len(enhanced_docs) >= 30:  # Límite total de 30
                                    break
                                # Truncar contenido
                                content = doc.page_content[:MAX_CHUNK_CHARS] if len(doc.page_content) > MAX_CHUNK_CHARS else doc.page_content
                                content_hash = hash(content)
                                if content_hash not in seen_content:
                                    seen_content.add(content_hash)
                                    if len(doc.page_content) > MAX_CHUNK_CHARS:
                                        from langchain_core.documents import Document
                                        enhanced_docs.append(Document(page_content=content + "...", metadata=doc.metadata))
                                    else:
                                        enhanced_docs.append(doc)
                                    needed -= 1
                    
                    context_docs = enhanced_docs[:30]  # Máximo 30 chunks
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
        
        # TRUNCAR contenido de chunks antes de pasarlos al ResearchAgent
        MAX_CHUNK_CHARS = 1500  # ~375 tokens por chunk
        MAX_TOTAL_CHUNKS = 30  # Máximo 30 chunks para evitar 429
        truncated_docs = []
        for doc in context_docs[:MAX_TOTAL_CHUNKS]:
            if len(doc.page_content) > MAX_CHUNK_CHARS:
                from langchain_core.documents import Document
                truncated_docs.append(Document(
                    page_content=doc.page_content[:MAX_CHUNK_CHARS] + "...",
                    metadata=doc.metadata
                ))
            else:
                truncated_docs.append(doc)
        context_docs = truncated_docs
        
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
            # Pasar conversational_mode al ResearchAgent para que ajuste max_tokens
            research = self.research_agent.run(
                state["question"], 
                context_docs, 
                conversational_mode=conversational_mode
            )
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
        
        # SELF-CORRECTION MECHANISM: Re-research si hay contradicciones o claims sin soporte
        # Pero limitar a máximo 3 iteraciones para evitar loops infinitos
        iteration_count = state.get("iteration_count", 0)
        max_iterations = 3
        
        should_re_research = False
        if iteration_count < max_iterations:
            # Re-research si:
            # 1. La respuesta NO está soportada por los documentos
            # 2. Hay contradicciones
            # 3. Hay claims sin soporte
            if not verification.supported:
                print(f"⚠️ Respuesta NO soportada - Re-ejecutando research (iteración {iteration_count + 1}/{max_iterations})")
                should_re_research = True
            elif verification.contradictions:
                print(f"⚠️ Contradicciones detectadas: {verification.contradictions}")
                print(f"   Re-ejecutando research (iteración {iteration_count + 1}/{max_iterations})")
                should_re_research = True
            elif verification.unsupported_claims:
                print(f"⚠️ Claims sin soporte: {verification.unsupported_claims}")
                print(f"   Re-ejecutando research (iteración {iteration_count + 1}/{max_iterations})")
                should_re_research = True
        
        if should_re_research:
            return {
                **state,
                "verification": verification,
                "should_continue": "re_research",
                "iteration_count": iteration_count + 1,
                "answer": state.get("draft_answer", ""),  # Mantener draft_answer como fallback
            }
        else:
            # Respuesta verificada o máximo de iteraciones alcanzado
            if iteration_count >= max_iterations:
                print(f"⚠️ Máximo de iteraciones alcanzado ({max_iterations}). Retornando respuesta actual.")
            else:
                print("✅ Respuesta verificada y soportada por los documentos.")
            
            return {
                **state,
                "verification": verification,
                "should_continue": "end",
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
            "iteration_count": 0,  # Inicializar contador de iteraciones para self-correction
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

