"""
Scheduler de Ingesta Automática para STAR AGENT.

Ejecuta ingesta automática según configuración (scheduler cada X horas).
Completamente configurable desde UI.
"""

from __future__ import annotations

import schedule
import threading
import time
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path

from .multi_source_ingester import MultiSourceIngester


class IngestionScheduler:
    """
    Scheduler para ingesta automática.
    
    Características:
    - Scheduler configurable (cada X horas)
    - Fuentes configurables (Website, Instagram, Facebook)
    - Toggle ON/OFF por fuente
    - Ejecución manual con "Run now"
    - Completamente configurable desde UI
    """
    
    def __init__(
        self,
        enabled: bool = False,
        interval_hours: int = 6,
        website_enabled: bool = False,
        website_url: Optional[str] = None,
        instagram_enabled: bool = False,
        instagram_token: Optional[str] = None,
        facebook_enabled: bool = False,
        facebook_token: Optional[str] = None,
        rag_manager=None,  # AdvancedRAGManager
    ):
        """
        Inicializa el scheduler de ingesta.
        
        Args:
            enabled: Si el scheduler está habilitado
            interval_hours: Intervalo en horas (default: 6)
            website_enabled: Si ingesta de website está habilitada
            website_url: URL del website
            instagram_enabled: Si ingesta de Instagram está habilitada
            instagram_token: Token de Instagram
            facebook_enabled: Si ingesta de Facebook está habilitada
            facebook_token: Token de Facebook
            rag_manager: Instancia de AdvancedRAGManager para agregar documentos
        """
        self.enabled = enabled
        self.interval_hours = interval_hours
        self.website_enabled = website_enabled
        self.website_url = website_url
        self.instagram_enabled = instagram_enabled
        self.instagram_token = instagram_token
        self.facebook_enabled = facebook_enabled
        self.facebook_token = facebook_token
        self.rag_manager = rag_manager
        
        # Inicializar ingester
        self.ingester = MultiSourceIngester(rag_manager=rag_manager)
        
        # Thread para scheduler
        self._scheduler_thread: Optional[threading.Thread] = None
        self._running = False
        
        # Si está habilitado, iniciar scheduler
        if self.enabled:
            self.start()
    
    def update_config(self, config: Dict[str, Any]):
        """
        Actualiza configuración desde dict.
        
        Args:
            config: Dict con configuración de ingesta
        """
        # Detener scheduler actual
        self.stop()
        
        # Actualizar configuración
        self.enabled = config.get("ingestion_scheduler_enabled", False)
        self.interval_hours = config.get("ingestion_interval_hours", 6)
        self.website_enabled = config.get("ingestion_website_enabled", False)
        self.website_url = config.get("ingestion_website_url")
        self.instagram_enabled = config.get("ingestion_instagram_enabled", False)
        self.instagram_token = config.get("ingestion_instagram_token")
        self.facebook_enabled = config.get("ingestion_facebook_enabled", False)
        self.facebook_token = config.get("ingestion_facebook_token")
        
        # Reiniciar scheduler si está habilitado
        if self.enabled:
            self.start()
    
    def start(self):
        """Inicia el scheduler."""
        if self._running:
            return
        
        self._running = True
        
        # Configurar job según intervalo
        schedule.clear()  # Limpiar jobs anteriores
        schedule.every(self.interval_hours).hours.do(self._run_ingestion)
        
        # Iniciar thread del scheduler
        self._scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self._scheduler_thread.start()
        
        print(f"✅ Scheduler de ingesta iniciado (cada {self.interval_hours} horas)")
    
    def stop(self):
        """Detiene el scheduler."""
        self._running = False
        schedule.clear()
        print("⏹️ Scheduler de ingesta detenido")
    
    def _scheduler_loop(self):
        """Loop del scheduler (ejecuta en thread separado)."""
        while self._running:
            schedule.run_pending()
            time.sleep(60)  # Revisar cada minuto
    
    def _run_ingestion(self):
        """Ejecuta ingesta automática según fuentes habilitadas."""
        print(f"🔄 Iniciando ingesta automática (scheduler cada {self.interval_hours}h)...")
        
        try:
            results = self.run_ingestion_now()
            print(f"✅ Ingesta automática completada: {len(results)} fuentes procesadas")
        except Exception as e:
            print(f"❌ Error en ingesta automática: {e}")
    
    def run_ingestion_now(self) -> Dict[str, Any]:
        """
        Ejecuta ingesta manual (Run now).
        
        Returns:
            Dict con resultados por fuente
        """
        results = {
            "website": {"success": False, "documents": 0},
            "instagram": {"success": False, "documents": 0},
            "facebook": {"success": False, "documents": 0},
        }
        
        # Ingesta de Website
        if self.website_enabled and self.website_url:
            try:
                print(f"🌐 Ingestando website: {self.website_url}")
                docs = self.ingester.ingest_website(self.website_url)
                if self.rag_manager and docs:
                    self.rag_manager.add_documents([doc.to_langchain_document() for doc in docs])
                results["website"] = {
                    "success": True,
                    "documents": len(docs),
                    "message": f"✅ {len(docs)} documentos ingeridos desde website",
                }
            except Exception as e:
                results["website"] = {
                    "success": False,
                    "documents": 0,
                    "message": f"❌ Error: {e}",
                }
        
        # Ingesta de Instagram
        if self.instagram_enabled and self.instagram_token:
            try:
                print(f"📷 Ingestando Instagram...")
                docs = self.ingester.ingest_instagram(self.instagram_token)
                if self.rag_manager and docs:
                    self.rag_manager.add_documents([doc.to_langchain_document() for doc in docs])
                results["instagram"] = {
                    "success": True,
                    "documents": len(docs),
                    "message": f"✅ {len(docs)} documentos ingeridos desde Instagram",
                }
            except Exception as e:
                results["instagram"] = {
                    "success": False,
                    "documents": 0,
                    "message": f"❌ Error: {e}",
                }
        
        # Ingesta de Facebook
        if self.facebook_enabled and self.facebook_token:
            try:
                print(f"📘 Ingestando Facebook...")
                docs = self.ingester.ingest_facebook(self.facebook_token)
                if self.rag_manager and docs:
                    self.rag_manager.add_documents([doc.to_langchain_document() for doc in docs])
                results["facebook"] = {
                    "success": True,
                    "documents": len(docs),
                    "message": f"✅ {len(docs)} documentos ingeridos desde Facebook",
                }
            except Exception as e:
                results["facebook"] = {
                    "success": False,
                    "documents": 0,
                    "message": f"❌ Error: {e}",
                }
        
        return results
    
    def get_status(self) -> Dict[str, Any]:
        """
        Retorna estado del scheduler.
        
        Returns:
            Dict con estado actual
        """
        return {
            "enabled": self.enabled,
            "running": self._running,
            "interval_hours": self.interval_hours,
            "next_run": self._get_next_run_time(),
            "sources": {
                "website": {"enabled": self.website_enabled, "url": self.website_url},
                "instagram": {"enabled": self.instagram_enabled},
                "facebook": {"enabled": self.facebook_enabled},
            },
        }
    
    def _get_next_run_time(self) -> Optional[str]:
        """Retorna próximo tiempo de ejecución."""
        if not self._running:
            return None
        
        jobs = schedule.get_jobs()
        if jobs:
            next_run = jobs[0].next_run
            return next_run.strftime("%Y-%m-%d %H:%M:%S") if next_run else None
        return None

