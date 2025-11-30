# 🤖 Chatbot Mode - Producto 10/10

## 🎯 ¿Qué es Chatbot Mode?

**Chatbot Mode** es un **backend RAG** que permite a empresas conectar sus chatbots existentes y hacer que respondan usando sus documentos privados.

**Flujo:**
1. Cliente pregunta → En el chatbot de la empresa (en su app)
2. Chatbot de la empresa consulta → DocChat Enterprise por API
3. DocChat Enterprise busca → En documentos privados de la empresa
4. DocChat Enterprise responde → Al chatbot de la empresa
5. Chatbot de la empresa muestra → Respuesta al cliente en su app

---

## ✨ Características (Producto 10/10)

### 🚀 Integración Super Simple
- ✅ **SDK de 3 líneas**: `client.preguntar("pregunta")`
- ✅ **Templates listos**: Copia, pega, funciona
- ✅ **Dashboard web**: Gestiona sin código
- ✅ **Guía super simple**: Para no técnicos

### 🧠 Sistema Inteligente
- ✅ **Relevancia previa**: Decide automáticamente si usar RAG
- ✅ **Respuesta híbrida**: Usa RAG solo cuando es necesario
- ✅ **Más rápido**: No consulta RAG para preguntas simples
- ✅ **Más barato**: Menos llamadas a la API

### ⚡ Optimizaciones
- ✅ **Caché de respuestas**: Respuestas frecuentes instantáneas
- ✅ **Streaming**: Muestra respuesta mientras se genera
- ✅ **RAG híbrido**: BM25 + Vector Search para mejor precisión
- ✅ **Reranking**: Mejora precisión de respuestas

### 📚 Enriquecimiento de Metadatos
- ✅ **KeyBERT**: Palabras clave automáticas
- ✅ **NER**: Detección de entidades
- ✅ **YAKE**: Frases representativas
- ✅ **LLM avanzado**: Metadatos para docs técnicos

---

## 🚀 Inicio Rápido

### Para Empresas (Super Simple)

1. **Registra tu chatbot** (en la UI de Gradio)
2. **Sube tus documentos** (PDF, DOCX, TXT, etc.)
3. **Copia el código** (templates listos)
4. **¡Listo!** Tu chatbot ya funciona

### Código Mínimo (3 Líneas)

```python
from docchat.chatbot_sdk import DocChatClient

client = DocChatClient(chatbot_id="tu-id", api_key="tu-key", api_url="https://tu-servidor.com")
respuesta = client.preguntar("¿Cuál es la política?")
```

---

## 📁 Archivos Importantes

### Para Desarrolladores
- `docchat/chatbot_sdk.py` - SDK simple para integración
- `docchat/chatbot_api.py` - API RESTful completa
- `docchat/chatbot_mode.py` - Lógica del backend RAG
- `api_server.py` - Servidor API

### Para Empresas (No Técnicos)
- `GUIA_INTEGRACION_SUPER_SIMPLE.md` - Guía paso a paso
- `CHATBOT_API_README.md` - Documentación completa
- `chatbot_dashboard.py` - Dashboard web simple
- `templates/` - Código listo para copiar

### Templates de Integración
- `templates/integracion_chatbot_simple.py` - Básico
- `templates/integracion_chatbot_inteligente.py` - Con relevancia previa
- `templates/integracion_chatbot_streaming.py` - Con streaming

---

## 🎯 Casos de Uso

### Empresas con Chatbots Existentes
- **Soporte al cliente**: Chatbot consulta políticas, términos, FAQs
- **Recursos humanos**: Chatbot interno consulta manuales y políticas
- **Ventas**: Asistente consulta catálogo de productos
- **Soporte técnico**: Chatbot consulta documentación técnica

---

## 🔧 Endpoints API

### Principales
- `POST /api/chatbot/register` - Registrar chatbot
- `POST /api/chatbot/{id}/upload` - Subir documentos
- `POST /api/chatbot/{id}/query` - **Consultar RAG (PRINCIPAL)**
- `POST /api/chatbot/{id}/needs-rag` - Verificar si necesita RAG
- `POST /api/chatbot/{id}/query/stream` - Consultar con streaming
- `GET /api/chatbot/{id}/info` - Info del chatbot

---

## 💡 Funcionalidades Avanzadas

### 1. Respuesta Inteligente
```python
# Usa RAG solo si es necesario
respuesta = client.responder_inteligente(
    pregunta="¿Cuál es la política?",
    respuesta_directa="Respuesta que ya tienes"
)
```

### 2. Streaming
```python
# Muestra respuesta mientras se genera
for chunk in client.preguntar_stream("¿Cuál es la política?"):
    print(chunk, end="", flush=True)
```

### 3. Verificar Relevancia
```python
# Decide si necesita RAG
necesita = client.necesita_rag("¿Cuál es la política?")
if necesita:
    respuesta = client.preguntar("¿Cuál es la política?")
```

---

## 📊 Dashboard

Ejecuta el dashboard para gestionar tu chatbot sin código:

```bash
python chatbot_dashboard.py
```

Accede en: `http://localhost:7861`

**Funcionalidades:**
- Ver estadísticas
- Probar consultas
- Generar código de integración
- Verificar relevancia

---

## 🎓 Documentación

- **Guía Super Simple**: `GUIA_INTEGRACION_SUPER_SIMPLE.md`
- **API Completa**: `CHATBOT_API_README.md`
- **Templates**: Carpeta `templates/`

---

## ✅ Checklist para Empresas

- [ ] Registrar chatbot (obtener ID y API key)
- [ ] Subir documentos privados
- [ ] Copiar código de integración
- [ ] Integrar en tu chatbot (3 líneas)
- [ ] Probar con dashboard
- [ ] ¡Listo! Tu chatbot funciona

---

## 🚀 Próximos Pasos

1. **Iniciar servidor API**: `python api_server.py`
2. **Abrir dashboard**: `python chatbot_dashboard.py`
3. **Registrar chatbot**: En la UI de Gradio
4. **Subir documentos**: En la UI de Gradio
5. **Copiar código**: Del dashboard o templates
6. **Integrar**: En tu chatbot (3 líneas)
7. **¡Funciona!**

---

## 💬 Soporte

Para más información:
- Revisa `GUIA_INTEGRACION_SUPER_SIMPLE.md`
- Usa el dashboard para generar código
- Consulta los templates en `templates/`


