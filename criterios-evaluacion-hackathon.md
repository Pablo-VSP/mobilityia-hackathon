# Criterios de Evaluación — ADO Intelligence Platform
## Hackathon AWS ITP LATAM

---

## 1. ¿Quién es el cliente?

**Mobility ADO** — el operador de transporte terrestre de pasajeros más grande de México.

- Opera más de **2,000 autobuses** en **32 estados** del país
- Ofrece tres niveles de servicio: económico, ejecutivo y lujo
- Gestiona venta de boletos por taquillas físicas, web y app móvil
- Es una **infraestructura social crítica**: para millones de mexicanos, el autobús de ADO es la única opción de movilidad interurbana accesible

**El tomador de decisión** es el **Director de Operaciones** — un perfil pragmático, orientado a resultados medibles, con presión constante sobre márgenes y cumplimiento regulatorio. No compra tecnología por tendencia; compra cuando el costo de no actuar supera el costo de la solución.

**Los usuarios del sistema** son tres perfiles distintos:

| Perfil | Rol en el sistema | Motivación principal |
|---|---|---|
| Director de Operaciones | Consume dashboards ejecutivos y reportes de CO₂ | Reducción de costos y evidencia para reguladores |
| Supervisor de Flota | Recibe alertas y gestiona órdenes de trabajo | Control operativo y menos fallas en ruta |
| Conductor | Recibe retroalimentación de conducción | Desarrollo profesional, no vigilancia |
| Taller Mecánico | Ejecuta órdenes de trabajo preventivas | Diagnósticos claros con tiempo de preparación |

---

## 2. ¿Cuál es el problema u oportunidad del cliente?

> **"Gasto mucho en combustible, no sé por qué, y no puedo mejorar lo que no mido."**

### El problema central

ADO opera una flota de miles de unidades con **datos disponibles pero sin inteligencia**. Tiene GPS en cada bus, pero esa telemetría nunca se convirtió en decisiones. El resultado es una operación que sangra rentabilidad de forma invisible:

### Los 3 dolores críticos

**🔥 Opacidad en consumo de combustible**
El combustible representa entre el **35% y 45% del costo operativo total**. Sin visibilidad granular sobre qué genera el consumo — conductor, ruta, técnica de manejo — es imposible controlarlo. La variabilidad entre conductores en la misma ruta llega al **40%**, lo que a escala de flota representa millones de pesos mensuales en pérdidas no visibles.

**🔧 Mantenimiento reactivo que destruye rentabilidad**
Las unidades fallan en carretera porque no existe un sistema que anticipe las señales de deterioro. Un mantenimiento correctivo cuesta entre **3 y 5 veces más** que uno preventivo, y cada unidad fuera de servicio genera pérdida de ingresos, penalizaciones y daño reputacional. El presupuesto de mantenimiento es un agujero negro: impredecible e incontrolable.

**📊 Sin evidencia para reguladores ni directivos**
México avanza en compromisos climáticos bajo el Acuerdo de París. ADO necesita datos verificables de reducción de emisiones CO₂ para cumplir auditorías ambientales (NOM-044-SEMARNAT), acceder a incentivos fiscales al IEPS sobre combustibles y responder a la presión de stakeholders. Sin datos estructurados, no puede demostrar avances ni cumplimiento.

### La oportunidad

No existe en el mercado mexicano de transporte de pasajeros un caso documentado de **agentes de IA autónomos para optimización de flota en tiempo real**. ADO tiene la infraestructura de datos (GPS, telemetría, historial de fallas en GCP) pero no la inteligencia para explotarla. Quien llegue primero a este modelo define el nuevo estándar operativo del sector.

---

## 3. ¿Cuál es la solución y el principal beneficio para el cliente?

### La solución: ADO Intelligence Platform

Un sistema autónomo de optimización de flotas construido sobre **Amazon Bedrock AgentCore**, con dos agentes de IA que operan en tiempo real sobre datos telemétricos reales de la flota ADO.

#### Arquitectura en una línea
```
Datos históricos GCP → S3 (Data Lake) → Lambda Simulador → DynamoDB
                                                               ↓
                                         Amazon Bedrock AgentCore
                                    ┌──────────────────────────────┐
                                    │  Agente Combustible          │
                                    │  Agente Mantenimiento        │
                                    └──────────────────────────────┘
                                                   ↓
                                    Dashboard QuickSight (Jurado)
```

#### Los 2 agentes autónomos

**🔥 Agente de Inteligencia de Combustible**
Monitorea en tiempo real el consumo de cada unidad, detecta desviaciones respecto al umbral histórico de su ruta, identifica la causa probable (aceleración brusca, RPM fuera de rango, velocidad excesiva) y genera alertas accionables en español para el supervisor. No presenta datos crudos — presenta narrativas operativas con impacto económico cuantificado en MXN.

**🔧 Agente de Mantenimiento Predictivo**
Analiza señales OBD de cada unidad (temperatura de motor, presión de aceite, códigos de diagnóstico), las compara contra patrones históricos de fallas de la flota usando RAG sobre la Knowledge Base, invoca un modelo ML en SageMaker para calcular la probabilidad de falla en los próximos 14 días, y genera órdenes de trabajo preventivas con diagnóstico técnico comprensible para el taller — antes de que el conductor note cualquier síntoma.

### El principal beneficio

**Convertir la incertidumbre operativa en ventaja competitiva medible.**

| Beneficio | Impacto cuantificado |
|---|---|
| Reducción de consumo de combustible | 8–15% → hasta **$2.8M MXN/mes** en ahorro directo |
| Anticipación de fallas mecánicas | 75–85% de fallas anticipadas → reducción 3–5x en costo de mantenimiento |
| Estandarización de conducción | Variabilidad entre conductores: de 18% → 7% |
| Evidencia regulatoria | **2,400 toneladas de CO₂** reducidas documentadas y auditables en 90 días |

---

## 4. ¿Cómo describo la experiencia y solución para el cliente?

### La experiencia desde cada rol

#### Para el Director de Operaciones
Cada mañana abre un dashboard en QuickSight que le muestra el estado de su flota en tiempo real: qué buses están consumiendo por encima del umbral, cuánto dinero se está perdiendo por ineficiencia, qué unidades tienen riesgo de falla esta semana y cuántas toneladas de CO₂ se han reducido en el mes. Por primera vez, puede presentar datos irrefutables ante su directivo, su área financiera y los reguladores ambientales — sin esperar reportes de fin de mes.

#### Para el Supervisor de Flota
Recibe una alerta en tiempo real: *"El Bus 247 consume 18% más de lo esperado en la ruta México-Puebla. Causa probable: aceleración brusca en los primeros 40 km. Ahorro potencial si se corrige: $3,200 MXN en este viaje."* Tiene la información exacta para actuar — no un reporte denso que interpretar.

#### Para el Taller Mecánico
Recibe una orden de trabajo generada automáticamente: *"OT-2026-0422-089 — Bus 089. Diagnóstico: patrón de temperatura que precedió falla de bomba de agua en 23 casos históricos. Probabilidad de falla en 11 días: 87%. Componentes a revisar: bomba de agua, termostato, mangueras de refrigeración. Urgencia: Esta semana."* El taller tiene tiempo de prepararse, pedir refacciones y programar la intervención en una ventana de baja demanda.

#### Para el Conductor
Recibe retroalimentación personalizada enmarcada como coaching profesional: *"Tu técnica de desaceleración anticipada en los últimos 200 metros antes de cada parada está entre las mejores del corredor Veracruz-CDMX. Esto te coloca en el top 10% de eficiencia de la flota."* El sistema no lo vigila — lo desarrolla.

### La narrativa correcta para ADO

> *"ADO Intelligence Platform no reemplaza la experiencia de tus equipos — la amplifica. Le da a tu supervisor información que antes no tenía. Le da a tu taller tiempo para prepararse. Le da a tu director evidencia para tomar decisiones. Y le da a tu conductor reconocimiento por hacer bien su trabajo."*

---

## 5. ¿Cómo pruebo y mido el éxito?

### Métricas de éxito del MVP (Hackathon — 5 días)

#### Criterios técnicos — el sistema funciona si:

| Criterio | Métrica | Umbral de éxito |
|---|---|---|
| Pipeline de datos operativo | Lambda simulador escribe en DynamoDB | Registros actualizados cada ≤10 segundos |
| Agente Combustible funcional | Responde en español con datos reales | Latencia de respuesta ≤ 30 segundos |
| Agente Mantenimiento funcional | Genera OT con probabilidad de falla | Precisión del modelo ML ≥ 70% en datos de prueba |
| Knowledge Base activa | RAG devuelve contexto relevante | Al menos 3 documentos indexados y consultables |
| Dashboard visible | QuickSight muestra datos en tiempo real | Carga en ≤ 5 segundos con datos frescos |

#### Criterios de negocio — el valor es demostrable si:

| Criterio | Cómo se mide | Evidencia para el jurado |
|---|---|---|
| Reducción de combustible | % desviación detectada vs. umbral histórico por ruta | El agente identifica buses en alerta y cuantifica el ahorro en MXN |
| Anticipación de fallas | Probabilidad de falla calculada por SageMaker | El agente genera OT con diagnóstico antes de que la falla ocurra |
| Calidad de respuesta | Respuestas en español, accionables, sin alucinaciones | Preguntas de demo respondidas correctamente en vivo |
| Impacto ambiental | CO₂ reducido calculado a partir del ahorro de combustible | Número visible en el dashboard ejecutivo |

### Métricas de éxito en producción (post-hackathon)

#### KPIs operativos (medibles desde el Día 1 de producción)

| KPI | Línea base actual | Objetivo 90 días | Cómo se mide |
|---|---|---|---|
| Consumo promedio flota (L/km) | Dato histórico GCP | Reducción 8–15% | Comparación mensual vs. baseline |
| Costo de mantenimiento correctivo (MXN/mes) | Dato histórico GCP | Reducción 40–60% | Registro de órdenes de trabajo correctivas vs. preventivas |
| Variabilidad de consumo entre conductores | ~40% de dispersión | < 10% de dispersión | Desviación estándar del consumo por ruta |
| Fallas en ruta (unidades fuera de servicio) | Dato histórico GCP | Reducción 70% | Incidentes reportados por terminal |
| Emisiones CO₂ (ton/mes) | Calculado desde consumo histórico | Reducción proporcional al ahorro de combustible | Reporte mensual auditable para SEMARNAT |

#### ROI esperado

```
Inversión estimada (AWS + implementación):     ~$150,000 MXN/mes
Ahorro en combustible (12% de flota 2,000 u):  ~$2,800,000 MXN/mes
Ahorro en mantenimiento correctivo evitado:    ~$800,000 MXN/mes
─────────────────────────────────────────────────────────────────
ROI mensual neto:                              ~$3,450,000 MXN/mes
Período de recuperación de inversión:          < 4 semanas
```

#### Indicadores de adopción (éxito cultural)

| Indicador | Objetivo 6 meses |
|---|---|
| % supervisores que usan el dashboard diariamente | ≥ 80% |
| % conductores que reciben y leen su retroalimentación | ≥ 70% |
| % órdenes de trabajo generadas por el sistema vs. manuales | ≥ 60% |
| NPS interno del sistema (encuesta a usuarios) | ≥ 7/10 |

---

## Síntesis ejecutiva para el jurado

> **ADO Intelligence Platform** transforma la mayor flota de autobuses de México en una operación inteligente y autónoma. Usando **Amazon Bedrock AgentCore** sobre datos reales de la flota, dos agentes de IA convierten telemetría en decisiones: uno que hace visible el costo invisible del combustible, y otro que anticipa fallas mecánicas antes de que destruyan rentabilidad. El resultado es medible desde la primera semana: menos combustible quemado, menos unidades fallando en carretera, y por primera vez, evidencia verificable de reducción de emisiones CO₂ para cumplir con los reguladores. **El costo de no actuar es $3.6 millones de pesos cada mes.**
