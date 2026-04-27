# 🌿 Manual de Reglas Ambientales y Control de Emisiones
## ADO MobilityIA — Alineación con Normatividad Ambiental Mexicana

> Este manual define las reglas de monitoreo ambiental basadas en los parámetros de motor (catálogo SPN) y su relación con la normatividad ambiental vigente en México.
> Línea pivote: ruta CDMX → Acapulco (~380 km por Autopista del Sol, Highway 95D).
> Rendimiento de referencia en esta ruta: 3.7 km/L de diésel.
> **C-004:** Los datos son simulados para fines del MVP.
> **C-003:** Las respuestas al usuario usan lenguaje difuso, sin valores numéricos específicos de mejora.

---

## 1. MARCO NORMATIVO APLICABLE

### 1.1 NOM-044-SEMARNAT-2017 — Emisiones de vehículos pesados diésel nuevos

Norma principal para autobuses de pasajeros con peso bruto vehicular mayor a 3,857 kg.

Establece límites máximos permisibles de emisiones contaminantes del escape de motores diésel nuevos. A partir de 2022, todos los vehículos pesados nuevos vendidos en México deben cumplir con estándares equivalentes a US EPA 2010 o Euro VI (estándar B de la norma).

Contaminantes regulados:
- CO (Monóxido de carbono)
- NOx (Óxidos de nitrógeno)
- NMHC (Hidrocarburos no metánicos)
- PM (Material particulado)
- Número de partículas
- NH₃ (Amoniaco) — solo Euro VI

Límites de referencia estándar B (los más estrictos, vigentes):

| Alineación | Ciclo de prueba | CO | NOx | NMHC | PM |
|------------|----------------|-----|------|------|-----|
| US EPA 2010 (1B) | SET & FTP | 15.5 g/bhp-hr | 0.20 g/bhp-hr | 0.14 g/bhp-hr | 0.01 g/bhp-hr |
| Euro VI (2B) | WHSC | 1.5 g/kWh | 0.4 g/kWh | 0.13 g/kWh | 0.01 g/kWh |
| Euro VI (2B) | WHTC | 4.0 g/kWh | 0.46 g/kWh | 0.16 g/kWh | 0.01 g/kWh |

Requisitos adicionales:
- Sistema OBD completo obligatorio para estándar B
- Sistema SCR (Reducción Catalítica Selectiva) con urea/DEF obligatorio
- Mecanismos anti-manipulación del sistema de post-tratamiento
- Alertas e inductores de falla cuando el DEF (urea) es insuficiente o de mala calidad

Fuente: [transportpolicy.net — Mexico Heavy-duty Emissions](https://www.transportpolicy.net/standard/mexico-heavy-duty-emissions/)

### 1.2 NOM-045-SEMARNAT-2006 — Opacidad de humo en vehículos diésel en circulación

Aplica a vehículos diésel ya en operación. Establece límites de opacidad de humo medidos en verificación vehicular periódica. Los autobuses en circulación deben pasar esta prueba para mantener su permiso de operación.

### 1.3 NOM-041-SEMARNAT-2006 — Emisiones de vehículos en circulación (gasolina)

Aunque aplica a gasolina, establece el marco general de verificación vehicular que también rige los programas de inspección para flotas de transporte.

### 1.4 Ley General de Cambio Climático (LGCC)

México se comprometió en su NDC (Contribución Nacionalmente Determinada) a reducir emisiones de GEI en un 35% para 2030 de forma incondicional. El sector transporte es uno de los principales emisores. Para el sector transporte, se requiere una reducción significativa de emisiones de CO₂ para alinearse con las metas del Acuerdo de París.

Fuente: [Climate Action Tracker — Mexico](https://climateactiontracker.org/countries/mexico/)

### 1.5 Acuerdo de París — Compromisos de México

México ha anunciado meta de cero emisiones netas para 2050 y un objetivo de 364–404 MtCO₂e para 2035. El transporte terrestre de pasajeros es un sector clave para alcanzar estas metas.

---

## 2. FACTOR DE EMISIÓN DE CO₂ — DIÉSEL

El factor de emisión estándar internacionalmente aceptado (IPCC) para diésel es:

> **2.68 kg de CO₂ por litro de diésel consumido**

Este factor se usa para estimar las emisiones de CO₂ a partir del consumo de combustible registrado por telemetría.

### 2.1 Cálculo de referencia — Ruta CDMX → Acapulco

| Parámetro | Valor de referencia |
|-----------|-------------------|
| Distancia de la ruta | ~380 km (Autopista del Sol, Hwy 95D) |
| Rendimiento de referencia | 3.7 km/L |
| Consumo estimado por viaje | ~102.7 L (380 km ÷ 3.7 km/L) |
| Emisión CO₂ estimada por viaje | ~275.2 kg CO₂ (102.7 L × 2.68 kg/L) |
| Emisión CO₂ por km | ~0.724 kg CO₂/km |

### 2.2 Fórmulas de cálculo para el agente

```
Consumo por viaje (L) = Distancia (km) ÷ Rendimiento (km/L)
Emisión CO₂ (kg) = Consumo (L) × 2.68
Emisión CO₂ por km (kg/km) = 2.68 ÷ Rendimiento (km/L)
```

Usando los parámetros SPN:
```
Rendimiento real = SPN 185 (Rendimiento km/L)
Consumo acumulado = SPN 250 (Combustible Consumido L)
Distancia recorrida = SPN 917 (Odómetro km)
Tasa instantánea = SPN 183 (Tasa de combustible L/h)
```

---

## 3. PARÁMETROS SPN QUE IMPACTAN EMISIONES

### 3.1 Parámetros de impacto directo en emisiones

| SPN | Nombre | Unidad | Relación con emisiones |
|-----|--------|--------|----------------------|
| 185 | Rendimiento | km/L | Indicador principal de eficiencia. Menor rendimiento = más litros = más CO₂ por km. |
| 184 | Ahorro de combustible instantáneo | km/L | Permite detectar en tiempo real momentos de ineficiencia. |
| 183 | Tasa de combustible | L/h | Consumo instantáneo. Valores altos sostenidos = emisiones elevadas. |
| 250 | Combustible Consumido | L | Acumulado total. Multiplicado por 2.68 = CO₂ total emitido. |
| 1761 | Nivel Urea (DEF) | % | Sin urea, el sistema SCR no reduce NOx. Impacto directo en cumplimiento NOM-044. |
| 110 | Temperatura Motor | °C | Motor sobrecalentado = combustión ineficiente = más emisiones. |
| 175 | Temperatura Aceite Motor | °C | Aceite degradado por temperatura = mayor fricción = mayor consumo. |

### 3.2 Parámetros de impacto indirecto (conducción)

| SPN | Nombre | Unidad | Relación con emisiones |
|-----|--------|--------|----------------------|
| 91 | Posición Pedal Acelerador | % | Aceleración brusca (>80%) genera picos de consumo y emisiones. |
| 521 | Posición Pedal Freno | % | Frenado brusco frecuente indica conducción ineficiente (aceleración-frenado). |
| 190 | RPM | rpm | RPM fuera del rango óptimo (1200-1600 rpm en crucero) = mayor consumo. |
| 84 | Velocidad km/h | km/h | Velocidad excesiva aumenta resistencia aerodinámica exponencialmente. |
| 513 | Porcentaje Torque | % | Torque alto sostenido = motor trabajando fuerte = más combustible. |
| 523 | Marchas | Marcha | Marcha incorrecta para la velocidad = RPM ineficientes. |
| 520 | Retarder Percent Torque | % | Uso excesivo de retarder puede indicar compensación por frenos deficientes. |
| 96 | Nivel Combustible | % | Monitoreo de consumo total por trayecto. |

### 3.3 Parámetros de contexto ambiental

| SPN | Nombre | Unidad | Relación con emisiones |
|-----|--------|--------|----------------------|
| 171 | Temperatura ambiente | °C | Temperaturas extremas afectan eficiencia del motor y sistema de enfriamiento. |
| 917 | Odómetro | km | Base para calcular emisiones por distancia recorrida. |

---

## 4. REGLAS DE MONITOREO AMBIENTAL

### 4.1 Eficiencia de combustible y CO₂ — Ruta CDMX-Acapulco

| Indicador | Rango eficiente | Alerta moderada | Alerta significativa |
|-----------|----------------|-----------------|---------------------|
| Rendimiento (SPN 185) | ≥ 3.7 km/L | 3.2 – 3.7 km/L | < 3.2 km/L |
| CO₂ por viaje (calculado) | ≤ 275 kg | 275 – 318 kg | > 318 kg |
| CO₂ por km (calculado) | ≤ 0.724 kg/km | 0.724 – 0.838 kg/km | > 0.838 kg/km |
| Tasa de combustible en crucero (SPN 183) | 15 – 30 L/h | 30 – 40 L/h | > 40 L/h |

Reglas:
- Si el rendimiento cae por debajo de 3.2 km/L en la ruta CDMX-Acapulco, se genera alerta ambiental.
- Cada 0.1 km/L de mejora en rendimiento representa una reducción proporcional de CO₂ por viaje.
- El agente debe reportar la tendencia de rendimiento por unidad y por conductor, sin mencionar valores numéricos específicos de ahorro (C-003).

### 4.2 Sistema SCR y Urea — Cumplimiento NOM-044

| Indicador | Rango normal | Alerta preventiva | Alerta crítica |
|-----------|-------------|-------------------|----------------|
| Nivel Urea (SPN 1761) | 30% – 100% | 15% – 30% | < 15% |

Reglas:
- Si el nivel de urea cae por debajo del 15%, el sistema SCR no puede reducir NOx de forma efectiva. Esto pone a la unidad fuera de cumplimiento con NOM-044-SEMARNAT-2017.
- La NOM-044 exige que los vehículos con estándar B tengan alertas luminosas, sonoras y limitación de operación cuando la urea es insuficiente.
- El agente debe generar alerta de cumplimiento ambiental cuando detecte nivel de urea bajo.
- Unidades operando sin urea o con urea de mala calidad deben ser retiradas de servicio hasta corregir.

### 4.3 Patrones de conducción que incrementan emisiones

| Patrón | Parámetros involucrados | Umbral de alerta | Impacto ambiental |
|--------|------------------------|-------------------|-------------------|
| Aceleración brusca | Pedal Acelerador (SPN 91) > 80% frecuente | Más de 10 eventos por hora de viaje | Picos de consumo que incrementan emisiones de CO₂, NOx y PM |
| Frenado tardío | Pedal Freno (SPN 521) > 70% frecuente | Más de 8 eventos por hora de viaje | Energía cinética desperdiciada = combustible quemado sin aprovechamiento |
| RPM excesivas en crucero | RPM (SPN 190) > 1800 rpm a velocidad constante | Sostenido más de 5 minutos | Motor fuera de zona de eficiencia = mayor consumo por km |
| Velocidad excesiva | Velocidad (SPN 84) > 95 km/h sostenido | Más de 15 minutos continuos | Resistencia aerodinámica crece exponencialmente. Cada km/h adicional sobre 90 km/h incrementa el consumo de forma no lineal. |
| Marcha incorrecta | Marchas (SPN 523) baja + Velocidad (SPN 84) alta | RPM > 2000 a velocidad de crucero | Motor trabajando en rango ineficiente |
| Torque al límite sin justificación | Torque (SPN 513) > 90% sin pendiente | Sostenido más de 10 minutos en terreno plano | Posible sobrecarga o problema mecánico que fuerza al motor |

### 4.4 Temperatura de motor y combustión eficiente

| Condición | Parámetros | Impacto ambiental |
|-----------|-----------|-------------------|
| Motor frío operando | Temperatura Motor (SPN 110) < 70°C | Combustión incompleta. Mayores emisiones de HC y CO. El motor debe alcanzar temperatura operativa antes de exigir carga. |
| Motor sobrecalentado | Temperatura Motor (SPN 110) > 115°C | Combustión ineficiente. Mayor consumo. Posible daño al catalizador/SCR. |
| Temperatura óptima | Temperatura Motor (SPN 110) 80°C – 105°C | Zona de máxima eficiencia de combustión y mínimas emisiones. |

---

## 5. ÍNDICE DE HUELLA DE CARBONO POR UNIDAD

### 5.1 Cálculo del índice

Para cada unidad se calcula un índice de huella de carbono basado en los datos de telemetría:

```
Índice CO₂ (kg/km) = 2.68 ÷ Rendimiento_real (km/L)

Donde:
  Rendimiento_real = SPN 185 (promedio del viaje)
  
  O alternativamente:
  Rendimiento_real = Δ Odómetro (SPN 917) ÷ Δ Combustible Consumido (SPN 250)
```

### 5.2 Clasificación ambiental de unidades — Ruta CDMX-Acapulco

| Clasificación | Índice CO₂ (kg/km) | Rendimiento equivalente | Código de color |
|--------------|--------------------|-----------------------|-----------------|
| 🟢 Eco-eficiente | < 0.670 | > 4.0 km/L | Verde |
| 🔵 Eficiente | 0.670 – 0.724 | 3.7 – 4.0 km/L | Azul |
| 🟡 Estándar | 0.724 – 0.838 | 3.2 – 3.7 km/L | Amarillo |
| 🟠 Ineficiente | 0.838 – 0.967 | 2.77 – 3.2 km/L | Naranja |
| 🔴 Crítico | > 0.967 | < 2.77 km/L | Rojo |

### 5.3 Métricas de flota para dashboard

El dashboard debe mostrar (en lenguaje difuso — C-003):
- Distribución de la flota por clasificación ambiental (gráfico de dona)
- Tendencia de huella de carbono promedio de la flota (línea temporal)
- Unidades con mayor oportunidad de mejora ambiental
- Estimación de reducción de CO₂ si las unidades ineficientes alcanzan el estándar
- Conductores con mejor y peor desempeño ambiental

---

## 6. REGLAS PARA EL AGENTE DE INTELIGENCIA AMBIENTAL

### 6.1 Árbol de decisión ambiental

```
EVALUACIÓN AMBIENTAL POR VIAJE:
│
├── 1. Calcular rendimiento real del viaje
│   └── Rendimiento = Δ Odómetro ÷ Δ Combustible
│
├── 2. Calcular CO₂ emitido
│   └── CO₂ = Combustible consumido × 2.68 kg/L
│
├── 3. Clasificar unidad (ver tabla 5.2)
│
├── 4. Identificar causas de ineficiencia:
│   ├── ¿Aceleración brusca? → SPN 91 > 80% frecuente
│   ├── ¿Frenado tardío? → SPN 521 > 70% frecuente
│   ├── ¿RPM excesivas? → SPN 190 > 1800 en crucero
│   ├── ¿Velocidad excesiva? → SPN 84 > 95 km/h sostenido
│   ├── ¿Marcha incorrecta? → SPN 523 baja + velocidad alta
│   ├── ¿Motor sobrecalentado? → SPN 110 > 115°C
│   └── ¿Urea baja? → SPN 1761 < 15%
│
├── 5. Generar recomendación ambiental
│   └── Usar lenguaje difuso (C-003):
│       ✅ "La unidad muestra una oportunidad significativa de reducción de huella de carbono"
│       ✅ "El patrón de conducción contribuye a emisiones superiores al estándar de la ruta"
│       ❌ "La unidad emite 43 kg más de CO₂ que el promedio" (NO usar)
│
└── 6. Registrar en ado-alertas si nivel ≥ MODERADO
```

### 6.2 Alertas ambientales automáticas

| Nivel | Condición | Acción |
|-------|-----------|--------|
| 🟢 Informativo | Rendimiento ≥ 3.7 km/L, urea > 30%, conducción eficiente | Registrar. Sin alerta. |
| 🟡 Moderado | Rendimiento 3.2 – 3.7 km/L o urea 15% – 30% | Alerta al supervisor. Sugerir revisión de estilo de conducción. |
| 🟠 Elevado | Rendimiento < 3.2 km/L o patrones de conducción agresiva recurrentes | Alerta prioritaria. Programar retroalimentación al conductor. Revisar estado mecánico. |
| 🔴 Crítico | Urea < 15% (incumplimiento NOM-044) o rendimiento < 2.77 km/L | Alerta inmediata. Unidad en riesgo de incumplimiento normativo. Retirar de servicio si urea agotada. |

---

## 7. ESTIMACIÓN DE IMPACTO AMBIENTAL DE LA FLOTA

### 7.1 Modelo de cálculo para la ruta CDMX-Acapulco

```
Por viaje sencillo (380 km):
  Consumo base = 380 ÷ 3.7 = ~102.7 L
  CO₂ base = 102.7 × 2.68 = ~275.2 kg

Por viaje redondo (760 km):
  Consumo base = 760 ÷ 3.7 = ~205.4 L
  CO₂ base = 205.4 × 2.68 = ~550.5 kg

Estimación mensual por unidad (asumiendo 1 viaje redondo diario, 26 días):
  Consumo mensual = 205.4 × 26 = ~5,340 L
  CO₂ mensual = 5,340 × 2.68 = ~14,311 kg (~14.3 toneladas)
```

### 7.2 Potencial de reducción

Si una unidad mejora su rendimiento de 3.2 km/L a 3.7 km/L en esta ruta:
```
  Consumo mejorado por viaje = 380 ÷ 3.7 = 102.7 L
  Consumo previo por viaje = 380 ÷ 3.2 = 118.75 L
  Ahorro por viaje = 16.05 L
  CO₂ evitado por viaje = 16.05 × 2.68 = ~43 kg
  CO₂ evitado mensual (52 viajes) = ~2,236 kg (~2.2 toneladas por unidad)
```

> **Nota C-003:** Estos cálculos son para uso interno del sistema. El agente debe reportar al usuario usando lenguaje como: "La unidad presenta una oportunidad relevante de reducción de huella de carbono" o "Se estima un potencial de mejora ambiental significativo al optimizar el estilo de conducción".

---

## 8. CHECKLIST DE CUMPLIMIENTO AMBIENTAL POR UNIDAD

Para cada unidad de la flota, el sistema debe verificar periódicamente:

| # | Verificación | Parámetro SPN | Criterio de cumplimiento |
|---|-------------|---------------|-------------------------|
| 1 | Sistema SCR operativo | Nivel Urea (SPN 1761) > 15% | Urea suficiente para reducción de NOx |
| 2 | Motor en temperatura operativa | Temperatura Motor (SPN 110) 80°C – 105°C | Combustión eficiente |
| 3 | Rendimiento dentro de estándar de ruta | Rendimiento (SPN 185) ≥ 3.7 km/L | Emisiones CO₂ dentro del rango esperado |
| 4 | Sin códigos OBD de emisiones activos | Código OBD relacionado con emisiones | Sin códigos P04xx (sistema de emisiones) |
| 5 | Conducción eficiente | Acelerador (SPN 91) < 80% promedio | Sin patrones de aceleración brusca |
| 6 | RPM en rango óptimo | RPM (SPN 190) 1200 – 1600 en crucero | Motor en zona de eficiencia |
| 7 | Velocidad controlada | Velocidad (SPN 84) ≤ 95 km/h en autopista | Resistencia aerodinámica controlada |
| 8 | Presión de aceite normal | Presión Aceite (SPN 100) 200 – 800 kPa | Motor sin fricción excesiva |

---

## 9. RELACIÓN CON NORMAS AMBIENTALES — RESUMEN EJECUTIVO

| Norma | Qué regula | Parámetros SPN relacionados | Cómo lo monitorea MobilityIA |
|-------|-----------|---------------------------|------------------------------|
| NOM-044-SEMARNAT-2017 | Emisiones de motores diésel nuevos (NOx, PM, CO) | SPN 1761 (Urea/SCR), SPN 110 (Temp Motor), SPN 190 (RPM) | Monitoreo continuo de nivel de urea y estado del sistema SCR. Alerta si urea < 15%. |
| NOM-045-SEMARNAT-2006 | Opacidad de humo en vehículos diésel en circulación | SPN 110 (Temp Motor), SPN 175 (Temp Aceite), SPN 100 (Presión Aceite) | Detección de condiciones que generan combustión incompleta (humo negro): motor frío, aceite degradado, presión baja. |
| Ley General de Cambio Climático | Reducción de GEI — meta 35% para 2030 | SPN 185 (Rendimiento), SPN 250 (Combustible), SPN 917 (Odómetro) | Cálculo de huella de carbono por unidad, por viaje y por flota. Índice CO₂ kg/km. |
| Acuerdo de París / NDC México | Cero emisiones netas 2050, 364-404 MtCO₂e para 2035 | Todos los de eficiencia | Tendencia de reducción de emisiones de la flota. Evidencia auditable de mejora continua. |

---

## 10. NOTAS PARA LA PRESENTACIÓN DEL HACKATHON

- La ruta CDMX → Acapulco es la línea pivote del MVP. Todos los cálculos de referencia usan esta ruta.
- El rendimiento de 3.7 km/L es el estándar de referencia. Unidades por debajo de este valor representan oportunidad de mejora ambiental.
- El factor de 2.68 kg CO₂/L de diésel es el estándar IPCC internacionalmente aceptado.
- El sistema genera evidencia auditable de esfuerzos de reducción de huella de carbono, lo cual posiciona a Mobility ADO como empresa comprometida con la sustentabilidad.
- Los parámetros de conducción (acelerador, freno, RPM, velocidad) son los que mayor impacto tienen en el consumo real vs. el teórico. La capacitación de conductores basada en datos es la palanca de mayor impacto para reducir emisiones.
- El monitoreo de urea (SPN 1761) es crítico para demostrar cumplimiento con NOM-044-SEMARNAT-2017 y la reducción de NOx.
- Todo lo anterior se presenta al jurado usando lenguaje difuso (C-003): "mejora significativa", "reducción notable", "alineación con normatividad vigente", "evidencia de compromiso ambiental".
