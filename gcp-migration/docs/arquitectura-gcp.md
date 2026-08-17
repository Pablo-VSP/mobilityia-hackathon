# Arquitectura GCP — ADO MobilityIA

## Diagrama

```
┌─────────────────────────────────────────────────────────────────┐
│  FRONTEND — React + Tailwind + Leaflet                          │
│  Firebase Hosting (gratis)                                      │
│  Auth: Firebase Authentication (JWT)                            │
└──────────────────────────┬──────────────────────────────────────┘
                           │ HTTPS
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│  CLOUD RUN — api-dashboard                                      │
│  GET /dashboard/*  →  FastAPI (flota, alertas, consumo, CO2)    │
└──────────────────────────┬──────────────────────────────────────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
┌──────────────────┐ ┌──────────────┐ ┌──────────────────────────┐
│  Firestore       │ │ Cloud Run    │ │  Cloud Run                │
│  telemetria-live │ │ agente-comb  │ │  agente-mant              │
│  alertas         │ │ (Gemini +    │ │  (Gemini + XGBoost        │
│                  │ │  FAISS RAG)  │ │   in-memory + FAISS)      │
└────────┬─────────┘ └──────────────┘ └──────────────────────────┘
         │                    ▲                   ▲
         │                    │                   │
         │               ┌────┴───────────────────┴────┐
         │               │  Cloud Run — chat-api       │
         │               │  POST /chat → route agents  │
         │               └─────────────────────────────┘
         ▼
┌─────────────────────────────────────────────────────────────────┐
│  Cloud Storage — ado-telemetry-mvp-gcp                          │
│  Datos simulados, catálogos, FAISS index, XGBoost model         │
└─────────────────────────────────────────────────────────────────┘
         ▲
         │
┌────────┴────────┐
│  Cloud Run      │
│  simulador      │
│  (Cloud         │
│   Scheduler     │
│   cada 1 min)   │
└─────────────────┘
```

## Comparativa AWS vs GCP

| Aspecto | AWS (actual) | GCP (propuesto) |
|---|---|---|
| Servicios gestionados | 12+ | 5 |
| Costo MVP 10 buses | ~$47-320/mes | ~$8-15/mes |
| "Vampiros" de costo | SageMaker + OpenSearch ($305/mes) | Ninguno |
| Escala a cero | Lambda sí, SageMaker/OpenSearch NO | Todo escala a cero |
| Deploy | Manual (zip + CLI × 10 lambdas) | 1 script, 5 `gcloud run deploy` |
| Scripts encender/apagar | Necesarios | No necesarios |
| Cold start agentes | AgentCore session ~3-5s | Cloud Run ~1-2s |
| Modelo ML | Endpoint dedicado ($0.115/h) | Embebido en container ($0) |
| RAG vectorial | OpenSearch 2 OCU ($0.48/h) | FAISS in-memory ($0) |
| Auth | Cognito (config compleja) | Firebase Auth (setup 5 min) |
| CDN | CloudFront | Firebase Hosting (incluido) |
| LLM | Claude 3.5 Sonnet ($3/$15 per 1M) | Gemini Flash ($0.075/$0.30 per 1M) |

## Servicios GCP utilizados

| Servicio | Función | Free Tier |
|---|---|---|
| Cloud Run | 5 microservicios | 2M requests/mes |
| Firestore | Base de datos | 1 GB + 50k reads/día |
| Cloud Storage | Data lake | 5 GB |
| Gemini 1.5 Flash | LLM para agentes | 15 RPM free tier |
| Firebase Hosting | Frontend | 10 GB/mes |
| Firebase Auth | Autenticación | 50k MAU |
| Cloud Scheduler | Trigger simulador | 3 jobs gratis |
| Cloud Logging | Observabilidad | 50 GB/mes |

## Decisiones de diseño

1. **Cloud Run sobre Cloud Functions**: Mejor para containers con estado (FAISS index, XGBoost model cargados en memoria). Concurrencia multi-request reduce costos.

2. **Gemini Flash sobre Claude**: 50x más barato. Suficiente calidad para análisis de datos estructurados en español.

3. **FAISS in-memory sobre Vertex AI Search**: Con 5 documentos, un vector store managed es overkill. FAISS es instantáneo y costo $0.

4. **XGBoost embebido sobre Vertex AI Prediction**: Modelo de 5 MB corre perfectamente en el container del agente. Elimina latencia de red y costo de endpoint.

5. **Firestore sobre Bigtable**: Para ~10-50 buses, Firestore es ideal (pay-per-use, free tier generoso, queries simples).

6. **Firebase Auth sobre Identity Platform**: Firebase Auth es gratis hasta 50k MAU y tiene SDK idéntico en complejidad a Cognito.
