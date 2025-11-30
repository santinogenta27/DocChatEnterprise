#!/bin/bash
# Script para construir y desplegar desde GitHub directamente
# Ejecutar en Cloud Shell

set -e

PROJECT_ID="enterprise-479018"
SERVICE_NAME="docchat-enterprise"
REGION="us-central1"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"
REPO_URL="https://github.com/santinogenta27/DocChatEnterprise.git"
BRANCH="main"

echo "🚀 Construyendo y desplegando desde GitHub..."
echo "📦 Proyecto: ${PROJECT_ID}"
echo "🌍 Región: ${REGION}"
echo ""

# Configurar proyecto
gcloud config set project ${PROJECT_ID}

# Construir y desplegar directamente desde GitHub usando Cloud Build
echo "🔨 Construyendo imagen desde GitHub con Cloud Build..."
gcloud builds submit --config=cloudbuild.yaml \
  --substitutions=_GITHUB_REPO=${REPO_URL},_BRANCH=${BRANCH} \
  ${REPO_URL}

# O mejor: construir desde el código actual si ya lo tienes
# Si no, usar el trigger manualmente

echo ""
echo "✅ ¡Despliegue completado!"

