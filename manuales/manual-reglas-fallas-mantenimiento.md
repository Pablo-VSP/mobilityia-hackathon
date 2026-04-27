# 🔧 Manual de Reglas de Fallas y Mantenimiento — ADO MobilityIA
## Hackathon AWS Builders League 2026

> **Fuente de datos:** `datos_spn/fault_data_catalog.JSON`
> **C-003:** Sin métricas numéricas específicas — lenguaje difuso en comunicaciones al usuario.
> **C-004:** Datos simulados — seguridad de información corporativa.
> **C-007:** Catálogo de fallas con `severidad_inferencia` para modelo predictivo SageMaker.

---

## Objetivo del manual

Este manual establece las reglas de negocio para la gestión de fallas detectadas en la flota de autobuses. Define:

1. Cómo actuar ante cada falla detectada (mantenimiento correctivo)
2. Cómo anticipar y prevenir esas fallas antes de que ocurran (mantenimiento preventivo)
3. Criterios de priorización basados en severidad inferida y frecuencia histórica

---

## Clasificación de severidad inferida

| Nivel | severidad_inferencia | Significado | Tiempo de respuesta |
|---|---|---|---|
| Baja | `null` o `1` | Falla informativa o de bajo impacto operativo | Próximo servicio programado |
| Media | `2` | Degradación progresiva — riesgo de escalamiento | Esta semana |
| Alta | `3` | Riesgo de seguridad o daño catastrófico a componente crítico | Inmediata |

---

## Fallas de severidad alta (severidad_inferencia = 3)

Estas fallas representan riesgo de seguridad para pasajeros y operadores, o daño catastrófico a componentes mayores del autobús. Requieren intervención inmediata.

---

### FALLA: Engine oil pressure (Presión de aceite del motor)
- **Código:** 100
- **Frecuencia histórica:** 116,188 ocurrencias (la más alta del catálogo)
- **Severidad inferida:** 3 — Alta
- **Sistema afectado:** Motor — lubricación

#### Reglas de mantenimiento correctivo
- Detener la unidad de forma segura en cuanto se confirme la alerta
- No continuar operación bajo ninguna circunstancia — riesgo de daño catastrófico al motor
- Verificar nivel de aceite físicamente en la unidad
- Inspeccionar bomba de aceite, filtro de aceite y conductos de lubricación
- Revisar sensor de presión de aceite (SPN 100) para descartar falso positivo
- Si la presión no se restablece tras verificación, trasladar la unidad a taller con grúa

#### Reglas de mantenimiento preventivo
- Monitorear tendencia de SPN 100 (Presión Aceite Motor) — si muestra descenso gradual sostenido, programar revisión antes de que alcance umbral crítico
- Monitorear SPN 98 (Nivel de Aceite) — un nivel descendente combinado con presión baja indica consumo anormal o fuga
- Monitorear SPN 175 (Temperatura Aceite Motor) — temperatura elevada combinada con presión baja indica degradación del lubricante
- Verificar intervalos de cambio de aceite por odómetro (SPN 917) y horas motor (SPN 247)
- Incluir análisis de aceite en cada servicio programado para detectar contaminación o desgaste metálico
- Revisar historial de fallas del bus — si hay recurrencia de código 100, investigar causa raíz en bomba o cojinetes

#### Señales predictivas clave
| SPN | Variable | Patrón de alerta |
|---|---|---|
| 100 | Presión Aceite Motor | Descenso progresivo entre lecturas consecutivas |
| 98 | Nivel de Aceite | Caída sostenida sin registro de relleno |
| 175 | Temperatura Aceite Motor | Incremento por encima del rango normal |
| 247 | Horas Motor | Acumulado elevado sin servicio de lubricación |

---

### FALLA: Engine cylinder knock sensor (Sensor de detonación de cilindro)
- **Código:** 100
- **Frecuencia histórica:** 116,188 ocurrencias
- **Severidad inferida:** 3 — Alta
- **Sistema afectado:** Motor — combustión interna

#### Reglas de mantenimiento correctivo
- Reducir carga del motor inmediatamente — evitar aceleración brusca
- Registrar condiciones de operación al momento de la alerta (RPM, temperatura, carga)
- Inspeccionar sensor de detonación y cableado asociado
- Verificar calidad de combustible — detonación puede ser causada por combustible de baja calidad
- Revisar sistema de inyección y timing del motor
- Si la detonación persiste, retirar la unidad de servicio para diagnóstico profundo

#### Reglas de mantenimiento preventivo
- Monitorear SPN 110 (Temperatura Motor) — temperatura elevada incrementa riesgo de detonación
- Monitorear SPN 190 (RPM) — operación sostenida en RPM elevadas aumenta estrés en cilindros
- Verificar que el combustible utilizado cumple especificaciones del fabricante
- Revisar sistema de enfriamiento — sobrecalentamiento es precursor de detonación
- Programar inspección de inyectores en cada servicio mayor
- Analizar patrones de conducción — aceleración brusca frecuente (SPN 91 elevado) incrementa riesgo

#### Señales predictivas clave
| SPN | Variable | Patrón de alerta |
|---|---|---|
| 110 | Temperatura Motor | Incremento sostenido fuera de rango |
| 190 | RPM | Operación prolongada en rango alto |
| 91 | Posición Acelerador | Picos frecuentes de aceleración brusca |
| 175 | Temperatura Aceite | Elevación correlacionada con temperatura motor |

---

### FALLA: Battery potential (voltage)-switched (Voltaje de batería)
- **Código:** 158
- **Frecuencia histórica:** 14,242 ocurrencias
- **Severidad inferida:** 3 — Alta
- **Sistema afectado:** Sistema eléctrico — alimentación general

#### Reglas de mantenimiento correctivo
- Verificar voltaje de batería con multímetro — confirmar lectura del sensor SPN 168
- Inspeccionar terminales de batería (corrosión, conexiones flojas)
- Verificar estado del alternador — voltaje bajo puede indicar falla en carga
- Revisar fusibles principales y relés de distribución eléctrica
- Si el voltaje no se recupera, reemplazar batería y/o alternador según diagnóstico
- No operar la unidad con voltaje críticamente bajo — riesgo de falla total de sistemas electrónicos

#### Reglas de mantenimiento preventivo
- Monitorear tendencia de SPN 168 (Voltaje Batería) — descenso gradual indica degradación de batería o alternador
- Incluir prueba de carga de batería en cada servicio programado
- Verificar tensión y estado de banda del alternador
- Inspeccionar cableado eléctrico principal en busca de desgaste o daño por vibración
- Considerar antigüedad de la batería — programar reemplazo preventivo según horas motor acumuladas (SPN 247)
- Revisar consumo eléctrico parasitario cuando la unidad está apagada

#### Señales predictivas clave
| SPN | Variable | Patrón de alerta |
|---|---|---|
| 168 | Voltaje Batería | Descenso progresivo entre arranques |
| 247 | Horas Motor | Acumulado alto sin reemplazo de batería |

---

### FALLA: Brake torque output axle 3 left (Torque de freno eje 3 izquierdo)
- **Código:** 86
- **Frecuencia histórica:** 14,024 ocurrencias
- **Severidad inferida:** 3 — Alta
- **Sistema afectado:** Frenos — seguridad crítica

#### Reglas de mantenimiento correctivo
- Retirar la unidad de servicio inmediatamente — falla de frenos es riesgo de seguridad máximo
- No operar la unidad hasta completar inspección y reparación
- Inspeccionar balatas, discos/tambores, calipers y líneas de freno del eje 3 izquierdo
- Verificar sistema neumático de frenos — presión de aire, válvulas, mangueras
- Revisar sensor de torque de freno y cableado
- Documentar condiciones de la falla para análisis de causa raíz

#### Reglas de mantenimiento preventivo
- Monitorear SPN 1099-1104 (Balatas, 6 posiciones) — desgaste progresivo es el principal indicador
- Monitorear SPN 521 (Posición Pedal Freno) — uso excesivo de freno indica técnica de conducción que acelera desgaste
- Programar inspección visual de componentes de freno en cada servicio
- Verificar espesor de balatas y estado de discos/tambores con medición periódica
- Revisar sistema neumático de frenos — fugas de aire reducen eficiencia de frenado
- Analizar patrones de frenado por conductor — frenado tardío y brusco acelera desgaste

#### Señales predictivas clave
| SPN | Variable | Patrón de alerta |
|---|---|---|
| 1099-1104 | Balatas (6 posiciones) | Porcentaje restante en descenso sostenido |
| 521 | Posición Pedal Freno | Uso frecuente con valores altos |
| 84 | Velocidad | Velocidad elevada combinada con frenado brusco |

---

## Fallas de severidad media (severidad_inferencia = 2)

Estas fallas indican degradación progresiva de componentes. Si no se atienden, pueden escalar a severidad alta. Requieren intervención programada dentro de la semana.

---

### FALLA: Nivel de refrigerante (Coolant level)
- **Código:** 111
- **Frecuencia histórica:** 85 ocurrencias
- **Severidad inferida:** 2 — Media
- **Sistema afectado:** Motor — sistema de enfriamiento

#### Reglas de mantenimiento correctivo
- Verificar nivel de refrigerante físicamente — confirmar lectura del sensor SPN 111
- Inspeccionar radiador, mangueras y conexiones en busca de fugas visibles
- Verificar tapa del radiador — pérdida de presión causa evaporación acelerada
- Revisar bomba de agua — fuga en sello es causa común
- Si hay pérdida de refrigerante sin fuga visible, verificar junta de culata (posible fuga interna)

#### Reglas de mantenimiento preventivo
- Monitorear tendencia de SPN 111 (Nivel Anticongelante) — descenso gradual sin relleno registrado indica fuga
- Monitorear SPN 110 (Temperatura Motor) — temperatura elevada combinada con nivel bajo de refrigerante es señal de alerta crítica
- Incluir inspección visual del sistema de enfriamiento en cada servicio
- Verificar concentración y estado del refrigerante — degradación reduce capacidad de enfriamiento
- Programar reemplazo de mangueras según antigüedad — el envejecimiento causa fisuras
- Revisar historial — si hay recurrencia, investigar causa raíz (radiador, bomba de agua, junta de culata)

#### Señales predictivas clave
| SPN | Variable | Patrón de alerta |
|---|---|---|
| 111 | Nivel Anticongelante | Descenso progresivo entre servicios |
| 110 | Temperatura Motor | Incremento correlacionado con nivel bajo |
| 247 | Horas Motor | Acumulado alto sin servicio de enfriamiento |

#### Riesgo de escalamiento
Si no se atiende, esta falla puede escalar a sobrecalentamiento del motor (daño catastrófico — severidad 3). La combinación de nivel bajo de refrigerante + temperatura motor elevada debe tratarse como emergencia.

---

### FALLA: Turbocharger wastegate drive (Actuador de wastegate del turbocompresor)
- **Código:** 32
- **Frecuencia histórica:** 1,774 ocurrencias
- **Severidad inferida:** 2 — Media
- **Sistema afectado:** Motor — sistema de sobrealimentación (turbo)

#### Reglas de mantenimiento correctivo
- Verificar funcionamiento del actuador de wastegate — puede estar atascado o con respuesta lenta
- Inspeccionar mangueras de vacío/presión del actuador
- Revisar turbocompresor por juego axial o radial excesivo
- Verificar sistema de control electrónico del turbo
- Si el wastegate no regula correctamente, el turbo puede sobrealimentar (daño al motor) o subalimentar (pérdida de potencia)

#### Reglas de mantenimiento preventivo
- Monitorear SPN 131 (Exhaust back pressure) — contrapresión elevada indica obstrucción que afecta al turbo
- Monitorear SPN 110 (Temperatura Motor) — sobrecalentamiento puede dañar componentes del turbo
- Verificar estado del aceite — el turbo depende de lubricación adecuada (SPN 100, SPN 175)
- Incluir inspección del turbocompresor en servicios mayores
- Revisar filtro de aire — restricción de admisión afecta rendimiento del turbo
- Analizar patrones de RPM (SPN 190) — operación prolongada en RPM extremas acelera desgaste del turbo

#### Señales predictivas clave
| SPN | Variable | Patrón de alerta |
|---|---|---|
| 131 | Contrapresión de escape | Incremento sostenido |
| 110 | Temperatura Motor | Elevación fuera de rango |
| 100 | Presión Aceite | Descenso que afecta lubricación del turbo |
| 190 | RPM | Operación prolongada en extremos |

#### Riesgo de escalamiento
Un wastegate defectuoso puede causar sobrealimentación del motor, resultando en daño a pistones, juntas y sistema de escape. Escala a severidad 3 si no se atiende.

---

### FALLA: Exhaust back pressure (Contrapresión de escape)
- **Código:** 131
- **Frecuencia histórica:** 2,727 ocurrencias
- **Severidad inferida:** 2 — Media
- **Sistema afectado:** Escape — sistema de postratamiento (DPF/SCR)

#### Reglas de mantenimiento correctivo
- Verificar estado del filtro de partículas diésel (DPF) — obstrucción es la causa más común
- Inspeccionar sistema SCR y catalizador
- Verificar si hay regeneración pendiente del DPF
- Revisar sensores de presión diferencial del sistema de escape
- Si la contrapresión es excesiva, forzar regeneración del DPF o reemplazar si está saturado

#### Reglas de mantenimiento preventivo
- Monitorear tendencia de SPN 131 — incremento gradual indica acumulación de hollín en DPF
- Monitorear SPN 1761 (Nivel Urea) — nivel bajo de urea afecta sistema SCR y puede incrementar contrapresión
- Verificar calidad del diésel — combustible de baja calidad genera más hollín
- Programar regeneraciones del DPF según horas motor (SPN 247) y kilómetros (SPN 917)
- Revisar sistema de inyección de urea — obstrucción del inyector afecta postratamiento
- Analizar patrones de operación — trayectos cortos a baja carga impiden regeneración natural del DPF

#### Señales predictivas clave
| SPN | Variable | Patrón de alerta |
|---|---|---|
| 131 | Contrapresión de escape | Incremento progresivo entre regeneraciones |
| 1761 | Nivel Urea | Nivel bajo o descendente |
| 110 | Temperatura Motor | Puede elevarse por restricción de escape |
| 247 | Horas Motor | Acumulado alto sin regeneración de DPF |

#### Riesgo de escalamiento
Contrapresión excesiva sostenida puede dañar el turbocompresor, reducir potencia del motor y causar sobrecalentamiento. Además, afecta el cumplimiento de normas de emisiones (NOM-044-SEMARNAT). Escala a severidad 3 si se combina con falla de turbo.

---

### FALLA: Tractor brake slack out of adjustment axle 2 left (Desajuste de freno eje 2 izquierdo)
- **Código:** 37
- **Frecuencia histórica:** 11,929 ocurrencias
- **Severidad inferida:** 2 — Media
- **Sistema afectado:** Frenos — ajuste mecánico

#### Reglas de mantenimiento correctivo
- Verificar ajuste de freno del eje 2 izquierdo — medir recorrido de la cámara de freno
- Inspeccionar ajustador automático de holgura (slack adjuster) — puede estar trabado o dañado
- Verificar estado de balatas y tambor/disco
- Revisar cámara de freno por fugas de aire
- Ajustar o reemplazar slack adjuster según hallazgos

#### Reglas de mantenimiento preventivo
- Monitorear SPN 1099-1104 (Balatas) — desgaste desigual entre posiciones indica desajuste
- Monitorear SPN 521 (Posición Pedal Freno) — esfuerzo de frenado mayor al esperado puede indicar desajuste
- Incluir verificación de ajuste de frenos en cada servicio programado
- Lubricar slack adjusters según intervalos del fabricante
- Revisar historial de fallas de frenos del bus — recurrencia indica problema sistémico
- Verificar alineación de ejes — desalineación causa desgaste desigual de frenos

#### Señales predictivas clave
| SPN | Variable | Patrón de alerta |
|---|---|---|
| 1099-1104 | Balatas | Desgaste desigual entre posiciones del mismo eje |
| 521 | Posición Pedal Freno | Incremento en esfuerzo de frenado |
| 84 | Velocidad | Distancia de frenado mayor a la esperada |

#### Riesgo de escalamiento
Un freno desajustado reduce la capacidad de frenado total del vehículo. Si se combina con desgaste de balatas, escala a severidad 3 (riesgo de seguridad). Alta frecuencia histórica (11,929 ocurrencias) indica que es un problema recurrente que requiere atención sistemática.

---

### FALLA: Engine oil replacement valve (Válvula de reemplazo de aceite del motor)
- **Código:** 86
- **Frecuencia histórica:** 14,024 ocurrencias
- **Severidad inferida:** 2 — Media
- **Sistema afectado:** Motor — sistema de lubricación

#### Reglas de mantenimiento correctivo
- Verificar funcionamiento de la válvula de reemplazo de aceite
- Inspeccionar circuito de lubricación asociado
- Revisar sensor y cableado — descartar falso positivo
- Si la válvula está defectuosa, reemplazar para evitar contaminación del aceite

#### Reglas de mantenimiento preventivo
- Monitorear SPN 100 (Presión Aceite) — presión irregular puede indicar problema en válvula
- Monitorear SPN 98 (Nivel de Aceite) — variaciones inesperadas pueden estar relacionadas
- Incluir inspección de válvula en servicios de cambio de aceite
- Verificar calidad del aceite mediante análisis periódico
- Revisar historial — si hay recurrencia con código 100 (presión de aceite), investigar relación

#### Señales predictivas clave
| SPN | Variable | Patrón de alerta |
|---|---|---|
| 100 | Presión Aceite | Fluctuaciones irregulares |
| 98 | Nivel de Aceite | Variaciones sin registro de relleno |
| 175 | Temperatura Aceite | Elevación por lubricación deficiente |

#### Riesgo de escalamiento
Una válvula de aceite defectuosa puede causar pérdida de presión de lubricación, escalando a daño catastrófico del motor (severidad 3). La alta frecuencia histórica (14,024 ocurrencias) refuerza la necesidad de monitoreo continuo.

---

### FALLA: Brake light relay (Relé de luces de freno)
- **Código:** 100
- **Frecuencia histórica:** 116,188 ocurrencias (compartida con código 100)
- **Severidad inferida:** 2 — Media
- **Sistema afectado:** Sistema eléctrico — señalización

#### Reglas de mantenimiento correctivo
- Verificar funcionamiento de luces de freno — confirmar que encienden al frenar
- Inspeccionar relé de luces de freno — reemplazar si está defectuoso
- Revisar cableado y conectores del circuito de luces de freno
- Verificar fusible asociado
- Confirmar que el sensor de pedal de freno envía señal correcta

#### Reglas de mantenimiento preventivo
- Incluir verificación de luces de freno en inspección diaria pre-viaje
- Programar reemplazo preventivo de relés según antigüedad
- Verificar estado de conectores eléctricos — corrosión es causa común de falla intermitente
- Monitorear SPN 168 (Voltaje Batería) — voltaje bajo puede causar fallas en relés

#### Señales predictivas clave
| SPN | Variable | Patrón de alerta |
|---|---|---|
| 168 | Voltaje Batería | Voltaje bajo afecta relés |
| 521 | Posición Pedal Freno | Señal de freno sin activación de luces |

#### Riesgo de escalamiento
Luces de freno inoperantes son un riesgo de seguridad vial. Aunque el sistema de frenado funcione, los vehículos detrás no reciben señal visual. Puede resultar en incidentes de tránsito.

---

## Fallas de severidad baja (severidad_inferencia = 1 o null)

Estas fallas son informativas o de bajo impacto operativo inmediato. Se atienden en el próximo servicio programado. Sin embargo, su acumulación o recurrencia puede indicar problemas sistémicos.

---

### FALLA: Cruise control set speed (Velocidad de crucero configurada)
- **Código:** 86
- **Frecuencia histórica:** 14,024 ocurrencias
- **Severidad inferida:** 1 — Baja
- **Sistema afectado:** Control de crucero

#### Reglas de mantenimiento correctivo
- Verificar funcionamiento del sistema de cruise control
- Inspeccionar interruptores y controles del volante
- Revisar módulo de control electrónico del cruise
- Verificar sensor de velocidad (SPN 84)

#### Reglas de mantenimiento preventivo
- Monitorear SPN 527/596 (Cruise Control States/Enable) — falla intermitente indica degradación
- Incluir verificación de cruise control en inspecciones periódicas
- Un cruise control funcional contribuye a la eficiencia de combustible — su reparación tiene impacto positivo en consumo

#### Impacto operativo
Bajo impacto en seguridad. Impacto moderado en eficiencia de combustible — sin cruise control, el conductor depende de control manual de velocidad, lo que puede incrementar variabilidad en consumo.

---

### FALLA: Diagnostic output (Salida de diagnóstico)
- **Código:** 37
- **Frecuencia histórica:** 11,929 ocurrencias
- **Severidad inferida:** 1 — Baja
- **Sistema afectado:** Sistema de diagnóstico a bordo

#### Reglas de mantenimiento correctivo
- Verificar puerto de diagnóstico OBD y conectividad
- Revisar módulo de comunicación de diagnóstico
- Confirmar que el sistema reporta correctamente a la plataforma de telemetría

#### Reglas de mantenimiento preventivo
- Verificar conectividad del sistema de diagnóstico en cada servicio
- Un sistema de diagnóstico inoperante impide la detección temprana de otras fallas — su reparación es prioritaria para el programa de mantenimiento preventivo

#### Impacto operativo
Bajo impacto directo en operación. Alto impacto indirecto — sin diagnóstico funcional, el sistema de mantenimiento predictivo pierde visibilidad sobre la unidad.

---

### Fallas sin severidad asignada (severidad_inferencia = null)

Las siguientes fallas no tienen severidad inferida asignada. Se tratan como severidad baja por defecto, pero deben evaluarse caso por caso:

| Código | Descripción | Frecuencia | Acción recomendada |
|---|---|---|---|
| 255 | Reserved / Extension | 2 | Ignorar — código reservado del protocolo |
| 177 | Transmission #1 oil temperature | 3 | Monitorear — baja frecuencia, revisar en servicio programado |
| 31 | Aftertreatment #1 supply air pressure | 57 | Monitorear — relacionado con sistema de postratamiento |
| 31 | Tachometer signal output | 57 | Verificar señal de tacómetro en servicio |
| 31 | Pressure control valve #1 | 57 | Incluir en inspección de sistema neumático |
| 31 | Transmission range position | 57 | Verificar sensor de posición de transmisión |
| 31 | Tire pressure sensor #14 | 57 | Verificar sensor de presión de neumáticos |
| 84 | Road speed | 77 | Verificar sensor de velocidad |
| 84 | Brake torque output axle 2 left | 77 | Monitorear — relacionado con frenos, evaluar si requiere reclasificación |
| 111 | Engine cylinder #22 knock sensor | 85 | Monitorear — sensor de detonación, evaluar tendencia |
| 0 | Request parameter / Reserved | 224 | Ignorar — códigos de protocolo |
| 32 | Tire pressure sensor #15 | 1,774 | Verificar sensor de presión de neumáticos |
| 32 | Aftertreatment #1 purge air pressure | 1,774 | Monitorear — sistema de postratamiento |
| 32 | Transmission splitter position | 1,774 | Verificar en servicio programado |
| 37 | Headlamp low beam left #2 | 11,929 | Verificar iluminación — seguridad vial |
| 37 | Transmission tank air pressure | 11,929 | Monitorear presión de aire de transmisión |
| 37 | Tire temperature sensor #4 | 11,929 | Verificar sensor de temperatura de neumáticos |

> **Regla de negocio:** Si una falla sin severidad asignada se presenta con frecuencia creciente en una unidad específica, debe escalarse a severidad 2 para evaluación.

---

## Reglas de negocio transversales

### Regla 1 — Escalamiento por acumulación
Si una unidad presenta 3 o más fallas activas simultáneamente, independientemente de su severidad individual, el nivel de riesgo general de la unidad se eleva al siguiente nivel:
- 3 fallas de severidad baja → Tratar como severidad media
- 2 fallas de severidad media → Tratar como severidad alta
- Cualquier combinación con 1 falla de severidad alta → Intervención inmediata

### Regla 2 — Escalamiento por recurrencia
Si una misma falla se presenta más de 3 veces en 30 días en la misma unidad, su severidad efectiva se incrementa en 1 nivel, independientemente de la severidad inferida original.

### Regla 3 — Correlación de fallas
Ciertas combinaciones de fallas indican problemas sistémicos mayores:

| Combinación | Diagnóstico probable | Acción |
|---|---|---|
| SPN 100 (presión aceite) + SPN 175 (temp aceite) + SPN 110 (temp motor) | Falla inminente del sistema de lubricación | Intervención inmediata — retirar de servicio |
| SPN 111 (nivel refrigerante) + SPN 110 (temp motor) | Fuga de refrigerante con sobrecalentamiento | Intervención inmediata — riesgo de daño a culata |
| SPN 168 (voltaje batería) + múltiples fallas eléctricas | Falla del sistema de carga (alternador) | Programar esta semana — riesgo de falla total |
| SPN 131 (contrapresión) + SPN 1761 (nivel urea) | Sistema de postratamiento degradado | Programar esta semana — riesgo de incumplimiento NOM-044 |
| Balatas (SPN 1099-1104) múltiples posiciones bajas + código 86 (frenos) | Desgaste generalizado del sistema de frenos | Intervención inmediata — seguridad |

### Regla 4 — Priorización para el taller
Cuando hay múltiples unidades con fallas pendientes, priorizar en este orden:
1. Fallas de severidad 3 (alta) — siempre primero
2. Fallas de frenos (cualquier severidad) — seguridad de pasajeros
3. Fallas de motor con riesgo de daño catastrófico
4. Fallas del sistema eléctrico
5. Fallas de postratamiento/emisiones (cumplimiento regulatorio)
6. Demás fallas por orden de severidad y antigüedad

### Regla 5 — Documentación obligatoria
Toda intervención correctiva o preventiva debe registrarse en la tabla `ado-alertas` de DynamoDB con:
- Número de referencia OT (Orden de Trabajo)
- Bus afectado
- Diagnóstico
- Nivel de riesgo
- Componentes revisados/reemplazados
- Urgencia asignada
- Estado de resolución

---

## Matriz de decisión rápida

| Severidad | Tiempo de respuesta | ¿Puede seguir operando? | ¿Quién decide? |
|---|---|---|---|
| 3 — Alta | Inmediata | No — retirar de servicio | Supervisor de operaciones |
| 2 — Media | Esta semana | Sí, con monitoreo reforzado | Jefe de taller |
| 1 — Baja | Próximo servicio | Sí, operación normal | Técnico de mantenimiento |
| null — Sin clasificar | Evaluar en servicio | Sí, operación normal | Técnico de mantenimiento |

---

## Integración con el modelo predictivo de SageMaker (C-007)

Este manual alimenta directamente al modelo predictivo de mantenimiento:

1. Las fallas con `severidad_inferencia >= 2` son el target del modelo (`evento_14_dias = 1` si ocurre falla de severidad 2 o 3 en los próximos 14 días)
2. Las señales predictivas clave de cada falla se traducen en features del modelo (promedios, máximos, desviaciones estándar y conteos fuera de rango por SPN en ventana de 7 días)
3. Las reglas de correlación de fallas informan la ingeniería de features — combinaciones de SPNs anómalos son features de alto valor predictivo
4. El fallback heurístico en Lambda (`tool-predecir-evento`) implementa una versión simplificada de estas reglas cuando el endpoint de SageMaker no está disponible

---

## Integración con el Agente de Mantenimiento Predictivo (AgentCore)

El agente `ado-agente-mantenimiento` utiliza este manual como referencia a través de la Knowledge Base de Bedrock:

- Cuando detecta señales anómalas, consulta las reglas de mantenimiento preventivo para generar recomendaciones contextualizadas
- Utiliza las señales predictivas clave para priorizar qué SPNs analizar
- Aplica las reglas de escalamiento por acumulación y recurrencia para determinar el nivel de riesgo
- Genera órdenes de trabajo (OT) siguiendo el formato de documentación obligatoria
- Responde siempre en español con lenguaje difuso (C-003), sin mencionar valores numéricos específicos de probabilidad
