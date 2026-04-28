import json
import folium

# Ruta IDA
with open('data/ruta_ida_2704712.json', 'r', encoding='utf-8') as f:
    ida = json.load(f)

coords_ida = ida["coordenadas"]
center_ida = [sum(c[0] for c in coords_ida)/len(coords_ida), sum(c[1] for c in coords_ida)/len(coords_ida)]

m_ida = folium.Map(location=center_ida, zoom_start=8, tiles='CartoDB dark_matter')
folium.PolyLine(coords_ida, color='#00ff88', weight=3, opacity=0.8).add_to(m_ida)
folium.CircleMarker(coords_ida[0], radius=10, color='#00ff88', fill=True, popup="INICIO - MEXICO TAXQUENA").add_to(m_ida)
folium.CircleMarker(coords_ida[-1], radius=10, color='#ff4444', fill=True, popup="FIN - ACAPULCO COSTERA").add_to(m_ida)
m_ida.save('data/mapa_ruta_ida.html')

# Ruta REGRESO
with open('data/ruta_regreso_2725965.json', 'r', encoding='utf-8') as f:
    regreso = json.load(f)

coords_reg = regreso["coordenadas"]
center_reg = [sum(c[0] for c in coords_reg)/len(coords_reg), sum(c[1] for c in coords_reg)/len(coords_reg)]

m_reg = folium.Map(location=center_reg, zoom_start=8, tiles='CartoDB dark_matter')
folium.PolyLine(coords_reg, color='#44aaff', weight=3, opacity=0.8).add_to(m_reg)
folium.CircleMarker(coords_reg[0], radius=10, color='#00ff88', fill=True, popup="INICIO - ACAPULCO COSTERA").add_to(m_reg)
folium.CircleMarker(coords_reg[-1], radius=10, color='#ff4444', fill=True, popup="FIN - MEXICO TAXQUENA").add_to(m_reg)
m_reg.save('data/mapa_ruta_regreso.html')

print("Mapas generados:")
print(f"  data/mapa_ruta_ida.html - {ida['origen']} -> {ida['destino']} ({ida['puntos_gps']} puntos)")
print(f"  data/mapa_ruta_regreso.html - {regreso['origen']} -> {regreso['destino']} ({regreso['puntos_gps']} puntos)")
