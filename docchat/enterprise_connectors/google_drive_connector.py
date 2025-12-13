"""
Google Drive Connector - Conecta a Google Drive Enterprise.

Usa Google Drive API v3 con:
- Polling (Drive API no tiene webhooks confiables)
- OAuth2 con Google
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple

try:
    from google.oauth2.credentials import Credentials
    from google.oauth2 import service_account
    from google_auth_oauthlib.flow import Flow
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    from google.auth.transport.requests import Request
    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False

import requests

from .base_connector import BaseEnterpriseConnector, ConnectorConfig, ConnectorStatus


class GoogleDriveConnector(BaseEnterpriseConnector):
    """Conector para Google Drive usando Google Drive API v3."""
    
    SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
    API_NAME = 'drive'
    API_VERSION = 'v3'
    
    def __init__(self, config: ConnectorConfig, process_pdf_callback=None):
        super().__init__(config, process_pdf_callback)
        self.drive_service = None
    
    async def authenticate(self) -> bool:
        """Autentica usando OAuth2 con Google o Access Token directo."""
        try:
            if not GOOGLE_AVAILABLE:
                print("⚠️ [Google Drive] google-api-python-client no está instalado. Instala con: pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib")
                return False
            
            # Si tenemos Access Token directo (del OAuth Playground), usarlo directamente
            if self.config.access_token and not self.config.client_id:
                # Token directo sin refresh token
                creds = Credentials(
                    token=self.config.access_token,
                    token_uri="https://oauth2.googleapis.com/token"
                )
                self.drive_service = build(self.API_NAME, self.API_VERSION, credentials=creds)
                print("✅ [Google Drive] Autenticado con Access Token directo")
                return True
            
            # Si tenemos refresh token, usar credenciales existentes
            if self.config.refresh_token:
                creds = Credentials(
                    token=self.config.access_token,
                    refresh_token=self.config.refresh_token,
                    token_uri="https://oauth2.googleapis.com/token",
                    client_id=self.config.client_id,
                    client_secret=self.config.client_secret
                )
                
                # Refrescar si es necesario
                if creds.expired:
                    creds.refresh(requests.Request())
                    self.config.access_token = creds.token
                    self.config.refresh_token = creds.refresh_token
                    self.config.token_expires_at = creds.expiry
                
                self.drive_service = build(self.API_NAME, self.API_VERSION, credentials=creds)
                print("✅ [Google Drive] Autenticado con credenciales existentes")
                return True
            
            # Si no, necesitamos flujo OAuth2 completo
            print("⚠️ [Google Drive] Necesitas implementar el flujo OAuth2 completo")
            print("💡 [Google Drive] Usa Google OAuth2 Playground o implementa el flujo de autorización")
            return False
            
        except Exception as e:
            print(f"❌ [Google Drive] Error en autenticación: {e}")
            return False
    
    async def refresh_access_token(self) -> bool:
        """Refresca el access token."""
        try:
            if not self.config.refresh_token:
                return False
            
            creds = Credentials(
                token=None,
                refresh_token=self.config.refresh_token,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=self.config.client_id,
                client_secret=self.config.client_secret
            )
            
            creds.refresh(requests.Request())
            self.config.access_token = creds.token
            self.config.refresh_token = creds.refresh_token
            self.config.token_expires_at = creds.expiry
            
            self.drive_service = build(self.API_NAME, self.API_VERSION, credentials=creds)
            print("✅ [Google Drive] Token refrescado")
            return True
            
        except Exception as e:
            print(f"❌ [Google Drive] Error refrescando token: {e}")
            return False
    
    async def list_new_files(self, since: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """Lista archivos nuevos en Google Drive."""
        try:
            await self._ensure_authenticated()
            
            if not self.drive_service:
                return []
            
            files = []
            page_token = None
            
            # Construir query
            query_parts = [
                "mimeType='application/pdf'",
                "trashed=false"
            ]
            
            if since:
                # Google Drive API usa milisegundos desde epoch
                since_ms = int(since.timestamp() * 1000)
                query_parts.append(f"modifiedTime > '{since.isoformat()}'")
            
            query = " and ".join(query_parts)
            
            # Si hay carpetas específicas, buscar en ellas
            folder_ids = self.config.extra_config.get("folder_ids", [])
            if folder_ids:
                for folder_id in folder_ids:
                    folder_query = f"'{folder_id}' in parents and {query}"
                    folder_files = await self._list_files_with_query(folder_query)
                    files.extend(folder_files)
            else:
                # Buscar en todo Drive
                files = await self._list_files_with_query(query)
            
            return files
            
        except HttpError as e:
            print(f"❌ [Google Drive] Error listando archivos: {e}")
            return []
        except Exception as e:
            print(f"❌ [Google Drive] Error inesperado: {e}")
            return []
    
    async def _list_files_with_query(self, query: str) -> List[Dict[str, Any]]:
        """Lista archivos usando una query de Google Drive API."""
        files = []
        page_token = None
        
        while True:
            try:
                results = self.drive_service.files().list(
                    q=query,
                    pageSize=100,
                    fields="nextPageToken, files(id, name, size, modifiedTime, webViewLink, webContentLink, mimeType)",
                    pageToken=page_token
                ).execute()
                
                items = results.get('files', [])
                
                for item in items:
                    modified_time = datetime.fromisoformat(item['modifiedTime'].replace('Z', '+00:00'))
                    
                    file_info = {
                        "file_id": item['id'],
                        "file_name": item['name'],
                        "file_url": item.get('webContentLink') or item.get('webViewLink'),
                        "file_size": int(item.get('size', 0)),
                        "modified_at": modified_time.replace(tzinfo=None),
                        "metadata": {
                            "mime_type": item.get('mimeType'),
                            "web_view_link": item.get('webViewLink')
                        }
                    }
                    files.append(file_info)
                
                page_token = results.get('nextPageToken')
                if not page_token:
                    break
                    
            except HttpError as e:
                print(f"❌ [Google Drive] Error en query: {e}")
                break
        
        return files
    
    async def download_file(self, file_url: str, file_id: str) -> Tuple[bytes, Dict[str, Any]]:
        """Descarga un archivo desde Google Drive."""
        try:
            await self._ensure_authenticated()
            
            if not self.drive_service:
                raise Exception("Drive service no inicializado")
            
            # Descargar usando la API
            request = self.drive_service.files().get_media(fileId=file_id)
            content = request.execute()
            
            # Obtener metadata
            file_metadata = self.drive_service.files().get(
                fileId=file_id,
                fields="name, size, mimeType, modifiedTime"
            ).execute()
            
            metadata = {
                "content_type": file_metadata.get('mimeType', 'application/pdf'),
                "content_length": len(content),
                "file_id": file_id,
                "file_name": file_metadata.get('name')
            }
            
            return content, metadata
            
        except HttpError as e:
            print(f"❌ [Google Drive] Error descargando archivo {file_id}: {e}")
            raise
        except Exception as e:
            print(f"❌ [Google Drive] Error inesperado: {e}")
            raise
    
    async def setup_webhook(self, webhook_url: str) -> bool:
        """Google Drive API v3 no tiene webhooks confiables. Usar polling."""
        print("⚠️ [Google Drive] Drive API no soporta webhooks directos. Usando polling.")
        return False
    
    async def delete_webhook(self) -> bool:
        """No hay webhook que eliminar."""
        return True
    
    async def connect(self, use_webhooks: Optional[bool] = None) -> bool:
        """Conecta a Google Drive. Siempre usa polling."""
        return await super().connect(use_webhooks=False)

