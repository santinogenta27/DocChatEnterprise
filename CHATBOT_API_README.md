# 🤖 Chatbot Mode API - Backend RAG para Chatbots Empresariales

## 🎯 Integración Super Simple (3 Líneas de Código)

```python
from docchat.chatbot_sdk import DocChatClient

client = DocChatClient(chatbot_id="tu-id", api_key="tu-key", api_url="https://tu-servidor.com")
respuesta = client.preguntar("¿Cuál es la política de devoluciones?")
```

**¡Eso es todo!** Tu chatbot ya puede responder usando tus documentos privados.

---

## 📋 Descripción

**DocChat Enterprise Chatbot Mode** es un **backend RAG** que permite a empresas conectar sus chatbots existentes y usar RAG con su data privada.

### 🔄 Flujo Completo

**Ejemplo del flujo:**

1. **Cliente hace pregunta** → En el chatbot de la empresa (en su app)
2. **Chatbot de la empresa consulta** → DocChat Enterprise por API
3. **DocChat Enterprise busca** → En los documentos privados que la empresa subió
4. **DocChat Enterprise devuelve respuesta** → Al chatbot de la empresa
5. **Chatbot de la empresa muestra respuesta** → Al cliente en su app

**En resumen:** DocChat Enterprise es el **backend RAG** que tu chatbot consulta. La respuesta se muestra al cliente en **tu app**, no en la nuestra.

---

## 🚀 Inicio Rápido

### Opción 1: Usar SDK (Super Fácil - Recomendado)

```python
from docchat.chatbot_sdk import DocChatClient

# Conectar
client = DocChatClient(
    chatbot_id="tu-chatbot-id",
    api_key="tu-api-key",
    api_url="https://tu-servidor.com"
)

# Preguntar
respuesta = client.preguntar("¿Cuál es la política?")
print(respuesta)
```

**¡Solo 3 líneas de código!** Ver más en `GUIA_INTEGRACION_SUPER_SIMPLE.md`

### Opción 2: Usar API Directamente

### 1. Iniciar el Servidor API

```bash
python api_server.py
```

El servidor se iniciará en `http://localhost:8000`

### 2. Registrar tu Chatbot

```bash
curl -X POST "http://localhost:8000/api/chatbot/register" \
  -H "Content-Type: application/json" \
  -d '{
    "chatbot_name": "Chatbot Soporte Cliente",
    "company_name": "Tu Empresa"
  }'
```

**Respuesta:**
```json
{
  "chatbot_id": "abc123-def456-...",
  "chatbot_name": "Chatbot Soporte MercadoLibre",
  "company_name": "MercadoLibre",
  "api_key": "tu-api-key-secreta",
  "message": "Chatbot registrado exitosamente..."
}
```

**⚠️ IMPORTANTE:** Guarda el `chatbot_id` y `api_key`. Los necesitarás para todo.

### 3. Subir Documentos

```bash
curl -X POST "http://localhost:8000/api/chatbot/{chatbot_id}/upload" \
  -H "X-API-Key: tu-api-key-secreta" \
  -F "files=@documento1.pdf" \
  -F "files=@documento2.pdf"
```

### 4. Consultar RAG desde tu Chatbot

**Este es el endpoint principal que usarás en tu chatbot:**

```python
import requests

# Cuando un cliente hace una pregunta en tu chatbot (en tu app)
chatbot_id = "abc123-def456-..."
api_key = "tu-api-key-secreta"
user_question = "¿Cuál es la política de devoluciones?"

# Tu chatbot consulta a DocChat Enterprise (backend RAG)
response = requests.post(
    f"http://localhost:8000/api/chatbot/{chatbot_id}/query",
    json={
        "question": user_question,
        "use_reranking": True,  # Mejora precisión
        "max_chunks": 5
    },
    headers={"X-API-Key": api_key}
)

data = response.json()

# Esta es la respuesta que muestras al cliente en TU APP
answer = data["answer"]
sources = data["sources"]  # Fuentes usadas (opcional mostrar)
confidence = data["confidence"]  # Confianza de la respuesta

# Mostrar answer al cliente en tu app
```

**Respuesta:**
```json
{
  "answer": "Según nuestros documentos, la política de devoluciones permite...",
  "sources": ["politicas.pdf", "terminos.pdf"],
  "confidence": 0.95,
  "chunks_used": 5,
  "reranked": true,
  "metadata": {
    "chatbot_name": "Chatbot Soporte MercadoLibre",
    "company_name": "MercadoLibre"
  }
}
```

---

## 📚 Endpoints Completos

### POST `/api/chatbot/register`
Registra un nuevo chatbot.

**Request:**
```json
{
  "chatbot_name": "Nombre del Chatbot",
  "company_name": "Nombre de la Empresa",
  "api_key": "opcional-si-quieres-usar-una-propia"
}
```

### POST `/api/chatbot/{chatbot_id}/upload`
Sube documentos para procesar.

**Headers:**
- `X-API-Key`: Tu API key

**Body:** Form-data con archivos
- `files`: Archivos (PDF, DOCX, TXT, MD)

### POST `/api/chatbot/{chatbot_id}/query` ⭐ **PRINCIPAL**
Consulta el RAG. Este es el endpoint que usarás desde tu chatbot.

**Headers:**
- `X-API-Key`: Tu API key

**Request:**
```json
{
  "question": "Pregunta del usuario",
  "use_reranking": true,
  "max_chunks": 5
}
```

### GET `/api/chatbot/{chatbot_id}/info`
Obtiene información del chatbot.

**Headers:**
- `X-API-Key`: Tu API key

### GET `/api/chatbot/list`
Lista todos los chatbots (sin autenticación, para admin).

### GET `/api/chatbot/health`
Health check del servicio.

---

## 🔧 Ejemplo Completo de Integración

### Para tu Chatbot Empresarial

```python
# chatbot_integration.py
import requests
from typing import Optional

class EmpresaChatbotRAG:
    """
    Integración de RAG para tu chatbot empresarial.
    
    Este código va en TU chatbot. Cuando un cliente pregunta,
    tu chatbot consulta a DocChat Enterprise y muestra la respuesta.
    """
    
    def __init__(self, chatbot_id: str, api_key: str, api_url: str = "http://localhost:8000"):
        self.chatbot_id = chatbot_id
        self.api_key = api_key
        self.api_url = api_url
    
    def query(self, user_question: str) -> dict:
        """
        Consulta RAG y retorna respuesta.
        
        Esta función la llamas desde tu chatbot cuando un cliente hace una pregunta.
        """
        try:
            response = requests.post(
                f"{self.api_url}/api/chatbot/{self.chatbot_id}/query",
                json={
                    "question": user_question,
                    "use_reranking": True,
                    "max_chunks": 5
                },
                headers={"X-API-Key": self.api_key},
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {
                "answer": "Lo siento, no pude consultar la base de conocimiento en este momento.",
                "error": str(e)
            }
    
    def get_answer(self, user_question: str) -> str:
        """
        Obtiene solo la respuesta (sin metadatos).
        Útil para mostrar directamente al cliente.
        """
        result = self.query(user_question)
        return result.get("answer", "No pude generar una respuesta.")


# Uso en tu chatbot empresarial
rag = EmpresaChatbotRAG(
    chatbot_id="tu-chatbot-id",
    api_key="tu-api-key",
    api_url="https://tu-servidor.com"  # URL de producción
)

# Cuando un cliente pregunta en tu chatbot (en tu app)
user_question = "¿Cuál es la política de devoluciones?"

# Tu chatbot consulta a DocChat Enterprise (backend RAG)
response = rag.query(user_question)

# Mostrar respuesta al cliente en TU APP
answer = response["answer"]
print(f"Respuesta para el cliente: {answer}")
```

---

## 🎯 Pipeline de Procesamiento

El sistema procesa documentos con este pipeline optimizado:

1. **Subida de documentos** → PDF, DOCX, TXT, MD
2. **Parsing y limpieza** → Headers, footers, formato uniforme
3. **Enriquecimiento de metadatos** (opcional):
   - KeyBERT → Palabras clave
   - YAKE → Frases representativas
   - NER (spaCy) → Entidades (personas, organizaciones, lugares)
   - LLM (opcional) → Metadatos avanzados para docs técnicos
4. **Chunking inteligente** → 300-500 tokens con overlap
5. **Vectorización** → text-embedding-ada-002 (OpenAI)
6. **Base vectorizada** → ChromaDB (local) o Pinecone (opcional)
7. **RAG Blended** → Búsqueda híbrida (BM25 + Vector) + Reranking

---

## 🔒 Seguridad

- Cada chatbot tiene su propia `api_key` única
- La API key se valida en cada request
- Los documentos están aislados por `chatbot_id`
- CORS configurado para permitir requests desde tu dominio

---

## 📊 Documentación Interactiva

Cuando el servidor esté corriendo, visita:
- **Swagger UI:** `http://localhost:8000/docs`
- **ReDoc:** `http://localhost:8000/redoc`

---

## 💡 Casos de Uso

### Empresas con Chatbots Existentes
- **Soporte al cliente**: Tu chatbot consulta políticas, términos, FAQs desde DocChat Enterprise
- **Recursos humanos**: Chatbot interno que consulta manuales y políticas
- **Ventas**: Asistente que consulta catálogo de productos y especificaciones
- **Soporte técnico**: Chatbot que consulta documentación técnica

**Flujo en todos los casos:**
1. Cliente pregunta → En tu chatbot (en tu app)
2. Tu chatbot consulta → DocChat Enterprise por API
3. DocChat Enterprise busca → En tus documentos privados
4. DocChat Enterprise responde → A tu chatbot
5. Tu chatbot muestra → Respuesta al cliente en tu app

---

## 🆘 Troubleshooting

**Error 401 (Unauthorized):**
- Verifica que el `X-API-Key` en el header sea correcto

**Error 404 (Not Found):**
- Verifica que el `chatbot_id` sea correcto
- Asegúrate de haber subido documentos primero

**Error 500 (Internal Server Error):**
- Revisa los logs del servidor
- Verifica que los documentos se procesaron correctamente

---

## 📞 Soporte

Para más información, consulta la documentación completa en `/docs` cuando el servidor esté corriendo.

