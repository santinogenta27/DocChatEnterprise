"""PostgreSQL Session Manager - Memoria de Largo Plazo para STAR AGENT.

Permite que el agente recuerde clientes meses despuÃ©s de la Ãºltima conversaciÃ³n.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from dataclasses import asdict

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    from psycopg2.pool import ThreadedConnectionPool
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False

from .customer_session import CustomerSessionState, CustomerProfile, SentimentLabel


class PostgreSQLSessionManager:
    """Gestor de sesiones con PostgreSQL para memoria de largo plazo.
    
    Permite:
    - Recordar clientes meses despuÃ©s
    - Historial completo de conversaciones
    - AnÃ¡lisis de comportamiento a largo plazo
    - PersonalizaciÃ³n basada en historial
    """
    
    def __init__(self, database_url: str, pool_size: int = 10):
        """Inicializa el gestor de PostgreSQL.
        
        Args:
            database_url: URL de conexiÃ³n PostgreSQL (postgresql://user:pass@host:port/db)
            pool_size: TamaÃ±o del pool de conexiones
        """
        if not PSYCOPG2_AVAILABLE:
            raise ImportError(
                "psycopg2 no estÃ¡ instalado. Instala con: pip install psycopg2-binary"
            )
        
        self.database_url = database_url
        self.pool_size = pool_size
        self.pool: Optional[ThreadedConnectionPool] = None
        
        # Inicializar base de datos
        self._init_database()
    
    def _init_database(self):
        """Inicializa las tablas necesarias en PostgreSQL."""
        try:
            # Crear pool de conexiones
            self.pool = ThreadedConnectionPool(
                minconn=1,
                maxconn=self.pool_size,
                dsn=self.database_url
            )
            
            # Crear tablas si no existen
            conn = self.pool.getconn()
            try:
                cur = conn.cursor()
                
                # Tabla de sesiones
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS star_agent_sessions (
                        session_id VARCHAR(255) PRIMARY KEY,
                        user_id VARCHAR(255) NOT NULL,
                        profile JSONB,
                        cart JSONB,
                        recent_orders JSONB,
                        open_tickets JSONB,
                        last_messages JSONB,
                        sentiment VARCHAR(50),
                        frustration_score FLOAT,
                        needs_handoff BOOLEAN,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Tabla de historial de mensajes (para anÃ¡lisis a largo plazo)
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS star_agent_messages (
                        id SERIAL PRIMARY KEY,
                        session_id VARCHAR(255) NOT NULL,
                        role VARCHAR(50) NOT NULL,
                        content TEXT NOT NULL,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        metadata JSONB,
                        FOREIGN KEY (session_id) REFERENCES star_agent_sessions(session_id) ON DELETE CASCADE
                    )
                """)
                
                # Tabla de compras histÃ³ricas (para cross-selling y recomendaciones)
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS star_agent_purchases (
                        id SERIAL PRIMARY KEY,
                        session_id VARCHAR(255) NOT NULL,
                        user_id VARCHAR(255) NOT NULL,
                        order_id VARCHAR(255),
                        products JSONB NOT NULL,
                        total_amount FLOAT,
                        purchase_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (session_id) REFERENCES star_agent_sessions(session_id) ON DELETE CASCADE
                    )
                """)
                
                # Ãndices para bÃºsqueda rÃ¡pida
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_sessions_user_id 
                    ON star_agent_sessions(user_id)
                """)
                
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_messages_session_id 
                    ON star_agent_messages(session_id)
                """)
                
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_purchases_user_id 
                    ON star_agent_purchases(user_id)
                """)
                
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_purchases_date 
                    ON star_agent_purchases(purchase_date)
                """)
                
                conn.commit()
                print("âœ… PostgreSQL Session Manager inicializado - Memoria de largo plazo activa")
            finally:
                self.pool.putconn(conn)
        except Exception as e:
            print(f"âš ï¸ Error inicializando PostgreSQL: {e}")
            raise
    
    def get_or_create(self, session_id: str, profile: CustomerProfile) -> CustomerSessionState:
        """Obtiene o crea una sesiÃ³n desde PostgreSQL."""
        conn = self.pool.getconn()
        try:
            cur = conn.cursor(cursor_factory=RealDictCursor)
            
            # Buscar sesiÃ³n existente
            cur.execute("""
                SELECT * FROM star_agent_sessions 
                WHERE session_id = %s
            """, (session_id,))
            
            row = cur.fetchone()
            
            if row:
                # SesiÃ³n existe, cargar desde DB
                session = self._row_to_session(row)
            else:
                # Crear nueva sesiÃ³n
                session = CustomerSessionState(
                    session_id=session_id,
                    profile=profile
                )
                self._save_session(session)
            
            return session
        finally:
            self.pool.putconn(conn)
    
    def update(self, session: CustomerSessionState) -> None:
        """Actualiza una sesiÃ³n en PostgreSQL."""
        self._save_session(session)
    
    def get(self, session_id: str) -> Optional[CustomerSessionState]:
        """Obtiene una sesiÃ³n por ID."""
        conn = self.pool.getconn()
        try:
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute("""
                SELECT * FROM star_agent_sessions 
                WHERE session_id = %s
            """, (session_id,))
            
            row = cur.fetchone()
            if row:
                return self._row_to_session(row)
            return None
        finally:
            self.pool.putconn(conn)
    
    def get_user_history(self, user_id: str, days: int = 180) -> Dict[str, Any]:
        """Obtiene historial completo de un usuario (Ãºltimos N dÃ­as).
        
        Retorna:
        - Sesiones anteriores
        - Compras histÃ³ricas
        - Mensajes mÃ¡s relevantes
        - Perfil consolidado
        """
        conn = self.pool.getconn()
        try:
            cur = conn.cursor(cursor_factory=RealDictCursor)
            
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            # Obtener sesiones recientes
            cur.execute("""
                SELECT * FROM star_agent_sessions 
                WHERE user_id = %s AND updated_at >= %s
                ORDER BY updated_at DESC
                LIMIT 10
            """, (user_id, cutoff_date))
            
            sessions = [dict(row) for row in cur.fetchall()]
            
            # Obtener compras histÃ³ricas
            cur.execute("""
                SELECT * FROM star_agent_purchases 
                WHERE user_id = %s AND purchase_date >= %s
                ORDER BY purchase_date DESC
            """, (user_id, cutoff_date))
            
            purchases = [dict(row) for row in cur.fetchall()]
            
            # Obtener mensajes recientes (Ãºltimos 50)
            cur.execute("""
                SELECT m.* FROM star_agent_messages m
                INNER JOIN star_agent_sessions s ON m.session_id = s.session_id
                WHERE s.user_id = %s AND m.timestamp >= %s
                ORDER BY m.timestamp DESC
                LIMIT 50
            """, (user_id, cutoff_date))
            
            messages = [dict(row) for row in cur.fetchall()]
            
            return {
                "sessions": sessions,
                "purchases": purchases,
                "messages": messages,
                "total_purchases": len(purchases),
                "total_spent": sum(p.get("total_amount", 0) or 0 for p in purchases),
                "last_purchase_date": purchases[0]["purchase_date"] if purchases else None
            }
        finally:
            self.pool.putconn(conn)
    
    def save_message(self, session_id: str, role: str, content: str, metadata: Optional[Dict] = None):
        """Guarda un mensaje en el historial."""
        conn = self.pool.getconn()
        try:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO star_agent_messages (session_id, role, content, metadata)
                VALUES (%s, %s, %s, %s)
            """, (session_id, role, content, json.dumps(metadata or {})))
            conn.commit()
        finally:
            self.pool.putconn(conn)
    
    def save_purchase(self, session_id: str, user_id: str, order_id: str, products: List[Dict], total_amount: float):
        """Guarda una compra en el historial."""
        conn = self.pool.getconn()
        try:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO star_agent_purchases (session_id, user_id, order_id, products, total_amount)
                VALUES (%s, %s, %s, %s, %s)
            """, (session_id, user_id, order_id, json.dumps(products), total_amount))
            conn.commit()
        finally:
            self.pool.putconn(conn)
    
    def _save_session(self, session: CustomerSessionState):
        """Guarda una sesiÃ³n en PostgreSQL."""
        conn = self.pool.getconn()
        try:
            cur = conn.cursor()
            
            # Convertir sesiÃ³n a JSON
            profile_dict = asdict(session.profile) if session.profile else None
            
            cur.execute("""
                INSERT INTO star_agent_sessions (
                    session_id, user_id, profile, cart, recent_orders, 
                    open_tickets, last_messages, sentiment, frustration_score, 
                    needs_handoff, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (session_id) DO UPDATE SET
                    profile = EXCLUDED.profile,
                    cart = EXCLUDED.cart,
                    recent_orders = EXCLUDED.recent_orders,
                    open_tickets = EXCLUDED.open_tickets,
                    last_messages = EXCLUDED.last_messages,
                    sentiment = EXCLUDED.sentiment,
                    frustration_score = EXCLUDED.frustration_score,
                    needs_handoff = EXCLUDED.needs_handoff,
                    updated_at = CURRENT_TIMESTAMP
            """, (
                session.session_id,
                session.profile.user_id if session.profile else "unknown",
                json.dumps(profile_dict) if profile_dict else None,
                json.dumps(session.cart) if session.cart else None,
                json.dumps(session.recent_orders) if session.recent_orders else None,
                json.dumps(session.open_tickets) if session.open_tickets else None,
                json.dumps(session.last_messages) if session.last_messages else None,
                session.sentiment.value if session.sentiment else None,
                session.frustration_score,
                session.needs_handoff
            ))
            
            conn.commit()
        finally:
            self.pool.putconn(conn)
    
    def _row_to_session(self, row: Dict) -> CustomerSessionState:
        """Convierte una fila de DB a CustomerSessionState."""
        from .customer_session import CustomerProfile
        
        profile_dict = row.get("profile") or {}
        if isinstance(profile_dict, str):
            profile_dict = json.loads(profile_dict)
        
        profile = CustomerProfile(
            user_id=profile_dict.get("user_id", row.get("user_id", "unknown")),
            channel=profile_dict.get("channel", "web"),
            display_name=profile_dict.get("display_name"),
            language=profile_dict.get("language"),
            metadata=profile_dict.get("metadata", {})
        )
        
        session = CustomerSessionState(
            session_id=row["session_id"],
            profile=profile
        )
        
        # Cargar datos desde JSON
        if row.get("cart"):
            session.cart = json.loads(row["cart"]) if isinstance(row["cart"], str) else row["cart"]
        
        if row.get("recent_orders"):
            session.recent_orders = json.loads(row["recent_orders"]) if isinstance(row["recent_orders"], str) else row["recent_orders"]
        
        if row.get("open_tickets"):
            session.open_tickets = json.loads(row["open_tickets"]) if isinstance(row["open_tickets"], str) else row["open_tickets"]
        
        if row.get("last_messages"):
            session.last_messages = json.loads(row["last_messages"]) if isinstance(row["last_messages"], str) else row["last_messages"]
        
        if row.get("sentiment"):
            try:
                session.sentiment = SentimentLabel(row["sentiment"])
            except:
                session.sentiment = SentimentLabel.NEUTRAL
        
        session.frustration_score = float(row.get("frustration_score", 0) or 0)
        session.needs_handoff = bool(row.get("needs_handoff", False))
        
        return session
    
    def clear(self, session_id: str) -> None:
        """Elimina una sesiÃ³n (y sus mensajes relacionados por CASCADE)."""
        conn = self.pool.getconn()
        try:
            cur = conn.cursor()
            cur.execute("DELETE FROM star_agent_sessions WHERE session_id = %s", (session_id,))
            conn.commit()
        finally:
            self.pool.putconn(conn)















