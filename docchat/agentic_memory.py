"""Memoria persistente para Agentic Workflows.

Implementa memoria a largo plazo, reward signals para RL,
y tracking de decisiones para recursive self-improvement.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime
import sqlite3


@dataclass
class RewardSignal:
    """Señal de recompensa para reinforcement learning."""
    signal_id: str
    workflow_id: str
    agent_id: str
    reward: float  # -1.0 a 1.0
    feedback: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class AgentDecision:
    """Decisión tomada por un agent (para recursive self-improvement)."""
    decision_id: str
    workflow_id: str
    agent_id: str
    input_state: Dict[str, Any]
    decision: Dict[str, Any]
    outcome: Optional[Dict[str, Any]] = None
    success: Optional[bool] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class AgenticMemory:
    """Sistema de memoria persistente para agentic workflows."""
    
    def __init__(self, config: Any):
        self.config = config
        self.memory_dir = config.cache_dir / "agentic_memory"
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        
        # Base de datos SQLite para memoria persistente
        self.db_path = self.memory_dir / "agentic_memory.db"
        self._init_database()
    
    def _init_database(self):
        """Inicializa la base de datos SQLite."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Tabla de sesiones/workflows
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS workflow_sessions (
                session_id TEXT PRIMARY KEY,
                workflow_id TEXT,
                state TEXT,
                created_at TEXT,
                updated_at TEXT
            )
        """)
        
        # Tabla de reward signals
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS reward_signals (
                signal_id TEXT PRIMARY KEY,
                workflow_id TEXT,
                agent_id TEXT,
                reward REAL,
                feedback TEXT,
                context TEXT,
                timestamp TEXT
            )
        """)
        
        # Tabla de decisiones de agents
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agent_decisions (
                decision_id TEXT PRIMARY KEY,
                workflow_id TEXT,
                agent_id TEXT,
                input_state TEXT,
                decision TEXT,
                outcome TEXT,
                success INTEGER,
                timestamp TEXT
            )
        """)
        
        # Índices
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_workflow_id ON reward_signals(workflow_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_agent_id ON reward_signals(agent_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_workflow_decisions ON agent_decisions(workflow_id)")
        
        conn.commit()
        conn.close()
    
    def save_session_state(
        self,
        session_id: str,
        workflow_id: str,
        state: Dict[str, Any],
    ):
        """Guarda el estado de una sesión."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO workflow_sessions
            (session_id, workflow_id, state, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
        """, (
            session_id,
            workflow_id,
            json.dumps(state),
            datetime.now().isoformat(),
            datetime.now().isoformat(),
        ))
        
        conn.commit()
        conn.close()
    
    def load_session_state(
        self,
        session_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Carga el estado de una sesión."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT state FROM workflow_sessions
            WHERE session_id = ?
        """, (session_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return json.loads(row[0])
        return None
    
    def record_reward(
        self,
        workflow_id: str,
        agent_id: str,
        reward: float,
        feedback: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Registra una señal de recompensa."""
        import uuid
        signal_id = str(uuid.uuid4())
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO reward_signals
            (signal_id, workflow_id, agent_id, reward, feedback, context, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            signal_id,
            workflow_id,
            agent_id,
            reward,
            feedback,
            json.dumps(context or {}),
            datetime.now().isoformat(),
        ))
        
        conn.commit()
        conn.close()
        
        return signal_id
    
    def get_agent_rewards(
        self,
        agent_id: str,
        limit: int = 100,
    ) -> List[RewardSignal]:
        """Obtiene reward signals de un agent para aprendizaje."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT signal_id, workflow_id, agent_id, reward, feedback, context, timestamp
            FROM reward_signals
            WHERE agent_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
        """, (agent_id, limit))
        
        rows = cursor.fetchall()
        conn.close()
        
        signals = []
        for row in rows:
            signals.append(RewardSignal(
                signal_id=row[0],
                workflow_id=row[1],
                agent_id=row[2],
                reward=row[3],
                feedback=row[4],
                context=json.loads(row[5]) if row[5] else {},
                timestamp=row[6],
            ))
        
        return signals
    
    def record_decision(
        self,
        workflow_id: str,
        agent_id: str,
        input_state: Dict[str, Any],
        decision: Dict[str, Any],
        outcome: Optional[Dict[str, Any]] = None,
        success: Optional[bool] = None,
    ) -> str:
        """Registra una decisión de un agent (para recursive self-improvement)."""
        import uuid
        decision_id = str(uuid.uuid4())
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO agent_decisions
            (decision_id, workflow_id, agent_id, input_state, decision, outcome, success, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            decision_id,
            workflow_id,
            agent_id,
            json.dumps(input_state),
            json.dumps(decision),
            json.dumps(outcome) if outcome else None,
            1 if success else 0 if success is False else None,
            datetime.now().isoformat(),
        ))
        
        conn.commit()
        conn.close()
        
        return decision_id
    
    def get_successful_patterns(
        self,
        agent_id: str,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Obtiene patrones exitosos de un agent para auto-mejora."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT input_state, decision, outcome
            FROM agent_decisions
            WHERE agent_id = ? AND success = 1
            ORDER BY timestamp DESC
            LIMIT ?
        """, (agent_id, limit))
        
        rows = cursor.fetchall()
        conn.close()
        
        patterns = []
        for row in rows:
            patterns.append({
                "input_state": json.loads(row[0]),
                "decision": json.loads(row[1]),
                "outcome": json.loads(row[2]) if row[2] else None,
            })
        
        return patterns

