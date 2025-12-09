"""
Agent 3: Screener - Valida contra listas de sanciones, PEP, adverse media.
"""

from __future__ import annotations

import logging
import requests
from typing import Dict, Any, List, Optional
from datetime import datetime

try:
    from rapidfuzz import fuzz, process
    RAPIDFUZZ_AVAILABLE = True
except ImportError:
    RAPIDFUZZ_AVAILABLE = False
    logging.warning("rapidfuzz no disponible, usando fallback")

from .base_agent import BaseBanksAgent
from ..schemas import SanctionHit, PEPHit, AdverseMediaHit
from docchat.config import AppConfig

try:
    from ..integrations.worldcheck_integration import WorldCheckIntegration
    WORLDCHECK_INTEGRATION_AVAILABLE = True
except ImportError:
    WORLDCHECK_INTEGRATION_AVAILABLE = False

logger = logging.getLogger(__name__)


class ScreenerAgent(BaseBanksAgent):
    """Agente que hace screening contra listas de sanciones, PEP, adverse media."""
    
    def __init__(self, config: AppConfig):
        super().__init__(config, "screener")
        
        # API Keys (opcionales, con fallbacks gratuitos)
        # Usar getattr en lugar de __dict__ para evitar problemas
        self.worldcheck_api_key = getattr(config, "worldcheck_api_key", "")
        self.dowjones_api_key = getattr(config, "dowjones_api_key", "")
        self.google_news_api_key = getattr(config, "google_news_api_key", "")
        
        # Inicializar integración World-Check si hay API key
        if WORLDCHECK_INTEGRATION_AVAILABLE and self.worldcheck_api_key:
            self.worldcheck = WorldCheckIntegration(self.worldcheck_api_key)
        else:
            self.worldcheck = None
        
        # Cache de resultados (usar Redis en producción)
        self.cache: Dict[str, Any] = {}
    
    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Hace screening de entidades extraídas.
        
        Input state:
            - extracted_entities: List[EntityExtraction]
        
        Output state:
            - sanction_hits: List[SanctionHit]
            - pep_hits: List[PEPHit]
            - adverse_media_hits: List[AdverseMediaHit]
        """
        entities = state.get("extracted_entities", [])
        
        # Verificar whitelist/blacklist
        try:
            from ..config_manager import BanksConfigManager
            config_manager = BanksConfigManager(self.config)
        except ImportError:
            config_manager = None
        
        sanction_hits = []
        pep_hits = []
        adverse_media_hits = []
        
        for entity in entities:
            name = entity.get("name") if isinstance(entity, dict) else getattr(entity, "name", None)
            if not name:
                continue
            
            # Skip si está en whitelist
            if config_manager and config_manager.is_whitelisted(name):
                logger.info(f"Entidad {name} está en whitelist, saltando screening")
                continue
            
            # Auto-flag si está en blacklist
            if config_manager and config_manager.is_blacklisted(name):
                logger.warning(f"Entidad {name} está en blacklist, flagging automáticamente")
                sanction_hits.append(SanctionHit(
                    name=name,
                    match_type="blacklist",
                    confidence=1.0,
                    list_name="Internal Blacklist",
                    reason="Entidad en lista negra interna"
                ))
                continue
            
            # Screening de sanciones
            try:
                hits = self._check_sanctions(name, entity)
                sanction_hits.extend(hits)
            except Exception as e:
                logger.error(f"Error en screening de sanciones para {name}: {e}")
            
            # Screening de PEP
            try:
                pep = self._check_pep(name, entity)
                if pep:
                    pep_hits.append(pep)
            except Exception as e:
                logger.error(f"Error en screening PEP para {name}: {e}")
            
            # Adverse media
            try:
                media = self._check_adverse_media(name)
                adverse_media_hits.extend(media)
            except Exception as e:
                logger.error(f"Error en adverse media para {name}: {e}")
        
        # Log de auditoría
        self.log_audit(
            action="screening",
            input_data={"entities_count": len(entities)},
            output_data={
                "sanction_hits": len(sanction_hits),
                "pep_hits": len(pep_hits),
                "adverse_media_hits": len(adverse_media_hits)
            }
        )
        
        state["sanction_hits"] = sanction_hits
        state["pep_hits"] = pep_hits
        state["adverse_media_hits"] = adverse_media_hits
        
        return state
    
    def _check_sanctions(self, name: str, entity: Any = None) -> List[SanctionHit]:
        """Verifica contra listas de sanciones."""
        hits = []
        
        # OFAC (gratuito, API pública)
        try:
            ofac_hits = self._check_ofac(name)
            hits.extend(ofac_hits)
        except Exception as e:
            logger.warning(f"Error en OFAC check: {e}")
        
        # EU Consolidated List (gratuito)
        try:
            eu_hits = self._check_eu_list(name)
            hits.extend(eu_hits)
        except Exception as e:
            logger.warning(f"Error en EU list check: {e}")
        
        # UN Sanctions (gratuito)
        try:
            un_hits = self._check_un_sanctions(name)
            hits.extend(un_hits)
        except Exception as e:
            logger.warning(f"Error en UN sanctions check: {e}")
        
        # World-Check (si hay API key) - PRIORITARIO
        if self.worldcheck:
            try:
                wc_hits = self._check_worldcheck(name, entity)
                hits.extend(wc_hits)
            except Exception as e:
                logger.warning(f"Error en World-Check: {e}")
        
        return hits
    
    def _check_ofac(self, name: str) -> List[SanctionHit]:
        """Verifica contra OFAC (US Treasury)."""
        # OFAC tiene una API, pero también listas descargables
        # Por ahora, simulación con fuzzy matching contra lista conocida
        # En producción, usar API oficial de OFAC
        
        # Lista de ejemplo (en producción, cargar desde fuente oficial)
        ofac_list = [
            "Ahmed Khan", "Mohammed Al-Qahtani",  # Ejemplos
        ]
        
        hits = []
        if RAPIDFUZZ_AVAILABLE:
            matches = process.extract(name, ofac_list, limit=3, scorer=fuzz.ratio)
            for match, score, _ in matches:
                if score >= 85:  # Threshold de confianza
                    hits.append(SanctionHit(
                        name=match,
                        match_type="fuzzy",
                        confidence=score / 100.0,
                        list_name="OFAC",
                        reason="Fuzzy match en lista OFAC"
                    ))
        else:
            # Fallback simple
            name_lower = name.lower()
            for ofac_name in ofac_list:
                if name_lower in ofac_name.lower() or ofac_name.lower() in name_lower:
                    hits.append(SanctionHit(
                        name=ofac_name,
                        match_type="partial",
                        confidence=0.7,
                        list_name="OFAC"
                    ))
        
        return hits
    
    def _check_eu_list(self, name: str) -> List[SanctionHit]:
        """Verifica contra EU Consolidated List."""
        # Similar a OFAC, usar API oficial o lista descargable
        # Por ahora, simulación
        return []
    
    def _check_un_sanctions(self, name: str) -> List[SanctionHit]:
        """Verifica contra UN Sanctions List."""
        # Similar a OFAC
        return []
    
    def _check_worldcheck(self, name: str, entity: Any = None) -> List[SanctionHit]:
        """Verifica contra World-Check One API (LSEG)."""
        if not self.worldcheck:
            return []
        
        try:
            # Extraer datos adicionales de la entidad si están disponibles
            date_of_birth = None
            nationality = None
            
            if entity:
                if isinstance(entity, dict):
                    date_of_birth = entity.get("date_of_birth")
                    nationality = entity.get("nationality")
                else:
                    date_of_birth = getattr(entity, "date_of_birth", None)
                    nationality = getattr(entity, "nationality", None)
            
            # Hacer screening con World-Check
            result = self.worldcheck.screen_entity(
                name=name,
                date_of_birth=date_of_birth,
                nationality=nationality
            )
            
            if result.get("success"):
                return result.get("hits", [])
            else:
                logger.warning(f"World-Check screening falló: {result.get('error')}")
                return []
        
        except Exception as e:
            logger.error(f"Error en World-Check API: {e}")
            return []
    
    def _check_pep(self, name: str, entity: Any) -> Optional[PEPHit]:
        """Verifica si es PEP (Politically Exposed Person)."""
        # Verificar si ya está marcado como PEP en la entidad
        if isinstance(entity, dict):
            pep_status = entity.get("pep_status")
        else:
            pep_status = getattr(entity, "pep_status", None)
        
        if pep_status and pep_status in ["1", "2", "3"]:
            return PEPHit(
                name=name,
                pep_level=int(pep_status),
                match_confidence=0.9,
                source="document_extraction"
            )
        
        # Verificar contra base de datos de PEP (en producción, usar API)
        # Por ahora, retornar None si no hay match
        return None
    
    def _check_adverse_media(self, name: str) -> List[AdverseMediaHit]:
        """Busca adverse media (noticias negativas)."""
        hits = []
        
        # Google News API (si está disponible)
        if self.google_news_api_key:
            try:
                google_hits = self._check_google_news(name)
                hits.extend(google_hits)
            except Exception as e:
                logger.warning(f"Error en Google News search: {e}")
        
        # En producción, también integrar:
        # - LexisNexis API
        # - Dow Jones Risk & Compliance API
        # - NewsAPI.org
        
        return hits
    
    def _check_google_news(self, name: str) -> List[AdverseMediaHit]:
        """Busca adverse media usando Google News API."""
        hits = []
        
        try:
            # Búsqueda en Google News
            query = f"{name} fraud OR corruption OR money laundering OR sanctions"
            url = "https://newsapi.org/v2/everything"
            params = {
                "q": query,
                "apiKey": self.google_news_api_key,
                "language": "en,es",
                "sortBy": "relevancy",
                "pageSize": 10
            }
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                for article in data.get("articles", []):
                    # Filtrar por relevancia (título debe contener el nombre)
                    title = article.get("title", "").lower()
                    if name.lower() in title:
                        hits.append(AdverseMediaHit(
                            name=name,
                            title=article.get("title", ""),
                            url=article.get("url", ""),
                            source=article.get("source", {}).get("name", "Unknown"),
                            date=article.get("publishedAt", ""),
                            relevance_score=0.8  # Alto si el nombre está en el título
                        ))
        except Exception as e:
            logger.error(f"Error en Google News API: {e}")
        
        return hits

