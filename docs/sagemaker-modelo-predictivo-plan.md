# Plan del Modelo Predictivo de Fallas — SageMaker Studio
## ADO MobilityIA MVP — Hackathon AWS Builders League 2026

> **C-004:** Datos simulados. **C-003:** Sin métricas numéricas específicas en respuestas al usuario.
> Este documento describe el plan completo para entrenar y desplegar el modelo predictivo
> de fallas mecánicas usando Amazon SageMaker Studio con datos en S3 (Parquet).

---

## 1. Objetivo del Modelo

Predecir si un autobús tendrá un **evento de falla mecánica en los próximos 14 días**,
basándose en señales de telemetría (SPNs) y el historial de fallas (`data_fault`).

- **Tipo de problema:** Clasificación binaria
- **Target:** `evento_14_dias` → 1 si hubo falla en los siguientes 14 días, 0 si no
- **Consumidor:** Lambda `tool-predecir-evento` (ya tiene fallback heurístico implementado)

---

## 2. Fuentes de Datos en S3 (Parquet)

Los datos ya están en el bucket como Parquet. El modelo se construye cruzando dos fuentes:

### Fuente A — Telemetría (`telemetry-data`)
```
s3://ado-mobilityia-mvp/telemetria-simulada/{YYYY-MM}/{autobus}/
    telemetria_{autobus}_{YYYY-MM-DD}.parquet
```

Estructura por registro (1 fila = 1 lectura de 1 SPN):

| Campo | Tipo | Rol |
|---|---|---|
| `autobus` | bigint | Identificador del bus |
| `evento_fecha` | date | Fecha de la lectura |
| `evento_fecha_hora` | timestamp | Timestamp exacto |
| `evento_spn` | bigint | SPN ID del sensor leído |
| `evento_valor` | double | Valor numérico de la lectura |
| `viaje_id` | bigint | ID del viaje |
| `viaje_ruta` | string | Ruta del viaje |
| `operador_cve` | string | Clave del conductor |

### Fuente B — Fallas (`data_fault`)
```
s3://ado-mobilityia-mvp/fallas-simuladas/data_fault.parquet
```

| Campo | Tipo | Rol |
|---|---|---|
| `autobus` | string | Bus afectado |
| `fecha_hora` | timestamp | Cuándo ocurrió la falla |
| `codigo` | string | Código de falla (tipo OBD/DTC) |
| `severidad` | bigint | Nivel de severidad (1-5) |
| `modelo` | string | Modelo del bus |
| `marca_comercial` | string | Marca comercial |
| `descripcion` | string | Descripción de la falla |
| `componente` | string | Componente afectado (derivable de `codigo`) |

### Fuente C — Catálogo SPN (`motor_spn`)
```
s3://ado-mobilityia-mvp/catalogo/motor_spn.json
```

Define rangos normales (`minimo`, `maximo`) y variación esperada (`delta`) por SPN.
Se usa para calcular features de "fuera de rango" y "variación anómala".

---

## 3. Estrategia de Feature Engineering

El modelo necesita transformar datos granulares (1 fila por SPN por lectura) en
**un vector de features por autobús por día** (o por ventana de 7 días).

### 3.1 Unidad de observación

Cada fila del dataset de entrenamiento representa:
> **1 autobús × 1 fecha de corte** con features agregadas de los 7 días previos.

### 3.2 Features de Telemetría (por SPN de mantenimiento)

Para cada uno de los **19 SPNs de mantenimiento**, calcular sobre ventana de 7 días:

| Feature | Descripción |
|---|---|
| `spn_{id}_avg_7d` | Promedio de las lecturas |
| `spn_{id}_max_7d` | Valor máximo |
| `spn_{id}_min_7d` | Valor mínimo |
| `spn_{id}_std_7d` | Desviación estándar |
| `spn_{id}_oor_count_7d` | Conteo de lecturas fuera de rango (vs catálogo) |
| `spn_{id}_anomaly_count_7d` | Conteo de variaciones anómalas (> 2× delta) |

**SPNs de mantenimiento (19 confirmados):**

| SPN ID | Nombre | Unidad |
|---|---|---|
| 110 | Temperatura Motor | °C |
| 175 | Temperatura Aceite Motor | °C |
| 100 | Presión Aceite Motor | kPa |
| 98 | Nivel de Aceite | % |
| 111 | Nivel de Anticongelante | % |
| 168 | Voltaje Batería | V |
| 1761 | Nivel Urea | % |
| 520 | Retarder Percent Torque | % |
| 917 | Odómetro | km |
| 247 | Horas Motor | h |
| 190 | RPM | rpm |
| 171 | Temperatura Ambiente | °C |
| 521 | Posición Pedal Freno | % |
| 1099 | Balata Delantero Izquierdo | % |
| 1100 | Balata Delantero Derecho | % |
| 1101 | Balata Trasero Izquierdo 1 | % |
| 1102 | Balata Trasero Derecho 1 | % |
| 1103 | Balata Trasero Izquierdo 2 | % |
| 1104 | Balata Trasero Derecho 2 | % |

Esto genera: **19 SPNs × 6 features = 114 features de telemetría**

### 3.3 Features de Historial de Fallas

Calculadas desde `data_fault` para cada autobús a la fecha de corte:

| Feature | Descripción |
|---|---|
| `fallas_ultimos_30d` | Conteo de fallas en los últimos 30 días |
| `fallas_ultimos_90d` | Conteo de fallas en los últimos 90 días |
| `severidad_max_30d` | Severidad máxima de fallas en últimos 30 días |
| `severidad_avg_30d` | Severidad promedio de fallas en últimos 30 días |
| `dias_desde_ultima_falla` | Días transcurridos desde la última falla |
| `tiene_falla_activa` | 1 si hay falla con código activo, 0 si no |
| `codigos_unicos_90d` | Cantidad de códigos de falla distintos en 90 días |

### 3.4 Features Contextuales

| Feature | Descripción |
|---|---|
| `km_desde_ultimo_mant` | Diferencia de odómetro desde último evento de mantenimiento |
| `horas_motor_acumuladas` | Último valor de SPN 247 (Horas Motor) |
| `balata_min_pct` | Mínimo de las 6 balatas (peor estado de frenos) |
| `total_spns_fuera_rango` | Conteo total de SPNs fuera de rango en la ventana |
| `total_anomalias` | Conteo total de variaciones anómalas en la ventana |

### 3.5 Variable Target

```python
# Para cada (autobus, fecha_corte):
# Buscar en data_fault si existe alguna falla con:
#   autobus == autobus AND fecha_hora BETWEEN fecha_corte AND fecha_corte + 14 días
# Si existe → evento_14_dias = 1
# Si no    → evento_14_dias = 0
```

---

## 4. Pipeline en SageMaker Studio — Paso a Paso

### Paso 1 — Notebook de Exploración y Feature Engineering

**Notebook:** `01-feature-engineering.ipynb`

```
Entorno recomendado:
  - SageMaker Studio Notebook
  - Kernel: Python 3 (Data Science 3.0)
  - Instance: ml.m5.xlarge (4 vCPU, 16 GB RAM)
```

**Flujo del notebook:**

```python
# 1. Leer telemetría desde S3 (Parquet)
import pandas as pd
import boto3

telemetria = pd.read_parquet("s3://ado-mobilityia-mvp/telemetria-simulada/")
fallas = pd.read_parquet("s3://ado-mobilityia-mvp/fallas-simuladas/data_fault.parquet")
catalogo = pd.read_json("s3://ado-mobilityia-mvp/catalogo/motor_spn.json")

# 2. Indexar catálogo SPN
catalogo_dict = {int(row["id"]): row for _, row in catalogo.iterrows()}

# 3. Filtrar solo SPNs de mantenimiento
SPNS_MANTENIMIENTO = {110, 175, 100, 98, 111, 168, 1761, 520, 917, 247,
                       190, 171, 521, 1099, 1100, 1101, 1102, 1103, 1104}
tel_mant = telemetria[telemetria["evento_spn"].isin(SPNS_MANTENIMIENTO)]

# 4. Generar fechas de corte (una por bus por día)
buses = tel_mant["autobus"].unique()
fechas = pd.date_range(
    tel_mant["evento_fecha"].min() + pd.Timedelta(days=7),
    tel_mant["evento_fecha"].max() - pd.Timedelta(days=14),
    freq="D"
)

# 5. Para cada (bus, fecha_corte): calcular features de ventana 7d
# 6. Cruzar con data_fault para generar target
# 7. Exportar dataset final a S3
```

**Output:**
```
s3://ado-mobilityia-mvp/modelos/sagemaker/training-data/
    features_eventos_simulados.parquet
```

### Paso 2 — Entrenamiento del Modelo

**Notebook:** `02-entrenamiento-modelo.ipynb`

**Algoritmo recomendado:** XGBoost (built-in de SageMaker)

Razones:
- Maneja bien datos tabulares con features numéricas
- Robusto ante features con valores faltantes (SPNs que no siempre tienen lectura)
- Rápido de entrenar — clave para hackathon de 5 días
- Built-in de SageMaker = sin necesidad de container custom

```python
import sagemaker
from sagemaker.xgboost import XGBoost
from sagemaker.inputs import TrainingInput

sess = sagemaker.Session()
role = sagemaker.get_execution_role()

# Separar train/validation (80/20 stratified por target)
# Guardar en S3 como CSV (formato requerido por XGBoost built-in)

xgb = XGBoost(
    entry_point="train.py",           # o usar built-in sin script
    framework_version="1.7-1",
    role=role,
    instance_count=1,
    instance_type="ml.m5.xlarge",
    output_path=f"s3://ado-mobilityia-mvp/modelos/sagemaker/output/",
    hyperparameters={
        "objective": "binary:logistic",
        "num_round": 200,
        "max_depth": 6,
        "eta": 0.1,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "eval_metric": "auc",
        "scale_pos_weight": "auto",    # Ajustar por desbalance de clases
    },
)

train_input = TrainingInput(
    s3_data="s3://ado-mobilityia-mvp/modelos/sagemaker/training-data/train.csv",
    content_type="text/csv",
)
val_input = TrainingInput(
    s3_data="s3://ado-mobilityia-mvp/modelos/sagemaker/training-data/validation.csv",
    content_type="text/csv",
)

xgb.fit({"train": train_input, "validation": val_input})
```

### Paso 3 — Evaluación del Modelo

**Notebook:** `03-evaluacion-modelo.ipynb`

```python
# Métricas a evaluar (uso interno, no se exponen al usuario — C-003):
# - AUC-ROC
# - Precision / Recall / F1
# - Matriz de confusión
# - Feature importance (top 20 features)

# Para la demo: lo importante es que el modelo clasifique correctamente
# los buses "trampa" pre-cargados con señales de riesgo.
```

**Criterio de aceptación para el MVP:**
- El modelo debe clasificar correctamente los buses con señales anómalas
  pre-cargadas para la demo
- No se requiere un AUC mínimo formal — es un MVP de hackathon

### Paso 4 — Despliegue como Endpoint

**Notebook:** `04-despliegue-endpoint.ipynb`

```python
from sagemaker.xgboost import XGBoostModel

model = XGBoostModel(
    model_data=xgb.model_data,        # S3 URI del modelo entrenado
    role=role,
    framework_version="1.7-1",
    entry_point="inference.py",        # Script de inferencia custom
)

predictor = model.deploy(
    initial_instance_count=1,
    instance_type="ml.m5.large",       # Instancia pequeña para MVP
    endpoint_name="ado-prediccion-eventos",
)
```

---

## 5. Script de Inferencia (`inference.py`)

El endpoint debe recibir el formato que ya envía `tool-predecir-evento`:

```python
"""
inference.py — Script de inferencia para el endpoint SageMaker.

Recibe features de mantenimiento por autobús, ejecuta predicción
con XGBoost, y retorna nivel de riesgo cualitativo (C-003).
"""
import json
import numpy as np
import xgboost as xgb

# Mapeo de probabilidad a nivel de riesgo cualitativo
RISK_THRESHOLDS = {
    "BAJO": (0.0, 0.25),
    "MODERADO": (0.25, 0.50),
    "ELEVADO": (0.50, 0.75),
    # CRITICO: >= 0.75
}

RISK_DESCRIPTIONS = {
    "BAJO": "Las señales del autobús se encuentran dentro de parámetros normales.",
    "MODERADO": "Se detectan señales con desviación leve. Programar revisión próxima.",
    "ELEVADO": "Señales consistentes con patrones previos a eventos mecánicos. Intervención esta semana.",
    "CRITICO": "Múltiples señales de alerta. Intervención inmediata recomendada.",
}

# Orden de features esperado (debe coincidir con el entrenamiento)
FEATURE_ORDER = []  # Se define durante el entrenamiento


def model_fn(model_dir):
    """Carga el modelo XGBoost desde el directorio del modelo."""
    model = xgb.Booster()
    model.load_model(f"{model_dir}/xgboost-model")
    return model


def input_fn(request_body, content_type="application/json"):
    """Parsea el request del Lambda tool-predecir-evento."""
    if content_type == "application/json":
        data = json.loads(request_body)
        return data
    raise ValueError(f"Content type no soportado: {content_type}")


def predict_fn(input_data, model):
    """Ejecuta la predicción y clasifica el riesgo."""
    features = input_data.get("features", {})
    autobus = input_data.get("autobus", "")

    # Construir vector de features en el orden correcto
    feature_vector = []
    for feature_name in FEATURE_ORDER:
        spn_id = feature_name.split("_")[1]  # Extraer SPN ID
        stat = feature_name.split("_")[-1]   # avg, max, min, etc.
        spn_data = features.get(spn_id, {})
        feature_vector.append(spn_data.get(stat, 0.0))

    # Predicción
    dmatrix = xgb.DMatrix(np.array([feature_vector]))
    probability = float(model.predict(dmatrix)[0])

    # Clasificar riesgo (C-003: sin probabilidades numéricas al usuario)
    if probability < 0.25:
        nivel = "BAJO"
    elif probability < 0.50:
        nivel = "MODERADO"
    elif probability < 0.75:
        nivel = "ELEVADO"
    else:
        nivel = "CRITICO"

    return {
        "autobus": autobus,
        "nivel_riesgo": nivel,
        "descripcion": RISK_DESCRIPTIONS[nivel],
        "score": round(probability * 10, 1),  # Score 0-10 para uso interno
    }


def output_fn(prediction, accept="application/json"):
    """Serializa la respuesta."""
    return json.dumps(prediction), accept
```

---

## 6. Integración con Lambda `tool-predecir-evento`

La Lambda ya está preparada para consumir el endpoint. El flujo actual:

```
1. Lambda recibe autobus del agente Bedrock
2. Consulta últimos 20 registros de DynamoDB
3. Construye feature vector desde SPNs de mantenimiento
4. Intenta invocar SageMaker endpoint "ado-prediccion-eventos"
   ├── Si éxito → usa resultado ML (nivel_riesgo, descripcion, componentes)
   └── Si falla → usa heurística de scoring (ya implementada como fallback)
5. Retorna respuesta al agente
```

**Lo que ya está implementado en la Lambda:**
- `_build_feature_vector()` — construye features desde registros DynamoDB
- `_invoke_sagemaker()` — invoca el endpoint con try/except
- `_heuristic_score()` — fallback completo con scoring por umbrales
- `_classify_risk()` — clasificación BAJO/MODERADO/ELEVADO/CRITICO
- `_get_at_risk_components()` — mapeo SPN → componente en riesgo

**Lo que hay que alinear:**
- El formato del payload que envía la Lambda debe coincidir con lo que espera `inference.py`
- El `FEATURE_ORDER` en `inference.py` debe coincidir con el orden del entrenamiento

---

## 7. Estructura de Archivos en S3

```
s3://ado-mobilityia-mvp/modelos/sagemaker/
├── training-data/
│   ├── features_eventos_simulados.parquet   ← Dataset completo
│   ├── train.csv                            ← 80% para entrenamiento
│   └── validation.csv                       ← 20% para validación
├── output/
│   └── xgboost-{timestamp}/
│       └── model.tar.gz                     ← Modelo entrenado
└── notebooks/
    ├── 01-feature-engineering.ipynb
    ├── 02-entrenamiento-modelo.ipynb
    ├── 03-evaluacion-modelo.ipynb
    └── 04-despliegue-endpoint.ipynb
```

---

## 8. Plan de Ejecución (dentro del Día 3)

| Paso | Tarea | Tiempo estimado |
|---|---|---|
| 1 | Crear notebook en SageMaker Studio, configurar acceso a S3 | 30 min |
| 2 | Feature engineering: leer Parquets, pivotar SPNs, generar target | 2-3 horas |
| 3 | Entrenar XGBoost con datos procesados | 30 min |
| 4 | Evaluar modelo, verificar que clasifica buses "trampa" correctamente | 30 min |
| 5 | Desplegar endpoint `ado-prediccion-eventos` | 15 min |
| 6 | Probar integración con Lambda `tool-predecir-evento` | 30 min |
| **Total** | | **~4-5 horas** |

### Plan B (Fallback)

Si SageMaker tarda demasiado o hay problemas:
- La Lambda `tool-predecir-evento` **ya tiene el fallback heurístico completo**
- El scoring por umbrales de SPNs + severidad de fallas recientes funciona sin ML
- Para la demo, el fallback es suficiente — el agente responde igual con nivel de riesgo cualitativo

---

## 9. Datos "Trampa" para la Demo

Pre-cargar en DynamoDB buses con señales que garanticen alertas durante la presentación:

| Bus | Señal anómala | Resultado esperado |
|---|---|---|
| Bus A | Temperatura motor elevada + presión aceite baja | CRITICO — sistema refrigeración + circuito aceite |
| Bus B | Balatas con desgaste avanzado | ELEVADO — sistema de frenos |
| Bus C | Voltaje batería bajo + nivel urea bajo | MODERADO — sistema eléctrico + escape |
| Bus D | Todas las señales normales | BAJO — sin intervención requerida |

---

## 10. Permisos IAM Necesarios

### Rol de SageMaker Studio
```yaml
Políticas:
  - AmazonSageMakerFullAccess
  - AmazonS3FullAccess              # Acceso al bucket ado-mobilityia-mvp
  - CloudWatchLogsFullAccess         # Logs de entrenamiento
```

### Rol de Lambda (ya configurado)
```yaml
Política adicional para tool-predecir-evento:
  - sagemaker:InvokeEndpoint
  - Resource: arn:aws:sagemaker:us-east-1:*:endpoint/ado-prediccion-eventos
```

---

## 11. Checklist Pre-Entrenamiento

- [ ] Verificar que los Parquets de telemetría están en S3 con la estructura esperada
- [ ] Verificar que `data_fault.parquet` está en S3
- [ ] Verificar que `motor_spn.json` está en S3 como catálogo
- [ ] Crear rol IAM para SageMaker Studio con acceso a S3
- [ ] Crear SageMaker Studio domain en us-east-1
- [ ] Subir notebooks al Studio
- [ ] Ejecutar feature engineering y validar que el dataset tiene suficientes muestras positivas
- [ ] Entrenar modelo y verificar métricas básicas
- [ ] Desplegar endpoint y probar con payload de ejemplo
- [ ] Verificar que Lambda `tool-predecir-evento` conecta correctamente al endpoint
