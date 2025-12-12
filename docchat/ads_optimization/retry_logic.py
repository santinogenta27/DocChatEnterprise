"""
Retry Logic y Circuit Breakers para APIs externas
Manejo robusto de errores con exponential backoff
"""

from __future__ import annotations

import time
import logging
from typing import Callable, Any, Optional, TypeVar, List
from functools import wraps
from enum import Enum

try:
    from tenacity import (
        retry,
        stop_after_attempt,
        wait_exponential,
        retry_if_exception_type,
        RetryError
    )
    TENACITY_AVAILABLE = True
except ImportError:
    TENACITY_AVAILABLE = False
    print("⚠️ Tenacity no disponible. Instala con: pip install tenacity")

try:
    from circuitbreaker import circuit
    CIRCUITBREAKER_AVAILABLE = True
except ImportError:
    CIRCUITBREAKER_AVAILABLE = False
    print("⚠️ CircuitBreaker no disponible. Instala con: pip install circuitbreaker")

T = TypeVar('T')


class APIError(Exception):
    """Error de API"""
    pass


class RateLimitError(APIError):
    """Error de rate limit"""
    pass


class CircuitOpenError(APIError):
    """Error cuando el circuit breaker está abierto"""
    pass


class RetryConfig:
    """Configuración de retry"""
    
    def __init__(
        self,
        max_attempts: int = 3,
        initial_wait: float = 1.0,
        max_wait: float = 60.0,
        exponential_base: float = 2.0,
        retry_on: tuple = (Exception,)
    ):
        self.max_attempts = max_attempts
        self.initial_wait = initial_wait
        self.max_wait = max_wait
        self.exponential_base = exponential_base
        self.retry_on = retry_on


def retry_with_backoff(
    func: Callable[..., T],
    config: Optional[RetryConfig] = None
) -> Callable[..., T]:
    """Decora una función con retry logic"""
    
    if config is None:
        config = RetryConfig()
    
    if not TENACITY_AVAILABLE:
        # Fallback simple sin tenacity
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(config.max_attempts):
                try:
                    return func(*args, **kwargs)
                except config.retry_on as e:
                    last_exception = e
                    if attempt < config.max_attempts - 1:
                        wait_time = min(
                            config.initial_wait * (config.exponential_base ** attempt),
                            config.max_wait
                        )
                        time.sleep(wait_time)
                    else:
                        raise
            if last_exception:
                raise last_exception
        return wrapper
    
    # Usar tenacity para retry avanzado
    retry_decorator = retry(
        stop=stop_after_attempt(config.max_attempts),
        wait=wait_exponential(
            multiplier=config.initial_wait,
            max=config.max_wait,
            exp_base=config.exponential_base
        ),
        retry=retry_if_exception_type(config.retry_on),
        reraise=True
    )
    
    return retry_decorator(func)


class CircuitBreaker:
    """Circuit breaker simple si no hay librería disponible"""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: tuple = (Exception,)
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half_open
    
    def call(self, func: Callable[..., T], *args, **kwargs) -> T:
        """Ejecuta función con circuit breaker"""
        if self.state == "open":
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = "half_open"
            else:
                raise CircuitOpenError("Circuit breaker is OPEN")
        
        try:
            result = func(*args, **kwargs)
            if self.state == "half_open":
                self.state = "closed"
                self.failure_count = 0
            return result
        except self.expected_exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            if self.failure_count >= self.failure_threshold:
                self.state = "open"
            
            raise


def with_circuit_breaker(
    failure_threshold: int = 5,
    recovery_timeout: int = 60,
    expected_exception: tuple = (Exception,)
):
    """Decora función con circuit breaker"""
    
    if CIRCUITBREAKER_AVAILABLE:
        return circuit(
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout,
            expected_exception=expected_exception
        )
    
    # Fallback sin librería
    breaker = CircuitBreaker(failure_threshold, recovery_timeout, expected_exception)
    
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs):
            return breaker.call(func, *args, **kwargs)
        return wrapper
    
    return decorator


class APIClient:
    """Cliente de API con retry y circuit breaker"""
    
    def __init__(
        self,
        name: str,
        retry_config: Optional[RetryConfig] = None,
        circuit_breaker_config: Optional[dict] = None
    ):
        self.name = name
        self.retry_config = retry_config or RetryConfig()
        self.circuit_breaker_config = circuit_breaker_config or {
            "failure_threshold": 5,
            "recovery_timeout": 60
        }
        self.logger = logging.getLogger(f"api_client.{name}")
    
    def call(
        self,
        func: Callable[..., T],
        *args,
        **kwargs
    ) -> T:
        """Ejecuta función con retry y circuit breaker"""
        
        # Aplicar circuit breaker
        if CIRCUITBREAKER_AVAILABLE:
            func = circuit(
                failure_threshold=self.circuit_breaker_config["failure_threshold"],
                recovery_timeout=self.circuit_breaker_config["recovery_timeout"]
            )(func)
        else:
            breaker = CircuitBreaker(
                failure_threshold=self.circuit_breaker_config["failure_threshold"],
                recovery_timeout=self.circuit_breaker_config["recovery_timeout"]
            )
            func = breaker.call
        
        # Aplicar retry
        func = retry_with_backoff(func, self.retry_config)
        
        try:
            return func(*args, **kwargs)
        except Exception as e:
            self.logger.error(f"Error en {self.name}: {e}")
            raise

