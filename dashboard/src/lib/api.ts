import { config } from '../config';
import { getIdToken } from './auth';

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const token = await getIdToken();
  const res = await fetch(`${config.api.baseUrl}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
      ...options?.headers,
    },
  });
  if (!res.ok) throw new Error(`API ${res.status}: ${res.statusText}`);
  return res.json();
}

// --- Types ---

export interface Bus {
  autobus: string;
  viaje_ruta: string;
  viaje_ruta_origen: string;
  viaje_ruta_destino: string;
  operador_desc: string;
  estado_consumo: string;
  spns_fuera_de_rango: number;
  ultimo_timestamp: string;
  alertas_spn: AlertaSPN[];
  latitud?: number;
  longitud?: number;
  velocidad_kmh?: number;
  rpm?: number;
  temperatura_motor_c?: number;
  presion_aceite_kpa?: number;
  tasa_combustible_lh?: number;
  nivel_combustible_pct?: number;
}

export interface AlertaSPN {
  spn_id: number;
  nombre: string;
  valor: number;
  unidad: string;
  mensaje: string;
}

export interface FlotaStatus {
  total_buses: number;
  buses_activos: number;
  resumen_por_estado: Record<string, number>;
  buses: Bus[];
}

export interface Alerta {
  alerta_id: string;
  timestamp: string;
  autobus: string;
  tipo_alerta: string;
  nivel_riesgo: string;
  diagnostico: string;
  urgencia: string;
  componentes: string[];
  numero_referencia: string;
  estado: string;
  agente_origen: string;
  viaje_ruta: string;
  operador_desc: string;
}

export interface AlertasActivas {
  total_alertas: number;
  alertas: Alerta[];
}

export interface RutaResumen {
  viaje_ruta: string;
  total_registros: number;
  total_buses: number;
  buses: string[];
  rendimiento_promedio_kml: number | null;
  resumen_estados: Record<string, number>;
  eficiencia_ruta: string;
}

export interface ResumenConsumo {
  total_rutas: number;
  rutas: RutaResumen[];
}

export interface CO2BusIndicador {
  autobus: string;
  operador: string;
  ruta: string;
  rendimiento_promedio_kml: number;
  co2_estimado_por_viaje_kg: number;
  co2_referencia_por_viaje_kg: number;
  co2_por_km_kg: number;
  clasificacion_ambiental: string;
  tendencia: string;
}

export interface CO2Flota {
  buses_activos: number;
  rendimiento_promedio_kml: number;
  co2_promedio_por_km_kg: number;
  co2_total_estimado_kg: number;
  co2_total_referencia_kg: number;
  ahorro_potencial_co2_kg: number;
  distribucion_ambiental: Record<string, number>;
  descripcion: string;
}

export interface CO2Estimado {
  titulo: string;
  factor_co2: string;
  rendimiento_referencia_kml: number;
  distancia_ruta_km: number;
  co2_referencia_por_viaje_kg: number;
  flota: CO2Flota;
  buses: CO2BusIndicador[];
  cumplimiento_normativo: {
    nom_044: string;
    acuerdo_paris: string;
  };
  // Legacy fields (may not be present in new API)
  estado?: string;
  mensaje?: string;
}

export interface ChatResponse {
  respuesta: string;
  agente_usado: string;
  session_id: string;
  error?: boolean;
}

// --- API calls ---

export const fetchFlotaStatus = () => apiFetch<FlotaStatus>('/dashboard/flota-status');
export const fetchAlertasActivas = () => apiFetch<AlertasActivas>('/dashboard/alertas-activas');
export const fetchResumenConsumo = () => apiFetch<ResumenConsumo>('/dashboard/resumen-consumo');
export const fetchCO2Estimado = () => apiFetch<CO2Estimado>('/dashboard/co2-estimado');

export async function sendChatMessage(prompt: string, agente?: string): Promise<ChatResponse> {
  return apiFetch<ChatResponse>('/chat', {
    method: 'POST',
    body: JSON.stringify({ prompt, agente }),
  });
}
