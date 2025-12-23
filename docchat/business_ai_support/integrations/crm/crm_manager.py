"""
CRM Manager - Orchestrates multiple CRM connectors

Manages connections to multiple CRM systems (Salesforce, HubSpot, Zendesk)
and provides unified interface for the Business AI Agent.
"""

from __future__ import annotations

from typing import Dict, Any, Optional, List
from .base import CRMConnector, CRMConfig, CRMProvider, CRMRecord, CRMRecordType
from .salesforce_connector import SalesforceConnector
from .hubspot_connector import HubSpotConnector
from .zendesk_connector import ZendeskConnector


class CRMManager:
    """
    Manages multiple CRM connections and provides unified interface.
    
    Can connect to multiple CRMs simultaneously and route operations
    to the appropriate system based on configuration.
    """

    def __init__(self, configs: Optional[List[CRMConfig]] = None):
        """Initialize CRM Manager with CRM configurations."""
        self.connectors: Dict[CRMProvider, CRMConnector] = {}
        
        if configs:
            for config in configs:
                self.add_connector(config)

    def add_connector(self, config: CRMConfig) -> None:
        """Add a CRM connector."""
        try:
            if config.provider == CRMProvider.SALESFORCE:
                connector = SalesforceConnector(config)
            elif config.provider == CRMProvider.HUBSPOT:
                connector = HubSpotConnector(config)
            elif config.provider == CRMProvider.ZENDESK:
                connector = ZendeskConnector(config)
            else:
                raise ValueError(f"Unsupported CRM provider: {config.provider}")
            
            # Test connection
            if connector.test_connection():
                self.connectors[config.provider] = connector
                print(f"✅ CRM {config.provider.value} conectado exitosamente")
            else:
                print(f"⚠️ Error conectando a {config.provider.value}")
        except Exception as e:
            print(f"⚠️ Error inicializando {config.provider.value}: {e}")

    def get_connector(self, provider: Optional[CRMProvider] = None) -> Optional[CRMConnector]:
        """Get a specific connector or the first available one."""
        if provider:
            return self.connectors.get(provider)
        
        # Return first available connector
        if self.connectors:
            return list(self.connectors.values())[0]
        return None

    def has_connector(self, provider: CRMProvider) -> bool:
        """Check if a specific CRM connector is available."""
        return provider in self.connectors

    def get_contact(self, contact_id: str, provider: Optional[CRMProvider] = None) -> Optional[CRMRecord]:
        """Get contact from CRM."""
        connector = self.get_connector(provider)
        if connector:
            return connector.get_contact(contact_id)
        return None

    def search_contact(self, email: str, phone: Optional[str] = None, provider: Optional[CRMProvider] = None) -> Optional[CRMRecord]:
        """Search for contact across all connected CRMs."""
        if provider:
            connector = self.get_connector(provider)
            if connector:
                return connector.search_contact(email, phone)
        else:
            # Search across all connectors
            for connector in self.connectors.values():
                try:
                    result = connector.search_contact(email, phone)
                    if result:
                        return result
                except Exception as e:
                    print(f"Error buscando contacto en {connector.provider}: {e}")
                    continue
        return None

    def create_contact(self, contact_data: Dict[str, Any], provider: Optional[CRMProvider] = None) -> Optional[CRMRecord]:
        """Create contact in CRM."""
        connector = self.get_connector(provider)
        if connector:
            return connector.create_contact(contact_data)
        return None

    def update_contact(self, contact_id: str, updates: Dict[str, Any], provider: Optional[CRMProvider] = None) -> Optional[CRMRecord]:
        """Update contact in CRM."""
        connector = self.get_connector(provider)
        if connector:
            return connector.update_contact(contact_id, updates)
        return None

    def create_case(self, case_data: Dict[str, Any], provider: Optional[CRMProvider] = None) -> Optional[CRMRecord]:
        """Create case/ticket in CRM."""
        connector = self.get_connector(provider)
        if connector:
            return connector.create_case(case_data)
        return None

    def update_case(self, case_id: str, updates: Dict[str, Any], provider: Optional[CRMProvider] = None) -> Optional[CRMRecord]:
        """Update case/ticket in CRM."""
        connector = self.get_connector(provider)
        if connector:
            return connector.update_case(case_id, updates)
        return None

    def close_case(self, case_id: str, resolution: Optional[str] = None, provider: Optional[CRMProvider] = None) -> Optional[CRMRecord]:
        """Close case/ticket in CRM."""
        connector = self.get_connector(provider)
        if connector:
            return connector.close_case(case_id, resolution)
        return None

    def get_customer_history(self, contact_id: str, provider: Optional[CRMProvider] = None) -> List[CRMRecord]:
        """Get customer history from CRM."""
        connector = self.get_connector(provider)
        if connector:
            return connector.get_customer_history(contact_id)
        return []

    def add_note(self, record_id: str, note_text: str, record_type: CRMRecordType = CRMRecordType.CONTACT, provider: Optional[CRMProvider] = None) -> Optional[CRMRecord]:
        """Add note to record in CRM."""
        connector = self.get_connector(provider)
        if connector:
            return connector.add_note(record_id, note_text, record_type)
        return None

    def create_task(self, task_data: Dict[str, Any], provider: Optional[CRMProvider] = None) -> Optional[CRMRecord]:
        """Create task/follow-up in CRM."""
        connector = self.get_connector(provider)
        if connector:
            return connector.create_task(task_data)
        return None

    def sync_ticket_to_crm(self, ticket_data: Dict[str, Any], contact_email: Optional[str] = None, provider: Optional[CRMProvider] = None) -> Optional[CRMRecord]:
        """
        Sync a ticket from internal system to CRM.
        This is a convenience method that:
        1. Finds or creates contact
        2. Creates case/ticket in CRM
        3. Links them together
        """
        connector = self.get_connector(provider)
        if not connector:
            return None

        contact = None
        if contact_email:
            # Try to find existing contact
            contact = connector.search_contact(contact_email)
            
            # Create contact if not found
            if not contact:
                contact = connector.create_contact({
                    "email": contact_email,
                    "name": ticket_data.get("customer_name", "Unknown")
                })

        # Create case with contact association
        case_data = {
            "subject": ticket_data.get("subject", "Support Case"),
            "description": ticket_data.get("description", ""),
            "status": ticket_data.get("status", "new"),
            "priority": ticket_data.get("priority", "normal")
        }
        
        # Add contact association based on CRM
        if contact:
            if connector.provider == CRMProvider.SALESFORCE:
                case_data["ContactId"] = contact.record_id
            elif connector.provider == CRMProvider.HUBSPOT:
                case_data["associations"] = {"contactIds": [contact.record_id]}
            elif connector.provider == CRMProvider.ZENDESK:
                case_data["requester_id"] = contact.record_id

        return connector.create_case(case_data)

