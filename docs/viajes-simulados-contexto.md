# 🚌 Viajes Simulados — Contexto de Generación
## Input para Lambda `ado-simulador-telemetria`

---

## Ubicación en S3

```
s3://ado-telemetry-mvp/hackathon-data/simulacion/viajes_consolidados.json
```

---

## Qué contiene

Un JSON con 10 viajes simulados de 5 minutos cada uno, listos para ser reproducidos por la Lambda `ado-simulador-telemetria` como telemetría en tiempo real.

---

## Cómo se generaron

### Fuentes de datos

| Fuente | Uso |
|---|---|
| `posibles_viajes.JSON` | Datos de bus (número económico), operador (clave y nombre), ruta (origen/destino) |
| `data/ruta_ida_2704712.json` | Trazado GPS limpio: México Taxqueña → Acapulco Costera (10,403 puntos) |
| `data/ruta_regreso_2725965.json` | Trazado GPS limpio: Acapulco Costera → México Taxqueña (9,107 puntos) |
| `manuales/manual-reglas-mantenimiento-motor.md` | Rangos normales de cada SPN para generar valores realistas |

### Proceso

1. Se seleccionaron 10 buses diferentes de `posibles_viajes.JSON` (sin repetir número económico)
2. Se detectó si cada viaje es de ida o regreso según el campo `VIAJE_RUTA_ORIGEN`
3. Se asignó un fragmento continuo de 300 puntos GPS del trazado correspondiente (ida o regreso), distribuidos sin solaparse entre sí
4. Se generaron 300 frames (1 por segundo = 5 minutos) con SPNs variados por frame
5. Los valores de SPN se mantienen dentro de rangos normales con suavizado (inercia entre frames)
6. Se inyectaron 2-3 anomalías aleatorias por viaje en ventanas de 20-35 segundos

### Limpieza GPS

Los trazados GPS originales se extrajeron de los Parquets en S3 (`travel_samples_for_10_travels/`) y se filtraron con un bounding box de México (lat 14.5–32.7, lon -118.5 a -86.7) para eliminar coordenadas anómalas (0,0 o fuera de rango).

---

## Estructura del JSON

```json
{
  "viajes": [ ... ],
  "metadata": {
    "total_viajes": 10,
    "fecha": "2021-01-15",
    "hora_aproximada": "14:00-14:10",
    "spns_disponibles": [84, 91, 96, 98, 100, 110, 111, 168, ...],
    "total_spns": 22,
    "generado": "2026-04-28T17:30:00Z"
  }
}
```

### Estructura de cada viaje

```json
{
  "viaje_id": 9000001,
  "autobus": "7321",
  "operador_cve": "1265571",
  "operador_desc": "SANTIAGO GARCIA OSCAR",
  "viaje_ruta": "ACAPULCO COSTERA - MEXICO TAXQUENA",
  "viaje_ruta_origen": "ACAPULCO COSTERA",
  "viaje_ruta_destino": "MEXICO TAXQUENA",
  "fecha": "2021-01-15",
  "hora_inicio": "14:04:00",
  "total_frames": 300,
  "duracion_segundos": 300,
  "frames": [ ... ]
}
```

### Estructura de cada frame

```json
{
  "offset": 0,
  "segundos_desde_inicio": 0,
  "latitud": 17.123456,
  "longitud": -99.654321,
  "spn_valores": {
    "84": {"valor": 82.3, "name": "Velocidad Km/h", "unidad": "km/h"},
    "190": {"valor": 1150.0, "name": "RPM", "unidad": "rpm"},
    "175": {"valor": 102.4, "name": "Temperatura Aceite Motor", "unidad": "°C"}
  }
}
```

**Nota:** No todos los SPNs aparecen en cada frame. Cada SPN tiene una frecuencia de aparición que simula el comportamiento real de lectura por evento (entre 3 y 11 SPNs por frame, promedio ~6).

---

## Los 10 viajes

| # | Bus | Operador | Dirección | Hora inicio |
|---|---|---|---|---|
| 1 | 7301 | SAMUEL CARTEÑO BAUTISTA | IDA (Méx → Aca) | 14:09 |
| 2 | 7313 | PEREZ LAGUNAS JOSE MANUEL | IDA (Méx → Aca) | 14:07 |
| 3 | 7303 | ISAC JUAREZ GALINDO | IDA (Méx → Aca) | 14:10 |
| 4 | 7317 | ARMAS AVALOS VICTOR | IDA (Méx → Aca) | 14:06 |
| 5 | 7321 | SANTIAGO GARCIA OSCAR | REGRESO (Aca → Méx) | 14:04 |
| 6 | 7312 | CARLOS MENDOZA SALAZAR | REGRESO (Aca → Méx) | 14:06 |
| 7 | 7302 | GARCIA QUIROZ PEDRO | REGRESO (Aca → Méx) | 14:04 |
| 8 | 7324 | REY ALBINO GOMEZ WENCES | REGRESO (Aca → Méx) | 14:01 |
| 9 | 7315 | RAMIRO SANCHEZ CABELLO | REGRESO (Aca → Méx) | 14:10 |
| 10 | 7327 | CARLOS ALBERTO PEREZ LAGUNAS | REGRESO (Aca → Méx) | 14:05 |

---

## SPNs incluidos (22 total)

### Conducción y combustible (Agente Combustible)

| SPN | Nombre | Unidad | Rango normal generado |
|---|---|---|---|
| 84 | Velocidad | km/h | 70–90 |
| 190 | RPM | rpm | 900–1400 |
| 91 | Posición Pedal Acelerador | % | 25–55 |
| 521 | Posición Pedal Freno | % | 0–5 |
| 183 | Tasa de combustible | L/h | 15–35 |
| 185 | Rendimiento | km/L | 3.0–4.5 |
| 96 | Nivel Combustible | % | 60–85 (decrece gradualmente) |
| 513 | Porcentaje Torque | % | 25–55 |

### Mantenimiento (Agente Mantenimiento)

| SPN | Nombre | Unidad | Rango normal generado |
|---|---|---|---|
| 110 | Temperatura Motor | °C | 85–98 |
| 175 | Temperatura Aceite Motor | °C | 90–110 |
| 100 | Presión Aceite Motor | kPa | 300–550 |
| 98 | Nivel de aceite | % | 70–95 |
| 111 | Nivel de anticongelante | % | 80–100 |
| 168 | Voltaje Batería | V | 13.2–14.2 |
| 917 | Odómetro | km | acumulador (~520,000+) |
| 1761 | Nivel Urea | % | 65–80 |

### Balatas

| SPN | Nombre | Unidad | Rango normal generado |
|---|---|---|---|
| 1099 | Balata delantero izquierdo | % | 55–70 |
| 1100 | Balata delantero derecho | % | 55–70 |
| 1101 | Balata trasero izquierdo 1 | % | 50–65 |
| 1102 | Balata trasero derecho 1 | % | 50–65 |
| 1103 | Balata trasero izquierdo 2 | % | 50–65 |
| 1104 | Balata trasero derecho 2 | % | 50–65 |

---

## Anomalías inyectadas

Cada viaje tiene 2-3 anomalías aleatorias de los siguientes tipos:

| Tipo | SPNs afectados | Valores fuera de rango |
|---|---|---|
| Conducción agresiva | 91, 183, 185, 513 | Acelerador >82%, Tasa >58 L/h, Rendimiento <2.0 km/L |
| Riesgo mecánico | 110, 175, 100, 168 | Temp Motor >122°C, Temp Aceite >130°C, Presión <150 kPa, Voltaje <12V |
| Velocidad excesiva | 84, 190, 91, 183, 185 | Velocidad >122 km/h, RPM >2500, Rendimiento <2.1 km/L |
| Frenado brusco | 521, 84, 190 | Freno >55%, Velocidad cae a <50 km/h, RPM baja |
| Balatas desgastadas | 1099-1102 | Valores <20% (umbral preventivo del manual) |

Las anomalías se posicionan en ventanas de 20-35 segundos, sin solaparse entre sí dentro del mismo viaje. Los valores transicionan gradualmente (suavizado con inercia) para simular un comportamiento realista.

---

## Cómo lo consume la Lambda

La Lambda `ado-simulador-telemetria`:
1. Lee este JSON de S3 (cachea en memoria)
2. Usa `time.time()` para calcular qué frame le toca a cada bus (stateless)
3. Aplica desfase entre buses (variable `DESFASE_PCT`)
4. Escribe el estado de cada bus en DynamoDB (`ado-telemetria-live`)
5. Valida cada SPN contra el catálogo `motor_spn.json` y marca `fuera_de_rango` si aplica
6. Clasifica el estado de consumo: `EFICIENTE`, `ALERTA_MODERADA`, `ALERTA_SIGNIFICATIVA`

Los viajes se reproducen en loop infinito — al terminar los 300 frames, reinician.

---

## Consideraciones

- **C-004:** Todos los datos son simulados — no son datos reales de la flota ADO
- **C-008:** La fecha (15 enero 2021) corresponde al periodo reservado para simulación en tiempo real
- Los fragmentos GPS no se solapan entre viajes — cada bus aparece en una posición diferente del mapa
- El archivo pesa ~1.5 MB (10 viajes × 300 frames × ~22 SPNs)
