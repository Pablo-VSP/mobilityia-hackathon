# Criterios de Evaluación — ADO Intelligence Platform  
## Hackathon AWS Builders League 2026

---

## 1. ¿Quién es el cliente?

**Mobility ADO** — uno de los operadores de transporte terrestre de pasajeros más importantes de México.

- Opera más de **2,000 autobuses** en el país  
- Ofrece tres niveles de servicio: económico, ejecutivo y lujo  
- Gestiona la venta de boletos a través de taquillas físicas, web y app móvil  

**Los usuarios del sistema** son cuatro perfiles clave:

| Perfil | Rol en el sistema | Motivación principal |
|---|---|---|
| Director de Operaciones | Consume dashboards ejecutivos y reportes de CO₂ | Optimización de costos y cumplimiento regulatorio |
| Supervisor de Flota | Recibe alertas y gestiona órdenes de trabajo | Continuidad operativa y eficiencia en ruta |
| Conductor | Recibe retroalimentación de conducción | Desarrollo profesional y mejora continua |
| Taller Mecánico | Ejecuta órdenes de trabajo preventivas | Planeación eficiente y diagnósticos oportunos |

---

## 2. ¿Cuál es el problema u oportunidad del cliente?

### Contexto operativo

Mobility ADO cuenta con una infraestructura sólida de telemetría (GPS, sensores y registros históricos), lo que representa una base estratégica de información con alto potencial de aprovechamiento.

Actualmente, existe una **oportunidad de evolucionar el uso de estos datos hacia modelos avanzados de inteligencia operativa**, que permitan traducir la información en decisiones oportunas y medibles.

### Áreas clave de oportunidad

**Optimización del consumo de combustible**  
El combustible representa el **mayor costo operativo**. Contar con visibilidad más granular sobre los factores que influyen en el consumo — como condiciones de ruta, estilo de conducción o desempeño del vehículo — abre la posibilidad de generar eficiencias relevantes a escala de flota.

**Evolución hacia mantenimiento predictivo**  
La incorporación de modelos predictivos permitiría anticipar comportamientos mecánicos y programar intervenciones con mayor precisión. Esto facilita una mejor planeación operativa, optimización de costos y mayor disponibilidad de unidades.

**Fortalecimiento de la trazabilidad y cumplimiento ambiental**  
Ante un entorno regulatorio cada vez más enfocado en sostenibilidad, contar con información estructurada y verificable sobre emisiones de CO₂ representa una ventaja estratégica.

### La oportunidad estratégica

El sector de transporte de pasajeros en México se encuentra en un punto clave para integrar **modelos de inteligencia artificial aplicada a la operación en tiempo real**.

Mobility ADO ya dispone de los elementos fundamentales (datos, infraestructura y escala). La integración de capacidades avanzadas de análisis representa una oportunidad para **establecer un nuevo estándar operativo en la industria**.

---

## 3. ¿Cuál es la solución y el principal beneficio para el cliente?

### La solución: ADO MobilityIA

Una plataforma de optimización de flota basada en inteligencia artificial, construida sobre **Amazon Bedrock AgentCore**, que transforma datos telemétricos en decisiones operativas accionables.

#### Arquitectura general

Datos históricos GCP → S3 (Data Lake) → Lambda Simulador → DynamoDB
↓
Amazon Bedrock AgentCore
┌──────────────────────────────┐
│ Agente Combustible │
│ Agente Mantenimiento │
└──────────────────────────────┘
↓
Dashboard QuickSight

### Componentes principales

**Agente de Inteligencia de Combustible**  
Analiza el consumo en tiempo real, identifica desviaciones respecto a patrones históricos y genera recomendaciones claras para optimizar la eficiencia operativa.

**Agente de Mantenimiento Predictivo**  
Evalúa señales técnicas de las unidades, identifica patrones asociados a posibles fallas y genera recomendaciones preventivas que permiten planificar intervenciones con anticipación.

### Beneficio principal

**Transformar los datos operativos en decisiones estratégicas medibles.**

| Beneficio | Impacto estimado |
|---|---|
| Optimización de consumo de combustible | Mejora potencial por viaje |
| Anticipación de eventos mecánicos | Mayor disponibilidad de flota |
| Estandarización operativa | Reducción de variabilidad entre unidades |
| Cumplimiento ambiental | Métricas estimadas de reducción de CO₂ |

---

## 4. ¿Como describo la experiencia y solución para el cliente?

### Experiencia por rol

**Director de Operaciones**  
Accede a un dashboard consolidado con visibilidad en tiempo real del desempeño de la flota, indicadores de eficiencia y métricas ambientales, facilitando la toma de decisiones estratégicas con información confiable.

**Supervisor de Flota**  
Recibe alertas claras y priorizadas que le permiten actuar de forma inmediata ante desviaciones operativas, optimizando la gestión diaria.

**Taller Mecánico**  
Cuenta con recomendaciones anticipadas que facilitan la planeación de mantenimientos, disponibilidad de refacciones y programación eficiente de intervenciones.

**Conductor**  
Recibe retroalimentación orientada al desarrollo profesional, promoviendo mejores prácticas de conducción y reconocimiento de desempeño.

### Enfoque de la solución

> *"ADO MobilityIA complementa la experiencia operativa existente, potenciando las capacidades de cada equipo mediante información oportuna, clara y accionable."*

---

## 5. ¿Cómo pruebo y mido el éxito?

### Métricas del MVP (Hackathon)

#### Criterios técnicos

| Criterio | Métrica | Umbral |
|---|---|---|
| Pipeline de datos | Actualización continua | ≤ 10 segundos |
| Agente de combustible | Respuestas claras en español | ≤ 30 segundos |
| Agente de mantenimiento | Generación de recomendaciones | Precisión ≥ 70% |
| Knowledge Base | Información consultable | ≥ 3 documentos |
| Dashboard | Visualización en tiempo real | ≤ 10 segundos |

#### Criterios de valor

| Criterio | Evidencia |
|---|---|
| Identificación de oportunidades de ahorro | Alertas con impacto estimado |
| Anticipación de eventos | Recomendaciones preventivas |
| Calidad de interacción | Respuestas claras y accionables |
| Impacto ambiental | Métricas visibles en dashboard |

---

### Métricas en producción

#### KPIs operativos

| KPI | Objetivo en corto plazo |
|---|---|
| Consumo promedio de flota | Reducción de consumo |
| Costos de mantenimiento | Optimización significativa |
| Variabilidad operativa | Reducción sostenida |
| Disponibilidad de unidades | Incremento medible |
| Emisiones CO₂ | Reducción proporcional |

---

## Síntesis ejecutiva

> **ADO MobilityIA** representa una evolución natural hacia una operación más inteligente, eficiente y sostenible.  

> A través del uso de inteligencia artificial sobre datos existentes, la plataforma habilita una toma de decisiones más informada, mejora la eficiencia operativa y fortalece la capacidad de cumplimiento regulatorio.  

> Más que un cambio tecnológico, es una oportunidad para consolidar el liderazgo de Mobility ADO en innovación dentro del sector de transporte en México.
