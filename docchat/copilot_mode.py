"""
Copilot Mode - Sistema Empresarial de Rendimiento Supremo para Análisis Legal Masivo
======================================================================================

Sistema diseñado específicamente para empresas que manejan millones de PDFs con:

1. COMPLIANCE Y RIESGO CONTRACTUAL AUTOMÁTICO
   - Detecta cláusulas peligrosas automáticamente
   - Señala vencimientos y fechas críticas
   - Resalta obligaciones legales
   - Advierte multas/costos ocultos
   - Compara versiones de contratos

2. ANÁLISIS DE DUE DILIGENCE PARA M&A
   - Resumen rápido de millones de PDFs
   - Detecta pasivos, riesgos, excepciones
   - Genera reportes listos para inversores

3. EXTRACTORES DE KPI + TABLAS + DATOS ACCIONABLES
   - Transforma PDFs en Excel, Dashboards, Integraciones CRM
   - Ventas por región, Cláusulas de pago, Plazos por contrato
   - Excepciones por cliente

4. ALERTAS Y MONITOREO AUTOMÁTICO CONTINUO
   - Escanea nuevos PDFs automáticamente
   - Genera alertas cuando hay riesgo
   - Reporta cambios críticos

💰 Modelo de negocio: SaaS + Auditorías pagadas
Precio típico: USD 5k-500k / empresa por año
"""

from __future__ import annotations

from typing import List, Dict, Any, Optional, Iterator, Tuple
from datetime import datetime, timedelta
from pathlib import Path
import json
import hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, asdict
from enum import Enum
import re

from langchain_core.documents import Document
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI

from .config import AppConfig
from .document_processor import DocumentProcessor
try:
    from docling.document_converter import DocumentConverter
    DOCLING_AVAILABLE = True
except ImportError:
    DOCLING_AVAILABLE = False
    DocumentConverter = None
from .retriever_builder import RetrieverBuilder
from .workflow import AgentWorkflow
from .memory import MemoryStore, ContextManager
from .advanced_agent import AdvancedAutonomousAgent
from .tools import (
    EmailTool, ReportTool, DatabaseTool, PresentationTool,
    IntegrationTool, TableAnalysisTool, SchedulerTool
)


class RiskLevel(Enum):
    """Niveles de riesgo para cláusulas y obligaciones."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class ClauseType(Enum):
    """Tipos de cláusulas legales comunes."""
    TERMINATION = "termination"
    LIABILITY = "liability"
    INDEMNIFICATION = "indemnification"
    CONFIDENTIALITY = "confidentiality"
    NON_COMPETE = "non_compete"
    PAYMENT = "payment"
    WARRANTIES = "warranties"
    LIMITATION_OF_LIABILITY = "limitation_of_liability"
    INSURANCE = "insurance"
    ASSIGNMENT = "assignment"
    GOVERNING_LAW = "governing_law"
    DISPUTE_RESOLUTION = "dispute_resolution"
    MODIFICATION = "modification"
    FORCE_MAJEURE = "force_majeure"
    DEFAULT = "default"


@dataclass
class DangerousClause:
    """Representa una cláusula peligrosa detectada."""
    clause_type: str
    risk_level: RiskLevel
    description: str
    location: str  # Ubicación en el documento
    recommendation: str
    potential_cost: Optional[str] = None
    legal_implications: List[str] = None
    
    def __post_init__(self):
        if self.legal_implications is None:
            self.legal_implications = []


@dataclass
class CriticalDate:
    """Representa una fecha crítica en el documento."""
    date: str
    date_type: str  # vencimiento, plazo, expiracion, limite, renewal
    description: str
    days_until: int
    risk_level: RiskLevel
    action_required: str
    parties_involved: List[str] = None
    
    def __post_init__(self):
        if self.parties_involved is None:
            self.parties_involved = []


@dataclass
class LegalObligation:
    """Representa una obligación legal identificada."""
    obligation_type: str
    description: str
    responsible_party: str
    deadline: Optional[str] = None
    risk_level: RiskLevel = RiskLevel.MEDIUM
    compliance_status: str = "pending"  # pending, in_progress, completed, overdue
    penalties: List[str] = None
    
    def __post_init__(self):
        if self.penalties is None:
            self.penalties = []


@dataclass
class HiddenCost:
    """Representa un costo oculto detectado."""
    cost_type: str
    amount: Optional[str] = None
    description: str = ""
    trigger_conditions: List[str] = None
    risk_level: RiskLevel = RiskLevel.MEDIUM
    frequency: str = "one_time"  # one_time, monthly, annual, variable
    
    def __post_init__(self):
        if self.trigger_conditions is None:
            self.trigger_conditions = []


@dataclass
class DueDiligenceFinding:
    """Hallazgo en análisis de due diligence."""
    finding_type: str  # liability, risk, exception, compliance_issue
    severity: RiskLevel
    description: str
    location: str
    recommendation: str
    related_clauses: List[str] = None
    financial_impact: Optional[str] = None
    
    def __post_init__(self):
        if self.related_clauses is None:
            self.related_clauses = []


@dataclass
class ContractVersionDiff:
    """Diferencia entre versiones de contrato."""
    field: str
    version_1_value: str
    version_2_value: str
    change_type: str  # added, removed, modified
    risk_assessment: str
    recommendation: str


@dataclass
class KPIExtraction:
    """KPI extraído del documento."""
    kpi_name: str
    value: Any
    unit: str
    period: str
    context: str
    data_source: str  # tabla, texto, cálculo


@dataclass
class MonitoringAlert:
    """Alerta generada por el sistema de monitoreo."""
    alert_type: str
    severity: RiskLevel
    message: str
    document_id: str
    timestamp: datetime
    action_required: bool = True
    auto_resolved: bool = False


class CopilotMode:
    """
    Copilot Mode: Sistema Empresarial de Rendimiento Supremo para Análisis Legal Masivo.
    
    Sistema diseñado específicamente para empresas que manejan millones de PDFs
    con capacidades avanzadas de:
    - Compliance y riesgo contractual automático
    - Due Diligence para M&A
    - Extracción de KPIs y datos estructurados
    - Monitoreo y alertas continuas
    """
    
    def __init__(self, config: AppConfig, provider: str = "openai"):
        self.config = config
        self.provider = provider
        self.processor = DocumentProcessor(config)
        self.retriever_builder = RetrieverBuilder(config)
        self.workflow = AgentWorkflow(config)
        self.advanced_agent = AdvancedAutonomousAgent(config) if config.enable_autonomous_agents else None
        
        # Memoria y contexto
        self.memory_store = MemoryStore(config.memory_dir, config.memory_retention_days) if config.enable_memory else None
        self.context_manager = ContextManager(self.memory_store, config) if self.memory_store else None
        
        # LLM principal para análisis legal complejo
        from docchat.utils.llm_factory import create_llm
        self.llm = create_llm(
            provider=provider,
            model=config.agentic_model,
            temperature=0.1,  # Baja temperatura para precisión legal
            api_key=config.openai_api_key if provider == "openai" else config.anthropic_api_key,
            request_timeout=600  # Timeout largo para documentos complejos
        )
        
        # LLM rápido para tareas de clasificación y detección
        fast_model = "gpt-4o-mini" if provider == "openai" else "claude-haiku-4-5-20251001"
        self.fast_llm = create_llm(
            provider=provider,
            model=fast_model,
            temperature=0.0,  # Sin aleatoriedad para clasificación
            api_key=config.openai_api_key if provider == "openai" else config.anthropic_api_key,
            request_timeout=300
        )
        
        # Herramientas avanzadas
        self.tools = {
            "email": EmailTool(config),
            "report": ReportTool(config),
            "database": DatabaseTool(config),
            "presentation": PresentationTool(config),
            "integration": IntegrationTool(config),
            "table_analysis": TableAnalysisTool(config),
            "scheduler": SchedulerTool(config),
        }
    
        # Base de datos de contratos para comparación
        self.contract_database: Dict[str, Dict[str, Any]] = {}
        
        # Sistema de alertas
        self.active_alerts: List[MonitoringAlert] = []
        
        # Cache de análisis para optimización
        self.analysis_cache: Dict[str, Dict[str, Any]] = {}
    
    # ============================================================================
    # 1. COMPLIANCE Y RIESGO CONTRACTUAL AUTOMÁTICO
    # ============================================================================
    
    def analyze_contract_compliance(
        self,
        files: List,
        enable_dangerous_clauses: bool = True,
        enable_dates: bool = True,
        enable_obligations: bool = True,
        enable_hidden_costs: bool = True
    ) -> Dict[str, Any]:
        """
        Análisis completo de compliance y riesgo contractual.
        
        Detecta:
        - Cláusulas peligrosas
        - Vencimientos y fechas críticas
        - Obligaciones legales
        - Multas/costos ocultos
        """
        results = {
            "timestamp": datetime.now().isoformat(),
            "documents_analyzed": len(files),
            "dangerous_clauses": [],
            "critical_dates": [],
            "legal_obligations": [],
            "hidden_costs": [],
            "overall_risk_score": 0.0,
            "compliance_status": "unknown"
        }
        
        try:
            # Procesar documentos
            print("🔍 [Copilot] Iniciando análisis de compliance y riesgo...")
            docs = self.processor.process(files)
            
            if not docs:
                results["error"] = "No se pudieron procesar los documentos"
                return results
            
            # Construir contexto completo
            import uuid
            session_namespace = f"copilot_compliance_{uuid.uuid4().hex[:8]}"
            retriever = self.retriever_builder.build_hybrid_retriever(docs, namespace=session_namespace)
            
            # Analizar cada documento
            all_dangerous_clauses = []
            all_critical_dates = []
            all_obligations = []
            all_hidden_costs = []
            
            # Agrupar por archivo
            from collections import defaultdict
            docs_by_file = defaultdict(list)
            for doc in docs:
                source = doc.metadata.get("source", "")
                if source:
                    file_key = Path(source).name
                    docs_by_file[file_key].append(doc)
            
            with ThreadPoolExecutor(max_workers=3) as executor:
                futures = []
                for file_name, file_docs in docs_by_file.items():
                    if enable_dangerous_clauses:
                        futures.append(executor.submit(
                            self._detect_dangerous_clauses, file_docs, retriever, file_name
                        ))
                    if enable_dates:
                        futures.append(executor.submit(
                            self._detect_critical_dates, file_docs, retriever, file_name
                        ))
                    if enable_obligations:
                        futures.append(executor.submit(
                            self._detect_legal_obligations, file_docs, retriever, file_name
                        ))
                    if enable_hidden_costs:
                        futures.append(executor.submit(
                            self._detect_hidden_costs, file_docs, retriever, file_name
                        ))
                
                for future in as_completed(futures):
                    try:
                        result = future.result()
                        result_type = result.get("type")
                        if result_type == "dangerous_clauses":
                            all_dangerous_clauses.extend(result.get("clauses", []))
                        elif result_type == "critical_dates":
                            all_critical_dates.extend(result.get("dates", []))
                        elif result_type == "obligations":
                            all_obligations.extend(result.get("obligations", []))
                        elif result_type == "hidden_costs":
                            all_hidden_costs.extend(result.get("costs", []))
                    except Exception as e:
                        print(f"⚠️ Error en análisis paralelo: {e}")
            
            # Calcular riesgo general
            risk_score = self._calculate_overall_risk_score(
                all_dangerous_clauses, all_critical_dates, all_obligations, all_hidden_costs
            )
            
            results.update({
                "dangerous_clauses": [asdict(c) for c in all_dangerous_clauses],
                "critical_dates": [asdict(c) for c in all_critical_dates],
                "legal_obligations": [asdict(o) for o in all_obligations],
                "hidden_costs": [asdict(c) for c in all_hidden_costs],
                "overall_risk_score": risk_score,
                "compliance_status": self._determine_compliance_status(risk_score)
            })
            
            print(f"✅ [Copilot] Análisis completado. Risk Score: {risk_score:.2f}/100")
            
        except Exception as e:
            results["error"] = str(e)
            print(f"❌ [Copilot] Error en análisis: {e}")
        
        return results
    
    def _detect_dangerous_clauses(
        self,
        docs: List[Document],
        retriever,
        file_name: str
    ) -> List[DangerousClause]:
        """Detecta cláusulas peligrosas en el documento."""
        context = "\n\n---\n\n".join([d.page_content[:2000] for d in docs[:30]])
        
        prompt = f"""Analiza este documento legal/contractual y detecta TODAS las cláusulas peligrosas o riesgosas.

DOCUMENTO: {file_name}

CONTENIDO:
{context[:15000]}

INSTRUCCIONES:
Identifica cláusulas que presenten riesgos significativos incluyendo pero no limitado a:
- Limitación de responsabilidad excesiva
- Cláusulas de indemnización unilateral
- Multas o penalizaciones desproporcionadas
- Terminación automática sin derecho a remediación
- Cambios unilaterales de términos
- Confidencialidad perpetua
- No competencia excesivamente restrictiva
- Arbitraje forzoso en jurisdicciones desfavorables
- Renuncia a derechos legales
- Liquidated damages excesivos
- Auto-renovación automática sin opción de cancelación

Para cada cláusula peligrosa, proporciona:
1. Tipo de cláusula (termination, liability, indemnification, etc.)
2. Nivel de riesgo (critical, high, medium, low)
3. Descripción detallada
4. Ubicación aproximada en el documento
5. Recomendación de acción
6. Costo potencial (si aplicable)
7. Implicaciones legales

Responde ÚNICAMENTE en formato JSON:
{{
    "dangerous_clauses": [
        {{
            "clause_type": "tipo de cláusula",
            "risk_level": "critical|high|medium|low",
            "description": "descripción detallada",
            "location": "ubicación aproximada (página, sección)",
            "recommendation": "recomendación de acción",
            "potential_cost": "costo estimado o impacto financiero si aplica",
            "legal_implications": ["implicación 1", "implicación 2"]
        }}
    ]
}}"""
        
        try:
            response = self.llm.invoke(prompt).content.strip()
            if response.startswith("```json"):
                response = response.replace("```json", "").replace("```", "").strip()
            elif response.startswith("```"):
                response = response.replace("```", "").strip()
            
            data = json.loads(response)
            clauses = []
            for clause_data in data.get("dangerous_clauses", []):
                try:
                    clauses.append(DangerousClause(
                        clause_type=clause_data.get("clause_type", "unknown"),
                        risk_level=RiskLevel(clause_data.get("risk_level", "medium")),
                        description=clause_data.get("description", ""),
                        location=clause_data.get("location", ""),
                        recommendation=clause_data.get("recommendation", ""),
                        potential_cost=clause_data.get("potential_cost"),
                        legal_implications=clause_data.get("legal_implications", [])
                    ))
                except Exception as e:
                    print(f"⚠️ Error procesando cláusula: {e}")
                    continue
            
            return {"type": "dangerous_clauses", "clauses": clauses}
        except Exception as e:
            print(f"⚠️ Error detectando cláusulas peligrosas: {e}")
            return {"type": "dangerous_clauses", "clauses": []}
    
    def _detect_critical_dates(
        self,
        docs: List[Document],
        retriever,
        file_name: str
    ) -> List[CriticalDate]:
        """Detecta fechas críticas: vencimientos, plazos, renovaciones."""
        context = "\n\n---\n\n".join([d.page_content[:2000] for d in docs[:30]])
        
        prompt = f"""Analiza este documento y extrae TODAS las fechas críticas.

DOCUMENTO: {file_name}

CONTENIDO:
{context[:15000]}

INSTRUCCIONES:
Identifica todas las fechas importantes incluyendo:
- Vencimientos de contratos
- Plazos para cumplimiento de obligaciones
- Fechas de renovación automática
- Límites para ejercer derechos
- Fechas de expiración de garantías
- Deadlines para pagos
- Períodos de notificación requeridos
- Fechas de entrega o milestones
- Fechas de auditoría o inspección

Para cada fecha crítica, proporciona:
1. Fecha en formato YYYY-MM-DD (calcula la fecha real)
2. Tipo de fecha (vencimiento, plazo, expiracion, limite, renewal, milestone, etc.)
3. Descripción del evento
4. Días hasta la fecha (calcula desde hoy)
5. Nivel de riesgo basado en urgencia
6. Acción requerida
7. Partes involucradas

IMPORTANTE: Si encuentras períodos relativos (ej: "30 días después de..."), calcula la fecha absoluta.

Responde ÚNICAMENTE en formato JSON:
{{
    "critical_dates": [
        {{
            "date": "YYYY-MM-DD",
            "date_type": "tipo de fecha",
            "description": "descripción del evento",
            "days_until": N,
            "risk_level": "critical|high|medium|low",
            "action_required": "acción que debe tomarse",
            "parties_involved": ["parte1", "parte2"]
        }}
    ]
}}"""
        
        try:
            response = self.llm.invoke(prompt).content.strip()
            if response.startswith("```json"):
                response = response.replace("```json", "").replace("```", "").strip()
            elif response.startswith("```"):
                response = response.replace("```", "").strip()
            
            data = json.loads(response)
            dates = []
            today = datetime.now().date()
            
            for date_data in data.get("critical_dates", []):
                try:
                    date_str = date_data.get("date", "")
                    days_until = date_data.get("days_until", 0)
                    
                    # Calcular días si no está presente
                    if date_str and not days_until:
                        try:
                            date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
                            days_until = (date_obj - today).days
                        except:
                            pass
            
                    dates.append(CriticalDate(
                        date=date_str,
                        date_type=date_data.get("date_type", "unknown"),
                        description=date_data.get("description", ""),
                        days_until=days_until,
                        risk_level=RiskLevel(date_data.get("risk_level", "medium")),
                        action_required=date_data.get("action_required", ""),
                        parties_involved=date_data.get("parties_involved", [])
                    ))
                except Exception as e:
                    print(f"⚠️ Error procesando fecha: {e}")
                    continue
            
            return {"type": "critical_dates", "dates": dates}
        except Exception as e:
            print(f"⚠️ Error detectando fechas críticas: {e}")
            return {"type": "critical_dates", "dates": []}
    
    def _detect_legal_obligations(
        self,
        docs: List[Document],
        retriever,
        file_name: str
    ) -> List[LegalObligation]:
        """Detecta obligaciones legales y requisitos de cumplimiento."""
        context = "\n\n---\n\n".join([d.page_content[:2000] for d in docs[:30]])
        
        prompt = f"""Analiza este documento y extrae TODAS las obligaciones legales.

DOCUMENTO: {file_name}

CONTENIDO:
{context[:15000]}

INSTRUCCIONES:
Identifica todas las obligaciones legales incluyendo:
- Obligaciones contractuales explícitas
- Requisitos de cumplimiento normativo
- Responsabilidades de cada parte
- Requisitos de reporte o documentación
- Obligaciones de mantenimiento o servicio
- Requisitos de notificación
- Obligaciones de confidencialidad
- Requisitos de seguros
- Obligaciones de pago

Para cada obligación, proporciona:
1. Tipo de obligación (contrato, regulacion, compromiso, requisito)
2. Descripción detallada
3. Parte responsable
4. Fecha límite (deadline) si aplica
5. Nivel de riesgo si no se cumple
6. Estado de cumplimiento (pending, in_progress, completed, overdue)
7. Penalizaciones o consecuencias si no se cumple

Responde ÚNICAMENTE en formato JSON:
{{
    "legal_obligations": [
        {{
            "obligation_type": "tipo",
            "description": "descripción",
            "responsible_party": "parte responsable",
            "deadline": "YYYY-MM-DD o null",
            "risk_level": "critical|high|medium|low",
            "compliance_status": "pending|in_progress|completed|overdue",
            "penalties": ["penalización 1", "penalización 2"]
        }}
    ]
}}"""
        
        try:
            response = self.llm.invoke(prompt).content.strip()
            if response.startswith("```json"):
                response = response.replace("```json", "").replace("```", "").strip()
            elif response.startswith("```"):
                response = response.replace("```", "").strip()
            
            data = json.loads(response)
            obligations = []
            
            for obl_data in data.get("legal_obligations", []):
                try:
                    obligations.append(LegalObligation(
                        obligation_type=obl_data.get("obligation_type", "unknown"),
                        description=obl_data.get("description", ""),
                        responsible_party=obl_data.get("responsible_party", "unknown"),
                        deadline=obl_data.get("deadline"),
                        risk_level=RiskLevel(obl_data.get("risk_level", "medium")),
                        compliance_status=obl_data.get("compliance_status", "pending"),
                        penalties=obl_data.get("penalties", [])
                    ))
                    except Exception as e:
                    print(f"⚠️ Error procesando obligación: {e}")
                    continue
            
            return {"type": "obligations", "obligations": obligations}
        except Exception as e:
            print(f"⚠️ Error detectando obligaciones: {e}")
            return {"type": "obligations", "obligations": []}
    
    def _detect_hidden_costs(
        self,
        docs: List[Document],
        retriever,
        file_name: str
    ) -> List[HiddenCost]:
        """Detecta costos ocultos, multas y cargos no obvios."""
        context = "\n\n---\n\n".join([d.page_content[:2000] for d in docs[:30]])
        
        prompt = f"""Analiza este documento y detecta TODOS los costos ocultos o no obvios.

DOCUMENTO: {file_name}

CONTENIDO:
{context[:15000]}

INSTRUCCIONES:
Identifica costos que puedan no ser evidentes a primera vista:
- Multas por incumplimiento
- Penalizaciones por terminación anticipada
- Cargos por uso excesivo o overages
- Costos de renovación automática
- Cargos administrativos ocultos
- Costos de migración o transferencia
- Penalizaciones por cambios
- Cargos por servicios adicionales no incluidos
- Costos de cumplimiento o auditoría
- Tarifas de actualización o mantenimiento

Para cada costo oculto, proporciona:
1. Tipo de costo
2. Monto (si está especificado, incluye moneda)
3. Descripción
4. Condiciones que lo activan
5. Nivel de riesgo
6. Frecuencia (one_time, monthly, annual, variable)

Responde ÚNICAMENTE en formato JSON:
{{
    "hidden_costs": [
        {{
            "cost_type": "tipo de costo",
            "amount": "monto y moneda si está especificado",
            "description": "descripción detallada",
            "trigger_conditions": ["condición 1", "condición 2"],
            "risk_level": "critical|high|medium|low",
            "frequency": "one_time|monthly|annual|variable"
        }}
    ]
}}"""
        
        try:
            response = self.llm.invoke(prompt).content.strip()
            if response.startswith("```json"):
                response = response.replace("```json", "").replace("```", "").strip()
            elif response.startswith("```"):
                response = response.replace("```", "").strip()
            
            data = json.loads(response)
            costs = []
            
            for cost_data in data.get("hidden_costs", []):
                try:
                    costs.append(HiddenCost(
                        cost_type=cost_data.get("cost_type", "unknown"),
                        amount=cost_data.get("amount"),
                        description=cost_data.get("description", ""),
                        trigger_conditions=cost_data.get("trigger_conditions", []),
                        risk_level=RiskLevel(cost_data.get("risk_level", "medium")),
                        frequency=cost_data.get("frequency", "one_time")
                    ))
                except Exception as e:
                    print(f"⚠️ Error procesando costo: {e}")
                    continue
            
            return {"type": "hidden_costs", "costs": costs}
        except Exception as e:
            print(f"⚠️ Error detectando costos ocultos: {e}")
            return {"type": "hidden_costs", "costs": []}
        
    def _calculate_overall_risk_score(
        self,
        clauses: List[DangerousClause],
        dates: List[CriticalDate],
        obligations: List[LegalObligation],
        costs: List[HiddenCost]
    ) -> float:
        """Calcula un score de riesgo general de 0-100."""
        score = 0.0
        
        # Cláusulas peligrosas (peso: 30%)
        for clause in clauses:
            if clause.risk_level == RiskLevel.CRITICAL:
                score += 10
            elif clause.risk_level == RiskLevel.HIGH:
                score += 5
            elif clause.risk_level == RiskLevel.MEDIUM:
                score += 2
        score = min(score, 30)
        
        # Fechas críticas próximas (peso: 25%)
        today = datetime.now().date()
        for date in dates:
            if date.days_until < 0:  # Vencidas
                if date.risk_level in [RiskLevel.CRITICAL, RiskLevel.HIGH]:
                    score += 8
            else:
                    score += 3
            elif date.days_until <= 30:  # Próximas
                if date.risk_level == RiskLevel.CRITICAL:
                    score += 6
                elif date.risk_level == RiskLevel.HIGH:
                    score += 3
        score = min(score, 25)
        
        # Obligaciones no cumplidas (peso: 25%)
        for obligation in obligations:
            if obligation.compliance_status in ["overdue", "pending"]:
                if obligation.risk_level == RiskLevel.CRITICAL:
                    score += 8
                elif obligation.risk_level == RiskLevel.HIGH:
                    score += 5
                elif obligation.risk_level == RiskLevel.MEDIUM:
                    score += 2
        score = min(score, 25)
        
        # Costos ocultos significativos (peso: 20%)
        for cost in costs:
            if cost.risk_level in [RiskLevel.CRITICAL, RiskLevel.HIGH]:
                score += 4
            elif cost.risk_level == RiskLevel.MEDIUM:
                score += 2
        
        return min(score, 100.0)
    
    def _determine_compliance_status(self, risk_score: float) -> str:
        """Determina el estado de cumplimiento basado en el risk score."""
        if risk_score >= 75:
            return "critical_attention_required"
        elif risk_score >= 50:
            return "high_risk"
        elif risk_score >= 25:
            return "moderate_risk"
        elif risk_score >= 10:
            return "low_risk"
        else:
            return "compliant"
    
    def compare_contract_versions(
        self,
        version_1_files: List,
        version_2_files: List
    ) -> Dict[str, Any]:
        """
        Compara dos versiones de contratos y destaca diferencias críticas.
        """
        print("📊 [Copilot] Comparando versiones de contratos...")
        
        # Procesar ambas versiones
        v1_docs = self.processor.process(version_1_files)
        v2_docs = self.processor.process(version_2_files)
        
        v1_text = "\n\n".join([d.page_content for d in v1_docs])
        v2_text = "\n\n".join([d.page_content for d in v2_docs])
        
        prompt = f"""Compara estas dos versiones de un contrato y identifica TODAS las diferencias.

VERSIÓN 1:
{v1_text[:20000]}

VERSIÓN 2:
{v2_text[:20000]}

INSTRUCCIONES:
Identifica todas las diferencias significativas incluyendo:
- Cláusulas agregadas
- Cláusulas removidas
- Cláusulas modificadas
- Cambios en montos, fechas, o términos clave
- Cambios en responsabilidades
- Modificaciones en penalizaciones o multas

Para cada diferencia, proporciona:
1. Campo o sección afectada
2. Valor en versión 1
3. Valor en versión 2
4. Tipo de cambio (added, removed, modified)
5. Evaluación de riesgo del cambio
6. Recomendación

Responde ÚNICAMENTE en formato JSON:
{{
    "differences": [
        {{
            "field": "campo o sección",
            "version_1_value": "valor en v1",
            "version_2_value": "valor en v2",
            "change_type": "added|removed|modified",
            "risk_assessment": "evaluación de riesgo",
            "recommendation": "recomendación"
        }}
    ],
    "summary": "resumen general de cambios"
}}"""
        
        try:
            response = self.llm.invoke(prompt).content.strip()
            if response.startswith("```json"):
                response = response.replace("```json", "").replace("```", "").strip()
            elif response.startswith("```"):
                response = response.replace("```", "").strip()
            
            data = json.loads(response)
            
            differences = []
            for diff_data in data.get("differences", []):
                differences.append(ContractVersionDiff(
                    field=diff_data.get("field", ""),
                    version_1_value=diff_data.get("version_1_value", ""),
                    version_2_value=diff_data.get("version_2_value", ""),
                    change_type=diff_data.get("change_type", "modified"),
                    risk_assessment=diff_data.get("risk_assessment", ""),
                    recommendation=diff_data.get("recommendation", "")
                ))
            
            return {
                "timestamp": datetime.now().isoformat(),
                "differences": [asdict(d) for d in differences],
                "summary": data.get("summary", ""),
                "total_changes": len(differences)
            }
        except Exception as e:
            return {
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    # ============================================================================
    # 2. ANÁLISIS DE DUE DILIGENCE PARA M&A
    # ============================================================================
    
    def analyze_due_diligence(
        self,
        files: List,
        focus_areas: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Análisis completo de Due Diligence para fusiones y adquisiciones.
        
        Detecta:
        - Pasivos ocultos
        - Riesgos legales y financieros
        - Excepciones y limitaciones
        - Issues de cumplimiento
        """
        if focus_areas is None:
            focus_areas = ["liabilities", "risks", "exceptions", "compliance"]
        
        print("🔍 [Copilot] Iniciando análisis de Due Diligence...")
        
        results = {
            "timestamp": datetime.now().isoformat(),
            "documents_analyzed": len(files),
            "findings": [],
            "executive_summary": "",
            "risk_assessment": {},
            "recommendations": []
        }
        
        try:
            # Procesar documentos
            docs = self.processor.process(files)
            if not docs:
                results["error"] = "No se pudieron procesar los documentos"
                return results
            
            # Construir contexto
            context = "\n\n---\n\n".join([d.page_content[:3000] for d in docs[:50]])
            
            prompt = f"""Realiza un análisis completo de Due Diligence para una operación de M&A.

DOCUMENTOS ANALIZADOS: {len(files)}

CONTENIDO:
{context[:25000]}

ÁREAS DE ENFOQUE: {", ".join(focus_areas)}

INSTRUCCIONES:
Analiza los documentos y identifica:

1. PASIVOS OCULTOS:
   - Deudas no declaradas
   - Obligaciones contingentes
   - Litigios pendientes o potenciales
   - Garantías y avales
   - Contratos con términos onerosos

2. RIESGOS:
   - Riesgos legales significativos
   - Riesgos financieros
   - Riesgos operacionales
   - Riesgos regulatorios
   - Riesgos reputacionales

3. EXCEPCIONES Y LIMITACIONES:
   - Exclusiones en garantías
   - Límites de responsabilidad
   - Condiciones precedentes
   - Representaciones y garantías limitadas

4. ISSUES DE CUMPLIMIENTO:
   - Violaciones regulatorias
   - Incumplimientos contractuales
   - Problemas de compliance
   - Requisitos pendientes

Para cada hallazgo, proporciona:
- Tipo de hallazgo (liability, risk, exception, compliance_issue)
- Severidad (critical, high, medium, low)
- Descripción detallada
- Ubicación en documentos
- Recomendación
- Cláusulas relacionadas
- Impacto financiero estimado (si aplica)

Responde ÚNICAMENTE en formato JSON:
{{
    "findings": [
        {{
            "finding_type": "liability|risk|exception|compliance_issue",
            "severity": "critical|high|medium|low",
            "description": "descripción detallada",
            "location": "ubicación en documentos",
            "recommendation": "recomendación",
            "related_clauses": ["cláusula 1", "cláusula 2"],
            "financial_impact": "impacto financiero si aplica"
        }}
    ],
    "executive_summary": "resumen ejecutivo de 3-4 párrafos",
    "risk_assessment": {{
        "overall_risk": "critical|high|medium|low",
        "critical_issues_count": N,
        "high_risk_issues_count": N
    }},
    "recommendations": ["recomendación 1", "recomendación 2"]
}}"""
        
            response = self.llm.invoke(prompt).content.strip()
            if response.startswith("```json"):
                response = response.replace("```json", "").replace("```", "").strip()
            elif response.startswith("```"):
                response = response.replace("```", "").strip()
            
            data = json.loads(response)
            
            findings = []
            for finding_data in data.get("findings", []):
                try:
                    findings.append(DueDiligenceFinding(
                        finding_type=finding_data.get("finding_type", "unknown"),
                        severity=RiskLevel(finding_data.get("severity", "medium")),
                        description=finding_data.get("description", ""),
                        location=finding_data.get("location", ""),
                        recommendation=finding_data.get("recommendation", ""),
                        related_clauses=finding_data.get("related_clauses", []),
                        financial_impact=finding_data.get("financial_impact")
                    ))
        except Exception as e:
                    print(f"⚠️ Error procesando hallazgo: {e}")
                    continue
            
            results.update({
                "findings": [asdict(f) for f in findings],
                "executive_summary": data.get("executive_summary", ""),
                "risk_assessment": data.get("risk_assessment", {}),
                "recommendations": data.get("recommendations", [])
            })
            
            print(f"✅ [Copilot] Due Diligence completado. Hallazgos: {len(findings)}")
            
        except Exception as e:
            results["error"] = str(e)
            print(f"❌ [Copilot] Error en Due Diligence: {e}")
        
        return results
    
    def generate_investor_report(
        self,
        due_diligence_results: Dict[str, Any],
        format: str = "pdf"
    ) -> Dict[str, Any]:
        """
        Genera reporte ejecutivo listo para inversores basado en análisis de Due Diligence.
        """
        print("📄 [Copilot] Generando reporte para inversores...")
        
        try:
            report_tool = self.tools.get("report")
            if not report_tool:
                return {"error": "Report tool not available"}
            
            # Estructurar datos para el reporte
                report_data = {
                "title": "Due Diligence Report - Executive Summary",
                "timestamp": due_diligence_results.get("timestamp"),
                "executive_summary": due_diligence_results.get("executive_summary", ""),
                "risk_assessment": due_diligence_results.get("risk_assessment", {}),
                "findings": {
                    "critical": [f for f in due_diligence_results.get("findings", []) 
                               if f.get("severity") == "critical"],
                    "high": [f for f in due_diligence_results.get("findings", []) 
                            if f.get("severity") == "high"],
                    "medium": [f for f in due_diligence_results.get("findings", []) 
                              if f.get("severity") == "medium"],
                    "low": [f for f in due_diligence_results.get("findings", []) 
                           if f.get("severity") == "low"]
                },
                "recommendations": due_diligence_results.get("recommendations", [])
            }
            
                result = report_tool.execute(
                    data=report_data,
                format=format,
                title="Due Diligence Report for Investors"
                )
            
                if result.success:
                return {
                    "status": "success",
                    "report_path": str(result.data) if result.data else None,
                    "format": format
                }
            else:
                return {"status": "error", "message": result.message}
                
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    # ============================================================================
    # 3. EXTRACTORES DE KPI + TABLAS + DATOS ACCIONABLES
    # ============================================================================
    
    def extract_kpis_and_metrics(
        self,
        files: List,
        kpi_template: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Extrae KPIs, métricas y datos estructurados de documentos.
        Transforma PDFs en datos accionables para Excel, Dashboards, CRM.
        """
        print("📊 [Copilot] Extrayendo KPIs y métricas...")
        
        results = {
            "timestamp": datetime.now().isoformat(),
            "documents_processed": len(files),
            "kpis": [],
            "tables": [],
            "structured_data": {},
            "ready_for_export": True
        }
        
        try:
            docs = self.processor.process(files)
            if not docs:
                results["error"] = "No se pudieron procesar los documentos"
                return results
            
            # Extraer tablas primero
            table_results = []
            table_tool = self.tools.get("table_analysis")
            if table_tool:
                for doc in docs[:20]:  # Limitar para rendimiento
                    try:
                        table_data = table_tool.extract_tables(doc.page_content)
                        if table_data:
                            table_results.extend(table_data)
                    except:
                        pass
            
            # Construir contexto para extracción de KPIs
            context = "\n\n---\n\n".join([d.page_content[:2000] for d in docs[:40]])
            
            prompt = f"""Extrae TODOS los KPIs, métricas y datos estructurados de estos documentos.

DOCUMENTOS:
{context[:20000]}

INSTRUCCIONES:
Extrae información estructurada incluyendo:

1. KPIs Y MÉTRICAS:
   - Ventas por región, producto, período
   - Cláusulas de pago (montos, plazos, condiciones)
   - Plazos por contrato (duración, renovación, terminación)
   - Excepciones por cliente o contrato
   - Volúmenes, cantidades, porcentajes
   - Tasas, ratios, índices
   - Fechas y períodos relevantes

2. DATOS ESTRUCTURADOS:
   - Información de contratos (partes, fechas, términos)
   - Información financiera (montos, pagos, cargos)
   - Información de productos/servicios
   - Información de clientes/proveedores
   - Condiciones y términos

3. METADATOS ACCIONABLES:
   - Categorización automática
   - Tags y etiquetas
   - Prioridades
   - Estados

Para cada KPI, proporciona:
- Nombre del KPI
- Valor (numérico si es posible)
- Unidad de medida
- Período temporal
- Contexto
- Fuente en el documento (tabla, texto, cálculo)

Responde ÚNICAMENTE en formato JSON:
{{
    "kpis": [
        {{
            "kpi_name": "nombre del KPI",
            "value": "valor (numérico o texto)",
            "unit": "unidad",
            "period": "período",
            "context": "contexto adicional",
            "data_source": "tabla|texto|calculo"
        }}
    ],
    "structured_data": {{
        "contracts": [
            {{
                "parties": ["parte1", "parte2"],
                "effective_date": "YYYY-MM-DD",
                "expiration_date": "YYYY-MM-DD",
                "value": "monto",
                "currency": "moneda"
            }}
        ],
        "payments": [
            {{
                "amount": "monto",
                "currency": "moneda",
                "due_date": "YYYY-MM-DD",
                "recipient": "destinatario"
            }}
        ],
        "clients": [
            {{
                "name": "nombre",
                "category": "categoría",
                "contract_count": N
            }}
        ]
    }}
}}"""
        
            response = self.llm.invoke(prompt).content.strip()
            if response.startswith("```json"):
                response = response.replace("```json", "").replace("```", "").strip()
            elif response.startswith("```"):
                response = response.replace("```", "").strip()
            
            data = json.loads(response)
            
            kpis = []
            for kpi_data in data.get("kpis", []):
                try:
                    kpis.append(KPIExtraction(
                        kpi_name=kpi_data.get("kpi_name", ""),
                        value=kpi_data.get("value"),
                        unit=kpi_data.get("unit", ""),
                        period=kpi_data.get("period", ""),
                        context=kpi_data.get("context", ""),
                        data_source=kpi_data.get("data_source", "texto")
                    ))
        except Exception as e:
                    print(f"⚠️ Error procesando KPI: {e}")
                    continue
            
            results.update({
                "kpis": [asdict(k) for k in kpis],
                "tables": table_results,
                "structured_data": data.get("structured_data", {})
            })
            
            print(f"✅ [Copilot] Extracción completada. KPIs: {len(kpis)}, Tablas: {len(table_results)}")
            
        except Exception as e:
            results["error"] = str(e)
            print(f"❌ [Copilot] Error en extracción: {e}")
        
        return results
    
    def export_to_excel(
        self,
        kpi_results: Dict[str, Any],
        output_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Exporta KPIs y datos estructurados a Excel.
        """
        try:
            import pandas as pd
            from pathlib import Path
            
            if output_path is None:
                output_dir = Path(self.config.memory_dir) / "exports"
                output_dir.mkdir(parents=True, exist_ok=True)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_path = str(output_dir / f"copilot_kpis_{timestamp}.xlsx")
            
            with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
                # Hoja de KPIs
                if kpi_results.get("kpis"):
                    kpis_df = pd.DataFrame(kpi_results["kpis"])
                    kpis_df.to_excel(writer, sheet_name="KPIs", index=False)
                
                # Hoja de datos estructurados
                structured = kpi_results.get("structured_data", {})
                if structured.get("contracts"):
                    contracts_df = pd.DataFrame(structured["contracts"])
                    contracts_df.to_excel(writer, sheet_name="Contracts", index=False)
                
                if structured.get("payments"):
                    payments_df = pd.DataFrame(structured["payments"])
                    payments_df.to_excel(writer, sheet_name="Payments", index=False)
                
                if structured.get("clients"):
                    clients_df = pd.DataFrame(structured["clients"])
                    clients_df.to_excel(writer, sheet_name="Clients", index=False)
            
            return {
                "status": "success",
                "output_path": output_path,
                "sheets_created": len([s for s in [kpi_results.get("kpis"), 
                                                   structured.get("contracts"),
                                                   structured.get("payments"),
                                                   structured.get("clients")] if s])
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    # ============================================================================
    # 4. ALERTAS Y MONITOREO AUTOMÁTICO CONTINUO
    # ============================================================================
    
    def process_with_monitoring(
        self,
        files: List,
        alert_rules: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Procesa documentos con monitoreo automático y genera alertas.
        """
        print("🔔 [Copilot] Procesando con monitoreo activo...")
        
        if alert_rules is None:
            alert_rules = {
                "critical_risk_threshold": 75,
                "date_warning_days": 30,
                "auto_alert_on_hidden_costs": True,
                "auto_alert_on_dangerous_clauses": True
            }
        
        # Análisis completo
        compliance_results = self.analyze_contract_compliance(files)
        
        # Generar alertas
        alerts = []
        
        # Alertas por riesgo crítico
        if compliance_results.get("overall_risk_score", 0) >= alert_rules.get("critical_risk_threshold", 75):
            alerts.append(MonitoringAlert(
                alert_type="critical_risk",
                severity=RiskLevel.CRITICAL,
                message=f"Risk score crítico detectado: {compliance_results.get('overall_risk_score'):.2f}/100",
                document_id="multiple",
                timestamp=datetime.now(),
                action_required=True
            ))
        
        # Alertas por fechas próximas
        for date in compliance_results.get("critical_dates", []):
            date_obj = date if isinstance(date, dict) else asdict(date) if hasattr(date, '__dict__') else date
            days_until = date_obj.get("days_until", 999)
            if 0 < days_until <= alert_rules.get("date_warning_days", 30):
                alerts.append(MonitoringAlert(
                    alert_type="upcoming_deadline",
                    severity=RiskLevel(date_obj.get("risk_level", "medium")),
                    message=f"Fecha crítica próxima: {date_obj.get('description')} en {days_until} días",
                    document_id=date_obj.get("location", "unknown"),
                    timestamp=datetime.now(),
                    action_required=True
                ))
        
        # Alertas por cláusulas peligrosas
        if alert_rules.get("auto_alert_on_dangerous_clauses", True):
            for clause in compliance_results.get("dangerous_clauses", []):
                clause_obj = clause if isinstance(clause, dict) else asdict(clause) if hasattr(clause, '__dict__') else clause
                if clause_obj.get("risk_level") in ["critical", "high"]:
                    alerts.append(MonitoringAlert(
                        alert_type="dangerous_clause",
                        severity=RiskLevel(clause_obj.get("risk_level", "medium")),
                        message=f"Cláusula peligrosa detectada: {clause_obj.get('description', '')[:100]}",
                        document_id=clause_obj.get("location", "unknown"),
                        timestamp=datetime.now(),
                        action_required=True
                    ))
        
        # Guardar alertas
        self.active_alerts.extend(alerts)
        
        return {
            "timestamp": datetime.now().isoformat(),
            "compliance_analysis": compliance_results,
            "alerts_generated": len(alerts),
            "alerts": [asdict(a) for a in alerts],
            "monitoring_active": True
        }
    
    def get_active_alerts(
        self,
        severity: Optional[RiskLevel] = None,
        alert_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Obtiene alertas activas filtradas por severidad y tipo."""
        filtered = self.active_alerts
        
        if severity:
            filtered = [a for a in filtered if a.severity == severity]
        
        if alert_type:
            filtered = [a for a in filtered if a.alert_type == alert_type]
        
        # Ordenar por severidad y timestamp
        severity_order = {RiskLevel.CRITICAL: 0, RiskLevel.HIGH: 1, 
                         RiskLevel.MEDIUM: 2, RiskLevel.LOW: 3, RiskLevel.INFO: 4}
        filtered.sort(key=lambda x: (severity_order.get(x.severity, 99), x.timestamp), reverse=True)
        
        return [asdict(a) for a in filtered]
    
    def generate_weekly_monitoring_report(self) -> Dict[str, Any]:
        """Genera reporte semanal de monitoreo."""
        try:
            report_tool = self.tools.get("report")
            if not report_tool:
                return {"error": "Report tool not available"}
            
            # Obtener alertas de la semana
            week_ago = datetime.now() - timedelta(days=7)
            recent_alerts = [a for a in self.active_alerts if a.timestamp >= week_ago]
            
                report_data = {
                "title": "Weekly Monitoring Report",
                "period": f"{week_ago.date()} to {datetime.now().date()}",
                "total_alerts": len(recent_alerts),
                "alerts_by_severity": {
                    "critical": len([a for a in recent_alerts if a.severity == RiskLevel.CRITICAL]),
                    "high": len([a for a in recent_alerts if a.severity == RiskLevel.HIGH]),
                    "medium": len([a for a in recent_alerts if a.severity == RiskLevel.MEDIUM]),
                    "low": len([a for a in recent_alerts if a.severity == RiskLevel.LOW])
                },
                "alerts_by_type": {},
                "top_alerts": [asdict(a) for a in sorted(recent_alerts, 
                                                         key=lambda x: (x.severity.value, x.timestamp),
                                                         reverse=True)[:10]]
            }
            
            # Agrupar por tipo
            for alert in recent_alerts:
                alert_type = alert.alert_type
                report_data["alerts_by_type"][alert_type] = report_data["alerts_by_type"].get(alert_type, 0) + 1
            
                result = report_tool.execute(
                    data=report_data,
                format="pdf",
                title="Weekly Monitoring Report"
                )
            
                if result.success:
                return {
                    "status": "success",
                    "report_path": str(result.data) if result.data else None,
                    "alerts_summary": report_data
                }
            else:
                return {"status": "error", "message": result.message}
                
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    # ============================================================================
    # MÉTODO PRINCIPAL UNIFICADO
    # ============================================================================
    
    def process_documents_comprehensive(
        self,
        files: List,
        analysis_modes: Optional[List[str]] = None,
        enable_monitoring: bool = True
    ) -> Dict[str, Any]:
        """
        Procesamiento integral de documentos con todas las capacidades de Copilot.
        
        analysis_modes puede incluir:
        - "compliance": Análisis de compliance y riesgo
        - "due_diligence": Análisis de due diligence
        - "kpi_extraction": Extracción de KPIs y métricas
        - "monitoring": Monitoreo y alertas
        """
        if analysis_modes is None:
            analysis_modes = ["compliance", "kpi_extraction", "monitoring"]
        
        print("🚀 [Copilot] Iniciando procesamiento integral...")
        
        results = {
            "timestamp": datetime.now().isoformat(),
            "documents_processed": len(files),
            "analysis_modes": analysis_modes,
            "compliance_analysis": None,
            "due_diligence": None,
            "kpi_extraction": None,
            "monitoring": None
        }
        
        try:
            # Compliance y riesgo
            if "compliance" in analysis_modes:
                print("  → Ejecutando análisis de compliance...")
                results["compliance_analysis"] = self.analyze_contract_compliance(files)
            
            # Due Diligence
            if "due_diligence" in analysis_modes:
                print("  → Ejecutando análisis de Due Diligence...")
                results["due_diligence"] = self.analyze_due_diligence(files)
            
            # Extracción de KPIs
            if "kpi_extraction" in analysis_modes:
                print("  → Extrayendo KPIs y métricas...")
                results["kpi_extraction"] = self.extract_kpis_and_metrics(files)
            
            # Monitoreo
            if enable_monitoring and "monitoring" in analysis_modes:
                print("  → Activando monitoreo...")
                results["monitoring"] = self.process_with_monitoring(files)
            
            print("✅ [Copilot] Procesamiento integral completado")
            
        except Exception as e:
            results["error"] = str(e)
            print(f"❌ [Copilot] Error en procesamiento: {e}")
        
        return results
