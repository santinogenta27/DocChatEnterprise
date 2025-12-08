# 🏦 Modo BANKS - Compliance Agent para KYC/AML

Sistema multi-agente especializado en compliance regulatorio para bancos medianos ($1B–$15B assets).

## 🚀 Características Principales

### 1. Procesamiento Masivo de Documentos
- Soporta carpetas con 1000+ documentos
- Formatos: PDF, DOCX, Word, Excel, imágenes (PNG, JPG)
- OCR automático para documentos escaneados
- Particionado inteligente con Unstructured.io

### 2. Extracción de Entidades
- Nombre completo, DNI/ID, dirección
- Beneficiarios finales (UBO)
- Status PEP (Politically Exposed Person)
- Transacciones relevantes (>€10k)

### 3. Screening Automático
- **OFAC** (US Treasury) - Gratuito
- **EU Consolidated List** - Gratuito
- **UN Sanctions** - Gratuito
- **World-Check One API** (LSEG) - Requiere API key
- Fuzzy matching con RapidFuzz
- Verificación PEP
- Búsqueda de adverse media

### 4. Risk Scoring
- Score 1-100 con breakdown detallado
- Categorías: país (40%), PEP (25%), adverse media (20%), transacciones (10%), UBO (5%)
- Explicación completa con evidencia clicable
- Ubicación precisa (página, línea)

### 5. Generación de SARs
- Formato **FinCEN XML** (US)
- Formatos locales: SAGRILAFT (Colombia), UIF (México)
- PDF consolidado con todos los resultados
- Listo para subir al regulador

### 6. Human-in-the-Loop Steering
- Comandos en lenguaje natural
- Re-planificación en tiempo real
- Audit trail completo (todo.md estilo EDR)
- Ejemplos:
  - "Ignora PEP level 1 para clientes España"
  - "Solo flaggea si beneficiario final en Panamá"
  - "Prioriza EU AI Act risks"

### 7. Audit Trail
- Logs inmutables por agente
- Registro de todas las decisiones
- Evidencia completa para reguladores
- Exportable a PDF

## 📋 Arquitectura

### 6 Agentes Especializados

1. **IngestorAgent**: Procesa y particiona documentos
2. **ExtractorAgent**: Extrae entidades con LLM + Pydantic
3. **ScreenerAgent**: Screening contra listas de sanciones
4. **RiskEngineAgent**: Calcula risk scores con explicación
5. **SteeringManagerAgent**: Maneja steering humano
6. **ReportGeneratorAgent**: Genera SARs y reportes

### Workflow LangGraph

```
Ingestor → Extractor → Screener → Risk Engine
                                    ↓
                            [Steering?] → Report Generator
```

## 🔧 Uso

### Desde la Interfaz Gradio

1. Ve a la pestaña **"🏦 BANKS - Compliance KYC/AML"**
2. Sube documentos o proporciona ruta a carpeta/ZIP
3. Selecciona jurisdicción (US, EU, MX, CO, etc.)
4. Opcionalmente añade comandos de steering
5. Ejecuta y recibe resultados

### Desde Código

```python
from docchat.banks import BanksMode
from docchat import load_config

config = load_config()
banks_mode = BanksMode(config)

result = banks_mode.process_compliance_check(
    input_path="/path/to/documents",
    jurisdiction="US",
    steering_commands=["Ignora PEP level 1 para España"]
)

# Acceder a resultados
entities = result["result"]["extracted_entities"]
risk_scores = result["result"]["risk_scores"]
reports = result["result"]["generated_reports"]
```

## 📁 Estructura de Archivos

```
docchat/banks/
├── __init__.py
├── banks_mode.py          # Modo principal
├── workflow.py            # Workflow LangGraph
├── schemas.py            # Schemas Pydantic
├── agents/
│   ├── __init__.py
│   ├── base_agent.py
│   ├── ingestor.py
│   ├── extractor.py
│   ├── screener.py
│   ├── risk_engine.py
│   ├── steering_manager.py
│   └── report_generator.py
└── README.md
```

## 🔗 Integraciones (Próximamente)

- Salesforce Financial Services Cloud
- Jira/ClickUp
- Slack/Teams
- Core Banking (Mambu, Temenos, Finacle)
- World-Check One API (LSEG)
- Dow Jones Risk & Compliance

## 📊 Formatos de Salida

### SAR (Suspicious Activity Report)
- XML FinCEN para US
- JSON para otros países
- Incluye: cliente, actividad sospechosa, score, evidencia

### PDF Consolidado
- Reporte completo con todos los resultados
- Entidades de alto riesgo destacadas
- Explicaciones detalladas

## 🔒 Seguridad y Compliance

- Audit trail completo e inmutable
- Logging de todas las decisiones
- Explainability total (requisito EU AI Act)
- Human oversight en cualquier punto
- Datos encriptados en reposo y tránsito

## 📈 Roadmap

- [ ] Integración con Salesforce FSC
- [ ] Integración con Jira/ClickUp
- [ ] Integración con Slack/Teams
- [ ] World-Check One API completa
- [ ] Certificación EU AI Act
- [ ] On-premise deployment option
- [ ] API REST completa
- [ ] Dashboard de analytics

## 💰 Pricing Model

- **Tier 1** (bancos pequeños): $4,999/mes (hasta 500 onboardings/mes)
- **Tier 2** (medio): $14,999/mes (hasta 2,000)
- **Tier 3** (grande): $29,999–$65k/mes (ilimitado)
- **Setup fee**: $50k–$150k (integración custom)

## 🎯 Target Market

Bancos medianos ($1B–$15B assets) en:
- España, México, Colombia, Chile, Perú
- Portugal, Polonia
- Otros mercados emergentes

## 📚 Referencias

- Deloitte State of AI in Financial Services 2025
- McKinsey AML Compliance Reports
- Capgemini Rise of Agentic AI
- EU AI Act Compliance Requirements
- FinCEN SAR Filing Guidelines

---

**Desarrollado para DocChat Enterprise**  
**Versión 1.0.0 - Diciembre 2025**

