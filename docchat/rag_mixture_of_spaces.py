"""Mixture of Spaces: Múltiples representaciones paralelas del mismo documento.

Basado en el paper de Corvic AI sobre L4 RAG:
- Semantic Space: embeddings de significado
- Structural Space: layout, jerarquía, relaciones
- Metadata Space: títulos, tags, anotaciones

Permite recuperar información que single-space perdería.
"""

from __future__ import annotations

import json
import hashlib
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from pathlib import Path

from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma, FAISS


@dataclass
class DocumentStructure:
    """Estructura de un documento (jerarquía, layout, relaciones)."""
    document_id: str
    sections: List[Dict[str, Any]] = field(default_factory=list)  # [{level, title, content, start_pos, end_pos}]
    tables: List[Dict[str, Any]] = field(default_factory=list)  # [{table_id, headers, rows, position}]
    headings: List[Dict[str, Any]] = field(default_factory=list)  # [{level, text, position}]
    cross_references: List[Dict[str, Any]] = field(default_factory=list)  # [{from, to, type}]
    lists: List[Dict[str, Any]] = field(default_factory=list)  # [{type, items, position}]


@dataclass
class DocumentMetadata:
    """Metadata enriquecida de un documento."""
    document_id: str
    title: Optional[str] = None
    author: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    categories: List[str] = field(default_factory=list)
    domain: Optional[str] = None  # "Ventas", "Finanzas", "RRHH", etc.
    created_at: Optional[str] = None
    modified_at: Optional[str] = None
    custom_fields: Dict[str, Any] = field(default_factory=dict)


class SemanticSpace:
    """Espacio semántico: embeddings de significado."""
    
    def __init__(self, config: Any):
        self.config = config
        self.embedding_function = OpenAIEmbeddings(model=config.embedding_model)
        self.vector_store: Optional[Any] = None
        self.space_path = config.persist_dir / "semantic_space"
    
    def build_index(self, documents: List[Document]) -> None:
        """Construye índice semántico."""
        try:
            self.vector_store = Chroma.from_documents(
                documents=documents,
                embedding=self.embedding_function,
                persist_directory=str(self.space_path),
            )
            print(f"✅ Semantic Space: {len(documents)} documentos indexados")
        except Exception as e:
            print(f"⚠️ Error construyendo Semantic Space: {e}")
            # Fallback a FAISS si Chroma falla
            try:
                from langchain_community.vectorstores import FAISS
                self.vector_store = FAISS.from_documents(
                    documents=documents,
                    embedding=self.embedding_function,
                )
            except Exception as e2:
                print(f"❌ Error con FAISS fallback: {e2}")
    
    def search(self, query: str, k: int = 5) -> List[Document]:
        """Busca en espacio semántico."""
        if not self.vector_store:
            return []
        
        try:
            results = self.vector_store.similarity_search(query, k=k)
            return results
        except Exception as e:
            print(f"⚠️ Error en búsqueda semántica: {e}")
            return []


class StructuralSpace:
    """Espacio estructural: layout, jerarquía, relaciones."""
    
    def __init__(self, config: Any):
        self.config = config
        self.structures: Dict[str, DocumentStructure] = {}  # document_id -> structure
        self.structural_index: Dict[str, List[str]] = {}  # heading_text -> [document_ids]
        self.table_index: Dict[str, List[str]] = {}  # table_header -> [document_ids]
    
    def build_index(self, documents: List[Document], structures: Optional[List[DocumentStructure]] = None) -> None:
        """Construye índice estructural."""
        # Si no se proporcionan structures, extraerlas de documentos
        if not structures:
            structures = [self._extract_structure(doc) for doc in documents]
        
        for struct in structures:
            self.structures[struct.document_id] = struct
            
            # Indexar headings
            for heading in struct.headings:
                heading_text = heading.get("text", "").lower()
                if heading_text not in self.structural_index:
                    self.structural_index[heading_text] = []
                self.structural_index[heading_text].append(struct.document_id)
            
            # Indexar tablas
            for table in struct.tables:
                headers = table.get("headers", [])
                for header in headers:
                    header_lower = header.lower()
                    if header_lower not in self.table_index:
                        self.table_index[header_lower] = []
                    self.table_index[header_lower].append(struct.document_id)
        
        print(f"✅ Structural Space: {len(structures)} estructuras indexadas")
    
    def _extract_structure(self, doc: Document) -> DocumentStructure:
        """Extrae estructura de un documento."""
        doc_id = doc.metadata.get("id", hashlib.md5(doc.page_content.encode()).hexdigest())
        content = doc.page_content
        
        structure = DocumentStructure(document_id=doc_id)
        
        # Extraer headings (simplificado)
        lines = content.split('\n')
        current_section = None
        
        for i, line in enumerate(lines):
            line_stripped = line.strip()
            
            # Detectar headings
            if line_stripped.startswith('#'):
                level = len(line_stripped) - len(line_stripped.lstrip('#'))
                heading_text = line_stripped.lstrip('#').strip()
                structure.headings.append({
                    "level": level,
                    "text": heading_text,
                    "position": i,
                })
            
            # Detectar listas (simplificado)
            if line_stripped.startswith('-') or line_stripped.startswith('*'):
                structure.lists.append({
                    "type": "unordered",
                    "items": [line_stripped.lstrip('-*').strip()],
                    "position": i,
                })
        
        return structure
    
    def search_by_heading(self, heading_query: str, k: int = 5) -> List[str]:
        """Busca documentos por heading."""
        heading_lower = heading_query.lower()
        matching_docs = []
        
        for heading_text, doc_ids in self.structural_index.items():
            if heading_lower in heading_text or heading_text in heading_lower:
                matching_docs.extend(doc_ids[:k])
        
        return list(set(matching_docs))[:k]
    
    def search_by_table(self, table_query: str, k: int = 5) -> List[str]:
        """Busca documentos por tabla/columna."""
        query_lower = table_query.lower()
        matching_docs = []
        
        for header, doc_ids in self.table_index.items():
            if query_lower in header or header in query_lower:
                matching_docs.extend(doc_ids[:k])
        
        return list(set(matching_docs))[:k]
    
    def get_structure(self, document_id: str) -> Optional[DocumentStructure]:
        """Obtiene estructura de un documento."""
        return self.structures.get(document_id)


class MetadataSpace:
    """Espacio de metadata: títulos, tags, anotaciones."""
    
    def __init__(self, config: Any):
        self.config = config
        self.metadata_store: Dict[str, DocumentMetadata] = {}  # document_id -> metadata
        self.tag_index: Dict[str, List[str]] = {}  # tag -> [document_ids]
        self.domain_index: Dict[str, List[str]] = {}  # domain -> [document_ids]
        self.title_index: Dict[str, List[str]] = {}  # title_word -> [document_ids]
    
    def build_index(self, documents: List[Document], metadata_list: Optional[List[DocumentMetadata]] = None) -> None:
        """Construye índice de metadata."""
        # Si no se proporcionan metadata, extraerlas de documentos
        if not metadata_list:
            metadata_list = [self._extract_metadata(doc) for doc in documents]
        
        for metadata in metadata_list:
            self.metadata_store[metadata.document_id] = metadata
            
            # Indexar tags
            for tag in metadata.tags:
                tag_lower = tag.lower()
                if tag_lower not in self.tag_index:
                    self.tag_index[tag_lower] = []
                self.tag_index[tag_lower].append(metadata.document_id)
            
            # Indexar domain
            if metadata.domain:
                domain_lower = metadata.domain.lower()
                if domain_lower not in self.domain_index:
                    self.domain_index[domain_lower] = []
                self.domain_index[domain_lower].append(metadata.document_id)
            
            # Indexar título
            if metadata.title:
                title_words = metadata.title.lower().split()
                for word in title_words:
                    if word not in self.title_index:
                        self.title_index[word] = []
                    self.title_index[word].append(metadata.document_id)
        
        print(f"✅ Metadata Space: {len(metadata_list)} documentos indexados")
    
    def _extract_metadata(self, doc: Document) -> DocumentMetadata:
        """Extrae metadata de un documento."""
        doc_id = doc.metadata.get("id", hashlib.md5(doc.page_content.encode()).hexdigest())
        metadata = doc.metadata
        
        return DocumentMetadata(
            document_id=doc_id,
            title=metadata.get("title") or metadata.get("source"),
            author=metadata.get("author"),
            tags=metadata.get("tags", []),
            categories=metadata.get("categories", []),
            domain=metadata.get("domain"),
            created_at=metadata.get("created_at"),
            modified_at=metadata.get("modified_at"),
            custom_fields={k: v for k, v in metadata.items() 
                          if k not in ["id", "title", "author", "tags", "categories", "domain", "created_at", "modified_at"]},
        )
    
    def search_by_tag(self, tag: str, k: int = 5) -> List[str]:
        """Busca documentos por tag."""
        tag_lower = tag.lower()
        return self.tag_index.get(tag_lower, [])[:k]
    
    def search_by_domain(self, domain: str, k: int = 5) -> List[str]:
        """Busca documentos por domain."""
        domain_lower = domain.lower()
        return self.domain_index.get(domain_lower, [])[:k]
    
    def search_by_title(self, title_query: str, k: int = 5) -> List[str]:
        """Busca documentos por palabras en título."""
        query_words = title_query.lower().split()
        matching_docs = []
        
        for word in query_words:
            if word in self.title_index:
                matching_docs.extend(self.title_index[word])
        
        return list(set(matching_docs))[:k]


class MixtureOfSpaces:
    """Sistema de múltiples espacios para recuperación robusta."""
    
    def __init__(self, config: Any):
        self.config = config
        self.semantic_space = SemanticSpace(config)
        self.structural_space = StructuralSpace(config)
        self.metadata_space = MetadataSpace(config)
    
    def build_indexes(
        self,
        documents: List[Document],
        structures: Optional[List[DocumentStructure]] = None,
        metadata_list: Optional[List[DocumentMetadata]] = None,
    ) -> None:
        """Construye todos los índices."""
        print("🔨 Construyendo Mixture of Spaces...")
        self.semantic_space.build_index(documents)
        self.structural_space.build_index(documents, structures)
        self.metadata_space.build_index(documents, metadata_list)
        print("✅ Mixture of Spaces construido")
    
    def search(
        self,
        query: str,
        k: int = 5,
        use_semantic: bool = True,
        use_structural: bool = True,
        use_metadata: bool = True,
    ) -> List[Document]:
        """Busca en múltiples espacios y combina resultados."""
        all_results: Dict[str, Document] = {}  # doc_id -> Document
        scores: Dict[str, float] = {}  # doc_id -> score
        
        # Búsqueda semántica
        if use_semantic:
            semantic_results = self.semantic_space.search(query, k=k*2)
            for i, doc in enumerate(semantic_results):
                doc_id = doc.metadata.get("id", hashlib.md5(doc.page_content.encode()).hexdigest())
                all_results[doc_id] = doc
                # Score: más alto = más relevante, más bajo = más abajo en ranking
                scores[doc_id] = scores.get(doc_id, 0) + (len(semantic_results) - i) * 0.4
        
        # Búsqueda estructural
        if use_structural:
            # Buscar por headings
            heading_doc_ids = self.structural_space.search_by_heading(query, k=k)
            for doc_id in heading_doc_ids:
                scores[doc_id] = scores.get(doc_id, 0) + 0.3
            
            # Buscar por tablas
            table_doc_ids = self.structural_space.search_by_table(query, k=k)
            for doc_id in table_doc_ids:
                scores[doc_id] = scores.get(doc_id, 0) + 0.3
        
        # Búsqueda por metadata
        if use_metadata:
            # Buscar por tags
            tag_doc_ids = self.metadata_space.search_by_tag(query, k=k)
            for doc_id in tag_doc_ids:
                scores[doc_id] = scores.get(doc_id, 0) + 0.2
            
            # Buscar por domain
            domain_doc_ids = self.metadata_space.search_by_domain(query, k=k)
            for doc_id in domain_doc_ids:
                scores[doc_id] = scores.get(doc_id, 0) + 0.2
            
            # Buscar por título
            title_doc_ids = self.metadata_space.search_by_title(query, k=k)
            for doc_id in title_doc_ids:
                scores[doc_id] = scores.get(doc_id, 0) + 0.1
        
        # Ordenar por score y retornar top-k
        sorted_docs = sorted(
            all_results.items(),
            key=lambda x: scores.get(x[0], 0),
            reverse=True
        )
        
        return [doc for doc_id, doc in sorted_docs[:k]]

