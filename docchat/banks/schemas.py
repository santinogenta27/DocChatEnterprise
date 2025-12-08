"""
Schemas Pydantic para datos estructurados del modo BANKS.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class EntityExtraction(BaseModel):
    """Entidades extraídas de documentos."""
    name: Optional[str] = None
    id_number: Optional[str] = None
    id_type: Optional[str] = None  # DNI, Passport, etc.
    address: Optional[str] = None
    date_of_birth: Optional[str] = None
    nationality: Optional[str] = None
    ubo: List[Dict[str, Any]] = Field(default_factory=list)  # Ultimate Beneficial Owner
    pep_status: Optional[str] = None  # PEP level 1, 2, 3, or None
    transactions: List[Dict[str, Any]] = Field(default_factory=list)
    extracted_at: datetime = Field(default_factory=datetime.now)


class SanctionHit(BaseModel):
    """Hit de screening contra listas de sanciones."""
    name: str
    match_type: str  # "exact", "fuzzy", "transliteration"
    confidence: float  # 0.0 - 1.0
    list_name: str  # "OFAC", "EU Consolidated", "UN", "World-Check", etc.
    list_id: Optional[str] = None
    reason: Optional[str] = None
    url: Optional[str] = None
    checked_at: datetime = Field(default_factory=datetime.now)


class PEPHit(BaseModel):
    """Hit de PEP (Politically Exposed Person)."""
    name: str
    pep_level: int  # 1, 2, or 3
    country: Optional[str] = None
    position: Optional[str] = None
    match_confidence: float
    source: str
    checked_at: datetime = Field(default_factory=datetime.now)


class AdverseMediaHit(BaseModel):
    """Hit de adverse media (noticias negativas)."""
    name: str
    title: str
    url: str
    source: str
    date: Optional[str] = None
    relevance_score: float
    checked_at: datetime = Field(default_factory=datetime.now)


class RiskScore(BaseModel):
    """Score de riesgo calculado."""
    total_score: int = Field(ge=1, le=100)
    country_risk: float = Field(ge=0.0, le=1.0)
    pep_risk: float = Field(ge=0.0, le=1.0)
    adverse_media_risk: float = Field(ge=0.0, le=1.0)
    transaction_risk: float = Field(ge=0.0, le=1.0)
    ubo_risk: float = Field(ge=0.0, le=1.0)
    breakdown: Dict[str, Any] = Field(default_factory=dict)
    explanation: str
    evidence: List[Dict[str, Any]] = Field(default_factory=list)  # Página, línea, etc.
    calculated_at: datetime = Field(default_factory=datetime.now)


class SARData(BaseModel):
    """Datos para generar un SAR (Suspicious Activity Report)."""
    report_id: str
    client_name: str
    client_id: str
    report_type: str  # "SAR", "CTR", etc.
    jurisdiction: str  # "US", "EU", "MX", "CO", etc.
    suspicious_activity: str
    amount: Optional[float] = None
    currency: str = "USD"
    risk_score: int
    evidence: List[Dict[str, Any]]
    filed_at: Optional[datetime] = None
    status: str = "draft"  # "draft", "filed", "rejected"


class SteeringCommand(BaseModel):
    """Comando de steering humano."""
    command_id: str
    command_text: str
    parsed_action: Dict[str, Any]
    applied_at: datetime = Field(default_factory=datetime.now)
    applied_by: Optional[str] = None
    affected_agents: List[str] = Field(default_factory=list)
    result: Optional[Dict[str, Any]] = None


class AuditLog(BaseModel):
    """Log de auditoría."""
    log_id: str
    timestamp: datetime = Field(default_factory=datetime.now)
    agent: str
    action: str
    input_data: Dict[str, Any]
    output_data: Dict[str, Any]
    user_id: Optional[str] = None
    steering_applied: Optional[str] = None
    evidence: List[Dict[str, Any]] = Field(default_factory=list)

