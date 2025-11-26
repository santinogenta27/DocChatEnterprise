"""Context manager for maintaining enterprise context."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from datetime import datetime

from .memory_store import MemoryStore


class ContextManager:
    """Manages context across sessions and queries."""
    
    def __init__(self, memory_store: MemoryStore, config: Any):
        self.memory_store = memory_store
        self.config = config
        self.current_session_id: Optional[str] = None
        self.session_context: Dict[str, Any] = {}
    
    def start_session(self, session_id: Optional[str] = None) -> str:
        """Start a new session."""
        if session_id is None:
            session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        self.current_session_id = session_id
        self.session_context = {
            "session_id": session_id,
            "started_at": datetime.now().isoformat(),
            "queries": [],
            "documents_processed": [],
            "insights": []
        }
        
        return session_id
    
    def add_query(self, query: str, answer: str, sources: List[str], metadata: Optional[Dict] = None):
        """Add a query to the current session."""
        if not self.current_session_id:
            self.start_session()
        
        query_entry = {
            "query": query,
            "answer": answer,
            "sources": sources,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {}
        }
        
        self.session_context["queries"].append(query_entry)
        
        # Also add to persistent memory
        self.memory_store.add_memory(
            query=query,
            answer=answer,
            context=self.session_context,
            sources=sources,
            metadata=metadata
        )
    
    def get_context_for_query(self, query: str) -> Dict[str, Any]:
        """Get enriched context for a query."""
        # Get from memory
        memory_context = self.memory_store.get_context_for_query(query)
        
        # Get from current session
        session_context = {
            "recent_queries": self.session_context.get("queries", [])[-5:],
            "documents_in_session": self.session_context.get("documents_processed", []),
            "session_insights": self.session_context.get("insights", [])
        }
        
        # Combine contexts
        enriched_context = {
            **memory_context,
            **session_context,
            "session_id": self.current_session_id,
            "context_window_size": self.config.context_window_size
        }
        
        return enriched_context
    
    def add_insight(self, insight: str, category: str = "general"):
        """Add an insight to the session."""
        if not self.current_session_id:
            self.start_session()
        
        insight_entry = {
            "insight": insight,
            "category": category,
            "timestamp": datetime.now().isoformat()
        }
        
        self.session_context["insights"].append(insight_entry)
    
    def get_session_summary(self) -> Dict[str, Any]:
        """Get summary of current session."""
        return {
            "session_id": self.current_session_id,
            "queries_count": len(self.session_context.get("queries", [])),
            "documents_count": len(self.session_context.get("documents_processed", [])),
            "insights_count": len(self.session_context.get("insights", [])),
            "started_at": self.session_context.get("started_at"),
            "duration_minutes": self._calculate_duration()
        }
    
    def _calculate_duration(self) -> Optional[float]:
        """Calculate session duration in minutes."""
        started_at = self.session_context.get("started_at")
        if not started_at:
            return None
        
        start = datetime.fromisoformat(started_at)
        now = datetime.now()
        delta = now - start
        return delta.total_seconds() / 60.0



