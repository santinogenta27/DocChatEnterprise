"""MÃ³dulos de inteligencia para STAR AGENT."""

from .behavior_analyzer import BehaviorAnalyzer, BehaviorAnalysis, PurchaseSignal, UrgencyLevel, CustomerSegment
from .proactive_suggestions import ProactiveSuggestionsEngine, ProactiveSuggestion, ProactiveActionType
from .closing_techniques import ClosingTechniquesManager, ClosingStrategy, ClosingTechnique
from .product_recommender import ProductRecommender, ProductRecommendation, RecommendationType

__all__ = [
    "BehaviorAnalyzer",
    "BehaviorAnalysis",
    "PurchaseSignal",
    "UrgencyLevel",
    "CustomerSegment",
    "ProactiveSuggestionsEngine",
    "ProactiveSuggestion",
    "ProactiveActionType",
    "ClosingTechniquesManager",
    "ClosingStrategy",
    "ClosingTechnique",
    "ProductRecommender",
    "ProductRecommendation",
    "RecommendationType",
]


