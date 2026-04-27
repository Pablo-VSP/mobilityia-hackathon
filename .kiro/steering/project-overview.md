---
inclusion: always
---

# 🚌 ADO MobilityIA — Visión General del Proyecto
## Hackathon AWS Builders League 2026

---

## Qué estamos construyendo

**ADO MobilityIA** es una plataforma de optimización de flota basada en inteligencia artificial, construida sobre **Amazon Bedrock AgentCore**. Transforma datos telemétricos simulados de autobuses de Mobility ADO en decisiones operativas accionables: optimiza el consumo de combustible, anticipa eventos de mantenimiento y fortalece el cumplimiento ambiental.

> **C-003:** No se usan métricas con valores numéricos específicos. Se usa lenguaje difuso: "mayor", "menor", "reducción", "mejora", "optimización".
> **C-004:** Los datos son **simulados** — no se usan datos reales de la flota ADO por seguridad de la información corporativa.
> **C-005:** Los agentes son de **Amazon Bedrock AgentCore** — no de Bedrock Agents clásico.
> **C-006:** Esquemas de datos alineados con los archivos reales en `models/` (telemetry-data, motor_spn, data_fault).
> **C-007:** Catálogo de fallas con `severidad_inferencia` para el modelo predictivo de SageMaker.

---

## Cliente

**Mobility ADO** — uno de los operadores de transporte terrestre de pasajeros más importantes de México.
- Más de 2,000 unidades en operación
- Cobertura nacional en múltiples estados
- Segmentos: económico, ejecutivo, lujo

---

## Problema central

Mobility ADO cuenta con infraestructura de telemetría (GPS, sensores, registros históricos) pero no la explota analíticamente. Existe una oportunidad de evolucionar hacia modelos de inteligencia operativa que traduzcan esos datos en decisiones oportunas:

- El combustible es el **mayor costo operativo** — sin visibilidad granular, no se puede controlar
- El mantenimiento es **reactivo** — sin predicción, las fallas ocurren en ruta con alto costo
- Sin datos estructurados de emisiones, el **cumplimiento regulatorio ambiental** es difícil de demostrar

---

## Consideraciones activas

| ID | Descripción |
|---|---|
| C-001 | MVP acotado para hackathon — último día de desarrollo |
| C-002 | Ingesta simulada con Lambda — sin IoT Core ni Kinesis |
| C-003 | Sin métricas numéricas específicas — lenguaje difuso en todas las comunicaciones |
| C-004 | Datos simulados — seguridad de información corporativa de Mobility ADO |
| C-005 | Agentes son de AgentCore — no de Bedrock Agents clásico |
| C-006 | Esquemas alineados con `models/` (telemetry-data, motor_spn, data_fault) |
| C-007 | Catálogo de fallas con `severidad_inferencia` para modelo predictivo |
| C-008 | Partición temporal: oct-dic 2020 para entrenamiento ML, enero 2021 para simulación en tiempo real |

---

## Solución MVP — 2 Agentes Autónomos de IA (AgentCore)

Dos agentes autónomos de IA desplegados en **Amazon Bedrock AgentCore** (C-005) que demuestran el mayor valor técnico y de negocio:

### 🔥 Agente 1 — Motor de Inteligencia de Combustible
- Detecta desviaciones de consumo por unidad y conductor (datos simulados en tiempo real)
- Genera alertas accionables en lenguaje natural (español)
- Identifica patrones: aceleración brusca, RPM fuera de rango, velocidad excesiva

### 🔧 Agente 2 — Mantenimiento Predictivo
- Analiza señales OBD simuladas: temperatura, presión de aceite, códigos de diagnóstico
- Compara contra patrones de fallas del dataset simulado
- Genera recomendaciones preventivas antes de que el evento ocurra

---

## Resultados esperados para la demo (lenguaje difuso — C-003)

| Área | Resultado esperado |
|---|---|
| Consumo de combustible | Mejora potencial por viaje identificada |
| Disponibilidad de flota | Mayor disponibilidad por anticipación de eventos |
| Variabilidad operativa | Reducción de variabilidad entre unidades |
| Cumplimiento ambiental | Métricas estimadas de reducción de CO₂ visibles |

---

## Stack tecnológico central

- **Amazon Bedrock AgentCore** — Orquestación de agentes autónomos (C-005)
- **Anthropic Claude 3.5 Sonnet** — Narrativas en lenguaje natural (español)
- **Amazon SageMaker** — Modelo predictivo de eventos mecánicos (con fallback heurístico)
- **Amazon S3** — Data Lake con datos **simulados** (C-004): telemetry-data, motor_spn, data_fault
- **AWS Lambda** — Simulador de ingesta en tiempo real (C-002) + 7 tools para agentes + dashboard API
- **Amazon DynamoDB** — Estado en tiempo real por unidad (pivoteo de SPNs)
- **Amazon Bedrock Knowledge Bases** — RAG con catálogo SPN, manuales técnicos, normas NOM-044
- **Amazon QuickSight** — Dashboard ejecutivo y métricas de emisiones CO₂ (o Streamlit como alternativa)
