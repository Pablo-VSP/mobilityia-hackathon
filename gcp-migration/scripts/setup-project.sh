#!/bin/bash
# setup-project.sh — Configura el proyecto GCP para ADO MobilityIA
set -e

PROJECT_ID="${GCP_PROJECT_ID:-ado-mobilityia}"
REGION="${GCP_REGION:-us-central1}"
BUCKET="${GCS_BUCKET:-ado-telemetry-mvp-gcp}"

echo "=== ADO MobilityIA — GCP Setup ==="
echo "Project: $PROJECT_ID"
echo "Region: $REGION"
echo ""

# 1. Set project
gcloud config set project "$PROJECT_ID"

# 2. Enable required APIs
echo "Enabling APIs..."
gcloud services enable \
    run.googleapis.com \
    firestore.googleapis.com \
    storage.googleapis.com \
    aiplatform.googleapis.com \
    cloudscheduler.googleapis.com \
    cloudbuild.googleapis.com \
    generativelanguage.googleapis.com

# 3. Create Firestore database (Native mode)
echo "Creating Firestore database..."
gcloud firestore databases create \
    --location="$REGION" \
    --type=firestore-native \
    2>/dev/null || echo "Firestore already exists"

# 4. Create Cloud Storage bucket
echo "Creating GCS bucket..."
gsutil mb -l "$REGION" "gs://$BUCKET" 2>/dev/null || echo "Bucket already exists"

# 5. Upload data from AWS bucket (assumes data is already downloaded locally)
echo ""
echo "=== Next Steps ==="
echo "1. Upload data to GCS:"
echo "   gsutil -m rsync -r ./data gs://$BUCKET/hackathon-data/"
echo ""
echo "2. Deploy services:"
echo "   ./scripts/deploy-all.sh"
echo ""
echo "3. Setup Cloud Scheduler for simulator:"
echo "   gcloud scheduler jobs create http ado-simulador \\"
echo "     --schedule='* * * * *' \\"
echo "     --uri='https://simulador-XXXXX-uc.a.run.app/simulate' \\"
echo "     --http-method=POST \\"
echo "     --location=$REGION"
echo ""
echo "4. Deploy frontend:"
echo "   cd frontend && npm run build && firebase deploy"
echo ""
echo "Setup complete!"
