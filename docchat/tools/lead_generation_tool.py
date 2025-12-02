"""
Lead Generation Tool para generación automática de leads con Agentic AI.
Integra con LinkedIn, Apollo.io, ZoomInfo, Google Ads, Facebook Lead Ads, etc.
"""

from __future__ import annotations

import json
import os
import requests
from typing import Any, Dict, List, Optional
from datetime import datetime

from .base_tool import BaseTool, ToolResult


class LeadGenerationTool(BaseTool):
    """
    Herramienta de generación automática de leads usando Agentic AI.
    
    Integraciones:
    - LinkedIn Sales Navigator / LinkedIn API
    - Apollo.io (B2B database)
    - ZoomInfo (B2B database)
    - Google Ads (Lead form extensions)
    - Facebook Lead Ads
    - Web scraping (con permisos)
    - APIs públicas de empresas
    """
    
    def __init__(self, config: Any):
        super().__init__(config)
        
        # Credenciales de APIs
        # LinkedIn
        self.linkedin_client_id = os.getenv("LINKEDIN_CLIENT_ID", "")
        self.linkedin_client_secret = os.getenv("LINKEDIN_CLIENT_SECRET", "")
        self.linkedin_access_token = os.getenv("LINKEDIN_ACCESS_TOKEN", "")
        
        # Apollo.io
        self.apollo_api_key = os.getenv("APOLLO_API_KEY", "")
        
        # ZoomInfo
        self.zoominfo_username = os.getenv("ZOOMINFO_USERNAME", "")
        self.zoominfo_password = os.getenv("ZOOMINFO_PASSWORD", "")
        
        # Google Ads
        self.google_ads_client_id = os.getenv("GOOGLE_ADS_CLIENT_ID", "")
        self.google_ads_client_secret = os.getenv("GOOGLE_ADS_CLIENT_SECRET", "")
        self.google_ads_refresh_token = os.getenv("GOOGLE_ADS_REFRESH_TOKEN", "")
        self.google_ads_customer_id = os.getenv("GOOGLE_ADS_CUSTOMER_ID", "")
        
        # Facebook Lead Ads
        self.facebook_access_token = os.getenv("FACEBOOK_ACCESS_TOKEN", "")
        self.facebook_app_id = os.getenv("FACEBOOK_APP_ID", "")
        self.facebook_app_secret = os.getenv("FACEBOOK_APP_SECRET", "")
    
    def get_name(self) -> str:
        return "lead_generation"
    
    def get_description(self) -> str:
        return """Automatic lead generation tool using Agentic AI:
        - Search LinkedIn for prospects
        - Query B2B databases (Apollo, ZoomInfo)
        - Extract leads from Google Ads
        - Get leads from Facebook Lead Ads
        - Web scraping (with permissions)
        - Generate leads based on criteria"""
    
    def get_keywords(self) -> List[str]:
        return [
            "lead generation", "prospecting", "find leads", "apollo", "zoominfo",
            "linkedin", "google ads", "facebook leads", "generate leads", "b2b database"
        ]
    
    def execute(
        self,
        action: str,
        source: str,
        criteria: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> ToolResult:
        """
        Ejecuta acciones de generación de leads.
        
        Args:
            action: Acción (search_prospects, generate_leads, extract_leads, etc.)
            source: Fuente (linkedin, apollo, zoominfo, google_ads, facebook, web)
            criteria: Criterios de búsqueda (industry, location, company_size, etc.)
        """
        try:
            if action == "search_prospects" or action == "generate_leads":
                if source == "linkedin":
                    return self._search_linkedin(criteria or kwargs)
                elif source == "apollo":
                    return self._search_apollo(criteria or kwargs)
                elif source == "zoominfo":
                    return self._search_zoominfo(criteria or kwargs)
                elif source == "google_ads":
                    return self._extract_google_ads_leads(criteria or kwargs)
                elif source == "facebook":
                    return self._extract_facebook_leads(criteria or kwargs)
                elif source == "web":
                    return self._scrape_web_leads(criteria or kwargs)
                else:
                    return ToolResult(
                        success=False,
                        data=None,
                        message=f"Source {source} not supported",
                        metadata={}
                    )
            elif action == "enrich_lead":
                return self._enrich_lead_data(kwargs.get("lead_data"))
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
                message=f"Error executing lead generation: {str(e)}",
                metadata={"error": str(e)}
            )
    
    def _search_linkedin(self, criteria: Dict[str, Any]) -> ToolResult:
        """Busca prospects en LinkedIn."""
        if not self.linkedin_access_token:
            return ToolResult(
                success=False,
                data=None,
                message="LinkedIn credentials not configured",
                metadata={"note": "Set LINKEDIN_ACCESS_TOKEN"}
            )
        
        try:
            # LinkedIn API v2 para búsqueda de personas
            url = "https://api.linkedin.com/v2/people-search"
            headers = {
                "Authorization": f"Bearer {self.linkedin_access_token}",
                "Content-Type": "application/json"
            }
            
            # Construir query de búsqueda
            query_parts = []
            if criteria.get("industry"):
                query_parts.append(f"industry:{criteria['industry']}")
            if criteria.get("location"):
                query_parts.append(f"location:{criteria['location']}")
            if criteria.get("company"):
                query_parts.append(f"company:{criteria['company']}")
            if criteria.get("title"):
                query_parts.append(f"title:{criteria['title']}")
            
            params = {
                "keywords": " ".join(query_parts) if query_parts else "",
                "count": criteria.get("limit", 10)
            }
            
            response = requests.get(url, headers=headers, params=params, timeout=10)
            
            if response.status_code == 200:
                results = response.json()
                leads = []
                
                for person in results.get("elements", []):
                    lead = {
                        "name": f"{person.get('firstName', '')} {person.get('lastName', '')}",
                        "position": person.get("headline", ""),
                        "company": person.get("companyName", ""),
                        "location": person.get("location", ""),
                        "linkedin_url": person.get("profileUrl", ""),
                        "source": "linkedin"
                    }
                    leads.append(lead)
                
                return ToolResult(
                    success=True,
                    data={"leads": leads, "total": len(leads)},
                    message=f"Found {len(leads)} prospects on LinkedIn",
                    metadata={"source": "linkedin", "criteria": criteria}
                )
            else:
                return ToolResult(
                    success=False,
                    data=None,
                    message=f"LinkedIn API error: {response.status_code} - {response.text}",
                    metadata={"source": "linkedin", "status_code": response.status_code}
                )
        
        except Exception as e:
            return ToolResult(
                success=False,
                data=None,
                message=f"LinkedIn API error: {str(e)}",
                metadata={"source": "linkedin", "error": str(e)}
            )
    
    def _search_apollo(self, criteria: Dict[str, Any]) -> ToolResult:
        """Busca prospects en Apollo.io."""
        if not self.apollo_api_key:
            return ToolResult(
                success=False,
                data=None,
                message="Apollo.io API key not configured",
                metadata={"note": "Set APOLLO_API_KEY"}
            )
        
        try:
            url = "https://api.apollo.io/v1/mixed_people/search"
            headers = {
                "Cache-Control": "no-cache",
                "Content-Type": "application/json"
            }
            
            payload = {
                "api_key": self.apollo_api_key,
                "q_keywords": criteria.get("keywords", ""),
                "person_titles": criteria.get("titles", []),
                "person_locations": criteria.get("locations", []),
                "organization_locations": criteria.get("company_locations", []),
                "organization_industries": criteria.get("industries", []),
                "organization_num_employees_ranges": criteria.get("company_sizes", []),
                "page": criteria.get("page", 1),
                "per_page": criteria.get("limit", 25)
            }
            
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            
            if response.status_code == 200:
                results = response.json()
                leads = []
                
                for person in results.get("people", []):
                    lead = {
                        "name": person.get("name", ""),
                        "email": person.get("email", ""),
                        "phone": person.get("phone_numbers", [{}])[0].get("raw_number", "") if person.get("phone_numbers") else "",
                        "position": person.get("title", ""),
                        "company": person.get("organization", {}).get("name", "") if person.get("organization") else "",
                        "industry": person.get("organization", {}).get("industry", "") if person.get("organization") else "",
                        "location": person.get("city", "") + ", " + person.get("state", ""),
                        "linkedin_url": person.get("linkedin_url", ""),
                        "source": "apollo"
                    }
                    leads.append(lead)
                
                return ToolResult(
                    success=True,
                    data={"leads": leads, "total": len(leads), "pagination": results.get("pagination", {})},
                    message=f"Found {len(leads)} prospects on Apollo.io",
                    metadata={"source": "apollo", "criteria": criteria}
                )
            else:
                return ToolResult(
                    success=False,
                    data=None,
                    message=f"Apollo.io API error: {response.status_code} - {response.text}",
                    metadata={"source": "apollo", "status_code": response.status_code}
                )
        
        except Exception as e:
            return ToolResult(
                success=False,
                data=None,
                message=f"Apollo.io API error: {str(e)}",
                metadata={"source": "apollo", "error": str(e)}
            )
    
    def _search_zoominfo(self, criteria: Dict[str, Any]) -> ToolResult:
        """Busca prospects en ZoomInfo."""
        if not self.zoominfo_username or not self.zoominfo_password:
            return ToolResult(
                success=False,
                data=None,
                message="ZoomInfo credentials not configured",
                metadata={"note": "Set ZOOMINFO_USERNAME and ZOOMINFO_PASSWORD"}
            )
        
        try:
            # ZoomInfo API requiere autenticación y luego búsqueda
            # Por simplicidad, retornamos estructura básica
            return ToolResult(
                success=False,
                data=None,
                message="ZoomInfo integration requires additional setup",
                metadata={"note": "ZoomInfo API integration needs OAuth setup"}
            )
        
        except Exception as e:
            return ToolResult(
                success=False,
                data=None,
                message=f"ZoomInfo API error: {str(e)}",
                metadata={"source": "zoominfo", "error": str(e)}
            )
    
    def _extract_google_ads_leads(self, criteria: Dict[str, Any]) -> ToolResult:
        """Extrae leads de Google Ads Lead Form Extensions."""
        if not self.google_ads_refresh_token:
            return ToolResult(
                success=False,
                data=None,
                message="Google Ads credentials not configured",
                metadata={"note": "Set GOOGLE_ADS_REFRESH_TOKEN"}
            )
        
        try:
            # Google Ads API para obtener leads de formularios
            # Requiere OAuth y acceso a Google Ads API
            return ToolResult(
                success=False,
                data=None,
                message="Google Ads lead extraction requires OAuth setup",
                metadata={"note": "Google Ads API integration needs OAuth flow"}
            )
        
        except Exception as e:
            return ToolResult(
                success=False,
                data=None,
                message=f"Google Ads API error: {str(e)}",
                metadata={"source": "google_ads", "error": str(e)}
            )
    
    def _extract_facebook_leads(self, criteria: Dict[str, Any]) -> ToolResult:
        """Extrae leads de Facebook Lead Ads."""
        if not self.facebook_access_token:
            return ToolResult(
                success=False,
                data=None,
                message="Facebook access token not configured",
                metadata={"note": "Set FACEBOOK_ACCESS_TOKEN"}
            )
        
        try:
            # Facebook Graph API para obtener leads
            lead_form_id = criteria.get("lead_form_id")
            if not lead_form_id:
                return ToolResult(
                    success=False,
                    data=None,
                    message="Lead form ID required",
                    metadata={}
                )
            
            url = f"https://graph.facebook.com/v18.0/{lead_form_id}/leads"
            params = {
                "access_token": self.facebook_access_token,
                "limit": criteria.get("limit", 100)
            }
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                results = response.json()
                leads = []
                
                for lead_data in results.get("data", []):
                    field_data = lead_data.get("field_data", [])
                    lead = {
                        "name": "",
                        "email": "",
                        "phone": "",
                        "source": "facebook_lead_ads"
                    }
                    
                    for field in field_data:
                        field_name = field.get("name", "").lower()
                        field_value = field.get("values", [""])[0] if field.get("values") else ""
                        
                        if "name" in field_name or "full_name" in field_name:
                            lead["name"] = field_value
                        elif "email" in field_name:
                            lead["email"] = field_value
                        elif "phone" in field_name:
                            lead["phone"] = field_value
                    
                    leads.append(lead)
                
                return ToolResult(
                    success=True,
                    data={"leads": leads, "total": len(leads)},
                    message=f"Extracted {len(leads)} leads from Facebook Lead Ads",
                    metadata={"source": "facebook", "lead_form_id": lead_form_id}
                )
            else:
                return ToolResult(
                    success=False,
                    data=None,
                    message=f"Facebook API error: {response.status_code} - {response.text}",
                    metadata={"source": "facebook", "status_code": response.status_code}
                )
        
        except Exception as e:
            return ToolResult(
                success=False,
                data=None,
                message=f"Facebook API error: {str(e)}",
                metadata={"source": "facebook", "error": str(e)}
            )
    
    def _scrape_web_leads(self, criteria: Dict[str, Any]) -> ToolResult:
        """Scrapea leads de sitios web (con permisos y respetando robots.txt)."""
        # Web scraping debe ser usado con cuidado y respetando términos de servicio
        return ToolResult(
            success=False,
            data=None,
            message="Web scraping requires careful implementation and legal compliance",
            metadata={"note": "Web scraping should respect robots.txt and terms of service"}
        )
    
    def _enrich_lead_data(self, lead_data: Dict[str, Any]) -> ToolResult:
        """Enriquece datos de un lead usando múltiples fuentes."""
        # Implementar enriquecimiento usando Apollo, ZoomInfo, etc.
        return ToolResult(
            success=False,
            data=None,
            message="Lead enrichment not yet fully implemented",
            metadata={}
        )

