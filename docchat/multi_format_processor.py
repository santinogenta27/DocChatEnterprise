"""
Multi-Format Document Processor - Procesador de documentos que soporta todos los formatos de texto.

Soporta:
- Documentos: PDF, DOC/DOCX, ODT, RTF, TXT, MD, LaTeX, HTML, EPUB, MOBI
- Datos estructurados: CSV, TSV, JSON, XML, YAML, INI, LOG
- Presentaciones: PPT/PPTX, ODP, Keynote
- Hojas de cálculo: XLS/XLSX
- Y más formatos de texto
"""

from __future__ import annotations

import time
import json
import csv
import xml.etree.ElementTree as ET
import configparser
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional
import io

# YAML es opcional
try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False

from docling.document_converter import DocumentConverter
from langchain_core.documents import Document
from langchain_text_splitters import MarkdownHeaderTextSplitter

from .config import AppConfig
from .utils import load_pickle, read_bytes, save_pickle, sha256_bytes


@dataclass(slots=True)
class CachedChunks:
    chunks: List[Document]
    timestamp: float


class MultiFormatProcessor:
    """
    Procesador de documentos que soporta todos los formatos de texto.
    Extiende DocumentProcessor con soporte para formatos adicionales.
    """
    
    # Todos los formatos soportados
    SUPPORTED_EXT = {
        # Documentos
        ".pdf", ".doc", ".docx", ".odt", ".rtf", ".txt", ".md", ".tex", ".html", ".htm",
        ".epub", ".mobi",
        # Datos estructurados
        ".csv", ".tsv", ".json", ".xml", ".yaml", ".yml", ".ini", ".log",
        # Presentaciones
        ".ppt", ".pptx", ".odp", ".key",  # Keynote
        # Hojas de cálculo
        ".xls", ".xlsx",
        # Subtítulos y transcripciones
        ".srt", ".vtt",  # Subtítulos
        # Código fuente y texto programado
        ".py", ".js", ".ts", ".java", ".cpp", ".c", ".h", ".cs", ".php", ".rb", ".go", ".rs",
        ".sh", ".bash", ".ps1", ".bat", ".cmd",  # Scripts
        # Otros formatos de texto
        ".gdoc", ".zip",  # Google Docs export, ZIPs con contenido
        ".eml", ".msg",  # Emails (archivos)
        ".sql",  # SQL
        ".r", ".R",  # R
        ".m", ".matlab",  # MATLAB
    }
    
    # Formatos que Docling puede procesar directamente
    DOCLING_FORMATS = {
        ".pdf", ".docx", ".odt", ".rtf", ".html", ".htm", ".pptx", ".odp", ".xlsx", ".vtt"
    }
    
    # Formatos que requieren procesamiento especial
    SPECIAL_FORMATS = {
        ".txt", ".md", ".tex", ".csv", ".tsv", ".json", ".xml", ".yaml", ".yml", 
        ".ini", ".log", ".ppt", ".xls", ".mobi", ".epub", ".srt", ".key",
        ".eml", ".msg", ".sql"
    }
    
    # Formatos de código fuente (procesar como texto)
    CODE_FORMATS = {
        ".py", ".js", ".ts", ".java", ".cpp", ".c", ".h", ".cs", ".php", ".rb", ".go", ".rs",
        ".sh", ".bash", ".ps1", ".bat", ".cmd", ".r", ".R", ".m", ".matlab"
    }
    
    def __init__(self, config: AppConfig):
        self.config = config
        self.converter = DocumentConverter()
        self.splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=config.headers_to_split_on,
            strip_headers=False,
        )
    
    def validate_files(self, files: Iterable) -> None:
        """Valida que los archivos no excedan el límite de tamaño."""
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
        """Procesa múltiples archivos de diferentes formatos."""
        if not files:
            raise ValueError("Debes subir al menos un documento.")
        self.validate_files(files)
        
        total_files = len(files)
        if total_files > 1:
            print(f"\n{'='*60}")
            print(f"📄 PROCESANDO {total_files} DOCUMENTOS (MULTI-FORMATO)")
            print(f"{'='*60}\n")
        else:
            file_name = getattr(files[0], "name", "documento")
            print(f"\n📄 Procesando documento: {file_name}\n")
        
        unique_chunks: dict[str, Document] = {}
        for idx, file_obj in enumerate(files, 1):
            original_name = getattr(file_obj, "original_name", None)
            file_name = original_name if original_name else getattr(file_obj, "name", "documento")
            suffix = Path(file_name).suffix.lower()
            
            if suffix not in self.SUPPORTED_EXT:
                print(f"   ⚠️ Formato {suffix} no soportado, saltando: {file_name}")
                continue
            
            if total_files > 1:
                print(f"[{idx}/{total_files}] Procesando: {file_name} ({suffix})")
            
            data = read_bytes(file_obj)
            file_hash = sha256_bytes(data)
            cache_path = self.config.cache_dir / f"{file_hash}.pkl"
            
            if cache_path.exists() and self._is_cache_valid(cache_path):
                cached = load_pickle(cache_path)
                chunks = cached.chunks
                if original_name:
                    for chunk in chunks:
                        if chunk.metadata.get("source"):
                            chunk.metadata["source"] = file_name
                if total_files > 1:
                    print(f"   ✅ Usando caché: {len(chunks)} chunks")
            else:
                chunks = self._process_file(data, file_name, file_hash, suffix)
                if chunks:
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
    
    def _process_file(self, data: bytes, file_name: str, file_hash: str, suffix: str) -> List[Document]:
        """Procesa un archivo según su formato."""
        # Formatos que Docling puede procesar
        if suffix in self.DOCLING_FORMATS:
            return self._process_with_docling(data, file_name, file_hash, suffix)
        
        # Formatos especiales que requieren procesamiento manual
        elif suffix in self.SPECIAL_FORMATS:
            return self._process_special_format(data, file_name, file_hash, suffix)
        
        else:
            print(f"   ⚠️ Formato {suffix} no tiene procesador específico, intentando como texto plano")
            return self._process_as_text(data, file_name, file_hash)
    
    def _process_with_docling(self, data: bytes, file_name: str, file_hash: str, suffix: str) -> List[Document]:
        """Procesa archivo usando Docling."""
        import tempfile
        
        file_size_mb = len(data) / (1024*1024)
        print(f"   📄 Procesando con Docling: {file_name} ({file_size_mb:.2f} MB)")
        
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(data)
            tmp.flush()
            tmp_path = tmp.name
        
        try:
            print(f"   🔄 Convirtiendo con Docling...")
            start_time = time.time()
            result = self.converter.convert(tmp_path)
            elapsed = time.time() - start_time
            print(f"   ✅ Conversión completada en {elapsed:.1f} segundos")
        except Exception as e:
            print(f"   ❌ Error en Docling: {e}")
            return []
        finally:
            Path(tmp_path).unlink(missing_ok=True)
        
        return self._extract_documents_from_result(result, file_name, file_hash)
    
    def _process_special_format(self, data: bytes, file_name: str, file_hash: str, suffix: str) -> List[Document]:
        """Procesa formatos especiales (CSV, JSON, XML, etc.)."""
        try:
            text_content = data.decode('utf-8', errors='ignore')
            
            if suffix == ".csv":
                return self._process_csv(text_content, file_name, file_hash)
            elif suffix == ".tsv":
                return self._process_tsv(text_content, file_name, file_hash)
            elif suffix == ".json":
                return self._process_json(text_content, file_name, file_hash)
            elif suffix == ".xml":
                return self._process_xml(text_content, file_name, file_hash)
            elif suffix in [".yaml", ".yml"]:
                return self._process_yaml(text_content, file_name, file_hash)
            elif suffix == ".ini":
                return self._process_ini(text_content, file_name, file_hash)
            elif suffix == ".log":
                return self._process_log(text_content, file_name, file_hash)
            elif suffix in [".txt", ".md", ".tex"]:
                return self._process_as_text(data, file_name, file_hash)
            elif suffix == ".mobi":
                # MOBI es complejo, intentar como texto o usar Docling si está disponible
                print(f"   ⚠️ MOBI requiere procesamiento especial, intentando como texto")
                return self._process_as_text(data, file_name, file_hash)
            elif suffix == ".epub":
                # EPUB - procesar con librería especializada o extraer contenido
                return self._process_epub(data, file_name, file_hash)
            elif suffix in [".ppt", ".xls"]:
                # Formatos antiguos de Office, intentar con Docling o como binario
                print(f"   ⚠️ Formato antiguo {suffix}, intentando con Docling")
                return self._process_with_docling(data, file_name, file_hash, suffix)
            elif suffix == ".key":
                # Keynote - intentar con Docling o como texto
                print(f"   ⚠️ Keynote (.key), intentando con Docling")
                return self._process_with_docling(data, file_name, file_hash, suffix)
            elif suffix == ".srt":
                # Subtítulos SRT
                return self._process_subtitles(data, file_name, file_hash, suffix)
            elif suffix == ".vtt":
                # VTT puede ser procesado por Docling, pero si falla usar procesador especial
                try:
                    return self._process_with_docling(data, file_name, file_hash, suffix)
                except Exception:
                    return self._process_subtitles(data, file_name, file_hash, suffix)
            elif suffix in [".eml", ".msg"]:
                # Archivos de email
                return self._process_email_file(data, file_name, file_hash, suffix)
            elif suffix == ".sql":
                # SQL
                return self._process_code_file(data, file_name, file_hash, suffix)
            else:
                return self._process_as_text(data, file_name, file_hash)
        except Exception as e:
            print(f"   ❌ Error procesando {suffix}: {e}")
            return []
    
    def _process_csv(self, content: str, file_name: str, file_hash: str) -> List[Document]:
        """Procesa archivo CSV."""
        try:
            csv_reader = csv.reader(io.StringIO(content))
            rows = list(csv_reader)
            
            if not rows:
                return []
            
            # Convertir a texto estructurado
            text_parts = [f"# CSV: {file_name}\n\n"]
            text_parts.append(f"**Columnas:** {', '.join(rows[0])}\n\n")
            text_parts.append("**Datos:**\n\n")
            
            for idx, row in enumerate(rows[1:21], 1):  # Primeras 20 filas
                row_text = " | ".join(str(cell) for cell in row)
                text_parts.append(f"{idx}. {row_text}\n")
            
            if len(rows) > 21:
                text_parts.append(f"\n... y {len(rows) - 21} filas más")
            
            markdown = "".join(text_parts)
            return self._split_markdown_to_documents(markdown, file_name, file_hash)
        except Exception as e:
            print(f"   ❌ Error procesando CSV: {e}")
            return []
    
    def _process_tsv(self, content: str, file_name: str, file_hash: str) -> List[Document]:
        """Procesa archivo TSV."""
        try:
            tsv_reader = csv.reader(io.StringIO(content), delimiter='\t')
            rows = list(tsv_reader)
            
            if not rows:
                return []
            
            text_parts = [f"# TSV: {file_name}\n\n"]
            text_parts.append(f"**Columnas:** {', '.join(rows[0])}\n\n")
            text_parts.append("**Datos:**\n\n")
            
            for idx, row in enumerate(rows[1:21], 1):
                row_text = " | ".join(str(cell) for cell in row)
                text_parts.append(f"{idx}. {row_text}\n")
            
            if len(rows) > 21:
                text_parts.append(f"\n... y {len(rows) - 21} filas más")
            
            markdown = "".join(text_parts)
            return self._split_markdown_to_documents(markdown, file_name, file_hash)
        except Exception as e:
            print(f"   ❌ Error procesando TSV: {e}")
            return []
    
    def _process_json(self, content: str, file_name: str, file_hash: str) -> List[Document]:
        """Procesa archivo JSON."""
        try:
            data = json.loads(content)
            
            # Convertir JSON a texto estructurado
            text_parts = [f"# JSON: {file_name}\n\n"]
            
            if isinstance(data, dict):
                text_parts.append("**Estructura JSON:**\n\n")
                text_parts.append(self._json_to_markdown(data, max_depth=3))
            elif isinstance(data, list):
                text_parts.append(f"**Array con {len(data)} elementos:**\n\n")
                for idx, item in enumerate(data[:20], 1):
                    text_parts.append(f"{idx}. {json.dumps(item, ensure_ascii=False, indent=2)[:500]}\n")
                if len(data) > 20:
                    text_parts.append(f"\n... y {len(data) - 20} elementos más")
            else:
                text_parts.append(f"**Contenido:**\n\n{json.dumps(data, ensure_ascii=False, indent=2)}")
            
            markdown = "".join(text_parts)
            return self._split_markdown_to_documents(markdown, file_name, file_hash)
        except Exception as e:
            print(f"   ❌ Error procesando JSON: {e}")
            return []
    
    def _json_to_markdown(self, obj: dict, prefix: str = "", max_depth: int = 3, current_depth: int = 0) -> str:
        """Convierte JSON a markdown estructurado."""
        if current_depth >= max_depth:
            return f"{prefix}...\n"
        
        lines = []
        for key, value in list(obj.items())[:50]:  # Limitar a 50 keys
            if isinstance(value, dict):
                lines.append(f"{prefix}**{key}:**\n")
                lines.append(self._json_to_markdown(value, prefix + "  ", max_depth, current_depth + 1))
            elif isinstance(value, list):
                lines.append(f"{prefix}**{key}:** [{len(value)} elementos]\n")
                if value and isinstance(value[0], dict):
                    lines.append(self._json_to_markdown(value[0], prefix + "  ", max_depth, current_depth + 1))
            else:
                value_str = str(value)[:200]
                lines.append(f"{prefix}**{key}:** {value_str}\n")
        
        return "".join(lines)
    
    def _process_xml(self, content: str, file_name: str, file_hash: str) -> List[Document]:
        """Procesa archivo XML."""
        try:
            root = ET.fromstring(content)
            
            text_parts = [f"# XML: {file_name}\n\n"]
            text_parts.append(f"**Elemento raíz:** {root.tag}\n\n")
            text_parts.append("**Estructura:**\n\n")
            text_parts.append(self._xml_to_markdown(root, max_depth=3))
            
            markdown = "".join(text_parts)
            return self._split_markdown_to_documents(markdown, file_name, file_hash)
        except Exception as e:
            print(f"   ❌ Error procesando XML: {e}")
            return []
    
    def _xml_to_markdown(self, element: ET.Element, prefix: str = "", max_depth: int = 3, current_depth: int = 0) -> str:
        """Convierte XML a markdown."""
        if current_depth >= max_depth:
            return f"{prefix}...\n"
        
        lines = []
        lines.append(f"{prefix}**<{element.tag}>**\n")
        
        if element.text and element.text.strip():
            text = element.text.strip()[:200]
            lines.append(f"{prefix}  Texto: {text}\n")
        
        for child in list(element)[:20]:  # Limitar a 20 hijos
            lines.append(self._xml_to_markdown(child, prefix + "  ", max_depth, current_depth + 1))
        
        return "".join(lines)
    
    def _process_yaml(self, content: str, file_name: str, file_hash: str) -> List[Document]:
        """Procesa archivo YAML."""
        if not YAML_AVAILABLE:
            print(f"   ⚠️ YAML no está instalado, procesando como texto plano")
            return self._process_as_text(content.encode('utf-8'), file_name, file_hash)
        
        try:
            data = yaml.safe_load(content)
            
            text_parts = [f"# YAML: {file_name}\n\n"]
            
            if isinstance(data, dict):
                text_parts.append("**Estructura YAML:**\n\n")
                text_parts.append(yaml.dump(data, default_flow_style=False, allow_unicode=True)[:5000])
            else:
                text_parts.append(f"**Contenido:**\n\n{yaml.dump(data, allow_unicode=True)}")
            
            markdown = "".join(text_parts)
            return self._split_markdown_to_documents(markdown, file_name, file_hash)
        except Exception as e:
            print(f"   ❌ Error procesando YAML: {e}")
            return []
    
    def _process_ini(self, content: str, file_name: str, file_hash: str) -> List[Document]:
        """Procesa archivo INI."""
        try:
            config = configparser.ConfigParser()
            config.read_string(content)
            
            text_parts = [f"# INI: {file_name}\n\n"]
            
            for section in config.sections():
                text_parts.append(f"## [{section}]\n\n")
                for key, value in config.items(section):
                    text_parts.append(f"**{key}:** {value}\n")
                text_parts.append("\n")
            
            markdown = "".join(text_parts)
            return self._split_markdown_to_documents(markdown, file_name, file_hash)
        except Exception as e:
            print(f"   ❌ Error procesando INI: {e}")
            return []
    
    def _process_log(self, content: str, file_name: str, file_hash: str) -> List[Document]:
        """Procesa archivo LOG."""
        lines = content.split('\n')
        
        text_parts = [f"# LOG: {file_name}\n\n"]
        text_parts.append(f"**Total de líneas:** {len(lines)}\n\n")
        text_parts.append("**Contenido (primeras 100 líneas):**\n\n")
        
        for line in lines[:100]:
            text_parts.append(f"{line}\n")
        
        if len(lines) > 100:
            text_parts.append(f"\n... y {len(lines) - 100} líneas más")
        
        markdown = "".join(text_parts)
        return self._split_markdown_to_documents(markdown, file_name, file_hash)
    
    def _process_as_text(self, data: bytes, file_name: str, file_hash: str) -> List[Document]:
        """Procesa archivo como texto plano."""
        try:
            text = data.decode('utf-8', errors='ignore')
            if not text.strip():
                return []
            
            # Agregar header según extensión
            suffix = Path(file_name).suffix.lower()
            if suffix == ".md":
                markdown = text
            elif suffix == ".tex":
                markdown = f"# LaTeX: {file_name}\n\n```latex\n{text}\n```"
            else:
                markdown = f"# {file_name}\n\n{text}"
            
            return self._split_markdown_to_documents(markdown, file_name, file_hash)
        except Exception as e:
            print(f"   ❌ Error procesando como texto: {e}")
            return []
    
    def _extract_documents_from_result(self, result, file_name: str, file_hash: str) -> List[Document]:
        """Extrae documentos del resultado de Docling."""
        try:
            markdown = result.document.export_to_markdown()
            if not markdown or not markdown.strip():
                print(f"⚠️ Advertencia: {file_name} no generó contenido markdown")
                return []
        except Exception as e:
            print(f"❌ Error exportando markdown: {e}")
            return []
        
        return self._split_markdown_to_documents(markdown, file_name, file_hash)
    
    def _split_markdown_to_documents(self, markdown: str, file_name: str, file_hash: str) -> List[Document]:
        """Divide markdown en documentos LangChain."""
        chunks = self.splitter.split_text(markdown)
        documents: List[Document] = []
        for idx, chunk in enumerate(chunks):
            metadata = chunk.metadata or {}
            metadata.update({
                "source": file_name,
                "hash": file_hash,
                "chunk_index": idx,
            })
            documents.append(Document(page_content=chunk.page_content.strip(), metadata=metadata))
        
        filtered_docs = [doc for doc in documents if doc.page_content]
        if len(filtered_docs) > 0:
            print(f"   ✅ {file_name}: {len(filtered_docs)} chunks generados")
        else:
            print(f"   ⚠️ {file_name}: No se generaron chunks válidos")
        return filtered_docs
    
    def _process_code_file(self, data: bytes, file_name: str, file_hash: str, suffix: str) -> List[Document]:
        """Procesa archivo de código fuente."""
        try:
            text = data.decode('utf-8', errors='ignore')
            if not text.strip():
                return []
            
            # Detectar lenguaje por extensión
            lang_map = {
                ".py": "python", ".js": "javascript", ".ts": "typescript", ".java": "java",
                ".cpp": "cpp", ".c": "c", ".h": "c", ".cs": "csharp", ".php": "php",
                ".rb": "ruby", ".go": "go", ".rs": "rust", ".sh": "bash", ".bash": "bash",
                ".ps1": "powershell", ".bat": "batch", ".cmd": "batch", ".r": "r", ".R": "r",
                ".m": "matlab", ".matlab": "matlab", ".sql": "sql"
            }
            lang = lang_map.get(suffix, "text")
            
            markdown = f"# Código: {file_name}\n\n**Lenguaje:** {lang}\n\n```{lang}\n{text}\n```"
            return self._split_markdown_to_documents(markdown, file_name, file_hash)
        except Exception as e:
            print(f"   ❌ Error procesando código: {e}")
            return []
    
    def _process_subtitles(self, data: bytes, file_name: str, file_hash: str, suffix: str) -> List[Document]:
        """Procesa archivos de subtítulos (SRT, VTT)."""
        try:
            text = data.decode('utf-8', errors='ignore')
            lines = text.split('\n')
            
            text_parts = [f"# Subtítulos: {file_name}\n\n"]
            text_parts.append(f"**Formato:** {suffix.upper()}\n\n")
            text_parts.append("**Contenido:**\n\n")
            
            # Para SRT, parsear estructura básica
            if suffix == ".srt":
                i = 0
                while i < len(lines):
                    line = lines[i].strip()
                    if line.isdigit():  # Número de secuencia
                        i += 1
                        if i < len(lines):
                            timecode = lines[i].strip()
                            i += 1
                            subtitle_text = []
                            while i < len(lines) and lines[i].strip():
                                subtitle_text.append(lines[i].strip())
                                i += 1
                            if subtitle_text:
                                text_parts.append(f"**{timecode}**\n{''.join(subtitle_text)}\n\n")
                    i += 1
            else:  # VTT
                text_parts.append(text[:5000])  # Primeros 5000 caracteres
            
            markdown = "".join(text_parts)
            return self._split_markdown_to_documents(markdown, file_name, file_hash)
        except Exception as e:
            print(f"   ❌ Error procesando subtítulos: {e}")
            return []
    
    def _process_epub(self, data: bytes, file_name: str, file_hash: str) -> List[Document]:
        """Procesa archivo EPUB."""
        try:
            # Intentar usar ebooklib si está disponible
            try:
                import ebooklib
                from ebooklib import epub
                from bs4 import BeautifulSoup
                
                book = epub.read_epub(io.BytesIO(data))
                text_parts = [f"# EPUB: {file_name}\n\n"]
                
                # Extraer metadata
                title = book.get_metadata('DC', 'title')
                if title:
                    text_parts.append(f"**Título:** {title[0][0]}\n\n")
                
                # Extraer contenido de todos los capítulos
                text_parts.append("**Contenido:**\n\n")
                
                for item in book.get_items():
                    if item.get_type() == ebooklib.ITEM_DOCUMENT:
                        soup = BeautifulSoup(item.get_content(), 'html.parser')
                        text = soup.get_text()
                        if text.strip():
                            text_parts.append(f"{text}\n\n")
                
                markdown = "".join(text_parts)
                return self._split_markdown_to_documents(markdown, file_name, file_hash)
            except ImportError:
                # Si ebooklib no está disponible, intentar extraer como ZIP
                print(f"   ⚠️ ebooklib no está instalado, intentando extraer como ZIP")
                return self._process_epub_as_zip(data, file_name, file_hash)
        except Exception as e:
            print(f"   ❌ Error procesando EPUB: {e}")
            # Fallback: intentar como ZIP
            try:
                return self._process_epub_as_zip(data, file_name, file_hash)
            except Exception as e2:
                print(f"   ❌ Error en fallback ZIP: {e2}")
                return []
    
    def _process_epub_as_zip(self, data: bytes, file_name: str, file_hash: str) -> List[Document]:
        """Procesa EPUB como ZIP (EPUB es básicamente un ZIP)."""
        try:
            import zipfile
            from html.parser import HTMLParser
            
            text_parts = [f"# EPUB: {file_name}\n\n"]
            text_parts.append("**Contenido extraído del EPUB:**\n\n")
            
            with zipfile.ZipFile(io.BytesIO(data), 'r') as zip_ref:
                # Buscar archivos HTML/XHTML dentro del EPUB
                for file_info in zip_ref.namelist():
                    if file_info.endswith(('.html', '.xhtml', '.htm')) and 'META-INF' not in file_info:
                        try:
                            content = zip_ref.read(file_info)
                            text = content.decode('utf-8', errors='ignore')
                            
                            # Extraer texto básico de HTML
                            class TextExtractor(HTMLParser):
                                def __init__(self):
                                    super().__init__()
                                    self.text = []
                                
                                def handle_data(self, data):
                                    if data.strip():
                                        self.text.append(data.strip())
                            
                            parser = TextExtractor()
                            parser.feed(text)
                            extracted_text = ' '.join(parser.text)
                            
                            if extracted_text:
                                text_parts.append(f"**{file_info}:**\n{extracted_text[:2000]}\n\n")
                        except Exception:
                            continue
                
                # Si no hay HTML, buscar archivos de texto
                if len(text_parts) == 2:  # Solo header
                    for file_info in zip_ref.namelist():
                        if file_info.endswith('.txt') and 'META-INF' not in file_info:
                            try:
                                content = zip_ref.read(file_info)
                                text = content.decode('utf-8', errors='ignore')
                                if text.strip():
                                    text_parts.append(f"**{file_info}:**\n{text[:5000]}\n\n")
                            except Exception:
                                continue
            
            if len(text_parts) > 2:  # Hay contenido extraído
                markdown = "".join(text_parts)
                return self._split_markdown_to_documents(markdown, file_name, file_hash)
            else:
                print(f"   ⚠️ No se pudo extraer contenido del EPUB")
                return []
        except Exception as e:
            print(f"   ❌ Error procesando EPUB como ZIP: {e}")
            return []
    
    def _process_email_file(self, data: bytes, file_name: str, file_hash: str, suffix: str) -> List[Document]:
        """Procesa archivos de email (.eml, .msg)."""
        try:
            if suffix == ".eml":
                # EML es texto plano con headers y body
                text = data.decode('utf-8', errors='ignore')
                text_parts = [f"# Email: {file_name}\n\n"]
                
                # Extraer headers básicos
                lines = text.split('\n')
                in_body = False
                body_lines = []
                
                for line in lines:
                    if line.strip() == "" and not in_body:
                        in_body = True
                        continue
                    if in_body:
                        body_lines.append(line)
                    elif ':' in line and not in_body:
                        if any(header in line.lower() for header in ['from:', 'to:', 'subject:', 'date:']):
                            text_parts.append(f"**{line.strip()}**\n")
                
                if body_lines:
                    text_parts.append("\n**Cuerpo:**\n\n")
                    text_parts.append("\n".join(body_lines[:100]))  # Primeras 100 líneas
                
                markdown = "".join(text_parts)
                return self._split_markdown_to_documents(markdown, file_name, file_hash)
            else:  # .msg - formato binario de Outlook, intentar como texto
                print(f"   ⚠️ .msg requiere procesamiento especial, intentando como texto")
                return self._process_as_text(data, file_name, file_hash)
        except Exception as e:
            print(f"   ❌ Error procesando email: {e}")
            return []
    
    def _is_cache_valid(self, cache_path: Path) -> bool:
        """Verifica si el caché es válido."""
        cached = load_pickle(cache_path)
        age_days = (time.time() - cached.timestamp) / (60 * 60 * 24)
        return age_days <= self.config.cache_expire_days

