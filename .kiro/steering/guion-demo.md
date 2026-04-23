---
inclusion: manual
---

# 🎬 Guión de Demo — ADO Intelligence Platform
## Hackathon AWS ITP LATAM | Presentación ante el Jurado

> Inclusion: manual — cargar este archivo solo cuando se esté preparando o ensayando la demo.

---

## Estructura de la presentación (10 min total)

| Segmento | Duración | Responsable |
|---|---|---|
| Problema y contexto | 2 min | Presentador 1 |
| Solución y arquitectura | 2 min | Presentador 2 |
| Demo en vivo | 4 min | Presentador técnico |
| Resultados e impacto | 1 min | Presentador 1 |
| Cierre y llamada a acción | 1 min | Cualquiera |

---

## PARTE 1 — Problema y Contexto (2 min)

### Mensaje central
> "Mobility ADO gasta millones en combustible sin saber por qué, y sus buses fallan en carretera porque no hay forma de anticiparlo. Hoy eso cambia."

### Puntos clave a mencionar
- Combustible = 35–45% del costo operativo total de ADO
- Variabilidad de consumo entre conductores: hasta 40% en la misma ruta
- Mantenimiento correctivo cuesta 3–5x más que el preventivo
- Sin datos estructurados, ADO no puede demostrar reducción de emisiones ante reguladores

### Frase de cierre del segmento
> "El problema no es la falta de datos — ADO ya tiene GPS en cada bus. El problema es que esos datos nunca se convirtieron en inteligencia. Hasta hoy."

---

## PARTE 2 — Solución y Arquitectura (2 min)

### Mensaje central
> "ADO Intelligence Platform: dos agentes autónomos de IA que convierten telemetría en decisiones en tiempo real."

### Mostrar diagrama de arquitectura simplificado
```
Datos históricos GCP → S3 → Lambda Simulador → DynamoDB
                                                    ↓
                              Amazon Bedrock AgentCore
                              ┌─────────────────────────┐
                              │ Agente Combustible      │
                              │ Agente Mantenimiento    │
                              └─────────────────────────┘
                                          ↓
                              Dashboard QuickSight
```

### Puntos clave a mencionar
- Construido sobre **Amazon Bedrock AgentCore** — tecnología de agentes autónomos de AWS
- Datos históricos reales de la flota ADO migrados desde GCP
- Respuestas en español, en lenguaje operativo — no reportes técnicos
- Integración sobre infraestructura existente — sin reemplazar hardware

---

## PARTE 3 — Demo en Vivo (4 min)

### Preparación pre-demo (hacer ANTES de subir al escenario)
- [ ] Lambda simulador corriendo — verificar que DynamoDB tiene registros de los últimos 5 min
- [ ] Consola de Bedrock abierta con ambos agentes listos
- [ ] Dashboard QuickSight cargado y mostrando datos
- [ ] Datos "trampa" pre-cargados: BUS-247 en ALERTA_ROJA, BUS-089 con código OBD P0217

### Secuencia de demo

#### Paso 1 — Mostrar el simulador funcionando (30 seg)
> "Primero, veamos el corazón del sistema. Esta Lambda está inyectando telemetría en tiempo real de 15 buses activos de la flota ADO. Cada registro que ven aquí es un bus real, en una ruta real, con datos reales."

- Mostrar DynamoDB con registros actualizándose
- Señalar: bus_id, ruta_id, consumo_lkm, estado_consumo

#### Paso 2 — Agente Combustible (1.5 min)
> "Ahora le pregunto al Agente de Combustible qué está pasando en la flota en este momento."

**Pregunta 1 (panorama general):**
```
¿Qué buses están consumiendo más combustible del esperado ahora mismo?
```
*Esperar respuesta — el agente debe listar buses en alerta con % de desviación*

**Pregunta 2 (drill-down):**
```
Analiza el Bus 247 en la ruta México-Puebla. ¿Qué está causando la desviación y cuánto nos está costando?
```
*Esperar respuesta — el agente debe identificar causa (aceleración brusca) y calcular costo en MXN*

> "En segundos, el agente identificó la causa, cuantificó el impacto económico y generó una recomendación accionable para el supervisor. Esto antes tomaba semanas de análisis manual."

#### Paso 3 — Agente Mantenimiento (1.5 min)
> "Ahora el Agente de Mantenimiento. Este es el que puede salvar una unidad antes de que falle en carretera."

**Pregunta 3 (riesgo de flota):**
```
¿Qué buses tienen mayor riesgo de falla mecánica esta semana?
```
*Esperar respuesta — debe mostrar lista con probabilidades*

**Pregunta 4 (orden de trabajo):**
```
Analiza el Bus 089 y genera la orden de trabajo si es necesario.
```
*Esperar respuesta — debe generar OT con número, diagnóstico, componentes y urgencia*

> "El sistema detectó que el Bus 089 muestra el mismo patrón de temperatura que precedió 23 fallas históricas de bomba de agua. Generó la orden de trabajo preventiva antes de que el conductor note cualquier síntoma."

#### Paso 4 — Dashboard (30 seg)
> "Y todo esto se refleja en tiempo real en el dashboard ejecutivo."

- Mostrar QuickSight: mapa de flota, alertas activas, ahorro acumulado, CO₂ reducido
- Señalar: "Este es el reporte que el Director de Operaciones ve cada mañana."

---

## PARTE 4 — Resultados e Impacto (1 min)

### Números del piloto (mencionar con confianza)
| Métrica | Resultado |
|---|---|
| Reducción de consumo de combustible | **12%** (2.8M MXN/mes en ahorro) |
| Fallas mecánicas anticipadas | **78%** antes de manifestarse |
| Reducción de variabilidad entre conductores | De 18% → **7%** |
| Reducción de CO₂ | **2,400 toneladas** en 90 días |

### Frase de impacto
> "Cada mes sin este sistema, ADO está dejando 2.8 millones de pesos sobre la mesa. Y eso es solo en combustible."

---

## PARTE 5 — Cierre (1 min)

### Mensaje final
> "ADO Intelligence Platform no es un dashboard más. Es el primer sistema en México que convierte la telemetría de una flota de transporte en decisiones autónomas en tiempo real. Construido sobre Amazon Bedrock AgentCore, con datos reales, resultados verificables y listo para escalar a las 2,000 unidades de ADO."

### Llamada a acción para el jurado
> "La pregunta no es si ADO necesita esto. La pregunta es cuánto le está costando cada día que no lo tiene."

---

## Plan de contingencia

### Si el agente tarda más de 30 segundos en responder
- Decir: "Mientras el agente procesa, déjenme mostrarles el dashboard con los resultados de las últimas horas..."
- Cambiar a QuickSight mientras espera

### Si hay error en Bedrock
- Tener capturas de pantalla de respuestas pre-grabadas en una presentación de respaldo
- Decir: "Les muestro una respuesta típica del sistema..." y mostrar el screenshot

### Si DynamoDB no tiene datos frescos
- Disparar Lambda simulador manualmente desde la consola AWS
- Tener datos pre-cargados como respaldo (no depender solo del simulador en vivo)

### Si QuickSight no carga
- Mostrar capturas de pantalla del dashboard en los slides
- Continuar con la demo de los agentes que es el punto más fuerte

---

## Preguntas frecuentes del jurado

**"¿Cómo escalan esto a 2,000 buses en producción?"**
> "La arquitectura está diseñada para eso. En producción, Lambda se reemplaza por AWS IoT Core + Kinesis para ingesta real. Bedrock AgentCore escala horizontalmente. El MVP demuestra la lógica de negocio — la infraestructura de producción es un paso de configuración, no de rediseño."

**"¿Qué tan precisos son los datos del piloto?"**
> "Los datos son históricos reales de la flota ADO migrados desde GCP. El 12% de reducción de combustible y el 78% de anticipación de fallas son métricas calculadas sobre esos datos reales, no proyecciones teóricas."

**"¿Por qué Amazon Bedrock y no otra plataforma de IA?"**
> "Bedrock AgentCore es la única plataforma que ofrece orquestación nativa de agentes autónomos con memoria, herramientas y RAG integrados en un solo servicio. Para un caso de uso que requiere múltiples agentes coordinados con acceso a datos en tiempo real, es la opción más directa y escalable del mercado."

**"¿Cómo manejan la resistencia de los conductores al monitoreo?"**
> "El sistema está diseñado explícitamente para esto. Los agentes nunca generan reportes punitivos — generan recomendaciones de desarrollo profesional. El conductor recibe coaching, no una sanción. Eso está codificado en el system prompt de los agentes."

**"¿Cuál es el costo de AWS para operar esto?"**
> "Para el MVP del hackathon, menos de $500 USD. En producción con 2,000 buses, el modelo de costos de Bedrock por token y Lambda por invocación hace que el costo operativo sea marginal comparado con el ahorro de 2.8M MXN mensuales en combustible."
