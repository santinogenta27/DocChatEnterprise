"""Audit logging for security and compliance."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, asdict


@dataclass
class AuditLogEntry:
    """A single audit log entry."""
    timestamp: str
    event_type: str
    user_id: Optional[str]
    action: str
    resource: str
    result: str
    metadata: Dict[str, Any]
    ip_address: Optional[str] = None
    session_id: Optional[str] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return asdict(self)


class AuditLogger:
    """Audit logger for security and compliance."""
    
    def __init__(self, audit_dir: Path, enabled: bool = True):
        self.audit_dir = Path(audit_dir)
        self.audit_dir.mkdir(parents=True, exist_ok=True)
        self.enabled = enabled
        self.log_file = self.audit_dir / f"audit_{datetime.now().strftime('%Y%m%d')}.jsonl"
    
    def log(
        self,
        event_type: str,
        action: str,
        resource: str,
        result: str = "success",
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        session_id: Optional[str] = None
    ):
        """Log an audit event."""
        if not self.enabled:
            return
        
        entry = AuditLogEntry(
            timestamp=datetime.now().isoformat(),
            event_type=event_type,
            user_id=user_id,
            action=action,
            resource=resource,
            result=result,
            metadata=metadata or {},
            ip_address=ip_address,
            session_id=session_id
        )
        
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(entry.to_dict(), ensure_ascii=False) + '\n')
        except Exception as e:
            print(f"Warning: Failed to write audit log: {e}")
    
    def query_logs(
        self,
        event_type: Optional[str] = None,
        user_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100
    ) -> List[AuditLogEntry]:
        """Query audit logs."""
        if not self.enabled:
            return []
        
        entries = []
        
        # Load all log files in date range
        if start_date:
            start_file = self.audit_dir / f"audit_{start_date.strftime('%Y%m%d')}.jsonl"
        else:
            start_file = self.log_file
        
        if end_date:
            end_file = self.audit_dir / f"audit_{end_date.strftime('%Y%m%d')}.jsonl"
        else:
            end_file = self.log_file
        
        # Read log files
        log_files = sorted(self.audit_dir.glob("audit_*.jsonl"))
        for log_file in log_files:
            if log_file < start_file or log_file > end_file:
                continue
            
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        if not line.strip():
                            continue
                        data = json.loads(line)
                        entry = AuditLogEntry(**data)
                        
                        # Apply filters
                        if event_type and entry.event_type != event_type:
                            continue
                        if user_id and entry.user_id != user_id:
                            continue
                        
                        entries.append(entry)
            except Exception:
                continue
        
        # Sort by timestamp and limit
        entries.sort(key=lambda x: x.timestamp, reverse=True)
        return entries[:limit]
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get audit log statistics."""
        if not self.enabled:
            return {}
        
        entries = []
        for log_file in self.audit_dir.glob("audit_*.jsonl"):
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.strip():
                            entries.append(json.loads(line))
            except Exception:
                continue
        
        if not entries:
            return {"total_entries": 0}
        
        event_types = {}
        actions = {}
        results = {}
        
        for entry in entries:
            event_types[entry.get("event_type", "unknown")] = \
                event_types.get(entry.get("event_type", "unknown"), 0) + 1
            actions[entry.get("action", "unknown")] = \
                actions.get(entry.get("action", "unknown"), 0) + 1
            results[entry.get("result", "unknown")] = \
                results.get(entry.get("result", "unknown"), 0) + 1
        
        return {
            "total_entries": len(entries),
            "event_types": event_types,
            "actions": actions,
            "results": results,
            "oldest_entry": min([e.get("timestamp") for e in entries]) if entries else None,
            "newest_entry": max([e.get("timestamp") for e in entries]) if entries else None
        }



