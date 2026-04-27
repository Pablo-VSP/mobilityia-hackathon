# 🔧 Manual de Reglas de Mantenimiento — Parámetros de Motor
## ADO MobilityIA — Catálogo SPN (Suspect Parameter Numbers)

> Este manual define las reglas de mantenimiento programado, preventivo y correctivo basadas en los 37 parámetros de motor monitoreados por telemetría.
> Los umbrales se derivan de los valores mínimos y máximos del catálogo SPN del parque vehicular.
> **C-004:** Los datos de referencia son simulados para fines del MVP.

---

## Índice de parámetros monitoreados

| SPN | Nombre | Unidad | Mínimo | Máximo |
|-----|--------|--------|--------|--------|
| 10098 | Nivel de aceite (litros) | L | -6.75 | 0.00 |
| 70 | Interruptor freno de estacionamiento | bit | 0 | 1 |
| 597 | Brake Switch | bit | 0 | 1 |
| 596 | Cruise Control Enable Switch | bit | 0 | 1 |
| 598 | Clutch Switch | bit | 0 | 1 |
| 527 | Cruise Control States | bit | 0 | 6 |
| 523 | Marchas | Marcha | -3 | 16 |
| 20001 | Voltaje batería mínimo histórico | V | 0 | 36 |
| 20000 | Voltaje batería sin alternador | V | 0 | 36 |
| 168 | Voltaje Batería | V | 0 | 36 |
| 185 | Rendimiento | km/L | 0 | 50 |
| 184 | Ahorro de combustible instantáneo | km/L | 0 | 50 |
| 171 | Temperatura ambiente | °C | -10 | 75 |
| 521 | Posición Pedal Freno | % | 0 | 100 |
| 1761 | Nivel Urea | % | 0 | 100 |
| 91 | Posición Pedal Acelerador | % | 0 | 100 |
| 183 | Tasa de combustible | L/h | 0 | 100 |
| 513 | Porcentaje Torque | % | 0 | 100 |
| 111 | Nivel de anticongelante | % | 0 | 110 |
| 98 | Nivel de aceite (%) | % | 0 | 110 |
| 1624 | Velocidad tacógrafo | km/h | 0 | 120 |
| 96 | Nivel Combustible | % | 0 | 120 |
| 84 | Velocidad km/h | km/h | 0 | 120 |
| 520 | Retarder Percent Torque | % | -125 | 125 |
| 175 | Temperatura Aceite Motor | °C | 0 | 150 |
| 110 | Temperatura Motor | °C | 0 | 150 |
| 100 | Presión Aceite Motor | kPa | 0 | 1000 |
| 190 | RPM | rpm | 0 | 3000 |
| 250 | Combustible Consumido | L | 1 | 4,211,081 |
| 247 | Horas Motor | h | 1 | 214,748,400 |
| 917 | Odómetro | km | 0 | 691,208,000 |
| 1102 | % Restante balata trasero derecho 1 | % | 0 | 100 |
| 1099 | % Restante balata delantero izquierdo | % | 0 | 100 |
| 1104 | % Restante balata trasero derecho 2 | % | 0 | 100 |
| 1101 | % Restante balata trasero izquierdo 1 | % | 0 | 100 |
| 1100 | % Restante balata delantero derecho | % | 0 | 100 |
| 1103 | % Restante balata trasero izquierdo 2 | % | 0 | 100 |

---

## 1. MANTENIMIENTO PROGRAMADO

Mantenimiento basado en intervalos de uso acumulado (kilómetros, horas motor, litros consumidos). Se ejecuta independientemente del estado actual de los componentes.

---

### 1.1 Por Odómetro (SPN 917)

| Intervalo (km) | Acción de mantenimiento |
|-----------------|------------------------|
| Cada 10,000 km | Revisión general de niveles (aceite, anticongelante, urea). Inspección visual de balatas. Verificación de voltaje de batería. |
| Cada 20,000 km | Cambio de aceite de motor. Revisión de presión de aceite (SPN 100). Inspección de sistema de frenos completo. |
| Cada 40,000 km | Cambio de filtros (aceite, combustible, aire). Revisión de sistema de enfriamiento (temperatura motor SPN 110, temperatura aceite SPN 175). Calibración de sensores de pedal (SPN 91, SPN 521). |
| Cada 80,000 km | Revisión mayor de transmisión (SPN 523 — marchas). Inspección de retarder (SPN 520). Evaluación de rendimiento de combustible (SPN 185) contra línea base de la ruta. |
| Cada 150,000 km | Overhaul parcial de motor. Revisión de sistema eléctrico completo (SPN 168, 20000, 20001). Cambio de balatas si no se ha realizado por desgaste. |

### 1.2 Por Horas Motor (SPN 247)

| Intervalo (horas) | Acción de mantenimiento |
|--------------------|------------------------|
| Cada 250 h | Verificación de niveles de aceite (SPN 98, SPN 10098) y anticongelante (SPN 111). |
| Cada 500 h | Cambio de aceite de motor. Revisión de presión de aceite (SPN 100). Análisis de rendimiento de combustible (SPN 185, SPN 184). |
| Cada 1,000 h | Revisión de sistema de enfriamiento. Inspección de sistema de escape y nivel de urea (SPN 1761). |
| Cada 2,500 h | Revisión mayor de motor. Evaluación integral de todos los parámetros contra valores de referencia. |

### 1.3 Por Combustible Consumido (SPN 250)

| Intervalo (litros) | Acción de mantenimiento |
|---------------------|------------------------|
| Cada 5,000 L | Revisión de filtros de combustible. Verificar tasa de combustible (SPN 183) dentro de rango operativo. |
| Cada 20,000 L | Limpieza/revisión de inyectores. Comparar rendimiento (SPN 185) contra histórico de la unidad. |

---

## 2. MANTENIMIENTO PREVENTIVO

Mantenimiento activado cuando los parámetros en tiempo real muestran tendencias de desgaste o degradación, antes de que se conviertan en falla. Se basa en umbrales de alerta derivados de los rangos del catálogo SPN.

---

### 2.1 Sistema de Frenos — Balatas (SPN 1099, 1100, 1101, 1102, 1103, 1104)

| Parámetro | Rango normal | Umbral preventivo | Regla |
|-----------|-------------|-------------------|-------|
| % Restante balata delantero izquierdo (SPN 1099) | 100% – 30% | ≤ 30% | Programar cambio en próximo servicio |
| % Restante balata delantero derecho (SPN 1100) | 100% – 30% | ≤ 30% | Programar cambio en próximo servicio |
| % Restante balata trasero izquierdo 1 (SPN 1101) | 100% – 30% | ≤ 30% | Programar cambio en próximo servicio |
| % Restante balata trasero derecho 1 (SPN 1102) | 100% – 30% | ≤ 30% | Programar cambio en próximo servicio |
| % Restante balata trasero izquierdo 2 (SPN 1103) | 100% – 30% | ≤ 30% | Programar cambio en próximo servicio |
| % Restante balata trasero derecho 2 (SPN 1104) | 100% – 30% | ≤ 30% | Programar cambio en próximo servicio |
| Cualquier balata | — | ≤ 20% | Cambio urgente esta semana |
| Diferencia entre balatas del mismo eje | — | > 15% de diferencia | Revisar desgaste desigual — posible problema de alineación o caliper |

### 2.2 Sistema de Lubricación

| Parámetro | Rango normal | Umbral preventivo | Regla |
|-----------|-------------|-------------------|-------|
| Nivel de aceite litros (SPN 10098) | -6.75 a 0 L | Tendencia descendente sostenida (> 3 lecturas consecutivas bajando) | Inspeccionar fugas. Programar revisión de empaques y sellos. |
| Nivel de aceite % (SPN 98) | 50% – 110% | ≤ 25% | Rellenar aceite y programar inspección de consumo anormal. |
| Presión Aceite Motor (SPN 100) | 200 – 800 kPa | ≤ 150 kPa en operación normal | Revisar bomba de aceite, filtro y viscosidad del lubricante. |
| Temperatura Aceite Motor (SPN 175) | 80°C – 120°C | ≥ 130°C sostenido | Revisar sistema de enfriamiento de aceite. Verificar nivel y calidad del lubricante. |

### 2.3 Sistema de Enfriamiento

| Parámetro | Rango normal | Umbral preventivo | Regla |
|-----------|-------------|-------------------|-------|
| Temperatura Motor (SPN 110) | 80°C – 105°C | ≥ 115°C sostenido (> 5 min) | Revisar termostato, radiador, bomba de agua. Verificar nivel de anticongelante. |
| Nivel de anticongelante (SPN 111) | 60% – 110% | ≤ 40% | Rellenar y buscar fugas en el sistema de enfriamiento. |
| Temperatura ambiente (SPN 171) | -10°C – 75°C | ≥ 45°C | Considerar ajuste de intervalos de enfriamiento. Monitorear temperatura motor con mayor frecuencia. |

### 2.4 Sistema Eléctrico

| Parámetro | Rango normal | Umbral preventivo | Regla |
|-----------|-------------|-------------------|-------|
| Voltaje Batería (SPN 168) | 12.4V – 14.8V | ≤ 12.0V o ≥ 15.5V | Revisar alternador y estado de batería. |
| Voltaje batería sin alternador (SPN 20000) | 12.0V – 13.0V | ≤ 11.5V | Batería con capacidad reducida. Programar reemplazo. |
| Voltaje batería mínimo histórico (SPN 20001) | > 10.5V | ≤ 10.0V | Batería ha sufrido descarga profunda. Evaluar reemplazo y revisar consumo parásito. |

### 2.5 Sistema de Combustible y Rendimiento

| Parámetro | Rango normal | Umbral preventivo | Regla |
|-----------|-------------|-------------------|-------|
| Rendimiento (SPN 185) | Varía por ruta (ver catálogo de rutas) | Caída sostenida respecto al promedio histórico de la unidad en la misma ruta | Revisar inyectores, filtros de combustible, presión de llantas, estilo de conducción. |
| Tasa de combustible (SPN 183) | 10 – 60 L/h (según operación) | ≥ 70 L/h sostenido en crucero | Posible fuga o inyección excesiva. Revisar sistema de inyección. |
| Nivel Combustible (SPN 96) | 20% – 100% | ≤ 15% | Alerta de reabastecimiento. Evitar operación con tanque bajo (riesgo de succión de sedimentos). |
| Nivel Urea (SPN 1761) | 20% – 100% | ≤ 15% | Reabastecer urea. Sin urea el sistema SCR no reduce emisiones NOx (impacto en cumplimiento NOM-044). |

### 2.6 Motor y Transmisión

| Parámetro | Rango normal | Umbral preventivo | Regla |
|-----------|-------------|-------------------|-------|
| RPM (SPN 190) | 600 – 2200 rpm | ≥ 2500 rpm sostenido en crucero | Revisar estilo de conducción. Posible problema en transmisión (no cambia a marcha superior). |
| Porcentaje Torque (SPN 513) | 20% – 85% | ≥ 95% sostenido sin carga en pendiente | Motor trabajando al límite. Revisar carga, freno de motor, estado de turbo. |
| Marchas (SPN 523) | 1 – 16 (según modelo) | Cambios erráticos o permanencia prolongada en marchas bajas a velocidad de crucero | Revisar transmisión automática/automatizada. Posible falla en ECU de transmisión. |
| Retarder Percent Torque (SPN 520) | -125% a 0% (frenado) | Uso excesivo sostenido (> -100% frecuente) | Revisar sistema de frenos principal. El conductor podría estar compensando frenos deficientes con retarder. |

### 2.7 Conducción — Patrones de Alerta

| Parámetro | Rango normal | Umbral preventivo | Regla |
|-----------|-------------|-------------------|-------|
| Posición Pedal Acelerador (SPN 91) | 20% – 60% en crucero | ≥ 80% sostenido frecuentemente | Patrón de aceleración brusca. Genera desgaste prematuro y mayor consumo. Retroalimentar al conductor. |
| Posición Pedal Freno (SPN 521) | 0% – 40% en frenado normal | ≥ 70% frecuentemente | Patrón de frenado tardío/brusco. Desgaste acelerado de balatas. Retroalimentar al conductor. |
| Velocidad (SPN 84) | Según ruta y tramo | ≥ 100 km/h sostenido en tramos urbanos | Exceso de velocidad. Impacto en seguridad, consumo y desgaste. |
| Velocidad tacógrafo (SPN 1624) | Debe coincidir con SPN 84 | Diferencia > 5 km/h respecto a SPN 84 | Posible descalibración de tacógrafo. Revisar sensor. |

---

## 3. MANTENIMIENTO CORRECTIVO

Mantenimiento activado cuando los parámetros exceden los límites operativos seguros. Requiere intervención inmediata — la unidad debe salir de servicio o ser atendida en la próxima parada.

---

### 3.1 Condiciones de Paro Inmediato 🔴

Estas condiciones requieren detener la unidad de forma segura lo antes posible:

| Condición | Parámetros involucrados | Acción correctiva |
|-----------|------------------------|-------------------|
| Sobrecalentamiento de motor | Temperatura Motor (SPN 110) ≥ 140°C | Detener unidad. No apagar motor inmediatamente (dejar enfriar en ralentí 3-5 min). Inspeccionar radiador, termostato, bomba de agua, mangueras. |
| Sobrecalentamiento de aceite | Temperatura Aceite Motor (SPN 175) ≥ 145°C | Detener unidad. Verificar nivel de aceite, enfriador de aceite, bomba de aceite. |
| Pérdida de presión de aceite | Presión Aceite Motor (SPN 100) ≤ 50 kPa en operación | Detener motor inmediatamente. Riesgo de daño catastrófico a componentes internos. Remolcar a taller. |
| Falla eléctrica crítica | Voltaje Batería (SPN 168) ≤ 10V o ≥ 16.5V | Detener unidad. Voltaje bajo: falla de alternador. Voltaje alto: regulador de voltaje dañado (riesgo de daño a ECUs). |
| Balatas agotadas | Cualquier balata (SPN 1099-1104) ≤ 5% | Unidad fuera de servicio. Cambio inmediato obligatorio antes de volver a operar. |

### 3.2 Condiciones de Intervención Urgente 🟠

La unidad puede completar su viaje actual pero debe ser atendida antes del siguiente servicio:

| Condición | Parámetros involucrados | Acción correctiva |
|-----------|------------------------|-------------------|
| Temperatura motor persistentemente alta | Temperatura Motor (SPN 110) entre 120°C – 140°C de forma sostenida | Completar viaje a velocidad reducida. En taller: revisar termostato, nivel de anticongelante, radiador, ventilador. |
| Presión de aceite baja | Presión Aceite Motor (SPN 100) entre 50 – 150 kPa | Completar viaje monitoreando. En taller: cambio de aceite, revisión de bomba y filtro. |
| Nivel de aceite crítico | Nivel de aceite % (SPN 98) ≤ 15% | Rellenar aceite en próxima parada. Inspeccionar fugas visibles. Programar revisión de empaques. |
| Anticongelante crítico | Nivel de anticongelante (SPN 111) ≤ 20% | Rellenar en próxima parada. Buscar fugas en mangueras, radiador, bomba de agua. |
| RPM excesivas sostenidas | RPM (SPN 190) ≥ 2800 rpm sostenido | Verificar transmisión (¿no cambia de marcha?). Revisar ECU de transmisión, sensores de velocidad, actuadores. |
| Voltaje anormal sostenido | Voltaje Batería (SPN 168) entre 10V – 12V o 15.5V – 16.5V | Revisar alternador, regulador de voltaje, conexiones de batería. |
| Desgaste desigual severo de balatas | Diferencia > 30% entre balatas del mismo eje | Revisar calipers, mangueras de freno, válvula de distribución. Posible caliper pegado. |

### 3.3 Condiciones de Registro y Seguimiento 🟡

No requieren paro pero deben documentarse y dar seguimiento en el próximo mantenimiento programado:

| Condición | Parámetros involucrados | Acción correctiva |
|-----------|------------------------|-------------------|
| Consumo de combustible anormalmente alto | Rendimiento (SPN 185) consistentemente por debajo del promedio de ruta + Tasa de combustible (SPN 183) elevada | Registrar. Revisar en próximo servicio: inyectores, filtros, presión de llantas, alineación. |
| Patrón de conducción agresiva recurrente | Pedal Acelerador (SPN 91) ≥ 80% frecuente + Pedal Freno (SPN 521) ≥ 70% frecuente | Registrar conductor y unidad. Programar retroalimentación de conducción eficiente. |
| Uso excesivo de retarder | Retarder (SPN 520) en valores extremos frecuentemente | Registrar. Verificar estado de frenos de servicio — el conductor podría estar compensando. |
| Marchas erráticas | Marchas (SPN 523) con cambios no lógicos o permanencia en neutro | Registrar. Revisar ECU de transmisión y sensores en próximo servicio. |
| Descalibración de tacógrafo | Diferencia entre Velocidad (SPN 84) y Tacógrafo (SPN 1624) > 5 km/h | Registrar. Calibrar tacógrafo en próximo servicio. Verificar sensor de velocidad. |
| Nivel de urea bajo | Nivel Urea (SPN 1761) ≤ 10% | Reabastecer. Si es recurrente, verificar consumo del sistema SCR y posibles fugas. |

---

## 4. MATRIZ DE CORRELACIÓN DE PARÁMETROS

Algunos eventos de mantenimiento se detectan mejor combinando múltiples señales:

| Escenario | Señales combinadas | Diagnóstico probable | Tipo de mantenimiento |
|-----------|-------------------|---------------------|----------------------|
| Falla inminente de bomba de agua | Temperatura Motor ↑ + Nivel anticongelante ↓ + RPM normales | Bomba de agua con fuga o falla mecánica | Correctivo urgente |
| Turbo con degradación | RPM altas + Torque bajo + Consumo alto + Acelerador alto | Turbocompresor con pérdida de eficiencia | Preventivo — programar revisión |
| Transmisión con problemas | Marchas erráticas + RPM altas a velocidad baja + Consumo elevado | Falla en ECU o actuadores de transmisión | Correctivo urgente |
| Frenos compensados con retarder | Retarder uso excesivo + Balatas con desgaste desigual + Pedal freno bajo | Caliper pegado o manguera de freno obstruida | Preventivo — revisar esta semana |
| Alternador fallando | Voltaje batería ↓ + Voltaje sin alternador ↓ + Voltaje mínimo histórico ↓ | Alternador con carga insuficiente o batería agotada | Correctivo — reemplazar antes de falla total |
| Conducción ineficiente | Acelerador alto frecuente + Frenado brusco frecuente + Rendimiento bajo + Velocidad variable | Estilo de conducción agresivo | Preventivo — capacitación al conductor |
| Fuga de aceite | Nivel aceite (L) descendente + Nivel aceite (%) descendente + Presión aceite descendente | Fuga en empaques, sellos o cárter | Preventivo — inspección visual y reparación |

---

## 5. REGLAS PARA EL AGENTE DE MANTENIMIENTO PREDICTIVO

Resumen de umbrales que el agente de IA debe considerar al analizar telemetría:

```
REGLAS DE ALERTA AUTOMÁTICA:
├── 🔴 CRÍTICO (paro inmediato):
│   ├── Temperatura Motor ≥ 140°C
│   ├── Temperatura Aceite ≥ 145°C
│   ├── Presión Aceite ≤ 50 kPa
│   ├── Voltaje Batería ≤ 10V o ≥ 16.5V
│   └── Cualquier balata ≤ 5%
│
├── 🟠 ELEVADO (intervención esta semana):
│   ├── Temperatura Motor 120°C – 140°C sostenido
│   ├── Presión Aceite 50 – 150 kPa
│   ├── Nivel aceite ≤ 15%
│   ├── Anticongelante ≤ 20%
│   ├── RPM ≥ 2800 sostenido
│   ├── Voltaje 10V – 12V o 15.5V – 16.5V
│   ├── Cualquier balata ≤ 20%
│   └── Diferencia entre balatas mismo eje > 30%
│
├── 🟡 MODERADO (próximo servicio):
│   ├── Temperatura Motor 115°C – 120°C
│   ├── Presión Aceite 150 – 200 kPa
│   ├── Nivel aceite 15% – 25%
│   ├── Anticongelante 20% – 40%
│   ├── Cualquier balata 20% – 30%
│   ├── Diferencia entre balatas mismo eje 15% – 30%
│   ├── Rendimiento por debajo del promedio de ruta
│   ├── Urea ≤ 15%
│   └── Voltaje mínimo histórico ≤ 10V
│
└── 🟢 BAJO (monitoreo normal):
    └── Todos los parámetros dentro de rangos operativos
```

---

## 6. NOTAS OPERATIVAS

- Los intervalos de mantenimiento programado deben ajustarse según las condiciones de operación: rutas con mayor altitud, temperatura extrema o tráfico urbano intenso pueden requerir intervalos más cortos.
- Las reglas preventivas se activan por tendencia, no por lecturas aisladas. Una sola lectura fuera de rango puede ser ruido del sensor. Se requieren al menos 3 lecturas consecutivas o un patrón sostenido para generar alerta.
- Las reglas correctivas de paro inmediato (🔴) se activan con una sola lectura confirmada — la seguridad del pasajero es prioridad absoluta.
- Los switches binarios (SPN 70, 597, 596, 598) se usan para contexto operativo (¿está frenando?, ¿está en crucero?) y no generan alertas de mantenimiento por sí mismos.
- El Cruise Control States (SPN 527) y Cruise Control Enable Switch (SPN 596) se usan para correlacionar patrones de conducción con consumo de combustible.
