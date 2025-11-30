"""
API RESTful para Modo Chatbot - Backend RAG para Chatbots Empresariales

Backend RAG que permite a empresas conectar sus chatbots existentes
y usar RAG con su data privada para responder consultas.

Flujo:
1. Cliente pregunta → En el chatbot de la empresa (en su app)
2. Chatbot de la empresa consulta → DocChat Enterprise por API
3. DocChat Enterprise busca → En documentos privados de la empresa
4. DocChat Enterprise responde → Al chatbot de la empresa
5. Chatbot de la empresa muestra → Respuesta al cliente en su app

Endpoints:
- POST /api/chatbot/register - Registrar nuevo chatbot
- POST /api/chatbot/{chatbot_id}/upload - Subir documentos
- POST /api/chatbot/{chatbot_id}/query - Consultar RAG (PRINCIPAL)
- GET /api/chatbot/{chatbot_id}/info - Info del chatbot
- GET /api/chatbot/list - Listar chatbots
"""

from __future__ import annotations

import json
from typing import Dict, List, Optional, Any
from fastapi import FastAPI, HTTPException, Header, UploadFile, File, Form
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import json

from .chatbot_mode import ChatbotMode, RAGResponse
from .config import AppConfig


# ==================== Modelos Pydantic ====================

class RegisterChatbotRequest(BaseModel):
    chatbot_name: str
    company_name: str
    api_key: Optional[str] = None


class RegisterChatbotResponse(BaseModel):
    chatbot_id: str
    chatbot_name: str
    company_name: str
    api_key: str
    message: str


class QueryRequest(BaseModel):
    question: str
    use_reranking: bool = True
    max_chunks: int = 5
    use_cache: bool = True


class NeedsRAGRequest(BaseModel):
    question: str


class NeedsRAGResponse(BaseModel):
    needs_rag: bool
    reason: str


class QueryResponse(BaseModel):
    answer: str
    sources: List[str]
    confidence: float
    chunks_used: int
    reranked: bool
    metadata: Dict[str, Any]


class ChatbotInfoResponse(BaseModel):
    chatbot_id: str
    chatbot_name: str
    company_name: str
    status: str
    documents_count: int
    chunks_count: int
    created_at: str


class UploadResponse(BaseModel):
    chatbot_id: str
    documents_processed: int
    chunks_created: int
    message: str


# ==================== API Router ====================

def create_chatbot_api(app: FastAPI, chatbot_mode: ChatbotMode):
    """Crea los endpoints de API para el modo Chatbot."""
    
    # CORS para permitir requests desde cualquier origen (empresas externas)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # En producción, especificar dominios permitidos
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    @app.post("/api/chatbot/register", response_model=RegisterChatbotResponse)
    async def register_chatbot(request: RegisterChatbotRequest):
        """
        Registra un nuevo chatbot.
        
        Ejemplo de uso desde tu chatbot:
        ```python
        import requests
        
        response = requests.post(
            "https://tu-servidor.com/api/chatbot/register",
            json={
                "chatbot_name": "Chatbot Soporte MercadoLibre",
                "company_name": "MercadoLibre"
            }
        )
        data = response.json()
        chatbot_id = data["chatbot_id"]
        api_key = data["api_key"]
        ```
        """
        try:
            connection = chatbot_mode.register_chatbot(
                chatbot_name=request.chatbot_name,
                company_name=request.company_name,
                api_key=request.api_key
            )
            
            return RegisterChatbotResponse(
                chatbot_id=connection.chatbot_id,
                chatbot_name=connection.chatbot_name,
                company_name=connection.company_name,
                api_key=connection.api_key,
                message="Chatbot registrado exitosamente. Guarda el chatbot_id y api_key."
            )
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))
    
    @app.post("/api/chatbot/{chatbot_id}/upload", response_model=UploadResponse)
    async def upload_documents(
        chatbot_id: str,
        files: List[UploadFile] = File(...),
        api_key: str = Header(..., alias="X-API-Key")
    ):
        """
        Sube y procesa documentos para un chatbot.
        
        Ejemplo de uso:
        ```python
        import requests
        
        files = [
            ("files", open("documento1.pdf", "rb")),
            ("files", open("documento2.pdf", "rb"))
        ]
        
        response = requests.post(
            f"https://tu-servidor.com/api/chatbot/{chatbot_id}/upload",
            files=files,
            headers={"X-API-Key": api_key}
        )
        ```
        """
        try:
            # Verificar API key
            chatbot_info = chatbot_mode.get_chatbot_info(chatbot_id)
            if chatbot_info["api_key"] != api_key:
                raise HTTPException(status_code=401, detail="API key inválida")
            
            # Convertir UploadFile a formato esperado por chatbot_mode
            file_objects = []
            for file in files:
                # Leer contenido del archivo
                content = await file.read()
                # Crear objeto tipo file para compatibilidad
                from io import BytesIO
                file_obj = BytesIO(content)
                file_obj.name = file.filename
                file_objects.append(file_obj)
            
            result = chatbot_mode.upload_chatbot_data(
                chatbot_id=chatbot_id,
                files=file_objects
            )
            
            return UploadResponse(
                chatbot_id=chatbot_id,
                documents_processed=result["documents_processed"],
                chunks_created=result["chunks_created"],
                message=f"✅ {result['documents_processed']} documentos procesados, {result['chunks_created']} chunks creados"
            )
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/api/chatbot/{chatbot_id}/query", response_model=QueryResponse)
    async def query_chatbot(
        chatbot_id: str,
        request: QueryRequest,
        api_key: str = Header(..., alias="X-API-Key")
    ):
        """
        Consulta el RAG del chatbot.
        
        Esta es la función principal que tu chatbot empresarial debe usar.
        
        Flujo:
        1. Cliente pregunta → En tu chatbot (en tu app)
        2. Tu chatbot llama este endpoint → DocChat Enterprise busca en tus documentos
        3. DocChat Enterprise responde → A tu chatbot
        4. Tu chatbot muestra → Respuesta al cliente en tu app
        
        Ejemplo de uso desde tu chatbot:
        ```python
        import requests
        
        # Cuando un cliente pregunta en tu chatbot (en tu app)
        user_question = "¿Cuál es la política de devoluciones?"
        
        # Tu chatbot consulta a DocChat Enterprise (backend RAG)
        response = requests.post(
            f"https://tu-servidor.com/api/chatbot/{chatbot_id}/query",
            json={
                "question": user_question,
                "use_reranking": True,
                "max_chunks": 5
            },
            headers={"X-API-Key": api_key}
        )
        
        data = response.json()
        answer = data["answer"]  # Esta es la respuesta que muestras al cliente
        sources = data["sources"]  # Fuentes usadas (opcional mostrar)
        
        # Mostrar answer al cliente en TU APP
        ```
        """
        try:
            # Verificar API key
            chatbot_info = chatbot_mode.get_chatbot_info(chatbot_id)
            if chatbot_info["api_key"] != api_key:
                raise HTTPException(status_code=401, detail="API key inválida")
            
            # Consultar RAG
            rag_response = chatbot_mode.query_chatbot(
                chatbot_id=chatbot_id,
                user_question=request.question,
                use_reranking=request.use_reranking,
                max_chunks=request.max_chunks,
                use_cache=request.use_cache
            )
            
            return QueryResponse(
                answer=rag_response.answer,
                sources=rag_response.sources,
                confidence=rag_response.confidence,
                chunks_used=rag_response.chunks_used,
                reranked=rag_response.reranked,
                metadata=rag_response.metadata
            )
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/api/chatbot/{chatbot_id}/needs-rag", response_model=NeedsRAGResponse)
    async def needs_rag(
        chatbot_id: str,
        request: NeedsRAGRequest,
        api_key: str = Header(..., alias="X-API-Key")
    ):
        """
        Determina si la pregunta necesita consultar documentos privados.
        
        Útil para decidir si usar RAG o responder directamente.
        
        Ejemplo:
        ```python
        response = requests.post(
            f"/api/chatbot/{chatbot_id}/needs-rag",
            json={"question": "¿Cuál es la política de devoluciones?"},
            headers={"X-API-Key": api_key}
        )
        needs_rag = response.json()["needs_rag"]
        ```
        """
        try:
            # Verificar API key
            chatbot_info = chatbot_mode.get_chatbot_info(chatbot_id)
            if chatbot_info["api_key"] != api_key:
                raise HTTPException(status_code=401, detail="API key inválida")
            
            needs = chatbot_mode.needs_rag(chatbot_id, request.question)
            reason = "La pregunta requiere consultar documentos privados" if needs else "La pregunta puede responderse directamente"
            
            return NeedsRAGResponse(needs_rag=needs, reason=reason)
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/api/chatbot/{chatbot_id}/query/stream")
    async def query_chatbot_stream(
        chatbot_id: str,
        request: QueryRequest,
        api_key: str = Header(..., alias="X-API-Key")
    ):
        """
        Consulta el RAG y genera respuesta en streaming (palabra por palabra).
        
        Útil para mostrar la respuesta mientras se genera.
        
        Ejemplo:
        ```python
        response = requests.post(
            f"/api/chatbot/{chatbot_id}/query/stream",
            json={"question": "¿Cuál es la política?"},
            headers={"X-API-Key": api_key},
            stream=True
        )
        
        for line in response.iter_lines():
            if line:
                chunk = json.loads(line)
                print(chunk["chunk"], end="", flush=True)
        ```
        """
        try:
            # Verificar API key
            chatbot_info = chatbot_mode.get_chatbot_info(chatbot_id)
            if chatbot_info["api_key"] != api_key:
                raise HTTPException(status_code=401, detail="API key inválida")
            
            def generate():
                try:
                    for chunk in chatbot_mode.query_chatbot_stream(
                        chatbot_id=chatbot_id,
                        user_question=request.question,
                        use_reranking=request.use_reranking,
                        max_chunks=request.max_chunks
                    ):
                        yield json.dumps({"chunk": chunk}) + "\n"
                except Exception as e:
                    yield json.dumps({"error": str(e)}) + "\n"
            
            return StreamingResponse(
                generate(),
                media_type="application/x-ndjson"
            )
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/api/chatbot/{chatbot_id}/info", response_model=ChatbotInfoResponse)
    async def get_chatbot_info(
        chatbot_id: str,
        api_key: str = Header(..., alias="X-API-Key")
    ):
        """Obtiene información de un chatbot."""
        try:
            chatbot_info = chatbot_mode.get_chatbot_info(chatbot_id)
            if chatbot_info["api_key"] != api_key:
                raise HTTPException(status_code=401, detail="API key inválida")
            
            return ChatbotInfoResponse(**chatbot_info)
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))
    
    @app.get("/api/chatbot/list")
    async def list_chatbots():
        """Lista todos los chatbots registrados (sin API key para admin)."""
        try:
            chatbots = chatbot_mode.list_chatbots()
            return {"chatbots": chatbots, "count": len(chatbots)}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/api/chatbot/health")
    async def health_check():
        """Health check del servicio."""
        return {
            "status": "healthy",
            "service": "Chatbot Mode API",
            "version": "1.0.0"
        }

