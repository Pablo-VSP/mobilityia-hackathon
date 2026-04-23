---
inclusion: always
---

# 🏗️ Arquitectura MVP — ADO Intelligence Platform
## Hackathon AWS (5 días) — Aplicando C-001 y C-002

---

## Principio rector

> Construir solo lo que se puede demostrar en vivo ante el jurado. Cada servicio AWS debe justificarse con una funcionalidad visible en la demo.

---

## Arquitectura simplificada MVP

```
┌─────────────────────────────────────────────────────────────┐
│  DATOS HISTÓRICOS (GCP → S3)                                │
│  BigQuery / GCS ──────────────────────► Amazon S3           │
│                                         (Data Lake)         │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  SIMULADOR DE TIEMPO REAL (C-002)                           │
│  AWS Lambda ──► Lee S3 ──► Escribe DynamoDB (estado live)   │
│  (dispara cada N segundos, simula bus en movimiento)        │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  NÚCLEO DE IA — Amazon Bedrock AgentCore                    │
│                                                             │
│  ┌─────────────────────┐  ┌─────────────────────────────┐  │
│  │ Agente Combustible  │  │ Agente Mantenimiento        │  │
│  │ • Lee DynamoDB      │  │ • Lee DynamoDB (OBD)        │  │
│  │ • Detecta desv.     │  │ • Consulta Knowledge Base   │  │
│  │ • Claude → alerta   │  │ • SageMaker → predicción    │  │
│  │   en español        │  │ • Claude → orden de trabajo │  │
│  └─────────────────────┘  └─────────────────────────────┘  │
│                                                             │
│  Knowledge Bases (RAG): manuales OBD, histórico fallas,    │
│  normas NOM-044, umbrales de eficiencia por ruta           │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  PRESENTACIÓN                                               │
│  Amazon QuickSight ──► Dashboard ejecutivo + CO₂           │
│  (o Streamlit/Amplify si QuickSight no está disponible)    │
└─────────────────────────────────────────────────────────────┘
```

---

## Servicios AWS del MVP (lista definitiva)

### Incluidos ✅
| Servicio | Rol en el MVP | Prioridad |
|---|---|---|
| **Amazon S3** | Data Lake — datos históricos migrados de GCP | 🔴 Crítico |
| **AWS Lambda** | Simulador de ingesta en tiempo real | 🔴 Crítico |
| **Amazon DynamoDB** | Estado en tiempo real por unidad (escritura Lambda, lectura Agentes) | 🔴 Crítico |
| **Amazon Bedrock AgentCore** | Orquestación de los 2 agentes autónomos | 🔴 Crítico |
| **Amazon Bedrock Knowledge Bases** | RAG con documentos técnicos | 🔴 Crítico |
| **Amazon Bedrock Guardrails** | Seguridad básica de respuestas | 🟡 Importante |
| **Anthropic Claude (via Bedrock)** | Generación de narrativas en español | 🔴 Crítico |
| **Amazon SageMaker** | Modelo predictivo de fallas (puede ser endpoint pre-entrenado) | 🟡 Importante |
| **Amazon QuickSight** | Dashboard demo para el jurado | 🟡 Importante |
| **AWS IAM** | Roles y permisos entre servicios | 🔴 Crítico |
| **Amazon CloudWatch** | Logs básicos para debugging durante el hackathon | 🟡 Importante |

### Excluidos del MVP ❌ (por C-001 y C-002)
| Servicio | Razón de exclusión |
|---|---|
| ~~AWS IoT Core~~ | Reemplazado por Lambda simulador (C-002) |
| ~~Amazon Kinesis~~ | Reemplazado por Lambda simulador (C-002) |
| ~~Amazon Kinesis Firehose~~ | No necesario sin Kinesis |
| ~~Amazon Timestream~~ | DynamoDB cubre el caso de uso para el MVP |
| ~~Amazon Redshift~~ | S3 + Athena o QuickSight directo es suficiente |
| ~~AWS Glue~~ | ETL manual o script Python para la migración |
| ~~Amazon EMR~~ | Demasiado complejo para 5 días |
| ~~AWS Step Functions~~ | Lambda directa es suficiente para el MVP |
| ~~Amazon EventBridge~~ | No necesario en MVP |
| ~~Amazon SNS / SQS~~ | No necesario en MVP (alertas van directo al dashboard) |
| ~~AWS Amplify~~ | QuickSight o Streamlit es más rápido de implementar |
| ~~Amazon Cognito~~ | Auth no es prioridad para demo del hackathon |
| ~~AWS KMS~~ | Encriptación por defecto de S3/DynamoDB es suficiente |
| ~~AWS CloudTrail~~ | No necesario para el MVP |
| ~~AWS WAF~~ | No necesario para el MVP |
| ~~AWS X-Ray~~ | CloudWatch básico es suficiente |

---

## Flujo de datos detallado del MVP

### Paso 1 — Migración GCP → S3 (pre-hackathon o Día 1)
```
GCP (BigQuery / GCS)
  └── Export CSV/Parquet
        └── aws s3 cp / Transfer Service
              └── s3://ado-intelligence-mvp/
                    ├── telemetria-historica/     ← datos de buses
                    ├── fallas-historicas/        ← historial de mantenimiento
                    └── knowledge-base/           ← manuales, normas OBD
```

### Paso 2 — Lambda Simulador (tiempo real simulado)
```python
# Pseudocódigo del simulador
def lambda_handler(event, context):
    # Lee registro histórico de S3 (por bus_id, timestamp)
    registro = leer_siguiente_registro_s3(bus_id, offset)
    
    # Escribe en DynamoDB como si fuera "ahora"
    dynamodb.put_item({
        'bus_id': registro['bus_id'],
        'timestamp': datetime.now().isoformat(),
        'velocidad': registro['velocidad'],
        'rpm': registro['rpm'],
        'consumo_combustible': registro['consumo'],
        'temperatura_motor': registro['temp_motor'],
        'codigo_obd': registro['obd'],
        ...
    })
    
    # Trigger: EventBridge Scheduler cada 5 segundos (o API call manual para demo)
```

### Paso 3 — Agentes Bedrock leen DynamoDB y actúan
```
DynamoDB (estado actual flota)
  └── Agente Combustible
        ├── Tool: consultar_telemetria(bus_id)
        ├── Tool: calcular_desviacion(bus_id, ruta_id)
        └── Claude → "El Bus 247 consume 18% más de lo esperado en
                       la ruta México-Puebla. Causa probable: aceleración
                       brusca en los primeros 40 km. Recomendación: ..."

  └── Agente Mantenimiento
        ├── Tool: consultar_señales_obd(bus_id)
        ├── Tool: buscar_patrones_historicos(codigo_obd, temperatura)
        ├── SageMaker endpoint → probabilidad_falla(features)
        └── Claude → "El Bus 089 muestra patrón de temperatura que
                       precedió falla de bomba de agua en 23 casos.
                       Probabilidad de falla en 11 días: 87%. Orden
                       de trabajo generada: OT-2026-0422-089"
```

### Paso 4 — Visualización para el jurado
```
QuickSight Dashboard:
  ├── Mapa de flota en tiempo real (simulado)
  ├── Top 10 buses con mayor desviación de consumo
  ├── Alertas de mantenimiento predictivo activas
  ├── Ahorro proyectado en combustible ($MXN)
  └── Reducción de CO₂ acumulada (toneladas)
```

---

## Decisiones de arquitectura clave

1. **Lambda como simulador** — Se dispara manualmente o con EventBridge Scheduler durante la demo para mostrar "datos en vivo". El jurado ve el sistema reaccionando en tiempo real.

2. **DynamoDB como hub central** — Punto de lectura para ambos agentes. Tabla principal: `ado-telemetria` con `bus_id` como PK y `timestamp` como SK.

3. **Knowledge Base con S3** — Los documentos técnicos (manuales OBD, normas NOM-044, umbrales por ruta) se cargan en S3 y se indexan en Bedrock Knowledge Bases para RAG.

4. **SageMaker como endpoint** — Si el tiempo no alcanza, el modelo predictivo puede ser un endpoint pre-entrenado con datos históricos de GCP, o incluso un modelo de regresión logística simple entrenado en SageMaker Studio.

5. **Un solo AWS Account** — Todo en la misma cuenta y región (`us-east-1`) para simplificar permisos y latencia.
