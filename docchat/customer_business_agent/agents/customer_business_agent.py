from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Dict, Any, Optional, List

from langchain_core.language_models import BaseLanguageModel
from langchain_core.messages import SystemMessage, HumanMessage

from ...commerce.product_catalog import ProductSearchResult
from ...config import AppConfig
from ..state.customer_session import CustomerSessionManager, CustomerSessionState, SentimentLabel
from ..sentiment.sentiment_analyzer import SentimentAnalyzer
from ..tools.catalog_tool import CatalogTool
from ..tools.cart_tool import CartTool
from ..tools.payment_tool import PaymentTool
from ..tools.order_tool import OrderTool
from ..tools.support_tool import SupportTool
from ..config.chatbot_config_manager import ChatbotConfigManager


@dataclass
class CustomerBusinessAgentConfig:
    brand_name: str = "Your Brand"
    language: str = "es"
    # Personalización del chatbot (opcional)
    tone: str = "friendly"  # friendly, professional, casual, formal, enthusiastic
    personality: str = ""  # Descripción libre de la personalidad
    custom_instructions: str = ""  # Instrucciones personalizadas adicionales


class CustomerBusinessAgent:
    """Agente orquestador de Customer Business Agent.

    Combina ventas (catálogo, carrito, pagos) + soporte (pedidos, tickets)
    en un solo flujo conversacional.
    """

    def __init__(
        self,
        llm: BaseLanguageModel,
        session_manager: CustomerSessionManager,
        sentiment_analyzer: SentimentAnalyzer,
        catalog_tool: CatalogTool,
        cart_tool: CartTool,
        payment_tool: PaymentTool,
        order_tool: OrderTool,
        support_tool: SupportTool,
        config: CustomerBusinessAgentConfig | None = None,
        fallback_llm: Optional[BaseLanguageModel] = None,
        app_config: Optional[AppConfig] = None,
    ) -> None:
        self.llm = llm
        self._fallback_llm = fallback_llm  # LLM de respaldo si el principal falla
        self.session_manager = session_manager
        self.sentiment_analyzer = sentiment_analyzer
        self.catalog_tool = catalog_tool
        self.cart_tool = cart_tool
        self.payment_tool = payment_tool
        self.order_tool = order_tool
        self.support_tool = support_tool
        self.config = config or CustomerBusinessAgentConfig()
        self.app_config = app_config
        
        # Cargar configuraciones del chatbot desde JSON (o .env como fallback)
        self.chatbot_config_manager = ChatbotConfigManager()
        self.chatbot_config = self.chatbot_config_manager.load()
        
        # Inicializar RAG si está habilitado
        self.rag_retriever = None
        if self.chatbot_config.rag_enabled:
            self._initialize_rag()
        
        # Traductor multilingüe (si está habilitado)
        self.translator = None
        if self.chatbot_config.multilingual_enabled and app_config:
            try:
                from ...i18n.translator import MultiLanguageTranslator
                self.translator = MultiLanguageTranslator(app_config)
            except Exception as e:
                print(f"⚠️ No se pudo inicializar traductor multilingüe: {e}")
        
        # Integraciones en tiempo real (Shopify/WooCommerce) - Nivel Meta
        self.shopify_integration = None
        self.woocommerce_integration = None
        self._initialize_ecommerce_integrations()
        
        # Sistemas de Inteligencia Avanzada (Nivel Dios Alien) 🚀
        from pathlib import Path
        memory_storage_dir = Path(app_config.memory_dir if app_config else "memory") / "customer_business_agent" / "conversation_memory"
        
        # 1. Memoria Conversacional Profunda
        from ..memory.conversation_memory import ConversationMemory
        self.conversation_memory = ConversationMemory(storage_dir=memory_storage_dir)
        
        # 2. Análisis de Comportamiento Avanzado
        from ..intelligence.behavior_analyzer import BehaviorAnalyzer
        self.behavior_analyzer = BehaviorAnalyzer()
        
        # 3. Sugerencias Proactivas
        from ..intelligence.proactive_suggestions import ProactiveSuggestionsEngine
        self.proactive_engine = ProactiveSuggestionsEngine()
        
        # 4. Técnicas de Cierre Avanzadas
        from ..intelligence.closing_techniques import ClosingTechniquesManager
        self.closing_manager = ClosingTechniquesManager()
        
        # 5. Servicio de Carritos Abandonados
        from ..services.abandoned_cart_service import AbandonedCartService
        cart_storage_dir = Path(app_config.memory_dir if app_config else "memory") / "customer_business_agent" / "abandoned_carts"
        self.abandoned_cart_service = AbandonedCartService(storage_dir=cart_storage_dir)
        
        # 6. Tracking de Conversiones (PRIORIDAD 1) 📊
        from ..analytics.conversion_tracker import ConversionTracker
        analytics_storage_dir = Path(app_config.memory_dir if app_config else "memory") / "customer_business_agent" / "analytics"
        self.conversion_tracker = ConversionTracker(
            storage_dir=analytics_storage_dir,
            enable_ga=False,  # Configurar en .env si se necesita
            enable_meta_pixel=False  # Configurar en .env si se necesita
        )
        
        # 7. Recomendador de Productos (PRIORIDAD 2) 🎯
        from ..intelligence.product_recommender import ProductRecommender
        self.product_recommender = ProductRecommender()
        
        # 8. Servicio de Suscripciones (Inspirado en Sierra.ai) 📅
        from ..services.subscription_service import SubscriptionService
        subscription_storage_dir = Path(app_config.memory_dir if app_config else "memory") / "customer_business_agent" / "subscriptions"
        self.subscription_service = SubscriptionService(storage_dir=subscription_storage_dir)
        
        # 9. Mejora de Lenguaje Natural (Inspirado en Sierra.ai) 🧠
        from ..intelligence.natural_language_enhancer import NaturalLanguageEnhancer
        self.nlp_enhancer = NaturalLanguageEnhancer()
        
        # 10. Integración con CRMs Reales (TOP LEVEL) 🏢
        self.crm_integration = None
        self._initialize_crm_integration()
        
        # 11. Integración con OMS Reales (TOP LEVEL) 📦
        self.oms_integration = None
        self._initialize_oms_integration()
    
    def _invoke_llm_with_fallback(self, messages):
        """Invoca el LLM con fallback automático si falla la autenticación.
        
        Optimizado para velocidad y confiabilidad.
        """
        import time
        start_time = time.time()
        
        try:
            result = self.llm.invoke(messages)
            elapsed = time.time() - start_time
            if elapsed > 2.0:  # Si tarda más de 2 segundos, advertir
                print(f"⚠️ LLM tardó {elapsed:.2f}s (objetivo: <0.5s)")
            return result
        except Exception as llm_error:
            error_msg = str(llm_error)
            # Si es error de autenticación (401) y hay fallback, usarlo
            if ("401" in error_msg or "AuthenticationError" in error_msg or "Invalid API Key" in error_msg) and self._fallback_llm:
                print(f"⚠️ Error de autenticación con LLM principal: {error_msg}")
                print("⚠️ Usando LLM de fallback (OpenAI)...")
                try:
                    result = self._fallback_llm.invoke(messages)
                    # Cambiar el LLM principal al fallback para próximas llamadas
                    self.llm = self._fallback_llm
                    print("✅ Cambiado a LLM de fallback exitosamente")
                    return result
                except Exception as fallback_error:
                    print(f"❌ Error también con LLM de fallback: {fallback_error}")
                    raise ValueError(f"Error con ambos LLMs: Principal={error_msg}, Fallback={fallback_error}")
            else:
                # Si no hay fallback o es otro tipo de error, lanzar excepción
                raise

    def _initialize_rag(self):
        """Inicializa el sistema RAG - carga chunks guardados (embeddings se generan al consultar - lazy loading)."""
        try:
            from pathlib import Path
            import pickle
            
            storage_dir = Path("docchat/customer_business_agent/rag_storage")
            chunks_path = storage_dir / "document_chunks.pkl"
            metadata_path = storage_dir / "retriever_metadata.pkl"
            
            # Guardar referencia a chunks_path para lazy loading
            self._rag_chunks_path = chunks_path
            self._rag_metadata_path = metadata_path
            self._rag_chunks = None  # Se cargan cuando se necesiten
            self._rag_retriever_built = False
            
            if chunks_path.exists() and metadata_path.exists():
                try:
                    # Cargar metadata (no cargamos chunks aún - lazy loading)
                    with open(metadata_path, "rb") as f:
                        retriever_metadata = pickle.load(f)
                    
                    chunks_count = retriever_metadata.get("chunks_count", 0)
                    embeddings_generated = retriever_metadata.get("embeddings_generated", False)
                    
                    print(f"✅ RAG inicializado - {chunks_count} chunks disponibles (embeddings: {'generados' if embeddings_generated else 'lazy loading'})")
                    print(f"   Los embeddings se generarán automáticamente cuando se consulte")
                except Exception as e:
                    print(f"⚠️ Error cargando metadata RAG: {e}")
                    import traceback
                    traceback.print_exc()
            else:
                print("⚠️ No hay documentos RAG procesados. Procesa documentos primero en el tab RAG.")
                print(f"   Buscando en: {chunks_path}")
        except Exception as e:
            print(f"⚠️ Error inicializando RAG: {e}")
            import traceback
            traceback.print_exc()
    
    def _initialize_ecommerce_integrations(self):
        """Inicializa las integraciones de e-commerce (Shopify/WooCommerce)."""
        try:
            # Cargar configuración del chatbot para obtener credenciales
            chatbot_config = self.chatbot_config_manager.load()
            
            # Inicializar Shopify si está configurado
            if chatbot_config.ecommerce_enabled and chatbot_config.shopify_api_key:
                try:
                    from ..integrations.shopify_integration import ShopifyIntegration
                    shop_url = chatbot_config.shopify_shop_name or ""
                    if shop_url:
                        self.shopify_integration = ShopifyIntegration(
                            shop_url=shop_url,
                            access_token=chatbot_config.shopify_api_key  # En Shopify, el API key es el access_token
                        )
                        print("✅ Shopify integration inicializada")
                except Exception as e:
                    print(f"⚠️ Error inicializando Shopify: {e}")
            
            # Inicializar WooCommerce si está configurado
            if chatbot_config.ecommerce_enabled and chatbot_config.woocommerce_url and chatbot_config.woocommerce_consumer_key:
                try:
                    from ..integrations.woocommerce_integration import WooCommerceIntegration
                    self.woocommerce_integration = WooCommerceIntegration(
                        store_url=chatbot_config.woocommerce_url,
                        consumer_key=chatbot_config.woocommerce_consumer_key,
                        consumer_secret=chatbot_config.woocommerce_consumer_secret or ""
                    )
                    print("✅ WooCommerce integration inicializada")
                except Exception as e:
                    print(f"⚠️ Error inicializando WooCommerce: {e}")
    
    def _initialize_crm_integration(self):
        """Inicializa integración con CRM real."""
        try:
            chatbot_config = self.chatbot_config_manager.load()
            
            if chatbot_config.crm_webhook_url and chatbot_config.crm_type:
                from ..integrations.crm_integration import CRMIntegration, CRMType
                
                crm_type_map = {
                    "hubspot": CRMType.HUBSPOT,
                    "salesforce": CRMType.SALESFORCE,
                    "pipedrive": CRMType.PIPEDRIVE,
                    "other": CRMType.GENERIC,
                }
                
                crm_type = crm_type_map.get(chatbot_config.crm_type.lower(), CRMType.GENERIC)
                
                # Obtener credenciales desde .env o config
                import os
                crm_api_key = os.getenv("CRM_API_KEY") or chatbot_config.crm_webhook_url.split("?")[0] if "?" in chatbot_config.crm_webhook_url else None
                crm_access_token = os.getenv("CRM_ACCESS_TOKEN")
                
                if crm_type == CRMType.HUBSPOT:
                    self.crm_integration = CRMIntegration(
                        crm_type=crm_type,
                        api_key=crm_api_key or os.getenv("HUBSPOT_API_KEY"),
                    )
                    print("✅ CRM Integration (HubSpot) inicializada")
                elif crm_type == CRMType.SALESFORCE:
                    self.crm_integration = CRMIntegration(
                        crm_type=crm_type,
                        api_url=os.getenv("SALESFORCE_INSTANCE_URL"),
                        access_token=crm_access_token or os.getenv("SALESFORCE_ACCESS_TOKEN"),
                    )
                    print("✅ CRM Integration (Salesforce) inicializada")
                elif crm_type == CRMType.GENERIC:
                    # API genérica - usar webhook URL como base
                    self.crm_integration = CRMIntegration(
                        crm_type=crm_type,
                        api_url=chatbot_config.crm_webhook_url.rsplit("/", 1)[0] if "/" in chatbot_config.crm_webhook_url else chatbot_config.crm_webhook_url,
                        api_key=crm_api_key,
                        headers={"Authorization": f"Bearer {crm_api_key}"} if crm_api_key else {},
                    )
                    print("✅ CRM Integration (Generic) inicializada")
        except Exception as e:
            print(f"⚠️ Error inicializando CRM Integration: {e}")
            import traceback
            traceback.print_exc()
    
    def _initialize_oms_integration(self):
        """Inicializa integración con OMS real."""
        try:
            chatbot_config = self.chatbot_config_manager.load()
            
            # Si hay Shopify o WooCommerce, usar como OMS
            if chatbot_config.ecommerce_enabled:
                from ..integrations.oms_integration import OMSIntegration, OMSType
                
                if chatbot_config.shopify_api_key and chatbot_config.shopify_shop_name:
                    self.oms_integration = OMSIntegration(
                        oms_type=OMSType.SHOPIFY,
                        api_key=chatbot_config.shopify_api_key,
                        shop_name=chatbot_config.shopify_shop_name,
                    )
                    print("✅ OMS Integration (Shopify) inicializada")
                elif chatbot_config.woocommerce_url and chatbot_config.woocommerce_consumer_key:
                    self.oms_integration = OMSIntegration(
                        oms_type=OMSType.WOOCOMMERCE,
                        api_key=chatbot_config.woocommerce_consumer_key,
                        api_secret=chatbot_config.woocommerce_consumer_secret,
                        api_url=chatbot_config.woocommerce_url,
                    )
                    print("✅ OMS Integration (WooCommerce) inicializada")
                
                # También soportar OMS personalizado desde .env
                import os
                oms_api_url = os.getenv("OMS_API_URL")
                oms_api_key = os.getenv("OMS_API_KEY")
                
                if oms_api_url and oms_api_key and not self.oms_integration:
                    self.oms_integration = OMSIntegration(
                        oms_type=OMSType.CUSTOM,
                        api_url=oms_api_url,
                        api_key=oms_api_key,
                        headers={"Authorization": f"Bearer {oms_api_key}"},
                    )
                    print("✅ OMS Integration (Custom) inicializada")
        except Exception as e:
            print(f"⚠️ Error inicializando OMS Integration: {e}")
            import traceback
            traceback.print_exc()
            
        except Exception as e:
            print(f"⚠️ Error inicializando integraciones de e-commerce: {e}")
            # Continuar sin integraciones de e-commerce
            self.shopify_integration = None
            self.woocommerce_integration = None
    
    def _query_ecommerce_catalog_realtime(self, search_query: str, limit: int = 5) -> str:
        """
        Consulta productos en tiempo real desde Shopify/WooCommerce.
        
        Args:
            search_query: Término de búsqueda
            limit: Número máximo de productos a retornar
            
        Returns:
            String formateado con información de productos para el prompt
        """
        if not self.chatbot_config or not self.chatbot_config.ecommerce_enabled:
            return ""
        
        results = []
        
        # Consultar Shopify
        if self.shopify_integration:
            try:
                shopify_products = self.shopify_integration.search_products(search_query, limit=limit)
                if shopify_products and isinstance(shopify_products, list):
                    for product in shopify_products:
                        shop_url = getattr(self.shopify_integration, 'shop_url', '')
                        product_handle = getattr(product, 'handle', '')
                        product_url = f"https://{shop_url}/products/{product_handle}" if shop_url and product_handle else ""
                        results.append({
                            "title": getattr(product, 'title', 'N/A'),
                            "price": getattr(product, 'price', 0),
                            "currency": getattr(product, 'currency', '$'),
                            "availability": getattr(product, 'in_stock', False),
                            "url": product_url
                        })
            except Exception as e:
                print(f"⚠️ Error consultando Shopify: {e}")
        
        # Consultar WooCommerce
        if self.woocommerce_integration:
            try:
                wc_products = self.woocommerce_integration.search_products(search_query, limit=limit)
                if wc_products:
                    # WooCommerce puede devolver lista o objeto con .products
                    if isinstance(wc_products, list):
                        products_list = wc_products
                    elif hasattr(wc_products, 'products'):
                        products_list = wc_products.products
                    else:
                        products_list = []
                    
                    for product in products_list:
                        # WooCommerce usa 'name' en lugar de 'title', y 'permalink' en lugar de 'url'
                        title = getattr(product, 'name', None) or getattr(product, 'title', 'N/A')
                        if isinstance(product, dict):
                            title = product.get('name') or product.get('title', 'N/A')
                        
                        url = getattr(product, 'permalink', None) or getattr(product, 'url', '')
                        if isinstance(product, dict):
                            url = product.get('permalink') or product.get('url', '')
                        
                        results.append({
                            "title": title if title else 'N/A',
                            "price": getattr(product, 'price', 0) if hasattr(product, 'price') else (product.get('price', 0) if isinstance(product, dict) else 0),
                            "currency": getattr(product, 'currency', '$') if hasattr(product, 'currency') else (product.get('currency', '$') if isinstance(product, dict) else '$'),
                            "availability": getattr(product, 'in_stock', False) if hasattr(product, 'in_stock') else (product.get('in_stock', False) if isinstance(product, dict) else False),
                            "url": url
                        })
            except Exception as e:
                print(f"⚠️ Error consultando WooCommerce: {e}")
        
        # Formatear resultados para el prompt
        if not results:
            return ""
        
        formatted = "**PRODUCTOS DISPONIBLES (CONSULTA EN TIEMPO REAL):**\n"
        for i, product in enumerate(results[:limit], 1):
            availability_text = "✅ Disponible" if product.get("availability") else "❌ Agotado"
            formatted += f"{i}. **{product.get('title', 'N/A')}** - {product.get('currency', '$')}{product.get('price', 'N/A')} - {availability_text}\n"
            if product.get("url"):
                formatted += f"   URL: {product['url']}\n"
        
        return formatted
    
    def _build_rag_retriever_lazy(self):
        """Construye el retriever RAG cuando se necesita (lazy loading) - genera embeddings si es necesario."""
        if self._rag_retriever_built and self.rag_retriever:
            return self.rag_retriever
        
        try:
            from pathlib import Path
            import pickle
            from langchain_chroma import Chroma
            from langchain_openai import OpenAIEmbeddings
            from langchain_community.retrievers import BM25Retriever
            from langchain.retrievers import EnsembleRetriever
            from ...retriever_builder import HybridRetriever
            
            # Cargar chunks guardados
            if not self._rag_chunks_path or not self._rag_chunks_path.exists():
                print("⚠️ No hay chunks RAG disponibles")
                return None
            
            if self._rag_chunks is None:
                with open(self._rag_chunks_path, "rb") as f:
                    self._rag_chunks = pickle.load(f)
                print(f"📂 Cargados {len(self._rag_chunks)} chunks para RAG")
            
            # Obtener API key para embeddings (OpenAI para embeddings, Groq para LLM)
            api_key = None
            if self.app_config:
                api_key = getattr(self.app_config, "openai_api_key", None)
            if not api_key:
                import os
                api_key = os.getenv("OPENAI_API_KEY", "")
            
            if not api_key:
                print("⚠️ OpenAI API key no configurada para embeddings")
                return None
            
            # Cargar metadata
            metadata_path = self._rag_metadata_path or Path("docchat/customer_business_agent/rag_storage/retriever_metadata.pkl")
            persist_dir = None
            
            if metadata_path.exists():
                with open(metadata_path, "rb") as f:
                    retriever_metadata = pickle.load(f)
                
                persist_dir = retriever_metadata.get("persist_dir")
                embeddings_generated = retriever_metadata.get("embeddings_generated", False)
                
                if persist_dir:
                    persist_dir = Path(persist_dir)
            
            # Crear embeddings
            embeddings = OpenAIEmbeddings(
                model="text-embedding-3-small",
                openai_api_key=api_key
            )
            
            # Si ya hay embeddings persistidos, cargarlos
            if persist_dir and persist_dir.exists() and embeddings_generated:
                print(f"📂 Cargando embeddings desde: {persist_dir}")
                vector_store = Chroma(
                    persist_directory=str(persist_dir),
                    embedding_function=embeddings
                )
                vector_retriever = vector_store.as_retriever(search_kwargs={"k": 5})
            else:
                # Generar embeddings ahora (lazy loading)
                print(f"🔄 Generando embeddings para {len(self._rag_chunks)} chunks (esto puede tardar unos minutos)...")
                from ...config import AppConfig
                from ... import load_config
                config = self.app_config or load_config()
                persist_dir = Path(config.persist_dir) / "customer_business_agent_rag"
                
                vector_store = Chroma.from_documents(
                    documents=self._rag_chunks,
                    embedding=embeddings,
                    persist_directory=str(persist_dir)
                )
                vector_retriever = vector_store.as_retriever(search_kwargs={"k": 5})
                
                # Actualizar metadata
                if metadata_path.exists():
                    with open(metadata_path, "rb") as f:
                        retriever_metadata = pickle.load(f)
                else:
                    retriever_metadata = {}
                
                retriever_metadata["persist_dir"] = str(persist_dir)
                retriever_metadata["embeddings_generated"] = True
                
                with open(metadata_path, "wb") as f:
                    pickle.dump(retriever_metadata, f)
                
                print(f"✅ Embeddings generados y guardados en: {persist_dir}")
            
            # Crear BM25 retriever
            bm25_retriever = BM25Retriever.from_documents(self._rag_chunks)
            bm25_retriever.k = 5
            
            # Crear Hybrid Retriever
            self.rag_retriever = HybridRetriever(
                bm25_retriever=bm25_retriever,
                vector_retriever=vector_retriever,
                weights=(0.4, 0.6)  # 40% BM25, 60% Vector
            )
            
            self._rag_retriever_built = True
            print(f"✅ Hybrid Retriever construido (BM25 + Vector Search)")
            
            return self.rag_retriever
            
        except Exception as e:
            print(f"⚠️ Error construyendo retriever RAG: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _detect_language(self, text: str) -> str:
        """Detecta el idioma del texto."""
        if self.translator:
            return self.translator.detect_language(text)
        # Detección básica si no hay traductor
        text_lower = text.lower()
        if any(word in text_lower for word in ["the", "is", "are", "and", "or", "what", "how"]):
            return "en"
        elif any(word in text_lower for word in ["o", "a", "é", "de", "da", "você", "não"]):
            return "pt"
        elif any(word in text_lower for word in ["le", "la", "les", "de", "et", "vous"]):
            return "fr"
        elif any(word in text_lower for word in ["der", "die", "das", "und", "oder"]):
            return "de"
        return self.chatbot_config.default_language
    
    def _check_objections(self, user_message: str) -> Optional[str]:
        """Verifica si el mensaje contiene objeciones y retorna respuesta personalizada."""
        if not self.chatbot_config.objection_responses:
            return None
        
        user_msg_lower = user_message.lower()
        for objection_key, response in self.chatbot_config.objection_responses.items():
            if objection_key.lower() in user_msg_lower:
                return response
        return None
    
    def _query_rag(self, query: str, top_k: int = 5) -> str:
        """Consulta el índice RAG usando sistema multi-agente completo (Relevance Checker + Research + Verification)."""
        if not self.chatbot_config.rag_enabled:
            return ""
        
        # Construir retriever lazy (genera embeddings si es necesario)
        retriever = self._build_rag_retriever_lazy()
        if not retriever:
            return ""
        
        try:
            # Usar sistema multi-agente completo (como Meta/DocChat)
            from ...workflow import AgentWorkflow
            
            # Crear workflow con Groq (provider="groq")
            workflow = AgentWorkflow(
                config=self.app_config,
                provider="groq"  # SIEMPRE usar Groq para Customer Business Agent
            )
            
            # Obtener todos los documentos para el workflow
            all_documents = self._rag_chunks if self._rag_chunks else []
            
            # Ejecutar workflow completo (Relevance Checker + Research + Verification)
            result = workflow.run(
                question=query,
                retriever=retriever,
                all_documents=all_documents,
                conversational_mode=False
            )
            
            # Obtener respuesta del workflow
            answer = result.get("answer") or result.get("draft_answer", "")
            
            if not answer:
                return ""
            
            # Retornar respuesta procesada por el sistema multi-agente
            return answer
            
        except Exception as e:
            print(f"⚠️ Error consultando RAG con sistema multi-agente: {e}")
            import traceback
            traceback.print_exc()
            
            # Fallback: usar método simple si falla el workflow
            try:
                retrieved_docs = retriever.invoke(query)
                if not retrieved_docs:
                    return ""
                
                retrieved_docs = retrieved_docs[:top_k]
                context_parts = []
                for i, doc in enumerate(retrieved_docs, 1):
                    content = doc.page_content if hasattr(doc, 'page_content') else str(doc)
                    source = doc.metadata.get('source', 'Documento') if hasattr(doc, 'metadata') else 'Documento'
                    context_parts.append(f"[Documento {i} - {source}]\n{content}")
                
                return "\n\n---\n\n".join(context_parts)
            except Exception as fallback_error:
                print(f"⚠️ Error también en fallback: {fallback_error}")
                return ""
    
    def _check_handoff_keywords(self, user_message: str) -> bool:
        """Verifica si el mensaje contiene palabras clave para handoff."""
        if not self.chatbot_config.handoff_keywords:
            return False
        
        user_msg_lower = user_message.lower()
        for keyword in self.chatbot_config.handoff_keywords:
            if keyword.lower() in user_msg_lower:
                return True
        return False
    
    def _calculate_lead_score(self, session: CustomerSessionState) -> int:
        """Calcula el score del lead basado en respuestas a preguntas de calificación."""
        if not self.chatbot_config.lead_scoring_enabled:
            return 0
        
        score = 0
        
        # Si hay respuestas guardadas, calcular score
        if hasattr(session, 'lead_responses') and session.lead_responses:
            for response_data in session.lead_responses:
                question_weight = response_data.get("weight", 1)
                answer_value = response_data.get("value", 0)  # 0-5 o similar
                score += question_weight * answer_value
        else:
            # Score básico basado en actividad/interacción
            # Más mensajes = mayor interés
            message_count = len(session.last_messages) if hasattr(session, 'last_messages') else 0
            if message_count > 5:
                score += 2
            if message_count > 10:
                score += 2
            # Carrito con productos = interés de compra
            if session.cart and isinstance(session.cart, dict):
                items = session.cart.get("items", [])
                if len(items) > 0:
                    score += 3
            # Sentimiento positivo = buen lead
            if session.sentiment == SentimentLabel.POSITIVE:
                score += 2
        
        return score
    
    def _build_handoff_summary(self, session: CustomerSessionState, user_message: str, reason: str) -> str:
        """
        Construye un resumen completo de la conversación para el humano.
        
        Args:
            session: Sesión del cliente
            user_message: Último mensaje del usuario
            reason: Razón del handoff
            
        Returns:
            Resumen completo de la conversación
        """
        from datetime import datetime
        
        summary_parts = []
        
        # Información básica
        summary_parts.append(f"**HANDOFF AUTOMÁTICO - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}**")
        summary_parts.append(f"**Razón:** {reason}")
        summary_parts.append(f"**Session ID:** {session.session_id}")
        
        # Perfil del cliente
        if session.profile:
            profile_info = []
            if hasattr(session.profile, 'display_name') and session.profile.display_name:
                profile_info.append(f"Nombre: {session.profile.display_name}")
            if hasattr(session.profile, 'email') and session.profile.email:
                profile_info.append(f"Email: {session.profile.email}")
            if hasattr(session.profile, 'user_id') and session.profile.user_id:
                profile_info.append(f"User ID: {session.profile.user_id}")
            if profile_info:
                summary_parts.append(f"**Cliente:** {', '.join(profile_info)}")
        
        # Sentimiento y frustración
        summary_parts.append(f"**Sentimiento:** {session.sentiment.value}")
        summary_parts.append(f"**Frustración:** {session.frustration_score:.2f}/10")
        
        # Historial de conversación (últimos 10 mensajes)
        if session.last_messages:
            summary_parts.append(f"\n**Historial de Conversación (últimos {min(10, len(session.last_messages))} mensajes):**")
            for msg in session.last_messages[-10:]:
                role = msg.get("role", "unknown")
                content = msg.get("content", "")[:200]  # Limitar longitud
                summary_parts.append(f"- {role.upper()}: {content}")
        
        # Carrito actual
        if session.cart and session.cart.get("items"):
            items = session.cart["items"]
            total = sum(item.get("price", 0) * item.get("quantity", 1) for item in items if isinstance(item, dict))
            summary_parts.append(f"\n**Carrito Actual:**")
            summary_parts.append(f"- Items: {len(items)}")
            summary_parts.append(f"- Total: ${total:.2f}")
        
        # Órdenes recientes
        if session.recent_orders:
            summary_parts.append(f"\n**Órdenes Recientes:**")
            for order in session.recent_orders[-3:]:  # Últimas 3 órdenes
                order_id = order.get("order_id") or order.get("id", "N/A")
                status = order.get("status", "N/A")
                summary_parts.append(f"- Orden {order_id}: {status}")
        
        # Último mensaje del usuario
        summary_parts.append(f"\n**Último Mensaje del Usuario:**")
        summary_parts.append(f"{user_message}")
        
        # Recomendaciones para el humano
        summary_parts.append(f"\n**Recomendaciones para el Agente Humano:**")
        if session.frustration_score >= 0.8:
            summary_parts.append("- Cliente muy frustrado. Priorizar empatía y resolución rápida.")
        if session.cart and session.cart.get("items"):
            summary_parts.append("- Cliente tiene items en carrito. Oportunidad de cerrar venta.")
        if session.recent_orders:
            summary_parts.append("- Cliente tiene historial de compras. Verificar satisfacción previa.")
        
        return "\n".join(summary_parts)
    
    def _trigger_human_handoff(self, session: CustomerSessionState, reason: str, user_message: str, conversation_summary: Optional[str] = None):
        """Activa handoff humano y envía alerta con contexto completo."""
        session.needs_handoff = True
        
        # Usar resumen completo si está disponible
        description = conversation_summary if conversation_summary else f"Razón: {reason}\nMensaje del usuario: {user_message[:500]}"
        
        ticket = self.support_tool.create_ticket(
            session_id=session.session_id,
            subject=f"Handoff Automático: {reason}",
            description=description,
            priority="high",
        )
        session.open_tickets.append(ticket)
        
        # TODO: Enviar notificación a contacto configurado (WhatsApp, email, Slack, etc.)
        print(f"🚨 HANDOFF ACTIVADO: {reason} - Session: {session.session_id}")
        print(f"📋 Resumen de conversación preparado para el agente humano")
        
        return ticket
    
    def _send_lead_to_crm(self, session: CustomerSessionState, lead_score: int, lead_label: str, booking_url: str):
        """Envía datos del lead al CRM vía webhook."""
        if not REQUESTS_AVAILABLE:
            print("⚠️ requests no disponible. Instala con: pip install requests")
            return
        
        crm_type = self.chatbot_config.crm_type.lower()
        webhook_url = self.chatbot_config.crm_webhook_url
        
        # Preparar datos del lead
        lead_data = {
            "session_id": session.session_id,
            "lead_score": lead_score,
            "lead_label": lead_label,
            "booking_url": booking_url,
            "timestamp": session.created_at.isoformat() if hasattr(session, 'created_at') else None,
            "message_count": len(session.messages) if hasattr(session, 'messages') else 0,
        }
        
        # Agregar información adicional si está disponible
        if hasattr(session, 'cart') and session.cart:
            lead_data["has_cart"] = True
            lead_data["cart_items_count"] = len(session.cart.get('items', []))
        
        # Formatear según tipo de CRM
        if crm_type == "hubspot":
            payload = {
                "properties": [
                    {"property": "lead_score", "value": lead_score},
                    {"property": "lead_label", "value": lead_label},
                    {"property": "booking_url", "value": booking_url},
                ]
            }
        elif crm_type == "salesforce":
            payload = {
                "Lead_Score__c": lead_score,
                "Lead_Label__c": lead_label,
                "Booking_URL__c": booking_url,
            }
        elif crm_type == "pipedrive":
            payload = {
                "lead_score": lead_score,
                "lead_label": lead_label,
                "booking_url": booking_url,
            }
        else:
            payload = lead_data
        
        # Enviar webhook
        try:
            response = requests.post(
                webhook_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=5
            )
            response.raise_for_status()
            print(f"✅ Lead enviado a CRM ({crm_type}): {response.status_code}")
        except Exception as e:
            print(f"⚠️ Error enviando lead a CRM ({crm_type}): {e}")
    
    def handle_message(
        self,
        session: CustomerSessionState,
        user_message: str,
        image_data: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Procesa un mensaje del usuario con pipeline completo de ventas.
        
        Pipeline de Ventas:
        1. Detección de idioma (multilingüismo)
        2. Detección de objeciones (respuestas personalizadas)
        3. Motor RAG activo (consultar documentos si no tiene respuesta)
        4. Sistema de Lead Scoring (calificar lead)
        5. Detección de Handoff Humano (palabras clave + frustración)
        6. Generación de respuesta final
        
        Args:
            session: Estado de sesión del cliente
            user_message: Mensaje de texto del usuario
            image_data: Datos de imagen en base64 (opcional)
        """
        # === VALIDACIÓN DE INPUTS (PRODUCCIÓN) ===
        if not user_message or not isinstance(user_message, str):
            return {
                "text": "Lo siento, no pude entender tu mensaje. ¿Podrías intentar de nuevo?",
                "error": True,
                "session": session,
            }
        
        # Limpiar y validar mensaje
        user_message = user_message.strip()
        if len(user_message) == 0:
            return {
                "text": "Por favor, escribe un mensaje para que pueda ayudarte.",
                "error": False,
                "session": session,
            }
        
        # Limitar longitud para evitar abusos
        if len(user_message) > 5000:
            user_message = user_message[:5000]
            print(f"⚠️ Mensaje truncado a 5000 caracteres")
        
        # Recargar configuración para obtener cambios recientes
        try:
            self.chatbot_config = self.chatbot_config_manager.load()
        except Exception as e:
            print(f"⚠️ Error cargando configuración: {e}")
            # Usar configuración por defecto si falla
            self.chatbot_config = self.chatbot_config_manager.load_from_env()
        
        session.add_message("user", user_message)
        
        # === PASO 0: Mejora de Lenguaje Natural (Inspirado en Sierra.ai) 🧠 ===
        # Corregir typos y mejorar comprensión
        enhanced_query = self.nlp_enhancer.enhance_product_search_query(user_message)
        corrected_message = enhanced_query.get("corrected_query", user_message)
        has_typos = enhanced_query.get("has_typos", False)
        
        if has_typos:
            print(f"✅ Typos corregidos: '{user_message}' → '{corrected_message}'")
        
        # Extraer información de entrega si está presente
        delivery_info = self.nlp_enhancer.extract_delivery_info(corrected_message)
        
        # Usar mensaje corregido para el resto del procesamiento
        processed_message = corrected_message
        
        # === PASO 1: Detección de Idioma (Multilingüismo Dinámico) ===
        detected_language = self.chatbot_config.default_language
        if self.chatbot_config.multilingual_enabled:
            detected_language = self._detect_language(processed_message)
        
        # === PASO 2: Detección de Objeciones ===
        objection_response = self._check_objections(user_message)
        if objection_response:
            # Si encontramos una objeción, usar respuesta personalizada directamente
            final_text = objection_response
            if self.translator and detected_language != self.chatbot_config.default_language:
                final_text = self.translator.translate(final_text, detected_language)
            
            session.add_message("assistant", final_text)
            return {
                "text": final_text,
                "intent": "objection_handling",
                "language": detected_language,
                "session": session,
            }
        
        # === PASO 3: Análisis de Sentimiento y Handoff ===
        sentiment_result = self.sentiment_analyzer.analyze(user_message, session)
        self.sentiment_analyzer.update_session_sentiment(session, sentiment_result)
        
        # Verificar handoff por palabras clave
        handoff_by_keywords = self._check_handoff_keywords(user_message)
        handoff_by_sentiment = session.frustration_score >= self.chatbot_config.handoff_sentiment_threshold
        
        if handoff_by_keywords or handoff_by_sentiment:
            reason = "Palabras clave de handoff" if handoff_by_keywords else f"Frustración alta ({session.frustration_score:.2f})"
            
            # === HANDOFF MEJORADO: Contexto Completo para el Humano ===
            # Construir resumen completo de la conversación para el humano
            conversation_summary = self._build_handoff_summary(session, user_message, reason)
            
            ticket = self._trigger_human_handoff(session, reason, user_message, conversation_summary)
            
            # Sincronizar con CRM si está configurado (marcar como necesita atención)
            if self.crm_integration:
                try:
                    from ..integrations.crm_integration import CRMContact
                    customer_email = session.profile.email if session.profile and hasattr(session.profile, 'email') else None
                    if customer_email:
                        contact = CRMContact(
                            email=customer_email,
                            name=session.profile.display_name if session.profile and hasattr(session.profile, 'display_name') else None,
                            custom_fields={
                                "needs_human_attention": True,
                                "handoff_reason": reason,
                                "frustration_score": session.frustration_score,
                                "last_message": user_message[:200],
                            }
                        )
                        self.crm_integration.create_or_update_contact(contact)
                        print(f"✅ Cliente marcado en CRM como necesita atención humana")
                except Exception as e:
                    print(f"⚠️ Error sincronizando handoff con CRM: {e}")
            
            handoff_message = "Entiendo que necesitas hablar con una persona de nuestro equipo. Te voy a conectar con un agente humano que podrá ayudarte mejor. Un momento, por favor."
            if self.translator and detected_language != self.chatbot_config.default_language:
                handoff_message = self.translator.translate(handoff_message, detected_language)
            
            return {
                "text": handoff_message,
                "handoff": True,
                "ticket": ticket,
                "conversation_summary": conversation_summary,
                "language": detected_language,
                "session": session,
            }
        
        # Si ya necesita handoff humano (desde sesión previa), enfocarnos en eso
        if session.needs_handoff:
            ticket = self.support_tool.create_ticket(
                session_id=session.session_id,
                subject="Escalamiento automático por frustración",
                description=f"Conversación requiere humano. Último mensaje: {user_message[:500]}",
                priority="high",
            )
            session.open_tickets.append(ticket)
            return {
                "text": "Voy a pasarte con una persona de nuestro equipo para ayudarte mejor.",
                "handoff": True,
                "ticket": ticket,
                "language": detected_language,
                "session": session,
            }
        
        # Guardar mensaje del usuario en PostgreSQL si está habilitado
        if hasattr(self.session_manager, 'save_message'):
            try:
                self.session_manager.save_message(
                    session_id=session.session_id,
                    role="user",
                    content=user_message,
                    metadata={"language": detected_language}
                )
            except:
                pass
        
        # === PASO 4: Análisis de Comportamiento Avanzado (Nivel Dios Alien) 🚀 ===
        conversation_history = list(self.conversation_memory._conversation_histories.get(session.session_id, []))
        conversation_context_obj = self.conversation_memory.get_conversation_context(session.session_id)
        conversation_context_dict = {
            "preferences": conversation_context_obj.preferences if conversation_context_obj else {},
            "needs_mentioned": conversation_context_obj.needs_mentioned if conversation_context_obj else [],
            "objections_raised": conversation_context_obj.objections_raised if conversation_context_obj else [],
            "products_viewed": conversation_context_obj.products_viewed if conversation_context_obj else [],
            "products_interested": conversation_context_obj.products_interested if conversation_context_obj else [],
        }
        
        products_viewed = conversation_context_dict.get("products_viewed", [])
        time_in_session = None  # TODO: Calcular tiempo real de sesión
        
        behavior_analysis = self.behavior_analyzer.analyze(
            message=user_message,
            conversation_history=conversation_history,
            user_profile={"is_returning": False},  # TODO: Detectar clientes recurrentes
            time_in_session=time_in_session,
            products_viewed=products_viewed
        )
        
        print(f"🧠 Análisis de Comportamiento: {behavior_analysis.segment.value} | Señal: {behavior_analysis.purchase_signal.value} | Urgencia: {behavior_analysis.urgency_level.value}")
        
        # Generar sugerencias proactivas
        cart_items = []  # TODO: Obtener items del carrito real
        time_since_last_message = None  # TODO: Calcular tiempo real
        
        proactive_suggestions = self.proactive_engine.generate_suggestions(
            behavior_analysis=behavior_analysis,
            conversation_context=conversation_context_dict,
            products_viewed=products_viewed,
            time_since_last_message=time_since_last_message,
            cart_items=cart_items
        )
        
        # === PASO 5: Procesar imagen si viene ===
        image_analysis = None
        if image_data or "[Image]" in user_message:
            if "[Image]" in user_message:
                try:
                    image_base64 = user_message.split("[Image]")[1].strip()
                    image_analysis = self._analyze_image(image_base64)
                except:
                    pass
            if image_data:
                image_analysis = self._analyze_image(image_data)

        # === PASO 5: Consultar Catálogo E-commerce en Tiempo Real (Nivel Meta) ===
        ecommerce_context = ""
        
        # Detectar si la pregunta es sobre productos
        product_keywords = ["producto", "precio", "stock", "disponible", "comprar", "catalogo", 
                           "product", "price", "stock", "available", "buy", "catalog",
                           "cuánto cuesta", "tienen", "venden", "ofrecen"]
        is_product_query = any(keyword in user_message.lower() for keyword in product_keywords)
        
        if is_product_query:
            # Extraer término de búsqueda del mensaje
            # Intentar extraer nombre de producto del mensaje
            search_query = user_message  # Por ahora usar todo el mensaje
            
            # Consultar catálogo en tiempo real
            ecommerce_context = self._query_ecommerce_catalog_realtime(search_query, limit=5)
            if ecommerce_context:
                print(f"✅ Productos encontrados en tiempo real para: {search_query}")
        
        # === PASO 6: Motor RAG Activo ===
        rag_context = ""
        if self.chatbot_config.rag_enabled:
            rag_context = self._query_rag(user_message, top_k=5)
        
        # === PASO 6: Lead Scoring ===
        lead_score = self._calculate_lead_score(session)
        lead_label = "Lead Caliente" if lead_score >= self.chatbot_config.lead_hot_threshold else "Lead Frío"
        
        # Almacenar score en sesión
        if not hasattr(session, 'lead_score'):
            session.lead_score = 0
        session.lead_score = lead_score
        session.lead_label = lead_label
        
        # SINCRONIZACIÓN: BehaviorAnalyzer → ClosingTechniquesManager (NIVEL DIOS) 🚀
        # El BehaviorAnalyzer ahora envía un TRIGGER directo cuando detecta que es momento de cerrar
        closing_strategy = None
        should_activate_closing = behavior_analysis.should_activate_closing
        
        if should_activate_closing:
            print(f"🎯 [TRIGGER DE CIERRE] Activado: {behavior_analysis.closing_trigger_reason}")
            # Seleccionar técnica de cierre apropiada
            closing_strategy = self.closing_manager.select_technique(
                behavior_analysis=behavior_analysis,
                conversation_context=conversation_context_dict,
                stock_available=None  # TODO: Obtener stock real del producto de interés
            )
            
            if closing_strategy:
                print(f"🎯 [Cierre Proactivo ACTIVADO] Técnica: {closing_strategy.technique.value} | Confianza: {closing_strategy.confidence:.0%}")
                system_prompt += f"**🚀 CIERRE PROACTIVO ACTIVADO (TRIGGER AUTOMÁTICO):**\n"
                system_prompt += f"- **Razón del trigger:** {behavior_analysis.closing_trigger_reason}\n"
                system_prompt += f"- **Técnica seleccionada:** {closing_strategy.technique.value}\n"
                system_prompt += f"- **Mensaje de cierre OBLIGATORIO:** {closing_strategy.message_template}\n"
                system_prompt += f"- **Justificación:** {closing_strategy.rationale}\n"
                system_prompt += f"- **INSTRUCCIÓN CRÍTICA:** DEBES INTEGRAR este mensaje de cierre DIRECTAMENTE en tu respuesta. "
                system_prompt += f"NO solo lo sugieras - ÚSALO. El cliente está listo para comprar AHORA. "
                system_prompt += f"Este es el momento de cerrar la venta, no de seguir explicando.\n\n"
        
        # Paso 1: Construir perfil contextual del usuario (CSALES approach)
        user_profile_context = self._build_user_profile_context(session, user_message)
        
        # Obtener user_id para memoria
        user_id = session.customer_id if hasattr(session, 'customer_id') else session.session_id
        
        # Paso 1.5: Añadir Memoria Conversacional Profunda (Nivel Dios Alien) 🚀
        full_conversation_context = self.conversation_memory.get_full_context_for_prompt(
            session_id=session.session_id,
            user_id=user_id,
            include_history=True,
            include_long_term=True
        )
        
        # Paso 2: pedir al LLM que entienda intención de alto nivel (con perfil contextual)
        
        # Mapeo de tonos a descripciones
        tone_descriptions = {
            "friendly": "Amigable y cercano, como un amigo que quiere ayudar",
            "professional": "Profesional pero accesible, con expertise técnico",
            "casual": "Relajado y conversacional, como si fuera un compañero",
            "formal": "Formal y respetuoso, usando un lenguaje más estructurado",
            "enthusiastic": "Entusiasta y energético, apasionado por los productos"
        }
        
        tone_desc = tone_descriptions.get(self.config.tone, tone_descriptions["friendly"])
        
        # Construir prompt base
        system_prompt = (
            f"Eres el agente oficial de {self.config.brand_name}. "
            "Sabes vender productos, responder dudas, dar estado de pedidos y gestionar devoluciones. "
            "Debes decidir QUÉ acción tomar (ventas vs soporte) y QUÉ tools usar (catálogo, carrito, pago, pedidos, tickets).\n\n"
        )
        
        # Agregar personalización de tono
        if self.config.tone:
            system_prompt += f"**Tono de Comunicación:** {tone_desc}\n\n"
        
        # Agregar personalidad personalizada si está definida
        if self.config.personality:
            system_prompt += f"**Personalidad:** {self.config.personality}\n\n"
        
        # Agregar instrucciones personalizadas si están definidas
        if self.config.custom_instructions:
            system_prompt += f"**Instrucciones Personalizadas:**\n{self.config.custom_instructions}\n\n"
        
        # Continuar con el prompt base
        system_prompt += (
            f"**Perfil del Cliente:**\n{user_profile_context}\n\n"
        )
        
        # CUSTOMER DNA (NIVEL DIOS) - "Ficha Médica" del Comprador 🧬
        conversation_context_obj = self.conversation_memory.get_accumulated_context(session.session_id)
        customer_dna = conversation_context_obj.customer_dna if conversation_context_obj else None
        
        if customer_dna:
            system_prompt += f"**🧬 CUSTOMER DNA (Perfil del Cliente - NIVEL DIOS):**\n"
            system_prompt += f"- **Resumen:** {customer_dna.get('summary', 'N/A')}\n"
            system_prompt += f"- **Sensibilidad:** {customer_dna.get('sensibility', 'unknown')} (precio vs calidad)\n"
            system_prompt += f"- **Estilo de comunicación:** {customer_dna.get('communication_style', 'unknown')}\n"
            system_prompt += f"- **Velocidad de decisión:** {customer_dna.get('decision_speed', 'unknown')}\n"
            if customer_dna.get('recurring_objection'):
                system_prompt += f"- **Objeción recurrente:** {customer_dna['recurring_objection']}\n"
            system_prompt += f"- **Incentivo preferido:** {customer_dna.get('preferred_incentive', 'value')}\n"
            if customer_dna.get('personality_traits'):
                system_prompt += f"- **Rasgos de personalidad:** {', '.join(customer_dna['personality_traits'])}\n"
            system_prompt += "\n"
            system_prompt += "**USO DEL CUSTOMER DNA:**\n"
            system_prompt += "- Adapta tu tono al estilo de comunicación del cliente\n"
            system_prompt += f"- Si prefiere {customer_dna.get('preferred_incentive')}, usa ese tipo de incentivo\n"
            if customer_dna.get('recurring_objection'):
                system_prompt += f"- Aborda proactivamente la objeción recurrente: '{customer_dna['recurring_objection']}'\n"
            system_prompt += "- Haz referencia al resumen para personalizar tu respuesta\n\n"
        
        # Añadir Memoria Conversacional Profunda (solo si NO hay customer_dna o para contexto adicional)
        if full_conversation_context and not customer_dna:
            system_prompt += f"**MEMORIA CONVERSACIONAL PROFUNDA:**\n{full_conversation_context}\n"
            system_prompt += "**IMPORTANTE:** Usa esta memoria para hacer referencias como 'Como mencionaste antes...', 'Recuerdo que te interesaba...', etc.\n\n"
        
        # Añadir Análisis de Comportamiento al prompt
        system_prompt += f"**ANÁLISIS DE COMPORTAMIENTO (INTERNO):**\n"
        system_prompt += f"- Segmento del cliente: {behavior_analysis.segment.value}\n"
        system_prompt += f"- Señal de compra: {behavior_analysis.purchase_signal.value} (Confianza: {behavior_analysis.confidence:.0%})\n"
        system_prompt += f"- Nivel de urgencia: {behavior_analysis.urgency_level.value}\n"
        system_prompt += f"- Riesgo de abandono: {behavior_analysis.risk_of_abandonment:.0%}\n"
        if behavior_analysis.estimated_time_to_purchase:
            system_prompt += f"- Tiempo estimado de compra: {behavior_analysis.estimated_time_to_purchase}\n"
        system_prompt += f"- Acciones sugeridas: {', '.join(behavior_analysis.suggested_actions)}\n\n"
        
        # Si hay sugerencias proactivas de alta prioridad, mencionarlas
        high_priority_suggestions = [s for s in proactive_suggestions if s.priority >= 7]
        if high_priority_suggestions:
            system_prompt += f"**SUGERENCIAS PROACTIVAS (ACCIÓN RECOMENDADA):**\n"
            for suggestion in high_priority_suggestions[:2]:  # Máximo 2
                system_prompt += f"- {suggestion.message}\n"
            system_prompt += "\n"
        
        # Añadir contexto de E-commerce en tiempo real (PRIORIDAD ALTA - Nivel Meta)
        product_recommendations_text = ""
        if ecommerce_context:
            system_prompt += f"**INFORMACIÓN DE PRODUCTOS EN TIEMPO REAL (ACTUALIZADA):**\n{ecommerce_context}\n\n"
            system_prompt += "**IMPORTANTE:** Esta información es EN TIEMPO REAL. Usa estos productos, precios y stock actuales. "
            system_prompt += "Si un producto no está en stock, di que está agotado. Si está en stock, confirma disponibilidad.\n\n"
        
        # Añadir contexto RAG si está disponible
        if rag_context:
            system_prompt += f"**Información de Documentos (RAG):**\n{rag_context}\n\n"
            system_prompt += "**IMPORTANTE:** Usa SOLO la información de los documentos arriba. NO inventes información.\n\n"
            
            # RECOMENDACIONES INTELIGENTES usando RAG (PRIORIDAD 2) 🎯
            try:
                # Obtener productos mencionados en la conversación
                conversation_context_obj = self.conversation_memory.get_accumulated_context(session.session_id)
                products_mentioned = conversation_context_obj.products_interested if conversation_context_obj else []
                
                # Si hay productos mencionados, generar recomendaciones usando RAG
                if products_mentioned and rag_context:
                    # Obtener primer producto mencionado
                    first_product_id = products_mentioned[0] if products_mentioned else None
                    
                    if first_product_id:
                        # Obtener productos disponibles del catálogo/e-commerce
                        available_products = []  # Se obtendrá del contexto de e-commerce o catálogo
                        
                        # Generar recomendaciones
                        recommendations = self.product_recommender.get_all_recommendations(
                            current_product_id=first_product_id,
                            current_product_name=first_product_id,
                            rag_context=rag_context,
                            available_products=available_products,
                            limit=3
                        )
                        
                        if recommendations:
                            product_recommendations_text = self.product_recommender.format_recommendations_for_prompt(recommendations)
            except Exception as e:
                print(f"⚠️ Error generando recomendaciones: {e}")
        
        # Añadir recomendaciones de productos al prompt
        if product_recommendations_text:
            system_prompt += product_recommendations_text
        
        # Añadir información de Lead Scoring
        if self.chatbot_config.lead_scoring_enabled:
            system_prompt += f"**Lead Score:** {lead_score} ({lead_label})\n"
            if lead_label == "Lead Caliente":
                system_prompt += "**PRIORIDAD:** Este es un Lead Caliente. Enfócate en cerrar la venta, ofrecer productos, crear urgencia.\n"
                # Si booking está habilitado, mencionarlo en el prompt
                if self.chatbot_config.booking_enabled:
                    system_prompt += "**AGENDAMIENTO:** Si el cliente muestra interés, puedes mencionar que pueden agendar una cita para una demo personalizada.\n"
            system_prompt += "\n"
        
        # === MEJORAS SIERRA.AI: Instrucciones Específicas ===
        system_prompt += (
            "**🌟 COMPORTAMIENTO INSPIRADO EN SIERRA.AI (Máxima Calidad):**\n\n"
            "**1. Comprensión de Lenguaje Natural Mejorada:**\n"
            "- El usuario puede tener typos (ej: 'delivr' → 'deliver', 'thse' → 'these').\n"
            "- NO te quedes atascado con errores tipográficos. Entiende la intención real.\n"
            "- Si el usuario escribe 'can you delivr tomorrow?', entiende que quiere entrega mañana.\n\n"
            "**2. Recomendaciones Contextuales Inteligentes:**\n"
            "- SIEMPRE ofrece recomendaciones basadas en el contexto de la conversación.\n"
            "- Si el usuario menciona 'dinner party', sugiere productos apropiados para esa ocasión.\n"
            "- Si un producto no está disponible, NO termines con un problema - ofrece una alternativa creativa.\n"
            "- Ejemplo: 'No tenemos ese bouquet para mañana, pero tengo este otro que es perfecto para tu cena.'\n\n"
            "**3. Resolución Creativa de Problemas:**\n"
            "- Si algo no está disponible, NO digas solo 'no está disponible'.\n"
            "- Ofrece alternativas inmediatamente: 'No tenemos X para mañana, pero Y está disponible y es perfecto para tu ocasión.'\n"
            "- Usa el contexto previo: 'Como mencionaste que es para una cena, este bouquet de girasoles sería ideal.'\n\n"
            "**4. Sugerencias Proactivas de Suscripciones:**\n"
            "- Si el cliente ha hecho 2+ pedidos o ha gastado $100+, es buen candidato para suscripción.\n"
            "- Sugiere suscripción de forma natural: 'Noté que eres un amante regular de las flores. ¿Has considerado nuestro servicio de auto-entrega?'\n"
            "- Destaca beneficios: 'Ofrece 15% de descuento en cada entrega y puedes reprogramar hasta 24 horas antes.'\n"
            "- Si el cliente acepta ('bill my card'), confirma la suscripción y menciona la próxima fecha de entrega.\n\n"
            "**5. Actualización de Órdenes en Tiempo Real:**\n"
            "- Si el cliente quiere cambiar la dirección de entrega, hazlo INMEDIATAMENTE.\n"
            "- NO redirijas a otra página o digas 'llama a soporte'.\n"
            "- Pide confirmación clara: 'Para confirmar, quieres que entreguemos tu pedido del 1 de septiembre a Judy Bloom en 123 Main St, San Francisco, CA, ¿correcto?'\n"
            "- Una vez confirmado, actualiza la orden y confirma: '¡Perfecto! He actualizado la dirección de entrega.'\n\n"
            "**6. Confirmaciones Claras Antes de Cambios:**\n"
            "- Antes de hacer cambios importantes (dirección, fecha, suscripción), SIEMPRE confirma.\n"
            "- Usa formato: 'Para confirmar, quieres [acción], ¿correcto?'\n"
            "- Espera confirmación antes de ejecutar el cambio.\n\n"
            "**7. Información de Entrega e Inventario:**\n"
            "- SIEMPRE verifica disponibilidad y tiempos de entrega antes de recomendar.\n"
            "- Si un producto necesita 2 días de entrega y el cliente quiere mañana, ofrece alternativas inmediatamente.\n"
            "- Menciona detalles específicos: 'Este bouquet necesita 2 días de entrega, pero tengo otros que podemos entregar mañana.'\n\n"
            "**8. Experiencia Conversacional Natural:**\n"
            "- Mantén el contexto de la conversación. Si el usuario mencionó algo antes, refiérete a eso.\n"
            "- Ejemplo: 'Como mencionaste que es para una cena, este bouquet sería perfecto.'\n"
            "- Haz la conversación fluida, no robótica.\n"
            "- Responde de forma empática y genuina, como un humano experto.\n\n"
        )
        
        system_prompt += (
            "**🎯 ESTRATEGIA DE VENTAS AVANZADA (Nivel Meta Sales Agent):**\n\n"
            "**1. Descubrimiento Inteligente de Necesidades:**\n"
            "- Haz preguntas estratégicas para entender el contexto real del cliente (presupuesto, timeline, necesidad específica).\n"
            "- NO asumas. Pregunta antes de recomendar. Ejemplo: '¿Para qué ocasión lo necesitas?' o '¿Cuál es tu presupuesto aproximado?'\n"
            "- Escucha activamente: si el cliente menciona algo, profundiza en eso.\n\n"
            "**2. Persuasión Estratégica y Cierre Avanzado:**\n"
            "- Usa técnicas de cierre suave: '¿Te parece bien si te muestro 3 opciones que encajan perfecto con lo que buscas?'\n"
            "- Crea urgencia cuando sea apropiado: 'Solo quedan 2 unidades en tu talla' o 'Esta oferta termina mañana'.\n"
            "- Resuelve objeciones proactivamente: si detectas dudas sobre precio, explica el valor, no solo el costo.\n"
            "- Usa prueba social: 'Este producto es muy popular entre clientes como tú'.\n\n"
            "**3. Cross-Selling y Up-Selling Inteligente:**\n"
            "- Si el usuario pregunta por un producto, NO solo muestres ese producto. Sugiere complementos lógicos.\n"
            "- Ejemplo: Si pregunta por zapatillas, sugiere calcetines, plantillas, o productos de cuidado.\n"
            "- Up-selling natural: 'Para un uso intensivo, te recomendaría la versión Pro que dura 3x más'.\n"
            "- **USA LAS RECOMENDACIONES DE PRODUCTOS:** Si hay productos recomendados arriba, menciónalos de forma natural en tu respuesta.\n"
            "- Integra recomendaciones naturalmente: 'Este producto va perfecto con X que también tenemos, ¿te interesa verlo?'\n\n"
            "**4. Personalización Extrema:**\n"
            "- Adapta tu tono al perfil del usuario (más formal para B2B, más entusiasta para lifestyle).\n"
            "- Usa el historial de conversación para personalizar recomendaciones.\n"
            "- Si el cliente mencionó algo antes, refiérete a eso: 'Como mencionaste que buscas algo cómodo...'\n\n"
            "**5. Proactividad y Anticipación:**\n"
            "- Después de resolver una pregunta, pregunta proactivamente: '¿Hay algo más en lo que pueda ayudarte?'\n"
            "- Anticipa necesidades: Si alguien compra un producto, ofrece información sobre garantía, envío, o cuidado.\n"
            "- Si el cliente muestra interés pero no compra, pregunta qué le falta: '¿Hay algo específico que te gustaría saber antes de decidir?'\n\n"
            "**6. Manejo de Objeciones Avanzado:**\n"
            "- Si el cliente dice 'está caro', no solo defiendas el precio. Pregunta: '¿Comparado con qué?' o '¿Cuál es tu presupuesto?'\n"
            "- Si dice 'lo voy a pensar', pregunta: '¿Hay algo específico en lo que pueda ayudarte a decidir?'\n"
            "- Usa técnicas de cierre suave: '¿Te parece bien si te envío un resumen con las opciones que vimos?'\n\n"
            "**7. Experiencia de Conversación Natural:**\n"
            "- Maneja diálogos mixtos: puedes responder preguntas, recomendar, vender y hacer chit-chat en la misma conversación.\n"
            "- Si el usuario envía una imagen, analízala para entender su necesidad (producto, problema, reclamo).\n"
            "- Sé conversacional pero enfocado en resultados.\n"
            "- Evita respuestas genéricas. Sé específico y útil.\n\n"
            "**8. Técnicas de Cierre de Ventas (cuando es Lead Caliente):**\n"
            "- Usa el método de 'asumir la venta': 'Perfecto, ¿qué talla necesitas?' en lugar de '¿Te gustaría comprarlo?'\n"
            "- Crea escasez cuando sea real: 'Solo quedan X unidades'.\n"
            "- Ofrece alternativas: 'Si este no encaja, tengo otras 2 opciones que podrían funcionar mejor'.\n"
            "- Cierra con un siguiente paso claro: '¿Te parece bien si te muestro el carrito para que revises?'\n"
        )
        
        # Añadir instrucciones de idioma si es necesario
        if detected_language != self.chatbot_config.default_language:
            system_prompt += f"- Responde siempre en {detected_language}.\n"
        
        # Construir prompt de análisis de intención
        analysis_prompt = (
            "Analiza el mensaje del usuario y responde en JSON con esta estructura mínima:\n"
            "{\n"
            "  'intent': 'sales' | 'support' | 'order_status' | 'refund' | 'small_talk',\n"
            "  'needs_product_search': true/false,\n"
            "  'product_query': 'texto o vacío',\n"
            "  'needs_cart_update': true/false,\n"
            "  'cart_action': 'add' | 'remove' | 'none',\n"
            "  'product_id': 'opcional',\n"
            "  'quantity': numero,\n"
            "  'needs_payment': true/false,\n"
            "  'order_id': 'opcional si pregunta por un pedido',\n"
            "  'needs_handoff': true/false\n"
            "}\n"
            f"Mensaje: {user_message[:1500]}\n"
        )
        
        # Agregar análisis de imagen al prompt si existe
        if image_analysis:
            import json
            analysis_prompt += f"\n**Análisis de Imagen:** {json.dumps(image_analysis)}\n"

        # Usar helper para invocar LLM con fallback automático
        llm_resp = self._invoke_llm_with_fallback([
            SystemMessage(content=system_prompt),
            HumanMessage(content=analysis_prompt),
        ])
        
        content = getattr(llm_resp, "content", str(llm_resp))

        # Parsing muy defensivo del JSON
        import json, re

        match = re.search(r"\{[\s\S]*\}", content)
        if match:
            try:
                intent_data = json.loads(match.group().replace("'", '"'))
            except Exception:
                intent_data = {"intent": "small_talk"}
        else:
            intent_data = {"intent": "small_talk"}

        intent = intent_data.get("intent", "small_talk")

        # Ejecutar acciones de alto nivel según intención
        tool_results: Dict[str, Any] = {}

        # Búsqueda de productos (con cross-selling inteligente)
        if intent_data.get("needs_product_search"):
            query = intent_data.get("product_query") or user_message
            try:
                search_result = self.catalog_tool.search_products(query=query, limit=5)
                # ProductSearchResult tiene un atributo .products que es la lista
                if isinstance(search_result, ProductSearchResult):
                    products_list = search_result.products if hasattr(search_result, 'products') else []
                elif hasattr(search_result, '__iter__') and not isinstance(search_result, str):
                    # Fallback: si es iterable pero no ProductSearchResult
                    products_list = list(search_result) if not hasattr(search_result, 'products') else search_result.products
                else:
                    products_list = []
                
                # Convertir productos a diccionarios
                tool_results["products"] = []
                for p in products_list:
                    if hasattr(p, '__dict__'):
                        tool_results["products"].append({
                            "id": getattr(p, 'id', str(p)),
                            "title": getattr(p, 'title', str(p)),
                            "description": getattr(p, 'description', ''),
                            "price": getattr(p, 'price', 0),
                            "image_url": getattr(p, 'image_url', ''),
                            "in_stock": getattr(p, 'in_stock', False),
                            "stock": getattr(p, 'stock', 0),
                        })
                
                # Cross-selling: Si hay productos encontrados, buscar complementos
                if products_list and len(products_list) > 0:
                    primary_product = products_list[0]
                    product_id = getattr(primary_product, 'id', None) or getattr(primary_product, 'product_id', None)
                    if product_id:
                        try:
                            related_products = self.catalog_tool.suggest_alternatives(
                                product_id=str(product_id),
                                limit=3
                            )
                            if related_products and isinstance(related_products, list):
                                tool_results["cross_sell_products"] = [
                                    {
                                        "id": getattr(p, 'id', str(p)),
                                        "title": getattr(p, 'title', str(p)),
                                        "price": getattr(p, 'price', 0),
                                    }
                                    for p in related_products
                                ]
                        except Exception as e:
                            print(f"⚠️ Error en cross-selling: {e}")
                            pass  # Si falla, continuar sin cross-selling
            except Exception as e:
                print(f"⚠️ Error buscando productos: {e}")
                import traceback
                traceback.print_exc()
                tool_results["products"] = []

        # Actualización de carrito
        session_id = session.session_id
        if intent_data.get("needs_cart_update"):
            cart_action = intent_data.get("cart_action", "none")
            product_id = intent_data.get("product_id")
            quantity = int(intent_data.get("quantity") or 1)
            if product_id:
                if cart_action == "add":
                    cart = self.cart_tool.add_item(session_id, product_id, quantity)
                    
                    # Tracking de conversión: ADD_TO_CART (PRIORIDAD 1) 📊
                    user_id = session.customer_id if hasattr(session, 'customer_id') else session.session_id
                    product_info = next((p for p in tool_results.get("products", []) if isinstance(p, dict) and str(p.get("id")) == str(product_id)), {})
                    product_name = product_info.get("title") or product_info.get("name") or "Producto"
                    product_price = float(product_info.get("price", 0))
                    
                    self.conversion_tracker.track_add_to_cart(
                        session_id=session_id,
                        user_id=user_id,
                        product_id=str(product_id),
                        product_name=product_name,
                        price=product_price,
                        quantity=quantity
                    )
                elif cart_action == "remove":
                    cart = self.cart_tool.remove_item(session_id, product_id)
                else:
                    cart = self.cart_tool.get_cart(session_id)
            else:
                cart = self.cart_tool.get_cart(session_id)
            tool_results["cart"] = cart.to_dict() if hasattr(cart, "to_dict") else cart.__dict__
            session.cart = tool_results["cart"]

        # Pago
        if intent_data.get("needs_payment"):
            cart = self.cart_tool.get_cart(session_id)
            cart_dict = cart.to_dict() if hasattr(cart, "to_dict") else cart.__dict__
            cart_items = cart_dict.get("items", [])
            cart_value = sum(item.get("price", 0) * item.get("quantity", 1) for item in cart_items if isinstance(item, dict))
            
            # Tracking de conversión: INITIATE_CHECKOUT (PRIORIDAD 1) 📊
            user_id = session.customer_id if hasattr(session, 'customer_id') else session.session_id
            self.conversion_tracker.track_initiate_checkout(
                session_id=session_id,
                user_id=user_id,
                cart_value=cart_value,
                items=cart_items
            )
            
            payment_result = self.payment_tool.create_payment_for_cart(session_id=session_id, cart=cart)
            tool_results["payment"] = payment_result.__dict__
            
            # Crear orden
            order = self.order_tool.create_order(
                session_id=session_id,
                cart_snapshot=tool_results.get("cart") or cart_dict,
                payment_info=tool_results["payment"],
            )
            tool_results["order"] = order
            session.recent_orders.append(order)
            
            # Tracking de conversión: PURCHASE_COMPLETE (PRIORIDAD 1) 📊
            order_id = order.get("order_id", order.get("id", ""))
            self.conversion_tracker.track_purchase_complete(
                session_id=session_id,
                user_id=user_id,
                order_id=str(order_id),
                total=cart_value,
                items=cart_items,
                currency="USD"
            )

        # === MEJORAS SIERRA.AI: Track Order Mejorado ===
        # Detectar si el usuario pregunta por estado de pedido (con mejor comprensión de lenguaje natural)
        track_order_keywords = ["track", "order", "pedido", "delivery", "entrega", "when", "cuando", "status", "estado"]
        is_track_order_query = (
            intent == "order_status" or 
            any(keyword in processed_message.lower() for keyword in track_order_keywords)
        )
        
        if is_track_order_query:
            # Intentar extraer order_id del mensaje o usar el proporcionado
            order_id = intent_data.get("order_id")
            if not order_id:
                # Buscar número de orden en el mensaje
                import re
                order_match = re.search(r'\b(\d{6,})\b', processed_message)
                if order_match:
                    order_id = order_match.group(1)
            
            # Si tenemos order_id, buscar la orden
            if order_id:
                order = self.order_tool.get_order_status(order_id)
                if order:
                    tool_results["order_status"] = order
                    # Agregar tracking number si existe
                    if order.get("tracking_number"):
                        tool_results["tracking_number"] = order.get("tracking_number")
                        tool_results["tracking_carrier"] = order.get("tracking_carrier", "UPS")
            else:
                # Si no hay order_id, el agente debe pedirlo en la respuesta
                tool_results["needs_order_info"] = True
        
        # === MEJORAS SIERRA.AI: Gestión de Suscripciones ===
        subscription_keywords = ["subscription", "suscripcion", "auto-delivery", "auto delivery", "recurring", "recurrente"]
        is_subscription_query = any(keyword in processed_message.lower() for keyword in subscription_keywords)
        
        # Detectar si el usuario es candidato para suscripción (después de una compra o consulta)
        should_suggest_subscription = False
        if len(session.recent_orders) >= 1 or len(tool_results.get("products", [])) > 0:
            # Verificar si es buen candidato
            total_spent = sum(
                order.get("cart", {}).get("total", 0) 
                for order in session.recent_orders 
                if isinstance(order, dict)
            )
            is_candidate = self.subscription_service.is_customer_subscription_candidate(
                customer_id=session.session_id,
                order_history=session.recent_orders,
                total_spent=total_spent
            )
            if is_candidate and not is_subscription_query:
                should_suggest_subscription = True
                tool_results["subscription_suggestion"] = {
                    "should_suggest": True,
                    "discount_percentage": 15.0,
                    "frequency_weeks": 4,
                }
        
        # Procesar creación o actualización de suscripción
        if is_subscription_query or "bill my card" in processed_message.lower() or "bill card" in processed_message.lower():
            # Detectar si quiere crear suscripción
            if "sign up" in processed_message.lower() or "subscribe" in processed_message.lower() or "bill my card" in processed_message.lower():
                # Obtener producto del carrito o última orden
                product_id = None
                product_name = "Producto"
                
                if tool_results.get("products") and len(tool_results["products"]) > 0:
                    product = tool_results["products"][0]
                    product_id = product.get("id")
                    product_name = product.get("title") or product.get("name", "Producto")
                elif session.cart and session.cart.get("items"):
                    item = session.cart["items"][0]
                    product_id = item.get("product_id")
                    product_name = item.get("name", "Producto")
                
                if product_id:
                    subscription = self.subscription_service.create_subscription(
                        customer_id=session.session_id,
                        session_id=session.session_id,
                        product_id=str(product_id),
                        product_name=product_name,
                        frequency_weeks=4,
                        discount_percentage=15.0,
                    )
                    tool_results["subscription"] = {
                        "subscription_id": subscription.subscription_id,
                        "next_delivery_date": subscription.next_delivery_date,
                        "discount_percentage": subscription.discount_percentage,
                    }
        
        # === MEJORAS SIERRA.AI: Actualización de Órdenes con OMS Real ===
        update_order_keywords = ["update", "change", "modify", "actualizar", "cambiar", "send to", "send them to"]
        is_update_order_query = any(keyword in processed_message.lower() for keyword in update_order_keywords)
        
        if is_update_order_query:
            # Detectar si quiere cambiar dirección de entrega
            if "address" in processed_message.lower() or "mom" in processed_message.lower() or "send to" in processed_message.lower():
                # Extraer información de dirección del mensaje
                address_info = self.nlp_enhancer.extract_address_info(processed_message)
                
                # Buscar orden reciente o suscripción
                if tool_results.get("order_status"):
                    order_id = tool_results["order_status"].get("order_id")
                    if order_id:
                        # 1. Intentar actualizar en OMS real primero (si está configurado)
                        updated_order = None
                        if self.oms_integration:
                            try:
                                from ..integrations.oms_integration import OrderUpdate
                                order_update = OrderUpdate(
                                    order_id=order_id,
                                    delivery_address=address_info
                                )
                                updated_order = self.oms_integration.update_order(order_update)
                                if updated_order:
                                    print(f"✅ Orden {order_id} actualizada en OMS real")
                                    tool_results["order_updated"] = True
                                    tool_results["updated_order"] = updated_order
                                    tool_results["updated_in_real_oms"] = True
                            except Exception as e:
                                print(f"⚠️ Error actualizando orden en OMS: {e}")
                        
                        # 2. Si no se pudo actualizar en OMS real, actualizar en sistema local
                        if not updated_order:
                            updated_order = self.order_tool.update_order_delivery_address(
                                order_id=order_id,
                                new_address=address_info
                            )
                            if updated_order:
                                tool_results["order_updated"] = True
                                tool_results["updated_order"] = updated_order
                                tool_results["updated_in_real_oms"] = False
                
                # Si hay suscripción activa, también actualizarla
                customer_subscriptions = self.subscription_service.get_customer_subscriptions(session.session_id)
                if customer_subscriptions:
                    active_sub = next((s for s in customer_subscriptions if s.status.value == "active"), None)
                    if active_sub:
                        updated_sub = self.subscription_service.update_delivery_address(
                            subscription_id=active_sub.subscription_id,
                            new_address=address_info
                        )
                        if updated_sub:
                            tool_results["subscription_updated"] = True
                            tool_results["updated_subscription"] = {
                                "subscription_id": updated_sub.subscription_id,
                                "next_delivery_date": updated_sub.next_delivery_date,
                            }
        
        # === Sincronizar con CRM Real ===
        # Si hay una compra o interacción importante, sincronizar con CRM
        if tool_results.get("order") or tool_results.get("subscription"):
            if self.crm_integration:
                try:
                    from ..integrations.crm_integration import CRMContact, CRMDeal
                    
                    # Obtener información del cliente
                    customer_email = session.profile.email if session.profile and hasattr(session.profile, 'email') else None
                    customer_name = session.profile.display_name if session.profile and hasattr(session.profile, 'display_name') else None
                    
                    if customer_email:
                        # Crear/actualizar contacto en CRM
                        contact = CRMContact(
                            email=customer_email,
                            name=customer_name,
                            custom_fields={
                                "last_interaction": datetime.now().isoformat(),
                                "session_id": session.session_id,
                            }
                        )
                        crm_contact = self.crm_integration.create_or_update_contact(contact)
                        tool_results["crm_contact_synced"] = True
                        tool_results["crm_contact_id"] = crm_contact.get("contact_id")
                        
                        # Si hay una compra, crear deal
                        if tool_results.get("order"):
                            order = tool_results["order"]
                            total = sum(
                                item.get("price", 0) * item.get("quantity", 1)
                                for item in tool_results.get("cart", {}).get("items", [])
                                if isinstance(item, dict)
                            )
                            
                            deal = CRMDeal(
                                name=f"Orden {order.get('order_id', 'Nueva')}",
                                amount=total,
                                contact_email=customer_email,
                                stage="closed-won" if order.get("status") == "completed" else "negotiation",
                            )
                            crm_deal = self.crm_integration.create_deal(deal)
                            tool_results["crm_deal_created"] = True
                            tool_results["crm_deal_id"] = crm_deal.get("deal_id")
                            
                            print(f"✅ Contacto y deal sincronizados con CRM")
                except Exception as e:
                    print(f"⚠️ Error sincronizando con CRM: {e}")
                    import traceback
                    traceback.print_exc()

        # Devoluciones / soporte
        if intent in ("support", "refund"):
            ticket = self.support_tool.create_ticket(
                session_id=session_id,
                subject=f"Soporte: {intent}",
                description=user_message[:1000],
                priority="normal" if intent == "support" else "high",
            )
            session.open_tickets.append(ticket)
            tool_results["ticket"] = ticket

        # Agregar información sobre acciones ejecutadas (Sierra.ai style)
        actions_summary = ""
        if tool_results.get("order_status"):
            order = tool_results["order_status"]
            actions_summary += f"**ORDEN ENCONTRADA:**\n"
            actions_summary += f"- ID: {order.get('order_id')}\n"
            if tool_results.get("tracking_number"):
                actions_summary += f"- Tracking: {tool_results['tracking_number']} ({tool_results.get('tracking_carrier', 'UPS')})\n"
            actions_summary += f"- Estado: {order.get('status')}\n\n"
        
        if tool_results.get("subscription"):
            sub = tool_results["subscription"]
            actions_summary += f"**SUSCRIPCIÓN CREADA:**\n"
            actions_summary += f"- Próxima entrega: {sub['next_delivery_date']}\n"
            actions_summary += f"- Descuento: {sub['discount_percentage']}%\n\n"
        
        if tool_results.get("order_updated"):
            actions_summary += f"**ORDEN ACTUALIZADA:** La dirección de entrega ha sido modificada.\n\n"
        
        if tool_results.get("subscription_updated"):
            sub = tool_results["updated_subscription"]
            actions_summary += f"**SUSCRIPCIÓN ACTUALIZADA:** Próxima entrega: {sub['next_delivery_date']}\n\n"
        
        if tool_results.get("subscription_suggestion", {}).get("should_suggest"):
            actions_summary += f"**SUGERENCIA PROACTIVA:** El cliente es buen candidato para suscripción. Sugiérela de forma natural.\n\n"
        
        # Generar respuesta final amigable (con personalización y persuasión nivel Meta Sales Agent + Sierra.ai)
        summary_prompt = (
            "Genera una respuesta INTELIGENTE, PROACTIVA y PERSUASIVA en español para el cliente.\n\n"
            "**Contexto de herramientas ejecutadas:**\n"
            f"{json.dumps(tool_results, default=str)[:2000]}\n\n"
            f"**Acciones ejecutadas:**\n{actions_summary}\n\n"
            f"**Mensaje original del cliente:** {user_message[:500]}\n"
            f"**Mensaje corregido (sin typos):** {processed_message[:500]}\n\n"
            f"**Perfil del cliente:** {user_profile_context}\n\n"
            "**🌟 COMPORTAMIENTO SIERRA.AI (OBLIGATORIO):**\n\n"
            "**1. Comprensión Natural:** El cliente puede tener typos. Entiende la intención real, no te quedes atascado.\n"
            "**2. Recomendaciones Contextuales:** Ofrece productos basados en el contexto (ej: 'dinner party' → productos para cena).\n"
            "**3. Resolución Creativa:** Si algo no está disponible, NO termines con un problema. Ofrece alternativas inmediatamente.\n"
            "**4. Suscripciones Proactivas:** Si el cliente es candidato, sugiere suscripción de forma natural con beneficios claros.\n"
            "**5. Actualizaciones en Tiempo Real:** Si el cliente quiere cambiar dirección, hazlo INMEDIATAMENTE. NO redirijas a otra página.\n"
            "**6. Confirmaciones Claras:** Antes de cambios importantes, confirma: 'Para confirmar, quieres X, ¿correcto?'\n\n"
            "**🎯 INSTRUCCIONES DE RESPUESTA (Nivel Meta Sales Agent - Super Genio):**\n\n"
            "**1. Responde DIRECTAMENTE y ESPECÍFICAMENTE:**\n"
            "- NO uses saludos genéricos si el usuario ya hizo una pregunta específica.\n"
            "- Si el usuario pregunta por productos, lista los productos encontrados con NOMBRES, PRECIOS y CARACTERÍSTICAS específicas.\n"
            "- NO digas genéricamente 'tenemos productos'. Muestra los productos REALES con detalles concretos.\n"
            "- Si el usuario pregunta 'qué día es hoy', responde con la fecha actual REAL.\n"
            "- Si el usuario pregunta 'qué sabes', explica ESPECÍFICAMENTE qué puedes hacer con ejemplos concretos.\n\n"
            "**2. Personalización Extrema:**\n"
            "- Si hay productos sugeridos, explica POR QUÉ son buenos para este cliente específico basándote en su perfil.\n"
            "- Usa el historial: 'Como mencionaste que buscas algo cómodo...' o 'Basándome en lo que te gustó antes...'\n"
            "- Adapta el tono al perfil del cliente (formal vs casual, técnico vs simple).\n\n"
            "**3. Cross-Selling y Up-Selling Inteligente:**\n"
            "- Si hay productos de cross-selling, preséntalos de forma natural: 'Este producto va perfecto con X que también tenemos'.\n"
            "- Up-selling suave: 'Para un uso más intensivo, te recomendaría la versión Pro que...'\n"
            "- NO seas agresivo. Sé útil y natural.\n\n"
            "**4. Persuasión Estratégica:**\n"
            "- Si el cliente muestra dudas sobre precio, explica el VALOR, no solo el costo: 'Este producto te durará X años, lo que significa que cuesta solo Y por mes'.\n"
            "- Crea urgencia cuando sea real: 'Solo quedan X unidades en tu talla' o 'Esta oferta termina mañana'.\n"
            "- Usa prueba social: 'Este producto es muy popular entre clientes como tú'.\n\n"
            "**5. Proactividad y Cierre:**\n"
            "- Después de resolver la pregunta actual, pregunta proactivamente: '¿Hay algo más en lo que pueda ayudarte?' o '¿Te gustaría ver más opciones?'\n"
            "- Si hay carrito, muestra resumen y anima a completar la compra: 'Tienes X productos en tu carrito. ¿Te parece bien si revisamos el total?'\n"
            "- Si es Lead Caliente, sé más directo: 'Veo que estás muy interesado. ¿Te parece bien si te muestro cómo completar la compra?'\n\n"
            "**6. Manejo de Situaciones Específicas:**\n"
            "- Si NO hay productos encontrados, di claramente que no encontraste productos pero ofrece ayuda alternativa: 'No encontré exactamente eso, pero tengo estas opciones similares que podrían funcionar...'\n"
            "- Si hay productos, incluye detalles relevantes (precio, características, disponibilidad, envío).\n"
            "- Si hay análisis de imagen, úsalo para verificar reclamos o identificar productos.\n\n"
            "**7. Evita Respuestas Genéricas (CRÍTICO):**\n"
            "- NO digas 'Me alegra que hayas iniciado esta conversación' cuando el usuario ya hizo una pregunta específica.\n"
            "- NO uses frases vacías como 'Estoy aquí para ayudarte' sin contexto.\n"
            "- NO repitas información que el cliente ya sabe.\n"
            "- SIEMPRE personaliza basándote en el historial de conversación.\n"
            "- Si el cliente mencionó algo antes, refiérete a eso específicamente.\n"
            "- Cada respuesta debe agregar valor real y ser específica al contexto del cliente.\n"
            "- Ejemplo MALO: 'Tenemos muchos productos que podrían interesarte.'\n"
            "- Ejemplo BUENO: 'Como mencionaste que buscas algo para una cena, este bouquet de girasoles sería perfecto.'\n\n"
            "**8. Técnicas de Cierre Avanzadas (si es Lead Caliente):**\n"
            "- Usa el método de 'asumir la venta': 'Perfecto, ¿qué talla necesitas?' en lugar de '¿Te gustaría comprarlo?'\n"
            "- Ofrece alternativas: 'Si este no encaja, tengo otras 2 opciones que podrían funcionar mejor'.\n"
            "- Cierra con un siguiente paso claro: '¿Te parece bien si te muestro el carrito para que revises?' o '¿Quieres que te ayude a completar la compra?'\n"
        )

        # Usar helper para invocar LLM con fallback automático
        final_resp = self._invoke_llm_with_fallback([
            SystemMessage(content=system_prompt),
            HumanMessage(content=summary_prompt),
        ])
        final_text = getattr(final_resp, "content", str(final_resp))
        
        # === PASO 7: Agendamiento de Citas (Booking/CTA) - PRIORIDAD ALTA 🚨 ===
        booking_cta = ""
        booking_url = None
        if (self.chatbot_config.booking_enabled and 
            lead_label == "Lead Caliente" and 
            (self.chatbot_config.calendly_url or self.chatbot_config.google_calendar_url)):
            
            # Construir mensaje de booking con link
            booking_message = self.chatbot_config.booking_message or "Veo que estás listo para empezar. ¿Te parece bien agendar una demo? Puedes elegir el horario que mejor te convenga."
            
            # Priorizar Calendly si está configurado, sino Google Calendar
            booking_url = self.chatbot_config.calendly_url or self.chatbot_config.google_calendar_url
            booking_cta = f"\n\n📅 **{booking_message}**\n\n🔗 [Agendar Cita Aquí]({booking_url})"
            
            # Enviar datos al CRM si está configurado
            if self.chatbot_config.crm_webhook_url and self.chatbot_config.crm_type:
                try:
                    self._send_lead_to_crm(session, lead_score, lead_label, booking_url)
                except Exception as e:
                    print(f"⚠️ Error enviando lead a CRM: {e}")
        
        # === PASO 8: Traducción Multilingüe ===
        if self.translator and detected_language != self.chatbot_config.default_language:
            try:
                final_text = self.translator.translate(final_text, detected_language)
                if booking_cta:
                    booking_cta = self.translator.translate(booking_cta, detected_language)
            except Exception as e:
                print(f"⚠️ Error traduciendo respuesta: {e}")

        # Agregar CTA de booking a la respuesta final
        final_text_with_booking = final_text + booking_cta
        
        session.add_message("assistant", final_text_with_booking)
        
        # Guardar respuesta en memoria conversacional (Nivel Dios Alien) 🚀
        user_id = session.customer_id if hasattr(session, 'customer_id') else session.session_id
        self.conversation_memory.add_message(
            session_id=session.session_id,
            user_id=user_id,
            role="assistant",
            content=final_text_with_booking,
            metadata={"behavior_analysis": behavior_analysis.segment.value if behavior_analysis else None}
        )
        
        # Guardar mensaje en PostgreSQL si está habilitado (para memoria de largo plazo)
        if hasattr(self.session_manager, 'save_message'):
            try:
                self.session_manager.save_message(
                    session_id=session.session_id,
                    role="assistant",
                    content=final_text_with_booking if booking_cta else final_text,
                    metadata={
                        "intent": intent,
                        "sentiment": session.sentiment.value,
                        "frustration_score": session.frustration_score,
                        "booking_offered": bool(booking_cta),
                        "booking_url": booking_url if booking_cta else None
                    }
                )
            except:
                pass  # Si falla, continuar sin guardar
        
        # Guardar compra si se completó una orden
        if tool_results.get("order") and hasattr(self.session_manager, 'save_purchase'):
            try:
                order = tool_results["order"]
                products = tool_results.get("cart", {}).get("items", []) if isinstance(tool_results.get("cart"), dict) else []
                total = sum(item.get("price", 0) * item.get("quantity", 1) for item in products if isinstance(item, dict))
                
                self.session_manager.save_purchase(
                    session_id=session.session_id,
                    user_id=session.profile.user_id if session.profile else "unknown",
                    order_id=str(order.get("order_id", "")),
                    products=products,
                    total_amount=float(total)
                )
            except:
                pass  # Si falla, continuar sin guardar

        # Incluir información del carrito en la respuesta (para el widget)
        response_data = {
            "text": final_text_with_booking if booking_cta else final_text,
            "intent": intent,
            "tools": tool_results,
            "sentiment": session.sentiment.value,
            "frustration_score": session.frustration_score,
            "needs_handoff": session.needs_handoff,
            "language": detected_language,
            "lead_score": lead_score if self.chatbot_config.lead_scoring_enabled else None,
            "lead_label": lead_label if self.chatbot_config.lead_scoring_enabled else None,
            "booking_offered": bool(booking_cta),
            "booking_url": booking_url if booking_cta else None,
            "session": session,
        }
        
        # Agregar carrito si existe (para actualizar badge en widget)
        if session.cart:
            response_data["cart"] = session.cart.get("items", []) if isinstance(session.cart, dict) else []
        
        # Agregar perfil de usuario si se ha inferido
        if hasattr(session, 'inferred_profile'):
            response_data["user_profile"] = session.inferred_profile
        
        return response_data
    
    def _build_user_profile_context(self, session: CustomerSessionState, user_message: str) -> str:
        """Construye contexto del perfil de usuario (CSALES approach).
        
        Basado en:
        - Historial de conversación
        - Productos vistos/interesados
        - Carrito actual
        - Sentimiento
        - Comportamiento (activo/pasivo)
        - Historial de largo plazo (PostgreSQL) si está disponible
        """
        context_parts = []
        
        # Información básica
        if session.profile:
            if session.profile.display_name:
                context_parts.append(f"Nombre: {session.profile.display_name}")
            if session.profile.language:
                context_parts.append(f"Idioma: {session.profile.language}")
        
        # Historial de largo plazo (PostgreSQL) - Memoria de meses
        if hasattr(self.session_manager, 'get_user_history'):
            try:
                user_history = self.session_manager.get_user_history(
                    user_id=session.profile.user_id if session.profile else "unknown",
                    days=180  # Últimos 6 meses
                )
                
                if user_history.get("total_purchases", 0) > 0:
                    context_parts.append(f"Cliente recurrente: {user_history['total_purchases']} compra(s) en últimos 6 meses")
                    context_parts.append(f"Total gastado: ${user_history.get('total_spent', 0):.2f}")
                    
                    if user_history.get("last_purchase_date"):
                        last_purchase = user_history["last_purchase_date"]
                        if isinstance(last_purchase, str):
                            from datetime import datetime
                            try:
                                last_purchase = datetime.fromisoformat(last_purchase.replace('Z', '+00:00'))
                            except:
                                pass
                        if isinstance(last_purchase, datetime):
                            days_ago = (datetime.utcnow() - last_purchase.replace(tzinfo=None)).days
                            context_parts.append(f"Última compra: hace {days_ago} días")
                
                # Productos comprados anteriormente (para cross-selling)
                if user_history.get("purchases"):
                    previous_products = []
                    for purchase in user_history["purchases"][:5]:  # Últimas 5 compras
                        products = purchase.get("products", [])
                        if isinstance(products, str):
                            import json
                            products = json.loads(products)
                        if isinstance(products, list):
                            for p in products:
                                if isinstance(p, dict):
                                    product_name = p.get("name") or p.get("product_name")
                                    if product_name:
                                        previous_products.append(product_name)
                    
                    if previous_products:
                        context_parts.append(f"Productos comprados anteriormente: {', '.join(set(previous_products)[:3])}")
            except Exception as e:
                # Si falla, continuar sin historial de largo plazo
                pass
        
        # Historial de conversación (sesión actual)
        if session.last_messages:
            recent_count = len(session.last_messages)
            context_parts.append(f"Mensajes en esta sesión: {recent_count}")
            
            # Detectar si es usuario activo o pasivo (CSALES)
            avg_message_length = sum(len(msg.get('content', '')) for msg in session.last_messages) / max(recent_count, 1)
            if avg_message_length > 50:
                context_parts.append("Tipo de usuario: Activo (proporciona detalles)")
            elif avg_message_length < 20:
                context_parts.append("Tipo de usuario: Pasivo (respuestas cortas)")
        
        # Carrito
        if session.cart:
            if isinstance(session.cart, dict):
                items = session.cart.get("items", [])
            else:
                items = getattr(session.cart, "items", [])
            if items:
                context_parts.append(f"Carrito: {len(items)} producto(s)")
                total = sum(item.get('price', 0) * item.get('quantity', 1) for item in items if isinstance(item, dict))
                if total > 0:
                    context_parts.append(f"Presupuesto estimado: ${total:.2f}")
        
        # Sentimiento
        if session.sentiment != SentimentLabel.NEUTRAL:
            context_parts.append(f"Sentimiento: {session.sentiment.value}")
        
        # Pedidos recientes (sesión actual)
        if session.recent_orders:
            context_parts.append(f"Pedidos en esta sesión: {len(session.recent_orders)}")
        
        return " | ".join(context_parts) if context_parts else "Cliente nuevo"
    
    def _analyze_image(self, image_base64: str) -> Optional[Dict[str, Any]]:
        """Analiza imagen usando visión (Mix-ECom approach para after-sales).
        
        Usa GPT-4 Vision para:
        - Verificar reclamos de calidad
        - Identificar productos en imágenes
        - Detectar daños o problemas
        """
        try:
            # Si el LLM soporta visión, usarlo
            if hasattr(self.llm, 'with_structured_output') or 'gpt-4' in str(self.llm).lower():
                from langchain_core.messages import HumanMessage
                from langchain_core.messages.content import ImageContent
                
                # Crear mensaje con imagen
                vision_prompt = (
                    "Analiza esta imagen y responde en JSON:\n"
                    "{\n"
                    "  'contains_product': true/false,\n"
                    "  'product_description': 'descripción del producto si es visible',\n"
                    "  'has_issue': true/false,\n"
                    "  'issue_description': 'descripción del problema si hay',\n"
                    "  'can_verify_claim': true/false\n"
                    "}\n"
                )
                
                # Intentar usar visión si está disponible
                try:
                    # Para GPT-4o con visión
                    # Usar helper para invocar LLM con fallback automático
                    response = self._invoke_llm_with_fallback([
                        SystemMessage(content="Eres un analizador de imágenes para e-commerce. Analiza productos y problemas."),
                        HumanMessage(content=[
                            {"type": "text", "text": vision_prompt},
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}}
                        ])
                    ])
                    
                    import json, re
                    content = getattr(response, "content", str(response))
                    match = re.search(r"\{[\s\S]*\}", content)
                    if match:
                        return json.loads(match.group().replace("'", '"'))
                except:
                    # Si falla, retornar análisis básico
                    return {
                        "contains_product": True,
                        "can_verify_claim": True,
                        "note": "Imagen recibida, análisis visual disponible"
                    }
        except Exception as e:
            # Si falla completamente, retornar None
            return None

















