"""
Website Learner - Aprende del website del negocio

Este módulo es OPCIONAL y se configura por separado.
No afecta el funcionamiento del agente principal si no está configurado.

Funcionalidades:
- Extrae información del website
- Procesa páginas importantes (home, productos, FAQs, etc.)
- Incorpora conocimiento en el RAG del agente
"""

from __future__ import annotations

import os
import re
from typing import Dict, Any, Optional, List
from pathlib import Path
from urllib.parse import urljoin, urlparse
from dataclasses import dataclass

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


@dataclass
class WebsitePage:
    """Página del website."""
    url: str
    title: str
    content: str
    page_type: str  # home, product, faq, about, etc.
    metadata: Dict[str, Any] = None


class WebsiteLearner:
    """
    Aprende del website del negocio.
    
    Características:
    - Extrae información de páginas importantes
    - Procesa contenido relevante
    - Incorpora conocimiento en el RAG
    """
    
    def __init__(
        self,
        website_url: Optional[str] = None,
        max_pages: int = 20,
        max_depth: int = 2,
    ):
        """
        Inicializa el Website Learner.
        
        Args:
            website_url: URL del website (opcional, puede venir de .env)
            max_pages: Número máximo de páginas a procesar
            max_depth: Profundidad máxima de crawling
        """
        self.website_url = website_url or os.getenv("WEBSITE_URL")
        self.max_pages = max_pages
        self.max_depth = max_depth
        
        # Verificar si está configurado
        self.is_configured = bool(self.website_url)
        
        if not REQUESTS_AVAILABLE:
            print("⚠️ requests no está instalado. Instala con: pip install requests")
            self.is_configured = False
        
        if not BEAUTIFULSOUP_AVAILABLE:
            print("⚠️ beautifulsoup4 no está instalado. Instala con: pip install beautifulsoup4")
            self.is_configured = False
        
        if self.is_configured:
            print(f"✅ Website Learner configurado para: {self.website_url}")
        else:
            print("⚠️ Website Learner NO configurado (opcional - no afecta funcionamiento principal)")
    
    def _is_valid_url(self, url: str) -> bool:
        """Verifica si una URL es válida para procesar."""
        if not url:
            return False
        
        parsed = urlparse(url)
        
        # Solo URLs HTTP/HTTPS
        if parsed.scheme not in ["http", "https"]:
            return False
        
        # Evitar archivos (PDFs, imágenes, etc.)
        invalid_extensions = [".pdf", ".jpg", ".jpeg", ".png", ".gif", ".svg", ".css", ".js", ".xml"]
        if any(url.lower().endswith(ext) for ext in invalid_extensions):
            return False
        
        return True
    
    def _extract_text_from_html(self, html: str) -> str:
        """Extrae texto limpio de HTML."""
        if not BEAUTIFULSOUP_AVAILABLE:
            # Fallback básico sin BeautifulSoup
            text = re.sub(r'<[^>]+>', '', html)
            text = re.sub(r'\s+', ' ', text)
            return text.strip()
        
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Remover scripts y styles
            for script in soup(["script", "style", "nav", "footer", "header"]):
                script.decompose()
            
            # Extraer texto
            text = soup.get_text()
            
            # Limpiar espacios
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = ' '.join(chunk for chunk in chunks if chunk)
            
            return text
        except Exception as e:
            print(f"⚠️ Error extrayendo texto de HTML: {e}")
            return ""
    
    def _detect_page_type(self, url: str, title: str, content: str) -> str:
        """Detecta el tipo de página."""
        url_lower = url.lower()
        title_lower = title.lower()
        content_lower = content.lower()[:500]  # Primeros 500 chars
        
        if "faq" in url_lower or "faq" in title_lower or "preguntas" in content_lower:
            return "faq"
        elif "product" in url_lower or "producto" in url_lower or "shop" in url_lower:
            return "product"
        elif "about" in url_lower or "nosotros" in url_lower or "sobre" in url_lower:
            return "about"
        elif "contact" in url_lower or "contacto" in url_lower:
            return "contact"
        elif url_lower.endswith("/") or "home" in url_lower or "inicio" in url_lower:
            return "home"
        else:
            return "other"
    
    def fetch_page(self, url: str) -> Optional[WebsitePage]:
        """
        Obtiene y procesa una página del website.
        
        Args:
            url: URL de la página
            
        Returns:
            WebsitePage o None si hay error
        """
        if not self.is_configured or not REQUESTS_AVAILABLE:
            return None
        
        if not self._is_valid_url(url):
            return None
        
        try:
            response = requests.get(url, timeout=10, headers={
                "User-Agent": "Mozilla/5.0 (compatible; SalesAIAgent/1.0; +https://example.com/bot)"
            })
            response.raise_for_status()
            
            # Extraer título y contenido
            html = response.text
            
            if BEAUTIFULSOUP_AVAILABLE:
                soup = BeautifulSoup(html, 'html.parser')
                title = soup.title.string if soup.title else url
            else:
                # Fallback básico
                title_match = re.search(r'<title>(.*?)</title>', html, re.IGNORECASE)
                title = title_match.group(1) if title_match else url
            
            content = self._extract_text_from_html(html)
            page_type = self._detect_page_type(url, title, content)
            
            return WebsitePage(
                url=url,
                title=title,
                content=content[:5000],  # Limitar a 5000 caracteres
                page_type=page_type,
                metadata={"status_code": response.status_code}
            )
            
        except Exception as e:
            print(f"⚠️ Error obteniendo página {url}: {e}")
            return None
    
    def crawl_website(self) -> List[WebsitePage]:
        """
        Hace crawling del website para extraer información.
        
        Returns:
            Lista de páginas procesadas
        """
        if not self.is_configured:
            return []
        
        if not self.website_url:
            return []
        
        pages = []
        visited_urls = set()
        urls_to_visit = [self.website_url]
        depth = 0
        
        while urls_to_visit and len(pages) < self.max_pages and depth <= self.max_depth:
            current_url = urls_to_visit.pop(0)
            
            if current_url in visited_urls:
                continue
            
            visited_urls.add(current_url)
            
            # Obtener página
            page = self.fetch_page(current_url)
            if page:
                pages.append(page)
                print(f"✅ Procesada: {page.title[:50]}... ({page.page_type})")
                
                # Si es HTML y tenemos BeautifulSoup, extraer links
                if BEAUTIFULSOUP_AVAILABLE and depth < self.max_depth:
                    try:
                        response = requests.get(current_url, timeout=10)
                        soup = BeautifulSoup(response.text, 'html.parser')
                        
                        # Encontrar links internos
                        base_url = urlparse(self.website_url)
                        for link in soup.find_all('a', href=True):
                            href = link['href']
                            absolute_url = urljoin(current_url, href)
                            
                            # Solo URLs del mismo dominio
                            parsed = urlparse(absolute_url)
                            if parsed.netloc == base_url.netloc and absolute_url not in visited_urls:
                                if self._is_valid_url(absolute_url):
                                    urls_to_visit.append(absolute_url)
                    except:
                        pass  # Si falla, continuar sin extraer más links
            
            depth += 1
        
        print(f"✅ Website crawling completado: {len(pages)} páginas procesadas")
        return pages
    
    def extract_knowledge_from_website(self) -> str:
        """
        Extrae conocimiento del website para incorporar en el RAG.
        
        Returns:
            Texto con conocimiento extraído
        """
        if not self.is_configured:
            return ""
        
        pages = self.crawl_website()
        
        if not pages:
            return ""
        
        knowledge_parts = []
        
        # Agrupar por tipo de página
        by_type = {}
        for page in pages:
            if page.page_type not in by_type:
                by_type[page.page_type] = []
            by_type[page.page_type].append(page)
        
        # Priorizar páginas importantes
        priority_types = ["home", "faq", "product", "about"]
        
        for page_type in priority_types:
            if page_type in by_type:
                for page in by_type[page_type][:3]:  # Máximo 3 por tipo
                    knowledge_parts.append(
                        f"**{page.title} ({page.page_type}):**\n{page.content[:1000]}"
                    )
        
        return "\n\n".join(knowledge_parts)

