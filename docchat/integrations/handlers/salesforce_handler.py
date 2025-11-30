"""
Handler para Salesforce
"""

from __future__ import annotations

from typing import List
from langchain_core.documents import Document
import requests

from .base_handler import BaseIntegrationHandler


class SalesforceHandler(BaseIntegrationHandler):
    """Handler para Salesforce."""
    
    def search(self, query: str, access_token: str, max_results: int = 10) -> List[Document]:
        """
        Busca en Salesforce.
        
        access_token debe ser: "instance_url|access_token"
        """
        # Parsear token
        if "|" in access_token:
            instance_url, token = access_token.split("|", 1)
        else:
            instance_url = getattr(self.config, 'salesforce_instance_url', '')
            token = access_token
        
        if not instance_url:
            print("⚠️ Necesitás configurar SALESFORCE_INSTANCE_URL o incluirla en el token como 'url|token'")
            return []
        
        instance_url = instance_url.rstrip('/')
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        documents = []
        
        try:
            # Buscar usando SOSL (Salesforce Object Search Language)
            search_url = f"{instance_url}/services/data/v58.0/search"
            sosl_query = f"FIND {{{query}}} IN ALL FIELDS RETURNING Account(Id,Name,Description), Contact(Id,Name,Email), Lead(Id,Name,Company), Case(Id,Subject,Description), Opportunity(Id,Name,Description) LIMIT {max_results}"
            
            params = {"q": sosl_query}
            response = requests.get(search_url, headers=headers, params=params, timeout=10)
            
            if response.status_code == 200:
                results = response.json()
                for record_type, records in results.get("searchRecords", {}).items():
                    for record in records:
                        name = record.get("Name", "")
                        description = record.get("Description", "") or record.get("Subject", "")
                        content = f"{name}\n\n{description}".strip()
                        
                        if content:
                            documents.append(Document(
                                page_content=content[:5000],
                                metadata={
                                    "source": f"salesforce - {record_type}",
                                    "record_id": record.get("Id", ""),
                                    "record_type": record_type,
                                    "name": name,
                                    "integration": "salesforce"
                                }
                            ))
        except Exception as e:
            print(f"Error buscando en Salesforce: {e}")
        
        return documents[:max_results]


