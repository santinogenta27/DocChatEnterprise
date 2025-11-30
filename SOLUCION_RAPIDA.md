# 🚀 Solución Rápida - Desplegar SIN esperar 30 minutos

## ✅ OPCIÓN 1: Ejecutar Trigger Manualmente (MÁS RÁPIDO - 2 minutos)

### Paso 1: Ir a Cloud Build Console
1. Ve a: https://console.cloud.google.com/cloud-build/triggers?project=enterprise-479018
2. Busca el trigger: `rmgpgab-docchat-enterprise-us-central1-santinogenta27-DocChaidj`
3. Click en **"RUN"** (botón de play ▶️)
4. Selecciona branch: `main`
5. Click en **"RUN"**

**Tiempo: 2-3 minutos** ⚡ (más rápido que esperar el auto-build)

---

## ✅ OPCIÓN 2: Descargar Código como ZIP (NO requiere autenticación)

Ejecuta estos comandos en Cloud Shell:

```bash
# Configurar proyecto
gcloud config set project enterprise-479018

# Descargar código como ZIP (no requiere autenticación)
cd ~
wget https://github.com/santinogenta27/DocChatEnterprise/archive/refs/heads/main.zip
unzip main.zip
cd DocChatEnterprise-main

# Construir imagen
docker build -t gcr.io/enterprise-479018/docchat-enterprise .

# Subir imagen
docker push gcr.io/enterprise-479018/docchat-enterprise

# Desplegar (CORREGIDO: sin --cpu-throttling=false)
gcloud run deploy docchat-enterprise \
  --image gcr.io/enterprise-479018/docchat-enterprise \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated \
  --port 8080 \
  --timeout 300 \
  --memory 4Gi \
  --cpu 2 \
  --max-instances 10 \
  --min-instances 0 \
  --concurrency 80
```

**Tiempo: 2-3 minutos** ⚡

---

## ✅ OPCIÓN 3: Usar Cloud Build Submit (Desde GitHub directamente)

```bash
# Configurar proyecto
gcloud config set project enterprise-479018

# Construir desde GitHub directamente (requiere que el repo sea público o tengas acceso)
gcloud builds submit --config=cloudbuild.yaml \
  --source=https://github.com/santinogenta27/DocChatEnterprise.git#main
```

**Nota:** Esto solo funciona si el repo es público o tienes Cloud Build conectado a GitHub.

---

## 🎯 RECOMENDACIÓN: Usa OPCIÓN 1 (Trigger Manual)

Es la más rápida y confiable:
- ✅ No necesitas descargar código
- ✅ Usa la configuración ya probada
- ✅ 2-3 minutos vs 30 minutos
- ✅ Puedes ver los logs en tiempo real

