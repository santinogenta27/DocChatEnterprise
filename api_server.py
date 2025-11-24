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
from docchat.enterprise_agentic_ai import EnterpriseAgenticAI
from docchat.customer_service_agent import CustomerServiceAgent
from docchat.chatbot_mode import ChatbotMode
from docchat.cloud_integrations import CloudStorageIntegration, WebhookProcessor
from docchat.rpa_automation import RPAAutomationEngine
from docchat.rpa_enterprise_integration import RPAEnterpriseIntegration
from docchat.audit import AuditLogger

# Cargar configuración
config = load_config()
enterprise_api = EnterpriseAPIMode(config)
enterprise_agentic_ai = EnterpriseAgenticAI(config) if config.enable_autonomous_agents else None
customer_service_agent = CustomerServiceAgent(config) if config.enable_autonomous_agents else None
chatbot_mode = ChatbotMode(config)
cloud_integration = CloudStorageIntegration(config, enterprise_api)
webhook_processor = WebhookProcessor(config, enterprise_api)
audit_logger = AuditLogger(config.audit_log_dir, config.enable_audit_logs)

# Crear app FastAPI
app = FastAPI(
    title="DocChat Enterprise API",
    description="API para procesamiento automático de documentos con Agentic AI y Atención al Cliente 24/7",
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
            "GET /api/v1/stats": "Estadísticas del sistema",
            "POST /api/v1/customer-service/inquiry": "Procesar consulta de cliente",
            "POST /api/v1/customer-service/webhook/{channel}": "Webhook para recibir mensajes en tiempo real",
            "POST /api/v1/customer-service/connect-channel": "Conectar canal externo (Gmail, WhatsApp, etc.)",
            "POST /api/v1/customer-service/load-knowledge": "Cargar base de conocimiento",
            "GET /api/v1/customer-service/stats": "Estadísticas de atención al cliente"
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


# ==================== Enterprise Agentic AI Endpoints ====================

class IDPProcessRequest(BaseModel):
    """Request para procesar documentos con IDP."""
    extract_entities: bool = True
    extract_metrics: bool = True


class AgenticTaskRequest(BaseModel):
    """Request para ejecutar tarea autónoma."""
    task_description: str = Field(..., description="Descripción de la tarea a ejecutar")
    task_type: str = Field(
        default="análisis",
        description="Tipo de tarea: análisis, automatización, integración, generación, optimización"
    )
    context: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Contexto adicional en JSON")
    use_processed_data: bool = Field(default=True, description="Usar datos procesados con IDP")


@app.post("/api/v1/agentic-ai/process-idp")
async def process_documents_with_idp(
    files: List[UploadFile] = File(...),
    extract_entities: bool = True,
    extract_metrics: bool = True
):
    """
    Procesa documentos con Intelligent Document Processing (IDP).
    
    IDP extrae información estructurada de documentos:
    - Clasificación de tipo de documento
    - Extracción de entidades (nombres, fechas, montos, etc.)
    - Extracción de métricas clave
    - Estructuración de contenido
    """
    if not enterprise_agentic_ai:
        raise HTTPException(
            status_code=503,
            detail="Enterprise Agentic AI no está habilitado. Configura DOCCHAT_ENABLE_AGENTS=true"
        )
    
    try:
        # Convertir UploadFile a objetos procesables
        file_objects = []
        for file in files:
            # Crear objeto temporal con atributos necesarios
            class FileObj:
                def __init__(self, name, content):
                    self.name = name
                    self.content = content
                    self.read = lambda: content
                    self.seek = lambda pos: None
            
            content = await file.read()
            file_obj = FileObj(file.filename, content)
            file_objects.append(file_obj)
        
        # Procesar con IDP
        idp_results = enterprise_agentic_ai.process_documents_with_idp(
            files=file_objects,
            extract_entities=extract_entities,
            extract_metrics=extract_metrics
        )
        
        # Formatear resultados para respuesta
        results = {}
        for file_name, result in idp_results.items():
            results[file_name] = {
                "document_type": result.document_type,
                "entities": result.entities,
                "key_metrics": result.key_metrics,
                "structured_content": result.structured_content,
                "metadata": result.metadata
            }
        
        audit_logger.log(
            event_type="idp_processing",
            action="process_documents",
            resource="enterprise_agentic_ai",
            metadata={"file_count": len(files)}
        )
        
        return {
            "success": True,
            "documents_processed": len(idp_results),
            "results": results
        }
        
    except Exception as e:
        audit_logger.log(
            event_type="idp_processing",
            action="error",
            resource="enterprise_agentic_ai",
            metadata={"error": str(e)}
        )
        raise HTTPException(status_code=500, detail=f"Error en procesamiento IDP: {str(e)}")


@app.post("/api/v1/agentic-ai/execute-task")
async def execute_agentic_task(request: AgenticTaskRequest):
    """
    Ejecuta una tarea autónoma usando Enterprise Agentic AI.
    
    Tipos de tareas soportadas:
    - análisis: Analizar datos y generar insights
    - automatización: Automatizar procesos empresariales
    - integración: Integrar con sistemas externos
    - generación: Generar contenido, informes, etc.
    - optimización: Optimizar procesos y recursos
    """
    if not enterprise_agentic_ai:
        raise HTTPException(
            status_code=503,
            detail="Enterprise Agentic AI no está habilitado. Configura DOCCHAT_ENABLE_AGENTS=true"
        )
    
    if request.use_processed_data and not enterprise_agentic_ai.idp_results:
        raise HTTPException(
            status_code=400,
            detail="No hay documentos procesados con IDP. Primero procesa documentos con /api/v1/agentic-ai/process-idp"
        )
    
    try:
        result = enterprise_agentic_ai.execute_autonomous_task(
            task_description=request.task_description,
            task_type=request.task_type,
            context=request.context or {},
            use_processed_data=request.use_processed_data
        )
        
        audit_logger.log(
            event_type="enterprise_agentic_task",
            action="execute_task",
            resource="enterprise_agentic_ai",
            metadata={
                "task": request.task_description[:100],
                "task_type": request.task_type
            }
        )
        
        return {
            "success": result.get("success", False),
            "task_description": result.get("task_description"),
            "task_type": result.get("task_type"),
            "tools_used": result.get("tools_used", []),
            "summary": result.get("summary", ""),
            "idp_data_used": result.get("idp_data_used", 0),
            "results": result.get("results", [])
        }
        
    except Exception as e:
        audit_logger.log(
            event_type="enterprise_agentic_task",
            action="error",
            resource="enterprise_agentic_ai",
            metadata={"error": str(e)}
        )
        raise HTTPException(status_code=500, detail=f"Error ejecutando tarea: {str(e)}")


@app.get("/api/v1/agentic-ai/idp-summary")
async def get_idp_summary():
    """Obtiene un resumen de todos los documentos procesados con IDP."""
    if not enterprise_agentic_ai:
        raise HTTPException(
            status_code=503,
            detail="Enterprise Agentic AI no está habilitado."
        )
    
    if not enterprise_agentic_ai.idp_results:
        return {
            "success": True,
            "message": "No hay documentos procesados con IDP.",
            "documents": []
        }
    
    documents = []
    for file_name, result in enterprise_agentic_ai.idp_results.items():
        documents.append({
            "file_name": file_name,
            "document_type": result.document_type,
            "entities_count": len(result.entities),
            "metrics_count": len(result.key_metrics),
            "entities": result.entities[:10],  # Primeras 10 entidades
            "key_metrics": dict(list(result.key_metrics.items())[:5])  # Primeras 5 métricas
        })
    
        return {
            "success": True,
            "documents_processed": len(documents),
            "documents": documents
        }


# ==================== Chatbot Mode Endpoints ====================

class ChatbotQueryRequest(BaseModel):
    """Request para consultar chatbot."""
    chatbot_id: str = Field(..., description="ID del chatbot")
    question: str = Field(..., description="Pregunta del usuario")
    use_reranking: bool = Field(default=True, description="Usar reranking avanzado")
    max_chunks: int = Field(default=5, description="Máximo número de chunks a usar")


class ChatbotRegisterRequest(BaseModel):
    """Request para registrar chatbot."""
    chatbot_name: str = Field(..., description="Nombre del chatbot")
    company_name: str = Field(..., description="Nombre de la empresa")
    api_key: Optional[str] = Field(None, description="API key personalizada (opcional)")


def verify_chatbot_api_key(chatbot_id: str, api_key: str) -> bool:
    """Verifica que el API key sea válido para el chatbot."""
    try:
        chatbot_info = chatbot_mode.get_chatbot_info(chatbot_id)
        return chatbot_info.get("api_key") == api_key
    except Exception:
        return False


@app.post("/api/v1/chatbot/query")
async def query_chatbot_api(
    request: ChatbotQueryRequest,
    authorization: Optional[str] = Header(None, alias="Authorization")
):
    """
    Endpoint para que chatbots externos consulten la base vectorizada.
    
    Autenticación: Bearer token con formato: "Bearer chatbot_id:api_key"
    """
    try:
        # Verificar autenticación
        if not authorization:
            raise HTTPException(status_code=401, detail="Authorization header required")
        
        # Extraer chatbot_id y api_key del header
        auth_parts = authorization.replace("Bearer ", "").strip().split(":")
        if len(auth_parts) != 2:
            raise HTTPException(status_code=401, detail="Invalid authorization format. Use: Bearer chatbot_id:api_key")
        
        auth_chatbot_id, auth_api_key = auth_parts
        
        # Verificar que el chatbot_id coincida
        if auth_chatbot_id != request.chatbot_id:
            raise HTTPException(status_code=403, detail="Chatbot ID mismatch")
        
        # Verificar API key
        if not verify_chatbot_api_key(auth_chatbot_id, auth_api_key):
            raise HTTPException(status_code=403, detail="Invalid API key")
        
        # Consultar chatbot
        response = chatbot_mode.query_chatbot(
            chatbot_id=request.chatbot_id,
            user_question=request.question,
            use_reranking=request.use_reranking,
            max_chunks=request.max_chunks
        )
        
        audit_logger.log(
            event_type="chatbot_query",
            action="api_query",
            resource="chatbot_mode",
            metadata={
                "chatbot_id": request.chatbot_id,
                "question_length": len(request.question),
                "chunks_used": response.chunks_used
            }
        )
        
        return {
            "success": True,
            "answer": response.answer,
            "sources": response.sources,
            "confidence": response.confidence,
            "chunks_used": response.chunks_used,
            "reranked": response.reranked,
            "metadata": response.metadata
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        audit_logger.log(
            event_type="chatbot_query",
            action="error",
            resource="chatbot_mode",
            metadata={"error": str(e)}
        )
        raise HTTPException(status_code=500, detail=f"Error consultando chatbot: {str(e)}")


@app.post("/api/v1/chatbot/register")
async def register_chatbot_api(request: ChatbotRegisterRequest):
    """Registra un nuevo chatbot."""
    try:
        connection = chatbot_mode.register_chatbot(
            chatbot_name=request.chatbot_name,
            company_name=request.company_name,
            api_key=request.api_key
        )
        
        audit_logger.log(
            event_type="chatbot_registration",
            action="api_register",
            resource="chatbot_mode",
            metadata={
                "chatbot_name": connection.chatbot_name,
                "company_name": connection.company_name
            }
        )
        
        return {
            "success": True,
            "chatbot_id": connection.chatbot_id,
            "api_key": connection.api_key,
            "chatbot_name": connection.chatbot_name,
            "company_name": connection.company_name,
            "created_at": connection.created_at
        }
        
    except Exception as e:
        audit_logger.log(
            event_type="chatbot_registration",
            action="error",
            resource="chatbot_mode",
            metadata={"error": str(e)}
        )
        raise HTTPException(status_code=500, detail=f"Error registrando chatbot: {str(e)}")


@app.post("/api/v1/chatbot/upload-data")
async def upload_chatbot_data_api(
    chatbot_id: str,
    files: List[UploadFile] = File(...),
    authorization: Optional[str] = Header(None, alias="Authorization")
):
    """Sube data para un chatbot."""
    try:
        # Verificar autenticación
        if not authorization:
            raise HTTPException(status_code=401, detail="Authorization header required")
        
        auth_parts = authorization.replace("Bearer ", "").strip().split(":")
        if len(auth_parts) != 2:
            raise HTTPException(status_code=401, detail="Invalid authorization format")
        
        auth_chatbot_id, auth_api_key = auth_parts
        
        if auth_chatbot_id != chatbot_id:
            raise HTTPException(status_code=403, detail="Chatbot ID mismatch")
        
        if not verify_chatbot_api_key(auth_chatbot_id, auth_api_key):
            raise HTTPException(status_code=403, detail="Invalid API key")
        
        # Convertir UploadFile a objetos procesables
        file_objects = []
        for file in files:
            class FileObj:
                def __init__(self, name, content):
                    self.name = name
                    self.content = content
                    self.read = lambda: content
                    self.seek = lambda pos: None
            
            content = await file.read()
            file_obj = FileObj(file.filename, content)
            file_objects.append(file_obj)
        
        # Procesar data
        result = chatbot_mode.upload_chatbot_data(
            chatbot_id=chatbot_id,
            files=file_objects
        )
        
        audit_logger.log(
            event_type="chatbot_data_upload",
            action="api_upload",
            resource="chatbot_mode",
            metadata={
                "chatbot_id": chatbot_id,
                "files_count": len(files)
            }
        )
        
        return {
            "success": True,
            "chatbot_id": chatbot_id,
            "documents_processed": result["documents_processed"],
            "chunks_created": result["chunks_created"]
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        audit_logger.log(
            event_type="chatbot_data_upload",
            action="error",
            resource="chatbot_mode",
            metadata={"error": str(e)}
        )
        raise HTTPException(status_code=500, detail=f"Error subiendo data: {str(e)}")


@app.get("/api/v1/chatbot/info/{chatbot_id}")
async def get_chatbot_info_api(
    chatbot_id: str,
    authorization: Optional[str] = Header(None, alias="Authorization")
):
    """Obtiene información de un chatbot."""
    try:
        # Verificar autenticación
        if not authorization:
            raise HTTPException(status_code=401, detail="Authorization header required")
        
        auth_parts = authorization.replace("Bearer ", "").strip().split(":")
        if len(auth_parts) != 2:
            raise HTTPException(status_code=401, detail="Invalid authorization format")
        
        auth_chatbot_id, auth_api_key = auth_parts
        
        if auth_chatbot_id != chatbot_id:
            raise HTTPException(status_code=403, detail="Chatbot ID mismatch")
        
        if not verify_chatbot_api_key(auth_chatbot_id, auth_api_key):
            raise HTTPException(status_code=403, detail="Invalid API key")
        
        info = chatbot_mode.get_chatbot_info(chatbot_id)
        # No retornar api_key por seguridad
        info.pop("api_key", None)
        
        return {
            "success": True,
            "chatbot": info
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo info: {str(e)}")


# ============================================================================
# CUSTOMER SERVICE API ENDPOINTS - Atención al Cliente Automática 24/7
# ============================================================================

class CustomerInquiryRequest(BaseModel):
    """Request para procesar consulta de cliente."""
    channel: str = Field(..., description="Canal: email, whatsapp, chat, phone")
    customer_email: str = Field(..., description="Email del cliente")
    message: str = Field(..., description="Mensaje del cliente")
    customer_phone: Optional[str] = Field(None, description="Teléfono (para WhatsApp)")
    subject: Optional[str] = Field(None, description="Asunto (para emails)")
    use_knowledge_base: bool = Field(True, description="Usar base de conocimiento RAG")


class CustomerInquiryResponse(BaseModel):
    """Response de consulta procesada."""
    success: bool
    inquiry_id: str
    response_text: str
    channel: str
    sent: bool
    ticket_created: bool
    ticket_id: Optional[str] = None
    tools_used: List[str] = []
    confidence: float
    escalated: bool
    timestamp: str


class ChannelConnectionRequest(BaseModel):
    """Request para conectar canal externo."""
    channel_type: str = Field(..., description="Tipo: gmail, whatsapp_business, slack, teams")
    credentials: Dict[str, Any] = Field(..., description="Credenciales del canal")
    webhook_url: Optional[str] = Field(None, description="URL para recibir notificaciones")
    auto_respond: bool = Field(True, description="Responder automáticamente a mensajes")


@app.post("/api/v1/customer-service/inquiry", response_model=CustomerInquiryResponse)
async def process_customer_inquiry(
    request: CustomerInquiryRequest,
    authorization: Optional[str] = Header(None, alias="Authorization")
):
    """
    Procesa una consulta de cliente y genera respuesta automática.
    
    Este endpoint permite a sistemas externos enviar consultas de clientes
    y recibir respuestas automáticas generadas por Agentic AI.
    """
    if not customer_service_agent:
        raise HTTPException(
            status_code=503,
            detail="Customer Service Agent no está habilitado. Configure DOCCHAT_ENABLE_AGENTS=true"
        )
    
    try:
        audit_logger.log(
            event_type="customer_inquiry",
            action="process",
            resource="customer_service",
            metadata={
                "channel": request.channel,
                "customer_email": request.customer_email[:50]
            }
        )
        
        # Procesar consulta
        response = customer_service_agent.process_inquiry(
            channel=request.channel,
            customer_email=request.customer_email,
            message=request.message,
            customer_phone=request.customer_phone,
            subject=request.subject,
            use_knowledge_base=request.use_knowledge_base
        )
        
        return CustomerInquiryResponse(
            success=True,
            inquiry_id=response.inquiry_id,
            response_text=response.response_text,
            channel=response.channel,
            sent=response.sent,
            ticket_created=response.ticket_created,
            ticket_id=response.ticket_id,
            tools_used=response.tools_used,
            confidence=response.confidence,
            escalated=response.escalated,
            timestamp=datetime.now().isoformat()
        )
    
    except Exception as e:
        audit_logger.log(
            event_type="customer_inquiry",
            action="error",
            resource="customer_service",
            metadata={"error": str(e)}
        )
        raise HTTPException(status_code=500, detail=f"Error procesando consulta: {str(e)}")


@app.post("/api/v1/customer-service/webhook/{channel}")
async def customer_service_webhook(
    channel: str,
    payload: Dict[str, Any],
    authorization: Optional[str] = Header(None, alias="X-Webhook-Token")
):
    """
    Webhook para recibir mensajes de clientes en tiempo real.
    
    Este endpoint permite a servicios externos (Gmail, WhatsApp Business, etc.)
    enviar mensajes de clientes que serán procesados automáticamente.
    
    Formatos soportados:
    - Gmail: { "from": "email", "subject": "...", "body": "...", "message_id": "..." }
    - WhatsApp: { "from": "phone", "message": "...", "message_id": "..." }
    - Slack: { "user": "...", "text": "...", "channel": "..." }
    """
    if not customer_service_agent:
        raise HTTPException(
            status_code=503,
            detail="Customer Service Agent no está habilitado"
        )
    
    try:
        # Validar token de webhook (opcional pero recomendado)
        expected_token = os.getenv("WEBHOOK_TOKEN", "")
        if expected_token and authorization != f"Bearer {expected_token}":
            raise HTTPException(status_code=401, detail="Invalid webhook token")
        
        # Parsear mensaje según el canal
        if channel == "gmail" or channel == "email":
            customer_email = payload.get("from", payload.get("sender", ""))
            message = payload.get("body", payload.get("text", payload.get("message", "")))
            subject = payload.get("subject", "")
            
            if not customer_email or not message:
                raise HTTPException(status_code=400, detail="Missing 'from' or 'body' in payload")
        
        elif channel == "whatsapp":
            customer_phone = payload.get("from", payload.get("phone", ""))
            customer_email = payload.get("email", f"whatsapp_{customer_phone}@unknown.com")
            message = payload.get("message", payload.get("text", payload.get("body", "")))
            
            if not customer_phone or not message:
                raise HTTPException(status_code=400, detail="Missing 'from' or 'message' in payload")
        
        elif channel == "slack":
            customer_email = payload.get("user_email", payload.get("user", f"slack_{payload.get('user_id', 'unknown')}@slack.com"))
            message = payload.get("text", payload.get("message", ""))
            subject = f"Slack: {payload.get('channel', 'general')}"
            
            if not message:
                raise HTTPException(status_code=400, detail="Missing 'text' or 'message' in payload")
        
        else:
            # Formato genérico
            customer_email = payload.get("customer_email", payload.get("from", payload.get("email", "unknown@unknown.com")))
            message = payload.get("message", payload.get("text", payload.get("body", "")))
            subject = payload.get("subject", "")
            customer_phone = payload.get("customer_phone", payload.get("phone"))
        
        # Procesar consulta automáticamente
        response = customer_service_agent.process_inquiry(
            channel=channel,
            customer_email=customer_email,
            message=message,
            customer_phone=customer_phone if channel == "whatsapp" else None,
            subject=subject if channel in ["email", "gmail"] else None,
            use_knowledge_base=True
        )
        
        audit_logger.log(
            event_type="customer_service_webhook",
            action="processed",
            resource="customer_service",
            metadata={
                "channel": channel,
                "inquiry_id": response.inquiry_id,
                "sent": response.sent
            }
        )
        
        return {
            "success": True,
            "inquiry_id": response.inquiry_id,
            "response_sent": response.sent,
            "ticket_id": response.ticket_id,
            "escalated": response.escalated,
            "timestamp": datetime.now().isoformat()
        }
    
    except HTTPException:
        raise
    except Exception as e:
        audit_logger.log(
            event_type="customer_service_webhook",
            action="error",
            resource="customer_service",
            metadata={"error": str(e), "channel": channel}
        )
        raise HTTPException(status_code=500, detail=f"Error procesando webhook: {str(e)}")


@app.post("/api/v1/customer-service/connect-channel")
async def connect_channel(
    request: ChannelConnectionRequest,
    authorization: Optional[str] = Header(None, alias="Authorization")
):
    """
    Conecta un canal externo (Gmail, WhatsApp Business, etc.) para recibir mensajes automáticamente.
    
    Ejemplo para Gmail:
    {
        "channel_type": "gmail",
        "credentials": {
            "client_id": "...",
            "client_secret": "...",
            "refresh_token": "..."
        },
        "webhook_url": "https://tu-servidor.com/api/v1/customer-service/webhook/gmail",
        "auto_respond": true
    }
    """
    if not customer_service_agent:
        raise HTTPException(
            status_code=503,
            detail="Customer Service Agent no está habilitado"
        )
    
    try:
        # Aquí se implementaría la lógica de conexión real
        # Por ahora, solo registramos la conexión
        
        audit_logger.log(
            event_type="channel_connection",
            action="connect",
            resource="customer_service",
            metadata={
                "channel_type": request.channel_type,
                "auto_respond": request.auto_respond
            }
        )
        
        return {
            "success": True,
            "channel_type": request.channel_type,
            "status": "connected",
            "webhook_url": request.webhook_url,
            "auto_respond": request.auto_respond,
            "message": f"Canal {request.channel_type} conectado. Configura el webhook en tu servicio externo para: {request.webhook_url or 'N/A'}",
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error conectando canal: {str(e)}")


@app.post("/api/v1/customer-service/load-knowledge")
async def load_customer_service_knowledge(
    files: List[UploadFile] = File(...),
    authorization: Optional[str] = Header(None, alias="Authorization")
):
    """
    Carga documentos en la base de conocimiento para Customer Service.
    
    Estos documentos serán usados por el Agentic AI para responder consultas de clientes.
    """
    if not customer_service_agent:
        raise HTTPException(
            status_code=503,
            detail="Customer Service Agent no está habilitado"
        )
    
    try:
        # Guardar archivos temporalmente
        temp_files = []
        for file in files:
            temp_path = Path(config.temp_dir) / f"cs_kb_{datetime.now().timestamp()}_{file.filename}"
            temp_path.parent.mkdir(parents=True, exist_ok=True)
            with open(temp_path, "wb") as f:
                content = await file.read()
                f.write(content)
            temp_files.append(temp_path)
        
        # Cargar en base de conocimiento
        customer_service_agent.load_knowledge_base(temp_files)
        
        stats = customer_service_agent.get_stats()
        
        # Limpiar archivos temporales
        for temp_file in temp_files:
            try:
                temp_file.unlink()
            except:
                pass
        
        audit_logger.log(
            event_type="customer_service_knowledge",
            action="load",
            resource="customer_service",
            metadata={"files_count": len(files), "chunks": stats.get("knowledge_base_documents", 0)}
        )
        
        return {
            "success": True,
            "files_loaded": len(files),
            "knowledge_base_chunks": stats.get("knowledge_base_documents", 0),
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error cargando base de conocimiento: {str(e)}")


@app.get("/api/v1/customer-service/stats")
async def get_customer_service_stats(
    authorization: Optional[str] = Header(None, alias="Authorization")
):
    """Obtiene estadísticas del servicio de atención al cliente."""
    if not customer_service_agent:
        raise HTTPException(
            status_code=503,
            detail="Customer Service Agent no está habilitado"
        )
    
    try:
        stats = customer_service_agent.get_stats()
        return {
            "success": True,
            "stats": stats,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo estadísticas: {str(e)}")


if __name__ == "__main__":
    port = int(os.getenv("API_PORT", "8000"))
    print(f"🚀 Iniciando DocChat Enterprise API en http://0.0.0.0:{port}")
    print(f"📚 Documentación: http://0.0.0.0:{port}/docs")
    uvicorn.run(app, host="0.0.0.0", port=port)

