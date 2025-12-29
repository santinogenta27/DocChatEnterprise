from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any

from ..state.customer_session import CustomerProfile


@dataclass
class ChannelMessage:
    """Mensaje normalizado desde cualquier canal."""
    session_id: str
    channel: str  # web, whatsapp, instagram, messenger
    user_id: str
    content: str
    metadata: Dict[str, Any]


class BaseChannelAdapter:
    """Adaptador base para canales (web, WhatsApp, IG, Messenger).

    Su responsabilidad es traducir mensajes externos al formato
    interno `ChannelMessage` y viceversa.
    """

    channel_name: str = "base"

    def to_internal(self, raw_payload: Dict[str, Any]) -> ChannelMessage:
        raise NotImplementedError

    def to_profile(self, msg: ChannelMessage) -> CustomerProfile:
        return CustomerProfile(
            user_id=msg.user_id,
            channel=msg.channel,
            display_name=msg.metadata.get("display_name"),
            language=msg.metadata.get("language"),
            metadata=msg.metadata,
        )

    def to_external_response(self, response_text: str, extra: Dict[str, Any] | None = None) -> Dict[str, Any]:
        payload = {"text": response_text}
        if extra:
            payload.update(extra)
        
        # Asegurar que 'tools' esté disponible si viene en extra
        if extra and "tools" in extra:
            payload["tools"] = extra["tools"]
        
        return payload

