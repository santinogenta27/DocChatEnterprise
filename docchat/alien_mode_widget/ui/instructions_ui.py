"""UI de Instrucciones para Alien Mode Widget."""

from __future__ import annotations


class InstructionsUI:
    """UI con instrucciones de uso."""
    
    def create_ui(self):
        """Crea UI de Gradio con instrucciones."""
        import gradio as gr
        
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
                
                ### Opción 1: Desde la UI de Chat
                
                1. Ve al tab **"💬 Chat"**
                2. Usa el campo **"📄 Subir Documentos"**
                3. Selecciona tus PDFs, DOCX, TXT o archivos Markdown
                4. Haz click en **"Enviar"** o envía un mensaje
                5. Los documentos se procesarán automáticamente
                
                ### Opción 2: Desde la API
                
                Puedes procesar documentos mediante la API del widget:
                
                ```python
                import requests
                
                # Subir documento
                files = {'file': open('mi_documento.pdf', 'rb')}
                response = requests.post(
                    'http://127.0.0.1:7865/api/widget/upload',
                    files=files,
                    params={'session_id': 'tu_session_id'}
                )
                ```
                
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
            
            with gr.Tab("🔍 Características de Alien Mode"):
                gr.Markdown("""
                ## 🔍 Características de Alien Mode
                
                Alien Mode es un **Sistema Multi-Agente RAG de Máxima Calidad** con:
                
                ### 🔬 Sistema Multi-Agente
                
                - **🔍 Relevance Checker**: Verifica si la pregunta es relevante a los documentos
                - **🔬 Research Agent**: Genera respuestas iniciales basadas en documentos recuperados
                - **✅ Verification Agent**: Verifica que las respuestas estén soportadas (anti-hallucinación)
                - **🔄 Self-Correction**: Re-ejecuta research automáticamente si hay contradicciones
                - **🔀 Hybrid Retriever**: Combina BM25 (búsqueda léxica) + Vector Search (búsqueda semántica)
                
                ### 🚀 Capacidades Avanzadas
                
                - **Context Folding**: Gestión eficiente de contextos masivos (500+ PDFs)
                - **Data Provenance**: Trazabilidad completa de cada pieza de información
                - **Chain of Thought Reasoning**: Razonamiento paso a paso
                - **Path-dependent Reasoning**: Múltiples enfoques probados
                - **Test Time Training**: Mejora continua con cada conversación
                - **Person in the Loop**: Control humano para decisiones críticas
                - **Reinforcement Learning & Planning**: Estrategias adaptativas
                - **MCP Powered**: Conexión a sistemas externos, bases de datos, APIs
                
                ### 📄 Procesamiento de Documentos
                
                - Extracción perfecta de PDFs (PyPDF2 + Docling fallback)
                - Soporte para DOCX, TXT, Markdown
                - Caché inteligente de documentos procesados
                - Chunking optimizado con solapamiento
                
                ---
                
                **🎯 Resultado:** Respuestas precisas, verificadas y basadas 100% en tus documentos.
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
                
                - Asegúrate de haber subido documentos primero
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
            
            with gr.Tab("📚 Recursos Adicionales"):
                gr.Markdown("""
                ## 📚 Recursos Adicionales
                
                ### Documentación
                
                - **Alien Mode Core**: `docchat/alien_mode.py`
                - **DocumentProcessor**: `docchat/document_processor.py`
                - **RetrieverBuilder**: `docchat/retriever_builder.py`
                
                ### Archivos del Widget
                
                - **API Server**: `docchat/alien_mode_widget/widget/api_server.py`
                - **Widget JS**: Se genera automáticamente en `/static/alien-mode-widget.js`
                - **Wrapper**: `docchat/alien_mode_widget/alien_mode_wrapper.py`
                
                ### Ejemplos de Uso
                
                ```python
                from docchat.alien_mode_widget import AlienModeWidgetWrapper
                
                # Crear wrapper
                wrapper = AlienModeWidgetWrapper()
                
                # Obtener interfaz Gradio
                demo = wrapper.get_gradio_interface()
                demo.launch()
                
                # O iniciar solo el servidor API
                wrapper.start_api_server(port=7865)
                ```
                
                ---
                
                **🎯 ¿Preguntas?** Revisa los logs o la documentación del código fuente.
                """)
        
        return instruction_tabs


