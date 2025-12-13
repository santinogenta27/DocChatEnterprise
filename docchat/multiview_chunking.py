"""
Multiview Chunking: Segmentación de documentos PDF en múltiples vistas
Basado en NeuSym-RAG y Advanced ingestion process papers.
"""

from __future__ import annotations

import json
from typing import List, Dict, Optional, Any, Tuple
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum

from langchain_core.documents import Document


class ChunkingView(Enum):
    """Diferentes vistas para chunking de documentos."""
    PAGES = "pages"
    SECTIONS = "sections"
    TABLES = "tables"
    IMAGES = "images"
    FORMULAS = "formulas"
    CHUNKS = "chunks"
    PARAGRAPHS = "paragraphs"


@dataclass
class PageChunk:
    """Chunk de página."""
    page_number: int
    content: str
    summary: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SectionChunk:
    """Chunk de sección."""
    section_index: int
    title: str
    content: str
    summary: Optional[str] = None
    page_number: int = 1
    level: int = 1  # Nivel de jerarquía (1, 2, 3, etc.)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TableChunk:
    """Chunk de tabla."""
    table_index: int
    caption: Optional[str] = None
    content: str = ""  # HTML o texto estructurado
    summary: Optional[str] = None
    page_number: int = 1
    bounding_box: List[float] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ImageChunk:
    """Chunk de imagen."""
    image_index: int
    caption: Optional[str] = None
    description: Optional[str] = None
    summary: Optional[str] = None
    page_number: int = 1
    bounding_box: List[float] = field(default_factory=list)
    image_type: str = "figure"  # figure, plot, flowchart, snapshot
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FormulaChunk:
    """Chunk de fórmula/ecuación."""
    equation_index: int
    content: str  # LaTeX
    page_number: int = 1
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TextChunk:
    """Chunk de texto (párrafo o fragmento)."""
    chunk_index: int
    content: str
    page_number: int = 1
    chunk_type: str = "paragraph"  # paragraph, list, quote, etc.
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MultiviewChunks:
    """Contenedor para todas las vistas de chunking de un documento."""
    paper_id: str
    pages: List[PageChunk] = field(default_factory=list)
    sections: List[SectionChunk] = field(default_factory=list)
    tables: List[TableChunk] = field(default_factory=list)
    images: List[ImageChunk] = field(default_factory=list)
    formulas: List[FormulaChunk] = field(default_factory=list)
    chunks: List[TextChunk] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class MultiviewChunker:
    """
    Chunker que segmenta documentos PDF en múltiples vistas simultáneamente.
    
    Vistas soportadas:
    - Pages: Por número de página
    - Sections: Por secciones jerárquicas
    - Tables: Tablas extraídas
    - Images: Figuras, gráficos, diagramas
    - Formulas: Ecuaciones en LaTeX
    - Chunks: Fragmentos de texto de tamaño fijo o semántico
    """
    
    def __init__(
        self,
        llm: Optional[Any] = None,
        chunk_size: int = 512,
        chunk_overlap: int = 50
    ):
        self.llm = llm
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
    
    def chunk_document(
        self,
        paper_id: str,
        documents: List[Document],
        metadata: Optional[Dict[str, Any]] = None
    ) -> MultiviewChunks:
        """
        Chunking multiview de un documento.
        
        Args:
            paper_id: ID único del documento
            documents: Lista de Documentos de LangChain
            metadata: Metadata adicional del documento
        
        Returns:
            MultiviewChunks con todas las vistas
        """
        multiview = MultiviewChunks(paper_id=paper_id, metadata=metadata or {})
        
        # Extraer texto completo
        full_text = "\n\n".join([doc.page_content for doc in documents])
        
        # 1. Chunking por páginas
        multiview.pages = self._chunk_by_pages(documents)
        
        # 2. Chunking por secciones
        multiview.sections = self._chunk_by_sections(full_text, documents)
        
        # 3. Extraer tablas
        multiview.tables = self._extract_tables(documents)
        
        # 4. Extraer imágenes
        multiview.images = self._extract_images(documents)
        
        # 5. Extraer fórmulas
        multiview.formulas = self._extract_formulas(full_text)
        
        # 6. Chunking semántico/fijo
        multiview.chunks = self._chunk_text(full_text, documents)
        
        return multiview
    
    def _chunk_by_pages(self, documents: List[Document]) -> List[PageChunk]:
        """Chunking por páginas."""
        pages = []
        current_page = 1
        current_content = []
        
        for doc in documents:
            page_num = doc.metadata.get("page", current_page)
            
            if page_num != current_page and current_content:
                pages.append(PageChunk(
                    page_number=current_page,
                    content="\n".join(current_content),
                    metadata={"source": doc.metadata.get("source", "")}
                ))
                current_content = []
                current_page = page_num
            
            current_content.append(doc.page_content)
        
        # Última página
        if current_content:
            pages.append(PageChunk(
                page_number=current_page,
                content="\n".join(current_content)
            ))
        
        return pages
    
    def _chunk_by_sections(self, full_text: str, documents: List[Document]) -> List[SectionChunk]:
        """Chunking por secciones jerárquicas."""
        sections = []
        
        # Detectar secciones usando patrones comunes
        import re
        
        # Patrones para títulos de sección
        section_patterns = [
            r'^#+\s+(.+)$',  # Markdown headers
            r'^\d+\.\d*\s+(.+)$',  # Numbered sections
            r'^([A-Z][A-Z\s]+)$',  # ALL CAPS headers
        ]
        
        lines = full_text.split('\n')
        current_section = None
        current_content = []
        section_index = 0
        
        for line in lines:
            is_header = False
            for pattern in section_patterns:
                match = re.match(pattern, line.strip())
                if match:
                    # Guardar sección anterior
                    if current_section:
                        sections.append(SectionChunk(
                            section_index=section_index,
                            title=current_section,
                            content="\n".join(current_content),
                            level=1
                        ))
                        section_index += 1
                    
                    # Nueva sección
                    current_section = match.group(1).strip()
                    current_content = []
                    is_header = True
                    break
            
            if not is_header and current_section:
                current_content.append(line)
        
        # Última sección
        if current_section:
            sections.append(SectionChunk(
                section_index=section_index,
                title=current_section,
                content="\n".join(current_content),
                level=1
            ))
        
        return sections
    
    def _extract_tables(self, documents: List[Document]) -> List[TableChunk]:
        """Extrae tablas del documento."""
        tables = []
        table_index = 0
        
        for doc in documents:
            # Buscar tablas en el contenido (HTML, markdown, o texto estructurado)
            content = doc.page_content
            
            # Detectar tablas HTML
            import re
            html_tables = re.findall(r'<table[^>]*>.*?</table>', content, re.DOTALL)
            
            for table_html in html_tables:
                tables.append(TableChunk(
                    table_index=table_index,
                    content=table_html,
                    page_number=doc.metadata.get("page", 1),
                    metadata={"source": doc.metadata.get("source", "")}
                ))
                table_index += 1
        
        return tables
    
    def _extract_images(self, documents: List[Document]) -> List[ImageChunk]:
        """Extrae imágenes/figuras del documento."""
        images = []
        image_index = 0
        
        for doc in documents:
            # Buscar referencias a imágenes en metadata o contenido
            metadata = doc.metadata
            
            if "images" in metadata:
                for img_data in metadata["images"]:
                    images.append(ImageChunk(
                        image_index=image_index,
                        caption=img_data.get("caption"),
                        description=img_data.get("description"),
                        page_number=img_data.get("page", doc.metadata.get("page", 1)),
                        bounding_box=img_data.get("bbox", []),
                        image_type=img_data.get("type", "figure")
                    ))
                    image_index += 1
        
        return images
    
    def _extract_formulas(self, full_text: str) -> List[FormulaChunk]:
        """Extrae fórmulas/ecuaciones del documento."""
        formulas = []
        
        # Detectar fórmulas LaTeX
        import re
        
        # Patrones comunes para ecuaciones LaTeX
        latex_patterns = [
            r'\$\$(.+?)\$\$',  # Display math
            r'\$(.+?)\$',  # Inline math
            r'\\begin\{equation\}(.+?)\\end\{equation\}',  # Equation environment
        ]
        
        equation_index = 0
        for pattern in latex_patterns:
            matches = re.finditer(pattern, full_text, re.DOTALL)
            for match in matches:
                formulas.append(FormulaChunk(
                    equation_index=equation_index,
                    content=match.group(1).strip()
                ))
                equation_index += 1
        
        return formulas
    
    def _chunk_text(
        self,
        full_text: str,
        documents: List[Document]
    ) -> List[TextChunk]:
        """Chunking de texto en fragmentos de tamaño fijo o semántico."""
        chunks = []
        
        # Chunking simple por tamaño
        words = full_text.split()
        chunk_index = 0
        
        for i in range(0, len(words), self.chunk_size - self.chunk_overlap):
            chunk_words = words[i:i + self.chunk_size]
            chunk_text = " ".join(chunk_words)
            
            # Determinar página basada en posición
            page_num = 1
            if documents:
                # Aproximación: calcular página basada en posición
                total_chars = sum(len(doc.page_content) for doc in documents)
                current_chars = sum(len(doc.page_content) for doc in documents[:i // (self.chunk_size // 2)])
                page_num = int((current_chars / total_chars) * len(documents)) + 1
            
            chunks.append(TextChunk(
                chunk_index=chunk_index,
                content=chunk_text,
                page_number=page_num,
                chunk_type="paragraph"
            ))
            chunk_index += 1
        
        return chunks
    
    def generate_summaries(
        self,
        multiview: MultiviewChunks,
        llm: Optional[Any] = None
    ) -> MultiviewChunks:
        """
        Genera resúmenes para diferentes vistas usando LLM.
        """
        if not llm:
            return multiview
        
        # Generar resúmenes para páginas
        for page in multiview.pages:
            if not page.summary and len(page.content) > 100:
                prompt = f"Generate a brief summary (1-2 sentences) of this page content:\n\n{page.content[:1000]}"
                try:
                    response = llm.invoke(prompt)
                    page.summary = str(response.content).strip()
                except:
                    pass
        
        # Generar resúmenes para secciones
        for section in multiview.sections:
            if not section.summary:
                prompt = f"Generate a brief summary of this section '{section.title}':\n\n{section.content[:1000]}"
                try:
                    response = llm.invoke(prompt)
                    section.summary = str(response.content).strip()
                except:
                    pass
        
        # Generar resúmenes para tablas
        for table in multiview.tables:
            if not table.summary:
                prompt = f"Describe the key information in this table:\n\n{table.content[:1000]}"
                try:
                    response = llm.invoke(prompt)
                    table.summary = str(response.content).strip()
                except:
                    pass
        
        # Generar descripciones para imágenes
        for image in multiview.images:
            if not image.description:
                prompt = f"Describe this image with caption '{image.caption}':"
                try:
                    response = llm.invoke(prompt)
                    image.description = str(response.content).strip()
                except:
                    pass
        
        return multiview

