# 📊 Investigación de Precios AWS — ADO MobilityIA
## Fuentes verificadas | Agosto 2026

> Documento de referencia con precios oficiales de AWS consultados para el análisis de costos del proyecto.
> Región de referencia: **us-east-2 (Ohio)** — precios equivalentes a us-east-1 para la mayoría de servicios.

---

## 1. AWS Lambda

**Fuente:** [AWS Lambda Pricing](https://aws.amazon.com/lambda/pricing/) | [CloudZero Lambda Pricing Guide (Jul 2026)](https://www.cloudzero.com/blog/lambda-pricing/)

| Concepto | Precio x86 | Precio ARM (Graviton2) |
|---|---|---|
| Requests | $0.20 / 1M requests ($0.0000002 each) | Igual |
| Duration | $0.0000166667 / GB-second | $0.0000133334 / GB-second (~20% menos) |
| Provisioned Concurrency | $0.0000041667 / GB-second | ~20% menos |
| Ephemeral Storage (>512 MB) | $0.0000000309 / GB-second | Igual |

**Free Tier (permanente, no expira):**
- 1,000,000 requests/mes
- 400,000 GB-seconds/mes
- 100 GiB response streaming/mes

**Notas de pricing relevantes para el proyecto:**
- La duración se cobra por milisegundo (redondeo al ms más cercano)
- La memoria configurada determina el precio por segundo (más memoria = más caro pero más CPU)
- Las funciones que esperan a modelos de IA (Bedrock, SageMaker) pagan por todo el tiempo de espera

Content was rephrased for compliance with licensing restrictions.

---

## 2. Amazon DynamoDB (On-Demand)

**Fuente:** [DynamoDB On-Demand Pricing](https://aws.amazon.com/dynamodb/pricing/on-demand/) | [AWS Blog: DynamoDB Price Reduction Nov 2024](https://aws.amazon.com/blogs/database/new-amazon-dynamodb-lowers-pricing-for-on-demand-throughput-and-global-tables/)

**Reducción de precios (noviembre 2024):** AWS redujo los precios on-demand en 50% y global tables hasta 67%.

| Concepto | Precio (post Nov 2024) | Precio anterior |
|---|---|---|
| Write Request Unit (WRU) | $0.625 / millón | $1.25 / millón |
| Read Request Unit (RRU) | $0.125 / millón | $0.25 / millón |
| Storage (Standard) | $0.25 / GB-mes | Sin cambio |
| Storage (IA) | $0.10 / GB-mes | Sin cambio |

**Notas:**
- 1 WRU = 1 escritura de hasta 1 KB
- 1 RRU = 1 lectura eventual consistente de hasta 4 KB (strongly consistent = 2 RRU)
- Scan consume 1 RRU por cada 4 KB leídos (no por item)
- TTL deletes no se cobran
- DynamoDB Streams: primeras 2.5M lecturas/mes gratis, luego $0.02/100,000

**Provisioned (comparación):**
- WCU: $0.00065 / WCU-hora ($0.468/WCU-mes)
- RCU: $0.00013 / RCU-hora ($0.0936/RCU-mes)
- Reserved Capacity (1 año): ~60% descuento sobre provisioned

Content was rephrased for compliance with licensing restrictions.

---

## 3. Amazon SageMaker — Real-Time Inference

**Fuente:** [SageMaker Pricing](https://aws.amazon.com/sagemaker/pricing/) | [CloudZero SageMaker Pricing Guide](https://www.cloudzero.com/blog/sagemaker-pricing/)

| Instancia | vCPU | RAM | Precio/hora (us-east-2) |
|---|---|---|---|
| ml.t2.medium | 2 | 4 GB | $0.056 |
| ml.m5.large | 2 | 8 GB | $0.115 |
| ml.m5.xlarge | 4 | 16 GB | $0.230 |
| ml.c5.large | 2 | 4 GB | $0.102 |
| ml.c5.xlarge | 4 | 8 GB | $0.204 |

**SageMaker Serverless Inference (alternativa):**
- $0.0000833 / GB-second de procesamiento
- Sin costo cuando no hay tráfico
- Cold start: ~2-5 segundos en primera invocación

**Nuestro uso:** `ml.m5.large` @ $0.115/hora = $82.80/mes (24/7) o $27.60/mes (8h/día)

Content was rephrased for compliance with licensing restrictions.

---

## 4. Amazon Bedrock — Claude 3.5 Sonnet v2

**Fuente:** [Amazon Bedrock Pricing](https://aws.amazon.com/bedrock/pricing/) | [Anthropic Claude Sonnet Pricing](https://www.anthropic.com/claude/sonnet) | [FutureAGI Bedrock Calculator](https://www.futureagi.com/llm-cost-calculator/bedrock/anthropic-claude-3-5-sonnet-20240620-v1-0)

| Modelo | Input tokens | Output tokens | Context window |
|---|---|---|---|
| Claude 3.5 Sonnet v2 | $3.00 / 1M tokens | $15.00 / 1M tokens | 200K tokens |
| Claude 3.5 Haiku | $0.80 / 1M tokens | $4.00 / 1M tokens | 200K tokens |
| Claude Sonnet 4 (intro pricing hasta ago 2026) | $2.00 / 1M tokens | $10.00 / 1M tokens | 200K tokens |

**Optimizaciones disponibles:**
- Prompt Caching: hasta 90% ahorro en tokens repetidos
- Batch Inference: 50% descuento vs on-demand (procesamiento diferido)

**Estimación por mensaje de chat (nuestro patrón):**
- System prompt + contexto herramientas: ~2,000 tokens input
- Respuesta del agente: ~800 tokens output
- Tool calls (2-3 por turno): ~1,500 tokens input + 500 tokens output
- **Costo por mensaje: ~$0.03 USD** (con Claude 3.5 Sonnet v2)

Content was rephrased for compliance with licensing restrictions.

---

## 5. Amazon Bedrock AgentCore Runtime

**Fuente:** [AgentCore Pricing](https://aws.amazon.com/bedrock/agentcore/pricing/)

| Concepto | Precio |
|---|---|
| CPU | $0.0895 / vCPU-hour |
| Memory | $0.00945 / GB-hour |

**Modelo de cobro:** Consumption-based — se cobra solo por tiempo activo de sesión (CPU + memoria usada).

**Nuestro patrón:** Los agentes se invocan via Lambda → AgentCore Runtime. Cada sesión dura lo que dura la consulta (~10-30 segundos), no se mantienen sesiones largas.

**Estimación por invocación (2 vCPU, 4 GB, 20s):**
- CPU: 2 × $0.0895 × (20/3600) = $0.001
- Memory: 4 × $0.00945 × (20/3600) = $0.0002
- **Total por invocación: ~$0.0012**

**Nota:** El costo dominante es el modelo (Claude), no el runtime de AgentCore.

---

## 6. Amazon OpenSearch Serverless (Knowledge Bases)

**Fuente:** [OpenSearch Service Pricing](https://aws.amazon.com/opensearch-service/pricing/) | [AWS re:Post - OCU Pricing Clarification](https://repost.aws/questions/QUPxlXCMbVSdqLvCqQcW-lMw/clarification-on-opensearch-serverless-pricing)

| Concepto | Precio |
|---|---|
| OCU (indexación o búsqueda) | $0.24 / OCU-hora |
| Storage (managed) | $0.024 / GB-mes |

**Configuración mínima:**
- Con redundancia (default): 1 OCU indexación + 1 OCU búsqueda = 2 OCUs mínimo
- Desde junio 2024: soporte para 0.5 OCU mínimo → 1 OCU total mínimo posible

**Costo mensual mínimo:**
- 2 OCUs × $0.24/h × 720h = **$345.60/mes** (24/7)
- 2 OCUs × $0.24/h × 240h = **$115.20/mes** (8h/día)
- 1 OCU (reducido) × $0.24/h × 720h = **$172.80/mes** (24/7)

**Nuestro uso:** Knowledge Base `ado-mobilityia-kb` con 5 documentos. OpenSearch Serverless se activa solo durante demo.

Content was rephrased for compliance with licensing restrictions.

---

## 7. Amazon API Gateway (HTTP API)

**Fuente:** [API Gateway Pricing](https://aws.amazon.com/api-gateway/pricing/) | [AWS Whitepaper Cost Optimization](https://docs.aws.amazon.com/whitepapers/latest/best-practices-api-gateway-private-apis-integration/cost-optimization.html)

| Concepto | Precio |
|---|---|
| Primeras 300M requests/mes | $1.00 / millón |
| 300M+ requests/mes | $0.90 / millón |
| Data transfer | Standard AWS data transfer rates |

**Free Tier (12 meses):** 1M HTTP API calls/mes

**Nuestro uso:** ~260,000 requests/mes (dashboard polling + chat) → dentro del free tier o ~$0.26/mes

---

## 8. Amazon S3

**Fuente:** [S3 Pricing](https://aws.amazon.com/s3/pricing/) | [CloudZero S3 Guide (2026)](https://www.cloudzero.com/blog/s3-pricing/)

| Concepto | Precio (Standard, us-east-2) |
|---|---|
| Storage (primeros 50 TB) | $0.023 / GB-mes |
| PUT/COPY/POST/LIST | $0.005 / 1,000 requests |
| GET/SELECT | $0.0004 / 1,000 requests |
| Data Transfer Out (primeros 100 GB) | Gratis |
| Data Transfer Out (hasta 10 TB) | $0.09 / GB |

**Nuestro uso:** ~500 MB de datos simulados + frontend → **~$0.01/mes** en storage

---

## 9. Amazon CloudFront

**Fuente:** [CloudFront Pricing](https://aws.amazon.com/cloudfront/pricing/)

| Concepto | Precio (North America) |
|---|---|
| Primeros 10 TB/mes | $0.085 / GB |
| Requests HTTP | $0.0075 / 10,000 |
| Requests HTTPS | $0.0100 / 10,000 |

**Free Tier (permanente):** 1 TB transfer + 10M requests/mes

**Nuestro uso:** Dashboard React ~700 KB, pocos usuarios demo → dentro del free tier

---

## 10. Amazon Cognito

**Fuente:** [Cognito Pricing](https://aws.amazon.com/cognito/pricing/)

| Concepto | Precio |
|---|---|
| Primeros 50,000 MAU | **Gratis** |
| 50,001 - 100,000 MAU | $0.0055 / MAU |

**Nuestro uso:** 1 usuario demo → **$0.00**

---

## 11. Amazon CloudWatch

**Fuente:** [CloudWatch Pricing](https://aws.amazon.com/cloudwatch/pricing/)

| Concepto | Precio |
|---|---|
| Log ingestion | $0.50 / GB |
| Log storage | $0.03 / GB-mes |
| Primeros 5 GB ingest/mes | Gratis |
| Primeros 5 GB archive/mes | Gratis |

**Nuestro uso:** 11 Lambdas, logs moderados → ~$2-5/mes

---

## Resumen de precios por servicio (escenario 10 buses, demo)

| Servicio | Precio unitario clave | Costo estimado/mes (demo) |
|---|---|---|
| Lambda | $0.20/1M req + $0.0000166667/GB-s | ~$5.50 |
| DynamoDB | $0.625/1M WRU + $0.125/1M RRU | ~$2.00 |
| SageMaker ml.m5.large | $0.115/hora | ~$7 (solo durante demo) |
| Bedrock Claude 3.5 Sonnet | $3/$15 per 1M input/output tokens | ~$18 (20 msgs/día) |
| AgentCore Runtime | $0.0895/vCPU-h + $0.00945/GB-h | ~$1.50 |
| OpenSearch Serverless | $0.24/OCU-h (2 OCU mín) | ~$29 (solo durante demo) |
| API Gateway HTTP | $1.00/1M requests | ~$0.26 |
| S3 | $0.023/GB-mes | ~$0.01 |
| CloudFront | $0.085/GB transfer | $0.00 (free tier) |
| Cognito | Gratis hasta 50K MAU | $0.00 |
| CloudWatch | $0.50/GB ingest | ~$3.00 |
| **TOTAL DEMO** | | **~$67/mes** |

---

## Fuentes consultadas

1. [AWS Lambda Pricing](https://aws.amazon.com/lambda/pricing/)
2. [CloudZero Lambda Pricing (Jul 2026)](https://www.cloudzero.com/blog/lambda-pricing/)
3. [DynamoDB On-Demand Pricing](https://aws.amazon.com/dynamodb/pricing/on-demand/)
4. [AWS Blog: DynamoDB Price Reduction Nov 2024](https://aws.amazon.com/blogs/database/new-amazon-dynamodb-lowers-pricing-for-on-demand-throughput-and-global-tables/)
5. [SageMaker Pricing](https://aws.amazon.com/sagemaker/pricing/)
6. [CloudZero SageMaker Guide](https://www.cloudzero.com/blog/sagemaker-pricing/)
7. [Amazon Bedrock Pricing](https://aws.amazon.com/bedrock/pricing/)
8. [Anthropic Claude Sonnet](https://www.anthropic.com/claude/sonnet)
9. [AgentCore Pricing](https://aws.amazon.com/bedrock/agentcore/pricing/)
10. [OpenSearch Service Pricing](https://aws.amazon.com/opensearch-service/pricing/)
11. [API Gateway Pricing](https://aws.amazon.com/api-gateway/pricing/)
12. [S3 Pricing](https://aws.amazon.com/s3/pricing/)
13. [CloudFront Pricing](https://aws.amazon.com/cloudfront/pricing/)
14. [Cognito Pricing](https://aws.amazon.com/cognito/pricing/)
15. [CloudWatch Pricing](https://aws.amazon.com/cloudwatch/pricing/)

---

## Notas importantes

1. **DynamoDB corregido:** Los precios anteriores en nuestro análisis usaban $1.25/M WRU (precio viejo). Post noviembre 2024, el precio correcto es **$0.625/M WRU** — 50% menos.

2. **AgentCore es nuevo:** El pricing de AgentCore Runtime es consumption-based (vCPU-hour + GB-hour). No tiene cargos fijos por tener un runtime desplegado, solo por sesiones activas.

3. **Claude Sonnet 4:** Si se migra a Sonnet 4 antes de septiembre 2026, el pricing introductorio es $2/$10 (33% menos que Sonnet 3.5 v2).

4. **OpenSearch Serverless es el gasto fijo más alto:** Para un hackathon/demo, vale la pena apagar este servicio fuera de horario. En producción, considerar FAISS local o Pinecone.
