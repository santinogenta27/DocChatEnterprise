"""RAG query tool for Research & Action Agent - integrates with DocChat RAG system."""

from __future__ import annotations

import json
import time
import uuid
from typing import List, Dict, Any, Optional
from langchain.tools import tool
from .base_tool import ToolResponse


@tool
def rag_query_tool(query: str, top_k: int = 8) -> str:
    """
    Query DocChat's RAG system to search internal company documents.
    
    This tool searches the document base using BM25 + embeddings + hierarchical chunking.
    
    Args:
        query: The search query string
        top_k: Maximum number of documents to return (default: 8)
    
    Returns:
        JSON string with standard contract: {status, data, meta, error}
    """
    start_time = time.time()
    request_id = str(uuid.uuid4())
    
    try:
        # Import here to avoid circular dependencies
        from docchat.semantic_data_engine import SemanticDataEngine
        from docchat.config import AppConfig
        
        # Get config and initialize engine if needed
        config = AppConfig()
        
        # Try to get the global semantic engine if available
        # This will be injected by the agent or accessed from app.py
        global_semantic_engine = None
        
        # Try to access from app.py's global semantic_engine
        try:
            import sys
            # Try to get from main module if available
            main_module = sys.modules.get('__main__')
            if main_module and hasattr(main_module, 'semantic_engine'):
                global_semantic_engine = main_module.semantic_engine
        except:
            pass
        
        # Try to access from module-level cache if available
        if global_semantic_engine is None:
            try:
                import docchat.semantic_data_engine as sde_module
                if hasattr(sde_module, '_global_engine'):
                    global_semantic_engine = sde_module._global_engine
            except:
                pass
        
        # If no global engine, create a temporary one
        if global_semantic_engine is None:
            try:
                global_semantic_engine = SemanticDataEngine(config)
            except Exception as e:
                return json.dumps([{
                    "doc_id": "error",
                    "title": "RAG Engine Error",
                    "snippet": f"Could not initialize RAG engine: {str(e)}",
                    "score": 0.0,
                    "metadata": {}
                }])
        
        # Perform hybrid search
        try:
            results = global_semantic_engine.hybrid_search(
                query=query,
                k=top_k,
                filters=None
            )
            
            # Format results
            formatted_results = []
            low_confidence = False
            
            for idx, doc in enumerate(results):
                score = doc.get("score", 1.0 - (idx * 0.05))
                
                # Check score threshold
                if score < 0.2:
                    low_confidence = True
                
                formatted_results.append({
                    "doc_id": doc.get("doc_id", f"doc_{idx}"),
                    "title": doc.get("title", doc.get("source", "Unknown Document")),
                    "chunk_id": doc.get("chunk_id", ""),
                    "text_snippet": doc.get("content", doc.get("preview", ""))[:500],
                    "score": score,
                    "metadata": doc.get("metadata", {})
                })
            
            if formatted_results:
                return ToolResponse(
                    status="ok",
                    data={
                        "results": formatted_results,
                        "low_confidence": low_confidence
                    },
                    tool_name="search_docs",
                    duration_ms=int((time.time() - start_time) * 1000),
                    request_id=request_id,
                    source="internal_rag"
                ).to_json()
            else:
                return ToolResponse(
                    status="ok",
                    data={
                        "results": [],
                        "low_confidence": True
                    },
                    tool_name="search_docs",
                    duration_ms=int((time.time() - start_time) * 1000),
                    request_id=request_id,
                    source="internal_rag"
                ).to_json()
                
        except Exception as e:
            return ToolResponse(
                status="error",
                tool_name="search_docs",
                request_id=request_id,
                source="internal_rag",
                error={
                    "code": "rag_search_error",
                    "message": f"Error during RAG search: {str(e)}",
                    "details": {}
                }
            ).to_json()
            
    except Exception as e:
        # Fallback if RAG system is not available
        return ToolResponse(
            status="error",
            tool_name="search_docs",
            request_id=request_id,
            source="internal_rag",
            error={
                "code": "rag_unavailable",
                "message": f"RAG system could not be accessed. Error: {str(e)}",
                "details": {"query": query}
            }
        ).to_json()

