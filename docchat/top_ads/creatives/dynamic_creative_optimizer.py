"""
Dynamic Creative Optimization (DCO) - Optimización dinámica de creativos
Combina componentes (imágenes, headlines, CTAs) dinámicamente según perfil de usuario.

Similar a Meta's Dynamic Creative Optimization que combina hasta:
- 10 imágenes/videos
- 5 headlines
- 5 primary texts
- 5 descriptions
- 5 CTAs

Y los combina dinámicamente según perfil del usuario (demographics, intereses, comportamiento).
"""

from __future__ import annotations

from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from datetime import datetime
from langchain_core.language_models import BaseLanguageModel
from langchain_core.messages import SystemMessage, HumanMessage
import json
import re

from ...config import AppConfig
from ..utils.logger import TopAdsLogger


@dataclass
class UserProfile:
    """Perfil de usuario para DCO."""
    age: Optional[int] = None
    gender: Optional[str] = None  # "male", "female", "other"
    location: Optional[Dict[str, Any]] = None  # {"country": "US", "city": "New York"}
    interests: List[str] = None  # ["technology", "sports", ...]
    behaviors: List[str] = None  # ["online_shopper", "mobile_user", ...]
    demographics: Optional[Dict[str, Any]] = None
    past_interactions: Optional[Dict[str, Any]] = None  # {"clicks": 5, "purchases": 2}
    device_type: Optional[str] = None  # "mobile", "desktop", "tablet"
    language: Optional[str] = None


@dataclass
class CreativeComponent:
    """Componente de creative para DCO."""
    component_type: str  # "image", "headline", "primary_text", "description", "cta"
    content: str
    metadata: Optional[Dict[str, Any]] = None
    performance_score: float = 0.0  # Score histórico de performance (0-1)


@dataclass
class DynamicCreative:
    """Creative dinámico generado por DCO."""
    image_path: Optional[str] = None
    headline: str = ""
    primary_text: str = ""
    description: str = ""
    cta: str = ""
    user_profile: Optional[UserProfile] = None
    combination_score: float = 0.0  # Score de esta combinación específica
    created_at: str = ""


class DynamicCreativeOptimizer:
    """
    Optimizador de creativos dinámicos (DCO).
    
    Combina componentes automáticamente según perfil de usuario:
    - Analiza perfil del usuario (demographics, intereses, comportamiento)
    - Selecciona mejor combinación de componentes
    - Optimiza para máximo engagement y conversión
    """
    
    def __init__(
        self,
        config: AppConfig,
        llm: BaseLanguageModel,
        logger: TopAdsLogger
    ):
        self.config = config
        self.llm = llm
        self.logger = logger
        
        # Componentes disponibles para combinar
        self.images: List[CreativeComponent] = []
        self.headlines: List[CreativeComponent] = []
        self.primary_texts: List[CreativeComponent] = []
        self.descriptions: List[CreativeComponent] = []
        self.ctas: List[CreativeComponent] = []
        
        # Historial de combinaciones y performance
        self.combination_history: List[Dict[str, Any]] = []
    
    def load_components(
        self,
        images: List[str],
        headlines: List[str],
        primary_texts: List[str],
        descriptions: List[str] = None,
        ctas: List[str] = None
    ):
        """
        Carga componentes disponibles para DCO.
        
        Args:
            images: Lista de paths a imágenes
            headlines: Lista de headlines
            primary_texts: Lista de textos primarios
            descriptions: Lista de descripciones (opcional)
            ctas: Lista de CTAs (opcional)
        """
        self.logger.info(f"Cargando componentes DCO: {len(images)} imágenes, {len(headlines)} headlines")
        
        # Cargar imágenes
        self.images = [
            CreativeComponent(
                component_type="image",
                content=img,
                metadata={"path": img}
            )
            for img in images
        ]
        
        # Cargar headlines
        self.headlines = [
            CreativeComponent(
                component_type="headline",
                content=headline,
                metadata={"length": len(headline)}
            )
            for headline in headlines
        ]
        
        # Cargar primary texts
        self.primary_texts = [
            CreativeComponent(
                component_type="primary_text",
                content=text,
                metadata={"length": len(text)}
            )
            for text in primary_texts
        ]
        
        # Cargar descriptions
        if descriptions:
            self.descriptions = [
                CreativeComponent(
                    component_type="description",
                    content=desc,
                    metadata={"length": len(desc)}
                )
                for desc in descriptions
            ]
        else:
            self.descriptions = []
        
        # Cargar CTAs
        if ctas:
            self.ctas = [
                CreativeComponent(
                    component_type="cta",
                    content=cta,
                    metadata={}
                )
                for cta in ctas
            ]
        else:
            self.ctas = [
                CreativeComponent(component_type="cta", content="Learn More", metadata={}),
                CreativeComponent(component_type="cta", content="Shop Now", metadata={}),
                CreativeComponent(component_type="cta", content="Get Started", metadata={}),
                CreativeComponent(component_type="cta", content="Sign Up", metadata={}),
                CreativeComponent(component_type="cta", content="Download", metadata={})
            ]
    
    def create_dynamic_creative(
        self,
        user_profile: UserProfile
    ) -> DynamicCreative:
        """
        Crea un creative dinámico optimizado para el perfil de usuario.
        
        Similar a Meta's DCO: combina componentes automáticamente basado en:
        - Demographics (edad, género, ubicación)
        - Intereses y comportamientos
        - Historial de interacciones
        - Contexto (dispositivo, idioma)
        
        Args:
            user_profile: Perfil del usuario
        
        Returns:
            Creative dinámico optimizado
        """
        self.logger.info(f"Creando creative dinámico para usuario: {user_profile.age} años, {user_profile.location}")
        
        # Seleccionar mejor combinación usando LLM
        selected_components = self._select_best_combination(user_profile)
        
        # Crear creative dinámico
        dynamic_creative = DynamicCreative(
            image_path=selected_components.get("image"),
            headline=selected_components.get("headline", ""),
            primary_text=selected_components.get("primary_text", ""),
            description=selected_components.get("description", ""),
            cta=selected_components.get("cta", "Learn More"),
            user_profile=user_profile,
            combination_score=selected_components.get("score", 0.0),
            created_at=datetime.now().isoformat()
        )
        
        # Guardar en historial
        self.combination_history.append({
            "creative": dynamic_creative,
            "user_profile": user_profile,
            "timestamp": datetime.now().isoformat()
        })
        
        return dynamic_creative
    
    def _select_best_combination(
        self,
        user_profile: UserProfile
    ) -> Dict[str, Any]:
        """
        Selecciona la mejor combinación de componentes usando LLM.
        
        Args:
            user_profile: Perfil del usuario
        
        Returns:
            Dict con componentes seleccionados y score
        """
        # Construir contexto del usuario
        user_context = self._build_user_context(user_profile)
        
        # Construir prompt para LLM
        prompt = f"""Selecciona la mejor combinación de componentes publicitarios para este usuario:

PERFIL DE USUARIO:
{user_context}

COMPONENTES DISPONIBLES:

IMÁGENES ({len(self.images)} disponibles):
{chr(10).join([f"{i+1}. {img.content}" for i, img in enumerate(self.images[:10])])}

HEADLINES ({len(self.headlines)} disponibles):
{chr(10).join([f"{i+1}. {headline.content}" for i, headline in enumerate(self.headlines[:5])])}

PRIMARY TEXTS ({len(self.primary_texts)} disponibles):
{chr(10).join([f"{i+1}. {text.content[:100]}..." for i, text in enumerate(self.primary_texts[:5])])}

DESCRIPTIONS ({len(self.descriptions)} disponibles):
{chr(10).join([f"{i+1}. {desc.content[:100]}..." if desc.content else f"{i+1}. (vacío)" for i, desc in enumerate(self.descriptions[:5])])}

CTAs ({len(self.ctas)} disponibles):
{chr(10).join([f"{i+1}. {cta.content}" for i, cta in enumerate(self.ctas[:5])])}

INSTRUCCIONES:
1. Selecciona la mejor imagen que resuene con el perfil del usuario
2. Selecciona el headline más relevante y persuasivo
3. Selecciona el primary text que mejor conecte con los intereses del usuario
4. Selecciona description si es relevante (puede estar vacío)
5. Selecciona el CTA más apropiado para el perfil

Responde en formato JSON:
{{
    "image_index": 0,
    "headline_index": 0,
    "primary_text_index": 0,
    "description_index": 0,
    "cta_index": 0,
    "reasoning": "Explicación de por qué esta combinación es óptima para este usuario",
    "expected_engagement_score": 0.85
}}"""
        
        try:
            response = self.llm.invoke([
                SystemMessage(content="Eres un experto en optimización de creativos publicitarios dinámicos. Seleccionas la mejor combinación de componentes basándote en el perfil del usuario para maximizar engagement y conversión."),
                HumanMessage(content=prompt)
            ])
            
            content = response.content if hasattr(response, 'content') else str(response)
            
            # Parsear JSON
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                selection = json.loads(json_match.group())
            else:
                # Fallback: selección aleatoria ponderada
                selection = self._fallback_selection(user_profile)
            
            # Obtener componentes seleccionados
            image_idx = min(selection.get("image_index", 0), len(self.images) - 1)
            headline_idx = min(selection.get("headline_index", 0), len(self.headlines) - 1)
            text_idx = min(selection.get("primary_text_index", 0), len(self.primary_texts) - 1)
            desc_idx = min(selection.get("description_index", 0), len(self.descriptions) - 1) if self.descriptions else 0
            cta_idx = min(selection.get("cta_index", 0), len(self.ctas) - 1)
            
            return {
                "image": self.images[image_idx].content if self.images else None,
                "headline": self.headlines[headline_idx].content if self.headlines else "",
                "primary_text": self.primary_texts[text_idx].content if self.primary_texts else "",
                "description": self.descriptions[desc_idx].content if self.descriptions and desc_idx < len(self.descriptions) else "",
                "cta": self.ctas[cta_idx].content if self.ctas else "Learn More",
                "score": selection.get("expected_engagement_score", 0.5),
                "reasoning": selection.get("reasoning", "Combinación seleccionada automáticamente")
            }
            
        except Exception as e:
            self.logger.error(f"Error seleccionando combinación: {e}")
            return self._fallback_selection(user_profile)
    
    def _build_user_context(self, user_profile: UserProfile) -> str:
        """Construye contexto del usuario para el prompt."""
        context_parts = []
        
        if user_profile.age:
            context_parts.append(f"Edad: {user_profile.age} años")
        
        if user_profile.gender:
            context_parts.append(f"Género: {user_profile.gender}")
        
        if user_profile.location:
            location_str = user_profile.location.get("city", "")
            if user_profile.location.get("country"):
                location_str += f", {user_profile.location['country']}"
            if location_str:
                context_parts.append(f"Ubicación: {location_str}")
        
        if user_profile.interests:
            context_parts.append(f"Intereses: {', '.join(user_profile.interests[:5])}")
        
        if user_profile.behaviors:
            context_parts.append(f"Comportamientos: {', '.join(user_profile.behaviors[:5])}")
        
        if user_profile.device_type:
            context_parts.append(f"Dispositivo: {user_profile.device_type}")
        
        if user_profile.language:
            context_parts.append(f"Idioma: {user_profile.language}")
        
        if user_profile.past_interactions:
            clicks = user_profile.past_interactions.get("clicks", 0)
            purchases = user_profile.past_interactions.get("purchases", 0)
            context_parts.append(f"Historial: {clicks} clics, {purchases} compras")
        
        return "\n".join(context_parts) if context_parts else "Usuario genérico"
    
    def _fallback_selection(self, user_profile: UserProfile) -> Dict[str, Any]:
        """Selección fallback cuando falla el LLM."""
        # Selección simple basada en edad y género
        image_idx = 0
        headline_idx = 0
        text_idx = 0
        desc_idx = 0
        cta_idx = 0
        
        # Ajustar según edad
        if user_profile.age:
            if user_profile.age < 25:
                # Jóvenes: más casual, moderno
                headline_idx = min(1, len(self.headlines) - 1)
                cta_idx = min(2, len(self.ctas) - 1)  # "Get Started"
            elif user_profile.age > 50:
                # Mayores: más formal, claro
                headline_idx = min(0, len(self.headlines) - 1)
                cta_idx = min(0, len(self.ctas) - 1)  # "Learn More"
        
        return {
            "image_index": image_idx,
            "headline_index": headline_idx,
            "primary_text_index": text_idx,
            "description_index": desc_idx,
            "cta_index": cta_idx,
            "expected_engagement_score": 0.6,
            "reasoning": "Selección automática basada en perfil básico"
        }
    
    def update_component_performance(
        self,
        component_type: str,
        component_index: int,
        performance_score: float
    ):
        """
        Actualiza score de performance de un componente.
        
        Args:
            component_type: Tipo de componente ("image", "headline", etc.)
            component_index: Índice del componente
            performance_score: Score de performance (0-1)
        """
        component_lists = {
            "image": self.images,
            "headline": self.headlines,
            "primary_text": self.primary_texts,
            "description": self.descriptions,
            "cta": self.ctas
        }
        
        component_list = component_lists.get(component_type)
        if component_list and 0 <= component_index < len(component_list):
            component_list[component_index].performance_score = performance_score
            self.logger.info(f"Actualizado performance de {component_type}[{component_index}]: {performance_score}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Obtiene estadísticas del DCO."""
        return {
            "total_components": {
                "images": len(self.images),
                "headlines": len(self.headlines),
                "primary_texts": len(self.primary_texts),
                "descriptions": len(self.descriptions),
                "ctas": len(self.ctas)
            },
            "combinations_created": len(self.combination_history),
            "average_score": sum(
                c.get("creative", {}).combination_score if isinstance(c.get("creative"), DynamicCreative) else 0.0
                for c in self.combination_history
            ) / max(len(self.combination_history), 1)
        }

