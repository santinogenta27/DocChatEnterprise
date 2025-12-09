"""
Dashboard Ejecutivo para el modo BANKS.
Proporciona métricas, KPIs y visualizaciones en tiempo real.
"""

from __future__ import annotations

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict

from docchat.config import AppConfig
from .banks_mode import BanksMode

logger = logging.getLogger(__name__)


class BanksDashboard:
    """Dashboard ejecutivo con métricas y KPIs."""
    
    def __init__(self, config: AppConfig):
        self.config = config
        self.banks_mode = BanksMode(config)
        self.audit_dir = Path(config.audit_log_dir) / "banks"
        self.reports_dir = Path(config.cache_dir) / "banks" / "reports"
    
    def get_executive_summary(self, days: int = 30) -> Dict[str, Any]:
        """Genera resumen ejecutivo de los últimos N días."""
        try:
            # Analizar logs de auditoría
            total_checks = 0
            total_entities = 0
            high_risk_count = 0
            sars_generated = 0
            avg_processing_time = 0.0
            
            # Contar reportes
            if self.reports_dir.exists():
                reports = list(self.reports_dir.glob("*"))
                sars_generated = len([r for r in reports if r.suffix == ".xml"])
            
            # Analizar logs (simplificado - en producción usar base de datos)
            cutoff_date = datetime.now() - timedelta(days=days)
            
            for agent_dir in self.audit_dir.glob("*"):
                if agent_dir.is_dir():
                    for log_file in agent_dir.glob("*.json"):
                        try:
                            import json
                            with open(log_file, 'r', encoding='utf-8') as f:
                                log_data = json.load(f)
                            
                            timestamp = datetime.fromisoformat(log_data.get("timestamp", ""))
                            if timestamp >= cutoff_date:
                                if log_data.get("action") == "compliance_check":
                                    total_checks += 1
                                    output = log_data.get("output_data", {})
                                    total_entities += output.get("entities_count", 0)
                                    high_risk_count += output.get("high_risk_count", 0)
                        except Exception as e:
                            logger.warning(f"Error leyendo log {log_file}: {e}")
            
            # Calcular métricas
            avg_entities_per_check = total_entities / total_checks if total_checks > 0 else 0
            high_risk_percentage = (high_risk_count / total_entities * 100) if total_entities > 0 else 0
            
            return {
                "period_days": days,
                "total_compliance_checks": total_checks,
                "total_entities_processed": total_entities,
                "high_risk_entities": high_risk_count,
                "high_risk_percentage": round(high_risk_percentage, 2),
                "sars_generated": sars_generated,
                "avg_entities_per_check": round(avg_entities_per_check, 1),
                "avg_processing_time_seconds": round(avg_processing_time, 2),
                "compliance_rate": 100.0,  # En producción, calcular basado en errores
                "last_updated": datetime.now().isoformat()
            }
        
        except Exception as e:
            logger.error(f"Error generando resumen ejecutivo: {e}", exc_info=True)
            return {
                "error": str(e),
                "period_days": days,
                "total_compliance_checks": 0,
                "total_entities_processed": 0,
                "high_risk_entities": 0,
                "high_risk_percentage": 0.0,
                "sars_generated": 0,
                "last_updated": datetime.now().isoformat()
            }
    
    def get_risk_distribution(self) -> Dict[str, int]:
        """Retorna distribución de riesgos."""
        distribution = {
            "critical": 0,  # 90-100
            "high": 0,      # 70-89
            "medium": 0,     # 50-69
            "low": 0,       # 30-49
            "very_low": 0   # 1-29
        }
        
        try:
            # Analizar reportes y logs para obtener scores
            # En producción, esto vendría de una base de datos
            for agent_dir in self.audit_dir.glob("*"):
                if agent_dir.is_dir() and agent_dir.name == "risk_engine":
                    for log_file in agent_dir.glob("*.json"):
                        try:
                            import json
                            with open(log_file, 'r', encoding='utf-8') as f:
                                log_data = json.load(f)
                            
                            output = log_data.get("output_data", {})
                            scores = output.get("risk_scores", [])
                            
                            for score in scores:
                                if isinstance(score, dict):
                                    total_score = score.get("total_score", 0)
                                else:
                                    total_score = getattr(score, "total_score", 0)
                                
                                if total_score >= 90:
                                    distribution["critical"] += 1
                                elif total_score >= 70:
                                    distribution["high"] += 1
                                elif total_score >= 50:
                                    distribution["medium"] += 1
                                elif total_score >= 30:
                                    distribution["low"] += 1
                                else:
                                    distribution["very_low"] += 1
                        except Exception as e:
                            logger.warning(f"Error procesando log: {e}")
        except Exception as e:
            logger.error(f"Error calculando distribución: {e}")
        
        return distribution
    
    def get_jurisdiction_stats(self) -> Dict[str, int]:
        """Estadísticas por jurisdicción."""
        stats = defaultdict(int)
        
        try:
            for agent_dir in self.audit_dir.glob("*"):
                if agent_dir.is_dir():
                    for log_file in agent_dir.glob("*.json"):
                        try:
                            import json
                            with open(log_file, 'r', encoding='utf-8') as f:
                                log_data = json.load(f)
                            
                            input_data = log_data.get("input_data", {})
                            jurisdiction = input_data.get("jurisdiction", "Unknown")
                            stats[jurisdiction] += 1
                        except Exception:
                            pass
        except Exception as e:
            logger.error(f"Error calculando stats por jurisdicción: {e}")
        
        return dict(stats)
    
    def get_trends(self, days: int = 30) -> Dict[str, List[Dict[str, Any]]]:
        """Tendencias de los últimos N días."""
        trends = {
            "daily_checks": [],
            "daily_entities": [],
            "daily_high_risk": []
        }
        
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            daily_data = defaultdict(lambda: {"checks": 0, "entities": 0, "high_risk": 0})
            
            for agent_dir in self.audit_dir.glob("*"):
                if agent_dir.is_dir():
                    for log_file in agent_dir.glob("*.json"):
                        try:
                            import json
                            with open(log_file, 'r', encoding='utf-8') as f:
                                log_data = json.load(f)
                            
                            timestamp = datetime.fromisoformat(log_data.get("timestamp", ""))
                            if timestamp >= cutoff_date:
                                date_key = timestamp.date().isoformat()
                                
                                if log_data.get("action") == "compliance_check":
                                    daily_data[date_key]["checks"] += 1
                                    output = log_data.get("output_data", {})
                                    daily_data[date_key]["entities"] += output.get("entities_count", 0)
                                    daily_data[date_key]["high_risk"] += output.get("high_risk_count", 0)
                        except Exception:
                            pass
            
            # Ordenar por fecha
            for date_str in sorted(daily_data.keys()):
                data = daily_data[date_str]
                trends["daily_checks"].append({"date": date_str, "value": data["checks"]})
                trends["daily_entities"].append({"date": date_str, "value": data["entities"]})
                trends["daily_high_risk"].append({"date": date_str, "value": data["high_risk"]})
        
        except Exception as e:
            logger.error(f"Error calculando tendencias: {e}")
        
        return trends
    
    def get_roi_metrics(self) -> Dict[str, Any]:
        """Calcula métricas de ROI."""
        summary = self.get_executive_summary(days=30)
        
        # Estimaciones basadas en datos típicos
        avg_time_per_entity_minutes = 15  # Tiempo manual promedio
        analyst_hourly_rate = 50  # USD por hora
        entities_processed = summary.get("total_entities_processed", 0)
        
        # Cálculos
        manual_time_hours = (entities_processed * avg_time_per_entity_minutes) / 60
        manual_cost = manual_time_hours * analyst_hourly_rate
        
        # Tiempo con BANKS (asumiendo 70% reducción)
        automated_time_hours = manual_time_hours * 0.3
        automated_cost = automated_time_hours * analyst_hourly_rate
        
        time_saved_hours = manual_time_hours - automated_time_hours
        cost_saved = manual_cost - automated_cost
        
        return {
            "entities_processed": entities_processed,
            "manual_time_hours": round(manual_time_hours, 1),
            "automated_time_hours": round(automated_time_hours, 1),
            "time_saved_hours": round(time_saved_hours, 1),
            "time_saved_percentage": 70.0,
            "manual_cost_usd": round(manual_cost, 2),
            "automated_cost_usd": round(automated_cost, 2),
            "cost_saved_usd": round(cost_saved, 2),
            "roi_percentage": round((cost_saved / (summary.get("total_compliance_checks", 1) * 15000 / 30)) * 100, 1) if summary.get("total_compliance_checks", 0) > 0 else 0,
            "period_days": 30
        }
    
    def get_full_dashboard(self) -> Dict[str, Any]:
        """Genera dashboard completo."""
        return {
            "executive_summary": self.get_executive_summary(),
            "risk_distribution": self.get_risk_distribution(),
            "jurisdiction_stats": self.get_jurisdiction_stats(),
            "trends": self.get_trends(),
            "roi_metrics": self.get_roi_metrics(),
            "generated_at": datetime.now().isoformat()
        }


