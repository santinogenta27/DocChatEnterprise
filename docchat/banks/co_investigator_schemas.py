"""
Schemas y dataclasses para Co-Investigator AI.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, List, Optional


@dataclass
class CrimeTypology:
    """Tipología de crimen financiero detectada."""
    typology_type: str  # elder_exploitation, romance_scam, money_mule, etc.
    confidence_score: float  # 0.0 - 1.0
    risk_indicators: List[str]
    supporting_evidence: List[Dict[str, Any]]
    detected_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class SARNarrative:
    """Narrativa de SAR generada."""
    narrative_id: str
    subject_details: Dict[str, Any]
    suspicious_activity_description: str
    date_range: Dict[str, str]
    institution_information: Dict[str, Any]
    filer_contact: Dict[str, Any]
    narrative_text: str
    supporting_documentation: List[str]
    compliance_score: float  # 0.0 - 1.0
    confidence_scores: Dict[str, float]
    generated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    reviewed_by: Optional[str] = None
    feedback_applied: List[str] = field(default_factory=list)













