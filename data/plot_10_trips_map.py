"""
Visualiza los 10 viajes en un mapa para verificar que no se solapan.
Cada bus tiene un color diferente y se muestra su posición inicial.
"""
import json
import folium

with open('data/viajes_consolidados.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

viajes = data["viajes"]

# Colores distintos por bus
colors = ['#00ff88', '#ff4444', '#44aaff', '#ffaa00', '#ff44aa',
          '#44ffaa', '#aa44ff', '#ffffff', '#ff8844', '#88ff44']

# Centro del mapa
all_lats = []
all_lons = []
for v in viajes:
    for f in v["frames"]:
        all_lats.append(f["latitud"])
        all_lons.append(f["longitud"])

center = [sum(all_lats)/len(all_lats), sum(all_lons)/len(all_lons)]

m = folium.Map(location=center, zoom_start=8, tiles='CartoDB dark_matter')

# Dibujar ruta completa de ida y regreso como referencia (gris tenue)
with open('data/ruta_ida_2704712.json', 'r') as f:
    ruta_ida = json.load(f)
with open('data/ruta_regreso_2725965.json', 'r') as f:
    ruta_regreso = json.load(f)

folium.PolyLine(ruta_ida["coordenadas"], color='#333333', weight=1, opacity=0.4).add_to(m)
folium.PolyLine(ruta_regreso["coordenadas"], color='#333333', weight=1, opacity=0.4).add_to(m)

# Dibujar cada viaje
for i, viaje in enumerate(viajes):
    coords = [[f["latitud"], f["longitud"]] for f in viaje["frames"]]
    color = colors[i % len(colors)]
    tipo = "IDA" if viaje["viaje_ruta_origen"] == "MEXICO TAXQUENA" else "REGRESO"
    
    # Línea del fragmento
    folium.PolyLine(
        coords, color=color, weight=4, opacity=0.9,
        popup=f"Bus {viaje['autobus']} | {viaje['operador_desc']}<br>{tipo} | {viaje['hora_inicio']}"
    ).add_to(m)
    
    # Marcador de posición del bus (punto medio del fragmento)
    mid = len(coords) // 2
    folium.CircleMarker(
        coords[mid], radius=8, color=color, fill=True, fill_opacity=1,
        popup=f"<b>Bus {viaje['autobus']}</b><br>{viaje['operador_desc']}<br>{tipo}<br>Inicio: {viaje['hora_inicio']}"
    ).add_to(m)
    
    # Label con número de bus
    folium.Marker(
        coords[mid],
        icon=folium.DivIcon(html=f'<div style="font-size:10px;color:{color};font-weight:bold;text-shadow:1px 1px #000;">{viaje["autobus"]}</div>')
    ).add_to(m)

# Leyenda
legend_html = '<div style="position:fixed;bottom:20px;left:20px;background:#1a1a2e;padding:15px;border-radius:8px;border:1px solid #333;z-index:9999;font-family:monospace;font-size:11px;color:#eee;">'
legend_html += '<b>10 Viajes Simulados — 15 Ene 2021</b><br><br>'
for i, viaje in enumerate(viajes):
    tipo = "→" if viaje["viaje_ruta_origen"] == "MEXICO TAXQUENA" else "←"
    legend_html += f'<span style="color:{colors[i]}">■</span> Bus {viaje["autobus"]} {tipo} {viaje["hora_inicio"]}<br>'
legend_html += '</div>'

m.get_root().html.add_child(folium.Element(legend_html))
m.save('data/mapa_10_viajes.html')
print("Mapa guardado en data/mapa_10_viajes.html")
print(f"  → = ida (México → Acapulco)")
print(f"  ← = regreso (Acapulco → México)")
