#!/bin/bash
# Script para ejecutar el build de Cloud Run
# Ejecutar en Cloud Shell

echo "🚀 Ejecutando build de Cloud Run..."
echo ""

# Ejecutar trigger
gcloud builds triggers run rmgpgab-docchat-enterprise-us-central1-santinogenta27-DocChaidj \
  --branch=main \
  --project=enterprise-479018

echo ""
echo "✅ Build iniciado!"
echo "📊 Monitorear en: https://console.cloud.google.com/cloud-build/builds?project=enterprise-479018"

