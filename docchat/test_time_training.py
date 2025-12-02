"""
Test Time Training - Aprendizaje en tiempo de ejecución
El sistema aprende mientras está trabajando, no solo durante el entrenamiento inicial
Tercera ley de escalado según Eric Schmidt
"""

from __future__ import annotations

import json
import time
import uuid
from typing import List, Dict, Optional, Any, Callable
from dataclasses import dataclass, field, asdict
from pathlib import Path
from collections import defaultdict

from langchain_core.language_models import BaseLanguageModel

from .config import AppConfig


@dataclass
class LearningEpisode:
    """Un episodio de aprendizaje."""
    episode_id: str
    task_type: str  # Tipo de tarea
    input_data: Any  # Entrada
    output_data: Any  # Salida generada
    expected_output: Optional[Any] = None  # Salida esperada (si hay)
    success: bool = False
    feedback: Optional[str] = None  # Feedback del usuario o sistema
    timestamp: float = field(default_factory=time.time)
    execution_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LearnedPattern:
    """Patrón aprendido."""
    pattern_id: str
    pattern_type: str  # "action_sequence", "query_pattern", "error_recovery", etc.
    pattern_data: Dict[str, Any]
    success_count: int = 0
    failure_count: int = 0
    confidence: float = 0.0
    last_used: float = field(default_factory=time.time)
    created_at: float = field(default_factory=time.time)
    usage_count: int = 0


class TestTimeTrainer:
    """
    Sistema de aprendizaje en tiempo de ejecución.
    
    Características:
    - Aprende de cada interacción
    - Mejora continuamente sin intervención
    - Identifica patrones exitosos
    - Evita repetir errores
    - Adapta comportamiento según contexto
    """
    
    def __init__(
        self,
        config: AppConfig,
        llm: Optional[BaseLanguageModel] = None,
        learning_rate: float = 0.1,
        min_confidence: float = 0.6
    ):
        self.config = config
        self.llm = llm
        self.learning_rate = learning_rate
        self.min_confidence = min_confidence
        
        # Episodios de aprendizaje
        self.episodes: List[LearningEpisode] = []
        
        # Patrones aprendidos
        self.learned_patterns: Dict[str, LearnedPattern] = {}
        
        # Estadísticas por tipo de tarea
        self.task_statistics: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            "total": 0,
            "successful": 0,
            "failed": 0,
            "avg_execution_time": 0.0,
            "common_errors": []
        })
        
        # Directorio para persistencia
        self.storage_dir = Path(config.memory_dir) / "test_time_training"
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        # Cargar aprendizaje previo
        self._load_learning_data()
    
    def _load_learning_data(self):
        """Carga datos de aprendizaje previo."""
        # Cargar episodios
        episodes_file = self.storage_dir / "episodes.json"
        if episodes_file.exists():
            try:
                with open(episodes_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for ep_data in data.get("episodes", [])[-1000:]:  # Últimos 1000
                        episode = LearningEpisode(**ep_data)
                        self.episodes.append(episode)
                print(f"✅ [Test Time Training] {len(self.episodes)} episodios cargados")
            except Exception as e:
                print(f"⚠️ [Test Time Training] Error cargando episodios: {e}")
        
        # Cargar patrones
        patterns_file = self.storage_dir / "patterns.json"
        if patterns_file.exists():
            try:
                with open(patterns_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for pat_data in data.get("patterns", []):
                        pattern = LearnedPattern(**pat_data)
                        self.learned_patterns[pattern.pattern_id] = pattern
                print(f"✅ [Test Time Training] {len(self.learned_patterns)} patrones cargados")
            except Exception as e:
                print(f"⚠️ [Test Time Training] Error cargando patrones: {e}")
        
        # Cargar estadísticas
        stats_file = self.storage_dir / "statistics.json"
        if stats_file.exists():
            try:
                with open(stats_file, "r", encoding="utf-8") as f:
                    self.task_statistics = json.load(f)
            except Exception as e:
                print(f"⚠️ [Test Time Training] Error cargando estadísticas: {e}")
    
    def _save_learning_data(self):
        """Guarda datos de aprendizaje."""
        # Guardar episodios (últimos 1000)
        episodes_file = self.storage_dir / "episodes.json"
        try:
            with open(episodes_file, "w", encoding="utf-8") as f:
                json.dump({
                    "episodes": [asdict(ep) for ep in self.episodes[-1000:]]
                }, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"⚠️ [Test Time Training] Error guardando episodios: {e}")
        
        # Guardar patrones
        patterns_file = self.storage_dir / "patterns.json"
        try:
            with open(patterns_file, "w", encoding="utf-8") as f:
                json.dump({
                    "patterns": [asdict(pat) for pat in self.learned_patterns.values()]
                }, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"⚠️ [Test Time Training] Error guardando patrones: {e}")
        
        # Guardar estadísticas
        stats_file = self.storage_dir / "statistics.json"
        try:
            with open(stats_file, "w", encoding="utf-8") as f:
                json.dump(dict(self.task_statistics), f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"⚠️ [Test Time Training] Error guardando estadísticas: {e}")
    
    def record_episode(
        self,
        task_type: str,
        input_data: Any,
        output_data: Any,
        success: bool,
        expected_output: Optional[Any] = None,
        feedback: Optional[str] = None,
        execution_time: float = 0.0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Registra un episodio de aprendizaje.
        
        Returns:
            episode_id: ID del episodio registrado
        """
        episode = LearningEpisode(
            episode_id=str(uuid.uuid4()),
            task_type=task_type,
            input_data=input_data,
            output_data=output_data,
            expected_output=expected_output,
            success=success,
            feedback=feedback,
            execution_time=execution_time,
            metadata=metadata or {}
        )
        
        self.episodes.append(episode)
        
        # Actualizar estadísticas
        stats = self.task_statistics[task_type]
        stats["total"] += 1
        if success:
            stats["successful"] += 1
        else:
            stats["failed"] += 1
        
        # Actualizar tiempo promedio
        total_time = stats["avg_execution_time"] * (stats["total"] - 1) + execution_time
        stats["avg_execution_time"] = total_time / stats["total"]
        
        # Aprender del episodio
        self._learn_from_episode(episode)
        
        # Guardar periódicamente (cada 10 episodios)
        if len(self.episodes) % 10 == 0:
            self._save_learning_data()
        
        return episode.episode_id
    
    def _learn_from_episode(self, episode: LearningEpisode):
        """Aprende de un episodio."""
        if episode.success:
            # Aprender patrones exitosos
            self._extract_success_pattern(episode)
        else:
            # Aprender de errores
            self._extract_failure_pattern(episode)
    
    def _extract_success_pattern(self, episode: LearningEpisode):
        """Extrae patrones de éxito."""
        # Buscar patrones similares
        similar_patterns = self._find_similar_patterns(
            pattern_type="success",
            task_type=episode.task_type,
            input_data=episode.input_data
        )
        
        if similar_patterns:
            # Actualizar patrón existente
            for pattern_id in similar_patterns:
                pattern = self.learned_patterns[pattern_id]
                pattern.success_count += 1
                pattern.usage_count += 1
                pattern.last_used = time.time()
                
                # Actualizar confianza
                total = pattern.success_count + pattern.failure_count
                pattern.confidence = pattern.success_count / total if total > 0 else 0.0
        else:
            # Crear nuevo patrón
            pattern = LearnedPattern(
                pattern_id=str(uuid.uuid4()),
                pattern_type="success",
                pattern_data={
                    "task_type": episode.task_type,
                    "input_pattern": str(episode.input_data)[:200],
                    "output_pattern": str(episode.output_data)[:200],
                    "metadata": episode.metadata
                },
                success_count=1,
                confidence=1.0
            )
            self.learned_patterns[pattern.pattern_id] = pattern
    
    def _extract_failure_pattern(self, episode: LearningEpisode):
        """Extrae patrones de falla."""
        # Buscar patrones similares de error
        similar_patterns = self._find_similar_patterns(
            pattern_type="failure",
            task_type=episode.task_type,
            input_data=episode.input_data
        )
        
        if similar_patterns:
            # Actualizar patrón existente
            for pattern_id in similar_patterns:
                pattern = self.learned_patterns[pattern_id]
                pattern.failure_count += 1
                pattern.last_used = time.time()
                
                # Actualizar confianza
                total = pattern.success_count + pattern.failure_count
                pattern.confidence = pattern.success_count / total if total > 0 else 0.0
        else:
            # Crear nuevo patrón de error
            pattern = LearnedPattern(
                pattern_id=str(uuid.uuid4()),
                pattern_type="failure",
                pattern_data={
                    "task_type": episode.task_type,
                    "input_pattern": str(episode.input_data)[:200],
                    "error": episode.feedback or "Error desconocido",
                    "metadata": episode.metadata
                },
                failure_count=1,
                confidence=0.0
            )
            self.learned_patterns[pattern.pattern_id] = pattern
    
    def _find_similar_patterns(
        self,
        pattern_type: str,
        task_type: str,
        input_data: Any
    ) -> List[str]:
        """Encuentra patrones similares."""
        similar = []
        input_str = str(input_data)[:200]
        
        for pattern_id, pattern in self.learned_patterns.items():
            if pattern.pattern_type != pattern_type:
                continue
            
            if pattern.pattern_data.get("task_type") != task_type:
                continue
            
            # Comparación simple (puede mejorarse con embeddings)
            pattern_input = pattern.pattern_data.get("input_pattern", "")
            if input_str in pattern_input or pattern_input in input_str:
                similar.append(pattern_id)
        
        return similar
    
    def get_best_pattern(
        self,
        task_type: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[LearnedPattern]:
        """
        Obtiene el mejor patrón aprendido para un tipo de tarea.
        """
        best_pattern = None
        best_score = 0.0
        
        for pattern in self.learned_patterns.values():
            if pattern.pattern_data.get("task_type") != task_type:
                continue
            
            if pattern.confidence < self.min_confidence:
                continue
            
            # Calcular score (confianza + recencia)
            recency_score = 1.0 / (1.0 + (time.time() - pattern.last_used) / 86400)  # Decaimiento diario
            score = pattern.confidence * 0.7 + recency_score * 0.3
            
            if score > best_score:
                best_score = score
                best_pattern = pattern
        
        return best_pattern
    
    def get_improvement_suggestions(
        self,
        task_type: str
    ) -> List[Dict[str, Any]]:
        """
        Obtiene sugerencias de mejora basadas en aprendizaje.
        """
        suggestions = []
        stats = self.task_statistics.get(task_type, {})
        
        if stats.get("total", 0) == 0:
            return suggestions
        
        success_rate = stats["successful"] / stats["total"] if stats["total"] > 0 else 0
        
        # Si la tasa de éxito es baja, sugerir mejoras
        if success_rate < 0.7:
            suggestions.append({
                "type": "low_success_rate",
                "message": f"Tasa de éxito baja ({success_rate*100:.1f}%). Considera revisar el enfoque.",
                "priority": "high"
            })
        
        # Buscar patrones de error comunes
        failure_patterns = [
            p for p in self.learned_patterns.values()
            if p.pattern_type == "failure"
            and p.pattern_data.get("task_type") == task_type
            and p.failure_count >= 3
        ]
        
        if failure_patterns:
            suggestions.append({
                "type": "common_errors",
                "message": f"Se detectaron {len(failure_patterns)} patrones de error comunes.",
                "patterns": [p.pattern_data.get("error", "Error desconocido") for p in failure_patterns[:3]],
                "priority": "medium"
            })
        
        return suggestions
    
    def apply_learned_knowledge(
        self,
        task_type: str,
        input_data: Any,
        default_action: Callable
    ) -> Any:
        """
        Aplica conocimiento aprendido a una nueva tarea.
        
        Si hay un patrón exitoso aprendido, lo usa.
        Si no, usa la acción por defecto y aprende del resultado.
        """
        # Buscar patrón exitoso
        pattern = self.get_best_pattern(task_type)
        
        if pattern and pattern.confidence >= self.min_confidence:
            # Usar patrón aprendido
            pattern.usage_count += 1
            pattern.last_used = time.time()
            
            # Aplicar patrón (simplificado - en producción sería más sofisticado)
            output_pattern = pattern.pattern_data.get("output_pattern", "")
            
            # Si el patrón tiene suficiente confianza, intentar usarlo
            if pattern.confidence > 0.8:
                return output_pattern
        
        # Si no hay patrón confiable, usar acción por defecto
        return default_action()
    
    def get_statistics(self) -> Dict[str, Any]:
        """Obtiene estadísticas de aprendizaje."""
        total_episodes = len(self.episodes)
        successful_episodes = sum(1 for ep in self.episodes if ep.success)
        
        return {
            "total_episodes": total_episodes,
            "successful_episodes": successful_episodes,
            "success_rate": (successful_episodes / total_episodes * 100) if total_episodes > 0 else 0,
            "learned_patterns": len(self.learned_patterns),
            "high_confidence_patterns": sum(1 for p in self.learned_patterns.values() if p.confidence >= 0.8),
            "task_statistics": dict(self.task_statistics),
            "recent_learning_rate": self._calculate_recent_learning_rate()
        }
    
    def _calculate_recent_learning_rate(self) -> float:
        """Calcula la tasa de aprendizaje reciente (últimas 24 horas)."""
        cutoff = time.time() - 86400  # 24 horas
        recent_episodes = [ep for ep in self.episodes if ep.timestamp > cutoff]
        
        if len(recent_episodes) == 0:
            return 0.0
        
        successful = sum(1 for ep in recent_episodes if ep.success)
        return successful / len(recent_episodes) if recent_episodes else 0.0

