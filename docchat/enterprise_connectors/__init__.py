"""
Enterprise Connectors - Sistema de conexión automática a apps enterprise.

Conecta automáticamente a:
- SharePoint / OneDrive
- AWS S3
- Google Drive
- Salesforce
- ServiceNow

Detecta nuevos PDFs y los procesa automáticamente usando webhooks o polling.
"""

from .base_connector import BaseEnterpriseConnector, ConnectorStatus, ConnectorConfig
from .sharepoint_connector import SharePointConnector
from .aws_s3_connector import AWSS3Connector
from .google_drive_connector import GoogleDriveConnector
from .salesforce_connector import SalesforceConnector
from .servicenow_connector import ServiceNowConnector
from .connector_manager import EnterpriseConnectorManager

__all__ = [
    "BaseEnterpriseConnector",
    "ConnectorStatus",
    "ConnectorConfig",
    "SharePointConnector",
    "AWSS3Connector",
    "GoogleDriveConnector",
    "SalesforceConnector",
    "ServiceNowConnector",
    "EnterpriseConnectorManager",
]

