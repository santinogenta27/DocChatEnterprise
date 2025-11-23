from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List

from docling.document_converter import DocumentConverter
from langchain_core.documents import Document
from langchain_text_splitters import MarkdownHeaderTextSplitter

from .config import AppConfig
from .utils import load_pickle, read_bytes, save_pickle, sha256_bytes


@dataclass(slots=True)
class CachedChunks:
    chunks: List[Document]
    timestamp: float


class DocumentProcessor:
    """Parse, chunk, and cache uploaded documents with Docling."""

    SUPPORTED_EXT = {".pdf", ".docx", ".txt", ".md"}

    def __init__(self, config: AppConfig):
        self.config = config
        # Usar DocumentConverter sin forzar OCR - extraerá texto nativo primero
        self.converter = DocumentConverter()
        self.splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=config.headers_to_split_on,
            strip_headers=False,
        )

    def validate_files(self, files: Iterable) -> None:
        total_bytes = 0
        for file_obj in files:
            data = read_bytes(file_obj)
            total_bytes += len(data)
        limit = self.config.max_total_upload_mb * 1024 * 1024
        if total_bytes > limit:
            raise ValueError(
                f"Los archivos superan el máximo permitido de {self.config.max_total_upload_mb} MB."
            )

    def process(self, files: List) -> List[Document]:
        if not files:
            raise ValueError("Debes subir al menos un documento.")
        self.validate_files(files)

        total_files = len(files)
        if total_files > 1:
            print(f"\n{'='*60}")
            print(f"📄 PROCESANDO {total_files} DOCUMENTOS")
            print(f"{'='*60}\n")
        else:
            file_name = getattr(files[0], "name", "documento")
            print(f"\n📄 Procesando documento: {file_name}\n")

        unique_chunks: dict[str, Document] = {}
        for idx, file_obj in enumerate(files, 1):
            # Obtener nombre original si está disponible (para archivos de Google Drive)
            original_name = getattr(file_obj, "original_name", None)
            file_name = original_name if original_name else getattr(file_obj, "name", "documento")
            suffix = Path(file_name).suffix.lower()
            if suffix not in self.SUPPORTED_EXT:
                raise ValueError(
                    f"Formato {suffix} no soportado. Usa PDF, DOCX, TXT o Markdown."
                )
            
            if total_files > 1:
                print(f"[{idx}/{total_files}] Procesando: {file_name}")
            
            data = read_bytes(file_obj)
            file_hash = sha256_bytes(data)
            cache_path = self.config.cache_dir / f"{file_hash}.pkl"

            if cache_path.exists() and self._is_cache_valid(cache_path):
                cached = load_pickle(cache_path)
                chunks = cached.chunks
                # Actualizar el source de los chunks si tenemos un nombre original disponible
                # Esto es importante para archivos de Google Drive que pueden tener nombres temporales en caché
                if original_name:
                    for chunk in chunks:
                        if chunk.metadata.get("source"):
                            chunk.metadata["source"] = file_name
                if total_files > 1:
                    print(f"   ✅ Usando caché: {len(chunks)} chunks")
            else:
                chunks = self._process_bytes(data, file_name, file_hash)
                save_pickle(cache_path, CachedChunks(chunks=chunks, timestamp=time.time()))

            for chunk_idx, chunk in enumerate(chunks):
                chunk_id = f"{file_hash}-{chunk_idx}"
                if chunk_id not in unique_chunks:
                    unique_chunks[chunk_id] = chunk

        total_chunks = len(unique_chunks)
        if total_files > 1:
            print(f"\n✅ Procesamiento completado: {total_chunks} chunks totales\n")
        else:
            print(f"✅ Procesamiento completado: {total_chunks} chunks generados\n")

        return list(unique_chunks.values())

    def _process_bytes(self, data: bytes, file_name: str, file_hash: str) -> List[Document]:
        """Run Docling and split markdown into LangChain documents."""
        import tempfile

        suffix = Path(file_name).suffix.lower()
        
        # Para PDFs, intentar primero extracción de texto nativo sin OCR
        if suffix == ".pdf":
            return self._process_pdf_with_fallback(data, file_name, file_hash)
        
        # Para otros formatos, usar Docling normal
        print(f"   📄 Procesando {suffix.upper()}: {file_name} ({len(data) / (1024*1024):.2f} MB)")
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(data)
            tmp.flush()
            tmp_path = tmp.name
        try:
            print(f"   🔄 Convirtiendo con Docling (esto puede tardar varios minutos)...")
            import time
            start_time = time.time()
            result = self.converter.convert(tmp_path)
            elapsed = time.time() - start_time
            print(f"   ✅ Conversión completada en {elapsed:.1f} segundos")
        except Exception as e:
            print(f"   ❌ Error en Docling para {file_name}: {e}")
            raise
        finally:
            Path(tmp_path).unlink(missing_ok=True)
        
        return self._extract_documents_from_result(result, file_name, file_hash)
    
    def _process_pdf_with_fallback(self, data: bytes, file_name: str, file_hash: str) -> List[Document]:
        """Procesar PDF usando solo PyPDF2. Si falla, se salta el documento y continúa."""
        import tempfile
        
        file_size_mb = len(data) / (1024*1024)
        print(f"   📄 Procesando PDF: {file_name} ({file_size_mb:.2f} MB)")
        
        # ESTRATEGIA OPTIMIZADA: PyPDF2 primero (10-100x más rápido)
        # Solo usar Docling si PyPDF2 falla o no extrae suficiente texto
        try:
            print(f"   ⚡ Intentando extracción rápida con PyPDF2...")
            import time
            start_time = time.time()
            chunks = self._extract_text_native_pdf(data, file_name, file_hash)
            elapsed = time.time() - start_time
            
            # Si PyPDF2 extrajo texto suficiente, usarlo
            if chunks and len(chunks) > 0:
                total_text = sum(len(chunk.page_content) for chunk in chunks)
                if total_text > 100:  # Al menos 100 caracteres extraídos
                    print(f"   ✅ PyPDF2 completado en {elapsed:.1f}s → {len(chunks)} chunks")
                    return chunks
                else:
                    print(f"   ⚠️ PyPDF2 extrajo poco texto ({total_text} chars)")
                    print(f"   ⏭️ Saltando este documento y continuando con el siguiente...")
                    return []  # Retornar lista vacía para continuar con siguiente documento
            else:
                print(f"   ⚠️ PyPDF2 no extrajo texto")
                print(f"   ⏭️ Saltando este documento y continuando con el siguiente...")
                return []  # Retornar lista vacía para continuar con siguiente documento
        except Exception as pypdf_error:
            print(f"   ⚠️ PyPDF2 falló: {str(pypdf_error)[:80]}")
            print(f"   ⏭️ Saltando este documento y continuando con el siguiente...")
            return []  # Retornar lista vacía para continuar con siguiente documento
    
    def _extract_text_native_pdf(self, data: bytes, file_name: str, file_hash: str) -> List[Document]:
        """Extraer texto nativo de PDF usando PyPDF2 (método rápido)."""
        try:
            import PyPDF2
            from io import BytesIO
            
            pdf_file = BytesIO(data)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            total_pages = len(pdf_reader.pages)
            
            text_parts = []
            for page_num, page in enumerate(pdf_reader.pages, 1):
                try:
                    text = page.extract_text()
                    if text.strip():
                        text_parts.append(f"# Página {page_num}\n\n{text}")
                    # Mostrar progreso cada 10 páginas
                    if page_num % 10 == 0 or page_num == total_pages:
                        print(f"      📄 Página {page_num}/{total_pages} procesada...", end='\r')
                except Exception as e:
                    # Continuar con siguiente página si una falla
                    continue
            
            print()  # Nueva línea después del progreso
            
            if not text_parts:
                return []
            
            markdown = "\n\n".join(text_parts)
            return self._split_markdown_to_documents(markdown, file_name, file_hash)
        except ImportError:
            print("   ⚠️ PyPDF2 no está instalado")
            return []
        except Exception as e:
            print(f"   ❌ Error en PyPDF2: {str(e)[:80]}")
            return []
    
    def _extract_documents_from_result(self, result, file_name: str, file_hash: str) -> List[Document]:
        """Extraer documentos del resultado de Docling."""
        try:
            markdown = result.document.export_to_markdown()
            if not markdown or not markdown.strip():
                print(f"⚠️ Advertencia: {file_name} no generó contenido markdown")
                return []
        except Exception as e:
            print(f"❌ Error exportando markdown para {file_name}: {e}")
            return []
        
        return self._split_markdown_to_documents(markdown, file_name, file_hash)
    
    def _split_markdown_to_documents(self, markdown: str, file_name: str, file_hash: str) -> List[Document]:
        """Dividir markdown en documentos LangChain."""
        chunks = self.splitter.split_text(markdown)
        documents: List[Document] = []
        for idx, chunk in enumerate(chunks):
            metadata = chunk.metadata or {}
            metadata.update(
                {
                    "source": file_name,
                    "hash": file_hash,
                    "chunk_index": idx,
                }
            )
            documents.append(Document(page_content=chunk.page_content.strip(), metadata=metadata))
        
        filtered_docs = [doc for doc in documents if doc.page_content]
        if len(filtered_docs) > 0:
            print(f"   ✅ {file_name}: {len(filtered_docs)} chunks generados de {len(chunks)} secciones")
        else:
            print(f"   ⚠️ {file_name}: No se generaron chunks válidos")
        return filtered_docs

    def _is_cache_valid(self, cache_path: Path) -> bool:
        cached = load_pickle(cache_path)
        age_days = (time.time() - cached.timestamp) / (60 * 60 * 24)
        return age_days <= self.config.cache_expire_days

