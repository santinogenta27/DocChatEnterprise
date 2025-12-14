"""
Agentic AI para Advertising - Basado en MindFuse Framework
Implementa el sistema completo de co-creación estratégica de marketing con GenAI explicable.

Basado en: "MindFuse: Towards GenAI Explainability in Marketing Strategy Co-Creation"
"""

from __future__ import annotations

import json
import time
from typing import List, Dict, Optional, Any, Tuple
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from dataclasses import dataclass, field

import numpy as np
try:
    from sklearn.cluster import KMeans
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    # Fallback simple clustering
    class KMeans:
        def __init__(self, n_clusters=2, random_state=42, n_init=10):
            self.n_clusters = n_clusters
        def fit_predict(self, X):
            # Clustering simple basado en distancia
            n_samples = len(X)
            if n_samples <= self.n_clusters:
                return np.arange(n_samples)
            # Dividir en clusters simples
            labels = np.arange(n_samples) % self.n_clusters
            return labels

from langchain_core.language_models import BaseLanguageModel
from langchain_openai import ChatOpenAI
from langchain_openai import OpenAIEmbeddings

from .config import AppConfig


@dataclass
class ContentPillar:
    """Pilar de contenido extraído de un anuncio."""
    customer_need: str
    product_category: str
    emotional_appeal: str
    stylistic_tone: str
    target_audience: str
    value_proposition: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CustomerPersona:
    """Persona de cliente identificada mediante clustering."""
    persona_id: str
    name: str
    description: str
    psychological_profile: str
    behavioral_patterns: List[str]
    content_items: List[str] = field(default_factory=list)
    cluster_size: int = 0


@dataclass
class ThematicChallenge:
    """Desafío temático identificado en las campañas."""
    challenge_id: str
    name: str
    description: str
    pain_points: List[str]
    value_propositions: List[str]
    content_items: List[str] = field(default_factory=list)
    cluster_size: int = 0


@dataclass
class CampaignNarrative:
    """Narrativa estratégica generada combinando persona + desafío."""
    narrative_id: str
    persona: CustomerPersona
    challenge: ThematicChallenge
    story: str
    campaign_insight: str
    creative_direction: str
    target_messaging: str
    generated_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class ContentScore:
    """Score predictivo de contenido con explicabilidad."""
    creative_id: str
    predicted_ctr: float
    predicted_cpr: float
    confidence: float
    attention_heatmap: Optional[Dict[str, Any]] = None
    high_impact_regions: List[Dict[str, Any]] = field(default_factory=list)
    optimization_suggestions: List[str] = field(default_factory=list)


@dataclass
class CampaignMetrics:
    """Métricas de campaña para análisis de performance."""
    reach: int
    frequency: float
    results: int
    cost_per_result: float
    spend: float
    cpm: float
    ctr: float
    click_to_view: float
    click_to_result: float
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class PerformanceInsight:
    """Insight estratégico generado por el agente de performance."""
    insight_id: str
    metric_disruption: str
    causal_analysis: str
    strategic_recommendation: str
    tactical_actions: List[str]
    confidence: float
    generated_at: str = field(default_factory=lambda: datetime.now().isoformat())


class ContentPillarExtractor:
    """
    Extrae pilares de contenido de anuncios usando LLMs.
    Implementa la Sección 2 del paper MindFuse.
    """
    
    def __init__(self, config: AppConfig, llm: Optional[BaseLanguageModel] = None):
        self.config = config
        self.llm = llm or ChatOpenAI(
            model=config.research_model or "gpt-4o",
            temperature=0.2,
            api_key=config.openai_api_key,
            max_tokens=2000
        )
    
    def extract_pillars(self, ad_content: Dict[str, Any]) -> ContentPillar:
        """
        Extrae pilares semánticos estructurados de un anuncio.
        
        Args:
            ad_content: Diccionario con 'text', 'image_url', 'metadata', etc.
        
        Returns:
            ContentPillar con atributos estructurados
        """
        prompt = f"""Eres un analista estratégico de marketing de nivel C-Suite. 
Analiza este anuncio y extrae los siguientes pilares de contenido estructurados:

CONTENIDO DEL ANUNCIO:
Texto: {ad_content.get('text', 'N/A')}
Imagen: {ad_content.get('image_url', 'N/A')}
Metadata: {ad_content.get('metadata', {})}

INSTRUCCIONES:
Extrae los siguientes pilares de contenido (responde en formato JSON):

1. **customer_need**: ¿Cuál es la necesidad humana subyacente que este anuncio está dirigiendo?
2. **product_category**: ¿Qué categoría de producto se está promocionando?
3. **emotional_appeal**: ¿Qué apelación emocional se está utilizando? (ej: miedo, aspiracional, urgencia, etc.)
4. **stylistic_tone**: ¿Cuál es el tono estilístico del mensaje? (ej: profesional, casual, urgente, etc.)
5. **target_audience**: ¿Qué audiencia está siendo dirigida? Describe el perfil demográfico y psicográfico.
6. **value_proposition**: ¿Cuál es la propuesta de valor principal del producto/servicio?

Responde SOLO con un JSON válido en este formato:
{{
    "customer_need": "...",
    "product_category": "...",
    "emotional_appeal": "...",
    "stylistic_tone": "...",
    "target_audience": "...",
    "value_proposition": "..."
}}"""

        try:
            response = self.llm.invoke(prompt)
            content = response.content if hasattr(response, 'content') else str(response)
            
            # Parsear JSON
            if content.strip().startswith('```'):
                # Remover markdown code blocks
                content = content.strip()
                if '```json' in content:
                    content = content.split('```json')[1].split('```')[0].strip()
                elif '```' in content:
                    content = content.split('```')[1].split('```')[0].strip()
            
            pillars_data = json.loads(content)
            
            return ContentPillar(
                customer_need=pillars_data.get('customer_need', ''),
                product_category=pillars_data.get('product_category', ''),
                emotional_appeal=pillars_data.get('emotional_appeal', ''),
                stylistic_tone=pillars_data.get('stylistic_tone', ''),
                target_audience=pillars_data.get('target_audience', ''),
                value_proposition=pillars_data.get('value_proposition', ''),
                metadata=ad_content.get('metadata', {})
            )
        except Exception as e:
            print(f"⚠️ Error extrayendo pilares: {e}")
            return ContentPillar(
                customer_need="Unknown",
                product_category="Unknown",
                emotional_appeal="Unknown",
                stylistic_tone="Unknown",
                target_audience="Unknown",
                value_proposition="Unknown"
            )
    
    def extract_pillars_batch(self, ad_corpus: List[Dict[str, Any]]) -> List[ContentPillar]:
        """Extrae pilares de un corpus de anuncios."""
        pillars = []
        for ad in ad_corpus:
            pillar = self.extract_pillars(ad)
            pillars.append(pillar)
        return pillars


class PersonaMiner:
    """
    Identifica personas de cliente mediante clustering semántico.
    Implementa la Sección 3.2 del paper MindFuse.
    """
    
    def __init__(self, config: AppConfig, llm: Optional[BaseLanguageModel] = None):
        self.config = config
        self.llm = llm or ChatOpenAI(
            model=config.research_model or "gpt-4o",
            temperature=0.3,
            api_key=config.openai_api_key,
            max_tokens=1500
        )
        self.embeddings = OpenAIEmbeddings(
            model="text-embedding-3-small",
            api_key=config.openai_api_key
        )
    
    def mine_personas(
        self,
        content_pillars: List[ContentPillar],
        n_clusters: Optional[int] = None
    ) -> List[CustomerPersona]:
        """
        Identifica personas mediante clustering de embeddings del pilar "Audience".
        
        Args:
            content_pillars: Lista de pilares de contenido extraídos
            n_clusters: Número de clusters (None = auto-detect)
        
        Returns:
            Lista de CustomerPersona identificadas
        """
        if not content_pillars:
            return []
        
        # Extraer textos de audiencia
        audience_texts = [pillar.target_audience for pillar in content_pillars]
        
        # Generar embeddings
        try:
            embeddings = self.embeddings.embed_documents(audience_texts)
            embeddings_array = np.array(embeddings)
        except Exception as e:
            print(f"⚠️ Error generando embeddings: {e}")
            return []
        
        # Determinar número de clusters (X-Means style)
        if n_clusters is None:
            n_clusters = self._estimate_optimal_clusters(embeddings_array)
        
        # Clustering con K-Means (o fallback simple)
        if not SKLEARN_AVAILABLE:
            print("⚠️ sklearn no disponible, usando clustering simple")
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        cluster_labels = kmeans.fit_predict(embeddings_array)
        
        # Agrupar por cluster
        clusters = defaultdict(list)
        for idx, label in enumerate(cluster_labels):
            clusters[label].append((content_pillars[idx], idx))
        
        # Generar personas usando LLM
        personas = []
        for cluster_id, items in clusters.items():
            persona = self._generate_persona_from_cluster(cluster_id, items, content_pillars)
            if persona:
                personas.append(persona)
        
        return personas
    
    def _estimate_optimal_clusters(self, embeddings: np.ndarray, max_clusters: int = 10) -> int:
        """Estima el número óptimo de clusters usando método del codo."""
        if len(embeddings) < 3:
            return 1
        
        max_k = min(max_clusters, len(embeddings) // 2)
        if max_k < 2:
            return 1
        
        inertias = []
        for k in range(1, max_k + 1):
            kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
            if SKLEARN_AVAILABLE:
                kmeans.fit(embeddings)
                inertias.append(kmeans.inertia_)
            else:
                # Fallback simple: usar varianza
                inertias.append(np.var(embeddings) * (1 - k/max_k))
        
        # Método del codo simplificado
        if len(inertias) < 2:
            return 1
        
        # Calcular diferencias
        diffs = [inertias[i] - inertias[i+1] for i in range(len(inertias)-1)]
        if not diffs:
            return 1
        
        # Encontrar el punto donde la reducción de inercia se estabiliza
        for i in range(len(diffs)-1):
            if diffs[i+1] < diffs[i] * 0.5:  # Reducción significativa
                return i + 2
        
        return max_k
    
    def _generate_persona_from_cluster(
        self,
        cluster_id: int,
        cluster_items: List[Tuple[ContentPillar, int]],
        all_pillars: List[ContentPillar]
    ) -> Optional[CustomerPersona]:
        """Genera una persona usando LLM a partir de un cluster."""
        # Agrupar textos de audiencia del cluster
        audience_texts = [item[0].target_audience for item in cluster_items]
        needs = [item[0].customer_need for item in cluster_items]
        
        prompt = f"""Eres un estratega de marketing senior. Analiza estos perfiles de audiencia agrupados 
y crea una persona de cliente coherente y estratégica.

PERFILES DE AUDIENCIA EN ESTE GRUPO:
{chr(10).join([f"- {text}" for text in audience_texts[:10]])}

NECESIDADES IDENTIFICADAS:
{chr(10).join([f"- {need}" for need in needs[:10]])}

TAREA:
Crea una persona de cliente que represente este grupo. Responde en formato JSON:

{{
    "name": "Nombre descriptivo de la persona (ej: 'Efficiency Enthusiasts')",
    "description": "Descripción completa de la persona (2-3 párrafos)",
    "psychological_profile": "Perfil psicológico y motivaciones",
    "behavioral_patterns": ["patrón1", "patrón2", "patrón3"]
}}"""

        try:
            response = self.llm.invoke(prompt)
            content = response.content if hasattr(response, 'content') else str(response)
            
            # Parsear JSON
            if content.strip().startswith('```'):
                if '```json' in content:
                    content = content.split('```json')[1].split('```')[0].strip()
                elif '```' in content:
                    content = content.split('```')[1].split('```')[0].strip()
            
            persona_data = json.loads(content)
            
            return CustomerPersona(
                persona_id=f"persona_{cluster_id}",
                name=persona_data.get('name', f'Persona {cluster_id}'),
                description=persona_data.get('description', ''),
                psychological_profile=persona_data.get('psychological_profile', ''),
                behavioral_patterns=persona_data.get('behavioral_patterns', []),
                content_items=[f"ad_{item[1]}" for item in cluster_items],
                cluster_size=len(cluster_items)
            )
        except Exception as e:
            print(f"⚠️ Error generando persona: {e}")
            return None


class ThematicChallengeMiner:
    """
    Identifica desafíos temáticos mediante clustering de insights.
    Implementa la Sección 3.3 del paper MindFuse.
    """
    
    def __init__(self, config: AppConfig, llm: Optional[BaseLanguageModel] = None):
        self.config = config
        self.llm = llm or ChatOpenAI(
            model=config.research_model or "gpt-4o",
            temperature=0.3,
            api_key=config.openai_api_key,
            max_tokens=1500
        )
        self.embeddings = OpenAIEmbeddings(
            model="text-embedding-3-small",
            api_key=config.openai_api_key
        )
    
    def mine_challenges(
        self,
        content_pillars: List[ContentPillar],
        n_clusters: Optional[int] = None
    ) -> List[ThematicChallenge]:
        """
        Identifica desafíos temáticos mediante clustering del pilar "Insights".
        
        Args:
            content_pillars: Lista de pilares de contenido
            n_clusters: Número de clusters (None = auto-detect)
        
        Returns:
            Lista de ThematicChallenge identificados
        """
        if not content_pillars:
            return []
        
        # Combinar customer_need + value_proposition como "insights"
        insight_texts = [
            f"{pillar.customer_need}. {pillar.value_proposition}"
            for pillar in content_pillars
        ]
        
        # Generar embeddings
        try:
            embeddings = self.embeddings.embed_documents(insight_texts)
            embeddings_array = np.array(embeddings)
        except Exception as e:
            print(f"⚠️ Error generando embeddings: {e}")
            return []
        
        # Determinar número de clusters
        if n_clusters is None:
            n_clusters = self._estimate_optimal_clusters(embeddings_array)
        
        # Clustering (con fallback si sklearn no está disponible)
        if not SKLEARN_AVAILABLE:
            print("⚠️ sklearn no disponible, usando clustering simple")
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        cluster_labels = kmeans.fit_predict(embeddings_array)
        
        # Agrupar por cluster
        clusters = defaultdict(list)
        for idx, label in enumerate(cluster_labels):
            clusters[label].append((content_pillars[idx], idx))
        
        # Generar desafíos usando LLM
        challenges = []
        for cluster_id, items in clusters.items():
            challenge = self._generate_challenge_from_cluster(cluster_id, items, content_pillars)
            if challenge:
                challenges.append(challenge)
        
        return challenges
    
    def _estimate_optimal_clusters(self, embeddings: np.ndarray, max_clusters: int = 10) -> int:
        """Estima el número óptimo de clusters."""
        if len(embeddings) < 3:
            return 1
        
        max_k = min(max_clusters, len(embeddings) // 2)
        if max_k < 2:
            return 1
        
        inertias = []
        for k in range(1, max_k + 1):
            kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
            if SKLEARN_AVAILABLE:
                kmeans.fit(embeddings)
                inertias.append(kmeans.inertia_)
            else:
                # Fallback simple: usar varianza
                inertias.append(np.var(embeddings) * (1 - k/max_k))
        
        if len(inertias) < 2:
            return 1
        
        diffs = [inertias[i] - inertias[i+1] for i in range(len(inertias)-1)]
        if not diffs:
            return 1
        
        for i in range(len(diffs)-1):
            if diffs[i+1] < diffs[i] * 0.5:
                return i + 2
        
        return max_k
    
    def _generate_challenge_from_cluster(
        self,
        cluster_id: int,
        cluster_items: List[Tuple[ContentPillar, int]],
        all_pillars: List[ContentPillar]
    ) -> Optional[ThematicChallenge]:
        """Genera un desafío temático usando LLM."""
        needs = [item[0].customer_need for item in cluster_items]
        values = [item[0].value_proposition for item in cluster_items]
        
        prompt = f"""Eres un estratega de marketing senior. Analiza estos insights agrupados 
y crea un desafío temático estratégico.

NECESIDADES IDENTIFICADAS:
{chr(10).join([f"- {need}" for need in needs[:10]])}

PROPUESTAS DE VALOR:
{chr(10).join([f"- {value}" for value in values[:10]])}

TAREA:
Crea un desafío temático que represente este grupo. Responde en formato JSON:

{{
    "name": "Nombre del desafío (ej: 'Inefficient Corporate Expense Management')",
    "description": "Descripción completa del desafío (2-3 párrafos)",
    "pain_points": ["dolor1", "dolor2", "dolor3"],
    "value_propositions": ["propuesta1", "propuesta2", "propuesta3"]
}}"""

        try:
            response = self.llm.invoke(prompt)
            content = response.content if hasattr(response, 'content') else str(response)
            
            if content.strip().startswith('```'):
                if '```json' in content:
                    content = content.split('```json')[1].split('```')[0].strip()
                elif '```' in content:
                    content = content.split('```')[1].split('```')[0].strip()
            
            challenge_data = json.loads(content)
            
            return ThematicChallenge(
                challenge_id=f"challenge_{cluster_id}",
                name=challenge_data.get('name', f'Challenge {cluster_id}'),
                description=challenge_data.get('description', ''),
                pain_points=challenge_data.get('pain_points', []),
                value_propositions=challenge_data.get('value_propositions', []),
                content_items=[f"ad_{item[1]}" for item in cluster_items],
                cluster_size=len(cluster_items)
            )
        except Exception as e:
            print(f"⚠️ Error generando desafío: {e}")
            return None


class NarrativeGenerator:
    """
    Genera narrativas estratégicas combinando personas + desafíos.
    Implementa la Sección 4 del paper MindFuse.
    """
    
    def __init__(self, config: AppConfig, llm: Optional[BaseLanguageModel] = None):
        self.config = config
        self.llm = llm or ChatOpenAI(
            model=config.research_model or "gpt-4o",
            temperature=0.7,
            api_key=config.openai_api_key,
            max_tokens=2000
        )
    
    def generate_narrative(
        self,
        persona: CustomerPersona,
        challenge: ThematicChallenge,
        brand_context: Optional[Dict[str, Any]] = None
    ) -> CampaignNarrative:
        """
        Genera una narrativa estratégica combinando persona + desafío.
        
        Args:
            persona: Persona de cliente
            challenge: Desafío temático
            brand_context: Contexto de marca (productos, servicios, etc.)
        
        Returns:
            CampaignNarrative completa
        """
        prompt = f"""Eres un consultor estratégico senior de nivel C-Suite. 
Tu tarea es crear una narrativa estratégica de campaña combinando una persona de cliente 
con un desafío temático.

PERSONA DE CLIENTE:
Nombre: {persona.name}
Descripción: {persona.description}
Perfil Psicológico: {persona.psychological_profile}
Patrones de Comportamiento: {', '.join(persona.behavioral_patterns)}

DESAFÍO TEMÁTICO:
Nombre: {challenge.name}
Descripción: {challenge.description}
Puntos de Dolor: {', '.join(challenge.pain_points)}
Propuestas de Valor: {', '.join(challenge.value_propositions)}

CONTEXTO DE MARCA:
{brand_context.get('description', 'No especificado') if brand_context else 'No especificado'}

TAREA:
Crea una narrativa estratégica completa que combine esta persona con este desafío.
La narrativa debe seguir la estructura "héroe + conflicto" y ser lista para usar como brief de campaña.

Responde en formato JSON:

{{
    "story": "Historia narrativa completa (3-4 párrafos) que cuenta cómo la marca ayuda a la persona a resolver el desafío. Incluye un personaje ficticio representativo (ej: 'Samuel Tan')",
    "campaign_insight": "Insight estratégico clave de la campaña (1-2 párrafos)",
    "creative_direction": "Dirección creativa recomendada (tono, estilo, mensajes clave)",
    "target_messaging": "Mensaje principal para esta audiencia y desafío"
}}"""

        try:
            response = self.llm.invoke(prompt)
            content = response.content if hasattr(response, 'content') else str(response)
            
            if content.strip().startswith('```'):
                if '```json' in content:
                    content = content.split('```json')[1].split('```')[0].strip()
                elif '```' in content:
                    content = content.split('```')[1].split('```')[0].strip()
            
            narrative_data = json.loads(content)
            
            return CampaignNarrative(
                narrative_id=f"narrative_{int(time.time())}",
                persona=persona,
                challenge=challenge,
                story=narrative_data.get('story', ''),
                campaign_insight=narrative_data.get('campaign_insight', ''),
                creative_direction=narrative_data.get('creative_direction', ''),
                target_messaging=narrative_data.get('target_messaging', '')
            )
        except Exception as e:
            print(f"⚠️ Error generando narrativa: {e}")
            return CampaignNarrative(
                narrative_id=f"narrative_{int(time.time())}",
                persona=persona,
                challenge=challenge,
                story="Error generando narrativa",
                campaign_insight="",
                creative_direction="",
                target_messaging=""
            )


class ContentScorer:
    """
    Scoring predictivo de contenido con explicabilidad.
    Implementa la Sección 5 del paper MindFuse.
    """
    
    def __init__(self, config: AppConfig):
        self.config = config
        # En producción, aquí se cargaría un modelo entrenado de CTR prediction
        # Por ahora, simulamos con heurísticas basadas en LLM
    
    def score_content(
        self,
        creative_content: Dict[str, Any],
        narrative: Optional[CampaignNarrative] = None
    ) -> ContentScore:
        """
        Evalúa el contenido y predice performance con explicabilidad.
        
        Args:
            creative_content: Contenido del creativo (texto, imagen, etc.)
            narrative: Narrativa estratégica asociada (opcional)
        
        Returns:
            ContentScore con predicciones y explicabilidad
        """
        # En producción, esto usaría un modelo entrenado tipo SODA
        # Por ahora, usamos heurísticas basadas en análisis LLM
        
        # Simulación de scoring (en producción sería un modelo real)
        predicted_ctr = 0.02 + np.random.random() * 0.03  # 2-5% CTR típico
        predicted_cpr = 10.0 + np.random.random() * 20.0  # $10-30 CPR
        
        # Identificar regiones de alto impacto (simulado)
        high_impact_regions = [
            {"type": "primary_visual", "importance": 0.85, "description": "Elemento visual principal"},
            {"type": "cta_button", "importance": 0.75, "description": "Botón de llamada a la acción"},
            {"type": "background", "importance": 0.65, "description": "Fondo del creativo"}
        ]
        
        # Sugerencias de optimización
        optimization_suggestions = [
            "Asegurar que el elemento visual principal sea prominente",
            "El CTA debe tener alto contraste y ser claramente visible",
            "El fondo debe proporcionar contraste adecuado con el contenido principal"
        ]
        
        return ContentScore(
            creative_id=creative_content.get('id', f"creative_{int(time.time())}"),
            predicted_ctr=predicted_ctr,
            predicted_cpr=predicted_cpr,
            confidence=0.75,
            high_impact_regions=high_impact_regions,
            optimization_suggestions=optimization_suggestions
        )


class PerformanceMarketingAgent:
    """
    Agente autónomo de performance marketing que analiza y optimiza campañas en tiempo real.
    Implementa la Sección 6 del paper MindFuse.
    """
    
    def __init__(self, config: AppConfig, llm: Optional[BaseLanguageModel] = None):
        self.config = config
        self.llm = llm or ChatOpenAI(
            model=config.research_model or "gpt-4o",
            temperature=0.2,
            api_key=config.openai_api_key,
            max_tokens=3000
        )
    
    def analyze_campaign_performance(
        self,
        metrics_history: List[CampaignMetrics],
        creative_samples: Optional[List[Dict[str, Any]]] = None
    ) -> PerformanceInsight:
        """
        Analiza performance de campaña y genera insights estratégicos.
        
        Args:
            metrics_history: Historial de métricas de campaña
            creative_samples: Muestras de creativos (opcional)
        
        Returns:
            PerformanceInsight con análisis y recomendaciones
        """
        # Preparar datos para el LLM
        metrics_summary = self._prepare_metrics_summary(metrics_history)
        
        prompt = f"""Eres un Performance Marketing Lead senior con experiencia en optimización de campañas.
Tu tarea es analizar el performance de esta campaña y proporcionar insights estratégicos accionables.

DEFINICIONES DE MÉTRICAS:
- Reach: Personas únicas expuestas a la campaña
- Frequency: Promedio de exposiciones por usuario (crítico para monitorear fatiga)
- Results: Conversiones, leads o compras
- Cost per Result (CPR): Eficiencia de conversión
- Spend: Presupuesto desplegado
- CPM: Costo por 1,000 impresiones (proxy de competitividad del mercado)
- CTR: Tasa de engagement del anuncio
- CR (Click-to-View): % de usuarios que llegan a la página de destino
- CR (Click-to-Result): % de usuarios que completan el objetivo de la campaña

DATOS DE PERFORMANCE:
{metrics_summary}

CREATIVOS DE LA CAMPAÑA:
{self._prepare_creatives_summary(creative_samples) if creative_samples else 'No disponibles'}

TAREA PRINCIPAL: Minimizar Cost Per Result (CPR)

Responde las siguientes preguntas y proporciona recomendaciones:

1. ¿Cómo evolucionaron CPR y Spend?
2. ¿Cuáles fueron los cambios correspondientes en CTR, CPM y CR?
3. ¿Están estos cambios causalmente conectados?
4. ¿Qué métricas secundarias influyeron más en CPR?
5. ¿Qué insights a nivel creativo explican estos cambios?
6. ¿Qué acciones deben tomarse?

Responde en formato JSON:

{{
    "metric_disruption": "Descripción de las disrupciones en métricas clave (2-3 párrafos)",
    "causal_analysis": "Análisis causal de las relaciones entre métricas (2-3 párrafos)",
    "strategic_recommendation": "Recomendación estratégica principal (2-3 párrafos)",
    "tactical_actions": [
        "Acción táctica 1",
        "Acción táctica 2",
        "Acción táctica 3"
    ],
    "confidence": 0.0-1.0
}}"""

        try:
            response = self.llm.invoke(prompt)
            content = response.content if hasattr(response, 'content') else str(response)
            
            if content.strip().startswith('```'):
                if '```json' in content:
                    content = content.split('```json')[1].split('```')[0].strip()
                elif '```' in content:
                    content = content.split('```')[1].split('```')[0].strip()
            
            insight_data = json.loads(content)
            
            return PerformanceInsight(
                insight_id=f"insight_{int(time.time())}",
                metric_disruption=insight_data.get('metric_disruption', ''),
                causal_analysis=insight_data.get('causal_analysis', ''),
                strategic_recommendation=insight_data.get('strategic_recommendation', ''),
                tactical_actions=insight_data.get('tactical_actions', []),
                confidence=insight_data.get('confidence', 0.7)
            )
        except Exception as e:
            print(f"⚠️ Error analizando performance: {e}")
            return PerformanceInsight(
                insight_id=f"insight_{int(time.time())}",
                metric_disruption="Error en análisis",
                causal_analysis="",
                strategic_recommendation="",
                tactical_actions=[],
                confidence=0.0
            )
    
    def _prepare_metrics_summary(self, metrics_history: List[CampaignMetrics]) -> str:
        """Prepara resumen de métricas para el LLM."""
        if not metrics_history:
            return "No hay datos de métricas disponibles"
        
        summary = "HISTORIAL DE MÉTRICAS:\n\n"
        for i, metric in enumerate(metrics_history[-10:], 1):  # Últimas 10
            summary += f"Período {i} ({metric.timestamp}):\n"
            summary += f"  - Reach: {metric.reach:,}\n"
            summary += f"  - Frequency: {metric.frequency:.2f}\n"
            summary += f"  - Results: {metric.results}\n"
            summary += f"  - CPR: ${metric.cost_per_result:.2f}\n"
            summary += f"  - Spend: ${metric.spend:.2f}\n"
            summary += f"  - CPM: ${metric.cpm:.2f}\n"
            summary += f"  - CTR: {metric.ctr*100:.2f}%\n"
            summary += f"  - CR (Click-to-View): {metric.click_to_view*100:.2f}%\n"
            summary += f"  - CR (Click-to-Result): {metric.click_to_result*100:.2f}%\n\n"
        
        # Calcular tendencias
        if len(metrics_history) >= 2:
            latest = metrics_history[-1]
            previous = metrics_history[-2]
            
            summary += "TENDENCIAS (último vs anterior):\n"
            summary += f"  - CPR: {((latest.cost_per_result / previous.cost_per_result - 1) * 100):+.1f}%\n"
            summary += f"  - CTR: {((latest.ctr / previous.ctr - 1) * 100):+.1f}%\n"
            summary += f"  - CPM: {((latest.cpm / previous.cpm - 1) * 100):+.1f}%\n"
            summary += f"  - CR: {((latest.click_to_result / previous.click_to_result - 1) * 100):+.1f}%\n"
        
        return summary
    
    def _prepare_creatives_summary(self, creatives: List[Dict[str, Any]]) -> str:
        """Prepara resumen de creativos para el LLM."""
        if not creatives:
            return "No hay creativos disponibles"
        
        summary = "CREATIVOS DE LA CAMPAÑA:\n\n"
        for i, creative in enumerate(creatives[:5], 1):  # Primeros 5
            summary += f"Creativo {i}:\n"
            summary += f"  - Texto: {creative.get('text', 'N/A')[:200]}\n"
            summary += f"  - Tipo: {creative.get('type', 'N/A')}\n"
            summary += f"  - Metadata: {str(creative.get('metadata', {}))[:200]}\n\n"
        
        return summary


class MindFuseAgenticAI:
    """
    Sistema completo de Agentic AI para Advertising basado en MindFuse.
    Integra todos los módulos en un flujo coherente.
    """
    
    def __init__(self, config: AppConfig):
        self.config = config
        
        # Inicializar módulos
        self.pillar_extractor = ContentPillarExtractor(config)
        self.persona_miner = PersonaMiner(config)
        self.challenge_miner = ThematicChallengeMiner(config)
        self.narrative_generator = NarrativeGenerator(config)
        self.content_scorer = ContentScorer(config)
        self.performance_agent = PerformanceMarketingAgent(config)
        
        # Almacenamiento
        self.content_pillars: List[ContentPillar] = []
        self.personas: List[CustomerPersona] = []
        self.challenges: List[ThematicChallenge] = []
        self.narratives: List[CampaignNarrative] = []
    
    def process_ad_corpus(self, ad_corpus: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Procesa un corpus de anuncios y extrae insights estratégicos.
        
        Args:
            ad_corpus: Lista de anuncios con estructura {'text': ..., 'image_url': ..., etc.}
        
        Returns:
            Diccionario con todos los insights extraídos
        """
        print("📊 [MindFuse] Procesando corpus de anuncios...")
        
        # 1. Extraer pilares de contenido
        print("  → Extrayendo pilares de contenido...")
        self.content_pillars = self.pillar_extractor.extract_pillars_batch(ad_corpus)
        print(f"  ✅ {len(self.content_pillars)} pilares extraídos")
        
        # 2. Identificar personas
        print("  → Identificando personas de cliente...")
        self.personas = self.persona_miner.mine_personas(self.content_pillars)
        print(f"  ✅ {len(self.personas)} personas identificadas")
        
        # 3. Identificar desafíos temáticos
        print("  → Identificando desafíos temáticos...")
        self.challenges = self.challenge_miner.mine_challenges(self.content_pillars)
        print(f"  ✅ {len(self.challenges)} desafíos identificados")
        
        return {
            "content_pillars": self.content_pillars,
            "personas": self.personas,
            "challenges": self.challenges,
            "total_ads_processed": len(ad_corpus)
        }
    
    def generate_campaign_narratives(
        self,
        brand_context: Optional[Dict[str, Any]] = None,
        max_narratives: int = 5
    ) -> List[CampaignNarrative]:
        """
        Genera narrativas estratégicas combinando personas + desafíos.
        
        Args:
            brand_context: Contexto de marca
            max_narratives: Número máximo de narrativas a generar
        
        Returns:
            Lista de CampaignNarrative
        """
        if not self.personas or not self.challenges:
            print("⚠️ Primero procesa un corpus de anuncios")
            return []
        
        print(f"📝 [MindFuse] Generando narrativas estratégicas...")
        
        narratives = []
        count = 0
        
        # Combinar cada persona con cada desafío
        for persona in self.personas[:3]:  # Top 3 personas
            for challenge in self.challenges[:3]:  # Top 3 desafíos
                if count >= max_narratives:
                    break
                
                narrative = self.narrative_generator.generate_narrative(
                    persona=persona,
                    challenge=challenge,
                    brand_context=brand_context
                )
                narratives.append(narrative)
                count += 1
        
        self.narratives = narratives
        print(f"  ✅ {len(narratives)} narrativas generadas")
        
        return narratives
    
    def score_creative(self, creative_content: Dict[str, Any]) -> ContentScore:
        """Evalúa un creativo y predice su performance."""
        narrative = self.narratives[0] if self.narratives else None
        return self.content_scorer.score_content(creative_content, narrative)
    
    def analyze_performance(
        self,
        metrics_history: List[CampaignMetrics],
        creative_samples: Optional[List[Dict[str, Any]]] = None
    ) -> PerformanceInsight:
        """Analiza performance de campaña y genera insights."""
        return self.performance_agent.analyze_campaign_performance(
            metrics_history, creative_samples
        )

