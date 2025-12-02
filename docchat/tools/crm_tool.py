"""
CRM Tool para integración con Salesforce, HubSpot, Zoho CRM, Pipedrive, etc.
Permite sincronizar leads, crear contactos, actualizar pipelines, etc.
"""

from __future__ import annotations

import json
import os
import requests
from typing import Any, Dict, List, Optional
from datetime import datetime

from .base_tool import BaseTool, ToolResult


class CRMTool(BaseTool):
    """
    Herramienta de CRM para:
    - Sincronizar leads con CRMs
    - Crear/actualizar contactos
    - Gestionar pipelines
    - Obtener datos de leads existentes
    - Integraciones: Salesforce, HubSpot, Zoho CRM, Pipedrive, Close.com
    """
    
    def __init__(self, config: Any):
        super().__init__(config)
        
        # Credenciales de APIs (desde .env)
        # Salesforce
        self.salesforce_instance_url = os.getenv("SALESFORCE_INSTANCE_URL", "")
        self.salesforce_access_token = os.getenv("SALESFORCE_ACCESS_TOKEN", "")
        self.salesforce_client_id = os.getenv("SALESFORCE_CLIENT_ID", "")
        self.salesforce_client_secret = os.getenv("SALESFORCE_CLIENT_SECRET", "")
        
        # HubSpot
        self.hubspot_api_key = os.getenv("HUBSPOT_API_KEY", "")
        
        # Zoho CRM
        self.zoho_client_id = os.getenv("ZOHO_CLIENT_ID", "")
        self.zoho_client_secret = os.getenv("ZOHO_CLIENT_SECRET", "")
        self.zoho_refresh_token = os.getenv("ZOHO_REFRESH_TOKEN", "")
        self.zoho_api_domain = os.getenv("ZOHO_API_DOMAIN", "https://www.zohoapis.com")
        
        # Pipedrive
        self.pipedrive_api_token = os.getenv("PIPEDRIVE_API_TOKEN", "")
        self.pipedrive_company_domain = os.getenv("PIPEDRIVE_COMPANY_DOMAIN", "")
        
        # Close.com
        self.close_api_key = os.getenv("CLOSE_API_KEY", "")
    
    def get_name(self) -> str:
        return "crm_integration"
    
    def get_description(self) -> str:
        return """CRM integration tool for:
        - Syncing leads with CRMs (Salesforce, HubSpot, Zoho, Pipedrive, Close.com)
        - Creating/updating contacts
        - Managing pipelines and deals
        - Getting lead data from CRMs"""
    
    def get_keywords(self) -> List[str]:
        return [
            "crm", "salesforce", "hubspot", "zoho", "pipedrive", "close.com",
            "sync leads", "create contact", "update pipeline", "crm integration"
        ]
    
    def execute(
        self,
        action: str,
        platform: str,
        lead_data: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> ToolResult:
        """
        Ejecuta acciones de CRM.
        
        Args:
            action: Acción (sync_lead, create_contact, update_deal, get_leads, etc.)
            platform: Plataforma (salesforce, hubspot, zoho, pipedrive, close)
            lead_data: Datos del lead
        """
        try:
            if action == "sync_lead" or action == "create_contact":
                return self._create_contact(platform, lead_data or kwargs)
            elif action == "update_contact":
                return self._update_contact(platform, kwargs.get("contact_id"), lead_data or kwargs)
            elif action == "get_leads":
                return self._get_leads(platform, kwargs.get("limit", 100))
            elif action == "create_deal":
                return self._create_deal(platform, lead_data or kwargs)
            elif action == "update_deal":
                return self._update_deal(platform, kwargs.get("deal_id"), lead_data or kwargs)
            elif action == "search_contacts":
                return self._search_contacts(platform, kwargs.get("query"))
            else:
                return ToolResult(
                    success=False,
                    data=None,
                    message=f"Unknown action: {action}",
                    metadata={}
                )
        
        except Exception as e:
            return ToolResult(
                success=False,
                data=None,
                message=f"Error executing CRM action: {str(e)}",
                metadata={"error": str(e)}
            )
    
    def _create_contact(self, platform: str, lead_data: Dict[str, Any]) -> ToolResult:
        """Crea un contacto en el CRM."""
        if platform == "salesforce":
            return self._create_salesforce_contact(lead_data)
        elif platform == "hubspot":
            return self._create_hubspot_contact(lead_data)
        elif platform == "zoho":
            return self._create_zoho_contact(lead_data)
        elif platform == "pipedrive":
            return self._create_pipedrive_person(lead_data)
        elif platform == "close":
            return self._create_close_lead(lead_data)
        else:
            return ToolResult(
                success=False,
                data=None,
                message=f"Platform {platform} not supported",
                metadata={}
            )
    
    def _create_salesforce_contact(self, lead_data: Dict[str, Any]) -> ToolResult:
        """Crea contacto en Salesforce."""
        if not self.salesforce_instance_url or not self.salesforce_access_token:
            return ToolResult(
                success=False,
                data=None,
                message="Salesforce credentials not configured",
                metadata={"note": "Set SALESFORCE_INSTANCE_URL and SALESFORCE_ACCESS_TOKEN"}
            )
        
        try:
            url = f"{self.salesforce_instance_url}/services/data/v58.0/sobjects/Contact"
            headers = {
                "Authorization": f"Bearer {self.salesforce_access_token}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "FirstName": lead_data.get("name", "").split()[0] if lead_data.get("name") else "",
                "LastName": " ".join(lead_data.get("name", "").split()[1:]) if lead_data.get("name") else "",
                "Email": lead_data.get("email", ""),
                "Phone": lead_data.get("phone", ""),
                "Company": lead_data.get("company", ""),
                "Title": lead_data.get("position", ""),
                "Industry": lead_data.get("industry", ""),
                "LeadSource": lead_data.get("source", "API")
            }
            
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            
            if response.status_code in [200, 201]:
                return ToolResult(
                    success=True,
                    data=response.json(),
                    message=f"Contact created in Salesforce: {response.json().get('id')}",
                    metadata={"platform": "salesforce", "contact_id": response.json().get("id")}
                )
            else:
                return ToolResult(
                    success=False,
                    data=None,
                    message=f"Salesforce API error: {response.status_code} - {response.text}",
                    metadata={"platform": "salesforce", "status_code": response.status_code}
                )
        
        except Exception as e:
            return ToolResult(
                success=False,
                data=None,
                message=f"Salesforce API error: {str(e)}",
                metadata={"platform": "salesforce", "error": str(e)}
            )
    
    def _create_hubspot_contact(self, lead_data: Dict[str, Any]) -> ToolResult:
        """Crea contacto en HubSpot."""
        if not self.hubspot_api_key:
            return ToolResult(
                success=False,
                data=None,
                message="HubSpot API key not configured",
                metadata={"note": "Set HUBSPOT_API_KEY"}
            )
        
        try:
            url = "https://api.hubapi.com/crm/v3/objects/contacts"
            headers = {
                "Authorization": f"Bearer {self.hubspot_api_key}",
                "Content-Type": "application/json"
            }
            
            properties = {
                "email": lead_data.get("email", ""),
                "firstname": lead_data.get("name", "").split()[0] if lead_data.get("name") else "",
                "lastname": " ".join(lead_data.get("name", "").split()[1:]) if lead_data.get("name") else "",
                "phone": lead_data.get("phone", ""),
                "company": lead_data.get("company", ""),
                "jobtitle": lead_data.get("position", ""),
                "industry": lead_data.get("industry", ""),
                "hs_lead_status": "NEW"
            }
            
            payload = {"properties": properties}
            
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            
            if response.status_code in [200, 201]:
                return ToolResult(
                    success=True,
                    data=response.json(),
                    message=f"Contact created in HubSpot: {response.json().get('id')}",
                    metadata={"platform": "hubspot", "contact_id": response.json().get("id")}
                )
            else:
                return ToolResult(
                    success=False,
                    data=None,
                    message=f"HubSpot API error: {response.status_code} - {response.text}",
                    metadata={"platform": "hubspot", "status_code": response.status_code}
                )
        
        except Exception as e:
            return ToolResult(
                success=False,
                data=None,
                message=f"HubSpot API error: {str(e)}",
                metadata={"platform": "hubspot", "error": str(e)}
            )
    
    def _create_zoho_contact(self, lead_data: Dict[str, Any]) -> ToolResult:
        """Crea contacto en Zoho CRM."""
        if not self.zoho_refresh_token:
            return ToolResult(
                success=False,
                data=None,
                message="Zoho credentials not configured",
                metadata={"note": "Set ZOHO_REFRESH_TOKEN"}
            )
        
        try:
            # Obtener access token
            access_token = self._get_zoho_access_token()
            if not access_token:
                return ToolResult(
                    success=False,
                    data=None,
                    message="Failed to get Zoho access token",
                    metadata={}
                )
            
            url = f"{self.zoho_api_domain}/crm/v3/Contacts"
            headers = {
                "Authorization": f"Zoho-oauthtoken {access_token}",
                "Content-Type": "application/json"
            }
            
            data = [{
                "First_Name": lead_data.get("name", "").split()[0] if lead_data.get("name") else "",
                "Last_Name": " ".join(lead_data.get("name", "").split()[1:]) if lead_data.get("name") else "",
                "Email": lead_data.get("email", ""),
                "Phone": lead_data.get("phone", ""),
                "Account_Name": {"name": lead_data.get("company", "")},
                "Title": lead_data.get("position", ""),
                "Industry": lead_data.get("industry", ""),
                "Lead_Source": lead_data.get("source", "API")
            }]
            
            payload = {"data": data}
            
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            
            if response.status_code in [200, 201]:
                result = response.json()
                return ToolResult(
                    success=True,
                    data=result,
                    message=f"Contact created in Zoho CRM",
                    metadata={"platform": "zoho", "contact_id": result.get("data", [{}])[0].get("details", {}).get("id")}
                )
            else:
                return ToolResult(
                    success=False,
                    data=None,
                    message=f"Zoho API error: {response.status_code} - {response.text}",
                    metadata={"platform": "zoho", "status_code": response.status_code}
                )
        
        except Exception as e:
            return ToolResult(
                success=False,
                data=None,
                message=f"Zoho API error: {str(e)}",
                metadata={"platform": "zoho", "error": str(e)}
            )
    
    def _get_zoho_access_token(self) -> Optional[str]:
        """Obtiene access token de Zoho."""
        try:
            url = "https://accounts.zoho.com/oauth/v2/token"
            params = {
                "refresh_token": self.zoho_refresh_token,
                "client_id": self.zoho_client_id,
                "client_secret": self.zoho_client_secret,
                "grant_type": "refresh_token"
            }
            
            response = requests.post(url, params=params, timeout=10)
            if response.status_code == 200:
                return response.json().get("access_token")
        except:
            pass
        return None
    
    def _create_pipedrive_person(self, lead_data: Dict[str, Any]) -> ToolResult:
        """Crea persona en Pipedrive."""
        if not self.pipedrive_api_token:
            return ToolResult(
                success=False,
                data=None,
                message="Pipedrive API token not configured",
                metadata={"note": "Set PIPEDRIVE_API_TOKEN"}
            )
        
        try:
            url = f"https://{self.pipedrive_company_domain or 'api'}.pipedrive.com/api/v1/persons"
            params = {"api_token": self.pipedrive_api_token}
            
            payload = {
                "name": lead_data.get("name", ""),
                "email": [{"value": lead_data.get("email", ""), "primary": True}],
                "phone": [{"value": lead_data.get("phone", ""), "primary": True}] if lead_data.get("phone") else [],
                "org_name": lead_data.get("company", "")
            }
            
            response = requests.post(url, params=params, json=payload, timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                return ToolResult(
                    success=result.get("success", False),
                    data=result.get("data"),
                    message=f"Person created in Pipedrive",
                    metadata={"platform": "pipedrive", "person_id": result.get("data", {}).get("id")}
                )
            else:
                return ToolResult(
                    success=False,
                    data=None,
                    message=f"Pipedrive API error: {response.status_code} - {response.text}",
                    metadata={"platform": "pipedrive", "status_code": response.status_code}
                )
        
        except Exception as e:
            return ToolResult(
                success=False,
                data=None,
                message=f"Pipedrive API error: {str(e)}",
                metadata={"platform": "pipedrive", "error": str(e)}
            )
    
    def _create_close_lead(self, lead_data: Dict[str, Any]) -> ToolResult:
        """Crea lead en Close.com."""
        if not self.close_api_key:
            return ToolResult(
                success=False,
                data=None,
                message="Close.com API key not configured",
                metadata={"note": "Set CLOSE_API_KEY"}
            )
        
        try:
            url = "https://api.close.com/api/v1/lead/"
            headers = {
                "Authorization": f"Bearer {self.close_api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "name": lead_data.get("company", lead_data.get("name", "")),
                "contacts": [{
                    "name": lead_data.get("name", ""),
                    "emails": [{"email": lead_data.get("email", "")}],
                    "phones": [{"phone": lead_data.get("phone", "")}] if lead_data.get("phone") else []
                }]
            }
            
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            
            if response.status_code in [200, 201]:
                return ToolResult(
                    success=True,
                    data=response.json(),
                    message=f"Lead created in Close.com",
                    metadata={"platform": "close", "lead_id": response.json().get("id")}
                )
            else:
                return ToolResult(
                    success=False,
                    data=None,
                    message=f"Close.com API error: {response.status_code} - {response.text}",
                    metadata={"platform": "close", "status_code": response.status_code}
                )
        
        except Exception as e:
            return ToolResult(
                success=False,
                data=None,
                message=f"Close.com API error: {str(e)}",
                metadata={"platform": "close", "error": str(e)}
            )
    
    def _update_contact(self, platform: str, contact_id: str, lead_data: Dict[str, Any]) -> ToolResult:
        """Actualiza un contacto en el CRM."""
        # Implementación similar a _create_contact pero con PUT/PATCH
        return ToolResult(
            success=False,
            data=None,
            message="Update contact not yet implemented",
            metadata={}
        )
    
    def _get_leads(self, platform: str, limit: int = 100) -> ToolResult:
        """Obtiene leads del CRM."""
        return ToolResult(
            success=False,
            data=None,
            message="Get leads not yet implemented",
            metadata={}
        )
    
    def _create_deal(self, platform: str, deal_data: Dict[str, Any]) -> ToolResult:
        """Crea un deal/oportunidad en el CRM."""
        return ToolResult(
            success=False,
            data=None,
            message="Create deal not yet implemented",
            metadata={}
        )
    
    def _update_deal(self, platform: str, deal_id: str, deal_data: Dict[str, Any]) -> ToolResult:
        """Actualiza un deal en el CRM."""
        return ToolResult(
            success=False,
            data=None,
            message="Update deal not yet implemented",
            metadata={}
        )
    
    def _search_contacts(self, platform: str, query: str) -> ToolResult:
        """Busca contactos en el CRM."""
        return ToolResult(
            success=False,
            data=None,
            message="Search contacts not yet implemented",
            metadata={}
        )
