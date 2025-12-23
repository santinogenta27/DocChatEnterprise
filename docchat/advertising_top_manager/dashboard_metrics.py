"""
Dashboard de métricas visual para Advertising Top Manager
Muestra CTR, CPC, gasto, conversiones con gráficos simples
"""
from __future__ import annotations

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from pathlib import Path
import csv
import io

from .database import DatabaseManager


class DashboardMetrics:
    """Gestor de métricas para dashboard visual"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    def get_campaign_metrics(
        self, 
        campaign_id: Optional[str] = None,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Obtiene métricas de campaña(s)
        
        Args:
            campaign_id: ID de campaña específica (None = todas)
            days: Días hacia atrás para métricas
            
        Returns:
            Dict con métricas agregadas
        """
        if not self.db.SQLALCHEMY_AVAILABLE:
            return {
                "campaign_id": campaign_id or "all",
                "ctr": 0.0,
                "cpc": 0.0,
                "spend": 0.0,
                "conversions": 0,
                "impressions": 0,
                "clicks": 0,
                "daily_data": []
            }
        
        try:
            from sqlalchemy import func
            from .database import PerformanceMetricsDB, CampaignDB
            
            session = self.db.get_session()
            
            # Filtro por fecha
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            query = session.query(
                func.sum(PerformanceMetricsDB.impressions).label('total_impressions'),
                func.sum(PerformanceMetricsDB.clicks).label('total_clicks'),
                func.sum(PerformanceMetricsDB.conversions).label('total_conversions'),
                func.sum(PerformanceMetricsDB.spend).label('total_spend'),
                func.avg(PerformanceMetricsDB.ctr).label('avg_ctr'),
                func.avg(PerformanceMetricsDB.cpc).label('avg_cpc')
            ).filter(
                PerformanceMetricsDB.timestamp >= cutoff_date
            )
            
            # Filtrar por campaña si se especifica
            if campaign_id:
                query = query.filter(PerformanceMetricsDB.campaign_id == campaign_id)
            
            result = query.first()
            
            # Calcular métricas
            total_impressions = result.total_impressions or 0
            total_clicks = result.total_clicks or 0
            total_conversions = result.total_conversions or 0
            total_spend = result.total_spend or 0.0
            avg_ctr = result.avg_ctr or 0.0
            avg_cpc = result.avg_cpc or 0.0
            
            # Si no hay datos de CTR/CPC, calcularlos
            if total_impressions > 0 and avg_ctr == 0.0:
                avg_ctr = (total_clicks / total_impressions) * 100
            
            if total_clicks > 0 and avg_cpc == 0.0:
                avg_cpc = total_spend / total_clicks
            
            # Obtener datos diarios para gráficos
            daily_data = self._get_daily_metrics(campaign_id, days, session)
            
            session.close()
            
            return {
                "campaign_id": campaign_id or "all",
                "ctr": round(avg_ctr, 2),
                "cpc": round(avg_cpc, 2),
                "spend": round(total_spend, 2),
                "conversions": int(total_conversions),
                "impressions": int(total_impressions),
                "clicks": int(total_clicks),
                "daily_data": daily_data
            }
            
        except Exception as e:
            print(f"❌ Error obteniendo métricas: {e}")
            import traceback
            traceback.print_exc()
            return {
                "campaign_id": campaign_id or "all",
                "ctr": 0.0,
                "cpc": 0.0,
                "spend": 0.0,
                "conversions": 0,
                "impressions": 0,
                "clicks": 0,
                "daily_data": []
            }
    
    def _get_daily_metrics(
        self, 
        campaign_id: Optional[str], 
        days: int,
        session
    ) -> List[Dict[str, Any]]:
        """Obtiene métricas agrupadas por día"""
        try:
            from sqlalchemy import func, Date
            from .database import PerformanceMetricsDB
            
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            query = session.query(
                func.date(PerformanceMetricsDB.timestamp).label('date'),
                func.sum(PerformanceMetricsDB.spend).label('spend'),
                func.sum(PerformanceMetricsDB.conversions).label('conversions'),
                func.sum(PerformanceMetricsDB.clicks).label('clicks'),
                func.sum(PerformanceMetricsDB.impressions).label('impressions')
            ).filter(
                PerformanceMetricsDB.timestamp >= cutoff_date
            ).group_by(
                func.date(PerformanceMetricsDB.timestamp)
            )
            
            if campaign_id:
                query = query.filter(PerformanceMetricsDB.campaign_id == campaign_id)
            
            results = query.order_by(func.date(PerformanceMetricsDB.timestamp)).all()
            
            daily_data = []
            for row in results:
                daily_ctr = 0.0
                if row.impressions and row.impressions > 0:
                    daily_ctr = (row.clicks / row.impressions) * 100
                
                daily_cpc = 0.0
                if row.clicks and row.clicks > 0:
                    daily_cpc = row.spend / row.clicks
                
                daily_data.append({
                    "date": row.date.isoformat() if row.date else "",
                    "spend": round(row.spend or 0.0, 2),
                    "conversions": int(row.conversions or 0),
                    "clicks": int(row.clicks or 0),
                    "impressions": int(row.impressions or 0),
                    "ctr": round(daily_ctr, 2),
                    "cpc": round(daily_cpc, 2)
                })
            
            return daily_data
            
        except Exception as e:
            print(f"❌ Error obteniendo métricas diarias: {e}")
            return []
    
    def list_campaigns(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Lista todas las campañas disponibles"""
        if not self.db.SQLALCHEMY_AVAILABLE:
            return []
        
        try:
            from .database import CampaignDB
            
            session = self.db.get_session()
            
            query = session.query(CampaignDB).order_by(CampaignDB.created_at.desc())
            
            if user_id:
                query = query.filter(CampaignDB.user_id == user_id)
            
            campaigns = query.all()
            
            result = []
            for campaign in campaigns:
                result.append({
                    "campaign_id": campaign.campaign_id,
                    "name": campaign.name,
                    "status": campaign.status,
                    "platforms": campaign.platforms,
                    "budget_daily": campaign.budget_daily,
                    "created_at": campaign.created_at.isoformat() if campaign.created_at else ""
                })
            
            session.close()
            return result
            
        except Exception as e:
            print(f"❌ Error listando campañas: {e}")
            return []
    
    def export_csv(
        self,
        campaign_id: Optional[str] = None,
        days: int = 30
    ) -> str:
        """
        Exporta métricas a CSV
        
        Returns:
            String con contenido CSV
        """
        if not self.db.SQLALCHEMY_AVAILABLE:
            return "Fecha,Campaña,CTR,CPC,Gasto,Conversiones\n"
        
        try:
            from sqlalchemy import func
            from .database import PerformanceMetricsDB, CampaignDB
            
            session = self.db.get_session()
            
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            # Query con join a campaigns para obtener nombre
            query = session.query(
                func.date(PerformanceMetricsDB.timestamp).label('date'),
                CampaignDB.name.label('campaign_name'),
                CampaignDB.campaign_id,
                func.avg(PerformanceMetricsDB.ctr).label('avg_ctr'),
                func.avg(PerformanceMetricsDB.cpc).label('avg_cpc'),
                func.sum(PerformanceMetricsDB.spend).label('total_spend'),
                func.sum(PerformanceMetricsDB.conversions).label('total_conversions')
            ).join(
                CampaignDB, PerformanceMetricsDB.campaign_id == CampaignDB.campaign_id
            ).filter(
                PerformanceMetricsDB.timestamp >= cutoff_date
            ).group_by(
                func.date(PerformanceMetricsDB.timestamp),
                CampaignDB.campaign_id,
                CampaignDB.name
            )
            
            if campaign_id:
                query = query.filter(PerformanceMetricsDB.campaign_id == campaign_id)
            
            results = query.order_by(func.date(PerformanceMetricsDB.timestamp).desc()).all()
            
            # Crear CSV en memoria
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Header
            writer.writerow(['Fecha', 'Campaña', 'CTR (%)', 'CPC ($)', 'Gasto ($)', 'Conversiones'])
            
            # Datos
            for row in results:
                avg_ctr = row.avg_ctr or 0.0
                avg_cpc = row.avg_cpc or 0.0
                total_spend = row.total_spend or 0.0
                total_conversions = row.total_conversions or 0
                
                writer.writerow([
                    row.date.isoformat() if row.date else "",
                    row.campaign_name or "N/A",
                    f"{avg_ctr:.2f}",
                    f"{avg_cpc:.2f}",
                    f"{total_spend:.2f}",
                    int(total_conversions)
                ])
            
            csv_content = output.getvalue()
            output.close()
            session.close()
            
            return csv_content
            
        except Exception as e:
            print(f"❌ Error exportando CSV: {e}")
            import traceback
            traceback.print_exc()
            return "Fecha,Campaña,CTR,CPC,Gasto,Conversiones\n"

