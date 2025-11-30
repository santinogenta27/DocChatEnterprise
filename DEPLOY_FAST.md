# 🚀 Despliegue Rápido en Cloud Run (2-3 minutos)

## ✅ OPCIÓN 1: Cloud Shell (RECOMENDADA - 2-3 minutos)

### Paso 1: Abrir Cloud Shell
1. Ve a [Google Cloud Console](https://console.cloud.google.com)
2. Click en el ícono de **Cloud Shell** (terminal) en la esquina superior derecha
3. Espera a que se abra (30 segundos)

### Paso 2: Clonar tu repositorio
```bash
cd ~
git clone https://github.com/santinogenta27/DocChatEnterprise.git
cd DocChatEnterprise
git checkout main
```

### Paso 3: Ejecutar el script de despliegue
```bash
bash deploy-fast.sh
```

**Tiempo total: 2-3 minutos** ⚡

---

## ✅ OPCIÓN 2: Comandos Manuales en Cloud Shell

Si prefieres ejecutar los comandos uno por uno:

```bash
# Configurar proyecto
gcloud config set project enterprise-479018

# Construir imagen
docker build -t gcr.io/enterprise-479018/docchat-enterprise .

# Subir imagen
docker push gcr.io/enterprise-479018/docchat-enterprise

# Desplegar
gcloud run deploy docchat-enterprise \
  --image gcr.io/enterprise-479018/docchat-enterprise \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated \
  --port 8080 \
  --timeout 300 \
  --memory 4Gi \
  --cpu 2 \
  --cpu-throttling=false
```

---

## ✅ OPCIÓN 3: Desactivar Cloud Build Trigger (Evitar builds automáticos)

1. Ve a **Cloud Build → Triggers**
2. Busca el trigger: `rmgpgab-docchat-enterprise-us-central1-santinogenta27-DocChaidj`
3. Click en **Disable** (desactivar)
4. Ahora Cloud Run NO compilará automáticamente

---

## ✅ OPCIÓN 4: Rollback a Revisión Anterior (5 segundos)

Si quieres volver a una versión que funcionaba:

1. Ve a **Cloud Run → docchat-enterprise → Revisions**
2. Busca una revisión anterior que funcionaba
3. Click en **"..." → Deploy 100% of traffic**
4. **Tiempo: 5 segundos** ⚡

---

## 📊 Comparación de Tiempos

| Método | Tiempo | Ventajas |
|--------|--------|----------|
| Cloud Build Trigger | 20-30 min | Automático |
| Cloud Shell (este script) | 2-3 min | Rápido, control total |
| Rollback | 5 seg | Instantáneo |

---

## 🎯 Recomendación

**Usa Cloud Shell con el script `deploy-fast.sh`**:
- ✅ Rápido (2-3 minutos)
- ✅ Puedes ver los logs en tiempo real
- ✅ No esperas 30 minutos
- ✅ Sabes inmediatamente si funciona

