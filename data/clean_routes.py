import json

# Ruta IDA
with open('data/ruta_ida_2704712.json', 'r', encoding='utf-8') as f:
    ida = json.load(f)

ida_clean = {
    "tipo": "ida",
    "origen": "MEXICO TAXQUENA",
    "destino": "ACAPULCO COSTERA",
    "puntos_gps": ida["puntos_gps"],
    "coordenadas": ida["coordenadas"]
}

with open('data/ruta_ida_2704712.json', 'w', encoding='utf-8') as f:
    json.dump(ida_clean, f, ensure_ascii=False, indent=2)

# Ruta REGRESO
with open('data/ruta_regreso_2725965.json', 'r', encoding='utf-8') as f:
    regreso = json.load(f)

regreso_clean = {
    "tipo": "regreso",
    "origen": "ACAPULCO COSTERA",
    "destino": "MEXICO TAXQUENA",
    "puntos_gps": regreso["puntos_gps"],
    "coordenadas": regreso["coordenadas"]
}

with open('data/ruta_regreso_2725965.json', 'w', encoding='utf-8') as f:
    json.dump(regreso_clean, f, ensure_ascii=False, indent=2)

print("Listo. JSONs limpiados:")
print(f"  ruta_ida_2704712.json: MEXICO TAXQUENA -> ACAPULCO COSTERA ({ida_clean['puntos_gps']} puntos)")
print(f"  ruta_regreso_2725965.json: ACAPULCO COSTERA -> MEXICO TAXQUENA ({regreso_clean['puntos_gps']} puntos)")
