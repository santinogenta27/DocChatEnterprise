"""Motor de Guías Paso a Paso (Troubleshooting) para Business AI Support.

Permite crear guías interactivas paso a paso para resolver problemas comunes.
"""

from __future__ import annotations

from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from datetime import datetime
import json
try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False


class StepType(str, Enum):
    """Tipo de paso en la guía."""
    QUESTION = "question"  # Pregunta al usuario
    INFORMATION = "information"  # Información/instrucción
    DECISION = "decision"  # Punto de decisión (sí/no, múltiple opción)
    ACTION = "action"  # Acción que el usuario debe realizar
    RAG_QUERY = "rag_query"  # Consulta al RAG para información


@dataclass
class TroubleshootingStep:
    """Paso individual en una guía de troubleshooting."""
    step_id: str
    step_type: StepType
    title: str
    content: str
    options: List[Dict[str, str]] = field(default_factory=list)  # Para decisiones
    next_steps: Dict[str, str] = field(default_factory=dict)  # Mapeo respuesta -> siguiente paso
    rag_query: Optional[str] = None  # Si es RAG_QUERY
    requires_confirmation: bool = False


@dataclass
class TroubleshootingGuide:
    """Guía completa de troubleshooting."""
    guide_id: str
    title: str
    description: str
    category: str
    steps: List[TroubleshootingStep]
    start_step_id: str
    metadata: Dict[str, Any] = field(default_factory=dict)


class TroubleshootingEngine:
    """Motor que ejecuta guías de troubleshooting paso a paso."""
    
    def __init__(self, guides_dir: Optional[Path] = None):
        """Inicializa el motor de troubleshooting.
        
        Args:
            guides_dir: Directorio donde están las guías (YAML/JSON)
        """
        self.guides_dir = guides_dir or Path("docchat/business_ai_support/troubleshooting/guides")
        self.guides_dir.mkdir(parents=True, exist_ok=True)
        
        self.guides: Dict[str, TroubleshootingGuide] = {}
        self.active_sessions: Dict[str, Dict[str, Any]] = {}  # session_id -> {guide_id, current_step, history}
        
        # Cargar guías existentes
        self._load_guides()
    
    def _load_guides(self):
        """Carga guías desde archivos YAML/JSON."""
        if not self.guides_dir.exists():
            return
        
        if YAML_AVAILABLE:
            for file_path in self.guides_dir.glob("*.yaml"):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = yaml.safe_load(f)
                        guide = self._parse_guide(data)
                        self.guides[guide.guide_id] = guide
                        print(f"✅ Guía cargada: {guide.title}")
                except Exception as e:
                    print(f"⚠️ Error cargando guía {file_path}: {e}")
        
        for file_path in self.guides_dir.glob("*.json"):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    guide = self._parse_guide(data)
                    self.guides[guide.guide_id] = guide
                    print(f"✅ Guía cargada: {guide.title}")
            except Exception as e:
                print(f"⚠️ Error cargando guía {file_path}: {e}")
    
    def _parse_guide(self, data: Dict[str, Any]) -> TroubleshootingGuide:
        """Parsea un diccionario a TroubleshootingGuide."""
        steps = []
        for step_data in data.get("steps", []):
            step = TroubleshootingStep(
                step_id=step_data["step_id"],
                step_type=StepType(step_data["step_type"]),
                title=step_data["title"],
                content=step_data["content"],
                options=step_data.get("options", []),
                next_steps=step_data.get("next_steps", {}),
                rag_query=step_data.get("rag_query"),
                requires_confirmation=step_data.get("requires_confirmation", False)
            )
            steps.append(step)
        
        return TroubleshootingGuide(
            guide_id=data["guide_id"],
            title=data["title"],
            description=data.get("description", ""),
            category=data.get("category", "general"),
            steps=steps,
            start_step_id=data.get("start_step_id", steps[0].step_id if steps else ""),
            metadata=data.get("metadata", {})
        )
    
    def start_guide(self, session_id: str, guide_id: str) -> Dict[str, Any]:
        """Inicia una guía para una sesión."""
        if guide_id not in self.guides:
            return {
                "success": False,
                "error": f"Guía {guide_id} no encontrada"
            }
        
        guide = self.guides[guide_id]
        start_step = self._get_step(guide, guide.start_step_id)
        
        if not start_step:
            return {
                "success": False,
                "error": f"Paso inicial {guide.start_step_id} no encontrado"
            }
        
        self.active_sessions[session_id] = {
            "guide_id": guide_id,
            "current_step_id": guide.start_step_id,
            "history": [],
            "started_at": datetime.now().isoformat()
        }
        
        return {
            "success": True,
            "guide_id": guide_id,
            "guide_title": guide.title,
            "current_step": self._format_step(start_step),
            "message": start_step.content
        }
    
    def process_response(
        self,
        session_id: str,
        user_response: str,
        rag_result: Optional[str] = None
    ) -> Dict[str, Any]:
        """Procesa la respuesta del usuario y avanza en la guía."""
        if session_id not in self.active_sessions:
            return {
                "success": False,
                "error": "No hay guía activa para esta sesión"
            }
        
        session = self.active_sessions[session_id]
        guide = self.guides[session["guide_id"]]
        current_step = self._get_step(guide, session["current_step_id"])
        
        if not current_step:
            return {
                "success": False,
                "error": f"Paso {session['current_step_id']} no encontrado"
            }
        
        # Agregar al historial
        session["history"].append({
            "step_id": current_step.step_id,
            "user_response": user_response,
            "timestamp": datetime.now().isoformat()
        })
        
        # Determinar siguiente paso
        next_step_id = self._determine_next_step(current_step, user_response, rag_result)
        
        if not next_step_id:
            # Guía completada o sin siguiente paso
            del self.active_sessions[session_id]
            return {
                "success": True,
                "completed": True,
                "message": "Guía completada. ¿Necesitas algo más?",
                "history": session["history"]
            }
        
        # Avanzar al siguiente paso
        session["current_step_id"] = next_step_id
        next_step = self._get_step(guide, next_step_id)
        
        return {
            "success": True,
            "current_step": self._format_step(next_step),
            "message": next_step.content,
            "completed": False
        }
    
    def _get_step(self, guide: TroubleshootingGuide, step_id: str) -> Optional[TroubleshootingStep]:
        """Obtiene un paso por ID."""
        for step in guide.steps:
            if step.step_id == step_id:
                return step
        return None
    
    def _determine_next_step(
        self,
        current_step: TroubleshootingStep,
        user_response: str,
        rag_result: Optional[str] = None
    ) -> Optional[str]:
        """Determina el siguiente paso basado en la respuesta del usuario."""
        if current_step.step_type == StepType.DECISION:
            # Buscar en opciones
            user_lower = user_response.lower().strip()
            for option in current_step.options:
                if option.get("value", "").lower() in user_lower or \
                   option.get("label", "").lower() in user_lower:
                    return current_step.next_steps.get(option["value"])
            
            # Buscar en next_steps por respuesta directa
            for key, next_id in current_step.next_steps.items():
                if key.lower() in user_lower:
                    return next_id
            
            # Default: primera opción o None
            if current_step.options:
                return current_step.next_steps.get(current_step.options[0].get("value"))
        
        elif current_step.step_type == StepType.RAG_QUERY:
            # Si hay resultado RAG, avanzar
            if rag_result:
                return current_step.next_steps.get("success") or current_step.next_steps.get("default")
            else:
                return current_step.next_steps.get("failure") or current_step.next_steps.get("default")
        
        else:
            # Para otros tipos, usar next_steps["default"] o None
            return current_step.next_steps.get("default")
    
    def _format_step(self, step: TroubleshootingStep) -> Dict[str, Any]:
        """Formatea un paso para respuesta."""
        return {
            "step_id": step.step_id,
            "type": step.step_type.value,
            "title": step.title,
            "content": step.content,
            "options": step.options,
            "requires_confirmation": step.requires_confirmation
        }
    
    def get_active_guide(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Obtiene información de la guía activa."""
        if session_id not in self.active_sessions:
            return None
        
        session = self.active_sessions[session_id]
        guide = self.guides[session["guide_id"]]
        current_step = self._get_step(guide, session["current_step_id"])
        
        return {
            "guide_id": session["guide_id"],
            "guide_title": guide.title,
            "current_step": self._format_step(current_step) if current_step else None,
            "history_length": len(session["history"])
        }
    
    def cancel_guide(self, session_id: str) -> bool:
        """Cancela la guía activa."""
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]
            return True
        return False

