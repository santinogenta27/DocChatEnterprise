"""
Knowledge Base Search Tool - RAG-based search
Production-ready with optimized retrieval
"""
from typing import Dict, Any, List, Optional
import logging

from ..utils.logging import setup_logger

logger = setup_logger("customer_service_24_7.tools.kb")


class KBSearchTool:
    """Tool for searching knowledge base using RAG"""
    
    def __init__(self, knowledge_base):
        """
        Initialize KB Search Tool
        
        Args:
            knowledge_base: AdvancedKnowledgeBase instance
        """
        self.kb = knowledge_base
        logger.info("✅ KB Search Tool inicializado")
    
    def search(self, query: str, k: int = 3) -> List[Dict[str, Any]]:
        """
        Search knowledge base
        
        Args:
            query: Search query
            k: Number of results
            
        Returns:
            List of relevant documents
        """
        logger.info(f"🔍 Buscando en KB: '{query}'")
        results = self.kb.search(query, k=k)
        return results
    
    def get_langchain_tool(self):
        """Get LangChain tool wrapper"""
        from langchain.tools import tool
        
        @tool
        def search_knowledge_base_tool(query: str) -> str:
            """
            Search the knowledge base for relevant information about policies, FAQs, or procedures. ALWAYS use this tool FIRST before taking actions to ensure you follow correct policies.
            
            Args:
                query: The search query (required)
                
            Returns:
                JSON string with relevant documents from the knowledge base containing policies, procedures, and FAQs
            """
            results = self.search(query)
            import json
            return json.dumps(results, indent=2)
        
        return search_knowledge_base_tool
