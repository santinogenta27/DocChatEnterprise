"""
Inicio Rápido: Integración del Sistema Agentic AI
Ejemplo mínimo para empezar a usar agentes autónomos
"""

import os
from openai import OpenAI
import chromadb
from chromadb.config import Settings
from agentic_system.agent_orchestrator import AgentOrchestrator


def quick_example():
    """
    Ejemplo rápido de cómo usar el sistema agentic
    """
    # 1. Configurar API Key
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        print("⚠️  Configura OPENAI_API_KEY como variable de entorno")
        return
    
    # 2. Inicializar clientes
    llm_client = OpenAI(api_key=api_key)
    chroma_client = chromadb.Client(Settings(persist_directory=".chromadb"))
    
    # 3. Crear orquestador
    orchestrator = AgentOrchestrator(
        llm_client=llm_client,
        chroma_client=chroma_client,
        collection_name="general_vectors"
    )
    
    # 4. Ejecutar una tarea autónoma
    print("🤖 Ejecutando tarea autónoma...")
    result = orchestrator.execute_task_autonomously(
        task_description="Analiza los documentos subidos y extrae los temas principales",
        context={"top_k": 5}
    )
    
    # 5. Mostrar resultado
    print(f"\n✅ Estado: {result['status']}")
    print(f"🤖 Agente: {result['agent_used']}")
    
    if result.get('output') and result['output'].get('final_output'):
        print(f"\n📄 Resultado:\n{result['output']['final_output']}")
    
    return result


if __name__ == "__main__":
    quick_example()


