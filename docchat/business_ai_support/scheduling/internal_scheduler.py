"""Sistema de Scheduling Interno Simple para Business AI Support.

Permite programar citas con slots fijos y disponibilidad básica.
"""

from __future__ import annotations

from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
import uuid

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False


class AppointmentStatus(str, Enum):
    """Estado de una cita."""
    AVAILABLE = "available"
    BOOKED = "booked"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"


@dataclass
class AppointmentSlot:
    """Slot de cita."""
    slot_id: str
    start_time: datetime
    end_time: datetime
    appointment_type: str
    status: AppointmentStatus
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    booked_by: Optional[str] = None
    notes: Optional[str] = None


class InternalScheduler:
    """Sistema de scheduling interno simple."""
    
    def __init__(self, database_url: Optional[str] = None, pool=None):
        """Inicializa el scheduler interno.
        
        Args:
            database_url: URL de conexión PostgreSQL (opcional)
            pool: Pool de conexiones PostgreSQL (opcional)
        """
        self.use_postgresql = False
        self.database_url = database_url
        self.pool = pool
        
        # Slots en memoria (fallback)
        self.slots: Dict[str, AppointmentSlot] = {}
        
        # Configuración de slots fijos
        self.default_slot_duration = timedelta(minutes=30)
        self.working_hours = {
            "start": "09:00",
            "end": "18:00"
        }
        
        if database_url and pool and PSYCOPG2_AVAILABLE:
            self.use_postgresql = True
            print("✅ InternalScheduler usando PostgreSQL")
        else:
            print("⚠️ InternalScheduler usando almacenamiento en memoria")
    
    def create_slot(
        self,
        start_time: datetime,
        end_time: Optional[datetime] = None,
        appointment_type: str = "consultation"
    ) -> AppointmentSlot:
        """Crea un nuevo slot de cita."""
        if not end_time:
            end_time = start_time + self.default_slot_duration
        
        slot_id = f"SLOT-{uuid.uuid4().hex[:12].upper()}"
        
        slot = AppointmentSlot(
            slot_id=slot_id,
            start_time=start_time,
            end_time=end_time,
            appointment_type=appointment_type,
            status=AppointmentStatus.AVAILABLE
        )
        
        if self.use_postgresql:
            try:
                conn = self.pool.getconn()
                try:
                    cur = conn.cursor()
                    cur.execute("""
                        INSERT INTO appointment_slots 
                        (slot_id, start_time, end_time, appointment_type, status, created_at, updated_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """, (
                        slot_id, start_time, end_time, appointment_type,
                        AppointmentStatus.AVAILABLE.value,
                        datetime.now(), datetime.now()
                    ))
                    conn.commit()
                    print(f"✅ Slot {slot_id} creado en PostgreSQL")
                finally:
                    self.pool.putconn(conn)
            except Exception as e:
                print(f"⚠️ Error guardando slot en PostgreSQL: {e}")
                self.slots[slot_id] = slot
        else:
            self.slots[slot_id] = slot
        
        return slot
    
    def create_recurring_slots(
        self,
        start_date: datetime,
        end_date: datetime,
        days_of_week: List[int],  # 0=Monday, 6=Sunday
        time_slots: List[str],  # ["09:00", "10:00", "11:00"]
        appointment_type: str = "consultation"
    ) -> List[AppointmentSlot]:
        """Crea slots recurrentes para un rango de fechas."""
        created_slots = []
        current_date = start_date.date()
        end_date_only = end_date.date()
        
        while current_date <= end_date_only:
            if current_date.weekday() in days_of_week:
                for time_str in time_slots:
                    hour, minute = map(int, time_str.split(":"))
                    slot_datetime = datetime.combine(current_date, datetime.min.time().replace(hour=hour, minute=minute))
                    slot = self.create_slot(slot_datetime, appointment_type=appointment_type)
                    created_slots.append(slot)
            
            current_date += timedelta(days=1)
        
        return created_slots
    
    def get_available_slots(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        appointment_type: Optional[str] = None
    ) -> List[AppointmentSlot]:
        """Obtiene slots disponibles."""
        if self.use_postgresql:
            try:
                conn = self.pool.getconn()
                try:
                    cur = conn.cursor(cursor_factory=RealDictCursor)
                    
                    query = """
                        SELECT * FROM appointment_slots 
                        WHERE status = 'available'
                    """
                    params = []
                    
                    if start_date:
                        query += " AND start_time >= %s"
                        params.append(start_date)
                    
                    if end_date:
                        query += " AND start_time <= %s"
                        params.append(end_date)
                    
                    if appointment_type:
                        query += " AND appointment_type = %s"
                        params.append(appointment_type)
                    
                    query += " ORDER BY start_time ASC"
                    
                    cur.execute(query, params)
                    results = cur.fetchall()
                    
                    slots = []
                    for row in results:
                        slot = AppointmentSlot(
                            slot_id=row["slot_id"],
                            start_time=row["start_time"],
                            end_time=row["end_time"],
                            appointment_type=row["appointment_type"],
                            status=AppointmentStatus(row["status"]),
                            session_id=row.get("session_id"),
                            user_id=row.get("user_id"),
                            booked_by=row.get("booked_by"),
                            notes=row.get("notes")
                        )
                        slots.append(slot)
                    
                    return slots
                finally:
                    self.pool.putconn(conn)
            except Exception as e:
                print(f"⚠️ Error obteniendo slots en PostgreSQL: {e}")
                return []
        
        # Fallback en memoria
        available = [
            slot for slot in self.slots.values()
            if slot.status == AppointmentStatus.AVAILABLE
        ]
        
        if start_date:
            available = [s for s in available if s.start_time >= start_date]
        if end_date:
            available = [s for s in available if s.start_time <= end_date]
        if appointment_type:
            available = [s for s in available if s.appointment_type == appointment_type]
        
        return sorted(available, key=lambda x: x.start_time)
    
    def book_appointment(
        self,
        slot_id: str,
        session_id: str,
        user_id: str,
        notes: Optional[str] = None
    ) -> Optional[AppointmentSlot]:
        """Reserva una cita."""
        if self.use_postgresql:
            try:
                conn = self.pool.getconn()
                try:
                    cur = conn.cursor(cursor_factory=RealDictCursor)
                    
                    # Verificar que el slot esté disponible
                    cur.execute("""
                        SELECT * FROM appointment_slots 
                        WHERE slot_id = %s AND status = 'available'
                    """, (slot_id,))
                    row = cur.fetchone()
                    
                    if not row:
                        print(f"⚠️ Slot {slot_id} no disponible")
                        return None
                    
                    # Reservar
                    cur.execute("""
                        UPDATE appointment_slots 
                        SET status = 'booked',
                            session_id = %s,
                            user_id = %s,
                            booked_by = %s,
                            notes = %s,
                            updated_at = %s
                        WHERE slot_id = %s
                        RETURNING *
                    """, (session_id, user_id, user_id, notes, datetime.now(), slot_id))
                    
                    result = cur.fetchone()
                    conn.commit()
                    
                    if result:
                        slot = AppointmentSlot(
                            slot_id=result["slot_id"],
                            start_time=result["start_time"],
                            end_time=result["end_time"],
                            appointment_type=result["appointment_type"],
                            status=AppointmentStatus(result["status"]),
                            session_id=result["session_id"],
                            user_id=result["user_id"],
                            booked_by=result["booked_by"],
                            notes=result["notes"]
                        )
                        print(f"✅ Cita reservada: {slot_id}")
                        return slot
                    
                    return None
                finally:
                    self.pool.putconn(conn)
            except Exception as e:
                print(f"⚠️ Error reservando cita en PostgreSQL: {e}")
                return None
        
        # Fallback en memoria
        slot = self.slots.get(slot_id)
        if not slot or slot.status != AppointmentStatus.AVAILABLE:
            return None
        
        slot.status = AppointmentStatus.BOOKED
        slot.session_id = session_id
        slot.user_id = user_id
        slot.booked_by = user_id
        slot.notes = notes
        
        return slot
    
    def confirm_appointment(self, slot_id: str) -> bool:
        """Confirma una cita reservada."""
        if self.use_postgresql:
            try:
                conn = self.pool.getconn()
                try:
                    cur = conn.cursor()
                    cur.execute("""
                        UPDATE appointment_slots 
                        SET status = 'confirmed', updated_at = %s
                        WHERE slot_id = %s AND status = 'booked'
                    """, (datetime.now(), slot_id))
                    conn.commit()
                    return cur.rowcount > 0
                finally:
                    self.pool.putconn(conn)
            except Exception as e:
                print(f"⚠️ Error confirmando cita en PostgreSQL: {e}")
                return False
        
        # Fallback en memoria
        slot = self.slots.get(slot_id)
        if slot and slot.status == AppointmentStatus.BOOKED:
            slot.status = AppointmentStatus.CONFIRMED
            return True
        return False
    
    def cancel_appointment(self, slot_id: str) -> bool:
        """Cancela una cita."""
        if self.use_postgresql:
            try:
                conn = self.pool.getconn()
                try:
                    cur = conn.cursor()
                    cur.execute("""
                        UPDATE appointment_slots 
                        SET status = 'cancelled', updated_at = %s
                        WHERE slot_id = %s AND status IN ('booked', 'confirmed')
                    """, (datetime.now(), slot_id))
                    conn.commit()
                    return cur.rowcount > 0
                finally:
                    self.pool.putconn(conn)
            except Exception as e:
                print(f"⚠️ Error cancelando cita en PostgreSQL: {e}")
                return False
        
        # Fallback en memoria
        slot = self.slots.get(slot_id)
        if slot and slot.status in [AppointmentStatus.BOOKED, AppointmentStatus.CONFIRMED]:
            slot.status = AppointmentStatus.CANCELLED
            slot.session_id = None
            slot.user_id = None
            slot.booked_by = None
            return True
        return False
    
    def get_user_appointments(self, user_id: str) -> List[AppointmentSlot]:
        """Obtiene las citas de un usuario."""
        if self.use_postgresql:
            try:
                conn = self.pool.getconn()
                try:
                    cur = conn.cursor(cursor_factory=RealDictCursor)
                    cur.execute("""
                        SELECT * FROM appointment_slots 
                        WHERE user_id = %s AND status IN ('booked', 'confirmed')
                        ORDER BY start_time ASC
                    """, (user_id,))
                    results = cur.fetchall()
                    
                    slots = []
                    for row in results:
                        slot = AppointmentSlot(
                            slot_id=row["slot_id"],
                            start_time=row["start_time"],
                            end_time=row["end_time"],
                            appointment_type=row["appointment_type"],
                            status=AppointmentStatus(row["status"]),
                            session_id=row.get("session_id"),
                            user_id=row.get("user_id"),
                            booked_by=row.get("booked_by"),
                            notes=row.get("notes")
                        )
                        slots.append(slot)
                    
                    return slots
                finally:
                    self.pool.putconn(conn)
            except Exception as e:
                print(f"⚠️ Error obteniendo citas en PostgreSQL: {e}")
                return []
        
        # Fallback en memoria
        return [
            slot for slot in self.slots.values()
            if slot.user_id == user_id and slot.status in [AppointmentStatus.BOOKED, AppointmentStatus.CONFIRMED]
        ]




