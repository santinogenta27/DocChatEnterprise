"""
Alien Mode Widget Wrapper - Envuelve Alien Mode con funcionalidades de widget.

NO modifica el core de Alien Mode, solo lo envuelve con:
- API Server (FastAPI)
- Widget Generator (código HTML)
- UI de Configuración (Gradio)
- Instrucciones
"""

from __future__ import annotations

import os
import uuid
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path

from ..config import AppConfig, load_config
from ..document_processor import DocumentProcessor
from ..retriever_builder import RetrieverBuilder
from ..alien_mode import AlienMode, get_alien_mode


class AlienModeWidgetWrapper:
    """
    Wrapper para Alien Mode que agrega funcionalidades de widget sin modificar el core.
    
    Proporciona:
    - API Server (FastAPI) para widget web
    - Widget Generator (genera código HTML para embed)
    - UI de Configuración (Gradio)
    - Instrucciones
    """
    
    def __init__(
        self,
        config: Optional[AppConfig] = None,
        processor: Optional[DocumentProcessor] = None,
        retriever_builder: Optional[RetrieverBuilder] = None,
        alien_mode: Optional[AlienMode] = None
    ):
        """
        Inicializa el wrapper.
        
        Args:
            config: Configuración de la aplicación
            processor: Procesador de documentos (se crea si no se proporciona)
            retriever_builder: Constructor de retriever (se crea si no se proporciona)
            alien_mode: Instancia de Alien Mode (se crea si no se proporciona)
        """
        # Cargar configuración
        self.config = config or load_config()
        
        # Crear componentes si no se proporcionan
        if processor is None:
            self.processor = DocumentProcessor(self.config)
        else:
            self.processor = processor
        
        if retriever_builder is None:
            self.retriever_builder = RetrieverBuilder(self.config)
        else:
            self.retriever_builder = retriever_builder
        
        # Usar Alien Mode existente o crear uno nuevo
        if alien_mode is None:
            self.alien_mode = get_alien_mode(
                config=self.config,
                processor=self.processor,
                retriever_builder=self.retriever_builder
            )
        else:
            self.alien_mode = alien_mode
        
        # Estado de API server
        self.api_server: Optional[Any] = None
        self.api_server_port = int(os.getenv("ALIEN_WIDGET_API_PORT", "7865"))
    
    def get_gradio_interface(self):
        """
        Retorna interfaz de Gradio para Alien Mode Widget.
        
        Incluye:
        - Chat con Alien Mode
        - Panel de configuración
        - Generar Código (widget embeddable)
        - Servidor API
        - Instrucciones
        """
        try:
            import gradio as gr
        except ImportError as e:
            raise ImportError("Gradio no está instalado. Añade gradio al entorno para usar esta función.") from e
        
        # Crear interfaz principal con tabs
        with gr.Blocks(
            theme=gr.themes.Soft(),
            title="👽 Alien Mode Widget - Asistente Virtual RAG",
            css="""
            .gradio-container {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            }
            """
        ) as demo:
            gr.Markdown("""
            # 👽 Alien Mode Widget - Asistente Virtual RAG
            
            Sistema Multi-Agente RAG de Máxima Calidad. Integra en tu website con el widget embeddable.
            """)
            
            with gr.Tabs() as main_tabs:
                # TAB 1: Chat con Alien Mode
                with gr.Tab("💬 Chat"):
                    gr.Markdown("### Prueba tu Alien Mode")
                    
                    chatbot = gr.Chatbot(
                        label="Conversación",
                        height=500,
                        show_copy_button=True
                    )
                    
                    with gr.Row():
                        msg = gr.Textbox(
                            label="Mensaje",
                            placeholder="Escribe tu pregunta aquí...",
                            scale=4
                        )
                        submit_btn = gr.Button("Enviar", variant="primary", scale=1)
                    
                    file_upload = gr.File(
                        label="📄 Subir Documentos (PDF, DOCX, TXT, MD)",
                        file_count="multiple",
                        file_types=[".pdf", ".docx", ".txt", ".md"]
                    )
                    
                    with gr.Accordion("⚙️ Opciones Avanzadas", open=False):
                        speed_mode = gr.Radio(
                            label="Modo de Velocidad",
                            choices=[
                                ("⚡ Rápido", "fast"),
                                ("⚖️ Balanceado", "balanced"),
                                ("🎯 Preciso", "accurate")
                            ],
                            value="balanced"
                        )
                        provider = gr.Radio(
                            label="Provider LLM",
                            choices=[
                                ("OpenAI", "openai"),
                                ("Anthropic (Claude)", "anthropic")
                            ],
                            value="openai"
                        )
                    
                    session_id_state = gr.State(value=str(uuid.uuid4()))
                    
                    def chat_fn(message, history, files, session_id, speed, provider_selected):
                        """Función de chat con Alien Mode."""
                        if not message:
                            return history, session_id
                        
                        # Procesar documentos si hay
                        if files:
                            try:
                                result = self.alien_mode.process_documents(session_id, files)
                                if result.get("status") == "error":
                                    history.append([None, f"❌ Error procesando documentos: {result.get('error')}"])
                                    return history, session_id
                            except Exception as e:
                                history.append([None, f"❌ Error: {str(e)}"])
                                return history, session_id
                        
                        # Agregar mensaje del usuario
                        history.append([message, None])
                        
                        # Procesar query con Alien Mode
                        try:
                            import asyncio
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                            
                            new_history, error, metadata = loop.run_until_complete(
                                self.alien_mode.process_query_async(
                                    session_id=session_id,
                                    message=message,
                                    history=[(h[0], h[1]) for h in history[:-1] if h[1]],
                                    speed_mode=speed,
                                    provider=provider_selected
                                )
                            )
                            loop.close()
                            
                            # Actualizar historia
                            if error:
                                history[-1][1] = f"❌ Error: {error}"
                            else:
                                history = new_history
                            
                            return history, session_id
                        except Exception as e:
                            history[-1][1] = f"❌ Error procesando mensaje: {str(e)}"
                            return history, session_id
                    
                    submit_btn.click(
                        chat_fn,
                        inputs=[msg, chatbot, file_upload, session_id_state, speed_mode, provider],
                        outputs=[chatbot, session_id_state]
                    )
                    msg.submit(
                        chat_fn,
                        inputs=[msg, chatbot, file_upload, session_id_state, speed_mode, provider],
                        outputs=[chatbot, session_id_state]
                    )
                
                # TAB 2: Generar Código
                with gr.Tab("🔧 Generar Código"):
                    # Importar UI de configuración
                    try:
                        from .ui.widget_code_generator import WidgetCodeGenerator
                        code_generator = WidgetCodeGenerator(self)
                        code_generator.create_ui()
                    except Exception as e:
                        gr.Markdown(f"⚠️ Error cargando generador de código: {e}")
                
                # TAB 3: Configuración Enterprise
                with gr.Tab("⚙️ Configuración Enterprise"):
                    # Importar UI de configuración
                    try:
                        from .ui.config_ui import AlienModeConfigUI
                        config_ui = AlienModeConfigUI(self)
                        config_ui.create_ui()
                    except Exception as e:
                        gr.Markdown(f"⚠️ Error cargando UI de configuración: {e}")
                        import traceback
                        gr.Markdown(f"```\n{traceback.format_exc()}\n```")
                
                # TAB 4: Servidor API
                with gr.Tab("🚀 Servidor API"):
                    # Importar UI del servidor API
                    try:
                        from .ui.api_server_ui import APIServerUI
                        api_ui = APIServerUI(self)
                        api_ui.create_ui()
                    except Exception as e:
                        gr.Markdown(f"⚠️ Error cargando UI del servidor API: {e}")
                        import traceback
                        gr.Markdown(f"```\n{traceback.format_exc()}\n```")
                
                # TAB 5: Instrucciones
                with gr.Tab("📖 Instrucciones"):
                    try:
                        from .ui.instructions_ui import InstructionsUI
                        instructions_ui = InstructionsUI()
                        instructions_ui.create_ui()
                    except Exception as e:
                        gr.Markdown(f"⚠️ Error cargando instrucciones: {e}")
                        import traceback
                        gr.Markdown(f"```\n{traceback.format_exc()}\n```")
            
            return demo
    
    def get_api_server(self):
        """
        Retorna el servidor API FastAPI para el widget.
        
        Returns:
            Instancia de FastAPI configurada
        """
        if self.api_server is None:
            # Verificar FastAPI directamente antes de importar
            fastapi_available = False
            try:
                from fastapi import FastAPI
                fastapi_available = True
            except ImportError as e:
                print(f"[Alien Mode Widget] Error importando FastAPI: {e}")
                fastapi_available = False
            except Exception as e:
                # Capturar otros errores (encoding, etc.)
                print(f"[Alien Mode Widget] Error inesperado importando FastAPI: {e}")
                fastapi_available = False
            
            if not fastapi_available:
                print("[Alien Mode Widget] FastAPI no estÃ¡ disponible")
                return None
            
            try:
                from .widget.api_server import create_api_server
                self.api_server = create_api_server(self)
                if self.api_server is None:
                    print("[Alien Mode Widget] create_api_server retornÃ³ None")
            except Exception as e:
                print(f"[Alien Mode Widget] Error creando servidor API: {e}")
                import traceback
                traceback.print_exc()
                return None
        return self.api_server
    
    def start_api_server(self, port: Optional[int] = None, host: str = "0.0.0.0"):
        """
        Inicia el servidor API en un puerto específico.
        
        Args:
            port: Puerto donde correr el servidor (default: 7865)
            host: Host donde correr (default: 0.0.0.0)
        """
        if port is None:
            port = self.api_server_port
        
        try:
            import uvicorn
        except ImportError:
            raise ImportError("uvicorn no está instalado. Instala con: pip install uvicorn")
        
        api_app = self.get_api_server()
        if api_app is None:
            raise RuntimeError(
                "FastAPI no estÃ¡ disponible. El servidor API no se puede iniciar.\n"
                "Instala FastAPI con: pip install fastapi uvicorn"
            )
        
        
        print(f"🚀 Iniciando Alien Mode Widget API Server en http://{host}:{port}")
        uvicorn.run(api_app, host=host, port=port)
    
    def process_message(self, message: str, session_id: str, history: Optional[List[Tuple[str, str]]] = None) -> Dict[str, Any]:
        """
        Procesa un mensaje usando Alien Mode (para API).
        
        Args:
            message: Mensaje del usuario
            session_id: ID de sesión
            history: Historial de conversación (opcional)
            
        Returns:
            Dict con respuesta y metadata
        """
        try:
            import asyncio
            
            # Si hay un loop corriendo, usarlo; si no, crear uno nuevo
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            # Ejecutar query async
            new_history, error, metadata = loop.run_until_complete(
                self.alien_mode.process_query_async(
                    session_id=session_id,
                    message=message,
                    history=history or [],
                    speed_mode="balanced",
                    provider="openai"
                )
            )
            
            if error:
                return {
                    "text": f"Error: {error}",
                    "error": True,
                    "metadata": metadata
                }
            
            # Obtener última respuesta
            last_response = new_history[-1][1] if new_history else "No hay respuesta"
            
            return {
                "text": last_response,
                "error": False,
                "metadata": metadata,
                "history": new_history
            }
        except Exception as e:
            return {
                "text": f"Error procesando mensaje: {str(e)}",
                "error": True,
                "metadata": {}
            }

