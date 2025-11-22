"""Gradio app for DocChat Enterprise - Multi-Agent RAG with Autonomous Agents."""

from __future__ import annotations

import os
import json
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
from docchat.enterprise_api import EnterpriseAPIMode
from docchat.cloud_integrations import CloudStorageIntegration, WebhookProcessor
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
enterprise_api = EnterpriseAPIMode(config)
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


def run_enterprise_api_mode(files, auto_detect: bool = True, rules_json: str = ""):
    """Ejecuta modo Enterprise API con procesamiento automático."""
    if not files:
        raise gr.Error("Primero sube documentos para procesar.")
    
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
    
    # Verificar espacio en disco al inicio
    try:
        import shutil
        disk_usage = shutil.disk_usage(".")
        free_space_gb = disk_usage.free / (1024 * 1024 * 1024)
        
        if free_space_gb < 1:
            gr.Info(
                f"⚠️ ADVERTENCIA: Espacio en disco muy bajo ({free_space_gb:.2f} GB libre).\n"
                f"Para procesar muchos PDFs necesitas al menos 2-3 GB libres.\n"
                f"Ejecuta .\\LIMPIAR_TEMPORALES.ps1 para liberar espacio."
            )
    except:
        pass
    
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
            
            with gr.Row():
                enterprise_files = gr.Files(
                    label="📂 Documentos Empresariales (PDF, DOCX, TXT, MD, Emails)",
                    file_count="multiple",
                    file_types=[".pdf", ".docx", ".txt", ".md"],
                )
            
            with gr.Row():
                auto_detect_check = gr.Checkbox(
                    label="🔍 Detección Automática (Problemas, Oportunidades, Patrones)",
                    value=True,
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
            
            enterprise_button = gr.Button("🚀 Procesar con Enterprise API", variant="primary", size="lg")
            
            enterprise_output = gr.Markdown(label="📊 Resultados Enterprise API")
            
            enterprise_button.click(
                fn=run_enterprise_api_mode,
                inputs=[enterprise_files, auto_detect_check, rules_input],
                outputs=[enterprise_output],
            )
        
        # Tab 4.5: Cloud Storage Integration (NUEVO)
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
