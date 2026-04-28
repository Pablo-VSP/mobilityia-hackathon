# ⚡ Plan de Funciones Lambda — ADO MobilityIA MVP
## Hackathon AWS Builders League 2026

> Documento de planeación técnica para todas las funciones Lambda del proyecto.
> **C-004:** Todos los datos son simulados. **C-001:** Solo lo necesario para la demo.

---

## Fuentes de datos reales (carpeta `models/`)

El proyecto cuenta con 3 fuentes de datos en S3 cuya estructura define toda la lógica de las Lambdas:

### Fuente 1 — `telemetry-data` (Telemetría por evento SPN)

Cada registro es **una lectura de un sensor específico** (SPN) en un momento dado. Para reconstruir el estado completo de un bus en un instante, hay que agrupar múltiples registros por `autobus` + `evento_fecha_hora`.

| Campo | Tipo | Descripción |
|---|---|---|
| `viaje_id` | bigint | ID del viaje |
| `autobus` | bigint | Número económico del autobús |
| `operador_cve` | string | Clave del operador/conductor |
| `operador_desc` | string | Nombre del operador/conductor |
| `evento_fecha` | date | Fecha del evento |
| `evento_fecha_hora` | timestamp | Timestamp exacto de la lectura |
| `evento_spn` | bigint | **SPN (Suspect Parameter Number)** — ID de la variable leída |
| `evento_descripcion` | string | Descripción de la variable (ej: "Velocidad del vehículo") |
| `evento_valor` | double | Valor numérico de la lectura |
| `evento_latitud` | double | Coordenada GPS |
| `evento_longitud` | double | Coordenada GPS |
| `viaje_ruta` | string | Nombre/código de la ruta |
| `viaje_ruta_origen` | string | Ciudad origen |
| `viaje_ruta_destino` | string | Ciudad destino |
| `evento_protocolo` | string | Protocolo de comunicación |
| `evento_firmware` | string | Versión de firmware del dispositivo |
| `evento_version` | bigint | Versión del evento |

> **Implicación clave:** Un "snapshot" de un bus requiere N registros (uno por cada SPN). La Lambda simulador debe agrupar por `autobus` + ventana temporal y pivotar los SPNs a columnas para escribir un estado consolidado en DynamoDB.

### Fuente 2 — `motor_spn` (Catálogo de variables SPN)

Catálogo maestro que define cada variable de motor, combustible, odómetro, presión, etc. Es la **tabla de referencia** para interpretar los `evento_spn` de la telemetría.

| Campo | Tipo | Descripción |
|---|---|---|
| `id` | bigint | **SPN ID** — se cruza con `evento_spn` de telemetry-data |
| `name` | string | Nombre legible de la variable (ej: "Engine Oil Pressure") |
| `unidad` | string | Unidad de medida (ej: "kPa", "°C", "km/h", "L/h") |
| `minimo` | double | Valor mínimo esperado (rango normal) |
| `maximo` | double | Valor máximo esperado (rango normal) |
| `tipo` | string | Clasificación del SPN |
| `delta` | double | Delta de variación esperada |
| `variable_tipo` | string | Tipo de variable (motor, combustible, frenos, etc.) |

> **Implicación clave:** Los umbrales de alerta ya están definidos aquí (`minimo`, `maximo`). Las Lambdas de análisis deben consultar este catálogo para determinar si un valor está fuera de rango, en lugar de usar umbrales hardcodeados.

### Fuente 3 — `data_fault` (Fallas y códigos de diagnóstico)

Historial de fallas/códigos de diagnóstico con contexto operativo rico: región, marca, modelo, zona, severidad.

| Campo | Tipo | Descripción |
|---|---|---|
| `type` | string | Tipo de falla |
| `id` | string | ID único del evento de falla |
| `fecha_hora` | timestamp | Timestamp de la falla |
| `autobus` | string | Número del autobús |
| `region` | string | Región operativa |
| `marca_comercial` | string | Marca comercial del bus |
| `zona` | string | Zona geográfica |
| `modelo` | string | Modelo del bus |
| `submodelo` | string | Submodelo |
| `servicio` | string | Tipo de servicio (económico, ejecutivo, lujo) |
| `anio` | bigint | Año del bus |
| `conexion` | string | Tipo de conexión del dispositivo |
| `evento_latitud` | double | Coordenada GPS |
| `evento_longitud` | double | Coordenada GPS |
| `operador_cve` | bigint | Clave del operador |
| `codigo` | string | **Código de falla** (equivalente a código OBD/DTC) |
| `tipolectura` | string | Tipo de lectura |
| `contador` | string | Contador de ocurrencias |
| `fecha_hora_fin` | timestamp | Fin del evento de falla |
| `protocolo` | string | Protocolo de comunicación |
| `firmware` | string | Versión de firmware |
| `severidad` | bigint | **Nivel de severidad numérico** |
| `source` | string | Fuente del dato |
| `descripcion` | string | Descripción de la falla |

> **Implicación clave:** Las fallas ya tienen `severidad`, `modelo`, `marca_comercial`, `zona` y `region`. Esto permite al Agente de Mantenimiento buscar patrones por modelo/marca específico, no solo por código de falla.

---

## Cambios fundamentales respecto al diseño original

| Aspecto | Diseño original | Diseño adaptado a datos reales |
|---|---|---|
| Telemetría | 1 registro plano por bus con todos los campos | 1 registro por SPN por lectura — hay que pivotar |
| IDs de bus | `BUS-SIM-001` | `autobus` (bigint — número económico real simulado) |
| IDs de conductor | `COND-SIM-001` | `operador_cve` + `operador_desc` |
| Rutas | `RUTA-MEX-PUE` | `viaje_ruta` + `viaje_ruta_origen` + `viaje_ruta_destino` |
| Variables de motor | Campos fijos (rpm, temperatura, etc.) | SPNs dinámicos — el catálogo `motor_spn` define qué es cada uno |
| Umbrales | Hardcodeados por ruta | Definidos en `motor_spn.minimo` / `motor_spn.maximo` |
| Fallas | Código OBD simple | `codigo` + `severidad` + `modelo` + `marca_comercial` + `zona` |
| Viajes | No existía concepto | `viaje_id` agrupa toda la telemetría de un trayecto |

---

## Resumen ejecutivo de Lambdas

El MVP requiere **9 funciones Lambda** organizadas en 4 grupos:

| Grupo | Funciones | Día |
|---|---|---|
| 🟠 Simulador de ingesta | 1 Lambda | Día 1 |
| 🔥 Tools del Agente Combustible | 3 Lambdas | Día 2 |
| 🔧 Tools del Agente Mantenimiento | 4 Lambdas | Día 3 |
| 📊 Dashboard API | 1 Lambda | Día 4 |

---

## Convenciones generales

```yaml
Runtime:          Python 3.12
Región:           us-east-1
Naming:           ado-{función}
Layers compartidos:
  - ado-common-layer  # boto3 actualizado, utilidades compartidas, catálogo SPN
Formato de logs:  JSON estructurado (CloudWatch)
Variables de entorno comunes:
  - DYNAMODB_TABLE_TELEMETRIA: ado-telemetria-live
  - DYNAMODB_TABLE_ALERTAS: ado-alertas
  - S3_BUCKET: ado-telemetry-mvp
  - ENVIRONMENT: mvp
```

### Estructura de código

```
lambda-functions/
├── layers/
│   └── ado-common/
│       └── python/
│           └── ado_common/
│               ├── __init__.py
│               ├── dynamo_utils.py       # Helpers DynamoDB
│               ├── s3_utils.py           # Helpers S3
│               ├── spn_catalog.py        # Carga y consulta del catálogo motor_spn
│               ├── telemetry_pivot.py    # Pivotea registros SPN → estado consolidado
│               ├── constants.py          # SPNs clave, mapeos
│               └── response.py           # Formato estándar de respuesta
├── ado-simulador-telemetria/
├── tool-consultar-telemetria/
├── tool-calcular-desviacion/
├── tool-listar-buses-activos/
├── tool-consultar-obd/
├── tool-predecir-evento/
├── tool-buscar-patrones-historicos/
├── tool-generar-recomendacion/
└── ado-dashboard-api/
```

---

## Catálogo SPN real — 36 variables confirmadas

El catálogo `motor_spn` contiene **36 variables** organizadas en dos tipos:

- **`EDA`** (26 variables) — Lecturas en tiempo real, muestreo continuo durante el viaje
- **`inicio_fin`** (10 variables) — Acumuladores que se leen al inicio y fin de viaje (odómetro, combustible consumido, desgaste de balatas, horas motor)

### SPNs tipo `EDA` — Tiempo real

| SPN ID | Nombre | Unidad | Mínimo | Máximo | Delta | Uso en MVP |
|---|---|---|---|---|---|---|
| **84** | Velocidad Km/h | km/h | 0 | 120 | 12 | 🔥 Combustible — velocidad excesiva |
| **190** | RPM | rpm | 0 | 3000 | 360 | 🔥 Combustible — RPM fuera de rango |
| **91** | Posicion Pedal Acelerador | % | 0 | 100 | 80 | 🔥 Combustible — aceleración brusca |
| **521** | Posicion Pedal Freno | % | 0 | 100 | 30 | 🔥 Combustible — frenado tardío |
| **183** | Tasa de combustible | L/h | 0 | 100 | 45 | 🔥 Combustible — consumo instantáneo |
| **185** | Rendimiento | km/L | 0 | 50 | 0 | 🔥 Combustible — eficiencia directa |
| **184** | Ahorro de combustible instantáneo | km/L | 0 | 50 | 31 | 🔥 Combustible — eficiencia instantánea |
| **96** | Nivel Combustible | % | 0 | 120 | 8 | 🔥 Combustible — nivel de tanque |
| **110** | Temperatura Motor | °C | 0 | 150 | 3 | 🔧 Mantenimiento — sobretemperatura |
| **175** | Temperatura Aceite Motor | °C | 0 | 150 | 2 | 🔧 Mantenimiento — aceite sobrecalentado |
| **100** | Presion Aceite Motor | kPa | 0 | 1000 | 100 | 🔧 Mantenimiento — presión baja |
| **98** | Nivel de aceite | % | 0 | 110 | 22 | 🔧 Mantenimiento — nivel bajo |
| **10098** | Nivel de aceite litros | L | -6.75 | 0 | 3 | 🔧 Mantenimiento — nivel en litros |
| **111** | Nivel de anticongelante | % | 0 | 110 | 95 | 🔧 Mantenimiento — refrigeración |
| **171** | Temperatura ambiente | °C | -10 | 75 | 0.5 | 🔧 Contexto ambiental |
| **168** | Voltaje Bateria | V | 0 | 36 | 0.5 | 🔧 Mantenimiento — sistema eléctrico |
| **20000** | Voltaje bateria sin alternador | V | 0 | 36 | 4 | 🔧 Mantenimiento — batería |
| **20001** | Voltaje bateria minimo historico | V | 0 | 36 | 10 | 🔧 Mantenimiento — batería |
| **513** | Porcentaje Torque | % | 0 | 100 | 75 | 🔥🔧 Ambos — esfuerzo del motor |
| **520** | Retarder Percent Torque | % | -125 | 125 | 90 | 🔧 Mantenimiento — retardador |
| **523** | Marchas | Marcha | -3 | 16 | 5 | 🔥 Combustible — patrón de cambios |
| **527** | Cruise Control States | bit | 0 | 6 | 6 | 🔥 Combustible — uso de crucero |
| **596** | Cruise Control Enable Switch | bit | 0 | 1 | 1 | 🔥 Combustible — crucero habilitado |
| **597** | Brake Switch | bit | 0 | 1 | 1 | 🔥 Combustible — frenado |
| **598** | Clutch Switch | bit | 0 | 1 | 1 | 🔥 Combustible — embrague |
| **70** | Interruptor freno estacionamiento | bit | 0 | 1 | 1 | Informativo |
| **1624** | Velocidad tacografo | km/h | 0 | 120 | 10 | Redundante con SPN 84 |
| **1761** | Nivel Urea | % | 0 | 100 | 2 | 🔧 Mantenimiento — emisiones |

### SPNs tipo `inicio_fin` — Acumuladores por viaje

| SPN ID | Nombre | Unidad | Mínimo | Máximo | Uso en MVP |
|---|---|---|---|---|---|
| **917** | Odometro | km | 0 | 691,207,984 | 🔧 Mantenimiento — km desde último servicio |
| **250** | Combustible Consumido | L | 1 | 4,211,081 | 🔥 Combustible — consumo acumulado |
| **247** | Horas Motor | h | 1 | 214,748,364 | 🔧 Mantenimiento — horas de operación |
| **1099** | % Restante balata, delantero izquierdo | % | 0 | 100 | 🔧 Mantenimiento — desgaste frenos |
| **1100** | % Restante balata, delantero derecho | % | 0 | 100 | 🔧 Mantenimiento — desgaste frenos |
| **1101** | % Restante balata, trasero izquierdo 1 | % | 0 | 100 | 🔧 Mantenimiento — desgaste frenos |
| **1102** | % Restante balata, trasero derecho 1 | % | 0 | 100 | 🔧 Mantenimiento — desgaste frenos |
| **1103** | % Restante balata, trasero izquierdo 2 | % | 0 | 100 | 🔧 Mantenimiento — desgaste frenos |
| **1104** | % Restante balata, trasero derecho 2 | % | 0 | 100 | 🔧 Mantenimiento — desgaste frenos |

### Hallazgos importantes del catálogo

1. **`variable_tipo` solo tiene 2 valores:** `EDA` e `inicio_fin` — no hay categorías como "motor", "combustible", "frenos". La clasificación funcional la hacemos nosotros.
2. **El campo `delta`** indica la variación esperada entre lecturas consecutivas — útil para detectar anomalías (si un valor cambia más que su delta, es sospechoso).
3. **Balatas (6 SPNs):** Dato muy valioso para mantenimiento predictivo de frenos — porcentaje restante por posición.
4. **Nivel de Urea (SPN 1761):** Relevante para emisiones y cumplimiento NOM-044.
5. **Rendimiento (SPN 185) y Ahorro instantáneo (SPN 184):** Métricas directas de eficiencia en km/L — más útiles que calcular desde tasa de combustible.
6. **Nivel de aceite en litros (SPN 10098):** Rango mínimo es -6.75 L — indica que mide la diferencia respecto al nivel óptimo (negativo = faltante).

---

## Módulo compartido clave: `spn_catalog.py`

Este módulo carga el catálogo y expone funciones para interpretar SPNs. Lo usan casi todas las Lambdas.

```python
"""
Catálogo SPN — Cargado desde S3 o embebido en el layer.
Mapea evento_spn → nombre, unidad, rango normal, clasificación funcional.
"""
import json
import boto3
from functools import lru_cache

# ═══════════════════════════════════════════════════════════════
# SPNs CLAVE — IDs CONFIRMADOS del catálogo real
# ═══════════════════════════════════════════════════════════════

# --- Agente Combustible (🔥) ---
SPN_VELOCIDAD = 84               # Velocidad Km/h — km/h — max 120
SPN_RPM = 190                    # RPM — rpm — max 3000
SPN_ACELERADOR = 91              # Posicion Pedal Acelerador — % — max 100
SPN_FRENO_PEDAL = 521            # Posicion Pedal Freno — % — max 100
SPN_TASA_COMBUSTIBLE = 183       # Tasa de combustible — L/h — max 100
SPN_RENDIMIENTO = 185            # Rendimiento — km/L — max 50
SPN_AHORRO_INSTANTANEO = 184     # Ahorro combustible instantáneo — km/L — max 50
SPN_NIVEL_COMBUSTIBLE = 96       # Nivel Combustible — % — max 120
SPN_TORQUE = 513                 # Porcentaje Torque — % — max 100
SPN_MARCHAS = 523                # Marchas — Marcha — -3 a 16
SPN_CRUISE_CONTROL = 527         # Cruise Control States — bit — 0 a 6
SPN_CRUISE_ENABLE = 596          # Cruise Control Enable Switch — bit
SPN_BRAKE_SWITCH = 597           # Brake Switch — bit
SPN_CLUTCH_SWITCH = 598          # Clutch Switch — bit
SPN_COMBUSTIBLE_CONSUMIDO = 250  # Combustible Consumido — L (inicio_fin)

# --- Agente Mantenimiento (🔧) ---
SPN_TEMP_MOTOR = 110             # Temperatura Motor — °C — max 150
SPN_TEMP_ACEITE = 175            # Temperatura Aceite Motor — °C — max 150
SPN_PRESION_ACEITE = 100         # Presion Aceite Motor — kPa — max 1000
SPN_NIVEL_ACEITE_PCT = 98        # Nivel de aceite — % — max 110
SPN_NIVEL_ACEITE_L = 10098       # Nivel de aceite litros — L — min -6.75, max 0
SPN_ANTICONGELANTE = 111         # Nivel de anticongelante — % — max 110
SPN_VOLTAJE_BATERIA = 168        # Voltaje Bateria — V — max 36
SPN_VOLTAJE_SIN_ALT = 20000      # Voltaje sin alternador — V — max 36
SPN_VOLTAJE_MIN_HIST = 20001     # Voltaje mínimo histórico — V — max 36
SPN_RETARDER = 520               # Retarder Percent Torque — % — -125 a 125
SPN_TEMP_AMBIENTE = 171          # Temperatura ambiente — °C — -10 a 75
SPN_ODOMETRO = 917               # Odometro — km (inicio_fin)
SPN_HORAS_MOTOR = 247            # Horas Motor — h (inicio_fin)
SPN_NIVEL_UREA = 1761            # Nivel Urea — % — max 100

# Balatas (6 posiciones)
SPN_BALATA_DEL_IZQ = 1099        # Delantero izquierdo — %
SPN_BALATA_DEL_DER = 1100        # Delantero derecho — %
SPN_BALATA_TRAS_IZQ_1 = 1101     # Trasero izquierdo 1 — %
SPN_BALATA_TRAS_DER_1 = 1102     # Trasero derecho 1 — %
SPN_BALATA_TRAS_IZQ_2 = 1103     # Trasero izquierdo 2 — %
SPN_BALATA_TRAS_DER_2 = 1104     # Trasero derecho 2 — %

# ═══════════════════════════════════════════════════════════════
# AGRUPACIONES FUNCIONALES (el catálogo solo tiene EDA/inicio_fin)
# ═══════════════════════════════════════════════════════════════

SPNS_COMBUSTIBLE = {
    SPN_VELOCIDAD, SPN_RPM, SPN_ACELERADOR, SPN_FRENO_PEDAL,
    SPN_TASA_COMBUSTIBLE, SPN_RENDIMIENTO, SPN_AHORRO_INSTANTANEO,
    SPN_NIVEL_COMBUSTIBLE, SPN_TORQUE, SPN_MARCHAS,
    SPN_CRUISE_CONTROL, SPN_CRUISE_ENABLE, SPN_BRAKE_SWITCH,
    SPN_CLUTCH_SWITCH, SPN_COMBUSTIBLE_CONSUMIDO,
}

SPNS_MANTENIMIENTO = {
    SPN_TEMP_MOTOR, SPN_TEMP_ACEITE, SPN_PRESION_ACEITE,
    SPN_NIVEL_ACEITE_PCT, SPN_NIVEL_ACEITE_L, SPN_ANTICONGELANTE,
    SPN_VOLTAJE_BATERIA, SPN_VOLTAJE_SIN_ALT, SPN_VOLTAJE_MIN_HIST,
    SPN_RETARDER, SPN_ODOMETRO, SPN_HORAS_MOTOR, SPN_NIVEL_UREA,
    SPN_BALATA_DEL_IZQ, SPN_BALATA_DEL_DER,
    SPN_BALATA_TRAS_IZQ_1, SPN_BALATA_TRAS_DER_1,
    SPN_BALATA_TRAS_IZQ_2, SPN_BALATA_TRAS_DER_2,
}

# SPNs que el simulador debe escribir en DynamoDB (los más relevantes para la demo)
SPNS_DEMO_PRIORITARIOS = {
    SPN_VELOCIDAD, SPN_RPM, SPN_ACELERADOR, SPN_FRENO_PEDAL,
    SPN_TASA_COMBUSTIBLE, SPN_RENDIMIENTO, SPN_NIVEL_COMBUSTIBLE,
    SPN_TEMP_MOTOR, SPN_TEMP_ACEITE, SPN_PRESION_ACEITE,
    SPN_NIVEL_ACEITE_PCT, SPN_ANTICONGELANTE, SPN_VOLTAJE_BATERIA,
    SPN_TORQUE, SPN_ODOMETRO, SPN_HORAS_MOTOR, SPN_NIVEL_UREA,
    SPN_BALATA_DEL_IZQ, SPN_BALATA_DEL_DER,
    SPN_BALATA_TRAS_IZQ_1, SPN_BALATA_TRAS_DER_1,
}

@lru_cache(maxsize=1)
def cargar_catalogo_spn(bucket, key="hackathon-data/catalogo/motor_spn.json"):
    """Carga el catálogo SPN desde S3. Se cachea en memoria."""
    s3 = boto3.client("s3")
    obj = s3.get_object(Bucket=bucket, Key=key)
    catalogo = json.loads(obj["Body"].read())
    return {int(spn["id"]): spn for spn in catalogo}

def obtener_spn(catalogo, spn_id):
    """Retorna info del SPN: name, unidad, minimo, maximo, tipo, delta."""
    return catalogo.get(int(spn_id))

def valor_fuera_de_rango(catalogo, spn_id, valor):
    """Verifica si un valor está fuera del rango [minimo, maximo] del catálogo."""
    spn = catalogo.get(int(spn_id))
    if not spn:
        return False, "SPN no encontrado en catálogo"
    minimo = spn.get("minimo")
    maximo = spn.get("maximo")
    if minimo is not None and valor < minimo:
        return True, f"{spn['name'].strip()}: {valor} {spn['unidad'].strip()} por debajo del mínimo ({minimo})"
    if maximo is not None and valor > maximo:
        return True, f"{spn['name'].strip()}: {valor} {spn['unidad'].strip()} por encima del máximo ({maximo})"
    return False, "Dentro de rango normal"

def variacion_anomala(catalogo, spn_id, valor_anterior, valor_actual):
    """
    Detecta si la variación entre dos lecturas consecutivas excede el delta esperado.
    Útil para detectar saltos anómalos en sensores.
    """
    spn = catalogo.get(int(spn_id))
    if not spn or not spn.get("delta"):
        return False
    delta_real = abs(valor_actual - valor_anterior)
    delta_esperado = spn["delta"]
    return delta_real > delta_esperado * 2  # Umbral: 2x el delta normal
```

---

## Módulo compartido: `telemetry_pivot.py`

Pivotea registros de telemetría (1 fila por SPN) a un estado consolidado por bus.

```python
"""
Transforma registros de telemetría basados en SPN a un estado consolidado por bus.
Input:  Lista de registros [{evento_spn, evento_valor, evento_fecha_hora, ...}]
Output: Dict con valores por SPN como keys, más campos de contexto planos
"""
from ado_common.spn_catalog import (
    SPN_VELOCIDAD, SPN_RPM, SPN_ACELERADOR, SPN_FRENO_PEDAL,
    SPN_TASA_COMBUSTIBLE, SPN_RENDIMIENTO, SPN_NIVEL_COMBUSTIBLE,
    SPN_TEMP_MOTOR, SPN_TEMP_ACEITE, SPN_PRESION_ACEITE,
    SPN_NIVEL_ACEITE_PCT, SPN_ANTICONGELANTE, SPN_VOLTAJE_BATERIA,
    SPN_TORQUE, SPN_ODOMETRO, SPN_HORAS_MOTOR, SPN_NIVEL_UREA,
    SPNS_DEMO_PRIORITARIOS, valor_fuera_de_rango,
)

# Mapeo SPN → nombre corto para campos planos en DynamoDB
SPN_NOMBRE_CORTO = {
    84:  "velocidad_kmh",
    190: "rpm",
    91:  "pct_acelerador",
    521: "pct_freno",
    183: "tasa_combustible_lh",
    185: "rendimiento_kml",
    184: "ahorro_instantaneo_kml",
    96:  "nivel_combustible_pct",
    110: "temperatura_motor_c",
    175: "temperatura_aceite_c",
    100: "presion_aceite_kpa",
    98:  "nivel_aceite_pct",
    111: "nivel_anticongelante_pct",
    168: "voltaje_bateria_v",
    513: "torque_pct",
    520: "retarder_torque_pct",
    523: "marcha",
    917: "odometro_km",
    247: "horas_motor_h",
    250: "combustible_consumido_l",
    171: "temperatura_ambiente_c",
    1761: "nivel_urea_pct",
    1099: "balata_del_izq_pct",
    1100: "balata_del_der_pct",
    1101: "balata_tras_izq1_pct",
    1102: "balata_tras_der1_pct",
    1103: "balata_tras_izq2_pct",
    1104: "balata_tras_der2_pct",
}


def pivotar_telemetria(registros, catalogo_spn, solo_prioritarios=True):
    """
    Agrupa registros SPN de un bus y los pivotea a un estado consolidado.
    
    Args:
        registros: Lista de dicts con evento_spn, evento_valor, evento_fecha_hora, etc.
        catalogo_spn: Dict indexado por SPN ID (de cargar_catalogo_spn)
        solo_prioritarios: Si True, solo incluye SPNS_DEMO_PRIORITARIOS
    
    Returns:
        Dict con:
        - Campos planos (velocidad_kmh, rpm, etc.) para queries rápidos
        - spn_valores: Map completo {spn_id: {valor, name, unidad, fuera_de_rango}}
        - alertas_spn: Lista de SPNs fuera de rango
        - Contexto del viaje (autobus, operador, ruta, GPS)
    """
    spn_valores = {}
    alertas_spn = []
    campos_planos = {}
    
    # Contexto del viaje (del primer registro)
    contexto = {}
    if registros:
        r0 = registros[0]
        contexto = {
            "autobus": str(r0.get("autobus", "")),
            "viaje_id": r0.get("viaje_id"),
            "operador_cve": str(r0.get("operador_cve", "")),
            "operador_desc": str(r0.get("operador_desc", "")).strip(),
            "viaje_ruta": str(r0.get("viaje_ruta", "")).strip(),
            "viaje_ruta_origen": str(r0.get("viaje_ruta_origen", "")).strip(),
            "viaje_ruta_destino": str(r0.get("viaje_ruta_destino", "")).strip(),
            "latitud": r0.get("evento_latitud"),
            "longitud": r0.get("evento_longitud"),
        }
    
    for reg in registros:
        spn_id = int(reg["evento_spn"])
        valor = float(reg["evento_valor"])
        
        # Filtrar si solo queremos prioritarios
        if solo_prioritarios and spn_id not in SPNS_DEMO_PRIORITARIOS:
            continue
        
        spn_info = catalogo_spn.get(spn_id, {})
        nombre = spn_info.get("name", f"SPN-{spn_id}").strip()
        unidad = spn_info.get("unidad", "").strip()
        
        fuera, mensaje = valor_fuera_de_rango(catalogo_spn, spn_id, valor)
        
        spn_valores[str(spn_id)] = {
            "valor": valor,
            "name": nombre,
            "unidad": unidad,
            "fuera_de_rango": fuera,
        }
        
        if fuera:
            alertas_spn.append({
                "spn_id": spn_id,
                "name": nombre,
                "valor": valor,
                "unidad": unidad,
                "mensaje": mensaje,
            })
        
        # Campo plano para queries directos en DynamoDB
        nombre_corto = SPN_NOMBRE_CORTO.get(spn_id)
        if nombre_corto:
            campos_planos[nombre_corto] = valor
        
        # Actualizar GPS con la última lectura
        if reg.get("evento_latitud"):
            contexto["latitud"] = reg["evento_latitud"]
            contexto["longitud"] = reg["evento_longitud"]
    
    return {
        **contexto,
        **campos_planos,
        "spn_valores": spn_valores,
        "alertas_spn": alertas_spn,
    }
```

---

## IAM — Roles de ejecución

```yaml
Rol base: ado-lambda-execution-role
Políticas comunes:
  - AWSLambdaBasicExecutionRole          # CloudWatch Logs
  - AmazonDynamoDBReadOnlyAccess         # Lectura DynamoDB (tools de lectura)
  - AmazonS3ReadOnlyAccess               # Lectura S3 (datos simulados + catálogo SPN)

Políticas adicionales por función:
  ado-simulador-telemetria:
    - dynamodb:PutItem, dynamodb:BatchWriteItem en ado-telemetria-live
    - s3:GetObject en ado-telemetry-mvp/hackathon-data/telemetria-simulada/*
  
  tool-generar-recomendacion:
    - dynamodb:PutItem en ado-alertas
  
  tool-predecir-evento:
    - sagemaker:InvokeEndpoint en ado-prediccion-eventos
  
  tool-buscar-patrones-historicos:
    - s3:GetObject en ado-telemetry-mvp/hackathon-data/fallas-simuladas/*
  
  ado-dashboard-api:
    - dynamodb:Query en ado-telemetria-live
    - dynamodb:Query, dynamodb:Scan en ado-alertas
```

---

## Estructura S3 adaptada a las fuentes reales

```
s3://ado-telemetry-mvp/hackathon-data/
├── telemetria-simulada/              ← Datos de telemetry-data (simulados)
│   └── {YYYY-MM}/
│       └── {autobus}/
│           └── telemetria_{autobus}_{YYYY-MM-DD}.parquet
├── fallas-simuladas/                 ← Datos de data_fault (simulados)
│   └── fallas_simuladas.parquet      
├── catalogo/                         ← Catálogo motor_spn
│   └── motor_spn.json                
├── knowledge-base/
│   └── docs/
│       ├── motor_spn.json            ← También aquí para Knowledge Base RAG
│       ├── codigos-falla-catalogo.csv
│       ├── normas-conduccion-eficiente.pdf
│       └── nom-044-resumen.pdf
└── modelos/
    └── sagemaker/
        └── training-data/
            └── features_eventos_simulados.parquet
```

---

## DynamoDB — Tabla `ado-telemetria-live` (adaptada)

El simulador pivotea los registros SPN y escribe un estado consolidado por bus.

- **PK:** `autobus` (S) — número económico del bus
- **SK:** `timestamp` (S) — ISO 8601
- **TTL:** `ttl_expiry` — 24 horas

| Atributo | Tipo | Origen | Descripción |
|---|---|---|---|
| `autobus` | S | telemetry-data.autobus | PK — número económico |
| `timestamp` | S | generado (now) | SK — timestamp simulado |
| `viaje_id` | N | telemetry-data.viaje_id | ID del viaje activo |
| `operador_cve` | S | telemetry-data.operador_cve | Clave del conductor |
| `operador_desc` | S | telemetry-data.operador_desc | Nombre del conductor |
| `viaje_ruta` | S | telemetry-data.viaje_ruta | Código de ruta |
| `viaje_ruta_origen` | S | telemetry-data.viaje_ruta_origen | Ciudad origen |
| `viaje_ruta_destino` | S | telemetry-data.viaje_ruta_destino | Ciudad destino |
| `latitud` | N | telemetry-data.evento_latitud | Última coordenada GPS |
| `longitud` | N | telemetry-data.evento_longitud | Última coordenada GPS |
| `spn_valores` | M (Map) | Pivoteo de SPNs | Mapa: `{spn_id: {valor, name, unidad, fuera_de_rango}}` |
| `alertas_spn` | L (List) | Calculado | Lista de SPNs fuera de rango normal |
| `estado_consumo` | S | Calculado | `EFICIENTE`, `ALERTA_MODERADA`, `ALERTA_SIGNIFICATIVA` |
| `ttl_expiry` | N | Calculado | Unix timestamp + 86400 |

**GSI:** `viaje_ruta-timestamp-index` (PK: `viaje_ruta`, SK: `timestamp`)

> **Nota:** `spn_valores` es un Map de DynamoDB que contiene todos los SPNs leídos en esa ventana temporal. Esto permite flexibilidad — si el catálogo SPN cambia, no hay que modificar el esquema de DynamoDB.

---

## LAMBDA 1 — `ado-simulador-telemetria`

### Propósito
Simula la ingesta de telemetría en tiempo real. Lee registros de `telemetry-data` en S3, los agrupa por bus y ventana temporal, pivotea los SPNs usando el catálogo `motor_spn`, y escribe un estado consolidado en DynamoDB.

### Clasificación
- **Grupo:** Simulador de ingesta
- **Prioridad:** 🔴 Crítica
- **Día:** Día 1

### Especificación técnica

```yaml
Nombre:           ado-simulador-telemetria
Runtime:          Python 3.12
Memoria:          512 MB
Timeout:          30 segundos
Trigger:          Amazon EventBridge Scheduler — rate(10 seconds)
Concurrencia:     1
```

### Variables de entorno

```yaml
DYNAMODB_TABLE:       ado-telemetria-live
S3_BUCKET:            ado-telemetry-mvp
S3_TELEMETRIA_PREFIX: hackathon-data/telemetria-simulada/
S3_CATALOGO_KEY:      hackathon-data/catalogo/motor_spn.json
NUM_BUSES:            "20"
```

### Flujo de ejecución

```
1. EventBridge dispara cada 10 segundos

2. Cargar catálogo SPN desde S3 (cacheado en memoria entre invocaciones)
   catalogo = cargar_catalogo_spn(bucket, "hackathon-data/catalogo/motor_spn.json")

3. Para cada bus simulado (lista de autobus IDs):
   a. Calcular offset stateless:
      offset = (int(time.time()) // 10 + bus_index) % total_registros
   
   b. Leer bloque de registros de S3 para ese bus y offset
      → Obtener N registros de telemetry-data donde autobus = bus_id
      → Cada registro es un SPN individual
   
   c. Agrupar registros por ventana temporal cercana (~30 seg)
      → Resultado: lista de {evento_spn, evento_valor, evento_descripcion}
   
   d. Pivotar SPNs a estado consolidado:
      Para cada registro en el grupo:
        - Buscar SPN en catálogo → obtener name, unidad, minimo, maximo
        - Verificar si valor está fuera de rango (minimo/maximo del catálogo)
        - Agregar a spn_valores map
   
   e. Calcular estado_consumo:
      - Buscar SPN de consumo de combustible en spn_valores
      - Comparar contra rango del catálogo motor_spn
      - Clasificar: EFICIENTE / ALERTA_MODERADA / ALERTA_SIGNIFICATIVA
   
   f. Construir alertas_spn:
      - Lista de SPNs donde valor está fuera de rango
   
   g. Escribir en DynamoDB con timestamp = now()

4. batch_write_item para los 20 buses
5. Log: "{n} buses actualizados, {m} con alertas SPN"
```

### Lógica de clasificación de consumo (SPNs reales confirmados)

```python
from ado_common.spn_catalog import (
    SPN_RENDIMIENTO,          # 185 — Rendimiento km/L (max 50)
    SPN_TASA_COMBUSTIBLE,     # 183 — Tasa de combustible L/h (max 100)
    SPN_AHORRO_INSTANTANEO,   # 184 — Ahorro instantáneo km/L (max 50)
)

def clasificar_consumo(spn_valores):
    """
    Clasifica el estado de consumo usando SPN 185 (Rendimiento km/L) como métrica principal.
    Fallback a SPN 183 (Tasa de combustible L/h) si rendimiento no está disponible.
    
    Rendimiento (SPN 185): más km/L = más eficiente
      - > 3.0 km/L → EFICIENTE (para autobús de pasajeros)
      - 2.0 - 3.0 km/L → ALERTA_MODERADA
      - < 2.0 km/L → ALERTA_SIGNIFICATIVA
    
    Tasa combustible (SPN 183): menos L/h = más eficiente
      - < 30 L/h → EFICIENTE
      - 30 - 50 L/h → ALERTA_MODERADA
      - > 50 L/h → ALERTA_SIGNIFICATIVA
    """
    # Prioridad 1: Rendimiento directo (km/L)
    rendimiento = spn_valores.get("185", {}).get("valor")
    if rendimiento is not None:
        if rendimiento >= 3.0:
            return "EFICIENTE"
        elif rendimiento >= 2.0:
            return "ALERTA_MODERADA"
        else:
            return "ALERTA_SIGNIFICATIVA"
    
    # Prioridad 2: Tasa de combustible (L/h) — inverso
    tasa = spn_valores.get("183", {}).get("valor")
    if tasa is not None:
        if tasa <= 30:
            return "EFICIENTE"
        elif tasa <= 50:
            return "ALERTA_MODERADA"
        else:
            return "ALERTA_SIGNIFICATIVA"
    
    return "SIN_DATOS"
```

### Formato del item DynamoDB (con SPNs reales)

```json
{
  "autobus": {"S": "1247"},
  "timestamp": {"S": "2026-04-25T14:32:00Z"},
  "viaje_id": {"N": "98765"},
  "operador_cve": {"S": "1042"},
  "operador_desc": {"S": "García López Juan"},
  "viaje_ruta": {"S": "MEX-PUE-001"},
  "viaje_ruta_origen": {"S": "México"},
  "viaje_ruta_destino": {"S": "Puebla"},
  "latitud": {"N": "19.4326"},
  "longitud": {"N": "-99.1332"},
  "velocidad_kmh": {"N": "87.5"},
  "rpm": {"N": "1850"},
  "pct_acelerador": {"N": "35.2"},
  "pct_freno": {"N": "12.1"},
  "tasa_combustible_lh": {"N": "28.5"},
  "rendimiento_kml": {"N": "3.2"},
  "nivel_combustible_pct": {"N": "68.0"},
  "temperatura_motor_c": {"N": "104.2"},
  "temperatura_aceite_c": {"N": "95.1"},
  "presion_aceite_kpa": {"N": "320.0"},
  "nivel_aceite_pct": {"N": "85.0"},
  "nivel_anticongelante_pct": {"N": "92.0"},
  "voltaje_bateria_v": {"N": "27.5"},
  "torque_pct": {"N": "45.0"},
  "odometro_km": {"N": "187432.5"},
  "horas_motor_h": {"N": "12450.3"},
  "nivel_urea_pct": {"N": "78.0"},
  "balata_del_izq_pct": {"N": "62.0"},
  "balata_del_der_pct": {"N": "58.0"},
  "balata_tras_izq1_pct": {"N": "45.0"},
  "balata_tras_der1_pct": {"N": "47.0"},
  "spn_valores": {"M": {
    "84":  {"M": {"valor": {"N": "87.5"},  "name": {"S": "Velocidad Km/h"},          "unidad": {"S": "km/h"}, "fuera_de_rango": {"BOOL": false}}},
    "190": {"M": {"valor": {"N": "1850"},  "name": {"S": "RPM"},                     "unidad": {"S": "rpm"},  "fuera_de_rango": {"BOOL": false}}},
    "110": {"M": {"valor": {"N": "104.2"}, "name": {"S": "Temperatura Motor"},       "unidad": {"S": "°C"},   "fuera_de_rango": {"BOOL": true}}},
    "100": {"M": {"valor": {"N": "320.0"}, "name": {"S": "Presion Aceite Motor"},    "unidad": {"S": "kpa"},  "fuera_de_rango": {"BOOL": false}}},
    "183": {"M": {"valor": {"N": "28.5"},  "name": {"S": "Tasa de combustible"},     "unidad": {"S": "L/h"},  "fuera_de_rango": {"BOOL": false}}},
    "185": {"M": {"valor": {"N": "3.2"},   "name": {"S": "Rendimiento"},             "unidad": {"S": "km/L"}, "fuera_de_rango": {"BOOL": false}}}
  }},
  "alertas_spn": {"L": [
    {"M": {"spn_id": {"N": "110"}, "name": {"S": "Temperatura Motor"}, "valor": {"N": "104.2"}, "unidad": {"S": "°C"}, "mensaje": {"S": "Temperatura Motor: 104.2 °C por encima del máximo (150)"}}}
  ]},
  "estado_consumo": {"S": "EFICIENTE"},
  "ttl_expiry": {"N": "1745600000"}
}
```

> **Nota:** El item tiene campos planos (`velocidad_kmh`, `rpm`, etc.) para queries directos y filtros en DynamoDB, más el Map `spn_valores` completo para análisis detallado por los agentes. Esto es redundante a propósito — optimiza tanto queries como análisis.

---

## LAMBDA 2 — `tool-consultar-telemetria`

### Propósito
Tool del Agente Combustible. Consulta los últimos N registros consolidados de un bus desde DynamoDB. Traduce los SPNs a nombres legibles usando el catálogo.

### Clasificación
- **Grupo:** Tools Agente Combustible
- **Prioridad:** 🔴 Crítica
- **Día:** Día 2

### Especificación técnica

```yaml
Nombre:           tool-consultar-telemetria
Runtime:          Python 3.12
Memoria:          256 MB
Timeout:          10 segundos
Trigger:          Bedrock AgentCore (Action Group)
```

### Input (desde Bedrock AgentCore)

```json
{
  "autobus": "1247",
  "ultimos_n_registros": 10
}
```

### Flujo de ejecución

```
1. Recibir autobus y ultimos_n_registros (default: 10, max: 50)
2. Cargar catálogo SPN (cacheado)
3. Query DynamoDB:
   - Table: ado-telemetria-live
   - KeyCondition: autobus = :autobus
   - ScanIndexForward: False (más recientes primero)
   - Limit: ultimos_n_registros
4. Para cada registro:
   - Extraer spn_valores (Map)
   - Traducir SPNs a nombres legibles con catálogo
   - Identificar SPNs fuera de rango
5. Retornar al agente con formato interpretable
```

### Output (hacia el agente — con nombres reales del catálogo)

```json
{
  "autobus": "1247",
  "registros_encontrados": 10,
  "viaje_ruta": "MEX-PUE-001",
  "viaje_ruta_origen": "México",
  "viaje_ruta_destino": "Puebla",
  "operador": "García López Juan (cve: 1042)",
  "ultimo_registro": "2026-04-25T14:32:00Z",
  "variables_actuales": [
    {"spn": 84,  "nombre": "Velocidad Km/h",          "valor": 87.5,  "unidad": "km/h", "rango": "0-120",    "estado": "normal"},
    {"spn": 190, "nombre": "RPM",                      "valor": 1850,  "unidad": "rpm",  "rango": "0-3000",   "estado": "normal"},
    {"spn": 91,  "nombre": "Posicion Pedal Acelerador","valor": 72.3,  "unidad": "%",    "rango": "0-100",    "estado": "normal"},
    {"spn": 521, "nombre": "Posicion Pedal Freno",     "valor": 12.1,  "unidad": "%",    "rango": "0-100",    "estado": "normal"},
    {"spn": 183, "nombre": "Tasa de combustible",      "valor": 42.5,  "unidad": "L/h",  "rango": "0-100",    "estado": "normal"},
    {"spn": 185, "nombre": "Rendimiento",              "valor": 2.1,   "unidad": "km/L", "rango": "0-50",     "estado": "normal"},
    {"spn": 110, "nombre": "Temperatura Motor",        "valor": 104.2, "unidad": "°C",   "rango": "0-150",    "estado": "FUERA_DE_RANGO"},
    {"spn": 100, "nombre": "Presion Aceite Motor",     "valor": 320.0, "unidad": "kPa",  "rango": "0-1000",   "estado": "normal"},
    {"spn": 513, "nombre": "Porcentaje Torque",        "valor": 68.0,  "unidad": "%",    "rango": "0-100",    "estado": "normal"},
    {"spn": 96,  "nombre": "Nivel Combustible",        "valor": 68.0,  "unidad": "%",    "rango": "0-120",    "estado": "normal"}
  ],
  "alertas_activas": [
    "Temperatura Motor: 104.2°C — dentro del rango del catálogo (0-150°C) pero en tendencia ascendente"
  ],
  "estado_consumo": "ALERTA_MODERADA",
  "historial_reciente": [
    {
      "timestamp": "2026-04-25T14:32:00Z",
      "estado_consumo": "ALERTA_MODERADA",
      "rendimiento_kml": 2.1,
      "spn_fuera_de_rango": 0
    },
    {
      "timestamp": "2026-04-25T14:31:50Z",
      "estado_consumo": "EFICIENTE",
      "rendimiento_kml": 3.4,
      "spn_fuera_de_rango": 0
    }
  ]
}
```

---

## LAMBDA 3 — `tool-calcular-desviacion`

### Propósito
Tool del Agente Combustible. Calcula la desviación del consumo de un bus respecto a los rangos definidos en el catálogo `motor_spn`. Identifica causas probables analizando otros SPNs correlacionados.

### Clasificación
- **Grupo:** Tools Agente Combustible
- **Prioridad:** 🔴 Crítica
- **Día:** Día 2

### Especificación técnica

```yaml
Nombre:           tool-calcular-desviacion
Runtime:          Python 3.12
Memoria:          256 MB
Timeout:          10 segundos
Trigger:          Bedrock AgentCore (Action Group)
```

### Input

```json
{
  "autobus": "1247",
  "viaje_ruta": "MEX-PUE-001"
}
```

### Flujo de ejecución

```
1. Recibir autobus y viaje_ruta
2. Cargar catálogo SPN
3. Query DynamoDB: últimos 10 registros del bus
4. Para cada registro, extraer SPNs de eficiencia:
   - SPN 185 (Rendimiento km/L) — métrica principal
   - SPN 183 (Tasa de combustible L/h) — métrica secundaria
   - SPN 184 (Ahorro instantáneo km/L) — complementaria
5. Calcular promedios de los últimos 10 registros
6. Clasificar desviación:
   Rendimiento (SPN 185):
   - >= 3.0 km/L → DENTRO_DE_RANGO
   - 2.5 - 3.0 km/L → DESVIACION_LEVE
   - 2.0 - 2.5 km/L → DESVIACION_MODERADA
   - < 2.0 km/L → DESVIACION_SIGNIFICATIVA
7. Identificar causas probables analizando SPNs correlacionados:
   - SPN 190 (RPM) promedio > 2200 → "RPM por encima del rango óptimo de crucero"
   - SPN 91 (Pedal Acelerador) promedio > 65% → "Aceleración brusca frecuente"
   - SPN 84 (Velocidad) promedio > 100 km/h → "Velocidad excesiva"
   - SPN 521 (Pedal Freno) promedio > 25% → "Frenado tardío frecuente"
   - SPN 513 (Torque) promedio > 75% → "Motor bajo esfuerzo elevado sostenido"
   - SPN 523 (Marchas) cambios frecuentes → "Patrón de cambios ineficiente"
   - SPN 527/596 (Cruise Control) no activo → "Sin uso de control de crucero"
8. Retornar resultado
```

### Output

```json
{
  "autobus": "1247",
  "viaje_ruta": "MEX-PUE-001",
  "viaje_ruta_origen": "México",
  "viaje_ruta_destino": "Puebla",
  "eficiencia": {
    "rendimiento_kml": {
      "spn_id": 185,
      "nombre": "Rendimiento",
      "promedio_reciente": 2.3,
      "unidad": "km/L",
      "rango_catalogo": {"minimo": 0, "maximo": 50}
    },
    "tasa_combustible_lh": {
      "spn_id": 183,
      "nombre": "Tasa de combustible",
      "promedio_reciente": 42.5,
      "unidad": "L/h",
      "rango_catalogo": {"minimo": 0, "maximo": 100}
    }
  },
  "desviacion_categoria": "DESVIACION_MODERADA",
  "desviacion_descripcion": "El rendimiento reciente es moderadamente inferior al esperado para operación eficiente",
  "causas_probables": [
    {
      "spn_id": 190,
      "nombre": "RPM",
      "hallazgo": "RPM promedio por encima del rango óptimo de crucero",
      "valor_promedio": 2250,
      "unidad": "rpm",
      "rango_catalogo": "0-3000 rpm"
    },
    {
      "spn_id": 91,
      "nombre": "Posicion Pedal Acelerador",
      "hallazgo": "Porcentaje de acelerador elevado de forma frecuente",
      "valor_promedio": 72.3,
      "unidad": "%",
      "rango_catalogo": "0-100%"
    },
    {
      "spn_id": 527,
      "nombre": "Cruise Control States",
      "hallazgo": "Control de crucero no activo — oportunidad de mejora en tramos de autopista",
      "valor_promedio": 0,
      "unidad": "bit",
      "rango_catalogo": "0-6"
    }
  ],
  "estado_consumo_actual": "ALERTA_MODERADA"
}
```

---

## LAMBDA 4 — `tool-listar-buses-activos`

### Propósito
Tool del Agente Combustible. Lista buses con telemetría reciente, opcionalmente filtrada por ruta. Ordena por severidad de alertas.

### Clasificación
- **Grupo:** Tools Agente Combustible
- **Prioridad:** 🟡 Importante
- **Día:** Día 2

### Especificación técnica

```yaml
Nombre:           tool-listar-buses-activos
Runtime:          Python 3.12
Memoria:          256 MB
Timeout:          10 segundos
Trigger:          Bedrock AgentCore (Action Group)
```

### Input

```json
{
  "viaje_ruta": "MEX-PUE-001"
}
```
*(viaje_ruta es opcional)*

### Flujo de ejecución

```
1. Calcular timestamp_limite = (now - 5 minutos).isoformat()
2. Si viaje_ruta proporcionado:
   - Query GSI viaje_ruta-timestamp-index
   - KeyCondition: viaje_ruta = :viaje_ruta AND timestamp > :timestamp_limite
3. Si no hay viaje_ruta:
   - Scan con FilterExpression: timestamp > :timestamp_limite
   (aceptable para ~20 buses en MVP)
4. Para cada bus, extraer:
   - autobus, viaje_ruta, operador_desc, estado_consumo
   - Contar SPNs fuera de rango (de alertas_spn)
5. Ordenar: ALERTA_SIGNIFICATIVA primero, luego por cantidad de alertas SPN
6. Retornar lista
```

### Output

```json
{
  "timestamp_consulta": "2026-04-25T14:35:00Z",
  "ventana_actividad": "5 minutos",
  "filtro_ruta": "MEX-PUE-001",
  "buses_activos": 6,
  "buses": [
    {
      "autobus": "1247",
      "viaje_ruta": "MEX-PUE-001",
      "operador": "García López Juan",
      "ultimo_timestamp": "2026-04-25T14:34:50Z",
      "estado_consumo": "ALERTA_SIGNIFICATIVA",
      "spn_fuera_de_rango": 3,
      "alertas_resumen": ["Engine Coolant Temperature elevada", "Engine Oil Pressure baja", "Fuel Rate elevado"]
    },
    {
      "autobus": "1103",
      "viaje_ruta": "MEX-PUE-001",
      "operador": "Martínez Ruiz Pedro",
      "ultimo_timestamp": "2026-04-25T14:34:40Z",
      "estado_consumo": "EFICIENTE",
      "spn_fuera_de_rango": 0,
      "alertas_resumen": []
    }
  ]
}
```

---

## LAMBDA 5 — `tool-consultar-obd`

### Propósito
Tool del Agente Mantenimiento. Consulta señales de diagnóstico de un bus. A diferencia de `tool-consultar-telemetria` (enfocada en consumo), esta se enfoca en SPNs de tipo motor, frenos, transmisión — las variables relevantes para mantenimiento predictivo. También cruza con `data_fault` para verificar si hay fallas activas o recientes.

### Clasificación
- **Grupo:** Tools Agente Mantenimiento
- **Prioridad:** 🔴 Crítica
- **Día:** Día 3

### Especificación técnica

```yaml
Nombre:           tool-consultar-obd
Runtime:          Python 3.12
Memoria:          256 MB
Timeout:          10 segundos
Trigger:          Bedrock AgentCore (Action Group)
```

### Input

```json
{
  "autobus": "1089"
}
```

### Flujo de ejecución

```
1. Recibir autobus
2. Cargar catálogo SPN
3. Query DynamoDB: últimos 20 registros del bus
4. Para cada registro, extraer spn_valores
5. Filtrar SPNs relevantes para mantenimiento (SPNS_MANTENIMIENTO):
   - SPN 110: Temperatura Motor (°C, max 150)
   - SPN 175: Temperatura Aceite Motor (°C, max 150)
   - SPN 100: Presion Aceite Motor (kPa, max 1000)
   - SPN 98:  Nivel de aceite (%, max 110)
   - SPN 10098: Nivel de aceite litros (L, min -6.75, max 0)
   - SPN 111: Nivel de anticongelante (%, max 110)
   - SPN 168: Voltaje Bateria (V, max 36)
   - SPN 520: Retarder Percent Torque (%, -125 a 125)
   - SPN 917: Odometro (km)
   - SPN 247: Horas Motor (h)
   - SPN 1761: Nivel Urea (%, max 100)
   - SPNs 1099-1104: Balatas (% restante por posición)
6. Calcular tendencias (primera mitad vs segunda mitad de los 20 registros):
   - Para cada SPN: "estable" | "ascendente" | "descendente"
7. Detectar variaciones anómalas usando campo delta del catálogo:
   - Si variación entre lecturas > 2x delta → anomalía
8. Buscar fallas recientes del bus en data_fault (S3):
   - Filtrar por autobus = :autobus
   - Últimas 5 fallas
   - Incluir: codigo, severidad, descripcion, modelo, marca_comercial
9. Construir resumen de salud mecánica
10. Retornar
```

### Output (con SPNs reales y balatas)

```json
{
  "autobus": "1089",
  "viaje_ruta": "MEX-QRO-003",
  "odometro_km": 187432.5,
  "horas_motor_h": 12450.3,
  "señales_mecanicas": [
    {
      "spn_id": 110,
      "nombre": "Temperatura Motor",
      "valor_actual": 104.2,
      "unidad": "°C",
      "rango_catalogo": {"minimo": 0, "maximo": 150},
      "delta_esperado": 3.0,
      "estado": "normal",
      "tendencia": "ascendente",
      "nota": "Dentro del rango del catálogo pero en tendencia ascendente sostenida"
    },
    {
      "spn_id": 175,
      "nombre": "Temperatura Aceite Motor",
      "valor_actual": 138.5,
      "unidad": "°C",
      "rango_catalogo": {"minimo": 0, "maximo": 150},
      "delta_esperado": 2.0,
      "estado": "normal",
      "tendencia": "ascendente",
      "nota": "Cercano al máximo del catálogo (150°C)"
    },
    {
      "spn_id": 100,
      "nombre": "Presion Aceite Motor",
      "valor_actual": 180.0,
      "unidad": "kPa",
      "rango_catalogo": {"minimo": 0, "maximo": 1000},
      "delta_esperado": 100.0,
      "estado": "normal",
      "tendencia": "descendente",
      "nota": "Presión baja relativa al rango — tendencia descendente"
    },
    {
      "spn_id": 111,
      "nombre": "Nivel de anticongelante",
      "valor_actual": 45.0,
      "unidad": "%",
      "rango_catalogo": {"minimo": 0, "maximo": 110},
      "delta_esperado": 95.0,
      "estado": "normal",
      "tendencia": "descendente",
      "nota": "Nivel bajo de anticongelante — posible fuga"
    },
    {
      "spn_id": 1761,
      "nombre": "Nivel Urea",
      "valor_actual": 22.0,
      "unidad": "%",
      "rango_catalogo": {"minimo": 0, "maximo": 100},
      "delta_esperado": 2.0,
      "estado": "normal",
      "tendencia": "descendente",
      "nota": "Nivel bajo de urea — requiere recarga para cumplimiento de emisiones"
    }
  ],
  "estado_balatas": {
    "delantero_izquierdo": {"spn": 1099, "pct_restante": 62.0, "estado": "aceptable"},
    "delantero_derecho":   {"spn": 1100, "pct_restante": 58.0, "estado": "aceptable"},
    "trasero_izquierdo_1": {"spn": 1101, "pct_restante": 25.0, "estado": "REQUIERE_ATENCION"},
    "trasero_derecho_1":   {"spn": 1102, "pct_restante": 22.0, "estado": "REQUIERE_ATENCION"},
    "trasero_izquierdo_2": {"spn": 1103, "pct_restante": 45.0, "estado": "aceptable"},
    "trasero_derecho_2":   {"spn": 1104, "pct_restante": 47.0, "estado": "aceptable"},
    "resumen": "Balatas traseras posición 1 (izq: 25%, der: 22%) requieren reemplazo próximo"
  },
  "fallas_recientes": [
    {
      "codigo": "SPN110-FMI0",
      "severidad": 3,
      "descripcion": "Temperatura de refrigerante por encima del rango",
      "fecha_hora": "2026-04-20T08:15:00Z",
      "modelo": "IRIZAR i8",
      "marca_comercial": "ADO Platino",
      "zona": "Centro"
    }
  ],
  "resumen_salud": "Señales de atención: temperatura de motor y aceite en tendencia ascendente. Nivel de anticongelante bajo (45%). Balatas traseras posición 1 con desgaste avanzado (22-25% restante). Nivel de urea bajo (22%) — requiere recarga. Falla reciente SPN110-FMI0 hace 5 días."
}
```

---

## LAMBDA 6 — `tool-predecir-evento`

### Propósito
Tool del Agente Mantenimiento. Construye el vector de features desde los SPNs del bus, invoca SageMaker para predicción, o usa fallback heurístico basado en los rangos del catálogo `motor_spn`.

### Clasificación
- **Grupo:** Tools Agente Mantenimiento
- **Prioridad:** 🟡 Importante (tiene fallback)
- **Día:** Día 3

### Especificación técnica

```yaml
Nombre:           tool-predecir-evento
Runtime:          Python 3.12
Memoria:          256 MB
Timeout:          30 segundos
Trigger:          Bedrock AgentCore (Action Group)
```

### Variables de entorno adicionales

```yaml
SAGEMAKER_ENDPOINT:       ado-prediccion-eventos
USE_HEURISTIC_FALLBACK:   "true"
S3_CATALOGO_KEY:          hackathon-data/catalogo/motor_spn.json
```

### Input

```json
{
  "autobus": "1089"
}
```

### Flujo de ejecución

```
1. Recibir autobus
2. Cargar catálogo SPN
3. Query DynamoDB: últimos 20 registros del bus
4. Construir vector de features desde SPNs:
   Para cada SPN relevante en los 20 registros:
   - Calcular promedio, máximo, mínimo
   - Verificar cuántos están fuera de rango (usando catálogo motor_spn)
   - Contar fallas recientes del bus (de data_fault)
   
   Features resultantes:
   - temperatura_motor_avg, temperatura_motor_max
   - presion_aceite_avg, presion_aceite_min
   - tiene_falla_reciente (1/0)
   - cantidad_spn_fuera_de_rango
   - rpm_avg
   - pct_freno_avg
   
5. Intentar invocar SageMaker:
   - Si éxito → usar predicción del modelo
   - Si falla → fallback heurístico
   
6. Clasificar y retornar
```

### Fallback heurístico (con SPNs reales confirmados)

```python
from ado_common.spn_catalog import (
    SPN_TEMP_MOTOR, SPN_TEMP_ACEITE, SPN_PRESION_ACEITE,
    SPN_NIVEL_ACEITE_PCT, SPN_ANTICONGELANTE, SPN_VOLTAJE_BATERIA,
    SPN_NIVEL_UREA, SPN_HORAS_MOTOR, SPN_ODOMETRO,
    SPN_BALATA_DEL_IZQ, SPN_BALATA_DEL_DER,
    SPN_BALATA_TRAS_IZQ_1, SPN_BALATA_TRAS_DER_1,
    SPN_BALATA_TRAS_IZQ_2, SPN_BALATA_TRAS_DER_2,
)

BALATAS_SPNS = [
    SPN_BALATA_DEL_IZQ, SPN_BALATA_DEL_DER,
    SPN_BALATA_TRAS_IZQ_1, SPN_BALATA_TRAS_DER_1,
    SPN_BALATA_TRAS_IZQ_2, SPN_BALATA_TRAS_DER_2,
]

def predecir_heuristico(spn_promedios, catalogo, fallas_recientes):
    """
    Scoring de riesgo basado en SPNs reales y rangos del catálogo.
    
    SPNs evaluados:
      110 — Temperatura Motor (°C, max 150)
      175 — Temperatura Aceite Motor (°C, max 150)
      100 — Presion Aceite Motor (kPa, max 1000)
       98 — Nivel de aceite (%, max 110)
      111 — Nivel de anticongelante (%, max 110)
      168 — Voltaje Bateria (V, max 36)
     1761 — Nivel Urea (%, max 100)
     1099-1104 — Balatas (% restante)
    """
    score = 0
    factores = []
    componentes_riesgo = set()
    
    # --- Temperatura Motor (SPN 110) ---
    temp_motor = spn_promedios.get(SPN_TEMP_MOTOR)
    if temp_motor:
        promedio = temp_motor["promedio"]
        maximo_lectura = temp_motor["maximo"]
        if promedio > 120:  # > 80% del rango (150)
            score += 3
            factores.append("Temperatura Motor: promedio elevado sostenido")
            componentes_riesgo.add("sistema_refrigeracion")
        if maximo_lectura > 140:  # Cercano al máximo del catálogo
            score += 2
            factores.append("Temperatura Motor: picos cercanos al límite del catálogo (150°C)")
            componentes_riesgo.add("bomba_agua")
    
    # --- Temperatura Aceite (SPN 175) ---
    temp_aceite = spn_promedios.get(SPN_TEMP_ACEITE)
    if temp_aceite:
        if temp_aceite["promedio"] > 130:
            score += 2
            factores.append("Temperatura Aceite Motor: promedio elevado")
            componentes_riesgo.add("circuito_aceite")
    
    # --- Presión Aceite (SPN 100) — rango 0-1000 kPa ---
    presion = spn_promedios.get(SPN_PRESION_ACEITE)
    if presion:
        if presion["minimo"] < 150:  # Presión baja
            score += 3
            factores.append("Presion Aceite Motor: lecturas por debajo del rango operativo seguro")
            componentes_riesgo.add("bomba_aceite")
        if presion["promedio"] < 250:
            score += 1
            factores.append("Presion Aceite Motor: promedio bajo")
    
    # --- Nivel de aceite (SPN 98) ---
    nivel_aceite = spn_promedios.get(SPN_NIVEL_ACEITE_PCT)
    if nivel_aceite and nivel_aceite["promedio"] < 30:
        score += 2
        factores.append("Nivel de aceite bajo — posible consumo excesivo o fuga")
        componentes_riesgo.add("circuito_aceite")
    
    # --- Anticongelante (SPN 111) ---
    anticongelante = spn_promedios.get(SPN_ANTICONGELANTE)
    if anticongelante and anticongelante["promedio"] < 40:
        score += 2
        factores.append("Nivel de anticongelante bajo — posible fuga en sistema de refrigeración")
        componentes_riesgo.add("sistema_refrigeracion")
    
    # --- Voltaje batería (SPN 168) ---
    voltaje = spn_promedios.get(SPN_VOLTAJE_BATERIA)
    if voltaje and voltaje["minimo"] < 22:
        score += 1
        factores.append("Voltaje de batería bajo — revisar alternador y batería")
        componentes_riesgo.add("sistema_electrico")
    
    # --- Nivel Urea (SPN 1761) ---
    urea = spn_promedios.get(SPN_NIVEL_UREA)
    if urea and urea["promedio"] < 15:
        score += 1
        factores.append("Nivel de urea bajo — requiere recarga para cumplimiento de emisiones")
        componentes_riesgo.add("sistema_escape")
    
    # --- Balatas (SPNs 1099-1104) ---
    for spn_balata in BALATAS_SPNS:
        balata = spn_promedios.get(spn_balata)
        if balata:
            if balata["promedio"] < 15:
                score += 2
                nombre = catalogo.get(spn_balata, {}).get("name", f"Balata SPN {spn_balata}").strip()
                factores.append(f"{nombre}: desgaste crítico ({balata['promedio']:.0f}% restante)")
                componentes_riesgo.add("sistema_frenos")
            elif balata["promedio"] < 30:
                score += 1
                nombre = catalogo.get(spn_balata, {}).get("name", f"Balata SPN {spn_balata}").strip()
                factores.append(f"{nombre}: desgaste avanzado ({balata['promedio']:.0f}% restante)")
                componentes_riesgo.add("sistema_frenos")
    
    # --- Fallas recientes (de data_fault) ---
    if fallas_recientes:
        for falla in fallas_recientes[:3]:
            severidad = falla.get("severidad", 1)
            score += severidad  # Severidad directa como score
            factores.append(
                f"Falla reciente: {falla.get('descripcion', falla.get('codigo', 'N/A'))} "
                f"(severidad: {severidad})"
            )
    
    # --- Clasificar ---
    if score <= 2:
        nivel = "BAJO"
        desc = "Señales dentro de parámetros normales"
        urgencia = "PROXIMO_SERVICIO"
    elif score <= 5:
        nivel = "MODERADO"
        desc = "Algunas señales requieren seguimiento"
        urgencia = "PROXIMO_SERVICIO"
    elif score <= 8:
        nivel = "ELEVADO"
        desc = "Patrón consistente con condiciones previas a eventos mecánicos"
        urgencia = "ESTA_SEMANA"
    else:
        nivel = "CRITICO"
        desc = "Múltiples señales de alerta activas — intervención recomendada"
        urgencia = "INMEDIATA"
    
    return {
        "nivel_riesgo": nivel,
        "descripcion_riesgo": desc,
        "urgencia_sugerida": urgencia,
        "factores_principales": factores,
        "componentes_en_riesgo": list(componentes_riesgo),
        "score_interno": score,  # Para debugging, no se muestra al usuario
    }
```

### Output

```json
{
  "autobus": "1089",
  "metodo_prediccion": "heuristico",
  "nivel_riesgo": "ELEVADO",
  "descripcion_riesgo": "Patrón consistente con condiciones previas a eventos mecánicos",
  "factores_principales": [
    "Engine Coolant Temperature: promedio significativamente por encima del máximo",
    "Engine Oil Pressure: promedio significativamente por debajo del mínimo",
    "Falla reciente: Temperatura de refrigerante por encima del rango (severidad: 3)"
  ],
  "componentes_en_riesgo": ["sistema_refrigeracion", "bomba_agua", "circuito_aceite"],
  "urgencia_sugerida": "ESTA_SEMANA"
}
```

---

## LAMBDA 7 — `tool-buscar-patrones-historicos`

### Propósito
Tool del Agente Mantenimiento. Busca en `data_fault` (S3) fallas históricas con patrones similares: mismo código de falla, mismo modelo/marca de bus, misma zona. Aprovecha los campos ricos de `data_fault` (modelo, submodelo, marca_comercial, region, zona, severidad).

### Clasificación
- **Grupo:** Tools Agente Mantenimiento
- **Prioridad:** 🟡 Importante
- **Día:** Día 3

### Especificación técnica

```yaml
Nombre:           tool-buscar-patrones-historicos
Runtime:          Python 3.12
Memoria:          512 MB
Timeout:          30 segundos
Trigger:          Bedrock AgentCore (Action Group)
Dependencias:     pandas, pyarrow (en layer) — o JSON/CSV como alternativa
```

### Input

```json
{
  "codigo": "SPN110-FMI0",
  "modelo": "IRIZAR i8",
  "marca_comercial": "ADO Platino"
}
```
*(modelo y marca_comercial son opcionales — mejoran la búsqueda)*

### Flujo de ejecución

```
1. Recibir codigo, y opcionalmente modelo, marca_comercial
2. Leer data_fault desde S3:
   s3://ado-telemetry-mvp/hackathon-data/fallas-simuladas/fallas_simuladas.parquet (o .json)
3. Filtrar fallas donde:
   - codigo == :codigo (match exacto o parcial)
   - Si modelo proporcionado: modelo == :modelo (priorizar, no excluir)
   - Si marca_comercial proporcionada: marca_comercial == :marca_comercial
4. Ordenar por fecha_hora (más recientes primero)
5. Limitar a top 10 eventos más relevantes
6. Calcular estadísticas del patrón:
   - Severidad promedio de fallas con este código
   - Modelos/marcas más afectados
   - Zonas/regiones con mayor incidencia
   - Duración promedio del evento (fecha_hora_fin - fecha_hora)
7. Retornar resumen
```

### Output

```json
{
  "codigo_buscado": "SPN110-FMI0",
  "filtro_modelo": "IRIZAR i8",
  "eventos_encontrados": 8,
  "patron_identificado": {
    "severidad_promedio": 2.8,
    "descripcion_patron": "Este código de falla se ha presentado con mayor frecuencia en unidades IRIZAR i8 de la marca ADO Platino, principalmente en la zona Sureste",
    "modelos_mas_afectados": ["IRIZAR i8", "VOLVO 9800"],
    "zonas_mayor_incidencia": ["Sureste", "Centro"],
    "duracion_promedio_evento": "2.5 horas",
    "servicios_afectados": ["Platino", "GL"]
  },
  "eventos_similares": [
    {
      "id": "FAULT-2026-001234",
      "autobus": "1089",
      "fecha_hora": "2026-04-20T08:15:00Z",
      "codigo": "SPN110-FMI0",
      "severidad": 3,
      "descripcion": "Temperatura de refrigerante por encima del rango",
      "modelo": "IRIZAR i8",
      "marca_comercial": "ADO Platino",
      "zona": "Centro",
      "region": "CDMX",
      "servicio": "Platino",
      "duracion": "3.2 horas"
    }
  ]
}
```

### Alternativa sin pandas
Si el layer de pandas/pyarrow es demasiado pesado:
- Convertir `data_fault` a JSON Lines en S3
- Leer con `boto3 s3.get_object()` + `json.loads()` línea por línea
- Filtrar en memoria (aceptable para ~500-1000 registros simulados)

---

## LAMBDA 8 — `tool-generar-recomendacion`

### Propósito
Tool del Agente Mantenimiento. Crea un registro de recomendación preventiva en `ado-alertas`. Incluye contexto del modelo/marca del bus desde `data_fault`.

### Clasificación
- **Grupo:** Tools Agente Mantenimiento
- **Prioridad:** 🔴 Crítica
- **Día:** Día 3

### Especificación técnica

```yaml
Nombre:           tool-generar-recomendacion
Runtime:          Python 3.12
Memoria:          256 MB
Timeout:          10 segundos
Trigger:          Bedrock AgentCore (Action Group)
```

### Input

```json
{
  "autobus": "1089",
  "diagnostico": "Señales consistentes con patrón previo a evento de refrigeración. Temperatura en tendencia ascendente con falla reciente SPN110-FMI0.",
  "nivel_riesgo": "ELEVADO",
  "urgencia": "ESTA_SEMANA",
  "componentes": ["bomba_agua", "termostato", "mangueras_refrigeracion"]
}
```

### Flujo de ejecución

```
1. Recibir parámetros del agente
2. Generar alerta_id: UUID v4
3. Generar numero_referencia: OT-{YYYY}-{MMDD}-{autobus}
   Ejemplo: OT-2026-0425-1089
4. Enriquecer con datos del bus (opcional — query rápido a DynamoDB):
   - viaje_ruta, operador_desc
5. Construir item para DynamoDB ado-alertas:
   - tipo_alerta = "MANTENIMIENTO"
   - estado = "ACTIVA"
   - agente_origen = "ado-agente-mantenimiento"
   - nivel_riesgo_cualitativo = mapeo del nivel
6. PutItem en ado-alertas
7. Retornar confirmación
```

### Output

```json
{
  "exito": true,
  "alerta_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "numero_referencia": "OT-2026-0425-1089",
  "autobus": "1089",
  "nivel_riesgo": "ELEVADO",
  "urgencia": "ESTA_SEMANA",
  "mensaje": "Recomendación preventiva generada exitosamente. Orden de trabajo OT-2026-0425-1089 creada para autobús 1089 con urgencia: esta semana."
}
```

---

## LAMBDA 9 — `ado-dashboard-api`

### Propósito
Backend para el dashboard. Sirve datos consolidados de DynamoDB para QuickSight o Streamlit. Traduce SPNs a nombres legibles para visualización.

### Clasificación
- **Grupo:** Dashboard / Presentación
- **Prioridad:** 🟡 Importante
- **Día:** Día 4

### Especificación técnica

```yaml
Nombre:           ado-dashboard-api
Runtime:          Python 3.12
Memoria:          256 MB
Timeout:          15 segundos
Trigger:          Amazon API Gateway (REST)
```

### Endpoints

| Método | Path | Descripción |
|---|---|---|
| GET | `/dashboard/flota-status` | Estado actual de todos los buses con SPNs traducidos |
| GET | `/dashboard/alertas-activas` | Alertas y recomendaciones activas |
| GET | `/dashboard/resumen-consumo` | Resumen de eficiencia por ruta |
| GET | `/dashboard/co2-estimado` | Métricas estimadas de CO₂ |

### Output — `/dashboard/flota-status`

```json
{
  "timestamp": "2026-04-25T14:35:00Z",
  "total_buses": 20,
  "buses_activos": 18,
  "resumen_estado": {
    "eficiente": 12,
    "alerta_moderada": 4,
    "alerta_significativa": 2
  },
  "buses": [
    {
      "autobus": "1247",
      "viaje_ruta": "MEX-PUE-001",
      "viaje_ruta_origen": "México",
      "viaje_ruta_destino": "Puebla",
      "operador": "García López Juan",
      "estado_consumo": "ALERTA_SIGNIFICATIVA",
      "spn_fuera_de_rango": 3,
      "ultimo_update": "2026-04-25T14:34:50Z"
    }
  ]
}
```

---

## Matriz de dependencias actualizada

```
                    ┌──────────────────────────┐
                    │  S3                       │
                    │  ├── telemetry-data       │
                    │  ├── motor_spn (catálogo) │
                    │  └── data_fault           │
                    └────────────┬─────────────┘
                                 │
                    ┌────────────▼─────────────┐
                    │  ado-simulador-telemetria │
                    │  (L1)                     │
                    │  Lee: telemetry-data + spn│
                    │  Escribe: DynamoDB        │
                    └────────────┬─────────────┘
                                 │
                    ┌────────────▼─────────────┐
                    │  DynamoDB                 │
                    │  ado-telemetria-live      │
                    │  (estado consolidado      │
                    │   con spn_valores Map)    │
                    └────────────┬─────────────┘
                                 │ leen
          ┌──────────────────────┼──────────────────────┐
          │                      │                      │
┌─────────▼────────┐  ┌─────────▼────────┐  ┌─────────▼────────┐
│ tool-consultar-   │  │ tool-calcular-   │  │ tool-consultar-  │
│ telemetria (L2)   │  │ desviacion (L3)  │  │ obd (L5)         │
│ Lee: DynamoDB+SPN │  │ Lee: DynamoDB+SPN│  │ Lee: DynamoDB+SPN│
└──────────────────┘  └──────────────────┘  │ + data_fault (S3)│
                                             └────────┬─────────┘
┌──────────────────┐  ┌──────────────────┐           │
│ tool-listar-     │  │ tool-buscar-     │  ┌────────▼─────────┐
│ buses-activos    │  │ patrones-hist.   │  │ tool-predecir-   │
│ (L4)             │  │ (L7)             │  │ evento (L6)      │
│ Lee: DynamoDB    │  │ Lee: data_fault  │  │ Lee: DynamoDB+SPN│
└──────────────────┘  │ (S3) — modelo,   │  │ + SageMaker      │
                      │ marca, zona,     │  └────────┬─────────┘
                      │ severidad        │           │
                      └──────────────────┘  ┌────────▼─────────┐
                                            │ tool-generar-    │
                                            │ recomendacion    │
                                            │ (L8)             │
                                            │ Escribe:         │
                                            │ ado-alertas      │
                                            └────────┬─────────┘
                                                     │
                                            ┌────────▼─────────┐
                                            │ ado-dashboard-   │
                                            │ api (L9)         │
                                            │ Lee: ambas tablas│
                                            │ + catálogo SPN   │
                                            └──────────────────┘
```

---

## Orden de implementación

### Día 1 — Fundación
| # | Lambda | Dependencia previa | Notas |
|---|---|---|---|
| 0 | — | Subir motor_spn.json, telemetry-data y data_fault a S3 | Pre-requisito |
| 1 | `ado-simulador-telemetria` | S3 poblado, DynamoDB creada | Lo más complejo del día: pivoteo de SPNs |

### Día 2 — Agente Combustible
| # | Lambda | Dependencia previa | Notas |
|---|---|---|---|
| 2 | `tool-consultar-telemetria` | DynamoDB con datos | Empezar aquí — la más directa |
| 3 | `tool-calcular-desviacion` | DynamoDB + catálogo SPN | Lógica de negocio con rangos del catálogo |
| 4 | `tool-listar-buses-activos` | DynamoDB con datos | Query con GSI |

### Día 3 — Agente Mantenimiento
| # | Lambda | Dependencia previa | Notas |
|---|---|---|---|
| 5 | `tool-consultar-obd` | DynamoDB + data_fault en S3 | Cruza telemetría con fallas |
| 6 | `tool-predecir-evento` | DynamoDB + SageMaker (o fallback) | Implementar fallback primero |
| 7 | `tool-buscar-patrones-historicos` | data_fault en S3 | Búsqueda por código, modelo, marca, zona |
| 8 | `tool-generar-recomendacion` | DynamoDB tabla ado-alertas | La más simple del grupo |

### Día 4 — Dashboard
| # | Lambda | Dependencia previa | Notas |
|---|---|---|---|
| 9 | `ado-dashboard-api` | Ambas tablas DynamoDB | Solo si se usa Streamlit |

---

## Estimación de esfuerzo (actualizada)

| Lambda | Complejidad | Tiempo | Riesgo | Cambio vs original |
|---|---|---|---|---|
| `ado-simulador-telemetria` | **Alta** | 4-5h | Alto | ⬆️ Pivoteo de SPNs es nuevo |
| `tool-consultar-telemetria` | Baja-Media | 1.5h | Bajo | ⬆️ Traducción de SPNs |
| `tool-calcular-desviacion` | Media | 2-3h | Medio | ⬆️ Rangos dinámicos del catálogo |
| `tool-listar-buses-activos` | Baja | 1.5h | Bajo | ~ Similar |
| `tool-consultar-obd` | **Media-Alta** | 3h | Medio | ⬆️ Cruce con data_fault |
| `tool-predecir-evento` | **Alta** | 3-4h | Alto | ⬆️ Features desde SPNs dinámicos |
| `tool-buscar-patrones-historicos` | Media | 2-3h | Medio | ⬆️ Campos ricos de data_fault |
| `tool-generar-recomendacion` | Baja | 1h | Bajo | ~ Similar |
| `ado-dashboard-api` | Media | 2-3h | Medio | ⬆️ Traducción SPNs para UI |
| **TOTAL** | | **~21-27h** | | |

---

## Riesgos y mitigaciones (actualizado con datos reales)

| Riesgo | Impacto | Mitigación |
|---|---|---|
| ~~No conocemos los SPN IDs~~ | ~~Todas las Lambdas fallan~~ | ✅ RESUELTO — 36 SPNs mapeados con IDs, rangos y unidades |
| Telemetría tiene ~20+ SPNs por lectura → DynamoDB item grande | Simulador lento o item > 400KB | Filtrar con `SPNS_DEMO_PRIORITARIOS` (21 SPNs) + campos planos |
| data_fault es muy grande para leer en Lambda | L5 y L7 timeout | Convertir a JSON Lines, o pre-indexar en DynamoDB auxiliar |
| Rangos del catálogo son muy amplios (ej: Presión Aceite 0-1000 kPa) | Pocas alertas "fuera de rango" | Usar umbrales operativos internos más estrictos que los del catálogo |
| `variable_tipo` solo tiene EDA/inicio_fin — no hay categorías funcionales | Filtrado por tipo no funciona | ✅ RESUELTO — clasificación funcional definida en `SPNS_COMBUSTIBLE` y `SPNS_MANTENIMIENTO` |
| Campo `delta` puede no ser confiable para detección de anomalías | Falsos positivos | Usar 2x delta como umbral conservador |
| SageMaker no listo para Día 3 | L6 sin ML | ✅ Fallback heurístico diseñado con SPNs reales |
| Layer de pandas/pyarrow excede 250 MB | L7 no funciona | Usar JSON/CSV en lugar de Parquet para data_fault |

---

## ✅ Tarea Día 0 — COMPLETADA

Los datos del catálogo SPN han sido explorados y mapeados. Hallazgos:

1. **36 SPNs confirmados** — 26 tipo `EDA` (tiempo real) + 10 tipo `inicio_fin` (acumuladores)
2. **`variable_tipo` solo tiene 2 valores:** `EDA` e `inicio_fin` — la clasificación funcional (combustible vs mantenimiento) la definimos nosotros en `spn_catalog.py`
3. **Campo `delta`** disponible para detección de anomalías entre lecturas consecutivas
4. **Balatas (6 SPNs):** Dato valioso para mantenimiento predictivo de frenos
5. **Rendimiento directo (SPN 185):** Métrica km/L disponible — más útil que calcular desde tasa de combustible
6. **Nivel de Urea (SPN 1761):** Relevante para emisiones y NOM-044

### Pendiente para Día 0
- Explorar `telemetry-data` real en S3: confirmar cuántos buses, formato de `viaje_ruta`, cantidad de registros por bus
- Explorar `data_fault` real en S3: confirmar formato de `codigo`, valores de `severidad`, modelos y marcas disponibles
