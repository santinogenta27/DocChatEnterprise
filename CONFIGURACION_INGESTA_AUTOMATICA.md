# ⚙️ CONFIGURACIÓN DE INGESTA AUTOMÁTICA MULTI-FUENTE

## 📋 RESUMEN

Se ha implementado el sistema completo de **Ingesta Automática Multi-Fuente** según todas las especificaciones.

---

## ✅ LO QUE SE IMPLEMENTÓ

### 1. ✅ **MultiSourceIngester Completo**
- ✅ Crawlers web (Playwright para JS-heavy sites)
- ✅ APIs Instagram/Facebook (Graph API)
- ✅ Google Business API
- ✅ Normalización semántica + clasificación
- ✅ Chunking inteligente
- ✅ Embeddings automáticos
- ✅ Actualización en Vector DB

### 2. ✅ **Scheduler Automático**
- ✅ Scheduler cada 6h para web (según especificaciones)
- ✅ Scheduler diario para redes sociales
- ✅ Ejecución en background thread

### 3. ✅ **Webhooks para Nuevos Posts**
- ✅ Endpoint `/webhooks/instagram` para nuevos posts de Instagram
- ✅ Endpoint `/webhooks/facebook` para nuevos posts de Facebook
- ✅ Actualización en tiempo real

---

## 🔧 CONFIGURACIÓN

### **Paso 1: Variables de Entorno**

Agrega estas variables a tu archivo `.env`:

```bash
# Ingesta Automática (habilitar)
ENABLE_AUTO_INGESTION=true

# Website
WEBSITE_URL=https://tu-empresa.com

# Instagram Graph API
INSTAGRAM_ACCESS_TOKEN=tu-access-token-de-instagram

# Facebook Graph API
FACEBOOK_ACCESS_TOKEN=tu-access-token-de-facebook
FACEBOOK_PAGE_ID=tu-page-id
FACEBOOK_VERIFY_TOKEN=tu-verify-token-para-webhooks

# Google Business
GOOGLE_BUSINESS_API_KEY=tu-api-key-de-google
GOOGLE_PLACE_ID=tu-place-id-de-google-business
```

### **Paso 2: Obtener Tokens**

#### **Instagram Access Token:**
1. Ve a https://developers.facebook.com/
2. Crea una app
3. Agrega "Instagram Graph API"
4. Genera access token con permisos: `instagram_basic`, `instagram_content_publish`

#### **Facebook Access Token:**
1. Ve a https://developers.facebook.com/
2. Crea una app
3. Agrega "Facebook Login"
4. Genera access token con permisos: `pages_read_engagement`, `pages_read_user_content`

#### **Google Business API Key:**
1. Ve a https://console.cloud.google.com/
2. Crea un proyecto
3. Habilita "Places API"
4. Genera API key

#### **Google Place ID:**
1. Ve a https://www.google.com/maps
2. Busca tu negocio
3. Copia el Place ID de la URL o usa Google Places API

### **Paso 3: Habilitar en Config**

En tu archivo de configuración (`config.py` o `.env`):

```python
# Habilitar ingesta automática
enable_auto_ingestion = True
website_url = "https://tu-empresa.com"
```

---

## 🚀 USO

### **Inicio Automático**

Cuando inicias `StarAgentMode` con `enable_auto_ingestion=True`:

1. **Ingesta inicial automática:**
   - Crawlea tu sitio web
   - Extrae posts de Instagram/Facebook
   - Extrae reviews de Google
   - Indexa todo en RAG automáticamente

2. **Scheduler automático:**
   - Web: Se actualiza cada 6 horas automáticamente
   - Redes sociales: Se actualiza diariamente

3. **Webhooks:**
   - Cuando publicas en Instagram → se indexa automáticamente
   - Cuando publicas en Facebook → se indexa automáticamente

### **Uso Manual (Opcional)**

También puedes ejecutar ingesta manualmente:

```python
from docchat.star_agent import StarAgentMode

# Inicializar con ingesta automática habilitada
star_agent = StarAgentMode(config=config)

# Ejecutar ingesta manual
if star_agent.multi_source_ingester:
    counts = star_agent.multi_source_ingester.ingest_all_sources()
    print(f"Documentos extraídos: {counts}")
```

---

## 📊 ENDPOINTS DE WEBHOOKS

### **Instagram Webhook**

**URL:** `POST /webhooks/instagram`

**Configuración en Instagram:**
1. Ve a https://developers.facebook.com/
2. Configura webhook para tu app
3. URL del webhook: `https://tu-servidor.com/webhooks/instagram`
4. Suscríbete a eventos: `instagram` → `mentions`

### **Facebook Webhook**

**URL:** `POST /webhooks/facebook`

**Configuración en Facebook:**
1. Ve a https://developers.facebook.com/
2. Configura webhook para tu página
3. URL del webhook: `https://tu-servidor.com/webhooks/facebook`
4. Verify Token: El que configuraste en `FACEBOOK_VERIFY_TOKEN`
5. Suscríbete a eventos: `feed` → `posts`

---

## 🔍 VERIFICACIÓN

### **Verificar que funciona:**

1. **Revisar logs:**
   ```
   ✅ Sistema de ingesta multi-fuente inicializado
   ✅ Scheduler configurado: web cada 6h, redes sociales diario
   ✅ Scheduler iniciado en background
   🔄 Ejecutando ingesta inicial de todas las fuentes...
   ✅ Extraídos X documentos del sitio web
   ✅ Extraídos X posts de Instagram
   ✅ Extraídos X posts de Facebook
   ✅ Extraídos X reviews de Google
   ✅ Documentos agregados a RAG avanzado
   ```

2. **Probar webhook:**
   ```bash
   curl -X POST http://localhost:8000/webhooks/instagram \
     -H "Content-Type: application/json" \
     -d '{"entry": [{"id": "test", "caption": "Test post"}]}'
   ```

3. **Verificar scheduler:**
   - Espera 6 horas y revisa logs
   - Deberías ver: `⏰ [SCHEDULER] Iniciando ingesta automática de web`

---

## ⚠️ NOTAS IMPORTANTES

### **Dependencias Requeridas:**

```bash
pip install playwright beautifulsoup4 requests schedule
playwright install chromium
```

### **Límites de APIs:**

- **Instagram Graph API:** 200 requests/hora (suficiente para la mayoría)
- **Facebook Graph API:** 200 requests/hora (suficiente)
- **Google Places API:** Depende de tu plan (gratis: 1000 requests/día)

### **Costo:**

- **Playwright:** Gratis (open source)
- **Instagram/Facebook API:** Gratis (con límites)
- **Google Places API:** Gratis hasta 1000 requests/día, luego $0.017 por request

### **Seguridad:**

- ✅ Los tokens se guardan en variables de entorno (nunca en código)
- ✅ Webhooks verifican tokens antes de procesar
- ✅ Solo procesa contenido público

---

## 🎯 EJEMPLO DE USO COMPLETO

```python
from docchat.config import load_config
from docchat.star_agent import StarAgentMode

# Cargar configuración
config = load_config()

# Habilitar ingesta automática en config
config.enable_auto_ingestion = True
config.website_url = "https://mi-empresa.com"

# Inicializar STAR AGENT
star_agent = StarAgentMode(config=config)

# El sistema automáticamente:
# 1. Crawlea https://mi-empresa.com
# 2. Extrae posts de Instagram/Facebook
# 3. Extrae reviews de Google
# 4. Indexa todo en RAG
# 5. Inicia scheduler (actualiza cada 6h)
# 6. Habilita webhooks para nuevos posts

# Ahora el agente sabe de TODO automáticamente
# Sin intervención humana
```

---

## 📈 RESULTADO

**Antes (sin ingesta automática):**
- ❌ Tienes que subir documentos manualmente
- ❌ Si cambias algo en tu sitio, el agente no lo sabe
- ❌ Si publicas en Instagram, el agente no lo sabe
- ❌ Tiempo: 2-10 horas/mes actualizando manualmente

**Después (con ingesta automática):**
- ✅ Todo se actualiza automáticamente
- ✅ El agente siempre sabe de contenido nuevo
- ✅ Nuevos posts se indexan en tiempo real
- ✅ Tiempo: 0 horas (todo automático)

**Ahorro: 2-10 horas/mes en tiempo manual**

---

*Documento generado: 2025-01-XX*  
*Versión: 1.0.0 - Configuración de Ingesta Automática*

