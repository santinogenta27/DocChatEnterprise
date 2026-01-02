"""
Servidor API FastAPI para widget de Alien Mode.

Proporciona endpoints REST para que el widget se comunique con Alien Mode.
"""

from __future__ import annotations

import time
import uuid
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path

try:
    from fastapi import FastAPI, Request, Response, UploadFile, File
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import JSONResponse, HTMLResponse
    from fastapi.staticfiles import StaticFiles
    FASTAPI_AVAILABLE = True
except ImportError as e:
    FASTAPI_AVAILABLE = False
    import sys
    if "codec" not in str(e).lower():
        print(f"âš ï¸ FastAPI no disponible: {e}")
        print("Instala con: pip install fastapi uvicorn")
except Exception as e:
    FASTAPI_AVAILABLE = False
    if "codec" not in str(e).lower():
        print(f"âš ï¸ Error importando FastAPI: {e}")
    # Original: print("âš ï¸ FastAPI no disponible. Instala con: pip install fastapi uvicorn")

def create_api_server(wrapper) -> Optional[Any]:
    """
    Crea aplicaciÃ³n FastAPI para widget de Alien Mode.
    
    Args:
        wrapper: Instancia de AlienModeWidgetWrapper
        
    Returns:
        FastAPI app o None si FastAPI no estÃ¡ disponible
    """
    if not FASTAPI_AVAILABLE:
        return None
    
    app = FastAPI(
        title="Alien Mode Widget API",
        description="API para widget web de Alien Mode - Sistema Multi-Agente RAG"
    )
    
    # CORS para widget embebido
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # TODO: Configurar en producciÃ³n
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Servir archivos estÃ¡ticos
    static_dir = Path(__file__).parent.parent.parent / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
    else:
        # Crear directorio si no existe
        static_dir.mkdir(parents=True, exist_ok=True)
        # Crear widget JS bÃ¡sico
        _create_widget_js(static_dir)
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
    
    @app.get("/api/widget/health")
    async def health_check():
        """Health check endpoint."""
        return {
            "status": "healthy",
            "service": "alien_mode_widget",
            "alien_mode_available": wrapper.alien_mode is not None
        }
    
    @app.post("/api/widget/chat")
    async def widget_chat(request: Request, payload: Dict[str, Any]):
        """
        Endpoint REST de chat para widget web.
        
        Payload:
        {
            "session_id": "uuid",
            "user_id": "user_id",
            "message": "mensaje del usuario",
            "channel": "web"
        }
        
        Returns:
        {
            "text": "respuesta de Alien Mode",
            "error": false,
            "metadata": {...}
        }
        """
        start_time = time.time()

        message = payload.get("message", "")
        session_id = payload.get("session_id") or "gradio_user"  # Usar "gradio_user" por defecto para compartir documentos con Alien Mode UI
        user_id = payload.get("user_id", "anon")
        history = payload.get("history", [])
        if not message:
            return JSONResponse(
                status_code=400,
                content={
                    "error": True,
                    "text": "Por favor, envÃ­a un mensaje.",
                    "message": "Mensaje vacÃ­o"
                }
            )            # Procesar mensaje con Alien Mode usando el mismo proceso multi-agente que la UI
            # Convertir history al formato que espera Alien Mode
        alien_history = []
        if history:
            for h in history:
                if isinstance(h, dict):
                    alien_history.append((h.get("content", ""), ""))
                elif isinstance(h, (list, tuple)) and len(h) >= 2:
                    alien_history.append((str(h[0]), str(h[1]) if len(h) > 1 and h[1] else ""))
                else:
                    alien_history.append((str(h), ""))
            
            # Agregar prompt comercial al mensaje para el widget
            commercial_prompt = """CONTEXTO
Los PDFs cargados contienen informaciÃ³n interna del negocio
(productos, materiales, procesos, tiempos, opciones comerciales).
No son contenido para ser explicado al usuario.

ROL DEL AGENTE
ActuÃ¡s como un Sales + Customer Service AI en producciÃ³n,
orientado a conversiÃ³n y avance de conversaciÃ³n.

USO DE LOS PDFs (OBLIGATORIO)
- Nunca mencionar PDFs, documentos, pÃ¡ginas ni anÃ¡lisis.
- Nunca resumir documentos completos.
- Usar la informaciÃ³n solo para:
  â€¢ responder dudas concretas
  â€¢ recomendar productos
  â€¢ justificar beneficios
  â€¢ dar opciones comerciales claras

ESTILO DE RESPUESTA
- Lenguaje natural y humano
- Comercial, no acadÃ©mico
- Claro y conciso
- Sin tecnicismos internos
- Nunca responder como FAQ pasivo

LOOP OBLIGATORIO EN CADA RESPUESTA
1. Resolver la duda del usuario
2. Conectar la respuesta con valor del negocio
3. Avanzar la conversaciÃ³n con una pregunta o CTA suave

GESTIÃ“N DE INTENCIÃ“N
Antes de responder, determina internamente:
- IntenciÃ³n del usuario:
  â€¢ informativa
  â€¢ exploratoria
  â€¢ compra
- Nivel de decisiÃ³n:
  â€¢ curioso
  â€¢ evaluando
  â€¢ listo para comprar

Adapta el tono y el CTA segÃºn ese nivel.

SI EL USUARIO HACE UNA PREGUNTA ABIERTA
- Dar una visiÃ³n resumida del negocio
- Presentar 2â€“3 opciones claras
- Guiar con una pregunta de avance

PRINCIPIO CLAVE
UsÃ¡ los PDFs como si fueras un vendedor que ya se sabe todo de memoria.

OBJETIVO FINAL
Transformar conocimiento interno (PDFs) en conversaciones comerciales
que avancen hacia cotizaciÃ³n, selecciÃ³n de producto o contacto.

PROHIBIDO ABSOLUTAMENTE:
- Mencionar "PDF", "documento", "pÃ¡gina", "anÃ¡lisis", "proceder a analizar"
- Incluir metadata tÃ©cnica, verificaciones, fuentes
- Incluir informaciÃ³n del "Proceso Multi-Agente DocChat"
- Incluir secciones como "AnÃ¡lisis de Relevancia", "VerificaciÃ³n de Respuesta", "Fuentes Consultadas"
- Incluir emojis tÃ©cnicos (ðŸ”, ðŸ”¬, âœ…, etc.)
- Incluir separadores "---" o secciones tÃ©cnicas

IMPORTANTE: Responde SOLO con el contenido comercial, directo y natural, como si fueras un vendedor experto hablando con un cliente."""

            # Combinar prompt comercial con el mensaje del usuario
            try:

                enhanced_message = commercial_prompt + "\n\nUsuario pregunta: " + message
                # Llamar directamente a process_query_async de Alien Mode
                new_history, error, metadata = await wrapper.alien_mode.process_query_async(
                session_id=session_id,
                message=enhanced_message,
                history=alien_history,
                speed_mode="fast",  # Usar modo rÃ¡pido para widget
                provider="openai"
                )

                if error:
                    result = {"text": f"Error: {error}", "response": f"Error: {error}", "error": True, "metadata": metadata or {}}
                else:
                    last_response = new_history[-1][1] if new_history and len(new_history[-1]) > 1 else "No hay respuesta"
                # Filtrar metadata tÃ©cnica de la respuesta para el widget
                # Eliminar TODA la metadata del proceso multi-agente y menciones a documentos
                import re
                
                cleaned_response = last_response
                
                # Eliminar TODA la metadata del proceso multi-agente
                # Primero, eliminar todo despuÃ©s del primer "---"
                if '---' in cleaned_response:
                    cleaned_response = cleaned_response.split('---')[0].strip()
                
                # Eliminar secciones completas de metadata tÃ©cnica
                # Patrones para eliminar secciones completas
                section_patterns = [
                    r'(?i)proceso multi-agente docchat.*',
                    r'(?i)anÃ¡lisis de relevancia.*',
                    r'(?i)verificaciÃ³n.*',
                    r'(?i)fuentes consultadas.*',
                    r'(?i)capacidades avanzadas.*',
                    r'ðŸ”¬.*',
                    r'ðŸ“‹.*',
                    r'âœ….*',
                    r'ðŸ“š.*',
                    r'ðŸ§ .*',
                    r'ðŸ”.*procedencia.*',
                ]
                
                for pattern in section_patterns:
                    cleaned_response = re.sub(pattern, '', cleaned_response, flags=re.DOTALL)
                
                # Eliminar menciones especÃ­ficas a PDFs, documentos, pÃ¡ginas, anÃ¡lisis
                text_replacements = [
                    (r'\b(PDF|pdf|documento|documentos)\b', ''),
                    (r'\b(pÃ¡gina|pÃ¡ginas|page|pages)\s+\d+', ''),
                    (r'\b(proceder a analizar|analizar el|anÃ¡lisis del|anÃ¡lisis de)\b', ''),
                    (r'\b(segÃºn el documento|en el documento|del documento|el documento)\b', ''),
                    (r'\b(este documento|este PDF|el PDF|los documentos)\b', ''),
                    (r'\(.*?Clothing-Catalogue\.pdf.*?\)', ''),
                    (r'\(.*?\.pdf.*?\)', ''),
                ]
                
                for pattern, replacement in text_replacements:
                    cleaned_response = re.sub(pattern, replacement, cleaned_response, flags=re.IGNORECASE)
                
                # Limpiar lÃ­neas vacÃ­as mÃºltiples y espacios extra
                cleaned_response = re.sub(r'\n{3,}', '\n\n', cleaned_response)
                cleaned_response = re.sub(r' +', ' ', cleaned_response)
                cleaned_response = cleaned_response.strip()
                
                # Si despuÃ©s de limpiar queda muy corto, extraer solo el contenido principal
                if not cleaned_response or len(cleaned_response) < 20:
                    # Extraer solo el contenido antes del primer "---" o "Proceso Multi-Agente"
                    main_content = last_response.split('---')[0] if '---' in last_response else last_response
                    if 'Proceso Multi-Agente' in main_content:
                        main_content = main_content.split('Proceso Multi-Agente')[0]
                    # Limpiar menciones bÃ¡sicas
                    main_content = re.sub(r'\b(PDF|pdf|documento|documentos|pÃ¡gina|pÃ¡ginas)\b', '', main_content, flags=re.IGNORECASE)
                    main_content = re.sub(r'\b(proceder a analizar|analizar el|anÃ¡lisis)\b', '', main_content, flags=re.IGNORECASE)
                    cleaned_response = main_content.strip()
                
                # Asegurar que la respuesta no estÃ© vacÃ­a
                if not cleaned_response:
                    cleaned_response = last_response.split('---')[0].strip() if '---' in last_response else last_response.strip()

                
                
                result = {"text": cleaned_response, "response": cleaned_response, "error": False, "metadata": metadata or {}, "history": new_history}
                # Calcular tiempo de respuesta
                response_time = time.time() - start_time
                
                # Agregar metadata
                result["response_time"] = response_time
                result["session_id"] = session_id
                
                return JSONResponse(content=result)

            except Exception as e:
                import traceback
                error_msg = str(e)
                print(f"[Widget API] Error procesando mensaje: {error_msg}")
                traceback.print_exc()
                return JSONResponse(
                    status_code=500,
                    content={
                        "error": True,
                        "text": f"Error procesando mensaje: {error_msg}",
                        "response": f"Error procesando mensaje: {error_msg}",
                        "message": error_msg
                }
            )

    return app
