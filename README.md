# 🚌 ADO MobilityIA
## Hackathon AWS Builders League 2026 — Amazon Bedrock AgentCore

Plataforma de optimización de flota basada en inteligencia artificial para **Mobility ADO**, construida sobre **Amazon Bedrock AgentCore** (C-005). Transforma datos telemétricos simulados en decisiones operativas accionables: optimiza el consumo de combustible, anticipa eventos de mantenimiento y fortalece el cumplimiento ambiental.

> **C-004:** Los datos utilizados en este MVP son **simulados** por razones de seguridad de la información corporativa.
> **C-003:** No se usan métricas con valores numéricos específicos — lenguaje difuso en todas las comunicaciones.
> **C-005:** Los agentes son de **AgentCore**, no de Bedrock Agents clásico.

---

## 🎯 El problema

> "Mobility ADO ya tiene los datos. El problema es que esos datos nunca se convirtieron en inteligencia operativa."

- El combustible es el **mayor costo operativo** — sin visibilidad granular, no se puede controlar
- El mantenimiento es **reactivo** — las unidades fallan en carretera porque no hay forma de anticiparlo
- Sin datos estructurados de emisiones, el **cumplimiento regulatorio ambiental** es difícil de demostrar

---

## 🤖 La solución — 2 Agentes Autónomos de IA (AgentCore)

### 🔥 Agente de Inteligencia de Combustible
Analiza 15 SPNs de conducción y rendimiento en tiempo real (datos simulados), detecta desviaciones de consumo, identifica causas (aceleración brusca, RPM fuera de rango, bajo uso de cruise control) y genera alertas accionables en español.

### 🔧 Agente de Mantenimiento Predictivo
Analiza 19 SPNs de mantenimiento (temperatura, presión, balatas, voltaje), compara contra patrones históricos de fallas con severidad inferida (C-007), invoca modelo ML en SageMaker (con fallback heurístico) y genera recomendaciones preventivas.

---

## 🏗️ Arquitectura MVP

```
Datos simulados (Parquet) → Amazon S3 (Data Lake)
                                    │
                          AWS Lambda Simulador
                     (pivotea SPNs → estado consolidado)
                                    │
                             Amazon DynamoDB
                          (estado live por bus)
                                    │
                  Amazon Bedrock AgentCore (C-005)
             ┌──────────────────────────────────┐
             │  Agente Combustible (3 tools)     │
             │  Agente Mantenimiento (4 tools)   │
             │  Knowledge Bases (RAG)            │
             │  Claude 3.5 Sonnet                │
             │  SageMaker Endpoint (+ fallback)  │
             └──────────────────────────────────┘
                                    │
                        Dashboard (QuickSight/Streamlit)
```

---

## 📊 Impacto estimado (lenguaje difuso — C-003)

| Área | Resultado esperado |
|---|---|
| Consumo de combustible | Mejora potencial por viaje identificada |
| Disponibilidad de flota | Mayor disponibilidad por anticipación de eventos |
| Variabilidad operativa | Reducción sostenida entre unidades |
| Cumplimiento ambiental | Métricas estimadas de reducción de CO₂ visibles |

---

## 📁 Estructura del repositorio

```
├── README.md
├── .kiro/
│   ├── steering/                        # Guías del proyecto para Kiro AI
│   │   ├── project-overview.md          # Visión general + consideraciones C-001 a C-007
│   │   ├── arquitectura-mvp.md          # Arquitectura y servicios AWS
│   │   ├── plan-5-dias.md               # Plan de ejecución (día final)
│   │   ├── agentes-prompts.md           # System prompts AgentCore + tools
│   │   ├── data-schema.md               # Esquemas alineados con models/ (C-006)
│   │   ├── guion-demo.md                # Guión de presentación
│   │   └── consideraciones.md           # Control de decisiones C-001 a C-007
│   └── specs/                           # Especificaciones de implementación
├── lambda-functions/
│   ├── ado-simulador-telemetria/        # Simulador de ingesta (pivoteo SPN)
│   ├── tool-consultar-telemetria/       # Tool Agente Combustible
│   ├── tool-calcular-desviacion/        # Tool Agente Combustible
│   ├── tool-listar-buses-activos/       # Tool Agente Combustible
│   ├── tool-consultar-obd/              # Tool Agente Mantenimiento
│   ├── tool-predecir-evento/            # Tool Agente Mantenimiento (+ fallback)
│   ├── tool-buscar-patrones-historicos/ # Tool Agente Mantenimiento
│   ├── tool-generar-recomendacion/      # Tool Agente Mantenimiento
│   ├── ado-dashboard-api/               # API REST para dashboard
│   └── layers/ado-common/               # Shared layer (SPN catalog, utils)
├── models/                              # Esquemas de datos reales (C-006)
│   ├── telemetry-data.JSON              # 17 campos de telemetría por SPN
│   ├── motor_spn.JSON                   # 36 SPNs con rangos y umbrales
│   └── data_fault.JSON                  # 23 campos de fallas
├── datos_spn/
│   ├── data.JSON                        # Catálogo de 36 SPNs confirmados
│   └── fault_data_catalog.JSON          # Fallas con severidad_inferencia (C-007)
├── docs/
│   ├── lambdas-plan.md                  # Especificaciones técnicas de Lambdas
│   ├── plan-agentes-bedrock.md          # Plan de agentes AgentCore
│   └── sagemaker-modelo-predictivo-plan.md  # Plan de modelo ML
└── criterios-evaluacion-hackathon.md    # Criterios del jurado
```

---

## 🚀 Stack tecnológico

- **Amazon Bedrock AgentCore** — Orquestación de agentes autónomos (C-005)
- **Anthropic Claude 3.5 Sonnet** — Narrativas operativas en español
- **Amazon Bedrock Knowledge Bases** — RAG con catálogo SPN y manuales técnicos
- **Amazon SageMaker** — Modelo predictivo (XGBoost) con fallback heurístico
- **Amazon S3** — Data Lake con datos simulados (telemetry-data, motor_spn, data_fault)
- **AWS Lambda** — 9 funciones: simulador + 7 tools + dashboard API
- **Amazon DynamoDB** — Estado en tiempo real por unidad (pivoteo de SPNs)
- **Amazon QuickSight** — Dashboard ejecutivo (o Streamlit como alternativa)

---

## 📋 Consideraciones del proyecto

| ID | Descripción | Estado |
|---|---|---|
| C-001 | MVP acotado para hackathon | ✅ Aplicada |
| C-002 | Ingesta simulada con Lambda — sin IoT Core ni Kinesis | ✅ Aplicada |
| C-003 | Sin métricas numéricas específicas — lenguaje difuso | ✅ Aplicada |
| C-004 | Datos simulados — seguridad corporativa | ✅ Aplicada |
| C-005 | Agentes de AgentCore — no Bedrock Agents clásico | ✅ Aplicada |
| C-006 | Esquemas alineados con `models/` | ✅ Aplicada |
| C-007 | Catálogo de fallas con `severidad_inferencia` | ✅ Aplicada |

---

## 👥 Cliente

**Mobility ADO** — uno de los operadores de transporte terrestre de pasajeros más importantes de México.

---

*Hackathon AWS Builders League 2026 | Amazon Bedrock AgentCore*
