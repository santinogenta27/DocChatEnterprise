#!/bin/bash
# Script para ver logs del servidor Cloud Run
# Ejecutar en Cloud Shell

SERVICE_NAME="docchat-enterprise"
REGION="us-central1"
PROJECT_ID="enterprise-479018"

echo "📊 Ver logs del servidor Cloud Run..."
echo ""

# Ver logs recientes (últimos 100)
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=${SERVICE_NAME}" \
  --project=${PROJECT_ID} \
  --limit=100 \
  --format="table(timestamp,severity,textPayload)" \
  --freshness=1h

echo ""
echo "🔍 Para ver logs en tiempo real:"
echo "gcloud logging tail \"resource.type=cloud_run_revision AND resource.labels.service_name=${SERVICE_NAME}\" --project=${PROJECT_ID}"

