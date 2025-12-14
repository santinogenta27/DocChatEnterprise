"""Base Workflow - Clase base para todos los workflows."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime

from ..orchestrator.decision_orchestrator import WorkflowResult
from ..actions.action_layer import ActionLayer
from ..orchestrator.decision_orchestrator import ClassifiedDocument


@dataclass
class WorkflowResult:
    """Resultado de ejecución de workflow (alias para compatibilidad)."""
    workflow_name: str
    document_type: str
    success: bool
    summary: str
    extracted_fields: Dict[str, Any]
    actions_performed: List[Dict[str, Any]]
    confidence: float
    errors: List[str]
    timestamp: datetime


class BaseWorkflow(ABC):
    """
    Clase base para todos los workflows.
    
    Cada workflow debe implementar:
    - extract_fields(): Extraer campos específicos del documento
    - validate(): Validar datos extraídos
    - execute_actions(): Ejecutar acciones automáticas
    """
    
    def __init__(self, config: Any, llm: Any, action_layer: ActionLayer):
        """
        Inicializa el workflow.
        
        Args:
            config: Configuración de la aplicación
            llm: Instancia del LLM
            action_layer: Capa de acciones
        """
        self.config = config
        self.llm = llm
        self.action_layer = action_layer
        self.workflow_name = self.__class__.__name__.replace("Workflow", "").lower()
    
    @abstractmethod
    def extract_fields(self, documents: List[ClassifiedDocument]) -> Dict[str, Any]:
        """
        Extrae campos específicos del tipo de documento.
        
        Args:
            documents: Documentos clasificados
            
        Returns:
            Diccionario con campos extraídos
        """
        pass
    
    @abstractmethod
    def validate(self, extracted_fields: Dict[str, Any]) -> tuple[bool, List[str]]:
        """
        Valida los campos extraídos.
        
        Args:
            extracted_fields: Campos extraídos
            
        Returns:
            Tuple (es_válido, lista_de_errores)
        """
        pass
    
    @abstractmethod
    def execute_actions(self, extracted_fields: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Ejecuta acciones automáticas basadas en los campos extraídos.
        
        Args:
            extracted_fields: Campos extraídos y validados
            
        Returns:
            Lista de acciones ejecutadas
        """
        pass
    
    def execute(self, documents: List[ClassifiedDocument]) -> WorkflowResult:
        """
        Ejecuta el workflow completo.
        
        Args:
            documents: Documentos clasificados a procesar
            
        Returns:
            Resultado del workflow
        """
        errors = []
        actions_performed = []
        
        try:
            # 1. Extraer campos
            extracted_fields = self.extract_fields(documents)
            
            # 2. Validar
            is_valid, validation_errors = self.validate(extracted_fields)
            if not is_valid:
                errors.extend(validation_errors)
            
            # 3. Ejecutar acciones (solo si es válido o si hay campos extraídos)
            if extracted_fields or not errors:
                try:
                    actions_performed = self.execute_actions(extracted_fields)
                except Exception as e:
                    errors.append(f"Error ejecutando acciones: {str(e)}")
            
            # 4. Generar resumen
            summary = self._generate_summary(extracted_fields, actions_performed, errors)
            
            # 5. Calcular confianza
            confidence = self._calculate_confidence(extracted_fields, errors)
            
            return WorkflowResult(
                workflow_name=self.workflow_name,
                document_type=documents[0].doc_type.value if documents else "unknown",
                success=len(errors) == 0,
                summary=summary,
                extracted_fields=extracted_fields,
                actions_performed=actions_performed,
                confidence=confidence,
                errors=errors,
                timestamp=datetime.now()
            )
            
        except Exception as e:
            return WorkflowResult(
                workflow_name=self.workflow_name,
                document_type=documents[0].doc_type.value if documents else "unknown",
                success=False,
                summary=f"Error ejecutando workflow: {str(e)}",
                extracted_fields={},
                actions_performed=[],
                confidence=0.0,
                errors=[str(e)],
                timestamp=datetime.now()
            )
    
    def _generate_summary(
        self,
        extracted_fields: Dict[str, Any],
        actions_performed: List[Dict[str, Any]],
        errors: List[str]
    ) -> str:
        """Genera un resumen del procesamiento."""
        summary_parts = [
            f"Workflow: {self.workflow_name}",
            f"Campos extraídos: {len(extracted_fields)}",
            f"Acciones ejecutadas: {len(actions_performed)}"
        ]
        
        if errors:
            summary_parts.append(f"Errores: {len(errors)}")
        
        return " | ".join(summary_parts)
    
    def _calculate_confidence(
        self,
        extracted_fields: Dict[str, Any],
        errors: List[str]
    ) -> float:
        """Calcula el nivel de confianza del procesamiento."""
        if errors:
            return max(0.0, 1.0 - (len(errors) * 0.2))
        
        if not extracted_fields:
            return 0.5
        
        # Más campos = mayor confianza (hasta cierto punto)
        field_count = len(extracted_fields)
        return min(1.0, 0.5 + (field_count * 0.1))

