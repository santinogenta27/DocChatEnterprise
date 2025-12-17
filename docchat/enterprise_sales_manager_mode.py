"""
Enterprise Sales Manager Mode - Sistema Autónomo de Ventas Orientado a ROI
PRODUCTION-GRADE IMPLEMENTATION

Arquitectura Multi-Agente para Ventas:
- LangGraph: Máquina de estado con patrones avanzados (routing, parallelization, reflection)
- CrewAI: Agentes especializados con herramientas y tareas bien definidas
- AutoGen: Comunicación, debate y auto-corrección entre agentes
- BeeAI: Integración con herramientas empresariales y extensibilidad

Agentes Especializados:
1. LeadQualifierAgent: Califica y prioriza leads usando BANT
2. SalesStrategistAgent: Define estrategias de ventas personalizadas
3. OutreachAgent: Ejecuta campañas multi-canal (email, LinkedIn, phone)
4. NegotiationAgent: Maneja negociaciones complejas
5. ClosingAgent: Cierra ventas identificando señales de compra
6. SalesAnalystAgent: Analiza performance y optimiza continuamente

Workflow LangGraph con Patrones Avanzados:
START -> Router (Lead Type) -> [Parallel: Qualification + Research] -> 
Strategy Planning -> [Reflection Loop] -> Outreach -> 
Negotiation -> Closing -> Analysis -> END

MVP: Ads Agent para ventas de e-commerce
V2: Integración completa con CRM, plataformas de ads, y analytics
"""

from __future__ import annotations

import json
import os
import time
import uuid
import asyncio
import logging
from typing import Any, Dict, List, Optional, TypedDict, Annotated, Literal
from datetime import datetime
from pathlib import Path
from enum import Enum
from dataclasses import dataclass, asdict
from collections import defaultdict
import operator
import traceback

# LangGraph imports
try:
    from langgraph.graph import StateGraph, END, START
    from langgraph.types import Send
    from langgraph.checkpoint.memory import MemorySaver
    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False
    print("⚠️ LangGraph no está instalado. Instala con: pip install langgraph")

# CrewAI imports
try:
    from crewai import Agent, Task, Crew, Process, LLM
    from crewai.tools import BaseTool
    from crewai_tools import SerperDevTool, WebsiteSearchTool
    CREWAI_AVAILABLE = True
except ImportError:
    CREWAI_AVAILABLE = False
    print("⚠️ CrewAI no está instalado. Instala con: pip install crewai crewai-tools")

# AutoGen imports
try:
    from autogen import ConversableAgent, AssistantAgent, UserProxyAgent, GroupChat, GroupChatManager
    from autogen.llm_config import LLMConfig
    AUTOGEN_AVAILABLE = True
except ImportError:
    AUTOGEN_AVAILABLE = False
    print("⚠️ AutoGen no está instalado. Instala con: pip install autogen")

# BeeAI imports
try:
    from beeai_framework.agents.experimental import RequirementAgent
    from beeai_framework.memory import UnconstrainedMemory
    from beeai_framework.backend import ChatModel, ChatModelParameters
    from beeai_framework.tools import Tool, StringToolOutput, ToolRunOptions
    from beeai_framework.context import RunContext
    from beeai_framework.middleware.trajectory import GlobalTrajectoryMiddleware
    BEEAI_AVAILABLE = True
except ImportError:
    BEEAI_AVAILABLE = False
    print("⚠️ BeeAI Framework no está instalado. Instala con: pip install beeai-framework")

from pydantic import BaseModel, Field
from langchain_core.language_models import BaseLanguageModel
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_core.documents import Document

from .config import AppConfig
from .document_processor import DocumentProcessor
from .retriever_builder import RetrieverBuilder
from .memory import MemoryStore, ContextManager

# Configurar logging
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


# ============================================
# MODELOS DE DATOS
# ============================================

class LeadStatus(str, Enum):
    """Estado del lead."""
    NEW = "new"
    QUALIFIED = "qualified"
    CONTACTED = "contacted"
    NEGOTIATING = "negotiating"
    CLOSED_WON = "closed_won"
    CLOSED_LOST = "closed_lost"
    NURTURING = "nurturing"


class SalesStage(str, Enum):
    """Etapas del proceso de ventas."""
    DISCOVERY = "discovery"
    QUALIFICATION = "qualification"
    PROPOSAL = "proposal"
    NEGOTIATION = "negotiation"
    CLOSING = "closing"
    POST_SALE = "post_sale"


@dataclass
class Lead:
    """Lead de ventas."""
    lead_id: str
    name: str
    email: str
    company: Optional[str] = None
    phone: Optional[str] = None
    status: LeadStatus = LeadStatus.NEW
    score: float = 0.0
    source: str = "unknown"
    metadata: Dict[str, Any] = None
    created_at: str = ""
    updated_at: str = ""


@dataclass
class SalesStrategy:
    """Estrategia de ventas generada."""
    strategy_id: str
    lead_id: str
    approach: str  # "cold_outreach", "warm_introduction", "content_marketing", etc.
    messaging: Dict[str, str]  # email_template, linkedin_template, etc.
    channels: List[str]  # ["email", "linkedin", "phone"]
    timeline: Dict[str, Any]
    expected_outcome: str
    reasoning: str


@dataclass
class OutreachResult:
    """Resultado de outreach."""
    outreach_id: str
    lead_id: str
    channel: str
    status: str  # "sent", "opened", "clicked", "replied", "bounced"
    response: Optional[str] = None
    timestamp: str = ""


@dataclass
class SalesMetrics:
    """Métricas de ventas."""
    total_leads: int = 0
    qualified_leads: int = 0
    contacted_leads: int = 0
    meetings_booked: int = 0
    proposals_sent: int = 0
    closed_won: int = 0
    closed_lost: int = 0
    revenue: float = 0.0
    conversion_rate: float = 0.0
    avg_deal_size: float = 0.0
    sales_cycle_days: float = 0.0


# ============================================
# LANGGRAPH STATE DEFINITION
# ============================================

class SalesState(TypedDict):
    """Estado del workflow de ventas en LangGraph con patrones avanzados."""
    lead: Lead
    lead_type: str  # "enterprise", "smb", "consumer" - para routing
    qualification_score: float
    research_data: Dict[str, Any]  # Datos de investigación paralela
    strategy: Optional[SalesStrategy]
    strategy_evaluation: str  # Para reflection pattern
    outreach_results: Annotated[List[OutreachResult], operator.add]
    negotiation_notes: str
    closing_status: str
    metrics: SalesMetrics
    errors: Annotated[List[str], operator.add]
    iteration_count: int
    reflection_count: int  # Para reflection loop


# ============================================
# STUBS PARA APIs EXTERNAS
# ============================================

class CRMStub:
    """Stub para integración con CRM (Salesforce, HubSpot, etc.)."""
    
    def create_lead(self, lead: Lead) -> Dict[str, Any]:
        """Crea un lead en el CRM."""
        return {
            "crm_id": f"crm_{uuid.uuid4().hex[:8]}",
            "status": "created",
            "lead": asdict(lead)
        }
    
    def update_lead_status(self, lead_id: str, status: LeadStatus) -> Dict[str, Any]:
        """Actualiza el estado de un lead."""
        return {
            "lead_id": lead_id,
            "new_status": status.value,
            "updated_at": datetime.now().isoformat()
        }
    
    def get_lead(self, lead_id: str) -> Optional[Dict[str, Any]]:
        """Obtiene información de un lead."""
        return {
            "lead_id": lead_id,
            "status": "active",
            "data": {}
        }


class AdsPlatformStub:
    """Stub para plataformas de anuncios (Meta Ads, Google Ads, etc.)."""
    
    def create_campaign(self, campaign_config: Dict[str, Any]) -> Dict[str, Any]:
        """Crea una campaña de anuncios."""
        return {
            "campaign_id": f"ads_{uuid.uuid4().hex[:8]}",
            "status": "active",
            "budget": campaign_config.get("budget", 0),
            "platform": campaign_config.get("platform", "meta_ads")
        }
    
    def get_campaign_metrics(self, campaign_id: str) -> Dict[str, Any]:
        """Obtiene métricas de una campaña."""
        return {
            "campaign_id": campaign_id,
            "impressions": 10000,
            "clicks": 500,
            "conversions": 25,
            "spend": 150.0,
            "roas": 3.5
        }


class EmailPlatformStub:
    """Stub para plataforma de email marketing."""
    
    def send_email(self, to: str, subject: str, body: str) -> Dict[str, Any]:
        """Envía un email."""
        return {
            "email_id": f"email_{uuid.uuid4().hex[:8]}",
            "status": "sent",
            "to": to,
            "timestamp": datetime.now().isoformat()
        }
    
    def track_email(self, email_id: str) -> Dict[str, Any]:
        """Rastrea el estado de un email."""
        return {
            "email_id": email_id,
            "opened": True,
            "clicked": False,
            "replied": False
        }


# ============================================
# CREWAI AGENTS - AGENTES ESPECIALIZADOS
# ============================================

class SalesAgentFactory:
    """Factory para crear agentes de ventas con CrewAI y herramientas."""
    
    def __init__(self, config: AppConfig, llm: BaseLanguageModel):
        self.config = config
        self.llm = llm
        self.tools = self._get_available_tools()
    
    def _get_available_tools(self) -> List[Any]:
        """Obtiene herramientas disponibles para los agentes."""
        tools = []
        if CREWAI_AVAILABLE:
            try:
                # Herramienta de búsqueda web para investigación
                if os.getenv("SERPER_API_KEY"):
                    tools.append(SerperDevTool())
                # WebsiteSearchTool para investigación de empresas
                tools.append(WebsiteSearchTool())
            except Exception as e:
                logger.warning(f"No se pudieron cargar todas las herramientas: {e}")
        return tools
    
    def create_lead_qualifier(self) -> Agent:
        """Crea agente especializado en calificación de leads con herramientas."""
        return Agent(
            role="Lead Qualification Specialist",
            goal="Calificar y priorizar leads basándose en fit de producto, presupuesto, autoridad y necesidad (BANT)",
            backstory="""Eres un experto en calificación de leads con años de experiencia.
            Tu trabajo es determinar qué leads tienen mayor probabilidad de convertirse en clientes.
            Evalúas Budget (presupuesto), Authority (autoridad), Need (necesidad) y Timeline (tiempo).
            Priorizas leads con alto score para maximizar ROI.
            Usas herramientas de investigación para validar información del lead.""",
            verbose=True,
            allow_delegation=False,
            llm=self.llm,
            tools=self.tools
        )
    
    def create_sales_strategist(self) -> Agent:
        """Crea agente especializado en estrategias de ventas con herramientas."""
        return Agent(
            role="Sales Strategy Architect",
            goal="Diseñar estrategias personalizadas de outreach y ventas para cada lead",
            backstory="""Eres un arquitecto de estrategias de ventas con experiencia en múltiples industrias.
            Diseñas enfoques personalizados basados en el perfil del lead, industria, y etapa del buyer journey.
            Creas mensajes persuasivos y seleccionas los mejores canales para cada situación.
            Investigas tendencias del mercado y mejores prácticas para cada industria.""",
            verbose=True,
            allow_delegation=True,
            llm=self.llm,
            tools=self.tools
        )
    
    def create_outreach_agent(self) -> Agent:
        """Crea agente especializado en outreach con herramientas."""
        return Agent(
            role="Outreach Execution Specialist",
            goal="Ejecutar campañas de outreach multi-canal (email, LinkedIn, phone) de manera efectiva",
            backstory="""Eres un especialista en outreach con track record de altas tasas de respuesta.
            Personalizas cada mensaje para resonar con el prospecto.
            Optimizas timing, tono y contenido para maximizar engagement.
            Investigas el perfil del prospecto para personalizar mejor los mensajes.""",
            verbose=True,
            allow_delegation=False,
            llm=self.llm,
            tools=self.tools
        )
    
    def create_negotiation_agent(self) -> Agent:
        """Crea agente especializado en negociación."""
        return Agent(
            role="Negotiation Expert",
            goal="Manejar negociaciones complejas manteniendo relaciones positivas y maximizando valor",
            backstory="""Eres un negociador experto que encuentra win-win solutions.
            Entiendes las objeciones del cliente y las conviertes en oportunidades.
            Proteges el margen mientras entregas valor al cliente.""",
            verbose=True,
            allow_delegation=True,
            llm=self.llm
        )
    
    def create_closing_agent(self) -> Agent:
        """Crea agente especializado en cierre de ventas."""
        return Agent(
            role="Sales Closer",
            goal="Cerrar ventas de manera efectiva identificando señales de compra y eliminando obstáculos",
            backstory="""Eres un closer de élite con alta tasa de cierre.
            Identificas señales de compra y actúas rápidamente.
            Eliminas objeciones finales y guías al cliente hacia la decisión.""",
            verbose=True,
            allow_delegation=False,
            llm=self.llm
        )
    
    def create_sales_analyst(self) -> Agent:
        """Crea agente especializado en análisis de ventas con herramientas."""
        return Agent(
            role="Sales Performance Analyst",
            goal="Analizar métricas de ventas, identificar patrones y optimizar el proceso continuamente",
            backstory="""Eres un analista de datos de ventas con expertise en optimización de funnels.
            Identificas cuellos de botella, oportunidades de mejora y mejores prácticas.
            Proporcionas insights accionables para mejorar conversión y ROI.
            Investigas benchmarks de la industria para comparar performance.""",
            verbose=True,
            allow_delegation=True,
            llm=self.llm,
            tools=self.tools
        )


# ============================================
# LANGGRAPH WORKFLOW NODES
# ============================================

class SalesWorkflowNodes:
    """Nodos del workflow de LangGraph para ventas con patrones avanzados."""
    
    def __init__(self, config: AppConfig, llm: BaseLanguageModel, crm: CRMStub, ads: AdsPlatformStub, email: EmailPlatformStub):
        self.config = config
        self.llm = llm
        self.crm = crm
        self.ads = ads
        self.email = email
        self.agent_factory = SalesAgentFactory(config, llm)
    
    # ============================================
    # PATRÓN: ROUTING - Clasificar tipo de lead
    # ============================================
    
    def route_lead_type(self, state: SalesState) -> str:
        """Router: Determina el tipo de lead para routing condicional."""
        lead = state["lead"]
        company = lead.company or ""
        email = lead.email or ""
        
        # Lógica de routing basada en dominio de email y nombre de empresa
        if any(keyword in company.lower() for keyword in ["inc", "corp", "llc", "ltd", "enterprise"]):
            return "enterprise"
        elif any(keyword in email.lower() for keyword in ["@gmail.com", "@yahoo.com", "@hotmail.com"]):
            return "consumer"
        else:
            return "smb"
    
    def classify_lead_type(self, state: SalesState) -> SalesState:
        """Nodo: Clasifica el tipo de lead usando LLM."""
        lead = state["lead"]
        
        # Usar LLM para clasificación más precisa
        prompt = f"""Clasifica este lead en una de estas categorías:
        - enterprise: Empresas grandes con múltiples departamentos
        - smb: Pequeñas y medianas empresas
        - consumer: Consumidores individuales
        
        Lead: {lead.name}
        Email: {lead.email}
        Company: {lead.company or 'N/A'}
        
        Responde solo con: enterprise, smb, o consumer"""
        
        try:
            response = self.llm.invoke(prompt)
            lead_type = response.content.strip().lower()
            if lead_type not in ["enterprise", "smb", "consumer"]:
                lead_type = "smb"  # Default
        except Exception as e:
            logger.warning(f"Error en clasificación de lead: {e}")
            lead_type = "smb"
        
        return {
            **state,
            "lead_type": lead_type
        }
    
    # ============================================
    # PATRÓN: PARALLELIZATION - Investigación paralela
    # ============================================
    
    def research_company(self, state: SalesState) -> Dict[str, Any]:
        """Nodo paralelo: Investiga la empresa del lead."""
        lead = state["lead"]
        company = lead.company or ""
        
        if not company:
            return {"research_data": {}}
        
        # Crear agente de investigación
        research_agent = Agent(
            role="Company Research Specialist",
            goal="Investigar información sobre empresas para contexto de ventas",
            backstory="Eres un investigador experto que encuentra información relevante sobre empresas.",
            verbose=False,
            llm=self.llm,
            tools=self.agent_factory.tools
        )
        
        research_task = Task(
            description=f"""Investiga información sobre la empresa: {company}
            Busca: tamaño, industria, productos, noticias recientes, desafíos comunes.""",
            expected_output="Resumen de información de la empresa",
            agent=research_agent
        )
        
        try:
            crew = Crew(
                agents=[research_agent],
                tasks=[research_task],
                process=Process.sequential,
                verbose=False
            )
            result = crew.kickoff()
            
            return {
                "research_data": {
                    "company_info": result.raw[:1000],
                    "timestamp": datetime.now().isoformat()
                }
            }
        except Exception as e:
            logger.error(f"Error en investigación de empresa: {e}")
            return {"research_data": {}}
    
    def research_contact(self, state: SalesState) -> Dict[str, Any]:
        """Nodo paralelo: Investiga el contacto del lead."""
        lead = state["lead"]
        
        # Crear agente de investigación
        research_agent = Agent(
            role="Contact Research Specialist",
            goal="Investigar información sobre contactos para personalización",
            backstory="Eres un investigador experto que encuentra información sobre personas.",
            verbose=False,
            llm=self.llm,
            tools=self.agent_factory.tools
        )
        
        research_task = Task(
            description=f"""Investiga información sobre: {lead.name} ({lead.email})
            Busca: rol, experiencia, intereses profesionales, actividad en redes sociales.""",
            expected_output="Resumen de información del contacto",
            agent=research_agent
        )
        
        try:
            crew = Crew(
                agents=[research_agent],
                tasks=[research_task],
                process=Process.sequential,
                verbose=False
            )
            result = crew.kickoff()
            
            existing_research = state.get("research_data", {})
            existing_research["contact_info"] = result.raw[:1000]
            
            return {"research_data": existing_research}
        except Exception as e:
            logger.error(f"Error en investigación de contacto: {e}")
            return {"research_data": state.get("research_data", {})}
    
    def qualify_lead(self, state: SalesState) -> SalesState:
        """Nodo: Calificar lead con datos de investigación."""
        lead = state["lead"]
        research_data = state.get("research_data", {})
        
        # Crear agente de calificación
        qualifier = self.agent_factory.create_lead_qualifier()
        
        # Incluir datos de investigación en el prompt
        research_context = ""
        if research_data:
            company_info = research_data.get("company_info", "")
            contact_info = research_data.get("contact_info", "")
            if company_info:
                research_context += f"\n\nInformación de la empresa:\n{company_info}"
            if contact_info:
                research_context += f"\n\nInformación del contacto:\n{contact_info}"
        
        # Crear tarea de calificación
        qualification_task = Task(
            description=f"""Califica el siguiente lead usando criterios BANT:
            - Budget: ¿Tiene presupuesto?
            - Authority: ¿Tiene autoridad para decidir?
            - Need: ¿Tiene necesidad real?
            - Timeline: ¿Cuándo necesita la solución?
            
            Lead: {lead.name} ({lead.email})
            Company: {lead.company}
            Source: {lead.source}
            {research_context}
            
            Asigna un score de 0-100 y determina si está calificado.
            Responde en formato JSON: {{"score": 85, "qualified": true, "reasoning": "..."}}""",
            expected_output="Score de calificación (0-100) y recomendación (qualified/not_qualified) en formato JSON",
            agent=qualifier
        )
        
        # Ejecutar calificación
        try:
            crew = Crew(
                agents=[qualifier],
                tasks=[qualification_task],
                process=Process.sequential,
                verbose=False
            )
            
            result = crew.kickoff()
            
            # Parsear resultado JSON
            try:
                # Intentar extraer JSON del resultado
                result_text = result.raw
                # Buscar JSON en el texto
                import re
                json_match = re.search(r'\{[^{}]*"score"[^{}]*\}', result_text)
                if json_match:
                    qual_data = json.loads(json_match.group())
                    score = qual_data.get("score", 50.0)
                    qualified = qual_data.get("qualified", False)
                else:
                    # Fallback: buscar números en el texto
                    score_match = re.search(r'score[:\s]+(\d+)', result_text, re.IGNORECASE)
                    score = float(score_match.group(1)) if score_match else 50.0
                    qualified = "qualified" in result_text.lower() or score >= 70
            except Exception as e:
                logger.warning(f"Error parseando resultado de calificación: {e}")
                score = 50.0
                qualified = "qualified" in result.raw.lower()
            
            if qualified and score >= 70:
                lead.status = LeadStatus.QUALIFIED
                lead.score = score
            else:
                lead.status = LeadStatus.NURTURING
                lead.score = score
            
            # Actualizar en CRM
            self.crm.update_lead_status(lead.lead_id, lead.status)
            
            return {
                **state,
                "lead": lead,
                "qualification_score": score,
                "iteration_count": state.get("iteration_count", 0) + 1
            }
        except Exception as e:
            logger.error(f"Error en calificación de lead: {e}")
            return {
                **state,
                "errors": state.get("errors", []) + [f"Error en calificación: {str(e)}"],
                "lead": lead
            }
    
    def plan_strategy(self, state: SalesState) -> SalesState:
        """Nodo: Planificar estrategia de ventas con datos de investigación."""
        lead = state["lead"]
        research_data = state.get("research_data", {})
        lead_type = state.get("lead_type", "smb")
        
        if lead.status != LeadStatus.QUALIFIED:
            return {**state, "errors": state.get("errors", []) + ["Lead no calificado para estrategia"]}
        
        # Crear agente de estrategia
        strategist = self.agent_factory.create_sales_strategist()
        
        # Incluir contexto de investigación
        research_context = ""
        if research_data:
            company_info = research_data.get("company_info", "")
            contact_info = research_data.get("contact_info", "")
            if company_info:
                research_context += f"\n\nInformación de la empresa:\n{company_info}"
            if contact_info:
                research_context += f"\n\nInformación del contacto:\n{contact_info}"
        
        strategy_task = Task(
            description=f"""Diseña una estrategia de ventas personalizada para:
            Lead: {lead.name} ({lead.email})
            Company: {lead.company}
            Score: {lead.score}
            Tipo: {lead_type}
            {research_context}
            
            Define:
            1. Enfoque de outreach (cold/warm) basado en el tipo de lead
            2. Canales a usar (email, LinkedIn, phone) según preferencias del lead
            3. Mensajes personalizados usando la información de investigación
            4. Timeline de ejecución apropiado para {lead_type}
            5. Resultado esperado
            
            Responde en formato estructurado con secciones claras.""",
            expected_output="Estrategia completa de ventas con mensajes y timeline en formato estructurado",
            agent=strategist
        )
        
        try:
            crew = Crew(
                agents=[strategist],
                tasks=[strategy_task],
                process=Process.sequential,
                verbose=False
            )
            
            result = crew.kickoff()
            
            # Extraer información de la estrategia (mejorable con parsing más robusto)
            strategy_text = result.raw
            
            # Determinar canales basado en el tipo de lead
            if lead_type == "enterprise":
                channels = ["email", "linkedin", "phone"]
            elif lead_type == "smb":
                channels = ["email", "linkedin"]
            else:
                channels = ["email"]
            
            # Crear estrategia
            strategy = SalesStrategy(
                strategy_id=f"strategy_{uuid.uuid4().hex[:8]}",
                lead_id=lead.lead_id,
                approach=f"{lead_type}_outreach",
                messaging={
                    "email_template": self._extract_email_template(strategy_text),
                    "linkedin_template": self._extract_linkedin_template(strategy_text)
                },
                channels=channels,
                timeline={
                    "start": datetime.now().isoformat(),
                    "follow_up_days": 3 if lead_type == "enterprise" else 2
                },
                expected_outcome="meeting_booked",
                reasoning=strategy_text[:2000]
            )
            
            return {
                **state,
                "strategy": strategy,
                "iteration_count": state.get("iteration_count", 0) + 1
            }
        except Exception as e:
            logger.error(f"Error en planificación de estrategia: {e}")
            return {
                **state,
                "errors": state.get("errors", []) + [f"Error en estrategia: {str(e)}"]
            }
    
    def _extract_email_template(self, text: str) -> str:
        """Extrae template de email del texto."""
        # Buscar sección de email
        email_keywords = ["email", "correo", "mensaje email"]
        for keyword in email_keywords:
            if keyword.lower() in text.lower():
                # Intentar extraer el template
                parts = text.split(keyword, 1)
                if len(parts) > 1:
                    return parts[1][:500]
        return text[:500]  # Fallback
    
    def _extract_linkedin_template(self, text: str) -> str:
        """Extrae template de LinkedIn del texto."""
        # Buscar sección de LinkedIn
        linkedin_keywords = ["linkedin", "linkedin message"]
        for keyword in linkedin_keywords:
            if keyword.lower() in text.lower():
                parts = text.split(keyword, 1)
                if len(parts) > 1:
                    return parts[1][:500]
        return ""
    
    def execute_outreach(self, state: SalesState) -> SalesState:
        """Nodo: Ejecutar outreach."""
        lead = state["lead"]
        strategy = state.get("strategy")
        
        if not strategy:
            return {**state, "errors": state.get("errors", []) + ["No hay estrategia para ejecutar"]}
        
        # Crear agente de outreach
        outreach_agent = self.agent_factory.create_outreach_agent()
        
        outreach_task = Task(
            description=f"""Ejecuta outreach para {lead.name} usando la estrategia definida.
            Canales: {', '.join(strategy.channels)}
            Personaliza los mensajes según el perfil del lead.""",
            expected_output="Confirmación de outreach ejecutado con detalles",
            agent=outreach_agent
        )
        
        crew = Crew(
            agents=[outreach_agent],
            tasks=[outreach_task],
            process=Process.sequential,
            verbose=False
        )
        
        result = crew.kickoff()
        
        # Ejecutar outreach real (stubs)
        outreach_results = []
        for channel in strategy.channels:
            if channel == "email":
                email_result = self.email.send_email(
                    to=lead.email,
                    subject=f"Oportunidad para {lead.company}",
                    body=strategy.messaging.get("email_template", "")
                )
                outreach_results.append(OutreachResult(
                    outreach_id=email_result["email_id"],
                    lead_id=lead.lead_id,
                    channel="email",
                    status="sent",
                    timestamp=email_result["timestamp"]
                ))
        
        return {
            **state,
            "outreach_results": state.get("outreach_results", []) + outreach_results,
            "lead": Lead(**{**asdict(lead), "status": LeadStatus.CONTACTED}),
            "iteration_count": state.get("iteration_count", 0) + 1
        }
    
    def handle_negotiation(self, state: SalesState) -> SalesState:
        """Nodo: Manejar negociación."""
        lead = state["lead"]
        
        if lead.status != LeadStatus.CONTACTED:
            return state
        
        # Crear agente de negociación
        negotiator = self.agent_factory.create_negotiation_agent()
        
        negotiation_task = Task(
            description=f"""Maneja la negociación con {lead.name}.
            Objetivo: Llegar a un acuerdo win-win.
            Considera objeciones comunes y prepárate para contraofertas.""",
            expected_output="Notas de negociación y recomendaciones",
            agent=negotiator
        )
        
        crew = Crew(
            agents=[negotiator],
            tasks=[negotiation_task],
            process=Process.sequential,
            verbose=False
        )
        
        result = crew.kickoff()
        
        return {
            **state,
            "negotiation_notes": result.raw,
            "lead": Lead(**{**asdict(lead), "status": LeadStatus.NEGOTIATING}),
            "iteration_count": state.get("iteration_count", 0) + 1
        }
    
    def close_sale(self, state: SalesState) -> SalesState:
        """Nodo: Cerrar venta."""
        lead = state["lead"]
        
        if lead.status not in [LeadStatus.NEGOTIATING, LeadStatus.CONTACTED]:
            return state
        
        # Crear agente de cierre
        closer = self.agent_factory.create_closing_agent()
        
        closing_task = Task(
            description=f"""Cierra la venta con {lead.name}.
            Identifica señales de compra y elimina obstáculos finales.
            Guía hacia la decisión positiva.""",
            expected_output="Estado de cierre (won/lost) y razones",
            agent=closer
        )
        
        crew = Crew(
            agents=[closer],
            tasks=[closing_task],
            process=Process.sequential,
            verbose=False
        )
        
        result = crew.kickoff()
        
        # Determinar resultado
        if "won" in result.raw.lower() or "closed" in result.raw.lower():
            closing_status = "won"
            lead.status = LeadStatus.CLOSED_WON
        else:
            closing_status = "lost"
            lead.status = LeadStatus.CLOSED_LOST
        
        # Actualizar CRM
        self.crm.update_lead_status(lead.lead_id, lead.status)
        
        return {
            **state,
            "closing_status": closing_status,
            "lead": lead,
            "iteration_count": state.get("iteration_count", 0) + 1
        }
    
    # ============================================
    # PATRÓN: REFLECTION - Evaluar y mejorar estrategia
    # ============================================
    
    def evaluate_strategy(self, state: SalesState) -> SalesState:
        """Nodo: Evalúa la estrategia usando reflection pattern."""
        strategy = state.get("strategy")
        lead = state["lead"]
        
        if not strategy:
            return state
        
        # Crear agente evaluador
        evaluator = Agent(
            role="Strategy Evaluator",
            goal="Evaluar estrategias de ventas y proporcionar feedback constructivo",
            backstory="Eres un evaluador experto que analiza estrategias de ventas y sugiere mejoras.",
            verbose=False,
            llm=self.llm
        )
        
        evaluation_task = Task(
            description=f"""Evalúa esta estrategia de ventas:
            Lead: {lead.name} ({lead.email})
            Company: {lead.company}
            Tipo: {state.get('lead_type', 'smb')}
            Score: {state.get('qualification_score', 0)}
            
            Estrategia:
            Enfoque: {strategy.approach}
            Canales: {', '.join(strategy.channels)}
            Reasoning: {strategy.reasoning[:500]}
            
            Evalúa:
            1. ¿Es apropiada para el tipo de lead?
            2. ¿Los canales son correctos?
            3. ¿El mensaje es persuasivo?
            4. ¿Qué mejoras sugerirías?
            
            Responde: APPROVED o NEEDS_IMPROVEMENT con razones.""",
            expected_output="Evaluación de estrategia con recomendaciones",
            agent=evaluator
        )
        
        try:
            crew = Crew(
                agents=[evaluator],
                tasks=[evaluation_task],
                process=Process.sequential,
                verbose=False
            )
            
            result = crew.kickoff()
            evaluation_text = result.raw
            
            # Determinar si necesita mejora
            needs_improvement = "needs_improvement" in evaluation_text.lower() or "improve" in evaluation_text.lower()
            
            return {
                **state,
                "strategy_evaluation": evaluation_text,
                "reflection_count": state.get("reflection_count", 0) + 1
            }
        except Exception as e:
            logger.error(f"Error en evaluación de estrategia: {e}")
            return {
                **state,
                "strategy_evaluation": "Error en evaluación",
                "errors": state.get("errors", []) + [f"Error en evaluación: {str(e)}"]
            }
    
    def improve_strategy(self, state: SalesState) -> SalesState:
        """Nodo: Mejora la estrategia basado en evaluación."""
        strategy = state.get("strategy")
        evaluation = state.get("strategy_evaluation", "")
        lead = state["lead"]
        
        if not strategy or not evaluation:
            return state
        
        # Crear agente mejorador
        improver = self.agent_factory.create_sales_strategist()
        
        improvement_task = Task(
            description=f"""Mejora esta estrategia de ventas basándote en la evaluación:
            
            Estrategia actual:
            {strategy.reasoning[:1000]}
            
            Evaluación:
            {evaluation}
            
            Lead: {lead.name} ({lead.email})
            Company: {lead.company}
            
            Crea una versión mejorada de la estrategia incorporando las sugerencias.""",
            expected_output="Estrategia mejorada con cambios específicos",
            agent=improver
        )
        
        try:
            crew = Crew(
                agents=[improver],
                tasks=[improvement_task],
                process=Process.sequential,
                verbose=False
            )
            
            result = crew.kickoff()
            
            # Actualizar estrategia con mejoras
            improved_strategy = SalesStrategy(
                strategy_id=strategy.strategy_id,
                lead_id=strategy.lead_id,
                approach=strategy.approach,
                messaging=strategy.messaging,  # Mejorar templates
                channels=strategy.channels,
                timeline=strategy.timeline,
                expected_outcome=strategy.expected_outcome,
                reasoning=f"{strategy.reasoning}\n\nMEJORAS APLICADAS:\n{result.raw[:1000]}"
            )
            
            return {
                **state,
                "strategy": improved_strategy,
                "reflection_count": state.get("reflection_count", 0)
            }
        except Exception as e:
            logger.error(f"Error mejorando estrategia: {e}")
            return state
    
    def analyze_performance(self, state: SalesState) -> SalesState:
        """Nodo: Analizar performance."""
        # Crear agente de análisis
        analyst = self.agent_factory.create_sales_analyst()
        
        analysis_task = Task(
            description=f"""Analiza el performance del proceso de ventas para el lead {state['lead'].lead_id}.
            Evalúa:
            - Efectividad de cada etapa
            - Tiempo en cada etapa
            - Conversión final
            - Oportunidades de mejora
            - Comparación con benchmarks de la industria""",
            expected_output="Análisis completo con métricas y recomendaciones",
            agent=analyst
        )
        
        try:
            crew = Crew(
                agents=[analyst],
                tasks=[analysis_task],
                process=Process.sequential,
                verbose=False
            )
            
            result = crew.kickoff()
            
            # Actualizar métricas
            metrics = state.get("metrics", SalesMetrics())
            if state["lead"].status == LeadStatus.CLOSED_WON:
                metrics.closed_won += 1
            elif state["lead"].status == LeadStatus.CLOSED_LOST:
                metrics.closed_lost += 1
            
            return {
                **state,
                "metrics": metrics,
                "iteration_count": state.get("iteration_count", 0) + 1
            }
        except Exception as e:
            logger.error(f"Error en análisis de performance: {e}")
            return {
                **state,
                "errors": state.get("errors", []) + [f"Error en análisis: {str(e)}"]
            }


# ============================================
# AUTOGEN INTEGRATION - DEBATE Y AUTO-CORRECCIÓN
# ============================================

class AutoGenSalesDebate:
    """Sistema de debate AutoGen para mejorar decisiones de ventas."""
    
    def __init__(self, config: AppConfig, llm_config: LLMConfig):
        self.config = config
        self.llm_config = llm_config
    
    def debate_strategy(self, lead: Lead, initial_strategy: SalesStrategy) -> SalesStrategy:
        """Usa AutoGen para debatir y mejorar la estrategia."""
        if not AUTOGEN_AVAILABLE:
            return initial_strategy
        
        # Crear agentes para debate
        strategist_1 = ConversableAgent(
            name="conservative_strategist",
            system_message="Eres un estratega conservador. Prefieres enfoques probados y de bajo riesgo.",
            llm_config=self.llm_config,
            human_input_mode="NEVER"
        )
        
        strategist_2 = ConversableAgent(
            name="aggressive_strategist",
            system_message="Eres un estratega agresivo. Prefieres enfoques innovadores y de alto impacto.",
            llm_config=self.llm_config,
            human_input_mode="NEVER"
        )
        
        # Crear GroupChat para debate
        groupchat = GroupChat(
            agents=[strategist_1, strategist_2],
            messages=[],
            max_round=3,
            speaker_selection_method="auto"
        )
        
        manager = GroupChatManager(
            name="debate_manager",
            groupchat=groupchat,
            llm_config=self.llm_config
        )
        
        # Iniciar debate
        debate_prompt = f"""Debatan la mejor estrategia de ventas para:
        Lead: {lead.name} ({lead.email})
        Company: {lead.company}
        Score: {lead.score}
        
        Estrategia inicial: {initial_strategy.approach}
        
        Mejoren la estrategia considerando ambos puntos de vista."""
        
        result = strategist_1.initiate_chat(
            recipient=manager,
            message=debate_prompt,
            max_turns=3
        )
        
        # Mejorar estrategia basado en debate
        improved_strategy = SalesStrategy(
            strategy_id=initial_strategy.strategy_id,
            lead_id=initial_strategy.lead_id,
            approach=initial_strategy.approach,
            messaging=initial_strategy.messaging,
            channels=initial_strategy.channels,
            timeline=initial_strategy.timeline,
            expected_outcome=initial_strategy.expected_outcome,
            reasoning=f"{initial_strategy.reasoning}\n\nDebate mejorado: {result.summary}"
        )
        
        return improved_strategy


# ============================================
# BEEAI INTEGRATION - HERRAMIENTAS EMPRESARIALES
# ============================================

class BeeAISalesTools:
    """Herramientas BeeAI para integración empresarial y extensibilidad."""
    
    def __init__(self, config: AppConfig):
        self.config = config
        self.llm = None
        self.agents: Dict[str, RequirementAgent] = {}
        
        if BEEAI_AVAILABLE:
            try:
                # Intentar diferentes providers
                providers = [
                    ("openai", "gpt-4o-mini"),
                    ("watsonx", "ibm/granite-3-3-8b-instruct"),
                ]
                
                for provider, model in providers:
                    try:
                        if provider == "openai":
                            self.llm = ChatModel.from_name(
                                f"openai:{model}",
                                ChatModelParameters(temperature=0)
                            )
                        elif provider == "watsonx":
                            self.llm = ChatModel.from_name(
                                f"watsonx:{model}",
                                ChatModelParameters(temperature=0)
                            )
                        break
                    except Exception:
                        continue
                
                if not self.llm:
                    logger.warning("No se pudo inicializar BeeAI LLM con ningún provider")
            except Exception as e:
                logger.warning(f"Error inicializando BeeAI LLM: {e}")
    
    def create_sales_agent(self, agent_type: str = "general") -> Optional[RequirementAgent]:
        """Crea un agente BeeAI para ventas con diferentes especializaciones."""
        if not BEEAI_AVAILABLE or not self.llm:
            return None
        
        if agent_type in self.agents:
            return self.agents[agent_type]
        
        instructions_map = {
            "general": """Eres un agente de ventas experto.
            Ayudas a calificar leads, crear estrategias y cerrar ventas.
            Siempre priorizas el ROI y la satisfacción del cliente.""",
            
            "qualifier": """Eres un especialista en calificación de leads.
            Evalúas leads usando criterios BANT (Budget, Authority, Need, Timeline).
            Priorizas leads con mayor probabilidad de conversión.""",
            
            "strategist": """Eres un arquitecto de estrategias de ventas.
            Diseñas enfoques personalizados basados en el perfil del lead.
            Creas mensajes persuasivos y seleccionas canales óptimos.""",
            
            "closer": """Eres un closer de élite.
            Identificas señales de compra y eliminas obstáculos finales.
            Guías a los clientes hacia decisiones positivas."""
        }
        
        instructions = instructions_map.get(agent_type, instructions_map["general"])
        
        try:
            from beeai_framework.tools import Tool
            from beeai_framework.middleware.trajectory import GlobalTrajectoryMiddleware
            
            agent = RequirementAgent(
                llm=self.llm,
                tools=[],
                memory=UnconstrainedMemory(),
                instructions=instructions,
                middlewares=[GlobalTrajectoryMiddleware(included=[Tool])]
            )
            
            self.agents[agent_type] = agent
            return agent
        except Exception as e:
            logger.error(f"Error creando agente BeeAI {agent_type}: {e}")
            return None
    
    async def analyze_lead_with_beeai(self, lead: Lead) -> Dict[str, Any]:
        """Usa BeeAI para analizar un lead."""
        agent = self.create_sales_agent("qualifier")
        if not agent:
            return {}
        
        try:
            query = f"""Analiza este lead:
            Nombre: {lead.name}
            Email: {lead.email}
            Empresa: {lead.company or 'N/A'}
            
            Proporciona insights sobre fit de producto y probabilidad de conversión."""
            
            result = await agent.run(query)
            return {
                "analysis": result.answer.text if hasattr(result, 'answer') else str(result),
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error en análisis BeeAI: {e}")
            return {}


# ============================================
# CLASE PRINCIPAL: ENTERPRISE SALES MANAGER
# ============================================

class EnterpriseSalesManagerMode:
    """
    Enterprise Sales Manager - Sistema Autónomo de Ventas
    
    Integra:
    - LangGraph para workflows de estado
    - CrewAI para agentes especializados
    - AutoGen para debate y auto-corrección
    - BeeAI para herramientas empresariales
    """
    
    def __init__(
        self,
        config: AppConfig,
        processor: DocumentProcessor,
        retriever_builder: RetrieverBuilder,
        context_manager: Optional[ContextManager] = None,
        provider: str = "openai"
    ):
        self.config = config
        self.provider = provider
        self.processor = processor
        self.retriever_builder = retriever_builder
        self.context_manager = context_manager
        
        # LLM
        self.llm = self._get_llm_for_provider(provider)
        
        # Stubs para APIs externas
        self.crm = CRMStub()
        self.ads = AdsPlatformStub()
        self.email = EmailPlatformStub()
        
        # Nodos del workflow
        self.workflow_nodes = SalesWorkflowNodes(config, self.llm, self.crm, self.ads, self.email)
        
        # AutoGen para debate (solo si está disponible)
        if AUTOGEN_AVAILABLE:
            from autogen.llm_config import LLMConfig
            llm_config = LLMConfig(api_type="openai", model="gpt-4o-mini")
            self.autogen_debate = AutoGenSalesDebate(config, llm_config)
        else:
            self.autogen_debate = None
        
        # BeeAI
        self.beeai_tools = BeeAISalesTools(config)
        
        # LangGraph workflow
        self.workflow = self._build_langgraph_workflow()
        
        # Almacenamiento
        self.leads: Dict[str, Lead] = {}
        self.strategies: Dict[str, SalesStrategy] = {}
        self.metrics = SalesMetrics()
        
        logger.info("✅ Enterprise Sales Manager Mode inicializado")
        logger.info(f"   - LangGraph: {'✅' if LANGGRAPH_AVAILABLE else '❌'}")
        logger.info(f"   - CrewAI: {'✅' if CREWAI_AVAILABLE else '❌'}")
        logger.info(f"   - AutoGen: {'✅' if AUTOGEN_AVAILABLE else '❌'}")
        logger.info(f"   - BeeAI: {'✅' if BEEAI_AVAILABLE else '❌'}")
        logger.info(f"   - Provider: {provider}")
        logger.info(f"   - Model: {self.llm.model_name if hasattr(self.llm, 'model_name') else 'N/A'}")
    
    def _get_llm_for_provider(self, provider: str) -> BaseLanguageModel:
        """Obtiene LLM según el provider."""
        if provider == "openai":
            return ChatOpenAI(
                model=self.config.agentic_model or "gpt-4o-mini",
                temperature=0.7,
                api_key=self.config.openai_api_key
            )
        elif provider == "anthropic":
            return ChatAnthropic(
                model="claude-3-5-sonnet-20241022",
                temperature=0.7,
                api_key=self.config.anthropic_api_key
            )
        else:
            return ChatOpenAI(model="gpt-4o-mini", temperature=0.7)
    
    def _build_langgraph_workflow(self) -> Optional[StateGraph]:
        """Construye el workflow de LangGraph con patrones avanzados."""
        if not LANGGRAPH_AVAILABLE:
            return None
        
        workflow = StateGraph(SalesState)
        
        # ============================================
        # NODOS DEL WORKFLOW
        # ============================================
        
        # Router: Clasificar tipo de lead
        workflow.add_node("classify_lead_type", self.workflow_nodes.classify_lead_type)
        
        # Parallel: Investigación en paralelo
        workflow.add_node("research_company", self.workflow_nodes.research_company)
        workflow.add_node("research_contact", self.workflow_nodes.research_contact)
        
        # Calificación con datos de investigación
        workflow.add_node("qualify_lead", self.workflow_nodes.qualify_lead)
        
        # Estrategia
        workflow.add_node("plan_strategy", self.workflow_nodes.plan_strategy)
        
        # Reflection: Evaluar y mejorar estrategia
        workflow.add_node("evaluate_strategy", self.workflow_nodes.evaluate_strategy)
        workflow.add_node("improve_strategy", self.workflow_nodes.improve_strategy)
        
        # Ejecución
        workflow.add_node("execute_outreach", self.workflow_nodes.execute_outreach)
        workflow.add_node("handle_negotiation", self.workflow_nodes.handle_negotiation)
        workflow.add_node("close_sale", self.workflow_nodes.close_sale)
        workflow.add_node("analyze_performance", self.workflow_nodes.analyze_performance)
        
        # ============================================
        # FLUJO DEL WORKFLOW CON PATRONES AVANZADOS
        # ============================================
        
        # Entry point
        workflow.set_entry_point("classify_lead_type")
        
        # Después de clasificar, investigación en paralelo
        workflow.add_edge("classify_lead_type", "research_company")
        workflow.add_edge("classify_lead_type", "research_contact")
        
        # Después de investigación paralela, calificar
        workflow.add_edge("research_company", "qualify_lead")
        workflow.add_edge("research_contact", "qualify_lead")
        
        # Calificación -> Estrategia
        workflow.add_edge("qualify_lead", "plan_strategy")
        
        # Reflection loop: Evaluar estrategia
        workflow.add_edge("plan_strategy", "evaluate_strategy")
        
        # Routing condicional: Si necesita mejora, mejorar; si no, continuar
        def should_improve_strategy(state: SalesState) -> str:
            """Router: Decide si mejorar la estrategia."""
            evaluation = state.get("strategy_evaluation", "").lower()
            reflection_count = state.get("reflection_count", 0)
            
            # Máximo 2 iteraciones de mejora
            if reflection_count >= 2:
                return "continue"
            
            # Si la evaluación sugiere mejora
            if "needs_improvement" in evaluation or "improve" in evaluation:
                return "improve"
            
            return "continue"
        
        workflow.add_conditional_edges(
            "evaluate_strategy",
            should_improve_strategy,
            {
                "improve": "improve_strategy",
                "continue": "execute_outreach"
            }
        )
        
        # Si mejora, volver a evaluar
        workflow.add_edge("improve_strategy", "evaluate_strategy")
        
        # Flujo principal de ejecución
        workflow.add_edge("execute_outreach", "handle_negotiation")
        workflow.add_edge("handle_negotiation", "close_sale")
        workflow.add_edge("close_sale", "analyze_performance")
        workflow.add_edge("analyze_performance", END)
        
        # Compilar con memory para checkpointing
        try:
            memory = MemorySaver()
            return workflow.compile(checkpointer=memory)
        except Exception as e:
            logger.warning(f"No se pudo usar MemorySaver: {e}. Compilando sin checkpointing.")
            return workflow.compile()
    
    def process_lead(self, lead_data: Dict[str, Any], use_autogen_debate: bool = False) -> Dict[str, Any]:
        """Procesa un lead a través del workflow completo con manejo robusto de errores."""
        start_time = time.time()
        lead_id = None
        
        try:
            # Crear lead
            lead = Lead(
                lead_id=f"lead_{uuid.uuid4().hex[:8]}",
                name=lead_data.get("name", "Unknown"),
                email=lead_data.get("email", ""),
                company=lead_data.get("company"),
                phone=lead_data.get("phone"),
                source=lead_data.get("source", "manual"),
                metadata=lead_data.get("metadata", {}),
                created_at=datetime.now().isoformat(),
                updated_at=datetime.now().isoformat()
            )
            
            lead_id = lead.lead_id
            self.leads[lead.lead_id] = lead
            
            logger.info(f"Procesando lead: {lead.name} ({lead.email}) - ID: {lead_id}")
            
            # Crear estado inicial con todos los campos
            initial_state: SalesState = {
                "lead": lead,
                "lead_type": "",
                "qualification_score": 0.0,
                "research_data": {},
                "strategy": None,
                "strategy_evaluation": "",
                "outreach_results": [],
                "negotiation_notes": "",
                "closing_status": "",
                "metrics": SalesMetrics(),
                "errors": [],
                "iteration_count": 0,
                "reflection_count": 0
            }
            
            # Ejecutar workflow
            if not self.workflow:
                raise Exception("LangGraph workflow no disponible")
            
            logger.info("Iniciando workflow de LangGraph...")
            final_state = self.workflow.invoke(initial_state)
            
            # Aplicar debate AutoGen si está habilitado y hay estrategia
            if use_autogen_debate and final_state.get("strategy") and AUTOGEN_AVAILABLE and self.autogen_debate is not None:
                logger.info("Aplicando debate AutoGen para mejorar estrategia...")
                try:
                    improved_strategy = self.autogen_debate.debate_strategy(
                        final_state["lead"],
                        final_state["strategy"]
                    )
                    final_state["strategy"] = improved_strategy
                    logger.info("Estrategia mejorada con debate AutoGen")
                except Exception as e:
                    logger.warning(f"Error en debate AutoGen: {e}")
            
            # Guardar estrategia si existe
            if final_state.get("strategy"):
                self.strategies[final_state["strategy"].strategy_id] = final_state["strategy"]
            
            # Actualizar métricas globales
            self.metrics.total_leads += 1
            if final_state["lead"].status == LeadStatus.QUALIFIED:
                self.metrics.qualified_leads += 1
            if final_state["lead"].status == LeadStatus.CONTACTED:
                self.metrics.contacted_leads += 1
            if final_state["lead"].status == LeadStatus.CLOSED_WON:
                self.metrics.closed_won += 1
            elif final_state["lead"].status == LeadStatus.CLOSED_LOST:
                self.metrics.closed_lost += 1
            
            processing_time = time.time() - start_time
            
            result = {
                "success": True,
                "lead_id": lead_id,
                "final_status": final_state["lead"].status.value,
                "qualification_score": final_state.get("qualification_score", 0.0),
                "lead_type": final_state.get("lead_type", "smb"),
                "strategy_id": final_state.get("strategy").strategy_id if final_state.get("strategy") else None,
                "strategy_approach": final_state.get("strategy").approach if final_state.get("strategy") else None,
                "outreach_channels": final_state.get("strategy").channels if final_state.get("strategy") else [],
                "reflection_iterations": final_state.get("reflection_count", 0),
                "metrics": asdict(final_state["metrics"]),
                "errors": final_state.get("errors", []),
                "processing_time_seconds": round(processing_time, 2),
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"Lead procesado exitosamente: {lead_id} - Tiempo: {processing_time:.2f}s")
            return result
            
        except Exception as e:
            error_msg = str(e)
            error_trace = traceback.format_exc()
            logger.error(f"Error procesando lead {lead_id}: {error_msg}\n{error_trace}")
            
            return {
                "success": False,
                "error": error_msg,
                "error_trace": error_trace if self.config.debug_mode else None,
                "lead_id": lead_id,
                "timestamp": datetime.now().isoformat()
            }
    
    def get_metrics(self) -> Dict[str, Any]:
        """Obtiene métricas de ventas."""
        return asdict(self.metrics)
    
    def get_lead(self, lead_id: str) -> Optional[Dict[str, Any]]:
        """Obtiene información de un lead."""
        lead = self.leads.get(lead_id)
        if lead:
            return asdict(lead)
        return None


# ============================================
# FUNCIONES DE INTERFAZ
# ============================================

def get_enterprise_sales_manager_mode(
    config: AppConfig,
    processor: DocumentProcessor,
    retriever_builder: RetrieverBuilder,
    context_manager: Optional[ContextManager] = None,
    provider: str = "openai"
) -> EnterpriseSalesManagerMode:
    """Obtiene instancia del modo Enterprise Sales Manager."""
    return EnterpriseSalesManagerMode(
        config=config,
        processor=processor,
        retriever_builder=retriever_builder,
        context_manager=context_manager,
        provider=provider
    )


def run_enterprise_sales_manager_mode(
    sales_manager: EnterpriseSalesManagerMode,
    lead_data: Dict[str, Any]
) -> Dict[str, Any]:
    """Ejecuta el modo Enterprise Sales Manager."""
    return sales_manager.process_lead(lead_data)

