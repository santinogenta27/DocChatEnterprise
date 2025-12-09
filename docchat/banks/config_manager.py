"""
Gestor de configuración de reglas de negocio para el modo BANKS.
Permite configurar reglas sin hard-coding.
"""

from __future__ import annotations

import json
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime

from docchat.config import AppConfig

logger = logging.getLogger(__name__)


class BanksConfigManager:
    """Gestor de configuración de reglas de negocio."""
    
    def __init__(self, config: AppConfig):
        self.config = config
        self.config_dir = Path(config.cache_dir) / "banks" / "config"
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.config_file = self.config_dir / "business_rules.json"
        
        # Cargar configuración
        self.business_rules = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Carga la configuración desde archivo."""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error cargando configuración: {e}")
        
        # Configuración por defecto
        return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Retorna configuración por defecto."""
        return {
            "risk_scoring": {
                "weights": {
                    "country_risk": 0.4,
                    "pep_risk": 0.25,
                    "adverse_media_risk": 0.2,
                    "transaction_risk": 0.1,
                    "ubo_risk": 0.05
                },
                "thresholds": {
                    "low_risk": 30,
                    "medium_risk": 50,
                    "high_risk": 70,
                    "critical_risk": 90
                }
            },
            "screening": {
                "fuzzy_match_threshold": 85,
                "enable_worldcheck": True,
                "enable_ofac": True,
                "enable_eu_list": True,
                "enable_un_sanctions": True
            },
            "pep_levels": {
                "level_1_weight": 0.3,
                "level_2_weight": 0.6,
                "level_3_weight": 0.9
            },
            "high_risk_countries": [
                "Russia", "Iran", "North Korea", "Syria", "Cuba",
                "Venezuela", "Myanmar", "Belarus", "Sudan", "Yemen"
            ],
            "transaction_thresholds": {
                "suspicious_amount": 10000,
                "high_risk_amount": 100000
            },
            "whitelist": [],
            "blacklist": [],
            "auto_actions": {
                "create_jira_ticket_threshold": 70,
                "block_core_banking_threshold": 90,
                "send_alert_threshold": 50
            },
            "updated_at": datetime.now().isoformat()
        }
    
    def save_config(self) -> bool:
        """Guarda la configuración en archivo."""
        try:
            self.business_rules["updated_at"] = datetime.now().isoformat()
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.business_rules, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            logger.error(f"Error guardando configuración: {e}")
            return False
    
    def get_risk_weights(self) -> Dict[str, float]:
        """Retorna los pesos para risk scoring."""
        return self.business_rules.get("risk_scoring", {}).get("weights", {})
    
    def get_risk_thresholds(self) -> Dict[str, int]:
        """Retorna los thresholds de riesgo."""
        return self.business_rules.get("risk_scoring", {}).get("thresholds", {})
    
    def get_high_risk_countries(self) -> List[str]:
        """Retorna lista de países de alto riesgo."""
        return self.business_rules.get("high_risk_countries", [])
    
    def is_whitelisted(self, entity_name: str) -> bool:
        """Verifica si una entidad está en whitelist."""
        whitelist = self.business_rules.get("whitelist", [])
        return any(entity_name.lower() in w.lower() or w.lower() in entity_name.lower() 
                  for w in whitelist)
    
    def is_blacklisted(self, entity_name: str) -> bool:
        """Verifica si una entidad está en blacklist."""
        blacklist = self.business_rules.get("blacklist", [])
        return any(entity_name.lower() in b.lower() or b.lower() in entity_name.lower() 
                  for b in blacklist)
    
    def add_to_whitelist(self, entity_name: str, reason: Optional[str] = None) -> bool:
        """Añade una entidad a la whitelist."""
        if entity_name not in self.business_rules.get("whitelist", []):
            if "whitelist" not in self.business_rules:
                self.business_rules["whitelist"] = []
            self.business_rules["whitelist"].append({
                "name": entity_name,
                "reason": reason,
                "added_at": datetime.now().isoformat()
            })
            return self.save_config()
        return False
    
    def add_to_blacklist(self, entity_name: str, reason: Optional[str] = None) -> bool:
        """Añade una entidad a la blacklist."""
        if entity_name not in self.business_rules.get("blacklist", []):
            if "blacklist" not in self.business_rules:
                self.business_rules["blacklist"] = []
            self.business_rules["blacklist"].append({
                "name": entity_name,
                "reason": reason,
                "added_at": datetime.now().isoformat()
            })
            return self.save_config()
        return False
    
    def update_risk_weights(self, weights: Dict[str, float]) -> bool:
        """Actualiza los pesos de risk scoring."""
        if "risk_scoring" not in self.business_rules:
            self.business_rules["risk_scoring"] = {}
        self.business_rules["risk_scoring"]["weights"] = weights
        return self.save_config()
    
    def update_risk_thresholds(self, thresholds: Dict[str, int]) -> bool:
        """Actualiza los thresholds de riesgo."""
        if "risk_scoring" not in self.business_rules:
            self.business_rules["risk_scoring"] = {}
        self.business_rules["risk_scoring"]["thresholds"] = thresholds
        return self.save_config()


