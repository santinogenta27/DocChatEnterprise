#!/bin/bash
# Script para verificar el estado actual del build y la aplicación

echo "=== 1. ESTADO DEL BUILD MÁS RECIENTE ==="
gcloud builds list --project=enterprise-479018 --limit=1 --format="table(id,status,createTime,finishTime,source.repoSource.commitSha)"

echo ""
echo "=== 2. REVISIÓN ACTUAL EN CLOUD RUN ==="
gcloud run revisions list --service=docchat-enterprise --region=us-central1 --project=enterprise-479018 --limit=1 --format="table(name,status,createTime,trafficPercent)"

echo ""
echo "=== 3. ÚLTIMOS ERRORES EN CLOUD RUN (últimos 5 minutos) ==="
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=docchat-enterprise AND severity>=ERROR" \
  --project=enterprise-479018 \
  --limit=10 \
  --freshness=5m \
  --format="value(timestamp,severity,textPayload)" | head -20

echo ""
echo "=== 4. COMMIT SHA ACTUAL EN PRODUCCIÓN ==="
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=docchat-enterprise" \
  --project=enterprise-479018 \
  --limit=1 \
  --freshness=5m \
  --format="value(labels.commit-sha)"

