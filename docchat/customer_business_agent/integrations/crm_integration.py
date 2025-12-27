"""
CRM Integration - Integración Profunda con CRMs Reales
Soporta HubSpot, Salesforce, y APIs genéricas
"""

from __future__ import annotations

import requests
import json
from typing import Dict, Any, Optional, List
from enum import Enum
from dataclasses import dataclass


class CRMType(Enum):
    """Tipos de CRM soportados."""
    HUBSPOT = "hubspot"
    SALESFORCE = "salesforce"
    PIPEDRIVE = "pipedrive"
    GENERIC = "generic"  # Para APIs genéricas


@dataclass
class CRMContact:
    """Modelo de contacto en CRM."""
    email: str
    name: Optional[str] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    custom_fields: Dict[str, Any] = None


@dataclass
class CRMDeal:
    """Modelo de deal/oportunidad en CRM."""
    name: str
    amount: Optional[float] = None
    stage: Optional[str] = None
    contact_email: Optional[str] = None
    custom_fields: Dict[str, Any] = None


class CRMIntegration:
    """
    Integración profunda con CRMs reales.
    
    Permite:
    - Crear/actualizar contactos
    - Crear deals/oportunidades
    - Sincronizar datos de clientes
    - Obtener historial de interacciones
    """
    
    def __init__(
        self,
        crm_type: CRMType,
        api_key: Optional[str] = None,
        api_url: Optional[str] = None,
        access_token: Optional[str] = None,
        **kwargs
    ):
        """
        Inicializa integración con CRM.
        
        Args:
            crm_type: Tipo de CRM
            api_key: API key (para HubSpot, Pipedrive)
            api_url: URL base de API (para Salesforce, genérico)
            access_token: Access token (para Salesforce OAuth)
        """
        self.crm_type = crm_type
        self.api_key = api_key
        self.api_url = api_url
        self.access_token = access_token
        self.extra_config = kwargs
        
        # Configurar headers según tipo de CRM
        self.headers = self._get_headers()
    
    def _get_headers(self) -> Dict[str, str]:
        """Obtiene headers apropiados según tipo de CRM."""
        headers = {"Content-Type": "application/json"}
        
        if self.crm_type == CRMType.HUBSPOT:
            headers["Authorization"] = f"Bearer {self.api_key}"
        elif self.crm_type == CRMType.SALESFORCE:
            headers["Authorization"] = f"Bearer {self.access_token}"
        elif self.crm_type == CRMType.PIPEDRIVE:
            headers["api-token"] = self.api_key
        elif self.crm_type == CRMType.GENERIC:
            # Headers personalizados desde extra_config
            if "headers" in self.extra_config:
                headers.update(self.extra_config["headers"])
        
        return headers
    
    def _get_base_url(self) -> str:
        """Obtiene URL base según tipo de CRM."""
        if self.crm_type == CRMType.HUBSPOT:
            return "https://api.hubapi.com"
        elif self.crm_type == CRMType.SALESFORCE:
            return self.api_url or "https://your-instance.salesforce.com"
        elif self.crm_type == CRMType.PIPEDRIVE:
            return f"https://{self.extra_config.get('company_domain', 'api')}.pipedrive.com/api/v1"
        elif self.crm_type == CRMType.GENERIC:
            return self.api_url or ""
        
        return ""
    
    def create_or_update_contact(self, contact: CRMContact) -> Dict[str, Any]:
        """
        Crea o actualiza un contacto en el CRM.
        
        Args:
            contact: Datos del contacto
            
        Returns:
            Dict con información del contacto creado/actualizado
        """
        # Validación de input
        if not contact or not contact.email:
            raise ValueError("Contacto debe tener email")
        
        try:
            base_url = self._get_base_url()
            
            if self.crm_type == CRMType.HUBSPOT:
                return self._hubspot_create_contact(base_url, contact)
            elif self.crm_type == CRMType.SALESFORCE:
                return self._salesforce_create_contact(base_url, contact)
            elif self.crm_type == CRMType.PIPEDRIVE:
                return self._pipedrive_create_contact(base_url, contact)
            elif self.crm_type == CRMType.GENERIC:
                return self._generic_create_contact(base_url, contact)
            
            raise ValueError(f"CRM type {self.crm_type} not supported")
        except Exception as e:
            print(f"⚠️ Error creando/actualizando contacto en CRM: {e}")
            # Retornar dict vacío en lugar de lanzar excepción (para no romper el flujo)
            return {"error": str(e), "contact_id": None}
    
    def _hubspot_create_contact(self, base_url: str, contact: CRMContact) -> Dict[str, Any]:
        """Crea/actualiza contacto en HubSpot."""
        url = f"{base_url}/crm/v3/objects/contacts"
        
        properties = {
            "email": contact.email,
        }
        if contact.name:
            properties["firstname"] = contact.name.split()[0] if contact.name else ""
            if len(contact.name.split()) > 1:
                properties["lastname"] = " ".join(contact.name.split()[1:])
        if contact.phone:
            properties["phone"] = contact.phone
        if contact.company:
            properties["company"] = contact.company
        if contact.custom_fields:
            properties.update(contact.custom_fields)
        
        data = {"properties": properties}
        
        # Intentar actualizar primero (por email)
        search_url = f"{base_url}/crm/v3/objects/contacts/search"
        search_data = {
            "filterGroups": [{
                "filters": [{
                    "propertyName": "email",
                    "operator": "EQ",
                    "value": contact.email
                }]
            }]
        }
        
        try:
            response = requests.post(search_url, headers=self.headers, json=search_data, timeout=10)
            if response.status_code == 200:
                results = response.json().get("results", [])
                if results:
                    # Actualizar contacto existente
                    contact_id = results[0]["id"]
                    update_url = f"{url}/{contact_id}"
                    response = requests.patch(update_url, headers=self.headers, json=data, timeout=10)
                    response.raise_for_status()
                    return {"contact_id": contact_id, "action": "updated", **response.json()}
        except:
            pass
        
        # Crear nuevo contacto
        response = requests.post(url, headers=self.headers, json=data, timeout=10)
        response.raise_for_status()
        result = response.json()
        return {"contact_id": result.get("id"), "action": "created", **result}
    
    def _salesforce_create_contact(self, base_url: str, contact: CRMContact) -> Dict[str, Any]:
        """Crea/actualiza contacto en Salesforce."""
        url = f"{base_url}/services/data/v57.0/sobjects/Contact"
        
        data = {
            "Email": contact.email,
        }
        if contact.name:
            name_parts = contact.name.split()
            data["FirstName"] = name_parts[0] if name_parts else ""
            if len(name_parts) > 1:
                data["LastName"] = " ".join(name_parts[1:])
            else:
                data["LastName"] = contact.name
        if contact.phone:
            data["Phone"] = contact.phone
        if contact.company:
            data["AccountId"] = contact.company  # Asumimos que es AccountId
        if contact.custom_fields:
            data.update(contact.custom_fields)
        
        # Buscar contacto existente
        query_url = f"{base_url}/services/data/v57.0/query"
        query = f"SELECT Id FROM Contact WHERE Email = '{contact.email}' LIMIT 1"
        
        try:
            response = requests.get(query_url, headers=self.headers, params={"q": query}, timeout=10)
            if response.status_code == 200:
                results = response.json().get("records", [])
                if results:
                    # Actualizar
                    contact_id = results[0]["Id"]
                    update_url = f"{url}/{contact_id}"
                    response = requests.patch(update_url, headers=self.headers, json=data, timeout=10)
                    response.raise_for_status()
                    return {"contact_id": contact_id, "action": "updated"}
        except:
            pass
        
        # Crear nuevo
        response = requests.post(url, headers=self.headers, json=data, timeout=10)
        response.raise_for_status()
        result = response.json()
        return {"contact_id": result.get("id"), "action": "created", **result}
    
    def _pipedrive_create_contact(self, base_url: str, contact: CRMContact) -> Dict[str, Any]:
        """Crea/actualiza contacto en Pipedrive."""
        url = f"{base_url}/persons"
        
        data = {
            "email": [{"value": contact.email, "primary": True}],
        }
        if contact.name:
            data["name"] = contact.name
        if contact.phone:
            data["phone"] = [{"value": contact.phone, "primary": True}]
        if contact.company:
            data["org_name"] = contact.company
        if contact.custom_fields:
            data.update(contact.custom_fields)
        
        # Buscar existente
        search_url = f"{base_url}/persons/search"
        search_params = {"term": contact.email, "fields": "email"}
        
        try:
            response = requests.get(search_url, headers=self.headers, params=search_params, timeout=10)
            if response.status_code == 200:
                results = response.json().get("data", {}).get("items", [])
                if results:
                    person_id = results[0]["item"]["id"]
                    update_url = f"{url}/{person_id}"
                    response = requests.put(update_url, headers=self.headers, json=data, timeout=10)
                    response.raise_for_status()
                    return {"contact_id": person_id, "action": "updated", **response.json()}
        except:
            pass
        
        # Crear nuevo
        response = requests.post(url, headers=self.headers, json=data, timeout=10)
        response.raise_for_status()
        result = response.json()
        return {"contact_id": result.get("data", {}).get("id"), "action": "created", **result}
    
    def _generic_create_contact(self, base_url: str, contact: CRMContact) -> Dict[str, Any]:
        """Crea/actualiza contacto en API genérica."""
        endpoint = self.extra_config.get("contact_endpoint", "/contacts")
        url = f"{base_url}{endpoint}"
        
        data = {
            "email": contact.email,
            "name": contact.name,
            "phone": contact.phone,
            "company": contact.company,
        }
        if contact.custom_fields:
            data.update(contact.custom_fields)
        
        # Método HTTP personalizable
        method = self.extra_config.get("contact_method", "POST").upper()
        
        if method == "PUT":
            # Buscar primero
            search_endpoint = self.extra_config.get("contact_search_endpoint", "/contacts/search")
            search_url = f"{base_url}{search_endpoint}"
            try:
                search_response = requests.post(
                    search_url,
                    headers=self.headers,
                    json={"email": contact.email},
                    timeout=10
                )
                if search_response.status_code == 200:
                    existing = search_response.json()
                    if existing.get("id"):
                        update_url = f"{url}/{existing['id']}"
                        response = requests.put(update_url, headers=self.headers, json=data, timeout=10)
                        response.raise_for_status()
                        return {"contact_id": existing["id"], "action": "updated", **response.json()}
            except:
                pass
        
        response = requests.post(url, headers=self.headers, json=data, timeout=10)
        response.raise_for_status()
        return {"contact_id": response.json().get("id"), "action": "created", **response.json()}
    
    def create_deal(self, deal: CRMDeal) -> Dict[str, Any]:
        """
        Crea un deal/oportunidad en el CRM.
        
        Args:
            deal: Datos del deal
            
        Returns:
            Dict con información del deal creado
        """
        base_url = self._get_base_url()
        
        if self.crm_type == CRMType.HUBSPOT:
            return self._hubspot_create_deal(base_url, deal)
        elif self.crm_type == CRMType.SALESFORCE:
            return self._salesforce_create_deal(base_url, deal)
        elif self.crm_type == CRMType.PIPEDRIVE:
            return self._pipedrive_create_deal(base_url, deal)
        elif self.crm_type == CRMType.GENERIC:
            return self._generic_create_deal(base_url, deal)
        
        raise ValueError(f"CRM type {self.crm_type} not supported")
    
    def _hubspot_create_deal(self, base_url: str, deal: CRMDeal) -> Dict[str, Any]:
        """Crea deal en HubSpot."""
        url = f"{base_url}/crm/v3/objects/deals"
        
        properties = {
            "dealname": deal.name,
        }
        if deal.amount:
            properties["amount"] = str(deal.amount)
        if deal.stage:
            properties["dealstage"] = deal.stage
        if deal.contact_email:
            # Buscar contacto y asociarlo
            search_url = f"{base_url}/crm/v3/objects/contacts/search"
            search_data = {
                "filterGroups": [{
                    "filters": [{
                        "propertyName": "email",
                        "operator": "EQ",
                        "value": deal.contact_email
                    }]
                }]
            }
            try:
                search_response = requests.post(search_url, headers=self.headers, json=search_data, timeout=10)
                if search_response.status_code == 200:
                    results = search_response.json().get("results", [])
                    if results:
                        contact_id = results[0]["id"]
                        properties["associations"] = [{
                            "to": {"id": contact_id},
                            "types": [{"associationCategory": "HUBSPOT_DEFINED", "associationTypeId": 3}]
                        }]
            except:
                pass
        
        if deal.custom_fields:
            properties.update(deal.custom_fields)
        
        data = {"properties": properties}
        response = requests.post(url, headers=self.headers, json=data, timeout=10)
        response.raise_for_status()
        result = response.json()
        return {"deal_id": result.get("id"), **result}
    
    def _salesforce_create_deal(self, base_url: str, deal: CRMDeal) -> Dict[str, Any]:
        """Crea oportunidad en Salesforce."""
        url = f"{base_url}/services/data/v57.0/sobjects/Opportunity"
        
        data = {
            "Name": deal.name,
        }
        if deal.amount:
            data["Amount"] = deal.amount
        if deal.stage:
            data["StageName"] = deal.stage
        if deal.custom_fields:
            data.update(deal.custom_fields)
        
        response = requests.post(url, headers=self.headers, json=data, timeout=10)
        response.raise_for_status()
        result = response.json()
        return {"deal_id": result.get("id"), **result}
    
    def _pipedrive_create_deal(self, base_url: str, deal: CRMDeal) -> Dict[str, Any]:
        """Crea deal en Pipedrive."""
        url = f"{base_url}/deals"
        
        data = {
            "title": deal.name,
        }
        if deal.amount:
            data["value"] = deal.amount
        if deal.stage:
            data["stage_id"] = deal.stage
        if deal.custom_fields:
            data.update(deal.custom_fields)
        
        response = requests.post(url, headers=self.headers, json=data, timeout=10)
        response.raise_for_status()
        result = response.json()
        return {"deal_id": result.get("data", {}).get("id"), **result}
    
    def _generic_create_deal(self, base_url: str, deal: CRMDeal) -> Dict[str, Any]:
        """Crea deal en API genérica."""
        endpoint = self.extra_config.get("deal_endpoint", "/deals")
        url = f"{base_url}{endpoint}"
        
        data = {
            "name": deal.name,
            "amount": deal.amount,
            "stage": deal.stage,
        }
        if deal.custom_fields:
            data.update(deal.custom_fields)
        
        response = requests.post(url, headers=self.headers, json=data, timeout=10)
        response.raise_for_status()
        return {"deal_id": response.json().get("id"), **response.json()}
    
    def get_contact_history(self, email: str) -> List[Dict[str, Any]]:
        """
        Obtiene historial de interacciones de un contacto.
        
        Args:
            email: Email del contacto
            
        Returns:
            Lista de interacciones
        """
        # Implementación básica - cada CRM tiene su propia API
        # Por ahora retornamos lista vacía (se puede extender)
        return []

