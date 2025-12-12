"""
Rate Limiting y Throttling para APIs
Previene rate limit errors y controla uso de recursos
"""

from __future__ import annotations

import time
from typing import Dict, Optional
from collections import defaultdict
from threading import Lock
from dataclasses import dataclass, field
from datetime import datetime, timedelta

try:
    from slowapi import Limiter, _rate_limit_exceeded_handler
    from slowapi.util import get_remote_address
    from slowapi.errors import RateLimitExceeded
    SLOWAPI_AVAILABLE = True
except ImportError:
    SLOWAPI_AVAILABLE = False
    print("⚠️ SlowAPI no disponible. Instala con: pip install slowapi")

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    print("⚠️ Redis no disponible. Instala con: pip install redis")


@dataclass
class RateLimit:
    """Configuración de rate limit"""
    requests: int  # Número de requests
    window_seconds: int  # Ventana de tiempo en segundos


@dataclass
class RateLimitRecord:
    """Registro de rate limit"""
    count: int = 0
    window_start: datetime = field(default_factory=datetime.now)
    lock: Lock = field(default_factory=Lock)


class InMemoryRateLimiter:
    """Rate limiter en memoria (fallback)"""
    
    def __init__(self):
        self.records: Dict[str, RateLimitRecord] = defaultdict(RateLimitRecord)
        self.lock = Lock()
    
    def is_allowed(
        self,
        key: str,
        limit: RateLimit
    ) -> bool:
        """Verifica si el request está permitido"""
        with self.lock:
            record = self.records[key]
            
            # Resetear si la ventana expiró
            now = datetime.now()
            if (now - record.window_start).total_seconds() > limit.window_seconds:
                record.count = 0
                record.window_start = now
            
            # Verificar límite
            if record.count >= limit.requests:
                return False
            
            record.count += 1
            return True
    
    def get_remaining(
        self,
        key: str,
        limit: RateLimit
    ) -> int:
        """Obtiene requests restantes"""
        with self.lock:
            record = self.records[key]
            
            now = datetime.now()
            if (now - record.window_start).total_seconds() > limit.window_seconds:
                return limit.requests
            
            return max(0, limit.requests - record.count)
    
    def reset(self, key: str):
        """Resetea el contador para una key"""
        with self.lock:
            if key in self.records:
                del self.records[key]


class RedisRateLimiter:
    """Rate limiter usando Redis"""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
    
    def is_allowed(
        self,
        key: str,
        limit: RateLimit
    ) -> bool:
        """Verifica si el request está permitido usando Redis"""
        try:
            redis_key = f"ratelimit:{key}"
            current = self.redis.get(redis_key)
            
            if current is None:
                # Primera request en la ventana
                self.redis.setex(redis_key, limit.window_seconds, 1)
                return True
            
            current_count = int(current)
            if current_count >= limit.requests:
                return False
            
            # Incrementar contador
            self.redis.incr(redis_key)
            return True
        except Exception as e:
            print(f"Error en Redis rate limiter: {e}")
            return True  # Permitir en caso de error
    
    def get_remaining(
        self,
        key: str,
        limit: RateLimit
    ) -> int:
        """Obtiene requests restantes"""
        try:
            redis_key = f"ratelimit:{key}"
            current = self.redis.get(redis_key)
            
            if current is None:
                return limit.requests
            
            current_count = int(current)
            return max(0, limit.requests - current_count)
        except Exception:
            return limit.requests  # Fallback


class RateLimiterManager:
    """Gestor de rate limiting"""
    
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        if REDIS_AVAILABLE and redis_client:
            self.limiter = RedisRateLimiter(redis_client)
            self.use_redis = True
        else:
            self.limiter = InMemoryRateLimiter()
            self.use_redis = False
        
        # Límites por API
        self.limits: Dict[str, RateLimit] = {
            "meta": RateLimit(requests=200, window_seconds=3600),  # 200 req/hora
            "google": RateLimit(requests=100, window_seconds=3600),  # 100 req/hora
            "tiktok": RateLimit(requests=300, window_seconds=3600),  # 300 req/hora
            "default": RateLimit(requests=100, window_seconds=3600)
        }
    
    def is_allowed(
        self,
        api_name: str,
        identifier: str = "default"
    ) -> bool:
        """Verifica si un request está permitido"""
        limit = self.limits.get(api_name, self.limits["default"])
        key = f"{api_name}:{identifier}"
        return self.limiter.is_allowed(key, limit)
    
    def get_remaining(
        self,
        api_name: str,
        identifier: str = "default"
    ) -> int:
        """Obtiene requests restantes"""
        limit = self.limits.get(api_name, self.limits["default"])
        key = f"{api_name}:{identifier}"
        return self.limiter.get_remaining(key, limit)
    
    def wait_if_needed(
        self,
        api_name: str,
        identifier: str = "default"
    ):
        """Espera si es necesario para respetar rate limits"""
        if not self.is_allowed(api_name, identifier):
            # Calcular tiempo de espera
            limit = self.limits.get(api_name, self.limits["default"])
            # Esperar un poco antes de reintentar
            time.sleep(1.0)
            raise RateLimitError(f"Rate limit excedido para {api_name}")


class RateLimitError(Exception):
    """Error de rate limit"""
    pass

