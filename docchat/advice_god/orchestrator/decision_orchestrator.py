"""Decision Orchestrator - Coordina la ejecución de workflows según el tipo de documento."""

from __future__ import annotations

from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
import json

from ..classifier.document_classifier import DocumentTypeClassifier, DocumentType
from ..actions.action_layer import ActionLayer
from langchain_core.documents import Document


@dataclass
class WorkflowResult:
    """Resultado de la ejecución de un workflow."""
    workflow_name: str
    document_type: str
    success: bool
    summary: str
    extracted_fields: Dict[str, Any]
    actions_performed: List[Dict[str, Any]]
    confidence: float
    errors: List[str]
    timestamp: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte el resultado a diccionario."""
        return {
            "workflow_name": self.workflow_name,
            "document_type": self.document_type,
            "success": self.success,
            "summary": self.summary,
            "extracted_fields": self.extracted_fields,
            "actions_performed": self.actions_performed,
            "confidence": self.confidence,
            "errors": self.errors,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class ClassifiedDocument:
    """Documento clasificado con su tipo y confianza."""
    document: Document
    doc_type: DocumentType
    confidence: float
    text: str


class DecisionOrchestrator:
    """
    Orquestador de decisiones - Coordina workflows según tipo de documento.
    
    Flujo:
    1. Recibe PDFs ya procesados (texto extraído)
    2. Clasifica cada PDF
    3. Agrupa por tipo
    4. Ejecuta workflow correspondiente
    5. Devuelve resultados estructurados
    """
    
    def __init__(self, config: Any, llm: Any, action_layer: Optional[ActionLayer] = None):
        """
        Inicializa el orquestador.
        
        Args:
            config: Configuración de la aplicación
            llm: Instancia del LLM para extracción
            action_layer: Capa de acciones (opcional, se crea si no se proporciona)
        """
        self.config = config
        self.llm = llm
        self.classifier = DocumentTypeClassifier()
        self.action_layer = action_layer or ActionLayer(config, dry_run=False)
        
        # Mapeo de tipos de documento a workflows
        self.workflow_mapping = {
            DocumentType.INVOICE: "invoice_workflow",
            DocumentType.BANK_STATEMENT: "bank_statement_workflow",
            DocumentType.CONTRACT: "contract_workflow",
            DocumentType.LEGAL_DOCUMENT: "legal_document_workflow",
            DocumentType.PAYROLL: "payroll_workflow",
            DocumentType.INSURANCE_CLAIM: "insurance_claim_workflow",
            DocumentType.SHIPPING_DOCUMENT: "shipping_document_workflow",
            DocumentType.HR_RESUME: "hr_resume_workflow",
            DocumentType.TAX_DOCUMENT: "tax_document_workflow",
            DocumentType.PURCHASE_ORDER: "purchase_order_workflow",
            DocumentType.GENERIC_DOCUMENT: "generic_workflow"
        }
        
        # Importar workflows dinámicamente
        self._load_workflows()
    
    def _load_workflows(self) -> None:
        """Carga los workflows disponibles."""
        self.workflows = {}
        
        try:
            from ..workflows.invoice_workflow import InvoiceWorkflow
            self.workflows["invoice_workflow"] = InvoiceWorkflow(self.config, self.llm, self.action_layer)
        except ImportError:
            pass
        
        try:
            from ..workflows.contract_workflow import ContractWorkflow
            self.workflows["contract_workflow"] = ContractWorkflow(self.config, self.llm, self.action_layer)
        except ImportError:
            pass
        
        try:
            from ..workflows.bank_statement_workflow import BankStatementWorkflow
            self.workflows["bank_statement_workflow"] = BankStatementWorkflow(self.config, self.llm, self.action_layer)
        except ImportError:
            pass
        
        try:
            from ..workflows.hr_resume_workflow import HRResumeWorkflow
            self.workflows["hr_resume_workflow"] = HRResumeWorkflow(self.config, self.llm, self.action_layer)
        except ImportError:
            pass
        
        try:
            from ..workflows.insurance_claim_workflow import InsuranceClaimWorkflow
            self.workflows["insurance_claim_workflow"] = InsuranceClaimWorkflow(self.config, self.llm, self.action_layer)
        except ImportError:
            pass
        
        try:
            from ..workflows.generic_workflow import GenericWorkflow
            self.workflows["generic_workflow"] = GenericWorkflow(self.config, self.llm, self.action_layer)
        except ImportError:
            pass
    
    def classify_documents(self, documents: List[Document]) -> List[ClassifiedDocument]:
        """
        Clasifica una lista de documentos.
        
        Args:
            documents: Lista de documentos procesados
            
        Returns:
            Lista de documentos clasificados
        """
        classified = []
        
        for doc in documents:
            text = doc.page_content
            metadata = doc.metadata
            
            # Clasificar
            doc_type, confidence = self.classifier.classify(text, metadata)
            
            classified.append(ClassifiedDocument(
                document=doc,
                doc_type=doc_type,
                confidence=confidence,
                text=text
            ))
        
        return classified
    
    def group_by_type(self, classified_docs: List[ClassifiedDocument]) -> Dict[DocumentType, List[ClassifiedDocument]]:
        """
        Agrupa documentos por tipo.
        
        Args:
            classified_docs: Lista de documentos clasificados
            
        Returns:
            Diccionario agrupado por tipo
        """
        grouped = {}
        for doc in classified_docs:
            if doc.doc_type not in grouped:
                grouped[doc.doc_type] = []
            grouped[doc.doc_type].append(doc)
        
        return grouped
    
    def execute_workflow(
        self,
        workflow_name: str,
        documents: List[ClassifiedDocument]
    ) -> WorkflowResult:
        """
        Ejecuta un workflow específico.
        
        Args:
            workflow_name: Nombre del workflow
            documents: Documentos a procesar
            
        Returns:
            Resultado del workflow
        """
        if workflow_name not in self.workflows:
            # Workflow no disponible, usar genérico
            workflow_name = "generic_workflow"
            if workflow_name not in self.workflows:
                # Crear resultado de error
                return WorkflowResult(
                    workflow_name=workflow_name,
                    document_type=documents[0].doc_type.value if documents else "unknown",
                    success=False,
                    summary=f"Workflow '{workflow_name}' no está disponible",
                    extracted_fields={},
                    actions_performed=[],
                    confidence=0.0,
                    errors=[f"Workflow '{workflow_name}' no implementado"],
                    timestamp=datetime.now()
                )
        
        workflow = self.workflows[workflow_name]
        
        try:
            # Ejecutar workflow
            result = workflow.execute(documents)
            return result
            
        except Exception as e:
            return WorkflowResult(
                workflow_name=workflow_name,
                document_type=documents[0].doc_type.value if documents else "unknown",
                success=False,
                summary=f"Error ejecutando workflow: {str(e)}",
                extracted_fields={},
                actions_performed=[],
                confidence=0.0,
                errors=[str(e)],
                timestamp=datetime.now()
            )
    
    def process_documents(
        self,
        documents: List[Document],
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        Procesa una lista de documentos completando el ciclo Sense → Think → Act → Report.
        
        Args:
            documents: Lista de documentos ya procesados (texto extraído)
            dry_run: Si True, simula acciones sin ejecutarlas
            
        Returns:
            Diccionario con resultados estructurados
        """
        # Configurar dry_run en action layer
        self.action_layer.dry_run = dry_run
        
        # SENSE: Clasificar documentos
        classified_docs = self.classify_documents(documents)
        
        # Agrupar por tipo
        grouped_docs = self.group_by_type(classified_docs)
        
        # THINK: Determinar workflows a ejecutar
        workflow_results: List[WorkflowResult] = []
        
        # ACT: Ejecutar workflows
        for doc_type, docs_list in grouped_docs.items():
            workflow_name = self.workflow_mapping.get(doc_type, "generic_workflow")
            
            # Ejecutar workflow para este grupo
            result = self.execute_workflow(workflow_name, docs_list)
            workflow_results.append(result)
        
        # REPORT: Generar reporte consolidado
        total_docs = len(documents)
        successful = sum(1 for r in workflow_results if r.success)
        failed = total_docs - successful
        
        # Calcular confianza promedio
        avg_confidence = sum(r.confidence for r in workflow_results) / len(workflow_results) if workflow_results else 0.0
        
        # Consolidar acciones ejecutadas
        all_actions = []
        for result in workflow_results:
            all_actions.extend(result.actions_performed)
        
        # Consolidar campos extraídos
        all_extracted_fields = {}
        for result in workflow_results:
            all_extracted_fields[result.workflow_name] = result.extracted_fields
        
        # Consolidar errores
        all_errors = []
        for result in workflow_results:
            all_errors.extend(result.errors)
        
        # Generar resumen ejecutivo
        summary = f"""
Procesamiento completado: {total_docs} documentos
- Exitosos: {successful}
- Fallidos: {failed}
- Confianza promedio: {avg_confidence:.2%}
- Workflows ejecutados: {len(workflow_results)}
- Acciones realizadas: {len(all_actions)}
"""
        
        return {
            "status": "completed",
            "timestamp": datetime.now().isoformat(),
            "summary": summary.strip(),
            "total_documents": total_docs,
            "successful": successful,
            "failed": failed,
            "average_confidence": avg_confidence,
            "workflow_results": [r.to_dict() for r in workflow_results],
            "extracted_fields": all_extracted_fields,
            "actions_performed": all_actions,
            "errors": all_errors,
            "dry_run": dry_run
        }

