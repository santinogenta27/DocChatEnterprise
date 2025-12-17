"""
Business AI Agent Mode - Multi-tenant SaaS AI Agent para Sales & Customer Support
==================================================================================

Sistema multi-tenant que permite a empresas conectar AI Agents a:
- Websites (widget JavaScript)
- WhatsApp Business API

Funcionalidades:
- Sales support (ventas 24/7)
- Customer support automation
- Lead capture
- Escalación a humanos
- Analytics y métricas

Arquitectura:
- Backend: FastAPI
- Base de datos: PostgreSQL (multi-tenant)
- LLM: OpenAI/Anthropic con prompts especializados
- Canales: Web Widget + WhatsApp Business API
"""

from __future__ import annotations

import os
import json
import uuid
import hashlib
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from pathlib import Path
from dataclasses import dataclass, asdict, field
from enum import Enum
import re

# SQLAlchemy imports
try:
    from sqlalchemy import (
        create_engine, Column, Integer, String, Text, Boolean, 
        DateTime, Float, ForeignKey, JSON, Index
    )
    from sqlalchemy.ext.declarative import declarative_base
    from sqlalchemy.orm import sessionmaker, relationship, Session
    from sqlalchemy.pool import QueuePool
    SQLALCHEMY_AVAILABLE = True
except ImportError:
    SQLALCHEMY_AVAILABLE = False
    Base = None
    create_engine = None
    sessionmaker = None

# LLM imports
try:
    from langchain_openai import ChatOpenAI
    from langchain_anthropic import ChatAnthropic
    from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
    from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    ChatOpenAI = None

# FastAPI imports
try:
    from fastapi import FastAPI, HTTPException, Depends, Request
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import JSONResponse
    from pydantic import BaseModel, Field
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False
    FastAPI = None

from .config import AppConfig


# ==================== ENUMS ====================

class IntentType(str, Enum):
    """Tipos de intención del usuario."""
    PRODUCT_INQUIRY = "product_inquiry"
    PRICING = "pricing"
    PURCHASE = "purchase"
    SUPPORT = "support"
    GENERAL = "general"
    GREETING = "greeting"
    GOODBYE = "goodbye"


class ChannelType(str, Enum):
    """Canales de comunicación."""
    WEB = "web"
    WHATSAPP = "whatsapp"


class LeadStatus(str, Enum):
    """Estado de un lead."""
    NEW = "new"
    CONTACTED = "contacted"
    QUALIFIED = "qualified"
    CONVERTED = "converted"
    LOST = "lost"


class ConversationStatus(str, Enum):
    """Estado de una conversación."""
    ACTIVE = "active"
    ESCALATED = "escalated"
    CLOSED = "closed"
    ABANDONED = "abandoned"


# ==================== DATACLASSES ====================

@dataclass
class CompanyConfig:
    """Configuración de una empresa."""
    company_id: str
    name: str
    description: str
    products: List[Dict[str, Any]]
    faqs: List[Dict[str, Any]]
    business_rules: Dict[str, Any]
    whatsapp_config: Optional[Dict[str, Any]] = None
    cta_links: Dict[str, str] = field(default_factory=dict)
    escalation_triggers: List[str] = field(default_factory=list)
    system_prompt: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Product:
    """Producto o servicio de una empresa."""
    product_id: str
    company_id: str
    name: str
    description: str
    price: Optional[float] = None
    price_unit: str = "USD"
    link: Optional[str] = None
    features: List[str] = field(default_factory=list)
    category: Optional[str] = None


@dataclass
class Conversation:
    """Conversación con un usuario."""
    conversation_id: str
    company_id: str
    channel: ChannelType
    user_id: str  # Puede ser número de WhatsApp o session ID de web
    status: ConversationStatus
    messages: List[Dict[str, Any]] = field(default_factory=list)
    intent: Optional[IntentType] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    escalated: bool = False
    escalated_to: Optional[str] = None


@dataclass
class Lead:
    """Lead capturado."""
    lead_id: str
    company_id: str
    conversation_id: str
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    intent: Optional[IntentType] = None
    status: LeadStatus = LeadStatus.NEW
    meta_data: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)


# ==================== DATABASE MODELS ====================

if SQLALCHEMY_AVAILABLE:
    Base = declarative_base()
    
    class Company(Base):
        __tablename__ = "business_ai_companies"
        
        company_id = Column(String, primary_key=True)
        name = Column(String, nullable=False)
        description = Column(Text)
        config = Column(JSON)  # Almacena CompanyConfig completo
        whatsapp_phone_id = Column(String)
        whatsapp_access_token = Column(String)
        whatsapp_verify_token = Column(String)
        widget_secret_key = Column(String, unique=True, nullable=False)
        active = Column(Boolean, default=True)
        created_at = Column(DateTime, default=datetime.utcnow)
        updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
        
        # Relaciones
        products = relationship("Product", back_populates="company", cascade="all, delete-orphan")
        conversations = relationship("Conversation", back_populates="company", cascade="all, delete-orphan")
        leads = relationship("Lead", back_populates="company", cascade="all, delete-orphan")
        
        __table_args__ = (
            Index('idx_company_widget_key', 'widget_secret_key'),
        )
    
    class Product(Base):
        __tablename__ = "business_ai_products"
        
        product_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
        company_id = Column(String, ForeignKey("business_ai_companies.company_id"), nullable=False)
        name = Column(String, nullable=False)
        description = Column(Text)
        price = Column(Float)
        price_unit = Column(String, default="USD")
        link = Column(String)
        features = Column(JSON, default=list)
        category = Column(String)
        active = Column(Boolean, default=True)
        created_at = Column(DateTime, default=datetime.utcnow)
        
        company = relationship("Company", back_populates="products")
        
        __table_args__ = (
            Index('idx_product_company', 'company_id'),
        )
    
    class Conversation(Base):
        __tablename__ = "business_ai_conversations"
        
        conversation_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
        company_id = Column(String, ForeignKey("business_ai_companies.company_id"), nullable=False)
        channel = Column(String, nullable=False)  # web, whatsapp
        user_id = Column(String, nullable=False)
        status = Column(String, default="active")
        messages = Column(JSON, default=list)
        intent = Column(String)
        escalated = Column(Boolean, default=False)
        escalated_to = Column(String)
        created_at = Column(DateTime, default=datetime.utcnow)
        updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
        
        company = relationship("Company", back_populates="conversations")
        leads = relationship("Lead", back_populates="conversation")
        
        __table_args__ = (
            Index('idx_conversation_company', 'company_id'),
            Index('idx_conversation_user', 'user_id'),
            Index('idx_conversation_status', 'status'),
        )
    
    class Lead(Base):
        __tablename__ = "business_ai_leads"
        
        lead_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
        company_id = Column(String, ForeignKey("business_ai_companies.company_id"), nullable=False)
        conversation_id = Column(String, ForeignKey("business_ai_conversations.conversation_id"))
        name = Column(String)
        phone = Column(String)
        email = Column(String)
        intent = Column(String)
        status = Column(String, default="new")
        meta_data = Column(JSON, default=dict)
        created_at = Column(DateTime, default=datetime.utcnow)
        
        company = relationship("Company", back_populates="leads")
        conversation = relationship("Conversation", back_populates="leads")
        
        __table_args__ = (
            Index('idx_lead_company', 'company_id'),
            Index('idx_lead_status', 'status'),
        )
    
    class Analytics(Base):
        __tablename__ = "business_ai_analytics"
        
        analytics_id = Column(Integer, primary_key=True, autoincrement=True)
        company_id = Column(String, ForeignKey("business_ai_companies.company_id"), nullable=False)
        date = Column(DateTime, default=datetime.utcnow)
        metric_type = Column(String, nullable=False)  # conversation, lead, escalation, etc.
        metric_value = Column(Integer, default=0)
        meta_data = Column(JSON, default=dict)
        
        __table_args__ = (
            Index('idx_analytics_company_date', 'company_id', 'date'),
        )


# ==================== PROMPT TEMPLATES ====================

SALES_SYSTEM_PROMPT_TEMPLATE = """Eres un asistente de ventas y soporte al cliente profesional y amigable para {company_name}.

INFORMACIÓN DE LA EMPRESA:
{company_description}

PRODUCTOS/SERVICIOS DISPONIBLES:
{products_info}

PREGUNTAS FRECUENTES:
{faqs_info}

TU OBJETIVO:
1. Responder preguntas sobre productos, precios y servicios de manera clara y concisa
2. Guiar a los clientes hacia la compra cuando muestren interés
3. Capturar información de leads cuando sea apropiado
4. Escalar a un humano cuando sea necesario

REGLAS DE CONVERSACIÓN:
- Sé profesional pero amigable
- Responde de forma concisa (máximo 2-3 oraciones por respuesta)
- Si el cliente pregunta por precios, muestra los productos relevantes con sus precios
- Si muestra interés en comprar, ofrece el link de checkout o captura su información
- Si el cliente pide hablar con un humano o tiene un problema complejo, indica que un agente humano se pondrá en contacto pronto
- Nunca inventes información que no tengas

INSTRUCCIONES ESPECÍFICAS:
- Cuando el cliente pregunte por productos, lista los productos relevantes con nombres, descripciones breves y precios
- Cuando el cliente muestre intención de compra, ofrece: "Puedes comprar [producto] aquí: [link] o puedo ayudarte con más información"
- Para capturar leads, pregunta discretamente: "¿Te gustaría que te contacte un especialista? Puedo tomar tu nombre y teléfono"
- Para escalar: "Entiendo tu necesidad. Un agente humano se pondrá en contacto contigo pronto para ayudarte mejor"

CTAs DISPONIBLES:
{cta_links}

Responde en el idioma del cliente. Si no está claro, usa español por defecto.
"""


# ==================== MAIN CLASS ====================

class BusinessAIAgentMode:
    """
    Modo Business AI Agent - Sistema multi-tenant para sales y customer support.
    """
    
    def __init__(
        self,
        config: AppConfig,
        provider: str = "openai",
        db_url: Optional[str] = None
    ):
        """
        Inicializa el Business AI Agent Mode.
        
        Args:
            config: Configuración de la aplicación
            provider: Proveedor LLM ("openai" o "anthropic")
            db_url: URL de conexión a PostgreSQL (opcional)
        """
        self.config = config
        self.provider = provider
        
        # Inicializar base de datos
        self._init_database(db_url)
        
        # Inicializar LLM
        self._init_llm()
        
        # FastAPI app (se inicializa cuando se necesite)
        self.fastapi_app = None
    
    def _init_database(self, db_url: Optional[str] = None):
        """Inicializa la conexión a la base de datos."""
        if not SQLALCHEMY_AVAILABLE:
            print("⚠️ SQLAlchemy no disponible. Usando modo fallback.")
            self.engine = None
            self.Session = None
            return
        
        # Obtener URL de conexión
        if not db_url:
            db_url = os.getenv(
                "BUSINESS_AI_DATABASE_URL",
                f"sqlite:///{Path(self.config.memory_dir if self.config.memory_dir else 'data') / 'business_ai_agent.db'}"
            )
        
        try:
            if "postgresql" in db_url or "postgres" in db_url:
                # PostgreSQL
                self.engine = create_engine(
                    db_url,
                    poolclass=QueuePool,
                    pool_size=5,
                    max_overflow=10,
                    pool_pre_ping=True,
                    echo=False
                )
            else:
                # SQLite fallback
                self.engine = create_engine(db_url, echo=False)
            
            self.Session = sessionmaker(bind=self.engine)
            
            # Crear tablas
            if Base:
                Base.metadata.create_all(self.engine)
            
            print(f"✅ Base de datos Business AI Agent conectada")
            
        except Exception as e:
            print(f"⚠️ Error conectando a base de datos: {e}")
            self.engine = None
            self.Session = None
    
    def _init_llm(self):
        """Inicializa el modelo LLM."""
        if not LANGCHAIN_AVAILABLE:
            print("⚠️ LangChain no disponible. Usando modo fallback.")
            self.llm = None
            return
        
        api_key = os.getenv("OPENAI_API_KEY") if self.provider == "openai" else os.getenv("ANTHROPIC_API_KEY")
        
        if not api_key:
            print(f"⚠️ API key no encontrada para {self.provider}")
            self.llm = None
            return
        
        try:
            if self.provider == "openai":
                self.llm = ChatOpenAI(
                    model="gpt-4o-mini",
                    temperature=0.7,
                    api_key=api_key
                )
            elif self.provider == "anthropic":
                self.llm = ChatAnthropic(
                    model="claude-3-haiku-20240307",
                    temperature=0.7,
                    api_key=api_key
                )
            else:
                self.llm = None
                
            print(f"✅ LLM inicializado: {self.provider}")
            
        except Exception as e:
            print(f"⚠️ Error inicializando LLM: {e}")
            self.llm = None
    
    # ==================== COMPANY MANAGEMENT ====================
    
    def create_company(
        self,
        name: str,
        description: str,
        products: List[Dict[str, Any]],
        faqs: List[Dict[str, Any]] = None,
        business_rules: Dict[str, Any] = None,
        whatsapp_config: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Crea una nueva empresa en el sistema.
        
        Returns:
            company_id: ID único de la empresa
        """
        if not self.Session:
            raise RuntimeError("Base de datos no inicializada")
        
        company_id = str(uuid.uuid4())
        widget_secret_key = self._generate_widget_key()
        
        company_config = CompanyConfig(
            company_id=company_id,
            name=name,
            description=description,
            products=products or [],
            faqs=faqs or [],
            business_rules=business_rules or {}
        )
        
        session = self.Session()
        try:
            company = Company(
                company_id=company_id,
                name=name,
                description=description,
                config=asdict(company_config),
                whatsapp_phone_id=whatsapp_config.get("phone_id") if whatsapp_config else None,
                whatsapp_access_token=whatsapp_config.get("access_token") if whatsapp_config else None,
                whatsapp_verify_token=whatsapp_config.get("verify_token") if whatsapp_config else None,
                widget_secret_key=widget_secret_key,
                active=True
            )
            
            session.add(company)
            
            # Agregar productos
            for product_data in products:
                product = Product(
                    company_id=company_id,
                    name=product_data.get("name", ""),
                    description=product_data.get("description", ""),
                    price=product_data.get("price"),
                    price_unit=product_data.get("price_unit", "USD"),
                    link=product_data.get("link"),
                    features=product_data.get("features", []),
                    category=product_data.get("category")
                )
                session.add(product)
            
            session.commit()
            return company_id
            
        except Exception as e:
            session.rollback()
            raise RuntimeError(f"Error creando empresa: {e}")
        finally:
            session.close()
    
    def get_company(self, company_id: str) -> Optional[Dict[str, Any]]:
        """Obtiene la configuración de una empresa."""
        if not self.Session:
            return None
        
        session = self.Session()
        try:
            company = session.query(Company).filter_by(company_id=company_id).first()
            if not company:
                return None
            
            return {
                "company_id": company.company_id,
                "name": company.name,
                "description": company.description,
                "config": company.config,
                "widget_secret_key": company.widget_secret_key,
                "whatsapp_configured": bool(company.whatsapp_phone_id),
                "active": company.active,
                "created_at": company.created_at.isoformat() if company.created_at else None
            }
        finally:
            session.close()
    
    def get_company_by_widget_key(self, widget_key: str) -> Optional[Dict[str, Any]]:
        """Obtiene empresa por widget secret key."""
        if not self.Session:
            return None
        
        session = self.Session()
        try:
            company = session.query(Company).filter_by(widget_secret_key=widget_key).first()
            if not company:
                return None
            
            return self.get_company(company.company_id)
        finally:
            session.close()
    
    def _generate_widget_key(self) -> str:
        """Genera una clave secreta única para el widget."""
        random_str = f"{uuid.uuid4()}{datetime.utcnow().isoformat()}"
        return hashlib.sha256(random_str.encode()).hexdigest()[:32]
    
    # ==================== MESSAGE PROCESSING ====================
    
    def process_message(
        self,
        company_id: str,
        user_message: str,
        user_id: str,
        channel: ChannelType,
        conversation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Procesa un mensaje del usuario y genera una respuesta.
        
        Returns:
            Dict con la respuesta y metadatos
        """
        if not self.llm:
            return {
                "response": "Lo siento, el sistema de IA no está disponible en este momento.",
                "intent": IntentType.GENERAL.value,
                "escalate": False
            }
        
        # Obtener configuración de la empresa
        company_data = self.get_company(company_id)
        if not company_data:
            return {
                "response": "Error: Empresa no encontrada",
                "intent": IntentType.GENERAL.value,
                "escalate": False
            }
        
        config = company_data.get("config", {})
        
        # Obtener o crear conversación
        conversation_id = self._get_or_create_conversation(
            company_id, user_id, channel, conversation_id
        )
        
        # Obtener historial de conversación
        conversation_history = self._get_conversation_history(conversation_id)
        
        # Detectar intención
        intent = self._detect_intent(user_message)
        
        # Construir prompt del sistema
        system_prompt = self._build_system_prompt(config, company_data)
        
        # Generar respuesta con LLM
        response = self._generate_response(
            system_prompt,
            user_message,
            conversation_history,
            intent
        )
        
        # Verificar si necesita escalación
        should_escalate = self._should_escalate(user_message, response, intent, config)
        
        # Guardar mensaje en conversación
        self._save_message(
            conversation_id,
            user_message,
            response,
            intent,
            channel
        )
        
        # Intentar capturar lead si hay intención de compra
        lead_captured = False
        if intent == IntentType.PURCHASE:
            lead_captured = self._try_capture_lead(company_id, conversation_id, user_id, intent)
        
        return {
            "response": response,
            "intent": intent.value,
            "escalate": should_escalate,
            "conversation_id": conversation_id,
            "lead_captured": lead_captured
        }
    
    def _build_system_prompt(
        self,
        config: Dict[str, Any],
        company_data: Dict[str, Any]
    ) -> str:
        """Construye el prompt del sistema para el LLM."""
        products = config.get("products", [])
        products_info = "\n".join([
            f"- {p.get('name', 'N/A')}: {p.get('description', '')} - Precio: {p.get('price', 'N/A')} {p.get('price_unit', 'USD')}"
            for p in products
        ])
        
        faqs = config.get("faqs", [])
        faqs_info = "\n".join([
            f"P: {f.get('question', '')}\nR: {f.get('answer', '')}\n"
            for f in faqs
        ])
        
        cta_links = config.get("cta_links", {})
        cta_info = "\n".join([f"{k}: {v}" for k, v in cta_links.items()])
        
        return SALES_SYSTEM_PROMPT_TEMPLATE.format(
            company_name=company_data.get("name", "la empresa"),
            company_description=company_data.get("description", ""),
            products_info=products_info or "No hay productos configurados",
            faqs_info=faqs_info or "No hay FAQs configuradas",
            cta_links=cta_info or "No hay CTAs configurados"
        )
    
    def _detect_intent(self, message: str) -> IntentType:
        """Detecta la intención del usuario en el mensaje."""
        message_lower = message.lower()
        
        # Patrones de intención
        if any(word in message_lower for word in ["hola", "hi", "hello", "buenos días", "buenas tardes"]):
            return IntentType.GREETING
        
        if any(word in message_lower for word in ["adios", "bye", "gracias", "thanks"]):
            return IntentType.GOODBYE
        
        if any(word in message_lower for word in ["precio", "price", "cuesta", "costo", "cost", "cuánto", "how much"]):
            return IntentType.PRICING
        
        if any(word in message_lower for word in ["comprar", "buy", "purchase", "orden", "order", "quiero"]):
            return IntentType.PURCHASE
        
        if any(word in message_lower for word in ["producto", "product", "servicio", "service", "qué", "what"]):
            return IntentType.PRODUCT_INQUIRY
        
        if any(word in message_lower for word in ["problema", "problem", "ayuda", "help", "soporte", "support", "error"]):
            return IntentType.SUPPORT
        
        return IntentType.GENERAL
    
    def _generate_response(
        self,
        system_prompt: str,
        user_message: str,
        conversation_history: List[Dict[str, str]],
        intent: IntentType
    ) -> str:
        """Genera respuesta usando el LLM."""
        try:
            messages = [SystemMessage(content=system_prompt)]
            
            # Agregar historial (últimos 5 mensajes)
            for msg in conversation_history[-5:]:
                if msg["role"] == "user":
                    messages.append(HumanMessage(content=msg["content"]))
                else:
                    messages.append(AIMessage(content=msg["content"]))
            
            # Agregar mensaje actual
            messages.append(HumanMessage(content=user_message))
            
            # Generar respuesta
            response = self.llm.invoke(messages)
            return response.content
            
        except Exception as e:
            print(f"Error generando respuesta: {e}")
            return "Lo siento, hubo un error procesando tu mensaje. Por favor intenta de nuevo."
    
    def _should_escalate(
        self,
        user_message: str,
        response: str,
        intent: IntentType,
        config: Dict[str, Any]
    ) -> bool:
        """Determina si la conversación debe escalarse a un humano."""
        escalation_triggers = config.get("escalation_triggers", [])
        message_lower = user_message.lower()
        
        # Triggers por defecto
        default_triggers = [
            "hablar con humano", "speak to human", "agente humano", "human agent",
            "quebja", "complaint", "reclamo", "problema grave", "serious problem"
        ]
        
        all_triggers = escalation_triggers + default_triggers
        
        if any(trigger.lower() in message_lower for trigger in all_triggers):
            return True
        
        if intent == IntentType.SUPPORT:
            # Si es soporte y el mensaje es largo, puede necesitar humano
            if len(user_message) > 200:
                return True
        
        return False
    
    def _get_or_create_conversation(
        self,
        company_id: str,
        user_id: str,
        channel: ChannelType,
        conversation_id: Optional[str] = None
    ) -> str:
        """Obtiene o crea una conversación."""
        if not self.Session:
            return str(uuid.uuid4())
        
        session = self.Session()
        try:
            if conversation_id:
                conv = session.query(Conversation).filter_by(
                    conversation_id=conversation_id,
                    company_id=company_id
                ).first()
                if conv:
                    return conversation_id
            
            # Buscar conversación activa existente
            conv = session.query(Conversation).filter_by(
                company_id=company_id,
                user_id=user_id,
                channel=channel.value,
                status="active"
            ).order_by(Conversation.created_at.desc()).first()
            
            if conv:
                return conv.conversation_id
            
            # Crear nueva conversación
            new_conv = Conversation(
                company_id=company_id,
                channel=channel.value,
                user_id=user_id,
                status="active"
            )
            session.add(new_conv)
            session.commit()
            return new_conv.conversation_id
            
        except Exception as e:
            session.rollback()
            return str(uuid.uuid4())
        finally:
            session.close()
    
    def _get_conversation_history(self, conversation_id: str) -> List[Dict[str, str]]:
        """Obtiene el historial de una conversación."""
        if not self.Session:
            return []
        
        session = self.Session()
        try:
            conv = session.query(Conversation).filter_by(conversation_id=conversation_id).first()
            if not conv or not conv.messages:
                return []
            return conv.messages
        finally:
            session.close()
    
    def _save_message(
        self,
        conversation_id: str,
        user_message: str,
        ai_response: str,
        intent: IntentType,
        channel: ChannelType
    ):
        """Guarda un mensaje en la conversación."""
        if not self.Session:
            return
        
        session = self.Session()
        try:
            conv = session.query(Conversation).filter_by(conversation_id=conversation_id).first()
            if not conv:
                return
            
            if not conv.messages:
                conv.messages = []
            
            conv.messages.append({
                "role": "user",
                "content": user_message,
                "timestamp": datetime.utcnow().isoformat()
            })
            conv.messages.append({
                "role": "assistant",
                "content": ai_response,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            conv.intent = intent.value
            conv.updated_at = datetime.utcnow()
            
            session.commit()
            
        except Exception as e:
            session.rollback()
            print(f"Error guardando mensaje: {e}")
        finally:
            session.close()
    
    def _try_capture_lead(
        self,
        company_id: str,
        conversation_id: str,
        user_id: str,
        intent: IntentType
    ) -> bool:
        """Intenta capturar información de lead."""
        # Esta función se puede expandir para extraer información del mensaje
        # Por ahora solo crea un lead básico
        if not self.Session:
            return False
        
        session = self.Session()
        try:
            lead = Lead(
                company_id=company_id,
                conversation_id=conversation_id,
                phone=user_id if user_id.startswith("+") else None,
                intent=intent.value,
                status=LeadStatus.NEW
            )
            session.add(lead)
            session.commit()
            return True
        except Exception:
            session.rollback()
            return False
        finally:
            session.close()
    
    # ==================== ANALYTICS ====================
    
    def get_analytics(
        self,
        company_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Obtiene analytics de una empresa."""
        if not self.Session:
            return {}
        
        if not start_date:
            start_date = datetime.utcnow() - timedelta(days=30)
        if not end_date:
            end_date = datetime.utcnow()
        
        session = self.Session()
        try:
            # Conversaciones
            total_conversations = session.query(Conversation).filter_by(
                company_id=company_id
            ).filter(
                Conversation.created_at >= start_date,
                Conversation.created_at <= end_date
            ).count()
            
            # Leads
            total_leads = session.query(Lead).filter_by(
                company_id=company_id
            ).filter(
                Lead.created_at >= start_date,
                Lead.created_at <= end_date
            ).count()
            
            # Escalaciones
            escalations = session.query(Conversation).filter_by(
                company_id=company_id,
                escalated=True
            ).filter(
                Conversation.created_at >= start_date,
                Conversation.created_at <= end_date
            ).count()
            
            # Intents más comunes
            intents = session.query(Conversation.intent).filter_by(
                company_id=company_id
            ).filter(
                Conversation.created_at >= start_date,
                Conversation.created_at <= end_date
            ).all()
            
            intent_counts = {}
            for (intent,) in intents:
                if intent:
                    intent_counts[intent] = intent_counts.get(intent, 0) + 1
            
            return {
                "total_conversations": total_conversations,
                "total_leads": total_leads,
                "escalations": escalations,
                "intent_distribution": intent_counts,
                "period": {
                    "start": start_date.isoformat(),
                    "end": end_date.isoformat()
                }
            }
        finally:
            session.close()
    
    # ==================== WIDGET KEY GENERATION ====================
    
    def get_widget_script(self, company_id: str) -> str:
        """Genera el script JavaScript para el widget."""
        company = self.get_company(company_id)
        if not company:
            return ""
        
        widget_key = company.get("widget_secret_key")
        
        # URL base de la API (debe configurarse)
        api_base_url = os.getenv(
            "BUSINESS_AI_API_BASE_URL",
            "http://localhost:8000"
        )
        
        script = f"""
<script>
(function() {{
    var script = document.createElement('script');
    script.src = '{api_base_url}/static/widget.js?key={widget_key}';
    script.async = true;
    document.head.appendChild(script);
}})();
</script>
"""
        return script

