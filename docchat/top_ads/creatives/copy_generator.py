"""
Copy Generator - Generación automática de copys publicitarios
con múltiples variantes A/B
"""

from __future__ import annotations

from typing import List, Dict, Optional, Any
from datetime import datetime
from langchain_core.language_models import BaseLanguageModel
from langchain_core.messages import SystemMessage, HumanMessage
import json
import re

from ...config import AppConfig
from ..utils.logger import TopAdsLogger


class CopyGenerator:
    """
    Generador de copys publicitarios.
    
    Genera:
    - Headlines
    - Primary text
    - CTAs
    - Variantes A/B automáticas
    - Adaptación por plataforma (Meta vs TikTok)
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
        self.generation_count = 0
    
    def generate_creatives(
        self,
        processed_assets: Dict[str, Any],
        business_objective: str,
        num_variants: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Genera creativos publicitarios a partir de assets procesados.
        
        Args:
            processed_assets: Assets procesados (imágenes, videos, textos)
            business_objective: Objetivo de negocio
            num_variants: Número de variantes a generar
        
        Returns:
            Lista de creativos generados
        """
        self.logger.info(f"Generando {num_variants} variantes de creativos...")
        
        # Extraer información de assets
        asset_info = self._extract_asset_info(processed_assets)
        
        creatives = []
        
        for i in range(num_variants):
            try:
                creative = self._generate_single_creative(
                    asset_info=asset_info,
                    business_objective=business_objective,
                    variant_number=i
                )
                creatives.append(creative)
                self.generation_count += 1
            except Exception as e:
                self.logger.error(f"Error generando variante {i}: {e}")
                continue
        
        self.logger.info(f"Generados {len(creatives)} creativos exitosamente")
        return creatives
    
    def _extract_asset_info(self, processed_assets: Dict[str, Any]) -> Dict[str, Any]:
        """Extrae información relevante de assets procesados."""
        info = {
            "has_images": len(processed_assets.get("images", [])) > 0,
            "has_videos": len(processed_assets.get("videos", [])) > 0,
            "has_texts": len(processed_assets.get("texts", [])) > 0,
            "text_content": [],
            "image_analysis": [],
            "video_analysis": []
        }
        
        # Extraer textos
        for text_asset in processed_assets.get("texts", []):
            if "text" in text_asset:
                info["text_content"].append(text_asset["text"])
            if "analysis" in text_asset:
                info["text_content"].append(str(text_asset["analysis"]))
        
        # Extraer análisis de imágenes
        for img_asset in processed_assets.get("images", []):
            if "analysis" in img_asset:
                info["image_analysis"].append(img_asset["analysis"])
        
        return info
    
    def _generate_single_creative(
        self,
        asset_info: Dict[str, Any],
        business_objective: str,
        variant_number: int
    ) -> Dict[str, Any]:
        """Genera un solo creative."""
        # Construir contexto para el LLM
        context = f"""
Objetivo de negocio: {business_objective}
Variante número: {variant_number + 1}

Assets disponibles:
- Imágenes: {asset_info["has_images"]}
- Videos: {asset_info["has_videos"]}
- Textos: {len(asset_info["text_content"])}

Contenido de textos:
{chr(10).join(asset_info["text_content"][:3])}
"""
        
        prompt = f"""Genera un creative publicitario completo con estas especificaciones:

{context}

Crea:
1. Headline (máximo 40 caracteres para Meta, 27 para TikTok)
2. Primary text (máximo 125 caracteres)
3. CTA (Call-to-Action) apropiado
4. Descripción (opcional, máximo 200 caracteres)

Variantes de estilo:
- Variante {variant_number + 1}: {"Emocional" if variant_number % 2 == 0 else "Racional"}
- Tono: {"Casual y cercano" if variant_number % 3 == 0 else "Profesional" if variant_number % 3 == 1 else "Urgente y directo"}

Responde en formato JSON:
{{
    "headline": "...",
    "primary_text": "...",
    "description": "...",
    "cta": "...",
    "tone": "...",
    "style": "..."
}}"""
        
        try:
            response = self.llm.invoke([
                SystemMessage(content="Eres un copywriter publicitario experto. Generas copys efectivos, concisos y persuasivos."),
                HumanMessage(content=prompt)
            ])
            
            content = response.content if hasattr(response, 'content') else str(response)
            
            # Parsear JSON
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                creative_data = json.loads(json_match.group())
            else:
                # Fallback
                creative_data = {
                    "headline": f"Descubre nuestro producto {variant_number + 1}",
                    "primary_text": "Oferta especial limitada. No te lo pierdas.",
                    "description": "",
                    "cta": "Learn More",
                    "tone": "casual",
                    "style": "emotional" if variant_number % 2 == 0 else "rational"
                }
            
            # Agregar metadata
            creative = {
                "id": f"creative_{variant_number}",
                "headline": creative_data.get("headline", ""),
                "primary_text": creative_data.get("primary_text", ""),
                "description": creative_data.get("description", ""),
                "cta": creative_data.get("cta", "Learn More"),
                "tone": creative_data.get("tone", "neutral"),
                "style": creative_data.get("style", "neutral"),
                "platforms": ["meta", "tiktok"],  # Por defecto para ambas plataformas
                "created_at": datetime.now().isoformat()
            }
            
            return creative
            
        except Exception as e:
            self.logger.error(f"Error generando creative: {e}")
            # Creative por defecto
            return {
                "id": f"creative_{variant_number}",
                "headline": f"Oferta especial {variant_number + 1}",
                "primary_text": "Descubre nuestra oferta exclusiva",
                "description": "",
                "cta": "Learn More",
                "tone": "neutral",
                "style": "neutral",
                "platforms": ["meta", "tiktok"],
                "created_at": datetime.now().isoformat()
            }
    
    def get_generation_count(self) -> int:
        """Retorna el número de creativos generados."""
        return self.generation_count



































