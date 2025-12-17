"""
Multimodal Processor - Procesador multimodal
Soporta texto, imágenes, audio, y video
Basado en: Multimodal Generative AI Applications
"""

from __future__ import annotations

import base64
import json
import os
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

try:
    from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
    from langchain_openai import ChatOpenAI
    MULTIMODAL_AVAILABLE = True
except ImportError:
    MULTIMODAL_AVAILABLE = False


class MediaType(str, Enum):
    """Tipos de media soportados"""
    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"


@dataclass
class MediaInput:
    """Input de media"""
    media_type: MediaType
    content: Union[str, bytes, Path]  # Texto, base64, o path
    metadata: Optional[Dict[str, Any]] = None


class MultimodalProcessor:
    """
    Procesador multimodal que maneja texto, imágenes, audio, y video
    Basado en OpenAI Whisper, DALL-E, y modelos de visión
    """
    
    def __init__(self, config: Any):
        self.config = config
        self.openai_api_key = getattr(config, 'openai_api_key', None)
    
    def process_input(self, media_input: MediaInput) -> Dict[str, Any]:
        """
        Procesa input multimodal
        
        Returns:
            Dict con contenido procesado y metadata
        """
        if media_input.media_type == MediaType.TEXT:
            return self._process_text(media_input)
        elif media_input.media_type == MediaType.IMAGE:
            return self._process_image(media_input)
        elif media_input.media_type == MediaType.AUDIO:
            return self._process_audio(media_input)
        elif media_input.media_type == MediaType.VIDEO:
            return self._process_video(media_input)
        else:
            raise ValueError(f"Tipo de media no soportado: {media_input.media_type}")
    
    def _process_text(self, media_input: MediaInput) -> Dict[str, Any]:
        """Procesa texto"""
        return {
            "type": "text",
            "content": str(media_input.content),
            "metadata": media_input.metadata or {}
        }
    
    def _process_image(self, media_input: MediaInput) -> Dict[str, Any]:
        """Procesa imagen"""
        # Convertir a base64 si es path
        if isinstance(media_input.content, Path):
            with open(media_input.content, 'rb') as f:
                image_bytes = f.read()
                image_base64 = base64.b64encode(image_bytes).decode('utf-8')
        elif isinstance(media_input.content, bytes):
            image_base64 = base64.b64encode(media_input.content).decode('utf-8')
        else:
            image_base64 = media_input.content  # Asumir que ya es base64
        
        return {
            "type": "image",
            "content": image_base64,
            "format": "base64",
            "metadata": media_input.metadata or {}
        }
    
    def _process_audio(self, media_input: MediaInput) -> Dict[str, Any]:
        """Procesa audio usando Whisper API"""
        try:
            import os
            from openai import OpenAI
            
            # Obtener API key
            api_key = self.openai_api_key or os.getenv("OPENAI_API_KEY")
            if not api_key:
                # Intentar cargar desde configuración guardada
                try:
                    config_file = Path(self.config.memory_dir) / "enterprise_ads_config.json" if hasattr(self.config, 'memory_dir') and self.config.memory_dir else Path("data/enterprise_ads_config.json")
                    if config_file.exists():
                        with open(config_file, 'r', encoding='utf-8') as f:
                            saved_config = json.load(f)
                            api_key = saved_config.get("openai_key") or os.getenv("OPENAI_API_KEY")
                except Exception:
                    pass
            
            if not api_key:
                raise ValueError("OpenAI API key no configurada para transcripción de audio")
            
            client = OpenAI(api_key=api_key)
            
            # Preparar archivo de audio
            audio_file = None
            if isinstance(media_input.content, Path):
                audio_file = open(media_input.content, 'rb')
            elif isinstance(media_input.content, bytes):
                import tempfile
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
                temp_file.write(media_input.content)
                temp_file.close()
                audio_file = open(temp_file.name, 'rb')
            else:
                # Asumir que es un path string
                audio_file = open(media_input.content, 'rb')
            
            try:
                # Transcribir con Whisper
                transcript = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    response_format="text"
                )
                
                return {
                    "type": "audio",
                    "content": transcript,
                    "transcription": transcript,
                    "metadata": {
                        **(media_input.metadata or {}),
                        "model": "whisper-1",
                        "processed": True
                    }
                }
            finally:
                audio_file.close()
                if isinstance(media_input.content, bytes) and 'temp_file' in locals():
                    os.unlink(temp_file.name)
        except Exception as e:
            print(f"⚠️ Error procesando audio con Whisper: {e}")
            return {
                "type": "audio",
                "content": f"[Error en transcripción: {str(e)}]",
                "transcription": None,
                "metadata": {
                    **(media_input.metadata or {}),
                    "error": str(e),
                    "processed": False
                }
            }
    
    def _process_video(self, media_input: MediaInput) -> Dict[str, Any]:
        """Procesa video"""
        # Implementación futura
        return {
            "type": "video",
            "content": str(media_input.content),
            "frames": [],  # Se extraerán frames
            "metadata": media_input.metadata or {}
        }
    
    def create_multimodal_message(
        self,
        text: Optional[str] = None,
        images: Optional[List[Union[str, bytes, Path]]] = None,
        audio: Optional[Union[str, bytes, Path]] = None
    ) -> List[Any]:
        """
        Crea mensaje multimodal para LangChain
        
        Returns:
            Lista de mensajes para ChatOpenAI
        """
        if not MULTIMODAL_AVAILABLE:
            raise ImportError("LangChain requerido para mensajes multimodales")
        
        content = []
        
        # Agregar texto
        if text:
            content.append({"type": "text", "text": text})
        
        # Agregar imágenes
        if images:
            for image in images:
                if isinstance(image, Path):
                    with open(image, 'rb') as f:
                        image_bytes = f.read()
                        image_base64 = base64.b64encode(image_bytes).decode('utf-8')
                elif isinstance(image, bytes):
                    image_base64 = base64.b64encode(image).decode('utf-8')
                else:
                    image_base64 = image  # Asumir base64
                
                content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{image_base64}"
                    }
                })
        
        # Agregar audio (futuro)
        if audio:
            # Implementación futura
            pass
        
        return [HumanMessage(content=content)]
    
    def generate_image_caption(self, image_path: Union[str, Path]) -> str:
        """Genera caption para imagen usando visión"""
        if not self.openai_api_key:
            raise ValueError("OpenAI API key requerida")
        
        # Implementación con GPT-4 Vision
        # Por ahora, placeholder
        return "Imagen procesada"
    
    def transcribe_audio(self, audio_path: Union[str, Path]) -> str:
        """Transcribe audio usando Whisper"""
        if not self.openai_api_key:
            raise ValueError("OpenAI API key requerida")
        
        # Implementación con Whisper
        # Por ahora, placeholder
        return "Transcripción de audio"
