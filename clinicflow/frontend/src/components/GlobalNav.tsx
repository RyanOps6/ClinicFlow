import { useEffect, useState } from 'react';
import { Activity, User, LogOut } from 'lucide-react';
import { BASE } from '../api/client';
import { NavLink, Link } from 'react-router-dom';

function useHealthStatus() {
  const [status, setStatus] = useState<'operational' | 'degraded' | 'unknown'>('unknown');

  useEffect(() => {
    let isActive = true;
    const check = async () => {
      try {
        const res = await fetch(`${BASE}/api/health`, { signal: AbortSignal.timeout(5000) });
        if (isActive) setStatus(res.ok ? 'operational' : 'degraded');
      } catch {
        if (isActive) setStatus('degraded');
      }
    };
    check();
    const id = setInterval(check, 30000);
    return () => { isActive = false; clearInterval(id); };
  }, []);

  return status;
}

export default function GlobalNav() {
  const health = useHealthStatus();

  const statusConfig = {
    operational: { color: 'bg-emerald-500', text: 'Operational', bg: 'bg-emerald-50 text-emerald-700 border border-emerald-200' },
    degraded: { color: 'bg-amber-500', text: 'Degraded', bg: 'bg-amber-50 text-amber-700 border border-amber-200' },
    unknown: { color: 'bg-slate-400', text: 'Checking...', bg: 'bg-slate-50 text-slate-500 border border-slate-200' },
  } as const;

  const s = statusConfig[health];

  return (
    <header id="global-header" className="sticky top-0 z-50 w-full backdrop-blur-md bg-white/75 border-b border-slate-200 text-slate-800 px-6 py-3 flex flex-col md:flex-row items-center justify-between shadow-sm gap-4 md:gap-0">
      
      {/* Brand logo linked to Home Page */}
      <Link to="/" className="flex items-center gap-2.5 hover:opacity-90 transition-opacity">
        <div className="w-8 h-8 bg-gradient-to-tr from-teal-500 to-sky-500 rounded-lg flex items-center justify-center shadow-md shadow-teal-500/10">
          <Activity className="w-5 h-5 text-white animate-pulse" />
        </div>
        <span className="font-bold text-base tracking-tight bg-gradient-to-r from-teal-600 to-sky-600 bg-clip-text text-transparent">
          ClinicFlow Executive
        </span>
      </Link>

      {/* Modernist Editorial Routing Navigation Bar */}
      <nav className="flex items-center gap-6 sm:gap-8 font-sans">
        <NavLink 
          to="/" 
          className={({ isActive }) => 
            `text-[10px] font-bold uppercase tracking-widest transition-colors duration-200 relative py-1.5
            ${isActive ? 'text-teal-600' : 'text-slate-500 hover:text-slate-800'}`
          }
        >
          {({ isActive }) => (
            <>
              <span>Home</span>
              {isActive && (
                <span className="absolute bottom-0 left-0 right-0 h-[2px] bg-teal-500 rounded-full animate-fadeIn" />
              )}
            </>
          )}
        </NavLink>
        <NavLink 
          to="/playground" 
          className={({ isActive }) => 
            `text-[10px] font-bold uppercase tracking-widest transition-colors duration-200 relative py-1.5
            ${isActive ? 'text-teal-600' : 'text-slate-500 hover:text-slate-800'}`
          }
        >
          {({ isActive }) => (
            <>
              <span>Playground</span>
              {isActive && (
                <span className="absolute bottom-0 left-0 right-0 h-[2px] bg-teal-500 rounded-full animate-fadeIn" />
              )}
            </>
          )}
        </NavLink>
        <NavLink 
          to="/sessions" 
          className={({ isActive }) => 
            `text-[10px] font-bold uppercase tracking-widest transition-colors duration-200 relative py-1.5
            ${isActive ? 'text-teal-600' : 'text-slate-500 hover:text-slate-800'}`
          }
        >
          {({ isActive }) => (
            <>
              <span>Sessions</span>
              {isActive && (
                <span className="absolute bottom-0 left-0 right-0 h-[2px] bg-teal-500 rounded-full animate-fadeIn" />
              )}
            </>
          )}
        </NavLink>
        <NavLink 
          to="/appointments" 
          className={({ isActive }) => 
            `text-[10px] font-bold uppercase tracking-widest transition-colors duration-200 relative py-1.5
            ${isActive ? 'text-teal-600' : 'text-slate-500 hover:text-slate-800'}`
          }
        >
          {({ isActive }) => (
            <>
              <span>Appointments</span>
              {isActive && (
                <span className="absolute bottom-0 left-0 right-0 h-[2px] bg-teal-500 rounded-full animate-fadeIn" />
              )}
            </>
          )}
        </NavLink>
      </nav>

      {/* User profile & backend stats */}
      <div className="flex items-center gap-4">
        <div className={`hidden sm:flex items-center gap-1.5 px-3 py-1 rounded-full ${s.bg} text-xs font-semibold transition-all duration-300 ease-in-out`}>
          <span className={`w-1.5 h-1.5 rounded-full ${s.color} animate-pulse transition-all duration-300 ease-in-out`} />
          <span className="transition-all duration-300 ease-in-out">Backend API: {s.text}</span>
        </div>

        <div className="flex items-center gap-2.5 pl-0 sm:pl-4 sm:border-l border-slate-200">
          <div className="w-8 h-8 bg-slate-100 rounded-full flex items-center justify-center border border-slate-200">
            <User className="w-4 h-4 text-slate-500" />
          </div>
          <div className="hidden lg:block">
            <p className="text-xs text-slate-800 font-bold">Dr. Sarah Chen</p>
            <p className="text-[10px] text-slate-500 font-medium">Chief Administrator</p>
          </div>
        </div>

        {localStorage.getItem('auth_token') && (
          <button
            onClick={() => {
              localStorage.removeItem('auth_token');
              window.location.reload();
            }}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-50 hover:bg-rose-50 text-slate-500 hover:text-rose-600 border border-slate-200 hover:border-rose-200 rounded-lg text-[10px] font-bold transition-all duration-200 shadow-sm"
            title="Sign Out"
          >
            <LogOut className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Sign Out</span>
          </button>
        )}
      </div>
    </header>
  );
}
