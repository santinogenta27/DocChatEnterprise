"""
Behavior Analyzer - AnÃ¡lisis de Comportamiento Avanzado
Detecta seÃ±ales de compra, urgencia, intenciÃ³n y segmenta clientes automÃ¡ticamente
"""

from __future__ import annotations

import re
from typing import Dict, Optional, List, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum


class PurchaseSignal(Enum):
    """SeÃ±ales de intenciÃ³n de compra."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    NONE = "none"


class UrgencyLevel(Enum):
    """Niveles de urgencia."""
    CRITICAL = "critical"  # Compra inmediata
    HIGH = "high"  # Compra esta semana
    MEDIUM = "medium"  # Compra este mes
    LOW = "low"  # ExploraciÃ³n
    NONE = "none"


class CustomerSegment(Enum):
    """Segmentos de clientes."""
    HOT_LEAD = "hot_lead"  # Listo para comprar
    WARM_LEAD = "warm_lead"  # Interesado, necesita mÃ¡s info
    COLD_LEAD = "cold_lead"  # Explorando
    RETURNING_CUSTOMER = "returning_customer"  # Cliente recurrente
    PRICE_SHOPPER = "price_shopper"  # Solo busca precio
    RESEARCHER = "researcher"  # Comparando opciones


@dataclass
class BehaviorAnalysis:
    """AnÃ¡lisis completo de comportamiento."""
    purchase_signal: PurchaseSignal
    urgency_level: UrgencyLevel
    segment: CustomerSegment
    confidence: float  # 0.0 - 1.0
    signals_detected: List[str]
    suggested_actions: List[str]
    risk_of_abandonment: float  # 0.0 - 1.0
    estimated_time_to_purchase: Optional[str]  # "immediate", "this_week", "this_month", etc.
    should_activate_closing: bool = False  # TRIGGER: Activar cierre proactivo ahora
    closing_trigger_reason: str = ""  # RazÃ³n por la que se activa el cierre


class BehaviorAnalyzer:
    """
    Analizador de comportamiento avanzado.
    
    Detecta:
    - SeÃ±ales de compra (alto/medio/bajo)
    - Nivel de urgencia
    - IntenciÃ³n de compra (predicciÃ³n ML bÃ¡sica)
    - SegmentaciÃ³n automÃ¡tica de clientes
    """
    
    def __init__(self):
        """Inicializa el analizador de comportamiento."""
        # Patrones de seÃ±ales de compra (alto)
        self.high_purchase_signals = [
            r"\b(?:comprar|compra|adquirir|quiero comprar|vamos a comprar|decidido|listo para comprar)\b",
            r"\b(?:agregar al carrito|aÃ±adir|carrito|checkout|pagar|proceder con la compra)\b",
            r"\b(?:envÃ­o|entrega|cuÃ¡ndo llega|garantÃ­a|devoluciÃ³n|polÃ­tica)\b",  # Preguntas de post-compra
            r"\b(?:descuento|cÃ³digo|cupÃ³n|promociÃ³n|oferta)\b",  # Buscando descuento (casi listo)
        ]
        
        # Patrones de urgencia
        self.urgency_patterns = {
            "critical": [
                r"\b(?:urgente|inmediato|hoy|maÃ±ana|ahora mismo|rÃ¡pido|asap)\b",
                r"\b(?:fecha lÃ­mite|deadline|necesito ya|tengo que tener)\b",
            ],
            "high": [
                r"\b(?:esta semana|pronto|en los prÃ³ximos dÃ­as|rapidez)\b",
                r"\b(?:evento|fecha importante|ocasiÃ³n especial)\b",
            ],
            "medium": [
                r"\b(?:este mes|en breve|cuando pueda|tarde o temprano)\b",
            ]
        }
        
        # Patrones de abandono
        self.abandonment_signals = [
            r"\b(?:pensarlo|pensar|lo pensarÃ©|dÃ©jame pensar|no estoy seguro|duda|indeciso)\b",
            r"\b(?:muy caro|no tengo dinero|presupuesto|no puedo permitirme)\b",
            r"\b(?:comparar|buscar otras opciones|ver otras alternativas|mirar mÃ¡s)\b",
            r"\b(?:gracias pero|no gracias|tal vez despuÃ©s|otra vez)\b",
        ]
    
    def analyze(self, 
                message: str,
                conversation_history: List[Dict],
                user_profile: Optional[Dict] = None,
                time_in_session: Optional[float] = None,
                products_viewed: Optional[List[str]] = None) -> BehaviorAnalysis:
        """
        Analiza el comportamiento del usuario.
        
        Args:
            message: Mensaje actual del usuario
            conversation_history: Historial de la conversaciÃ³n
            user_profile: Perfil del usuario (opcional)
            time_in_session: Tiempo en sesiÃ³n en minutos (opcional)
            products_viewed: Lista de productos vistos (opcional)
            
        Returns:
            BehaviorAnalysis con anÃ¡lisis completo
        """
        message_lower = message.lower()
        signals_detected = []
        purchase_score = 0.0
        urgency_score = 0.0
        abandonment_score = 0.0
        
        # 1. Detectar seÃ±ales de compra
        for pattern in self.high_purchase_signals:
            if re.search(pattern, message_lower, re.IGNORECASE):
                purchase_score += 0.3
                signals_detected.append(f"SeÃ±al de compra: {pattern[:30]}")
        
        # SeÃ±ales adicionales del historial
        if conversation_history:
            recent_messages = " ".join([msg.get("content", "") for msg in conversation_history[-5:]])
            recent_lower = recent_messages.lower()
            
            # Preguntas sobre producto especÃ­fico
            if re.search(r"\b(?:tiene|tienen|cantidad|disponible|stock)\b", recent_lower):
                purchase_score += 0.2
                signals_detected.append("Pregunta sobre disponibilidad")
            
            # MÃºltiples productos vistos
            if products_viewed and len(products_viewed) >= 3:
                purchase_score += 0.2
                signals_detected.append("MÃºltiples productos vistos")
            
            # Tiempo en sesiÃ³n largo (indica interÃ©s)
            if time_in_session and time_in_session > 5:  # MÃ¡s de 5 minutos
                purchase_score += 0.1
                signals_detected.append("Tiempo prolongado en sesiÃ³n")
        
        # 2. Detectar urgencia
        urgency_level = UrgencyLevel.NONE
        for level, patterns in self.urgency_patterns.items():
            for pattern in patterns:
                if re.search(pattern, message_lower, re.IGNORECASE):
                    if level == "critical":
                        urgency_level = UrgencyLevel.CRITICAL
                        urgency_score = 1.0
                    elif level == "high" and urgency_score < 0.8:
                        urgency_level = UrgencyLevel.HIGH
                        urgency_score = 0.8
                    elif level == "medium" and urgency_score < 0.5:
                        urgency_level = UrgencyLevel.MEDIUM
                        urgency_score = 0.5
                    signals_detected.append(f"Urgencia {level}")
        
        # 3. Detectar seÃ±ales de abandono
        for pattern in self.abandonment_signals:
            if re.search(pattern, message_lower, re.IGNORECASE):
                abandonment_score += 0.3
                signals_detected.append("SeÃ±al de abandono detectada")
        
        # Normalizar scores
        purchase_score = min(1.0, purchase_score)
        abandonment_score = min(1.0, abandonment_score)
        
        # Determinar nivel de seÃ±al de compra
        if purchase_score >= 0.7:
            purchase_signal = PurchaseSignal.HIGH
        elif purchase_score >= 0.4:
            purchase_signal = PurchaseSignal.MEDIUM
        elif purchase_score > 0:
            purchase_signal = PurchaseSignal.LOW
        else:
            purchase_signal = PurchaseSignal.NONE
        
        # Si hay urgencia pero no seÃ±al de compra, subir seÃ±al
        if urgency_score > 0.5 and purchase_signal == PurchaseSignal.NONE:
            purchase_signal = PurchaseSignal.MEDIUM
            purchase_score = 0.5
        
        # 4. Segmentar cliente
        segment = self._segment_customer(
            purchase_score, urgency_score, abandonment_score,
            user_profile, products_viewed
        )
        
        # 5. Calcular tiempo estimado de compra
        estimated_time = self._estimate_time_to_purchase(
            purchase_score, urgency_level, abandonment_score
        )
        
        # 6. Sugerir acciones
        suggested_actions = self._suggest_actions(
            purchase_signal, urgency_level, segment, abandonment_score
        )
        
        # Confidence basado en nÃºmero de seÃ±ales
        confidence = min(1.0, len(signals_detected) * 0.2 + 0.3)
        
        # 7. TRIGGER DE CIERRE: Detectar cuÃ¡ndo activar cierre proactivo (NIVEL DIOS) ðŸš€
        should_activate_closing = False
        closing_trigger_reason = ""
        
        # Extraer preguntas y objeciones del historial
        questions_asked = []
        objections_detected = []
        if conversation_history:
            for msg in conversation_history[-10:]:  # Ãšltimos 10 mensajes
                content_lower = msg.get("content", "").lower()
                # Detectar preguntas
                if "?" in msg.get("content", "") or any(word in content_lower for word in ["cuÃ¡nto", "cuÃ¡l", "quÃ©", "cÃ³mo", "cuÃ¡ndo"]):
                    questions_asked.append(msg.get("content", ""))
                # Detectar objeciones
                if any(word in content_lower for word in ["caro", "costoso", "dudo", "no estoy seguro", "pensar"]):
                    objections_detected.append(msg.get("content", ""))
        
        # Regla 1: SeÃ±al de compra alta + urgencia media/alta
        if purchase_signal == PurchaseSignal.HIGH and urgency_level in [UrgencyLevel.HIGH, UrgencyLevel.CRITICAL]:
            should_activate_closing = True
            closing_trigger_reason = "Cliente muestra alta intenciÃ³n de compra con urgencia"
        
        # Regla 2: Cliente preguntÃ³ por precio, garantÃ­a Y tiempo de envÃ­o (secuencia de compra)
        all_questions_text = " ".join(questions_asked).lower()
        if ("precio" in all_questions_text or "cuÃ¡nto" in all_questions_text) and \
           ("garantÃ­a" in all_questions_text or "garantizar" in all_questions_text) and \
           any(keyword in all_questions_text for keyword in ["envÃ­o", "entrega", "cuÃ¡ndo llega", "tiempo"]):
            should_activate_closing = True
            closing_trigger_reason = "Cliente completÃ³ secuencia de preguntas de compra (precio, garantÃ­a, envÃ­o)"
        
        # Regla 3: Segmento hot_lead con confianza alta
        if segment == CustomerSegment.HOT_LEAD and confidence >= 0.7:
            should_activate_closing = True
            closing_trigger_reason = "Lead caliente con alta confianza - momento Ã³ptimo para cerrar"
        
        # Regla 4: MencionÃ³ objeciones pero luego preguntÃ³ por detalles prÃ¡cticos (superÃ³ objeciones)
        if len(objections_detected) > 0 and len(questions_asked) >= 2:
            # Si tiene objeciones pero sigue preguntando, estÃ¡ considerando comprar
            should_activate_closing = True
            closing_trigger_reason = "Cliente superÃ³ objeciones iniciales y muestra interÃ©s real"
        
        return BehaviorAnalysis(
            purchase_signal=purchase_signal,
            urgency_level=urgency_level,
            segment=segment,
            confidence=confidence,
            signals_detected=signals_detected,
            suggested_actions=suggested_actions,
            risk_of_abandonment=abandonment_score,
            estimated_time_to_purchase=estimated_time,
            should_activate_closing=should_activate_closing,
            closing_trigger_reason=closing_trigger_reason
        )
    
    def _segment_customer(self,
                         purchase_score: float,
                         urgency_score: float,
                         abandonment_score: float,
                         user_profile: Optional[Dict],
                         products_viewed: Optional[List[str]]) -> CustomerSegment:
        """Segmenta al cliente basÃ¡ndose en el anÃ¡lisis."""
        # Cliente recurrente
        if user_profile and user_profile.get("is_returning", False):
            return CustomerSegment.RETURNING_CUSTOMER
        
        # Hot lead (listo para comprar)
        if purchase_score >= 0.7 and urgency_score >= 0.5:
            return CustomerSegment.HOT_LEAD
        
        # Price shopper (solo busca precio)
        if abandonment_score > 0.6 and purchase_score > 0.3:
            return CustomerSegment.PRICE_SHOPPER
        
        # Warm lead
        if purchase_score >= 0.4:
            return CustomerSegment.WARM_LEAD
        
        # Researcher (compara opciones)
        if products_viewed and len(products_viewed) >= 3:
            return CustomerSegment.RESEARCHER
        
        # Cold lead (explorando)
        return CustomerSegment.COLD_LEAD
    
    def _estimate_time_to_purchase(self,
                                   purchase_score: float,
                                   urgency: UrgencyLevel,
                                   abandonment_score: float) -> Optional[str]:
        """Estima tiempo hasta la compra."""
        if abandonment_score > 0.7:
            return None  # No comprarÃ¡
        
        if urgency == UrgencyLevel.CRITICAL:
            return "immediate"
        elif urgency == UrgencyLevel.HIGH or purchase_score >= 0.7:
            return "this_week"
        elif purchase_score >= 0.4:
            return "this_month"
        else:
            return "unknown"
    
    def _suggest_actions(self,
                        purchase_signal: PurchaseSignal,
                        urgency: UrgencyLevel,
                        segment: CustomerSegment,
                        abandonment_score: float) -> List[str]:
        """Sugiere acciones basÃ¡ndose en el anÃ¡lisis."""
        actions = []
        
        # Si hay riesgo de abandono
        if abandonment_score > 0.5:
            actions.append("address_objections")  # Abordar objeciones
            actions.append("offer_incentive")  # Ofrecer incentivo
        
        # Si es hot lead
        if purchase_signal == PurchaseSignal.HIGH:
            actions.append("close_sale")  # Cerrar venta
            if urgency == UrgencyLevel.CRITICAL:
                actions.append("create_urgency")  # Crear urgencia adicional
        
        # Si es warm lead
        if purchase_signal == PurchaseSignal.MEDIUM:
            actions.append("provide_more_info")  # Dar mÃ¡s informaciÃ³n
            actions.append("suggest_complementary")  # Sugerir productos complementarios
        
        # Si es price shopper
        if segment == CustomerSegment.PRICE_SHOPPER:
            actions.append("highlight_value")  # Destacar valor
            actions.append("offer_discount")  # Ofrecer descuento
        
        # Si es researcher
        if segment == CustomerSegment.RESEARCHER:
            actions.append("compare_options")  # Comparar opciones
            actions.append("social_proof")  # Prueba social
        
        return actions


