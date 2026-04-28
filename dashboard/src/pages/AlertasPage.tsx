import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { fetchAlertasActivas, type Alerta } from '../lib/api';
import StatusBadge from '../components/StatusBadge';
import { AlertTriangle, Clock, Wrench, ChevronDown, ChevronUp, MessageSquare } from 'lucide-react';

interface BusAlertGroup {
  autobus: string;
  viaje_ruta: string;
  operador_desc: string;
  maxNivel: string;
  alertas: Alerta[];
}

const nivelOrder: Record<string, number> = {
  CRITICO: 0,
  ELEVADO: 1,
  MODERADO: 2,
  BAJO: 3,
};

function groupByBus(alertas: Alerta[]): BusAlertGroup[] {
  const map = new Map<string, BusAlertGroup>();
  for (const a of alertas) {
    const existing = map.get(a.autobus);
    if (existing) {
      existing.alertas.push(a);
      // Keep the highest severity
      if ((nivelOrder[a.nivel_riesgo] ?? 9) < (nivelOrder[existing.maxNivel] ?? 9)) {
        existing.maxNivel = a.nivel_riesgo;
      }
    } else {
      map.set(a.autobus, {
        autobus: a.autobus,
        viaje_ruta: a.viaje_ruta,
        operador_desc: a.operador_desc,
        maxNivel: a.nivel_riesgo,
        alertas: [a],
      });
    }
  }
  // Sort groups by max severity
  return [...map.values()].sort(
    (a, b) => (nivelOrder[a.maxNivel] ?? 9) - (nivelOrder[b.maxNivel] ?? 9)
  );
}

export default function AlertasPage() {
  const [alertas, setAlertas] = useState<Alerta[]>([]);
  const [loading, setLoading] = useState(true);
  const [expandedBus, setExpandedBus] = useState<string | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    fetchAlertasActivas()
      .then(data => setAlertas(data.alertas))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  const groups = groupByBus(alertas);

  const openChat = (autobus: string, diagnostico: string) => {
    const context = encodeURIComponent(`Tiene una alerta activa: ${diagnostico}`);
    navigate(`/chat?bus=${autobus}&context=${context}`);
  };

  return (
    <div className="h-full overflow-y-auto p-6">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-2xl font-bold text-white mb-1 flex items-center gap-3">
          <AlertTriangle className="w-7 h-7 text-amber-400" />
          Alertas Activas
        </h1>
        <p className="text-slate-400 mb-6">
          {alertas.length} alerta(s) en {groups.length} autobús(es)
        </p>

        {loading && <p className="text-slate-500">Cargando alertas...</p>}

        <div className="space-y-4">
          {groups.map(group => {
            const isExpanded = expandedBus === group.autobus;
            const hasMultiple = group.alertas.length > 1;
            // Sort alertas within group: most severe first, then newest
            const sorted = [...group.alertas].sort((a, b) => {
              const levelDiff = (nivelOrder[a.nivel_riesgo] ?? 9) - (nivelOrder[b.nivel_riesgo] ?? 9);
              if (levelDiff !== 0) return levelDiff;
              return b.timestamp.localeCompare(a.timestamp);
            });
            const latest = sorted[0];

            return (
              <div key={group.autobus} className="bg-slate-800 rounded-xl border border-slate-700 overflow-hidden">
                {/* Group header */}
                <div
                  className={`p-5 ${hasMultiple ? 'cursor-pointer hover:bg-slate-750' : ''}`}
                  onClick={() => hasMultiple && setExpandedBus(isExpanded ? null : group.autobus)}
                >
                  <div className="flex items-start justify-between mb-3">
                    <div>
                      <h3 className="text-white font-bold text-lg flex items-center gap-2">
                        Bus {group.autobus}
                        {hasMultiple && (
                          <span className="text-xs bg-slate-700 text-slate-300 px-2 py-0.5 rounded-full">
                            {group.alertas.length} tickets
                          </span>
                        )}
                      </h3>
                      <p className="text-slate-400 text-sm">{group.viaje_ruta}</p>
                    </div>
                    <div className="flex items-center gap-2">
                      <StatusBadge status={group.maxNivel} />
                      {hasMultiple && (
                        isExpanded
                          ? <ChevronUp className="w-4 h-4 text-slate-400" />
                          : <ChevronDown className="w-4 h-4 text-slate-400" />
                      )}
                    </div>
                  </div>

                  {/* Show latest alert always */}
                  <p className="text-slate-200 mb-3">{latest.diagnostico}</p>

                  <div className="flex flex-wrap gap-2 mb-3">
                    {latest.componentes.map((c, i) => (
                      <span key={i} className="inline-flex items-center gap-1 px-2 py-1 bg-slate-700 rounded-lg text-xs text-slate-300">
                        <Wrench className="w-3 h-3" /> {c.replace(/_/g, ' ')}
                      </span>
                    ))}
                  </div>

                  <div className="flex items-center gap-4 text-xs text-slate-500">
                    <span className="flex items-center gap-1">
                      <Clock className="w-3 h-3" />
                      {latest.urgencia.replace(/_/g, ' ')}
                    </span>
                    <span>{latest.numero_referencia}</span>
                    <span>{new Date(latest.timestamp).toLocaleString('es-MX')}</span>
                  </div>
                </div>

                {/* Expanded: show all tickets for this bus */}
                {isExpanded && hasMultiple && (
                  <div className="border-t border-slate-700">
                    <div className="px-5 py-2 bg-slate-850">
                      <p className="text-xs text-slate-500 font-medium uppercase tracking-wider">
                        Historial de tickets — Bus {group.autobus}
                      </p>
                    </div>
                    {sorted.map((a, idx) => (
                      <div
                        key={a.alerta_id}
                        className={`px-5 py-3 ${idx > 0 ? 'border-t border-slate-700/50' : ''} ${idx === 0 ? 'bg-slate-750/30' : ''}`}
                      >
                        <div className="flex items-center justify-between mb-1">
                          <div className="flex items-center gap-2">
                            <StatusBadge status={a.nivel_riesgo} />
                            <span className="text-xs text-slate-500">{a.numero_referencia}</span>
                          </div>
                          <span className="text-xs text-slate-500">
                            {new Date(a.timestamp).toLocaleString('es-MX')}
                          </span>
                        </div>
                        <p className="text-slate-300 text-sm mb-1">{a.diagnostico}</p>
                        <div className="flex items-center gap-2 text-xs text-slate-500">
                          <Clock className="w-3 h-3" />
                          <span>{a.urgencia.replace(/_/g, ' ')}</span>
                          {a.componentes.length > 0 && (
                            <span className="text-slate-600">· {a.componentes.join(', ').replace(/_/g, ' ')}</span>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}

                {/* Ask agent button */}
                <div className="px-5 py-3 border-t border-slate-700 bg-slate-800/50">
                  <button
                    onClick={() => openChat(group.autobus, latest.diagnostico)}
                    className="w-full flex items-center justify-center gap-2 py-2 bg-red-600/20 hover:bg-red-600 text-red-400 hover:text-white text-sm font-medium rounded-lg transition-colors"
                  >
                    <MessageSquare className="w-4 h-4" />
                    Preguntar al Agente sobre este bus
                  </button>
                </div>
              </div>
            );
          })}

          {!loading && alertas.length === 0 && (
            <div className="text-center py-12 text-slate-500">
              <AlertTriangle className="w-12 h-12 mx-auto mb-3 opacity-30" />
              <p>No hay alertas activas en este momento</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
