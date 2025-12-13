"""
LLM-Generated Ads: From Personalization Parity to Persuasion Superiority

Implementa las funcionalidades de los papers:
1. "LLM-Generated Ads: From Personalization Parity to Persuasion Superiority" (Meguellati et al. 2025)
2. "Against Opacity: Explainable AI and Large Language Models for Effective Digital Advertising" (SODA)
3. "Improving Generative Ad Text on Facebook using Reinforcement Learning" (AdLlama/RLPF)
4. "Analysis of Anonymous User Interaction Relationships" (DTH-GNN)

Características:
- Personalización basada en personalidad (Big Five: Openness, Neuroticism)
- Principios de persuasión (Authority, Consensus, Cognition, Scarcity)
- SODA framework (CTR prediction + explainability)
- RLPF (Reinforcement Learning with Performance Feedback)
- Análisis de ads con LLMs
- Generación optimizada de ads
"""

from __future__ import annotations

import json
import time
import asyncio
import uuid
from typing import List, Dict, Optional, Any, Tuple
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum

from langchain_core.language_models import BaseLanguageModel
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from .config import AppConfig


class PersonalityTrait(Enum):
    """Rasgos de personalidad Big Five para personalización."""
    OPENNESS = "openness"  # Alto: busca novedad e innovación
    NEUROTICISM = "neuroticism"  # Alto: evita riesgo, busca seguridad
    CONSCIENTIOUSNESS = "conscientiousness"
    EXTRAVERSION = "extraversion"
    AGREEABLENESS = "agreeableness"


class PersuasionPrinciple(Enum):
    """Principios de persuasión psicológica."""
    AUTHORITY = "authority"  # Credibilidad y experticia
    CONSENSUS = "consensus"  # Prueba social y popularidad
    COGNITION = "cognition"  # Racionalidad y características lógicas
    SCARCITY = "scarcity"  # Disponibilidad limitada y urgencia


@dataclass
class PersonalityProfile:
    """Perfil de personalidad del usuario."""
    openness: float  # 0.0 - 1.0
    neuroticism: float  # 0.0 - 1.0
    conscientiousness: float = 0.5
    extraversion: float = 0.5
    agreeableness: float = 0.5


@dataclass
class AdVariation:
    """Variación de anuncio generada."""
    variation_id: str
    ad_text: str
    headline: str
    description: str
    personality_target: Optional[PersonalityTrait] = None
    persuasion_principle: Optional[PersuasionPrinciple] = None
    predicted_ctr: float = 0.0
    confidence_score: float = 0.0
    generated_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class CTRPrediction:
    """Predicción de CTR con explicabilidad."""
    predicted_ctr: float
    confidence: float
    category: str  # "below_average", "average", "above_average"
    attention_heatmap: Optional[Dict[str, Any]] = None
    key_factors: List[str] = field(default_factory=list)
    improvement_suggestions: List[str] = field(default_factory=list)


@dataclass
class AdAnalysis:
    """Análisis completo de un anuncio."""
    ad_id: str
    human_need: str
    product_category: str
    archetype: str
    emotional_appeal: str
    stylistic_tone: str
    content_pillars: List[str] = field(default_factory=list)
    target_persona: Optional[str] = None
    persuasion_principle: Optional[PersuasionPrinciple] = None


class LLMGeneratedAdsSystem:
    """
    Sistema completo para generación de ads con LLMs.
    
    Basado en los papers:
    - Personalización basada en personalidad (Study 1)
    - Principios de persuasión (Study 2)
    - SODA framework (CTR prediction + explainability)
    - RLPF (Reinforcement Learning with Performance Feedback)
    """
    
    def __init__(self, config: AppConfig, llm: Optional[BaseLanguageModel] = None):
        self.config = config
        self.llm = llm or ChatOpenAI(
            model="gpt-4o",
            temperature=0.7,
            api_key=config.openai_api_key
        )
        
        # Almacenamiento
        self.generated_ads: Dict[str, AdVariation] = {}
        self.performance_data: Dict[str, Dict[str, Any]] = {}
        self.reward_model_data: List[Dict[str, Any]] = []
        
        # Directorio de persistencia
        self.storage_dir = Path(config.data_dir) / "llm_generated_ads"
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        print("✅ [LLM Generated Ads] Sistema inicializado")
    
    # ============================================
    # STUDY 1: PERSONALIZATION BASED ON PERSONALITY
    # ============================================
    
    async def generate_personality_targeted_ad(
        self,
        product_name: str,
        personality_trait: PersonalityTrait,
        product_description: Optional[str] = None
    ) -> AdVariation:
        """
        Genera un anuncio personalizado para un rasgo de personalidad específico.
        
        Basado en Study 1: Personalizing with LLMs
        - Openness: Enfoque en novedad, innovación, exploración
        - Neuroticism: Enfoque en seguridad, confiabilidad, reducción de ansiedad
        """
        variation_id = f"AD-{uuid.uuid4().hex[:8].upper()}"
        
        # Prompt específico según el rasgo
        if personality_trait == PersonalityTrait.OPENNESS:
            prompt = f"""Escribe un anuncio de 1 línea para un producto llamado {product_name} dirigido a personas con alto nivel de apertura (openness) sin mencionar explícitamente el rasgo.

Personas con alta apertura:
- Buscan novedad e innovación
- Disfrutan explorar nuevas ideas
- Valoran la creatividad y la originalidad
- Están abiertas a nuevas experiencias

Producto: {product_name}
Descripción: {product_description or "No proporcionada"}

Genera un anuncio que:
- Enfatice la innovación y novedad del producto
- Use lenguaje inspirador y visionario
- Conecte con el deseo de explorar y descubrir
- Sea creativo y único

Anuncio (1 línea):"""
        
        elif personality_trait == PersonalityTrait.NEUROTICISM:
            prompt = f"""Escribe un anuncio de 1 línea para un producto llamado {product_name} dirigido a personas con alto nivel de neuroticismo sin mencionar explícitamente el rasgo.

Personas con alta neuroticismo:
- Buscan seguridad y confiabilidad
- Valoran la estabilidad
- Prefieren evitar riesgos
- Necesitan reducir ansiedad e incertidumbre

Producto: {product_name}
Descripción: {product_description or "No proporcionada"}

Genera un anuncio que:
- Enfatice la seguridad y confiabilidad
- Reduzca ansiedad e incertidumbre
- Use lenguaje tranquilizador
- Destaque garantías y protección

Anuncio (1 línea):"""
        
        else:
            # Fallback genérico
            prompt = f"""Escribe un anuncio de 1 línea para {product_name}.

Producto: {product_name}
Descripción: {product_description or "No proporcionada"}

Anuncio (1 línea):"""
        
        try:
            response = await self.llm.ainvoke(prompt)
            ad_text = response.content if hasattr(response, 'content') else str(response)
            ad_text = ad_text.strip().strip('"').strip("'")
            
            # Generar headline y description
            headline = await self._generate_headline(ad_text, product_name)
            description = await self._generate_description(ad_text, product_name)
            
            variation = AdVariation(
                variation_id=variation_id,
                ad_text=ad_text,
                headline=headline,
                description=description,
                personality_target=personality_trait,
                confidence_score=0.8
            )
            
            self.generated_ads[variation_id] = variation
            return variation
            
        except Exception as e:
            print(f"❌ [LLM Generated Ads] Error generando ad personalizado: {e}")
            raise
    
    async def _generate_headline(self, ad_text: str, product_name: str) -> str:
        """Genera un headline basado en el texto del anuncio."""
        prompt = f"""Crea un headline corto y atractivo (máximo 60 caracteres) basado en este anuncio:

Anuncio: {ad_text}
Producto: {product_name}

Headline:"""
        
        try:
            response = await self.llm.ainvoke(prompt)
            return response.content.strip().strip('"').strip("'")
        except:
            return product_name
    
    async def _generate_description(self, ad_text: str, product_name: str) -> str:
        """Genera una descripción basada en el texto del anuncio."""
        prompt = f"""Crea una descripción breve (2-3 líneas) basada en este anuncio:

Anuncio: {ad_text}
Producto: {product_name}

Descripción:"""
        
        try:
            response = await self.llm.ainvoke(prompt)
            return response.content.strip()
        except:
            return ad_text
    
    # ============================================
    # STUDY 2: PERSUASION PRINCIPLES
    # ============================================
    
    async def generate_persuasion_principle_ad(
        self,
        product_name: str,
        principle: PersuasionPrinciple,
        product_description: Optional[str] = None,
        product_image_url: Optional[str] = None
    ) -> AdVariation:
        """
        Genera un anuncio basado en un principio de persuasión.
        
        Basado en Study 2: Persuasion Principles with LLMs
        - Authority: Credibilidad, experticia, respaldo profesional
        - Consensus: Prueba social, popularidad, "muchos otros lo usan"
        - Cognition: Racionalidad, características lógicas, beneficios funcionales
        - Scarcity: Disponibilidad limitada, urgencia, tiempo limitado
        """
        variation_id = f"AD-{uuid.uuid4().hex[:8].upper()}"
        
        # Prompts específicos por principio
        if principle == PersuasionPrinciple.AUTHORITY:
            prompt = f"""Crea un anuncio completo (texto, headline, descripción) para {product_name} usando el principio de AUTORIDAD.

Principio de Autoridad:
- Destaca credibilidad y experticia
- Menciona respaldos profesionales o certificaciones
- Usa lenguaje que transmita confianza y conocimiento
- Enfatiza la calidad y profesionalismo

Producto: {product_name}
Descripción: {product_description or "No proporcionada"}

Genera un anuncio que:
- Suene profesional y creíble
- Use lenguaje que transmita autoridad
- Incluya elementos que sugieran experticia
- Sea inspirador y elevado

Formato JSON:
{{
    "ad_text": "Texto principal del anuncio",
    "headline": "Headline corto y poderoso",
    "description": "Descripción detallada"
}}"""
        
        elif principle == PersuasionPrinciple.CONSENSUS:
            prompt = f"""Crea un anuncio completo (texto, headline, descripción) para {product_name} usando el principio de CONSENSO.

Principio de Consenso:
- Enfatiza popularidad y uso masivo
- Menciona que muchos otros lo usan
- Destaca testimonios y casos de éxito
- Usa prueba social

Producto: {product_name}
Descripción: {product_description or "No proporcionada"}

Genera un anuncio que:
- Muestre que es popular y ampliamente usado
- Incluya elementos de prueba social
- Sea accesible y cercano
- Conecte con el deseo de pertenencia

Formato JSON:
{{
    "ad_text": "Texto principal del anuncio",
    "headline": "Headline corto y poderoso",
    "description": "Descripción detallada"
}}"""
        
        elif principle == PersuasionPrinciple.COGNITION:
            prompt = f"""Crea un anuncio completo (texto, headline, descripción) para {product_name} usando el principio de COGNICIÓN.

Principio de Cognición:
- Apela al pensamiento racional
- Destaca características lógicas y funcionales
- Enfatiza beneficios prácticos
- Usa datos y hechos

Producto: {product_name}
Descripción: {product_description or "No proporcionada"}

Genera un anuncio que:
- Sea claro y directo
- Enfatice beneficios funcionales
- Use lenguaje racional y lógico
- Proporcione información útil

Formato JSON:
{{
    "ad_text": "Texto principal del anuncio",
    "headline": "Headline corto y poderoso",
    "description": "Descripción detallada"
}}"""
        
        elif principle == PersuasionPrinciple.SCARCITY:
            prompt = f"""Crea un anuncio completo (texto, headline, descripción) para {product_name} usando el principio de ESCASEZ.

Principio de Escasez:
- Enfatiza disponibilidad limitada
- Crea sentido de urgencia
- Menciona tiempo limitado o stock limitado
- Usa lenguaje que impulse acción inmediata

Producto: {product_name}
Descripción: {product_description or "No proporcionada"}

Genera un anuncio que:
- Cree urgencia sin ser demasiado agresivo
- Mencione limitaciones de tiempo o cantidad
- Impulse acción inmediata
- Sea convincente pero no manipulador

Formato JSON:
{{
    "ad_text": "Texto principal del anuncio",
    "headline": "Headline corto y poderoso",
    "description": "Descripción detallada"
}}"""
        
        try:
            response = await self.llm.ainvoke(prompt)
            content = response.content if hasattr(response, 'content') else str(response)
            
            # Parsear JSON
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            
            ad_data = json.loads(content)
            
            variation = AdVariation(
                variation_id=variation_id,
                ad_text=ad_data.get("ad_text", ""),
                headline=ad_data.get("headline", ""),
                description=ad_data.get("description", ""),
                persuasion_principle=principle,
                confidence_score=0.85
            )
            
            self.generated_ads[variation_id] = variation
            return variation
            
        except Exception as e:
            print(f"❌ [LLM Generated Ads] Error generando ad de persuasión: {e}")
            raise
    
    # ============================================
    # SODA FRAMEWORK: CTR PREDICTION + EXPLAINABILITY
    # ============================================
    
    async def predict_ctr_with_explanation(
        self,
        ad_text: str,
        headline: str,
        description: str,
        product_category: Optional[str] = None
    ) -> CTRPrediction:
        """
        Predice CTR y proporciona explicabilidad.
        
        Basado en SODA framework:
        - Predicción de CTR usando modelo multimodal
        - Attention heatmaps para visualización
        - Identificación de factores clave
        - Sugerencias de mejora
        """
        # Simular predicción de CTR (en producción usaría modelo entrenado)
        # Basado en análisis del texto con LLM
        
        analysis_prompt = f"""Analiza este anuncio y predice su potencial de click-through rate (CTR).

Anuncio:
- Headline: {headline}
- Texto: {ad_text}
- Descripción: {description}
- Categoría: {product_category or "General"}

Evalúa:
1. Predicción de CTR (0.0 - 1.0): ¿Qué porcentaje de personas harían clic?
2. Categoría: "below_average" (< 2%), "average" (2-4%), "above_average" (> 4%)
3. Factores clave que influyen en el CTR
4. Sugerencias de mejora específicas

Formato JSON:
{{
    "predicted_ctr": 0.0-1.0,
    "category": "below_average|average|above_average",
    "confidence": 0.0-1.0,
    "key_factors": ["factor1", "factor2", ...],
    "improvement_suggestions": ["sugerencia1", "sugerencia2", ...]
}}"""
        
        try:
            response = await self.llm.ainvoke(analysis_prompt)
            content = response.content if hasattr(response, 'content') else str(response)
            
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            
            prediction_data = json.loads(content)
            
            # Generar attention heatmap simulado
            attention_heatmap = await self._generate_attention_heatmap(ad_text, headline)
            
            prediction = CTRPrediction(
                predicted_ctr=float(prediction_data.get("predicted_ctr", 0.02)),
                confidence=float(prediction_data.get("confidence", 0.7)),
                category=prediction_data.get("category", "average"),
                attention_heatmap=attention_heatmap,
                key_factors=prediction_data.get("key_factors", []),
                improvement_suggestions=prediction_data.get("improvement_suggestions", [])
            )
            
            return prediction
            
        except Exception as e:
            print(f"❌ [LLM Generated Ads] Error prediciendo CTR: {e}")
            # Fallback
            return CTRPrediction(
                predicted_ctr=0.02,
                confidence=0.5,
                category="average",
                key_factors=["Análisis no disponible"],
                improvement_suggestions=["Revisar el anuncio manualmente"]
            )
    
    async def _generate_attention_heatmap(
        self,
        ad_text: str,
        headline: str
    ) -> Dict[str, Any]:
        """Genera un heatmap de atención simulado."""
        # En producción, esto usaría el modelo SoWide-v2 para generar heatmaps reales
        # Por ahora, simulamos con análisis de LLM
        
        prompt = f"""Identifica las palabras y frases más importantes en este anuncio que influyen en su efectividad.

Headline: {headline}
Texto: {ad_text}

Identifica:
1. Palabras clave de alto impacto (máximo 5)
2. Frases que generan más atención (máximo 3)
3. Elementos que deberían destacarse visualmente

Formato JSON:
{{
    "high_impact_words": ["palabra1", "palabra2", ...],
    "attention_phrases": ["frase1", "frase2", ...],
    "visual_elements": ["elemento1", "elemento2", ...]
}}"""
        
        try:
            response = await self.llm.ainvoke(prompt)
            content = response.content if hasattr(response, 'content') else str(response)
            
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            
            heatmap_data = json.loads(content)
            
            return {
                "high_impact_words": heatmap_data.get("high_impact_words", []),
                "attention_phrases": heatmap_data.get("attention_phrases", []),
                "visual_elements": heatmap_data.get("visual_elements", []),
                "visualization_type": "attention_heatmap"
            }
        except:
            return {
                "high_impact_words": [],
                "attention_phrases": [],
                "visual_elements": [],
                "visualization_type": "attention_heatmap"
            }
    
    # ============================================
    # SODA: AD ANALYSIS WITH LLMs
    # ============================================
    
    async def analyze_ad_content(
        self,
        ad_text: str,
        headline: str,
        description: str,
        image_url: Optional[str] = None
    ) -> AdAnalysis:
        """
        Analiza un anuncio usando LLMs para extraer insights estructurados.
        
        Basado en SODA framework:
        - Extrae content pillars (necesidades, productos, apelaciones emocionales)
        - Identifica arquetipos y tono
        - Analiza mensajes y estrategias
        """
        ad_id = f"ANALYSIS-{uuid.uuid4().hex[:8].upper()}"
        
        analysis_prompt = f"""Analiza este anuncio publicitario y extrae insights estructurados.

Anuncio:
- Headline: {headline}
- Texto: {ad_text}
- Descripción: {description}
- Imagen: {"Disponible" if image_url else "No disponible"}

Extrae:
1. Necesidad humana subyacente que se aborda
2. Categoría de producto
3. Arquetipo usado en el mensaje
4. Apelación emocional principal
5. Tono estilístico
6. Content pillars (necesidades, propuestas de valor, apelaciones emocionales, tono)
7. Persona objetivo (si es evidente)
8. Principio de persuasión usado (si aplica)

Formato JSON:
{{
    "human_need": "descripción de la necesidad",
    "product_category": "categoría",
    "archetype": "arquetipo usado",
    "emotional_appeal": "apelación emocional",
    "stylistic_tone": "tono estilístico",
    "content_pillars": ["pillar1", "pillar2", ...],
    "target_persona": "persona objetivo",
    "persuasion_principle": "authority|consensus|cognition|scarcity|none"
}}"""
        
        try:
            response = await self.llm.ainvoke(analysis_prompt)
            content = response.content if hasattr(response, 'content') else str(response)
            
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            
            analysis_data = json.loads(content)
            
            persuasion_principle = None
            if analysis_data.get("persuasion_principle") and analysis_data["persuasion_principle"] != "none":
                try:
                    persuasion_principle = PersuasionPrinciple(analysis_data["persuasion_principle"])
                except:
                    pass
            
            analysis = AdAnalysis(
                ad_id=ad_id,
                human_need=analysis_data.get("human_need", ""),
                product_category=analysis_data.get("product_category", ""),
                archetype=analysis_data.get("archetype", ""),
                emotional_appeal=analysis_data.get("emotional_appeal", ""),
                stylistic_tone=analysis_data.get("stylistic_tone", ""),
                content_pillars=analysis_data.get("content_pillars", []),
                target_persona=analysis_data.get("target_persona"),
                persuasion_principle=persuasion_principle
            )
            
            return analysis
            
        except Exception as e:
            print(f"❌ [LLM Generated Ads] Error analizando ad: {e}")
            raise
    
    # ============================================
    # RLPF: REINFORCEMENT LEARNING WITH PERFORMANCE FEEDBACK
    # ============================================
    
    async def generate_optimized_ad_variations(
        self,
        original_ad_text: str,
        product_name: str,
        num_variations: int = 5,
        use_rlpf: bool = True
    ) -> List[AdVariation]:
        """
        Genera múltiples variaciones optimizadas de un anuncio.
        
        Basado en AdLlama/RLPF:
        - Genera variaciones usando LLM
        - Predice CTR para cada variación
        - Ordena por performance esperada
        - Aprende de feedback histórico
        """
        variations = []
        
        for i in range(num_variations):
            # Generar variación
            variation_prompt = f"""Genera una variación mejorada de este anuncio:

Anuncio original: {original_ad_text}
Producto: {product_name}
Variación número: {i + 1} de {num_variations}

Crea una variación que:
- Mantenga el mensaje central
- Mejore el engagement potencial
- Sea única pero coherente
- Optimice para click-through rate

Variación mejorada:"""
            
            try:
                response = await self.llm.ainvoke(variation_prompt)
                variation_text = response.content.strip().strip('"').strip("'")
                
                headline = await self._generate_headline(variation_text, product_name)
                description = await self._generate_description(variation_text, product_name)
                
                # Predecir CTR
                ctr_prediction = await self.predict_ctr_with_explanation(
                    ad_text=variation_text,
                    headline=headline,
                    description=description
                )
                
                variation = AdVariation(
                    variation_id=f"VAR-{uuid.uuid4().hex[:8].upper()}",
                    ad_text=variation_text,
                    headline=headline,
                    description=description,
                    predicted_ctr=ctr_prediction.predicted_ctr,
                    confidence_score=ctr_prediction.confidence
                )
                
                variations.append(variation)
                
            except Exception as e:
                print(f"⚠️ [LLM Generated Ads] Error generando variación {i+1}: {e}")
                continue
        
        # Ordenar por CTR predicho
        variations.sort(key=lambda v: v.predicted_ctr, reverse=True)
        
        # Guardar para aprendizaje futuro
        for variation in variations:
            self.generated_ads[variation.variation_id] = variation
        
        return variations
    
    # ============================================
    # COMPARATIVE ANALYSIS: AI vs HUMAN
    # ============================================
    
    async def compare_ai_vs_human_ads(
        self,
        ai_ad: AdVariation,
        human_ad_text: str,
        human_headline: str,
        human_description: str
    ) -> Dict[str, Any]:
        """
        Compara un anuncio generado por AI vs uno escrito por humanos.
        
        Basado en los estudios que muestran:
        - AI ads pueden lograr paridad o superioridad
        - Quality Resilience: calidad supera origen
        """
        # Analizar ambos ads
        ai_analysis = await self.analyze_ad_content(
            ad_text=ai_ad.ad_text,
            headline=ai_ad.headline,
            description=ai_ad.description
        )
        
        human_analysis = await self.analyze_ad_content(
            ad_text=human_ad_text,
            headline=human_headline,
            description=human_description
        )
        
        # Predecir CTR para ambos
        ai_ctr = await self.predict_ctr_with_explanation(
            ad_text=ai_ad.ad_text,
            headline=ai_ad.headline,
            description=ai_ad.description
        )
        
        human_ctr = await self.predict_ctr_with_explanation(
            ad_text=human_ad_text,
            headline=human_headline,
            description=human_description
        )
        
        # Comparación
        comparison = {
            "ai_ad": {
                "text": ai_ad.ad_text,
                "headline": ai_ad.headline,
                "predicted_ctr": ai_ctr.predicted_ctr,
                "category": ai_ctr.category,
                "analysis": {
                    "human_need": ai_analysis.human_need,
                    "emotional_appeal": ai_analysis.emotional_appeal,
                    "tone": ai_analysis.stylistic_tone
                }
            },
            "human_ad": {
                "text": human_ad_text,
                "headline": human_headline,
                "predicted_ctr": human_ctr.predicted_ctr,
                "category": human_ctr.category,
                "analysis": {
                    "human_need": human_analysis.human_need,
                    "emotional_appeal": human_analysis.emotional_appeal,
                    "tone": human_analysis.stylistic_tone
                }
            },
            "comparison": {
                "ctr_difference": ai_ctr.predicted_ctr - human_ctr.predicted_ctr,
                "ai_advantage": ai_ctr.predicted_ctr > human_ctr.predicted_ctr,
                "relative_improvement": ((ai_ctr.predicted_ctr - human_ctr.predicted_ctr) / max(human_ctr.predicted_ctr, 0.001)) * 100
            }
        }
        
        return comparison
    
    # ============================================
    # UTILITY METHODS
    # ============================================
    
    def get_ad(self, variation_id: str) -> Optional[AdVariation]:
        """Obtiene un anuncio por ID."""
        return self.generated_ads.get(variation_id)
    
    def list_ads(self, personality_trait: Optional[PersonalityTrait] = None, 
                 persuasion_principle: Optional[PersuasionPrinciple] = None) -> List[AdVariation]:
        """Lista anuncios con filtros opcionales."""
        results = []
        for ad in self.generated_ads.values():
            if personality_trait and ad.personality_target != personality_trait:
                continue
            if persuasion_principle and ad.persuasion_principle != persuasion_principle:
                continue
            results.append(ad)
        return results










