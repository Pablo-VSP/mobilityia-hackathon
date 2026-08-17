# Plan de trabajo — Migración de ADO MobilityIA a GCP

**Fecha de elaboración:** 12 de agosto de 2026  
**Inicio estimado:** 13 de agosto de 2026  
**Objetivo interno de cutover:** 11 de septiembre de 2026  
**Compromiso conservador de estabilización:** 18 de septiembre de 2026  
**Inicio posible del retiro de AWS:** 21 de septiembre de 2026

## 1. Objetivo

Completar la migración operativa de ADO MobilityIA desde AWS hacia GCP con una arquitectura de bajo costo y baja carga operacional. El desarrollo será asistido intensivamente por IA para acelerar implementación, SQL, pruebas, infraestructura y documentación, sin reducir las validaciones humanas, los controles de seguridad ni la observación productiva.

La migración operativa y la evolución del modelo predictivo se administran como dos entregas distintas:

1. **Migración operativa:** ingesta real, almacenamiento, APIs, agentes, frontend, autenticación, observabilidad y cutover.
2. **Predicción específica de fallas:** entrega posterior, condicionada a disponer de diagnósticos de taller u otras etiquetas verificadas.

## 2. Supuestos de estimación

- Equipo mínimo: cloud/backend, data/ML y frontend trabajando en paralelo.
- Apoyo parcial de un administrador GCP, seguridad y un experto de mantenimiento.
- La IA apoya generación de código, revisiones, transformaciones SQL, pruebas, documentación y automatización.
- Todo artefacto generado por IA debe ser revisado por una persona responsable.
- Firestore, IAM, Gemini e ingress se resuelven durante la primera fase.
- El MVP operativo utiliza anomalías, riesgo general y riesgo por subsistema mientras el catálogo siga siendo ambiguo.
- Los datos de demostración y prueba continúan identificándose como simulados; la fuente real se integra mediante Pub/Sub.

## 3. Estado de partida

### Implementado o desplegado parcialmente

- Cinco servicios base en Cloud Run: `api-dashboard`, `simulador`, `agente-combustible`, `agente-mantenimiento` y `chat-api`.
- VPC y subred corporativas configuradas.
- Datos disponibles en `gs://proy-ado-telemetria-dev-data-v1/aws_bl_hackathon/`.
- Health check interno de `api-dashboard` verificado.
- Simulador y Cloud Scheduler disponibles.
- Estructura inicial de agentes Gemini y herramientas locales.
- Generador de índice FAISS.
- Configuración inicial del cliente Firebase.

### Pendiente o incompleto

- Firestore `(default)` no existe y requiere intervención administrativa.
- La política organizacional permite únicamente ingress interno; falta definir el punto de entrada aprobado.
- Pub/Sub, el ingestor real y su dead-letter queue no están implementados.
- BigQuery no está integrado en la aplicación migrada.
- El simulador escribe directamente en Firestore en lugar de publicar en Pub/Sub.
- Gemini no tiene una identidad de ejecución completamente configurada.
- La inferencia XGBoost real está deshabilitada y utiliza un vector de features provisional.
- El RAG no está completo en ambos agentes.
- El frontend visual no está completo.
- El backend no valida Firebase JWT ni utiliza identidad entre servicios.
- Los scripts de despliegue todavía contienen un bucket distinto al bucket real.
- No existen pruebas automatizadas, CI/CD, alertamiento ni runbooks suficientes.
- El catálogo de fallas es ambiguo y no proporciona ground truth confiable.

## 4. Cronograma asistido por IA

| Fase | Fechas | Duración estimada | Entregable |
|---|---|---:|---|
| 0. Desbloqueos y decisiones | 13–17 ago | 3 días hábiles | Firestore, IAM, Gemini e ingress definidos |
| 1. Base cloud y configuración | 17–19 ago | 3 días | Despliegue reproducible y configuración consistente |
| 2. Pub/Sub, ingestor y BigQuery | 19–26 ago | 6 días | Ingesta real operativa |
| 3. Calidad de fallas y targets | 17 ago–2 sep | Trabajo paralelo | Catálogo curado y estrategia de resolución |
| 4. APIs, agentes, RAG y ML provisional | 24–28 ago | 5 días | Backend integrado |
| 5. Frontend y autenticación | 24 ago–1 sep | 7 días | Dashboard autenticado |
| 6. Integración, seguridad y pruebas | 2–4 sep | 3 días | Versión candidata |
| 7. Ensayo y cutover | 7–11 sep | 5 días | Operación principal en GCP |
| 8. Estabilización | 14–18 sep | 5 días | Aprobación operativa |
| 9. Retiro progresivo de AWS | Desde 21 sep | Condicionado | Apagado controlado |
| 10. Modelo supervisado específico | Hasta 16 oct | Condicionado | Predicción validada en modo sombra |

## 5. Fase 0 — Desbloqueos y decisiones

**Fechas:** 13–17 de agosto  
**Responsables:** administrador GCP, cloud/backend y seguridad.

### Tareas

- [ ] Crear Firestore Native `(default)` en `us-central1`.
- [ ] Aprobar el patrón de acceso al frontend y las APIs bajo la política de ingress corporativa.
- [ ] Crear service accounts dedicadas por servicio.
- [ ] Asignar permisos mínimos para Cloud Run, GCS, Firestore, BigQuery, Pub/Sub y Vertex AI.
- [ ] Configurar Gemini mediante Vertex AI e identidad GCP.
- [ ] Configurar Secret Manager para cualquier secreto residual.
- [ ] Confirmar topic, esquema y productor real de telemetría Pub/Sub.
- [ ] Abrir una solicitud formal al proveedor sobre SPN, FMI, ECU, `Source` y codificación de `Modulo`.

### Criterio de salida

Los servicios pueden autenticarse y acceder a sus dependencias, y existe una decisión aprobada para que el frontend alcance las APIs.

## 6. Fase 1 — Base cloud y configuración reproducible

**Fechas:** 17–19 de agosto  
**Responsable principal:** cloud/backend.

### Tareas

- [ ] Corregir `scripts/deploy-all.sh` para utilizar proyecto, región, bucket, prefijo, VPC y subred reales.
- [ ] Eliminar exposición pública y API keys directas donde no correspondan.
- [ ] Parametrizar Firestore, datasets, topics y URLs.
- [ ] Asignar una service account a cada servicio Cloud Run.
- [ ] Crear pipelines de build y deploy.
- [ ] Separar configuración de desarrollo y producción.
- [ ] Corregir documentación que presente componentes objetivo como ya implementados.

### Criterio de salida

El entorno puede desplegarse de forma repetible sin comandos ad hoc ni secretos locales.

## 7. Fase 2 — Ingesta real y capa de datos

**Fechas:** 19–26 de agosto  
**Responsables:** data engineer y cloud/backend.

### BigQuery

- [ ] Crear datasets `raw`, `curated` y `features`.
- [ ] Crear tablas de telemetría, fallas, candidatos, resoluciones y resultados de mantenimiento.
- [ ] Particionar temporalmente y clusterizar por autobús y firma diagnóstica.
- [ ] Crear vistas autorizadas y límites de consulta.
- [ ] Diseñar backfill idempotente desde el histórico existente.

### Pub/Sub

- [ ] Crear topics de telemetría y fallas.
- [ ] Crear suscripciones push para Cloud Run.
- [ ] Crear dead-letter topic y política de reintentos.
- [ ] Versionar y validar el esquema de mensajes.

### Ingestor Cloud Run

- [ ] Crear el servicio `ingestor`.
- [ ] Validar y normalizar payloads, timestamps y coordenadas.
- [ ] Generar claves de idempotencia.
- [ ] Pivotear lecturas SPN.
- [ ] Clasificar rangos operativos usando el catálogo SPN.
- [ ] Escribir estado reciente en Firestore.
- [ ] Escribir histórico en BigQuery.
- [ ] Conservar códigos y descripciones del proveedor como evidencia no verificada.
- [ ] Enviar mensajes inválidos a dead letter.
- [ ] Añadir logs y métricas estructuradas.

### Simulador

- [ ] Cambiar el simulador para publicar en Pub/Sub.
- [ ] Utilizar el mismo ingestor para datos simulados y reales.
- [ ] Mantener el simulador solo para pruebas y contingencia.

### Criterio de salida

Un evento publicado en Pub/Sub actualiza Firestore, se conserva en BigQuery y puede reprocesarse sin duplicarse.

## 8. Fase 3 — Calidad de fallas y construcción de targets

**Fechas:** 17 de agosto–2 de septiembre  
**Responsables:** data engineer, data scientist y experto de mantenimiento.

### Tareas

- [ ] Comparar BigQuery contra el payload crudo antes del enriquecimiento.
- [ ] Identificar dónde se agrega `descripcion`.
- [ ] Perfilar ambigüedad por modelo, submodelo, protocolo, firmware, módulo y código.
- [ ] Verificar si `CodigoOriginal` representa SPN bajo `J1939VO`.
- [ ] Investigar la codificación de `Modulo`.
- [ ] Normalizar y deduplicar descripciones sin sobrescribir la fuente.
- [ ] Crear taxonomía de sistema, subsistema, componente y modo de falla.
- [ ] Implementar estados `CONFIRMED`, `PROBABLE`, `AMBIGUOUS`, `NO_EVIDENCE` y `REJECTED`.
- [ ] Diseñar captura de diagnósticos y resultados de taller.
- [ ] Crear tablas `fault_event_raw`, `fault_mapping_candidate`, `fault_event_resolved` y `maintenance_outcome`.

### Regla de calidad

`descripcion` no se usa como target supervisado. Mientras no exista evidencia independiente, el sistema comunica anomalía, riesgo general, subsistema probable y firma diagnóstica cruda.

## 9. Fase 4 — APIs, agentes, RAG y ML provisional

**Fechas:** 24–28 de agosto  
**Responsables:** backend y ML/IA.

### Tareas

- [ ] Integrar `api-dashboard` con Firestore para estado reciente.
- [ ] Integrar BigQuery mediante consultas parametrizadas y acotadas.
- [ ] Evitar SQL libre generado por agentes.
- [ ] Validar Firebase JWT en `api-dashboard` y `chat-api`.
- [ ] Implementar identidad entre `chat-api` y los agentes.
- [ ] Migrar Gemini a Vertex AI.
- [ ] Completar function calling y manejo de errores.
- [ ] Construir y subir los artefactos FAISS.
- [ ] Integrar RAG en ambos agentes.
- [ ] Reemplazar el vector XGBoost provisional por features reales o deshabilitar la afirmación de predicción específica.
- [ ] Incorporar respuestas `PROBABLE` y `AMBIGUOUS` con evidencia.

### Criterio de salida

Los agentes consultan herramientas controladas, no inventan una descripción de falla y pueden explicar la evidencia usada para una recomendación.

## 10. Fase 5 — Frontend y autenticación

**Fechas:** 24 de agosto–1 de septiembre  
**Responsable:** frontend.

### Tareas

- [ ] Completar React, Vite y TypeScript.
- [ ] Migrar mapa, alertas, eficiencia, ambiental y chat.
- [ ] Integrar Firebase Auth.
- [ ] Adjuntar ID tokens en todas las llamadas.
- [ ] Representar visualmente estados probables y ambiguos.
- [ ] Implementar estados de carga, error y expiración de sesión.
- [ ] Normalizar coordenadas antes de mostrarlas.
- [ ] Configurar Firebase Hosting y CORS.
- [ ] Validar el patrón de ingress aprobado.

### Criterio de salida

Un usuario autenticado puede consultar estado reciente, históricos, alertas y agentes desde el entorno autorizado.

## 11. Fase 6 — Integración, seguridad y pruebas

**Fechas:** 2–4 de septiembre  
**Responsables:** todos los frentes.

### Pruebas

- [ ] Unitarias para normalización, pivoteo, idempotencia y resolución de fallas.
- [ ] Contrato de mensajes Pub/Sub.
- [ ] Integración Firestore y BigQuery.
- [ ] Autenticación y autorización.
- [ ] Comunicación Cloud Run a Cloud Run.
- [ ] Function calling y RAG.
- [ ] Replay desde GCS y dead-letter queue.
- [ ] Flujo end-to-end desde frontend.

### Operación y seguridad

- [ ] Añadir correlation IDs y logs estructurados.
- [ ] Crear dashboards de Cloud Monitoring.
- [ ] Alertar por errores, dead letters y latencia.
- [ ] Crear presupuestos y alertas de costo.
- [ ] Aplicar menor privilegio, Secret Manager y CORS restringido.
- [ ] Crear runbooks de incidente, replay y rollback.

### Criterio de salida

Existe una versión candidata reproducible, observable y con pruebas críticas aprobadas.

## 12. Fase 7 — Ensayo y cutover

**Fechas:** 7–11 de septiembre  
**Responsables:** cloud, data, producto y operaciones.

### Tareas

- [ ] Ejecutar un ensayo completo con replay representativo.
- [ ] Activar publicación real a Pub/Sub.
- [ ] Operar temporalmente en paralelo con el flujo anterior.
- [ ] Comparar eventos, snapshots y alertas.
- [ ] Validar frontend y agentes.
- [ ] Probar rollback.
- [ ] Desactivar el Scheduler del simulador.
- [ ] Actualizar el frontend con URLs finales.
- [ ] Obtener aprobación operativa y de seguridad.

### Criterio de salida

GCP es la ruta principal y AWS permanece disponible únicamente como rollback.

## 13. Fase 8 — Estabilización y retiro de AWS

**Estabilización:** 14–18 de septiembre  
**Retiro progresivo:** desde el 21 de septiembre.

### Tareas

- [ ] Monitorear mensajes inválidos, duplicados, latencia y costos.
- [ ] Ajustar escalamiento y timeouts.
- [ ] Corregir defectos funcionales y de experiencia.
- [ ] Confirmar que no existan consumidores restantes en AWS.
- [ ] Respaldar datos y configuración.
- [ ] Obtener aprobación formal antes de eliminar recursos.

AWS no se elimina durante el cutover. El retiro comienza únicamente después de completar la estabilización y cumplir la ventana de rollback.

## 14. Línea de trabajo del modelo predictivo

La migración operativa no depende de resolver completamente el catálogo. La predicción exacta de componente sí depende de etiquetas confiables.

### Si existen órdenes de trabajo o diagnósticos históricos

| Actividad | Fechas estimadas |
|---|---|
| Integración y limpieza de resultados de taller | 1–4 sep |
| Construcción de targets confirmados | 7–11 sep |
| Feature engineering | 7–14 sep |
| Entrenamiento y evaluación temporal | 15–18 sep |
| Inicio de modo sombra | 21 sep |
| Observación y calibración | 21 sep–9 oct |
| Revisión con mantenimiento | 12–14 oct |
| Liberación tentativa | 16 oct |

### Si no existen etiquetas confirmadas

La primera versión ofrece:

- Detección de anomalías.
- Riesgo general.
- Subsistema con mayor evidencia.
- Firma diagnóstica cruda.
- Resolución probable o ambigua.
- Recomendación preventiva.

No se publica una predicción exacta de componente hasta contar con validación independiente.

## 15. Ruta crítica

```text
Permisos + Firestore + ingress + Gemini
                    ↓
Configuración + Pub/Sub + BigQuery + ingestor
                    ↓
APIs + agentes + frontend
                    ↓
Seguridad + pruebas end-to-end
                    ↓
Ensayo + cutover
                    ↓
Estabilización
```

## 16. Fechas de compromiso

- **Objetivo interno de cutover:** 11 de septiembre de 2026.
- **Compromiso conservador:** 18 de septiembre de 2026.
- **Retiro progresivo de AWS:** desde el 21 de septiembre de 2026.
- **Modelo supervisado específico:** 16 de octubre de 2026, solo si existen etiquetas confirmadas oportunamente.

Los bloqueos administrativos, la respuesta del proveedor y la obtención de ground truth pueden mover estas fechas; la asistencia de IA no elimina esas dependencias.
