# 🚌 ADO MobilityIA
## Hackathon AWS Builders League 2026 — Working Backwards con Amazon Bedrock AgentCore

Plataforma de optimización de flota basada en inteligencia artificial para **Mobility ADO**, construida sobre **Amazon Bedrock AgentCore**. Transforma datos telemétricos simulados en decisiones operativas accionables: optimiza el consumo de combustible, anticipa eventos de mantenimiento y fortalece el cumplimiento ambiental.

> **Nota:** Los datos utilizados en este MVP son **simulados** por razones de seguridad de la información corporativa. No se utilizan datos reales de la flota de Mobility ADO.

---

## 🎯 El problema

> "Mobility ADO ya tiene los datos. El problema es que esos datos nunca se convirtieron en inteligencia operativa."

- El combustible es el **mayor costo operativo** — sin visibilidad granular, no se puede controlar
- El mantenimiento es **reactivo** — las unidades fallan en carretera porque no hay forma de anticiparlo
- Sin datos estructurados de emisiones, el **cumplimiento regulatorio ambiental** es difícil de demostrar

---

## 🤖 La solución — 2 Agentes Autónomos de IA

### 🔥 Agente de Inteligencia de Combustible
Detecta desviaciones de consumo en tiempo real (datos simulados), identifica causas (aceleración brusca, RPM fuera de rango) y genera alertas accionables en español con impacto operativo cualitativo.

### 🔧 Agente de Mantenimiento Predictivo
Analiza señales OBD simuladas, compara contra patrones históricos via RAG, invoca modelo ML en SageMaker y genera recomendaciones preventivas antes de que el evento ocurra.

---

## 🏗️ Arquitectura MVP (Hackathon — 5 días)

```
Script Python (datos simulados) → Amazon S3 (Data Lake)
                                          │
                                AWS Lambda Simulador
                                (ingesta tiempo real)
                                          │
                                   Amazon DynamoDB
                                (estado live por bus)
                                          │
                          Amazon Bedrock AgentCore
                     ┌────────────────────────────────┐
                     │  Agente Combustible             │
                     │  Agente Mantenimiento           │
                     │  Knowledge Bases (RAG)          │
                     │  Claude 3.5 Sonnet              │
                     │  SageMaker Endpoint             │
                     └────────────────────────────────┘
                                          │
                              Amazon QuickSight
                          (Dashboard ejecutivo)
```

---

## 📊 Impacto estimado

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
│   └── steering/                        # Guías del proyecto para Kiro AI
│       ├── project-overview.md          # Visión general
│       ├── arquitectura-mvp.md          # Arquitectura y servicios AWS
│       ├── plan-5-dias.md               # Plan de desarrollo día a día
│       ├── agentes-prompts.md           # System prompts y tools de los agentes
│       ├── data-schema.md               # Esquemas de datos (S3, DynamoDB, SageMaker)
│       ├── guion-demo.md                # Guión de presentación ante el jurado
│       └── consideraciones.md          # Control de decisiones del proyecto
├── ADO-Intelligence-Platform-AWS-Architecture.md   # Arquitectura completa
├── criterios-evaluacion-hackathon.md               # Criterios de evaluación
├── diagrama_arquitectura_mermaid.md                # Diagrama Mermaid para draw.io
├── diagrama_arch.drawio                            # Diagrama draw.io
└── ITP-LATAM-WB-Workshop.md                        # Working Backwards original
```

---

## 🚀 Stack tecnológico

- **Amazon Bedrock AgentCore** — Orquestación de agentes autónomos
- **Anthropic Claude 3.5 Sonnet** — Narrativas operativas en español
- **Amazon Bedrock Knowledge Bases** — RAG con manuales OBD y normas NOM-044
- **Amazon SageMaker** — Modelo predictivo entrenado con datos simulados
- **Amazon S3** — Data Lake con datos simulados
- **AWS Lambda** — Simulador de ingesta en tiempo real
- **Amazon DynamoDB** — Estado en tiempo real por unidad
- **Amazon QuickSight** — Dashboard ejecutivo y métricas de emisiones CO₂

---

## 📋 Consideraciones del proyecto

| ID | Descripción |
|---|---|
| C-001 | MVP acotado para hackathon — máximo 5 días de desarrollo |
| C-002 | Ingesta simulada con Lambda — sin IoT Core ni Kinesis |
| C-003 | Sin métricas numéricas específicas — lenguaje difuso en todas las comunicaciones |
| C-004 | Datos simulados — seguridad de información corporativa de Mobility ADO |

---

## 👥 Cliente

**Mobility ADO** — uno de los operadores de transporte terrestre de pasajeros más importantes de México.
Múltiples estados · 2,000+ unidades · Segmentos: económico, ejecutivo, lujo.

---

*Hackathon AWS Builders League 2026 | Working Backwards powered by AI*
