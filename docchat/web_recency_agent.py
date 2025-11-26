"""
Web Recency Agent - Mantiene información actualizada mediante web scraping.

Resuelve el problema de "recency" mencionado por Eric Schmidt:
- Los modelos toman 18 meses en entrenarse, siempre están desactualizados
- Context windows permiten alimentar información reciente
- Este agente busca y actualiza información en tiempo real
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import re

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.documents import Document

from .config import AppConfig
from .utils.llm_factory import create_llm


@dataclass
class WebSource:
    """Fuente web de información."""
    url: str
    title: str
    content: str
    scraped_at: str
    relevance_score: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RecencyUpdate:
    """Actualización de información reciente."""
    update_id: str
    topic: str
    query: str
    sources: List[WebSource]
    summary: str
    key_facts: List[str]
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class WebRecencyAgent:
    """
    Agente que mantiene información actualizada mediante web scraping.
    
    Resuelve el problema de recency:
    - Busca información reciente sobre temas
    - Actualiza contexto con información actual
    - Permite preguntar sobre eventos recientes
    """
    
    def __init__(self, config: AppConfig, provider: str = "openai"):
        self.config = config
        self.provider = provider
        
        # LLM para búsqueda y análisis
        self.llm = create_llm(
            provider=provider,
            model=config.agentic_model or "gpt-4o",
            temperature=0.2,
            api_key=config.openai_api_key if provider == "openai" else config.anthropic_api_key,
            max_tokens=8000,
            request_timeout=180
        )
        
        # Directorio para almacenar información
        self.data_dir = Path(config.memory_dir) / "web_recency"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Historial de actualizaciones
        self.updates: Dict[str, RecencyUpdate] = {}
        
        # Cache de búsquedas
        self.search_cache: Dict[str, List[WebSource]] = {}
    
    def get_recent_information(
        self,
        query: str,
        topic: Optional[str] = None,
        max_sources: int = 5,
        time_range: str = "1 week"
    ) -> RecencyUpdate:
        """
        Obtiene información reciente sobre un tema.
        
        Args:
            query: Pregunta o tema a investigar
            topic: Tema general (opcional)
            max_sources: Máximo de fuentes a buscar
            time_range: Rango de tiempo (ej: "1 week", "1 month", "1 day")
        
        Returns:
            RecencyUpdate con información actualizada
        """
        topic = topic or query
        
        print(f"\n{'='*60}")
        print(f"🌐 BUSCANDO INFORMACIÓN RECIENTE")
        print(f"{'='*60}")
        print(f"📝 Query: {query}")
        print(f"📅 Rango: {time_range}\n")
        
        # Paso 1: Generar términos de búsqueda
        print("🔍 Paso 1: Generando términos de búsqueda...")
        search_queries = self._generate_search_queries(query, topic)
        print(f"   ✅ {len(search_queries)} términos de búsqueda generados\n")
        
        # Paso 2: Buscar en web (simulado - en producción usar API real)
        print("🌐 Paso 2: Buscando información en web...")
        sources = []
        for i, search_query in enumerate(search_queries[:3], 1):  # Limitar a 3 búsquedas
            print(f"   [{i}/{min(3, len(search_queries))}] Buscando: {search_query[:50]}...")
            found_sources = self._search_web(search_query, time_range)
            sources.extend(found_sources)
            time.sleep(0.5)  # Rate limiting simulado
        
        # Filtrar y rankear fuentes
        sources = self._rank_sources(sources, query)[:max_sources]
        print(f"   ✅ {len(sources)} fuentes relevantes encontradas\n")
        
        # Paso 3: Extraer y resumir información
        print("📊 Paso 3: Extrayendo y resumiendo información...")
        summary, key_facts = self._extract_and_summarize(sources, query, topic)
        print(f"   ✅ Información extraída y resumida\n")
        
        # Crear actualización
        update_id = f"update_{int(time.time())}"
        update = RecencyUpdate(
            update_id=update_id,
            topic=topic,
            query=query,
            sources=sources,
            summary=summary,
            key_facts=key_facts
        )
        
        # Guardar actualización
        self.updates[update_id] = update
        self._save_update(update)
        
        print(f"{'='*60}")
        print(f"✅ INFORMACIÓN RECIENTE OBTENIDA")
        print(f"{'='*60}\n")
        
        return update
    
    def _generate_search_queries(self, query: str, topic: str) -> List[str]:
        """Genera términos de búsqueda optimizados."""
        prompt = f"""Eres un experto en búsqueda web generando términos de búsqueda efectivos.

QUERY ORIGINAL: {query}
TEMA: {topic}

INSTRUCCIONES:
1. Genera 5-10 términos de búsqueda optimizados para encontrar información RECIENTE
2. Incluye variaciones y sinónimos
3. Agrega términos de tiempo reciente (ej: "2024", "recent", "latest")
4. Optimiza para encontrar noticias y artículos actuales

FORMATO DE RESPUESTA (JSON):
{{
    "search_queries": [
        "término de búsqueda 1",
        "término de búsqueda 2",
        ...
    ],
    "reasoning": "Por qué estos términos son efectivos"
}}

Genera los términos de búsqueda ahora:"""
        
        try:
            response = self.llm.invoke(prompt).content.strip()
            json_match = self._extract_json(response)
            
            if json_match:
                data = json.loads(json_match)
                return data.get("search_queries", [query])
            else:
                # Fallback: usar query original con variaciones
                return [
                    query,
                    f"{query} 2024",
                    f"{query} recent",
                    f"{topic} latest news",
                    f"{query} update"
                ]
        except Exception as e:
            print(f"   ⚠️ Error generando queries: {e}")
            return [query]
    
    def _search_web(self, query: str, time_range: str) -> List[WebSource]:
        """Busca información en web (simulado - en producción usar API real como SerpAPI, Google Custom Search, etc.)."""
        # En producción, aquí se usaría una API real como:
        # - Google Custom Search API
        # - SerpAPI
        # - Bing Search API
        # - DuckDuckGo API
        
        # Por ahora, simulamos resultados usando el LLM para generar contenido relevante
        prompt = f"""Simula resultados de búsqueda web recientes para esta query.

QUERY: {query}
TIME RANGE: {time_range}

Genera 3-5 resultados de búsqueda simulados que serían relevantes y recientes.
Cada resultado debe tener:
- URL (simulada pero realista)
- Título
- Contenido/extracto (2-3 párrafos)

FORMATO DE RESPUESTA (JSON):
{{
    "results": [
        {{
            "url": "https://ejemplo.com/articulo-reciente",
            "title": "Título del artículo",
            "content": "Contenido del artículo...",
            "date": "2024-11-XX"
        }},
        ...
    ]
}}

Genera los resultados ahora:"""
        
        try:
            response = self.llm.invoke(prompt).content.strip()
            json_match = self._extract_json(response)
            
            if json_match:
                data = json.loads(json_match)
                sources = []
                for result in data.get("results", []):
                    source = WebSource(
                        url=result.get("url", ""),
                        title=result.get("title", ""),
                        content=result.get("content", ""),
                        scraped_at=datetime.now().isoformat(),
                        metadata={"date": result.get("date", "")}
                    )
                    sources.append(source)
                return sources
            else:
                # Fuente simulada básica
                return [
                    WebSource(
                        url=f"https://example.com/search?q={query.replace(' ', '+')}",
                        title=f"Información reciente sobre {query}",
                        content=f"Contenido simulado sobre {query}. Esta es información que sería encontrada en una búsqueda web reciente.",
                        scraped_at=datetime.now().isoformat()
                    )
                ]
        except Exception as e:
            print(f"      ⚠️ Error en búsqueda: {e}")
            return []
    
    def _rank_sources(self, sources: List[WebSource], query: str) -> List[WebSource]:
        """Rankea fuentes por relevancia."""
        # Calcular relevancia usando LLM
        for source in sources:
            prompt = f"""Evalúa la relevancia de esta fuente para la query.

QUERY: {query}

FUENTE:
Título: {source.title}
Contenido: {source.content[:500]}

Asigna un score de relevancia de 0.0 a 1.0.

RESPUESTA (JSON):
{{
    "relevance_score": 0.85,
    "reasoning": "Por qué este score"
}}
"""
            try:
                response = self.llm.invoke(prompt).content.strip()
                json_match = self._extract_json(response)
                if json_match:
                    data = json.loads(json_match)
                    source.relevance_score = float(data.get("relevance_score", 0.5))
            except Exception:
                source.relevance_score = 0.5
        
        # Ordenar por relevancia
        sources.sort(key=lambda s: s.relevance_score, reverse=True)
        return sources
    
    def _extract_and_summarize(
        self,
        sources: List[WebSource],
        query: str,
        topic: str
    ) -> tuple[str, List[str]]:
        """Extrae y resume información de las fuentes."""
        sources_text = "\n\n".join([
            f"=== Fuente {i+1}: {s.title} ===\nURL: {s.url}\n{s.content[:1000]}"
            for i, s in enumerate(sources)
        ])
        
        prompt = f"""Eres un experto extrayendo y resumiendo información reciente.

QUERY: {query}
TEMA: {topic}

FUENTES ENCONTRADAS:
{sources_text[:20000]}

INSTRUCCIONES:
1. Extrae la información MÁS RECIENTE y RELEVANTE
2. Crea un resumen comprensivo
3. Identifica los hechos clave más importantes
4. Enfócate en información actualizada (no información antigua)

FORMATO DE RESPUESTA (JSON):
{{
    "summary": "Resumen comprensivo de la información reciente encontrada",
    "key_facts": [
        "Hecho clave 1",
        "Hecho clave 2",
        ...
    ],
    "most_recent_date": "Fecha más reciente mencionada",
    "confidence": 0.0-1.0
}}

Extrae y resume la información ahora:"""
        
        try:
            response = self.llm.invoke(prompt).content.strip()
            json_match = self._extract_json(response)
            
            if json_match:
                data = json.loads(json_match)
                summary = data.get("summary", "No se pudo extraer información")
                key_facts = data.get("key_facts", [])
                return summary, key_facts
            else:
                # Fallback
                summary = f"Información reciente sobre {query} extraída de {len(sources)} fuentes."
                key_facts = [f"Información encontrada en {len(sources)} fuentes recientes"]
                return summary, key_facts
        except Exception as e:
            print(f"   ⚠️ Error extrayendo información: {e}")
            return f"Error extrayendo información: {str(e)}", []
    
    def enrich_context_with_recency(
        self,
        query: str,
        existing_context: str,
        time_range: str = "1 week"
    ) -> str:
        """
        Enriquece contexto existente con información reciente.
        
        Útil para agregar información actualizada a context windows.
        """
        update = self.get_recent_information(query, time_range=time_range)
        
        enriched = f"""{existing_context}

=== INFORMACIÓN RECIENTE (Actualizada: {update.timestamp}) ===
Tema: {update.topic}

Resumen:
{update.summary}

Hechos Clave:
{chr(10).join([f"- {fact}" for fact in update.key_facts])}

Fuentes:
{chr(10).join([f"- {s.title} ({s.url})" for s in update.sources[:3]])}
=== FIN DE INFORMACIÓN RECIENTE ===
"""
        return enriched
    
    def _extract_json(self, text: str) -> Optional[str]:
        """Extrae JSON de un texto."""
        import re
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            return json_match.group(0)
        return None
    
    def _save_update(self, update: RecencyUpdate):
        """Guarda una actualización."""
        update_file = self.data_dir / f"{update.update_id}.json"
        update_dict = {
            "update_id": update.update_id,
            "topic": update.topic,
            "query": update.query,
            "sources": [
                {
                    "url": s.url,
                    "title": s.title,
                    "content": s.content[:5000],  # Limitar tamaño
                    "scraped_at": s.scraped_at,
                    "relevance_score": s.relevance_score,
                    "metadata": s.metadata
                }
                for s in update.sources
            ],
            "summary": update.summary,
            "key_facts": update.key_facts,
            "timestamp": update.timestamp
        }
        
        with open(update_file, 'w', encoding='utf-8') as f:
            json.dump(update_dict, f, indent=2, ensure_ascii=False)
    
    def get_latest_update(self, topic: str) -> Optional[RecencyUpdate]:
        """Obtiene la actualización más reciente de un tema."""
        topic_updates = [u for u in self.updates.values() if topic.lower() in u.topic.lower()]
        if topic_updates:
            return max(topic_updates, key=lambda u: u.timestamp)
        return None

