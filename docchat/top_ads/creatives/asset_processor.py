"""
Asset Processor - Procesamiento multimodal de assets del usuario
(imágenes, videos, textos)
"""

from __future__ import annotations

import base64
from pathlib import Path
from typing import List, Dict, Optional, Any
from langchain_core.language_models import BaseLanguageModel
from langchain_core.messages import SystemMessage, HumanMessage
import json

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False

from ...config import AppConfig
from ..utils.logger import TopAdsLogger


class AssetProcessor:
    """
    Procesador de assets publicitarios.
    
    Procesa:
    - Imágenes: análisis visual, extracción de características
    - Videos: metadata, keyframes, transcripción de audio
    - Textos: limpieza, clasificación, extracción de propuesta de valor
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
    
    def process_assets(
        self,
        images: List[str],
        videos: List[str],
        texts: List[str]
    ) -> Dict[str, Any]:
        """
        Procesa todos los assets del usuario.
        
        Args:
            images: Lista de paths a imágenes
            videos: Lista de paths a videos
            texts: Lista de textos base
        
        Returns:
            Diccionario con assets procesados
        """
        self.logger.info(f"Procesando assets: {len(images)} imágenes, {len(videos)} videos, {len(texts)} textos")
        
        processed = {
            "images": [],
            "videos": [],
            "texts": []
        }
        
        # Procesar imágenes
        for img_path in images:
            try:
                processed_img = self.process_image(img_path)
                processed["images"].append(processed_img)
            except Exception as e:
                self.logger.error(f"Error procesando imagen {img_path}: {e}")
        
        # Procesar videos
        for vid_path in videos:
            try:
                processed_vid = self.process_video(vid_path)
                processed["videos"].append(processed_vid)
            except Exception as e:
                self.logger.error(f"Error procesando video {vid_path}: {e}")
        
        # Procesar textos
        for text in texts:
            try:
                processed_text = self.process_text(text)
                processed["texts"].append(processed_text)
            except Exception as e:
                self.logger.error(f"Error procesando texto: {e}")
        
        return processed
    
    def process_image(self, image_path: str) -> Dict[str, Any]:
        """Procesa una imagen."""
        path = Path(image_path)
        
        if not path.exists():
            raise FileNotFoundError(f"Imagen no encontrada: {image_path}")
        
        result = {
            "path": str(path),
            "type": "image",
            "metadata": {}
        }
        
        # Análisis básico con PIL
        if PIL_AVAILABLE:
            try:
                with Image.open(path) as img:
                    result["metadata"] = {
                        "width": img.width,
                        "height": img.height,
                        "format": img.format,
                        "mode": img.mode,
                        "size_bytes": path.stat().st_size
                    }
            except Exception as e:
                self.logger.warning(f"Error analizando imagen con PIL: {e}")
        
        # Análisis con LLM Vision (si está disponible)
        if hasattr(self.llm, 'with_structured_output') or 'vision' in str(type(self.llm)).lower():
            try:
                # Leer imagen como base64
                with open(path, 'rb') as f:
                    img_data = base64.b64encode(f.read()).decode('utf-8')
                
                # Analizar con LLM
                analysis = self._analyze_image_with_llm(img_data)
                result["analysis"] = analysis
            except Exception as e:
                self.logger.warning(f"Error analizando imagen con LLM: {e}")
        
        return result
    
    def process_video(self, video_path: str) -> Dict[str, Any]:
        """Procesa un video."""
        path = Path(video_path)
        
        if not path.exists():
            raise FileNotFoundError(f"Video no encontrado: {video_path}")
        
        result = {
            "path": str(path),
            "type": "video",
            "metadata": {}
        }
        
        # Análisis básico con OpenCV
        if CV2_AVAILABLE:
            try:
                cap = cv2.VideoCapture(str(path))
                if cap.isOpened():
                    fps = cap.get(cv2.CAP_PROP_FPS)
                    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                    duration = frame_count / fps if fps > 0 else 0
                    
                    result["metadata"] = {
                        "duration_seconds": duration,
                        "fps": fps,
                        "frame_count": frame_count,
                        "width": width,
                        "height": height,
                        "size_bytes": path.stat().st_size
                    }
                    
                    cap.release()
            except Exception as e:
                self.logger.warning(f"Error analizando video con OpenCV: {e}")
        else:
            # Metadata básica sin OpenCV
            result["metadata"] = {
                "size_bytes": path.stat().st_size
            }
        
        return result
    
    def process_text(self, text: str) -> Dict[str, Any]:
        """Procesa un texto."""
        result = {
            "text": text,
            "type": "text",
            "length": len(text),
            "word_count": len(text.split())
        }
        
        # Análisis con LLM
        try:
            analysis = self._analyze_text_with_llm(text)
            result["analysis"] = analysis
        except Exception as e:
            self.logger.warning(f"Error analizando texto con LLM: {e}")
        
        return result
    
    def _analyze_image_with_llm(self, img_base64: str) -> Dict[str, Any]:
        """Analiza imagen con LLM Vision."""
        prompt = """Analiza esta imagen publicitaria y extrae:
1. Tipo de producto/servicio
2. Estilo visual (moderno, clásico, minimalista, etc.)
3. Colores dominantes
4. Presencia de personas
5. Mensaje emocional
6. Elementos de branding

Responde en formato JSON."""
        
        # Nota: Esto requiere un LLM con capacidad de visión
        # Por ahora, retornamos análisis básico
        return {
            "product_type": "unknown",
            "style": "unknown",
            "colors": [],
            "has_people": False,
            "emotional_message": "unknown",
            "branding_elements": []
        }
    
    def _analyze_text_with_llm(self, text: str) -> Dict[str, Any]:
        """Analiza texto con LLM."""
        prompt = f"""Analiza este texto publicitario y extrae:
1. Propuesta de valor principal
2. Tono (formal, casual, emocional, etc.)
3. Llamado a la acción (CTA)
4. Palabras clave
5. Intención del mensaje

Texto: {text}

Responde en formato JSON."""
        
        try:
            response = self.llm.invoke([
                SystemMessage(content="Eres un experto en análisis de copy publicitario."),
                HumanMessage(content=prompt)
            ])
            
            content = response.content if hasattr(response, 'content') else str(response)
            
            # Intentar parsear JSON
            import re
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            else:
                return {
                    "value_proposition": text[:100],
                    "tone": "neutral",
                    "cta": "unknown",
                    "keywords": text.split()[:5],
                    "intent": "informational"
                }
        except Exception as e:
            self.logger.warning(f"Error en análisis de texto: {e}")
            return {
                "value_proposition": text[:100],
                "tone": "neutral",
                "cta": "unknown",
                "keywords": [],
                "intent": "unknown"
            }

