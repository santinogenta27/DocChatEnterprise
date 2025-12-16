"""
Generador de Videos para Anuncios - Integración Real con Runway/Pika
Basado en la visión de Meta 2026: generación automática de videos publicitarios
"""

from __future__ import annotations

import os
import json
import time
import asyncio
from typing import Dict, Any, Optional, List
from pathlib import Path
from dataclasses import dataclass

try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False
    print("⚠️ aiohttp no disponible. Instala con: pip install aiohttp")

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


@dataclass
class VideoGenerationRequest:
    """Request para generar video"""
    prompt: str
    image_url: Optional[str] = None
    duration: int = 5  # segundos
    style: str = "cinematic"
    aspect_ratio: str = "16:9"
    fps: int = 24


@dataclass
class GeneratedVideo:
    """Video generado"""
    video_id: str
    video_url: str
    thumbnail_url: Optional[str] = None
    duration: float = 0.0
    file_path: Optional[str] = None
    metadata: Dict[str, Any] = None


class VideoGenerator:
    """
    Generador de videos usando Runway, Pika, o OpenAI Sora
    Implementa generación real de videos para anuncios
    """
    
    def __init__(self, config: Any):
        self.config = config
        self.runway_api_key = os.getenv("RUNWAY_API_KEY")
        self.pika_api_key = os.getenv("PIKA_API_KEY")
        self.openai_api_key = config.openai_api_key if hasattr(config, 'openai_api_key') else None
        
        # Directorio para videos generados
        self.output_dir = Path(config.memory_dir) / "generated_videos" if config.memory_dir else Path("data/generated_videos")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Preferencia de proveedor
        self.provider = os.getenv("VIDEO_GENERATION_PROVIDER", "runway")  # runway, pika, sora
    
    async def generate_video(
        self,
        prompt: str,
        image_url: Optional[str] = None,
        duration: int = 5,
        style: str = "cinematic",
        aspect_ratio: str = "16:9"
    ) -> Optional[GeneratedVideo]:
        """
        Genera un video real usando el proveedor configurado
        """
        request = VideoGenerationRequest(
            prompt=prompt,
            image_url=image_url,
            duration=duration,
            style=style,
            aspect_ratio=aspect_ratio
        )
        
        if self.provider == "runway" and self.runway_api_key:
            return await self._generate_with_runway(request)
        elif self.provider == "pika" and self.pika_api_key:
            return await self._generate_with_pika(request)
        elif self.provider == "sora" and self.openai_api_key and OPENAI_AVAILABLE:
            return await self._generate_with_sora(request)
        else:
            # Fallback: usar imagen estática como video (solo para desarrollo)
            print("⚠️ No hay API keys configuradas. Usando fallback de imagen estática.")
            return await self._fallback_video_generation(request)
    
    async def _generate_with_runway(self, request: VideoGenerationRequest) -> Optional[GeneratedVideo]:
        """Genera video usando Runway API"""
        if not AIOHTTP_AVAILABLE:
            return None
        try:
            async with aiohttp.ClientSession() as session:
                # Runway Gen-2 API
                url = "https://api.runwayml.com/v1/image-to-video"
                
                headers = {
                    "Authorization": f"Bearer {self.runway_api_key}",
                    "Content-Type": "application/json"
                }
                
                payload = {
                    "image": request.image_url,
                    "prompt": request.prompt,
                    "duration": request.duration,
                    "ratio": request.aspect_ratio,
                    "seed": int(time.time())
                }
                
                async with session.post(url, json=payload, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        video_id = data.get("id", f"runway_{int(time.time())}")
                        
                        # Polling para obtener el video cuando esté listo
                        video_url = await self._poll_runway_status(session, video_id)
                        
                        if video_url:
                            # Descargar video localmente
                            file_path = await self._download_video(video_url, video_id)
                            
                            return GeneratedVideo(
                                video_id=video_id,
                                video_url=video_url,
                                duration=request.duration,
                                file_path=str(file_path) if file_path else None,
                                metadata={
                                    "provider": "runway",
                                    "prompt": request.prompt,
                                    "style": request.style
                                }
                            )
                    else:
                        error_text = await response.text()
                        print(f"❌ Error Runway API: {response.status} - {error_text}")
                        return None
        except Exception as e:
            print(f"❌ Error generando video con Runway: {e}")
            return None
    
    async def _generate_with_pika(self, request: VideoGenerationRequest) -> Optional[GeneratedVideo]:
        """Genera video usando Pika API"""
        if not AIOHTTP_AVAILABLE:
            return None
        try:
            async with aiohttp.ClientSession() as session:
                # Pika API
                url = "https://api.pika.art/v1/generate"
                
                headers = {
                    "Authorization": f"Bearer {self.pika_api_key}",
                    "Content-Type": "application/json"
                }
                
                payload = {
                    "prompt": request.prompt,
                    "image_url": request.image_url,
                    "duration": request.duration,
                    "aspect_ratio": request.aspect_ratio
                }
                
                async with session.post(url, json=payload, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        video_id = data.get("video_id", f"pika_{int(time.time())}")
                        video_url = data.get("video_url")
                        
                        if video_url:
                            # Descargar video localmente
                            file_path = await self._download_video(video_url, video_id)
                            
                            return GeneratedVideo(
                                video_id=video_id,
                                video_url=video_url,
                                duration=request.duration,
                                file_path=str(file_path) if file_path else None,
                                metadata={
                                    "provider": "pika",
                                    "prompt": request.prompt,
                                    "style": request.style
                                }
                            )
                    else:
                        error_text = await response.text()
                        print(f"❌ Error Pika API: {response.status} - {error_text}")
                        return None
        except Exception as e:
            print(f"❌ Error generando video con Pika: {e}")
            return None
    
    async def _generate_with_sora(self, request: VideoGenerationRequest) -> Optional[GeneratedVideo]:
        """Genera video usando OpenAI Sora (cuando esté disponible)"""
        if not OPENAI_AVAILABLE:
            return None
        
        try:
            client = openai.OpenAI(api_key=self.openai_api_key)
            
            # Sora API (cuando esté disponible públicamente)
            # Por ahora, simulamos la estructura
            response = client.videos.generate(
                model="sora",
                prompt=request.prompt,
                image_url=request.image_url,
                duration=request.duration,
                aspect_ratio=request.aspect_ratio
            )
            
            video_id = f"sora_{int(time.time())}"
            video_url = response.video_url
            
            # Descargar video localmente
            file_path = await self._download_video(video_url, video_id)
            
            return GeneratedVideo(
                video_id=video_id,
                video_url=video_url,
                duration=request.duration,
                file_path=str(file_path) if file_path else None,
                metadata={
                    "provider": "sora",
                    "prompt": request.prompt,
                    "style": request.style
                }
            )
        except Exception as e:
            print(f"❌ Error generando video con Sora: {e}")
            return None
    
    async def _poll_runway_status(self, session, video_id: str, max_attempts: int = 30) -> Optional[str]:
        """Polling para verificar estado del video en Runway"""
        if not AIOHTTP_AVAILABLE:
            return None
        url = f"https://api.runwayml.com/v1/videos/{video_id}"
        headers = {"Authorization": f"Bearer {self.runway_api_key}"}
        
        for attempt in range(max_attempts):
            await asyncio.sleep(2)  # Esperar 2 segundos entre intentos
            
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    status = data.get("status")
                    
                    if status == "completed":
                        return data.get("video_url")
                    elif status == "failed":
                        print(f"❌ Video generation failed: {data.get('error')}")
                        return None
                    # Si está "processing", continuar polling
        
        print(f"⚠️ Timeout esperando video de Runway: {video_id}")
        return None
    
    async def _download_video(self, video_url: str, video_id: str) -> Optional[Path]:
        """Descarga video y lo guarda localmente"""
        if not AIOHTTP_AVAILABLE:
            return None
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(video_url) as response:
                    if response.status == 200:
                        file_path = self.output_dir / f"{video_id}.mp4"
                        with open(file_path, 'wb') as f:
                            async for chunk in response.content.iter_chunked(8192):
                                f.write(chunk)
                        return file_path
        except Exception as e:
            print(f"⚠️ Error descargando video: {e}")
            return None
    
    async def _fallback_video_generation(self, request: VideoGenerationRequest) -> GeneratedVideo:
        """Fallback: crea un video simple desde imagen (solo para desarrollo)"""
        video_id = f"fallback_{int(time.time())}"
        
        # En producción, esto debería generar un video real
        # Por ahora, retornamos metadata
        return GeneratedVideo(
            video_id=video_id,
            video_url=f"https://placeholder.com/video/{video_id}.mp4",
            duration=request.duration,
            metadata={
                "provider": "fallback",
                "prompt": request.prompt,
                "note": "Video generation requires API keys (Runway/Pika/Sora)"
            }
        )
