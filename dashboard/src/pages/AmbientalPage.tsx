import { useEffect, useState } from 'react';
import { fetchCO2Estimado, type CO2Estimado } from '../lib/api';
import { Leaf, Shield, TrendingDown, TrendingUp, Minus, Truck, Droplets, Gauge } from 'lucide-react';

const clasificacionConfig: Record<string, { color: string; bg: string; label: string }> = {
  ECO_EFICIENTE: { color: 'text-emerald-400', bg: 'bg-emerald-500/20', label: 'Eco-Eficiente' },
  EFICIENTE: { color: 'text-green-400', bg: 'bg-green-500/20', label: 'Eficiente' },
  ESTANDAR: { color: 'text-amber-400', bg: 'bg-amber-500/20', label: 'Estándar' },
  INEFICIENTE: { color: 'text-orange-400', bg: 'bg-orange-500/20', label: 'Ineficiente' },
  CRITICO: { color: 'text-red-400', bg: 'bg-red-500/20', label: 'Crítico' },
};

export default function AmbientalPage() {
  const [data, setData] = useState<CO2Estimado | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchCO2Estimado()
      .then(setData)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="p-6 text-slate-500">Cargando datos ambientales...</div>;
  if (!data) return <div className="p-6 text-slate-500">No hay datos disponibles</div>;

  // Handle "sin_datos" state
  if (data.estado === 'sin_datos') {
    return (
      <div className="h-full overflow-y-auto p-6">
        <div className="max-w-5xl mx-auto text-center py-16">
          <Leaf className="w-16 h-16 text-slate-600 mx-auto mb-4" />
          <h1 className="text-2xl font-bold text-white mb-2">{data.titulo}</h1>
          <p className="text-slate-400">{data.mensaje}</p>
        </div>
      </div>
    );
  }

  const flota = data.flota;
  const buses = data.buses || [];

  return (
    <div className="h-full overflow-y-auto p-6">
      <div className="max-w-5xl mx-auto">
        {/* Header */}
        <h1 className="text-2xl font-bold text-white mb-1 flex items-center gap-3">
          <Leaf className="w-7 h-7 text-emerald-400" />
          {data.titulo}
        </h1>
        <p className="text-slate-400 text-sm mb-6">
          Factor: {data.factor_co2} · Referencia: {data.rendimiento_referencia_kml} km/L · Ruta: {data.distancia_ruta_km} km
        </p>

        {/* Fleet summary cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
          <div className="bg-slate-800 rounded-xl p-4 border border-slate-700">
            <div className="flex items-center gap-2 text-slate-400 text-xs mb-2">
              <Truck className="w-4 h-4" /> Buses Activos
            </div>
            <p className="text-3xl font-bold text-white">{flota.buses_activos}</p>
          </div>
          <div className="bg-slate-800 rounded-xl p-4 border border-slate-700">
            <div className="flex items-center gap-2 text-slate-400 text-xs mb-2">
              <Gauge className="w-4 h-4" /> Rendimiento Flota
            </div>
            <p className="text-3xl font-bold text-white">{flota.rendimiento_promedio_kml} <span className="text-base text-slate-400">km/L</span></p>
          </div>
          <div className="bg-slate-800 rounded-xl p-4 border border-slate-700">
            <div className="flex items-center gap-2 text-slate-400 text-xs mb-2">
              <Droplets className="w-4 h-4" /> CO₂ Total Estimado
            </div>
            <p className="text-3xl font-bold text-white">{flota.co2_total_estimado_kg} <span className="text-base text-slate-400">kg</span></p>
            <p className="text-xs text-slate-500 mt-1">Ref: {flota.co2_total_referencia_kg} kg</p>
          </div>
          <div className="bg-slate-800 rounded-xl p-4 border border-slate-700">
            <div className="flex items-center gap-2 text-slate-400 text-xs mb-2">
              <Leaf className="w-4 h-4" /> Ahorro Potencial CO₂
            </div>
            <p className={`text-3xl font-bold ${flota.ahorro_potencial_co2_kg > 0 ? 'text-amber-400' : 'text-emerald-400'}`}>
              {flota.ahorro_potencial_co2_kg} <span className="text-base text-slate-400">kg</span>
            </p>
          </div>
        </div>

        {/* Fleet description */}
        <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700 mb-6">
          <p className="text-slate-300 text-sm leading-relaxed">{flota.descripcion}</p>
        </div>

        {/* Distribution bar */}
        {Object.keys(flota.distribucion_ambiental).length > 0 && (
          <div className="mb-6">
            <h3 className="text-white font-semibold text-sm mb-3">Distribución Ambiental de la Flota</h3>
            <div className="flex rounded-lg overflow-hidden h-8">
              {Object.entries(flota.distribucion_ambiental).map(([cls, count]) => {
                const cfg = clasificacionConfig[cls] || clasificacionConfig.ESTANDAR;
                const pct = flota.buses_activos > 0 ? (count / flota.buses_activos) * 100 : 0;
                if (pct === 0) return null;
                return (
                  <div
                    key={cls}
                    className={`${cfg.bg} flex items-center justify-center text-xs font-medium ${cfg.color}`}
                    style={{ width: `${pct}%` }}
                    title={`${cfg.label}: ${count} bus(es)`}
                  >
                    {count > 0 && `${count}`}
                  </div>
                );
              })}
            </div>
            <div className="flex flex-wrap gap-3 mt-2">
              {Object.entries(flota.distribucion_ambiental).map(([cls, count]) => {
                const cfg = clasificacionConfig[cls] || clasificacionConfig.ESTANDAR;
                return (
                  <span key={cls} className={`text-xs ${cfg.color} flex items-center gap-1`}>
                    <span className={`w-2 h-2 rounded-full ${cfg.color.replace('text-', 'bg-')}`} />
                    {cfg.label}: {count}
                  </span>
                );
              })}
            </div>
          </div>
        )}

        {/* Per-bus indicators */}
        <h3 className="text-white font-semibold text-sm mb-3">Indicadores por Autobús</h3>
        <div className="space-y-3 mb-6">
          {buses.map(bus => {
            const cfg = clasificacionConfig[bus.clasificacion_ambiental] || clasificacionConfig.ESTANDAR;
            const diff = bus.co2_estimado_por_viaje_kg - bus.co2_referencia_por_viaje_kg;
            return (
              <div key={bus.autobus} className="bg-slate-800 rounded-xl p-4 border border-slate-700">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-3">
                    <span className="text-white font-bold">Bus {bus.autobus}</span>
                    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${cfg.bg} ${cfg.color}`}>
                      {cfg.label}
                    </span>
                  </div>
                  <div className="flex items-center gap-1 text-sm">
                    {diff > 5 ? (
                      <TrendingUp className="w-4 h-4 text-red-400" />
                    ) : diff < -5 ? (
                      <TrendingDown className="w-4 h-4 text-emerald-400" />
                    ) : (
                      <Minus className="w-4 h-4 text-slate-400" />
                    )}
                    <span className={diff > 5 ? 'text-red-400' : diff < -5 ? 'text-emerald-400' : 'text-slate-400'}>
                      {diff > 0 ? '+' : ''}{diff.toFixed(1)} kg CO₂
                    </span>
                  </div>
                </div>
                <div className="grid grid-cols-4 gap-2 mb-2">
                  <div className="text-center">
                    <p className="text-white font-semibold text-sm">{bus.rendimiento_promedio_kml}</p>
                    <p className="text-slate-500 text-xs">km/L</p>
                  </div>
                  <div className="text-center">
                    <p className="text-white font-semibold text-sm">{bus.co2_estimado_por_viaje_kg}</p>
                    <p className="text-slate-500 text-xs">kg CO₂/viaje</p>
                  </div>
                  <div className="text-center">
                    <p className="text-white font-semibold text-sm">{bus.co2_por_km_kg}</p>
                    <p className="text-slate-500 text-xs">kg CO₂/km</p>
                  </div>
                  <div className="text-center">
                    <p className="text-slate-400 font-semibold text-sm">{bus.ruta || '—'}</p>
                    <p className="text-slate-500 text-xs">Ruta</p>
                  </div>
                </div>
                <p className="text-slate-400 text-xs">{bus.tendencia}</p>
              </div>
            );
          })}
        </div>

        {/* Compliance */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <div className="bg-emerald-500/10 border border-emerald-500/30 rounded-xl p-4">
            <h3 className="text-emerald-400 font-bold text-sm mb-2 flex items-center gap-2">
              <Shield className="w-4 h-4" /> NOM-044
            </h3>
            <p className="text-slate-300 text-xs leading-relaxed">{data.cumplimiento_normativo.nom_044}</p>
          </div>
          <div className="bg-emerald-500/10 border border-emerald-500/30 rounded-xl p-4">
            <h3 className="text-emerald-400 font-bold text-sm mb-2 flex items-center gap-2">
              <Leaf className="w-4 h-4" /> Acuerdo de París
            </h3>
            <p className="text-slate-300 text-xs leading-relaxed">{data.cumplimiento_normativo.acuerdo_paris}</p>
          </div>
        </div>
      </div>
    </div>
  );
}
