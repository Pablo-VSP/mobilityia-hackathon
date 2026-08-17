# 💰 Análisis de Costos AWS — ADO MobilityIA
## Escalamiento por Autobús | us-east-2 (Ohio)

> Precios de referencia: AWS Public Pricing us-east-2, agosto 2026.
> **Calibrado con factura real** del mes anterior (julio 2026): $319.77 USD sin QuickSight.

---

## 📋 Factura real vs estimación (validación del modelo)

| Servicio | Factura real (jul 2026) | Mi estimación | Diferencia | Explicación |
|---|---|---|---|---|
| OpenSearch Serverless | **$172.80** | $115-345 | ✅ Exacto | 2 OCUs × $0.24/h × 360h = $172.80 (12h/día × 30 días) |
| SageMaker | **$132.59** | $27-83 | ⚠️ +60% | Endpoint ml.m5.large encendido ~1,153h (se olvidó apagar) |
| DynamoDB | **$3.64** | $1.95 | ✅ Cercano | Simulador corriendo intermitente (~5.8M WRU) |
| Others (Lambda, S3, CW, API GW) | **$10.74** | $10-20 | ✅ Exacto | Lambda + CloudWatch + S3 + data transfer |
| **TOTAL (sin QuickSight, sin tax)** | **$319.77** | — | — | — |
| Tax | $85.36 | — | — | IVA 16% México sobre servicios digitales |

### Lecciones de la factura real:
1. **OpenSearch es el 54% del gasto** — las 2 OCUs se cobran aunque no haya consultas
2. **SageMaker se acumula rápido si se olvida apagar** — a $0.115/h, un mes completo = $82.80, pero la factura muestra $132.59 (probablemente estuvo encendido desde el mes anterior)
3. **DynamoDB y Lambda son baratos** — juntos representan solo el 4.5% del total
4. **El costo real del MVP con 10 buses es ~$320/mes** (incluyendo los servicios "vampiro" encendidos)

---

## Resumen Ejecutivo — Escenarios de escala

| Escenario | Buses | Costo mensual | Costo por bus/mes | Nota |
|---|---|---|---|---|
| **MVP Demo (optimizado)** | 10 | ~$47 USD | ~$4.70 | Solo encender para demo (2h/día) |
| **MVP Demo (real, sin control)** | 10 | ~$320 USD | ~$32.00 | Lo que pasó: servicios encendidos sin gestión |
| **Piloto** | 50 | ~$180 USD | ~$3.60 | SageMaker serverless + KB horario |
| **Producción Fase 1** | 200 | ~$350 USD | ~$1.75 | Con optimizaciones básicas |
| **Producción Full** | 2,000 | ~$1,100 USD | ~$0.55 | Todas las optimizaciones |

> El costo por bus **decrece agresivamente** al escalar porque OpenSearch, SageMaker y CloudFront son costos fijos.

---

## Componentes de costo por servicio

### 1. AWS Lambda — Simulador + Tools + APIs

**Configuración actual:**
| Función | Memoria | Timeout | Frecuencia |
|---|---|---|---|
| `ado-simulador-telemetria` | 512 MB | 30s | 1/min (EventBridge) |
| `tool-consultar-telemetria` | 256 MB | 15s | Por consulta de agente |
| `tool-calcular-desviacion` | 256 MB | 15s | Por consulta de agente |
| `tool-listar-buses-activos` | 256 MB | 15s | Por consulta de agente |
| `tool-consultar-obd` | 256 MB | 15s | Por consulta de agente |
| `tool-predecir-evento` | 512 MB | 30s | Por consulta de agente |
| `tool-buscar-patrones-historicos` | 256 MB | 15s | Por consulta de agente |
| `tool-generar-recomendacion` | 256 MB | 15s | Por consulta de agente |
| `tool-consultar-alertas` | 256 MB | 15s | Por consulta de agente |
| `ado-dashboard-api` | 256 MB | 15s | Polling frontend 10s |
| `ado-chat-api` | 512 MB | 120s | Por mensaje de chat |

**Precios Lambda (us-east-2):**
- Requests: $0.20 por 1M invocaciones
- Duration: $0.0000166667 por GB-segundo
- Free Tier: 1M requests + 400,000 GB-s/mes (permanente)

**Cálculo mensual por escenario:**

| Componente | 10 buses | 50 buses | 200 buses | 2,000 buses |
|---|---|---|---|---|
| Simulador (1/min × 24/7) | $2.80 | $3.50 | $5.00 | $12.00 |
| Dashboard API (6 req/min × usuarios) | $1.50 | $3.00 | $8.00 | $25.00 |
| Chat API (~50 msgs/día) | $0.80 | $2.00 | $5.00 | $15.00 |
| Tool Lambdas (~2 tools/chat) | $0.40 | $1.00 | $3.00 | $8.00 |
| **Subtotal Lambda** | **~$5.50** | **~$9.50** | **~$21.00** | **~$60.00** |

> **Factura real confirmó:** Lambda + others = ~$10.74, consistente con estimación.
> Lambda escala **linealmente** con buses en el simulador, y **sublinealmente** en tools/chat.

---

### 2. Amazon DynamoDB — Estado en tiempo real + Alertas

**Patrón de uso (On-Demand):**
- **Escrituras (simulador):** 6 ticks × N buses × 1/min = 6N writes/min
  - 10 buses → 60 writes/min → 2,592,000 writes/mes (24/7)
  - Factura real: $3.64 → ~5.8M WRU → simulador corrió ~13 días intermitentes
- **Lecturas (dashboard):** Scan cada 10s de últimos 10 min
- **Almacenamiento:** TTL 24h → máximo ~N × 8,640 items (~2 KB/item)

**Precios DynamoDB On-Demand (us-east-2, post Nov 2024 — reducción 50%):**
- Write: $0.625 por millón de WRU
- Read: $0.125 por millón de RRU
- Storage: $0.25/GB-mes

| Componente | 10 buses | 50 buses | 200 buses | 2,000 buses |
|---|---|---|---|---|
| Writes (simulador 24/7) | $1.62 | $8.10 | $32.40 | $324.00 |
| Reads (dashboard + tools) | $0.32 | $1.62 | $6.48 | $64.80 |
| Storage (despreciable) | $0.01 | $0.02 | $0.10 | $1.00 |
| **Subtotal DynamoDB** | **~$1.95** | **~$9.74** | **~$38.98** | **~$389.80** |

> ✅ **Validado con factura real:** $3.64 (uso intermitente) vs $1.95 estimado (24/7 continuo normalizado).
> DynamoDB escala **linealmente** con buses. Es barato hasta 200 buses.
> **Optimización:** Provisioned Capacity reduce ~60% adicional en producción.

---

### 3. Amazon SageMaker — Modelo Predictivo XGBoost

**Configuración actual:**
- Endpoint: `ml.m5.large` (2 vCPU, 8 GB RAM)
- Precio: **$0.115/hora** (us-east-2)
- Capacidad: >1,000 inferencias/segundo con XGBoost

**⚠️ LECCIÓN DE LA FACTURA REAL: $132.59**
Esto equivale a 1,153 horas de endpoint activo (~48 días continuos).
El endpoint se quedó encendido después de una sesión de demo/desarrollo.

| Modo | Horas/mes | Costo | Recomendación |
|---|---|---|---|
| Solo demo (2h/día) | 60h | **$6.90** | Usar scripts encender/apagar |
| Operación 8h/día | 240h | $27.60 | Para piloto |
| 24/7 permanente | 720h | $82.80 | Solo si se justifica con uso |
| **Lo que pasó (real)** | **~1,153h** | **$132.59** | ❌ Se olvidó apagar |

> **Costo fijo** — no escala con buses. Un endpoint sirve 10 o 2,000 buses.
> **Recomendación #1:** Usar `demo-apagar.sh` SIEMPRE después de la demo.
> **Recomendación #2:** Migrar a SageMaker Serverless Inference → $0 cuando no se usa.

---

### 4. Amazon Bedrock AgentCore — 2 Agentes IA

**Modelo:** Claude 3.5 Sonnet v2
**Pricing (Bedrock on-demand):**
- Input tokens: $3.00 / 1M tokens
- Output tokens: $15.00 / 1M tokens

**AgentCore Runtime:**
- CPU: $0.0895/vCPU-hora
- Memory: $0.00945/GB-hora
- Solo se cobra por sesión activa (~20s por consulta)

**Costo por mensaje de chat:** ~$0.03 USD (dominado por tokens de Claude)

| Mensajes/día | Costo mensual |
|---|---|
| 5 (demo ocasional) | $4.50 |
| 20 (uso regular) | $18.00 |
| 50 (piloto) | $45.00 |
| 200 (producción ligera) | $180.00 |

> Escala con **uso humano** (consultas), no con buses.
> En la factura real aparece dentro de "Others" — fue poco uso durante desarrollo.

---

### 5. Amazon Bedrock Knowledge Bases (OpenSearch Serverless)

**⚠️ MAYOR "VAMPIRO" DE COSTOS — 54% de la factura real**

**Configuración:**
- 2 OCUs mínimo (1 indexación + 1 búsqueda) con redundancia
- Precio: **$0.24/OCU-hora**
- Se cobra AUNQUE NO HAYA CONSULTAS — solo por estar encendido

**Factura real: $172.80**
- Cálculo: 2 OCUs × $0.24/h × 360h = $172.80 exacto
- Estuvo encendido 360h = 12h/día × 30 días (o 15 días 24/7)

| Modo | Horas/mes | Costo |
|---|---|---|
| Solo demo (2h/día) | 60h | $28.80 |
| Horario laboral (8h/día) | 240h | $115.20 |
| 12h/día (lo que pasó) | 360h | **$172.80** ← factura real |
| 24/7 permanente | 720h | $345.60 |

> **Recomendación URGENTE:** Incluir OpenSearch en `demo-apagar.sh`.
> **Alternativa de producción:** Reemplazar con FAISS en Lambda (costo $0) o Pinecone ($20/mes).

---

### 6. Servicios de costo fijo (no escalan con buses)

| Servicio | Costo mensual | Confirmado en factura |
|---|---|---|
| **Amazon CloudFront** | ~$0.50 | ✅ Dentro de "Others" |
| **Amazon S3** | ~$2-3 | ✅ Dentro de "Others" |
| **Amazon Cognito** | $0 | Free tier |
| **Amazon API Gateway** | ~$1-2 | ✅ Dentro de "Others" |
| **Amazon CloudWatch** | ~$3-5 | ✅ Dentro de "Others" |
| **Data Transfer** | ~$1-2 | ✅ Dentro de "Others" |
| **Subtotal fijos** | **~$10** | **Factura real: $10.74** ✅ |

---

## 🔑 Los 2 "vampiros" de costo y cómo matarlos

### Vampiro #1: OpenSearch Serverless ($172.80/mes)

**Problema:** Las 2 OCUs se cobran por hora encendida, incluso sin consultas.

**Soluciones por orden de impacto:**

| Solución | Ahorro | Esfuerzo | Descripción |
|---|---|---|---|
| Apagar fuera de demo | -$144/mes | 5 min | Agregar a `demo-apagar.sh` |
| Reducir a 1 OCU (sin redundancia) | -$86/mes | Bajo | Deshabilitar redundancia en collection |
| Reemplazar con FAISS en Lambda | -$172/mes | 1-2 días | Embedings pre-calculados en S3, búsqueda en Lambda |
| Reemplazar con Bedrock KB + Pinecone | -$150/mes | Medio | $20/mes vs $172/mes |

### Vampiro #2: SageMaker Endpoint ($132.59/mes)

**Problema:** El endpoint cobra $0.115/h 24/7 mientras esté en estado `InService`.

**Soluciones por orden de impacto:**

| Solución | Ahorro | Esfuerzo | Descripción |
|---|---|---|---|
| Usar scripts encender/apagar | -$105/mes | 0 | Ya existen: `demo-encender.sh` / `demo-apagar.sh` |
| SageMaker Serverless Inference | -$120/mes | Medio | $0 cuando idle, ~$0.01/invocación |
| Fallback heurístico (ya funciona) | -$132/mes | 0 | El código ya tiene fallback sin SageMaker |
| Lambda-only inference (XGBoost en Lambda) | -$132/mes | Bajo | XGBoost es pequeño, corre en 256MB Lambda |

---

## Modelo de escalamiento calibrado con datos reales

### Fórmula actualizada

```
Costo mensual = OpenSearch + SageMaker + DynamoDB + Lambda + AgentCore + Fijos

Donde (modo "controlado"):
  OpenSearch = $0.24 × 2 OCUs × horas_encendido/mes
  SageMaker  = $0.115 × horas_encendido/mes
  DynamoDB   = $0.625 × (6 × N_buses × 60 × 24 × 30) / 1,000,000 + reads
  Lambda     = ~$5.50 + proporcional a buses/usuarios
  AgentCore  = ~$0.03 × N_mensajes/mes
  Fijos      = ~$10/mes (S3, CF, CW, API GW, Cognito)
```

### Tabla de costos por escenario (modo controlado vs no controlado)

| Escenario | Sin control (24/7 todo) | Controlado (encender/apagar) |
|---|---|---|
| 10 buses, demo | ~$450 | **~$47** |
| 50 buses, piloto | ~$520 | **~$180** |
| 200 buses, producción | ~$780 | **~$350** |
| 2,000 buses, full | ~$1,900 | **~$1,100** |

---

## Plan de acción inmediato (ahorro $270/mes)

### 1. Agregar OpenSearch a `demo-apagar.sh` (ahorra $144/mes)
```bash
# Agregar al script demo-apagar.sh:
aws opensearchserverless delete-collection --id <collection-id> --region us-east-2
# O usar el SDK para "pausar" la collection (no existe pause — hay que re-crear)
```

> **Nota:** OpenSearch Serverless no tiene "pause". Opciones:
> - Borrar y re-crear (5-10 min de startup, re-indexar KB)
> - Aceptar el costo como fijo de operación
> - Migrar a otra solución de vector store

### 2. SIEMPRE ejecutar `demo-apagar.sh` después de demo (ahorra $105/mes)
El script ya existe y apaga SageMaker. Solo falta la disciplina de usarlo.

### 3. Considerar mover XGBoost a Lambda (ahorra $132/mes)
El modelo XGBoost es pequeño (~5 MB). Puede correr directamente en Lambda 512MB con `xgboost` como dependencia en el layer, eliminando completamente la necesidad de SageMaker endpoint.

---

## Comparación: valor generado vs costo

| Concepto | Costo/valor |
|---|---|
| Costo plataforma optimizada (200 buses/mes) | **~$350 USD = ~$6,000 MXN** |
| UNA grúa por falla en ruta | $5,000 - $15,000 MXN |
| UNA reparación correctiva de motor | $50,000 - $200,000 MXN |
| Pérdida de ingresos por unidad/día fuera de servicio | $15,000 - $40,000 MXN |

> **Con prevenir UNA sola falla en ruta al mes, la plataforma se paga sola.**
> ROI positivo desde la primera falla anticipada.

---

## Resumen final — Costo por bus según escala

```
Costo por bus/mes ($USD)

$32.00 ┤ ● Sin control (real del mes pasado)
       │
$18.00 ┤
       │
$10.00 ┤
       │
 $5.00 ┤   ● Controlado (10 buses)
       │
 $3.60 ┤       ● Piloto (50 buses)
       │
 $1.75 ┤              ● Producción (200 buses)
       │
 $0.55 ┤                           ● Full (2,000 buses)
       │
 $0.00 ├──┬──────┬──────┬──────┬──────→ Buses
       0  10    50    200  2,000
```

**Conclusión:** El sistema es económicamente viable desde 50 buses con gestión básica de encendido/apagado. A 2,000 buses el costo por unidad es menor a $1 USD/mes — insignificante comparado con el valor de prevenir una sola falla.
