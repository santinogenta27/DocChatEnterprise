from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, ValidationError, validator


class DocumentType(str, Enum):
    CONTRACT = "contract"
    INVOICE = "invoice"
    RESUME = "resume"
    REPORT = "report"
    POLICY = "policy"
    LEGAL_NOTICE = "legal_notice"
    OTHER = "other"


class ContractSchema(BaseModel):
    parties: List[str] = Field(default_factory=list)
    start_date: Optional[str] = None  # YYYY-MM-DD | null
    end_date: Optional[str] = None  # YYYY-MM-DD | null
    payment_terms: Optional[str] = None
    termination_clause: bool = False
    jurisdiction: Optional[str] = None

    @validator("start_date", "end_date", pre=True)
    def normalize_date(cls, v: Any) -> Optional[str]:
        if v in (None, "", "null", "None"):
            return None
        if isinstance(v, str):
            return v.strip()
        return None


class InvoiceSchema(BaseModel):
    invoice_number: str
    issuer: str
    recipient: str
    total_amount: float
    currency: str
    due_date: Optional[str] = None  # YYYY-MM-DD | null

    @validator("invoice_number", "issuer", "recipient", "currency", pre=True)
    def normalize_str(cls, v: Any) -> str:
        if v is None:
            return ""
        return str(v).strip()

    @validator("due_date", pre=True)
    def normalize_date(cls, v: Any) -> Optional[str]:
        if v in (None, "", "null", "None"):
            return None
        if isinstance(v, str):
            return v.strip()
        return None


class ResumeSchema(BaseModel):
    name: str
    email: Optional[str] = None
    skills: List[str] = Field(default_factory=list)
    years_experience: Optional[float] = None

    @validator("name", pre=True)
    def normalize_name(cls, v: Any) -> str:
        if v is None:
            return ""
        return str(v).strip()

    @validator("email", pre=True)
    def normalize_email(cls, v: Any) -> Optional[str]:
        if v in (None, "", "null", "None"):
            return None
        return str(v).strip()


SCHEMA_MAP = {
    DocumentType.CONTRACT: ContractSchema,
    DocumentType.INVOICE: InvoiceSchema,
    DocumentType.RESUME: ResumeSchema,
}


def validate_data_for_type(document_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Valida el diccionario `data` contra el schema del tipo de documento.
    Devuelve el diccionario normalizado o lanza ValidationError.
    """
    try:
        dtype = DocumentType(document_type)
    except ValueError:
        dtype = DocumentType.OTHER

    schema_cls = SCHEMA_MAP.get(dtype)
    if not schema_cls:
        # Para tipos sin schema específico (report, policy, legal_notice, other),
        # devolvemos el data tal cual, siempre que sea dict.
        return data if isinstance(data, dict) else {}

    model = schema_cls(**(data or {}))
    return model.dict()


def build_success_result(
    document_type: str,
    data: Dict[str, Any],
    confidence: float,
) -> Dict[str, Any]:
    """
    Construye el JSON final estándar para éxito.
    """
    try:
        dtype = DocumentType(document_type)
    except ValueError:
        dtype = DocumentType.OTHER

    # Clamp de confianza
    try:
        c = float(confidence)
    except Exception:
        c = 0.0
    c = max(0.0, min(1.0, c))

    return {
        "status": "success",
        "document_type": dtype.value,
        "data": data,
        "confidence": c,
    }


def build_error_result(
    document_type: str,
    message: str,
) -> Dict[str, Any]:
    """
    Construye el JSON final estándar para error.
    """
    try:
        dtype = DocumentType(document_type)
    except ValueError:
        dtype = DocumentType.OTHER

    return {
        "status": "error",
        "document_type": dtype.value,
        "data": {"error": message},
        "confidence": 0.0,
    }


