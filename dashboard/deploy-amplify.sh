#!/bin/bash
# Deploy manual a AWS Amplify Hosting
# Uso: ./deploy-amplify.sh

set -e

APP_ID="d3p5yfvjmj2mj6"
BRANCH="main"
REGION="us-east-2"
ZIP_PATH="/tmp/ado-dashboard-deploy.zip"

echo "🔨 Building dashboard..."
npm run build

echo "📦 Creating deployment zip..."
(cd dist && zip -r "$ZIP_PATH" .)

echo "🚀 Creating Amplify deployment..."
DEPLOY_OUTPUT=$(aws amplify create-deployment \
  --app-id "$APP_ID" \
  --branch-name "$BRANCH" \
  --region "$REGION" \
  --output json)

JOB_ID=$(echo "$DEPLOY_OUTPUT" | python3 -c "import sys,json; print(json.load(sys.stdin)['jobId'])")
UPLOAD_URL=$(echo "$DEPLOY_OUTPUT" | python3 -c "import sys,json; print(json.load(sys.stdin)['zipUploadUrl'])")

echo "📤 Uploading artifacts (job $JOB_ID)..."
curl -s -T "$ZIP_PATH" "$UPLOAD_URL"

echo "▶️  Starting deployment..."
aws amplify start-deployment \
  --app-id "$APP_ID" \
  --branch-name "$BRANCH" \
  --job-id "$JOB_ID" \
  --region "$REGION" \
  --output json > /dev/null

echo "⏳ Waiting for deployment..."
while true; do
  STATUS=$(aws amplify get-job \
    --app-id "$APP_ID" \
    --branch-name "$BRANCH" \
    --job-id "$JOB_ID" \
    --region "$REGION" \
    --query 'job.summary.status' \
    --output text)
  
  if [ "$STATUS" = "SUCCEED" ]; then
    echo "✅ Deploy exitoso → https://main.${APP_ID}.amplifyapp.com"
    break
  elif [ "$STATUS" = "FAILED" ] || [ "$STATUS" = "CANCELLED" ]; then
    echo "❌ Deploy falló con status: $STATUS"
    exit 1
  else
    echo "   Status: $STATUS..."
    sleep 5
  fi
done

# Cleanup
rm -f "$ZIP_PATH"
