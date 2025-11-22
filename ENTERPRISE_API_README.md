# 🏢 Enterprise API Mode - Guía Completa

## 🎯 ¿Qué es Enterprise API Mode?

Es un modo avanzado que hace **exactamente lo mismo que Consulta RAG**, pero con capacidades adicionales de Agentic AI:

✅ **Procesa documentos automáticamente** (igual que Consulta RAG)  
✅ **Detecta problemas, oportunidades y patrones** sin que se lo pidas  
✅ **Genera resúmenes automáticos** de cada documento  
✅ **Ejecuta acciones** según reglas personalizadas  
✅ **Aprende y mejora** continuamente con nuevos documentos  

---

## 🚀 Cómo Usar

### Opción 1: Desde la UI (Gradio)

1. Ve a la tab **"🏢 Enterprise API"**
2. Sube tus documentos
3. Activa "Detección Automática" (recomendado)
4. Opcional: Agrega reglas en JSON
5. Click en **"🚀 Procesar con Enterprise API"**

### Opción 2: Por API REST

#### Iniciar el servidor API:
```powershell
python api_server.py
```

El servidor estará en: `http://localhost:8000`

#### Documentación interactiva:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

#### Ejemplo de uso con cURL:
```bash
curl -X POST "http://localhost:8000/api/v1/process" \
  -H "Content-Type: multipart/form-data" \
  -F "files=@documento1.pdf" \
  -F "files=@documento2.pdf" \
  -F "auto_detect=true"
```

#### Ejemplo con Python:
```python
import requests

files = [
    ('files', open('documento1.pdf', 'rb')),
    ('files', open('documento2.pdf', 'rb'))
]

response = requests.post(
    'http://localhost:8000/api/v1/process',
    files=files,
    data={'auto_detect': True}
)

results = response.json()
print(results)
```

---

## ⚙️ Reglas y Automatizaciones

Puedes definir reglas que se ejecutan automáticamente cuando se cumplen ciertas condiciones.

### Ejemplo de Reglas (JSON):

```json
[
  {
    "name": "Alerta de Contrato Vencido",
    "type": "condition",
    "condition": {
      "type": "keyword",
      "keyword": "vencimiento"
    },
    "action": {
      "type": "notify",
      "channel": "email",
      "recipient": "legal@empresa.com"
    }
  },
  {
    "name": "Generar Reporte de Problemas Críticos",
    "type": "condition",
    "condition": {
      "type": "problem_detected",
      "problem_type": "legal"
    },
    "action": {
      "type": "generate_report",
      "format": "excel"
    }
  },
  {
    "name": "Marcar para Revisión",
    "type": "condition",
    "condition": {
      "type": "pattern",
      "pattern_name": "anomalía financiera"
    },
    "action": {
      "type": "flag_for_review",
      "priority": "alta"
    }
  }
]
```

### Tipos de Condiciones:

- **keyword**: Busca una palabra clave en los documentos
- **problem_detected**: Se detectó un problema específico
- **pattern**: Se encontró un patrón específico

### Tipos de Acciones:

- **notify**: Enviar notificación (email, Slack, etc.)
- **generate_report**: Generar reporte automático
- **flag_for_review**: Marcar para revisión manual

---

## 📊 Respuesta de la API

La API devuelve un JSON con:

```json
{
  "status": "completed",
  "timestamp": "2025-11-20T21:00:00",
  "documents_processed": 10,
  "chunks_generated": 450,
  "summaries": {
    "documento1.pdf": {
      "summary": "Resumen ejecutivo...",
      "key_points": ["punto 1", "punto 2"],
      "document_type": "contrato",
      "entities": ["Empresa A", "Empresa B"]
    }
  },
  "problems_detected": [
    {
      "type": "riesgo_legal",
      "severity": "alta",
      "description": "Cláusula problemática detectada",
      "source": "documento1.pdf",
      "recommendation": "Revisar con departamento legal"
    }
  ],
  "opportunities_detected": [
    {
      "type": "optimización",
      "impact": "alto",
      "description": "Oportunidad de ahorro identificada",
      "source": "documento2.pdf",
      "action": "Evaluar implementación"
    }
  ],
  "patterns_found": [
    {
      "type": "tendencia",
      "description": "Aumento en contratos de tipo X",
      "frequency": "alta",
      "implication": "Considerar estrategia específica"
    }
  ],
  "actions_taken": [
    {
      "rule": "Alerta de Contrato Vencido",
      "condition_met": true,
      "action_executed": {
        "status": "notified",
        "channel": "email"
      }
    }
  ],
  "insights": [
    {
      "type": "summary",
      "title": "Resumen General",
      "content": "Se procesaron 10 documentos..."
    }
  ]
}
```

---

## 🔧 Configuración

### Variables de Entorno:

```bash
# Puerto del servidor API
API_PORT=8000

# Configuración de Enterprise API
DOCCHAT_ENABLE_AGENTS=true
DOCCHAT_ENABLE_MEMORY=true
DOCCHAT_AGENTIC_MODEL=gpt-4o
```

---

## 💡 Casos de Uso Empresariales

### 1. Procesamiento Masivo de Contratos
- Sube 1000 contratos
- AI detecta automáticamente cláusulas problemáticas
- Genera alertas para el equipo legal

### 2. Análisis de Emails Corporativos
- Conecta tu email corporativo
- AI analiza automáticamente todos los emails
- Detecta oportunidades y problemas

### 3. Due Diligence Automatizado
- Sube documentos de una empresa objetivo
- AI detecta riesgos y oportunidades
- Genera reporte ejecutivo automático

### 4. Monitoreo Continuo
- Configura webhooks
- AI procesa documentos nuevos automáticamente
- Notifica cuando detecta algo importante

---

## 🆚 Comparación con Consulta RAG

| Característica | Consulta RAG | Enterprise API |
|----------------|-------------|----------------|
| Procesa documentos | ✅ | ✅ |
| Responde preguntas | ✅ | ✅ |
| Verificación multi-agente | ✅ | ✅ |
| **Detección automática** | ❌ | ✅ |
| **Resúmenes automáticos** | ❌ | ✅ |
| **Reglas y automatizaciones** | ❌ | ✅ |
| **API REST** | ❌ | ✅ |
| **Aprendizaje continuo** | ⚠️ Básico | ✅ Avanzado |

---

## 🚀 Próximos Pasos

1. **Probar desde la UI**: Ve a la tab "🏢 Enterprise API"
2. **Configurar API**: Ejecuta `python api_server.py`
3. **Integrar con tu sistema**: Usa la API REST
4. **Definir reglas**: Personaliza automatizaciones
5. **Monitorear resultados**: Revisa insights y acciones

---

## 📞 Soporte

Para más información, revisa:
- `ESTADO_SISTEMA.md` - Estado actual del sistema
- `INTEGRACION_COMPLETA.md` - Integraciones disponibles
- `README_ENTERPRISE.md` - Documentación enterprise

---

**¡Tu producto Enterprise API está listo para competir con Harvey, Glean y Casetext!** 🚀

