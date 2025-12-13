"""
Salesforce Connector - Conecta a Salesforce.

Usa Salesforce REST API con:
- Webhooks vía Apex Triggers + Outbound Messages
- Polling como fallback
- OAuth2 (Username-Password Flow o Web Server Flow)
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple

try:
    from simple_salesforce import Salesforce
    SIMPLE_SALESFORCE_AVAILABLE = True
except ImportError:
    SIMPLE_SALESFORCE_AVAILABLE = False

from .base_connector import BaseEnterpriseConnector, ConnectorConfig, ConnectorStatus


class SalesforceConnector(BaseEnterpriseConnector):
    """Conector para Salesforce usando simple-salesforce."""
    
    def __init__(self, config: ConnectorConfig, process_pdf_callback=None):
        super().__init__(config, process_pdf_callback)
        self.sf = None
        self.instance_url = config.extra_config.get("instance_url")
    
    async def authenticate(self) -> bool:
        """Autentica usando OAuth2 con Salesforce o Access Token directo."""
        try:
            # Si tenemos Access Token directo, usarlo directamente
            if self.config.access_token and not self.config.extra_config.get("username"):
                instance_url = self.config.extra_config.get("instance_url")
                if not instance_url:
                    print("❌ [Salesforce] instance_url requerido cuando usas Access Token")
                    return False
                
                # Usar simple-salesforce con token directo
                if not SIMPLE_SALESFORCE_AVAILABLE:
                    print("⚠️ [Salesforce] simple-salesforce no está instalado. Instala con: pip install simple-salesforce")
                    return False
                
                # Crear cliente con token directo
                self.sf = Salesforce(
                    instance_url=instance_url,
                    session_id=self.config.access_token
                )
                
                self.instance_url = instance_url
                print(f"✅ [Salesforce] Autenticado con Access Token directo: {self.instance_url}")
                return True
            
            if not SIMPLE_SALESFORCE_AVAILABLE:
                print("⚠️ [Salesforce] simple-salesforce no está instalado. Instala con: pip install simple-salesforce")
                return False
            
            username = self.config.extra_config.get("username")
            password = self.config.extra_config.get("password")
            security_token = self.config.extra_config.get("security_token", "")
            domain = self.config.extra_config.get("domain", "login")  # login o test
            
            if not username or not password:
                print("❌ [Salesforce] username y password requeridos")
                return False
            
            # Autenticar usando Username-Password Flow
            self.sf = Salesforce(
                username=username,
                password=password,
                security_token=security_token,
                domain=domain
            )
            
            # Guardar tokens
            self.config.access_token = self.sf.session_id
            self.instance_url = self.sf.base_url.split('/services')[0]
            self.config.extra_config["instance_url"] = self.instance_url
            
            print(f"✅ [Salesforce] Autenticado: {self.instance_url}")
            return True
            
        except Exception as e:
            print(f"❌ [Salesforce] Error en autenticación: {e}")
            return False
    
    async def refresh_access_token(self) -> bool:
        """Salesforce tokens expiran, necesitamos re-autenticar."""
        return await self.authenticate()
    
    async def list_new_files(self, since: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """Lista archivos nuevos (ContentVersion objects) en Salesforce."""
        try:
            await self._ensure_authenticated()
            
            if not self.sf:
                return []
            
            files = []
            
            # SOQL query para ContentVersion (archivos)
            query = """
                SELECT Id, Title, ContentDocumentId, FileExtension, ContentSize, 
                       VersionData, CreatedDate, LastModifiedDate, ContentUrl
                FROM ContentVersion
                WHERE FileExtension = 'pdf'
                AND IsLatest = true
            """
            
            if since:
                since_str = since.strftime("%Y-%m-%dT%H:%M:%S.000Z")
                query += f" AND LastModifiedDate > {since_str}"
            
            query += " ORDER BY LastModifiedDate DESC LIMIT 100"
            
            results = self.sf.query(query)
            
            for record in results.get('records', []):
                file_info = {
                    "file_id": record['Id'],
                    "file_name": f"{record.get('Title', 'document')}.pdf",
                    "file_url": f"{self.instance_url}/sfc/servlet.shepherd/version/download/{record['Id']}",
                    "file_size": record.get('ContentSize', 0),
                    "modified_at": datetime.fromisoformat(record['LastModifiedDate'].replace('Z', '+00:00')).replace(tzinfo=None),
                    "metadata": {
                        "content_document_id": record.get('ContentDocumentId'),
                        "file_extension": record.get('FileExtension'),
                        "salesforce_id": record['Id']
                    }
                }
                files.append(file_info)
            
            return files
            
        except Exception as e:
            print(f"❌ [Salesforce] Error listando archivos: {e}")
            return []
    
    async def download_file(self, file_url: str, file_id: str) -> Tuple[bytes, Dict[str, Any]]:
        """Descarga un archivo desde Salesforce."""
        try:
            await self._ensure_authenticated()
            
            if not self.sf:
                raise Exception("Salesforce client no inicializado")
            
            # Descargar usando la URL o el ID
            if file_url:
                headers = {"Authorization": f"Bearer {self.config.access_token}"}
                response = self.session.get(file_url, headers=headers)
                response.raise_for_status()
                content = response.content
            else:
                # Usar simple-salesforce para descargar
                result = self.sf.ContentVersion.get(file_id)
                # Nota: VersionData requiere una llamada adicional
                content = b""  # Placeholder - necesitarías implementar la descarga real
            
            metadata = {
                "content_type": "application/pdf",
                "content_length": len(content),
                "file_id": file_id
            }
            
            return content, metadata
            
        except Exception as e:
            print(f"❌ [Salesforce] Error descargando archivo {file_id}: {e}")
            raise
    
    async def setup_webhook(self, webhook_url: str) -> bool:
        """
        Configura webhook en Salesforce usando Apex Trigger + Outbound Message.
        
        Nota: Esto requiere configuración en Salesforce (Apex Trigger + Workflow Rule).
        Por ahora, retornamos False y usamos polling.
        """
        print("⚠️ [Salesforce] Webhooks requieren configuración en Salesforce (Apex Trigger + Outbound Message)")
        print("💡 [Salesforce] Tip: Crea un Apex Trigger en ContentVersion que llame a tu webhook")
        return False
    
    async def delete_webhook(self) -> bool:
        """No hay webhook que eliminar (se configura en Salesforce)."""
        return True
    
    async def connect(self, use_webhooks: Optional[bool] = None) -> bool:
        """Conecta a Salesforce. Usa polling por defecto."""
        return await super().connect(use_webhooks=False)

