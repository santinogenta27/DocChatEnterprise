#!/bin/bash
# Verificar por qué el nuevo build no se desplegó

echo "=== REVISIONES DE CLOUD RUN (últimas 3) ==="
gcloud run revisions list --service=docchat-enterprise --region=us-central1 --project=enterprise-479018 --limit=3 --format="table(name,status,createTime,trafficPercent,labels.commit-sha)"

echo ""
echo "=== REVISIÓN ACTIVA ACTUAL ==="
gcloud run services describe docchat-enterprise --region=us-central1 --project=enterprise-479018 --format="value(status.latestReadyRevisionName,status.latestCreatedRevisionName)"

echo ""
echo "=== ÚLTIMO BUILD Y SU DEPLOY ==="
BUILD_ID=$(gcloud builds list --project=enterprise-479018 --limit=1 --format="value(id)")
echo "Build ID: $BUILD_ID"
gcloud builds describe $BUILD_ID --project=enterprise-479018 --format="value(status,steps[*].name,steps[*].status)"

