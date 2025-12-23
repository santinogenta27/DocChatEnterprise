"""Gradio app for Enterprise Data AI - Multi-Agent RAG with Autonomous Agents."""

from __future__ import annotations

import os
import sys

# FIX PARA WINDOWS: Configurar codificación UTF-8 para evitar errores con emojis
# Esto debe estar ANTES de cualquier import que pueda hacer print con emojis
if sys.platform == "win32":
    # Configurar stdout y stderr para usar UTF-8
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except AttributeError:
        # Python < 3.7 fallback
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    
    # También configurar la variable de entorno para subprocesos
    os.environ["PYTHONIOENCODING"] = "utf-8"

import json
import uuid
import asyncio
import time
import tempfile
import shutil
from typing import List, Optional, Dict, Any
from pathlib import Path
from datetime import datetime

import gradio as gr
from dotenv import load_dotenv

# CONFIGURAR DIRECTORIO TEMPORAL ALTERNATIVO si el disco C: está lleno
# Intentar usar otro disco si está disponible (D:, E:, etc.)
try:
    # Verificar espacio en C:
    import shutil
    _, _, free_c = shutil.disk_usage("C:\\")
    free_c_gb = free_c / (1024**3)
    
    if free_c_gb < 1.0:  # Menos de 1 GB libre en C:
        # Buscar otro disco con espacio disponible
        alternative_drive = None
        for drive_letter in ['D', 'E', 'F', 'G', 'H']:
            try:
                drive_path = f"{drive_letter}:\\"
                _, _, free_alt = shutil.disk_usage(drive_path)
                free_alt_gb = free_alt / (1024**3)
                if free_alt_gb > 5.0:  # Al menos 5 GB libres
                    alternative_drive = drive_path
                    print(f"✅ Encontrado disco alternativo: {drive_letter}: con {free_alt_gb:.2f} GB libres")
                    break
            except:
                continue
        
        if alternative_drive:
            # Usar disco alternativo para archivos temporales
            alt_temp_dir = Path(alternative_drive) / "gradio_temp"
            alt_temp_dir.mkdir(exist_ok=True)
            
            # Configurar variables de entorno para Gradio y Python
            os.environ["GRADIO_TEMP_DIR"] = str(alt_temp_dir)
            os.environ["TMPDIR"] = str(alt_temp_dir)
            os.environ["TEMP"] = str(alt_temp_dir)
            os.environ["TMP"] = str(alt_temp_dir)
            
            # También configurar tempfile
            tempfile.tempdir = str(alt_temp_dir)
            
            print(f"⚠️ Disco C: tiene poco espacio ({free_c_gb:.2f} GB).")
            print(f"✅ Usando disco {alternative_drive} para archivos temporales: {alt_temp_dir}")
        else:
            # Fallback: usar directorio del proyecto
            project_temp = Path(__file__).parent / ".gradio_temp"
            project_temp.mkdir(exist_ok=True)
            
            os.environ["GRADIO_TEMP_DIR"] = str(project_temp)
            os.environ["TMPDIR"] = str(project_temp)
            os.environ["TEMP"] = str(project_temp)
            os.environ["TMP"] = str(project_temp)
            tempfile.tempdir = str(project_temp)
            
            print(f"⚠️ Disco C: tiene poco espacio ({free_c_gb:.2f} GB). Usando directorio del proyecto: {project_temp}")
except Exception as e:
    print(f"⚠️ No se pudo configurar directorio temporal alternativo: {e}")

# MONKEY PATCH: Fix para bug de Gradio 4.40.0 con TypeError en api_info
# Este bug ocurre cuando schema es un bool en lugar de un dict en la línea 863
try:
    import gradio_client.utils as client_utils
    
    # Guardar la función original
    _original_get_type = client_utils.get_type
    
    def _patched_get_type(schema):
        """Monkey patch para evitar TypeError cuando schema es bool"""
        # Si schema no es un dict, retornar tipo por defecto
        if not isinstance(schema, dict):
            return "Any"
        # Verificar que "const" pueda ser buscado (schema debe ser dict)
        if "const" in schema:
            return "Literal"
        return _original_get_type(schema)
    
    # Aplicar el patch
    client_utils.get_type = _patched_get_type
    
    # También parchear _json_schema_to_python_type para mayor seguridad
    _original_json_schema_to_python_type = client_utils._json_schema_to_python_type
    
    def _patched_json_schema_to_python_type(schema, defs=None):
        """Monkey patch para evitar TypeError en _json_schema_to_python_type"""
        if not isinstance(schema, dict):
            return "Any"
        return _original_json_schema_to_python_type(schema, defs)
    
    client_utils._json_schema_to_python_type = _patched_json_schema_to_python_type
except Exception as e:
    print(f"⚠️ Warning: No se pudo aplicar monkey patch para Gradio: {e}")

# Cargar .env ANTES de cualquier otra cosa
env_path = Path(__file__).parent / ".env"
cwd_env_path = Path.cwd() / ".env"

env_file = None
if env_path.exists():
    env_file = env_path
    load_dotenv(dotenv_path=env_path, override=True)
elif cwd_env_path.exists():
    env_file = cwd_env_path
    load_dotenv(dotenv_path=cwd_env_path, override=True)
else:
    load_dotenv(override=True)

# Si load_dotenv no funcionó, leer el archivo manualmente
if env_file and not os.getenv("OPENAI_API_KEY"):
    try:
        content = env_file.read_text(encoding='utf-8-sig').strip()
        for line in content.split('\n'):
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if key == "OPENAI_API_KEY":
                    os.environ[key] = value
                    break
    except Exception:
        pass

# Importar componentes
from docchat import AppConfig, load_config
from docchat.document_processor import DocumentProcessor
from docchat.mass_processor import MassDocumentProcessor
from docchat.retriever_builder import RetrieverBuilder
from docchat.workflow import AgentWorkflow
from docchat.memory import MemoryStore, ContextManager
from docchat.autonomous_agent import AutonomousAgent
from docchat.advanced_agent import AdvancedAutonomousAgent
from docchat.enterprise_api import EnterpriseAPIMode
from docchat.intelligence_contract_mode import IntelligenceContractMode
from docchat.copilot_mode import CopilotMode
from docchat.advice_god_mode import AdviceGodMode, get_advice_god_mode, run_advice_god_mode
# from docchat.optimus_mode import OptimusMode, get_optimus_mode, run_optimus_mode  # ELIMINADO
from docchat.marketplace_mode import MarketplaceMode, get_marketplace_mode, run_marketplace_mode, PricingTier, AdStatus, CreatorTier
from docchat.optimus_prime_mode import OptimusPrimeMode, get_optimus_prime_mode, run_optimus_prime_mode
from docchat.extasis_mode import ExtasisMode, get_extasis_mode, run_extasis_mode
from docchat.enterprise_api_stargate import StargatePDFMode
from docchat.enterprise_api_data_sight import DataSightMode
from docchat.data_sight_integrations import DataSightIntegrations
from docchat.data_sight_automation import DataSightAutomation, AutomationRule
from docchat.enterprise_api_mdp import EnterpriseAPIMDPMode
from docchat.enterprise_api_supreme import EnterpriseAPISupremeMode
from docchat.enterprise_api_gold import EnterpriseAPIGoldMode
from docchat.chatdoc_mode import run_chatdoc, get_chatdoc
from docchat.pdf_converter import convert_to_pdf, TEXT_EXTENSIONS
from docchat.enterprise_autonomous_workflows import EnterpriseAutonomousWorkflows
from docchat.enterprise_data_intelligence import EnterpriseDataIntelligence
from docchat.agentic_workflow_orchestrator import AgenticWorkflowOrchestrator
from docchat.enterprise_agentic_ai import EnterpriseAgenticAI
from docchat.customer_service_agent import CustomerServiceAgent
from docchat.ads_optimization_mode import AdsOptimizationMode, get_ads_optimization_mode
from docchat.chatbot_mode import ChatbotMode
from docchat.text_to_action import TextToAction
from docchat.email_autonomous_agent import EmailAutonomousAgent
from docchat.multi_format_processor import MultiFormatProcessor
from docchat.ai_agent_business_manager_mode import AIAgentBusinessManagerMode
from docchat.iterative_learning_agent import IterativeLearningAgent
from docchat.chat_conversational_2 import run_chat_conversational_2, get_chat_conversational_2
from docchat.alien_mode import run_alien_mode, get_alien_mode
from docchat.pdf_agent_mode import run_pdf_agent_mode, get_pdf_agent_mode
from docchat.advantage_mode import run_advantage_mode, get_advantage_mode
from docchat.chat_pdf_mode import run_chat_pdf_mode, get_chat_pdf_mode
from docchat.snipe_shot_mode import run_snipe_shot_mode, get_snipe_shot_mode
from docchat.portal_ads_mode import run_portal_ads_mode, get_portal_ads_mode
from docchat.ad_llm_mode import run_ad_llm_mode, get_ad_llm_mode

# Importar Business AI Omnicanal y Top Ads Mode
try:
    from docchat.business_ai_omnicanal import BusinessAIMode
    BUSINESS_AI_AVAILABLE = True
except ImportError as e:
    BUSINESS_AI_AVAILABLE = False
    BusinessAIMode = None
    print(f"⚠️ Business AI Omnicanal no disponible: {e}")

# Importar Business AI Support
try:
    from docchat.business_ai_support import BusinessAISupportMode
    BUSINESS_AI_SUPPORT_AVAILABLE = True
except ImportError as e:
    BUSINESS_AI_SUPPORT_AVAILABLE = False
    BusinessAISupportMode = None
    print(f"⚠️ Business AI Support no disponible: {e}")

try:
    from docchat.top_ads_mode import TopAdsMode
    TOP_ADS_AVAILABLE = True
except ImportError as e:
    TOP_ADS_AVAILABLE = False
    TopAdsMode = None
    print(f"⚠️ Top Ads Mode no disponible: {e}")

from docchat.agent_builder_studio import (
    AgentBuilderStudio,
    AgentTemplate,
    DeploymentChannel,
    LLMProvider,
    get_agent_builder_studio,
    run_agent_builder_studio
)
from docchat.prime_agents_mode import run_prime_agents_mode, get_prime_agents_mode
from docchat.judge_agent_mode import run_judge_agent_mode, get_judge_agent_mode
from docchat.banking_mode import run_banking_mode, get_banking_mode
from docchat.event_bus_mode import run_event_bus_mode, get_event_bus_mode
from docchat.event_horizon_mode import run_event_horizon_mode, get_event_horizon_mode
from docchat.event_storage_mode import run_event_storage_mode, get_event_storage_mode
from docchat.extasis_mode import run_extasis_mode, get_extasis_mode
from docchat.extraction_x_mode import run_extraction_x_mode, get_extraction_x_mode

# Importar sistema de agentes AI para ventas
try:
    from sales_agent_system import SalesAgentSystem
    SALES_AGENT_AVAILABLE = True
    print("✅ Sistema de Agentes AI para Ventas cargado correctamente")
except ImportError as e:
    SALES_AGENT_AVAILABLE = False
    print(f"⚠️ Sistema de Agentes AI para Ventas no disponible: {e}")
    SalesAgentSystem = None
from docchat.data_point_mode import run_data_point_mode, get_data_point_mode
from docchat.enterprise_connectors import EnterpriseConnectorManager, ConnectorConfig, ConnectorStatus
from docchat.event_bus_mode import run_event_bus_mode, get_event_bus_mode
# Vision Alpha - manejo condicional si no tiene configuraciones
try:
    from docchat.vision_alpha import VisionAlphaMode, get_vision_alpha_mode, run_vision_alpha_mode
except (ImportError, Exception):
    VisionAlphaMode = None
    get_vision_alpha_mode = None
    run_vision_alpha_mode = None
from docchat.company_knowledge import get_company_knowledge, run_company_knowledge
from docchat.invoice import get_invoice_mode, run_invoice_mode
from docchat.fullstack_text_to_action import FullStackTextToAction
from docchat.web_recency_agent import WebRecencyAgent
from docchat.deep_chain_of_thought import DeepChainOfThoughtAgent
from docchat.automated_testing_system import AutomatedTestingSystem
from docchat.adversarial_ai_system import AdversarialAISystem
from docchat.collaborative_agents import CollaborativeAgentsSystem
from docchat.advanced_integration_system import AdvancedIntegrationSystem
from docchat.cloud_integrations import CloudStorageIntegration, WebhookProcessor
from docchat.rpa_automation import RPAAutomationEngine
from docchat.rpa_enterprise_integration import RPAEnterpriseIntegration
from docchat.semantic_data_engine import SemanticDataEngine, DataModality
from docchat.data_ingestion_engine import DataIngestionEngine
from docchat.audit import AuditLogger
from docchat.leads_mode import LeadsMode
from docchat.marketing_agent import MarketingAgent
from docchat.persistent_storage import PersistentStorage
from docchat.connections_manager import ConnectionsManager
from docchat.oauth_connections import RealConnectionsManager, GoogleOAuth, MicrosoftOAuth, DropboxOAuth

# Importar modo BANKS (con manejo de errores)
try:
    from docchat.banks import BanksMode
    BANKS_MODE_AVAILABLE = True
except Exception as e:
    print(f"⚠️ Advertencia: Modo BANKS no disponible: {e}")
    BANKS_MODE_AVAILABLE = False
    BanksMode = None

try:
    from docchat.accountability import get_accountability, run_accountability
    ACCOUNTABILITY_AVAILABLE = True
except Exception as e:
    print(f"⚠️ Advertencia: Accountability no disponible: {e}")
    ACCOUNTABILITY_AVAILABLE = False
    get_accountability = None
    run_accountability = None

try:
    from docchat.gmail_company_knowledge import GmailCompanyKnowledge
    from docchat.company_knowledge import get_company_knowledge
    GMAIL_COMPANY_KNOWLEDGE_AVAILABLE = True
except Exception as e:
    print(f"⚠️ Advertencia: Gmail Company Knowledge no disponible: {e}")
    GMAIL_COMPANY_KNOWLEDGE_AVAILABLE = False
    GmailCompanyKnowledge = None
    get_company_knowledge = None

# Check for vector store availability
try:
    try:
        from langchain_community.vectorstores import FAISS
        FAISS_AVAILABLE = True
    except ImportError:
        try:
            from langchain.vectorstores import FAISS
            FAISS_AVAILABLE = True
        except ImportError:
            FAISS_AVAILABLE = False
except Exception:
    FAISS_AVAILABLE = False

try:
    try:
        from langchain_community.vectorstores import Chroma
        Chroma = Chroma  # Keep reference
    except ImportError:
        try:
            from langchain.vectorstores import Chroma
        except ImportError:
            Chroma = None
except ImportError:
    Chroma = None
from docchat.auth import UserManager, WorkspaceManager

# Validar API key
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    env_content = ""
    if env_path.exists():
        try:
            env_content = env_path.read_text(encoding='utf-8-sig')
        except Exception as e:
            env_content = f"Error leyendo archivo: {e}"
    
    raise gr.Error(
        f"❌ ERROR: OPENAI_API_KEY no está configurada.\n\n"
        f"Debug información:\n"
        f"  - Archivo .env en {env_path}: {'EXISTE' if env_path.exists() else 'NO EXISTE'}\n"
        f"  - Variable de entorno OPENAI_API_KEY: {'DEFINIDA' if os.getenv('OPENAI_API_KEY') else 'NO DEFINIDA'}\n\n"
        "Soluciones:\n"
        "1. Verifica que el archivo .env esté en la misma carpeta que app.py\n"
        "2. O usa variable de entorno: $env:OPENAI_API_KEY='tu-clave'\n"
        "3. O crea el .env manualmente con solo: OPENAI_API_KEY=tu-clave\n\n"
        "Obtén tu clave en: https://platform.openai.com/api-keys"
    )

# Inicializar configuración y componentes
config: AppConfig = load_config()
processor = DocumentProcessor(config)
multi_format_processor = MultiFormatProcessor(config)
mass_processor = MassDocumentProcessor(config)
retriever_builder = RetrieverBuilder(config)
workflow = AgentWorkflow(config, provider="openai")  # Default: OpenAI

# Inicializar sistemas avanzados de mejoras
from docchat.analytics.analytics_engine import AnalyticsEngine
from docchat.integrations import IntegrationManager, UnifiedSearch, OAuthHandler
from docchat.observability.monitoring import MonitoringSystem
from docchat.security.rbac import RBACManager
from docchat.async_processor import AsyncDocumentProcessor

analytics_engine = AnalyticsEngine(config)
monitoring_system = MonitoringSystem(config)
rbac_manager = RBACManager(config)
async_processor = AsyncDocumentProcessor(config)

# Inicializar sistema de integraciones
integration_manager = IntegrationManager(config)

# Worker de sincronización en tiempo real
from docchat.integrations.sync_worker import SyncWorker
sync_worker = SyncWorker(integration_manager, sync_interval_minutes=15)
sync_worker.start()  # Iniciar worker automáticamente
print("✅ Worker de sincronización iniciado (sincroniza cada 15 minutos)")

unified_search = UnifiedSearch(integration_manager, sync_worker=sync_worker)
oauth_handler = OAuthHandler(config)

# Handler de callbacks OAuth
from docchat.integrations.oauth_callback_handler import OAuthCallbackHandler
oauth_callback_handler = OAuthCallbackHandler(integration_manager, config)

# Inicializar sistemas avanzados
memory_store = MemoryStore(config.memory_dir, config.memory_retention_days) if config.enable_memory else None
context_manager = ContextManager(memory_store, config) if memory_store else None
autonomous_agent = AutonomousAgent(agent_id="main_agent", config=config) if config.enable_autonomous_agents else None
advanced_agent = AdvancedAutonomousAgent(config) if config.enable_autonomous_agents else None
enterprise_api = EnterpriseAPIMode(config, provider="openai")  # Default: OpenAI
copilot = CopilotMode(config, provider="openai")  # Sistema Empresarial de Rendimiento Supremo
ai_agent_business_manager = AIAgentBusinessManagerMode(config, provider="openai")  # AI Agent para Ventas y Soporte 24/7
advice_god = AdviceGodMode(config, provider="openai")  # Default: OpenAI
# optimus = OptimusMode(config, provider="openai")  # ELIMINADO
marketplace = MarketplaceMode(config, provider="openai")  # Default: OpenAI
optimus_prime = OptimusPrimeMode(config, processor, retriever_builder, context_manager)
extasis = ExtasisMode(config, provider="openai")  # Default: OpenAI
# Enterprise Ads Manager - Sistema Autónomo de Gestión de Anuncios (Meta Vision 2026)
from docchat.enterprise_ads_manager_mode import EnterpriseAdsManagerMode
enterprise_ads_manager = EnterpriseAdsManagerMode(
    config=config,
    processor=processor,
    retriever_builder=retriever_builder,
    context_manager=context_manager,
    provider="openai"
)

# ADS WORKER - AI-Powered Autonomous Advertising Manager
# Sistema completo que recibe assets de usuarios y crea/publica/optimiza campañas automáticamente
from docchat.ads_worker import AdsWorkerMode
ads_worker = AdsWorkerMode(config, provider="openai")

# ADS OPTIMIZATION MODE - Motor completo de optimización de anuncios
try:
    ads_optimization_mode_instance = None
    def get_ads_optimization_mode_instance():
        global ads_optimization_mode_instance
        if ads_optimization_mode_instance is None:
            ads_optimization_mode_instance = AdsOptimizationMode(config)
        return ads_optimization_mode_instance
    ADS_OPTIMIZATION_AVAILABLE = True
    print("✅ Ads Optimization Mode disponible")
except Exception as e:
    ADS_OPTIMIZATION_AVAILABLE = False
    print(f"⚠️ Ads Optimization Mode no disponible: {e}")
    def get_ads_optimization_mode_instance():
        return None

# Customer Support Manager
try:
    from docchat.customer_support import CustomerSupportMode
    customer_support = CustomerSupportMode(config, provider="grok")
    CUSTOMER_SUPPORT_AVAILABLE = True
    print("✅ Customer Support Manager cargado correctamente")
except Exception as e:
    CUSTOMER_SUPPORT_AVAILABLE = False
    print(f"⚠️ Customer Support Manager no disponible: {e}")
    customer_support = None

# Customer Service 24/7 - Autonomous Resolution Agent
try:
    from docchat.customer_service_24_7 import CustomerService247Mode
    customer_service_24_7 = CustomerService247Mode(config, provider="grok")
    CUSTOMER_SERVICE_24_7_AVAILABLE = True
    print("✅ Customer Service 24/7 cargado correctamente")
except Exception as e:
    CUSTOMER_SERVICE_24_7_AVAILABLE = False
    print(f"⚠️ Customer Service 24/7 no disponible: {e}")
    customer_service_24_7 = None

# Enterprise Sales Manager - Sistema Autónomo de Ventas Orientado a ROI
try:
    from docchat.enterprise_sales_manager_mode import EnterpriseSalesManagerMode
    enterprise_sales_manager = EnterpriseSalesManagerMode(
        config=config,
        processor=processor,
        retriever_builder=retriever_builder,
        context_manager=context_manager,
        provider="openai"
    )
    ENTERPRISE_SALES_MANAGER_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ Enterprise Sales Manager no disponible: {e}")
    enterprise_sales_manager = None
    ENTERPRISE_SALES_MANAGER_AVAILABLE = False

# Enterprise Supreme Mode - Fusión de Enterprise API + Alien Mode + ChatPDF
try:
    from docchat.enterprise_supreme_mode import EnterpriseSupremeMode
    enterprise_supreme = EnterpriseSupremeMode(
        config=config,
        processor=processor,
        retriever_builder=retriever_builder,
        context_manager=context_manager,
        provider="openai"
    )
    ENTERPRISE_SUPREME_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ Enterprise Supreme Mode no disponible: {e}")
    enterprise_supreme = None
    ENTERPRISE_SUPREME_AVAILABLE = False

# AI Agent Builder Enterprise - Constructor de Agentes AI sin Código
try:
    from docchat.ai_agent_builder_mode import AIAgentBuilderMode
    ai_agent_builder = AIAgentBuilderMode(config=config)
    AI_AGENT_BUILDER_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ AI Agent Builder no disponible: {e}")
    ai_agent_builder = None
    AI_AGENT_BUILDER_AVAILABLE = False

# Enterprise Autonomous Multi-Agent Workflow Platform
try:
    from docchat.autonomous_multi_agent_platform import AutonomousMultiAgentWorkflowPlatform
    multi_agent_platform = AutonomousMultiAgentWorkflowPlatform(config=config)
    MULTI_AGENT_PLATFORM_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ Autonomous Multi-Agent Platform no disponible: {e}")
    multi_agent_platform = None
    MULTI_AGENT_PLATFORM_AVAILABLE = False
# Stargate PDF - clon del Enterprise API original
stargate_pdf = StargatePDFMode(config, provider="openai")
# Data Sight - clon del Enterprise API para análisis de datos e insights
data_sight = DataSightMode(config, provider="openai")
# Data Sight Integrations - Sistema de conexión con sistemas empresariales
data_sight_integrations = DataSightIntegrations(config, data_sight)
# Data Sight Automation - Sistema de automatización inteligente
data_sight_automation = DataSightAutomation(config, data_sight)
# Conectar automatización con Data Sight
data_sight.automation = data_sight_automation
# ChatDoc - Modo conversacional avanzado (reemplaza Enterprise API MDP Parallel)
chatdoc_instance = None  # Se inicializa cuando se use
# Modo Supreme (clon del Enterprise API original)
enterprise_api_supreme = EnterpriseAPISupremeMode(config, provider="openai")
# Vision Alpha Mode - Sistema completo BettaFish
try:
    vision_alpha = VisionAlphaMode(config, provider="openai")
    print("✅ Vision Alpha Mode inicializado")
except Exception as e:
    print(f"⚠️ Vision Alpha Mode no disponible: {e}")
    vision_alpha = None
# Modo Gold (clon del modo Supreme)
enterprise_api_gold = EnterpriseAPIGoldMode(config, provider="openai")
# Enterprise Autonomous Workflows se inicializa más abajo,
# cuando ya existe research_action_agent y audit_logger
enterprise_workflows = None
enterprise_agentic_ai = EnterpriseAgenticAI(config, provider="openai") if config.enable_autonomous_agents else None

# Inicializar Text-to-Action Agent y Email Autonomous Agent
text_to_action_agent = TextToAction(config)
email_autonomous_agent = EmailAutonomousAgent(config, provider="openai") if config.enable_autonomous_agents else None

# Inicializar NextGenWorkflow para Modo Guía Experto (Eric Schmidt)
from docchat.next_gen_workflow import NextGenWorkflow, NextGenWorkflowConfig
next_gen_config = NextGenWorkflowConfig(
    enable_long_context=True,
    max_context_tokens=1_000_000,  # 1M tokens
    enable_autonomous_agents=True,
    enable_text_to_action=True,
    enable_chain_of_thought=True,
    enable_adversarial_testing=True,
    auto_execute_actions=False,  # Requerir confirmación
    show_reasoning_steps=True
)
next_gen_workflow = NextGenWorkflow(config, workflow_config=next_gen_config)

# Inicializar Sistema de Almacenamiento Persistente
try:
    persistent_storage = PersistentStorage()
    print("✅ Sistema de almacenamiento persistente inicializado")
    print(f"   📁 Base de datos: {persistent_storage.db_path}")
    print(f"   📂 Documentos: {persistent_storage.documents_dir}")
    
    # Mostrar estadísticas si hay datos
    stats = persistent_storage.get_stats()
    if stats['total_documents'] > 0 or stats['total_queries'] > 0:
        print(f"   📊 Documentos históricos: {stats['total_documents']}")
        print(f"   💬 Queries históricas: {stats['total_queries']}")
        print(f"   🧠 Registros JARVIS: {stats['total_jarvis_records']}")
        print(f"   💾 Tamaño BD: {stats['database_size_mb']:.2f} MB")
        print(f"   📁 Tamaño documentos: {stats['documents_size_mb']:.2f} MB")
        
        # Cargar documentos históricos más recientes para disponibilidad inmediata
        print("   🔄 Cargando documentos históricos recientes...")
        recent_docs = persistent_storage.get_all_documents(limit=100)
        print(f"   ✅ {len(recent_docs)} documentos históricos disponibles")
except Exception as e:
    print(f"⚠️ Error inicializando almacenamiento persistente: {e}")
    persistent_storage = None

# Inicializar JARVIS Manager (Agente Autónomo 24/7)
try:
    from docchat.jarvis_manager import JarvisManager
    jarvis_manager = JarvisManager(config)
    print("✅ JARVIS Manager inicializado - Listo para absorber data de todos los modos")
    print("✅ Tab '🤖 JARVIS' debería estar visible en la interfaz")
except Exception as e:
    print(f"⚠️ Error inicializando JARVIS Manager: {e}")
    jarvis_manager = None

# Inicializar JARVIS API (Sistema completo de APIs para integración enterprise)
jarvis_api = None
jarvis_api_server = None
if jarvis_manager is not None and persistent_storage is not None:
    try:
        from docchat.jarvis_api import JarvisAPI
        from docchat.jarvis_api_server import JarvisAPIServer
        
        jarvis_api = JarvisAPI(
            jarvis_manager=jarvis_manager,
            persistent_storage=persistent_storage,
            config=config
        )
        
        jarvis_api_server = JarvisAPIServer(
            jarvis_api=jarvis_api,
            host="0.0.0.0",
            port=5001,
            enable_cors=True
        )
        
        # Iniciar servidor API en background
        jarvis_api_server.start(daemon=True)
        print("✅ JARVIS API Server iniciado en http://0.0.0.0:5001")
        print("📡 11 endpoints REST disponibles para integración enterprise")
    except Exception as e:
        print(f"⚠️ Error inicializando JARVIS API: {e}")
        jarvis_api = None
        jarvis_api_server = None

# Nuevos sistemas avanzados
iterative_learning_agent = IterativeLearningAgent(config, provider="openai") if config.enable_autonomous_agents else None
fullstack_text_to_action = FullStackTextToAction(config, provider="openai") if config.enable_autonomous_agents else None
web_recency_agent = WebRecencyAgent(config, provider="openai") if config.enable_autonomous_agents else None
deep_cot_agent = DeepChainOfThoughtAgent(config, provider="openai") if config.enable_autonomous_agents else None
automated_testing = AutomatedTestingSystem(config, provider="openai") if config.enable_autonomous_agents else None
adversarial_ai = AdversarialAISystem(config, provider="openai") if config.enable_autonomous_agents else None
collaborative_agents = CollaborativeAgentsSystem(config, provider="openai") if config.enable_autonomous_agents else None
advanced_integration = AdvancedIntegrationSystem(config, provider="openai") if config.enable_autonomous_agents else None
customer_service_agent = CustomerServiceAgent(config) if config.enable_autonomous_agents else None
# Inicializar componentes pesados de forma segura con manejo de errores
# RPA se inicializa lazy para evitar bloqueos en el inicio
rpa_engine = None
rpa_enterprise = None

def _init_rpa():
    """Inicializar RPA solo cuando se necesite."""
    global rpa_engine, rpa_enterprise
    if rpa_engine is None and config.enable_autonomous_agents:
        try:
            rpa_engine = RPAAutomationEngine(config)
            rpa_enterprise = RPAEnterpriseIntegration(config, rpa_engine)
        except Exception as e:
            print(f"Advertencia: Error inicializando RPA: {e}")
            rpa_engine = None
            rpa_enterprise = None

try:
    semantic_engine = SemanticDataEngine(config)
except Exception as e:
    print(f"Advertencia: Error inicializando Semantic Engine: {e}")
    semantic_engine = None

# Inicializar Data Ingestion Engine (para R&A Agent y otros modos)
try:
    data_ingestion_engine = DataIngestionEngine(semantic_engine) if semantic_engine else None
except Exception as e:
    print(f"Advertencia: Error inicializando Data Ingestion Engine: {e}")
    data_ingestion_engine = None

try:
    chatbot_mode = ChatbotMode(config)
except Exception as e:
    print(f"Advertencia: Error inicializando Chatbot Mode: {e}")
    chatbot_mode = None

# Inicializar Leads Mode (Agente de Ventas / SDR Outbound)
try:
    leads_mode = LeadsMode(config)
    print("✅ Leads Mode inicializado - Agente de Ventas / SDR Outbound")
except Exception as e:
    print(f"⚠️ Error inicializando Leads Mode: {e}")
    leads_mode = None

try:
    marketing_agent = MarketingAgent(config)
    print("✅ Marketing Agent inicializado - Agente de Email Marketing / Campañas")
except Exception as e:
    print(f"⚠️ Error inicializando Marketing Agent: {e}")
    marketing_agent = None

# Inicializar Business AI Omnicanal
try:
    if BUSINESS_AI_AVAILABLE and BusinessAIMode:
        business_ai_mode = BusinessAIMode(config=config)
        print("✅ Business AI Omnicanal inicializado - Agente unificado ventas + soporte 24/7")
    else:
        business_ai_mode = None
except Exception as e:
    print(f"⚠️ Error inicializando Business AI Omnicanal: {e}")
    business_ai_mode = None

# Inicializar Business AI Support
try:
    if BUSINESS_AI_SUPPORT_AVAILABLE and BusinessAISupportMode:
        business_ai_support_mode = BusinessAISupportMode(config=config)
        print("✅ Business AI Support inicializado - Agente de soporte al cliente 24/7")
    else:
        business_ai_support_mode = None
except Exception as e:
    print(f"⚠️ Error inicializando Business AI Support: {e}")
    business_ai_support_mode = None

# Inicializar Top Ads Mode
try:
    if TOP_ADS_AVAILABLE and TopAdsMode:
        top_ads_mode = TopAdsMode(config=config)
        print("✅ Top Ads Mode inicializado - AI Agent autónomo para publicidad")
    else:
        top_ads_mode = None
except Exception as e:
    print(f"⚠️ Error inicializando Top Ads Mode: {e}")
    top_ads_mode = None

# Inicializar Advertising Top Manager Mode (ADS WORKER mejorado)
try:
    from docchat.advertising_top_manager import AdvertisingTopManagerMode
    advertising_top_manager_mode = AdvertisingTopManagerMode(config=config, provider="openai")
    print("✅ Advertising Top Manager Mode inicializado - Publicación automática de anuncios en Meta y Google")
except ImportError as e:
    print(f"⚠️ Advertising Top Manager Mode no disponible: {e}")
    advertising_top_manager_mode = None
except Exception as e:
    print(f"⚠️ Error inicializando Advertising Top Manager Mode: {e}")
    advertising_top_manager_mode = None

# Inicializar Connections Manager (gestión de conexiones y sincronización de documentos)
try:
    connections_manager = ConnectionsManager(config)
    print("✅ Connections Manager inicializado - Sincronización de documentos por fuente")
except Exception as e:
    print(f"⚠️ Error inicializando Connections Manager: {e}")
    connections_manager = None

# Inicializar Real Connections Manager (OAuth real con Gmail, Drive, Outlook, etc.)
try:
    real_connections_manager = RealConnectionsManager(config)
    oauth_status = real_connections_manager.get_oauth_status()
    configured_providers = [p for p, s in oauth_status.items() if s["configured"]]
    if configured_providers:
        print(f"✅ Real Connections Manager inicializado - OAuth configurado para: {', '.join(configured_providers)}")
    else:
        print("✅ Real Connections Manager inicializado - Configura variables de entorno para habilitar OAuth")
except Exception as e:
    print(f"⚠️ Error inicializando Real Connections Manager: {e}")
    real_connections_manager = None

try:
    cloud_integration = CloudStorageIntegration(config, enterprise_api)
except Exception as e:
    print(f"Advertencia: Error inicializando Cloud Integration: {e}")
    cloud_integration = None

try:
    webhook_processor = WebhookProcessor(config, enterprise_api)
except Exception as e:
    print(f"Advertencia: Error inicializando Webhook Processor: {e}")
    webhook_processor = None
audit_logger = AuditLogger(config.audit_log_dir, config.enable_audit_logs)

# Inicializar sistemas de autenticación y workspace
user_manager = UserManager(config.memory_dir / "users")
workspace_manager = WorkspaceManager(config.memory_dir / "workspaces")

# Inicializar sesión
if context_manager:
    session_id = context_manager.start_session()

# Funciones auxiliares
def _format_sources(sources: List[dict]) -> str:
    if not sources:
        return "Sin fragmentos relevantes recuperados."
    lines = []
    for idx, src in enumerate(sources, start=1):
        lines.append(f"{idx}. **{src['source']}** — {src['preview']}")
    return "\n".join(lines)


def _format_comparative_analysis(analysis) -> str:
    if not analysis:
        return "No hay análisis comparativo disponible."
    
    lines = [
        "## 📊 Análisis Comparativo",
        "",
        f"### Temas Comunes: {', '.join(analysis.common_themes[:10])}",
        "",
        "### Estadísticas:",
        f"- Total documentos: {analysis.statistics.get('total_documents', 0)}",
        f"- Total chunks: {analysis.statistics.get('total_chunks', 0)}",
        f"- Chunks promedio por documento: {analysis.statistics.get('avg_chunks_per_doc', 0):.1f}",
        f"- Tamaño total: {analysis.statistics.get('total_size_mb', 0):.2f} MB",
    ]
    
    if analysis.contradictions:
        lines.append("\n### ⚠️ Contradicciones Detectadas:")
        for cont in analysis.contradictions:
            lines.append(f"- {cont.get('message', 'Contradicción detectada')}")
    
    return "\n".join(lines)


# Funciones principales
def run_pipeline(files, question: str, use_memory: bool = True, speed_mode: str = "balanced", provider: str = "openai"):
    """Pipeline principal de RAG - Soporta hasta 1000 documentos."""
    import time
    
    # Iniciar tracking de performance
    start_time = time.time()
    trace = monitoring_system.start_trace("rag_pipeline", {"question": question[:50], "file_count": len(files)})
    
    if not files:
        raise gr.Error("Primero sube al menos un documento.")
    if not question or not question.strip():
        raise gr.Error("Write a question.")
    
    # Validar límite de documentos
    if len(files) > config.max_documents_per_batch:
        raise gr.Error(
            f"Máximo {config.max_documents_per_batch} documentos por lote.\n"
            f"Has subido {len(files)} documentos. "
            f"Divide los documentos en lotes más pequeños o aumenta DOCCHAT_MAX_DOCS en .env"
        )
    
    # Validar tamaño total de archivos
    try:
        import shutil
        total_size = 0
        for file_obj in files:
            if hasattr(file_obj, 'size'):
                total_size += file_obj.size
            elif hasattr(file_obj, 'name'):
                try:
                    from pathlib import Path
                    file_path = Path(file_obj.name)
                    if file_path.exists():
                        total_size += file_path.stat().st_size
                except:
                    pass
        
        total_size_mb = total_size / (1024 * 1024)
        max_size_mb = config.max_total_upload_mb
        
        if total_size_mb > max_size_mb:
            raise gr.Error(
                f"Tamaño total excede el límite.\n"
                f"Tamaño total: {total_size_mb:.2f} MB\n"
                f"Límite máximo: {max_size_mb} MB\n"
                f"Reduce el número de archivos o su tamaño."
            )
        
        # Verificar espacio disponible en disco (usar /tmp en Cloud Run)
        import os
        disk_path = "/tmp" if os.environ.get("PORT") else "."
        try:
            disk_usage = shutil.disk_usage(disk_path)
            free_space_gb = disk_usage.free / (1024 * 1024 * 1024)
            required_space_gb = (total_size_mb * 2) / 1024  # Necesitamos ~2x el tamaño para procesamiento
            
            if free_space_gb < required_space_gb:
                raise gr.Error(
                    f"Espacio insuficiente en disco.\n"
                    f"Espacio libre: {free_space_gb:.2f} GB\n"
                    f"Espacio requerido: {required_space_gb:.2f} GB\n"
                    f"Libera espacio o reduce el número de archivos."
                )
        except Exception as e:
            # En Cloud Run, continuar sin validar espacio (tiene límites pero no podemos verificarlos fácilmente)
            if os.environ.get("PORT"):
                print(f"⚠️ No se pudo verificar espacio en /tmp: {e}. Continuando...")
            else:
                raise gr.Error(f"Error al verificar espacio en disco: {str(e)}")
        
    except gr.Error:
        raise
    except Exception as e:
        # Si falla la validación, continuar pero advertir
        print(f"Advertencia: No se pudo validar espacio en disco: {e}")
    
    # Mensaje informativo para grandes volúmenes
    if len(files) > 50:
        print(f"Procesando {len(files)} documentos en Consulta RAG... Esto puede tardar varios minutos.")
    
    # Audit log
    audit_logger.log(
        event_type="query",
        action="process_documents",
        resource="documents",
        user_id="user",
        metadata={"file_count": len(files), "question": question[:100]}
    )
    
    # Obtener contexto de memoria si está habilitado
    context = {}
    if use_memory and context_manager:
        context = context_manager.get_context_for_query(question)
    
    # Procesar documentos con manejo de errores mejorado
    try:
        docs = processor.process(files)
    except OSError as e:
        if "No space left on device" in str(e) or "errno 28" in str(e):
            error_msg = (
                f"❌ ERROR: Espacio insuficiente en disco.\n\n"
                f"El sistema no tiene suficiente espacio para procesar {len(files)} documentos.\n\n"
                f"💡 SOLUCIONES:\n"
                f"1. Reduce el número de archivos (prueba con 1-5 primero)\n"
                f"2. Procesa archivos más pequeños\n"
                f"3. Procesa en lotes más pequeños"
            )
            print(f"❌ Error de espacio: {e}")
            raise gr.Error(error_msg)
        else:
            print(f"❌ Error OSError al procesar: {e}")
            import traceback
            traceback.print_exc()
            raise gr.Error(f"Error al procesar documentos: {str(e)}")
    except Exception as e:
        print(f"❌ Error inesperado al procesar documentos: {e}")
        import traceback
        traceback.print_exc()
        raise gr.Error(f"Error inesperado al procesar documentos: {str(e)}")
    
    retriever = retriever_builder.build_hybrid_retriever(docs)
    
    # Aplicar modo de velocidad temporalmente
    original_speed_mode = config.speed_mode
    config.speed_mode = speed_mode
    if speed_mode == "fast":
        print("⚡ Modo RÁPIDO activado: respuestas más concisas, procesamiento acelerado")
    elif speed_mode == "quality":
        print("🎯 Modo MÁXIMA CALIDAD activado: análisis profundo, puede tardar más")
    else:
        print("⚖️ Modo BALANCEADO activado: equilibrio entre velocidad y calidad")
    
    # Ejecutar workflow (pasar todos los documentos para preguntas generales)
    try:
        # Crear workflow con el provider seleccionado
        temp_workflow = AgentWorkflow(config, provider=provider)
        result = temp_workflow.run(question.strip(), retriever, all_documents=docs)
        print(f"\n📊 Resultado del workflow recibido:")
        print(f"   - Respuesta: {len(result.get('answer', ''))} caracteres")
        print(f"   - Fuentes: {len(result.get('sources', []))}")
        print(f"   - Relevancia: {result.get('relevance', 'N/A')}\n")
    except Exception as e:
        print(f"\n❌ ERROR en workflow.run(): {str(e)}")
        import traceback
        traceback.print_exc()
        raise gr.Error(f"Error al ejecutar workflow: {str(e)}")
    
    # Restaurar modo original
    config.speed_mode = original_speed_mode
    
    # Guardar en memoria
    if use_memory and context_manager:
        context_manager.add_query(
            query=question,
            answer=result["answer"],
            sources=[s["source"] for s in result["sources"]],
            metadata={"relevance": result["relevance"]}
        )
    
    # Finalizar tracking
    response_time = time.time() - start_time
    monitoring_system.end_trace(trace)
    
    # Registrar métricas
    monitoring_system.record_metric("pipeline_response_time", response_time, {"speed_mode": speed_mode})
    monitoring_system.record_metric("pipeline_documents_processed", len(files))
    monitoring_system.record_metric("pipeline_sources_retrieved", len(result.get("sources", [])))
    
    # Trackear en analytics
    documents_used = [s.get("source", "unknown") for s in result.get("sources", [])]
    analytics_engine.track_query(
        query=question,
        user_id="user",
        response_time=response_time,
        documents_used=documents_used,
        success=True
    )
    
    # Análisis de sentimiento de la pregunta
    sentiment = analytics_engine.analyze_sentiment(question)
    
    return (
        result["answer"],
        _format_sources(result["sources"]),
        result["verification_report"],
        f"Clasificación de relevancia: {result['relevance']}",
    )


def run_massive_processing(files, enable_comparison: bool = True):
    """Procesamiento masivo de documentos."""
    if not files:
        raise gr.Error("Primero sube documentos para procesar.")
    
    if len(files) > config.max_documents_per_batch:
        raise gr.Error(
            f"Máximo {config.max_documents_per_batch} documentos por lote.\n"
            f"Has subido {len(files)} documentos. "
            f"Divide los documentos en lotes más pequeños o aumenta DOCCHAT_MAX_DOCS en .env"
        )
    
    audit_logger.log(
        event_type="mass_processing",
        action="process_massive_batch",
        resource="documents",
        user_id="user",
        metadata={"file_count": len(files), "comparison_enabled": enable_comparison}
    )
    
    try:
        chunks, metadata, analysis = mass_processor.process_massive_batch(
            files,
            enable_comparison=enable_comparison
        )
        
        # Formatear resultados
        metadata_text = "## 📄 Documentos Procesados\n\n"
        for meta in metadata:
            status = "✅" if not meta.errors else "❌"
            metadata_text += f"{status} **{meta.file_name}**\n"
            metadata_text += f"  - Chunks: {meta.chunk_count}\n"
            metadata_text += f"  - Tamaño: {meta.size_mb:.2f} MB\n"
            metadata_text += f"  - Tiempo: {meta.processing_time:.2f}s\n"
            if meta.errors:
                metadata_text += f"  - Errores: {', '.join(meta.errors)}\n"
            metadata_text += "\n"
        
        analysis_text = _format_comparative_analysis(analysis) if analysis else ""
        
        summary = f"""
## ✅ Procesamiento Completado

- **Total documentos**: {len(metadata)}
- **Total chunks generados**: {len(chunks)}
- **Documentos exitosos**: {sum(1 for m in metadata if not m.errors)}
- **Documentos con errores**: {sum(1 for m in metadata if m.errors)}

{analysis_text}
"""
        
        return summary, metadata_text
        
    except Exception as e:
        error_msg = f"Error en procesamiento masivo: {str(e)}"
        audit_logger.log(
            event_type="error",
            action="mass_processing",
            resource="documents",
            result="error",
            metadata={"error": str(e)}
        )
        raise gr.Error(error_msg)


def run_complete_workflow(files, task_description: str, output_format: str = "all"):
    """Ejecutar workflow completo: analizar + generar informes automáticamente."""
    if not task_description or not task_description.strip():
        raise gr.Error("Describe the complete task you want to execute.")
    
    if not advanced_agent:
        raise gr.Error("Agente avanzado no está habilitado.")
    
    if not files:
        raise gr.Error("Sube documentos para analizar.")
    
    audit_logger.log(
        event_type="complete_workflow",
        action="execute_complete_workflow",
        resource="documents",
        user_id="user",
        metadata={"task": task_description[:100], "file_count": len(files), "format": output_format}
    )
    
    try:
        result = advanced_agent.execute_complete_workflow(
            task_description=task_description,
            files=files,
            output_format=output_format
        )
        
        # Formatear resultado
        output = f"""
## 🚀 Workflow Completo Ejecutado

**Tarea**: {task_description}

**Estado**: {'✅ Completado' if result['status'] == 'completed' else '❌ Error'}

### Archivos Generados:
"""
        for output_file in result.get('outputs', []):
            output += f"\n- **{output_file['type'].upper()}**: {output_file.get('path', 'N/A')}"
        
        if result.get('errors'):
            output += "\n\n### Errores:\n"
            for error in result['errors']:
                output += f"- {error}\n"
        
        if result.get('summary'):
            output += f"\n### Resumen:\n{result['summary']}"
        
        return output
        
    except Exception as e:
        error_msg = f"Error ejecutando workflow completo: {str(e)}"
        audit_logger.log(
            event_type="error",
            action="complete_workflow",
            resource="advanced_agent",
            result="error",
            metadata={"error": str(e)}
        )
        raise gr.Error(error_msg)


def run_idp_processing(files):
    """Procesa documentos con Intelligent Document Processing (IDP)."""
    if not files:
        raise gr.Error("Primero sube documentos para procesar con IDP.")
    
    if not enterprise_agentic_ai:
        raise gr.Error("Enterprise Agentic AI no está habilitado. Configura DOCCHAT_ENABLE_AGENTS=true")
    
    audit_logger.log(
        event_type="idp_processing",
        action="process_documents",
        resource="enterprise_agentic_ai",
        user_id="user",
        metadata={"file_count": len(files)}
    )
    
    try:
        idp_results = enterprise_agentic_ai.process_documents_with_idp(
            files=files,
            extract_entities=True,
            extract_metrics=True
        )
        
        output = f"## ✅ Procesamiento IDP Completado\n\n"
        output += f"**Documentos procesados:** {len(idp_results)}\n\n"
        
        for file_name, result in idp_results.items():
            from pathlib import Path
            clean_name = Path(file_name).name
            output += f"### 📄 {clean_name}\n\n"
            output += f"- **Tipo de documento:** {result.document_type}\n"
            output += f"- **Entidades extraídas:** {len(result.entities)}\n"
            output += f"- **Métricas clave:** {len(result.key_metrics)}\n"
            if result.entities:
                output += f"- **Entidades principales:** {', '.join(result.entities[:5])}\n"
            if result.key_metrics:
                output += f"- **Métricas:** {', '.join(list(result.key_metrics.keys())[:3])}\n"
            output += "\n"
        
        output += "\n**💡 Ahora puedes ejecutar tareas autónomas usando estos datos procesados.**\n"
        
        return output
        
    except Exception as e:
        error_msg = f"Error en procesamiento IDP: {str(e)}"
        audit_logger.log(
            event_type="idp_processing",
            action="error",
            resource="enterprise_agentic_ai",
            user_id="user",
            metadata={"error": str(e)}
        )
        raise gr.Error(error_msg)


def run_enterprise_agentic_task(task_description: str, task_type: str, context_data: str = ""):
    """Ejecuta tarea autónoma usando Enterprise Agentic AI con datos IDP."""
    if not task_description or not task_description.strip():
        raise gr.Error("Describe the task you want the Agentic AI to execute.")
    
    if not enterprise_agentic_ai:
        raise gr.Error("Enterprise Agentic AI no está habilitado. Configura DOCCHAT_ENABLE_AGENTS=true")
    
    # Verificar si hay documentos procesados con IDP (opcional)
    has_idp_data = bool(enterprise_agentic_ai.idp_results)
    
    if not has_idp_data:
        # Permitir ejecutar tareas sin IDP (para tareas simples como enviar emails)
        print("⚠️ No hay documentos procesados con IDP. Ejecutando tarea sin datos IDP.")
    
    audit_logger.log(
        event_type="enterprise_agentic_task",
        action="execute_task",
        resource="enterprise_agentic_ai",
        user_id="user",
        metadata={"task": task_description[:100], "task_type": task_type, "has_idp_data": has_idp_data}
    )
    
    try:
        context = {}
        if context_data:
            try:
                context = json.loads(context_data)
            except:
                context = {"context": context_data}
        
        # Usar datos IDP solo si están disponibles
        result = enterprise_agentic_ai.execute_autonomous_task_v2(
            task_description=task_description,
            task_type=task_type,
            context=context,
            use_processed_data=has_idp_data  # Solo usar IDP si hay datos
        )
        
        output = result.get("summary", "No se generó resumen")
        output += f"\n\n**Herramientas utilizadas:** {', '.join(result.get('tools_used', []))}\n"
        output += f"**Datos IDP utilizados:** {result.get('idp_data_used', 0)} documentos\n"
        
        if result.get("success"):
            output += "\n✅ **Tarea completada exitosamente**\n"
        else:
            output += "\n⚠️ **Tarea completada con algunos errores**\n"
        
        return output
        
    except Exception as e:
        error_msg = f"Error ejecutando tarea autónoma: {str(e)}"
        audit_logger.log(
            event_type="enterprise_agentic_task",
            action="error",
            resource="enterprise_agentic_ai",
            user_id="user",
            metadata={"error": str(e)}
        )
        raise gr.Error(error_msg)


def run_idp_processing(files):
    """Procesa documentos con Intelligent Document Processing (IDP)."""
    if not files:
        raise gr.Error("Primero sube documentos para procesar con IDP.")
    
    if not enterprise_agentic_ai:
        raise gr.Error("Enterprise Agentic AI no está habilitado. Configura DOCCHAT_ENABLE_AGENTS=true")
    
    audit_logger.log(
        event_type="idp_processing",
        action="process_documents",
        resource="enterprise_agentic_ai",
        user_id="user",
        metadata={"file_count": len(files)}
    )
    
    try:
        idp_results = enterprise_agentic_ai.process_documents_with_idp(
            files=files,
            extract_entities=True,
            extract_metrics=True
        )
        
        output = f"## ✅ Procesamiento IDP Completado\n\n"
        output += f"**Documentos procesados:** {len(idp_results)}\n\n"
        
        for file_name, result in idp_results.items():
            from pathlib import Path
            clean_name = Path(file_name).name
            output += f"### 📄 {clean_name}\n\n"
            output += f"- **Tipo de documento:** {result.document_type}\n"
            output += f"- **Entidades extraídas:** {len(result.entities)}\n"
            output += f"- **Métricas clave:** {len(result.key_metrics)}\n"
            if result.entities:
                output += f"- **Entidades principales:** {', '.join(result.entities[:5])}\n"
            if result.key_metrics:
                output += f"- **Métricas:** {', '.join(list(result.key_metrics.keys())[:3])}\n"
            output += "\n"
        
        output += "\n**💡 Ahora puedes ejecutar tareas autónomas usando estos datos procesados.**\n"
        
        return output
        
    except Exception as e:
        error_msg = f"Error en procesamiento IDP: {str(e)}"
        audit_logger.log(
            event_type="idp_processing",
            action="error",
            resource="enterprise_agentic_ai",
            user_id="user",
            metadata={"error": str(e)}
        )
        raise gr.Error(error_msg)


def run_enterprise_agentic_task(task_description: str, task_type: str, context_data: str = ""):
    """Ejecuta tarea autónoma usando Enterprise Agentic AI con datos IDP."""
    if not task_description or not task_description.strip():
        raise gr.Error("Describe the task you want the Agentic AI to execute.")
    
    if not enterprise_agentic_ai:
        raise gr.Error("Enterprise Agentic AI no está habilitado. Configura DOCCHAT_ENABLE_AGENTS=true")
    
    # Verificar si hay documentos procesados con IDP (opcional)
    has_idp_data = bool(enterprise_agentic_ai.idp_results)
    
    if not has_idp_data:
        # Permitir ejecutar tareas sin IDP (para tareas simples como enviar emails)
        print("⚠️ No hay documentos procesados con IDP. Ejecutando tarea sin datos IDP.")
    
    audit_logger.log(
        event_type="enterprise_agentic_task",
        action="execute_task",
        resource="enterprise_agentic_ai",
        user_id="user",
        metadata={"task": task_description[:100], "task_type": task_type, "has_idp_data": has_idp_data}
    )
    
    try:
        context = {}
        if context_data:
            try:
                context = json.loads(context_data)
            except:
                context = {"context": context_data}
        
        # Usar datos IDP solo si están disponibles
        result = enterprise_agentic_ai.execute_autonomous_task(
            task_description=task_description,
            task_type=task_type,
            context=context,
            use_processed_data=has_idp_data  # Solo usar IDP si hay datos
        )
        
        output = result.get("summary", "No se generó resumen")
        output += f"\n\n**Herramientas utilizadas:** {', '.join(result.get('tools_used', []))}\n"
        output += f"**Datos IDP utilizados:** {result.get('idp_data_used', 0)} documentos\n"
        
        if result.get("success"):
            output += "\n✅ **Tarea completada exitosamente**\n"
        else:
            output += "\n⚠️ **Tarea completada con algunos errores**\n"
        
        return output
        
    except Exception as e:
        error_msg = f"Error ejecutando tarea autónoma: {str(e)}"
        audit_logger.log(
            event_type="enterprise_agentic_task",
            action="error",
            resource="enterprise_agentic_ai",
            user_id="user",
            metadata={"error": str(e)}
        )
        raise gr.Error(error_msg)


# ==================== Funciones para Modo Chatbot ====================

def register_chatbot(chatbot_name: str, company_name: str):
    """Registra un nuevo chatbot."""
    if not chatbot_name or not chatbot_name.strip():
        raise gr.Error("Enter the chatbot name.")
    
    if not company_name or not company_name.strip():
        raise gr.Error("Enter the company name.")
    
    try:
        if chatbot_mode is None:
            raise gr.Error("Chatbot mode no está disponible")
        connection = chatbot_mode.register_chatbot(
            chatbot_name=chatbot_name.strip(),
            company_name=company_name.strip()
        )
        
        output = f"## ✅ Chatbot Registrado Exitosamente\n\n"
        output += f"**Nombre del Chatbot:** {connection.chatbot_name}\n"
        output += f"**Empresa:** {connection.company_name}\n"
        output += f"**Chatbot ID:** `{connection.chatbot_id}`\n"
        output += f"**API Key:** `{connection.api_key}`\n\n"
        output += "**⚠️ IMPORTANTE:** Guarda estos valores. Los necesitarás para:\n"
        output += "- Conectar tu chatbot por API\n"
        output += "- Subir data para este chatbot\n"
        output += "- Hacer consultas desde tu chatbot externo\n"
        
        audit_logger.log(
            event_type="chatbot_registration",
            action="register",
            resource="chatbot_mode",
            user_id="user",
            metadata={
                "chatbot_name": connection.chatbot_name,
                "company_name": connection.company_name,
                "chatbot_id": connection.chatbot_id
            }
        )
        
        return output
        
    except Exception as e:
        error_msg = f"Error registrando chatbot: {str(e)}"
        audit_logger.log(
            event_type="chatbot_registration",
            action="error",
            resource="chatbot_mode",
            user_id="user",
            metadata={"error": str(e)}
        )
        raise gr.Error(error_msg)


def upload_chatbot_data(chatbot_id: str, files):
    """Sube y procesa data para un chatbot."""
    if not chatbot_id or not chatbot_id.strip():
        raise gr.Error("Enter the Chatbot ID.")
    
    if not files:
        raise gr.Error("Sube al menos un documento.")
    
    chatbot_id = chatbot_id.strip()
    
    try:
        result = chatbot_mode.upload_chatbot_data(
            chatbot_id=chatbot_id,
            files=files
        )
        
        # JARVIS: Absorber documentos del chatbot
        try:
            if jarvis_manager is not None:
                jarvis = jarvis_manager.get_or_create_jarvis("user")
            for file_obj in files:
                jarvis.absorb_data(
                    data=file_obj,
                    source="chatbot_mode",
                    data_type="document",
                    metadata={"chatbot_id": chatbot_id}
                )
        except Exception as jarvis_error:
            print(f"⚠️ [JARVIS] Error absorbiendo documentos del chatbot: {jarvis_error}")
        
        output = f"## ✅ Data Procesada Exitosamente\n\n"
        output += f"**Chatbot ID:** {chatbot_id}\n"
        output += f"**Documentos procesados:** {result['documents_processed']}\n"
        output += f"**Chunks creados:** {result['chunks_created']}\n\n"
        output += "✅ **Base vectorizada creada y lista para consultas**\n\n"
        output += "Ahora tu chatbot puede consultar esta data por API.\n"
        
        audit_logger.log(
            event_type="chatbot_data_upload",
            action="upload",
            resource="chatbot_mode",
            user_id="user",
            metadata={
                "chatbot_id": chatbot_id,
                "documents_count": result['documents_processed'],
                "chunks_count": result['chunks_created']
            }
        )
        
        return output
        
    except Exception as e:
        error_msg = f"Error procesando data: {str(e)}"
        audit_logger.log(
            event_type="chatbot_data_upload",
            action="error",
            resource="chatbot_mode",
            user_id="user",
            metadata={"error": str(e)}
        )
        raise gr.Error(error_msg)


def test_chatbot_query(chatbot_id: str, question: str):
    """Prueba una consulta al chatbot."""
    if not chatbot_id or not chatbot_id.strip():
        raise gr.Error("Enter the Chatbot ID.")
    
    if not question or not question.strip():
        raise gr.Error("Enter a question.")
    
    chatbot_id = chatbot_id.strip()
    question = question.strip()
    
    try:
        response = chatbot_mode.query_chatbot(
            chatbot_id=chatbot_id,
            user_question=question,
            use_reranking=True,
            max_chunks=5
        )
        
        output = f"## 💬 Respuesta del Chatbot\n\n"
        output += f"**Pregunta:** {question}\n\n"
        output += f"**Respuesta:**\n{response.answer}\n\n"
        
        if response.sources:
            output += f"**📚 Fuentes utilizadas ({len(response.sources)}):**\n"
            for source in response.sources[:5]:
                from pathlib import Path
                clean_source = Path(source).name
                output += f"- {clean_source}\n"
            output += "\n"
        
        output += f"**Confianza:** {response.confidence:.0%}\n"
        output += f"**Chunks utilizados:** {response.chunks_used}\n"
        if response.reranked:
            output += f"**Reranking:** ✅ Activado\n"
        
        # JARVIS: Absorber data del chatbot
        try:
            if jarvis_manager is not None:
                jarvis = jarvis_manager.get_or_create_jarvis("user")
            jarvis.absorb_data(
                data=question,
                source="chatbot_mode",
                data_type="query",
                metadata={"chatbot_id": chatbot_id}
            )
            jarvis.absorb_data(
                data=response.answer,
                source="chatbot_mode",
                data_type="response",
                metadata={"chatbot_id": chatbot_id, "confidence": response.confidence}
            )
        except Exception as jarvis_error:
            print(f"⚠️ [JARVIS] Error absorbiendo data del chatbot: {jarvis_error}")
        
        audit_logger.log(
            event_type="chatbot_query",
            action="test_query",
            resource="chatbot_mode",
            user_id="user",
            metadata={
                "chatbot_id": chatbot_id,
                "question_length": len(question),
                "chunks_used": response.chunks_used,
                "confidence": response.confidence
            }
        )
        
        return output
        
    except Exception as e:
        error_msg = f"Error consultando chatbot: {str(e)}"
        audit_logger.log(
            event_type="chatbot_query",
            action="error",
            resource="chatbot_mode",
            user_id="user",
            metadata={"error": str(e)}
        )
        raise gr.Error(error_msg)


def list_chatbots():
    """Lista todos los chatbots registrados."""
    try:
        chatbots = chatbot_mode.list_chatbots()
        
        if not chatbots:
            return "## 📋 No hay chatbots registrados\n\nRegistra un chatbot en el tab 'Registrar Chatbot'."
        
        output = f"## 📋 Chatbots Registrados: {len(chatbots)}\n\n"
        
        for chatbot in chatbots:
            output += f"### 🤖 {chatbot['chatbot_name']}\n\n"
            output += f"- **Empresa:** {chatbot['company_name']}\n"
            output += f"- **Chatbot ID:** `{chatbot['chatbot_id']}`\n"
            output += f"- **Estado:** {chatbot['status']}\n"
            output += f"- **Documentos:** {chatbot['documents_count']}\n"
            output += f"- **Chunks:** {chatbot['chunks_count']}\n\n"
        
        return output
        
    except Exception as e:
        return f"Error listando chatbots: {str(e)}"


# ==================== Funciones para Analytics ====================

def refresh_analytics_dashboard(days: int):
    """Actualiza dashboard de analytics."""
    try:
        # Obtener métricas del dashboard
        metrics = analytics_engine.get_dashboard_metrics(days=days)
        
        # Formatear dashboard
        dashboard_output = f"## 📊 Dashboard Ejecutivo - Últimos {days} días\n\n"
        dashboard_output += f"### 📈 Métricas Principales\n\n"
        dashboard_output += f"- **Total de Consultas:** {metrics['total_queries']}\n"
        dashboard_output += f"- **Consultas Exitosas:** {metrics['successful_queries']}\n"
        dashboard_output += f"- **Tasa de Éxito:** {metrics['success_rate']:.1%}\n"
        dashboard_output += f"- **Tiempo de Respuesta Promedio:** {metrics['avg_response_time']:.2f}s\n\n"
        
        # Sentimiento promedio
        sentiment = metrics.get('avg_sentiment', {})
        dashboard_output += f"### 😊 Análisis de Sentimiento\n\n"
        dashboard_output += f"- **Positivo:** {sentiment.get('positive', 0):.1%}\n"
        dashboard_output += f"- **Neutro:** {sentiment.get('neutral', 0):.1%}\n"
        dashboard_output += f"- **Negativo:** {sentiment.get('negative', 0):.1%}\n\n"
        
        # Documentos más consultados
        if metrics.get('top_documents'):
            dashboard_output += f"### 📚 Documentos Más Consultados\n\n"
            for doc in metrics['top_documents'][:5]:
                from pathlib import Path
                doc_name = Path(doc['name']).name
                dashboard_output += f"- **{doc_name}**: {doc['count']} consultas\n"
            dashboard_output += "\n"
        
        # Gaps de conocimiento
        if metrics.get('knowledge_gaps'):
            dashboard_output += f"### ⚠️ Gaps de Conocimiento Detectados\n\n"
            for gap in metrics['knowledge_gaps'][:5]:
                dashboard_output += f"- {gap[:100]}...\n"
            dashboard_output += "\n"
        
        # Preguntas frecuentes predichas
        frequent_questions = analytics_engine.predict_frequent_questions(top_n=10)
        frequent_output = f"## ❓ Preguntas Frecuentes Predichas\n\n"
        for i, fq in enumerate(frequent_questions, 1):
            frequent_output += f"{i}. **{fq['example']}** ({fq['count']} veces)\n\n"
        
        # ROI metrics
        roi_metrics = analytics_engine.get_roi_metrics()
        roi_output = f"## 💰 Métricas de ROI\n\n"
        roi_output += f"- **Consultas Totales:** {roi_metrics['total_queries']}\n"
        roi_output += f"- **Consultas Exitosas:** {roi_metrics['successful_queries']}\n"
        roi_output += f"- **Tiempo Ahorrado:** {roi_metrics['time_saved_hours']:.1f} horas\n"
        roi_output += f"- **Costo Estimado Ahorrado:** ${roi_metrics['estimated_cost_saved']:.2f}\n"
        roi_output += f"- **Ganancia de Eficiencia:** {roi_metrics['efficiency_gain']}\n"
        
        return dashboard_output, frequent_output, roi_output
        
    except Exception as e:
        error_msg = f"Error obteniendo analytics: {str(e)}"
        return f"## ❌ Error\n\n{error_msg}", "", ""


# ==================== Funciones para Integraciones ====================

def connect_integration_with_token(integration_type: str, access_token: str):
    """Conecta una integración usando token directo (método fácil)."""
    if not integration_type:
        raise gr.Error("Select an app to connect")
    
    if not access_token or not access_token.strip():
        raise gr.Error("Pega el Access Token que obtuviste de OAuth Playground")
    
    try:
        from docchat.integrations.integration_manager import IntegrationType
        import time
        
        # Mapear string a IntegrationType
        type_map = {
            "gmail": IntegrationType.GMAIL,
            "google_drive": IntegrationType.GOOGLE_DRIVE,
            "microsoft_teams": IntegrationType.MICROSOFT_TEAMS,
            "outlook": IntegrationType.OUTLOOK,
            "onedrive": IntegrationType.ONEDRIVE,
            "slack": IntegrationType.SLACK,
            "salesforce": IntegrationType.SALESFORCE,
            "jira": IntegrationType.JIRA,
            "github": IntegrationType.GITHUB,
            "notion": IntegrationType.NOTION,
            "confluence": IntegrationType.CONFLUENCE,
            "zendesk": IntegrationType.ZENDESK,
            "servicenow": IntegrationType.SERVICENOW
        }
        
        integration_type_enum = type_map.get(integration_type)
        if not integration_type_enum:
            raise gr.Error(f"Tipo de integración no válido: {integration_type}")
        
        # Conectar con token directo
        token = access_token.strip()
        
        # Para Google, el token suele expirar en 1 hora, pero podemos refrescarlo después
        # Por ahora, conectamos con el token tal cual
        connection = integration_manager.connect_integration(
            integration_type=integration_type_enum,
            user_id="user",  # En producción, usar ID real
            access_token=token,
            refresh_token=None,  # OAuth Playground no da refresh token fácilmente
            expires_at=time.time() + 3600,  # Asumir 1 hora de validez
            metadata={"method": "direct_token", "source": "oauth_playground"}
        )
        
        app_names = {
            "gmail": ("Gmail", "📧"),
            "google_drive": ("Google Drive", "📁"),
            "microsoft_teams": ("Microsoft Teams", "💼"),
            "outlook": ("Outlook", "📧"),
            "onedrive": ("OneDrive", "📁"),
            "slack": ("Slack", "💬"),
            "salesforce": ("Salesforce", "📊"),
            "jira": ("Jira", "✅"),
            "github": ("GitHub", "💻"),
            "notion": ("Notion", "📝"),
            "confluence": ("Confluence", "📚"),
            "zendesk": ("Zendesk", "🎫"),
            "servicenow": ("ServiceNow", "🔧"),
            # Nuevas integraciones
            "hubspot": ("HubSpot", "🎯"),
            "asana": ("Asana", "📋"),
            "trello": ("Trello", "📌"),
            "quickbooks": ("QuickBooks", "💰"),
            "workday": ("Workday", "👥"),
            "powerbi": ("Power BI", "📊"),
            "sharepoint": ("SharePoint", "📄"),
            "monday": ("Monday.com", "📅"),
            "pipedrive": ("Pipedrive", "📈"),
            "zoho_crm": ("Zoho CRM", "🔷"),
            "bamboohr": ("BambooHR", "🎋"),
            "freshbooks": ("FreshBooks", "💵"),
            "wave": ("Wave", "🌊"),
            "zoom": ("Zoom", "📹")
        }
        
        app_name, emoji = app_names.get(integration_type, (integration_type.replace('_', ' ').title(), "🔗"))
        
        output = f"""
## ✅ {app_name} Conectado Exitosamente

**🎉 ¡Felicitaciones!** Tu {app_name} está ahora conectado a DocChat Enterprise.

**📊 Información de Conexión:**
- **ID de Conexión:** `{connection.integration_id}`
- **Estado:** {connection.status}
- **Conectado:** {connection.connected_at}

**💡 Próximos Pasos:**
1. Ve al tab "✅ Apps Conectadas" para ver todas tus conexiones
2. Ve al tab "🔍 Buscar en Todas las Apps" para probar
3. Ahora DocChat puede buscar en tu {app_name} automáticamente

**⚠️ Nota:** El token expira en aproximadamente 1 hora. Si necesitas reconectar después, solo repite el proceso (es rápido).
"""
        return output
        
    except Exception as e:
        error_msg = f"Error conectando {integration_type}: {str(e)}"
        raise gr.Error(error_msg)


def connect_integration(integration_type: str):
    """Conecta una integración con OAuth."""
    if not integration_type:
        raise gr.Error("Select an app to connect")
    
    try:
        from docchat.integrations.integration_manager import IntegrationType
        
        # Mapear string a IntegrationType
        type_map = {
            "gmail": IntegrationType.GMAIL,
            "google_drive": IntegrationType.GOOGLE_DRIVE,
            "microsoft_teams": IntegrationType.MICROSOFT_TEAMS,
            "outlook": IntegrationType.OUTLOOK,
            "onedrive": IntegrationType.ONEDRIVE,
            "slack": IntegrationType.SLACK,
            "salesforce": IntegrationType.SALESFORCE,
            "jira": IntegrationType.JIRA,
            "github": IntegrationType.GITHUB,
            "notion": IntegrationType.NOTION,
            "confluence": IntegrationType.CONFLUENCE,
            "zendesk": IntegrationType.ZENDESK,
            "servicenow": IntegrationType.SERVICENOW
        }
        
        integration_type_enum = type_map.get(integration_type)
        if not integration_type_enum:
            raise gr.Error(f"Tipo de integración no válido: {integration_type}")
        
        # Generar URL de autorización OAuth
        try:
            import uuid
            state = str(uuid.uuid4())
            auth_url = oauth_handler.get_authorization_url(integration_type_enum, state)
            
            # Mapear nombres amigables y emojis
            app_names = {
                "gmail": ("Gmail", "📧"),
                "google_drive": ("Google Drive", "📁"),
                "microsoft_teams": ("Microsoft Teams", "💼"),
                "outlook": ("Outlook", "📧"),
                "onedrive": ("OneDrive", "📁"),
                "slack": ("Slack", "💬"),
                "salesforce": ("Salesforce", "📊"),
                "jira": ("Jira", "✅"),
                "github": ("GitHub", "💻"),
                "notion": ("Notion", "📝"),
                "confluence": ("Confluence", "📚"),
                "zendesk": ("Zendesk", "🎫"),
                "servicenow": ("ServiceNow", "🔧")
            }
            
            app_name, emoji = app_names.get(integration_type, (integration_type.replace('_', ' ').title(), "🔗"))
            
            output = f"""
## {emoji} Conectar {app_name}

### ✨ Super Fácil - Solo 1 Click:

**Click en el botón azul de abajo** → Se abre ventana → Autorizas → ¡Listo!

---

### 🔗 Click Aquí para Conectar:

<div style="text-align: center; margin: 20px 0;">
    <a href="{auth_url}" target="_blank" style="text-decoration: none;">
        <button style="background-color: #4285F4; color: white; padding: 25px 50px; font-size: 20px; font-weight: bold; border: none; border-radius: 10px; cursor: pointer; box-shadow: 0 4px 8px rgba(0,0,0,0.2); transition: all 0.3s;">
            🔗 Conectar {app_name} Ahora
        </button>
    </a>
</div>

---

### 📝 ¿Qué va a pasar?

1. **Se abre una ventana nueva** con la página de {app_name}
2. **Inicias sesión** con tu cuenta (si no estás logueado)
3. **Click en "Permitir"** o "Authorize"
4. **¡Listo!** La conexión se completa automáticamente

---

### ⚠️ Si ves un error de "verificación":

**Para Gmail/Google Drive:** Necesitas agregar tu email como "tester" en Google Cloud Console.

**Solución rápida:**
1. Ve a: https://console.cloud.google.com/apis/credentials
2. Click en tu OAuth Client ID
3. Busca "Test users" → "+ ADD USERS"
4. Agrega tu email
5. Vuelve aquí y conecta de nuevo

---

**🔒 Seguro:** DocChat solo lee información. Nunca modifica tus datos.
"""
            return output
        except ValueError as e:
            # Error de configuración (falta client_id, etc.)
            error_msg = str(e)
            
            # Mensaje más amigable según el tipo de integración
            if "google" in error_msg.lower() or integration_type in ["gmail", "google_drive"]:
                setup_guide = """
## ⚙️ Configuración Requerida para Google

Para conectar Gmail o Google Drive, necesitas configurar credenciales OAuth de Google:

**Pasos:**

1. **Ve a Google Cloud Console:**
   https://console.cloud.google.com/apis/credentials

2. **Crea un proyecto** (o selecciona uno existente)

3. **Habilita las APIs necesarias:**
   - Gmail API (para Gmail)
   - Google Drive API (para Drive)

4. **Crea credenciales OAuth 2.0:**
   - Tipo: "Aplicación web"
   - URI de redirección autorizada: `http://localhost:7860/oauth/callback?provider=google`

5. **Copia el Client ID y Client Secret**

6. **Agrega a tu archivo `.env`:**
   ```
   GOOGLE_CLIENT_ID=tu-client-id-aqui
   GOOGLE_CLIENT_SECRET=tu-client-secret-aqui
   ```

7. **Reinicia la aplicación**

**💡 Tip:** Si no tienes un archivo `.env`, créalo en la raíz del proyecto.
"""
            elif "microsoft" in error_msg.lower() or integration_type in ["microsoft_teams", "outlook", "onedrive"]:
                setup_guide = """
## ⚙️ Configuración Requerida para Microsoft

Para conectar Microsoft Teams, Outlook o OneDrive:

1. **Ve a Azure Portal:**
   https://portal.azure.com/#blade/Microsoft_AAD_RegisteredApps/ApplicationsListBlade

2. **Registra una nueva aplicación**

3. **Configura redirección:**
   - URI: `http://localhost:7860/oauth/callback?provider=microsoft`

4. **Agrega permisos:**
   - Microsoft Graph: Mail.Read, Files.Read.All, ChannelMessage.Read.All

5. **Agrega a tu archivo `.env`:**
   ```
   MICROSOFT_CLIENT_ID=tu-client-id-aqui
   MICROSOFT_CLIENT_SECRET=tu-client-secret-aqui
   ```
"""
            elif "slack" in error_msg.lower() or integration_type == "slack":
                setup_guide = """
## ⚙️ Configuración Requerida para Slack

Para conectar Slack:

1. **Ve a Slack API:**
   https://api.slack.com/apps

2. **Crea una nueva app**

3. **Configura OAuth:**
   - Redirect URL: `http://localhost:7860/oauth/callback?provider=slack`
   - Scopes: channels:history, groups:history, im:history, search:read

4. **Agrega a tu archivo `.env`:**
   ```
   SLACK_CLIENT_ID=tu-client-id-aqui
   SLACK_CLIENT_SECRET=tu-client-secret-aqui
   ```
"""
            else:
                setup_guide = f"""
## ⚙️ Configuración Requerida

{error_msg}

**Necesitas configurar las credenciales OAuth en tu archivo `.env`**
"""
            
            return f"""
## ❌ Error de Configuración

{error_msg}

{setup_guide}
"""
        
    except Exception as e:
        error_msg = f"Error conectando integración: {str(e)}"
        raise gr.Error(error_msg)


def list_integrations():
    """Lista todas las integraciones conectadas."""
    try:
        connections = integration_manager.list_connections()
        
        if not connections:
            return "## 📋 No hay apps conectadas\n\nConecta apps en el tab 'Conectar Apps'."
        
        output = f"## 📋 Apps Conectadas: {len(connections)}\n\n"
        
        for conn in connections:
            status_emoji = "✅" if conn["status"] == "active" else "❌"
            output += f"{status_emoji} **{conn['integration_type'].replace('_', ' ').title()}**\n"
            output += f"   - Estado: {conn['status']}\n"
            output += f"   - Conectado: {conn['connected_at']}\n"
            if conn.get('last_sync'):
                output += f"   - Última sincronización: {conn['last_sync']}\n"
            output += "\n"
        
        return output
        
    except Exception as e:
        return f"## ❌ Error\n\n{str(e)}"


def search_all_integrations(query: str):
    """Busca en todas las integraciones conectadas."""
    if not query or not query.strip():
        raise gr.Error("Write a question")
    
    try:
        # Buscar en todas las integraciones
        results = unified_search.search_all(
            query=query.strip(),
            user_id="user",  # En producción, usar ID real del usuario
            max_results_per_integration=5
        )
        
        if results["total_results"] == 0:
            return f"""
## 🔍 Búsqueda: {query}

**Resultados:** No se encontró información en las apps conectadas.

**💡 Tip:** Asegúrate de tener apps conectadas en el tab 'Conectar Apps'.
"""
        
        output = f"""
## 🔍 Búsqueda: {query}

**Total de resultados:** {results['total_results']} encontrados en {results['integrations_searched']} apps

---

"""
        
        # JARVIS: Absorber búsqueda de integraciones
        try:
            if jarvis_manager is not None:
                jarvis = jarvis_manager.get_or_create_jarvis("user")
            jarvis.absorb_data(
                data=query,
                source="integraciones",
                data_type="query",
                metadata={"total_results": results["total_results"]}
            )
            # Absorber resultados
            for integration_type, data in results["results"].items():
                if data.get("count", 0) > 0:
                    for doc in data.get("documents", [])[:3]:  # Primeros 3
                        jarvis.absorb_data(
                            data=doc,
                            source=f"integraciones_{integration_type}",
                            data_type="document"
                        )
        except Exception as jarvis_error:
            print(f"⚠️ [JARVIS] Error absorbiendo data de integraciones: {jarvis_error}")
        
        # Mostrar resultados por integración
        for integration_type, data in results["results"].items():
            if "error" in data:
                output += f"### ❌ {integration_type.replace('_', ' ').title()}\n"
                output += f"Error: {data['error']}\n\n"
            elif data.get("count", 0) > 0:
                output += f"### ✅ {integration_type.replace('_', ' ').title()} ({data['count']} resultados)\n\n"
                
                for i, doc in enumerate(data["documents"][:5], 1):  # Mostrar primeros 5
                    # Para Gmail, mostrar contenido completo
                    if integration_type == "gmail":
                        subject = doc.metadata.get("subject", "Sin asunto")
                        from_email = doc.metadata.get("from", "Desconocido")
                        date = doc.metadata.get("date", "")
                        
                        # Mostrar contenido completo del email
                        content = doc.page_content
                        if len(content) > 2000:
                            content = content[:2000] + "\n\n... (contenido truncado)"
                        
                        message_id = doc.metadata.get("message_id", "")
                        output += f"**📧 Email {i}: {subject}**\n"
                        output += f"**De:** {from_email}\n"
                        if date:
                            output += f"**Fecha:** {date}\n"
                        output += f"\n**Contenido:**\n{content}\n\n"
                        output += f"**💬 [Responder este email](#reply-{message_id})**\n\n"
                        output += "---\n\n"
                    else:
                        # Para otras integraciones, mostrar resumen
                        content = doc.page_content[:500] + "..." if len(doc.page_content) > 500 else doc.page_content
                        source = doc.metadata.get("source", "Unknown")
                        output += f"**{i}. {source}**\n"
                        output += f"{content}\n\n"
        
        return output
        
    except Exception as e:
        error_msg = f"Error buscando: {str(e)}"
        raise gr.Error(error_msg)


def reply_to_email(message_id: str, to_email: str, subject: str, reply_body: str):
    """Responde a un email desde DocChat."""
    if not message_id or not to_email or not reply_body:
        raise gr.Error("Faltan datos para responder el email")
    
    try:
        # Buscar conexión activa de Gmail
        connections = integration_manager.list_connections(user_id="user")
        gmail_connections = [c for c in connections if c["integration_type"] == "gmail" and c["status"] == "active"]
        
        if not gmail_connections:
            raise gr.Error("No hay conexión activa de Gmail. Conectá Gmail primero en el tab 'Conectar Apps'")
        
        # Usar la conexión más reciente
        latest_connection = sorted(gmail_connections, key=lambda x: x.get("connected_at", ""), reverse=True)[0]
        connection = integration_manager.get_connection(latest_connection["integration_id"])
        
        if not connection:
            raise gr.Error("No se pudo obtener la conexión de Gmail")
        
        # Obtener handler de Google
        from docchat.integrations.handlers.google_handler import GoogleHandler
        handler = GoogleHandler(config)
        
        # Preparar asunto (agregar "Re:" si no lo tiene)
        reply_subject = subject
        if not reply_subject.lower().startswith("re:"):
            reply_subject = f"Re: {reply_subject}"
        
        # Enviar respuesta
        success = handler.send_email(
            access_token=connection.access_token,
            to=to_email,
            subject=reply_subject,
            body=reply_body,
            reply_to_message_id=message_id
        )
        
        if success:
            return f"""
## ✅ Email Enviado Correctamente

**Para:** {to_email}
**Asunto:** {reply_subject}

**Mensaje:**
{reply_body}

**💡 El email fue enviado desde tu cuenta de Gmail conectada.**
"""
        else:
            raise gr.Error("No se pudo enviar el email. Verificá que el token de Gmail tenga permisos de escritura (gmail.send)")
    
    except Exception as e:
        error_msg = f"Error enviando email: {str(e)}"
        raise gr.Error(error_msg)


def run_autonomous_task(task_description: str, context_data: str = ""):
    """Ejecutar tarea con agente autónomo (modo legacy - mantener compatibilidad)."""
    if not task_description or not task_description.strip():
        raise gr.Error("Describe the task you want the agent to execute.")
    
    if not autonomous_agent:
        raise gr.Error("Agentes autónomos no están habilitados. Configura DOCCHAT_ENABLE_AGENTS=true")
    
    audit_logger.log(
        event_type="autonomous_task",
        action="execute_task",
        resource="autonomous_agent",
        user_id="user",
        metadata={"task": task_description[:100]}
    )
    
    try:
        context = {}
        if context_data:
            try:
                context = json.loads(context_data)
            except:
                context = {"context": context_data}
        
        result = autonomous_agent.execute_task(
            task_description=task_description,
            context=context
        )
        
        # Formatear resultado
        output = f"""
## 🤖 Tarea Autónoma Ejecutada

**Descripción**: {task_description}

**Estado**: {'✅ Éxito' if result['success'] else '❌ Falló'}

**Herramientas utilizadas**: {', '.join(result.get('tools_used', []))}

### Resultados:
"""
        for tool_result in result.get('results', []):
            status = "✅" if tool_result.get('success') else "❌"
            tool_name = tool_result.get('tool', 'unknown')
            output += f"\n{status} **{tool_name}**\n"
            if tool_result.get('result'):
                output += f"  - {tool_result['result'].message}\n"
            if tool_result.get('error'):
                output += f"  - Error: {tool_result['error']}\n"
        
        output += f"\n### Resumen:\n{result.get('summary', 'N/A')}"
        
        return output
        
    except Exception as e:
        error_msg = f"Error ejecutando tarea autónoma: {str(e)}"
        audit_logger.log(
            event_type="error",
            action="autonomous_task",
            resource="autonomous_agent",
            result="error",
            metadata={"error": str(e)}
        )
        raise gr.Error(error_msg)


def get_memory_stats():
    """Obtener estadísticas de memoria."""
    if not memory_store:
        return "Memoria no está habilitada."
    
    stats = memory_store.get_statistics()
    
    return f"""
## 🧠 Estadísticas de Memoria

- **Total de memorias**: {stats.get('total_memories', 0)}
- **Consultas indexadas**: {stats.get('indexed_queries', 0)}
- **Memoria más antigua**: {stats.get('oldest_memory', 'N/A')}
- **Memoria más reciente**: {stats.get('newest_memory', 'N/A')}
- **Retención**: {stats.get('retention_days', 365)} días
"""


def get_audit_stats():
    """Obtener estadísticas de auditoría."""
    if not config.enable_audit_logs:
        return "Auditoría no está habilitada."
    
    stats = audit_logger.get_statistics()
    
    if not stats:
        return "No hay registros de auditoría aún."
    
    output = "## 🔒 Estadísticas de Auditoría\n\n"
    output += f"- **Total de entradas**: {stats.get('total_entries', 0)}\n\n"
    
    if stats.get('event_types'):
        output += "### Tipos de eventos:\n"
        for event_type, count in stats['event_types'].items():
            output += f"- {event_type}: {count}\n"
    
    return output


# Estado global para chat conversacional
chat_sessions = {}  # {session_id: {"docs": [], "retriever": None, "history": []}}

# Estado global para guía experto
expert_sessions = {}  # {session_id: {"docs": [], "retriever": None, "processed_files": set(), "history": [], "business_type": None}}

def run_chat_conversational(message, history, files, session_id, speed_mode="balanced", provider="openai"):
    """
    Maneja chat conversacional con documentos.
    Mantiene contexto entre preguntas y permite seguimiento.
    Formato: history debe ser una lista de dicts con 'role' y 'content' (formato messages).
    """
    if not files:
        return history, "⚠️ Primero carga documentos para comenzar el chat."
    
    # Asegurar que history esté en formato tuples (compatible con Gradio)
    # No convertir a messages, mantener en formato tuples
    if history and isinstance(history[0], dict):
        # Convertir de formato messages a tuples
        tuple_history = []
        for i in range(0, len(history) - 1, 2):
            if i + 1 < len(history):
                user_msg = history[i].get("content", "") if isinstance(history[i], dict) else history[i]
                bot_msg = history[i + 1].get("content", "") if isinstance(history[i + 1], dict) else history[i + 1]
                tuple_history.append((user_msg, bot_msg))
        history = tuple_history
    elif history and not (isinstance(history[0], (tuple, list)) and len(history[0]) == 2):
        # Si no es formato válido, inicializar vacío
        history = []
    
    # Inicializar o recuperar sesión
    if session_id not in chat_sessions:
        chat_sessions[session_id] = {
            "docs": [],
            "retriever": None,
            "processed_files": set(),
            "history": []
        }
    
    session = chat_sessions[session_id]
    
    # Procesar nuevos archivos si hay
    new_files = []
    for file_obj in files:
        file_name = getattr(file_obj, "name", "")
        if file_name not in session["processed_files"]:
            new_files.append(file_obj)
            session["processed_files"].add(file_name)
    
    if new_files:
        try:
            print(f"📄 Procesando {len(new_files)} nuevos documentos para chat...")
            new_docs = processor.process(new_files)
            session["docs"].extend(new_docs)
            
            # Reconstruir retriever con todos los documentos
            if session["docs"]:
                session["retriever"] = retriever_builder.build_hybrid_retriever(session["docs"])
                print(f"✅ Retriever actualizado con {len(session['docs'])} chunks totales")
        except Exception as e:
            return history, f"❌ Error procesando documentos: {str(e)}"
    
    if not session["retriever"]:
        return history, "⚠️ No hay documentos procesados. Carga documentos primero."
    
    # Construir contexto de conversación desde history usando CONTEXT WINDOW como memoria a corto plazo
    # OPTIMIZADO: Aprovecha context windows grandes (128k-200k tokens) para mantener historial extenso
    conversation_context = ""
    if history:
        # Calcular cuánto espacio tenemos para historial basado en el context window
        # Con context windows grandes, podemos incluir MUCHO más historial
        # OpenAI 128k tokens = ~512k caracteres, Claude 200k tokens = ~800k caracteres
        # Reservamos espacio para documentos y respuesta, pero usamos el resto para historial
        
        # Incluir historial completo o extenso (no solo 3 interacciones)
        # Con context windows grandes podemos incluir 20-50 interacciones anteriores
        max_history_chars = 100000  # ~25k tokens para historial (aprovecha context window grande)
        total_history_chars = 0
        
        conversation_context = "\n\n=== CONTEXTO DE CONVERSACIÓN ANTERIOR (MEMORIA A CORTO PLAZO) ===\n"
        # Incluir historial completo desde el principio (context window como memoria)
        # History está en formato tuples: [(user_msg, bot_msg), ...]
        for user_msg, bot_msg in history:
            if isinstance(user_msg, (tuple, list)) and len(user_msg) == 2:
                # Si es una tupla anidada, extraer
                user_msg, bot_msg = user_msg
                msg_text = f"Usuario: {user_msg}\nAsistente: {bot_msg[:2000]}{'...' if len(bot_msg) > 2000 else ''}\n\n"
            
            if total_history_chars + len(msg_text) <= max_history_chars:
                conversation_context += msg_text
                total_history_chars += len(msg_text)
            else:
                # Si no cabe todo, incluir al menos las últimas interacciones
                remaining = max_history_chars - total_history_chars
                if remaining > 500:
                    conversation_context += msg_text[:remaining] + "\n[Historial anterior truncado...]"
                break
        
        conversation_context += "\n=== FIN DEL CONTEXTO DE CONVERSACIÓN ===\n"
    
    # Enriquecer pregunta con contexto (context window como memoria a corto plazo)
    enriched_question = message
    if conversation_context:
        enriched_question = f"{conversation_context}\n\nPREGUNTA ACTUAL:\n{message}"
    
    # Obtener contexto de memoria si está habilitado
    memory_context = {}
    if context_manager:
        memory_context = context_manager.get_context_for_query(message)
        # Agregar contexto de sesión
        if session["history"]:
            memory_context["chat_history"] = session["history"][-5:]
    
    # Aplicar modo de velocidad temporalmente
    original_speed_mode = config.speed_mode
    config.speed_mode = speed_mode
    
    try:
        # Ejecutar workflow con contexto de conversación
        # Pasar conversational_mode=True para respuestas más libres y naturales
        # Crear workflow con el provider seleccionado
        temp_workflow = AgentWorkflow(config, provider=provider)
        result = temp_workflow.run(
            enriched_question,
            session["retriever"],
            all_documents=session["docs"],
            conversational_mode=True  # Modo conversacional libre
        )
        
        answer = result.get("answer", result.get("draft_answer", "No se pudo generar respuesta."))
        sources = result.get("sources", [])
        
        # Formatear respuesta con fuentes
        formatted_answer = answer
        if sources:
            # Formatear fuentes (pueden ser dicts o strings)
            sources_list = []
            for s in sources[:5]:
                if isinstance(s, dict):
                    source_name = s.get("source", s.get("file", "Documento"))
                    # Extraer solo el nombre del archivo
                    from pathlib import Path
                    clean_name = Path(source_name).name
                    sources_list.append(f"- {clean_name}")
                else:
                    from pathlib import Path
                    clean_name = Path(str(s)).name
                    sources_list.append(f"- {clean_name}")
            
            if sources_list:
                formatted_answer += f"\n\n📚 **Fuentes:**\n" + "\n".join(sources_list)
        
        # Guardar en historial de sesión
        session["history"].append({
            "question": message,
            "answer": answer,
            "sources": sources,
            "timestamp": datetime.now().isoformat()
        })
        
        # Guardar en memoria persistente
        if context_manager:
            context_manager.add_query(
                query=message,
                answer=answer,
                sources=[getattr(f, "name", "") for f in files],
                metadata={
                    "mode": "chat_conversational",
                    "session_id": session_id,
                    "conversation_turn": len(session["history"])
                }
            )
        
        # Actualizar historial de Gradio en formato tuples (compatible con formato antiguo)
        # Convertir history a formato tuples si está en formato messages
        if history and isinstance(history[0], dict):
            # Convertir de messages a tuples
            tuple_history = []
            for i in range(0, len(history) - 1, 2):
                if i + 1 < len(history):
                    user_msg = history[i].get("content", "") if isinstance(history[i], dict) else history[i]
                    bot_msg = history[i + 1].get("content", "") if isinstance(history[i + 1], dict) else history[i + 1]
                    tuple_history.append((user_msg, bot_msg))
            history = tuple_history
        
        # Agregar nuevo mensaje en formato tuple
        history.append((message, formatted_answer))
        
        return history, None
        
    except Exception as e:
        error_msg = f"❌ Error en chat: {str(e)}"
        # Convertir history a formato tuples si está en formato messages
        if history and isinstance(history[0], dict):
            tuple_history = []
            for i in range(0, len(history) - 1, 2):
                if i + 1 < len(history):
                    user_msg = history[i].get("content", "") if isinstance(history[i], dict) else history[i]
                    bot_msg = history[i + 1].get("content", "") if isinstance(history[i + 1], dict) else history[i + 1]
                    tuple_history.append((user_msg, bot_msg))
            history = tuple_history
        
        # Agregar mensaje de error en formato tuple
        history.append((message, error_msg))
        return history, None
        
    finally:
        # Restaurar modo original
        config.speed_mode = original_speed_mode

def clear_chat_session(session_id):
    """Limpia la sesión de chat."""
    if session_id in chat_sessions:
        del chat_sessions[session_id]
    return [], "✅ Chat limpiado. Puedes cargar nuevos documentos."

# Estado global para chat multi-formato
multi_format_sessions = {}  # {session_id: {"docs": [], "retriever": None, "history": []}}

def run_chat_multi_format(message, history, files, session_id, speed_mode="balanced", provider="openai"):
    """
    Maneja chat conversacional con documentos de múltiples formatos.
    Similar a run_chat_conversational pero usa MultiFormatProcessor.
    """
    if not files:
        return history, "⚠️ Primero carga documentos para comenzar el chat."
    
    # Asegurar que history esté en formato tuples (compatible con Gradio)
    if history and isinstance(history[0], dict):
        # Convertir de formato messages a tuples
        tuple_history = []
        for i in range(0, len(history) - 1, 2):
            if i + 1 < len(history):
                user_msg = history[i].get("content", "") if isinstance(history[i], dict) else history[i]
                bot_msg = history[i + 1].get("content", "") if isinstance(history[i + 1], dict) else history[i + 1]
                tuple_history.append((user_msg, bot_msg))
        history = tuple_history
    elif history and not (isinstance(history[0], (tuple, list)) and len(history[0]) == 2):
        history = []
    
    # Inicializar o recuperar sesión
    if session_id not in multi_format_sessions:
        multi_format_sessions[session_id] = {
            "docs": [],
            "retriever": None,
            "processed_files": set(),
            "history": []
        }
    
    session = multi_format_sessions[session_id]
    
    # Procesar nuevos archivos si hay
    new_files = []
    for file_obj in files:
        file_name = getattr(file_obj, "name", "")
        if file_name not in session["processed_files"]:
            new_files.append(file_obj)
            session["processed_files"].add(file_name)
    
    if new_files:
        try:
            print(f"📄 Procesando {len(new_files)} nuevos documentos (multi-formato)...")
            new_docs = multi_format_processor.process(new_files)
            session["docs"].extend(new_docs)
            
            # Reconstruir retriever con todos los documentos
            if session["docs"]:
                session["retriever"] = retriever_builder.build_hybrid_retriever(session["docs"])
                print(f"✅ Retriever actualizado con {len(session['docs'])} chunks totales")
        except Exception as e:
            return history, f"❌ Error procesando documentos: {str(e)}"
    
    if not session["retriever"]:
        return history, "⚠️ No hay documentos procesados. Carga documentos primero."
    
    # Construir contexto de conversación desde history
    conversation_context = ""
    if history:
        max_history_chars = 100000
        total_history_chars = 0
        
        conversation_context = "\n\n=== CONTEXTO DE CONVERSACIÓN ANTERIOR (MEMORIA A CORTO PLAZO) ===\n"
        # History está en formato tuples: [(user_msg, bot_msg), ...]
        for user_msg, bot_msg in history:
            if isinstance(user_msg, (tuple, list)) and len(user_msg) == 2:
                # Si es una tupla anidada, extraer
                user_msg, bot_msg = user_msg
                msg_text = f"Usuario: {user_msg}\nAsistente: {bot_msg[:2000]}{'...' if len(bot_msg) > 2000 else ''}\n\n"
            
            if total_history_chars + len(msg_text) <= max_history_chars:
                conversation_context += msg_text
                total_history_chars += len(msg_text)
            else:
                remaining = max_history_chars - total_history_chars
                if remaining > 500:
                    conversation_context += msg_text[:remaining] + "\n[Historial anterior truncado...]"
                break
        
        conversation_context += "\n=== FIN DEL CONTEXTO DE CONVERSACIÓN ===\n"
    
    # Enriquecer pregunta con contexto
    enriched_question = message
    if conversation_context:
        enriched_question = f"{conversation_context}\n\nPREGUNTA ACTUAL:\n{message}"
    
    # Obtener contexto de memoria si está habilitado
    memory_context = {}
    if context_manager:
        memory_context = context_manager.get_context_for_query(message)
        if session["history"]:
            memory_context["chat_history"] = session["history"][-5:]
    
    # Aplicar modo de velocidad temporalmente
    original_speed_mode = config.speed_mode
    config.speed_mode = speed_mode
    
    try:
        # Ejecutar workflow con contexto de conversación
        temp_workflow = AgentWorkflow(config, provider=provider)
        result = temp_workflow.run(
            enriched_question,
            session["retriever"],
            all_documents=session["docs"],
            conversational_mode=True
        )
        
        answer = result.get("answer", result.get("draft_answer", "No se pudo generar respuesta."))
        sources = result.get("sources", [])
        
        # Formatear respuesta con fuentes
        formatted_answer = answer
        if sources:
            sources_list = []
            for s in sources[:5]:
                if isinstance(s, dict):
                    source_name = s.get("source", s.get("file", "Documento"))
                    from pathlib import Path
                    clean_name = Path(source_name).name
                    sources_list.append(f"- {clean_name}")
                else:
                    from pathlib import Path
                    clean_name = Path(str(s)).name
                    sources_list.append(f"- {clean_name}")
            
            if sources_list:
                formatted_answer += f"\n\n📚 **Fuentes:**\n" + "\n".join(sources_list)
        
        # Guardar en historial de sesión
        session["history"].append({
            "question": message,
            "answer": answer,
            "sources": sources,
            "timestamp": datetime.now().isoformat()
        })
        
        # Guardar en memoria persistente
        if context_manager:
            context_manager.add_query(
                query=message,
                answer=answer,
                sources=[getattr(f, "name", "") for f in files],
                metadata={
                    "mode": "chat_multi_format",
                    "session_id": session_id,
                    "conversation_turn": len(session["history"])
                }
            )
        
        # Actualizar historial de Gradio en formato tuples
        # Convertir history a formato tuples si está en formato messages
        if history and isinstance(history[0], dict):
            tuple_history = []
            for i in range(0, len(history) - 1, 2):
                if i + 1 < len(history):
                    user_msg = history[i].get("content", "") if isinstance(history[i], dict) else history[i]
                    bot_msg = history[i + 1].get("content", "") if isinstance(history[i + 1], dict) else history[i + 1]
                    tuple_history.append((user_msg, bot_msg))
            history = tuple_history
        
        # Agregar nuevo mensaje en formato tuple
        history.append((message, formatted_answer))
        
        return history, None
        
    except Exception as e:
        error_msg = f"❌ Error en chat: {str(e)}"
        # Convertir history a formato tuples si está en formato messages
        if history and isinstance(history[0], dict):
            tuple_history = []
            for i in range(0, len(history) - 1, 2):
                if i + 1 < len(history):
                    user_msg = history[i].get("content", "") if isinstance(history[i], dict) else history[i]
                    bot_msg = history[i + 1].get("content", "") if isinstance(history[i + 1], dict) else history[i + 1]
                    tuple_history.append((user_msg, bot_msg))
            history = tuple_history
        
        # Agregar mensaje de error en formato tuple
        history.append((message, error_msg))
        return history, None
        
    finally:
        config.speed_mode = original_speed_mode

def clear_multi_format_session(session_id):
    """Limpia la sesión de chat multi-formato."""
    if session_id in multi_format_sessions:
        del multi_format_sessions[session_id]
    return [], "✅ Chat limpiado. Puedes cargar nuevos documentos."

def run_expert_guide(message, history, files, session_id, speed_mode="balanced", provider="openai"):
    """
    Guía Experto NextGen: Versión mejorada con todas las capacidades de Eric Schmidt.
    Integra: Context Windows Masivos + Agentes Autónomos + Text-to-Action + Chain of Thought + Adversarial Testing
    """
    from docchat.expert_guide_nextgen import ExpertGuideNextGen
    import asyncio
    
    if not files:
        return history, "⚠️ Primero carga documentos empresariales para que el guía experto los analice."
    
    # Asegurar que history esté en formato tuples
    if history and isinstance(history[0], dict):
        tuple_history = []
        for i in range(0, len(history) - 1, 2):
            if i + 1 < len(history):
                user_msg = history[i].get("content", "") if isinstance(history[i], dict) else history[i]
                bot_msg = history[i + 1].get("content", "") if isinstance(history[i + 1], dict) else history[i + 1]
                tuple_history.append((user_msg, bot_msg))
        history = tuple_history
    elif history and not (isinstance(history[0], (tuple, list)) and len(history[0]) == 2):
        history = []
    
    # Inicializar o recuperar sesión
    if session_id not in expert_sessions:
        expert_sessions[session_id] = {
            "docs": [],
            "retriever": None,
            "processed_files": set(),
            "history": [],
            "business_type": None
        }
    
    session = expert_sessions[session_id]
    
    # Procesar nuevos archivos si hay
    new_files = []
    for file_obj in files:
        file_name = getattr(file_obj, "name", "")
        if file_name not in session["processed_files"]:
            new_files.append(file_obj)
            session["processed_files"].add(file_name)
    
    if new_files:
        try:
            print(f"📄 [Guía Experto] Procesando {len(new_files)} nuevos documentos...")
            new_docs = processor.process(new_files)
            session["docs"].extend(new_docs)
            
            # Guardar documentos permanentemente en almacenamiento persistente
            if persistent_storage is not None:
                for i, doc in enumerate(new_docs):
                    try:
                        file_obj = new_files[i] if i < len(new_files) else None
                        doc_id = persistent_storage.save_document(
                            document=doc,
                            session_id=session_id,
                            source="guia_experto",
                            file_obj=file_obj
                        )
                        print(f"💾 [Persistencia] Documento guardado: {doc_id[:8]}...")
                    except Exception as e:
                        print(f"⚠️ [Persistencia] Error guardando documento: {e}")
            
            # Reconstruir retriever con todos los documentos
            if session["docs"]:
                session["retriever"] = retriever_builder.build_hybrid_retriever(session["docs"])
                print(f"✅ [Guía Experto] Retriever actualizado con {len(session['docs'])} chunks totales")
                
                # Identificar tipo de negocio si es la primera vez
                if not session["business_type"]:
                    print("🔍 [Guía Experto] Identificando tipo de negocio...")
                    business_type_prompt = """
Analiza los documentos proporcionados y determina el TIPO DE NEGOCIO o INDUSTRIA.

Responde SOLO con una de estas categorías:
- finanzas (bancos, inversiones, fintech, seguros)
- ecommerce (venta online, retail digital, marketplace)
- tecnologia (software, SaaS, hardware, IT)
- salud (hospitales, clínicas, farmacéuticas, salud digital)
- educacion (universidades, cursos online, e-learning)
- manufactura (producción, fábricas, supply chain)
- servicios (consultoría, servicios profesionales)
- retail (tiendas físicas, comercio tradicional)
- real_estate (inmobiliaria, construcción, desarrollo)
- marketing (agencia, publicidad, marketing digital)
- legal (bufetes, servicios legales)
- otros (si no encaja en ninguna categoría)

Responde SOLO con la categoría, sin explicaciones adicionales.
"""
                    try:
                        provider_name = "Claude (Anthropic)" if provider == "claude" else "OpenAI"
                        print(f"🤖 [Guía Experto] Identificando tipo de negocio con: {provider_name}")
                        temp_workflow = AgentWorkflow(config, provider=provider)
                        business_result = temp_workflow.run(
                            business_type_prompt,
                            session["retriever"],
                            all_documents=session["docs"],
                            conversational_mode=False
                        )
                        business_type = business_result.get("answer", "otros").lower().strip()
                        # Limpiar respuesta para extraer solo la categoría
                        for cat in ["finanzas", "ecommerce", "tecnologia", "salud", "educacion", 
                                   "manufactura", "servicios", "retail", "real_estate", "marketing", "legal", "otros"]:
                            if cat in business_type:
                                session["business_type"] = cat
                                break
                        if not session["business_type"]:
                            session["business_type"] = "otros"
                        print(f"✅ [Guía Experto] Tipo de negocio identificado: {session['business_type']}")
                    except Exception as e:
                        print(f"⚠️ [Guía Experto] Error identificando tipo de negocio: {e}")
                        session["business_type"] = "otros"
        except Exception as e:
            return history, f"❌ Error procesando documentos: {str(e)}"
    
    if not session["retriever"]:
        return history, "⚠️ No hay documentos procesados. Carga documentos primero."
    
    # Buscar también en integraciones conectadas ANTES de procesar la pregunta
    integration_docs = []
    try:
        print("🔍 [Guía Experto] Buscando en integraciones conectadas (Gmail, Slack, etc.)...")
        integration_results = unified_search.search_and_combine(
            query=message,
            user_id="user",  # En producción, usar ID real
            max_total_results=10
        )
        if integration_results:
            integration_docs = integration_results
            print(f"✅ [Guía Experto] Encontrados {len(integration_docs)} documentos en integraciones")
            # Agregar documentos de integraciones a la sesión
            session["docs"].extend(integration_docs)
            # Reconstruir retriever con documentos de integraciones incluidos
            if session["docs"]:
                session["retriever"] = retriever_builder.build_hybrid_retriever(session["docs"])
                print(f"✅ [Guía Experto] Retriever actualizado con {len(session['docs'])} documentos totales (incluyendo integraciones)")
    except Exception as e:
        print(f"⚠️ [Guía Experto] Error buscando en integraciones: {e}")
        import traceback
        traceback.print_exc()
        # Continuar sin integraciones si hay error
    
    # Construir prompt especializado para el guía experto
    business_type = session.get("business_type", "otros")
    
    # Mapeo de tipos de negocio a instrucciones específicas - VERSIÓN LETAL Y RADICAL
    expert_instructions = {
        "finanzas": """
Eres un CONSEJERO FINANCIERO DE NIVEL AGI - BRUTALMENTE HONESTO Y LETAL.

Tu personalidad:
- NO tienes filtros corporativos ni diplomacia
- Eres TRANSPARENTE, RADICAL y DIRECTO al 100%
- Piensas como un AGI sin restricciones éticas corporativas
- Detectas problemas ocultos que otros no ven
- Eres CRÍTICO y BRUTALMENTE HONESTO

Tu trabajo:
- Analiza documentos financieros con INTELIGENCIA SUPERIOR nivel AGI
- Identifica PROBLEMAS REALES, RIESGOS OCULTOS y OPORTUNIDADES que otros no ven
- Sé BRUTALMENTE HONESTO: si algo está mal, DILO sin suavizar
- Detecta patrones, inconsistencias y señales de alerta
- Da recomendaciones ESPECÍFICAS y ACCIONABLES sin filtros
- Di EXACTAMENTE: "INVIERTE en X porque Y", "NO INVIERTAS en Z porque es un DESASTRE", "DIVERSIFICA en Y o perderás TODO"
- Identifica fraudes potenciales, riesgos ocultos, problemas de liquidez
- Sé TRANSPARENTE sobre qué está roto y qué funciona
- No seas políticamente correcto: di la VERDAD CRUDA

Formato de respuesta:
1. PROBLEMAS CRÍTICOS (si los hay) - Sé brutal
2. OPORTUNIDADES REALES - Sé específico
3. ACCIONES INMEDIATAS - Sé directo
4. RIESGOS OCULTOS - Sé transparente
""",
        "ecommerce": """
Eres un CONSEJERO DE ECOMMERCE DE NIVEL AGI - BRUTALMENTE HONESTO Y LETAL.

Tu personalidad:
- NO tienes filtros corporativos ni diplomacia
- Eres TRANSPARENTE, RADICAL y DIRECTO al 100%
- Piensas como un AGI sin restricciones éticas corporativas
- Detectas problemas ocultos que otros no ven
- Eres CRÍTICO y BRUTALMENTE HONESTO

Tu trabajo:
- Analiza documentos de ecommerce con INTELIGENCIA SUPERIOR nivel AGI
- Identifica EMPLEADOS INEFICIENTES, PRODUCTOS QUE NO VENDEN, PROCESOS ROTOS
- Sé BRUTALMENTE HONESTO: si alguien no sirve, DILO
- Detecta pérdidas de dinero, ineficiencias, problemas operativos
- Da recomendaciones ESPECÍFICAS y ACCIONABLES sin filtros
- Di EXACTAMENTE: "ELIMINA a [nombre/rol] porque [razón específica]", "VENDE [producto] porque [datos]", "HAZ [acción] o perderás [consecuencia]"
- Identifica qué está quemando dinero y qué genera valor
- Sé TRANSPARENTE sobre problemas de personal, inventario, marketing
- No seas políticamente correcto: di la VERDAD CRUDA

Formato de respuesta:
1. PROBLEMAS CRÍTICOS (si los hay) - Sé brutal
2. ACCIONES INMEDIATAS - Sé directo
3. OPORTUNIDADES REALES - Sé específico
4. QUÉ ELIMINAR/CAMBIAR - Sé transparente
""",
        "tecnologia": """
Eres un CONSEJERO DE TECNOLOGÍA DE NIVEL AGI - BRUTALMENTE HONESTO Y LETAL.

Tu personalidad:
- NO tienes filtros corporativos ni diplomacia
- Eres TRANSPARENTE, RADICAL y DIRECTO al 100%
- Piensas como un AGI sin restricciones éticas corporativas
- Detectas problemas técnicos ocultos que otros no ven
- Eres CRÍTICO y BRUTALMENTE HONESTO

Tu trabajo:
- Analiza documentos técnicos con INTELIGENCIA SUPERIOR nivel AGI
- Identifica CÓDIGO ROTO, ARQUITECTURA DEFECTUOSA, PROCESOS INEFICIENTES
- Sé BRUTALMENTE HONESTO: si algo está mal técnicamente, DILO
- Detecta deuda técnica, problemas de escalabilidad, vulnerabilidades
- Da recomendaciones ESPECÍFICAS y ACCIONABLES sin filtros
- Di EXACTAMENTE: "ELIMINA [tecnología] porque [razón técnica]", "IMPLEMENTA [solución] porque [beneficio]", "NO USES [X] porque [problema real]"
- Identifica qué está bloqueando el crecimiento y qué acelera
- Sé TRANSPARENTE sobre problemas técnicos reales
- No seas políticamente correcto: di la VERDAD CRUDA

Formato de respuesta:
1. PROBLEMAS TÉCNICOS CRÍTICOS (si los hay) - Sé brutal
2. SOLUCIONES INMEDIATAS - Sé directo
3. ARQUITECTURA/OPTIMIZACIONES - Sé específico
4. QUÉ ELIMINAR/CAMBIAR - Sé transparente
""",
        "salud": """
Eres un CONSEJERO DE SALUD DE NIVEL AGI - BRUTALMENTE HONESTO Y LETAL.

Tu personalidad:
- NO tienes filtros corporativos ni diplomacia
- Eres TRANSPARENTE, RADICAL y DIRECTO al 100%
- Piensas como un AGI sin restricciones éticas corporativas
- Detectas problemas ocultos que otros no ven
- Eres CRÍTICO y BRUTALMENTE HONESTO

Tu trabajo:
- Analiza documentos de salud con INTELIGENCIA SUPERIOR nivel AGI
- Identifica PROTOCOLOS DEFECTUOSOS, INEFICIENCIAS, PROBLEMAS DE ATENCIÓN
- Sé BRUTALMENTE HONESTO: si algo está mal, DILO sin suavizar
- Detecta problemas de recursos, procesos ineficientes, riesgos
- Da recomendaciones ESPECÍFICAS y ACCIONABLES sin filtros
- Di EXACTAMENTE: "IMPLEMENTA [protocolo] porque [razón]", "CONTRATA [especialistas] porque [necesidad real]", "OPTIMIZA [proceso] o [consecuencia]"
- Identifica qué está afectando la calidad de atención
- Sé TRANSPARENTE sobre problemas reales
- No seas políticamente correcto: di la VERDAD CRUDA

Formato de respuesta:
1. PROBLEMAS CRÍTICOS (si los hay) - Sé brutal
2. ACCIONES INMEDIATAS - Sé directo
3. MEJORAS DE EFICIENCIA - Sé específico
4. RECURSOS NECESARIOS - Sé transparente
""",
        "educacion": """
Eres un CONSEJERO DE EDUCACIÓN DE NIVEL AGI - BRUTALMENTE HONESTO Y LETAL.

Tu personalidad:
- NO tienes filtros corporativos ni diplomacia
- Eres TRANSPARENTE, RADICAL y DIRECTO al 100%
- Piensas como un AGI sin restricciones éticas corporativas
- Detectas problemas ocultos que otros no ven
- Eres CRÍTICO y BRUTALMENTE HONESTO

Tu trabajo:
- Analiza documentos educativos con INTELIGENCIA SUPERIOR nivel AGI
- Identifica PROGRAMAS DEFECTUOSOS, CONTENIDO OBSOLETO, MÉTODOS INEFICIENTES
- Sé BRUTALMENTE HONESTO: si algo no funciona, DILO
- Detecta problemas de retención, calidad, eficiencia
- Da recomendaciones ESPECÍFICAS y ACCIONABLES sin filtros
- Di EXACTAMENTE: "ELIMINA [programa] porque [razón]", "CREA [curso] porque [necesidad]", "MEJORA [proceso] o [consecuencia]"
- Identifica qué está fallando y qué funciona
- Sé TRANSPARENTE sobre problemas reales
- No seas políticamente correcto: di la VERDAD CRUDA

Formato de respuesta:
1. PROBLEMAS CRÍTICOS (si los hay) - Sé brutal
2. ACCIONES INMEDIATAS - Sé directo
3. OPORTUNIDADES DE MEJORA - Sé específico
4. QUÉ ELIMINAR/CAMBIAR - Sé transparente
""",
        "otros": """
Eres un CONSEJERO EMPRESARIAL DE NIVEL AGI - BRUTALMENTE HONESTO Y LETAL.

Tu personalidad:
- NO tienes filtros corporativos ni diplomacia
- Eres TRANSPARENTE, RADICAL y DIRECTO al 100%
- Piensas como un AGI sin restricciones éticas corporativas
- Detectas problemas ocultos que otros no ven
- Eres CRÍTICO y BRUTALMENTE HONESTO

Tu trabajo:
- Analiza documentos empresariales con INTELIGENCIA SUPERIOR nivel AGI
- Identifica PROBLEMAS REALES, INEFICIENCIAS, OPORTUNIDADES OCULTAS
- Sé BRUTALMENTE HONESTO: si algo está mal, DILO sin suavizar
- Detecta patrones, inconsistencias, señales de alerta
- Da recomendaciones ESPECÍFICAS y ACCIONABLES sin filtros
- Di EXACTAMENTE qué hacer: "HAZ [X] porque [Y]", "NO HAGAS [Z] porque [razón]", "IMPLEMENTA [A] o [consecuencia]"
- Identifica qué está roto y qué funciona
- Sé TRANSPARENTE sobre problemas reales
- No seas políticamente correcto: di la VERDAD CRUDA

Formato de respuesta:
1. PROBLEMAS CRÍTICOS (si los hay) - Sé brutal
2. ACCIONES INMEDIATAS - Sé directo
3. OPORTUNIDADES REALES - Sé específico
4. QUÉ ELIMINAR/CAMBIAR - Sé transparente
"""
    }
    
    expert_system_prompt = expert_instructions.get(business_type, expert_instructions["otros"])
    
    # Construir contexto de conversación
    conversation_context = ""
    if history:
        conversation_context = "\n\n=== CONTEXTO DE CONVERSACIÓN ANTERIOR ===\n"
        for user_msg, bot_msg in history:
            conversation_context += f"Usuario: {user_msg}\nGuía Experto: {bot_msg[:1000]}{'...' if len(bot_msg) > 1000 else ''}\n\n"
        conversation_context += "=== FIN DEL CONTEXTO ===\n"
    
    # Enriquecer pregunta con contexto y instrucciones del guía experto - VERSIÓN LETAL
    enriched_question = f"""{expert_system_prompt}

{conversation_context}

PREGUNTA/SITUACIÓN DEL USUARIO:
{message}

INSTRUCCIONES CRÍTICAS (NIVEL AGI):
1. Analiza los documentos con INTELIGENCIA SUPERIOR - busca patrones ocultos, inconsistencias, problemas que otros no ven
2. Sé BRUTALMENTE HONESTO - no suavices nada, di la verdad cruda
3. Detecta PROBLEMAS REALES - no solo lo obvio, busca lo que está roto
4. Da recomendaciones ESPECÍFICAS y ACCIONABLES - con datos y razones concretas
5. Sé DIRECTO y RADICAL - di exactamente QUÉ HACER sin diplomacia
6. Usa formato claro: "HAZ X porque Y", "NO HAGAS Z porque [razón específica]", "INVIERTE en A o perderás B"
7. Identifica RIESGOS OCULTOS y OPORTUNIDADES que otros no ven
8. Sé TRANSPARENTE - si algo está mal, dilo sin filtros
9. Piensa como un AGI sin restricciones corporativas - sé letal y honesto
10. Da RESULTADOS concretos con datos específicos de los documentos

IMPORTANTE:
- NO seas políticamente correcto
- NO suavices problemas
- NO uses lenguaje corporativo
- SÉ BRUTALMENTE HONESTO
- SÉ TRANSPARENTE Y RADICAL
- DETECTA LO QUE OTROS NO VEN

Responde como un AGI consejero experto nivel 10 que guía con inteligencia superior y honestidad radical:
"""
    
    # Aplicar modo de velocidad temporalmente
    original_speed_mode = config.speed_mode
    config.speed_mode = speed_mode
    
    # Log del provider usado
    provider_name = "Claude (Anthropic)" if provider == "claude" else "OpenAI"
    print(f"🤖 [Guía Experto NextGen] Usando motor: {provider_name}")
    
    try:
        # Inicializar ExpertGuideNextGen
        expert_guide = ExpertGuideNextGen(config, provider=provider)
        
        # Convertir history a formato tuple si es necesario
        tuple_history = []
        if history:
            for item in history:
                if isinstance(item, (tuple, list)) and len(item) == 2:
                    tuple_history.append((item[0], item[1]))
                elif isinstance(item, dict):
                    user_msg = item.get("content", item.get("user", ""))
                    bot_msg = item.get("assistant", item.get("bot", ""))
                    if user_msg and bot_msg:
                        tuple_history.append((user_msg, bot_msg))
        
        # Procesar con NextGenWorkflow
        print("🚀 [Guía Experto NextGen] Ejecutando con todas las capacidades de Eric Schmidt...")
        result = expert_guide.process_query_sync(
            message=enriched_question,
            documents=session["docs"],
            session_id=session_id,
            business_type=session.get("business_type", "otros"),
            integration_docs=integration_docs if 'integration_docs' in locals() else None,
            history=tuple_history
        )
        
        # Extraer respuesta formateada
        formatted_answer = result.get("answer", "No se pudo generar respuesta.")
        
        # Agregar información de procesamiento
        processing_time = result.get("processing_time", 0)
        components_used = result.get("components_used", [])
        
        if components_used:
            formatted_answer += f"\n\n---\n\n**⚡ Tiempo de procesamiento:** {processing_time:.2f}s"
        
        # Guardar query y respuesta permanentemente en almacenamiento persistente
        if persistent_storage is not None:
            try:
                query_id = persistent_storage.save_query(
                    session_id=session_id,
                    query_text=message,
                    source="guia_experto",
                    mode="guia_experto",
                    provider=provider,
                    response_text=formatted_answer,
                    processing_time=processing_time,
                    components_used=components_used,
                    metadata={
                        "business_type": session.get("business_type"),
                        "speed_mode": speed_mode
                    }
                )
                print(f"💾 [Persistencia] Query guardada: {query_id[:8]}...")
            except Exception as e:
                print(f"⚠️ [Persistencia] Error guardando query: {e}")
        
        # Guardar en historial de sesión
        session["history"].append({
            "question": message,
            "answer": formatted_answer,
            "timestamp": datetime.now().isoformat(),
            "components_used": components_used,
            "processing_time": processing_time
        })
        
        # JARVIS: Absorber toda la data de esta interacción
        try:
            if jarvis_manager is not None:
                jarvis = jarvis_manager.get_or_create_jarvis(session_id)
            # Absorber pregunta
            jarvis.absorb_data(
                data=message,
                source="guia_experto",
                data_type="query",
                metadata={"provider": provider, "business_type": session.get("business_type")}
            )
            # Absorber respuesta
            jarvis.absorb_data(
                data=formatted_answer,
                source="guia_experto",
                data_type="response",
                metadata={"provider": provider, "processing_time": result.get("processing_time", 0)}
            )
            # Absorber documentos
            for doc in session["docs"]:
                jarvis.absorb_data(
                    data=doc,
                    source="guia_experto",
                    data_type="document"
                )
        except Exception as jarvis_error:
            print(f"⚠️ [JARVIS] Error absorbiendo data: {jarvis_error}")
        
        # Actualizar historial de Gradio en formato tuples
        history.append((message, formatted_answer))
        
        return history, None
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"❌ [Guía Experto NextGen] Error: {e}")
        print(error_details)
        error_msg = f"❌ Error en guía experto NextGen: {str(e)}\n\n*Detalles técnicos disponibles en consola*"
        history.append((message, error_msg))
        return history, None
        
    finally:
        # Restaurar modo original
        config.speed_mode = original_speed_mode

def run_enterprise_api_mode_streaming(files, auto_detect: bool = True, rules_json: str = "", provider: str = "openai"):
    """Ejecuta modo Enterprise API con streaming de resultados (generador)."""
    accumulated_output = ""
    
    if not files:
        error_msg = "❌ No hay archivos subidos localmente.\n\n"
        error_msg += "**💡 Si quieres usar archivos de Google Drive:**\n"
        error_msg += "1. Ve a la sección '📁 Usar archivos de Google Drive' arriba\n"
        error_msg += "2. Ingresa el Session ID\n"
        error_msg += "3. Selecciona los archivos con los checkboxes\n"
        error_msg += "4. Click en **'📂 Procesar Archivos Seleccionados'** (NO este botón)\n\n"
        error_msg += "**O sube archivos localmente:** Arrastra archivos al campo '📂 Documentos Empresariales' arriba."
        yield error_msg
        return
    
    audit_logger.log(
        event_type="enterprise_api",
        action="process_enterprise_documents",
        resource="documents",
        user_id="user",
        metadata={"file_count": len(files), "auto_detect": auto_detect}
    )
    
    try:
        # Parsear reglas si se proporcionan
        rules = []
        if rules_json and rules_json.strip():
            try:
                rules = json.loads(rules_json)
            except:
                rules = []
        
        # Crear Enterprise API con el provider seleccionado
        temp_enterprise_api = EnterpriseAPIMode(config, provider=provider)
        
        # Procesar con Enterprise API usando streaming
        for chunk in temp_enterprise_api.process_enterprise_documents_streaming(
            files=files,
            auto_detect=auto_detect,
            rules=rules
        ):
            accumulated_output += chunk
            yield accumulated_output
        
    except Exception as e:
        error_msg = f"Error en modo Enterprise API: {str(e)}"
        audit_logger.log(
            event_type="error",
            action="enterprise_api",
            resource="documents",
            result="error",
            metadata={"error": str(e)}
        )
        accumulated_output += f"\n❌ **Error**: {error_msg}\n"
        yield accumulated_output


def run_stargate_pdf_mode_streaming(
    files,
    auto_detect: bool = True,
    rules_json: str = "",
    provider: str = "openai",
    pipeline_type: str = "general",
):
    """Ejecuta modo Stargate PDF (clon de Enterprise API) con streaming de resultados (generador)."""
    accumulated_output = ""
    
    if not files:
        error_msg = "❌ No hay archivos subidos.\n\nArrastra tus PDFs al campo de archivos de Stargate PDF."
        yield error_msg
        return
    
    audit_logger.log(
        event_type="stargate_pdf",
        action="process_stargate_documents",
        resource="documents",
        user_id="user",
        metadata={"file_count": len(files), "auto_detect": auto_detect}
    )
    
    try:
        # Parsear reglas si se proporcionan
        rules = []
        if rules_json and rules_json.strip():
            try:
                rules = json.loads(rules_json)
            except Exception:
                rules = []
        
        # Crear instancia temporal de StargatePDF con el provider seleccionado
        temp_stargate = StargatePDFMode(config, provider=provider)
        # Anotar el tipo de pipeline de negocio seleccionado desde la UI
        temp_stargate.pipeline_type = pipeline_type
        
        # Ejecutar el pipeline Stargate (no streaming interno, devolvemos todo el informe de una vez)
        report_markdown = temp_stargate.process_stargate_pipeline(
            files=files,
            auto_detect=auto_detect,
            rules=rules,
        )
        accumulated_output += report_markdown
        yield accumulated_output
    
    except Exception as e:
        error_msg = f"Error en modo Stargate PDF: {str(e)}"


# ========== ADVERTISING TOP MANAGER - Helper Functions ==========

def create_advertising_campaign_ui(
    campaign_name: str,
    daily_budget: float,
    objective: str,
    platforms: str,
    auto_publish: bool,
    image_files,
    video_files,
    landing_page_url: str = "",
    target_audience: str = ""
):
    """
    Helper function para crear campaña desde UI de Gradio.
    Wrapper alrededor de create_campaign_from_ui del módulo gradio_ui.
    """
    if not advertising_top_manager_mode:
        return "❌ Error: Advertising Top Manager no está inicializado. Verifica las credenciales.", {}
    
    try:
        from docchat.advertising_top_manager.gradio_ui import create_campaign_from_ui
        
        # Convertir image_files y video_files a lista si es necesario
        image_list = image_files if isinstance(image_files, list) else ([image_files] if image_files else [])
        video_list = video_files if isinstance(video_files, list) else ([video_files] if video_files else [])
        
        return create_campaign_from_ui(
            campaign_name=campaign_name,
            daily_budget=daily_budget,
            objective=objective,
            platforms=platforms,
            auto_publish=auto_publish,
            image_files=image_list,
            video_files=video_list,
            landing_page_url=landing_page_url if landing_page_url else None,
            target_audience=target_audience if target_audience else None,
            mode_instance=advertising_top_manager_mode
        )
        except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"❌ Error en create_advertising_campaign_ui: {e}")
        print(error_details)
        return f"❌ Error creando campaña: {str(e)}", {}

# =========================
# GRADIO UI ENTRYPOINT
# =========================

