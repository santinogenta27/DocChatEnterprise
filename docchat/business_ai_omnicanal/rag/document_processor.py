"""Procesador de documentos usando PyPDF2 para Business AI Omnicanal RAG.

Procesa PDFs usando solo PyPDF2 (sin Docling, sin APIs externas).
Los documentos se procesan y guardan localmente, sin llamadas a API durante el procesamiento.
"""

from __future__ import annotations

import hashlib
import pickle
from pathlib import Path
from typing import List, Any, Optional
from datetime import datetime, timedelta

try:
    from langchain_core.documents import Document
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    Document = None
    RecursiveCharacterTextSplitter = None

# Constantes
CACHE_EXPIRE_DAYS = 30  # Cache válido por 30 días
MAX_FILE_SIZE_MB = 100
MAX_TOTAL_SIZE_MB = 500

# Configuración de chunking (como Meta: fragmentación inteligente por unidades de significado)
CHUNK_SIZE = 700  # tokens (~525 caracteres)
CHUNK_OVERLAP = 50  # tokens (~38 caracteres)


class DocumentProcessor:
    """Procesador de documentos usando solo PyPDF2 (sin APIs externas).
    
    Procesa PDFs localmente y guarda chunks sin generar embeddings.
    Los embeddings se generan solo cuando se consulta (lazy loading).
    """
    
    def __init__(self, cache_dir: Optional[Path] = None):
        """Inicializa el procesador de documentos.
        
        Args:
            cache_dir: Directorio para cache de documentos procesados
        """
        if not LANGCHAIN_AVAILABLE:
            raise ImportError(
                "LangChain no está instalado. Instala con: pip install langchain langchain-core langchain-text-splitters"
            )
        
        self.cache_dir = cache_dir or Path("docchat/business_ai_omnicanal/rag/cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Inicializar text splitter (chunking inteligente por unidades de significado)
        # Meta usa fragmentación por unidades de significado, no por páginas
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""]  # Priorizar párrafos completos
        )
    
    def validate_files(self, files: List[Any]) -> None:
        """Valida que los archivos no excedan el tamaño máximo.
        
        Args:
            files: Lista de archivos a validar
            
        Raises:
            ValueError: Si el tamaño total excede el límite
        """
        total_size = 0
        for file in files:
            if isinstance(file, (str, Path)):
                path = Path(file)
            else:
                # Gradio file object
                path = Path(getattr(file, "name", ""))
            
            if path.exists():
                size_mb = path.stat().st_size / (1024 * 1024)
                total_size += size_mb
                
                if size_mb > MAX_FILE_SIZE_MB:
                    raise ValueError(
                        f"Archivo {path.name} excede el tamaño máximo de {MAX_FILE_SIZE_MB}MB"
                    )
        
        if total_size > MAX_TOTAL_SIZE_MB:
            raise ValueError(
                f"Tamaño total de archivos ({total_size:.2f}MB) excede el límite de {MAX_TOTAL_SIZE_MB}MB"
            )
    
    def process(self, files: List[Any]) -> List[Document]:
        """Procesa archivos y retorna documentos chunked (SIN llamadas a API).
        
        Args:
            files: Lista de archivos (paths o objetos de Gradio)
            
        Returns:
            Lista de documentos chunked (sin embeddings aún)
        """
        if not files:
            return []
        
        self.validate_files(files)
        
        all_chunks = []
        seen_hashes = set()
        
        for file in files:
            try:
                # Obtener path del archivo
                if isinstance(file, (str, Path)):
                    file_path = Path(file)
                else:
                    # Gradio file object
                    file_path = Path(getattr(file, "name", ""))
                
                if not file_path.exists():
                    print(f"⚠️ Archivo no encontrado: {file_path}")
                    continue
                
                # Generar hash para cache
                file_hash = self._generate_hash(file_path)
                cache_path = self.cache_dir / f"{file_hash}.pkl"
                
                # Intentar cargar desde cache
                if cache_path.exists() and self._is_cache_valid(cache_path):
                    chunks = self._load_from_cache(cache_path)
                    print(f"✅ Cargado desde cache: {file_path.name} ({len(chunks)} chunks)")
                else:
                    # Procesar archivo (SOLO PyPDF2, SIN APIs)
                    chunks = self._process_file(file_path, file_hash)
                    
                    # Guardar en cache
                    if chunks:
                        self._save_to_cache(chunks, cache_path)
                        print(f"✅ Procesado: {file_path.name} ({len(chunks)} chunks)")
                
                # Evitar duplicados
                for chunk in chunks:
                    chunk_hash = hashlib.sha256(chunk.page_content.encode()).hexdigest()
                    if chunk_hash not in seen_hashes:
                        seen_hashes.add(chunk_hash)
                        all_chunks.append(chunk)
                        
            except Exception as e:
                print(f"⚠️ Error procesando {file_path.name}: {e}")
                import traceback
                traceback.print_exc()
                continue
        
        print(f"\n✅ Total: {len(all_chunks)} chunks únicos procesados (SIN llamadas a API)")
        return all_chunks
    
    def _process_file(self, file_path: Path, file_hash: str) -> List[Document]:
        """Procesa un archivo individual usando SOLO PyPDF2 (sin APIs externas).
        
        Args:
            file_path: Path al archivo
            file_hash: Hash del archivo para metadata
            
        Returns:
            Lista de documentos chunked
        """
        ext = file_path.suffix.lower()
        
        # Solo procesar formatos soportados
        if ext not in [".pdf", ".txt", ".md"]:
            print(f"⚠️ Formato no soportado: {ext} (solo PDF, TXT, MD)")
            return []
        
        # Para PDFs: usar SOLO PyPDF2 (sin Docling, sin APIs)
        if ext == ".pdf":
            return self._process_pdf_pypdf2_only(file_path, file_hash)
        
        # Para texto: leer directamente
        elif ext in [".txt", ".md"]:
            return self._process_text_file(file_path, file_hash)
        
        return []
    
    def _process_pdf_pypdf2_only(self, file_path: Path, file_hash: str) -> List[Document]:
        """Procesar PDF usando SOLO PyPDF2 (rápido, sin APIs, sin Docling)."""
        import time
        
        file_size_mb = file_path.stat().st_size / (1024 * 1024)
        print(f"   📄 Procesando PDF con PyPDF2: {file_path.name} ({file_size_mb:.2f} MB)")
        
        try:
            import PyPDF2
            
            start_time = time.time()
            
            with open(file_path, "rb") as f:
                pdf_reader = PyPDF2.PdfReader(f)
                total_pages = len(pdf_reader.pages)
                
                # Extraer texto de todas las páginas
                text_parts = []
                for page_num, page in enumerate(pdf_reader.pages, 1):
                    try:
                        text = page.extract_text()
                        if text.strip():
                            # Fragmentación inteligente: mantener párrafos completos
                            text_parts.append(text.strip())
                        # Mostrar progreso cada 10 páginas
                        if page_num % 10 == 0 or page_num == total_pages:
                            print(f"      📄 Página {page_num}/{total_pages} procesada...", end='\r')
                    except Exception as e:
                        # Continuar con siguiente página si una falla
                        print(f"      ⚠️ Error en página {page_num}: {e}")
                        continue
                
                print()  # Nueva línea después del progreso
                
                if not text_parts:
                    print(f"   ⚠️ No se extrajo texto del PDF")
                    return []
                
                # Combinar todo el texto (fragmentación inteligente como Meta)
                full_text = "\n\n".join(text_parts)
                
                # Dividir en chunks usando text splitter (unidades de significado)
                # Meta divide por unidades de significado, no por páginas
                text_chunks = self.splitter.split_text(full_text)
                
                # Convertir a Document objects de LangChain
                documents = []
                for idx, chunk_text in enumerate(text_chunks):
                    if chunk_text.strip():  # Solo chunks con contenido
                        doc = Document(
                            page_content=chunk_text.strip(),
                            metadata={
                                "source": str(file_path),
                                "file_name": file_path.name,
                                "file_hash": file_hash,
                                "chunk_index": idx,
                                "total_chunks": len(text_chunks),
                                "total_pages": total_pages,
                                "processing_method": "pypdf2_only"  # Sin APIs
                            }
                        )
                        documents.append(doc)
                
                elapsed = time.time() - start_time
                print(f"   ✅ PyPDF2 completado en {elapsed:.1f}s → {len(documents)} chunks (fragmentación inteligente)")
                
                return documents
                
        except ImportError:
            print(f"   ❌ PyPDF2 no está instalado. Instala con: pip install PyPDF2")
            return []
        except Exception as e:
            error_msg = str(e).lower()
            if "pycryptodome" in error_msg or "aes" in error_msg or "encrypted" in error_msg:
                print(f"   ❌ PDF encriptado detectado. PyPDF2 requiere PyCryptodome para desencriptar.")
                print(f"   💡 Instala con: pip install pycryptodome")
            else:
                print(f"   ❌ Error procesando PDF: {str(e)[:100]}")
            return []
    
    def _process_text_file(self, file_path: Path, file_hash: str) -> List[Document]:
        """Procesa archivo de texto (TXT, MD) directamente."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            if not content.strip():
                return []
            
            # Dividir en chunks usando text splitter
            text_chunks = self.splitter.split_text(content)
            
            # Convertir a Document objects
            documents = []
            for idx, chunk_text in enumerate(text_chunks):
                if chunk_text.strip():
                    doc = Document(
                        page_content=chunk_text.strip(),
                        metadata={
                            "source": str(file_path),
                            "file_name": file_path.name,
                            "file_hash": file_hash,
                            "chunk_index": idx,
                            "total_chunks": len(text_chunks),
                            "processing_method": "text_direct"  # Sin APIs
                        }
                    )
                    documents.append(doc)
            
            print(f"   ✅ Archivo de texto procesado: {len(documents)} chunks")
            return documents
            
        except Exception as e:
            print(f"   ❌ Error procesando archivo de texto: {e}")
            return []
    
    def _generate_hash(self, file_path: Path) -> str:
        """Genera hash SHA-256 del contenido del archivo.
        
        Args:
            file_path: Path al archivo
            
        Returns:
            Hash hexadecimal
        """
        with open(file_path, "rb") as f:
            content = f.read()
        return hashlib.sha256(content).hexdigest()
    
    def _save_to_cache(self, chunks: List[Document], cache_path: Path) -> None:
        """Guarda chunks procesados en cache (SIN embeddings).
        
        Args:
            chunks: Lista de documentos chunked
            cache_path: Path donde guardar el cache
        """
        try:
            with open(cache_path, "wb") as f:
                pickle.dump({
                    "chunks": chunks,
                    "timestamp": datetime.now(),
                }, f)
        except Exception as e:
            print(f"⚠️ Error guardando cache: {e}")
    
    def _load_from_cache(self, cache_path: Path) -> List[Document]:
        """Carga chunks desde cache.
        
        Args:
            cache_path: Path al archivo de cache
            
        Returns:
            Lista de documentos chunked
        """
        try:
            with open(cache_path, "rb") as f:
                data = pickle.load(f)
                return data.get("chunks", [])
        except Exception as e:
            print(f"⚠️ Error cargando cache: {e}")
            return []
    
    def _is_cache_valid(self, cache_path: Path) -> bool:
        """Verifica si el cache es válido (no expirado).
        
        Args:
            cache_path: Path al archivo de cache
            
        Returns:
            True si el cache es válido
        """
        try:
            mtime = datetime.fromtimestamp(cache_path.stat().st_mtime)
            age = datetime.now() - mtime
            return age < timedelta(days=CACHE_EXPIRE_DAYS)
        except Exception:
            return False
