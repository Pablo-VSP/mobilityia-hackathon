import { NavLink, Outlet } from 'react-router-dom';
import { Map, AlertTriangle, Fuel, Leaf, MessageSquare, LogOut } from 'lucide-react';
import { signOut } from '../lib/auth';

const LOGO_MOBILITY = '/IMG_Logo Blanco_V1_04-08-26_Mobility ADO.svg';

const navItems = [
  { to: '/', icon: Map, label: 'Mapa' },
  { to: '/alertas', icon: AlertTriangle, label: 'Alertas' },
  { to: '/eficiencia', icon: Fuel, label: 'Eficiencia' },
  { to: '/ambiental', icon: Leaf, label: 'Ambiental' },
  { to: '/chat', icon: MessageSquare, label: 'Chat IA' },
];

interface Props { onLogout: () => void }

export default function Layout({ onLogout }: Props) {
  const handleLogout = () => { signOut(); onLogout(); };

  return (
    <div className="flex flex-col md:flex-row h-screen overflow-hidden">
      {/* Desktop sidebar */}
      <nav className="hidden md:flex w-20 bg-white border-r border-slate-200 flex-col items-center py-4 gap-2 shrink-0 shadow-sm">
        <div className="w-14 h-14 bg-slate-900 rounded-xl flex items-center justify-center mb-4 p-2">
          <img src={LOGO_MOBILITY} alt="Mobility ADO" className="w-full h-full object-contain" />
        </div>

        {navItems.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) =>
              `w-14 h-14 flex flex-col items-center justify-center rounded-xl transition-colors text-xs gap-1 ${
                isActive
                  ? 'bg-red-50 text-red-600'
                  : 'text-slate-500 hover:text-slate-700 hover:bg-slate-100'
              }`
            }
          >
            <Icon className="w-5 h-5" />
            <span className="truncate">{label}</span>
          </NavLink>
        ))}

        <div className="mt-auto">
          <button
            onClick={handleLogout}
            className="w-14 h-14 flex flex-col items-center justify-center rounded-xl text-slate-500 hover:text-red-600 hover:bg-red-50 transition-colors text-xs gap-1"
          >
            <LogOut className="w-5 h-5" />
            <span>Salir</span>
          </button>
        </div>
      </nav>

      {/* Main content */}
      <main className="flex-1 overflow-hidden bg-slate-50">
        <Outlet />
      </main>

      {/* Mobile bottom nav */}
      <nav className="md:hidden bg-white border-t border-slate-200 flex items-center justify-around shrink-0 safe-bottom shadow-[0_-2px_10px_rgba(0,0,0,0.05)]">
        {navItems.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) =>
              `flex flex-col items-center justify-center py-2 px-1 transition-colors text-[10px] gap-0.5 min-w-0 flex-1 ${
                isActive
                  ? 'text-red-600'
                  : 'text-slate-500'
              }`
            }
          >
            <Icon className="w-5 h-5" />
            <span className="truncate">{label}</span>
          </NavLink>
        ))}
        <button
          onClick={handleLogout}
          className="flex flex-col items-center justify-center py-2 px-1 text-slate-500 text-[10px] gap-0.5 min-w-0 flex-1"
        >
          <LogOut className="w-5 h-5" />
          <span>Salir</span>
        </button>
      </nav>
    </div>
  );
}
