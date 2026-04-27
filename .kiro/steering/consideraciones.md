---
inclusion: always
---

# 📋 Control de Consideraciones del Proyecto
## ADO Intelligence Platform — Hackathon AWS ITP LATAM

> Este archivo es la fuente de verdad para todas las restricciones, decisiones y ajustes que afectan la planeación y desarrollo del proyecto. Toda nueva consideración debe registrarse aquí antes de aplicarse.

---

## ✅ CONSIDERACIONES ACTIVAS

### C-001 — Alcance MVP para Hackathon (5 días)
- **Fecha:** 2026-04-22
- **Estado:** ✅ Activa
- **Descripción:** El proyecto es una presentación para la competencia del Hackathon de AWS. Debe ser lo más acotado posible, abarcando solo lo necesario para presentarse como MVP. El tiempo máximo de desarrollo es de **5 días**.
- **Impacto:**
  - Solo se implementan los componentes estrictamente necesarios para demostrar el valor del sistema
  - Se priorizan los 2 agentes de mayor impacto visual y técnico para el jurado
  - Se elimina cualquier componente que no sea demostrable en la presentación
  - No se construye infraestructura de producción (sin multi-AZ, sin DR, sin auto-scaling complejo)
  - El código debe ser funcional y demostrable, no production-ready

### C-002 — Datos Históricos desde GCP + Simulación de Tiempo Real con Lambda
- **Fecha:** 2026-04-22
- **Estado:** ✅ Activa
- **Descripción:** El proyecto utilizará información histórica migrada desde la nube de GCP hacia S3. La ingesta en tiempo real será **simulada** mediante AWS Lambda para fines de presentación. No se conectará a buses reales ni a IoT Core en el MVP.
- **Impacto:**
  - **Se elimina AWS IoT Core** del MVP (reemplazado por Lambda simulador)
  - **Se elimina Amazon Kinesis** del MVP (reemplazado por Lambda que escribe directo a DynamoDB/S3)
  - Se requiere un script/proceso de migración de datos GCP → S3
  - Lambda actuará como "generador de telemetría" inyectando datos históricos con timestamps simulados en tiempo real
  - La arquitectura se simplifica significativamente en la capa de ingesta
  - Los datos en S3 son el punto de partida real; Lambda simula el flujo "en vivo" para la demo

### C-003 — Evitar uso de métricas por magnitudes definidas
- **Fecha:** 2026-04-23
- **Estado:** ✅ Activa 
- **Descripción:** El proyecto deberá evitar mencionar magnitudes definidas como métricas por ejemplo: 
| Beneficio | Impacto cuantificado |
|---|---|
| Reducción de consumo de combustible | 8–15% → hasta **$2.8M MXN/mes** en ahorro directo |
| Anticipación de fallas mecánicas | 75–85% de fallas anticipadas → reducción 3–5x en costo de mantenimiento |
| Estandarización de conducción | Variabilidad entre conductores: de 18% → 7% |
| Evidencia regulatoria | **2,400 toneladas de CO₂** reducidas documentadas y auditables en 90 días |

En lugar de ello debe mencionar mejoras en lenguaje difuso tal que "Aumento", "Mayor", "Menor" y demás adaptaciones sin mencionar valores numéricos específicos que podrían caer en información sin fundamentos al tratarse de un proyecto MVP por simulación para un Hackathon.

- **Impacto:**
  - Eliminar métricas con magnitudes numéricas y sustituirlas por lenguaje difuso
  - Se debe reescribir todo el flujo de planeación, archivos de steering files y redefinir el ITP-LATAM-WB-Workshop.md respecto a esta nueva consideración.


### C-004 — El proyecto se trabajará con datos simulados para mantener un tema de seguridad de la información corporativa para este proyecto MVP 
- **Fecha:** 2026-04-23
- **Estado:** ✅ Activa
- **Descripción:** Se debe considerar que la ingesta de datos al bucket de S3 se hará con datos simulados para fines de presentación del proyecto beta en el hackathon.
- **Impacto:**
  - En lugar de datos históricos se hablará de usar datos simulados
  - Se debe reescribir todo el flujo de planeación, archivos de steering files y redefinir el ITP-LATAM-WB-Workshop.md respecto a esta nueva consideración.


### C-005 — Definición del concepto de agentes
- **Fecha:** 2026-04-27
- **Estado:** ✅ Activa
- **Descripción:** Siempre que se hable del concepto de Agentes se debe considerar que son agentes de AgentCore, no considerar agentes de Bedrock.
- **Impacto:**
  - Cada que se hable de Agentes seran Agentes de AgentCore.
  - Se debe tener en cuenta la documentación más actualizada de Agentes de AgentCore.
  - Esto afecta a las descripciones y planeaciones realizadas hasta ahora.

  ### C-006 — Actualización de steering files y planeaciones de acuerdo a modelos relacionados con layout de las tablas ubicados en la carpeta Models
- **Fecha:** 2026-04-27
- **Estado:** ✅ Activa
- **Descripción:** Se deben actualizar los datos relacionados con el layout de las tablas a utilizar de acuerdo a directorio models.
- **Impacto:**
  - Se deben actualizar los steering files y archivos de planeacion de acuerdo a los campos de cada tabla ubicados en models.
  - Editar el data-schema.md actualizando sus consideraciones acerca del bucket de S3 considerando las tres tablas de la carpeta models, y catalogos de manual-reglas-mantenimiento-motor.md (que esta haciendo otro compañero) y manual-combustible.md  (que esta haciendo otro compañero) pero que ambos van referidos junto con el nuevo de la consideración C-007 a ser catálogos para la knoledge base.

### C-007 — Consideracion de códigos de falla a tomar en cuenta
- **Fecha:** 2026-04-27
- **Estado:** ✅ Activa 
- **Descripción:** Se debe estudiar y generar un catálogo de códigos de falla por descripción de acuerdo al documento fault_data_catalog.JSON ubicado en la carpeta datos_spn con el fin de determinar cuáles son los códigos de falla importantes para ser considerados por el modelo de predicción de fallas ml que se desarrollará en SAGEMAKER
- **Impacto:**
  - Cambia en el proyecto el enfoque de planeación para predecir tema de las fallas relevantes, generando o modificando el JSON de fault_data_catalog asignando un campo de severidad_inferencia en el cual asignes tú un nivel de severidad de 1 como mínimo a 3 como máxima con la que clasifiques al menos 5 fallas que consideres relevantes tomando en cuenta el campo NUM que corresponde a las veces que se presenta esa falla en el total de datos históricos que se tienen para simulación del proyecto. 
  - La idea es generar datos limpios que nos permitan entrenar un modelo de forma adecuada para el tema de mantenimiento preventivo.
---

## 🕐 CONSIDERACIONES PENDIENTES DE APLICAR
*(Todas aplicadas — C-005, C-006 y C-007 integradas en steering files el 2026-04-27)*
---

## 📝 PLANTILLA PARA NUEVA CONSIDERACIÓN

```
### C-XXX — [Título corto]
- **Fecha:** YYYY-MM-DD
- **Estado:** ✅ Activa | ⏸️ En revisión | ❌ Descartada
- **Descripción:** [Qué es la consideración]
- **Impacto:**
  - [Qué cambia en el proyecto]
  - [Qué se elimina o agrega]
  - [Qué decisiones técnicas afecta]
```

---

## ❌ CONSIDERACIONES DESCARTADAS
*(Ninguna por el momento)*
