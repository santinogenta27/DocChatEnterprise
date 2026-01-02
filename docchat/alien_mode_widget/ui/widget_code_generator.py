"""Generador de código HTML para widget embeddable de Alien Mode."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..alien_mode_wrapper import AlienModeWidgetWrapper


class WidgetCodeGenerator:
    """Genera código HTML para widget embeddable."""
    
    def __init__(self, wrapper: 'AlienModeWidgetWrapper'):
        self.wrapper = wrapper
    
    def create_ui(self):
        """Crea UI de Gradio para generar código."""
        import gradio as gr
        
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
                    value="Alien Mode",
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


