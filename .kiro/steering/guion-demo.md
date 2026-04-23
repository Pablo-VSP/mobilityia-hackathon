---
inclusion: manual
---

# 🎬 Guión de Demo — ADO MobilityIA
## Hackathon AWS Builders League 2026

> Inclusion: manual — cargar solo cuando se prepare o ensaye la demo.
> **C-003:** Nunca mencionar valores numéricos específicos de mejora en la presentación.
> **C-004:** Aclarar al jurado que los datos son simulados por seguridad corporativa.

---

## Estructura de la presentación (10 min total)

| Segmento | Duración | Responsable |
|---|---|---|
| Problema y contexto | 2 min | Presentador 1 |
| Solución y arquitectura | 2 min | Presentador 2 |
| Demo en vivo | 4 min | Presentador técnico |
| Impacto estimado y cierre | 2 min | Presentador 1 |

---

## PARTE 1 — Problema y Contexto (2 min)

### Mensaje central
> "Mobility ADO ya tiene los datos. El problema es que esos datos nunca se convirtieron en inteligencia operativa. Hasta hoy."

### Puntos clave
- El combustible es el mayor costo operativo de ADO — sin visibilidad granular, no se puede controlar
- El mantenimiento es reactivo — las unidades fallan en carretera porque no hay forma de anticiparlo
- Sin datos estructurados de emisiones, el cumplimiento regulatorio ambiental es difícil de demostrar
- ADO ya tiene GPS en cada bus — la oportunidad es convertir esa telemetría en decisiones

### Frase de cierre del segmento
> "El problema no es la falta de datos. Es la falta de inteligencia para convertirlos en acción."

---

## PARTE 2 — Solución y Arquitectura (2 min)

### Mensaje central
> "ADO MobilityIA: dos agentes autónomos de IA que convierten telemetría en decisiones operativas en tiempo real, construidos sobre Amazon Bedrock AgentCore."

### Mostrar diagrama de arquitectura
```
Datos simulados → S3 → Lambda Simulador → DynamoDB
                                              ↓
                          Amazon Bedrock AgentCore
                     ┌──────────────────────────────┐
                     │  Agente Combustible           │
                     │  Agente Mantenimiento         │
                     └──────────────────────────────┘
                                   ↓
                       Dashboard QuickSight
```

### Puntos clave
- Construido sobre **Amazon Bedrock AgentCore** — orquestación nativa de agentes autónomos
- Datos simulados que replican fielmente la operación real de ADO (seguridad corporativa)
- Respuestas en español, en lenguaje operativo — no reportes técnicos
- Integración sobre infraestructura existente — sin reemplazar hardware

---

## PARTE 3 — Demo en Vivo (4 min)

### Preparación pre-demo (hacer ANTES de subir al escenario)
- [ ] Lambda simulador corriendo — DynamoDB con registros de los últimos 5 min
- [ ] Consola de Bedrock abierta con ambos agentes listos
- [ ] Dashboard QuickSight cargado con datos simulados
- [ ] Datos "trampa" pre-cargados: BUS-SIM-247 en ALERTA_SIGNIFICATIVA, BUS-SIM-089 con código OBD P0217

### Secuencia de demo

#### Paso 1 — Mostrar el simulador funcionando (30 seg)
> "Primero, el corazón del sistema. Esta Lambda está inyectando telemetría simulada de 15 buses en tiempo real. Cada registro representa un bus en una ruta, con datos que replican fielmente la variabilidad de una flota real."

- Mostrar DynamoDB con registros actualizándose
- Señalar: bus_id, ruta_id, consumo_lkm, estado_consumo

#### Paso 2 — Agente Combustible (1.5 min)
> "Le pregunto al Agente de Combustible qué está pasando en la flota ahora mismo."

**Pregunta 1:**
```
¿Qué buses están mostrando mayor consumo del esperado en este momento?
```
*El agente lista buses con desviaciones usando lenguaje difuso — sin porcentajes*

**Pregunta 2:**
```
Analiza el Bus SIM-247 en la ruta México-Puebla. ¿Qué está causando la desviación?
```
*El agente identifica causa y genera recomendación accionable sin valores numéricos*

> "En segundos, el agente identificó la causa, describió el impacto operativo y generó una recomendación para el supervisor. Sin reportes manuales, sin esperar fin de mes."

#### Paso 3 — Agente Mantenimiento (1.5 min)
> "Ahora el Agente de Mantenimiento — el que puede evitar que una unidad falle en carretera."

**Pregunta 3:**
```
¿Qué buses tienen mayor riesgo de evento mecánico esta semana?
```
*El agente lista buses con nivel de riesgo cualitativo*

**Pregunta 4:**
```
Analiza el Bus SIM-089 y genera una recomendación si es necesario.
```
*El agente genera recomendación preventiva con diagnóstico y urgencia*

> "El sistema detectó señales consistentes con patrones previos a eventos de refrigeración. Generó la recomendación preventiva antes de que el conductor note cualquier síntoma."

#### Paso 4 — Dashboard (30 seg)
> "Todo esto se refleja en tiempo real en el dashboard ejecutivo."

- Mostrar QuickSight: estado de flota, alertas activas, métricas de eficiencia, CO₂ estimado
- "Este es el panel que el Director de Operaciones consulta cada mañana."

---

## PARTE 4 — Impacto Estimado y Cierre (2 min)

### Impacto (lenguaje difuso — C-003)

| Área | Impacto estimado |
|---|---|
| Consumo de combustible | Mejora potencial por viaje identificada y accionable |
| Disponibilidad de flota | Mayor disponibilidad por anticipación de eventos |
| Variabilidad operativa | Reducción sostenida entre unidades y conductores |
| Cumplimiento ambiental | Métricas de reducción de CO₂ visibles y auditables |

### Frase de cierre
> "ADO MobilityIA no reemplaza la experiencia de los equipos de ADO — la amplifica. Le da al supervisor información que antes no tenía. Le da al taller tiempo para prepararse. Le da al director evidencia para tomar decisiones. Y todo esto, sobre datos que ADO ya genera hoy."

### Llamada a acción
> "La pregunta no es si ADO necesita esto. La pregunta es cuánto valor operativo se está dejando sobre la mesa cada día sin convertir esos datos en inteligencia."

---

## Plan de contingencia

| Problema | Acción |
|---|---|
| Agente tarda más de 30 segundos | Cambiar a QuickSight mientras espera |
| Error en Bedrock | Mostrar capturas pre-grabadas de respuestas |
| DynamoDB sin datos frescos | Disparar Lambda simulador manualmente |
| QuickSight no carga | Mostrar capturas del dashboard en slides |

---

## Preguntas frecuentes del jurado

**"¿Por qué datos simulados y no datos reales de ADO?"**
> "Por seguridad de la información corporativa. Los datos operativos de una flota de esta escala son activos estratégicos sensibles. Los datos simulados replican fielmente la estructura y variabilidad de la operación real, permitiendo demostrar el valor del sistema sin comprometer información confidencial."

**"¿Cómo escalan esto a producción?"**
> "En producción, Lambda se reemplaza por AWS IoT Core + Kinesis para ingesta real desde los GPS de los buses. Bedrock AgentCore escala horizontalmente. El MVP demuestra la lógica de negocio — la infraestructura de producción es un paso de configuración, no de rediseño."

**"¿Por qué Amazon Bedrock y no otra plataforma?"**
> "Bedrock AgentCore es la única plataforma que ofrece orquestación nativa de agentes autónomos con memoria, herramientas y RAG integrados en un solo servicio managed. Para un caso de uso que requiere múltiples agentes coordinados con acceso a datos en tiempo real, es la opción más directa y escalable."

**"¿Cómo manejan la resistencia de los conductores al monitoreo?"**
> "El sistema está diseñado explícitamente para esto. Los agentes generan recomendaciones de desarrollo profesional, no reportes punitivos. Eso está codificado en el system prompt — el conductor recibe coaching, no una sanción."

**"¿Cuánto cuesta operar esto en AWS?"**
> "Para el MVP del hackathon, el costo es marginal. En producción, el modelo de costos de Bedrock por token y Lambda por invocación hace que la inversión tecnológica sea significativamente menor que el valor operativo generado por la optimización de combustible y la reducción de mantenimiento correctivo."
