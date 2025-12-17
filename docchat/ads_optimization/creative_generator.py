"""
Creative Generator - Generación completa de activos digitales
Genera imágenes, videos, copies, botones, CTAs desde cero
Similar a la visión de Zuckerberg: "solo dame tu objetivo y yo creo todo"
"""

from __future__ import annotations

import os
import base64
import json
import time
from typing import Dict, Any, Optional, List
from pathlib import Path
from dataclasses import dataclass, field

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    from PIL import Image, ImageDraw, ImageFont
    PILLOW_AVAILABLE = True
except ImportError:
    PILLOW_AVAILABLE = False

from ..config import AppConfig
from ..utils.llm_factory import create_llm


@dataclass
class BusinessInfo:
    """Información del negocio"""
    business_name: str
    business_type: str  # e.g., "e-commerce", "saas", "restaurant"
    description: str
    products_services: List[str] = field(default_factory=list)
    target_customers: str = ""
    unique_value_proposition: str = ""
    website: Optional[str] = None
    logo_url: Optional[str] = None


@dataclass
class GeneratedCreative:
    """Creative generado completamente"""
    creative_id: str
    headline: str
    description: str
    image_path: Optional[str] = None
    video_path: Optional[str] = None
    cta_button_text: str = "Learn More"
    cta_button_color: str = "#007BFF"
    cta_button_style: str = "rounded"
    layout: str = "standard"  # standard, carousel, story
    metadata: Dict[str, Any] = field(default_factory=dict)


class CreativeGenerator:
    """
    Generador completo de creativos
    Genera TODO desde cero: imágenes, videos, copies, botones, CTAs
    """
    
    def __init__(self, config: AppConfig):
        self.config = config
        self.openai_client = None
        
        if OPENAI_AVAILABLE and config.openai_api_key:
            self.openai_client = OpenAI(api_key=config.openai_api_key)
        
        # Crear LLM usando la función factory correcta
        self.llm = create_llm(
            provider="openai",
            model=getattr(config, 'openai_model', 'gpt-4o'),
            api_key=config.openai_api_key,
            temperature=getattr(config, 'temperature', 0.15)
        )
        
        # Directorio para creativos generados
        self.output_dir = Path(config.memory_dir) / "generated_creatives" if config.memory_dir else Path("data/generated_creatives")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        (self.output_dir / "images").mkdir(exist_ok=True)
        (self.output_dir / "videos").mkdir(exist_ok=True)
    
    async def generate_complete_campaign_from_business(
        self,
        business_info: BusinessInfo,
        objective: str,
        budget: float,
        num_creatives: int = 10
    ) -> List[GeneratedCreative]:
        """
        Genera campaña completa desde información del negocio
        Similar a la visión de Zuckerberg: "solo dame tu objetivo y yo creo todo"
        """
        creatives = []
        
        # 1. Generar múltiples copies usando LLM
        copies = await self._generate_copies(business_info, objective, num_creatives)
        
        # 2. Generar imágenes para cada copy
        for idx, copy_data in enumerate(copies):
            creative = GeneratedCreative(
                creative_id=f"creative_{int(time.time())}_{idx}",
                headline=copy_data["headline"],
                description=copy_data["description"],
                cta_button_text=copy_data.get("cta", "Learn More"),
                cta_button_color=copy_data.get("button_color", "#007BFF"),
                metadata=copy_data
            )
            
            # Generar imagen
            if self.openai_client:
                image_path = await self._generate_image(
                    business_info,
                    copy_data,
                    creative.creative_id
                )
                creative.image_path = image_path
            
            # Generar botón CTA visual
            if PILLOW_AVAILABLE:
                button_path = await self._generate_cta_button(
                    creative.cta_button_text,
                    creative.cta_button_color,
                    creative.creative_id
                )
                creative.metadata["button_image"] = button_path
            
            creatives.append(creative)
        
        return creatives
    
    async def _generate_copies(
        self,
        business_info: BusinessInfo,
        objective: str,
        num_copies: int
    ) -> List[Dict[str, Any]]:
        """Genera múltiples copies usando LLM"""
        prompt = f"""Eres un experto en copywriting publicitario. Genera {num_copies} copies completamente diferentes y creativos para este negocio:

NEGOCIO:
- Nombre: {business_info.business_name}
- Tipo: {business_info.business_type}
- Descripción: {business_info.description}
- Productos/Servicios: {', '.join(business_info.products_services)}
- Propuesta de Valor: {business_info.unique_value_proposition}
- Clientes Objetivo: {business_info.target_customers}

OBJETIVO: {objective}

INSTRUCCIONES:
1. Cada copy debe ser ÚNICO y diferente
2. Headline máximo 30 caracteres, impactante
3. Description máximo 125 caracteres, persuasiva
4. CTA button text (máximo 20 caracteres)
5. Button color (hex code)
6. Tono y estilo diferente para cada uno

FORMATO JSON:
{{
  "copies": [
    {{
      "headline": "Headline impactante",
      "description": "Descripción persuasiva",
      "cta": "Comprar Ahora",
      "button_color": "#FF0000",
      "tone": "urgent",
      "style": "direct"
    }},
    ...
  ]
}}
"""
        
        try:
            response = await self.llm.ainvoke(prompt)
            content = response.content.strip()
            
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            
            data = json.loads(content)
            return data.get("copies", [])
        
        except Exception as e:
            print(f"Error generando copies: {e}")
            # Fallback
            return [
                {
                    "headline": f"{business_info.business_name} - Oferta Especial",
                    "description": business_info.description[:125],
                    "cta": "Aprender Más",
                    "button_color": "#007BFF",
                    "tone": "professional"
                }
            ] * num_copies
    
    async def _generate_image(
        self,
        business_info: BusinessInfo,
        copy_data: Dict[str, Any],
        creative_id: str
    ) -> Optional[str]:
        """Genera imagen usando DALL-E 3"""
        if not self.openai_client:
            return None
        
        try:
            prompt = f"""Create a professional advertising image for:
Business: {business_info.business_name}
Type: {business_info.business_type}
Headline: {copy_data['headline']}
Description: {copy_data['description']}
Style: Modern, professional, eye-catching, suitable for social media advertising
Include: Visual elements related to {business_info.business_type}, appealing colors, clear composition"""
            
            response = self.openai_client.images.generate(
                model="dall-e-3",
                prompt=prompt,
                size="1024x1024",
                quality="standard",
                n=1
            )
            
            image_url = response.data[0].url
            
            # Descargar y guardar imagen
            import requests
            img_response = requests.get(image_url)
            image_path = self.output_dir / "images" / f"{creative_id}.png"
            
            with open(image_path, 'wb') as f:
                f.write(img_response.content)
            
            return str(image_path)
        
        except Exception as e:
            print(f"Error generando imagen: {e}")
            return None
    
    async def _generate_cta_button(
        self,
        button_text: str,
        button_color: str,
        creative_id: str
    ) -> Optional[str]:
        """Genera imagen de botón CTA"""
        if not PILLOW_AVAILABLE:
            return None
        
        try:
            # Crear imagen de botón
            width, height = 200, 60
            img = Image.new('RGB', (width, height), color=button_color)
            draw = ImageDraw.Draw(img)
            
            # Intentar usar fuente, fallback si no está disponible
            try:
                font = ImageFont.truetype("arial.ttf", 20)
            except:
                font = ImageFont.load_default()
            
            # Centrar texto
            bbox = draw.textbbox((0, 0), button_text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            x = (width - text_width) / 2
            y = (height - text_height) / 2
            
            draw.text((x, y), button_text, fill='white', font=font)
            
            # Guardar
            button_path = self.output_dir / "images" / f"{creative_id}_button.png"
            img.save(button_path)
            
            return str(button_path)
        
        except Exception as e:
            print(f"Error generando botón: {e}")
            return None
    
    async def generate_massive_variations(
        self,
        business_info: BusinessInfo,
        objective: str,
        target_count: int = 4000
    ) -> List[GeneratedCreative]:
        """
        Genera miles de variaciones automáticamente
        Como Zuckerberg: "4,000 diferentes versiones y testear cuál funciona mejor"
        """
        # Generar en batches para eficiencia
        batch_size = 50
        all_creatives = []
        
        num_batches = (target_count + batch_size - 1) // batch_size
        
        for batch_idx in range(num_batches):
            batch_creatives = await self.generate_complete_campaign_from_business(
                business_info,
                objective,
                budget=1000.0,  # Placeholder
                num_creatives=min(batch_size, target_count - len(all_creatives))
            )
            all_creatives.extend(batch_creatives)
            
            if len(all_creatives) >= target_count:
                break
        
        return all_creatives[:target_count]


class AutonomousCampaignCreator:
    """
    Creador de campañas completamente autónomo
    "Solo dame tu objetivo y yo hago todo"
    """
    
    def __init__(self, config: AppConfig):
        self.config = config
        self.creative_generator = CreativeGenerator(config)
        # Crear LLM usando la función factory correcta
        self.llm = create_llm(
            provider="openai",
            model=getattr(config, 'openai_model', 'gpt-4o'),
            api_key=config.openai_api_key,
            temperature=getattr(config, 'temperature', 0.15)
        )
    
    async def create_campaign_from_objective(
        self,
        business_description: str,
        objective: str,  # "quiero nuevos clientes", "quiero vender X productos"
        budget: float,
        max_cost_per_result: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Crea campaña completa solo con objetivo
        Similar a: "I want to get new customers to do this thing, tell us how much you're willing to pay"
        """
        # 1. Extraer información del negocio del description
        business_info = await self._extract_business_info(business_description)
        
        # 2. Generar creativos masivamente (como Zuckerberg: 4,000 versiones)
        num_creatives = 100  # Empezar con 100, escalable a 4,000
        creatives = await self.creative_generator.generate_massive_variations(
            business_info,
            objective,
            target_count=num_creatives
        )
        
        # 3. Predecir performance de todos
        # (usar el prediction model del engine)
        
        # 4. Seleccionar mejores automáticamente
        
        # 5. Crear y lanzar campaña
        
        return {
            "business_info": business_info,
            "creatives_generated": len(creatives),
            "creatives": creatives[:10],  # Mostrar solo primeros 10
            "status": "ready_to_launch"
        }
    
    async def _extract_business_info(self, description: str) -> BusinessInfo:
        """Extrae información del negocio del description usando LLM"""
        prompt = f"""Extrae información estructurada del negocio de esta descripción:

DESCRIPCIÓN:
{description}

Extrae:
- Nombre del negocio
- Tipo de negocio (e-commerce, saas, restaurant, etc.)
- Descripción clara
- Productos o servicios principales
- Clientes objetivo
- Propuesta de valor única

FORMATO JSON:
{{
  "business_name": "Nombre",
  "business_type": "tipo",
  "description": "descripción",
  "products_services": ["producto1", "producto2"],
  "target_customers": "descripción de clientes",
  "unique_value_proposition": "propuesta de valor"
}}
"""
        
        try:
            response = await self.llm.ainvoke(prompt)
            content = response.content.strip()
            
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            
            data = json.loads(content)
            
            return BusinessInfo(
                business_name=data.get("business_name", "Mi Negocio"),
                business_type=data.get("business_type", "general"),
                description=data.get("description", description),
                products_services=data.get("products_services", []),
                target_customers=data.get("target_customers", ""),
                unique_value_proposition=data.get("unique_value_proposition", "")
            )
        
        except Exception as e:
            print(f"Error extrayendo info del negocio: {e}")
            return BusinessInfo(
                business_name="Mi Negocio",
                business_type="general",
                description=description
            )

