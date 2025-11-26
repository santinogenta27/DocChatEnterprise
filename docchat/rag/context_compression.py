"""
Context Compression: Reduce tokens sin perder información crítica.
"""

from __future__ import annotations

from typing import List, Optional

from langchain_core.documents import Document
from langchain_openai import ChatOpenAI


class ContextCompressor:
    """
    Comprime contexto para reducir tokens manteniendo información importante.
    """
    
    def __init__(self, llm: ChatOpenAI):
        self.llm = llm
    
    def compress_documents(
        self,
        documents: List[Document],
        max_tokens: int = 4000,
        preserve_key_info: bool = True
    ) -> List[Document]:
        """
        Comprime documentos para reducir tokens.
        
        Args:
            documents: Lista de documentos a comprimir
            max_tokens: Máximo de tokens objetivo
            preserve_key_info: Si True, preserva información clave
        """
        if not documents:
            return documents
        
        # Calcular tokens aproximados
        total_chars = sum(len(doc.page_content) for doc in documents)
        estimated_tokens = total_chars // 4  # Aproximación
        
        if estimated_tokens <= max_tokens:
            return documents  # No necesita compresión
        
        # Comprimir cada documento
        compressed = []
        for doc in documents:
            compressed_doc = self._compress_document(doc, preserve_key_info)
            compressed.append(compressed_doc)
        
        return compressed
    
    def _compress_document(
        self,
        document: Document,
        preserve_key_info: bool = True
    ) -> Document:
        """Comprime un documento individual."""
        content = document.page_content
        
        # Si es muy corto, no comprimir
        if len(content) < 500:
            return document
        
        # Estrategia de compresión
        if preserve_key_info:
            # Compresión inteligente manteniendo info clave
            compressed_content = self._intelligent_compress(content)
        else:
            # Compresión simple (truncar)
            compressed_content = content[:2000] + "..."
        
        return Document(
            page_content=compressed_content,
            metadata={
                **document.metadata,
                "compressed": True,
                "original_length": len(content)
            }
        )
    
    def _intelligent_compress(self, text: str) -> str:
        """
        Compresión inteligente usando LLM para mantener información clave.
        """
        prompt = f"""Comprime el siguiente texto manteniendo TODA la información importante.
        Elimina redundancias, ejemplos repetitivos, y detalles menores.
        Mantén: hechos clave, números, fechas, nombres, conclusiones importantes.
        
        Texto a comprimir:
        {text[:3000]}
        
        Texto comprimido:"""
        
        try:
            response = self.llm.invoke(prompt)
            compressed = response.content.strip()
            
            # Asegurar que no sea más largo que el original
            if len(compressed) > len(text):
                return text
            
            return compressed
        
        except Exception:
            # Fallback: compresión simple
            return text[:2000] + "..."
    
    def summarize_chunks(self, chunks: List[Document], max_chunks: int = 5) -> List[Document]:
        """
        Resume múltiples chunks en menos chunks manteniendo información.
        """
        if len(chunks) <= max_chunks:
            return chunks
        
        # Agrupar chunks similares
        grouped = self._group_similar_chunks(chunks)
        
        # Resumir cada grupo
        summarized = []
        for group in grouped[:max_chunks]:
            if len(group) == 1:
                summarized.append(group[0])
            else:
                # Resumir grupo
                combined_text = "\n\n".join(doc.page_content for doc in group)
                summary = self._intelligent_compress(combined_text)
                
                summarized.append(Document(
                    page_content=summary,
                    metadata={
                        **group[0].metadata,
                        "summarized_from": len(group)
                    }
                ))
        
        return summarized
    
    def _group_similar_chunks(self, chunks: List[Document]) -> List[List[Document]]:
        """Agrupa chunks similares por fuente."""
        groups = {}
        
        for chunk in chunks:
            source = chunk.metadata.get("source", "unknown")
            if source not in groups:
                groups[source] = []
            groups[source].append(chunk)
        
        return list(groups.values())

