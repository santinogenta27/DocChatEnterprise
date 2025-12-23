# ✅ Implementación: Métricas Reales desde APIs (MVP)

## 🎯 Objetivo Cumplido

Implementación SIMPLE para obtener métricas reales de Meta Ads API y Google Ads API.

---

## ✅ LO QUE SE IMPLEMENTÓ

### 1. Módulo `metrics_fetcher.py` ✅

**Funciones principales:**

1. **`get_meta_campaign_metrics()`**
   - Obtiene métricas de Meta Ads API
   - Usa date_preset (last_7d, last_28d, last_90d, lifetime)
   - Retorna: impressions, clicks, spend, conversions, ctr, cpc
   - Maneja errores básicos

2. **`get_google_campaign_metrics()`**
   - Obtiene métricas de Google Ads API
   - Usa start_date y end_date (datetime)
   - Retorna: impressions, clicks, spend, conversions, ctr, cpc
   - Maneja errores básicos

3. **`fetch_and_save_campaign_metrics()`**
   - Función principal que:
     - Obtiene métricas de Meta y/o Google según la campaña
     - Calcula totales agregados
     - Guarda en PostgreSQL usando `save_metrics()`
     - Retorna resumen de métricas

---

### 2. Botón en UI ✅

**Ubicación:** Dashboard de Métricas
**Botón:** "📊 Actualizar Métricas Reales (API)"
**Funcionalidad:**
- Llama a `fetch_and_save_campaign_metrics()`
- Muestra status de la operación
- Actualiza dashboard automáticamente después

---

## 📊 MÉTRICAS QUE SE OBTIENEN

### Meta Ads API:
- ✅ Impressions
- ✅ Clicks
- ✅ Spend (gasto)
- ✅ Conversions (desde actions)
- ✅ CTR (convertido a porcentaje)
- ✅ CPC

### Google Ads API:
- ✅ Impressions
- ✅ Clicks
- ✅ Cost (convertido a spend en dólares)
- ✅ Conversions
- ✅ CTR (ya viene calculado)
- ✅ CPC (average_cpc convertido)

---

## 🔧 CÓMO FUNCIONA

### Flujo completo:

1. Usuario hace click en "📊 Actualizar Métricas Reales (API)"
2. Sistema obtiene información de la campaña desde BD
3. Identifica plataformas (meta, google, both)
4. Para cada plataforma:
   - Llama a `get_meta_campaign_metrics()` o `get_google_campaign_metrics()`
   - Obtiene métricas desde la API
   - Calcula CTR y CPC si no vienen
   - Guarda en BD con `save_metrics()`
5. Agrega métricas de todas las plataformas
6. Calcula totales (CTR, CPC agregados)
7. Muestra status al usuario
8. Actualiza dashboard automáticamente

---

## 🚀 USO

### Paso 1: Seleccionar Campaña
- Ir al Dashboard de Métricas
- Seleccionar campaña del dropdown
- (Click en "🔄 Cargar Campañas" si no hay campañas)

### Paso 2: Actualizar Métricas
- Ajustar período en días (si necesario)
- Click en "📊 Actualizar Métricas Reales (API)"
- Esperar (puede tomar unos segundos)

### Paso 3: Ver Resultados
- Dashboard se actualiza automáticamente
- Ver métricas reales (no más 0)
- Exportar CSV si necesario

---

## ⚠️ MANEJO DE ERRORES

### Errores que se manejan:

1. **Token inválido / API no disponible**
   - Retorna métricas en 0
   - Muestra error en logs
   - No rompe el flujo

2. **Campaña no encontrada**
   - Retorna error claro
   - No intenta obtener métricas

3. **División por cero**
   - CTR = 0 si impressions = 0
   - CPC = 0 si clicks = 0

4. **Servicio no disponible**
   - Retorna métricas en 0 para esa plataforma
   - Continúa con otras plataformas

---

## 📋 ARCHIVOS

### Nuevos:
- `docchat/advertising_top_manager/metrics_fetcher.py` - Módulo completo

### Modificados:
- `DocChatEnterprise/app.py` - Botón y handler en dashboard

---

## ✅ RESULTADO

**El dashboard ahora puede mostrar números reales distintos de 0.**

Cuando el usuario hace click en "Actualizar Métricas Reales":
- Se obtienen datos de Meta/Google Ads API
- Se guardan en PostgreSQL
- El dashboard muestra números reales

**Simple, funcional, MVP listo para usar.**

---

## 🔄 PRÓXIMOS PASOS (Opcionales)

1. Actualización automática periódica (jobs)
2. Webhooks para actualización en tiempo real
3. Más métricas (ROAS, CPA, etc.)
4. Métricas por ad individual (no solo campaña)

Pero **YA FUNCIONA** para el objetivo principal: mostrar números reales.

