import { useEffect, useState } from 'react';
import { fetchResumenConsumo, type RutaResumen } from '../lib/api';
import { Fuel, TrendingDown, TrendingUp } from 'lucide-react';

const eficienciaColors: Record<string, string> = {
  EFICIENTE: 'text-emerald-600',
  MODERADA: 'text-amber-600',
  REQUIERE_ATENCION: 'text-red-600',
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
    <div className="h-full overflow-y-auto p-6 bg-slate-50">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-2xl font-bold text-slate-800 mb-1 flex items-center gap-3">
          <Fuel className="w-7 h-7 text-amber-500" />
          Eficiencia por Ruta
        </h1>
        <p className="text-slate-500 mb-6">{rutas.length} ruta(s) activas</p>

        {loading && <p className="text-slate-400">Cargando datos de eficiencia...</p>}

        <div className="space-y-4">
          {rutas.map(r => (
            <div key={r.viaje_ruta} className="bg-white rounded-xl p-5 border border-slate-200 shadow-sm">
              <div className="flex items-start justify-between mb-3">
                <div>
                  <h3 className="text-slate-800 font-bold">{r.viaje_ruta}</h3>
                  <p className="text-slate-500 text-sm">{r.total_buses} bus(es) en ruta</p>
                </div>
                <span className={`font-semibold ${eficienciaColors[r.eficiencia_ruta] || 'text-slate-500'}`}>
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
                <div className="bg-slate-50 rounded-lg p-3 text-center">
                  <p className="text-2xl font-bold text-slate-800">
                    {r.rendimiento_promedio_kml?.toFixed(1) ?? '—'}
                  </p>
                  <p className="text-slate-500 text-xs">km/L promedio</p>
                </div>
                <div className="bg-slate-50 rounded-lg p-3 text-center">
                  <p className="text-2xl font-bold text-emerald-600">
                    {r.resumen_estados.EFICIENTE || 0}
                  </p>
                  <p className="text-slate-500 text-xs">Eficientes</p>
                </div>
                <div className="bg-slate-50 rounded-lg p-3 text-center">
                  <p className="text-2xl font-bold text-red-500">
                    {(r.resumen_estados.ALERTA_SIGNIFICATIVA || 0) + (r.resumen_estados.ALERTA_MODERADA || 0)}
                  </p>
                  <p className="text-slate-500 text-xs">Con alerta</p>
                </div>
              </div>
            </div>
          ))}

          {!loading && rutas.length === 0 && (
            <div className="text-center py-12 text-slate-400">
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
