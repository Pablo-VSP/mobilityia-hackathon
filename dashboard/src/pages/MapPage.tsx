import { useEffect, useState, useCallback, useRef } from 'react';
import { MapContainer, TileLayer, Marker, Popup, useMap } from 'react-leaflet';
import L from 'leaflet';
import { fetchFlotaStatus, type Bus, fetchAlertasActivas, type Alerta, sendChatMessage } from '../lib/api';
import { config } from '../config';
import StatusBadge from '../components/StatusBadge';
import { AlertTriangle, Fuel, Thermometer, Gauge, MessageSquare, RefreshCw, Send, X, Bot, Loader2 } from 'lucide-react';
import MarkdownContent from '../components/MarkdownContent';
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
      transition: all 0.3s ease;
    ">🚌</div>`,
  });
}

// Smooth marker animation component
function AnimatedMarker({ bus, onClick }: { bus: Bus; onClick: () => void }) {
  const markerRef = useRef<L.Marker>(null);
  const prevPos = useRef<[number, number] | null>(null);

  useEffect(() => {
    if (!bus.latitud || !bus.longitud || bus.latitud === 0) return;
    const newPos: [number, number] = [bus.latitud, bus.longitud];

    if (markerRef.current && prevPos.current) {
      // Animate from previous position to new position
      const marker = markerRef.current;
      const start = prevPos.current;
      const end = newPos;
      const duration = 2000; // 2 seconds
      const startTime = performance.now();

      function animate(currentTime: number) {
        const elapsed = currentTime - startTime;
        const progress = Math.min(elapsed / duration, 1);
        // Ease-in-out
        const eased = progress < 0.5
          ? 2 * progress * progress
          : 1 - Math.pow(-2 * progress + 2, 2) / 2;

        const lat = start[0] + (end[0] - start[0]) * eased;
        const lng = start[1] + (end[1] - start[1]) * eased;
        marker.setLatLng([lat, lng]);

        if (progress < 1) {
          requestAnimationFrame(animate);
        }
      }

      requestAnimationFrame(animate);
    }

    prevPos.current = newPos;
  }, [bus.latitud, bus.longitud]);

  if (!bus.latitud || !bus.longitud || bus.latitud === 0) return null;

  return (
    <Marker
      ref={markerRef}
      position={[bus.latitud, bus.longitud]}
      icon={busIcon(bus.estado_consumo)}
      eventHandlers={{ click: onClick }}
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
              <p className="text-white font-semibold">{bus.velocidad_kmh?.toFixed(0) ?? '—'} km/h</p>
            </div>
            <div className="bg-slate-700/50 rounded-lg p-2">
              <div className="flex items-center gap-1 text-slate-400 text-xs mb-1">
                <Fuel className="w-3 h-3" /> Combustible
              </div>
              <p className="text-white font-semibold">{bus.tasa_combustible_lh?.toFixed(1) ?? '—'} L/h</p>
            </div>
            <div className="bg-slate-700/50 rounded-lg p-2">
              <div className="flex items-center gap-1 text-slate-400 text-xs mb-1">
                <Thermometer className="w-3 h-3" /> Motor
              </div>
              <p className="text-white font-semibold">{bus.temperatura_motor_c?.toFixed(0) ?? '—'}°C</p>
            </div>
            <div className="bg-slate-700/50 rounded-lg p-2">
              <div className="flex items-center gap-1 text-slate-400 text-xs mb-1">RPM</div>
              <p className="text-white font-semibold">{bus.rpm?.toFixed(0) ?? '—'}</p>
            </div>
          </div>
          {bus.alertas_spn.length > 0 && (
            <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-2 mb-3">
              <p className="text-red-400 text-xs font-medium mb-1">⚠ {bus.alertas_spn.length} alerta(s) activa(s)</p>
              {bus.alertas_spn.slice(0, 2).map((a, i) => (
                <p key={i} className="text-red-300 text-xs">{a.mensaje}</p>
              ))}
            </div>
          )}
        </div>
      </Popup>
    </Marker>
  );
}

function FitBounds({ buses }: { buses: Bus[] }) {
  const map = useMap();
  const fitted = useRef(false);
  useEffect(() => {
    if (fitted.current) return;
    const valid = buses.filter(b => b.latitud && b.longitud && b.latitud !== 0);
    if (valid.length > 0) {
      const bounds = L.latLngBounds(valid.map(b => [b.latitud!, b.longitud!]));
      map.fitBounds(bounds, { padding: [50, 50], maxZoom: 10 });
      fitted.current = true;
    }
  }, [buses, map]);
  return null;
}

// Inline chat panel
function InlineChat({ busId, context, onClose }: { busId: string; context?: string; onClose: () => void }) {
  const [messages, setMessages] = useState<{ role: 'user' | 'assistant'; text: string; loading?: boolean }[]>([]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);

  // Auto-send initial analysis
  useEffect(() => {
    const prompt = context
      ? `Analiza el bus ${busId}. Contexto: ${context}`
      : `Analiza el estado completo del bus ${busId}: consumo de combustible y estado mecánico`;
    handleSend(prompt);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = async (text?: string) => {
    const prompt = text || input.trim();
    if (!prompt || sending) return;
    setInput('');
    setSending(true);
    setMessages(prev => [...prev, { role: 'user', text: prompt }, { role: 'assistant', text: '', loading: true }]);

    try {
      const resp = await sendChatMessage(prompt, 'ambos');
      setMessages(prev => {
        const updated = [...prev];
        updated[updated.length - 1] = { role: 'assistant', text: resp.respuesta };
        return updated;
      });
    } catch (err: any) {
      setMessages(prev => {
        const updated = [...prev];
        updated[updated.length - 1] = { role: 'assistant', text: `Error: ${err.message}` };
        return updated;
      });
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="flex flex-col h-full">
      <div className="p-3 border-b border-slate-700 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-2">
          <Bot className="w-4 h-4 text-red-400" />
          <span className="text-white font-semibold text-sm">Agente IA — Bus {busId}</span>
        </div>
        <button onClick={onClose} className="text-slate-400 hover:text-white"><X className="w-4 h-4" /></button>
      </div>
      <div className="flex-1 overflow-y-auto p-3 space-y-3">
        {messages.map((m, i) => (
          <div key={i} className={`${m.role === 'user' ? 'text-right' : ''}`}>
            {m.role === 'user' ? (
              <span className="inline-block bg-red-600 text-white text-xs px-3 py-2 rounded-xl max-w-[90%] text-left">{m.text}</span>
            ) : m.loading ? (
              <div className="flex items-center gap-2 text-slate-400 text-xs">
                <Loader2 className="w-3 h-3 animate-spin" /> Analizando...
              </div>
            ) : (
              <div className="bg-slate-700/50 rounded-xl px-3 py-2 text-xs">
                <MarkdownContent compact>{m.text}</MarkdownContent>
              </div>
            )}
          </div>
        ))}
        <div ref={endRef} />
      </div>
      <form onSubmit={e => { e.preventDefault(); handleSend(); }} className="p-2 border-t border-slate-700 flex gap-1 shrink-0">
        <input
          value={input}
          onChange={e => setInput(e.target.value)}
          placeholder="Pregunta más..."
          disabled={sending}
          className="flex-1 px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white text-xs placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-red-500 disabled:opacity-50"
        />
        <button type="submit" disabled={sending || !input.trim()} className="px-3 py-2 bg-red-600 hover:bg-red-700 disabled:bg-slate-700 text-white rounded-lg">
          <Send className="w-3 h-3" />
        </button>
      </form>
    </div>
  );
}

export default function MapPage() {
  const [buses, setBuses] = useState<Bus[]>([]);
  const [alertas, setAlertas] = useState<Alerta[]>([]);
  const [selectedBus, setSelectedBus] = useState<string | null>(null);
  const [chatBus, setChatBus] = useState<{ id: string; context?: string } | null>(null);
  const [loading, setLoading] = useState(true);
  const busCache = useRef<Map<string, Bus>>(new Map());

  const loadData = useCallback(async () => {
    try {
      const [flota, alertasData] = await Promise.all([
        fetchFlotaStatus(),
        fetchAlertasActivas(),
      ]);
      // Merge new data into cache — keep last known state for buses that disappear
      for (const bus of flota.buses) {
        busCache.current.set(bus.autobus, bus);
      }
      setBuses([...busCache.current.values()]);
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

  const openChat = (autobus: string, context?: string) => {
    setChatBus({ id: autobus, context });
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

          {buses.map(bus => (
            <AnimatedMarker
              key={bus.autobus}
              bus={bus}
              onClick={() => setSelectedBus(bus.autobus)}
            />
          ))}
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
              <p className="text-slate-400">Total</p>
            </div>
            <div className="text-center">
              <p className="text-2xl font-bold text-emerald-400">
                {buses.filter(b => b.estado_consumo === 'EFICIENTE').length}
              </p>
              <p className="text-slate-400">Eficientes</p>
            </div>
            <div className="text-center">
              <p className="text-2xl font-bold text-amber-400">
                {buses.filter(b => b.estado_consumo === 'ALERTA_MODERADA').length}
              </p>
              <p className="text-slate-400">Moderada</p>
            </div>
            <div className="text-center">
              <p className="text-2xl font-bold text-red-400">
                {buses.filter(b => b.estado_consumo === 'ALERTA_SIGNIFICATIVA').length}
              </p>
              <p className="text-slate-400">Alerta</p>
            </div>
            {buses.some(b => b.estado_consumo === 'SIN_DATOS') && (
              <div className="text-center">
                <p className="text-2xl font-bold text-slate-400">
                  {buses.filter(b => b.estado_consumo === 'SIN_DATOS').length}
                </p>
                <p className="text-slate-400">Sin datos</p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Right panel — Chat or Alerts */}
      <div className="w-80 bg-slate-900 border-l border-slate-800 flex flex-col shrink-0">
        {chatBus ? (
          <InlineChat
            busId={chatBus.id}
            context={chatBus.context}
            onClose={() => setChatBus(null)}
          />
        ) : (
          <>
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
                    onClick={e => {
                      e.stopPropagation();
                      const alertMsgs = bus.alertas_spn.map(a => a.mensaje).join('; ');
                      openChat(bus.autobus, alertMsgs || undefined);
                    }}
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
                        <span className="text-amber-400 text-xs">{alerta.urgencia.replace(/_/g, ' ')}</span>
                      </div>
                      <button
                        onClick={() => openChat(alerta.autobus, `Tiene alerta ${alerta.nivel_riesgo}: ${alerta.diagnostico}`)}
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
          </>
        )}
      </div>
    </div>
  );
}
