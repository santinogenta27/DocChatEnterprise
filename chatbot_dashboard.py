"""
Dashboard Simple para Empresas - Gestiona tu Chatbot sin Código

Este dashboard permite a empresas no técnicas:
- Ver estadísticas de uso
- Probar consultas
- Ver documentos subidos
- Obtener código de integración listo para copiar
"""

from __future__ import annotations

import gradio as gr
from docchat import AppConfig, load_config
from docchat.chatbot_mode import ChatbotMode
from docchat.chatbot_sdk import DocChatClient
import json
from pathlib import Path

# Cargar configuración
config = load_config()
chatbot_mode = ChatbotMode(config)


def obtener_estadisticas(chatbot_id: str, api_key: str):
    """Obtiene estadísticas del chatbot."""
    if not chatbot_id or not api_key:
        return "⚠️ Ingresa Chatbot ID y API Key"
    
    try:
        info = chatbot_mode.get_chatbot_info(chatbot_id)
        if info["api_key"] != api_key:
            return "❌ API Key incorrecta"
        
        stats = f"""
## 📊 Estadísticas de tu Chatbot

**Nombre:** {info['chatbot_name']}
**Empresa:** {info['company_name']}
**Estado:** {info['status']}
**Documentos:** {info['documents_count']}
**Chunks:** {info['chunks_count']}
**Creado:** {info['created_at']}
"""
        return stats
    except Exception as e:
        return f"❌ Error: {str(e)}"


def probar_consulta(chatbot_id: str, api_key: str, pregunta: str):
    """Prueba una consulta al chatbot."""
    if not chatbot_id or not api_key or not pregunta:
        return "⚠️ Completa todos los campos"
    
    try:
        info = chatbot_mode.get_chatbot_info(chatbot_id)
        if info["api_key"] != api_key:
            return "❌ API Key incorrecta"
        
        response = chatbot_mode.query_chatbot(
            chatbot_id=chatbot_id,
            user_question=pregunta,
            use_reranking=True,
            max_chunks=5
        )
        
        resultado = f"""
## 💬 Respuesta

**Pregunta:** {pregunta}

**Respuesta:**
{response.answer}

**Confianza:** {response.confidence:.0%}
**Chunks usados:** {response.chunks_used}
**Fuentes:** {', '.join(response.sources[:3]) if response.sources else 'N/A'}
"""
        return resultado
    except Exception as e:
        return f"❌ Error: {str(e)}"


def generar_codigo_integracion(chatbot_id: str, api_key: str, api_url: str):
    """Genera código de integración listo para copiar."""
    if not chatbot_id or not api_key:
        return "⚠️ Ingresa Chatbot ID y API Key"
    
    if not api_url:
        api_url = "https://tu-servidor.com"
    
    codigo = f'''"""
Código de Integración para tu Chatbot
Generado automáticamente por DocChat Enterprise
"""

import requests

# ==================== CONFIGURACIÓN ====================
CHATBOT_ID = "{chatbot_id}"
API_KEY = "{api_key}"
API_URL = "{api_url}"

# ==================== FUNCIÓN PRINCIPAL ====================
def responder_cliente(pregunta):
    """
    Esta función la llamas cuando un cliente pregunta algo.
    """
    try:
        response = requests.post(
            f"{{API_URL}}/api/chatbot/{{CHATBOT_ID}}/query",
            json={{
                "question": pregunta,
                "use_reranking": True,
                "max_chunks": 5
            }},
            headers={{"X-API-Key": API_KEY}},
            timeout=30
        )
        response.raise_for_status()
        data = response.json()
        return data["answer"]
    except Exception as e:
        return f"Error: {{str(e)}}"

# ==================== USO ====================
# Cuando un cliente pregunta en tu chatbot:
# respuesta = responder_cliente(pregunta_del_cliente)
# Muestra respuesta al cliente en tu app
'''
    
    return codigo


def verificar_necesita_rag(chatbot_id: str, api_key: str, pregunta: str):
    """Verifica si la pregunta necesita RAG."""
    if not chatbot_id or not api_key or not pregunta:
        return "⚠️ Completa todos los campos"
    
    try:
        info = chatbot_mode.get_chatbot_info(chatbot_id)
        if info["api_key"] != api_key:
            return "❌ API Key incorrecta"
        
        necesita = chatbot_mode.needs_rag(chatbot_id, pregunta)
        
        if necesita:
            return "✅ **SÍ necesita RAG**\n\nEsta pregunta requiere consultar tus documentos privados."
        else:
            return "❌ **NO necesita RAG**\n\nEsta pregunta puede responderse directamente sin consultar documentos."
    except Exception as e:
        return f"❌ Error: {str(e)}"


# Crear interfaz Gradio
with gr.Blocks(title="DocChat Enterprise - Dashboard Chatbot") as demo:
    gr.Markdown("# 🤖 Dashboard Chatbot - DocChat Enterprise")
    gr.Markdown("Gestiona tu chatbot sin necesidad de código técnico")
    
    with gr.Tabs():
        # Tab 1: Estadísticas
        with gr.Tab("📊 Estadísticas"):
            gr.Markdown("### Ver estadísticas de tu chatbot")
            
            chatbot_id_stats = gr.Textbox(
                label="Chatbot ID",
                placeholder="Pega tu Chatbot ID aquí"
            )
            api_key_stats = gr.Textbox(
                label="API Key",
                type="password",
                placeholder="Pega tu API Key aquí"
            )
            btn_stats = gr.Button("📊 Ver Estadísticas", variant="primary")
            output_stats = gr.Markdown()
            
            btn_stats.click(
                fn=obtener_estadisticas,
                inputs=[chatbot_id_stats, api_key_stats],
                outputs=output_stats
            )
        
        # Tab 2: Probar Consultas
        with gr.Tab("💬 Probar Consultas"):
            gr.Markdown("### Prueba consultas a tu chatbot")
            
            chatbot_id_test = gr.Textbox(
                label="Chatbot ID",
                placeholder="Pega tu Chatbot ID aquí"
            )
            api_key_test = gr.Textbox(
                label="API Key",
                type="password",
                placeholder="Pega tu API Key aquí"
            )
            pregunta_test = gr.Textbox(
                label="Pregunta de Prueba",
                placeholder="Ej: ¿Cuál es la política de devoluciones?",
                lines=3
            )
            btn_test = gr.Button("🔍 Probar Consulta", variant="primary")
            output_test = gr.Markdown()
            
            btn_test.click(
                fn=probar_consulta,
                inputs=[chatbot_id_test, api_key_test, pregunta_test],
                outputs=output_test
            )
        
        # Tab 3: Código de Integración
        with gr.Tab("📝 Código de Integración"):
            gr.Markdown("### Obtén código listo para copiar y pegar")
            
            chatbot_id_code = gr.Textbox(
                label="Chatbot ID",
                placeholder="Pega tu Chatbot ID aquí"
            )
            api_key_code = gr.Textbox(
                label="API Key",
                type="password",
                placeholder="Pega tu API Key aquí"
            )
            api_url_code = gr.Textbox(
                label="URL del Servidor",
                value="https://tu-servidor.com",
                placeholder="URL de tu servidor DocChat Enterprise"
            )
            btn_code = gr.Button("📋 Generar Código", variant="primary")
            output_code = gr.Code(
                language="python",
                label="Código Listo para Copiar"
            )
            
            btn_code.click(
                fn=generar_codigo_integracion,
                inputs=[chatbot_id_code, api_key_code, api_url_code],
                outputs=output_code
            )
        
        # Tab 4: Verificar Relevancia
        with gr.Tab("🔍 Verificar Relevancia"):
            gr.Markdown("### ¿Esta pregunta necesita consultar documentos?")
            
            chatbot_id_relevance = gr.Textbox(
                label="Chatbot ID",
                placeholder="Pega tu Chatbot ID aquí"
            )
            api_key_relevance = gr.Textbox(
                label="API Key",
                type="password",
                placeholder="Pega tu API Key aquí"
            )
            pregunta_relevance = gr.Textbox(
                label="Pregunta",
                placeholder="Ej: ¿Cuál es la política de devoluciones?",
                lines=3
            )
            btn_relevance = gr.Button("🔍 Verificar", variant="primary")
            output_relevance = gr.Markdown()
            
            btn_relevance.click(
                fn=verificar_necesita_rag,
                inputs=[chatbot_id_relevance, api_key_relevance, pregunta_relevance],
                outputs=output_relevance
            )


if __name__ == "__main__":
    print("🚀 Iniciando Dashboard Chatbot...")
    demo.launch(server_name="0.0.0.0", server_port=7861, share=False)


