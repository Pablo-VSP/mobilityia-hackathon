# 🚌 ADO Intelligence Platform
## Hackathon AWS ITP LATAM — Working Backwards con Amazon Bedrock AgentCore

Sistema autónomo de optimización de flotas para **Mobility ADO**, construido sobre **Amazon Bedrock AgentCore**. Convierte telemetría de autobuses en decisiones operativas en tiempo real: reduce consumo de combustible, anticipa fallas mecánicas y genera evidencia verificable de reducción de emisiones CO₂.

---

## 🎯 El problema

> "Gasto mucho en combustible, no sé por qué, y no puedo mejorar lo que no mido."

- Combustible = **35–45%** del costo operativo total de ADO
- Variabilidad de consumo entre conductores: hasta **40%** en la misma ruta
- Mantenimiento correctivo cuesta **3–5x** más que el preventivo
- Sin datos verificables de emisiones CO₂ para cumplimiento regulatorio (NOM-044)

---

## 🤖 La solución — 2 Agentes Autónomos de IA

### 🔥 Agente de Inteligencia de Combustible
Detecta desviaciones de consumo en tiempo real, identifica causas (aceleración brusca, RPM fuera de rango) y genera alertas accionables en español con impacto económico cuantificado en MXN.

### 🔧 Agente de Mantenimiento Predictivo
Analiza señales OBD, compara contra patrones históricos de fallas via RAG, invoca modelo ML en SageMaker y genera órdenes de trabajo preventivas antes de que la falla ocurra.

---

## 🏗️ Arquitectura MVP (Hackathon — 5 días)

```
GCP (BigQuery/GCS) ──► Amazon S3 (Data Lake)
                              │
                    AWS Lambda Simulador
                    (ingesta tiempo real)
                              │
                       Amazon DynamoDB
                    (estado live por bus)
                              │
              Amazon Bedrock AgentCore
         ┌────────────────────────────────┐
         │  Agente Combustible            │
         │  Agente Mantenimiento          │
         │  Knowledge Bases (RAG)         │
         │  Claude 3.5 Sonnet             │
         │  SageMaker Endpoint            │
         └────────────────────────────────┘
                              │
                  Amazon QuickSight
              (Dashboard ejecutivo)
```

---

## 📊 Resultados esperados

| Métrica | Objetivo |
|---|---|
| Reducción consumo combustible | 8–15% (~$2.8M MXN/mes) |
| Fallas mecánicas anticipadas | 75–85% |
| Variabilidad entre conductores | De 18% → 7% |
| Reducción CO₂ | ~2,400 ton/90 días |

---

## 📁 Estructura del repositorio

```
├── README.md
├── .kiro/
│   └── steering/                    # Guías del proyecto para Kiro AI
│       ├── project-overview.md      # Visión general
│       ├── arquitectura-mvp.md      # Arquitectura y servicios AWS
│       ├── plan-5-dias.md           # Plan de desarrollo día a día
│       ├── agentes-prompts.md       # System prompts y tools de los agentes
│       ├── data-schema.md           # Esquemas de datos (S3, DynamoDB, SageMaker)
│       ├── guion-demo.md            # Guión de presentación ante el jurado
│       └── consideraciones.md      # Control de decisiones del proyecto
├── ADO-Intelligence-Platform-AWS-Architecture.md   # Arquitectura completa
├── criterios-evaluacion-hackathon.md               # Criterios de evaluación
├── diagrama_arquitectura_mermaid.md                # Diagrama Mermaid para draw.io
└── ITP-LATAM-WB-Workshop.md                        # Working Backwards original
```

---

## 🚀 Stack tecnológico

- **Amazon Bedrock AgentCore** — Orquestación de agentes autónomos
- **Anthropic Claude 3.5 Sonnet** — Narrativas operativas en español
- **Amazon Bedrock Knowledge Bases** — RAG con manuales OBD y normas NOM-044
- **Amazon SageMaker** — Modelo predictivo de fallas (XGBoost)
- **Amazon S3** — Data Lake con datos históricos migrados desde GCP
- **AWS Lambda** — Simulador de ingesta en tiempo real
- **Amazon DynamoDB** — Estado en tiempo real por unidad
- **Amazon QuickSight** — Dashboard ejecutivo y reporte de emisiones CO₂

---

## 👥 Cliente

**Mobility ADO** — Operador de transporte terrestre de pasajeros más grande de México.
32 estados · 2,000+ unidades · Segmentos: económico, ejecutivo, lujo.

---

*Hackathon AWS ITP LATAM | Working Backwards powered by AI*
