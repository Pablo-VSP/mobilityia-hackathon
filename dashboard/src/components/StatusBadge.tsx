const statusConfig: Record<string, { bg: string; text: string; label: string }> = {
  EFICIENTE: { bg: 'bg-emerald-500/20', text: 'text-emerald-400', label: 'Eficiente' },
  ALERTA_MODERADA: { bg: 'bg-amber-500/20', text: 'text-amber-400', label: 'Alerta Moderada' },
  ALERTA_SIGNIFICATIVA: { bg: 'bg-red-500/20', text: 'text-red-400', label: 'Alerta Significativa' },
  SIN_DATOS: { bg: 'bg-slate-500/20', text: 'text-slate-400', label: 'Sin Datos' },
  BAJO: { bg: 'bg-emerald-500/20', text: 'text-emerald-400', label: 'Bajo' },
  MODERADO: { bg: 'bg-amber-500/20', text: 'text-amber-400', label: 'Moderado' },
  ELEVADO: { bg: 'bg-orange-500/20', text: 'text-orange-400', label: 'Elevado' },
  CRITICO: { bg: 'bg-red-500/20', text: 'text-red-400', label: 'Crítico' },
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
