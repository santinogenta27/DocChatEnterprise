"""
API Server para Widget Embebible de ChatPDF Mode.
Widget simple que expone ChatPDF como API sin modificaciones.
"""

from __future__ import annotations
from typing import Optional, Any, Dict, List
import json
from pathlib import Path

# Intentar importar FastAPI
try:
    from fastapi import FastAPI, Request, Body, UploadFile, File
    from fastapi.responses import JSONResponse
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.staticfiles import StaticFiles
    FASTAPI_AVAILABLE = True
except ImportError as e:
    FASTAPI_AVAILABLE = False
    print(f"⚠️ Error importando FastAPI: {e}")

def create_api_server_chatpdf(chatpdf_mode) -> Optional[Any]:
    """
    Crea aplicación FastAPI para widget de ChatPDF Mode.
    
    Args:
        chatpdf_mode: Instancia de ChatPDFMode
        
    Returns:
        FastAPI app o None si FastAPI no está disponible
    """
    if not FASTAPI_AVAILABLE:
        return None
    
    app = FastAPI(
        title="ChatPDF Widget API",
        description="API para widget web de ChatPDF Mode"
    )
    
    # CORS para widget embebido
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        return {
            "status": "healthy",
            "service": "chatpdf_widget",
            "chatpdf_mode_available": chatpdf_mode is not None
        }
    
    @app.post("/api/widget/chat")
    async def widget_chat(request: Request, payload: Dict[str, Any] = Body(...)):
        """
        Endpoint REST de chat para widget web.
        Usa la lógica existente de ChatPDF sin modificaciones.
        IMPORTANTE: Usa session_id="gradio_user" para compartir documentos con la UI de Gradio.
        """
        try:
            message = payload.get("message", "")
            # Usar "gradio_user" por defecto para compartir documentos con ChatPDF UI
            session_id = payload.get("session_id") or "gradio_user"
            history = payload.get("history", [])
            
            if not message:
                return JSONResponse(content={
                    "text": "Error: Mensaje vacío",
                    "error": True
                })
            
            # Convertir history a formato de ChatPDF (tuplas)
            chatpdf_history = []
            for h in history:
                if isinstance(h, (list, tuple)) and len(h) >= 2:
                    chatpdf_history.append((str(h[0]), str(h[1]) if h[1] else ""))
                elif isinstance(h, dict):
                    # Si viene como dict, convertir a tupla
                    user_msg = h.get("content", h.get("message", ""))
                    assistant_msg = h.get("response", h.get("text", ""))
                    chatpdf_history.append((user_msg, assistant_msg))
                else:
                    chatpdf_history.append((str(h), ""))
            
            # Llamar a process_query_async de ChatPDF (lógica original sin modificar)
            # Esta es la misma función que usa la UI de Gradio
            result_generator = chatpdf_mode.process_query_async(
                session_id=session_id,
                message=message,
                history=chatpdf_history,
                speed_mode="fast",
                provider="openai"
            )
            
            # ChatPDF retorna un generador, obtener el último resultado
            final_history = None
            final_error = None
            final_metadata = {}
            
            async for history_update, error, metadata in result_generator:
                final_history = history_update
                final_error = error
                final_metadata = metadata or {}
            
            if final_error:
                return JSONResponse(content={
                    "text": f"Error: {final_error}",
                    "error": True,
                    "metadata": final_metadata
                })
            
            # Extraer la última respuesta
            if final_history and len(final_history) > 0:
                last_response = final_history[-1][1] if len(final_history[-1]) > 1 else "No hay respuesta"
            else:
                last_response = "No hay respuesta"
            
            # Limpiar respuesta (remover metadata técnica si existe)
            cleaned_response = last_response
            if '---' in cleaned_response:
                cleaned_response = cleaned_response.split('---')[0].strip()
            
            return JSONResponse(content={
                "text": cleaned_response,
                "response": cleaned_response,
                "error": False,
                "metadata": final_metadata,
                "session_id": session_id
            })
            
        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            print(f"⚠️ [ChatPDF Widget API] Error en widget_chat: {e}\n{error_trace}")
            return JSONResponse(content={
                "text": f"Error: {str(e)}",
                "error": True
            }, status_code=500)
    
    @app.post("/api/widget/upload")
    async def widget_upload(request: Request, files: List[UploadFile] = File(...)):
        """
        Endpoint para subir documentos.
        Usa process_documents de ChatPDF sin modificaciones.
        IMPORTANTE: Usa session_id="gradio_user" para compartir documentos con la UI de Gradio.
        """
        try:
            # Usar "gradio_user" por defecto para compartir documentos con ChatPDF UI
            session_id = request.headers.get("X-Session-ID", "gradio_user")
            
            # Convertir UploadFile a formato esperado por ChatPDF
            # ChatPDF espera objetos con atributo .name (como los objetos de Gradio)
            import tempfile
            import os
            from pathlib import Path
            
            file_list = []
            temp_files = []  # Para limpiar después
            
            try:
                for file in files:
                    content = await file.read()
                    
                    # Crear archivo temporal (como hace Gradio)
                    temp_dir = Path(tempfile.gettempdir())
                    temp_file = temp_dir / file.filename
                    
                    with open(temp_file, 'wb') as f:
                        f.write(content)
                    
                    temp_files.append(temp_file)
                    
                    # Crear objeto similar a Gradio File con atributo .name
                    class FileObj:
                        def __init__(self, path):
                            self.name = str(path)
                            self.path = path
                        
                        def read(self):
                            with open(self.path, 'rb') as f:
                                return f.read()
                    
                    file_list.append(FileObj(temp_file))
                
                # Llamar a process_documents de ChatPDF (lógica original)
                # Esta es la misma función que usa la UI de Gradio
                result = chatpdf_mode.process_documents(
                    session_id=session_id,
                    files=file_list
                )
                
                return JSONResponse(content=result)
                
            finally:
                # Limpiar archivos temporales
                for temp_file in temp_files:
                    try:
                        if temp_file.exists():
                            os.unlink(temp_file)
                    except:
                        pass
            
        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            print(f"⚠️ [ChatPDF Widget API] Error en widget_upload: {e}\n{error_trace}")
            return JSONResponse(content={
                "status": "error",
                "error": str(e)
            }, status_code=500)
    
    # Servir archivos estáticos (widget JS)
    try:
        static_dir = Path(__file__).parent / "static"
        static_dir.mkdir(exist_ok=True)
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
    except Exception as e:
        print(f"⚠️ Error montando static files: {e}")
    
    return app
