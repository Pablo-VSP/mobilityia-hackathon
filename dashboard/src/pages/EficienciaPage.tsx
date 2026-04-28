import { useEffect, useState } from 'react';
import { fetchResumenConsumo, type RutaResumen } from '../lib/api';
import { Fuel, TrendingDown, TrendingUp } from 'lucide-react';

const eficienciaColors: Record<string, string> = {
  EFICIENTE: 'text-emerald-400',
  MODERADA: 'text-amber-400',
  REQUIERE_ATENCION: 'text-red-400',
};

export default function EficienciaPage() {
  const [rutas, setRutas] = useState<RutaResumen[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchResumenConsumo()
      .then(data => setRutas(data.rutas))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="h-full overflow-y-auto p-6">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-2xl font-bold text-white mb-1 flex items-center gap-3">
          <Fuel className="w-7 h-7 text-amber-400" />
          Eficiencia por Ruta
        </h1>
        <p className="text-slate-400 mb-6">{rutas.length} ruta(s) activas</p>

        {loading && <p className="text-slate-500">Cargando datos de eficiencia...</p>}

        <div className="space-y-4">
          {rutas.map(r => (
            <div key={r.viaje_ruta} className="bg-slate-800 rounded-xl p-5 border border-slate-700">
              <div className="flex items-start justify-between mb-3">
                <div>
                  <h3 className="text-white font-bold">{r.viaje_ruta}</h3>
                  <p className="text-slate-400 text-sm">{r.total_buses} bus(es) en ruta</p>
                </div>
                <span className={`font-semibold ${eficienciaColors[r.eficiencia_ruta] || 'text-slate-400'}`}>
                  {r.eficiencia_ruta === 'REQUIERE_ATENCION' ? (
                    <span className="flex items-center gap-1"><TrendingDown className="w-4 h-4" /> Requiere Atención</span>
                  ) : r.eficiencia_ruta === 'EFICIENTE' ? (
                    <span className="flex items-center gap-1"><TrendingUp className="w-4 h-4" /> Eficiente</span>
                  ) : (
                    'Moderada'
                  )}
                </span>
              </div>

              <div className="grid grid-cols-3 gap-3">
                <div className="bg-slate-700/50 rounded-lg p-3 text-center">
                  <p className="text-2xl font-bold text-white">
                    {r.rendimiento_promedio_kml?.toFixed(1) ?? '—'}
                  </p>
                  <p className="text-slate-400 text-xs">km/L promedio</p>
                </div>
                <div className="bg-slate-700/50 rounded-lg p-3 text-center">
                  <p className="text-2xl font-bold text-emerald-400">
                    {r.resumen_estados.EFICIENTE || 0}
                  </p>
                  <p className="text-slate-400 text-xs">Eficientes</p>
                </div>
                <div className="bg-slate-700/50 rounded-lg p-3 text-center">
                  <p className="text-2xl font-bold text-red-400">
                    {(r.resumen_estados.ALERTA_SIGNIFICATIVA || 0) + (r.resumen_estados.ALERTA_MODERADA || 0)}
                  </p>
                  <p className="text-slate-400 text-xs">Con alerta</p>
                </div>
              </div>
            </div>
          ))}

          {!loading && rutas.length === 0 && (
            <div className="text-center py-12 text-slate-500">
              <Fuel className="w-12 h-12 mx-auto mb-3 opacity-30" />
              <p>No hay datos de eficiencia disponibles</p>
              <p className="text-xs mt-1">El simulador debe estar activo para generar datos</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
