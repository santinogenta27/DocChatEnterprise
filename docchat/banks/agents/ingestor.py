"""
Agent 1: Ingestor - Procesa y particiona documentos.
"""

from __future__ import annotations

import zipfile
from pathlib import Path
from typing import Dict, Any, List
import logging

try:
    from unstructured.partition.auto import partition
    from unstructured.chunking.title import chunk_by_title
    UNSTRUCTURED_AVAILABLE = True
except ImportError as e:
    UNSTRUCTURED_AVAILABLE = False
    logging.warning(f"unstructured no disponible: {e}. Algunas funcionalidades pueden estar limitadas.")

try:
    import pytesseract
    from pdf2image import convert_from_path
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False
    logging.warning("OCR no disponible")

from .base_agent import BaseBanksAgent
from docchat.config import AppConfig
try:
    from docchat.document_processor import DocumentProcessor
except ImportError:
    DocumentProcessor = None

logger = logging.getLogger(__name__)


class IngestorAgent(BaseBanksAgent):
    """Agente que ingiere y procesa documentos masivamente."""
    
    def __init__(self, config: AppConfig):
        super().__init__(config, "ingestor")
        self.document_processor = DocumentProcessor(config) if DocumentProcessor else None
        self.supported_formats = {'.pdf', '.docx', '.doc', '.txt', '.md', '.xlsx', '.xls', '.png', '.jpg', '.jpeg'}
    
    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Procesa documentos desde carpeta/ZIP/URL.
        
        Input state:
            - input_path: str (carpeta, ZIP, o URL)
            - documents: List[Dict] (opcional, si ya están cargados)
        
        Output state:
            - processed_documents: List[Dict] con chunks y metadata
            - total_chunks: int
            - errors: List[str]
        """
        input_path = state.get("input_path")
        documents = state.get("documents", [])
        
        processed_docs = []
        errors = []
        total_chunks = 0
        
        try:
            # Si ya hay documentos cargados, usarlos
            if documents:
                docs_to_process = documents
            elif input_path:
                # Procesar desde path
                path = Path(input_path)
                if path.is_file() and path.suffix.lower() == '.zip':
                    docs_to_process = self._extract_zip(path)
                elif path.is_dir():
                    docs_to_process = self._scan_directory(path)
                else:
                    docs_to_process = [str(path)]
            else:
                raise ValueError("No se proporcionó input_path ni documents")
            
            # Procesar cada documento
            for doc_path in docs_to_process:
                try:
                    result = self._process_document(doc_path)
                    processed_docs.append(result)
                    total_chunks += result.get("chunks_count", 0)
                except Exception as e:
                    error_msg = f"Error procesando {doc_path}: {str(e)}"
                    logger.error(error_msg)
                    errors.append(error_msg)
            
            # Log de auditoría
            self.log_audit(
                action="document_ingestion",
                input_data={"input_path": str(input_path), "doc_count": len(docs_to_process)},
                output_data={"processed": len(processed_docs), "total_chunks": total_chunks, "errors": len(errors)}
            )
            
        except Exception as e:
            error_msg = f"Error en ingesta: {str(e)}"
            logger.error(error_msg)
            errors.append(error_msg)
        
        state["processed_documents"] = processed_docs
        state["total_chunks"] = total_chunks
        state["ingestion_errors"] = errors
        
        return state
    
    def _extract_zip(self, zip_path: Path) -> List[str]:
        """Extrae archivos de un ZIP."""
        extracted_files = []
        extract_dir = Path(self.config.cache_dir) / "extracted" / zip_path.stem
        extract_dir.mkdir(parents=True, exist_ok=True)
        
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)
            for file_path in extract_dir.rglob('*'):
                if file_path.is_file() and file_path.suffix.lower() in self.supported_formats:
                    extracted_files.append(str(file_path))
        
        return extracted_files
    
    def _scan_directory(self, directory: Path) -> List[str]:
        """Escanea un directorio buscando documentos."""
        files = []
        for ext in self.supported_formats:
            files.extend(directory.rglob(f"*{ext}"))
        return [str(f) for f in files if f.is_file()]
    
    def _process_document(self, doc_path: str) -> Dict[str, Any]:
        """Procesa un documento individual."""
        path = Path(doc_path)
        
        # Validar que el archivo existe
        if not path.exists():
            raise FileNotFoundError(f"Archivo no encontrado: {doc_path}")
        
        # Validar que es un archivo (no directorio)
        if not path.is_file():
            raise ValueError(f"La ruta no es un archivo: {doc_path}")
        
        # Intentar con unstructured primero
        if UNSTRUCTURED_AVAILABLE and path.suffix.lower() in {'.pdf', '.docx', '.doc', '.txt', '.md'}:
            try:
                elements = partition(str(path))
                chunks = chunk_by_title(elements, max_characters=2000, combine_text_under_n_chars=2000)
                
                return {
                    "path": str(path),
                    "type": path.suffix.lower(),
                    "chunks": [{"text": str(chunk), "metadata": chunk.metadata.to_dict()} for chunk in chunks],
                    "chunks_count": len(chunks),
                    "method": "unstructured"
                }
            except Exception as e:
                logger.warning(f"Unstructured falló para {doc_path}, usando fallback: {e}")
        
        # Fallback: usar DocumentProcessor del sistema base
        if self.document_processor:
            try:
                result = self.document_processor.process_document(str(path))
                return {
                    "path": str(path),
                    "type": path.suffix.lower(),
                    "chunks": result.get("chunks", []),
                    "chunks_count": len(result.get("chunks", [])),
                    "method": "fallback"
                }
            except Exception as e:
                logger.warning(f"DocumentProcessor falló para {doc_path}: {e}")
        
        # Último recurso: OCR si es imagen
        if OCR_AVAILABLE and path.suffix.lower() in {'.png', '.jpg', '.jpeg'}:
            try:
                text = pytesseract.image_to_string(str(path), lang='spa+eng')
                return {
                    "path": str(path),
                    "type": "image_ocr",
                    "chunks": [{"text": text, "metadata": {}}],
                    "chunks_count": 1,
                    "method": "ocr"
                }
            except Exception as e2:
                logger.error(f"OCR falló para {doc_path}: {e2}")
                raise Exception(f"OCR falló: {e2}")
        
        # Si llegamos aquí, ningún método funcionó
        raise Exception(f"No se pudo procesar el documento {doc_path}. Formatos soportados: PDF, DOCX, DOC, TXT, MD, XLSX, XLS, PNG, JPG, JPEG")

