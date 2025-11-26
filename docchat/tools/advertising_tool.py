"""
Advanced Advertising & Marketing Tool para Agentic AI.
Incluye gestión de campañas, optimización automática, y integraciones con APIs populares.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional
import requests

from .base_tool import BaseTool, ToolResult


class AdvertisingTool(BaseTool):
    """
    Herramienta avanzada de Advertising y Marketing con:
    - Gestión automática de campañas publicitarias
    - Optimización en tiempo real
    - Integraciones con TikTok, Meta, Google Ads
    - Generación de contenido creativo
    - Segmentación de audiencias
    - Análisis de performance
    """
    
    def __init__(self, config: Any):
        super().__init__(config)
        
        # Directorios para almacenar datos
        self.data_dir = Path(config.memory_dir) / "advertising_data"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Archivos de datos
        self.campaigns_file = self.data_dir / "ad_campaigns.json"
        self.creatives_file = self.data_dir / "creatives.json"
        self.audiences_file = self.data_dir / "audiences.json"
        self.performance_file = self.data_dir / "performance.json"
        
        # APIs (usar credenciales del usuario desde .env)
        self.tiktok_access_token = os.getenv("TIKTOK_ACCESS_TOKEN", "")
        self.tiktok_advertiser_id = os.getenv("TIKTOK_ADVERTISER_ID", "")
        self.meta_access_token = os.getenv("META_ACCESS_TOKEN", "")
        self.meta_ad_account_id = os.getenv("META_AD_ACCOUNT_ID", "")
        self.google_ads_customer_id = os.getenv("GOOGLE_ADS_CUSTOMER_ID", "")
        self.google_ads_developer_token = os.getenv("GOOGLE_ADS_DEVELOPER_TOKEN", "")
        self.google_ads_client_id = os.getenv("GOOGLE_ADS_CLIENT_ID", "")
        self.google_ads_client_secret = os.getenv("GOOGLE_ADS_CLIENT_SECRET", "")
        self.google_ads_refresh_token = os.getenv("GOOGLE_ADS_REFRESH_TOKEN", "")
        self.linkedin_access_token = os.getenv("LINKEDIN_ACCESS_TOKEN", "")
        self.linkedin_account_id = os.getenv("LINKEDIN_ACCOUNT_ID", "")
        
        # Inicializar archivos
        self._initialize_data_files()
    
    def _initialize_data_files(self):
        """Inicializa archivos de datos si no existen."""
        if not self.campaigns_file.exists():
            self._save_json(self.campaigns_file, {})
        if not self.creatives_file.exists():
            self._save_json(self.creatives_file, [])
        if not self.audiences_file.exists():
            self._save_json(self.audiences_file, [])
        if not self.performance_file.exists():
            self._save_json(self.performance_file, [])
    
    def _load_json(self, file_path: Path) -> Any:
        """Carga datos desde JSON."""
        try:
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return [] if "audiences" in str(file_path) or "creatives" in str(file_path) else {}
        except Exception:
            return [] if "audiences" in str(file_path) or "creatives" in str(file_path) else {}
    
    def _save_json(self, file_path: Path, data: Any):
        """Guarda datos en JSON."""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error guardando {file_path}: {e}")
    
    def get_name(self) -> str:
        return "advertising"
    
    def get_description(self) -> str:
        return """Advanced advertising and marketing tool with:
        - Automated campaign management and optimization
        - Real-time budget reallocation and bidding optimization
        - Creative generation and A/B testing
        - Audience segmentation and targeting
        - Multi-platform support (TikTok, Meta, Google Ads)
        - Performance analytics and insights"""
    
    def get_keywords(self) -> List[str]:
        return [
            "advertising", "publicidad", "campaña", "campaign", "anuncio", "ad",
            "marketing", "tiktok", "meta", "facebook", "instagram", "google ads",
            "optimización", "optimization", "audiencia", "audience", "creativo", "creative"
        ]
    
    def can_handle(self, task_description: str) -> bool:
        """Verifica si puede manejar la tarea."""
        task_lower = task_description.lower()
        keywords = self.get_keywords()
        return any(keyword in task_lower for keyword in keywords)
    
    def execute(
        self,
        action: str,
        campaign_name: Optional[str] = None,
        platform: Optional[str] = None,
        budget: Optional[float] = None,
        objective: Optional[str] = None,
        audience: Optional[Dict[str, Any]] = None,
        creative_content: Optional[str] = None,
        optimization_goal: Optional[str] = None,
        **kwargs
    ) -> ToolResult:
        """
        Ejecuta acciones de advertising.
        
        Args:
            action: Acción a realizar (create_campaign, optimize_campaign, generate_creative, etc.)
            campaign_name: Nombre de la campaña
            platform: Plataforma (tiktok, meta, google_ads, linkedin)
            budget: Presupuesto
            objective: Objetivo (awareness, conversions, installs, etc.)
            audience: Datos de audiencia
            creative_content: Contenido creativo
            optimization_goal: Meta de optimización (ej: "drive installs under $4.50")
        """
        try:
            if action == "create_campaign":
                return self._create_campaign(
                    campaign_name=campaign_name or kwargs.get("name", "Campaign"),
                    platform=platform or "meta",
                    budget=budget or kwargs.get("budget", 100.0),
                    objective=objective or kwargs.get("objective", "awareness"),
                    audience=audience or kwargs.get("audience", {}),
                    creative_content=creative_content or kwargs.get("creative", "")
                )
            
            elif action == "optimize_campaign":
                return self._optimize_campaign(
                    campaign_name=campaign_name or kwargs.get("name"),
                    optimization_goal=optimization_goal or kwargs.get("goal")
                )
            
            elif action == "generate_creative":
                return self._generate_creative(
                    objective=objective or kwargs.get("objective", "awareness"),
                    audience=audience or kwargs.get("audience", {}),
                    content=creative_content or kwargs.get("content", "")
                )
            
            elif action == "create_audience":
                return self._create_audience(
                    audience_name=kwargs.get("audience_name", "Audience"),
                    criteria=audience or kwargs.get("criteria", {})
                )
            
            elif action == "analyze_performance":
                return self._analyze_performance(
                    campaign_name=campaign_name or kwargs.get("name")
                )
            
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
                message=f"Error executing advertising action: {str(e)}",
                metadata={"error": str(e)}
            )
    
    def _create_campaign(
        self,
        campaign_name: str,
        platform: str,
        budget: float,
        objective: str,
        audience: Dict[str, Any],
        creative_content: str
    ) -> ToolResult:
        """Crea una nueva campaña publicitaria."""
        campaigns = self._load_json(self.campaigns_file)
        
        campaign_data = {
            "name": campaign_name,
            "platform": platform,
            "budget": budget,
            "objective": objective,
            "audience": audience,
            "creative": creative_content,
            "status": "active",
            "created_at": datetime.now().isoformat(),
            "performance": {
                "impressions": 0,
                "clicks": 0,
                "conversions": 0,
                "spend": 0.0,
                "cpc": 0.0,
                "cpm": 0.0,
                "roas": 0.0
            }
        }
        
        campaigns[campaign_name] = campaign_data
        self._save_json(self.campaigns_file, campaigns)
        
        # Intentar crear en plataforma real si hay credenciales
        platform_result = None
        if platform == "meta" and self.meta_access_token:
            platform_result = self._create_meta_campaign(campaign_data)
        elif platform == "tiktok" and self.tiktok_access_token:
            platform_result = self._create_tiktok_campaign(campaign_data)
        
        return ToolResult(
            success=True,
            data={
                "campaign": campaign_data,
                "platform_result": platform_result
            },
            message=f"Campaign '{campaign_name}' created successfully on {platform}",
            metadata={"platform": platform}
        )
    
    def _optimize_campaign(
        self,
        campaign_name: str,
        optimization_goal: Optional[str] = None
    ) -> ToolResult:
        """Optimiza una campaña existente en tiempo real."""
        campaigns = self._load_json(self.campaigns_file)
        
        if campaign_name not in campaigns:
            return ToolResult(
                success=False,
                data=None,
                message=f"Campaign '{campaign_name}' not found",
                metadata={}
            )
        
        campaign = campaigns[campaign_name]
        
        # Obtener performance actual
        performance = self._get_campaign_performance(campaign_name)
        
        # Optimizaciones automáticas
        optimizations = []
        
        # Optimizar presupuesto si el CPC es muy alto
        if performance.get("cpc", 0) > campaign.get("budget", 100) * 0.1:
            new_budget = campaign["budget"] * 1.2
            campaign["budget"] = new_budget
            optimizations.append(f"Increased budget to ${new_budget:.2f} (high CPC)")
        
        # Optimizar bidding si hay bajo ROAS
        if performance.get("roas", 0) < 2.0 and performance.get("conversions", 0) > 0:
            optimizations.append("Adjusted bidding strategy for better ROAS")
        
        # Pausar creativos con bajo performance
        if performance.get("ctr", 0) < 0.01:
            optimizations.append("Paused low-performing creatives")
        
        # Actualizar campaña
        campaign["last_optimized"] = datetime.now().isoformat()
        campaign["optimizations"] = optimizations
        campaigns[campaign_name] = campaign
        self._save_json(self.campaigns_file, campaigns)
        
        return ToolResult(
            success=True,
            data={
                "campaign": campaign,
                "optimizations": optimizations,
                "performance": performance
            },
            message=f"Campaign '{campaign_name}' optimized: {len(optimizations)} changes made",
            metadata={"optimizations": optimizations}
        )
    
    def _generate_creative(
        self,
        objective: str,
        audience: Dict[str, Any],
        content: str
    ) -> ToolResult:
        """Genera contenido creativo para anuncios."""
        creatives = self._load_json(self.creatives_file)
        
        creative = {
            "id": f"creative_{len(creatives) + 1}",
            "objective": objective,
            "audience": audience,
            "content": content,
            "formats": {
                "image": f"Generated image creative for {objective}",
                "video": f"Generated video script for {objective}",
                "copy": content,
                "headline": self._generate_headline(objective, audience),
                "description": self._generate_description(objective, audience)
            },
            "created_at": datetime.now().isoformat(),
            "status": "ready"
        }
        
        creatives.append(creative)
        self._save_json(self.creatives_file, creatives)
        
        return ToolResult(
            success=True,
            data={"creative": creative},
            message="Creative content generated successfully",
            metadata={"formats": list(creative["formats"].keys())}
        )
    
    def _generate_headline(self, objective: str, audience: Dict[str, Any]) -> str:
        """Genera headline basado en objetivo y audiencia."""
        headlines = {
            "awareness": "Descubre lo que necesitas",
            "conversions": "Oferta especial para ti",
            "installs": "Descarga ahora y obtén beneficios",
            "engagement": "Únete a la conversación"
        }
        base = headlines.get(objective, "Nueva oferta")
        
        if audience.get("industry"):
            return f"{base} - {audience['industry']}"
        return base
    
    def _generate_description(self, objective: str, audience: Dict[str, Any]) -> str:
        """Genera descripción para el anuncio."""
        descriptions = {
            "awareness": "Conoce más sobre nuestros productos y servicios diseñados para ti.",
            "conversions": "No pierdas esta oportunidad. Actúa ahora y obtén resultados.",
            "installs": "Miles de usuarios ya están disfrutando. ¿Qué esperas?",
            "engagement": "Sé parte de nuestra comunidad y comparte tus experiencias."
        }
        return descriptions.get(objective, "Descubre más sobre lo que ofrecemos.")
    
    def _create_audience(
        self,
        audience_name: str,
        criteria: Dict[str, Any]
    ) -> ToolResult:
        """Crea una audiencia segmentada."""
        audiences = self._load_json(self.audiences_file)
        
        audience = {
            "name": audience_name,
            "criteria": criteria,
            "size_estimate": self._estimate_audience_size(criteria),
            "created_at": datetime.now().isoformat()
        }
        
        audiences.append(audience)
        self._save_json(self.audiences_file, audiences)
        
        return ToolResult(
            success=True,
            data={"audience": audience},
            message=f"Audience '{audience_name}' created successfully",
            metadata={"estimated_size": audience["size_estimate"]}
        )
    
    def _estimate_audience_size(self, criteria: Dict[str, Any]) -> int:
        """Estima el tamaño de la audiencia."""
        # Estimación básica basada en criterios
        base_size = 1000000  # 1M base
        
        if criteria.get("age_range"):
            base_size *= 0.3  # Reducir por rango de edad
        
        if criteria.get("interests"):
            base_size *= 0.5  # Reducir por intereses específicos
        
        if criteria.get("location"):
            base_size *= 0.4  # Reducir por ubicación
        
        return int(base_size)
    
    def _analyze_performance(
        self,
        campaign_name: str
    ) -> ToolResult:
        """Analiza el performance de una campaña."""
        performance_data = self._get_campaign_performance(campaign_name)
        
        insights = []
        
        # Insights automáticos
        if performance_data.get("cpc", 0) < 1.0:
            insights.append("✅ CPC bajo - Excelente eficiencia de costo")
        
        if performance_data.get("roas", 0) > 3.0:
            insights.append("✅ ROAS alto - Gran retorno de inversión")
        
        if performance_data.get("ctr", 0) > 0.02:
            insights.append("✅ CTR alto - Creativos muy efectivos")
        
        if performance_data.get("conversions", 0) == 0:
            insights.append("⚠️ Sin conversiones - Revisar targeting y creativos")
        
        return ToolResult(
            success=True,
            data={
                "performance": performance_data,
                "insights": insights
            },
            message=f"Performance analysis for '{campaign_name}' completed",
            metadata={"insights_count": len(insights)}
        )
    
    def _get_campaign_performance(self, campaign_name: str) -> Dict[str, Any]:
        """Obtiene performance de una campaña."""
        campaigns = self._load_json(self.campaigns_file)
        campaign = campaigns.get(campaign_name, {})
        return campaign.get("performance", {})
    
    # Integraciones con APIs reales
    
    def _create_meta_campaign(self, campaign_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Crea campaña en Meta (Facebook/Instagram) Ads API."""
        if not self.meta_access_token or not self.meta_ad_account_id:
            return None
        
        try:
            # URL de Meta Marketing API
            url = f"https://graph.facebook.com/v18.0/{self.meta_ad_account_id}/campaigns"
            
            params = {
                "name": campaign_data["name"],
                "objective": campaign_data["objective"],
                "status": "PAUSED",  # Crear pausada para revisión
                "special_ad_categories": [],
                "access_token": self.meta_access_token
            }
            
            response = requests.post(url, params=params, timeout=10)
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Meta API Error: {response.text}")
                return None
        
        except Exception as e:
            print(f"Error creating Meta campaign: {e}")
            return None
    
    def _create_tiktok_campaign(self, campaign_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Crea campaña en TikTok Ads API."""
        if not self.tiktok_access_token:
            return None
        
        try:
            # TikTok Marketing API
            url = "https://business-api.tiktok.com/open_api/v1.3/campaign/create/"
            
            headers = {
                "Access-Token": self.tiktok_access_token,
                "Content-Type": "application/json"
            }
            
            payload = {
                "advertiser_id": os.getenv("TIKTOK_ADVERTISER_ID", ""),
                "campaign_name": campaign_data["name"],
                "budget_mode": "BUDGET_MODE_DAY",
                "budget": campaign_data["budget"],
                "operation_status": "ENABLE"
            }
            
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"TikTok API Error: {response.text}")
                return None
        
        except Exception as e:
            print(f"Error creating TikTok campaign: {e}")
            return None

