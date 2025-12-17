"""
Stubs de APIs externas para integración con plataformas de publicidad y CRM.
Estos son placeholders que simulan llamadas a APIs reales.
"""
from typing import List, Dict, Optional
import random
from datetime import datetime, timedelta
from .models import CampaignData, CampaignStatus, PerformanceMetric


class AdsAPIStub:
    """Stub para API de plataformas publicitarias (Google Ads, Meta Ads, etc.)"""
    
    def __init__(self, platform: str = "google_ads"):
        self.platform = platform
        self._campaigns = self._generate_mock_campaigns()
    
    def _generate_mock_campaigns(self) -> List[Dict]:
        """Genera datos mock de campañas"""
        campaigns = []
        for i in range(5):
            campaigns.append({
                "campaign_id": f"camp_{i+1}",
                "name": f"Campaña {['Producto A', 'Producto B', 'Servicio Premium', 'Oferta Especial', 'Brand Awareness'][i]}",
                "status": random.choice(["active", "paused", "completed"]),
                "budget": random.uniform(50, 500),
                "start_date": (datetime.now() - timedelta(days=random.randint(1, 30))).isoformat(),
                "end_date": None if random.random() > 0.5 else (datetime.now() + timedelta(days=random.randint(1, 30))).isoformat(),
                "platform": self.platform,
            })
        return campaigns
    
    def get_campaigns(self, account_id: str) -> List[Dict]:
        """Obtiene lista de campañas"""
        return self._campaigns
    
    def get_campaign_performance(self, campaign_id: str, date_range: tuple) -> Dict:
        """Obtiene métricas de rendimiento de una campaña"""
        base_impressions = random.randint(10000, 100000)
        base_clicks = int(base_impressions * random.uniform(0.01, 0.05))
        base_conversions = int(base_clicks * random.uniform(0.02, 0.10))
        base_spend = random.uniform(100, 2000)
        base_revenue = base_spend * random.uniform(1.5, 4.0)
        
        return {
            "impressions": base_impressions,
            "clicks": base_clicks,
            "conversions": base_conversions,
            "spend": round(base_spend, 2),
            "revenue": round(base_revenue, 2),
            "ctr": round((base_clicks / base_impressions) * 100, 2),
            "cpc": round(base_spend / base_clicks, 2) if base_clicks > 0 else 0,
            "cpa": round(base_spend / base_conversions, 2) if base_conversions > 0 else 0,
            "roas": round(base_revenue / base_spend, 2) if base_spend > 0 else 0,
        }
    
    def update_campaign_budget(self, campaign_id: str, new_budget: float) -> bool:
        """Actualiza el presupuesto de una campaña"""
        return True
    
    def pause_campaign(self, campaign_id: str) -> bool:
        """Pausa una campaña"""
        return True
    
    def resume_campaign(self, campaign_id: str) -> bool:
        """Reanuda una campaña"""
        return True


class CRMAPIStub:
    """Stub para API de CRM (Salesforce, HubSpot, etc.)"""
    
    def get_customer_data(self, customer_id: str) -> Dict:
        """Obtiene datos de un cliente"""
        return {
            "customer_id": customer_id,
            "name": "Cliente Ejemplo",
            "lifetime_value": random.uniform(500, 5000),
            "last_purchase_date": (datetime.now() - timedelta(days=random.randint(1, 90))).isoformat(),
            "segment": random.choice(["VIP", "Regular", "New"]),
        }
    
    def get_sales_funnel_metrics(self, date_range: tuple) -> Dict:
        """Obtiene métricas del embudo de ventas"""
        return {
            "leads": random.randint(1000, 5000),
            "qualified_leads": random.randint(200, 1000),
            "opportunities": random.randint(50, 500),
            "closed_won": random.randint(10, 100),
            "conversion_rate": random.uniform(0.01, 0.05),
        }


class AnalyticsAPIStub:
    """Stub para API de analytics (Google Analytics, Adobe Analytics, etc.)"""
    
    def get_website_metrics(self, date_range: tuple) -> Dict:
        """Obtiene métricas del sitio web"""
        return {
            "sessions": random.randint(5000, 50000),
            "users": random.randint(3000, 30000),
            "pageviews": random.randint(10000, 100000),
            "bounce_rate": random.uniform(0.30, 0.70),
            "avg_session_duration": random.uniform(60, 300),
            "conversion_rate": random.uniform(0.01, 0.05),
        }
    
    def get_conversion_paths(self, conversion_id: str) -> List[Dict]:
        """Obtiene rutas de conversión"""
        return [
            {
                "path": "Organic Search > Landing Page > Product Page > Checkout",
                "conversions": random.randint(10, 100),
                "revenue": random.uniform(1000, 10000),
            }
        ]


class CompetitorAnalysisStub:
    """Stub para análisis de competencia"""
    
    def get_competitor_ads(self, industry: str) -> List[Dict]:
        """Obtiene anuncios de competidores"""
        return [
            {
                "headline": "Oferta Especial Competidor",
                "description": "Descripción del anuncio competidor",
                "estimated_spend": random.uniform(1000, 10000),
                "platform": "google_ads",
            }
        ]
    
    def get_market_trends(self, industry: str) -> Dict:
        """Obtiene tendencias del mercado"""
        return {
            "avg_cpc": random.uniform(1.0, 5.0),
            "avg_ctr": random.uniform(0.02, 0.08),
            "trending_keywords": ["keyword1", "keyword2", "keyword3"],
            "seasonality": "high" if random.random() > 0.5 else "low",
        }

