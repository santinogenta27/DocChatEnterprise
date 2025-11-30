"""
Handler para ServiceNow
"""

from __future__ import annotations

from typing import List
from langchain_core.documents import Document
import requests
import base64

from .base_handler import BaseIntegrationHandler


class ServiceNowHandler(BaseIntegrationHandler):
    """Handler para ServiceNow."""
    
    def search(self, query: str, access_token: str, max_results: int = 10) -> List[Document]:
        """
        Busca en ServiceNow.
        
        access_token debe ser: "instance_url|username:password"
        """
        # Parsear token
        if "|" in access_token:
            instance_url, auth = access_token.split("|", 1)
        else:
            instance_url = getattr(self.config, 'servicenow_instance_url', '')
            auth = access_token
        
        if not instance_url:
            print("⚠️ Necesitás configurar SERVICENOW_INSTANCE_URL o incluirla en el token como 'url|user:pass'")
            return []
        
        instance_url = instance_url.rstrip('/')
        
        # Crear headers con Basic Auth
        username, password = auth.split(":", 1)
        credentials = f"{username}:{password}"
        encoded = base64.b64encode(credentials.encode()).decode()
        headers = {
            "Authorization": f"Basic {encoded}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        documents = []
        
        try:
            # Buscar en incidents
            search_url = f"{instance_url}/api/now/table/incident"
            params = {
                "sysparm_query": f"short_descriptionLIKE{query}^ORdescriptionLIKE{query}",
                "sysparm_limit": max_results,
                "sysparm_fields": "number,short_description,description,state"
            }
            
            response = requests.get(search_url, headers=headers, params=params, timeout=10)
            
            if response.status_code == 200:
                incidents = response.json().get("result", [])
                for incident in incidents:
                    short_desc = incident.get("short_description", "")
                    description = incident.get("description", "")
                    content = f"{short_desc}\n\n{description}".strip()
                    
                    if content:
                        documents.append(Document(
                            page_content=content[:5000],
                            metadata={
                                "source": f"servicenow - Incident {incident.get('number', '')}",
                                "incident_number": incident.get("number", ""),
                                "state": incident.get("state", ""),
                                "integration": "servicenow"
                            }
                        ))
        except Exception as e:
            print(f"Error buscando en ServiceNow: {e}")
        
        return documents


