# 📚 Documentación Técnica - Modo BANKS

## 🏗️ Arquitectura del Sistema

### Componentes Principales

```
┌─────────────────────────────────────────────────────────┐
│                   Gradio UI Layer                        │
│  (Interfaz Web + Dashboard + Configuración)            │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│                  BanksMode (Orchestrator)               │
│  - process_compliance_check()                           │
│  - process_batch_compliance()                           │
│  - get_reports_summary()                                │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│              BanksWorkflow (LangGraph)                  │
│  - Orchestrates 7 agents                                │
│  - State management                                     │
│  - Conditional routing                                  │
└────────────────────┬────────────────────────────────────┘
                     │
        ┌────────────┼────────────┐
        │            │            │
┌───────▼────┐ ┌────▼────┐ ┌─────▼─────┐
│  Ingestor  │ │Extractor│ │  Screener  │
└────────────┘ └─────────┘ └────────────┘
        │            │            │
┌───────▼────┐ ┌────▼────┐ ┌─────▼─────┐
│Risk Engine │ │ Steering │ │  Report   │
└────────────┘ └─────────┘ └────────────┘
        │
┌───────▼────┐
│   Action   │
│  Executor  │
└────────────┘
```

## 🔧 Agentes Especializados

### 1. IngestorAgent
**Responsabilidad:** Procesamiento masivo de documentos

**Tecnologías:**
- `unstructured.io` - Particionado inteligente
- `Tesseract OCR` - OCR para imágenes
- `pdf2image` - Conversión PDF a imagen

**Input:**
- Carpeta/ZIP/archivo individual
- Formatos: PDF, DOCX, DOC, TXT, XLSX, XLS, PNG, JPG, JPEG

**Output:**
- Lista de documentos procesados
- Chunks con metadata
- Total de chunks procesados

**Métodos clave:**
```python
process(state) -> Dict[str, Any]
_process_document(doc_path) -> Dict[str, Any]
_extract_zip(zip_path) -> List[str]
_scan_directory(directory) -> List[str]
```

### 2. ExtractorAgent
**Responsabilidad:** Extracción de entidades estructuradas

**Tecnologías:**
- `Claude 3.5 Sonnet` - LLM principal
- `Pydantic` - Validación de schemas
- `LangChain` - Orchestration

**Input:**
- Documentos procesados (chunks)

**Output:**
- Lista de `EntityExtraction`
- Campos: name, id_number, address, ubo, pep_status, transactions

**Precisión objetivo:** >97%

### 3. ScreenerAgent
**Responsabilidad:** Screening contra listas de sanciones

**Tecnologías:**
- `RapidFuzz` - Fuzzy matching
- `World-Check One API` - Screening premium
- `requests` - APIs gratuitas (OFAC, EU, UN)

**Input:**
- Entidades extraídas

**Output:**
- `SanctionHit[]`
- `PEPHit[]`
- `AdverseMediaHit[]`

**Listas verificadas:**
- OFAC (US Treasury) - Gratuito
- EU Consolidated List - Gratuito
- UN Sanctions - Gratuito
- World-Check One (LSEG) - Requiere API key

### 4. RiskEngineAgent
**Responsabilidad:** Cálculo de risk score con explicación

**Algoritmo:**
```
total_score = (
    country_risk * 0.4 +
    pep_risk * 0.25 +
    adverse_media_risk * 0.2 +
    transaction_risk * 0.1 +
    ubo_risk * 0.05
) * 100
```

**Output:**
- `RiskScore` con breakdown detallado
- Explicación completa
- Evidencia clicable (página, línea)

### 5. SteeringManagerAgent
**Responsabilidad:** Human-in-the-loop steering

**Capacidades:**
- Parseo de comandos en lenguaje natural
- Re-planificación de workflow
- Actualización de estado
- Audit trail en `todo.md`

**Ejemplos de comandos:**
- "Ignora PEP level 1 para clientes España"
- "Solo flaggea si beneficiario final en Panamá"
- "Prioriza EU AI Act risks"

### 6. ReportGeneratorAgent
**Responsabilidad:** Generación de SARs y reportes

**Formatos soportados:**
- FinCEN XML (US)
- SAGRILAFT (Colombia)
- UIF (México)
- PDF consolidado

**Tecnologías:**
- `Jinja2` - Templates
- `WeasyPrint` - PDF generation

### 7. ActionExecutorAgent
**Responsabilidad:** Acciones en sistemas externos

**Integraciones:**
- Salesforce Financial Services Cloud
- Jira/ClickUp
- Slack/Teams
- Core Banking (webhooks)

## 📊 Estado del Workflow (BanksState)

```python
class BanksState(TypedDict):
    input_path: str
    documents: list
    processed_documents: list
    extracted_entities: list
    sanction_hits: list
    pep_hits: list
    adverse_media_hits: list
    risk_scores: list
    steering_commands: list
    steering_applied: list
    generated_reports: list
    actions_executed: list
    action_config: dict
    jurisdiction: str
    errors: list
    workflow_updated: bool
    needs_reprocessing: bool
    batch_mode: bool
    client_id: str
```

## 🔐 Seguridad y Compliance

### Encriptación
- **En reposo:** AES-256 (pendiente implementación completa)
- **En tránsito:** TLS 1.3 (requiere configuración de servidor)

### Audit Trail
- Logs inmutables por agente
- Formato JSON con timestamps
- Ubicación: `.docchat_audit/banks/`

### EU AI Act Compliance
- Explainability total
- Human oversight
- Logging completo
- Impact assessment (pendiente documentación)

## 🚀 Deployment

### Requisitos del Sistema
- Python 3.10+
- 8GB RAM mínimo (16GB recomendado)
- 50GB disco para cache y logs

### Dependencias Principales
```bash
pip install langgraph langchain-anthropic langchain-openai
pip install unstructured[all-docs] rapidfuzz
pip install fastapi uvicorn  # Para API REST
pip install simple-salesforce atlassian-python-api  # Integraciones opcionales
```

### Variables de Entorno
```bash
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
WORLDCHECK_API_KEY=...  # Opcional
SALESFORCE_USERNAME=...
SALESFORCE_PASSWORD=...
SALESFORCE_SECURITY_TOKEN=...
JIRA_URL=...
JIRA_USERNAME=...
JIRA_API_TOKEN=...
SLACK_WEBHOOK_URL=...
TEAMS_WEBHOOK_URL=...
```

## 📡 API REST

### Endpoints Principales

#### `GET /health`
Health check del sistema.

#### `POST /api/v1/compliance/check`
Ejecuta compliance check.

**Request:**
```json
{
  "input_path": "/path/to/documents",
  "jurisdiction": "US",
  "steering_commands": ["Ignora PEP level 1"],
  "action_config": {
    "update_salesforce": false,
    "create_jira_ticket": true
  },
  "client_id": "CLIENT_001"
}
```

**Response:**
```json
{
  "success": true,
  "result": {...},
  "entities_count": 5,
  "risk_scores_count": 5,
  "reports_generated": 2,
  "actions_executed": 1,
  "errors": [],
  "processing_time_seconds": 12.5
}
```

#### `POST /api/v1/compliance/check/batch`
Procesamiento por lotes.

#### `POST /api/v1/compliance/check/upload`
Upload de archivos directamente.

#### `GET /api/v1/reports`
Lista todos los reportes.

#### `GET /api/v1/reports/{report_name}`
Descarga un reporte específico.

## 🔧 Configuración de Reglas

### Ubicación
`.docchat_cache/banks/config/business_rules.json`

### Estructura
```json
{
  "risk_scoring": {
    "weights": {
      "country_risk": 0.4,
      "pep_risk": 0.25,
      "adverse_media_risk": 0.2,
      "transaction_risk": 0.1,
      "ubo_risk": 0.05
    },
    "thresholds": {
      "low_risk": 30,
      "medium_risk": 50,
      "high_risk": 70,
      "critical_risk": 90
    }
  },
  "high_risk_countries": [...],
  "whitelist": [...],
  "blacklist": [...]
}
```

## 📈 Performance

### Benchmarks Esperados
- **Procesamiento:** 10-50 documentos/minuto
- **Screening:** 100-500 entidades/minuto
- **Risk scoring:** <1 segundo por entidad
- **Generación de SAR:** <5 segundos por reporte

### Escalabilidad
- **Horizontal:** Sharding de agentes
- **Vertical:** Más CPU/RAM para procesamiento paralelo
- **Cache:** Redis para resultados de screening

## 🧪 Testing

### Tests Unitarios
```bash
pytest docchat/banks/tests/
```

### Tests de Integración
```bash
pytest docchat/banks/tests/integration/
```

### Datos de Prueba
- Datos anonimizados de clientes reales
- Synthetic data generator
- Casos edge (documentos rotos, formatos raros)

## 🐛 Troubleshooting

### Error: "No se procesaron documentos"
**Causa:** Ruta incorrecta o sin permisos
**Solución:** Verificar ruta y permisos de lectura

### Error: "World-Check API falló"
**Causa:** API key inválida o sin créditos
**Solución:** Verificar credenciales, usar fallbacks gratuitos

### Error: "Risk score fuera de rango"
**Causa:** Pesos de risk scoring no suman 1.0
**Solución:** Verificar configuración de reglas

## 📞 Soporte

- **Documentación:** `docchat/banks/README.md`
- **Issues:** GitHub Issues
- **Email:** support@docchat.ai

---

**Versión:** 1.0.0  
**Última actualización:** Diciembre 2025


