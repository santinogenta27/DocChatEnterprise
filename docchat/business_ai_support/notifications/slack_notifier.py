"""Slack Notifier - Sends notifications to Slack via webhook."""

from __future__ import annotations

from typing import Dict, Any, Optional, List
import json

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False


class SlackNotifier:
    """Sends notifications to Slack via webhook."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize SlackNotifier.
        
        Args:
            config: Slack configuration dict with:
                - webhook_url: Slack webhook URL
        """
        self.webhook_url = config.get("webhook_url", "")
        
        if not REQUESTS_AVAILABLE:
            print("⚠️ requests no disponible. Instala con: pip install requests")
    
    def send(
        self,
        text: str,
        blocks: Optional[List[Dict[str, Any]]] = None,
        channel: Optional[str] = None
    ) -> bool:
        """Send Slack notification.
        
        Args:
            text: Notification text
            blocks: Slack blocks for rich formatting (optional)
            channel: Slack channel to send to (optional, uses webhook default)
            
        Returns:
            True if sent successfully
        """
        if not REQUESTS_AVAILABLE:
            print("⚠️ requests no disponible. No se puede enviar notificación a Slack.")
            return False
        
        if not self.webhook_url:
            print("⚠️ Slack webhook URL no configurada")
            return False
        
        try:
            payload = {
                "text": text
            }
            
            if blocks:
                payload["blocks"] = blocks
            
            if channel:
                payload["channel"] = channel
            
            response = requests.post(
                self.webhook_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if response.status_code == 200:
                print(f"✅ Notificación enviada a Slack")
                return True
            else:
                print(f"❌ Error enviando a Slack: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Error enviando notificación a Slack: {e}")
            import traceback
            traceback.print_exc()
            return False

