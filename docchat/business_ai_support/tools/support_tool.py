from __future__ import annotations

from typing import Dict, Any, List, Optional
from datetime import datetime
import uuid

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False


class SupportTool:
    """Wrapper de soporte/tickets con persistencia en PostgreSQL.
    
    Características:
    - Tickets persistentes en PostgreSQL
    - Estados: open, in_progress, closed, escalated
    - Escalación automática basada en reglas
    - Historial completo de tickets
    """

    def __init__(self, database_url: Optional[str] = None, pool=None) -> None:
        """Inicializa SupportTool con PostgreSQL opcional.
        
        Args:
            database_url: URL de conexión PostgreSQL (opcional)
            pool: Pool de conexiones PostgreSQL (opcional)
        """
        self._tickets: Dict[str, Dict[str, Any]] = {}  # Fallback en memoria
        self.use_postgresql = False
        self.database_url = database_url
        self.pool = pool
        
        if database_url and pool and PSYCOPG2_AVAILABLE:
            self.use_postgresql = True
            print("✅ SupportTool usando PostgreSQL para persistencia de tickets")
        else:
            print("⚠️ SupportTool usando almacenamiento en memoria (configura PostgreSQL para persistencia)")

    def create_ticket(
        self, 
        session_id: str, 
        subject: str, 
        description: str, 
        priority: str = "normal",
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Crea un nuevo ticket de soporte."""
        ticket_id = f"TICKET-{uuid.uuid4().hex[:12].upper()}"
        now = datetime.now().isoformat()
        
        ticket = {
            "ticket_id": ticket_id,
            "session_id": session_id,
            "user_id": user_id or session_id,
            "subject": subject,
            "description": description,
            "priority": priority,
            "status": "open",
            "escalated": False,
            "escalation_reason": None,
            "assigned_to": None,
            "resolution": None,
            "created_at": now,
            "updated_at": now,
            "closed_at": None,
        }
        
        if self.use_postgresql:
            try:
                conn = self.pool.getconn()
                try:
                    cur = conn.cursor()
                    cur.execute("""
                        INSERT INTO support_tickets 
                        (ticket_id, session_id, user_id, subject, description, priority, status, escalated, created_at, updated_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        ticket_id, session_id, user_id or session_id, subject, description,
                        priority, "open", False, now, now
                    ))
                    conn.commit()
                    print(f"✅ Ticket {ticket_id} creado en PostgreSQL")
                finally:
                    self.pool.putconn(conn)
            except Exception as e:
                print(f"⚠️ Error guardando ticket en PostgreSQL: {e}, usando memoria")
                self._tickets[ticket_id] = ticket
        else:
            self._tickets[ticket_id] = ticket
        
        return ticket

    def update_ticket_status(
        self, 
        ticket_id: str, 
        status: str,
        resolution: Optional[str] = None,
        assigned_to: Optional[str] = None
    ) -> Dict[str, Any] | None:
        """Actualiza el estado de un ticket."""
        now = datetime.now().isoformat()
        
        if self.use_postgresql:
            try:
                conn = self.pool.getconn()
                try:
                    cur = conn.cursor(cursor_factory=RealDictCursor)
                    
                    # Construir query dinámica
                    updates = ["status = %s", "updated_at = %s"]
                    values = [status, now]
                    
                    if resolution:
                        updates.append("resolution = %s")
                        values.append(resolution)
                    
                    if assigned_to:
                        updates.append("assigned_to = %s")
                        values.append(assigned_to)
                    
                    if status == "closed":
                        updates.append("closed_at = %s")
                        values.append(now)
                    
                    values.append(ticket_id)
                    
                    query = f"""
                        UPDATE support_tickets 
                        SET {', '.join(updates)}
                        WHERE ticket_id = %s
                        RETURNING *
                    """
                    
                    cur.execute(query, values)
                    result = cur.fetchone()
                    conn.commit()
                    
                    if result:
                        ticket = dict(result)
                        print(f"✅ Ticket {ticket_id} actualizado: {status}")
                        return ticket
                    else:
                        print(f"⚠️ Ticket {ticket_id} no encontrado")
                        return None
                finally:
                    self.pool.putconn(conn)
            except Exception as e:
                print(f"⚠️ Error actualizando ticket en PostgreSQL: {e}")
                return None
        
        # Fallback en memoria
        ticket = self._tickets.get(ticket_id)
        if not ticket:
            return None
        
        ticket["status"] = status
        ticket["updated_at"] = now
        if resolution:
            ticket["resolution"] = resolution
        if assigned_to:
            ticket["assigned_to"] = assigned_to
        if status == "closed":
            ticket["closed_at"] = now
        
        return ticket

    def escalate_ticket(
        self,
        ticket_id: str,
        reason: str,
        assigned_to: Optional[str] = None
    ) -> Dict[str, Any] | None:
        """Escala un ticket a un agente humano."""
        now = datetime.now().isoformat()
        
        if self.use_postgresql:
            try:
                conn = self.pool.getconn()
                try:
                    cur = conn.cursor(cursor_factory=RealDictCursor)
                    cur.execute("""
                        UPDATE support_tickets 
                        SET status = 'escalated', 
                            escalated = TRUE,
                            escalation_reason = %s,
                            assigned_to = %s,
                            updated_at = %s
                        WHERE ticket_id = %s
                        RETURNING *
                    """, (reason, assigned_to, now, ticket_id))
                    result = cur.fetchone()
                    conn.commit()
                    
                    if result:
                        ticket = dict(result)
                        print(f"✅ Ticket {ticket_id} escalado: {reason}")
                        return ticket
                    return None
                finally:
                    self.pool.putconn(conn)
            except Exception as e:
                print(f"⚠️ Error escalando ticket en PostgreSQL: {e}")
                return None
        
        # Fallback en memoria
        ticket = self._tickets.get(ticket_id)
        if not ticket:
            return None
        
        ticket["status"] = "escalated"
        ticket["escalated"] = True
        ticket["escalation_reason"] = reason
        ticket["assigned_to"] = assigned_to
        ticket["updated_at"] = now
        
        return ticket

    def list_tickets_for_session(self, session_id: str) -> List[Dict[str, Any]]:
        """Lista todos los tickets de una sesión."""
        if self.use_postgresql:
            try:
                conn = self.pool.getconn()
                try:
                    cur = conn.cursor(cursor_factory=RealDictCursor)
                    cur.execute("""
                        SELECT * FROM support_tickets 
                        WHERE session_id = %s 
                        ORDER BY created_at DESC
                    """, (session_id,))
                    results = cur.fetchall()
                    return [dict(row) for row in results]
                finally:
                    self.pool.putconn(conn)
            except Exception as e:
                print(f"⚠️ Error listando tickets en PostgreSQL: {e}")
                return []
        
        # Fallback en memoria
        return [t for t in self._tickets.values() if t.get("session_id") == session_id]

    def get_ticket(self, ticket_id: str) -> Dict[str, Any] | None:
        """Obtiene un ticket por ID."""
        if self.use_postgresql:
            try:
                conn = self.pool.getconn()
                try:
                    cur = conn.cursor(cursor_factory=RealDictCursor)
                    cur.execute("SELECT * FROM support_tickets WHERE ticket_id = %s", (ticket_id,))
                    result = cur.fetchone()
                    if result:
                        return dict(result)
                    return None
                finally:
                    self.pool.putconn(conn)
            except Exception as e:
                print(f"⚠️ Error obteniendo ticket en PostgreSQL: {e}")
                return None
        
        # Fallback en memoria
        return self._tickets.get(ticket_id)

    def get_open_tickets_count(self, session_id: Optional[str] = None) -> int:
        """Obtiene el conteo de tickets abiertos."""
        if self.use_postgresql:
            try:
                conn = self.pool.getconn()
                try:
                    cur = conn.cursor()
                    if session_id:
                        cur.execute("""
                            SELECT COUNT(*) FROM support_tickets 
                            WHERE session_id = %s AND status IN ('open', 'in_progress')
                        """, (session_id,))
                    else:
                        cur.execute("""
                            SELECT COUNT(*) FROM support_tickets 
                            WHERE status IN ('open', 'in_progress')
                        """)
                    result = cur.fetchone()
                    return result[0] if result else 0
                finally:
                    self.pool.putconn(conn)
            except Exception as e:
                print(f"⚠️ Error contando tickets en PostgreSQL: {e}")
                return 0
        
        # Fallback en memoria
        if session_id:
            return len([t for t in self._tickets.values() 
                       if t.get("session_id") == session_id and t.get("status") in ["open", "in_progress"]])
        return len([t for t in self._tickets.values() if t.get("status") in ["open", "in_progress"]])
