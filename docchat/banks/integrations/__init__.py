"""
Integraciones para el modo BANKS.
"""

try:
    from .salesforce_integration import SalesforceIntegration
    SALESFORCE_AVAILABLE = True
except ImportError:
    SALESFORCE_AVAILABLE = False
    SalesforceIntegration = None

try:
    from .jira_integration import JiraIntegration
    JIRA_AVAILABLE = True
except ImportError:
    JIRA_AVAILABLE = False
    JiraIntegration = None

from .slack_integration import SlackIntegration, TeamsIntegration
from .worldcheck_integration import WorldCheckIntegration
from .biometric_verification import BiometricVerification

__all__ = [
    "SalesforceIntegration",
    "JiraIntegration",
    "SlackIntegration",
    "TeamsIntegration",
    "WorldCheckIntegration",
    "BiometricVerification",
]

