---
inclusion: always
---

# 📅 Plan de 5 Días — ADO MobilityIA
## Hackathon AWS Builders League 2026 — Aplicando C-001, C-002, C-003 y C-004

> Cada día tiene entregables concretos y demostrables.
> Los datos son **simulados** (C-004). No se mencionan métricas numéricas específicas (C-003).

---

## Resumen del plan

| Día | Foco | Entregable clave |
|---|---|---|
| **Día 1** | Generación de datos simulados + infraestructura base | S3 poblado con datos simulados, DynamoDB creado, Lambda simulador funcionando |
| **Día 2** | Knowledge Base + Agente Combustible | Agente 1 respondiendo en español con datos simulados |
| **Día 3** | Modelo predictivo + Agente Mantenimiento | Agente 2 generando recomendaciones preventivas |
| **Día 4** | Dashboard + integración end-to-end | Demo completa funcionando de punta a punta |
| **Día 5** | Pulido, ensayo y presentación | Demo estable, pitch listo, backup preparado |

---

## DÍA 1 — Datos Simulados + Infraestructura Base

### Objetivo
Tener el pipeline de datos funcionando con datos simulados: Script → S3 → Lambda → DynamoDB.

### Tareas

#### 1.1 Setup de cuenta AWS
- [ ] Confirmar permisos IAM habilitados por admins de Mobility ADO
- [ ] Crear roles IAM necesarios (Lambda execution role, Bedrock access role)
- [ ] Verificar acceso a Amazon Bedrock y modelos Claude en `us-east-1`

#### 1.2 Generación de datos simulados (C-004)
- [ ] Crear script Python `generate_simulated_data.py`:
  - Genera telemetría sintética para 20 buses ficticios (BUS-SIM-001 a BUS-SIM-020)
  - Genera historial de eventos mecánicos simulados (mínimo 500 registros)
  - Incluye variabilidad realista: rutas, conductores, condiciones de carretera
  - **No usa datos reales de ADO** — datos 100% sintéticos
- [ ] Crear bucket S3: `s3://ado-mobilityia-mvp/`
- [ ] Subir datos simulados con estructura:
  ```
  s3://ado-mobilityia-mvp/
  ├── telemetria-simulada/YYYY-MM/bus_id/
  ├── fallas-simuladas/
  └── knowledge-base/docs/
  ```
- [ ] Validar que los datos tienen los campos requeridos (ver `data-schema.md`)

#### 1.3 DynamoDB
- [ ] Crear tabla `ado-telemetria-live`
  - PK: `bus_id` (String) | SK: `timestamp` (String ISO 8601)
  - TTL: `ttl_expiry` (24 horas)
  - GSI: `ruta_id-timestamp-index`
- [ ] Crear tabla `ado-alertas`
  - PK: `alerta_id` (String UUID) | SK: `timestamp`

#### 1.4 Lambda Simulador (C-002)
- [ ] Crear función Lambda `ado-simulador-telemetria`
- [ ] Lógica: lee registros simulados de S3, escribe en DynamoDB con timestamp = now()
- [ ] Simular 10–20 buses en paralelo
- [ ] Probar disparo manual y verificar escritura en DynamoDB
- [ ] Configurar EventBridge Scheduler: disparo cada 10 segundos

### Criterio de éxito del Día 1
> DynamoDB muestra registros de buses simulados actualizándose en tiempo real.

---

## DÍA 2 — Knowledge Base + Agente Combustible

### Objetivo
Agente 1 funcionando: recibe bus_id, consulta DynamoDB, detecta desviación, responde en español con lenguaje difuso (C-003).

### Tareas

#### 2.1 Knowledge Base en Bedrock
- [ ] Subir documentos a `s3://ado-mobilityia-mvp/knowledge-base/docs/`:
  - Umbrales de consumo por ruta (CSV — valores de referencia simulados)
  - Normas básicas de conducción eficiente
  - Glosario de códigos OBD relevantes
- [ ] Crear Knowledge Base en Amazon Bedrock
  - Data source: S3 bucket
  - Embeddings: Amazon Titan Text Embeddings v2
- [ ] Sincronizar y verificar indexación

#### 2.2 Tools del Agente Combustible (Lambda functions)
- [ ] `tool-consultar-telemetria` — últimos N registros de DynamoDB por bus_id
- [ ] `tool-calcular-desviacion` — % desviación vs. umbral histórico simulado
- [ ] `tool-listar-buses-activos` — buses con telemetría en los últimos 5 minutos

#### 2.3 Agente Combustible en Bedrock AgentCore
- [ ] Crear agente `ado-agente-combustible`
- [ ] System prompt en español con instrucción explícita de **no usar valores numéricos específicos** (C-003)
- [ ] Asociar Knowledge Base y Action Group
- [ ] Modelo: Claude 3.5 Sonnet
- [ ] Probar con preguntas de demo (ver `agentes-prompts.md`)

### Criterio de éxito del Día 2
> El Agente Combustible responde en español con datos simulados, identifica desviaciones y genera recomendaciones usando lenguaje difuso (sin porcentajes ni valores MXN específicos).

---

## DÍA 3 — Modelo Predictivo + Agente Mantenimiento

### Objetivo
Agente 2 funcionando: analiza señales OBD simuladas, predice eventos, genera recomendaciones preventivas.

### Tareas

#### 3.1 Modelo predictivo en SageMaker (entrenado con datos simulados — C-004)
- [ ] Opción A: Entrenar XGBoost/Random Forest con dataset simulado de fallas
  - Features: temperatura_motor, presión_aceite, codigo_obd, km_desde_ultimo_mant, rpm_promedio
  - Target: evento_en_proximos_14_dias (binario)
- [ ] Opción B (fallback): Reglas heurísticas en Lambda
- [ ] Desplegar como SageMaker endpoint: `ado-prediccion-eventos`
- [ ] Probar endpoint con datos simulados de ejemplo

#### 3.2 Tools del Agente Mantenimiento (Lambda functions)
- [ ] `tool-consultar-obd` — señales OBD actuales de DynamoDB
- [ ] `tool-predecir-evento` — llama al endpoint SageMaker
- [ ] `tool-buscar-patrones-historicos` — consulta S3 con eventos similares
- [ ] `tool-generar-recomendacion` — crea registro en `ado-alertas`

#### 3.3 Agente Mantenimiento en Bedrock AgentCore
- [ ] Crear agente `ado-agente-mantenimiento`
- [ ] System prompt con instrucción de **lenguaje difuso** (C-003): "alta probabilidad", "patrón consistente con", "se recomienda revisión"
- [ ] Asociar Knowledge Base y Action Group
- [ ] Probar con preguntas de demo (ver `agentes-prompts.md`)

### Criterio de éxito del Día 3
> El Agente Mantenimiento identifica buses simulados en riesgo y genera recomendaciones preventivas sin mencionar probabilidades numéricas específicas.

---

## DÍA 4 — Dashboard + Integración End-to-End

### Objetivo
Demo completa funcionando: simulador → agentes → dashboard visible para el jurado.

### Tareas

#### 4.1 Dashboard en QuickSight
- [ ] Conectar QuickSight a DynamoDB (via Athena + S3)
- [ ] Crear visualizaciones:
  - Estado de flota simulada (verde/amarillo/rojo)
  - Buses con mayor desviación de consumo
  - Recomendaciones de mantenimiento activas
  - Estimación de mejora en eficiencia (lenguaje difuso — C-003)
  - Métricas estimadas de reducción de CO₂
- [ ] Alternativa: Streamlit app si QuickSight es complejo

#### 4.2 Integración end-to-end
- [ ] Flujo completo: Lambda simulador → DynamoDB → Agente responde → Dashboard
- [ ] Probar escenario de demo completo (ver `guion-demo.md`)
- [ ] Corregir puntos de falla

#### 4.3 Script de demo
- [ ] Preparar 3–5 preguntas de alto impacto para los agentes
- [ ] Pre-cargar datos simulados "trampa" para garantizar alertas durante la demo
- [ ] Documentar comandos exactos para la presentación

### Criterio de éxito del Día 4
> Demo completa de principio a fin sin errores en menos de 5 minutos.

---

## DÍA 5 — Pulido, Ensayo y Presentación

### Objetivo
Demo estable, pitch afinado, equipo coordinado.

### Tareas

#### 5.1 Estabilización
- [ ] Corregir bugs del Día 4
- [ ] Pre-cargar datos simulados en DynamoDB como respaldo
- [ ] Preparar modo offline (screenshots/video) por si hay problemas de conectividad

#### 5.2 Presentación
- [ ] Slides: problema → solución → arquitectura → demo en vivo → impacto estimado
- [ ] Ensayar pitch completo (máximo 10 minutos + demo)
- [ ] Preparar respuestas a preguntas del jurado (ver `guion-demo.md`)

#### 5.3 Checklist pre-presentación
- [ ] Cuenta AWS activa con créditos suficientes
- [ ] Todos los servicios desplegados y funcionando
- [ ] Lambda simulador probado con datos simulados
- [ ] Ambos agentes respondiendo con lenguaje difuso (C-003)
- [ ] Dashboard cargando sin errores
- [ ] Backup de screenshots/video listo

---

## Riesgos y mitigaciones

| Riesgo | Probabilidad | Mitigación |
|---|---|---|
| Bedrock AgentCore no disponible en la región | Media | Fallback con Bedrock Agents clásico |
| SageMaker endpoint tarda en entrenar | Alta | Reglas heurísticas en Lambda como fallback |
| Datos simulados no tienen variabilidad suficiente | Media | Ajustar parámetros del script generador |
| QuickSight no conecta con DynamoDB fácilmente | Alta | Usar Streamlit como alternativa |
| Permisos IAM bloqueados por admins | Alta | Solicitar permisos el Día 0 |
| Agente usa valores numéricos específicos (viola C-003) | Media | Revisar system prompt y agregar instrucción explícita |
| Conectividad durante la demo | Baja | Screenshots y video de respaldo |
