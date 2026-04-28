# 📂 data/ — Datos de Telemetría y Herramientas de Análisis

## Estructura de la carpeta

```
data/
├── consolidated_telemetry.parquet   ← Dataset consolidado (NO versionado en Git)
├── trap_trips_dynamo.json           ← 5 viajes trampa pivoteados para DynamoDB
├── analyze_data.py                  ← Resumen estadístico del consolidado
├── find_trap_trips.py               ← Buscador de viajes candidatos para datos trampa
├── generate_trap_data.py            ← Generador de JSON para inyección en DynamoDB
└── README.md                        ← Este archivo
```

---

## ⚠️ Archivo consolidado — Descarga manual requerida

El archivo `consolidated_telemetry.parquet` está excluido de Git (`.gitignore`) por su tamaño.

Para obtenerlo:

1. Descargar `consolidated_telemetry.zip` desde la carpeta compartida en la nube del equipo.
2. Descomprimir el ZIP. Debe generar el archivo `consolidated_telemetry.parquet`.
3. Colocar el `.parquet` (no el ZIP) en la raíz de `data/` dentro del proyecto:
   ```
   mobilityia-hackathon/data/consolidated_telemetry.parquet
   ```
4. Verificar que se lee correctamente:
   ```bash
   cd data
   python analyze_data.py
   ```

> **Importante:** No colocar el `.zip` en la carpeta `data/`. Solo el `.parquet` descomprimido.

### Características del dataset

| Atributo | Valor |
|---|---|
| Registros totales | 27,415,659 |
| Buses únicos | 19 |
| Viajes únicos | 1,432 |
| Operadores únicos | 50 |
| SPNs (sensores) | 30 |
| Rutas | 2 (México Taxqueña ↔ Acapulco Costera) |
| Rango temporal | Octubre 2020 — Enero 2021 |
| Columnas | 17 (esquema telemetry-data estándar del proyecto) |

### Columnas del Parquet

| Columna | Tipo | Descripción |
|---|---|---|
| `VIAJE_ID` | int64 | Identificador único del viaje |
| `Autobus` | int64 | Número económico del autobús |
| `Operador_Cve` | string | Clave del operador/conductor |
| `Operador_Desc` | string | Nombre del operador/conductor |
| `EVENTO_FECHA` | string | Fecha del evento (YYYY-MM-DD) |
| `EVENTO_FECHA_HORA` | datetime64 | Timestamp exacto de la lectura |
| `EVENTO_SPN` | int64 | SPN ID del sensor leído |
| `EVENTO_DESCRIPCION` | string | Nombre legible del sensor |
| `EVENTO_VALOR` | float64 | Valor numérico de la lectura |
| `EVENTO_LATITUD` | float64 | Coordenada GPS latitud |
| `EVENTO_LONGITUD` | float64 | Coordenada GPS longitud |
| `VIAJE_RUTA` | string | Nombre completo de la ruta |
| `VIAJE_RUTA_ORIGEN` | string | Ciudad origen |
| `VIAJE_RUTA_DESTINO` | string | Ciudad destino |
| `EVENTO_PROTOCOLO` | string | Protocolo de comunicación (J1939) |
| `EVENTO_FIRMWARE` | string | Versión de firmware del dispositivo |
| `EVENTO_VERSION` | int64 | Versión del evento |

---

## 🔍 find_trap_trips.py — Buscador de viajes candidatos

Analiza el consolidado y muestra los mejores candidatos por cada perfil de anomalía, ordenados por un score de severidad.

### Uso

```bash
cd data
python find_trap_trips.py --mes 1 --anio 2021 --top 10
```

### Parámetros

| Parámetro | Tipo | Default | Descripción |
|---|---|---|---|
| `--mes` | int | 1 | Mes a filtrar (1-12) |
| `--anio` | int | 2021 | Año a filtrar |
| `--top` | int | 10 | Cantidad de candidatos a mostrar por perfil |

### Perfiles que busca

| Perfil | Qué busca | SPNs clave | Nivel esperado |
|---|---|---|---|
| 1 — Aceite/Motor | Presión aceite baja + temp motor alta | SPN 100, SPN 110 | CRITICO |
| 2 — Voltaje | Voltaje batería bajo + sin alternador | SPN 168, SPN 20000 | ELEVADO |
| 3 — Frenos | Balatas desgastadas o uso excesivo de freno | SPN 1099-1104, SPN 521 | ELEVADO |
| 4 — Normal | Todas las señales dentro de rango | SPN 100, SPN 110 | BAJO |
| 5 — Mixto | Múltiples señales leves simultáneas | SPN 175, SPN 190, SPN 96 | MODERADO |

### Salida

Imprime en consola los `VIAJE_ID` candidatos con sus métricas. Anotar los IDs deseados para pasarlos al siguiente script.

---

## 🔧 generate_trap_data.py — Generador de JSON para DynamoDB

Toma una lista de `VIAJE_ID`, los pivotea al formato de la tabla `ado-telemetria-live` y genera un JSON listo para inyectar.

### Uso

```bash
cd data
python generate_trap_data.py --mes 1 --anio 2021 --viajes 2689828,2702063,2734771,2737103,2710211
```

### Parámetros

| Parámetro | Tipo | Default | Descripción |
|---|---|---|---|
| `--mes` | int | 1 | Mes a filtrar (1-12) |
| `--anio` | int | 2021 | Año a filtrar |
| `--viajes` | string | *requerido* | Lista de VIAJE_IDs separados por coma |
| `--output` | string | `trap_trips_dynamo.json` | Nombre del archivo de salida |

### Formato de salida

Cada item del JSON tiene la estructura exacta de `ado-telemetria-live`:

```json
{
  "autobus": "7309",
  "viaje_id": 2689828,
  "operador_cve": "...",
  "operador_desc": "...",
  "viaje_ruta": "MEXICO TAXQUENA - ACAPULCO COSTERA",
  "viaje_ruta_origen": "MEXICO TAXQUENA",
  "viaje_ruta_destino": "ACAPULCO COSTERA",
  "latitud": 17.422,
  "longitud": -99.465,
  "spn_valores": {
    "100": {"valor": 264.0, "name": "Presion Aceite Motor", "unidad": "kPa", "fuera_de_rango": false},
    "110": {"valor": 83.0, "name": "Temperatura Motor", "unidad": "C", "fuera_de_rango": false}
  },
  "alertas_spn": [],
  "velocidad_kmh": 84.1,
  "rpm": 1135.88,
  "presion_aceite_kpa": 264.0,
  "temperatura_motor_c": 83.0,
  "estado_consumo": "ALERTA_SIGNIFICATIVA",
  "timestamp": "PLACEHOLDER_TIMESTAMP",
  "ttl_expiry": 0
}
```

> Los campos `timestamp` y `ttl_expiry` son placeholders. Se sobreescriben al momento de inyectar en DynamoDB.

### Inyección en DynamoDB

```python
import boto3
import json
import time
from datetime import datetime, timezone

table = boto3.resource('dynamodb', region_name='us-east-2').Table('ado-telemetria-live')

with open('data/trap_trips_dynamo.json', encoding='utf-8') as f:
    items = json.load(f)

for item in items:
    item['timestamp'] = datetime.now(timezone.utc).isoformat()
    item['ttl_expiry'] = int(time.time()) + 86400
    table.put_item(Item=json.loads(json.dumps(item), parse_float=str))
    print(f"Inyectado: Bus {item['autobus']} | Viaje {item['viaje_id']}")
```

> **Nota:** DynamoDB no acepta `float` nativo de Python. El snippet usa `parse_float=str` para convertir los valores numéricos a `Decimal` compatible. Si se usa `boto3` con la capa de serialización por defecto, considerar usar `TypeDeserializer`/`TypeSerializer` o la librería `dynamodb-json`.

---

## 📋 Viajes trampa seleccionados (Enero 2021)

El archivo `trap_trips_dynamo.json` actual contiene estos 5 viajes:

| # | VIAJE_ID | Bus | Perfil | Nivel esperado | Señal clave |
|---|---|---|---|---|---|
| 1 | 2689828 | 7309 | Aceite/Motor | CRITICO | Presión aceite mín 4 kPa, 281/999 lecturas bajo 200 kPa |
| 2 | 2702063 | 7303 | Voltaje | ELEVADO | Voltaje bat mín 17.6V, 44/178 lecturas bajo 26V |
| 3 | 2734771 | 7303 | Frenos | ELEVADO | 81/337 lecturas freno >30%, promedio 18.6% |
| 4 | 2737103 | 7305 | Normal | BAJO | Todas las señales dentro de rango |
| 5 | 2710211 | 7317 | Mixto | MODERADO | Combustible mín 12.8%, temp aceite cerca del límite |

---

## 🔄 Flujo de trabajo para generar nuevos datos trampa

```
1. Ejecutar find_trap_trips.py con el mes/año deseado
       ↓
2. Revisar candidatos, anotar los VIAJE_IDs
       ↓
3. Ejecutar generate_trap_data.py con los IDs seleccionados
       ↓
4. Inyectar el JSON resultante en DynamoDB
```

### Ejemplo completo para otro periodo

```bash
# Buscar candidatos en diciembre 2020
python find_trap_trips.py --mes 12 --anio 2020 --top 5

# Generar JSON con los viajes elegidos
python generate_trap_data.py --mes 12 --anio 2020 --viajes 123456,789012,345678 --output trap_dic2020.json
```

---

## Dependencias

- Python 3.9+
- pandas
- numpy
- pyarrow (para leer Parquet)
