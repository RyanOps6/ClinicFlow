import { useEffect, useState, useCallback } from 'react';
import { Phone, Users, BarChart3, Eye, Clock } from 'lucide-react';
import type { DashboardOverview } from '../types';
import { getDashboardOverview } from '../api/client';

function MetricCard({ label, value, icon: Icon, color }: { label: string; value: string | number; icon: React.ElementType; color: string }) {
  return (
    <div className="bg-white rounded-xl border border-slate-200 p-5 flex items-center gap-4 shadow-sm">
      <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${color}`}>
        <Icon className="w-6 h-6 text-white" />
      </div>
      <div>
        <p className="text-2xl font-bold text-slate-800">{value}</p>
        <p className="text-xs text-slate-500 font-medium">{label}</p>
      </div>
    </div>
  );
}

export default function SessionsLog() {
  const [data, setData] = useState<DashboardOverview | null>(null);
  const [loading, setLoading] = useState(true);

  const fetch = useCallback(async () => {
    setLoading(true);
    try {
      const res = await getDashboardOverview();
      setData(res);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetch();
  }, [fetch]);

  const sessions = data?.recent_sessions ?? [];
  const totalSessions = sessions.length;
  const activeCalls = sessions.filter(s => s.status === 'active').length;
  const completionRate = totalSessions > 0
    ? Math.round(((sessions.filter(s => s.status === 'completed').length / totalSessions) * 100))
    : 0;

  const statusStyles: Record<string, string> = {
    active: 'bg-medical-50 text-medical-700',
    completed: 'bg-emerald-50 text-emerald-700',
    terminated: 'bg-slate-100 text-slate-600',
    cancelled: 'bg-red-50 text-red-700',
  };

  return (
    <div className="space-y-6">
      {/* Metrics */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <MetricCard label="Total Sessions Today" value={totalSessions} icon={Phone} color="bg-medical-500" />
        <MetricCard label="Active Calls" value={activeCalls} icon={Clock} color="bg-amber-500" />
        <MetricCard label="Automation Completion Rate" value={`${completionRate}%`} icon={BarChart3} color="bg-emerald-500" />
      </div>

      {/* Table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="px-5 py-4 border-b border-slate-100 flex items-center justify-between">
          <h3 className="text-sm font-semibold text-slate-700 flex items-center gap-2">
            <Users className="w-4 h-4 text-medical-500" />
            Recent Call Sessions
          </h3>
        </div>

        {loading ? (
          <div className="p-8 text-center text-slate-400 text-sm">Loading sessions...</div>
        ) : sessions.length === 0 ? (
          <div className="p-8 text-center text-slate-400 text-sm">No sessions recorded today.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-slate-100">
                  <th className="text-left px-5 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">Session ID</th>
                  <th className="text-left px-5 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">Patient</th>
                  <th className="text-left px-5 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">Intent</th>
                  <th className="text-left px-5 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">Channel</th>
                  <th className="text-left px-5 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">Status</th>
                  <th className="text-left px-5 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">Action</th>
                </tr>
              </thead>
              <tbody>
                {sessions.map((s) => (
                  <tr key={s.id} className="border-b border-slate-50 hover:bg-slate-50 transition-colors">
                    <td className="px-5 py-3.5 text-sm font-medium text-slate-700">#{s.id}</td>
                    <td className="px-5 py-3.5 text-sm text-slate-600">{s.patient_name ?? '—'}</td>
                    <td className="px-5 py-3.5">
                      <span className="text-sm text-slate-600 capitalize">{s.intent || 'unknown'}</span>
                    </td>
                    <td className="px-5 py-3.5 text-sm text-slate-600 capitalize">{s.session_type}</td>
                    <td className="px-5 py-3.5">
                      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${statusStyles[s.status] ?? 'bg-slate-100 text-slate-600'}`}>
                        {s.status}
                      </span>
                    </td>
                    <td className="px-5 py-3.5">
                      <button className="flex items-center gap-1 text-xs text-medical-600 hover:text-medical-700 font-medium transition-colors">
                        <Eye className="w-3.5 h-3.5" /> View
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
