"""
Handoff Manager - Gestor de Handoff a Humanos.

Integra con Zendesk, WhatsApp, Email para transferir conversaciones a humanos.
Completamente configurable desde UI.
"""

from __future__ import annotations

import json
import os
from typing import Dict, Any, Optional
from enum import Enum


class HandoffProvider(str, Enum):
    """Proveedores de handoff disponibles."""
    ZENDESK = "zendesk"
    WHATSAPP = "whatsapp"
    EMAIL = "email"
    NONE = "none"


class HandoffTrigger(str, Enum):
    """Tipos de triggers para handoff."""
    MANUAL = "manual"  # Usuario lo pide explícitamente
    AUTO_LOW_CONFIDENCE = "auto_low_confidence"  # Confianza baja en respuesta
    AUTO_STRONG_OBJECTION = "auto_strong_objection"  # Objeción fuerte del cliente
    AUTO_FRUSTRATION = "auto_frustration"  # Frustración alta detectada


class HandoffManager:
    """
    Gestor de handoff a humanos.
    
    Características:
    - Soporta múltiples proveedores (Zendesk, WhatsApp, Email)
    - Triggers manuales y automáticos
    - Completamente configurable desde UI
    """
    
    def __init__(
        self,
        enabled: bool = False,
        provider: str = HandoffProvider.NONE.value,
        api_key: Optional[str] = None,
        api_token: Optional[str] = None,
        queue: Optional[str] = None,
        department: Optional[str] = None,
        email: Optional[str] = None,
        triggers: Optional[Dict[str, bool]] = None,
    ):
        """
        Inicializa el HandoffManager.
        
        Args:
            enabled: Si el handoff está habilitado
            provider: Proveedor (zendesk, whatsapp, email)
            api_key: API Key del proveedor
            api_token: API Token (para Zendesk)
            queue: Queue/Cola (para Zendesk)
            department: Departamento (para Zendesk)
            email: Email (para handoff por email)
            triggers: Dict con triggers habilitados {manual: True, auto_low_confidence: False, ...}
        """
        self.enabled = enabled
        self.provider = provider
        self.api_key = api_key
        self.api_token = api_token
        self.queue = queue
        self.department = department
        self.email = email
        self.triggers = triggers or {
            HandoffTrigger.MANUAL.value: True,
            HandoffTrigger.AUTO_LOW_CONFIDENCE.value: False,
            HandoffTrigger.AUTO_STRONG_OBJECTION.value: False,
            HandoffTrigger.AUTO_FRUSTRATION.value: False,
        }
        
        # Inicializar cliente del proveedor si está habilitado
        self._client = None
        if self.enabled and self.provider != HandoffProvider.NONE.value:
            self._init_provider_client()
    
    def _init_provider_client(self):
        """Inicializa el cliente del proveedor seleccionado."""
        if self.provider == HandoffProvider.ZENDESK.value:
            self._init_zendesk_client()
        elif self.provider == HandoffProvider.WHATSAPP.value:
            self._init_whatsapp_client()
        elif self.provider == HandoffProvider.EMAIL.value:
            # Email no requiere cliente especial
            pass
    
    def _init_zendesk_client(self):
        """Inicializa cliente de Zendesk."""
        try:
            # Zendesk requiere: subdomain, email, api_token
            # Por ahora solo validamos que existan credenciales
            if not self.api_key or not self.api_token:
                print("⚠️ Zendesk requiere api_key (subdomain) y api_token")
                return
            
            # En producción, aquí se inicializaría el cliente de Zendesk:
            # from zenpy import Zenpy
            # self._client = Zenpy(
            #     email=self.email,
            #     subdomain=self.api_key,  # subdomain
            #     token=self.api_token
            # )
            print(f"✅ Zendesk configurado (subdomain: {self.api_key}, queue: {self.queue})")
        except Exception as e:
            print(f"⚠️ Error inicializando Zendesk: {e}")
    
    def _init_whatsapp_client(self):
        """Inicializa cliente de WhatsApp para handoff."""
        try:
            # WhatsApp handoff usa la misma API de WhatsApp Business
            # Por ahora solo validamos que existan credenciales
            if not self.api_key:
                print("⚠️ WhatsApp handoff requiere api_key (access_token)")
                return
            
            print(f"✅ WhatsApp handoff configurado")
        except Exception as e:
            print(f"⚠️ Error inicializando WhatsApp handoff: {e}")
    
    def should_handoff(
        self,
        trigger: HandoffTrigger,
        confidence: Optional[float] = None,
        objection_strength: Optional[float] = None,
        frustration_score: Optional[float] = None,
    ) -> bool:
        """
        Determina si se debe hacer handoff según el trigger.
        
        Args:
            trigger: Tipo de trigger
            confidence: Nivel de confianza (0-1) para auto_low_confidence
            objection_strength: Fuerza de objeción (0-1) para auto_strong_objection
            frustration_score: Score de frustración (0-1) para auto_frustration
            
        Returns:
            True si se debe hacer handoff
        """
        if not self.enabled:
            return False
        
        trigger_key = trigger.value
        
        # Si el trigger no está habilitado, no hacer handoff
        if not self.triggers.get(trigger_key, False):
            return False
        
        # Validaciones específicas por trigger
        if trigger == HandoffTrigger.AUTO_LOW_CONFIDENCE:
            if confidence is not None and confidence < 0.5:  # Confianza < 50%
                return True
        
        if trigger == HandoffTrigger.AUTO_STRONG_OBJECTION:
            if objection_strength is not None and objection_strength > 0.7:  # Objeción > 70%
                return True
        
        if trigger == HandoffTrigger.AUTO_FRUSTRATION:
            if frustration_score is not None and frustration_score > 0.7:  # Frustración > 70%
                return True
        
        # Manual siempre retorna True si está habilitado
        if trigger == HandoffTrigger.MANUAL:
            return True
        
        return False
    
    def create_ticket(
        self,
        session_id: str,
        user_id: str,
        user_message: str,
        conversation_history: Optional[str] = None,
        priority: str = "normal",
    ) -> Dict[str, Any]:
        """
        Crea un ticket/caso para handoff.
        
        Args:
            session_id: ID de sesión
            user_id: ID del usuario
            user_message: Último mensaje del usuario
            conversation_history: Historial de conversación (opcional)
            priority: Prioridad (low, normal, high, urgent)
            
        Returns:
            Dict con resultado: {success: bool, ticket_id: str, message: str}
        """
        if not self.enabled:
            return {
                "success": False,
                "message": "Handoff no está habilitado",
            }
        
        if self.provider == HandoffProvider.NONE.value:
            return {
                "success": False,
                "message": "No hay proveedor de handoff configurado",
            }
        
        try:
            if self.provider == HandoffProvider.ZENDESK.value:
                return self._create_zendesk_ticket(
                    session_id, user_id, user_message, conversation_history, priority
                )
            elif self.provider == HandoffProvider.WHATSAPP.value:
                return self._create_whatsapp_handoff(
                    session_id, user_id, user_message, conversation_history
                )
            elif self.provider == HandoffProvider.EMAIL.value:
                return self._create_email_handoff(
                    session_id, user_id, user_message, conversation_history
                )
        except Exception as e:
            return {
                "success": False,
                "message": f"Error creando handoff: {e}",
            }
        
        return {
            "success": False,
            "message": f"Proveedor {self.provider} no soportado",
        }
    
    def _create_zendesk_ticket(
        self,
        session_id: str,
        user_id: str,
        user_message: str,
        conversation_history: Optional[str],
        priority: str,
    ) -> Dict[str, Any]:
        """Crea ticket en Zendesk."""
        try:
            # En producción, aquí se usaría el cliente de Zendesk:
            # ticket = self._client.tickets.create(
            #     Ticket(
            #         subject=f"Handoff desde STAR AGENT - Sesión {session_id}",
            #         description=f"Usuario: {user_id}\n\nMensaje: {user_message}\n\nHistorial:\n{conversation_history or 'N/A'}",
            #         priority=priority,
            #         type="question",
            #         requester={"email": user_id if "@" in user_id else f"{user_id}@example.com"},
            #         tags=["star_agent", "handoff", session_id],
            #     )
            # )
            # return {"success": True, "ticket_id": str(ticket.id), "message": f"Ticket creado: {ticket.id}"}
            
            # Por ahora retornamos simulación
            ticket_id = f"ZD-{session_id[:8]}"
            print(f"✅ Ticket Zendesk creado (simulado): {ticket_id}")
            return {
                "success": True,
                "ticket_id": ticket_id,
                "message": f"Te hemos conectado con un agente humano. Ticket: {ticket_id}",
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Error creando ticket Zendesk: {e}",
            }
    
    def _create_whatsapp_handoff(
        self,
        session_id: str,
        user_id: str,
        user_message: str,
        conversation_history: Optional[str],
    ) -> Dict[str, Any]:
        """Crea handoff vía WhatsApp."""
        try:
            # En producción, aquí se transferiría la conversación a un agente humano vía WhatsApp Business API
            # Por ahora retornamos simulación
            print(f"✅ Handoff WhatsApp iniciado (simulado) para sesión {session_id}")
            return {
                "success": True,
                "ticket_id": f"WA-{session_id[:8]}",
                "message": "Te estamos conectando con un agente humano por WhatsApp. Recibirás un mensaje pronto.",
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Error creando handoff WhatsApp: {e}",
            }
    
    def _create_email_handoff(
        self,
        session_id: str,
        user_id: str,
        user_message: str,
        conversation_history: Optional[str],
    ) -> Dict[str, Any]:
        """Crea handoff vía Email."""
        try:
            if not self.email:
                return {
                    "success": False,
                    "message": "Email de handoff no configurado",
                }
            
            # En producción, aquí se enviaría un email:
            # import smtplib
            # from email.mime.text import MIMEText
            # msg = MIMEText(f"Usuario: {user_id}\n\nMensaje: {user_message}\n\nHistorial:\n{conversation_history or 'N/A'}")
            # msg['Subject'] = f"Handoff STAR AGENT - Sesión {session_id}"
            # msg['From'] = "star_agent@example.com"
            # msg['To'] = self.email
            # smtp.sendmail(...)
            
            print(f"✅ Handoff Email enviado (simulado) a {self.email}")
            return {
                "success": True,
                "ticket_id": f"EM-{session_id[:8]}",
                "message": f"Tu consulta ha sido enviada a nuestro equipo. Te contactaremos pronto a {user_id if '@' in user_id else 'tu email'}.",
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Error creando handoff Email: {e}",
            }
    
    def update_config(self, config: Dict[str, Any]):
        """
        Actualiza configuración desde dict.
        
        Args:
            config: Dict con configuración de handoff
        """
        self.enabled = config.get("handoff_enabled", False)
        self.provider = config.get("handoff_provider", HandoffProvider.NONE.value)
        self.api_key = config.get("handoff_api_key")
        self.api_token = config.get("handoff_api_token")
        self.queue = config.get("handoff_queue")
        self.department = config.get("handoff_department")
        self.email = config.get("handoff_email")
        self.triggers = config.get("handoff_triggers", {
            HandoffTrigger.MANUAL.value: True,
            HandoffTrigger.AUTO_LOW_CONFIDENCE.value: False,
            HandoffTrigger.AUTO_STRONG_OBJECTION.value: False,
            HandoffTrigger.AUTO_FRUSTRATION.value: False,
        })
        
        # Reinicializar cliente si está habilitado
        if self.enabled and self.provider != HandoffProvider.NONE.value:
            self._init_provider_client()

