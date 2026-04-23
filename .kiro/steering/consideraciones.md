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
---

## 🕐 CONSIDERACIONES PENDIENTES DE APLICAR
*(Ninguna por el momento — C-003 y C-004 aplicadas en todos los archivos del proyecto)*
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
