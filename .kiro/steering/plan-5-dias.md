---
inclusion: always
---

# 📅 Plan de 5 Días — Hackathon ADO Intelligence Platform

> Basado en C-001 (MVP acotado) y C-002 (datos GCP + Lambda simulador).
> Cada día tiene entregables concretos y demostrables. Si una tarea se bloquea, escalar inmediatamente al equipo.

---

## Resumen del plan

| Día | Foco | Entregable clave |
|---|---|---|
| **Día 1** | Infraestructura base + migración de datos | S3 poblado, DynamoDB creado, Lambda simulador funcionando |
| **Día 2** | Knowledge Base + Agente Combustible | Agente 1 respondiendo en español con datos reales |
| **Día 3** | Modelo predictivo + Agente Mantenimiento | Agente 2 generando órdenes de trabajo |
| **Día 4** | Dashboard + integración end-to-end | Demo completa funcionando de punta a punta |
| **Día 5** | Pulido, ensayo y presentación | Demo estable, pitch listo, backup preparado |

---

## DÍA 1 — Infraestructura Base y Datos

### Objetivo
Tener el pipeline de datos funcionando: GCP → S3 → Lambda → DynamoDB.

### Tareas

#### 1.1 Setup de cuenta AWS
- [ ] Confirmar permisos IAM habilitados por admins de Mobility ADO
- [ ] Crear roles IAM necesarios (Lambda execution role, Bedrock access role)
- [ ] Verificar acceso a Amazon Bedrock y modelos Claude en `us-east-1`

#### 1.2 Migración GCP → S3
- [ ] Exportar datos históricos de telemetría desde BigQuery/GCS a CSV o Parquet
- [ ] Crear bucket S3: `s3://ado-intelligence-mvp/`
- [ ] Subir datos con estructura:
  ```
  s3://ado-intelligence-mvp/
  ├── telemetria-historica/YYYY-MM/bus_id/
  ├── fallas-historicas/
  └── knowledge-base/docs/
  ```
- [ ] Validar que los datos tienen los campos requeridos (ver esquema en `data-schema.md`)

#### 1.3 DynamoDB
- [ ] Crear tabla `ado-telemetria-live`
  - PK: `bus_id` (String)
  - SK: `timestamp` (String ISO 8601)
  - Atributos: velocidad, rpm, consumo_combustible, temperatura_motor, pct_acelerador, pct_freno, codigo_obd, ruta_id, conductor_id
- [ ] Crear tabla `ado-alertas`
  - PK: `alerta_id` (String UUID)
  - Atributos: bus_id, tipo_alerta, descripcion, timestamp, estado

#### 1.4 Lambda Simulador
- [ ] Crear función Lambda `ado-simulador-telemetria`
- [ ] Lógica: lee registros históricos de S3 secuencialmente por bus_id, escribe en DynamoDB con timestamp = now()
- [ ] Configurar para simular 10–20 buses en paralelo (suficiente para la demo)
- [ ] Probar disparo manual y verificar escritura en DynamoDB
- [ ] (Opcional) Configurar EventBridge Scheduler para disparo automático cada 10 segundos

### Criterio de éxito del Día 1
> DynamoDB muestra registros actualizándose en tiempo real al ejecutar el simulador Lambda.

---

## DÍA 2 — Knowledge Base + Agente Combustible

### Objetivo
Tener el Agente 1 (Combustible) funcionando: recibe bus_id, consulta DynamoDB, detecta desviación, responde en español.

### Tareas

#### 2.1 Knowledge Base en Bedrock
- [ ] Subir documentos a `s3://ado-intelligence-mvp/knowledge-base/docs/`:
  - Umbrales de consumo por ruta (CSV o PDF)
  - Normas básicas de conducción eficiente
  - Glosario de códigos OBD relevantes
- [ ] Crear Knowledge Base en Amazon Bedrock
  - Data source: S3 bucket
  - Embeddings: Amazon Titan Text Embeddings v2
- [ ] Sincronizar y verificar que los documentos están indexados

#### 2.2 Tools del Agente Combustible (Lambda functions)
- [ ] `tool-consultar-telemetria`: recibe bus_id, devuelve últimos N registros de DynamoDB
- [ ] `tool-calcular-desviacion`: recibe bus_id + ruta_id, calcula % desviación vs. umbral histórico de S3
- [ ] `tool-listar-buses-activos`: devuelve lista de buses con telemetría en los últimos 5 minutos

#### 2.3 Agente Combustible en Bedrock AgentCore
- [ ] Crear agente `ado-agente-combustible`
- [ ] System prompt en español (ver plantilla en `agentes-prompts.md`)
- [ ] Asociar Knowledge Base
- [ ] Asociar Action Group con las 3 tools Lambda
- [ ] Configurar modelo: Claude 3.5 Sonnet (o Claude 3 Haiku si hay límite de costos)
- [ ] Probar con preguntas de ejemplo:
  - "¿Qué buses están consumiendo más combustible del esperado ahora mismo?"
  - "Analiza el desempeño del Bus 247 en la ruta México-Puebla"
  - "Genera un reporte de eficiencia de los últimos 30 minutos"

### Criterio de éxito del Día 2
> El Agente Combustible responde en español con datos reales de DynamoDB, identifica desviaciones y genera recomendaciones accionables.

---

## DÍA 3 — Modelo Predictivo + Agente Mantenimiento

### Objetivo
Tener el Agente 2 (Mantenimiento) funcionando: analiza señales OBD, predice fallas, genera órdenes de trabajo.

### Tareas

#### 3.1 Modelo predictivo en SageMaker
- [ ] Opción A (recomendada para 5 días): Entrenar modelo de clasificación simple (Random Forest o XGBoost) con datos históricos de fallas de GCP
  - Features: temperatura_motor, presión_aceite, codigo_obd, km_desde_ultimo_mantenimiento, rpm_promedio
  - Target: falla_en_proximos_14_dias (binario)
- [ ] Opción B (fallback): Reglas heurísticas en Lambda si SageMaker no está disponible a tiempo
- [ ] Desplegar como SageMaker endpoint: `ado-prediccion-fallas`
- [ ] Probar endpoint con datos de ejemplo

#### 3.2 Tools del Agente Mantenimiento (Lambda functions)
- [ ] `tool-consultar-obd`: recibe bus_id, devuelve señales OBD actuales de DynamoDB
- [ ] `tool-predecir-falla`: llama al endpoint SageMaker, devuelve probabilidad y días estimados
- [ ] `tool-buscar-historial-fallas`: consulta S3 con fallas históricas similares (mismo código OBD + rango de temperatura)
- [ ] `tool-generar-orden-trabajo`: crea registro en DynamoDB tabla `ado-alertas` con la orden de trabajo

#### 3.3 Agente Mantenimiento en Bedrock AgentCore
- [ ] Crear agente `ado-agente-mantenimiento`
- [ ] System prompt en español (ver plantilla en `agentes-prompts.md`)
- [ ] Asociar Knowledge Base (misma que Agente Combustible)
- [ ] Asociar Action Group con las 4 tools Lambda
- [ ] Probar con preguntas de ejemplo:
  - "¿Qué buses requieren mantenimiento preventivo esta semana?"
  - "Analiza el estado mecánico del Bus 089"
  - "Genera las órdenes de trabajo prioritarias para el taller de Querétaro"

### Criterio de éxito del Día 3
> El Agente Mantenimiento identifica buses en riesgo, muestra probabilidad de falla y genera una orden de trabajo con diagnóstico en lenguaje natural.

---

## DÍA 4 — Dashboard + Integración End-to-End

### Objetivo
Demo completa funcionando: simulador → agentes → dashboard visible para el jurado.

### Tareas

#### 4.1 Dashboard en QuickSight (o alternativa)
- [ ] Conectar QuickSight a DynamoDB (via Athena + S3 si es necesario)
- [ ] Crear visualizaciones:
  - Mapa o tabla de flota activa con estado de consumo (verde/amarillo/rojo)
  - Top 10 buses con mayor desviación de combustible
  - Lista de alertas de mantenimiento activas con probabilidad
  - Ahorro proyectado en combustible (MXN)
  - Reducción de CO₂ acumulada (toneladas)
- [ ] Alternativa si QuickSight es complejo: Streamlit app en EC2 o Lambda + API Gateway

#### 4.2 Integración end-to-end
- [ ] Flujo completo: Lambda simulador → DynamoDB → Agente responde → Alerta en dashboard
- [ ] Probar escenario de demo completo (ver `guion-demo.md`)
- [ ] Identificar y corregir puntos de falla

#### 4.3 Script de demo
- [ ] Preparar 3–5 preguntas de alto impacto para hacer a los agentes en vivo
- [ ] Preparar datos "trampa" en el simulador para garantizar que aparezcan alertas durante la demo
- [ ] Documentar comandos exactos para ejecutar durante la presentación

### Criterio de éxito del Día 4
> Se puede ejecutar la demo completa de principio a fin sin errores en menos de 5 minutos.

---

## DÍA 5 — Pulido, Ensayo y Presentación

### Objetivo
Demo estable, pitch afinado, equipo coordinado.

### Tareas

#### 5.1 Estabilización
- [ ] Corregir bugs encontrados en el Día 4
- [ ] Preparar datos de demo pre-cargados en DynamoDB (no depender solo del simulador en vivo)
- [ ] Tener un "modo offline" de respaldo si hay problemas de conectividad

#### 5.2 Presentación
- [ ] Preparar slides con: problema, solución, arquitectura simplificada, resultados del piloto, demo en vivo
- [ ] Ensayar pitch completo (máximo 10 minutos + demo)
- [ ] Preparar respuestas a preguntas frecuentes del jurado (ver `faq-jurado.md`)

#### 5.3 Checklist pre-presentación
- [ ] Cuenta AWS activa y con créditos suficientes
- [ ] Todos los servicios desplegados y funcionando
- [ ] Lambda simulador probado
- [ ] Ambos agentes respondiendo correctamente
- [ ] Dashboard cargando sin errores
- [ ] Backup de screenshots/video de la demo funcionando

---

## Riesgos y mitigaciones

| Riesgo | Probabilidad | Mitigación |
|---|---|---|
| Bedrock AgentCore no disponible en la región | Media | Tener fallback con Bedrock Agents clásico |
| SageMaker endpoint tarda en entrenar | Alta | Preparar reglas heurísticas en Lambda como fallback |
| Datos GCP no tienen el formato esperado | Media | Preparar script de limpieza/transformación desde el Día 1 |
| QuickSight no conecta con DynamoDB fácilmente | Alta | Usar Streamlit como alternativa desde el Día 4 |
| Permisos IAM bloqueados por admins | Alta | Solicitar permisos el Día 0, tener lista la solicitud formal |
| Conectividad durante la demo | Baja | Tener screenshots y video de respaldo |
