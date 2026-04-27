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

| Código | Descripción | NUM (ocurrencias) | Justificación | Señales predictivas clave |
|---|---|---|---|---|
| `100` | Engine oil pressure | 116,188 | Presión de aceite baja → daño catastrófico al motor | SPN 100 ↓, SPN 98 ↓, SPN 175 ↑, SPN 247 acumulado |
| `100` | Engine cylinder knock sensor | 116,188 | Detonación en cilindro → daño interno inminente | SPN 110 ↑, SPN 190 ↑, SPN 91 picos, SPN 175 ↑ |
| `158` | Battery potential (voltage)-switched | 14,242 | Falla eléctrica → afecta todos los sistemas | SPN 168 ↓ progresivo, SPN 247 acumulado alto |
| `86` | Brake torque output axle 3 left | 14,024 | Falla de frenos → riesgo de seguridad crítico | SPN 1099-1104 ↓, SPN 521 uso excesivo, SPN 84 alta |

> **Nota:** El código `100` tiene 116,188 ocurrencias — es la falla dominante. Esto genera un dataset con buena representación de la clase positiva.

### Fallas de severidad 2 como señales de escalamiento

Las fallas con `severidad_inferencia = 2` no son target del modelo, pero su presencia reciente es una **feature de alto valor predictivo** porque pueden escalar a severidad 3:

| Código | Descripción | Escala a... |
|---|---|---|
| `111` | Nivel de refrigerante | Sobrecalentamiento motor → código 100 |
| `32` | Turbocharger wastegate drive | Daño a motor por sobrealimentación → código 100 |
| `131` | Exhaust back pressure | Daño a turbo + incumplimiento NOM-044 |
| `37` | Brake slack out of adjustment | Falla de frenos → código 86 |
| `86` | Engine oil replacement valve | Pérdida de presión de aceite → código 100 |

> **Regla de negocio (del manual de fallas):** Si una falla de severidad 2 se presenta >3 veces en 30 días, su severidad efectiva sube a 3.

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
| `fallas_sev2_30d` | Conteo de fallas con severidad_inferencia=2 en últimos 30 días (señal de escalamiento) |
| `fallas_sev2_recurrentes_30d` | 1 si alguna falla sev2 se repite >3 veces en 30 días (regla de escalamiento) |
| `severidad_max_30d` | Severidad máxima de fallas en últimos 30 días |
| `dias_desde_ultima_falla_critica` | Días desde la última falla con código crítico |
| `tiene_falla_activa` | 1 si hay falla con código crítico activo, 0 si no |
| `codigos_criticos_unicos_90d` | Cantidad de códigos críticos distintos en 90 días |
| `fallas_correlacionadas` | 1 si hay combinación de fallas que indica problema sistémico (ver manual de fallas) |

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

# Mapeo componente por código de falla (del manual de fallas)
COMPONENTES_POR_CODIGO = {
    '100': ['circuito_aceite_motor', 'bomba_aceite', 'filtro_aceite', 'sensor_presion', 'inyectores'],
    '158': ['bateria', 'alternador', 'sistema_electrico', 'cableado', 'fusibles'],
    '86': ['sistema_frenos', 'balatas', 'discos_freno', 'circuito_hidraulico', 'slack_adjuster'],
}

# Reglas de escalamiento por acumulación (del manual de fallas)
# - 3+ fallas de severidad baja simultáneas → tratar como severidad media
# - 2+ fallas de severidad media simultáneas → tratar como severidad alta
# - Cualquier combinación con 1 falla de severidad alta → intervención inmediata

# Correlaciones de fallas que indican problemas sistémicos (del manual de fallas)
CORRELACIONES_CRITICAS = {
    'lubricacion': {'spns': [100, 175, 110], 'diagnostico': 'Falla inminente del sistema de lubricación'},
    'refrigeracion': {'spns': [111, 110], 'diagnostico': 'Fuga de refrigerante con sobrecalentamiento'},
    'electrico': {'spns': [168], 'diagnostico': 'Falla del sistema de carga'},
    'postratamiento': {'spns': [131, 1761], 'diagnostico': 'Sistema de postratamiento degradado — riesgo NOM-044'},
    'frenos': {'spns': [1099, 1100, 1101, 1102, 1103, 1104], 'diagnostico': 'Desgaste generalizado del sistema de frenos'},
}
```

---

## 6. Umbrales del manual de mantenimiento para el fallback heurístico

Estos umbrales provienen del `manual-reglas-mantenimiento-motor.md` y se usan en el fallback:

```python
UMBRALES_CRITICOS = {
    # 🔴 PARO INMEDIATO
    110: {'max': 140, 'desc': 'Temperatura Motor ≥ 140°C'},
    175: {'max': 145, 'desc': 'Temperatura Aceite ≥ 145°C'},
    100: {'min': 50, 'desc': 'Presión Aceite ≤ 50 kPa'},
    168: {'min': 10, 'max': 16.5, 'desc': 'Voltaje Batería ≤ 10V o ≥ 16.5V'},
    # Balatas ≤ 5% → cualquiera de 1099-1104
}

UMBRALES_ELEVADOS = {
    # 🟠 INTERVENCIÓN ESTA SEMANA
    110: {'range': (120, 140), 'desc': 'Temperatura Motor 120-140°C sostenido'},
    100: {'range': (50, 150), 'desc': 'Presión Aceite 50-150 kPa'},
    98: {'max': 15, 'desc': 'Nivel aceite ≤ 15%'},
    111: {'max': 20, 'desc': 'Anticongelante ≤ 20%'},
    190: {'max': 2800, 'desc': 'RPM ≥ 2800 sostenido'},
    # Balatas ≤ 20% → cualquiera de 1099-1104
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
- [x] Manuales de Knowledge Base listos (3 manuales)
- [ ] Crear SageMaker Studio domain en us-east-2
- [ ] Ejecutar feature engineering notebook
- [ ] Entrenar XGBoost
- [ ] Desplegar endpoint
- [ ] Probar integración con Lambda

---

## 10. Integración con Knowledge Base y Manuales

Los tres manuales del equipo alimentan tanto al modelo predictivo como al RAG de los agentes de AgentCore:

### Manuales disponibles (carpeta `manuales/`)

| Manual | Aporta al modelo | Aporta al RAG | Destino en S3 |
|---|---|---|---|
| `manual-reglas-mantenimiento-motor.md` | Umbrales de alerta por SPN (CRITICO/ELEVADO/MODERADO/BAJO), intervalos de mantenimiento programado, matriz de correlación de parámetros | Reglas que el agente de mantenimiento consulta para generar recomendaciones contextualizadas | `knowledge-base/docs/` |
| `manual-reglas-ambientales-emisiones.md` | Factor de emisión CO₂ (2.68 kg/L), clasificación ambiental por rendimiento, umbrales de eficiencia por ruta | Reglas que el agente de combustible consulta para evaluar impacto ambiental y cumplimiento NOM-044 | `knowledge-base/docs/` |
| `manual-reglas-fallas-mantenimiento.md` | Señales predictivas clave por falla, reglas de escalamiento por acumulación/recurrencia, correlaciones de fallas | Reglas de negocio para priorización de intervenciones, formato de OT, matriz de decisión rápida | `knowledge-base/docs/` |

### Información clave extraída de los manuales para el modelo

**Del manual de mantenimiento motor:**
- Umbrales exactos de PARO INMEDIATO: Temp Motor ≥140°C, Temp Aceite ≥145°C, Presión Aceite ≤50 kPa, Voltaje ≤10V, Balatas ≤5%
- Umbrales de INTERVENCIÓN URGENTE: Temp Motor 120-140°C, Presión Aceite 50-150 kPa, Nivel aceite ≤15%, RPM ≥2800
- Regla: alertas preventivas se activan por tendencia (≥3 lecturas consecutivas), no por lecturas aisladas
- Regla: alertas correctivas de paro se activan con 1 sola lectura confirmada

**Del manual de emisiones:**
- Rendimiento de referencia: 3.7 km/L (ruta CDMX-Acapulco como línea pivote)
- Factor CO₂: 2.68 kg CO₂ por litro de diésel
- Urea <15% = incumplimiento NOM-044-SEMARNAT-2017
- RPM óptimas en crucero: 1200-1600 rpm

**Del manual de fallas:**
- Regla de escalamiento: falla sev2 que se repite >3 veces en 30 días → sube a sev3
- Regla de acumulación: 2+ fallas sev2 simultáneas → tratar como sev3
- Correlaciones críticas: presión aceite + temp aceite + temp motor = falla inminente de lubricación
- Priorización de taller: sev3 primero → frenos → motor → eléctrico → emisiones
