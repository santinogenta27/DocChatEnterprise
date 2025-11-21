"""
Ejemplo de integración del sistema Agentic AI con DocChat
Muestra cómo usar los agentes autónomos con los datos subidos
"""

import os
import sys
import json
from pathlib import Path

# Agregar el directorio raíz al path
sys.path.append(str(Path(__file__).parent.parent))

from openai import OpenAI
import chromadb
from chromadb.config import Settings
from agentic_system.agent_orchestrator import AgentOrchestrator


def setup_agentic_system(openai_api_key: str, chroma_persist_dir: str = ".chromadb") -> AgentOrchestrator:
    """
    Configura el sistema agentic AI
    
    Args:
        openai_api_key: Clave API de OpenAI
        chroma_persist_dir: Directorio donde está persistida la base de datos ChromaDB
    
    Returns:
        AgentOrchestrator configurado
    """
    # Inicializar cliente OpenAI
    llm_client = OpenAI(api_key=openai_api_key)
    
    # Inicializar cliente ChromaDB
    chroma_client = chromadb.Client(Settings(persist_directory=chroma_persist_dir))
    
    # Crear orquestador de agentes
    orchestrator = AgentOrchestrator(
        llm_client=llm_client,
        chroma_client=chroma_client,
        collection_name="general_vectors"  # O la colección que uses
    )
    
    return orchestrator


def example_autonomous_task(orchestrator: AgentOrchestrator):
    """
    Ejemplo 1: Tarea autónoma simple
    El agente planifica y ejecuta una tarea de forma independiente
    """
    print("=" * 60)
    print("EJEMPLO 1: Tarea Autónoma Simple")
    print("=" * 60)
    
    task_description = "Analiza los documentos subidos y extrae las políticas principales mencionadas"
    
    result = orchestrator.execute_task_autonomously(
        task_description=task_description,
        context={
            "collection_name": "general_vectors",
            "top_k": 10
        }
    )
    
    print(f"\n✅ Tarea completada: {result['task_id']}")
    print(f"📊 Estado: {result['status']}")
    print(f"🤖 Agente usado: {result['agent_used']}")
    print(f"\n📝 Pasos ejecutados:")
    for i, step in enumerate(result['steps_executed'], 1):
        print(f"  {i}. {step}")
    
    if result.get('output'):
        print(f"\n📄 Resultado:")
        print(json.dumps(result['output'], indent=2, ensure_ascii=False))


def example_multi_agent_workflow(orchestrator: AgentOrchestrator):
    """
    Ejemplo 2: Flujo de trabajo multi-agente
    Múltiples agentes colaboran para completar una tarea compleja
    """
    print("\n" + "=" * 60)
    print("EJEMPLO 2: Flujo Multi-Agente")
    print("=" * 60)
    
    main_task = "Crea un reporte completo comparando las políticas de diferentes documentos y genera recomendaciones"
    
    result = orchestrator.execute_multi_agent_workflow(
        main_task=main_task,
        context={
            "collection_name": "general_vectors",
            "top_k": 15
        }
    )
    
    print(f"\n✅ Tarea principal: {result['main_task']}")
    print(f"\n📋 Subtareas generadas:")
    for i, subtask in enumerate(result['subtasks'], 1):
        print(f"  {i}. {subtask}")
    
    print(f"\n📊 Resultados de subtareas:")
    for i, subtask_result in enumerate(result['subtask_results'], 1):
        status_icon = "✅" if subtask_result['status'] == 'completed' else "❌"
        print(f"  {status_icon} Subtarea {i}: {subtask_result['status']}")
    
    if result.get('final_result'):
        print(f"\n📄 Resultado Final Compilado:")
        print(result['final_result'].get('compiled_response', 'N/A')[:500] + "...")


def example_custom_subtasks(orchestrator: AgentOrchestrator):
    """
    Ejemplo 3: Flujo con subtareas personalizadas
    El usuario define las subtareas específicas
    """
    print("\n" + "=" * 60)
    print("EJEMPLO 3: Subtareas Personalizadas")
    print("=" * 60)
    
    main_task = "Análisis completo de documentos empresariales"
    
    custom_subtasks = [
        "Recupera todos los documentos relacionados con políticas de seguridad",
        "Analiza las políticas encontradas y extrae los puntos clave",
        "Compara las políticas de diferentes secciones del documento",
        "Genera un reporte estructurado con hallazgos y recomendaciones"
    ]
    
    result = orchestrator.execute_multi_agent_workflow(
        main_task=main_task,
        subtasks=custom_subtasks,
        context={
            "collection_name": "general_vectors",
            "top_k": 10
        }
    )
    
    print(f"\n✅ Tarea principal completada")
    print(f"📊 Subtareas ejecutadas: {len(result['subtask_results'])}")
    print(f"✅ Exitosas: {result['final_result'].get('successful_subtasks', 0)}")


def get_system_status(orchestrator: AgentOrchestrator):
    """
    Muestra el estado del sistema de agentes
    """
    print("\n" + "=" * 60)
    print("ESTADO DEL SISTEMA AGENTIC")
    print("=" * 60)
    
    status = orchestrator.get_system_status()
    
    print(f"\n🤖 Agentes disponibles: {status['total_agents']}")
    for agent_id, agent_info in status['agents'].items():
        print(f"\n  📌 {agent_id}:")
        print(f"     - Tareas completadas: {agent_info['completed']}")
        print(f"     - Tasa de éxito: {agent_info['success_rate']:.2%}")
        print(f"     - Capacidades: {', '.join(agent_info['capabilities'])}")
    
    print(f"\n📋 Tareas en cola: {status['tasks_queued']}")
    print(f"✅ Tareas completadas: {status['tasks_completed']}")
    print(f"\n🛠️  Herramientas disponibles: {', '.join(status['available_tools'])}")


if __name__ == "__main__":
    import json
    
    # Configurar API Key (puedes obtenerla de variables de entorno o input)
    api_key = os.getenv("OPENAI_API_KEY", "")
    
    if not api_key:
        print("⚠️  Por favor configura OPENAI_API_KEY como variable de entorno")
        print("   o modifica este script para ingresarla manualmente")
        sys.exit(1)
    
    # Configurar el sistema
    print("🚀 Inicializando sistema Agentic AI...")
    orchestrator = setup_agentic_system(api_key)
    
    # Ejecutar ejemplos
    try:
        # Ejemplo 1: Tarea autónoma simple
        example_autonomous_task(orchestrator)
        
        # Ejemplo 2: Flujo multi-agente
        example_multi_agent_workflow(orchestrator)
        
        # Ejemplo 3: Subtareas personalizadas
        example_custom_subtasks(orchestrator)
        
        # Mostrar estado del sistema
        get_system_status(orchestrator)
        
    except Exception as e:
        print(f"\n❌ Error ejecutando ejemplos: {e}")
        import traceback
        traceback.print_exc()

