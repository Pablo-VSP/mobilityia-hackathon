import pyarrow.parquet as pq
import pandas as pd
import os
import folium

folder = 'data/sample_parquets'
dfs = []
for f in sorted(os.listdir(folder)):
    if f.endswith('.parquet'):
        dfs.append(pq.read_table(os.path.join(folder, f)).to_pandas())
all_df = pd.concat(dfs, ignore_index=True)

# Filtrar coordenadas dentro de Mexico (bounding box)
# Lat: 14.5 a 32.7, Lon: -118.5 a -86.7
gps = all_df[['VIAJE_ID', 'Autobus', 'EVENTO_FECHA_HORA', 'EVENTO_LATITUD', 'EVENTO_LONGITUD', 'VIAJE_RUTA']].drop_duplicates(
    subset=['VIAJE_ID', 'EVENTO_FECHA_HORA', 'EVENTO_LATITUD', 'EVENTO_LONGITUD']
).sort_values(['VIAJE_ID', 'EVENTO_FECHA_HORA'])

total_antes = len(gps)
gps = gps[
    (gps['EVENTO_LATITUD'] >= 14.5) & (gps['EVENTO_LATITUD'] <= 32.7) &
    (gps['EVENTO_LONGITUD'] >= -118.5) & (gps['EVENTO_LONGITUD'] <= -86.7)
]
total_despues = len(gps)
print(f"Puntos GPS antes: {total_antes:,}")
print(f"Puntos GPS despues (limpios): {total_despues:,}")
print(f"Puntos anomalos eliminados: {total_antes - total_despues:,}")
print()

# Centro del mapa
center_lat = gps['EVENTO_LATITUD'].mean()
center_lon = gps['EVENTO_LONGITUD'].mean()

m = folium.Map(location=[center_lat, center_lon], zoom_start=7, tiles='CartoDB dark_matter')

colors = ['#00ff88', '#ff4444', '#44aaff']
viajes = sorted(gps['VIAJE_ID'].unique())

for i, vid in enumerate(viajes):
    sub = gps[gps['VIAJE_ID'] == vid].sort_values('EVENTO_FECHA_HORA')
    coords = list(zip(sub['EVENTO_LATITUD'], sub['EVENTO_LONGITUD']))
    bus = sub['Autobus'].iloc[0]
    ruta = sub['VIAJE_RUTA'].iloc[0]
    
    folium.PolyLine(
        coords, 
        color=colors[i % 3], 
        weight=3, 
        opacity=0.8,
        popup=f"Viaje {vid} | Bus {bus} | {ruta}"
    ).add_to(m)
    
    folium.CircleMarker(
        coords[0], radius=8, color=colors[i % 3], fill=True,
        popup=f"INICIO - Bus {bus}"
    ).add_to(m)
    
    folium.CircleMarker(
        coords[-1], radius=8, color=colors[i % 3], fill=True, fill_opacity=0.3,
        popup=f"FIN - Bus {bus}"
    ).add_to(m)

m.save('data/rutas_viajes.html')
print("Mapa limpio guardado en data/rutas_viajes.html")
for i, vid in enumerate(viajes):
    sub = gps[gps['VIAJE_ID'] == vid]
    print(f"  [{colors[i]}] Viaje {vid} - Bus {sub['Autobus'].iloc[0]} - {len(sub)} puntos GPS")
