"""
Handler para Slack
"""

from __future__ import annotations

from typing import List
from langchain_core.documents import Document
import requests

from .base_handler import BaseIntegrationHandler


class SlackHandler(BaseIntegrationHandler):
    """Handler para Slack."""
    
    def search(self, query: str, access_token: str, max_results: int = 10) -> List[Document]:
        """Busca en Slack."""
        headers = {"Authorization": f"Bearer {access_token}"}
        
        # Buscar mensajes
        search_url = "https://slack.com/api/search.messages"
        params = {"query": query, "count": max_results}
        
        response = requests.get(search_url, headers=headers, params=params)
        if response.status_code != 200:
            return []
        
        data = response.json()
        if not data.get("ok"):
            return []
        
        messages = data.get("messages", {}).get("matches", [])
        documents = []
        
        for msg in messages[:max_results]:
            try:
                text = msg.get("text", "")
                if text:
                    documents.append(Document(
                        page_content=text,
                        metadata={
                            "source": "slack",
                            "message_id": msg.get("ts", ""),
                            "channel": msg.get("channel", {}).get("name", ""),
                            "user": msg.get("username", ""),
                            "integration": "slack"
                        }
                    ))
            except Exception as e:
                print(f"Error procesando mensaje Slack: {e}")
        
        return documents
    
    def refresh_token(self, refresh_token: str) -> Optional[str]:
        """Refresca token de Slack."""
        # Slack usa refresh tokens de forma diferente
        # Implementar según necesidad
        return None


