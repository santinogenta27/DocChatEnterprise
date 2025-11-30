#!/bin/bash
# Script para crear cloudbuild.yaml directamente en Cloud Shell

cat > ~/DocChatEnterprise/cloudbuild.yaml << 'EOF'
steps:
  # Build the container image
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', 'gcr.io/$PROJECT_ID/docchat-enterprise', '.']
  
  # Push the container image to Container Registry
  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', 'gcr.io/$PROJECT_ID/docchat-enterprise']
  
  # Deploy container image to Cloud Run
  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
    entrypoint: gcloud
    args:
      - 'run'
      - 'deploy'
      - 'docchat-enterprise'
      - '--image'
      - 'gcr.io/$PROJECT_ID/docchat-enterprise'
      - '--region'
      - 'us-central1'
      - '--platform'
      - 'managed'
      - '--allow-unauthenticated'
      - '--port'
      - '8080'
      - '--timeout'
      - '240'
      - '--memory'
      - '2Gi'
      - '--cpu'
      - '2'

images:
  - 'gcr.io/$PROJECT_ID/docchat-enterprise'

options:
  machineType: 'E2_HIGHCPU_8'
  logging: CLOUD_LOGGING_ONLY
  defaultLogsBucketBehavior: 'REGIONAL_USER_OWNED_BUCKET'

timeout: '1200s'
EOF

echo "✅ cloudbuild.yaml creado exitosamente"

