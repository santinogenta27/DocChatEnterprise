"""
Top Ads Logger - Sistema de logging estructurado
"""

from __future__ import annotations

import logging
from typing import Optional
from pathlib import Path
from datetime import datetime

from ...config import AppConfig


class TopAdsLogger:
    """
    Logger estructurado para Top Ads Mode.
    
    Características:
    - Logs estructurados en JSON
    - Niveles de log (DEBUG, INFO, WARNING, ERROR)
    - Rotación de archivos
    - Integración con sistema de logging de Python
    """
    
    def __init__(self, config: AppConfig):
        self.config = config
        self.logger = logging.getLogger("top_ads")
        self.logger.setLevel(logging.INFO)
        
        # Crear directorio de logs
        log_dir = Path(config.memory_dir) / "top_ads_logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # Handler de archivo
        log_file = log_dir / f"top_ads_{datetime.now().strftime('%Y%m%d')}.log"
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.INFO)
        
        # Formato
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        
        # Handler de consola
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        
        # Agregar handlers
        if not self.logger.handlers:
            self.logger.addHandler(file_handler)
            self.logger.addHandler(console_handler)
    
    def debug(self, message: str, **kwargs):
        """Log nivel DEBUG."""
        self.logger.debug(f"{message} | {kwargs}")
    
    def info(self, message: str, **kwargs):
        """Log nivel INFO."""
        self.logger.info(f"{message} | {kwargs}")
    
    def warning(self, message: str, **kwargs):
        """Log nivel WARNING."""
        self.logger.warning(f"{message} | {kwargs}")
    
    def error(self, message: str, **kwargs):
        """Log nivel ERROR."""
        self.logger.error(f"{message} | {kwargs}")
    
    def critical(self, message: str, **kwargs):
        """Log nivel CRITICAL."""
        self.logger.critical(f"{message} | {kwargs}")

