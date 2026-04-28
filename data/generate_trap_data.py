"""
Genera viajes "trampa" para la demo, pivoteados al formato
de DynamoDB (ado-telemetria-live), listos para inyectar.

Uso:
    python generate_trap_data.py --mes 1 --anio 2021 --viajes 2689828,2702063,2734771,2737103,2710211

Parametros:
    --mes       Mes a filtrar (1-12). Default: 1
    --anio      Anio a filtrar. Default: 2021
    --viajes    Lista de VIAJE_IDs separados por coma (requerido)
    --output    Nombre del archivo de salida. Default: trap_trips_dynamo.json
"""

import argparse
import json
import pandas as pd
import numpy as np
from datetime import datetime, timezone
import time


# --- Catalogo SPN (rangos normales) ---
CATALOGO_SPN = {
    84:    {"name": "Velocidad Km/h", "unidad": "km/h", "minimo": 0, "maximo": 120},
    190:   {"name": "RPM", "unidad": "rpm", "minimo": 0, "maximo": 3000},
    91:    {"name": "Posicion Pedal Acelerador", "unidad": "%", "minimo": 0, "maximo": 100},
    521:   {"name": "Posicion Pedal Freno", "unidad": "%", "minimo": 0, "maximo": 100},
    183:   {"name": "Tasa de combustible", "unidad": "L/h", "minimo": 0, "maximo": 100},
    185:   {"name": "Rendimiento", "unidad": "km/L", "minimo": 0, "maximo": 50},
    184:   {"name": "Ahorro de combustible instantaneo", "unidad": "km/L", "minimo": 0, "maximo": 50},
    96:    {"name": "Nivel Combustible", "unidad": "%", "minimo": 0, "maximo": 120},
    110:   {"name": "Temperatura Motor", "unidad": "C", "minimo": 0, "maximo": 150},
    175:   {"name": "Temperatura Aceite Motor", "unidad": "C", "minimo": 0, "maximo": 150},
    100:   {"name": "Presion Aceite Motor", "unidad": "kPa", "minimo": 0, "maximo": 1000},
    98:    {"name": "Nivel de aceite", "unidad": "%", "minimo": 0, "maximo": 110},
    111:   {"name": "Nivel de anticongelante", "unidad": "%", "minimo": 0, "maximo": 110},
    168:   {"name": "Voltaje Bateria", "unidad": "V", "minimo": 5, "maximo": 36},
    513:   {"name": "Porcentaje Torque", "unidad": "%", "minimo": 0, "maximo": 100},
    520:   {"name": "Porcentaje de torque del retardador", "unidad": "%", "minimo": -108, "maximo": 5},
    523:   {"name": "Marchas", "unidad": "", "minimo": -3, "maximo": 16},
    917:   {"name": "Odometro", "unidad": "km", "minimo": 0, "maximo": 999999},
    247:   {"name": "Horas Motor", "unidad": "h", "minimo": 0, "maximo": 99999},
    250:   {"name": "Combustible Consumido", "unidad": "L", "minimo": 0, "maximo": 999999},
    171:   {"name": "Temperatura ambiente", "unidad": "C", "minimo": 0, "maximo": 60},
    1761:  {"name": "Nivel Urea", "unidad": "%", "minimo": 0, "maximo": 100},
    1099:  {"name": "Balata Del Izq", "unidad": "%", "minimo": 0, "maximo": 100},
    1100:  {"name": "Balata Del Der", "unidad": "%", "minimo": 0, "maximo": 100},
    1101:  {"name": "Balata Tras Izq 1", "unidad": "%", "minimo": 0, "maximo": 100},
    1102:  {"name": "Balata Tras Der 1", "unidad": "%", "minimo": 0, "maximo": 100},
    20000: {"name": "Voltaje de bateria sin alternador", "unidad": "V", "minimo": 5, "maximo": 36},
}

# Mapeo SPN -> campo plano (igual que telemetry_pivot.py)
SPN_NOMBRE_CORTO = {
    84:   "velocidad_kmh",
    190:  "rpm",
    91:   "pct_acelerador",
    521:  "pct_freno",
    183:  "tasa_combustible_lh",
    185:  "rendimiento_kml",
    184:  "ahorro_instantaneo_kml",
    96:   "nivel_combustible_pct",
    110:  "temperatura_motor_c",
    175:  "temperatura_aceite_c",
    100:  "presion_aceite_kpa",
    98:   "nivel_aceite_pct",
    111:  "nivel_anticongelante_pct",
    168:  "voltaje_bateria_v",
    513:  "torque_pct",
    520:  "retarder_torque_pct",
    523:  "marcha",
    917:  "odometro_km",
    247:  "horas_motor_h",
    250:  "combustible_consumido_l",
    171:  "temperatura_ambiente_c",
    1761: "nivel_urea_pct",
    1099: "balata_del_izq_pct",
    1100: "balata_del_der_pct",
    1101: "balata_tras_izq1_pct",
    1102: "balata_tras_der1_pct",
}


def clasificar_consumo(spn_valores):
    """Replica la logica del simulador Lambda."""
    spn185 = spn_valores.get("185")
    if spn185 and spn185.get("valor") is not None:
        r = float(spn185["valor"])
        if r >= 3.0:
            return "EFICIENTE"
        if r >= 2.0:
            return "ALERTA_MODERADA"
        return "ALERTA_SIGNIFICATIVA"

    spn183 = spn_valores.get("183")
    if spn183 and spn183.get("valor") is not None:
        t = float(spn183["valor"])
        if t <= 30.0:
            return "EFICIENTE"
        if t <= 50.0:
            return "ALERTA_MODERADA"
        return "ALERTA_SIGNIFICATIVA"

    return "SIN_DATOS"


def pivotar_viaje(viaje_df):
    """Pivotea registros de un viaje al formato DynamoDB ado-telemetria-live."""
    ultimo_por_spn = viaje_df.sort_values('EVENTO_FECHA_HORA').groupby('EVENTO_SPN').last()

    primer_reg = viaje_df.iloc[0]
    ultimo_reg = viaje_df.sort_values('EVENTO_FECHA_HORA').iloc[-1]

    estado = {
        "autobus": str(int(primer_reg["Autobus"])),
        "viaje_id": int(primer_reg["VIAJE_ID"]),
        "operador_cve": str(primer_reg.get("Operador_Cve", "")),
        "operador_desc": str(primer_reg.get("Operador_Desc", "")),
        "viaje_ruta": str(primer_reg.get("VIAJE_RUTA", "")),
        "viaje_ruta_origen": str(primer_reg.get("VIAJE_RUTA_ORIGEN", "")),
        "viaje_ruta_destino": str(primer_reg.get("VIAJE_RUTA_DESTINO", "")),
        "latitud": float(ultimo_reg.get("EVENTO_LATITUD", 0)),
        "longitud": float(ultimo_reg.get("EVENTO_LONGITUD", 0)),
        "spn_valores": {},
        "alertas_spn": [],
    }

    for spn_id, row in ultimo_por_spn.iterrows():
        spn_id = int(spn_id)
        valor = float(row["EVENTO_VALOR"])

        cat = CATALOGO_SPN.get(spn_id)
        if cat is None:
            continue

        fuera_rango = valor < cat["minimo"] or valor > cat["maximo"]
        mensaje = ""
        if fuera_rango:
            if valor < cat["minimo"]:
                mensaje = f"{cat['name']} ({valor:.1f} {cat['unidad']}) por debajo del minimo ({cat['minimo']})"
            else:
                mensaje = f"{cat['name']} ({valor:.1f} {cat['unidad']}) por encima del maximo ({cat['maximo']})"

        estado["spn_valores"][str(spn_id)] = {
            "valor": valor,
            "name": cat["name"],
            "unidad": cat["unidad"],
            "fuera_de_rango": fuera_rango,
        }

        nombre_corto = SPN_NOMBRE_CORTO.get(spn_id)
        if nombre_corto:
            estado[nombre_corto] = valor

        if fuera_rango:
            estado["alertas_spn"].append({
                "spn_id": spn_id,
                "name": cat["name"],
                "valor": valor,
                "unidad": cat["unidad"],
                "mensaje": mensaje,
            })

    estado["estado_consumo"] = clasificar_consumo(estado["spn_valores"])

    # Placeholders — se sobreescriben al inyectar en DynamoDB
    estado["timestamp"] = "PLACEHOLDER_TIMESTAMP"
    estado["ttl_expiry"] = 0

    return estado


def parse_args():
    parser = argparse.ArgumentParser(description="Genera datos trampa para DynamoDB")
    parser.add_argument("--mes", type=int, default=1, help="Mes a filtrar (1-12)")
    parser.add_argument("--anio", type=int, default=2021, help="Anio a filtrar")
    parser.add_argument("--viajes", type=str, required=True,
                        help="Lista de VIAJE_IDs separados por coma (ej: 2689828,2702063)")
    parser.add_argument("--output", type=str, default="trap_trips_dynamo.json",
                        help="Archivo de salida JSON")
    return parser.parse_args()


def main():
    args = parse_args()
    mes = args.mes
    anio = args.anio
    viaje_ids = [int(v.strip()) for v in args.viajes.split(",")]
    output_path = args.output

    print("=" * 70)
    print(f"Generando datos trampa para demo - {anio}-{mes:02d}")
    print(f"Viajes solicitados: {viaje_ids}")
    print("=" * 70)

    df = pd.read_parquet('consolidated_telemetry.parquet')
    df['EVENTO_FECHA_HORA'] = pd.to_datetime(df['EVENTO_FECHA_HORA'])

    # Filtrar por mes y anio
    periodo = df[
        (df['EVENTO_FECHA_HORA'].dt.year == anio) &
        (df['EVENTO_FECHA_HORA'].dt.month == mes)
    ]

    print(f"Registros en {anio}-{mes:02d}: {len(periodo):,}")

    items = []
    for viaje_id in viaje_ids:
        viaje_df = periodo[periodo["VIAJE_ID"] == viaje_id]

        if viaje_df.empty:
            print(f"\n  ADVERTENCIA: Viaje {viaje_id} no encontrado en {anio}-{mes:02d}")
            continue

        bus = int(viaje_df.iloc[0]["Autobus"])
        n_reg = len(viaje_df)
        print(f"\nProcesando viaje {viaje_id} | Bus {bus} | {n_reg} registros")

        estado = pivotar_viaje(viaje_df)
        items.append(estado)

        print(f"  SPNs pivoteados: {len(estado['spn_valores'])}")
        print(f"  Alertas: {len(estado['alertas_spn'])}")
        print(f"  Estado consumo: {estado['estado_consumo']}")
        if estado["alertas_spn"]:
            for a in estado["alertas_spn"]:
                print(f"    ALERTA: {a['mensaje']}")

    # Guardar JSON
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2, default=str)

    print(f"\n{'=' * 70}")
    print(f"Guardado: {output_path}")
    print(f"Total items: {len(items)}")
    print(f"\nPara inyectar en DynamoDB:")
    print(f"  import boto3, json, time")
    print(f"  from datetime import datetime, timezone")
    print(f"  table = boto3.resource('dynamodb').Table('ado-telemetria-live')")
    print(f"  for item in json.load(open('{output_path}')):")
    print(f"      item['timestamp'] = datetime.now(timezone.utc).isoformat()")
    print(f"      item['ttl_expiry'] = int(time.time()) + 86400")
    print(f"      table.put_item(Item=item)")


if __name__ == "__main__":
    main()
