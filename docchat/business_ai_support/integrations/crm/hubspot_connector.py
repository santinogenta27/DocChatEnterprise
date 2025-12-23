"""
HubSpot CRM Connector

Deep integration with HubSpot CRM using REST API.
Supports: Contacts, Deals, Tickets, Companies, Notes, Tasks
"""

from __future__ import annotations

import requests
from typing import Dict, Any, Optional, List
from datetime import datetime

from .base import CRMConnector, CRMConfig, CRMRecord, CRMProvider, CRMRecordType


class HubSpotConnector(CRMConnector):
    """
    HubSpot CRM Connector using REST API.
    
    Requires HubSpot API key or OAuth access token.
    """

    BASE_URL = "https://api.hubapi.com"

    def __init__(self, config: CRMConfig):
        """Initialize HubSpot connector."""
        super().__init__(config)
        self.api_key = config.api_key or config.access_token
        self.base_url = config.base_url or self.BASE_URL

    def _validate_config(self) -> None:
        """Validate HubSpot configuration."""
        if not (self.config.api_key or self.config.access_token):
            raise ValueError("HubSpot config must have api_key or access_token")

    def _get_headers(self) -> Dict[str, str]:
        """Get headers for API requests."""
        if self.config.access_token:
            return {"Authorization": f"Bearer {self.config.access_token}"}
        return {}

    def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Make authenticated request to HubSpot API."""
        url = f"{self.base_url}/{endpoint}"
        headers = self._get_headers()
        headers["Content-Type"] = "application/json"
        
        # Add API key to params if using API key auth
        if self.api_key and not self.config.access_token:
            if params is None:
                params = {}
            params["hapikey"] = self.api_key
        
        if method == "GET":
            response = requests.get(url, headers=headers, params=params)
        elif method == "POST":
            response = requests.post(url, headers=headers, json=data, params=params)
        elif method == "PATCH":
            response = requests.patch(url, headers=headers, json=data, params=params)
        elif method == "DELETE":
            response = requests.delete(url, headers=headers, params=params)
        else:
            raise ValueError(f"Unsupported method: {method}")
        
        if response.status_code >= 400:
            error_msg = response.text
            try:
                error_data = response.json()
                error_msg = error_data.get("message", error_msg)
            except:
                pass
            raise ValueError(f"HubSpot API error: {response.status_code} - {error_msg}")
        
        return response.json() if response.text else {}

    def test_connection(self) -> bool:
        """Test connection to HubSpot."""
        try:
            # Use v3 API for testing
            result = self._make_request("GET", "crm/v3/objects/contacts", params={"limit": 1})
            return True
        except Exception as e:
            print(f"❌ Error probando conexión HubSpot: {e}")
            return False

    # ========== READ OPERATIONS ==========

    def get_contact(self, contact_id: str) -> Optional[CRMRecord]:
        """Get a contact by ID."""
        if not self._check_permission("read_contact"):
            raise PermissionError("No permission to read contacts")
        
        try:
            data = self._make_request("GET", f"contacts/v1/contact/vid/{contact_id}/profile")
            return CRMRecord(
                record_type=CRMRecordType.CONTACT,
                record_id=str(data["vid"]),
                provider=self.provider,
                data=data["properties"],
                created_at=self._parse_timestamp(data["properties"].get("createdate")),
                updated_at=self._parse_timestamp(data["properties"].get("lastmodifieddate"))
            )
        except Exception as e:
            print(f"Error obteniendo contacto HubSpot: {e}")
            return None

    def search_contact(self, email: str, phone: Optional[str] = None) -> Optional[CRMRecord]:
        """Search for a contact by email or phone."""
        if not self._check_permission("read_contact"):
            raise PermissionError("No permission to read contacts")
        
        try:
            # Search by email
            data = self._make_request("GET", f"contacts/v1/contact/email/{email}/profile")
            if data and "vid" in data:
                return CRMRecord(
                    record_type=CRMRecordType.CONTACT,
                    record_id=str(data["vid"]),
                    provider=self.provider,
                    data=data.get("properties", {})
                )
            
            # If email not found and phone provided, search by phone
            if phone:
                # HubSpot search by phone requires using search API
                search_data = {
                    "filterGroups": [{
                        "filters": [{
                            "propertyName": "phone",
                            "operator": "EQ",
                            "value": phone
                        }]
                    }],
                    "properties": ["email", "firstname", "lastname", "phone"]
                }
                result = self._make_request("POST", "crm/v3/objects/contacts/search", data=search_data)
                if result.get("results") and len(result["results"]) > 0:
                    contact = result["results"][0]
                    return CRMRecord(
                        record_type=CRMRecordType.CONTACT,
                        record_id=contact["id"],
                        provider=self.provider,
                        data=contact.get("properties", {})
                    )
            
            return None
        except Exception as e:
            print(f"Error buscando contacto HubSpot: {e}")
            return None

    def get_case(self, case_id: str) -> Optional[CRMRecord]:
        """Get a ticket by ID (HubSpot uses tickets, not cases)."""
        if not self._check_permission("read_ticket"):
            raise PermissionError("No permission to read tickets")
        
        try:
            data = self._make_request("GET", f"crm/v3/objects/tickets/{case_id}")
            return CRMRecord(
                record_type=CRMRecordType.TICKET,
                record_id=data["id"],
                provider=self.provider,
                data=data.get("properties", {}),
                created_at=self._parse_timestamp(data.get("createdAt")),
                updated_at=self._parse_timestamp(data.get("updatedAt"))
            )
        except Exception as e:
            print(f"Error obteniendo ticket HubSpot: {e}")
            return None

    def get_customer_history(self, contact_id: str) -> List[CRMRecord]:
        """Get full interaction history for a customer."""
        if not self._check_permission("read_history"):
            raise PermissionError("No permission to read history")
        
        history = []
        
        # Get tickets associated with contact
        try:
            params = {"associations": "tickets", "includeAssociations": "true"}
            data = self._make_request("GET", f"contacts/v1/contact/vid/{contact_id}/profile", params=params)
            if "associated-ticket-ids" in data:
                for ticket_id in data["associated-ticket-ids"]:
                    ticket = self.get_case(ticket_id)
                    if ticket:
                        history.append(ticket)
        except Exception as e:
            print(f"Error obteniendo historial de tickets: {e}")
        
        # Get deals associated with contact
        try:
            params = {"associations": "deals", "includeAssociations": "true"}
            data = self._make_request("GET", f"contacts/v1/contact/vid/{contact_id}/profile", params=params)
            if "associated-deal-ids" in data:
                for deal_id in data["associated-deal-ids"]:
                    deal_data = self._make_request("GET", f"deals/v1/deal/{deal_id}")
                    history.append(CRMRecord(
                        record_type=CRMRecordType.DEAL,
                        record_id=str(deal_data["dealId"]),
                        provider=self.provider,
                        data=deal_data.get("properties", {})
                    ))
        except Exception as e:
            print(f"Error obteniendo historial de deals: {e}")
        
        return history

    def search_account(self, name: str) -> Optional[CRMRecord]:
        """Search for a company by name."""
        if not self._check_permission("read_account"):
            raise PermissionError("No permission to read accounts")
        
        try:
            search_data = {
                "filterGroups": [{
                    "filters": [{
                        "propertyName": "name",
                        "operator": "CONTAINS_TOKEN",
                        "value": name
                    }]
                }],
                "properties": ["name", "domain"]
            }
            result = self._make_request("POST", "crm/v3/objects/companies/search", data=search_data)
            if result.get("results") and len(result["results"]) > 0:
                company = result["results"][0]
                return CRMRecord(
                    record_type=CRMRecordType.ACCOUNT,
                    record_id=company["id"],
                    provider=self.provider,
                    data=company.get("properties", {})
                )
            return None
        except Exception as e:
            print(f"Error buscando compañía HubSpot: {e}")
            return None

    # ========== WRITE OPERATIONS ==========

    def create_contact(self, contact_data: Dict[str, Any]) -> CRMRecord:
        """Create a new contact."""
        if not self._check_permission("create_contact"):
            raise PermissionError("No permission to create contacts")
        
        try:
            # Convert to HubSpot format (properties object)
            properties = {}
            for key, value in contact_data.items():
                if key not in ["id", "vid", "createdAt", "updatedAt"]:
                    properties[key] = str(value)
            
            payload = {"properties": properties}
            result = self._make_request("POST", "contacts/v1/contact", data=payload)
            contact_id = str(result["vid"])
            return self.get_contact(contact_id)
        except Exception as e:
            raise ValueError(f"Error creando contacto HubSpot: {e}")

    def update_contact(self, contact_id: str, updates: Dict[str, Any]) -> CRMRecord:
        """Update an existing contact."""
        if not self._check_permission("update_contact"):
            raise PermissionError("No permission to update contacts")
        
        try:
            properties = {}
            for key, value in updates.items():
                if key not in ["id", "vid"]:
                    properties[key] = str(value)
            
            payload = {"properties": properties}
            self._make_request("POST", f"contacts/v1/contact/vid/{contact_id}/profile", data=payload)
            return self.get_contact(contact_id)
        except Exception as e:
            raise ValueError(f"Error actualizando contacto HubSpot: {e}")

    def create_case(self, case_data: Dict[str, Any]) -> CRMRecord:
        """Create a new ticket (HubSpot uses tickets, not cases)."""
        if not self._check_permission("create_ticket"):
            raise PermissionError("No permission to create tickets")
        
        try:
            # Convert to HubSpot format
            properties = {}
            for key, value in case_data.items():
                if key not in ["id"]:
                    properties[key] = str(value)
            
            # Ensure required fields
            if "subject" not in properties:
                properties["subject"] = "Support Ticket"
            if "content" not in properties and "description" in case_data:
                properties["content"] = case_data["description"]
            
            payload = {"properties": properties}
            result = self._make_request("POST", "crm/v3/objects/tickets", data=payload)
            ticket_id = result["id"]
            return self.get_case(ticket_id)
        except Exception as e:
            raise ValueError(f"Error creando ticket HubSpot: {e}")

    def update_case(self, case_id: str, updates: Dict[str, Any]) -> CRMRecord:
        """Update an existing ticket."""
        if not self._check_permission("update_ticket"):
            raise PermissionError("No permission to update tickets")
        
        try:
            properties = {}
            for key, value in updates.items():
                if key not in ["id"]:
                    properties[key] = str(value)
            
            payload = {"properties": properties}
            self._make_request("PATCH", f"crm/v3/objects/tickets/{case_id}", data=payload)
            return self.get_case(case_id)
        except Exception as e:
            raise ValueError(f"Error actualizando ticket HubSpot: {e}")

    def close_case(self, case_id: str, resolution: Optional[str] = None) -> CRMRecord:
        """Close a ticket with optional resolution."""
        updates = {"hs_pipeline_stage": "closedwon"}  # HubSpot uses pipeline stages
        if resolution:
            updates["content"] = resolution
        return self.update_case(case_id, updates)

    def add_note(self, record_id: str, note_text: str, record_type: CRMRecordType = CRMRecordType.CONTACT) -> CRMRecord:
        """Add a note to a record."""
        if not self._check_permission("create_note"):
            raise PermissionError("No permission to create notes")
        
        try:
            # Create an engagement (note) associated with the record
            engagement_data = {
                "engagement": {
                    "type": "NOTE"
                },
                "associations": {
                    "contactIds": [record_id] if record_type == CRMRecordType.CONTACT else [],
                    "companyIds": [record_id] if record_type == CRMRecordType.ACCOUNT else [],
                    "dealIds": [record_id] if record_type == CRMRecordType.DEAL else []
                },
                "metadata": {
                    "body": note_text
                }
            }
            result = self._make_request("POST", "engagements/v1/engagements", data=engagement_data)
            return CRMRecord(
                record_type=CRMRecordType.NOTE,
                record_id=str(result["engagement"]["id"]),
                provider=self.provider,
                data={"body": note_text}
            )
        except Exception as e:
            raise ValueError(f"Error agregando nota HubSpot: {e}")

    def create_task(self, task_data: Dict[str, Any]) -> CRMRecord:
        """Create a task/follow-up."""
        if not self._check_permission("create_task"):
            raise PermissionError("No permission to create tasks")
        
        try:
            # HubSpot tasks are created as engagements
            engagement_data = {
                "engagement": {
                    "type": "TASK",
                    "active": True
                },
                "associations": {
                    "contactIds": task_data.get("contactIds", []),
                    "companyIds": task_data.get("companyIds", []),
                    "dealIds": task_data.get("dealIds", [])
                },
                "metadata": {
                    "body": task_data.get("note", ""),
                    "subject": task_data.get("subject", "Follow-up"),
                    "status": task_data.get("status", "NOT_STARTED")
                }
            }
            result = self._make_request("POST", "engagements/v1/engagements", data=engagement_data)
            return CRMRecord(
                record_type=CRMRecordType.TASK,
                record_id=str(result["engagement"]["id"]),
                provider=self.provider,
                data=task_data
            )
        except Exception as e:
            raise ValueError(f"Error creando tarea HubSpot: {e}")

    # ========== UTILITY METHODS ==========

    def _parse_timestamp(self, timestamp_str: Optional[str]) -> Optional[datetime]:
        """Parse HubSpot timestamp (milliseconds since epoch)."""
        if not timestamp_str:
            return None
        try:
            # HubSpot uses milliseconds
            timestamp_ms = int(timestamp_str)
            return datetime.fromtimestamp(timestamp_ms / 1000)
        except:
            return None

