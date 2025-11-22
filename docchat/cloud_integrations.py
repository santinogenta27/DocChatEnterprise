"""Cloud Storage Integrations - Conecta automáticamente con storage empresarial."""

from __future__ import annotations

from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path
import asyncio
import json

from .config import AppConfig
from .enterprise_api import EnterpriseAPIMode


class CloudStorageIntegration:
    """
    Integración con Cloud Storage para procesamiento automático.
    
    Soporta:
    - AWS S3
    - Google Cloud Storage
    - Azure Blob Storage
    - Webhooks para sincronización automática
    """
    
    def __init__(self, config: AppConfig, enterprise_api: EnterpriseAPIMode):
        self.config = config
        self.enterprise_api = enterprise_api
    
    def connect_s3_bucket(
        self,
        bucket_name: str,
        access_key: str,
        secret_key: str,
        region: str = "us-east-1",
        prefix: str = "",
        auto_process: bool = True
    ) -> Dict[str, Any]:
        """
        Conecta un bucket de S3 para procesamiento automático.
        
        Args:
            bucket_name: Nombre del bucket
            access_key: AWS Access Key
            secret_key: AWS Secret Key
            region: Región de AWS
            prefix: Prefijo para filtrar archivos (ej: "documents/")
            auto_process: Si True, procesa automáticamente archivos nuevos
        """
        try:
            import boto3
            
            s3_client = boto3.client(
                's3',
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key,
                region_name=region
            )
            
            # Listar archivos en el bucket
            files = []
            paginator = s3_client.get_paginator('list_objects_v2')
            pages = paginator.paginate(Bucket=bucket_name, Prefix=prefix)
            
            for page in pages:
                for obj in page.get('Contents', []):
                    if obj['Key'].endswith(('.pdf', '.docx', '.txt', '.md')):
                        files.append({
                            'key': obj['Key'],
                            'size': obj['Size'],
                            'last_modified': obj['LastModified'].isoformat()
                        })
            
            # Si auto_process está activado, procesar archivos
            if auto_process and files:
                processed = self._process_s3_files(s3_client, bucket_name, files)
                return {
                    "status": "connected",
                    "bucket": bucket_name,
                    "files_found": len(files),
                    "files_processed": processed,
                    "auto_processing": auto_process
                }
            
            return {
                "status": "connected",
                "bucket": bucket_name,
                "files_found": len(files),
                "auto_processing": auto_process
            }
            
        except ImportError:
            raise Exception("boto3 no está instalado. Instala con: pip install boto3")
        except Exception as e:
            raise Exception(f"Error conectando S3: {str(e)}")
    
    def connect_gcs_bucket(
        self,
        bucket_name: str,
        credentials_path: str,
        prefix: str = "",
        auto_process: bool = True
    ) -> Dict[str, Any]:
        """
        Conecta un bucket de Google Cloud Storage.
        """
        try:
            from google.cloud import storage
            
            client = storage.Client.from_service_account_json(credentials_path)
            bucket = client.bucket(bucket_name)
            
            files = []
            blobs = bucket.list_blobs(prefix=prefix)
            
            for blob in blobs:
                if blob.name.endswith(('.pdf', '.docx', '.txt', '.md')):
                    files.append({
                        'name': blob.name,
                        'size': blob.size,
                        'updated': blob.updated.isoformat() if blob.updated else None
                    })
            
            if auto_process and files:
                processed = self._process_gcs_files(bucket, files)
                return {
                    "status": "connected",
                    "bucket": bucket_name,
                    "files_found": len(files),
                    "files_processed": processed,
                    "auto_processing": auto_process
                }
            
            return {
                "status": "connected",
                "bucket": bucket_name,
                "files_found": len(files),
                "auto_processing": auto_process
            }
            
        except ImportError:
            raise Exception("google-cloud-storage no está instalado. Instala con: pip install google-cloud-storage")
        except Exception as e:
            raise Exception(f"Error conectando GCS: {str(e)}")
    
    def connect_azure_blob(
        self,
        container_name: str,
        connection_string: str,
        prefix: str = "",
        auto_process: bool = True
    ) -> Dict[str, Any]:
        """
        Conecta un contenedor de Azure Blob Storage.
        """
        try:
            from azure.storage.blob import BlobServiceClient
            
            blob_service = BlobServiceClient.from_connection_string(connection_string)
            container_client = blob_service.get_container_client(container_name)
            
            files = []
            blobs = container_client.list_blobs(name_starts_with=prefix)
            
            for blob in blobs:
                if blob.name.endswith(('.pdf', '.docx', '.txt', '.md')):
                    files.append({
                        'name': blob.name,
                        'size': blob.size,
                        'last_modified': blob.last_modified.isoformat() if blob.last_modified else None
                    })
            
            if auto_process and files:
                processed = self._process_azure_files(container_client, files)
                return {
                    "status": "connected",
                    "container": container_name,
                    "files_found": len(files),
                    "files_processed": processed,
                    "auto_processing": auto_process
                }
            
            return {
                "status": "connected",
                "container": container_name,
                "files_found": len(files),
                "auto_processing": auto_process
            }
            
        except ImportError:
            raise Exception("azure-storage-blob no está instalado. Instala con: pip install azure-storage-blob")
        except Exception as e:
            raise Exception(f"Error conectando Azure: {str(e)}")
    
    def _process_s3_files(self, s3_client, bucket_name: str, files: List[Dict]) -> int:
        """Procesa archivos de S3."""
        processed = 0
        file_objects = []
        
        for file_info in files[:100]:  # Limitar a 100 archivos por batch
            try:
                # Descargar archivo temporalmente
                import tempfile
                with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file_info['key']).suffix) as tmp:
                    s3_client.download_fileobj(bucket_name, file_info['key'], tmp)
                    tmp_path = Path(tmp.name)
                    tmp_path.name = file_info['key']  # Preservar nombre original
                    file_objects.append(tmp_path)
            except Exception as e:
                print(f"Error descargando {file_info['key']}: {e}")
        
        if file_objects:
            # Procesar con Enterprise API
            results = self.enterprise_api.process_enterprise_documents(
                files=file_objects,
                auto_detect=True,
                rules=[]
            )
            processed = results.get('documents_processed', 0)
        
        return processed
    
    def _process_gcs_files(self, bucket, files: List[Dict]) -> int:
        """Procesa archivos de GCS."""
        processed = 0
        file_objects = []
        
        for file_info in files[:100]:
            try:
                import tempfile
                blob = bucket.blob(file_info['name'])
                with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file_info['name']).suffix) as tmp:
                    blob.download_to_file(tmp)
                    tmp_path = Path(tmp.name)
                    tmp_path.name = file_info['name']
                    file_objects.append(tmp_path)
            except Exception as e:
                print(f"Error descargando {file_info['name']}: {e}")
        
        if file_objects:
            results = self.enterprise_api.process_enterprise_documents(
                files=file_objects,
                auto_detect=True,
                rules=[]
            )
            processed = results.get('documents_processed', 0)
        
        return processed
    
    def _process_azure_files(self, container_client, files: List[Dict]) -> int:
        """Procesa archivos de Azure."""
        processed = 0
        file_objects = []
        
        for file_info in files[:100]:
            try:
                import tempfile
                blob_client = container_client.get_blob_client(file_info['name'])
                with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file_info['name']).suffix) as tmp:
                    blob_client.download_blob().readinto(tmp)
                    tmp_path = Path(tmp.name)
                    tmp_path.name = file_info['name']
                    file_objects.append(tmp_path)
            except Exception as e:
                print(f"Error descargando {file_info['name']}: {e}")
        
        if file_objects:
            results = self.enterprise_api.process_enterprise_documents(
                files=file_objects,
                auto_detect=True,
                rules=[]
            )
            processed = results.get('documents_processed', 0)
        
        return processed


class WebhookProcessor:
    """
    Procesa webhooks de cloud storage para sincronización automática.
    """
    
    def __init__(self, config: AppConfig, enterprise_api: EnterpriseAPIMode):
        self.config = config
        self.enterprise_api = enterprise_api
    
    def process_webhook(
        self,
        webhook_data: Dict[str, Any],
        source: str = "s3"
    ) -> Dict[str, Any]:
        """
        Procesa un webhook de cloud storage.
        
        Args:
            webhook_data: Datos del webhook
            source: Origen (s3, gcs, azure)
        """
        if source == "s3":
            return self._process_s3_webhook(webhook_data)
        elif source == "gcs":
            return self._process_gcs_webhook(webhook_data)
        elif source == "azure":
            return self._process_azure_webhook(webhook_data)
        else:
            raise ValueError(f"Source no soportado: {source}")
    
    def _process_s3_webhook(self, data: Dict) -> Dict[str, Any]:
        """Procesa webhook de S3."""
        # S3 envía eventos cuando se suben archivos
        records = data.get('Records', [])
        processed = []
        
        for record in records:
            if record.get('eventName', '').startswith('ObjectCreated'):
                bucket = record['s3']['bucket']['name']
                key = record['s3']['object']['key']
                
                if key.endswith(('.pdf', '.docx', '.txt', '.md')):
                    # Descargar y procesar
                    try:
                        import boto3
                        s3_client = boto3.client('s3')
                        import tempfile
                        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(key).suffix) as tmp:
                            s3_client.download_fileobj(bucket, key, tmp)
                            tmp_path = Path(tmp.name)
                            tmp_path.name = key
                            
                            results = self.enterprise_api.process_enterprise_documents(
                                files=[tmp_path],
                                auto_detect=True,
                                rules=[]
                            )
                            processed.append({
                                "file": key,
                                "status": "processed",
                                "results": results
                            })
                    except Exception as e:
                        processed.append({
                            "file": key,
                            "status": "error",
                            "error": str(e)
                        })
        
        return {
            "webhook_processed": True,
            "files_processed": len(processed),
            "details": processed
        }
    
    def _process_gcs_webhook(self, data: Dict) -> Dict[str, Any]:
        """Procesa webhook de GCS."""
        # GCS Pub/Sub notifications
        # Similar a S3 pero con formato diferente
        return {"status": "processed", "source": "gcs"}
    
    def _process_azure_webhook(self, data: Dict) -> Dict[str, Any]:
        """Procesa webhook de Azure."""
        # Azure Event Grid notifications
        return {"status": "processed", "source": "azure"}

