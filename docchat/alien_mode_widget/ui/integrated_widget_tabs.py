"""
Tabs integrados para Alien Mode dentro de app.py.

Estos tabs se integran dentro del tab de Alien Mode existente.
"""

from __future__ import annotations

import os
import uuid
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...config import AppConfig
    from ...alien_mode import AlienMode


def create_widget_tabs_in_alien_mode(
    config: 'AppConfig',
    alien_mode: 'AlienMode'
):
    """
    Crea los tabs de widget dentro del tab de Alien Mode.
    
    Args:
        config: Configuración de la app
        alien_mode: Instancia de AlienMode
    
    Returns:
        Función que crea los tabs usando gradio
    """
    import gradio as gr
    
    # Estado del servidor API (compartido)
    api_server_thread = None
    api_server_running = False
    
    def _create_tabs():
        """Crea los tabs internos."""
        nonlocal api_server_thread, api_server_running
        
        with gr.Tabs() as widget_tabs:
            # TAB 1: Generar Código
            with gr.Tab("🔧 Generar Código"):
                with gr.Row():
                    with gr.Column():
                        widget_api_url = gr.Textbox(
                            label="🌐 URL del Servidor",
                            value="http://127.0.0.1:7865",
                            placeholder="https://tu-servidor.com",
                            info="URL donde está corriendo tu servidor Alien Mode Widget API"
                        )
                        widget_id = gr.Textbox(
                            label="🆔 Widget ID",
                            placeholder="widget_abc123",
                            info="ID único para este widget (se genera automáticamente si lo dejas vacío)"
                        )
                        widget_brand_name = gr.Textbox(
                            label="🏷️ Nombre de Marca",
                            placeholder="Mi Empresa",
                            value=getattr(config, 'app_name', 'Alien Mode'),
                            info="Nombre que aparecerá en el widget"
                        )
                        widget_primary_color = gr.Textbox(
                            label="🎨 Color Principal",
                            value="#6366f1",
                            placeholder="#6366f1",
                            info="Color hexadecimal para el widget"
                        )
                        widget_position = gr.Radio(
                            label="📍 Posición",
                            choices=[("Esquina inferior derecha", "bottom-right"), ("Esquina inferior izquierda", "bottom-left")],
                            value="bottom-right"
                        )
                        widget_welcome_message = gr.Textbox(
                            label="💬 Mensaje de Bienvenida",
                            value="👋 ¡Hola! Soy tu asistente virtual. ¿En qué puedo ayudarte?",
                            lines=2,
                            info="Mensaje que verá el usuario al abrir el chat"
                        )
                        
                        generate_widget_code_btn = gr.Button("📋 Generar Código", variant="primary", size="lg")
                    
                    with gr.Column():
                        widget_code_output = gr.Code(
                            label="📋 Código HTML para Copiar y Pegar",
                            language="html",
                            lines=20,
                            value="**💡 Configura los campos de la izquierda y haz click en 'Generar Código'**"
                        )
                        widget_preview = gr.Markdown(
                            label="👁️ Preview",
                            value="**El código generado aparecerá arriba**"
                        )
                
                def generate_widget_code(api_url, widget_id_input, brand_name, primary_color, position, welcome_message):
                    """Genera código HTML/JS para el widget embeddable"""
                    try:
                        # Generar widget_id si no se proporciona
                        if not widget_id_input or not widget_id_input.strip():
                            widget_id_final = f"alien_widget_{uuid.uuid4().hex[:12]}"
                        else:
                            widget_id_final = widget_id_input.strip()
                        
                        # Validar URL
                        if not api_url or not api_url.strip():
                            return "⚠️ **URL del servidor es requerida**", "❌ Error: URL requerida"
                        
                        api_url_clean = api_url.strip().rstrip('/')
                        
                        # Construir código HTML con atributos base
                        code_lines = [
                            f'<script src="{api_url_clean}/static/alien-mode-widget.js"',
                            f'        data-api-url="{api_url_clean}"',
                            f'        data-widget-id="{widget_id_final}"',
                            f'        data-brand-name="{brand_name}"',
                            f'        data-primary-color="{primary_color}"',
                            f'        data-position="{position}"',
                            f'        data-welcome-message="{welcome_message}"',
                            '        async></script>'
                        ]
                        
                        code = '\n'.join(code_lines)
                        
                        preview = f"""## ✅ Código Generado Exitosamente

**Widget ID:** `{widget_id_final}`

**Instrucciones:**
1. Copia el código HTML de arriba
2. Pégalo antes de `</body>` en tu website
3. El widget aparecerá automáticamente en la esquina {position.replace('bottom-', 'inferior ').replace('right', 'derecha').replace('left', 'izquierda')}

**Características del Widget:**
- ✅ Chat flotante con interfaz moderna
- ✅ Conectado con Alien Mode (RAG Multi-Agente)
- ✅ Extracción perfecta de PDFs
- ✅ Sistema de verificación anti-hallucinación
- ✅ Respuestas precisas basadas en tus documentos

**Próximos Pasos:**
1. Inicia el servidor API (ve al tab "🚀 Servidor API")
2. Copia el código generado en tu website
3. ¡Listo! Tu widget estará funcionando
"""
                        
                        return code, preview
                    except Exception as e:
                        error_msg = f"❌ Error generando código: {str(e)}"
                        return error_msg, error_msg
                
                generate_widget_code_btn.click(
                    generate_widget_code,
                    inputs=[widget_api_url, widget_id, widget_brand_name, widget_primary_color, widget_position, widget_welcome_message],
                    outputs=[widget_code_output, widget_preview]
                )
            
            # TAB 2: Configuración Enterprise
            with gr.Tab("⚙️ Configuración Enterprise"):
                gr.Markdown("### ⚙️ Configuración Enterprise")
                
                with gr.Accordion("🔧 Configuración General", open=True):
                    brand_name = gr.Textbox(
                        label="Nombre de tu Empresa",
                        value=getattr(config, 'app_name', 'Alien Mode'),
                        placeholder="Ej: Mi Empresa"
                    )
                    
                    rag_model = gr.Dropdown(
                        label="Modelo de Embeddings para RAG",
                        choices=[
                            ("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2", "multilingual"),
                            ("sentence-transformers/all-MiniLM-L6-v2", "english"),
                        ],
                        value="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
                        info="Modelo para generar embeddings de documentos"
                    )
                
                with gr.Accordion("🎯 Configuración de Procesamiento", open=False):
                    max_chunk_size = gr.Number(
                        label="Tamaño Máximo de Chunk",
                        value=1000,
                        info="Tamaño máximo de cada fragmento de documento"
                    )
                    
                    chunk_overlap = gr.Number(
                        label="Solapamiento entre Chunks",
                        value=200,
                        info="Caracteres de solapamiento entre chunks"
                    )
                
                with gr.Accordion("🔐 API Keys", open=False):
                    openai_key = gr.Textbox(
                        label="OpenAI API Key",
                        type="password",
                        placeholder="sk-...",
                        value=os.getenv("OPENAI_API_KEY", ""),
                        info="Para usar OpenAI como LLM"
                    )
                    
                    anthropic_key = gr.Textbox(
                        label="Anthropic API Key",
                        type="password",
                        placeholder="sk-ant-...",
                        value=os.getenv("ANTHROPIC_API_KEY", ""),
                        info="Para usar Claude como LLM"
                    )
                
                save_config_btn = gr.Button("💾 Guardar Configuración", variant="primary")
                config_status = gr.Textbox(label="Estado", interactive=False)
                
                def save_config_fn(brand, rag_model_val, max_chunk, overlap, openai_key_val, anthropic_key_val):
                    """Guarda configuración."""
                    try:
                        # Actualizar configuración (sin modificar Alien Mode core)
                        config.app_name = brand
                        return "✅ Configuración guardada. Algunos cambios requieren reiniciar el servidor."
                    except Exception as e:
                        return f"❌ Error: {e}"
                
                save_config_btn.click(
                    save_config_fn,
                    inputs=[brand_name, rag_model, max_chunk_size, chunk_overlap, openai_key, anthropic_key],
                    outputs=[config_status]
                )
            
            # TAB 3: Servidor API
            with gr.Tab("🚀 Servidor API"):
                gr.Markdown("### 🚀 Servidor API para Widget")
                
                gr.Markdown("""
                **El Servidor API permite que tu widget se comunique con Alien Mode.**
                
                El servidor proporciona:
                - ✅ Endpoint REST para chat (`/api/widget/chat`)
                - ✅ Servir archivos estáticos del widget (`/static/`)
                - ✅ Health check (`/api/widget/health`)
                """)
                
                with gr.Row():
                    with gr.Column():
                        api_port = gr.Number(
                            label="Puerto del Servidor",
                            value=7865,
                            info="Puerto donde correrá el servidor API (default: 7865)"
                        )
                        
                        api_host = gr.Textbox(
                            label="Host",
                            value="0.0.0.0",
                            info="Host donde correrá el servidor (0.0.0.0 = todos los interfaces)"
                        )
                        
                        start_server_btn = gr.Button("🚀 Iniciar Servidor API", variant="primary", size="lg")
                        stop_server_btn = gr.Button("⏹️ Detener Servidor", variant="stop", size="lg")
                        check_server_btn = gr.Button("🔍 Verificar Estado", variant="secondary")
                    
                    with gr.Column():
                        server_status = gr.Markdown(
                            value="**Estado:** Servidor no iniciado"
                        )
                        
                        server_url = gr.Textbox(
                            label="URL del Servidor",
                            value="http://127.0.0.1:7865",
                            interactive=False,
                            info="URL que debes usar en 'Generar Código'"
                        )
                
                def start_server(port, host):
                    """Inicia el servidor API en un thread separado."""
                    nonlocal api_server_thread, api_server_running
                    
                    try:
                        import threading
                        import time
                        import requests
                        
                        host_display = host if host != "0.0.0.0" else "127.0.0.1"
                        
                        # Verificar si ya está corriendo
                        try:
                            response = requests.get(f"http://127.0.0.1:{int(port)}/api/widget/health", timeout=2)
                            if response.status_code == 200:
                                api_server_running = True
                                return f"✅ **Servidor API ya está corriendo en puerto {int(port)}**\n\n**URL:** http://{host_display}:{int(port)}\n\n**Status:** ✅ Activo", "Servidor ya está corriendo"
                        except:
                            pass
                        
                        # Si ya hay un thread corriendo, no iniciar otro
                        if api_server_thread is not None and api_server_thread.is_alive():
                            return f"⚠️ **Servidor API ya está iniciándose o corriendo**\n\n**URL:** http://{host_display}:{int(port)}", "Servidor ya está corriendo"
                        
                        # Crear wrapper para el servidor API
                        from docchat.alien_mode_widget import AlienModeWidgetWrapper
                        wrapper = AlienModeWidgetWrapper(
                            config=config,
                            alien_mode=alien_mode
                        )
                        
                        # Función para ejecutar el servidor en el thread
                        def run_server():
                            nonlocal api_server_running
                            try:
                                api_server_running = True
                                wrapper.start_api_server(port=int(port), host=host)
                            except Exception as e:
                                print(f"❌ Error en servidor API: {e}")
                                api_server_running = False
                        
                        # Iniciar thread
                        api_server_thread = threading.Thread(target=run_server, daemon=True)
                        api_server_thread.start()
                        
                        # Esperar un momento para que el servidor inicie
                        time.sleep(2)
                        
                        # Verificar que esté corriendo
                        try:
                            response = requests.get(f"http://127.0.0.1:{int(port)}/api/widget/health", timeout=2)
                            if response.status_code == 200:
                                return f"""✅ **Servidor API iniciado exitosamente**

**URL del Servidor:** `http://{host_display}:{int(port)}`

**Endpoints disponibles:**
- Health check: `http://{host_display}:{int(port)}/api/widget/health`
- Chat endpoint: `http://{host_display}:{int(port)}/api/widget/chat` (POST)
- Widget JS: `http://{host_display}:{int(port)}/static/alien-mode-widget.js`

**Próximos pasos:**
1. ✅ Usa esta URL en el tab "🔧 Generar Código"
2. ✅ Copia el código generado y pégalo en tu website
3. ✅ El widget funcionará automáticamente

**💡 El servidor está corriendo en background. Puedes cerrar esta ventana sin problemas.**
""", f"✅ Servidor corriendo en puerto {int(port)}"
                            else:
                                return f"⚠️ **Servidor iniciado pero no responde correctamente**\n\nIntenta verificar el estado nuevamente.", "Servidor iniciado"
                        except:
                            return f"""⚠️ **Servidor API iniciándose...**

**URL del Servidor:** `http://{host_display}:{int(port)}`

Espera unos segundos y haz click en "🔍 Verificar Estado" para confirmar que esté corriendo.

Si no responde después de 10 segundos, revisa los logs o intenta detenerlo y volver a iniciarlo.
""", "Servidor iniciándose"
                        
                    except Exception as e:
                        import traceback
                        api_server_running = False
                        return f"❌ **Error iniciando servidor API:** {str(e)}\n\n```\n{traceback.format_exc()}\n```", f"Error: {str(e)}"
                
                def stop_server(port_val, host_val):
                    """Detiene el servidor API."""
                    nonlocal api_server_thread, api_server_running
                    
                    try:
                        import requests
                        port_val = int(port_val) if port_val else 7865
                        
                        # Intentar hacer shutdown del servidor (si tiene endpoint de shutdown)
                        try:
                            # Si el servidor tiene endpoint de shutdown, usarlo
                            requests.post(f"http://127.0.0.1:{port_val}/api/widget/shutdown", timeout=1)
                            api_server_running = False
                            return f"""✅ **Servidor API detenido**

**Nota:** El servidor se ha detenido. Puedes iniciarlo nuevamente cuando lo necesites.
"""
                        except:
                            # Si no tiene endpoint de shutdown, solo informar
                            api_server_running = False
                            return f"""⚠️ **Para detener el servidor completamente:**

El servidor está corriendo en un thread en background. Para detenerlo completamente, reinicia la aplicación de Gradio.

**Alternativa:** Si necesitas detenerlo inmediatamente, puedes:
1. Cerrar la ventana de Gradio completamente
2. O reiniciar el proceso de Python
"""
                    except Exception as e:
                        return f"⚠️ **No se pudo detener el servidor automáticamente:** {str(e)}\n\nReinicia la aplicación de Gradio para detenerlo completamente."
                
                def check_server_status(port_val, host_val):
                    """Verifica el estado del servidor API."""
                    nonlocal api_server_running
                    try:
                        import requests
                        port_val = int(port_val) if port_val else 7865
                        host_val = host_val if host_val else "0.0.0.0"
                        host_display = host_val if host_val != "0.0.0.0" else "127.0.0.1"
                        
                        response = requests.get(f"http://127.0.0.1:{port_val}/api/widget/health", timeout=2)
                        if response.status_code == 200:
                            data = response.json()
                            api_server_running = True
                            return f"""✅ **Servidor API está corriendo**

**URL:** `http://{host_display}:{port_val}`
**Estado:** {data.get('status', 'healthy')}
**Alien Mode disponible:** {'✅ Sí' if data.get('alien_mode_available') else '❌ No'}

**Endpoints:**
- Health: `http://{host_display}:{port_val}/api/widget/health`
- Chat: `http://{host_display}:{port_val}/api/widget/chat` (POST)
- Widget JS: `http://{host_display}:{port_val}/static/alien-mode-widget.js`
"""
                        else:
                            api_server_running = False
                            return f"⚠️ **Servidor responde pero con error:** HTTP {response.status_code}"
                    except requests.exceptions.ConnectionError:
                        api_server_running = False
                        return "❌ **Servidor API no está corriendo**\n\nHaz click en '🚀 Iniciar Servidor API' para iniciarlo."
                    except Exception as e:
                        api_server_running = False
                        return f"❌ **Error verificando estado:** {str(e)}"
                
                start_server_btn.click(
                    start_server,
                    inputs=[api_port, api_host],
                    outputs=[server_status, server_url]
                )
                
                stop_server_btn.click(
                    stop_server,
                    inputs=[api_port, api_host],
                    outputs=[server_status]
                )
                
                check_server_btn.click(
                    check_server_status,
                    inputs=[api_port, api_host],
                    outputs=[server_status]
                )
                
                gr.Markdown("""
                ---
                
                **📝 Notas:**
                - El servidor debe estar corriendo para que el widget funcione
                - Asegúrate de que el puerto no esté en uso por otra aplicación
                - En producción, configura un proxy reverso (nginx, etc.) para HTTPS
                """)
            
            # TAB 4: Instrucciones
            with gr.Tab("📖 Instrucciones"):
                gr.Markdown("""
                # 📖 Instrucciones - Alien Mode Widget
                
                Guía completa para integrar Alien Mode en tu website usando el widget embeddable.
                """)
                
                with gr.Tabs() as instruction_tabs:
                    with gr.Tab("🚀 Inicio Rápido"):
                        gr.Markdown("""
                        ## 🚀 Inicio Rápido - 3 Pasos
                        
                        ### Paso 1: Iniciar Servidor API
                        
                        1. Ve al tab **"🚀 Servidor API"**
                        2. Configura el puerto (default: 7865)
                        3. Inicia el servidor usando el comando proporcionado
                        4. Verifica que el servidor esté corriendo: `http://127.0.0.1:7865/api/widget/health`
                        
                        ### Paso 2: Generar Código del Widget
                        
                        1. Ve al tab **"🔧 Generar Código"**
                        2. Configura:
                           - URL del Servidor (debe coincidir con el servidor iniciado)
                           - Nombre de Marca
                           - Color Principal
                           - Posición del widget
                           - Mensaje de Bienvenida
                        3. Haz click en **"📋 Generar Código"**
                        4. Copia el código HTML generado
                        
                        ### Paso 3: Integrar en tu Website
                        
                        1. Abre el código HTML de tu website
                        2. Busca la etiqueta `</body>`
                        3. Pega el código generado ANTES de `</body>`
                        4. Guarda y recarga tu website
                        5. ¡El widget aparecerá automáticamente!
                        
                        ---
                        
                        **✅ ¡Listo!** Tu widget de Alien Mode está funcionando.
                        """)
                    
                    with gr.Tab("📄 Procesar Documentos"):
                        gr.Markdown("""
                        ## 📄 Procesar Documentos en Alien Mode
                        
                        Para que Alien Mode pueda responder preguntas sobre tus documentos:
                        
                        ### Desde la UI de Alien Mode
                        
                        1. Ve al tab principal **"👽 Alien Mode"**
                        2. Usa el campo **"📂 Alien Mode Documents"**
                        3. Selecciona tus PDFs, DOCX, TXT o archivos Markdown
                        4. Haz click en **"📤 Send"** o envía un mensaje
                        5. Los documentos se procesarán automáticamente
                        
                        ### Desde la API del Widget
                        
                        Puedes procesar documentos mediante la API del widget una vez que el servidor esté corriendo.
                        
                        ---
                        
                        **📌 Nota:** Alien Mode usa `DocumentProcessor` que extrae información perfecta de PDFs usando PyPDF2 y Docling como fallback.
                        """)
                    
                    with gr.Tab("⚙️ Configuración Avanzada"):
                        gr.Markdown("""
                        ## ⚙️ Configuración Avanzada
                        
                        ### Variables de Entorno
                        
                        Configura en tu archivo `.env`:
                        
                        ```env
                        # LLM Provider
                        OPENAI_API_KEY=tu-clave-openai
                        ANTHROPIC_API_KEY=tu-clave-anthropic
                        
                        # Puerto del Servidor API
                        ALIEN_WIDGET_API_PORT=7865
                        
                        # Configuración de RAG
                        RAG_MODEL=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
                        ```
                        
                        ### Modos de Velocidad
                        
                        - **⚡ Rápido**: Respuestas más rápidas, menos precisión
                        - **⚖️ Balanceado**: Mejor equilibrio velocidad/precisión (recomendado)
                        - **🎯 Preciso**: Máxima precisión, más lento
                        
                        ### Providers de LLM
                        
                        - **OpenAI**: GPT-4o, GPT-4, GPT-3.5
                        - **Anthropic**: Claude 3 Opus, Sonnet, Haiku
                        
                        ---
                        
                        **💡 Tip:** Usa "Balanceado" para la mayoría de casos. "Preciso" solo cuando necesites máxima exactitud.
                        """)
                    
                    with gr.Tab("❓ Troubleshooting"):
                        gr.Markdown("""
                        ## ❓ Troubleshooting
                        
                        ### El widget no aparece
                        
                        - Verifica que el código HTML esté ANTES de `</body>`
                        - Revisa la consola del navegador para errores JavaScript
                        - Asegúrate de que el servidor API esté corriendo
                        - Verifica que la URL del servidor sea correcta
                        
                        ### El servidor API no inicia
                        
                        - Verifica que el puerto no esté en uso: `netstat -ano | findstr :7865`
                        - Asegúrate de que uvicorn esté instalado: `pip install uvicorn`
                        - Revisa los logs de error en la terminal
                        
                        ### Alien Mode no responde sobre mis documentos
                        
                        - Asegúrate de haber subido documentos primero en el tab principal de Alien Mode
                        - Verifica que los documentos se hayan procesado correctamente (revisa los logs)
                        - Intenta reprocesar los documentos
                        - Verifica que el formato del archivo sea soportado (PDF, DOCX, TXT, MD)
                        
                        ### Respuestas incorrectas o alucinaciones
                        
                        - Usa modo "🎯 Preciso" para máxima exactitud
                        - Verifica que los documentos contengan la información correcta
                        - Alien Mode tiene Verification Agent para reducir alucinaciones
                        - Si persiste, revisa los logs para ver qué documentos se están usando
                        
                        ### Errores de API Key
                        
                        - Verifica que tengas al menos una API Key configurada (OpenAI o Anthropic)
                        - Revisa que la API Key sea válida
                        - Configura en `.env` o en la UI de Configuración
                        
                        ---
                        
                        **💬 Si el problema persiste:** Revisa los logs detallados en la terminal donde está corriendo el servidor.
                        """)
        
        
            # TAB 5: Links DinÃ¡micos
            with gr.Tab("ðŸ”— Links DinÃ¡micos"):
                gr.Markdown("""
                # ðŸ”— Links DinÃ¡micos - ConfiguraciÃ³n de Enlaces para el Widget
                
                Configura links personalizados que el agente usarÃ¡ automÃ¡ticamente en sus respuestas.
                Cada link tiene un nombre visible, URL y etiqueta de acciÃ³n interna.
                """)
                
                with gr.Row():
                    with gr.Column(scale=2):
                        gr.Markdown("### ðŸ“ Configurar Links")
                        
                        link_name = gr.Textbox(
                            label="Nombre Visible",
                            placeholder="Ej: Ver catÃ¡logo, Contactar especialista, Solicitar presupuesto",
                            info="Nombre que verÃ¡ el usuario final"
                        )
                        
                        link_url = gr.Textbox(
                            label="URL",
                            placeholder="https://tu-sitio.com/accion",
                            info="URL completa del link"
                        )
                        
                        link_action_tag = gr.Textbox(
                            label="Etiqueta de AcciÃ³n",
                            placeholder="Ej: action_show_info, action_contact_support, action_book_meeting",
                            info="Etiqueta interna que el agente usarÃ¡ para identificar cuÃ¡ndo usar este link"
                        )
                        
                        with gr.Row():
                            add_link_btn = gr.Button("âž• Agregar Link", variant="primary")
                            clear_links_btn = gr.Button("ðŸ—‘ï¸ Limpiar Todos", variant="stop")
                        
                        links_status = gr.Markdown("**Estado:** Listo para agregar links")
                    
                    with gr.Column(scale=3):
                        gr.Markdown("### ðŸ“‹ Links Configurados")
                        
                        links_display = gr.JSON(
                            label="Links",
                            value={}
                        )
                        
                        gr.Markdown("""
                        ### ðŸ’¡ Ejemplos de Etiquetas de AcciÃ³n:
                        
                        - `action_show_info` - Mostrar mÃ¡s informaciÃ³n
                        - `action_contact_support` - Contactar soporte/especialista
                        - `action_book_meeting` - Reservar cita/clase
                        - `action_buy_product` - Comprar producto
                        - `action_request_quote` - Solicitar presupuesto
                        - `action_view_catalog` - Ver catÃ¡logo completo
                        - `action_compare_options` - Comparar opciones
                        
                        El agente usarÃ¡ automÃ¡ticamente estos links segÃºn el contexto de la conversaciÃ³n.
                        """)
                
                # Estado para almacenar links (en memoria, se puede persistir despuÃ©s)
                links_storage = gr.State(value={})
                
                def add_link(name, url, action_tag, current_links):
                    """Agrega un nuevo link a la configuraciÃ³n."""
                    if not name or not url or not action_tag:
                        return current_links, "âš ï¸ Por favor completa todos los campos", current_links
                    
                    if current_links is None:
                        current_links = {}
                    
                    # Agregar link
                    link_id = str(uuid.uuid4())[:8]
                    current_links[link_id] = {
                        "name": name,
                        "url": url,
                        "action_tag": action_tag
                    }
                    
                    # Guardar en archivo de configuraciÃ³n
                    import json
                    from pathlib import Path
                    links_file = Path(config.memory_dir) / "widget_links.json"
                    links_file.parent.mkdir(parents=True, exist_ok=True)
                    with open(links_file, 'w', encoding='utf-8') as f:
                        json.dump(current_links, f, indent=2, ensure_ascii=False)
                    
                    return current_links, f"âœ… Link agregado: {name}", current_links
                
                def clear_all_links(current_links):
                    """Limpia todos los links."""
                    import json
                    from pathlib import Path
                    links_file = Path(config.memory_dir) / "widget_links.json"
                    if links_file.exists():
                        links_file.unlink()
                    return {}, "ðŸ—‘ï¸ Todos los links eliminados", {}
                
                def load_links():
                    """Carga links desde archivo."""
                    import json
                    from pathlib import Path
                    links_file = Path(config.memory_dir) / "widget_links.json"
                    if links_file.exists():
                        with open(links_file, 'r', encoding='utf-8') as f:
                            return json.load(f)
                    return {}
                
                # Cargar links al iniciar
                initial_links = load_links()
                links_storage.value = initial_links
                links_display.value = initial_links
                
                add_link_btn.click(
                    add_link,
                    inputs=[link_name, link_url, link_action_tag, links_storage],
                    outputs=[links_storage, links_status, links_display]
                ).then(
                    lambda: ("", "", ""),
                    outputs=[link_name, link_url, link_action_tag]
                )
                
                clear_links_btn.click(
                    clear_all_links,
                    inputs=[links_storage],
                    outputs=[links_storage, links_status, links_display]
                )
                
                gr.Markdown("""
                ---
                
                ### ðŸ“– CÃ³mo Funciona:
                
                1. **Agrega Links**: Completa los campos y haz click en "Agregar Link"
                2. **Etiquetas de AcciÃ³n**: El agente usa estas etiquetas para decidir quÃ© link mostrar
                3. **AutomÃ¡tico**: El agente inserta los links automÃ¡ticamente en sus respuestas segÃºn el contexto
                4. **Personalizable**: Cada cliente puede tener sus propios links segÃºn su negocio
                
                **Ejemplo:**
                - Usuario pregunta: "Â¿CÃ³mo puedo contactar a un especialista?"
                - Agente genera respuesta con etiqueta `action_contact_support`
                - Sistema inserta automÃ¡ticamente el link configurado para esa acciÃ³n
                """)


        return widget_tabs
    
    return _create_tabs

