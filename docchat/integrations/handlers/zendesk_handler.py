"""
Handler para Zendesk
"""

from __future__ import annotations

from typing import List
from langchain_core.documents import Document
import requests
import base64

from .base_handler import BaseIntegrationHandler


class ZendeskHandler(BaseIntegrationHandler):
    """Handler para Zendesk."""
    
    def search(self, query: str, access_token: str, max_results: int = 10) -> List[Document]:
        """
        Busca en Zendesk.
        
        access_token debe ser: "subdomain|email:api_token"
        """
        # Parsear token
        if "|" in access_token:
            subdomain, auth = access_token.split("|", 1)
        else:
            subdomain = getattr(self.config, 'zendesk_subdomain', '')
            auth = access_token
        
        if not subdomain:
            print("⚠️ Necesitás configurar ZENDESK_SUBDOMAIN o incluirla en el token como 'subdomain|email:token'")
            return []
        
        # Crear headers con Basic Auth
        email, api_token = auth.split(":", 1)
        credentials = f"{email}/token:{api_token}"
        encoded = base64.b64encode(credentials.encode()).decode()
        headers = {
            "Authorization": f"Basic {encoded}",
            "Content-Type": "application/json"
        }
        
        zendesk_url = f"https://{subdomain}.zendesk.com"
        documents = []
        
        try:
            # Buscar tickets
            search_url = f"{zendesk_url}/api/v2/search.json"
            params = {
                "query": query,
                "type": "ticket",
                "per_page": max_results
            }
            
            response = requests.get(search_url, headers=headers, params=params, timeout=10)
            
            if response.status_code == 200:
                results = response.json().get("results", [])
                for ticket in results:
                    subject = ticket.get("subject", "")
                    description = ticket.get("description", "")
                    content = f"{subject}\n\n{description}".strip()
                    
                    if content:
                        documents.append(Document(
                            page_content=content[:5000],
                            metadata={
                                "source": f"zendesk - Ticket #{ticket.get('id', '')}",
                                "ticket_id": ticket.get("id", ""),
                                "subject": subject,
                                "status": ticket.get("status", ""),
                                "integration": "zendesk"
                            }
                        ))
        except Exception as e:
            print(f"Error buscando en Zendesk: {e}")
        
        return documents


