"""
Base class para todos los agentes del modo BANKS.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from pathlib import Path
import json
from datetime import datetime

from ....config import AppConfig
from ..schemas import AuditLog


class BaseBanksAgent(ABC):
    """Clase base para todos los agentes del modo BANKS."""
    
    def __init__(self, config: AppConfig, agent_name: str):
        self.config = config
        self.agent_name = agent_name
        self.audit_dir = Path(config.audit_log_dir) / "banks" / agent_name
        self.audit_dir.mkdir(parents=True, exist_ok=True)
    
    def log_audit(
        self,
        action: str,
        input_data: Dict[str, Any],
        output_data: Dict[str, Any],
        user_id: Optional[str] = None,
        steering_applied: Optional[str] = None,
        evidence: Optional[list] = None
    ) -> AuditLog:
        """Registra una acción en el audit trail."""
        log = AuditLog(
            log_id=f"{self.agent_name}_{datetime.now().timestamp()}",
            agent=self.agent_name,
            action=action,
            input_data=input_data,
            output_data=output_data,
            user_id=user_id,
            steering_applied=steering_applied,
            evidence=evidence or []
        )
        
        # Guardar en archivo
        log_file = self.audit_dir / f"{log.log_id}.json"
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(log.model_dump(mode='json'), f, indent=2, default=str, ensure_ascii=False)
        
        return log
    
    @abstractmethod
    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Procesa el estado y retorna el estado actualizado."""
        pass
    
    def get_evidence_location(self, document_path: str, page: int, line: Optional[int] = None) -> Dict[str, Any]:
        """Genera información de ubicación de evidencia."""
        return {
            "document": str(document_path),
            "page": page,
            "line": line,
            "timestamp": datetime.now().isoformat()
        }

