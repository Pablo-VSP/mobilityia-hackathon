---
inclusion: always
---

# 🏗️ Arquitectura MVP — ADO MobilityIA
## Hackathon AWS Builders League 2026 — Aplicando C-001, C-002, C-003, C-004, C-005, C-006 y C-007

---

## Principio rector

> Construir solo lo que se puede demostrar en vivo ante el jurado. Cada servicio AWS debe justificarse con una funcionalidad visible en la demo.
> Los datos son **simulados** (C-004). No se usan métricas numéricas específicas (C-003).
> Los agentes son de **AgentCore** (C-005). Esquemas alineados con `models/` (C-006).
> Catálogo de fallas con `severidad_inferencia` para modelo predictivo (C-007).

---

## Arquitectura simplificada MVP

```
┌─────────────────────────────────────────────────────────────┐
│  DATOS SIMULADOS (C-004)                                    │
│  Script generador de datos ──────────────► Amazon S3        │
│  (Python — telemetría y fallas simuladas)   (Data Lake)     │
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
│  NÚCLEO DE IA — Amazon Bedrock AgentCore (C-005)              │
│                                                             │
│  ┌─────────────────────┐  ┌─────────────────────────────┐  │
│  │ Agente Combustible  │  │ Agente Mantenimiento        │  │
│  │ • Lee DynamoDB      │  │ • Lee DynamoDB (OBD)        │  │
│  │ • Detecta desv.     │  │ • Consulta Knowledge Base   │  │
│  │ • Claude → alerta   │  │ • SageMaker → predicción    │  │
│  │   en español        │  │ • Claude → recomendación    │  │
│  └─────────────────────┘  └─────────────────────────────┘  │
│                                                             │
│  Knowledge Bases (RAG): manuales OBD simulados,            │
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

## Origen de datos — Simulado (C-004)

Los datos **no provienen de GCP ni de buses reales**. Se generan con un script Python que produce datos sintéticos realistas:

```
Script generador (Python)
  └── Genera CSV/Parquet simulados
        └── aws s3 cp → s3://ado-mobilityia-mvp/
              ├── telemetria-simulada/      ← lecturas de sensores ficticias
              ├── fallas-simuladas/         ← historial de eventos mecánicos
              └── knowledge-base/           ← manuales OBD, normas NOM-044
```

**Justificación:** Seguridad de la información corporativa de Mobility ADO. Los datos simulados replican fielmente la estructura y variabilidad de datos reales sin exponer información sensible.

---

## Servicios AWS del MVP (lista definitiva)

### Incluidos ✅
| Servicio | Rol en el MVP | Prioridad |
|---|---|---|
| **Amazon S3** | Data Lake — datos **simulados** (C-004) | 🔴 Crítico |
| **AWS Lambda** | Simulador de ingesta en tiempo real (C-002) | 🔴 Crítico |
| **Amazon DynamoDB** | Estado en tiempo real por unidad | 🔴 Crítico |
| **Amazon Bedrock AgentCore** | Orquestación de los 2 agentes autónomos | 🔴 Crítico |
| **Amazon Bedrock Knowledge Bases** | RAG con documentos técnicos | 🔴 Crítico |
| **Amazon Bedrock Guardrails** | Seguridad básica de respuestas | 🟡 Importante |
| **Anthropic Claude 3.5 Sonnet** | Narrativas en español | 🔴 Crítico |
| **Amazon SageMaker** | Modelo predictivo entrenado con datos simulados | 🟡 Importante |
| **Amazon QuickSight** | Dashboard demo para el jurado | 🟡 Importante |
| **AWS IAM** | Roles y permisos entre servicios | 🔴 Crítico |
| **Amazon CloudWatch** | Logs básicos para debugging | 🟡 Importante |

### Excluidos del MVP ❌ (por C-001 y C-002)
| Servicio | Razón de exclusión |
|---|---|
| ~~AWS IoT Core~~ | Reemplazado por Lambda simulador (C-002) |
| ~~Amazon Kinesis~~ | Reemplazado por Lambda simulador (C-002) |
| ~~Amazon Kinesis Firehose~~ | No necesario sin Kinesis |
| ~~Amazon Timestream~~ | DynamoDB cubre el caso de uso para el MVP |
| ~~Amazon Redshift~~ | S3 + Athena o QuickSight directo es suficiente |
| ~~AWS Glue~~ | Script Python de generación de datos es suficiente |
| ~~Amazon EMR~~ | Demasiado complejo para 5 días |
| ~~AWS Step Functions~~ | Lambda directa es suficiente para el MVP |
| ~~Amazon EventBridge~~ | No necesario en MVP |
| ~~Amazon SNS / SQS~~ | Alertas van directo al dashboard |
| ~~AWS Amplify~~ | QuickSight o Streamlit es más rápido |
| ~~Amazon Cognito~~ | Auth no es prioridad para demo |
| ~~AWS KMS~~ | Encriptación por defecto es suficiente |
| ~~AWS CloudTrail~~ | No necesario para el MVP |
| ~~AWS WAF~~ | No necesario para el MVP |
| ~~AWS X-Ray~~ | CloudWatch básico es suficiente |

---

## Flujo de datos detallado del MVP

### Paso 1 — Generación de datos simulados (C-004)
```python
# Script generador — produce datos sintéticos realistas
# NO usa datos reales de ADO por seguridad corporativa
generate_simulated_telemetry(
    n_buses=20,           # 20 buses ficticios para la demo
    n_routes=7,           # 7 rutas principales de ADO
    n_days=90,            # 90 días de historial simulado
    output='s3://ado-mobilityia-mvp/telemetria-simulada/'
)
generate_simulated_failures(
    n_events=500,         # 500 eventos de falla históricos simulados
    output='s3://ado-mobilityia-mvp/fallas-simuladas/'
)
```

### Paso 2 — Lambda Simulador (tiempo real simulado — C-002)
```python
def lambda_handler(event, context):
    # Lee registro simulado de S3 (por bus_id, offset)
    registro = leer_siguiente_registro_s3(bus_id, offset)

    # Escribe en DynamoDB como si fuera "ahora"
    dynamodb.put_item({
        'bus_id': registro['bus_id'],
        'timestamp': datetime.now().isoformat(),
        'velocidad_kmh': registro['velocidad_kmh'],
        'rpm': registro['rpm'],
        'consumo_lkm': registro['consumo_lkm'],
        'temperatura_motor_c': registro['temperatura_motor_c'],
        'codigo_obd': registro['codigo_obd'],
        ...
    })
    # Trigger: EventBridge Scheduler cada 10 segundos
```

### Paso 3 — Agentes Bedrock leen DynamoDB y actúan
```
DynamoDB (estado actual flota simulada)
  └── Agente Combustible
        ├── Tool: consultar_telemetria(bus_id)
        ├── Tool: calcular_desviacion(bus_id, ruta_id)
        └── Claude → "El Bus SIM-247 muestra un consumo superior
                       al patrón esperado en la ruta México-Puebla.
                       Se identificó un patrón de aceleración brusca
                       en los primeros tramos. Recomendación: ..."

  └── Agente Mantenimiento
        ├── Tool: consultar_obd(bus_id)
        ├── Tool: buscar_patrones_historicos(codigo_obd, temperatura)
        ├── SageMaker endpoint → probabilidad_evento(features)
        └── Claude → "El Bus SIM-089 presenta señales consistentes
                       con patrones previos a eventos de refrigeración.
                       Se recomienda revisión preventiva esta semana.
                       Orden de trabajo generada: OT-2026-0423-089"
```

### Paso 4 — Visualización para el jurado
```
QuickSight Dashboard:
  ├── Estado de flota simulada en tiempo real
  ├── Buses con mayor desviación de consumo
  ├── Recomendaciones de mantenimiento activas
  ├── Estimación de mejora en eficiencia operativa
  └── Métricas estimadas de reducción de CO₂
```

---

## Decisiones de arquitectura clave

1. **Datos simulados desde el inicio (C-004)** — El script generador crea datos sintéticos realistas que replican la variabilidad de una flota real sin exponer información corporativa sensible.

2. **Lambda como simulador (C-002)** — Se dispara con EventBridge Scheduler durante la demo para mostrar "datos en vivo". El jurado ve el sistema reaccionando en tiempo real.

3. **DynamoDB como hub central** — Tabla `ado-telemetria-live` con `autobus` como PK y `timestamp` como SK. Estado consolidado por pivoteo de SPNs.

4. **Knowledge Base con S3** — Catálogo SPN (`motor_spn.json`), catálogo de fallas con severidad inferida (C-007), manuales técnicos y normas NOM-044 indexados en Bedrock Knowledge Bases para RAG.

5. **SageMaker entrenado con datos simulados** — El modelo predictivo se entrena con features derivadas de los 19 SPNs de mantenimiento + historial de fallas con `severidad_inferencia` (C-007). Fallback heurístico implementado en Lambda.

6. **Lenguaje difuso en todas las respuestas (C-003)** — Los agentes están instruidos para no mencionar porcentajes ni valores monetarios específicos. Usan términos como "mejora significativa", "reducción notable", "mayor disponibilidad".

7. **Agentes en AgentCore (C-005)** — Los agentes se despliegan en Amazon Bedrock AgentCore, no en Bedrock Agents clásico. Esto permite orquestación nativa de agentes autónomos con memoria, herramientas y RAG integrados.
