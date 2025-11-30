"""
Handler para HubSpot
"""

from __future__ import annotations

from typing import List
from langchain_core.documents import Document
import requests

from .base_handler import BaseIntegrationHandler


class HubSpotHandler(BaseIntegrationHandler):
    """Handler para HubSpot CRM."""
    
    def search(self, query: str, access_token: str, max_results: int = 10) -> List[Document]:
        """Busca en HubSpot (contacts, deals, companies, tickets)."""
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        documents = []
        
        # Buscar en contacts
        try:
            contacts_url = "https://api.hubapi.com/crm/v3/objects/contacts/search"
            payload = {
                "query": query,
                "limit": max_results // 4,
                "properties": ["firstname", "lastname", "email", "company", "notes"]
            }
            response = requests.post(contacts_url, headers=headers, json=payload, timeout=10)
            if response.status_code == 200:
                contacts = response.json().get("results", [])
                for contact in contacts:
                    props = contact.get("properties", {})
                    content = f"Contact: {props.get('firstname', '')} {props.get('lastname', '')}\nEmail: {props.get('email', '')}\nCompany: {props.get('company', '')}\nNotes: {props.get('notes', '')}"
                    documents.append(Document(
                        page_content=content,
                        metadata={
                            "source": "hubspot - Contact",
                            "contact_id": contact.get("id", ""),
                            "email": props.get("email", ""),
                            "integration": "hubspot"
                        }
                    ))
        except Exception as e:
            print(f"Error buscando contacts en HubSpot: {e}")
        
        # Buscar en deals
        try:
            deals_url = "https://api.hubapi.com/crm/v3/objects/deals/search"
            payload = {
                "query": query,
                "limit": max_results // 4,
                "properties": ["dealname", "amount", "dealstage", "closedate"]
            }
            response = requests.post(deals_url, headers=headers, json=payload, timeout=10)
            if response.status_code == 200:
                deals = response.json().get("results", [])
                for deal in deals:
                    props = deal.get("properties", {})
                    content = f"Deal: {props.get('dealname', '')}\nAmount: {props.get('amount', '')}\nStage: {props.get('dealstage', '')}\nClose Date: {props.get('closedate', '')}"
                    documents.append(Document(
                        page_content=content,
                        metadata={
                            "source": "hubspot - Deal",
                            "deal_id": deal.get("id", ""),
                            "deal_name": props.get("dealname", ""),
                            "integration": "hubspot"
                        }
                    ))
        except Exception as e:
            print(f"Error buscando deals en HubSpot: {e}")
        
        return documents[:max_results]


