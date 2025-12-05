"""
Marketing Agent: Agente de Email Marketing / Campañas Autónomo
Sistema super inteligente para automatización completa de marketing por email.
"""

from __future__ import annotations

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
from .tools.email_marketing_tool import EmailMarketingTool
from .tools.advertising_tool import AdvertisingTool
from .text_to_action import TextToAction
from .integrations.langgraph_integration import LangGraphIntegration
from .integrations.crewai_integration import CrewAIIntegration
from .integrations.composio_integration import ComposioIntegration


@dataclass
class CampaignCopy:
    """Copy generado para una campaña."""
    copy_id: str
    campaign_id: str
    subject_line: str
    preheader: str
    body_html: str
    body_text: str
    cta_text: str
    cta_url: Optional[str] = None
    personalization_fields: List[str] = field(default_factory=list)
    generated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    ai_model: str = "gpt-4o"


@dataclass
class AudienceSegment:
    """Segmento de audiencia."""
    segment_id: str
    name: str
    criteria: Dict[str, Any]  # {field: value, conditions, etc}
    size: int = 0
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class MarketingCampaign:
    """Campaña de marketing."""
    campaign_id: str
    name: str
    campaign_type: str  # newsletter, promotional, transactional, automated
    platform: str  # mailchimp, hubspot, activecampaign, local
    status: str = "draft"  # draft, scheduled, sending, sent, paused
    copy: Optional[CampaignCopy] = None
    segments: List[str] = field(default_factory=list)  # segment IDs
    scheduled_at: Optional[str] = None
    sent_at: Optional[str] = None
    performance: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CampaignPerformance:
    """Performance de una campaña."""
    campaign_id: str
    sent: int = 0
    delivered: int = 0
    opened: int = 0
    clicked: int = 0
    bounced: int = 0
    unsubscribed: int = 0
    complained: int = 0
    revenue: float = 0.0
    open_rate: float = 0.0
    click_rate: float = 0.0
    bounce_rate: float = 0.0
    unsubscribe_rate: float = 0.0
    conversion_rate: float = 0.0
    analyzed_at: str = field(default_factory=lambda: datetime.now().isoformat())


class MarketingAgent:
    """
    Agente de Email Marketing / Campañas Autónomo
    
    Características:
    - Generación inteligente de copys con IA
    - Segmentación automática de audiencias
    - Creación y envío de campañas vía API
    - Análisis de performance automático
    - Text-to-Action para comandos en lenguaje natural
    - Integración con Mailchimp, HubSpot, ActiveCampaign
    """
    
    def __init__(self, config: AppConfig):
        self.config = config
        
        # Directorio para datos de marketing
        self.data_dir = Path(config.memory_dir) / "marketing_data"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Archivos de datos
        self.campaigns_file = self.data_dir / "campaigns.json"
        self.copies_file = self.data_dir / "copies.json"
        self.segments_file = self.data_dir / "segments.json"
        self.performance_file = self.data_dir / "performance.json"
        
        # LLM para generación de copys y análisis
        if not config.openai_api_key:
            raise ValueError("OPENAI_API_KEY requerida para Marketing Agent")
        
        self.llm = ChatOpenAI(
            model=config.research_model or "gpt-4o",
            temperature=0.8,  # Más creativo para marketing
            api_key=config.openai_api_key,
            max_tokens=2000
        )
        
        # Herramientas
        self.email_tool = EmailMarketingTool(config)
        self.text_to_action = TextToAction(config)
        self.advertising_tool = AdvertisingTool(config)
        
        # Integraciones avanzadas
        try:
            self.langgraph = LangGraphIntegration(config, llm=self.llm)
            print("✅ LangGraph integrado en Marketing Agent")
        except Exception as e:
            print(f"⚠️ LangGraph no disponible en Marketing Agent: {e}")
            self.langgraph = None
        
        try:
            self.crewai = CrewAIIntegration(config)
            print("✅ CrewAI integrado en Marketing Agent")
        except Exception as e:
            print(f"⚠️ CrewAI no disponible en Marketing Agent: {e}")
            self.crewai = None
        
        try:
            self.composio = ComposioIntegration(config)
            print("✅ Composio integrado en Marketing Agent")
        except Exception as e:
            print(f"⚠️ Composio no disponible en Marketing Agent: {e}")
            self.composio = None
        
        # Cargar datos existentes
        self.campaigns: Dict[str, MarketingCampaign] = self._load_campaigns()
        self.copies: Dict[str, CampaignCopy] = self._load_copies()
        self.segments: Dict[str, AudienceSegment] = self._load_segments()
        self.performance_data: Dict[str, CampaignPerformance] = self._load_performance()
        
        # Configuración
        self.default_platform = os.getenv("MARKETING_DEFAULT_PLATFORM", "local")
        self.auto_analyze_performance = os.getenv("MARKETING_AUTO_ANALYZE", "true").lower() == "true"
    
    def _load_campaigns(self) -> Dict[str, MarketingCampaign]:
        """Carga campañas desde archivo JSON."""
        if not self.campaigns_file.exists():
            return {}
        
        try:
            with open(self.campaigns_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                campaigns = {}
                for camp_id, camp_data in data.items():
                    copy_data = camp_data.get("copy")
                    copy = None
                    if copy_data:
                        copy = CampaignCopy(**copy_data)
                    campaigns[camp_id] = MarketingCampaign(
                        **{k: v for k, v in camp_data.items() if k != "copy"},
                        copy=copy
                    )
                return campaigns
        except Exception as e:
            print(f"Error cargando campañas: {e}")
            return {}
    
    def _save_campaigns(self):
        """Guarda campañas en archivo JSON."""
        try:
            data = {}
            for camp_id, campaign in self.campaigns.items():
                camp_dict = asdict(campaign)
                if campaign.copy:
                    camp_dict["copy"] = asdict(campaign.copy)
                data[camp_id] = camp_dict
            with open(self.campaigns_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error guardando campañas: {e}")
    
    def _load_copies(self) -> Dict[str, CampaignCopy]:
        """Carga copys desde archivo JSON."""
        if not self.copies_file.exists():
            return {}
        
        try:
            with open(self.copies_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return {
                    copy_id: CampaignCopy(**copy_data)
                    for copy_id, copy_data in data.items()
                }
        except Exception as e:
            print(f"Error cargando copys: {e}")
            return {}
    
    def _save_copies(self):
        """Guarda copys en archivo JSON."""
        try:
            data = {
                copy_id: asdict(copy)
                for copy_id, copy in self.copies.items()
            }
            with open(self.copies_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error guardando copys: {e}")
    
    def _load_segments(self) -> Dict[str, AudienceSegment]:
        """Carga segmentos desde archivo JSON."""
        if not self.segments_file.exists():
            return {}
        
        try:
            with open(self.segments_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return {
                    seg_id: AudienceSegment(**seg_data)
                    for seg_id, seg_data in data.items()
                }
        except Exception as e:
            print(f"Error cargando segmentos: {e}")
            return {}
    
    def _save_segments(self):
        """Guarda segmentos en archivo JSON."""
        try:
            data = {
                seg_id: asdict(segment)
                for seg_id, segment in self.segments.items()
            }
            with open(self.segments_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error guardando segmentos: {e}")
    
    def _load_performance(self) -> Dict[str, CampaignPerformance]:
        """Carga datos de performance desde archivo JSON."""
        if not self.performance_file.exists():
            return {}
        
        try:
            with open(self.performance_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return {
                    perf_id: CampaignPerformance(**perf_data)
                    for perf_id, perf_data in data.items()
                }
        except Exception as e:
            print(f"Error cargando performance: {e}")
            return {}
    
    def _save_performance(self):
        """Guarda datos de performance en archivo JSON."""
        try:
            data = {
                perf_id: asdict(perf)
                for perf_id, perf in self.performance_data.items()
            }
            with open(self.performance_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error guardando performance: {e}")
    
    def generate_campaign_copy(
        self,
        campaign_name: str,
        campaign_type: str,
        target_audience: str,
        key_message: str,
        tone: str = "professional",
        include_cta: bool = True,
        personalization_fields: Optional[List[str]] = None
    ) -> CampaignCopy:
        """
        Genera copy inteligente para una campaña usando IA.
        
        Args:
            campaign_name: Nombre de la campaña
            campaign_type: Tipo (newsletter, promotional, transactional, etc.)
            target_audience: Descripción de la audiencia objetivo
            key_message: Mensaje clave a comunicar
            tone: Tono (professional, friendly, urgent, casual, etc.)
            include_cta: Si incluir call-to-action
            personalization_fields: Campos para personalización (ej: ["name", "company"])
        """
        try:
            prompt_template = ChatPromptTemplate.from_messages([
                ("system", """You are an expert email marketing copywriter with decades of experience.
Your task is to create compelling, conversion-focused email copy that:
1. Captures attention with subject lines
2. Engages readers with compelling preheaders
3. Delivers value in the body
4. Includes clear, action-oriented CTAs
5. Uses best practices for email marketing (2025)

Follow email marketing best practices:
- Subject lines: 30-50 characters, create urgency/curiosity
- Preheaders: 40-130 characters, complement subject line
- Body: Clear, scannable, value-focused
- CTA: Action-oriented, benefit-focused
- Personalization: Use placeholders like {{name}}, {{company}}"""),
                ("user", """Generate email marketing copy for:

Campaign Name: {campaign_name}
Campaign Type: {campaign_type}
Target Audience: {target_audience}
Key Message: {key_message}
Tone: {tone}
Include CTA: {include_cta}
Personalization Fields: {personalization_fields}

Generate:
1. Subject line (30-50 chars, compelling)
2. Preheader (40-130 chars, complements subject)
3. Email body HTML (professional, scannable, engaging)
4. Email body text version (plain text alternative)
5. CTA text and suggested URL

Format as JSON:
{{
    "subject_line": "Subject line here",
    "preheader": "Preheader text here",
    "body_html": "<html>...</html>",
    "body_text": "Plain text version",
    "cta_text": "Call to action text",
    "cta_url": "https://example.com/cta",
    "personalization_fields": ["name", "company"]
}}""")
            ])
            
            response = self.llm.invoke(
                prompt_template.format_messages(
                    campaign_name=campaign_name,
                    campaign_type=campaign_type,
                    target_audience=target_audience,
                    key_message=key_message,
                    tone=tone,
                    include_cta=str(include_cta),
                    personalization_fields=", ".join(personalization_fields or [])
                )
            )
            
            # Parsear JSON de la respuesta
            import re
            json_match = re.search(r'\{.*\}', response.content, re.DOTALL)
            if json_match:
                copy_data = json.loads(json_match.group())
            else:
                # Fallback
                copy_data = {
                    "subject_line": f"{campaign_name} - {key_message[:30]}",
                    "preheader": key_message[:100],
                    "body_html": f"<p>{key_message}</p>",
                    "body_text": key_message,
                    "cta_text": "Learn More",
                    "cta_url": "https://example.com",
                    "personalization_fields": personalization_fields or []
                }
            
            # Crear CampaignCopy
            copy_id = str(uuid.uuid4())
            copy = CampaignCopy(
                copy_id=copy_id,
                campaign_id="",  # Se asignará cuando se cree la campaña
                subject_line=copy_data.get("subject_line", ""),
                preheader=copy_data.get("preheader", ""),
                body_html=copy_data.get("body_html", ""),
                body_text=copy_data.get("body_text", ""),
                cta_text=copy_data.get("cta_text", ""),
                cta_url=copy_data.get("cta_url"),
                personalization_fields=copy_data.get("personalization_fields", personalization_fields or [])
            )
            
            self.copies[copy_id] = copy
            self._save_copies()
            
            return copy
        
        except Exception as e:
            print(f"Error generando copy: {e}")
            # Fallback copy básico
            copy_id = str(uuid.uuid4())
            copy = CampaignCopy(
                copy_id=copy_id,
                campaign_id="",
                subject_line=f"{campaign_name} - {key_message[:30]}",
                preheader=key_message[:100],
                body_html=f"<p>{key_message}</p>",
                body_text=key_message,
                cta_text="Learn More",
                cta_url="https://example.com"
            )
            return copy
    
    def create_audience_segment(
        self,
        name: str,
        criteria: Dict[str, Any],
        description: Optional[str] = None
    ) -> AudienceSegment:
        """
        Crea un segmento de audiencia basado en criterios.
        
        Args:
            name: Nombre del segmento
            criteria: Criterios de segmentación {
                "field": "industry",
                "operator": "equals|contains|greater_than|less_than",
                "value": "Technology",
                "conditions": "AND|OR",
                "additional_filters": [...]
            }
            description: Descripción del segmento
        """
        try:
            segment_id = str(uuid.uuid4())
            segment = AudienceSegment(
                segment_id=segment_id,
                name=name,
                criteria=criteria,
                size=0,  # Se calculará cuando se use
                metadata={"description": description} if description else {}
            )
            
            self.segments[segment_id] = segment
            self._save_segments()
            
            return segment
        
        except Exception as e:
            print(f"Error creando segmento: {e}")
            raise
    
    def create_campaign(
        self,
        name: str,
        campaign_type: str,
        platform: Optional[str] = None,
        copy: Optional[CampaignCopy] = None,
        segments: Optional[List[str]] = None,
        scheduled_at: Optional[str] = None,
        auto_generate_copy: bool = True,
        copy_params: Optional[Dict[str, Any]] = None
    ) -> MarketingCampaign:
        """
        Crea una nueva campaña de marketing.
        
        Args:
            name: Nombre de la campaña
            campaign_type: Tipo (newsletter, promotional, transactional, automated)
            platform: Plataforma (mailchimp, hubspot, activecampaign, local)
            copy: Copy pre-generado (opcional)
            segments: Lista de IDs de segmentos
            scheduled_at: Fecha/hora programada (ISO format)
            auto_generate_copy: Si generar copy automáticamente
            copy_params: Parámetros para generación de copy
        """
        try:
            campaign_id = str(uuid.uuid4())
            platform = platform or self.default_platform
            
            # Generar copy si es necesario
            if auto_generate_copy and not copy:
                if copy_params:
                    copy = self.generate_campaign_copy(**copy_params)
                else:
                    # Generar copy básico
                    copy = self.generate_campaign_copy(
                        campaign_name=name,
                        campaign_type=campaign_type,
                        target_audience="General audience",
                        key_message=f"Campaign: {name}",
                        tone="professional"
                    )
            
            # Asignar campaign_id al copy
            if copy:
                copy.campaign_id = campaign_id
            
            campaign = MarketingCampaign(
                campaign_id=campaign_id,
                name=name,
                campaign_type=campaign_type,
                platform=platform,
                status="draft",
                copy=copy,
                segments=segments or [],
                scheduled_at=scheduled_at,
                metadata={}
            )
            
            self.campaigns[campaign_id] = campaign
            self._save_campaigns()
            
            # Crear campaña en la plataforma
            if platform != "local":
                self._create_campaign_in_platform(campaign)
            
            return campaign
        
        except Exception as e:
            print(f"Error creando campaña: {e}")
            raise
    
    def _create_campaign_in_platform(self, campaign: MarketingCampaign):
        """Crea la campaña en la plataforma de email marketing."""
        try:
            if not campaign.copy:
                return
            
            campaign_data = {
                "name": campaign.name,
                "subject": campaign.copy.subject_line,
                "content": campaign.copy.body_html,
                "list_id": campaign.segments[0] if campaign.segments else "default_list"
            }
            
            result = self.email_tool.execute(
                action="create_campaign",
                platform=campaign.platform,
                campaign_data=campaign_data
            )
            
            if result.success:
                campaign.metadata["platform_campaign_id"] = result.data.get("campaign", {}).get("id")
                self._save_campaigns()
        
        except Exception as e:
            print(f"Error creando campaña en plataforma: {e}")
    
    def send_campaign(
        self,
        campaign_id: str,
        confirm: bool = False
    ) -> Dict[str, Any]:
        """
        Envía una campaña.
        
        Args:
            campaign_id: ID de la campaña
            confirm: Si requiere confirmación antes de enviar
        """
        try:
            if campaign_id not in self.campaigns:
                return {
                    "success": False,
                    "error": "Campaña no encontrada"
                }
            
            campaign = self.campaigns[campaign_id]
            
            if campaign.status == "sent":
                return {
                    "success": False,
                    "error": "Campaña ya fue enviada"
                }
            
            # Enviar en plataforma
            if campaign.platform != "local":
                platform_campaign_id = campaign.metadata.get("platform_campaign_id")
                if platform_campaign_id:
                    result = self.email_tool.execute(
                        action="send_campaign",
                        platform=campaign.platform,
                        campaign_id=platform_campaign_id
                    )
                    
                    if not result.success:
                        return {
                            "success": False,
                            "error": f"Error enviando en plataforma: {result.message}"
                        }
            
            # Actualizar estado
            campaign.status = "sent"
            campaign.sent_at = datetime.now().isoformat()
            self._save_campaigns()
            
            # Iniciar análisis de performance si está habilitado
            if self.auto_analyze_performance:
                # Programar análisis para después del envío
                self._schedule_performance_analysis(campaign_id)
            
            return {
                "success": True,
                "campaign_id": campaign_id,
                "sent_at": campaign.sent_at,
                "platform": campaign.platform
            }
        
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def analyze_campaign_performance(
        self,
        campaign_id: str
    ) -> CampaignPerformance:
        """
        Analiza el performance de una campaña.
        
        Args:
            campaign_id: ID de la campaña
        """
        try:
            if campaign_id not in self.campaigns:
                raise ValueError("Campaña no encontrada")
            
            campaign = self.campaigns[campaign_id]
            
            # Obtener datos de performance de la plataforma
            if campaign.platform != "local":
                platform_campaign_id = campaign.metadata.get("platform_campaign_id")
                if platform_campaign_id:
                    result = self.email_tool.execute(
                        action="analyze_performance",
                        platform=campaign.platform,
                        campaign_id=platform_campaign_id
                    )
                    
                    if result.success and result.data:
                        platform_data = result.data
                    else:
                        platform_data = {}
                else:
                    platform_data = {}
            else:
                # Datos simulados para local
                platform_data = campaign.performance or {
                    "total_sent": 1000,
                    "total_opened": 250,
                    "total_clicked": 50,
                    "total_bounced": 10,
                    "total_unsubscribed": 5
                }
            
            # Calcular métricas
            sent = platform_data.get("total_sent", 0)
            opened = platform_data.get("total_opened", 0)
            clicked = platform_data.get("total_clicked", 0)
            bounced = platform_data.get("total_bounced", 0)
            unsubscribed = platform_data.get("total_unsubscribed", 0)
            delivered = sent - bounced
            
            open_rate = (opened / delivered * 100) if delivered > 0 else 0.0
            click_rate = (clicked / sent * 100) if sent > 0 else 0.0
            bounce_rate = (bounced / sent * 100) if sent > 0 else 0.0
            unsubscribe_rate = (unsubscribed / sent * 100) if sent > 0 else 0.0
            conversion_rate = (clicked / opened * 100) if opened > 0 else 0.0
            
            # Crear objeto de performance
            performance = CampaignPerformance(
                campaign_id=campaign_id,
                sent=sent,
                delivered=delivered,
                opened=opened,
                clicked=clicked,
                bounced=bounced,
                unsubscribed=unsubscribed,
                complained=platform_data.get("total_complained", 0),
                revenue=platform_data.get("revenue", 0.0),
                open_rate=open_rate,
                click_rate=click_rate,
                bounce_rate=bounce_rate,
                unsubscribe_rate=unsubscribe_rate,
                conversion_rate=conversion_rate
            )
            
            self.performance_data[campaign_id] = performance
            
            # Actualizar performance en campaña
            campaign.performance = {
                "sent": sent,
                "delivered": delivered,
                "opened": opened,
                "clicked": clicked,
                "bounced": bounced,
                "unsubscribed": unsubscribed,
                "open_rate": open_rate,
                "click_rate": click_rate,
                "bounce_rate": bounce_rate,
                "unsubscribe_rate": unsubscribe_rate,
                "conversion_rate": conversion_rate
            }
            
            self._save_performance()
            self._save_campaigns()
            
            return performance
        
        except Exception as e:
            print(f"Error analizando performance: {e}")
            raise
    
    def _schedule_performance_analysis(self, campaign_id: str):
        """Programa análisis de performance para después del envío."""
        # Por ahora, análisis inmediato. Se puede mejorar con scheduling
        try:
            time.sleep(2)  # Esperar un poco después del envío
            self.analyze_campaign_performance(campaign_id)
        except Exception as e:
            print(f"Error en análisis programado: {e}")
    
    def generate_performance_report(
        self,
        campaign_id: str
    ) -> Dict[str, Any]:
        """
        Genera un reporte completo de performance usando IA.
        
        Args:
            campaign_id: ID de la campaña
        """
        try:
            if campaign_id not in self.performance_data:
                performance = self.analyze_campaign_performance(campaign_id)
            else:
                performance = self.performance_data[campaign_id]
            
            campaign = self.campaigns.get(campaign_id)
            campaign_name = campaign.name if campaign else "Unknown"
            
            # Generar análisis con IA
            prompt = f"""Analiza el performance de esta campaña de email marketing y genera un reporte ejecutivo:

Campaña: {campaign_name}
Enviados: {performance.sent}
Entregados: {performance.delivered}
Abiertos: {performance.opened}
Clickeados: {performance.clicked}
Rebotados: {performance.bounced}
Desuscritos: {performance.unsubscribed}

Métricas:
- Tasa de apertura: {performance.open_rate:.2f}%
- Tasa de clicks: {performance.click_rate:.2f}%
- Tasa de rebote: {performance.bounce_rate:.2f}%
- Tasa de conversión: {performance.conversion_rate:.2f}%

Genera un reporte que incluya:
1. Resumen ejecutivo
2. Análisis de métricas clave
3. Comparación con benchmarks de la industria
4. Recomendaciones de mejora
5. Insights accionables

Formato: Markdown con secciones claras."""

            report_text = self.llm.invoke(prompt).content.strip()
            
            return {
                "success": True,
                "campaign_id": campaign_id,
                "campaign_name": campaign_name,
                "performance": asdict(performance),
                "report": report_text,
                "generated_at": datetime.now().isoformat()
            }
        
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def text_to_action_marketing(self, command: str) -> Dict[str, Any]:
        """
        Text-to-Action para marketing: Convierte comandos en lenguaje natural en acciones.
        
        Ejemplos:
        - "Crea una campaña de newsletter para clientes activos"
        - "Genera copy para promoción de producto nuevo"
        - "Envía campaña de bienvenida a nuevos suscriptores"
        - "Analiza performance de la última campaña"
        """
        try:
            # Usar LLM para parsear el comando
            prompt = ChatPromptTemplate.from_messages([
                ("system", """You are an expert at parsing marketing commands.
Parse the user's command and extract:
1. Action type (create_campaign, generate_copy, send_campaign, analyze_performance, create_segment)
2. Campaign details (name, type, audience, message)
3. Any specific requirements

Return JSON:
{{
    "action": "create_campaign|generate_copy|send_campaign|analyze_performance|create_segment",
    "campaign_name": "name",
    "campaign_type": "newsletter|promotional|transactional|automated",
    "target_audience": "description",
    "key_message": "main message",
    "tone": "professional|friendly|urgent",
    "platform": "mailchimp|hubspot|activecampaign|local",
    "auto_send": true/false
}}"""),
                ("user", f"Parse this marketing command: {command}")
            ])
            
            response = self.llm.invoke(prompt.format_messages())
            
            # Parsear JSON
            import re
            json_match = re.search(r'\{.*\}', response.content, re.DOTALL)
            if json_match:
                parsed = json.loads(json_match.group())
            else:
                # Fallback
                parsed = {
                    "action": "create_campaign",
                    "campaign_name": "Campaign from command",
                    "campaign_type": "promotional",
                    "target_audience": "General audience",
                    "key_message": command,
                    "tone": "professional",
                    "platform": "local",
                    "auto_send": False
                }
            
            # Ejecutar acción
            result = None
            
            if parsed.get("action") == "create_campaign":
                copy = self.generate_campaign_copy(
                    campaign_name=parsed.get("campaign_name", "Campaign"),
                    campaign_type=parsed.get("campaign_type", "promotional"),
                    target_audience=parsed.get("target_audience", "General audience"),
                    key_message=parsed.get("key_message", ""),
                    tone=parsed.get("tone", "professional")
                )
                
                campaign = self.create_campaign(
                    name=parsed.get("campaign_name", "Campaign"),
                    campaign_type=parsed.get("campaign_type", "promotional"),
                    platform=parsed.get("platform", "local"),
                    copy=copy,
                    auto_generate_copy=False
                )
                
                if parsed.get("auto_send", False):
                    send_result = self.send_campaign(campaign.campaign_id)
                    result = {
                        "action": "create_and_send_campaign",
                        "campaign": asdict(campaign),
                        "send_result": send_result
                    }
                else:
                    result = {
                        "action": "create_campaign",
                        "campaign": asdict(campaign)
                    }
            
            elif parsed.get("action") == "generate_copy":
                copy = self.generate_campaign_copy(
                    campaign_name=parsed.get("campaign_name", "Campaign"),
                    campaign_type=parsed.get("campaign_type", "promotional"),
                    target_audience=parsed.get("target_audience", "General audience"),
                    key_message=parsed.get("key_message", ""),
                    tone=parsed.get("tone", "professional")
                )
                result = {
                    "action": "generate_copy",
                    "copy": asdict(copy)
                }
            
            elif parsed.get("action") == "analyze_performance":
                # Buscar última campaña o campaña específica
                if self.campaigns:
                    latest_campaign = max(
                        self.campaigns.values(),
                        key=lambda c: c.created_at
                    )
                    report = self.generate_performance_report(latest_campaign.campaign_id)
                    result = {
                        "action": "analyze_performance",
                        "report": report
                    }
                else:
                    result = {
                        "action": "analyze_performance",
                        "error": "No hay campañas para analizar"
                    }
            
            else:
                result = {
                    "action": parsed.get("action", "unknown"),
                    "error": "Acción no implementada aún"
                }
            
            return {
                "success": True,
                "command": command,
                "parsed_command": parsed,
                "result": result
            }
        
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "command": command
            }
    
    def get_campaigns_list(self, status: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Obtiene lista de campañas."""
        campaigns_list = list(self.campaigns.values())
        
        if status:
            campaigns_list = [c for c in campaigns_list if c.status == status]
        
        # Ordenar por fecha de creación descendente
        campaigns_list.sort(key=lambda x: x.created_at, reverse=True)
        campaigns_list = campaigns_list[:limit]
        
        return [asdict(campaign) for campaign in campaigns_list]
    
    def get_analytics(self) -> Dict[str, Any]:
        """Obtiene analytics generales de marketing."""
        total_campaigns = len(self.campaigns)
        sent_campaigns = len([c for c in self.campaigns.values() if c.status == "sent"])
        
        # Calcular métricas agregadas
        total_sent = sum(p.sent for p in self.performance_data.values())
        total_opened = sum(p.opened for p in self.performance_data.values())
        total_clicked = sum(p.clicked for p in self.performance_data.values())
        
        avg_open_rate = sum(p.open_rate for p in self.performance_data.values()) / len(self.performance_data) if self.performance_data else 0.0
        avg_click_rate = sum(p.click_rate for p in self.performance_data.values()) / len(self.performance_data) if self.performance_data else 0.0
        
        return {
            "total_campaigns": total_campaigns,
            "sent_campaigns": sent_campaigns,
            "draft_campaigns": len([c for c in self.campaigns.values() if c.status == "draft"]),
            "total_segments": len(self.segments),
            "total_copies_generated": len(self.copies),
            "total_emails_sent": total_sent,
            "total_emails_opened": total_opened,
            "total_emails_clicked": total_clicked,
            "average_open_rate": f"{avg_open_rate:.2f}%",
            "average_click_rate": f"{avg_click_rate:.2f}%"
        }
    
    # ============================================
    # MÉTODOS CON LANGRAPH - Workflows Avanzados
    # ============================================
    
    def create_campaign_workflow(self, campaign_id: str) -> Dict[str, Any]:
        """
        Crea un workflow LangGraph para ejecución completa de campaña.
        
        Workflow:
        1. Generar copy
        2. Crear segmentos
        3. Crear campaña
        4. Enviar campaña
        5. Analizar performance
        """
        if not self.langgraph:
            return {"success": False, "error": "LangGraph no está disponible"}
        
        try:
            def generate_copy_node(state: Dict[str, Any]) -> Dict[str, Any]:
                """Nodo: Generar copy"""
                campaign = self.campaigns.get(state["data"]["campaign_id"])
                if campaign and not campaign.copy:
                    copy = self.generate_campaign_copy(
                        campaign_name=campaign.name,
                        campaign_type=campaign.campaign_type,
                        target_audience="General audience",
                        key_message=f"Campaign: {campaign.name}",
                        tone="professional"
                    )
                    campaign.copy = copy
                    self._save_campaigns()
                    state["data"]["copy_generated"] = True
                return state
            
            def create_campaign_node(state: Dict[str, Any]) -> Dict[str, Any]:
                """Nodo: Crear campaña en plataforma"""
                campaign = self.campaigns.get(state["data"]["campaign_id"])
                if campaign:
                    self._create_campaign_in_platform(campaign)
                    state["data"]["campaign_created"] = True
                return state
            
            def send_campaign_node(state: Dict[str, Any]) -> Dict[str, Any]:
                """Nodo: Enviar campaña"""
                result = self.send_campaign(
                    campaign_id=state["data"]["campaign_id"],
                    confirm=False
                )
                state["data"]["sent"] = result.get("success", False)
                return state
            
            def analyze_performance_node(state: Dict[str, Any]) -> Dict[str, Any]:
                """Nodo: Analizar performance"""
                if state["data"].get("sent"):
                    performance = self.analyze_campaign_performance(
                        state["data"]["campaign_id"]
                    )
                    state["data"]["performance"] = asdict(performance)
                return state
            
            # Crear workflow
            nodes = {
                "generate_copy": generate_copy_node,
                "create_campaign": create_campaign_node,
                "send": send_campaign_node,
                "analyze": analyze_performance_node
            }
            
            edges = [
                ("generate_copy", "create_campaign"),
                ("create_campaign", "send"),
                ("send", "analyze")
            ]
            
            workflow_id = f"campaign_{campaign_id}"
            workflow = self.langgraph.create_workflow(
                workflow_id=workflow_id,
                nodes=nodes,
                edges=edges,
                entry_point="generate_copy",
                exit_point="analyze"
            )
            
            # Ejecutar workflow
            result = self.langgraph.execute_workflow(
                workflow_id=workflow_id,
                initial_data={"campaign_id": campaign_id}
            )
            
            return result
        
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    # ============================================
    # MÉTODOS CON CREWAI - Multi-Agent Collaboration
    # ============================================
    
    def create_marketing_crew(self) -> Dict[str, Any]:
        """
        Crea un crew de agentes CrewAI para marketing.
        
        Agentes:
        - Copywriter: Genera copy persuasivo
        - Audience Analyst: Analiza y segmenta audiencias
        - Campaign Optimizer: Optimiza campañas
        - Performance Analyst: Analiza resultados
        """
        if not self.crewai:
            return {"success": False, "error": "CrewAI no está disponible"}
        
        try:
            # Crear agentes especializados
            copywriter = self.crewai.create_agent(
                agent_id="copywriter",
                role="Email Marketing Copywriter",
                goal="Create compelling, conversion-focused email copy that drives action",
                backstory="""You are an expert email copywriter with decades of experience 
                in direct response marketing. You know how to write subject lines that get 
                opened, body copy that engages, and CTAs that convert.""",
                verbose=True
            )
            
            audience_analyst = self.crewai.create_agent(
                agent_id="audience_analyst",
                role="Audience Segmentation Specialist",
                goal="Analyze audiences and create effective segments for targeted campaigns",
                backstory="""You are an expert at analyzing customer data and creating 
                meaningful segments. You understand demographics, behavior, and preferences 
                to create targeted audiences.""",
                verbose=True
            )
            
            campaign_optimizer = self.crewai.create_agent(
                agent_id="campaign_optimizer",
                role="Campaign Optimization Specialist",
                goal="Optimize email campaigns for maximum engagement and conversion",
                backstory="""You are an expert at A/B testing, timing optimization, and 
                campaign structure. You know what makes campaigns successful and how to 
                improve them.""",
                verbose=True
            )
            
            performance_analyst = self.crewai.create_agent(
                agent_id="performance_analyst",
                role="Marketing Performance Analyst",
                goal="Analyze campaign performance and provide actionable insights",
                backstory="""You are an expert at analyzing marketing metrics, identifying 
                trends, and providing recommendations. You understand open rates, click rates, 
                conversions, and ROI.""",
                verbose=True
            )
            
            # Crear tareas
            copy_task = self.crewai.create_task(
                description="Create compelling email copy for a marketing campaign",
                agent=copywriter,
                expected_output="Complete email copy with subject line, body, and CTA"
            )
            
            segmentation_task = self.crewai.create_task(
                description="Analyze audience and create segmentation strategy",
                agent=audience_analyst,
                expected_output="Segmentation strategy with defined audience segments"
            )
            
            optimization_task = self.crewai.create_task(
                description="Optimize campaign structure and timing",
                agent=campaign_optimizer,
                expected_output="Optimized campaign plan with recommendations"
            )
            
            analysis_task = self.crewai.create_task(
                description="Analyze campaign performance and provide insights",
                agent=performance_analyst,
                expected_output="Performance analysis report with actionable recommendations"
            )
            
            # Crear crew
            crew = self.crewai.create_crew(
                crew_id="marketing_crew",
                agents=[copywriter, audience_analyst, campaign_optimizer, performance_analyst],
                tasks=[copy_task, segmentation_task, optimization_task, analysis_task],
                process="sequential",
                verbose=True
            )
            
            return {
                "success": True,
                "crew_id": "marketing_crew",
                "agents": ["copywriter", "audience_analyst", "campaign_optimizer", "performance_analyst"],
                "message": "Marketing crew creado exitosamente"
            }
        
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def execute_marketing_crew(self, campaign_brief: str) -> Dict[str, Any]:
        """Ejecuta el crew de marketing para crear una campaña completa."""
        if not self.crewai:
            return {"success": False, "error": "CrewAI no está disponible"}
        
        try:
            # Asegurar que el crew existe
            if "marketing_crew" not in self.crewai.crews:
                self.create_marketing_crew()
            
            # Ejecutar crew
            result = self.crewai.execute_crew(
                crew_id="marketing_crew",
                inputs={
                    "campaign_brief": campaign_brief,
                    "target_audience": "B2B companies",
                    "campaign_goal": "Generate leads and increase engagement"
                }
            )
            
            return result
        
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    # ============================================
    # MÉTODOS CON COMPOSIO - 250+ Integraciones
    # ============================================
    
    def connect_marketing_platform(self, platform: str) -> Dict[str, Any]:
        """Conecta una plataforma de marketing usando Composio."""
        if not self.composio:
            return {"success": False, "error": "Composio no está disponible"}
        
        try:
            # Mapear nombres de plataformas
            platform_map = {
                "mailchimp": "mailchimp",
                "hubspot": "hubspot",
                "activecampaign": "activecampaign",
                "sendgrid": "sendgrid",
                "constant_contact": "constantcontact"
            }
            
            app_name = platform_map.get(platform.lower(), platform.lower())
            result = self.composio.connect_app(app_name)
            return result
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def send_campaign_via_composio(
        self,
        campaign_id: str,
        platform: str
    ) -> Dict[str, Any]:
        """
        Envía una campaña usando Composio para integración directa.
        
        Args:
            campaign_id: ID de la campaña
            platform: Plataforma (mailchimp, hubspot, activecampaign)
        """
        if not self.composio:
            return {"success": False, "error": "Composio no está disponible"}
        
        try:
            campaign = self.campaigns.get(campaign_id)
            if not campaign or not campaign.copy:
                return {"success": False, "error": "Campaña o copy no encontrado"}
            
            # Conectar plataforma si no está conectada
            if platform not in self.composio.connected_apps:
                connect_result = self.connect_marketing_platform(platform)
                if not connect_result.get("success"):
                    return connect_result
            
            # Mapear acciones según plataforma
            action_map = {
                "mailchimp": "create_campaign",
                "hubspot": "create_email_campaign",
                "activecampaign": "create_campaign"
            }
            
            action_name = action_map.get(platform, "create_campaign")
            
            # Preparar parámetros
            parameters = {
                "name": campaign.name,
                "subject": campaign.copy.subject_line,
                "html_content": campaign.copy.body_html,
                "text_content": campaign.copy.body_text
            }
            
            # Ejecutar acción
            result = self.composio.execute_action(
                app_name=platform,
                action_name=action_name,
                parameters=parameters
            )
            
            if result.get("success"):
                # Actualizar campaña con platform ID
                if "result" in result and isinstance(result["result"], dict):
                    platform_campaign_id = result["result"].get("id") or result["result"].get("campaign_id")
                    if platform_campaign_id:
                        campaign.metadata[f"{platform}_campaign_id"] = platform_campaign_id
                        self._save_campaigns()
            
            return result
        
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_composio_marketing_apps(self) -> List[Dict[str, Any]]:
        """Obtiene apps de marketing disponibles en Composio."""
        if not self.composio:
            return []
        
        try:
            all_apps = self.composio.get_available_apps()
            marketing_apps = [
                app for app in all_apps
                if any(keyword in app.get("name", "").lower() for keyword in 
                       ["mail", "marketing", "campaign", "email", "hubspot", "salesforce"])
            ]
            return marketing_apps
        except Exception as e:
            print(f"Error obteniendo apps de marketing: {e}")
            return []

    # ============================================
    # AGENTIC AI – Meta (FB/IG/WhatsApp) y TikTok
    # ============================================
    
    def connect_social_platform(self, platform: str) -> Dict[str, Any]:
        """
        Conecta una plataforma social (Meta / TikTok) vía Composio.
        
        Plataformas soportadas (mapeadas):
        - meta_marketing (Meta Marketing API: Facebook/Instagram Ads)
        - facebook
        - instagram
        - whatsapp_business
        - tiktok_ads
        - tiktok
        """
        if not self.composio:
            return {"success": False, "error": "Composio no está disponible para integrar Meta/TikTok"}
        
        try:
            platform_map = {
                "meta_ads": "meta_marketing",
                "meta": "meta_marketing",
                "facebook": "facebook",
                "instagram": "instagram",
                "whatsapp": "whatsapp_business",
                "whatsapp_business": "whatsapp_business",
                "tiktok": "tiktok",
                "tiktok_ads": "tiktok_ads",
            }
            app_name = platform_map.get(platform.lower(), platform.lower())
            result = self.composio.connect_app(app_name)
            if result.get("success"):
                return {
                    "success": True,
                    "platform": platform,
                    "app_name": app_name,
                    "message": result.get("message") or "Plataforma conectada (o simulada) vía Composio",
                }
            return result
        except Exception as e:
            return {"success": False, "error": str(e)}

    def run_agentic_social_workflow(
        self,
        channel: str,
        objective: str,
        audience: Optional[str] = None,
        budget_eur: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Lanza un flujo agentic de marketing para Meta/TikTok:
        - Usa LLM para definir estrategia y tipos de piezas.
        - Usa Composio para orquestar acciones básicas (simuladas o reales según COMPOSIO_API_KEY).
        
        Args:
            channel: "meta_ads", "facebook", "instagram", "whatsapp", "tiktok_ads", "tiktok"
            objective: Objetivo de negocio (ej: "aumentar ventas 20% en 90 días")
            audience: Descripción de la audiencia objetivo
            budget_eur: Presupuesto aproximado (solo informativo para el plan)
        """
        plan: Dict[str, Any] = {}
        actions: List[Dict[str, Any]] = []
        
        try:
            # 1) Generar plan de alto nivel con LLM
            audience_desc = audience or "audiencia general de marketing digital"
            budget_text = f"{budget_eur:.2f} EUR" if budget_eur is not None else "no especificado"
            
            prompt = f"""
You are an expert Agentic AI orchestrator for digital marketing on Meta (Facebook/Instagram/WhatsApp) and TikTok.

Design an agentic marketing plan for this channel: {channel}
Business objective: {objective}
Target audience: {audience_desc}
Budget: {budget_text}

Return a JSON with:
{{
  "strategy_summary": "...",
  "recommended_assets": [
    {{"type": "short_video", "channel": "tiktok", "count": 3}},
    {{"type": "image_ad", "channel": "meta", "count": 5}}
  ],
  "recommended_actions": [
    "Launch awareness campaign on TikTok with 3 creatives",
    "Test 2 creatives on Meta Ads optimized for purchases",
    "Retarget engaged users with WhatsApp broadcast (if allowed)"
  ]
}}
"""
            response = self.llm.invoke(prompt)
            import re
            json_match = re.search(r"\{.*\}", response.content, re.DOTALL)
            if json_match:
                plan = json.loads(json_match.group())
            else:
                plan = {
                    "strategy_summary": f"Plan básico para {channel} centrado en el objetivo: {objective}",
                    "recommended_assets": [],
                    "recommended_actions": [],
                }
        except Exception as e:
            plan = {
                "strategy_summary": f"⚠️ No se pudo generar un plan detallado: {e}",
                "recommended_assets": [],
                "recommended_actions": [],
            }
        
        # 2) Opcionalmente llamar a Composio para una acción mínima (si está disponible)
        composio_result: Optional[Dict[str, Any]] = None
        if self.composio:
            try:
                # Mapear canal a app Composio y a una acción genérica
                channel_map = {
                    "meta_ads": ("meta_marketing", "create_campaign"),
                    "meta": ("meta_marketing", "create_campaign"),
                    "facebook": ("facebook", "create_post"),
                    "instagram": ("instagram", "create_post"),
                    "whatsapp": ("whatsapp_business", "send_message"),
                    "whatsapp_business": ("whatsapp_business", "send_message"),
                    "tiktok_ads": ("tiktok_ads", "create_campaign"),
                    "tiktok": ("tiktok", "create_post"),
                }
                app_name, default_action = channel_map.get(
                    channel.lower(), ("meta_marketing", "create_campaign")
                )
                
                # Asegurar conexión
                _ = self.composio.connect_app(app_name)
                
                parameters = {
                    "objective": objective,
                    "audience_description": audience_desc,
                    "budget_eur": budget_eur,
                    "notes": "Generated by MarketingAgent.run_agentic_social_workflow (demo).",
                }
                
                composio_result = self.composio.execute_action(
                    app_name=app_name,
                    action_name=default_action,
                    parameters=parameters,
                )
                actions.append(
                    {
                        "app_name": app_name,
                        "action": default_action,
                        "parameters": parameters,
                        "result": composio_result,
                    }
                )
            except Exception as e:
                composio_result = {"success": False, "error": str(e)}
        else:
            composio_result = {
                "success": False,
                "error": "Composio no disponible: se requiere para integración directa con Meta/TikTok.",
            }
        
        return {
            "success": True,
            "channel": channel,
            "objective": objective,
            "audience": audience,
            "budget_eur": budget_eur,
            "plan": plan,
            "actions": actions,
            "composio_result": composio_result,
            "note": (
                "Si ves 'simulated: true' en los resultados de Composio, configura COMPOSIO_API_KEY "
                "y completa el onboarding OAuth en el panel de Composio para tener ejecución REAL "
                "dentro de Meta/TikTok."
            ),
        }

    # ============================================
    # AGENTIC AI – Google Ads & Meta Ads (Autonomous Ads)
    # ============================================

    def run_agentic_ads_workflow(
        self,
        platform: str,
        business_objective: str,
        kpi: str,
        daily_budget: float,
        audience_description: Optional[str] = None,
        advisory_mode: bool = True,
    ) -> Dict[str, Any]:
        """
        Ejecuta un flujo agentic para Google Ads / Meta Ads usando AdvertisingTool como capa de acción.

        Args:
            platform: "google_ads" o "meta"
            business_objective: Objetivo de negocio (ej: "maximizar ROAS", "bajar CPA a 20€")
            kpi: KPI principal (ej: "ROAS", "CPA", "leads", "ventas")
            daily_budget: Presupuesto diario aproximado
            audience_description: Descripción libre de la audiencia
            advisory_mode: Si True, el agente solo recomienda cambios; si False, intenta aplicarlos.
        """
        # 1) Generar plan de alto nivel con LLM (orquestador)
        try:
            prompt = f"""
Eres un orquestador de Agentic AI especializado en campañas de pago en Google Ads y Meta Ads.

Plataforma principal: {platform}
Objetivo de negocio: {business_objective}
KPI principal: {kpi}
Presupuesto diario aprox.: {daily_budget} EUR
Audiencia: {audience_description or "no especificada"}
Modo: {"ASESOR (solo recomendaciones, sin acciones directas)" if advisory_mode else "AUTÓNOMO (puede proponer y ejecutar cambios)"}

1. Resume la estrategia en 3-5 frases.
2. Define 3-7 acciones concretas a nivel de campañas/anuncios:
   - tipo: "create_campaign" | "optimize_campaign" | "analyze_performance"
   - nombre_campaña (si aplica)
   - plataforma: "google_ads" o "meta"
   - presupuesto_sugerido (número)
   - objetivo (texto corto)
3. Indica qué acciones deberían ser AUTO ejecutadas y cuáles solo sugeridas.

Devuelve SOLO JSON:
{{
  "strategy_summary": "...",
  "actions": [
    {{
      "type": "create_campaign",
      "campaign_name": "Performance Max - Brand X",
      "platform": "{platform}",
      "budget": {daily_budget},
      "objective": "conversions",
      "auto_execute": {str(not advisory_mode).lower()}
    }}
  ]
}}
"""
            response = self.llm.invoke(prompt)
            import re

            json_match = re.search(r"\{.*\}", response.content, re.DOTALL)
            if json_match:
                plan = json.loads(json_match.group())
            else:
                plan = {
                    "strategy_summary": f"Estrategia básica para {platform} con objetivo: {business_objective}",
                    "actions": [],
                }
        except Exception as e:
            plan = {
                "strategy_summary": f"⚠️ No se pudo generar plan con IA: {e}",
                "actions": [],
            }

        executed_actions: List[Dict[str, Any]] = []
        recommended_actions: List[Dict[str, Any]] = []

        # 2) Ejecutar acciones vía AdvertisingTool según guardrails (advisory_mode)
        for act in plan.get("actions", []):
            act_type = act.get("type", "analyze_performance")
            act_platform = act.get("platform", platform)
            act_campaign = act.get("campaign_name") or "AI_Autonomous_Campaign"
            act_budget = float(act.get("budget", daily_budget))
            act_objective = act.get("objective", "conversions")
            auto_exec = bool(act.get("auto_execute", False)) and not advisory_mode

            # Siempre añadimos a recomendaciones
            recommended_actions.append(
                {
                    "type": act_type,
                    "platform": act_platform,
                    "campaign_name": act_campaign,
                    "budget": act_budget,
                    "objective": act_objective,
                    "auto_execute_requested": auto_exec,
                }
            )

            if not auto_exec:
                # Solo recomendar, no ejecutar
                continue

            # Mapear al tool AdvertisingTool
            try:
                if act_type == "create_campaign":
                    tool_res = self.advertising_tool.execute(
                        action="create_campaign",
                        campaign_name=act_campaign,
                        platform=act_platform,
                        budget=act_budget,
                        objective=act_objective,
                        audience={"description": audience_description or ""},
                        creative_content=f"Autonomous campaign for: {business_objective} ({kpi})",
                    )
                elif act_type == "optimize_campaign":
                    tool_res = self.advertising_tool.execute(
                        action="optimize_campaign",
                        campaign_name=act_campaign,
                        optimization_goal=f"{business_objective} / {kpi}",
                    )
                else:  # analyze_performance u otros
                    tool_res = self.advertising_tool.execute(
                        action="analyze_performance",
                        campaign_name=act_campaign,
                    )

                executed_actions.append(
                    {
                        "requested": {
                            "type": act_type,
                            "platform": act_platform,
                            "campaign_name": act_campaign,
                        },
                        "tool_result": {
                            "success": tool_res.success,
                            "message": tool_res.message,
                            "metadata": tool_res.metadata,
                        },
                    }
                )
            except Exception as e:
                executed_actions.append(
                    {
                        "requested": {
                            "type": act_type,
                            "platform": act_platform,
                            "campaign_name": act_campaign,
                        },
                        "tool_result": {
                            "success": False,
                            "message": f"Error ejecutando acción: {e}",
                            "metadata": {},
                        },
                    }
                )

        return {
            "success": True,
            "platform": platform,
            "business_objective": business_objective,
            "kpi": kpi,
            "daily_budget": daily_budget,
            "audience_description": audience_description,
            "advisory_mode": advisory_mode,
            "strategy_summary": plan.get("strategy_summary", ""),
            "actions_recommended": recommended_actions,
            "actions_executed": executed_actions,
        }

