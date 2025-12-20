"""
Ticket Tool - Simulates Zendesk/Salesforce CRM integration
Production-ready with comprehensive ticket management
"""
from typing import Dict, Any, Optional, List
import logging
import uuid
from datetime import datetime
from enum import Enum

from ..utils.logging import setup_logger

logger = setup_logger("customer_service_24_7.tools.ticket")


class TicketPriority(Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class TicketTool:
    """Tool for creating and managing support tickets"""
    
    def __init__(self):
        """Initialize Ticket Tool"""
        self.tickets = {}  # In production, connect to Zendesk/Salesforce
        logger.info("✅ Ticket Tool inicializado")
    
    def create_ticket(
        self,
        issue_description: str,
        customer_email: Optional[str] = None,
        priority: str = "normal",
        category: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a support ticket
        
        Args:
            issue_description: Description of the issue
            customer_email: Customer email
            priority: Ticket priority (low, normal, high, urgent)
            category: Issue category
            
        Returns:
            Ticket information
        """
        logger.info(f"🎫 Creando ticket: {issue_description[:50]}...")
        
        if not issue_description:
            raise ValueError("issue_description is required")
        
        ticket_id = f"TKT-{uuid.uuid4().hex[:8].upper()}"
        
        # In production, this would call Zendesk/Salesforce API:
        # zendesk.tickets.create(subject=issue_description, ...)
        
        ticket = {
            "ticket_id": ticket_id,
            "issue_description": issue_description,
            "customer_email": customer_email,
            "priority": priority,
            "category": category or "general",
            "status": "open",
            "created_at": datetime.now().isoformat(),
            "estimated_response_time": self._get_response_time(priority),
            "message": f"Ticket #{ticket_id} created successfully"
        }
        
        self.tickets[ticket_id] = ticket
        
        logger.info(f"✅ Ticket creado: {ticket_id}")
        
        return ticket
    
    def get_ticket_status(self, ticket_id: str) -> Dict[str, Any]:
        """
        Get ticket status
        
        Args:
            ticket_id: Ticket ID
            
        Returns:
            Ticket status
        """
        if ticket_id in self.tickets:
            return self.tickets[ticket_id]
        
        return {
            "ticket_id": ticket_id,
            "status": "not_found",
            "message": "Ticket not found"
        }
    
    def update_ticket(
        self,
        ticket_id: str,
        status: Optional[str] = None,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update ticket
        
        Args:
            ticket_id: Ticket ID
            status: New status
            notes: Additional notes
            
        Returns:
            Updated ticket
        """
        if ticket_id not in self.tickets:
            return {"error": "Ticket not found"}
        
        if status:
            self.tickets[ticket_id]["status"] = status
        if notes:
            self.tickets[ticket_id]["notes"] = notes
        
        self.tickets[ticket_id]["updated_at"] = datetime.now().isoformat()
        
        logger.info(f"✅ Ticket actualizado: {ticket_id}")
        
        return self.tickets[ticket_id]
    
    def _get_response_time(self, priority: str) -> str:
        """Get estimated response time based on priority"""
        times = {
            "urgent": "2-4 hours",
            "high": "4-8 hours",
            "normal": "24 hours",
            "low": "48 hours"
        }
        return times.get(priority.lower(), "24 hours")
    
    def get_langchain_tool(self):
        """Get LangChain tool wrapper"""
        from langchain.tools import tool
        
        @tool
        def create_ticket_tool(issue_description: str, customer_email: Optional[str] = None, priority: str = "normal") -> str:
            """
            Create a support ticket for a customer issue. Use this when you need to escalate a complex issue or when policy requires human intervention.
            
            Args:
                issue_description: Description of the customer issue (required)
                customer_email: Customer email address
                priority: Ticket priority (low, normal, high, urgent)
                
            Returns:
                JSON string with ticket details including ticket_id, status, and estimated_response_time
            """
            result = self.create_ticket(issue_description, customer_email, priority)
            import json
            return json.dumps(result, indent=2)
        
        return create_ticket_tool













