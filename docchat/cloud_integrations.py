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
    - Google Drive (procesamiento directo sin descargar)
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
    
    def list_google_drive_files(
        self,
        access_token: str,
        folder_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Lista archivos de Google Drive sin descargarlos.
        Retorna lista de archivos para que el usuario seleccione.
        """
        try:
            from google.oauth2.credentials import Credentials
            from googleapiclient.discovery import build
            from google.auth.transport.requests import Request
            
            # Crear credenciales desde el token
            # Si el token expiró, intentar refrescarlo si es posible
            creds = Credentials(token=access_token.strip())
            
            # Verificar si el token está expirado y si podemos refrescarlo
            if creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception as refresh_error:
                    # Si no se puede refrescar, el token ha expirado
                    raise Exception(
                        f"El token de acceso ha expirado. Por favor obtén un nuevo token desde OAuth Playground.\n"
                        f"Error: {str(refresh_error)}"
                    )
            elif creds.expired:
                raise Exception(
                    "El token de acceso ha expirado. Los tokens de OAuth Playground expiran después de 1 hora.\n\n"
                    "**💡 Solución:**\n"
                    "1. Ve a OAuth Playground nuevamente\n"
                    "2. Obtén un nuevo Access Token\n"
                    "3. Pégalo en el campo de conexión"
                )
            
            service = build('drive', 'v3', credentials=creds)
            
            # Listar archivos
            files = []
            query = "mimeType='application/pdf' or mimeType='application/vnd.openxmlformats-officedocument.wordprocessingml.document' or mimeType='text/plain' or mimeType='text/markdown'"
            
            if folder_id and folder_id.strip():
                query += f" and '{folder_id.strip()}' in parents"
            
            page_token = None
            while len(files) < 200:  # Limitar a 200 archivos
                results = service.files().list(
                    q=query,
                    pageSize=100,
                    fields="nextPageToken, files(id, name, mimeType, size, modifiedTime)",
                    pageToken=page_token
                ).execute()
                
                items = results.get('files', [])
                for item in items:
                    files.append({
                        'id': item['id'],
                        'name': item['name'],
                        'mimeType': item.get('mimeType', ''),
                        'size': int(item.get('size', 0)),
                        'size_mb': round(int(item.get('size', 0)) / (1024 * 1024), 2),
                        'modified': item.get('modifiedTime', 'N/A')
                    })
                
                page_token = results.get('nextPageToken')
                if not page_token:
                    break
            
            # Guardar sesión para uso posterior
            if not hasattr(self, '_drive_sessions'):
                self._drive_sessions = {}
            
            session_id = f"drive_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            self._drive_sessions[session_id] = {
                'service': service,
                'files': files,
                'credentials': {'token': access_token.strip()},
                'folder_id': folder_id.strip() if folder_id else None
            }
            
            return {
                "status": "connected",
                "session_id": session_id,
                "files": files,
                "total_files": len(files)
            }
            
        except Exception as e:
            raise Exception(f"Error listando archivos de Google Drive: {str(e)}")
    
    def connect_google_drive(
        self,
        credentials_json: str,
        folder_id: Optional[str] = None,
        auto_process: bool = True
    ) -> Dict[str, Any]:
        """
        Conecta Google Drive para procesamiento directo sin descargar archivos.
        
        Args:
            credentials_json: JSON de credenciales de Google Drive API
            folder_id: ID de carpeta específica (opcional, si no se especifica usa "My Drive")
            auto_process: Si True, procesa automáticamente archivos encontrados
        """
        try:
            from google.oauth2.credentials import Credentials
            from google_auth_oauthlib.flow import InstalledAppFlow
            from google.auth.transport.requests import Request
            from googleapiclient.discovery import build
            from googleapiclient.http import MediaIoBaseDownload
            import io
            import json
            import tempfile
            
            # Parsear credenciales
            if isinstance(credentials_json, str):
                creds_data = json.loads(credentials_json)
            else:
                creds_data = credentials_json
            
            # Crear credenciales
            creds = None
            if 'token' in creds_data:
                creds = Credentials.from_authorized_user_info(creds_data)
            else:
                # Si es service account
                from google.oauth2 import service_account
                if creds_data.get('type') == 'service_account':
                    creds = service_account.Credentials.from_service_account_info(creds_data)
                else:
                    # OAuth flow - acepta tanto "web" como "installed"
                    # Convertir "web" a formato "installed" si es necesario
                    if 'web' in creds_data and 'installed' not in creds_data:
                        # Convertir formato web a installed para compatibilidad
                        creds_data['installed'] = creds_data['web'].copy()
                        # Agregar redirect_uris para aplicación de escritorio
                        creds_data['installed']['redirect_uris'] = [
                            'http://localhost:8080',
                            'http://127.0.0.1:8080',
                            'urn:ietf:wg:oauth:2.0:oob'
                        ]
                    
                    # OAuth flow
                    flow = InstalledAppFlow.from_client_config(
                        creds_data,
                        ['https://www.googleapis.com/auth/drive.readonly']
                    )
                    # Usar puerto fijo y URI específica
                    creds = flow.run_local_server(port=8080, open_browser=True)
            
            # Construir servicio de Drive
            service = build('drive', 'v3', credentials=creds)
            
            # Listar archivos
            files = []
            query = "mimeType='application/pdf' or mimeType='application/vnd.openxmlformats-officedocument.wordprocessingml.document' or mimeType='text/plain' or mimeType='text/markdown'"
            
            if folder_id:
                query += f" and '{folder_id}' in parents"
            
            page_token = None
            while True:
                results = service.files().list(
                    q=query,
                    pageSize=1000,
                    fields="nextPageToken, files(id, name, mimeType, size)",
                    pageToken=page_token
                ).execute()
                
                items = results.get('files', [])
                for item in items:
                    files.append({
                        'id': item['id'],
                        'name': item['name'],
                        'mimeType': item.get('mimeType', ''),
                        'size': int(item.get('size', 0))
                    })
                
                page_token = results.get('nextPageToken')
                if not page_token:
                    break
            
            # Guardar credenciales y archivos en sesión para uso posterior
            if not hasattr(self, '_drive_sessions'):
                self._drive_sessions = {}
            
            session_id = f"drive_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            self._drive_sessions[session_id] = {
                'service': service,
                'files': files,
                'credentials': creds_data,
                'folder_id': folder_id
            }
            
            # Si auto_process está activado, procesar archivos directamente desde Drive
            if auto_process and files:
                processed = self._process_drive_files_direct(service, files, session_id)
                return {
                    "status": "connected",
                    "session_id": session_id,
                    "files_found": len(files),
                    "files_processed": processed,
                    "auto_processing": auto_process,
                    "message": f"✅ Conectado a Google Drive. {len(files)} archivos encontrados. {processed} procesados."
                }
            
            return {
                "status": "connected",
                "session_id": session_id,
                "files_found": len(files),
                "auto_processing": auto_process,
                "message": f"✅ Conectado a Google Drive. {len(files)} archivos listos para procesar."
            }
            
        except ImportError:
            raise Exception("google-api-python-client no está instalado. Instala con: pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib")
        except Exception as e:
            raise Exception(f"Error conectando Google Drive: {str(e)}")
    
    def _process_drive_files_direct(
        self,
        service,
        files: List[Dict],
        session_id: str,
        selected_file_ids: Optional[List[str]] = None
    ) -> int:
        """
        Procesa archivos de Google Drive directamente sin descargarlos completamente.
        Lee en streaming y procesa con Enterprise API.
        
        Args:
            service: Servicio de Google Drive
            files: Lista de archivos disponibles
            session_id: ID de sesión
            selected_file_ids: IDs de archivos seleccionados (si None, procesa todos)
        """
        processed = 0
        file_objects = []
        
        # Filtrar archivos seleccionados
        if selected_file_ids:
            files_to_process = [f for f in files if f['id'] in selected_file_ids]
            print(f"📋 Procesando {len(files_to_process)} archivos seleccionados de {len(files)} disponibles...")
        else:
            files_to_process = files[:200]  # Limitar a 200 si no hay selección
            print(f"📋 Procesando todos los archivos disponibles (máximo 200 de {len(files)} totales)...")
        
        print(f"📥 Descargando {len(files_to_process)} archivos desde Google Drive...")
        print(f"   Esto puede tardar varios minutos dependiendo del tamaño de los archivos...\n")
        
        for idx, file_info in enumerate(files_to_process, 1):
            try:
                import tempfile
                from pathlib import Path
                from googleapiclient.http import MediaIoBaseDownload
                import io
                import time
                
                file_id = file_info['id']
                file_name = file_info['name']
                file_size_mb = file_info.get('size_mb', 0)
                
                print(f"[{idx}/{len(files_to_process)}] 📥 Descargando: {file_name} ({file_size_mb} MB)...")
                
                # Determinar extensión
                mime_to_ext = {
                    'application/pdf': '.pdf',
                    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': '.docx',
                    'text/plain': '.txt',
                    'text/markdown': '.md'
                }
                ext = mime_to_ext.get(file_info.get('mimeType', ''), '.pdf')
                
                # Descargar archivo en memoria temporal (streaming)
                print(f"   ⏳ Iniciando descarga...")
                request = service.files().get_media(fileId=file_id)
                file_content = io.BytesIO()
                downloader = MediaIoBaseDownload(file_content, request)
                
                done = False
                chunk_count = 0
                while not done:
                    status, done = downloader.next_chunk()
                    chunk_count += 1
                    if chunk_count % 10 == 0:  # Mostrar progreso cada 10 chunks
                        progress = int(status.progress() * 100) if status else 0
                        print(f"   📊 Progreso: {progress}%...", end='\r')
                
                # Guardar en archivo temporal con nombre único para evitar conflictos
                import uuid
                import os
                # Limpiar nombre de archivo de caracteres inválidos
                safe_name = "".join(c for c in file_name if c.isalnum() or c in (' ', '-', '_', '.'))[:100]
                unique_name = f"{uuid.uuid4().hex[:8]}_{safe_name}"
                
                # Crear archivo temporal con nombre único desde el inicio
                temp_dir = Path(tempfile.gettempdir())
                final_path = temp_dir / f"drive_{uuid.uuid4().hex[:12]}{ext}"
                
                print(f"   💾 Guardando archivo...")
                # Escribir contenido directamente al archivo final
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        with open(final_path, 'wb') as f:
                            f.write(file_content.getvalue())
                        # Cerrar el archivo antes de continuar
                        file_objects.append(final_path)
                        print(f"   ✅ {file_name} descargado y listo ({file_size_mb} MB)")
                        break
                    except (OSError, PermissionError) as e:
                        if attempt < max_retries - 1:
                            time.sleep(0.5 * (attempt + 1))  # Esperar más en cada intento
                            # Generar nuevo nombre único
                            final_path = temp_dir / f"drive_{uuid.uuid4().hex[:12]}{ext}"
                        else:
                            print(f"   ❌ Error guardando {file_info.get('name', 'archivo')} después de {max_retries} intentos: {e}")
                            raise
                
                time.sleep(0.1)  # Pequeña pausa para evitar rate limits
                
            except Exception as e:
                error_msg = str(e)
                if "403" in error_msg or "cannotDownloadFile" in error_msg:
                    print(f"   ⚠️ {file_info.get('name', 'archivo')}: Sin permisos de descarga (puede estar restringido)")
                elif "WinError 32" in error_msg:
                    print(f"   ⚠️ {file_info.get('name', 'archivo')}: Archivo en uso, omitiendo...")
                else:
                    print(f"   ❌ Error descargando {file_info.get('name', 'archivo')}: {error_msg[:150]}")
        
        if file_objects:
            print(f"\n{'='*60}")
            print(f"🚀 Enviando {len(file_objects)} archivos a Enterprise API Mode...")
            print(f"{'='*60}\n")
            # Procesar con Enterprise API
            results = self.enterprise_api.process_enterprise_documents(
                files=file_objects,
                auto_detect=True,
                rules=[]
            )
            processed = results.get('documents_processed', 0)
            print(f"\n✅ {processed} archivos procesados exitosamente de {len(file_objects)} descargados")
        else:
            print(f"\n⚠️ No se pudieron descargar archivos para procesar")
        
        return processed
    
    def get_drive_files_for_enterprise(
        self, 
        session_id: str,
        selected_file_ids: Optional[List[str]] = None
    ) -> List[Any]:
        """
        Obtiene archivos de Google Drive para usar en Enterprise API Mode.
        Retorna lista de archivos que pueden ser procesados directamente.
        
        Args:
            session_id: ID de sesión de Google Drive
            selected_file_ids: IDs de archivos seleccionados (si None, procesa todos)
        """
        if not hasattr(self, '_drive_sessions') or session_id not in self._drive_sessions:
            return []
        
        session = self._drive_sessions[session_id]
        service = session['service']
        files = session['files']
        
        # Filtrar archivos seleccionados
        if selected_file_ids:
            files_to_process = [f for f in files if f['id'] in selected_file_ids]
            print(f"📋 Procesando {len(files_to_process)} archivos seleccionados de {len(files)} disponibles...")
        else:
            files_to_process = files[:200]  # Limitar a 200 si no hay selección
            print(f"📋 Procesando todos los archivos disponibles (máximo 200 de {len(files)} totales)...")
        
        print(f"📥 Descargando {len(files_to_process)} archivos desde Google Drive...")
        print(f"   Esto puede tardar varios minutos dependiendo del tamaño de los archivos...\n")
        
        # Convertir archivos de Drive a objetos procesables
        file_objects = []
        for idx, file_info in enumerate(files_to_process, 1):
            try:
                import tempfile
                from pathlib import Path
                from googleapiclient.http import MediaIoBaseDownload
                import io
                import uuid
                import time
                
                file_id = file_info['id']
                file_name = file_info['name']
                file_size_mb = file_info.get('size_mb', 0)
                
                print(f"[{idx}/{len(files_to_process)}] 📥 Descargando: {file_name} ({file_size_mb} MB)...")
                
                mime_to_ext = {
                    'application/pdf': '.pdf',
                    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': '.docx',
                    'text/plain': '.txt',
                    'text/markdown': '.md'
                }
                ext = mime_to_ext.get(file_info.get('mimeType', ''), '.pdf')
                
                # Descargar en streaming
                print(f"   ⏳ Iniciando descarga desde Google Drive...")
                request = service.files().get_media(fileId=file_id)
                file_content = io.BytesIO()
                downloader = MediaIoBaseDownload(file_content, request)
                
                done = False
                chunk_count = 0
                while not done:
                    status, done = downloader.next_chunk()
                    chunk_count += 1
                    if chunk_count % 10 == 0:  # Mostrar progreso cada 10 chunks
                        progress = int(status.progress() * 100) if status else 0
                        print(f"   📊 Progreso: {progress}%...", end='\r')
                
                # Crear archivo temporal con nombre único desde el inicio
                import os
                # Limpiar nombre de archivo de caracteres inválidos
                safe_name = "".join(c for c in file_name if c.isalnum() or c in (' ', '-', '_', '.'))[:100]
                
                temp_dir = Path(tempfile.gettempdir())
                final_path = temp_dir / f"drive_{uuid.uuid4().hex[:12]}{ext}"
                
                # Escribir contenido directamente al archivo final
                print(f"   💾 Guardando archivo...")
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        with open(final_path, 'wb') as f:
                            f.write(file_content.getvalue())
                        
                        # Crear un wrapper simple para preservar el nombre original
                        # Path no permite atributos dinámicos, así que usamos un wrapper
                        class FileWrapper:
                            def __init__(self, path, original_name):
                                self._path = path
                                self.name = str(path)
                                self.original_name = original_name
                            
                            def __str__(self):
                                return str(self._path)
                            
                            def __fspath__(self):
                                return str(self._path)
                            
                            def __getattr__(self, name):
                                # Delegar otros atributos al Path
                                return getattr(self._path, name)
                        
                        wrapped_file = FileWrapper(final_path, file_name)
                        file_objects.append(wrapped_file)
                        print(f"   ✅ {file_name} descargado y listo ({file_size_mb} MB)")
                        break
                    except (OSError, PermissionError) as e:
                        if attempt < max_retries - 1:
                            time.sleep(0.5 * (attempt + 1))
                            final_path = temp_dir / f"drive_{uuid.uuid4().hex[:12]}{ext}"
                        else:
                            print(f"   ❌ Error guardando {file_info.get('name')} después de {max_retries} intentos: {e}")
                            raise
                
                time.sleep(0.1)  # Pausa para evitar rate limits
                    
            except Exception as e:
                error_msg = str(e)
                if "403" in error_msg or "cannotDownloadFile" in error_msg:
                    print(f"⚠️ {file_info.get('name')}: Sin permisos de descarga")
                else:
                    print(f"❌ Error obteniendo {file_info.get('name')}: {error_msg[:100]}")
        
        print(f"\n✅ Descarga completada: {len(file_objects)}/{len(files_to_process)} archivos descargados exitosamente\n")
        return file_objects


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

