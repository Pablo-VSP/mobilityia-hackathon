"""
Visualiza el viaje simulado: mapa GPS + gráficas de SPNs con anomalías marcadas.
"""
import json

with open('data/viaje_simulado_demo.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

viaje = data["viajes"][0]
frames = viaje["frames"]

# Extraer coordenadas
coords = [[f["latitud"], f["longitud"]] for f in frames]

# Extraer series de SPNs clave
spns_to_plot = {
    "84": {"label": "Velocidad (km/h)", "color": "#00ff88"},
    "190": {"label": "RPM", "color": "#44aaff"},
    "110": {"label": "Temp Motor (°C)", "color": "#ff4444"},
    "175": {"label": "Temp Aceite (°C)", "color": "#ff8844"},
    "100": {"label": "Presión Aceite (kPa)", "color": "#ffff44"},
    "183": {"label": "Tasa Combustible (L/h)", "color": "#aa44ff"},
    "185": {"label": "Rendimiento (km/L)", "color": "#44ffaa"},
    "91": {"label": "Pedal Acelerador (%)", "color": "#ff44aa"},
    "168": {"label": "Voltaje Batería (V)", "color": "#ffffff"},
}

series_data = {spn: {"x": [], "y": []} for spn in spns_to_plot}
for f in frames:
    seg = f["segundos_desde_inicio"]
    for spn_id in spns_to_plot:
        if spn_id in f["spn_valores"]:
            series_data[spn_id]["x"].append(seg)
            series_data[spn_id]["y"].append(f["spn_valores"][spn_id]["valor"])

# Generar HTML con mapa + charts
html = f"""<!DOCTYPE html>
<html>
<head>
<title>Viaje Simulado - Bus {viaje['autobus']}</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
body {{ margin:0; background:#1a1a2e; color:#eee; font-family:monospace; }}
.header {{ padding:15px 20px; background:#16213e; border-bottom:1px solid #333; }}
.header h1 {{ margin:0; font-size:18px; color:#00ff88; }}
.header p {{ margin:5px 0 0; font-size:12px; color:#aaa; }}
.container {{ display:flex; flex-wrap:wrap; }}
#map {{ width:100%; height:350px; }}
.charts {{ width:100%; padding:10px; display:grid; grid-template-columns:1fr 1fr 1fr; gap:10px; }}
.chart-box {{ background:#16213e; border-radius:8px; padding:10px; }}
.chart-box canvas {{ width:100%!important; height:150px!important; }}
.anomaly-legend {{ padding:10px 20px; background:#16213e; border-top:1px solid #333; font-size:12px; }}
.anomaly-legend span {{ margin-right:20px; }}
.a1 {{ color:#ff44aa; }} .a2 {{ color:#ff4444; }} .a3 {{ color:#ffff44; }}
</style>
</head>
<body>
<div class="header">
  <h1>🚌 Viaje Simulado - Bus {viaje['autobus']}</h1>
  <p>Operador: {viaje['operador_desc']} | Ruta: {viaje['viaje_ruta']} | Duración: 5 min (300 frames)</p>
</div>
<div class="anomaly-legend">
  <span class="a1">■ 90-120s: Conducción agresiva</span>
  <span class="a2">■ 180-210s: Riesgo mecánico</span>
  <span class="a3">■ 250-280s: Velocidad excesiva</span>
</div>
<div id="map"></div>
<div class="charts">
"""

# Agregar canvas por cada SPN
for spn_id, cfg in spns_to_plot.items():
    html += f'<div class="chart-box"><canvas id="chart_{spn_id}"></canvas></div>\n'

html += """</div>
<script>
// Mapa
var coords = """ + json.dumps(coords) + """;
var map = L.map('map').setView([coords[150][0], coords[150][1]], 11);
L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
  attribution: '© CARTO'
}).addTo(map);

// Ruta completa
L.polyline(coords, {color:'#00ff88', weight:2, opacity:0.6}).addTo(map);

// Segmentos de anomalía
var a1 = coords.slice(90, 121);
var a2 = coords.slice(180, 211);
var a3 = coords.slice(250, 281);
L.polyline(a1, {color:'#ff44aa', weight:5, opacity:0.9}).addTo(map).bindPopup('Conducción agresiva (90-120s)');
L.polyline(a2, {color:'#ff4444', weight:5, opacity:0.9}).addTo(map).bindPopup('Riesgo mecánico (180-210s)');
L.polyline(a3, {color:'#ffff44', weight:5, opacity:0.9}).addTo(map).bindPopup('Velocidad excesiva (250-280s)');

// Marcadores
L.circleMarker(coords[0], {radius:8, color:'#00ff88', fillOpacity:1}).addTo(map).bindPopup('INICIO');
L.circleMarker(coords[coords.length-1], {radius:8, color:'#ff4444', fillOpacity:1}).addTo(map).bindPopup('FIN');

// Charts
var anomalyBands = [
  {from:90, to:120, color:'rgba(255,68,170,0.15)'},
  {from:180, to:210, color:'rgba(255,68,68,0.15)'},
  {from:250, to:280, color:'rgba(255,255,68,0.15)'}
];

var annotationPlugin = {
  id: 'anomalyBands',
  beforeDraw(chart) {
    var ctx = chart.ctx;
    var xAxis = chart.scales.x;
    var yAxis = chart.scales.y;
    anomalyBands.forEach(function(band) {
      var left = xAxis.getPixelForValue(band.from);
      var right = xAxis.getPixelForValue(band.to);
      ctx.fillStyle = band.color;
      ctx.fillRect(left, yAxis.top, right-left, yAxis.bottom-yAxis.top);
    });
  }
};

function makeChart(canvasId, label, xData, yData, color) {
  new Chart(document.getElementById(canvasId), {
    type: 'line',
    data: {
      labels: xData,
      datasets: [{
        label: label,
        data: yData,
        borderColor: color,
        borderWidth: 1.5,
        pointRadius: 0,
        tension: 0.3,
        fill: false
      }]
    },
    options: {
      responsive: true,
      plugins: { legend: { labels: { color: '#eee', font: {size:10} } } },
      scales: {
        x: { title:{display:true, text:'Segundos', color:'#888'}, ticks:{color:'#888', maxTicksLimit:6} },
        y: { ticks:{color:'#888'} }
      }
    },
    plugins: [annotaionPlugin]
  });
}
var annotaionPlugin = anomalyBands.length > 0 ? {
  id: 'anomalyBands',
  beforeDraw(chart) {
    var ctx = chart.ctx;
    var xAxis = chart.scales.x;
    var yAxis = chart.scales.y;
    anomalyBands.forEach(function(band) {
      var xMin = xAxis.getPixelForValue(band.from);
      var xMax = xAxis.getPixelForValue(band.to);
      ctx.save();
      ctx.fillStyle = band.color;
      ctx.fillRect(xMin, yAxis.top, xMax - xMin, yAxis.bottom - yAxis.top);
      ctx.restore();
    });
  }
} : {};

"""

# Agregar datos de cada chart
for spn_id, cfg in spns_to_plot.items():
    sd = series_data[spn_id]
    html += f"makeChart('chart_{spn_id}', '{cfg['label']}', {json.dumps(sd['x'])}, {json.dumps(sd['y'])}, '{cfg['color']}');\n"

html += """
</script>
</body>
</html>"""

with open('data/viaje_simulado_visual.html', 'w', encoding='utf-8') as f:
    f.write(html)

print("Visualización guardada en data/viaje_simulado_visual.html")
print(f"  Mapa: fragmento GPS con anomalías resaltadas")
print(f"  Charts: {len(spns_to_plot)} SPNs con bandas de anomalía")
