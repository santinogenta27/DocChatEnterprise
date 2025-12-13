"""Document Type Classifier - Detecta automáticamente el tipo de documento PDF."""

from __future__ import annotations

from enum import Enum
from typing import Dict, List, Optional, Tuple
import re
from collections import Counter


class DocumentType(str, Enum):
    """Tipos de documentos soportados."""
    INVOICE = "invoice"
    BANK_STATEMENT = "bank_statement"
    CONTRACT = "contract"
    LEGAL_DOCUMENT = "legal_document"
    PAYROLL = "payroll"
    INSURANCE_CLAIM = "insurance_claim"
    SHIPPING_DOCUMENT = "shipping_document"
    HR_RESUME = "hr_resume"
    TAX_DOCUMENT = "tax_document"
    PURCHASE_ORDER = "purchase_order"
    GENERIC_DOCUMENT = "generic_document"


class DocumentTypeClassifier:
    """
    Clasificador de tipos de documentos basado en palabras clave, patrones y estructura.
    
    Usa heurísticas simples y rápidas para máxima precisión sin modelos pesados.
    """
    
    def __init__(self):
        """Inicializa el clasificador con reglas y patrones."""
        self._build_classification_rules()
    
    def _build_classification_rules(self) -> None:
        """Construye las reglas de clasificación para cada tipo de documento."""
        
        # Palabras clave por tipo de documento (español + inglés)
        self.keywords: Dict[DocumentType, List[str]] = {
            DocumentType.INVOICE: [
                # Español
                "factura", "invoice", "facturación", "billing",
                "proveedor", "supplier", "vendor", "monto total", "total amount",
                "impuesto", "tax", "iva", "subtotal", "número de factura",
                "invoice number", "fecha de factura", "invoice date",
                "orden de compra", "purchase order", "po number",
                "line items", "items", "descripción", "description",
                "neto", "net", "bruto", "gross"
            ],
            DocumentType.BANK_STATEMENT: [
                "extracto bancario", "bank statement", "estado de cuenta",
                "account statement", "transacciones", "transactions",
                "depósito", "deposit", "retiro", "withdrawal", "transferencia",
                "transfer", "saldo", "balance", "fecha de transacción",
                "transaction date", "número de cuenta", "account number",
                "banco", "bank", "débito", "debit", "crédito", "credit"
            ],
            DocumentType.CONTRACT: [
                "contrato", "contract", "acuerdo", "agreement",
                "partes", "parties", "cláusula", "clause", "jurisdicción",
                "jurisdiction", "firmas", "signatures", "vigencia",
                "validity", "términos y condiciones", "terms and conditions",
                "obligaciones", "obligations", "derechos", "rights",
                "prestación de servicios", "service agreement"
            ],
            DocumentType.LEGAL_DOCUMENT: [
                "documento legal", "legal document", "poder", "power of attorney",
                "testamento", "will", "escritura", "deed", "demanda",
                "lawsuit", "sentencia", "judgment", "acuerdo de confidencialidad",
                "nda", "non-disclosure", "contrato de arrendamiento", "lease"
            ],
            DocumentType.PAYROLL: [
                "nómina", "payroll", "planilla de pago", "payment slip",
                "salario", "salary", "wage", "deducciones", "deductions",
                "empleado", "employee", "empleador", "employer",
                "período de pago", "pay period", "neto a pagar", "net pay",
                "bruto", "gross", "seguro social", "social security"
            ],
            DocumentType.INSURANCE_CLAIM: [
                "reclamo", "claim", "seguro", "insurance", "siniestro",
                "accident", "póliza", "policy", "asegurado", "insured",
                "monto del reclamo", "claim amount", "fecha del siniestro",
                "loss date", "evidencia", "evidence", "daño", "damage",
                "cobertura", "coverage", "deducible", "deductible"
            ],
            DocumentType.SHIPPING_DOCUMENT: [
                "guía de despacho", "shipping document", "guía de envío",
                "delivery note", "remesa", "remittance", "tracking number",
                "número de seguimiento", "dirección de entrega",
                "delivery address", "transportista", "carrier",
                "peso", "weight", "dimensiones", "dimensions"
            ],
            DocumentType.HR_RESUME: [
                "currículum", "resume", "cv", "curriculum vitae",
                "experiencia", "experience", "educación", "education",
                "habilidades", "skills", "competencias", "competencies",
                "referencias", "references", "candidato", "candidate",
                "años de experiencia", "years of experience", "seniority"
            ],
            DocumentType.TAX_DOCUMENT: [
                "declaración de impuestos", "tax return", "formulario tributario",
                "tax form", "irs", "sii", "renta", "income tax",
                "impuesto a la renta", "contribuyente", "taxpayer",
                "ingresos", "income", "gastos", "expenses", "deducciones fiscales",
                "tax deductions", "formulario", "form"
            ],
            DocumentType.PURCHASE_ORDER: [
                "orden de compra", "purchase order", "po", "oc",
                "solicitud de compra", "purchase request", "requisición",
                "requisition", "proveedor", "supplier", "fecha de entrega",
                "delivery date", "cantidad", "quantity", "precio unitario",
                "unit price", "número de orden", "order number"
            ]
        }
        
        # Patrones regex por tipo
        self.patterns: Dict[DocumentType, List[str]] = {
            DocumentType.INVOICE: [
                r"factura\s*#?\s*\d+",
                r"invoice\s*#?\s*\d+",
                r"total\s*:?\s*\$?\s*[\d,]+\.?\d*",
                r"monto\s*total\s*:?\s*\$?\s*[\d,]+\.?\d*"
            ],
            DocumentType.BANK_STATEMENT: [
                r"account\s*:?\s*\d+",
                r"cuenta\s*:?\s*\d+",
                r"balance\s*:?\s*\$?\s*[\d,]+\.?\d*",
                r"saldo\s*:?\s*\$?\s*[\d,]+\.?\d*"
            ],
            DocumentType.CONTRACT: [
                r"contrato\s+de\s+\w+",
                r"contract\s+for\s+\w+",
                r"between\s+\w+\s+and\s+\w+",
                r"entre\s+\w+\s+y\s+\w+"
            ],
            DocumentType.HR_RESUME: [
                r"curriculum\s+vitae",
                r"resume",
                r"experiencia\s+profesional",
                r"professional\s+experience"
            ]
        }
        
        # Campos estructurales que indican tipo
        self.structural_fields: Dict[DocumentType, List[str]] = {
            DocumentType.INVOICE: ["invoice_number", "invoice_date", "line_items", "total_amount"],
            DocumentType.BANK_STATEMENT: ["account_number", "transactions", "balance", "statement_date"],
            DocumentType.CONTRACT: ["parties", "effective_date", "clauses", "signatures"],
            DocumentType.PAYROLL: ["employee_id", "pay_period", "gross_pay", "net_pay"],
            DocumentType.INSURANCE_CLAIM: ["policy_number", "claim_number", "loss_date", "claim_amount"]
        }
    
    def classify(self, text: str, metadata: Optional[Dict] = None) -> Tuple[DocumentType, float]:
        """
        Clasifica un documento basado en su texto.
        
        Args:
            text: Texto extraído del PDF
            metadata: Metadatos opcionales del documento
            
        Returns:
            Tuple[DocumentType, confidence]: Tipo detectado y nivel de confianza (0-1)
        """
        if not text or len(text.strip()) < 10:
            return DocumentType.GENERIC_DOCUMENT, 0.0
        
        text_lower = text.lower()
        scores: Dict[DocumentType, float] = {}
        
        # 1. Scoring por palabras clave (peso: 0.6)
        for doc_type, keywords in self.keywords.items():
            matches = sum(1 for keyword in keywords if keyword.lower() in text_lower)
            if matches > 0:
                # Normalizar por cantidad de keywords del tipo
                keyword_score = min(matches / len(keywords) * 2, 1.0) * 0.6
                scores[doc_type] = scores.get(doc_type, 0.0) + keyword_score
        
        # 2. Scoring por patrones regex (peso: 0.3)
        for doc_type, patterns_list in self.patterns.items():
            pattern_matches = sum(1 for pattern in patterns_list if re.search(pattern, text_lower, re.IGNORECASE))
            if pattern_matches > 0:
                pattern_score = min(pattern_matches / len(patterns_list) * 2, 1.0) * 0.3
                scores[doc_type] = scores.get(doc_type, 0.0) + pattern_score
        
        # 3. Scoring por estructura (peso: 0.1)
        # Detectar campos comunes que indican tipo
        if metadata:
            for doc_type, fields in self.structural_fields.items():
                field_matches = sum(1 for field in fields if field in str(metadata).lower())
                if field_matches > 0:
                    struct_score = (field_matches / len(fields)) * 0.1
                    scores[doc_type] = scores.get(doc_type, 0.0) + struct_score
        
        # 4. Detección de contexto adicional
        # Facturas suelen tener números de orden de compra
        if "orden de compra" in text_lower or "purchase order" in text_lower:
            if DocumentType.INVOICE in scores:
                scores[DocumentType.INVOICE] += 0.1
        
        # Contratos suelen mencionar "jurisdicción" o "ley aplicable"
        if "jurisdicción" in text_lower or "applicable law" in text_lower:
            if DocumentType.CONTRACT in scores:
                scores[DocumentType.CONTRACT] += 0.1
        
        # Si no hay scores, es genérico
        if not scores:
            return DocumentType.GENERIC_DOCUMENT, 0.0
        
        # Obtener el tipo con mayor score
        best_type = max(scores.items(), key=lambda x: x[1])
        confidence = min(best_type[1], 1.0)
        
        # Si la confianza es muy baja, marcar como genérico
        if confidence < 0.2:
            return DocumentType.GENERIC_DOCUMENT, confidence
        
        return best_type[0], confidence
    
    def classify_batch(self, texts: List[str], metadata_list: Optional[List[Dict]] = None) -> List[Tuple[DocumentType, float]]:
        """
        Clasifica múltiples documentos en batch.
        
        Args:
            texts: Lista de textos extraídos
            metadata_list: Lista opcional de metadatos
            
        Returns:
            Lista de tuplas (tipo, confianza)
        """
        if metadata_list is None:
            metadata_list = [None] * len(texts)
        
        results = []
        for text, metadata in zip(texts, metadata_list):
            doc_type, confidence = self.classify(text, metadata)
            results.append((doc_type, confidence))
        
        return results










