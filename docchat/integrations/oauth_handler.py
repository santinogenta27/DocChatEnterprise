"""
Manejador de OAuth

Gestiona autenticación OAuth para todas las integraciones.
"""

from __future__ import annotations

from typing import Dict, Any, Optional
from urllib.parse import urlencode

from .integration_manager import IntegrationType


class OAuthHandler:
    """
    Manejador de OAuth para todas las integraciones.
    
    Genera URLs de autorización y maneja callbacks OAuth.
    """
    
    def __init__(self, config):
        self.config = config
        self.redirect_base_url = getattr(config, 'oauth_redirect_url', 'http://localhost:7860/oauth/callback')
    
    def get_authorization_url(
        self,
        integration_type: IntegrationType,
        state: Optional[str] = None
    ) -> str:
        """
        Genera URL de autorización OAuth.
        
        Args:
            integration_type: Tipo de integración
            state: Estado para seguridad (opcional)
        
        Returns:
            URL de autorización
        """
        if integration_type in [IntegrationType.GOOGLE_DRIVE, IntegrationType.GMAIL]:
            return self._get_google_auth_url(integration_type, state)
        elif integration_type in [IntegrationType.MICROSOFT_TEAMS, IntegrationType.OUTLOOK, IntegrationType.ONEDRIVE]:
            return self._get_microsoft_auth_url(integration_type, state)
        elif integration_type == IntegrationType.SLACK:
            return self._get_slack_auth_url(state)
        elif integration_type == IntegrationType.SALESFORCE:
            return self._get_salesforce_auth_url(state)
        elif integration_type == IntegrationType.JIRA:
            return self._get_jira_auth_url(state)
        elif integration_type == IntegrationType.GITHUB:
            return self._get_github_auth_url(state)
        elif integration_type == IntegrationType.NOTION:
            return self._get_notion_auth_url(state)
        elif integration_type == IntegrationType.CONFLUENCE:
            return self._get_confluence_auth_url(state)
        elif integration_type == IntegrationType.ZENDESK:
            return self._get_zendesk_auth_url(state)
        elif integration_type == IntegrationType.SERVICENOW:
            return self._get_servicenow_auth_url(state)
        else:
            raise ValueError(f"Tipo de integración no soportado: {integration_type}")
    
    def _get_google_auth_url(self, integration_type: IntegrationType, state: Optional[str]) -> str:
        """URL de autorización de Google."""
        client_id = getattr(self.config, 'google_client_id', '')
        
        if not client_id:
            raise ValueError(
                "Google Client ID no configurado. "
                "Necesitas configurar GOOGLE_CLIENT_ID en tu archivo .env o configuración. "
                "Obtén tus credenciales en: https://console.cloud.google.com/apis/credentials"
            )
        
        scopes = 'https://www.googleapis.com/auth/drive.readonly https://www.googleapis.com/auth/gmail.readonly'
        
        if integration_type == IntegrationType.GOOGLE_DRIVE:
            scopes = 'https://www.googleapis.com/auth/drive.readonly'
        elif integration_type == IntegrationType.GMAIL:
            scopes = 'https://www.googleapis.com/auth/gmail.readonly'
        
        params = {
            'client_id': client_id,
            'redirect_uri': f"{self.redirect_base_url}?provider=google",
            'response_type': 'code',
            'scope': scopes,
            'access_type': 'offline',
            'prompt': 'consent',
            'state': state or ''
        }
        
        return f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"
    
    def _get_microsoft_auth_url(self, integration_type: IntegrationType, state: Optional[str]) -> str:
        """URL de autorización de Microsoft."""
        client_id = getattr(self.config, 'microsoft_client_id', '')
        scopes = 'https://graph.microsoft.com/Files.Read.All https://graph.microsoft.com/Mail.Read'
        
        if integration_type == IntegrationType.ONEDRIVE:
            scopes = 'https://graph.microsoft.com/Files.Read.All'
        elif integration_type == IntegrationType.OUTLOOK:
            scopes = 'https://graph.microsoft.com/Mail.Read'
        elif integration_type == IntegrationType.MICROSOFT_TEAMS:
            scopes = 'https://graph.microsoft.com/ChannelMessage.Read.All'
        
        params = {
            'client_id': client_id,
            'redirect_uri': f"{self.redirect_base_url}?provider=microsoft",
            'response_type': 'code',
            'scope': scopes,
            'state': state or ''
        }
        
        return f"https://login.microsoftonline.com/common/oauth2/v2.0/authorize?{urlencode(params)}"
    
    def _get_slack_auth_url(self, state: Optional[str]) -> str:
        """URL de autorización de Slack."""
        client_id = getattr(self.config, 'slack_client_id', '')
        
        params = {
            'client_id': client_id,
            'redirect_uri': f"{self.redirect_base_url}?provider=slack",
            'scope': 'channels:history,groups:history,im:history,mpim:history,search:read',
            'state': state or ''
        }
        
        return f"https://slack.com/oauth/v2/authorize?{urlencode(params)}"
    
    def _get_salesforce_auth_url(self, state: Optional[str]) -> str:
        """URL de autorización de Salesforce."""
        client_id = getattr(self.config, 'salesforce_client_id', '')
        instance_url = getattr(self.config, 'salesforce_instance_url', 'https://login.salesforce.com')
        
        params = {
            'response_type': 'code',
            'client_id': client_id,
            'redirect_uri': f"{self.redirect_base_url}?provider=salesforce",
            'scope': 'api refresh_token',
            'state': state or ''
        }
        
        return f"{instance_url}/services/oauth2/authorize?{urlencode(params)}"
    
    def _get_jira_auth_url(self, state: Optional[str]) -> str:
        """URL de autorización de Jira."""
        client_id = getattr(self.config, 'jira_client_id', '')
        jira_url = getattr(self.config, 'jira_url', 'https://your-domain.atlassian.net')
        
        params = {
            'audience': 'api.atlassian.com',
            'client_id': client_id,
            'scope': 'read:jira-work read:jira-user',
            'redirect_uri': f"{self.redirect_base_url}?provider=jira",
            'state': state or '',
            'response_type': 'code',
            'prompt': 'consent'
        }
        
        return f"https://auth.atlassian.com/authorize?{urlencode(params)}"
    
    def _get_github_auth_url(self, state: Optional[str]) -> str:
        """URL de autorización de GitHub."""
        client_id = getattr(self.config, 'github_client_id', '')
        
        params = {
            'client_id': client_id,
            'redirect_uri': f"{self.redirect_base_url}?provider=github",
            'scope': 'repo read:org read:user',
            'state': state or ''
        }
        
        return f"https://github.com/login/oauth/authorize?{urlencode(params)}"
    
    def _get_notion_auth_url(self, state: Optional[str]) -> str:
        """URL de autorización de Notion."""
        client_id = getattr(self.config, 'notion_client_id', '')
        
        params = {
            'client_id': client_id,
            'redirect_uri': f"{self.redirect_base_url}?provider=notion",
            'response_type': 'code',
            'owner': 'user',
            'state': state or ''
        }
        
        return f"https://api.notion.com/v1/oauth/authorize?{urlencode(params)}"
    
    def _get_confluence_auth_url(self, state: Optional[str]) -> str:
        """URL de autorización de Confluence."""
        # Similar a Jira (ambos son Atlassian)
        return self._get_jira_auth_url(state)
    
    def _get_zendesk_auth_url(self, state: Optional[str]) -> str:
        """URL de autorización de Zendesk."""
        client_id = getattr(self.config, 'zendesk_client_id', '')
        zendesk_url = getattr(self.config, 'zendesk_url', 'https://your-domain.zendesk.com')
        
        params = {
            'response_type': 'code',
            'client_id': client_id,
            'redirect_uri': f"{self.redirect_base_url}?provider=zendesk",
            'scope': 'read',
            'state': state or ''
        }
        
        return f"{zendesk_url}/oauth/authorizations/new?{urlencode(params)}"
    
    def _get_servicenow_auth_url(self, state: Optional[str]) -> str:
        """URL de autorización de ServiceNow."""
        client_id = getattr(self.config, 'servicenow_client_id', '')
        instance_url = getattr(self.config, 'servicenow_instance_url', 'https://your-instance.service-now.com')
        
        params = {
            'response_type': 'code',
            'client_id': client_id,
            'redirect_uri': f"{self.redirect_base_url}?provider=servicenow",
            'scope': 'useraccount',
            'state': state or ''
        }
        
        return f"{instance_url}/oauth_auth.do?{urlencode(params)}"
    
    def handle_callback(
        self,
        provider: str,
        code: str,
        state: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Maneja callback OAuth.
        
        Args:
            provider: Proveedor (google, microsoft, slack, etc.)
            code: Código de autorización
            state: Estado (para verificación)
        
        Returns:
            Dict con tokens y metadata
        """
        # Este método se implementará con cada handler específico
        # Por ahora, retorna estructura básica
        return {
            "provider": provider,
            "code": code,
            "state": state,
            "access_token": None,  # Se obtiene en el handler específico
            "refresh_token": None
        }

