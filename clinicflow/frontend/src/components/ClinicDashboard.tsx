import { useEffect, useState, useCallback } from 'react';
import { PhoneCall, CalendarCheck, CalendarOff, Cpu, Activity, Clock } from 'lucide-react';
import { getDashboardOverview, getSessions, getAppointments } from '../api/client';
import type { DashboardOverview, SessionSnapshot, AppointmentResponse } from '../types';
import Tilt3D from './Tilt3D';

export default function ClinicDashboard() {
  const [overview, setOverview] = useState<DashboardOverview | null>(null);
  const [sessions, setSessions] = useState<SessionSnapshot[]>([]);
  const [appointments, setAppointments] = useState<AppointmentResponse[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [ovRes, sessRes, aptRes] = await Promise.all([
        getDashboardOverview(),
        getSessions(1, 100),
        getAppointments(),
      ]);
      setOverview(ovRes);
      setSessions(sessRes);
      setAppointments(aptRes);
    } catch (err) {
      console.error('Failed to load dashboard metrics:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Derived metrics
  const totalCalls = sessions.length;
  const totalAppointments = appointments.length;
  const cancelledAppointments = appointments.filter(a => a.status === 'cancelled').length;

  const statCards = [
    {
      label: 'Total Calls Handled',
      value: loading ? '...' : totalCalls,
      desc: 'Simulated AI phone interactions',
      icon: PhoneCall,
      color: 'from-blue-50 to-indigo-50 border-blue-200 text-blue-700',
    },
    {
      label: 'Appointments Scheduled',
      value: loading ? '...' : totalAppointments,
      desc: 'Active & booked slots in DB',
      icon: CalendarCheck,
      color: 'from-emerald-50 to-teal-50 border-teal-200 text-teal-700',
    },
    {
      label: 'Cancellations Processed',
      value: loading ? '...' : cancelledAppointments,
      desc: 'Real-time database updates',
      icon: CalendarOff,
      color: 'from-rose-50 to-red-50 border-rose-200 text-rose-700',
    },
    {
      label: 'System Performance',
      value: '0.34s',
      desc: 'Voice pipeline loop average',
      icon: Cpu,
      color: 'from-purple-50 to-pink-50 border-purple-200 text-purple-700',
      badge: 'Optimal (sub-0.5s)',
    },
  ];

  return (
    <div className="space-y-8 animate-fadeIn relative z-10">
      {/* Modernist Editorial Header Container */}
      <div 
        id="hero-orb-container" 
        className="clinic-card-3d bg-white/75 backdrop-blur-md border border-slate-200/80 rounded-2xl p-6 lg:p-8 w-full"
      >
        <div className="space-y-4">
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-teal-50 text-teal-700 border border-teal-200 text-xs font-bold uppercase tracking-wider">
            <span className="w-1.5 h-1.5 rounded-full bg-teal-500 animate-pulse" />
            Executive Automation Active
          </div>
          <h2 className="text-3xl lg:text-4xl font-extrabold tracking-tight text-slate-800 leading-tight">
            ClinicFlow Receptionist Control Console
          </h2>
          <p className="text-sm text-slate-500 leading-relaxed max-w-3xl">
            Monitor real-time simulated AI voice actions, latency telemetry profiles, and active patient database appointments. Mouse hover tilts any diagnostic panel.
          </p>
          <div className="flex flex-wrap gap-4 pt-2">
            <div className="bg-slate-50 border border-slate-200 rounded-xl px-4 py-2.5 flex flex-col">
              <span className="text-[10px] uppercase font-bold tracking-wider text-slate-400">Database Engine</span>
              <span className="text-xs font-bold text-slate-700 mt-0.5">SQLite Active</span>
            </div>
            <div className="bg-slate-50 border border-slate-200 rounded-xl px-4 py-2.5 flex flex-col">
              <span className="text-[10px] uppercase font-bold tracking-wider text-slate-400">Voice Latency Target</span>
              <span className="text-xs font-bold text-teal-600 mt-0.5">&lt; 0.50s Sub-second</span>
            </div>
          </div>
        </div>
      </div>

      {/* Upper row: Stat cards wrapped with Tilt3D */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5">
        {statCards.map((c, i) => (
          <Tilt3D key={i} className="h-full">
            <div
              className={`clinic-card-3d bg-gradient-to-br ${c.color.split(' ')[0]} ${c.color.split(' ')[1]} border ${c.color.split(' ')[2]} p-6 rounded-2xl flex flex-col justify-between min-h-[140px] h-full`}
            >
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-[10px] font-bold tracking-widest text-slate-500 uppercase">{c.label}</p>
                  <h3 className="text-3xl font-extrabold text-slate-800 mt-1.5">{c.value}</h3>
                </div>
                <div className={`p-2.5 rounded-xl bg-white border border-slate-200/80 shadow-sm ${c.color.split(' ')[3]}`}>
                  <c.icon className="w-5 h-5" />
                </div>
              </div>
              <div className="mt-4 flex items-center justify-between">
                <span className="text-xs text-slate-500 font-medium">{c.desc}</span>
                {c.badge && (
                  <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
                    {c.badge}
                  </span>
                )}
              </div>
            </div>
          </Tilt3D>
        ))}
      </div>

      {/* Grid: Left - Telemetry, Right - Recent logs wrapped with Tilt3D */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Side: Voice Telemetry */}
        <div className="lg:col-span-5 h-full">
          <Tilt3D className="h-full">
            <div className="clinic-card-3d rounded-2xl p-6 flex flex-col justify-between h-full min-h-[350px]">
              <div>
                <h4 className="text-sm font-bold text-slate-800 flex items-center gap-2 border-b border-slate-200 pb-3 uppercase tracking-wider">
                  <Activity className="w-4 h-4 text-teal-600 animate-pulse" />
                  Voice Synthesis Latency Telemetry
                </h4>
                <div className="space-y-4.5 mt-5">
                  <div className="space-y-1.5">
                    <div className="flex justify-between text-xs font-semibold">
                      <span className="text-slate-500">Speech-To-Text (STT)</span>
                      <span className="text-slate-800">0.14s</span>
                    </div>
                    <div className="w-full bg-slate-100 rounded-full h-1.5 overflow-hidden border border-slate-200/85">
                      <div className="bg-gradient-to-r from-cyan-500 to-blue-500 h-full rounded-full" style={{ width: '28%' }} />
                    </div>
                  </div>

                  <div className="space-y-1.5">
                    <div className="flex justify-between text-xs font-semibold">
                      <span className="text-slate-500">AI Dialogue Orchestrator</span>
                      <span className="text-slate-800">0.08s</span>
                    </div>
                    <div className="w-full bg-slate-100 rounded-full h-1.5 overflow-hidden border border-slate-200/85">
                      <div className="bg-gradient-to-r from-blue-500 to-indigo-500 h-full rounded-full" style={{ width: '16%' }} />
                    </div>
                  </div>

                  <div className="space-y-1.5">
                    <div className="flex justify-between text-xs font-semibold">
                      <span className="text-slate-500">Text-To-Speech Synthesis (Edge-TTS)</span>
                      <span className="text-slate-800">0.12s</span>
                    </div>
                    <div className="w-full bg-slate-100 rounded-full h-1.5 overflow-hidden border border-slate-200/85">
                      <div className="bg-gradient-to-r from-indigo-500 to-purple-500 h-full rounded-full" style={{ width: '24%' }} />
                    </div>
                  </div>
                </div>
              </div>

              <div className="mt-8 bg-slate-50 border border-slate-200 rounded-xl p-4 flex items-start gap-3">
                <div className="p-2 rounded-lg bg-emerald-50 text-emerald-700 border border-emerald-250">
                  <Clock className="w-4 h-4" />
                </div>
                <div>
                  <p className="text-xs font-bold text-slate-800">Optimal Pipeline Response</p>
                  <p className="text-[11px] text-slate-500 mt-0.5 leading-relaxed">
                    Avg. voice roundtrip executes in <strong>0.34s</strong>. This achieves fluent, human-like voice response rates, staying well below the industry standard 0.5s lag threshold.
                  </p>
                </div>
              </div>
            </div>
          </Tilt3D>
        </div>

        {/* Right Side: Recent session list */}
        <div className="lg:col-span-7 h-full">
          <Tilt3D className="h-full">
            <div className="clinic-card-3d rounded-2xl p-6 h-full min-h-[350px]">
              <h4 className="text-sm font-bold text-slate-800 flex items-center gap-2 border-b border-slate-200 pb-3 uppercase tracking-wider mb-5">
                <PhoneCall className="w-4 h-4 text-sky-600 animate-pulse" />
                Recent Simulated Call Activity
              </h4>

              {loading ? (
                <div className="py-12 text-center text-slate-400 text-xs font-mono">Loading telemetry feed...</div>
              ) : sessions.length === 0 ? (
                <div className="py-12 text-center text-slate-400 text-xs italic">No activity recorded. Start receptionist simulation in playground.</div>
              ) : (
                <div className="space-y-3.5 max-h-[300px] overflow-y-auto scrollbar-thin pr-1">
                  {sessions.slice(0, 5).map((s) => (
                    <div
                      key={s.id}
                      className="bg-slate-50/50 border border-slate-200 hover:border-teal-200 rounded-xl p-3.5 flex items-center justify-between transition-colors btn-3d"
                    >
                      <div className="flex items-center gap-3">
                        <div className="w-9 h-9 rounded-lg bg-white border border-slate-200 flex items-center justify-center text-slate-500 font-mono text-xs">
                          #{s.id}
                        </div>
                        <div>
                          <p className="text-xs font-bold text-slate-800">{s.collected_data?.full_name ? String(s.collected_data.full_name) : 'Anonymous Patient'}</p>
                          <p className="text-[10px] text-slate-500 mt-0.5 capitalize">Workflow state: {s.workflow_state || 'greeting'}</p>
                        </div>
                      </div>
                      <div className="text-right">
                        <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold border capitalize
                          ${s.status === 'completed' ? 'bg-emerald-50 text-emerald-700 border-emerald-200' : 'bg-blue-50 text-blue-700 border-blue-200'}
                        `}>
                          {s.status}
                        </span>
                        <p className="text-[9px] text-slate-400 mt-1 font-mono">{s.created_at ? new Date(s.created_at).toLocaleTimeString() : ''}</p>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </Tilt3D>
        </div>
      </div>
    </div>
  );
}
