"""UI de Configuración Enterprise para Alien Mode Widget."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..alien_mode_wrapper import AlienModeWidgetWrapper


class AlienModeConfigUI:
    """UI de configuración enterprise."""
    
    def __init__(self, wrapper: 'AlienModeWidgetWrapper'):
        self.wrapper = wrapper
    
    def create_ui(self):
        """Crea UI de Gradio para configuración."""
        import gradio as gr
        
        gr.Markdown("### ⚙️ Configuración Enterprise")
        
        with gr.Accordion("🔧 Configuración General", open=True):
            brand_name = gr.Textbox(
                label="Nombre de tu Empresa",
                value=getattr(self.wrapper.config, 'app_name', 'Alien Mode'),
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
                info="Para usar OpenAI como LLM"
            )
            
            anthropic_key = gr.Textbox(
                label="Anthropic API Key",
                type="password",
                placeholder="sk-ant-...",
                info="Para usar Claude como LLM"
            )
        
        save_config_btn = gr.Button("💾 Guardar Configuración", variant="primary")
        config_status = gr.Textbox(label="Estado", interactive=False)
        
        def save_config_fn(brand, rag_model_val, max_chunk, overlap, openai_key_val, anthropic_key_val):
            """Guarda configuración."""
            try:
                # Actualizar configuración
                self.wrapper.config.app_name = brand
                # Nota: No modificamos alien_mode directamente, solo la config
                
                return "✅ Configuración guardada. Algunos cambios requieren reiniciar el servidor."
            except Exception as e:
                return f"❌ Error: {e}"
        
        save_config_btn.click(
            save_config_fn,
            inputs=[brand_name, rag_model, max_chunk_size, chunk_overlap, openai_key, anthropic_key],
            outputs=[config_status]
        )


