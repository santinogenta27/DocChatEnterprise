# Arquitectura del Sistema de Agentes AI para Ventas

## 📐 Visión General

Sistema de producción orientado a ventas que integra múltiples frameworks de agentes AI para optimizar campañas publicitarias de e-commerce.

## 🏗️ Arquitectura de Alto Nivel

```
┌─────────────────────────────────────────────────────────────┐
│                    Sales Agent System                        │
│                  (Orquestador Principal)                     │
└─────────────────────────────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
        ▼                   ▼                   ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  LangGraph   │    │   CrewAI     │    │   AutoGen    │
│  Workflow    │    │   Agents     │    │   Critique   │
└──────────────┘    └──────────────┘    └──────────────┘
        │                   │                   │
        └───────────────────┼───────────────────┘
                            │
                            ▼
                ┌───────────────────────┐
                │   API Integrations    │
                │  (Ads, CRM, Analytics)│
                └───────────────────────┘
```

## 🔄 Flujo de Datos

### 1. Entrada del Usuario
```
Usuario → Consulta → SalesAgentSystem
```

### 2. Obtención de Datos
```
SalesAgentSystem → AdsAPIStub → Datos de Campañas
```

### 3. Procesamiento Paralelo

#### 3.1 LangGraph Workflow
```
Fetch Data → Analyze → Optimize → Generate Creatives → Critique → Compile Report
```

#### 3.2 CrewAI Agents
```
Ads Analyst → Budget Optimizer → Creative Generator → Strategy Advisor
```

#### 3.3 AutoGen Critique
```
Critic Agent → Optimizer Agent → Validator Agent
```

### 4. Integración y Salida
```
Todos los resultados → Compilación → Reporte Final
```

## 🧩 Componentes Detallados

### LangGraph Workflow

**Patrón**: Orchestrator-Worker con Routing Condicional

**Nodos**:
1. `fetch_data`: Obtiene datos de campañas
2. `analyze_performance`: Analiza rendimiento
3. `optimize_budget`: Optimiza presupuestos
4. `generate_creatives`: Genera creativos
5. `critique_and_improve`: Critica y mejora
6. `compile_report`: Compila reporte final

**Transiciones**:
- Secuencial: fetch → analyze → optimize
- Paralelo: optimize || generate_creatives
- Condicional: critique → (iterate | finalize)

### CrewAI Agents

**Agentes Especializados**:

1. **Ads Analyst**
   - Rol: Analista de campañas publicitarias
   - Herramientas: SerperDevTool (búsqueda web)
   - Output: Análisis estructurado de rendimiento

2. **Budget Optimizer**
   - Rol: Optimizador de presupuestos
   - Herramientas: Ninguna (análisis interno)
   - Output: Recomendaciones de reasignación

3. **Creative Generator**
   - Rol: Generador de creativos
   - Herramientas: SerperDevTool (análisis de competencia)
   - Output: Headlines, descripciones, CTAs

4. **Strategy Advisor**
   - Rol: Asesor estratégico
   - Herramientas: Ninguna
   - Output: Estrategia de alto nivel

**Flujo CrewAI**:
```
Analysis Task → Optimization Task → Creative Task → Strategy Task
```

### AutoGen Critique System

**Agentes de Crítica**:

1. **Critic Agent**
   - Identifica debilidades
   - Encuentra inconsistencias
   - Sugiere mejoras

2. **Optimizer Agent**
   - Mejora basándose en crítica
   - Corrige problemas
   - Refina estrategias

3. **Validator Agent**
   - Valida calidad final
   - Verifica consistencia
   - Aprueba para producción

**Patrón**: GroupChat con debate colaborativo

## 📊 Modelos de Datos

### Jerarquía de Modelos

```
SalesAnalysisReport (Reporte Principal)
├── CampaignData (Datos de Campaña)
│   └── PerformanceMetric (Métricas)
├── OptimizationRecommendation (Recomendaciones)
├── BudgetAllocation (Asignaciones)
└── CreativeSuggestion (Creativos)
```

### Estado del Workflow

```python
SalesWorkflowState:
  - user_query: str
  - campaign_data: List[Dict]
  - analysis_result: str
  - optimization_result: str
  - creative_result: str
  - critique_result: str
  - final_report: str
  - errors: List[str]
  - iteration_count: int
  - should_continue: bool
```

## 🔌 Integraciones de API

### AdsAPIStub
- `get_campaigns()`: Lista de campañas
- `get_campaign_performance()`: Métricas de rendimiento
- `update_campaign_budget()`: Actualizar presupuesto
- `pause_campaign()`: Pausar campaña
- `resume_campaign()`: Reanudar campaña

### CRMAPIStub
- `get_customer_data()`: Datos de cliente
- `get_sales_funnel_metrics()`: Métricas de embudo

### AnalyticsAPIStub
- `get_website_metrics()`: Métricas del sitio
- `get_conversion_paths()`: Rutas de conversión

### CompetitorAnalysisStub
- `get_competitor_ads()`: Anuncios de competidores
- `get_market_trends()`: Tendencias del mercado

## 🎯 Patrones de Diseño Implementados

### 1. Orchestrator-Worker
- LangGraph orquesta el flujo
- CrewAI agents trabajan en tareas específicas

### 2. Reflection Pattern
- AutoGen critique mejora iterativamente
- Validación antes de finalizar

### 3. Routing Condicional
- Decisión de iterar o finalizar
- Basado en calidad del output

### 4. Parallel Execution
- Optimización y generación de creativos en paralelo
- Mejora eficiencia

### 5. State Management
- Estado compartido entre nodos
- Persistencia de contexto

## 🔒 Manejo de Errores

### Estrategias

1. **Try-Catch en cada nodo**
   - Captura errores específicos
   - Continúa con workflow

2. **Lista de errores en estado**
   - Acumula errores
   - Reporta al final

3. **Validación de datos**
   - Pydantic valida estructuras
   - Previene errores de tipo

4. **Límites de iteración**
   - Previene loops infinitos
   - Máximo 3 iteraciones

## 📈 Escalabilidad

### Horizontal
- Múltiples instancias de agentes
- Distribución de carga

### Vertical
- Optimización de prompts
- Caching de resultados
- Batch processing

## 🚀 Optimizaciones

1. **Caching**
   - Resultados de análisis
   - Datos de campañas

2. **Lazy Loading**
   - Carga datos bajo demanda
   - Reduce latencia inicial

3. **Parallel Processing**
   - Tareas independientes en paralelo
   - Reduce tiempo total

## 🔐 Seguridad

1. **API Keys**
   - Variables de entorno
   - No hardcodeadas

2. **Validación de Inputs**
   - Pydantic schemas
   - Sanitización

3. **Logging**
   - Todas las operaciones
   - Sin datos sensibles

## 📝 Próximos Pasos (V2)

1. **Integraciones Reales**
   - Reemplazar stubs con APIs reales
   - OAuth para autenticación

2. **ML/AI Avanzado**
   - Predicción de rendimiento
   - Clustering de campañas

3. **Tiempo Real**
   - Webhooks para actualizaciones
   - Streaming de resultados

4. **Dashboard**
   - Visualización interactiva
   - Monitoreo en tiempo real

5. **A/B Testing**
   - Automatización de tests
   - Análisis estadístico






