"""
ÉXTASIS Workflows - Workflows Empresariales Específicos con CrewAI

Workflows de producción para:
1. Auditoría automática de contratos (Contract Intelligence)
2. Revisión autónoma de facturas / AP Automation
3. Detección de fraude en facturas y pagos
4. Compliance normativo con reportes legales
5. Automatización de flujos de riesgo y alertas críticas
6. Conciliación de datos entre sistemas (ERP, CRM, billing)
7. Workflows inter-sistema (tickets, ERP, CRM, email, Slack, S3, PDF)
"""

from __future__ import annotations

import os
import json
from typing import Any, Dict, List, Optional
from datetime import datetime

try:
    from crewai import Agent, Task, Crew, Process
    CREWAI_AVAILABLE = True
except ImportError:
    CREWAI_AVAILABLE = False
    print("⚠️ CrewAI no está instalado. Instala con: pip install crewai")

from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic

from .config import AppConfig
from .extasis_tools import EXTASIS_TOOLS


class ExtasisWorkflowType:
    """Tipos de workflows empresariales."""
    CONTRACT_AUDIT = "contract_audit"
    INVOICE_REVIEW = "invoice_review"
    FRAUD_DETECTION = "fraud_detection"
    COMPLIANCE_REPORT = "compliance_report"
    RISK_ALERTS = "risk_alerts"
    DATA_RECONCILIATION = "data_reconciliation"
    INTER_SYSTEM_WORKFLOW = "inter_system_workflow"


class ExtasisWorkflow:
    """Base class para workflows de ÉXTASIS."""
    
    def __init__(
        self,
        config: AppConfig,
        provider: str = "openai",
        simulation_mode: bool = False
    ):
        self.config = config
        self.provider = provider
        self.simulation_mode = simulation_mode
        
        # Crear LLM
        if provider == "anthropic":
            if not config.anthropic_api_key:
                raise ValueError("ANTHROPIC_API_KEY requerida")
            self.llm = ChatAnthropic(
                model=config.anthropic_model or "claude-3-5-sonnet-20241022",
                temperature=0.3,
                api_key=config.anthropic_api_key,
            )
        else:
            if not config.openai_api_key:
                raise ValueError("OPENAI_API_KEY requerida")
            self.llm = ChatOpenAI(
                model=config.agentic_model or "gpt-4o",
                temperature=0.3,
                api_key=config.openai_api_key,
            )
        
        # Tools disponibles
        self.tools = EXTASIS_TOOLS
    
    def execute(self, documents: List[str], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Ejecuta el workflow."""
        raise NotImplementedError("Subclasses must implement execute method")


class ContractAuditWorkflow(ExtasisWorkflow):
    """Workflow de auditoría automática de contratos."""
    
    def execute(self, documents: List[str], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Audita contratos y detecta riesgos/cláusulas importantes."""
        if not CREWAI_AVAILABLE:
            return {"error": "CrewAI no está disponible"}
        
        context = context or {}
        
        # Agente especializado en auditoría de contratos
        contract_auditor = Agent(
            role="Especialista en Auditoría de Contratos",
            goal="Analizar contratos, detectar cláusulas críticas, riesgos legales y oportunidades",
            backstory="""Eres un experto legal con años de experiencia en revisión de contratos empresariales.
            Identificas cláusulas problemáticas, riesgos, oportunidades y áreas de mejora.
            Proporcionas análisis estructurados y accionables.""",
            tools=self.tools,
            llm=self.llm,
            verbose=True,
            allow_delegation=True,
            max_iter=10
        )
        
        # Agente de generación de alertas
        alert_agent = Agent(
            role="Especialista en Alertas y Notificaciones",
            goal="Generar alertas críticas y notificar a stakeholders",
            backstory="""Eres responsable de comunicar hallazgos críticos a los equipos relevantes.
            Creas tickets, envías emails y notificas en Slack cuando se detectan riesgos importantes.""",
            tools=self.tools,
            llm=self.llm,
            verbose=True,
            allow_delegation=False
        )
        
        # Tasks
        audit_task = Task(
            description=f"""
            Analiza los siguientes documentos de contratos: {json.dumps(documents)}
            
            Para cada contrato, identifica:
            1. Cláusulas críticas (terminación, indemnización, confidencialidad)
            2. Riesgos legales y financieros
            3. Oportunidades de mejora o negociación
            4. Cumplimiento normativo
            
            Genera un reporte estructurado con:
            - Resumen ejecutivo
            - Análisis detallado por contrato
            - Riesgos priorizados (Alto, Medio, Bajo)
            - Recomendaciones accionables
            """,
            agent=contract_auditor,
            expected_output="Reporte estructurado de auditoría de contratos con riesgos y recomendaciones"
        )
        
        alert_task = Task(
            description="""
            Basándote en el análisis de contratos, genera alertas para:
            - Riesgos altos o críticos
            - Contratos con cláusulas problemáticas
            - Fechas importantes (vencimientos, renovaciones)
            
            Crea tickets en Jira o ServiceNow para seguimiento.
            Envía emails a stakeholders relevantes.
            Notifica en Slack si hay riesgos críticos.
            """,
            agent=alert_agent,
            expected_output="Alertas creadas y notificaciones enviadas",
            context=[audit_task]
        )
        
        # Crew
        crew = Crew(
            agents=[contract_auditor, alert_agent],
            tasks=[audit_task, alert_task],
            process=Process.sequential,
            verbose=True
        )
        
        # Ejecutar
        result = crew.kickoff(inputs={"documents": documents, **context})
        
        return {
            "workflow": "contract_audit",
            "status": "completed",
            "result": str(result),
            "timestamp": datetime.now().isoformat()
        }


class InvoiceReviewWorkflow(ExtasisWorkflow):
    """Workflow de revisión autónoma de facturas (AP Automation)."""
    
    def execute(self, documents: List[str], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Revisa facturas y automatiza aprobaciones."""
        if not CREWAI_AVAILABLE:
            return {"error": "CrewAI no está disponible"}
        
        context = context or {}
        max_amount = context.get("max_auto_approval_amount", 1000)
        
        # Agente analizador de facturas
        invoice_analyzer = Agent(
            role="Analizador de Facturas",
            goal="Analizar facturas, validar información y detectar inconsistencias",
            backstory="""Eres un experto en cuentas por pagar. Analizas facturas en detalle:
            - Verificas montos, fechas, proveedores
            - Validas contra órdenes de compra
            - Detectas duplicados o errores
            - Identificas facturas sospechosas""",
            tools=self.tools,
            llm=self.llm,
            verbose=True,
            max_iter=8
        )
        
        # Agente de aprobación
        approval_agent = Agent(
            role="Especialista en Aprobación de Pagos",
            goal="Aprobar pagos automáticamente cuando es seguro, o escalar cuando es necesario",
            backstory="""Eres responsable de aprobar pagos según políticas empresariales.
            Apruebas automáticamente facturas menores a ${max_amount} que pasen validaciones.
            Escalas facturas grandes o sospechosas para revisión humana.""",
            tools=self.tools,
            llm=self.llm,
            verbose=True,
            allow_delegation=False
        )
        
        # Tasks
        analysis_task = Task(
            description=f"""
            Analiza las siguientes facturas: {json.dumps(documents)}
            
            Para cada factura:
            1. Extrae información clave (proveedor, monto, fecha, conceptos)
            2. Valida contra órdenes de compra en el ERP
            3. Detecta duplicados o errores
            4. Calcula riesgos de fraude
            5. Verifica cumplimiento de políticas
            
            Genera un reporte con:
            - Facturas válidas y listas para aprobar
            - Facturas que requieren revisión
            - Facturas con errores o inconsistencias
            """,
            agent=invoice_analyzer,
            expected_output="Análisis detallado de facturas con recomendaciones de aprobación"
        )
        
        approval_task = Task(
            description=f"""
            Basándote en el análisis de facturas:
            
            Para facturas menores a ${max_amount} y sin riesgos:
            - Aproba automáticamente en el ERP
            - Crea registros en el sistema de pagos
            - Envía confirmación al proveedor
            
            Para facturas grandes o con riesgos:
            - Crea tickets en Jira/ServiceNow para revisión humana
            - Envía alertas por email a finanzas
            - Notifica en Slack
            
            Genera reporte de aprobaciones y escalaciones.
            """,
            agent=approval_agent,
            expected_output="Facturas aprobadas automáticamente o escaladas para revisión",
            context=[analysis_task]
        )
        
        # Crew
        crew = Crew(
            agents=[invoice_analyzer, approval_agent],
            tasks=[analysis_task, approval_task],
            process=Process.sequential,
            verbose=True
        )
        
        result = crew.kickoff(inputs={"documents": documents, **context})
        
        return {
            "workflow": "invoice_review",
            "status": "completed",
            "result": str(result),
            "timestamp": datetime.now().isoformat()
        }


class FraudDetectionWorkflow(ExtasisWorkflow):
    """Workflow de detección de fraude en facturas y pagos."""
    
    def execute(self, documents: List[str], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Detecta fraude en facturas y pagos."""
        if not CREWAI_AVAILABLE:
            return {"error": "CrewAI no está disponible"}
        
        context = context or {}
        
        # Agente detector de fraude
        fraud_detector = Agent(
            role="Especialista en Detección de Fraude",
            goal="Detectar patrones de fraude, anomalías y transacciones sospechosas",
            backstory="""Eres un experto en detección de fraude financiero con años de experiencia.
            Identificas patrones sospechosos, anomalías estadísticas, y transacciones atípicas.
            Usas reglas heurísticas y análisis de datos para detectar fraudes.""",
            tools=self.tools,
            llm=self.llm,
            verbose=True,
            max_iter=10
        )
        
        # Agente de respuesta a fraude
        fraud_response = Agent(
            role="Especialista en Respuesta a Incidentes de Fraude",
            goal="Bloquear transacciones fraudulentas y alertar a equipos de seguridad",
            backstory="""Eres responsable de responder rápidamente a incidentes de fraude detectados.
            Bloqueas transacciones, alertas a equipos de seguridad, y creas casos de investigación.""",
            tools=self.tools,
            llm=self.llm,
            verbose=True,
            allow_delegation=False
        )
        
        # Tasks
        detection_task = Task(
            description=f"""
            Analiza las siguientes facturas/pagos para detectar fraude: {json.dumps(documents)}
            
            Busca:
            1. Montos anómalos (muy altos o fuera de rango normal)
            2. Proveedores nuevos o sospechosos
            3. Patrones de tiempo inusuales
            4. Duplicados o variaciones de facturas existentes
            5. Inconsistencias en información (direcciones, números de cuenta)
            
            Para cada caso sospechoso, calcula:
            - Nivel de riesgo (Alto, Medio, Bajo)
            - Score de fraude (0-100)
            - Justificación del riesgo
            
            Genera reporte de detección de fraude.
            """,
            agent=fraud_detector,
            expected_output="Reporte de detección de fraude con casos sospechosos priorizados"
        )
        
        response_task = Task(
            description="""
            Para cada caso de fraude detectado con riesgo ALTO:
            
            1. Bloquea la transacción en el ERP/CRM
            2. Crea ticket crítico en Jira/ServiceNow
            3. Envía alerta inmediata por email a finanzas y seguridad
            4. Notifica en Slack al canal de seguridad
            5. Genera reporte PDF y súbelo a S3 para auditoría
            
            Para casos de riesgo MEDIO:
            - Crea ticket para revisión
            - Envía notificación por email
            
            Genera reporte de acciones tomadas.
            """,
            agent=fraud_response,
            expected_output="Transacciones bloqueadas y alertas enviadas",
            context=[detection_task]
        )
        
        # Crew
        crew = Crew(
            agents=[fraud_detector, fraud_response],
            tasks=[detection_task, response_task],
            process=Process.sequential,
            verbose=True
        )
        
        result = crew.kickoff(inputs={"documents": documents, **context})
        
        return {
            "workflow": "fraud_detection",
            "status": "completed",
            "result": str(result),
            "timestamp": datetime.now().isoformat()
        }


class ComplianceReportWorkflow(ExtasisWorkflow):
    """Workflow de compliance normativo con reportes legales."""
    
    def execute(self, documents: List[str], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Genera reportes de compliance normativo."""
        if not CREWAI_AVAILABLE:
            return {"error": "CrewAI no está disponible"}
        
        context = context or {}
        regulation_type = context.get("regulation_type", "general")
        
        # Agente de compliance
        compliance_agent = Agent(
            role="Especialista en Compliance Legal",
            goal="Analizar documentos y generar reportes de cumplimiento normativo",
            backstory="""Eres un experto en compliance legal empresarial.
            Conoces regulaciones como GDPR, SOX, HIPAA, PCI-DSS, y otras normativas relevantes.
            Generas reportes estructurados de cumplimiento.""",
            tools=self.tools,
            llm=self.llm,
            verbose=True,
            max_iter=10
        )
        
        # Agente generador de reportes
        report_agent = Agent(
            role="Especialista en Generación de Reportes",
            goal="Generar reportes PDF profesionales y distribuirlos",
            backstory="""Eres responsable de generar reportes PDF profesionales de compliance.
            Formateas información de forma clara, agregas gráficos y tablas, y distribuyes reportes.""",
            tools=self.tools,
            llm=self.llm,
            verbose=True,
            allow_delegation=False
        )
        
        # Tasks
        compliance_task = Task(
            description=f"""
            Analiza los siguientes documentos para compliance {regulation_type}: {json.dumps(documents)}
            
            Verifica:
            1. Cumplimiento de regulaciones aplicables
            2. Áreas de no cumplimiento o riesgo
            3. Recomendaciones para mejorar compliance
            4. Evidencias y referencias normativas
            
            Genera análisis estructurado de compliance.
            """,
            agent=compliance_agent,
            expected_output="Análisis de compliance con áreas de cumplimiento y no cumplimiento"
        )
        
        report_task = Task(
            description="""
            Basándote en el análisis de compliance:
            
            1. Genera reporte PDF profesional con:
               - Resumen ejecutivo
               - Análisis detallado
               - Gráficos y tablas
               - Recomendaciones
               - Referencias normativas
            
            2. Sube el PDF a S3 para archivo
            3. Envía el reporte por email a compliance y legal
            4. Crea ticket en Jira para seguimiento de acciones
            
            Genera confirmación de reporte generado.
            """,
            agent=report_agent,
            expected_output="Reporte PDF generado, subido a S3 y distribuido",
            context=[compliance_task]
        )
        
        # Crew
        crew = Crew(
            agents=[compliance_agent, report_agent],
            tasks=[compliance_task, report_task],
            process=Process.sequential,
            verbose=True
        )
        
        result = crew.kickoff(inputs={"documents": documents, **context})
        
        return {
            "workflow": "compliance_report",
            "status": "completed",
            "result": str(result),
            "timestamp": datetime.now().isoformat()
        }


class DataReconciliationWorkflow(ExtasisWorkflow):
    """Workflow de conciliación de datos entre sistemas."""
    
    def execute(self, documents: List[str], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Concilia datos entre ERP, CRM y sistemas de billing."""
        if not CREWAI_AVAILABLE:
            return {"error": "CrewAI no está disponible"}
        
        context = context or {}
        systems = context.get("systems", ["erp", "crm"])
        
        # Agente de conciliación
        reconciliation_agent = Agent(
            role="Especialista en Conciliación de Datos",
            goal="Comparar y conciliar datos entre múltiples sistemas empresariales",
            backstory="""Eres un experto en integración de datos empresariales.
            Comparas datos entre sistemas, identificas diferencias, y propones correcciones.
            Aseguras consistencia entre ERP, CRM, y sistemas de billing.""",
            tools=self.tools,
            llm=self.llm,
            verbose=True,
            max_iter=10
        )
        
        # Agente de corrección
        correction_agent = Agent(
            role="Especialista en Corrección de Datos",
            goal="Corregir inconsistencias detectadas en sistemas",
            backstory="""Eres responsable de corregir datos inconsistentes entre sistemas.
            Actualizas registros, sincronizas información, y documentas cambios realizados.""",
            tools=self.tools,
            llm=self.llm,
            verbose=True,
            allow_delegation=False
        )
        
        # Tasks
        reconciliation_task = Task(
            description=f"""
            Concilia datos entre los siguientes sistemas: {json.dumps(systems)}
            
            Compara:
            1. Información de clientes entre CRM y ERP
            2. Facturas y pagos entre ERP y billing
            3. Órdenes y entregas entre sistemas
            
            Identifica:
            - Diferencias en datos
            - Registros faltantes
            - Inconsistencias de formato
            - Duplicados
            
            Genera reporte de conciliación con diferencias encontradas.
            """,
            agent=reconciliation_agent,
            expected_output="Reporte de conciliación con diferencias y recomendaciones"
        )
        
        correction_task = Task(
            description="""
            Basándote en el reporte de conciliación:
            
            Para diferencias claras y fáciles de corregir:
            1. Actualiza datos en los sistemas correspondientes
            2. Sincroniza información entre sistemas
            
            Para diferencias complejas:
            1. Crea tickets en Jira/ServiceNow para revisión
            2. Envía alertas por email a equipos relevantes
            3. Genera reporte de seguimiento
            
            Documenta todas las correcciones realizadas.
            """,
            agent=correction_agent,
            expected_output="Datos conciliados y correcciones documentadas",
            context=[reconciliation_task]
        )
        
        # Crew
        crew = Crew(
            agents=[reconciliation_agent, correction_agent],
            tasks=[reconciliation_task, correction_task],
            process=Process.sequential,
            verbose=True
        )
        
        result = crew.kickoff(inputs={"documents": documents, **context})
        
        return {
            "workflow": "data_reconciliation",
            "status": "completed",
            "result": str(result),
            "timestamp": datetime.now().isoformat()
        }


# ============================================================================
# FACTORY FUNCTION
# ============================================================================

def get_extasis_workflow(
    workflow_type: str,
    config: AppConfig,
    provider: str = "openai",
    simulation_mode: bool = False
) -> ExtasisWorkflow:
    """Obtiene un workflow de ÉXTASIS por tipo."""
    
    workflow_map = {
        ExtasisWorkflowType.CONTRACT_AUDIT: ContractAuditWorkflow,
        ExtasisWorkflowType.INVOICE_REVIEW: InvoiceReviewWorkflow,
        ExtasisWorkflowType.FRAUD_DETECTION: FraudDetectionWorkflow,
        ExtasisWorkflowType.COMPLIANCE_REPORT: ComplianceReportWorkflow,
        ExtasisWorkflowType.DATA_RECONCILIATION: DataReconciliationWorkflow,
    }
    
    workflow_class = workflow_map.get(workflow_type)
    if not workflow_class:
        raise ValueError(f"Workflow type no soportado: {workflow_type}")
    
    return workflow_class(
        config=config,
        provider=provider,
        simulation_mode=simulation_mode
    )

