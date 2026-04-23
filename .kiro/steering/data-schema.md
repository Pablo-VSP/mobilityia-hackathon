---
inclusion: always
---

# 🗄️ Esquema de Datos — ADO MobilityIA MVP
## Hackathon AWS Builders League 2026

> Fuente de verdad para todos los esquemas de tablas, estructuras S3 y formatos de datos.
> **C-004:** Todos los datos son **simulados** — generados por script Python, no datos reales de ADO.
> **C-003:** Los valores de referencia en este esquema son para uso interno del sistema. Las respuestas al usuario usan lenguaje difuso.

---

## S3 — Estructura del bucket

```
s3://ado-mobilityia-mvp/
├── telemetria-simulada/
│   └── {YYYY-MM}/
│       └── {bus_id}/
│           └── telemetria_{bus_id}_{YYYY-MM-DD}.parquet
├── fallas-simuladas/
│   └── eventos_mecanicos_simulados.parquet
├── knowledge-base/
│   └── docs/
│       ├── umbrales-consumo-rutas.csv
│       ├── codigos-obd-relevantes.pdf
│       ├── patrones-eventos-simulados.csv
│       ├── normas-conduccion-eficiente.pdf
│       └── nom-044-resumen.pdf
└── modelos/
    └── sagemaker/
        └── training-data/
            └── features_eventos_simulados.parquet
```

---

## Esquema: Telemetría simulada (S3 Parquet)

Generado por script Python. Un registro por lectura de sensor simulada (~cada 30 segundos por bus).

| Campo | Tipo | Descripción | Ejemplo |
|---|---|---|---|
| `bus_id` | STRING | ID del bus simulado | `BUS-SIM-247` |
| `conductor_id` | STRING | ID del conductor simulado | `COND-SIM-1042` |
| `ruta_id` | STRING | ID de la ruta | `RUTA-MEX-PUE` |
| `timestamp_utc` | TIMESTAMP | Fecha y hora UTC de la lectura simulada | `2025-11-15T14:32:00Z` |
| `latitud` | FLOAT | Coordenada GPS simulada | `19.4326` |
| `longitud` | FLOAT | Coordenada GPS simulada | `-99.1332` |
| `velocidad_kmh` | FLOAT | Velocidad simulada en km/h | `87.5` |
| `rpm` | INTEGER | RPM simuladas | `1850` |
| `consumo_lkm` | FLOAT | Consumo simulado en litros/km | `0.42` |
| `temperatura_motor_c` | FLOAT | Temperatura simulada en °C | `92.3` |
| `presion_aceite_psi` | FLOAT | Presión de aceite simulada en PSI | `45.0` |
| `pct_acelerador` | FLOAT | % acelerador simulado (0-100) | `35.2` |
| `pct_freno` | FLOAT | % freno simulado (0-100) | `12.1` |
| `odometro_km` | FLOAT | Odómetro simulado en km | `187432.5` |
| `codigo_obd` | STRING | Código OBD simulado (null si ninguno) | `P0217` |
| `nivel_combustible_pct` | FLOAT | % combustible simulado | `68.0` |

---

## Esquema: Eventos mecánicos simulados (S3 Parquet)

Historial de eventos de mantenimiento generado sintéticamente.

| Campo | Tipo | Descripción | Ejemplo |
|---|---|---|---|
| `evento_id` | STRING | ID único del evento simulado | `EVT-SIM-2025-08-001` |
| `bus_id` | STRING | Bus simulado afectado | `BUS-SIM-089` |
| `fecha_deteccion` | DATE | Fecha simulada de detección | `2025-08-12` |
| `fecha_resolucion` | DATE | Fecha simulada de resolución | `2025-08-14` |
| `codigo_obd_previo` | STRING | Código OBD activo días antes | `P0217` |
| `temperatura_previa_c` | FLOAT | Temperatura promedio 7 días antes | `104.5` |
| `presion_aceite_previa` | FLOAT | Presión de aceite promedio 7 días antes | `18.2` |
| `componente_afectado` | STRING | Componente simulado afectado | `bomba_agua` |
| `descripcion_evento` | STRING | Descripción técnica simulada | `Evento de refrigeración por temperatura elevada` |
| `tipo_mantenimiento` | STRING | `CORRECTIVO` o `PREVENTIVO` | `CORRECTIVO` |
| `dias_desde_ultimo_mant` | INTEGER | Días desde último mantenimiento simulado | `45` |
| `km_desde_ultimo_mant` | FLOAT | Km desde último mantenimiento simulado | `12400.0` |

---

## DynamoDB — Tabla: `ado-telemetria-live`

Estado en tiempo real de la flota simulada. Escrita por Lambda simulador, leída por los agentes.

- **PK:** `bus_id` (String) — ej: `BUS-SIM-247`
- **SK:** `timestamp` (String ISO 8601)
- **TTL:** `ttl_expiry` — expira en 24 horas

| Atributo | Tipo | Descripción |
|---|---|---|
| `bus_id` | S | PK — ID del bus simulado |
| `timestamp` | S | SK — Timestamp ISO 8601 |
| `conductor_id` | S | Conductor simulado activo |
| `ruta_id` | S | Ruta activa |
| `velocidad_kmh` | N | Velocidad actual simulada |
| `rpm` | N | RPM actual simulado |
| `consumo_lkm` | N | Consumo instantáneo simulado |
| `temperatura_motor_c` | N | Temperatura motor simulada |
| `presion_aceite_psi` | N | Presión aceite simulada |
| `pct_acelerador` | N | % acelerador simulado |
| `pct_freno` | N | % freno simulado |
| `odometro_km` | N | Odómetro simulado |
| `codigo_obd` | S | Código OBD simulado (vacío si ninguno) |
| `nivel_combustible_pct` | N | % combustible simulado |
| `estado_consumo` | S | `EFICIENTE`, `ALERTA_MODERADA`, `ALERTA_SIGNIFICATIVA` |
| `ttl_expiry` | N | Unix timestamp de expiración |

**GSI:** `ruta_id-timestamp-index`

---

## DynamoDB — Tabla: `ado-alertas`

Recomendaciones y alertas generadas por los agentes.

- **PK:** `alerta_id` (String UUID)
- **SK:** `timestamp` (String ISO 8601)

| Atributo | Tipo | Descripción |
|---|---|---|
| `alerta_id` | S | PK — UUID único |
| `timestamp` | S | SK — Timestamp de creación |
| `bus_id` | S | Bus simulado relacionado |
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

## Esquema: Features para modelo SageMaker (datos simulados)

| Feature | Tipo | Descripción |
|---|---|---|
| `temperatura_motor_avg_7d` | FLOAT | Temperatura promedio últimos 7 días (simulado) |
| `temperatura_motor_max_7d` | FLOAT | Temperatura máxima últimos 7 días (simulado) |
| `presion_aceite_avg_7d` | FLOAT | Presión de aceite promedio últimos 7 días (simulado) |
| `presion_aceite_min_7d` | FLOAT | Presión de aceite mínima últimos 7 días (simulado) |
| `tiene_codigo_obd` | INTEGER | 1 si hay código OBD activo, 0 si no |
| `codigo_obd_categoria` | INTEGER | 0=ninguno, 1=motor, 2=transmisión, 3=frenos, 4=otro |
| `rpm_avg_7d` | FLOAT | RPM promedio últimos 7 días (simulado) |
| `km_desde_ultimo_mant` | FLOAT | Km desde último mantenimiento (simulado) |
| `dias_desde_ultimo_mant` | INTEGER | Días desde último mantenimiento (simulado) |
| `pct_freno_avg_7d` | FLOAT | % uso de freno promedio últimos 7 días (simulado) |
| `edad_bus_años` | FLOAT | Antigüedad simulada del bus en años |
| **`evento_14_dias`** | INTEGER | **TARGET**: 1 si hubo evento en los próximos 14 días, 0 si no |

---

## Rutas simuladas de referencia

| ruta_id | descripcion | consumo_base_lkm |
|---|---|---|
| `RUTA-MEX-PUE` | México - Puebla | 0.38 |
| `RUTA-MEX-GDL` | México - Guadalajara | 0.41 |
| `RUTA-MEX-MTY` | México - Monterrey | 0.44 |
| `RUTA-VER-MEX` | Veracruz - México | 0.40 |
| `RUTA-MEX-OAX` | México - Oaxaca | 0.45 |
| `RUTA-MEX-QRO` | México - Querétaro | 0.36 |
| `RUTA-MEX-CUN` | México - Cancún | 0.47 |

> Nota: estos valores son de referencia interna para el sistema. Las respuestas de los agentes al usuario no deben mencionar estos valores numéricos (C-003).
