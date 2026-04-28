import pyarrow.parquet as pq
import pandas as pd
import os

folder = 'data/sample_parquets'
dfs = []
for f in sorted(os.listdir(folder)):
    if f.endswith('.parquet'):
        dfs.append(pq.read_table(os.path.join(folder, f)).to_pandas())
all_df = pd.concat(dfs, ignore_index=True)

# Filtrar viaje 2734727
viaje = all_df[all_df['VIAJE_ID'] == 2734727].copy()
viaje = viaje.sort_values('EVENTO_FECHA_HORA')

print("=== VIAJE 2734727 ===")
print(f"Bus: {viaje['Autobus'].iloc[0]}")
print(f"Operador: {viaje['Operador_Desc'].iloc[0]}")
print(f"Ruta: {viaje['VIAJE_RUTA'].iloc[0]}")
print(f"Fecha: {viaje['EVENTO_FECHA'].iloc[0]}")
print(f"Rango horario: {viaje['EVENTO_FECHA_HORA'].min()} -> {viaje['EVENTO_FECHA_HORA'].max()}")
print(f"Total registros: {len(viaje):,}")
print(f"SPNs distintos: {viaje['EVENTO_SPN'].nunique()}")
print()

# Detalle por SPN
print("=== DETALLE POR SPN ===")
spn_stats = viaje.groupby(['EVENTO_SPN', 'EVENTO_DESCRIPCION']).agg(
    registros=('EVENTO_VALOR', 'count'),
    min_val=('EVENTO_VALOR', 'min'),
    max_val=('EVENTO_VALOR', 'max'),
    avg_val=('EVENTO_VALOR', 'mean'),
    std_val=('EVENTO_VALOR', 'std')
).reset_index().sort_values('EVENTO_SPN')

for _, r in spn_stats.iterrows():
    std = r.std_val if pd.notna(r.std_val) else 0
    print(f"SPN {int(r.EVENTO_SPN):>5} | {r.EVENTO_DESCRIPCION:<50} | N={int(r.registros):>5} | Min={r.min_val:>9.1f} | Max={r.max_val:>9.1f} | Avg={r.avg_val:>9.1f} | Std={std:>7.1f}")

# Frecuencia temporal - cuantos timestamps unicos hay
timestamps_unicos = viaje['EVENTO_FECHA_HORA'].nunique()
print(f"\nTimestamps unicos: {timestamps_unicos:,}")

# Cuantos SPNs se capturan por timestamp (promedio)
spns_por_ts = viaje.groupby('EVENTO_FECHA_HORA')['EVENTO_SPN'].nunique()
print(f"SPNs por timestamp: min={spns_por_ts.min()}, max={spns_por_ts.max()}, avg={spns_por_ts.mean():.1f}")

# Intervalo entre lecturas
ts_sorted = viaje['EVENTO_FECHA_HORA'].drop_duplicates().sort_values()
diffs = ts_sorted.diff().dropna()
print(f"\nIntervalo entre lecturas:")
print(f"  Min: {diffs.min()}")
print(f"  Max: {diffs.max()}")
print(f"  Mediana: {diffs.median()}")
print(f"  Promedio: {diffs.mean()}")
