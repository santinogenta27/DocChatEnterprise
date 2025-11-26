"""
Advanced Email Tool con todas las funcionalidades de Agentic AI para emails.
Incluye: personalización, campañas, lead nurturing, soporte al cliente, etc.
"""

from __future__ import annotations

import smtplib
import json
import csv
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from typing import Any, Dict, List, Optional
import os
import re

from .base_tool import BaseTool, ToolResult


class AdvancedEmailTool(BaseTool):
    """
    Herramienta avanzada de emails con todas las funcionalidades:
    - Personalización avanzada
    - Campañas automatizadas
    - Lead nurturing
    - Seguimiento de emails
    - Soporte al cliente
    - FAQ handling
    - A/B testing
    """
    
    def __init__(self, config: Any):
        super().__init__(config)
        self.smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_user = os.getenv("SMTP_USER", "")
        self.smtp_password = os.getenv("SMTP_PASSWORD", "")
        
        # Directorios para almacenar datos (sin SQL, solo archivos)
        self.data_dir = Path(config.memory_dir) / "email_data"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Archivos de datos (JSON/CSV)
        self.leads_file = self.data_dir / "leads.json"
        self.campaigns_file = self.data_dir / "campaigns.json"
        self.email_tracking_file = self.data_dir / "email_tracking.json"
        self.faq_file = self.data_dir / "faq.json"
        self.support_tickets_file = self.data_dir / "support_tickets.json"
        
        # Inicializar archivos si no existen
        self._initialize_data_files()
    
    def _initialize_data_files(self):
        """Inicializa archivos de datos si no existen."""
        if not self.leads_file.exists():
            self._save_json(self.leads_file, [])
        if not self.campaigns_file.exists():
            self._save_json(self.campaigns_file, {})
        if not self.email_tracking_file.exists():
            self._save_json(self.email_tracking_file, [])
        if not self.faq_file.exists():
            self._save_json(self.faq_file, [])
        if not self.support_tickets_file.exists():
            self._save_json(self.support_tickets_file, [])
    
    def _load_json(self, file_path: Path) -> Any:
        """Carga datos desde JSON."""
        try:
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return []
        except Exception:
            return []
    
    def _save_json(self, file_path: Path, data: Any):
        """Guarda datos en JSON."""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error guardando {file_path}: {e}")
    
    def get_name(self) -> str:
        return "advanced_email"
    
    def get_description(self) -> str:
        return """Advanced email tool with:
        - Personalized sales outreach
        - Automated marketing campaigns
        - Lead nurturing with follow-ups
        - Customer support automation
        - FAQ handling
        - Email tracking and analytics
        - A/B testing
        - High-volume outreach"""
    
    def get_keywords(self) -> List[str]:
        return [
            "email", "correo", "enviar", "mail", "campaña", "campaign",
            "lead", "nurturing", "soporte", "support", "faq", "outreach",
            "marketing", "ventas", "sales"
        ]
    
    def can_handle(self, task_description: str) -> bool:
        """Verifica si puede manejar la tarea."""
        task_lower = task_description.lower()
        keywords = self.get_keywords()
        return any(keyword in task_lower for keyword in keywords)
    
    def execute(
        self,
        to: str | List[str],
        subject: str,
        body: str,
        html_body: Optional[str] = None,
        attachments: Optional[List[str]] = None,
        # Funcionalidades avanzadas
        campaign_name: Optional[str] = None,
        personalize: bool = False,
        lead_data: Optional[Dict[str, Any]] = None,
        follow_up_days: Optional[int] = None,
        support_ticket_id: Optional[str] = None,
        faq_category: Optional[str] = None,
        ab_test_variant: Optional[str] = None,
        **kwargs
    ) -> ToolResult:
        """
        Envía email con funcionalidades avanzadas.
        
        Args:
            to: Destinatario(s)
            subject: Asunto
            body: Cuerpo del mensaje
            html_body: Cuerpo HTML opcional
            campaign_name: Nombre de campaña (para tracking)
            personalize: Si True, personaliza usando lead_data
            lead_data: Datos del lead para personalización
            follow_up_days: Días para follow-up automático
            support_ticket_id: ID de ticket de soporte
            faq_category: Categoría FAQ para respuesta automática
            ab_test_variant: Variante para A/B testing
        """
        try:
            # Validar credenciales
            if not self.smtp_user or not self.smtp_password:
                return ToolResult(
                    success=False,
                    data=None,
                    message="SMTP credentials not configured",
                    metadata={}
                )
            
            if not to:
                return ToolResult(
                    success=False,
                    data=None,
                    message="Recipient email address required",
                    metadata={}
                )
            
            # Convertir a lista
            if isinstance(to, str):
                recipients = [to]
            else:
                recipients = to
            
            # Personalizar emails si se solicita
            if personalize and lead_data:
                subject, body = self._personalize_email(subject, body, lead_data)
            
            # Procesar FAQ si es soporte al cliente
            if faq_category:
                body = self._handle_faq_response(faq_category, body)
            
            # Enviar emails
            sent_count = 0
            failed_recipients = []
            
            for recipient in recipients:
                try:
                    # Personalizar por destinatario si hay datos
                    final_subject = subject
                    final_body = body
                    
                    if personalize:
                        # Buscar datos del lead
                        lead_info = self._get_lead_info(recipient)
                        if lead_info:
                            final_subject, final_body = self._personalize_email(
                                subject, body, lead_info
                            )
                    
                    # Crear mensaje
                    msg = MIMEMultipart('alternative')
                    msg['Subject'] = final_subject
                    msg['From'] = self.smtp_user
                    msg['To'] = recipient
                    
                    # Agregar cuerpo
                    if html_body:
                        part1 = MIMEText(final_body, 'plain')
                        part2 = MIMEText(html_body, 'html')
                        msg.attach(part1)
                        msg.attach(part2)
                    else:
                        msg.attach(MIMEText(final_body, 'plain'))
                    
                    # Enviar
                    with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                        server.starttls()
                        server.login(self.smtp_user, self.smtp_password)
                        server.send_message(msg, to_addrs=[recipient])
                    
                    sent_count += 1
                    
                    # Registrar tracking
                    self._track_email(
                        recipient=recipient,
                        subject=final_subject,
                        campaign_name=campaign_name,
                        ab_test_variant=ab_test_variant,
                        support_ticket_id=support_ticket_id
                    )
                    
                    # Programar follow-up si se especifica
                    if follow_up_days:
                        self._schedule_follow_up(
                            recipient=recipient,
                            days=follow_up_days,
                            campaign_name=campaign_name
                        )
                    
                    # Actualizar lead si existe
                    if personalize:
                        self._update_lead_engagement(recipient, "email_sent")
                    
                except Exception as e:
                    failed_recipients.append({"email": recipient, "error": str(e)})
            
            # Actualizar campaña si existe
            if campaign_name:
                self._update_campaign_stats(campaign_name, sent_count, len(recipients))
            
            return ToolResult(
                success=sent_count > 0,
                data={
                    "sent_to": sent_count,
                    "total_recipients": len(recipients),
                    "failed": failed_recipients,
                    "campaign": campaign_name
                },
                message=f"Email sent successfully to {sent_count}/{len(recipients)} recipient(s)",
                metadata={
                    "smtp_server": self.smtp_server,
                    "personalized": personalize,
                    "campaign": campaign_name
                }
            )
        
        except Exception as e:
            return ToolResult(
                success=False,
                data=None,
                message=f"Failed to send email: {str(e)}",
                metadata={"error": str(e)}
            )
    
    def _personalize_email(self, subject: str, body: str, lead_data: Dict[str, Any]) -> tuple:
        """Personaliza email usando datos del lead."""
        personalized_subject = subject
        personalized_body = body
        
        # Reemplazar variables comunes
        replacements = {
            "{name}": lead_data.get("name", "Valued Customer"),
            "{first_name}": lead_data.get("first_name", lead_data.get("name", "Valued").split()[0]),
            "{company}": lead_data.get("company", "your company"),
            "{industry}": lead_data.get("industry", ""),
            "{role}": lead_data.get("role", ""),
            "{location}": lead_data.get("location", ""),
        }
        
        for placeholder, value in replacements.items():
            personalized_subject = personalized_subject.replace(placeholder, str(value))
            personalized_body = personalized_body.replace(placeholder, str(value))
        
        return personalized_subject, personalized_body
    
    def _get_lead_info(self, email: str) -> Optional[Dict[str, Any]]:
        """Obtiene información del lead desde archivo JSON."""
        leads = self._load_json(self.leads_file)
        for lead in leads:
            if lead.get("email") == email:
                return lead
        return None
    
    def _update_lead_engagement(self, email: str, action: str):
        """Actualiza engagement del lead."""
        leads = self._load_json(self.leads_file)
        for lead in leads:
            if lead.get("email") == email:
                if "engagement" not in lead:
                    lead["engagement"] = []
                lead["engagement"].append({
                    "action": action,
                    "timestamp": datetime.now().isoformat()
                })
                lead["last_contact"] = datetime.now().isoformat()
                self._save_json(self.leads_file, leads)
                break
    
    def _track_email(self, recipient: str, subject: str, campaign_name: Optional[str] = None,
                     ab_test_variant: Optional[str] = None, support_ticket_id: Optional[str] = None):
        """Registra email enviado para tracking."""
        tracking = self._load_json(self.email_tracking_file)
        tracking.append({
            "recipient": recipient,
            "subject": subject,
            "sent_at": datetime.now().isoformat(),
            "campaign": campaign_name,
            "ab_test_variant": ab_test_variant,
            "support_ticket_id": support_ticket_id,
            "opened": False,
            "clicked": False
        })
        self._save_json(self.email_tracking_file, tracking)
    
    def _schedule_follow_up(self, recipient: str, days: int, campaign_name: Optional[str] = None):
        """Programa follow-up automático."""
        follow_up_date = datetime.now() + timedelta(days=days)
        # Guardar en archivo de seguimientos
        follow_ups_file = self.data_dir / "follow_ups.json"
        follow_ups = self._load_json(follow_ups_file)
        follow_ups.append({
            "recipient": recipient,
            "scheduled_date": follow_up_date.isoformat(),
            "campaign": campaign_name,
            "status": "pending"
        })
        self._save_json(follow_ups_file, follow_ups)
    
    def _update_campaign_stats(self, campaign_name: str, sent: int, total: int):
        """Actualiza estadísticas de campaña."""
        campaigns = self._load_json(self.campaigns_file)
        if campaign_name not in campaigns:
            campaigns[campaign_name] = {
                "created_at": datetime.now().isoformat(),
                "emails_sent": 0,
                "emails_opened": 0,
                "emails_clicked": 0,
                "conversions": 0
            }
        campaigns[campaign_name]["emails_sent"] += sent
        campaigns[campaign_name]["last_updated"] = datetime.now().isoformat()
        self._save_json(self.campaigns_file, campaigns)
    
    def _handle_faq_response(self, category: str, original_body: str) -> str:
        """Genera respuesta automática basada en FAQ."""
        faqs = self._load_json(self.faq_file)
        category_faqs = [faq for faq in faqs if faq.get("category") == category]
        
        if category_faqs:
            # Agregar respuestas FAQ al cuerpo
            faq_section = "\n\n--- Preguntas Frecuentes ---\n\n"
            for faq in category_faqs[:3]:  # Top 3 FAQs
                faq_section += f"Q: {faq.get('question', '')}\n"
                faq_section += f"A: {faq.get('answer', '')}\n\n"
            return original_body + faq_section
        
        return original_body
    
    # Métodos públicos para gestión avanzada
    
    def create_campaign(
        self,
        campaign_name: str,
        recipients: List[str],
        subject_template: str,
        body_template: str,
        schedule_date: Optional[str] = None
    ) -> ToolResult:
        """Crea una nueva campaña de email."""
        campaigns = self._load_json(self.campaigns_file)
        campaigns[campaign_name] = {
            "created_at": datetime.now().isoformat(),
            "recipients": recipients,
            "subject_template": subject_template,
            "body_template": body_template,
            "schedule_date": schedule_date,
            "status": "scheduled" if schedule_date else "active",
            "emails_sent": 0,
            "emails_opened": 0,
            "emails_clicked": 0
        }
        self._save_json(self.campaigns_file, campaigns)
        
        return ToolResult(
            success=True,
            data={"campaign_name": campaign_name},
            message=f"Campaign '{campaign_name}' created successfully",
            metadata={}
        )
    
    def add_lead(
        self,
        email: str,
        name: Optional[str] = None,
        company: Optional[str] = None,
        industry: Optional[str] = None,
        role: Optional[str] = None,
        **kwargs
    ) -> ToolResult:
        """Agrega un nuevo lead."""
        leads = self._load_json(self.leads_file)
        
        # Verificar si ya existe
        for lead in leads:
            if lead.get("email") == email:
                return ToolResult(
                    success=False,
                    data=None,
                    message=f"Lead with email {email} already exists",
                    metadata={}
                )
        
        new_lead = {
            "email": email,
            "name": name,
            "company": company,
            "industry": industry,
            "role": role,
            "added_at": datetime.now().isoformat(),
            "engagement": [],
            **kwargs
        }
        
        leads.append(new_lead)
        self._save_json(self.leads_file, leads)
        
        return ToolResult(
            success=True,
            data={"lead": new_lead},
            message=f"Lead added successfully: {email}",
            metadata={}
        )
    
    def get_campaign_stats(self, campaign_name: str) -> Dict[str, Any]:
        """Obtiene estadísticas de una campaña."""
        campaigns = self._load_json(self.campaigns_file)
        return campaigns.get(campaign_name, {})
    
    def get_email_analytics(self) -> Dict[str, Any]:
        """Obtiene analytics generales de emails."""
        tracking = self._load_json(self.email_tracking_file)
        campaigns = self._load_json(self.campaigns_file)
        
        total_sent = len(tracking)
        total_opened = sum(1 for t in tracking if t.get("opened", False))
        total_clicked = sum(1 for t in tracking if t.get("clicked", False))
        
        return {
            "total_emails_sent": total_sent,
            "total_opened": total_opened,
            "total_clicked": total_clicked,
            "open_rate": (total_opened / total_sent * 100) if total_sent > 0 else 0,
            "click_rate": (total_clicked / total_sent * 100) if total_sent > 0 else 0,
            "active_campaigns": len([c for c in campaigns.values() if c.get("status") == "active"]),
            "total_campaigns": len(campaigns)
        }

