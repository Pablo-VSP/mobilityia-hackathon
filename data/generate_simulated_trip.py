"""
Genera un viaje simulado de 5 minutos (300 frames, 1 por segundo).
- Toma datos del bus desde posibles_viajes.JSON (primer registro)
- Usa un fragmento continuo de la ruta GPS (sin saltos grandes)
- Genera SPNs variados por segundo (no todos en cada frame, como datos reales)
- Anomalías inyectadas en ventanas específicas
- Formato compatible con viajes_consolidados.json para Lambda ado-simulador-telemetria
"""
import json
import random
import math

# Cargar posibles viajes y tomar el primero
with open('posibles_viajes.JSON', 'r', encoding='utf-8') as f:
    posibles = json.load(f)

viaje_info = posibles[0]

# Detectar ida o regreso
if viaje_info['VIAJE_RUTA_ORIGEN'] == "ACAPULCO COSTERA":
    gps_file = 'data/ruta_regreso_2725965.json'
    tipo = "regreso"
else:
    gps_file = 'data/ruta_ida_2704712.json'
    tipo = "ida"

# Cargar ruta GPS
with open(gps_file, 'r', encoding='utf-8') as f:
    ruta = json.load(f)

coordenadas = ruta["coordenadas"]

# Configuración
DURACION_SEGUNDOS = 300  # 5 minutos
TOTAL_FRAMES = 300       # 1 frame por segundo

# Tomar un fragmento continuo de la ruta GPS (no toda la ruta)
# Elegimos un segmento del 20% al 23% de la ruta (~fragmento de carretera)
inicio_pct = 0.20
fin_pct = inicio_pct + (TOTAL_FRAMES / len(coordenadas))
idx_inicio = int(len(coordenadas) * inicio_pct)
idx_fin = idx_inicio + TOTAL_FRAMES

# Si no hay suficientes puntos, interpolar
if idx_fin > len(coordenadas):
    idx_fin = len(coordenadas)
    idx_inicio = idx_fin - TOTAL_FRAMES

fragmento_gps = coordenadas[idx_inicio:idx_fin]

# Si el fragmento es menor a 300, interpolar linealmente
while len(fragmento_gps) < TOTAL_FRAMES:
    fragmento_gps.append(fragmento_gps[-1])

print(f"Viaje seleccionado:")
print(f"  Bus: {viaje_info['Autobus']}")
print(f"  Operador: {viaje_info['Operador_Desc']}")
print(f"  Ruta: {viaje_info['VIAJE_RUTA']}")
print(f"  Tipo: {tipo}")
print(f"  Fragmento GPS: indices {idx_inicio}-{idx_fin} de {len(coordenadas)} puntos")
print()

# Definición de SPNs
SPN_DEFS = {
    "84":   {"name": "Velocidad Km/h",             "unidad": "km/h", "normal": (70, 90),    "freq": 0.7},
    "190":  {"name": "RPM",                        "unidad": "rpm",  "normal": (900, 1400), "freq": 0.7},
    "91":   {"name": "Posicion Pedal Acelerador",  "unidad": "%",    "normal": (25, 55),    "freq": 0.4},
    "521":  {"name": "Posicion Pedal Freno",       "unidad": "%",    "normal": (0, 5),      "freq": 0.2},
    "183":  {"name": "Tasa de combustible",        "unidad": "L/h",  "normal": (15, 35),    "freq": 0.5},
    "185":  {"name": "Rendimiento",                "unidad": "km/L", "normal": (3.0, 4.5),  "freq": 0.4},
    "96":   {"name": "Nivel Combustible",          "unidad": "%",    "normal": (60, 85),    "freq": 0.1},
    "513":  {"name": "Porcentaje Torque",          "unidad": "%",    "normal": (25, 55),    "freq": 0.4},
    "110":  {"name": "Temperatura Motor",          "unidad": "°C",   "normal": (85, 98),    "freq": 0.3},
    "175":  {"name": "Temperatura Aceite Motor",   "unidad": "°C",   "normal": (90, 110),   "freq": 0.5},
    "100":  {"name": "Presion Aceite Motor",       "unidad": "kPa",  "normal": (300, 550),  "freq": 0.3},
    "98":   {"name": "Nivel de aceite",            "unidad": "%",    "normal": (70, 95),    "freq": 0.05},
    "111":  {"name": "Nivel de anticongelante",    "unidad": "%",    "normal": (80, 100),   "freq": 0.03},
    "168":  {"name": "Voltaje Bateria",            "unidad": "V",    "normal": (13.2, 14.2),"freq": 0.1},
    "917":  {"name": "Odometro",                   "unidad": "km",   "normal": (520000, 520000), "freq": 0.5},
    "1761": {"name": "Nivel Urea",                 "unidad": "%",    "normal": (65, 80),    "freq": 0.05},
    "1099": {"name": "Balata delantero izquierdo", "unidad": "%",    "normal": (55, 70),    "freq": 0.02},
    "1100": {"name": "Balata delantero derecho",   "unidad": "%",    "normal": (55, 70),    "freq": 0.02},
    "1101": {"name": "Balata trasero izquierdo 1", "unidad": "%",    "normal": (50, 65),    "freq": 0.02},
    "1102": {"name": "Balata trasero derecho 1",   "unidad": "%",    "normal": (50, 65),    "freq": 0.02},
    "1103": {"name": "Balata trasero izquierdo 2", "unidad": "%",    "normal": (50, 65),    "freq": 0.02},
    "1104": {"name": "Balata trasero derecho 2",   "unidad": "%",    "normal": (50, 65),    "freq": 0.02},
}

# Estado persistente para suavizar valores entre frames
state = {}
for spn_id, cfg in SPN_DEFS.items():
    low, high = cfg["normal"]
    if spn_id == "917":
        state[spn_id] = 520000.0
    elif spn_id == "96":
        state[spn_id] = 82.0
    else:
        state[spn_id] = (low + high) / 2.0

# Anomalías: definidas como rangos de segundos con SPNs forzados
# Segundo 90-120: Conducción agresiva
# Segundo 180-210: Riesgo mecánico
# Segundo 250-280: Velocidad excesiva
def get_anomaly_overrides(segundo):
    overrides = {}
    if 90 <= segundo <= 120:
        # Conducción agresiva
        t = (segundo - 90) / 30.0  # 0 a 1
        overrides["91"] = 82.0 + random.uniform(0, 10)
        overrides["183"] = 58.0 + random.uniform(0, 15)
        overrides["185"] = 1.5 + random.uniform(0, 0.5)
        overrides["513"] = 88.0 + random.uniform(0, 8)
        if segundo > 110:
            overrides["521"] = 40.0 + random.uniform(0, 20)
    elif 180 <= segundo <= 210:
        # Riesgo mecánico
        overrides["110"] = 122.0 + random.uniform(0, 15)
        overrides["175"] = 130.0 + random.uniform(0, 10)
        overrides["100"] = 100.0 + random.uniform(0, 50)
        overrides["168"] = 11.0 + random.uniform(0, 1)
    elif 250 <= segundo <= 280:
        # Velocidad excesiva
        overrides["84"] = 122.0 + random.uniform(0, 12)
        overrides["190"] = 2500.0 + random.uniform(0, 300)
        overrides["91"] = 75.0 + random.uniform(0, 10)
        overrides["183"] = 52.0 + random.uniform(0, 12)
        overrides["185"] = 1.6 + random.uniform(0, 0.5)
    return overrides


def smooth_value(spn_id, target, max_delta=None):
    """Suaviza el valor actual hacia el target con inercia."""
    current = state[spn_id]
    if max_delta is None:
        low, high = SPN_DEFS[spn_id]["normal"]
        max_delta = (high - low) * 0.15
    diff = target - current
    change = max(min(diff, max_delta), -max_delta)
    new_val = current + change + random.uniform(-max_delta * 0.1, max_delta * 0.1)
    state[spn_id] = new_val
    return round(new_val, 1)


def generate_frame(frame_idx):
    segundo = frame_idx  # 1 frame = 1 segundo
    lat, lon = fragmento_gps[frame_idx]
    
    anomalies = get_anomaly_overrides(segundo)
    
    # Seleccionar qué SPNs aparecen en este frame (basado en frecuencia)
    spn_valores = {}
    for spn_id, cfg in SPN_DEFS.items():
        # Si hay anomalía para este SPN, forzar que aparezca
        if spn_id in anomalies:
            valor = smooth_value(spn_id, anomalies[spn_id])
            spn_valores[spn_id] = {
                "valor": valor,
                "name": cfg["name"],
                "unidad": cfg["unidad"]
            }
        elif random.random() < cfg["freq"]:
            # Generar valor normal suavizado
            low, high = cfg["normal"]
            if spn_id == "917":
                state[spn_id] += random.uniform(0.01, 0.04)
                valor = round(state[spn_id], 1)
            elif spn_id == "96":
                state[spn_id] -= random.uniform(0.001, 0.01)
                valor = round(state[spn_id], 1)
            else:
                target = random.uniform(low, high)
                valor = smooth_value(spn_id, target)
            
            spn_valores[spn_id] = {
                "valor": valor,
                "name": cfg["name"],
                "unidad": cfg["unidad"]
            }
    
    # Asegurar que siempre haya al menos 3 SPNs por frame
    if len(spn_valores) < 3:
        for spn_id in ["84", "190", "175"]:
            if spn_id not in spn_valores:
                cfg = SPN_DEFS[spn_id]
                low, high = cfg["normal"]
                valor = smooth_value(spn_id, random.uniform(low, high))
                spn_valores[spn_id] = {"valor": valor, "name": cfg["name"], "unidad": cfg["unidad"]}
    
    return {
        "offset": frame_idx,
        "segundos_desde_inicio": segundo,
        "latitud": round(lat, 6),
        "longitud": round(lon, 6),
        "spn_valores": spn_valores
    }


# Generar 300 frames (1 por segundo)
frames = [generate_frame(i) for i in range(TOTAL_FRAMES)]

# Construir viaje
viaje = {
    "viaje_id": 9000001,
    "autobus": viaje_info["Autobus"],
    "operador_cve": viaje_info["Operador_Cve"],
    "operador_desc": viaje_info["Operador_Desc"],
    "viaje_ruta": viaje_info["VIAJE_RUTA"],
    "viaje_ruta_origen": viaje_info["VIAJE_RUTA_ORIGEN"],
    "viaje_ruta_destino": viaje_info["VIAJE_RUTA_DESTINO"],
    "total_frames": TOTAL_FRAMES,
    "duracion_segundos": DURACION_SEGUNDOS,
    "frames": frames
}

output = {
    "viajes": [viaje],
    "metadata": {
        "total_viajes": 1,
        "spns_disponibles": sorted([int(k) for k in SPN_DEFS.keys()]),
        "total_spns": len(SPN_DEFS),
        "generado": "2026-04-28T17:00:00Z",
        "descripcion": "Viaje simulado 5 min, 1 frame/seg, fragmento GPS continuo, anomalias inyectadas"
    }
}

with open('data/viaje_simulado_demo.json', 'w', encoding='utf-8') as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

# Stats
spns_por_frame = [len(f["spn_valores"]) for f in frames]
print("=== VIAJE SIMULADO GENERADO ===")
print(f"Archivo: data/viaje_simulado_demo.json")
print(f"Bus: {viaje_info['Autobus']} | Operador: {viaje_info['Operador_Desc']}")
print(f"Ruta: {viaje_info['VIAJE_RUTA']} ({tipo})")
print(f"Duración: {DURACION_SEGUNDOS}s (5 min) | Frames: {TOTAL_FRAMES} (1/seg)")
print(f"SPNs por frame: min={min(spns_por_frame)}, max={max(spns_por_frame)}, avg={sum(spns_por_frame)/len(spns_por_frame):.1f}")
print()
print("=== ANOMALÍAS ===")
print("  90-120s: Conducción agresiva (acelerador, tasa combustible, rendimiento bajo)")
print("  180-210s: Riesgo mecánico (temp motor/aceite alta, presión aceite baja, voltaje bajo)")
print("  250-280s: Velocidad excesiva (>120 km/h, RPM >2500, rendimiento bajo)")
