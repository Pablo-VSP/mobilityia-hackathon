import { useEffect, useState } from 'react';
import { fetchCO2Estimado, type CO2Estimado } from '../lib/api';
import { Leaf, Shield, TreePine, Zap, Truck } from 'lucide-react';

const impactIcons: Record<string, typeof Leaf> = {
  'Optimización de combustible': Zap,
  'Conducción eficiente': Truck,
  'Mantenimiento preventivo': Shield,
  'Disponibilidad de flota': TreePine,
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

  return (
    <div className="h-full overflow-y-auto p-6">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-2xl font-bold text-white mb-1 flex items-center gap-3">
          <Leaf className="w-7 h-7 text-emerald-400" />
          {data.titulo}
        </h1>
        <p className="text-slate-300 mt-3 mb-8 text-lg leading-relaxed">{data.descripcion_general}</p>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-8">
          {data.areas_de_impacto.map((area, i) => {
            const Icon = impactIcons[area.area] || Leaf;
            return (
              <div key={i} className="bg-slate-800 rounded-xl p-5 border border-slate-700">
                <div className="flex items-center gap-3 mb-3">
                  <div className="w-10 h-10 bg-emerald-500/20 rounded-lg flex items-center justify-center">
                    <Icon className="w-5 h-5 text-emerald-400" />
                  </div>
                  <div>
                    <h3 className="text-white font-bold">{area.area}</h3>
                    <span className="text-emerald-400 text-xs font-medium uppercase">{area.nivel_impacto}</span>
                  </div>
                </div>
                <p className="text-slate-300 text-sm leading-relaxed">{area.descripcion}</p>
              </div>
            );
          })}
        </div>

        <div className="bg-emerald-500/10 border border-emerald-500/30 rounded-xl p-5 mb-4">
          <h3 className="text-emerald-400 font-bold mb-2 flex items-center gap-2">
            <Shield className="w-5 h-5" /> Cumplimiento Normativo
          </h3>
          <p className="text-slate-300 text-sm">{data.cumplimiento_normativo}</p>
        </div>

        <p className="text-slate-500 text-xs italic">{data.nota}</p>
      </div>
    </div>
  );
}
