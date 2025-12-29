"""
URL Crawler - Escaneo automático de URLs/FAQs del sitio web
Actualiza la base de conocimientos automáticamente cuando cambia el sitio
"""

from __future__ import annotations

import re
import time
from typing import List, Dict, Optional, Any, Set
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse, parse_qs

try:
    import requests
    from bs4 import BeautifulSoup
    REQUESTS_AVAILABLE = True
    BEAUTIFULSOUP_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    BEAUTIFULSOUP_AVAILABLE = False
    requests = None
    BeautifulSoup = None

from langchain_core.documents import Document


@dataclass
class CrawledPage:
    """Página crawleada."""
    url: str
    title: str
    content: str
    headings: List[str]
    links: List[str]
    crawled_at: str
    content_hash: str


class URLCrawler:
    """
    Crawler automático para escanear URLs/FAQs del sitio web.
    
    Características:
    - Escanea páginas automáticamente
    - Extrae FAQs y contenido relevante
    - Detecta cambios y actualiza conocimiento
    - Filtra contenido relevante
    - Convierte a Documentos para RAG
    """
    
    def __init__(self, max_depth: int = 2, max_pages: int = 50):
        """
        Inicializa el crawler.
        
        Args:
            max_depth: Profundidad máxima de crawling
            max_pages: Número máximo de páginas a crawlear
        """
        if not REQUESTS_AVAILABLE or not BEAUTIFULSOUP_AVAILABLE:
            raise ImportError("requests y beautifulsoup4 deben estar instalados: pip install requests beautifulsoup4")
        
        self.max_depth = max_depth
        self.max_pages = max_pages
        self.visited_urls: Set[str] = set()
        self.crawled_pages: List[CrawledPage] = []
        
        # Headers para parecer un navegador real
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive"
        }
        
        # Patrones para detectar FAQs y contenido relevante
        self.faq_patterns = [
            r"(?:FAQ|Preguntas Frecuentes|Frequently Asked Questions)",
            r"(?:pregunta|question).*?(?:respuesta|answer)",
            r"(?:¿|How|What|Where|When|Why).*\?",
        ]
    
    def crawl_url(self, url: str, base_url: Optional[str] = None) -> List[CrawledPage]:
        """
        Crawlea una URL y sus páginas relacionadas.
        
        Args:
            url: URL inicial para crawlear
            base_url: URL base para resolver URLs relativas (opcional)
            
        Returns:
            Lista de páginas crawleadas
        """
        if base_url is None:
            base_url = url
        
        self.visited_urls.clear()
        self.crawled_pages.clear()
        
        # Crawlear desde la URL inicial
        self._crawl_recursive(url, base_url, depth=0)
        
        return self.crawled_pages.copy()
    
    def _crawl_recursive(self, url: str, base_url: str, depth: int = 0):
        """Crawlea recursivamente una URL."""
        # Límites
        if depth > self.max_depth or len(self.crawled_pages) >= self.max_pages:
            return
        
        # Evitar crawlear la misma URL dos veces
        normalized_url = self._normalize_url(url)
        if normalized_url in self.visited_urls:
            return
        
        self.visited_urls.add(normalized_url)
        
        try:
            # Hacer request
            response = requests.get(url, headers=self.headers, timeout=10, allow_redirects=True)
            response.raise_for_status()
            
            # Solo procesar HTML
            content_type = response.headers.get("Content-Type", "")
            if "text/html" not in content_type:
                return
            
            # Parsear HTML
            soup = BeautifulSoup(response.content, "html.parser")
            
            # Extraer contenido
            page = self._extract_page_content(url, soup)
            
            if page:
                self.crawled_pages.append(page)
                
                # Si es página FAQ o relevante, buscar más links
                if self._is_relevant_page(page):
                    # Buscar links para crawlear
                    links = self._extract_links(soup, base_url)
                    for link in links[:10]:  # Limitar links por página
                        if len(self.crawled_pages) >= self.max_pages:
                            break
                        self._crawl_recursive(link, base_url, depth + 1)
                        
        except Exception as e:
            print(f"⚠️ Error crawleando {url}: {e}")
    
    def _normalize_url(self, url: str) -> str:
        """Normaliza URL para evitar duplicados."""
        parsed = urlparse(url)
        # Remover fragmentos y parámetros de tracking
        clean_path = parsed.path
        clean_query = ""
        
        if parsed.query:
            # Filtrar parámetros de tracking comunes
            params = parse_qs(parsed.query)
            filtered_params = {k: v for k, v in params.items() 
                             if k not in ["utm_source", "utm_medium", "utm_campaign", "fbclid", "gclid"]}
            if filtered_params:
                clean_query = "&".join(f"{k}={v[0]}" for k, v in filtered_params.items())
        
        normalized = f"{parsed.scheme}://{parsed.netloc}{clean_path}"
        if clean_query:
            normalized += f"?{clean_query}"
        
        return normalized
    
    def _extract_page_content(self, url: str, soup: BeautifulSoup) -> Optional[CrawledPage]:
        """Extrae contenido de una página."""
        try:
            # Título
            title_tag = soup.find("title")
            title = title_tag.get_text(strip=True) if title_tag else ""
            
            # Remover scripts y styles
            for script in soup(["script", "style", "nav", "footer", "header"]):
                script.decompose()
            
            # Extraer texto principal
            main_content = soup.find("main") or soup.find("article") or soup.find("body")
            if not main_content:
                return None
            
            # Extraer headings
            headings = []
            for heading in main_content.find_all(["h1", "h2", "h3", "h4", "h5", "h6"]):
                heading_text = heading.get_text(strip=True)
                if heading_text:
                    headings.append(heading_text)
            
            # Extraer texto
            text = main_content.get_text(separator="\n", strip=True)
            
            # Limpiar texto (remover espacios múltiples)
            text = re.sub(r"\n\s*\n", "\n\n", text)
            text = text.strip()
            
            if not text or len(text) < 100:  # Ignorar páginas muy cortas
                return None
            
            # Generar hash del contenido
            import hashlib
            content_hash = hashlib.md5(text.encode()).hexdigest()
            
            # Extraer links
            links = self._extract_links(soup, url)
            
            return CrawledPage(
                url=url,
                title=title,
                content=text,
                headings=headings,
                links=links,
                crawled_at=datetime.now().isoformat(),
                content_hash=content_hash
            )
            
        except Exception as e:
            print(f"⚠️ Error extrayendo contenido de {url}: {e}")
            return None
    
    def _extract_links(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """Extrae links de una página."""
        links = []
        base_parsed = urlparse(base_url)
        
        for link_tag in soup.find_all("a", href=True):
            href = link_tag["href"]
            absolute_url = urljoin(base_url, href)
            parsed = urlparse(absolute_url)
            
            # Solo links del mismo dominio
            if parsed.netloc == base_parsed.netloc:
                # Solo links HTML (no PDFs, imágenes, etc.)
                if not any(absolute_url.endswith(ext) for ext in [".pdf", ".jpg", ".png", ".gif", ".zip", ".exe"]):
                    links.append(absolute_url)
        
        return list(set(links))  # Remover duplicados
    
    def _is_relevant_page(self, page: CrawledPage) -> bool:
        """Verifica si una página es relevante (FAQ, etc.)."""
        content_lower = (page.title + " " + page.content).lower()
        
        # Buscar patrones de FAQ
        for pattern in self.faq_patterns:
            if re.search(pattern, content_lower, re.IGNORECASE):
                return True
        
        # Si tiene muchas preguntas, probablemente es FAQ
        questions = re.findall(r"[¿\?]", page.content)
        if len(questions) >= 3:
            return True
        
        return False
    
    def to_documents(self, pages: Optional[List[CrawledPage]] = None) -> List[Document]:
        """
        Convierte páginas crawleadas a Documentos de LangChain para RAG.
        
        Args:
            pages: Páginas a convertir (si None, usa self.crawled_pages)
            
        Returns:
            Lista de Documentos
        """
        if pages is None:
            pages = self.crawled_pages
        
        documents = []
        for page in pages:
            # Crear contenido estructurado
            content_parts = []
            
            if page.title:
                content_parts.append(f"# {page.title}\n")
            
            if page.headings:
                content_parts.append("\n## Secciones:\n")
                for heading in page.headings[:5]:  # Limitar headings
                    content_parts.append(f"- {heading}\n")
            
            content_parts.append(f"\n## Contenido:\n{page.content}\n")
            content_parts.append(f"\n**URL:** {page.url}\n")
            
            content = "".join(content_parts)
            
            doc = Document(
                page_content=content,
                metadata={
                    "source": page.url,
                    "title": page.title,
                    "url": page.url,
                    "crawled_at": page.crawled_at,
                    "content_hash": page.content_hash,
                    "type": "web_crawled"
                }
            )
            documents.append(doc)
        
        return documents
    
    def crawl_faqs_only(self, url: str) -> List[Document]:
        """
        Crawlea solo páginas FAQ relevantes y las convierte a Documentos.
        
        Args:
            url: URL inicial
            
        Returns:
            Lista de Documentos FAQ
        """
        # Crawlear con filtro de relevancia más estricto
        pages = self.crawl_url(url)
        
        # Filtrar solo FAQs relevantes
        faq_pages = [p for p in pages if self._is_relevant_page(p)]
        
        return self.to_documents(faq_pages)

