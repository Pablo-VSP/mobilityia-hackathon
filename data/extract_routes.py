import pyarrow.parquet as pq
import pandas as pd
import os
import json

folder = 'data/sample_parquets'
dfs = []
for f in sorted(os.listdir(folder)):
    if f.endswith('.parquet'):
        dfs.append(pq.read_table(os.path.join(folder, f)).to_pandas())
all_df = pd.concat(dfs, ignore_index=True)

# Bounding box Mexico para limpiar GPS anomalos
def clean_gps(df):
    return df[
        (df['EVENTO_LATITUD'] >= 14.5) & (df['EVENTO_LATITUD'] <= 32.7) &
        (df['EVENTO_LONGITUD'] >= -118.5) & (df['EVENTO_LONGITUD'] <= -86.7)
    ]

# Viaje IDA: 2704712 - Bus 7331 - Mexico Taxquena -> Acapulco Costera
ida = all_df[all_df['VIAJE_ID'] == 2704712].copy()
ida = clean_gps(ida)
ida_gps = ida[['EVENTO_FECHA_HORA', 'EVENTO_LATITUD', 'EVENTO_LONGITUD']].drop_duplicates(
    subset=['EVENTO_FECHA_HORA', 'EVENTO_LATITUD', 'EVENTO_LONGITUD']
).sort_values('EVENTO_FECHA_HORA')

ida_route = {
    "viaje_id": 2704712,
    "autobus": 7331,
    "tipo": "ida",
    "ruta": "MEXICO TAXQUENA - ACAPULCO COSTERA",
    "fecha": "2021-01-07",
    "puntos_gps": len(ida_gps),
    "coordenadas": [[row['EVENTO_LATITUD'], row['EVENTO_LONGITUD']] for _, row in ida_gps.iterrows()]
}

with open('data/ruta_ida_2704712.json', 'w', encoding='utf-8') as f:
    json.dump(ida_route, f, ensure_ascii=False, indent=2)

# Viaje REGRESO: 2725965 - Bus 7313 - Acapulco Costera -> Mexico Taxquena
regreso = all_df[all_df['VIAJE_ID'] == 2725965].copy()
regreso = clean_gps(regreso)
regreso_gps = regreso[['EVENTO_FECHA_HORA', 'EVENTO_LATITUD', 'EVENTO_LONGITUD']].drop_duplicates(
    subset=['EVENTO_FECHA_HORA', 'EVENTO_LATITUD', 'EVENTO_LONGITUD']
).sort_values('EVENTO_FECHA_HORA')

regreso_route = {
    "viaje_id": 2725965,
    "autobus": 7313,
    "tipo": "regreso",
    "ruta": "ACAPULCO COSTERA - MEXICO TAXQUENA",
    "fecha": "2021-01-15",
    "puntos_gps": len(regreso_gps),
    "coordenadas": [[row['EVENTO_LATITUD'], row['EVENTO_LONGITUD']] for _, row in regreso_gps.iterrows()]
}

with open('data/ruta_regreso_2725965.json', 'w', encoding='utf-8') as f:
    json.dump(regreso_route, f, ensure_ascii=False, indent=2)

print("=== RUTA IDA ===")
print(f"  Viaje: 2704712 | Bus: 7331")
print(f"  Mexico Taxquena -> Acapulco Costera")
print(f"  Puntos GPS limpios: {len(ida_gps):,}")
print(f"  Guardado: data/ruta_ida_2704712.json")
print()
print("=== RUTA REGRESO ===")
print(f"  Viaje: 2725965 | Bus: 7313")
print(f"  Acapulco Costera -> Mexico Taxquena")
print(f"  Puntos GPS limpios: {len(regreso_gps):,}")
print(f"  Guardado: data/ruta_regreso_2725965.json")
