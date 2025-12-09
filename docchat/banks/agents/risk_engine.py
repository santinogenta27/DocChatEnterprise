"""
Agent 4: Risk Engine - Calcula score de riesgo y explica decisiones.
"""

from __future__ import annotations

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

try:
    from langchain_anthropic import ChatAnthropic
    from langchain_openai import ChatOpenAI
    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False

from .base_agent import BaseBanksAgent
from ..schemas import RiskScore
from docchat.config import AppConfig

try:
    from ..config_manager import BanksConfigManager
    CONFIG_MANAGER_AVAILABLE = True
except ImportError:
    CONFIG_MANAGER_AVAILABLE = False

logger = logging.getLogger(__name__)

# Países de alto riesgo (ejemplo - en producción, usar lista oficial)
HIGH_RISK_COUNTRIES = {
    "Iran", "North Korea", "Syria", "Russia", "Myanmar", "Cuba",
    "Panama", "Cayman Islands", "British Virgin Islands", "Seychelles"
}


class RiskEngineAgent(BaseBanksAgent):
    """Agente que calcula score de riesgo con explicación completa."""
    
    def __init__(self, config: AppConfig):
        super().__init__(config, "risk_engine")
        
        if LLM_AVAILABLE:
            if config.anthropic_api_key:
                self.llm = ChatAnthropic(
                    model="claude-3-5-sonnet-20241022",
                    temperature=0.1,
                    api_key=config.anthropic_api_key
                )
            elif config.openai_api_key:
                self.llm = ChatOpenAI(
                    model="gpt-4o",
                    temperature=0.1,
                    api_key=config.openai_api_key
                )
            else:
                self.llm = None
        else:
            self.llm = None
        
        # Pesos configurables para scoring
        self.weights = {
            "country_risk": 0.40,
            "pep_risk": 0.25,
            "adverse_media_risk": 0.20,
            "transaction_risk": 0.10,
            "ubo_risk": 0.05
        }
    
    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calcula risk scores para todas las entidades.
        
        Input state:
            - extracted_entities: List[EntityExtraction]
            - sanction_hits: List[SanctionHit]
            - pep_hits: List[PEPHit]
            - adverse_media_hits: List[AdverseMediaHit]
        
        Output state:
            - risk_scores: List[RiskScore]
        """
        entities = state.get("extracted_entities", [])
        sanction_hits = state.get("sanction_hits", [])
        pep_hits = state.get("pep_hits", [])
        adverse_media_hits = state.get("adverse_media_hits", [])
        
        risk_scores = []
        
        for entity in entities:
            try:
                score = self._calculate_risk_score(
                    entity, sanction_hits, pep_hits, adverse_media_hits
                )
                risk_scores.append(score)
            except Exception as e:
                logger.error(f"Error calculando risk score: {e}")
                continue
        
        # Log de auditoría
        self.log_audit(
            action="risk_scoring",
            input_data={"entities_count": len(entities)},
            output_data={"scores_calculated": len(risk_scores)}
        )
        
        state["risk_scores"] = risk_scores
        return state
    
    def _calculate_risk_score(
        self,
        entity: Any,
        sanction_hits: List[Any],
        pep_hits: List[Any],
        adverse_media_hits: List[Any]
    ) -> RiskScore:
        """Calcula el risk score completo con explicación."""
        
        # Extraer datos de la entidad
        if isinstance(entity, dict):
            name = entity.get("name", "")
            nationality = entity.get("nationality", "")
            address = entity.get("address", "")
            ubo = entity.get("ubo", [])
            transactions = entity.get("transactions", [])
            pep_status = entity.get("pep_status")
        else:
            name = getattr(entity, "name", "")
            nationality = getattr(entity, "nationality", "")
            address = getattr(entity, "address", "")
            ubo = getattr(entity, "ubo", [])
            transactions = getattr(entity, "transactions", [])
            pep_status = getattr(entity, "pep_status", None)
        
        # 1. Country Risk (0.0 - 1.0)
        country_risk = self._calculate_country_risk(nationality, address)
        
        # 2. PEP Risk (0.0 - 1.0)
        pep_risk = self._calculate_pep_risk(pep_status, pep_hits, name)
        
        # 3. Adverse Media Risk (0.0 - 1.0)
        adverse_media_risk = self._calculate_adverse_media_risk(adverse_media_hits, name)
        
        # 4. Transaction Risk (0.0 - 1.0)
        transaction_risk = self._calculate_transaction_risk(transactions)
        
        # 5. UBO Risk (0.0 - 1.0)
        ubo_risk = self._calculate_ubo_risk(ubo)
        
        # Calcular score total (1-100)
        total_score = int(
            (country_risk * self.weights["country_risk"] +
             pep_risk * self.weights["pep_risk"] +
             adverse_media_risk * self.weights["adverse_media_risk"] +
             transaction_risk * self.weights["transaction_risk"] +
             ubo_risk * self.weights["ubo_risk"]) * 100
        )
        
        # Ajustar por sanction hits (crítico)
        if sanction_hits:
            for hit in sanction_hits:
                hit_name = hit.get("name") if isinstance(hit, dict) else getattr(hit, "name", "")
                if name and hit_name and name.lower() in hit_name.lower():
                    total_score = min(100, total_score + 50)  # +50 puntos por hit de sanción
        
        total_score = max(1, min(100, total_score))  # Asegurar rango 1-100
        
        # Generar explicación y evidencia
        explanation, evidence = self._generate_explanation(
            total_score, country_risk, pep_risk, adverse_media_risk,
            transaction_risk, ubo_risk, sanction_hits, name
        )
        
        breakdown = {
            "country_risk": country_risk,
            "pep_risk": pep_risk,
            "adverse_media_risk": adverse_media_risk,
            "transaction_risk": transaction_risk,
            "ubo_risk": ubo_risk,
            "sanction_hits_count": len(sanction_hits)
        }
        
        return RiskScore(
            total_score=total_score,
            country_risk=country_risk,
            pep_risk=pep_risk,
            adverse_media_risk=adverse_media_risk,
            transaction_risk=transaction_risk,
            ubo_risk=ubo_risk,
            breakdown=breakdown,
            explanation=explanation,
            evidence=evidence
        )
    
    def _calculate_country_risk(self, nationality: Optional[str], address: Optional[str]) -> float:
        """Calcula riesgo por país."""
        risk = 0.0
        
        # Verificar nacionalidad
        if nationality:
            for country in HIGH_RISK_COUNTRIES:
                if country.lower() in nationality.lower():
                    risk = max(risk, 0.8)
        
        # Verificar dirección
        if address:
            for country in HIGH_RISK_COUNTRIES:
                if country.lower() in address.lower():
                    risk = max(risk, 0.9)
        
        return risk
    
    def _calculate_pep_risk(self, pep_status: Optional[str], pep_hits: List[Any], name: str) -> float:
        """Calcula riesgo PEP."""
        if pep_status == "1":
            return 0.3
        elif pep_status == "2":
            return 0.6
        elif pep_status == "3":
            return 0.9
        
        # Verificar hits
        for hit in pep_hits:
            hit_name = hit.get("name") if isinstance(hit, dict) else getattr(hit, "name", "")
            if name and hit_name and name.lower() in hit_name.lower():
                level = hit.get("pep_level") if isinstance(hit, dict) else getattr(hit, "pep_level", 1)
                if level == 1:
                    return 0.3
                elif level == 2:
                    return 0.6
                elif level == 3:
                    return 0.9
        
        return 0.0
    
    def _calculate_adverse_media_risk(self, adverse_media_hits: List[Any], name: str) -> float:
        """Calcula riesgo por adverse media."""
        if not adverse_media_hits:
            return 0.0
        
        # Contar hits relevantes
        relevant_hits = 0
        for hit in adverse_media_hits:
            hit_name = hit.get("name") if isinstance(hit, dict) else getattr(hit, "name", "")
            if name and hit_name and name.lower() in hit_name.lower():
                relevant_hits += 1
        
        # Más hits = más riesgo
        if relevant_hits >= 3:
            return 0.8
        elif relevant_hits >= 2:
            return 0.5
        elif relevant_hits >= 1:
            return 0.3
        
        return 0.0
    
    def _calculate_transaction_risk(self, transactions: List[Any]) -> float:
        """Calcula riesgo por transacciones."""
        if not transactions:
            return 0.0
        
        risk = 0.0
        
        for txn in transactions:
            if isinstance(txn, dict):
                amount = txn.get("amount", 0)
                destination = txn.get("destination", "")
                currency = txn.get("currency", "USD")
            else:
                amount = getattr(txn, "amount", 0)
                destination = getattr(txn, "destination", "")
                currency = getattr(txn, "currency", "USD")
            
            # Transacciones grandes
            if amount > 100000:  # >€100k
                risk = max(risk, 0.6)
            elif amount > 10000:  # >€10k
                risk = max(risk, 0.3)
            
            # Destinos de alto riesgo
            if destination:
                for country in HIGH_RISK_COUNTRIES:
                    if country.lower() in destination.lower():
                        risk = max(risk, 0.9)
        
        return risk
    
    def _calculate_ubo_risk(self, ubo: List[Any]) -> float:
        """Calcula riesgo por UBO (Ultimate Beneficial Owner)."""
        if not ubo:
            return 0.0
        
        risk = 0.0
        
        for owner in ubo:
            if isinstance(owner, dict):
                country = owner.get("country", "")
            else:
                country = getattr(owner, "country", "")
            
            # UBO en países de alto riesgo
            for high_risk in HIGH_RISK_COUNTRIES:
                if high_risk.lower() in country.lower():
                    risk = max(risk, 0.7)
        
        return risk
    
    def _generate_explanation(
        self,
        total_score: int,
        country_risk: float,
        pep_risk: float,
        adverse_media_risk: float,
        transaction_risk: float,
        ubo_risk: float,
        sanction_hits: List[Any],
        name: str
    ) -> tuple[str, List[Dict[str, Any]]]:
        """Genera explicación detallada del score."""
        
        explanation_parts = []
        evidence = []
        
        if sanction_hits:
            explanation_parts.append(f"⚠️ CRÍTICO: {len(sanction_hits)} hit(s) en listas de sanciones")
            for hit in sanction_hits:
                hit_name = hit.get("name") if isinstance(hit, dict) else getattr(hit, "name", "")
                list_name = hit.get("list_name") if isinstance(hit, dict) else getattr(hit, "list_name", "")
                evidence.append({
                    "type": "sanction_hit",
                    "list": list_name,
                    "match": hit_name,
                    "severity": "critical"
                })
        
        if country_risk > 0.5:
            explanation_parts.append(f"País de alto riesgo detectado (score: {country_risk:.2f})")
        
        if pep_risk > 0.3:
            explanation_parts.append(f"PEP detectado (nivel de riesgo: {pep_risk:.2f})")
        
        if adverse_media_risk > 0.3:
            explanation_parts.append(f"Adverse media encontrado (riesgo: {adverse_media_risk:.2f})")
        
        if transaction_risk > 0.5:
            explanation_parts.append(f"Transacciones sospechosas detectadas (riesgo: {transaction_risk:.2f})")
        
        if ubo_risk > 0.5:
            explanation_parts.append(f"UBO en países de alto riesgo (riesgo: {ubo_risk:.2f})")
        
        if not explanation_parts:
            explanation_parts.append("No se detectaron riesgos significativos")
        
        explanation = f"Score de riesgo: {total_score}/100. " + ". ".join(explanation_parts)
        
        return explanation, evidence

