# LangGraph Agent - Customer Service Enterprise

## Arquitectura

Este módulo implementa un agente de Customer Service enterprise-grade usando LangGraph, siguiendo los principios de Meta Business AI y Sierra AI.

### Componentes Principales

1. **State (`state.py`)**: Estado tipado mínimo con:
   - `user_id`, `channel`
   - `intent`, `confidence`
   - `conversation_state`
   - `retrieval_context`, `retrieval_confidence`
   - `escalation_flag`, `escalation_reason`
   - `decision_history` (para auditoría)

2. **Intent Classifier (`intent_classifier.py`)**: Clasifica intenciones en 8 categorías:
   - pregunta_general
   - consulta_productos
   - soporte_tecnico
   - tracking_envio
   - devolucion_reclamo
   - compra_asistencia
   - conversacion_sentimiento_negativo
   - escalamiento_humano

3. **Decision Policy (`decision_policy.py`)**: Decide explícitamente entre:
   - `respond`: Responder con confianza
   - `ask_clarification`: Pedir aclaración
   - `escalate`: Escalar a humano
   - `reject`: Rechazar por baja confianza

4. **RAG Retriever (`rag_retriever.py`)**: Retrieval contextual optimizado por intención

5. **Agent Graph (`agent_graph.py`)**: Grafo LangGraph con:
   - Nodos de intención específicos
   - Nodos de decisión
   - Nodos de escalamiento
   - Flujo condicional explícito

## Uso

El agente se integra automáticamente en `AssistanceAIAgent` cuando `use_langgraph=True` (por defecto).

Para usar directamente:

```python
from docchat.assistance_ai.graph import CustomerServiceAgentGraph
from langchain_groq import ChatGroq

llm = ChatGroq(model="llama-3.3-70b-versatile", groq_api_key="...")
agent = CustomerServiceAgentGraph(llm=llm, tools={...})

result = agent.invoke({
    "user_id": "user123",
    "channel": "web",
    "user_message": "¿Tienen zapatillas talla 42?",
    "messages": []
})
```

## Flujo del Grafo

```
Entry → classify_intent → decision → [intent_nodes] → apply_decision_policy → [final_nodes] → END
```

Los nodos de intención procesan según su tipo y luego aplican la decision policy para determinar la acción final.

