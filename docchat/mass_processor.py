"""Massive document processing with parallel execution and comparative analysis."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError as FutureTimeoutError
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import time

from .document_processor import DocumentProcessor, CachedChunks
from .config import AppConfig
from langchain_core.documents import Document


@dataclass
class DocumentMetadata:
    """Metadata for a processed document."""
    file_name: str
    file_hash: str
    chunk_count: int
    processing_time: float
    size_mb: float
    errors: List[str]


@dataclass
class ComparativeAnalysis:
    """Results from comparative analysis across documents."""
    common_themes: List[str]
    unique_content: Dict[str, List[str]]  # file_name -> unique topics
    contradictions: List[Dict[str, str]]
    statistics: Dict[str, Any]


class MassDocumentProcessor:
    """Process hundreds of documents in parallel with comparative analysis."""
    
    def __init__(self, config: AppConfig):
        self.config = config
        self.processor = DocumentProcessor(config)
        # Aumentar workers para procesamiento más rápido (hasta 16 paralelos para 1000 docs)
        self.max_workers = min(config.max_workers, 16) if config.parallel_processing else 1
    
    def process_massive_batch(
        self,
        files: List,
        enable_comparison: bool = True
    ) -> tuple[List[Document], List[DocumentMetadata], Optional[ComparativeAnalysis]]:
        """Process a large batch of documents in parallel."""
        start_time = time.time()
        total_files = len(files)
        
        print(f"\n{'='*60}")
        print(f"🚀 INICIANDO PROCESAMIENTO MASIVO OPTIMIZADO")
        print(f"{'='*60}")
        print(f"📄 Total de documentos: {total_files}")
        print(f"⚙️  Workers paralelos: {self.max_workers}")
        print(f"⏱️  Timeout por documento: {self.config.document_timeout_seconds}s")
        print(f"\n⚡ OPTIMIZACIÓN: PyPDF2 primero (10-100x más rápido)")
        print(f"   - PyPDF2 para PDFs simples: ~1-5 segundos")
        print(f"   - Docling solo si es necesario: ~30-60 segundos")
        print(f"\n💡 NOTA: Los documentos se procesan EN PARALELO")
        print(f"   Puedes ver múltiples documentos procesándose simultáneamente")
        print(f"   El tiempo total será mucho menor que procesamiento secuencial")
        print(f"{'='*60}\n")
        
        # Validate total size
        total_size = sum(len(getattr(f, 'read', lambda: b'')() or b'') for f in files)
        if total_size > self.config.max_total_upload_mb * 1024 * 1024:
            raise ValueError(
                f"Total size exceeds limit of {self.config.max_total_upload_mb} MB"
            )
        
        # Process documents in parallel
        all_chunks: List[Document] = []
        metadata_list: List[DocumentMetadata] = []
        completed_count = 0
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(self._process_single_document, file_obj): file_obj
                for file_obj in files
            }
            
            timeout_seconds = self.config.document_timeout_seconds
            for future in as_completed(futures):
                file_obj = futures[future]
                completed_count += 1
                elapsed_time = time.time() - start_time
                
                try:
                    # Wait with timeout
                    chunks, metadata = future.result(timeout=timeout_seconds)
                    all_chunks.extend(chunks)
                    metadata_list.append(metadata)
                    
                    # Progress logging (mejorado para lotes grandes)
                    progress_pct = (completed_count / total_files) * 100
                    avg_time_per_doc = elapsed_time / completed_count
                    estimated_remaining = (total_files - completed_count) * avg_time_per_doc
                    
                    status_icon = "✅" if len(chunks) > 0 else "⚠️"
                    
                    # Para lotes grandes (>100), mostrar progreso cada 10 documentos
                    if total_files > 100 and completed_count % 10 != 0:
                        # Solo mostrar cada 10 documentos para no saturar la consola
                        pass
                    else:
                        print(f"{status_icon} [{completed_count}/{total_files}] {metadata.file_name}")
                        print(f"   └─ {len(chunks)} chunks | {metadata.processing_time:.1f}s | "
                              f"Progreso: {progress_pct:.1f}% | "
                              f"Tiempo restante: {estimated_remaining/60:.1f} min")
                    
                    # Mostrar resumen cada 50 documentos en lotes grandes
                    if total_files > 50 and completed_count % 50 == 0:
                        successful = sum(1 for m in metadata_list if m.chunk_count > 0)
                        failed = completed_count - successful
                        print(f"\n📊 PROGRESO: {completed_count}/{total_files} documentos procesados")
                        print(f"   ✅ Exitosos: {successful} | ❌ Fallidos: {failed} | "
                              f"⏱️ Tiempo transcurrido: {elapsed_time/60:.1f} min\n")
                    
                    if len(chunks) == 0:
                        print(f"   ⚠️ Advertencia: {metadata.file_name} no generó chunks")
                except FutureTimeoutError:
                    # Document took too long, skip it
                    file_name = getattr(file_obj, 'name', 'unknown')
                    print(f"⏱️ [{completed_count}/{total_files}] TIMEOUT: {file_name}")
                    print(f"   └─ Tardó más de {timeout_seconds}s, saltando...")
                    metadata_list.append(DocumentMetadata(
                        file_name=file_name,
                        file_hash="",
                        chunk_count=0,
                        processing_time=timeout_seconds,
                        size_mb=0.0,
                        errors=[f"Timeout: procesamiento excedió {timeout_seconds} segundos"]
                    ))
                    # Cancel the future if possible
                    future.cancel()
                except Exception as e:
                    # Create error metadata
                    import traceback
                    file_name = getattr(file_obj, 'name', 'unknown')
                    error_details = f"{str(e)}\n{traceback.format_exc()}"
                    print(f"❌ [{completed_count}/{total_files}] Error: {file_name}")
                    print(f"   └─ {str(e)}")
                    metadata_list.append(DocumentMetadata(
                        file_name=file_name,
                        file_hash="",
                        chunk_count=0,
                        processing_time=0.0,
                        size_mb=0.0,
                        errors=[str(e)]
                    ))
        
        # Perform comparative analysis if enabled
        comparative_analysis = None
        if enable_comparison and len(metadata_list) > 1:
            comparative_analysis = self._perform_comparative_analysis(
                all_chunks,
                metadata_list
            )
        
        total_time = time.time() - start_time
        
        successful = sum(1 for m in metadata_list if m.chunk_count > 0)
        failed = len(metadata_list) - successful
        
        print(f"\n{'='*60}")
        print(f"📊 RESUMEN DE PROCESAMIENTO")
        print(f"{'='*60}")
        print(f"✅ Documentos procesados: {len(files)}")
        print(f"✅ Exitosos: {successful}")
        print(f"❌ Fallidos: {failed}")
        print(f"📄 Total chunks generados: {len(all_chunks)}")
        print(f"⏱️  Tiempo total: {total_time:.2f} segundos")
        print(f"{'='*60}\n")
        
        if failed > 0:
            print("❌ Documentos con errores:")
            for meta in metadata_list:
                if meta.errors:
                    print(f"  - {meta.file_name}: {', '.join(meta.errors)}")
            print()
        
        return all_chunks, metadata_list, comparative_analysis
    
    def _process_single_document(
        self,
        file_obj
    ) -> tuple[List[Document], DocumentMetadata]:
        """Process a single document and return chunks + metadata."""
        start_time = time.time()
        
        # Handle different file object types
        if isinstance(file_obj, Path):
            file_name = str(file_obj.name) if hasattr(file_obj, 'name') else str(file_obj)
            file_path = file_obj
        elif hasattr(file_obj, 'name'):
            file_name = file_obj.name
            file_path = Path(file_obj.name)
        else:
            file_name = str(file_obj)
            file_path = Path(file_obj) if isinstance(file_obj, (str, Path)) else None
        
        # Log start of processing (this runs in parallel, so multiple may appear at once)
        # Note: This print happens when the thread starts, not when it's queued
        
        try:
            # Calculate file size
            if file_path and file_path.exists():
                size_mb = file_path.stat().st_size / (1024 * 1024)
            elif hasattr(file_obj, 'read'):
                # File object from Gradio
                file_obj.seek(0)
                file_data = file_obj.read()
                size_mb = len(file_data) / (1024 * 1024)
                file_obj.seek(0)
            else:
                size_mb = 0.0
            
            # Process document - handle both file objects and paths
            if file_path and file_path.exists():
                chunks = self.processor.process([file_path])
            elif hasattr(file_obj, 'read'):
                # Reset file pointer
                if hasattr(file_obj, 'seek'):
                    file_obj.seek(0)
                chunks = self.processor.process([file_obj])
            else:
                raise ValueError(f"No se pudo procesar el archivo: {file_name}")
            
            # Get file hash from first chunk metadata
            file_hash = chunks[0].metadata.get('hash', '') if chunks else ''
            
            processing_time = time.time() - start_time
            
            metadata = DocumentMetadata(
                file_name=file_name,
                file_hash=file_hash,
                chunk_count=len(chunks),
                processing_time=processing_time,
                size_mb=size_mb,
                errors=[]
            )
            
            return chunks, metadata
        
        except Exception as e:
            import traceback
            error_msg = f"{str(e)}\n{traceback.format_exc()}"
            print(f"Error procesando {file_name}: {error_msg}")
            processing_time = time.time() - start_time
            metadata = DocumentMetadata(
                file_name=file_name,
                file_hash="",
                chunk_count=0,
                processing_time=processing_time,
                size_mb=0.0,
                errors=[str(e)]
            )
            return [], metadata
    
    def _perform_comparative_analysis(
        self,
        all_chunks: List[Document],
        metadata_list: List[DocumentMetadata]
    ) -> ComparativeAnalysis:
        """Perform comparative analysis across documents."""
        # Group chunks by source file
        chunks_by_file: Dict[str, List[Document]] = {}
        for chunk in all_chunks:
            source = chunk.metadata.get('source', 'unknown')
            if source not in chunks_by_file:
                chunks_by_file[source] = []
            chunks_by_file[source].append(chunk)
        
        # Extract common themes (simple keyword-based approach)
        all_text = " ".join([chunk.page_content for chunk in all_chunks])
        common_themes = self._extract_common_themes(all_text)
        
        # Find unique content per document
        unique_content = {}
        for file_name, chunks in chunks_by_file.items():
            file_text = " ".join([chunk.page_content for chunk in chunks])
            unique_content[file_name] = self._extract_unique_topics(file_text, all_text)
        
        # Detect contradictions (simplified)
        contradictions = self._detect_contradictions(chunks_by_file)
        
        # Statistics
        statistics = {
            "total_documents": len(metadata_list),
            "total_chunks": len(all_chunks),
            "avg_chunks_per_doc": len(all_chunks) / len(metadata_list) if metadata_list else 0,
            "total_size_mb": sum(m.size_mb for m in metadata_list),
            "processing_errors": sum(len(m.errors) for m in metadata_list)
        }
        
        return ComparativeAnalysis(
            common_themes=common_themes,
            unique_content=unique_content,
            contradictions=contradictions,
            statistics=statistics
        )
    
    def _extract_common_themes(self, text: str, top_n: int = 10) -> List[str]:
        """Extract common themes from text."""
        # Simple keyword extraction (in production, use NLP)
        words = text.lower().split()
        # Filter common words
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'must', 'can'}
        filtered_words = [w for w in words if len(w) > 4 and w not in stop_words]
        
        # Count frequencies
        from collections import Counter
        word_counts = Counter(filtered_words)
        
        return [word for word, _ in word_counts.most_common(top_n)]
    
    def _extract_unique_topics(self, file_text: str, all_text: str) -> List[str]:
        """Extract topics unique to this file."""
        file_words = set(file_text.lower().split())
        all_words = set(all_text.lower().split())
        unique_words = file_words - all_words
        
        # Return meaningful unique words
        return [w for w in unique_words if len(w) > 4][:10]
    
    def _detect_contradictions(
        self,
        chunks_by_file: Dict[str, List[Document]]
    ) -> List[Dict[str, str]]:
        """Detect contradictions between documents."""
        # Simplified contradiction detection
        # In production, use more sophisticated NLP
        contradictions = []
        
        # Compare numeric values, dates, etc.
        # This is a placeholder - would implement actual contradiction detection
        if len(chunks_by_file) > 1:
            contradictions.append({
                "type": "potential_contradiction",
                "message": "Multiple documents detected - manual review recommended"
            })
        
        return contradictions

