"""
Handler para SharePoint
"""

from __future__ import annotations

from typing import List
from langchain_core.documents import Document
import requests

from .base_handler import BaseIntegrationHandler


class SharePointHandler(BaseIntegrationHandler):
    """Handler para SharePoint."""
    
    def search(self, query: str, access_token: str, max_results: int = 10) -> List[Document]:
        """Busca en SharePoint (sites, files, lists)."""
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json"
        }
        
        documents = []
        
        try:
            # Buscar sites
            search_url = "https://graph.microsoft.com/v1.0/sites"
            params = {"$search": query, "$top": max_results}
            response = requests.get(search_url, headers=headers, params=params, timeout=10)
            
            if response.status_code == 200:
                sites = response.json().get("value", [])
                for site in sites:
                    site_id = site.get("id", "")
                    # Buscar archivos en el site
                    files_url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drive/root/search(q='{query}')"
                    files_response = requests.get(files_url, headers=headers, timeout=10)
                    
                    if files_response.status_code == 200:
                        files = files_response.json().get("value", [])
                        for file in files[:max_results // 2]:
                            content = f"File: {file.get('name', '')}\nPath: {file.get('webUrl', '')}\nModified: {file.get('lastModifiedDateTime', '')}"
                            documents.append(Document(
                                page_content=content,
                                metadata={
                                    "source": "sharepoint - File",
                                    "file_id": file.get("id", ""),
                                    "file_name": file.get("name", ""),
                                    "site": site.get("displayName", ""),
                                    "integration": "sharepoint"
                                }
                            ))
        except Exception as e:
            print(f"Error buscando en SharePoint: {e}")
        
        return documents[:max_results]


