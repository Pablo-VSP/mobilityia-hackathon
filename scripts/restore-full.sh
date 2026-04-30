#!/usr/bin/env bash
# =============================================================================
# 🔄 ADO MobilityIA — Script de Restauración Completa
# =============================================================================
# Levanta TODA la infraestructura desde cero en una cuenta AWS nueva.
#
# PRERREQUISITOS:
#   1. AWS CLI configurado con credenciales de la nueva cuenta
#   2. Región: us-east-2
#   3. Node.js 18+ y npm
#   4. Python 3.12+ y pip/uv
#   5. AgentCore CLI: npm install -g @aws/agentcore-cli
#   6. Los datos de backup en ./backup/ (Parquets, viajes, modelo ML)
#      - Si no tienes backup de Parquets, el simulador no funcionará
#        hasta que regeneres viajes_consolidados.json
#
# USO:
#   chmod +x scripts/restore-full.sh
#   ./scripts/restore-full.sh
#
# El script es IDEMPOTENTE — si falla a mitad, puedes re-ejecutarlo.
# Los recursos que ya existen se saltan con un warning.
#
# Al terminar, genera scripts/restore-output.env con todos los IDs nuevos.
# =============================================================================

set -euo pipefail

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

REGION="us-east-2"
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUTPUT_FILE="${PROJECT_ROOT}/scripts/restore-output.env"
TEMP_DIR="/tmp/ado-restore-$$"

mkdir -p "$TEMP_DIR"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
log_step() { echo -e "\n${BLUE}━━━ PASO $1: $2 ━━━${NC}"; }
log_ok()   { echo -e "  ${GREEN}✅ $1${NC}"; }
log_warn() { echo -e "  ${YELLOW}⚠️  $1${NC}"; }
log_err()  { echo -e "  ${RED}❌ $1${NC}"; }
log_info() { echo -e "  ${BLUE}ℹ️  $1${NC}"; }

save_var() {
  local key=$1 val=$2
  # Actualizar o agregar en el archivo de output
  if grep -q "^${key}=" "$OUTPUT_FILE" 2>/dev/null; then
    sed -i.bak "s|^${key}=.*|${key}=${val}|" "$OUTPUT_FILE"
    rm -f "${OUTPUT_FILE}.bak"
  else
    echo "${key}=${val}" >> "$OUTPUT_FILE"
  fi
  export "$key"="$val"
  log_info "Guardado: ${key}=${val}"
}

# Inicializar archivo de output
echo "# ADO MobilityIA — IDs de restauración ($(date))" > "$OUTPUT_FILE"
echo "REGION=${REGION}" >> "$OUTPUT_FILE"

# Obtener Account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text --region $REGION)
save_var "ACCOUNT_ID" "$ACCOUNT_ID"
echo ""
echo -e "${GREEN}Cuenta AWS: ${ACCOUNT_ID} | Región: ${REGION}${NC}"
echo -e "${GREEN}Proyecto: ${PROJECT_ROOT}${NC}"
echo ""

# =============================================================================
# PASO 1 — Crear buckets S3
# =============================================================================
log_step "1/13" "Crear buckets S3"

create_bucket() {
  local BUCKET=$1
  if aws s3api head-bucket --bucket "$BUCKET" --region $REGION 2>/dev/null; then
    log_warn "Bucket $BUCKET ya existe — saltando"
  else
    aws s3 mb "s3://${BUCKET}" --region $REGION
    log_ok "Bucket $BUCKET creado"
  fi
}

create_bucket "ado-telemetry-mvp"
create_bucket "mobilityia-hackathon-bl-2026"
create_bucket "ado-mobilityia-dashboard"

# =============================================================================
# PASO 2 — Subir datos a S3
# =============================================================================
log_step "2/13" "Subir datos a S3"

# Catálogos (siempre disponibles en el repo)
aws s3 cp "${PROJECT_ROOT}/datos_spn/data.JSON" \
  "s3://ado-telemetry-mvp/hackathon-data/catalogo/motor_spn.json" --region $REGION
log_ok "Catálogo SPN subido"

aws s3 cp "${PROJECT_ROOT}/datos_spn/fault_data_catalog.JSON" \
  "s3://ado-telemetry-mvp/hackathon-data/fallas-simuladas/data_fault.json" --region $REGION
log_ok "Catálogo de fallas subido"

# Knowledge Base docs
for doc in manual-reglas-mantenimiento-motor.md manual-reglas-ambientales-emisiones.md manual-reglas-fallas-mantenimiento.md viaje-ideal-referencia.md; do
  if [ -f "${PROJECT_ROOT}/manuales/${doc}" ]; then
    aws s3 cp "${PROJECT_ROOT}/manuales/${doc}" \
      "s3://ado-telemetry-mvp/hackathon-data/knowledge-base/docs/${doc}" --region $REGION
    log_ok "KB doc: ${doc}"
  fi
done

# Catálogos adicionales para KB
aws s3 cp "${PROJECT_ROOT}/datos_spn/data.JSON" \
  "s3://ado-telemetry-mvp/hackathon-data/knowledge-base/docs/motor_spn.json" --region $REGION
aws s3 cp "${PROJECT_ROOT}/datos_spn/fault_data_catalog.JSON" \
  "s3://ado-telemetry-mvp/hackathon-data/knowledge-base/docs/codigos-falla-catalogo.csv" --region $REGION
log_ok "Catálogos copiados a KB"

# Datos de backup (Parquets, viajes, modelo ML)
BACKUP_DIR="${PROJECT_ROOT}/backup"
if [ -d "$BACKUP_DIR" ]; then
  # Viajes consolidados para el simulador
  if [ -f "${BACKUP_DIR}/viajes_consolidados.json" ]; then
    aws s3 cp "${BACKUP_DIR}/viajes_consolidados.json" \
      "s3://ado-telemetry-mvp/hackathon-data/simulacion/viajes_consolidados.json" --region $REGION
    log_ok "viajes_consolidados.json subido"
  else
    log_warn "No se encontró backup/viajes_consolidados.json — el simulador NO funcionará"
  fi

  # Parquets raw
  if [ -d "${BACKUP_DIR}/raw/travel_telemetry" ]; then
    aws s3 sync "${BACKUP_DIR}/raw/travel_telemetry/" \
      "s3://ado-telemetry-mvp/hackathon-data/raw/travel_telemetry/" --region $REGION
    log_ok "Parquets de telemetría subidos"
  else
    log_warn "No se encontraron Parquets de telemetría en backup/raw/travel_telemetry/"
  fi

  if [ -d "${BACKUP_DIR}/raw/data_fault" ]; then
    aws s3 sync "${BACKUP_DIR}/raw/data_fault/" \
      "s3://ado-telemetry-mvp/hackathon-data/raw/data_fault/" --region $REGION
    log_ok "Parquets de fallas subidos"
  fi

  if [ -d "${BACKUP_DIR}/raw/motor_spn" ]; then
    aws s3 sync "${BACKUP_DIR}/raw/motor_spn/" \
      "s3://ado-telemetry-mvp/hackathon-data/raw/motor_spn/" --region $REGION
    log_ok "Parquet de catálogo SPN subido"
  fi

  # Modelo ML pre-entrenado
  if [ -f "${BACKUP_DIR}/model.tar.gz" ]; then
    aws s3 cp "${BACKUP_DIR}/model.tar.gz" \
      "s3://ado-telemetry-mvp/hackathon-data/modelos/sagemaker/output/model.tar.gz" --region $REGION
    log_ok "Modelo ML subido"
  fi
  if [ -f "${BACKUP_DIR}/feature_names.json" ]; then
    aws s3 cp "${BACKUP_DIR}/feature_names.json" \
      "s3://ado-telemetry-mvp/hackathon-data/modelos/sagemaker-v2/training-data/feature_names.json" --region $REGION
    log_ok "feature_names.json subido"
  fi
else
  log_warn "No se encontró directorio backup/ — solo se suben catálogos y manuales del repo"
  log_warn "El simulador y SageMaker necesitan datos de backup para funcionar"
fi

# =============================================================================
# PASO 3 — Crear tablas DynamoDB
# =============================================================================
log_step "3/13" "Crear tablas DynamoDB"

# Tabla de telemetría
if aws dynamodb describe-table --table-name ado-telemetria-live --region $REGION 2>/dev/null | grep -q "ACTIVE"; then
  log_warn "Tabla ado-telemetria-live ya existe"
else
  aws dynamodb create-table \
    --table-name ado-telemetria-live \
    --attribute-definitions \
      AttributeName=autobus,AttributeType=S \
      AttributeName=timestamp,AttributeType=S \
      AttributeName=viaje_ruta,AttributeType=S \
    --key-schema \
      AttributeName=autobus,KeyType=HASH \
      AttributeName=timestamp,KeyType=RANGE \
    --global-secondary-indexes '[{
      "IndexName": "viaje_ruta-timestamp-index",
      "KeySchema": [
        {"AttributeName": "viaje_ruta", "KeyType": "HASH"},
        {"AttributeName": "timestamp", "KeyType": "RANGE"}
      ],
      "Projection": {"ProjectionType": "ALL"}
    }]' \
    --billing-mode PAY_PER_REQUEST \
    --region $REGION

  aws dynamodb wait table-exists --table-name ado-telemetria-live --region $REGION

  aws dynamodb update-time-to-live \
    --table-name ado-telemetria-live \
    --time-to-live-specification "Enabled=true,AttributeName=ttl_expiry" \
    --region $REGION

  log_ok "Tabla ado-telemetria-live creada con GSI y TTL"
fi

# Tabla de alertas
if aws dynamodb describe-table --table-name ado-alertas --region $REGION 2>/dev/null | grep -q "ACTIVE"; then
  log_warn "Tabla ado-alertas ya existe"
else
  aws dynamodb create-table \
    --table-name ado-alertas \
    --attribute-definitions \
      AttributeName=alerta_id,AttributeType=S \
      AttributeName=timestamp,AttributeType=S \
    --key-schema \
      AttributeName=alerta_id,KeyType=HASH \
      AttributeName=timestamp,KeyType=RANGE \
    --billing-mode PAY_PER_REQUEST \
    --region $REGION

  aws dynamodb wait table-exists --table-name ado-alertas --region $REGION
  log_ok "Tabla ado-alertas creada"
fi

# =============================================================================
# PASO 4 — Crear IAM Role
# =============================================================================
log_step "4/13" "Crear IAM Role para Lambdas"

ROLE_NAME="ado-lambda-execution-role"

if aws iam get-role --role-name $ROLE_NAME 2>/dev/null; then
  log_warn "Rol $ROLE_NAME ya existe"
  ROLE_ARN=$(aws iam get-role --role-name $ROLE_NAME --query 'Role.Arn' --output text)
else
  # Trust policy
  cat > "${TEMP_DIR}/trust-policy.json" << 'TRUST_EOF'
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "lambda.amazonaws.com"},
    "Action": "sts:AssumeRole"
  }]
}
TRUST_EOF

  ROLE_ARN=$(aws iam create-role \
    --role-name $ROLE_NAME \
    --assume-role-policy-document "file://${TEMP_DIR}/trust-policy.json" \
    --query 'Role.Arn' --output text)

  aws iam attach-role-policy \
    --role-name $ROLE_NAME \
    --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

  # Custom policy
  cat > "${TEMP_DIR}/custom-policy.json" << POLICY_EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "DynamoDB",
      "Effect": "Allow",
      "Action": ["dynamodb:PutItem","dynamodb:GetItem","dynamodb:Query","dynamodb:Scan","dynamodb:UpdateItem","dynamodb:DeleteItem","dynamodb:BatchWriteItem"],
      "Resource": [
        "arn:aws:dynamodb:${REGION}:${ACCOUNT_ID}:table/ado-telemetria-live",
        "arn:aws:dynamodb:${REGION}:${ACCOUNT_ID}:table/ado-telemetria-live/index/*",
        "arn:aws:dynamodb:${REGION}:${ACCOUNT_ID}:table/ado-alertas",
        "arn:aws:dynamodb:${REGION}:${ACCOUNT_ID}:table/ado-alertas/index/*"
      ]
    },
    {
      "Sid": "S3",
      "Effect": "Allow",
      "Action": ["s3:GetObject","s3:PutObject","s3:ListBucket"],
      "Resource": ["arn:aws:s3:::ado-telemetry-mvp","arn:aws:s3:::ado-telemetry-mvp/*"]
    },
    {
      "Sid": "SageMaker",
      "Effect": "Allow",
      "Action": ["sagemaker:InvokeEndpoint"],
      "Resource": "arn:aws:sagemaker:${REGION}:${ACCOUNT_ID}:endpoint/ado-prediccion-eventos"
    },
    {
      "Sid": "AgentCore",
      "Effect": "Allow",
      "Action": ["bedrock-agentcore:InvokeAgentRuntime"],
      "Resource": "arn:aws:bedrock-agentcore:${REGION}:${ACCOUNT_ID}:runtime/*"
    },
    {
      "Sid": "BedrockKB",
      "Effect": "Allow",
      "Action": ["bedrock:Retrieve","bedrock:RetrieveAndGenerate"],
      "Resource": "*"
    },
    {
      "Sid": "LambdaInvoke",
      "Effect": "Allow",
      "Action": ["lambda:InvokeFunction"],
      "Resource": "arn:aws:lambda:${REGION}:${ACCOUNT_ID}:function:tool-*"
    }
  ]
}
POLICY_EOF

  aws iam put-role-policy \
    --role-name $ROLE_NAME \
    --policy-name ado-lambda-custom-policy \
    --policy-document "file://${TEMP_DIR}/custom-policy.json"

  log_ok "Rol creado: $ROLE_ARN"
  log_info "Esperando 10s para propagación de IAM..."
  sleep 10
fi

save_var "ROLE_ARN" "$ROLE_ARN"

# =============================================================================
# PASO 5 — Publicar Lambda Layer
# =============================================================================
log_step "5/13" "Publicar Lambda Layer ado-common-layer"

cd "${PROJECT_ROOT}/lambda-functions/layers/ado-common"
zip -r "${TEMP_DIR}/ado-common-layer.zip" python/ -x "*__pycache__*"
cd "$PROJECT_ROOT"

LAYER_ARN=$(aws lambda publish-layer-version \
  --layer-name ado-common-layer \
  --description "Shared: SPN catalog, DynamoDB helpers, response format" \
  --zip-file "fileb://${TEMP_DIR}/ado-common-layer.zip" \
  --compatible-runtimes python3.12 \
  --region $REGION \
  --query 'LayerVersionArn' --output text)

save_var "LAYER_ARN" "$LAYER_ARN"
log_ok "Layer publicado: $LAYER_ARN"

# =============================================================================
# PASO 6 — Desplegar funciones Lambda
# =============================================================================
log_step "6/13" "Desplegar 11 funciones Lambda"

deploy_lambda() {
  local FUNC_NAME=$1
  local FUNC_DIR=$2
  local TIMEOUT=${3:-30}
  local MEMORY=${4:-256}
  local EXTRA_ENV=${5:-""}

  # Verificar si ya existe
  if aws lambda get-function --function-name "$FUNC_NAME" --region $REGION 2>/dev/null; then
    log_warn "$FUNC_NAME ya existe — actualizando código"
    cd "${PROJECT_ROOT}/lambda-functions/${FUNC_DIR}"
    zip -r "${TEMP_DIR}/${FUNC_NAME}.zip" lambda_function.py -x "*__pycache__*" "*.pyc"
    cd "$PROJECT_ROOT"
    aws lambda update-function-code \
      --function-name "$FUNC_NAME" \
      --zip-file "fileb://${TEMP_DIR}/${FUNC_NAME}.zip" \
      --region $REGION > /dev/null
    return
  fi

  cd "${PROJECT_ROOT}/lambda-functions/${FUNC_DIR}"
  zip -r "${TEMP_DIR}/${FUNC_NAME}.zip" lambda_function.py -x "*__pycache__*" "*.pyc"
  cd "$PROJECT_ROOT"

  local ENV_VARS="Variables={DYNAMODB_TABLE_TELEMETRIA=ado-telemetria-live,DYNAMODB_TABLE_ALERTAS=ado-alertas,S3_BUCKET=ado-telemetry-mvp,ENVIRONMENT=mvp${EXTRA_ENV}}"

  aws lambda create-function \
    --function-name "$FUNC_NAME" \
    --runtime python3.12 \
    --handler lambda_function.lambda_handler \
    --role "$ROLE_ARN" \
    --zip-file "fileb://${TEMP_DIR}/${FUNC_NAME}.zip" \
    --timeout "$TIMEOUT" \
    --memory-size "$MEMORY" \
    --layers "$LAYER_ARN" \
    --environment "$ENV_VARS" \
    --region $REGION > /dev/null

  log_ok "$FUNC_NAME desplegada (${MEMORY}MB, ${TIMEOUT}s)"
}

# Simulador
deploy_lambda "ado-simulador-telemetria" "ado-simulador-telemetria" 30 512

# Tools Agente Combustible
deploy_lambda "tool-consultar-telemetria" "tool-consultar-telemetria" 15 256
deploy_lambda "tool-calcular-desviacion" "tool-calcular-desviacion" 15 256
deploy_lambda "tool-listar-buses-activos" "tool-listar-buses-activos" 15 256

# Tools Agente Mantenimiento
deploy_lambda "tool-consultar-obd" "tool-consultar-obd" 15 256
deploy_lambda "tool-predecir-evento" "tool-predecir-evento" 30 512 ",SAGEMAKER_ENDPOINT=ado-prediccion-eventos"
deploy_lambda "tool-buscar-patrones-historicos" "tool-buscar-patrones-historicos" 15 256
deploy_lambda "tool-generar-recomendacion" "tool-generar-recomendacion" 15 256

# Tool alertas
deploy_lambda "tool-consultar-alertas" "tool-consultar-alertas" 15 256

# Dashboard API
deploy_lambda "ado-dashboard-api" "ado-dashboard-api" 15 256

# Chat API (sin layer, con env vars especiales — ARNs se actualizan después)
if aws lambda get-function --function-name "ado-chat-api" --region $REGION 2>/dev/null; then
  log_warn "ado-chat-api ya existe — actualizando código"
  cd "${PROJECT_ROOT}/lambda-functions/ado-chat-api"
  zip -r "${TEMP_DIR}/ado-chat-api.zip" lambda_function.py -x "*__pycache__*"
  cd "$PROJECT_ROOT"
  aws lambda update-function-code \
    --function-name "ado-chat-api" \
    --zip-file "fileb://${TEMP_DIR}/ado-chat-api.zip" \
    --region $REGION > /dev/null
else
  cd "${PROJECT_ROOT}/lambda-functions/ado-chat-api"
  zip -r "${TEMP_DIR}/ado-chat-api.zip" lambda_function.py -x "*__pycache__*"
  cd "$PROJECT_ROOT"
  aws lambda create-function \
    --function-name "ado-chat-api" \
    --runtime python3.12 \
    --handler lambda_function.lambda_handler \
    --role "$ROLE_ARN" \
    --zip-file "fileb://${TEMP_DIR}/ado-chat-api.zip" \
    --timeout 120 \
    --memory-size 512 \
    --environment "Variables={RUNTIME_ARN_COMBUSTIBLE=PLACEHOLDER,RUNTIME_ARN_MANTENIMIENTO=PLACEHOLDER,AWS_REGION_OVERRIDE=${REGION}}" \
    --region $REGION > /dev/null
  log_ok "ado-chat-api desplegada (ARNs de AgentCore pendientes)"
fi

log_ok "11 Lambdas desplegadas"

# =============================================================================
# PASO 7 — Crear Cognito User Pool
# =============================================================================
log_step "7/13" "Crear Cognito User Pool"

# Verificar si ya existe
EXISTING_POOL=$(aws cognito-idp list-user-pools --max-results 20 --region $REGION \
  --query "UserPools[?Name=='ado-mobilityia-users'].Id" --output text 2>/dev/null || echo "")

if [ -n "$EXISTING_POOL" ] && [ "$EXISTING_POOL" != "None" ]; then
  USER_POOL_ID="$EXISTING_POOL"
  log_warn "User Pool ya existe: $USER_POOL_ID"
else
  USER_POOL_ID=$(aws cognito-idp create-user-pool \
    --pool-name ado-mobilityia-users \
    --auto-verified-attributes email \
    --username-attributes email \
    --policies '{"PasswordPolicy":{"MinimumLength":8,"RequireUppercase":true,"RequireLowercase":true,"RequireNumbers":true,"RequireSymbols":true}}' \
    --region $REGION \
    --query 'UserPool.Id' --output text)
  log_ok "User Pool creado: $USER_POOL_ID"
fi
save_var "USER_POOL_ID" "$USER_POOL_ID"

# App Client
EXISTING_CLIENT=$(aws cognito-idp list-user-pool-clients --user-pool-id "$USER_POOL_ID" --region $REGION \
  --query "UserPoolClients[?ClientName=='ado-dashboard-client'].ClientId" --output text 2>/dev/null || echo "")

if [ -n "$EXISTING_CLIENT" ] && [ "$EXISTING_CLIENT" != "None" ]; then
  CLIENT_ID="$EXISTING_CLIENT"
  log_warn "App Client ya existe: $CLIENT_ID"
else
  CLIENT_ID=$(aws cognito-idp create-user-pool-client \
    --user-pool-id "$USER_POOL_ID" \
    --client-name ado-dashboard-client \
    --explicit-auth-flows ALLOW_USER_SRP_AUTH ALLOW_USER_PASSWORD_AUTH ALLOW_REFRESH_TOKEN_AUTH \
    --no-generate-secret \
    --region $REGION \
    --query 'UserPoolClient.ClientId' --output text)
  log_ok "App Client creado: $CLIENT_ID"
fi
save_var "CLIENT_ID" "$CLIENT_ID"

# Usuario demo
aws cognito-idp admin-create-user \
  --user-pool-id "$USER_POOL_ID" \
  --username "demo@adomobilityia.com" \
  --user-attributes Name=email,Value=demo@adomobilityia.com Name=email_verified,Value=true \
  --temporary-password "TempPass123!" \
  --message-action SUPPRESS \
  --region $REGION 2>/dev/null && log_ok "Usuario demo creado" || log_warn "Usuario demo ya existe"

aws cognito-idp admin-set-user-password \
  --user-pool-id "$USER_POOL_ID" \
  --username "demo@adomobilityia.com" \
  --password "DemoADO2026!" \
  --permanent \
  --region $REGION 2>/dev/null
log_ok "Password de demo configurado: demo@adomobilityia.com / DemoADO2026!"

# =============================================================================
# PASO 8 — Crear API Gateway HTTP API
# =============================================================================
log_step "8/13" "Crear API Gateway HTTP API"

# Verificar si ya existe
EXISTING_API=$(aws apigatewayv2 get-apis --region $REGION \
  --query "Items[?Name=='ado-mobilityia-api'].ApiId" --output text 2>/dev/null || echo "")

if [ -n "$EXISTING_API" ] && [ "$EXISTING_API" != "None" ]; then
  API_ID="$EXISTING_API"
  API_ENDPOINT=$(aws apigatewayv2 get-api --api-id "$API_ID" --region $REGION \
    --query 'ApiEndpoint' --output text)
  log_warn "API Gateway ya existe: $API_ID"
else
  API_RESULT=$(aws apigatewayv2 create-api \
    --name ado-mobilityia-api \
    --protocol-type HTTP \
    --cors-configuration '{"AllowOrigins":["http://localhost:3000","https://*.cloudfront.net"],"AllowMethods":["GET","POST","OPTIONS"],"AllowHeaders":["Content-Type","Authorization"],"MaxAge":86400}' \
    --region $REGION)

  API_ID=$(echo "$API_RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin)['ApiId'])")
  API_ENDPOINT=$(echo "$API_RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin)['ApiEndpoint'])")
  log_ok "API creada: $API_ID"
fi
save_var "API_ID" "$API_ID"
save_var "API_ENDPOINT" "$API_ENDPOINT"

# JWT Authorizer
EXISTING_AUTH=$(aws apigatewayv2 get-authorizers --api-id "$API_ID" --region $REGION \
  --query "Items[?Name=='cognito-jwt'].AuthorizerId" --output text 2>/dev/null || echo "")

if [ -n "$EXISTING_AUTH" ] && [ "$EXISTING_AUTH" != "None" ]; then
  AUTHORIZER_ID="$EXISTING_AUTH"
  log_warn "Authorizer ya existe: $AUTHORIZER_ID"
else
  AUTHORIZER_ID=$(aws apigatewayv2 create-authorizer \
    --api-id "$API_ID" \
    --authorizer-type JWT \
    --identity-source '$request.header.Authorization' \
    --name cognito-jwt \
    --jwt-configuration "{\"Audience\":[\"${CLIENT_ID}\"],\"Issuer\":\"https://cognito-idp.${REGION}.amazonaws.com/${USER_POOL_ID}\"}" \
    --region $REGION \
    --query 'AuthorizerId' --output text)
  log_ok "JWT Authorizer creado: $AUTHORIZER_ID"
fi
save_var "AUTHORIZER_ID" "$AUTHORIZER_ID"

# Integraciones Lambda
create_integration() {
  local FUNC_NAME=$1
  aws apigatewayv2 create-integration \
    --api-id "$API_ID" \
    --integration-type AWS_PROXY \
    --integration-uri "arn:aws:lambda:${REGION}:${ACCOUNT_ID}:function:${FUNC_NAME}" \
    --payload-format-version "2.0" \
    --region $REGION \
    --query 'IntegrationId' --output text
}

# Verificar si ya hay integraciones
EXISTING_INTEGRATIONS=$(aws apigatewayv2 get-integrations --api-id "$API_ID" --region $REGION \
  --query 'Items | length(@)' --output text 2>/dev/null || echo "0")

if [ "$EXISTING_INTEGRATIONS" -gt "0" ]; then
  log_warn "Integraciones ya existen — saltando creación de rutas"
else
  DASHBOARD_INT_ID=$(create_integration "ado-dashboard-api")
  CHAT_INT_ID=$(create_integration "ado-chat-api")
  log_ok "Integraciones creadas: dashboard=$DASHBOARD_INT_ID, chat=$CHAT_INT_ID"

  # Rutas del dashboard
  for ROUTE in "GET /dashboard/flota-status" "GET /dashboard/alertas-activas" "GET /dashboard/resumen-consumo" "GET /dashboard/co2-estimado"; do
    aws apigatewayv2 create-route \
      --api-id "$API_ID" \
      --route-key "$ROUTE" \
      --target "integrations/${DASHBOARD_INT_ID}" \
      --authorization-type JWT \
      --authorizer-id "$AUTHORIZER_ID" \
      --region $REGION > /dev/null
  done
  log_ok "4 rutas de dashboard creadas"

  # Ruta de chat
  aws apigatewayv2 create-route \
    --api-id "$API_ID" \
    --route-key "POST /chat" \
    --target "integrations/${CHAT_INT_ID}" \
    --authorization-type JWT \
    --authorizer-id "$AUTHORIZER_ID" \
    --region $REGION > /dev/null
  log_ok "Ruta POST /chat creada"

  # Stage con auto-deploy
  aws apigatewayv2 create-stage \
    --api-id "$API_ID" \
    --stage-name '$default' \
    --auto-deploy \
    --region $REGION > /dev/null 2>&1 || true
  log_ok "Stage \$default con auto-deploy"
fi

# Permisos para API Gateway → Lambda
for FUNC in ado-dashboard-api ado-chat-api; do
  aws lambda add-permission \
    --function-name "$FUNC" \
    --statement-id "apigateway-invoke-${FUNC}" \
    --action lambda:InvokeFunction \
    --principal apigateway.amazonaws.com \
    --source-arn "arn:aws:execute-api:${REGION}:${ACCOUNT_ID}:${API_ID}/*" \
    --region $REGION 2>/dev/null || true
done
log_ok "Permisos Lambda ← API Gateway configurados"

# =============================================================================
# PASO 9 — Knowledge Base (MANUAL — instrucciones)
# =============================================================================
log_step "9/13" "Knowledge Base en Bedrock"

echo -e "${YELLOW}"
echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║  ⚠️  PASO MANUAL: Crear Knowledge Base desde la consola AWS     ║"
echo "║                                                                 ║"
echo "║  1. Ir a Amazon Bedrock > Knowledge Bases > Create              ║"
echo "║  2. Nombre: ado-mobilityia-kb                                   ║"
echo "║  3. Data source: Amazon S3                                      ║"
echo "║  4. S3 URI: s3://ado-telemetry-mvp/hackathon-data/             ║"
echo "║            knowledge-base/docs/                                 ║"
echo "║  5. Embedding: Amazon Titan Embeddings v2                       ║"
echo "║  6. Vector store: Quick create (OpenSearch Serverless)          ║"
echo "║  7. Click Create y luego Sync                                   ║"
echo "║                                                                 ║"
echo "║  Documentos que se indexarán (ya subidos a S3):                 ║"
echo "║  - motor_spn.json                                              ║"
echo "║  - codigos-falla-catalogo.csv                                  ║"
echo "║  - manual-reglas-mantenimiento-motor.md                        ║"
echo "║  - manual-reglas-ambientales-emisiones.md                      ║"
echo "║  - manual-reglas-fallas-mantenimiento.md                       ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

read -p "Ingresa el Knowledge Base ID (ej: 4OAVLRB8VI): " KB_ID
if [ -z "$KB_ID" ]; then
  log_warn "KB ID vacío — los agentes no tendrán RAG hasta que lo configures"
  KB_ID="PENDIENTE"
fi
save_var "KB_ID" "$KB_ID"

# =============================================================================
# PASO 10 — SageMaker (MANUAL o con backup)
# =============================================================================
log_step "10/13" "Modelo SageMaker"

if [ -f "${BACKUP_DIR:-/nonexistent}/model.tar.gz" ] && [ -f "${BACKUP_DIR:-/nonexistent}/feature_names.json" ]; then
  echo -e "${YELLOW}"
  echo "╔══════════════════════════════════════════════════════════════════╗"
  echo "║  El modelo ML ya se subió a S3 en el Paso 2.                   ║"
  echo "║  Para crear el endpoint, ejecuta desde SageMaker Studio:       ║"
  echo "║                                                                 ║"
  echo "║  1. Crear modelo desde model.tar.gz en S3                      ║"
  echo "║  2. Crear endpoint config: ml.m5.large                         ║"
  echo "║  3. Crear endpoint: ado-prediccion-eventos                     ║"
  echo "║                                                                 ║"
  echo "║  O ejecutar: python sagemaker/02-modelo-v2-optimizado.py       ║"
  echo "║  (ajustar paths de S3 si cambiaron)                            ║"
  echo "╚══════════════════════════════════════════════════════════════════╝"
  echo -e "${NC}"
else
  echo -e "${YELLOW}"
  echo "╔══════════════════════════════════════════════════════════════════╗"
  echo "║  ⚠️  No hay backup del modelo ML.                               ║"
  echo "║                                                                 ║"
  echo "║  Opciones:                                                      ║"
  echo "║  A) Si tienes los Parquets raw, re-entrenar:                   ║"
  echo "║     python sagemaker/01-feature-engineering-and-training.py     ║"
  echo "║     python sagemaker/02-modelo-v2-optimizado.py                ║"
  echo "║                                                                 ║"
  echo "║  B) Si NO tienes Parquets, el sistema funciona sin SageMaker   ║"
  echo "║     La Lambda tool-predecir-evento tiene fallback heurístico.  ║"
  echo "║                                                                 ║"
  echo "║  Endpoint esperado: ado-prediccion-eventos (ml.m5.large)       ║"
  echo "╚══════════════════════════════════════════════════════════════════╝"
  echo -e "${NC}"
fi

read -p "¿El endpoint ado-prediccion-eventos está InService? (s/n): " SM_READY
if [ "$SM_READY" = "s" ]; then
  log_ok "SageMaker endpoint confirmado"
else
  log_warn "SageMaker no disponible — el agente usará fallback heurístico"
fi

# =============================================================================
# PASO 11 — Desplegar agentes AgentCore
# =============================================================================
log_step "11/13" "Desplegar agentes AgentCore"

# Actualizar aws-targets.json con la nueva cuenta
for AGENT_DIR in AdoCombustible AdoMantenimiento; do
  TARGETS_FILE="${PROJECT_ROOT}/agentcore-agents/${AGENT_DIR}/agentcore/aws-targets.json"
  cat > "$TARGETS_FILE" << TARGETS_EOF
[
  {
    "name": "default",
    "account": "${ACCOUNT_ID}",
    "region": "${REGION}"
  }
]
TARGETS_EOF
  log_ok "aws-targets.json actualizado para ${AGENT_DIR}"
done

# Actualizar Knowledge Base ID en los agentes
if [ "$KB_ID" != "PENDIENTE" ]; then
  for AGENT in AdoCombustible AdoMantenimiento; do
    MAIN_PY="${PROJECT_ROOT}/agentcore-agents/${AGENT}/app/${AGENT}/main.py"
    if [ -f "$MAIN_PY" ]; then
      sed -i.bak "s/KNOWLEDGE_BASE_ID = \"[^\"]*\"/KNOWLEDGE_BASE_ID = \"${KB_ID}\"/" "$MAIN_PY"
      rm -f "${MAIN_PY}.bak"
      log_ok "KB ID actualizado en ${AGENT}/main.py"
    fi
  done
fi

# Deploy de cada agente
echo ""
echo -e "${YELLOW}Desplegando agentes AgentCore (esto toma ~5 min por agente)...${NC}"

for AGENT_DIR in AdoCombustible AdoMantenimiento; do
  AGENTCORE_DIR="${PROJECT_ROOT}/agentcore-agents/${AGENT_DIR}/agentcore"

  echo -e "\n${BLUE}>>> Desplegando ${AGENT_DIR}...${NC}"

  # Instalar dependencias CDK si no existen
  if [ ! -d "${AGENTCORE_DIR}/cdk/node_modules" ]; then
    cd "${AGENTCORE_DIR}/cdk"
    npm install
    cd "$PROJECT_ROOT"
  fi

  # Deploy
  cd "$AGENTCORE_DIR"
  agentcore deploy --target default 2>&1 | tail -5
  cd "$PROJECT_ROOT"

  log_ok "${AGENT_DIR} desplegado"
done

# Obtener ARNs de los agentes
echo ""
log_info "Obteniendo ARNs de los agentes desplegados..."

# Leer del deployed-state.json
COMBUSTIBLE_STATE="${PROJECT_ROOT}/agentcore-agents/AdoCombustible/agentcore/.cli/deployed-state.json"
MANTENIMIENTO_STATE="${PROJECT_ROOT}/agentcore-agents/AdoMantenimiento/agentcore/.cli/deployed-state.json"

if [ -f "$COMBUSTIBLE_STATE" ]; then
  ARN_COMBUSTIBLE=$(python3 -c "
import json
with open('${COMBUSTIBLE_STATE}') as f:
    state = json.load(f)
for rt in state.get('runtimes', []):
    if 'agentRuntimeArn' in rt:
        print(rt['agentRuntimeArn'])
        break
" 2>/dev/null || echo "")
fi

if [ -f "$MANTENIMIENTO_STATE" ]; then
  ARN_MANTENIMIENTO=$(python3 -c "
import json
with open('${MANTENIMIENTO_STATE}') as f:
    state = json.load(f)
for rt in state.get('runtimes', []):
    if 'agentRuntimeArn' in rt:
        print(rt['agentRuntimeArn'])
        break
" 2>/dev/null || echo "")
fi

# Si no se encontraron en deployed-state, pedir manualmente
if [ -z "${ARN_COMBUSTIBLE:-}" ]; then
  echo -e "${YELLOW}No se pudo leer el ARN de AdoCombustible automáticamente.${NC}"
  read -p "Ingresa el ARN del agente AdoCombustible: " ARN_COMBUSTIBLE
fi

if [ -z "${ARN_MANTENIMIENTO:-}" ]; then
  echo -e "${YELLOW}No se pudo leer el ARN de AdoMantenimiento automáticamente.${NC}"
  read -p "Ingresa el ARN del agente AdoMantenimiento: " ARN_MANTENIMIENTO
fi

save_var "ARN_COMBUSTIBLE" "$ARN_COMBUSTIBLE"
save_var "ARN_MANTENIMIENTO" "$ARN_MANTENIMIENTO"

# Actualizar la Lambda ado-chat-api con los ARNs reales
aws lambda update-function-configuration \
  --function-name ado-chat-api \
  --environment "Variables={RUNTIME_ARN_COMBUSTIBLE=${ARN_COMBUSTIBLE},RUNTIME_ARN_MANTENIMIENTO=${ARN_MANTENIMIENTO},AWS_REGION_OVERRIDE=${REGION}}" \
  --region $REGION > /dev/null

log_ok "ado-chat-api actualizada con ARNs de AgentCore"

# =============================================================================
# PASO 12 — Frontend React + S3 + CloudFront
# =============================================================================
log_step "12/13" "Desplegar frontend React"

# Crear .env.local con los nuevos IDs
cat > "${PROJECT_ROOT}/dashboard/.env.local" << ENV_EOF
VITE_API_BASE_URL=${API_ENDPOINT}
VITE_COGNITO_USER_POOL_ID=${USER_POOL_ID}
VITE_COGNITO_CLIENT_ID=${CLIENT_ID}
VITE_AWS_REGION=${REGION}
ENV_EOF
log_ok ".env.local creado con nuevos IDs"

# Build
cd "${PROJECT_ROOT}/dashboard"
npm install
npx vite build
cd "$PROJECT_ROOT"
log_ok "Frontend compilado"

# Subir a S3
aws s3 sync "${PROJECT_ROOT}/dashboard/dist/" "s3://ado-mobilityia-dashboard/" \
  --delete --region $REGION
log_ok "Frontend subido a S3"

# CloudFront — crear OAC
OAC_ID=$(aws cloudfront create-origin-access-control \
  --origin-access-control-config "{
    \"Name\": \"ado-dashboard-oac-$(date +%s)\",
    \"Description\": \"OAC for ADO dashboard\",
    \"SigningProtocol\": \"sigv4\",
    \"SigningBehavior\": \"always\",
    \"OriginAccessControlOriginType\": \"s3\"
  }" \
  --query 'OriginAccessControl.Id' --output text 2>/dev/null || echo "")

if [ -z "$OAC_ID" ]; then
  log_warn "No se pudo crear OAC — puede que ya exista"
  OAC_ID=$(aws cloudfront list-origin-access-controls \
    --query "OriginAccessControlList.Items[?contains(Name,'ado-dashboard')].Id | [0]" --output text 2>/dev/null || echo "")
fi
save_var "OAC_ID" "${OAC_ID:-MANUAL}"

# Crear distribución CloudFront
cat > "${TEMP_DIR}/cf-config.json" << CF_EOF
{
  "CallerReference": "ado-dashboard-$(date +%s)",
  "Comment": "ADO MobilityIA Dashboard",
  "DefaultCacheBehavior": {
    "TargetOriginId": "S3-ado-mobilityia-dashboard",
    "ViewerProtocolPolicy": "redirect-to-https",
    "AllowedMethods": {"Quantity": 2, "Items": ["GET", "HEAD"]},
    "CachedMethods": {"Quantity": 2, "Items": ["GET", "HEAD"]},
    "ForwardedValues": {"QueryString": false, "Cookies": {"Forward": "none"}},
    "MinTTL": 0,
    "DefaultTTL": 86400,
    "MaxTTL": 31536000,
    "Compress": true
  },
  "Origins": {
    "Quantity": 1,
    "Items": [{
      "Id": "S3-ado-mobilityia-dashboard",
      "DomainName": "ado-mobilityia-dashboard.s3.${REGION}.amazonaws.com",
      "S3OriginConfig": {"OriginAccessIdentity": ""},
      "OriginAccessControlId": "${OAC_ID:-}"
    }]
  },
  "Enabled": true,
  "DefaultRootObject": "index.html",
  "CustomErrorResponses": {
    "Quantity": 1,
    "Items": [{
      "ErrorCode": 403,
      "ResponsePagePath": "/index.html",
      "ResponseCode": "200",
      "ErrorCachingMinTTL": 10
    }]
  }
}
CF_EOF

CF_RESULT=$(aws cloudfront create-distribution \
  --distribution-config "file://${TEMP_DIR}/cf-config.json" 2>/dev/null || echo "")

if [ -n "$CF_RESULT" ]; then
  CF_DISTRIBUTION_ID=$(echo "$CF_RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin)['Distribution']['Id'])")
  CF_DOMAIN=$(echo "$CF_RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin)['Distribution']['DomainName'])")
  save_var "CF_DISTRIBUTION_ID" "$CF_DISTRIBUTION_ID"
  save_var "CF_DOMAIN" "$CF_DOMAIN"
  log_ok "CloudFront creado: https://${CF_DOMAIN}"
else
  log_warn "No se pudo crear CloudFront automáticamente — crear manualmente"
  read -p "Ingresa el Distribution ID (o ENTER para saltar): " CF_DISTRIBUTION_ID
  read -p "Ingresa el dominio CloudFront (ej: dXXXXX.cloudfront.net): " CF_DOMAIN
  save_var "CF_DISTRIBUTION_ID" "${CF_DISTRIBUTION_ID:-MANUAL}"
  save_var "CF_DOMAIN" "${CF_DOMAIN:-MANUAL}"
fi

# Bucket policy para CloudFront
if [ -n "${CF_DISTRIBUTION_ID:-}" ] && [ "$CF_DISTRIBUTION_ID" != "MANUAL" ]; then
  cat > "${TEMP_DIR}/bucket-policy.json" << BP_EOF
{
  "Version": "2012-10-17",
  "Statement": [{
    "Sid": "AllowCloudFrontServicePrincipal",
    "Effect": "Allow",
    "Principal": {"Service": "cloudfront.amazonaws.com"},
    "Action": "s3:GetObject",
    "Resource": "arn:aws:s3:::ado-mobilityia-dashboard/*",
    "Condition": {
      "StringEquals": {
        "AWS:SourceArn": "arn:aws:cloudfront::${ACCOUNT_ID}:distribution/${CF_DISTRIBUTION_ID}"
      }
    }
  }]
}
BP_EOF

  aws s3api put-bucket-policy \
    --bucket ado-mobilityia-dashboard \
    --policy "file://${TEMP_DIR}/bucket-policy.json"
  log_ok "Bucket policy configurada para CloudFront"

  # Actualizar CORS en API Gateway
  aws apigatewayv2 update-api \
    --api-id "$API_ID" \
    --cors-configuration "{\"AllowOrigins\":[\"http://localhost:3000\",\"https://${CF_DOMAIN}\"],\"AllowMethods\":[\"GET\",\"POST\",\"OPTIONS\"],\"AllowHeaders\":[\"Content-Type\",\"Authorization\"],\"MaxAge\":86400}" \
    --region $REGION > /dev/null
  log_ok "CORS actualizado con dominio CloudFront"
fi

# =============================================================================
# PASO 13 — Verificación end-to-end
# =============================================================================
log_step "13/13" "Verificación end-to-end"

# Ejecutar simulador para poblar DynamoDB
log_info "Ejecutando simulador 3 veces para poblar DynamoDB..."
for i in 1 2 3; do
  aws lambda invoke \
    --function-name ado-simulador-telemetria \
    --payload '{}' \
    --region $REGION \
    "${TEMP_DIR}/sim-${i}.json" > /dev/null 2>&1 && \
    log_ok "Simulador invocación $i OK" || \
    log_warn "Simulador invocación $i falló (¿falta viajes_consolidados.json?)"
  sleep 5
done

# Verificar DynamoDB
ITEM_COUNT=$(aws dynamodb scan \
  --table-name ado-telemetria-live \
  --select COUNT \
  --region $REGION \
  --query 'Count' --output text 2>/dev/null || echo "0")
log_info "Items en ado-telemetria-live: $ITEM_COUNT"

# Test de API con Cognito
log_info "Probando autenticación Cognito..."
TOKEN=$(aws cognito-idp initiate-auth \
  --auth-flow USER_PASSWORD_AUTH \
  --client-id "$CLIENT_ID" \
  --auth-parameters "USERNAME=demo@adomobilityia.com,PASSWORD=DemoADO2026!" \
  --region $REGION \
  --query 'AuthenticationResult.IdToken' --output text 2>/dev/null || echo "")

if [ -n "$TOKEN" ] && [ "$TOKEN" != "None" ]; then
  log_ok "Token de Cognito obtenido"

  # Test flota-status
  HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
    -H "Authorization: Bearer $TOKEN" \
    "${API_ENDPOINT}/dashboard/flota-status" 2>/dev/null || echo "000")
  if [ "$HTTP_CODE" = "200" ]; then
    log_ok "GET /dashboard/flota-status → 200 OK"
  else
    log_warn "GET /dashboard/flota-status → HTTP $HTTP_CODE"
  fi

  # Test chat
  CHAT_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
    -X POST \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"prompt":"Hola, ¿qué buses están activos?","agente":"combustible"}' \
    "${API_ENDPOINT}/chat" 2>/dev/null || echo "000")
  if [ "$CHAT_CODE" = "200" ]; then
    log_ok "POST /chat → 200 OK (agente respondió)"
  else
    log_warn "POST /chat → HTTP $CHAT_CODE (puede tardar si AgentCore está arrancando)"
  fi
else
  log_warn "No se pudo obtener token de Cognito — verificar User Pool"
fi

# =============================================================================
# RESUMEN FINAL
# =============================================================================
echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}  ✅ RESTAURACIÓN COMPLETADA${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "  ${BLUE}Cuenta:${NC}        $ACCOUNT_ID"
echo -e "  ${BLUE}Región:${NC}        $REGION"
echo -e "  ${BLUE}API Gateway:${NC}   $API_ENDPOINT"
echo -e "  ${BLUE}CloudFront:${NC}    https://${CF_DOMAIN:-PENDIENTE}"
echo -e "  ${BLUE}Cognito Pool:${NC}  $USER_POOL_ID"
echo -e "  ${BLUE}Cognito Client:${NC} $CLIENT_ID"
echo -e "  ${BLUE}KB ID:${NC}         $KB_ID"
echo -e "  ${BLUE}Agente Comb:${NC}   ${ARN_COMBUSTIBLE:-PENDIENTE}"
echo -e "  ${BLUE}Agente Mant:${NC}   ${ARN_MANTENIMIENTO:-PENDIENTE}"
echo -e "  ${BLUE}DynamoDB:${NC}      $ITEM_COUNT items en telemetría"
echo ""
echo -e "  ${BLUE}Login:${NC}         demo@adomobilityia.com / DemoADO2026!"
echo ""
echo -e "  ${YELLOW}Todos los IDs guardados en:${NC} $OUTPUT_FILE"
echo ""

# Pasos manuales pendientes
echo -e "${YELLOW}📋 PASOS MANUALES PENDIENTES:${NC}"
if [ "$KB_ID" = "PENDIENTE" ]; then
  echo -e "  ${RED}[ ] Crear Knowledge Base en consola de Bedrock${NC}"
  echo -e "      Luego actualizar KB_ID en los main.py de los agentes y re-desplegar"
fi
if [ "${SM_READY:-n}" != "s" ]; then
  echo -e "  ${YELLOW}[ ] Crear endpoint SageMaker ado-prediccion-eventos${NC}"
  echo -e "      (opcional — el sistema funciona con fallback heurístico)"
fi
if [ "${CF_DOMAIN:-MANUAL}" = "MANUAL" ]; then
  echo -e "  ${RED}[ ] Crear distribución CloudFront manualmente${NC}"
fi
echo ""

# Cleanup
rm -rf "$TEMP_DIR"
