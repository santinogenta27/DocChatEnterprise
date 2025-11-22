"""API REST Server para Enterprise API Mode - Permite a empresas conectarse por API."""

from __future__ import annotations

import os
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime

from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import uvicorn

from docchat import load_config
from docchat.enterprise_api import EnterpriseAPIMode
from docchat.cloud_integrations import CloudStorageIntegration, WebhookProcessor
from docchat.audit import AuditLogger

# Cargar configuración
config = load_config()
enterprise_api = EnterpriseAPIMode(config)
cloud_integration = CloudStorageIntegration(config, enterprise_api)
webhook_processor = WebhookProcessor(config, enterprise_api)
audit_logger = AuditLogger(config.audit_log_dir, config.enable_audit_logs)

# Crear app FastAPI
app = FastAPI(
    title="DocChat Enterprise API",
    description="API para procesamiento automático de documentos con Agentic AI",
    version="1.0.0"
)

# CORS para permitir conexiones desde cualquier origen
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Modelos Pydantic
class Rule(BaseModel):
    name: str
    type: str = "condition"
    condition: Dict[str, Any]
    action: Dict[str, Any]

class EnterpriseAPIRequest(BaseModel):
    auto_detect: bool = True
    rules: Optional[List[Rule]] = None
    webhook_url: Optional[str] = None  # URL para notificaciones

class EnterpriseAPIResponse(BaseModel):
    status: str
    timestamp: str
    documents_processed: int
    chunks_generated: int
    summaries: Dict[str, Any]
    problems_detected: List[Dict[str, Any]]
    opportunities_detected: List[Dict[str, Any]]
    patterns_found: List[Dict[str, Any]]
    actions_taken: List[Dict[str, Any]]
    insights: List[Dict[str, Any]]


# Endpoints
@app.get("/")
async def root():
    """Endpoint raíz con información de la API."""
    return {
        "name": "DocChat Enterprise API",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "POST /api/v1/process": "Procesar documentos",
            "GET /api/v1/health": "Health check",
            "GET /api/v1/stats": "Estadísticas del sistema"
        }
    }


@app.get("/api/v1/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    }


@app.post("/api/v1/process", response_model=EnterpriseAPIResponse)
async def process_documents(
    files: List[UploadFile] = File(...),
    auto_detect: bool = True,
    rules_json: Optional[str] = None,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key")
):
    """
    Procesa documentos empresariales con Agentic AI.
    
    Args:
        files: Lista de archivos a procesar
        auto_detect: Si True, detecta problemas/oportunidades automáticamente
        rules_json: JSON string con reglas de automatización
        x_api_key: API key para autenticación (opcional por ahora)
    
    Returns:
        EnterpriseAPIResponse con resultados completos
    """
    try:
        # Parsear reglas
        rules = []
        if rules_json:
            import json
            rules_data = json.loads(rules_json)
            rules = [r if isinstance(r, dict) else r.dict() for r in rules_data]
        
        # Convertir UploadFile a formato compatible
        file_objects = []
        for file in files:
            # Leer contenido
            content = await file.read()
            # Crear objeto file-like
            from io import BytesIO
            file_obj = BytesIO(content)
            file_obj.name = file.filename
            file_objects.append(file_obj)
        
        # Procesar con Enterprise API
        results = enterprise_api.process_enterprise_documents(
            files=file_objects,
            auto_detect=auto_detect,
            rules=rules
        )
        
        # Log de auditoría
        audit_logger.log(
            event_type="api_request",
            action="process_documents",
            resource="api",
            user_id=x_api_key or "api_user",
            metadata={
                "file_count": len(files),
                "auto_detect": auto_detect,
                "status": results.get("status")
            }
        )
        
        # Convertir a respuesta
        response = EnterpriseAPIResponse(**results)
        return response
        
    except Exception as e:
        audit_logger.log(
            event_type="error",
            action="api_process",
            resource="api",
            result="error",
            metadata={"error": str(e)}
        )
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/stats")
async def get_stats():
    """Obtiene estadísticas del sistema."""
    stats = audit_logger.get_statistics()
    return {
        "audit_logs": stats,
        "timestamp": datetime.now().isoformat()
    }


# ========== CLOUD STORAGE INTEGRATIONS ==========

class S3ConnectionRequest(BaseModel):
    bucket_name: str
    access_key: str
    secret_key: str
    region: str = "us-east-1"
    prefix: str = ""
    auto_process: bool = True

class GCSConnectionRequest(BaseModel):
    bucket_name: str
    credentials_json: str  # JSON string de credenciales
    prefix: str = ""
    auto_process: bool = True

class AzureConnectionRequest(BaseModel):
    container_name: str
    connection_string: str
    prefix: str = ""
    auto_process: bool = True


@app.post("/api/v1/cloud/connect/s3")
async def connect_s3(request: S3ConnectionRequest):
    """
    Conecta un bucket de AWS S3 para procesamiento automático.
    
    Cuando se suban archivos al bucket, se procesarán automáticamente.
    """
    try:
        result = cloud_integration.connect_s3_bucket(
            bucket_name=request.bucket_name,
            access_key=request.access_key,
            secret_key=request.secret_key,
            region=request.region,
            prefix=request.prefix,
            auto_process=request.auto_process
        )
        
        audit_logger.log(
            event_type="cloud_connection",
            action="connect_s3",
            resource="s3",
            metadata={"bucket": request.bucket_name}
        )
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/cloud/connect/gcs")
async def connect_gcs(request: GCSConnectionRequest):
    """
    Conecta un bucket de Google Cloud Storage.
    """
    try:
        # Guardar credenciales temporalmente
        import tempfile
        import json
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(json.loads(request.credentials_json), f)
            creds_path = f.name
        
        result = cloud_integration.connect_gcs_bucket(
            bucket_name=request.bucket_name,
            credentials_path=creds_path,
            prefix=request.prefix,
            auto_process=request.auto_process
        )
        
        # Limpiar archivo temporal
        os.unlink(creds_path)
        
        audit_logger.log(
            event_type="cloud_connection",
            action="connect_gcs",
            resource="gcs",
            metadata={"bucket": request.bucket_name}
        )
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/cloud/connect/azure")
async def connect_azure(request: AzureConnectionRequest):
    """
    Conecta un contenedor de Azure Blob Storage.
    """
    try:
        result = cloud_integration.connect_azure_blob(
            container_name=request.container_name,
            connection_string=request.connection_string,
            prefix=request.prefix,
            auto_process=request.auto_process
        )
        
        audit_logger.log(
            event_type="cloud_connection",
            action="connect_azure",
            resource="azure",
            metadata={"container": request.container_name}
        )
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/cloud/webhook/{source}")
async def process_webhook(
    source: str,
    webhook_data: Dict[str, Any]
):
    """
    Procesa webhooks de cloud storage para sincronización automática.
    
    Fuentes soportadas: s3, gcs, azure
    
    Configura webhooks en tu cloud storage para que notifique a este endpoint
    cuando se suban nuevos archivos.
    """
    try:
        result = webhook_processor.process_webhook(
            webhook_data=webhook_data,
            source=source
        )
        
        audit_logger.log(
            event_type="webhook",
            action="process_webhook",
            resource=source,
            metadata={"source": source}
        )
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    port = int(os.getenv("API_PORT", "8000"))
    print(f"🚀 Iniciando DocChat Enterprise API en http://0.0.0.0:{port}")
    print(f"📚 Documentación: http://0.0.0.0:{port}/docs")
    uvicorn.run(app, host="0.0.0.0", port=port)

