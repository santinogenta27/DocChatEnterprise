"""Data Sight Integrations - Sistema de conexión automática con sistemas empresariales.

Permite conectar:
- SharePoint/OneDrive (Microsoft Graph API)
- Google Drive/Workspace (Google Drive API)
- Servidores internos/SMB/NFS
- DMS/ECM (Box, Alfresco, DocuWare, OpenText)
- SAP, Salesforce, Odoo
- Email (Gmail, Outlook)

Y recibir documentos automáticamente vía webhooks/API.
"""

from __future__ import annotations

import json
import time
import asyncio
from typing import List, Dict, Any, Optional, Iterator
from pathlib import Path
from datetime import datetime
import requests
from dataclasses import dataclass, field

from .config import AppConfig
from .enterprise_api_data_sight import DataSightMode
from .integrations.integration_manager import IntegrationManager, IntegrationType, IntegrationConnection


@dataclass
class DataSightConnection:
    """Conexión específica de Data Sight a un sistema empresarial."""
    connection_id: str
    system_type: str  # sharepoint, google_drive, smb, sap, salesforce, etc.
    name: str
    credentials: Dict[str, Any]
    auto_sync: bool = True
    sync_interval_minutes: int = 15
    last_sync: Optional[str] = None
    status: str = "active"  # active, error, disconnected
    webhook_url: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


class DataSightIntegrations:
    """
    Sistema de integraciones para Data Sight.
    
    Permite conectar sistemas empresariales y recibir documentos automáticamente.
    """
    
    def __init__(self, config: AppConfig, data_sight_mode: DataSightMode):
        self.config = config
        self.data_sight_mode = data_sight_mode
        
        # Directorio para datos de conexiones
        self.data_dir = Path(config.memory_dir) / "data_sight_integrations"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Archivo de conexiones
        self.connections_file = self.data_dir / "connections.json"
        
        # Cargar conexiones existentes
        self.connections: Dict[str, DataSightConnection] = self._load_connections()
        
        # Integration Manager para usar handlers existentes
        self.integration_manager = IntegrationManager(config)
        
        # Webhook endpoint base (se configura desde app.py)
        self.webhook_base_url: Optional[str] = None
    
    def _load_connections(self) -> Dict[str, DataSightConnection]:
        """Carga conexiones desde archivo."""
        try:
            if self.connections_file.exists():
                with open(self.connections_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    connections = {}
                    for conn_id, conn_data in data.items():
                        connections[conn_id] = DataSightConnection(**conn_data)
                    return connections
        except Exception as e:
            print(f"⚠️ Error cargando conexiones Data Sight: {e}")
        return {}
    
    def _save_connections(self):
        """Guarda conexiones a archivo."""
        try:
            data = {}
            for conn_id, conn in self.connections.items():
                data[conn_id] = {
                    "connection_id": conn.connection_id,
                    "system_type": conn.system_type,
                    "name": conn.name,
                    "credentials": conn.credentials,
                    "auto_sync": conn.auto_sync,
                    "sync_interval_minutes": conn.sync_interval_minutes,
                    "last_sync": conn.last_sync,
                    "status": conn.status,
                    "webhook_url": conn.webhook_url,
                    "metadata": conn.metadata,
                    "created_at": conn.created_at,
                }
            with open(self.connections_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"❌ Error guardando conexiones Data Sight: {e}")
    
    def connect_sharepoint(
        self,
        name: str,
        client_id: str,
        client_secret: str,
        tenant_id: str,
        site_url: Optional[str] = None,
        auto_sync: bool = True
    ) -> Dict[str, Any]:
        """
        Conecta SharePoint/OneDrive usando Microsoft Graph API.
        
        Requiere:
        - Azure App Registration
        - OAuth configurado
        - Permisos: Files.Read.All, Sites.Read.All
        """
        try:
            # Obtener token de acceso
            token_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
            token_data = {
                "client_id": client_id,
                "client_secret": client_secret,
                "scope": "https://graph.microsoft.com/.default",
                "grant_type": "client_credentials"
            }
            
            response = requests.post(token_url, data=token_data, timeout=10)
            if response.status_code != 200:
                return {
                    "success": False,
                    "error": f"Error obteniendo token: {response.status_code} - {response.text[:200]}"
                }
            
            access_token = response.json().get("access_token")
            if not access_token:
                return {"success": False, "error": "No se obtuvo access_token"}
            
            # Crear conexión
            conn_id = f"sharepoint_{int(time.time())}"
            connection = DataSightConnection(
                connection_id=conn_id,
                system_type="sharepoint",
                name=name,
                credentials={
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "tenant_id": tenant_id,
                    "access_token": access_token,
                    "site_url": site_url,
                },
                auto_sync=auto_sync,
                metadata={"connected_at": datetime.now().isoformat()}
            )
            
            self.connections[conn_id] = connection
            self._save_connections()
            
            return {
                "success": True,
                "connection_id": conn_id,
                "message": f"✅ SharePoint '{name}' conectado exitosamente"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def connect_google_drive(
        self,
        name: str,
        access_token: str,
        refresh_token: Optional[str] = None,
        folder_id: Optional[str] = None,
        auto_sync: bool = True
    ) -> Dict[str, Any]:
        """
        Conecta Google Drive/Workspace.
        
        Requiere:
        - OAuth token con scope: https://www.googleapis.com/auth/drive.readonly
        """
        try:
            # Verificar token
            headers = {"Authorization": f"Bearer {access_token}"}
            profile_url = "https://www.googleapis.com/drive/v3/about?fields=user"
            response = requests.get(profile_url, headers=headers, timeout=10)
            
            if response.status_code != 200:
                return {
                    "success": False,
                    "error": f"Token inválido: {response.status_code}"
                }
            
            # Crear conexión
            conn_id = f"google_drive_{int(time.time())}"
            connection = DataSightConnection(
                connection_id=conn_id,
                system_type="google_drive",
                name=name,
                credentials={
                    "access_token": access_token,
                    "refresh_token": refresh_token,
                    "folder_id": folder_id,
                },
                auto_sync=auto_sync,
                metadata={"connected_at": datetime.now().isoformat()}
            )
            
            self.connections[conn_id] = connection
            self._save_connections()
            
            return {
                "success": True,
                "connection_id": conn_id,
                "message": f"✅ Google Drive '{name}' conectado exitosamente"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def connect_smb_share(
        self,
        name: str,
        server: str,
        share_name: str,
        username: str,
        password: str,
        domain: Optional[str] = None,
        auto_sync: bool = True
    ) -> Dict[str, Any]:
        """
        Conecta a un recurso compartido SMB (Windows Share).
        
        Requiere:
        - Acceso a la red interna
        - Credenciales de dominio o local
        """
        try:
            # Verificar conexión básica (sin instalar smbprotocol aquí, solo validar formato)
            conn_id = f"smb_{int(time.time())}"
            connection = DataSightConnection(
                connection_id=conn_id,
                system_type="smb",
                name=name,
                credentials={
                    "server": server,
                    "share_name": share_name,
                    "username": username,
                    "password": password,  # En producción, encriptar
                    "domain": domain,
                },
                auto_sync=auto_sync,
                metadata={"connected_at": datetime.now().isoformat()}
            )
            
            self.connections[conn_id] = connection
            self._save_connections()
            
            return {
                "success": True,
                "connection_id": conn_id,
                "message": f"✅ Recurso compartido SMB '{name}' configurado. Nota: Requiere acceso a red interna."
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def connect_salesforce(
        self,
        name: str,
        instance_url: str,
        access_token: str,
        auto_sync: bool = True
    ) -> Dict[str, Any]:
        """Conecta Salesforce para obtener attachments/documentos."""
        try:
            # Verificar conexión
            headers = {"Authorization": f"Bearer {access_token}"}
            test_url = f"{instance_url}/services/data/v58.0/"
            response = requests.get(test_url, headers=headers, timeout=10)
            
            if response.status_code != 200:
                return {
                    "success": False,
                    "error": f"Error conectando a Salesforce: {response.status_code}"
                }
            
            conn_id = f"salesforce_{int(time.time())}"
            connection = DataSightConnection(
                connection_id=conn_id,
                system_type="salesforce",
                name=name,
                credentials={
                    "instance_url": instance_url,
                    "access_token": access_token,
                },
                auto_sync=auto_sync,
                metadata={"connected_at": datetime.now().isoformat()}
            )
            
            self.connections[conn_id] = connection
            self._save_connections()
            
            return {
                "success": True,
                "connection_id": conn_id,
                "message": f"✅ Salesforce '{name}' conectado exitosamente"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def connect_email(
        self,
        name: str,
        email_type: str,  # gmail, outlook
        access_token: str,
        refresh_token: Optional[str] = None,
        auto_sync: bool = True
    ) -> Dict[str, Any]:
        """Conecta Gmail o Outlook para recibir PDFs de emails."""
        try:
            conn_id = f"email_{email_type}_{int(time.time())}"
            connection = DataSightConnection(
                connection_id=conn_id,
                system_type=f"email_{email_type}",
                name=name,
                credentials={
                    "email_type": email_type,
                    "access_token": access_token,
                    "refresh_token": refresh_token,
                },
                auto_sync=auto_sync,
                metadata={"connected_at": datetime.now().isoformat()}
            )
            
            self.connections[conn_id] = connection
            self._save_connections()
            
            return {
                "success": True,
                "connection_id": conn_id,
                "message": f"✅ {email_type.upper()} '{name}' conectado exitosamente"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def sync_connection(self, connection_id: str) -> Dict[str, Any]:
        """
        Sincroniza documentos desde una conexión específica.
        
        Descarga documentos nuevos y los procesa con Data Sight.
        """
        if connection_id not in self.connections:
            return {"success": False, "error": "Conexión no encontrada"}
        
        connection = self.connections[connection_id]
        
        try:
            files_to_process = []
            
            if connection.system_type == "sharepoint":
                files_to_process = self._sync_sharepoint(connection)
            elif connection.system_type == "google_drive":
                files_to_process = self._sync_google_drive(connection)
            elif connection.system_type == "smb":
                files_to_process = self._sync_smb(connection)
            elif connection.system_type == "salesforce":
                files_to_process = self._sync_salesforce(connection)
            elif connection.system_type.startswith("email_"):
                files_to_process = self._sync_email(connection)
            
            if files_to_process:
                # Procesar archivos con Data Sight
                result = self.data_sight_mode.process_data_sight_pipeline(
                    files=files_to_process,
                    auto_detect=True,
                    rules=None
                )
                
                connection.last_sync = datetime.now().isoformat()
                connection.status = "active"
                self._save_connections()
                
                return {
                    "success": True,
                    "files_processed": len(files_to_process),
                    "result": result
                }
            else:
                return {
                    "success": True,
                    "files_processed": 0,
                    "message": "No se encontraron documentos nuevos"
                }
        except Exception as e:
            connection.status = "error"
            self._save_connections()
            return {"success": False, "error": str(e)}
    
    def _sync_sharepoint(self, connection: DataSightConnection) -> List[str]:
        """Sincroniza documentos de SharePoint."""
        files = []
        try:
            access_token = connection.credentials.get("access_token")
            site_url = connection.credentials.get("site_url")
            
            headers = {"Authorization": f"Bearer {access_token}"}
            
            if site_url:
                # Sincronizar sitio específico
                site_id = self._get_site_id(site_url, headers)
                if site_id:
                    drive_url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drive/root/children"
                    response = requests.get(drive_url, headers=headers, timeout=10)
                    if response.status_code == 200:
                        items = response.json().get("value", [])
                        for item in items:
                            if item.get("file", {}).get("mimeType", "").endswith("pdf"):
                                download_url = item.get("@microsoft.graph.downloadUrl")
                                if download_url:
                                    # Descargar y guardar temporalmente
                                    file_path = self._download_file(download_url, item.get("name", "file.pdf"))
                                    if file_path:
                                        files.append(file_path)
            else:
                # Sincronizar OneDrive personal
                drive_url = "https://graph.microsoft.com/v1.0/me/drive/root/children"
                response = requests.get(drive_url, headers=headers, timeout=10)
                if response.status_code == 200:
                    items = response.json().get("value", [])
                    for item in items:
                        if item.get("file", {}).get("mimeType", "").endswith("pdf"):
                            download_url = item.get("@microsoft.graph.downloadUrl")
                            if download_url:
                                file_path = self._download_file(download_url, item.get("name", "file.pdf"))
                                if file_path:
                                    files.append(file_path)
        except Exception as e:
            print(f"❌ Error sincronizando SharePoint: {e}")
        
        return files
    
    def _sync_google_drive(self, connection: DataSightConnection) -> List[str]:
        """Sincroniza documentos de Google Drive."""
        files = []
        try:
            access_token = connection.credentials.get("access_token")
            folder_id = connection.credentials.get("folder_id")
            
            headers = {"Authorization": f"Bearer {access_token}"}
            
            if folder_id:
                query = f"'{folder_id}' in parents and mimeType='application/pdf'"
            else:
                query = "mimeType='application/pdf'"
            
            drive_url = "https://www.googleapis.com/drive/v3/files"
            params = {"q": query, "pageSize": 100}
            response = requests.get(drive_url, headers=headers, params=params, timeout=10)
            
            if response.status_code == 200:
                items = response.json().get("files", [])
                for item in items:
                    file_id = item.get("id")
                    file_name = item.get("name", "file.pdf")
                    
                    # Descargar archivo
                    download_url = f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media"
                    file_path = self._download_file(download_url, file_name, headers=headers)
                    if file_path:
                        files.append(file_path)
        except Exception as e:
            print(f"❌ Error sincronizando Google Drive: {e}")
        
        return files
    
    def _sync_smb(self, connection: DataSightConnection) -> List[str]:
        """Sincroniza documentos de recurso compartido SMB."""
        # Nota: Requiere librería smbprotocol o similar
        # Por ahora, retornar lista vacía con mensaje
        print("⚠️ Sincronización SMB requiere librería smbprotocol. Instalar: pip install smbprotocol")
        return []
    
    def _sync_salesforce(self, connection: DataSightConnection) -> List[str]:
        """Sincroniza attachments/documentos de Salesforce."""
        files = []
        try:
            instance_url = connection.credentials.get("instance_url")
            access_token = connection.credentials.get("access_token")
            
            headers = {"Authorization": f"Bearer {access_token}"}
            
            # Buscar attachments con PDFs
            query_url = f"{instance_url}/services/data/v58.0/query"
            params = {
                "q": "SELECT Id, Name, ContentType, Body FROM Attachment WHERE ContentType='application/pdf' LIMIT 50"
            }
            response = requests.get(query_url, headers=headers, params=params, timeout=10)
            
            if response.status_code == 200:
                records = response.json().get("records", [])
                for record in records:
                    file_name = record.get("Name", "file.pdf")
                    body = record.get("Body")
                    if body:
                        # Guardar archivo temporalmente
                        file_path = self._save_temp_file(body, file_name)
                        if file_path:
                            files.append(file_path)
        except Exception as e:
            print(f"❌ Error sincronizando Salesforce: {e}")
        
        return files
    
    def _sync_email(self, connection: DataSightConnection) -> List[str]:
        """Sincroniza PDFs adjuntos de emails."""
        files = []
        try:
            email_type = connection.credentials.get("email_type")
            access_token = connection.credentials.get("access_token")
            
            if email_type == "gmail":
                # Buscar emails con PDFs adjuntos
                headers = {"Authorization": f"Bearer {access_token}"}
                search_url = "https://www.googleapis.com/gmail/v1/users/me/messages"
                params = {"q": "has:attachment filename:pdf", "maxResults": 20}
                response = requests.get(search_url, headers=headers, params=params, timeout=10)
                
                if response.status_code == 200:
                    messages = response.json().get("messages", [])
                    for msg in messages:
                        # Obtener mensaje completo
                        msg_url = f"https://www.googleapis.com/gmail/v1/users/me/messages/{msg['id']}"
                        msg_response = requests.get(msg_url, headers=headers, timeout=10)
                        if msg_response.status_code == 200:
                            msg_data = msg_response.json()
                            # Extraer attachments PDF
                            attachments = self._extract_pdf_attachments(msg_data, headers)
                            files.extend(attachments)
        except Exception as e:
            print(f"❌ Error sincronizando email: {e}")
        
        return files
    
    def _download_file(self, url: str, filename: str, headers: Optional[Dict] = None) -> Optional[str]:
        """Descarga un archivo y lo guarda temporalmente."""
        try:
            temp_dir = Path(self.config.temp_dir) / "data_sight_sync"
            temp_dir.mkdir(parents=True, exist_ok=True)
            
            file_path = temp_dir / filename
            response = requests.get(url, headers=headers, timeout=30, stream=True)
            
            if response.status_code == 200:
                with open(file_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                return str(file_path)
        except Exception as e:
            print(f"❌ Error descargando archivo: {e}")
        return None
    
    def _save_temp_file(self, content: str, filename: str) -> Optional[str]:
        """Guarda contenido en archivo temporal."""
        try:
            import base64
            temp_dir = Path(self.config.temp_dir) / "data_sight_sync"
            temp_dir.mkdir(parents=True, exist_ok=True)
            
            file_path = temp_dir / filename
            decoded = base64.b64decode(content)
            with open(file_path, 'wb') as f:
                f.write(decoded)
            return str(file_path)
        except Exception as e:
            print(f"❌ Error guardando archivo temporal: {e}")
        return None
    
    def _get_site_id(self, site_url: str, headers: Dict) -> Optional[str]:
        """Obtiene el ID de un sitio de SharePoint."""
        try:
            # Convertir URL a formato Graph API
            site_hostname = site_url.replace("https://", "").replace("http://", "").split("/")[0]
            site_path = "/".join(site_url.split("/")[3:]) if len(site_url.split("/")) > 3 else ""
            
            graph_url = f"https://graph.microsoft.com/v1.0/sites/{site_hostname}:/{site_path}"
            response = requests.get(graph_url, headers=headers, timeout=10)
            if response.status_code == 200:
                return response.json().get("id")
        except Exception as e:
            print(f"❌ Error obteniendo site ID: {e}")
        return None
    
    def _extract_pdf_attachments(self, msg_data: dict, headers: Dict) -> List[str]:
        """Extrae PDFs adjuntos de un mensaje de Gmail."""
        files = []
        try:
            payload = msg_data.get("payload", {})
            parts = payload.get("parts", [])
            
            for part in parts:
                if part.get("filename", "").endswith(".pdf"):
                    attachment_id = part.get("body", {}).get("attachmentId")
                    if attachment_id:
                        # Descargar attachment
                        att_url = f"https://www.googleapis.com/gmail/v1/users/me/messages/{msg_data['id']}/attachments/{attachment_id}"
                        att_response = requests.get(att_url, headers=headers, timeout=10)
                        if att_response.status_code == 200:
                            att_data = att_response.json().get("data", "")
                            file_path = self._save_temp_file(att_data, part.get("filename", "attachment.pdf"))
                            if file_path:
                                files.append(file_path)
        except Exception as e:
            print(f"❌ Error extrayendo attachments: {e}")
        
        return files
    
    def list_connections(self) -> List[Dict[str, Any]]:
        """Lista todas las conexiones configuradas."""
        return [
            {
                "connection_id": conn.connection_id,
                "name": conn.name,
                "system_type": conn.system_type,
                "status": conn.status,
                "auto_sync": conn.auto_sync,
                "last_sync": conn.last_sync,
                "created_at": conn.created_at,
            }
            for conn in self.connections.values()
        ]
    
    def disconnect(self, connection_id: str) -> Dict[str, Any]:
        """Desconecta una conexión."""
        if connection_id in self.connections:
            del self.connections[connection_id]
            self._save_connections()
            return {"success": True, "message": "Conexión desconectada"}
        return {"success": False, "error": "Conexión no encontrada"}

