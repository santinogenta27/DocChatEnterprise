"""
CRM Integration Module - Deep Integration with Salesforce, HubSpot, Zendesk

This module provides deep CRM integration capabilities for Business AI Support,
allowing the agent to:
- Read customer data in real-time
- Create and update records automatically
- Execute actions and workflows
- Maintain data synchronization
"""

from .base import CRMConnector, CRMConfig, CRMRecord
from .salesforce_connector import SalesforceConnector
from .hubspot_connector import HubSpotConnector
from .zendesk_connector import ZendeskConnector
from .crm_manager import CRMManager

__all__ = [
    'CRMConnector',
    'CRMConfig',
    'CRMRecord',
    'SalesforceConnector',
    'HubSpotConnector',
    'ZendeskConnector',
    'CRMManager',
]

