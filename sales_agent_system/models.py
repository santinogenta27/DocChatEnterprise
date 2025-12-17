"""
Modelos de datos Pydantic para el sistema de ventas con agentes AI.
Define la estructura de datos para campañas, análisis, optimizaciones y recomendaciones.
"""
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Literal
from datetime import datetime
from enum import Enum


class CampaignStatus(str, Enum):
    """Estado de una campaña publicitaria"""
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    DRAFT = "draft"


class PerformanceMetric(BaseModel):
    """Métrica de rendimiento de campaña"""
    impressions: int = Field(description="Número de impresiones")
    clicks: int = Field(description="Número de clics")
    conversions: int = Field(description="Número de conversiones")
    spend: float = Field(description="Gasto total en USD")
    revenue: float = Field(description="Ingresos generados en USD")
    ctr: float = Field(description="Click-through rate (%)")
    cpc: float = Field(description="Costo por clic (USD)")
    cpa: float = Field(description="Costo por adquisición (USD)")
    roas: float = Field(description="Return on ad spend")


class CampaignData(BaseModel):
    """Datos de una campaña publicitaria"""
    campaign_id: str = Field(description="ID único de la campaña")
    name: str = Field(description="Nombre de la campaña")
    status: CampaignStatus = Field(description="Estado actual")
    budget: float = Field(description="Presupuesto diario en USD")
    start_date: str = Field(description="Fecha de inicio")
    end_date: Optional[str] = Field(description="Fecha de fin (opcional)")
    platform: str = Field(description="Plataforma (Google Ads, Meta Ads, etc.)")
    performance: PerformanceMetric = Field(description="Métricas de rendimiento")


class OptimizationRecommendation(BaseModel):
    """Recomendación de optimización"""
    recommendation_type: Literal["budget", "bid", "targeting", "creative", "timing"] = Field(
        description="Tipo de recomendación"
    )
    priority: Literal["high", "medium", "low"] = Field(description="Prioridad")
    description: str = Field(description="Descripción de la recomendación")
    expected_impact: str = Field(description="Impacto esperado")
    action_items: List[str] = Field(description="Acciones específicas a tomar")
    estimated_roi_improvement: float = Field(description="Mejora estimada de ROI (%)")


class CreativeSuggestion(BaseModel):
    """Sugerencia de creativo publicitario"""
    headline: str = Field(description="Título del anuncio")
    description: str = Field(description="Descripción del anuncio")
    call_to_action: str = Field(description="Llamada a la acción")
    target_audience: str = Field(description="Audiencia objetivo")
    rationale: str = Field(description="Razón de la sugerencia")
    expected_performance: str = Field(description="Rendimiento esperado")


class BudgetAllocation(BaseModel):
    """Asignación de presupuesto optimizada"""
    campaign_id: str = Field(description="ID de campaña")
    current_budget: float = Field(description="Presupuesto actual")
    recommended_budget: float = Field(description="Presupuesto recomendado")
    adjustment_reason: str = Field(description="Razón del ajuste")
    expected_impact: str = Field(description="Impacto esperado del cambio")


class SalesAnalysisReport(BaseModel):
    """Reporte completo de análisis de ventas"""
    campaign_summary: CampaignData = Field(description="Resumen de campaña")
    top_performers: List[CampaignData] = Field(description="Campañas con mejor rendimiento")
    underperformers: List[CampaignData] = Field(description="Campañas con bajo rendimiento")
    recommendations: List[OptimizationRecommendation] = Field(description="Recomendaciones")
    budget_allocations: List[BudgetAllocation] = Field(description="Asignaciones de presupuesto")
    creative_suggestions: List[CreativeSuggestion] = Field(description="Sugerencias creativas")
    overall_roi: float = Field(description="ROI general")
    next_steps: List[str] = Field(description="Próximos pasos recomendados")
    generated_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class AgentState(BaseModel):
    """Estado compartido entre agentes en el workflow"""
    user_query: str = Field(description="Consulta del usuario")
    campaign_data: Optional[List[CampaignData]] = None
    analysis_complete: bool = False
    optimization_complete: bool = False
    creative_generation_complete: bool = False
    critique_complete: bool = False
    final_report: Optional[SalesAnalysisReport] = None
    errors: List[str] = Field(default_factory=list)
    iteration_count: int = 0
    max_iterations: int = 3

