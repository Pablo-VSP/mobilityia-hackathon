#!/usr/bin/env bash
# =============================================================================
# 🔴 ADO MobilityIA — Apagar todo después de la demo
# =============================================================================
# Ejecutar al terminar la presentación para dejar de generar costos.
# Elimina los 3 recursos que cobran por hora:
#   - SageMaker Endpoint (~$0.13/h)
#   - OpenSearch Serverless (~$0.48/h)
#   - EventBridge Scheduler (invoca Lambda cada minuto)
#
# TODO lo demás (Lambdas, DynamoDB, S3, API Gateway, Cognito, CloudFront,
# AgentCore) NO genera costo mientras no se use.
#
# USO:
#   ./scripts/demo-apagar.sh
# =============================================================================

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

REGION="us-east-2"

echo -e "${RED}🔴 Apagando recursos costosos de ADO MobilityIA...${NC}"
echo ""

# ─────────────────────────────────────────────────────────────────────────────
# 1. SageMaker Endpoint
# ─────────────────────────────────────────────────────────────────────────────
echo -e "${BLUE}[1/3] SageMaker Endpoint...${NC}"

SM_STATUS=$(aws sagemaker describe-endpoint --endpoint-name ado-prediccion-eventos \
  --region $REGION --query EndpointStatus --output text 2>/dev/null || echo "NOT_FOUND")

if [ "$SM_STATUS" = "NOT_FOUND" ]; then
  echo -e "  ${GREEN}✅ Ya está apagado${NC}"
else
  aws sagemaker delete-endpoint --endpoint-name ado-prediccion-eventos --region $REGION
  echo -e "  ${GREEN}✅ Endpoint eliminado (ahorro: ~\$0.13/hora)${NC}"
  echo -e "  ${BLUE}ℹ️  El modelo y la config siguen en AWS — se recrea con demo-encender.sh${NC}"
fi

# ─────────────────────────────────────────────────────────────────────────────
# 2. OpenSearch Serverless (Knowledge Base vector store)
# ─────────────────────────────────────────────────────────────────────────────
echo -e "${BLUE}[2/3] OpenSearch Serverless...${NC}"

# Listar colecciones
COLLECTIONS=$(aws opensearchserverless list-collections --region $REGION \
  --query 'collectionSummaries[].{id:id,name:name}' --output json 2>/dev/null || echo "[]")

COLLECTION_COUNT=$(echo "$COLLECTIONS" | python3 -c "import sys,json; print(len(json.load(sys.stdin)))")

if [ "$COLLECTION_COUNT" = "0" ]; then
  echo -e "  ${GREEN}✅ No hay colecciones OpenSearch activas${NC}"
else
  # Eliminar cada colección
  echo "$COLLECTIONS" | python3 -c "
import sys, json
for c in json.load(sys.stdin):
    print(c['id'])
" | while read -r COL_ID; do
    aws opensearchserverless delete-collection --id "$COL_ID" --region $REGION > /dev/null 2>&1
    echo -e "  ${GREEN}✅ Colección ${COL_ID} eliminándose (ahorro: ~\$0.48/hora)${NC}"
  done

  # También eliminar la KB asociada (queda huérfana sin el vector store)
  KB_LIST=$(aws bedrock-agent list-knowledge-bases --region $REGION \
    --query "knowledgeBaseSummaries[?status=='ACTIVE'].knowledgeBaseId" --output text 2>/dev/null || echo "")

  if [ -n "$KB_LIST" ] && [ "$KB_LIST" != "None" ]; then
    for KB_ID in $KB_LIST; do
      # Eliminar data sources primero
      DS_LIST=$(aws bedrock-agent list-data-sources --knowledge-base-id "$KB_ID" --region $REGION \
        --query "dataSourceSummaries[].dataSourceId" --output text 2>/dev/null || echo "")
      for DS_ID in $DS_LIST; do
        aws bedrock-agent delete-data-source --knowledge-base-id "$KB_ID" \
          --data-source-id "$DS_ID" --region $REGION > /dev/null 2>&1 || true
      done
      aws bedrock-agent delete-knowledge-base --knowledge-base-id "$KB_ID" \
        --region $REGION > /dev/null 2>&1 || true
      echo -e "  ${GREEN}✅ Knowledge Base ${KB_ID} eliminada${NC}"
    done
  fi
fi

# ─────────────────────────────────────────────────────────────────────────────
# 3. EventBridge Scheduler
# ─────────────────────────────────────────────────────────────────────────────
echo -e "${BLUE}[3/3] Simulador EventBridge...${NC}"

SCHED_EXISTS=$(aws scheduler get-schedule --name ado-simulador-demo \
  --region $REGION 2>/dev/null && echo "YES" || echo "NO")

if [ "$SCHED_EXISTS" = "NO" ]; then
  echo -e "  ${GREEN}✅ Ya está apagado${NC}"
else
  aws scheduler delete-schedule --name ado-simulador-demo --region $REGION
  echo -e "  ${GREEN}✅ Simulador eliminado${NC}"
fi

# ─────────────────────────────────────────────────────────────────────────────
# Resumen
# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}  🔴 SISTEMA APAGADO — Costo recurrente: ~\$0/hora${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "  Lo que sigue activo (sin costo mientras no se use):"
echo -e "    • Lambdas (11 funciones)"
echo -e "    • DynamoDB (2 tablas, pay-per-request)"
echo -e "    • API Gateway + Cognito"
echo -e "    • S3 (3 buckets, ~\$0.01/día)"
echo -e "    • CloudFront"
echo -e "    • AgentCore (2 agentes)"
echo ""
echo -e "  ${BLUE}Para re-encender: ./scripts/demo-encender.sh${NC}"
echo ""
