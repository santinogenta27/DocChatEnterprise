"""
Schema Annotations - Sistema de anotaciones para esquemas de datos
Permite a JARVIS entender mejor las estructuras de datos, bases de datos, tablas, columnas, etc.
"""

from __future__ import annotations

import json
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from pathlib import Path
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class SchemaObjectType(str, Enum):
    """Tipos de objetos de esquema que se pueden anotar."""
    DATABASE = "database"
    TABLE = "table"
    COLUMN = "column"
    VIEW = "view"
    PROCEDURE = "procedure"
    FUNCTION = "function"
    INDEX = "index"
    CONSTRAINT = "constraint"
    RELATIONSHIP = "relationship"
    GROUP = "group"  # Para agrupar tablas relacionadas (ej: "ONLINE RETAIL SALES")


@dataclass
class SchemaAnnotation:
    """Anotación de un objeto de esquema."""
    annotation_id: str
    object_type: SchemaObjectType
    object_name: str  # Nombre del objeto (tabla, columna, etc.)
    schema_name: Optional[str] = None  # Schema/database name
    description: str = ""  # Descripción en lenguaje natural
    category: Optional[str] = None  # Categoría (ej: "ONLINE RETAIL SALES", "PAYROLL", etc.)
    group: Optional[str] = None  # Grupo al que pertenece
    data_type: Optional[str] = None  # Tipo de dato (para columnas)
    sample_data: Optional[str] = None  # Ejemplo de datos (JSON string o texto)
    business_meaning: Optional[str] = None  # Significado de negocio
    usage_notes: Optional[str] = None  # Notas de uso
    related_objects: List[str] = field(default_factory=list)  # IDs de objetos relacionados
    tags: List[str] = field(default_factory=list)  # Tags para búsqueda
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    created_by: str = "user"
    metadata: Dict[str, Any] = field(default_factory=dict)


class SchemaAnnotationManager:
    """
    Gestiona anotaciones de esquemas para mejorar la comprensión de JARVIS.
    
    Permite:
    - Anotar bases de datos, tablas, columnas con descripciones en lenguaje natural
    - Agrupar objetos relacionados (ej: todas las tablas de "PAYROLL")
    - Proporcionar ejemplos de datos para que JARVIS entienda mejor
    - Mejorar la precisión de queries y respuestas de JARVIS
    """
    
    def __init__(self, storage_dir: Path):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.annotations_file = self.storage_dir / "schema_annotations.json"
        self.annotations: Dict[str, SchemaAnnotation] = {}
        self._load_annotations()
    
    def _load_annotations(self):
        """Carga anotaciones guardadas."""
        if self.annotations_file.exists():
            try:
                with open(self.annotations_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for ann_data in data.get("annotations", []):
                        ann = SchemaAnnotation(**ann_data)
                        self.annotations[ann.annotation_id] = ann
                logger.info(f"✅ [Schema Annotations] {len(self.annotations)} anotaciones cargadas")
            except Exception as e:
                logger.error(f"❌ [Schema Annotations] Error cargando anotaciones: {e}")
    
    def _save_annotations(self):
        """Guarda anotaciones."""
        try:
            data = {
                "annotations": [asdict(ann) for ann in self.annotations.values()],
                "last_updated": time.time()
            }
            with open(self.annotations_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"❌ [Schema Annotations] Error guardando anotaciones: {e}")
    
    def add_annotation(
        self,
        object_type: SchemaObjectType,
        object_name: str,
        description: str,
        schema_name: Optional[str] = None,
        category: Optional[str] = None,
        group: Optional[str] = None,
        data_type: Optional[str] = None,
        sample_data: Optional[str] = None,
        business_meaning: Optional[str] = None,
        usage_notes: Optional[str] = None,
        tags: Optional[List[str]] = None,
        annotation_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Agrega una nueva anotación de esquema.
        
        Returns:
            annotation_id: ID de la anotación creada
        """
        import uuid
        
        if annotation_id is None:
            annotation_id = f"{object_type.value}_{object_name}_{int(time.time())}"
        
        annotation = SchemaAnnotation(
            annotation_id=annotation_id,
            object_type=object_type,
            object_name=object_name,
            schema_name=schema_name,
            description=description,
            category=category,
            group=group,
            data_type=data_type,
            sample_data=sample_data,
            business_meaning=business_meaning,
            usage_notes=usage_notes,
            tags=tags or [],
            metadata=metadata or {}
        )
        
        self.annotations[annotation_id] = annotation
        self._save_annotations()
        
        logger.info(f"✅ [Schema Annotations] Anotación agregada: {object_name} ({object_type.value})")
        return annotation_id
    
    def update_annotation(
        self,
        annotation_id: str,
        **updates
    ) -> bool:
        """Actualiza una anotación existente."""
        if annotation_id not in self.annotations:
            return False
        
        annotation = self.annotations[annotation_id]
        
        # Actualizar campos permitidos
        for key, value in updates.items():
            if hasattr(annotation, key) and key not in ["annotation_id", "created_at", "created_by"]:
                setattr(annotation, key, value)
        
        annotation.updated_at = time.time()
        self._save_annotations()
        
        logger.info(f"✅ [Schema Annotations] Anotación actualizada: {annotation_id}")
        return True
    
    def remove_annotation(self, annotation_id: str) -> bool:
        """Elimina una anotación."""
        if annotation_id in self.annotations:
            del self.annotations[annotation_id]
            self._save_annotations()
            logger.info(f"✅ [Schema Annotations] Anotación eliminada: {annotation_id}")
            return True
        return False
    
    def get_annotation(self, annotation_id: str) -> Optional[SchemaAnnotation]:
        """Obtiene una anotación por ID."""
        return self.annotations.get(annotation_id)
    
    def find_annotations(
        self,
        object_name: Optional[str] = None,
        object_type: Optional[SchemaObjectType] = None,
        schema_name: Optional[str] = None,
        category: Optional[str] = None,
        group: Optional[str] = None,
        tag: Optional[str] = None
    ) -> List[SchemaAnnotation]:
        """Busca anotaciones por criterios."""
        results = []
        
        for ann in self.annotations.values():
            if object_name and ann.object_name != object_name:
                continue
            if object_type and ann.object_type != object_type:
                continue
            if schema_name and ann.schema_name != schema_name:
                continue
            if category and ann.category != category:
                continue
            if group and ann.group != group:
                continue
            if tag and tag not in ann.tags:
                continue
            
            results.append(ann)
        
        return results
    
    def get_schema_context(
        self,
        object_name: str,
        object_type: Optional[SchemaObjectType] = None
    ) -> str:
        """
        Obtiene contexto enriquecido de un objeto de esquema para JARVIS.
        
        Returns:
            Contexto en formato texto que JARVIS puede usar para entender mejor el objeto.
        """
        annotations = self.find_annotations(
            object_name=object_name,
            object_type=object_type
        )
        
        if not annotations:
            return f"Objeto '{object_name}' sin anotaciones disponibles."
        
        context_parts = []
        
        for ann in annotations:
            context = f"**{ann.object_name}** ({ann.object_type.value})"
            
            if ann.schema_name:
                context += f" en schema '{ann.schema_name}'"
            
            if ann.description:
                context += f"\nDescripción: {ann.description}"
            
            if ann.category:
                context += f"\nCategoría: {ann.category}"
            
            if ann.group:
                context += f"\nGrupo: {ann.group}"
            
            if ann.business_meaning:
                context += f"\nSignificado de negocio: {ann.business_meaning}"
            
            if ann.data_type:
                context += f"\nTipo de dato: {ann.data_type}"
            
            if ann.sample_data:
                context += f"\nEjemplo de datos: {ann.sample_data}"
            
            if ann.usage_notes:
                context += f"\nNotas de uso: {ann.usage_notes}"
            
            if ann.tags:
                context += f"\nTags: {', '.join(ann.tags)}"
            
            context_parts.append(context)
        
        return "\n\n".join(context_parts)
    
    def get_group_context(self, group_name: str) -> str:
        """Obtiene contexto de un grupo completo de objetos relacionados."""
        annotations = self.find_annotations(group=group_name)
        
        if not annotations:
            return f"Grupo '{group_name}' sin anotaciones."
        
        context = f"**Grupo: {group_name}**\n\n"
        context += f"Este grupo contiene {len(annotations)} objetos relacionados:\n\n"
        
        for ann in annotations:
            context += f"- **{ann.object_name}** ({ann.object_type.value}): {ann.description or 'Sin descripción'}\n"
        
        return context
    
    def get_all_groups(self) -> List[str]:
        """Obtiene lista de todos los grupos definidos."""
        groups = set()
        for ann in self.annotations.values():
            if ann.group:
                groups.add(ann.group)
        return sorted(list(groups))
    
    def get_all_categories(self) -> List[str]:
        """Obtiene lista de todas las categorías definidas."""
        categories = set()
        for ann in self.annotations.values():
            if ann.category:
                categories.add(ann.category)
        return sorted(list(categories))
    
    def list_annotations(
        self,
        object_type: Optional[SchemaObjectType] = None
    ) -> List[Dict[str, Any]]:
        """Lista todas las anotaciones (o filtradas por tipo)."""
        results = []
        
        for ann in self.annotations.values():
            if object_type and ann.object_type != object_type:
                continue
            
            results.append({
                "annotation_id": ann.annotation_id,
                "object_type": ann.object_type.value,
                "object_name": ann.object_name,
                "schema_name": ann.schema_name,
                "description": ann.description,
                "category": ann.category,
                "group": ann.group,
                "tags": ann.tags,
                "created_at": ann.created_at,
                "updated_at": ann.updated_at
            })
        
        return results
    
    def get_statistics(self) -> Dict[str, Any]:
        """Obtiene estadísticas de las anotaciones."""
        stats = {
            "total_annotations": len(self.annotations),
            "by_type": {},
            "by_category": {},
            "by_group": {},
            "total_groups": len(self.get_all_groups()),
            "total_categories": len(self.get_all_categories())
        }
        
        for ann in self.annotations.values():
            # Por tipo
            type_key = ann.object_type.value
            stats["by_type"][type_key] = stats["by_type"].get(type_key, 0) + 1
            
            # Por categoría
            if ann.category:
                stats["by_category"][ann.category] = stats["by_category"].get(ann.category, 0) + 1
            
            # Por grupo
            if ann.group:
                stats["by_group"][ann.group] = stats["by_group"].get(ann.group, 0) + 1
        
        return stats

