"""Microsoft Teams integration."""

from __future__ import annotations

from typing import List, Dict, Optional
import requests


class TeamsIntegration:
    """Microsoft Teams integration."""
    
    def __init__(self, webhook_url: Optional[str] = None):
        self.webhook_url = webhook_url
    
    def send_message(self, title: str, text: str, theme_color: str = "0078D4") -> bool:
        """Send message to Teams channel via webhook."""
        if not self.webhook_url:
            return False
        
        try:
            payload = {
                "@type": "MessageCard",
                "@context": "https://schema.org/extensions",
                "summary": title,
                "themeColor": theme_color,
                "title": title,
                "text": text
            }
            
            response = requests.post(self.webhook_url, json=payload, timeout=10)
            response.raise_for_status()
            return True
        except Exception as e:
            print(f"Error sending Teams message: {e}")
            return False
    
    def send_file(self, title: str, file_url: str, description: str = "") -> bool:
        """Send file notification to Teams."""
        if not self.webhook_url:
            return False
        
        try:
            payload = {
                "@type": "MessageCard",
                "@context": "https://schema.org/extensions",
                "summary": title,
                "themeColor": "0078D4",
                "title": title,
                "text": description,
                "potentialAction": [{
                    "@type": "OpenUri",
                    "name": "View File",
                    "targets": [{"os": "default", "uri": file_url}]
                }]
            }
            
            response = requests.post(self.webhook_url, json=payload, timeout=10)
            response.raise_for_status()
            return True
        except Exception as e:
            print(f"Error sending Teams file: {e}")
            return False



