"""
Conversation Memory - Memoria Conversacional Profunda
Sistema de memoria inteligente que mantiene contexto completo de conversaciones
"""

from __future__ import annotations

import json
import time
from typing import List, Dict, Optional, Any
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict, field
from collections import deque

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage


@dataclass
class ConversationContext:
    """Contexto acumulado de una conversación."""
    session_id: str
    user_id: str
    preferences: Dict[str, Any] = field(default_factory=dict)
    needs_mentioned: List[str] = field(default_factory=list)
    objections_raised: List[str] = field(default_factory=list)
    products_viewed: List[str] = field(default_factory=list)
    products_interested: List[str] = field(default_factory=list)
    budget_range: Optional[str] = None
    timeline: Optional[str] = None
    use_case: Optional[str] = None
    previous_concerns: List[str] = field(default_factory=list)
    key_insights: List[str] = field(default_factory=list)
    customer_dna: Optional[Dict[str, Any]] = None  # "Ficha médica" del comprador (NIVEL DIOS)
    last_updated: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class ConversationSummary:
    """Resumen inteligente de una conversación."""
    session_id: str
    user_id: str
    summary: str
    key_points: List[str]
    preferences: Dict[str, Any]
    next_steps: List[str]
    sentiment: str  # positive, neutral, negative, frustrated
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


class ConversationMemory:
    """
    Sistema de memoria conversacional profunda.
    
    Características:
    - Resumen inteligente de conversaciones largas
    - Referencias a mensajes anteriores
    - Contexto acumulado de preferencias y necesidades
    - Memoria a largo plazo entre sesiones
    """
    
    def __init__(self, storage_dir: Path):
        """
        Inicializa el sistema de memoria.
        
        Args:
            storage_dir: Directorio para almacenar memoria persistente
        """
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        # Memoria en memoria (cache)
        self._conversation_contexts: Dict[str, ConversationContext] = {}
        self._conversation_histories: Dict[str, deque] = {}  # session_id -> deque de mensajes
        self._user_long_term_memory: Dict[str, List[ConversationSummary]] = {}  # user_id -> summaries
        
        # Configuración
        self.max_messages_in_memory = 50  # Mensajes recientes en memoria
        self.summarize_every_n_messages = 20  # Resumir cada N mensajes
        self.max_long_term_summaries = 10  # Máximo de resúmenes por usuario
    
    def add_message(self, session_id: str, user_id: str, role: str, content: str, metadata: Optional[Dict] = None):
        """
        Añade un mensaje a la memoria de la conversación.
        
        Args:
            session_id: ID de la sesión actual
            user_id: ID del usuario
            role: "user" o "assistant"
            content: Contenido del mensaje
            metadata: Metadata adicional (productos mencionados, etc.)
        """
        # Inicializar contextos si no existen
        if session_id not in self._conversation_contexts:
            self._conversation_contexts[session_id] = ConversationContext(
                session_id=session_id,
                user_id=user_id
            )
            # Cargar memoria a largo plazo del usuario
            self._load_user_long_term_memory(user_id)
        
        if session_id not in self._conversation_histories:
            self._conversation_histories[session_id] = deque(maxlen=self.max_messages_in_memory)
        
        # Añadir mensaje al historial
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {}
        }
        self._conversation_histories[session_id].append(message)
        
        # Actualizar contexto acumulado
        self._update_context_from_message(session_id, role, content, metadata)
        
        # Guardar memoria a largo plazo periódicamente
        if len(self._conversation_histories[session_id]) % self.summarize_every_n_messages == 0:
            self._create_conversation_summary(session_id)
    
    def _update_context_from_message(self, session_id: str, role: str, content: str, metadata: Optional[Dict]):
        """Actualiza el contexto acumulado basándose en el mensaje."""
        context = self._conversation_contexts[session_id]
        content_lower = content.lower()
        
        # Detectar preferencias, necesidades, objeciones, etc.
        if role == "user":
            # Preferencias
            if any(word in content_lower for word in ["me gusta", "prefiero", "me encanta", "favorito"]):
                # Extraer preferencias del mensaje
                context.preferences["likes"] = context.preferences.get("likes", [])
                # Puede mejorarse con NER para extraer entidades
            
            # Necesidades mencionadas
            if any(word in content_lower for word in ["necesito", "busco", "quiero", "requiero"]):
                context.needs_mentioned.append(content[:200])  # Primeros 200 chars
            
            # Objeciones
            objection_keywords = ["caro", "costoso", "precio", "no tengo", "no puedo", "no estoy seguro", "duda"]
            if any(keyword in content_lower for keyword in objection_keywords):
                context.objections_raised.append(content[:200])
            
            # Presupuesto
            if "presupuesto" in content_lower or "precio" in content_lower:
                # Intentar extraer rango de presupuesto
                context.budget_range = content[:100]
            
            # Timeline
            if any(word in content_lower for word in ["urgente", "rápido", "pronto", "inmediato", "fecha", "cuándo"]):
                context.timeline = content[:100]
            
            # Productos mencionados/interesados
            if metadata:
                if "product_id" in metadata:
                    product_id = metadata["product_id"]
                    if product_id not in context.products_viewed:
                        context.products_viewed.append(product_id)
                    if "interest_level" in metadata and metadata["interest_level"] == "high":
                        if product_id not in context.products_interested:
                            context.products_interested.append(product_id)
        
        context.last_updated = datetime.now().isoformat()
        
        # Generar/actualizar customer_dna si hay suficiente información (cada 7 mensajes)
        history = self._conversation_histories.get(session_id)
        if history and len(history) % 7 == 0:  # Cada ~7 mensajes
            self._generate_customer_dna(session_id)
    
    def get_conversation_context(self, session_id: str) -> Optional[ConversationContext]:
        """Obtiene el contexto acumulado de una conversación."""
        return self._conversation_contexts.get(session_id)
    
    def get_accumulated_context(self, session_id: str) -> ConversationContext:
        """Obtiene el contexto acumulado de una conversación (alias para compatibilidad)."""
        if session_id not in self._conversation_contexts:
            # Crear contexto vacío si no existe
            user_id = "unknown"
            return ConversationContext(session_id=session_id, user_id=user_id)
        return self._conversation_contexts[session_id]
    
    def get_conversation_summary_text(self, session_id: str) -> str:
        """
        Genera un resumen de texto del contexto de conversación para usar en prompts.
        
        Returns:
            Texto formateado con resumen del contexto
        """
        context = self._conversation_contexts.get(session_id)
        if not context:
            return ""
        
        summary_parts = []
        
        # Preferencias
        if context.preferences:
            summary_parts.append(f"**Preferencias del cliente:** {json.dumps(context.preferences, ensure_ascii=False)}")
        
        # Necesidades mencionadas
        if context.needs_mentioned:
            summary_parts.append(f"**Necesidades mencionadas:** {', '.join(context.needs_mentioned[-3:])}")  # Últimas 3
        
        # Objeciones previas
        if context.objections_raised:
            summary_parts.append(f"**Objeciones previas:** {', '.join(context.objections_raised[-3:])}")
        
        # Productos de interés
        if context.products_interested:
            summary_parts.append(f"**Productos de interés:** {', '.join(context.products_interested)}")
        
        # Presupuesto y timeline
        if context.budget_range:
            summary_parts.append(f"**Presupuesto mencionado:** {context.budget_range}")
        if context.timeline:
            summary_parts.append(f"**Timeline/Urgencia:** {context.timeline}")
        
        # Insights clave
        if context.key_insights:
            summary_parts.append(f"**Insights clave:** {', '.join(context.key_insights)}")
        
        if summary_parts:
            return "\n".join(summary_parts)
        return ""
    
    def get_recent_history_text(self, session_id: str, last_n: int = 5) -> str:
        """
        Obtiene los últimos N mensajes como texto.
        
        Args:
            session_id: ID de la sesión
            last_n: Número de mensajes recientes
            
        Returns:
            Texto con mensajes recientes
        """
        if session_id not in self._conversation_histories:
            return ""
        
        messages = list(self._conversation_histories[session_id])[-last_n:]
        
        history_text = []
        for msg in messages:
            role_label = "Cliente" if msg["role"] == "user" else "Asistente"
            history_text.append(f"{role_label}: {msg['content']}")
        
        return "\n".join(history_text)
    
    def get_long_term_memory_text(self, user_id: str) -> str:
        """
        Obtiene memoria a largo plazo del usuario (de sesiones anteriores).
        
        Args:
            user_id: ID del usuario
            
        Returns:
            Texto con memoria a largo plazo
        """
        if user_id not in self._user_long_term_memory:
            return ""
        
        summaries = self._user_long_term_memory[user_id][-3:]  # Últimas 3 conversaciones
        
        memory_parts = []
        for summary in summaries:
            memory_parts.append(f"**Conversación anterior ({summary.created_at[:10]}):**")
            memory_parts.append(f"- Resumen: {summary.summary}")
            if summary.key_points:
                memory_parts.append(f"- Puntos clave: {', '.join(summary.key_points[:3])}")
            if summary.preferences:
                memory_parts.append(f"- Preferencias: {json.dumps(summary.preferences, ensure_ascii=False)}")
        
        if memory_parts:
            return "\n".join(memory_parts)
        return ""
    
    def _create_conversation_summary(self, session_id: str):
        """Crea un resumen inteligente de la conversación."""
        context = self._conversation_contexts.get(session_id)
        history = self._conversation_histories.get(session_id)
        
        if not context or not history:
            return
        
        # Crear resumen básico (puede mejorarse con LLM)
        summary_text = f"Conversación sobre {', '.join(context.needs_mentioned[:3]) if context.needs_mentioned else 'productos y servicios'}"
        
        key_points = []
        if context.products_interested:
            key_points.append(f"Interés en productos: {', '.join(context.products_interested)}")
        if context.objections_raised:
            key_points.append(f"Objeciones: {len(context.objections_raised)} mencionadas")
        if context.budget_range:
            key_points.append(f"Presupuesto: {context.budget_range}")
        
        summary = ConversationSummary(
            session_id=session_id,
            user_id=context.user_id,
            summary=summary_text,
            key_points=key_points,
            preferences=context.preferences.copy(),
            next_steps=[],
            sentiment="neutral"
        )
        
        # Guardar en memoria a largo plazo
        if context.user_id not in self._user_long_term_memory:
            self._user_long_term_memory[context.user_id] = []
        
        self._user_long_term_memory[context.user_id].append(summary)
        
        # Limitar número de resúmenes
        if len(self._user_long_term_memory[context.user_id]) > self.max_long_term_summaries:
            self._user_long_term_memory[context.user_id] = self._user_long_term_memory[context.user_id][-self.max_long_term_summaries:]
        
        # Persistir
        self._save_user_long_term_memory(context.user_id)
    
    def _load_user_long_term_memory(self, user_id: str):
        """Carga memoria a largo plazo de un usuario desde disco."""
        memory_file = self.storage_dir / f"user_memory_{user_id}.json"
        
        if not memory_file.exists():
            return
        
        try:
            with open(memory_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            summaries = [ConversationSummary(**s) for s in data.get("summaries", [])]
            self._user_long_term_memory[user_id] = summaries
        except Exception as e:
            print(f"⚠️ Error cargando memoria a largo plazo para {user_id}: {e}")
    
    def _save_user_long_term_memory(self, user_id: str):
        """Guarda memoria a largo plazo de un usuario en disco."""
        if user_id not in self._user_long_term_memory:
            return
        
        memory_file = self.storage_dir / f"user_memory_{user_id}.json"
        
        try:
            data = {
                "user_id": user_id,
                "summaries": [asdict(s) for s in self._user_long_term_memory[user_id]],
                "last_updated": datetime.now().isoformat()
            }
            
            with open(memory_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"⚠️ Error guardando memoria a largo plazo para {user_id}: {e}")
    
    def save_session_memory(self, session_id: str):
        """Guarda la memoria de una sesión completa."""
        context = self._conversation_contexts.get(session_id)
        if context:
            # Crear resumen final
            self._create_conversation_summary(session_id)
    
    def get_full_context_for_prompt(self, session_id: str, user_id: str, include_history: bool = True, include_long_term: bool = True) -> str:
        """
        Obtiene contexto completo formateado para usar en prompts del LLM.
        
        Args:
            session_id: ID de la sesión actual
            user_id: ID del usuario
            include_history: Incluir historial reciente
            include_long_term: Incluir memoria a largo plazo
            
        Returns:
            Texto formateado con todo el contexto
        """
        context_parts = []
        
        # Memoria a largo plazo (sesiones anteriores)
        if include_long_term:
            long_term = self.get_long_term_memory_text(user_id)
            if long_term:
                context_parts.append("**MEMORIA A LARGO PLAZO (Sesiones Anteriores):**")
                context_parts.append(long_term)
                context_parts.append("")
        
        # Contexto acumulado de esta sesión
        context_summary = self.get_conversation_summary_text(session_id)
        if context_summary:
            context_parts.append("**CONTEXTO ACUMULADO DE ESTA CONVERSACIÓN:**")
            context_parts.append(context_summary)
            context_parts.append("")
        
        # Historial reciente
        if include_history:
            recent_history = self.get_recent_history_text(session_id, last_n=5)
            if recent_history:
                context_parts.append("**HISTORIAL RECIENTE:**")
                context_parts.append(recent_history)
                context_parts.append("")
        
        return "\n".join(context_parts)
    
    def _generate_customer_dna(self, session_id: str):
        """
        Genera el "Customer DNA" - Resumen inteligente del perfil del comprador.
        
        Esto es como una "ficha médica" que resume la personalidad, preferencias y estilo
        del cliente sin necesidad de leer todo el historial cada vez.
        """
        context = self._conversation_contexts.get(session_id)
        history = self._conversation_histories.get(session_id)
        
        if not context or not history or len(history) < 3:
            return  # No hay suficiente información aún
        
        try:
            # Generar customer_dna usando reglas (puede mejorarse con LLM)
            customer_dna = self._generate_dna_from_rules(context, list(history)[-10:])
            context.customer_dna = customer_dna
            
            print(f"🧬 Customer DNA generado para sesión {session_id[:8]}: {customer_dna.get('summary', 'N/A')[:50]}...")
            
        except Exception as e:
            print(f"⚠️ Error generando customer_dna: {e}")
            # Si falla, crear DNA básico
            context.customer_dna = {
                "summary": "Cliente en proceso de evaluación",
                "sensibility": "unknown",
                "communication_style": "unknown"
            }
    
    def _generate_dna_from_rules(self, context: ConversationContext, recent_messages: List[Dict]) -> Dict[str, Any]:
        """Genera customer_dna usando reglas básicas (fallback sin LLM)."""
        dna = {
            "summary": "",
            "sensibility": "both",
            "communication_style": "friendly",
            "decision_speed": "medium",
            "recurring_objection": None,
            "preferred_incentive": "value",
            "personality_traits": [],
            "trust_builders": [],
            "deal_breakers": []
        }
        
        # Analizar sensibilidad (precio vs calidad)
        all_text = " ".join([msg.get("content", "").lower() for msg in recent_messages])
        price_mentions = sum(1 for word in ["precio", "caro", "barato", "costo", "descuento", "oferta"] if word in all_text)
        quality_mentions = sum(1 for word in ["calidad", "durable", "bueno", "excelente", "premium"] if word in all_text)
        
        if price_mentions > quality_mentions * 1.5:
            dna["sensibility"] = "price"
            dna["preferred_incentive"] = "discount"
        elif quality_mentions > price_mentions * 1.5:
            dna["sensibility"] = "quality"
            dna["preferred_incentive"] = "value"
        
        # Analizar estilo de comunicación
        avg_message_length = sum(len(msg.get("content", "")) for msg in recent_messages) / len(recent_messages) if recent_messages else 0
        if avg_message_length < 30:
            dna["communication_style"] = "direct"
        elif avg_message_length > 100:
            dna["communication_style"] = "detailed"
        
        # Objeción recurrente
        if context.objections_raised:
            dna["recurring_objection"] = context.objections_raised[-1]
        
        # Resumen
        traits = []
        if dna["sensibility"] == "price":
            traits.append("Orientado al precio")
        elif dna["sensibility"] == "quality":
            traits.append("Valora la calidad")
        
        if dna["communication_style"] == "direct":
            traits.append("Comunicación directa")
        
        dna["personality_traits"] = traits
        
        dna["summary"] = f"Cliente {dna['sensibility']}-orientado con estilo {dna['communication_style']}. " + \
                        (f"Objeción recurrente: {dna['recurring_objection']}" if dna["recurring_objection"] else "")
        
        return dna

