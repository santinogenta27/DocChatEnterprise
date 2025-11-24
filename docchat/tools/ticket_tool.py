"""Ticket management tool for customer service automation."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from datetime import datetime
import json

from .base_tool import BaseTool, ToolResult


class TicketTool(BaseTool):
    """Tool for managing customer service tickets (create, update, resolve, escalate)."""
    
    def __init__(self, config: Any):
        super().__init__(config)
        # Almacenamiento simple de tickets (en producción usar base de datos)
        self.tickets: Dict[str, Dict[str, Any]] = {}
        self.ticket_counter = 0
    
    def get_name(self) -> str:
        return "ticket_manager"
    
    def get_description(self) -> str:
        return "Create, update, resolve, and escalate customer service tickets"
    
    def get_keywords(self) -> List[str]:
        return ["ticket", "incidente", "caso", "solicitud", "problema", "issue", "support ticket"]
    
    def execute(
        self,
        action: str,
        ticket_id: Optional[str] = None,
        customer_email: Optional[str] = None,
        subject: Optional[str] = None,
        description: Optional[str] = None,
        priority: str = "medium",
        status: Optional[str] = None,
        resolution: Optional[str] = None,
        **kwargs
    ) -> ToolResult:
        """Execute ticket management action."""
        try:
            action = action.lower()
            
            if action == "create":
                return self._create_ticket(customer_email, subject, description, priority)
            elif action == "update":
                if not ticket_id:
                    return ToolResult(
                        success=False,
                        data=None,
                        message="ticket_id required for update action",
                        metadata={}
                    )
                return self._update_ticket(ticket_id, status, resolution, **kwargs)
            elif action == "resolve":
                if not ticket_id:
                    return ToolResult(
                        success=False,
                        data=None,
                        message="ticket_id required for resolve action",
                        metadata={}
                    )
                return self._resolve_ticket(ticket_id, resolution)
            elif action == "escalate":
                if not ticket_id:
                    return ToolResult(
                        success=False,
                        data=None,
                        message="ticket_id required for escalate action",
                        metadata={}
                    )
                return self._escalate_ticket(ticket_id)
            elif action == "get":
                if not ticket_id:
                    return ToolResult(
                        success=False,
                        data=None,
                        message="ticket_id required for get action",
                        metadata={}
                    )
                return self._get_ticket(ticket_id)
            else:
                return ToolResult(
                    success=False,
                    data=None,
                    message=f"Unknown action: {action}. Use: create, update, resolve, escalate, get",
                    metadata={}
                )
        
        except Exception as e:
            return ToolResult(
                success=False,
                data=None,
                message=f"Ticket operation failed: {str(e)}",
                metadata={"error": str(e)}
            )
    
    def _create_ticket(
        self,
        customer_email: str,
        subject: str,
        description: str,
        priority: str = "medium"
    ) -> ToolResult:
        """Create a new support ticket."""
        self.ticket_counter += 1
        ticket_id = f"TICKET-{self.ticket_counter:06d}"
        
        ticket = {
            "ticket_id": ticket_id,
            "customer_email": customer_email,
            "subject": subject,
            "description": description,
            "priority": priority,
            "status": "open",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "resolved_at": None,
            "resolution": None,
            "escalated": False
        }
        
        self.tickets[ticket_id] = ticket
        
        return ToolResult(
            success=True,
            data=ticket,
            message=f"Ticket {ticket_id} created successfully",
            metadata={"ticket_id": ticket_id, "priority": priority}
        )
    
    def _update_ticket(
        self,
        ticket_id: str,
        status: Optional[str] = None,
        resolution: Optional[str] = None,
        **kwargs
    ) -> ToolResult:
        """Update an existing ticket."""
        if ticket_id not in self.tickets:
            return ToolResult(
                success=False,
                data=None,
                message=f"Ticket {ticket_id} not found",
                metadata={}
            )
        
        ticket = self.tickets[ticket_id]
        
        if status:
            ticket["status"] = status
        if resolution:
            ticket["resolution"] = resolution
        if kwargs:
            ticket.update(kwargs)
        
        ticket["updated_at"] = datetime.now().isoformat()
        
        return ToolResult(
            success=True,
            data=ticket,
            message=f"Ticket {ticket_id} updated successfully",
            metadata={"ticket_id": ticket_id}
        )
    
    def _resolve_ticket(self, ticket_id: str, resolution: Optional[str] = None) -> ToolResult:
        """Resolve a ticket."""
        if ticket_id not in self.tickets:
            return ToolResult(
                success=False,
                data=None,
                message=f"Ticket {ticket_id} not found",
                metadata={}
            )
        
        ticket = self.tickets[ticket_id]
        ticket["status"] = "resolved"
        ticket["resolved_at"] = datetime.now().isoformat()
        if resolution:
            ticket["resolution"] = resolution
        
        return ToolResult(
            success=True,
            data=ticket,
            message=f"Ticket {ticket_id} resolved successfully",
            metadata={"ticket_id": ticket_id}
        )
    
    def _escalate_ticket(self, ticket_id: str) -> ToolResult:
        """Escalate a ticket to human agent."""
        if ticket_id not in self.tickets:
            return ToolResult(
                success=False,
                data=None,
                message=f"Ticket {ticket_id} not found",
                metadata={}
            )
        
        ticket = self.tickets[ticket_id]
        ticket["escalated"] = True
        ticket["status"] = "escalated"
        ticket["updated_at"] = datetime.now().isoformat()
        
        return ToolResult(
            success=True,
            data=ticket,
            message=f"Ticket {ticket_id} escalated to human agent",
            metadata={"ticket_id": ticket_id, "escalated": True}
        )
    
    def _get_ticket(self, ticket_id: str) -> ToolResult:
        """Get ticket information."""
        if ticket_id not in self.tickets:
            return ToolResult(
                success=False,
                data=None,
                message=f"Ticket {ticket_id} not found",
                metadata={}
            )
        
        return ToolResult(
            success=True,
            data=self.tickets[ticket_id],
            message=f"Ticket {ticket_id} retrieved successfully",
            metadata={"ticket_id": ticket_id}
        )

