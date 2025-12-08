"""
Integración con Jira/ClickUp.
"""

from __future__ import annotations

import logging
from typing import Dict, Any, Optional
from datetime import datetime

try:
    from atlassian import Jira
    JIRA_AVAILABLE = True
except ImportError:
    JIRA_AVAILABLE = False
    logging.warning("atlassian-python-api no disponible")

logger = logging.getLogger(__name__)


class JiraIntegration:
    """Integración con Jira."""
    
    def __init__(self, url: str, username: str, api_token: str):
        if not JIRA_AVAILABLE:
            raise ImportError("atlassian-python-api no está instalado. Instala con: pip install atlassian-python-api")
        
        self.client = Jira(
            url=url,
            username=username,
            password=api_token
        )
        self.url = url
    
    def create_aml_ticket(
        self,
        entity_name: str,
        risk_score: int,
        explanation: str,
        project_key: str = "AML",
        priority: str = "High"
    ) -> Dict[str, Any]:
        """Crea un ticket de investigación AML en Jira."""
        try:
            issue_dict = {
                "project": {"key": project_key},
                "summary": f"AML Investigation Required: {entity_name} (Risk Score: {risk_score})",
                "description": f"""
**High Risk Entity Detected**

Entity: {entity_name}
Risk Score: {risk_score}/100

Explanation:
{explanation}

Action Required: Manual review and investigation.
                """,
                "issuetype": {"name": "Task"},
                "priority": {"name": priority}
            }
            
            new_issue = self.client.create_issue(fields=issue_dict)
            
            return {
                "success": True,
                "ticket_id": new_issue.key,
                "ticket_url": f"{self.url}/browse/{new_issue.key}"
            }
        
        except Exception as e:
            logger.error(f"Error creando ticket Jira: {e}")
            return {"success": False, "error": str(e)}

