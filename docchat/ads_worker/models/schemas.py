"""
Pydantic schemas for ADS WORKER
"""
from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class AssetType(str, Enum):
    """Types of assets that can be uploaded"""
    IMAGE = "image"
    VIDEO = "video"
    TEXT = "text"


class CampaignObjective(str, Enum):
    """Campaign objectives"""
    CONVERSIONS = "CONVERSIONS"
    TRAFFIC = "TRAFFIC"
    ENGAGEMENT = "ENGAGEMENT"
    AWARENESS = "AWARENESS"
    LEAD_GENERATION = "LEAD_GENERATION"
    SALES = "SALES"


class Platform(str, Enum):
    """Advertising platforms"""
    META = "meta"
    GOOGLE = "google"
    BOTH = "both"


class AssetUpload(BaseModel):
    """Schema for asset upload request"""
    asset_type: AssetType
    file_path: Optional[str] = None
    file_url: Optional[str] = None
    text_content: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)
    
    class Config:
        json_schema_extra = {
            "example": {
                "asset_type": "image",
                "file_path": "/uploads/image.jpg",
                "metadata": {
                    "product_name": "Product X",
                    "category": "Electronics"
                }
            }
        }


class AssetAnalysis(BaseModel):
    """Schema for asset analysis results"""
    asset_id: str
    asset_type: AssetType
    analysis_timestamp: datetime = Field(default_factory=datetime.now)
    
    # Image/Video analysis
    labels: List[str] = Field(default_factory=list)
    objects_detected: List[Dict[str, Any]] = Field(default_factory=list)
    dominant_colors: List[str] = Field(default_factory=list)
    style_tags: List[str] = Field(default_factory=list)
    emotion_tags: List[str] = Field(default_factory=list)
    
    # Video specific
    duration: Optional[float] = None
    key_frames: List[str] = Field(default_factory=list)  # URLs to key frames
    transcript: Optional[str] = None  # Audio transcription
    
    # Text analysis
    sentiment: Optional[str] = None
    keywords: List[str] = Field(default_factory=list)
    topics: List[str] = Field(default_factory=list)
    
    # Metadata
    resolution: Optional[Dict[str, int]] = None
    file_size: Optional[int] = None
    format: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "asset_id": "asset_123",
                "asset_type": "image",
                "labels": ["product", "electronics", "modern"],
                "objects_detected": [{"name": "smartphone", "confidence": 0.95}],
                "dominant_colors": ["#FFFFFF", "#000000"],
                "style_tags": ["minimalist", "professional"]
            }
        }


class CreativeGeneration(BaseModel):
    """Schema for generated creative"""
    creative_id: str
    asset_id: str
    creative_type: Literal["copy", "visual", "video"]
    
    # Copy generation
    headline: Optional[str] = None
    description: Optional[str] = None
    cta: Optional[str] = None
    tone: Optional[str] = None
    
    # Visual generation
    visual_url: Optional[str] = None
    format: Optional[str] = None  # "1:1", "4:5", "9:16", etc.
    
    # Video generation
    video_url: Optional[str] = None
    video_duration: Optional[float] = None
    
    # Metadata
    generation_params: Dict[str, Any] = Field(default_factory=dict)
    performance_score: Optional[float] = None  # Predicted performance
    
    class Config:
        json_schema_extra = {
            "example": {
                "creative_id": "creative_123",
                "asset_id": "asset_123",
                "creative_type": "copy",
                "headline": "Discover the Future of Technology",
                "description": "Experience innovation like never before",
                "cta": "Shop Now",
                "tone": "professional"
            }
        }


class CampaignRequest(BaseModel):
    """Schema for campaign creation request"""
    name: str
    objective: CampaignObjective
    budget_daily: float = Field(gt=0, description="Daily budget in USD")
    budget_total: Optional[float] = Field(None, gt=0, description="Total budget in USD")
    
    # Assets to use
    asset_ids: List[str] = Field(min_items=1)
    
    # Platforms
    platforms: Platform = Platform.BOTH
    
    # Targeting (optional, will use AI if not provided)
    target_audience: Optional[Dict[str, Any]] = None
    demographics: Optional[Dict[str, Any]] = None
    interests: Optional[List[str]] = None
    
    # Campaign settings
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    
    # Optimization preferences
    optimization_goal: Literal["conversions", "ctr", "roas", "cpa"] = "conversions"
    auto_optimize: bool = True
    
    # Publication settings - CRÍTICO para publicación autónoma
    auto_activate: bool = Field(
        default=True, 
        description="Activar campaña automáticamente después de crearla (como Meta Ads Manager)"
    )

    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "Summer Sale Campaign",
                "objective": "CONVERSIONS",
                "budget_daily": 50.0,
                "asset_ids": ["asset_123", "asset_456"],
                "platforms": "both",
                "optimization_goal": "conversions",
                "auto_optimize": True
            }
        }


class CampaignResponse(BaseModel):
    """Schema for campaign response"""
    campaign_id: str
    name: str
    status: str
    platforms: List[str]
    
    # Campaign details
    budget_daily: float
    budget_spent: float = 0.0
    budget_remaining: float
    
    # Performance metrics
    impressions: int = 0
    clicks: int = 0
    conversions: int = 0
    ctr: float = 0.0
    cpc: float = 0.0
    cpa: float = 0.0
    roas: float = 0.0
    
    # Ads created
    ads_count: int = 0
    active_ads: int = 0
    
    # Timestamps
    created_at: datetime
    updated_at: datetime
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    
    # Links to platform campaigns
    platform_campaign_ids: Dict[str, str] = Field(default_factory=dict)
    
    class Config:
        json_schema_extra = {
            "example": {
                "campaign_id": "campaign_123",
                "name": "Summer Sale Campaign",
                "status": "active",
                "platforms": ["meta", "google"],
                "budget_daily": 50.0,
                "budget_spent": 125.50,
                "budget_remaining": 374.50,
                "impressions": 50000,
                "clicks": 2500,
                "conversions": 125,
                "ctr": 0.05,
                "cpc": 0.50,
                "cpa": 10.04,
                "roas": 4.5
            }
        }


class AdPerformance(BaseModel):
    """Schema for individual ad performance"""
    ad_id: str
    campaign_id: str
    platform: str
    creative_id: str
    
    # Metrics
    impressions: int = 0
    clicks: int = 0
    conversions: int = 0
    spend: float = 0.0
    
    # Calculated metrics
    ctr: float = 0.0
    cpc: float = 0.0
    cpa: float = 0.0
    roas: float = 0.0
    
    # Status
    status: str = "active"  # active, paused, archived
    
    # Timestamps
    created_at: datetime
    updated_at: datetime
    last_performance_update: datetime
    
    class Config:
        json_schema_extra = {
            "example": {
                "ad_id": "ad_123",
                "campaign_id": "campaign_123",
                "platform": "meta",
                "creative_id": "creative_123",
                "impressions": 10000,
                "clicks": 500,
                "conversions": 25,
                "spend": 250.0,
                "ctr": 0.05,
                "cpc": 0.50,
                "cpa": 10.0,
                "roas": 5.0,
                "status": "active"
            }
        }


class OptimizationResult(BaseModel):
    """Schema for optimization results"""
    optimization_id: str
    campaign_id: str
    optimization_timestamp: datetime = Field(default_factory=datetime.now)
    
    # Actions taken
    ads_paused: List[str] = Field(default_factory=list)
    ads_scaled: List[str] = Field(default_factory=list)
    budget_reallocated: Dict[str, float] = Field(default_factory=dict)
    
    # Performance changes
    performance_improvement: Dict[str, float] = Field(default_factory=dict)
    
    # Recommendations
    recommendations: List[str] = Field(default_factory=list)
    
    class Config:
        json_schema_extra = {
            "example": {
                "optimization_id": "opt_123",
                "campaign_id": "campaign_123",
                "ads_paused": ["ad_456", "ad_789"],
                "ads_scaled": ["ad_123"],
                "budget_reallocated": {"ad_123": 25.0},
                "performance_improvement": {
                    "ctr": 0.02,
                    "cpa": -2.5
                },
                "recommendations": [
                    "Scale ad_123 budget by 50%",
                    "Pause underperforming ads"
                ]
            }
        }



















