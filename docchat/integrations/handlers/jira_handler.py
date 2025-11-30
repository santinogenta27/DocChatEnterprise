"""
Handler para Jira
"""

from __future__ import annotations

from typing import List
from langchain_core.documents import Document
import requests
import base64

from .base_handler import BaseIntegrationHandler


class JiraHandler(BaseIntegrationHandler):
    """Handler para Jira."""
    
    def search(self, query: str, access_token: str, max_results: int = 10) -> List[Document]:
        """
        Busca en Jira.
        
        access_token debe ser: "email:api_token" o "jira_url|email:api_token"
        """
        # Parsear token (puede ser "url|email:token" o solo "email:token")
        if "|" in access_token:
            jira_url, auth = access_token.split("|", 1)
        else:
            jira_url = None
            auth = access_token
        
        # Si no hay URL, usar la del config o pedirla
        if not jira_url:
            jira_url = getattr(self.config, 'jira_url', '')
            if not jira_url:
                print("⚠️ Necesitás configurar JIRA_URL en .env o incluirla en el token como 'url|email:token'")
                return []
        
        # Asegurar que la URL no termine en /
        jira_url = jira_url.rstrip('/')
        
        # Crear headers con Basic Auth
        email, api_token = auth.split(":", 1)
        credentials = f"{email}:{api_token}"
        encoded = base64.b64encode(credentials.encode()).decode()
        headers = {
            "Authorization": f"Basic {encoded}",
            "Accept": "application/json"
        }
        
        documents = []
        
        try:
            # Buscar issues
            search_url = f"{jira_url}/rest/api/3/search"
            params = {
                "jql": f'text ~ "{query}" OR summary ~ "{query}"',
                "maxResults": max_results,
                "fields": "summary,description,status,assignee,reporter"
            }
            
            response = requests.get(search_url, headers=headers, params=params, timeout=10)
            
            if response.status_code == 200:
                issues = response.json().get("issues", [])
                for issue in issues:
                    key = issue.get("key", "")
                    fields = issue.get("fields", {})
                    summary = fields.get("summary", "")
                    description = fields.get("description", {}).get("content", [])
                    
                    # Extraer texto de description (puede ser formato ADF)
                    desc_text = ""
                    if isinstance(description, list):
                        for item in description:
                            if isinstance(item, dict):
                                if item.get("type") == "paragraph":
                                    content = item.get("content", [])
                                    for para in content:
                                        if para.get("type") == "text":
                                            desc_text += para.get("text", "") + "\n"
                    
                    content = f"{summary}\n\n{desc_text}".strip()
                    
                    documents.append(Document(
                        page_content=content[:5000],
                        metadata={
                            "source": f"jira - {key}",
                            "issue_key": key,
                            "summary": summary,
                            "status": fields.get("status", {}).get("name", ""),
                            "integration": "jira"
                        }
                    ))
        except Exception as e:
            print(f"Error buscando en Jira: {e}")
            import traceback
            traceback.print_exc()
        
        return documents


