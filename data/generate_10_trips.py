"""
Genera 10 viajes simulados de 5 minutos cada uno.
- Todos ocurren el mismo día: 15 de enero 2021
- Horarios casi simultáneos (separados por 1-2 minutos de inicio)
- Fragmentos GPS distribuidos SIN solaparse a lo largo de la ruta
- Buses/operadores aleatorios de posibles_viajes.JSON
- Formato compatible con viajes_consolidados.json
"""
import json
import random
from datetime import datetime, timedelta

# Cargar datos
with open('posibles_viajes.JSON', 'r', encoding='utf-8') as f:
    posibles = json.load(f)

with open('data/ruta_ida_2704712.json', 'r', encoding='utf-8') as f:
    ruta_ida = json.load(f)

with open('data/ruta_regreso_2725965.json', 'r', encoding='utf-8') as f:
    ruta_regreso = json.load(f)

# Configuración
NUM_VIAJES = 10
DURACION_SEGUNDOS = 300
TOTAL_FRAMES = 300

# Fecha base: 15 enero 2021, todos inician entre 14:00 y 14:15
FECHA_BASE = datetime(2021, 1, 15, 14, 0, 0)

# Seleccionar 10 viajes aleatorios (sin repetir bus)
random.shuffle(posibles)
seleccionados = []
buses_usados = set()
for v in posibles:
    if v["Autobus"] not in buses_usados:
        seleccionados.append(v)
        buses_usados.add(v["Autobus"])
    if len(seleccionados) == NUM_VIAJES:
        break

# Separar en ida y regreso
viajes_ida = [v for v in seleccionados if v["VIAJE_RUTA_ORIGEN"] == "MEXICO TAXQUENA"]
viajes_regreso = [v for v in seleccionados if v["VIAJE_RUTA_ORIGEN"] == "ACAPULCO COSTERA"]

print(f"Viajes de ida: {len(viajes_ida)}")
print(f"Viajes de regreso: {len(viajes_regreso)}")
print()

# Distribuir fragmentos GPS sin solaparse
# Cada viaje usa 300 puntos GPS. Dejamos un gap de 200 puntos entre cada uno.
FRAGMENT_SIZE = 300
GAP = 200  # puntos de separación entre fragmentos

def assign_gps_fragments(viajes_list, coordenadas):
    """Asigna fragmentos GPS distribuidos sin solaparse."""
    n = len(viajes_list)
    if n == 0:
        return []
    
    total_needed = n * FRAGMENT_SIZE + (n - 1) * GAP
    available = len(coordenadas)
    
    # Calcular inicio para centrar los fragmentos en la ruta
    if total_needed > available:
        # Reducir gap si no cabe
        gap = max(50, (available - n * FRAGMENT_SIZE) // (n + 1))
    else:
        gap = (available - n * FRAGMENT_SIZE) // (n + 1)
    
    fragments = []
    for i in range(n):
        start = gap + i * (FRAGMENT_SIZE + gap)
        end = start + FRAGMENT_SIZE
        if end > available:
            start = available - FRAGMENT_SIZE
            end = available
        fragments.append(coordenadas[start:end])
    
    return fragments

fragments_ida = assign_gps_fragments(viajes_ida, ruta_ida["coordenadas"])
fragments_regreso = assign_gps_fragments(viajes_regreso, ruta_regreso["coordenadas"])

# SPNs
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

ANOMALY_TYPES = [
    {
        "nombre": "Conducción agresiva",
        "overrides": lambda: {
            "91": 82.0 + random.uniform(0, 10),
            "183": 58.0 + random.uniform(0, 15),
            "185": 1.5 + random.uniform(0, 0.5),
            "513": 88.0 + random.uniform(0, 8),
        }
    },
    {
        "nombre": "Riesgo mecánico",
        "overrides": lambda: {
            "110": 122.0 + random.uniform(0, 15),
            "175": 130.0 + random.uniform(0, 10),
            "100": 100.0 + random.uniform(0, 50),
            "168": 11.0 + random.uniform(0, 1),
        }
    },
    {
        "nombre": "Velocidad excesiva",
        "overrides": lambda: {
            "84": 122.0 + random.uniform(0, 12),
            "190": 2500.0 + random.uniform(0, 300),
            "91": 75.0 + random.uniform(0, 10),
            "183": 52.0 + random.uniform(0, 12),
            "185": 1.6 + random.uniform(0, 0.5),
        }
    },
    {
        "nombre": "Frenado brusco",
        "overrides": lambda: {
            "521": 55.0 + random.uniform(0, 25),
            "84": 30.0 + random.uniform(0, 20),
            "190": 600.0 + random.uniform(0, 200),
        }
    },
    {
        "nombre": "Balatas desgastadas",
        "overrides": lambda: {
            "1099": 12.0 + random.uniform(0, 8),
            "1100": 14.0 + random.uniform(0, 8),
            "1101": 10.0 + random.uniform(0, 5),
            "1102": 18.0 + random.uniform(0, 5),
        }
    },
]


def generate_trip(viaje_info, viaje_idx, fragmento_gps, hora_inicio):
    """Genera un viaje completo."""
    state = {}
    for spn_id, cfg in SPN_DEFS.items():
        low, high = cfg["normal"]
        if spn_id == "917":
            state[spn_id] = 520000.0 + viaje_idx * 5000
        elif spn_id == "96":
            state[spn_id] = 75.0 + random.uniform(0, 10)
        else:
            state[spn_id] = (low + high) / 2.0 + random.uniform(-3, 3)
    
    # Anomalías aleatorias (2-3 por viaje)
    num_anomalias = random.randint(2, 3)
    anomalias_sel = random.sample(ANOMALY_TYPES, num_anomalias)
    ventanas = []
    for anom in anomalias_sel:
        for _ in range(50):
            inicio = random.randint(30, 250)
            fin = inicio + random.randint(20, 35)
            if fin > 295:
                fin = 295
            solapa = any(not (fin < v[0] or inicio > v[1]) for v in ventanas)
            if not solapa:
                ventanas.append((inicio, fin, anom))
                break
    
    def get_overrides(segundo):
        for inicio, fin, anom in ventanas:
            if inicio <= segundo <= fin:
                return anom["overrides"]()
        return {}
    
    def smooth_value(spn_id, target):
        current = state[spn_id]
        low, high = SPN_DEFS[spn_id]["normal"]
        max_delta = (high - low) * 0.15
        diff = target - current
        change = max(min(diff, max_delta), -max_delta)
        new_val = current + change + random.uniform(-max_delta * 0.1, max_delta * 0.1)
        state[spn_id] = new_val
        return round(new_val, 1)
    
    frames = []
    for frame_idx in range(TOTAL_FRAMES):
        lat, lon = fragmento_gps[frame_idx]
        anomalies = get_overrides(frame_idx)
        
        spn_valores = {}
        for spn_id, cfg in SPN_DEFS.items():
            if spn_id in anomalies:
                valor = smooth_value(spn_id, anomalies[spn_id])
                spn_valores[spn_id] = {"valor": valor, "name": cfg["name"], "unidad": cfg["unidad"]}
            elif random.random() < cfg["freq"]:
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
                spn_valores[spn_id] = {"valor": valor, "name": cfg["name"], "unidad": cfg["unidad"]}
        
        if len(spn_valores) < 3:
            for spn_id in ["84", "190", "175"]:
                if spn_id not in spn_valores:
                    cfg = SPN_DEFS[spn_id]
                    low, high = cfg["normal"]
                    valor = smooth_value(spn_id, random.uniform(low, high))
                    spn_valores[spn_id] = {"valor": valor, "name": cfg["name"], "unidad": cfg["unidad"]}
        
        frames.append({
            "offset": frame_idx,
            "segundos_desde_inicio": frame_idx,
            "latitud": round(lat, 6),
            "longitud": round(lon, 6),
            "spn_valores": spn_valores
        })
    
    viaje_obj = {
        "viaje_id": 9000001 + viaje_idx,
        "autobus": viaje_info["Autobus"],
        "operador_cve": viaje_info["Operador_Cve"],
        "operador_desc": viaje_info["Operador_Desc"],
        "viaje_ruta": viaje_info["VIAJE_RUTA"],
        "viaje_ruta_origen": viaje_info["VIAJE_RUTA_ORIGEN"],
        "viaje_ruta_destino": viaje_info["VIAJE_RUTA_DESTINO"],
        "fecha": "2021-01-15",
        "hora_inicio": hora_inicio.strftime("%H:%M:%S"),
        "total_frames": TOTAL_FRAMES,
        "duracion_segundos": DURACION_SEGUNDOS,
        "frames": frames
    }
    
    anomalias_desc = [(inicio, fin, anom["nombre"]) for inicio, fin, anom in ventanas]
    return viaje_obj, anomalias_desc


# Generar viajes
viajes = []
viaje_global_idx = 0

print("=== GENERANDO 10 VIAJES — 15 ENERO 2021, ~14:00 hrs ===\n")

# Viajes de ida
for i, viaje_info in enumerate(viajes_ida):
    hora = FECHA_BASE + timedelta(minutes=random.randint(0, 10))
    viaje_obj, anomalias = generate_trip(viaje_info, viaje_global_idx, fragments_ida[i], hora)
    viajes.append(viaje_obj)
    tipo = "ida"
    print(f"Viaje {viaje_global_idx+1}: Bus {viaje_info['Autobus']} | {viaje_info['Operador_Desc']}")
    print(f"  {tipo.upper()} | Inicio: {hora.strftime('%H:%M:%S')}")
    for inicio, fin, nombre in anomalias:
        print(f"  Anomalía: {nombre} ({inicio}-{fin}s)")
    print()
    viaje_global_idx += 1

# Viajes de regreso
for i, viaje_info in enumerate(viajes_regreso):
    hora = FECHA_BASE + timedelta(minutes=random.randint(0, 10))
    viaje_obj, anomalias = generate_trip(viaje_info, viaje_global_idx, fragments_regreso[i], hora)
    viajes.append(viaje_obj)
    tipo = "regreso"
    print(f"Viaje {viaje_global_idx+1}: Bus {viaje_info['Autobus']} | {viaje_info['Operador_Desc']}")
    print(f"  {tipo.upper()} | Inicio: {hora.strftime('%H:%M:%S')}")
    for inicio, fin, nombre in anomalias:
        print(f"  Anomalía: {nombre} ({inicio}-{fin}s)")
    print()
    viaje_global_idx += 1

# Guardar
output = {
    "viajes": viajes,
    "metadata": {
        "total_viajes": NUM_VIAJES,
        "fecha": "2021-01-15",
        "hora_aproximada": "14:00-14:10",
        "spns_disponibles": sorted([int(k) for k in SPN_DEFS.keys()]),
        "total_spns": len(SPN_DEFS),
        "generado": "2026-04-28T17:30:00Z",
        "descripcion": "10 viajes simultaneos, fragmentos GPS sin solaparse, anomalias aleatorias"
    }
}

with open('data/viajes_consolidados.json', 'w', encoding='utf-8') as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print(f"=== ARCHIVO GENERADO ===")
print(f"data/viajes_consolidados.json")
print(f"Fecha: 15 enero 2021, ~14:00 hrs")
print(f"Total viajes: {NUM_VIAJES} ({len(viajes_ida)} ida + {len(viajes_regreso)} regreso)")
print(f"Fragmentos GPS distribuidos sin solaparse")
