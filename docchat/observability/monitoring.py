"""
Sistema de observabilidad y monitoring avanzado.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from ..config import AppConfig


@dataclass
class Metric:
    """Métrica de performance."""
    name: str
    value: float
    timestamp: str
    tags: Dict[str, str] = field(default_factory=dict)


@dataclass
class Trace:
    """Trace distribuido para debugging."""
    trace_id: str
    span_id: str
    operation: str
    start_time: float
    end_time: Optional[float] = None
    duration: Optional[float] = None
    metadata: Dict = field(default_factory=dict)


class MonitoringSystem:
    """
    Sistema de monitoring y observabilidad.
    """
    
    def __init__(self, config: AppConfig):
        self.config = config
        self.data_dir = Path(config.memory_dir) / "monitoring"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.metrics_file = self.data_dir / "metrics.json"
        self.traces_file = self.data_dir / "traces.json"
        self.errors_file = self.data_dir / "errors.json"
        
        self.metrics: List[Metric] = []
        self.traces: List[Trace] = []
        self.errors: List[Dict] = []
    
    def record_metric(self, name: str, value: float, tags: Dict[str, str] = None):
        """Registra una métrica."""
        metric = Metric(
            name=name,
            value=value,
            timestamp=datetime.now().isoformat(),
            tags=tags or {}
        )
        self.metrics.append(metric)
        
        # Guardar periódicamente
        if len(self.metrics) % 50 == 0:
            self._save_metrics()
    
    def start_trace(self, operation: str, metadata: Dict = None) -> Trace:
        """Inicia un trace."""
        import uuid
        trace_id = str(uuid.uuid4())
        span_id = str(uuid.uuid4())
        
        trace = Trace(
            trace_id=trace_id,
            span_id=span_id,
            operation=operation,
            start_time=time.time(),
            metadata=metadata or {}
        )
        
        self.traces.append(trace)
        return trace
    
    def end_trace(self, trace: Trace):
        """Termina un trace."""
        trace.end_time = time.time()
        trace.duration = trace.end_time - trace.start_time
        
        # Guardar
        if len(self.traces) % 20 == 0:
            self._save_traces()
    
    def record_error(self, error: Exception, context: Dict = None):
        """Registra un error."""
        error_data = {
            "error_type": type(error).__name__,
            "error_message": str(error),
            "timestamp": datetime.now().isoformat(),
            "context": context or {}
        }
        
        self.errors.append(error_data)
        
        # Guardar
        if len(self.errors) % 10 == 0:
            self._save_errors()
    
    def get_performance_metrics(self, hours: int = 24) -> Dict[str, any]:
        """Obtiene métricas de performance."""
        cutoff_time = time.time() - (hours * 3600)
        
        recent_metrics = [
            m for m in self.metrics
            if datetime.fromisoformat(m.timestamp).timestamp() >= cutoff_time
        ]
        
        # Agrupar por nombre
        metric_groups = {}
        for metric in recent_metrics:
            if metric.name not in metric_groups:
                metric_groups[metric.name] = []
            metric_groups[metric.name].append(metric.value)
        
        # Calcular estadísticas
        stats = {}
        for name, values in metric_groups.items():
            stats[name] = {
                "count": len(values),
                "avg": sum(values) / len(values),
                "min": min(values),
                "max": max(values)
            }
        
        return stats
    
    def get_error_summary(self, hours: int = 24) -> Dict[str, any]:
        """Obtiene resumen de errores."""
        cutoff_time = time.time() - (hours * 3600)
        
        recent_errors = [
            e for e in self.errors
            if datetime.fromisoformat(e["timestamp"]).timestamp() >= cutoff_time
        ]
        
        # Agrupar por tipo
        error_types = {}
        for error in recent_errors:
            error_type = error["error_type"]
            error_types[error_type] = error_types.get(error_type, 0) + 1
        
        return {
            "total_errors": len(recent_errors),
            "error_types": error_types,
            "recent_errors": recent_errors[-10:]  # Últimos 10
        }
    
    def _save_metrics(self):
        """Guarda métricas."""
        try:
            data = [
                {
                    "name": m.name,
                    "value": m.value,
                    "timestamp": m.timestamp,
                    "tags": m.tags
                }
                for m in self.metrics[-1000:]  # Guardar últimas 1000
            ]
            with open(self.metrics_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error guardando métricas: {e}")
    
    def _save_traces(self):
        """Guarda traces."""
        try:
            data = [
                {
                    "trace_id": t.trace_id,
                    "span_id": t.span_id,
                    "operation": t.operation,
                    "duration": t.duration,
                    "metadata": t.metadata
                }
                for t in self.traces[-500:]  # Guardar últimos 500
            ]
            with open(self.traces_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error guardando traces: {e}")
    
    def _save_errors(self):
        """Guarda errores."""
        try:
            with open(self.errors_file, 'w', encoding='utf-8') as f:
                json.dump(self.errors[-100:], f, indent=2, ensure_ascii=False)  # Últimos 100
        except Exception as e:
            print(f"Error guardando errores: {e}")

