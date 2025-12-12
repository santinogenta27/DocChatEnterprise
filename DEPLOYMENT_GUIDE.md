# 🚀 GUÍA DE DEPLOYMENT - Ads Optimization Engine

## 📋 PRE-REQUISITOS

### 1. Base de Datos
```bash
# PostgreSQL (recomendado)
sudo apt-get install postgresql postgresql-contrib
sudo -u postgres createdb ads_optimization

# O usar SQLite (fallback automático)
# No requiere instalación
```

### 2. Redis (opcional, recomendado)
```bash
# Ubuntu/Debian
sudo apt-get install redis-server

# macOS
brew install redis

# Windows
# Descargar de: https://github.com/microsoftarchive/redis/releases
```

### 3. Python Dependencies
```bash
pip install -r requirements.txt

# Dependencias adicionales para Ads Optimization
pip install xgboost joblib scikit-learn
pip install tenacity circuitbreaker slowapi
pip install python-json-logger sentry-sdk prometheus-client
pip install google-ads  # Para Google Ads API
```

---

## ⚙️ CONFIGURACIÓN

### 1. Variables de Entorno

Crear archivo `.env`:

```bash
# Base de datos
ADS_DATABASE_URL=postgresql://user:password@localhost:5432/ads_optimization
# O para SQLite (fallback):
# ADS_DATABASE_URL=sqlite:///data/ads_optimization.db

# Redis (opcional)
REDIS_URL=redis://localhost:6379

# Sentry (opcional, para error tracking)
SENTRY_DSN=https://your-sentry-dsn@sentry.io/project-id

# JWT Secret
JWT_SECRET_KEY=your-super-secret-key-change-this

# Monitoring
ENABLE_METRICS_SERVER=true
METRICS_PORT=8000
LOG_LEVEL=INFO

# Meta Ads API
META_ACCESS_TOKEN=your-meta-access-token
META_AD_ACCOUNT_ID=your-meta-ad-account-id

# Google Ads API
GOOGLE_ADS_CUSTOMER_ID=your-customer-id
GOOGLE_ADS_DEVELOPER_TOKEN=your-developer-token
GOOGLE_ADS_CLIENT_ID=your-client-id
GOOGLE_ADS_CLIENT_SECRET=your-client-secret
GOOGLE_ADS_REFRESH_TOKEN=your-refresh-token

# TikTok Ads API
TIKTOK_ACCESS_TOKEN=your-tiktok-token
TIKTOK_ADVERTISER_ID=your-advertiser-id

# OpenAI (para generación de variaciones)
OPENAI_API_KEY=your-openai-api-key
```

### 2. Inicializar Base de Datos

```python
from docchat.ads_optimization.database import DatabaseManager
from docchat.config import AppConfig

config = AppConfig()
db_manager = DatabaseManager(config)
# Las tablas se crean automáticamente
```

### 3. Crear Tenant Inicial

```python
from docchat.ads_optimization.tenant_manager import TenantManager
from pathlib import Path

tenant_manager = TenantManager(Path("data/ads_optimization"))
tenant = tenant_manager.create_tenant(
    name="Mi Empresa",
    email="admin@empresa.com",
    plan="pro"
)
print(f"Tenant creado: {tenant.tenant_id}")
```

---

## 🚀 DEPLOYMENT

### Opción 1: Local Development

```bash
# Iniciar Redis (si se usa)
redis-server

# Iniciar aplicación
python app.py
```

### Opción 2: Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV ADS_DATABASE_URL=postgresql://user:pass@db:5432/ads_optimization
ENV REDIS_URL=redis://redis:6379

CMD ["python", "app.py"]
```

### Opción 3: Cloud (AWS/GCP/Azure)

#### AWS
- **RDS PostgreSQL**: Base de datos
- **ElastiCache Redis**: Cache
- **ECS/EKS**: Contenedores
- **CloudWatch**: Logging

#### GCP
- **Cloud SQL**: PostgreSQL
- **Memorystore**: Redis
- **Cloud Run**: Contenedores
- **Cloud Logging**: Logs

#### Azure
- **Azure Database**: PostgreSQL
- **Azure Cache**: Redis
- **Container Instances**: Contenedores
- **Application Insights**: Monitoring

---

## 📊 MONITORING

### Prometheus Metrics

```bash
# Acceder a métricas
curl http://localhost:8000/metrics
```

### Grafana Dashboard

Importar dashboard desde métricas Prometheus:
- `ads_campaigns_created_total`
- `ads_api_calls_total`
- `ads_prediction_latency_seconds`
- `ads_active_campaigns`
- `ads_total_spend_usd`

### Sentry

Errores se envían automáticamente a Sentry si `SENTRY_DSN` está configurado.

---

## 🔒 SEGURIDAD

### 1. Rotar API Keys

```python
from docchat.ads_optimization.auth import AuthManager

auth = AuthManager(Path("data/ads_optimization"))
# Generar nueva key
new_key = auth.generate_api_key(
    user_id="user_123",
    name="Production Key",
    expires_days=90
)
# Revocar key antigua
```

### 2. Configurar HTTPS

Usar nginx o similar como reverse proxy con SSL.

### 3. Firewall

- Solo exponer puertos necesarios
- Restringir acceso a base de datos
- Rate limiting en nginx

---

## ✅ CHECKLIST DE DEPLOYMENT

- [ ] PostgreSQL instalado y corriendo
- [ ] Redis instalado y corriendo (opcional)
- [ ] Variables de entorno configuradas
- [ ] Base de datos inicializada
- [ ] Tenant inicial creado
- [ ] API keys de publicidad configuradas
- [ ] Tests pasando (`pytest tests/test_ads_optimization.py`)
- [ ] Monitoring configurado (Prometheus/Sentry)
- [ ] Logs funcionando
- [ ] Backup de base de datos configurado
- [ ] HTTPS configurado
- [ ] Firewall configurado

---

## 🐛 TROUBLESHOOTING

### Error: "Database connection failed"
- Verificar `ADS_DATABASE_URL`
- Verificar que PostgreSQL esté corriendo
- Verificar credenciales

### Error: "Redis connection failed"
- Verificar `REDIS_URL`
- Verificar que Redis esté corriendo
- Sistema usará fallback in-memory si Redis no está disponible

### Error: "Rate limit exceeded"
- Verificar cuotas del tenant
- Upgrade a plan superior
- Verificar rate limits de APIs externas

### Error: "Quota exceeded"
- Verificar plan del tenant
- Upgrade a plan superior
- Verificar uso actual

---

## 📈 ESCALAMIENTO

### Horizontal Scaling
- Múltiples instancias detrás de load balancer
- Redis compartido para cache
- PostgreSQL con replicación

### Vertical Scaling
- Aumentar recursos de servidor
- Optimizar queries de base de datos
- Cache más agresivo

---

## 💰 COSTOS ESTIMADOS

### Infraestructura (mensual)
- **PostgreSQL (RDS)**: $50-200
- **Redis (ElastiCache)**: $30-100
- **Servidor (EC2)**: $50-500
- **Sentry**: $26-99
- **Total**: ~$156-899/mes

### Por Cliente (PRO)
- **Base**: $99/mes
- **Uso adicional**: Variable
- **Margen**: ~60-70%

---

## 🎯 CONCLUSIÓN

El sistema está **100% listo para deployment en producción**.

Sigue esta guía paso a paso y tendrás el sistema corriendo en producción en menos de 1 hora.

