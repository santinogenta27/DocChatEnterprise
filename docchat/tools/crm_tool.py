"""
CRM Tool para Agentic AI - Integración con Salesforce, Pipedrive, Zoho CRM.
Permite gestionar leads, contactos, oportunidades y automatizar el proceso de ventas.
"""

from __future__ import annotations

import json
import os
import requests
from datetime import datetime
from typing import Any, Dict, List, Optional
from pathlib import Path

from .base_tool import BaseTool, ToolResult


class CRMTool(BaseTool):
    """
    Herramienta de CRM para gestionar:
    - Leads y contactos
    - Oportunidades de venta
    - Pipeline de ventas
    - Automatización de seguimiento
    - Integraciones con Salesforce, Pipedrive, Zoho CRM
    """
    
    def __init__(self, config: Any):
        super().__init__(config)
        
        # Directorios para almacenar datos
        self.data_dir = Path(config.memory_dir) / "crm_data"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Archivos de datos
        self.leads_file = self.data_dir / "leads.json"
        self.contacts_file = self.data_dir / "contacts.json"
        self.opportunities_file = self.data_dir / "opportunities.json"
        
        # Credenciales de APIs (desde .env)
        self.salesforce_instance_url = os.getenv("SALESFORCE_INSTANCE_URL", "")
        self.salesforce_access_token = os.getenv("SALESFORCE_ACCESS_TOKEN", "")
        self.pipedrive_api_token = os.getenv("PIPEDRIVE_API_TOKEN", "")
        self.pipedrive_company_domain = os.getenv("PIPEDRIVE_COMPANY_DOMAIN", "")
        self.zoho_api_token = os.getenv("ZOHO_API_TOKEN", "")
        self.zoho_org_id = os.getenv("ZOHO_ORG_ID", "")
        
        # Inicializar archivos
        self._initialize_data_files()
    
    def _initialize_data_files(self):
        """Inicializa archivos de datos si no existen."""
        for file_path in [self.leads_file, self.contacts_file, self.opportunities_file]:
            if not file_path.exists():
                self._save_json(file_path, [])
    
    def _load_json(self, file_path: Path) -> List[Dict[str, Any]]:
        """Carga datos desde JSON."""
        try:
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return []
        except Exception:
            return []
    
    def _save_json(self, file_path: Path, data: Any):
        """Guarda datos en JSON."""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error guardando {file_path}: {e}")
    
    def get_name(self) -> str:
        return "crm_manager"
    
    def get_description(self) -> str:
        return """CRM management tool with:
        - Lead and contact management
        - Sales opportunity tracking
        - Pipeline automation
        - Integration with Salesforce, Pipedrive, Zoho CRM
        - Automated follow-up and nurturing"""
    
    def get_keywords(self) -> List[str]:
        return [
            "crm", "salesforce", "pipedrive", "zoho", "lead", "contacto",
            "oportunidad", "opportunity", "pipeline", "ventas", "sales",
            "seguimiento", "follow-up", "nurturing"
        ]
    
    def execute(
        self,
        action: str,
        crm_platform: Optional[str] = None,
        lead_data: Optional[Dict[str, Any]] = None,
        contact_data: Optional[Dict[str, Any]] = None,
        opportunity_data: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> ToolResult:
        """
        Ejecuta acciones de CRM.
        
        Args:
            action: Acción (create_lead, update_contact, create_opportunity, etc.)
            crm_platform: Plataforma (salesforce, pipedrive, zoho, local)
            lead_data: Datos del lead
            contact_data: Datos del contacto
            opportunity_data: Datos de la oportunidad
        """
        try:
            platform = crm_platform or kwargs.get("platform", "local")
            
            if action == "create_lead":
                return self._create_lead(platform, lead_data or kwargs)
            elif action == "update_lead":
                return self._update_lead(platform, kwargs.get("lead_id"), lead_data or kwargs)
            elif action == "create_contact":
                return self._create_contact(platform, contact_data or kwargs)
            elif action == "update_contact":
                return self._update_contact(platform, kwargs.get("contact_id"), contact_data or kwargs)
            elif action == "create_opportunity":
                return self._create_opportunity(platform, opportunity_data or kwargs)
            elif action == "update_opportunity":
                return self._update_opportunity(platform, kwargs.get("opportunity_id"), opportunity_data or kwargs)
            elif action == "get_pipeline":
                return self._get_pipeline(platform)
            elif action == "automate_followup":
                return self._automate_followup(platform, kwargs.get("contact_id"))
            else:
                return ToolResult(
                    success=False,
                    data=None,
                    message=f"Unknown action: {action}",
                    metadata={}
                )
        
        except Exception as e:
            return ToolResult(
                success=False,
                data=None,
                message=f"Error executing CRM action: {str(e)}",
                metadata={"error": str(e)}
            )
    
    def _create_lead(self, platform: str, lead_data: Dict[str, Any]) -> ToolResult:
        """Crea un nuevo lead."""
        lead = {
            "id": f"lead_{int(datetime.now().timestamp())}",
            "name": lead_data.get("name", ""),
            "email": lead_data.get("email", ""),
            "phone": lead_data.get("phone", ""),
            "company": lead_data.get("company", ""),
            "status": "new",
            "source": lead_data.get("source", "website"),
            "created_at": datetime.now().isoformat(),
            "notes": lead_data.get("notes", "")
        }
        
        # Guardar localmente
        leads = self._load_json(self.leads_file)
        leads.append(lead)
        self._save_json(self.leads_file, leads)
        
        # Intentar crear en plataforma real
        platform_result = None
        if platform == "salesforce" and self.salesforce_access_token:
            platform_result = self._create_salesforce_lead(lead)
        elif platform == "pipedrive" and self.pipedrive_api_token:
            platform_result = self._create_pipedrive_person(lead)
        elif platform == "zoho" and self.zoho_api_token:
            platform_result = self._create_zoho_lead(lead)
        
        return ToolResult(
            success=True,
            data={"lead": lead, "platform_result": platform_result},
            message=f"Lead '{lead['name']}' created successfully",
            metadata={"platform": platform, "lead_id": lead["id"]}
        )
    
    def _create_contact(self, platform: str, contact_data: Dict[str, Any]) -> ToolResult:
        """Crea un nuevo contacto."""
        contact = {
            "id": f"contact_{int(datetime.now().timestamp())}",
            "name": contact_data.get("name", ""),
            "email": contact_data.get("email", ""),
            "phone": contact_data.get("phone", ""),
            "company": contact_data.get("company", ""),
            "title": contact_data.get("title", ""),
            "created_at": datetime.now().isoformat(),
            "last_contact": datetime.now().isoformat()
        }
        
        contacts = self._load_json(self.contacts_file)
        contacts.append(contact)
        self._save_json(self.contacts_file, contacts)
        
        return ToolResult(
            success=True,
            data={"contact": contact},
            message=f"Contact '{contact['name']}' created successfully",
            metadata={"platform": platform, "contact_id": contact["id"]}
        )
    
    def _create_opportunity(self, platform: str, opportunity_data: Dict[str, Any]) -> ToolResult:
        """Crea una nueva oportunidad de venta."""
        opportunity = {
            "id": f"opp_{int(datetime.now().timestamp())}",
            "name": opportunity_data.get("name", ""),
            "contact_id": opportunity_data.get("contact_id", ""),
            "amount": opportunity_data.get("amount", 0.0),
            "stage": opportunity_data.get("stage", "prospecting"),
            "probability": opportunity_data.get("probability", 10),
            "close_date": opportunity_data.get("close_date", ""),
            "created_at": datetime.now().isoformat()
        }
        
        opportunities = self._load_json(self.opportunities_file)
        opportunities.append(opportunity)
        self._save_json(self.opportunities_file, opportunities)
        
        return ToolResult(
            success=True,
            data={"opportunity": opportunity},
            message=f"Opportunity '{opportunity['name']}' created successfully",
            metadata={"platform": platform, "opportunity_id": opportunity["id"]}
        )
    
    def _update_lead(self, platform: str, lead_id: str, updates: Dict[str, Any]) -> ToolResult:
        """Actualiza un lead existente."""
        leads = self._load_json(self.leads_file)
        for lead in leads:
            if lead["id"] == lead_id:
                lead.update(updates)
                lead["updated_at"] = datetime.now().isoformat()
                self._save_json(self.leads_file, leads)
                return ToolResult(
                    success=True,
                    data={"lead": lead},
                    message=f"Lead '{lead_id}' updated successfully",
                    metadata={"platform": platform}
                )
        
        return ToolResult(
            success=False,
            data=None,
            message=f"Lead '{lead_id}' not found",
            metadata={}
        )
    
    def _update_contact(self, platform: str, contact_id: str, updates: Dict[str, Any]) -> ToolResult:
        """Actualiza un contacto existente."""
        contacts = self._load_json(self.contacts_file)
        for contact in contacts:
            if contact["id"] == contact_id:
                contact.update(updates)
                contact["updated_at"] = datetime.now().isoformat()
                self._save_json(self.contacts_file, contacts)
                return ToolResult(
                    success=True,
                    data={"contact": contact},
                    message=f"Contact '{contact_id}' updated successfully",
                    metadata={"platform": platform}
                )
        
        return ToolResult(
            success=False,
            data=None,
            message=f"Contact '{contact_id}' not found",
            metadata={}
        )
    
    def _update_opportunity(self, platform: str, opportunity_id: str, updates: Dict[str, Any]) -> ToolResult:
        """Actualiza una oportunidad existente."""
        opportunities = self._load_json(self.opportunities_file)
        for opp in opportunities:
            if opp["id"] == opportunity_id:
                opp.update(updates)
                opp["updated_at"] = datetime.now().isoformat()
                self._save_json(self.opportunities_file, opportunities)
                return ToolResult(
                    success=True,
                    data={"opportunity": opp},
                    message=f"Opportunity '{opportunity_id}' updated successfully",
                    metadata={"platform": platform}
                )
        
        return ToolResult(
            success=False,
            data=None,
            message=f"Opportunity '{opportunity_id}' not found",
            metadata={}
        )
    
    def _get_pipeline(self, platform: str) -> ToolResult:
        """Obtiene el pipeline de ventas."""
        opportunities = self._load_json(self.opportunities_file)
        
        pipeline = {
            "prospecting": [],
            "qualification": [],
            "proposal": [],
            "negotiation": [],
            "closed_won": [],
            "closed_lost": []
        }
        
        for opp in opportunities:
            stage = opp.get("stage", "prospecting")
            if stage in pipeline:
                pipeline[stage].append(opp)
        
        total_value = sum(opp.get("amount", 0) for opp in opportunities if opp.get("stage") not in ["closed_lost"])
        
        return ToolResult(
            success=True,
            data={
                "pipeline": pipeline,
                "total_opportunities": len(opportunities),
                "total_value": total_value,
                "by_stage": {stage: len(opps) for stage, opps in pipeline.items()}
            },
            message=f"Pipeline retrieved: {len(opportunities)} opportunities",
            metadata={"platform": platform}
        )
    
    def _automate_followup(self, platform: str, contact_id: Optional[str] = None) -> ToolResult:
        """Automatiza seguimiento con contactos."""
        contacts = self._load_json(self.contacts_file)
        
        followups = []
        for contact in contacts:
            if contact_id and contact["id"] != contact_id:
                continue
            
            # Verificar si necesita seguimiento (último contacto hace más de 7 días)
            last_contact = contact.get("last_contact", "")
            if last_contact:
                from datetime import datetime, timedelta
                last_date = datetime.fromisoformat(last_contact)
                if datetime.now() - last_date > timedelta(days=7):
                    followups.append({
                        "contact_id": contact["id"],
                        "name": contact["name"],
                        "email": contact["email"],
                        "action": "send_followup_email"
                    })
        
        return ToolResult(
            success=True,
            data={"followups": followups},
            message=f"Identified {len(followups)} contacts needing follow-up",
            metadata={"platform": platform, "count": len(followups)}
        )
    
    def _create_salesforce_lead(self, lead: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Crea lead en Salesforce."""
        try:
            url = f"{self.salesforce_instance_url}/services/data/v57.0/sobjects/Lead"
            headers = {
                "Authorization": f"Bearer {self.salesforce_access_token}",
                "Content-Type": "application/json"
            }
            payload = {
                "FirstName": lead.get("name", "").split()[0] if lead.get("name") else "",
                "LastName": lead.get("name", "").split()[-1] if lead.get("name") else "",
                "Email": lead.get("email", ""),
                "Phone": lead.get("phone", ""),
                "Company": lead.get("company", "")
            }
            
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            if response.status_code == 201:
                return response.json()
        except Exception as e:
            print(f"Error creating Salesforce lead: {e}")
        return None
    
    def _create_pipedrive_person(self, lead: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Crea persona en Pipedrive."""
        try:
            url = f"https://{self.pipedrive_company_domain}.pipedrive.com/api/v1/persons"
            params = {"api_token": self.pipedrive_api_token}
            payload = {
                "name": lead.get("name", ""),
                "email": [{"value": lead.get("email", ""), "primary": True}],
                "phone": [{"value": lead.get("phone", ""), "primary": True}]
            }
            
            response = requests.post(url, json=payload, params=params, timeout=10)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            print(f"Error creating Pipedrive person: {e}")
        return None
    
    def _create_zoho_lead(self, lead: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Crea lead en Zoho CRM."""
        try:
            url = f"https://www.zohoapis.com/crm/v2/Leads"
            headers = {
                "Authorization": f"Zoho-oauthtoken {self.zoho_api_token}",
                "Content-Type": "application/json"
            }
            payload = {
                "data": [{
                    "Last_Name": lead.get("name", ""),
                    "Email": lead.get("email", ""),
                    "Phone": lead.get("phone", ""),
                    "Company": lead.get("company", "")
                }]
            }
            
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            if response.status_code == 201:
                return response.json()
        except Exception as e:
            print(f"Error creating Zoho lead: {e}")
        return None

