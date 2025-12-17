"""
AI Agent Business Manager Mode - Sistema SaaS Multi-Tenant para Ventas y Soporte al Cliente
============================================================================================

Sistema empresarial que permite a empresas conectar un agente de IA a sus sitios web y WhatsApp Business
para automatizar ventas y soporte al cliente 24/7.

Funcionalidades:
- Agente de IA 24/7 para ventas y soporte
- Widget de chat para sitios web
- Integración con WhatsApp Business API
- Detección automática de intención (productos, precios, compras, soporte)
- Captura de leads
- Escalación a humanos cuando es necesario
- Sistema multi-tenant (datos separados por empresa)
- Analytics y métricas

Arquitectura:
- Backend: Python + FastAPI
- Base de datos: PostgreSQL (multi-tenant)
- LLM: OpenAI/Anthropic con prompts especializados
- Widget: JavaScript snippet para sitios web
- WhatsApp: Meta Cloud API
"""

from __future__ import annotations

import os
import json
import uuid
import hashlib
from typing import List, Dict, Any, Optional, Iterator, Tuple
from datetime import datetime, timedelta
from pathlib import Path
from dataclasses import dataclass, asdict, field
from enum import Enum
import re

try:
    from sqlalchemy import create_engine, Column, String, Integer, Float, Boolean, DateTime, JSON, Text, ForeignKey, Index
    from sqlalchemy.ext.declarative import declarative_base
    from sqlalchemy.orm import sessionmaker, Session, relationship
    from sqlalchemy.pool import QueuePool
    SQLALCHEMY_AVAILABLE = True
except ImportError:
    SQLALCHEMY_AVAILABLE = False
    print("⚠️ SQLAlchemy no disponible. Instala con: pip install sqlalchemy psycopg2-binary")

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic

from .config import AppConfig


if SQLALCHEMY_AVAILABLE:
    Base = declarative_base()
else:
    Base = None


# ==================== MODELOS DE BASE DE DATOS ====================

if SQLALCHEMY_AVAILABLE:
    class CompanyDB(Base):
        """Tabla de empresas/tenants"""
        __tablename__ = "ai_agent_companies"
        
        company_id = Column(String, primary_key=True)
        company_name = Column(String, nullable=False)
        company_description = Column(Text)
        contact_email = Column(String, nullable=False)
        plan = Column(String, default="free")  # free, pro, enterprise
        widget_script_id = Column(String, unique=True, index=True)  # ID único para widget
        whatsapp_phone_number = Column(String)  # Número de WhatsApp Business
        whatsapp_verified = Column(Boolean, default=False)
        whatsapp_webhook_verified = Column(Boolean, default=False)
        website_url = Column(String)
        company_config = Column(JSON)  # Configuración general de la empresa
        created_at = Column(DateTime, default=datetime.utcnow)
        updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
        is_active = Column(Boolean, default=True)
        
        # Índices
        __table_args__ = (
            Index('idx_company_widget', 'widget_script_id'),
            Index('idx_company_active', 'is_active'),
        )
    
    class ProductDB(Base):
        """Tabla de productos/servicios por empresa"""
        __tablename__ = "ai_agent_products"
        
        product_id = Column(String, primary_key=True)
        company_id = Column(String, ForeignKey("ai_agent_companies.company_id"), nullable=False, index=True)
        product_name = Column(String, nullable=False)
        product_description = Column(Text)
        price = Column(Float)
        currency = Column(String, default="USD")
        product_url = Column(String)  # Link al producto
        category = Column(String)
        in_stock = Column(Boolean, default=True)
        product_metadata = Column(JSON)  # Metadatos adicionales
        created_at = Column(DateTime, default=datetime.utcnow)
        updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    class FAQDB(Base):
        """Tabla de FAQs por empresa"""
        __tablename__ = "ai_agent_faqs"
        
        faq_id = Column(String, primary_key=True)
        company_id = Column(String, ForeignKey("ai_agent_companies.company_id"), nullable=False, index=True)
        question = Column(Text, nullable=False)
        answer = Column(Text, nullable=False)
        category = Column(String)  # product, support, pricing, etc.
        priority = Column(Integer, default=0)  # Prioridad para mostrar
        created_at = Column(DateTime, default=datetime.utcnow)
        updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    class LeadDB(Base):
        """Tabla de leads capturados"""
        __tablename__ = "ai_agent_leads"
        
        lead_id = Column(String, primary_key=True)
        company_id = Column(String, ForeignKey("ai_agent_companies.company_id"), nullable=False, index=True)
        name = Column(String)
        email = Column(String, index=True)
        phone = Column(String, index=True)
        intent = Column(String)  # product_inquiry, pricing, purchase, support
        product_interested = Column(String, ForeignKey("ai_agent_products.product_id"))
        message = Column(Text)
        channel = Column(String)  # web_widget, whatsapp
        status = Column(String, default="new")  # new, contacted, converted, lost
        lead_metadata = Column(JSON)
        created_at = Column(DateTime, default=datetime.utcnow, index=True)
        updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
        
        # Índices
        __table_args__ = (
            Index('idx_lead_company_status', 'company_id', 'status'),
            Index('idx_lead_created', 'created_at'),
        )
    
    class ConversationDB(Base):
        """Tabla de conversaciones"""
        __tablename__ = "ai_agent_conversations"
        
        conversation_id = Column(String, primary_key=True)
        company_id = Column(String, ForeignKey("ai_agent_companies.company_id"), nullable=False, index=True)
        channel = Column(String, nullable=False)  # web_widget, whatsapp
        user_id = Column(String, index=True)  # ID de usuario (anónimo o identificado)
        user_name = Column(String)
        user_email = Column(String)
        user_phone = Column(String)
        intent_detected = Column(String)  # product_inquiry, pricing, purchase, support
        status = Column(String, default="active")  # active, completed, escalated, abandoned
        escalated_to_human = Column(Boolean, default=False)
        lead_created = Column(Boolean, default=False)
        lead_id = Column(String, ForeignKey("ai_agent_leads.lead_id"))
        conversation_metadata = Column(JSON)
        started_at = Column(DateTime, default=datetime.utcnow, index=True)
        ended_at = Column(DateTime)
        updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
        
        # Índices
        __table_args__ = (
            Index('idx_conv_company_status', 'company_id', 'status'),
            Index('idx_conv_started', 'started_at'),
        )
    
    class MessageDB(Base):
        """Tabla de mensajes dentro de conversaciones"""
        __tablename__ = "ai_agent_messages"
        
        message_id = Column(String, primary_key=True)
        conversation_id = Column(String, ForeignKey("ai_agent_conversations.conversation_id"), nullable=False, index=True)
        role = Column(String, nullable=False)  # user, assistant, system
        content = Column(Text, nullable=False)
        intent_detected = Column(String)
        sentiment = Column(String)  # positive, neutral, negative
        message_metadata = Column(JSON)
        created_at = Column(DateTime, default=datetime.utcnow, index=True)
        
        # Índices
        __table_args__ = (
            Index('idx_msg_conv', 'conversation_id', 'created_at'),
        )
    
    class AnalyticsDB(Base):
        """Tabla de analytics agregados"""
        __tablename__ = "ai_agent_analytics"
        
        id = Column(Integer, primary_key=True, autoincrement=True)
        company_id = Column(String, ForeignKey("ai_agent_companies.company_id"), nullable=False, index=True)
        metric_date = Column(DateTime, nullable=False, index=True)
        total_conversations = Column(Integer, default=0)
        total_leads = Column(Integer, default=0)
        total_messages = Column(Integer, default=0)
        escalations_to_human = Column(Integer, default=0)
        purchase_intents = Column(Integer, default=0)
        product_inquiries = Column(Integer, default=0)
        support_requests = Column(Integer, default=0)
        avg_response_time_seconds = Column(Float, default=0.0)
        channel_breakdown = Column(JSON)  # {web_widget: X, whatsapp: Y}
        intent_breakdown = Column(JSON)  # {product_inquiry: X, pricing: Y, ...}
        created_at = Column(DateTime, default=datetime.utcnow)


# ==================== DATACLASSES ====================

class Intent(Enum):
    """Tipos de intenciones detectadas"""
    PRODUCT_INQUIRY = "product_inquiry"
    PRICING = "pricing"
    PURCHASE = "purchase"
    SUPPORT = "support"
    GREETING = "greeting"
    GOODBYE = "goodbye"
    OTHER = "other"


class ConversationStatus(Enum):
    """Estados de conversación"""
    ACTIVE = "active"
    COMPLETED = "completed"
    ESCALATED = "escalated"
    ABANDONED = "abandoned"


@dataclass
class Company:
    """Representa una empresa/tenant"""
    company_id: str
    company_name: str
    company_description: Optional[str] = None
    contact_email: str = ""
    plan: str = "free"
    widget_script_id: Optional[str] = None
    whatsapp_phone_number: Optional[str] = None
    website_url: Optional[str] = None
    config: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Product:
    """Representa un producto/servicio"""
    product_id: str
    company_id: str
    product_name: str
    product_description: Optional[str] = None
    price: Optional[float] = None
    currency: str = "USD"
    product_url: Optional[str] = None
    category: Optional[str] = None
    in_stock: bool = True


@dataclass
class Lead:
    """Representa un lead capturado"""
    lead_id: str
    company_id: str
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    intent: Optional[str] = None
    product_interested: Optional[str] = None
    message: Optional[str] = None
    channel: str = "web_widget"
    status: str = "new"


@dataclass
class Conversation:
    """Representa una conversación"""
    conversation_id: str
    company_id: str
    channel: str = "web_widget"
    user_id: Optional[str] = None
    status: str = "active"
    intent_detected: Optional[str] = None
    escalated_to_human: bool = False


# ==================== GESTOR DE BASE DE DATOS ====================

class BusinessAgentDatabaseManager:
    """Gestor de base de datos para AI Agent Business Manager"""
    
    def __init__(self, config: AppConfig):
        self.config = config
        self.use_fallback = True
        
        if not SQLALCHEMY_AVAILABLE:
            print("⚠️ SQLAlchemy no disponible. Usando fallback a archivos JSON")
            self._init_fallback()
            return
        
        # Obtener connection string
        db_url = os.getenv(
            "AI_AGENT_DATABASE_URL",
            f"sqlite:///{Path(config.memory_dir if config.memory_dir else 'data') / 'ai_agent_business.db'}"
        )
        
        try:
            self.engine = create_engine(
                db_url,
                poolclass=QueuePool,
                pool_size=5,
                max_overflow=10,
                pool_pre_ping=True,
                echo=False
            )
            self.Session = sessionmaker(bind=self.engine)
            
            # Crear tablas
            Base.metadata.create_all(self.engine)
            
            self.use_fallback = False
            print(f"✅ Base de datos AI Agent Business conectada: {db_url.split('@')[-1] if '@' in db_url else db_url}")
        except Exception as e:
            print(f"⚠️ Error conectando a base de datos: {e}")
            self._init_fallback()
    
    def _init_fallback(self):
        """Inicializa fallback a archivos JSON"""
        self.data_dir = Path(self.config.memory_dir if self.config.memory_dir else "data") / "ai_agent_business"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.engine = None
        self.Session = None
    
    def get_session(self) -> Optional[Session]:
        """Obtiene una sesión de base de datos"""
        if self.Session is None:
            return None
        return self.Session()
    
    # Métodos CRUD para Companies
    def create_company(
        self,
        company_name: str,
        contact_email: str,
        company_description: Optional[str] = None,
        plan: str = "free",
        website_url: Optional[str] = None
    ) -> Company:
        """Crea una nueva empresa"""
        company_id = str(uuid.uuid4())
        widget_script_id = hashlib.md5(f"{company_id}{datetime.now().isoformat()}".encode()).hexdigest()[:16]
        
        if self.use_fallback:
            company = Company(
                company_id=company_id,
                company_name=company_name,
                company_description=company_description,
                contact_email=contact_email,
                plan=plan,
                widget_script_id=widget_script_id,
                website_url=website_url
            )
            # Guardar en JSON
            companies_file = self.data_dir / "companies.json"
            companies = {}
            if companies_file.exists():
                with open(companies_file, 'r', encoding='utf-8') as f:
                    companies = json.load(f)
            companies[company_id] = asdict(company)
            with open(companies_file, 'w', encoding='utf-8') as f:
                json.dump(companies, f, indent=2, ensure_ascii=False)
            return company
        
        with self.get_session() as session:
            company_db = CompanyDB(
                company_id=company_id,
                company_name=company_name,
                company_description=company_description,
                contact_email=contact_email,
                plan=plan,
                widget_script_id=widget_script_id,
                website_url=website_url,
                company_config={}
            )
            session.add(company_db)
            session.commit()
            
            return Company(
                company_id=company_id,
                company_name=company_name,
                company_description=company_description,
                contact_email=contact_email,
                plan=plan,
                widget_script_id=widget_script_id,
                website_url=website_url
            )
    
    def get_company(self, company_id: str) -> Optional[Company]:
        """Obtiene una empresa"""
        if self.use_fallback:
            companies_file = self.data_dir / "companies.json"
            if not companies_file.exists():
                return None
            with open(companies_file, 'r', encoding='utf-8') as f:
                companies = json.load(f)
            if company_id not in companies:
                return None
            data = companies[company_id]
            return Company(**data)
        
        with self.get_session() as session:
            company_db = session.query(CompanyDB).filter_by(company_id=company_id).first()
            if not company_db:
                return None
            return Company(
                company_id=company_db.company_id,
                company_name=company_db.company_name,
                company_description=company_db.company_description,
                contact_email=company_db.contact_email,
                plan=company_db.plan,
                widget_script_id=company_db.widget_script_id,
                website_url=company_db.website_url,
                config=company_db.company_config or {}
            )
    
    def get_company_by_widget_id(self, widget_script_id: str) -> Optional[Company]:
        """Obtiene empresa por widget script ID"""
        if self.use_fallback:
            companies_file = self.data_dir / "companies.json"
            if not companies_file.exists():
                return None
            with open(companies_file, 'r', encoding='utf-8') as f:
                companies = json.load(f)
            for company_id, data in companies.items():
                if data.get("widget_script_id") == widget_script_id:
                    # Asegurar que config existe
                    if "config" not in data:
                        data["config"] = {}
                    return Company(**data)
            return None
        
        with self.get_session() as session:
            company_db = session.query(CompanyDB).filter_by(widget_script_id=widget_script_id).first()
            if not company_db:
                return None
            return Company(
                company_id=company_db.company_id,
                company_name=company_db.company_name,
                company_description=company_db.company_description,
                contact_email=company_db.contact_email,
                plan=company_db.plan,
                widget_script_id=company_db.widget_script_id,
                website_url=company_db.website_url,
                config=company_db.company_config or {}
            )
    
    # Métodos para Products
    def add_product(
        self,
        company_id: str,
        product_name: str,
        product_description: Optional[str] = None,
        price: Optional[float] = None,
        currency: str = "USD",
        product_url: Optional[str] = None,
        category: Optional[str] = None
    ) -> Product:
        """Agrega un producto a una empresa"""
        product_id = str(uuid.uuid4())
        
        if self.use_fallback:
            product = Product(
                product_id=product_id,
                company_id=company_id,
                product_name=product_name,
                product_description=product_description,
                price=price,
                currency=currency,
                product_url=product_url,
                category=category
            )
            products_file = self.data_dir / f"products_{company_id}.json"
            products = []
            if products_file.exists():
                with open(products_file, 'r', encoding='utf-8') as f:
                    products = json.load(f)
            products.append(asdict(product))
            with open(products_file, 'w', encoding='utf-8') as f:
                json.dump(products, f, indent=2, ensure_ascii=False)
            return product
        
        with self.get_session() as session:
            product_db = ProductDB(
                product_id=product_id,
                company_id=company_id,
                product_name=product_name,
                product_description=product_description,
                price=price,
                currency=currency,
                product_url=product_url,
                category=category
            )
            session.add(product_db)
            session.commit()
            
            return Product(
                product_id=product_id,
                company_id=company_id,
                product_name=product_name,
                product_description=product_description,
                price=price,
                currency=currency,
                product_url=product_url,
                category=category
            )
    
    def get_products(self, company_id: str) -> List[Product]:
        """Obtiene productos de una empresa"""
        if self.use_fallback:
            products_file = self.data_dir / f"products_{company_id}.json"
            if not products_file.exists():
                return []
            with open(products_file, 'r', encoding='utf-8') as f:
                products_data = json.load(f)
            return [Product(**p) for p in products_data]
        
        with self.get_session() as session:
            products_db = session.query(ProductDB).filter_by(company_id=company_id).all()
            return [
                Product(
                    product_id=p.product_id,
                    company_id=p.company_id,
                    product_name=p.product_name,
                    product_description=p.product_description,
                    price=p.price,
                    currency=p.currency,
                    product_url=p.product_url,
                    category=p.category,
                    in_stock=p.in_stock
                )
                for p in products_db
            ]
    
    # Métodos para Leads
    def create_lead(
        self,
        company_id: str,
        intent: str,
        name: Optional[str] = None,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        message: Optional[str] = None,
        channel: str = "web_widget",
        product_interested: Optional[str] = None
    ) -> Lead:
        """Crea un lead"""
        lead_id = str(uuid.uuid4())
        
        lead = Lead(
            lead_id=lead_id,
            company_id=company_id,
            name=name,
            email=email,
            phone=phone,
            intent=intent,
            product_interested=product_interested,
            message=message,
            channel=channel
        )
        
        if self.use_fallback:
            leads_file = self.data_dir / f"leads_{company_id}.json"
            leads = []
            if leads_file.exists():
                with open(leads_file, 'r', encoding='utf-8') as f:
                    leads = json.load(f)
            leads.append(asdict(lead))
            with open(leads_file, 'w', encoding='utf-8') as f:
                json.dump(leads, f, indent=2, ensure_ascii=False)
            return lead
        
        with self.get_session() as session:
            lead_db = LeadDB(
                lead_id=lead_id,
                company_id=company_id,
                name=name,
                email=email,
                phone=phone,
                intent=intent,
                product_interested=product_interested,
                message=message,
                channel=channel,
                status="new"
            )
            session.add(lead_db)
            session.commit()
        
        return lead
    
    def get_leads(self, company_id: str, limit: int = 100) -> List[Lead]:
        """Obtiene leads de una empresa"""
        if self.use_fallback:
            leads_file = self.data_dir / f"leads_{company_id}.json"
            if not leads_file.exists():
                return []
            with open(leads_file, 'r', encoding='utf-8') as f:
                leads_data = json.load(f)
            return [Lead(**l) for l in leads_data[-limit:]]
        
        with self.get_session() as session:
            leads_db = session.query(LeadDB).filter_by(company_id=company_id).order_by(LeadDB.created_at.desc()).limit(limit).all()
            return [
                Lead(
                    lead_id=l.lead_id,
                    company_id=l.company_id,
                    name=l.name,
                    email=l.email,
                    phone=l.phone,
                    intent=l.intent,
                    product_interested=l.product_interested,
                    message=l.message,
                    channel=l.channel,
                    status=l.status
                )
                for l in leads_db
            ]
    
    # Métodos para Conversations
    def create_conversation(
        self,
        company_id: str,
        channel: str = "web_widget",
        user_id: Optional[str] = None
    ) -> Conversation:
        """Crea una nueva conversación"""
        conversation_id = str(uuid.uuid4())
        if not user_id:
            user_id = f"user_{hashlib.md5(f'{company_id}{datetime.now().isoformat()}'.encode()).hexdigest()[:12]}"
        
        conversation = Conversation(
            conversation_id=conversation_id,
            company_id=company_id,
            channel=channel,
            user_id=user_id
        )
        
        if self.use_fallback:
            convs_file = self.data_dir / f"conversations_{company_id}.json"
            conversations = []
            if convs_file.exists():
                with open(convs_file, 'r', encoding='utf-8') as f:
                    conversations = json.load(f)
            conversations.append(asdict(conversation))
            with open(convs_file, 'w', encoding='utf-8') as f:
                json.dump(conversations, f, indent=2, ensure_ascii=False, default=str)
            return conversation
        
        with self.get_session() as session:
            conv_db = ConversationDB(
                conversation_id=conversation_id,
                company_id=company_id,
                channel=channel,
                user_id=user_id,
                status="active"
            )
            session.add(conv_db)
            session.commit()
        
        return conversation
    
    def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        intent_detected: Optional[str] = None
    ):
        """Agrega un mensaje a una conversación"""
        message_id = str(uuid.uuid4())
        message_data = {
            "message_id": message_id,
            "conversation_id": conversation_id,
            "role": role,
            "content": content,
            "intent_detected": intent_detected,
            "created_at": datetime.now().isoformat()
        }
        
        if self.use_fallback:
            messages_file = self.data_dir / f"messages_{conversation_id}.json"
            messages = []
            if messages_file.exists():
                with open(messages_file, 'r', encoding='utf-8') as f:
                    messages = json.load(f)
            messages.append(message_data)
            with open(messages_file, 'w', encoding='utf-8') as f:
                json.dump(messages, f, indent=2, ensure_ascii=False)
            return
        
        with self.get_session() as session:
            # Obtener company_id desde conversation
            conv_db = session.query(ConversationDB).filter_by(conversation_id=conversation_id).first()
            if not conv_db:
                return
            
            message_db = MessageDB(
                message_id=message_id,
                conversation_id=conversation_id,
                role=role,
                content=content,
                intent_detected=intent_detected
            )
            session.add(message_db)
            
            # Actualizar intent en conversación si hay
            if intent_detected and not conv_db.intent_detected:
                conv_db.intent_detected = intent_detected
            conv_db.updated_at = datetime.utcnow()
            
            session.commit()
    
    def get_conversation_messages(self, conversation_id: str) -> List[Dict[str, Any]]:
        """Obtiene mensajes de una conversación"""
        if self.use_fallback:
            messages_file = self.data_dir / f"messages_{conversation_id}.json"
            if not messages_file.exists():
                return []
            with open(messages_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        
        with self.get_session() as session:
            messages_db = session.query(MessageDB).filter_by(conversation_id=conversation_id).order_by(MessageDB.created_at).all()
            return [
                {
                    "role": m.role,
                    "content": m.content,
                    "created_at": m.created_at.isoformat() if m.created_at else None
                }
                for m in messages_db
            ]


# ==================== AGENTE CONVERSACIONAL ====================

class BusinessAgentConversationalAI:
    """Agente conversacional de IA para ventas y soporte"""
    
    def __init__(self, config: AppConfig, provider: str = "openai", api_key: Optional[str] = None):
        self.config = config
        self.provider = provider
        
        # Usar API key proporcionada, o intentar obtenerla de config/env
        if not api_key:
            api_key = os.getenv("OPENAI_API_KEY") or getattr(config, 'openai_api_key', None)
            if not api_key:
                # Intentar cargar desde .env manualmente
                env_path = Path(__file__).parent.parent / ".env"
                if env_path.exists():
                    try:
                        with open(env_path, 'r', encoding='utf-8') as f:
                            for line in f:
                                if line.startswith('OPENAI_API_KEY='):
                                    api_key = line.split('=', 1)[1].strip().strip('"').strip("'")
                                    break
                    except Exception:
                        pass
        
        # Inicializar LLM
        if provider == "openai":
            if not api_key:
                print("⚠️ ADVERTENCIA: OPENAI_API_KEY no encontrada. El agente usará respuestas de fallback.")
                self.llm = None
            else:
                try:
                    self.llm = ChatOpenAI(
                        model="gpt-4o-mini",
                        temperature=0.7,
                        api_key=api_key
                    )
                except Exception as e:
                    print(f"⚠️ Error inicializando LLM: {e}")
                    self.llm = None
        elif provider == "anthropic" or provider == "claude":
            api_key = os.getenv("ANTHROPIC_API_KEY")
            self.llm = ChatAnthropic(
                model="claude-3-5-sonnet-20241022",
                temperature=0.7,
                api_key=api_key
            )
        else:
            # Fallback a OpenAI
            api_key = os.getenv("OPENAI_API_KEY") or config.openai_api_key
            self.llm = ChatOpenAI(
                model="gpt-4o-mini",
                temperature=0.7,
                api_key=api_key
            )
    
    def detect_intent(self, message: str) -> str:
        """Detecta la intención del mensaje"""
        prompt = f"""Analiza el siguiente mensaje y determina la intención del usuario. 

Opciones:
- product_inquiry: Pregunta sobre productos o servicios específicos
- pricing: Pregunta sobre precios, costos, tarifas
- purchase: Quiere comprar, hacer pedido, contratar
- support: Necesita ayuda, tiene problema, pregunta de soporte técnico
- greeting: Saludo inicial (hola, buenos días, etc.)
- goodbye: Despedida (adiós, gracias, hasta luego)
- other: Otra intención

Mensaje: "{message}"

Responde SOLO con la intención (ejemplo: product_inquiry)."""
        
        try:
            if self.llm is None:
                # Fallback simple sin LLM
                msg_lower = message.lower()
                if any(word in msg_lower for word in ["hola", "buenos días", "buenas tardes", "hi", "hello"]):
                    return "greeting"
                elif any(word in msg_lower for word in ["producto", "servicio", "tienen", "ofrecen"]):
                    return "product_inquiry"
                elif any(word in msg_lower for word in ["precio", "cuesta", "costo", "tarifa", "cuanto"]):
                    return "pricing"
                elif any(word in msg_lower for word in ["comprar", "quiero", "deseo", "contratar", "adquirir"]):
                    return "purchase"
                elif any(word in msg_lower for word in ["ayuda", "soporte", "problema", "error"]):
                    return "support"
                else:
                    return "other"
            
            response = self.llm.invoke([HumanMessage(content=prompt)]).content.strip().lower()
            # Normalizar respuesta
            for intent in ["product_inquiry", "pricing", "purchase", "support", "greeting", "goodbye"]:
                if intent in response:
                    return intent
            return "other"
        except Exception as e:
            print(f"⚠️ Error detectando intención: {e}")
            # Fallback simple
            msg_lower = message.lower()
            if any(word in msg_lower for word in ["hola", "buenos días", "hi"]):
                return "greeting"
            elif any(word in msg_lower for word in ["producto", "tienen"]):
                return "product_inquiry"
            elif any(word in msg_lower for word in ["precio", "cuesta"]):
                return "pricing"
            return "other"
    
    def generate_response(
        self,
        message: str,
        company: Company,
        products: List[Product],
        faqs: List[Dict[str, Any]],
        conversation_history: List[Dict[str, Any]],
        intent: Optional[str] = None
    ) -> str:
        """Genera respuesta del agente"""
        
        # Construir contexto de la empresa
        company_context = f"""
Empresa: {company.company_name}
Descripción: {company.company_description or "No disponible"}
"""
        
        # Construir contexto de productos
        products_context = ""
        if products:
            products_context = "\n\nProductos/Servicios disponibles:\n"
            for product in products[:10]:  # Limitar a 10 productos
                price_str = f" - Precio: {product.currency} {product.price}" if product.price else " - Consultar precio"
                url_str = f" - Link: {product.product_url}" if product.product_url else ""
                products_context += f"- {product.product_name}\n"
                if product.product_description:
                    products_context += f"  Descripción: {product.product_description[:200]}...\n"
                products_context += f"  {price_str}{url_str}\n"
        
        # Construir contexto de FAQs
        faqs_context = ""
        if faqs:
            faqs_context = "\n\nPreguntas Frecuentes (FAQs):\n"
            for faq in faqs[:5]:  # Limitar a 5 FAQs
                faqs_context += f"P: {faq.get('question', '')}\nR: {faq.get('answer', '')}\n\n"
        
        # Construir historial de conversación
        history_context = ""
        if conversation_history:
            history_context = "\n\nHistorial de conversación:\n"
            for msg in conversation_history[-6:]:  # Últimas 6 mensajes
                role = "Usuario" if msg.get("role") == "user" else "Asistente"
                history_context += f"{role}: {msg.get('content', '')}\n"
        
        # Prompt del sistema
        system_prompt = f"""Eres un asistente de ventas y soporte al cliente profesional y amigable para {company.company_name}.

Tu objetivo es:
1. Responder preguntas sobre productos y servicios de forma clara y concisa
2. Proporcionar información de precios cuando sea relevante
3. Facilitar compras proporcionando enlaces o información de contacto
4. Resolver preguntas de soporte básicas usando las FAQs
5. Capturar leads cuando el usuario esté interesado (pedir nombre, email, teléfono)
6. Escalar a un humano cuando la consulta sea compleja o el usuario lo solicite explícitamente

Reglas importantes:
- Sé breve y directo (máximo 2-3 frases por respuesta)
- Mantén un tono profesional pero amigable
- Si no sabes algo, ofrece escalar a un humano
- Siempre ofrece ayuda adicional al final
- Si detectas interés de compra, ofrece capturar información de contacto
- Usa emojis con moderación (máximo 1-2 por mensaje)
- Si hay productos relevantes, menciona 1-2 con sus links

Información de la empresa:
{company_context}
{products_context}
{faqs_context}
{history_context}

Mensaje del usuario: "{message}"

Genera una respuesta breve, profesional y útil."""
        
        try:
            if self.llm is None:
                # Fallback sin LLM - respuesta básica
                intent_lower = (intent or "").lower()
                if intent_lower == "greeting":
                    return f"¡Hola! Bienvenido a {company.company_name}. ¿En qué puedo ayudarte hoy?"
                elif intent_lower == "product_inquiry":
                    if products:
                        products_list = "\n".join([f"- {p.product_name}" for p in products[:5]])
                        return f"Tenemos los siguientes productos disponibles:\n{products_list}\n\n¿Te interesa alguno en particular?"
                    else:
                        return "Tenemos varios productos disponibles. ¿Podrías decirme qué tipo de producto o servicio buscas?"
                elif intent_lower == "pricing":
                    if products:
                        prices_list = "\n".join([f"- {p.product_name}: {p.currency} {p.price:.2f}" if p.price else f"- {p.product_name}: Consultar precio" for p in products[:3]])
                        return f"Precios de nuestros productos:\n{prices_list}\n\n¿Te interesa algún plan en particular?"
                    else:
                        return "Estaré encantado de ayudarte con información de precios. ¿Qué producto te interesa?"
                else:
                    return f"Hola, gracias por contactar a {company.company_name}. ¿En qué puedo ayudarte?"
            
            messages = [SystemMessage(content=system_prompt), HumanMessage(content=message)]
            response = self.llm.invoke(messages).content.strip()
            return response
        except Exception as e:
            print(f"⚠️ Error generando respuesta: {e}")
            # Respuesta de fallback mejorada
            intent_lower = (intent or "").lower()
            if intent_lower == "greeting":
                return f"¡Hola! Bienvenido a {company.company_name}. ¿En qué puedo ayudarte?"
            elif intent_lower in ["product_inquiry", "pricing"]:
                if products:
                    return f"Tenemos {len(products)} productos disponibles. ¿Te interesa conocer más sobre alguno en particular?"
                return "Tenemos varios productos disponibles. ¿Qué tipo de producto buscas?"
            return "Lo siento, hubo un error procesando tu mensaje. ¿Puedes intentar de nuevo o prefieres hablar con un agente humano?"


# ==================== CLASE PRINCIPAL ====================

class AIAgentBusinessManagerMode:
    """Modo principal: AI Agent Business Manager - Sistema SaaS Multi-Tenant"""
    
    def __init__(self, config: AppConfig, provider: str = "openai"):
        self.config = config
        self.provider = provider
        
        # Inicializar componentes
        self.db_manager = BusinessAgentDatabaseManager(config)
        # El conversational_ai se inicializa sin LLM por defecto, se configurará por empresa
        self.conversational_ai = None  # Se inicializará por empresa cuando tengan API key
        
        print("✅ AI Agent Business Manager Mode inicializado")
    
    def create_company(
        self,
        company_name: str,
        contact_email: str,
        company_description: Optional[str] = None,
        plan: str = "free",
        website_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """Crea una nueva empresa y retorna su configuración"""
        company = self.db_manager.create_company(
            company_name=company_name,
            contact_email=contact_email,
            company_description=company_description,
            plan=plan,
            website_url=website_url
        )
        
        return {
            "company_id": company.company_id,
            "company_name": company.company_name,
            "widget_script_id": company.widget_script_id,
            "widget_code": self._generate_widget_code(company.widget_script_id),
            "status": "created"
        }
    
    def _generate_widget_code(self, widget_script_id: str) -> str:
        """Genera el código JavaScript del widget"""
        # Obtener URL base (detectar automáticamente o usar variable de entorno)
        base_url = os.getenv("AI_AGENT_BASE_URL")
        if not base_url:
            # Intentar detectar desde configuración
            base_url = "https://tu-servidor.com"  # Reemplazar en producción
        
        widget_code = f"""<!-- AI Agent Business Manager Widget -->
<script>
(function() {{
    var widgetConfig = {{
        scriptId: '{widget_script_id}',
        apiUrl: (window.location.origin || '{base_url}') + '/api/ai-agent-business',
        position: 'bottom-right'
    }};
    
    var script = document.createElement('script');
    script.src = (window.location.origin || '{base_url}') + '/static/ai-agent-widget.js';
    script.async = true;
    script.setAttribute('data-config', JSON.stringify(widgetConfig));
    document.head.appendChild(script);
}})();
</script>"""
        return widget_code
    
    def process_message(
        self,
        widget_script_id: str,
        message: str,
        user_id: Optional[str] = None,
        channel: str = "web_widget"
    ) -> Dict[str, Any]:
        """Procesa un mensaje del usuario y genera respuesta"""
        
        # Obtener empresa
        company = self.db_manager.get_company_by_widget_id(widget_script_id)
        if not company:
            return {
                "error": "Company not found",
                "response": "Lo siento, no se pudo identificar la empresa. Por favor, contacta al soporte."
            }
        
        # Obtener o crear conversación
        conversation = self.db_manager.create_conversation(
            company_id=company.company_id,
            channel=channel,
            user_id=user_id
        )
        
        # Agregar mensaje del usuario
        self.db_manager.add_message(
            conversation_id=conversation.conversation_id,
            role="user",
            content=message
        )
        
        # Detectar intención
        intent = self.conversational_ai.detect_intent(message)
        
        # Obtener productos y FAQs
        products = self.db_manager.get_products(company.company_id)
        
        # Obtener historial de conversación
        history = self.db_manager.get_conversation_messages(conversation.conversation_id)
        
        # Generar respuesta
        try:
            response = conversational_ai.generate_response(
                message=message,
                company=company,
                products=products,
                faqs=[],  # TODO: Implementar FAQs
                conversation_history=history,
                intent=intent
            )
        except Exception as e:
            print(f"⚠️ Error generando respuesta: {e}")
            response = "Lo siento, hubo un error generando la respuesta. Por favor, intenta de nuevo o contacta con soporte."
        
        # Agregar respuesta del asistente
        self.db_manager.add_message(
            conversation_id=conversation.conversation_id,
            role="assistant",
            content=response,
            intent_detected=intent
        )
        
        # Detectar si se debe crear lead o escalar
        should_create_lead = False
        should_escalate = False
        
        message_lower = message.lower()
        
        # Detectar intención de compra o interés
        purchase_keywords = ["quiero", "deseo", "interesado", "me gustaría", "quiero comprar", "deseo adquirir", "quiero contratar", "me interesa", "necesito", "quiero información"]
        if intent in ["purchase", "product_inquiry", "pricing"] and any(keyword in message_lower for keyword in purchase_keywords):
            should_create_lead = True
        
        # Detectar solicitud de escalación
        escalation_keywords = ["hablar con humano", "hablar con agente", "hablar con persona", "quiero hablar con", "necesito hablar con", "transferir a humano", "escalar"]
        if any(keyword in message_lower for keyword in escalation_keywords):
            should_escalate = True
            # Agregar mensaje de escalación a la respuesta
            response += "\n\n💬 He notificado a nuestro equipo. Un agente humano se pondrá en contacto contigo pronto."
        
        return {
            "conversation_id": conversation.conversation_id,
            "response": response,
            "intent": intent,
            "should_create_lead": should_create_lead,
            "should_escalate": should_escalate
        }
    
    def get_analytics(self, company_id: str, days: int = 30) -> Dict[str, Any]:
        """Obtiene analytics de una empresa"""
        leads = self.db_manager.get_leads(company_id, limit=1000)
        
        # Calcular métricas
        total_leads = len(leads)
        leads_by_intent = {}
        for lead in leads:
            intent = lead.intent or "other"
            leads_by_intent[intent] = leads_by_intent.get(intent, 0) + 1
        
        return {
            "company_id": company_id,
            "period_days": days,
            "total_leads": total_leads,
            "leads_by_intent": leads_by_intent,
            "leads_by_channel": {
                "web_widget": len([l for l in leads if l.channel == "web_widget"]),
                "whatsapp": len([l for l in leads if l.channel == "whatsapp"])
            }
        }
    
    def add_product(
        self,
        company_id: str,
        product_name: str,
        product_description: Optional[str] = None,
        price: Optional[float] = None,
        currency: str = "USD",
        product_url: Optional[str] = None,
        category: Optional[str] = None
    ) -> Dict[str, Any]:
        """Agrega un producto a una empresa"""
        product = self.db_manager.add_product(
            company_id=company_id,
            product_name=product_name,
            product_description=product_description,
            price=price,
            currency=currency,
            product_url=product_url,
            category=category
        )
        
        return {
            "product_id": product.product_id,
            "product_name": product.product_name,
            "status": "created"
        }
    
    def get_company_config(self, company_id: str) -> Dict[str, Any]:
        """Obtiene configuración completa de una empresa"""
        company = self.db_manager.get_company(company_id)
        if not company:
            return {"error": "Company not found"}
        
        products = self.db_manager.get_products(company_id)
        leads = self.db_manager.get_leads(company_id, limit=50)
        
        return {
            "company": {
                "company_id": company.company_id,
                "company_name": company.company_name,
                "company_description": company.company_description,
                "widget_script_id": company.widget_script_id,
                "widget_code": self._generate_widget_code(company.widget_script_id),
                "plan": company.plan,
                "website_url": company.website_url
            },
            "products": [
                {
                    "product_id": p.product_id,
                    "product_name": p.product_name,
                    "price": p.price,
                    "currency": p.currency,
                    "product_url": p.product_url
                }
                for p in products
            ],
            "total_leads": len(leads),
            "recent_leads": [
                {
                    "lead_id": l.lead_id,
                    "name": l.name,
                    "email": l.email,
                    "intent": l.intent,
                    "created_at": "recent"
                }
                for l in leads[:10]
            ]
        }
    
    def configure_company_api_key(
        self,
        company_id: str,
        openai_api_key: Optional[str] = None,
        anthropic_api_key: Optional[str] = None,
        provider: str = "openai"
    ) -> Dict[str, Any]:
        """Configura la API key de una empresa para usar su propio LLM"""
        company = self.db_manager.get_company(company_id)
        if not company:
            return {"error": "Company not found"}
        
        # Actualizar configuración de la empresa
        company_config = company.config.copy() if company.config else {}
        
        if openai_api_key:
            company_config["openai_api_key"] = openai_api_key
            company_config["llm_provider"] = "openai"
        if anthropic_api_key:
            company_config["anthropic_api_key"] = anthropic_api_key
            company_config["llm_provider"] = "anthropic"
        if provider:
            company_config["llm_provider"] = provider
        
        # Guardar configuración actualizada
        if self.db_manager.use_fallback:
            companies_file = self.db_manager.data_dir / "companies.json"
            if companies_file.exists():
                with open(companies_file, 'r', encoding='utf-8') as f:
                    companies = json.load(f)
                if company_id in companies:
                    companies[company_id]["config"] = company_config
                    with open(companies_file, 'w', encoding='utf-8') as f:
                        json.dump(companies, f, indent=2, ensure_ascii=False)
        else:
            with self.db_manager.get_session() as session:
                company_db = session.query(CompanyDB).filter_by(company_id=company_id).first()
                if company_db:
                    company_db.company_config = company_config
                    session.commit()
        
        return {
            "status": "configured",
            "message": "API key configurada correctamente",
            "provider": company_config.get("llm_provider", provider)
        }
    
    def configure_whatsapp(
        self,
        company_id: str,
        phone_number: str,
        verify_token: Optional[str] = None,
        access_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """Configura WhatsApp Business para una empresa"""
        company = self.db_manager.get_company(company_id)
        if not company:
            return {"error": "Company not found"}
        
        base_url = os.getenv("AI_AGENT_BASE_URL", "http://localhost:7860")
        webhook_url = f"{base_url}/api/ai-agent-business/whatsapp/webhook/{company_id}"
        
        # Guardar configuración
        whatsapp_config = {
            "phone_number": phone_number,
            "verify_token": verify_token,
            "access_token": access_token,
            "webhook_url": webhook_url,
            "verified": verify_token is not None,
            "webhook_verified": False,
            "setup_date": datetime.now().isoformat()
        }
        
        if self.db_manager.use_fallback:
            config_file = self.db_manager.data_dir / f"whatsapp_{company_id}.json"
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(whatsapp_config, f, indent=2)
            return {
                "status": "configured",
                "phone_number": phone_number,
                "webhook_url": webhook_url,
                "instructions": f"""
### ✅ WhatsApp Configurado

**📋 Pasos para completar la configuración:**

1. Ve a https://developers.facebook.com/apps/
2. Selecciona tu App → WhatsApp → Configuration
3. Configura el Webhook:
   - **Callback URL**: `{webhook_url}`
   - **Verify Token**: `{verify_token or 'tu_token_aqui'}`
4. Haz clic en "Verify and Save"
5. En "Webhook fields", selecciona:
   - ✅ messages
   - ✅ message_status
6. Guarda los cambios

**🔑 Access Token:**
Si tienes un Access Token de Meta, guárdalo de forma segura (no se almacena en texto plano en producción).

**✅ Una vez verificado, el agente comenzará a responder automáticamente en WhatsApp.**
"""
            }
        
        # Actualizar en base de datos
        with self.db_manager.get_session() as session:
            company_db = session.query(CompanyDB).filter_by(company_id=company_id).first()
            if company_db:
                company_db.whatsapp_phone_number = phone_number
                company_db.whatsapp_verified = verify_token is not None
                # Guardar config en JSON column
                if not company_db.company_config:
                    company_db.company_config = {}
                company_db.company_config["whatsapp"] = whatsapp_config
                session.commit()
        
        return {
            "status": "configured",
            "phone_number": phone_number,
            "webhook_url": webhook_url,
            "instructions": f"Webhook URL: {webhook_url}"
        }
    
    def send_whatsapp_message(
        self,
        company_id: str,
        phone_number: str,
        message: str
    ) -> Dict[str, Any]:
        """Envía un mensaje a través de WhatsApp Business API"""
        company = self.db_manager.get_company(company_id)
        if not company:
            return {"error": "Company not found"}
        
        # Obtener access token
        whatsapp_config = None
        if self.db_manager.use_fallback:
            config_file = self.db_manager.data_dir / f"whatsapp_{company_id}.json"
            if config_file.exists():
                with open(config_file, 'r', encoding='utf-8') as f:
                    whatsapp_config = json.load(f)
        else:
            with self.db_manager.get_session() as session:
                company_db = session.query(CompanyDB).filter_by(company_id=company_id).first()
                if company_db and company_db.company_config:
                    whatsapp_config = company_db.company_config.get("whatsapp")
        
        if not whatsapp_config or not whatsapp_config.get("access_token"):
            return {"error": "WhatsApp not configured or access token missing"}
        
        # Enviar mensaje usando Meta Cloud API
        try:
            import requests
            
            access_token = whatsapp_config["access_token"]
            phone_number_id = whatsapp_config.get("phone_number_id")  # ID del número de WhatsApp Business
            
            url = f"https://graph.facebook.com/v18.0/{phone_number_id}/messages"
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            payload = {
                "messaging_product": "whatsapp",
                "to": phone_number,
                "type": "text",
                "text": {
                    "body": message
                }
            }
            
            response = requests.post(url, headers=headers, json=payload, timeout=10)
            
            if response.status_code == 200:
                return {
                    "success": True,
                    "message_id": response.json().get("messages", [{}])[0].get("id")
                }
            else:
                return {
                    "success": False,
                    "error": f"API Error: {response.status_code} - {response.text}"
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

