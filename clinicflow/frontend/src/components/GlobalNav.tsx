import { useEffect, useState } from 'react';
import { Activity, User } from 'lucide-react';

function useHealthStatus() {
  const [status, setStatus] = useState<'operational' | 'degraded' | 'unknown'>('unknown');

  useEffect(() => {
    let isActive = true;
    const check = async () => {
      try {
        const res = await fetch('/api/health', { signal: AbortSignal.timeout(5000) });
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
    operational: { color: 'bg-emerald-500', text: 'Operational', bg: 'bg-emerald-50' },
    degraded: { color: 'bg-amber-500', text: 'Degraded', bg: 'bg-amber-50' },
    unknown: { color: 'bg-slate-400', text: 'Checking...', bg: 'bg-slate-50' },
  } as const;

  const s = statusConfig[health];

  return (
    <header className="bg-slate-900 text-white px-6 py-3 flex items-center justify-between shadow-sm">
      <div className="flex items-center gap-2.5">
        <div className="w-8 h-8 bg-medical-500 rounded-lg flex items-center justify-center">
          <Activity className="w-5 h-5 text-white" />
        </div>
        <span className="font-semibold text-base tracking-tight">ClinicFlow Dashboard</span>
      </div>

      <div className="flex items-center gap-3">
        <div className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full ${s.bg} text-xs font-medium`}>
          <span className={`w-2 h-2 rounded-full ${s.color}`} />
          <span className="text-slate-700">Backend API: {s.text}</span>
        </div>

        <div className="flex items-center gap-2 pl-3 border-l border-slate-700">
          <div className="w-8 h-8 bg-slate-700 rounded-full flex items-center justify-center">
            <User className="w-4 h-4 text-slate-300" />
          </div>
          <div className="hidden sm:block">
            <p className="text-xs text-slate-300 font-medium">Dr. Sarah Chen</p>
            <p className="text-[10px] text-slate-400">Administrator</p>
          </div>
        </div>
      </div>
    </header>
  );
}
