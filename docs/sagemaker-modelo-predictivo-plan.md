# Plan del Modelo Predictivo de Fallas — SageMaker Studio
## ADO MobilityIA MVP — Hackathon AWS Builders League 2026

> **C-004:** Datos simulados. **C-003:** Sin métricas numéricas específicas en respuestas al usuario.
> **C-007:** Solo fallas con `severidad_inferencia = 3` son el target del modelo.
> **Región:** us-east-2. **Profile:** mobilityadods. **Bucket:** ado-telemetry-mvp.

---

## 1. Objetivo del Modelo

Predecir si un autobús tendrá una **falla crítica (severidad_inferencia = 3) en los próximos 14 días**,
basándose en señales de telemetría (SPNs) y el historial de fallas.

- **Tipo de problema:** Clasificación binaria
- **Target:** `falla_critica_14d` → 1 si hubo falla con severidad_inferencia=3 en los siguientes 14 días, 0 si no
- **Consumidor:** Lambda `tool-predecir-evento` (ya tiene fallback heurístico implementado)

### Fallas objetivo (severidad_inferencia = 3) — C-007

Solo estas fallas son las que el modelo debe predecir:

| Código | Descripción | NUM (ocurrencias) | Justificación |
|---|---|---|---|
| `100` | Engine oil pressure | 116,188 | Presión de aceite baja → daño catastrófico al motor |
| `100` | Engine cylinder #11 knock sensor | 116,188 | Detonación en cilindro → daño interno inminente |
| `158` | Battery potential (voltage)-switched | 14,242 | Falla eléctrica → afecta todos los sistemas |
| `86` | Brake torque output axle 3 left | 14,024 | Falla de frenos → riesgo de seguridad crítico |

> **Nota:** El código `100` tiene 116,188 ocurrencias — es la falla dominante. Esto genera un dataset con buena representación de la clase positiva.

---

## 2. Fuentes de Datos en S3 (ya subidas)

Los datos ya están en el bucket `ado-telemetry-mvp` en `us-east-2`:

### Fuente A — Telemetría (`travel_telemetry`)
```
s3://ado-telemetry-mvp/hackathon-data/raw/travel_telemetry/
    travel_telemetry_000000000000.parquet ... travel_telemetry_000000001338.parquet
```
- **1,339 archivos Parquet**, ~447 MB total
- Muchos archivos son vacíos (~2.5KB), los con datos van de 100KB a 4.9MB
- Estructura: 1 fila = 1 lectura de 1 SPN (hay que pivotar)

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
s3://ado-telemetry-mvp/hackathon-data/raw/data_fault/
    data_fault_000000000000.parquet ... data_fault_000000000122.parquet
```
- **123 archivos Parquet**, ~6.5 MB total

| Campo | Tipo | Rol |
|---|---|---|
| `autobus` | string | Bus afectado |
| `fecha_hora` | timestamp | Cuándo ocurrió la falla |
| `codigo` | string | Código de falla |
| `severidad` | bigint | Nivel de severidad original |
| `modelo` | string | Modelo del bus |
| `marca_comercial` | string | Marca comercial |
| `descripcion` | string | Descripción de la falla |

### Fuente C — Catálogo SPN (`motor_spn`)
```
s3://ado-telemetry-mvp/hackathon-data/raw/motor_spn/
    motor_spn_000000000000.parquet
```
- **1 archivo Parquet**, ~3.6 KB — 36 SPNs con rangos y umbrales

---

## 3. Estrategia de Feature Engineering (acotada a fallas críticas)

### 3.1 Filtro de fallas — Solo severidad_inferencia = 3

```python
# Códigos de falla con severidad_inferencia = 3
CODIGOS_CRITICOS = {'100', '158', '86'}

# Filtrar data_fault para solo incluir fallas críticas
fallas_criticas = fallas[fallas['codigo'].isin(CODIGOS_CRITICOS)]
```

### 3.2 Unidad de observación

Cada fila del dataset de entrenamiento:
> **1 autobús × 1 fecha de corte** con features agregadas de los 7 días previos.

### 3.3 Features de Telemetría (SPNs de mantenimiento × 6 estadísticos)

Para cada uno de los **19 SPNs de mantenimiento**, calcular sobre ventana de 7 días:

| Feature | Descripción |
|---|---|
| `spn_{id}_avg_7d` | Promedio de lecturas |
| `spn_{id}_max_7d` | Valor máximo |
| `spn_{id}_min_7d` | Valor mínimo |
| `spn_{id}_std_7d` | Desviación estándar |
| `spn_{id}_oor_count_7d` | Lecturas fuera de rango (vs catálogo motor_spn) |
| `spn_{id}_anomaly_count_7d` | Variaciones anómalas (> 2× delta del catálogo) |

**SPNs de mantenimiento (19 confirmados):** 110, 175, 100, 98, 111, 168, 1761, 520, 917, 247, 190, 171, 521, 1099, 1100, 1101, 1102, 1103, 1104

→ **19 SPNs × 6 features = 114 features de telemetría**

### 3.4 Features de Historial de Fallas (acotadas a códigos críticos)

| Feature | Descripción |
|---|---|
| `fallas_criticas_30d` | Conteo de fallas con código en {100, 158, 86} en últimos 30 días |
| `fallas_criticas_90d` | Conteo de fallas críticas en últimos 90 días |
| `severidad_max_30d` | Severidad máxima de fallas en últimos 30 días |
| `dias_desde_ultima_falla_critica` | Días desde la última falla con código crítico |
| `tiene_falla_activa` | 1 si hay falla con código crítico activo, 0 si no |
| `codigos_criticos_unicos_90d` | Cantidad de códigos críticos distintos en 90 días |

### 3.5 Features Contextuales

| Feature | Descripción |
|---|---|
| `km_desde_ultimo_mant` | Diferencia de odómetro (SPN 917) |
| `horas_motor_acumuladas` | Último valor de SPN 247 |
| `balata_min_pct` | Mínimo de las 6 balatas (SPN 1099-1104) |
| `total_spns_fuera_rango` | Conteo total de SPNs fuera de rango |
| `total_anomalias` | Conteo total de variaciones anómalas |

### 3.6 Variable Target (acotada a C-007)

```python
# Para cada (autobus, fecha_corte):
# Buscar en data_fault si existe alguna falla con:
#   autobus == autobus
#   AND codigo IN ('100', '158', '86')  ← solo severidad_inferencia = 3
#   AND fecha_hora BETWEEN fecha_corte AND fecha_corte + 14 días
# Si existe → falla_critica_14d = 1
# Si no    → falla_critica_14d = 0
```

---

## 4. Pipeline en SageMaker Studio

### Paso 1 — Notebook de Feature Engineering

**Notebook:** `01-feature-engineering.ipynb`

```
Entorno: SageMaker Studio, Python 3 (Data Science 3.0), ml.m5.xlarge
Región: us-east-2
```

```python
import pandas as pd
import boto3

# 1. Leer datos desde S3 (Parquet particionado)
telemetria = pd.read_parquet("s3://ado-telemetry-mvp/hackathon-data/raw/travel_telemetry/")
fallas = pd.read_parquet("s3://ado-telemetry-mvp/hackathon-data/raw/data_fault/")
catalogo = pd.read_parquet("s3://ado-telemetry-mvp/hackathon-data/raw/motor_spn/")

# 2. Filtrar solo fallas críticas (severidad_inferencia = 3)
CODIGOS_CRITICOS = {'100', '158', '86'}
fallas_criticas = fallas[fallas['codigo'].astype(str).isin(CODIGOS_CRITICOS)]

# 3. Filtrar solo SPNs de mantenimiento
SPNS_MANTENIMIENTO = {110, 175, 100, 98, 111, 168, 1761, 520, 917, 247,
                       190, 171, 521, 1099, 1100, 1101, 1102, 1103, 1104}
tel_mant = telemetria[telemetria['evento_spn'].isin(SPNS_MANTENIMIENTO)]

# 4. Indexar catálogo para umbrales
catalogo_dict = {int(row['id']): row for _, row in catalogo.iterrows()}

# 5. Generar fechas de corte y calcular features por (autobus, fecha)
# 6. Cruzar con fallas_criticas para generar target
# 7. Exportar a S3
```

### Paso 2 — Entrenamiento XGBoost

```python
from sagemaker.xgboost import XGBoost

xgb = XGBoost(
    framework_version="1.7-1",
    role=role,
    instance_count=1,
    instance_type="ml.m5.xlarge",
    output_path="s3://ado-telemetry-mvp/hackathon-data/modelos/sagemaker/output/",
    hyperparameters={
        "objective": "binary:logistic",
        "num_round": 200,
        "max_depth": 6,
        "eta": 0.1,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "eval_metric": "auc",
        "scale_pos_weight": "auto",
    },
)
```

### Paso 3 — Deploy como Endpoint

```python
predictor = model.deploy(
    initial_instance_count=1,
    instance_type="ml.m5.large",
    endpoint_name="ado-prediccion-eventos",
)
```

---

## 5. Clasificación de Riesgo (C-003 — sin probabilidades numéricas)

```python
RISK_DESCRIPTIONS = {
    "BAJO": "Señales dentro de parámetros normales.",
    "MODERADO": "Desviación leve detectada. Programar revisión próxima.",
    "ELEVADO": "Señales consistentes con patrones previos a fallas críticas. Intervención esta semana.",
    "CRITICO": "Múltiples señales de alerta asociadas a fallas de motor/frenos/eléctrico. Intervención inmediata.",
}

# Mapeo componente por código de falla
COMPONENTES_POR_CODIGO = {
    '100': ['circuito_aceite_motor', 'bomba_aceite', 'filtro_aceite', 'sensor_presion'],
    '158': ['bateria', 'alternador', 'sistema_electrico', 'cableado'],
    '86': ['sistema_frenos', 'balatas', 'discos_freno', 'circuito_hidraulico'],
}
```

---

## 6. Plan B — Fallback Heurístico (ya implementado)

Si SageMaker no está listo a tiempo, la Lambda `tool-predecir-evento` ya tiene un scoring heurístico completo que:
- Evalúa SPNs de mantenimiento contra umbrales del catálogo
- Calcula score de riesgo por componente
- Clasifica en BAJO/MODERADO/ELEVADO/CRITICO
- Mapea SPNs a componentes en riesgo

Para la demo, el fallback es suficiente — el agente responde igual con nivel de riesgo cualitativo.

---

## 7. Datos "Trampa" para la Demo

Pre-cargar en DynamoDB buses con señales que disparen las fallas críticas:

| Bus | Señal anómala | Código target | Resultado esperado |
|---|---|---|---|
| Bus A | Presión aceite baja (SPN 100) + temp motor alta (SPN 110) | 100 | CRITICO — Engine oil pressure |
| Bus B | Voltaje batería bajo (SPN 168) + voltaje sin alternador bajo (SPN 20000) | 158 | ELEVADO — Battery voltage |
| Bus C | Balatas con desgaste avanzado (SPN 1099-1104 < 20%) | 86 | ELEVADO — Brake system |
| Bus D | Todas las señales normales | — | BAJO — Sin intervención |

---

## 8. Permisos IAM

### Rol de SageMaker Studio
```yaml
Políticas:
  - AmazonSageMakerFullAccess
  - AmazonS3FullAccess  # Acceso a ado-telemetry-mvp
  - CloudWatchLogsFullAccess
```

### Rol de Lambda (tool-predecir-evento)
```yaml
Política adicional:
  - sagemaker:InvokeEndpoint
  - Resource: arn:aws:sagemaker:us-east-2:084032333314:endpoint/ado-prediccion-eventos
```

---

## 9. Checklist

- [x] Datos de telemetría en S3 (1,339 archivos, ~447 MB)
- [x] Datos de fallas en S3 (123 archivos, ~6.5 MB)
- [x] Catálogo SPN en S3 (1 archivo)
- [x] Fallas clasificadas con severidad_inferencia (C-007)
- [x] Fallback heurístico implementado en Lambda
- [ ] Crear SageMaker Studio domain en us-east-2
- [ ] Ejecutar feature engineering notebook
- [ ] Entrenar XGBoost
- [ ] Desplegar endpoint
- [ ] Probar integración con Lambda
