"""
Base Classes for CRM Integration

Defines the abstract interface and common structures for CRM connectors.
"""

from __future__ import annotations

from typing import Dict, Any, Optional, List
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class CRMProvider(str, Enum):
    """Supported CRM providers."""
    SALESFORCE = "salesforce"
    HUBSPOT = "hubspot"
    ZENDESK = "zendesk"


class CRMRecordType(str, Enum):
    """Types of CRM records."""
    CONTACT = "contact"
    LEAD = "lead"
    ACCOUNT = "account"
    CASE = "case"
    TICKET = "ticket"
    OPPORTUNITY = "opportunity"
    DEAL = "deal"
    NOTE = "note"
    TASK = "task"


@dataclass
class CRMConfig:
    """Configuration for a CRM connection."""
    provider: CRMProvider
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    base_url: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    security_token: Optional[str] = None  # For Salesforce
    access_token: Optional[str] = None  # OAuth token
    refresh_token: Optional[str] = None  # OAuth refresh token
    instance_url: Optional[str] = None  # For Salesforce
    subdomain: Optional[str] = None  # For Zendesk
    permissions: List[str] = field(default_factory=list)  # Permitted actions
    encryption_key: Optional[str] = None  # For PII encryption


@dataclass
class CRMRecord:
    """Represents a CRM record."""
    record_type: CRMRecordType
    record_id: str
    provider: CRMProvider
    data: Dict[str, Any]
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class CRMConnector(ABC):
    """
    Abstract base class for CRM connectors.
    
    All CRM connectors must implement these methods to provide
    deep integration capabilities.
    """

    def __init__(self, config: CRMConfig):
        """Initialize the CRM connector."""
        self.config = config
        self.provider = config.provider
        self._validate_config()

    @abstractmethod
    def _validate_config(self) -> None:
        """Validate the configuration is complete and valid."""
        pass

    @abstractmethod
    def test_connection(self) -> bool:
        """Test the connection to the CRM."""
        pass

    # ========== READ OPERATIONS ==========

    @abstractmethod
    def get_contact(self, contact_id: str) -> Optional[CRMRecord]:
        """Get a contact by ID."""
        pass

    @abstractmethod
    def search_contact(self, email: str, phone: Optional[str] = None) -> Optional[CRMRecord]:
        """Search for a contact by email or phone."""
        pass

    @abstractmethod
    def get_case(self, case_id: str) -> Optional[CRMRecord]:
        """Get a case/ticket by ID."""
        pass

    @abstractmethod
    def get_customer_history(self, contact_id: str) -> List[CRMRecord]:
        """Get full interaction history for a customer."""
        pass

    @abstractmethod
    def search_account(self, name: str) -> Optional[CRMRecord]:
        """Search for an account/company by name."""
        pass

    # ========== WRITE OPERATIONS ==========

    @abstractmethod
    def create_contact(self, contact_data: Dict[str, Any]) -> CRMRecord:
        """Create a new contact."""
        pass

    @abstractmethod
    def update_contact(self, contact_id: str, updates: Dict[str, Any]) -> CRMRecord:
        """Update an existing contact."""
        pass

    @abstractmethod
    def create_case(self, case_data: Dict[str, Any]) -> CRMRecord:
        """Create a new case/ticket."""
        pass

    @abstractmethod
    def update_case(self, case_id: str, updates: Dict[str, Any]) -> CRMRecord:
        """Update an existing case/ticket."""
        pass

    @abstractmethod
    def close_case(self, case_id: str, resolution: Optional[str] = None) -> CRMRecord:
        """Close a case/ticket with optional resolution."""
        pass

    @abstractmethod
    def add_note(self, record_id: str, note_text: str, record_type: CRMRecordType = CRMRecordType.CONTACT) -> CRMRecord:
        """Add a note/comment to a record."""
        pass

    @abstractmethod
    def create_task(self, task_data: Dict[str, Any]) -> CRMRecord:
        """Create a task/follow-up."""
        pass

    # ========== UTILITY METHODS ==========

    def _check_permission(self, action: str) -> bool:
        """Check if the connector has permission for an action."""
        if not self.config.permissions:
            return True  # No restrictions if permissions not specified
        return action in self.config.permissions

    def _encrypt_pii(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Encrypt PII fields if encryption key is configured."""
        # TODO: Implement PII encryption
        # For now, return as-is
        return data

    def _decrypt_pii(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Decrypt PII fields if encryption key is configured."""
        # TODO: Implement PII decryption
        # For now, return as-is
        return data

