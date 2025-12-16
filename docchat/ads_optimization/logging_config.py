"""
Logging estructurado para Ads Optimization Engine
JSON logging para mejor integración con sistemas de monitoring
"""

from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

try:
    from pythonjsonlogger import jsonlogger
    JSON_LOGGER_AVAILABLE = True
except ImportError:
    JSON_LOGGER_AVAILABLE = False
    print("⚠️ python-json-logger no disponible. Instala con: pip install python-json-logger")

try:
    import sentry_sdk
    from sentry_sdk.integrations.logging import LoggingIntegration
    SENTRY_AVAILABLE = True
except ImportError:
    SENTRY_AVAILABLE = False
    print("⚠️ Sentry no disponible. Instala con: pip install sentry-sdk")


class JSONFormatter(logging.Formatter):
    """Formatter JSON para logs estructurados"""
    
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # Agregar campos adicionales si existen
        if hasattr(record, "tenant_id"):
            log_data["tenant_id"] = record.tenant_id
        if hasattr(record, "campaign_id"):
            log_data["campaign_id"] = record.campaign_id
        if hasattr(record, "request_id"):
            log_data["request_id"] = record.request_id
        
        # Agregar exception info si existe
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_data, ensure_ascii=False)


def setup_logging(
    log_level: str = "INFO",
    log_file: Optional[Path] = None,
    enable_sentry: bool = False,
    sentry_dsn: Optional[str] = None,
    config: Optional[Any] = None
) -> logging.Logger:
    """Configura logging estructurado"""
    
    logger = logging.getLogger("ads_optimization")
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Remover handlers existentes
    logger.handlers.clear()
    
    # Handler para consola
    console_handler = logging.StreamHandler(sys.stdout)
    if JSON_LOGGER_AVAILABLE:
        formatter = jsonlogger.JsonFormatter(
            "%(timestamp)s %(level)s %(name)s %(message)s",
            timestamp=True
        )
    else:
        formatter = JSONFormatter()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Handler para archivo si se especifica
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    # Integración con Sentry si está disponible
    # Intentar cargar DSN desde archivo de configuración si no se proporciona
    if not sentry_dsn and config:
        try:
            from pathlib import Path
            import json
            config_file = Path(config.memory_dir) / "enterprise_ads_config.json" if hasattr(config, 'memory_dir') and config.memory_dir else Path("data/enterprise_ads_config.json")
            if config_file.exists():
                with open(config_file, 'r', encoding='utf-8') as f:
                    saved_config = json.load(f)
                    sentry_dsn = saved_config.get("sentry_dsn") or os.getenv("SENTRY_DSN")
        except Exception:
            pass
    
    # Fallback a variable de entorno
    if not sentry_dsn:
        sentry_dsn = os.getenv("SENTRY_DSN")
    
    if enable_sentry and SENTRY_AVAILABLE and sentry_dsn:
        sentry_logging = LoggingIntegration(
            level=logging.INFO,
            event_level=logging.ERROR
        )
        sentry_sdk.init(
            dsn=sentry_dsn,
            integrations=[sentry_logging],
            traces_sample_rate=0.1
        )
        logger.info("Sentry integrado para error tracking")
    
    return logger


def get_logger(name: str = "ads_optimization") -> logging.Logger:
    """Obtiene un logger"""
    return logging.getLogger(name)


class LoggerAdapter:
    """Adapter para agregar contexto a logs"""
    
    def __init__(
        self,
        logger: logging.Logger,
        tenant_id: Optional[str] = None,
        campaign_id: Optional[str] = None,
        request_id: Optional[str] = None
    ):
        self.logger = logger
        self.tenant_id = tenant_id
        self.campaign_id = campaign_id
        self.request_id = request_id
    
    def _log(
        self,
        level: int,
        msg: str,
        *args,
        **kwargs
    ):
        """Log con contexto"""
        extra = kwargs.get("extra", {})
        if self.tenant_id:
            extra["tenant_id"] = self.tenant_id
        if self.campaign_id:
            extra["campaign_id"] = self.campaign_id
        if self.request_id:
            extra["request_id"] = self.request_id
        kwargs["extra"] = extra
        self.logger.log(level, msg, *args, **kwargs)
    
    def debug(self, msg: str, *args, **kwargs):
        self._log(logging.DEBUG, msg, *args, **kwargs)
    
    def info(self, msg: str, *args, **kwargs):
        self._log(logging.INFO, msg, *args, **kwargs)
    
    def warning(self, msg: str, *args, **kwargs):
        self._log(logging.WARNING, msg, *args, **kwargs)
    
    def error(self, msg: str, *args, **kwargs):
        self._log(logging.ERROR, msg, *args, **kwargs)
    
    def exception(self, msg: str, *args, **kwargs):
        kwargs["exc_info"] = True
        self._log(logging.ERROR, msg, *args, **kwargs)

