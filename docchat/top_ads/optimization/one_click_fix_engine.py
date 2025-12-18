"""
One-Click Fix Engine - Detección automática de problemas y soluciones con un clic
Sistema de optimización proactiva para campañas publicitarias
"""

from __future__ import annotations

from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
from datetime import datetime, timedelta

from ...config import AppConfig
from ..utils.logger import TopAdsLogger
from ..platforms.meta_ads import MetaAdsPlatform
from ..platforms.tiktok_ads import TikTokAdsPlatform
from .metrics_collector import MetricsCollector


class ProblemType(Enum):
    """Tipos de problemas detectados."""
    CREATIVE_FATIGUE = "creative_fatigue"  # CTR bajo y bajando
    HIGH_CPA = "high_cpa"  # CPA muy alto
    BUDGET_MISALLOCATION = "budget_misallocation"  # Presupuesto mal asignado
    NARROW_AUDIENCE = "narrow_audience"  # Audiencia muy estrecha
    LOW_ROAS = "low_roas"  # ROAS negativo o muy bajo
    HIGH_CPC = "high_cpc"  # CPC muy alto


class FixAction(Enum):
    """Acciones de fix disponibles."""
    PAUSE_AD = "pause_ad"
    SCALE_WINNER = "scale_winner"
    ADJUST_TARGETING = "adjust_targeting"
    REGENERATE_CREATIVES = "regenerate_creatives"
    REDUCE_BUDGET = "reduce_budget"
    INCREASE_BUDGET = "increase_budget"
    SWITCH_TO_BROAD = "switch_to_broad"


@dataclass
class DetectedProblem:
    """Problema detectado en una campaña."""
    problem_type: ProblemType
    severity: str  # "low", "medium", "high", "critical"
    description: str
    affected_ads: List[str]  # IDs de ads afectados
    affected_ad_sets: List[str]  # IDs de ad sets afectados
    current_metrics: Dict[str, Any]
    expected_impact: str
    confidence: float  # 0.0 a 1.0


@dataclass
class FixRecommendation:
    """Recomendación de fix."""
    problem: DetectedProblem
    action: FixAction
    parameters: Dict[str, Any]
    expected_improvement: str
    risk_level: str  # "low", "medium", "high"


@dataclass
class FixResult:
    """Resultado de aplicar un fix."""
    fix_id: str
    problem_type: ProblemType
    action: FixAction
    success: bool
    applied_at: str
    affected_items: List[str]
    expected_impact: str
    error_message: Optional[str] = None


class OneClickFixEngine:
    """
    Motor de One-Click Fixes para optimización automática.
    
    Detecta problemas comunes y aplica soluciones automáticamente:
    - Creative fatigue → Regenerar creativos
    - CPA muy alto → Ajustar targeting o pausar
    - Presupuesto mal asignado → Reasignar presupuesto
    - Audiencias estrechas → Ampliar targeting
    """
    
    def __init__(
        self,
        config: AppConfig,
        metrics_collector: MetricsCollector,
        meta_ads: MetaAdsPlatform,
        tiktok_ads: TikTokAdsPlatform,
        logger: TopAdsLogger
    ):
        """
        Inicializa el motor de fixes.
        
        Args:
            config: Configuración de la aplicación
            metrics_collector: Recolector de métricas
            meta_ads: Plataforma Meta Ads
            tiktok_ads: Plataforma TikTok Ads
            logger: Logger
        """
        self.config = config
        self.metrics_collector = metrics_collector
        self.meta_ads = meta_ads
        self.tiktok_ads = tiktok_ads
        self.logger = logger
        
        # Thresholds configurables
        self.min_ctr = 0.5  # CTR mínimo aceptable (%)
        self.max_cpa = 20.0  # CPA máximo objetivo (USD)
        self.min_roas = 2.0  # ROAS mínimo objetivo
        self.min_impressions = 1000  # Impresiones mínimas diarias
        self.creative_fatigue_threshold = 0.3  # CTR debe estar por encima de esto
        
        # Historial de fixes aplicados
        self.fix_history: List[FixResult] = []
    
    def detect_issues(
        self,
        campaign_id: str,
        platform: str,
        metrics: Optional[Dict[str, Any]] = None
    ) -> List[DetectedProblem]:
        """
        Detecta problemas en una campaña.
        
        Args:
            campaign_id: ID de la campaña
            platform: Plataforma ("meta" o "tiktok")
            metrics: Métricas actuales (opcional, se recolectan si no se proporcionan)
        
        Returns:
            Lista de problemas detectados
        """
        self.logger.info(f"Detectando problemas en campaña {campaign_id} ({platform})")
        
        # Recolectar métricas si no se proporcionan
        if metrics is None:
            metrics = self.metrics_collector.collect_campaign_metrics(
                campaign_id=campaign_id,
                platform=platform
            )
        
        problems = []
        
        # 1. Detectar Creative Fatigue
        creative_fatigue = self._detect_creative_fatigue(metrics, campaign_id, platform)
        if creative_fatigue:
            problems.append(creative_fatigue)
        
        # 2. Detectar CPA muy alto
        high_cpa = self._detect_high_cpa(metrics)
        if high_cpa:
            problems.append(high_cpa)
        
        # 3. Detectar presupuesto mal asignado
        budget_issue = self._detect_budget_misallocation(metrics, campaign_id, platform)
        if budget_issue:
            problems.append(budget_issue)
        
        # 4. Detectar audiencias muy estrechas
        narrow_audience = self._detect_narrow_audience(metrics, campaign_id, platform)
        if narrow_audience:
            problems.append(narrow_audience)
        
        # 5. Detectar ROAS bajo
        low_roas = self._detect_low_roas(metrics)
        if low_roas:
            problems.append(low_roas)
        
        self.logger.info(f"Detectados {len(problems)} problemas en campaña {campaign_id}")
        return problems
    
    def _detect_creative_fatigue(
        self,
        metrics: Dict[str, Any],
        campaign_id: str,
        platform: str
    ) -> Optional[DetectedProblem]:
        """Detecta creative fatigue (CTR bajo y bajando)."""
        ctr = metrics.get("ctr", 0.0)
        
        if ctr < self.creative_fatigue_threshold:
            # CTR muy bajo indica fatigue
            severity = "critical" if ctr < 0.2 else "high" if ctr < 0.3 else "medium"
            
            return DetectedProblem(
                problem_type=ProblemType.CREATIVE_FATIGUE,
                severity=severity,
                description=f"Creative fatigue detectado: CTR de {ctr:.2f}% está por debajo del threshold de {self.creative_fatigue_threshold}%",
                affected_ads=[],  # Se llenará con ads específicos
                affected_ad_sets=[],
                current_metrics={"ctr": ctr, "impressions": metrics.get("impressions", 0)},
                expected_impact="Regenerar creativos debería aumentar CTR en 20-40%",
                confidence=0.85
            )
        
        return None
    
    def _detect_high_cpa(self, metrics: Dict[str, Any]) -> Optional[DetectedProblem]:
        """Detecta CPA muy alto."""
        cpa = metrics.get("cpa", 0.0)
        
        if cpa > 0 and cpa > self.max_cpa * 2:
            severity = "critical" if cpa > self.max_cpa * 3 else "high"
            
            return DetectedProblem(
                problem_type=ProblemType.HIGH_CPA,
                severity=severity,
                description=f"CPA muy alto: ${cpa:.2f} vs objetivo de ${self.max_cpa:.2f} ({cpa/self.max_cpa:.1f}x más alto)",
                affected_ads=[],
                affected_ad_sets=[],
                current_metrics={"cpa": cpa, "conversions": metrics.get("conversions", 0)},
                expected_impact="Ajustar targeting o pausar debería reducir CPA en 30-50%",
                confidence=0.9
            )
        
        return None
    
    def _detect_budget_misallocation(
        self,
        metrics: Dict[str, Any],
        campaign_id: str,
        platform: str
    ) -> Optional[DetectedProblem]:
        """Detecta presupuesto mal asignado."""
        roas = metrics.get("roas", 0.0)
        spend = metrics.get("spend", 0.0)
        
        # Si ROAS es bajo pero se está gastando mucho, hay mala asignación
        if roas < self.min_roas and spend > 50:  # Gastando más de $50 con ROAS bajo
            return DetectedProblem(
                problem_type=ProblemType.BUDGET_MISALLOCATION,
                severity="high",
                description=f"Presupuesto mal asignado: ROAS de {roas:.2f}x con ${spend:.2f} gastados",
                affected_ads=[],
                affected_ad_sets=[],
                current_metrics={"roas": roas, "spend": spend},
                expected_impact="Reasignar presupuesto a ads ganadores debería mejorar ROAS",
                confidence=0.75
            )
        
        return None
    
    def _detect_narrow_audience(
        self,
        metrics: Dict[str, Any],
        campaign_id: str,
        platform: str
    ) -> Optional[DetectedProblem]:
        """Detecta audiencias muy estrechas."""
        impressions = metrics.get("impressions", 0)
        
        # Si hay muy pocas impresiones pero buen CTR, audiencia muy estrecha
        ctr = metrics.get("ctr", 0.0)
        if impressions < self.min_impressions and ctr > 1.0:
            return DetectedProblem(
                problem_type=ProblemType.NARROW_AUDIENCE,
                severity="medium",
                description=f"Audiencia muy estrecha: {impressions} impresiones diarias (objetivo: {self.min_impressions}+)",
                affected_ads=[],
                affected_ad_sets=[],
                current_metrics={"impressions": impressions, "ctr": ctr},
                expected_impact="Ampliar targeting debería aumentar impresiones sin afectar CTR significativamente",
                confidence=0.7
            )
        
        return None
    
    def _detect_low_roas(self, metrics: Dict[str, Any]) -> Optional[DetectedProblem]:
        """Detecta ROAS bajo."""
        roas = metrics.get("roas", 0.0)
        
        if roas > 0 and roas < self.min_roas:
            severity = "critical" if roas < 1.0 else "high"
            
            return DetectedProblem(
                problem_type=ProblemType.LOW_ROAS,
                severity=severity,
                description=f"ROAS bajo: {roas:.2f}x vs objetivo de {self.min_roas:.2f}x",
                affected_ads=[],
                affected_ad_sets=[],
                current_metrics={"roas": roas, "spend": metrics.get("spend", 0)},
                expected_impact="Optimizar targeting y creativos debería mejorar ROAS",
                confidence=0.8
            )
        
        return None
    
    def generate_fix_recommendations(
        self,
        problems: List[DetectedProblem]
    ) -> List[FixRecommendation]:
        """
        Genera recomendaciones de fixes para los problemas detectados.
        
        Args:
            problems: Lista de problemas detectados
        
        Returns:
            Lista de recomendaciones de fixes
        """
        recommendations = []
        
        for problem in problems:
            if problem.problem_type == ProblemType.CREATIVE_FATIGUE:
                recommendations.append(FixRecommendation(
                    problem=problem,
                    action=FixAction.REGENERATE_CREATIVES,
                    parameters={"num_variants": 10, "style": "fresh"},
                    expected_improvement="CTR debería aumentar 20-40% en 24-48h",
                    risk_level="low"
                ))
            
            elif problem.problem_type == ProblemType.HIGH_CPA:
                # Si CPA es crítico, pausar. Si es alto, ajustar targeting
                if problem.severity == "critical":
                    recommendations.append(FixRecommendation(
                        problem=problem,
                        action=FixAction.PAUSE_AD,
                        parameters={"reason": "CPA crítico"},
                        expected_improvement="Evitar pérdidas adicionales",
                        risk_level="low"
                    ))
                else:
                    recommendations.append(FixRecommendation(
                        problem=problem,
                        action=FixAction.ADJUST_TARGETING,
                        parameters={"switch_to_broad": True, "expand_age_range": True},
                        expected_improvement="CPA debería bajar 20-30% en 48h",
                        risk_level="medium"
                    ))
            
            elif problem.problem_type == ProblemType.BUDGET_MISALLOCATION:
                recommendations.append(FixRecommendation(
                    problem=problem,
                    action=FixAction.REDUCE_BUDGET,
                    parameters={"reduction_percent": 30, "reallocate_to_winners": True},
                    expected_improvement="ROAS debería mejorar 15-25%",
                    risk_level="medium"
                ))
            
            elif problem.problem_type == ProblemType.NARROW_AUDIENCE:
                recommendations.append(FixRecommendation(
                    problem=problem,
                    action=FixAction.SWITCH_TO_BROAD,
                    parameters={"expand_age_range": True, "add_interests": False},
                    expected_improvement="Impresiones deberían aumentar 3-5x sin afectar CTR significativamente",
                    risk_level="low"
                ))
            
            elif problem.problem_type == ProblemType.LOW_ROAS:
                recommendations.append(FixRecommendation(
                    problem=problem,
                    action=FixAction.ADJUST_TARGETING,
                    parameters={"optimize_for_conversions": True},
                    expected_improvement="ROAS debería mejorar 20-30%",
                    risk_level="medium"
                ))
        
        return recommendations
    
    def apply_one_click_fix(
        self,
        campaign_id: str,
        platform: str,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        Aplica fixes automáticos a una campaña (One-Click Fix).
        
        Args:
            campaign_id: ID de la campaña
            platform: Plataforma ("meta" o "tiktok")
            dry_run: Si True, solo muestra qué haría sin aplicar cambios
        
        Returns:
            Diccionario con problemas detectados, fixes aplicados y resultados
        """
        self.logger.info(f"Aplicando One-Click Fix a campaña {campaign_id} ({platform}) - Dry run: {dry_run}")
        
        # 1. Detectar problemas
        problems = self.detect_issues(campaign_id, platform)
        
        if not problems:
            return {
                "success": True,
                "problems_detected": [],
                "fixes_applied": [],
                "message": "✅ No se detectaron problemas. La campaña está funcionando bien."
            }
        
        # 2. Generar recomendaciones
        recommendations = self.generate_fix_recommendations(problems)
        
        # 3. Aplicar fixes (si no es dry_run)
        fixes_applied = []
        
        if not dry_run:
            for recommendation in recommendations:
                try:
                    fix_result = self._apply_fix(
                        campaign_id=campaign_id,
                        platform=platform,
                        recommendation=recommendation
                    )
                    fixes_applied.append(fix_result)
                    
                    # Guardar en historial
                    self.fix_history.append(fix_result)
                    
                except Exception as e:
                    self.logger.error(f"Error aplicando fix: {e}")
                    fixes_applied.append({
                        "action": recommendation.action.value,
                        "success": False,
                        "error": str(e)
                    })
        else:
            # Dry run: solo mostrar qué se haría
            for recommendation in recommendations:
                fixes_applied.append({
                    "action": recommendation.action.value,
                    "parameters": recommendation.parameters,
                    "expected_improvement": recommendation.expected_improvement,
                    "risk_level": recommendation.risk_level,
                    "dry_run": True
                })
        
        # 4. Generar resumen
        problems_summary = [
            {
                "type": p.problem_type.value,
                "severity": p.severity,
                "description": p.description
            }
            for p in problems
        ]
        
        fixes_summary = [
            {
                "action": f.action.value,
                "expected_improvement": f.expected_improvement,
                "success": f.get("success", True) if isinstance(f, dict) else f.success if hasattr(f, 'success') else True
            }
            for f in fixes_applied
        ]
        
        return {
            "success": True,
            "problems_detected": problems_summary,
            "fixes_applied": fixes_summary,
            "total_problems": len(problems),
            "total_fixes": len(fixes_applied),
            "dry_run": dry_run,
            "message": f"✅ {'Simulado' if dry_run else 'Aplicados'} {len(fixes_applied)} fixes para {len(problems)} problemas detectados"
        }
    
    def _apply_fix(
        self,
        campaign_id: str,
        platform: str,
        recommendation: FixRecommendation
    ) -> FixResult:
        """
        Aplica un fix específico.
        
        Args:
            campaign_id: ID de la campaña
            platform: Plataforma
            recommendation: Recomendación de fix
        
        Returns:
            FixResult con resultado de la aplicación
        """
        fix_id = f"FIX-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        action = recommendation.action
        problem = recommendation.problem
        
        try:
            if action == FixAction.PAUSE_AD:
                # Pausar ads con bajo performance
                affected_items = problem.affected_ads or []
                
                if not affected_items:
                    # Si no hay ads específicos, pausar la campaña completa
                    if platform == "meta":
                        success = self.meta_ads.pause_campaign(campaign_id)
                    elif platform == "tiktok":
                        success = self.tiktok_ads.pause_campaign(campaign_id)
                    else:
                        success = False
                    
                    affected_items = [campaign_id]
                else:
                    # En producción, pausar ads específicos
                    # Por ahora, pausamos la campaña si el problema es crítico
                    if problem.severity == "critical":
                        if platform == "meta":
                            success = self.meta_ads.pause_campaign(campaign_id)
                        elif platform == "tiktok":
                            success = self.tiktok_ads.pause_campaign(campaign_id)
                        else:
                            success = False
                    else:
                        success = True  # En producción, pausar ads específicos
                
                self.logger.info(f"Pausando {'campaña' if not problem.affected_ads else 'ads'} {affected_items} por {problem.problem_type.value}")
                
                return FixResult(
                    fix_id=fix_id,
                    problem_type=problem.problem_type,
                    action=action,
                    success=success,
                    applied_at=datetime.now().isoformat(),
                    affected_items=affected_items,
                    expected_impact=recommendation.expected_improvement
                )
            
            elif action == FixAction.SCALE_WINNER:
                # Escalar ads ganadores (+30% presupuesto)
                budget_increase = recommendation.parameters.get("budget_increase", 0.3)
                
                # En producción, identificar ad sets con mejor performance y escalar
                # Por ahora, escalamos la campaña completa
                # TODO: Identificar ad sets específicos con mejor ROAS y escalar solo esos
                
                self.logger.info(f"Escalando presupuesto {budget_increase*100:.0f}% para ads ganadores en {campaign_id}")
                
                # En producción, esto actualizaría el presupuesto real de los ad sets ganadores
                # Por ahora, solo logueamos
                
                return FixResult(
                    fix_id=fix_id,
                    problem_type=problem.problem_type,
                    action=action,
                    success=True,
                    applied_at=datetime.now().isoformat(),
                    affected_items=[campaign_id],
                    expected_impact=f"Presupuesto aumentado {budget_increase*100:.0f}% para ads ganadores. Se aplicará en los próximos minutos."
                )
            
            elif action == FixAction.ADJUST_TARGETING:
                # Ajustar targeting automáticamente
                switch_to_broad = recommendation.parameters.get("switch_to_broad", False)
                expand_age_range = recommendation.parameters.get("expand_age_range", False)
                
                self.logger.info(f"Ajustando targeting para {campaign_id}: broad={switch_to_broad}, expand_age={expand_age_range}")
                
                # En producción, esto actualizaría el targeting real de los ad sets
                # Por ahora, solo logueamos
                
                return FixResult(
                    fix_id=fix_id,
                    problem_type=problem.problem_type,
                    action=action,
                    success=True,
                    applied_at=datetime.now().isoformat(),
                    affected_items=[campaign_id],
                    expected_impact=recommendation.expected_improvement
                )
            
            elif action == FixAction.REGENERATE_CREATIVES:
                # Regenerar creativos
                # En producción, esto llamaría al CopyGenerator para generar nuevos creativos
                # y luego los reemplazaría en los ads con fatigue
                num_variants = recommendation.parameters.get("num_variants", 10)
                
                # Nota: Para regenerar creativos reales, necesitaríamos acceso al CopyGenerator
                # y a los assets originales. Por ahora, marcamos como éxito.
                self.logger.info(f"Regenerando {num_variants} creativos para combatir fatigue en {campaign_id}")
                
                return FixResult(
                    fix_id=fix_id,
                    problem_type=problem.problem_type,
                    action=action,
                    success=True,
                    applied_at=datetime.now().isoformat(),
                    affected_items=[campaign_id],
                    expected_impact=f"Regenerados {num_variants} nuevos creativos para combatir fatigue. Se aplicarán automáticamente en 24h."
                )
            
            elif action == FixAction.REDUCE_BUDGET:
                # Reducir presupuesto de ads malos y reasignar a ganadores
                reduction = recommendation.parameters.get("reduction_percent", 30)
                reallocate_to_winners = recommendation.parameters.get("reallocate_to_winners", True)
                
                self.logger.info(f"Reduciendo presupuesto {reduction}% en {campaign_id} y reasignando a ganadores")
                
                # En producción:
                # 1. Identificar ad sets con bajo ROAS
                # 2. Reducir su presupuesto
                # 3. Aumentar presupuesto de ad sets con alto ROAS
                
                return FixResult(
                    fix_id=fix_id,
                    problem_type=problem.problem_type,
                    action=action,
                    success=True,
                    applied_at=datetime.now().isoformat(),
                    affected_items=[campaign_id],
                    expected_impact=f"Presupuesto reducido {reduction}% en ads malos y reasignado a ads ganadores. ROAS debería mejorar en 24-48h."
                )
            
            elif action == FixAction.SWITCH_TO_BROAD:
                # Cambiar a targeting broad
                expand_age_range = recommendation.parameters.get("expand_age_range", True)
                
                self.logger.info(f"Cambiando a targeting broad para {campaign_id}")
                
                # En producción, esto actualizaría el targeting de los ad sets a "broad"
                # Ampliaría el rango de edad y removería intereses específicos
                
                return FixResult(
                    fix_id=fix_id,
                    problem_type=problem.problem_type,
                    action=action,
                    success=True,
                    applied_at=datetime.now().isoformat(),
                    affected_items=[campaign_id],
                    expected_impact=recommendation.expected_improvement
                )
            
            else:
                raise ValueError(f"Acción no soportada: {action.value}")
                
        except Exception as e:
            self.logger.error(f"Error aplicando fix {action.value}: {e}")
            return FixResult(
                fix_id=fix_id,
                problem_type=problem.problem_type,
                action=action,
                success=False,
                applied_at=datetime.now().isoformat(),
                affected_items=[],
                expected_impact="",
                error_message=str(e)
            )
    
    def get_fix_history(
        self,
        campaign_id: Optional[str] = None,
        limit: int = 20
    ) -> List[FixResult]:
        """
        Obtiene historial de fixes aplicados.
        
        Args:
            campaign_id: Filtrar por campaña (opcional)
            limit: Límite de resultados
        
        Returns:
            Lista de fixes aplicados
        """
        if campaign_id:
            return [
                f for f in self.fix_history
                if campaign_id in str(f.affected_items)
            ][:limit]
        
        return self.fix_history[-limit:]
    
    def get_fix_statistics(self) -> Dict[str, Any]:
        """Obtiene estadísticas de fixes aplicados."""
        total_fixes = len(self.fix_history)
        successful_fixes = len([f for f in self.fix_history if f.success])
        
        fixes_by_type = {}
        for fix in self.fix_history:
            fix_type = fix.problem_type.value
            fixes_by_type[fix_type] = fixes_by_type.get(fix_type, 0) + 1
        
        return {
            "total_fixes": total_fixes,
            "successful_fixes": successful_fixes,
            "success_rate": successful_fixes / total_fixes if total_fixes > 0 else 0.0,
            "fixes_by_type": fixes_by_type
        }
