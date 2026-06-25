import { useEffect, useState } from 'react';
import { Terminal, ChevronDown, ChevronRight, Play } from 'lucide-react';
import { getSessionAuditLogs } from '../api/client';

interface AuditLog {
  id: number;
  session_id: number;
  user_text: string;
  workflow_state_before: string;
  llm_payload_sent: any;
  llm_raw_response: any;
  final_action: string;
  created_at: string;
}

interface Props {
  sessionId: number | null;
}

export default function AuditLogPanel({ sessionId }: Props) {
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [expandedLogs, setExpandedLogs] = useState<Record<number, boolean>>({});

  useEffect(() => {
    if (!sessionId) {
      setLogs([]);
      return;
    }

    const fetchLogs = async () => {
      try {
        const data = await getSessionAuditLogs(sessionId);
        setLogs(data);
      } catch (err) {
        console.error('Failed to fetch audit logs:', err);
      }
    };

    fetchLogs();
    const interval = setInterval(fetchLogs, 2000);
    return () => clearInterval(interval);
  }, [sessionId]);

  const toggleExpand = (id: number) => {
    setExpandedLogs(prev => ({ ...prev, [id]: !prev[id] }));
  };

  return (
    <div className="flex flex-col h-full clinic-card-3d rounded-xl overflow-hidden font-mono text-xs text-slate-700">
      <div className="px-5 py-3.5 border-b border-slate-200 flex items-center gap-2 bg-slate-50">
        <Terminal className="w-4 h-4 text-emerald-500 animate-pulse" />
        <span className="font-bold text-slate-700">Developer Audit Logs</span>
        {sessionId && <span className="text-[10px] text-slate-400 ml-auto">ID: {sessionId}</span>}
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4 scrollbar-thin">
        {!sessionId ? (
          <div className="h-full flex flex-col items-center justify-center text-slate-500 gap-2 text-center py-8">
            <BotPlaceholder />
            <div className="font-bold text-slate-500">No active session</div>
            <div className="text-[10px] text-slate-500 max-w-[200px]">Start a staff playground session to view raw LLM prompts and turn audits.</div>
          </div>
        ) : logs.length === 0 ? (
          <div className="h-full flex items-center justify-center text-slate-400 py-8">
            Awaiting conversation turn...
          </div>
        ) : (
          logs.map((log, idx) => {
            const isExpanded = !!expandedLogs[log.id];
            return (
              <div key={log.id} className="border border-slate-200 rounded-lg bg-slate-50/20 overflow-hidden">
                {/* Header info */}
                <div className="p-3 border-b border-slate-200 flex items-center justify-between bg-slate-100/50">
                  <span className="text-emerald-600 font-bold flex items-center gap-1">
                    <Play className="w-2.5 h-2.5 fill-emerald-600 text-emerald-600" />
                    Turn #{idx + 1}
                  </span>
                  <span className="text-slate-400 text-[10px]">
                    {log.created_at ? new Date(log.created_at).toLocaleTimeString() : ''}
                  </span>
                </div>

                <div className="p-3 space-y-2">
                  <div>
                    <span className="text-slate-500">User text:</span>{' '}
                    <span className="text-slate-800 font-medium">"{log.user_text}"</span>
                  </div>
                  <div>
                    <span className="text-slate-500">State before:</span>{' '}
                    <span className="text-blue-600 font-semibold">{log.workflow_state_before || 'greeting'}</span>
                  </div>
                  <div>
                    <span className="text-slate-500">Final Action:</span>{' '}
                    <span className="text-amber-600 font-semibold">{log.final_action}</span>
                  </div>

                  {/* LLM payload/response details */}
                  {(log.llm_payload_sent || log.llm_raw_response) && (
                    <div className="mt-2 pt-2 border-t border-slate-200 space-y-2">
                      <button
                        onClick={() => toggleExpand(log.id)}
                        className="flex items-center gap-1 text-slate-500 hover:text-slate-700 transition-colors w-full text-left font-bold"
                      >
                        {isExpanded ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
                        <span>LLM Extractor Details</span>
                      </button>

                      {isExpanded && (
                        <div className="space-y-3 pl-4 pt-1 text-[10px] animate-fadeIn">
                          {log.llm_payload_sent && (
                            <div>
                              <div className="text-slate-500 mb-1">Payload Sent:</div>
                              <pre className="p-2 rounded bg-white text-slate-700 overflow-x-auto max-h-40 border border-slate-200 leading-normal whitespace-pre-wrap break-all scrollbar-thin">
                                {typeof log.llm_payload_sent === 'string'
                                  ? log.llm_payload_sent
                                  : JSON.stringify(log.llm_payload_sent, null, 2)}
                              </pre>
                            </div>
                          )}
                          {log.llm_raw_response && (
                            <div>
                              <div className="text-slate-500 mb-1">Raw Response:</div>
                              <pre className="p-2 rounded bg-white text-emerald-700 overflow-x-auto max-h-40 border border-slate-200 leading-normal whitespace-pre-wrap break-all scrollbar-thin">
                                {typeof log.llm_raw_response === 'string'
                                  ? log.llm_raw_response
                                  : JSON.stringify(log.llm_raw_response, null, 2)}
                              </pre>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}

function BotPlaceholder() {
  return (
    <div className="w-10 h-10 bg-slate-100 border border-slate-200 rounded-xl flex items-center justify-center mb-1 text-slate-400">
      <Terminal className="w-5 h-5" />
    </div>
  );
}
