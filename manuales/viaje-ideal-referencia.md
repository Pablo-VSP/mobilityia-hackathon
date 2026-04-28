# 🚌 Viajes Ideales de Referencia — Eficiencia de Combustible
## ADO MobilityIA — Ruta CDMX Taxqueña ↔ Acapulco Costera

> Este documento define los parámetros de conducción eficiente por tramo para las dos rutas principales.
> El agente de combustible compara los valores en tiempo real del conductor contra estos ideales para generar recomendaciones específicas de mejora.
> **C-003:** Las recomendaciones al usuario usan lenguaje difuso, sin valores numéricos específicos de ahorro.
> **C-004:** Los valores de referencia son para uso interno del sistema.

---

## Principio de conducción eficiente

La conducción eficiente en autobuses de pasajeros se basa en:
1. Mantener RPM en la zona de eficiencia del motor (1200-1600 rpm en crucero)
2. Uso consistente del cruise control en tramos de autopista
3. Aceleración progresiva (evitar picos de acelerador >70%)
4. Anticipación al frenado (evitar frenado brusco >50%)
5. Uso adecuado del retarder en descensos (preservar frenos de servicio)
6. Velocidad controlada (resistencia aerodinámica crece exponencialmente sobre 90 km/h)

---

## RUTA 1: MEXICO TAXQUEÑA → ACAPULCO COSTERA (~380 km, ~5 horas)

### Tramo 1 — Salida urbana: Taxqueña → Tlalpan (0-15 km, ~30 min)
**Características:** Tráfico urbano, semáforos, velocidad variable, arranques frecuentes.

| SPN | Parámetro | Valor ideal | Rango aceptable | Alerta si... |
|---|---|---|---|---|
| 84 | Velocidad | 30-50 km/h | 20-60 km/h | >60 km/h en zona urbana |
| 190 | RPM | 1000-1400 rpm | 800-1600 rpm | >1800 rpm sostenido |
| 91 | Acelerador | 25-40% | 15-50% | >70% frecuente (aceleración brusca) |
| 521 | Freno | 10-25% | 5-40% | >60% frecuente (frenado tardío) |
| 183 | Tasa combustible | 15-25 L/h | 10-35 L/h | >40 L/h sostenido |
| 185 | Rendimiento | 2.5-3.5 km/L | 2.0-4.0 km/L | <2.0 km/L |
| 513 | Torque | 30-50% | 20-60% | >80% sin justificación |
| 523 | Marcha | 4-8 | 3-10 | Permanencia en marchas bajas a velocidad media |

**Recomendaciones para este tramo:**
- Anticipar semáforos y reducir velocidad gradualmente
- Evitar aceleraciones bruscas al arrancar — usar acelerador progresivo
- Mantener distancia de seguimiento para evitar frenados de emergencia

### Tramo 2 — Subida a Cuernavaca: Tlalpan → Tres Marías → Cuernavaca (15-80 km, ~50 min)
**Características:** Pendiente ascendente pronunciada, curvas, altitud creciente (2,200m → 2,800m → 1,500m).

| SPN | Parámetro | Valor ideal | Rango aceptable | Alerta si... |
|---|---|---|---|---|
| 84 | Velocidad | 60-80 km/h | 50-90 km/h | >90 km/h en curvas |
| 190 | RPM | 1400-1800 rpm | 1200-2000 rpm | >2200 rpm sostenido (no cambia marcha) |
| 91 | Acelerador | 40-60% | 30-70% | >80% sostenido (motor forzado) |
| 521 | Freno | 5-15% | 0-25% | >40% frecuente en descenso (usar retarder) |
| 183 | Tasa combustible | 25-40 L/h | 20-50 L/h | >55 L/h |
| 185 | Rendimiento | 2.0-3.0 km/L | 1.5-3.5 km/L | <1.5 km/L |
| 513 | Torque | 50-75% | 40-85% | >90% sostenido sin pendiente |
| 520 | Retarder | 0 a -30% | 0 a -50% | No usar retarder en subida |

**Recomendaciones para este tramo:**
- En subida: mantener marcha que permita RPM en zona de torque óptimo
- En bajada hacia Cuernavaca: usar retarder como freno principal, preservar balatas
- No forzar el motor en pendiente — mejor reducir marcha que pisar acelerador a fondo

### Tramo 3 — Autopista Cuernavaca → Iguala (80-200 km, ~1.5 horas)
**Características:** Autopista plana/ondulada, velocidad de crucero, tramo más eficiente.

| SPN | Parámetro | Valor ideal | Rango aceptable | Alerta si... |
|---|---|---|---|---|
| 84 | Velocidad | 85-95 km/h | 80-100 km/h | >100 km/h (resistencia aerodinámica) |
| 190 | RPM | 1200-1500 rpm | 1100-1600 rpm | >1800 rpm en crucero (marcha incorrecta) |
| 91 | Acelerador | 25-35% | 20-45% | >60% frecuente (conducción agresiva) |
| 521 | Freno | 0-5% | 0-15% | >30% frecuente (no anticipa) |
| 183 | Tasa combustible | 18-28 L/h | 15-35 L/h | >40 L/h |
| 185 | Rendimiento | 3.5-4.5 km/L | 3.0-5.0 km/L | <3.0 km/L |
| 527 | Cruise control | Activo (5-6) | Activo | Inactivo en tramo plano (oportunidad perdida) |
| 596 | Cruise enable | 1 | 1 | 0 (cruise deshabilitado) |

**Recomendaciones para este tramo:**
- Activar cruise control — es el tramo donde más impacta en eficiencia
- Mantener velocidad constante entre 85-95 km/h
- Evitar aceleraciones para rebasar — planificar adelantamientos
- RPM ideal en crucero: 1200-1400 rpm en marcha más alta

### Tramo 4 — Zona montañosa: Iguala → Chilpancingo (200-300 km, ~1.5 horas)
**Características:** Curvas pronunciadas, pendientes variables, zona de mayor riesgo de consumo excesivo.

| SPN | Parámetro | Valor ideal | Rango aceptable | Alerta si... |
|---|---|---|---|---|
| 84 | Velocidad | 60-80 km/h | 50-90 km/h | >90 km/h en curvas |
| 190 | RPM | 1300-1700 rpm | 1100-1900 rpm | >2200 rpm |
| 91 | Acelerador | 35-55% | 25-65% | >75% frecuente |
| 521 | Freno | 10-20% | 5-30% | >50% frecuente (usar retarder) |
| 183 | Tasa combustible | 22-35 L/h | 18-45 L/h | >50 L/h |
| 185 | Rendimiento | 2.5-3.5 km/L | 2.0-4.0 km/L | <2.0 km/L |
| 520 | Retarder | -10 a -40% | 0 a -60% | No usar en descensos (desgasta frenos) |

**Recomendaciones para este tramo:**
- Alternar retarder y freno de servicio en descensos
- Anticipar curvas — reducir velocidad antes, no durante la curva
- En subidas: no forzar el motor, reducir marcha a tiempo

### Tramo 5 — Bajada a Acapulco: Chilpancingo → Acapulco (300-380 km, ~1 hora)
**Características:** Descenso prolongado hacia la costa, temperatura ambiente sube, motor puede sobrecalentarse.

| SPN | Parámetro | Valor ideal | Rango aceptable | Alerta si... |
|---|---|---|---|---|
| 84 | Velocidad | 70-90 km/h | 60-95 km/h | >95 km/h en descenso |
| 190 | RPM | 1200-1600 rpm | 1000-1800 rpm | >2000 rpm |
| 91 | Acelerador | 15-30% | 10-40% | >50% en descenso (innecesario) |
| 521 | Freno | 5-15% | 0-25% | >40% sostenido (usar retarder) |
| 520 | Retarder | -20 a -50% | -10 a -70% | 0% en descenso largo (no lo usa) |
| 110 | Temp motor | 85-100°C | 80-110°C | >115°C (sobrecalentamiento por descenso) |
| 183 | Tasa combustible | 10-20 L/h | 8-25 L/h | >30 L/h en descenso |
| 185 | Rendimiento | 4.0-6.0 km/L | 3.5-7.0 km/L | <3.0 km/L en descenso |

**Recomendaciones para este tramo:**
- Usar retarder como freno principal en el descenso prolongado
- Monitorear temperatura del motor — el descenso con carga genera calor
- Aprovechar la gravedad — mínimo uso de acelerador
- Si la temperatura sube, reducir velocidad y aumentar ventilación

---

## RUTA 2: ACAPULCO COSTERA → MEXICO TAXQUEÑA (~380 km, ~5 horas)

Los tramos son los mismos pero en orden inverso y con características de pendiente opuestas:

### Tramo 1 — Subida desde Acapulco: Acapulco → Chilpancingo (0-80 km, ~1 hora)
- **Pendiente ascendente** — mayor consumo, RPM más alto, torque alto
- Valores ideales similares al Tramo 2 de la Ruta 1 (subida)
- Acelerador: 40-60%, RPM: 1400-1800, Rendimiento: 2.0-3.0 km/L

### Tramo 2 — Zona montañosa: Chilpancingo → Iguala (80-180 km, ~1.5 horas)
- Similar al Tramo 4 de la Ruta 1
- Curvas, pendientes variables, retarder en descensos

### Tramo 3 — Autopista Iguala → Cuernavaca (180-300 km, ~1.5 horas)
- **Tramo más eficiente** — crucero, cruise control activo
- Valores ideales del Tramo 3 de la Ruta 1
- Rendimiento ideal: 3.5-4.5 km/L

### Tramo 4 — Subida y bajada Cuernavaca → Tres Marías → CDMX (300-365 km, ~50 min)
- Subida pronunciada a Tres Marías (1,500m → 2,800m) — alto consumo
- Bajada a CDMX (2,800m → 2,200m) — usar retarder
- RPM: 1400-1800 en subida, rendimiento: 1.5-2.5 km/L

### Tramo 5 — Entrada urbana: Tlalpan → Taxqueña (365-380 km, ~30 min)
- Tráfico urbano, velocidad baja, arranques frecuentes
- Valores ideales del Tramo 1 de la Ruta 1

---

## Resumen de valores ideales globales por ruta

### Promedios esperados para un viaje eficiente completo

| Parámetro | CDMX → Acapulco | Acapulco → CDMX |
|---|---|---|
| Rendimiento promedio (SPN 185) | 3.2-3.8 km/L | 3.0-3.6 km/L |
| Tasa combustible promedio (SPN 183) | 22-30 L/h | 24-32 L/h |
| RPM promedio (SPN 190) | 1300-1500 rpm | 1350-1550 rpm |
| Velocidad promedio (SPN 84) | 70-85 km/h | 68-83 km/h |
| % tiempo con cruise control | >40% del viaje | >35% del viaje |
| % aceleración brusca (SPN 91 >70%) | <5% del viaje | <5% del viaje |
| % frenado brusco (SPN 521 >50%) | <3% del viaje | <3% del viaje |

> **Nota C-003:** Estos valores son de referencia interna. El agente debe comunicar al usuario usando lenguaje como: "El conductor muestra un patrón de aceleración más agresivo que el estándar de la ruta" o "Se detecta una oportunidad de mejora en el uso del cruise control".

---

## Reglas para el Agente de Combustible

### Cómo usar este documento

1. **Identificar el tramo actual** del bus usando las coordenadas GPS (latitud/longitud)
2. **Comparar los SPNs actuales** contra los valores ideales del tramo
3. **Generar recomendación específica** si hay desviación significativa
4. **Priorizar recomendaciones** por impacto en eficiencia:
   - Velocidad excesiva (mayor impacto en consumo)
   - RPM fuera de rango (segundo mayor impacto)
   - Aceleración/frenado brusco (tercer impacto)
   - Cruise control inactivo en autopista (cuarto impacto)

### Ejemplos de recomendaciones (lenguaje difuso — C-003)

**Velocidad excesiva:**
> "El autobús {autobus} en la ruta {ruta} muestra una velocidad superior al patrón eficiente para este tramo de autopista. Reducir la velocidad en tramos de crucero contribuye significativamente a la eficiencia de combustible."

**Aceleración brusca:**
> "Se detecta un patrón de aceleración más agresivo que el estándar para el conductor {operador_desc}. Una aceleración más progresiva en los arranques puede mejorar notablemente el rendimiento del viaje."

**Cruise control inactivo:**
> "El autobús {autobus} no está utilizando el cruise control en un tramo de autopista plana. Activar el cruise control en estos tramos es una de las medidas de mayor impacto para mantener un consumo eficiente."

**RPM elevadas:**
> "Las RPM del autobús {autobus} se mantienen por encima del rango óptimo de crucero. Verificar que la transmisión esté en la marcha más alta posible para la velocidad actual."

**Frenado brusco frecuente:**
> "Se detecta un patrón de frenado tardío en el autobús {autobus}. Anticipar las reducciones de velocidad permite un frenado más suave y reduce el desgaste de balatas además de mejorar la eficiencia."

**Retarder no utilizado en descenso:**
> "El autobús {autobus} está en un tramo de descenso sin uso del retarder. Utilizar el retarder como freno principal en descensos prolongados preserva las balatas y mejora la seguridad."
