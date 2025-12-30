# ⭐ STAR AGENT - Asistente Virtual 24/7

## 🚀 Descripción

STAR AGENT es un asistente virtual inteligente de ventas y soporte diseñado para PYMEs. Funciona 24/7 en múltiples canales (WhatsApp, Instagram, Messenger, Web) y está optimizado para maximizar conversiones y cerrar ventas.

## 📊 Estadísticas del Proyecto

- **15,989 líneas de código** en **63 archivos Python**
- **Sistema enterprise completo**
- **Listo para producción**

## ✨ Características Principales

### 1. **Omnicanal**
- WhatsApp Business API
- Instagram Direct Messages
- Messenger (Facebook)
- Widget Web embebible

### 2. **Sales Closer Elite**
- Detección de etapas de venta (INTEREST → CONSIDERATION → READY → CLOSING)
- Manejo inteligente de objeciones
- Estrategias personalizables (ANCHORING, ROI, SOCIAL_PROOF)
- Cierre directo con urgencia ética
- Integración Stripe para pagos

### 3. **RAG Avanzado (Multi-Agent)**
- Índices separados por tipo de contenido (productos, políticas, marketing, reviews)
- Retrieval híbrido (BM25 + Vector Search)
- ScopeChecker para relevancia
- ResearchAgent para respuestas precisas
- ChromaDB para almacenamiento vectorial

### 4. **ReAct Pattern**
- Patrón completo Think → Act → Observe → Verify → Close
- LangGraph para workflows complejos
- State persistente entre interacciones
- Looping y branching dinámicos

### 5. **Handoff Real a Humanos**
- Integración con Zendesk
- WhatsApp Business
- Email
- Triggers configurables (manual, baja confianza, objeción fuerte, frustración)

### 6. **Ingesta Automática Multi-Fuente**
- Scheduler configurable (cada X horas)
- Website (crawling con Playwright)
- Instagram (Graph API)
- Facebook (Graph API)
- Google Business (reviews, horarios)
- Webhooks para actualización en tiempo real

### 7. **UI Completa de Configuración**
- 8 tabs completos en Gradio
- Configuración sin código
- Guardado automático de configuraciones
- Panel de métricas y analytics

### 8. **Seguridad**
- Rule of Two
- Guardrails anti-injection
- Validación de queries
- Cumplimiento de privacidad

## 🛠️ Instalación

### Requisitos

- Python 3.11 o superior
- GROQ_API_KEY (para LLM rápido)
- (Opcional) PostgreSQL para memoria de largo plazo
- (Opcional) Stripe API key para pagos
- (Opcional) Tokens de Meta para WhatsApp/Instagram

### Instalación de dependencias

```bash
pip install -r requirements.txt
```

### Configuración

1. Crea un archivo `.env` en la raíz del proyecto:

```env
GROQ_API_KEY=tu-clave-groq
STRIPE_API_KEY=tu-clave-stripe (opcional)
POSTGRESQL_URL=tu-url-postgresql (opcional)
OPENAI_API_KEY=tu-clave-openai (para embeddings, opcional)
```

2. Configura el agente desde la UI de Gradio (se abre automáticamente).

## 🚀 Uso

### Ejecutar STAR AGENT

```bash
python run_star_agent_ui.py
```

O con Python 3.12:

```bash
py -3.12 run_star_agent_ui.py
```

### Acceder a la UI

Una vez ejecutado, la UI estará disponible en:
- **Local**: http://127.0.0.1:7860
- **Compartido**: Se generará un link público automáticamente

## 📁 Estructura del Proyecto

```
docchat/star_agent/
├── agents/              # Agentes (ReAct, Sales Closer)
│   ├── react_sales_agent.py
│   └── star_agent_agent.py
├── ui/                  # UI de configuración
│   └── gradio_config_ui.py
├── rag/                 # RAG avanzado
│   ├── advanced_rag_manager.py
│   ├── scope_checker.py
│   └── research_agent.py
├── integrations/        # Integraciones externas
│   └── handoff_manager.py
├── ingestion/           # Ingesta automática
│   ├── multi_source_ingester.py
│   └── ingestion_scheduler.py
├── channels/            # Adaptadores de canales
├── sales/               # Sales Closer Elite
├── config/              # Configuración
├── state/               # Gestión de estado
├── tools/               # Herramientas del agente
└── star_agent_mode.py   # Modo principal
```

## 🎯 Características Técnicas

### Stack Tecnológico

- **Python 3.11+**
- **LangChain/LangGraph** - Framework para agentes
- **Gradio** - UI web
- **ChromaDB** - Vector database
- **Groq** - LLM rápido (Llama 3.3 70B)
- **Stripe** - Pagos
- **Playwright** - Web crawling
- **PostgreSQL** - Memoria de largo plazo (opcional)

### Arquitectura

- **Multi-Agent System**: Múltiples agentes colaborando
- **ReAct Pattern**: Reasoning + Acting
- **RAG Avanzado**: Multi-Agent RAG con índices separados
- **Orquestador**: Decision layer inteligente
- **Guardrails**: Seguridad y validación

## 📈 Métricas y Analytics

El agente incluye:
- Tracking de conversiones
- Análisis de sentimiento
- Métricas de rendimiento
- Drop-off tracking
- Análisis de objeciones

## 🔧 Configuración Avanzada

Todas las configuraciones se pueden realizar desde la UI de Gradio sin tocar código:

1. **Configuración Básica**: Nombre, tono, personalidad
2. **RAG Avanzado**: Habilitar/deshabilitar, configuración de índices
3. **Sales Closer**: Estrategias, objeciones, urgencia
4. **Integraciones**: Stripe, Meta, Zendesk
5. **Canales**: WhatsApp, Instagram, Messenger
6. **Ingesta Automática**: Scheduler, fuentes, webhooks
7. **Handoff**: Configuración de triggers y proveedores
8. **Métricas**: Dashboard de analytics

## 📝 Documentación

- Ver `ESTADO_ACTUAL_STAR_AGENT.md` para análisis completo
- Ver `LINEAS_CODIGO_STAR_AGENT.md` para estadísticas de código
- Ver `ACLARACION_APP_PY_VS_STAR_AGENT.md` para diferencias con otros modos

## ⚠️ Notas Importantes

- **NO ejecutes `app.py`** - Ese es el modo DocChat (documentos), no STAR AGENT
- **Ejecuta `run_star_agent_ui.py`** para el STAR AGENT
- El agente requiere GROQ_API_KEY para funcionar
- PostgreSQL es opcional pero recomendado para memoria de largo plazo

## 🤝 Contribuciones

Este es un proyecto propietario. Para sugerencias o mejoras, contacta al equipo de desarrollo.

## 📄 Licencia

[Especificar licencia aquí]

## 🎉 ¡Listo para Producción!

STAR AGENT está completamente implementado y listo para usar en producción.

---

**Versión**: 1.0.0  
**Fecha**: 2025-12-30  
**Líneas de código**: 15,989  
**Archivos**: 63 archivos Python

