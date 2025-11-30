#!/bin/bash
# Script para ejecutar build directamente sin trigger

# Ejecutar build directamente desde Cloud Shell
gcloud builds submit --config=cloudbuild.yaml \
  --substitutions=_SERVICE_NAME=docchat-enterprise \
  --region=us-central1

