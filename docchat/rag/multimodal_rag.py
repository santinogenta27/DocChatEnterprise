"""
Multi-modal RAG: Soporte para imágenes, tablas y diagramas además de texto.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

from langchain_core.documents import Document
from PIL import Image
import base64
import io


class MultiModalRAG:
    """
    RAG que soporta múltiples modos: texto, imágenes, tablas, diagramas.
    """
    
    def __init__(self):
        self.supported_image_formats = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"}
        self.supported_table_formats = {".csv", ".xlsx", ".xls"}
    
    def process_image(self, image_path: Path) -> Dict[str, any]:
        """
        Procesa imagen y extrae información.
        """
        try:
            img = Image.open(image_path)
            
            # Información básica
            info = {
                "type": "image",
                "format": img.format,
                "size": img.size,
                "mode": img.mode,
                "path": str(image_path)
            }
            
            # OCR básico (si hay texto en imagen)
            # En producción, usar Tesseract, EasyOCR, o modelo de visión
            try:
                # Intentar extraer texto (requiere pytesseract)
                # text = pytesseract.image_to_string(img)
                # info["extracted_text"] = text
                pass
            except Exception:
                pass
            
            # Convertir a base64 para almacenamiento
            buffered = io.BytesIO()
            img.save(buffered, format=img.format or "PNG")
            img_base64 = base64.b64encode(buffered.getvalue()).decode()
            info["base64"] = img_base64[:1000]  # Limitar tamaño
            
            return info
        
        except Exception as e:
            return {"type": "image", "error": str(e)}
    
    def process_table(self, table_path: Path) -> Dict[str, any]:
        """
        Procesa tabla (CSV, Excel) y extrae información.
        """
        try:
            import pandas as pd
            
            if table_path.suffix == ".csv":
                df = pd.read_csv(table_path)
            else:
                df = pd.read_excel(table_path)
            
            info = {
                "type": "table",
                "rows": len(df),
                "columns": list(df.columns),
                "data_preview": df.head(10).to_dict(orient="records"),
                "path": str(table_path)
            }
            
            # Generar descripción textual de la tabla
            description = f"Tabla con {len(df)} filas y {len(df.columns)} columnas: {', '.join(df.columns[:5])}"
            info["description"] = description
            
            return info
        
        except Exception as e:
            return {"type": "table", "error": str(e)}
    
    def create_multimodal_document(
        self,
        text: str,
        images: List[Path] = None,
        tables: List[Path] = None,
        metadata: Dict = None
    ) -> Document:
        """
        Crea documento multi-modal combinando texto, imágenes y tablas.
        """
        content_parts = [text]
        
        # Procesar imágenes
        image_data = []
        if images:
            for img_path in images:
                img_info = self.process_image(img_path)
                image_data.append(img_info)
                content_parts.append(f"[Imagen: {img_path.name}]")
        
        # Procesar tablas
        table_data = []
        if tables:
            for table_path in tables:
                table_info = self.process_table(table_path)
                table_data.append(table_info)
                content_parts.append(f"[Tabla: {table_path.name} - {table_info.get('description', '')}]")
        
        # Crear documento
        document = Document(
            page_content="\n\n".join(content_parts),
            metadata={
                **(metadata or {}),
                "multimodal": True,
                "images": len(image_data),
                "tables": len(table_data),
                "image_data": image_data,
                "table_data": table_data
            }
        )
        
        return document
    
    def extract_multimodal_context(self, document: Document) -> Dict[str, any]:
        """Extrae contexto multi-modal de documento."""
        context = {
            "text": document.page_content,
            "images": [],
            "tables": []
        }
        
        if document.metadata.get("multimodal"):
            context["images"] = document.metadata.get("image_data", [])
            context["tables"] = document.metadata.get("table_data", [])
        
        return context

