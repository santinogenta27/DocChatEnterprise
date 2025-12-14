"""
Agent 6: Action Executor - Ejecuta acciones en sistemas externos (Salesforce, Jira, Slack, etc.)
"""

from __future__ import annotations

import logging
import requests
from typing import Dict, Any, List, Optional
from datetime import datetime

try:
    from simple_salesforce import Salesforce
    SALESFORCE_AVAILABLE = True
except ImportError:
    SALESFORCE_AVAILABLE = False
    logging.warning("simple-salesforce no disponible")

try:
    from atlassian import Jira
    JIRA_AVAILABLE = True
except ImportError:
    JIRA_AVAILABLE = False
    logging.warning("atlassian-python-api no disponible")

from .base_agent import BaseBanksAgent
from docchat.config import AppConfig

logger = logging.getLogger(__name__)


class ActionExecutorAgent(BaseBanksAgent):
    """Agente que ejecuta acciones en sistemas externos basado en outcomes."""
    
    def __init__(self, config: AppConfig):
        super().__init__(config, "action_executor")
        
        # Configuración de integraciones
        self.salesforce_config = self._load_salesforce_config()
        self.jira_config = self._load_jira_config()
        # Usar getattr en lugar de __dict__ para evitar problemas
        self.slack_webhook = getattr(config, "slack_webhook_url", "")
        self.teams_webhook = getattr(config, "teams_webhook_url", "")
        
        # Clientes de APIs (inicializados bajo demanda)
        self.salesforce_client = None
        self.jira_client = None
    
    def _load_salesforce_config(self) -> Dict[str, Any]:
        """Carga configuración de Salesforce."""
        return {
            "username": getattr(self.config, "salesforce_username", ""),
            "password": getattr(self.config, "salesforce_password", ""),
            "security_token": getattr(self.config, "salesforce_security_token", ""),
            "domain": getattr(self.config, "salesforce_domain", "login")
        }
    
    def _load_jira_config(self) -> Dict[str, Any]:
        """Carga configuración de Jira."""
        return {
            "url": getattr(self.config, "jira_url", ""),
            "username": getattr(self.config, "jira_username", ""),
            "api_token": getattr(self.config, "jira_api_token", "")
        }
    
    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ejecuta acciones basadas en los resultados del compliance check.
        
        Input state:
            - extracted_entities: List[EntityExtraction]
            - risk_scores: List[RiskScore]
            - generated_reports: List[Dict]
            - action_config: Dict (configuración de acciones a ejecutar)
        
        Output state:
            - actions_executed: List[Dict] con resultados de acciones
        """
        entities = state.get("extracted_entities", [])
        risk_scores = state.get("risk_scores", [])
        reports = state.get("generated_reports", [])
        action_config = state.get("action_config", {})
        
        actions_executed = []
        
        # Determinar qué acciones ejecutar
        for i, entity in enumerate(entities):
            risk_score = risk_scores[i] if i < len(risk_scores) else None
            
            if isinstance(risk_score, dict):
                score_value = risk_score.get("total_score", 0)
            else:
                score_value = getattr(risk_score, "total_score", 0) if risk_score else 0
            
            entity_name = entity.get("name") if isinstance(entity, dict) else getattr(entity, "name", "Unknown")
            
            # Ejecutar acciones según score y configuración
            if action_config.get("update_salesforce", False):
                try:
                    result = self._update_salesforce(entity, risk_score, action_config)
                    if result:
                        actions_executed.append(result)
                except Exception as e:
                    logger.error(f"Error actualizando Salesforce: {e}")
            
            if action_config.get("create_jira_ticket", False) and score_value >= action_config.get("jira_threshold", 70):
                try:
                    result = self._create_jira_ticket(entity, risk_score, reports, action_config)
                    if result:
                        actions_executed.append(result)
                except Exception as e:
                    logger.error(f"Error creando ticket Jira: {e}")
            
            if action_config.get("send_notifications", False):
                try:
                    result = self._send_notifications(entity, risk_score, reports, action_config)
                    if result:
                        actions_executed.append(result)
                except Exception as e:
                    logger.error(f"Error enviando notificaciones: {e}")
            
            # Bloquear en core banking si score muy alto
            if action_config.get("block_core_banking", False) and score_value >= action_config.get("block_threshold", 90):
                try:
                    result = self._block_core_banking(entity, risk_score, action_config)
                    if result:
                        actions_executed.append(result)
                except Exception as e:
                    logger.error(f"Error bloqueando core banking: {e}")
        
        # Log de auditoría
        self.log_audit(
            action="external_actions",
            input_data={"entities_count": len(entities), "action_config": action_config},
            output_data={"actions_executed": len(actions_executed)}
        )
        
        state["actions_executed"] = actions_executed
        return state
    
    def _update_salesforce(self, entity: Any, risk_score: Any, config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Actualiza Salesforce Financial Services Cloud."""
        if not SALESFORCE_AVAILABLE or not all([
            self.salesforce_config.get("username"),
            self.salesforce_config.get("password"),
            self.salesforce_config.get("security_token")
        ]):
            return None
        
        try:
            # Inicializar cliente si no existe
            if not self.salesforce_client:
                self.salesforce_client = Salesforce(
                    username=self.salesforce_config["username"],
                    password=self.salesforce_config["password"],
                    security_token=self.salesforce_config["security_token"],
                    domain=self.salesforce_config["domain"]
                )
            
            # Extraer datos de la entidad
            if isinstance(entity, dict):
                entity_name = entity.get("name", "Unknown")
                entity_id = entity.get("id_number", "")
            else:
                entity_name = getattr(entity, "name", "Unknown")
                entity_id = getattr(entity, "id_number", "")
            
            score_value = 0
            if risk_score:
                score_value = risk_score.get("total_score") if isinstance(risk_score, dict) else getattr(risk_score, "total_score", 0)
            
            # Buscar o crear Opportunity/Account en Salesforce
            # En producción, usar el ID específico del cliente
            opportunity_id = config.get("salesforce_opportunity_id")
            
            if opportunity_id:
                # Actualizar Opportunity
                update_data = {
                    "KYC_Status__c": "KYC Review" if score_value < 50 else "High Risk",
                    "Risk_Score__c": score_value,
                    "KYC_Review_Date__c": datetime.now().isoformat()
                }
                
                self.salesforce_client.Opportunity.update(opportunity_id, update_data)
                
                # Añadir nota
                note = f"Compliance check completado. Risk Score: {score_value}/100. Entity: {entity_name}"
                self.salesforce_client.Note.create({
                    "ParentId": opportunity_id,
                    "Title": "KYC Compliance Check",
                    "Body": note
                })
                
                return {
                    "action": "salesforce_update",
                    "status": "success",
                    "opportunity_id": opportunity_id,
                    "data": update_data
                }
        
        except Exception as e:
            logger.error(f"Error en Salesforce update: {e}")
            return {
                "action": "salesforce_update",
                "status": "error",
                "error": str(e)
            }
        
        return None
    
    def _create_jira_ticket(self, entity: Any, risk_score: Any, reports: List[Any], config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Crea un ticket en Jira para investigación AML."""
        if not JIRA_AVAILABLE or not all([
            self.jira_config.get("url"),
            self.jira_config.get("username"),
            self.jira_config.get("api_token")
        ]):
            return None
        
        try:
            # Inicializar cliente si no existe
            if not self.jira_client:
                self.jira_client = Jira(
                    url=self.jira_config["url"],
                    username=self.jira_config["username"],
                    password=self.jira_config["api_token"]
                )
            
            # Extraer datos
            if isinstance(entity, dict):
                entity_name = entity.get("name", "Unknown")
            else:
                entity_name = getattr(entity, "name", "Unknown")
            
            score_value = 0
            explanation = ""
            if risk_score:
                score_value = risk_score.get("total_score") if isinstance(risk_score, dict) else getattr(risk_score, "total_score", 0)
                explanation = risk_score.get("explanation", "") if isinstance(risk_score, dict) else getattr(risk_score, "explanation", "")
            
            # Crear ticket
            issue_dict = {
                "project": {"key": config.get("jira_project_key", "AML")},
                "summary": f"AML Investigation Required: {entity_name} (Risk Score: {score_value})",
                "description": f"""
                **High Risk Entity Detected**
                
                Entity: {entity_name}
                Risk Score: {score_value}/100
                
                Explanation:
                {explanation}
                
                Reports Generated: {len(reports)}
                
                Action Required: Manual review and investigation.
                """,
                "issuetype": {"name": "Task"},
                "priority": {"name": "High" if score_value >= 80 else "Medium"}
            }
            
            new_issue = self.jira_client.create_issue(fields=issue_dict)
            
            return {
                "action": "jira_ticket_created",
                "status": "success",
                "ticket_id": new_issue.key,
                "ticket_url": f"{self.jira_config['url']}/browse/{new_issue.key}"
            }
        
        except Exception as e:
            logger.error(f"Error creando ticket Jira: {e}")
            return {
                "action": "jira_ticket_created",
                "status": "error",
                "error": str(e)
            }
    
    def _send_notifications(self, entity: Any, risk_score: Any, reports: List[Any], config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Envía notificaciones a Slack/Teams/Email."""
        results = []
        
        # Extraer datos
        if isinstance(entity, dict):
            entity_name = entity.get("name", "Unknown")
        else:
            entity_name = getattr(entity, "name", "Unknown")
        
        score_value = 0
        if risk_score:
            score_value = risk_score.get("total_score") if isinstance(risk_score, dict) else getattr(risk_score, "total_score", 0)
        
        # Slack
        if self.slack_webhook and config.get("notify_slack", True):
            try:
                message = {
                    "text": f"🚨 Compliance Alert: {entity_name}",
                    "blocks": [
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": f"*Compliance Check Completed*\n\n*Entity:* {entity_name}\n*Risk Score:* {score_value}/100\n*Reports:* {len(reports)}"
                            }
                        }
                    ]
                }
                
                response = requests.post(self.slack_webhook, json=message)
                if response.status_code == 200:
                    results.append({"platform": "slack", "status": "success"})
            except Exception as e:
                logger.error(f"Error enviando a Slack: {e}")
                results.append({"platform": "slack", "status": "error", "error": str(e)})
        
        # Microsoft Teams
        if self.teams_webhook and config.get("notify_teams", True):
            try:
                message = {
                    "@type": "MessageCard",
                    "@context": "https://schema.org/extensions",
                    "summary": f"Compliance Alert: {entity_name}",
                    "themeColor": "FF0000" if score_value >= 70 else "FFA500",
                    "title": "Compliance Check Alert",
                    "sections": [
                        {
                            "activityTitle": entity_name,
                            "facts": [
                                {"name": "Risk Score", "value": f"{score_value}/100"},
                                {"name": "Reports Generated", "value": str(len(reports))}
                            ]
                        }
                    ]
                }
                
                response = requests.post(self.teams_webhook, json=message)
                if response.status_code == 200:
                    results.append({"platform": "teams", "status": "success"})
            except Exception as e:
                logger.error(f"Error enviando a Teams: {e}")
                results.append({"platform": "teams", "status": "error", "error": str(e)})
        
        if results:
            return {
                "action": "notifications_sent",
                "status": "success",
                "results": results
            }
        
        return None
    
    def _block_core_banking(self, entity: Any, risk_score: Any, config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Bloquea onboarding en core banking si score muy alto."""
        core_banking_webhook = config.get("core_banking_webhook")
        if not core_banking_webhook:
            return None
        
        try:
            # Extraer datos
            if isinstance(entity, dict):
                entity_name = entity.get("name", "Unknown")
                entity_id = entity.get("id_number", "")
            else:
                entity_name = getattr(entity, "name", "Unknown")
                entity_id = getattr(entity, "id_number", "")
            
            score_value = 0
            if risk_score:
                score_value = risk_score.get("total_score") if isinstance(risk_score, dict) else getattr(risk_score, "total_score", 0)
            
            # Llamar webhook para bloquear
            payload = {
                "action": "freeze_account",
                "entity_id": entity_id,
                "entity_name": entity_name,
                "risk_score": score_value,
                "reason": "High risk score detected in compliance check"
            }
            
            response = requests.post(core_banking_webhook, json=payload, timeout=10)
            
            if response.status_code in [200, 201]:
                return {
                    "action": "core_banking_block",
                    "status": "success",
                    "entity_id": entity_id
                }
            else:
                return {
                    "action": "core_banking_block",
                    "status": "error",
                    "error": f"HTTP {response.status_code}"
                }
        
        except Exception as e:
            logger.error(f"Error bloqueando core banking: {e}")
            return {
                "action": "core_banking_block",
                "status": "error",
                "error": str(e)
            }

