"""UI para Servidor API de Alien Mode Widget."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..alien_mode_wrapper import AlienModeWidgetWrapper


class APIServerUI:
    """UI para gestionar el servidor API."""
    
    def __init__(self, wrapper: 'AlienModeWidgetWrapper'):
        self.wrapper = wrapper
    
    def create_ui(self):
        """Crea UI de Gradio para servidor API."""
        import gradio as gr
        
        gr.Markdown("### 🚀 Servidor API para Widget")
        
        gr.Markdown("""
        **El Servidor API permite que tu widget se comunique con Alien Mode.**
        
        El servidor proporciona:
        - ✅ Endpoint REST para chat (`/api/widget/chat`)
        - ✅ Servir archivos estáticos del widget (`/static/`)
        - ✅ WebSocket para comunicación en tiempo real (opcional)
        - ✅ Health check (`/api/widget/health`)
        """)
        
        with gr.Row():
            with gr.Column():
                api_port = gr.Number(
                    label="Puerto del Servidor",
                    value=self.wrapper.api_server_port,
                    info="Puerto donde correrá el servidor API (default: 7865)"
                )
                
                api_host = gr.Textbox(
                    label="Host",
                    value="0.0.0.0",
                    info="Host donde correrá el servidor (0.0.0.0 = todos los interfaces)"
                )
                
                start_server_btn = gr.Button("🚀 Iniciar Servidor API", variant="primary", size="lg")
                stop_server_btn = gr.Button("⏹️ Detener Servidor", variant="stop", size="lg")
            
            with gr.Column():
                server_status = gr.Markdown(
                    value="**Estado:** Servidor no iniciado"
                )
                
                server_url = gr.Textbox(
                    label="URL del Servidor",
                    value=f"http://127.0.0.1:{self.wrapper.api_server_port}",
                    interactive=False,
                    info="URL que debes usar en 'Generar Código'"
                )
        
        def start_server(port, host):
            """Inicia el servidor API."""
            try:
                # Actualizar puerto
                self.wrapper.api_server_port = int(port)
                
                # Nota: En Gradio no podemos iniciar un servidor en background fácilmente
                # El usuario debe iniciarlo manualmente con el método start_api_server()
                return f"""
**⚠️ Para iniciar el servidor API:**

1. Abre una terminal
2. Ejecuta:
```bash
cd C:\\Users\\usuario\\DocChatEnterprise
python -c "from docchat.alien_mode_widget import AlienModeWidgetWrapper; w = AlienModeWidgetWrapper(); w.start_api_server(port={int(port)}, host='{host}')"
```

3. O usa el script: `python -m docchat.alien_mode_widget.api_server --port {int(port)}`

**URL del Servidor:** `http://{host if host != '0.0.0.0' else '127.0.0.1'}:{int(port)}`

Una vez iniciado, usa esta URL en "Generar Código".
"""
            except Exception as e:
                return f"❌ Error: {e}"
        
        def stop_server():
            """Detiene el servidor API."""
            return "**Nota:** El servidor se detiene con Ctrl+C en la terminal donde está corriendo."
        
        start_server_btn.click(
            start_server,
            inputs=[api_port, api_host],
            outputs=[server_status]
        )
        
        stop_server_btn.click(
            stop_server,
            outputs=[server_status]
        )
        
        gr.Markdown("""
        ---
        
        **📝 Notas:**
        - El servidor debe estar corriendo para que el widget funcione
        - Asegúrate de que el puerto no esté en uso por otra aplicación
        - En producción, configura un proxy reverso (nginx, etc.) para HTTPS
        """)


