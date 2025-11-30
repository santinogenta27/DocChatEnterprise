# 🚀 Ejecutar Build Directo (SIN TRIGGER)

## Solución Simple:

### 1. En Cloud Shell, ejecuta:

```bash
cd ~
rm -rf DocChatEnterprise
git clone https://github.com/santinogenta27/DocChatEnterprise.git
cd DocChatEnterprise
```

### 2. Si pide autenticación, usa este método alternativo:

```bash
cd ~
rm -rf DocChatEnterprise
# Descargar como ZIP (sin autenticación)
curl -L https://github.com/santinogenta27/DocChatEnterprise/archive/refs/heads/main.zip -o repo.zip
unzip -q repo.zip
mv DocChatEnterprise-main DocChatEnterprise
cd DocChatEnterprise
```

### 3. Verificar que tienes los archivos:

```bash
ls -la Dockerfile cloudbuild.yaml app.py
```

### 4. Ejecutar build DIRECTAMENTE (sin trigger):

```bash
gcloud builds submit --config=cloudbuild.yaml --region=us-central1 --no-source
```

O mejor aún, sube el código directamente:

```bash
gcloud builds submit --config=cloudbuild.yaml --region=us-central1 .
```

### 5. Si el anterior falla, usa este comando más simple:

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
  --port 8080 \
  --timeout 240 \
  --memory 2Gi \
  --cpu 2
```

---

## Comando TODO EN UNO (copia y pega):

```bash
cd ~ && rm -rf DocChatEnterprise repo.zip && curl -L https://github.com/santinogenta27/DocChatEnterprise/archive/refs/heads/main.zip -o repo.zip && unzip -q repo.zip && mv DocChatEnterprise-main DocChatEnterprise && cd DocChatEnterprise && gcloud builds submit --tag gcr.io/enterprise-479018/docchat-enterprise && gcloud run deploy docchat-enterprise --image gcr.io/enterprise-479018/docchat-enterprise --region us-central1 --platform managed --allow-unauthenticated --port 8080 --timeout 240 --memory 2Gi --cpu 2
```

Este comando:
1. Descarga el código
2. Construye la imagen
3. La despliega en Cloud Run

**TODO SIN USAR EL TRIGGER**

