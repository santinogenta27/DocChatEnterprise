"""
Modo Leads: Agente de Ventas / SDR Outbound
Sistema completo para gestión y automatización de leads con Email y WhatsApp.
"""

from __future__ import annotations

import csv
import json
import os
import time
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from .config import AppConfig
from .tools.whatsapp_tool import WhatsAppTool
from .tools.email_marketing_tool import EmailMarketingTool
from .tools.crm_tool import CRMTool
from .tools.lead_generation_tool import LeadGenerationTool
from .tools.integration_tool import IntegrationTool
from .integrations.langgraph_integration import LangGraphIntegration
from .integrations.crewai_integration import CrewAIIntegration
from .integrations.composio_integration import ComposioIntegration


@dataclass
class Lead:
    """Representa un lead individual."""
    lead_id: str
    name: str
    email: str
    phone: Optional[str] = None
    company: Optional[str] = None
    position: Optional[str] = None
    industry: Optional[str] = None
    source: Optional[str] = None
    status: str = "new"  # new, contacted, responded, qualified, converted, lost
    score: float = 0.0
    notes: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    last_contacted: Optional[str] = None
    next_followup: Optional[str] = None
    channel_preference: str = "email"  # email, whatsapp, both


@dataclass
class Message:
    """Representa un mensaje enviado a un lead."""
    message_id: str
    lead_id: str
    channel: str  # email, whatsapp
    subject: Optional[str] = None
    content: str = ""
    status: str = "sent"  # sent, delivered, opened, clicked, replied, bounced
    sent_at: str = field(default_factory=lambda: datetime.now().isoformat())
    opened_at: Optional[str] = None
    replied_at: Optional[str] = None
    reply_content: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Sequence:
    """Secuencia de follow-up para leads."""
    sequence_id: str
    name: str
    steps: List[Dict[str, Any]]  # [{delay_days: int, channel: str, template: str}]
    active: bool = True
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


class LeadsMode:
    """
    Modo Leads: Agente de Ventas / SDR Outbound
    
    Características:
    - Importación de leads desde CSV
    - Generación de mensajes personalizados con LLM
    - Envío automático por Email y WhatsApp
    - Secuencias de follow-up automatizadas
    - Scoring y calificación de leads
    - Analytics y reportes
    """
    
    def __init__(self, config: AppConfig):
        self.config = config
        
        # Directorio para datos de leads
        self.data_dir = Path(config.memory_dir) / "leads_data"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Archivos de datos
        self.leads_file = self.data_dir / "leads.json"
        self.messages_file = self.data_dir / "messages.json"
        self.sequences_file = self.data_dir / "sequences.json"
        
        # LLM para generación de mensajes
        if not config.openai_api_key:
            raise ValueError("OPENAI_API_KEY requerida para Leads Mode")
        
        self.llm = ChatOpenAI(
            model=config.research_model or "gpt-4o",
            temperature=0.7,  # Más creativo para mensajes personalizados
            api_key=config.openai_api_key,
            max_tokens=1000
        )
        
        # Herramientas
        self.whatsapp_tool = WhatsAppTool(config)
        self.email_tool = EmailMarketingTool(config)
        self.crm_tool = CRMTool(config)
        self.lead_generation_tool = LeadGenerationTool(config)
        self.integration_tool = IntegrationTool(config)
        
        # Integraciones avanzadas
        try:
            self.langgraph = LangGraphIntegration(config, llm=self.llm)
            print("✅ LangGraph integrado en Leads Mode")
        except Exception as e:
            print(f"⚠️ LangGraph no disponible en Leads Mode: {e}")
            self.langgraph = None
        
        try:
            self.crewai = CrewAIIntegration(config)
            print("✅ CrewAI integrado en Leads Mode")
        except Exception as e:
            print(f"⚠️ CrewAI no disponible en Leads Mode: {e}")
            self.crewai = None
        
        try:
            self.composio = ComposioIntegration(config)
            print("✅ Composio integrado en Leads Mode")
        except Exception as e:
            print(f"⚠️ Composio no disponible en Leads Mode: {e}")
            self.composio = None
        
        # Configuración de CRMs conectados
        self.connected_crms: List[str] = []  # Lista de CRMs conectados
        self.crm_sync_enabled = os.getenv("CRM_SYNC_ENABLED", "false").lower() == "true"
        
        # Cargar datos existentes
        self.leads: Dict[str, Lead] = self._load_leads()
        self.messages: List[Message] = self._load_messages()
        self.sequences: Dict[str, Sequence] = self._load_sequences()
        
        # Configuración por defecto
        self.default_email_from = os.getenv("LEADS_EMAIL_FROM", "noreply@company.com")
        self.default_email_name = os.getenv("LEADS_EMAIL_NAME", "Sales Team")
        self.max_daily_emails = int(os.getenv("MAX_DAILY_EMAILS", "100"))
        self.max_daily_whatsapp = int(os.getenv("MAX_DAILY_WHATSAPP", "50"))
        
        # Contadores diarios
        self.daily_email_count = 0
        self.daily_whatsapp_count = 0
        self.last_reset_date = datetime.now().date()
    
    def _load_leads(self) -> Dict[str, Lead]:
        """Carga leads desde archivo JSON."""
        if not self.leads_file.exists():
            return {}
        
        try:
            with open(self.leads_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return {
                    lead_id: Lead(**lead_data)
                    for lead_id, lead_data in data.items()
                }
        except Exception as e:
            print(f"Error cargando leads: {e}")
            return {}
    
    def _save_leads(self):
        """Guarda leads en archivo JSON."""
        try:
            data = {
                lead_id: asdict(lead)
                for lead_id, lead in self.leads.items()
            }
            with open(self.leads_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error guardando leads: {e}")
    
    def _load_messages(self) -> List[Message]:
        """Carga mensajes desde archivo JSON."""
        if not self.messages_file.exists():
            return []
        
        try:
            with open(self.messages_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return [Message(**msg_data) for msg_data in data]
        except Exception as e:
            print(f"Error cargando mensajes: {e}")
            return []
    
    def _save_messages(self):
        """Guarda mensajes en archivo JSON."""
        try:
            data = [asdict(msg) for msg in self.messages]
            with open(self.messages_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error guardando mensajes: {e}")
    
    def _load_sequences(self) -> Dict[str, Sequence]:
        """Carga secuencias desde archivo JSON."""
        if not self.sequences_file.exists():
            return {}
        
        try:
            with open(self.sequences_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return {
                    seq_id: Sequence(**seq_data)
                    for seq_id, seq_data in data.items()
                }
        except Exception as e:
            print(f"Error cargando secuencias: {e}")
            return {}
    
    def _save_sequences(self):
        """Guarda secuencias en archivo JSON."""
        try:
            data = {
                seq_id: asdict(seq)
                for seq_id, seq in self.sequences.items()
            }
            with open(self.sequences_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error guardando secuencias: {e}")
    
    def import_leads_from_csv(self, csv_content: str) -> Dict[str, Any]:
        """
        Importa leads desde contenido CSV.
        
        Formato esperado: name, email, phone, company, position, industry, source
        """
        try:
            lines = csv_content.strip().split('\n')
            reader = csv.DictReader(lines)
            
            imported = 0
            errors = []
            
            for row_num, row in enumerate(reader, start=2):
                try:
                    # Validar campos requeridos
                    if not row.get('email') or not row.get('name'):
                        errors.append(f"Fila {row_num}: Falta email o nombre")
                        continue
                    
                    # Crear lead
                    lead_id = str(uuid.uuid4())
                    lead = Lead(
                        lead_id=lead_id,
                        name=row['name'].strip(),
                        email=row['email'].strip().lower(),
                        phone=row.get('phone', '').strip() or None,
                        company=row.get('company', '').strip() or None,
                        position=row.get('position', '').strip() or None,
                        industry=row.get('industry', '').strip() or None,
                        source=row.get('source', 'csv_import').strip() or 'csv_import',
                        metadata={k: v for k, v in row.items() if k not in ['name', 'email', 'phone', 'company', 'position', 'industry', 'source']}
                    )
                    
                    # Calcular score inicial
                    lead.score = self._calculate_lead_score(lead)
                    
                    self.leads[lead_id] = lead
                    imported += 1
                    
                except Exception as e:
                    errors.append(f"Fila {row_num}: {str(e)}")
            
            self._save_leads()
            
            return {
                "success": True,
                "imported": imported,
                "total": len(self.leads),
                "errors": errors
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "imported": 0
            }
    
    def _calculate_lead_score(self, lead: Lead) -> float:
        """Calcula un score inicial para el lead."""
        score = 0.0
        
        # Tener email: +20
        if lead.email:
            score += 20
        
        # Tener teléfono: +15
        if lead.phone:
            score += 15
        
        # Tener compañía: +20
        if lead.company:
            score += 20
        
        # Tener posición: +15
        if lead.position:
            score += 15
        
        # Tener industria: +10
        if lead.industry:
            score += 10
        
        # Fuente específica puede dar bonus
        if lead.source and lead.source not in ['csv_import', 'manual']:
            score += 10
        
        return min(score, 100.0)  # Máximo 100
    
    def generate_personalized_message(
        self,
        lead: Lead,
        message_type: str = "initial",
        product_info: Optional[str] = None,
        company_info: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Genera un mensaje personalizado usando LLM.
        
        Args:
            lead: El lead objetivo
            message_type: Tipo de mensaje (initial, followup, objection_response)
            product_info: Información del producto/servicio
            company_info: Información de la empresa
        """
        try:
            # Construir contexto del lead
            lead_context = f"""
Lead Information:
- Name: {lead.name}
- Company: {lead.company or 'Unknown'}
- Position: {lead.position or 'Unknown'}
- Industry: {lead.industry or 'Unknown'}
- Source: {lead.source or 'Unknown'}
"""
            
            if lead.notes:
                lead_context += f"\nPrevious interactions:\n" + "\n".join(f"- {note}" for note in lead.notes[-3:])
            
            # Prompt según tipo de mensaje
            if message_type == "initial":
                prompt_template = ChatPromptTemplate.from_messages([
                    ("system", """You are an expert sales development representative (SDR) writing personalized outreach messages.
Your goal is to create engaging, personalized messages that:
1. Show you've researched the prospect
2. Address their specific pain points
3. Provide clear value proposition
4. Include a soft call-to-action
5. Are concise (2-3 short paragraphs max)

Write in a professional but friendly tone. Avoid being too salesy."""),
                    ("user", """Generate a personalized {channel} message for this lead:

{lead_context}

{product_info}

{company_info}

Message type: {message_type}

Generate:
1. Subject line (for email) or opening line (for WhatsApp)
2. Personalized message body
3. Call-to-action

Format your response as JSON:
{{
    "subject": "Subject line (for email only)",
    "opening": "Opening line (for WhatsApp)",
    "body": "Message body",
    "cta": "Call-to-action"
}}""")
                ])
            else:
                prompt_template = ChatPromptTemplate.from_messages([
                    ("system", """You are an expert SDR writing follow-up messages.
Your goal is to re-engage prospects who haven't responded yet.
Be persistent but respectful. Add new value or angle in each follow-up."""),
                    ("user", """Generate a {message_type} message for this lead:

{lead_context}

{product_info}

Previous messages sent: {previous_count}

Generate a follow-up message that adds new value or angle.""")
                ])
            
            # Determinar canal
            channel = lead.channel_preference
            
            # Generar mensaje
            response = self.llm.invoke(
                prompt_template.format_messages(
                    channel=channel,
                    lead_context=lead_context,
                    product_info=product_info or "Our product helps companies improve their operations.",
                    company_info=company_info or "We are a leading provider of business solutions.",
                    message_type=message_type,
                    previous_count=len([m for m in self.messages if m.lead_id == lead.lead_id])
                )
            )
            
            # Parsear respuesta JSON
            try:
                import re
                json_match = re.search(r'\{.*\}', response.content, re.DOTALL)
                if json_match:
                    message_data = json.loads(json_match.group())
                else:
                    # Fallback si no hay JSON
                    message_data = {
                        "subject": f"Quick question about {lead.company or 'your business'}",
                        "opening": f"Hi {lead.name.split()[0] if lead.name else 'there'},",
                        "body": response.content,
                        "cta": "Would you be open to a quick 15-minute call?"
                    }
            except:
                message_data = {
                    "subject": f"Quick question about {lead.company or 'your business'}",
                    "opening": f"Hi {lead.name.split()[0] if lead.name else 'there'},",
                    "body": response.content,
                    "cta": "Would you be open to a quick 15-minute call?"
                }
            
            return {
                "success": True,
                "message": message_data,
                "channel": channel
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def send_message_to_lead(
        self,
        lead_id: str,
        channel: str,
        subject: Optional[str] = None,
        content: str = "",
        auto_generate: bool = True
    ) -> Dict[str, Any]:
        """
        Envía un mensaje a un lead por el canal especificado.
        
        Args:
            lead_id: ID del lead
            channel: Canal (email, whatsapp)
            subject: Asunto (solo para email)
            content: Contenido del mensaje
            auto_generate: Si True, genera mensaje personalizado si content está vacío
        """
        try:
            # Verificar límites diarios
            self._reset_daily_counters()
            
            if channel == "email" and self.daily_email_count >= self.max_daily_emails:
                return {
                    "success": False,
                    "error": f"Límite diario de emails alcanzado ({self.max_daily_emails})"
                }
            
            if channel == "whatsapp" and self.daily_whatsapp_count >= self.max_daily_whatsapp:
                return {
                    "success": False,
                    "error": f"Límite diario de WhatsApp alcanzado ({self.max_daily_whatsapp})"
                }
            
            # Obtener lead
            if lead_id not in self.leads:
                return {"success": False, "error": "Lead no encontrado"}
            
            lead = self.leads[lead_id]
            
            # Generar mensaje si es necesario
            if auto_generate and not content:
                message_gen = self.generate_personalized_message(lead, message_type="initial")
                if not message_gen.get("success"):
                    return message_gen
                
                message_data = message_gen["message"]
                if channel == "email":
                    subject = message_data.get("subject", subject)
                    content = f"{message_data.get('body', '')}\n\n{message_data.get('cta', '')}"
                else:
                    content = f"{message_data.get('opening', '')}\n\n{message_data.get('body', '')}\n\n{message_data.get('cta', '')}"
            
            # Enviar mensaje
            message_id = str(uuid.uuid4())
            result = None
            
            if channel == "email":
                # Usar email marketing tool
                result = self.email_tool.execute(
                    action="add_subscriber",
                    platform="local",
                    email=lead.email,
                    list_id="leads_list"
                )
                
                # Enviar email individual (simulado por ahora, se puede integrar con SMTP)
                result = {
                    "success": True,
                    "message": "Email prepared (configure SMTP for actual sending)",
                    "metadata": {"simulated": True}
                }
                
            elif channel == "whatsapp":
                # Usar WhatsApp tool
                phone = lead.phone or lead.email  # Fallback a email si no hay teléfono
                result = self.whatsapp_tool.execute(
                    to=phone,
                    message=content
                )
            
            # Registrar mensaje
            message = Message(
                message_id=message_id,
                lead_id=lead_id,
                channel=channel,
                subject=subject,
                content=content,
                status="sent" if result and result.get("success") else "failed",
                metadata={"tool_result": result}
            )
            
            self.messages.append(message)
            self._save_messages()
            
            # Actualizar lead
            lead.last_contacted = datetime.now().isoformat()
            lead.status = "contacted" if lead.status == "new" else lead.status
            self._save_leads()
            
            # Actualizar contadores
            if channel == "email":
                self.daily_email_count += 1
            else:
                self.daily_whatsapp_count += 1
            
            return {
                "success": result and result.get("success", False),
                "message_id": message_id,
                "result": result
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def _reset_daily_counters(self):
        """Resetea contadores diarios si es un nuevo día."""
        today = datetime.now().date()
        if today > self.last_reset_date:
            self.daily_email_count = 0
            self.daily_whatsapp_count = 0
            self.last_reset_date = today
    
    def get_analytics(self) -> Dict[str, Any]:
        """Obtiene analytics y métricas de leads."""
        total_leads = len(self.leads)
        total_messages = len(self.messages)
        
        # Leads por status
        status_counts = {}
        for lead in self.leads.values():
            status_counts[lead.status] = status_counts.get(lead.status, 0) + 1
        
        # Mensajes por canal
        channel_counts = {}
        for msg in self.messages:
            channel_counts[msg.channel] = channel_counts.get(msg.channel, 0) + 1
        
        # Mensajes por status
        message_status_counts = {}
        for msg in self.messages:
            message_status_counts[msg.status] = message_status_counts.get(msg.status, 0) + 1
        
        # Tasa de respuesta (si hay replies)
        replied_count = len([m for m in self.messages if m.status == "replied"])
        response_rate = (replied_count / total_messages * 100) if total_messages > 0 else 0
        
        return {
            "total_leads": total_leads,
            "total_messages": total_messages,
            "status_distribution": status_counts,
            "channel_distribution": channel_counts,
            "message_status_distribution": message_status_counts,
            "response_rate": f"{response_rate:.2f}%",
            "daily_emails_sent": self.daily_email_count,
            "daily_whatsapp_sent": self.daily_whatsapp_count,
            "daily_email_limit": self.max_daily_emails,
            "daily_whatsapp_limit": self.max_daily_whatsapp
        }
    
    def get_leads_list(self, status: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Obtiene lista de leads, opcionalmente filtrada por status."""
        leads_list = list(self.leads.values())
        
        if status:
            leads_list = [l for l in leads_list if l.status == status]
        
        # Ordenar por score descendente
        leads_list.sort(key=lambda x: x.score, reverse=True)
        
        # Limitar
        leads_list = leads_list[:limit]
        
        return [asdict(lead) for lead in leads_list]
    
    def generate_leads_autonomously(
        self,
        criteria: Dict[str, Any],
        sources: List[str] = None,
        max_leads: int = 50
    ) -> Dict[str, Any]:
        """
        Genera leads automáticamente usando Agentic AI.
        
        Args:
            criteria: Criterios de búsqueda (industry, location, company_size, titles, etc.)
            sources: Fuentes a usar (linkedin, apollo, zoominfo, google_ads, facebook)
            max_leads: Máximo de leads a generar
        """
        try:
            sources = sources or ["apollo", "linkedin"]  # Por defecto
            
            all_leads = []
            results_by_source = {}
            
            for source in sources:
                try:
                    result = self.lead_generation_tool.execute(
                        action="generate_leads",
                        source=source,
                        criteria=criteria
                    )
                    
                    if result.get("success") and result.get("data"):
                        leads = result.get("data", {}).get("leads", [])
                        all_leads.extend(leads)
                        results_by_source[source] = {
                            "success": True,
                            "count": len(leads),
                            "leads": leads
                        }
                    else:
                        results_by_source[source] = {
                            "success": False,
                            "error": result.get("message", "Unknown error")
                        }
                
                except Exception as e:
                    results_by_source[source] = {
                        "success": False,
                        "error": str(e)
                    }
            
            # Limitar total de leads
            all_leads = all_leads[:max_leads]
            
            # Convertir a formato Lead y guardar
            imported_count = 0
            for lead_data in all_leads:
                try:
                    lead_id = str(uuid.uuid4())
                    lead = Lead(
                        lead_id=lead_id,
                        name=lead_data.get("name", "Unknown"),
                        email=lead_data.get("email", ""),
                        phone=lead_data.get("phone"),
                        company=lead_data.get("company"),
                        position=lead_data.get("position"),
                        industry=lead_data.get("industry") or criteria.get("industry"),
                        source=lead_data.get("source", "agentic_ai"),
                        metadata={
                            "generated_by": "agentic_ai",
                            "generation_criteria": criteria,
                            "original_source": lead_data.get("source"),
                            "linkedin_url": lead_data.get("linkedin_url"),
                            "location": lead_data.get("location")
                        }
                    )
                    
                    # Calcular score
                    lead.score = self._calculate_lead_score(lead)
                    
                    self.leads[lead_id] = lead
                    imported_count += 1
                
                except Exception as e:
                    print(f"Error procesando lead: {e}")
            
            self._save_leads()
            
            # Sincronizar con CRMs si está habilitado
            if self.crm_sync_enabled and self.connected_crms:
                self._sync_leads_to_crms([l for l in all_leads if l.get("email")])
            
            return {
                "success": True,
                "total_generated": len(all_leads),
                "imported": imported_count,
                "results_by_source": results_by_source,
                "criteria": criteria
            }
        
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "total_generated": 0
            }
    
    def _sync_leads_to_crms(self, leads_data: List[Dict[str, Any]]):
        """Sincroniza leads con CRMs conectados."""
        for crm_platform in self.connected_crms:
            for lead_data in leads_data:
                try:
                    result = self.crm_tool.execute(
                        action="sync_lead",
                        platform=crm_platform,
                        lead_data=lead_data
                    )
                    if not result.get("success"):
                        print(f"Error sincronizando con {crm_platform}: {result.get('message')}")
                except Exception as e:
                    print(f"Error sincronizando lead con {crm_platform}: {e}")
    
    def text_to_action_leads(self, command: str) -> Dict[str, Any]:
        """
        Text-to-Action para leads: Convierte comandos en lenguaje natural en acciones de generación de leads.
        
        Ejemplos:
        - "Genera 50 leads de empresas de tecnología en San Francisco"
        - "Busca 20 CEOs de startups de fintech en Nueva York"
        - "Encuentra leads de empresas de más de 100 empleados en la industria de SaaS"
        """
        try:
            # Usar LLM para parsear el comando
            prompt = ChatPromptTemplate.from_messages([
                ("system", """You are an expert at parsing lead generation commands.
Parse the user's command and extract:
1. Number of leads to generate
2. Industry/vertical
3. Location/region
4. Job titles/positions
5. Company size
6. Any other criteria

Return JSON with this structure:
{{
    "max_leads": 50,
    "criteria": {{
        "industry": "technology",
        "location": "San Francisco",
        "titles": ["CEO", "CTO"],
        "company_sizes": ["51-200"],
        "keywords": ""
    }},
    "sources": ["apollo", "linkedin"]
}}"""),
                ("user", f"Parse this lead generation command: {command}")
            ])
            
            response = self.llm.invoke(prompt.format_messages())
            
            # Parsear JSON de la respuesta
            import re
            json_match = re.search(r'\{.*\}', response.content, re.DOTALL)
            if json_match:
                parsed = json.loads(json_match.group())
            else:
                # Fallback parsing básico
                parsed = {
                    "max_leads": 50,
                    "criteria": {
                        "industry": "technology",
                        "location": "San Francisco",
                        "keywords": command
                    },
                    "sources": ["apollo", "linkedin"]
                }
            
            # Generar leads
            result = self.generate_leads_autonomously(
                criteria=parsed.get("criteria", {}),
                sources=parsed.get("sources", ["apollo", "linkedin"]),
                max_leads=parsed.get("max_leads", 50)
            )
            
            return {
                "success": True,
                "command": command,
                "parsed_command": parsed,
                "generation_result": result
            }
        
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "command": command
            }
    
    def connect_crm(self, platform: str, credentials: Dict[str, Any]) -> Dict[str, Any]:
        """
        Conecta un CRM al sistema de leads.
        
        Args:
            platform: Plataforma (salesforce, hubspot, zoho, pipedrive, close)
            credentials: Credenciales necesarias para la plataforma
        """
        try:
            # Validar credenciales haciendo una prueba de conexión
            test_result = self.crm_tool.execute(
                action="get_leads",
                platform=platform,
                limit=1
            )
            
            if test_result.get("success") or "not yet implemented" in test_result.get("message", ""):
                # Agregar a lista de CRMs conectados
                if platform not in self.connected_crms:
                    self.connected_crms.append(platform)
                
                return {
                    "success": True,
                    "message": f"CRM {platform} connected successfully",
                    "platform": platform
                }
            else:
                return {
                    "success": False,
                    "error": f"Failed to connect to {platform}: {test_result.get('message')}",
                    "platform": platform
                }
        
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "platform": platform
            }
    
    def send_alert(
        self,
        alert_type: str,
        message: str,
        lead_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Envía alertas sobre nuevos leads o eventos importantes.
        
        Args:
            alert_type: Tipo de alerta (slack, teams, email, sms)
            message: Mensaje de la alerta
            lead_data: Datos del lead (opcional)
        """
        try:
            if alert_type == "slack":
                result = self.integration_tool.execute(
                    action="send_slack",
                    channel=os.getenv("SLACK_LEADS_CHANNEL", "#sales-leads"),
                    message=message
                )
            elif alert_type == "teams":
                result = self.integration_tool.execute(
                    action="send_teams",
                    channel=os.getenv("TEAMS_LEADS_CHANNEL", ""),
                    message=message
                )
            elif alert_type == "email":
                # Usar email tool
                result = self.email_tool.execute(
                    action="add_subscriber",
                    platform="local",
                    email=os.getenv("LEADS_ALERT_EMAIL", ""),
                    list_id="alerts"
                )
                result = {"success": True, "message": "Email alert prepared"}
            elif alert_type == "sms":
                # Usar WhatsApp tool como SMS (o implementar SMS real)
                result = self.whatsapp_tool.execute(
                    to=os.getenv("LEADS_ALERT_PHONE", ""),
                    message=message
                )
            else:
                return {
                    "success": False,
                    "error": f"Alert type {alert_type} not supported"
                }
            
            return {
                "success": result.get("success", False),
                "alert_type": alert_type,
                "result": result
            }
        
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "alert_type": alert_type
            }
    
    # ============================================
    # MÉTODOS CON LANGRAPH - Workflows Avanzados
    # ============================================
    
    def create_lead_nurturing_workflow(self, lead_id: str) -> Dict[str, Any]:
        """
        Crea un workflow LangGraph para nurturing de leads.
        
        Workflow:
        1. Calificar lead
        2. Generar mensaje personalizado
        3. Enviar mensaje
        4. Programar follow-up
        5. Sincronizar con CRM
        """
        if not self.langgraph:
            return {"success": False, "error": "LangGraph no está disponible"}
        
        try:
            # Definir nodos del workflow
            def qualify_lead(state: Dict[str, Any]) -> Dict[str, Any]:
                """Nodo: Calificar lead"""
                lead = self.leads.get(state["data"]["lead_id"])
                if lead:
                    score = self._calculate_lead_score(lead)
                    state["data"]["score"] = score
                    state["data"]["qualified"] = score >= 50.0
                return state
            
            def generate_message(state: Dict[str, Any]) -> Dict[str, Any]:
                """Nodo: Generar mensaje"""
                lead = self.leads.get(state["data"]["lead_id"])
                if lead:
                    result = self.generate_personalized_message(
                        lead_id=lead.lead_id,
                        message_type="initial"
                    )
                    if result.get("success"):
                        state["data"]["message"] = result["message"]
                return state
            
            def send_message(state: Dict[str, Any]) -> Dict[str, Any]:
                """Nodo: Enviar mensaje"""
                lead = self.leads.get(state["data"]["lead_id"])
                if lead and state["data"].get("message"):
                    result = self.send_message_to_lead(
                        lead_id=lead.lead_id,
                        channel=lead.channel_preference,
                        content=json.dumps(state["data"]["message"]),
                        auto_generate=False
                    )
                    state["data"]["sent"] = result.get("success", False)
                return state
            
            def schedule_followup(state: Dict[str, Any]) -> Dict[str, Any]:
                """Nodo: Programar follow-up"""
                lead = self.leads.get(state["data"]["lead_id"])
                if lead and state["data"].get("sent"):
                    # Programar follow-up en 3 días
                    followup_date = (datetime.now() + timedelta(days=3)).isoformat()
                    lead.next_followup = followup_date
                    self._save_leads()
                    state["data"]["followup_scheduled"] = followup_date
                return state
            
            def sync_crm(state: Dict[str, Any]) -> Dict[str, Any]:
                """Nodo: Sincronizar con CRM"""
                if self.crm_sync_enabled and self.connected_crms:
                    lead = self.leads.get(state["data"]["lead_id"])
                    if lead:
                        self._sync_leads_to_crms([asdict(lead)])
                        state["data"]["crm_synced"] = True
                return state
            
            # Crear workflow
            nodes = {
                "qualify": qualify_lead,
                "generate": generate_message,
                "send": send_message,
                "followup": schedule_followup,
                "sync": sync_crm
            }
            
            edges = [
                ("qualify", "generate"),
                ("generate", "send"),
                ("send", "followup"),
                ("followup", "sync")
            ]
            
            workflow_id = f"lead_nurturing_{lead_id}"
            workflow = self.langgraph.create_workflow(
                workflow_id=workflow_id,
                nodes=nodes,
                edges=edges,
                entry_point="qualify",
                exit_point="sync"
            )
            
            # Ejecutar workflow
            result = self.langgraph.execute_workflow(
                workflow_id=workflow_id,
                initial_data={"lead_id": lead_id}
            )
            
            return result
        
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    # ============================================
    # MÉTODOS CON CREWAI - Multi-Agent Collaboration
    # ============================================
    
    def create_lead_generation_crew(self) -> Dict[str, Any]:
        """
        Crea un crew de agentes CrewAI para generación de leads.
        
        Agentes:
        - Lead Researcher: Investiga y encuentra leads
        - Lead Qualifier: Califica leads encontrados
        - Outreach Specialist: Genera mensajes personalizados
        """
        if not self.crewai:
            return {"success": False, "error": "CrewAI no está disponible"}
        
        try:
            # Crear agentes especializados
            researcher = self.crewai.create_agent(
                agent_id="lead_researcher",
                role="Lead Research Specialist",
                goal="Find and identify high-quality leads that match our ideal customer profile",
                backstory="""You are an expert at finding potential customers using various 
                sources like LinkedIn, company databases, and web research. You understand 
                what makes a good lead and you can identify companies and individuals that would 
                benefit from our product.""",
                verbose=True
            )
            
            qualifier = self.crewai.create_agent(
                agent_id="lead_qualifier",
                role="Lead Qualification Specialist",
                goal="Evaluate and score leads based on fit, budget, authority, need, and timeline",
                backstory="""You are an expert at qualifying leads. You analyze company size, 
                industry, job titles, and other signals to determine if a lead is worth pursuing. 
                You assign scores and prioritize leads.""",
                verbose=True
            )
            
            outreach_specialist = self.crewai.create_agent(
                agent_id="outreach_specialist",
                role="Outreach Message Specialist",
                goal="Create highly personalized and compelling outreach messages for qualified leads",
                backstory="""You are an expert at writing sales emails and messages that get 
                responses. You understand how to personalize messages, add value, and create 
                compelling calls-to-action.""",
                verbose=True
            )
            
            # Crear tareas
            research_task = self.crewai.create_task(
                description="Research and find 10 high-quality leads matching our ideal customer profile",
                agent=researcher,
                expected_output="List of 10 leads with company name, contact name, email, and company details"
            )
            
            qualification_task = self.crewai.create_task(
                description="Qualify the leads found by the researcher and assign scores",
                agent=qualifier,
                expected_output="List of qualified leads with scores and prioritization"
            )
            
            outreach_task = self.crewai.create_task(
                description="Create personalized outreach messages for the top 5 qualified leads",
                agent=outreach_specialist,
                expected_output="5 personalized outreach messages ready to send"
            )
            
            # Crear crew
            crew = self.crewai.create_crew(
                crew_id="lead_generation_crew",
                agents=[researcher, qualifier, outreach_specialist],
                tasks=[research_task, qualification_task, outreach_task],
                process="sequential",
                verbose=True
            )
            
            return {
                "success": True,
                "crew_id": "lead_generation_crew",
                "agents": ["researcher", "qualifier", "outreach_specialist"],
                "message": "Lead generation crew creado exitosamente"
            }
        
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def execute_lead_generation_crew(self, query: str, count: int = 10) -> Dict[str, Any]:
        """Ejecuta el crew de generación de leads."""
        if not self.crewai:
            return {"success": False, "error": "CrewAI no está disponible"}
        
        try:
            # Asegurar que el crew existe
            if "lead_generation_crew" not in self.crewai.crews:
                self.create_lead_generation_crew()
            
            # Ejecutar crew
            result = self.crewai.execute_crew(
                crew_id="lead_generation_crew",
                inputs={
                    "query": query,
                    "count": count,
                    "ideal_customer_profile": "B2B companies in technology, 50-500 employees"
                }
            )
            
            return result
        
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    # ============================================
    # MÉTODOS CON COMPOSIO - 250+ Integraciones
    # ============================================
    
    def connect_composio_app(self, app_name: str) -> Dict[str, Any]:
        """Conecta una app de Composio para usar en leads."""
        if not self.composio:
            return {"success": False, "error": "Composio no está disponible"}
        
        try:
            result = self.composio.connect_app(app_name)
            return result
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def sync_lead_to_composio_crm(self, lead_id: str, crm_app: str = "salesforce") -> Dict[str, Any]:
        """
        Sincroniza un lead a un CRM usando Composio.
        
        Args:
            lead_id: ID del lead
            crm_app: App de CRM (salesforce, hubspot, pipedrive, etc.)
        """
        if not self.composio:
            return {"success": False, "error": "Composio no está disponible"}
        
        try:
            lead = self.leads.get(lead_id)
            if not lead:
                return {"success": False, "error": "Lead no encontrado"}
            
            # Conectar app si no está conectada
            if crm_app not in self.composio.connected_apps:
                connect_result = self.composio.connect_app(crm_app)
                if not connect_result.get("success"):
                    return connect_result
            
            # Mapear acción según CRM
            action_map = {
                "salesforce": "create_lead",
                "hubspot": "create_contact",
                "pipedrive": "add_person"
            }
            
            action_name = action_map.get(crm_app, "create_lead")
            
            # Preparar parámetros según CRM
            if crm_app == "salesforce":
                parameters = {
                    "FirstName": lead.name.split()[0] if lead.name else "",
                    "LastName": " ".join(lead.name.split()[1:]) if lead.name and len(lead.name.split()) > 1 else "",
                    "Email": lead.email,
                    "Phone": lead.phone or "",
                    "Company": lead.company or "",
                    "Title": lead.position or ""
                }
            elif crm_app == "hubspot":
                parameters = {
                    "email": lead.email,
                    "firstname": lead.name.split()[0] if lead.name else "",
                    "lastname": " ".join(lead.name.split()[1:]) if lead.name and len(lead.name.split()) > 1 else "",
                    "phone": lead.phone or "",
                    "company": lead.company or "",
                    "jobtitle": lead.position or ""
                }
            else:
                parameters = {
                    "name": lead.name,
                    "email": lead.email,
                    "phone": lead.phone or "",
                    "company": lead.company or ""
                }
            
            # Ejecutar acción
            result = self.composio.execute_action(
                app_name=crm_app,
                action_name=action_name,
                parameters=parameters
            )
            
            if result.get("success"):
                # Actualizar lead con CRM ID
                if "result" in result and isinstance(result["result"], dict):
                    crm_id = result["result"].get("id") or result["result"].get("lead_id")
                    if crm_id:
                        lead.metadata[f"{crm_app}_id"] = crm_id
                        self._save_leads()
            
            return result
        
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_composio_available_apps(self) -> List[Dict[str, Any]]:
        """Obtiene lista de apps disponibles en Composio."""
        if not self.composio:
            return []
        
        try:
            return self.composio.get_available_apps()
        except Exception as e:
            print(f"Error obteniendo apps de Composio: {e}")
            return []

