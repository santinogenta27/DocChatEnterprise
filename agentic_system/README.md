# Sistema Agentic AI para DocChat

## 🎯 ¿Qué es esto?

Este sistema extiende DocChat con capacidades de **Agentic AI autónomo**, permitiendo que los agentes realicen tareas complejas de forma independiente con los datos que has subido.

## 🚀 Características Principales

### 1. **Agentes Autónomos**
- Los agentes pueden **planificar** tareas complejas descomponiéndolas en pasos
- **Ejecutan** acciones de forma independiente
- **Toman decisiones** sobre cómo proceder
- **Se auto-corrigen** cuando encuentran errores

### 2. **Múltiples Agentes Especializados**
- **Data Analyst**: Analiza datos, extrae información, identifica tendencias
- **Document Summarizer**: Resume documentos y extrae información clave
- **Comparison Agent**: Compara diferentes conjuntos de datos
- **Report Generator**: Genera reportes estructurados completos

### 3. **Herramientas (Tools)**
Los agentes tienen acceso a herramientas para interactuar con los datos:
- **DataRetrievalTool**: Búsqueda semántica en ChromaDB
- **DataAnalysisTool**: Análisis de patrones y tendencias
- **ReportGenerationTool**: Generación de reportes estructurados
- **ComparisonTool**: Comparación de datos

### 4. **Orquestador Inteligente**
- Asigna automáticamente tareas al agente más apropiado
- Coordina múltiples agentes para tareas complejas
- Descompone tareas grandes en subtareas manejables

## 📦 Instalación

```bash
pip install -r requirements.txt
```

## 🔧 Configuración

1. **Configura tu API Key de OpenAI:**
```bash
export OPENAI_API_KEY="tu-api-key-aqui"
```

2. **Asegúrate de que ChromaDB esté configurado** con tus datos subidos

## 💡 Ejemplos de Uso

### Ejemplo 1: Tarea Autónoma Simple

```python
from agentic_system.integration_example import setup_agentic_system
import os

# Configurar el sistema
orchestrator = setup_agentic_system(
    openai_api_key=os.getenv("OPENAI_API_KEY"),
    chroma_persist_dir=".chromadb"
)

# Ejecutar una tarea autónoma
result = orchestrator.execute_task_autonomously(
    task_description="Analiza los documentos y extrae las políticas principales",
    context={"collection_name": "general_vectors", "top_k": 10}
)

print(result)
```

### Ejemplo 2: Flujo Multi-Agente

```python
# Tarea compleja que requiere múltiples agentes
result = orchestrator.execute_multi_agent_workflow(
    main_task="Crea un reporte comparando políticas de diferentes documentos",
    context={"collection_name": "general_vectors"}
)

# El orquestador automáticamente:
# 1. Descompone la tarea en subtareas
# 2. Asigna cada subtarea al agente apropiado
# 3. Coordina la ejecución
# 4. Compila los resultados finales
```

### Ejemplo 3: Subtareas Personalizadas

```python
# Define tus propias subtareas
custom_subtasks = [
    "Recupera documentos sobre políticas de seguridad",
    "Analiza y extrae puntos clave",
    "Compara políticas de diferentes secciones",
    "Genera reporte con hallazgos"
]

result = orchestrator.execute_multi_agent_workflow(
    main_task="Análisis completo",
    subtasks=custom_subtasks,
    context={"collection_name": "general_vectors"}
)
```

## 🏗️ Arquitectura

```
┌─────────────────────────────────────────┐
│      AgentOrchestrator                  │
│  (Coordina múltiples agentes)           │
└──────────────┬──────────────────────────┘
               │
       ┌───────┴────────┐
       │                │
┌──────▼──────┐  ┌──────▼──────┐
│ Autonomous  │  │ Autonomous  │
│   Agent 1   │  │   Agent 2   │
└──────┬──────┘  └──────┬──────┘
       │                │
       └───────┬────────┘
               │
       ┌───────▼────────┐
       │    Tools      │
       │ - Retrieval   │
       │ - Analysis    │
       │ - Comparison  │
       │ - Report Gen  │
       └───────────────┘
```

## 🔄 Flujo de Trabajo

1. **Usuario solicita una tarea** → "Analiza los documentos y genera un reporte"

2. **Orquestador asigna la tarea** → Selecciona el agente más apropiado

3. **Agente planifica** → Descompone la tarea en pasos específicos

4. **Agente ejecuta** → Usa herramientas para:
   - Recuperar datos relevantes
   - Analizar información
   - Comparar documentos
   - Generar reportes

5. **Agente verifica** → Valida los resultados y se auto-corrige si es necesario

6. **Resultado final** → Respuesta estructurada y verificada

## 🎨 Integración con DocChat

Para integrar esto con tu aplicación DocChat existente:

```python
# En tu app.py o archivo principal
from agentic_system.agent_orchestrator import AgentOrchestrator
from openai import OpenAI
import chromadb

# Inicializar en tu app
orchestrator = AgentOrchestrator(
    llm_client=OpenAI(api_key=os.getenv("OPENAI_API_KEY")),
    chroma_client=chroma_client,
    collection_name="general_vectors"
)

# Usar en tu interfaz de chat
def handle_autonomous_query(user_query: str):
    result = orchestrator.execute_task_autonomously(
        task_description=user_query,
        context={"collection_name": "general_vectors"}
    )
    return result["output"]["final_output"]
```

## 🛠️ Extender el Sistema

### Agregar Nuevos Agentes

```python
from agentic_system.autonomous_agent import AutonomousAgent, AgentCapability

new_agent = AutonomousAgent(
    agent_id="custom_agent",
    capabilities=[AgentCapability.DATA_ANALYSIS],
    llm_client=llm_client,
    tools=[your_custom_tool]
)

orchestrator.agents["custom_agent"] = new_agent
```

### Crear Nuevas Herramientas

```python
from agentic_system.tools import AgentTool

class MyCustomTool(AgentTool):
    def name(self) -> str:
        return "my_tool"
    
    def description(self) -> str:
        return "Descripción de mi herramienta"
    
    def can_handle(self, step_description: str) -> bool:
        return "mi_accion" in step_description.lower()
    
    def execute(self, step_description: str, context: Dict, previous_results: List):
        # Tu lógica aquí
        return {"result": "mi resultado"}
```

## 📊 Monitoreo

```python
# Ver estado del sistema
status = orchestrator.get_system_status()
print(f"Agentes: {status['total_agents']}")
print(f"Tareas completadas: {status['tasks_completed']}")
```

## ⚠️ Consideraciones

1. **Costo**: Cada agente usa llamadas a la API de OpenAI. Monitorea el uso.

2. **Tiempo**: Las tareas complejas pueden tomar varios minutos.

3. **Errores**: Los agentes intentan auto-corregirse, pero algunos errores pueden requerir intervención.

4. **Datos**: Asegúrate de que ChromaDB tenga los datos necesarios antes de ejecutar tareas.

## 🚀 Próximos Pasos

- [ ] Agregar más tipos de agentes especializados
- [ ] Implementar caché de resultados
- [ ] Agregar logging detallado
- [ ] Crear interfaz web para monitorear agentes
- [ ] Integrar con LangGraph para workflows más complejos

## 📝 Licencia

Este código es parte del proyecto DocChat y sigue la misma licencia.


