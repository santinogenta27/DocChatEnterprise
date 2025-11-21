"""Persistent memory storage for enterprise knowledge."""

from __future__ import annotations

import json
import pickle
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, asdict
import hashlib


@dataclass
class MemoryEntry:
    """A single memory entry."""
    id: str
    timestamp: str
    query: str
    answer: str
    context: Dict[str, Any]
    sources: List[str]
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> MemoryEntry:
        """Create from dictionary."""
        return cls(**data)


class MemoryStore:
    """Persistent memory store for enterprise knowledge."""
    
    def __init__(self, memory_dir: Path, retention_days: int = 365):
        self.memory_dir = Path(memory_dir)
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        self.retention_days = retention_days
        self.memories_file = self.memory_dir / "memories.json"
        self.index_file = self.memory_dir / "memory_index.pkl"
        self._memories: List[MemoryEntry] = []
        self._index: Dict[str, List[str]] = {}  # query_hash -> [memory_ids]
        self._load()
    
    def _load(self):
        """Load memories from disk."""
        if self.memories_file.exists():
            try:
                with open(self.memories_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self._memories = [MemoryEntry.from_dict(m) for m in data.get("memories", [])]
            except Exception:
                self._memories = []
        
        if self.index_file.exists():
            try:
                with open(self.index_file, 'rb') as f:
                    self._index = pickle.load(f)
            except Exception:
                self._index = {}
        
        # Clean old memories
        self._cleanup_old_memories()
    
    def _save(self):
        """Save memories to disk."""
        try:
            data = {
                "memories": [m.to_dict() for m in self._memories],
                "last_updated": datetime.now().isoformat()
            }
            with open(self.memories_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            with open(self.index_file, 'wb') as f:
                pickle.dump(self._index, f)
        except Exception as e:
            print(f"Warning: Failed to save memory: {e}")
    
    def _cleanup_old_memories(self):
        """Remove memories older than retention period."""
        cutoff = datetime.now() - timedelta(days=self.retention_days)
        original_count = len(self._memories)
        
        self._memories = [
            m for m in self._memories
            if datetime.fromisoformat(m.timestamp) > cutoff
        ]
        
        if len(self._memories) < original_count:
            # Rebuild index
            self._rebuild_index()
            self._save()
    
    def _rebuild_index(self):
        """Rebuild the search index."""
        self._index = {}
        for memory in self._memories:
            query_hash = self._hash_query(memory.query)
            if query_hash not in self._index:
                self._index[query_hash] = []
            self._index[query_hash].append(memory.id)
    
    def _hash_query(self, query: str) -> str:
        """Create hash of query for indexing."""
        normalized = query.lower().strip()
        return hashlib.md5(normalized.encode()).hexdigest()
    
    def add_memory(
        self,
        query: str,
        answer: str,
        context: Dict[str, Any],
        sources: List[str],
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Add a new memory entry."""
        memory_id = f"mem_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{hashlib.md5(query.encode()).hexdigest()[:8]}"
        
        entry = MemoryEntry(
            id=memory_id,
            timestamp=datetime.now().isoformat(),
            query=query,
            answer=answer,
            context=context,
            sources=sources,
            metadata=metadata or {}
        )
        
        self._memories.append(entry)
        
        # Update index
        query_hash = self._hash_query(query)
        if query_hash not in self._index:
            self._index[query_hash] = []
        self._index[query_hash].append(memory_id)
        
        self._save()
        return memory_id
    
    def search_memories(
        self,
        query: str,
        limit: int = 5,
        min_similarity: float = 0.0
    ) -> List[MemoryEntry]:
        """Search for similar memories."""
        query_hash = self._hash_query(query)
        
        # Exact match first
        if query_hash in self._index:
            memory_ids = self._index[query_hash]
            memories = [m for m in self._memories if m.id in memory_ids]
            if memories:
                return memories[:limit]
        
        # Fuzzy search - simple keyword matching
        query_lower = query.lower()
        query_words = set(query_lower.split())
        
        scored_memories = []
        for memory in self._memories:
            memory_text = f"{memory.query} {memory.answer}".lower()
            memory_words = set(memory_text.split())
            
            # Simple Jaccard similarity
            intersection = len(query_words & memory_words)
            union = len(query_words | memory_words)
            similarity = intersection / union if union > 0 else 0.0
            
            if similarity >= min_similarity:
                scored_memories.append((similarity, memory))
        
        # Sort by similarity and return top results
        scored_memories.sort(key=lambda x: x[0], reverse=True)
        return [m for _, m in scored_memories[:limit]]
    
    def get_context_for_query(self, query: str, max_context: int = 3) -> Dict[str, Any]:
        """Get relevant context from memory for a query."""
        memories = self.search_memories(query, limit=max_context)
        
        context = {
            "previous_queries": [m.query for m in memories],
            "previous_answers": [m.answer for m in memories],
            "related_sources": list(set([s for m in memories for s in m.sources])),
            "memory_count": len(memories)
        }
        
        return context
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get memory store statistics."""
        return {
            "total_memories": len(self._memories),
            "indexed_queries": len(self._index),
            "oldest_memory": min([m.timestamp for m in self._memories]) if self._memories else None,
            "newest_memory": max([m.timestamp for m in self._memories]) if self._memories else None,
            "retention_days": self.retention_days
        }



