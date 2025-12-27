"""Integración con Zendesk para gestión de tickets y casos.

El agent piensa en CASOS, no en tickets.
Un caso es: un problema, un contexto, un objetivo, una resolución.
"""

from __future__ import annotations

import os
import json
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False


class TicketStatus(str, Enum):
    """Estados de ticket en Zendesk."""
    NEW = "new"
    OPEN = "open"
    PENDING = "pending"
    HOLD = "hold"
    SOLVED = "solved"
    CLOSED = "closed"


@dataclass
class ZendeskTicket:
    """Representación de un ticket de Zendesk."""
    id: int
    subject: str
    description: str
    status: str
    priority: Optional[str] = None
    requester_id: Optional[int] = None
    requester_email: Optional[str] = None
    requester_name: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    comments: List[Dict[str, Any]] = field(default_factory=list)
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    custom_fields: Dict[str, Any] = field(default_factory=dict)
    
    def is_open(self) -> bool:
        """Verifica si el ticket está abierto."""
        return self.status in [TicketStatus.NEW.value, TicketStatus.OPEN.value, TicketStatus.PENDING.value]
    
    def is_solved(self) -> bool:
        """Verifica si el ticket está resuelto."""
        return self.status in [TicketStatus.SOLVED.value, TicketStatus.CLOSED.value]


class ZendeskIntegration:
    """Integración con Zendesk API.
    
    Permite:
    - Leer: ticket, requester, historial, estado, prioridad, tags
    - Escribir: respuestas públicas, notas internas, tags, cambiar estado
    """
    
    def __init__(
        self,
        subdomain: Optional[str] = None,
        email: Optional[str] = None,
        api_token: Optional[str] = None,
    ):
        """Inicializa la integración con Zendesk.
        
        Args:
            subdomain: Subdominio de Zendesk (ej: "miempresa" para miempresa.zendesk.com)
            email: Email del agente de Zendesk
            api_token: API token de Zendesk
        """
        self.subdomain = subdomain or os.getenv("ZENDESK_SUBDOMAIN")
        self.email = email or os.getenv("ZENDESK_EMAIL")
        self.api_token = api_token or os.getenv("ZENDESK_API_TOKEN")
        
        if not all([self.subdomain, self.email, self.api_token]):
            self.enabled = False
            print("⚠️ Zendesk no configurado. Configura ZENDESK_SUBDOMAIN, ZENDESK_EMAIL y ZENDESK_API_TOKEN en .env")
        else:
            self.enabled = True
            self.base_url = f"https://{self.subdomain}.zendesk.com/api/v2"
            self.auth = (f"{self.email}/token", self.api_token)
            print(f"✅ Zendesk habilitado para {self.subdomain}")
    
    def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Optional[Dict]:
        """Hace una petición a la API de Zendesk."""
        if not self.enabled:
            return None
        
        if not REQUESTS_AVAILABLE:
            print("⚠️ requests no está instalado. Instala con: pip install requests")
            return None
        
        url = f"{self.base_url}/{endpoint}"
        
        try:
            if method.upper() == "GET":
                response = requests.get(url, auth=self.auth, timeout=10)
            elif method.upper() == "POST":
                response = requests.post(url, auth=self.auth, json=data, timeout=10)
            elif method.upper() == "PUT":
                response = requests.put(url, auth=self.auth, json=data, timeout=10)
            else:
                return None
            
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"⚠️ Error en petición Zendesk: {e}")
            return None
    
    def get_ticket(self, ticket_id: int) -> Optional[ZendeskTicket]:
        """Obtiene un ticket por ID."""
        result = self._make_request("GET", f"tickets/{ticket_id}.json")
        if not result or "ticket" not in result:
            return None
        
        ticket_data = result["ticket"]
        return self._parse_ticket(ticket_data)
    
    def get_ticket_comments(self, ticket_id: int) -> List[Dict[str, Any]]:
        """Obtiene los comentarios de un ticket."""
        result = self._make_request("GET", f"tickets/{ticket_id}/comments.json")
        if not result or "comments" not in result:
            return []
        
        return result["comments"]
    
    def create_ticket(
        self,
        subject: str,
        description: str,
        requester_email: str,
        requester_name: Optional[str] = None,
        tags: Optional[List[str]] = None,
        priority: Optional[str] = None,
    ) -> Optional[ZendeskTicket]:
        """Crea un nuevo ticket."""
        ticket_data = {
            "ticket": {
                "subject": subject,
                "comment": {
                    "body": description
                },
                "requester": {
                    "email": requester_email,
                    "name": requester_name or requester_email
                }
            }
        }
        
        if tags:
            ticket_data["ticket"]["tags"] = tags
        if priority:
            ticket_data["ticket"]["priority"] = priority
        
        result = self._make_request("POST", "tickets.json", ticket_data)
        if not result or "ticket" not in result:
            return None
        
        return self._parse_ticket(result["ticket"])
    
    def add_public_comment(self, ticket_id: int, comment: str) -> bool:
        """Agrega un comentario público al ticket."""
        data = {
            "ticket": {
                "comment": {
                    "body": comment,
                    "public": True
                }
            }
        }
        
        result = self._make_request("PUT", f"tickets/{ticket_id}.json", data)
        return result is not None
    
    def add_internal_note(self, ticket_id: int, note: str) -> bool:
        """Agrega una nota interna al ticket."""
        data = {
            "ticket": {
                "comment": {
                    "body": note,
                    "public": False
                }
            }
        }
        
        result = self._make_request("PUT", f"tickets/{ticket_id}.json", data)
        return result is not None
    
    def update_ticket_status(self, ticket_id: int, status: str) -> bool:
        """Actualiza el estado de un ticket."""
        data = {
            "ticket": {
                "status": status
            }
        }
        
        result = self._make_request("PUT", f"tickets/{ticket_id}.json", data)
        return result is not None
    
    def add_tags(self, ticket_id: int, tags: List[str]) -> bool:
        """Agrega tags a un ticket."""
        ticket = self.get_ticket(ticket_id)
        if not ticket:
            return False
        
        existing_tags = set(ticket.tags)
        new_tags = existing_tags.union(set(tags))
        
        data = {
            "ticket": {
                "tags": list(new_tags)
            }
        }
        
        result = self._make_request("PUT", f"tickets/{ticket_id}.json", data)
        return result is not None
    
    def remove_tags(self, ticket_id: int, tags: List[str]) -> bool:
        """Elimina tags de un ticket."""
        ticket = self.get_ticket(ticket_id)
        if not ticket:
            return False
        
        existing_tags = set(ticket.tags)
        remaining_tags = existing_tags - set(tags)
        
        data = {
            "ticket": {
                "tags": list(remaining_tags)
            }
        }
        
        result = self._make_request("PUT", f"tickets/{ticket_id}.json", data)
        return result is not None
    
    def _parse_ticket(self, ticket_data: Dict[str, Any]) -> ZendeskTicket:
        """Parsea los datos de un ticket de la API."""
        return ZendeskTicket(
            id=ticket_data.get("id", 0),
            subject=ticket_data.get("subject", ""),
            description=ticket_data.get("description", ""),
            status=ticket_data.get("status", "new"),
            priority=ticket_data.get("priority"),
            requester_id=ticket_data.get("requester_id"),
            requester_email=ticket_data.get("via", {}).get("source", {}).get("from", {}).get("address"),
            tags=ticket_data.get("tags", []),
            created_at=ticket_data.get("created_at"),
            updated_at=ticket_data.get("updated_at"),
            custom_fields=ticket_data.get("custom_fields", {}),
        )

