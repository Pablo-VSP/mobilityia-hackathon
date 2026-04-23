---
inclusion: always
---

# 🚌 ADO Intelligence Platform — Visión General del Proyecto
## Hackathon AWS ITP LATAM

---

## Qué estamos construyendo

**ADO Intelligence Platform** es un sistema autónomo de optimización de flotas impulsado por agentes de IA usando **Amazon Bedrock AgentCore**. El sistema analiza datos telemétricos de autobuses de Mobility ADO para reducir consumo de combustible, anticipar mantenimiento preventivo y estandarizar la conducción eficiente.

## Cliente

**Mobility ADO** — Operador de transporte terrestre de pasajeros más grande de México.
- 2,000+ unidades en operación diaria
- Cobertura en 32 estados
- Segmentos: económico, ejecutivo, lujo

## Problema central

> "Gasto mucho en combustible, no sé por qué, y no puedo mejorar lo que no mido."

- Combustible = 35–45% del costo operativo total
- Mantenimiento reactivo destruye rentabilidad (correctivo cuesta 3–5x más)
- Variabilidad de consumo entre conductores de hasta 40% en la misma ruta
- Sin datos verificables de emisiones CO₂ para cumplimiento regulatorio

## Solución MVP (Hackathon — 5 días)

Dos agentes autónomos de IA que demuestran el mayor valor técnico y de negocio:

### 🔥 Agente 1 — Motor de Inteligencia de Combustible
- Detecta desviaciones de consumo por unidad y conductor en tiempo real (simulado)
- Genera alertas accionables en lenguaje natural (español)
- Identifica patrones: aceleración brusca, RPM fuera de rango, velocidad excesiva

### 🔧 Agente 2 — Mantenimiento Predictivo
- Analiza señales OBD: temperatura, presión de aceite, códigos de diagnóstico
- Compara contra patrones históricos de fallas de la flota
- Genera órdenes de trabajo preventivas antes de que la falla ocurra

## Resultados esperados para la demo

| Métrica | Objetivo |
|---|---|
| Reducción consumo combustible | 8–15% |
| Fallas anticipadas | 75–85% |
| Variabilidad entre conductores | De 18% → 7% |
| Reducción CO₂ (proyectada) | ~2,400 ton/90 días |

## Stack tecnológico central

- **Amazon Bedrock AgentCore** — Orquestación de agentes
- **Anthropic Claude** — Narrativas en lenguaje natural (español)
- **Amazon SageMaker** — Modelo predictivo de fallas
- **Amazon S3** — Data Lake con datos históricos migrados desde GCP
- **AWS Lambda** — Simulador de ingesta en tiempo real (reemplaza IoT Core + Kinesis)
- **Amazon DynamoDB** — Estado en tiempo real por unidad
- **Amazon Bedrock Knowledge Bases** — RAG con manuales técnicos y normas
- **Amazon QuickSight** — Dashboard ejecutivo y reporte de emisiones CO₂
