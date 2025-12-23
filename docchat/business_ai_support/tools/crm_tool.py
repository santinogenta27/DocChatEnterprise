"""
CRM Tool - Wrapper for CRM operations in Business AI Agent

Provides LangChain-compatible tool interface for CRM operations.
"""

from __future__ import annotations

from typing import Dict, Any, Optional, List
from ..integrations.crm.crm_manager import CRMManager
from ..integrations.crm.base import CRMProvider, CRMRecordType


class CRMTool:
    """
    Tool wrapper for CRM operations.
    
    Provides methods that can be called by the Business AI Agent
    to interact with CRM systems.
    """

    def __init__(self, crm_manager: CRMManager):
        """Initialize CRM Tool with CRM Manager."""
        self.crm_manager = crm_manager
        self.has_crm = crm_manager.connectors is not None and len(crm_manager.connectors) > 0

    def get_customer_info(self, email: str, phone: Optional[str] = None, provider: Optional[str] = None) -> Dict[str, Any]:
        """
        Get customer information from CRM.
        
        Args:
            email: Customer email
            phone: Customer phone (optional)
            provider: CRM provider (salesforce, hubspot, zendesk) - optional
            
        Returns:
            Dict with customer information or None if not found
        """
        if not self.has_crm:
            return {"error": "No CRM connector configured"}
        
        crm_provider = CRMProvider(provider) if provider else None
        contact = self.crm_manager.search_contact(email, phone, crm_provider)
        
        if contact:
            return {
                "found": True,
                "contact_id": contact.record_id,
                "data": contact.data,
                "provider": contact.provider.value
            }
        return {"found": False, "message": "Contact not found in CRM"}

    def get_customer_history(self, contact_id: str, provider: Optional[str] = None) -> Dict[str, Any]:
        """
        Get customer interaction history from CRM.
        
        Args:
            contact_id: Contact ID in CRM
            provider: CRM provider (optional)
            
        Returns:
            Dict with customer history
        """
        if not self.has_crm:
            return {"error": "No CRM connector configured"}
        
        crm_provider = CRMProvider(provider) if provider else None
        history = self.crm_manager.get_customer_history(contact_id, crm_provider)
        
        return {
            "contact_id": contact_id,
            "history_count": len(history),
            "records": [
                {
                    "type": record.record_type.value,
                    "id": record.record_id,
                    "data": record.data
                }
                for record in history
            ]
        }

    def create_or_update_contact(self, contact_data: Dict[str, Any], provider: Optional[str] = None) -> Dict[str, Any]:
        """
        Create or update a contact in CRM.
        If contact exists (by email), updates it. Otherwise creates new.
        
        Args:
            contact_data: Contact data (email, name, phone, etc.)
            provider: CRM provider (optional)
            
        Returns:
            Dict with created/updated contact information
        """
        if not self.has_crm:
            return {"error": "No CRM connector configured"}
        
        crm_provider = CRMProvider(provider) if provider else None
        email = contact_data.get("email")
        
        if email:
            # Try to find existing contact
            existing = self.crm_manager.search_contact(email, provider=crm_provider)
            if existing:
                # Update existing
                updated = self.crm_manager.update_contact(existing.record_id, contact_data, crm_provider)
                return {
                    "action": "updated",
                    "contact_id": updated.record_id,
                    "data": updated.data
                }
        
        # Create new
        new_contact = self.crm_manager.create_contact(contact_data, crm_provider)
        return {
            "action": "created",
            "contact_id": new_contact.record_id,
            "data": new_contact.data
        }

    def create_crm_case(self, case_data: Dict[str, Any], contact_email: Optional[str] = None, provider: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a case/ticket in CRM.
        Optionally links to existing contact.
        
        Args:
            case_data: Case data (subject, description, status, priority)
            contact_email: Email of contact to link (optional)
            provider: CRM provider (optional)
            
        Returns:
            Dict with created case information
        """
        if not self.has_crm:
            return {"error": "No CRM connector configured"}
        
        crm_provider = CRMProvider(provider) if provider else None
        
        # If contact_email provided, use sync method to handle linking
        if contact_email:
            result = self.crm_manager.sync_ticket_to_crm(case_data, contact_email, crm_provider)
        else:
            result = self.crm_manager.create_case(case_data, crm_provider)
        
        if result:
            return {
                "success": True,
                "case_id": result.record_id,
                "data": result.data,
                "provider": result.provider.value
            }
        return {"success": False, "error": "Failed to create case"}

    def update_crm_case(self, case_id: str, updates: Dict[str, Any], provider: Optional[str] = None) -> Dict[str, Any]:
        """
        Update a case/ticket in CRM.
        
        Args:
            case_id: Case ID in CRM
            updates: Updates to apply (status, priority, description, etc.)
            provider: CRM provider (optional)
            
        Returns:
            Dict with updated case information
        """
        if not self.has_crm:
            return {"error": "No CRM connector configured"}
        
        crm_provider = CRMProvider(provider) if provider else None
        updated = self.crm_manager.update_case(case_id, updates, crm_provider)
        
        if updated:
            return {
                "success": True,
                "case_id": updated.record_id,
                "data": updated.data
            }
        return {"success": False, "error": "Failed to update case"}

    def close_crm_case(self, case_id: str, resolution: Optional[str] = None, provider: Optional[str] = None) -> Dict[str, Any]:
        """
        Close a case/ticket in CRM with optional resolution.
        
        Args:
            case_id: Case ID in CRM
            resolution: Resolution notes (optional)
            provider: CRM provider (optional)
            
        Returns:
            Dict with closed case information
        """
        if not self.has_crm:
            return {"error": "No CRM connector configured"}
        
        crm_provider = CRMProvider(provider) if provider else None
        closed = self.crm_manager.close_case(case_id, resolution, crm_provider)
        
        if closed:
            return {
                "success": True,
                "case_id": closed.record_id,
                "status": "closed",
                "data": closed.data
            }
        return {"success": False, "error": "Failed to close case"}

    def add_crm_note(self, record_id: str, note_text: str, record_type: str = "contact", provider: Optional[str] = None) -> Dict[str, Any]:
        """
        Add a note/comment to a CRM record.
        
        Args:
            record_id: Record ID in CRM
            note_text: Note text
            record_type: Type of record (contact, case, ticket)
            provider: CRM provider (optional)
            
        Returns:
            Dict with note information
        """
        if not self.has_crm:
            return {"error": "No CRM connector configured"}
        
        crm_provider = CRMProvider(provider) if provider else None
        record_type_enum = CRMRecordType(record_type)
        
        note = self.crm_manager.add_note(record_id, note_text, record_type_enum, crm_provider)
        
        if note:
            return {
                "success": True,
                "note_id": note.record_id,
                "data": note.data
            }
        return {"success": False, "error": "Failed to add note"}

    def create_crm_task(self, task_data: Dict[str, Any], provider: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a task/follow-up in CRM.
        
        Args:
            task_data: Task data (subject, description, due_date, etc.)
            provider: CRM provider (optional)
            
        Returns:
            Dict with created task information
        """
        if not self.has_crm:
            return {"error": "No CRM connector configured"}
        
        crm_provider = CRMProvider(provider) if provider else None
        task = self.crm_manager.create_task(task_data, crm_provider)
        
        if task:
            return {
                "success": True,
                "task_id": task.record_id,
                "data": task.data
            }
        return {"success": False, "error": "Failed to create task"}

    def get_tool_description(self) -> str:
        """Get description of CRM tool for agent prompts."""
        if not self.has_crm:
            return "CRM integration is not configured."
        
        providers = [p.value for p in self.crm_manager.connectors.keys()]
        return f"""
CRM Tool - Deep Integration with {', '.join(providers)}

Available operations:
- get_customer_info: Get customer information from CRM by email/phone
- get_customer_history: Get full interaction history for a customer
- create_or_update_contact: Create or update customer contact
- create_crm_case: Create support case/ticket in CRM
- update_crm_case: Update existing case/ticket
- close_crm_case: Close case with resolution
- add_crm_note: Add note/comment to CRM record
- create_crm_task: Create follow-up task

The CRM system provides contextual customer data, allowing the agent to:
- Know customer history before responding
- Automatically create/update records
- Sync tickets between internal system and CRM
- Maintain accurate customer data without manual intervention
"""

