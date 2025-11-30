"""
Handlers de Integraciones

Cada handler maneja la conexión y búsqueda en una app específica.
"""

from .base_handler import BaseIntegrationHandler
from .google_handler import GoogleHandler
from .microsoft_handler import MicrosoftHandler
from .slack_handler import SlackHandler

# Handlers nuevos
try:
    from .github_handler import GitHubHandler
except ImportError:
    GitHubHandler = None

try:
    from .jira_handler import JiraHandler
except ImportError:
    JiraHandler = None

try:
    from .salesforce_handler import SalesforceHandler
except ImportError:
    SalesforceHandler = None

try:
    from .zendesk_handler import ZendeskHandler
except ImportError:
    ZendeskHandler = None

try:
    from .servicenow_handler import ServiceNowHandler
except ImportError:
    ServiceNowHandler = None

try:
    from .notion_handler import NotionHandler
except ImportError:
    NotionHandler = None

try:
    from .confluence_handler import ConfluenceHandler
except ImportError:
    ConfluenceHandler = None

try:
    from .hubspot_handler import HubSpotHandler
except ImportError:
    HubSpotHandler = None

try:
    from .asana_handler import AsanaHandler
except ImportError:
    AsanaHandler = None

try:
    from .trello_handler import TrelloHandler
except ImportError:
    TrelloHandler = None

try:
    from .quickbooks_handler import QuickBooksHandler
except ImportError:
    QuickBooksHandler = None

try:
    from .workday_handler import WorkdayHandler
except ImportError:
    WorkdayHandler = None

try:
    from .powerbi_handler import PowerBIHandler
except ImportError:
    PowerBIHandler = None

try:
    from .sharepoint_handler import SharePointHandler
except ImportError:
    SharePointHandler = None

__all__ = [
    "BaseIntegrationHandler",
    "GoogleHandler",
    "MicrosoftHandler",
    "SlackHandler",
    "HubSpotHandler",
    "AsanaHandler",
    "TrelloHandler",
    "QuickBooksHandler",
    "WorkdayHandler",
    "PowerBIHandler",
    "SharePointHandler",
]
