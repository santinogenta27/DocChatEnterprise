from __future__ import annotations

from typing import Dict, Any, List


class SupportTool:
    """Wrapper de soporte/tickets.

    En esta versión se deja una implementación mínima en memoria,
    pero está pensada para conectar con `customer_service_24_7`
    o `customer_support` vía API interna o llamadas directas.
    """

    def __init__(self) -> None:
        self._tickets: Dict[str, Dict[str, Any]] = {}

    def create_ticket(self, session_id: str, subject: str, description: str, priority: str = "normal") -> Dict[str, Any]:
        ticket_id = f"ticket_{len(self._tickets) + 1}"
        ticket = {
            "ticket_id": ticket_id,
            "session_id": session_id,
            "subject": subject,
            "description": description,
            "priority": priority,
            "status": "open",
        }
        self._tickets[ticket_id] = ticket
        return ticket

    def update_ticket_status(self, ticket_id: str, status: str) -> Dict[str, Any] | None:
        ticket = self._tickets.get(ticket_id)
        if not ticket:
            return None
        ticket["status"] = status
        return ticket

    def list_tickets_for_session(self, session_id: str) -> List[Dict[str, Any]]:
        return [t for t in self._tickets.values() if t.get("session_id") == session_id]



