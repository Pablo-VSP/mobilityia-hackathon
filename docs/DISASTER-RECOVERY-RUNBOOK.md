# 🔄 Runbook de Recuperación — ADO MobilityIA
## Cómo levantar TODO desde cero en una cuenta AWS nueva

> **Tiempo estimado:** 3-4 horas si se sigue este runbook paso a paso.
> **Región:** us-east-2 (Ohio) — todo el proyecto vive aquí.
> **Prerrequisitos:** AWS CLI configurado, Node.js 18+, Python 3.12+, uv (Python), AgentCore CLI.

---

## 📋 Inventario completo de lo que hay que recrear

| # | Recurso | Servicio AWS | Dependencias |
|---|---------|-------------|--------------|
| 1 | 3 buckets S3 | S3 | Ninguna |
| 2 | Datos simulados en S3 | S3 | Bucket creado |
| 3 | Knowledge Base docs en S3 | S3 | Bucket creado |
| 4 | IAM Role para Lambdas | IAM | Ninguna |
| 5 | Lambda Layer (ado-common) | Lambda | IAM Role |
| 6 | 10 funciones Lambda | Lambda | Layer + IAM Role |
| 7 | 2 tablas DynamoDB | DynamoDB | Ninguna |
| 8 | Cognito User Pool + usuario | Cognito | Ninguna |
| 9 | API Gateway HTTP API | API Gateway | Lambdas + Cognito |
| 10 | Knowledge Base | Bedrock | S3 docs |
| 11 | Modelo SageMaker | SageMaker | S3 datos |
| 12 | 2 Agentes AgentCore | AgentCore | Lambdas + KB + SageMaker |
| 13 | Frontend React en S3+CloudFront | S3 + CloudFront | API Gateway + Cognito |

---

## PASO 0 — Preparar el repositorio local

Todo el código fuente está en el repo Git. Clónalo y verifica la estructura:

```bash
# Verificar que tienes todo
ls lambda-functions/          # 10 carpetas de Lambdas + layers/
ls agentcore-agents/          # AdoCombustible/ y AdoMantenimiento/
ls dashboard/                 # Frontend React
ls sagemaker/                 # Scripts de entrenamiento ML
ls manuales/                  # 4 documentos para Knowledge Base
ls datos_spn/                 # Catálogos SPN y fallas
ls models/                    # Esquemas de datos JSON
```

Configura AWS CLI con la nueva cuenta:
```bash
aws configure
# Region: us-east-2
# Output: json
```


---

## PASO 1 — Crear buckets S3 (2 min)

```bash
# Bucket principal de datos (Data Lake)
aws s3 mb s3://ado-telemetry-mvp --region us-east-2

# Bucket para código de Lambdas
aws s3 mb s3://mobilityia-hackathon-bl-2026 --region us-east-2

# Bucket para frontend (hosting estático)
aws s3 mb s3://ado-mobilityia-dashboard --region us-east-2
```

> **Nota:** Si los nombres de bucket ya están tomados (son globales), usa un sufijo como `-v2` o tu account ID. Luego actualiza las referencias en las Lambdas y el frontend.

---

## PASO 2 — Subir datos simulados a S3 (10 min)

Los datos Parquet originales (~460 MB) deben estar en tu máquina local o en un backup. Si los tienes:

```bash
# Datos raw de telemetría (1,339 Parquets, ~447 MB)
aws s3 sync ./data/raw/travel_telemetry/ \
  s3://ado-telemetry-mvp/hackathon-data/raw/travel_telemetry/ --region us-east-2

# Datos raw de fallas (123 Parquets, ~6.5 MB)
aws s3 sync ./data/raw/data_fault/ \
  s3://ado-telemetry-mvp/hackathon-data/raw/data_fault/ --region us-east-2

# Catálogo SPN (1 Parquet)
aws s3 sync ./data/raw/motor_spn/ \
  s3://ado-telemetry-mvp/hackathon-data/raw/motor_spn/ --region us-east-2

# Catálogo SPN en JSON (para Lambdas)
aws s3 cp datos_spn/data.JSON \
  s3://ado-telemetry-mvp/hackathon-data/catalogo/motor_spn.json --region us-east-2

# Catálogo de fallas con severidad_inferencia
aws s3 cp datos_spn/fault_data_catalog.JSON \
  s3://ado-telemetry-mvp/hackathon-data/fallas-simuladas/data_fault.json --region us-east-2

# Viajes consolidados para el simulador (~12 MB)
aws s3 cp ./data/simulacion/viajes_consolidados.json \
  s3://ado-telemetry-mvp/hackathon-data/simulacion/viajes_consolidados.json --region us-east-2
```

### Subir documentos para Knowledge Base

```bash
# Crear carpeta de Knowledge Base en S3
aws s3 cp datos_spn/data.JSON \
  s3://ado-telemetry-mvp/hackathon-data/knowledge-base/docs/motor_spn.json --region us-east-2

aws s3 cp datos_spn/fault_data_catalog.JSON \
  s3://ado-telemetry-mvp/hackathon-data/knowledge-base/docs/codigos-falla-catalogo.csv --region us-east-2

aws s3 cp manuales/manual-reglas-mantenimiento-motor.md \
  s3://ado-telemetry-mvp/hackathon-data/knowledge-base/docs/ --region us-east-2

aws s3 cp manuales/manual-reglas-ambientales-emisiones.md \
  s3://ado-telemetry-mvp/hackathon-data/knowledge-base/docs/ --region us-east-2

aws s3 cp manuales/manual-reglas-fallas-mantenimiento.md \
  s3://ado-telemetry-mvp/hackathon-data/knowledge-base/docs/ --region us-east-2
```

> **⚠️ CRÍTICO:** Si NO tienes los Parquets originales, necesitas regenerarlos. Los scripts de generación de datos simulados deberían estar en el repo. Sin los Parquets, el simulador y el modelo ML no funcionan.


---

## PASO 3 — Crear tablas DynamoDB (2 min)

```bash
# Tabla de telemetría en tiempo real
aws dynamodb create-table \
  --table-name ado-telemetria-live \
  --attribute-definitions \
    AttributeName=autobus,AttributeType=S \
    AttributeName=timestamp,AttributeType=S \
    AttributeName=viaje_ruta,AttributeType=S \
  --key-schema \
    AttributeName=autobus,KeyType=HASH \
    AttributeName=timestamp,KeyType=RANGE \
  --global-secondary-indexes \
    '[{
      "IndexName": "viaje_ruta-timestamp-index",
      "KeySchema": [
        {"AttributeName": "viaje_ruta", "KeyType": "HASH"},
        {"AttributeName": "timestamp", "KeyType": "RANGE"}
      ],
      "Projection": {"ProjectionType": "ALL"},
      "ProvisionedThroughput": {"ReadCapacityUnits": 5, "WriteCapacityUnits": 5}
    }]' \
  --billing-mode PAY_PER_REQUEST \
  --region us-east-2

# Habilitar TTL
aws dynamodb update-time-to-live \
  --table-name ado-telemetria-live \
  --time-to-live-specification "Enabled=true,AttributeName=ttl_expiry" \
  --region us-east-2

# Tabla de alertas
aws dynamodb create-table \
  --table-name ado-alertas \
  --attribute-definitions \
    AttributeName=alerta_id,AttributeType=S \
    AttributeName=timestamp,AttributeType=S \
  --key-schema \
    AttributeName=alerta_id,KeyType=HASH \
    AttributeName=timestamp,KeyType=RANGE \
  --billing-mode PAY_PER_REQUEST \
  --region us-east-2
```

> **Nota:** El GSI usa `PAY_PER_REQUEST` en la tabla principal, así que no necesita throughput separado. El comando de arriba incluye el throughput del GSI por compatibilidad — DynamoDB lo ignora en modo on-demand.


---

## PASO 4 — Crear IAM Role para Lambdas (5 min)

```bash
# Crear el trust policy
cat > /tmp/lambda-trust-policy.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

# Crear el rol
aws iam create-role \
  --role-name ado-lambda-execution-role \
  --assume-role-policy-document file:///tmp/lambda-trust-policy.json

# Adjuntar políticas básicas
aws iam attach-role-policy \
  --role-name ado-lambda-execution-role \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

# Crear política personalizada con todos los permisos necesarios
cat > /tmp/ado-lambda-policy.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "DynamoDBAccess",
      "Effect": "Allow",
      "Action": [
        "dynamodb:PutItem",
        "dynamodb:GetItem",
        "dynamodb:Query",
        "dynamodb:Scan",
        "dynamodb:UpdateItem",
        "dynamodb:DeleteItem",
        "dynamodb:BatchWriteItem"
      ],
      "Resource": [
        "arn:aws:dynamodb:us-east-2:*:table/ado-telemetria-live",
        "arn:aws:dynamodb:us-east-2:*:table/ado-telemetria-live/index/*",
        "arn:aws:dynamodb:us-east-2:*:table/ado-alertas",
        "arn:aws:dynamodb:us-east-2:*:table/ado-alertas/index/*"
      ]
    },
    {
      "Sid": "S3Access",
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::ado-telemetry-mvp",
        "arn:aws:s3:::ado-telemetry-mvp/*"
      ]
    },
    {
      "Sid": "SageMakerInvoke",
      "Effect": "Allow",
      "Action": [
        "sagemaker:InvokeEndpoint"
      ],
      "Resource": "arn:aws:sagemaker:us-east-2:*:endpoint/ado-prediccion-eventos"
    },
    {
      "Sid": "BedrockAgentCoreInvoke",
      "Effect": "Allow",
      "Action": [
        "bedrock-agentcore:InvokeAgentRuntime"
      ],
      "Resource": "arn:aws:bedrock-agentcore:us-east-2:*:runtime/*"
    },
    {
      "Sid": "BedrockKBAccess",
      "Effect": "Allow",
      "Action": [
        "bedrock:Retrieve",
        "bedrock:RetrieveAndGenerate"
      ],
      "Resource": "*"
    },
    {
      "Sid": "LambdaInvoke",
      "Effect": "Allow",
      "Action": [
        "lambda:InvokeFunction"
      ],
      "Resource": "arn:aws:lambda:us-east-2:*:function:tool-*"
    }
  ]
}
EOF

aws iam put-role-policy \
  --role-name ado-lambda-execution-role \
  --policy-name ado-lambda-custom-policy \
  --policy-document file:///tmp/ado-lambda-policy.json
```

> **Anota el ARN del rol** — lo necesitas para todas las Lambdas:
> `arn:aws:iam::<NUEVA_ACCOUNT_ID>:role/ado-lambda-execution-role`


---

## PASO 5 — Desplegar Lambda Layer (5 min)

```bash
# Empaquetar el layer
cd lambda-functions/layers/ado-common
zip -r /tmp/ado-common-layer.zip python/

# Publicar el layer
aws lambda publish-layer-version \
  --layer-name ado-common-layer \
  --description "Shared utilities: SPN catalog, DynamoDB helpers, response format" \
  --zip-file fileb:///tmp/ado-common-layer.zip \
  --compatible-runtimes python3.12 \
  --region us-east-2

cd ../../..
```

> **Anota el LayerVersionArn** que retorna — lo necesitas para cada Lambda.
> Formato: `arn:aws:lambda:us-east-2:<ACCOUNT>:layer:ado-common-layer:1`

---

## PASO 6 — Desplegar las 10 funciones Lambda (20 min)

### Variables comunes para todas las Lambdas

```bash
export ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
export ROLE_ARN="arn:aws:iam::${ACCOUNT_ID}:role/ado-lambda-execution-role"
export LAYER_ARN="arn:aws:lambda:us-east-2:${ACCOUNT_ID}:layer:ado-common-layer:1"
```

### Script de deploy para cada Lambda

```bash
deploy_lambda() {
  local FUNC_NAME=$1
  local FUNC_DIR=$2
  local TIMEOUT=${3:-30}
  local MEMORY=${4:-256}
  local EXTRA_ENV=${5:-""}

  echo ">>> Deploying $FUNC_NAME..."

  # Empaquetar
  cd "lambda-functions/${FUNC_DIR}"
  zip -r /tmp/${FUNC_NAME}.zip lambda_function.py
  cd ../..

  # Variables de entorno base
  local ENV_VARS="Variables={DYNAMODB_TABLE_TELEMETRIA=ado-telemetria-live,DYNAMODB_TABLE_ALERTAS=ado-alertas,S3_BUCKET=ado-telemetry-mvp,ENVIRONMENT=mvp${EXTRA_ENV}}"

  # Crear función
  aws lambda create-function \
    --function-name "$FUNC_NAME" \
    --runtime python3.12 \
    --handler lambda_function.lambda_handler \
    --role "$ROLE_ARN" \
    --zip-file "fileb:///tmp/${FUNC_NAME}.zip" \
    --timeout "$TIMEOUT" \
    --memory-size "$MEMORY" \
    --layers "$LAYER_ARN" \
    --environment "$ENV_VARS" \
    --region us-east-2

  echo "<<< $FUNC_NAME deployed."
}
```

### Desplegar cada función

```bash
# 1. Simulador de telemetría
deploy_lambda "ado-simulador-telemetria" "ado-simulador-telemetria" 30 512

# 2. Tool: Consultar telemetría (Agente Combustible)
deploy_lambda "tool-consultar-telemetria" "tool-consultar-telemetria" 15 256

# 3. Tool: Calcular desviación (Agente Combustible)
deploy_lambda "tool-calcular-desviacion" "tool-calcular-desviacion" 15 256

# 4. Tool: Listar buses activos (Agente Combustible)
deploy_lambda "tool-listar-buses-activos" "tool-listar-buses-activos" 15 256

# 5. Tool: Consultar OBD (Agente Mantenimiento)
deploy_lambda "tool-consultar-obd" "tool-consultar-obd" 15 256

# 6. Tool: Predecir evento ML (Agente Mantenimiento)
deploy_lambda "tool-predecir-evento" "tool-predecir-evento" 30 512 \
  ",SAGEMAKER_ENDPOINT=ado-prediccion-eventos"

# 7. Tool: Buscar patrones históricos (Agente Mantenimiento)
deploy_lambda "tool-buscar-patrones-historicos" "tool-buscar-patrones-historicos" 15 256

# 8. Tool: Generar recomendación (Agente Mantenimiento)
deploy_lambda "tool-generar-recomendacion" "tool-generar-recomendacion" 15 256

# 9. Tool: Consultar alertas
deploy_lambda "tool-consultar-alertas" "tool-consultar-alertas" 15 256

# 10. Dashboard API (multi-endpoint)
deploy_lambda "ado-dashboard-api" "ado-dashboard-api" 15 256
```

### Chat API (requiere variables especiales — los ARNs de AgentCore se actualizan después)

```bash
cd lambda-functions/ado-chat-api
zip -r /tmp/ado-chat-api.zip lambda_function.py
cd ../..

aws lambda create-function \
  --function-name "ado-chat-api" \
  --runtime python3.12 \
  --handler lambda_function.lambda_handler \
  --role "$ROLE_ARN" \
  --zip-file "fileb:///tmp/ado-chat-api.zip" \
  --timeout 120 \
  --memory-size 512 \
  --environment "Variables={RUNTIME_ARN_COMBUSTIBLE=PLACEHOLDER,RUNTIME_ARN_MANTENIMIENTO=PLACEHOLDER,AWS_REGION_OVERRIDE=us-east-2}" \
  --region us-east-2
```

> **⚠️ IMPORTANTE:** Los ARNs de `RUNTIME_ARN_COMBUSTIBLE` y `RUNTIME_ARN_MANTENIMIENTO` se actualizan en el PASO 11 después de desplegar los agentes AgentCore.


---

## PASO 7 — Crear Cognito User Pool (5 min)

```bash
# Crear User Pool
aws cognito-idp create-user-pool \
  --pool-name ado-mobilityia-users \
  --auto-verified-attributes email \
  --username-attributes email \
  --policies '{"PasswordPolicy":{"MinimumLength":8,"RequireUppercase":true,"RequireLowercase":true,"RequireNumbers":true,"RequireSymbols":true}}' \
  --region us-east-2

# Anota el User Pool ID del output (ej: us-east-2_XXXXXXXXX)
export USER_POOL_ID="<EL_ID_QUE_RETORNA>"

# Crear App Client (sin secret — para SPA)
aws cognito-idp create-user-pool-client \
  --user-pool-id "$USER_POOL_ID" \
  --client-name ado-dashboard-client \
  --explicit-auth-flows ALLOW_USER_SRP_AUTH ALLOW_USER_PASSWORD_AUTH ALLOW_REFRESH_TOKEN_AUTH \
  --no-generate-secret \
  --region us-east-2

# Anota el ClientId del output
export CLIENT_ID="<EL_CLIENT_ID_QUE_RETORNA>"

# Crear usuario de demo
aws cognito-idp admin-create-user \
  --user-pool-id "$USER_POOL_ID" \
  --username "demo@adomobilityia.com" \
  --user-attributes Name=email,Value=demo@adomobilityia.com Name=email_verified,Value=true \
  --temporary-password "TempPass123!" \
  --region us-east-2

# Forzar password permanente
aws cognito-idp admin-set-user-password \
  --user-pool-id "$USER_POOL_ID" \
  --username "demo@adomobilityia.com" \
  --password "DemoADO2026!" \
  --permanent \
  --region us-east-2
```

> **Anota:** `USER_POOL_ID` y `CLIENT_ID` — los necesitas para API Gateway y el frontend.

---

## PASO 8 — Crear API Gateway HTTP API (10 min)

```bash
# Crear la API
aws apigatewayv2 create-api \
  --name ado-mobilityia-api \
  --protocol-type HTTP \
  --cors-configuration '{
    "AllowOrigins": ["http://localhost:3000", "https://*.cloudfront.net"],
    "AllowMethods": ["GET", "POST", "OPTIONS"],
    "AllowHeaders": ["Content-Type", "Authorization"],
    "MaxAge": 86400
  }' \
  --region us-east-2

# Anota el ApiId y ApiEndpoint
export API_ID="<API_ID>"
export API_ENDPOINT="<API_ENDPOINT>"  # ej: https://xxxxx.execute-api.us-east-2.amazonaws.com

# Crear JWT Authorizer con Cognito
aws apigatewayv2 create-authorizer \
  --api-id "$API_ID" \
  --authorizer-type JWT \
  --identity-source '$request.header.Authorization' \
  --name cognito-jwt \
  --jwt-configuration "{
    \"Audience\": [\"$CLIENT_ID\"],
    \"Issuer\": \"https://cognito-idp.us-east-2.amazonaws.com/$USER_POOL_ID\"
  }" \
  --region us-east-2

# Anota el AuthorizerId
export AUTHORIZER_ID="<AUTHORIZER_ID>"

# Crear integraciones Lambda
create_integration() {
  local FUNC_NAME=$1
  aws apigatewayv2 create-integration \
    --api-id "$API_ID" \
    --integration-type AWS_PROXY \
    --integration-uri "arn:aws:lambda:us-east-2:${ACCOUNT_ID}:function:${FUNC_NAME}" \
    --payload-format-version "2.0" \
    --region us-east-2
}

# Integración para dashboard API
DASHBOARD_INTEGRATION=$(create_integration "ado-dashboard-api")
export DASHBOARD_INTEGRATION_ID=$(echo $DASHBOARD_INTEGRATION | python3 -c "import sys,json; print(json.load(sys.stdin)['IntegrationId'])")

# Integración para chat API
CHAT_INTEGRATION=$(create_integration "ado-chat-api")
export CHAT_INTEGRATION_ID=$(echo $CHAT_INTEGRATION | python3 -c "import sys,json; print(json.load(sys.stdin)['IntegrationId'])")

# Crear rutas
for ROUTE in "GET /dashboard/flota-status" "GET /dashboard/alertas-activas" "GET /dashboard/resumen-consumo" "GET /dashboard/co2-estimado"; do
  aws apigatewayv2 create-route \
    --api-id "$API_ID" \
    --route-key "$ROUTE" \
    --target "integrations/$DASHBOARD_INTEGRATION_ID" \
    --authorization-type JWT \
    --authorizer-id "$AUTHORIZER_ID" \
    --region us-east-2
done

aws apigatewayv2 create-route \
  --api-id "$API_ID" \
  --route-key "POST /chat" \
  --target "integrations/$CHAT_INTEGRATION_ID" \
  --authorization-type JWT \
  --authorizer-id "$AUTHORIZER_ID" \
  --region us-east-2

# Crear stage con auto-deploy
aws apigatewayv2 create-stage \
  --api-id "$API_ID" \
  --stage-name '$default' \
  --auto-deploy \
  --region us-east-2

# Dar permiso a API Gateway para invocar las Lambdas
for FUNC in ado-dashboard-api ado-chat-api; do
  aws lambda add-permission \
    --function-name "$FUNC" \
    --statement-id "apigateway-invoke-${FUNC}" \
    --action lambda:InvokeFunction \
    --principal apigateway.amazonaws.com \
    --source-arn "arn:aws:execute-api:us-east-2:${ACCOUNT_ID}:${API_ID}/*" \
    --region us-east-2
done
```


---

## PASO 9 — Crear Knowledge Base en Bedrock (10 min)

Esto se hace desde la **consola de AWS** porque la CLI de Knowledge Bases requiere varios pasos:

### 9.1 — Desde la consola de Amazon Bedrock:

1. Ir a **Amazon Bedrock > Knowledge Bases > Create**
2. **Nombre:** `ado-mobilityia-kb`
3. **Data source:** Amazon S3
4. **S3 URI:** `s3://ado-telemetry-mvp/hackathon-data/knowledge-base/docs/`
5. **Embedding model:** Amazon Titan Embeddings v2
6. **Vector store:** Quick create (OpenSearch Serverless)
7. Click **Create** y esperar a que se sincronice

### 9.2 — Sincronizar la Knowledge Base

Una vez creada, hacer click en **Sync** para indexar los 5 documentos:
- `motor_spn.json` — Catálogo de 37 SPNs
- `codigos-falla-catalogo.csv` — Fallas con severidad_inferencia
- `manual-reglas-mantenimiento-motor.md` — Reglas de mantenimiento
- `manual-reglas-ambientales-emisiones.md` — Normas ambientales
- `manual-reglas-fallas-mantenimiento.md` — Reglas de fallas

> **Anota el Knowledge Base ID** (ej: `4OAVLRB8VI`) — se necesita en el código de los agentes AgentCore.

### 9.3 — Actualizar el ID en el código de los agentes

Editar estos archivos con el nuevo KB ID:
- `agentcore-agents/AdoCombustible/app/AdoCombustible/main.py` → línea `KNOWLEDGE_BASE_ID = "..."`
- `agentcore-agents/AdoMantenimiento/app/AdoMantenimiento/main.py` → línea `KNOWLEDGE_BASE_ID = "..."`

---

## PASO 10 — Entrenar y desplegar modelo SageMaker (30-45 min)

### 10.1 — Ejecutar feature engineering y entrenamiento

Los scripts están en `sagemaker/`:

```bash
# Opción A: Ejecutar desde SageMaker Studio (recomendado)
# 1. Abrir SageMaker Studio en us-east-2
# 2. Subir sagemaker/01-feature-engineering-and-training.py
# 3. Ejecutar como notebook o script
# 4. Luego ejecutar sagemaker/02-modelo-v2-optimizado.py

# Opción B: Ejecutar localmente con boto3 (si tienes los datos en local)
python sagemaker/01-feature-engineering-and-training.py
python sagemaker/02-modelo-v2-optimizado.py
```

### 10.2 — Verificar que el endpoint está InService

```bash
aws sagemaker describe-endpoint \
  --endpoint-name ado-prediccion-eventos \
  --query 'EndpointStatus' \
  --region us-east-2
# Debe retornar: "InService"
```

### 10.3 — Datos del modelo actual (referencia)

| Parámetro | Valor |
|-----------|-------|
| Algoritmo | XGBoost 1.7 |
| Features | 54 (40 telemetría + 6 umbrales + 2 contextuales + 6 fallas) |
| SPNs clave | 10: 100, 98, 175, 110, 190, 168, 521, 84, 520, 247 |
| Instancia | ml.m5.large |
| Feature names | `s3://ado-telemetry-mvp/hackathon-data/modelos/sagemaker-v2/training-data/feature_names.json` |

> **⚠️ IMPORTANTE:** El feature_names.json define el orden exacto de las 54 features que la Lambda `tool-predecir-evento` envía al endpoint. Si reentrenar el modelo cambia las features, hay que actualizar tanto el JSON como la Lambda.

> **Fallback:** Si SageMaker no está disponible, la Lambda `tool-predecir-evento` tiene un fallback heurístico que calcula riesgo basado en umbrales del catálogo SPN. El sistema funciona sin SageMaker, solo con menor precisión.


---

## PASO 11 — Desplegar agentes AgentCore (15 min)

### 11.1 — Prerrequisitos

```bash
# Instalar AgentCore CLI (si no lo tienes)
npm install -g @aws/agentcore-cli

# Verificar
agentcore --version
```

### 11.2 — Actualizar IDs en el código de los agentes

Antes de desplegar, actualizar en ambos `main.py`:

**`agentcore-agents/AdoCombustible/app/AdoCombustible/main.py`:**
- `KNOWLEDGE_BASE_ID = "<NUEVO_KB_ID>"` (del Paso 9)

**`agentcore-agents/AdoMantenimiento/app/AdoMantenimiento/main.py`:**
- `KNOWLEDGE_BASE_ID = "<NUEVO_KB_ID>"` (del Paso 9)

### 11.3 — Actualizar aws-targets.json con la nueva cuenta

**`agentcore-agents/AdoCombustible/agentcore/aws-targets.json`:**
```json
[
  {
    "name": "default",
    "account": "<NUEVA_ACCOUNT_ID>",
    "region": "us-east-2"
  }
]
```

**`agentcore-agents/AdoMantenimiento/agentcore/aws-targets.json`:**
```json
[
  {
    "name": "default",
    "account": "<NUEVA_ACCOUNT_ID>",
    "region": "us-east-2"
  }
]
```

### 11.4 — Desplegar Agente de Combustible

```bash
cd agentcore-agents/AdoCombustible/agentcore

# Instalar dependencias del CDK
cd cdk && npm install && cd ..

# Deploy
agentcore deploy --target default

cd ../../..
```

### 11.5 — Desplegar Agente de Mantenimiento

```bash
cd agentcore-agents/AdoMantenimiento/agentcore

cd cdk && npm install && cd ..

agentcore deploy --target default

cd ../../..
```

### 11.6 — Obtener los ARNs de los agentes desplegados

```bash
# Listar runtimes para obtener los ARNs
aws bedrock-agentcore list-agent-runtimes --region us-east-2

# O revisar el deployed-state.json de cada agente:
cat agentcore-agents/AdoCombustible/agentcore/.cli/deployed-state.json
cat agentcore-agents/AdoMantenimiento/agentcore/.cli/deployed-state.json
```

> **Anota los ARNs** — formato:
> `arn:aws:bedrock-agentcore:us-east-2:<ACCOUNT>:runtime/AdoCombustible_AdoCombustible-XXXXXXX`
> `arn:aws:bedrock-agentcore:us-east-2:<ACCOUNT>:runtime/AdoMantenimiento_AdoMantenimiento-XXXXXXX`

### 11.7 — Actualizar la Lambda ado-chat-api con los nuevos ARNs

```bash
aws lambda update-function-configuration \
  --function-name ado-chat-api \
  --environment "Variables={
    RUNTIME_ARN_COMBUSTIBLE=arn:aws:bedrock-agentcore:us-east-2:${ACCOUNT_ID}:runtime/<NUEVO_ARN_COMBUSTIBLE>,
    RUNTIME_ARN_MANTENIMIENTO=arn:aws:bedrock-agentcore:us-east-2:${ACCOUNT_ID}:runtime/<NUEVO_ARN_MANTENIMIENTO>,
    AWS_REGION_OVERRIDE=us-east-2
  }" \
  --region us-east-2
```

### 11.8 — Verificar que los agentes responden

```bash
# Test rápido del agente de combustible
agentcore invoke AdoCombustible --payload '{"prompt": "¿Qué buses tienen mayor consumo?"}'

# Test rápido del agente de mantenimiento
agentcore invoke AdoMantenimiento --payload '{"prompt": "¿Qué buses tienen riesgo mecánico?"}'
```


---

## PASO 12 — Desplegar frontend React (10 min)

### 12.1 — Actualizar configuración del frontend

Editar `dashboard/.env.local` (crear si no existe):

```bash
cat > dashboard/.env.local << EOF
VITE_API_BASE_URL=https://${API_ID}.execute-api.us-east-2.amazonaws.com
VITE_COGNITO_USER_POOL_ID=${USER_POOL_ID}
VITE_COGNITO_CLIENT_ID=${CLIENT_ID}
VITE_AWS_REGION=us-east-2
EOF
```

> **Nota:** También actualizar los defaults en `dashboard/src/config.ts` si quieres que funcione sin `.env.local`.

### 12.2 — Build del frontend

```bash
cd dashboard
npm install
npx vite build
cd ..
```

### 12.3 — Configurar S3 para hosting estático

```bash
# Habilitar hosting estático
aws s3 website s3://ado-mobilityia-dashboard \
  --index-document index.html \
  --error-document index.html

# Subir el build
aws s3 sync dashboard/dist/ s3://ado-mobilityia-dashboard/ \
  --delete --region us-east-2
```

### 12.4 — Crear distribución CloudFront

```bash
# Crear Origin Access Control
aws cloudfront create-origin-access-control \
  --origin-access-control-config '{
    "Name": "ado-dashboard-oac",
    "Description": "OAC for ADO dashboard",
    "SigningProtocol": "sigv4",
    "SigningBehavior": "always",
    "OriginAccessControlOriginType": "s3"
  }'

# Anota el OAC Id
export OAC_ID="<OAC_ID>"

# Crear distribución CloudFront
cat > /tmp/cf-config.json << EOF
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
      "DomainName": "ado-mobilityia-dashboard.s3.us-east-2.amazonaws.com",
      "S3OriginConfig": {"OriginAccessIdentity": ""},
      "OriginAccessControlId": "${OAC_ID}"
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
EOF

aws cloudfront create-distribution \
  --distribution-config file:///tmp/cf-config.json

# Anota el Distribution ID y el DomainName (ej: d1xxxxx.cloudfront.net)
export CF_DISTRIBUTION_ID="<DISTRIBUTION_ID>"
export CF_DOMAIN="<DOMAIN>.cloudfront.net"
```

### 12.5 — Actualizar bucket policy para CloudFront

```bash
cat > /tmp/bucket-policy.json << EOF
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
EOF

aws s3api put-bucket-policy \
  --bucket ado-mobilityia-dashboard \
  --policy file:///tmp/bucket-policy.json
```

### 12.6 — Actualizar CORS en API Gateway con el nuevo dominio CloudFront

```bash
aws apigatewayv2 update-api \
  --api-id "$API_ID" \
  --cors-configuration "{
    \"AllowOrigins\": [\"http://localhost:3000\", \"https://${CF_DOMAIN}\"],
    \"AllowMethods\": [\"GET\", \"POST\", \"OPTIONS\"],
    \"AllowHeaders\": [\"Content-Type\", \"Authorization\"],
    \"MaxAge\": 86400
  }" \
  --region us-east-2
```


---

## PASO 13 — Verificación end-to-end (10 min)

### 13.1 — Ejecutar el simulador para poblar DynamoDB

```bash
# Invocar el simulador manualmente
aws lambda invoke \
  --function-name ado-simulador-telemetria \
  --payload '{}' \
  --region us-east-2 \
  /tmp/simulador-output.json

cat /tmp/simulador-output.json
# Debe mostrar buses escritos en DynamoDB
```

Ejecutar varias veces (o configurar EventBridge Scheduler) para tener datos:

```bash
# Ejecutar 5 veces con 10 segundos entre cada una
for i in {1..5}; do
  aws lambda invoke --function-name ado-simulador-telemetria --payload '{}' --region us-east-2 /tmp/sim-$i.json
  echo "Iteración $i completada"
  sleep 10
done
```

### 13.2 — Verificar datos en DynamoDB

```bash
aws dynamodb scan \
  --table-name ado-telemetria-live \
  --select COUNT \
  --region us-east-2
# Debe mostrar items > 0
```

### 13.3 — Verificar API Gateway

```bash
# Obtener token de Cognito
TOKEN=$(aws cognito-idp initiate-auth \
  --auth-flow USER_PASSWORD_AUTH \
  --client-id "$CLIENT_ID" \
  --auth-parameters "USERNAME=demo@adomobilityia.com,PASSWORD=DemoADO2026!" \
  --region us-east-2 \
  --query 'AuthenticationResult.IdToken' \
  --output text)

# Test endpoint de flota
curl -H "Authorization: Bearer $TOKEN" \
  "${API_ENDPOINT}/dashboard/flota-status"

# Test endpoint de alertas
curl -H "Authorization: Bearer $TOKEN" \
  "${API_ENDPOINT}/dashboard/alertas-activas"

# Test chat con agente
curl -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "¿Qué buses están activos?", "agente": "combustible"}' \
  "${API_ENDPOINT}/chat"
```

### 13.4 — Verificar frontend

1. Abrir `https://<CF_DOMAIN>` en el navegador
2. Login con `demo@adomobilityia.com` / `DemoADO2026!`
3. Verificar que el mapa muestra buses
4. Verificar que el chat responde

### 13.5 — (Opcional) Configurar EventBridge Scheduler para simulador automático

```bash
# Crear schedule para ejecutar el simulador cada 10 segundos
# Nota: EventBridge Scheduler mínimo es 1 minuto con rate()
# Para 10 segundos, usar 6 schedules con offset de 10s cada una

aws scheduler create-schedule \
  --name ado-simulador-cada-minuto \
  --schedule-expression "rate(1 minute)" \
  --target '{
    "Arn": "arn:aws:lambda:us-east-2:'${ACCOUNT_ID}':function:ado-simulador-telemetria",
    "RoleArn": "'${ROLE_ARN}'"
  }' \
  --flexible-time-window '{"Mode": "OFF"}' \
  --region us-east-2
```

---

## 📝 Resumen de IDs que cambian entre cuentas

Después de completar todos los pasos, estos son los valores que debes actualizar en el código:

| Archivo | Variable | Valor anterior | Nuevo valor |
|---------|----------|---------------|-------------|
| `agentcore-agents/*/agentcore/aws-targets.json` | `account` | `084032333314` | `<NUEVA_ACCOUNT>` |
| `agentcore-agents/*/app/*/main.py` | `KNOWLEDGE_BASE_ID` | `4OAVLRB8VI` | `<NUEVO_KB_ID>` |
| `lambda-functions/ado-chat-api/lambda_function.py` | `RUNTIME_ARN_COMBUSTIBLE` | `...BJ7Uvb4ozE` | `<NUEVO_ARN>` |
| `lambda-functions/ado-chat-api/lambda_function.py` | `RUNTIME_ARN_MANTENIMIENTO` | `...2sL9qkC3yK` | `<NUEVO_ARN>` |
| `dashboard/.env.local` | `VITE_API_BASE_URL` | `https://sutgpijmoh...` | `<NUEVO_API_ENDPOINT>` |
| `dashboard/.env.local` | `VITE_COGNITO_USER_POOL_ID` | `us-east-2_5itNQjtYP` | `<NUEVO_POOL_ID>` |
| `dashboard/.env.local` | `VITE_COGNITO_CLIENT_ID` | `7f05s6kerku5ejb58odjj4b1fl` | `<NUEVO_CLIENT_ID>` |
| `dashboard/src/config.ts` | defaults hardcodeados | valores anteriores | `<NUEVOS_VALORES>` |

---

## ⚡ Orden de dependencias (diagrama)

```
S3 Buckets ──────────────────────────────────────────────────┐
  │                                                          │
  ├── Datos simulados (Parquets, JSONs)                      │
  │     │                                                    │
  │     ├── SageMaker (entrenamiento + endpoint) ────────┐   │
  │     │                                                │   │
  │     └── Knowledge Base docs ──── Bedrock KB ─────┐   │   │
  │                                                  │   │   │
  ├── DynamoDB (2 tablas) ───────────────────────┐   │   │   │
  │                                              │   │   │   │
  ├── IAM Role ──── Lambda Layer ──── Lambdas ───┤   │   │   │
  │                                    │         │   │   │   │
  │                                    │         │   │   │   │
  ├── Cognito ──── API Gateway ────────┘         │   │   │   │
  │                    │                         │   │   │   │
  │                    │     AgentCore Agents ────┘───┘───┘   │
  │                    │         │                            │
  │                    │         └── Actualizar Chat Lambda   │
  │                    │                                      │
  └── Frontend (build) ── S3 hosting ── CloudFront ──────────┘
```

---

## 🔥 Checklist rápido post-recuperación

- [ ] S3: 3 buckets creados y con datos
- [ ] DynamoDB: 2 tablas creadas con GSI y TTL
- [ ] IAM: Rol con permisos para DynamoDB, S3, SageMaker, AgentCore, Lambda
- [ ] Lambda Layer: `ado-common-layer` publicado
- [ ] Lambdas: 10 funciones + 1 chat API desplegadas
- [ ] Cognito: User Pool + App Client + usuario demo
- [ ] API Gateway: HTTP API con JWT authorizer y 5 rutas
- [ ] Knowledge Base: Creada y sincronizada con 5 documentos
- [ ] SageMaker: Endpoint `ado-prediccion-eventos` InService
- [ ] AgentCore: 2 agentes desplegados y respondiendo
- [ ] Chat Lambda: ARNs de agentes actualizados
- [ ] Frontend: Build con nuevos IDs, subido a S3
- [ ] CloudFront: Distribución creada, bucket policy configurada
- [ ] CORS: API Gateway permite el dominio de CloudFront
- [ ] Simulador: Ejecutado al menos 5 veces para poblar DynamoDB
- [ ] Test E2E: Login → Mapa → Chat → Respuesta del agente ✅

---

## 💾 Qué hacer AHORA para facilitar la recuperación futura

1. **Hacer backup de los Parquets** — Son ~460 MB y son la fuente de todo. Sin ellos no hay modelo ML ni simulador. Guardarlos fuera de AWS (Google Drive, disco local, otro cloud).

2. **Exportar el modelo SageMaker** — El `model.tar.gz` ya está en S3. Descargarlo:
   ```bash
   aws s3 cp s3://ado-telemetry-mvp/hackathon-data/modelos/sagemaker/output/model.tar.gz ./backup/
   aws s3 cp s3://ado-telemetry-mvp/hackathon-data/modelos/sagemaker-v2/training-data/feature_names.json ./backup/
   ```

3. **Guardar el `viajes_consolidados.json`** (~12 MB) — Es lo que el simulador lee:
   ```bash
   aws s3 cp s3://ado-telemetry-mvp/hackathon-data/simulacion/viajes_consolidados.json ./backup/
   ```

4. **Commit todo al repo Git** — El código de Lambdas, agentes, frontend, manuales, y este runbook.

5. **Documentar los IDs actuales** — Ya están en `docs/aws-resources.md`, mantenerlo actualizado.
