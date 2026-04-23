---
inclusion: always
---

# 🗄️ Esquema de Datos — ADO Intelligence Platform MVP

> Fuente de verdad para todos los esquemas de tablas, estructuras S3 y formatos de datos del proyecto.
> Cualquier Lambda, agente o dashboard debe respetar estos esquemas.

---

## S3 — Estructura del bucket

```
s3://ado-intelligence-mvp/
├── telemetria-historica/
│   └── {YYYY-MM}/
│       └── {bus_id}/
│           └── telemetria_{bus_id}_{YYYY-MM-DD}.parquet
├── fallas-historicas/
│   └── fallas_historicas_flota.parquet
├── knowledge-base/
│   └── docs/
│       ├── umbrales-consumo-rutas.csv
│       ├── codigos-obd-relevantes.pdf
│       ├── historial-fallas-resumen.csv
│       ├── normas-conduccion-eficiente.pdf
│       └── nom-044-resumen.pdf
└── modelos/
    └── sagemaker/
        └── training-data/
            └── features_fallas.parquet
```

---

## Esquema: Telemetría histórica (S3 Parquet)

Archivo fuente migrado desde GCP. Un registro por lectura de sensor (~cada 30 segundos por bus).

| Campo | Tipo | Descripción | Ejemplo |
|---|---|---|---|
| `bus_id` | STRING | Identificador único del bus | `BUS-247` |
| `conductor_id` | STRING | Identificador del conductor | `COND-1042` |
| `ruta_id` | STRING | Identificador de la ruta | `RUTA-MEX-PUE` |
| `timestamp_utc` | TIMESTAMP | Fecha y hora UTC de la lectura | `2025-11-15T14:32:00Z` |
| `latitud` | FLOAT | Coordenada GPS latitud | `19.4326` |
| `longitud` | FLOAT | Coordenada GPS longitud | `-99.1332` |
| `velocidad_kmh` | FLOAT | Velocidad en km/h | `87.5` |
| `rpm` | INTEGER | Revoluciones por minuto del motor | `1850` |
| `consumo_lkm` | FLOAT | Consumo instantáneo en litros/km | `0.42` |
| `temperatura_motor_c` | FLOAT | Temperatura del motor en °C | `92.3` |
| `presion_aceite_psi` | FLOAT | Presión de aceite en PSI | `45.0` |
| `pct_acelerador` | FLOAT | % apertura del acelerador (0-100) | `35.2` |
| `pct_freno` | FLOAT | % uso del freno (0-100) | `12.1` |
| `odometro_km` | FLOAT | Kilómetros totales del odómetro | `187432.5` |
| `codigo_obd` | STRING | Código OBD activo (null si ninguno) | `P0217` |
| `nivel_combustible_pct` | FLOAT | % de combustible en tanque | `68.0` |

---

## Esquema: Fallas históricas (S3 Parquet)

Historial de mantenimientos correctivos y preventivos de la flota.

| Campo | Tipo | Descripción | Ejemplo |
|---|---|---|---|
| `falla_id` | STRING | Identificador único de la falla | `FALLA-2025-08-001` |
| `bus_id` | STRING | Bus afectado | `BUS-089` |
| `fecha_deteccion` | DATE | Fecha en que se detectó la falla | `2025-08-12` |
| `fecha_reparacion` | DATE | Fecha en que se reparó | `2025-08-14` |
| `codigo_obd_previo` | STRING | Código OBD activo días antes de la falla | `P0217` |
| `temperatura_previa_c` | FLOAT | Temperatura promedio 7 días antes | `104.5` |
| `presion_aceite_previa` | FLOAT | Presión de aceite promedio 7 días antes | `18.2` |
| `componente_fallado` | STRING | Componente que falló | `bomba_agua` |
| `descripcion_falla` | STRING | Descripción técnica de la falla | `Falla de bomba de agua por sobrecalentamiento` |
| `costo_reparacion_mxn` | FLOAT | Costo total de la reparación en MXN | `18500.00` |
| `horas_fuera_servicio` | FLOAT | Horas que el bus estuvo fuera de servicio | `36.5` |
| `tipo_mantenimiento` | STRING | `CORRECTIVO` o `PREVENTIVO` | `CORRECTIVO` |
| `dias_desde_ultimo_mant` | INTEGER | Días desde el último mantenimiento | `45` |
| `km_desde_ultimo_mant` | FLOAT | Km desde el último mantenimiento | `12400.0` |

---

## DynamoDB — Tabla: `ado-telemetria-live`

Estado en tiempo real de la flota. Escrita por Lambda simulador, leída por los agentes.

- **Partition Key (PK):** `bus_id` (String)
- **Sort Key (SK):** `timestamp` (String — ISO 8601: `2026-04-22T14:32:00.000Z`)
- **TTL:** `ttl_expiry` — registros expiran automáticamente después de 24 horas

| Atributo | Tipo | Descripción |
|---|---|---|
| `bus_id` | S | PK — Identificador del bus |
| `timestamp` | S | SK — Timestamp ISO 8601 |
| `conductor_id` | S | Conductor activo |
| `ruta_id` | S | Ruta activa |
| `velocidad_kmh` | N | Velocidad actual |
| `rpm` | N | RPM actual |
| `consumo_lkm` | N | Consumo instantáneo L/km |
| `temperatura_motor_c` | N | Temperatura motor °C |
| `presion_aceite_psi` | N | Presión aceite PSI |
| `pct_acelerador` | N | % acelerador |
| `pct_freno` | N | % freno |
| `odometro_km` | N | Odómetro actual |
| `codigo_obd` | S | Código OBD activo (vacío si ninguno) |
| `nivel_combustible_pct` | N | % combustible en tanque |
| `estado_consumo` | S | `EFICIENTE`, `ALERTA_AMARILLA`, `ALERTA_ROJA` |
| `ttl_expiry` | N | Unix timestamp de expiración (now + 86400) |

**Índice secundario global (GSI):**
- `ruta_id-timestamp-index`: para consultar todos los buses activos en una ruta

---

## DynamoDB — Tabla: `ado-alertas`

Registro de alertas y órdenes de trabajo generadas por los agentes.

- **Partition Key (PK):** `alerta_id` (String — UUID v4)
- **Sort Key (SK):** `timestamp` (String — ISO 8601)

| Atributo | Tipo | Descripción |
|---|---|---|
| `alerta_id` | S | PK — UUID único |
| `timestamp` | S | SK — Timestamp de creación |
| `bus_id` | S | Bus relacionado |
| `tipo_alerta` | S | `COMBUSTIBLE` o `MANTENIMIENTO` |
| `nivel` | S | `VERDE`, `AMARILLO`, `ROJO` |
| `titulo` | S | Título corto de la alerta |
| `descripcion` | S | Descripción completa generada por el agente |
| `probabilidad_falla` | N | Solo para MANTENIMIENTO (0.0 - 1.0) |
| `ahorro_estimado_mxn` | N | Solo para COMBUSTIBLE |
| `urgencia` | S | `INMEDIATA`, `ESTA_SEMANA`, `PROXIMO_SERVICIO` |
| `componentes` | L | Lista de componentes a revisar (solo MANTENIMIENTO) |
| `numero_ot` | S | Número de orden de trabajo (solo MANTENIMIENTO) |
| `estado` | S | `ACTIVA`, `EN_PROCESO`, `RESUELTA` |
| `agente_origen` | S | `ado-agente-combustible` o `ado-agente-mantenimiento` |

---

## Esquema: Features para modelo SageMaker

Dataset de entrenamiento para el modelo de predicción de fallas.

| Feature | Tipo | Descripción |
|---|---|---|
| `temperatura_motor_avg_7d` | FLOAT | Temperatura promedio últimos 7 días |
| `temperatura_motor_max_7d` | FLOAT | Temperatura máxima últimos 7 días |
| `presion_aceite_avg_7d` | FLOAT | Presión de aceite promedio últimos 7 días |
| `presion_aceite_min_7d` | FLOAT | Presión de aceite mínima últimos 7 días |
| `tiene_codigo_obd` | INTEGER | 1 si hay código OBD activo, 0 si no |
| `codigo_obd_categoria` | INTEGER | Categoría del código (0=ninguno, 1=motor, 2=transmisión, 3=frenos, 4=otro) |
| `rpm_avg_7d` | FLOAT | RPM promedio últimos 7 días |
| `km_desde_ultimo_mant` | FLOAT | Kilómetros desde último mantenimiento |
| `dias_desde_ultimo_mant` | INTEGER | Días desde último mantenimiento |
| `pct_freno_avg_7d` | FLOAT | % uso de freno promedio últimos 7 días |
| `edad_bus_años` | FLOAT | Antigüedad del bus en años |
| **`falla_14_dias`** | INTEGER | **TARGET**: 1 si falló en los próximos 14 días, 0 si no |

---

## Umbrales de consumo por ruta (referencia)

Valores de referencia para el cálculo de desviaciones. Cargar en Knowledge Base.

| ruta_id | descripcion | consumo_base_lkm | tolerancia_pct |
|---|---|---|---|
| `RUTA-MEX-PUE` | México - Puebla | 0.38 | 5 |
| `RUTA-MEX-GDL` | México - Guadalajara | 0.41 | 5 |
| `RUTA-MEX-MTY` | México - Monterrey | 0.44 | 5 |
| `RUTA-VER-MEX` | Veracruz - México | 0.40 | 5 |
| `RUTA-MEX-OAX` | México - Oaxaca | 0.45 | 7 |
| `RUTA-MEX-QRO` | México - Querétaro | 0.36 | 5 |
| `RUTA-MEX-CUN` | México - Cancún | 0.47 | 7 |
