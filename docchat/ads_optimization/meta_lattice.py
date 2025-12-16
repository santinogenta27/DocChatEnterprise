"""
Meta Lattice: Model Space Redesign for Cost-Effective Industry-Scale Ads Recommendations
Implementación de técnicas avanzadas de Meta Lattice:
- Lattice Zipper: Mixing Attribution Windows
- Lattice Filter: Pareto-Optimal Feature Selection
- Lattice KTAP: Knowledge Transfer at Inference Time
"""

from __future__ import annotations

from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from collections import defaultdict
import hashlib

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False
    print("⚠️ NumPy no disponible. Instala con: pip install numpy")


@dataclass
class AttributionWindow:
    """Ventana de atribución"""
    window_minutes: int  # 90, 1440 (1 día), 10080 (7 días)
    weight: float = 1.0


@dataclass
class FeatureImportance:
    """Importancia de una feature"""
    feature_name: str
    importance_scores: Dict[str, float]  # task -> score
    is_pareto_optimal: bool = False


class LatticeZipper:
    """
    Lattice Zipper: Mezcla ventanas de atribución para balancear freshness y correctness
    Basado en: Meta Lattice paper - Section 3.2.1
    """
    
    def __init__(self, attribution_windows: List[AttributionWindow]):
        self.attribution_windows = attribution_windows
        self.total_weight = sum(w.weight for w in attribution_windows)
    
    def assign_window(self, impression_signature: str) -> AttributionWindow:
        """
        Asigna una ventana de atribución a una impresión usando hashing determinístico
        """
        # Hash determinístico del signature
        hash_value = int(hashlib.md5(impression_signature.encode()).hexdigest(), 16)
        
        # Normalizar pesos
        cumulative_weights = []
        cumulative = 0.0
        for window in self.attribution_windows:
            cumulative += window.weight / self.total_weight
            cumulative_weights.append(cumulative)
        
        # Seleccionar ventana basado en hash
        random_value = (hash_value % 10000) / 10000.0
        
        for i, cum_weight in enumerate(cumulative_weights):
            if random_value <= cum_weight:
                return self.attribution_windows[i]
        
        return self.attribution_windows[-1]
    
    def create_unified_dataset(
        self,
        impressions: List[Dict[str, Any]],
        conversion_data: Dict[str, Dict[int, bool]]  # impression_id -> {window_minutes: converted}
    ) -> List[Dict[str, Any]]:
        """
        Crea dataset unificado mezclando diferentes ventanas de atribución
        """
        unified_data = []
        
        for impression in impressions:
            signature = f"{impression.get('user_id')}_{impression.get('ad_id')}_{impression.get('timestamp')}"
            assigned_window = self.assign_window(signature)
            
            # Obtener conversión para esta ventana
            impression_id = impression.get('impression_id')
            converted = conversion_data.get(impression_id, {}).get(assigned_window.window_minutes, False)
            
            unified_impression = {
                **impression,
                "assigned_attribution_window": assigned_window.window_minutes,
                "converted": converted,
                "window_weight": assigned_window.weight
            }
            
            unified_data.append(unified_impression)
        
        return unified_data


class LatticeFilter:
    """
    Lattice Filter: Selección Pareto-óptima de features
    Basado en: Meta Lattice paper - Section 3.2.2
    """
    
    def __init__(self, target_feature_count: int):
        self.target_feature_count = target_feature_count
    
    def compute_feature_importance(
        self,
        features: List[str],
        tasks: List[str],
        importance_scores: Dict[str, Dict[str, float]]  # feature -> task -> score
    ) -> List[FeatureImportance]:
        """
        Calcula importancia de features usando permutation-based importance
        """
        feature_importances = []
        
        for feature in features:
            scores = importance_scores.get(feature, {})
            feature_importances.append(FeatureImportance(
                feature_name=feature,
                importance_scores=scores
            ))
        
        return feature_importances
    
    def select_pareto_optimal_features(
        self,
        feature_importances: List[FeatureImportance],
        tasks: List[str]
    ) -> List[str]:
        """
        Selecciona features Pareto-óptimas
        """
        if len(feature_importances) <= self.target_feature_count:
            return [f.feature_name for f in feature_importances]
        
        # Construir vectores de importancia
        feature_vectors = {}
        for feat in feature_importances:
            vector = np.array([feat.importance_scores.get(task, 0.0) for task in tasks])
            feature_vectors[feat.feature_name] = vector
        
        selected_features = []
        remaining_features = list(feature_vectors.keys())
        
        # Iterativamente seleccionar features en el Pareto frontier
        while len(selected_features) < self.target_feature_count and remaining_features:
            # Encontrar features en el Pareto frontier actual
            frontier = self._find_pareto_frontier(remaining_features, feature_vectors, tasks)
            
            # Si hay más features en el frontier que el presupuesto, seleccionar aleatoriamente
            if len(frontier) <= (self.target_feature_count - len(selected_features)):
                selected_features.extend(frontier)
                remaining_features = [f for f in remaining_features if f not in frontier]
            else:
                # Seleccionar aleatoriamente del frontier
                import random
                needed = self.target_feature_count - len(selected_features)
                selected = random.sample(frontier, needed)
                selected_features.extend(selected)
                break
        
        return selected_features[:self.target_feature_count]
    
    def _find_pareto_frontier(
        self,
        features: List[str],
        feature_vectors: Dict[str, np.ndarray],
        tasks: List[str]
    ) -> List[str]:
        """Encuentra el Pareto frontier"""
        frontier = []
        
        if not NUMPY_AVAILABLE:
            # Fallback sin NumPy
            return features[:min(10, len(features))]
        
        for feature in features:
            vector = feature_vectors[feature]
            is_dominated = False
            
            for other_feature in features:
                if feature == other_feature:
                    continue
                
                other_vector = feature_vectors[other_feature]
                
                # Verificar si está dominado
                if np.all(other_vector >= vector) and np.any(other_vector > vector):
                    is_dominated = True
                    break
            
            if not is_dominated:
                frontier.append(feature)
        
        return frontier


class LatticeKTAP:
    """
    Lattice KTAP: Knowledge Transfer at Inference Time
    Transfiere conocimiento de modelos teacher a student en tiempo de inferencia
    Basado en: Meta Lattice paper - Section 3.4
    """
    
    def __init__(self, ttl_hours: int = 6):
        self.ttl_hours = ttl_hours
        self.teacher_embeddings_cache: Dict[str, Dict[str, Any]] = {}  # user_item -> embedding + timestamp
    
    def store_teacher_embedding(
        self,
        user_id: str,
        item_id: str,
        embedding: np.ndarray,
        timestamp: float
    ):
        """Almacena embedding del teacher model"""
        key = f"{user_id}_{item_id}"
        self.teacher_embeddings_cache[key] = {
            "embedding": embedding,
            "timestamp": timestamp,
            "ttl": timestamp + (self.ttl_hours * 3600)
        }
    
    def get_teacher_embedding(
        self,
        user_id: str,
        item_id: str,
        current_timestamp: float
    ) -> Optional[np.ndarray]:
        """
        Obtiene embedding del teacher si está válido (dentro de TTL)
        """
        key = f"{user_id}_{item_id}"
        
        if key not in self.teacher_embeddings_cache:
            return None
        
        cached = self.teacher_embeddings_cache[key]
        
        # Verificar TTL
        if current_timestamp > cached["ttl"]:
            # Expiró, remover del cache
            del self.teacher_embeddings_cache[key]
            return None
        
        return cached["embedding"]
    
    def enhance_student_input(
        self,
        user_id: str,
        item_id: str,
        student_features,
        current_timestamp: float
    ):
        """
        Mejora input del student model con embedding del teacher
        """
        if not NUMPY_AVAILABLE:
            return student_features
        
        teacher_embedding = self.get_teacher_embedding(user_id, item_id, current_timestamp)
        
        if teacher_embedding is not None:
            # Concatenar embedding del teacher con features del student
            enhanced = np.concatenate([student_features, teacher_embedding])
            return enhanced
        else:
            # Si no hay embedding válido, usar zeros como placeholder
            placeholder = np.zeros(teacher_embedding.shape[0] if teacher_embedding is not None else 128)
            return np.concatenate([student_features, placeholder])


class MetaLatticeOptimizer:
    """
    Optimizador completo usando técnicas de Meta Lattice
    Integra Zipper, Filter, y KTAP
    """
    
    def __init__(self, config: Any):
        self.config = config
        
        # Configurar Lattice Zipper con ventanas comunes
        attribution_windows = [
            AttributionWindow(window_minutes=90, weight=0.3),   # 90 minutos (freshness)
            AttributionWindow(window_minutes=1440, weight=0.5),  # 1 día (balance)
            AttributionWindow(window_minutes=10080, weight=0.2)  # 7 días (correctness)
        ]
        self.zipper = LatticeZipper(attribution_windows)
        
        # Configurar Lattice Filter
        self.filter = LatticeFilter(target_feature_count=2000)
        
        # Configurar Lattice KTAP
        self.ktap = LatticeKTAP(ttl_hours=6)
    
    def optimize_attribution(self, impressions: List[Dict[str, Any]], conversions: Dict[str, Dict[int, bool]]) -> List[Dict[str, Any]]:
        """Optimiza atribución usando Lattice Zipper"""
        return self.zipper.create_unified_dataset(impressions, conversions)
    
    def optimize_features(self, features: List[str], tasks: List[str], importance_scores: Dict[str, Dict[str, float]]) -> List[str]:
        """Optimiza selección de features usando Lattice Filter"""
        feature_importances = self.filter.compute_feature_importance(features, tasks, importance_scores)
        return self.filter.select_pareto_optimal_features(feature_importances, tasks)
    
    def enhance_prediction(self, user_id: str, item_id: str, features: np.ndarray, timestamp: float) -> np.ndarray:
        """Mejora predicción usando Lattice KTAP"""
        return self.ktap.enhance_student_input(user_id, item_id, features, timestamp)
