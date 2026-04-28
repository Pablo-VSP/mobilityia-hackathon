import { useEffect, useState, useCallback } from 'react';
import { MapContainer, TileLayer, Marker, Popup, useMap } from 'react-leaflet';
import L from 'leaflet';
import { useNavigate } from 'react-router-dom';
import { fetchFlotaStatus, type Bus, fetchAlertasActivas, type Alerta } from '../lib/api';
import { config } from '../config';
import StatusBadge from '../components/StatusBadge';
import { AlertTriangle, Fuel, Thermometer, Gauge, MessageSquare, RefreshCw } from 'lucide-react';
import 'leaflet/dist/leaflet.css';

// Bus marker icons by status
function busIcon(estado: string): L.DivIcon {
  const colors: Record<string, string> = {
    EFICIENTE: '#10b981',
    ALERTA_MODERADA: '#f59e0b',
    ALERTA_SIGNIFICATIVA: '#ef4444',
    SIN_DATOS: '#6b7280',
  };
  const color = colors[estado] || colors.SIN_DATOS;
  return L.divIcon({
    className: '',
    iconSize: [36, 36],
    iconAnchor: [18, 18],
    popupAnchor: [0, -20],
    html: `<div style="
      width:36px;height:36px;border-radius:50%;
      background:${color};border:3px solid white;
      box-shadow:0 2px 8px rgba(0,0,0,0.4);
      display:flex;align-items:center;justify-content:center;
      font-size:11px;font-weight:700;color:white;
    ">🚌</div>`,
  });
}

function FitBounds({ buses }: { buses: Bus[] }) {
  const map = useMap();
  useEffect(() => {
    const valid = buses.filter(b => b.latitud && b.longitud && b.latitud !== 0);
    if (valid.length > 0) {
      const bounds = L.latLngBounds(valid.map(b => [b.latitud!, b.longitud!]));
      map.fitBounds(bounds, { padding: [50, 50], maxZoom: 10 });
    }
  }, [buses, map]);
  return null;
}

export default function MapPage() {
  const [buses, setBuses] = useState<Bus[]>([]);
  const [alertas, setAlertas] = useState<Alerta[]>([]);
  const [selectedBus, setSelectedBus] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  const loadData = useCallback(async () => {
    try {
      const [flota, alertasData] = await Promise.all([
        fetchFlotaStatus(),
        fetchAlertasActivas(),
      ]);
      setBuses(flota.buses);
      setAlertas(alertasData.alertas);
    } catch (err) {
      console.error('Error loading fleet data:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, config.polling.fleetIntervalMs);
    return () => clearInterval(interval);
  }, [loadData]);

  const busesWithAlerts = buses.filter(
    b => b.estado_consumo !== 'EFICIENTE' && b.estado_consumo !== 'SIN_DATOS'
  );

  const openChat = (autobus: string) => {
    navigate(`/chat?bus=${autobus}`);
  };

  return (
    <div className="flex h-full">
      {/* Map */}
      <div className="flex-1 relative">
        <MapContainer
          center={config.map.center}
          zoom={config.map.zoom}
          className="h-full w-full"
          zoomControl={false}
        >
          <TileLayer url={config.map.tileUrl} attribution={config.map.tileAttribution} />
          <FitBounds buses={buses} />

          {buses.map(bus => {
            if (!bus.latitud || !bus.longitud || bus.latitud === 0) return null;
            return (
              <Marker
                key={bus.autobus}
                position={[bus.latitud, bus.longitud]}
                icon={busIcon(bus.estado_consumo)}
                eventHandlers={{ click: () => setSelectedBus(bus.autobus) }}
              >
                <Popup maxWidth={320}>
                  <div className="min-w-[280px]">
                    <div className="flex items-center justify-between mb-3">
                      <h3 className="text-lg font-bold text-white">Bus {bus.autobus}</h3>
                      <StatusBadge status={bus.estado_consumo} />
                    </div>

                    <div className="text-sm text-slate-300 mb-3">
                      <p className="font-medium text-slate-200">{bus.viaje_ruta}</p>
                      <p className="text-slate-400">{bus.operador_desc || 'Operador no disponible'}</p>
                    </div>

                    <div className="grid grid-cols-2 gap-2 mb-3">
                      <div className="bg-slate-700/50 rounded-lg p-2">
                        <div className="flex items-center gap-1 text-slate-400 text-xs mb-1">
                          <Gauge className="w-3 h-3" /> Velocidad
                        </div>
                        <p className="text-white font-semibold">
                          {bus.velocidad_kmh?.toFixed(0) ?? '—'} km/h
                        </p>
                      </div>
                      <div className="bg-slate-700/50 rounded-lg p-2">
                        <div className="flex items-center gap-1 text-slate-400 text-xs mb-1">
                          <Fuel className="w-3 h-3" /> Combustible
                        </div>
                        <p className="text-white font-semibold">
                          {bus.tasa_combustible_lh?.toFixed(1) ?? '—'} L/h
                        </p>
                      </div>
                      <div className="bg-slate-700/50 rounded-lg p-2">
                        <div className="flex items-center gap-1 text-slate-400 text-xs mb-1">
                          <Thermometer className="w-3 h-3" /> Motor
                        </div>
                        <p className="text-white font-semibold">
                          {bus.temperatura_motor_c?.toFixed(0) ?? '—'}°C
                        </p>
                      </div>
                      <div className="bg-slate-700/50 rounded-lg p-2">
                        <div className="flex items-center gap-1 text-slate-400 text-xs mb-1">
                          RPM
                        </div>
                        <p className="text-white font-semibold">
                          {bus.rpm?.toFixed(0) ?? '—'}
                        </p>
                      </div>
                    </div>

                    {bus.alertas_spn.length > 0 && (
                      <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-2 mb-3">
                        <p className="text-red-400 text-xs font-medium mb-1">
                          ⚠ {bus.alertas_spn.length} alerta(s) activa(s)
                        </p>
                        {bus.alertas_spn.slice(0, 2).map((a, i) => (
                          <p key={i} className="text-red-300 text-xs">{a.mensaje}</p>
                        ))}
                      </div>
                    )}

                    <button
                      onClick={() => openChat(bus.autobus)}
                      className="w-full flex items-center justify-center gap-2 py-2 bg-red-600 hover:bg-red-700 text-white text-sm font-medium rounded-lg transition-colors"
                    >
                      <MessageSquare className="w-4 h-4" />
                      Preguntar al Agente IA
                    </button>
                  </div>
                </Popup>
              </Marker>
            );
          })}
        </MapContainer>

        {/* Top-left stats overlay */}
        <div className="absolute top-4 left-4 z-[1000] bg-slate-900/90 backdrop-blur rounded-xl p-4 border border-slate-700">
          <h2 className="text-white font-bold text-sm mb-2 flex items-center gap-2">
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            Flota en Tiempo Real
          </h2>
          <div className="flex gap-3 text-xs">
            <div className="text-center">
              <p className="text-2xl font-bold text-white">{buses.length}</p>
              <p className="text-slate-400">Activos</p>
            </div>
            <div className="text-center">
              <p className="text-2xl font-bold text-emerald-400">
                {buses.filter(b => b.estado_consumo === 'EFICIENTE').length}
              </p>
              <p className="text-slate-400">Eficientes</p>
            </div>
            <div className="text-center">
              <p className="text-2xl font-bold text-red-400">
                {buses.filter(b => b.estado_consumo === 'ALERTA_SIGNIFICATIVA').length}
              </p>
              <p className="text-slate-400">Alerta</p>
            </div>
          </div>
        </div>
      </div>

      {/* Right panel — Vehicles with relevant status */}
      <div className="w-80 bg-slate-900 border-l border-slate-800 flex flex-col shrink-0">
        <div className="p-4 border-b border-slate-800">
          <h2 className="text-white font-bold flex items-center gap-2">
            <AlertTriangle className="w-5 h-5 text-amber-400" />
            Vehículos con Alertas
          </h2>
          <p className="text-slate-400 text-xs mt-1">
            {busesWithAlerts.length} vehículo(s) requieren atención
          </p>
        </div>

        <div className="flex-1 overflow-y-auto p-2 space-y-2">
          {busesWithAlerts.length === 0 && (
            <div className="text-center text-slate-500 py-8">
              <p className="text-sm">Todos los vehículos operan con normalidad</p>
            </div>
          )}

          {busesWithAlerts.map(bus => (
            <div
              key={bus.autobus}
              className={`p-3 rounded-xl border transition-colors cursor-pointer ${
                selectedBus === bus.autobus
                  ? 'bg-slate-700/50 border-red-500/50'
                  : 'bg-slate-800/50 border-slate-700 hover:border-slate-600'
              }`}
              onClick={() => setSelectedBus(bus.autobus)}
            >
              <div className="flex items-center justify-between mb-2">
                <span className="text-white font-bold">Bus {bus.autobus}</span>
                <StatusBadge status={bus.estado_consumo} />
              </div>
              <p className="text-slate-400 text-xs truncate">{bus.viaje_ruta}</p>
              <p className="text-slate-500 text-xs">{bus.operador_desc || '—'}</p>

              {bus.spns_fuera_de_rango > 0 && (
                <p className="text-amber-400 text-xs mt-1">
                  ⚠ {bus.spns_fuera_de_rango} señal(es) fuera de rango
                </p>
              )}

              <button
                onClick={e => { e.stopPropagation(); openChat(bus.autobus); }}
                className="mt-2 w-full flex items-center justify-center gap-1 py-1.5 bg-slate-700 hover:bg-red-600 text-slate-300 hover:text-white text-xs font-medium rounded-lg transition-colors"
              >
                <MessageSquare className="w-3 h-3" />
                Consultar Agente
              </button>
            </div>
          ))}

          {/* Active alerts section */}
          {alertas.length > 0 && (
            <>
              <div className="pt-3 pb-1 px-1">
                <h3 className="text-slate-400 text-xs font-semibold uppercase tracking-wider">
                  Alertas de Mantenimiento
                </h3>
              </div>
              {alertas.map(alerta => (
                <div
                  key={alerta.alerta_id}
                  className="p-3 rounded-xl bg-red-500/5 border border-red-500/20"
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-white font-bold text-sm">Bus {alerta.autobus}</span>
                    <StatusBadge status={alerta.nivel_riesgo} />
                  </div>
                  <p className="text-slate-300 text-xs">{alerta.diagnostico}</p>
                  <div className="flex items-center gap-2 mt-2">
                    <span className="text-slate-500 text-xs">{alerta.numero_referencia}</span>
                    <span className="text-slate-600">·</span>
                    <span className="text-amber-400 text-xs">{alerta.urgencia.replace('_', ' ')}</span>
                  </div>
                  <button
                    onClick={() => openChat(alerta.autobus)}
                    className="mt-2 w-full flex items-center justify-center gap-1 py-1.5 bg-red-600/20 hover:bg-red-600 text-red-400 hover:text-white text-xs font-medium rounded-lg transition-colors"
                  >
                    <MessageSquare className="w-3 h-3" />
                    Preguntar sobre esta alerta
                  </button>
                </div>
              ))}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
