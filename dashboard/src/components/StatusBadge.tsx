const statusConfig: Record<string, { bg: string; text: string; label: string }> = {
  EFICIENTE: { bg: 'bg-emerald-100', text: 'text-emerald-700', label: 'Eficiente' },
  ALERTA_MODERADA: { bg: 'bg-amber-100', text: 'text-amber-700', label: 'Alerta Moderada' },
  ALERTA_SIGNIFICATIVA: { bg: 'bg-red-100', text: 'text-red-700', label: 'Alerta Significativa' },
  SIN_DATOS: { bg: 'bg-slate-100', text: 'text-slate-500', label: 'Sin Datos' },
  BAJO: { bg: 'bg-emerald-100', text: 'text-emerald-700', label: 'Bajo' },
  MODERADO: { bg: 'bg-amber-100', text: 'text-amber-700', label: 'Moderado' },
  ELEVADO: { bg: 'bg-orange-100', text: 'text-orange-700', label: 'Elevado' },
  CRITICO: { bg: 'bg-red-100', text: 'text-red-700', label: 'Crítico' },
};

export default function StatusBadge({ status, className = '' }: { status: string; className?: string }) {
  const cfg = statusConfig[status] || statusConfig.SIN_DATOS;
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${cfg.bg} ${cfg.text} ${className}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${cfg.text.replace('text-', 'bg-')} mr-1.5`} />
      {cfg.label}
    </span>
  );
}
