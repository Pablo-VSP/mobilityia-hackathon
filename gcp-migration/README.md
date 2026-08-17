# ADO MobilityIA — GCP Migration

## Arquitectura

```
gcp-migration/
├── services/
│   ├── api-dashboard/       # Cloud Run — API del dashboard (FastAPI)
│   ├── simulador/           # Cloud Run — Simulador de telemetría
│   ├── agente-combustible/  # Cloud Run — Agente IA con Gemini
│   ├── agente-mantenimiento/# Cloud Run — Agente IA con Gemini + XGBoost
│   └── chat-api/            # Cloud Run — Chat endpoint con streaming SSE
├── shared/                  # Librería compartida (firestore, gcs, spn catalog)
├── frontend/                # React app (Firebase Auth)
├── scripts/                 # Deploy, setup, scheduler
├── knowledge-base/          # Embeddings FAISS pre-calculados
└── docs/                    # Documentación de arquitectura y costos
```

## Stack GCP

| Servicio | Uso | Costo estimado |
|---|---|---|
| Cloud Run (5 services) | Backend completo | ~$5-10/mes |
| Firestore | Estado real-time + alertas | $0 (free tier) |
| Cloud Storage | Data lake | ~$1/mes |
| Gemini 1.5 Flash | LLM para agentes | ~$2-5/mes |
| Firebase Hosting | Frontend SPA | $0 (free tier) |
| Firebase Auth | Autenticación JWT | $0 (free tier) |
| Cloud Scheduler | Trigger simulador | $0 (free tier) |
| FAISS (in-memory) | RAG vectorial | $0 |
| XGBoost (in-memory) | ML predictivo | $0 |
| **TOTAL** | | **~$8-15/mes** |

## Ventajas sobre AWS

- **Sin vampiros de costo**: todo escala a 0 automáticamente
- **5 servicios vs 12+**: menor superficie operacional
- **Sin scripts encender/apagar**: Cloud Run maneja el ciclo de vida
- **Deploy simple**: `gcloud run deploy` (un comando)
- **Tools locales**: sin latencia de red entre agente y tools

## Plan de trabajo

El plan detallado para completar la migración, recalibrado para desarrollo asistido por IA, está disponible en:

- [Plan de trabajo de migración asistida por IA](docs/plan-trabajo-migracion-ia.md)

Hitos previstos:

- Cutover operativo interno: **11 de septiembre de 2026**.
- Estabilización y compromiso conservador: **18 de septiembre de 2026**.
- Retiro progresivo de AWS: desde el **21 de septiembre de 2026**, sujeto a aprobación.
- Predicción específica de fallas: entrega separada y condicionada a etiquetas confirmadas.

> **Estado actual:** los cinco servicios base de Cloud Run están desplegados o parcialmente implementados. Pub/Sub, el ingestor real, la integración histórica con BigQuery, el frontend completo, la autenticación backend y la inferencia ML final todavía forman parte del trabajo pendiente descrito en el plan.

## Quick Start

```bash
# 1. Setup proyecto GCP
./scripts/setup-project.sh

# 2. Deploy todos los servicios
./scripts/deploy-all.sh

# 3. Deploy frontend
cd frontend && npm run build && firebase deploy
```

## Credenciales necesarias

- GCP Project con billing habilitado
- `gcloud` CLI instalado y autenticado
- Firebase CLI para el frontend
- Vertex AI API habilitada (para Gemini)
