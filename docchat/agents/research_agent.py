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
            request_timeout=180  # Timeout de 3 minutos para respuestas largas
        )
        self.speed_mode = speed_mode
        self.base_max_tokens = max_tokens

    def run(self, question: str, documents: List[Document], conversational_mode: bool = False) -> ResearchResult:
        # Para modo conversacional, crear un LLM con más tokens para respuestas MUY largas
        if conversational_mode:
            # Crear LLM especial para modo conversacional con 8000 tokens
            conversational_llm = ChatOpenAI(
                model=self.llm.model_name,
                temperature=self.llm.temperature,
                max_tokens=8000,  # Respuestas MUY largas y completas
                max_retries=3,
                request_timeout=180
            )
            llm_to_use = conversational_llm
        else:
            llm_to_use = self.llm
        
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
        # Conversational: MÁXIMO contexto posible para respuestas completas
        if conversational_mode:
            max_context_chars = 120000  # ~30,000 tokens - MÁXIMO contexto para respuestas super completas
        elif self.speed_mode == "fast":
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
        
        # Prompt SUPER MEJORADO para chat conversacional (respuestas MUY largas, completas e inteligentes)
        if conversational_mode:
            prompt = (
                "Eres un asistente experto de nivel mundial con conocimiento profundo en múltiples áreas. "
                "Tu objetivo es proporcionar respuestas EXTREMADAMENTE COMPLETAS, DETALLADAS Y PERFECTAS. "
                "Piensa como un investigador senior, un consultor estratégico y un experto técnico combinados.\n\n"
                f"PREGUNTA DEL USUARIO:\n{question}\n\n"
                f"CONTEXTO COMPLETO DE LOS DOCUMENTOS ({num_sources} documento(s) con {len(documents)} fragmentos):\n{context}\n\n"
                "INSTRUCCIONES CRÍTICAS PARA UNA RESPUESTA PERFECTA:\n\n"
                "1. PROFUNDIDAD Y COMPLETITUD:\n"
                "   - Proporciona una respuesta EXTREMADAMENTE DETALLADA y COMPLETA\n"
                "   - No te limites a responder solo la pregunta directa, EXPLORA todos los aspectos relacionados\n"
                "   - Incluye contexto, antecedentes, implicaciones y consecuencias\n"
                "   - Mínimo 800-1500 palabras (respuestas MUY largas y completas)\n\n"
                "2. ANÁLISIS INTELIGENTE:\n"
                "   - Analiza la pregunta desde múltiples perspectivas (técnica, estratégica, práctica)\n"
                "   - Identifica patrones, conexiones y relaciones entre diferentes partes de los documentos\n"
                "   - Extrae insights profundos que no son obvios a primera vista\n"
                "   - Proporciona análisis comparativo si hay múltiples documentos\n\n"
                "3. INFORMACIÓN ESPECÍFICA Y PRECISA:\n"
                "   - Cita información específica de los documentos (números, fechas, nombres, datos concretos)\n"
                "   - Menciona de qué documento viene cada pieza de información\n"
                "   - Incluye ejemplos concretos y casos específicos mencionados en los documentos\n"
                "   - Proporciona detalles técnicos cuando sean relevantes\n\n"
                "4. ESTRUCTURA NATURAL PERO COMPLETA:\n"
                "   - Responde de forma conversacional y natural, como un experto explicando a un colega\n"
                "   - Organiza la información de manera lógica y fluida\n"
                "   - Usa párrafos bien desarrollados (no listas de viñetas simples)\n"
                "   - Conecta ideas de manera fluida y natural\n\n"
                "5. PERSPECTIVA ESTRATÉGICA:\n"
                "   - No solo digas QUÉ, explica POR QUÉ y CÓMO\n"
                "   - Incluye implicaciones prácticas y recomendaciones cuando sea apropiado\n"
                "   - Proporciona contexto sobre la importancia o relevancia de la información\n"
                "   - Conecta la información con conceptos más amplios cuando sea relevante\n\n"
                "6. EXHAUSTIVIDAD:\n"
                "   - Cubre TODOS los aspectos relevantes de la pregunta\n"
                "   - Si hay múltiples documentos, analiza información de TODOS ellos\n"
                "   - No omitas información importante aunque la pregunta no la mencione explícitamente\n"
                "   - Incluye información relacionada que pueda ser útil para entender mejor el tema\n\n"
                "7. CALIDAD DE ESCRITURA:\n"
                "   - Escribe de manera clara, profesional y sofisticada\n"
                "   - Usa un vocabulario rico y preciso\n"
                "   - Varía la estructura de las oraciones para mantener el interés\n"
                "   - Asegúrate de que cada párrafo aporte valor significativo\n\n"
                "8. VERIFICACIÓN:\n"
                "   - Solo usa información que esté explícitamente en los documentos\n"
                "   - Si algo no está claro en los documentos, indícalo pero proporciona el contexto disponible\n"
                "   - No inventes información, pero sé creativo en cómo la presentas y conectas\n\n"
                "IMPORTANTE: Esta respuesta debe ser EXTREMADAMENTE COMPLETA, DETALLADA Y PERFECTA. "
                "Piensa como si estuvieras escribiendo un análisis profesional de nivel ejecutivo. "
                "La respuesta debe ser tan completa que el usuario no necesite hacer preguntas de seguimiento "
                "para entender completamente el tema.\n\n"
                "RESPUESTA COMPLETA Y DETALLADA (mínimo 800-1500 palabras):"
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
                if conversational_mode:
                    print(f"   🧠 Generando respuesta SUPER COMPLETA en modo conversacional (puede tardar 3-5 minutos)...")
                answer = llm_to_use.invoke(prompt).content.strip()
                print(f"   ✅ Respuesta generada exitosamente ({len(answer)} caracteres)")
                if conversational_mode:
                    print(f"   📊 Respuesta completa generada: {len(answer.split())} palabras aproximadamente\n")
                else:
                    print()
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

