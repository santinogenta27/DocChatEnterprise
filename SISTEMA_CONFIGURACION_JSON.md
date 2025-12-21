# 📁 Sistema de Configuración con JSON (Sin .env)

## ✅ CAMBIO REALIZADO

He reemplazado el sistema de configuración basado en `.env` por un sistema basado en **JSON**, que es más fácil de usar para usuarios no técnicos.

## 🎯 Ventajas de JSON sobre .env

1. **Más legible:** JSON es formato estándar, fácil de leer y editar
2. **Estructurado:** Permite objetos anidados (objeciones, preguntas de lead scoring)
3. **No requiere conocimientos técnicos:** No hay que saber formato .env
4. **Mejor para UI:** Más fácil de parsear y mostrar en interfaces

## 📁 Ubicación del Archivo

**Archivo principal:** `docchat/business_ai_omnicanal/config/chatbot_config.json`

Este archivo se crea automáticamente cuando guardas configuración desde Gradio.

## 📋 Formato del Archivo JSON

```json
{
  "tone": "friendly",
  "personality": "Eres un experto en moda...",
  "custom_instructions": "Siempre menciona garantías...",
  "rag_enabled": true,
  "documents_dir": "/path/to/documents",
  "lead_scoring_enabled": true,
  "lead_questions": [
    {
      "question": "¿Cuál es tu presupuesto?",
      "weight": 3
    }
  ],
  "lead_hot_threshold": 7,
  "handoff_keywords": [
    "queja",
    "fraude",
    "hablar con humano"
  ],
  "handoff_sentiment_threshold": 0.7,
  "default_language": "es",
  "multilingual_enabled": true,
  "objection_responses": {
    "está caro": "Entiendo tu preocupación. ¿Sabías que...",
    "lo voy a pensar": "Por supuesto, ¿hay algo específico..."
  }
}
```

## 🔄 Compatibilidad con .env

El sistema mantiene compatibilidad con `.env`:

- **Carga:** Intenta cargar desde JSON primero, si no existe usa `.env` como fallback
- **Guardado:** Guarda principalmente en JSON, pero también actualiza `.env` para compatibilidad

## 🚀 Uso desde Gradio

Cuando guardas configuración desde Gradio:

1. Se crea/actualiza `chatbot_config.json`
2. Opcionalmente también se actualiza `.env` (para compatibilidad con código legacy)
3. No necesitas editar archivos manualmente

## 📝 Edición Manual (Opcional)

Si necesitas editar la configuración manualmente:

1. Abre `docchat/business_ai_omnicanal/config/chatbot_config.json`
2. Edita el JSON (usa un editor que valide JSON)
3. Guarda el archivo
4. Reinicia el servidor

**Ejemplo de edición:**
```json
{
  "tone": "professional",  // Cambiar tono
  "objection_responses": {
    "está caro": "Nueva respuesta personalizada"
  }
}
```

## 🔍 Cómo Funciona

### 1. ChatbotConfigManager

```python
from docchat.business_ai_omnicanal.config.chatbot_config_manager import ChatbotConfigManager

# Carga configuración (JSON o .env como fallback)
config_manager = ChatbotConfigManager()
config = config_manager.load()

# Guarda configuración (principalmente en JSON)
config_manager.save(chatbot_config, also_update_env=True)
```

### 2. BusinessAIAgent

El agente carga configuración automáticamente:

```python
# En __init__
self.chatbot_config_manager = ChatbotConfigManager()
self.chatbot_config = self.chatbot_config_manager.load()

# En handle_message (recarga para cambios recientes)
self.chatbot_config = self.chatbot_config_manager.load()
```

## ✅ Ventajas para Usuarios Finales

1. **No necesitan saber .env:** Configuran todo desde Gradio
2. **JSON es estándar:** Si necesitan editar, JSON es más fácil que .env
3. **Backup automático:** Se guarda también en .env como respaldo
4. **Validación:** JSON tiene mejor validación de formato

## 🎯 Migración desde .env

Si ya tienes configuraciones en `.env`:

1. El sistema las seguirá leyendo (compatibilidad hacia atrás)
2. Al guardar desde Gradio, se creará el JSON
3. Próximas cargas usarán JSON en lugar de .env

## 📊 Estructura de Archivos

```
docchat/
  business_ai_omnicanal/
    config/
      __init__.py
      chatbot_config_manager.py  # Gestor de configuraciones
      chatbot_config.json        # ✅ Configuración principal (JSON)
    documents/                   # Documentos para RAG
```

## 🔐 Seguridad

- **JSON no expone secretos:** Solo configuración de comportamiento
- **API keys siguen en .env:** Las API keys (Groq, OpenAI, etc.) se mantienen en .env por seguridad
- **JSON es editable:** Los usuarios pueden ver y editar su configuración fácilmente

## ⚠️ Notas

- **Reiniciar servidor:** Después de cambiar configuración, reinicia el servidor
- **Formato JSON válido:** Si editas manualmente, asegúrate de que el JSON sea válido
- **Backup:** El sistema crea backup en .env automáticamente

## 🎉 Resultado

Ahora los usuarios:
- ✅ No necesitan saber formato .env
- ✅ Configuran todo desde Gradio
- ✅ Pueden editar JSON si quieren (opcional)
- ✅ El sistema funciona automáticamente











