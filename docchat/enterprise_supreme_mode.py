"""
Enterprise Supreme Mode - Fusión de Enterprise API + Alien Mode + ChatPDF Mode
Sistema de Análisis de Documentos Empresariales de Máxima Calidad

CARACTERÍSTICAS PRINCIPALES:
1. Procesa 100+ PDFs automáticamente (como Enterprise API)
2. Recibe prompts opcionales del usuario (como Alien/ChatPDF)
3. Análisis automático DETALLADO (no general) con insights accionables
4. Optimizaciones técnicas avanzadas:
   - RAG mejorado con embeddings grandes (text-embedding-3-large)
   - Reranking avanzado con cross-encoder
   - Chain-of-Thought reasoning
   - Self-Consistency (múltiples respuestas y votación)
   - Procesamiento paralelo optimizado

CASOS DE USO:
- Inteligencia competitiva
- Análisis financiero / due diligence
- Optimización de ventas / marketing
- Automatización de cumplimiento / legales
- R&D y patentes
"""

from __future__ import annotations

import json
import os
import time
import asyncio
import uuid
from typing import List, Dict, Optional, Any, Tuple, Iterator
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field

from langchain_core.documents import Document
from langchain_core.language_models import BaseLanguageModel
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic

from .config import AppConfig
from .document_processor import DocumentProcessor
from .retriever_builder import RetrieverBuilder
from .workflow import AgentWorkflow
from .context_folding import ContextFolder
from .data_provenance import DataProvenanceTracker, DataProvenance, DataSourceType
from .chain_of_thought import ChainOfThoughtReasoner, ThoughtChain
from .path_dependent_reasoning import PathDependentReasoner
from .test_time_training import TestTimeTrainer
from .person_in_the_loop import PersonInTheLoop, DecisionCriticality
from .reinforcement_planning import ReinforcementPlanner, DecisionTree
from .mcp_manager import MCPManager

# Intentar importar reranking avanzado
try:
    from sentence_transformers import CrossEncoder
    RERANKING_AVAILABLE = True
except ImportError:
    RERANKING_AVAILABLE = False
    CrossEncoder = None
    print("⚠️ sentence-transformers no disponible. Reranking avanzado deshabilitado.")


@dataclass
class SupremeAnalysisResult:
    """Resultado de análisis detallado."""
    document_name: str
    document_type: str
    executive_summary: str
    key_insights: List[str]
    risks_detected: List[Dict[str, Any]]
    opportunities_detected: List[Dict[str, Any]]
    critical_clauses: List[Dict[str, Any]]
    kpis_extracted: Dict[str, Any]
    entities: List[str]
    recommendations: List[str]
    confidence_score: float
    processing_time: float


@dataclass
class SupremeQueryResult:
    """Resultado de consulta con optimizaciones."""
    answer: str
    sources: List[Dict[str, str]]
    confidence: float
    reasoning_chain: List[str]  # Chain-of-Thought
    consistency_score: float  # Self-Consistency
    reranked_docs: List[Document]
    metadata: Dict[str, Any]


class AdvancedReranker:
    """Reranking avanzado usando cross-encoder."""
    
    def __init__(self, config: AppConfig):
        self.config = config
        self.reranker = None
        
        if RERANKING_AVAILABLE:
            try:
                # Usar modelo cross-encoder para reranking
                # ms-marco-MiniLM-L-6-v2 es rápido y efectivo
                self.reranker = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')
                print("✅ Reranker avanzado inicializado (Cross-Encoder)")
            except Exception as e:
                print(f"⚠️ Error inicializando reranker: {e}")
                self.reranker = None
    
    def rerank(self, query: str, documents: List[Document], top_k: int = 10) -> List[Document]:
        """Rerankea documentos usando cross-encoder."""
        if not self.reranker or len(documents) <= top_k:
            return documents[:top_k]
        
        try:
            # Preparar pares query-documento
            pairs = [(query, doc.page_content[:512]) for doc in documents]
            
            # Calcular scores
            scores = self.reranker.predict(pairs)
            
            # Ordenar por score
            scored_docs = list(zip(scores, documents))
            scored_docs.sort(key=lambda x: x[0], reverse=True)
            
            # Retornar top_k
            reranked = [doc for _, doc in scored_docs[:top_k]]
            
            # Agregar metadata de reranking
            for doc in reranked:
                if "reranking" not in doc.metadata:
                    doc.metadata["reranking"] = {
                        "applied": True,
                        "model": "cross-encoder/ms-marco-MiniLM-L-6-v2"
                    }
            
            return reranked
        except Exception as e:
            print(f"⚠️ Error en reranking: {e}")
            return documents[:top_k]


class SelfConsistencyReasoner:
    """Self-Consistency: genera múltiples respuestas y vota por la mejor."""
    
    def __init__(self, llm: BaseLanguageModel, num_samples: int = 3):
        self.llm = llm
        self.num_samples = num_samples
    
    def generate_consistent_answer(
        self,
        query: str,
        context: str,
        use_chain_of_thought: bool = True
    ) -> Tuple[str, float]:
        """Genera múltiples respuestas y retorna la más consistente."""
        answers = []
        
        for i in range(self.num_samples):
            if use_chain_of_thought:
                prompt = f"""Responde la siguiente pregunta usando Chain-of-Thought reasoning.

Pregunta: {query}

Contexto:
{context[:4000]}

Paso 1: Identifica la información relevante en el contexto
Paso 2: Analiza cómo esta información responde la pregunta
Paso 3: Genera tu respuesta final

Respuesta:"""
            else:
                prompt = f"""Responde la siguiente pregunta basándote en el contexto.

Pregunta: {query}

Contexto:
{context[:4000]}

Respuesta:"""
            
            try:
                response = self.llm.invoke(prompt)
                answer = response.content.strip() if hasattr(response, 'content') else str(response).strip()
                answers.append(answer)
            except Exception as e:
                print(f"⚠️ Error generando respuesta {i+1}: {e}")
        
        if not answers:
            return "No se pudo generar respuesta.", 0.0
        
        # Votación por mayoría (simplificada)
        # En producción, usaría embeddings para medir similitud semántica
        if len(answers) == 1:
            return answers[0], 1.0
        
        # Contar respuestas similares
        from collections import Counter
        # Simplificación: usar las primeras 100 palabras como "signatura"
        signatures = [ans[:200].lower() for ans in answers]
        counter = Counter(signatures)
        most_common = counter.most_common(1)[0]
        
        # Encontrar la respuesta correspondiente
        best_answer = answers[0]
        for ans in answers:
            if ans[:200].lower() == most_common[0]:
                best_answer = ans
                break
        
        consistency_score = most_common[1] / len(answers)
        
        return best_answer, consistency_score


class EnterpriseSupremeMode:
    """
    Enterprise Supreme Mode - Fusión de Enterprise API + Alien Mode + ChatPDF Mode
    
    Combina:
    - Procesamiento masivo de Enterprise API (100+ PDFs)
    - QA interactivo de Alien/ChatPDF (prompts opcionales)
    - Análisis automático detallado (no general)
    - Optimizaciones técnicas avanzadas
    """
    
    def __init__(
        self,
        config: AppConfig,
        processor: DocumentProcessor,
        retriever_builder: RetrieverBuilder,
        context_manager: Optional[Any] = None,
        provider: str = "openai"
    ):
        self.config = config
        self.provider = provider
        self.processor = processor
        self.retriever_builder = retriever_builder
        self.context_manager = context_manager
        
        # LLM principal - usar modelo grande para mejor calidad
        self.llm = self._get_llm_for_provider(provider)
        
        # LLM para embeddings grandes (text-embedding-3-large)
        # Actualizar config temporalmente para usar embedding grande
        original_embedding_model = config.embedding_model
        config.embedding_model = "text-embedding-3-large"  # Embedding grande para mejor captura de contexto
        
        # Retriever builder con embeddings grandes
        self.supreme_retriever_builder = RetrieverBuilder(config)
        
        # Restaurar modelo original
        config.embedding_model = original_embedding_model
        
        # Módulos avanzados
        self.context_folder = ContextFolder(
            config=config,
            llm=self.llm,
            max_context_tokens=128000,  # Context window grande
            max_branches=10
        )
        
        self.provenance_tracker = DataProvenanceTracker(config=config)
        
        self.chain_reasoner = ChainOfThoughtReasoner(
            config=config,
            llm=self.llm
        )
        
        self.path_reasoner = PathDependentReasoner(
            config=config,
            llm=self.llm,
            max_paths=5
        )
        
        self.test_time_trainer = TestTimeTrainer(
            config=config,
            llm=self.llm,
            learning_rate=0.1,
            min_confidence=0.6
        )
        
        # Reranking avanzado
        self.reranker = AdvancedReranker(config)
        
        # Self-Consistency
        self.consistency_reasoner = SelfConsistencyReasoner(self.llm, num_samples=3)
        
        # Workflow
        self.workflow = AgentWorkflow(config)
        
        # Sesiones
        self.sessions: Dict[str, Dict[str, Any]] = {}
        
        print("✅ Enterprise Supreme Mode inicializado")
        print(f"   - Embeddings: text-embedding-3-large (grandes)")
        print(f"   - Reranking: {'✅ Cross-Encoder' if RERANKING_AVAILABLE else '❌ No disponible'}")
        print(f"   - Chain-of-Thought: ✅")
        print(f"   - Self-Consistency: ✅")
    
    def _get_llm_for_provider(self, provider: str) -> BaseLanguageModel:
        """Obtiene LLM según el provider."""
        from docchat.utils.llm_factory import create_llm
        
        if provider == "openai":
            return create_llm(
                provider="openai",
                model=self.config.research_model or "gpt-4o",
                temperature=0.2,
                api_key=self.config.openai_api_key,
                max_tokens=8000,
                request_timeout=300
            )
        elif provider == "anthropic":
            return create_llm(
                provider="anthropic",
                model="claude-3-5-sonnet-20241022",
                temperature=0.2,
                api_key=self.config.anthropic_api_key,
                max_tokens=8000,
                request_timeout=300
            )
        else:
            return ChatOpenAI(model="gpt-4o", temperature=0.2)
    
    def initialize_session(self, session_id: str) -> Dict[str, Any]:
        """Inicializa una sesión."""
        if session_id not in self.sessions:
            self.sessions[session_id] = {
                "docs": [],
                "retriever": None,
                "analyses": {},
                "created_at": datetime.now().isoformat()
            }
        return self.sessions[session_id]
    
    def process_documents(
        self,
        session_id: str,
        files: List[Any]
    ) -> Dict[str, Any]:
        """Procesa documentos (similar a Enterprise API pero con mejor RAG)."""
        session = self.initialize_session(session_id)
        
        try:
            # Procesar documentos
            print(f"📄 Procesando {len(files)} documentos...")
            docs = self.processor.process(files)
            
            if not docs:
                return {
                    "success": False,
                    "error": "No se pudieron procesar los documentos."
                }
            
            # Construir retriever con embeddings grandes
            namespace = f"supreme_{uuid.uuid4().hex[:8]}"
            retriever = self.supreme_retriever_builder.build_hybrid_retriever(
                docs,
                namespace=namespace
            )
            
            # Actualizar sesión
            session["docs"] = docs
            session["retriever"] = retriever
            session["files"] = files
            
            return {
                "success": True,
                "documents_processed": len(files),
                "chunks_generated": len(docs),
                "session_id": session_id
            }
        
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def _generate_detailed_analysis(
        self,
        file_name: str,
        file_docs: List[Document],
        retriever: Any
    ) -> SupremeAnalysisResult:
        """Genera análisis detallado (no general) de un documento."""
        start_time = time.time()
        
        # Construir contexto completo del documento
        doc_content = "\n\n".join([doc.page_content for doc in file_docs[:50]])  # Primeros 50 chunks
        
        # Prompt mejorado para análisis detallado
        analysis_prompt = f"""Eres un analista empresarial senior de nivel C-Suite. Analiza este documento en PROFUNDIDAD.

DOCUMENTO: {file_name}

CONTENIDO:
{doc_content[:15000]}

INSTRUCCIONES PARA ANÁLISIS DETALLADO:

1. TIPO DE DOCUMENTO:
   - Identifica el tipo exacto (contrato, reporte financiero, auditoría, etc.)
   - Determina el propósito y contexto empresarial

2. RESUMEN EJECUTIVO (2-3 párrafos):
   - Resumen conciso pero completo
   - Enfoque en información accionable para toma de decisiones

3. INSIGHTS CLAVE (mínimo 5):
   - Información crítica que requiere atención inmediata
   - Patrones, tendencias o anomalías detectadas
   - Datos numéricos importantes (KPIs, métricas, porcentajes)

4. RIESGOS DETECTADOS:
   - Riesgos legales, financieros, operacionales o de compliance
   - Nivel de severidad (Alto, Medio, Bajo)
   - Impacto potencial en el negocio

5. OPORTUNIDADES DETECTADAS:
   - Oportunidades de crecimiento, optimización o mejora
   - Potencial de ROI o valor empresarial
   - Acciones recomendadas para capitalizar

6. CLÁUSULAS CRÍTICAS (si aplica):
   - Cláusulas importantes en contratos
   - Términos y condiciones relevantes
   - Fechas de vencimiento o plazos críticos

7. KPIs Y MÉTRICAS EXTRAÍDAS:
   - Números clave, porcentajes, ratios
   - Tendencias temporales si hay datos históricos
   - Comparaciones o benchmarks si están disponibles

8. ENTIDADES PRINCIPALES:
   - Personas, empresas, organizaciones mencionadas
   - Roles y responsabilidades identificadas

9. RECOMENDACIONES ACCIONABLES (mínimo 3):
   - Recomendaciones específicas basadas en el análisis
   - Priorizadas por impacto y urgencia
   - Enfocadas en resultados empresariales

IMPORTANTE:
- Sé ESPECÍFICO y DETALLADO, no general
- Cita datos exactos del documento (números, fechas, nombres)
- Proporciona contexto empresarial relevante
- Enfócate en información accionable

Responde en formato JSON con las siguientes claves:
{{
    "document_type": "...",
    "executive_summary": "...",
    "key_insights": ["...", "..."],
    "risks_detected": [{{"type": "...", "severity": "...", "description": "...", "impact": "..."}}],
    "opportunities_detected": [{{"type": "...", "impact": "...", "description": "...", "recommended_action": "..."}}],
    "critical_clauses": [{{"clause": "...", "importance": "...", "description": "..."}}],
    "kpis_extracted": {{"metric_name": "value", ...}},
    "entities": ["...", "..."],
    "recommendations": ["...", "..."]
}}"""
        
        try:
            response = self.llm.invoke(analysis_prompt)
            analysis_text = response.content.strip() if hasattr(response, 'content') else str(response).strip()
            
            # Parsear JSON
            try:
                # Intentar extraer JSON del texto
                import re
                json_match = re.search(r'\{.*\}', analysis_text, re.DOTALL)
                if json_match:
                    analysis_json = json.loads(json_match.group(0))
                else:
                    # Fallback: crear estructura básica
                    analysis_json = {
                        "document_type": "unknown",
                        "executive_summary": analysis_text[:500],
                        "key_insights": [],
                        "risks_detected": [],
                        "opportunities_detected": [],
                        "critical_clauses": [],
                        "kpis_extracted": {},
                        "entities": [],
                        "recommendations": []
                    }
            except json.JSONDecodeError:
                # Si no se puede parsear, crear estructura básica
                analysis_json = {
                    "document_type": "unknown",
                    "executive_summary": analysis_text[:500],
                    "key_insights": [analysis_text],
                    "risks_detected": [],
                    "opportunities_detected": [],
                    "critical_clauses": [],
                    "kpis_extracted": {},
                    "entities": [],
                    "recommendations": []
                }
            
            processing_time = time.time() - start_time
            
            return SupremeAnalysisResult(
                document_name=file_name,
                document_type=analysis_json.get("document_type", "unknown"),
                executive_summary=analysis_json.get("executive_summary", ""),
                key_insights=analysis_json.get("key_insights", []),
                risks_detected=analysis_json.get("risks_detected", []),
                opportunities_detected=analysis_json.get("opportunities_detected", []),
                critical_clauses=analysis_json.get("critical_clauses", []),
                kpis_extracted=analysis_json.get("kpis_extracted", {}),
                entities=analysis_json.get("entities", []),
                recommendations=analysis_json.get("recommendations", []),
                confidence_score=0.85,  # Placeholder
                processing_time=processing_time
            )
        
        except Exception as e:
            print(f"⚠️ Error generando análisis: {e}")
            return SupremeAnalysisResult(
                document_name=file_name,
                document_type="error",
                executive_summary=f"Error: {str(e)}",
                key_insights=[],
                risks_detected=[],
                opportunities_detected=[],
                critical_clauses=[],
                kpis_extracted={},
                entities=[],
                recommendations=[],
                confidence_score=0.0,
                processing_time=time.time() - start_time
            )
    
    def process_enterprise_documents_streaming(
        self,
        files: List,
        user_query: Optional[str] = None,
        auto_analyze: bool = True
    ) -> Iterator[str]:
        """Procesa documentos con streaming (modo híbrido)."""
        yield "## 🚀 Enterprise Supreme Mode - Procesamiento Iniciado\n\n"
        yield f"📄 Documentos recibidos: {len(files)}\n\n"
        
        try:
            # 1. Procesar documentos
            yield "### ⚙️ Procesando documentos...\n\n"
            docs = self.processor.process(files)
            yield f"✅ **Chunks generados**: {len(docs)}\n\n"
            
            if not docs:
                yield "❌ No se pudieron procesar los documentos.\n"
                return
            
            # 2. Construir retriever con embeddings grandes
            yield "### 🧠 Construyendo índice con embeddings grandes...\n\n"
            namespace = f"supreme_{uuid.uuid4().hex[:8]}"
            retriever = self.supreme_retriever_builder.build_hybrid_retriever(
                docs,
                namespace=namespace
            )
            yield "✅ **Índice construido** (text-embedding-3-large)\n\n"
            
            # 3. Análisis automático detallado (si está habilitado)
            if auto_analyze:
                yield "### 📊 Generando Análisis Detallado Automático...\n\n"
                
                # Agrupar documentos por archivo
                docs_by_file = defaultdict(list)
                for doc in docs:
                    source = doc.metadata.get("source", "unknown")
                    file_name = Path(source).name
                    docs_by_file[file_name].append(doc)
                
                # Analizar cada archivo en paralelo
                analyses = {}
                max_workers = min(3, len(docs_by_file))
                
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    future_to_file = {
                        executor.submit(self._generate_detailed_analysis, file_name, file_docs, retriever):
                        file_name
                        for file_name, file_docs in docs_by_file.items()
                    }
                    
                    for future in as_completed(future_to_file):
                        file_name = future_to_file[future]
                        try:
                            analysis = future.result()
                            analyses[file_name] = analysis
                            
                            # Emitir análisis inmediatamente
                            yield f"#### 📄 {analysis.document_name}\n\n"
                            yield f"**Tipo**: {analysis.document_type}\n\n"
                            yield f"**Resumen Ejecutivo**:\n{analysis.executive_summary}\n\n"
                            
                            if analysis.key_insights:
                                yield f"**💡 Insights Clave** ({len(analysis.key_insights)}):\n"
                                for i, insight in enumerate(analysis.key_insights[:10], 1):
                                    yield f"{i}. {insight}\n"
                                yield "\n"
                            
                            if analysis.risks_detected:
                                yield f"**⚠️ Riesgos Detectados** ({len(analysis.risks_detected)}):\n"
                                for risk in analysis.risks_detected[:5]:
                                    yield f"- **{risk.get('type', 'Unknown')}** ({risk.get('severity', 'N/A')}): {risk.get('description', 'N/A')}\n"
                                yield "\n"
                            
                            if analysis.opportunities_detected:
                                yield f"**💡 Oportunidades** ({len(analysis.opportunities_detected)}):\n"
                                for opp in analysis.opportunities_detected[:5]:
                                    yield f"- **{opp.get('type', 'Unknown')}**: {opp.get('description', 'N/A')}\n"
                                yield "\n"
                            
                            if analysis.recommendations:
                                yield f"**🎯 Recomendaciones** ({len(analysis.recommendations)}):\n"
                                for i, rec in enumerate(analysis.recommendations[:5], 1):
                                    yield f"{i}. {rec}\n"
                                yield "\n"
                            
                            yield "---\n\n"
                        
                        except Exception as e:
                            yield f"❌ Error analizando {file_name}: {str(e)[:100]}\n\n"
            
            # 4. Si hay query del usuario, responderla
            if user_query:
                yield f"### ❓ Respondiendo Consulta del Usuario\n\n"
                yield f"**Pregunta**: {user_query}\n\n"
                
                query_result = self._process_query_advanced(
                    query=user_query,
                    retriever=retriever,
                    docs=docs
                )
                
                yield f"**Respuesta**:\n{query_result.answer}\n\n"
                yield f"**Confianza**: {query_result.confidence:.2%}\n"
                yield f"**Consistencia**: {query_result.consistency_score:.2%}\n\n"
                
                if query_result.sources:
                    yield "**Fuentes**:\n"
                    for source in query_result.sources[:5]:
                        yield f"- {source.get('document', 'Unknown')}\n"
                    yield "\n"
            
            yield "\n✅ **Procesamiento completado exitosamente!**\n"
        
        except Exception as e:
            yield f"\n❌ **Error**: {str(e)}\n"
            import traceback
            traceback.print_exc()
    
    def _process_query_advanced(
        self,
        query: str,
        retriever: Any,
        docs: List[Document]
    ) -> SupremeQueryResult:
        """Procesa query con todas las optimizaciones."""
        start_time = time.time()
        
        # 1. Retrieval inicial (más documentos para reranking)
        retrieved_docs = retriever.invoke(query)
        
        # 2. Reranking avanzado
        if self.reranker and len(retrieved_docs) > 5:
            reranked_docs = self.reranker.rerank(query, retrieved_docs, top_k=10)
        else:
            reranked_docs = retrieved_docs[:10]
        
        # 3. Construir contexto
        context = "\n\n".join([
            f"=== DOCUMENTO: {doc.metadata.get('source', 'Unknown')} ===\n{doc.page_content[:1000]}"
            for doc in reranked_docs[:5]
        ])
        
        # 4. Chain-of-Thought reasoning
        thought_chain = self.chain_reasoner.reason(
            query=query,
            context=context
        )
        
        reasoning_steps = [step.thought for step in thought_chain.steps] if thought_chain else []
        
        # 5. Self-Consistency
        answer, consistency_score = self.consistency_reasoner.generate_consistent_answer(
            query=query,
            context=context,
            use_chain_of_thought=True
        )
        
        # 6. Calcular confianza
        confidence = min(0.95, 0.7 + (consistency_score * 0.25))
        
        # 7. Fuentes
        sources = [
            {
                "document": Path(doc.metadata.get("source", "Unknown")).name,
                "chunk": doc.page_content[:200],
                "relevance": "high" if i < 3 else "medium"
            }
            for i, doc in enumerate(reranked_docs[:5])
        ]
        
        return SupremeQueryResult(
            answer=answer,
            sources=sources,
            confidence=confidence,
            reasoning_chain=reasoning_steps,
            consistency_score=consistency_score,
            reranked_docs=reranked_docs,
            metadata={
                "processing_time": time.time() - start_time,
                "documents_retrieved": len(retrieved_docs),
                "documents_reranked": len(reranked_docs)
            }
        )
    
    def process_query(
        self,
        session_id: str,
        query: str,
        provider: str = "openai"
    ) -> SupremeQueryResult:
        """Procesa una consulta del usuario."""
        session = self.initialize_session(session_id)
        
        if not session["retriever"]:
            return SupremeQueryResult(
                answer="⚠️ No hay documentos procesados. Carga documentos primero.",
                sources=[],
                confidence=0.0,
                reasoning_chain=[],
                consistency_score=0.0,
                reranked_docs=[],
                metadata={}
            )
        
        # Actualizar LLM según provider
        self.llm = self._get_llm_for_provider(provider)
        self.consistency_reasoner.llm = self.llm
        self.chain_reasoner.llm = self.llm
        
        return self._process_query_advanced(
            query=query,
            retriever=session["retriever"],
            docs=session["docs"]
        )


# Funciones de interfaz
def get_enterprise_supreme_mode(
    config: AppConfig,
    processor: DocumentProcessor,
    retriever_builder: RetrieverBuilder,
    context_manager: Optional[Any] = None,
    provider: str = "openai"
) -> EnterpriseSupremeMode:
    """Obtiene instancia del modo Enterprise Supreme."""
    return EnterpriseSupremeMode(
        config=config,
        processor=processor,
        retriever_builder=retriever_builder,
        context_manager=context_manager,
        provider=provider
    )


def run_enterprise_supreme_mode_streaming(
    files: List,
    user_query: Optional[str] = None,
    auto_analyze: bool = True,
    provider: str = "openai"
) -> Iterator[str]:
    """Ejecuta el modo Enterprise Supreme con streaming."""
    from .config import load_config
    
    config = load_config()
    processor = DocumentProcessor(config)
    retriever_builder = RetrieverBuilder(config)
    
    supreme_mode = EnterpriseSupremeMode(
        config=config,
        processor=processor,
        retriever_builder=retriever_builder,
        provider=provider
    )
    
    yield from supreme_mode.process_enterprise_documents_streaming(
        files=files,
        user_query=user_query,
        auto_analyze=auto_analyze
    )






