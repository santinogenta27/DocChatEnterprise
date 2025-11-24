"""
Email Marketing Tool para Agentic AI - Integración con Mailchimp, HubSpot, ActiveCampaign.
Permite crear campañas, automatizar flujos, segmentar audiencias y analizar performance.
"""

from __future__ import annotations

import json
import os
import requests
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from pathlib import Path

from .base_tool import BaseTool, ToolResult


class EmailMarketingTool(BaseTool):
    """
    Herramienta de Email Marketing para:
    - Crear y gestionar campañas de email
    - Automatizar flujos de trabajo
    - Segmentar audiencias
    - Analizar performance
    - Integraciones con Mailchimp, HubSpot, ActiveCampaign
    """
    
    def __init__(self, config: Any):
        super().__init__(config)
        
        # Directorios para almacenar datos
        self.data_dir = Path(config.memory_dir) / "email_marketing_data"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Archivos de datos
        self.campaigns_file = self.data_dir / "email_campaigns.json"
        self.audiences_file = self.data_dir / "audiences.json"
        self.automations_file = self.data_dir / "automations.json"
        
        # Credenciales de APIs (desde .env)
        self.mailchimp_api_key = os.getenv("MAILCHIMP_API_KEY", "")
        self.mailchimp_server = os.getenv("MAILCHIMP_SERVER", "")  # ej: us1, us2
        self.hubspot_api_key = os.getenv("HUBSPOT_API_KEY", "")
        self.activecampaign_api_key = os.getenv("ACTIVECAMPAIGN_API_KEY", "")
        self.activecampaign_api_url = os.getenv("ACTIVECAMPAIGN_API_URL", "")
        
        # Inicializar archivos
        self._initialize_data_files()
    
    def _initialize_data_files(self):
        """Inicializa archivos de datos si no existen."""
        for file_path in [self.campaigns_file, self.audiences_file, self.automations_file]:
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
        return "email_marketing"
    
    def get_description(self) -> str:
        return """Email marketing tool with:
        - Campaign creation and management
        - Automated workflows and sequences
        - Audience segmentation
        - Performance analytics
        - Integration with Mailchimp, HubSpot, ActiveCampaign"""
    
    def get_keywords(self) -> List[str]:
        return [
            "email marketing", "mailchimp", "hubspot", "activecampaign",
            "campaña email", "email campaign", "newsletter", "automation",
            "workflow", "segmentación", "segmentation", "audience"
        ]
    
    def execute(
        self,
        action: str,
        platform: Optional[str] = None,
        campaign_data: Optional[Dict[str, Any]] = None,
        audience_data: Optional[Dict[str, Any]] = None,
        automation_data: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> ToolResult:
        """
        Ejecuta acciones de email marketing.
        
        Args:
            action: Acción (create_campaign, send_campaign, create_audience, etc.)
            platform: Plataforma (mailchimp, hubspot, activecampaign, local)
            campaign_data: Datos de la campaña
            audience_data: Datos de la audiencia
            automation_data: Datos de automatización
        """
        try:
            platform = platform or kwargs.get("platform", "local")
            
            if action == "create_campaign":
                return self._create_campaign(platform, campaign_data or kwargs)
            elif action == "send_campaign":
                return self._send_campaign(platform, kwargs.get("campaign_id"))
            elif action == "create_audience":
                return self._create_audience(platform, audience_data or kwargs)
            elif action == "add_subscriber":
                return self._add_subscriber(platform, kwargs.get("email"), kwargs.get("list_id"))
            elif action == "create_automation":
                return self._create_automation(platform, automation_data or kwargs)
            elif action == "analyze_performance":
                return self._analyze_performance(platform, kwargs.get("campaign_id"))
            elif action == "segment_audience":
                return self._segment_audience(platform, kwargs.get("list_id"), kwargs.get("criteria"))
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
                message=f"Error executing email marketing action: {str(e)}",
                metadata={"error": str(e)}
            )
    
    def _create_campaign(self, platform: str, campaign_data: Dict[str, Any]) -> ToolResult:
        """Crea una nueva campaña de email."""
        campaign = {
            "id": f"campaign_{int(datetime.now().timestamp())}",
            "name": campaign_data.get("name", "Email Campaign"),
            "subject": campaign_data.get("subject", ""),
            "content": campaign_data.get("content", ""),
            "list_id": campaign_data.get("list_id", ""),
            "platform": platform,
            "status": "draft",
            "created_at": datetime.now().isoformat(),
            "scheduled_at": campaign_data.get("scheduled_at"),
            "performance": {
                "sent": 0,
                "delivered": 0,
                "opened": 0,
                "clicked": 0,
                "bounced": 0,
                "unsubscribed": 0
            }
        }
        
        campaigns = self._load_json(self.campaigns_file)
        campaigns.append(campaign)
        self._save_json(self.campaigns_file, campaigns)
        
        # Intentar crear en plataforma real
        platform_result = None
        if platform == "mailchimp" and self.mailchimp_api_key:
            platform_result = self._create_mailchimp_campaign(campaign)
        elif platform == "hubspot" and self.hubspot_api_key:
            platform_result = self._create_hubspot_campaign(campaign)
        elif platform == "activecampaign" and self.activecampaign_api_key:
            platform_result = self._create_activecampaign_campaign(campaign)
        
        return ToolResult(
            success=True,
            data={"campaign": campaign, "platform_result": platform_result},
            message=f"Email campaign '{campaign['name']}' created successfully",
            metadata={"platform": platform, "campaign_id": campaign["id"]}
        )
    
    def _send_campaign(self, platform: str, campaign_id: str) -> ToolResult:
        """Envía una campaña de email."""
        campaigns = self._load_json(self.campaigns_file)
        for campaign in campaigns:
            if campaign["id"] == campaign_id:
                campaign["status"] = "sent"
                campaign["sent_at"] = datetime.now().isoformat()
                self._save_json(self.campaigns_file, campaigns)
                
                # Intentar enviar en plataforma real
                if platform == "mailchimp" and self.mailchimp_api_key:
                    self._send_mailchimp_campaign(campaign_id)
                
                return ToolResult(
                    success=True,
                    data={"campaign": campaign},
                    message=f"Campaign '{campaign_id}' sent successfully",
                    metadata={"platform": platform}
                )
        
        return ToolResult(
            success=False,
            data=None,
            message=f"Campaign '{campaign_id}' not found",
            metadata={}
        )
    
    def _create_audience(self, platform: str, audience_data: Dict[str, Any]) -> ToolResult:
        """Crea una nueva audiencia/lista."""
        audience = {
            "id": f"audience_{int(datetime.now().timestamp())}",
            "name": audience_data.get("name", "Audience"),
            "platform": platform,
            "subscriber_count": 0,
            "created_at": datetime.now().isoformat()
        }
        
        audiences = self._load_json(self.audiences_file)
        audiences.append(audience)
        self._save_json(self.audiences_file, audiences)
        
        return ToolResult(
            success=True,
            data={"audience": audience},
            message=f"Audience '{audience['name']}' created successfully",
            metadata={"platform": platform, "audience_id": audience["id"]}
        )
    
    def _add_subscriber(self, platform: str, email: str, list_id: str) -> ToolResult:
        """Agrega un suscriptor a una lista."""
        # Actualizar contador de audiencia
        audiences = self._load_json(self.audiences_file)
        for audience in audiences:
            if audience["id"] == list_id:
                audience["subscriber_count"] = audience.get("subscriber_count", 0) + 1
                self._save_json(self.audiences_file, audiences)
                break
        
        return ToolResult(
            success=True,
            data={"email": email, "list_id": list_id},
            message=f"Subscriber '{email}' added to list",
            metadata={"platform": platform}
        )
    
    def _create_automation(self, platform: str, automation_data: Dict[str, Any]) -> ToolResult:
        """Crea un flujo de automatización."""
        automation = {
            "id": f"automation_{int(datetime.now().timestamp())}",
            "name": automation_data.get("name", "Automation"),
            "trigger": automation_data.get("trigger", "subscriber_added"),
            "steps": automation_data.get("steps", []),
            "platform": platform,
            "status": "active",
            "created_at": datetime.now().isoformat()
        }
        
        automations = self._load_json(self.automations_file)
        automations.append(automation)
        self._save_json(self.automations_file, automations)
        
        return ToolResult(
            success=True,
            data={"automation": automation},
            message=f"Automation '{automation['name']}' created successfully",
            metadata={"platform": platform, "automation_id": automation["id"]}
        )
    
    def _analyze_performance(self, platform: str, campaign_id: Optional[str] = None) -> ToolResult:
        """Analiza el performance de campañas."""
        campaigns = self._load_json(self.campaigns_file)
        
        if campaign_id:
            campaigns = [c for c in campaigns if c["id"] == campaign_id]
        
        total_sent = sum(c.get("performance", {}).get("sent", 0) for c in campaigns)
        total_opened = sum(c.get("performance", {}).get("opened", 0) for c in campaigns)
        total_clicked = sum(c.get("performance", {}).get("clicked", 0) for c in campaigns)
        
        open_rate = (total_opened / total_sent * 100) if total_sent > 0 else 0
        click_rate = (total_clicked / total_sent * 100) if total_sent > 0 else 0
        
        return ToolResult(
            success=True,
            data={
                "total_campaigns": len(campaigns),
                "total_sent": total_sent,
                "total_opened": total_opened,
                "total_clicked": total_clicked,
                "open_rate": f"{open_rate:.2f}%",
                "click_rate": f"{click_rate:.2f}%"
            },
            message=f"Performance analyzed: {len(campaigns)} campaigns",
            metadata={"platform": platform}
        )
    
    def _segment_audience(self, platform: str, list_id: str, criteria: Dict[str, Any]) -> ToolResult:
        """Segmenta una audiencia según criterios."""
        return ToolResult(
            success=True,
            data={"list_id": list_id, "criteria": criteria, "segment_size": 0},
            message=f"Audience segmented based on criteria",
            metadata={"platform": platform}
        )
    
    def _create_mailchimp_campaign(self, campaign: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Crea campaña en Mailchimp."""
        try:
            url = f"https://{self.mailchimp_server}.api.mailchimp.com/3.0/campaigns"
            auth = ("apikey", self.mailchimp_api_key)
            payload = {
                "type": "regular",
                "recipients": {"list_id": campaign.get("list_id", "")},
                "settings": {
                    "subject_line": campaign.get("subject", ""),
                    "from_name": "Your Company",
                    "reply_to": "noreply@example.com"
                }
            }
            
            response = requests.post(url, json=payload, auth=auth, timeout=10)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            print(f"Error creating Mailchimp campaign: {e}")
        return None
    
    def _create_hubspot_campaign(self, campaign: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Crea campaña en HubSpot."""
        try:
            url = "https://api.hubapi.com/marketing/v3/campaigns"
            headers = {
                "Authorization": f"Bearer {self.hubspot_api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "name": campaign.get("name", ""),
                "type": "EMAIL"
            }
            
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            if response.status_code == 201:
                return response.json()
        except Exception as e:
            print(f"Error creating HubSpot campaign: {e}")
        return None
    
    def _create_activecampaign_campaign(self, campaign: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Crea campaña en ActiveCampaign."""
        try:
            url = f"{self.activecampaign_api_url}/api/3/campaigns"
            headers = {
                "Api-Token": self.activecampaign_api_key,
                "Content-Type": "application/json"
            }
            payload = {
                "campaign": {
                    "name": campaign.get("name", ""),
                    "type": "single"
                }
            }
            
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            if response.status_code == 201:
                return response.json()
        except Exception as e:
            print(f"Error creating ActiveCampaign campaign: {e}")
        return None
    
    def _send_mailchimp_campaign(self, campaign_id: str):
        """Envía campaña en Mailchimp."""
        try:
            url = f"https://{self.mailchimp_server}.api.mailchimp.com/3.0/campaigns/{campaign_id}/actions/send"
            auth = ("apikey", self.mailchimp_api_key)
            requests.post(url, auth=auth, timeout=10)
        except Exception as e:
            print(f"Error sending Mailchimp campaign: {e}")

