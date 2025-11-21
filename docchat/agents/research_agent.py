from __future__ import annotations

from dataclasses import dataclass
from typing import List

from langchain_core.documents import Document
from langchain_openai import ChatOpenAI


@dataclass(slots=True)
class ResearchResult:
    answer: str
    context: str


class ResearchAgent:
    def __init__(self, model_name: str, temperature: float = 0.2, max_tokens: int = 4000):
        # Aumentado a 4000 tokens para permitir respuestas más completas y detalladas
        # Agregar retry con backoff para manejar rate limits
        self.llm = ChatOpenAI(
            model=model_name, 
            temperature=temperature, 
            max_tokens=max_tokens,
            max_retries=3,  # Reintentar hasta 3 veces
            request_timeout=120  # Timeout de 2 minutos
        )

    def run(self, question: str, documents: List[Document]) -> ResearchResult:
        if not documents:
            return ResearchResult(
                answer="No encontré suficiente información en los documentos para responder.",
                context="",
            )

        # Agrupar documentos por fuente para mejor análisis
        docs_by_source = {}
        for doc in documents:
            source = doc.metadata.get("source", "documento desconocido")
            if source not in docs_by_source:
                docs_by_source[source] = []
            docs_by_source[source].append(doc)
        
        # Construir contexto con información de múltiples fuentes
        # Limitar el tamaño de cada chunk para evitar exceder límites de tokens
        context_parts = []
        for source, docs in docs_by_source.items():
            # Limitar cada chunk a 500 caracteres para reducir tokens
            source_chunks = []
            for doc in docs:
                content = doc.page_content
                if len(content) > 1000:  # Truncar chunks muy largos
                    content = content[:1000] + "..."
                source_chunks.append(content)
            source_content = "\n\n".join(source_chunks)
            # Limitar el contenido total por documento
            if len(source_content) > 2000:
                source_content = source_content[:2000] + "..."
            context_parts.append(f"=== DOCUMENTO: {source} ===\n{source_content}")
        
        context = "\n\n".join(context_parts)
        
        # Limitar el contexto total a ~15,000 tokens (estimado)
        # Cada token ≈ 4 caracteres, entonces ~60,000 caracteres máximo
        if len(context) > 60000:
            context = context[:60000] + "\n\n[Contexto truncado para evitar límites de tokens]"
        
        num_sources = len(docs_by_source)
        prompt = (
            "Eres un investigador experto en análisis de documentos. Tu tarea es analizar TODOS los documentos proporcionados de manera exhaustiva.\n\n"
            f"PREGUNTA DEL USUARIO:\n{question}\n\n"
            f"DOCUMENTOS A ANALIZAR ({num_sources} documento(s) diferente(s)):\n{context}\n\n"
            "INSTRUCCIONES CRÍTICAS:\n"
            "1. DEBES analizar CADA UNO de los documentos proporcionados\n"
            "2. Para cada documento, identifica y extrae:\n"
            "   - Título o tema principal\n"
            "   - Puntos clave (mínimo 3-5 por documento)\n"
            "   - Información más valiosa o insights principales\n"
            "   - Conclusiones o recomendaciones importantes\n"
            "3. Organiza tu respuesta por documento, usando el nombre del archivo como encabezado\n"
            "4. NO omitas ningún documento - todos deben ser analizados\n"
            "5. Si un documento tiene poca información, indícalo pero aún así extrae lo que puedas\n"
            "6. Responde en español, con precisión y sin inventar datos\n"
            "7. Sé específico y detallado - evita respuestas genéricas\n\n"
            "FORMATO DE RESPUESTA REQUERIDO:\n"
            "Para cada documento, estructura así:\n"
            "## [Nombre del Documento]\n"
            "- **Tema Principal:** [descripción]\n"
            "- **Puntos Clave:**\n"
            "  1. [punto 1]\n"
            "  2. [punto 2]\n"
            "  3. [punto 3]\n"
            "- **Información Más Valiosa:** [insights principales]\n\n"
            "RESPUESTA COMPLETA:"
        )

        # LangChain 1.0+ uses invoke() instead of predict()
        # Manejar rate limits con retry
        import time
        max_retries = 3
        retry_delay = 2  # segundos
        
        for attempt in range(max_retries):
            try:
                answer = self.llm.invoke(prompt).content.strip()
                return ResearchResult(answer=answer, context=context)
            except Exception as e:
                error_str = str(e).lower()
                if "rate limit" in error_str or "429" in error_str or "too many requests" in error_str or "tpm" in error_str:
                    if attempt < max_retries - 1:
                        wait_time = retry_delay * (2 ** attempt)  # Exponential backoff
                        print(f"⚠️ Rate limit alcanzado. Esperando {wait_time}s antes de reintentar...")
                        time.sleep(wait_time)
                        continue
                    else:
                        raise Exception(
                            "Error: Límite de tasa de OpenAI excedido. El contexto es demasiado grande.\n"
                            "Solución: Intenta con menos documentos o espera unos minutos antes de volver a intentar."
                        )
                else:
                    raise  # Re-raise si no es un error de rate limit

