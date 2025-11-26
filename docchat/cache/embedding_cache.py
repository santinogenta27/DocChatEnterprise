"""
Sistema de caché de embeddings para evitar regenerar embeddings de documentos.
"""

from __future__ import annotations

import hashlib
import json
import pickle
from pathlib import Path
from typing import List, Optional

from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings

from ..config import AppConfig
from ..utils import load_pickle, save_pickle


class EmbeddingCache:
    """
    Caché inteligente de embeddings para evitar regenerar embeddings
    de documentos que ya fueron procesados.
    """
    
    def __init__(self, config: AppConfig):
        self.config = config
        self.cache_dir = Path(config.memory_dir) / "embedding_cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Metadata de caché
        self.metadata_file = self.cache_dir / "cache_metadata.json"
        self.metadata = self._load_metadata()
    
    def _load_metadata(self) -> dict:
        """Carga metadata del caché."""
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}
    
    def _save_metadata(self):
        """Guarda metadata del caché."""
        try:
            with open(self.metadata_file, 'w', encoding='utf-8') as f:
                json.dump(self.metadata, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error guardando metadata: {e}")
    
    def _get_cache_key(self, text: str, model: str) -> str:
        """Genera clave única para el caché basada en texto y modelo."""
        content = f"{model}:{text}"
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    def get_embedding(self, text: str, model: str) -> Optional[List[float]]:
        """Obtiene embedding del caché si existe."""
        cache_key = self._get_cache_key(text, model)
        cache_file = self.cache_dir / f"{cache_key}.pkl"
        
        if cache_file.exists():
            try:
                embedding = load_pickle(cache_file)
                # Actualizar estadísticas
                if cache_key not in self.metadata:
                    self.metadata[cache_key] = {"hits": 0, "model": model}
                self.metadata[cache_key]["hits"] = self.metadata[cache_key].get("hits", 0) + 1
                self._save_metadata()
                return embedding
            except Exception as e:
                print(f"Error cargando embedding del caché: {e}")
        
        return None
    
    def save_embedding(self, text: str, model: str, embedding: List[float]):
        """Guarda embedding en el caché."""
        cache_key = self._get_cache_key(text, model)
        cache_file = self.cache_dir / f"{cache_key}.pkl"
        
        try:
            save_pickle(cache_file, embedding)
            self.metadata[cache_key] = {
                "hits": 0,
                "model": model,
                "text_preview": text[:100]
            }
            self._save_metadata()
        except Exception as e:
            print(f"Error guardando embedding en caché: {e}")
    
    def get_cache_stats(self) -> dict:
        """Obtiene estadísticas del caché."""
        total_embeddings = len(self.metadata)
        total_hits = sum(m.get("hits", 0) for m in self.metadata.values())
        
        return {
            "total_embeddings": total_embeddings,
            "total_hits": total_hits,
            "cache_size_mb": self._get_cache_size_mb(),
            "hit_rate": total_hits / max(total_embeddings, 1)
        }
    
    def _get_cache_size_mb(self) -> float:
        """Calcula tamaño del caché en MB."""
        total_size = 0
        for cache_file in self.cache_dir.glob("*.pkl"):
            total_size += cache_file.stat().st_size
        return total_size / (1024 * 1024)
    
    def clear_cache(self, older_than_days: Optional[int] = None):
        """Limpia el caché."""
        # Por ahora limpia todo, se puede mejorar para limpiar por fecha
        for cache_file in self.cache_dir.glob("*.pkl"):
            try:
                cache_file.unlink()
            except Exception:
                pass
        
        self.metadata = {}
        self._save_metadata()


class CachedOpenAIEmbeddings(OpenAIEmbeddings):
    """
    Wrapper de OpenAIEmbeddings con caché integrado.
    """
    
    def __init__(self, config: AppConfig, *args, **kwargs):
        # Guardar config y cache en __dict__ para evitar problemas con Pydantic
        model_name = kwargs.get("model", "text-embedding-3-small")
        super().__init__(*args, **kwargs)
        # Usar __dict__ para evitar validación de Pydantic
        self.__dict__["_config"] = config
        self.__dict__["_cache"] = EmbeddingCache(config)
        self.__dict__["_model"] = model_name
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed documentos con caché."""
        cache = self.__dict__.get("_cache")
        model = self.__dict__.get("_model", "text-embedding-3-small")
        
        embeddings = []
        texts_to_embed = []
        text_indices = []
        
        # Verificar caché para cada texto
        for idx, text in enumerate(texts):
            cached = cache.get_embedding(text, model)
            if cached:
                embeddings.append((idx, cached))
            else:
                texts_to_embed.append((idx, text))
        
        # Embed textos no cacheados
        if texts_to_embed:
            texts_only = [text for _, text in texts_to_embed]
            new_embeddings = super().embed_documents(texts_only)
            
            # Guardar en caché y agregar a resultados
            for (idx, text), embedding in zip(texts_to_embed, new_embeddings):
                cache.save_embedding(text, model, embedding)
                embeddings.append((idx, embedding))
        
        # Ordenar por índice original
        embeddings.sort(key=lambda x: x[0])
        return [emb for _, emb in embeddings]
    
    def embed_query(self, text: str) -> List[float]:
        """Embed query con caché."""
        cache = self.__dict__.get("_cache")
        model = self.__dict__.get("_model", "text-embedding-3-small")
        
        cached = cache.get_embedding(text, model)
        if cached:
            return cached
        
        embedding = super().embed_query(text)
        cache.save_embedding(text, model, embedding)
        return embedding

