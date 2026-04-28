# 🔑 Recursos AWS — ADO MobilityIA
## Hackathon AWS Builders League 2026

> Documento de referencia con todos los recursos desplegados.
> Última actualización: 2026-04-28 00:00 CST

---

## Dashboard Frontend

| Recurso | Valor |
|---|---|
| **URL Producción** | `https://d1zr7g3ygmf5pk.cloudfront.net` |
| **URL Local** | `http://localhost:3000` |
| CloudFront Distribution | `E1M19Q2U1SVAYR` |
| S3 Bucket (hosting) | `ado-mobilityia-dashboard` |
| OAC ID | `E1VWCZE68EW0MK` |
| Stack | Vite + React 19 + TypeScript + Tailwind v4 + Leaflet |

### Vistas del Dashboard

| Vista | Ruta | Descripción |
|---|---|---|
| Mapa en Vivo | `/` | Mapa con buses en tiempo real, popups con datos, panel de alertas |
| Alertas | `/alertas` | Alertas activas ordenadas por urgencia |
| Eficiencia | `/eficiencia` | Resumen de consumo por ruta |
| Ambiental | `/ambiental` | Estimación cualitativa de CO₂ (C-003) |
| Chat IA | `/chat` | Chat con agentes de combustible y mantenimiento |

### Deploy del frontend
```bash
cd dashboard && npx vite build
aws s3 sync dist/ s3://ado-mobilityia-dashboard/ --delete --region us-east-2
aws cloudfront create-invalidation --distribution-id E1M19Q2U1SVAYR --paths "/*"
```

---

## API Gateway

| Recurso | Valor |
|---|---|
| API ID | `sutgpijmoh` |
| **Endpoint** | `https://sutgpijmoh.execute-api.us-east-2.amazonaws.com` |
| Región | `us-east-2` |
| Tipo | HTTP API (v2) con auto-deploy |
| Authorizer | JWT (Cognito) — ID: `34m4xh` |

### Endpoints disponibles

| Método | Path | Lambda | Descripción |
|---|---|---|---|
| GET | `/dashboard/flota-status` | `ado-dashboard-api` | Estado de flota con GPS, velocidad, SPNs |
| GET | `/dashboard/alertas-activas` | `ado-dashboard-api` | Alertas activas por urgencia |
| GET | `/dashboard/resumen-consumo` | `ado-dashboard-api` | Eficiencia por ruta |
| GET | `/dashboard/co2-estimado` | `ado-dashboard-api` | Impacto ambiental (lenguaje difuso) |
| POST | `/chat` | `ado-chat-api` | Chat con agentes AgentCore |

**Body del chat:** `{"prompt": "...", "agente": "combustible|mantenimiento"}`

Todos los endpoints requieren header `Authorization: Bearer <id_token>` de Cognito.

---

## Cognito

| Recurso | Valor |
|---|---|
| User Pool ID | `us-east-2_5itNQjtYP` |
| App Client ID | `7f05s6kerku5ejb58odjj4b1fl` |
| Dominio | `ado-mobilityia.auth.us-east-2.amazoncognito.com` |
| Región | `us-east-2` |
| Auth flows | SRP + Password + Refresh |

### Usuario de demo

| Campo | Valor |
|---|---|
| Email | `demo@adomobilityia.com` |
| Password | `DemoADO2026!` |

---

## DynamoDB

| Tabla | PK | SK | GSI | Items |
|---|---|---|---|---|
| `ado-telemetria-live` | `autobus` (S) | `timestamp` (S) | `viaje_ruta-timestamp-index` | ~75+ |
| `ado-alertas` | `alerta_id` (S) | `timestamp` (S) | — | 1+ |

### Campos clave de `ado-telemetria-live`
- `spn_valores` (Map) — 26 SPNs pivoteados con `{valor, name, unidad, fuera_de_rango}`
- `alertas_spn` (List) — SPNs fuera de rango
- `estado_consumo` — `EFICIENTE`, `ALERTA_MODERADA`, `ALERTA_SIGNIFICATIVA`, `SIN_DATOS`
- Campos planos: `velocidad_kmh`, `rpm`, `temperatura_motor_c`, `presion_aceite_kpa`, `tasa_combustible_lh`, `nivel_combustible_pct`, `latitud`, `longitud`, etc.
- TTL: `ttl_expiry` (24 horas)

---

## S3

| Bucket | Uso |
|---|---|
| `ado-telemetry-mvp` | Datos simulados, catálogos, modelos ML, viajes consolidados |
| `mobilityia-hackathon-bl-2026` | Código de Lambdas (deploy original) |
| `ado-mobilityia-dashboard` | Frontend React (hosting estático) |

### Estructura de `ado-telemetry-mvp`
```
hackathon-data/
├── catalogo/motor_spn.json                    ← Catálogo 37 SPNs
├── fallas-simuladas/data_fault.json           ← Historial de fallas
├── telemetria-simulada/bus_*.json             ← Datos por bus (legacy)
├── simulacion/viajes_consolidados.json        ← 3 viajes pre-procesados (11.7 MB)
├── sample_data/travel_telemetry_examples_/    ← 3 Parquets originales
├── raw/travel_telemetry/                      ← 1,339 Parquets (426 MB)
├── raw/data_fault/                            ← 123 Parquets (6.5 MB)
├── raw/motor_spn/                             ← 1 Parquet
├── knowledge-base/docs/                       ← 5 documentos para RAG
└── modelos/sagemaker/
    ├── training-data/feature_names.json       ← 128 features del modelo
    ├── training-data/train.csv
    ├── output/model.tar.gz                    ← Modelo XGBoost entrenado
    └── model_summary.json                     ← Métricas y umbrales
```

---

## SageMaker

| Recurso | Valor |
|---|---|
| Endpoint | `ado-prediccion-eventos` |
| Estado | InService |
| Modelo | XGBoost 1.7 |
| Features | 128 (114 telemetría + 9 fallas + 5 contextuales) |
| Instancia | `ml.m5.large` |
| AUC-ROC | 0.969 |
| Target | `evento_14_dias` (falla con severidad ≥ 2 en 14 días) |

### Umbrales de riesgo ML
| Score | Nivel | Urgencia |
|---|---|---|
| < 0.25 | BAJO | PROXIMO_SERVICIO |
| 0.25 – 0.50 | MODERADO | ESTA_SEMANA |
| 0.50 – 0.75 | ELEVADO | ESTA_SEMANA |
| ≥ 0.75 | CRITICO | INMEDIATA |

---

## Lambdas (10 funciones, us-east-2)

Todas usan `ado-common-layer:2` y `S3_BUCKET=ado-telemetry-mvp`.

| Lambda | Grupo | Memoria | Timeout | Descripción |
|---|---|---|---|---|
| `ado-simulador-telemetria` | Simulador | 512 MB | 30s | Simula 3 buses con desfase temporal |
| `tool-consultar-telemetria` | Agente Combustible | 256 MB | 15s | Últimos registros de un bus |
| `tool-calcular-desviacion` | Agente Combustible | 256 MB | 15s | Desviación de consumo vs patrón |
| `tool-listar-buses-activos` | Agente Combustible | 256 MB | 15s | Buses con telemetría activa |
| `tool-consultar-obd` | Agente Mantenimiento | 256 MB | 15s | Señales OBD y salud mecánica |
| `tool-predecir-evento` | Agente Mantenimiento | 256 MB | 30s | Predicción ML + heurística fallback |
| `tool-buscar-patrones-historicos` | Agente Mantenimiento | 256 MB | 15s | Patrones en historial de fallas |
| `tool-generar-recomendacion` | Agente Mantenimiento | 256 MB | 15s | Crea recomendación en DynamoDB |
| `ado-dashboard-api` | Dashboard | 256 MB | 15s | API REST con 4 endpoints |
| `ado-chat-api` | Chat | 256 MB | 120s | Proxy a agentes AgentCore |

---

## AgentCore

| Agente | Runtime ARN | Modelo |
|---|---|---|
| `AdoCombustible` | `arn:aws:bedrock-agentcore:us-east-2:084032333314:runtime/AdoCombustible_AdoCombustible-BJ7Uvb4ozE` | Claude 3.5 Sonnet |
| `AdoMantenimiento` | `arn:aws:bedrock-agentcore:us-east-2:084032333314:runtime/AdoMantenimiento_AdoMantenimiento-2sL9qkC3yK` | Claude 3.5 Sonnet |

### Tools por agente

**Combustible:** `consultar_telemetria`, `calcular_desviacion`, `listar_buses_activos`, `consultar_knowledge_base`

**Mantenimiento:** `consultar_obd`, `predecir_evento`, `buscar_patrones_historicos`, `generar_recomendacion`, `consultar_knowledge_base`

### Knowledge Base

| Recurso | Valor |
|---|---|
| KB ID | `4OAVLRB8VI` |
| Data Source ID | `LL4E15XKR4` |
| Nombre | `ado-mobilityia-kb` |
| Documentos | 5 (catálogo SPN, fallas, 3 manuales) |

---

## IAM

| Rol | Uso | Permisos clave |
|---|---|---|
| `ado-lambda-execution-role` | Todas las Lambdas | DynamoDB (CRUD), S3 (Read), SageMaker (Invoke), AgentCore (Invoke) |
| `ado-bedrock-agent-role` | Agentes Bedrock | Bedrock models, Knowledge Base |

### Política inline `ado-lambda-permissions`
- DynamoDB: PutItem, BatchWriteItem, GetItem, Query, Scan en `ado-telemetria-live` y `ado-alertas`
- S3: GetObject, ListBucket en `ado-telemetry-mvp` y `mobilityia-hackathon-bl-2026`
- SageMaker: InvokeEndpoint en `ado-prediccion-eventos`
- AgentCore: InvokeAgentRuntime en `runtime/*`

---

## Simulación

### Datos de viajes
3 viajes pre-procesados desde Parquets reales:

| Viaje | Bus | Ruta | Duración | Frames | SPNs |
|---|---|---|---|---|---|
| 055 | 7331 | MEX TAXQUEÑA → ACAPULCO | ~5h | 2,349 | 27 |
| 181 | 7302 | MEX TAXQUEÑA → ACAPULCO | ~5h | 2,392 | 27 |
| 216 | 7313 | ACAPULCO → MEX TAXQUEÑA | ~5h | 2,391 | 27 |

### Configuración del simulador
- **Desfase:** 15% entre buses (~45 min de diferencia)
- **Speedup:** 3x (STEP_SECONDS=30, viaje de 5h en ~1.7h)
- **Trigger:** EventBridge Scheduler rate(10 seconds) — pendiente de configurar
- **Datos:** `viajes_consolidados.json` (11.7 MB, cacheado en memoria)

### Invocar manualmente
```bash
aws lambda invoke --function-name ado-simulador-telemetria --payload '{}' --region us-east-2 /tmp/sim.json
```
