"""
Handler para Workday
"""

from __future__ import annotations

from typing import List
from langchain_core.documents import Document
import requests
import base64

from .base_handler import BaseIntegrationHandler


class WorkdayHandler(BaseIntegrationHandler):
    """Handler para Workday HCM."""
    
    def search(self, query: str, access_token: str, max_results: int = 10) -> List[Document]:
        """
        Busca en Workday.
        
        access_token debe ser: "tenant|username:password"
        """
        # Parsear token
        if "|" in access_token:
            tenant, auth = access_token.split("|", 1)
        else:
            tenant = getattr(self.config, 'workday_tenant', '')
            auth = access_token
        
        if not tenant:
            print("⚠️ Necesitás configurar WORKDAY_TENANT o incluirla en el token como 'tenant|user:pass'")
            return []
        
        # Basic Auth
        username, password = auth.split(":", 1)
        credentials = f"{username}:{password}"
        encoded = base64.b64encode(credentials.encode()).decode()
        headers = {
            "Authorization": f"Basic {encoded}",
            "Content-Type": "application/xml"
        }
        
        base_url = f"https://wd2-impl-services1.workday.com/ccx/service/{tenant}"
        documents = []
        
        try:
            # Buscar workers (empleados)
            search_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<env:Envelope xmlns:env="http://schemas.xmlsoap.org/soap/envelope/" xmlns:wd="urn:com.workday/bsvc">
    <env:Body>
        <wd:Get_Workers_Request>
            <wd:Request_References>
                <wd:Worker_Reference>
                    <wd:ID wd:type="Employee_ID">{query}</wd:ID>
                </wd:Worker_Reference>
            </wd:Request_References>
        </wd:Get_Workers_Request>
    </env:Body>
</env:Envelope>"""
            
            response = requests.post(
                f"{base_url}/Human_Resources/v{getattr(self.config, 'workday_api_version', '40')}/Workday_Account",
                headers=headers,
                data=search_xml,
                timeout=10
            )
            
            if response.status_code == 200:
                # Parsear XML response (simplificado)
                content = response.text[:5000]  # Limitar tamaño
                documents.append(Document(
                    page_content=content,
                    metadata={
                        "source": "workday - Worker",
                        "integration": "workday"
                    }
                ))
        except Exception as e:
            print(f"Error buscando en Workday: {e}")
        
        return documents


