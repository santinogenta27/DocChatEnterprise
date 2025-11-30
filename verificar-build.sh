#!/bin/bash
# Script para verificar el estado del build y la app
# Ejecutar en Cloud Shell

BUILD_ID="e6354256-5945-49ac-8236-6bd039d6d2c1"
PROJECT_ID="enterprise-479018"
SERVICE_URL="https://docchat-enterprise-316171173172.us-central1.run.app"

echo "🔍 Verificando estado del build..."
echo ""

# Ver estado del build
gcloud builds describe ${BUILD_ID} --project=${PROJECT_ID} --format="value(status)"

echo ""
echo "📊 Para ver logs en tiempo real (Cloud Logging):"
echo "gcloud beta builds log ${BUILD_ID} --stream"
echo ""
echo "🌐 URL de la app: ${SERVICE_URL}"
echo ""
echo "✅ Cuando el build termine, prueba la URL con:"
echo "curl ${SERVICE_URL}"

