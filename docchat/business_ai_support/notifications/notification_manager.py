"""Notification Manager - Orchestrates email and Slack notifications."""

from __future__ import annotations

from typing import Dict, Any, Optional, List
from .email_notifier import EmailNotifier
from .slack_notifier import SlackNotifier


class NotificationManager:
    """Manages notifications to humans via email and Slack."""
    
    def __init__(
        self,
        email_enabled: bool = True,
        slack_enabled: bool = True,
        email_config: Optional[Dict[str, Any]] = None,
        slack_config: Optional[Dict[str, Any]] = None
    ):
        """Initialize NotificationManager.
        
        Args:
            email_enabled: Enable email notifications
            slack_enabled: Enable Slack notifications
            email_config: Email configuration (smtp_server, smtp_port, smtp_user, smtp_password, from_email, to_emails)
            slack_config: Slack configuration (webhook_url)
        """
        self.email_enabled = email_enabled
        self.slack_enabled = slack_enabled
        
        self.email_notifier = None
        if email_enabled:
            self.email_notifier = EmailNotifier(
                config=email_config or {}
            )
        
        self.slack_notifier = None
        if slack_enabled:
            self.slack_notifier = SlackNotifier(
                config=slack_config or {}
            )
    
    def notify_escalation(
        self,
        ticket_id: str,
        summary: Dict[str, Any],
        priority: str = "normal"
    ) -> Dict[str, Any]:
        """Notify humans about escalated ticket.
        
        Args:
            ticket_id: Ticket ID
            summary: Structured summary (issue, sentiment, actions_taken, pending_actions, urgency)
            priority: Priority level (normal, medium, high)
            
        Returns:
            Dict with notification results
        """
        results = {
            "ticket_id": ticket_id,
            "email_sent": False,
            "slack_sent": False,
            "errors": []
        }
        
        # Format message
        subject = f"🚨 Ticket Escalado: {ticket_id} ({priority.upper()})"
        
        message = self._format_escalation_message(ticket_id, summary, priority)
        
        # Send email
        if self.email_enabled and self.email_notifier:
            try:
                self.email_notifier.send(
                    subject=subject,
                    body=message,
                    priority=priority
                )
                results["email_sent"] = True
            except Exception as e:
                results["errors"].append(f"Email error: {str(e)}")
        
        # Send Slack
        if self.slack_enabled and self.slack_notifier:
            try:
                self.slack_notifier.send(
                    text=subject,
                    blocks=self._format_slack_blocks(ticket_id, summary, priority)
                )
                results["slack_sent"] = True
            except Exception as e:
                results["errors"].append(f"Slack error: {str(e)}")
        
        return results
    
    def notify_appointment_confirmation(
        self,
        appointment_id: str,
        customer_email: str,
        appointment_details: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Send appointment confirmation email.
        
        Args:
            appointment_id: Appointment ID
            customer_email: Customer email
            appointment_details: Appointment details (date, time, subject, etc.)
            
        Returns:
            Dict with notification results
        """
        results = {
            "appointment_id": appointment_id,
            "email_sent": False,
            "errors": []
        }
        
        if self.email_enabled and self.email_notifier:
            try:
                subject = f"✅ Confirmación de Cita: {appointment_details.get('subject', 'Cita Programada')}"
                body = self._format_appointment_confirmation(appointment_details)
                
                self.email_notifier.send_to(
                    to_email=customer_email,
                    subject=subject,
                    body=body
                )
                results["email_sent"] = True
            except Exception as e:
                results["errors"].append(f"Email error: {str(e)}")
        
        return results
    
    def notify_new_ticket(
        self,
        ticket_id: str,
        ticket_subject: str,
        priority: str = "normal"
    ) -> Dict[str, Any]:
        """Notify about new ticket (for urgent tickets).
        
        Args:
            ticket_id: Ticket ID
            ticket_subject: Ticket subject
            priority: Priority level
            
        Returns:
            Dict with notification results
        """
        # Only notify for high priority tickets
        if priority != "high":
            return {"notified": False, "reason": "Priority not high enough"}
        
        results = {
            "ticket_id": ticket_id,
            "email_sent": False,
            "slack_sent": False,
            "errors": []
        }
        
        subject = f"🎫 Nuevo Ticket Urgente: {ticket_id}"
        message = f"**Ticket ID:** {ticket_id}\n**Asunto:** {ticket_subject}\n**Prioridad:** {priority.upper()}"
        
        # Send email
        if self.email_enabled and self.email_notifier:
            try:
                self.email_notifier.send(
                    subject=subject,
                    body=message,
                    priority="high"
                )
                results["email_sent"] = True
            except Exception as e:
                results["errors"].append(f"Email error: {str(e)}")
        
        # Send Slack
        if self.slack_enabled and self.slack_notifier:
            try:
                self.slack_notifier.send(
                    text=subject,
                    blocks=[
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": f"*Ticket ID:* {ticket_id}\n*Asunto:* {ticket_subject}\n*Prioridad:* {priority.upper()}"
                            }
                        }
                    ]
                )
                results["slack_sent"] = True
            except Exception as e:
                results["errors"].append(f"Slack error: {str(e)}")
        
        return results
    
    def _format_escalation_message(
        self,
        ticket_id: str,
        summary: Dict[str, Any],
        priority: str
    ) -> str:
        """Format escalation message for email."""
        message = f"""
🚨 **TICKET ESCALADO A HUMANO**

**Ticket ID:** {ticket_id}
**Prioridad:** {priority.upper()}

---

## 📋 RESUMEN DEL CASO

**Problema/Consulta:**
{summary.get('issue', 'No especificado')}

**Sentimiento del Cliente:**
{summary.get('sentiment', 'No detectado')}

**Urgencia:**
{summary.get('urgency', 'Media')}

---

## ✅ ACCIONES TOMADAS

{self._format_list(summary.get('actions_taken', []))}

---

## ⏳ ACCIONES PENDIENTES

{self._format_list(summary.get('pending_actions', []))}

---

## 📊 CONTEXTO ADICIONAL

{summary.get('additional_context', 'N/A')}

---

**⚠️ Este ticket requiere atención humana inmediata.**
"""
        return message.strip()
    
    def _format_slack_blocks(
        self,
        ticket_id: str,
        summary: Dict[str, Any],
        priority: str
    ) -> List[Dict[str, Any]]:
        """Format Slack blocks for escalation notification."""
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"🚨 Ticket Escalado: {ticket_id}"
                }
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Prioridad:*\n{priority.upper()}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Urgencia:*\n{summary.get('urgency', 'Media')}"
                    }
                ]
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Problema/Consulta:*\n{summary.get('issue', 'No especificado')}"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Sentimiento:*\n{summary.get('sentiment', 'No detectado')}"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Acciones Tomadas:*\n{self._format_list_markdown(summary.get('actions_taken', []))}"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Acciones Pendientes:*\n{self._format_list_markdown(summary.get('pending_actions', []))}"
                }
            }
        ]
        
        if summary.get('additional_context'):
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Contexto Adicional:*\n{summary.get('additional_context')}"
                }
            })
        
        return blocks
    
    def _format_appointment_confirmation(self, details: Dict[str, Any]) -> str:
        """Format appointment confirmation email."""
        message = f"""
✅ **CITA CONFIRMADA**

Estimado/a cliente,

Su cita ha sido confirmada exitosamente.

**Detalles de la Cita:**

- **Asunto:** {details.get('subject', 'Cita Programada')}
- **Fecha:** {details.get('date', 'N/A')}
- **Hora:** {details.get('time', 'N/A')}
- **Duración:** {details.get('duration', '30 minutos')}

{details.get('notes', '')}

Si necesita modificar o cancelar esta cita, por favor contacte con nosotros.

¡Esperamos poder ayudarle!

Atentamente,
Equipo de Soporte
"""
        return message.strip()
    
    def _format_list(self, items: List[str]) -> str:
        """Format list for plain text."""
        if not items:
            return "- Ninguna"
        return "\n".join(f"- {item}" for item in items)
    
    def _format_list_markdown(self, items: List[str]) -> str:
        """Format list for Markdown/Slack."""
        if not items:
            return "• Ninguna"
        return "\n".join(f"• {item}" for item in items)

