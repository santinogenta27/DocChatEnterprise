"""
Integración con Slack y Microsoft Teams.
"""

from __future__ import annotations

import logging
import requests
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


class SlackIntegration:
    """Integración con Slack via Webhooks."""
    
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url
    
    def send_compliance_alert(
        self,
        entity_name: str,
        risk_score: int,
        reports_count: int,
        details: Optional[str] = None
    ) -> Dict[str, Any]:
        """Envía alerta de compliance a Slack."""
        try:
            message = {
                "text": f"🚨 Compliance Alert: {entity_name}",
                "blocks": [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*Compliance Check Completed*\n\n*Entity:* {entity_name}\n*Risk Score:* {risk_score}/100\n*Reports:* {reports_count}"
                        }
                    }
                ]
            }
            
            if details:
                message["blocks"].append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Details:*\n{details}"
                    }
                })
            
            response = requests.post(self.webhook_url, json=message, timeout=10)
            
            if response.status_code == 200:
                return {"success": True, "platform": "slack"}
            else:
                return {"success": False, "error": f"HTTP {response.status_code}"}
        
        except Exception as e:
            logger.error(f"Error enviando a Slack: {e}")
            return {"success": False, "error": str(e)}


class TeamsIntegration:
    """Integración con Microsoft Teams via Webhooks."""
    
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url
    
    def send_compliance_alert(
        self,
        entity_name: str,
        risk_score: int,
        reports_count: int,
        details: Optional[str] = None
    ) -> Dict[str, Any]:
        """Envía alerta de compliance a Teams."""
        try:
            message = {
                "@type": "MessageCard",
                "@context": "https://schema.org/extensions",
                "summary": f"Compliance Alert: {entity_name}",
                "themeColor": "FF0000" if risk_score >= 70 else "FFA500",
                "title": "Compliance Check Alert",
                "sections": [
                    {
                        "activityTitle": entity_name,
                        "facts": [
                            {"name": "Risk Score", "value": f"{risk_score}/100"},
                            {"name": "Reports Generated", "value": str(reports_count)}
                        ]
                    }
                ]
            }
            
            if details:
                message["sections"][0]["text"] = details
            
            response = requests.post(self.webhook_url, json=message, timeout=10)
            
            if response.status_code == 200:
                return {"success": True, "platform": "teams"}
            else:
                return {"success": False, "error": f"HTTP {response.status_code}"}
        
        except Exception as e:
            logger.error(f"Error enviando a Teams: {e}")
            return {"success": False, "error": str(e)}

