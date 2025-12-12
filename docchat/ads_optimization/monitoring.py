"""
Sistema de Monitoring y Alertas
Métricas con Prometheus, alertas automáticas
"""

from __future__ import annotations

import time
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

try:
    from prometheus_client import Counter, Histogram, Gauge, start_http_server
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    print("⚠️ Prometheus no disponible. Instala con: pip install prometheus-client")


class AlertLevel(Enum):
    """Niveles de alerta"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class Alert:
    """Alerta del sistema"""
    alert_id: str
    level: AlertLevel
    title: str
    message: str
    campaign_id: Optional[str] = None
    tenant_id: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    resolved: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


class MetricsCollector:
    """Colector de métricas con Prometheus"""
    
    def __init__(self):
        if PROMETHEUS_AVAILABLE:
            # Counters
            self.campaigns_created = Counter(
                'ads_campaigns_created_total',
                'Total campaigns created'
            )
            self.assets_uploaded = Counter(
                'ads_assets_uploaded_total',
                'Total assets uploaded'
            )
            self.variations_generated = Counter(
                'ads_variations_generated_total',
                'Total variations generated'
            )
            self.predictions_made = Counter(
                'ads_predictions_made_total',
                'Total predictions made'
            )
            self.api_calls = Counter(
                'ads_api_calls_total',
                'Total API calls',
                ['platform', 'status']
            )
            
            # Histograms
            self.prediction_latency = Histogram(
                'ads_prediction_latency_seconds',
                'Prediction latency',
                buckets=[0.1, 0.5, 1.0, 2.0, 5.0]
            )
            self.api_latency = Histogram(
                'ads_api_latency_seconds',
                'API call latency',
                ['platform'],
                buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
            )
            
            # Gauges
            self.active_campaigns = Gauge(
                'ads_active_campaigns',
                'Number of active campaigns'
            )
            self.total_spend = Gauge(
                'ads_total_spend_usd',
                'Total spend in USD'
            )
            self.avg_ctr = Gauge(
                'ads_avg_ctr',
                'Average CTR'
            )
            self.avg_roas = Gauge(
                'ads_avg_roas',
                'Average ROAS'
            )
        else:
            # Fallback sin Prometheus
            self.metrics: Dict[str, float] = {}
    
    def record_campaign_created(self):
        """Registra creación de campaña"""
        if PROMETHEUS_AVAILABLE:
            self.campaigns_created.inc()
        else:
            self.metrics["campaigns_created"] = self.metrics.get("campaigns_created", 0) + 1
    
    def record_asset_uploaded(self):
        """Registra subida de asset"""
        if PROMETHEUS_AVAILABLE:
            self.assets_uploaded.inc()
        else:
            self.metrics["assets_uploaded"] = self.metrics.get("assets_uploaded", 0) + 1
    
    def record_prediction(self, latency: float):
        """Registra predicción con latencia"""
        if PROMETHEUS_AVAILABLE:
            self.predictions_made.inc()
            self.prediction_latency.observe(latency)
        else:
            self.metrics["predictions_made"] = self.metrics.get("predictions_made", 0) + 1
            self.metrics["prediction_latency"] = latency
    
    def record_api_call(self, platform: str, status: str, latency: float):
        """Registra llamada a API"""
        if PROMETHEUS_AVAILABLE:
            self.api_calls.labels(platform=platform, status=status).inc()
            self.api_latency.labels(platform=platform).observe(latency)
        else:
            key = f"api_calls_{platform}_{status}"
            self.metrics[key] = self.metrics.get(key, 0) + 1
    
    def update_active_campaigns(self, count: int):
        """Actualiza número de campañas activas"""
        if PROMETHEUS_AVAILABLE:
            self.active_campaigns.set(count)
        else:
            self.metrics["active_campaigns"] = count
    
    def update_spend(self, amount: float):
        """Actualiza gasto total"""
        if PROMETHEUS_AVAILABLE:
            self.total_spend.set(amount)
        else:
            self.metrics["total_spend"] = amount
    
    def update_avg_metrics(self, ctr: float, roas: float):
        """Actualiza métricas promedio"""
        if PROMETHEUS_AVAILABLE:
            self.avg_ctr.set(ctr)
            self.avg_roas.set(roas)
        else:
            self.metrics["avg_ctr"] = ctr
            self.metrics["avg_roas"] = roas
    
    def start_metrics_server(self, port: int = 8000):
        """Inicia servidor de métricas Prometheus"""
        if PROMETHEUS_AVAILABLE:
            start_http_server(port)
            print(f"✅ Prometheus metrics server iniciado en puerto {port}")


class AlertManager:
    """Gestor de alertas"""
    
    def __init__(self):
        self.alerts: List[Alert] = []
        self.alert_rules: List[Dict[str, Any]] = []
        self._setup_default_rules()
    
    def _setup_default_rules(self):
        """Configura reglas de alerta por defecto"""
        self.alert_rules = [
            {
                "name": "low_ctr",
                "condition": lambda metrics: metrics.get("ctr", 0) < 0.01,
                "level": AlertLevel.WARNING,
                "message": "CTR muy bajo (< 1%)"
            },
            {
                "name": "high_cpc",
                "condition": lambda metrics: metrics.get("cpc", 0) > 10.0,
                "level": AlertLevel.WARNING,
                "message": "CPC muy alto (> $10)"
            },
            {
                "name": "low_roas",
                "condition": lambda metrics: metrics.get("roas", 0) < 1.0 and metrics.get("spend", 0) > 100,
                "level": AlertLevel.ERROR,
                "message": "ROAS negativo o muy bajo"
            },
            {
                "name": "budget_exhausted",
                "condition": lambda metrics: metrics.get("spend", 0) >= metrics.get("budget", 0) * 0.95,
                "level": AlertLevel.WARNING,
                "message": "Presupuesto casi agotado (> 95%)"
            }
        ]
    
    def check_alerts(self, metrics: Dict[str, Any], campaign_id: str, tenant_id: str) -> List[Alert]:
        """Verifica reglas de alerta y genera alertas"""
        new_alerts = []
        
        for rule in self.alert_rules:
            if rule["condition"](metrics):
                alert = Alert(
                    alert_id=f"alert_{int(time.time())}_{len(self.alerts)}",
                    level=rule["level"],
                    title=rule["name"],
                    message=rule["message"],
                    campaign_id=campaign_id,
                    tenant_id=tenant_id,
                    metadata={"metrics": metrics}
                )
                new_alerts.append(alert)
                self.alerts.append(alert)
        
        return new_alerts
    
    def get_active_alerts(
        self,
        tenant_id: Optional[str] = None,
        campaign_id: Optional[str] = None,
        level: Optional[AlertLevel] = None
    ) -> List[Alert]:
        """Obtiene alertas activas"""
        alerts = [a for a in self.alerts if not a.resolved]
        
        if tenant_id:
            alerts = [a for a in alerts if a.tenant_id == tenant_id]
        if campaign_id:
            alerts = [a for a in alerts if a.campaign_id == campaign_id]
        if level:
            alerts = [a for a in alerts if a.level == level]
        
        return alerts
    
    def resolve_alert(self, alert_id: str):
        """Resuelve una alerta"""
        for alert in self.alerts:
            if alert.alert_id == alert_id:
                alert.resolved = True
                break


class MonitoringSystem:
    """Sistema completo de monitoring"""
    
    def __init__(self, start_metrics_server: bool = False, metrics_port: int = 8000):
        self.metrics = MetricsCollector()
        self.alerts = AlertManager()
        
        if start_metrics_server:
            self.metrics.start_metrics_server(metrics_port)
    
    def record_campaign_created(self):
        """Registra creación de campaña"""
        self.metrics.record_campaign_created()
    
    def record_asset_uploaded(self):
        """Registra subida de asset"""
        self.metrics.record_asset_uploaded()
    
    def record_prediction(self, latency: float):
        """Registra predicción"""
        self.metrics.record_prediction(latency)
    
    def record_api_call(self, platform: str, success: bool, latency: float):
        """Registra llamada a API"""
        status = "success" if success else "error"
        self.metrics.record_api_call(platform, status, latency)
    
    def check_campaign_alerts(
        self,
        campaign_id: str,
        tenant_id: str,
        metrics: Dict[str, Any]
    ) -> List[Alert]:
        """Verifica alertas para una campaña"""
        return self.alerts.check_alerts(metrics, campaign_id, tenant_id)
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Obtiene resumen de métricas"""
        if PROMETHEUS_AVAILABLE:
            # En producción, obtener de Prometheus
            return {
                "note": "Métricas disponibles en /metrics endpoint"
            }
        else:
            return self.metrics.metrics

