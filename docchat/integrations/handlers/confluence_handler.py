"""
Handler para Confluence
"""

from __future__ import annotations

from typing import List
from langchain_core.documents import Document
import requests
import base64

from .base_handler import BaseIntegrationHandler


class ConfluenceHandler(BaseIntegrationHandler):
    """Handler para Confluence."""
    
    def search(self, query: str, access_token: str, max_results: int = 10) -> List[Document]:
        """
        Busca en Confluence.
        
        access_token debe ser: "base_url|email:api_token"
        """
        # Parsear token
        if "|" in access_token:
            base_url, auth = access_token.split("|", 1)
        else:
            base_url = getattr(self.config, 'confluence_base_url', '')
            auth = access_token
        
        if not base_url:
            print("⚠️ Necesitás configurar CONFLUENCE_BASE_URL o incluirla en el token como 'url|email:token'")
            return []
        
        base_url = base_url.rstrip('/')
        
        # Crear headers con Basic Auth
        email, api_token = auth.split(":", 1)
        credentials = f"{email}:{api_token}"
        encoded = base64.b64encode(credentials.encode()).decode()
        headers = {
            "Authorization": f"Basic {encoded}",
            "Content-Type": "application/json"
        }
        
        documents = []
        
        try:
            # Buscar contenido
            search_url = f"{base_url}/rest/api/content/search"
            params = {
                "cql": f"text ~ \"{query}\"",
                "limit": max_results,
                "expand": "body.storage,version"
            }
            
            response = requests.get(search_url, headers=headers, params=params, timeout=10)
            
            if response.status_code == 200:
                results = response.json().get("results", [])
                for page in results:
                    title = page.get("title", "")
                    body = page.get("body", {}).get("storage", {}).get("value", "")
                    
                    # Limpiar HTML básico
                    import re
                    text = re.sub(r'<[^>]+>', ' ', body)
                    text = re.sub(r'\s+', ' ', text).strip()
                    
                    content = f"{title}\n\n{text}".strip()
                    
                    if content:
                        documents.append(Document(
                            page_content=content[:5000],
                            metadata={
                                "source": f"confluence - {title}",
                                "page_id": page.get("id", ""),
                                "title": title,
                                "space": page.get("space", {}).get("name", ""),
                                "integration": "confluence"
                            }
                        ))
        except Exception as e:
            print(f"Error buscando en Confluence: {e}")
        
        return documents


