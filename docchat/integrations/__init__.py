"""
Sistema de Integraciones Nativas

Conecta DocChat Enterprise con las 10 apps más importantes:
- Google Drive / Gmail
- Microsoft Teams / Outlook / OneDrive
- Slack
- Salesforce
- Jira
- GitHub
- Notion
- Confluence
- Zendesk
- ServiceNow
"""

from .integration_manager import IntegrationManager
from .unified_search import UnifiedSearch
from .oauth_handler import OAuthHandler

__all__ = ["IntegrationManager", "UnifiedSearch", "OAuthHandler"]
