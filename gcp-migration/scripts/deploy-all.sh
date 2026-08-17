#!/bin/bash
# deploy-all.sh — Deploy all Cloud Run services
set -e

PROJECT_ID="${GCP_PROJECT_ID:-ado-mobilityia}"
REGION="${GCP_REGION:-us-central1}"

echo "=== Deploying ADO MobilityIA to Cloud Run ==="
echo "Project: $PROJECT_ID | Region: $REGION"
echo ""

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BASE_DIR="$(dirname "$SCRIPT_DIR")"

# Common deploy flags
COMMON_FLAGS="--region=$REGION --platform=managed --allow-unauthenticated --min-instances=0 --max-instances=5 --memory=512Mi --timeout=120s"

# 1. Deploy API Dashboard
echo "[1/5] Deploying api-dashboard..."
gcloud run deploy api-dashboard \
    --source="$BASE_DIR/services/api-dashboard" \
    $COMMON_FLAGS \
    --set-env-vars="GCS_BUCKET=ado-telemetry-mvp-gcp,GCP_PROJECT_ID=$PROJECT_ID"

API_URL=$(gcloud run services describe api-dashboard --region=$REGION --format='value(status.url)')
echo "  → $API_URL"

# 2. Deploy Simulador
echo ""
echo "[2/5] Deploying simulador..."
gcloud run deploy simulador \
    --source="$BASE_DIR/services/simulador" \
    $COMMON_FLAGS \
    --set-env-vars="GCS_BUCKET=ado-telemetry-mvp-gcp,GCP_PROJECT_ID=$PROJECT_ID"

SIM_URL=$(gcloud run services describe simulador --region=$REGION --format='value(status.url)')
echo "  → $SIM_URL"

# 3. Deploy Agente Combustible
echo ""
echo "[3/5] Deploying agente-combustible..."
gcloud run deploy agente-combustible \
    --source="$BASE_DIR/services/agente-combustible" \
    $COMMON_FLAGS \
    --memory=1Gi \
    --set-env-vars="GCS_BUCKET=ado-telemetry-mvp-gcp,GCP_PROJECT_ID=$PROJECT_ID,GOOGLE_API_KEY=${GOOGLE_API_KEY}"

COMB_URL=$(gcloud run services describe agente-combustible --region=$REGION --format='value(status.url)')
echo "  → $COMB_URL"

# 4. Deploy Agente Mantenimiento
echo ""
echo "[4/5] Deploying agente-mantenimiento..."
gcloud run deploy agente-mantenimiento \
    --source="$BASE_DIR/services/agente-mantenimiento" \
    $COMMON_FLAGS \
    --memory=1Gi \
    --set-env-vars="GCS_BUCKET=ado-telemetry-mvp-gcp,GCP_PROJECT_ID=$PROJECT_ID,GOOGLE_API_KEY=${GOOGLE_API_KEY}"

MANT_URL=$(gcloud run services describe agente-mantenimiento --region=$REGION --format='value(status.url)')
echo "  → $MANT_URL"

# 5. Deploy Chat API (needs agent URLs)
echo ""
echo "[5/5] Deploying chat-api..."
gcloud run deploy chat-api \
    --source="$BASE_DIR/services/chat-api" \
    $COMMON_FLAGS \
    --set-env-vars="GCS_BUCKET=ado-telemetry-mvp-gcp,GCP_PROJECT_ID=$PROJECT_ID,AGENTE_COMBUSTIBLE_URL=$COMB_URL,AGENTE_MANTENIMIENTO_URL=$MANT_URL"

CHAT_URL=$(gcloud run services describe chat-api --region=$REGION --format='value(status.url)')
echo "  → $CHAT_URL"

# 6. Setup Cloud Scheduler for simulator
echo ""
echo "[+] Setting up Cloud Scheduler..."
gcloud scheduler jobs delete ado-simulador --location=$REGION --quiet 2>/dev/null || true
gcloud scheduler jobs create http ado-simulador \
    --schedule="* * * * *" \
    --uri="${SIM_URL}/simulate" \
    --http-method=POST \
    --location=$REGION \
    --oidc-service-account-email="${PROJECT_ID}@appspot.gserviceaccount.com"

echo ""
echo "=== Deploy Complete ==="
echo ""
echo "Service URLs:"
echo "  Dashboard API:       $API_URL"
echo "  Simulador:           $SIM_URL"
echo "  Agente Combustible:  $COMB_URL"
echo "  Agente Mantenimiento:$MANT_URL"
echo "  Chat API:            $CHAT_URL"
echo ""
echo "Frontend config (update frontend/src/config.ts):"
echo "  VITE_API_BASE_URL=$API_URL"
echo "  VITE_CHAT_URL=$CHAT_URL"
