"""
Handler para GitHub
"""

from __future__ import annotations

from typing import List
from langchain_core.documents import Document
import requests

from .base_handler import BaseIntegrationHandler


class GitHubHandler(BaseIntegrationHandler):
    """Handler para GitHub."""
    
    def search(self, query: str, access_token: str, max_results: int = 10) -> List[Document]:
        """Busca en GitHub (issues, PRs, code)."""
        headers = {
            "Authorization": f"token {access_token}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        documents = []
        
        # Buscar en issues
        try:
            issues_url = "https://api.github.com/search/issues"
            params = {"q": query, "per_page": max_results // 3}
            response = requests.get(issues_url, headers=headers, params=params, timeout=10)
            
            if response.status_code == 200:
                issues = response.json().get("items", [])
                for issue in issues:
                    documents.append(Document(
                        page_content=f"{issue.get('title', '')}\n\n{issue.get('body', '')}",
                        metadata={
                            "source": f"github - Issue #{issue.get('number', '')}",
                            "issue_id": issue.get("id", ""),
                            "title": issue.get("title", ""),
                            "url": issue.get("html_url", ""),
                            "integration": "github"
                        }
                    ))
        except Exception as e:
            print(f"Error buscando issues en GitHub: {e}")
        
        # Buscar en código
        try:
            code_url = "https://api.github.com/search/code"
            params = {"q": query, "per_page": max_results // 3}
            response = requests.get(code_url, headers=headers, params=params, timeout=10)
            
            if response.status_code == 200:
                code_results = response.json().get("items", [])
                for item in code_results:
                    # Obtener contenido del archivo
                    file_url = item.get("url", "")
                    if file_url:
                        file_response = requests.get(file_url, headers=headers, timeout=10)
                        if file_response.status_code == 200:
                            file_data = file_response.json()
                            content = file_data.get("content", "")
                            if content:
                                import base64
                                try:
                                    decoded = base64.b64decode(content).decode('utf-8', errors='ignore')
                                    documents.append(Document(
                                        page_content=decoded[:5000],
                                        metadata={
                                            "source": f"github - {item.get('name', '')}",
                                            "file_path": item.get("path", ""),
                                            "repository": item.get("repository", {}).get("full_name", ""),
                                            "integration": "github"
                                        }
                                    ))
                                except Exception:
                                    pass
        except Exception as e:
            print(f"Error buscando código en GitHub: {e}")
        
        return documents[:max_results]


