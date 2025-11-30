#!/bin/bash
# Script para construir y desplegar rápidamente en Cloud Run (2-3 minutos)
# Ejecutar en Cloud Shell: bash deploy-fast.sh

set -e  # Salir si hay error

PROJECT_ID="enterprise-479018"
SERVICE_NAME="docchat-enterprise"
REGION="us-central1"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

echo "🚀 Iniciando build rápido en Cloud Shell..."
echo "📦 Proyecto: ${PROJECT_ID}"
echo "🌍 Región: ${REGION}"
echo ""

# Configurar proyecto
gcloud config set project ${PROJECT_ID}

# Construir imagen (más rápido que Cloud Build)
echo "🔨 Construyendo imagen Docker..."
docker build -t ${IMAGE_NAME} .

# Subir imagen
echo "📤 Subiendo imagen a Container Registry..."
docker push ${IMAGE_NAME}

# Desplegar en Cloud Run
echo "🚀 Desplegando en Cloud Run..."
gcloud run deploy ${SERVICE_NAME} \
  --image ${IMAGE_NAME} \
  --region ${REGION} \
  --platform managed \
  --allow-unauthenticated \
  --port 8080 \
  --timeout 300 \
  --memory 4Gi \
  --cpu 2 \
  --max-instances 10 \
  --min-instances 0 \
  --concurrency 80 \
  --cpu-throttling=false

echo ""
echo "✅ ¡Despliegue completado!"
echo "🌐 URL: https://${SERVICE_NAME}-316171173172.${REGION}.run.app"

