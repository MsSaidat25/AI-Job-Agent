#!/usr/bin/env bash
# Deploy AI Job Agent to Google Cloud Run.
#
# Prerequisites:
#   1. gcloud CLI installed and authenticated
#   2. GCP project with required APIs enabled
#   3. Secrets stored in Secret Manager
#   4. Cloud SQL instance with jobagent_db created
#
# Security model:
#   - Private service: authenticated invokers only (Cloud Run IAM)
#   - AUTH_ENABLED=true for app-level bearer-token flows
#   - If you later switch to public access, add API key validation in-app
#     and configure Cloud Armor / stricter rate limiting.
#
# Usage:
#   ./deploy-cloudrun.sh [PROJECT_ID] [REGION]

set -euo pipefail

PROJECT_ID="${1:?Usage: ./deploy-cloudrun.sh PROJECT_ID [REGION]}"
REGION="${2:-northamerica-northeast2}"
SERVICE_NAME="ai-job-agent"
CLOUD_SQL_INSTANCE="${PROJECT_ID}:${REGION}:jobpath-db"
IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/ai-job-agent/${SERVICE_NAME}:latest"

echo "==> Deploying to project: ${PROJECT_ID}, region: ${REGION}"

# Build and push Docker image via Cloud Build
echo "==> Building Docker image..."
gcloud builds submit \
  --tag "${IMAGE}" \
  --project "${PROJECT_ID}" \
  --region "${REGION}"

# Deploy to Cloud Run with Secret Manager references and Cloud SQL
echo "==> Deploying to Cloud Run..."
gcloud run deploy "${SERVICE_NAME}" \
  --image "${IMAGE}" \
  --project "${PROJECT_ID}" \
  --region "${REGION}" \
  --platform managed \
  --no-allow-unauthenticated \
  --add-cloudsql-instances "${CLOUD_SQL_INSTANCE}" \
  --set-env-vars "GCP_PROJECT_ID=${PROJECT_ID}" \
  --set-env-vars "VERTEX_PROJECT=${PROJECT_ID}" \
  --set-env-vars "VERTEX_LOCATION=${REGION}" \
  --set-env-vars "USE_VERTEX_FAILOVER=true" \
  --set-env-vars "AUTH_ENABLED=true" \
  --set-secrets "OPENROUTER_API_KEY=OPENROUTER_API_KEY:latest" \
  --set-secrets "ANTHROPIC_API_KEY=ANTHROPIC_API_KEY:latest" \
  --set-secrets "ADZUNA_APP_ID=ADZUNA_APP_ID:latest" \
  --set-secrets "ADZUNA_APP_KEY=ADZUNA_APP_KEY:latest" \
  --set-secrets "DATABASE_URL=DATABASE_URL:latest" \
  --set-secrets "RESEND_API_KEY=RESEND_API_KEY:latest" \
  --set-env-vars "AGENT_MODEL=claude-sonnet-4-6" \
  --set-env-vars "ADZUNA_COUNTRY=us" \
  --min-instances 0 \
  --max-instances 10 \
  --memory 512Mi \
  --cpu 1 \
  --timeout 300

echo ""
echo "==> Deployment complete!"
gcloud run services describe "${SERVICE_NAME}" \
  --project "${PROJECT_ID}" \
  --region "${REGION}" \
  --format "value(status.url)"
