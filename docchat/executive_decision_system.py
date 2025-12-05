"""
Sistema Ejecutivo de Decisión Inteligente
Transforma analizador genérico → Sistema Ejecutivo de Decisión ($1999+/mes)

6 CAPAS PROFESIONALES:
1. EntityIdentifier - Identifica "qué documento es de quién"
2. AnswerEngine - Respuestas estructuradas ejecutivas
3. PriorityEngine - Priorización inteligente ROJO/AMARILLO/VERDE
4. ImpactCalculator - Cálculo impacto financiero cuantificado
5. ActionGenerator - Acciones específicas y accionables
6. ValidationSystem - Validación cruzada y corrección automática
"""

from __future__ import annotations

import json
import re
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta, date
from pathlib import Path


@dataclass
class EntityInfo:
    """Información de entidad detectada en documento."""
    entity_type: str  # "empresa_principal", "cliente_externo", "proveedor_externo", "regulador", "socio_comercial"
    entity_name: Optional[str] = None
    confidence: float = 0.0  # 0.0-1.0
    signals: List[str] = None
    
    def __post_init__(self):
        if self.signals is None:
            self.signals = []


@dataclass
class ExtractedItem:
    """Item extraído con metadatos completos."""
    item_type: str  # "factura", "contrato", "estado_financiero", etc.
    item_id: str  # número de factura, ID de contrato, etc.
    entity: str  # "empresa_principal" o entidad externa
    fecha_emision: Optional[str] = None
    fecha_vencimiento: Optional[str] = None
    monto: Optional[float] = None
    moneda: Optional[str] = None
    estado: Optional[str] = None  # "vencido", "pendiente", "al_dia", etc.
    cliente_proveedor: Optional[str] = None
    dias_hasta_vencimiento: Optional[int] = None
    prioridad: Optional[str] = None  # "ROJO", "AMARILLO", "VERDE"
    confianza: float = 0.0  # Confianza en la extracción
    fuente: Optional[str] = None  # Archivo y página
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        
        # Calcular días hasta vencimiento si hay fechas
        if self.fecha_vencimiento and not self.dias_hasta_vencimiento:
            try:
                fecha_venc = datetime.strptime(self.fecha_vencimiento, "%Y-%m-%d")
                hoy = datetime.now()
                self.dias_hasta_vencimiento = (fecha_venc - hoy).days
            except:
                pass


@dataclass
class StructuredAnswer:
    """Respuesta estructurada ejecutiva."""
    respuesta_directa: str
    detalle_contratos: List[ExtractedItem]
    detalle_facturas: List[ExtractedItem]
    acciones_priorizadas: Dict[str, List[str]]
    impacto_financiero: Dict[str, Any]
    recomendaciones: List[str]
    fuentes: List[str]
    confianza_general: float = 0.0
    validaciones: List[str] = None
    
    def __post_init__(self):
        if self.validaciones is None:
            self.validaciones = []


class EntityIdentifier:
    """
    CAPA 1: Identificación Inteligente de Entidades
    Detecta si documento representa "YO" vs "CLIENTE" vs "PROVEEDOR"
    """
    
    def __init__(self, config: Any):
        self.config = config
        
        # Señales de empresa principal (YO)
        self.señales_empresa_principal = [
            "nuestra empresa", "nuestros estados", "nuestras facturas",
            "facturas emitidas por nosotros", "contratos firmados por nosotros",
            "balance general", "estado de resultados", "nuestro balance",
            "mis facturas", "mis contratos", "mi empresa",
            "empresa principal", "entidad principal"
        ]
        
        # Señales de cliente externo
        self.señales_cliente = [
            "financial statements of", "annual report of",
            "estados financieros de", "reporte anual de",
            "balance sheet of", "income statement of",
            "cliente:", "customer:", "client:"
        ]
        
        # Señales de proveedor externo
        self.señales_proveedor = [
            "invoice from", "factura de", "bill from",
            "proveedor:", "supplier:", "vendor:",
            "payment to", "pago a"
        ]
        
        # Señales de regulador
        self.señales_regulador = [
            "regulación", "regulation", "normativa",
            "gobierno", "government", "ministerio",
            "superintendencia", "comisión"
        ]
    
    def identify_entity(self, documento: Dict[str, Any]) -> EntityInfo:
        """
        Identifica la entidad del documento.
        
        Returns:
            EntityInfo con tipo de entidad y confianza
        """
        text = documento.get("text", "").lower()
        file_name = documento.get("file_name", "").lower()
        metadata = documento.get("metadata", {})
        
        # Combinar texto y nombre de archivo
        combined_text = f"{text} {file_name}"
        
        # Detectar señales
        señales_empresa = sum(1 for señal in self.señales_empresa_principal if señal in combined_text)
        señales_cliente = sum(1 for señal in self.señales_cliente if señal in combined_text)
        señales_proveedor = sum(1 for señal in self.señales_proveedor if señal in combined_text)
        señales_regulador = sum(1 for señal in self.señales_regulador if señal in combined_text)
        
        # Lógica de decisión
        if señales_empresa > 0 and señales_empresa >= max(señales_cliente, señales_proveedor, señales_regulador):
            # Es empresa principal
            confidence = min(0.9, 0.5 + (señales_empresa * 0.1))
            return EntityInfo(
                entity_type="empresa_principal",
                confidence=confidence,
                signals=[s for s in self.señales_empresa_principal if s in combined_text]
            )
        elif señales_cliente > 0:
            # Extraer nombre del cliente
            cliente_name = self._extract_entity_name(text, "cliente")
            return EntityInfo(
                entity_type="cliente_externo",
                entity_name=cliente_name,
                confidence=0.7 + (señales_cliente * 0.1),
                signals=[s for s in self.señales_cliente if s in combined_text]
            )
        elif señales_proveedor > 0:
            proveedor_name = self._extract_entity_name(text, "proveedor")
            return EntityInfo(
                entity_type="proveedor_externo",
                entity_name=proveedor_name,
                confidence=0.7 + (señales_proveedor * 0.1),
                signals=[s for s in self.señales_proveedor if s in combined_text]
            )
        elif señales_regulador > 0:
            return EntityInfo(
                entity_type="regulador",
                confidence=0.8,
                signals=[s for s in self.señales_regulador if s in combined_text]
            )
        else:
            # Por defecto, si no hay señales claras, asumir empresa principal
            # (para documentos internos sin señales explícitas)
            return EntityInfo(
                entity_type="empresa_principal",
                confidence=0.5,
                signals=[]
            )
    
    def _extract_entity_name(self, text: str, entity_type: str) -> Optional[str]:
        """Extrae nombre de entidad del texto."""
        # Buscar patrones como "cliente: Nestlé" o "supplier: Black Sea Bank"
        patterns = [
            rf"{entity_type}[:]\s*([A-Z][A-Za-z\s&]+)",
            rf"{entity_type}\s+([A-Z][A-Za-z\s&]+)",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return None


class PriorityEngine:
    """
    CAPA 3: Priorización Inteligente
    Prioriza items por ROJO/AMARILLO/VERDE con reglas específicas
    """
    
    def __init__(self):
        self.prioridad_rules = {
            "ROJO": {
                "condiciones": [
                    lambda item: item.dias_hasta_vencimiento is not None and item.dias_hasta_vencimiento < 0,  # Vencido
                    lambda item: item.estado == "vencido",
                    lambda item: item.monto and item.monto > 10000,  # Monto alto
                    lambda item: item.metadata.get("cliente_estrategico") == True,
                ],
                "accion": "RESOLVER HOY",
                "responsable": "CEO/Finanzas",
                "color": "🔴"
            },
            "AMARILLO": {
                "condiciones": [
                    lambda item: item.dias_hasta_vencimiento is not None and 0 <= item.dias_hasta_vencimiento <= 7,
                    lambda item: item.monto and 5000 < item.monto <= 10000,
                ],
                "accion": "RESOLVER ESTA SEMANA",
                "responsable": "Gerente",
                "color": "🟡"
            },
            "VERDE": {
                "condiciones": [
                    lambda item: item.dias_hasta_vencimiento is not None and item.dias_hasta_vencimiento > 7,
                    lambda item: item.monto and item.monto <= 5000,
                    lambda item: item.estado == "al_dia",
                ],
                "accion": "MONITOREAR",
                "responsable": "Equipo",
                "color": "🟢"
            }
        }
    
    def priorize_items(self, items: List[ExtractedItem]) -> List[ExtractedItem]:
        """Prioriza items según reglas."""
        for item in items:
            prioridad = self._calculate_priority(item)
            item.prioridad = prioridad
        
        # Ordenar por prioridad (ROJO primero)
        priority_order = {"ROJO": 0, "AMARILLO": 1, "VERDE": 2}
        items.sort(key=lambda x: priority_order.get(x.prioridad, 3))
        
        return items
    
    def _calculate_priority(self, item: ExtractedItem) -> str:
        """Calcula prioridad de un item."""
        # Verificar condiciones en orden de severidad
        for prioridad_name, rules in self.prioridad_rules.items():
            for condition in rules["condiciones"]:
                try:
                    if condition(item):
                        return prioridad_name
                except:
                    continue
        
        # Default: VERDE
        return "VERDE"


class ImpactCalculator:
    """
    CAPA 4: Cuantificación de Impacto
    Calcula impacto financiero con números reales
    """
    
    def calculate_financial_impact(self, items: List[ExtractedItem]) -> Dict[str, Any]:
        """Calcula impacto financiero cuantificado."""
        # Separar por estado
        vencidos = [item for item in items if item.dias_hasta_vencimiento is not None and item.dias_hasta_vencimiento < 0]
        proximos = [item for item in items if item.dias_hasta_vencimiento is not None and 0 <= item.dias_hasta_vencimiento <= 30]
        
        # Calcular montos (normalizar a USD si es necesario)
        riesgo_inmediato = sum(self._normalize_amount(item.monto, item.moneda) for item in vencidos if item.monto)
        riesgo_proximo = sum(self._normalize_amount(item.monto, item.moneda) for item in proximos if item.monto)
        
        # Estimar multas (10-20% típico)
        multas_estimadas_min = riesgo_inmediato * 0.10
        multas_estimadas_max = riesgo_inmediato * 0.20
        
        # Calcular costo de oportunidad (interés perdido, etc.)
        costo_oportunidad = self._calculate_opportunity_cost(items)
        
        # Impacto relacional (clientes estratégicos)
        impacto_relacional = self._assess_relationship_impact(items)
        
        return {
            "riesgo_inmediato": riesgo_inmediato,
            "riesgo_proximo": riesgo_proximo,
            "multas_estimadas_min": multas_estimadas_min,
            "multas_estimadas_max": multas_estimadas_max,
            "costo_oportunidad": costo_oportunidad,
            "impacto_relacional": impacto_relacional,
            "total_exposicion": riesgo_inmediato + riesgo_proximo + multas_estimadas_max,
            "items_vencidos": len(vencidos),
            "items_proximos": len(proximos)
        }
    
    def _normalize_amount(self, amount: Optional[float], currency: Optional[str]) -> float:
        """Normaliza montos a USD (simplificado)."""
        if not amount:
            return 0.0
        
        # Tasas de cambio simplificadas (en producción usar API)
        rates = {
            "USD": 1.0,
            "EUR": 1.1,
            "GBP": 1.25,
            "MXN": 0.06,
            "ARS": 0.001
        }
        
        rate = rates.get(currency or "USD", 1.0)
        return amount * rate
    
    def _calculate_opportunity_cost(self, items: List[ExtractedItem]) -> float:
        """Calcula costo de oportunidad."""
        # Simplificado: interés perdido por pagos tardíos
        return 0.0  # En producción calcular basado en tasas de interés
    
    def _assess_relationship_impact(self, items: List[ExtractedItem]) -> str:
        """Evalúa impacto en relaciones comerciales."""
        clientes_estrategicos_afectados = sum(
            1 for item in items 
            if item.metadata.get("cliente_estrategico") and item.estado == "vencido"
        )
        
        if clientes_estrategicos_afectados > 0:
            return f"⚠️ {clientes_estrategicos_afectados} cliente(s) estratégico(s) afectado(s)"
        return "✅ Sin impacto relacional crítico"


class ActionGenerator:
    """
    CAPA 5: Generación de Acciones
    Genera acciones específicas y accionables
    """
    
    def __init__(self, priority_engine: PriorityEngine):
        self.priority_engine = priority_engine
    
    def generate_actions(self, items_priorizados: List[ExtractedItem]) -> Dict[str, List[str]]:
        """Genera acciones priorizadas."""
        acciones = {
            "inmediatas": [],
            "corto_plazo": [],
            "preventivas": []
        }
        
        for item in items_priorizados:
            if item.prioridad == "ROJO":
                accion = self._generate_immediate_action(item)
                acciones["inmediatas"].append(accion)
            elif item.prioridad == "AMARILLO":
                accion = self._generate_short_term_action(item)
                acciones["corto_plazo"].append(accion)
            else:
                accion = self._generate_preventive_action(item)
                if accion:
                    acciones["preventivas"].append(accion)
        
        # Acciones preventivas generales
        if any(item.prioridad == "ROJO" for item in items_priorizados):
            acciones["preventivas"].append("Revisar política de cobranza para evitar vencimientos futuros")
            acciones["preventivas"].append("Implementar sistema de alertas automáticas para vencimientos")
        
        return acciones
    
    def _generate_immediate_action(self, item: ExtractedItem) -> str:
        """Genera acción inmediata para item ROJO."""
        if item.item_type == "factura":
            if item.cliente_proveedor:
                return f"HOY: Contactar a {item.cliente_proveedor} sobre {item.item_type} #{item.item_id} VENCIDA - ${item.monto:,.2f}"
            else:
                return f"HOY: Resolver {item.item_type} #{item.item_id} VENCIDA - ${item.monto:,.2f}"
        elif item.item_type == "contrato":
            return f"HOY: Revisar {item.item_type} {item.item_id} - Acción requerida inmediata"
        else:
            return f"HOY: Resolver {item.item_type} {item.item_id} - Prioridad máxima"
    
    def _generate_short_term_action(self, item: ExtractedItem) -> str:
        """Genera acción a corto plazo para item AMARILLO."""
        if item.fecha_vencimiento:
            return f"48H: Programar pago {item.item_type} #{item.item_id} antes de {item.fecha_vencimiento} - ${item.monto:,.2f}"
        else:
            return f"Esta semana: Revisar {item.item_type} #{item.item_id} - ${item.monto:,.2f}"
    
    def _generate_preventive_action(self, item: ExtractedItem) -> Optional[str]:
        """Genera acción preventiva para item VERDE."""
        if item.item_type == "contrato" and item.dias_hasta_vencimiento and item.dias_hasta_vencimiento > 7:
            return f"15 días antes: Revisar {item.item_type} {item.item_id} para renovación"
        return None


class ValidationSystem:
    """
    CAPA 6: Validación y Corrección
    Valida datos extraídos y corrige errores automáticamente
    """
    
    def __init__(self):
        self.validation_rules = [
            self._validate_amount_reasonableness,
            self._validate_date_consistency,
            self._validate_entity_consistency,
        ]
    
    def validate_and_correct(self, items: List[ExtractedItem], entity_info: EntityInfo) -> Tuple[List[ExtractedItem], List[str]]:
        """
        Valida y corrige items extraídos.
        
        Returns:
            (items_corregidos, problemas_detectados)
        """
        problemas = []
        items_corregidos = []
        
        for item in items:
            # Validar item
            item_problemas = []
            for rule in self.validation_rules:
                problema = rule(item, entity_info)
                if problema:
                    item_problemas.append(problema)
            
            # Corregir si es posible
            item_corregido = self._auto_correct(item, item_problemas)
            items_corregidos.append(item_corregido)
            
            if item_problemas:
                problemas.extend(item_problemas)
        
        return items_corregidos, problemas
    
    def _validate_amount_reasonableness(self, item: ExtractedItem, entity_info: EntityInfo) -> Optional[str]:
        """Valida que montos sean razonables."""
        if entity_info.entity_type == "empresa_principal" and item.monto:
            # Si es empresa principal y monto > $1M, puede ser error
            if item.monto > 1000000:
                return f"⚠️ Monto muy alto (${item.monto:,.2f}) para empresa principal - Verificar si es correcto"
        return None
    
    def _validate_date_consistency(self, item: ExtractedItem, entity_info: EntityInfo) -> Optional[str]:
        """Valida consistencia de fechas."""
        if item.fecha_emision and item.fecha_vencimiento:
            try:
                fecha_emi = datetime.strptime(item.fecha_emision, "%Y-%m-%d")
                fecha_venc = datetime.strptime(item.fecha_vencimiento, "%Y-%m-%d")
                if fecha_venc < fecha_emi:
                    return f"⚠️ Fecha vencimiento ({item.fecha_vencimiento}) anterior a emisión ({item.fecha_emision})"
            except:
                pass
        return None
    
    def _validate_entity_consistency(self, item: ExtractedItem, entity_info: EntityInfo) -> Optional[str]:
        """Valida consistencia de entidad."""
        if entity_info.entity_type != "empresa_principal" and item.entity == "empresa_principal":
            return f"⚠️ Conflicto: Documento es {entity_info.entity_type} pero item marcado como empresa_principal"
        return None
    
    def _auto_correct(self, item: ExtractedItem, problemas: List[str]) -> ExtractedItem:
        """Corrige automáticamente errores detectados."""
        # Por ahora solo marca problemas, en producción podría corregir fechas, etc.
        if problemas:
            item.metadata["problemas_detectados"] = problemas
            item.metadata["requiere_revision"] = True
        
        return item
    
    def calculate_confidence(self, item: ExtractedItem) -> float:
        """Calcula confianza en la extracción del item."""
        confianza = 1.0
        
        # Reducir confianza si hay problemas
        if item.metadata.get("problemas_detectados"):
            confianza -= 0.3
        
        # Reducir si falta información crítica
        if not item.monto and item.item_type in ["factura", "contrato"]:
            confianza -= 0.2
        
        if not item.fecha_vencimiento and item.item_type in ["factura", "contrato"]:
            confianza -= 0.1
        
        return max(0.0, confianza)


class AnswerEngine:
    """
    CAPA 2: Motor de Respuestas Estructuradas
    Genera respuestas ejecutivas estructuradas y accionables
    """
    
    def __init__(
        self,
        priority_engine: PriorityEngine,
        impact_calculator: ImpactCalculator,
        action_generator: ActionGenerator,
        validation_system: ValidationSystem
    ):
        self.priority_engine = priority_engine
        self.impact_calculator = impact_calculator
        self.action_generator = action_generator
        self.validation_system = validation_system
    
    def parse_intention(self, pregunta: str) -> Dict[str, Any]:
        """Parsea la intención de la pregunta."""
        pregunta_lower = pregunta.lower()
        
        intención = {
            "tipo": "general",
            "documentos": [],
            "filtros": {}
        }
        
        # Detectar tipo de pregunta
        if any(word in pregunta_lower for word in ["vencer", "vencimiento", "vencen", "vencidos"]):
            intención["tipo"] = "vencimientos"
        
        if any(word in pregunta_lower for word in ["contrato", "contratos"]):
            intención["documentos"].append("contratos")
        
        if any(word in pregunta_lower for word in ["factura", "facturas", "invoice"]):
            intención["documentos"].append("facturas")
        
        # Detectar filtros temporales
        if "febrero" in pregunta_lower or "february" in pregunta_lower:
            intención["filtros"]["mes"] = 2
        
        if "marzo" in pregunta_lower or "march" in pregunta_lower:
            intención["filtros"]["mes"] = 3
        
        # Detectar filtros de monto
        if "mayor a" in pregunta_lower or ">" in pregunta_lower:
            # Extraer monto
            match = re.search(r'(\d+[.,]?\d*)', pregunta_lower)
            if match:
                monto_str = match.group(1).replace(",", "").replace(".", "")
                intención["filtros"]["monto_minimo"] = float(monto_str)
        
        return intención
    
    def filter_relevant_docs(
        self,
        documentos: List[Dict[str, Any]],
        intención: Dict[str, Any],
        entity_identifier: EntityIdentifier
    ) -> List[Dict[str, Any]]:
        """Filtra documentos relevantes SOLO de empresa principal."""
        relevantes = []
        
        for doc in documentos:
            # Identificar entidad
            entity_info = entity_identifier.identify_entity(doc)
            
            # SOLO incluir documentos de empresa principal
            if entity_info.entity_type != "empresa_principal":
                continue
            
            # Verificar si es tipo de documento relevante
            doc_type = doc.get("document_type", "").lower()
            if intención["documentos"]:
                if not any(tipo in doc_type for tipo in intención["documentos"]):
                    continue
            
            relevantes.append(doc)
        
        return relevantes
    
    def extract_specific_info(
        self,
        documentos_relevantes: List[Dict[str, Any]],
        intención: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Extrae información específica según intención."""
        items = []
        
        for doc in documentos_relevantes:
            # Extraer items del documento según tipo
            if "factura" in doc.get("document_type", "").lower():
                facturas = self._extract_facturas(doc, intención)
                items.extend(facturas)
            elif "contrato" in doc.get("document_type", "").lower():
                contratos = self._extract_contratos(doc, intención)
                items.extend(contratos)
        
        return {
            "contratos": [item for item in items if item.item_type == "contrato"],
            "facturas": [item for item in items if item.item_type == "factura"],
            "todos": items
        }
    
    def _extract_facturas(self, doc: Dict[str, Any], intención: Dict[str, Any]) -> List[ExtractedItem]:
        """Extrae facturas del documento con extracción robusta del texto."""
        items = []
        text = doc.get("text", "").lower()
        file_name = doc.get("file_name", "N/A")
        
        # Primero intentar usar datos estructurados si existen
        structured_data = doc.get("structured_data")
        if structured_data:
            extracted_fields = structured_data.get("extracted_fields", {})
            
            # Si hay múltiples facturas en extracted_fields (lista o dict anidado)
            if isinstance(extracted_fields, dict):
                # Buscar facturas individuales
                facturas_list = extracted_fields.get("facturas", [])
                if not facturas_list and "numero_factura" in extracted_fields:
                    # Una sola factura
                    facturas_list = [extracted_fields]
                
                for factura_data in facturas_list:
                    if isinstance(factura_data, dict):
                        item = self._create_factura_item(factura_data, file_name)
                        if item and self._matches_intention(item, intención):
                            items.append(item)
        
        # Si no hay datos estructurados o no se encontraron facturas, extraer del texto directamente
        if not items:
            items.extend(self._extract_facturas_from_text(text, file_name, intención))
        
        return items
    
    def _create_factura_item(self, factura_data: Dict[str, Any], file_name: str) -> Optional[ExtractedItem]:
        """Crea un ExtractedItem de factura desde datos estructurados."""
        try:
            # Normalizar nombres de campos
            numero = factura_data.get("numero_factura") or factura_data.get("numero") or factura_data.get("factura") or factura_data.get("id")
            fecha_venc = factura_data.get("fecha_vencimiento") or factura_data.get("vencimiento") or factura_data.get("fecha_venc")
            fecha_emi = factura_data.get("fecha_emision") or factura_data.get("emision") or factura_data.get("fecha")
            monto = factura_data.get("monto_total") or factura_data.get("monto") or factura_data.get("deuda_total") or factura_data.get("importe")
            estado_raw = factura_data.get("estado") or factura_data.get("status") or "pendiente"
            
            # Normalizar estado
            estado_raw_lower = str(estado_raw).lower()
            if "vencido" in estado_raw_lower or "vencida" in estado_raw_lower or "venc" in estado_raw_lower:
                estado = "vencido"
            elif "pagado" in estado_raw_lower or "pago" in estado_raw_lower or "pagada" in estado_raw_lower:
                estado = "pagado"
            elif "pendiente" in estado_raw_lower or "pend" in estado_raw_lower:
                estado = "pendiente"
            else:
                estado = "pendiente"  # Default
            
            # Convertir monto a float si es string
            if monto:
                if isinstance(monto, str):
                    # Limpiar string: remover $, comas, espacios
                    monto_clean = re.sub(r'[^\d.]', '', monto)
                    try:
                        monto = float(monto_clean)
                    except:
                        monto = None
                elif not isinstance(monto, (int, float)):
                    monto = None
            
            # Parsear fechas
            fecha_venc_parsed = self._parse_date(fecha_venc) if fecha_venc else None
            fecha_emi_parsed = self._parse_date(fecha_emi) if fecha_emi else None
            
            # Calcular días hasta vencimiento
            dias_hasta_venc = None
            if fecha_venc_parsed:
                try:
                    hoy = datetime.now().date()
                    dias_hasta_venc = (fecha_venc_parsed - hoy).days
                    # Si está vencido, actualizar estado
                    if dias_hasta_venc < 0 and estado != "pagado":
                        estado = "vencido"
                except:
                    pass
            
            return ExtractedItem(
                item_type="factura",
                item_id=str(numero) if numero else "N/A",
                entity="empresa_principal",
                fecha_emision=fecha_emi_parsed.strftime("%Y-%m-%d") if fecha_emi_parsed else None,
                fecha_vencimiento=fecha_venc_parsed.strftime("%Y-%m-%d") if fecha_venc_parsed else None,
                monto=monto,
                moneda=factura_data.get("moneda", "USD"),
                estado=estado,
                cliente_proveedor=factura_data.get("cliente") or factura_data.get("proveedor") or factura_data.get("concepto"),
                dias_hasta_vencimiento=dias_hasta_venc,
                fuente=file_name,
                confianza=0.9  # Alta confianza si viene de datos estructurados
            )
        except Exception as e:
            print(f"⚠️ Error creando item de factura: {e}")
            return None
    
    def _parse_date(self, date_str: Any) -> Optional[datetime.date]:
        """Parsea una fecha desde string en varios formatos."""
        if not date_str:
            return None
        
        date_str = str(date_str).strip()
        
        # Formatos comunes
        formats = [
            "%Y-%m-%d",
            "%d-%m-%Y",
            "%d/%m/%Y",
            "%m/%d/%Y",
            "%Y/%m/%d",
            "%d-%m-%y",
            "%d/%m/%y",
            "%d-%b-%Y",
            "%d-%B-%Y",
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt).date()
            except:
                continue
        
        # Intentar extraer fecha con regex (ej: "10-nov-2025")
        date_patterns = [
            r'(\d{1,2})[-/](\d{1,2})[-/](\d{4})',  # DD-MM-YYYY
            r'(\d{1,2})[-/](\w{3,})[-/](\d{4})',  # DD-Mon-YYYY
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, date_str, re.IGNORECASE)
            if match:
                try:
                    if len(match.groups()) == 3:
                        day, month, year = match.groups()
                        # Si month es texto, convertir a número
                        if not month.isdigit():
                            months = {
                                "ene": 1, "jan": 1, "feb": 2, "mar": 3, "abr": 4, "apr": 4,
                                "may": 5, "jun": 6, "jul": 7, "ago": 8, "aug": 8,
                                "sep": 9, "oct": 10, "nov": 11, "dic": 12, "dec": 12
                            }
                            month_num = months.get(month.lower()[:3], 1)
                        else:
                            month_num = int(month)
                        return datetime(int(year), month_num, int(day)).date()
                except:
                    continue
        
        return None
    
    def _extract_facturas_from_text(self, text: str, file_name: str, intención: Dict[str, Any]) -> List[ExtractedItem]:
        """Extrae facturas directamente del texto usando regex y patrones."""
        items = []
        
        # Patrones para encontrar facturas en texto
        # Formato común: Factura #XXX, fecha, monto, estado
        patterns = [
            # Factura #XXX, fecha, monto, estado
            r'factura\s*#?\s*(\d+)[^\n]*?(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})[^\n]*?(\$?\s*\d+[.,]?\d*)[^\n]*?(vencido|pendiente|pagado|vencida)',
            # Tabla: Factura | Fecha | Monto | Estado
            r'(\d+)\s+\|\s*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})\s+\|\s*(\$?\s*\d+[.,]?\d*)\s+\|\s*(vencido|pendiente|pagado|vencida)',
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                try:
                    numero = match.group(1)
                    fecha_str = match.group(2)
                    monto_str = match.group(3)
                    estado_str = match.group(4).lower()
                    
                    # Parsear monto
                    monto_clean = re.sub(r'[^\d.]', '', monto_str)
                    monto = float(monto_clean) if monto_clean else None
                    
                    # Parsear fecha
                    fecha_venc = self._parse_date(fecha_str)
                    
                    # Normalizar estado
                    if "vencido" in estado_str or "venc" in estado_str:
                        estado = "vencido"
                    elif "pagado" in estado_str or "pago" in estado_str:
                        estado = "pagado"
                    else:
                        estado = "pendiente"
                    
                    # Calcular días hasta vencimiento
                    dias_hasta_venc = None
                    if fecha_venc:
                        hoy = datetime.now().date()
                        dias_hasta_venc = (fecha_venc - hoy).days
                        if dias_hasta_venc < 0 and estado != "pagado":
                            estado = "vencido"
                    
                    item = ExtractedItem(
                        item_type="factura",
                        item_id=numero,
                        entity="empresa_principal",
                        fecha_vencimiento=fecha_venc.strftime("%Y-%m-%d") if fecha_venc else None,
                        monto=monto,
                        moneda="USD",
                        estado=estado,
                        dias_hasta_vencimiento=dias_hasta_venc,
                        fuente=file_name,
                        confianza=0.7  # Confianza media para extracción de texto
                    )
                    
                    if self._matches_intention(item, intención):
                        items.append(item)
                except Exception as e:
                    continue
        
        return items
    
    def _extract_contratos(self, doc: Dict[str, Any], intención: Dict[str, Any]) -> List[ExtractedItem]:
        """Extrae contratos del documento."""
        items = []
        
        structured_data = doc.get("structured_data")
        if structured_data:
            extracted_fields = structured_data.get("extracted_fields", {})
            
            item = ExtractedItem(
                item_type="contrato",
                item_id=extracted_fields.get("numero_contrato", "N/A"),
                entity="empresa_principal",
                fecha_emision=extracted_fields.get("fecha_inicio") or extracted_fields.get("fecha_firma"),
                fecha_vencimiento=extracted_fields.get("fecha_vencimiento") or extracted_fields.get("fecha_fin"),
                monto=extracted_fields.get("monto_total"),
                moneda=extracted_fields.get("moneda", "USD"),
                estado="activo",
                cliente_proveedor=extracted_fields.get("contraparte") or extracted_fields.get("parte_contratante"),
                fuente=f"{doc.get('file_name', 'N/A')}",
                confianza=0.8
            )
            
            if self._matches_intention(item, intención):
                items.append(item)
        
        return items
    
    def _matches_intention(self, item: ExtractedItem, intención: Dict[str, Any]) -> bool:
        """Verifica si item coincide con intención."""
        # Filtro por mes
        if "mes" in intención["filtros"]:
            if item.fecha_vencimiento:
                try:
                    fecha = datetime.strptime(item.fecha_vencimiento, "%Y-%m-%d")
                    if fecha.month != intención["filtros"]["mes"]:
                        return False
                except:
                    pass
        
        # Filtro por monto mínimo
        if "monto_minimo" in intención["filtros"]:
            if not item.monto or item.monto < intención["filtros"]["monto_minimo"]:
                return False
        
        return True
    
    def structure_executive_response(
        self,
        info_extraída: Dict[str, Any],
        intención: Dict[str, Any]
    ) -> StructuredAnswer:
        """Estructura respuesta ejecutiva completa."""
        # Priorizar items
        todos_items = info_extraída["todos"]
        items_priorizados = self.priority_engine.priorize_items(todos_items)
        
        # Validar y corregir
        entity_info = EntityInfo(entity_type="empresa_principal")  # Asumimos empresa principal
        items_validados, problemas = self.validation_system.validate_and_correct(items_priorizados, entity_info)
        
        # Calcular impacto
        impacto = self.impact_calculator.calculate_financial_impact(items_validados)
        
        # Generar acciones
        acciones = self.action_generator.generate_actions(items_validados)
        
        # Generar respuesta directa
        respuesta_directa = self._generate_direct_answer(items_validados, intención)
        
        # Generar recomendaciones
        recomendaciones = self._generate_recommendations(items_validados, impacto)
        
        # Extraer fuentes
        fuentes = list(set(item.fuente for item in items_validados if item.fuente))
        
        # Calcular confianza general
        confianza_general = sum(item.confianza for item in items_validados) / len(items_validados) if items_validados else 0.0
        
        return StructuredAnswer(
            respuesta_directa=respuesta_directa,
            detalle_contratos=[item for item in items_validados if item.item_type == "contrato"],
            detalle_facturas=[item for item in items_validados if item.item_type == "factura"],
            acciones_priorizadas=acciones,
            impacto_financiero=impacto,
            recomendaciones=recomendaciones,
            fuentes=fuentes,
            confianza_general=confianza_general,
            validaciones=problemas
        )
    
    def _generate_direct_answer(self, items: List[ExtractedItem], intención: Dict[str, Any]) -> str:
        """Genera respuesta directa a la pregunta, ultra concreta y sin relleno."""
        contratos = [item for item in items if item.item_type == "contrato"]
        facturas = [item for item in items if item.item_type == "factura"]
        
        if intención["tipo"] == "vencimientos":
            # Detectar vencidos y próximos con reglas claras
            vencidos = [
                item
                for item in items
                if (
                    (item.dias_hasta_vencimiento is not None and item.dias_hasta_vencimiento < 0)
                    or (item.estado == "vencido")
                )
            ]
            proximos = [
                item
                for item in items
                if (
                    item.dias_hasta_vencimiento is not None
                    and 0 <= item.dias_hasta_vencimiento <= 30
                )
            ]

            # Caso 1: no hay nada vencido ni próximo
            if not vencidos and not proximos:
                return (
                    "No se encontraron facturas ni contratos vencidos ni próximos a vencer "
                    "en los documentos analizados."
                )

            # Construir respuesta tipo “sí hay vencidos” con ejemplos concretos
            partes: List[str] = []

            if vencidos:
                # Total de riesgo inmediato solo sobre vencidos con monto
                riesgo_inmediato = sum(item.monto or 0.0 for item in vencidos if item.monto)

                partes.append("SÍ. Hay elementos VENCIDOS.")

                # Ejemplos concretos (máximo 3) priorizando facturas
                vencidos_ordenados = sorted(
                    vencidos,
                    key=lambda x: (x.item_type != "factura", -(x.monto or 0.0)),
                )
                ejemplos = []
                for item in vencidos_ordenados[:3]:
                    tipo = item.item_type.upper()
                    monto_txt = f"${item.monto:,.2f}" if item.monto else "monto no especificado"
                    fecha_txt = item.fecha_vencimiento or "fecha no especificada"
                    cliente_txt = f" - {item.cliente_proveedor}" if item.cliente_proveedor else ""
                    ejemplos.append(
                        f"{tipo} #{item.item_id} VENCIDA - {monto_txt} - venció el {fecha_txt}{cliente_txt}"
                    )

                partes.append("Ejemplos:")
                for ej in ejemplos:
                    partes.append(f"- {ej}")

                partes.append(
                    f"Riesgo directo aproximado (solo vencidos con monto): "
                    f"${riesgo_inmediato:,.2f}"
                )

            if proximos:
                partes.append(
                    f"Además hay {len(proximos)} elemento(s) próximos a vencer en los "
                    "próximos 30 días."
                )

            return " ".join(partes)
        else:
            # Respuesta general, pero manteniendo concreción básica
            if not contratos and not facturas:
                return "No se encontraron contratos ni facturas relevantes en los documentos analizados."
            return (
                f"Se encontraron {len(contratos)} contrato(s) y {len(facturas)} factura(s) "
                "relevantes en los documentos analizados."
            )
    
    def _generate_recommendations(self, items: List[ExtractedItem], impacto: Dict[str, Any]) -> List[str]:
        """Genera recomendaciones estratégicas."""
        recomendaciones = []
        
        if impacto["riesgo_inmediato"] > 0:
            recomendaciones.append(f"⚠️ Acción inmediata requerida: ${impacto['riesgo_inmediato']:,.2f} en riesgo")
        
        if impacto["items_vencidos"] > 0:
            recomendaciones.append(f"🔴 {impacto['items_vencidos']} items vencidos requieren atención HOY")
        
        if impacto["multas_estimadas_max"] > 0:
            recomendaciones.append(f"💰 Multas estimadas: ${impacto['multas_estimadas_min']:,.2f} - ${impacto['multas_estimadas_max']:,.2f}")
        
        return recomendaciones
    
    def format_executive_response(self, structured_answer: StructuredAnswer) -> str:
        """Formatea respuesta ejecutiva en markdown con estructura precisa y tablas."""
        output = []
        
        # Respuesta directa (ultra-corta)
        output.append(f"## 🎯 Respuesta Ejecutiva\n\n{structured_answer.respuesta_directa}\n\n")
        
        # TABLA DE FACTURAS/CONTRATOS (información clave)
        todos_items = structured_answer.detalle_facturas + structured_answer.detalle_contratos
        
        if todos_items:
            output.append("## 📊 Tabla de Información Clave\n\n")
            output.append("| Tipo | ID | Fecha Vencimiento | Monto | Estado | Días | Fuente |\n")
            output.append("|------|----|-------------------|-------|--------|------|--------|\n")
            
            for item in todos_items:
                tipo = item.item_type.upper()
                item_id = item.item_id or "N/A"
                fecha_venc = item.fecha_vencimiento or "N/A"
                monto = f"${item.monto:,.2f}" if item.monto else "N/A"
                estado = item.estado.upper() if item.estado else "N/A"
                dias = str(item.dias_hasta_vencimiento) if item.dias_hasta_vencimiento is not None else "N/A"
                fuente = Path(item.fuente).name if item.fuente else "N/A"
                
                output.append(f"| {tipo} | {item_id} | {fecha_venc} | {monto} | {estado} | {dias} | {fuente} |\n")
            
            output.append("\n")
        
        # Vencimientos identificados (solo si hay)
        vencidos = [item for item in todos_items if item.estado == "vencido" or (item.dias_hasta_vencimiento is not None and item.dias_hasta_vencimiento < 0)]
        proximos = [item for item in todos_items if item.dias_hasta_vencimiento is not None and 0 <= item.dias_hasta_vencimiento <= 30]
        
        if vencidos or proximos:
            output.append("## 📅 Vencimientos Identificados\n\n")
            
            if vencidos:
                output.append("### 🔴 VENCIDOS (ACCIÓN INMEDIATA)\n\n")
                for item in vencidos:
                    output.append(f"• **{item.item_type.upper()} #{item.item_id}**: ")
                    output.append(f"VENCIDO")
                    if item.monto:
                        output.append(f" - ${item.monto:,.2f}")
                    if item.fecha_vencimiento:
                        output.append(f" (venció {item.fecha_vencimiento})")
                    if item.cliente_proveedor:
                        output.append(f" - {item.cliente_proveedor}")
                    output.append(f"\n  📄 Fuente: {Path(item.fuente).name if item.fuente else 'N/A'}\n\n")
            
            if proximos:
                output.append("### 🟡 PRÓXIMOS A VENCER (ESTA SEMANA)\n\n")
                for item in proximos:
                    output.append(f"• **{item.item_type.upper()} #{item.item_id}**: ")
                    output.append(f"PENDIENTE")
                    if item.monto:
                        output.append(f" - ${item.monto:,.2f}")
                    if item.fecha_vencimiento:
                        output.append(f" (vence {item.fecha_vencimiento})")
                    if item.dias_hasta_vencimiento is not None:
                        output.append(f" ({item.dias_hasta_vencimiento} días)")
                    output.append(f"\n  📄 Fuente: {Path(item.fuente).name if item.fuente else 'N/A'}\n\n")
        else:
            # Si no hay vencidos, ser claro
            output.append("## 📅 Vencimientos\n\n")
            output.append("✅ **No se encontraron facturas o contratos vencidos en los documentos analizados.**\n\n")
        
        # Impacto financiero (solo si hay números reales)
        impacto = structured_answer.impacto_financiero
        if impacto["riesgo_inmediato"] > 0 or impacto["riesgo_proximo"] > 0:
            output.append("## 💰 Impacto Financiero\n\n")
            if impacto["riesgo_inmediato"] > 0:
                output.append(f"• **Riesgo inmediato (vencidos)**: ${impacto['riesgo_inmediato']:,.2f}\n")
                if impacto["multas_estimadas_max"] > 0:
                    output.append(f"• **Multas estimadas**: ${impacto['multas_estimadas_min']:,.2f} - ${impacto['multas_estimadas_max']:,.2f}\n")
            if impacto["riesgo_proximo"] > 0:
                output.append(f"• **Riesgo próximo (30 días)**: ${impacto['riesgo_proximo']:,.2f}\n")
            output.append(f"• **Total exposición**: ${impacto['total_exposicion']:,.2f}\n\n")
        else:
            output.append("## 💰 Impacto Financiero\n\n")
            output.append("• **Riesgo inmediato**: $0.00\n")
            output.append("• **Riesgo próximo**: $0.00\n")
            output.append("• **Total exposición**: $0.00\n\n")
        
        # Acciones sugeridas (solo si hay acciones reales)
        acciones = structured_answer.acciones_priorizadas
        if acciones.get("inmediatas") or acciones.get("corto_plazo"):
            output.append("## 🤖 Acciones Recomendadas\n\n")
            if acciones.get("inmediatas"):
                for i, accion in enumerate(acciones["inmediatas"][:5], 1):
                    output.append(f"{i}. **HOY**: {accion}\n")
            if acciones.get("corto_plazo"):
                for i, accion in enumerate(acciones["corto_plazo"][:5], len(acciones.get("inmediatas", [])) + 1):
                    output.append(f"{i}. **48H**: {accion}\n")
            output.append("\n")
        
        # Fuentes (precisas)
        if structured_answer.fuentes:
            output.append("## 📚 Fuentes\n\n")
            for fuente in structured_answer.fuentes[:10]:
                fuente_name = Path(fuente).name if fuente else "N/A"
                output.append(f"• {fuente_name}\n")
            output.append("\n")
        
        # Validaciones (solo si hay problemas reales)
        if structured_answer.validaciones:
            output.append("## ⚠️ Validaciones\n\n")
            for validacion in structured_answer.validaciones[:5]:
                output.append(f"• {validacion}\n")
            output.append("\n")
        
        return "\n".join(output)

