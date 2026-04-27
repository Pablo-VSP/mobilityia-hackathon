"""
ADO MobilityIA — Feature Engineering + Entrenamiento + Deploy
Hackathon AWS Builders League 2026

Ejecutar en SageMaker Studio (us-east-2) con kernel Python 3 (Data Science 3.0)
Instance recomendada: ml.m5.xlarge

Este script:
1. Lee telemetría y fallas desde S3 (Parquet)
2. Filtra solo fallas críticas (severidad_inferencia = 3): códigos 100, 158, 86
3. Genera features por (autobus, fecha_corte) con ventana de 7 días
4. Entrena XGBoost para clasificación binaria
5. Despliega endpoint 'ado-prediccion-eventos'
"""

import pandas as pd
import numpy as np
import boto3
import json
import os
from datetime import timedelta
from collections import defaultdict

# ============================================================
# CONFIGURACIÓN
# ============================================================
BUCKET = "ado-telemetry-mvp"
PREFIX_TELEMETRY = "hackathon-data/raw/travel_telemetry/"
PREFIX_FAULTS = "hackathon-data/raw/data_fault/"
PREFIX_SPN = "hackathon-data/raw/motor_spn/"
REGION = "us-east-2"

# Códigos de falla con severidad_inferencia = 3 (C-007)
CODIGOS_CRITICOS = {"100", "158", "86"}

# Códigos de falla con severidad_inferencia = 2 (señales de escalamiento)
CODIGOS_ESCALAMIENTO = {"111", "32", "131", "37"}

# SPNs de mantenimiento (19 confirmados)
SPNS_MANTENIMIENTO = {
    110, 175, 100, 98, 111, 168, 1761, 520, 917, 247,
    190, 171, 521, 1099, 1100, 1101, 1102, 1103, 1104
}

VENTANA_DIAS = 7
HORIZONTE_PREDICCION = 14

print("=" * 60)
print("ADO MobilityIA — Modelo Predictivo de Fallas Críticas")
print("=" * 60)

# ============================================================
# PASO 1: CARGAR DATOS DESDE S3
# ============================================================
print("\n[1/7] Cargando datos desde S3...")

telemetria = pd.read_parquet(f"s3://{BUCKET}/{PREFIX_TELEMETRY}")
print(f"  Telemetría: {len(telemetria):,} registros")

fallas = pd.read_parquet(f"s3://{BUCKET}/{PREFIX_FAULTS}")
print(f"  Fallas: {len(fallas):,} registros")

catalogo = pd.read_parquet(f"s3://{BUCKET}/{PREFIX_SPN}")
print(f"  Catálogo SPN: {len(catalogo)} variables")

# Indexar catálogo por SPN ID
catalogo_dict = {}
for _, row in catalogo.iterrows():
    spn_id = int(row["id"])
    catalogo_dict[spn_id] = {
        "name": str(row.get("name", "")).strip(),
        "minimo": float(row.get("minimo", 0)),
        "maximo": float(row.get("maximo", 0)),
        "delta": float(row.get("delta", 0)),
    }

print(f"  Catálogo indexado: {len(catalogo_dict)} SPNs")

# ============================================================
# PASO 2: EXPLORAR Y LIMPIAR DATOS
# ============================================================
print("\n[2/7] Explorando y limpiando datos...")

# Convertir tipos
telemetria["autobus"] = telemetria["autobus"].astype(str)
telemetria["evento_spn"] = telemetria["evento_spn"].astype(int)
telemetria["evento_valor"] = pd.to_numeric(telemetria["evento_valor"], errors="coerce")

# Parsear fechas de telemetría
if "evento_fecha" in telemetria.columns:
    telemetria["evento_fecha"] = pd.to_datetime(telemetria["evento_fecha"], errors="coerce")
if "evento_fecha_hora" in telemetria.columns:
    telemetria["evento_fecha_hora"] = pd.to_datetime(telemetria["evento_fecha_hora"], errors="coerce")
    if telemetria["evento_fecha"].isna().all():
        telemetria["evento_fecha"] = telemetria["evento_fecha_hora"].dt.date

# Limpiar fallas
fallas["autobus"] = fallas["autobus"].astype(str)
fallas["codigo"] = fallas["codigo"].astype(str).str.strip()
if "fecha_hora" in fallas.columns:
    fallas["fecha_hora"] = pd.to_datetime(fallas["fecha_hora"], errors="coerce")

# Filtrar telemetría vacía
telemetria = telemetria.dropna(subset=["evento_valor", "evento_spn"])

# Filtrar solo SPNs de mantenimiento
tel_mant = telemetria[telemetria["evento_spn"].isin(SPNS_MANTENIMIENTO)].copy()

print(f"  Telemetría de mantenimiento: {len(tel_mant):,} registros")
print(f"  Buses únicos en telemetría: {tel_mant['autobus'].nunique()}")
print(f"  Buses únicos en fallas: {fallas['autobus'].nunique()}")
print(f"  Rango de fechas telemetría: {tel_mant['evento_fecha'].min()} a {tel_mant['evento_fecha'].max()}")
print(f"  Rango de fechas fallas: {fallas['fecha_hora'].min()} a {fallas['fecha_hora'].max()}")

# Estadísticas de fallas por código
print("\n  Distribución de fallas por código:")
for codigo in sorted(CODIGOS_CRITICOS | CODIGOS_ESCALAMIENTO):
    count = len(fallas[fallas["codigo"] == codigo])
    sev = "SEV3" if codigo in CODIGOS_CRITICOS else "SEV2"
    print(f"    Código {codigo} ({sev}): {count:,} ocurrencias")

# ============================================================
# PASO 3: FEATURE ENGINEERING
# ============================================================
print("\n[3/7] Generando features por (autobus, fecha_corte)...")

# Obtener lista de buses que tienen tanto telemetría como fallas
buses_telemetria = set(tel_mant["autobus"].unique())
buses_fallas = set(fallas["autobus"].unique())
buses_comunes = buses_telemetria & buses_fallas
print(f"  Buses con telemetría Y fallas: {len(buses_comunes)}")

# Si no hay buses comunes, usar todos los de telemetría
if len(buses_comunes) == 0:
    print("  WARN: No hay buses comunes. Usando todos los buses de telemetría.")
    buses_target = buses_telemetria
else:
    buses_target = buses_comunes

# Generar fechas de corte
tel_mant["evento_fecha_dt"] = pd.to_datetime(tel_mant["evento_fecha"])
fecha_min = tel_mant["evento_fecha_dt"].min() + timedelta(days=VENTANA_DIAS)
fecha_max = tel_mant["evento_fecha_dt"].max() - timedelta(days=HORIZONTE_PREDICCION)

if fecha_min >= fecha_max:
    print("  WARN: Rango de fechas insuficiente. Ajustando...")
    fecha_min = tel_mant["evento_fecha_dt"].min() + timedelta(days=3)
    fecha_max = tel_mant["evento_fecha_dt"].max() - timedelta(days=7)

fechas_corte = pd.date_range(fecha_min, fecha_max, freq="7D")  # Una muestra cada 7 días
print(f"  Fechas de corte: {len(fechas_corte)} (de {fecha_min.date()} a {fecha_max.date()})")


def calcular_features_spn(registros_ventana, catalogo_dict):
    """Calcula features agregadas por SPN sobre una ventana de registros."""
    features = {}
    
    for spn_id in SPNS_MANTENIMIENTO:
        spn_data = registros_ventana[registros_ventana["evento_spn"] == spn_id]["evento_valor"]
        prefix = f"spn_{spn_id}"
        
        if len(spn_data) == 0:
            features[f"{prefix}_avg_7d"] = np.nan
            features[f"{prefix}_max_7d"] = np.nan
            features[f"{prefix}_min_7d"] = np.nan
            features[f"{prefix}_std_7d"] = np.nan
            features[f"{prefix}_oor_count_7d"] = 0
            features[f"{prefix}_anomaly_count_7d"] = 0
            continue
        
        features[f"{prefix}_avg_7d"] = spn_data.mean()
        features[f"{prefix}_max_7d"] = spn_data.max()
        features[f"{prefix}_min_7d"] = spn_data.min()
        features[f"{prefix}_std_7d"] = spn_data.std() if len(spn_data) > 1 else 0
        
        # Fuera de rango (vs catálogo)
        oor_count = 0
        cat = catalogo_dict.get(spn_id)
        if cat:
            oor_count = ((spn_data < cat["minimo"]) | (spn_data > cat["maximo"])).sum()
        features[f"{prefix}_oor_count_7d"] = int(oor_count)
        
        # Variaciones anómalas (> 2× delta)
        anomaly_count = 0
        if cat and cat["delta"] > 0 and len(spn_data) > 1:
            diffs = spn_data.diff().abs()
            anomaly_count = (diffs > cat["delta"] * 2).sum()
        features[f"{prefix}_anomaly_count_7d"] = int(anomaly_count)
    
    return features


def calcular_features_fallas(bus_id, fecha_corte, fallas_df):
    """Calcula features de historial de fallas para un bus a una fecha."""
    fallas_bus = fallas_df[fallas_df["autobus"] == bus_id].copy()
    
    if len(fallas_bus) == 0:
        return {
            "fallas_criticas_30d": 0,
            "fallas_criticas_90d": 0,
            "fallas_sev2_30d": 0,
            "fallas_sev2_recurrentes_30d": 0,
            "severidad_max_30d": 0,
            "dias_desde_ultima_falla_critica": 999,
            "tiene_falla_activa": 0,
            "codigos_criticos_unicos_90d": 0,
            "fallas_correlacionadas": 0,
        }
    
    fecha_30d = fecha_corte - timedelta(days=30)
    fecha_90d = fecha_corte - timedelta(days=90)
    
    fallas_30d = fallas_bus[
        (fallas_bus["fecha_hora"] >= fecha_30d) & (fallas_bus["fecha_hora"] < fecha_corte)
    ]
    fallas_90d = fallas_bus[
        (fallas_bus["fecha_hora"] >= fecha_90d) & (fallas_bus["fecha_hora"] < fecha_corte)
    ]
    
    # Fallas críticas (sev3)
    criticas_30d = fallas_30d[fallas_30d["codigo"].isin(CODIGOS_CRITICOS)]
    criticas_90d = fallas_90d[fallas_90d["codigo"].isin(CODIGOS_CRITICOS)]
    
    # Fallas de escalamiento (sev2)
    sev2_30d = fallas_30d[fallas_30d["codigo"].isin(CODIGOS_ESCALAMIENTO)]
    
    # Regla de escalamiento: sev2 que se repite >3 veces en 30 días
    sev2_recurrente = 0
    if len(sev2_30d) > 0:
        sev2_counts = sev2_30d["codigo"].value_counts()
        sev2_recurrente = int((sev2_counts > 3).any())
    
    # Días desde última falla crítica
    fallas_criticas_previas = fallas_bus[
        (fallas_bus["fecha_hora"] < fecha_corte) & (fallas_bus["codigo"].isin(CODIGOS_CRITICOS))
    ]
    if len(fallas_criticas_previas) > 0:
        dias_desde = (fecha_corte - fallas_criticas_previas["fecha_hora"].max()).days
    else:
        dias_desde = 999
    
    # Severidad máxima
    sev_max = 0
    if "severidad" in fallas_30d.columns and len(fallas_30d) > 0:
        sev_max = fallas_30d["severidad"].max()
    
    # Correlaciones de fallas (del manual)
    codigos_activos = set(fallas_30d["codigo"].unique())
    correlacionadas = 0
    if "100" in codigos_activos and ("158" in codigos_activos or "86" in codigos_activos):
        correlacionadas = 1
    
    return {
        "fallas_criticas_30d": len(criticas_30d),
        "fallas_criticas_90d": len(criticas_90d),
        "fallas_sev2_30d": len(sev2_30d),
        "fallas_sev2_recurrentes_30d": sev2_recurrente,
        "severidad_max_30d": int(sev_max) if not pd.isna(sev_max) else 0,
        "dias_desde_ultima_falla_critica": min(dias_desde, 999),
        "tiene_falla_activa": int(len(criticas_30d) > 0),
        "codigos_criticos_unicos_90d": criticas_90d["codigo"].nunique(),
        "fallas_correlacionadas": correlacionadas,
    }


def calcular_features_contextuales(registros_ventana):
    """Features contextuales del manual de mantenimiento."""
    features = {}
    
    # Balata mínima
    balata_spns = [1099, 1100, 1101, 1102, 1103, 1104]
    balata_vals = []
    for spn in balata_spns:
        vals = registros_ventana[registros_ventana["evento_spn"] == spn]["evento_valor"]
        if len(vals) > 0:
            balata_vals.append(vals.min())
    features["balata_min_pct"] = min(balata_vals) if balata_vals else np.nan
    
    # Odómetro y horas motor (último valor)
    for spn_id, name in [(917, "odometro_km"), (247, "horas_motor_h")]:
        vals = registros_ventana[registros_ventana["evento_spn"] == spn_id]["evento_valor"]
        features[name] = vals.iloc[-1] if len(vals) > 0 else np.nan
    
    # Total SPNs fuera de rango
    total_oor = 0
    total_anomalies = 0
    for spn_id in SPNS_MANTENIMIENTO:
        spn_data = registros_ventana[registros_ventana["evento_spn"] == spn_id]["evento_valor"]
        cat = catalogo_dict.get(spn_id)
        if cat and len(spn_data) > 0:
            total_oor += ((spn_data < cat["minimo"]) | (spn_data > cat["maximo"])).sum()
            if cat["delta"] > 0 and len(spn_data) > 1:
                diffs = spn_data.diff().abs()
                total_anomalies += (diffs > cat["delta"] * 2).sum()
    
    features["total_spns_fuera_rango"] = int(total_oor)
    features["total_anomalias"] = int(total_anomalies)
    
    return features


def calcular_target(bus_id, fecha_corte, fallas_df):
    """Target: ¿hay falla con severidad_inferencia=3 en los próximos 14 días?"""
    fecha_fin = fecha_corte + timedelta(days=HORIZONTE_PREDICCION)
    fallas_futuras = fallas_df[
        (fallas_df["autobus"] == bus_id)
        & (fallas_df["fecha_hora"] >= fecha_corte)
        & (fallas_df["fecha_hora"] < fecha_fin)
        & (fallas_df["codigo"].isin(CODIGOS_CRITICOS))
    ]
    return int(len(fallas_futuras) > 0)


# Generar dataset
rows = []
total = len(buses_target) * len(fechas_corte)
processed = 0

for bus_id in buses_target:
    tel_bus = tel_mant[tel_mant["autobus"] == bus_id]
    
    for fecha_corte in fechas_corte:
        processed += 1
        if processed % 500 == 0:
            print(f"  Procesando {processed}/{total} ({processed*100//total}%)...")
        
        # Ventana de 7 días previos
        fecha_inicio = fecha_corte - timedelta(days=VENTANA_DIAS)
        ventana = tel_bus[
            (tel_bus["evento_fecha_dt"] >= fecha_inicio)
            & (tel_bus["evento_fecha_dt"] < fecha_corte)
        ]
        
        if len(ventana) == 0:
            continue
        
        # Features
        feat_spn = calcular_features_spn(ventana, catalogo_dict)
        feat_fallas = calcular_features_fallas(bus_id, fecha_corte, fallas)
        feat_ctx = calcular_features_contextuales(ventana)
        target = calcular_target(bus_id, fecha_corte, fallas)
        
        row = {
            "autobus": bus_id,
            "fecha_corte": fecha_corte,
            **feat_spn,
            **feat_fallas,
            **feat_ctx,
            "falla_critica_14d": target,
        }
        rows.append(row)

dataset = pd.DataFrame(rows)
print(f"\n  Dataset generado: {len(dataset):,} filas, {len(dataset.columns)} columnas")
print(f"  Target distribution:")
print(f"    0 (sin falla): {(dataset['falla_critica_14d'] == 0).sum():,}")
print(f"    1 (falla crítica): {(dataset['falla_critica_14d'] == 1).sum():,}")
print(f"    Ratio positivos: {dataset['falla_critica_14d'].mean():.2%}")

# ============================================================
# PASO 4: PREPARAR DATOS PARA ENTRENAMIENTO
# ============================================================
print("\n[4/7] Preparando datos para entrenamiento...")

from sklearn.model_selection import train_test_split

# Eliminar columnas no-feature
feature_cols = [c for c in dataset.columns if c not in ["autobus", "fecha_corte", "falla_critica_14d"]]
X = dataset[feature_cols].fillna(0)
y = dataset["falla_critica_14d"]

# Split estratificado 80/20
X_train, X_val, y_train, y_val = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

print(f"  Train: {len(X_train):,} filas ({y_train.mean():.2%} positivos)")
print(f"  Validation: {len(X_val):,} filas ({y_val.mean():.2%} positivos)")

# Guardar en S3 como CSV (formato requerido por XGBoost built-in)
train_df = pd.concat([y_train.reset_index(drop=True), X_train.reset_index(drop=True)], axis=1)
val_df = pd.concat([y_val.reset_index(drop=True), X_val.reset_index(drop=True)], axis=1)

output_prefix = f"s3://{BUCKET}/hackathon-data/modelos/sagemaker/training-data"
train_df.to_csv(f"{output_prefix}/train.csv", index=False, header=False)
val_df.to_csv(f"{output_prefix}/validation.csv", index=False, header=False)

# Guardar feature names para referencia
feature_names_path = f"{output_prefix}/feature_names.json"
s3 = boto3.client("s3", region_name=REGION)
s3.put_object(
    Bucket=BUCKET,
    Key="hackathon-data/modelos/sagemaker/training-data/feature_names.json",
    Body=json.dumps(feature_cols),
    ContentType="application/json",
)

# Guardar dataset completo como Parquet
dataset.to_parquet(f"{output_prefix}/features_completo.parquet", index=False)

print(f"  Datos guardados en {output_prefix}/")
print(f"  Features: {len(feature_cols)}")

# ============================================================
# PASO 5: ENTRENAR XGBOOST
# ============================================================
print("\n[5/7] Entrenando XGBoost...")

import sagemaker
from sagemaker.inputs import TrainingInput
from sagemaker import image_uris

sess = sagemaker.Session()
role = sagemaker.get_execution_role()

# Calcular scale_pos_weight para desbalance de clases
n_neg = (y_train == 0).sum()
n_pos = (y_train == 1).sum()
scale_pos = max(1, n_neg / max(n_pos, 1))
print(f"  scale_pos_weight: {scale_pos:.1f} (neg={n_neg}, pos={n_pos})")

# Obtener imagen de XGBoost
xgb_image = image_uris.retrieve("xgboost", REGION, version="1.7-1")

xgb = sagemaker.estimator.Estimator(
    image_uri=xgb_image,
    role=role,
    instance_count=1,
    instance_type="ml.m5.xlarge",
    output_path=f"s3://{BUCKET}/hackathon-data/modelos/sagemaker/output/",
    sagemaker_session=sess,
)

xgb.set_hyperparameters(
    objective="binary:logistic",
    num_round=200,
    max_depth=6,
    eta=0.1,
    subsample=0.8,
    colsample_bytree=0.8,
    eval_metric="auc",
    scale_pos_weight=round(scale_pos, 1),
)

train_input = TrainingInput(
    s3_data=f"{output_prefix}/train.csv",
    content_type="text/csv",
)
val_input = TrainingInput(
    s3_data=f"{output_prefix}/validation.csv",
    content_type="text/csv",
)

xgb.fit({"train": train_input, "validation": val_input})
print("  Entrenamiento completado.")

# ============================================================
# PASO 6: EVALUAR MODELO
# ============================================================
print("\n[6/7] Evaluando modelo...")

from sklearn.metrics import classification_report, roc_auc_score, confusion_matrix

# Predicción en validación usando el modelo local
import xgboost as xgb_lib

# Descargar modelo
model_path = xgb.model_data
print(f"  Modelo en: {model_path}")

# Usar batch transform para predicción rápida
transformer = xgb.transformer(
    instance_count=1,
    instance_type="ml.m5.large",
    output_path=f"s3://{BUCKET}/hackathon-data/modelos/sagemaker/predictions/",
)

# Guardar validación sin target para predicción
X_val.to_csv(f"{output_prefix}/val_features.csv", index=False, header=False)
transformer.transform(
    f"{output_prefix}/val_features.csv",
    content_type="text/csv",
    split_type="Line",
)
transformer.wait()

# Leer predicciones
preds_df = pd.read_csv(
    f"s3://{BUCKET}/hackathon-data/modelos/sagemaker/predictions/val_features.csv.out",
    header=None,
)
y_pred_proba = preds_df[0].values
y_pred = (y_pred_proba >= 0.5).astype(int)

# Métricas (uso interno — C-003)
auc = roc_auc_score(y_val, y_pred_proba)
print(f"\n  AUC-ROC: {auc:.4f}")
print(f"\n  Classification Report:")
print(classification_report(y_val, y_pred, target_names=["Sin falla", "Falla crítica"]))
print(f"  Confusion Matrix:")
print(confusion_matrix(y_val, y_pred))

# ============================================================
# PASO 7: DESPLEGAR ENDPOINT
# ============================================================
print("\n[7/7] Desplegando endpoint 'ado-prediccion-eventos'...")

predictor = xgb.deploy(
    initial_instance_count=1,
    instance_type="ml.m5.large",
    endpoint_name="ado-prediccion-eventos",
    serializer=sagemaker.serializers.CSVSerializer(),
    deserializer=sagemaker.deserializers.JSONDeserializer(),
)

print(f"  Endpoint desplegado: ado-prediccion-eventos")
print(f"  Región: {REGION}")
print(f"  Account: 084032333314")

# Test rápido con un registro de validación
test_row = X_val.iloc[0:1].values.tolist()[0]
test_csv = ",".join([str(v) for v in test_row])
result = predictor.predict(test_csv)
print(f"\n  Test de predicción:")
print(f"    Input: {len(test_row)} features")
print(f"    Output (probabilidad): {result}")

# Clasificar riesgo
prob = float(result) if isinstance(result, (int, float)) else float(result[0]) if isinstance(result, list) else 0.5
if prob < 0.25:
    nivel = "BAJO"
elif prob < 0.50:
    nivel = "MODERADO"
elif prob < 0.75:
    nivel = "ELEVADO"
else:
    nivel = "CRITICO"
print(f"    Nivel de riesgo: {nivel}")

print("\n" + "=" * 60)
print("MODELO DESPLEGADO EXITOSAMENTE")
print(f"  Endpoint: ado-prediccion-eventos")
print(f"  Features: {len(feature_cols)}")
print(f"  Feature names guardados en: {output_prefix}/feature_names.json")
print(f"  Modelo en: {model_path}")
print("=" * 60)

# ============================================================
# GUARDAR RESUMEN
# ============================================================
resumen = {
    "endpoint_name": "ado-prediccion-eventos",
    "region": REGION,
    "n_features": len(feature_cols),
    "feature_names": feature_cols,
    "n_train": len(X_train),
    "n_val": len(X_val),
    "target_ratio": float(y.mean()),
    "auc_roc": float(auc),
    "codigos_criticos": list(CODIGOS_CRITICOS),
    "codigos_escalamiento": list(CODIGOS_ESCALAMIENTO),
    "model_data": model_path,
    "risk_thresholds": {
        "BAJO": "< 0.25",
        "MODERADO": "0.25 - 0.50",
        "ELEVADO": "0.50 - 0.75",
        "CRITICO": ">= 0.75",
    },
}

s3.put_object(
    Bucket=BUCKET,
    Key="hackathon-data/modelos/sagemaker/model_summary.json",
    Body=json.dumps(resumen, indent=2, default=str),
    ContentType="application/json",
)
print(f"\nResumen guardado en s3://{BUCKET}/hackathon-data/modelos/sagemaker/model_summary.json")
