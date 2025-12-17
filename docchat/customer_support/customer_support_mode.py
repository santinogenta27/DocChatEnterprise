"""
Customer Support Manager Mode
Main integration mode for the Customer Support Manager system
"""
from typing import Dict, Any, Optional
import os
from pathlib import Path
import logging

from .agents.support_agent import SupportAgent
from .utils.logging import setup_logger

logger = setup_logger("customer_support.mode")


class CustomerSupportMode:
    """Customer Support Manager - Autonomous Resolution Agent"""
    
    def __init__(self, config, provider: str = "grok"):
        """
        Initialize Customer Support Manager
        
        Args:
            config: Application config
            provider: LLM provider (grok, openai, etc.)
        """
        # Get API keys
        grok_api_key = os.getenv("GROK_API_KEY") or os.getenv("XAI_API_KEY")
        openai_api_key = os.getenv("OPENAI_API_KEY")
        
        # Storage paths
        storage_path = Path(getattr(config, "memory_dir", "./data")) / "customer_support"
        storage_path.mkdir(parents=True, exist_ok=True)
        
        kb_path = storage_path / "knowledge_base"
        kb_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize agent
        try:
            self.agent = SupportAgent(
                grok_api_key=grok_api_key,
                openai_api_key=openai_api_key,
                provider=provider,
                kb_path=str(kb_path),
                storage_path=str(storage_path)
            )
            
            logger.info("✅ Customer Support Manager Mode inicializado")
            logger.info(f"   - Provider: {provider}")
            logger.info(f"   - RAG: ✅")
            logger.info(f"   - Tools: ✅")
            logger.info(f"   - LangGraph: ✅")
            
        except Exception as e:
            logger.error(f"⚠️ Error inicializando Customer Support Manager: {e}")
            self.agent = None
    
    def get_api_router(self):
        """Get FastAPI router for integration"""
        # Set global mode instance for API
        from .api import routes
        routes.mode_instance = self
        return routes.router
    
    def get_gradio_interface(self):
        """Get Gradio interface for embedding"""
        if not self.agent:
            raise ValueError("Customer Support Manager agent not initialized")
        return self.agent.get_gradio_interface()
