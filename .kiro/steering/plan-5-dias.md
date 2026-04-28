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
- 9 funciones Lambda codificadas, desplegadas y activas en us-east-2
  - Bucket de Lambdas: `mobilityia-hackathon-bl-2026`
  - Bucket de datos raw: `ado-telemetry-mvp`
- Shared layer `ado-common-layer` (v2) desplegado
- DynamoDB tablas creadas: `ado-telemetria-live`, `ado-alertas`
- Knowledge Base creada: `ado-mobilityia-kb` (ID: `4OAVLRB8VI`) con 5 documentos indexados
- Modelo XGBoost entrenado y endpoint desplegado: `ado-prediccion-eventos` (InService, 128 features)
- 2 Agentes Bedrock creados y en estado PREPARED:
  - `ado-agente-combustible` (ID: `5N3U0PMGXX`) — modelo: Nova Micro, 3 action groups
  - `ado-agente-mantenimiento` (ID: `KLLFLAH0SJ`) — modelo: Nova Pro, 4 action groups
- Catálogo de 36 SPNs confirmados con rangos y umbrales
- Catálogo de fallas con `severidad_inferencia` clasificada (C-007)
- 3 manuales completos subidos a S3 Knowledge Base
- Documentación completa: steering files, prompts de agentes, esquemas de datos

### ⚠️ Pendiente — Acciones inmediatas
- **Knowledge Base NO asociada a los agentes** — Ambos agentes tienen 0 Knowledge Bases asociadas
- **Verificar que el simulador apunte a datos de enero 2021** (C-008)
- **Probar flujo end-to-end**: simulador → DynamoDB → agentes → respuesta
- **Dashboard** (QuickSight o Streamlit)

### 📋 IDs de recursos AWS (us-east-2, cuenta 084032333314)

| Recurso | ID / Nombre |
|---|---|
| Agente Combustible | `5N3U0PMGXX` (`ado-agente-combustible`) |
| Agente Mantenimiento | `KLLFLAH0SJ` (`ado-agente-mantenimiento`) |
| Knowledge Base | `4OAVLRB8VI` (`ado-mobilityia-kb`) |
| Data Source KB | `LL4E15XKR4` (`manuales-y-catalogos`) |
| SageMaker Endpoint | `ado-prediccion-eventos` (InService) |
| DynamoDB Telemetría | `ado-telemetria-live` |
| DynamoDB Alertas | `ado-alertas` |
| Bucket datos raw | `ado-telemetry-mvp` |
| Bucket lambdas | `mobilityia-hackathon-bl-2026` |
| Lambda Simulador | `ado-simulador-telemetria` |
| Lambda Predecir | `tool-predecir-evento` (SAGEMAKER_ENDPOINT=ado-prediccion-eventos) |
| Rol Agentes | `ado-bedrock-agent-role` |
| Rol Lambdas | `ado-lambda-execution-role` |

---

## Plan del día — Bloques de trabajo

### BLOQUE 1 — Infraestructura base ✅ COMPLETADO
> S3 + DynamoDB + Lambdas desplegadas por compañero de equipo.

#### 1.1 Infraestructura ✅
- [x] Bucket S3 `mobilityia-hackathon-bl-2026` (lambdas y catálogos)
- [x] Bucket S3 `ado-telemetry-mvp` (datos raw)
- [x] Tabla DynamoDB `ado-telemetria-live`
- [x] Tabla DynamoDB `ado-alertas`
- [x] Roles IAM: `ado-lambda-execution-role`, `ado-bedrock-agent-role`

#### 1.2 Datos en S3 ✅
- [x] Datos de telemetría (1,339 archivos Parquet, ~447 MB, 27.4M registros)
- [x] Datos de fallas (123 archivos Parquet, ~6.5 MB, 550K registros)
- [x] Catálogo SPN (1 archivo Parquet, 37 variables)
- [x] 3 manuales + 2 catálogos en Knowledge Base S3

#### 1.3 Lambdas desplegadas ✅
- [x] `ado-simulador-telemetria` (512 MB, 30s timeout)
- [x] `tool-consultar-telemetria`
- [x] `tool-calcular-desviacion`
- [x] `tool-listar-buses-activos`
- [x] `tool-consultar-obd`
- [x] `tool-predecir-evento` (SAGEMAKER_ENDPOINT=ado-prediccion-eventos)
- [x] `tool-buscar-patrones-historicos`
- [x] `tool-generar-recomendacion`
- [x] `ado-dashboard-api`
- [x] Layer `ado-common-layer` v2

### BLOQUE 2 — Agentes Bedrock (⚠️ PARCIALMENTE COMPLETADO)
> **Pendiente crítico:** Asociar Knowledge Base a ambos agentes.

#### 2.1 Knowledge Base ✅
- [x] Crear Knowledge Base en Bedrock: `ado-mobilityia-kb` (ID: `4OAVLRB8VI`)
- [x] 5 documentos indexados y sincronizados

#### 2.2 Agente Combustible ✅ (parcial)
- [x] Agente creado: `ado-agente-combustible` (ID: `5N3U0PMGXX`)
- [x] Modelo: Amazon Nova Micro
- [x] 3 Action Groups: consultar-telemetria, calcular-desviacion, listar-buses-activos
- [ ] **⚠️ PENDIENTE: Asociar Knowledge Base `4OAVLRB8VI`**
- [ ] Probar con preguntas de demo

#### 2.3 Agente Mantenimiento ✅ (parcial)
- [x] Agente creado: `ado-agente-mantenimiento` (ID: `KLLFLAH0SJ`)
- [x] Modelo: Amazon Nova Pro
- [x] 4 Action Groups: consultar-obd, predecir-evento, buscar-patrones-historicos, generar-recomendacion
- [ ] **⚠️ PENDIENTE: Asociar Knowledge Base `4OAVLRB8VI`**
- [ ] Probar con preguntas de demo

### BLOQUE 3 — SageMaker ✅ COMPLETADO
- [x] Modelo XGBoost entrenado con datos oct-dic 2020 (C-008)
- [x] Endpoint `ado-prediccion-eventos` desplegado y en InService
- [x] 128 features, test de predicción exitoso
- [x] Lambda `tool-predecir-evento` apunta al endpoint correcto

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
