# 🤖 Guía del Modo Chatbot

## Descripción

El **Modo Chatbot** permite a empresas conectar sus chatbots existentes por API y usar RAG (Retrieval-Augmented Generation) con su data privada para responder consultas de usuarios.

## Características Principales

### 1. RAG Optimizado
- **Chunking Inteligente**: Documentos divididos en chunks de 300-500 tokens con overlap de 50 tokens
- **Retrieval Híbrido**: Combina BM25 (keywords) + Vector Search (semántico) para mejor precisión
- **Reranking Avanzado**: Usa LLM para evaluar relevancia y mejorar resultados
- **Prompt Interno**: Fuerza al LLM a usar solo información de documentos, evitando alucinaciones

### 2. Base Vectorizada por Chatbot
- Cada chatbot tiene su propia base vectorizada
- Aislamiento completo de datos entre chatbots
- Actualización dinámica sin reconstruir todo

### 3. API RESTful
- Endpoints para registrar chatbots
- Endpoints para subir data
- Endpoints para consultas desde chatbots externos
- Autenticación por API key

## Flujo de Uso

### Paso 1: Registrar Chatbot

**Desde la UI:**
1. Ve al tab "🤖 Chatbot"
2. Sub-tab "📝 Registrar Chatbot"
3. Ingresa nombre del chatbot y empresa
4. Obtén `chatbot_id` y `api_key`

**Desde API:**
```bash
POST /api/v1/chatbot/register
{
    "chatbot_name": "Chatbot de Soporte",
    "company_name": "Mi Empresa S.A."
}
```

**Response:**
```json
{
    "success": true,
    "chatbot_id": "uuid-del-chatbot",
    "api_key": "api-key-generada",
    "chatbot_name": "Chatbot de Soporte",
    "company_name": "Mi Empresa S.A."
}
```

### Paso 2: Subir Data

**Desde la UI:**
1. Sub-tab "📂 Subir Data del Chatbot"
2. Pega el `chatbot_id`
3. Sube documentos (PDF, DOCX, TXT, MD)
4. Espera procesamiento

**Desde API:**
```bash
POST /api/v1/chatbot/upload-data?chatbot_id=TU_CHATBOT_ID
Authorization: Bearer TU_CHATBOT_ID:TU_API_KEY
Content-Type: multipart/form-data

files: [archivo1.pdf, archivo2.pdf, ...]
```

**Response:**
```json
{
    "success": true,
    "chatbot_id": "uuid-del-chatbot",
    "documents_processed": 10,
    "chunks_created": 245
}
```

### Paso 3: Conectar tu Chatbot Externo

**Endpoint de Consulta:**
```bash
POST /api/v1/chatbot/query
Authorization: Bearer TU_CHATBOT_ID:TU_API_KEY
Content-Type: application/json

{
    "chatbot_id": "uuid-del-chatbot",
    "question": "¿Cuáles son las políticas de la empresa?",
    "use_reranking": true,
    "max_chunks": 5
}
```

**Response:**
```json
{
    "success": true,
    "answer": "Según la documentación de la empresa...",
    "sources": ["politicas.pdf", "manual.pdf"],
    "confidence": 0.95,
    "chunks_used": 5,
    "reranked": true,
    "metadata": {
        "chatbot_name": "Chatbot de Soporte",
        "company_name": "Mi Empresa S.A."
    }
}
```

## Integración con Chatbot Existente

### Ejemplo: Integración con Dialogflow

```python
import requests

def consultar_rag(question: str):
    """Consulta RAG desde Dialogflow."""
    response = requests.post(
        "http://tu-servidor:8000/api/v1/chatbot/query",
        headers={
            "Authorization": f"Bearer {CHATBOT_ID}:{API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "chatbot_id": CHATBOT_ID,
            "question": question,
            "use_reranking": True,
            "max_chunks": 5
        }
    )
    
    if response.status_code == 200:
        data = response.json()
        return data["answer"]
    else:
        return "Error consultando base de conocimiento"
```

### Ejemplo: Integración con Rasa

```python
from rasa_sdk import Action
from rasa_sdk.events import SlotSet
import requests

class ActionConsultarRAG(Action):
    def name(self) -> str:
        return "action_consultar_rag"
    
    def run(self, dispatcher, tracker, domain):
        question = tracker.latest_message.get("text")
        
        response = requests.post(
            "http://tu-servidor:8000/api/v1/chatbot/query",
            headers={
                "Authorization": f"Bearer {CHATBOT_ID}:{API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "chatbot_id": CHATBOT_ID,
                "question": question,
                "use_reranking": True
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            dispatcher.utter_message(text=data["answer"])
        else:
            dispatcher.utter_message(text="No pude consultar la base de conocimiento")
        
        return []
```

## Optimizaciones Implementadas

### 1. Chunking Inteligente
- Tamaño: 300-500 tokens por chunk
- Overlap: 50 tokens entre chunks
- Preserva contexto entre fragmentos

### 2. Retrieval Híbrido
- **BM25**: Búsqueda por keywords (40% peso)
- **Vector Search**: Búsqueda semántica (60% peso)
- Combina ambos para mejor precisión

### 3. Reranking Avanzado
- Evalúa relevancia de cada chunk con LLM
- Score de 0-10 por chunk
- Selecciona top-K más relevantes

### 4. Prompt Interno
```
Eres un asistente de {company_name}. Tu tarea es responder preguntas 
de usuarios usando ÚNICAMENTE la información proporcionada en los 
documentos de la empresa.

INSTRUCCIONES CRÍTICAS:
1. Usa SOLO la información de los documentos proporcionados
2. NO inventes información que no esté en los documentos
3. Si la información no está, di claramente: "No tengo información 
   sobre esto en la base de conocimiento"
4. Sé preciso y específico
5. Cita las fuentes cuando sea relevante
```

## Seguridad

- Autenticación por API key por chatbot
- Aislamiento completo de datos entre chatbots
- Validación de `chatbot_id` en cada request
- Logs de auditoría para todas las operaciones

## Endpoints Disponibles

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/api/v1/chatbot/register` | POST | Registrar nuevo chatbot |
| `/api/v1/chatbot/upload-data` | POST | Subir data para chatbot |
| `/api/v1/chatbot/query` | POST | Consultar RAG desde chatbot externo |
| `/api/v1/chatbot/info/{chatbot_id}` | GET | Obtener información del chatbot |

## Notas Importantes

- Cada chatbot tiene su propia base vectorizada
- Los datos se guardan en: `memory/chatbot_data/{chatbot_id}/`
- El sistema funciona sin SQL, usando solo archivos JSON y Chroma
- Reranking es opcional pero recomendado para mejor precisión
- El prompt interno previene alucinaciones del LLM

## Troubleshooting

### Error: "Chatbot ID no encontrado"
- Verifica que hayas registrado el chatbot correctamente
- Usa el `chatbot_id` exacto que recibiste al registrar

### Error: "Invalid API key"
- Verifica que estés usando el formato correcto: `Bearer chatbot_id:api_key`
- Asegúrate de usar el `api_key` correcto para ese `chatbot_id`

### Error: "No tiene data procesada"
- Primero debes subir data para el chatbot
- Espera a que termine el procesamiento antes de consultar

### Respuestas genéricas o sin información
- Verifica que hayas subido documentos relevantes
- Aumenta `max_chunks` en la consulta
- Activa `use_reranking` para mejor precisión

