"""
Sistema de Aprendizaje Continuo para STAR AGENT.

Mejora con interacciones y feedback:
- Aprende de respuestas exitosas
- Aprende de feedback del usuario
- Mejora recomendaciones basadas en conversiones
- Soporta lenguaje informal
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
from collections import defaultdict

from ..state.customer_session import CustomerSessionState


@dataclass
class InteractionFeedback:
    """Feedback de una interacción"""
    session_id: str
    message: str
    response: str
    feedback_type: str  # positive, negative, neutral
    conversion: bool = False
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LearningPattern:
    """Patrón aprendido de interacciones"""
    pattern_type: str  # successful_response, objection_handling, closing_technique
    context: str
    action: str
    success_rate: float
    usage_count: int
    last_used: datetime


class ContinuousLearningSystem:
    """
    Sistema de aprendizaje continuo.
    
    Características:
    - Aprende de interacciones exitosas
    - Mejora con feedback del usuario
    - Aprende patrones de lenguaje informal
    - Optimiza técnicas de cierre basadas en conversiones
    """
    
    def __init__(self, learning_dir: Optional[Path] = None):
        """
        Inicializa el sistema de aprendizaje.
        
        Args:
            learning_dir: Directorio para almacenar datos de aprendizaje
        """
        self.learning_dir = learning_dir or Path("docchat/star_agent/learning_data")
        self.learning_dir.mkdir(parents=True, exist_ok=True)
        
        # Almacenamiento de feedback
        self.feedback_history: List[InteractionFeedback] = []
        
        # Patrones aprendidos
        self.learned_patterns: Dict[str, LearningPattern] = {}
        
        # Métricas de éxito
        self.success_metrics: Dict[str, Any] = defaultdict(int)
        
        # Cargar datos existentes
        self._load_learning_data()
    
    def record_interaction(
        self,
        session: CustomerSessionState,
        user_message: str,
        agent_response: str,
        conversion: bool = False,
    ):
        """
        Registra una interacción para aprendizaje.
        
        Args:
            session: Estado de sesión
            user_message: Mensaje del usuario
            agent_response: Respuesta del agente
            conversion: Si resultó en conversión
        """
        feedback = InteractionFeedback(
            session_id=session.profile.user_id if session.profile else "unknown",
            message=user_message,
            response=agent_response,
            feedback_type="positive" if conversion else "neutral",
            conversion=conversion,
            metadata={
                "sales_stage": getattr(session, 'sales_stage', 'unknown'),
                "sentiment": session.sentiment.value if hasattr(session, 'sentiment') else 'neutral',
            }
        )
        
        self.feedback_history.append(feedback)
        
        # Aprender de la interacción
        if conversion:
            self._learn_from_success(user_message, agent_response, session)
        
        # Guardar periódicamente
        if len(self.feedback_history) % 10 == 0:
            self._save_learning_data()
    
    def record_feedback(
        self,
        session_id: str,
        feedback_type: str,
        message: str,
        response: str,
    ):
        """
        Registra feedback explícito del usuario.
        
        Args:
            session_id: ID de sesión
            feedback_type: "positive", "negative", "neutral"
            message: Mensaje original del usuario
            response: Respuesta del agente
        """
        feedback = InteractionFeedback(
            session_id=session_id,
            message=message,
            response=response,
            feedback_type=feedback_type,
            conversion=False,
        )
        
        self.feedback_history.append(feedback)
        
        # Aprender del feedback
        if feedback_type == "positive":
            self._learn_from_success(message, response, None)
        elif feedback_type == "negative":
            self._learn_from_failure(message, response)
        
        self._save_learning_data()
    
    def _learn_from_success(
        self,
        user_message: str,
        agent_response: str,
        session: Optional[CustomerSessionState],
    ):
        """Aprende de interacciones exitosas"""
        # Extraer patrones de la respuesta exitosa
        pattern_key = f"successful_response_{hash(user_message[:50])}"
        
        if pattern_key not in self.learned_patterns:
            self.learned_patterns[pattern_key] = LearningPattern(
                pattern_type="successful_response",
                context=user_message[:100],
                action=agent_response[:200],
                success_rate=1.0,
                usage_count=1,
                last_used=datetime.now(),
            )
        else:
            pattern = self.learned_patterns[pattern_key]
            pattern.usage_count += 1
            pattern.success_rate = (pattern.success_rate * (pattern.usage_count - 1) + 1.0) / pattern.usage_count
            pattern.last_used = datetime.now()
        
        # Actualizar métricas
        self.success_metrics["successful_interactions"] += 1
        if session and hasattr(session, 'sales_stage'):
            self.success_metrics[f"success_{session.sales_stage}"] += 1
    
    def _learn_from_failure(self, user_message: str, agent_response: str):
        """Aprende de interacciones fallidas"""
        # Identificar qué salió mal
        pattern_key = f"failed_response_{hash(user_message[:50])}"
        
        if pattern_key not in self.learned_patterns:
            self.learned_patterns[pattern_key] = LearningPattern(
                pattern_type="failed_response",
                context=user_message[:100],
                action=agent_response[:200],
                success_rate=0.0,
                usage_count=1,
                last_used=datetime.now(),
            )
        else:
            pattern = self.learned_patterns[pattern_key]
            pattern.usage_count += 1
            pattern.success_rate = (pattern.success_rate * (pattern.usage_count - 1) + 0.0) / pattern.usage_count
        
        self.success_metrics["failed_interactions"] += 1
    
    def get_best_response_pattern(self, context: str) -> Optional[str]:
        """
        Obtiene el mejor patrón de respuesta aprendido para un contexto.
        
        Args:
            context: Contexto de la conversación
            
        Returns:
            Patrón de respuesta recomendado o None
        """
        # Buscar patrones similares con alta tasa de éxito
        best_pattern = None
        best_score = 0.0
        
        for pattern in self.learned_patterns.values():
            if pattern.pattern_type == "successful_response":
                # Calcular similitud simple (en producción usar embeddings)
                similarity = self._simple_similarity(context, pattern.context)
                score = similarity * pattern.success_rate
                
                if score > best_score:
                    best_score = score
                    best_pattern = pattern
        
        return best_pattern.action if best_pattern else None
    
    def _simple_similarity(self, text1: str, text2: str) -> float:
        """Calcula similitud simple entre dos textos"""
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        
        return intersection / union if union > 0 else 0.0
    
    def get_conversion_insights(self) -> Dict[str, Any]:
        """
        Obtiene insights de conversión para optimización.
        
        Returns:
            Dict con métricas y recomendaciones
        """
        total_interactions = len(self.feedback_history)
        conversions = sum(1 for f in self.feedback_history if f.conversion)
        conversion_rate = conversions / total_interactions if total_interactions > 0 else 0.0
        
        # Patrones más exitosos
        successful_patterns = [
            p for p in self.learned_patterns.values()
            if p.pattern_type == "successful_response" and p.success_rate > 0.7
        ]
        successful_patterns.sort(key=lambda x: x.success_rate, reverse=True)
        
        return {
            "total_interactions": total_interactions,
            "conversions": conversions,
            "conversion_rate": conversion_rate,
            "top_patterns": [
                {
                    "context": p.context,
                    "action": p.action[:100],
                    "success_rate": p.success_rate,
                    "usage_count": p.usage_count,
                }
                for p in successful_patterns[:5]
            ],
            "metrics": dict(self.success_metrics),
        }
    
    def _load_learning_data(self):
        """Carga datos de aprendizaje desde archivo"""
        data_file = self.learning_dir / "learning_data.json"
        if data_file.exists():
            try:
                with open(data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                    # Cargar patrones
                    for key, pattern_data in data.get("patterns", {}).items():
                        self.learned_patterns[key] = LearningPattern(
                            pattern_type=pattern_data["pattern_type"],
                            context=pattern_data["context"],
                            action=pattern_data["action"],
                            success_rate=pattern_data["success_rate"],
                            usage_count=pattern_data["usage_count"],
                            last_used=datetime.fromisoformat(pattern_data["last_used"]),
                        )
                    
                    # Cargar métricas
                    self.success_metrics = data.get("metrics", {})
            
            except Exception as e:
                print(f"⚠️ Error cargando datos de aprendizaje: {e}")
    
    def _save_learning_data(self):
        """Guarda datos de aprendizaje"""
        data_file = self.learning_dir / "learning_data.json"
        try:
            data = {
                "patterns": {
                    key: {
                        "pattern_type": pattern.pattern_type,
                        "context": pattern.context,
                        "action": pattern.action,
                        "success_rate": pattern.success_rate,
                        "usage_count": pattern.usage_count,
                        "last_used": pattern.last_used.isoformat(),
                    }
                    for key, pattern in self.learned_patterns.items()
                },
                "metrics": dict(self.success_metrics),
                "last_updated": datetime.now().isoformat(),
            }
            
            with open(data_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        
        except Exception as e:
            print(f"⚠️ Error guardando datos de aprendizaje: {e}")

