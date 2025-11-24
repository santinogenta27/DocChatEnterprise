"""Gradio app for DocChat Enterprise - Multi-Agent RAG with Autonomous Agents."""

from __future__ import annotations

import os
import json
import uuid
from typing import List, Optional, Dict, Any
from pathlib import Path
from datetime import datetime

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
from docchat.enterprise_api import EnterpriseAPIMode
from docchat.enterprise_agentic_ai import EnterpriseAgenticAI
from docchat.customer_service_agent import CustomerServiceAgent
from docchat.chatbot_mode import ChatbotMode
from docchat.cloud_integrations import CloudStorageIntegration, WebhookProcessor
from docchat.rpa_automation import RPAAutomationEngine
from docchat.rpa_enterprise_integration import RPAEnterpriseIntegration
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

# Inicializar sistemas avanzados de mejoras
from docchat.analytics.analytics_engine import AnalyticsEngine
from docchat.observability.monitoring import MonitoringSystem
from docchat.security.rbac import RBACManager
from docchat.async_processor import AsyncDocumentProcessor

analytics_engine = AnalyticsEngine(config)
monitoring_system = MonitoringSystem(config)
rbac_manager = RBACManager(config)
async_processor = AsyncDocumentProcessor(config)

# Inicializar sistemas avanzados
memory_store = MemoryStore(config.memory_dir, config.memory_retention_days) if config.enable_memory else None
context_manager = ContextManager(memory_store, config) if memory_store else None
autonomous_agent = AutonomousAgent(config) if config.enable_autonomous_agents else None
advanced_agent = AdvancedAutonomousAgent(config) if config.enable_autonomous_agents else None
enterprise_api = EnterpriseAPIMode(config)
enterprise_agentic_ai = EnterpriseAgenticAI(config) if config.enable_autonomous_agents else None
customer_service_agent = CustomerServiceAgent(config) if config.enable_autonomous_agents else None
rpa_engine = RPAAutomationEngine(config) if config.enable_autonomous_agents else None
rpa_enterprise = RPAEnterpriseIntegration(config, rpa_engine) if rpa_engine else None
chatbot_mode = ChatbotMode(config)
cloud_integration = CloudStorageIntegration(config, enterprise_api)
webhook_processor = WebhookProcessor(config, enterprise_api)
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
def run_pipeline(files, question: str, use_memory: bool = True, speed_mode: str = "balanced"):
    """Pipeline principal de RAG - Soporta hasta 1000 documentos."""
    import time
    
    # Iniciar tracking de performance
    start_time = time.time()
    trace = monitoring_system.start_trace("rag_pipeline", {"question": question[:50], "file_count": len(files)})
    
    if not files:
        raise gr.Error("Primero sube al menos un documento.")
    if not question or not question.strip():
        raise gr.Error("Escribe una pregunta.")
    
    # Validar límite de documentos
    if len(files) > config.max_documents_per_batch:
        raise gr.Error(
            f"Máximo {config.max_documents_per_batch} documentos por lote.\n"
            f"Has subido {len(files)} documentos. "
            f"Divide los documentos en lotes más pequeños o aumenta DOCCHAT_MAX_DOCS en .env"
        )
    
    # Validar tamaño total de archivos
    try:
        import shutil
        total_size = 0
        for file_obj in files:
            if hasattr(file_obj, 'size'):
                total_size += file_obj.size
            elif hasattr(file_obj, 'name'):
                try:
                    from pathlib import Path
                    file_path = Path(file_obj.name)
                    if file_path.exists():
                        total_size += file_path.stat().st_size
                except:
                    pass
        
        total_size_mb = total_size / (1024 * 1024)
        max_size_mb = config.max_total_upload_mb
        
        if total_size_mb > max_size_mb:
            raise gr.Error(
                f"Tamaño total excede el límite.\n"
                f"Tamaño total: {total_size_mb:.2f} MB\n"
                f"Límite máximo: {max_size_mb} MB\n"
                f"Reduce el número de archivos o su tamaño."
            )
        
        # Verificar espacio disponible en disco
        disk_usage = shutil.disk_usage(".")
        free_space_gb = disk_usage.free / (1024 * 1024 * 1024)
        required_space_gb = (total_size_mb * 2) / 1024  # Necesitamos ~2x el tamaño para procesamiento
        
        if free_space_gb < required_space_gb:
            raise gr.Error(
                f"Espacio insuficiente en disco.\n"
                f"Espacio libre: {free_space_gb:.2f} GB\n"
                f"Espacio requerido: {required_space_gb:.2f} GB\n"
                f"Libera espacio en disco o reduce el número de archivos.\n\n"
                f"💡 Sugerencia: Limpia archivos temporales de Gradio en:\n"
                f"   C:\\Users\\Random\\AppData\\Local\\Temp\\gradio"
            )
        
    except gr.Error:
        raise
    except Exception as e:
        # Si falla la validación, continuar pero advertir
        print(f"Advertencia: No se pudo validar espacio en disco: {e}")
    
    # Mensaje informativo para grandes volúmenes
    if len(files) > 50:
        print(f"Procesando {len(files)} documentos en Consulta RAG... Esto puede tardar varios minutos.")
    
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
    
    # Procesar documentos con manejo de errores mejorado
    try:
        docs = processor.process(files)
    except OSError as e:
        if "No space left on device" in str(e) or "errno 28" in str(e):
            raise gr.Error(
                f"❌ ERROR: Espacio insuficiente en disco.\n\n"
                f"El sistema no tiene suficiente espacio para procesar {len(files)} documentos.\n\n"
                f"💡 SOLUCIONES:\n"
                f"1. Libera espacio en disco (necesitas al menos 2-3 GB libres)\n"
                f"2. Limpia archivos temporales:\n"
                f"   - C:\\Users\\Random\\AppData\\Local\\Temp\\gradio\n"
                f"   - C:\\Users\\Random\\AppData\\Local\\Temp\n"
                f"3. Reduce el número de archivos (prueba con 20-30 primero)\n"
                f"4. Procesa en lotes más pequeños\n\n"
                f"Para limpiar archivos temporales de Gradio, ejecuta:\n"
                f"   Remove-Item -Path \"$env:LOCALAPPDATA\\Temp\\gradio\\*\" -Recurse -Force"
            )
        else:
            raise gr.Error(f"Error al procesar documentos: {str(e)}")
    except Exception as e:
        raise gr.Error(f"Error inesperado al procesar documentos: {str(e)}")
    
    retriever = retriever_builder.build_hybrid_retriever(docs)
    
    # Aplicar modo de velocidad temporalmente
    original_speed_mode = config.speed_mode
    config.speed_mode = speed_mode
    if speed_mode == "fast":
        print("⚡ Modo RÁPIDO activado: respuestas más concisas, procesamiento acelerado")
    elif speed_mode == "quality":
        print("🎯 Modo MÁXIMA CALIDAD activado: análisis profundo, puede tardar más")
    else:
        print("⚖️ Modo BALANCEADO activado: equilibrio entre velocidad y calidad")
    
    # Ejecutar workflow (pasar todos los documentos para preguntas generales)
    try:
        result = workflow.run(question.strip(), retriever, all_documents=docs)
        print(f"\n📊 Resultado del workflow recibido:")
        print(f"   - Respuesta: {len(result.get('answer', ''))} caracteres")
        print(f"   - Fuentes: {len(result.get('sources', []))}")
        print(f"   - Relevancia: {result.get('relevance', 'N/A')}\n")
    except Exception as e:
        print(f"\n❌ ERROR en workflow.run(): {str(e)}")
        import traceback
        traceback.print_exc()
        raise gr.Error(f"Error al ejecutar workflow: {str(e)}")
    
    # Restaurar modo original
    config.speed_mode = original_speed_mode
    
    # Guardar en memoria
    if use_memory and context_manager:
        context_manager.add_query(
            query=question,
            answer=result["answer"],
            sources=[s["source"] for s in result["sources"]],
            metadata={"relevance": result["relevance"]}
        )
    
    # Finalizar tracking
    response_time = time.time() - start_time
    monitoring_system.end_trace(trace)
    
    # Registrar métricas
    monitoring_system.record_metric("pipeline_response_time", response_time, {"speed_mode": speed_mode})
    monitoring_system.record_metric("pipeline_documents_processed", len(files))
    monitoring_system.record_metric("pipeline_sources_retrieved", len(result.get("sources", [])))
    
    # Trackear en analytics
    documents_used = [s.get("source", "unknown") for s in result.get("sources", [])]
    analytics_engine.track_query(
        query=question,
        user_id="user",
        response_time=response_time,
        documents_used=documents_used,
        success=True
    )
    
    # Análisis de sentimiento de la pregunta
    sentiment = analytics_engine.analyze_sentiment(question)
    
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


def run_idp_processing(files):
    """Procesa documentos con Intelligent Document Processing (IDP)."""
    if not files:
        raise gr.Error("Primero sube documentos para procesar con IDP.")
    
    if not enterprise_agentic_ai:
        raise gr.Error("Enterprise Agentic AI no está habilitado. Configura DOCCHAT_ENABLE_AGENTS=true")
    
    audit_logger.log(
        event_type="idp_processing",
        action="process_documents",
        resource="enterprise_agentic_ai",
        user_id="user",
        metadata={"file_count": len(files)}
    )
    
    try:
        idp_results = enterprise_agentic_ai.process_documents_with_idp(
            files=files,
            extract_entities=True,
            extract_metrics=True
        )
        
        output = f"## ✅ Procesamiento IDP Completado\n\n"
        output += f"**Documentos procesados:** {len(idp_results)}\n\n"
        
        for file_name, result in idp_results.items():
            from pathlib import Path
            clean_name = Path(file_name).name
            output += f"### 📄 {clean_name}\n\n"
            output += f"- **Tipo de documento:** {result.document_type}\n"
            output += f"- **Entidades extraídas:** {len(result.entities)}\n"
            output += f"- **Métricas clave:** {len(result.key_metrics)}\n"
            if result.entities:
                output += f"- **Entidades principales:** {', '.join(result.entities[:5])}\n"
            if result.key_metrics:
                output += f"- **Métricas:** {', '.join(list(result.key_metrics.keys())[:3])}\n"
            output += "\n"
        
        output += "\n**💡 Ahora puedes ejecutar tareas autónomas usando estos datos procesados.**\n"
        
        return output
        
    except Exception as e:
        error_msg = f"Error en procesamiento IDP: {str(e)}"
        audit_logger.log(
            event_type="idp_processing",
            action="error",
            resource="enterprise_agentic_ai",
            user_id="user",
            metadata={"error": str(e)}
        )
        raise gr.Error(error_msg)


def run_enterprise_agentic_task(task_description: str, task_type: str, context_data: str = ""):
    """Ejecuta tarea autónoma usando Enterprise Agentic AI con datos IDP."""
    if not task_description or not task_description.strip():
        raise gr.Error("Describe la tarea que quieres que el Agentic AI ejecute.")
    
    if not enterprise_agentic_ai:
        raise gr.Error("Enterprise Agentic AI no está habilitado. Configura DOCCHAT_ENABLE_AGENTS=true")
    
    # Verificar si hay documentos procesados con IDP (opcional)
    has_idp_data = bool(enterprise_agentic_ai.idp_results)
    
    if not has_idp_data:
        # Permitir ejecutar tareas sin IDP (para tareas simples como enviar emails)
        print("⚠️ No hay documentos procesados con IDP. Ejecutando tarea sin datos IDP.")
    
    audit_logger.log(
        event_type="enterprise_agentic_task",
        action="execute_task",
        resource="enterprise_agentic_ai",
        user_id="user",
        metadata={"task": task_description[:100], "task_type": task_type, "has_idp_data": has_idp_data}
    )
    
    try:
        context = {}
        if context_data:
            try:
                context = json.loads(context_data)
            except:
                context = {"context": context_data}
        
        # Usar datos IDP solo si están disponibles
        result = enterprise_agentic_ai.execute_autonomous_task(
            task_description=task_description,
            task_type=task_type,
            context=context,
            use_processed_data=has_idp_data  # Solo usar IDP si hay datos
        )
        
        output = result.get("summary", "No se generó resumen")
        output += f"\n\n**Herramientas utilizadas:** {', '.join(result.get('tools_used', []))}\n"
        output += f"**Datos IDP utilizados:** {result.get('idp_data_used', 0)} documentos\n"
        
        if result.get("success"):
            output += "\n✅ **Tarea completada exitosamente**\n"
        else:
            output += "\n⚠️ **Tarea completada con algunos errores**\n"
        
        return output
        
    except Exception as e:
        error_msg = f"Error ejecutando tarea autónoma: {str(e)}"
        audit_logger.log(
            event_type="enterprise_agentic_task",
            action="error",
            resource="enterprise_agentic_ai",
            user_id="user",
            metadata={"error": str(e)}
        )
        raise gr.Error(error_msg)


def run_idp_processing(files):
    """Procesa documentos con Intelligent Document Processing (IDP)."""
    if not files:
        raise gr.Error("Primero sube documentos para procesar con IDP.")
    
    if not enterprise_agentic_ai:
        raise gr.Error("Enterprise Agentic AI no está habilitado. Configura DOCCHAT_ENABLE_AGENTS=true")
    
    audit_logger.log(
        event_type="idp_processing",
        action="process_documents",
        resource="enterprise_agentic_ai",
        user_id="user",
        metadata={"file_count": len(files)}
    )
    
    try:
        idp_results = enterprise_agentic_ai.process_documents_with_idp(
            files=files,
            extract_entities=True,
            extract_metrics=True
        )
        
        output = f"## ✅ Procesamiento IDP Completado\n\n"
        output += f"**Documentos procesados:** {len(idp_results)}\n\n"
        
        for file_name, result in idp_results.items():
            from pathlib import Path
            clean_name = Path(file_name).name
            output += f"### 📄 {clean_name}\n\n"
            output += f"- **Tipo de documento:** {result.document_type}\n"
            output += f"- **Entidades extraídas:** {len(result.entities)}\n"
            output += f"- **Métricas clave:** {len(result.key_metrics)}\n"
            if result.entities:
                output += f"- **Entidades principales:** {', '.join(result.entities[:5])}\n"
            if result.key_metrics:
                output += f"- **Métricas:** {', '.join(list(result.key_metrics.keys())[:3])}\n"
            output += "\n"
        
        output += "\n**💡 Ahora puedes ejecutar tareas autónomas usando estos datos procesados.**\n"
        
        return output
        
    except Exception as e:
        error_msg = f"Error en procesamiento IDP: {str(e)}"
        audit_logger.log(
            event_type="idp_processing",
            action="error",
            resource="enterprise_agentic_ai",
            user_id="user",
            metadata={"error": str(e)}
        )
        raise gr.Error(error_msg)


def run_enterprise_agentic_task(task_description: str, task_type: str, context_data: str = ""):
    """Ejecuta tarea autónoma usando Enterprise Agentic AI con datos IDP."""
    if not task_description or not task_description.strip():
        raise gr.Error("Describe la tarea que quieres que el Agentic AI ejecute.")
    
    if not enterprise_agentic_ai:
        raise gr.Error("Enterprise Agentic AI no está habilitado. Configura DOCCHAT_ENABLE_AGENTS=true")
    
    # Verificar si hay documentos procesados con IDP (opcional)
    has_idp_data = bool(enterprise_agentic_ai.idp_results)
    
    if not has_idp_data:
        # Permitir ejecutar tareas sin IDP (para tareas simples como enviar emails)
        print("⚠️ No hay documentos procesados con IDP. Ejecutando tarea sin datos IDP.")
    
    audit_logger.log(
        event_type="enterprise_agentic_task",
        action="execute_task",
        resource="enterprise_agentic_ai",
        user_id="user",
        metadata={"task": task_description[:100], "task_type": task_type, "has_idp_data": has_idp_data}
    )
    
    try:
        context = {}
        if context_data:
            try:
                context = json.loads(context_data)
            except:
                context = {"context": context_data}
        
        # Usar datos IDP solo si están disponibles
        result = enterprise_agentic_ai.execute_autonomous_task(
            task_description=task_description,
            task_type=task_type,
            context=context,
            use_processed_data=has_idp_data  # Solo usar IDP si hay datos
        )
        
        output = result.get("summary", "No se generó resumen")
        output += f"\n\n**Herramientas utilizadas:** {', '.join(result.get('tools_used', []))}\n"
        output += f"**Datos IDP utilizados:** {result.get('idp_data_used', 0)} documentos\n"
        
        if result.get("success"):
            output += "\n✅ **Tarea completada exitosamente**\n"
        else:
            output += "\n⚠️ **Tarea completada con algunos errores**\n"
        
        return output
        
    except Exception as e:
        error_msg = f"Error ejecutando tarea autónoma: {str(e)}"
        audit_logger.log(
            event_type="enterprise_agentic_task",
            action="error",
            resource="enterprise_agentic_ai",
            user_id="user",
            metadata={"error": str(e)}
        )
        raise gr.Error(error_msg)


# ==================== Funciones para Modo Chatbot ====================

def register_chatbot(chatbot_name: str, company_name: str):
    """Registra un nuevo chatbot."""
    if not chatbot_name or not chatbot_name.strip():
        raise gr.Error("Ingresa el nombre del chatbot.")
    
    if not company_name or not company_name.strip():
        raise gr.Error("Ingresa el nombre de la empresa.")
    
    try:
        connection = chatbot_mode.register_chatbot(
            chatbot_name=chatbot_name.strip(),
            company_name=company_name.strip()
        )
        
        output = f"## ✅ Chatbot Registrado Exitosamente\n\n"
        output += f"**Nombre del Chatbot:** {connection.chatbot_name}\n"
        output += f"**Empresa:** {connection.company_name}\n"
        output += f"**Chatbot ID:** `{connection.chatbot_id}`\n"
        output += f"**API Key:** `{connection.api_key}`\n\n"
        output += "**⚠️ IMPORTANTE:** Guarda estos valores. Los necesitarás para:\n"
        output += "- Conectar tu chatbot por API\n"
        output += "- Subir data para este chatbot\n"
        output += "- Hacer consultas desde tu chatbot externo\n"
        
        audit_logger.log(
            event_type="chatbot_registration",
            action="register",
            resource="chatbot_mode",
            user_id="user",
            metadata={
                "chatbot_name": connection.chatbot_name,
                "company_name": connection.company_name,
                "chatbot_id": connection.chatbot_id
            }
        )
        
        return output
        
    except Exception as e:
        error_msg = f"Error registrando chatbot: {str(e)}"
        audit_logger.log(
            event_type="chatbot_registration",
            action="error",
            resource="chatbot_mode",
            user_id="user",
            metadata={"error": str(e)}
        )
        raise gr.Error(error_msg)


def upload_chatbot_data(chatbot_id: str, files):
    """Sube y procesa data para un chatbot."""
    if not chatbot_id or not chatbot_id.strip():
        raise gr.Error("Ingresa el Chatbot ID.")
    
    if not files:
        raise gr.Error("Sube al menos un documento.")
    
    chatbot_id = chatbot_id.strip()
    
    try:
        result = chatbot_mode.upload_chatbot_data(
            chatbot_id=chatbot_id,
            files=files
        )
        
        output = f"## ✅ Data Procesada Exitosamente\n\n"
        output += f"**Chatbot ID:** {chatbot_id}\n"
        output += f"**Documentos procesados:** {result['documents_processed']}\n"
        output += f"**Chunks creados:** {result['chunks_created']}\n\n"
        output += "✅ **Base vectorizada creada y lista para consultas**\n\n"
        output += "Ahora tu chatbot puede consultar esta data por API.\n"
        
        audit_logger.log(
            event_type="chatbot_data_upload",
            action="upload",
            resource="chatbot_mode",
            user_id="user",
            metadata={
                "chatbot_id": chatbot_id,
                "documents_count": result['documents_processed'],
                "chunks_count": result['chunks_created']
            }
        )
        
        return output
        
    except Exception as e:
        error_msg = f"Error procesando data: {str(e)}"
        audit_logger.log(
            event_type="chatbot_data_upload",
            action="error",
            resource="chatbot_mode",
            user_id="user",
            metadata={"error": str(e)}
        )
        raise gr.Error(error_msg)


def test_chatbot_query(chatbot_id: str, question: str):
    """Prueba una consulta al chatbot."""
    if not chatbot_id or not chatbot_id.strip():
        raise gr.Error("Ingresa el Chatbot ID.")
    
    if not question or not question.strip():
        raise gr.Error("Ingresa una pregunta.")
    
    chatbot_id = chatbot_id.strip()
    question = question.strip()
    
    try:
        response = chatbot_mode.query_chatbot(
            chatbot_id=chatbot_id,
            user_question=question,
            use_reranking=True,
            max_chunks=5
        )
        
        output = f"## 💬 Respuesta del Chatbot\n\n"
        output += f"**Pregunta:** {question}\n\n"
        output += f"**Respuesta:**\n{response.answer}\n\n"
        
        if response.sources:
            output += f"**📚 Fuentes utilizadas ({len(response.sources)}):**\n"
            for source in response.sources[:5]:
                from pathlib import Path
                clean_source = Path(source).name
                output += f"- {clean_source}\n"
            output += "\n"
        
        output += f"**Confianza:** {response.confidence:.0%}\n"
        output += f"**Chunks utilizados:** {response.chunks_used}\n"
        if response.reranked:
            output += f"**Reranking:** ✅ Activado\n"
        
        audit_logger.log(
            event_type="chatbot_query",
            action="test_query",
            resource="chatbot_mode",
            user_id="user",
            metadata={
                "chatbot_id": chatbot_id,
                "question_length": len(question),
                "chunks_used": response.chunks_used,
                "confidence": response.confidence
            }
        )
        
        return output
        
    except Exception as e:
        error_msg = f"Error consultando chatbot: {str(e)}"
        audit_logger.log(
            event_type="chatbot_query",
            action="error",
            resource="chatbot_mode",
            user_id="user",
            metadata={"error": str(e)}
        )
        raise gr.Error(error_msg)


def list_chatbots():
    """Lista todos los chatbots registrados."""
    try:
        chatbots = chatbot_mode.list_chatbots()
        
        if not chatbots:
            return "## 📋 No hay chatbots registrados\n\nRegistra un chatbot en el tab 'Registrar Chatbot'."
        
        output = f"## 📋 Chatbots Registrados: {len(chatbots)}\n\n"
        
        for chatbot in chatbots:
            output += f"### 🤖 {chatbot['chatbot_name']}\n\n"
            output += f"- **Empresa:** {chatbot['company_name']}\n"
            output += f"- **Chatbot ID:** `{chatbot['chatbot_id']}`\n"
            output += f"- **Estado:** {chatbot['status']}\n"
            output += f"- **Documentos:** {chatbot['documents_count']}\n"
            output += f"- **Chunks:** {chatbot['chunks_count']}\n\n"
        
        return output
        
    except Exception as e:
        return f"Error listando chatbots: {str(e)}"


# ==================== Funciones para Analytics ====================

def refresh_analytics_dashboard(days: int):
    """Actualiza dashboard de analytics."""
    try:
        # Obtener métricas del dashboard
        metrics = analytics_engine.get_dashboard_metrics(days=days)
        
        # Formatear dashboard
        dashboard_output = f"## 📊 Dashboard Ejecutivo - Últimos {days} días\n\n"
        dashboard_output += f"### 📈 Métricas Principales\n\n"
        dashboard_output += f"- **Total de Consultas:** {metrics['total_queries']}\n"
        dashboard_output += f"- **Consultas Exitosas:** {metrics['successful_queries']}\n"
        dashboard_output += f"- **Tasa de Éxito:** {metrics['success_rate']:.1%}\n"
        dashboard_output += f"- **Tiempo de Respuesta Promedio:** {metrics['avg_response_time']:.2f}s\n\n"
        
        # Sentimiento promedio
        sentiment = metrics.get('avg_sentiment', {})
        dashboard_output += f"### 😊 Análisis de Sentimiento\n\n"
        dashboard_output += f"- **Positivo:** {sentiment.get('positive', 0):.1%}\n"
        dashboard_output += f"- **Neutro:** {sentiment.get('neutral', 0):.1%}\n"
        dashboard_output += f"- **Negativo:** {sentiment.get('negative', 0):.1%}\n\n"
        
        # Documentos más consultados
        if metrics.get('top_documents'):
            dashboard_output += f"### 📚 Documentos Más Consultados\n\n"
            for doc in metrics['top_documents'][:5]:
                from pathlib import Path
                doc_name = Path(doc['name']).name
                dashboard_output += f"- **{doc_name}**: {doc['count']} consultas\n"
            dashboard_output += "\n"
        
        # Gaps de conocimiento
        if metrics.get('knowledge_gaps'):
            dashboard_output += f"### ⚠️ Gaps de Conocimiento Detectados\n\n"
            for gap in metrics['knowledge_gaps'][:5]:
                dashboard_output += f"- {gap[:100]}...\n"
            dashboard_output += "\n"
        
        # Preguntas frecuentes predichas
        frequent_questions = analytics_engine.predict_frequent_questions(top_n=10)
        frequent_output = f"## ❓ Preguntas Frecuentes Predichas\n\n"
        for i, fq in enumerate(frequent_questions, 1):
            frequent_output += f"{i}. **{fq['example']}** ({fq['count']} veces)\n\n"
        
        # ROI metrics
        roi_metrics = analytics_engine.get_roi_metrics()
        roi_output = f"## 💰 Métricas de ROI\n\n"
        roi_output += f"- **Consultas Totales:** {roi_metrics['total_queries']}\n"
        roi_output += f"- **Consultas Exitosas:** {roi_metrics['successful_queries']}\n"
        roi_output += f"- **Tiempo Ahorrado:** {roi_metrics['time_saved_hours']:.1f} horas\n"
        roi_output += f"- **Costo Estimado Ahorrado:** ${roi_metrics['estimated_cost_saved']:.2f}\n"
        roi_output += f"- **Ganancia de Eficiencia:** {roi_metrics['efficiency_gain']}\n"
        
        return dashboard_output, frequent_output, roi_output
        
    except Exception as e:
        error_msg = f"Error obteniendo analytics: {str(e)}"
        return f"## ❌ Error\n\n{error_msg}", "", ""


def run_autonomous_task(task_description: str, context_data: str = ""):
    """Ejecutar tarea con agente autónomo (modo legacy - mantener compatibilidad)."""
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


# Estado global para chat conversacional
chat_sessions = {}  # {session_id: {"docs": [], "retriever": None, "history": []}}

def run_chat_conversational(message, history, files, session_id, speed_mode="balanced"):
    """
    Maneja chat conversacional con documentos.
    Mantiene contexto entre preguntas y permite seguimiento.
    Formato: history debe ser una lista de dicts con 'role' y 'content' (formato messages).
    """
    if not files:
        return history, "⚠️ Primero carga documentos para comenzar el chat."
    
    # Convertir history a formato messages si viene en formato antiguo (tuplas)
    if history and isinstance(history[0], (tuple, list)) and len(history[0]) == 2:
        # Convertir de formato (user_msg, bot_msg) a formato messages
        messages_history = []
        for user_msg, bot_msg in history:
            messages_history.append({"role": "user", "content": user_msg})
            messages_history.append({"role": "assistant", "content": bot_msg})
        history = messages_history
    
    # Inicializar o recuperar sesión
    if session_id not in chat_sessions:
        chat_sessions[session_id] = {
            "docs": [],
            "retriever": None,
            "processed_files": set(),
            "history": []
        }
    
    session = chat_sessions[session_id]
    
    # Procesar nuevos archivos si hay
    new_files = []
    for file_obj in files:
        file_name = getattr(file_obj, "name", "")
        if file_name not in session["processed_files"]:
            new_files.append(file_obj)
            session["processed_files"].add(file_name)
    
    if new_files:
        try:
            print(f"📄 Procesando {len(new_files)} nuevos documentos para chat...")
            new_docs = processor.process(new_files)
            session["docs"].extend(new_docs)
            
            # Reconstruir retriever con todos los documentos
            if session["docs"]:
                session["retriever"] = retriever_builder.build_hybrid_retriever(session["docs"])
                print(f"✅ Retriever actualizado con {len(session['docs'])} chunks totales")
        except Exception as e:
            return history, f"❌ Error procesando documentos: {str(e)}"
    
    if not session["retriever"]:
        return history, "⚠️ No hay documentos procesados. Carga documentos primero."
    
    # Construir contexto de conversación desde history (formato messages)
    conversation_context = ""
    if history:
        # Incluir últimas 3 interacciones para contexto
        recent_history = history[-6:] if len(history) > 6 else history  # 3 pares user/assistant
        conversation_context = "\n\nContexto de la conversación anterior:\n"
        for msg in recent_history:
            if isinstance(msg, dict):
                role = msg.get("role", "")
                content = msg.get("content", "")
                if role == "user":
                    conversation_context += f"Usuario: {content}\n"
                elif role == "assistant":
                    conversation_context += f"Asistente: {content[:200]}...\n\n"
            elif isinstance(msg, (tuple, list)) and len(msg) == 2:
                # Formato antiguo (tupla)
                user_msg, bot_msg = msg
                conversation_context += f"Usuario: {user_msg}\n"
                conversation_context += f"Asistente: {bot_msg[:200]}...\n\n"
    
    # Enriquecer pregunta con contexto
    enriched_question = message
    if conversation_context:
        enriched_question = f"{message}\n\n{conversation_context}"
    
    # Obtener contexto de memoria si está habilitado
    memory_context = {}
    if context_manager:
        memory_context = context_manager.get_context_for_query(message)
        # Agregar contexto de sesión
        if session["history"]:
            memory_context["chat_history"] = session["history"][-5:]
    
    # Aplicar modo de velocidad temporalmente
    original_speed_mode = config.speed_mode
    config.speed_mode = speed_mode
    
    try:
        # Ejecutar workflow con contexto de conversación
        # Pasar conversational_mode=True para respuestas más libres y naturales
        result = workflow.run(
            enriched_question,
            session["retriever"],
            all_documents=session["docs"],
            conversational_mode=True  # Modo conversacional libre
        )
        
        answer = result.get("answer", result.get("draft_answer", "No se pudo generar respuesta."))
        sources = result.get("sources", [])
        
        # Formatear respuesta con fuentes
        formatted_answer = answer
        if sources:
            # Formatear fuentes (pueden ser dicts o strings)
            sources_list = []
            for s in sources[:5]:
                if isinstance(s, dict):
                    source_name = s.get("source", s.get("file", "Documento"))
                    # Extraer solo el nombre del archivo
                    from pathlib import Path
                    clean_name = Path(source_name).name
                    sources_list.append(f"- {clean_name}")
                else:
                    from pathlib import Path
                    clean_name = Path(str(s)).name
                    sources_list.append(f"- {clean_name}")
            
            if sources_list:
                formatted_answer += f"\n\n📚 **Fuentes:**\n" + "\n".join(sources_list)
        
        # Guardar en historial de sesión
        session["history"].append({
            "question": message,
            "answer": answer,
            "sources": sources,
            "timestamp": datetime.now().isoformat()
        })
        
        # Guardar en memoria persistente
        if context_manager:
            context_manager.add_query(
                query=message,
                answer=answer,
                sources=[getattr(f, "name", "") for f in files],
                metadata={
                    "mode": "chat_conversational",
                    "session_id": session_id,
                    "conversation_turn": len(session["history"])
                }
            )
        
        # Actualizar historial de Gradio en formato messages
        # Agregar mensaje del usuario
        history.append({"role": "user", "content": message})
        # Agregar respuesta del asistente
        history.append({"role": "assistant", "content": formatted_answer})
        
        return history, None
        
    except Exception as e:
        error_msg = f"❌ Error en chat: {str(e)}"
        # Agregar mensaje del usuario
        history.append({"role": "user", "content": message})
        # Agregar mensaje de error
        history.append({"role": "assistant", "content": error_msg})
        return history, None
        
    finally:
        # Restaurar modo original
        config.speed_mode = original_speed_mode

def clear_chat_session(session_id):
    """Limpia la sesión de chat."""
    if session_id in chat_sessions:
        del chat_sessions[session_id]
    return [], "✅ Chat limpiado. Puedes cargar nuevos documentos."

def run_enterprise_api_mode(files, auto_detect: bool = True, rules_json: str = ""):
    """Ejecuta modo Enterprise API con procesamiento automático (SOLO para archivos locales)."""
    if not files:
        raise gr.Error(
            "❌ No hay archivos subidos localmente.\n\n"
            "**💡 Si quieres usar archivos de Google Drive:**\n"
            "1. Ve a la sección '📁 Usar archivos de Google Drive' arriba\n"
            "2. Ingresa el Session ID\n"
            "3. Selecciona los archivos con los checkboxes\n"
            "4. Click en **'📂 Procesar Archivos Seleccionados'** (NO este botón)\n\n"
            "**O sube archivos localmente:** Arrastra archivos al campo '📂 Documentos Empresariales' arriba."
        )
    
    audit_logger.log(
        event_type="enterprise_api",
        action="process_enterprise_documents",
        resource="documents",
        user_id="user",
        metadata={"file_count": len(files), "auto_detect": auto_detect}
    )
    
    try:
        # Parsear reglas si se proporcionan
        rules = []
        if rules_json and rules_json.strip():
            try:
                rules = json.loads(rules_json)
            except:
                rules = []
        
        # Procesar con Enterprise API
        results = enterprise_api.process_enterprise_documents(
            files=files,
            auto_detect=auto_detect,
            rules=rules
        )
        
        # Formatear resultados
        output = "## 🚀 Procesamiento Enterprise API Completado\n\n"
        output += f"**Estado**: {results.get('status', 'unknown')}\n"
        output += f"**Documentos procesados**: {results.get('documents_processed', 0)}\n"
        output += f"**Chunks generados**: {results.get('chunks_generated', 0)}\n\n"
        
        # Resúmenes
        if results.get('summaries'):
            total_summaries = len(results['summaries'])
            successful_summaries = sum(1 for s in results['summaries'].values() if s.get('summary') and s.get('summary') != 'No se pudo generar resumen')
            
            output += f"### 📄 Resúmenes Automáticos ({successful_summaries}/{total_summaries} exitosos)\n\n"
            for file_name, summary in list(results['summaries'].items()):
                # Extraer solo el nombre del archivo
                from pathlib import Path
                clean_file_name = Path(file_name).name
                
                output += f"#### {clean_file_name}\n\n"
                output += f"**Tipo de Documento**: {summary.get('document_type', 'N/A')}\n\n"
                
                # Resumen completo (sin truncar)
                full_summary = summary.get('summary', 'N/A')
                output += f"**Resumen Ejecutivo**:\n{full_summary}\n\n"
                
                # Puntos clave
                if summary.get('key_points'):
                    output += f"**Puntos Clave** ({len(summary['key_points'])}):\n"
                    for i, point in enumerate(summary['key_points'][:10], 1):
                        output += f"{i}. {point}\n"
                    output += "\n"
                
                # Temas si están disponibles
                if summary.get('topics'):
                    output += f"**Temas**: {', '.join(summary['topics'][:5])}\n\n"
                
                # Valor para el negocio
                if summary.get('business_value'):
                    output += f"**Valor para el Negocio**: {summary['business_value']}\n\n"
                
                # Entidades
                if summary.get('entities'):
                    output += f"**Entidades Principales**: {', '.join(summary['entities'][:5])}\n\n"
                
                output += "---\n\n"
        
        # Problemas detectados
        if results.get('problems_detected'):
            output += "### ⚠️ Problemas Detectados\n\n"
            for problem in results['problems_detected'][:5]:
                output += f"- **{problem.get('type', 'Unknown')}** ({problem.get('severity', 'N/A')}): "
                output += f"{problem.get('description', 'N/A')[:150]}...\n"
            output += "\n"
        
        # Oportunidades
        if results.get('opportunities_detected'):
            output += "### 💡 Oportunidades Detectadas\n\n"
            for opp in results['opportunities_detected'][:5]:
                output += f"- **{opp.get('type', 'Unknown')}** ({opp.get('impact', 'N/A')}): "
                output += f"{opp.get('description', 'N/A')[:150]}...\n"
            output += "\n"
        
        # Patrones
        if results.get('patterns_found'):
            output += "### 🔍 Patrones Encontrados\n\n"
            for pattern in results['patterns_found'][:5]:
                output += f"- **{pattern.get('type', 'Unknown')}**: {pattern.get('description', 'N/A')[:150]}...\n"
            output += "\n"
        
        # Acciones ejecutadas
        if results.get('actions_taken'):
            output += "### ⚙️ Acciones Ejecutadas\n\n"
            for action in results['actions_taken']:
                output += f"- **{action.get('rule', 'Unknown')}**: {action.get('action_executed', {}).get('status', 'N/A')}\n"
            output += "\n"
        
        # Insights
        if results.get('insights'):
            output += "### 💡 Insights Generales\n\n"
            for insight in results['insights']:
                output += f"#### {insight.get('title', 'Insight')}\n"
                output += f"{insight.get('content', 'N/A')}\n\n"
        
        return output
        
    except Exception as e:
        error_msg = f"Error en modo Enterprise API: {str(e)}"
        audit_logger.log(
            event_type="error",
            action="enterprise_api",
            resource="documents",
            result="error",
            metadata={"error": str(e)}
        )
        raise gr.Error(error_msg)


def connect_s3_storage(
    bucket_name: str,
    access_key: str,
    secret_key: str,
    region: str,
    prefix: str,
    auto_process: bool
):
    """Conecta un bucket de S3 desde la UI."""
    if not bucket_name or not access_key or not secret_key:
        raise gr.Error("Por favor completa todos los campos requeridos.")
    
    try:
        result = cloud_integration.connect_s3_bucket(
            bucket_name=bucket_name,
            access_key=access_key,
            secret_key=secret_key,
            region=region or "us-east-1",
            prefix=prefix or "",
            auto_process=auto_process
        )
        
        audit_logger.log(
            event_type="cloud_connection",
            action="connect_s3_ui",
            resource="s3",
            metadata={"bucket": bucket_name}
        )
        
        output = "## ✅ Conexión S3 Exitosa\n\n"
        output += f"**Bucket**: {result.get('bucket', 'N/A')}\n"
        output += f"**Archivos encontrados**: {result.get('files_found', 0)}\n"
        
        if auto_process:
            output += f"**Archivos procesados**: {result.get('files_processed', 0)}\n"
            output += "\n✅ **Procesamiento automático activado**\n"
            output += "Los archivos se procesarán automáticamente cuando se suban al bucket.\n"
        else:
            output += "\n⚠️ **Procesamiento automático desactivado**\n"
            output += "Los archivos no se procesarán automáticamente.\n"
        
        return output
        
    except Exception as e:
        error_msg = f"Error conectando S3: {str(e)}"
        audit_logger.log(
            event_type="error",
            action="connect_s3_ui",
            resource="s3",
            result="error",
            metadata={"error": str(e)}
        )
        raise gr.Error(error_msg)


def connect_gcs_storage(
    bucket_name: str,
    credentials_json: str,
    prefix: str,
    auto_process: bool
):
    """Conecta un bucket de GCS desde la UI."""
    if not bucket_name or not credentials_json:
        raise gr.Error("Por favor completa todos los campos requeridos.")
    
    try:
        import tempfile
        import json
        
        # Validar JSON
        try:
            creds_data = json.loads(credentials_json)
        except:
            raise Exception("Las credenciales no son un JSON válido.")
        
        # Guardar temporalmente
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(creds_data, f)
            creds_path = f.name
        
        result = cloud_integration.connect_gcs_bucket(
            bucket_name=bucket_name,
            credentials_path=creds_path,
            prefix=prefix or "",
            auto_process=auto_process
        )
        
        # Limpiar
        import os
        os.unlink(creds_path)
        
        audit_logger.log(
            event_type="cloud_connection",
            action="connect_gcs_ui",
            resource="gcs",
            metadata={"bucket": bucket_name}
        )
        
        output = "## ✅ Conexión GCS Exitosa\n\n"
        output += f"**Bucket**: {result.get('bucket', 'N/A')}\n"
        output += f"**Archivos encontrados**: {result.get('files_found', 0)}\n"
        
        if auto_process:
            output += f"**Archivos procesados**: {result.get('files_processed', 0)}\n"
            output += "\n✅ **Procesamiento automático activado**\n"
        else:
            output += "\n⚠️ **Procesamiento automático desactivado**\n"
        
        return output
        
    except Exception as e:
        error_msg = f"Error conectando GCS: {str(e)}"
        audit_logger.log(
            event_type="error",
            action="connect_gcs_ui",
            resource="gcs",
            result="error",
            metadata={"error": str(e)}
        )
        raise gr.Error(error_msg)


def connect_google_drive_with_token(
    access_token: str,
    folder_id: str,
    auto_process: bool
):
    """Conecta Google Drive usando un token de acceso directo (método fácil).
    SOLO LISTA los archivos, NO los descarga automáticamente.
    """
    if not access_token or not access_token.strip():
        raise gr.Error("Por favor ingresa el Access Token de Google Drive.")
    
    try:
        # Usar el nuevo método que solo lista archivos
        result = cloud_integration.list_google_drive_files(
            access_token=access_token.strip(),
            folder_id=folder_id.strip() if folder_id else None
        )
        
        session_id = result['session_id']
        files = result['files']
        
        # Formatear lista de archivos para mostrar
        files_list = ""
        for i, file_info in enumerate(files[:50], 1):  # Mostrar primeros 50
            size_mb = file_info.get('size_mb', 0)
            files_list += f"{i}. **{file_info['name']}** ({size_mb} MB)\n"
        
        if len(files) > 50:
            files_list += f"\n... y {len(files) - 50} archivos más\n"
        
        output = f"## ✅ ¡Google Drive Conectado Exitosamente!\n\n"
        output += f"**📁 Archivos encontrados**: **{len(files)}**\n\n"
        output += f"**🔑 Session ID**: `{session_id}`\n\n"
        output += "---\n\n"
        output += "### 📋 Archivos Disponibles:\n\n"
        output += files_list
        output += "\n---\n\n"
        
        output += "**💡 IMPORTANTE - Selecciona qué archivos procesar:**\n\n"
        output += f"1. Ve al tab **'🏢 Enterprise API'**\n"
        output += f"2. En el campo **'📁 Session ID de Google Drive'**, pega:\n"
        output += f"   ```\n   {session_id}\n   ```\n"
        output += f"3. Selecciona los archivos que quieres procesar (máximo 200)\n"
        output += f"4. Click en **'📂 Procesar Archivos Seleccionados'**\n\n"
        output += "**✨ Ventajas:**\n"
        output += "- ✅ Solo descargas los archivos que seleccionas\n"
        output += "- ✅ Ahorras espacio en disco\n"
        output += "- ✅ Procesas solo lo que necesitas\n"
        output += "- ✅ Los archivos se procesan directamente desde Drive\n"
        
        audit_logger.log(
            event_type="cloud_connection",
            action="connect_google_drive_token",
            resource="google_drive",
            metadata={"session_id": session_id, "files_found": len(files)}
        )
        
        return output
        
    except Exception as e:
        error_msg = f"Error conectando Google Drive: {str(e)}"
        raise gr.Error(error_msg)

def connect_google_drive_storage(
    credentials_json: str,
    folder_id: str,
    auto_process: bool
):
    """Conecta Google Drive desde la UI y procesa archivos directamente."""
    if not credentials_json:
        raise gr.Error("Por favor proporciona las credenciales JSON de Google Drive.")
    
    try:
        result = cloud_integration.connect_google_drive(
            credentials_json=credentials_json,
            folder_id=folder_id if folder_id.strip() else None,
            auto_process=auto_process
        )
        
        audit_logger.log(
            event_type="cloud_connection",
            action="connect_google_drive_ui",
            resource="google_drive",
            metadata={"session_id": result.get('session_id'), "files_found": result.get('files_found', 0)}
        )
        
        output = "## ✅ Conexión Google Drive Exitosa\n\n"
        output += f"**Archivos encontrados**: {result.get('files_found', 0)}\n"
        output += f"**Session ID**: `{result.get('session_id', 'N/A')}`\n\n"
        
        if auto_process:
            output += f"**Archivos procesados**: {result.get('files_processed', 0)}\n"
            output += "\n✅ **Procesamiento automático completado**\n"
            output += "Los archivos han sido procesados con Enterprise API Mode.\n"
        else:
            output += "\n⚠️ **Procesamiento automático desactivado**\n"
            output += "Los archivos están listos para procesar en Enterprise API Mode.\n"
            output += f"\n💡 **Para procesar estos archivos:**\n"
            output += f"1. Ve al tab '🏢 Enterprise API'\n"
            output += f"2. Usa el botón '📂 Usar archivos de Google Drive'\n"
            output += f"3. Ingresa el Session ID: `{result.get('session_id', 'N/A')}`\n"
        
        return output
        
    except Exception as e:
        error_msg = f"Error conectando Google Drive: {str(e)}"
        audit_logger.log(
            event_type="error",
            action="connect_google_drive_ui",
            resource="google_drive",
            result="error",
            metadata={"error": str(e)}
        )
        raise gr.Error(error_msg)

def list_drive_files_for_selection(session_id: str):
    """Lista archivos de Google Drive y retorna datos para checkboxes interactivos."""
    if not session_id or not session_id.strip():
        return [], "⚠️ Por favor ingresa el Session ID de Google Drive primero."
    
    try:
        if not hasattr(cloud_integration, '_drive_sessions') or session_id.strip() not in cloud_integration._drive_sessions:
            return [], "⚠️ Session ID no encontrado. Por favor conecta Google Drive primero."
        
        session = cloud_integration._drive_sessions[session_id.strip()]
        files = session.get('files', [])
        
        if not files:
            return [], "⚠️ No se encontraron archivos en esta sesión."
        
        # Limitar a 200 archivos
        files_to_show = files[:200]
        
        # Crear lista de opciones para CheckboxGroup: "Nombre (Tamaño MB) | ID"
        file_options = []
        file_id_map = {}  # Mapeo de índice a file_id
        
        for i, file_info in enumerate(files_to_show):
            file_name = file_info.get('name', 'Sin nombre')
            size_mb = file_info.get('size_mb', 0)
            file_id = file_info.get('id', '')
            
            # Formato: "Nombre del archivo (2.5 MB)"
            display_name = f"{file_name} ({size_mb} MB)"
            file_options.append(display_name)
            file_id_map[display_name] = file_id
        
        info_text = f"## 📋 Archivos Disponibles ({len(files_to_show)}/{len(files)} archivos)\n\n"
        info_text += f"**💡 Selecciona los archivos que quieres procesar:**\n\n"
        if len(files) > 200:
            info_text += f"⚠️ Mostrando primeros 200 archivos (de {len(files)} totales)\n\n"
        info_text += "**✅ Los archivos seleccionados se procesarán automáticamente**\n"
        
        return file_options, info_text
        
    except Exception as e:
        return [], f"❌ Error: {str(e)}"

def convert_selected_files_to_ids(selected_files: list, session_id: str):
    """Convierte los nombres de archivos seleccionados a sus IDs."""
    if not selected_files or not session_id:
        return ""
    
    try:
        if not hasattr(cloud_integration, '_drive_sessions') or session_id.strip() not in cloud_integration._drive_sessions:
            return ""
        
        session = cloud_integration._drive_sessions[session_id.strip()]
        files = session.get('files', [])[:200]  # Limitar a 200
        
        # Crear mapeo de nombre a ID
        name_to_id = {}
        for file_info in files:
            file_name = file_info.get('name', 'Sin nombre')
            size_mb = file_info.get('size_mb', 0)
            file_id = file_info.get('id', '')
            display_name = f"{file_name} ({size_mb} MB)"
            name_to_id[display_name] = file_id
        
        # Convertir nombres seleccionados a IDs
        selected_ids = []
        for selected in selected_files:
            if selected in name_to_id:
                selected_ids.append(name_to_id[selected])
        
        return ", ".join(selected_ids)
        
    except Exception as e:
        print(f"Error convirtiendo archivos seleccionados: {e}")
        return ""

def use_drive_files_in_enterprise(
    session_id: str, 
    selected_file_ids: str = "",
    auto_detect: bool = True, 
    rules_json: str = ""
):
    """Usa archivos de Google Drive conectados en Enterprise API Mode.
    
    Args:
        session_id: Session ID de Google Drive
        selected_file_ids: IDs de archivos seleccionados (separados por comas). Si está vacío, procesa todos (máx 200)
        auto_detect: Si activar detección automática
        rules_json: Reglas de automatización en JSON
    """
    if not session_id or not session_id.strip():
        raise gr.Error(
            "❌ Por favor ingresa el Session ID de Google Drive.\n\n"
            "**💡 Cómo obtener el Session ID:**\n"
            "1. Ve al tab '☁️ Cloud Storage' → '📁 Google Drive'\n"
            "2. Conecta tu Google Drive con el token\n"
            "3. Copia el Session ID que aparece (ej: `drive_20241122_163132`)\n"
            "4. Pégalo en el campo de arriba"
        )
    
    try:
        print(f"\n{'='*60}")
        print(f"🚀 INICIANDO PROCESAMIENTO DE GOOGLE DRIVE")
        print(f"{'='*60}\n")
        
        # Parsear IDs seleccionados
        file_ids_list = None
        if selected_file_ids and selected_file_ids.strip():
            # Separar por comas y limpiar espacios
            file_ids_list = [fid.strip() for fid in selected_file_ids.strip().split(',') if fid.strip()]
            print(f"📋 Archivos seleccionados: {len(file_ids_list)} archivos")
        else:
            print(f"📋 Procesando todos los archivos disponibles (máximo 200)")
        
        print(f"🔑 Session ID: {session_id.strip()}\n")
        
        # Obtener archivos de Drive (solo los seleccionados si hay selección)
        print(f"📥 Descargando archivos desde Google Drive...")
        drive_files = cloud_integration.get_drive_files_for_enterprise(
            session_id.strip(),
            selected_file_ids=file_ids_list
        )
        
        print(f"✅ {len(drive_files)} archivos descargados exitosamente\n")
        
        if not drive_files:
            raise gr.Error(
                f"No se encontraron archivos para procesar.\n"
                f"Verifica que:\n"
                f"1. El Session ID sea correcto\n"
                f"2. Hayas conectado Google Drive primero\n"
                f"3. Los IDs de archivos seleccionados sean válidos (si especificaste algunos)"
            )
        
        # Parsear reglas
        rules = []
        if rules_json and rules_json.strip():
            try:
                rules = json.loads(rules_json)
            except:
                rules = []
        
        # Procesar con Enterprise API
        results = enterprise_api.process_enterprise_documents(
            files=drive_files,
            auto_detect=auto_detect,
            rules=rules
        )
        
        # Formatear resultados (igual que run_enterprise_api_mode)
        output = "## 🚀 Procesamiento Enterprise API con Google Drive\n\n"
        output += f"**Estado**: {results.get('status', 'unknown')}\n"
        output += f"**Documentos procesados**: {results.get('documents_processed', 0)}\n"
        output += f"**Chunks generados**: {results.get('chunks_generated', 0)}\n\n"
        
        # Resúmenes
        if results.get('summaries'):
            total_summaries = len(results['summaries'])
            successful_summaries = sum(1 for s in results['summaries'].values() if s.get('summary') and s.get('summary') != 'No se pudo generar resumen')
            
            output += f"### 📄 Resúmenes Automáticos ({successful_summaries}/{total_summaries} exitosos)\n\n"
            for file_name, summary in list(results['summaries'].items()):
                from pathlib import Path
                clean_file_name = Path(file_name).name
                
                output += f"#### {clean_file_name}\n\n"
                output += f"**Tipo de Documento**: {summary.get('document_type', 'N/A')}\n\n"
                output += f"**Resumen Ejecutivo**:\n{summary.get('summary', 'N/A')}\n\n"
                
                if summary.get('key_points'):
                    output += f"**Puntos Clave** ({len(summary['key_points'])}):\n"
                    for i, point in enumerate(summary['key_points'][:10], 1):
                        output += f"{i}. {point}\n"
                    output += "\n"
                
                if summary.get('topics'):
                    output += f"**Temas**: {', '.join(summary['topics'][:5])}\n\n"
                
                if summary.get('business_value'):
                    output += f"**Valor para el Negocio**: {summary['business_value']}\n\n"
                
                output += "---\n\n"
        
        # Problemas, oportunidades, patrones (igual que run_enterprise_api_mode)
        if results.get('problems_detected'):
            output += "### ⚠️ Problemas Detectados\n\n"
            for problem in results['problems_detected'][:5]:
                output += f"- **{problem.get('type', 'Unknown')}** ({problem.get('severity', 'N/A')}): "
                output += f"{problem.get('description', 'N/A')[:150]}...\n"
            output += "\n"
        
        if results.get('opportunities_detected'):
            output += "### 💡 Oportunidades Detectadas\n\n"
            for opp in results['opportunities_detected'][:5]:
                output += f"- **{opp.get('type', 'Unknown')}** ({opp.get('impact', 'N/A')}): "
                output += f"{opp.get('description', 'N/A')[:150]}...\n"
            output += "\n"
        
        if results.get('patterns_found'):
            output += "### 🔍 Patrones Encontrados\n\n"
            for pattern in results['patterns_found'][:5]:
                output += f"- **{pattern.get('type', 'Unknown')}**: {pattern.get('description', 'N/A')[:150]}...\n"
            output += "\n"
        
        return output
        
    except Exception as e:
        error_msg = f"Error usando archivos de Google Drive: {str(e)}"
        raise gr.Error(error_msg)

def connect_azure_storage(
    container_name: str,
    connection_string: str,
    prefix: str,
    auto_process: bool
):
    """Conecta un contenedor de Azure desde la UI."""
    if not container_name or not connection_string:
        raise gr.Error("Por favor completa todos los campos requeridos.")
    
    try:
        result = cloud_integration.connect_azure_blob(
            container_name=container_name,
            connection_string=connection_string,
            prefix=prefix or "",
            auto_process=auto_process
        )
        
        audit_logger.log(
            event_type="cloud_connection",
            action="connect_azure_ui",
            resource="azure",
            metadata={"container": container_name}
        )
        
        output = "## ✅ Conexión Azure Exitosa\n\n"
        output += f"**Contenedor**: {result.get('container', 'N/A')}\n"
        output += f"**Archivos encontrados**: {result.get('files_found', 0)}\n"
        
        if auto_process:
            output += f"**Archivos procesados**: {result.get('files_processed', 0)}\n"
            output += "\n✅ **Procesamiento automático activado**\n"
        else:
            output += "\n⚠️ **Procesamiento automático desactivado**\n"
        
        return output
        
    except Exception as e:
        error_msg = f"Error conectando Azure: {str(e)}"
        audit_logger.log(
            event_type="error",
            action="connect_azure_ui",
            resource="azure",
            result="error",
            metadata={"error": str(e)}
        )
        raise gr.Error(error_msg)


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
        - 📊 Procesamiento masivo (1000+ documentos)
        - 🏢 Enterprise API Mode (Procesamiento automático con Agentic AI)
        - 🔒 Auditoría y seguridad
        """
    )
    
    # Verificar espacio en disco al inicio y mostrar advertencia
    disk_warning_shown = False
    try:
        import shutil
        import psutil
        disk_usage = shutil.disk_usage(".")
        free_space_gb = disk_usage.free / (1024 * 1024 * 1024)
        
        if free_space_gb < 1:
            disk_warning_shown = True
            gr.Markdown(
                f"""
                ## ⚠️ ADVERTENCIA CRÍTICA: Espacio en Disco Muy Bajo
                
                **Espacio libre actual**: {free_space_gb:.2f} GB
                
                **Problema**: No hay suficiente espacio para subir archivos. Gradio necesita espacio temporal.
                
                **Solución inmediata**:
                1. Ejecuta `LIMPIAR_TEMPORALES.ps1` en PowerShell para liberar espacio
                2. O libera espacio manualmente en:
                   - `C:\\Users\\Random\\AppData\\Local\\Temp\\gradio`
                   - Papelera de reciclaje
                   - Archivos temporales de Windows
                
                **Recomendación**: Necesitas al menos **2-3 GB libres** para procesar PDFs.
                
                **💡 Alternativa**: Usa Google Drive desde el tab "☁️ Cloud Storage" para procesar archivos sin ocupar espacio local.
                """,
                visible=True
            )
        elif free_space_gb < 2:
            gr.Markdown(
                f"""
                ⚠️ **Advertencia**: Espacio en disco bajo ({free_space_gb:.2f} GB libre).
                Para procesar muchos PDFs se recomienda al menos 2-3 GB libres.
                Ejecuta `LIMPIAR_TEMPORALES.ps1` si necesitas más espacio.
                """,
                visible=True
            )
    except Exception as e:
        print(f"Advertencia: No se pudo verificar espacio en disco: {e}")
    
    with gr.Tabs():
        # Tab 1: RAG Principal
        with gr.Tab("🔍 Consulta RAG"):
            gr.Markdown("### Consulta estándar con verificación multi-agente")
            gr.Markdown("💡 **SOPORTA HASTA 1000 DOCUMENTOS** - Procesa grandes volúmenes con análisis inteligente")
            
            # Advertencia sobre espacio en disco
            try:
                import shutil
                disk_usage = shutil.disk_usage(".")
                free_space_gb = disk_usage.free / (1024 * 1024 * 1024)
                if free_space_gb < 2:
                    gr.Markdown(
                        f"⚠️ **ADVERTENCIA**: Espacio en disco bajo ({free_space_gb:.2f} GB libre). "
                        f"Para procesar muchos PDFs necesitas al menos 2-3 GB libres. "
                        f"Ejecuta `LIMPIAR_TEMPORALES.ps1` para liberar espacio."
                    )
            except:
                pass
            
            with gr.Row():
                file_input = gr.Files(
                    label="📂 Documentos (PDF, DOCX, TXT, MD) - Hasta 1000 documentos",
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
                speed_mode = gr.Radio(
                    label="⚡ Modo de Velocidad",
                    choices=[
                        ("🚀 Rápido (2-3x más rápido, respuestas concisas)", "fast"),
                        ("⚖️ Balanceado (recomendado)", "balanced"),
                        ("🎯 Máxima Calidad (más lento, análisis profundo)", "quality")
                    ],
                    value="balanced",
                    info="Rápido: menos chunks, respuestas más concisas. Balanceado: equilibrio velocidad/calidad. Máxima Calidad: análisis más profundo."
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
                inputs=[file_input, question_input, use_memory_check, speed_mode],
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
        
        # Tab 3: Agentes Autónomos (Enterprise Agentic AI con IDP)
        with gr.Tab("🤖 Agentes Autónomos"):
            gr.Markdown("### 🤖 Enterprise Agentic AI con Intelligent Document Processing (IDP)")
            gr.Markdown("""
            **🚀 Funcionalidades:**
            - Sube todos tus datos empresariales (hasta 1000 documentos)
            - Procesamiento IDP automático: extrae información estructurada de documentos
            - Conecta tu Agentic AI por API a tu empresa
            - Ejecuta 50+ tareas autónomas usando tus datos procesados
            
            **📋 Tipos de tareas soportadas:**
            - Análisis de datos y generación de insights
            - Automatización de procesos empresariales
            - Integración con sistemas externos (CRM, ERP, etc.)
            - Generación de contenido, informes y presentaciones
            - Optimización de procesos y recursos
            - **Marketing y Advertising:** Campañas publicitarias, optimización automática, generación de creativos
            - **Sales:** Gestión de leads, outreach personalizado, seguimiento automático
            - **Email Marketing:** Campañas automatizadas, personalización, lead nurturing
            """)
            
            with gr.Row():
                with gr.Column(scale=1):
                    gr.Markdown("### 📂 Paso 1: Subir Datos Empresariales")
                    agentic_files = gr.File(
                        label="📄 Documentos Empresariales (PDF, DOCX, TXT, MD)",
                        file_count="multiple",
                        file_types=[".pdf", ".docx", ".txt", ".md"]
                    )
                    
                    process_idp_btn = gr.Button("🔍 Procesar con IDP", variant="primary")
                    idp_status = gr.Markdown(label="📊 Estado IDP")
                
                with gr.Column(scale=1):
                    gr.Markdown("### 🤖 Paso 2: Ejecutar Tareas Autónomas")
                    
                    task_type = gr.Dropdown(
                        label="Tipo de Tarea",
                        choices=[
                            "análisis",
                            "automatización",
                            "integración",
                            "generación",
                            "optimización"
                        ],
                        value="análisis"
                    )
                    
                    task_input = gr.Textbox(
                        label="📝 Descripción de la tarea",
                        placeholder="Ejemplo: Analizar los datos y generar un reporte de ventas con las métricas clave",
                        lines=4,
                    )
                    
                    context_input = gr.Textbox(
                        label="📋 Contexto adicional (JSON opcional)",
                        placeholder='{"recipient": "juan@empresa.com", "format": "excel", "priority": "high"}',
                        lines=3,
                    )
                    
                    execute_task_btn = gr.Button("🚀 Ejecutar Tarea Autónoma", variant="primary")
            
            with gr.Row():
                agent_output = gr.Markdown(label="📊 Resultado de Tarea")
            
            with gr.Row():
                gr.Markdown("### 🔌 Conexión API")
                gr.Markdown("""
                **Para conectar tu Agentic AI por API:**
                1. Inicia el servidor API: `python api_server.py` o `python INICIAR_API.py`
                2. Usa los endpoints `/api/v1/agentic-ai/process-idp` y `/api/v1/agentic-ai/execute-task`
                3. Autentica con tu API key en el header: `Authorization: Bearer YOUR_API_KEY`
                
                **Endpoints disponibles:**
                - `POST /api/v1/agentic-ai/process-idp`: Procesa documentos con IDP
                - `POST /api/v1/agentic-ai/execute-task`: Ejecuta tarea autónoma
                - `GET /api/v1/agentic-ai/idp-summary`: Obtiene resumen de documentos procesados
                """)
            
            # Event handlers
            process_idp_btn.click(
                fn=run_idp_processing,
                inputs=[agentic_files],
                outputs=[idp_status]
            )
            
            execute_task_btn.click(
                fn=run_enterprise_agentic_task,
                inputs=[task_input, task_type, context_input],
                outputs=[agent_output]
            )
        
        # Tab 4.5: Enterprise API Mode (NUEVO)
        with gr.Tab("🏢 Enterprise API"):
            gr.Markdown("### Modo Enterprise API - Procesamiento Automático con Agentic AI")
            gr.Markdown("""
            **🚀 Funcionalidades:**
            - Procesa documentos automáticamente (igual que Consulta RAG)
            - Detecta problemas, oportunidades y patrones sin que se lo pidas
            - Genera resúmenes automáticos de cada documento
            - Ejecuta acciones según reglas personalizadas
            - Aprende y mejora continuamente
            
            **💼 Perfecto para empresas que necesitan:**
            - Procesar contratos, emails, documentos masivamente
            - Detección automática de riesgos y oportunidades
            - Automatización de workflows empresariales
            """)
            
            gr.Markdown("""
            **💡 NUEVO: Usa archivos de Google Drive sin descargarlos**
            
            Si tienes archivos en Google Drive, conéctalos desde el tab "☁️ Cloud Storage" → "📁 Google Drive"
            y luego úsalos aquí con el botón de abajo.
            """)
            
            with gr.Row():
                enterprise_files = gr.Files(
                    label="📂 Documentos Empresariales (PDF, DOCX, TXT, MD, Emails) - O usa Google Drive abajo",
                    file_count="multiple",
                    file_types=[".pdf", ".docx", ".txt", ".md"],
                )
            
            with gr.Row():
                rules_input = gr.Textbox(
                    label="⚙️ Reglas y Automatizaciones (JSON opcional)",
                    placeholder='''[
  {
    "name": "Alerta de Contrato Vencido",
    "type": "condition",
    "condition": {
      "type": "keyword",
      "keyword": "vencimiento"
    },
    "action": {
      "type": "notify",
      "channel": "email"
    }
  }
]''',
                    lines=8,
                )
            
            with gr.Row():
                with gr.Column():
                    drive_session_id = gr.Textbox(
                        label="📁 Usar archivos de Google Drive (Session ID)",
                        placeholder="Pega el Session ID que obtuviste al conectar Google Drive",
                        info="Obtén el Session ID desde el tab '☁️ Cloud Storage' → '📁 Google Drive'",
                    )
                    list_drive_files_btn = gr.Button("📋 Listar Archivos Disponibles", variant="secondary")
                    
                    drive_files_info = gr.Markdown(
                        label="ℹ️ Información",
                        value="**💡 Instrucciones:**\n\n1. Ingresa el Session ID arriba\n2. Click en 'Listar Archivos Disponibles'\n3. Selecciona los archivos que quieres procesar (aparecerán checkboxes)\n4. Los IDs se llenarán automáticamente\n5. Click en 'Procesar Archivos Seleccionados'"
                    )
                    
                    drive_files_checkboxes = gr.CheckboxGroup(
                        label="📋 Selecciona Archivos para Procesar",
                        choices=[],
                        value=[],
                        interactive=True,
                        visible=False,
                        info="Marca los archivos que quieres procesar. Los IDs se actualizarán automáticamente.",
                    )
                    
                    selected_file_ids = gr.Textbox(
                        label="📝 IDs de Archivos Seleccionados (se llena automáticamente)",
                        placeholder="Los IDs aparecerán aquí cuando selecciones archivos arriba",
                        info="Este campo se llena automáticamente cuando seleccionas archivos. También puedes editarlo manualmente.",
                        lines=2,
                        interactive=True,
                    )
                    
                    use_drive_btn = gr.Button(
                        "📂 Procesar Archivos Seleccionados de Google Drive", 
                        variant="primary", 
                        size="lg",
                        elem_id="drive_process_btn"
                    )
                
                with gr.Column():
                    auto_detect_check = gr.Checkbox(
                        label="🔍 Detección Automática (Problemas, Oportunidades, Patrones)",
                        value=True,
                    )
            
            drive_enterprise_output = gr.Markdown(
                label="📊 Resultados desde Google Drive",
                value="**💡 Instrucciones:**\n\n1. ✅ Selecciona archivos de Google Drive arriba con los checkboxes\n2. ✅ Los IDs se llenarán automáticamente\n3. ✅ Click en **'📂 Procesar Archivos Seleccionados'** (el botón verde arriba)\n4. ⚠️ **NO uses el botón 'Procesar con Enterprise API' de abajo** (ese es SOLO para archivos locales)"
            )
            
            gr.Markdown("---\n\n**⚠️ IMPORTANTE:** El botón de abajo es **SOLO para archivos subidos localmente**. Para Google Drive usa el botón **'📂 Procesar Archivos Seleccionados'** de arriba.\n")
            
            enterprise_button = gr.Button("🚀 Procesar con Enterprise API (Archivos Locales)", variant="secondary", size="lg")
            
            enterprise_output = gr.Markdown(label="📊 Resultados Enterprise API (Archivos Locales)")
            
            # Función para actualizar checkboxes cuando se seleccionan archivos
            def update_file_ids(selected_files, session_id):
                """Actualiza el campo de IDs cuando se seleccionan archivos."""
                ids = convert_selected_files_to_ids(selected_files, session_id)
                return ids
            
            # Botón para listar archivos
            def load_drive_files(session_id):
                """Carga archivos y muestra checkboxes."""
                file_options, info_text = list_drive_files_for_selection(session_id)
                if file_options:
                    return (
                        gr.update(choices=file_options, value=[], visible=True, interactive=True),
                        gr.update(value=info_text, visible=True),
                        gr.update(value="")  # Limpiar IDs
                    )
                else:
                    return (
                        gr.update(choices=[], value=[], visible=False),
                        gr.update(value=info_text, visible=True),
                        gr.update(value="")
                    )
            
            list_drive_files_btn.click(
                fn=load_drive_files,
                inputs=[drive_session_id],
                outputs=[drive_files_checkboxes, drive_files_info, selected_file_ids],
            )
            
            # Actualizar IDs automáticamente cuando se seleccionan archivos
            drive_files_checkboxes.change(
                fn=update_file_ids,
                inputs=[drive_files_checkboxes, drive_session_id],
                outputs=[selected_file_ids],
            )
            
            use_drive_btn.click(
                fn=use_drive_files_in_enterprise,
                inputs=[drive_session_id, selected_file_ids, auto_detect_check, rules_input],
                outputs=[drive_enterprise_output],
            )
            
            enterprise_button.click(
                fn=run_enterprise_api_mode,
                inputs=[enterprise_files, auto_detect_check, rules_input],
                outputs=[enterprise_output],
            )
        
        # Tab 4.6: Atención al Cliente Automática (NUEVO)
        with gr.Tab("🎧 Atención al Cliente 24/7"):
            gr.Markdown("### Agentic AI para Atención al Cliente Automática")
            gr.Markdown("""
            **🚀 Soporte 24/7 Automático con Agentic AI**
            
            - 📧 Responde automáticamente emails, WhatsApp, mensajes
            - 🤖 Resuelve consultas de forma autónoma usando tu base de conocimiento
            - 🎫 Gestiona tickets automáticamente
            - 📊 Escala a humanos solo cuando es necesario
            - 💬 Soporte multi-canal (email, WhatsApp, chat)
            
            **💼 Perfecto para:**
            - Empresas que necesitan soporte 24/7
            - Reducir costos operativos de atención al cliente
            - Mejorar tiempos de respuesta
            - Escalar sin aumentar personal
            """)
            
            with gr.Tabs():
                with gr.Tab("📚 Cargar Base de Conocimiento"):
                    gr.Markdown("""
                    **Carga documentos que el AI usará para responder consultas de clientes:**
                    - Manuales de producto
                    - FAQs y políticas
                    - Documentación técnica
                    - Información de la empresa
                    """)
                    
                    cs_knowledge_files = gr.Files(
                        label="📂 Documentos para Base de Conocimiento (PDF, DOCX, TXT, MD)",
                        file_count="multiple",
                        file_types=[".pdf", ".docx", ".txt", ".md"],
                    )
                    
                    load_knowledge_btn = gr.Button("📚 Cargar Base de Conocimiento", variant="primary")
                    knowledge_status = gr.Markdown("")
                    
                    def load_cs_knowledge(files):
                        if not customer_service_agent:
                            return "❌ Customer Service Agent no está habilitado. Configura DOCCHAT_ENABLE_AGENTS=true"
                        
                        if not files:
                            return "⚠️ Por favor, sube al menos un documento para la base de conocimiento."
                        
                        try:
                            customer_service_agent.load_knowledge_base(files)
                            stats = customer_service_agent.get_stats()
                            return f"✅ Base de conocimiento cargada exitosamente!\n\n📊 Documentos en base: {stats['knowledge_base_documents']} chunks"
                        except Exception as e:
                            return f"❌ Error cargando base de conocimiento: {str(e)}"
                    
                    load_knowledge_btn.click(
                        fn=load_cs_knowledge,
                        inputs=[cs_knowledge_files],
                        outputs=[knowledge_status]
                    )
                
                with gr.Tab("📧 Procesar Consulta"):
                    gr.Markdown("""
                    **Simula una consulta de cliente y recibe respuesta automática:**
                    """)
                    
                    with gr.Row():
                        cs_channel = gr.Dropdown(
                            label="📱 Canal de Comunicación",
                            choices=["email", "whatsapp", "chat"],
                            value="email",
                            interactive=True
                        )
                    
                    with gr.Row():
                        cs_customer_email = gr.Textbox(
                            label="📧 Email del Cliente",
                            placeholder="cliente@ejemplo.com",
                            value="cliente@ejemplo.com"
                        )
                    
                    with gr.Row():
                        cs_customer_phone = gr.Textbox(
                            label="📱 Teléfono (opcional, para WhatsApp)",
                            placeholder="+1234567890",
                            value=""
                        )
                    
                    with gr.Row():
                        cs_subject = gr.Textbox(
                            label="📝 Asunto (opcional, para emails)",
                            placeholder="Consulta sobre producto",
                            value=""
                        )
                    
                    with gr.Row():
                        cs_message = gr.Textbox(
                            label="💬 Mensaje del Cliente",
                            placeholder="Hola, tengo una pregunta sobre...",
                            lines=5
                        )
                    
                    process_inquiry_btn = gr.Button("🚀 Procesar Consulta", variant="primary")
                    cs_response_output = gr.Markdown("")
                    
                    def process_customer_inquiry(channel, email, phone, subject, message):
                        if not customer_service_agent:
                            return "❌ Customer Service Agent no está habilitado. Configura DOCCHAT_ENABLE_AGENTS=true"
                        
                        if not message or not message.strip():
                            return "⚠️ Por favor, ingresa un mensaje del cliente."
                        
                        if not email or not email.strip():
                            return "⚠️ Por favor, ingresa el email del cliente."
                        
                        try:
                            response = customer_service_agent.process_inquiry(
                                channel=channel,
                                customer_email=email,
                                message=message,
                                customer_phone=phone if phone else None,
                                subject=subject if subject else None,
                                use_knowledge_base=True
                            )
                            
                            output = f"""
## ✅ Consulta Procesada

**ID de Consulta:** {response.inquiry_id}

### 📤 Respuesta Generada:
{response.response_text}

### 📊 Detalles:
- **Canal:** {response.channel}
- **Enviada:** {'✅ Sí' if response.sent else '❌ No'}
- **Ticket Creado:** {'✅ Sí' if response.ticket_created else '❌ No'}
- **Ticket ID:** {response.ticket_id or 'N/A'}
- **Confianza:** {response.confidence:.1%}
- **Escalado:** {'⚠️ Sí' if response.escalated else '✅ No'}
- **Herramientas Usadas:** {', '.join(response.tools_used) if response.tools_used else 'Ninguna'}
"""
                            return output
                        except Exception as e:
                            import traceback
                            traceback.print_exc()
                            return f"❌ Error procesando consulta: {str(e)}"
                    
                    process_inquiry_btn.click(
                        fn=process_customer_inquiry,
                        inputs=[cs_channel, cs_customer_email, cs_customer_phone, cs_subject, cs_message],
                        outputs=[cs_response_output]
                    )
                
                with gr.Tab("📊 Estadísticas"):
                    gr.Markdown("""
                    **Estadísticas del servicio de atención al cliente:**
                    """)
                    
                    cs_stats_output = gr.Markdown("")
                    refresh_stats_btn = gr.Button("🔄 Actualizar Estadísticas", variant="secondary")
                    
                    def get_cs_stats():
                        if not customer_service_agent:
                            return "❌ Customer Service Agent no está habilitado."
                        
                        try:
                            stats = customer_service_agent.get_stats()
                            return f"""
## 📊 Estadísticas de Atención al Cliente

### 📈 Métricas Generales:
- **Total de Consultas:** {stats['total_inquiries']}
- **Resueltas Autónomamente:** {stats['resolved_autonomously']}
- **Escaladas a Humanos:** {stats['escalated']}
- **Tickets Creados:** {stats['tickets_created']}

### 📊 Tasas:
- **Tasa de Resolución:** {stats['resolution_rate']}
- **Tasa de Escalación:** {stats['escalation_rate']}

### 📚 Base de Conocimiento:
- **Documentos Cargados:** {stats['knowledge_base_documents']} chunks
"""
                        except Exception as e:
                            return f"❌ Error obteniendo estadísticas: {str(e)}"
                    
                    refresh_stats_btn.click(
                        fn=get_cs_stats,
                        outputs=[cs_stats_output]
                    )
                    
                    # Cargar estadísticas iniciales
                    cs_stats_output.value = get_cs_stats()
                
                with gr.Tab("🤖 Reglas Automáticas"):
                    gr.Markdown("""
                    ### 🤖 Configurar Respuestas Automáticas en Tiempo Real
                    
                    **Programa respuestas automáticas que se ejecutan cuando llegan mensajes:**
                    
                    - ✅ **Respuesta Fija**: Siempre responde lo mismo (ej: "Gracias por contactarnos")
                    - ✅ **Por Palabra Clave**: Responde cuando el mensaje contiene ciertas palabras
                    - ✅ **Por Patrón**: Responde cuando el mensaje coincide con un patrón (regex)
                    - ✅ **Siempre**: Responde automáticamente a todos los mensajes
                    
                    **Ejemplo:** Si alguien escribe "hola" en WhatsApp, siempre responder "¡Hola! ¿En qué puedo ayudarte?"
                    """)
                    
                    with gr.Row():
                        with gr.Column(scale=1):
                            rule_name = gr.Textbox(
                                label="📝 Nombre de la Regla",
                                placeholder="Ej: Saludo automático",
                                value=""
                            )
                            
                            rule_channel = gr.Dropdown(
                                label="📱 Canal",
                                choices=["whatsapp", "email", "chat", "all"],
                                value="whatsapp",
                                info="Selecciona el canal donde aplicará esta regla"
                            )
                            
                            rule_trigger_type = gr.Dropdown(
                                label="🎯 Tipo de Trigger",
                                choices=[
                                    ("Siempre", "always"),
                                    ("Palabra Clave", "keyword"),
                                    ("Patrón (Regex)", "pattern"),
                                    ("AI Detection", "ai_detection")
                                ],
                                value="keyword",
                                info="Cómo detectar cuándo aplicar esta regla"
                            )
                            
                            rule_trigger_value = gr.Textbox(
                                label="🔍 Valor del Trigger",
                                placeholder='Ej: hola,hola,buenos días (para keyword) o regex para pattern',
                                value="",
                                info="Palabras clave separadas por comas, o patrón regex"
                            )
                            
                            rule_response_type = gr.Dropdown(
                                label="💬 Tipo de Respuesta",
                                choices=[
                                    ("Respuesta Fija", "fixed"),
                                    ("Template con Variables", "template"),
                                    ("Generada por AI", "ai_generated")
                                ],
                                value="fixed",
                                info="Tipo de respuesta a generar"
                            )
                            
                            rule_response_content = gr.Textbox(
                                label="📝 Contenido de la Respuesta",
                                placeholder="Ej: ¡Hola! Gracias por contactarnos. ¿En qué puedo ayudarte?",
                                lines=5,
                                value=""
                            )
                            
                            rule_priority = gr.Slider(
                                label="⭐ Prioridad",
                                minimum=0,
                                maximum=10,
                                value=5,
                                step=1,
                                info="Mayor prioridad = se ejecuta primero si hay múltiples reglas"
                            )
                            
                            create_rule_btn = gr.Button("✅ Crear Regla", variant="primary")
                            rule_status = gr.Markdown("")
                        
                        with gr.Column(scale=1):
                            gr.Markdown("### 📋 Reglas Existentes")
                            
                            rules_list = gr.Dataframe(
                                label="Reglas Configuradas",
                                headers=["ID", "Nombre", "Canal", "Trigger", "Estado", "Uso"],
                                interactive=False,
                                wrap=True
                            )
                            
                            refresh_rules_btn = gr.Button("🔄 Actualizar Lista", variant="secondary")
                            
                            gr.Markdown("### 🗑️ Eliminar Regla")
                            delete_rule_id = gr.Textbox(
                                label="ID de Regla a Eliminar",
                                placeholder="RULE-1234567890-0",
                                value=""
                            )
                            delete_rule_btn = gr.Button("🗑️ Eliminar", variant="stop")
                            
                            rules_stats = gr.Markdown("")
                    
                    def create_auto_rule(name, channel, trigger_type, trigger_value, response_type, response_content, priority):
                        if not customer_service_agent:
                            return "❌ Customer Service Agent no está habilitado.", None, ""
                        
                        if not name or not trigger_value or not response_content:
                            return "⚠️ Completa todos los campos requeridos.", None, ""
                        
                        try:
                            rule = customer_service_agent.auto_response_manager.add_rule(
                                name=name,
                                channel=channel,
                                trigger_type=trigger_type,
                                trigger_value=trigger_value,
                                response_type=response_type,
                                response_content=response_content,
                                priority=int(priority)
                            )
                            
                            return f"✅ Regla '{name}' creada exitosamente!\n\n**ID:** {rule.rule_id}", None, ""
                        except Exception as e:
                            return f"❌ Error creando regla: {str(e)}", None, ""
                    
                    def refresh_rules_list():
                        if not customer_service_agent:
                            return None, "❌ Customer Service Agent no está habilitado."
                        
                        try:
                            rules = customer_service_agent.auto_response_manager.get_all_rules()
                            
                            if not rules:
                                return None, "📝 No hay reglas configuradas aún."
                            
                            data = []
                            for rule in rules:
                                status = "✅ Activa" if rule.enabled else "❌ Desactivada"
                                data.append([
                                    rule.rule_id[:20] + "...",
                                    rule.name,
                                    rule.channel,
                                    f"{rule.trigger_type}: {rule.trigger_value[:30]}",
                                    status,
                                    str(rule.usage_count)
                                ])
                            
                            stats = customer_service_agent.auto_response_manager.get_stats()
                            stats_text = f"""
### 📊 Estadísticas de Reglas:
- **Total:** {stats['total_rules']}
- **Activas:** {stats['enabled_rules']}
- **Desactivadas:** {stats['disabled_rules']}
- **Total de Usos:** {stats['total_usage']}
"""
                            
                            return data, stats_text
                        except Exception as e:
                            return None, f"❌ Error: {str(e)}"
                    
                    def delete_rule(rule_id):
                        if not customer_service_agent:
                            return "❌ Customer Service Agent no está habilitado.", None, ""
                        
                        if not rule_id or not rule_id.strip():
                            return "⚠️ Ingresa el ID de la regla a eliminar.", None, ""
                        
                        try:
                            success = customer_service_agent.auto_response_manager.delete_rule(rule_id.strip())
                            if success:
                                return f"✅ Regla '{rule_id}' eliminada exitosamente.", None, ""
                            else:
                                return f"❌ No se encontró la regla '{rule_id}'.", None, ""
                        except Exception as e:
                            return f"❌ Error eliminando regla: {str(e)}", None, ""
                    
                    create_rule_btn.click(
                        fn=create_auto_rule,
                        inputs=[rule_name, rule_channel, rule_trigger_type, rule_trigger_value, rule_response_type, rule_response_content, rule_priority],
                        outputs=[rule_status, rules_list, rules_stats]
                    )
                    
                    refresh_rules_btn.click(
                        fn=refresh_rules_list,
                        outputs=[rules_list, rules_stats]
                    )
                    
                    delete_rule_btn.click(
                        fn=delete_rule,
                        inputs=[delete_rule_id],
                        outputs=[rule_status, rules_list, rules_stats]
                    )
                    
                    # Cargar reglas iniciales
                    initial_rules, initial_stats = refresh_rules_list()
                    if initial_rules:
                        rules_list.value = initial_rules
                    if initial_stats:
                        rules_stats.value = initial_stats
                
                with gr.Tab("🔌 API y Conexiones"):
                    gr.Markdown("""
                    ### 🔗 Conectar Canales Externos por API
                    
                    **Conecta Gmail, WhatsApp Business, Slack y otros servicios para recibir y responder mensajes automáticamente.**
                    """)
                    
                    gr.Markdown("""
                    ## 📡 Endpoints de API Disponibles
                    
                    ### 1. **Webhook para Mensajes en Tiempo Real**
                    `POST /api/v1/customer-service/webhook/{channel}`
                    
                    Recibe mensajes de clientes desde servicios externos y responde automáticamente.
                    
                    **Canales soportados:** `gmail`, `whatsapp`, `slack`, `email`, `chat`
                    
                    **Ejemplo Gmail:**
                    ```json
                    {
                      "from": "cliente@ejemplo.com",
                      "subject": "Consulta sobre producto",
                      "body": "Hola, necesito información...",
                      "message_id": "gmail_123"
                    }
                    ```
                    
                    **Ejemplo WhatsApp:**
                    ```json
                    {
                      "from": "+1234567890",
                      "message": "Hola, tengo una pregunta",
                      "message_id": "whatsapp_123"
                    }
                    ```
                    
                    ### 2. **Procesar Consulta Manual**
                    `POST /api/v1/customer-service/inquiry`
                    
                    Envía una consulta de cliente y recibe respuesta automática.
                    
                    ### 3. **Cargar Base de Conocimiento**
                    `POST /api/v1/customer-service/load-knowledge`
                    
                    Sube documentos que el AI usará para responder consultas.
                    
                    ### 4. **Estadísticas**
                    `GET /api/v1/customer-service/stats`
                    
                    Obtiene métricas del servicio de atención al cliente.
                    
                    ---
                    
                    ## 🔧 Cómo Conectar Gmail
                    
                    1. **Configura Google Cloud:**
                       - Crea proyecto en https://console.cloud.google.com
                       - Habilita Gmail API
                       - Obtén OAuth 2.0 credentials
                    
                    2. **Monitorea bandeja de entrada:**
                       - Usa IMAP o Google Cloud Pub/Sub
                       - Cuando llegue un email, envía al webhook:
                       ```python
                       import requests
                       
                       webhook_url = "https://tu-servidor.com/api/v1/customer-service/webhook/gmail"
                       payload = {
                           "from": email.from_address,
                           "subject": email.subject,
                           "body": email.body,
                           "message_id": email.id
                       }
                       
                       requests.post(webhook_url, json=payload, headers={
                           "X-Webhook-Token": "Bearer tu_token"
                       })
                       ```
                    
                    ## 📱 Cómo Conectar WhatsApp Business
                    
                    1. **Opción 1: Twilio (Recomendado para empezar)**
                       - Crea cuenta en https://www.twilio.com
                       - Configura WhatsApp Sandbox
                       - En configuración de Twilio, apunta webhook a:
                         `https://tu-servidor.com/api/v1/customer-service/webhook/whatsapp`
                       - Twilio enviará mensajes automáticamente
                    
                    2. **Opción 2: Meta WhatsApp Business API**
                       - Ve a https://developers.facebook.com
                       - Crea app de WhatsApp Business
                       - Configura webhook en Meta
                    
                    ## 💬 Cómo Conectar Slack
                    
                    1. **Crear Slack App:**
                       - Ve a https://api.slack.com/apps
                       - Crea nueva app
                       - Habilita Event Subscriptions
                    
                    2. **Configurar webhook:**
                       - URL: `https://tu-servidor.com/api/v1/customer-service/webhook/slack`
                       - Slack enviará eventos automáticamente
                    
                    ---
                    
                    ## 🔒 Seguridad
                    
                    Configura un token secreto en tu `.env`:
                    ```
                    WEBHOOK_TOKEN=tu_token_secreto_muy_seguro
                    ```
                    
                    Luego inclúyelo en los headers:
                    ```
                    X-Webhook-Token: Bearer tu_token_secreto_muy_seguro
                    ```
                    
                    ---
                    
                    ## 📚 Documentación Completa
                    
                    Consulta `CUSTOMER_SERVICE_API.md` para:
                    - Ejemplos de código completos
                    - Guías paso a paso
                    - Mejores prácticas
                    - Troubleshooting
                    """)
                    
                    api_base_url = gr.Textbox(
                        label="🌐 URL Base de tu API",
                        value="http://localhost:8000",
                        placeholder="https://tu-servidor.com",
                        interactive=True
                    )
                    
                    webhook_token = gr.Textbox(
                        label="🔑 Webhook Token (opcional)",
                        value=os.getenv("WEBHOOK_TOKEN", ""),
                        type="password",
                        placeholder="Configura WEBHOOK_TOKEN en .env",
                        interactive=False
                    )
                    
                    gr.Markdown(f"""
                    **📖 Documentación completa:** Ver archivo `CUSTOMER_SERVICE_API.md` en el proyecto.
                    
                    **🚀 Iniciar servidor API:**
                    ```bash
                    python api_server.py
                    ```
                    
                    O usa el script:
                    ```bash
                    .\\INICIAR_API.bat
                    ```
                    
                    Luego accede a la documentación interactiva en:
                    **http://localhost:8000/docs**
                    """)
        
        # Tab 4.5: Chat Conversacional (NUEVO)
        with gr.Tab("💬 Chat Conversacional"):
            gr.Markdown("### Chat Prolongado con Documentos")
            gr.Markdown("""
            **🚀 Conversación Natural con tus Documentos**
            
            - 💬 Haz preguntas de seguimiento sin repetir contexto
            - 📚 Carga documentos una vez, chatea todo lo que quieras
            - 🧠 El sistema recuerda la conversación anterior
            - 🔄 Ideal para explorar documentos en profundidad
            
            **💡 Ejemplo:** 
            - "¿Qué dice sobre X?"
            - "Y sobre Y, qué menciona?"
            - "Compara X con Y"
            """)
            
            # Generar session_id único
            chat_session_id = gr.State(value=str(uuid.uuid4()))
            
            with gr.Row():
                chat_files = gr.Files(
                    label="📂 Documentos para Chat (PDF, DOCX, TXT, MD) - Hasta 1000 documentos",
                    file_count="multiple",
                    file_types=[".pdf", ".docx", ".txt", ".md"],
                )
            
            with gr.Row():
                chat_speed_mode = gr.Radio(
                    label="⚡ Modo de Velocidad",
                    choices=[
                        ("🚀 Rápido", "fast"),
                        ("⚖️ Balanceado (recomendado)", "balanced"),
                        ("🎯 Máxima Calidad", "quality")
                    ],
                    value="balanced",
                )
            
            # Chatbot component
            chatbot = gr.Chatbot(
                label="💬 Conversación",
                height=500,
                show_copy_button=True,
                avatar_images=(None, "🤖"),
                type="messages",
            )
            
            with gr.Row():
                chat_input = gr.Textbox(
                    label="Escribe tu pregunta",
                    placeholder="Ejemplo: ¿Qué información importante hay en estos documentos?",
                    lines=2,
                    scale=4,
                )
                chat_submit_btn = gr.Button("📤 Enviar", variant="primary", scale=1)
            
            with gr.Row():
                clear_chat_btn = gr.Button("🗑️ Limpiar Chat", variant="secondary")
                clear_files_btn = gr.Button("📂 Limpiar Documentos", variant="secondary")
            
            chat_status = gr.Markdown(label="ℹ️ Estado del Chat")
            
            # Event handlers
            def chat_submit(message, history, files, session_id, speed_mode):
                if not message.strip():
                    return history, history, "⚠️ Escribe una pregunta."
                if not files:
                    return history, history, "⚠️ Primero carga documentos."
                
                new_history, error = run_chat_conversational(
                    message, history, files, session_id, speed_mode
                )
                status = f"✅ {len(new_history)} mensajes en la conversación"
                if error:
                    status = error
                return new_history, new_history, status
            
            def clear_chat(history, session_id):
                new_history, status = clear_chat_session(session_id)
                return new_history, status
            
            def clear_files(files, session_id):
                if session_id in chat_sessions:
                    chat_sessions[session_id]["processed_files"].clear()
                    chat_sessions[session_id]["docs"] = []
                    chat_sessions[session_id]["retriever"] = None
                return None, "✅ Documentos limpiados. Puedes cargar nuevos."
            
            chat_submit_btn.click(
                fn=chat_submit,
                inputs=[chat_input, chatbot, chat_files, chat_session_id, chat_speed_mode],
                outputs=[chatbot, chatbot, chat_status],
            ).then(
                lambda: "", None, chat_input
            )
            
            chat_input.submit(
                fn=chat_submit,
                inputs=[chat_input, chatbot, chat_files, chat_session_id, chat_speed_mode],
                outputs=[chatbot, chatbot, chat_status],
            ).then(
                lambda: "", None, chat_input
            )
            
            clear_chat_btn.click(
                fn=clear_chat,
                inputs=[chatbot, chat_session_id],
                outputs=[chatbot, chat_status],
            )
            
            clear_files_btn.click(
                fn=clear_files,
                inputs=[chat_files, chat_session_id],
                outputs=[chat_files, chat_status],
            )
        
        # Tab 4.7: Chatbot Mode (NUEVO - Para conectar chatbots externos)
        with gr.Tab("🤖 Chatbot"):
            gr.Markdown("### 🤖 Modo Chatbot - Conecta tu Chatbot por API")
            gr.Markdown("""
            **🚀 Funcionalidades:**
            - Conecta tu chatbot existente por API
            - Sube toda tu data privada empresarial
            - Tu chatbot usa RAG con tu data para responder consultas
            - Optimizado con chunking inteligente, reranking y prompt interno
            - Base vectorizada por chatbot
            
            **💡 Perfecto para empresas que ya tienen chatbots y quieren mejorarlos con RAG**
            """)
            
            with gr.Tabs():
                # Sub-tab: Registrar Chatbot
                with gr.Tab("📝 Registrar Chatbot"):
                    gr.Markdown("### Paso 1: Registra tu Chatbot")
                    gr.Markdown("""
                    Registra tu chatbot para obtener un `chatbot_id` y `api_key` que usarás
                    para conectar tu chatbot por API.
                    """)
                    
                    chatbot_name_input = gr.Textbox(
                        label="Nombre del Chatbot",
                        placeholder="Ej: Chatbot de Soporte Cliente"
                    )
                    
                    company_name_input = gr.Textbox(
                        label="Nombre de la Empresa",
                        placeholder="Ej: Mi Empresa S.A."
                    )
                    
                    register_chatbot_btn = gr.Button("📝 Registrar Chatbot", variant="primary")
                    chatbot_registration_output = gr.Markdown(label="📊 Información del Chatbot")
                    
                    register_chatbot_btn.click(
                        fn=register_chatbot,
                        inputs=[chatbot_name_input, company_name_input],
                        outputs=[chatbot_registration_output]
                    )
                
                # Sub-tab: Subir Data
                with gr.Tab("📂 Subir Data del Chatbot"):
                    gr.Markdown("### Paso 2: Sube la Data para tu Chatbot")
                    gr.Markdown("""
                    Sube todos los documentos que tu chatbot necesita para responder.
                    Se procesarán con chunking optimizado y se creará una base vectorizada.
                    """)
                    
                    chatbot_id_input = gr.Textbox(
                        label="Chatbot ID",
                        placeholder="Pega el chatbot_id que obtuviste al registrar"
                    )
                    
                    chatbot_files = gr.File(
                        label="📄 Documentos para el Chatbot (PDF, DOCX, TXT, MD)",
                        file_count="multiple",
                        file_types=[".pdf", ".docx", ".txt", ".md"]
                    )
                    
                    upload_chatbot_data_btn = gr.Button("📤 Subir y Procesar Data", variant="primary")
                    chatbot_data_output = gr.Markdown(label="📊 Estado del Procesamiento")
                    
                    upload_chatbot_data_btn.click(
                        fn=upload_chatbot_data,
                        inputs=[chatbot_id_input, chatbot_files],
                        outputs=[chatbot_data_output]
                    )
                
                # Sub-tab: Probar Chatbot
                with gr.Tab("💬 Probar Chatbot"):
                    gr.Markdown("### Paso 3: Prueba tu Chatbot")
                    gr.Markdown("""
                    Prueba consultas a tu chatbot para verificar que funciona correctamente
                    con la data que subiste.
                    """)
                    
                    test_chatbot_id = gr.Textbox(
                        label="Chatbot ID",
                        placeholder="Pega el chatbot_id"
                    )
                    
                    test_question = gr.Textbox(
                        label="Pregunta de Prueba",
                        placeholder="Ej: ¿Cuáles son las políticas de la empresa?",
                        lines=3
                    )
                    
                    test_chatbot_btn = gr.Button("🔍 Consultar Chatbot", variant="primary")
                    chatbot_test_output = gr.Markdown(label="📊 Respuesta del Chatbot")
                    
                    test_chatbot_btn.click(
                        fn=test_chatbot_query,
                        inputs=[test_chatbot_id, test_question],
                        outputs=[chatbot_test_output]
                    )
                
                # Sub-tab: API y Conexión
                with gr.Tab("🔌 API y Conexión"):
                    gr.Markdown("### Paso 4: Conecta tu Chatbot por API")
                    gr.Markdown("""
                    **Para conectar tu chatbot externo:**
                    
                    1. Inicia el servidor API: `python api_server.py`
                    2. Usa el endpoint: `POST /api/v1/chatbot/query`
                    3. Autentica con tu `api_key` en el header: `Authorization: Bearer YOUR_API_KEY`
                    
                    **Ejemplo de request:**
                    ```json
                    {
                        "chatbot_id": "tu-chatbot-id",
                        "question": "pregunta del usuario",
                        "use_reranking": true
                    }
                    ```
                    
                    **Ejemplo de response:**
                    ```json
                    {
                        "answer": "respuesta basada en tu data",
                        "sources": ["documento1.pdf", "documento2.pdf"],
                        "confidence": 0.95,
                        "chunks_used": 5
                    }
                    ```
                    """)
            
            with gr.Row():
                gr.Markdown("### 📋 Chatbots Registrados")
                list_chatbots_btn = gr.Button("📋 Listar Chatbots", variant="secondary")
                chatbots_list_output = gr.Markdown(label="📊 Lista de Chatbots")
                
                list_chatbots_btn.click(
                    fn=list_chatbots,
                    inputs=[],
                    outputs=[chatbots_list_output]
                )
        
        # Tab 4.7: Automatización RPA (NUEVO)
        with gr.Tab("🤖 Automatización RPA"):
            gr.Markdown("### Automatización de Procesos con RPA + IA")
            gr.Markdown("""
            **🚀 Automatiza tareas repetitivas empresariales con Agentic AI**
            
            - 💰 **Finanzas**: Facturación, conciliación, pagos, impuestos, auditoría, cuentas
            - 👥 **RRHH**: Reclutamiento, onboarding, nómina, ausencias, evaluaciones
            - 📦 **Logística**: Inventario, envíos, rutas, órdenes de compra, facturación transporte
            - 📢 **Marketing**: Leads, campañas, seguimiento, precios, análisis comportamiento
            - 🏥 **Salud**: Registros médicos, citas, reclamaciones, diagnóstico, monitoreo
            - 🏭 **Manufactura**: Mantenimiento predictivo, calidad, producción, proveedores, productividad
            - 🔒 **TI**: Seguridad, contraseñas, anomalías, backups
            - ⚖️ **Legal**: Contratos, documentos, cumplimiento, investigación
            - 📊 **Proyectos**: Gestión, reportes, recursos, alertas
            - 🎓 **Educación**: Evaluaciones, contenidos, inscripciones, progreso
            - 💬 **Comunicaciones**: Emails, agendas, transcripciones
            
            **💡 Perfecto para empresas que quieren automatizar procesos complejos sin intervención humana**
            """)
            
            with gr.Tabs():
                with gr.Tab("🎯 Ejecutar Automatización"):
                    gr.Markdown("### Selecciona una categoría y tipo de automatización")
                    
                    with gr.Row():
                        with gr.Column(scale=1):
                            rpa_category = gr.Dropdown(
                                label="📂 Categoría",
                                choices=[
                                    ("💰 Finanzas y Contabilidad", "finanzas"),
                                    ("👥 Recursos Humanos", "rrhh"),
                                    ("📦 Logística y Cadena de Suministro", "logistica"),
                                    ("📢 Marketing y Ventas", "marketing"),
                                    ("🏥 Salud", "salud"),
                                    ("🏭 Industria y Manufactura", "manufactura"),
                                    ("🔒 TI y Seguridad", "ti_seguridad"),
                                    ("⚖️ Legal", "legal"),
                                    ("📊 Gestión de Proyectos", "gestion_proyectos"),
                                    ("🎓 Educación", "educacion"),
                                    ("💬 Comunicaciones", "comunicaciones")
                                ],
                                value="finanzas",
                                info="Selecciona el área de automatización"
                            )
                            
                            rpa_task_type = gr.Dropdown(
                                label="⚙️ Tipo de Tarea",
                                choices=[],
                                value=None,
                                info="Selecciona la tarea específica a automatizar"
                            )
                            
                            rpa_parameters = gr.Textbox(
                                label="📝 Parámetros (JSON)",
                                placeholder='{"parametro1": "valor1", "parametro2": "valor2"}',
                                lines=10,
                                value="{}",
                                info="Ingresa los parámetros necesarios en formato JSON"
                            )
                            
                            rpa_documents = gr.Files(
                                label="📄 Documentos de Entrada (Opcional)",
                                file_count="multiple",
                                file_types=[".pdf", ".docx", ".txt", ".json", ".csv"]
                            )
                            
                            execute_rpa_btn = gr.Button("🚀 Ejecutar Automatización", variant="primary", size="lg")
                        
                        with gr.Column(scale=1):
                            rpa_output = gr.Markdown("")
                            rpa_execution_time = gr.Markdown("")
                    
                    def update_task_types(category):
                        """Actualiza los tipos de tarea según la categoría seleccionada."""
                        if not rpa_engine:
                            return gr.Dropdown(choices=[], value=None)
                        
                        categories = rpa_engine.get_available_categories()
                        category_data = next((c for c in categories if c["category"] == category), None)
                        
                        if category_data:
                            choices = [(task["name"], task["id"]) for task in category_data["tasks"]]
                            return gr.Dropdown(choices=choices, value=choices[0][1] if choices else None)
                        return gr.Dropdown(choices=[], value=None)
                    
                    def execute_rpa_automation(category, task_type, parameters_json, documents):
                        """Ejecuta una automatización RPA."""
                        if not rpa_engine:
                            return "❌ RPA Engine no está habilitado. Configura DOCCHAT_ENABLE_AGENTS=true", ""
                        
                        if not category or not task_type:
                            return "⚠️ Por favor, selecciona una categoría y tipo de tarea.", ""
                        
                        try:
                            # Parsear parámetros JSON
                            try:
                                parameters = json.loads(parameters_json) if parameters_json.strip() else {}
                            except json.JSONDecodeError:
                                return "❌ Error: Los parámetros deben estar en formato JSON válido.", ""
                            
                            # Procesar documentos si hay
                            docs = None
                            if documents:
                                from docchat.document_processor import DocumentProcessor
                                processor = DocumentProcessor(rpa_engine.config)
                                docs = processor.process(documents)
                            
                            # Ejecutar automatización
                            result = rpa_engine.execute_automation(
                                category=category,
                                task_type=task_type,
                                parameters=parameters,
                                documents=docs
                            )
                            
                            # Formatear salida
                            output = f"""
## ✅ Automatización Completada

**ID:** {result.automation_id}
**Categoría:** {result.category}
**Tipo:** {result.task_type}
**Estado:** {'✅ Éxito' if result.success else '❌ Error'}
**Tiempo de Ejecución:** {result.execution_time:.2f} segundos

### 📊 Resultado:
```json
{json.dumps(result.data, indent=2, ensure_ascii=False)}
```

### 💬 Mensaje:
{result.message}

### 🔧 Herramientas Usadas:
{', '.join(result.tools_used) if result.tools_used else 'Ninguna'}
"""
                            
                            time_info = f"⏱️ **Tiempo de ejecución:** {result.execution_time:.2f} segundos"
                            
                            return output, time_info
                        
                        except Exception as e:
                            import traceback
                            traceback.print_exc()
                            return f"❌ Error ejecutando automatización: {str(e)}", ""
                    
                    rpa_category.change(
                        fn=update_task_types,
                        inputs=[rpa_category],
                        outputs=[rpa_task_type]
                    )
                    
                    execute_rpa_btn.click(
                        fn=execute_rpa_automation,
                        inputs=[rpa_category, rpa_task_type, rpa_parameters, rpa_documents],
                        outputs=[rpa_output, rpa_execution_time]
                    )
                    
                    # Cargar tipos de tarea iniciales
                    if rpa_engine:
                        initial_tasks = update_task_types("finanzas")
                        if hasattr(initial_tasks, 'choices') and initial_tasks.choices:
                            rpa_task_type.choices = initial_tasks.choices
                            rpa_task_type.value = initial_tasks.value
                
                with gr.Tab("📋 Categorías Disponibles"):
                    gr.Markdown("### Todas las Categorías y Tareas de Automatización")
                    
                    categories_info = gr.Markdown("")
                    
                    def load_categories_info():
                        if not rpa_engine:
                            return "❌ RPA Engine no está habilitado."
                        
                        categories = rpa_engine.get_available_categories()
                        
                        info = "## 📚 Categorías de Automatización RPA\n\n"
                        
                        for cat in categories:
                            info += f"### {cat['name']}\n\n"
                            info += f"**Categoría ID:** `{cat['category']}`\n\n"
                            info += "**Tareas disponibles:**\n"
                            for task in cat['tasks']:
                                info += f"- **{task['name']}** (ID: `{task['id']}`)\n"
                            info += "\n---\n\n"
                        
                        return info
                    
                    if rpa_engine:
                        categories_info.value = load_categories_info()
                    else:
                        categories_info.value = "❌ RPA Engine no está habilitado."
                
                with gr.Tab("📊 Estadísticas"):
                    gr.Markdown("### Estadísticas de Automatizaciones RPA")
                    
                    rpa_stats_output = gr.Markdown("")
                    refresh_rpa_stats_btn = gr.Button("🔄 Actualizar Estadísticas", variant="secondary")
                    
                    def get_rpa_stats():
                        if not rpa_engine:
                            return "❌ RPA Engine no está habilitado."
                        
                        try:
                            stats = rpa_engine.get_stats()
                            
                            return f"""
## 📊 Estadísticas de Automatización RPA

### 📈 Métricas Generales:
- **Total de Tareas:** {stats['total_tasks']}
- **Completadas:** {stats['completed_tasks']}
- **Fallidas:** {stats['failed_tasks']}
- **Tasa de Éxito:** {stats.get('success_rate', 0):.1f}%
- **Tiempo Promedio:** {stats.get('average_execution_time', 0):.2f} segundos

### 📂 Por Categoría:
{chr(10).join([f"- **{cat}**: {count} tareas" for cat, count in stats.get('by_category', {}).items()]) if stats.get('by_category') else "Ninguna"}

### 📊 Total de Automatizaciones:
- **Ejecutadas:** {stats.get('total_automations', 0)}
"""
                        except Exception as e:
                            return f"❌ Error obteniendo estadísticas: {str(e)}"
                    
                    refresh_rpa_stats_btn.click(
                        fn=get_rpa_stats,
                        outputs=[rpa_stats_output]
                    )
                    
                    if rpa_engine:
                        rpa_stats_output.value = get_rpa_stats()
                    else:
                        rpa_stats_output.value = "❌ RPA Engine no está habilitado."
                
                with gr.Tab("🔌 API y Conexiones Enterprise"):
                    gr.Markdown("### Conecta tu Sistema Enterprise por API")
                    gr.Markdown("""
                    **🚀 Integra tu sistema empresarial con Automatización RPA**
                    
                    Conecta tu ERP, CRM, o cualquier sistema empresarial para que los Agentic AI procesen datos automáticamente en tiempo real.
                    
                    **Características:**
                    - 📡 **Webhooks en Tiempo Real**: Recibe datos de tu empresa automáticamente
                    - 🤖 **Procesamiento Automático**: Los Agentic AI procesan datos sin intervención
                    - 🔄 **Integración Continua**: Datos fluyen automáticamente desde tu sistema
                    - 📊 **Monitoreo en Tiempo Real**: Ve el estado de todas las automatizaciones
                    """)
                    
                    with gr.Row():
                        with gr.Column(scale=1):
                            gr.Markdown("### 📝 Registrar Conexión Enterprise")
                            
                            enterprise_name = gr.Textbox(
                                label="🏢 Nombre de la Empresa/App",
                                placeholder="Mi Empresa S.A.",
                                value=""
                            )
                            
                            enterprise_api_key = gr.Textbox(
                                label="🔑 API Key (se generará automáticamente)",
                                value="",
                                interactive=False
                            )
                            
                            enterprise_webhook_url = gr.Textbox(
                                label="📡 Webhook URL de tu Sistema",
                                placeholder="https://tu-sistema.com/webhook",
                                value="",
                                info="URL donde tu sistema enviará datos en tiempo real"
                            )
                            
                            enterprise_categories = gr.CheckboxGroup(
                                label="📂 Categorías de Automatización",
                                choices=[
                                    "Finanzas",
                                    "RRHH",
                                    "Logística",
                                    "Marketing",
                                    "Salud",
                                    "Manufactura",
                                    "TI y Seguridad",
                                    "Legal",
                                    "Gestión de Proyectos",
                                    "Educación",
                                    "Comunicaciones"
                                ],
                                value=[],
                                info="Selecciona las categorías que tu empresa usará"
                            )
                            
                            register_enterprise_btn = gr.Button("✅ Registrar Conexión Enterprise", variant="primary")
                            enterprise_status = gr.Markdown("")
                        
                        with gr.Column(scale=1):
                            gr.Markdown("### 📋 Conexiones Registradas")
                            
                            enterprise_connections = gr.Dataframe(
                                label="Conexiones Activas",
                                headers=["Empresa", "Enterprise ID", "Estado", "Total Requests", "Éxito"],
                                interactive=False,
                                wrap=True
                            )
                            
                            refresh_connections_btn = gr.Button("🔄 Actualizar Lista", variant="secondary")
                            
                            def refresh_connections_list():
                                """Actualiza la lista de conexiones."""
                                if not rpa_enterprise:
                                    return None, "❌ RPA Enterprise Integration no está habilitado."
                                
                                try:
                                    connections = rpa_enterprise.get_all_connections()
                                    
                                    if not connections:
                                        return None, "📝 No hay conexiones registradas aún."
                                    
                                    data = []
                                    for conn in connections:
                                        success_rate = (
                                            (conn.get("successful_automations", 0) / conn.get("total_requests", 1) * 100)
                                            if conn.get("total_requests", 0) > 0 else 0
                                        )
                                        data.append([
                                            conn.get("name", ""),
                                            conn.get("enterprise_id", "")[:20] + "...",
                                            "✅ Activa" if conn.get("status") == "active" else "⏸️ Pausada",
                                            str(conn.get("total_requests", 0)),
                                            f"{success_rate:.1f}%"
                                        ])
                                    
                                    return data, f"✅ {len(connections)} conexiones encontradas"
                                except Exception as e:
                                    return None, f"❌ Error: {str(e)}"
                            
                            refresh_connections_btn.click(
                                fn=refresh_connections_list,
                                outputs=[enterprise_connections, enterprise_status]
                            )
                            
                            # Cargar conexiones iniciales
                            if rpa_enterprise:
                                initial_data, initial_msg = refresh_connections_list()
                                if initial_data:
                                    enterprise_connections.value = initial_data
                            
                            gr.Markdown("### 📡 Endpoint de Webhook")
                            webhook_endpoint_info = gr.Markdown("""
                            **URL del Webhook para recibir datos:**
                            
                            ```
                            POST http://tu-servidor:8000/api/v1/rpa/webhook/{enterprise_id}
                            ```
                            
                            **Headers requeridos:**
                            - `X-API-Key`: Tu API Key
                            - `Content-Type`: application/json
                            
                            **Body (JSON):**
                            ```json
                            {
                              "category": "finanzas",
                              "task_type": "generar_factura",
                              "data": {
                                "parametro1": "valor1",
                                "parametro2": "valor2"
                              }
                            }
                            ```
                            """)
                    
                    def register_enterprise_connection(name, webhook_url, categories):
                        """Registra una nueva conexión enterprise."""
                        if not rpa_enterprise:
                            return "❌ RPA Enterprise Integration no está habilitado.", None, ""
                        
                        if not name or not name.strip():
                            return "⚠️ Ingresa el nombre de la empresa.", None, ""
                        
                        try:
                            # Registrar conexión
                            connection = rpa_enterprise.register_enterprise_connection(
                                name=name,
                                webhook_url=webhook_url if webhook_url else None,
                                categories=categories if categories else None
                            )
                            
                            status_msg = f"""
✅ **Conexión registrada exitosamente!**

**Enterprise ID:** `{connection.enterprise_id}`
**API Key:** `{connection.api_key}`

⚠️ **IMPORTANTE:** Guarda esta API Key de forma segura. No se mostrará nuevamente.

**Endpoint de Webhook:**
```
POST http://tu-servidor:8000/api/v1/rpa/webhook/{connection.enterprise_id}
Headers:
  X-API-Key: {connection.api_key}
  Content-Type: application/json

Body:
{{
  "category": "finanzas",
  "task_type": "generar_factura",
  "data": {{ ... }}
}}
```
"""
                            
                            return status_msg, None, connection.api_key
                        except Exception as e:
                            return f"❌ Error registrando conexión: {str(e)}", None, ""
                    
                    register_enterprise_btn.click(
                        fn=register_enterprise_connection,
                        inputs=[enterprise_name, enterprise_webhook_url, enterprise_categories],
                        outputs=[enterprise_status, enterprise_connections, enterprise_api_key]
                    )
                
                with gr.Tab("📖 Guía y Ejemplos"):
                    gr.Markdown("""
                    ### 📖 Guía de Uso de Automatización RPA
                    
                    ## 🎯 Cómo Usar
                    
                    1. **Selecciona una Categoría** (ej: Finanzas, RRHH, Logística)
                    2. **Selecciona un Tipo de Tarea** (se actualiza automáticamente)
                    3. **Ingresa los Parámetros** en formato JSON
                    4. **Opcionalmente sube Documentos** relacionados
                    5. **Ejecuta** y recibe el resultado automáticamente
                    
                    ## 💰 Ejemplo: Finanzas - Generar Factura
                    
                    **Parámetros:**
                    ```json
                    {
                      "orden_compra": "OC-12345",
                      "cliente": {
                        "nombre": "Empresa ABC",
                        "email": "contacto@empresaabc.com",
                        "direccion": "Calle 123"
                      },
                      "items": [
                        {"descripcion": "Producto A", "cantidad": 2, "precio": 100},
                        {"descripcion": "Producto B", "cantidad": 1, "precio": 200}
                      ]
                    }
                    ```
                    
                    ## 👥 Ejemplo: RRHH - Filtrar CVs
                    
                    **Parámetros:**
                    ```json
                    {
                      "cvs": [
                        {
                          "nombre": "Juan Pérez",
                          "contenido": "Ingeniero con 5 años de experiencia en Python, SQL, Machine Learning..."
                        }
                      ],
                      "requisitos": {
                        "experiencia_minima": 3,
                        "educacion": "universitaria",
                        "habilidades": ["Python", "SQL", "Machine Learning"]
                      }
                    }
                    ```
                    
                    ## 📦 Ejemplo: Logística - Gestión de Inventario
                    
                    **Parámetros:**
                    ```json
                    {
                      "productos": [
                        {"id": "PROD-001", "nombre": "Producto A", "stock": 5, "stock_maximo": 100, "proveedor": "Proveedor X"},
                        {"id": "PROD-002", "nombre": "Producto B", "stock": 15, "stock_maximo": 50, "proveedor": "Proveedor Y"}
                      ],
                      "umbral_minimo": 10
                    }
                    ```
                    
                    ## 🏥 Ejemplo: Salud - Gestión de Citas
                    
                    **Parámetros:**
                    ```json
                    {
                      "solicitudes": [
                        {
                          "paciente": "María García",
                          "fecha_preferida": "2025-01-25T10:00:00",
                          "tipo": "consulta"
                        }
                      ],
                      "doctores": [
                        {"id": "DOC-001", "nombre": "Dr. López", "especialidad": "General"}
                      ]
                    }
                    ```
                    
                    ## ⚖️ Ejemplo: Legal - Revisar Contrato
                    
                    **Parámetros:**
                    ```json
                    {
                      "contrato": "Texto del contrato aquí..."
                    }
                    ```
                    
                    O sube un documento PDF/DOCX con el contrato.
                    
                    ## 🔒 Ejemplo: TI - Gestión de Contraseñas
                    
                    **Parámetros:**
                    ```json
                    {
                      "sistemas": [
                        {"nombre": "Sistema ERP", "usuario": "admin"},
                        {"nombre": "Sistema CRM", "usuario": "admin"}
                      ],
                      "longitud": 16
                    }
                    ```
                    
                    ---
                    
                    **💡 Tip:** Consulta la documentación completa en `GUIA_RPA_AUTOMATION.md`
                    """)
        
        # Tab 4.8: Analytics y Dashboard (NUEVO)
        with gr.Tab("📊 Analytics y Dashboard"):
            gr.Markdown("### 📊 Analytics y Business Intelligence")
            gr.Markdown("""
            **🚀 Métricas y Insights en Tiempo Real:**
            - Dashboard ejecutivo con métricas de uso
            - Análisis de sentimiento en consultas
            - Detección de gaps de conocimiento
            - Predicción de preguntas frecuentes
            - ROI calculator
            - Performance metrics
            """)
            
            with gr.Row():
                with gr.Column(scale=1):
                    analytics_days = gr.Slider(
                        label="Período de Análisis (días)",
                        minimum=1,
                        maximum=90,
                        value=30,
                        step=1
                    )
                    refresh_analytics_btn = gr.Button("🔄 Actualizar Analytics", variant="primary")
                
                with gr.Column(scale=2):
                    analytics_output = gr.Markdown(label="📊 Dashboard Ejecutivo")
            
            with gr.Row():
                with gr.Column():
                    frequent_questions_output = gr.Markdown(label="❓ Preguntas Frecuentes Predichas")
                
                with gr.Column():
                    roi_output = gr.Markdown(label="💰 Métricas de ROI")
            
            refresh_analytics_btn.click(
                fn=refresh_analytics_dashboard,
                inputs=[analytics_days],
                outputs=[analytics_output, frequent_questions_output, roi_output]
            )
        
        # Tab 4.6: Cloud Storage Integration (NUEVO)
        with gr.Tab("☁️ Cloud Storage"):
            gr.Markdown("### Conecta tu Cloud Storage para Procesamiento Automático")
            gr.Markdown("""
            **🚀 Conecta S3, Google Cloud Storage o Azure Blob Storage**
            
            - Sube archivos a tu cloud storage
            - Se procesan automáticamente
            - Detecta problemas y oportunidades
            - Genera resúmenes ejecutivos
            
            **💡 Perfecto para empresas que tienen datos en la nube**
            """)
            
            with gr.Tabs():
                # Sub-tab: AWS S3
                with gr.Tab("📦 AWS S3"):
                    gr.Markdown("### Conectar Bucket de AWS S3")
                    
                    with gr.Row():
                        with gr.Column():
                            s3_bucket = gr.Textbox(
                                label="Nombre del Bucket",
                                placeholder="mi-bucket-empresa",
                            )
                            s3_access_key = gr.Textbox(
                                label="AWS Access Key",
                                type="password",
                                placeholder="AKIAIOSFODNN7EXAMPLE",
                            )
                            s3_secret_key = gr.Textbox(
                                label="AWS Secret Key",
                                type="password",
                                placeholder="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
                            )
                            s3_region = gr.Textbox(
                                label="Región",
                                value="us-east-1",
                                placeholder="us-east-1",
                            )
                            s3_prefix = gr.Textbox(
                                label="Prefijo (opcional)",
                                placeholder="documentos/",
                                info="Solo procesa archivos en esta carpeta",
                            )
                            s3_auto_process = gr.Checkbox(
                                label="Procesar archivos automáticamente",
                                value=True,
                            )
                            s3_connect_btn = gr.Button("🔗 Conectar S3", variant="primary")
                    
                    s3_output = gr.Markdown(label="📊 Resultado de Conexión")
                    
                    s3_connect_btn.click(
                        fn=connect_s3_storage,
                        inputs=[s3_bucket, s3_access_key, s3_secret_key, s3_region, s3_prefix, s3_auto_process],
                        outputs=[s3_output],
                    )
                
                # Sub-tab: Google Drive (NUEVO - LA MEJOR OPCIÓN)
                with gr.Tab("📁 Google Drive (Recomendado)"):
                    gr.Markdown("### Conectar Google Drive")
                    gr.Markdown("""
                    **🚀 LA MEJOR OPCIÓN - Procesa archivos directamente sin descargarlos**
                    
                    - ✅ Conecta tu Google Drive
                    - ✅ Procesa hasta 200 PDFs sin ocupar espacio en tu PC
                    - ✅ Los archivos se procesan directamente desde Drive
                    - ✅ Perfecto para Enterprise API Mode
                    """)
                    
                    with gr.Tabs():
                        # Opción 1: Método fácil (Token directo)
                        with gr.Tab("🔑 Método Fácil (Recomendado)"):
                            gr.Markdown("""
                            ### ✨ Conectar Google Drive en 3 Pasos Simples
                            
                            **Paso 1:** Click en el botón azul de abajo → Se abre OAuth Playground
                            
                            **Paso 2:** 
                            - Marca: `https://www.googleapis.com/auth/drive.readonly`
                            - Click en "Authorize APIs"
                            - Inicia sesión con Google
                            - Click en "Exchange authorization code for tokens"
                            
                            **Paso 3:** Copia el "Access token" y pégalo abajo → Click en "Conectar"
                            """)
                            
                            # Botón para abrir OAuth Playground
                            oauth_link = gr.Markdown("""
                            <div style="text-align: center; margin: 20px 0;">
                                <a href="https://developers.google.com/oauthplayground/" target="_blank" style="text-decoration: none;">
                                    <button style="background-color: #4285F4; color: white; padding: 20px 40px; font-size: 18px; font-weight: bold; border: none; border-radius: 8px; cursor: pointer; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                                        🔗 Abrir OAuth Playground (Click Aquí)
                                    </button>
                                </a>
                            </div>
                            """)
                            
                            gr.Markdown("""
                            **💡 Tip:** El token empieza con `ya29.` y es largo (más de 100 caracteres)
                            """)
                            
                            with gr.Row():
                                with gr.Column():
                                    drive_access_token = gr.Textbox(
                                        label="🔑 Pega aquí el Access Token",
                                        placeholder="ya29.a0AfH6SMC...",
                                        type="password",
                                        info="Copia el token desde OAuth Playground (paso 6 arriba)",
                                    )
                                    
                                    with gr.Accordion("⚙️ Opciones Avanzadas (Opcional)", open=False):
                                        drive_folder_id_easy = gr.Textbox(
                                            label="ID de Carpeta específica (opcional)",
                                            placeholder="1ABC123xyz...",
                                            info="Deja vacío para procesar todo 'My Drive'",
                                        )
                                    drive_auto_process_easy = gr.Checkbox(
                                        label="Procesar automáticamente al conectar",
                                        value=False,
                                        info="⚠️ DESACTIVADO por defecto - Primero lista los archivos y selecciona cuáles procesar"
                                    )
                                    
                                    drive_connect_easy_btn = gr.Button("✅ Conectar Google Drive", variant="primary", size="lg")
                            
                            drive_output_easy = gr.Markdown(
                                label="📊 Resultado",
                                value="**Esperando conexión...**\n\n1. Click en el botón de arriba para abrir OAuth Playground\n2. Sigue los pasos\n3. Pega el token y click en 'Conectar Google Drive'"
                            )
                            
                            drive_connect_easy_btn.click(
                                fn=lambda token, folder, auto: connect_google_drive_with_token(token, folder, auto),
                                inputs=[drive_access_token, drive_folder_id_easy, drive_auto_process_easy],
                                outputs=[drive_output_easy],
                            )
                        
                        # Opción 2: Método completo (OAuth completo)
                        with gr.Tab("⚙️ Método Completo (OAuth)"):
                            gr.Markdown("""
                            **📋 Cómo obtener credenciales:**
                            1. Ve a [Google Cloud Console](https://console.cloud.google.com/)
                            2. Crea un proyecto o selecciona uno existente
                            3. Habilita "Google Drive API"
                            4. Crea credenciales OAuth 2.0 (tipo "Aplicación de escritorio")
                            5. Descarga el JSON de credenciales
                            6. Agrega estas URIs de redirección: `http://localhost:8080`, `http://127.0.0.1:8080`
                            """)
                            
                            with gr.Row():
                                with gr.Column():
                                    drive_credentials = gr.Textbox(
                                        label="Credenciales JSON de Google Drive",
                                        placeholder='{"web": {"client_id": "...", "client_secret": "...", ...}}',
                                        lines=8,
                                        info="Pega el contenido completo del archivo JSON de credenciales",
                                    )
                                    drive_folder_id = gr.Textbox(
                                        label="ID de Carpeta (opcional)",
                                        placeholder="1ABC123xyz...",
                                        info="Deja vacío para procesar todo 'My Drive'",
                                    )
                                    drive_auto_process = gr.Checkbox(
                                        label="Procesar automáticamente al conectar",
                                        value=True,
                                    )
                                    drive_connect_btn = gr.Button("🔗 Conectar Google Drive", variant="primary", size="lg")
                            
                            drive_output = gr.Markdown(label="📊 Resultado de Conexión")
                            
                            drive_connect_btn.click(
                                fn=connect_google_drive_storage,
                                inputs=[drive_credentials, drive_folder_id, drive_auto_process],
                                outputs=[drive_output],
                            )
                    
                    drive_connect_btn.click(
                        fn=connect_google_drive_storage,
                        inputs=[drive_credentials, drive_folder_id, drive_auto_process],
                        outputs=[drive_output],
                    )
                
                # Sub-tab: Google Cloud Storage
                with gr.Tab("📦 Google Cloud Storage"):
                    gr.Markdown("### Conectar Bucket de Google Cloud Storage")
                    
                    with gr.Row():
                        with gr.Column():
                            gcs_bucket = gr.Textbox(
                                label="Nombre del Bucket",
                                placeholder="mi-bucket-gcs",
                            )
                            gcs_credentials = gr.Textbox(
                                label="Credenciales JSON",
                                placeholder='{"type": "service_account", ...}',
                                lines=5,
                                info="Pega el contenido completo del archivo JSON de credenciales",
                            )
                            gcs_prefix = gr.Textbox(
                                label="Prefijo (opcional)",
                                placeholder="documentos/",
                            )
                            gcs_auto_process = gr.Checkbox(
                                label="Procesar archivos automáticamente",
                                value=True,
                            )
                            gcs_connect_btn = gr.Button("🔗 Conectar GCS", variant="primary")
                    
                    gcs_output = gr.Markdown(label="📊 Resultado de Conexión")
                    
                    gcs_connect_btn.click(
                        fn=connect_gcs_storage,
                        inputs=[gcs_bucket, gcs_credentials, gcs_prefix, gcs_auto_process],
                        outputs=[gcs_output],
                    )
                
                # Sub-tab: Azure Blob Storage
                with gr.Tab("📦 Azure Blob Storage"):
                    gr.Markdown("### Conectar Contenedor de Azure Blob Storage")
                    
                    with gr.Row():
                        with gr.Column():
                            azure_container = gr.Textbox(
                                label="Nombre del Contenedor",
                                placeholder="mi-contenedor",
                            )
                            azure_connection_string = gr.Textbox(
                                label="Connection String",
                                type="password",
                                placeholder="DefaultEndpointsProtocol=https;AccountName=...",
                            )
                            azure_prefix = gr.Textbox(
                                label="Prefijo (opcional)",
                                placeholder="documentos/",
                            )
                            azure_auto_process = gr.Checkbox(
                                label="Procesar archivos automáticamente",
                                value=True,
                            )
                            azure_connect_btn = gr.Button("🔗 Conectar Azure", variant="primary")
                    
                    azure_output = gr.Markdown(label="📊 Resultado de Conexión")
                    
                    azure_connect_btn.click(
                        fn=connect_azure_storage,
                        inputs=[azure_container, azure_connection_string, azure_prefix, azure_auto_process],
                        outputs=[azure_output],
                    )
                
                # Sub-tab: Webhooks
                with gr.Tab("🔔 Webhooks"):
                    gr.Markdown("### Configurar Webhooks para Procesamiento en Tiempo Real")
                    gr.Markdown("""
                    **📋 Instrucciones:**
                    
                    1. Configura un webhook en tu cloud storage
                    2. Cuando se suba un archivo, se procesará automáticamente
                    3. El endpoint es: `http://tu-servidor:8000/api/v1/cloud/webhook/{source}`
                    
                    **Fuentes soportadas:** `s3`, `gcs`, `azure`
                    """)
                    
                    webhook_info = gr.Markdown("""
                    ### 📍 Endpoint de Webhook
                    
                    **URL Base:** `http://tu-servidor:8000/api/v1/cloud/webhook/`
                    
                    **Ejemplos:**
                    - S3: `http://tu-servidor:8000/api/v1/cloud/webhook/s3`
                    - GCS: `http://tu-servidor:8000/api/v1/cloud/webhook/gcs`
                    - Azure: `http://tu-servidor:8000/api/v1/cloud/webhook/azure`
                    
                    **Configuración en AWS S3:**
                    1. Ve a tu bucket → Properties → Event notifications
                    2. Crea nueva notificación
                    3. Event type: `s3:ObjectCreated:*`
                    4. Destination: HTTP/HTTPS endpoint
                    5. URL: `http://tu-servidor:8000/api/v1/cloud/webhook/s3`
                    """)
        
        # Tab 4.8: Automatización RPA - Movido arriba, eliminar duplicado
            gr.Markdown("### Automatización de Procesos con RPA + IA")
            gr.Markdown("""
            **🚀 Automatiza tareas repetitivas empresariales con Agentic AI**
            
            - 💰 **Finanzas**: Facturación, conciliación, pagos, impuestos, auditoría, cuentas
            - 👥 **RRHH**: Reclutamiento, onboarding, nómina, ausencias, evaluaciones
            - 📦 **Logística**: Inventario, envíos, rutas, órdenes de compra, facturación transporte
            - 📢 **Marketing**: Leads, campañas, seguimiento, precios, análisis comportamiento
            - 🏥 **Salud**: Registros médicos, citas, reclamaciones, diagnóstico, monitoreo
            - 🏭 **Manufactura**: Mantenimiento predictivo, calidad, producción, proveedores, productividad
            - 🔒 **TI**: Seguridad, contraseñas, anomalías, backups
            - ⚖️ **Legal**: Contratos, documentos, cumplimiento, investigación
            - 📊 **Proyectos**: Gestión, reportes, recursos, alertas
            - 🎓 **Educación**: Evaluaciones, contenidos, inscripciones, progreso
            - 💬 **Comunicaciones**: Emails, agendas, transcripciones
            
            **💡 Perfecto para empresas que quieren automatizar procesos complejos sin intervención humana**
            """)
            
            with gr.Tabs():
                with gr.Tab("🎯 Ejecutar Automatización"):
                    gr.Markdown("### Selecciona una categoría y tipo de automatización")
                    
                    with gr.Row():
                        with gr.Column(scale=1):
                            rpa_category = gr.Dropdown(
                                label="📂 Categoría",
                                choices=[
                                    ("💰 Finanzas y Contabilidad", "finanzas"),
                                    ("👥 Recursos Humanos", "rrhh"),
                                    ("📦 Logística y Cadena de Suministro", "logistica"),
                                    ("📢 Marketing y Ventas", "marketing"),
                                    ("🏥 Salud", "salud"),
                                    ("🏭 Industria y Manufactura", "manufactura"),
                                    ("🔒 TI y Seguridad", "ti_seguridad"),
                                    ("⚖️ Legal", "legal"),
                                    ("📊 Gestión de Proyectos", "gestion_proyectos"),
                                    ("🎓 Educación", "educacion"),
                                    ("💬 Comunicaciones", "comunicaciones")
                                ],
                                value="finanzas",
                                info="Selecciona el área de automatización"
                            )
                            
                            rpa_task_type = gr.Dropdown(
                                label="⚙️ Tipo de Tarea",
                                choices=[],
                                value=None,
                                info="Selecciona la tarea específica a automatizar"
                            )
                            
                            rpa_parameters = gr.Textbox(
                                label="📝 Parámetros (JSON)",
                                placeholder='{"parametro1": "valor1", "parametro2": "valor2"}',
                                lines=10,
                                value="{}",
                                info="Ingresa los parámetros necesarios en formato JSON"
                            )
                            
                            rpa_documents = gr.Files(
                                label="📄 Documentos de Entrada (Opcional)",
                                file_count="multiple",
                                file_types=[".pdf", ".docx", ".txt", ".json", ".csv"]
                            )
                            
                            execute_rpa_btn = gr.Button("🚀 Ejecutar Automatización", variant="primary", size="lg")
                        
                        with gr.Column(scale=1):
                            rpa_output = gr.Markdown("")
                            rpa_execution_time = gr.Markdown("")
                    
                    def update_task_types(category):
                        """Actualiza los tipos de tarea según la categoría seleccionada."""
                        if not rpa_engine:
                            return gr.Dropdown(choices=[], value=None)
                        
                        categories = rpa_engine.get_available_categories()
                        category_data = next((c for c in categories if c["category"] == category), None)
                        
                        if category_data:
                            choices = [(task["name"], task["id"]) for task in category_data["tasks"]]
                            return gr.Dropdown(choices=choices, value=choices[0][1] if choices else None)
                        return gr.Dropdown(choices=[], value=None)
                    
                    def execute_rpa_automation(category, task_type, parameters_json, documents):
                        """Ejecuta una automatización RPA."""
                        if not rpa_engine:
                            return "❌ RPA Engine no está habilitado. Configura DOCCHAT_ENABLE_AGENTS=true", ""
                        
                        if not category or not task_type:
                            return "⚠️ Por favor, selecciona una categoría y tipo de tarea.", ""
                        
                        try:
                            # Parsear parámetros JSON
                            try:
                                parameters = json.loads(parameters_json) if parameters_json.strip() else {}
                            except json.JSONDecodeError:
                                return "❌ Error: Los parámetros deben estar en formato JSON válido.", ""
                            
                            # Procesar documentos si hay
                            docs = None
                            if documents:
                                from docchat.document_processor import DocumentProcessor
                                processor = DocumentProcessor(rpa_engine.config)
                                docs = processor.process(documents)
                            
                            # Ejecutar automatización
                            result = rpa_engine.execute_automation(
                                category=category,
                                task_type=task_type,
                                parameters=parameters,
                                documents=docs
                            )
                            
                            # Formatear salida
                            output = f"""
## ✅ Automatización Completada

**ID:** {result.automation_id}
**Categoría:** {result.category}
**Tipo:** {result.task_type}
**Estado:** {'✅ Éxito' if result.success else '❌ Error'}
**Tiempo de Ejecución:** {result.execution_time:.2f} segundos

### 📊 Resultado:
```json
{json.dumps(result.data, indent=2, ensure_ascii=False)}
```

### 💬 Mensaje:
{result.message}

### 🔧 Herramientas Usadas:
{', '.join(result.tools_used) if result.tools_used else 'Ninguna'}
"""
                            
                            time_info = f"⏱️ **Tiempo de ejecución:** {result.execution_time:.2f} segundos"
                            
                            return output, time_info
                        
                        except Exception as e:
                            import traceback
                            traceback.print_exc()
                            return f"❌ Error ejecutando automatización: {str(e)}", ""
                    
                    rpa_category.change(
                        fn=update_task_types,
                        inputs=[rpa_category],
                        outputs=[rpa_task_type]
                    )
                    
                    execute_rpa_btn.click(
                        fn=execute_rpa_automation,
                        inputs=[rpa_category, rpa_task_type, rpa_parameters, rpa_documents],
                        outputs=[rpa_output, rpa_execution_time]
                    )
                    
                    # Cargar tipos de tarea iniciales
                    if rpa_engine:
                        initial_tasks = update_task_types("finanzas")
                        if hasattr(initial_tasks, 'choices') and initial_tasks.choices:
                            rpa_task_type.choices = initial_tasks.choices
                            rpa_task_type.value = initial_tasks.value
                
                with gr.Tab("📋 Categorías Disponibles"):
                    gr.Markdown("### Todas las Categorías y Tareas de Automatización")
                    
                    categories_info = gr.Markdown("")
                    
                    def load_categories_info():
                        if not rpa_engine:
                            return "❌ RPA Engine no está habilitado."
                        
                        categories = rpa_engine.get_available_categories()
                        
                        info = "## 📚 Categorías de Automatización RPA\n\n"
                        
                        for cat in categories:
                            info += f"### {cat['name']}\n\n"
                            info += f"**Categoría ID:** `{cat['category']}`\n\n"
                            info += "**Tareas disponibles:**\n"
                            for task in cat['tasks']:
                                info += f"- **{task['name']}** (ID: `{task['id']}`)\n"
                            info += "\n---\n\n"
                        
                        return info
                    
                    if rpa_engine:
                        categories_info.value = load_categories_info()
                    else:
                        categories_info.value = "❌ RPA Engine no está habilitado."
                
                with gr.Tab("📊 Estadísticas"):
                    gr.Markdown("### Estadísticas de Automatizaciones RPA")
                    
                    rpa_stats_output = gr.Markdown("")
                    refresh_rpa_stats_btn = gr.Button("🔄 Actualizar Estadísticas", variant="secondary")
                    
                    def get_rpa_stats():
                        if not rpa_engine:
                            return "❌ RPA Engine no está habilitado."
                        
                        try:
                            stats = rpa_engine.get_stats()
                            
                            return f"""
## 📊 Estadísticas de Automatización RPA

### 📈 Métricas Generales:
- **Total de Tareas:** {stats['total_tasks']}
- **Completadas:** {stats['completed_tasks']}
- **Fallidas:** {stats['failed_tasks']}
- **Tasa de Éxito:** {stats.get('success_rate', 0):.1f}%
- **Tiempo Promedio:** {stats.get('average_execution_time', 0):.2f} segundos

### 📂 Por Categoría:
{chr(10).join([f"- **{cat}**: {count} tareas" for cat, count in stats.get('by_category', {}).items()]) if stats.get('by_category') else "Ninguna"}

### 📊 Total de Automatizaciones:
- **Ejecutadas:** {stats.get('total_automations', 0)}
"""
                        except Exception as e:
                            return f"❌ Error obteniendo estadísticas: {str(e)}"
                    
                    refresh_rpa_stats_btn.click(
                        fn=get_rpa_stats,
                        outputs=[rpa_stats_output]
                    )
                    
                    if rpa_engine:
                        rpa_stats_output.value = get_rpa_stats()
                    else:
                        rpa_stats_output.value = "❌ RPA Engine no está habilitado."
                
                with gr.Tab("📖 Guía y Ejemplos"):
                    gr.Markdown("""
                    ### 📖 Guía de Uso de Automatización RPA
                    
                    ## 🎯 Cómo Usar
                    
                    1. **Selecciona una Categoría** (ej: Finanzas, RRHH, Logística)
                    2. **Selecciona un Tipo de Tarea** (se actualiza automáticamente)
                    3. **Ingresa los Parámetros** en formato JSON
                    4. **Opcionalmente sube Documentos** relacionados
                    5. **Ejecuta** y recibe el resultado automáticamente
                    
                    ## 💰 Ejemplo: Finanzas - Generar Factura
                    
                    **Parámetros:**
                    ```json
                    {
                      "orden_compra": "OC-12345",
                      "cliente": {
                        "nombre": "Empresa ABC",
                        "email": "contacto@empresaabc.com",
                        "direccion": "Calle 123"
                      },
                      "items": [
                        {"descripcion": "Producto A", "cantidad": 2, "precio": 100},
                        {"descripcion": "Producto B", "cantidad": 1, "precio": 200}
                      ]
                    }
                    ```
                    
                    ## 👥 Ejemplo: RRHH - Filtrar CVs
                    
                    **Parámetros:**
                    ```json
                    {
                      "cvs": [
                        {
                          "nombre": "Juan Pérez",
                          "contenido": "Ingeniero con 5 años de experiencia en Python, SQL, Machine Learning..."
                        }
                      ],
                      "requisitos": {
                        "experiencia_minima": 3,
                        "educacion": "universitaria",
                        "habilidades": ["Python", "SQL", "Machine Learning"]
                      }
                    }
                    ```
                    
                    ## 📦 Ejemplo: Logística - Gestión de Inventario
                    
                    **Parámetros:**
                    ```json
                    {
                      "productos": [
                        {"id": "PROD-001", "nombre": "Producto A", "stock": 5, "stock_maximo": 100, "proveedor": "Proveedor X"},
                        {"id": "PROD-002", "nombre": "Producto B", "stock": 15, "stock_maximo": 50, "proveedor": "Proveedor Y"}
                      ],
                      "umbral_minimo": 10
                    }
                    ```
                    
                    ## 🏥 Ejemplo: Salud - Gestión de Citas
                    
                    **Parámetros:**
                    ```json
                    {
                      "solicitudes": [
                        {
                          "paciente": "María García",
                          "fecha_preferida": "2025-01-25T10:00:00",
                          "tipo": "consulta"
                        }
                      ],
                      "doctores": [
                        {"id": "DOC-001", "nombre": "Dr. López", "especialidad": "General"}
                      ]
                    }
                    ```
                    
                    ## ⚖️ Ejemplo: Legal - Revisar Contrato
                    
                    **Parámetros:**
                    ```json
                    {
                      "contrato": "Texto del contrato aquí..."
                    }
                    ```
                    
                    O sube un documento PDF/DOCX con el contrato.
                    
                    ## 🔒 Ejemplo: TI - Gestión de Contraseñas
                    
                    **Parámetros:**
                    ```json
                    {
                      "sistemas": [
                        {"nombre": "Sistema ERP", "usuario": "admin"},
                        {"nombre": "Sistema CRM", "usuario": "admin"}
                      ],
                      "longitud": 16
                    }
                    ```
                    
                    ---
                    
                    **💡 Tip:** Consulta la documentación completa en `GUIA_RPA_AUTOMATION.md`
                    """)
        
    
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
