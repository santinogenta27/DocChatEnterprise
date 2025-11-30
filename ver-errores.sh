#!/bin/bash
# Script para ver errores recientes del servidor
# Ejecutar en Cloud Shell

echo "🔍 Buscando errores recientes..."
echo ""

# Ver errores recientes
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=docchat-enterprise AND severity>=ERROR" \
  --project=enterprise-479018 \
  --limit=20 \
  --freshness=10m \
  --format="value(timestamp,severity,textPayload)"

echo ""
echo "📊 Para ver más detalles, ejecuta:"
echo "gcloud logging read \"resource.type=cloud_run_revision AND resource.labels.service_name=docchat-enterprise\" --project=enterprise-479018 --limit=100 --freshness=10m --format=json"

