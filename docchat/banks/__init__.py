"""
BANKS Mode - Compliance Agent para KYC/AML
Sistema multi-agente especializado en compliance regulatorio para bancos.
"""

from .banks_mode import BanksMode
from .workflow import BanksWorkflow
from .dashboard import BanksDashboard
from .config_manager import BanksConfigManager

try:
    from .co_investigator import CoInvestigatorAI
    CO_INVESTIGATOR_AVAILABLE = True
except ImportError:
    CO_INVESTIGATOR_AVAILABLE = False
    CoInvestigatorAI = None
from .agents import (
    IngestorAgent,
    ExtractorAgent,
    ScreenerAgent,
    RiskEngineAgent,
    SteeringManagerAgent,
    ReportGeneratorAgent,
    ActionExecutorAgent
)

try:
    from .api.banks_api import BanksAPI
    API_AVAILABLE = True
except ImportError:
    API_AVAILABLE = False
    BanksAPI = None

__all__ = [
    "BanksMode",
    "BanksWorkflow",
    "BanksDashboard",
    "BanksConfigManager",
    "IngestorAgent",
    "ExtractorAgent",
    "ScreenerAgent",
    "RiskEngineAgent",
    "SteeringManagerAgent",
    "ReportGeneratorAgent",
    "ActionExecutorAgent",
]

if CO_INVESTIGATOR_AVAILABLE:
    __all__.append("CoInvestigatorAI")

if API_AVAILABLE:
    __all__.append("BanksAPI")

