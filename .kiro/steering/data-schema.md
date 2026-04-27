---
inclusion: always
---

# 🗄️ Esquema de Datos — ADO MobilityIA MVP
## Hackathon AWS Builders League 2026

> Fuente de verdad para todos los esquemas de tablas, estructuras S3 y formatos de datos.
> **C-004:** Todos los datos son **simulados** — generados por script Python, no datos reales de ADO.
> **C-003:** Los valores de referencia en este esquema son para uso interno del sistema. Las respuestas al usuario usan lenguaje difuso.
> **C-005:** Los agentes son de **AgentCore**, no de Bedrock Agents clásico.
> **C-006:** Esquemas alineados con los archivos reales en `models/`.

---

## S3 — Estructura del bucket

```
s3://ado-telemetry-mvp/hackathon-data/
├── raw/
│   ├── travel_telemetry/                 ← 1,339 archivos Parquet (~447 MB)
│   │   └── travel_telemetry_000000000000.parquet ... 
│   ├── data_fault/                       ← 123 archivos Parquet (~6.5 MB)
│   │   └── data_fault_000000000000.parquet ...
│   └── motor_spn/                        ← 1 archivo Parquet (~3.6 KB)
│       └── motor_spn_000000000000.parquet
├── catalogo/                             ← Catálogo SPN en JSON (para Lambdas)
│   └── motor_spn.json
├── knowledge-base/
│   └── docs/
│       ├── motor_spn.json                ← Catálogo SPN para RAG
│       ├── codigos-falla-catalogo.csv    ← Catálogo de fallas con severidad_inferencia
│       ├── manual-reglas-mantenimiento-motor.md  ← (compañero de equipo)
│       ├── manual-combustible.md         ← (compañero de equipo)
│       ├── normas-conduccion-eficiente.pdf
│       └── nom-044-resumen.pdf
└── modelos/
    └── sagemaker/
        └── training-data/
            └── features_eventos_simulados.parquet
```

> **Nota:** El bucket real es `ado-telemetry-mvp` en `us-east-2`, profile `mobilityadods`. Los datos raw ya están subidos.

---

## Esquema: Telemetría simulada — `telemetry-data` (S3 Parquet)

Cada registro es **una lectura de un sensor SPN específico** en un momento dado. Para reconstruir el estado completo de un bus, hay que agrupar por `autobus` + `evento_fecha_hora` y pivotar los SPNs.

| Campo | Tipo | Descripción | Ejemplo |
|---|---|---|---|
| `viaje_id` | BIGINT | ID del viaje | `12345` |
| `autobus` | BIGINT | Número económico del autobús | `8042` |
| `operador_cve` | STRING | Clave del operador/conductor | `OP-1042` |
| `operador_desc` | STRING | Nombre del operador/conductor | `Juan Pérez` |
| `evento_fecha` | DATE | Fecha del evento | `2026-04-15` |
| `evento_fecha_hora` | TIMESTAMP | Timestamp exacto de la lectura | `2026-04-15T14:32:00Z` |
| `evento_spn` | BIGINT | SPN ID de la variable leída | `110` |
| `evento_descripcion` | STRING | Descripción de la variable | `Temperatura Motor` |
| `evento_valor` | DOUBLE | Valor numérico de la lectura | `92.3` |
| `evento_latitud` | DOUBLE | Coordenada GPS | `19.4326` |
| `evento_longitud` | DOUBLE | Coordenada GPS | `-99.1332` |
| `viaje_ruta` | STRING | Nombre/código de la ruta | `MEX-PUE` |
| `viaje_ruta_origen` | STRING | Ciudad origen | `México` |
| `viaje_ruta_destino` | STRING | Ciudad destino | `Puebla` |
| `evento_protocolo` | STRING | Protocolo de comunicación | `J1939` |
| `evento_firmware` | STRING | Versión de firmware | `v3.2.1` |
| `evento_version` | BIGINT | Versión del evento | `1` |

> **Nota clave:** Un "snapshot" de un bus requiere N registros (uno por cada SPN). La Lambda simulador agrupa por `autobus` + ventana temporal y pivotea los SPNs a columnas para escribir un estado consolidado en DynamoDB.

---

## Esquema: Catálogo SPN — `motor_spn` (S3 JSON)

Catálogo maestro de 36 variables SPN confirmadas. Define rangos normales y umbrales de alerta.

| Campo | Tipo | Descripción | Ejemplo |
|---|---|---|---|
| `id` | BIGINT | SPN ID — se cruza con `evento_spn` | `110` |
| `name` | STRING | Nombre legible de la variable | `Temperatura Motor` |
| `unidad` | STRING | Unidad de medida | `°C` |
| `minimo` | DOUBLE | Valor mínimo esperado (rango normal) | `0.0` |
| `maximo` | DOUBLE | Valor máximo esperado (rango normal) | `150.0` |
| `tipo` | STRING | Tipo de dato (FLOAT, INTEGER) | `FLOAT` |
| `delta` | DOUBLE | Variación esperada entre lecturas consecutivas | `3.0` |
| `variable_tipo` | STRING | `EDA` (tiempo real) o `inicio_fin` (acumulador) | `EDA` |

> **Nota:** Los umbrales de alerta están definidos aquí (`minimo`, `maximo`). Las Lambdas consultan este catálogo en lugar de usar umbrales hardcodeados. El campo `delta` detecta variaciones anómalas (si un valor cambia más de 2× delta, es sospechoso).

---

## Esquema: Fallas y códigos de diagnóstico — `data_fault` (S3 Parquet)

Historial de fallas con contexto operativo: región, marca, modelo, zona, severidad.

| Campo | Tipo | Descripción | Ejemplo |
|---|---|---|---|
| `type` | STRING | Tipo de falla | `DTC` |
| `id` | STRING | ID único del evento de falla | `F-2026-001` |
| `fecha_hora` | TIMESTAMP | Timestamp de la falla | `2026-03-12T08:15:00Z` |
| `autobus` | STRING | Número del autobús | `8042` |
| `region` | STRING | Región operativa | `Centro` |
| `marca_comercial` | STRING | Marca comercial del bus | `ADO` |
| `zona` | STRING | Zona geográfica | `Sureste` |
| `modelo` | STRING | Modelo del bus | `Volvo 9800` |
| `submodelo` | STRING | Submodelo | `DD13` |
| `servicio` | STRING | Tipo de servicio | `Ejecutivo` |
| `anio` | BIGINT | Año del bus | `2020` |
| `conexion` | STRING | Tipo de conexión del dispositivo | `4G` |
| `evento_latitud` | DOUBLE | Coordenada GPS | `19.4326` |
| `evento_longitud` | DOUBLE | Coordenada GPS | `-99.1332` |
| `operador_cve` | BIGINT | Clave del operador | `1042` |
| `codigo` | STRING | Código de falla (equivalente OBD/DTC) | `100` |
| `tipolectura` | STRING | Tipo de lectura | `activa` |
| `contador` | STRING | Contador de ocurrencias | `3` |
| `fecha_hora_fin` | TIMESTAMP | Fin del evento de falla | `2026-03-12T09:30:00Z` |
| `protocolo` | STRING | Protocolo de comunicación | `J1939` |
| `firmware` | STRING | Versión de firmware | `v3.2.1` |
| `severidad` | BIGINT | Nivel de severidad numérico | `3` |
| `source` | STRING | Fuente del dato | `telemetria` |
| `descripcion` | STRING | Descripción de la falla | `Engine oil pressure` |

---

## Catálogo de fallas con severidad inferida — `fault_data_catalog.JSON` (C-007)

Catálogo de códigos de falla con campo `severidad_inferencia` (1=baja, 2=media, 3=alta) asignado a las fallas más relevantes para el modelo predictivo de SageMaker.

### Fallas clasificadas con severidad_inferencia (top 5 por relevancia operativa)

| Código | Descripción | NUM (ocurrencias) | severidad_inferencia | Justificación |
|---|---|---|---|---|
| `100` | Engine oil pressure | 116,188 | 3 (Alta) | Falla más frecuente. Presión de aceite baja causa daño catastrófico al motor. |
| `100` | Engine cylinder #11 knock sensor | 116,188 | 3 (Alta) | Detonación en cilindro indica daño interno inminente. |
| `158` | Battery potential (voltage)-switched | 14,242 | 3 (Alta) | Falla eléctrica afecta todos los sistemas del bus. Alta frecuencia. |
| `86` | Brake torque output axle 3 left | 14,024 | 3 (Alta) | Falla de frenos es riesgo de seguridad crítico. |
| `131` | Exhaust back pressure | 2,727 | 2 (Media) | Contrapresión de escape indica obstrucción en sistema de escape/DPF. |

> **Criterio de clasificación:** Se priorizaron fallas con alta frecuencia (NUM alto) que afectan componentes críticos de seguridad (frenos, motor, sistema eléctrico). Severidad 3 = riesgo de seguridad o daño catastrófico. Severidad 2 = degradación progresiva. Severidad 1 = informativo/menor.

---

## DynamoDB — Tabla: `ado-telemetria-live`

Estado en tiempo real de la flota simulada. Escrita por Lambda simulador (pivoteo de SPNs), leída por los agentes de AgentCore.

- **PK:** `autobus` (String) — número económico del bus
- **SK:** `timestamp` (String ISO 8601)
- **TTL:** `ttl_expiry` — expira en 24 horas

| Atributo | Tipo | Origen | Descripción |
|---|---|---|---|
| `autobus` | S | telemetry-data.autobus | PK — número económico |
| `timestamp` | S | generado (now) | SK — timestamp simulado |
| `viaje_id` | N | telemetry-data.viaje_id | ID del viaje activo |
| `operador_cve` | S | telemetry-data.operador_cve | Clave del conductor |
| `operador_desc` | S | telemetry-data.operador_desc | Nombre del conductor |
| `viaje_ruta` | S | telemetry-data.viaje_ruta | Código de ruta |
| `viaje_ruta_origen` | S | telemetry-data.viaje_ruta_origen | Ciudad origen |
| `viaje_ruta_destino` | S | telemetry-data.viaje_ruta_destino | Ciudad destino |
| `latitud` | N | telemetry-data.evento_latitud | Última coordenada GPS |
| `longitud` | N | telemetry-data.evento_longitud | Última coordenada GPS |
| `spn_valores` | M (Map) | Pivoteo de SPNs | `{spn_id: {valor, name, unidad, fuera_de_rango}}` |
| `alertas_spn` | L (List) | Calculado | Lista de SPNs fuera de rango normal |
| `estado_consumo` | S | Calculado | `EFICIENTE`, `ALERTA_MODERADA`, `ALERTA_SIGNIFICATIVA` |
| `ttl_expiry` | N | Calculado | Unix timestamp + 86400 |

**Campos planos (para queries directos):** `velocidad_kmh`, `rpm`, `pct_acelerador`, `pct_freno`, `tasa_combustible_lh`, `rendimiento_kml`, `nivel_combustible_pct`, `temperatura_motor_c`, `temperatura_aceite_c`, `presion_aceite_kpa`, `nivel_aceite_pct`, `nivel_anticongelante_pct`, `voltaje_bateria_v`, `torque_pct`, `odometro_km`, `horas_motor_h`, `nivel_urea_pct`, `balata_del_izq_pct`, `balata_del_der_pct`, `balata_tras_izq1_pct`, `balata_tras_der1_pct`

**GSI:** `viaje_ruta-timestamp-index` (PK: `viaje_ruta`, SK: `timestamp`)

---

## DynamoDB — Tabla: `ado-alertas`

Recomendaciones y alertas generadas por los agentes de AgentCore.

- **PK:** `alerta_id` (String UUID)
- **SK:** `timestamp` (String ISO 8601)

| Atributo | Tipo | Descripción |
|---|---|---|
| `alerta_id` | S | PK — UUID único |
| `timestamp` | S | SK — Timestamp de creación |
| `autobus` | S | Bus relacionado (número económico) |
| `tipo_alerta` | S | `COMBUSTIBLE` o `MANTENIMIENTO` |
| `nivel` | S | `BAJO`, `MODERADO`, `ELEVADO`, `CRITICO` |
| `titulo` | S | Título corto de la alerta |
| `descripcion` | S | Descripción generada por el agente (lenguaje difuso) |
| `nivel_riesgo_cualitativo` | S | Descripción cualitativa del riesgo |
| `urgencia` | S | `INMEDIATA`, `ESTA_SEMANA`, `PROXIMO_SERVICIO` |
| `componentes` | L | Lista de componentes a revisar |
| `numero_referencia` | S | Número de referencia OT (solo MANTENIMIENTO) |
| `estado` | S | `ACTIVA`, `EN_PROCESO`, `RESUELTA` |
| `agente_origen` | S | `ado-agente-combustible` o `ado-agente-mantenimiento` |

---

## Esquema: Features para modelo SageMaker (C-007 aplicada)

Para cada uno de los 19 SPNs de mantenimiento, se calculan 6 features sobre ventana de 7 días = **114 features de telemetría** + features de historial de fallas + features contextuales.

### Features de telemetría (por SPN de mantenimiento × 6 estadísticos)

| Feature | Descripción |
|---|---|
| `spn_{id}_avg_7d` | Promedio de lecturas en 7 días |
| `spn_{id}_max_7d` | Valor máximo en 7 días |
| `spn_{id}_min_7d` | Valor mínimo en 7 días |
| `spn_{id}_std_7d` | Desviación estándar en 7 días |
| `spn_{id}_oor_count_7d` | Conteo de lecturas fuera de rango (vs catálogo) |
| `spn_{id}_anomaly_count_7d` | Conteo de variaciones anómalas (> 2× delta) |

### Features de historial de fallas

| Feature | Descripción |
|---|---|
| `fallas_ultimos_30d` | Conteo de fallas en últimos 30 días |
| `fallas_ultimos_90d` | Conteo de fallas en últimos 90 días |
| `severidad_max_30d` | Severidad máxima de fallas en últimos 30 días |
| `severidad_inferencia_max_30d` | Severidad inferida máxima (C-007) en últimos 30 días |
| `dias_desde_ultima_falla` | Días desde la última falla |
| `tiene_falla_activa` | 1 si hay código activo, 0 si no |
| `codigos_unicos_90d` | Códigos de falla distintos en 90 días |

### Features contextuales

| Feature | Descripción |
|---|---|
| `km_desde_ultimo_mant` | Diferencia de odómetro desde último mantenimiento |
| `horas_motor_acumuladas` | Último valor de SPN 247 |
| `balata_min_pct` | Mínimo de las 6 balatas |
| `total_spns_fuera_rango` | Conteo total de SPNs fuera de rango |
| `total_anomalias` | Conteo total de variaciones anómalas |

### Variable Target

| Feature | Tipo | Descripción |
|---|---|---|
| **`evento_14_dias`** | INTEGER | **TARGET**: 1 si hubo falla con `severidad_inferencia >= 2` en los próximos 14 días, 0 si no |
