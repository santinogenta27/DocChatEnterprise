"""Audit logging for Research & Action Agent."""

from __future__ import annotations

import sqlite3
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List


DB_PATH = os.environ.get(
    "RAG_AGENT_AUDIT_DB",
    str(Path.cwd() / "data" / "react_agent_audit.db")
)


def init_audit_db():
    """Initialize the audit database."""
    try:
        # Ensure directory exists
        db_path = Path(DB_PATH)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        
        cur.execute("""
        CREATE TABLE IF NOT EXISTS react_audit (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            query TEXT NOT NULL,
            mode TEXT,
            log_json TEXT,
            final_result TEXT,
            created_at TEXT,
            execution_time_ms INTEGER
        )
        """)
        
        # Create index for faster queries
        cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_created_at ON react_audit(created_at)
        """)
        
        conn.commit()
        conn.close()
        
    except Exception as e:
        print(f"⚠️ Error initializing audit DB: {e}")


def save_audit_log(
    query: str,
    mode: str,
    log: Dict[str, Any],
    final_result: Optional[Dict[str, Any]] = None,
    execution_time_ms: Optional[int] = None
):
    """Save an audit log entry."""
    try:
        init_audit_db()
        
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        
        cur.execute(
            """INSERT INTO react_audit 
               (query, mode, log_json, final_result, created_at, execution_time_ms) 
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                query,
                mode,
                json.dumps(log),
                json.dumps(final_result) if final_result else None,
                datetime.utcnow().isoformat(),
                execution_time_ms
            )
        )
        
        conn.commit()
        conn.close()
        
    except Exception as e:
        print(f"⚠️ Error saving audit log: {e}")


class AuditLogger:
    """Audit logger for Research & Action Agent."""
    
    def __init__(self):
        init_audit_db()
    
    def log(
        self,
        query: str,
        mode: str,
        log: Dict[str, Any],
        final_result: Optional[Dict[str, Any]] = None,
        execution_time_ms: Optional[int] = None
    ):
        """Log an audit entry."""
        save_audit_log(query, mode, log, final_result, execution_time_ms)
    
    def get_recent_logs(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent audit logs."""
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            
            cur.execute(
                """SELECT * FROM react_audit 
                   ORDER BY created_at DESC 
                   LIMIT ?""",
                (limit,)
            )
            
            rows = cur.fetchall()
            conn.close()
            
            return [dict(row) for row in rows]
            
        except Exception as e:
            print(f"⚠️ Error getting audit logs: {e}")
            return []

