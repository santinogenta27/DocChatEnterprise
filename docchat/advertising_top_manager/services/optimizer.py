"""
Campaign Optimizer Service
Implements Multi-Armed Bandit and optimization algorithms
Production-ready with robust error handling
"""
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
import numpy as np
import logging

try:
    from sklearn.ensemble import RandomForestRegressor
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

from ..utils.logging import setup_logger

logger = setup_logger("ads_worker.optimizer")

from ..models.schemas import AdPerformance, OptimizationResult


class CampaignOptimizer:
    """Optimizes campaigns using Multi-Armed Bandit and ML algorithms"""
    
    def __init__(self, epsilon: float = 0.1, min_impressions: int = 1000):
        """
        Initialize optimizer
        
        Args:
            epsilon: Exploration rate for epsilon-greedy (0-1)
            min_impressions: Minimum impressions before optimization
        """
        self.epsilon = epsilon
        self.min_impressions = min_impressions
        
        # Performance model
        self.performance_model = None
        if SKLEARN_AVAILABLE:
            self.performance_model = RandomForestRegressor(n_estimators=100, random_state=42)
    
    def fetch_metrics_from_providers(
        self,
        meta_service: Optional[Any],
        google_service: Optional[Any],
        campaign_ids: Dict[str, List[str]]
    ) -> List[AdPerformance]:
        """
        Fetch metrics from Meta and Google Ads
        
        Args:
            meta_service: MetaAdsService instance
            google_service: GoogleAdsService instance
            campaign_ids: Dict with platform -> list of campaign/ad IDs
            
        Returns:
            List of AdPerformance objects
        """
        logger.info(f"📊 Obteniendo métricas de plataformas...")
        performances = []
        
        # Fetch from Meta
        if meta_service and "meta" in campaign_ids:
            for ad_id in campaign_ids["meta"]:
                try:
                    # Get ad metrics (simplified - in production get from ad level)
                    metrics = meta_service.get_campaign_metrics(ad_id)
                    if metrics:
                        performance = AdPerformance(
                            ad_id=ad_id,
                            campaign_id=campaign_ids.get("campaign_id", ""),
                            platform="meta",
                            creative_id="",  # Will be set by caller
                            impressions=metrics.get("impressions", 0),
                            clicks=metrics.get("clicks", 0),
                            conversions=metrics.get("conversions", 0),
                            spend=metrics.get("spend", 0.0),
                            ctr=metrics.get("ctr", 0.0),
                            cpc=metrics.get("cpc", 0.0),
                            cpa=metrics.get("cpa", 0.0),
                            roas=metrics.get("roas", 0.0),
                            status="active",
                            created_at=datetime.now(),
                            updated_at=datetime.now(),
                            last_performance_update=datetime.now()
                        )
                        performances.append(performance)
                        logger.debug(f"   ✅ Métricas Meta obtenidas para ad: {ad_id}")
                except Exception as e:
                    logger.warning(f"⚠️ Error fetching Meta metrics for {ad_id}: {e}")
        
        # Fetch from Google
        if google_service and "google" in campaign_ids:
            for ad_id in campaign_ids["google"]:
                try:
                    metrics = google_service.get_campaign_metrics(ad_id)
                    if metrics:
                        performance = AdPerformance(
                            ad_id=ad_id,
                            campaign_id=campaign_ids.get("campaign_id", ""),
                            platform="google",
                            creative_id="",
                            impressions=metrics.get("impressions", 0),
                            clicks=metrics.get("clicks", 0),
                            conversions=metrics.get("conversions", 0),
                            spend=metrics.get("spend", 0.0),
                            ctr=metrics.get("ctr", 0.0),
                            cpc=metrics.get("cpc", 0.0),
                            cpa=metrics.get("cpa", 0.0),
                            roas=metrics.get("roas", 0.0),
                            status="active",
                            created_at=datetime.now(),
                            updated_at=datetime.now(),
                            last_performance_update=datetime.now()
                        )
                        performances.append(performance)
                        logger.debug(f"   ✅ Métricas Google obtenidas para ad: {ad_id}")
                except Exception as e:
                    logger.warning(f"⚠️ Error fetching Google metrics for {ad_id}: {e}")
        
        logger.info(f"✅ {len(performances)} métricas obtenidas en total")
        return performances
    
    def run_bandit_algorithm(
        self,
        performances: List[AdPerformance],
        optimization_goal: str = "conversions"
    ) -> List[Tuple[str, float]]:
        """
        Run Multi-Armed Bandit algorithm to rank ads
        
        Args:
            performances: List of ad performances
            optimization_goal: Goal to optimize for (conversions, ctr, roas, cpa)
            
        Returns:
            List of (ad_id, score) tuples sorted by performance
        """
        if not performances:
            logger.warning("No hay performances para optimizar")
            return []
        
        logger.info(f"🎰 Ejecutando algoritmo Multi-Armed Bandit (objetivo: {optimization_goal})")
        
        # Calculate scores based on optimization goal
        scores = []
        
        for perf in performances:
            if perf.impressions < self.min_impressions:
                # Not enough data, use exploration
                score = np.random.random() * self.epsilon
            else:
                # Exploitation: use actual performance
                if optimization_goal == "conversions":
                    score = perf.conversions / max(perf.spend, 1)  # Conversion rate per dollar
                elif optimization_goal == "ctr":
                    score = perf.ctr
                elif optimization_goal == "roas":
                    score = perf.roas
                elif optimization_goal == "cpa":
                    score = 1.0 / max(perf.cpa, 0.01)  # Inverse CPA (higher is better)
                else:
                    score = perf.ctr  # Default to CTR
                
                # Add exploration component
                if np.random.random() < self.epsilon:
                    score += np.random.random() * 0.1
            
            scores.append((perf.ad_id, score))
        
        # Sort by score (descending)
        scores.sort(key=lambda x: x[1], reverse=True)
        
        logger.info(f"✅ Ranking generado: {len(scores)} ads ordenados")
        if scores:
            logger.info(f"   Top ad: {scores[0][0]} (score: {scores[0][1]:.4f})")
        
        return scores
    
    def apply_budget_reassignment(
        self,
        ranking: List[Tuple[str, float]],
        total_budget: float,
        top_n: int = 3
    ) -> Dict[str, float]:
        """
        Reassign budget based on performance ranking
        
        Args:
            ranking: List of (ad_id, score) tuples
            total_budget: Total budget to allocate
            top_n: Number of top performers to focus on
            
        Returns:
            Dict mapping ad_id to new budget allocation
        """
        if not ranking:
            return {}
        
        # Allocate more budget to top performers
        top_ads = ranking[:top_n]
        remaining_ads = ranking[top_n:]
        
        # Calculate total score for normalization
        top_score_sum = sum(score for _, score in top_ads)
        remaining_score_sum = sum(score for _, score in remaining_ads) if remaining_ads else 0
        
        allocations = {}
        
        # Allocate 70% to top performers, 30% to others
        top_budget = total_budget * 0.7
        remaining_budget = total_budget * 0.3
        
        # Allocate top budget proportionally
        if top_score_sum > 0:
            for ad_id, score in top_ads:
                allocations[ad_id] = (score / top_score_sum) * top_budget
        
        # Allocate remaining budget proportionally
        if remaining_score_sum > 0 and remaining_ads:
            for ad_id, score in remaining_ads:
                allocations[ad_id] = (score / remaining_score_sum) * remaining_budget
        
        return allocations
    
    def pause_low_performance_ads(
        self,
        performances: List[AdPerformance],
        threshold_ctr: float = 0.01,
        threshold_cpa: Optional[float] = None,
        min_impressions: Optional[int] = None
    ) -> List[str]:
        """
        Identify ads that should be paused due to low performance
        
        Args:
            performances: List of ad performances
            threshold_ctr: Minimum CTR threshold
            threshold_cpa: Maximum CPA threshold (optional)
            min_impressions: Minimum impressions before considering pause
            
        Returns:
            List of ad IDs to pause
        """
        if min_impressions is None:
            min_impressions = self.min_impressions
        
        ads_to_pause = []
        
        for perf in performances:
            # Only consider ads with enough data
            if perf.impressions < min_impressions:
                continue
            
            should_pause = False
            
            # Check CTR threshold
            if perf.ctr < threshold_ctr:
                should_pause = True
            
            # Check CPA threshold if provided
            if threshold_cpa and perf.cpa > threshold_cpa and perf.conversions > 0:
                should_pause = True
            
            # Check if no conversions after significant spend
            if perf.spend > 50 and perf.conversions == 0:
                should_pause = True
            
            if should_pause:
                ads_to_pause.append(perf.ad_id)
        
        return ads_to_pause
    
    def optimize_campaign(
        self,
        performances: List[AdPerformance],
        total_budget: float,
        optimization_goal: str = "conversions"
    ) -> OptimizationResult:
        """
        Run complete optimization process
        
        Args:
            performances: List of ad performances
            total_budget: Total campaign budget
            optimization_goal: Optimization goal
            
        Returns:
            OptimizationResult with actions and recommendations
        """
        optimization_id = f"opt_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        campaign_id = performances[0].campaign_id if performances else ""
        
        logger.info(f"🔧 Iniciando optimización: {optimization_id}")
        logger.info(f"   - Campaña: {campaign_id}")
        logger.info(f"   - Ads: {len(performances)}")
        logger.info(f"   - Presupuesto total: ${total_budget}")
        logger.info(f"   - Objetivo: {optimization_goal}")
        
        # Run bandit algorithm
        ranking = self.run_bandit_algorithm(performances, optimization_goal)
        
        # Identify ads to pause
        ads_to_pause = self.pause_low_performance_ads(performances)
        
        # Identify top performers to scale
        top_ads = [ad_id for ad_id, _ in ranking[:3]]
        
        # Reassign budget
        budget_reallocation = self.apply_budget_reassignment(ranking, total_budget)
        
        # Calculate performance improvement (predicted)
        performance_improvement = {}
        if ranking:
            top_score = ranking[0][1]
            avg_score = np.mean([score for _, score in ranking])
            if avg_score > 0:
                performance_improvement["score_improvement"] = (top_score - avg_score) / avg_score
        
        # Generate recommendations
        recommendations = []
        if ads_to_pause:
            recommendations.append(f"Pause {len(ads_to_pause)} underperforming ads")
        if top_ads:
            recommendations.append(f"Scale budget for top {len(top_ads)} performing ads")
        if budget_reallocation:
            recommendations.append("Reallocate budget based on performance")
        
        logger.info(f"✅ Optimización completada: {optimization_id}")
        logger.info(f"   - Ads a pausar: {len(ads_to_pause)}")
        logger.info(f"   - Ads a escalar: {len(top_ads)}")
        logger.info(f"   - Recomendaciones: {len(recommendations)}")
        
        return OptimizationResult(
            optimization_id=optimization_id,
            campaign_id=campaign_id,
            ads_paused=ads_to_pause,
            ads_scaled=top_ads,
            budget_reallocated=budget_reallocation,
            performance_improvement=performance_improvement,
            recommendations=recommendations
        )


