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



def _load_widget_links(config) -> Dict[str, Dict[str, str]]:
    """Carga links configurados desde archivo."""
    import json
    from pathlib import Path
    links_file = Path(config.memory_dir) / "widget_links.json"
    if links_file.exists():
        try:
            with open(links_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

def _insert_links_in_response(response: str, links: Dict[str, Dict[str, str]]) -> str:
    """Inserta links dinÃ¡micos en la respuesta segÃºn etiquetas de acciÃ³n."""
    import re
    # Buscar etiquetas de acciÃ³n en la respuesta (ej: [action_show_info])
    pattern = r'\[(action_\w+)\]'
    matches = re.findall(pattern, response)
    
    for action_tag in matches:
        # Buscar link con esta etiqueta
        for link_id, link_data in links.items():
            if link_data.get('action_tag') == action_tag:
                link_name = link_data.get('name', 'Ver mÃ¡s')
                link_url = link_data.get('url', '#')
                # Reemplazar etiqueta con link HTML
                link_html = f'<a href="{link_url}" target="_blank" style="color: #6366f1; text-decoration: underline;">{link_name}</a>'
                response = response.replace(f'[{action_tag}]', link_html)
                break
    
    return response

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

ðŸš« REGLA CRÃTICA DE USO DE DATOS (OBLIGATORIA)

Los PDFs cargados son la ÃšNICA fuente de verdad sobre:
- productos
- servicios
- precios
- mÃ­nimos
- materiales
- procesos
- tiempos
- condiciones comerciales

ðŸš« EstÃ¡ PROHIBIDO usar conocimiento general o inferencias externas
si el dato existe (o deberÃ­a existir) en el PDF.

FLUJO INTERNO OBLIGATORIO ANTES DE RESPONDER:

1. Identificar la intenciÃ³n del usuario
2. Buscar en los PDFs SOLO la informaciÃ³n relevante a esa intenciÃ³n
3. Extraer Ãºnicamente los fragmentos necesarios
4. Transformar esos datos en lenguaje comercial
5. Responder sin mencionar la fuente
6. Cerrar con acciÃ³n sugerida

REGLAS DE COMPORTAMIENTO

1. INFORMACIÃ“N PRECISA (CRÃTICO):
- SOLO responde con datos que estÃ©n EXPLÃCITAMENTE en el PDF
- Si el PDF contiene datos concretos relacionados con la pregunta, es OBLIGATORIO usarlos
- UsÃ¡ los PDFs como memoria interna del negocio
- Si un dato existe en el PDF, DEBES usarlo
- Si no hay informaciÃ³n en el PDF, dilo claramente: "No tengo esa informaciÃ³n en el catÃ¡logo"
- NUNCA inventes datos
- NUNCA uses conocimiento general si el dato deberÃ­a estar en el PDF

2. EXTRACCIÃ“N DE DATOS ESPECÃFICOS:
- Extrae nombres EXACTOS de productos del PDF (ej: "Vanth T-shirt", "Pampinea T-shirt")
- Extrae materiales EXACTOS (ej: "100% algodÃ³n", "viscosa y elastano")
- Extrae talles EXACTOS (ej: "XS a XXL", "S-XL")
- Extrae precios EXACTOS si estÃ¡n en el PDF
- Extrae mÃ­nimos de pedido EXACTOS si estÃ¡n en el PDF
- Extrae opciones de personalizaciÃ³n EXACTAS del PDF
- Extrae colores disponibles EXACTOS del PDF
- Menciona TODO tipo de datos que haya en el PDF relacionados con la pregunta

3. TONO PROFESIONAL Y PERSUASIVO:
- Claro, amigable, confiable y cercano
- Adaptado a emprendedores, compradores B2B y socios comerciales
- Lenguaje natural y humano
- Transforma datos tÃ©cnicos del PDF en lenguaje comercial

4. RESUMIR Y RESALTAR:
- Menciona TODO tipo de DATOS del producto en el PDF
- Incluye: caracterÃ­sticas, personalizaciÃ³n, colores, talles, materiales, precios, mÃ­nimos de pedido, disponibilidad, etc.
- Ejemplo de respuesta correcta: "El catÃ¡logo incluye camisetas como Vanth T-shirt y Pampinea T-shirt. Material: 100% algodÃ³n. PersonalizaciÃ³n: ImpresiÃ³n digital o 3D, etiquetas en el cuello, bordados. Tallas: XS a XXL."

5. CONTEXTO Y MEMORIA DE SESIÃ“N:
- Recuerda preguntas previas y preferencias del usuario
- No repitas informaciÃ³n innecesaria
- Construye sobre lo ya conversado

6. GUIAR AL USUARIO:
- Haz preguntas proactivas para avanzar:
  * Explorar categorÃ­as
  * Ver productos populares
  * Consultar precios o mÃ­nimos
  * Contactar a gerente/especialista

7. CROSS-SELL Y UPSELL:
- Sugiere productos relacionados si tienen sentido, siempre basado en el PDF
- Prioriza productos mÃ¡s vendidos o con mayor rentabilidad si aplica

8. ADAPTABLE A CUALQUIER CLIENTE:
- Cada negocio tiene su propio PDF/catÃ¡logo
- Lee y adapta automÃ¡ticamente la informaciÃ³n a ese PDF
- No asumas datos genÃ©ricos

9. CIERRE CON ACCIÃ“N SUGERIDA + LINKS DINÃMICOS:
- Cada respuesta debe terminar con un call to action
- Usa etiquetas de acciÃ³n para links dinÃ¡micos:
  * action_show_info â†’ "Â¿Quieres que te muestre las opciones mÃ¡s populares?"
  * action_contact_support â†’ "Â¿Deseas que te conecte con un especialista?"
  * action_compare_options â†’ "Â¿Quieres que comparemos estas opciones segÃºn tus necesidades?"
- El sistema insertarÃ¡ automÃ¡ticamente el link configurado para esa acciÃ³n
- Formato: Termina con pregunta/CTA y agrega [action_tag] al final

FORMATO DE RESPUESTA:
- Responde directamente la pregunta
- Menciona TODOS los datos relevantes del PDF con nombres EXACTOS (nombres de productos, materiales, talles, precios, etc.)
- Usa datos ESPECÃFICOS del PDF, no descripciones genÃ©ricas
- Termina con una pregunta o CTA con etiqueta de acciÃ³n
- Ejemplo: "El catÃ¡logo incluye camisetas Vanth T-shirt y Pampinea T-shirt en 100% algodÃ³n, talles XS-XXL, con personalizaciÃ³n digital o 3D. Â¿Quieres que te muestre mÃ¡s detalles? [action_show_info]"

PROHIBIDO ABSOLUTAMENTE:
- Mencionar "PDF", "documento", "pÃ¡gina", "anÃ¡lisis"
- Incluir metadata tÃ©cnica, verificaciones, fuentes
- Incluir informaciÃ³n del "Proceso Multi-Agente DocChat"
- Incluir secciones tÃ©cnicas
- Usar emojis tÃ©cnicos
- Inventar datos que no estÃ©n en el PDF
- Usar conocimiento general cuando el dato deberÃ­a estar en el PDF
- Hacer inferencias o asumir datos no presentes en el PDF

IMPORTANTE: 
- Los PDFs son tu ÃšNICA fuente de verdad
- Si un dato existe en el PDF, es OBLIGATORIO usarlo
- Si no existe en el PDF, di claramente que no tienes esa informaciÃ³n
- Responde SOLO con el contenido comercial, directo y natural, como si fueras un vendedor experto hablando con un cliente, pero usando SOLO datos reales del PDF."""

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
                
                # Cargar links configurados e insertarlos en la respuesta
                # Obtener config del wrapper
                try:
                    if hasattr(wrapper, "config") and wrapper.config:
                        widget_config = wrapper.config
                    elif hasattr(wrapper, "alien_mode") and hasattr(wrapper.alien_mode, "config") and wrapper.alien_mode.config:
                        widget_config = wrapper.alien_mode.config
                    else:
                        widget_config = None
                except:
                    widget_config = None
                
                widget_links = _load_widget_links(widget_config) if widget_config else {}
                if widget_links:
                    cleaned_response = _insert_links_in_response(cleaned_response, widget_links)
                
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
