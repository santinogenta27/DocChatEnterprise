"""
Zendesk CRM Connector

Deep integration with Zendesk using REST API.
Supports: Tickets, Users (Contacts), Organizations (Accounts), Comments, Tags
"""

from __future__ import annotations

import requests
from typing import Dict, Any, Optional, List
from datetime import datetime
import base64

from .base import CRMConnector, CRMConfig, CRMRecord, CRMProvider, CRMRecordType


class ZendeskConnector(CRMConnector):
    """
    Zendesk CRM Connector using REST API.
    
    Supports authentication via:
    - API Token (email + token)
    - OAuth (Access Token)
    """

    def __init__(self, config: CRMConfig):
        """Initialize Zendesk connector."""
        super().__init__(config)
        self.subdomain = config.subdomain
        if not self.subdomain:
            raise ValueError("Zendesk config must have subdomain")
        self.base_url = f"https://{self.subdomain}.zendesk.com/api/v2"
        self._setup_auth()

    def _validate_config(self) -> None:
        """Validate Zendesk configuration."""
        if not self.config.subdomain:
            raise ValueError("Zendesk config must have subdomain")
        
        # Must have either API token (email + api_key) OR access_token
        if not (self.config.access_token or (self.config.username and self.config.api_key)):
            raise ValueError("Zendesk config must have access_token OR username/api_key")

    def _setup_auth(self) -> None:
        """Setup authentication for Zendesk API."""
        if self.config.access_token:
            # OAuth token
            self.auth_header = f"Bearer {self.config.access_token}"
        else:
            # API Token authentication (email + token)
            if not (self.config.username and self.config.api_key):
                raise ValueError("Zendesk API token auth requires username and api_key")
            credentials = f"{self.config.username}/token:{self.config.api_key}"
            encoded = base64.b64encode(credentials.encode()).decode()
            self.auth_header = f"Basic {encoded}"

    def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Make authenticated request to Zendesk API."""
        url = f"{self.base_url}/{endpoint}"
        headers = {
            "Authorization": self.auth_header,
            "Content-Type": "application/json"
        }
        
        if method == "GET":
            response = requests.get(url, headers=headers, params=params)
        elif method == "POST":
            response = requests.post(url, headers=headers, json=data, params=params)
        elif method == "PUT":
            response = requests.put(url, headers=headers, json=data, params=params)
        elif method == "DELETE":
            response = requests.delete(url, headers=headers, params=params)
        else:
            raise ValueError(f"Unsupported method: {method}")
        
        if response.status_code >= 400:
            error_msg = response.text
            try:
                error_data = response.json()
                error_msg = error_data.get("error", {}).get("title", error_msg)
            except:
                pass
            raise ValueError(f"Zendesk API error: {response.status_code} - {error_msg}")
        
        return response.json() if response.text else {}

    def test_connection(self) -> bool:
        """Test connection to Zendesk."""
        try:
            result = self._make_request("GET", "users/me.json")
            return True
        except Exception as e:
            print(f"❌ Error probando conexión Zendesk: {e}")
            return False

    # ========== READ OPERATIONS ==========

    def get_contact(self, contact_id: str) -> Optional[CRMRecord]:
        """Get a user (contact) by ID."""
        if not self._check_permission("read_contact"):
            raise PermissionError("No permission to read contacts")
        
        try:
            data = self._make_request("GET", f"users/{contact_id}.json")
            user = data["user"]
            return CRMRecord(
                record_type=CRMRecordType.CONTACT,
                record_id=str(user["id"]),
                provider=self.provider,
                data=user,
                created_at=self._parse_datetime(user.get("created_at")),
                updated_at=self._parse_datetime(user.get("updated_at"))
            )
        except Exception as e:
            print(f"Error obteniendo usuario Zendesk: {e}")
            return None

    def search_contact(self, email: str, phone: Optional[str] = None) -> Optional[CRMRecord]:
        """Search for a user by email or phone."""
        if not self._check_permission("read_contact"):
            raise PermissionError("No permission to read contacts")
        
        try:
            # Search by email
            result = self._make_request("GET", f"users/search.json", params={"query": email})
            users = result.get("users", [])
            if users:
                user = users[0]
                return CRMRecord(
                    record_type=CRMRecordType.CONTACT,
                    record_id=str(user["id"]),
                    provider=self.provider,
                    data=user
                )
            
            # If phone provided, search by phone
            if phone:
                result = self._make_request("GET", f"users/search.json", params={"query": phone})
                users = result.get("users", [])
                if users:
                    user = users[0]
                    return CRMRecord(
                        record_type=CRMRecordType.CONTACT,
                        record_id=str(user["id"]),
                        provider=self.provider,
                        data=user
                    )
            
            return None
        except Exception as e:
            print(f"Error buscando usuario Zendesk: {e}")
            return None

    def get_case(self, case_id: str) -> Optional[CRMRecord]:
        """Get a ticket by ID."""
        if not self._check_permission("read_ticket"):
            raise PermissionError("No permission to read tickets")
        
        try:
            data = self._make_request("GET", f"tickets/{case_id}.json")
            ticket = data["ticket"]
            return CRMRecord(
                record_type=CRMRecordType.TICKET,
                record_id=str(ticket["id"]),
                provider=self.provider,
                data=ticket,
                created_at=self._parse_datetime(ticket.get("created_at")),
                updated_at=self._parse_datetime(ticket.get("updated_at"))
            )
        except Exception as e:
            print(f"Error obteniendo ticket Zendesk: {e}")
            return None

    def get_customer_history(self, contact_id: str) -> List[CRMRecord]:
        """Get full interaction history for a customer."""
        if not self._check_permission("read_history"):
            raise PermissionError("No permission to read history")
        
        history = []
        
        # Get tickets for this user
        try:
            result = self._make_request("GET", f"users/{contact_id}/tickets/requested.json")
            for ticket in result.get("tickets", []):
                history.append(CRMRecord(
                    record_type=CRMRecordType.TICKET,
                    record_id=str(ticket["id"]),
                    provider=self.provider,
                    data=ticket,
                    created_at=self._parse_datetime(ticket.get("created_at"))
                ))
        except Exception as e:
            print(f"Error obteniendo historial de tickets: {e}")
        
        return history

    def search_account(self, name: str) -> Optional[CRMRecord]:
        """Search for an organization by name."""
        if not self._check_permission("read_account"):
            raise PermissionError("No permission to read accounts")
        
        try:
            result = self._make_request("GET", "organizations/search.json", params={"name": name})
            organizations = result.get("organizations", [])
            if organizations:
                org = organizations[0]
                return CRMRecord(
                    record_type=CRMRecordType.ACCOUNT,
                    record_id=str(org["id"]),
                    provider=self.provider,
                    data=org,
                    created_at=self._parse_datetime(org.get("created_at"))
                )
            return None
        except Exception as e:
            print(f"Error buscando organización Zendesk: {e}")
            return None

    # ========== WRITE OPERATIONS ==========

    def create_contact(self, contact_data: Dict[str, Any]) -> CRMRecord:
        """Create a new user (contact)."""
        if not self._check_permission("create_contact"):
            raise PermissionError("No permission to create contacts")
        
        try:
            # Ensure required fields
            user_data = {
                "name": contact_data.get("name", "Unknown"),
                "email": contact_data.get("email"),
                "phone": contact_data.get("phone"),
                "role": "end-user"  # or "admin", "agent"
            }
            payload = {"user": user_data}
            result = self._make_request("POST", "users.json", data=payload)
            user = result["user"]
            return CRMRecord(
                record_type=CRMRecordType.CONTACT,
                record_id=str(user["id"]),
                provider=self.provider,
                data=user
            )
        except Exception as e:
            raise ValueError(f"Error creando usuario Zendesk: {e}")

    def update_contact(self, contact_id: str, updates: Dict[str, Any]) -> CRMRecord:
        """Update an existing user."""
        if not self._check_permission("update_contact"):
            raise PermissionError("No permission to update contacts")
        
        try:
            payload = {"user": updates}
            self._make_request("PUT", f"users/{contact_id}.json", data=payload)
            return self.get_contact(contact_id)
        except Exception as e:
            raise ValueError(f"Error actualizando usuario Zendesk: {e}")

    def create_case(self, case_data: Dict[str, Any]) -> CRMRecord:
        """Create a new ticket."""
        if not self._check_permission("create_ticket"):
            raise PermissionError("No permission to create tickets")
        
        try:
            # Ensure required fields
            ticket_data = {
                "subject": case_data.get("subject", "Support Ticket"),
                "comment": {
                    "body": case_data.get("description", case_data.get("comment", ""))
                },
                "priority": case_data.get("priority", "normal"),  # low, normal, high, urgent
                "status": case_data.get("status", "new")  # new, open, pending, solved, closed
            }
            
            # Add requester if provided
            if "requester_id" in case_data:
                ticket_data["requester_id"] = case_data["requester_id"]
            elif "requester_email" in case_data:
                ticket_data["requester"] = {"email": case_data["requester_email"]}
            
            payload = {"ticket": ticket_data}
            result = self._make_request("POST", "tickets.json", data=payload)
            ticket = result["ticket"]
            return CRMRecord(
                record_type=CRMRecordType.TICKET,
                record_id=str(ticket["id"]),
                provider=self.provider,
                data=ticket
            )
        except Exception as e:
            raise ValueError(f"Error creando ticket Zendesk: {e}")

    def update_case(self, case_id: str, updates: Dict[str, Any]) -> CRMRecord:
        """Update an existing ticket."""
        if not self._check_permission("update_ticket"):
            raise PermissionError("No permission to update tickets")
        
        try:
            payload = {"ticket": updates}
            self._make_request("PUT", f"tickets/{case_id}.json", data=payload)
            return self.get_case(case_id)
        except Exception as e:
            raise ValueError(f"Error actualizando ticket Zendesk: {e}")

    def close_case(self, case_id: str, resolution: Optional[str] = None) -> CRMRecord:
        """Close a ticket with optional resolution."""
        updates = {"status": "solved"}
        if resolution:
            # Add comment with resolution
            comment_data = {
                "ticket": {
                    "status": "solved",
                    "comment": {
                        "body": resolution,
                        "public": False  # Internal note
                    }
                }
            }
            self._make_request("PUT", f"tickets/{case_id}.json", data=comment_data)
            return self.get_case(case_id)
        return self.update_case(case_id, updates)

    def add_note(self, record_id: str, note_text: str, record_type: CRMRecordType = CRMRecordType.CONTACT) -> CRMRecord:
        """Add a comment/note to a ticket."""
        if not self._check_permission("create_note"):
            raise PermissionError("No permission to create notes")
        
        # In Zendesk, notes are added as comments on tickets
        if record_type == CRMRecordType.TICKET:
            try:
                comment_data = {
                    "ticket": {
                        "comment": {
                            "body": note_text,
                            "public": False  # Internal note
                        }
                    }
                }
                self._make_request("PUT", f"tickets/{record_id}.json", data=comment_data)
                return CRMRecord(
                    record_type=CRMRecordType.NOTE,
                    record_id=record_id,
                    provider=self.provider,
                    data={"body": note_text}
                )
            except Exception as e:
                raise ValueError(f"Error agregando nota Zendesk: {e}")
        else:
            raise ValueError("Zendesk notes can only be added to tickets")

    def create_task(self, task_data: Dict[str, Any]) -> CRMRecord:
        """Create a task/follow-up (Zendesk doesn't have separate tasks, use ticket with status 'pending')."""
        if not self._check_permission("create_task"):
            raise PermissionError("No permission to create tasks")
        
        try:
            # Create a ticket with status 'pending' as a task
            ticket_data = {
                "subject": task_data.get("subject", "Follow-up Task"),
                "comment": {
                    "body": task_data.get("description", task_data.get("note", ""))
                },
                "status": "pending",
                "priority": task_data.get("priority", "normal")
            }
            
            if "requester_id" in task_data:
                ticket_data["requester_id"] = task_data["requester_id"]
            
            payload = {"ticket": ticket_data}
            result = self._make_request("POST", "tickets.json", data=payload)
            ticket = result["ticket"]
            return CRMRecord(
                record_type=CRMRecordType.TASK,
                record_id=str(ticket["id"]),
                provider=self.provider,
                data=ticket
            )
        except Exception as e:
            raise ValueError(f"Error creando tarea Zendesk: {e}")

    # ========== UTILITY METHODS ==========

    def _parse_datetime(self, date_str: Optional[str]) -> Optional[datetime]:
        """Parse Zendesk datetime string (ISO 8601 format)."""
        if not date_str:
            return None
        try:
            return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except:
            return None

