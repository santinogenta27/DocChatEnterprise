"""
Salesforce CRM Connector

Deep integration with Salesforce CRM using REST API.
Supports: Cases, Contacts, Accounts, Leads, Notes, Tasks
"""

from __future__ import annotations

import requests
from typing import Dict, Any, Optional, List
from datetime import datetime
import json

try:
    from simple_salesforce import Salesforce
    SIMPLE_SALESFORCE_AVAILABLE = True
except ImportError:
    SIMPLE_SALESFORCE_AVAILABLE = False

from .base import CRMConnector, CRMConfig, CRMRecord, CRMProvider, CRMRecordType


class SalesforceConnector(CRMConnector):
    """
    Salesforce CRM Connector using REST API.
    
    Supports authentication via:
    - Username/Password/Security Token
    - OAuth (Access Token/Refresh Token)
    """

    def __init__(self, config: CRMConfig):
        """Initialize Salesforce connector."""
        super().__init__(config)
        self.instance_url = config.instance_url
        self.session_id = None  # Session ID for API calls
        self._authenticate()

    def _validate_config(self) -> None:
        """Validate Salesforce configuration."""
        # Must have either username/password/token OR access_token/instance_url
        if self.config.access_token and self.config.instance_url:
            return  # OAuth flow
        
        if not (self.config.username and self.config.password):
            raise ValueError("Salesforce config must have username/password OR access_token/instance_url")
        
        if not self.config.security_token:
            raise ValueError("Salesforce config must have security_token for username/password auth")

    def _authenticate(self) -> None:
        """Authenticate with Salesforce."""
        if self.config.access_token and self.config.instance_url:
            # OAuth flow - already authenticated
            self.instance_url = self.config.instance_url
            self.session_id = self.config.access_token
            return

        # Username/Password/Token authentication
        if SIMPLE_SALESFORCE_AVAILABLE:
            try:
                self.sf = Salesforce(
                    username=self.config.username,
                    password=self.config.password,
                    security_token=self.config.security_token,
                    domain='login'  # or 'test' for sandbox
                )
                self.instance_url = self.sf.sf_instance
                self.session_id = self.sf.session_id
                print(f"✅ Salesforce autenticado: {self.instance_url}")
            except Exception as e:
                raise ValueError(f"Error autenticando con Salesforce: {e}")
        else:
            # Manual authentication via REST API
            auth_url = "https://login.salesforce.com/services/oauth2/token"
            payload = {
                "grant_type": "password",
                "client_id": self.config.api_key or "",
                "client_secret": self.config.api_secret or "",
                "username": self.config.username,
                "password": self.config.password + self.config.security_token
            }
            response = requests.post(auth_url, data=payload)
            if response.status_code != 200:
                raise ValueError(f"Error autenticando: {response.text}")
            data = response.json()
            self.instance_url = data["instance_url"]
            self.session_id = data["access_token"]
            print(f"✅ Salesforce autenticado: {self.instance_url}")

    def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        """Make authenticated request to Salesforce API."""
        url = f"{self.instance_url}/services/data/v58.0/{endpoint}"
        headers = {
            "Authorization": f"Bearer {self.session_id}",
            "Content-Type": "application/json"
        }
        
        if method == "GET":
            response = requests.get(url, headers=headers)
        elif method == "POST":
            response = requests.post(url, headers=headers, json=data)
        elif method == "PATCH":
            response = requests.patch(url, headers=headers, json=data)
        elif method == "DELETE":
            response = requests.delete(url, headers=headers)
        else:
            raise ValueError(f"Unsupported method: {method}")
        
        if response.status_code >= 400:
            raise ValueError(f"Salesforce API error: {response.status_code} - {response.text}")
        
        return response.json() if response.text else {}

    def test_connection(self) -> bool:
        """Test connection to Salesforce."""
        try:
            result = self._make_request("GET", "sobjects/Contact/describe")
            return True
        except Exception as e:
            print(f"❌ Error probando conexión Salesforce: {e}")
            return False

    # ========== READ OPERATIONS ==========

    def get_contact(self, contact_id: str) -> Optional[CRMRecord]:
        """Get a contact by ID."""
        if not self._check_permission("read_contact"):
            raise PermissionError("No permission to read contacts")
        
        try:
            data = self._make_request("GET", f"sobjects/Contact/{contact_id}")
            return CRMRecord(
                record_type=CRMRecordType.CONTACT,
                record_id=data["Id"],
                provider=self.provider,
                data=data,
                created_at=self._parse_datetime(data.get("CreatedDate")),
                updated_at=self._parse_datetime(data.get("LastModifiedDate"))
            )
        except Exception as e:
            print(f"Error obteniendo contacto Salesforce: {e}")
            return None

    def search_contact(self, email: str, phone: Optional[str] = None) -> Optional[CRMRecord]:
        """Search for a contact by email or phone."""
        if not self._check_permission("read_contact"):
            raise PermissionError("No permission to read contacts")
        
        try:
            # SOQL query to search by email
            query = f"SELECT Id, FirstName, LastName, Email, Phone FROM Contact WHERE Email = '{email}' LIMIT 1"
            if phone:
                query = f"SELECT Id, FirstName, LastName, Email, Phone FROM Contact WHERE Email = '{email}' OR Phone = '{phone}' LIMIT 1"
            
            result = self._make_request("GET", f"query/?q={query.replace(' ', '+')}")
            if result.get("records") and len(result["records"]) > 0:
                data = result["records"][0]
                return CRMRecord(
                    record_type=CRMRecordType.CONTACT,
                    record_id=data["Id"],
                    provider=self.provider,
                    data=data
                )
            return None
        except Exception as e:
            print(f"Error buscando contacto Salesforce: {e}")
            return None

    def get_case(self, case_id: str) -> Optional[CRMRecord]:
        """Get a case by ID."""
        if not self._check_permission("read_case"):
            raise PermissionError("No permission to read cases")
        
        try:
            data = self._make_request("GET", f"sobjects/Case/{case_id}")
            return CRMRecord(
                record_type=CRMRecordType.CASE,
                record_id=data["Id"],
                provider=self.provider,
                data=data,
                created_at=self._parse_datetime(data.get("CreatedDate")),
                updated_at=self._parse_datetime(data.get("LastModifiedDate"))
            )
        except Exception as e:
            print(f"Error obteniendo caso Salesforce: {e}")
            return None

    def get_customer_history(self, contact_id: str) -> List[CRMRecord]:
        """Get full interaction history for a customer."""
        if not self._check_permission("read_history"):
            raise PermissionError("No permission to read history")
        
        history = []
        
        # Get cases
        try:
            query = f"SELECT Id, Subject, Status, CreatedDate FROM Case WHERE ContactId = '{contact_id}' ORDER BY CreatedDate DESC"
            result = self._make_request("GET", f"query/?q={query.replace(' ', '+')}")
            for record in result.get("records", []):
                history.append(CRMRecord(
                    record_type=CRMRecordType.CASE,
                    record_id=record["Id"],
                    provider=self.provider,
                    data=record,
                    created_at=self._parse_datetime(record.get("CreatedDate"))
                ))
        except Exception as e:
            print(f"Error obteniendo historial de casos: {e}")
        
        # Get tasks
        try:
            query = f"SELECT Id, Subject, Status, CreatedDate FROM Task WHERE WhoId = '{contact_id}' ORDER BY CreatedDate DESC LIMIT 50"
            result = self._make_request("GET", f"query/?q={query.replace(' ', '+')}")
            for record in result.get("records", []):
                history.append(CRMRecord(
                    record_type=CRMRecordType.TASK,
                    record_id=record["Id"],
                    provider=self.provider,
                    data=record,
                    created_at=self._parse_datetime(record.get("CreatedDate"))
                ))
        except Exception as e:
            print(f"Error obteniendo historial de tareas: {e}")
        
        return history

    def search_account(self, name: str) -> Optional[CRMRecord]:
        """Search for an account by name."""
        if not self._check_permission("read_account"):
            raise PermissionError("No permission to read accounts")
        
        try:
            query = f"SELECT Id, Name FROM Account WHERE Name LIKE '%{name}%' LIMIT 1"
            result = self._make_request("GET", f"query/?q={query.replace(' ', '+')}")
            if result.get("records") and len(result["records"]) > 0:
                data = result["records"][0]
                return CRMRecord(
                    record_type=CRMRecordType.ACCOUNT,
                    record_id=data["Id"],
                    provider=self.provider,
                    data=data
                )
            return None
        except Exception as e:
            print(f"Error buscando cuenta Salesforce: {e}")
            return None

    # ========== WRITE OPERATIONS ==========

    def create_contact(self, contact_data: Dict[str, Any]) -> CRMRecord:
        """Create a new contact."""
        if not self._check_permission("create_contact"):
            raise PermissionError("No permission to create contacts")
        
        try:
            result = self._make_request("POST", "sobjects/Contact/", contact_data)
            # Get the created record
            contact_id = result["id"]
            return self.get_contact(contact_id)
        except Exception as e:
            raise ValueError(f"Error creando contacto Salesforce: {e}")

    def update_contact(self, contact_id: str, updates: Dict[str, Any]) -> CRMRecord:
        """Update an existing contact."""
        if not self._check_permission("update_contact"):
            raise PermissionError("No permission to update contacts")
        
        try:
            self._make_request("PATCH", f"sobjects/Contact/{contact_id}", updates)
            return self.get_contact(contact_id)
        except Exception as e:
            raise ValueError(f"Error actualizando contacto Salesforce: {e}")

    def create_case(self, case_data: Dict[str, Any]) -> CRMRecord:
        """Create a new case."""
        if not self._check_permission("create_case"):
            raise PermissionError("No permission to create cases")
        
        # Ensure required fields
        if "Subject" not in case_data:
            case_data["Subject"] = "Support Case"
        if "Status" not in case_data:
            case_data["Status"] = "New"
        
        try:
            result = self._make_request("POST", "sobjects/Case/", case_data)
            case_id = result["id"]
            return self.get_case(case_id)
        except Exception as e:
            raise ValueError(f"Error creando caso Salesforce: {e}")

    def update_case(self, case_id: str, updates: Dict[str, Any]) -> CRMRecord:
        """Update an existing case."""
        if not self._check_permission("update_case"):
            raise PermissionError("No permission to update cases")
        
        try:
            self._make_request("PATCH", f"sobjects/Case/{case_id}", updates)
            return self.get_case(case_id)
        except Exception as e:
            raise ValueError(f"Error actualizando caso Salesforce: {e}")

    def close_case(self, case_id: str, resolution: Optional[str] = None) -> CRMRecord:
        """Close a case with optional resolution."""
        updates = {"Status": "Closed"}
        if resolution:
            updates["Description"] = resolution
        return self.update_case(case_id, updates)

    def add_note(self, record_id: str, note_text: str, record_type: CRMRecordType = CRMRecordType.CONTACT) -> CRMRecord:
        """Add a note/comment to a record."""
        if not self._check_permission("create_note"):
            raise PermissionError("No permission to create notes")
        
        # In Salesforce, notes are added via ContentNote or Note objects
        # For simplicity, we'll use the Description field or create a Task
        try:
            # Create a Task as a note
            task_data = {
                "WhoId": record_id if record_type == CRMRecordType.CONTACT else None,
                "WhatId": record_id if record_type != CRMRecordType.CONTACT else None,
                "Subject": "Note from AI Agent",
                "Description": note_text,
                "Status": "Completed"
            }
            result = self._make_request("POST", "sobjects/Task/", task_data)
            task_id = result["id"]
            data = self._make_request("GET", f"sobjects/Task/{task_id}")
            return CRMRecord(
                record_type=CRMRecordType.NOTE,
                record_id=task_id,
                provider=self.provider,
                data=data
            )
        except Exception as e:
            raise ValueError(f"Error agregando nota Salesforce: {e}")

    def create_task(self, task_data: Dict[str, Any]) -> CRMRecord:
        """Create a task/follow-up."""
        if not self._check_permission("create_task"):
            raise PermissionError("No permission to create tasks")
        
        try:
            result = self._make_request("POST", "sobjects/Task/", task_data)
            task_id = result["id"]
            data = self._make_request("GET", f"sobjects/Task/{task_id}")
            return CRMRecord(
                record_type=CRMRecordType.TASK,
                record_id=task_id,
                provider=self.provider,
                data=data
            )
        except Exception as e:
            raise ValueError(f"Error creando tarea Salesforce: {e}")

    # ========== UTILITY METHODS ==========

    def _parse_datetime(self, date_str: Optional[str]) -> Optional[datetime]:
        """Parse Salesforce datetime string."""
        if not date_str:
            return None
        try:
            # Salesforce format: "2024-01-01T12:00:00.000+0000"
            return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except:
            return None

