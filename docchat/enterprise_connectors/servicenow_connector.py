"""
ServiceNow Connector - Conecta a ServiceNow.

Usa ServiceNow REST API con:
- Webhooks vía Outbound REST Messages
- Polling como fallback
- OAuth2 o Basic Auth
"""

from __future__ import annotations

import asyncio
import base64
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple

from .base_connector import BaseEnterpriseConnector, ConnectorConfig, ConnectorStatus


class ServiceNowConnector(BaseEnterpriseConnector):
    """Conector para ServiceNow usando REST API."""
    
    def __init__(self, config: ConnectorConfig, process_pdf_callback=None):
        super().__init__(config, process_pdf_callback)
        self.instance_url = config.extra_config.get("instance_url")  # ej: https://yourinstance.service-now.com
        self.table_name = config.extra_config.get("table_name", "sys_attachment")  # Tabla donde están los PDFs
    
    async def authenticate(self) -> bool:
        """Autentica usando OAuth2, Basic Auth o Access Token directo."""
        try:
            # Si tenemos Access Token directo, usarlo directamente
            if self.config.access_token and not self.config.extra_config.get("username"):
                # Verificar que el token funcione
                try:
                    url = f"{self.instance_url}/api/now/table/sys_user"
                    headers = {
                        "Authorization": f"Bearer {self.config.access_token}",
                        "Accept": "application/json"
                    }
                    response = self.session.get(url, headers=headers, params={"sysparm_limit": 1})
                    if response.status_code == 200:
                        print("✅ [ServiceNow] Autenticado con Access Token directo")
                        return True
                    else:
                        print(f"⚠️ [ServiceNow] Token inválido o expirado: {response.status_code}")
                        return False
                except Exception as e:
                    print(f"❌ [ServiceNow] Error validando token: {e}")
                    return False
            
            username = self.config.extra_config.get("username")
            password = self.config.extra_config.get("password")
            
            if not username or not password:
                print("❌ [ServiceNow] username y password requeridos para Basic Auth")
                return False
            
            # Usar Basic Auth (más simple) o OAuth2
            auth_type = self.config.extra_config.get("auth_type", "basic")
            
            if auth_type == "basic":
                # Basic Auth
                credentials = f"{username}:{password}"
                encoded = base64.b64encode(credentials.encode()).decode()
                self.config.access_token = encoded  # Guardar para usar en headers
                print("✅ [ServiceNow] Autenticado con Basic Auth")
                return True
            else:
                # OAuth2 (si está configurado)
                if self.config.client_id and self.config.client_secret:
                    return await self._oauth2_authenticate()
                else:
                    print("⚠️ [ServiceNow] OAuth2 requiere client_id y client_secret")
                    return False
                    
        except Exception as e:
            print(f"❌ [ServiceNow] Error en autenticación: {e}")
            return False
    
    async def _oauth2_authenticate(self) -> bool:
        """Autentica usando OAuth2."""
        try:
            token_url = f"{self.instance_url}/oauth_token.do"
            data = {
                "grant_type": "password",
                "client_id": self.config.client_id,
                "client_secret": self.config.client_secret,
                "username": self.config.extra_config.get("username"),
                "password": self.config.extra_config.get("password")
            }
            
            response = self.session.post(token_url, data=data)
            response.raise_for_status()
            
            token_data = response.json()
            self.config.access_token = token_data["access_token"]
            expires_in = token_data.get("expires_in", 3600)
            self.config.token_expires_at = datetime.now() + timedelta(seconds=expires_in - 300)
            
            print("✅ [ServiceNow] Autenticado con OAuth2")
            return True
            
        except Exception as e:
            print(f"❌ [ServiceNow] Error en OAuth2: {e}")
            return False
    
    async def refresh_access_token(self) -> bool:
        """Refresca el token OAuth2 o re-autentica con Basic Auth."""
        if self.config.extra_config.get("auth_type") == "basic":
            return True  # Basic Auth no expira
        return await self._oauth2_authenticate()
    
    async def list_new_files(self, since: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """Lista archivos nuevos (attachments) en ServiceNow."""
        try:
            await self._ensure_authenticated()
            
            if not self.instance_url:
                print("❌ [ServiceNow] instance_url no configurado")
                return []
            
            files = []
            
            # Construir query para sys_attachment
            query = "content_type=application/pdf^ORcontent_type=application/x-pdf"
            
            if since:
                since_str = since.strftime("%Y-%m-%d %H:%M:%S")
                query += f"^sys_updated_on>{since_str}"
            
            url = f"{self.instance_url}/api/now/table/{self.table_name}"
            headers = self._get_auth_headers()
            params = {
                "sysparm_query": query,
                "sysparm_fields": "sys_id,file_name,size_bytes,sys_updated_on,content_type,download_link",
                "sysparm_limit": 100
            }
            
            response = self.session.get(url, headers=headers, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            for record in data.get("result", []):
                updated_on = datetime.fromisoformat(record["sys_updated_on"].replace("Z", "+00:00"))
                
                # Construir URL de descarga
                file_id = record["sys_id"]
                download_url = f"{self.instance_url}/api/now/attachment/{file_id}/file"
                
                file_info = {
                    "file_id": file_id,
                    "file_name": record.get("file_name", "document.pdf"),
                    "file_url": download_url,
                    "file_size": int(record.get("size_bytes", 0)),
                    "modified_at": updated_on.replace(tzinfo=None),
                    "metadata": {
                        "content_type": record.get("content_type"),
                        "sys_id": file_id
                    }
                }
                files.append(file_info)
            
            return files
            
        except Exception as e:
            print(f"❌ [ServiceNow] Error listando archivos: {e}")
            return []
    
    def _get_auth_headers(self) -> Dict[str, str]:
        """Obtiene headers de autenticación."""
        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        
        auth_type = self.config.extra_config.get("auth_type", "basic")
        
        if auth_type == "basic":
            headers["Authorization"] = f"Basic {self.config.access_token}"
        else:
            headers["Authorization"] = f"Bearer {self.config.access_token}"
        
        return headers
    
    async def download_file(self, file_url: str, file_id: str) -> Tuple[bytes, Dict[str, Any]]:
        """Descarga un archivo desde ServiceNow."""
        try:
            await self._ensure_authenticated()
            
            headers = self._get_auth_headers()
            response = self.session.get(file_url, headers=headers)
            response.raise_for_status()
            
            content = response.content
            metadata = {
                "content_type": response.headers.get("Content-Type", "application/pdf"),
                "content_length": len(content),
                "file_id": file_id
            }
            
            return content, metadata
            
        except Exception as e:
            print(f"❌ [ServiceNow] Error descargando archivo {file_id}: {e}")
            raise
    
    async def setup_webhook(self, webhook_url: str) -> bool:
        """
        Configura webhook en ServiceNow usando Outbound REST Message.
        
        Nota: Esto requiere configuración en ServiceNow (Outbound REST Message + Business Rule).
        Por ahora, retornamos False y usamos polling.
        """
        print("⚠️ [ServiceNow] Webhooks requieren configuración en ServiceNow (Outbound REST Message)")
        print("💡 [ServiceNow] Tip: Crea un Outbound REST Message que llame a tu webhook cuando se crea un attachment")
        return False
    
    async def delete_webhook(self) -> bool:
        """No hay webhook que eliminar (se configura en ServiceNow)."""
        return True
    
    async def connect(self, use_webhooks: Optional[bool] = None) -> bool:
        """Conecta a ServiceNow. Usa polling por defecto."""
        return await super().connect(use_webhooks=False)

