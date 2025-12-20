# Top Ads Mode - Autonomous AI Agent for Advertising

Sistema completo comparable a **Meta Ads Manager + AI Agent**, diseñado como producto production-ready, multi-tenant, escalable y extensible.

## 🎯 Objetivo Principal

Construir un AI Agent autónomo que:
- Reciba inputs del usuario (imágenes, videos, textos, objetivos, presupuesto)
- Cree, publique, optimice y escale campañas publicitarias automáticamente
- Opere en **Meta Ads** (Facebook, Instagram, WhatsApp) y **TikTok Ads**
- Gestione todo el ciclo de vida publicitario con autonomía configurable

## 🧩 Arquitectura

### 1. Core Agent Layer (Brain)
- **TopAdsCoreAgent**: Motor de razonamiento basado en LLM
- **CampaignPlanner**: Planificación de estrategias de campaña
- **DecisionEngine**: Toma de decisiones basada en autonomía

### 2. Input & Creative Processing Layer
- **AssetProcessor**: Procesamiento multimodal (imágenes, videos, textos)
- **CopyGenerator**: Generación automática de copys publicitarios con variantes A/B

### 3. Campaign Strategy Engine
- Decisión automática de:
  - Tipo de campaña
  - Objetivo (conversions, leads, traffic, etc.)
  - Audiencias (broad, interest-based, lookalike, retargeting)
  - Estructura (Campaign → Ad Sets → Ads)

### 4. Ads Platform Integration Layer
- **MetaAdsPlatform**: Integración real con Meta Marketing API
- **TikTokAdsPlatform**: Integración con TikTok Marketing API

### 5. Optimization & Learning Loop
- **MetricsCollector**: Recolección de métricas (CTR, CPA, ROAS, etc.)
- **CampaignOptimizer**: Optimización automática basada en performance

### 6. Autonomy Control System
- **FULL_AUTONOMOUS**: 🔴 100% autónomo
- **APPROVAL_REQUIRED**: 🟡 Human-in-the-loop
- **RECOMMENDATION_ONLY**: 🟢 Solo recomendaciones

### 7. Logging, Safety & Compliance
- **TopAdsLogger**: Logs estructurados
- **AdsPolicyValidator**: Validación contra políticas de ads

## 📦 Estructura del Proyecto

```
docchat/top_ads/
├── __init__.py
├── agent/
│   ├── __init__.py
│   ├── core_agent.py          # Brain del sistema
│   ├── planner.py             # Planificador de campañas
│   └── decision_engine.py     # Motor de decisiones
├── creatives/
│   ├── __init__.py
│   ├── asset_processor.py     # Procesamiento multimodal
│   └── copy_generator.py      # Generación de copys
├── platforms/
│   ├── __init__.py
│   ├── meta_ads.py            # Integración Meta Ads
│   └── tiktok_ads.py          # Integración TikTok Ads
├── optimization/
│   ├── __init__.py
│   ├── metrics_collector.py   # Recolección de métricas
│   └── optimizer.py           # Optimización automática
└── utils/
    ├── __init__.py
    ├── logger.py              # Sistema de logging
    └── validators.py          # Validación de políticas
```

## 🚀 Uso Básico

```python
from docchat import TopAdsMode, UserInput, CampaignObjective, AutonomyMode
from docchat.config import load_config

# Cargar configuración
config = load_config()

# Inicializar Top Ads Mode
top_ads = TopAdsMode(config=config)

# Crear input del usuario
user_input = UserInput(
    images=["path/to/image1.jpg", "path/to/image2.jpg"],
    videos=["path/to/video1.mp4"],
    texts=["Descripción del producto", "Propuesta de valor"],
    business_objective=CampaignObjective.CONVERSIONS,
    budget=100.0,  # $100 diarios
    autonomy_mode=AutonomyMode.FULL_AUTONOMOUS,
    campaign_name="Mi Campaña Top Ads"
)

# Crear campaña
results = top_ads.create_campaign(
    user_input=user_input,
    platforms=["meta", "tiktok"]
)

# Obtener métricas
for result in results:
    metrics = top_ads.get_campaign_metrics(
        campaign_id=result.campaign_id,
        platform=result.platform
    )
    print(f"Métricas {result.platform}: {metrics}")

# Optimizar campaña
optimization = top_ads.optimize_campaign(
    campaign_id=results[0].campaign_id,
    platform=results[0].platform
)
```

## 🔧 Configuración

### Variables de Entorno Requeridas

#### Meta Ads
```bash
META_ACCESS_TOKEN=tu_access_token
META_APP_ID=tu_app_id
META_APP_SECRET=tu_app_secret
META_AD_ACCOUNT_ID=tu_ad_account_id
```

#### TikTok Ads
```bash
TIKTOK_ACCESS_TOKEN=tu_access_token
TIKTOK_APP_ID=tu_app_id
TIKTOK_APP_SECRET=tu_app_secret
TIKTOK_ADVERTISER_ID=tu_advertiser_id
```

#### OpenAI (para LLM)
```bash
OPENAI_API_KEY=tu_api_key
```

## 📊 Métricas Soportadas

- **Impressions**: Impresiones
- **Clicks**: Clics
- **CTR**: Click-through rate
- **CPC**: Cost per click
- **CPA**: Cost per acquisition
- **ROAS**: Return on ad spend
- **Conversions**: Conversiones
- **Spend**: Gasto total

## 🔄 Flujo de Optimización

1. **Recolección**: Se recolectan métricas de todas las campañas activas
2. **Evaluación**: Se evalúa el performance (score 0-100)
3. **Decisión**: Se decide qué acción tomar basado en performance
4. **Ejecución**: Se aplican optimizaciones automáticas:
   - Ajustar presupuesto
   - Pausar ads malos
   - Escalar ads ganadores
   - Cambiar targeting
   - Regenerar creativos

## 🛡️ Validación de Políticas

El sistema valida automáticamente todos los creativos contra:
- Políticas de Meta Ads
- Políticas de TikTok Ads
- Contenido prohibido
- Claims falsos
- Lenguaje inapropiado

## 📝 Logging

Todos los eventos se registran en:
- Archivos de log rotativos: `.docchat_memory/top_ads_logs/`
- Formato estructurado con timestamps
- Niveles: DEBUG, INFO, WARNING, ERROR, CRITICAL

## 🔮 Próximas Mejoras

- [ ] Integración con Google Ads
- [ ] Reinforcement Learning para optimización
- [ ] Generación de imágenes/videos con IA
- [ ] Dashboard web para visualización
- [ ] API REST para integraciones
- [ ] Multi-tenant completo con aislamiento de datos
- [ ] A/B testing automático avanzado
- [ ] Predicción de performance con ML

## 📚 Referencias

- [Meta Marketing API](https://developers.facebook.com/docs/marketing-apis)
- [TikTok Marketing API](https://ads.tiktok.com/marketing_api/docs)
- [OpenAI Agents](https://platform.openai.com/docs/guides/function-calling)

## ⚠️ Notas Importantes

- El sistema requiere tokens de acceso válidos para cada plataforma
- Las integraciones reales requieren aprobación de Meta y TikTok
- En modo de desarrollo, se pueden usar mocks para testing
- Siempre validar políticas antes de publicar anuncios
- Respetar rate limits de las APIs













