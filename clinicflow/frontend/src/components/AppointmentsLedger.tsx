import { useEffect, useState, useCallback } from 'react';
import { Calendar, User, Stethoscope, Clock, CheckCircle2, XCircle } from 'lucide-react';
import type { AppointmentResponse } from '../types';
import { getAppointments } from '../api/client';

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

  const statusConfig: Record<string, { label: string; bg: string; text: string; icon: React.ElementType }> = {
    booked: { label: 'Upcoming', bg: 'bg-medical-50', text: 'text-medical-700', icon: CheckCircle2 },
    rescheduled: { label: 'Rescheduled', bg: 'bg-amber-50', text: 'text-amber-700', icon: Clock },
    cancelled: { label: 'Cancelled', bg: 'bg-red-50', text: 'text-red-700', icon: XCircle },
    completed: { label: 'Completed', bg: 'bg-emerald-50', text: 'text-emerald-700', icon: CheckCircle2 },
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-slate-700 flex items-center gap-2">
          <Calendar className="w-4 h-4 text-medical-500" />
          Appointments Ledger
        </h3>
        <span className="text-xs text-slate-400">{appointments.length} total</span>
      </div>

      {loading ? (
        <div className="p-8 text-center text-slate-400 text-sm">Loading appointments...</div>
      ) : appointments.length === 0 ? (
        <div className="bg-white rounded-xl border border-slate-200 p-8 text-center text-slate-400 text-sm shadow-sm">
          No appointments found. Start a booking session to create one.
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-4">
          {appointments.map((a) => {
            const sc = statusConfig[a.status] || { label: a.status, bg: 'bg-slate-50', text: 'text-slate-600', icon: Clock };
            const Icon = sc.icon;
            return (
              <div key={a.id} className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden hover:shadow-md transition-shadow">
                <div className="px-5 py-3.5 border-b border-slate-100 flex items-center justify-between bg-slate-50">
                  <div className="flex items-center gap-2">
                    <Calendar className="w-4 h-4 text-slate-400" />
                    <span className="text-sm font-semibold text-slate-700">{a.scheduled_date}</span>
                  </div>
                  <span className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium ${sc.bg} ${sc.text}`}>
                    <Icon className="w-3 h-3" />
                    {sc.label}
                  </span>
                </div>
                <div className="p-5 space-y-3">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 bg-medical-50 rounded-full flex items-center justify-center flex-shrink-0">
                      <User className="w-5 h-5 text-medical-600" />
                    </div>
                    <div>
                      <p className="text-sm font-semibold text-slate-800">{a.patient_name ?? 'Unknown Patient'}</p>
                      <p className="text-xs text-slate-500">{a.reason_for_visit}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-4 pt-2 border-t border-slate-50">
                    <div className="flex items-center gap-1.5 text-sm text-slate-600">
                      <Clock className="w-3.5 h-3.5 text-slate-400" />
                      <span>{a.scheduled_time}</span>
                    </div>
                    {a.doctor_name && (
                      <div className="flex items-center gap-1.5 text-sm text-slate-600">
                        <Stethoscope className="w-3.5 h-3.5 text-slate-400" />
                        <span>{a.doctor_name}</span>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
