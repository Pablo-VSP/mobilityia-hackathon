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

---

## 🕐 CONSIDERACIONES PENDIENTES DE APLICAR
*(Ninguna por el momento)*

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
