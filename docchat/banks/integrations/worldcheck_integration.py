"""
Integración completa con World-Check One API (LSEG).
"""

from __future__ import annotations

import logging
import requests
from typing import Dict, Any, List, Optional
from datetime import datetime

from ..schemas import SanctionHit, PEPHit

logger = logging.getLogger(__name__)


class WorldCheckIntegration:
    """Integración con World-Check One API de LSEG."""
    
    def __init__(self, api_key: str, api_url: str = "https://api.worldcheck.com/v1"):
        self.api_key = api_key
        self.api_url = api_url
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    
    def screen_entity(
        self,
        name: str,
        date_of_birth: Optional[str] = None,
        nationality: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Hace screening de una entidad contra World-Check.
        
        Returns:
            Dict con hits, PEP status, adverse media, etc.
        """
        try:
            payload = {
                "name": name,
                "date_of_birth": date_of_birth,
                "nationality": nationality
            }
            
            response = requests.post(
                f"{self.api_url}/screening",
                json=payload,
                headers=self.headers,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "success": True,
                    "hits": self._parse_hits(data),
                    "pep_status": data.get("pep_status"),
                    "adverse_media": data.get("adverse_media", []),
                    "sanctions": data.get("sanctions", [])
                }
            else:
                logger.error(f"World-Check API error: {response.status_code} - {response.text}")
                return {"success": False, "error": f"HTTP {response.status_code}"}
        
        except Exception as e:
            logger.error(f"Error en World-Check screening: {e}")
            return {"success": False, "error": str(e)}
    
    def _parse_hits(self, data: Dict[str, Any]) -> List[SanctionHit]:
        """Parsea hits de World-Check a SanctionHit."""
        hits = []
        
        for hit in data.get("matches", []):
            hits.append(SanctionHit(
                name=hit.get("name", ""),
                match_type=hit.get("match_type", "fuzzy"),
                confidence=hit.get("confidence", 0.0),
                list_name="World-Check",
                list_id=hit.get("id"),
                reason=hit.get("reason"),
                url=hit.get("url")
            ))
        
        return hits

