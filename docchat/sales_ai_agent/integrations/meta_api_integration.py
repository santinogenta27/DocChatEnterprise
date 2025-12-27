"""
Meta API Integration - Integración opcional con Facebook/Instagram/Meta Ads API

Este módulo es OPCIONAL y se configura por separado.
No afecta el funcionamiento del agente principal si no está configurado.

Funcionalidades:
- Aprende de posts de Facebook/Instagram
- Aprende de campañas de Meta Ads
- Extrae conocimiento de contenido social
- Incorpora conocimiento en el RAG del agente
"""

from __future__ import annotations

import os
import json
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime, timedelta

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    requests = None


@dataclass
class MetaPost:
    """Post de Facebook/Instagram."""
    post_id: str
    message: str
    created_time: str
    page_id: str
    engagement_count: int = 0
    metadata: Dict[str, Any] = None


@dataclass
class MetaAdCampaign:
    """Campaña de Meta Ads."""
    campaign_id: str
    name: str
    objective: str
    status: str
    ad_creative_text: str
    ad_creative_description: str
    metadata: Dict[str, Any] = None


class MetaAPIIntegration:
    """
    Integración opcional con Meta APIs.
    
    Características:
    - Lee posts de Facebook/Instagram
    - Lee campañas de Meta Ads
    - Extrae conocimiento de contenido social
    - Incorpora conocimiento en el RAG
    """
    
    def __init__(
        self,
        facebook_access_token: Optional[str] = None,
        instagram_access_token: Optional[str] = None,
        meta_ads_access_token: Optional[str] = None,
        facebook_page_id: Optional[str] = None,
        instagram_business_account_id: Optional[str] = None,
        meta_ads_account_id: Optional[str] = None,
    ):
        """
        Inicializa la integración con Meta APIs.
        
        Args:
            facebook_access_token: Token de acceso de Facebook (opcional)
            instagram_access_token: Token de acceso de Instagram (opcional)
            meta_ads_access_token: Token de acceso de Meta Ads (opcional)
            facebook_page_id: ID de la página de Facebook (opcional)
            instagram_business_account_id: ID de la cuenta de negocio de Instagram (opcional)
            meta_ads_account_id: ID de la cuenta de Meta Ads (opcional)
        """
        # Cargar desde variables de entorno si no se proporcionan
        self.facebook_access_token = facebook_access_token or os.getenv("FACEBOOK_ACCESS_TOKEN")
        self.instagram_access_token = instagram_access_token or os.getenv("INSTAGRAM_ACCESS_TOKEN")
        self.meta_ads_access_token = meta_ads_access_token or os.getenv("META_ADS_ACCESS_TOKEN")
        
        self.facebook_page_id = facebook_page_id or os.getenv("FACEBOOK_PAGE_ID")
        self.instagram_business_account_id = instagram_business_account_id or os.getenv("INSTAGRAM_BUSINESS_ACCOUNT_ID")
        self.meta_ads_account_id = meta_ads_account_id or os.getenv("META_ADS_ACCOUNT_ID")
        
        # Verificar si está configurado
        self.is_configured = bool(
            (self.facebook_access_token and self.facebook_page_id) or
            (self.instagram_access_token and self.instagram_business_account_id) or
            (self.meta_ads_access_token and self.meta_ads_account_id)
        )
        
        if not REQUESTS_AVAILABLE:
            print("⚠️ requests no está instalado. Instala con: pip install requests")
            self.is_configured = False
        
        if self.is_configured:
            print("✅ Meta API Integration configurada")
        else:
            print("⚠️ Meta API Integration NO configurada (opcional - no afecta funcionamiento principal)")
    
    def fetch_facebook_posts(self, limit: int = 50) -> List[MetaPost]:
        """
        Obtiene posts recientes de Facebook.
        
        Args:
            limit: Número máximo de posts a obtener
            
        Returns:
            Lista de posts de Facebook
        """
        if not self.is_configured or not self.facebook_access_token or not self.facebook_page_id:
            return []
        
        if not REQUESTS_AVAILABLE:
            return []
        
        try:
            url = f"https://graph.facebook.com/v18.0/{self.facebook_page_id}/posts"
            params = {
                "access_token": self.facebook_access_token,
                "fields": "id,message,created_time,shares,likes.summary(true),comments.summary(true)",
                "limit": min(limit, 100),  # Máximo 100 por request
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            posts = []
            
            for post_data in data.get("data", []):
                # Calcular engagement total
                engagement = 0
                if "likes" in post_data:
                    engagement += post_data["likes"].get("summary", {}).get("total_count", 0)
                if "comments" in post_data:
                    engagement += post_data["comments"].get("summary", {}).get("total_count", 0)
                if "shares" in post_data:
                    engagement += post_data.get("shares", {}).get("count", 0)
                
                post = MetaPost(
                    post_id=post_data.get("id", ""),
                    message=post_data.get("message", ""),
                    created_time=post_data.get("created_time", ""),
                    page_id=self.facebook_page_id,
                    engagement_count=engagement,
                    metadata=post_data
                )
                posts.append(post)
            
            print(f"✅ Obtenidos {len(posts)} posts de Facebook")
            return posts
            
        except Exception as e:
            print(f"⚠️ Error obteniendo posts de Facebook: {e}")
            return []
    
    def fetch_instagram_posts(self, limit: int = 50) -> List[MetaPost]:
        """
        Obtiene posts recientes de Instagram.
        
        Args:
            limit: Número máximo de posts a obtener
            
        Returns:
            Lista de posts de Instagram
        """
        if not self.is_configured or not self.instagram_access_token or not self.instagram_business_account_id:
            return []
        
        if not REQUESTS_AVAILABLE:
            return []
        
        try:
            url = f"https://graph.facebook.com/v18.0/{self.instagram_business_account_id}/media"
            params = {
                "access_token": self.instagram_access_token,
                "fields": "id,caption,timestamp,like_count,comments_count",
                "limit": min(limit, 100),
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            posts = []
            
            for post_data in data.get("data", []):
                engagement = (
                    post_data.get("like_count", 0) +
                    post_data.get("comments_count", 0)
                )
                
                post = MetaPost(
                    post_id=post_data.get("id", ""),
                    message=post_data.get("caption", ""),
                    created_time=post_data.get("timestamp", ""),
                    page_id=self.instagram_business_account_id,
                    engagement_count=engagement,
                    metadata=post_data
                )
                posts.append(post)
            
            print(f"✅ Obtenidos {len(posts)} posts de Instagram")
            return posts
            
        except Exception as e:
            print(f"⚠️ Error obteniendo posts de Instagram: {e}")
            return []
    
    def fetch_meta_ads_campaigns(self, limit: int = 50) -> List[MetaAdCampaign]:
        """
        Obtiene campañas recientes de Meta Ads.
        
        Args:
            limit: Número máximo de campañas a obtener
            
        Returns:
            Lista de campañas de Meta Ads
        """
        if not self.is_configured or not self.meta_ads_access_token or not self.meta_ads_account_id:
            return []
        
        if not REQUESTS_AVAILABLE:
            return []
        
        try:
            url = f"https://graph.facebook.com/v18.0/{self.meta_ads_account_id}/campaigns"
            params = {
                "access_token": self.meta_ads_access_token,
                "fields": "id,name,objective,status,adcreatives{body,title,description}",
                "limit": min(limit, 100),
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            campaigns = []
            
            for campaign_data in data.get("data", []):
                # Extraer texto de creativos
                ad_creatives = campaign_data.get("adcreatives", {}).get("data", [])
                creative_text = ""
                creative_description = ""
                
                if ad_creatives:
                    first_creative = ad_creatives[0]
                    creative_text = first_creative.get("title", "") + " " + first_creative.get("body", "")
                    creative_description = first_creative.get("description", "")
                
                campaign = MetaAdCampaign(
                    campaign_id=campaign_data.get("id", ""),
                    name=campaign_data.get("name", ""),
                    objective=campaign_data.get("objective", ""),
                    status=campaign_data.get("status", ""),
                    ad_creative_text=creative_text,
                    ad_creative_description=creative_description,
                    metadata=campaign_data
                )
                campaigns.append(campaign)
            
            print(f"✅ Obtenidas {len(campaigns)} campañas de Meta Ads")
            return campaigns
            
        except Exception as e:
            print(f"⚠️ Error obteniendo campañas de Meta Ads: {e}")
            return []
    
    def extract_knowledge_from_posts(self, posts: List[MetaPost]) -> str:
        """
        Extrae conocimiento de posts para incorporar en el RAG.
        
        Args:
            posts: Lista de posts
            
        Returns:
            Texto con conocimiento extraído
        """
        if not posts:
            return ""
        
        knowledge_parts = []
        
        for post in posts:
            if post.message:
                knowledge_parts.append(f"**Post ({post.created_time[:10]}):** {post.message[:500]}")
        
        return "\n\n".join(knowledge_parts)
    
    def extract_knowledge_from_campaigns(self, campaigns: List[MetaAdCampaign]) -> str:
        """
        Extrae conocimiento de campañas para incorporar en el RAG.
        
        Args:
            campaigns: Lista de campañas
            
        Returns:
            Texto con conocimiento extraído
        """
        if not campaigns:
            return ""
        
        knowledge_parts = []
        
        for campaign in campaigns:
            if campaign.ad_creative_text:
                knowledge_parts.append(
                    f"**Campaña '{campaign.name}' ({campaign.objective}):** {campaign.ad_creative_text[:500]}"
                )
            if campaign.ad_creative_description:
                knowledge_parts.append(f"**Descripción:** {campaign.ad_creative_description[:300]}")
        
        return "\n\n".join(knowledge_parts)
    
    def get_all_knowledge(self) -> Dict[str, str]:
        """
        Obtiene todo el conocimiento de Meta (posts + campañas).
        
        Returns:
            Dict con 'posts_knowledge' y 'campaigns_knowledge'
        """
        if not self.is_configured:
            return {
                "posts_knowledge": "",
                "campaigns_knowledge": ""
            }
        
        # Obtener posts
        facebook_posts = self.fetch_facebook_posts(limit=30)
        instagram_posts = self.fetch_instagram_posts(limit=30)
        all_posts = facebook_posts + instagram_posts
        
        # Obtener campañas
        campaigns = self.fetch_meta_ads_campaigns(limit=30)
        
        return {
            "posts_knowledge": self.extract_knowledge_from_posts(all_posts),
            "campaigns_knowledge": self.extract_knowledge_from_campaigns(campaigns)
        }

