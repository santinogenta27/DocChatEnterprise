# Sistema de Agentes AI para Ventas

Sistema de producción orientado a ventas que integra LangGraph, CrewAI, AutoGen y BeeAI para optimización de campañas publicitarias.

## 🎯 Objetivo

Optimizar campañas publicitarias de e-commerce mediante análisis inteligente, optimización de presupuestos, generación de creativos y recomendaciones estratégicas.

## 🏗️ Arquitectura

### Componentes Principales

1. **LangGraph Workflow** (`langgraph_workflow.py`)
   - Orquestación principal del flujo de trabajo
   - Patrones: Routing, Parallelización, Secuencial
   - Estados y transiciones controladas

2. **CrewAI Agents** (`crewai_agents.py`)
   - **Ads Analyst**: Análisis de rendimiento de campañas
   - **Budget Optimizer**: Optimización de presupuestos
   - **Creative Generator**: Generación de creativos publicitarios
   - **Strategy Advisor**: Asesoría estratégica de alto nivel

3. **AutoGen Critique** (`autogen_critique.py`)
   - Sistema de crítica y auto-corrección
   - Debate entre agentes para mejorar outputs
   - Validación de calidad de producción

4. **API Stubs** (`api_stubs.py`)
   - Integración con plataformas de publicidad (Google Ads, Meta Ads)
   - Integración con CRM (Salesforce, HubSpot)
   - Integración con Analytics (Google Analytics)

## 📦 Instalación

```bash
pip install -r requirements.txt
```

## 🚀 Uso Básico

```python
from sales_agent_system import SalesAgentSystem

# Inicializar sistema
system = SalesAgentSystem()

# Ejecutar análisis completo
result = system.run_complete_analysis(
    "Analiza mis campañas y proporciona recomendaciones para mejorar ROI"
)

# Ver resultados
print(result['final_report'])
```

## 🔄 Flujo de Trabajo

1. **Obtención de Datos**: Fetch de campañas desde APIs
2. **Análisis LangGraph**: Workflow orquestado de análisis
3. **Análisis CrewAI**: Agentes especializados generan insights
4. **Crítica AutoGen**: Sistema de mejora iterativa
5. **Compilación Final**: Reporte ejecutivo completo

## 📊 Modelos de Datos

- `CampaignData`: Datos de campañas publicitarias
- `PerformanceMetric`: Métricas de rendimiento
- `OptimizationRecommendation`: Recomendaciones de optimización
- `CreativeSuggestion`: Sugerencias de creativos
- `SalesAnalysisReport`: Reporte completo de análisis

## 🔌 Integraciones

### APIs Soportadas (Stubs)

- **Ads API**: Google Ads, Meta Ads
- **CRM API**: Salesforce, HubSpot
- **Analytics API**: Google Analytics, Adobe Analytics
- **Competitor Analysis**: Análisis de competencia

## 🎨 Patrones Implementados

- **Sequential Agent Coordination**: Flujo secuencial de agentes
- **Intent-Based Routing**: Routing basado en condiciones
- **Parallel Agent Execution**: Ejecución paralela de tareas
- **Reflection Pattern**: Auto-crítica y mejora iterativa
- **Orchestrator-Worker**: Patrón orquestador-trabajador

## 📈 MVP vs V2

### MVP (Actual)
- ✅ Análisis básico de campañas
- ✅ Optimización de presupuestos
- ✅ Generación de creativos
- ✅ Sistema de crítica
- ✅ Integración con APIs (stubs)

### V2 (Futuro)
- 🔄 Integración real con APIs de publicidad
- 🔄 A/B testing automatizado
- 🔄 Predicción de rendimiento con ML
- 🔄 Optimización en tiempo real
- 🔄 Dashboard de visualización
- 🔄 Alertas y notificaciones

## 💰 Modelo de Monetización

### Pricing Sugerido

1. **Starter**: $99/mes
   - Hasta 10 campañas
   - Análisis semanal
   - Recomendaciones básicas

2. **Professional**: $299/mes
   - Hasta 50 campañas
   - Análisis diario
   - Optimización automática
   - Soporte prioritario

3. **Enterprise**: Custom
   - Campañas ilimitadas
   - Análisis en tiempo real
   - Integraciones personalizadas
   - SLA garantizado

## 🔒 Seguridad

- API keys gestionadas mediante variables de entorno
- Validación de inputs con Pydantic
- Manejo de errores robusto
- Logging de todas las operaciones

## 📝 Licencia

Proprietary - Todos los derechos reservados

## 👥 Contribuidores

Sistema desarrollado para DocChat Enterprise



