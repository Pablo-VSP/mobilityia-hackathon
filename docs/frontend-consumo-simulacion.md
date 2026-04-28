# 🖥️ Frontend — Consumo de Datos de Simulación
## Contexto para el equipo de frontend de ADO MobilityIA

---

## Veredicto rápido

**El frontend NO necesita cambios para consumir los nuevos datos de simulación.** La interfaz entre el simulador y el frontend (la Lambda `ado-dashboard-api`) no cambió. Los tipos, endpoints y formato de respuesta son idénticos.

Este documento explica cómo fluyen los datos para que el equipo de frontend tenga contexto completo.

---

## Arquitectura del flujo de datos

```
Lambda Simulador                    Lambda Dashboard API              React Frontend
(ado-simulador-telemetria)          (ado-dashboard-api)               (CloudFront)
                                                                      
Cada 1 min (EventBridge):           Cada request del frontend:        Cada 10s (polling):
  Lee viajes de S3                    Scan DynamoDB últimos 10 min      GET /dashboard/flota-status
  Genera 6 ticks × 10 buses          Último registro por bus           Actualiza markers en mapa
  Escribe 60 items a DynamoDB         Traduce SPNs, clasifica          Muestra popups con datos
                                      Retorna JSON al frontend
                                                                      Cada 30s:
                                                                        GET /dashboard/alertas-activas
```

El frontend **nunca habla directamente con el simulador ni con DynamoDB**. Siempre pasa por la Lambda `ado-dashboard-api` via API Gateway.

---

## Qué cambió en el simulador (y qué NO cambió en la API)

### Lo que cambió (backend, transparente para el frontend)

| Aspecto | Antes | Ahora |
|---|---|---|
| Viajes | 10 × 30 frames (gap 600s) | 10 × 300 frames (gap 1s) |
| Duración del loop | ~1.7 min a 180x | 5 min a 1x |
| `STEP_SECONDS` | 1800 | 10 |
| `DESFASE_PCT` | 10 | 0 |
| Movimiento GPS | Saltos grandes cada 10 min | Fluido cada 10s |
| Anomalías | No inyectadas | 2-3 por viaje (visibles) |
| SPNs por frame | ~27 (todos siempre presentes) | 3-11 (varía por frame, realista) |

### Lo que NO cambió (contrato con el frontend)

| Aspecto | Valor | Notas |
|---|---|---|
| Endpoint | `GET /dashboard/flota-status` | Mismo path, misma respuesta |
| Formato de respuesta | `FlotaStatus` con array de `Bus` | Mismo tipo TypeScript |
| Campos por bus | `autobus`, `latitud`, `longitud`, `velocidad_kmh`, `rpm`, `temperatura_motor_c`, `tasa_combustible_lh`, `estado_consumo`, `alertas_spn`, etc. | Mismos campos |
| Polling interval | 10,000 ms | Ya configurado en `config.ts` |
| Auth | JWT Bearer (Cognito) | Sin cambios |

---

## Endpoints que consume el frontend

### 1. `GET /dashboard/flota-status` — Mapa en vivo

**Polling:** cada 10 segundos (`config.polling.fleetIntervalMs`)

**Qué hace la API:**
1. Scan de `ado-telemetria-live` con filtro `timestamp > (now - 10 min)`
2. Agrupa por `autobus`, se queda con el registro más reciente de cada uno
3. Traduce SPNs a nombres legibles usando el catálogo
4. Ordena: `ALERTA_SIGNIFICATIVA` primero, luego por cantidad de SPNs fuera de rango

**Respuesta:**
```json
{
  "total_buses": 10,
  "buses_activos": 10,
  "resumen_por_estado": {
    "EFICIENTE": 7,
    "ALERTA_MODERADA": 2,
    "ALERTA_SIGNIFICATIVA": 1
  },
  "buses": [
    {
      "autobus": "7321",
      "viaje_ruta": "ACAPULCO COSTERA - MEXICO TAXQUENA",
      "viaje_ruta_origen": "ACAPULCO COSTERA",
      "viaje_ruta_destino": "MEXICO TAXQUENA",
      "operador_desc": "SANTIAGO GARCIA OSCAR",
      "estado_consumo": "EFICIENTE",
      "spns_fuera_de_rango": 0,
      "ultimo_timestamp": "2026-04-28T18:15:12+00:00",
      "alertas_spn": [],
      "latitud": 16.928016,
      "longitud": -99.802316,
      "velocidad_kmh": 78.8,
      "rpm": 1150.0,
      "temperatura_motor_c": 92.3,
      "presion_aceite_kpa": 420.0,
      "tasa_combustible_lh": 25.3,
      "nivel_combustible_pct": 72.0
    }
  ]
}
```

**Cómo lo usa el frontend (`MapPage.tsx`):**
- Renderiza un `Marker` de Leaflet por cada bus con GPS válido
- Color del marker según `estado_consumo` (verde/amarillo/rojo)
- Popup al click con velocidad, combustible, temperatura, RPM
- Panel derecho con buses que tienen alertas
- Overlay con contadores: activos, eficientes, en alerta

### 2. `GET /dashboard/alertas-activas` — Alertas de mantenimiento

**Polling:** cada 30 segundos (`config.polling.alertsIntervalMs`)

**Fuente:** Tabla `ado-alertas` (generadas por los agentes de AgentCore, no por el simulador)

**Respuesta:**
```json
{
  "total_alertas": 2,
  "alertas": [
    {
      "alerta_id": "uuid",
      "timestamp": "2026-04-28T18:00:00+00:00",
      "autobus": "7313",
      "tipo_alerta": "MANTENIMIENTO",
      "nivel_riesgo": "ELEVADO",
      "diagnostico": "Señales consistentes con riesgo mecánico...",
      "urgencia": "ESTA_SEMANA",
      "componentes": ["sistema_refrigeracion", "presion_aceite"],
      "numero_referencia": "OT-2026-0428-7313",
      "estado": "ACTIVA",
      "agente_origen": "ado-agente-mantenimiento"
    }
  ]
}
```

### 3. `GET /dashboard/resumen-consumo` — Eficiencia por ruta

**Fuente:** Scan de `ado-telemetria-live` últimos 10 min, agrupado por `viaje_ruta`

**Respuesta:**
```json
{
  "total_rutas": 2,
  "rutas": [
    {
      "viaje_ruta": "MEXICO TAXQUENA - ACAPULCO COSTERA",
      "total_buses": 4,
      "rendimiento_promedio_kml": 3.5,
      "resumen_estados": { "EFICIENTE": 3, "ALERTA_MODERADA": 1 },
      "eficiencia_ruta": "EFICIENTE"
    }
  ]
}
```

### 4. `GET /dashboard/co2-estimado` — Impacto ambiental

**Fuente:** Cálculo basado en datos de `ado-telemetria-live` con factor IPCC (2.68 kg CO₂/L)

**Respuesta:** Texto cualitativo con áreas de impacto (lenguaje difuso, C-003)

### 5. `POST /chat` — Chat con agentes IA

**Fuente:** Lambda `ado-chat-api` → Bedrock AgentCore

**Request:**
```json
{ "prompt": "Analiza el bus 7321", "agente": "combustible" }
```

**Respuesta:**
```json
{
  "respuesta": "El Bus 7321 muestra un consumo...",
  "agente_usado": "combustible",
  "session_id": "uuid"
}
```

---

## Campos que pueden llegar como `null`

Con los nuevos viajes, **no todos los SPNs aparecen en cada frame** (entre 3 y 11 por frame). Esto significa que algunos campos pueden llegar como `null` o `0` en la respuesta de `flota-status`:

| Campo | Puede ser null | Cómo lo maneja el frontend |
|---|---|---|
| `velocidad_kmh` | ✅ Sí | `bus.velocidad_kmh?.toFixed(0) ?? '—'` ✅ |
| `rpm` | ✅ Sí | `bus.rpm?.toFixed(0) ?? '—'` ✅ |
| `temperatura_motor_c` | ✅ Sí | `bus.temperatura_motor_c?.toFixed(0) ?? '—'` ✅ |
| `tasa_combustible_lh` | ✅ Sí | `bus.tasa_combustible_lh?.toFixed(1) ?? '—'` ✅ |
| `presion_aceite_kpa` | ✅ Sí | No se muestra en popup (solo en datos internos) |
| `latitud` / `longitud` | ❌ Siempre presente | Filtro `bus.latitud !== 0` en MapPage ✅ |
| `estado_consumo` | ❌ Siempre presente | Puede ser `SIN_DATOS` si no hay SPN 185 ni 183 |

El frontend ya usa optional chaining (`?.`) y fallback (`?? '—'`) en todos los campos numéricos del popup, así que **no necesita cambios**.

---

## Comportamiento esperado en el mapa

### Movimiento de buses

- **10 buses** visibles simultáneamente en la ruta México–Acapulco
- **4 buses van de ida** (México → Acapulco, de norte a sur)
- **6 buses van de regreso** (Acapulco → México, de sur a norte)
- Cada bus tiene un **fragmento GPS diferente** — no se solapan
- Los buses se mueven **fluidamente cada 10 segundos** (el frontend hace poll cada 10s y el simulador genera datos cada 10s)
- Los viajes duran **5 minutos** y luego reinician en loop

### Cambios de estado visibles

- La mayoría del tiempo los buses están en **verde** (EFICIENTE)
- Cada viaje tiene **2-3 ventanas de anomalía** de 20-35 segundos donde el bus cambia a **amarillo** (ALERTA_MODERADA) o **rojo** (ALERTA_SIGNIFICATIVA)
- Las anomalías incluyen: conducción agresiva, riesgo mecánico, velocidad excesiva, frenado brusco, balatas desgastadas
- Cuando un bus está en anomalía, `alertas_spn` tendrá 1-4 alertas con mensajes descriptivos

### Ejemplo de lo que verá el usuario

1. Bus 7313 se mueve de norte a sur, verde (eficiente)
2. En el segundo 120-150 del viaje, cambia a rojo: velocidad 126 km/h, rendimiento 1.5 km/L
3. El popup muestra "⚠ 3 alerta(s) activa(s)" con mensajes como "SPN 84: valor 126 km/h por encima del máximo 120 km/h"
4. Después de 35 segundos, vuelve a verde
5. Al minuto 5, el viaje reinicia desde el inicio

---

## Configuración actual del frontend

```typescript
// dashboard/src/config.ts
export const config = {
  api: {
    baseUrl: 'https://sutgpijmoh.execute-api.us-east-2.amazonaws.com',
  },
  polling: {
    fleetIntervalMs: 10_000,   // ← Alineado con TICK_INTERVAL=10s del simulador
    alertsIntervalMs: 30_000,
  },
  map: {
    center: [18.5, -99.5],     // ← Centro de la ruta México-Acapulco
    zoom: 7,
  },
};
```

**Todo está alineado.** El polling de 10s del frontend coincide con la resolución de 10s del simulador.

---

## Resumen: ¿Necesita cambios el frontend?

| Componente | ¿Necesita cambios? | Razón |
|---|---|---|
| `config.ts` | ❌ No | Polling ya está en 10s, centro del mapa correcto |
| `lib/api.ts` | ❌ No | Tipos y endpoints sin cambios |
| `MapPage.tsx` | ❌ No | Ya maneja nulls con `?.`, colores por estado, alertas |
| `AlertasPage.tsx` | ❌ No | Lee de `ado-alertas`, no del simulador |
| `EficienciaPage.tsx` | ❌ No | Agrega por ruta, mismos campos |
| `AmbientalPage.tsx` | ❌ No | Cálculo cualitativo, mismos datos |
| `ChatPage.tsx` | ❌ No | Independiente del simulador |

**El frontend funciona tal cual con los nuevos datos de simulación.**
