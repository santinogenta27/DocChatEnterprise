"""
Sistema de agentes AI para ventas y optimización de campañas publicitarias.

Este sistema integra:
- LangGraph: Para orquestación de workflows
- CrewAI: Para agentes especializados
- AutoGen: Para crítica y auto-corrección
- APIs: Para integración con plataformas de publicidad
"""
from .main import SalesAgentSystem
from .models import (
    CampaignData,
    PerformanceMetric,
    OptimizationRecommendation,
    CreativeSuggestion,
    BudgetAllocation,
    SalesAnalysisReport
)
from .api_stubs import AdsAPIStub, CRMAPIStub, AnalyticsAPIStub, CompetitorAnalysisStub

__version__ = "1.0.0"
__all__ = [
    "SalesAgentSystem",
    "CampaignData",
    "PerformanceMetric",
    "OptimizationRecommendation",
    "CreativeSuggestion",
    "BudgetAllocation",
    "SalesAnalysisReport",
    "AdsAPIStub",
    "CRMAPIStub",
    "AnalyticsAPIStub",
    "CompetitorAnalysisStub"
]

