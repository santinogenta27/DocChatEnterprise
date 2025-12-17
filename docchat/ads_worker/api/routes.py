"""
FastAPI routes for ADS WORKER
"""
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from fastapi.responses import JSONResponse
from typing import List, Optional, Dict, Any
import os
import uuid
from pathlib import Path

from ..models.schemas import (
    AssetUpload,
    AssetAnalysis,
    CampaignRequest,
    CampaignResponse,
    AdPerformance,
    OptimizationResult
)
from ..services.asset_processor import AssetProcessor
from ..agents.ads_agent import AdsWorkerAgent

router = APIRouter(prefix="/api/ads-worker", tags=["ads-worker"])

# Global agent instance (will be initialized in main mode)
agent_instance: Optional[AdsWorkerAgent] = None


def get_agent() -> AdsWorkerAgent:
    """Dependency to get agent instance"""
    if agent_instance is None:
        raise HTTPException(status_code=500, detail="ADS WORKER agent not initialized")
    return agent_instance


@router.post("/upload-asset", response_model=AssetAnalysis)
async def upload_asset(
    file: Optional[UploadFile] = File(None),
    asset_type: str = Form(...),
    text_content: Optional[str] = Form(None),
    metadata: Optional[str] = Form(None),
    agent: AdsWorkerAgent = Depends(get_agent)
):
    """
    Upload and analyze an asset (image, video, or text)
    
    Returns analysis with labels, objects, style tags, etc.
    """
    from ..models.schemas import AssetType
    import json
    
    try:
        asset_type_enum = AssetType(asset_type)
        
        # Save uploaded file if provided
        file_path = None
        if file:
            storage_path = Path("./assets/uploads")
            storage_path.mkdir(parents=True, exist_ok=True)
            file_path = storage_path / f"{uuid.uuid4()}_{file.filename}"
            with open(file_path, "wb") as f:
                content = await file.read()
                f.write(content)
            file_path = str(file_path)
        
        # Parse metadata
        metadata_dict = {}
        if metadata:
            try:
                metadata_dict = json.loads(metadata)
            except:
                pass
        
        # Process asset
        analysis = agent.asset_processor.process_asset(
            asset_type_enum,
            file_path,
            None,  # file_url
            text_content,
            metadata_dict
        )
        
        return analysis
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing asset: {str(e)}")


@router.get("/campaigns", response_model=List[CampaignResponse])
async def get_campaigns(agent: AdsWorkerAgent = Depends(get_agent)):
    """
    Get all campaigns
    
    Returns list of campaigns with metrics
    """
    # In production, fetch from database
    return []


@router.post("/launch-campaign", response_model=CampaignResponse)
async def launch_campaign(
    campaign_request: CampaignRequest,
    agent: AdsWorkerAgent = Depends(get_agent)
):
    """
    Launch a new campaign
    
    Processes assets, generates creatives, and publishes to Meta/Google
    """
    try:
        # In production, get assets from database using asset_ids
        # For now, return a mock response
        from ..models.schemas import AssetUpload, AssetType
        
        # Mock assets (in production fetch from DB)
        assets = []
        
        # Process and launch
        campaign = agent.process_and_launch_campaign(assets, campaign_request)
        
        return campaign
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error launching campaign: {str(e)}")


@router.get("/campaign/{campaign_id}/metrics", response_model=List[AdPerformance])
async def get_campaign_metrics(
    campaign_id: str,
    agent: AdsWorkerAgent = Depends(get_agent)
):
    """
    Get performance metrics for a campaign
    """
    # In production, fetch from database and APIs
    return []


@router.post("/campaign/{campaign_id}/optimize", response_model=OptimizationResult)
async def optimize_campaign(
    campaign_id: str,
    agent: AdsWorkerAgent = Depends(get_agent)
):
    """
    Optimize a campaign based on performance
    
    Returns optimization actions and recommendations
    """
    try:
        # In production, get platform_campaign_ids from database
        platform_campaign_ids = {}
        
        result = agent.optimize_existing_campaign(campaign_id, platform_campaign_ids)
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error optimizing campaign: {str(e)}")


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "ads-worker",
        "version": "1.0.0"
    }
