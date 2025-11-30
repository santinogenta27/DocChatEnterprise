# 🚀 Ejecutar Build Directamente (Sin Trigger)

## Desde Cloud Shell:

### 1. Abre Cloud Shell
- Ve a: https://console.cloud.google.com/cloudshell
- O click en el ícono de terminal en la consola

### 2. Clona o navega a tu repositorio
```bash
git clone https://github.com/santinogenta27/DocChatEnterprise.git
cd DocChatEnterprise
```

### 3. Ejecuta el build directamente
```bash
gcloud builds submit --config=cloudbuild.yaml --region=us-central1
```

### 4. O con el proyecto específico
```bash
gcloud builds submit --config=cloudbuild.yaml \
  --project=enterprise-479018 \
  --region=us-central1
```

---

## Alternativa: Build más simple

Si el anterior falla, usa este (sin opciones avanzadas):

```bash
gcloud builds submit --tag gcr.io/enterprise-479018/docchat-enterprise
```

Luego despliega manualmente:

```bash
gcloud run deploy docchat-enterprise \
  --image gcr.io/enterprise-479018/docchat-enterprise \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated \
  --port 8080
```

---

## Comando Completo (Copia y pega en Cloud Shell):

```bash
cd ~
git clone https://github.com/santinogenta27/DocChatEnterprise.git
cd DocChatEnterprise
gcloud builds submit --config=cloudbuild.yaml --region=us-central1
```

¡Listo! Esto ejecutará el build directamente sin usar el trigger.

