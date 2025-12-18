from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, Any, List, Optional


class SentimentLabel(str, Enum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"
    CRITICAL = "critical"


@dataclass
class CustomerProfile:
    user_id: str
    channel: str  # web, whatsapp, instagram, messenger, etc.
    display_name: Optional[str] = None
    language: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CustomerSessionState:
    """Estado unificado por sesión/cliente.

    Centraliza toda la información necesaria para ventas + soporte:
    - Perfil del cliente
    - Carrito actual
    - Pedidos recientes
    - Tickets abiertos
    - Historial de mensajes breves
    - Sentimiento / frustración acumulada
    """

    session_id: str
    profile: CustomerProfile
    cart: Dict[str, Any] = field(default_factory=dict)
    recent_orders: List[Dict[str, Any]] = field(default_factory=list)
    open_tickets: List[Dict[str, Any]] = field(default_factory=list)
    last_messages: List[Dict[str, Any]] = field(default_factory=list)
    sentiment: SentimentLabel = SentimentLabel.NEUTRAL
    frustration_score: float = 0.0
    needs_handoff: bool = False
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def add_message(self, role: str, content: str) -> None:
        self.last_messages.append({
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat(),
        })
        # Mantener solo las últimas N interacciones breves
        if len(self.last_messages) > 20:
            self.last_messages = self.last_messages[-20:]
        self.updated_at = datetime.utcnow().isoformat()


class CustomerSessionManager:
    """Gestor simple en memoria de sesiones de cliente.

    En producción, esto se puede extender a Redis, DB, etc.
    """

    def __init__(self) -> None:
        self._sessions: Dict[str, CustomerSessionState] = {}

    def get_or_create(self, session_id: str, profile: CustomerProfile) -> CustomerSessionState:
        if session_id not in self._sessions:
            self._sessions[session_id] = CustomerSessionState(session_id=session_id, profile=profile)
        return self._sessions[session_id]

    def update(self, session: CustomerSessionState) -> None:
        self._sessions[session.session_id] = session

    def get(self, session_id: str) -> Optional[CustomerSessionState]:
        return self._sessions.get(session_id)

    def clear(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)

