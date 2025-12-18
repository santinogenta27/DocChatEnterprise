# ADS WORKER - AI-Powered Autonomous Advertising Manager

Sistema completo de gestión de anuncios con IA que automatiza la creación, publicación y optimización de campañas publicitarias.

## 🚀 Características

- **Recepción de Assets**: Imágenes, videos y textos de usuarios
- **Análisis Inteligente**: Visión por IA, transcripción de audio, análisis de texto
- **Generación Automática**: Copy y visuales generados con IA
- **Publicación Multi-Plataforma**: Meta (Facebook/Instagram) y Google Ads
- **Optimización en Tiempo Real**: Multi-Armed Bandit, reasignación de presupuesto
- **Agente Autónomo**: LangChain-based agent que orquesta todo el flujo

## 📋 Requisitos

Ver `requirements.txt` para dependencias completas.

Principales:
- Python 3.10+
- FastAPI
- LangChain
- OpenAI API
- Meta Marketing API credentials
- Google Ads API credentials

## 🔧 Configuración

### Variables de Entorno

```bash
# OpenAI
export OPENAI_API_KEY="your-key"

# Meta Ads
export META_ACCESS_TOKEN="your-token"
export META_APP_ID="your-app-id"
export META_APP_SECRET="your-secret"
export META_AD_ACCOUNT_ID="your-account-id"

# Google Ads
export GOOGLE_ADS_CUSTOMER_ID="your-customer-id"
export GOOGLE_ADS_CONFIG_PATH="google-ads.yaml"
```

### Google Ads Config

Crea `google-ads.yaml` en tu directorio home:

```yaml
developer_token: YOUR_DEVELOPER_TOKEN
client_id: YOUR_CLIENT_ID
client_secret: YOUR_CLIENT_SECRET
refresh_token: YOUR_REFRESH_TOKEN
```

## 📖 Uso

### Desde Python

```python
from docchat.ads_worker import AdsWorkerMode
from docchat.ads_worker.models.schemas import AssetUpload, CampaignRequest, AssetType

# Inicializar modo
ads_worker = AdsWorkerMode(config, provider="openai")

# Procesar assets
assets = [
    AssetUpload(
        asset_type=AssetType.IMAGE,
        file_path="/path/to/image.jpg"
    )
]

analyses = ads_worker.process_assets(assets)

# Lanzar campaña
campaign_request = CampaignRequest(
    name="Summer Sale",
    objective="CONVERSIONS",
    budget_daily=50.0,
    asset_ids=[a.asset_id for a in analyses],
    platforms="both"
)

campaign = ads_worker.launch_campaign(campaign_request)
```

### API FastAPI

Los endpoints están disponibles en `/api/ads-worker/`:

- `POST /api/ads-worker/upload-asset` - Subir y analizar asset
- `GET /api/ads-worker/campaigns` - Listar campañas
- `POST /api/ads-worker/launch-campaign` - Lanzar nueva campaña
- `GET /api/ads-worker/campaign/{id}/metrics` - Métricas de campaña
- `POST /api/ads-worker/campaign/{id}/optimize` - Optimizar campaña

## 🏗️ Arquitectura

```
ADS WORKER
├── api/              # FastAPI endpoints
├── services/         # Servicios principales
│   ├── asset_processor.py    # Análisis de assets
│   ├── copy_generator.py    # Generación de copy
│   ├── visual_generator.py  # Generación de visuales
│   ├── meta_ads_service.py  # Integración Meta
│   ├── google_ads_service.py # Integración Google
│   └── optimizer.py         # Optimización automática
├── agents/           # Agente orquestador
│   └── ads_agent.py  # LangChain agent
├── models/           # Schemas Pydantic
└── tests/            # Tests automatizados
```

## 🔄 Flujo de Trabajo

1. **Recepción**: Usuario sube imágenes/videos/textos
2. **Análisis**: IA analiza contenido (visión, audio, texto)
3. **Generación**: Se generan múltiples variaciones de copy y visuales
4. **Publicación**: Se crean campañas en Meta y Google Ads
5. **Optimización**: Sistema optimiza continuamente basado en métricas

## 📊 Optimización

El sistema usa:
- **Multi-Armed Bandit**: Para ranking de anuncios
- **Epsilon-Greedy**: Balance entre exploración y explotación
- **Reasignación de Presupuesto**: Basada en performance
- **Pausa Automática**: Anuncios de bajo rendimiento

## 🧪 Tests

```bash
pytest docchat/ads_worker/tests/
```

## 📝 Notas

- El sistema requiere credenciales válidas de Meta y Google Ads
- Los assets se almacenan localmente por defecto (configurable a S3/GCS)
- La optimización se ejecuta periódicamente (configurable)

## 🔐 Seguridad

- Nunca commitees credenciales
- Usa variables de entorno para secrets
- Valida todos los inputs de usuario
- Implementa rate limiting en producción

