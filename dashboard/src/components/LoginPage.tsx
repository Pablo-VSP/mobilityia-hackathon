import { useState } from 'react';
import { signIn } from '../lib/auth';

interface Props { onLogin: () => void }

const LOGO_MOBILITY = '/IMG_Logo Blanco_V1_04-08-26_Mobility ADO.svg';
const LOGO_SIIAB = '/IMG_Logo Blanco_V1_04-08-26_SIIAB.svg';
const LOGO_TELEMATICS = '/IMG_Logo Blanco_V1_04-08-26_Telematics.svg';

export default function LoginPage({ onLogin }: Props) {
  const [email, setEmail] = useState('demo@adomobilityia.com');
  const [password, setPassword] = useState('DemoADO2026!');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      await signIn(email, password);
      onLogin();
    } catch (err: any) {
      setError(err.message || 'Error de autenticación');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-gradient-to-br from-slate-800 via-slate-900 to-slate-800 px-4">
      <div className="w-full max-w-md p-8 bg-white rounded-2xl shadow-xl border border-slate-200">
        {/* Logo principal */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center bg-slate-900 rounded-2xl p-4 mb-4">
            <img src={LOGO_MOBILITY} alt="Mobility ADO" className="h-10" />
          </div>
          <h1 className="text-2xl font-bold text-slate-800">ADO MobilityIA</h1>
          <p className="text-slate-500 mt-1">Plataforma de Inteligencia de Flota</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm text-slate-600 mb-1">Email</label>
            <input
              type="email"
              value={email}
              onChange={e => setEmail(e.target.value)}
              className="w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-lg text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-red-500 focus:border-transparent"
              placeholder="usuario@ado.com"
            />
          </div>
          <div>
            <label className="block text-sm text-slate-600 mb-1">Contraseña</label>
            <input
              type="password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              className="w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-lg text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-red-500 focus:border-transparent"
            />
          </div>
          {error && <p className="text-red-500 text-sm">{error}</p>}
          <button
            type="submit"
            disabled={loading}
            className="w-full py-3 bg-red-600 hover:bg-red-700 disabled:bg-slate-300 text-white font-semibold rounded-lg transition-colors"
          >
            {loading ? 'Ingresando...' : 'Ingresar'}
          </button>
        </form>

        <p className="text-center text-slate-400 text-xs mt-6">
          Hackathon AWS Builders League 2026 — Datos simulados
        </p>
      </div>

      {/* Footer logos */}
      <div className="mt-8 flex items-center gap-6 opacity-70">
        <img src={LOGO_SIIAB} alt="SIIAB" className="h-6" />
        <img src={LOGO_TELEMATICS} alt="Telematics" className="h-6" />
        <img src={LOGO_MOBILITY} alt="Mobility ADO" className="h-6" />
      </div>
    </div>
  );
}
