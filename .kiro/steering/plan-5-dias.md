---
inclusion: always
---

# 📅 Plan de Ejecución — ADO MobilityIA
## Hackathon AWS Builders League 2026 — ESTADO FINAL

> **Contexto:** Último día de desarrollo. El sistema está funcional end-to-end.
> Los datos son **simulados** (C-004). Sin métricas numéricas específicas (C-003).
> Los agentes son de **AgentCore** (C-005). Esquemas alineados con `models/` (C-006).

---

## Estado actual del proyecto

### ✅ COMPLETADO — Infraestructura
- 10 funciones Lambda codificadas, desplegadas y activas en us-east-2
  - Bucket de datos: `ado-telemetry-mvp` (todas las Lambdas apuntan aquí)
  - Bucket de Lambdas: `mobilityia-hackathon-bl-2026`
  - Bucket de frontend: `ado-mobilityia-dashboard`
- Shared layer `ado-common-layer` (v2) desplegado
- DynamoDB tablas creadas y activas: `ado-telemetria-live`, `ado-alertas`
- IAM rol `ado-lambda-execution-role` con permisos para DynamoDB, S3, SageMaker y AgentCore

### ✅ COMPLETADO — Agentes de IA (AgentCore)
- 2 Agentes desplegados en Amazon Bedrock AgentCore:
  - `AdoCombustible` — Claude 3.5 Sonnet, 4 tools (telemetría, desviación, buses activos, KB)
  - `AdoMantenimiento` — Claude 3.5 Sonnet, 5 tools (OBD, predicción ML, patrones, recomendación, KB)
- Knowledge Base `ado-mobilityia-kb` (ID: `VURICCT2OJ`) con 5 documentos indexados
- Ambos agentes responden en español con lenguaje difuso (C-003)

### ✅ COMPLETADO — Modelo ML (SageMaker)
- Modelo XGBoost entrenado con 128 features (AUC-ROC: 0.969)
- Endpoint `ado-prediccion-eventos` InService en ml.m5.large
- Lambda `tool-predecir-evento` corregida para enviar CSV con 128 features en orden exacto
- Fallback heurístico funcional cuando SageMaker no está disponible
- Predicción ML verificada: score 0.873 para bus con señales anómalas

### ✅ COMPLETADO — Simulación en Tiempo Real
- 10 viajes pre-procesados desde Parquets (27 SPNs, 300 frames cada uno)
- Simulador reescrito: lee `viajes_consolidados.json`, desfase 15% entre buses, speedup 3x
- Buses se mueven con GPS real a lo largo de la ruta México-Acapulco
- Datos ricos en DynamoDB: 26 SPNs por registro, campos planos, alertas, estado de consumo

### ✅ COMPLETADO — API Gateway + Cognito
- API Gateway HTTP API con JWT authorizer (Cognito)
- 5 endpoints protegidos: flota-status, alertas-activas, resumen-consumo, co2-estimado, chat
- Cognito User Pool con usuario de demo: `demo@adomobilityia.com` / `DemoADO2026!`
- CORS configurado para localhost:3000 y CloudFront

### ✅ COMPLETADO — Chat con Agentes
- Lambda `ado-chat-api` invoca agentes de AgentCore via SDK `bedrock-agentcore`
- Auto-detección de agente por keywords del prompt
- Parseo de respuesta SSE y limpieza de tags `<thinking>`
- Endpoint POST /chat en API Gateway con JWT auth

### ✅ COMPLETADO — Frontend React
- Dashboard profesional con 5 vistas: Mapa, Alertas, Eficiencia, Ambiental, Chat
- Mapa en vivo con Leaflet (dark theme, CARTO tiles)
- Click en bus → popup con datos en tiempo real + botón "Preguntar al Agente"
- Panel lateral con vehículos con alertas y recomendaciones de mantenimiento
- Chat con efecto typing, markdown rendering, selector de agente
- Login con Cognito (SRP auth)
- Desplegado en S3 + CloudFront: `https://d1zr7g3ygmf5pk.cloudfront.net`

### ✅ COMPLETADO — Ensayo End-to-End
- Simulador → DynamoDB → Dashboard API → Frontend: verificado
- Chat → AgentCore → Lambdas tools → DynamoDB/S3/SageMaker: verificado
- Predicción ML con modelo_ml (no heurística): verificado
- Cognito auth → API Gateway JWT: verificado
- Todos los endpoints retornan datos correctos

### ⚠️ PENDIENTE — Mejoras opcionales
- [ ] EventBridge Scheduler para simulador automático (rate 10 seconds)
- [ ] Datos "trampa" con señales anómalas para demo impactante
- [ ] Function URL streaming para chat en tiempo real (403 pendiente de resolver)
- [ ] Más viajes de ejemplo para simular más buses simultáneamente

---

## 📋 IDs de recursos AWS (us-east-2, cuenta 084032333314)

| Recurso | ID / Nombre |
|---|---|
| **Dashboard URL** | `https://d1zr7g3ygmf5pk.cloudfront.net` |
| **API Gateway** | `https://sutgpijmoh.execute-api.us-east-2.amazonaws.com` |
| CloudFront Distribution | `E1M19Q2U1SVAYR` |
| Cognito User Pool | `us-east-2_5itNQjtYP` |
| Cognito Client ID | `7f05s6kerku5ejb58odjj4b1fl` |
| Agente Combustible ARN | `arn:aws:bedrock-agentcore:us-east-2:084032333314:runtime/AdoCombustible_AdoCombustible-BJ7Uvb4ozE` |
| Agente Mantenimiento ARN | `arn:aws:bedrock-agentcore:us-east-2:084032333314:runtime/AdoMantenimiento_AdoMantenimiento-2sL9qkC3yK` |
| Knowledge Base | `VURICCT2OJ` (`ado-mobilityia-kb`) |
| SageMaker Endpoint | `ado-prediccion-eventos` (InService) |
| DynamoDB Telemetría | `ado-telemetria-live` |
| DynamoDB Alertas | `ado-alertas` |
| Bucket datos | `ado-telemetry-mvp` |
| Bucket lambdas | `mobilityia-hackathon-bl-2026` |
| Bucket frontend | `ado-mobilityia-dashboard` |
| Rol Lambdas | `ado-lambda-execution-role` |

---

## Flujo de la demo

### Guión recomendado (5 minutos)

1. **Login** (30s)
   - Abrir `https://d1zr7g3ygmf5pk.cloudfront.net`
   - Ingresar con `demo@adomobilityia.com`

2. **Mapa en Vivo** (1 min)
   - Mostrar 10 buses moviéndose en la ruta México-Acapulco
   - Señalar los colores: verde (eficiente), rojo (alerta)
   - Click en un bus con alerta → popup con datos en tiempo real

3. **Chat con Agente de Combustible** (1 min)
   - Desde el popup, click "Preguntar al Agente IA"
   - El agente analiza el bus y detecta desviaciones
   - Mostrar el efecto typing y la respuesta en español

4. **Chat con Agente de Mantenimiento** (1 min)
   - Cambiar a agente de mantenimiento
   - Preguntar: "¿Qué buses tienen riesgo mecánico?"
   - El agente usa SageMaker ML para predecir y recomienda intervención

5. **Alertas + Ambiental** (1 min)
   - Mostrar la vista de alertas con OT generada
   - Mostrar el panel de impacto ambiental con lenguaje difuso

6. **Cierre** (30s)
   - Resaltar: AgentCore + SageMaker ML + Knowledge Base RAG
   - Todo en datos simulados, todo en español, todo en tiempo real

### Preguntas de alto impacto para el chat

**Combustible:**
- "¿Qué buses tienen mayor consumo en este momento?"
- "Analiza el bus 7313, ¿qué está causando el consumo elevado?"

**Mantenimiento:**
- "¿Qué buses tienen riesgo mecánico esta semana?"
- "Analiza el riesgo del bus 7331 y genera una recomendación"

---

## Arquitectura desplegada

```
┌─────────────────────────────────────────────────────────────────┐
│  FRONTEND — React + Tailwind + Leaflet                          │
│  S3 + CloudFront (https://d1zr7g3ygmf5pk.cloudfront.net)       │
│  Login: Cognito JWT                                             │
└──────────────────────────┬──────────────────────────────────────┘
                           │ HTTPS
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│  API GATEWAY HTTP API (JWT Authorizer)                          │
│  https://sutgpijmoh.execute-api.us-east-2.amazonaws.com         │
│                                                                 │
│  GET /dashboard/*  →  ado-dashboard-api (Lambda)                │
│  POST /chat        →  ado-chat-api (Lambda)                     │
└──────────────────────────┬──────────────────────────────────────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
┌──────────────────┐ ┌──────────┐ ┌──────────────────────┐
│  DynamoDB        │ │ AgentCore│ │  SageMaker           │
│  ado-telemetria  │ │ 2 Agentes│ │  XGBoost (128 feat)  │
│  ado-alertas     │ │ + KB RAG │ │  ado-prediccion      │
└────────┬─────────┘ └────┬─────┘ └──────────────────────┘
         │                │
         │                ▼
         │         ┌──────────────┐
         │         │  7 Lambda    │
         │         │  Tools       │
         │         │  (consultar, │
         │         │   predecir,  │
         │         │   recomendar)│
         │         └──────┬───────┘
         │                │
         ▼                ▼
┌─────────────────────────────────────────────────────────────────┐
│  S3 — ado-telemetry-mvp                                         │
│  Datos simulados, catálogos, Knowledge Base, modelo ML          │
└─────────────────────────────────────────────────────────────────┘
         ▲
         │
┌────────┴────────┐
│  Simulador      │
│  Lambda         │
│  (10 buses,     │
│   desfase 15%,  │
│   27 SPNs)      │
└─────────────────┘
```

---

## Servicios AWS utilizados

| Servicio | Uso | Estado |
|---|---|---|
| Amazon Bedrock AgentCore | 2 agentes autónomos (Combustible + Mantenimiento) | ✅ Activo |
| Amazon Bedrock Knowledge Bases | RAG con manuales técnicos y catálogos | ✅ Activo |
| Anthropic Claude 3.5 Sonnet | Modelo de lenguaje para los agentes | ✅ Activo |
| Amazon SageMaker | Modelo XGBoost predictivo (128 features) | ✅ InService |
| Amazon S3 | Data Lake + hosting frontend | ✅ Activo |
| Amazon DynamoDB | Estado en tiempo real + alertas | ✅ Activo |
| AWS Lambda | 10 funciones (simulador, tools, APIs) | ✅ Activo |
| Amazon API Gateway | HTTP API con JWT auth | ✅ Activo |
| Amazon Cognito | Autenticación de usuarios | ✅ Activo |
| Amazon CloudFront | CDN para frontend | ✅ Desplegado |
| Amazon CloudWatch | Logs de todas las Lambdas | ✅ Activo |
