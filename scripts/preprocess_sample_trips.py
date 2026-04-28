"""
Pre-procesa los 3 viajes de ejemplo (Parquet) en un JSON consolidado
optimizado para el simulador Lambda.

Cada viaje se convierte en una lista ordenada de "frames" — un frame
es un snapshot temporal con todos los SPNs pivoteados, GPS, y contexto.

Output: s3://ado-telemetry-mvp/hackathon-data/simulacion/viajes_consolidados.json

Estructura del JSON:
{
  "viajes": [
    {
      "viaje_id": 2704712,
      "autobus": "7331",
      "operador_cve": "...",
      "operador_desc": "GARCIA VALENTIN JULIO",
      "viaje_ruta": "MEXICO TAXQUENA - ACAPULCO COSTERA",
      "viaje_ruta_origen": "MEXICO TAXQUENA",
      "viaje_ruta_destino": "ACAPULCO COSTERA",
      "total_frames": 2349,
      "duracion_segundos": 17995,
      "frames": [
        {
          "offset": 0,
          "segundos_desde_inicio": 0,
          "latitud": 19.3427,
          "longitud": -99.1234,
          "spn_valores": {
            "84": {"valor": 45.2, "name": "Velocidad Km/h", "unidad": "km/h"},
            "190": {"valor": 1200.0, "name": "RPM", "unidad": "rpm"},
            ...
          }
        },
        ...
      ]
    },
    ...
  ],
  "metadata": {
    "total_viajes": 3,
    "spns_disponibles": [84, 91, 96, ...],
    "generado": "2026-04-28T..."
  }
}
"""

import json
import sys
from datetime import datetime
from collections import defaultdict

import boto3
import pandas as pd
import io

BUCKET = "ado-telemetry-mvp"
REGION = "us-east-2"
PREFIX = "hackathon-data/sample_data/travel_telemetry_examples_/"
OUTPUT_KEY = "hackathon-data/simulacion/viajes_consolidados.json"

# The 3 large files (the rest are empty schema-only files)
TRIP_FILES = [
    "travel_telemetry_examples_000000000055.parquet",
    "travel_telemetry_examples_000000000181.parquet",
    "travel_telemetry_examples_000000000216.parquet",
]

# SPN catalog for name/unit lookup
SPN_CATALOG_KEY = "hackathon-data/catalogo/motor_spn.json"


def load_spn_catalog(s3_client):
    """Load SPN catalog from S3."""
    resp = s3_client.get_object(Bucket=BUCKET, Key=SPN_CATALOG_KEY)
    catalog_raw = json.loads(resp["Body"].read().decode("utf-8"))
    return {int(entry["id"]): entry for entry in catalog_raw}


def load_parquet_from_s3(s3_client, key):
    """Download and read a Parquet file from S3."""
    resp = s3_client.get_object(Bucket=BUCKET, Key=f"{PREFIX}{key}")
    body = resp["Body"].read()
    df = pd.read_parquet(io.BytesIO(body))
    df.columns = [c.lower() for c in df.columns]
    return df


def process_trip(df, spn_catalog):
    """Convert a trip DataFrame into a list of consolidated frames."""
    # Sort by timestamp
    df["evento_fecha_hora"] = pd.to_datetime(df["evento_fecha_hora"])
    df = df.sort_values("evento_fecha_hora")

    # Get trip metadata from first record
    first = df.iloc[0]
    viaje_id = int(first["viaje_id"])
    autobus = str(int(first["autobus"]))
    operador_cve = str(first.get("operador_cve", ""))
    operador_desc = str(first.get("operador_desc", "")).strip()
    viaje_ruta = str(first.get("viaje_ruta", "")).strip()
    viaje_ruta_origen = str(first.get("viaje_ruta_origen", "")).strip()
    viaje_ruta_destino = str(first.get("viaje_ruta_destino", "")).strip()

    # Group by unique timestamp to create frames
    t0 = df["evento_fecha_hora"].min()
    timestamps = sorted(df["evento_fecha_hora"].unique())

    frames = []
    # Keep a running state of all SPNs (carry forward last known value)
    running_state = {}

    for i, ts in enumerate(timestamps):
        ts_records = df[df["evento_fecha_hora"] == ts]
        segundos = (pd.Timestamp(ts) - pd.Timestamp(t0)).total_seconds()

        # Update running state with new SPN values from this timestamp
        lat = 0.0
        lon = 0.0
        for _, row in ts_records.iterrows():
            spn_id = int(row["evento_spn"])
            valor = float(row["evento_valor"])
            spn_info = spn_catalog.get(spn_id, {})

            running_state[str(spn_id)] = {
                "valor": round(valor, 2),
                "name": spn_info.get("name", f"SPN_{spn_id}").strip(),
                "unidad": spn_info.get("unidad", "").strip(),
            }

            # Use non-zero GPS
            if row["evento_latitud"] != 0:
                lat = float(row["evento_latitud"])
            if row["evento_longitud"] != 0:
                lon = float(row["evento_longitud"])

        # Only emit a frame if we have GPS data
        if lat == 0.0 and lon == 0.0:
            # Try to carry forward from previous frame
            if frames:
                lat = frames[-1]["latitud"]
                lon = frames[-1]["longitud"]

        frames.append({
            "offset": i,
            "segundos_desde_inicio": int(segundos),
            "latitud": round(lat, 6),
            "longitud": round(lon, 6),
            "spn_valores": dict(running_state),  # snapshot of all known SPNs
        })

    duracion = int((pd.Timestamp(timestamps[-1]) - pd.Timestamp(timestamps[0])).total_seconds())

    return {
        "viaje_id": viaje_id,
        "autobus": autobus,
        "operador_cve": operador_cve,
        "operador_desc": operador_desc,
        "viaje_ruta": viaje_ruta,
        "viaje_ruta_origen": viaje_ruta_origen,
        "viaje_ruta_destino": viaje_ruta_destino,
        "total_frames": len(frames),
        "duracion_segundos": duracion,
        "frames": frames,
    }


def main():
    s3 = boto3.client("s3", region_name=REGION)
    spn_catalog = load_spn_catalog(s3)
    print(f"Catálogo SPN cargado: {len(spn_catalog)} entradas")

    viajes = []
    all_spns = set()

    for filename in TRIP_FILES:
        print(f"\nProcesando {filename}...")
        df = load_parquet_from_s3(s3, filename)
        print(f"  {len(df)} registros, {df['evento_spn'].nunique()} SPNs")

        trip = process_trip(df, spn_catalog)
        viajes.append(trip)
        print(f"  Bus {trip['autobus']}: {trip['total_frames']} frames, {trip['duracion_segundos']}s")

        # Collect all SPNs
        for frame in trip["frames"]:
            all_spns.update(int(k) for k in frame["spn_valores"].keys())

    output = {
        "viajes": viajes,
        "metadata": {
            "total_viajes": len(viajes),
            "spns_disponibles": sorted(all_spns),
            "total_spns": len(all_spns),
            "generado": datetime.utcnow().isoformat() + "Z",
        },
    }

    # Upload to S3
    json_bytes = json.dumps(output, ensure_ascii=False, default=str).encode("utf-8")
    print(f"\nSubiendo a s3://{BUCKET}/{OUTPUT_KEY} ({len(json_bytes) / 1024 / 1024:.1f} MB)...")

    s3.put_object(
        Bucket=BUCKET,
        Key=OUTPUT_KEY,
        Body=json_bytes,
        ContentType="application/json",
    )
    print("¡Listo!")

    # Print summary
    print(f"\n=== RESUMEN ===")
    print(f"Viajes: {len(viajes)}")
    for v in viajes:
        print(f"  Bus {v['autobus']}: {v['total_frames']} frames, ruta {v['viaje_ruta']}")
    print(f"SPNs totales: {len(all_spns)}")
    print(f"Output: s3://{BUCKET}/{OUTPUT_KEY}")


if __name__ == "__main__":
    main()
