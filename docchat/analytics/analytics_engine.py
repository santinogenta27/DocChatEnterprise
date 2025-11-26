"""
Motor de Analytics y Business Intelligence para métricas de uso y insights.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
from collections import defaultdict, Counter

from ..config import AppConfig


class AnalyticsEngine:
    """
    Motor de analytics para tracking de uso, métricas y business intelligence.
    """
    
    def __init__(self, config: AppConfig):
        self.config = config
        self.data_dir = Path(config.memory_dir) / "analytics"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Archivos de datos
        self.queries_file = self.data_dir / "queries.json"
        self.documents_file = self.data_dir / "documents_usage.json"
        self.users_file = self.data_dir / "users.json"
        self.sentiment_file = self.data_dir / "sentiment.json"
        
        # Cargar datos existentes
        self.queries = self._load_json(self.queries_file, [])
        self.documents_usage = self._load_json(self.documents_file, {})
        self.users = self._load_json(self.users_file, {})
        self.sentiment_data = self._load_json(self.sentiment_file, [])
    
    def _load_json(self, file_path: Path, default):
        """Carga datos JSON."""
        try:
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return default
        except Exception:
            return default
    
    def _save_json(self, file_path: Path, data):
        """Guarda datos JSON."""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error guardando analytics: {e}")
    
    def track_query(
        self,
        query: str,
        user_id: Optional[str] = None,
        response_time: float = 0.0,
        documents_used: List[str] = None,
        success: bool = True
    ):
        """Registra una consulta."""
        query_data = {
            "query": query,
            "user_id": user_id or "anonymous",
            "timestamp": datetime.now().isoformat(),
            "response_time": response_time,
            "documents_used": documents_used or [],
            "success": success
        }
        
        self.queries.append(query_data)
        
        # Guardar (cada 10 queries para no saturar)
        if len(self.queries) % 10 == 0:
            self._save_json(self.queries_file, self.queries)
        
        # Actualizar uso de documentos
        for doc in documents_used or []:
            self.documents_usage[doc] = self.documents_usage.get(doc, 0) + 1
        
        self._save_json(self.documents_file, self.documents_usage)
    
    def analyze_sentiment(self, text: str) -> Dict[str, float]:
        """
        Analiza sentimiento de un texto.
        Retorna scores de positivo, negativo, neutro.
        """
        # Análisis básico de sentimiento (se puede mejorar con modelo dedicado)
        positive_words = ["bueno", "excelente", "perfecto", "genial", "útil", "ayuda"]
        negative_words = ["malo", "error", "falla", "problema", "no funciona", "lento"]
        
        text_lower = text.lower()
        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)
        
        total = positive_count + negative_count
        if total == 0:
            return {"positive": 0.5, "negative": 0.3, "neutral": 0.2}
        
        positive_score = positive_count / total
        negative_score = negative_count / total
        neutral_score = 1.0 - positive_score - negative_score
        
        sentiment = {
            "positive": max(0, positive_score),
            "negative": max(0, negative_score),
            "neutral": max(0, neutral_score)
        }
        
        # Guardar
        self.sentiment_data.append({
            "text": text[:200],
            "sentiment": sentiment,
            "timestamp": datetime.now().isoformat()
        })
        
        if len(self.sentiment_data) % 10 == 0:
            self._save_json(self.sentiment_file, self.sentiment_data)
        
        return sentiment
    
    def get_dashboard_metrics(self, days: int = 30) -> Dict[str, any]:
        """Obtiene métricas para dashboard ejecutivo."""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        # Filtrar queries recientes
        recent_queries = [
            q for q in self.queries
            if datetime.fromisoformat(q["timestamp"]) >= cutoff_date
        ]
        
        # Métricas básicas
        total_queries = len(recent_queries)
        successful_queries = sum(1 for q in recent_queries if q.get("success", True))
        avg_response_time = sum(q.get("response_time", 0) for q in recent_queries) / max(total_queries, 1)
        
        # Documentos más consultados
        doc_counter = Counter()
        for q in recent_queries:
            for doc in q.get("documents_used", []):
                doc_counter[doc] += 1
        
        top_documents = [{"name": doc, "count": count} for doc, count in doc_counter.most_common(10)]
        
        # Análisis de sentimiento promedio
        recent_sentiments = [
            s for s in self.sentiment_data
            if datetime.fromisoformat(s["timestamp"]) >= cutoff_date
        ]
        
        avg_sentiment = {
            "positive": 0.5,
            "negative": 0.3,
            "neutral": 0.2
        }
        
        if recent_sentiments:
            avg_positive = sum(s["sentiment"]["positive"] for s in recent_sentiments) / len(recent_sentiments)
            avg_negative = sum(s["sentiment"]["negative"] for s in recent_sentiments) / len(recent_sentiments)
            avg_neutral = sum(s["sentiment"]["neutral"] for s in recent_sentiments) / len(recent_sentiments)
            avg_sentiment = {
                "positive": avg_positive,
                "negative": avg_negative,
                "neutral": avg_neutral
            }
        
        # Gaps de conocimiento (preguntas sin respuesta exitosa)
        failed_queries = [q for q in recent_queries if not q.get("success", True)]
        knowledge_gaps = [q["query"] for q in failed_queries[:10]]
        
        return {
            "total_queries": total_queries,
            "successful_queries": successful_queries,
            "success_rate": successful_queries / max(total_queries, 1),
            "avg_response_time": avg_response_time,
            "top_documents": top_documents,
            "avg_sentiment": avg_sentiment,
            "knowledge_gaps": knowledge_gaps,
            "period_days": days
        }
    
    def predict_frequent_questions(self, top_n: int = 10) -> List[Dict[str, any]]:
        """Predice preguntas frecuentes basado en patrones."""
        # Agrupar queries similares
        query_groups = defaultdict(list)
        
        for query in self.queries:
            # Normalizar query
            normalized = query["query"].lower().strip()
            # Agrupar por palabras clave principales
            key_words = [w for w in normalized.split() if len(w) > 4][:3]
            group_key = " ".join(key_words) if key_words else normalized[:20]
            query_groups[group_key].append(query)
        
        # Ordenar por frecuencia
        frequent = sorted(
            query_groups.items(),
            key=lambda x: len(x[1]),
            reverse=True
        )[:top_n]
        
        return [
            {
                "query_pattern": pattern,
                "count": len(queries),
                "example": queries[0]["query"] if queries else ""
            }
            for pattern, queries in frequent
        ]
    
    def get_roi_metrics(self) -> Dict[str, any]:
        """Calcula métricas de ROI para mostrar valor a clientes."""
        total_queries = len(self.queries)
        successful_queries = sum(1 for q in self.queries if q.get("success", True))
        
        # Estimación de tiempo ahorrado (asumiendo 5 min por consulta manual)
        time_saved_minutes = successful_queries * 5
        time_saved_hours = time_saved_minutes / 60
        
        # Estimación de costo ahorrado (asumiendo $50/hora de empleado)
        cost_saved = time_saved_hours * 50
        
        return {
            "total_queries": total_queries,
            "successful_queries": successful_queries,
            "time_saved_hours": round(time_saved_hours, 2),
            "estimated_cost_saved": round(cost_saved, 2),
            "efficiency_gain": f"{((time_saved_hours / max(total_queries * 0.1, 1)) * 100):.1f}%"
        }

