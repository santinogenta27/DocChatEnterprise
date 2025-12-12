"""
Multi-Tenant Isolation Manager
Separa datos y recursos por tenant/cliente
"""

from __future__ import annotations

import hashlib
from typing import Dict, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
import json
from pathlib import Path


@dataclass
class Tenant:
    """Información de un tenant"""
    tenant_id: str
    name: str
    email: str
    plan: str = "free"  # free, pro, enterprise
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)
    quotas: Dict[str, int] = field(default_factory=dict)
    usage: Dict[str, int] = field(default_factory=dict)


@dataclass
class TenantQuota:
    """Cuotas por plan"""
    max_campaigns: int
    max_assets: int
    max_variations_per_asset: int
    max_api_calls_per_day: int
    max_budget_per_campaign: float


# Cuotas por plan
PLAN_QUOTAS = {
    "free": TenantQuota(
        max_campaigns=5,
        max_assets=20,
        max_variations_per_asset=3,
        max_api_calls_per_day=100,
        max_budget_per_campaign=100.0
    ),
    "pro": TenantQuota(
        max_campaigns=50,
        max_assets=500,
        max_variations_per_asset=10,
        max_api_calls_per_day=1000,
        max_budget_per_campaign=10000.0
    ),
    "enterprise": TenantQuota(
        max_campaigns=1000,
        max_assets=10000,
        max_variations_per_asset=50,
        max_api_calls_per_day=100000,
        max_budget_per_campaign=1000000.0
    )
}


class TenantManager:
    """Gestor de tenants con isolation"""
    
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir / "tenants"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.tenants_file = self.data_dir / "tenants.json"
        self.tenants: Dict[str, Tenant] = {}
        self._load_tenants()
    
    def _load_tenants(self):
        """Carga tenants desde disco"""
        if self.tenants_file.exists():
            try:
                with open(self.tenants_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for tid, tenant_data in data.items():
                        self.tenants[tid] = Tenant(**tenant_data)
            except Exception as e:
                print(f"Error cargando tenants: {e}")
    
    def _save_tenants(self):
        """Guarda tenants a disco"""
        try:
            data = {
                tid: {
                    "tenant_id": t.tenant_id,
                    "name": t.name,
                    "email": t.email,
                    "plan": t.plan,
                    "created_at": t.created_at,
                    "metadata": t.metadata,
                    "quotas": t.quotas,
                    "usage": t.usage
                }
                for tid, t in self.tenants.items()
            }
            with open(self.tenants_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error guardando tenants: {e}")
    
    def create_tenant(
        self,
        name: str,
        email: str,
        plan: str = "free"
    ) -> Tenant:
        """Crea un nuevo tenant"""
        tenant_id = hashlib.md5(f"{email}{datetime.now().isoformat()}".encode()).hexdigest()[:16]
        
        tenant = Tenant(
            tenant_id=tenant_id,
            name=name,
            email=email,
            plan=plan,
            quotas={},
            usage={
                "campaigns": 0,
                "assets": 0,
                "api_calls_today": 0,
                "last_reset": datetime.now().isoformat()
            }
        )
        
        self.tenants[tenant_id] = tenant
        self._save_tenants()
        
        return tenant
    
    def get_tenant(self, tenant_id: str) -> Optional[Tenant]:
        """Obtiene un tenant"""
        return self.tenants.get(tenant_id)
    
    def get_quota(self, tenant_id: str) -> Optional[TenantQuota]:
        """Obtiene cuotas de un tenant"""
        tenant = self.get_tenant(tenant_id)
        if not tenant:
            return None
        return PLAN_QUOTAS.get(tenant.plan, PLAN_QUOTAS["free"])
    
    def check_quota(
        self,
        tenant_id: str,
        resource: str,
        amount: int = 1
    ) -> bool:
        """Verifica si un tenant puede usar un recurso"""
        tenant = self.get_tenant(tenant_id)
        if not tenant:
            return False
        
        quota = self.get_quota(tenant_id)
        if not quota:
            return False
        
        # Resetear contadores diarios si es necesario
        self._reset_daily_usage_if_needed(tenant)
        
        # Verificar cuota según recurso
        if resource == "campaigns":
            return tenant.usage.get("campaigns", 0) + amount <= quota.max_campaigns
        elif resource == "assets":
            return tenant.usage.get("assets", 0) + amount <= quota.max_assets
        elif resource == "api_calls":
            return tenant.usage.get("api_calls_today", 0) + amount <= quota.max_api_calls_per_day
        elif resource == "budget":
            return amount <= quota.max_budget_per_campaign
        
        return True
    
    def increment_usage(
        self,
        tenant_id: str,
        resource: str,
        amount: int = 1
    ):
        """Incrementa uso de un recurso"""
        tenant = self.get_tenant(tenant_id)
        if not tenant:
            return
        
        self._reset_daily_usage_if_needed(tenant)
        
        if resource in tenant.usage:
            tenant.usage[resource] = tenant.usage.get(resource, 0) + amount
        else:
            tenant.usage[resource] = amount
        
        self._save_tenants()
    
    def _reset_daily_usage_if_needed(self, tenant: Tenant):
        """Resetea uso diario si es necesario"""
        last_reset = tenant.usage.get("last_reset")
        if last_reset:
            last_reset_dt = datetime.fromisoformat(last_reset)
            now = datetime.now()
            if (now - last_reset_dt).days >= 1:
                tenant.usage["api_calls_today"] = 0
                tenant.usage["last_reset"] = now.isoformat()
        else:
            tenant.usage["last_reset"] = datetime.now().isoformat()
    
    def upgrade_plan(self, tenant_id: str, new_plan: str):
        """Upgrade plan de un tenant"""
        tenant = self.get_tenant(tenant_id)
        if not tenant:
            return
        
        if new_plan not in PLAN_QUOTAS:
            raise ValueError(f"Plan inválido: {new_plan}")
        
        tenant.plan = new_plan
        self._save_tenants()

