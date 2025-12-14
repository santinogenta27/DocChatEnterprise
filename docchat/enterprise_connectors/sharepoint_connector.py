"""
SharePoint / OneDrive Connector - Conecta a Microsoft 365.

Usa Microsoft Graph API con:
- Webhooks (subscriptions) para notificaciones en tiempo real
- Polling como fallback
- OAuth2 con Azure AD
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from urllib.parse import urlencode

import requests

from .base_connector import BaseEnterpriseConnector, ConnectorConfig, ConnectorStatus


class SharePointConnector(BaseEnterpriseConnector):
    """Conector para SharePoint / OneDrive usando Microsoft Graph API."""
    
    GRAPH_API_BASE = "https://graph.microsoft.com/v1.0"
    AUTH_BASE = "https://login.microsoftonline.com"
    
    def __init__(self, config: ConnectorConfig, process_pdf_callback=None):
        super().__init__(config, process_pdf_callback)
        self.subscription_id: Optional[str] = None  # ID de la suscripción webhook
    
    async def authenticate(self) -> bool:
        """Autentica usando OAuth2 con Azure AD o Access Token directo."""
        try:
            # Si tenemos Access Token directo (del Graph Explorer), usarlo directamente
            if self.config.access_token and not self.config.client_id:
                # Verificar que el token funcione haciendo una llamada de prueba
                try:
                    url = f"{self.GRAPH_API_BASE}/me"
                    headers = {"Authorization": f"Bearer {self.config.access_token}"}
                    response = self.session.get(url, headers=headers)
                    if response.status_code == 200:
                        print("✅ [SharePoint] Autenticado con Access Token directo")
                        return True
                    else:
                        print(f"⚠️ [SharePoint] Token inválido o expirado: {response.status_code}")
                        return False
                except Exception as e:
                    print(f"❌ [SharePoint] Error validando token: {e}")
                    return False
            
            if not self.config.tenant_id:
                print("❌ [SharePoint] tenant_id requerido para autenticación OAuth2")
                return False
            
            # Si ya tenemos refresh token, usarlo
            if self.config.refresh_token:
                return await self.refresh_access_token()
            
            # Si no, necesitamos autorización del usuario (devolver URL de auth)
            auth_url = self._get_auth_url()
            print(f"🔐 [SharePoint] Autorización requerida. Visita: {auth_url}")
            print("⚠️ [SharePoint] Necesitas implementar el flujo OAuth2 completo con redirect")
            
            # Por ahora, retornar False (requiere implementación del flujo completo)
            return False
            
        except Exception as e:
            print(f"❌ [SharePoint] Error en autenticación: {e}")
            return False
    
    def _get_auth_url(self) -> str:
        """Genera la URL de autorización OAuth2."""
        params = {
            "client_id": self.config.client_id,
            "response_type": "code",
            "redirect_uri": self.config.redirect_uri or "http://localhost:5001/oauth/callback",
            "response_mode": "query",
            "scope": "Files.Read.All Sites.Read.All offline_access",
            "state": self.config.connector_id
        }
        return f"{self.AUTH_BASE}/{self.config.tenant_id}/oauth2/v2.0/authorize?{urlencode(params)}"
    
    async def refresh_access_token(self) -> bool:
        """Refresca el access token usando el refresh token."""
        try:
            if not self.config.refresh_token:
                return False
            
            url = f"{self.AUTH_BASE}/{self.config.tenant_id}/oauth2/v2.0/token"
            data = {
                "client_id": self.config.client_id,
                "client_secret": self.config.client_secret,
                "refresh_token": self.config.refresh_token,
                "grant_type": "refresh_token",
                "scope": "Files.Read.All Sites.Read.All offline_access"
            }
            
            response = self.session.post(url, data=data)
            response.raise_for_status()
            
            token_data = response.json()
            self.config.access_token = token_data["access_token"]
            self.config.refresh_token = token_data.get("refresh_token") or self.config.refresh_token
            
            # Calcular expiración (normalmente 3600 segundos)
            expires_in = token_data.get("expires_in", 3600)
            self.config.token_expires_at = datetime.now() + timedelta(seconds=expires_in - 300)  # 5 min buffer
            
            print("✅ [SharePoint] Token refrescado")
            return True
            
        except Exception as e:
            print(f"❌ [SharePoint] Error refrescando token: {e}")
            return False
    
    async def list_new_files(self, since: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """Lista archivos nuevos desde SharePoint/OneDrive."""
        try:
            await self._ensure_authenticated()
            
            files = []
            
            # Si hay carpetas específicas configuradas, buscar en ellas
            if self.config.folder_paths:
                for folder_path in self.config.folder_paths:
                    folder_files = await self._list_files_in_folder(folder_path, since)
                    files.extend(folder_files)
            else:
                # Buscar en OneDrive raíz
                files = await self._list_files_in_drive("me/drive/root", since)
            
            return files
            
        except Exception as e:
            print(f"❌ [SharePoint] Error listando archivos: {e}")
            return []
    
    async def _list_files_in_drive(self, drive_path: str, since: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """Lista archivos en un drive específico."""
        files = []
        url = f"{self.GRAPH_API_BASE}/{drive_path}/children"
        
        headers = {"Authorization": f"Bearer {self.config.access_token}"}
        params = {
            "$filter": "file ne null",  # Solo archivos
            "$orderby": "lastModifiedDateTime desc",
            "$top": 100
        }
        
        if since:
            # Filtrar por fecha de modificación
            since_str = since.strftime("%Y-%m-%dT%H:%M:%SZ")
            params["$filter"] = f"file ne null and lastModifiedDateTime gt {since_str}"
        
        while url:
            response = self.session.get(url, headers=headers, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            for item in data.get("value", []):
                if item.get("file"):
                    file_info = {
                        "file_id": item["id"],
                        "file_name": item["name"],
                        "file_url": item.get("@microsoft.graph.downloadUrl") or item.get("webUrl"),
                        "file_size": item.get("size", 0),
                        "modified_at": datetime.fromisoformat(item["lastModifiedDateTime"].replace("Z", "+00:00")),
                        "metadata": {
                            "mime_type": item.get("file", {}).get("mimeType"),
                            "web_url": item.get("webUrl"),
                            "parent_id": item.get("parentReference", {}).get("id")
                        }
                    }
                    files.append(file_info)
            
            # Paginación
            url = data.get("@odata.nextLink")
            params = None  # La URL nextLink ya incluye los parámetros
        
        return files
    
    async def _list_files_in_folder(self, folder_path: str, since: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """Lista archivos en una carpeta específica (por path)."""
        # Convertir path a ID de carpeta o usar directamente
        # Por simplicidad, asumimos que folder_path es un ID o path relativo
        if folder_path.startswith("/"):
            folder_path = folder_path[1:]
        
        drive_path = f"me/drive/root:/{folder_path}"
        return await self._list_files_in_drive(drive_path, since)
    
    async def download_file(self, file_url: str, file_id: str) -> Tuple[bytes, Dict[str, Any]]:
        """Descarga un archivo desde SharePoint/OneDrive."""
        try:
            await self._ensure_authenticated()
            
            # Si no hay downloadUrl directa, obtenerla desde Graph API
            if not file_url or "downloadUrl" not in file_url:
                url = f"{self.GRAPH_API_BASE}/me/drive/items/{file_id}/content"
            else:
                url = file_url
            
            headers = {"Authorization": f"Bearer {self.config.access_token}"}
            response = self.session.get(url, headers=headers, stream=True)
            response.raise_for_status()
            
            content = response.content
            metadata = {
                "content_type": response.headers.get("Content-Type"),
                "content_length": len(content),
                "file_id": file_id
            }
            
            return content, metadata
            
        except Exception as e:
            print(f"❌ [SharePoint] Error descargando archivo {file_id}: {e}")
            raise
    
    async def setup_webhook(self, webhook_url: str) -> bool:
        """Configura un webhook (subscription) en Microsoft Graph."""
        try:
            await self._ensure_authenticated()
            
            # Crear subscription para cambios en archivos
            url = f"{self.GRAPH_API_BASE}/subscriptions"
            headers = {
                "Authorization": f"Bearer {self.config.access_token}",
                "Content-Type": "application/json"
            }
            
            # Calcular expiración (máximo 3 días para Graph API)
            expiration = datetime.now() + timedelta(days=2, hours=23)
            
            payload = {
                "changeType": "created,updated",
                "notificationUrl": webhook_url,
                "resource": "/me/drive/root",  # Monitorear OneDrive raíz
                "expirationDateTime": expiration.isoformat(),
                "clientState": self.config.webhook_secret or "default_secret"
            }
            
            response = self.session.post(url, headers=headers, json=payload)
            
            if response.status_code == 201:
                data = response.json()
                self.subscription_id = data["id"]
                print(f"✅ [SharePoint] Webhook configurado: {self.subscription_id}")
                return True
            else:
                print(f"⚠️ [SharePoint] No se pudo configurar webhook: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ [SharePoint] Error configurando webhook: {e}")
            return False
    
    async def delete_webhook(self) -> bool:
        """Elimina el webhook configurado."""
        try:
            if not self.subscription_id:
                return True
            
            await self._ensure_authenticated()
            
            url = f"{self.GRAPH_API_BASE}/subscriptions/{self.subscription_id}"
            headers = {"Authorization": f"Bearer {self.config.access_token}"}
            
            response = self.session.delete(url, headers=headers)
            
            if response.status_code in [204, 404]:
                self.subscription_id = None
                print("✅ [SharePoint] Webhook eliminado")
                return True
            else:
                print(f"⚠️ [SharePoint] Error eliminando webhook: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ [SharePoint] Error eliminando webhook: {e}")
            return False
    
    def handle_webhook_notification(self, notification: Dict[str, Any]) -> bool:
        """
        Maneja una notificación de webhook de Microsoft Graph.
        
        Debe ser llamado desde el endpoint de webhook.
        """
        try:
            # Validar clientState
            if self.config.webhook_secret:
                if notification.get("clientState") != self.config.webhook_secret:
                    print("⚠️ [SharePoint] Webhook notification con clientState inválido")
                    return False
            
            # Procesar cada cambio
            value = notification.get("value", [])
            for change in value:
                resource = change.get("resource")
                change_type = change.get("changeType")
                
                if change_type in ["created", "updated"]:
                    # Obtener metadata del archivo
                    file_id = resource.split("/")[-1] if "/" in resource else resource
                    asyncio.create_task(self._process_webhook_file(file_id))
            
            return True
            
        except Exception as e:
            print(f"❌ [SharePoint] Error procesando webhook notification: {e}")
            return False
    
    async def _process_webhook_file(self, file_id: str):
        """Procesa un archivo detectado vía webhook."""
        try:
            await self._ensure_authenticated()
            
            # Obtener metadata del archivo
            url = f"{self.GRAPH_API_BASE}/me/drive/items/{file_id}"
            headers = {"Authorization": f"Bearer {self.config.access_token}"}
            
            response = self.session.get(url, headers=headers)
            response.raise_for_status()
            
            item = response.json()
            
            if item.get("file"):
                file_info = {
                    "file_id": item["id"],
                    "file_name": item["name"],
                    "file_url": item.get("@microsoft.graph.downloadUrl") or item.get("webUrl"),
                    "file_size": item.get("size", 0),
                    "modified_at": datetime.fromisoformat(item["lastModifiedDateTime"].replace("Z", "+00:00")),
                    "metadata": {
                        "mime_type": item.get("file", {}).get("mimeType"),
                        "web_url": item.get("webUrl")
                    }
                }
                
                await self.process_new_file(file_info)
                
        except Exception as e:
            print(f"❌ [SharePoint] Error procesando archivo de webhook {file_id}: {e}")

