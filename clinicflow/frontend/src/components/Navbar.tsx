import { useState } from 'react';

interface NavbarProps {
  serverStatus: 'operational' | 'degraded' | 'down';
}

export default function Navbar({ serverStatus }: NavbarProps) {
  const [showProfile, setShowProfile] = useState(false);

  const statusConfig = {
    operational: { color: 'bg-emerald-500', bg: 'bg-emerald-50', text: 'text-emerald-700', label: 'Operational' },
    degraded: { color: 'bg-amber-500', bg: 'bg-amber-50', text: 'text-amber-700', label: 'Degraded' },
    down: { color: 'bg-red-500', bg: 'bg-red-50', text: 'text-red-700', label: 'Down' },
  };

  const s = statusConfig[serverStatus];

  return (
    <header className="bg-white border-b border-slate-200">
      <div className="max-w-[1600px] mx-auto px-6 h-16 flex items-center justify-between">
        {/* Left: Logo & Brand */}
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-medical-500 flex items-center justify-center shadow-sm">
            <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
            </svg>
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-lg font-bold text-slate-900 tracking-tight">ClinicFlow</span>
            <span className="text-sm font-medium text-slate-500 hidden sm:inline">Dashboard</span>
          </div>
        </div>

        {/* Center: Server Status */}
        <div className={`flex items-center gap-2 px-3 py-1.5 rounded-full ${s.bg} border border-slate-200`}>
          <span className={`w-2 h-2 rounded-full ${s.color} animate-pulse`} />
          <span className={`text-xs font-semibold ${s.text}`}>Backend API: {s.label}</span>
        </div>

        {/* Right: Profile */}
        <div className="relative">
          <button
            onClick={() => setShowProfile(!showProfile)}
            className="flex items-center gap-2.5 px-2 py-1.5 rounded-lg hover:bg-slate-50 transition-colors"
          >
            <div className="w-8 h-8 rounded-full bg-medical-100 flex items-center justify-center border border-medical-200">
              <svg className="w-4 h-4 text-medical-600" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z" />
              </svg>
            </div>
            <div className="hidden sm:block text-left">
              <p className="text-sm font-semibold text-slate-900 leading-tight">Dr. Sarah Chen</p>
              <p className="text-xs text-slate-500 leading-tight">Administrator</p>
            </div>
            <svg className="w-4 h-4 text-slate-400" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5" />
            </svg>
          </button>

          {showProfile && (
            <div className="absolute right-0 top-full mt-1 w-56 bg-white rounded-xl shadow-lg border border-slate-200 py-2 animate-fade-in z-50">
              <div className="px-4 py-3 border-b border-slate-100">
                <p className="text-sm font-semibold text-slate-900">Dr. Sarah Chen</p>
                <p className="text-xs text-slate-500">sarah.chen@clinicflow.com</p>
              </div>
              <div className="py-1">
                <button className="w-full text-left px-4 py-2 text-sm text-slate-700 hover:bg-slate-50 transition-colors">
                  My Profile
                </button>
                <button className="w-full text-left px-4 py-2 text-sm text-slate-700 hover:bg-slate-50 transition-colors">
                  Settings
                </button>
                <button className="w-full text-left px-4 py-2 text-sm text-red-600 hover:bg-red-50 transition-colors">
                  Sign Out
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
