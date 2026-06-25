import { useEffect, useState } from 'react';
import { Activity, User } from 'lucide-react';
import { BASE } from '../api/client';

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
    <header className="backdrop-blur-md bg-white/75 border-b border-slate-200 text-slate-800 px-6 py-3 flex items-center justify-between relative z-10 shadow-sm">
      <div className="flex items-center gap-2.5">
        <div className="w-8 h-8 bg-gradient-to-tr from-teal-500 to-sky-500 rounded-lg flex items-center justify-center shadow-md shadow-teal-500/10">
          <Activity className="w-5 h-5 text-white animate-pulse" />
        </div>
        <span className="font-bold text-base tracking-tight bg-gradient-to-r from-teal-600 to-sky-600 bg-clip-text text-transparent">
          ClinicFlow Executive
        </span>
      </div>

      <div className="flex items-center gap-4">
        <div className={`flex items-center gap-1.5 px-3 py-1 rounded-full ${s.bg} text-xs font-semibold`}>
          <span className={`w-1.5 h-1.5 rounded-full ${s.color} animate-pulse`} />
          <span>Backend API: {s.text}</span>
        </div>

        <div className="flex items-center gap-2.5 pl-4 border-l border-slate-250">
          <div className="w-8 h-8 bg-slate-100 rounded-full flex items-center justify-center border border-slate-200">
            <User className="w-4 h-4 text-slate-500" />
          </div>
          <div className="hidden sm:block">
            <p className="text-xs text-slate-800 font-bold">Dr. Sarah Chen</p>
            <p className="text-[10px] text-slate-500 font-medium">Chief Administrator</p>
          </div>
        </div>
      </div>
    </header>
  );
}
