# 🚌 Guía del Simulador de Streaming de Telemetría
## ADO MobilityIA — Lambda `ado-simulador-telemetria`

> Este documento describe cómo funciona el microservicio de simulación de telemetría en tiempo real,
> qué formato de datos espera como entrada, y cómo generar nuevos viajes compatibles.

---

## Visión general

El simulador es una **Lambda stateless** que reproduce viajes pre-procesados como si fueran telemetría en tiempo real. Lee un archivo JSON consolidado desde S3, selecciona el frame correspondiente al momento actual para cada bus, y escribe el estado completo en DynamoDB cada 10 segundos.

```
┌──────────────────────┐     ┌─────────────────────────┐     ┌──────────────────┐
│  S3                  │     │  Lambda Simulador       │     │  DynamoDB        │
│                      │     │                         │     │                  │
│  viajes_consolidados │────▶│  1. Lee viajes (cached) │────▶│  ado-telemetria  │
│  .json               │     │  2. Selecciona frame    │     │  -live           │
│                      │     │  3. Valida vs catálogo  │     │                  │
│  motor_spn.json      │────▶│  4. Clasifica consumo   │     │  PK: autobus     │
│  (catálogo SPN)      │     │  5. Batch write ×6 ticks│     │  SK: timestamp   │
└──────────────────────┘     └─────────────────────────┘     └──────────────────┘
                                       ▲
                                       │ rate(1 minute)
                              ┌────────┴────────┐
                              │  EventBridge     │
                              │  Scheduler       │
                              └─────────────────┘
```

---

## Mecanismo de burst (resolución de 10 segundos)

EventBridge Scheduler tiene un mínimo de 1 minuto. Para lograr resolución de 10 segundos:

- El scheduler dispara la Lambda **1 vez por minuto**
- La Lambda genera **6 ticks** por invocación (configurable via `BURST_COUNT`)
- Cada tick está separado por **10 segundos** (configurable via `TICK_INTERVAL`)
- 6 ticks × 10s = 60s → cubre el minuto completo

**Resultado:** DynamoDB tiene registros cada 10 segundos aunque la Lambda solo corre cada minuto.

```
Minuto 0:00 → Lambda genera ticks para: 0:00, 0:10, 0:20, 0:30, 0:40, 0:50
Minuto 1:00 → Lambda genera ticks para: 1:00, 1:10, 1:20, 1:30, 1:40, 1:50
...
```

---

## Variables de entorno

| Variable | Default | Descripción |
|---|---|---|
| `S3_BUCKET` | `ado-telemetry-mvp` | Bucket donde están los viajes y el catálogo |
| `S3_VIAJES_KEY` | `hackathon-data/simulacion/viajes_consolidados.json` | Ruta al JSON de viajes |
| `S3_CATALOGO_KEY` | `hackathon-data/catalogo/motor_spn.json` | Ruta al catálogo SPN |
| `DYNAMODB_TABLE` | `ado-telemetria-live` | Tabla destino en DynamoDB |
| `STEP_SECONDS` | `30` | Segundos de viaje que avanza cada tick. Controla el speedup. |
| `TICK_INTERVAL` | `10` | Segundos reales entre cada tick del burst |
| `BURST_COUNT` | `6` | Cantidad de ticks por invocación |
| `DESFASE_PCT` | `15` | Porcentaje de desfase entre buses (0-100) |

### Fórmula de speedup

```
speedup = STEP_SECONDS / TICK_INTERVAL
```

| STEP_SECONDS | TICK_INTERVAL | Speedup | Viaje de 5h dura... |
|---|---|---|---|
| `10` | `10` | 1x (tiempo real) | 5 horas |
| `30` | `10` | 3x | ~1.7 horas |
| `100` | `10` | 10x | 30 minutos |
| `300` | `10` | 30x | 10 minutos |
| `1800` | `10` | 180x | ~1.7 minutos |

---

## Selección de frame (stateless)

El simulador **no guarda estado** entre invocaciones. Usa el reloj del sistema (`time.time()`) para calcular determinísticamente qué frame le toca a cada bus:

```python
# Desfase por bus (para que no vayan todos juntos)
desfase_segundos = duracion_viaje * (DESFASE_PCT / 100) * bus_index

# Posición en el viaje (con speedup)
elapsed = (unix_timestamp * STEP_SECONDS // TICK_INTERVAL) + desfase_segundos
posicion_en_viaje = elapsed % duracion_viaje  # loop infinito

# Binary search para encontrar el frame más cercano
frame = binary_search(frames, posicion_en_viaje)
```

**Consecuencias:**
- Los viajes se reproducen en **loop infinito** — al llegar al final, reinician
- Cada bus tiene un **desfase** para que no estén todos en la misma posición
- Si la Lambda se reinicia (cold start), retoma exactamente donde debería estar
- Con speedup bajo (1x), varios ticks consecutivos pueden caer en el mismo frame

---

## Formato de entrada: `viajes_consolidados.json`

Este es el archivo que la Lambda lee de S3. Contiene todos los viajes pre-procesados listos para reproducir.

### Estructura raíz

```json
{
  "viajes": [ ... ],
  "metadata": {
    "total_viajes": 3,
    "spns_disponibles": [84, 91, 96, 100, 110, ...],
    "total_spns": 27,
    "generado": "2026-04-28T12:00:00Z"
  }
}
```

### Estructura de un viaje

```json
{
  "viaje_id": 2704712,
  "autobus": "7331",
  "operador_cve": "OP-1042",
  "operador_desc": "GARCIA VALENTIN JULIO",
  "viaje_ruta": "MEXICO TAXQUENA - ACAPULCO COSTERA",
  "viaje_ruta_origen": "MEXICO TAXQUENA",
  "viaje_ruta_destino": "ACAPULCO COSTERA",
  "total_frames": 2349,
  "duracion_segundos": 17995,
  "frames": [ ... ]
}
```

| Campo | Tipo | Requerido | Descripción |
|---|---|---|---|
| `viaje_id` | int | ✅ | Identificador único del viaje |
| `autobus` | string | ✅ | Número económico del bus (se usa como PK en DynamoDB) |
| `operador_cve` | string | ✅ | Clave del conductor |
| `operador_desc` | string | ✅ | Nombre del conductor |
| `viaje_ruta` | string | ✅ | Nombre completo de la ruta |
| `viaje_ruta_origen` | string | ✅ | Ciudad/terminal de origen |
| `viaje_ruta_destino` | string | ✅ | Ciudad/terminal de destino |
| `total_frames` | int | ✅ | Cantidad de frames en el viaje |
| `duracion_segundos` | int | ✅ | Duración total del viaje en segundos |
| `frames` | array | ✅ | Lista ordenada de frames (snapshots temporales) |

### Estructura de un frame

```json
{
  "offset": 0,
  "segundos_desde_inicio": 0,
  "latitud": 19.342700,
  "longitud": -99.123400,
  "spn_valores": {
    "84":  {"valor": 45.2,  "name": "Velocidad Km/h",           "unidad": "km/h"},
    "190": {"valor": 1200.0,"name": "RPM",                      "unidad": "rpm"},
    "91":  {"valor": 35.0,  "name": "Posición Pedal Acelerador","unidad": "%"},
    "110": {"valor": 88.5,  "name": "Temperatura Motor",        "unidad": "°C"},
    "185": {"valor": 3.2,   "name": "Rendimiento",              "unidad": "km/L"}
  }
}
```

| Campo | Tipo | Requerido | Descripción |
|---|---|---|---|
| `offset` | int | ✅ | Índice secuencial del frame (0, 1, 2...) |
| `segundos_desde_inicio` | int | ✅ | Segundos transcurridos desde el inicio del viaje. **Debe estar ordenado ascendentemente.** |
| `latitud` | float | ✅ | Coordenada GPS (6 decimales recomendado) |
| `longitud` | float | ✅ | Coordenada GPS (6 decimales recomendado) |
| `spn_valores` | object | ✅ | Mapa de SPN ID (string) → valores del sensor |

### Estructura de un valor SPN

```json
{
  "valor": 88.5,
  "name": "Temperatura Motor",
  "unidad": "°C"
}
```

| Campo | Tipo | Requerido | Descripción |
|---|---|---|---|
| `valor` | float | ✅ | Valor numérico de la lectura |
| `name` | string | ✅ | Nombre legible del sensor |
| `unidad` | string | ✅ | Unidad de medida |

---

## SPNs esperados por el simulador

El simulador procesa **cualquier SPN** presente en `spn_valores`, pero los siguientes son los que se mapean a campos planos en DynamoDB y son consumidos por el dashboard y los agentes:

### SPNs de conducción y combustible (Agente Combustible)

| SPN ID | Campo plano en DynamoDB | Nombre | Unidad | Rango normal |
|---|---|---|---|---|
| `84` | `velocidad_kmh` | Velocidad | km/h | 0–120 |
| `190` | `rpm` | RPM | rpm | 0–3000 |
| `91` | `pct_acelerador` | Posición Pedal Acelerador | % | 0–100 |
| `521` | `pct_freno` | Posición Pedal Freno | % | 0–100 |
| `183` | `tasa_combustible_lh` | Tasa de combustible | L/h | 0–100 |
| `185` | `rendimiento_kml` | Rendimiento | km/L | 0–50 |
| `184` | `ahorro_instantaneo_kml` | Ahorro instantáneo | km/L | 0–50 |
| `96` | `nivel_combustible_pct` | Nivel Combustible | % | 0–120 |
| `513` | `torque_pct` | Porcentaje Torque | % | 0–100 |

### SPNs de mantenimiento (Agente Mantenimiento)

| SPN ID | Campo plano en DynamoDB | Nombre | Unidad | Rango normal |
|---|---|---|---|---|
| `110` | `temperatura_motor_c` | Temperatura Motor | °C | 0–150 |
| `175` | `temperatura_aceite_c` | Temperatura Aceite | °C | 0–150 |
| `100` | `presion_aceite_kpa` | Presión Aceite Motor | kPa | 0–1000 |
| `98` | `nivel_aceite_pct` | Nivel de Aceite | % | 0–110 |
| `111` | `nivel_anticongelante_pct` | Nivel Anticongelante | % | 0–110 |
| `168` | `voltaje_bateria_v` | Voltaje Batería | V | 0–36 |
| `917` | `odometro_km` | Odómetro | km | acumulador |
| `247` | `horas_motor_h` | Horas Motor | h | acumulador |
| `1761` | `nivel_urea_pct` | Nivel Urea | % | 0–100 |

### SPNs de balatas (frenos)

| SPN ID | Campo plano en DynamoDB | Nombre | Unidad | Rango normal |
|---|---|---|---|---|
| `1099` | `balata_del_izq_pct` | Balata delantero izquierdo | % | 0–100 |
| `1100` | `balata_del_der_pct` | Balata delantero derecho | % | 0–100 |
| `1101` | `balata_tras_izq1_pct` | Balata trasero izquierdo 1 | % | 0–100 |
| `1102` | `balata_tras_der1_pct` | Balata trasero derecho 1 | % | 0–100 |
| `1103` | `balata_tras_izq2_pct` | Balata trasero izquierdo 2 | % | 0–100 |
| `1104` | `balata_tras_der2_pct` | Balata trasero derecho 2 | % | 0–100 |

---

## Clasificación de consumo

La Lambda clasifica automáticamente el estado de consumo de cada bus usando esta lógica (prioridad: SPN 185 > SPN 183):

| Estado | SPN 185 (Rendimiento km/L) | SPN 183 (Tasa L/h) |
|---|---|---|
| `EFICIENTE` | ≥ 3.0 | ≤ 30 |
| `ALERTA_MODERADA` | 2.0 – 3.0 | 30 – 50 |
| `ALERTA_SIGNIFICATIVA` | < 2.0 | > 50 |
| `SIN_DATOS` | — | — |

---

## Validación fuera de rango

Cada valor SPN se valida contra el catálogo `motor_spn.json`. Si el valor está fuera del rango `[minimo, maximo]`, se marca como `fuera_de_rango: true` y se agrega a la lista `alertas_spn` del registro en DynamoDB.

---

## Desfase entre buses

Para que los buses no estén todos en la misma posición de la ruta:

```
Bus 0: inicia en 0% del viaje
Bus 1: inicia en DESFASE_PCT% del viaje (ej: 15% = ~45 min en viaje de 5h)
Bus 2: inicia en 2×DESFASE_PCT% del viaje
...
```

Con `DESFASE_PCT=10` y un viaje de 18,000 segundos:
- Bus 0: offset 0s
- Bus 1: offset 1,800s (30 min)
- Bus 2: offset 3,600s (1 hora)

---

## Qué escribe en DynamoDB

Cada tick genera un item por bus con esta estructura:

```json
{
  "autobus": "7331",
  "timestamp": "2026-04-28T16:25:12.479910+00:00",
  "viaje_id": 2704712,
  "operador_cve": "OP-1042",
  "operador_desc": "GARCIA VALENTIN JULIO",
  "viaje_ruta": "MEXICO TAXQUENA - ACAPULCO COSTERA",
  "viaje_ruta_origen": "MEXICO TAXQUENA",
  "viaje_ruta_destino": "ACAPULCO COSTERA",
  "latitud": 19.342700,
  "longitud": -99.123400,
  "velocidad_kmh": 45.2,
  "rpm": 1200.0,
  "temperatura_motor_c": 88.5,
  "rendimiento_kml": 3.2,
  "spn_valores": { ... },
  "alertas_spn": [ ... ],
  "estado_consumo": "EFICIENTE",
  "ttl_expiry": 1777479312
}
```

**Volumen por invocación:** `BURST_COUNT × número_de_viajes` items.
Ejemplo: 6 ticks × 10 viajes = 60 items por minuto.

---

## Guía para generar nuevos viajes

### Requisitos mínimos

1. **Cada viaje debe tener un `autobus` único** — es la partition key en DynamoDB
2. **Los frames deben estar ordenados** por `segundos_desde_inicio` ascendente
3. **Incluir GPS realista** — latitud/longitud que formen una ruta geográfica coherente
4. **Incluir al menos los SPNs 84, 185 y 110** — son los mínimos para que el dashboard y los agentes funcionen
5. **`duracion_segundos`** debe coincidir con el último `segundos_desde_inicio`

### Resolución temporal recomendada

- **Ideal:** 1 frame cada 7-10 segundos (coincide con `TICK_INTERVAL=10`)
- **Mínimo aceptable:** 1 frame cada 30 segundos
- **Máximo práctico:** 1 frame cada 3 segundos (genera archivos muy grandes)

Con resolución de 8 segundos y un viaje de 5 horas: ~2,250 frames por viaje.

### Cómo inyectar anomalías para la demo

Para que los agentes de IA detecten problemas, incluye frames con valores fuera de rango:

```json
{
  "offset": 500,
  "segundos_desde_inicio": 4000,
  "latitud": 18.5,
  "longitud": -99.3,
  "spn_valores": {
    "84":  {"valor": 135.0, "name": "Velocidad Km/h",     "unidad": "km/h"},
    "110": {"valor": 155.0, "name": "Temperatura Motor",  "unidad": "°C"},
    "185": {"valor": 1.5,   "name": "Rendimiento",        "unidad": "km/L"},
    "100": {"valor": 50.0,  "name": "Presión Aceite Motor","unidad": "kPa"}
  }
}
```

Esto generará:
- `estado_consumo: ALERTA_SIGNIFICATIVA` (rendimiento < 2.0)
- `alertas_spn` con velocidad > 120, temperatura > 150, presión baja
- Los agentes de AgentCore detectarán estas señales y generarán recomendaciones

### Datos trampa sugeridos por bus

| Bus | Comportamiento | SPNs afectados |
|---|---|---|
| Bus "normal" | Todo en rango, eficiente | Ninguno fuera de rango |
| Bus "consumo alto" | Aceleración brusca, bajo rendimiento | 91 alto, 185 bajo, 183 alto |
| Bus "riesgo mecánico" | Temperatura elevada, presión baja | 110 alto, 100 bajo, 175 alto |
| Bus "frenos desgastados" | Balatas bajas | 1099-1104 < 20% |
| Bus "eléctrico" | Voltaje bajo | 168 < 22V |

### Script de referencia

El script `scripts/preprocess_sample_trips.py` muestra cómo convertir datos Parquet en el formato esperado. Para generar viajes sintéticos, replica la misma estructura de salida:

```python
viaje = {
    "viaje_id": 9000001,
    "autobus": "SIM-001",
    "operador_cve": "OP-SIM-01",
    "operador_desc": "CONDUCTOR SIMULADO",
    "viaje_ruta": "MEXICO TAXQUENA - ACAPULCO COSTERA",
    "viaje_ruta_origen": "MEXICO TAXQUENA",
    "viaje_ruta_destino": "ACAPULCO COSTERA",
    "total_frames": len(frames),
    "duracion_segundos": frames[-1]["segundos_desde_inicio"],
    "frames": frames,
}
```

### Ubicación en S3

```
s3://ado-telemetry-mvp/hackathon-data/simulacion/viajes_consolidados.json
```

Al subir un nuevo archivo, la Lambda lo cargará automáticamente en la siguiente invocación cold start (o al reciclar la instancia).

---

## Recursos AWS relacionados

| Recurso | Valor |
|---|---|
| Lambda | `ado-simulador-telemetria` |
| Scheduler | `ado-simulador-demo` (rate 1 minute) |
| Tabla DynamoDB | `ado-telemetria-live` |
| Bucket S3 | `ado-telemetry-mvp` |
| Layer | `ado-common-layer:2` |
| Región | `us-east-2` |
| Timeout | 60 segundos |
| Runtime | Python 3.12 |
