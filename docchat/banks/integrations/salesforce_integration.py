"""
Integración con Salesforce Financial Services Cloud.
"""

from __future__ import annotations

import logging
from typing import Dict, Any, Optional
from datetime import datetime

try:
    from simple_salesforce import Salesforce
    SALESFORCE_AVAILABLE = True
except ImportError:
    SALESFORCE_AVAILABLE = False
    logging.warning("simple-salesforce no disponible")

logger = logging.getLogger(__name__)


class SalesforceIntegration:
    """Integración con Salesforce Financial Services Cloud."""
    
    def __init__(self, username: str, password: str, security_token: str, domain: str = "login"):
        if not SALESFORCE_AVAILABLE:
            raise ImportError("simple-salesforce no está instalado. Instala con: pip install simple-salesforce")
        
        self.client = Salesforce(
            username=username,
            password=password,
            security_token=security_token,
            domain=domain
        )
    
    def update_opportunity(
        self,
        opportunity_id: str,
        kyc_status: str,
        risk_score: int,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """Actualiza una Opportunity en Salesforce."""
        try:
            update_data = {
                "KYC_Status__c": kyc_status,
                "Risk_Score__c": risk_score,
                "KYC_Review_Date__c": datetime.now().isoformat()
            }
            
            self.client.Opportunity.update(opportunity_id, update_data)
            
            # Añadir nota si se proporciona
            if notes:
                self.client.Note.create({
                    "ParentId": opportunity_id,
                    "Title": "KYC Compliance Check",
                    "Body": notes
                })
            
            return {"success": True, "opportunity_id": opportunity_id}
        
        except Exception as e:
            logger.error(f"Error actualizando Salesforce: {e}")
            return {"success": False, "error": str(e)}

