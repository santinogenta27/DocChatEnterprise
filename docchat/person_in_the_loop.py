"""
Person in the Loop - Control humano
Requisito ético y legal para decisiones críticas
Previene decisiones peligrosas
Mantiene control humano
"""

from __future__ import annotations

import json
import time
import uuid
from typing import List, Dict, Optional, Any, Callable
from dataclasses import dataclass, field, asdict
from pathlib import Path
from enum import Enum

from .config import AppConfig


class ApprovalStatus(str, Enum):
    """Estado de aprobación."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    MODIFIED = "modified"
    EXPIRED = "expired"


class DecisionCriticality(str, Enum):
    """Nivel de criticidad de una decisión."""
    LOW = "low"  # No requiere aprobación
    MEDIUM = "medium"  # Aprobación recomendada
    HIGH = "high"  # Aprobación requerida
    CRITICAL = "critical"  # Aprobación obligatoria


@dataclass
class HumanApproval:
    """Solicitud de aprobación humana."""
    approval_id: str
    decision_type: str  # Tipo de decisión
    decision_content: str  # Contenido de la decisión
    context: str  # Contexto de la decisión
    criticality: DecisionCriticality
    status: ApprovalStatus = ApprovalStatus.PENDING
    created_at: float = field(default_factory=time.time)
    expires_at: Optional[float] = None  # Tiempo de expiración
    approved_by: Optional[str] = None  # Usuario que aprobó
    approved_at: Optional[float] = None
    rejection_reason: Optional[str] = None
    modifications: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ApprovalRule:
    """Regla para determinar cuándo se requiere aprobación."""
    rule_id: str
    decision_type: str  # Tipo de decisión que activa la regla
    conditions: Dict[str, Any]  # Condiciones que activan la regla
    required_criticality: DecisionCriticality  # Nivel de criticidad requerido
    auto_approve_after: Optional[float] = None  # Auto-aprobar después de X segundos
    enabled: bool = True


class PersonInTheLoop:
    """
    Sistema de control humano (Person in the Loop).
    
    Características:
    - Requisito ético y legal
    - Previene decisiones peligrosas
    - Mantiene control humano
    - Sin esto, el producto es riesgoso
    """
    
    def __init__(
        self,
        config: AppConfig,
        auto_approve_low: bool = True,  # Auto-aprobar decisiones de baja criticidad
        default_expiration: float = 3600  # 1 hora por defecto
    ):
        self.config = config
        self.auto_approve_low = auto_approve_low
        self.default_expiration = default_expiration
        
        # Solicitudes de aprobación
        self.pending_approvals: Dict[str, HumanApproval] = {}
        self.completed_approvals: List[HumanApproval] = []
        
        # Reglas de aprobación
        self.approval_rules: List[ApprovalRule] = []
        
        # Callback para notificar aprobaciones
        self.approval_callback: Optional[Callable] = None
        
        # Directorio para persistencia
        self.storage_dir = Path(config.memory_dir) / "person_in_the_loop"
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        # Cargar historial
        self._load_history()
        
        # Cargar reglas por defecto
        self._load_default_rules()
    
    def _load_history(self):
        """Carga historial de aprobaciones."""
        history_file = self.storage_dir / "approvals.json"
        if history_file.exists():
            try:
                with open(history_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for approval_data in data.get("approvals", [])[-500:]:  # Últimas 500
                        approval = HumanApproval(**approval_data)
                        if approval.status == ApprovalStatus.PENDING:
                            # Verificar si expiró
                            if approval.expires_at and time.time() > approval.expires_at:
                                approval.status = ApprovalStatus.EXPIRED
                                self.completed_approvals.append(approval)
                            else:
                                self.pending_approvals[approval.approval_id] = approval
                        else:
                            self.completed_approvals.append(approval)
                    print(f"✅ [Person in the Loop] {len(self.pending_approvals)} aprobaciones pendientes")
            except Exception as e:
                print(f"⚠️ [Person in the Loop] Error cargando historial: {e}")
    
    def _save_history(self):
        """Guarda historial de aprobaciones."""
        history_file = self.storage_dir / "approvals.json"
        try:
            all_approvals = list(self.pending_approvals.values()) + self.completed_approvals
            with open(history_file, "w", encoding="utf-8") as f:
                json.dump({
                    "approvals": [asdict(approval) for approval in all_approvals[-500:]]
                }, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"⚠️ [Person in the Loop] Error guardando historial: {e}")
    
    def _load_default_rules(self):
        """Carga reglas de aprobación por defecto."""
        # Reglas por defecto para decisiones críticas
        default_rules = [
            ApprovalRule(
                rule_id=str(uuid.uuid4()),
                decision_type="financial_transaction",
                conditions={"amount": {"gt": 10000}},
                required_criticality=DecisionCriticality.CRITICAL
            ),
            ApprovalRule(
                rule_id=str(uuid.uuid4()),
                decision_type="data_deletion",
                conditions={},
                required_criticality=DecisionCriticality.HIGH
            ),
            ApprovalRule(
                rule_id=str(uuid.uuid4()),
                decision_type="legal_document",
                conditions={},
                required_criticality=DecisionCriticality.HIGH
            ),
            ApprovalRule(
                rule_id=str(uuid.uuid4()),
                decision_type="medical_diagnosis",
                conditions={},
                required_criticality=DecisionCriticality.CRITICAL
            )
        ]
        
        self.approval_rules.extend(default_rules)
    
    def requires_approval(
        self,
        decision_type: str,
        decision_content: str,
        context: str = "",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, DecisionCriticality]:
        """
        Determina si una decisión requiere aprobación humana.
        
        Returns:
            (requires_approval, criticality): Si requiere aprobación y nivel de criticidad
        """
        # Buscar regla aplicable
        applicable_rule = None
        for rule in self.approval_rules:
            if not rule.enabled:
                continue
            if rule.decision_type == decision_type:
                # Verificar condiciones
                if self._check_conditions(rule.conditions, metadata or {}):
                    applicable_rule = rule
                    break
        
        if applicable_rule:
            criticality = applicable_rule.required_criticality
        else:
            # Por defecto, decisiones desconocidas son de criticidad media
            criticality = DecisionCriticality.MEDIUM
        
        # Auto-aprobar si es baja criticidad y está habilitado
        if criticality == DecisionCriticality.LOW and self.auto_approve_low:
            return False, criticality
        
        # Requerir aprobación para medium, high y critical
        return criticality in [
            DecisionCriticality.MEDIUM,
            DecisionCriticality.HIGH,
            DecisionCriticality.CRITICAL
        ], criticality
    
    def _check_conditions(
        self,
        conditions: Dict[str, Any],
        metadata: Dict[str, Any]
    ) -> bool:
        """Verifica si las condiciones de una regla se cumplen."""
        if not conditions:
            return True
        
        for key, condition in conditions.items():
            if key not in metadata:
                return False
            
            value = metadata[key]
            
            # Verificar operadores (gt, lt, eq, in, etc.)
            if isinstance(condition, dict):
                if "gt" in condition and not (value > condition["gt"]):
                    return False
                if "lt" in condition and not (value < condition["lt"]):
                    return False
                if "eq" in condition and not (value == condition["eq"]):
                    return False
                if "in" in condition and not (value in condition["in"]):
                    return False
            elif value != condition:
                return False
        
        return True
    
    def request_approval(
        self,
        decision_type: str,
        decision_content: str,
        context: str = "",
        criticality: Optional[DecisionCriticality] = None,
        expiration_seconds: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Solicita aprobación humana para una decisión.
        
        Returns:
            approval_id: ID de la solicitud de aprobación
        """
        # Determinar criticidad si no se proporciona
        if criticality is None:
            requires, crit = self.requires_approval(decision_type, decision_content, context, metadata)
            criticality = crit
        
        approval_id = str(uuid.uuid4())
        
        expires_at = None
        if expiration_seconds:
            expires_at = time.time() + expiration_seconds
        elif self.default_expiration:
            expires_at = time.time() + self.default_expiration
        
        approval = HumanApproval(
            approval_id=approval_id,
            decision_type=decision_type,
            decision_content=decision_content,
            context=context,
            criticality=criticality,
            expires_at=expires_at,
            metadata=metadata or {}
        )
        
        self.pending_approvals[approval_id] = approval
        
        # Notificar si hay callback
        if self.approval_callback:
            try:
                self.approval_callback(approval)
            except Exception as e:
                print(f"⚠️ [Person in the Loop] Error en callback: {e}")
        
        print(f"⏳ [Person in the Loop] Aprobación solicitada: {decision_type} ({criticality.value})")
        
        # Guardar periódicamente
        if len(self.pending_approvals) % 10 == 0:
            self._save_history()
        
        return approval_id
    
    def approve(
        self,
        approval_id: str,
        approved_by: str,
        modifications: Optional[str] = None
    ) -> bool:
        """
        Aprueba una decisión.
        
        Returns:
            True si se aprobó exitosamente
        """
        if approval_id not in self.pending_approvals:
            return False
        
        approval = self.pending_approvals[approval_id]
        
        # Verificar expiración
        if approval.expires_at and time.time() > approval.expires_at:
            approval.status = ApprovalStatus.EXPIRED
            self.completed_approvals.append(approval)
            del self.pending_approvals[approval_id]
            return False
        
        approval.status = ApprovalStatus.APPROVED if not modifications else ApprovalStatus.MODIFIED
        approval.approved_by = approved_by
        approval.approved_at = time.time()
        approval.modifications = modifications
        
        self.completed_approvals.append(approval)
        del self.pending_approvals[approval_id]
        
        self._save_history()
        
        print(f"✅ [Person in the Loop] Aprobación {approval_id} aprobada por {approved_by}")
        
        return True
    
    def reject(
        self,
        approval_id: str,
        rejected_by: str,
        reason: str
    ) -> bool:
        """
        Rechaza una decisión.
        
        Returns:
            True si se rechazó exitosamente
        """
        if approval_id not in self.pending_approvals:
            return False
        
        approval = self.pending_approvals[approval_id]
        approval.status = ApprovalStatus.REJECTED
        approval.approved_by = rejected_by
        approval.approved_at = time.time()
        approval.rejection_reason = reason
        
        self.completed_approvals.append(approval)
        del self.pending_approvals[approval_id]
        
        self._save_history()
        
        print(f"❌ [Person in the Loop] Aprobación {approval_id} rechazada por {rejected_by}")
        
        return True
    
    def get_approval(self, approval_id: str) -> Optional[HumanApproval]:
        """Obtiene una aprobación por ID."""
        if approval_id in self.pending_approvals:
            return self.pending_approvals[approval_id]
        
        return next((a for a in self.completed_approvals if a.approval_id == approval_id), None)
    
    def list_pending_approvals(
        self,
        decision_type: Optional[str] = None
    ) -> List[HumanApproval]:
        """Lista aprobaciones pendientes."""
        approvals = list(self.pending_approvals.values())
        
        if decision_type:
            approvals = [a for a in approvals if a.decision_type == decision_type]
        
        return sorted(approvals, key=lambda a: a.created_at, reverse=True)
    
    def format_approval_request(self, approval_id: str) -> str:
        """
        Formatea una solicitud de aprobación para mostrar al usuario.
        
        Returns:
            Solicitud formateada
        """
        approval = self.get_approval(approval_id)
        if not approval:
            return f"Aprobación {approval_id} no encontrada"
        
        output = f"⏳ SOLICITUD DE APROBACIÓN\n"
        output += f"{'='*60}\n\n"
        output += f"ID: {approval_id}\n"
        output += f"Tipo: {approval.decision_type}\n"
        output += f"Criticidad: {approval.criticality.value.upper()}\n"
        output += f"Estado: {approval.status.value}\n"
        output += f"Fecha: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(approval.created_at))}\n"
        
        if approval.expires_at:
            remaining = approval.expires_at - time.time()
            if remaining > 0:
                output += f"Expira en: {remaining/60:.1f} minutos\n"
            else:
                output += f"⚠️ EXPIRADA\n"
        
        output += f"\n📋 DECISIÓN:\n"
        output += f"{approval.decision_content}\n"
        
        if approval.context:
            output += f"\n📚 CONTEXTO:\n"
            output += f"{approval.context}\n"
        
        if approval.metadata:
            output += f"\n🔧 METADATOS:\n"
            output += f"{json.dumps(approval.metadata, indent=2)}\n"
        
        return output
    
    def get_statistics(self) -> Dict[str, Any]:
        """Obtiene estadísticas de aprobaciones."""
        total = len(self.pending_approvals) + len(self.completed_approvals)
        approved = sum(1 for a in self.completed_approvals if a.status == ApprovalStatus.APPROVED)
        rejected = sum(1 for a in self.completed_approvals if a.status == ApprovalStatus.REJECTED)
        
        # Por criticidad
        by_criticality = {}
        for approval in self.completed_approvals + list(self.pending_approvals.values()):
            crit = approval.criticality.value
            by_criticality[crit] = by_criticality.get(crit, 0) + 1
        
        return {
            "pending_approvals": len(self.pending_approvals),
            "total_approvals": total,
            "approved": approved,
            "rejected": rejected,
            "approval_rate": (approved / total * 100) if total > 0 else 0,
            "by_criticality": by_criticality,
            "active_rules": len([r for r in self.approval_rules if r.enabled])
        }

