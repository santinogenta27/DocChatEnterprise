"""PostgreSQL Session Manager - Memoria de Largo Plazo para Business AI Omnicanal.

Permite que el agente recuerde clientes meses después de la última conversación.
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
    - Recordar clientes meses después
    - Historial completo de conversaciones
    - Análisis de comportamiento a largo plazo
    - Personalización basada en historial
    """
    
    def __init__(self, database_url: str, pool_size: int = 10):
        """Inicializa el gestor de PostgreSQL.
        
        Args:
            database_url: URL de conexión PostgreSQL (postgresql://user:pass@host:port/db)
            pool_size: Tamaño del pool de conexiones
        """
        if not PSYCOPG2_AVAILABLE:
            raise ImportError(
                "psycopg2 no está instalado. Instala con: pip install psycopg2-binary"
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
                    CREATE TABLE IF NOT EXISTS business_ai_sessions (
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
                
                # Tabla de historial de mensajes (para análisis a largo plazo)
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS business_ai_messages (
                        id SERIAL PRIMARY KEY,
                        session_id VARCHAR(255) NOT NULL,
                        role VARCHAR(50) NOT NULL,
                        content TEXT NOT NULL,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        metadata JSONB,
                        FOREIGN KEY (session_id) REFERENCES business_ai_sessions(session_id) ON DELETE CASCADE
                    )
                """)
                
                # Tabla de compras históricas (para cross-selling y recomendaciones)
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS business_ai_purchases (
                        id SERIAL PRIMARY KEY,
                        session_id VARCHAR(255) NOT NULL,
                        user_id VARCHAR(255) NOT NULL,
                        order_id VARCHAR(255),
                        products JSONB NOT NULL,
                        total_amount FLOAT,
                        purchase_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (session_id) REFERENCES business_ai_sessions(session_id) ON DELETE CASCADE
                    )
                """)
                
                # Índices para búsqueda rápida
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_sessions_user_id 
                    ON business_ai_sessions(user_id)
                """)
                
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_messages_session_id 
                    ON business_ai_messages(session_id)
                """)
                
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_purchases_user_id 
                    ON business_ai_purchases(user_id)
                """)
                
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_purchases_date 
                    ON business_ai_purchases(purchase_date)
                """)
                
                conn.commit()
                print("✅ PostgreSQL Session Manager inicializado - Memoria de largo plazo activa")
            finally:
                self.pool.putconn(conn)
        except Exception as e:
            print(f"⚠️ Error inicializando PostgreSQL: {e}")
            raise
    
    def get_or_create(self, session_id: str, profile: CustomerProfile) -> CustomerSessionState:
        """Obtiene o crea una sesión desde PostgreSQL."""
        conn = self.pool.getconn()
        try:
            cur = conn.cursor(cursor_factory=RealDictCursor)
            
            # Buscar sesión existente
            cur.execute("""
                SELECT * FROM business_ai_sessions 
                WHERE session_id = %s
            """, (session_id,))
            
            row = cur.fetchone()
            
            if row:
                # Sesión existe, cargar desde DB
                session = self._row_to_session(row)
            else:
                # Crear nueva sesión
                session = CustomerSessionState(
                    session_id=session_id,
                    profile=profile
                )
                self._save_session(session)
            
            return session
        finally:
            self.pool.putconn(conn)
    
    def update(self, session: CustomerSessionState) -> None:
        """Actualiza una sesión en PostgreSQL."""
        self._save_session(session)
    
    def get(self, session_id: str) -> Optional[CustomerSessionState]:
        """Obtiene una sesión por ID."""
        conn = self.pool.getconn()
        try:
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute("""
                SELECT * FROM business_ai_sessions 
                WHERE session_id = %s
            """, (session_id,))
            
            row = cur.fetchone()
            if row:
                return self._row_to_session(row)
            return None
        finally:
            self.pool.putconn(conn)
    
    def get_user_history(self, user_id: str, days: int = 180) -> Dict[str, Any]:
        """Obtiene historial completo de un usuario (últimos N días).
        
        Retorna:
        - Sesiones anteriores
        - Compras históricas
        - Mensajes más relevantes
        - Perfil consolidado
        """
        conn = self.pool.getconn()
        try:
            cur = conn.cursor(cursor_factory=RealDictCursor)
            
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            # Obtener sesiones recientes
            cur.execute("""
                SELECT * FROM business_ai_sessions 
                WHERE user_id = %s AND updated_at >= %s
                ORDER BY updated_at DESC
                LIMIT 10
            """, (user_id, cutoff_date))
            
            sessions = [dict(row) for row in cur.fetchall()]
            
            # Obtener compras históricas
            cur.execute("""
                SELECT * FROM business_ai_purchases 
                WHERE user_id = %s AND purchase_date >= %s
                ORDER BY purchase_date DESC
            """, (user_id, cutoff_date))
            
            purchases = [dict(row) for row in cur.fetchall()]
            
            # Obtener mensajes recientes (últimos 50)
            cur.execute("""
                SELECT m.* FROM business_ai_messages m
                INNER JOIN business_ai_sessions s ON m.session_id = s.session_id
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
                INSERT INTO business_ai_messages (session_id, role, content, metadata)
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
                INSERT INTO business_ai_purchases (session_id, user_id, order_id, products, total_amount)
                VALUES (%s, %s, %s, %s, %s)
            """, (session_id, user_id, order_id, json.dumps(products), total_amount))
            conn.commit()
        finally:
            self.pool.putconn(conn)
    
    def _save_session(self, session: CustomerSessionState):
        """Guarda una sesión en PostgreSQL."""
        conn = self.pool.getconn()
        try:
            cur = conn.cursor()
            
            # Convertir sesión a JSON
            profile_dict = asdict(session.profile) if session.profile else None
            
            cur.execute("""
                INSERT INTO business_ai_sessions (
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
        """Elimina una sesión (y sus mensajes relacionados por CASCADE)."""
        conn = self.pool.getconn()
        try:
            cur = conn.cursor()
            cur.execute("DELETE FROM business_ai_sessions WHERE session_id = %s", (session_id,))
            conn.commit()
        finally:
            self.pool.putconn(conn)




