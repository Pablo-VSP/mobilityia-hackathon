---
inclusion: manual
---

# 🎬 Guión de Demo — ADO MobilityIA
## Hackathon AWS Builders League 2026

> Inclusion: manual — cargar solo cuando se prepare o ensaye la demo.
> **C-003:** Nunca mencionar valores numéricos específicos de mejora en la presentación.
> **C-004:** Aclarar al jurado que los datos son simulados por seguridad corporativa.

---

## URLs de la demo

| Recurso | URL |
|---|---|
| **Dashboard** | `https://d1zr7g3ygmf5pk.cloudfront.net` |
| **Login** | `demo@adomobilityia.com` / `DemoADO2026!` |

---

## Estructura de la presentación (10 min total)

| Segmento | Duración | Contenido |
|---|---|---|
| Problema y contexto | 2 min | Por qué ADO necesita inteligencia operativa |
| Solución y arquitectura | 2 min | AgentCore + SageMaker + React |
| Demo en vivo | 4 min | Dashboard, mapa, chat con agentes |
| Impacto y cierre | 2 min | Resultados cualitativos, servicios AWS |

---

## PARTE 1 — Problema y Contexto (2 min)

### Mensaje central
> "Mobility ADO ya tiene los datos. El problema es que esos datos nunca se convirtieron en inteligencia operativa. Hasta hoy."

### Puntos clave
- El combustible es el mayor costo operativo — sin visibilidad granular, no se puede controlar
- El mantenimiento es reactivo — las unidades fallan en carretera sin anticipación
- Sin datos estructurados de emisiones, el cumplimiento regulatorio es difícil de demostrar

---

## PARTE 2 — Solución y Arquitectura (2 min)

### Mensaje central
> "ADO MobilityIA: dos agentes autónomos de IA que convierten telemetría en decisiones operativas en tiempo real, construidos sobre Amazon Bedrock AgentCore."

### Servicios AWS a mencionar
- **Amazon Bedrock AgentCore** — 2 agentes autónomos con tools y RAG
- **Amazon SageMaker** — Modelo XGBoost con 128 features (AUC-ROC 0.969)
- **Amazon Bedrock Knowledge Bases** — RAG con manuales técnicos
- **Amazon Cognito + API Gateway** — Autenticación y API segura
- **React + CloudFront** — Dashboard profesional en tiempo real
- **DynamoDB + Lambda** — Simulación de telemetría en tiempo real

---

## PARTE 3 — Demo en Vivo (4 min)

### Preparación pre-demo
- [ ] Invocar simulador 2-3 veces para tener datos frescos en DynamoDB
- [ ] Verificar que el dashboard carga correctamente
- [ ] Tener las preguntas de chat preparadas

```bash
# Inyectar datos frescos (ejecutar 2-3 veces con 10s entre cada una)
aws lambda invoke --function-name ado-simulador-telemetria --payload '{}' --region us-east-2 /tmp/sim.json
```

### Secuencia de demo

#### Paso 1 — Login y Mapa en Vivo (45 seg)
1. Abrir `https://d1zr7g3ygmf5pk.cloudfront.net`
2. Login con `demo@adomobilityia.com`
3. Mostrar el mapa con los 10 buses moviéndose en la ruta México-Acapulco
4. Señalar los colores: verde = eficiente, rojo = alerta
5. Mostrar el panel derecho con vehículos que requieren atención

> "Aquí vemos la flota en tiempo real. Cada punto es un autobús con telemetría de 27 sensores. Los colores indican el estado de consumo."

#### Paso 2 — Click en Bus con Alerta (30 seg)
1. Click en el bus rojo (7313 o el que tenga ALERTA_SIGNIFICATIVA)
2. Mostrar el popup con datos en tiempo real: velocidad, RPM, temperatura, combustible
3. Señalar las alertas activas

> "Al hacer click vemos los datos en tiempo real: velocidad, temperatura del motor, consumo de combustible. Este bus muestra un consumo elevado."

#### Paso 3 — Chat con Agente de Combustible (1 min)
1. Click en "Preguntar al Agente IA" desde el popup
2. El chat se abre pre-llenado con el bus seleccionado
3. Enviar la pregunta
4. Mostrar cómo el agente analiza y responde en español con recomendaciones

> "Le preguntamos al agente de combustible. Usa Claude 3.5 Sonnet con acceso a la telemetría en tiempo real y la Knowledge Base con manuales técnicos."

#### Paso 4 — Chat con Agente de Mantenimiento (1 min)
1. Cambiar al agente de mantenimiento (selector en el header)
2. Preguntar: "¿Qué buses tienen riesgo mecánico esta semana?"
3. El agente usa SageMaker ML para predecir y genera recomendación

> "El agente de mantenimiento usa un modelo XGBoost entrenado con datos históricos para predecir eventos mecánicos. Genera una orden de trabajo preventiva."

#### Paso 5 — Alertas y Ambiental (45 seg)
1. Navegar a la vista de Alertas → mostrar la alerta con OT generada
2. Navegar a Ambiental → mostrar el panel de CO₂ con lenguaje difuso

> "Las alertas se generan automáticamente con nivel de urgencia y componentes a revisar. El panel ambiental muestra el impacto estimado en reducción de emisiones."

---

## PARTE 4 — Impacto y Cierre (2 min)

### Resultados cualitativos (C-003 — sin valores numéricos)
- Mejora significativa en la visibilidad del consumo de combustible
- Anticipación de eventos mecánicos antes de que ocurran en ruta
- Reducción notable de la variabilidad operativa entre conductores
- Fortalecimiento del cumplimiento regulatorio ambiental (NOM-044)

### Diferenciadores técnicos
- **AgentCore** — Agentes autónomos con tools, RAG y ML integrados
- **SageMaker** — Modelo predictivo real con 128 features y AUC 0.969
- **Tiempo real** — Simulación con GPS real y 27 SPNs por bus
- **Español** — Todo el sistema responde en español latinoamericano

### Frase de cierre
> "ADO MobilityIA demuestra que la inteligencia artificial puede transformar datos de telemetría en decisiones operativas que impactan directamente la eficiencia, la seguridad y el cumplimiento ambiental de una flota de transporte."

---

## Preguntas de alto impacto para el chat

### Combustible
- "¿Qué buses tienen mayor consumo en este momento?"
- "Analiza el bus 7313, ¿qué está causando el consumo elevado?"
- "¿Cuáles son las oportunidades de mejora en eficiencia de la flota?"

### Mantenimiento
- "¿Qué buses tienen riesgo mecánico esta semana?"
- "Analiza el riesgo del bus 7331 y genera una recomendación"
- "¿Cuáles son las recomendaciones preventivas prioritarias para el taller?"

---

## Backup (si algo falla)

- Si el dashboard no carga: usar `http://localhost:3000` (dev server local)
- Si los agentes no responden: mostrar screenshots de respuestas previas
- Si DynamoDB está vacío: invocar el simulador manualmente desde la terminal
- Si SageMaker falla: el sistema usa fallback heurístico automáticamente
