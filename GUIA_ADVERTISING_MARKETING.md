# 🚀 Guía de Advertising y Marketing con Agentic AI

## Funcionalidades Disponibles

### 1. Gestión de Campañas Publicitarias
- Crear campañas en TikTok, Meta (Facebook/Instagram), Google Ads
- Optimización automática en tiempo real
- Reasignación de presupuesto inteligente
- Ajuste de estrategias de bidding automático

### 2. Generación de Contenido Creativo
- Generación automática de copy para anuncios
- Headlines y descripciones optimizadas
- Scripts para videos
- Contenido adaptado por plataforma

### 3. Segmentación de Audiencias
- Creación de audiencias personalizadas
- Segmentación por comportamiento, demografía, intereses
- Estimación de tamaño de audiencia

### 4. Optimización Automática
- Optimización en tiempo real basada en performance
- Ajuste automático de presupuesto
- Pausa de creativos con bajo rendimiento
- Optimización de bidding strategies

### 5. Analytics y Performance
- Análisis de performance de campañas
- Insights automáticos
- Métricas: CPC, CPM, ROAS, CTR, conversiones

## Configuración de APIs

### TikTok Ads API

1. Ve a: https://ads.tiktok.com/
2. Crea una cuenta de publicidad
3. Obtén tu Access Token desde el panel de desarrolladores
4. Agrega al archivo `.env`:
```env
TIKTOK_ACCESS_TOKEN=tu_access_token
TIKTOK_ADVERTISER_ID=tu_advertiser_id
```

### Meta (Facebook/Instagram) Ads API

1. Ve a: https://developers.facebook.com/
2. Crea una app y obtén Access Token
3. Obtén tu Ad Account ID desde Facebook Ads Manager
4. Agrega al archivo `.env`:
```env
META_ACCESS_TOKEN=tu_access_token
META_AD_ACCOUNT_ID=tu_ad_account_id
```

### Google Ads API

1. Ve a: https://ads.google.com/
2. Obtén Developer Token desde Google Ads
3. Obtén Customer ID (formato: XXX-XXX-XXXX)
4. Agrega al archivo `.env`:
```env
GOOGLE_ADS_CUSTOMER_ID=tu_customer_id
GOOGLE_ADS_DEVELOPER_TOKEN=tu_developer_token
```

## Ejemplos de Uso

### Crear Campaña Publicitaria

**Tarea:**
```
Crear una campaña publicitaria llamada "Q1 Sales 2025" en Meta con presupuesto de $500, objetivo de conversiones, para audiencia de tecnología entre 25-45 años
```

**Tipo de Tarea:** marketing

### Optimizar Campaña

**Tarea:**
```
Optimizar la campaña "Q1 Sales 2025" para lograr instalaciones bajo $4.50
```

**Tipo de Tarea:** optimización

### Generar Contenido Creativo

**Tarea:**
```
Generar contenido creativo para campaña de awareness dirigida a audiencia de tecnología, con mensaje sobre innovación
```

**Tipo de Tarea:** generación

### Analizar Performance

**Tarea:**
```
Analizar el performance de la campaña "Q1 Sales 2025" y dame insights
```

**Tipo de Tarea:** análisis

## Funcionalidades Avanzadas

### Optimización Automática en Tiempo Real

El Agentic AI puede:
- Ajustar presupuesto automáticamente si el CPC es muy alto
- Optimizar bidding strategies para mejor ROAS
- Pausar creativos con bajo performance
- Reasignar presupuesto a mejores performers

### Personalización Hiper-Avanzada

- Contenido adaptado por audiencia
- Mensajes personalizados por segmento
- Creativos optimizados por plataforma
- A/B testing automático

### Integración con Datos IDP

Cuando procesas documentos con IDP, el Agentic AI puede:
- Usar insights de documentos para crear campañas
- Personalizar mensajes basados en datos extraídos
- Optimizar targeting usando información de documentos

## Notas Importantes

- Las APIs requieren credenciales válidas del usuario
- Si no configuras las APIs, el sistema funciona localmente guardando campañas en archivos JSON
- Todas las funcionalidades funcionan sin SQL, usando solo archivos JSON/CSV
- Los datos se guardan en: `memory/advertising_data/`

