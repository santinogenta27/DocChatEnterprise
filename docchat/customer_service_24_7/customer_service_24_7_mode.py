"""
Customer Service 24/7 Mode
Main integration mode for the Customer Service 24/7 system
Production-ready autonomous resolution agent
"""
from typing import Dict, Any, Optional
import os
from pathlib import Path
import logging

from .agents.autonomous_agent import AutonomousResolutionAgent
from .api.routes import router
from .utils.logging import setup_logger

logger = setup_logger("customer_service_24_7.mode")


class CustomerService247Mode:
    """Customer Service 24/7 - Autonomous Resolution Agent"""
    
    def __init__(self, config, provider: str = "grok"):
        """
        Initialize Customer Service 24/7
        
        Args:
            config: Application config
            provider: LLM provider (grok, openai)
        """
        # Get API keys
        grok_api_key = os.getenv("GROK_API_KEY") or os.getenv("XAI_API_KEY")
        openai_api_key = os.getenv("OPENAI_API_KEY")
        
        # Storage paths
        storage_path = Path(getattr(config, "memory_dir", "./data")) / "customer_service_24_7"
        storage_path.mkdir(parents=True, exist_ok=True)
        
        kb_path = storage_path / "knowledge_base"
        kb_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize agent
        try:
            self.agent = AutonomousResolutionAgent(
                grok_api_key=grok_api_key,
                openai_api_key=openai_api_key,
                provider=provider,
                kb_path=str(kb_path),
                storage_path=str(storage_path)
            )
            
            logger.info("✅ Customer Service 24/7 Mode inicializado")
            logger.info(f"   - Provider: {provider}")
            logger.info(f"   - RAG: ✅ (FAISS/ChromaDB)")
            logger.info(f"   - LangGraph: ✅ (Stateful workflows)")
            logger.info(f"   - Tools: ✅ (4 tools)")
            logger.info(f"   - Resolution Rate Target: 70-85%")
            
        except Exception as e:
            logger.error(f"⚠️ Error inicializando Customer Service 24/7: {e}")
            self.agent = None
    
    def get_api_router(self):
        """Get FastAPI router for integration"""
        from .api import routes
        routes.mode_instance = self
        return routes.router
    
    def get_gradio_interface(self):
        """Get Gradio interface for embedding"""
        if not self.agent:
            raise ValueError("Customer Service 24/7 agent not initialized")
        return self.agent.get_gradio_interface()
