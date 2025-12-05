"""Enterprise Policy Engine

Motor de políticas corporativas para Enterprise Autonomous Workflows.

Objetivo:
- Asegurar que los agentes NO ejecuten acciones fuera de las reglas del cliente.
- Soportar modos: simulación vs ejecución real.
- Permitir políticas por tenant y por tipo de workflow.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class PolicyDecision:
    allowed: bool
    reason: str
    require_approval: bool = False
    simulation_only: bool = False


class EnterprisePolicyEngine:
    """Evalúa acciones propuestas por los agentes contra políticas corporativas."""

    def __init__(self, default_policies: Optional[Dict[str, Any]] = None):
        # default_policies es un fallback muy simple (límites globales)
        self.default_policies = default_policies or {
            "payments": {"max_auto_approval": 2000},
            "risk": {"min_severity_for_ticket": "high"},
        }

    def _get_tenant_policies(self, tenant_id: str, integration_prefs: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        prefs = integration_prefs or {}
        by_tenant = prefs.get("policies_by_tenant", {})
        return by_tenant.get(tenant_id, prefs.get("policies", {})) or {}

    def evaluate_actions(
        self,
        tenant_id: str,
        workflow_type: str,
        proposed_actions: List[Dict[str, Any]],
        simulation_mode: bool,
        integration_prefs: Optional[Dict[str, Any]] = None,
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Devuelve (acciones_permitidas, decisiones_por_accion)."""
        tenant_policies = self._get_tenant_policies(tenant_id, integration_prefs)
        policies = {**self.default_policies, **tenant_policies}

        allowed_actions: List[Dict[str, Any]] = []
        decisions: List[Dict[str, Any]] = []

        for action in proposed_actions:
            decision = self._evaluate_single_action(action, workflow_type, simulation_mode, policies)
            action_with_decision = {**action, "_policy": decision.__dict__}

            # Si estamos en simulación, nunca se ejecutan de verdad
            if not simulation_mode and decision.allowed and not decision.require_approval:
                allowed_actions.append(action_with_decision)

            decisions.append(
                {
                    "action": action,
                    "decision": decision.__dict__,
                }
            )

        return allowed_actions, decisions

    def _evaluate_single_action(
        self,
        action: Dict[str, Any],
        workflow_type: str,
        simulation_mode: bool,
        policies: Dict[str, Any],
    ) -> PolicyDecision:
        """Reglas simples pero útiles, basadas en tipo de acción."""
        action_type = action.get("type") or action.get("action_type") or ""

        # Siempre seguro en simulación
        if simulation_mode:
            return PolicyDecision(
                allowed=False,
                reason="Simulation mode: acción solo registrada, no ejecutada.",
                simulation_only=True,
            )

        # Pagos / finanzas
        if action_type in {"approve_payment", "execute_payment"}:
            amount = float(action.get("amount", 0))
            max_auto = float(policies.get("payments", {}).get("max_auto_approval", 0))
            if amount <= max_auto:
                return PolicyDecision(
                    allowed=True,
                    reason=f"Pago <= límite auto-aprobación ({max_auto}).",
                    require_approval=False,
                )
            return PolicyDecision(
                allowed=False,
                reason=f"Pago excede límite auto-aprobación ({max_auto}), requiere aprobación humana.",
                require_approval=True,
            )

        # Tickets por riesgo
        if action_type in {"create_ticket", "create_incident"} and workflow_type in {"risk_scan", "alertas_riesgo"}:
            severity = str(action.get("severity", "medium")).lower()
            min_sev = str(policies.get("risk", {}).get("min_severity_for_ticket", "high")).lower()
            order = {"low": 0, "medium": 1, "high": 2, "critical": 3}
            if order.get(severity, 1) >= order.get(min_sev, 2):
                return PolicyDecision(
                    allowed=True,
                    reason=f"Severidad {severity} >= umbral {min_sev}, ticket permitido.",
                )
            return PolicyDecision(
                allowed=False,
                reason=f"Severidad {severity} < umbral {min_sev}, no crear ticket automático.",
            )

        # Por defecto: permitir pero marcado como "requiere política explícita" (para logging)
        return PolicyDecision(
            allowed=False,
            reason="Acción no cubierta por políticas explícitas, requiere revisión o política específica.",
            require_approval=True,
        )


__all__ = ["EnterprisePolicyEngine", "PolicyDecision"]


