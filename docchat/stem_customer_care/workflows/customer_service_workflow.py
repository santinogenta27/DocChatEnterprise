"""Workflows/Playbooks para Customer Service.

El agent NO improvisa. Siempre sigue flujos definidos:
Problema → Verificar → Actuar → Confirmar → Cerrar
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any, Optional, List
from enum import Enum


class WorkflowStep(str, Enum):
    """Pasos de un workflow."""
    RECOGNIZE = "recognize"  # Reconocer el problema
    VERIFY = "verify"  # Verificar información
    ACT = "act"  # Ejecutar acción
    CONFIRM = "confirm"  # Confirmar resultado
    CLOSE = "close"  # Cerrar caso


@dataclass
class Workflow:
    """Define un workflow/playbook para resolver un tipo de caso."""
    workflow_id: str
    name: str
    description: str
    steps: List[Dict[str, Any]]
    conditions: Optional[Dict[str, Any]] = None
    
    def get_next_step(self, current_step: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Obtiene el siguiente paso del workflow."""
        if not current_step:
            return self.steps[0] if self.steps else None
        
        current_index = next(
            (i for i, step in enumerate(self.steps) if step.get("step_id") == current_step),
            -1
        )
        
        if current_index < 0 or current_index >= len(self.steps) - 1:
            return None
        
        return self.steps[current_index + 1]


class CustomerServiceWorkflowManager:
    """Gestor de workflows para customer service."""
    
    def __init__(self):
        self.workflows: Dict[str, Workflow] = {}
        self._load_default_workflows()
    
    def _load_default_workflows(self):
        """Carga workflows por defecto."""
        # Workflow genérico de resolución
        generic_workflow = Workflow(
            workflow_id="generic_resolution",
            name="Resolución Genérica",
            description="Workflow estándar para resolver casos",
            steps=[
                {
                    "step_id": "recognize",
                    "step_type": WorkflowStep.RECOGNIZE,
                    "instruction": "Resumir el problema del cliente y demostrar comprensión",
                    "required": True
                },
                {
                    "step_id": "verify",
                    "step_type": WorkflowStep.VERIFY,
                    "instruction": "Verificar información necesaria (consultar RAG, tickets, historial)",
                    "required": True
                },
                {
                    "step_id": "act",
                    "step_type": WorkflowStep.ACT,
                    "instruction": "Ejecutar acción para resolver el problema",
                    "required": True
                },
                {
                    "step_id": "confirm",
                    "step_type": WorkflowStep.CONFIRM,
                    "instruction": "Confirmar que la acción se ejecutó y el problema está resuelto",
                    "required": True
                },
                {
                    "step_id": "close",
                    "step_type": WorkflowStep.CLOSE,
                    "instruction": "Cerrar el caso de forma clara y definitiva",
                    "required": True
                }
            ]
        )
        
        self.workflows["generic_resolution"] = generic_workflow
    
    def get_workflow(self, workflow_id: str) -> Optional[Workflow]:
        """Obtiene un workflow por ID."""
        return self.workflows.get(workflow_id)
    
    def get_workflow_for_case(self, case_type: str) -> Workflow:
        """Obtiene el workflow apropiado para un tipo de caso."""
        # Por ahora retornamos el workflow genérico
        # En el futuro se pueden tener workflows específicos por tipo de caso
        return self.workflows.get("generic_resolution")

