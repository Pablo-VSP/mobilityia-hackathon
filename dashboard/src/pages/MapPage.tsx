import { useEffect, useState, useCallback, useRef } from 'react';
import { MapContainer, TileLayer, Marker, Popup, useMap } from 'react-leaflet';
import L from 'leaflet';
import { fetchFlotaStatus, type Bus, fetchAlertasActivas, type Alerta, sendChatMessage } from '../lib/api';
import { config } from '../config';
import StatusBadge from '../components/StatusBadge';
import { AlertTriangle, Fuel, Thermometer, Gauge, MessageSquare, RefreshCw, Send, X, Bot, Loader2, GripVertical, ChevronLeft, ChevronRight } from 'lucide-react';
import MarkdownContent from '../components/MarkdownContent';
import 'leaflet/dist/leaflet.css';

// Bus marker icons by status — cached to avoid re-creating DOM elements
const iconCache = new Map<string, L.DivIcon>();
function busIcon(estado: string): L.DivIcon {
  if (iconCache.has(estado)) return iconCache.get(estado)!;
  const colors: Record<string, string> = {
    EFICIENTE: '#10b981',
    ALERTA_MODERADA: '#f59e0b',
    ALERTA_SIGNIFICATIVA: '#ef4444',
    SIN_DATOS: '#6b7280',
  };
  const color = colors[estado] || colors.SIN_DATOS;
  const icon = L.divIcon({
    className: '',
    iconSize: [36, 36],
    iconAnchor: [18, 18],
    popupAnchor: [0, -20],
    html: `<div style="
      width:36px;height:36px;border-radius:50%;
      background:${color};border:3px solid white;
      box-shadow:0 2px 8px rgba(0,0,0,0.2);
      display:flex;align-items:center;justify-content:center;
      font-size:11px;font-weight:700;color:white;
    ">🚌</div>`,
  });
  iconCache.set(estado, icon);
  return icon;
}

// Smooth marker animation
function AnimatedMarker({ bus, onClick }: { bus: Bus; onClick: () => void }) {
  const markerRef = useRef<L.Marker>(null);
  const prevPos = useRef<[number, number] | null>(null);
  const animRef = useRef<number>(0);

  useEffect(() => {
    if (!bus.latitud || !bus.longitud || bus.latitud === 0) return;
    const newPos: [number, number] = [bus.latitud, bus.longitud];

    if (markerRef.current && prevPos.current) {
      const marker = markerRef.current;
      const start = prevPos.current;
      const end = newPos;
      const duration = 2000;
      const startTime = performance.now();

      if (animRef.current) cancelAnimationFrame(animRef.current);

      function animate(currentTime: number) {
        const elapsed = currentTime - startTime;
        const progress = Math.min(elapsed / duration, 1);
        const eased = progress < 0.5
          ? 2 * progress * progress
          : 1 - Math.pow(-2 * progress + 2, 2) / 2;
        const lat = start[0] + (end[0] - start[0]) * eased;
        const lng = start[1] + (end[1] - start[1]) * eased;
        marker.setLatLng([lat, lng]);
        if (progress < 1) animRef.current = requestAnimationFrame(animate);
      }
      animRef.current = requestAnimationFrame(animate);
    }
    prevPos.current = newPos;

    return () => { if (animRef.current) cancelAnimationFrame(animRef.current); };
  }, [bus.latitud, bus.longitud]);

  if (!bus.latitud || !bus.longitud || bus.latitud === 0) return null;

  return (
    <Marker
      ref={markerRef}
      position={[bus.latitud, bus.longitud]}
      icon={busIcon(bus.estado_consumo)}
      eventHandlers={{ click: onClick }}
    >
      <Popup maxWidth={340} className="bus-popup">
        <div className="min-w-[280px] -mx-4 -my-3">
          {/* Header con gradiente según estado */}
          <div className={`px-4 py-3 rounded-t-xl ${
            bus.estado_consumo === 'ALERTA_SIGNIFICATIVA' ? 'bg-gradient-to-r from-red-600 to-red-500' :
            bus.estado_consumo === 'ALERTA_MODERADA' ? 'bg-gradient-to-r from-amber-500 to-orange-500' :
            'bg-gradient-to-r from-emerald-600 to-teal-500'
          }`}>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="text-2xl">🚌</span>
                <div>
                  <h3 className="text-white font-bold text-base leading-tight">Bus {bus.autobus}</h3>
                  <p className="text-white/80 text-[10px] font-medium mt-0.5">
                    {bus.estado_consumo === 'EFICIENTE' ? 'Operación normal' :
                     bus.estado_consumo === 'ALERTA_MODERADA' ? 'Alerta moderada' : 'Alerta significativa'}
                  </p>
                </div>
              </div>
              {bus.nivel_combustible_pct != null && (
                <div className="text-right">
                  <p className="text-white/70 text-[9px] uppercase tracking-wide">Tanque</p>
                  <p className="text-white font-bold text-sm">{bus.nivel_combustible_pct.toFixed(0)}%</p>
                </div>
              )}
            </div>
          </div>

          {/* Ruta y operador */}
          <div className="px-4 py-2 border-b border-slate-100 bg-slate-50/50">
            <p className="text-slate-700 text-xs font-semibold truncate">{bus.viaje_ruta}</p>
            <p className="text-slate-400 text-[10px] mt-0.5">{bus.operador_desc || 'Operador no disponible'}</p>
          </div>

          {/* Métricas principales */}
          <div className="px-4 py-3">
            <div className="grid grid-cols-4 gap-1.5">
              <div className="text-center">
                <div className="w-8 h-8 mx-auto bg-blue-50 rounded-lg flex items-center justify-center mb-1">
                  <Gauge className="w-4 h-4 text-blue-600" />
                </div>
                <p className="text-slate-800 font-bold text-sm leading-none">{bus.velocidad_kmh?.toFixed(0) ?? '—'}</p>
                <p className="text-slate-400 text-[9px] mt-0.5">km/h</p>
              </div>
              <div className="text-center">
                <div className="w-8 h-8 mx-auto bg-purple-50 rounded-lg flex items-center justify-center mb-1">
                  <span className="text-purple-600 text-[10px] font-bold">RPM</span>
                </div>
                <p className="text-slate-800 font-bold text-sm leading-none">{bus.rpm?.toFixed(0) ?? '—'}</p>
                <p className="text-slate-400 text-[9px] mt-0.5">rev/min</p>
              </div>
              <div className="text-center">
                <div className="w-8 h-8 mx-auto bg-orange-50 rounded-lg flex items-center justify-center mb-1">
                  <Fuel className="w-4 h-4 text-orange-600" />
                </div>
                <p className="text-slate-800 font-bold text-sm leading-none">{bus.tasa_combustible_lh?.toFixed(1) ?? '—'}</p>
                <p className="text-slate-400 text-[9px] mt-0.5">L/h</p>
              </div>
              <div className="text-center">
                <div className="w-8 h-8 mx-auto bg-red-50 rounded-lg flex items-center justify-center mb-1">
                  <Thermometer className="w-4 h-4 text-red-500" />
                </div>
                <p className="text-slate-800 font-bold text-sm leading-none">{bus.temperatura_motor_c?.toFixed(0) ?? '—'}</p>
                <p className="text-slate-400 text-[9px] mt-0.5">°C</p>
              </div>
            </div>
          </div>

          {/* Alertas */}
          {bus.alertas_spn.length > 0 && (
            <div className="px-4 pb-2">
              <div className="bg-red-50 border border-red-100 rounded-lg p-2.5">
                <div className="flex items-center gap-1.5 mb-1.5">
                  <AlertTriangle className="w-3.5 h-3.5 text-red-500" />
                  <span className="text-red-700 text-[11px] font-semibold">{bus.alertas_spn.length} alerta{bus.alertas_spn.length > 1 ? 's' : ''} activa{bus.alertas_spn.length > 1 ? 's' : ''}</span>
                </div>
                {bus.alertas_spn.slice(0, 2).map((a, i) => (
                  <p key={i} className="text-red-600/80 text-[10px] leading-tight pl-5">{a.mensaje}</p>
                ))}
              </div>
            </div>
          )}

          {/* Botón Agente IA */}
          <div className="px-4 pb-3 pt-1">
            <button
              onClick={(e) => { e.stopPropagation(); }}
              className="w-full flex items-center justify-center gap-2 py-2 bg-gradient-to-r from-red-600 to-red-500 hover:from-red-700 hover:to-red-600 text-white text-xs font-semibold rounded-lg transition-all shadow-sm shadow-red-600/20 active:scale-[0.98]"
            >
              <MessageSquare className="w-3.5 h-3.5" />
              Preguntar al Agente IA
            </button>
          </div>
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

  useEffect(() => {
    const prompt = context
      ? `Analiza el bus ${busId}. Contexto: ${context}`
      : `Analiza el estado completo del bus ${busId}: consumo de combustible y estado mecánico`;
    handleSend(prompt);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages]);

  const handleSend = async (text?: string) => {
    const prompt = text || input.trim();
    if (!prompt || sending) return;
    setInput('');
    setSending(true);
    setMessages(prev => [...prev, { role: 'user', text: prompt }, { role: 'assistant', text: '', loading: true }]);
    try {
      const resp = await sendChatMessage(prompt, 'ambos');
      setMessages(prev => { const u = [...prev]; u[u.length - 1] = { role: 'assistant', text: resp.respuesta }; return u; });
    } catch (err: any) {
      setMessages(prev => { const u = [...prev]; u[u.length - 1] = { role: 'assistant', text: `Error: ${err.message}` }; return u; });
    } finally { setSending(false); }
  };

  return (
    <div className="flex flex-col h-full">
      <div className="p-3 border-b border-slate-200 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-2">
          <Bot className="w-4 h-4 text-red-500" />
          <span className="text-slate-800 font-semibold text-sm">Agente IA — Bus {busId}</span>
        </div>
        <button onClick={onClose} className="text-slate-400 hover:text-slate-700 p-1"><X className="w-4 h-4" /></button>
      </div>
      <div className="flex-1 overflow-y-auto p-3 space-y-3">
        {messages.map((m, i) => (
          <div key={i} className={m.role === 'user' ? 'text-right' : ''}>
            {m.role === 'user' ? (
              <span className="inline-block bg-red-600 text-white text-xs px-3 py-2 rounded-xl max-w-[90%] text-left">{m.text}</span>
            ) : m.loading ? (
              <div className="flex items-center gap-2 text-slate-500 text-xs"><Loader2 className="w-3 h-3 animate-spin" /> Analizando...</div>
            ) : (
              <div className="bg-slate-100 rounded-xl px-3 py-2 text-xs text-slate-700">
                <MarkdownContent compact>{m.text}</MarkdownContent>
              </div>
            )}
          </div>
        ))}
        <div ref={endRef} />
      </div>
      <form onSubmit={e => { e.preventDefault(); handleSend(); }} className="p-2 border-t border-slate-200 flex gap-1 shrink-0">
        <input value={input} onChange={e => setInput(e.target.value)} placeholder="Pregunta más..." disabled={sending}
          className="flex-1 px-3 py-2 bg-slate-100 border border-slate-200 rounded-lg text-slate-800 text-xs placeholder-slate-400 focus:outline-none focus:ring-1 focus:ring-red-500 disabled:opacity-50" />
        <button type="submit" disabled={sending || !input.trim()} className="px-3 py-2 bg-red-600 hover:bg-red-700 disabled:bg-slate-200 text-white rounded-lg">
          <Send className="w-3 h-3" />
        </button>
      </form>
    </div>
  );
}

// Resizable panel hook
function useResizablePanel(initialWidth: number, minWidth: number, maxWidth: number) {
  const [width, setWidth] = useState(initialWidth);
  const dragging = useRef(false);
  const startX = useRef(0);
  const startW = useRef(0);

  const onMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    dragging.current = true;
    startX.current = e.clientX;
    startW.current = width;

    const onMouseMove = (ev: MouseEvent) => {
      if (!dragging.current) return;
      const delta = startX.current - ev.clientX; // dragging left = wider
      const newW = Math.min(maxWidth, Math.max(minWidth, startW.current + delta));
      setWidth(newW);
    };
    const onMouseUp = () => {
      dragging.current = false;
      document.removeEventListener('mousemove', onMouseMove);
      document.removeEventListener('mouseup', onMouseUp);
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    };
    document.addEventListener('mousemove', onMouseMove);
    document.addEventListener('mouseup', onMouseUp);
    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';
  }, [width, minWidth, maxWidth]);

  return { width, onMouseDown };
}

export default function MapPage() {
  const [buses, setBuses] = useState<Bus[]>([]);
  const [alertas, setAlertas] = useState<Alerta[]>([]);
  const [selectedBus, setSelectedBus] = useState<string | null>(null);
  const [chatBus, setChatBus] = useState<{ id: string; context?: string } | null>(null);
  const [panelOpen, setPanelOpen] = useState(false);
  const [desktopPanelOpen, setDesktopPanelOpen] = useState(true);
  const [loading, setLoading] = useState(true);
  const busCache = useRef<Map<string, Bus>>(new Map());
  const { width: panelWidth, onMouseDown: onResizeStart } = useResizablePanel(320, 240, 600);

  const loadData = useCallback(async () => {
    try {
      const [flota, alertasData] = await Promise.all([
        fetchFlotaStatus(),
        fetchAlertasActivas(),
      ]);
      // Smart merge: never overwrite good values with 0 or null
      for (const bus of flota.buses) {
        const cached = busCache.current.get(bus.autobus);
        if (cached) {
          // Preserve estado_consumo if new data says SIN_DATOS but we had a real state
          if (bus.estado_consumo === 'SIN_DATOS' && cached.estado_consumo !== 'SIN_DATOS') {
            bus.estado_consumo = cached.estado_consumo;
          }
          // For numeric telemetry fields: keep cached value when new value is 0/null/undefined
          const numericFields = [
            'velocidad_kmh', 'rpm', 'tasa_combustible_lh', 'temperatura_motor_c',
            'nivel_combustible_pct', 'presion_aceite_kpa',
          ] as const;
          for (const field of numericFields) {
            if (!bus[field] && cached[field]) {
              (bus as any)[field] = cached[field];
            }
          }
        }
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
    setPanelOpen(true);
    setDesktopPanelOpen(true);
  };

  const panelContent = chatBus ? (
    <InlineChat
      busId={chatBus.id}
      context={chatBus.context}
      onClose={() => { setChatBus(null); setPanelOpen(false); }}
    />
  ) : (
    <>
      <div className="p-4 border-b border-slate-200">
        <h2 className="text-slate-800 font-bold flex items-center gap-2">
          <AlertTriangle className="w-5 h-5 text-amber-500" />
          Vehículos con Alertas
        </h2>
        <p className="text-slate-500 text-xs mt-1">{busesWithAlerts.length} vehículo(s) requieren atención</p>
      </div>
      <div className="flex-1 overflow-y-auto p-2 space-y-2">
        {busesWithAlerts.length === 0 && (
          <div className="text-center text-slate-400 py-8"><p className="text-sm">Todos los vehículos operan con normalidad</p></div>
        )}
        {busesWithAlerts.map(bus => (
          <div key={bus.autobus}
            className={`p-3 rounded-xl border transition-colors cursor-pointer ${selectedBus === bus.autobus ? 'bg-red-50 border-red-200' : 'bg-white border-slate-200 hover:border-slate-300 shadow-sm'}`}
            onClick={() => setSelectedBus(bus.autobus)}>
            <div className="flex items-center justify-between mb-2">
              <span className="text-slate-800 font-bold">Bus {bus.autobus}</span>
              <StatusBadge status={bus.estado_consumo} />
            </div>
            <p className="text-slate-500 text-xs truncate">{bus.viaje_ruta}</p>
            <p className="text-slate-400 text-xs">{bus.operador_desc || '—'}</p>
            {bus.spns_fuera_de_rango > 0 && (
              <p className="text-amber-600 text-xs mt-1">⚠ {bus.spns_fuera_de_rango} señal(es) fuera de rango</p>
            )}
            <button onClick={e => { e.stopPropagation(); openChat(bus.autobus, bus.alertas_spn.map(a => a.mensaje).join('; ') || undefined); }}
              className="mt-2 w-full flex items-center justify-center gap-1 py-1.5 bg-slate-100 hover:bg-red-600 text-slate-600 hover:text-white text-xs font-medium rounded-lg transition-colors">
              <MessageSquare className="w-3 h-3" /> Consultar Agente
            </button>
          </div>
        ))}
        {alertas.length > 0 && (
          <>
            <div className="pt-3 pb-1 px-1"><h3 className="text-slate-500 text-xs font-semibold uppercase tracking-wider">Alertas de Mantenimiento</h3></div>
            {alertas.map(alerta => (
              <div key={alerta.alerta_id} className="p-3 rounded-xl bg-red-50 border border-red-200">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-slate-800 font-bold text-sm">Bus {alerta.autobus}</span>
                  <StatusBadge status={alerta.nivel_riesgo} />
                </div>
                <p className="text-slate-600 text-xs">{alerta.diagnostico}</p>
                <div className="flex items-center gap-2 mt-2">
                  <span className="text-slate-400 text-xs">{alerta.numero_referencia}</span>
                  <span className="text-slate-300">·</span>
                  <span className="text-amber-600 text-xs">{alerta.urgencia.replace(/_/g, ' ')}</span>
                </div>
                <button onClick={() => openChat(alerta.autobus, `Tiene alerta ${alerta.nivel_riesgo}: ${alerta.diagnostico}`)}
                  className="mt-2 w-full flex items-center justify-center gap-1 py-1.5 bg-red-100 hover:bg-red-600 text-red-600 hover:text-white text-xs font-medium rounded-lg transition-colors">
                  <MessageSquare className="w-3 h-3" /> Preguntar sobre esta alerta
                </button>
              </div>
            ))}
          </>
        )}
      </div>
    </>
  );

  const eficientes = buses.filter(b => b.estado_consumo === 'EFICIENTE').length;
  const moderadas = buses.filter(b => b.estado_consumo === 'ALERTA_MODERADA').length;
  const significativas = buses.filter(b => b.estado_consumo === 'ALERTA_SIGNIFICATIVA').length;

  return (
    <div className="flex flex-col md:flex-row h-full relative">
      {/* Map */}
      <div className="flex-1 relative">
        <MapContainer center={config.map.center} zoom={config.map.zoom} className="h-full w-full" zoomControl={false}>
          <TileLayer url={config.map.tileUrl} attribution={config.map.tileAttribution} />
          <FitBounds buses={buses} />
          {buses.map(bus => (
            <AnimatedMarker key={bus.autobus} bus={bus} onClick={() => setSelectedBus(bus.autobus)} />
          ))}
        </MapContainer>

        {/* Telematics logo overlay */}
        <div className="absolute top-2 right-2 md:top-4 md:right-4 z-[1000] bg-slate-900/85 backdrop-blur rounded-xl px-3 py-2 border border-slate-700 shadow-lg">
          <img src="/IMG_Logo Blanco_V1_04-08-26_Telematics.svg" alt="Telematics" className="h-6 md:h-8 w-auto" />
        </div>

        {/* Stats overlay */}
        <div className="absolute top-2 left-2 md:top-4 md:left-4 z-[1000] bg-white/95 backdrop-blur rounded-xl p-2 md:p-4 border border-slate-200 shadow-lg">
          <h2 className="text-slate-800 font-bold text-xs md:text-sm mb-1 md:mb-2 flex items-center gap-1 md:gap-2">
            <RefreshCw className={`w-3 h-3 md:w-4 md:h-4 text-slate-500 ${loading ? 'animate-spin' : ''}`} />
            <span className="hidden sm:inline">Flota en Tiempo Real</span>
            <span className="sm:hidden">Flota</span>
          </h2>
          <div className="flex gap-2 md:gap-3 text-[10px] md:text-xs">
            <div className="text-center">
              <p className="text-lg md:text-2xl font-bold text-slate-800">{buses.length}</p>
              <p className="text-slate-500">Total</p>
            </div>
            <div className="text-center">
              <p className="text-lg md:text-2xl font-bold text-emerald-600">{eficientes}</p>
              <p className="text-slate-500">OK</p>
            </div>
            {moderadas > 0 && (
              <div className="text-center">
                <p className="text-lg md:text-2xl font-bold text-amber-500">{moderadas}</p>
                <p className="text-slate-500">Mod</p>
              </div>
            )}
            {significativas > 0 && (
              <div className="text-center">
                <p className="text-lg md:text-2xl font-bold text-red-500">{significativas}</p>
                <p className="text-slate-500">Alerta</p>
              </div>
            )}
          </div>
        </div>

        {/* Mobile FAB */}
        {!panelOpen && (
          <button onClick={() => setPanelOpen(true)}
            className="md:hidden absolute bottom-4 right-4 z-[1000] w-14 h-14 bg-red-600 rounded-full flex items-center justify-center shadow-lg shadow-red-600/30 active:scale-95 transition-transform">
            <AlertTriangle className="w-6 h-6 text-white" />
            {busesWithAlerts.length > 0 && (
              <span className="absolute -top-1 -right-1 w-5 h-5 bg-amber-500 rounded-full text-[10px] font-bold text-white flex items-center justify-center">{busesWithAlerts.length}</span>
            )}
          </button>
        )}

        {/* Desktop: toggle panel button */}
        {!desktopPanelOpen && (
          <button onClick={() => setDesktopPanelOpen(true)}
            className="hidden md:flex absolute top-1/2 right-0 -translate-y-1/2 z-[1000] w-6 h-16 bg-white border border-slate-200 border-r-0 rounded-l-lg items-center justify-center text-slate-400 hover:text-slate-700 hover:bg-slate-50 transition-colors shadow-sm">
            <ChevronLeft className="w-4 h-4" />
          </button>
        )}
      </div>

      {/* Desktop: resizable side panel */}
      {desktopPanelOpen && (
        <div className="hidden md:flex shrink-0" style={{ width: panelWidth }}>
          {/* Resize handle */}
          <div onMouseDown={onResizeStart}
            className="w-1.5 bg-slate-100 hover:bg-red-200 cursor-col-resize flex items-center justify-center group transition-colors border-x border-slate-200">
            <GripVertical className="w-3 h-3 text-slate-400 group-hover:text-red-500 transition-colors" />
          </div>
          {/* Panel content */}
          <div className="flex-1 bg-slate-50 flex flex-col overflow-hidden border-l border-slate-200">
            {/* Collapse button */}
            <button onClick={() => setDesktopPanelOpen(false)}
              className="absolute top-2 right-2 z-10 p-1 text-slate-400 hover:text-slate-700">
              <ChevronRight className="w-4 h-4" />
            </button>
            {panelContent}
          </div>
        </div>
      )}

      {/* Mobile: bottom sheet */}
      {panelOpen && (
        <div className="md:hidden absolute inset-x-0 bottom-0 z-[1001] flex flex-col bg-white border-t border-slate-200 rounded-t-2xl max-h-[70vh] shadow-2xl animate-slide-up">
          <div className="flex items-center justify-center pt-2 pb-1 shrink-0">
            <div className="w-10 h-1 bg-slate-300 rounded-full" />
          </div>
          <button onClick={() => { setPanelOpen(false); setChatBus(null); }}
            className="absolute top-2 right-3 text-slate-400 hover:text-slate-700 z-10">
            <X className="w-5 h-5" />
          </button>
          <div className="flex-1 overflow-y-auto flex flex-col">{panelContent}</div>
        </div>
      )}
    </div>
  );
}
