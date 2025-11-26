"""Tool for integrations (Slack, Teams, Webhooks)."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional
from datetime import datetime
import requests

from .base_tool import BaseTool, ToolResult


class IntegrationTool(BaseTool):
    """Tool for sending messages to Slack, Teams, or webhooks."""
    
    def __init__(self, config: Any):
        super().__init__(config)
        self.slack_webhook = config.slack_webhook_url
        self.teams_webhook = config.teams_webhook_url
    
    def get_name(self) -> str:
        return "integration_sender"
    
    def get_description(self) -> str:
        return "Send notifications to Slack, Microsoft Teams, or custom webhooks"
    
    def get_keywords(self) -> List[str]:
        return ["slack", "teams", "webhook", "notificar", "enviar mensaje", "notificación"]
    
    def execute(
        self,
        platform: str,
        message: str,
        title: Optional[str] = None,
        webhook_url: Optional[str] = None,
        **kwargs
    ) -> ToolResult:
        """Send message to integration platform."""
        try:
            platform_lower = platform.lower()
            
            if platform_lower == "slack":
                return self._send_slack(message, title, webhook_url)
            elif platform_lower == "teams" or platform_lower == "microsoft teams":
                return self._send_teams(message, title, webhook_url)
            elif platform_lower == "webhook":
                return self._send_webhook(message, webhook_url or "")
            else:
                return ToolResult(
                    success=False,
                    data=None,
                    message=f"Unsupported platform: {platform}",
                    metadata={}
                )
        except Exception as e:
            return ToolResult(
                success=False,
                data=None,
                message=f"Integration failed: {str(e)}",
                metadata={"error": str(e)}
            )
    
    def _send_slack(self, message: str, title: Optional[str], webhook_url: Optional[str]) -> ToolResult:
        """Send message to Slack."""
        webhook = webhook_url or self.slack_webhook
        if not webhook:
            return ToolResult(
                success=False,
                data=None,
                message="Slack webhook URL not configured",
                metadata={}
            )
        
        payload = {
            "text": title or "DocChat Notification",
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": message
                    }
                }
            ]
        }
        
        response = requests.post(webhook, json=payload, timeout=10)
        response.raise_for_status()
        
        return ToolResult(
            success=True,
            data={"platform": "slack", "message_sent": True},
            message="Message sent to Slack successfully",
            metadata={"platform": "slack"}
        )
    
    def _send_teams(self, message: str, title: Optional[str], webhook_url: Optional[str]) -> ToolResult:
        """Send message to Microsoft Teams."""
        webhook = webhook_url or self.teams_webhook
        if not webhook:
            return ToolResult(
                success=False,
                data=None,
                message="Teams webhook URL not configured",
                metadata={}
            )
        
        payload = {
            "@type": "MessageCard",
            "@context": "https://schema.org/extensions",
            "summary": title or "DocChat Notification",
            "title": title or "DocChat Notification",
            "text": message
        }
        
        response = requests.post(webhook, json=payload, timeout=10)
        response.raise_for_status()
        
        return ToolResult(
            success=True,
            data={"platform": "teams", "message_sent": True},
            message="Message sent to Teams successfully",
            metadata={"platform": "teams"}
        )
    
    def _send_webhook(self, message: str, webhook_url: str) -> ToolResult:
        """Send data to custom webhook."""
        if not webhook_url:
            return ToolResult(
                success=False,
                data=None,
                message="Webhook URL required",
                metadata={}
            )
        
        payload = {"message": message, "timestamp": str(datetime.now())}
        
        response = requests.post(webhook_url, json=payload, timeout=10)
        response.raise_for_status()
        
        return ToolResult(
            success=True,
            data={"webhook": webhook_url, "sent": True},
            message="Webhook called successfully",
            metadata={"webhook_url": webhook_url}
        )

