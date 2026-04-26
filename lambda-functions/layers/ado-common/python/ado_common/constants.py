"""
constants — Constantes de SPN IDs y agrupaciones funcionales.

Define los 36 identificadores SPN confirmados del catálogo motor_spn
y los agrupa en conjuntos funcionales para uso por los agentes de
combustible y mantenimiento de ADO MobilityIA.

Agrupaciones:
    SPNS_COMBUSTIBLE        15 SPNs relevantes para el agente de combustible.
    SPNS_MANTENIMIENTO      19 SPNs relevantes para el agente de mantenimiento.
    SPNS_DEMO_PRIORITARIOS  21 SPNs prioritarios para el simulador de telemetría.
"""

# ---------------------------------------------------------------------------
# SPN ID Constants — 36 SPNs confirmados del catálogo
# ---------------------------------------------------------------------------

# --- Velocidad y conducción ---
SPN_VELOCIDAD = 84               # Velocidad Km/h
SPN_RPM = 190                    # RPM
SPN_ACELERADOR = 91              # Posición Pedal Acelerador (%)
SPN_FRENO = 521                  # Posición Pedal Freno (%)
SPN_MARCHA = 523                 # Marchas
SPN_TORQUE = 513                 # Porcentaje Torque (%)
SPN_RETARDER_TORQUE = 520        # Retarder Percent Torque (%)

# --- Combustible y rendimiento ---
SPN_TASA_COMBUSTIBLE = 183       # Tasa de combustible (L/h)
SPN_RENDIMIENTO = 185            # Rendimiento (km/L)
SPN_AHORRO_INSTANTANEO = 184     # Ahorro de combustible instantáneo (km/L)
SPN_NIVEL_COMBUSTIBLE = 96       # Nivel Combustible (%)
SPN_COMBUSTIBLE_CONSUMIDO = 250  # Combustible Consumido (L) — inicio_fin

# --- Temperaturas ---
SPN_TEMPERATURA_MOTOR = 110      # Temperatura Motor (°C)
SPN_TEMPERATURA_ACEITE = 175     # Temperatura Aceite Motor (°C)
SPN_TEMPERATURA_AMBIENTE = 171   # Temperatura ambiente (°C)

# --- Presión y niveles de fluidos ---
SPN_PRESION_ACEITE = 100         # Presión Aceite Motor (kPa)
SPN_NIVEL_ACEITE = 98            # Nivel de aceite (%)
SPN_NIVEL_ANTICONGELANTE = 111   # Nivel de anticongelante (%)
SPN_NIVEL_UREA = 1761            # Nivel Urea (%)

# --- Eléctrico ---
SPN_VOLTAJE_BATERIA = 168        # Voltaje Batería (V)

# --- Acumuladores de viaje (inicio_fin) ---
SPN_ODOMETRO = 917               # Odómetro (km)
SPN_HORAS_MOTOR = 247            # Horas Motor (h)

# --- Balatas (frenos) — inicio_fin ---
SPN_BALATA_DEL_IZQ = 1099        # % Restante balata, delantero izquierdo
SPN_BALATA_DEL_DER = 1100        # % Restante balata, delantero derecho
SPN_BALATA_TRAS_IZQ1 = 1101      # % Restante balata, trasero izquierdo 1
SPN_BALATA_TRAS_DER1 = 1102      # % Restante balata, trasero derecho 1
SPN_BALATA_TRAS_IZQ2 = 1103      # % Restante balata, trasero izquierdo 2
SPN_BALATA_TRAS_DER2 = 1104      # % Restante balata, trasero derecho 2

# --- Cruise control y switches ---
SPN_CRUISE_CONTROL_STATES = 527  # Cruise Control States
SPN_CRUISE_CONTROL_ENABLE = 596  # Cruise Control Enable Switch
SPN_BRAKE_SWITCH = 597           # Brake Switch
SPN_CLUTCH_SWITCH = 598          # Clutch Switch
SPN_PARKING_BRAKE = 70           # Interruptor del freno de estacionamiento

# --- Otros ---
SPN_VELOCIDAD_TACOGRAFO = 1624   # Velocidad tacógrafo (km/h)
SPN_NIVEL_ACEITE_LITROS = 10098  # Nivel de aceite litros (l)
SPN_VOLTAJE_BAT_MIN_HIST = 20001 # Voltaje de batería mínimo histórico (V)
SPN_VOLTAJE_BAT_SIN_ALT = 20000  # Voltaje de batería sin alternador (V)

# ---------------------------------------------------------------------------
# Agrupaciones funcionales
# ---------------------------------------------------------------------------

SPNS_COMBUSTIBLE: set[int] = {
    SPN_VELOCIDAD,            # 84  — Velocidad
    SPN_RPM,                  # 190 — RPM
    SPN_ACELERADOR,           # 91  — Acelerador
    SPN_FRENO,                # 521 — Freno
    SPN_MARCHA,               # 523 — Marchas
    SPN_TORQUE,               # 513 — Torque
    SPN_RETARDER_TORQUE,      # 520 — Retarder
    SPN_TASA_COMBUSTIBLE,     # 183 — Tasa combustible L/h
    SPN_RENDIMIENTO,          # 185 — Rendimiento km/L
    SPN_AHORRO_INSTANTANEO,   # 184 — Ahorro instantáneo km/L
    SPN_NIVEL_COMBUSTIBLE,    # 96  — Nivel combustible %
    SPN_COMBUSTIBLE_CONSUMIDO,# 250 — Combustible consumido L
    SPN_CRUISE_CONTROL_STATES,# 527 — Cruise control states
    SPN_CRUISE_CONTROL_ENABLE,# 596 — Cruise control enable
    SPN_TEMPERATURA_AMBIENTE, # 171 — Temperatura ambiente
}

SPNS_MANTENIMIENTO: set[int] = {
    SPN_TEMPERATURA_MOTOR,    # 110  — Temperatura motor
    SPN_TEMPERATURA_ACEITE,   # 175  — Temperatura aceite
    SPN_PRESION_ACEITE,       # 100  — Presión aceite
    SPN_NIVEL_ACEITE,         # 98   — Nivel aceite %
    SPN_NIVEL_ANTICONGELANTE, # 111  — Nivel anticongelante
    SPN_VOLTAJE_BATERIA,      # 168  — Voltaje batería
    SPN_NIVEL_UREA,           # 1761 — Nivel urea
    SPN_RETARDER_TORQUE,      # 520  — Retarder torque
    SPN_ODOMETRO,             # 917  — Odómetro
    SPN_HORAS_MOTOR,          # 247  — Horas motor
    SPN_BALATA_DEL_IZQ,       # 1099 — Balata del. izq.
    SPN_BALATA_DEL_DER,       # 1100 — Balata del. der.
    SPN_BALATA_TRAS_IZQ1,     # 1101 — Balata tras. izq. 1
    SPN_BALATA_TRAS_DER1,     # 1102 — Balata tras. der. 1
    SPN_BALATA_TRAS_IZQ2,     # 1103 — Balata tras. izq. 2
    SPN_BALATA_TRAS_DER2,     # 1104 — Balata tras. der. 2
    SPN_RPM,                  # 190  — RPM
    SPN_TEMPERATURA_AMBIENTE, # 171  — Temperatura ambiente
    SPN_FRENO,                # 521  — Freno (para análisis de desgaste)
}

SPNS_DEMO_PRIORITARIOS: set[int] = {
    # Conducción y rendimiento (core para la demo)
    SPN_VELOCIDAD,            # 84
    SPN_RPM,                  # 190
    SPN_ACELERADOR,           # 91
    SPN_FRENO,                # 521
    SPN_MARCHA,               # 523
    SPN_TORQUE,               # 513
    SPN_TASA_COMBUSTIBLE,     # 183
    SPN_RENDIMIENTO,          # 185
    SPN_AHORRO_INSTANTANEO,   # 184
    SPN_NIVEL_COMBUSTIBLE,    # 96
    # Mantenimiento (señales clave para predicción)
    SPN_TEMPERATURA_MOTOR,    # 110
    SPN_TEMPERATURA_ACEITE,   # 175
    SPN_PRESION_ACEITE,       # 100
    SPN_NIVEL_ACEITE,         # 98
    SPN_NIVEL_ANTICONGELANTE, # 111
    SPN_VOLTAJE_BATERIA,      # 168
    SPN_NIVEL_UREA,           # 1761
    # Balatas (estado de frenos)
    SPN_BALATA_DEL_IZQ,       # 1099
    SPN_BALATA_DEL_DER,       # 1100
    SPN_BALATA_TRAS_IZQ1,     # 1101
    SPN_BALATA_TRAS_DER1,     # 1102
}

# Conjunto de todos los SPN IDs de balatas para iteración rápida
SPNS_BALATAS: set[int] = {
    SPN_BALATA_DEL_IZQ,
    SPN_BALATA_DEL_DER,
    SPN_BALATA_TRAS_IZQ1,
    SPN_BALATA_TRAS_DER1,
    SPN_BALATA_TRAS_IZQ2,
    SPN_BALATA_TRAS_DER2,
}
