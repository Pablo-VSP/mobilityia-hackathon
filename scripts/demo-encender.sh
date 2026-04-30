#!/usr/bin/env bash
# =============================================================================
# 🟢 ADO MobilityIA — Encender todo para la demo
# =============================================================================
# Ejecutar ~15 minutos ANTES de la presentación.
# Levanta: SageMaker endpoint, EventBridge simulador, Knowledge Base.
#
# USO:
#   ./scripts/demo-encender.sh
#
# COSTOS mientras esté encendido:
#   SageMaker ml.m5.large  ~$0.13/hora
#   OpenSearch Serverless   ~$0.48/hora (2 OCUs mínimo)
#   EventBridge + Lambda    ~$0.001/hora
#   TOTAL                   ~$0.61/hora ≈ $14.64/día
# =============================================================================

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

REGION="us-east-2"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text --region $REGION)

echo -e "${GREEN}🟢 Encendiendo ADO MobilityIA para la demo...${NC}"
echo -e "   Cuenta: ${ACCOUNT_ID} | Región: ${REGION}"
echo ""

# ─────────────────────────────────────────────────────────────────────────────
# 1. SageMaker Endpoint (~5-8 min para InService)
# ─────────────────────────────────────────────────────────────────────────────
echo -e "${BLUE}[1/3] SageMaker Endpoint...${NC}"

SM_STATUS=$(aws sagemaker describe-endpoint --endpoint-name ado-prediccion-eventos \
  --region $REGION --query EndpointStatus --output text 2>/dev/null || echo "NOT_FOUND")

if [ "$SM_STATUS" = "InService" ]; then
  echo -e "  ${GREEN}✅ Ya está InService${NC}"
elif [ "$SM_STATUS" = "Creating" ]; then
  echo -e "  ${YELLOW}⏳ Ya está creándose — espera unos minutos${NC}"
else
  # Verificar que la endpoint config existe
  aws sagemaker describe-endpoint-config --endpoint-config-name ado-prediccion-eventos \
    --region $REGION > /dev/null 2>&1 || {
    echo -e "  ${RED}❌ No existe endpoint config 'ado-prediccion-eventos'${NC}"
    echo -e "  ${RED}   Necesitas re-entrenar el modelo. Ver docs/sagemaker-modelo-predictivo-plan.md${NC}"
    echo -e "  ${YELLOW}   El sistema funciona sin SageMaker (fallback heurístico)${NC}"
    SM_STATUS="SKIP"
  }

  if [ "$SM_STATUS" != "SKIP" ]; then
    aws sagemaker create-endpoint \
      --endpoint-name ado-prediccion-eventos \
      --endpoint-config-name ado-prediccion-eventos \
      --region $REGION > /dev/null
    echo -e "  ${GREEN}✅ Endpoint creándose (~5-8 min para InService)${NC}"
  fi
fi

# ─────────────────────────────────────────────────────────────────────────────
# 2. Knowledge Base + OpenSearch Serverless (~5-10 min)
# ─────────────────────────────────────────────────────────────────────────────
echo -e "${BLUE}[2/3] Knowledge Base...${NC}"

EXISTING_KB=$(aws bedrock-agent list-knowledge-bases --region $REGION \
  --query "knowledgeBaseSummaries[?status=='ACTIVE'].knowledgeBaseId" --output text 2>/dev/null || echo "")

if [ -n "$EXISTING_KB" ] && [ "$EXISTING_KB" != "None" ]; then
  echo -e "  ${GREEN}✅ KB ya activa: ${EXISTING_KB}${NC}"
  KB_ID="$EXISTING_KB"
else
  echo -e "  ${YELLOW}⚠️  No hay Knowledge Base activa.${NC}"
  echo ""
  echo -e "  ${YELLOW}Créala desde la consola de Bedrock (5 min):${NC}"
  echo -e "  1. Amazon Bedrock > Knowledge Bases > Create"
  echo -e "  2. Nombre: ${BLUE}ado-mobilityia-kb${NC}"
  echo -e "  3. Rol: ${BLUE}AmazonBedrockExecutionRoleForKnowledgeBase_f6leu${NC}"
  echo -e "  4. Data source: S3 → ${BLUE}s3://ado-telemetry-mvp/hackathon-data/knowledge-base/docs/${NC}"
  echo -e "  5. Embedding: ${BLUE}Titan Text Embeddings v2${NC}"
  echo -e "  6. Vector store: ${BLUE}Quick create (OpenSearch Serverless)${NC}"
  echo -e "  7. Create → Sync"
  echo ""
  read -p "  Ingresa el nuevo Knowledge Base ID (o ENTER para saltar): " KB_ID

  if [ -n "$KB_ID" ]; then
    echo -e "  ${GREEN}✅ KB ID: ${KB_ID}${NC}"
  else
    KB_ID=""
    echo -e "  ${YELLOW}⚠️  Sin KB — los agentes funcionan pero sin RAG${NC}"
  fi
fi

# Actualizar KB ID en los agentes si cambió
if [ -n "$KB_ID" ]; then
  PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
  for AGENT in AdoCombustible AdoMantenimiento; do
    MAIN_PY="${PROJECT_ROOT}/agentcore-agents/${AGENT}/app/${AGENT}/main.py"
    if [ -f "$MAIN_PY" ]; then
      CURRENT_KB=$(grep 'KNOWLEDGE_BASE_ID' "$MAIN_PY" | head -1 | sed 's/.*"\(.*\)".*/\1/')
      if [ "$CURRENT_KB" != "$KB_ID" ]; then
        sed -i.bak "s/KNOWLEDGE_BASE_ID = \"[^\"]*\"/KNOWLEDGE_BASE_ID = \"${KB_ID}\"/" "$MAIN_PY"
        rm -f "${MAIN_PY}.bak"
        echo -e "  ${GREEN}✅ KB ID actualizado en ${AGENT}/main.py${NC}"
        echo -e "  ${YELLOW}⚠️  Necesitas re-desplegar el agente:${NC}"
        echo -e "     cd agentcore-agents/${AGENT}/agentcore && agentcore deploy --target default"
      fi
    fi
  done
fi

# ─────────────────────────────────────────────────────────────────────────────
# 3. EventBridge Scheduler (simulador)
# ─────────────────────────────────────────────────────────────────────────────
echo -e "${BLUE}[3/3] Simulador de telemetría...${NC}"

SCHED_EXISTS=$(aws scheduler get-schedule --name ado-simulador-demo \
  --region $REGION --query State --output text 2>/dev/null || echo "NOT_FOUND")

if [ "$SCHED_EXISTS" = "ENABLED" ]; then
  echo -e "  ${GREEN}✅ Simulador ya está corriendo${NC}"
elif [ "$SCHED_EXISTS" = "DISABLED" ]; then
  # Obtener datos del schedule existente para re-habilitarlo
  SCHED_JSON=$(aws scheduler get-schedule --name ado-simulador-demo --region $REGION 2>/dev/null)
  TARGET_ARN=$(echo "$SCHED_JSON" | python3 -c "import sys,json; print(json.load(sys.stdin)['Target']['Arn'])")
  ROLE_ARN=$(echo "$SCHED_JSON" | python3 -c "import sys,json; print(json.load(sys.stdin)['Target']['RoleArn'])")

  aws scheduler update-schedule \
    --name ado-simulador-demo \
    --state ENABLED \
    --schedule-expression "rate(1 minutes)" \
    --flexible-time-window '{"Mode":"OFF"}' \
    --target "{\"Arn\":\"${TARGET_ARN}\",\"RoleArn\":\"${ROLE_ARN}\"}" \
    --region $REGION > /dev/null
  echo -e "  ${GREEN}✅ Simulador re-habilitado${NC}"
else
  # Crear desde cero
  aws scheduler create-schedule \
    --name ado-simulador-demo \
    --schedule-expression "rate(1 minutes)" \
    --state ENABLED \
    --flexible-time-window '{"Mode":"OFF"}' \
    --target "{\"Arn\":\"arn:aws:lambda:${REGION}:${ACCOUNT_ID}:function:ado-simulador-telemetria\",\"RoleArn\":\"arn:aws:iam::${ACCOUNT_ID}:role/ado-scheduler-role\"}" \
    --region $REGION > /dev/null
  echo -e "  ${GREEN}✅ Simulador creado y corriendo${NC}"
fi

# Invocar simulador 3 veces para tener datos inmediatos
echo -e "  ${BLUE}Poblando DynamoDB con datos iniciales...${NC}"
for i in 1 2 3; do
  aws lambda invoke --function-name ado-simulador-telemetria \
    --payload '{}' --region $REGION /tmp/sim-demo-$i.json > /dev/null 2>&1
  sleep 3
done
echo -e "  ${GREEN}✅ 3 ciclos de simulación ejecutados${NC}"

# ─────────────────────────────────────────────────────────────────────────────
# Esperar SageMaker si está creándose
# ─────────────────────────────────────────────────────────────────────────────
SM_STATUS=$(aws sagemaker describe-endpoint --endpoint-name ado-prediccion-eventos \
  --region $REGION --query EndpointStatus --output text 2>/dev/null || echo "NOT_FOUND")

if [ "$SM_STATUS" = "Creating" ]; then
  echo ""
  echo -e "${YELLOW}⏳ Esperando SageMaker endpoint (puede tardar ~5 min)...${NC}"
  aws sagemaker wait endpoint-in-service \
    --endpoint-name ado-prediccion-eventos --region $REGION 2>/dev/null && \
    echo -e "${GREEN}✅ SageMaker InService${NC}" || \
    echo -e "${YELLOW}⚠️  Timeout esperando SageMaker — verificar manualmente${NC}"
fi

# ─────────────────────────────────────────────────────────────────────────────
# Resumen
# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}  🟢 SISTEMA ENCENDIDO — Listo para la demo${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "  Dashboard:  ${BLUE}https://d1zr7g3ygmf5pk.cloudfront.net${NC}"
echo -e "  Login:      ${BLUE}demo@adomobilityia.com / DemoADO2026!${NC}"
echo ""
echo -e "  ${YELLOW}⚠️  Recuerda apagar al terminar: ./scripts/demo-apagar.sh${NC}"
echo -e "  ${YELLOW}    Costo mientras esté encendido: ~\$0.61/hora${NC}"
echo ""
