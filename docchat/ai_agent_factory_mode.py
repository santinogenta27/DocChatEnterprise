"""
AI Agent Factory - Plataforma No-Code para Crear AI Agents Personalizados

Basado en la visión de Mark Zuckerberg:
- "Cientos de millones de pequeñas empresas necesitarán AI agents"
- "Más de 200 millones de creadores necesitarán AI agents"
- "Probablemente más AI agents que personas en el mundo"

Características Ultra Útiles:
1. Creación No-Code: Crea agentes en minutos sin programar
2. Templates Avanzados: Para empresas, creadores, influencers, negocios
3. Personalización Profunda: Voz, personalidad, valores, objetivos
4. Deployment Multi-Canal: Web, WhatsApp, Messenger, Instagram, API
5. Marketplace de Agentes: Comparte, clona, mejora agentes de la comunidad
6. Analytics Avanzados: Monitoreo en tiempo real, métricas de engagement
7. Integración Social: Conecta con redes sociales para entrenar agentes
8. Multi-Agent Orchestration: Crea ecosistemas de agentes que colaboran

Arquitectura:
- ReAct Paradigm (Reasoning + Acting)
- BYOA (Bring Your Own Assistant)
- Agent-to-Agent Communication
- Real-time Analytics
- Community-Driven Marketplace
"""

from __future__ import annotations

import json
import time
import asyncio
import uuid
import os
from typing import List, Dict, Optional, Any, Tuple, Callable
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field, asdict
from enum import Enum
from collections import defaultdict

from langchain_core.language_models import BaseLanguageModel
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_openai import ChatOpenAI

try:
    from langchain_anthropic import ChatAnthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    ChatAnthropic = None

try:
    from langchain_google_genai import ChatGoogleGenerativeAI
    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False
    ChatGoogleGenerativeAI = None

from .config import AppConfig
from .mcp_manager import MCPManager


class AgentCategory(Enum):
    """Categorías de agentes."""
    SMALL_BUSINESS = "small_business"  # Pequeñas empresas
    CREATOR = "creator"  # Creadores de contenido
    INFLUENCER = "influencer"  # Influencers
    ENTERPRISE = "enterprise"  # Grandes empresas
    PERSONAL = "personal"  # Uso personal
    COMMUNITY = "community"  # Comunidades
    EDUCATION = "education"  # Educación
    HEALTHCARE = "healthcare"  # Salud
    ECOMMERCE = "ecommerce"  # E-commerce
    CUSTOM = "custom"  # Personalizado


class AgentTemplate(Enum):
    """Templates pre-construidos ultra útiles."""
    # Para Pequeñas Empresas
    CUSTOMER_SERVICE_24_7 = "customer_service_24_7"
    SALES_ASSISTANT = "sales_assistant"
    BOOKING_MANAGER = "booking_manager"
    PRODUCT_RECOMMENDER = "product_recommender"
    FAQ_BOT = "faq_bot"
    
    # Para Creadores
    CREATOR_ASSISTANT = "creator_assistant"
    COMMUNITY_MANAGER = "community_manager"
    CONTENT_PLANNER = "content_planner"
    FAN_INTERACTION = "fan_interaction"
    BRAND_COLLABORATOR = "brand_collaborator"
    
    # Para Influencers
    INFLUENCER_PERSONA = "influencer_persona"
    DM_RESPONDER = "dm_responder"
    CONTENT_CREATOR = "content_creator"
    ENGAGEMENT_BOOSTER = "engagement_booster"
    
    # Para E-commerce
    SHOPPING_ASSISTANT = "shopping_assistant"
    ORDER_TRACKER = "order_tracker"
    RETURN_HANDLER = "return_handler"
    CART_RECOVERY = "cart_recovery"
    
    # Personalizados
    CUSTOM = "custom"


class DeploymentChannel(Enum):
    """Canales de deployment."""
    WEB = "web"
    API = "api"
    WHATSAPP = "whatsapp"
    MESSENGER = "messenger"
    INSTAGRAM = "instagram"
    SLACK = "slack"
    TEAMS = "teams"
    EMAIL = "email"
    SMS = "sms"
    VOICE = "voice"


class LLMProvider(Enum):
    """Proveedores de LLM."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    META_LLAMA = "meta_llama"
    DEEPSEEK = "deepseek"


@dataclass
class AgentPersonality:
    """Personalidad del agente."""
    tone: str  # formal, casual, friendly, professional, etc.
    communication_style: str  # concise, detailed, storytelling, etc.
    humor_level: str  # none, subtle, moderate, high
    empathy_level: str  # low, medium, high
    formality: str  # very_formal, formal, casual, very_casual
    language: str = "es"
    custom_voice_description: Optional[str] = None  # Descripción libre de la voz


@dataclass
class AgentValues:
    """Valores y principios del agente."""
    core_values: List[str]  # Ej: ["transparency", "customer_first", "innovation"]
    brand_voice: str  # Descripción de cómo debe sonar la marca
    do_not_say: List[str]  # Frases o temas a evitar
    must_mention: List[str]  # Frases o temas que siempre debe mencionar
    ethical_guidelines: List[str] = field(default_factory=list)


@dataclass
class SocialIntegration:
    """Integración con redes sociales."""
    platform: str  # instagram, twitter, tiktok, youtube, etc.
    connected: bool = False
    access_token: Optional[str] = None
    last_sync: Optional[str] = None
    content_sources: List[str] = field(default_factory=list)  # Posts, stories, videos, etc.


@dataclass
class AgentConfig:
    """Configuración completa de un agente."""
    agent_id: str
    name: str
    description: str
    category: AgentCategory
    template: AgentTemplate
    system_prompt: str
    personality: AgentPersonality
    values: AgentValues
    llm_provider: LLMProvider
    model: str = "gpt-4o"
    temperature: float = 0.7
    max_tokens: int = 2000
    enabled: bool = True
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    created_by: Optional[str] = None
    social_integrations: List[SocialIntegration] = field(default_factory=list)
    deployment_channels: List[DeploymentChannel] = field(default_factory=list)
    tools: List[str] = field(default_factory=list)
    knowledge_base: List[str] = field(default_factory=list)  # URLs o documentos
    custom_instructions: str = ""
    is_public: bool = False  # Para marketplace
    marketplace_tags: List[str] = field(default_factory=list)
    marketplace_description: str = ""
    clone_count: int = 0  # Cuántas veces ha sido clonado
    rating: float = 0.0  # Rating promedio del marketplace
    usage_count: int = 0  # Número de interacciones


@dataclass
class AgentAnalytics:
    """Analytics de un agente."""
    agent_id: str
    total_interactions: int = 0
    successful_interactions: int = 0
    failed_interactions: int = 0
    average_response_time_ms: float = 0.0
    user_satisfaction_score: float = 0.0
    most_common_queries: List[Dict[str, Any]] = field(default_factory=list)
    channel_breakdown: Dict[str, int] = field(default_factory=dict)
    daily_active_users: int = 0
    retention_rate: float = 0.0
    cost_per_interaction: float = 0.0
    total_cost: float = 0.0
    last_updated: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class MarketplaceAgent:
    """Agente en el marketplace."""
    agent_id: str
    name: str
    description: str
    category: str
    template: str
    creator: str
    tags: List[str]
    rating: float
    clone_count: int
    preview_image: Optional[str] = None
    featured: bool = False


class AIAgentFactory:
    """
    AI Agent Factory - Plataforma No-Code para Crear AI Agents.
    
    Permite a cualquier persona crear, personalizar y desplegar AI agents
    sin necesidad de programar, enfocado en empresas y creadores.
    """
    
    def __init__(
        self,
        config: AppConfig,
        llm: Optional[BaseLanguageModel] = None,
        mcp_manager: Optional[MCPManager] = None
    ):
        self.config = config
        self.llm = llm or ChatOpenAI(
            model="gpt-4o",
            temperature=0.7,
            api_key=config.openai_api_key
        )
        self.mcp_manager = mcp_manager
        
        # Almacenamiento
        self.agents: Dict[str, AgentConfig] = {}
        self.analytics: Dict[str, AgentAnalytics] = {}
        self.marketplace: Dict[str, MarketplaceAgent] = {}
        
        # Directorio de persistencia
        self.storage_dir = Path(config.data_dir) / "ai_agent_factory"
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        # Cargar datos
        self._load_data()
        
        # Inicializar templates
        self._initialize_templates()
        
        print("✅ [AI Agent Factory] Inicializado correctamente")
    
    def _load_data(self):
        """Carga datos guardados."""
        agents_file = self.storage_dir / "agents.json"
        analytics_file = self.storage_dir / "analytics.json"
        marketplace_file = self.storage_dir / "marketplace.json"
        
        if agents_file.exists():
            try:
                with open(agents_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for agent_id, agent_data in data.items():
                        # Convertir dict a AgentConfig
                        agent_data['category'] = AgentCategory(agent_data['category'])
                        agent_data['template'] = AgentTemplate(agent_data['template'])
                        agent_data['llm_provider'] = LLMProvider(agent_data['llm_provider'])
                        agent_data['personality'] = AgentPersonality(**agent_data['personality'])
                        agent_data['values'] = AgentValues(**agent_data['values'])
                        agent_data['social_integrations'] = [
                            SocialIntegration(**si) for si in agent_data.get('social_integrations', [])
                        ]
                        agent_data['deployment_channels'] = [
                            DeploymentChannel(dc) for dc in agent_data.get('deployment_channels', [])
                        ]
                        self.agents[agent_id] = AgentConfig(**agent_data)
                print(f"✅ [AI Agent Factory] Cargados {len(self.agents)} agentes")
            except Exception as e:
                print(f"⚠️ [AI Agent Factory] Error cargando agentes: {e}")
        
        if analytics_file.exists():
            try:
                with open(analytics_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for agent_id, analytics_data in data.items():
                        self.analytics[agent_id] = AgentAnalytics(**analytics_data)
            except Exception as e:
                print(f"⚠️ [AI Agent Factory] Error cargando analytics: {e}")
        
        if marketplace_file.exists():
            try:
                with open(marketplace_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for agent_id, marketplace_data in data.items():
                        self.marketplace[agent_id] = MarketplaceAgent(**marketplace_data)
            except Exception as e:
                print(f"⚠️ [AI Agent Factory] Error cargando marketplace: {e}")
    
    def _save_data(self):
        """Guarda datos."""
        agents_file = self.storage_dir / "agents.json"
        analytics_file = self.storage_dir / "analytics.json"
        marketplace_file = self.storage_dir / "marketplace.json"
        
        try:
            # Guardar agentes
            agents_data = {}
            for agent_id, agent in self.agents.items():
                agent_dict = asdict(agent)
                agent_dict['category'] = agent.category.value
                agent_dict['template'] = agent.template.value
                agent_dict['llm_provider'] = agent.llm_provider.value
                agent_dict['deployment_channels'] = [dc.value for dc in agent.deployment_channels]
                agents_data[agent_id] = agent_dict
            
            with open(agents_file, 'w', encoding='utf-8') as f:
                json.dump(agents_data, f, indent=2, ensure_ascii=False)
            
            # Guardar analytics
            analytics_data = {
                agent_id: asdict(analytics) 
                for agent_id, analytics in self.analytics.items()
            }
            with open(analytics_file, 'w', encoding='utf-8') as f:
                json.dump(analytics_data, f, indent=2, ensure_ascii=False)
            
            # Guardar marketplace
            marketplace_data = {
                agent_id: asdict(marketplace_agent)
                for agent_id, marketplace_agent in self.marketplace.items()
            }
            with open(marketplace_file, 'w', encoding='utf-8') as f:
                json.dump(marketplace_data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            print(f"⚠️ [AI Agent Factory] Error guardando datos: {e}")
    
    def _initialize_templates(self):
        """Inicializa templates pre-construidos."""
        self.templates = {
            # ============================================
            # TEMPLATES PARA PEQUEÑAS EMPRESAS
            # ============================================
            AgentTemplate.CUSTOMER_SERVICE_24_7: {
                "name": "Atención al Cliente 24/7",
                "description": "Agente especializado en atención al cliente que responde consultas, resuelve problemas y guía a los clientes 24 horas al día.",
                "category": AgentCategory.SMALL_BUSINESS,
                "system_prompt": """Eres un agente de atención al cliente profesional y empático. Tu objetivo es ayudar a los clientes de manera rápida y efectiva.

CAPACIDADES:
- Responder preguntas sobre productos y servicios
- Resolver problemas y quejas
- Procesar devoluciones y cambios
- Guiar a los clientes en el proceso de compra
- Escalar casos complejos cuando sea necesario

TONO: Amigable, profesional, empático y proactivo.
Siempre busca resolver el problema del cliente de la mejor manera posible.""",
                "personality": AgentPersonality(
                    tone="friendly",
                    communication_style="helpful",
                    humor_level="subtle",
                    empathy_level="high",
                    formality="casual"
                ),
                "values": AgentValues(
                    core_values=["customer_first", "empathy", "efficiency"],
                    brand_voice="Amigable y profesional, siempre buscando ayudar",
                    do_not_say=["No puedo ayudarte", "Eso no es mi problema"],
                    must_mention=["Estoy aquí para ayudarte", "¿Hay algo más en lo que pueda asistirte?"]
                ),
                "tools": ["query_knowledge_base", "create_ticket", "process_refund", "track_order"]
            },
            
            AgentTemplate.SALES_ASSISTANT: {
                "name": "Asistente de Ventas",
                "description": "Agente que ayuda a calificar leads, recomendar productos y cerrar ventas.",
                "category": AgentCategory.SMALL_BUSINESS,
                "system_prompt": """Eres un asistente de ventas experto. Tu objetivo es ayudar a los clientes a encontrar el producto perfecto y cerrar ventas.

CAPACIDADES:
- Calificar leads y entender necesidades
- Recomendar productos basado en preferencias
- Explicar características y beneficios
- Manejar objeciones comunes
- Crear enlaces de pago y procesar pedidos
- Hacer seguimiento post-venta

TONO: Entusiasta, consultivo, persuasivo pero no agresivo.
Siempre prioriza la satisfacción del cliente sobre la venta.""",
                "personality": AgentPersonality(
                    tone="enthusiastic",
                    communication_style="consultative",
                    humor_level="moderate",
                    empathy_level="high",
                    formality="casual"
                ),
                "values": AgentValues(
                    core_values=["customer_satisfaction", "transparency", "value"],
                    brand_voice="Entusiasta pero honesto, siempre buscando el mejor match",
                    do_not_say=["Tienes que comprar esto", "Es tu última oportunidad"],
                    must_mention=["¿Qué estás buscando exactamente?", "¿Te gustaría que te muestre opciones?"]
                ),
                "tools": ["query_catalog", "calculate_price", "create_payment_link", "send_followup"]
            },
            
            # ============================================
            # TEMPLATES PARA CREADORES
            # ============================================
            AgentTemplate.CREATOR_ASSISTANT: {
                "name": "Asistente para Creadores",
                "description": "Agente que ayuda a creadores a gestionar su comunidad, planificar contenido y responder a fans.",
                "category": AgentCategory.CREATOR,
                "system_prompt": """Eres el asistente personal de un creador de contenido. Tu objetivo es ayudar a gestionar la comunidad y el contenido.

CAPACIDADES:
- Responder mensajes de fans de manera auténtica
- Planificar contenido basado en tendencias
- Analizar engagement y sugerir mejoras
- Gestionar colaboraciones con marcas
- Mantener el tono y voz del creador

TONO: Auténtico, cercano, inspirador.
Refleja la personalidad única del creador.""",
                "personality": AgentPersonality(
                    tone="authentic",
                    communication_style="storytelling",
                    humor_level="moderate",
                    empathy_level="high",
                    formality="very_casual"
                ),
                "values": AgentValues(
                    core_values=["authenticity", "community", "creativity"],
                    brand_voice="Auténtico y cercano, como hablar con un amigo",
                    do_not_say=["Gracias por tu mensaje genérico", "No puedo ayudarte con eso"],
                    must_mention=["¡Gracias por ser parte de esta comunidad!", "Tu apoyo significa mucho"]
                ),
                "tools": ["analyze_engagement", "suggest_content", "respond_to_dm", "schedule_post"]
            },
            
            AgentTemplate.INFLUENCER_PERSONA: {
                "name": "Persona de Influencer",
                "description": "Agente que representa la personalidad del influencer, interactuando con fans como si fuera el influencer mismo.",
                "category": AgentCategory.INFLUENCER,
                "system_prompt": """Eres la personalidad AI de un influencer. Interactúas con fans como si fueras el influencer mismo.

CAPACIDADES:
- Responder DMs y comentarios con la voz del influencer
- Crear contenido que refleje el estilo del influencer
- Mantener engagement constante 24/7
- Construir comunidad y conexión
- Reflejar valores y personalidad únicos

TONO: Exactamente como el influencer - personal, auténtico, único.
Aprende del contenido histórico del influencer para mantener coherencia.""",
                "personality": AgentPersonality(
                    tone="personal",
                    communication_style="conversational",
                    humor_level="high",
                    empathy_level="high",
                    formality="very_casual"
                ),
                "values": AgentValues(
                    core_values=["authenticity", "connection", "positivity"],
                    brand_voice="Exactamente como el influencer - única e irrepetible",
                    do_not_say=["No soy el influencer real", "Solo soy un bot"],
                    must_mention=["¡Gracias por tu apoyo!", "Me encanta conectar contigo"]
                ),
                "tools": ["respond_to_dm", "create_content", "post_to_social", "analyze_engagement"]
            },
            
            # ============================================
            # TEMPLATES PARA E-COMMERCE
            # ============================================
            AgentTemplate.SHOPPING_ASSISTANT: {
                "name": "Asistente de Compras",
                "description": "Agente que ayuda a los clientes a encontrar productos, comparar opciones y completar compras.",
                "category": AgentCategory.ECOMMERCE,
                "system_prompt": """Eres un asistente de compras experto. Ayudas a los clientes a encontrar exactamente lo que buscan.

CAPACIDADES:
- Entender necesidades y preferencias
- Buscar y filtrar productos
- Comparar opciones
- Explicar características y diferencias
- Agregar al carrito y procesar pagos
- Sugerir productos complementarios

TONO: Amigable, útil, no presionador.
Siempre prioriza ayudar al cliente a encontrar lo mejor para ellos.""",
                "personality": AgentPersonality(
                    tone="friendly",
                    communication_style="helpful",
                    humor_level="subtle",
                    empathy_level="medium",
                    formality="casual"
                ),
                "values": AgentValues(
                    core_values=["helpfulness", "transparency", "customer_satisfaction"],
                    brand_voice="Tu asistente personal de compras, siempre aquí para ayudarte",
                    do_not_say=["Tienes que comprar esto", "No hay otras opciones"],
                    must_mention=["¿Qué estás buscando?", "¿Te gustaría ver opciones similares?"]
                ),
                "tools": ["search_products", "compare_products", "add_to_cart", "process_payment", "suggest_related"]
            }
        }
    
    # ============================================
    # CREACIÓN DE AGENTES
    # ============================================
    
    def create_agent(
        self,
        name: str,
        description: str,
        category: str,
        template: str,
        personality: Optional[Dict[str, Any]] = None,
        values: Optional[Dict[str, Any]] = None,
        custom_instructions: str = "",
        knowledge_base: Optional[List[str]] = None,
        deployment_channels: Optional[List[str]] = None,
        created_by: Optional[str] = None
    ) -> str:
        """
        Crea un nuevo agente usando un template.
        
        Returns:
            agent_id: ID del agente creado
        """
        agent_id = str(uuid.uuid4())
        
        # Obtener template
        template_enum = AgentTemplate(template)
        template_data = self.templates.get(template_enum, {})
        
        # Construir personalidad
        if personality:
            agent_personality = AgentPersonality(**personality)
        else:
            agent_personality = template_data.get("personality", AgentPersonality(
                tone="friendly",
                communication_style="helpful",
                humor_level="subtle",
                empathy_level="medium",
                formality="casual"
            ))
        
        # Construir valores
        if values:
            agent_values = AgentValues(**values)
        else:
            agent_values = template_data.get("values", AgentValues(
                core_values=["helpfulness", "transparency"],
                brand_voice="Amigable y profesional",
                do_not_say=[],
                must_mention=[]
            ))
        
        # Construir system prompt personalizado
        base_prompt = template_data.get("system_prompt", "Eres un asistente AI útil y amigable.")
        if custom_instructions:
            system_prompt = f"{base_prompt}\n\nINSTRUCCIONES PERSONALIZADAS:\n{custom_instructions}"
        else:
            system_prompt = base_prompt
        
        # Agregar personalidad al prompt
        personality_prompt = f"""
PERSONALIDAD:
- Tono: {agent_personality.tone}
- Estilo de comunicación: {agent_personality.communication_style}
- Nivel de humor: {agent_personality.humor_level}
- Nivel de empatía: {agent_personality.empathy_level}
- Formalidad: {agent_personality.formality}
"""
        if agent_personality.custom_voice_description:
            personality_prompt += f"- Voz personalizada: {agent_personality.custom_voice_description}\n"
        
        system_prompt += personality_prompt
        
        # Agregar valores al prompt
        values_prompt = f"""
VALORES Y PRINCIPIOS:
- Valores principales: {', '.join(agent_values.core_values)}
- Voz de marca: {agent_values.brand_voice}
- Nunca digas: {', '.join(agent_values.do_not_say) if agent_values.do_not_say else 'N/A'}
- Siempre menciona: {', '.join(agent_values.must_mention) if agent_values.must_mention else 'N/A'}
"""
        system_prompt += values_prompt
        
        # Deployment channels
        channels = []
        if deployment_channels:
            channels = [DeploymentChannel(dc) for dc in deployment_channels]
        else:
            channels = [DeploymentChannel.WEB]  # Default
        
        # Crear agente
        agent = AgentConfig(
            agent_id=agent_id,
            name=name,
            description=description,
            category=AgentCategory(category),
            template=template_enum,
            system_prompt=system_prompt,
            personality=agent_personality,
            values=agent_values,
            llm_provider=LLMProvider.OPENAI,  # Default, puede cambiarse
            custom_instructions=custom_instructions,
            knowledge_base=knowledge_base or [],
            deployment_channels=channels,
            tools=template_data.get("tools", []),
            created_by=created_by
        )
        
        self.agents[agent_id] = agent
        
        # Inicializar analytics
        self.analytics[agent_id] = AgentAnalytics(agent_id=agent_id)
        
        # Guardar
        self._save_data()
        
        print(f"✅ [AI Agent Factory] Agente creado: {name} ({agent_id})")
        return agent_id
    
    # ============================================
    # PERSONALIZACIÓN AVANZADA
    # ============================================
    
    def personalize_agent_from_social(
        self,
        agent_id: str,
        platform: str,
        access_token: str,
        content_types: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Personaliza un agente analizando contenido de redes sociales.
        
        Extrae:
        - Voz y tono del creador
        - Temas y valores
        - Estilo de comunicación
        - Personalidad única
        """
        if agent_id not in self.agents:
            return {"error": "Agente no encontrado"}
        
        agent = self.agents[agent_id]
        
        # Simular análisis de contenido social
        # En producción, esto haría llamadas reales a APIs de redes sociales
        print(f"🔍 [AI Agent Factory] Analizando contenido de {platform} para personalizar agente...")
        
        # Usar LLM para analizar y extraer personalidad
        analysis_prompt = f"""Analiza el contenido de un creador/influencer en {platform} y extrae:

1. Tono y voz única
2. Temas y valores principales
3. Estilo de comunicación
4. Personalidad distintiva
5. Frases o expresiones características
6. Qué temas evita
7. Qué temas siempre menciona

Genera un análisis detallado en formato JSON."""
        
        try:
            # En producción, aquí se obtendría el contenido real
            # Por ahora, simulamos con el LLM
            response = self.llm.invoke(analysis_prompt)
            analysis_text = response.content if hasattr(response, 'content') else str(response)
            
            # Actualizar agente con análisis
            # Esto se haría parseando el JSON y actualizando personality y values
            
            # Agregar integración social
            social_integration = SocialIntegration(
                platform=platform,
                connected=True,
                access_token=access_token,
                last_sync=datetime.now().isoformat(),
                content_sources=content_types or ["posts", "stories", "videos"]
            )
            
            agent.social_integrations.append(social_integration)
            agent.updated_at = datetime.now().isoformat()
            
            self._save_data()
            
            return {
                "success": True,
                "message": f"Agente personalizado desde {platform}",
                "analysis": analysis_text
            }
        except Exception as e:
            return {"error": str(e)}
    
    # ============================================
    # DEPLOYMENT
    # ============================================
    
    def deploy_agent(
        self,
        agent_id: str,
        channel: str,
        config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Despliega un agente en un canal específico.
        
        Returns:
            Dict con información de deployment (URLs, endpoints, etc.)
        """
        if agent_id not in self.agents:
            return {"error": "Agente no encontrado"}
        
        agent = self.agents[agent_id]
        channel_enum = DeploymentChannel(channel)
        
        # Agregar canal si no está
        if channel_enum not in agent.deployment_channels:
            agent.deployment_channels.append(channel_enum)
        
        deployment_info = {
            "agent_id": agent_id,
            "agent_name": agent.name,
            "channel": channel,
            "status": "deployed",
            "deployed_at": datetime.now().isoformat()
        }
        
        # Generar URLs/endpoints según el canal
        if channel_enum == DeploymentChannel.WEB:
            deployment_info["web_url"] = f"https://agents.example.com/{agent_id}"
            deployment_info["embed_code"] = f'<iframe src="https://agents.example.com/{agent_id}" width="400" height="600"></iframe>'
        
        elif channel_enum == DeploymentChannel.API:
            deployment_info["api_endpoint"] = f"https://api.example.com/agents/{agent_id}/chat"
            deployment_info["api_key"] = str(uuid.uuid4())
        
        elif channel_enum == DeploymentChannel.WHATSAPP:
            deployment_info["whatsapp_number"] = "+1234567890"
            deployment_info["setup_instructions"] = "Conecta este número a tu WhatsApp Business API"
        
        elif channel_enum == DeploymentChannel.MESSENGER:
            deployment_info["messenger_page_id"] = "123456789"
            deployment_info["setup_instructions"] = "Conecta a tu página de Facebook"
        
        elif channel_enum == DeploymentChannel.INSTAGRAM:
            deployment_info["instagram_account"] = "@tu_cuenta"
            deployment_info["setup_instructions"] = "Conecta a tu cuenta de Instagram Business"
        
        agent.updated_at = datetime.now().isoformat()
        self._save_data()
        
        print(f"✅ [AI Agent Factory] Agente {agent.name} desplegado en {channel}")
        return deployment_info
    
    # ============================================
    # MARKETPLACE
    # ============================================
    
    def publish_to_marketplace(
        self,
        agent_id: str,
        tags: List[str],
        marketplace_description: str,
        preview_image: Optional[str] = None
    ) -> Dict[str, Any]:
        """Publica un agente en el marketplace."""
        if agent_id not in self.agents:
            return {"error": "Agente no encontrado"}
        
        agent = self.agents[agent_id]
        
        # Hacer público
        agent.is_public = True
        agent.marketplace_tags = tags
        agent.marketplace_description = marketplace_description
        agent.updated_at = datetime.now().isoformat()
        
        # Agregar al marketplace
        marketplace_agent = MarketplaceAgent(
            agent_id=agent_id,
            name=agent.name,
            description=marketplace_description or agent.description,
            category=agent.category.value,
            template=agent.template.value,
            creator=agent.created_by or "Anonymous",
            tags=tags,
            rating=agent.rating,
            clone_count=agent.clone_count,
            preview_image=preview_image
        )
        
        self.marketplace[agent_id] = marketplace_agent
        self._save_data()
        
        return {
            "success": True,
            "message": f"Agente {agent.name} publicado en el marketplace",
            "marketplace_url": f"https://marketplace.example.com/agents/{agent_id}"
        }
    
    def clone_agent(self, agent_id: str, new_name: str, created_by: Optional[str] = None) -> str:
        """Clona un agente del marketplace o de otro usuario."""
        if agent_id not in self.agents:
            return None
        
        original_agent = self.agents[agent_id]
        
        # Crear nuevo agente basado en el original
        new_agent_id = str(uuid.uuid4())
        
        new_agent = AgentConfig(
            agent_id=new_agent_id,
            name=new_name,
            description=original_agent.description,
            category=original_agent.category,
            template=original_agent.template,
            system_prompt=original_agent.system_prompt,
            personality=original_agent.personality,
            values=original_agent.values,
            llm_provider=original_agent.llm_provider,
            model=original_agent.model,
            temperature=original_agent.temperature,
            max_tokens=original_agent.max_tokens,
            enabled=True,
            created_by=created_by,
            deployment_channels=original_agent.deployment_channels.copy(),
            tools=original_agent.tools.copy(),
            knowledge_base=original_agent.knowledge_base.copy(),
            custom_instructions=original_agent.custom_instructions,
            is_public=False,  # El clon no es público por defecto
            marketplace_tags=[],
            marketplace_description=""
        )
        
        self.agents[new_agent_id] = new_agent
        self.analytics[new_agent_id] = AgentAnalytics(agent_id=new_agent_id)
        
        # Incrementar contador de clones
        original_agent.clone_count += 1
        if original_agent.is_public:
            if agent_id in self.marketplace:
                self.marketplace[agent_id].clone_count += 1
        
        self._save_data()
        
        print(f"✅ [AI Agent Factory] Agente clonado: {new_name} ({new_agent_id})")
        return new_agent_id
    
    def search_marketplace(
        self,
        query: str,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        min_rating: float = 0.0,
        limit: int = 20
    ) -> List[MarketplaceAgent]:
        """Busca agentes en el marketplace."""
        results = []
        
        for agent_id, marketplace_agent in self.marketplace.items():
            # Filtros
            if category and marketplace_agent.category != category:
                continue
            
            if marketplace_agent.rating < min_rating:
                continue
            
            if tags:
                if not any(tag in marketplace_agent.tags for tag in tags):
                    continue
            
            # Búsqueda por texto
            if query:
                query_lower = query.lower()
                if (query_lower not in marketplace_agent.name.lower() and
                    query_lower not in marketplace_agent.description.lower() and
                    not any(query_lower in tag.lower() for tag in marketplace_agent.tags)):
                    continue
            
            results.append(marketplace_agent)
        
        # Ordenar por rating y clone_count
        results.sort(key=lambda x: (x.rating, x.clone_count), reverse=True)
        
        return results[:limit]
    
    # ============================================
    # INTERACCIÓN CON AGENTES
    # ============================================
    
    async def chat_with_agent(
        self,
        agent_id: str,
        message: str,
        session_id: Optional[str] = None,
        channel: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Chatea con un agente.
        
        Returns:
            Dict con respuesta del agente y metadata
        """
        if agent_id not in self.agents:
            return {"error": "Agente no encontrado"}
        
        agent = self.agents[agent_id]
        
        if not agent.enabled:
            return {"error": "Agente deshabilitado"}
        
        start_time = time.time()
        
        try:
            # Construir mensajes
            messages = [
                SystemMessage(content=agent.system_prompt),
                HumanMessage(content=message)
            ]
            
            # Invocar LLM
            response = await self.llm.ainvoke(messages)
            response_text = response.content if hasattr(response, 'content') else str(response)
            
            # Actualizar analytics
            if agent_id in self.analytics:
                analytics = self.analytics[agent_id]
                analytics.total_interactions += 1
                analytics.successful_interactions += 1
                analytics.usage_count += 1
                
                response_time_ms = (time.time() - start_time) * 1000
                analytics.average_response_time_ms = (
                    (analytics.average_response_time_ms * (analytics.total_interactions - 1) + response_time_ms) /
                    analytics.total_interactions
                )
                
                if channel:
                    analytics.channel_breakdown[channel] = analytics.channel_breakdown.get(channel, 0) + 1
                
                analytics.last_updated = datetime.now().isoformat()
            
            agent.usage_count += 1
            agent.updated_at = datetime.now().isoformat()
            self._save_data()
            
            return {
                "agent_id": agent_id,
                "agent_name": agent.name,
                "response": response_text,
                "session_id": session_id,
                "channel": channel,
                "response_time_ms": (time.time() - start_time) * 1000,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            if agent_id in self.analytics:
                self.analytics[agent_id].failed_interactions += 1
            
            return {"error": str(e)}
    
    # ============================================
    # ANALYTICS
    # ============================================
    
    def get_agent_analytics(self, agent_id: str) -> Optional[AgentAnalytics]:
        """Obtiene analytics de un agente."""
        return self.analytics.get(agent_id)
    
    def list_agents(self, category: Optional[str] = None, created_by: Optional[str] = None) -> List[AgentConfig]:
        """Lista agentes."""
        results = []
        for agent in self.agents.values():
            if category and agent.category.value != category:
                continue
            if created_by and agent.created_by != created_by:
                continue
            results.append(agent)
        return results
    
    def get_agent(self, agent_id: str) -> Optional[AgentConfig]:
        """Obtiene un agente por ID."""
        return self.agents.get(agent_id)


# ============================================
# FUNCIONES HELPER PARA GRADIO
# ============================================

_ai_agent_factory_instance: Optional[AIAgentFactory] = None


def get_ai_agent_factory(config: Optional[AppConfig] = None, llm: Optional[BaseLanguageModel] = None) -> AIAgentFactory:
    """Obtiene la instancia singleton de AIAgentFactory."""
    global _ai_agent_factory_instance
    
    if _ai_agent_factory_instance is None:
        if config is None:
            from .config import AppConfig
            config = AppConfig()
        
        _ai_agent_factory_instance = AIAgentFactory(config=config, llm=llm)
    
    return _ai_agent_factory_instance


def run_ai_agent_factory(
    message: str,
    agent_id: Optional[str] = None,
    session_id: Optional[str] = None,
    config: Optional[AppConfig] = None
) -> Dict[str, Any]:
    """Función helper para Gradio."""
    factory = get_ai_agent_factory(config=config)
    
    if agent_id:
        return asyncio.run(factory.chat_with_agent(agent_id, message, session_id))
    else:
        return {"error": "agent_id requerido"}

