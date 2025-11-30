#!/bin/bash
# Script para monitorear el progreso del build
# Ejecutar en Cloud Shell

BUILD_ID="e6354256-5945-49ac-8236-6bd039d6d2c1"
PROJECT_ID="enterprise-479018"

echo "🔍 Monitoreando build: ${BUILD_ID}"
echo "📊 Ver logs en tiempo real..."
echo ""

# Ver logs del build
gcloud builds log ${BUILD_ID} --project=${PROJECT_ID} --stream

