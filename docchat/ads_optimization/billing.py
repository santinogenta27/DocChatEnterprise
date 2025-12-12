"""
Sistema de Facturación Básico
Tracking de uso y facturación por tenant
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Dict, Optional, List
from pathlib import Path
from dataclasses import dataclass, field, asdict


@dataclass
class UsageRecord:
    """Registro de uso"""
    tenant_id: str
    resource: str  # campaigns, assets, api_calls, predictions
    amount: float
    unit: str  # count, calls, predictions
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict = field(default_factory=dict)


@dataclass
class BillingRecord:
    """Registro de facturación"""
    billing_id: str
    tenant_id: str
    period_start: str
    period_end: str
    total_amount: float
    currency: str = "USD"
    items: List[Dict] = field(default_factory=list)
    status: str = "pending"  # pending, paid, overdue
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


# Precios por plan y recurso
PRICING = {
    "free": {
        "campaigns": 0.0,
        "assets": 0.0,
        "api_calls": 0.0,
        "predictions": 0.0,
        "base_monthly": 0.0
    },
    "pro": {
        "campaigns": 0.10,  # $0.10 por campaña
        "assets": 0.01,  # $0.01 por asset
        "api_calls": 0.001,  # $0.001 por API call
        "predictions": 0.005,  # $0.005 por predicción
        "base_monthly": 99.0  # $99/mes base
    },
    "enterprise": {
        "campaigns": 0.05,  # $0.05 por campaña (descuento)
        "assets": 0.005,  # $0.005 por asset
        "api_calls": 0.0005,  # $0.0005 por API call
        "predictions": 0.002,  # $0.002 por predicción
        "base_monthly": 999.0  # $999/mes base
    }
}


class BillingManager:
    """Gestor de facturación"""
    
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir / "billing"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.usage_file = self.data_dir / "usage.json"
        self.billing_file = self.data_dir / "billing.json"
        
        self.usage_records: List[UsageRecord] = []
        self.billing_records: Dict[str, BillingRecord] = {}
        
        self._load_data()
    
    def _load_data(self):
        """Carga datos de facturación"""
        # Cargar usage
        if self.usage_file.exists():
            try:
                with open(self.usage_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.usage_records = [UsageRecord(**r) for r in data]
            except Exception as e:
                print(f"Error cargando usage: {e}")
        
        # Cargar billing
        if self.billing_file.exists():
            try:
                with open(self.billing_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.billing_records = {
                        bid: BillingRecord(**br) for bid, br in data.items()
                    }
            except Exception as e:
                print(f"Error cargando billing: {e}")
    
    def _save_data(self):
        """Guarda datos de facturación"""
        # Guardar usage
        try:
            with open(self.usage_file, 'w', encoding='utf-8') as f:
                json.dump([asdict(r) for r in self.usage_records], f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error guardando usage: {e}")
        
        # Guardar billing
        try:
            with open(self.billing_file, 'w', encoding='utf-8') as f:
                data = {
                    bid: asdict(br) for bid, br in self.billing_records.items()
                }
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error guardando billing: {e}")
    
    def record_usage(
        self,
        tenant_id: str,
        resource: str,
        amount: float = 1.0,
        unit: str = "count",
        metadata: Optional[Dict] = None
    ):
        """Registra uso de un recurso"""
        record = UsageRecord(
            tenant_id=tenant_id,
            resource=resource,
            amount=amount,
            unit=unit,
            metadata=metadata or {}
        )
        self.usage_records.append(record)
        self._save_data()
    
    def calculate_cost(
        self,
        tenant_id: str,
        plan: str,
        period_start: datetime,
        period_end: datetime
    ) -> float:
        """Calcula costo para un periodo"""
        # Filtrar usage en el periodo
        period_usage = [
            r for r in self.usage_records
            if r.tenant_id == tenant_id and
            period_start <= datetime.fromisoformat(r.timestamp) <= period_end
        ]
        
        # Obtener precios
        pricing = PRICING.get(plan, PRICING["free"])
        
        # Calcular costo base
        total = pricing["base_monthly"]
        
        # Calcular costo por recurso
        resource_costs = {}
        for record in period_usage:
            resource = record.resource
            if resource in pricing:
                cost = record.amount * pricing[resource]
                total += cost
                if resource not in resource_costs:
                    resource_costs[resource] = 0.0
                resource_costs[resource] += cost
        
        return total
    
    def generate_bill(
        self,
        tenant_id: str,
        plan: str,
        period_start: Optional[datetime] = None,
        period_end: Optional[datetime] = None
    ) -> BillingRecord:
        """Genera factura para un periodo"""
        if period_start is None:
            period_start = datetime.now().replace(day=1)  # Inicio del mes
        if period_end is None:
            period_end = datetime.now()  # Ahora
        
        # Calcular costo
        total = self.calculate_cost(tenant_id, plan, period_start, period_end)
        
        # Crear items de factura
        items = []
        pricing = PRICING.get(plan, PRICING["free"])
        
        if pricing["base_monthly"] > 0:
            items.append({
                "description": f"Plan {plan} - Base mensual",
                "quantity": 1,
                "unit_price": pricing["base_monthly"],
                "total": pricing["base_monthly"]
            })
        
        # Agregar items por recurso usado
        period_usage = [
            r for r in self.usage_records
            if r.tenant_id == tenant_id and
            period_start <= datetime.fromisoformat(r.timestamp) <= period_end
        ]
        
        resource_totals = {}
        for record in period_usage:
            resource = record.resource
            if resource in pricing and pricing[resource] > 0:
                cost = record.amount * pricing[resource]
                if resource not in resource_totals:
                    resource_totals[resource] = {"amount": 0.0, "cost": 0.0}
                resource_totals[resource]["amount"] += record.amount
                resource_totals[resource]["cost"] += cost
        
        for resource, totals in resource_totals.items():
            items.append({
                "description": f"{resource} usage",
                "quantity": totals["amount"],
                "unit_price": pricing[resource],
                "total": totals["cost"]
            })
        
        # Crear billing record
        billing_id = f"bill_{tenant_id}_{period_start.strftime('%Y%m')}"
        bill = BillingRecord(
            billing_id=billing_id,
            tenant_id=tenant_id,
            period_start=period_start.isoformat(),
            period_end=period_end.isoformat(),
            total_amount=total,
            items=items,
            status="pending"
        )
        
        self.billing_records[billing_id] = bill
        self._save_data()
        
        return bill
    
    def get_usage_summary(
        self,
        tenant_id: str,
        days: int = 30
    ) -> Dict[str, float]:
        """Obtiene resumen de uso"""
        cutoff = datetime.now() - timedelta(days=days)
        
        period_usage = [
            r for r in self.usage_records
            if r.tenant_id == tenant_id and
            datetime.fromisoformat(r.timestamp) >= cutoff
        ]
        
        summary = {}
        for record in period_usage:
            resource = record.resource
            if resource not in summary:
                summary[resource] = 0.0
            summary[resource] += record.amount
        
        return summary

