"""Gradio app for DocChat Enterprise - Multi-Agent RAG with Autonomous Agents."""

from __future__ import annotations

import os
from typing import List, Optional, Dict, Any
from pathlib import Path

import gradio as gr
from dotenv import load_dotenv

# Cargar .env ANTES de cualquier otra cosa
env_path = Path(__file__).parent / ".env"
cwd_env_path = Path.cwd() / ".env"

env_file = None
if env_path.exists():
    env_file = env_path
    load_dotenv(dotenv_path=env_path, override=True)
elif cwd_env_path.exists():
    env_file = cwd_env_path
    load_dotenv(dotenv_path=cwd_env_path, override=True)
else:
    load_dotenv(override=True)

# Si load_dotenv no funcionó, leer el archivo manualmente
if env_file and not os.getenv("OPENAI_API_KEY"):
    try:
        content = env_file.read_text(encoding='utf-8-sig').strip()
        for line in content.split('\n'):
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if key == "OPENAI_API_KEY":
                    os.environ[key] = value
                    break
    except Exception:
        pass

# Importar componentes
from docchat import AppConfig, load_config
from docchat.document_processor import DocumentProcessor
from docchat.mass_processor import MassDocumentProcessor
from docchat.retriever_builder import RetrieverBuilder
from docchat.workflow import AgentWorkflow
from docchat.memory import MemoryStore, ContextManager
from docchat.autonomous_agent import AutonomousAgent
from docchat.advanced_agent import AdvancedAutonomousAgent
from docchat.audit import AuditLogger
from docchat.auth import UserManager, WorkspaceManager

# Validar API key
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    env_content = ""
    if env_path.exists():
        try:
            env_content = env_path.read_text(encoding='utf-8-sig')
        except Exception as e:
            env_content = f"Error leyendo archivo: {e}"
    
    raise ValueError(
        f"❌ ERROR: OPENAI_API_KEY no está configurada.\n\n"
        f"Debug información:\n"
        f"  - Archivo .env en {env_path}: {'EXISTE' if env_path.exists() else 'NO EXISTE'}\n"
        f"  - Variable de entorno OPENAI_API_KEY: {'DEFINIDA' if os.getenv('OPENAI_API_KEY') else 'NO DEFINIDA'}\n\n"
        "Soluciones:\n"
        "1. Verifica que el archivo .env esté en la misma carpeta que app.py\n"
        "2. O usa variable de entorno: $env:OPENAI_API_KEY='tu-clave'\n"
        "3. O crea el .env manualmente con solo: OPENAI_API_KEY=tu-clave\n\n"
        "Obtén tu clave en: https://platform.openai.com/api-keys"
    )

# Inicializar configuración y componentes
config: AppConfig = load_config()
processor = DocumentProcessor(config)
mass_processor = MassDocumentProcessor(config)
retriever_builder = RetrieverBuilder(config)
workflow = AgentWorkflow(config)

# Inicializar sistemas avanzados
memory_store = MemoryStore(config.memory_dir, config.memory_retention_days) if config.enable_memory else None
context_manager = ContextManager(memory_store, config) if memory_store else None
autonomous_agent = AutonomousAgent(config) if config.enable_autonomous_agents else None
advanced_agent = AdvancedAutonomousAgent(config) if config.enable_autonomous_agents else None
audit_logger = AuditLogger(config.audit_log_dir, config.enable_audit_logs)

# Inicializar sistemas de autenticación y workspace
user_manager = UserManager(config.memory_dir / "users")
workspace_manager = WorkspaceManager(config.memory_dir / "workspaces")

# Inicializar sesión
if context_manager:
    session_id = context_manager.start_session()

# Funciones auxiliares
def _format_sources(sources: List[dict]) -> str:
    if not sources:
        return "Sin fragmentos relevantes recuperados."
    lines = []
    for idx, src in enumerate(sources, start=1):
        lines.append(f"{idx}. **{src['source']}** — {src['preview']}")
    return "\n".join(lines)


def _format_comparative_analysis(analysis) -> str:
    if not analysis:
        return "No hay análisis comparativo disponible."
    
    lines = [
        "## 📊 Análisis Comparativo",
        "",
        f"### Temas Comunes: {', '.join(analysis.common_themes[:10])}",
        "",
        "### Estadísticas:",
        f"- Total documentos: {analysis.statistics.get('total_documents', 0)}",
        f"- Total chunks: {analysis.statistics.get('total_chunks', 0)}",
        f"- Chunks promedio por documento: {analysis.statistics.get('avg_chunks_per_doc', 0):.1f}",
        f"- Tamaño total: {analysis.statistics.get('total_size_mb', 0):.2f} MB",
    ]
    
    if analysis.contradictions:
        lines.append("\n### ⚠️ Contradicciones Detectadas:")
        for cont in analysis.contradictions:
            lines.append(f"- {cont.get('message', 'Contradicción detectada')}")
    
    return "\n".join(lines)


# Funciones principales
def run_pipeline(files, question: str, use_memory: bool = True):
    """Pipeline principal de RAG."""
    if not files:
        raise gr.Error("Primero sube al menos un documento.")
    if not question or not question.strip():
        raise gr.Error("Escribe una pregunta.")
    
    # Audit log
    audit_logger.log(
        event_type="query",
        action="process_documents",
        resource="documents",
        user_id="user",
        metadata={"file_count": len(files), "question": question[:100]}
    )
    
    # Obtener contexto de memoria si está habilitado
    context = {}
    if use_memory and context_manager:
        context = context_manager.get_context_for_query(question)
    
    # Procesar documentos
    docs = processor.process(files)
    retriever = retriever_builder.build_hybrid_retriever(docs)
    
    # Ejecutar workflow (pasar todos los documentos para preguntas generales)
    result = workflow.run(question.strip(), retriever, all_documents=docs)
    
    # Guardar en memoria
    if use_memory and context_manager:
        context_manager.add_query(
            query=question,
            answer=result["answer"],
            sources=[s["source"] for s in result["sources"]],
            metadata={"relevance": result["relevance"]}
        )
    
    return (
        result["answer"],
        _format_sources(result["sources"]),
        result["verification_report"],
        f"Clasificación de relevancia: {result['relevance']}",
    )


def run_massive_processing(files, enable_comparison: bool = True):
    """Procesamiento masivo de documentos."""
    if not files:
        raise gr.Error("Primero sube documentos para procesar.")
    
    if len(files) > config.max_documents_per_batch:
        raise gr.Error(
            f"Máximo {config.max_documents_per_batch} documentos por lote.\n"
            f"Has subido {len(files)} documentos. "
            f"Divide los documentos en lotes más pequeños o aumenta DOCCHAT_MAX_DOCS en .env"
        )
    
    audit_logger.log(
        event_type="mass_processing",
        action="process_massive_batch",
        resource="documents",
        user_id="user",
        metadata={"file_count": len(files), "comparison_enabled": enable_comparison}
    )
    
    try:
        chunks, metadata, analysis = mass_processor.process_massive_batch(
            files,
            enable_comparison=enable_comparison
        )
        
        # Formatear resultados
        metadata_text = "## 📄 Documentos Procesados\n\n"
        for meta in metadata:
            status = "✅" if not meta.errors else "❌"
            metadata_text += f"{status} **{meta.file_name}**\n"
            metadata_text += f"  - Chunks: {meta.chunk_count}\n"
            metadata_text += f"  - Tamaño: {meta.size_mb:.2f} MB\n"
            metadata_text += f"  - Tiempo: {meta.processing_time:.2f}s\n"
            if meta.errors:
                metadata_text += f"  - Errores: {', '.join(meta.errors)}\n"
            metadata_text += "\n"
        
        analysis_text = _format_comparative_analysis(analysis) if analysis else ""
        
        summary = f"""
## ✅ Procesamiento Completado

- **Total documentos**: {len(metadata)}
- **Total chunks generados**: {len(chunks)}
- **Documentos exitosos**: {sum(1 for m in metadata if not m.errors)}
- **Documentos con errores**: {sum(1 for m in metadata if m.errors)}

{analysis_text}
"""
        
        return summary, metadata_text
        
    except Exception as e:
        error_msg = f"Error en procesamiento masivo: {str(e)}"
        audit_logger.log(
            event_type="error",
            action="mass_processing",
            resource="documents",
            result="error",
            metadata={"error": str(e)}
        )
        raise gr.Error(error_msg)


def run_complete_workflow(files, task_description: str, output_format: str = "all"):
    """Ejecutar workflow completo: analizar + generar informes automáticamente."""
    if not task_description or not task_description.strip():
        raise gr.Error("Describe la tarea completa que quieres ejecutar.")
    
    if not advanced_agent:
        raise gr.Error("Agente avanzado no está habilitado.")
    
    if not files:
        raise gr.Error("Sube documentos para analizar.")
    
    audit_logger.log(
        event_type="complete_workflow",
        action="execute_complete_workflow",
        resource="documents",
        user_id="user",
        metadata={"task": task_description[:100], "file_count": len(files), "format": output_format}
    )
    
    try:
        result = advanced_agent.execute_complete_workflow(
            task_description=task_description,
            files=files,
            output_format=output_format
        )
        
        # Formatear resultado
        output = f"""
## 🚀 Workflow Completo Ejecutado

**Tarea**: {task_description}

**Estado**: {'✅ Completado' if result['status'] == 'completed' else '❌ Error'}

### Archivos Generados:
"""
        for output_file in result.get('outputs', []):
            output += f"\n- **{output_file['type'].upper()}**: {output_file.get('path', 'N/A')}"
        
        if result.get('errors'):
            output += "\n\n### Errores:\n"
            for error in result['errors']:
                output += f"- {error}\n"
        
        if result.get('summary'):
            output += f"\n### Resumen:\n{result['summary']}"
        
        return output
        
    except Exception as e:
        error_msg = f"Error ejecutando workflow completo: {str(e)}"
        audit_logger.log(
            event_type="error",
            action="complete_workflow",
            resource="advanced_agent",
            result="error",
            metadata={"error": str(e)}
        )
        raise gr.Error(error_msg)


def run_autonomous_task(task_description: str, context_data: str = ""):
    """Ejecutar tarea con agente autónomo."""
    if not task_description or not task_description.strip():
        raise gr.Error("Describe la tarea que quieres que el agente ejecute.")
    
    if not autonomous_agent:
        raise gr.Error("Agentes autónomos no están habilitados. Configura DOCCHAT_ENABLE_AGENTS=true")
    
    audit_logger.log(
        event_type="autonomous_task",
        action="execute_task",
        resource="autonomous_agent",
        user_id="user",
        metadata={"task": task_description[:100]}
    )
    
    try:
        context = {}
        if context_data:
            try:
                import json
                context = json.loads(context_data)
            except:
                context = {"context": context_data}
        
        result = autonomous_agent.execute_task(
            task_description=task_description,
            context=context
        )
        
        # Formatear resultado
        output = f"""
## 🤖 Tarea Autónoma Ejecutada

**Descripción**: {task_description}

**Estado**: {'✅ Éxito' if result['success'] else '❌ Falló'}

**Herramientas utilizadas**: {', '.join(result.get('tools_used', []))}

### Resultados:
"""
        for tool_result in result.get('results', []):
            status = "✅" if tool_result.get('success') else "❌"
            tool_name = tool_result.get('tool', 'unknown')
            output += f"\n{status} **{tool_name}**\n"
            if tool_result.get('result'):
                output += f"  - {tool_result['result'].message}\n"
            if tool_result.get('error'):
                output += f"  - Error: {tool_result['error']}\n"
        
        output += f"\n### Resumen:\n{result.get('summary', 'N/A')}"
        
        return output
        
    except Exception as e:
        error_msg = f"Error ejecutando tarea autónoma: {str(e)}"
        audit_logger.log(
            event_type="error",
            action="autonomous_task",
            resource="autonomous_agent",
            result="error",
            metadata={"error": str(e)}
        )
        raise gr.Error(error_msg)


def get_memory_stats():
    """Obtener estadísticas de memoria."""
    if not memory_store:
        return "Memoria no está habilitada."
    
    stats = memory_store.get_statistics()
    
    return f"""
## 🧠 Estadísticas de Memoria

- **Total de memorias**: {stats.get('total_memories', 0)}
- **Consultas indexadas**: {stats.get('indexed_queries', 0)}
- **Memoria más antigua**: {stats.get('oldest_memory', 'N/A')}
- **Memoria más reciente**: {stats.get('newest_memory', 'N/A')}
- **Retención**: {stats.get('retention_days', 365)} días
"""


def get_audit_stats():
    """Obtener estadísticas de auditoría."""
    if not config.enable_audit_logs:
        return "Auditoría no está habilitada."
    
    stats = audit_logger.get_statistics()
    
    if not stats:
        return "No hay registros de auditoría aún."
    
    output = "## 🔒 Estadísticas de Auditoría\n\n"
    output += f"- **Total de entradas**: {stats.get('total_entries', 0)}\n\n"
    
    if stats.get('event_types'):
        output += "### Tipos de eventos:\n"
        for event_type, count in stats['event_types'].items():
            output += f"- {event_type}: {count}\n"
    
    return output


# Interfaz Gradio
with gr.Blocks(title="DocChat Enterprise", theme=gr.themes.Soft(primary_hue="teal")) as demo:
    gr.Markdown(
        """
        # 🚀 DocChat Enterprise · Multi-Agent RAG con Agentes Autónomos
        
        Sistema avanzado de análisis de documentos con agentes autónomos, memoria persistente y procesamiento masivo.
        
        **Funcionalidades:**
        - 📚 Procesamiento híbrido (Docling + chunking jerárquico)
        - 🔍 Recuperación híbrida (BM25 + embeddings)
        - 🤖 Agentes autónomos con herramientas
        - 🧠 Memoria persistente empresarial
        - 📊 Procesamiento masivo (200+ documentos)
        - 🔒 Auditoría y seguridad
        """
    )
    
    with gr.Tabs():
        # Tab 1: RAG Principal
        with gr.Tab("🔍 Consulta RAG"):
            gr.Markdown("### Consulta estándar con verificación multi-agente")
            
            with gr.Row():
                file_input = gr.Files(
                    label="📂 Documentos (PDF, DOCX, TXT, MD)",
                    file_count="multiple",
                    file_types=[".pdf", ".docx", ".txt", ".md"],
                )
            
            with gr.Row():
                question_input = gr.Textbox(
                    label="❓ Pregunta",
                    placeholder="Ejemplo: ¿Cuál es el PUE del data center en Singapur según el informe?",
                    lines=3,
                )
            
            with gr.Row():
                use_memory_check = gr.Checkbox(
                    label="Usar memoria persistente",
                    value=config.enable_memory,
                )
            
            run_button = gr.Button("🚀 Ejecutar pipeline", variant="primary")
            
            with gr.Row():
                with gr.Column():
                    answer_output = gr.Markdown(label="🧠 Respuesta")
                    sources_output = gr.Markdown(label="📚 Fuentes recuperadas")
                with gr.Column():
                    verification_output = gr.Markdown(label="✅ Verificación")
                    relevance_output = gr.Markdown(label="🔎 Estado de relevancia")
            
            run_button.click(
                fn=run_pipeline,
                inputs=[file_input, question_input, use_memory_check],
                outputs=[answer_output, sources_output, verification_output, relevance_output],
            )
        
        # Tab 2: Procesamiento Masivo
        with gr.Tab("📚 Procesamiento Masivo"):
            gr.Markdown("### Procesa hasta 1000 documentos con análisis comparativo")
            gr.Markdown("💡 **NUEVO**: Arrastra carpetas completas o selecciona múltiples archivos")
            gr.Markdown("🚀 **ESCALABLE**: Soporta hasta 1000 documentos por lote con procesamiento paralelo optimizado")
            
            with gr.Row():
                mass_files = gr.Files(
                    label="📂 Documentos (hasta 1000) - Arrastra carpetas o selecciona múltiples",
                    file_count="multiple",
                    file_types=[".pdf", ".docx", ".txt", ".md"],
                )
            
            with gr.Row():
                comparison_check = gr.Checkbox(
                    label="Habilitar análisis comparativo",
                    value=True,
                )
            
            mass_process_button = gr.Button("🚀 Procesar Masivamente", variant="primary")
            
            with gr.Row():
                mass_summary = gr.Markdown(label="📊 Resumen")
                mass_metadata = gr.Markdown(label="📄 Detalles por Documento")
            
            mass_process_button.click(
                fn=run_massive_processing,
                inputs=[mass_files, comparison_check],
                outputs=[mass_summary, mass_metadata],
            )
        
        # Tab 2.5: Workflow Completo (NUEVO)
        with gr.Tab("🔥 Workflow Completo"):
            gr.Markdown("### Analiza documentos y genera informes automáticamente")
            gr.Markdown("""
            **Ejemplos:**
            - "Analiza estos 80 PDFs y genera informe + PPT + Excel con los hallazgos"
            - "Procesa todos los documentos y crea un reporte ejecutivo completo"
            - "Analiza los contratos y genera un resumen en Excel"
            """)
            
            with gr.Row():
                workflow_files = gr.Files(
                    label="📂 Documentos para analizar (hasta 1000 soportados)",
                    file_count="multiple",
                    file_types=[".pdf", ".docx", ".txt", ".md"],
                )
            
            with gr.Row():
                workflow_task = gr.Textbox(
                    label="📝 Tarea completa a ejecutar",
                    placeholder="Ejemplo: Analiza estos documentos y genera informe + PPT + Excel con los hallazgos principales",
                    lines=3,
                )
            
            with gr.Row():
                output_format = gr.Radio(
                    choices=["all", "report", "presentation", "excel"],
                    value="all",
                    label="📊 Formato de salida",
                    info="'all' genera todos los formatos"
                )
            
            workflow_button = gr.Button("🚀 Ejecutar Workflow Completo", variant="primary", size="lg")
            
            workflow_output = gr.Markdown(label="📊 Resultado del Workflow")
            
            workflow_button.click(
                fn=run_complete_workflow,
                inputs=[workflow_files, workflow_task, output_format],
                outputs=[workflow_output],
            )
        
        # Tab 3: Agentes Autónomos
        with gr.Tab("🤖 Agentes Autónomos"):
            gr.Markdown("### Ejecuta tareas autónomas con herramientas")
            
            if not autonomous_agent:
                gr.Markdown("⚠️ **Agentes autónomos no están habilitados.** Configura `DOCCHAT_ENABLE_AGENTS=true`")
            else:
                gr.Markdown("""
                **Ejemplos de tareas:**
                - "Analizar los documentos y generar un reporte en Excel"
                - "Enviar un email a juan@empresa.com con el resumen del análisis"
                - "Crear una presentación con los hallazgos principales"
                - "Programar una tarea para ejecutar cada lunes"
                """)
            
            with gr.Row():
                task_input = gr.Textbox(
                    label="📝 Descripción de la tarea",
                    placeholder="Ejemplo: Analizar los documentos y enviar un reporte por email",
                    lines=4,
                )
            
            with gr.Row():
                context_input = gr.Textbox(
                    label="📋 Contexto adicional (JSON opcional)",
                    placeholder='{"recipient": "juan@empresa.com", "format": "excel"}',
                    lines=3,
                )
            
            agent_button = gr.Button("🚀 Ejecutar Tarea Autónoma", variant="primary")
            
            agent_output = gr.Markdown(label="📊 Resultado")
            
            agent_button.click(
                fn=run_autonomous_task,
                inputs=[task_input, context_input],
                outputs=[agent_output],
            )
        
        # Tab 4: Memoria y Estadísticas
        with gr.Tab("🧠 Memoria y Estadísticas"):
            gr.Markdown("### Estadísticas del sistema")
            
            with gr.Row():
                memory_stats_btn = gr.Button("📊 Ver Estadísticas de Memoria", variant="secondary")
                audit_stats_btn = gr.Button("🔒 Ver Estadísticas de Auditoría", variant="secondary")
            
            with gr.Row():
                stats_output = gr.Markdown(label="📈 Estadísticas")
            
            memory_stats_btn.click(
                fn=get_memory_stats,
                outputs=[stats_output],
            )
            
            audit_stats_btn.click(
                fn=get_audit_stats,
                outputs=[stats_output],
            )
    
    gr.Markdown(
        """
        ---
        ### 💡 Consejos
        
        - **RAG Principal**: Para consultas estándar con verificación
        - **Procesamiento Masivo**: Para analizar grandes volúmenes de documentos
        - **Agentes Autónomos**: Para automatizar tareas complejas
        - **Memoria**: El sistema aprende y mejora con cada consulta
        
        ### ⚙️ Configuración
        
        - Límite de documentos: hasta 1000 por lote
        - Tamaño máximo: 5GB por lote
        - Workers paralelos: 16 (optimizado para lotes grandes)
        - Memoria: Habilitada por defecto (365 días de retención)
        - Auditoría: Habilitada por defecto
        """
    )


if __name__ == "__main__":
    import socket
    
    # Find an available port
    def find_free_port(start_port=7860):
        for port in range(start_port, start_port + 10):
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.bind(('127.0.0.1', port))
                    return port
            except OSError:
                continue
        return start_port  # Fallback
    
    port = find_free_port()
    print(f"🚀 Starting DocChat Enterprise on http://127.0.0.1:{port}")
    demo.queue().launch(server_name="127.0.0.1", server_port=port, show_api=False)
