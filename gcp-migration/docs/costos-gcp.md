# Análisis de Costos GCP — ADO MobilityIA

## Resumen ejecutivo

| Escenario | Buses | Costo GCP/mes | Costo AWS/mes | Ahorro |
|---|---|---|---|---|
| **MVP Demo** | 10 | ~$8-15 | ~$47 (opt) / $320 (real) | 70-95% |
| **Piloto** | 50 | ~$25-40 | ~$180 | 78-86% |
| **Producción** | 200 | ~$80-120 | ~$350 | 66-77% |
| **Full** | 2,000 | ~$300-450 | ~$1,100 | 59-73% |

## Desglose por servicio

### Cloud Run (5 servicios)

**Pricing:**
- CPU: $0.00002400/vCPU-second (solo mientras procesa requests)
- Memory: $0.00000250/GiB-second
- Requests: $0.40/million
- Free tier: 2M requests, 360k vCPU-sec, 180k GiB-sec/mes

| Servicio | Requests/mes | CPU/request | Costo |
|---|---|---|---|
| api-dashboard | ~260k (10s polling) | ~50ms | ~$0.50 |
| simulador | ~43k (1/min) | ~200ms | ~$0.30 |
| agente-combustible | ~1.5k (50 chats/día) | ~5s | ~$1.50 |
| agente-mantenimiento | ~1.5k | ~5s | ~$1.50 |
| chat-api | ~1.5k | ~100ms | ~$0.10 |
| **Total Cloud Run** | | | **~$3.90** |

> Con free tier (2M requests), el MVP de 10 buses probablemente cuesta **$0** en Cloud Run.

### Gemini 1.5 Flash (LLM)

**Pricing (agosto 2026):**
- Input: $0.075/1M tokens
- Output: $0.30/1M tokens
- Free tier: 15 RPM, 1M tokens/día

**Estimación por mensaje de chat:**
- Input promedio: ~2,000 tokens (system prompt + tool results)
- Output promedio: ~800 tokens
- Costo por mensaje: ~$0.0004

| Uso | Mensajes/mes | Costo |
|---|---|---|
| Demo (5/día) | 150 | ~$0.06 |
| Regular (20/día) | 600 | ~$0.24 |
| Piloto (50/día) | 1,500 | ~$0.60 |
| Producción (200/día) | 6,000 | ~$2.40 |

> **50x más barato que Claude 3.5 Sonnet** ($3/$15 per 1M tokens)

### Firestore

**Pricing:**
- Write: $0.18/100k documents
- Read: $0.06/100k documents
- Delete: $0.02/100k documents
- Storage: $0.18/GiB-month
- Free tier: 50k reads, 20k writes, 20k deletes/día; 1 GiB storage

**Estimación 10 buses:**
- Writes (simulador): 6 ticks × 10 buses × 1/min × 60 min × 24h = 86,400/día
- Reads (dashboard): ~8,640/día
- Storage: TTL 24h → ~86k docs × ~2 KB = ~170 MB

| Componente | 10 buses | 50 buses | 200 buses |
|---|---|---|---|
| Writes | $0 (free tier) | ~$2.30 | ~$9.30 |
| Reads | $0 (free tier) | ~$0.50 | ~$2.00 |
| Storage | $0 (free tier) | ~$0.10 | ~$0.40 |
| **Total** | **$0** | **~$2.90** | **~$11.70** |

> El free tier de Firestore cubre completamente el MVP de 10 buses (86k writes/día < umbral si ajustas burst).

### Cloud Storage

- Storage: $0.020/GB-month (Standard)
- Operations: $0.005/10k (Class A), $0.0004/10k (Class B)
- Free tier: 5 GB

**Estimación:** ~50 GB de datos simulados → ~$1/mes

### Firebase Hosting

- Free tier: 10 GB storage, 360 MB/day transfer
- Para un SPA React de ~2 MB: **$0/mes**

### Firebase Authentication

- Free tier: 50,000 MAU
- Para demo/piloto: **$0/mes**

### Cloud Scheduler

- Free tier: 3 jobs/account
- Solo necesitamos 1 (simulador): **$0/mes**

### Cloud Logging

- Free tier: First 50 GiB/month
- Para 5 servicios Cloud Run con logging moderado: **$0/mes**

---

## Comparativa directa de costos (10 buses, modo demo)

| Servicio | AWS (real factura) | GCP (estimado) |
|---|---|---|
| OpenSearch Serverless | **$172.80** | $0 (FAISS in-memory) |
| SageMaker endpoint | **$132.59** | $0 (XGBoost in-container) |
| DynamoDB | $3.64 | $0 (Firestore free tier) |
| Lambda/Cloud Run | ~$5.50 | ~$0-4 |
| LLM (Bedrock/Gemini) | ~$4.50 | ~$0.06 |
| S3/Cloud Storage | ~$2 | ~$1 |
| CDN/Hosting | ~$0.50 | $0 (Firebase) |
| API Gateway | ~$1 | $0 (Cloud Run directo) |
| Auth (Cognito) | $0 | $0 (Firebase) |
| **TOTAL** | **~$320** | **~$5-15** |

## Eliminación de "vampiros" de costo

| Vampiro AWS | Costo AWS | Equivalente GCP | Costo GCP | Ahorro |
|---|---|---|---|---|
| OpenSearch Serverless (2 OCU) | $172.80/mes | FAISS in-memory | $0 | 100% |
| SageMaker endpoint (24/7) | $82-132/mes | XGBoost en container | $0 | 100% |
| **Total vampiros eliminados** | **$255-305/mes** | | **$0** | **$255-305/mes** |

## Scaling model

```
Costo mensual GCP =
    Cloud Run (pay-per-request, escala a 0) +
    Gemini Flash ($0.0004/mensaje) +
    Firestore (free tier hasta 50 buses) +
    Cloud Storage (~$1 fijo)

Para 10 buses: ~$8-15/mes (mayormente Gemini)
Para 2,000 buses: ~$300-450/mes (Firestore + Cloud Run dominan)
```

## Conclusión

La migración a GCP reduce costos entre 70-95% para el MVP y 60-73% a escala completa.
El ahorro principal viene de eliminar servicios que cobran por estar encendidos
(OpenSearch, SageMaker) y reemplazar Claude por Gemini Flash.
