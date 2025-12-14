"""
AWS S3 Connector - Conecta a buckets de S3.

Usa boto3 (AWS SDK) con:
- Polling (S3 no tiene webhooks nativos)
- IAM credentials o Access Keys
- Event notifications opcionales vía SNS/SQS
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple

try:
    import boto3
    from botocore.exceptions import ClientError, NoCredentialsError
    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False

from .base_connector import BaseEnterpriseConnector, ConnectorConfig, ConnectorStatus


class AWSS3Connector(BaseEnterpriseConnector):
    """Conector para AWS S3 usando boto3."""
    
    def __init__(self, config: ConnectorConfig, process_pdf_callback=None):
        super().__init__(config, process_pdf_callback)
        self.s3_client = None
        self.bucket_name = config.extra_config.get("bucket_name")
        self.prefix = config.extra_config.get("prefix", "")  # Prefijo de carpeta en S3
        
        if not BOTO3_AVAILABLE:
            print("⚠️ [AWS S3] boto3 no está instalado. Instala con: pip install boto3")
    
    async def authenticate(self) -> bool:
        """Autentica usando AWS credentials (IAM, Access Keys, o variables de entorno)."""
        try:
            if not BOTO3_AVAILABLE:
                return False
            
            # Configurar credenciales desde config o variables de entorno
            aws_access_key_id = self.config.extra_config.get("aws_access_key_id")
            aws_secret_access_key = self.config.extra_config.get("aws_secret_access_key")
            aws_region = self.config.extra_config.get("aws_region", "us-east-1")
            
            if aws_access_key_id and aws_secret_access_key:
                self.s3_client = boto3.client(
                    's3',
                    aws_access_key_id=aws_access_key_id,
                    aws_secret_access_key=aws_secret_access_key,
                    region_name=aws_region
                )
            else:
                # Usar credenciales por defecto (IAM role, ~/.aws/credentials, o variables de entorno)
                self.s3_client = boto3.client('s3', region_name=aws_region)
            
            # Verificar conexión listando el bucket
            if self.bucket_name:
                self.s3_client.head_bucket(Bucket=self.bucket_name)
                print(f"✅ [AWS S3] Autenticado y conectado a bucket: {self.bucket_name}")
                return True
            else:
                print("⚠️ [AWS S3] bucket_name no configurado")
                return False
                
        except NoCredentialsError:
            print("❌ [AWS S3] No se encontraron credenciales de AWS")
            return False
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            if error_code == '403':
                print("❌ [AWS S3] Acceso denegado al bucket. Verifica permisos IAM.")
            elif error_code == '404':
                print(f"❌ [AWS S3] Bucket no encontrado: {self.bucket_name}")
            else:
                print(f"❌ [AWS S3] Error de autenticación: {e}")
            return False
        except Exception as e:
            print(f"❌ [AWS S3] Error en autenticación: {e}")
            return False
    
    async def refresh_access_token(self) -> bool:
        """AWS S3 no usa tokens OAuth2, usa IAM credentials que no expiran (o se renuevan automáticamente)."""
        # Para S3, simplemente verificamos que el cliente esté activo
        try:
            if self.s3_client and self.bucket_name:
                self.s3_client.head_bucket(Bucket=self.bucket_name)
                return True
            return await self.authenticate()
        except Exception:
            return await self.authenticate()
    
    async def list_new_files(self, since: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """Lista archivos nuevos en el bucket de S3."""
        try:
            if not self.s3_client or not self.bucket_name:
                await self._ensure_authenticated()
            
            files = []
            paginator = self.s3_client.get_paginator('list_objects_v2')
            
            list_kwargs = {
                'Bucket': self.bucket_name,
                'Prefix': self.prefix
            }
            
            # Si hay filtro por fecha, necesitamos listar todo y filtrar después
            # (S3 no soporta filtrado por fecha en list_objects_v2 directamente)
            
            for page in paginator.paginate(**list_kwargs):
                for obj in page.get('Contents', []):
                    # Filtrar por fecha si se especificó
                    if since:
                        last_modified = obj['LastModified'].replace(tzinfo=None)
                        if last_modified < since.replace(tzinfo=None):
                            continue
                    
                    # Solo archivos (no carpetas)
                    if obj['Key'].endswith('/'):
                        continue
                    
                    # Verificar extensión
                    if not any(obj['Key'].lower().endswith(ext) for ext in self.config.file_extensions):
                        continue
                    
                    # Generar URL pre-firmada (válida por 1 hora)
                    file_url = self.s3_client.generate_presigned_url(
                        'get_object',
                        Params={'Bucket': self.bucket_name, 'Key': obj['Key']},
                        ExpiresIn=3600
                    )
                    
                    file_info = {
                        "file_id": obj['Key'],  # Usar la key como ID único
                        "file_name": obj['Key'].split('/')[-1],  # Nombre del archivo
                        "file_url": file_url,
                        "file_size": obj['Size'],
                        "modified_at": obj['LastModified'].replace(tzinfo=None),
                        "metadata": {
                            "s3_key": obj['Key'],
                            "s3_bucket": self.bucket_name,
                            "etag": obj['ETag'].strip('"'),
                            "storage_class": obj.get('StorageClass', 'STANDARD')
                        }
                    }
                    
                    files.append(file_info)
            
            return files
            
        except ClientError as e:
            print(f"❌ [AWS S3] Error listando archivos: {e}")
            return []
        except Exception as e:
            print(f"❌ [AWS S3] Error inesperado listando archivos: {e}")
            return []
    
    async def download_file(self, file_url: str, file_id: str) -> Tuple[bytes, Dict[str, Any]]:
        """Descarga un archivo desde S3."""
        try:
            if not self.s3_client or not self.bucket_name:
                await self._ensure_authenticated()
            
            # file_id es la S3 key
            s3_key = file_id
            
            # Descargar objeto
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=s3_key)
            content = response['Body'].read()
            
            metadata = {
                "content_type": response.get('ContentType', 'application/octet-stream'),
                "content_length": len(content),
                "s3_key": s3_key,
                "s3_bucket": self.bucket_name,
                "etag": response.get('ETag', '').strip('"'),
                "last_modified": response.get('LastModified')
            }
            
            return content, metadata
            
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            if error_code == 'NoSuchKey':
                print(f"❌ [AWS S3] Archivo no encontrado: {file_id}")
            else:
                print(f"❌ [AWS S3] Error descargando archivo {file_id}: {e}")
            raise
        except Exception as e:
            print(f"❌ [AWS S3] Error inesperado descargando archivo: {e}")
            raise
    
    async def setup_webhook(self, webhook_url: str) -> bool:
        """
        S3 no tiene webhooks nativos, pero se puede configurar Event Notifications
        que envían eventos a SNS/SQS, y luego un listener puede llamar al webhook.
        
        Por ahora, retornamos False y usamos polling.
        """
        print("⚠️ [AWS S3] S3 no soporta webhooks directos. Usando polling.")
        print("💡 [AWS S3] Tip: Configura S3 Event Notifications → SNS → Lambda → Webhook para tiempo real")
        return False
    
    async def delete_webhook(self) -> bool:
        """No hay webhook que eliminar."""
        return True
    
    async def connect(self, use_webhooks: Optional[bool] = None) -> bool:
        """
        Conecta a S3. Siempre usa polling (S3 no tiene webhooks nativos).
        """
        # Forzar polling para S3
        return await super().connect(use_webhooks=False)

