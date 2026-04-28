import { useEffect, useState } from 'react';
import { fetchAlertasActivas, type Alerta } from '../lib/api';
import StatusBadge from '../components/StatusBadge';
import { AlertTriangle, Clock, Wrench } from 'lucide-react';

export default function AlertasPage() {
  const [alertas, setAlertas] = useState<Alerta[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchAlertasActivas()
      .then(data => setAlertas(data.alertas))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="h-full overflow-y-auto p-6">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-2xl font-bold text-white mb-1 flex items-center gap-3">
          <AlertTriangle className="w-7 h-7 text-amber-400" />
          Alertas Activas
        </h1>
        <p className="text-slate-400 mb-6">{alertas.length} alerta(s) requieren atención</p>

        {loading && <p className="text-slate-500">Cargando alertas...</p>}

        <div className="space-y-4">
          {alertas.map(a => (
            <div key={a.alerta_id} className="bg-slate-800 rounded-xl p-5 border border-slate-700">
              <div className="flex items-start justify-between mb-3">
                <div>
                  <h3 className="text-white font-bold text-lg">Bus {a.autobus}</h3>
                  <p className="text-slate-400 text-sm">{a.viaje_ruta}</p>
                </div>
                <div className="flex flex-col items-end gap-1">
                  <StatusBadge status={a.nivel_riesgo} />
                  <span className="text-xs text-slate-500">{a.tipo_alerta}</span>
                </div>
              </div>

              <p className="text-slate-200 mb-3">{a.diagnostico}</p>

              <div className="flex flex-wrap gap-2 mb-3">
                {a.componentes.map((c, i) => (
                  <span key={i} className="inline-flex items-center gap-1 px-2 py-1 bg-slate-700 rounded-lg text-xs text-slate-300">
                    <Wrench className="w-3 h-3" /> {c.replace(/_/g, ' ')}
                  </span>
                ))}
              </div>

              <div className="flex items-center gap-4 text-xs text-slate-500">
                <span className="flex items-center gap-1">
                  <Clock className="w-3 h-3" />
                  {a.urgencia.replace(/_/g, ' ')}
                </span>
                <span>{a.numero_referencia}</span>
                <span>{a.agente_origen}</span>
                <span>{new Date(a.timestamp).toLocaleString('es-MX')}</span>
              </div>
            </div>
          ))}

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
