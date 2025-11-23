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
    def __init__(self, model_name: str, temperature: float = 0.2, max_tokens: int = 4000, speed_mode: str = "balanced"):
        # max_tokens ajustado según modo de velocidad
        # Balanced: 3000 tokens (suficiente para respuestas completas, más rápido)
        # Quality: 4000 tokens (máxima calidad)
        # Fast: 2000 tokens (más rápido, respuestas más concisas)
        if speed_mode == "fast":
            max_tokens = min(2000, max_tokens)
        elif speed_mode == "balanced":
            max_tokens = min(3000, max_tokens)
        # Quality mode usa el max_tokens original (4000)
        
        # Agregar retry con backoff para manejar rate limits
        self.llm = ChatOpenAI(
            model=model_name, 
            temperature=temperature, 
            max_tokens=max_tokens,
            max_retries=3,  # Reintentar hasta 3 veces
            request_timeout=120  # Timeout de 2 minutos
        )
        self.speed_mode = speed_mode

    def run(self, question: str, documents: List[Document], conversational_mode: bool = False) -> ResearchResult:
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
        
        # Limitar el contexto según modo de velocidad
        # Fast: menos contexto, más rápido
        # Balanced: contexto moderado
        # Quality: máximo contexto
        if self.speed_mode == "fast":
            max_context_chars = 40000  # ~10,000 tokens
        elif self.speed_mode == "balanced":
            max_context_chars = 60000  # ~15,000 tokens
        else:  # quality
            max_context_chars = 80000  # ~20,000 tokens
        
        if len(context) > max_context_chars:
            context = context[:max_context_chars] + "\n\n[Contexto truncado para optimizar velocidad]"
        
        num_sources = len(docs_by_source)
        print(f"   Analizando {num_sources} documento(s) con {len(documents)} chunks totales...")
        print(f"   Generando respuesta (esto puede tardar 2-5 minutos)...\n")
        
        # Prompt diferente para chat conversacional (más libre y natural)
        if conversational_mode:
            prompt = (
                "Eres un asistente experto que ayuda a los usuarios a entender y explorar documentos. "
                "Responde de manera natural, conversacional y directa, como si estuvieras teniendo una conversación.\n\n"
                f"PREGUNTA DEL USUARIO:\n{question}\n\n"
                f"CONTEXTO DE LOS DOCUMENTOS ({num_sources} documento(s)):\n{context}\n\n"
                "INSTRUCCIONES:\n"
                "1. Responde de forma natural y conversacional, como en una charla\n"
                "2. Sé directo y claro, sin estructuras rígidas\n"
                "3. Usa el contexto de los documentos para responder la pregunta específica\n"
                "4. Si la pregunta requiere comparar o analizar múltiples documentos, hazlo de forma fluida\n"
                "5. Incluye información específica y relevante de los documentos\n"
                "6. Responde en español de manera natural\n"
                "7. NO uses formatos estructurados como 'Tema Principal', 'Puntos Clave', etc.\n"
                "8. Simplemente responde la pregunta de manera clara y útil\n\n"
                "RESPUESTA:"
            )
        else:
            # Prompt original para otros modos (Consulta RAG, etc.)
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
                if attempt > 0:
                    print(f"   Reintentando generación de respuesta (intento {attempt + 1}/{max_retries})...")
                answer = self.llm.invoke(prompt).content.strip()
                print(f"   ✅ Respuesta generada exitosamente ({len(answer)} caracteres)\n")
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

