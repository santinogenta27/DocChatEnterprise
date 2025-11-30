"""
Manejador de Callback OAuth

Procesa los callbacks OAuth y completa la conexión automáticamente.
"""

from __future__ import annotations

import requests
from typing import Dict, Any, Optional
from .integration_manager import IntegrationManager, IntegrationType


class OAuthCallbackHandler:
    """Maneja callbacks OAuth y completa conexiones automáticamente."""
    
    def __init__(self, integration_manager: IntegrationManager, config):
        self.integration_manager = integration_manager
        self.config = config
    
    def handle_google_callback(self, code: str, state: Optional[str] = None) -> Dict[str, Any]:
        """Maneja callback de Google OAuth."""
        client_id = getattr(self.config, 'google_client_id', '')
        client_secret = getattr(self.config, 'google_client_secret', '')
        redirect_uri = f"{getattr(self.config, 'oauth_redirect_url', 'http://localhost:7860/oauth/callback')}?provider=google"
        
        # Intercambiar código por tokens
        token_url = "https://oauth2.googleapis.com/token"
        data = {
            "code": code,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code"
        }
        
        response = requests.post(token_url, data=data)
        if response.status_code != 200:
            return {"success": False, "error": response.text}
        
        tokens = response.json()
        access_token = tokens.get("access_token")
        refresh_token = tokens.get("refresh_token")
        expires_in = tokens.get("expires_in", 3600)
        
        # Determinar tipo de integración basado en scopes
        scopes = tokens.get("scope", "").split()
        if "gmail.readonly" in scopes:
            integration_type = IntegrationType.GMAIL
        elif "drive.readonly" in scopes:
            integration_type = IntegrationType.GOOGLE_DRIVE
        else:
            integration_type = IntegrationType.GMAIL  # Default
        
        # Conectar integración
        connection = self.integration_manager.connect_integration(
            integration_type=integration_type,
            user_id="user",  # En producción, usar ID real
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=None  # Se calculará basado en expires_in
        )
        
        return {
            "success": True,
            "connection": connection,
            "message": f"✅ {integration_type.value} conectado exitosamente"
        }
    
    def handle_microsoft_callback(self, code: str, state: Optional[str] = None) -> Dict[str, Any]:
        """Maneja callback de Microsoft OAuth."""
        client_id = getattr(self.config, 'microsoft_client_id', '')
        client_secret = getattr(self.config, 'microsoft_client_secret', '')
        redirect_uri = f"{getattr(self.config, 'oauth_redirect_url', 'http://localhost:7860/oauth/callback')}?provider=microsoft"
        
        token_url = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
        data = {
            "code": code,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code"
        }
        
        response = requests.post(token_url, data=data)
        if response.status_code != 200:
            return {"success": False, "error": response.text}
        
        tokens = response.json()
        access_token = tokens.get("access_token")
        refresh_token = tokens.get("refresh_token")
        
        # Por ahora, conectar como Outlook (se puede mejorar detectando scope)
        connection = self.integration_manager.connect_integration(
            integration_type=IntegrationType.OUTLOOK,
            user_id="user",
            access_token=access_token,
            refresh_token=refresh_token
        )
        
        return {
            "success": True,
            "connection": connection,
            "message": "✅ Microsoft conectado exitosamente"
        }
    
    def handle_callback(self, provider: str, code: str, state: Optional[str] = None) -> Dict[str, Any]:
        """Maneja callback genérico según proveedor."""
        if provider == "google":
            return self.handle_google_callback(code, state)
        elif provider == "microsoft":
            return self.handle_microsoft_callback(code, state)
        else:
            return {"success": False, "error": f"Proveedor no soportado: {provider}"}


