---
inclusion: always
---

# 📅 Plan de Ejecución — ADO MobilityIA
## Hackathon AWS Builders League 2026 — DÍA FINAL

> **Contexto:** Estamos en el último día de desarrollo. Las Lambdas están 100% codificadas.
> Falta desplegar infraestructura AWS, conectar agentes de AgentCore y preparar la demo.
> Los datos son **simulados** (C-004). Sin métricas numéricas específicas (C-003).
> Los agentes son de **AgentCore** (C-005). Esquemas alineados con `models/` (C-006).

---

## Estado actual del proyecto

### ✅ Completado
- 9 funciones Lambda codificadas y listas para deploy
- Shared layer `ado-common` con catálogo SPN, pivoteo, utilidades
- Catálogo de 36 SPNs confirmados con rangos y umbrales
- Catálogo de fallas con `severidad_inferencia` clasificada (C-007)
- Documentación completa: steering files, prompts de agentes, esquemas de datos
- Plan de modelo predictivo SageMaker con fallback heurístico

### ❌ Pendiente de desplegar
- Infraestructura AWS (S3, DynamoDB, Lambda, IAM)
- Datos simulados en S3
- Agentes de AgentCore con tools conectados
- Knowledge Base en Bedrock
- SageMaker endpoint (o confirmar fallback heurístico)
- Dashboard (QuickSight o Streamlit)

---

## Plan del día — Bloques de trabajo

### BLOQUE 1 — Infraestructura base (2-3 horas)
> **Objetivo:** S3 + DynamoDB + Lambda simulador funcionando.

#### 1.1 Infraestructura con CDK/CloudFormation + CLI
- [ ] Crear bucket S3: `ado-mobilityia-mvp` con estructura de carpetas
- [ ] Crear tabla DynamoDB `ado-telemetria-live`
  - PK: `autobus` (S) | SK: `timestamp` (S)
  - TTL: `ttl_expiry`
  - GSI: `viaje_ruta-timestamp-index`
- [ ] Crear tabla DynamoDB `ado-alertas`
  - PK: `alerta_id` (S) | SK: `timestamp` (S)
- [ ] Crear roles IAM (Lambda execution, Bedrock access, SageMaker)

#### 1.2 Datos simulados en S3
- [ ] Subir catálogo SPN (`motor_spn.json`) a `catalogo/`
- [ ] Generar y subir telemetría simulada (Parquet) a `telemetria-simulada/`
- [ ] Subir fallas simuladas (Parquet) a `fallas-simuladas/`
- [ ] Subir documentos de Knowledge Base a `knowledge-base/docs/`

#### 1.3 Deploy de Lambdas
- [ ] Crear Lambda layer `ado-common-layer` con el shared code
- [ ] Deploy `ado-simulador-telemetria` con EventBridge Scheduler (rate 10s)
- [ ] Deploy las 7 Lambdas de tools (3 combustible + 4 mantenimiento)
- [ ] Deploy `ado-dashboard-api`
- [ ] Probar simulador: verificar escritura en DynamoDB

### BLOQUE 2 — Agentes de AgentCore (2-3 horas)
> **Objetivo:** Ambos agentes respondiendo en español con datos simulados.

#### 2.1 Knowledge Base
- [ ] Crear Knowledge Base en Bedrock
  - Data source: `s3://ado-mobilityia-mvp/knowledge-base/docs/`
  - Embeddings: Amazon Titan Text Embeddings v2
- [ ] Sincronizar y verificar indexación

#### 2.2 Agente Combustible (AgentCore — C-005)
- [ ] Crear agente `ado-agente-combustible` en AgentCore
- [ ] Configurar system prompt (ver `agentes-prompts.md`)
- [ ] Asociar Action Group con 3 Lambdas tools
- [ ] Asociar Knowledge Base
- [ ] Modelo: Claude 3.5 Sonnet
- [ ] Probar con preguntas de demo

#### 2.3 Agente Mantenimiento (AgentCore — C-005)
- [ ] Crear agente `ado-agente-mantenimiento` en AgentCore
- [ ] Configurar system prompt (ver `agentes-prompts.md`)
- [ ] Asociar Action Group con 4 Lambdas tools
- [ ] Asociar Knowledge Base
- [ ] Probar con preguntas de demo

### BLOQUE 3 — SageMaker (1-2 horas, o confirmar fallback)
> **Decisión:** Si no hay tiempo, el fallback heurístico en Lambda es suficiente para la demo.

- [ ] Opción A: Entrenar XGBoost rápido en SageMaker Studio
- [ ] Opción B: Confirmar que el fallback heurístico funciona correctamente
- [ ] Probar `tool-predecir-evento` end-to-end

### BLOQUE 4 — Dashboard + Demo (2 horas)
> **Objetivo:** Demo completa funcionando de punta a punta.

#### 4.1 Dashboard
- [ ] Opción A: QuickSight conectado a DynamoDB (via Athena)
- [ ] Opción B: Streamlit app usando `ado-dashboard-api`
- [ ] Visualizaciones: estado de flota, alertas activas, eficiencia, CO₂

#### 4.2 Datos "trampa" para la demo
- [ ] Pre-cargar buses con señales anómalas en DynamoDB:
  - Bus A: Temperatura motor elevada + presión aceite baja → CRITICO
  - Bus B: Balatas con desgaste avanzado → ELEVADO
  - Bus C: Voltaje batería bajo + nivel urea bajo → MODERADO
  - Bus D: Todas las señales normales → BAJO

#### 4.3 Ensayo de demo
- [ ] Probar flujo completo: simulador → DynamoDB → agentes → dashboard
- [ ] Preparar 3-5 preguntas de alto impacto
- [ ] Preparar backup (screenshots/video) por si hay problemas

---

## Herramientas disponibles para el deploy

Contamos con MCPs de AWS que nos permiten:
- **AWS CLI** (`call_aws`) — Crear recursos directamente desde aquí
- **AWS Documentation** — Consultar docs actualizadas de AgentCore, Bedrock, etc.
- **AWS Pricing** — Verificar costos de los servicios
- **AWS Regional Availability** — Verificar disponibilidad de servicios en us-east-1

### Estrategia de deploy recomendada
1. **CDK/CloudFormation** para infraestructura reproducible (S3, DynamoDB, IAM, Lambda)
2. **AWS CLI** para configuraciones rápidas y verificaciones
3. **Consola AWS** para Bedrock AgentCore (configuración visual de agentes)

---

## Criterio de éxito del día

> Demo completa de principio a fin:
> 1. Lambda simulador inyectando datos en DynamoDB ✓
> 2. Agente Combustible respondiendo en español con lenguaje difuso ✓
> 3. Agente Mantenimiento generando recomendaciones preventivas ✓
> 4. Dashboard mostrando estado de flota y alertas ✓
> 5. Todo funcionando sin errores en menos de 5 minutos ✓

---

## Riesgos y mitigaciones (día final)

| Riesgo | Mitigación |
|---|---|
| AgentCore no disponible en us-east-1 | Verificar disponibilidad regional primero |
| SageMaker tarda en entrenar | Usar fallback heurístico (ya implementado) |
| Permisos IAM bloqueados | Solicitar permisos inmediatamente |
| QuickSight complejo de configurar | Usar Streamlit como alternativa rápida |
| Agente usa valores numéricos (viola C-003) | System prompt tiene instrucción explícita |
