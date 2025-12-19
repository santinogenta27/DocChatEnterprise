# ADS WORKER - Guía de Producción

## 🚀 Estado: Listo para Producción

El sistema ADS WORKER está completamente implementado y optimizado para producción con:

- ✅ Base de datos para persistencia (SQLite/PostgreSQL)
- ✅ Logging estructurado
- ✅ Retry logic y manejo robusto de errores
- ✅ Validaciones de entrada
- ✅ Procesamiento asíncrono con colas
- ✅ Rate limiting
- ✅ Arquitectura modular y escalable

## 📋 Instalación

### 1. Instalar Dependencias

```bash
pip install -r docchat/ads_worker/requirements.txt
```

### 2. Configurar Variables de Entorno

Crear archivo `.env` o exportar variables:

```bash
# OpenAI (REQUERIDO)
export OPENAI_API_KEY="sk-..."

# Meta Ads (Opcional pero recomendado)
export META_ACCESS_TOKEN="your-token"
export META_APP_ID="your-app-id"
export META_APP_SECRET="your-secret"
export META_AD_ACCOUNT_ID="your-account-id"
export META_PAGE_ID="your-page-id"  # Requerido para creatives

# Google Ads (Opcional pero recomendado)
export GOOGLE_ADS_CUSTOMER_ID="your-customer-id"
export GOOGLE_ADS_CONFIG_PATH="google-ads.yaml"

# Base de datos (Opcional - usa SQLite por defecto)
export ADS_WORKER_DB_URL="postgresql://user:pass@localhost/ads_worker"

# Configuración
export ADS_WORKER_MAX_WORKERS=4
export ADS_WORKER_STORAGE_PATH="./assets"
```

### 3. Configurar Google Ads

Crear `google-ads.yaml` en directorio home:

```yaml
developer_token: YOUR_TOKEN
client_id: YOUR_CLIENT_ID
client_secret: YOUR_SECRET
refresh_token: YOUR_REFRESH_TOKEN
```

## 🔧 Uso

### Desde Python

```python
from docchat.ads_worker import AdsWorkerMode
from docchat.ads_worker.models.schemas import AssetUpload, CampaignRequest, AssetType

# Inicializar (ya está en app.py)
ads_worker = AdsWorkerMode(config, provider="openai")

# Procesar assets
assets = [
    AssetUpload(
        asset_type=AssetType.IMAGE,
        file_path="/path/to/image.jpg",
        metadata={"product_name": "Product X"}
    )
]

analyses = ads_worker.process_assets(assets, user_id="user_123")

# Lanzar campaña
campaign = ads_worker.launch_campaign(
    CampaignRequest(
        name="Summer Sale",
        objective="CONVERSIONS",
        budget_daily=50.0,
        asset_ids=[a["asset_id"] for a in analyses],
        platforms="both"
    ),
    user_id="user_123"
)

# Optimizar campaña
optimization = ads_worker.optimize_campaign(campaign.campaign_id)
```

### Desde API REST

```bash
# 1. Subir asset
curl -X POST "http://localhost:7860/api/ads-worker/upload-asset" \
  -H "X-User-ID: user_123" \
  -F "file=@image.jpg" \
  -F "asset_type=image" \
  -F 'metadata={"product_name": "Product X"}'

# 2. Lanzar campaña
curl -X POST "http://localhost:7860/api/ads-worker/launch-campaign" \
  -H "Content-Type: application/json" \
  -H "X-User-ID: user_123" \
  -d '{
    "name": "Summer Sale",
    "objective": "CONVERSIONS",
    "budget_daily": 50.0,
    "asset_ids": ["asset_123"],
    "platforms": "both"
  }'

# 3. Obtener métricas
curl "http://localhost:7860/api/ads-worker/campaign/campaign_123/metrics?hours=24"

# 4. Optimizar
curl -X POST "http://localhost:7860/api/ads-worker/campaign/campaign_123/optimize"
```

## 📊 Arquitectura de Producción

```
ADS WORKER
├── Database Layer (SQLite/PostgreSQL)
│   ├── Assets
│   ├── Creatives
│   ├── Campaigns
│   ├── Ads
│   ├── Performance Metrics
│   └── Optimization History
│
├── Service Layer
│   ├── Asset Processor (con retry logic)
│   ├── Copy Generator (con rate limiting)
│   ├── Visual Generator
│   ├── Meta Ads Service (con retry)
│   ├── Google Ads Service (con retry)
│   └── Optimizer (MAB)
│
├── Agent Layer
│   └── LangChain Agent (orquestador)
│
├── API Layer
│   └── FastAPI endpoints (con validación)
│
└── Queue System
    └── ThreadPoolExecutor (procesamiento async)
```

## 🔒 Seguridad y Mejores Prácticas

1. **Credenciales**: Nunca commitees credenciales. Usa variables de entorno.
2. **Validación**: Todos los inputs son validados con Pydantic.
3. **Rate Limiting**: Copy Generator tiene rate limiting integrado.
4. **Retry Logic**: Todos los servicios tienen retry con backoff exponencial.
5. **Logging**: Logging estructurado para debugging y monitoreo.
6. **Error Handling**: Manejo robusto de errores en todos los niveles.

## 📈 Escalabilidad

### Para Bajo Presupuesto:
- SQLite para desarrollo/pruebas
- Procesamiento en serie (ajustar `max_workers`)
- Almacenamiento local de assets

### Para Producción:
- PostgreSQL para base de datos
- Aumentar `max_workers` para más paralelismo
- S3/GCS para almacenamiento de assets
- Celery para colas distribuidas (opcional)

## 🧪 Tests

```bash
# Ejecutar tests
pytest docchat/ads_worker/tests/ -v

# Con coverage
pytest docchat/ads_worker/tests/ --cov=docchat/ads_worker --cov-report=html
```

## 📝 Logs

Los logs se guardan en:
- Consola: INFO y superior
- Archivo (si se configura): DEBUG y superior

Ubicación por defecto: `./logs/ads_worker.log`

## 🐳 Docker (Opcional)

```dockerfile
FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONUNBUFFERED=1
CMD ["python", "app.py"]
```

## ✅ Checklist de Producción

- [x] Base de datos implementada
- [x] Logging estructurado
- [x] Retry logic en servicios
- [x] Validación de inputs
- [x] Manejo de errores robusto
- [x] Procesamiento asíncrono
- [x] Rate limiting
- [x] Documentación completa
- [x] Tests básicos
- [ ] Tests de integración completos (pendiente)
- [ ] Dashboard web (opcional)
- [ ] Monitoreo y alertas (opcional)

## 🎯 Próximos Pasos

1. **Tests de Integración**: Tests completos con mocks de APIs
2. **Dashboard**: Interfaz web para visualizar campañas
3. **Monitoreo**: Integración con Prometheus/Grafana
4. **Más Plataformas**: TikTok Ads, LinkedIn Ads
5. **ML Avanzado**: Modelos de predicción de performance

## 📞 Soporte

Para problemas o preguntas, revisa:
- `README.md` - Documentación general
- `IMPLEMENTACION_COMPLETA.md` - Detalles técnicos
- Logs en `./logs/ads_worker.log`

¡El sistema está listo para producción! 🚀




