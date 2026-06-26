import { useEffect, useState, useCallback } from 'react';
import { Calendar, User, Stethoscope, Clock, CheckCircle2, XCircle, Ban } from 'lucide-react';
import type { AppointmentResponse } from '../types';
import { getAppointments, cancelAppointmentPatch } from '../api/client';

export default function AppointmentsLedger() {
  const [appointments, setAppointments] = useState<AppointmentResponse[]>([]);
  const [loading, setLoading] = useState(true);

  const fetch = useCallback(async () => {
    setLoading(true);
    try {
      const data = await getAppointments();
      setAppointments(data);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetch();
  }, [fetch]);

  const handleCancel = async (id: number) => {
    try {
      const updated = await cancelAppointmentPatch(id);
      setAppointments(prev => prev.map(a => a.id === id ? updated : a));
    } catch (err) {
      console.error('Failed to cancel appointment:', err);
      alert('Failed to cancel appointment');
    }
  };

  const statusConfig: Record<string, { label: string; bg: string; text: string; icon: React.ElementType }> = {
    booked: { label: 'Upcoming', bg: 'bg-teal-50 border border-teal-200', text: 'text-teal-700', icon: CheckCircle2 },
    rescheduled: { label: 'Rescheduled', bg: 'bg-amber-50 border border-amber-200', text: 'text-amber-700', icon: Clock },
    cancelled: { label: 'Cancelled', bg: 'bg-rose-50 border border-rose-200', text: 'text-rose-700', icon: XCircle },
    completed: { label: 'Completed', bg: 'bg-emerald-50 border border-emerald-200', text: 'text-emerald-700', icon: CheckCircle2 },
  };

  return (
    <div className="space-y-6 animate-fadeIn relative z-10">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-bold text-slate-800 flex items-center gap-2 uppercase tracking-wider">
          <Calendar className="w-4 h-4 text-teal-600 animate-pulse" />
          Appointments Ledger & Active Cancellations
        </h3>
        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold bg-slate-100 border border-slate-200 text-slate-650">
          {appointments.length} total
        </span>
      </div>

      {loading ? (
        <div className="py-12 text-center text-slate-450 text-xs font-mono">Loading appointment database...</div>
      ) : appointments.length === 0 ? (
        <div className="clinic-card-3d p-8 text-center text-slate-500 text-xs rounded-xl">
          No appointments found in database. Start receptionist playground simulation to book slots.
        </div>
      ) : (
        <div className="clinic-card-3d rounded-2xl overflow-hidden bg-white">
          <div className="overflow-auto max-h-[calc(100vh-20rem)] lg:max-h-[calc(100vh-16rem)] scrollbar-thin">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-slate-200 bg-slate-50">
                  <th className="px-6 py-4 text-[10px] font-bold text-slate-500 uppercase tracking-wider">Appointment ID</th>
                  <th className="px-6 py-4 text-[10px] font-bold text-slate-500 uppercase tracking-wider">Patient Name</th>
                  <th className="px-6 py-4 text-[10px] font-bold text-slate-500 uppercase tracking-wider">Reason for Visit</th>
                  <th className="px-6 py-4 text-[10px] font-bold text-slate-500 uppercase tracking-wider">Schedule Details</th>
                  <th className="px-6 py-4 text-[10px] font-bold text-slate-500 uppercase tracking-wider">Doctor</th>
                  <th className="px-6 py-4 text-[10px] font-bold text-slate-500 uppercase tracking-wider">Status</th>
                  <th className="px-6 py-4 text-[10px] font-bold text-slate-500 uppercase tracking-wider text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-250">
                {appointments.map((a) => {
                  const sc = statusConfig[a.status] || { label: a.status, bg: 'bg-slate-100 border border-slate-200', text: 'text-slate-600', icon: Clock };
                  const Icon = sc.icon;
                  const isBooked = a.status === 'booked' || a.status === 'rescheduled';
                  return (
                    <tr key={a.id} className="hover:bg-slate-50/50 transition-colors">
                      <td className="px-6 py-4.5 text-xs font-semibold text-slate-500 font-mono">#{a.id}</td>
                      <td className="px-6 py-4.5">
                        <div className="flex items-center gap-2.5">
                          <div className="w-7 h-7 rounded-full bg-slate-100 border border-slate-200 flex items-center justify-center text-slate-500">
                            <User className="w-3.5 h-3.5" />
                          </div>
                          <span className="text-xs font-bold text-slate-800">{a.patient_name ?? 'Unknown Patient'}</span>
                        </div>
                      </td>
                      <td className="px-6 py-4.5 text-xs text-slate-650 max-w-[200px] truncate">{a.reason_for_visit ?? '—'}</td>
                      <td className="px-6 py-4.5 text-xs text-slate-650">
                        <div className="flex flex-col gap-0.5">
                          <span className="font-bold text-slate-800">{a.scheduled_date}</span>
                          <span className="text-[10px] text-slate-450 flex items-center gap-1 font-mono">
                            <Clock className="w-2.5 h-2.5" />
                            {a.scheduled_time}
                          </span>
                        </div>
                      </td>
                      <td className="px-6 py-4.5 text-xs text-slate-650">
                        {a.doctor_name ? (
                          <div className="flex items-center gap-1">
                            <Stethoscope className="w-3 h-3 text-slate-400" />
                            <span>{a.doctor_name}</span>
                          </div>
                        ) : '—'}
                      </td>
                      <td className="px-6 py-4.5">
                        <span className={`inline-flex items-center gap-1 px-2.5 py-0.75 rounded-full text-[10px] font-bold tracking-wide uppercase ${sc.bg} ${sc.text}`}>
                          <Icon className="w-2.5 h-2.5" />
                          {sc.label}
                        </span>
                      </td>
                      <td className="px-6 py-4.5 text-right">
                        {isBooked ? (
                          <button
                            onClick={() => handleCancel(a.id)}
                            className="inline-flex items-center gap-1 px-3 py-1 bg-rose-50 hover:bg-rose-100/80 text-rose-700 border border-rose-200 hover:border-rose-300 rounded text-[10px] font-bold transition-all duration-300 btn-3d"
                          >
                            <Ban className="w-3 h-3" />
                            Cancel Appointment
                          </button>
                        ) : (
                          <span className="text-[10px] text-slate-400 font-semibold italic">Non-modifiable</span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
