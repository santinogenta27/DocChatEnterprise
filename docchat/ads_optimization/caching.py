"""
Sistema de Caching con Redis
Cache de predicciones, resultados de APIs, y datos frecuentes
"""

from __future__ import annotations

import json
import hashlib
from typing import Any, Optional, Dict
from datetime import datetime, timedelta

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    print("⚠️ Redis no disponible. Instala con: pip install redis")


class CacheManager:
    """Gestor de cache con Redis"""
    
    def __init__(self, redis_url: Optional[str] = None):
        self.redis_client: Optional[redis.Redis] = None
        self.use_redis = False
        
        if REDIS_AVAILABLE:
            try:
                redis_url = redis_url or "redis://localhost:6379"
                self.redis_client = redis.Redis.from_url(
                    redis_url,
                    decode_responses=True,
                    socket_connect_timeout=5
                )
                self.redis_client.ping()  # Test connection
                self.use_redis = True
            except Exception:
                # Fallback a cache en memoria
                self.cache: Dict[str, Dict[str, Any]] = {}
                self.use_redis = False
        else:
            self.cache: Dict[str, Dict[str, Any]] = {}
    
    def _make_key(self, prefix: str, *args, **kwargs) -> str:
        """Crea una key de cache"""
        key_parts = [prefix]
        key_parts.extend(str(arg) for arg in args)
        key_parts.extend(f"{k}:{v}" for k, v in sorted(kwargs.items()))
        key_string = ":".join(key_parts)
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def get(
        self,
        prefix: str,
        *args,
        default: Any = None,
        **kwargs
    ) -> Optional[Any]:
        """Obtiene valor del cache"""
        key = self._make_key(prefix, *args, **kwargs)
        
        if self.use_redis and self.redis_client:
            try:
                value = self.redis_client.get(key)
                if value:
                    return json.loads(value)
            except Exception:
                pass
        else:
            if key in self.cache:
                entry = self.cache[key]
                # Verificar expiración
                if datetime.now() < datetime.fromisoformat(entry["expires_at"]):
                    return entry["value"]
                else:
                    del self.cache[key]
        
        return default
    
    def set(
        self,
        prefix: str,
        value: Any,
        ttl_seconds: int = 3600,
        *args,
        **kwargs
    ):
        """Guarda valor en cache"""
        key = self._make_key(prefix, *args, **kwargs)
        
        if self.use_redis and self.redis_client:
            try:
                self.redis_client.setex(
                    key,
                    ttl_seconds,
                    json.dumps(value, default=str)
                )
            except Exception:
                pass
        else:
            expires_at = datetime.now() + timedelta(seconds=ttl_seconds)
            self.cache[key] = {
                "value": value,
                "expires_at": expires_at.isoformat()
            }
    
    def delete(self, prefix: str, *args, **kwargs):
        """Elimina valor del cache"""
        key = self._make_key(prefix, *args, **kwargs)
        
        if self.use_redis and self.redis_client:
            try:
                self.redis_client.delete(key)
            except Exception:
                pass
        else:
            if key in self.cache:
                del self.cache[key]
    
    def clear_prefix(self, prefix: str):
        """Limpia todas las keys con un prefix"""
        if self.use_redis and self.redis_client:
            try:
                pattern = f"{prefix}:*"
                keys = self.redis_client.keys(pattern)
                if keys:
                    self.redis_client.delete(*keys)
            except Exception:
                pass
        else:
            keys_to_delete = [k for k in self.cache.keys() if k.startswith(prefix)]
            for k in keys_to_delete:
                del self.cache[k]


class PredictionCache:
    """Cache especializado para predicciones"""
    
    def __init__(self, cache_manager: CacheManager):
        self.cache = cache_manager
        self.ttl = 86400  # 24 horas
    
    def get_prediction(
        self,
        variation_id: str,
        platform: str,
        objective: str
    ) -> Optional[Dict[str, float]]:
        """Obtiene predicción del cache"""
        return self.cache.get(
            "prediction",
            variation_id=variation_id,
            platform=platform,
            objective=objective
        )
    
    def set_prediction(
        self,
        variation_id: str,
        platform: str,
        objective: str,
        predictions: Dict[str, float]
    ):
        """Guarda predicción en cache"""
        self.cache.set(
            "prediction",
            predictions,
            ttl_seconds=self.ttl,
            variation_id=variation_id,
            platform=platform,
            objective=objective
        )


class APICache:
    """Cache para respuestas de APIs"""
    
    def __init__(self, cache_manager: CacheManager):
        self.cache = cache_manager
        self.ttl = 300  # 5 minutos
    
    def get_api_response(
        self,
        api_name: str,
        endpoint: str,
        params: Dict[str, Any]
    ) -> Optional[Any]:
        """Obtiene respuesta de API del cache"""
        return self.cache.get(
            "api_response",
            api_name=api_name,
            endpoint=endpoint,
            **params
        )
    
    def set_api_response(
        self,
        api_name: str,
        endpoint: str,
        params: Dict[str, Any],
        response: Any
    ):
        """Guarda respuesta de API en cache"""
        self.cache.set(
            "api_response",
            response,
            ttl_seconds=self.ttl,
            api_name=api_name,
            endpoint=endpoint,
            **params
        )

