#!/bin/bash
# Manual one-shot deploy to Cloud Run (no Cloud Build required).
# Usage:
#   ./deploy.sh
# Prerequisites:
#   gcloud auth login
#   gcloud config set project <PROJECT_ID>
#   Artifact Registry repo must exist:
#     gcloud artifacts repositories create mcp-servers \
#       --repository-format=docker --location=asia-southeast1

set -euo pipefail

REGION="asia-southeast1"
PROJECT=$(gcloud config get-value project)
AR_REPO="mcp-servers"
SERVICE="tiktok-ads-mcp"
IMAGE="${REGION}-docker.pkg.dev/${PROJECT}/${AR_REPO}/${SERVICE}:latest"

echo "==> Building image: ${IMAGE}"
docker build --platform linux/amd64 -t "${IMAGE}" .

echo "==> Configuring Docker for Artifact Registry"
gcloud auth configure-docker "${REGION}-docker.pkg.dev" --quiet

echo "==> Pushing image"
docker push "${IMAGE}"

echo "==> Deploying to Cloud Run"
gcloud run deploy "${SERVICE}" \
  --image="${IMAGE}" \
  --region="${REGION}" \
  --platform=managed \
  --allow-unauthenticated \
  --port=8080 \
  --memory=512Mi \
  --cpu=1 \
  --min-instances=0 \
  --max-instances=3 \
  --timeout=300 \
  --set-env-vars="TIKTOK_APP_ID=${TIKTOK_APP_ID},TIKTOK_SECRET=${TIKTOK_SECRET},TIKTOK_ACCESS_TOKEN=${TIKTOK_ACCESS_TOKEN}"

echo ""
echo "==> Deployed. Endpoint:"
gcloud run services describe "${SERVICE}" \
  --region="${REGION}" \
  --format="value(status.url)"
