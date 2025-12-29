"""
Sistema de Ingesta Multi-Fuente para STAR AGENT.

Arquitectura:
Fuentes Datos (Web/IG/FB/Google) → Crawlers/APIs → Normalización → Chunking → Embeddings → Vector DB → RAG → LLM
"""

from __future__ import annotations

import json
import os
import schedule
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum

try:
    from playwright.sync_api import sync_playwright, Browser, Page
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    print("⚠️ Playwright no disponible. Instala con: pip install playwright && playwright install")

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

from bs4 import BeautifulSoup
from langchain_core.documents import Document

from ..rag.advanced_rag_manager import AdvancedRAGManager, IntentType as RAGIntentType


class SourceType(str, Enum):
    """Tipos de fuentes de datos"""
    WEBSITE = "website"
    INSTAGRAM = "instagram"
    FACEBOOK = "facebook"
    GOOGLE_BUSINESS = "google_business"
    CATALOG = "catalog"
    FAQ = "faq"


@dataclass
class IngestedDocument:
    """Documento normalizado después de ingesta"""
    source: SourceType
    source_id: str  # URL, post_id, review_id, etc.
    title: str
    content: str
    category: str  # producto, política, marketing, review, general
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


class MultiSourceIngester:
    """
    Sistema completo de ingesta multi-fuente.
    
    Características:
    - Crawling web con Playwright (JS-heavy sites)
    - APIs oficiales Instagram/Facebook/Google
    - Normalización semántica
    - Clasificación automática
    - Chunking inteligente
    - Actualización automática (scheduler + webhooks)
    """
    
    def __init__(
        self,
        advanced_rag: AdvancedRAGManager,
        base_dir: Optional[Path] = None,
    ):
        """
        Inicializa el sistema de ingesta.
        
        Args:
            advanced_rag: Instancia de AdvancedRAGManager para agregar documentos
            base_dir: Directorio base para almacenar datos
        """
        self.advanced_rag = advanced_rag
        self.base_dir = base_dir or Path("docchat/star_agent/ingestion_data")
        self.base_dir.mkdir(parents=True, exist_ok=True)
        
        # Browser para Playwright
        self.browser: Optional[Browser] = None
        
        # Configuración de APIs
        self.instagram_token: Optional[str] = os.getenv("INSTAGRAM_ACCESS_TOKEN")
        self.instagram_user_id: Optional[str] = os.getenv("INSTAGRAM_USER_ID")
        self.facebook_token: Optional[str] = os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN")
        self.google_api_key: Optional[str] = os.getenv("GOOGLE_API_KEY")
        self.google_place_id: Optional[str] = os.getenv("GOOGLE_PLACE_ID")
        
        # Historial de ingesta (para evitar duplicados)
        self.ingestion_history: Dict[str, datetime] = {}
        self._load_ingestion_history()
        
        # Inicializar Playwright si está disponible
        if PLAYWRIGHT_AVAILABLE:
            self._init_playwright()
    
    def _init_playwright(self):
        """Inicializa Playwright para crawling web"""
        try:
            self.playwright = sync_playwright().start()
            self.browser = self.playwright.chromium.launch(headless=True)
        except Exception as e:
            print(f"⚠️ Error inicializando Playwright: {e}")
            self.browser = None
    
    def _load_ingestion_history(self):
        """Carga historial de ingesta desde archivo"""
        history_file = self.base_dir / "ingestion_history.json"
        if history_file.exists():
            try:
                with open(history_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for key, timestamp_str in data.items():
                        self.ingestion_history[key] = datetime.fromisoformat(timestamp_str)
            except Exception as e:
                print(f"⚠️ Error cargando historial: {e}")
    
    def _save_ingestion_history(self):
        """Guarda historial de ingesta"""
        history_file = self.base_dir / "ingestion_history.json"
        try:
            data = {
                key: timestamp.isoformat()
                for key, timestamp in self.ingestion_history.items()
            }
            with open(history_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"⚠️ Error guardando historial: {e}")
    
    # === EXTRACCIÓN WEBSITE ===
    
    def ingest_website(
        self,
        url: str,
        use_playwright: bool = True,
        extract_schema: bool = True,
    ) -> Optional[IngestedDocument]:
        """
        Extrae contenido de un sitio web.
        
        Args:
            url: URL del sitio web
            use_playwright: Usar Playwright para JS-heavy sites
            extract_schema: Priorizar schema.org, OpenGraph
        """
        # Verificar si ya fue ingerido recientemente
        if url in self.ingestion_history:
            last_ingest = self.ingestion_history[url]
            if (datetime.now() - last_ingest).total_seconds() < 3600:  # 1 hora
                return None
        
        try:
            if use_playwright and self.browser:
                content = self._crawl_with_playwright(url)
            else:
                content = self._crawl_with_requests(url)
            
            if not content:
                return None
            
            # Extraer schema.org y OpenGraph
            metadata = {}
            if extract_schema:
                metadata.update(self._extract_schema_org(content))
                metadata.update(self._extract_opengraph(content))
            
            # Normalizar y clasificar
            doc = self._normalize_document(
                source=SourceType.WEBSITE,
                source_id=url,
                raw_content=content,
                metadata=metadata,
            )
            
            # Actualizar historial
            self.ingestion_history[url] = datetime.now()
            self._save_ingestion_history()
            
            return doc
            
        except Exception as e:
            print(f"⚠️ Error ingiriendo website {url}: {e}")
            return None
    
    def _crawl_with_playwright(self, url: str) -> Optional[str]:
        """Crawling con Playwright para JS-heavy sites"""
        if not self.browser:
            return None
        
        try:
            page = self.browser.new_page()
            page.goto(url, wait_until="networkidle", timeout=30000)
            content = page.content()
            page.close()
            
            # Extraer texto con BeautifulSoup
            soup = BeautifulSoup(content, 'html.parser')
            
            # Remover scripts y styles
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Extraer texto principal
            text = soup.get_text(separator='\n', strip=True)
            return text
            
        except Exception as e:
            print(f"⚠️ Error en Playwright crawl: {e}")
            return None
    
    def _crawl_with_requests(self, url: str) -> Optional[str]:
        """Crawling básico con requests"""
        if not REQUESTS_AVAILABLE:
            return None
        
        try:
            response = requests.get(url, timeout=10, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            for script in soup(["script", "style"]):
                script.decompose()
            
            text = soup.get_text(separator='\n', strip=True)
            return text
            
        except Exception as e:
            print(f"⚠️ Error en requests crawl: {e}")
            return None
    
    def _extract_schema_org(self, html_content: str) -> Dict[str, Any]:
        """Extrae datos de schema.org"""
        metadata = {}
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Buscar JSON-LD
            for script in soup.find_all('script', type='application/ld+json'):
                try:
                    data = json.loads(script.string)
                    if isinstance(data, dict):
                        metadata.update(data)
                except:
                    pass
            
            # Buscar microdata
            for item in soup.find_all(attrs={"itemtype": True}):
                item_type = item.get("itemtype", "")
                if "Product" in item_type:
                    metadata["type"] = "product"
                elif "Organization" in item_type:
                    metadata["type"] = "organization"
        
        except Exception as e:
            print(f"⚠️ Error extrayendo schema.org: {e}")
        
        return metadata
    
    def _extract_opengraph(self, html_content: str) -> Dict[str, Any]:
        """Extrae datos de OpenGraph"""
        metadata = {}
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            for meta in soup.find_all('meta', property=lambda x: x and x.startswith('og:')):
                prop = meta.get('property', '').replace('og:', '')
                content = meta.get('content', '')
                if prop and content:
                    metadata[f"og_{prop}"] = content
        
        except Exception as e:
            print(f"⚠️ Error extrayendo OpenGraph: {e}")
        
        return metadata
    
    # === EXTRACCIÓN INSTAGRAM ===
    
    def ingest_instagram_post(self, post_id: str) -> Optional[IngestedDocument]:
        """Extrae post de Instagram usando Graph API"""
        if not self.instagram_token or not REQUESTS_AVAILABLE:
            return None
        
        try:
            url = f"https://graph.instagram.com/{post_id}"
            params = {
                "fields": "id,caption,media_type,media_url,timestamp,permalink",
                "access_token": self.instagram_token,
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # Normalizar
            doc = self._normalize_document(
                source=SourceType.INSTAGRAM,
                source_id=post_id,
                raw_content=data.get("caption", ""),
                metadata={
                    "post_id": post_id,
                    "media_type": data.get("media_type"),
                    "media_url": data.get("media_url"),
                    "permalink": data.get("permalink"),
                    "timestamp": data.get("timestamp"),
                },
            )
            
            return doc
            
        except Exception as e:
            print(f"⚠️ Error ingiriendo Instagram post {post_id}: {e}")
            return None
    
    def ingest_instagram_posts(self, limit: int = 25) -> List[IngestedDocument]:
        """Ingiere múltiples posts de Instagram"""
        if not self.instagram_user_id or not self.instagram_token:
            return []
        
        try:
            url = f"https://graph.instagram.com/{self.instagram_user_id}/media"
            params = {
                "fields": "id,caption,media_type,media_url,timestamp,permalink",
                "access_token": self.instagram_token,
                "limit": limit,
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            docs = []
            for post in data.get("data", []):
                doc = self.ingest_instagram_post(post["id"])
                if doc:
                    docs.append(doc)
            
            return docs
            
        except Exception as e:
            print(f"⚠️ Error ingiriendo posts de Instagram: {e}")
            return []
    
    # === EXTRACCIÓN FACEBOOK ===
    
    def ingest_facebook_post(self, post_id: str) -> Optional[IngestedDocument]:
        """Extrae post de Facebook usando Graph API"""
        if not self.facebook_token or not REQUESTS_AVAILABLE:
            return None
        
        try:
            url = f"https://graph.facebook.com/v18.0/{post_id}"
            params = {
                "fields": "id,message,created_time,permalink_url",
                "access_token": self.facebook_token,
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            doc = self._normalize_document(
                source=SourceType.FACEBOOK,
                source_id=post_id,
                raw_content=data.get("message", ""),
                metadata={
                    "post_id": post_id,
                    "created_time": data.get("created_time"),
                    "permalink_url": data.get("permalink_url"),
                },
            )
            
            return doc
            
        except Exception as e:
            print(f"⚠️ Error ingiriendo Facebook post {post_id}: {e}")
            return None
    
    # === EXTRACCIÓN GOOGLE BUSINESS ===
    
    def ingest_google_reviews(self, limit: int = 10) -> List[IngestedDocument]:
        """Extrae reviews de Google Business"""
        if not self.google_place_id or not self.google_api_key or not REQUESTS_AVAILABLE:
            return []
        
        try:
            url = "https://maps.googleapis.com/maps/api/place/details/json"
            params = {
                "place_id": self.google_place_id,
                "fields": "reviews,rating",
                "key": self.google_api_key,
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            docs = []
            for review in data.get("result", {}).get("reviews", [])[:limit]:
                doc = self._normalize_document(
                    source=SourceType.GOOGLE_BUSINESS,
                    source_id=review.get("author_name", ""),
                    raw_content=review.get("text", ""),
                    metadata={
                        "rating": review.get("rating"),
                        "author_name": review.get("author_name"),
                        "relative_time_description": review.get("relative_time_description"),
                    },
                )
                docs.append(doc)
            
            return docs
            
        except Exception as e:
            print(f"⚠️ Error ingiriendo Google reviews: {e}")
            return []
    
    # === NORMALIZACIÓN Y CLASIFICACIÓN ===
    
    def _normalize_document(
        self,
        source: SourceType,
        source_id: str,
        raw_content: str,
        metadata: Dict[str, Any],
    ) -> IngestedDocument:
        """
        Normaliza y clasifica documento.
        
        Convierte todo a formato semántico con metadata (source, type, intent).
        """
        # Clasificar categoría automáticamente
        category = self._classify_content(raw_content)
        
        # Extraer título
        title = metadata.get("og_title") or metadata.get("name") or source_id
        
        return IngestedDocument(
            source=source,
            source_id=source_id,
            title=title,
            content=raw_content,
            category=category,
            metadata=metadata,
            timestamp=datetime.now(),
        )
    
    def _classify_content(self, content: str) -> str:
        """Clasifica contenido en categorías (producto, política, marketing, review, general)"""
        content_lower = content.lower()
        
        # Producto
        if any(x in content_lower for x in ["precio", "producto", "disponible", "stock", "comprar"]):
            return "producto"
        
        # Política
        if any(x in content_lower for x in ["envío", "política", "garantía", "devolución", "términos"]):
            return "política"
        
        # Marketing
        if any(x in content_lower for x in ["promoción", "oferta", "descuento", "nuevo", "lanzamiento"]):
            return "marketing"
        
        # Review
        if any(x in content_lower for x in ["opinión", "reseña", "review", "calificación", "experiencia"]):
            return "review"
        
        return "general"
    
    # === CHUNKING Y AGREGACIÓN A RAG ===
    
    def add_to_rag(self, doc: IngestedDocument):
        """Agrega documento normalizado al RAG avanzado"""
        # Convertir a Document de LangChain
        langchain_doc = Document(
            page_content=doc.content,
            metadata={
                "source": doc.source.value,
                "source_id": doc.source_id,
                "title": doc.title,
                "category": doc.category,
                "timestamp": doc.timestamp.isoformat(),
                **doc.metadata,
            }
        )
        
        # Mapear categoría a IntentType
        category_to_intent = {
            "producto": RAGIntentType.PRODUCTOS,
            "política": RAGIntentType.POLITICAS,
            "marketing": RAGIntentType.MARKETING,
            "review": RAGIntentType.REVIEWS,
            "general": RAGIntentType.GENERAL,
        }
        
        intent = category_to_intent.get(doc.category, RAGIntentType.GENERAL)
        
        # Agregar al RAG
        self.advanced_rag.add_documents([langchain_doc], intent=intent)
    
    # === ACTUALIZACIÓN AUTOMÁTICA ===
    
    def setup_scheduler(self, websites: List[str], interval_hours: int = 6):
        """
        Configura scheduler para actualización automática.
        
        Args:
            websites: Lista de URLs a actualizar periódicamente
            interval_hours: Intervalo en horas (default: 6)
        """
        def update_websites():
            print(f"🔄 Actualizando websites (scheduled task)...")
            for url in websites:
                doc = self.ingest_website(url)
                if doc:
                    self.add_to_rag(doc)
                    print(f"✅ Actualizado: {url}")
        
        # Programar actualización cada X horas
        schedule.every(interval_hours).hours.do(update_websites)
        print(f"✅ Scheduler configurado: actualización cada {interval_hours} horas")
    
    def run_scheduler_loop(self):
        """Ejecuta loop del scheduler (debe correr en thread separado)"""
        while True:
            schedule.run_pending()
            time.sleep(60)  # Verificar cada minuto
    
    # === WEBHOOKS PARA IG/FB ===
    
    def handle_webhook_new_post(self, channel: str, post_data: Dict[str, Any]):
        """
        Maneja webhook de nuevo post desde Instagram/Facebook.
        
        Args:
            channel: "instagram" o "facebook"
            post_data: Datos del post del webhook
        """
        try:
            if channel == "instagram":
                post_id = post_data.get("id")
                if post_id:
                    doc = self.ingest_instagram_post(post_id)
                    if doc:
                        self.add_to_rag(doc)
                        print(f"✅ Nuevo post de Instagram ingerido: {post_id}")
            
            elif channel == "facebook":
                post_id = post_data.get("id")
                if post_id:
                    doc = self.ingest_facebook_post(post_id)
                    if doc:
                        self.add_to_rag(doc)
                        print(f"✅ Nuevo post de Facebook ingerido: {post_id}")
        
        except Exception as e:
            print(f"⚠️ Error procesando webhook: {e}")
    
    def __del__(self):
        """Cleanup al destruir instancia"""
        if hasattr(self, 'browser') and self.browser:
            self.browser.close()
        if hasattr(self, 'playwright'):
            self.playwright.stop()

