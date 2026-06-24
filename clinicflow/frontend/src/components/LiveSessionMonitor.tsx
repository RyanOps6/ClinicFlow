import { Fingerprint, User, Phone, FileText, ClipboardList } from 'lucide-react';

interface Props {
  intent: string;
  collectedData: Record<string, unknown>;
  workflowState: string;
  status: string;
}

const intentColors: Record<string, { bg: string; text: string; label: string }> = {
  booking: { bg: 'bg-teal-50', text: 'text-teal-700', label: 'Booking' },
  reschedule: { bg: 'bg-amber-50', text: 'text-amber-700', label: 'Reschedule' },
  cancel: { bg: 'bg-red-50', text: 'text-red-700', label: 'Cancel' },
  unified: { bg: 'bg-teal-50', text: 'text-teal-700', label: 'Booking' },
  unknown: { bg: 'bg-slate-50', text: 'text-slate-600', label: 'Unknown' },
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
    <div className="flex flex-col h-full bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
      <div className="px-5 py-3 border-b border-slate-100 bg-slate-50">
        <h3 className="text-sm font-semibold text-slate-700 flex items-center gap-2">
          <Fingerprint className="w-4 h-4 text-medical-500" />
          Live Session Monitor
        </h3>
      </div>

      <div className="p-5 space-y-5">
        {/* Intent Status Badge */}
        <div className="bg-slate-50 rounded-lg p-4 border border-slate-100">
          <p className="text-xs font-medium text-slate-400 uppercase tracking-wider mb-2">Active Intent</p>
          <span className={`inline-flex items-center px-3 py-1.5 rounded-full text-sm font-semibold ${ic.bg} ${ic.text}`}>
            {ic.label}
          </span>
  <p className="text-xs text-slate-400 mt-2 flex items-center gap-1">
            State: <span className="font-medium text-slate-600">{workflowState}</span>
          </p>
          <p className="text-xs text-slate-400 flex items-center gap-1">
            Status: <span className={`font-medium ${status === 'completed' ? 'text-emerald-600' : status === 'active' ? 'text-medical-600' : 'text-slate-600'}`}>{status}</span>
          </p>
        </div>

        {/* Patient Profile Matrix */}
        <div>
          <p className="text-xs font-medium text-slate-400 uppercase tracking-wider mb-3">Patient Profile Matrix</p>
          <div className="bg-slate-50 rounded-lg border border-slate-100 overflow-hidden">
            <table className="w-full">
              <tbody>
                {patientFields.map(({ label, key, icon: Icon }) => {
                  const value = collectedData?.[key];
                  return (
                    <tr key={key} className="border-b border-slate-100 last:border-b-0">
                      <td className="px-4 py-3 w-40">
                        <div className="flex items-center gap-2 text-slate-500">
                          <Icon className="w-3.5 h-3.5" />
                          <span className="text-xs font-medium">{label}</span>
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        {value ? (
                          <span className="text-sm text-slate-700 font-medium">{String(value)}</span>
                        ) : (
                          <span className="text-sm italic text-slate-400">Awaiting input...</span>
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
            <p className="text-xs font-medium text-slate-400 uppercase tracking-wider mb-3">Raw Data</p>
            <div className="bg-slate-900 rounded-lg p-3 overflow-x-auto">
              <pre className="text-xs text-emerald-400 font-mono">
                {JSON.stringify(collectedData, null, 2)}
              </pre>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
