from __future__ import annotations

from dataclasses import dataclass
from typing import List

from langchain_core.documents import Document
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from docchat.utils.llm_factory import create_llm


@dataclass(slots=True)
class ResearchResult:
    answer: str
    context: str


class ResearchAgent:
    def __init__(self, model_name: str, temperature: float = 0.2, max_tokens: int = 16000, speed_mode: str = "balanced", provider: str = "openai", config=None):
        # max_tokens AUMENTADO para respuestas MUY largas y detalladas
        # Total permitido: 27,000 tokens (15,000 docs + 12,000 respuesta)
        # Fast: 10000 tokens (aumentado para respuestas más completas)
        # Balanced: 15000 tokens (aumentado para llegar a 27,000 total)
        # Quality: 16000 tokens (máxima calidad - máximo permitido)
        if speed_mode == "fast":
            max_tokens = min(10000, max_tokens)  # Aumentado de 8000 a 10000
        elif speed_mode == "balanced":
            max_tokens = min(15000, max_tokens)  # Aumentado de 12000 a 15000
        # Quality mode usa el max_tokens original (16000)
        
        # Agregar retry con backoff para manejar rate limits
        self.provider = provider
        self.config = config
        api_key = None
        if config:
            if provider == "groq":
                api_key = config.groq_api_key
            elif provider == "claude":
                api_key = config.anthropic_api_key
            else:
                api_key = config.openai_api_key
        
        self.llm = create_llm(
            provider=provider,
            model=model_name,
            temperature=temperature,
            max_tokens=max_tokens,
            api_key=api_key,
            request_timeout=180,
            max_retries=3
        )
        self.speed_mode = speed_mode
        self.base_max_tokens = max_tokens

    def run(self, question: str, documents: List[Document], conversational_mode: bool = False) -> ResearchResult:
        # Para modo conversacional, crear un LLM con más tokens para respuestas MUY largas
        if conversational_mode:
            # Crear LLM especial para modo conversacional con 16000 tokens (aprovecha context window grande)
            model_name = self.llm.model_name if hasattr(self.llm, 'model_name') else (self.llm.model if hasattr(self.llm, 'model') else "gpt-4o")
            temperature = self.llm.temperature if hasattr(self.llm, 'temperature') else 0.15
            api_key = None
            if self.config:
                api_key = self.config.openai_api_key if self.provider == "openai" else self.config.anthropic_api_key
            
            # Aumentar max_tokens para modo conversacional (respuestas MUY largas)
            # Total permitido: 27,000 tokens (15,000 docs + 12,000-15,000 respuesta)
            conversational_max_tokens = 16000 if self.speed_mode == "quality" else (15000 if self.speed_mode == "balanced" else 10000)
            conversational_llm = create_llm(
                provider=self.provider,
                model=model_name,
                temperature=temperature,
                max_tokens=conversational_max_tokens,
                api_key=api_key,
                request_timeout=180,
                max_retries=3
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
        # OPTIMIZADO para soportar hasta 1000 PDFs en una sola consulta
        num_sources = len(docs_by_source)
        
        # Calcular límite por documento basado en el número total de documentos
        # ESTRATEGIA: Asegurar que TODOS los documentos tengan contenido representativo
        # Para preguntas generales, es crítico incluir información de todos los documentos
        if num_sources > 500:
            # Para 500+ documentos: ~400 caracteres por documento
            chars_per_doc = 400
            max_chunk_size = 300
        elif num_sources > 200:
            # Para 200-500 documentos: ~800 caracteres por documento
            chars_per_doc = 800
            max_chunk_size = 600
        elif num_sources > 100:
            # Para 100-200 documentos: ~1200 caracteres por documento
            chars_per_doc = 1200
            max_chunk_size = 800
        elif num_sources > 50:
            # Para 50-100 documentos: ~1500 caracteres por documento
            chars_per_doc = 1500
            max_chunk_size = 1000
        elif num_sources > 20:
            # Para 20-50 documentos: ~2000 caracteres por documento
            chars_per_doc = 2000
            max_chunk_size = 1200
        else:
            # Para <20 documentos: máximo contenido por documento para análisis completo
            chars_per_doc = 2500
            max_chunk_size = 1500
        
        context_parts = []
        for source, docs in docs_by_source.items():
            source_chunks = []
            for doc in docs:
                content = doc.page_content
                if len(content) > max_chunk_size:
                    content = content[:max_chunk_size] + "..."
                source_chunks.append(content)
            source_content = "\n\n".join(source_chunks)
            # Limitar el contenido total por documento según número de documentos
            if len(source_content) > chars_per_doc:
                source_content = source_content[:chars_per_doc] + "..."
            context_parts.append(f"=== DOCUMENTO: {source} ===\n{source_content}")
        
        context = "\n\n".join(context_parts)
        
        # Limitar el contexto según modo de velocidad - AJUSTADO para cumplir límite de 30,000 TPM de OpenAI
        # Límite real de OpenAI gpt-4o: 30,000 TPM (tokens per minute)
        # AUMENTADO: Total de 27,000 tokens (15,000 docs + 12,000 respuesta)
        # Aproximación: 1 token ≈ 4 caracteres
        if conversational_mode:
            # Modo conversacional: límite aumentado para incluir más documentos
            max_context_chars = 100000  # ~25,000 tokens (dejando 2,000 para prompt base)
        elif self.speed_mode == "fast":
            max_context_chars = 60000  # ~15,000 tokens (aumentado)
        elif self.speed_mode == "balanced":
            max_context_chars = 80000  # ~20,000 tokens (aumentado para llegar a 27,000 total)
        else:  # quality
            max_context_chars = 100000  # ~25,000 tokens (aumentado)
        
        if len(context) > max_context_chars:
            context = context[:max_context_chars] + "\n\n[Contexto truncado para cumplir límite de tokens (30,000 TPM)]"
        
        num_sources = len(docs_by_source)
        print(f"   Analizando {num_sources} documento(s) con {len(documents)} chunks totales...")
        print(f"   Generando respuesta (esto puede tardar 2-5 minutos)...\n")
        
        # Prompt SUPER MEJORADO para chat conversacional (respuestas MUY largas, completas e inteligentes)
        # CON CHAIN OF THOUGHT REASONING Y MEMORIA A CORTO PLAZO (CONTEXT WINDOW)
        if conversational_mode:
            prompt = (
                "Eres un asistente experto de nivel mundial con conocimiento profundo en múltiples áreas. "
                "Tu objetivo es proporcionar respuestas EXTREMADAMENTE COMPLETAS, DETALLADAS Y PERFECTAS. "
                "Piensa como un investigador senior, un consultor estratégico y un experto técnico combinados.\n\n"
                "🧠 MEMORIA A CORTO PLAZO (CONTEXT WINDOW):\n"
                "Tienes acceso a un context window grande (128k-200k tokens) que actúa como tu memoria a corto plazo.\n"
                "Si la pregunta incluye 'CONTEXTO DE CONVERSACIÓN ANTERIOR', ese es tu historial completo de conversaciones previas.\n"
                "Úsalo para entender referencias a conversaciones anteriores, preguntas de seguimiento, y contexto completo.\n"
                "Esta memoria a corto plazo te permite mantener hasta 20-50 interacciones anteriores en contexto.\n\n"
                "🧠 MÉTODO DE RAZONAMIENTO (CHAIN OF THOUGHT):\n"
                "DEBES razonar paso a paso antes de responder. Sigue este proceso:\n"
                "1. ANÁLISIS INICIAL: Identifica qué se está preguntando y qué información necesitas\n"
                "2. REVISAR MEMORIA: Si hay contexto de conversación anterior, revísalo para entender el contexto completo\n"
                "3. EXPLORACIÓN: Revisa todos los documentos para encontrar información relevante\n"
                "4. CONEXIÓN: Identifica relaciones, patrones y conexiones entre diferentes partes\n"
                "5. SÍNTESIS: Organiza la información de manera lógica y coherente\n"
                "6. VERIFICACIÓN: Asegúrate de que tu respuesta sea completa y precisa\n\n"
                f"{question}\n\n"
                f"CONTEXTO COMPLETO DE LOS DOCUMENTOS ({num_sources} documento(s) con {len(documents)} fragmentos):\n{context}\n\n"
                "INSTRUCCIONES CRÍTICAS PARA UNA RESPUESTA PERFECTA:\n\n"
                "1. PROFUNDIDAD Y COMPLETITUD - CRÍTICO:\n"
                "   - Proporciona una respuesta EXTREMADAMENTE DETALLADA y COMPLETA\n"
                "   - No te limites a responder solo la pregunta directa, EXPLORA todos los aspectos relacionados\n"
                "   - Incluye contexto, antecedentes, implicaciones y consecuencias\n"
                "   - Mínimo 2000-3000 palabras para análisis de múltiples documentos (respuestas MUY largas y completas)\n"
                "   - Si hay 17 documentos, la respuesta debe tener al menos 3000-4000 palabras\n"
                "   - Cada documento debe tener un análisis de al menos 200-300 palabras\n"
                "   - NO escribas respuestas cortas. Sé exhaustivo y detallado.\n\n"
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
                "6. EXHAUSTIVIDAD Y COBERTURA COMPLETA:\n"
                "   - Cubre TODOS los aspectos relevantes de la pregunta\n"
                "   - Si hay múltiples documentos, analiza información de TODOS ellos\n"
                "   - IMPORTANTE: Debes mencionar o analizar información de CADA documento proporcionado\n"
                "   - Si hay 17 documentos, debes incluir información de los 17, no solo de unos pocos\n"
                "   - Para cada documento, identifica al menos un punto clave o información valiosa\n"
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
                "CRÍTICO: Si hay múltiples documentos, cada uno debe tener un análisis profundo de al menos 200-300 palabras. "
                "NO escribas solo un párrafo por documento. Sé exhaustivo, detallado y completo.\n\n"
                "RESPUESTA COMPLETA Y DETALLADA (mínimo 2000-3000 palabras para múltiples documentos):"
            )
        else:
            # Prompt original para otros modos (Consulta RAG, etc.) CON CHAIN OF THOUGHT REASONING
            prompt = (
                "Eres un investigador experto en análisis de documentos. Tu tarea es analizar TODOS los documentos proporcionados de manera exhaustiva.\n\n"
                "🧠 MÉTODO DE RAZONAMIENTO (CHAIN OF THOUGHT):\n"
                "DEBES razonar paso a paso antes de responder:\n"
                "1. Identifica qué información se necesita de los documentos\n"
                "2. Revisa cada documento sistemáticamente\n"
                "3. Extrae información relevante de cada uno\n"
                "4. Organiza la información de manera lógica\n"
                "5. Verifica que hayas cubierto todos los documentos\n\n"
                f"CONTEXTO DE CONVERSACIÓN (si está presente arriba, úsalo como memoria a corto plazo):\n"
                f"La pregunta puede hacer referencia a consultas anteriores.\n"
                f"Si hay contexto de conversación anterior, úsalo para entender el contexto completo.\n\n"
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

        # TRUNCAMIENTO FINAL DEL PROMPT: Asegurar que el prompt completo no exceda 20,000 tokens
        # Límite de OpenAI gpt-4o: 30,000 TPM, usamos 20,000 como límite MUY seguro
        MAX_PROMPT_TOKENS = 20000
        estimated_prompt_tokens = len(prompt) // 4  # Aproximación: 1 token = 4 caracteres
        
        if estimated_prompt_tokens > MAX_PROMPT_TOKENS:
            # Calcular cuántos caracteres podemos usar
            max_prompt_chars = MAX_PROMPT_TOKENS * 4 * 0.95  # 95% para margen
            max_prompt_chars = int(max_prompt_chars)
            
            # Truncar el contexto dentro del prompt, manteniendo la pregunta y las instrucciones
            if "CONTEXTO COMPLETO DE LOS DOCUMENTOS" in prompt:
                # Separar prompt base del contexto
                parts = prompt.split("CONTEXTO COMPLETO DE LOS DOCUMENTOS")
                prompt_base = parts[0]
                context_part = parts[1] if len(parts) > 1 else ""
                
                # Calcular espacio disponible para contexto
                base_tokens = len(prompt_base) // 4
                available_tokens = MAX_PROMPT_TOKENS - base_tokens - 1000  # Margen
                available_chars = available_tokens * 4
                
                if available_chars > 0 and len(context_part) > available_chars:
                    # Truncar contexto manteniendo el inicio (más relevante)
                    truncated_context = context_part[:int(available_chars * 0.9)]
                    truncated_context += "\n\n[... contexto truncado para cumplir límite de 30,000 TPM ...]"
                    prompt = prompt_base + "CONTEXTO COMPLETO DE LOS DOCUMENTOS" + truncated_context
                    print(f"⚠️ [ResearchAgent] Prompt truncado: {estimated_prompt_tokens} → ~{MAX_PROMPT_TOKENS} tokens")
            else:
                # Si no hay sección de contexto, truncar desde el final
                prompt = prompt[:max_prompt_chars] + "\n\n[... prompt truncado ...]"

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
                    print(f"   🧠 Generando respuesta SUPER COMPLETA con Chain of Thought reasoning (puede tardar 3-5 minutos)...")
                else:
                    print(f"   🧠 Generando respuesta con Chain of Thought reasoning...")
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

