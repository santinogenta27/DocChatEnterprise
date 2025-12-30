"""
Sistema de Ingesta Multi-Fuente Automática para STAR AGENT.

Implementa según especificaciones:
- Crawlers web (Playwright para JS-heavy sites)
- APIs Instagram/Facebook (Graph API)
- Google Business API
- Normalización semántica + clasificación
- Chunking inteligente
- Embeddings automáticos
- Actualización en Vector DB
- Scheduler cada 6h para web
- Webhooks para nuevos posts IG/FB
"""

from __future__ import annotations

import os
import json
import hashlib
import schedule
import time
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, asdict

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
    print("⚠️ requests no disponible. Instala con: pip install requests")

try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False
    print("⚠️ BeautifulSoup no disponible. Instala con: pip install beautifulsoup4")

from langchain_core.documents import Document

from ..rag.advanced_rag_manager import AdvancedRAGManager, IntentType


@dataclass
class IngestedDocument:
    """Documento normalizado según especificaciones."""
    source: str  # "website", "instagram", "facebook", "google"
    url: Optional[str] = None
    title: Optional[str] = None
    content: str = ""
    category: Optional[str] = None  # "producto", "política", "marketing", "review"
    metadata: Dict[str, Any] = None
    date: Optional[str] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if self.date is None:
            self.date = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte a diccionario."""
        return asdict(self)
    
    def to_langchain_document(self) -> Document:
        """Convierte a Document de LangChain."""
        return Document(
            page_content=self.content,
            metadata={
                "source": self.source,
                "url": self.url or "",
                "title": self.title or "",
                "category": self.category or "general",
                "date": self.date,
                **self.metadata,
            }
        )


class WebCrawler:
    """
    Crawler web usando Playwright según especificaciones.
    
    Características:
    - Maneja JS-heavy sites
    - Prioriza schema.org y OpenGraph
    - Extracción semántica
    """
    
    def __init__(self):
        self.browser: Optional[Browser] = None
        self.playwright = None
        
        if PLAYWRIGHT_AVAILABLE:
            try:
                self.playwright = sync_playwright().start()
                self.browser = self.playwright.chromium.launch(headless=True)
            except Exception as e:
                print(f"⚠️ Error inicializando Playwright: {e}")
    
    def crawl_website(self, url: str, max_pages: int = 10) -> List[IngestedDocument]:
        """
        Crawlea sitio web usando Playwright.
        
        Args:
            url: URL del sitio web
            max_pages: Número máximo de páginas a crawlear
            
        Returns:
            Lista de documentos normalizados
        """
        if not PLAYWRIGHT_AVAILABLE or not self.browser:
            print("⚠️ Playwright no disponible. Retornando lista vacía.")
            return []
        
        documents = []
        visited_urls = set()
        
        try:
            page = self.browser.new_page()
            
            # Crawlear página principal
            docs = self._crawl_page(page, url, visited_urls, max_pages)
            documents.extend(docs)
            
            page.close()
        except Exception as e:
            print(f"⚠️ Error crawleando {url}: {e}")
        
        return documents
    
    def _crawl_page(self, page: Page, url: str, visited: set, max_pages: int, depth: int = 0) -> List[IngestedDocument]:
        """Crawlea una página específica."""
        if url in visited or depth > 3 or len(visited) >= max_pages:
            return []
        
        visited.add(url)
        documents = []
        
        try:
            page.goto(url, wait_until="networkidle", timeout=30000)
            
            # Esperar a que cargue JavaScript
            page.wait_for_timeout(2000)
            
            # Extraer contenido
            content = self._extract_content(page)
            
            # Extraer metadata (schema.org, OpenGraph)
            metadata = self._extract_metadata(page)
            
            # Crear documento normalizado
            doc = IngestedDocument(
                source="website",
                url=url,
                title=metadata.get("title", ""),
                content=content,
                category=self._classify_content(content),
                metadata=metadata,
            )
            documents.append(doc)
            
            # Encontrar enlaces para crawlear más páginas
            if depth < 2:  # Máximo 2 niveles de profundidad
                links = page.query_selector_all("a[href]")
                for link in links[:10]:  # Máximo 10 enlaces por página
                    href = link.get_attribute("href")
                    if href and href.startswith("http") and href not in visited:
                        try:
                            sub_docs = self._crawl_page(page, href, visited, max_pages, depth + 1)
                            documents.extend(sub_docs)
                        except:
                            pass  # Continuar si falla un enlace
            
        except Exception as e:
            print(f"⚠️ Error crawleando página {url}: {e}")
        
        return documents
    
    def _extract_content(self, page: Page) -> str:
        """Extrae contenido semántico de la página."""
        try:
            # Intentar extraer texto principal
            content_parts = []
            
            # Priorizar schema.org structured data
            schema_data = page.evaluate("""
                () => {
                    const scripts = Array.from(document.querySelectorAll('script[type="application/ld+json"]'));
                    return scripts.map(s => s.textContent).join('\\n');
                }
            """)
            if schema_data:
                content_parts.append(schema_data)
            
            # Extraer texto del body
            body_text = page.evaluate("""
                () => {
                    // Remover scripts y styles
                    const scripts = document.querySelectorAll('script, style');
                    scripts.forEach(s => s.remove());
                    
                    // Extraer texto
                    return document.body.innerText;
                }
            """)
            if body_text:
                content_parts.append(body_text)
            
            return "\n\n".join(content_parts)
        except Exception as e:
            print(f"⚠️ Error extrayendo contenido: {e}")
            return ""
    
    def _extract_metadata(self, page: Page) -> Dict[str, Any]:
        """Extrae metadata (schema.org, OpenGraph)."""
        metadata = {}
        
        try:
            # OpenGraph
            og_title = page.query_selector('meta[property="og:title"]')
            if og_title:
                metadata["og_title"] = og_title.get_attribute("content")
            
            og_description = page.query_selector('meta[property="og:description"]')
            if og_description:
                metadata["og_description"] = og_description.get_attribute("content")
            
            # Schema.org
            schema_scripts = page.query_selector_all('script[type="application/ld+json"]')
            for script in schema_scripts:
                try:
                    schema_data = json.loads(script.inner_text())
                    if isinstance(schema_data, dict):
                        metadata.update(schema_data)
                except:
                    pass
            
            # Título de la página
            title = page.title()
            if title:
                metadata["title"] = title
            
        except Exception as e:
            print(f"⚠️ Error extrayendo metadata: {e}")
        
        return metadata
    
    def _classify_content(self, content: str) -> str:
        """Clasifica contenido según especificaciones."""
        content_lower = content.lower()
        
        if any(x in content_lower for x in ["precio", "producto", "comprar", "disponible"]):
            return "producto"
        elif any(x in content_lower for x in ["envío", "política", "garantía", "devolución"]):
            return "política"
        elif any(x in content_lower for x in ["promoción", "oferta", "descuento", "nuevo"]):
            return "marketing"
        elif any(x in content_lower for x in ["opinión", "reseña", "review", "calificación"]):
            return "review"
        else:
            return "general"
    
    def close(self):
        """Cierra el browser."""
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()


class InstagramExtractor:
    """
    Extractor de Instagram usando Graph API según especificaciones.
    
    Extrae:
    - Bio
    - Posts
    - Captions
    - Product tags
    - Reviews
    """
    
    def __init__(self, access_token: Optional[str] = None):
        self.access_token = access_token or os.getenv("INSTAGRAM_ACCESS_TOKEN")
        self.base_url = "https://graph.instagram.com"
    
    def extract_posts(self, user_id: Optional[str] = None, limit: int = 25) -> List[IngestedDocument]:
        """
        Extrae posts de Instagram.
        
        Args:
            user_id: ID de usuario de Instagram (si None, usa el del token)
            limit: Número máximo de posts a extraer
            
        Returns:
            Lista de documentos normalizados
        """
        if not self.access_token:
            print("⚠️ Instagram access token no configurado")
            return []
        
        documents = []
        
        try:
            # Obtener user_id si no se proporciona
            if not user_id:
                user_id = self._get_user_id()
            
            if not user_id:
                return []
            
            # Obtener posts
            url = f"{self.base_url}/{user_id}/media"
            params = {
                "access_token": self.access_token,
                "fields": "id,caption,media_type,permalink,timestamp",
                "limit": limit,
            }
            
            if not REQUESTS_AVAILABLE:
                print("⚠️ requests no disponible")
                return []
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            posts = data.get("data", [])
            
            for post in posts:
                doc = IngestedDocument(
                    source="instagram",
                    url=post.get("permalink", ""),
                    title="Instagram Post",
                    content=post.get("caption", ""),
                    category="marketing",  # Posts de Instagram son marketing
                    metadata={
                        "post_id": post.get("id", ""),
                        "media_type": post.get("media_type", ""),
                        "timestamp": post.get("timestamp", ""),
                    },
                    date=post.get("timestamp", datetime.now().isoformat()),
                )
                documents.append(doc)
                
        except Exception as e:
            print(f"⚠️ Error extrayendo posts de Instagram: {e}")
        
        return documents
    
    def _get_user_id(self) -> Optional[str]:
        """Obtiene el user_id desde el access token."""
        try:
            url = f"{self.base_url}/me"
            params = {"access_token": self.access_token, "fields": "id"}
            
            if not REQUESTS_AVAILABLE:
                return None
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            return data.get("id")
        except:
            return None


class FacebookExtractor:
    """
    Extractor de Facebook usando Graph API según especificaciones.
    
    Extrae:
    - Posts
    - Captions
    - Product tags
    - Reviews
    """
    
    def __init__(self, access_token: Optional[str] = None):
        self.access_token = access_token or os.getenv("FACEBOOK_ACCESS_TOKEN")
        self.base_url = "https://graph.facebook.com/v18.0"
    
    def extract_posts(self, page_id: Optional[str] = None, limit: int = 25) -> List[IngestedDocument]:
        """
        Extrae posts de Facebook.
        
        Args:
            page_id: ID de la página de Facebook
            limit: Número máximo de posts a extraer
            
        Returns:
            Lista de documentos normalizados
        """
        if not self.access_token:
            print("⚠️ Facebook access token no configurado")
            return []
        
        if not page_id:
            page_id = os.getenv("FACEBOOK_PAGE_ID")
        
        if not page_id:
            print("⚠️ Facebook page_id no configurado")
            return []
        
        documents = []
        
        try:
            url = f"{self.base_url}/{page_id}/posts"
            params = {
                "access_token": self.access_token,
                "fields": "id,message,created_time,permalink_url",
                "limit": limit,
            }
            
            if not REQUESTS_AVAILABLE:
                print("⚠️ requests no disponible")
                return []
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            posts = data.get("data", [])
            
            for post in posts:
                doc = IngestedDocument(
                    source="facebook",
                    url=post.get("permalink_url", ""),
                    title="Facebook Post",
                    content=post.get("message", ""),
                    category="marketing",
                    metadata={
                        "post_id": post.get("id", ""),
                        "created_time": post.get("created_time", ""),
                    },
                    date=post.get("created_time", datetime.now().isoformat()),
                )
                documents.append(doc)
                
        except Exception as e:
            print(f"⚠️ Error extrayendo posts de Facebook: {e}")
        
        return documents


class GoogleBusinessExtractor:
    """
    Extractor de Google Business según especificaciones.
    
    Extrae:
    - Reviews
    - Q&A
    - Horarios
    """
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GOOGLE_BUSINESS_API_KEY")
        self.place_id = os.getenv("GOOGLE_PLACE_ID")
    
    def extract_reviews(self) -> List[IngestedDocument]:
        """
        Extrae reviews de Google Business.
        
        Returns:
            Lista de documentos normalizados
        """
        if not self.api_key or not self.place_id:
            print("⚠️ Google Business API key o place_id no configurado")
            return []
        
        documents = []
        
        try:
            # Google Places API
            url = "https://maps.googleapis.com/maps/api/place/details/json"
            params = {
                "place_id": self.place_id,
                "fields": "review,rating",
                "key": self.api_key,
            }
            
            if not REQUESTS_AVAILABLE:
                print("⚠️ requests no disponible")
                return []
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            result = data.get("result", {})
            reviews = result.get("reviews", [])
            
            for review in reviews:
                doc = IngestedDocument(
                    source="google",
                    url=f"https://www.google.com/maps/place/?q=place_id:{self.place_id}",
                    title="Google Review",
                    content=review.get("text", ""),
                    category="review",
                    metadata={
                        "rating": review.get("rating", 0),
                        "author_name": review.get("author_name", ""),
                        "time": review.get("time", ""),
                    },
                    date=datetime.fromtimestamp(review.get("time", 0)).isoformat() if review.get("time") else None,
                )
                documents.append(doc)
                
        except Exception as e:
            print(f"⚠️ Error extrayendo reviews de Google: {e}")
        
        return documents


class MultiSourceIngester:
    """
    Sistema de Ingesta Multi-Fuente Automática según especificaciones.
    
    Arquitectura:
    Fuentes Datos (Web/IG/FB/Google) → Crawlers/APIs → Normalización → 
    Chunking → Embeddings → Vector DB → RAG → LLM
    """
    
    def __init__(
        self,
        advanced_rag: AdvancedRAGManager,
        website_url: Optional[str] = None,
        enable_scheduler: bool = True,
        enable_webhooks: bool = True,
    ):
        """
        Inicializa el sistema de ingesta multi-fuente.
        
        Args:
            advanced_rag: Instancia de AdvancedRAGManager para actualizar índices
            website_url: URL del sitio web a crawlear
            enable_scheduler: Habilitar scheduler automático cada 6h
            enable_webhooks: Habilitar webhooks para nuevos posts
        """
        self.advanced_rag = advanced_rag
        self.website_url = website_url or os.getenv("WEBSITE_URL")
        self.enable_scheduler = enable_scheduler
        self.enable_webhooks = enable_webhooks
        
        # Extractores
        self.web_crawler = WebCrawler() if PLAYWRIGHT_AVAILABLE else None
        self.instagram_extractor = InstagramExtractor()
        self.facebook_extractor = FacebookExtractor()
        self.google_extractor = GoogleBusinessExtractor()
        
        # Cache de documentos procesados (para evitar duplicados)
        self.processed_docs_hash: set = set()
        
        # Scheduler
        self.scheduler_running = False
        
        if enable_scheduler:
            self._setup_scheduler()
    
    def ingest_all_sources(self) -> Dict[str, int]:
        """
        Ingestiona desde todas las fuentes configuradas.
        
        Returns:
            Dict con conteo de documentos por fuente
        """
        counts = {
            "website": 0,
            "instagram": 0,
            "facebook": 0,
            "google": 0,
        }
        
        all_documents: List[Document] = []
        
        # 1. Website crawling
        if self.website_url and self.web_crawler:
            try:
                print(f"🔄 Crawleando sitio web: {self.website_url}")
                web_docs = self.web_crawler.crawl_website(self.website_url, max_pages=20)
                counts["website"] = len(web_docs)
                
                # Convertir a Document de LangChain
                for doc in web_docs:
                    langchain_doc = doc.to_langchain_document()
                    all_documents.append(langchain_doc)
                
                print(f"✅ Extraídos {len(web_docs)} documentos del sitio web")
            except Exception as e:
                print(f"⚠️ Error crawleando sitio web: {e}")
        
        # 2. Instagram
        try:
            print("🔄 Extrayendo posts de Instagram...")
            ig_docs = self.instagram_extractor.extract_posts(limit=25)
            counts["instagram"] = len(ig_docs)
            
            for doc in ig_docs:
                langchain_doc = doc.to_langchain_document()
                all_documents.append(langchain_doc)
            
            print(f"✅ Extraídos {len(ig_docs)} posts de Instagram")
        except Exception as e:
            print(f"⚠️ Error extrayendo Instagram: {e}")
        
        # 3. Facebook
        try:
            print("🔄 Extrayendo posts de Facebook...")
            fb_docs = self.facebook_extractor.extract_posts(limit=25)
            counts["facebook"] = len(fb_docs)
            
            for doc in fb_docs:
                langchain_doc = doc.to_langchain_document()
                all_documents.append(langchain_doc)
            
            print(f"✅ Extraídos {len(fb_docs)} posts de Facebook")
        except Exception as e:
            print(f"⚠️ Error extrayendo Facebook: {e}")
        
        # 4. Google Business
        try:
            print("🔄 Extrayendo reviews de Google Business...")
            google_docs = self.google_extractor.extract_reviews()
            counts["google"] = len(google_docs)
            
            for doc in google_docs:
                langchain_doc = doc.to_langchain_document()
                all_documents.append(langchain_doc)
            
            print(f"✅ Extraídos {len(google_docs)} reviews de Google")
        except Exception as e:
            print(f"⚠️ Error extrayendo Google: {e}")
        
        # 5. Filtrar duplicados
        unique_documents = self._filter_duplicates(all_documents)
        
        # 6. Agregar a RAG avanzado
        if unique_documents:
            print(f"🔄 Agregando {len(unique_documents)} documentos únicos a RAG...")
            self.advanced_rag.add_documents(unique_documents)
            print(f"✅ Documentos agregados a RAG avanzado")
        
        return counts
    
    def _filter_duplicates(self, documents: List[Document]) -> List[Document]:
        """Filtra documentos duplicados basado en hash del contenido."""
        unique_docs = []
        
        for doc in documents:
            # Generar hash del contenido
            content_hash = hashlib.md5(doc.page_content.encode()).hexdigest()
            
            if content_hash not in self.processed_docs_hash:
                self.processed_docs_hash.add(content_hash)
                unique_docs.append(doc)
        
        return unique_docs
    
    def _setup_scheduler(self):
        """Configura scheduler automático cada 6h según especificaciones."""
        if not self.enable_scheduler:
            return
        
        # Scheduler cada 6 horas para web
        schedule.every(6).hours.do(self._scheduled_ingest_web)
        
        # Scheduler diario para redes sociales (más frecuente)
        schedule.every().day.at("09:00").do(self._scheduled_ingest_social)
        
        print("✅ Scheduler configurado: web cada 6h, redes sociales diario")
    
    def _scheduled_ingest_web(self):
        """Ejecuta ingesta de web según scheduler."""
        if self.website_url and self.web_crawler:
            try:
                print(f"⏰ [SCHEDULER] Iniciando ingesta automática de web: {datetime.now()}")
                web_docs = self.web_crawler.crawl_website(self.website_url, max_pages=20)
                
                if web_docs:
                    langchain_docs = [doc.to_langchain_document() for doc in web_docs]
                    unique_docs = self._filter_duplicates(langchain_docs)
                    
                    if unique_docs:
                        self.advanced_rag.add_documents(unique_docs)
                        print(f"✅ [SCHEDULER] Agregados {len(unique_docs)} documentos nuevos de web")
            except Exception as e:
                print(f"⚠️ [SCHEDULER] Error en ingesta automática de web: {e}")
    
    def _scheduled_ingest_social(self):
        """Ejecuta ingesta de redes sociales según scheduler."""
        try:
            print(f"⏰ [SCHEDULER] Iniciando ingesta automática de redes sociales: {datetime.now()}")
            self.ingest_all_sources()
        except Exception as e:
            print(f"⚠️ [SCHEDULER] Error en ingesta automática de redes sociales: {e}")
    
    def start_scheduler(self):
        """Inicia el scheduler en un thread separado."""
        if not self.enable_scheduler:
            return
        
        import threading
        
        def run_scheduler():
            self.scheduler_running = True
            while self.scheduler_running:
                schedule.run_pending()
                time.sleep(60)  # Verificar cada minuto
        
        scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
        scheduler_thread.start()
        print("✅ Scheduler iniciado en background")
    
    def stop_scheduler(self):
        """Detiene el scheduler."""
        self.scheduler_running = False
        schedule.clear()
        print("✅ Scheduler detenido")
    
    def handle_webhook_new_post(self, platform: str, post_data: Dict[str, Any]) -> bool:
        """
        Maneja webhook de nuevo post según especificaciones.
        
        Args:
            platform: "instagram" o "facebook"
            post_data: Datos del post desde webhook
            
        Returns:
            True si se procesó exitosamente
        """
        if not self.enable_webhooks:
            return False
        
        try:
            # Normalizar datos según plataforma
            if platform == "instagram":
                doc = IngestedDocument(
                    source="instagram",
                    url=post_data.get("permalink", ""),
                    title="Instagram Post",
                    content=post_data.get("caption", ""),
                    category="marketing",
                    metadata={
                        "post_id": post_data.get("id", ""),
                        "media_type": post_data.get("media_type", ""),
                    },
                    date=post_data.get("timestamp", datetime.now().isoformat()),
                )
            elif platform == "facebook":
                doc = IngestedDocument(
                    source="facebook",
                    url=post_data.get("permalink_url", ""),
                    title="Facebook Post",
                    content=post_data.get("message", ""),
                    category="marketing",
                    metadata={
                        "post_id": post_data.get("id", ""),
                    },
                    date=post_data.get("created_time", datetime.now().isoformat()),
                )
            else:
                print(f"⚠️ Plataforma desconocida: {platform}")
                return False
            
            # Convertir a Document y agregar a RAG
            langchain_doc = doc.to_langchain_document()
            unique_docs = self._filter_duplicates([langchain_doc])
            
            if unique_docs:
                self.advanced_rag.add_documents(unique_docs)
                print(f"✅ [WEBHOOK] Nuevo post de {platform} agregado a RAG")
                return True
            
            return False
            
        except Exception as e:
            print(f"⚠️ [WEBHOOK] Error procesando nuevo post: {e}")
            return False
    
    def close(self):
        """Cierra recursos."""
        if self.web_crawler:
            self.web_crawler.close()
        self.stop_scheduler()
