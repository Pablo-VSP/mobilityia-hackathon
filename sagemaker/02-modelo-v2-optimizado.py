"""
ADO MobilityIA — Modelo Predictivo v2 (optimizado)
Hackathon AWS Builders League 2026

Cambios vs v1:
- Solo ~10 SPNs directamente correlacionados con fallas críticas (no 19)
- 4 estadísticos por SPN (avg, max, min, oor_count) en lugar de 6
- ~50 features totales en lugar de 128
- Mejor señal/ruido para las 3 fallas target

SPNs seleccionados por falla crítica (de los manuales):
  Código 100 (presión aceite/motor): SPN 100, 98, 175, 110, 190, 247
  Código 158 (voltaje batería): SPN 168, 247
  Código 86 (frenos): SPN 521, 84, 520, 1099-1104 (balatas)

C-007: Solo fallas severidad_inferencia = 3
C-008: Entrenamiento oct-dic 2020, simulación enero 2021
"""

import pandas as pd
import numpy as np
import boto3
import json
from datetime import timedelta

BUCKET = "ado-telemetry-mvp"
PREFIX_TELEMETRY = "hackathon-data/raw/travel_telemetry/"
PREFIX_FAULTS = "hackathon-data/raw/data_fault/"
PREFIX_SPN = "hackathon-data/raw/motor_spn/"
REGION = "us-east-2"

CODIGOS_CRITICOS = {"100", "158", "86"}
CODIGOS_ESCALAMIENTO = {"111", "32", "131", "37"}
FECHA_CORTE = pd.Timestamp("2021-01-01")
VENTANA_DIAS = 7
HORIZONTE = 14

# SPNs clave por sistema de falla
SPNS_MODELO = {
    100: "presion_aceite",     # Código 100 — presión aceite motor
    98:  "nivel_aceite",       # Código 100 — nivel aceite %
    175: "temp_aceite",        # Código 100 — temperatura aceite
    110: "temp_motor",         # Código 100 — temperatura motor
    190: "rpm",                # Código 100 — RPM (estrés motor)
    168: "voltaje_bat",        # Código 158 — voltaje batería
    521: "freno",              # Código 86 — pedal freno
    84:  "velocidad",          # Código 86 — velocidad (frenado brusco)
    520: "retarder",           # Código 86 — retarder (compensación frenos)
    247: "horas_motor",        # Todos — acumulador de desgaste
}

print("=" * 60)
print("ADO MobilityIA — Modelo Predictivo v2 (optimizado)")
print(f"SPNs clave: {len(SPNS_MODELO)} (enfocados en fallas 100, 158, 86)")
print(f"Entrenamiento: antes de {FECHA_CORTE.date()}")
print("=" * 60)

# ============================================================
# PASO 1: CARGAR Y LIMPIAR DATOS
# ============================================================
print("\n[1/6] Cargando datos desde S3...")

telemetria = pd.read_parquet(f"s3://{BUCKET}/{PREFIX_TELEMETRY}")
fallas = pd.read_parquet(f"s3://{BUCKET}/{PREFIX_FAULTS}")
catalogo = pd.read_parquet(f"s3://{BUCKET}/{PREFIX_SPN}")

# Normalizar columnas a lowercase
telemetria.columns = telemetria.columns.str.strip().str.lower()
fallas.columns = fallas.columns.str.strip().str.lower()
catalogo.columns = catalogo.columns.str.strip().str.lower()

for col in catalogo.select_dtypes(include="object").columns:
    catalogo[col] = catalogo[col].str.strip()
for col in fallas.select_dtypes(include="object").columns:
    fallas[col] = fallas[col].str.strip()

# Tipos
telemetria["autobus"] = telemetria["autobus"].astype(str).str.strip()
telemetria["evento_spn"] = pd.to_numeric(telemetria["evento_spn"], errors="coerce").astype("Int64")
telemetria["evento_valor"] = pd.to_numeric(telemetria["evento_valor"], errors="coerce")
telemetria["evento_fecha_hora"] = pd.to_datetime(telemetria["evento_fecha_hora"], errors="coerce")
telemetria["evento_fecha"] = pd.to_datetime(telemetria["evento_fecha"], errors="coerce")

fallas["autobus"] = fallas["autobus"].astype(str).str.strip()
fallas["codigo"] = fallas["codigo"].astype(str).str.strip()
fallas["fecha_hora"] = pd.to_datetime(fallas["fecha_hora"], errors="coerce")

# Catálogo indexado
catalogo_dict = {}
for _, row in catalogo.iterrows():
    catalogo_dict[int(row["id"])] = {
        "minimo": float(row.get("minimo", 0)),
        "maximo": float(row.get("maximo", 0)),
        "delta": float(row.get("delta", 0)),
    }

print(f"  Telemetría: {len(telemetria):,} registros")
print(f"  Fallas: {len(fallas):,} registros")

# C-008: Filtrar entrenamiento (oct-dic 2020)
tel_train = telemetria[telemetria["evento_fecha"] < FECHA_CORTE].copy()
fallas_train = fallas[fallas["fecha_hora"] < FECHA_CORTE].copy()

# Solo SPNs del modelo
tel_train = tel_train[tel_train["evento_spn"].isin(SPNS_MODELO.keys())].copy()
tel_train = tel_train.dropna(subset=["evento_valor"])

print(f"  Entrenamiento — Telemetría (SPNs filtrados): {len(tel_train):,}")
print(f"  Entrenamiento — Fallas: {len(fallas_train):,}")
print(f"  Buses únicos: {tel_train['autobus'].nunique()}")
print(f"  Rango: {tel_train['evento_fecha'].min()} a {tel_train['evento_fecha'].max()}")

# ============================================================
# PASO 2: FEATURE ENGINEERING (ventana 7 días por bus)
# ============================================================
print("\n[2/6] Generando features por (autobus, fecha_corte)...")

buses = tel_train["autobus"].unique()
tel_train["evento_fecha_dt"] = tel_train["evento_fecha"]

fecha_min = tel_train["evento_fecha_dt"].min() + timedelta(days=VENTANA_DIAS)
fecha_max = tel_train["evento_fecha_dt"].max() - timedelta(days=HORIZONTE)
fechas_corte = pd.date_range(fecha_min, fecha_max, freq="7D")

print(f"  Buses: {len(buses)}")
print(f"  Fechas de corte: {len(fechas_corte)} (cada 7 días)")


def features_ventana(registros, catalogo_dict):
    """Features de SPNs clave sobre una ventana de registros."""
    f = {}

    for spn_id, nombre in SPNS_MODELO.items():
        vals = registros[registros["evento_spn"] == spn_id]["evento_valor"]
        if len(vals) > 0:
            f[f"{nombre}_avg"] = vals.mean()
            f[f"{nombre}_max"] = vals.max()
            f[f"{nombre}_min"] = vals.min()
            # Fuera de rango
            cat = catalogo_dict.get(spn_id)
            if cat:
                f[f"{nombre}_oor"] = int(((vals < cat["minimo"]) | (vals > cat["maximo"])).sum())
            else:
                f[f"{nombre}_oor"] = 0
        else:
            f[f"{nombre}_avg"] = np.nan
            f[f"{nombre}_max"] = np.nan
            f[f"{nombre}_min"] = np.nan
            f[f"{nombre}_oor"] = 0

    # Features de umbrales críticos (del manual de mantenimiento)
    presion = registros[registros["evento_spn"] == 100]["evento_valor"]
    temp_motor = registros[registros["evento_spn"] == 110]["evento_valor"]
    voltaje = registros[registros["evento_spn"] == 168]["evento_valor"]

    f["pct_presion_bajo_150"] = (presion < 150).mean() if len(presion) > 0 else 0
    f["pct_presion_bajo_50"] = (presion < 50).mean() if len(presion) > 0 else 0
    f["pct_temp_motor_sobre_115"] = (temp_motor > 115).mean() if len(temp_motor) > 0 else 0
    f["pct_temp_motor_sobre_140"] = (temp_motor > 140).mean() if len(temp_motor) > 0 else 0
    f["pct_voltaje_bajo_12"] = (voltaje < 12).mean() if len(voltaje) > 0 else 0
    f["pct_voltaje_sobre_15_5"] = (voltaje > 15.5).mean() if len(voltaje) > 0 else 0

    # Total fuera de rango
    f["total_oor"] = sum(v for k, v in f.items() if k.endswith("_oor"))

    # Cantidad de registros (proxy de actividad del bus)
    f["n_registros_ventana"] = len(registros)

    return f


def features_fallas(bus_id, fecha_corte, fallas_df):
    """Features de historial de fallas."""
    fallas_bus = fallas_df[fallas_df["autobus"] == bus_id]
    f30 = fecha_corte - timedelta(days=30)
    f90 = fecha_corte - timedelta(days=90)

    fallas_30d = fallas_bus[(fallas_bus["fecha_hora"] >= f30) & (fallas_bus["fecha_hora"] < fecha_corte)]
    fallas_90d = fallas_bus[(fallas_bus["fecha_hora"] >= f90) & (fallas_bus["fecha_hora"] < fecha_corte)]

    criticas_30d = fallas_30d[fallas_30d["codigo"].isin(CODIGOS_CRITICOS)]
    sev2_30d = fallas_30d[fallas_30d["codigo"].isin(CODIGOS_ESCALAMIENTO)]

    # Recurrencia sev2 (regla del manual: >3 veces en 30 días → escala)
    sev2_recurrente = 0
    if len(sev2_30d) > 0:
        sev2_recurrente = int((sev2_30d["codigo"].value_counts() > 3).any())

    # Días desde última falla crítica
    criticas_previas = fallas_bus[
        (fallas_bus["fecha_hora"] < fecha_corte) & (fallas_bus["codigo"].isin(CODIGOS_CRITICOS))
    ]
    dias_desde = (fecha_corte - criticas_previas["fecha_hora"].max()).days if len(criticas_previas) > 0 else 999

    return {
        "fallas_criticas_30d": len(criticas_30d),
        "fallas_sev2_30d": len(sev2_30d),
        "fallas_sev2_recurrentes": sev2_recurrente,
        "dias_desde_ultima_critica": min(dias_desde, 999),
        "tiene_falla_activa": int(len(criticas_30d) > 0),
        "total_fallas_90d": len(fallas_90d),
    }


def calcular_target(bus_id, fecha_corte, fallas_df):
    """¿Falla crítica en los próximos 14 días?"""
    fecha_fin = fecha_corte + timedelta(days=HORIZONTE)
    futuras = fallas_df[
        (fallas_df["autobus"] == bus_id)
        & (fallas_df["fecha_hora"] >= fecha_corte)
        & (fallas_df["fecha_hora"] < fecha_fin)
        & (fallas_df["codigo"].isin(CODIGOS_CRITICOS))
    ]
    return int(len(futuras) > 0)


# Generar dataset
rows = []
total = len(buses) * len(fechas_corte)
processed = 0

for bus_id in buses:
    tel_bus = tel_train[tel_train["autobus"] == bus_id]

    for fecha_corte in fechas_corte:
        processed += 1
        if processed % 500 == 0:
            print(f"  {processed}/{total} ({processed*100//total}%)...")

        fecha_inicio = fecha_corte - timedelta(days=VENTANA_DIAS)
        ventana = tel_bus[
            (tel_bus["evento_fecha_dt"] >= fecha_inicio) & (tel_bus["evento_fecha_dt"] < fecha_corte)
        ]

        if len(ventana) < 10:
            continue

        feat_spn = features_ventana(ventana, catalogo_dict)
        feat_fallas = features_fallas(bus_id, fecha_corte, fallas_train)
        target = calcular_target(bus_id, fecha_corte, fallas_train)

        rows.append({
            "autobus": bus_id,
            "fecha_corte": fecha_corte,
            **feat_spn,
            **feat_fallas,
            "falla_critica_14d": target,
        })

dataset = pd.DataFrame(rows)
print(f"\n  Dataset: {len(dataset):,} filas")
print(f"  Target: 0={( dataset['falla_critica_14d']==0).sum():,}, 1={(dataset['falla_critica_14d']==1).sum():,} ({dataset['falla_critica_14d'].mean():.2%})")

# ============================================================
# PASO 3: ENTRENAR XGBOOST
# ============================================================
print("\n[3/6] Entrenando XGBoost v2...")

from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, roc_auc_score
import sagemaker
from sagemaker.inputs import TrainingInput
from sagemaker import image_uris

meta_cols = ["autobus", "fecha_corte", "falla_critica_14d"]
feature_cols = [c for c in dataset.columns if c not in meta_cols]
X = dataset[feature_cols].fillna(0)
y = dataset["falla_critica_14d"]

print(f"  Features: {len(feature_cols)}")

X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
print(f"  Train: {len(X_train):,} ({y_train.mean():.2%} pos)")
print(f"  Val: {len(X_val):,} ({y_val.mean():.2%} pos)")

output_prefix = f"s3://{BUCKET}/hackathon-data/modelos/sagemaker-v2/training-data"
train_df = pd.concat([y_train.reset_index(drop=True), X_train.reset_index(drop=True)], axis=1)
val_df = pd.concat([y_val.reset_index(drop=True), X_val.reset_index(drop=True)], axis=1)
train_df.to_csv(f"{output_prefix}/train.csv", index=False, header=False)
val_df.to_csv(f"{output_prefix}/validation.csv", index=False, header=False)

s3 = boto3.client("s3", region_name=REGION)
s3.put_object(
    Bucket=BUCKET,
    Key="hackathon-data/modelos/sagemaker-v2/training-data/feature_names.json",
    Body=json.dumps(feature_cols), ContentType="application/json",
)
dataset.to_parquet(f"{output_prefix}/dataset_completo.parquet", index=False)

sess = sagemaker.Session()
role = sagemaker.get_execution_role()
n_pos = max((y_train == 1).sum(), 1)
scale_pos = max(1, (y_train == 0).sum() / n_pos)

xgb_image = image_uris.retrieve("xgboost", REGION, version="1.7-1")
xgb = sagemaker.estimator.Estimator(
    image_uri=xgb_image, role=role, instance_count=1, instance_type="ml.m5.xlarge",
    output_path=f"s3://{BUCKET}/hackathon-data/modelos/sagemaker-v2/output/",
    sagemaker_session=sess,
)
xgb.set_hyperparameters(
    objective="binary:logistic", num_round=150, max_depth=5, eta=0.1,
    subsample=0.8, colsample_bytree=0.8, eval_metric="auc",
    scale_pos_weight=round(scale_pos, 1),
)

xgb.fit({
    "train": TrainingInput(f"{output_prefix}/train.csv", content_type="text/csv"),
    "validation": TrainingInput(f"{output_prefix}/validation.csv", content_type="text/csv"),
})
print("  Entrenamiento completado.")

# ============================================================
# PASO 4: EVALUAR
# ============================================================
print("\n[4/6] Evaluando...")

transformer = xgb.transformer(
    instance_count=1, instance_type="ml.m5.large",
    output_path=f"s3://{BUCKET}/hackathon-data/modelos/sagemaker-v2/predictions/",
)
X_val.to_csv(f"{output_prefix}/val_features.csv", index=False, header=False)
transformer.transform(f"{output_prefix}/val_features.csv", content_type="text/csv", split_type="Line")
transformer.wait()

preds = pd.read_csv(
    f"s3://{BUCKET}/hackathon-data/modelos/sagemaker-v2/predictions/val_features.csv.out", header=None
)
y_proba = preds[0].values
y_pred = (y_proba >= 0.5).astype(int)
auc = roc_auc_score(y_val, y_proba)

print(f"  AUC-ROC: {auc:.4f}")
print(classification_report(y_val, y_pred, target_names=["Sin falla", "Falla crítica"]))

# ============================================================
# PASO 5: REEMPLAZAR ENDPOINT
# ============================================================
print("\n[5/6] Reemplazando endpoint...")

sm_client = boto3.client("sagemaker", region_name=REGION)
try:
    sm_client.delete_endpoint(EndpointName="ado-prediccion-eventos")
    print("  Endpoint v1 eliminado. Esperando 30s...")
    import time; time.sleep(30)
except Exception as e:
    print(f"  No había endpoint previo: {e}")

predictor = xgb.deploy(
    initial_instance_count=1, instance_type="ml.m5.large",
    endpoint_name="ado-prediccion-eventos",
    serializer=sagemaker.serializers.CSVSerializer(),
    deserializer=sagemaker.deserializers.JSONDeserializer(),
)

test_csv = ",".join([str(v) for v in X_val.iloc[0].values])
result = predictor.predict(test_csv)
print(f"  Test: {result}")

# ============================================================
# PASO 6: GUARDAR RESUMEN
# ============================================================
print("\n[6/6] Guardando resumen...")

resumen = {
    "version": "v2-optimizado",
    "endpoint_name": "ado-prediccion-eventos",
    "region": REGION,
    "n_features": len(feature_cols),
    "feature_names": feature_cols,
    "spns_modelo": {str(k): v for k, v in SPNS_MODELO.items()},
    "n_train": len(X_train),
    "n_val": len(X_val),
    "target_ratio": float(y.mean()),
    "auc_roc": float(auc),
    "codigos_criticos": list(CODIGOS_CRITICOS),
    "model_data": xgb.model_data,
    "enfoque": "Ventana 7 días, 10 SPNs clave por falla, ~50 features, umbrales del manual de mantenimiento",
}

s3.put_object(
    Bucket=BUCKET,
    Key="hackathon-data/modelos/sagemaker-v2/model_summary.json",
    Body=json.dumps(resumen, indent=2, default=str),
    ContentType="application/json",
)

print("\n" + "=" * 60)
print("MODELO v2 DESPLEGADO")
print(f"  Endpoint: ado-prediccion-eventos")
print(f"  Features: {len(feature_cols)} (vs 128 del v1)")
print(f"  SPNs: {len(SPNS_MODELO)} (enfocados en fallas 100, 158, 86)")
print(f"  AUC: {auc:.4f}")
print(f"  Modelo: {xgb.model_data}")
print("=" * 60)
