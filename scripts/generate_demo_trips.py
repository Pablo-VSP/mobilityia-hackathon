"""
Genera 10 viajes simulados para la demo del hackathon.

Basado en viajes reales de enero 2021 (posibles_viajes.JSON), crea 10 viajes con:
- Buses y conductores reales del dataset
- Variaciones en SPNs para disparar alertas de ambos agentes
- Algunos buses con señales críticas (presión aceite baja, temp alta, voltaje bajo)
- 60 frames por viaje, simulando ~10 min de streaming con EventBridge rate(10s)

Output: s3://ado-telemetry-mvp/hackathon-data/simulacion/viajes_consolidados.json

Ejecutar: python scripts/generate_demo_trips.py
Requiere: pip install boto3
"""

import json
import random
import boto3
from datetime import datetime

BUCKET = "ado-telemetry-mvp"
REGION = "us-east-2"
OUTPUT_KEY = "hackathon-data/simulacion/viajes_consolidados.json"

# 10 buses con conductores reales (del archivo posibles_viajes.JSON)
BUSES = [
    {"autobus": "7321", "operador_cve": "1265571", "operador_desc": "SANTIAGO GARCIA OSCAR",
     "viaje_id": 2740101, "viaje_ruta": "ACAPULCO COSTERA - MEXICO TAXQUENA",
     "viaje_ruta_origen": "ACAPULCO COSTERA", "viaje_ruta_destino": "MEXICO TAXQUENA"},
    {"autobus": "7302", "operador_cve": "1336374", "operador_desc": "JORGE ARMANDO CORTES RADILLA",
     "viaje_id": 2740102, "viaje_ruta": "MEXICO TAXQUENA - ACAPULCO COSTERA",
     "viaje_ruta_origen": "MEXICO TAXQUENA", "viaje_ruta_destino": "ACAPULCO COSTERA"},
    {"autobus": "7313", "operador_cve": "1265518", "operador_desc": "GARCIA QUIROZ PEDRO",
     "viaje_id": 2740103, "viaje_ruta": "MEXICO TAXQUENA - ACAPULCO COSTERA",
     "viaje_ruta_origen": "MEXICO TAXQUENA", "viaje_ruta_destino": "ACAPULCO COSTERA"},
    {"autobus": "7301", "operador_cve": "1321464", "operador_desc": "SAMUEL CARTENO BAUTISTA",
     "viaje_id": 2740104, "viaje_ruta": "MEXICO TAXQUENA - ACAPULCO COSTERA",
     "viaje_ruta_origen": "MEXICO TAXQUENA", "viaje_ruta_destino": "ACAPULCO COSTERA"},
    {"autobus": "7307", "operador_cve": "1258238", "operador_desc": "JESUS GONZALEZ LOAIZA",
     "viaje_id": 2740105, "viaje_ruta": "ACAPULCO COSTERA - MEXICO TAXQUENA",
     "viaje_ruta_origen": "ACAPULCO COSTERA", "viaje_ruta_destino": "MEXICO TAXQUENA"},
    {"autobus": "7331", "operador_cve": "1265549", "operador_desc": "GARCIA VALENTIN JULIO",
     "viaje_id": 2740106, "viaje_ruta": "MEXICO TAXQUENA - ACAPULCO COSTERA",
     "viaje_ruta_origen": "MEXICO TAXQUENA", "viaje_ruta_destino": "ACAPULCO COSTERA"},
    {"autobus": "7309", "operador_cve": "1265513", "operador_desc": "ALVARO VARGAS ESTRADA",
     "viaje_id": 2740107, "viaje_ruta": "MEXICO TAXQUENA - ACAPULCO COSTERA",
     "viaje_ruta_origen": "MEXICO TAXQUENA", "viaje_ruta_destino": "ACAPULCO COSTERA"},
    {"autobus": "7305", "operador_cve": "1289212", "operador_desc": "QUINTERO RIVERA MAYOLO",
     "viaje_id": 2740108, "viaje_ruta": "ACAPULCO COSTERA - MEXICO TAXQUENA",
     "viaje_ruta_origen": "ACAPULCO COSTERA", "viaje_ruta_destino": "MEXICO TAXQUENA"},
    {"autobus": "7319", "operador_cve": "1294065", "operador_desc": "EVARISTO SANCHEZ DE DIOS",
     "viaje_id": 2740109, "viaje_ruta": "ACAPULCO COSTERA - MEXICO TAXQUENA",
     "viaje_ruta_origen": "ACAPULCO COSTERA", "viaje_ruta_destino": "MEXICO TAXQUENA"},
    {"autobus": "7315", "operador_cve": "1274899", "operador_desc": "RAMIRO SANCHEZ CABELLO",
     "viaje_id": 2740110, "viaje_ruta": "MEXICO TAXQUENA - ACAPULCO COSTERA",
     "viaje_ruta_origen": "MEXICO TAXQUENA", "viaje_ruta_destino": "ACAPULCO COSTERA"},
]

# Perfiles: qué tipo de señales genera cada bus
# normal=6, alerta_combustible=2, alerta_mantenimiento=1, critico=1
BUS_PROFILES = {
    "7321": "normal",
    "7302": "normal",
    "7313": "alerta_combustible",
    "7301": "normal",
    "7307": "alerta_mantenimiento",
    "7331": "critico",
    "7309": "normal",
    "7305": "normal",
    "7319": "alerta_combustible",
    "7315": "alerta_mantenimiento",
}

# Coordenadas ruta CDMX-Acapulco
RUTA_COORDS = [
    (19.3440, -99.1310), (19.2900, -99.1500), (19.1800, -99.2200),
    (18.9200, -99.2300), (18.7500, -99.3000), (18.4000, -99.4500),
    (17.8000, -99.5500), (17.2000, -99.7000), (16.8600, -99.8800),
]

FRAMES_PER_TRIP = 60
DURACION_SEGUNDOS = 18000  # 5h simuladas


def interpolate_coords(progress):
    n = len(RUTA_COORDS) - 1
    idx = progress * n
    i = min(int(idx), n - 1)
    t = idx - i
    lat = RUTA_COORDS[i][0] + t * (RUTA_COORDS[i+1][0] - RUTA_COORDS[i][0])
    lon = RUTA_COORDS[i][1] + t * (RUTA_COORDS[i+1][1] - RUTA_COORDS[i][1])
    return round(lat, 6), round(lon, 6)


def generate_spn_values(profile, progress, frame_idx):
    base = {
        "84": {"valor": 85 + random.uniform(-10, 10), "name": "Velocidad Km/h", "unidad": "km/h"},
        "190": {"valor": 1400 + random.uniform(-200, 200), "name": "RPM", "unidad": "rpm"},
        "91": {"valor": 35 + random.uniform(-10, 15), "name": "Posicion Pedal Acelerador", "unidad": "%"},
        "521": {"valor": random.uniform(0, 15), "name": "Posicion Pedal Freno", "unidad": "%"},
        "183": {"valor": 25 + random.uniform(-5, 5), "name": "Tasa de combustible", "unidad": "L/h"},
        "185": {"valor": 3.5 + random.uniform(-0.3, 0.3), "name": "Rendimiento", "unidad": "km/L"},
        "184": {"valor": 3.2 + random.uniform(-0.5, 0.5), "name": "Ahorro de combustible instantaneo", "unidad": "km/L"},
        "96": {"valor": 75 - progress * 30 + random.uniform(-2, 2), "name": "Nivel Combustible", "unidad": "%"},
        "110": {"valor": 92 + random.uniform(-3, 5), "name": "Temperatura Motor", "unidad": "C"},
        "175": {"valor": 95 + random.uniform(-3, 5), "name": "Temperatura Aceite Motor", "unidad": "C"},
        "100": {"valor": 450 + random.uniform(-50, 50), "name": "Presion Aceite Motor", "unidad": "kPa"},
        "98": {"valor": 75 + random.uniform(-5, 5), "name": "Nivel de aceite", "unidad": "%"},
        "111": {"valor": 80 + random.uniform(-5, 5), "name": "Nivel de anticongelante", "unidad": "%"},
        "168": {"valor": 13.8 + random.uniform(-0.3, 0.3), "name": "Voltaje Bateria", "unidad": "V"},
        "513": {"valor": 55 + random.uniform(-15, 15), "name": "Porcentaje Torque", "unidad": "%"},
        "520": {"valor": random.uniform(-20, 0), "name": "Retarder Percent Torque", "unidad": "%"},
        "523": {"valor": random.choice([10, 11, 12]), "name": "Marchas", "unidad": "Marcha"},
        "917": {"valor": 185000 + frame_idx * 2.5, "name": "Odometro", "unidad": "km"},
        "247": {"valor": 12500 + frame_idx * 0.08, "name": "Horas Motor", "unidad": "h"},
        "250": {"valor": 50000 + frame_idx * 0.7, "name": "Combustible Consumido", "unidad": "L"},
        "1761": {"valor": 65 + random.uniform(-3, 3), "name": "Nivel Urea", "unidad": "%"},
        "171": {"valor": 28 + random.uniform(-2, 2), "name": "Temperatura ambiente", "unidad": "C"},
        "1624": {"valor": 85 + random.uniform(-10, 10), "name": "Velocidad tacografo", "unidad": "km/h"},
        "70": {"valor": 0, "name": "Interruptor del freno de estacionamiento", "unidad": "bit"},
        "527": {"valor": 5, "name": "Cruise Control States", "unidad": "bit"},
        "596": {"valor": 1, "name": "Cruise Control Enable Switch", "unidad": "bit"},
        "597": {"valor": 0, "name": "Brake Switch", "unidad": "bit"},
        "598": {"valor": 0, "name": "Clutch Switch", "unidad": "bit"},
        "20001": {"valor": 12.5 + random.uniform(-0.2, 0.2), "name": "Voltaje de bateria minimo historico", "unidad": "V"},
    }

    if profile == "alerta_combustible":
        base["91"]["valor"] = 75 + random.uniform(0, 20)
        base["521"]["valor"] = 50 + random.uniform(0, 25)
        base["190"]["valor"] = 2100 + random.uniform(0, 300)
        base["185"]["valor"] = 2.5 + random.uniform(-0.3, 0.3)
        base["183"]["valor"] = 45 + random.uniform(0, 15)
        base["84"]["valor"] = 100 + random.uniform(0, 15)

    elif profile == "alerta_mantenimiento":
        base["100"]["valor"] = 120 + random.uniform(-20, 20)
        base["110"]["valor"] = 118 + random.uniform(-3, 5)
        base["175"]["valor"] = 125 + random.uniform(-3, 5)
        base["98"]["valor"] = 22 + random.uniform(-3, 3)

    elif profile == "critico":
        base["100"]["valor"] = 80 + random.uniform(-20, 20)
        base["110"]["valor"] = 135 + random.uniform(-5, 8)
        base["168"]["valor"] = 11.2 + random.uniform(-0.5, 0.3)
        base["175"]["valor"] = 138 + random.uniform(-3, 5)
        base["98"]["valor"] = 15 + random.uniform(-3, 3)
        base["111"]["valor"] = 25 + random.uniform(-5, 5)

    for spn_data in base.values():
        spn_data["valor"] = round(spn_data["valor"], 2)

    return base


def generate_trip(bus_info, profile):
    frames = []
    reverse = bus_info["viaje_ruta_origen"] == "ACAPULCO COSTERA"

    for i in range(FRAMES_PER_TRIP):
        progress = i / max(FRAMES_PER_TRIP - 1, 1)
        if reverse:
            progress = 1.0 - progress

        lat, lon = interpolate_coords(progress)
        spn_valores = generate_spn_values(profile, progress, i)

        frames.append({
            "offset": i,
            "segundos_desde_inicio": int(i * (DURACION_SEGUNDOS / FRAMES_PER_TRIP)),
            "latitud": lat,
            "longitud": lon,
            "spn_valores": spn_valores,
        })

    return {
        "viaje_id": bus_info["viaje_id"],
        "autobus": bus_info["autobus"],
        "operador_cve": bus_info["operador_cve"],
        "operador_desc": bus_info["operador_desc"],
        "viaje_ruta": bus_info["viaje_ruta"],
        "viaje_ruta_origen": bus_info["viaje_ruta_origen"],
        "viaje_ruta_destino": bus_info["viaje_ruta_destino"],
        "total_frames": FRAMES_PER_TRIP,
        "duracion_segundos": DURACION_SEGUNDOS,
        "frames": frames,
    }


def main():
    print("Generando 10 viajes simulados para demo...")
    random.seed(42)

    viajes = []
    all_spns = set()

    for bus in BUSES:
        profile = BUS_PROFILES[bus["autobus"]]
        trip = generate_trip(bus, profile)
        viajes.append(trip)
        print(f"  Bus {bus['autobus']} ({profile:20s}) | {bus['operador_desc'][:25]:25s} | {bus['viaje_ruta'][:35]}")
        for frame in trip["frames"]:
            all_spns.update(int(k) for k in frame["spn_valores"].keys())

    output = {
        "viajes": viajes,
        "metadata": {
            "total_viajes": len(viajes),
            "spns_disponibles": sorted(all_spns),
            "total_spns": len(all_spns),
            "generado": datetime.utcnow().isoformat() + "Z",
            "perfiles": BUS_PROFILES,
            "nota": "10 viajes demo. 60 frames c/u. EventBridge rate(10s) + STEP_SECONDS=300 = 10 min de demo.",
        },
    }

    s3 = boto3.Session(profile_name="mobilityadods").client("s3", region_name=REGION)
    json_bytes = json.dumps(output, ensure_ascii=False).encode("utf-8")
    print(f"\nSubiendo a s3://{BUCKET}/{OUTPUT_KEY} ({len(json_bytes) / 1024:.1f} KB)...")
    s3.put_object(Bucket=BUCKET, Key=OUTPUT_KEY, Body=json_bytes, ContentType="application/json")

    print("\nListo! Perfiles de alerta para la demo:")
    print("  7313 - ALERTA COMBUSTIBLE (aceleracion brusca, consumo alto)")
    print("  7319 - ALERTA COMBUSTIBLE (RPM alto, frenado brusco)")
    print("  7307 - ALERTA MANTENIMIENTO (presion aceite baja, temp alta)")
    print("  7315 - ALERTA MANTENIMIENTO (voltaje bajo, nivel aceite bajo)")
    print("  7331 - CRITICO (presion+voltaje+temp+aceite+anticongelante)")


if __name__ == "__main__":
    main()
