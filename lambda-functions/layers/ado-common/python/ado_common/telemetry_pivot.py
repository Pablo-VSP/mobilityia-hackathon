"""
telemetry_pivot — Pivoteo de registros por-SPN a estado consolidado de autobús.

Transforma una lista de registros de telemetría (un registro por lectura
de sensor/SPN) en un diccionario consolidado por autobús que incluye:

  - Campos planos (flat fields) para consultas directas en DynamoDB
  - Mapa spn_valores con detalle por SPN
  - Lista alertas_spn con SPNs fuera de rango
  - Contexto de viaje (autobus, viaje_id, operador, ruta, GPS)

Cada registro de entrada tiene la estructura del modelo telemetry-data:
    viaje_id, autobus, operador_cve, operador_desc, evento_fecha,
    evento_fecha_hora, evento_spn, evento_descripcion, evento_valor,
    evento_latitud, evento_longitud, viaje_ruta, viaje_ruta_origen,
    viaje_ruta_destino, evento_protocolo, evento_firmware, evento_version

Requisitos: 1.6, 1.7
"""

import logging

from .spn_catalog import obtener_spn, valor_fuera_de_rango
from .constants import SPNS_DEMO_PRIORITARIOS

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# ---------------------------------------------------------------------------
# Mapeo SPN ID → nombre corto para campos planos en DynamoDB (Req 1.7)
# 28 SPNs mapeados según la tabla SPN-to-Flat-Field del diseño
# ---------------------------------------------------------------------------

SPN_NOMBRE_CORTO: dict[int, str] = {
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
    1103: "balata_tras_izq2_pct",
    1104: "balata_tras_der2_pct",
}


def pivotar_telemetria(
    registros: list[dict],
    catalogo_spn: dict[int, dict],
    solo_prioritarios: bool = True,
) -> dict:
    """
    Pivotea una lista de registros por-SPN en un estado consolidado de autobús.

    Toma N registros (cada uno con un evento_spn y evento_valor) y produce
    un único diccionario con:
      - Contexto de viaje: autobus, viaje_id, operador_cve, operador_desc,
        viaje_ruta, viaje_ruta_origen, viaje_ruta_destino, latitud, longitud
      - Campos planos: velocidad_kmh, rpm, temperatura_motor_c, etc.
        (solo para SPNs con mapeo en SPN_NOMBRE_CORTO)
      - spn_valores: {str(spn_id): {valor, name, unidad, fuera_de_rango}}
      - alertas_spn: [{spn_id, name, valor, unidad, mensaje}]

    Args:
        registros: Lista de dicts con la estructura de telemetry-data.
                   Cada registro tiene evento_spn (int) y evento_valor (float).
        catalogo_spn: Diccionario retornado por cargar_catalogo_spn().
        solo_prioritarios: Si True, solo procesa SPNs en SPNS_DEMO_PRIORITARIOS.
                          Si False, procesa todos los SPNs encontrados.

    Returns:
        Diccionario consolidado con el estado del autobús.
        Retorna dict vacío si no hay registros.
    """
    if not registros:
        return {}

    # --- Extraer contexto de viaje del primer registro disponible ---
    primer_registro = registros[0]
    estado: dict = {
        # Contexto de viaje
        "autobus": str(primer_registro.get("autobus", "")),
        "viaje_id": primer_registro.get("viaje_id"),
        "operador_cve": str(primer_registro.get("operador_cve", "")),
        "operador_desc": str(primer_registro.get("operador_desc", "")),
        "viaje_ruta": str(primer_registro.get("viaje_ruta", "")),
        "viaje_ruta_origen": str(primer_registro.get("viaje_ruta_origen", "")),
        "viaje_ruta_destino": str(primer_registro.get("viaje_ruta_destino", "")),
        "latitud": primer_registro.get("evento_latitud"),
        "longitud": primer_registro.get("evento_longitud"),
        # Contenedores para datos pivoteados
        "spn_valores": {},
        "alertas_spn": [],
    }

    # --- Pivotear cada registro SPN ---
    for registro in registros:
        spn_id = registro.get("evento_spn")
        if spn_id is None:
            continue

        spn_id = int(spn_id)

        # Filtrar por SPNs prioritarios si se solicita
        if solo_prioritarios and spn_id not in SPNS_DEMO_PRIORITARIOS:
            continue

        valor = registro.get("evento_valor")
        if valor is None:
            continue

        try:
            valor = float(valor)
        except (ValueError, TypeError):
            continue

        # Buscar info del catálogo
        spn_info = obtener_spn(catalogo_spn, spn_id)
        spn_name = spn_info["name"] if spn_info else f"SPN_{spn_id}"
        spn_unidad = spn_info["unidad"] if spn_info else ""

        # Verificar si está fuera de rango
        fuera_rango, mensaje = valor_fuera_de_rango(catalogo_spn, spn_id, valor)

        # Agregar al mapa spn_valores
        estado["spn_valores"][str(spn_id)] = {
            "valor": valor,
            "name": spn_name,
            "unidad": spn_unidad,
            "fuera_de_rango": fuera_rango,
        }

        # Agregar campo plano si tiene mapeo
        nombre_corto = SPN_NOMBRE_CORTO.get(spn_id)
        if nombre_corto:
            estado[nombre_corto] = valor

        # Registrar alerta si está fuera de rango
        if fuera_rango:
            estado["alertas_spn"].append({
                "spn_id": spn_id,
                "name": spn_name,
                "valor": valor,
                "unidad": spn_unidad,
                "mensaje": mensaje,
            })

        # Actualizar GPS con el registro más reciente que tenga coordenadas
        lat = registro.get("evento_latitud")
        lon = registro.get("evento_longitud")
        if lat is not None and lon is not None:
            estado["latitud"] = lat
            estado["longitud"] = lon

    return estado
