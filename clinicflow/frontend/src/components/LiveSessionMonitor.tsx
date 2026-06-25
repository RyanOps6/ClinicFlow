import { Fingerprint, User, Phone, FileText, ClipboardList } from 'lucide-react';

interface Props {
  intent: string;
  collectedData: Record<string, unknown>;
  workflowState: string;
  status: string;
}

const intentColors: Record<string, { bg: string; text: string; label: string }> = {
  booking: { bg: 'bg-teal-50 border border-teal-200', text: 'text-teal-700', label: 'Booking' },
  reschedule: { bg: 'bg-amber-50 border border-amber-200', text: 'text-amber-700', label: 'Reschedule' },
  cancel: { bg: 'bg-rose-50 border border-rose-200', text: 'text-rose-700', label: 'Cancel' },
  unified: { bg: 'bg-teal-50 border border-teal-200', text: 'text-teal-700', label: 'Booking' },
  unknown: { bg: 'bg-slate-100 border border-slate-200', text: 'text-slate-650', label: 'Unknown' },
};

export default function LiveSessionMonitor({ intent, collectedData, workflowState, status }: Props) {
  const ic = intentColors[intent] || intentColors.unknown;

  const patientFields = [
    { label: 'Full Name', key: 'full_name', icon: User },
    { label: 'Phone Number', key: 'phone', icon: Phone },
    { label: 'Reason for Visit', key: 'reason_for_visit', icon: FileText },
    { label: 'Preferred Slot', key: 'preferred_slot_or_date', icon: ClipboardList },
  ];

  return (
    <div className="flex flex-col h-full clinic-card-3d rounded-xl overflow-hidden text-slate-800">
      <div className="px-5 py-3.5 border-b border-slate-200 bg-slate-50">
        <h3 className="text-sm font-bold text-slate-700 flex items-center gap-2">
          <Fingerprint className="w-4 h-4 text-teal-600 animate-pulse" />
          Live Session Monitor
        </h3>
      </div>

      <div className="p-5 space-y-5 flex-1 overflow-y-auto scrollbar-thin">
        {/* Intent Status Badge */}
        <div className="bg-slate-50 rounded-lg p-4 border border-slate-200">
          <p className="text-[10px] font-bold text-slate-500 uppercase tracking-wider mb-2">Active Intent</p>
          <span className={`inline-flex items-center px-3 py-1.5 rounded-full text-xs font-bold transition-all duration-300 ease-in-out ${ic.bg} ${ic.text}`}>
            {ic.label}
          </span>
          <p className="text-xs text-slate-600 mt-3.5 flex items-center gap-1">
            State: <span className="font-bold text-slate-800 transition-all duration-300 ease-in-out">{workflowState}</span>
          </p>
          <p className="text-xs text-slate-600 flex items-center gap-1">
            Status: <span className={`font-bold transition-all duration-300 ease-in-out ${status === 'completed' ? 'text-emerald-600' : status === 'active' ? 'text-teal-600' : 'text-slate-500'}`}>{status}</span>
          </p>
        </div>

        {/* Patient Profile Matrix */}
        <div>
          <p className="text-[10px] font-bold text-slate-500 uppercase tracking-wider mb-3">Patient Profile Matrix</p>
          <div className="bg-slate-50/50 rounded-lg border border-slate-200 overflow-hidden">
            <table className="w-full">
              <tbody>
                {patientFields.map(({ label, key, icon: Icon }) => {
                  const value = collectedData?.[key];
                  return (
                    <tr key={key} className="border-b border-slate-200 last:border-b-0">
                       <td className="px-4 py-3 w-40">
                        <div className="flex items-center gap-2 text-slate-500">
                          <Icon className="w-3.5 h-3.5" />
                          <span className="text-xs font-semibold">{label}</span>
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        {value ? (
                          <span className="text-sm text-slate-800 font-bold transition-all duration-300 ease-in-out">{String(value)}</span>
                        ) : (
                          <span className="text-xs italic text-slate-400 transition-all duration-300 ease-in-out">Awaiting input...</span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>

        {/* Raw Collected Data */}
        {Object.keys(collectedData || {}).length > 0 && (
          <div>
            <p className="text-[10px] font-bold text-slate-500 uppercase tracking-wider mb-3">Raw Data</p>
            <div className="bg-white border border-slate-200 rounded-lg p-3 overflow-x-auto scrollbar-thin">
              <pre className="text-xs text-teal-700 font-mono leading-normal">
                {JSON.stringify(collectedData, null, 2)}
              </pre>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
