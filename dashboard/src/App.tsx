import { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { getCurrentUser } from './lib/auth';
import LoginPage from './components/LoginPage';
import Layout from './components/Layout';
import MapPage from './pages/MapPage';
import AlertasPage from './pages/AlertasPage';
import EficienciaPage from './pages/EficienciaPage';
import AmbientalPage from './pages/AmbientalPage';
import ChatPage from './pages/ChatPage';

export default function App() {
  const [authenticated, setAuthenticated] = useState(false);
  const [checking, setChecking] = useState(true);

  useEffect(() => {
    const user = getCurrentUser();
    if (user) {
      user.getSession((err: Error | null) => {
        setAuthenticated(!err);
        setChecking(false);
      });
    } else {
      setChecking(false);
    }
  }, []);

  if (checking) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-900">
        <div className="text-slate-400">Cargando...</div>
      </div>
    );
  }

  if (!authenticated) {
    return <LoginPage onLogin={() => setAuthenticated(true)} />;
  }

  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout onLogout={() => setAuthenticated(false)} />}>
          <Route path="/" element={<MapPage />} />
          <Route path="/alertas" element={<AlertasPage />} />
          <Route path="/eficiencia" element={<EficienciaPage />} />
          <Route path="/ambiental" element={<AmbientalPage />} />
          <Route path="/chat" element={<ChatPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
