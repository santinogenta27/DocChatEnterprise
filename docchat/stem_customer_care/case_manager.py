"""Gestor de Casos para Customer Service.

El agent piensa en CASOS, no en tickets.
Un caso es: un problema, un contexto, un objetivo, una resolución.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum


class CaseStatus(str, Enum):
    """Estados de un caso."""
    OPEN = "open"
    INVESTIGATING = "investigating"
    PENDING = "pending"
    RESOLVED = "resolved"
    ESCALATED = "escalated"
    CLOSED = "closed"


class CasePriority(str, Enum):
    """Prioridades de un caso."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


@dataclass
class Case:
    """Representación de un caso de customer service."""
    case_id: str
    subject: str
    description: str
    requester_email: str
    requester_name: Optional[str] = None
    status: CaseStatus = CaseStatus.OPEN
    priority: CasePriority = CasePriority.MEDIUM
    tags: List[str] = field(default_factory=list)
    messages: List[Dict[str, Any]] = field(default_factory=list)
    actions_taken: List[Dict[str, Any]] = field(default_factory=list)
    zendesk_ticket_id: Optional[int] = None
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    resolved_at: Optional[str] = None
    escalation_reason: Optional[str] = None
    
    def add_message(self, role: str, content: str, metadata: Optional[Dict] = None):
        """Agrega un mensaje al caso."""
        self.messages.append({
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": metadata or {}
        })
        self.updated_at = datetime.utcnow().isoformat()
    
    def add_action(self, action_type: str, description: str, result: Optional[str] = None):
        """Registra una acción tomada en el caso."""
        self.actions_taken.append({
            "action_type": action_type,
            "description": description,
            "result": result,
            "timestamp": datetime.utcnow().isoformat()
        })
        self.updated_at = datetime.utcnow().isoformat()
    
    def update_status(self, new_status: CaseStatus, reason: Optional[str] = None):
        """Actualiza el estado del caso."""
        self.status = new_status
        self.updated_at = datetime.utcnow().isoformat()
        
        if new_status == CaseStatus.RESOLVED:
            self.resolved_at = datetime.utcnow().isoformat()
        
        if reason:
            self.add_action("status_change", f"Estado cambiado a {new_status.value}", reason)
    
    def escalate(self, reason: str):
        """Escala el caso."""
        self.status = CaseStatus.ESCALATED
        self.escalation_reason = reason
        self.updated_at = datetime.utcnow().isoformat()
        self.add_action("escalation", f"Caso escalado: {reason}")


class CaseManager:
    """Gestor de casos de customer service."""
    
    def __init__(self):
        self.cases: Dict[str, Case] = {}
    
    def create_case(
        self,
        subject: str,
        description: str,
        requester_email: str,
        requester_name: Optional[str] = None,
        priority: CasePriority = CasePriority.MEDIUM,
    ) -> Case:
        """Crea un nuevo caso."""
        case_id = f"case_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{len(self.cases)}"
        
        case = Case(
            case_id=case_id,
            subject=subject,
            description=description,
            requester_email=requester_email,
            requester_name=requester_name,
            priority=priority,
        )
        
        case.add_message("system", f"Caso creado: {subject}")
        self.cases[case_id] = case
        
        return case
    
    def get_case(self, case_id: str) -> Optional[Case]:
        """Obtiene un caso por ID."""
        return self.cases.get(case_id)
    
    def get_case_by_email(self, email: str) -> Optional[Case]:
        """Obtiene el caso activo más reciente para un email."""
        active_cases = [
            case for case in self.cases.values()
            if case.requester_email == email
            and case.status not in [CaseStatus.RESOLVED, CaseStatus.CLOSED]
        ]
        
        if not active_cases:
            return None
        
        # Retornar el más reciente
        return max(active_cases, key=lambda c: c.updated_at)
    
    def get_all_cases(self, status: Optional[CaseStatus] = None) -> List[Case]:
        """Obtiene todos los casos, opcionalmente filtrados por estado."""
        if status:
            return [case for case in self.cases.values() if case.status == status]
        return list(self.cases.values())

