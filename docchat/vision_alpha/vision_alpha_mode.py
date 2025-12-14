"""
Vision Alpha Mode - Integración completa del sistema BettaFish
Sistema multi-agente de análisis de opinión pública y generación de reportes profesionales
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional, List, Iterator
from datetime import datetime
import json
import asyncio
from concurrent.futures import ThreadPoolExecutor

# Agregar el directorio de vision_alpha al path para imports
VISION_ALPHA_DIR = Path(__file__).parent
sys.path.insert(0, str(VISION_ALPHA_DIR))

from ..config import AppConfig
from .config_adapter import create_bettafish_config

# Imports de BettaFish engines
try:
    from QueryEngine.agent import DeepSearchAgent as QueryAgent
    from MediaEngine.agent import DeepSearchAgent as MediaAgent
    from InsightEngine.agent import DeepSearchAgent as InsightAgent
    from ReportEngine.agent import ReportAgent
    from ForumEngine.monitor import start_forum_monitoring, stop_forum_monitoring
    from ForumEngine.llm_host import ForumHost
    BETTAFISH_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ Advertencia: No se pudieron importar algunos componentes de BettaFish: {e}")
    BETTAFISH_AVAILABLE = False


class VisionAlphaMode:
    """
    Vision Alpha Mode - Sistema completo de análisis multi-agente BettaFish
    
    Integra:
    - QueryEngine: Búsqueda de información en web
    - MediaEngine: Análisis de contenido multimedia
    - InsightEngine: Análisis de base de datos y sentimientos
    - ReportEngine: Generación de reportes profesionales HTML/PDF
    - ForumEngine: Colaboración entre agentes
    """
    
    def __init__(self, config: AppConfig, provider: str = "openai"):
        if not BETTAFISH_AVAILABLE:
            raise ImportError("Los componentes de BettaFish no están disponibles. Verifica las dependencias.")
        
        self.config = config
        self.provider = provider
        
        # Adaptador de configuración
        self.bf_config = create_bettafish_config(config)
        
        # Inicializar engines
        self._initialize_engines()
        
        # Inicializar ForumEngine
        self._initialize_forum()
        
        # Estado de sesiones
        self.sessions: Dict[str, Dict[str, Any]] = {}
        
        print("✅ Vision Alpha Mode inicializado - Sistema multi-agente BettaFish listo")
    
    def _initialize_engines(self):
        """Inicializa todos los engines de BettaFish"""
        try:
            # Query Engine - Búsqueda web
            self.query_agent = QueryAgent(config=self.bf_config)
            print("✅ QueryEngine inicializado")
        except Exception as e:
            print(f"⚠️ Error inicializando QueryEngine: {e}")
            self.query_agent = None
        
        try:
            # Media Engine - Análisis multimedia
            self.media_agent = MediaAgent(config=self.bf_config)
            print("✅ MediaEngine inicializado")
        except Exception as e:
            print(f"⚠️ Error inicializando MediaEngine: {e}")
            self.media_agent = None
        
        try:
            # Insight Engine - Análisis de base de datos
            self.insight_agent = InsightAgent(config=self.bf_config)
            print("✅ InsightEngine inicializado")
        except Exception as e:
            print(f"⚠️ Error inicializando InsightEngine: {e}")
            self.insight_agent = None
        
        try:
            # Report Engine - Generación de reportes
            self.report_agent = ReportAgent(config=self.bf_config)
            print("✅ ReportEngine inicializado")
        except Exception as e:
            print(f"⚠️ Error inicializando ReportEngine: {e}")
            self.report_agent = None
    
    def _initialize_forum(self):
        """Inicializa ForumEngine para colaboración entre agentes"""
        try:
            # Inicializar ForumEngine
            start_forum_monitoring()
            self.forum_host = ForumHost(config=self.bf_config)
            print("✅ ForumEngine inicializado")
        except Exception as e:
            print(f"⚠️ Error inicializando ForumEngine: {e}")
            self.forum_host = None
    
    def analyze_query(
        self,
        query: str,
        session_id: Optional[str] = None,
        use_query_engine: bool = True,
        use_media_engine: bool = True,
        use_insight_engine: bool = False
    ) -> Iterator[str]:
        """
        Ejecuta análisis completo usando los engines disponibles
        
        Args:
            query: Consulta del usuario
            session_id: ID de sesión (opcional)
            use_query_engine: Usar QueryEngine para búsqueda web
            use_media_engine: Usar MediaEngine para análisis multimedia
            use_insight_engine: Usar InsightEngine para análisis de BD (requiere BD configurada)
        
        Yields:
            Mensajes de progreso y resultados
        """
        if not session_id:
            session_id = f"vision_alpha_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Inicializar sesión
        if session_id not in self.sessions:
            self.sessions[session_id] = {
                "query": query,
                "results": {},
                "start_time": datetime.now(),
                "status": "running"
            }
        
        yield f"🔍 Iniciando análisis: {query}\n\n"
        
        results = {}
        
        # 1. Query Engine - Búsqueda web
        if use_query_engine and self.query_agent:
            try:
                yield "📡 QueryEngine: Buscando información en web...\n"
                query_result = self.query_agent.run(query=query)
                results["query"] = query_result
                yield f"✅ QueryEngine completado\n\n"
            except Exception as e:
                yield f"❌ Error en QueryEngine: {str(e)}\n\n"
        
        # 2. Media Engine - Análisis multimedia
        if use_media_engine and self.media_agent:
            try:
                yield "🎬 MediaEngine: Analizando contenido multimedia...\n"
                media_result = self.media_agent.run(query=query)
                results["media"] = media_result
                yield f"✅ MediaEngine completado\n\n"
            except Exception as e:
                yield f"❌ Error en MediaEngine: {str(e)}\n\n"
        
        # 3. Insight Engine - Análisis de BD (opcional)
        if use_insight_engine and self.insight_agent:
            try:
                yield "💡 InsightEngine: Analizando base de datos...\n"
                insight_result = self.insight_agent.run(query=query)
                results["insight"] = insight_result
                yield f"✅ InsightEngine completado\n\n"
            except Exception as e:
                yield f"❌ Error en InsightEngine: {str(e)}\n\n"
        
        # Guardar resultados en sesión
        self.sessions[session_id]["results"] = results
        self.sessions[session_id]["status"] = "completed"
        
        yield f"📊 Análisis completado. Resultados guardados en sesión: {session_id}\n"
    
    def generate_report(
        self,
        session_id: str,
        report_title: Optional[str] = None,
        template_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Genera un reporte profesional usando ReportEngine
        
        Args:
            session_id: ID de sesión con resultados de análisis
            report_title: Título del reporte (opcional)
            template_name: Nombre del template (opcional)
        
        Returns:
            Dict con información del reporte generado
        """
        if session_id not in self.sessions:
            return {
                "success": False,
                "error": f"Sesión {session_id} no encontrada"
            }
        
        if not self.report_agent:
            return {
                "success": False,
                "error": "ReportEngine no está disponible"
            }
        
        session = self.sessions[session_id]
        results = session["results"]
        query = session["query"]
        
        # Preparar datos para el reporte
        report_data = {
            "query": query,
            "results": results,
            "title": report_title or query,
            "template": template_name
        }
        
        try:
            # Generar reporte usando ReportEngine
            report_path = self.report_agent.generate_report(
                query=query,
                analysis_results=results,
                title=report_title or query,
                template=template_name
            )
            
            return {
                "success": True,
                "report_path": str(report_path),
                "session_id": session_id,
                "title": report_title or query
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_session_results(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Obtiene los resultados de una sesión"""
        return self.sessions.get(session_id)
    
    def list_sessions(self) -> List[Dict[str, Any]]:
        """Lista todas las sesiones"""
        return [
            {
                "session_id": sid,
                "query": data["query"],
                "status": data["status"],
                "start_time": data["start_time"].isoformat()
            }
            for sid, data in self.sessions.items()
        ]
    
    def cleanup(self):
        """Limpia recursos y detiene ForumEngine"""
        try:
            if self.forum_host:
                stop_forum_monitoring()
        except Exception as e:
            print(f"Error deteniendo ForumEngine: {e}")


# Instancia global
_vision_alpha_instance: Optional[VisionAlphaMode] = None


def get_vision_alpha_mode(
    config: AppConfig,
    provider: str = "openai"
) -> VisionAlphaMode:
    """Obtiene o crea la instancia global de Vision Alpha Mode"""
    global _vision_alpha_instance
    
    if _vision_alpha_instance is None:
        _vision_alpha_instance = VisionAlphaMode(config=config, provider=provider)
    
    return _vision_alpha_instance


def run_vision_alpha_mode(
    query: str,
    config: Optional[AppConfig] = None,
    provider: str = "openai",
    session_id: Optional[str] = None,
    use_query_engine: bool = True,
    use_media_engine: bool = True,
    use_insight_engine: bool = False
) -> Iterator[str]:
    """Ejecuta análisis en Vision Alpha Mode"""
    if config is None:
        from ..config import load_config
        config = load_config()
    
    mode = get_vision_alpha_mode(config=config, provider=provider)
    
    yield from mode.analyze_query(
        query=query,
        session_id=session_id,
        use_query_engine=use_query_engine,
        use_media_engine=use_media_engine,
        use_insight_engine=use_insight_engine
    )

