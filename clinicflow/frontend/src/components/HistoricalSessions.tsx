import { useEffect, useState, useCallback } from 'react';
import { History, Clock, User, Bot, Play, Terminal, ChevronRight, MessageSquare, Clipboard } from 'lucide-react';
import { getSessions, getSessionMessages, getSessionAuditLogs } from '../api/client';
import type { SessionSnapshot } from '../types';

interface MessageEntry {
  role: string;
  content: string;
}

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

export default function HistoricalSessions() {
  const [sessions, setSessions] = useState<SessionSnapshot[]>([]);
  const [selectedSessionId, setSelectedSessionId] = useState<number | null>(null);
  const [messages, setMessages] = useState<MessageEntry[]>([]);
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([]);
  const [loadingList, setLoadingList] = useState(true);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [activeRightTab, setActiveRightTab] = useState<'transcript' | 'ledger'>('transcript');
  const [expandedLogId, setExpandedLogId] = useState<number | null>(null);

  const fetchSessions = useCallback(async () => {
    setLoadingList(true);
    try {
      const data = await getSessions(1, 50);
      setSessions(data);
    } catch (err) {
      console.error('Failed to load past sessions:', err);
    } finally {
      setLoadingList(false);
    }
  }, []);

  useEffect(() => {
    fetchSessions();
  }, [fetchSessions]);

  const selectSession = useCallback(async (id: number) => {
    setSelectedSessionId(id);
    setLoadingDetail(true);
    setExpandedLogId(null);
    try {
      const [msgRes, logRes] = await Promise.all([
        getSessionMessages(id),
        getSessionAuditLogs(id),
      ]);
      setMessages(msgRes);
      setAuditLogs(logRes);
    } catch (err) {
      console.error('Failed to fetch session detail:', err);
    } finally {
      setLoadingDetail(false);
    }
  }, []);

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 h-[calc(100vh-12rem)] relative z-10 animate-fadeIn">
      {/* Left Column: Sessions List */}
      <div className="lg:col-span-4 clinic-card-3d rounded-2xl flex flex-col overflow-hidden h-full">
        <div className="px-5 py-4 border-b border-slate-200 bg-slate-50 flex items-center gap-2">
          <History className="w-4 h-4 text-teal-600" />
          <h3 className="text-sm font-bold text-slate-700 uppercase tracking-wider">Past Call Sessions</h3>
        </div>

        <div className="flex-1 overflow-y-auto p-4 space-y-3.5 scrollbar-thin">
          {loadingList ? (
            <div className="py-8 text-center text-slate-450 text-xs font-mono">Loading sessions...</div>
          ) : sessions.length === 0 ? (
            <div className="py-8 text-center text-slate-450 text-xs italic">No session logs found in database.</div>
          ) : (
            sessions.map((s) => {
              const isSelected = selectedSessionId === s.id;
              const patientName = s.collected_data?.full_name ? String(s.collected_data.full_name) : 'Anonymous Patient';
              return (
                <button
                  key={s.id}
                  onClick={() => selectSession(s.id)}
                  className={`w-full text-left p-4 rounded-xl border transition-all duration-300 btn-3d flex flex-col justify-between gap-2.5
                    ${
                      isSelected
                        ? 'bg-teal-50/50 border-teal-500/50 shadow-md shadow-teal-500/5'
                        : 'bg-white border-slate-200 hover:border-slate-350'
                    }`}
                >
                  <div className="flex items-center justify-between w-full">
                    <span className="text-[10px] font-bold font-mono text-slate-400">SESSION #{s.id}</span>
                    <span className={`px-2 py-0.5 rounded-full text-[9px] font-bold border uppercase tracking-wider
                      ${s.status === 'completed' ? 'bg-emerald-50 text-emerald-700 border-emerald-200' : 'bg-blue-50 text-blue-700 border-blue-200'}
                    `}>
                      {s.status}
                    </span>
                  </div>

                  <div>
                    <h4 className="text-xs font-bold text-slate-800">{patientName}</h4>
                    <p className="text-[10px] text-slate-500 mt-0.5 capitalize">Workflow state: {s.workflow_state || 'greeting'}</p>
                  </div>

                  <div className="flex items-center justify-between mt-1 text-[10px] text-slate-400 border-t border-slate-100 pt-2 w-full">
                    <span className="capitalize">{s.session_type} ({s.channel})</span>
                    <span className="font-mono">{s.created_at ? new Date(s.created_at).toLocaleDateString() : ''}</span>
                  </div>
                </button>
              );
            })
          )}
        </div>
      </div>

      {/* Right Column: Historical Inspectors */}
      <div className="lg:col-span-8 clinic-card-3d rounded-2xl flex flex-col overflow-hidden h-full">
        {!selectedSessionId ? (
          <div className="flex-1 flex flex-col items-center justify-center text-slate-500 p-8 text-center gap-2.5">
            <div className="w-12 h-12 bg-slate-50 border border-slate-200 rounded-2xl flex items-center justify-center mb-1">
              <Clipboard className="w-6 h-6 text-slate-400" />
            </div>
            <h4 className="text-sm font-bold text-slate-800">Retrospective Inspector</h4>
            <p className="text-xs text-slate-500 max-w-sm">Select a historical call session from the left sidebar to audit transcripts and extraction logs.</p>
          </div>
        ) : loadingDetail ? (
          <div className="flex-1 flex flex-col items-center justify-center text-slate-500 p-8 font-mono text-xs">
            Loading session ledger data...
          </div>
        ) : (
          <>
            {/* Tab switch header */}
            <div className="px-5 py-3 border-b border-slate-200 bg-slate-50 flex items-center justify-between">
              <div className="flex gap-2">
                <button
                  onClick={() => setActiveRightTab('transcript')}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold uppercase tracking-wider transition-all duration-200 border
                    ${
                      activeRightTab === 'transcript'
                        ? 'bg-teal-50 border-teal-200 text-teal-700'
                        : 'bg-slate-50 border-slate-200 text-slate-500 hover:text-slate-700'
                    }`}
                >
                  <MessageSquare className="w-3.5 h-3.5" />
                  Transcript Log
                </button>
                <button
                  onClick={() => setActiveRightTab('ledger')}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold uppercase tracking-wider transition-all duration-200 border
                    ${
                      activeRightTab === 'ledger'
                        ? 'bg-teal-50 border-teal-200 text-teal-700'
                        : 'bg-slate-50 border-slate-200 text-slate-500 hover:text-slate-700'
                    }`}
                >
                  <Terminal className="w-3.5 h-3.5" />
                  State Transitions
                </button>
              </div>
              <span className="text-[10px] font-mono text-slate-450">AUDITING SESSION #{selectedSessionId}</span>
            </div>

            {/* Content view */}
            <div className="flex-1 overflow-y-auto p-5 scrollbar-thin">
              {activeRightTab === 'transcript' ? (
                <div className="space-y-4">
                  {messages.length === 0 ? (
                    <div className="text-center text-slate-500 text-xs italic py-12">No messages recorded for this session.</div>
                  ) : (
                    messages.map((m, idx) => (
                      <div key={idx} className={`flex gap-3.5 ${m.role === 'user' ? 'flex-row-reverse' : ''}`}>
                        <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 border ${
                          m.role === 'user' ? 'bg-slate-100 border-slate-200' : 'bg-teal-50 border-teal-250'
                        }`}>
                          {m.role === 'user' ? <User className="w-3.5 h-3.5 text-slate-500" /> : <Bot className="w-3.5 h-3.5 text-teal-600" />}
                        </div>
                        <div className={`max-w-[75%] px-4 py-2.5 rounded-2xl text-xs leading-relaxed border ${
                          m.role === 'user'
                            ? 'bg-slate-50 border-slate-200 text-slate-800 rounded-br-md'
                            : 'bg-teal-50/50 border-teal-100 text-slate-800 rounded-bl-md'
                        }`}>
                          {m.content}
                        </div>
                      </div>
                    ))
                  )}
                </div>
              ) : (
                <div className="space-y-4 font-mono text-xs">
                  {auditLogs.length === 0 ? (
                    <div className="text-center text-slate-500 text-xs italic py-12">No state log entries recorded.</div>
                  ) : (
                    auditLogs.map((log, idx) => {
                      const isExpanded = expandedLogId === log.id;
                      return (
                        <div key={log.id} className="border border-slate-200 rounded-lg bg-slate-50/30 overflow-hidden">
                          <div className="p-3 border-b border-slate-200 flex items-center justify-between bg-slate-100/50">
                            <span className="text-emerald-600 font-bold flex items-center gap-1.5">
                              <Play className="w-2.5 h-2.5 fill-emerald-600 text-emerald-600" />
                              Turn #{idx + 1}
                            </span>
                            <span className="text-slate-400 text-[10px]">
                              {log.created_at ? new Date(log.created_at).toLocaleTimeString() : ''}
                            </span>
                          </div>

                          <div className="p-3 space-y-2 text-[11px]">
                            <div>
                              <span className="text-slate-500">User Speech Input:</span>{' '}
                              <span className="text-slate-800 font-medium">"{log.user_text}"</span>
                            </div>
                            <div>
                              <span className="text-slate-500">Engine State Before:</span>{' '}
                              <span className="text-blue-600 font-semibold">{log.workflow_state_before || 'greeting'}</span>
                            </div>
                            <div>
                              <span className="text-slate-500">Result Action Event:</span>{' '}
                              <span className="text-amber-600 font-semibold">{log.final_action}</span>
                            </div>

                            {(log.llm_payload_sent || log.llm_raw_response) && (
                              <div className="mt-2.5 pt-2 border-t border-slate-200 space-y-2">
                                <button
                                  onClick={() => setExpandedLogId(isExpanded ? null : log.id)}
                                  className="flex items-center gap-1 text-slate-500 hover:text-slate-700 transition-colors w-full text-left font-bold text-[10px]"
                                >
                                  <span>{isExpanded ? '[-] HIDE RAW LLM METADATA' : '[+] SHOW RAW LLM METADATA'}</span>
                                </button>

                                {isExpanded && (
                                  <div className="space-y-3.5 pt-2 pl-2">
                                    {log.llm_payload_sent && (
                                      <div>
                                        <div className="text-slate-505 mb-1 text-[10px]">Orchestrator Payload:</div>
                                        <pre className="p-2 rounded bg-white text-slate-700 overflow-x-auto max-h-40 border border-slate-200 leading-normal whitespace-pre-wrap break-all scrollbar-thin text-[10px]">
                                          {typeof log.llm_payload_sent === 'string'
                                            ? log.llm_payload_sent
                                            : JSON.stringify(log.llm_payload_sent, null, 2)}
                                        </pre>
                                      </div>
                                    )}
                                    {log.llm_raw_response && (
                                      <div>
                                        <div className="text-slate-505 mb-1 text-[10px]">Raw LLM Output JSON:</div>
                                        <pre className="p-2 rounded bg-white text-emerald-700 overflow-x-auto max-h-40 border border-slate-200 leading-normal whitespace-pre-wrap break-all scrollbar-thin text-[10px]">
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
              )}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
