"""
FastAPI routes for Customer Support Manager
"""
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from typing import Dict, Any, Optional
import logging

from ..utils.logging import setup_logger

logger = setup_logger("customer_support.api")

router = APIRouter(prefix="/api/customer-support", tags=["customer-support"])

# Global agent instance (will be set from CustomerSupportMode)
agent_instance = None
mode_instance = None


def get_agent():
    """Dependency to get agent instance"""
    global agent_instance, mode_instance
    if mode_instance is None:
        raise HTTPException(status_code=503, detail="Customer Support Manager mode not initialized")
    if mode_instance.agent is None:
        raise HTTPException(status_code=503, detail="Customer Support Manager agent not initialized")
    return mode_instance.agent


@router.post("/query")
async def process_query(
    query: str,
    session_id: Optional[str] = None,
    customer_info: Optional[Dict[str, Any]] = None,
    agent = Depends(get_agent)
):
    """
    Process a customer support query
    
    Args:
        query: Customer query
        session_id: Optional session ID for conversation history
        customer_info: Optional customer information
        
    Returns:
        Agent response
    """
    try:
        logger.info(f"📥 Query recibida: '{query[:50]}...'")
        result = agent.process_query(query, session_id, customer_info)
        logger.info(f"✅ Query procesada")
        return result
    except Exception as e:
        logger.error(f"Error procesando query: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing query: {str(e)}")


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "customer-support-manager",
        "version": "1.0.0"
    }













