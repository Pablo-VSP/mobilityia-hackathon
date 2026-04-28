"""
Busca viajes candidatos para "datos trampa" en el consolidado de telemetria.

Uso:
    python find_trap_trips.py --mes 1 --anio 2021 --top 10

Parametros:
    --mes   Mes a filtrar (1-12). Default: 1
    --anio  Anio a filtrar. Default: 2021
    --top   Cantidad de candidatos a mostrar por perfil. Default: 10
"""

import argparse
import pandas as pd
import numpy as np


def parse_args():
    parser = argparse.ArgumentParser(description="Busca viajes candidatos para datos trampa")
    parser.add_argument("--mes", type=int, default=1, help="Mes a filtrar (1-12)")
    parser.add_argument("--anio", type=int, default=2021, help="Anio a filtrar")
    parser.add_argument("--top", type=int, default=10, help="Candidatos a mostrar por perfil")
    return parser.parse_args()


def main():
    args = parse_args()
    mes = args.mes
    anio = args.anio
    top_n = args.top

    print(f"Buscando viajes trampa en {anio}-{mes:02d} (top {top_n} por perfil)")
    print()

    df = pd.read_parquet('consolidated_telemetry.parquet')
    df['EVENTO_FECHA_HORA'] = pd.to_datetime(df['EVENTO_FECHA_HORA'])

    # Filtrar por mes y anio
    periodo = df[
        (df['EVENTO_FECHA_HORA'].dt.year == anio) &
        (df['EVENTO_FECHA_HORA'].dt.month == mes)
    ].copy()

    print(f'Registros {anio}-{mes:02d}: {len(periodo):,}')
    print(f'Viajes unicos: {periodo["VIAJE_ID"].nunique()}')
    print(f'Buses unicos: {periodo["Autobus"].nunique()}')
    print()

    if periodo.empty:
        print("No hay datos para el periodo seleccionado.")
        return

    # Base de viajes
    viajes = periodo.groupby('VIAJE_ID').agg(
        autobus=('Autobus', 'first'),
        operador=('Operador_Desc', 'first'),
        ruta=('VIAJE_RUTA', 'first'),
        fecha_inicio=('EVENTO_FECHA_HORA', 'min'),
        fecha_fin=('EVENTO_FECHA_HORA', 'max'),
        n_registros=('EVENTO_VALOR', 'count'),
    ).reset_index()

    # ============================================================
    # PERFIL 1: Presion aceite baja (SPN 100) + Temp motor alta (SPN 110)
    # ============================================================
    print('=' * 80)
    print('PERFIL 1: Presion aceite baja + Temp motor alta (codigo 100 - CRITICO)')
    print('=' * 80)

    spn100 = periodo[periodo['EVENTO_SPN'] == 100].groupby('VIAJE_ID').agg(
        presion_min=('EVENTO_VALOR', 'min'),
        presion_avg=('EVENTO_VALOR', 'mean'),
        presion_max=('EVENTO_VALOR', 'max'),
        lecturas_100=('EVENTO_VALOR', 'count'),
        lecturas_bajo_150=('EVENTO_VALOR', lambda x: (x <= 150).sum()),
        lecturas_bajo_200=('EVENTO_VALOR', lambda x: (x <= 200).sum()),
    )
    spn110 = periodo[periodo['EVENTO_SPN'] == 110].groupby('VIAJE_ID').agg(
        temp_motor_min=('EVENTO_VALOR', 'min'),
        temp_motor_avg=('EVENTO_VALOR', 'mean'),
        temp_motor_max=('EVENTO_VALOR', 'max'),
        lecturas_110=('EVENTO_VALOR', 'count'),
        lecturas_sobre_100=('EVENTO_VALOR', lambda x: (x >= 100).sum()),
        lecturas_sobre_95=('EVENTO_VALOR', lambda x: (x >= 95).sum()),
    )
    p1 = viajes.merge(spn100, on='VIAJE_ID', how='inner').merge(spn110, on='VIAJE_ID', how='inner')
    p1['score'] = (p1['lecturas_bajo_200'] / p1['lecturas_100']) + (p1['lecturas_sobre_95'] / p1['lecturas_110'])
    p1 = p1.sort_values('score', ascending=False)
    print(f'Viajes con ambos SPNs (100 y 110): {len(p1)}')
    print(f'\nTop {top_n} candidatos:')
    for _, r in p1.head(top_n).iterrows():
        print(f'  VIAJE {r["VIAJE_ID"]} | Bus {r["autobus"]} | {str(r["operador"])[:30]}')
        print(f'    Presion aceite: min={r["presion_min"]:.0f}, avg={r["presion_avg"]:.0f}, max={r["presion_max"]:.0f} kPa | bajo 200: {r["lecturas_bajo_200"]}/{r["lecturas_100"]}')
        print(f'    Temp motor: min={r["temp_motor_min"]:.1f}, avg={r["temp_motor_avg"]:.1f}, max={r["temp_motor_max"]:.1f} C | sobre 95: {r["lecturas_sobre_95"]}/{r["lecturas_110"]}')
        print(f'    Ruta: {r["ruta"]} | Fecha: {r["fecha_inicio"]} a {r["fecha_fin"]}')
        print(f'    Score: {r["score"]:.3f}')
        print()

    # ============================================================
    # PERFIL 2: Voltaje bateria bajo (SPN 168) + Voltaje sin alternador (SPN 20000)
    # ============================================================
    print('=' * 80)
    print('PERFIL 2: Voltaje bateria bajo + Voltaje sin alternador bajo (codigo 158 - ELEVADO)')
    print('=' * 80)

    spn168 = periodo[periodo['EVENTO_SPN'] == 168].groupby('VIAJE_ID').agg(
        volt_min=('EVENTO_VALOR', 'min'),
        volt_avg=('EVENTO_VALOR', 'mean'),
        volt_max=('EVENTO_VALOR', 'max'),
        lecturas_168=('EVENTO_VALOR', 'count'),
        lecturas_bajo_26=('EVENTO_VALOR', lambda x: (x <= 26).sum()),
        lecturas_bajo_25=('EVENTO_VALOR', lambda x: (x <= 25).sum()),
    )
    spn20000 = periodo[periodo['EVENTO_SPN'] == 20000].groupby('VIAJE_ID').agg(
        volt_alt_min=('EVENTO_VALOR', 'min'),
        volt_alt_avg=('EVENTO_VALOR', 'mean'),
        volt_alt_max=('EVENTO_VALOR', 'max'),
        lecturas_20000=('EVENTO_VALOR', 'count'),
    )

    p2_both = viajes.merge(spn168, on='VIAJE_ID', how='inner').merge(spn20000, on='VIAJE_ID', how='inner')
    print(f'Viajes con ambos SPNs (168 y 20000): {len(p2_both)}')
    if len(p2_both) > 0:
        p2_both['score'] = (p2_both['lecturas_bajo_26'] / p2_both['lecturas_168']) + (1 - p2_both['volt_alt_min'] / 30)
        p2_both = p2_both.sort_values('score', ascending=False)
        print(f'Top {top_n} candidatos (ambos SPNs):')
        for _, r in p2_both.head(top_n).iterrows():
            print(f'  VIAJE {r["VIAJE_ID"]} | Bus {r["autobus"]} | {str(r["operador"])[:30]}')
            print(f'    Voltaje bat: min={r["volt_min"]:.1f}, avg={r["volt_avg"]:.1f} V | bajo 26V: {r["lecturas_bajo_26"]}/{r["lecturas_168"]}')
            print(f'    Voltaje sin alt: min={r["volt_alt_min"]:.1f}, avg={r["volt_alt_avg"]:.1f} V')
            print(f'    Ruta: {r["ruta"]} | Fecha: {r["fecha_inicio"]} a {r["fecha_fin"]}')
            print()

    p2_solo = viajes.merge(spn168, on='VIAJE_ID', how='inner').sort_values('volt_min')
    print(f'\nViajes solo con SPN 168: {len(p2_solo)}')
    print(f'Top {top_n} con voltaje mas bajo:')
    for _, r in p2_solo.head(top_n).iterrows():
        print(f'  VIAJE {r["VIAJE_ID"]} | Bus {r["autobus"]} | volt min={r["volt_min"]:.1f}, avg={r["volt_avg"]:.1f} V | bajo 26V: {r["lecturas_bajo_26"]}/{r["lecturas_168"]}')
    print()

    # ============================================================
    # PERFIL 3: Balatas desgastadas (SPN 1099-1104) o uso excesivo de freno (SPN 521)
    # ============================================================
    print('=' * 80)
    print('PERFIL 3: Balatas desgastadas / uso excesivo de freno (codigo 86 - ELEVADO)')
    print('=' * 80)

    spns_balatas = [1099, 1100, 1101, 1102, 1103, 1104]
    bal_data = periodo[periodo['EVENTO_SPN'].isin(spns_balatas)]
    print(f'Registros de balatas: {len(bal_data)}')

    if len(bal_data) > 0:
        bal_viaje = bal_data.groupby('VIAJE_ID').agg(
            balata_min=('EVENTO_VALOR', 'min'),
            balata_avg=('EVENTO_VALOR', 'mean'),
            lecturas_bal=('EVENTO_VALOR', 'count'),
            lecturas_bajo_20=('EVENTO_VALOR', lambda x: (x < 20).sum()),
        )
        p3 = viajes.merge(bal_viaje, on='VIAJE_ID', how='inner').sort_values('balata_min')
        print(f'Viajes con datos de balatas: {len(p3)}')
        print(f'Top {top_n} con balatas mas bajas:')
        for _, r in p3.head(top_n).iterrows():
            print(f'  VIAJE {r["VIAJE_ID"]} | Bus {r["autobus"]} | balata min={r["balata_min"]:.1f}%, avg={r["balata_avg"]:.1f}% | bajo 20%: {r["lecturas_bajo_20"]}/{r["lecturas_bal"]}')
    else:
        print('NO hay datos de balatas en este periodo')
        spn521 = periodo[periodo['EVENTO_SPN'] == 521].groupby('VIAJE_ID').agg(
            freno_avg=('EVENTO_VALOR', 'mean'),
            freno_max=('EVENTO_VALOR', 'max'),
            lecturas_521=('EVENTO_VALOR', 'count'),
            lecturas_freno_alto=('EVENTO_VALOR', lambda x: (x >= 30).sum()),
        )
        p3_alt = viajes.merge(spn521, on='VIAJE_ID', how='inner').sort_values('freno_max', ascending=False)
        print(f'\nAlternativa: Viajes con uso excesivo de freno (SPN 521): {len(p3_alt)}')
        print(f'Top {top_n} con mayor uso de freno:')
        for _, r in p3_alt.head(top_n).iterrows():
            print(f'  VIAJE {r["VIAJE_ID"]} | Bus {r["autobus"]} | freno avg={r["freno_avg"]:.1f}%, max={r["freno_max"]:.1f}% | alto (>30%): {r["lecturas_freno_alto"]}/{r["lecturas_521"]}')
    print()

    # ============================================================
    # PERFIL 4: Bus con senales normales (BAJO)
    # ============================================================
    print('=' * 80)
    print('PERFIL 4: Bus con senales normales (BAJO - control)')
    print('=' * 80)

    normal = viajes.merge(spn100, on='VIAJE_ID', how='inner').merge(spn110, on='VIAJE_ID', how='inner')
    normal = normal[
        (normal['presion_min'] >= 200) &
        (normal['temp_motor_max'] <= 100) &
        (normal['temp_motor_min'] >= 80)
    ].sort_values('n_registros', ascending=False)
    print(f'Viajes con senales completamente normales: {len(normal)}')
    print(f'Top {top_n}:')
    for _, r in normal.head(top_n).iterrows():
        print(f'  VIAJE {r["VIAJE_ID"]} | Bus {r["autobus"]} | {str(r["operador"])[:30]}')
        print(f'    Presion aceite: min={r["presion_min"]:.0f}, avg={r["presion_avg"]:.0f} kPa')
        print(f'    Temp motor: min={r["temp_motor_min"]:.1f}, avg={r["temp_motor_avg"]:.1f}, max={r["temp_motor_max"]:.1f} C')
        print(f'    Registros: {r["n_registros"]} | Ruta: {r["ruta"]}')
        print(f'    Fecha: {r["fecha_inicio"]} a {r["fecha_fin"]}')
        print()

    # ============================================================
    # PERFIL 5: Caso mixto/moderado
    # ============================================================
    print('=' * 80)
    print('PERFIL 5: Caso mixto/moderado - multiples senales leves')
    print('=' * 80)

    spn175 = periodo[periodo['EVENTO_SPN'] == 175].groupby('VIAJE_ID').agg(
        temp_aceite_avg=('EVENTO_VALOR', 'mean'),
        temp_aceite_max=('EVENTO_VALOR', 'max'),
        lecturas_175=('EVENTO_VALOR', 'count'),
        lecturas_sobre_110=('EVENTO_VALOR', lambda x: (x >= 110).sum()),
    )
    spn190 = periodo[periodo['EVENTO_SPN'] == 190].groupby('VIAJE_ID').agg(
        rpm_avg=('EVENTO_VALOR', 'mean'),
        rpm_max=('EVENTO_VALOR', 'max'),
        lecturas_190=('EVENTO_VALOR', 'count'),
        lecturas_sobre_1800=('EVENTO_VALOR', lambda x: (x >= 1800).sum()),
    )
    spn96 = periodo[periodo['EVENTO_SPN'] == 96].groupby('VIAJE_ID').agg(
        combustible_min=('EVENTO_VALOR', 'min'),
        combustible_avg=('EVENTO_VALOR', 'mean'),
        lecturas_96=('EVENTO_VALOR', 'count'),
    )

    p5 = viajes.merge(spn175, on='VIAJE_ID', how='inner').merge(spn190, on='VIAJE_ID', how='inner').merge(spn96, on='VIAJE_ID', how='inner')
    p5['score'] = (p5['lecturas_sobre_110'] / p5['lecturas_175'].clip(lower=1)) + \
                  (p5['lecturas_sobre_1800'] / p5['lecturas_190'].clip(lower=1)) + \
                  (1 - p5['combustible_min'] / 100)
    p5 = p5.sort_values('score', ascending=False)
    print(f'Viajes con SPNs 175, 190 y 96: {len(p5)}')
    print(f'Top {top_n} candidatos mixtos:')
    for _, r in p5.head(top_n).iterrows():
        print(f'  VIAJE {r["VIAJE_ID"]} | Bus {r["autobus"]} | {str(r["operador"])[:30]}')
        print(f'    Temp aceite: avg={r["temp_aceite_avg"]:.1f}, max={r["temp_aceite_max"]:.1f} C | sobre 110: {r["lecturas_sobre_110"]}/{r["lecturas_175"]}')
        print(f'    RPM: avg={r["rpm_avg"]:.0f}, max={r["rpm_max"]:.0f} | sobre 1800: {r["lecturas_sobre_1800"]}/{r["lecturas_190"]}')
        print(f'    Combustible: min={r["combustible_min"]:.1f}%, avg={r["combustible_avg"]:.1f}%')
        print(f'    Ruta: {r["ruta"]} | Fecha: {r["fecha_inicio"]} a {r["fecha_fin"]}')
        print()


if __name__ == "__main__":
    main()
