"""
FastAPI routes for ADS WORKER
Production-ready with validation and error handling
"""
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends, Header
from fastapi.responses import JSONResponse
from typing import List, Optional, Dict, Any
import os
import uuid
import logging
from pathlib import Path

from datetime import datetime
from ..models.schemas import (
    AssetUpload,
    AssetAnalysis,
    CampaignRequest,
    CampaignResponse,
    AdPerformance,
    OptimizationResult,
    AssetType
)
from ..agents.ads_agent import AdsWorkerAgent
from ..utils.logging import setup_logger

logger = setup_logger("ads_worker.api")

router = APIRouter(prefix="/api/ads-worker", tags=["ads-worker"])

# Global agent instance (will be initialized in main mode)
agent_instance: Optional[AdsWorkerAgent] = None
mode_instance = None  # Will be set from AdsWorkerMode


def get_agent() -> AdsWorkerAgent:
    """Dependency to get agent instance"""
    if agent_instance is None:
        raise HTTPException(status_code=503, detail="ADS WORKER agent not initialized")
    return agent_instance


def get_mode():
    """Dependency to get mode instance"""
    global mode_instance
    if mode_instance is None:
        raise HTTPException(status_code=503, detail="ADS WORKER mode not initialized")
    return mode_instance


def get_user_id(x_user_id: Optional[str] = Header(None)) -> str:
    """Get user ID from header or use default"""
    return x_user_id or "default"


@router.post("/upload-asset", response_model=AssetAnalysis)
async def upload_asset(
    file: Optional[UploadFile] = File(None),
    asset_type: str = Form(...),
    text_content: Optional[str] = Form(None),
    metadata: Optional[str] = Form(None),
    agent: AdsWorkerAgent = Depends(get_agent),
    mode = Depends(get_mode),
    user_id: str = Depends(get_user_id)
):
    """
    Upload and analyze an asset (image, video, or text)
    
    Returns analysis with labels, objects, style tags, etc.
    """
    import json
    
    try:
        # Validate asset type
        try:
            asset_type_enum = AssetType(asset_type)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid asset_type: {asset_type}. Must be: image, video, or text")
        
        # Validate input
        if asset_type_enum == AssetType.TEXT and not text_content:
            raise HTTPException(status_code=400, detail="text_content is required for text assets")
        
        if asset_type_enum != AssetType.TEXT and not file:
            raise HTTPException(status_code=400, detail="file is required for image/video assets")
        
        logger.info(f"📤 Upload de asset: tipo={asset_type}, usuario={user_id}")
        
        # Save uploaded file if provided
        file_path = None
        if file:
            # Validate file size (max 100MB)
            content = await file.read()
            if len(content) > 100 * 1024 * 1024:
                raise HTTPException(status_code=400, detail="File size exceeds 100MB limit")
            
            storage_path = Path("./assets/uploads")
            storage_path.mkdir(parents=True, exist_ok=True)
            file_path = storage_path / f"{uuid.uuid4()}_{file.filename}"
            file_path.write_bytes(content)
            file_path = str(file_path)
            logger.info(f"✅ Archivo guardado: {file_path}")
        
        # Parse metadata
        metadata_dict = {}
        if metadata:
            try:
                metadata_dict = json.loads(metadata)
            except json.JSONDecodeError:
                logger.warning(f"Metadata inválido, ignorando: {metadata}")
        
        # Process asset using mode (which includes database)
        asset_upload = AssetUpload(
            asset_type=asset_type_enum,
            file_path=file_path,
            file_url=None,
            text_content=text_content,
            metadata=metadata_dict
        )
        
        analyses = mode.process_assets([asset_upload], user_id=user_id)
        
        if not analyses:
            raise HTTPException(status_code=500, detail="Failed to process asset")
        
        # Return first analysis
        analysis_dict = analyses[0]
        from ..models.schemas import AssetAnalysis
        analysis = AssetAnalysis(**analysis_dict)
        
        logger.info(f"✅ Asset procesado: {analysis.asset_id}")
        return analysis
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error procesando asset: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error processing asset: {str(e)}")


@router.get("/campaigns", response_model=List[CampaignResponse])
async def get_campaigns(
    mode = Depends(get_mode),
    user_id: str = Depends(get_user_id)
):
    """
    Get all campaigns for the user
    
    Returns list of campaigns with metrics
    """
    try:
        # In production, fetch from database filtered by user_id
        # For now, return empty list (database query not fully implemented)
        logger.info(f"📋 Obteniendo campañas para usuario: {user_id}")
        return []
    except Exception as e:
        logger.error(f"Error obteniendo campañas: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching campaigns: {str(e)}")


@router.post("/launch-campaign", response_model=CampaignResponse)
async def launch_campaign(
    campaign_request: CampaignRequest,
    mode = Depends(get_mode),
    user_id: str = Depends(get_user_id)
):
    """
    Launch a new campaign
    
    Processes assets, generates creatives, and publishes to Meta/Google
    """
    try:
        # Validate campaign request
        if not campaign_request.asset_ids:
            raise HTTPException(status_code=400, detail="asset_ids cannot be empty")
        
        if campaign_request.budget_daily <= 0:
            raise HTTPException(status_code=400, detail="budget_daily must be greater than 0")
        
        logger.info(f"🚀 Lanzando campaña: {campaign_request.name} para usuario: {user_id}")
        
        # Launch campaign using mode (which includes database)
        campaign = mode.launch_campaign(campaign_request, user_id=user_id)
        
        logger.info(f"✅ Campaña lanzada exitosamente: {campaign.campaign_id}")
        return campaign
        
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Error de validación: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error lanzando campaña: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error launching campaign: {str(e)}")


@router.get("/campaign/{campaign_id}/metrics", response_model=List[AdPerformance])
async def get_campaign_metrics(
    campaign_id: str,
    hours: int = 24,
    mode = Depends(get_mode)
):
    """
    Get performance metrics for a campaign
    
    Args:
        campaign_id: Campaign ID
        hours: Number of hours to look back (default: 24)
    """
    try:
        logger.info(f"📊 Obteniendo métricas para campaña: {campaign_id} (últimas {hours}h)")
        
        # Get metrics from database
        metrics_data = mode.get_campaign_metrics(campaign_id, hours=hours)
        
        # Convert to AdPerformance objects
        performances = []
        for m in metrics_data:
            perf = AdPerformance(
                ad_id=m["ad_id"],
                campaign_id=campaign_id,
                platform=m["platform"],
                creative_id="",  # Will be set if available
                impressions=m.get("impressions", 0),
                clicks=m.get("clicks", 0),
                conversions=m.get("conversions", 0),
                spend=m.get("spend", 0.0),
                ctr=m.get("ctr", 0.0),
                cpc=m.get("cpc", 0.0),
                cpa=m.get("cpa", 0.0),
                roas=m.get("roas", 0.0),
                status="active",
                created_at=datetime.fromisoformat(m["timestamp"]) if m.get("timestamp") else datetime.now(),
                updated_at=datetime.fromisoformat(m["timestamp"]) if m.get("timestamp") else datetime.now(),
                last_performance_update=datetime.fromisoformat(m["timestamp"]) if m.get("timestamp") else datetime.now()
            )
            performances.append(perf)
        
        logger.info(f"✅ {len(performances)} métricas obtenidas")
        return performances
        
    except Exception as e:
        logger.error(f"Error obteniendo métricas: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching metrics: {str(e)}")


@router.post("/campaign/{campaign_id}/optimize", response_model=OptimizationResult)
async def optimize_campaign(
    campaign_id: str,
    mode = Depends(get_mode)
):
    """
    Optimize a campaign based on performance
    
    Returns optimization actions and recommendations
    """
    try:
        logger.info(f"🔧 Optimizando campaña: {campaign_id}")
        
        # Optimize using mode (which handles database)
        result = mode.optimize_campaign(campaign_id)
        
        logger.info(f"✅ Optimización completada: {result.optimization_id}")
        return result
        
    except ValueError as e:
        logger.error(f"Error de validación: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error optimizando campaña: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error optimizing campaign: {str(e)}")


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "ads-worker",
        "version": "1.0.0"
    }
