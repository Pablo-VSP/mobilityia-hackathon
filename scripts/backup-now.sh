#!/usr/bin/env bash
# =============================================================================
# 💾 ADO MobilityIA — Backup de datos críticos desde AWS
# =============================================================================
# Descarga todo lo que NO está en el repo Git y que se necesita para restaurar.
# Ejecutar ANTES de que borren la cuenta.
#
# USO:
#   chmod +x scripts/backup-now.sh
#   ./scripts/backup-now.sh
# =============================================================================

set -euo pipefail

REGION="us-east-2"
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BACKUP_DIR="${PROJECT_ROOT}/backup"

echo "💾 Creando backup en ${BACKUP_DIR}..."
mkdir -p "${BACKUP_DIR}/raw/travel_telemetry"
mkdir -p "${BACKUP_DIR}/raw/data_fault"
mkdir -p "${BACKUP_DIR}/raw/motor_spn"

# 1. Viajes consolidados (CRÍTICO — sin esto el simulador no funciona)
echo ">>> Descargando viajes_consolidados.json (~12 MB)..."
aws s3 cp "s3://ado-telemetry-mvp/hackathon-data/simulacion/viajes_consolidados.json" \
  "${BACKUP_DIR}/viajes_consolidados.json" --region $REGION

# 2. Modelo ML entrenado (ahorra 45 min de re-entrenamiento)
echo ">>> Descargando modelo SageMaker..."
aws s3 cp "s3://ado-telemetry-mvp/hackathon-data/modelos/sagemaker/output/model.tar.gz" \
  "${BACKUP_DIR}/model.tar.gz" --region $REGION 2>/dev/null || \
  echo "⚠️  model.tar.gz no encontrado en ruta original"

aws s3 cp "s3://ado-telemetry-mvp/hackathon-data/modelos/sagemaker-v2/training-data/feature_names.json" \
  "${BACKUP_DIR}/feature_names.json" --region $REGION 2>/dev/null || \
  echo "⚠️  feature_names.json no encontrado"

# 3. Parquets raw (GRANDE — ~460 MB, pero necesario para re-entrenar ML)
echo ">>> Descargando Parquets de telemetría (~447 MB, puede tardar)..."
aws s3 sync "s3://ado-telemetry-mvp/hackathon-data/raw/travel_telemetry/" \
  "${BACKUP_DIR}/raw/travel_telemetry/" --region $REGION

echo ">>> Descargando Parquets de fallas (~6.5 MB)..."
aws s3 sync "s3://ado-telemetry-mvp/hackathon-data/raw/data_fault/" \
  "${BACKUP_DIR}/raw/data_fault/" --region $REGION

echo ">>> Descargando Parquet de catálogo SPN..."
aws s3 sync "s3://ado-telemetry-mvp/hackathon-data/raw/motor_spn/" \
  "${BACKUP_DIR}/raw/motor_spn/" --region $REGION

# 4. Training data de SageMaker
echo ">>> Descargando datos de entrenamiento..."
mkdir -p "${BACKUP_DIR}/sagemaker-training"
aws s3 sync "s3://ado-telemetry-mvp/hackathon-data/modelos/" \
  "${BACKUP_DIR}/sagemaker-training/" --region $REGION 2>/dev/null || true

# Resumen
echo ""
echo "✅ Backup completado en: ${BACKUP_DIR}"
echo ""
echo "Contenido:"
du -sh "${BACKUP_DIR}"/* 2>/dev/null || true
echo ""
echo "⚠️  IMPORTANTE: Agrega backup/ a .gitignore si no quieres commitear ~460 MB"
echo "   O súbelo a Google Drive / disco externo como respaldo adicional."
