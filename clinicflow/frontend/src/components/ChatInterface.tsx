import { useState, useRef, useCallback, useEffect } from 'react';
import { Send, RotateCcw, User, Bot, PhoneCall, CalendarPlus, CalendarX, Mic, MicOff } from 'lucide-react';
import type { SendMessageResponse } from '../types';
import { sendMessage, startRescheduleSession, startCancelSession, startSession } from '../api/client';

interface Message {
  role: 'user' | 'assistant';
  content: string;
}

interface Props {
  onSessionUpdate?: (data: {
    sessionId: number | null;
    intent: string;
    collectedData: Record<string, unknown>;
    workflowState: string;
    status: string;
  }) => void;
}

export default function ChatInterface({ onSessionUpdate }: Props) {
  const [sessionId, setSessionId] = useState<number | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState<'idle' | 'active' | 'completed'>('idle');
  const [intent, setIntent] = useState('unknown');
  const [collectedData, setCollectedData] = useState<Record<string, unknown>>({});
  const [workflowState, setWorkflowState] = useState('—');
  const inputRef = useRef<HTMLInputElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Live voice refs and states
  const [isCallActive, setIsCallActive] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const recognitionRef = useRef<any>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => { scrollToBottom(); }, [messages]);

  const endVoiceCall = useCallback(() => {
    setIsCallActive(false);
    if (recognitionRef.current) {
      try {
        recognitionRef.current.onend = null;
        recognitionRef.current.stop();
      } catch (e) {}
      recognitionRef.current = null;
    }
    if (wsRef.current) {
      try {
        wsRef.current.close();
      } catch (e) {}
      wsRef.current = null;
    }
    if (audioRef.current) {
      try {
        audioRef.current.pause();
      } catch (e) {}
      audioRef.current = null;
    }
  }, []);

  const startVoiceCall = useCallback(() => {
    if (!sessionId) return;
    
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//localhost:8000/api/sessions/ws/${sessionId}`;
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;
    
    ws.onopen = () => {
      console.log("WebSocket connected");
      setIsCallActive(true);
    };
    
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        const reply = data.assistant_response;
        const userSpeech = data.transcription;
        
        if (userSpeech) {
          setMessages(prev => {
            const last = prev[prev.length - 1];
            if (last && last.role === 'user' && last.content === userSpeech) {
              return prev;
            }
            return [...prev, { role: 'user', content: userSpeech }];
          });
        }
        
        if (reply) {
          setMessages(prev => [...prev, { role: 'assistant', content: reply }]);
        }
        
        if (data.workflow_state) {
          setWorkflowState(data.workflow_state);
        }
        
        const newStatus = data.completed ? 'completed' : 'active';
        if (data.completed) {
          setStatus('completed');
          endVoiceCall();
        }
        
        onSessionUpdate?.({
          sessionId,
          intent: data.intent || intent,
          collectedData: data.collected_data || collectedData,
          workflowState: data.workflow_state,
          status: newStatus
        });
        
        if (data.audio) {
          const audioUrl = `data:audio/wav;base64,${data.audio}`;
          if (audioRef.current) {
            audioRef.current.pause();
          }
          const audio = new Audio(audioUrl);
          audioRef.current = audio;
          audio.play().catch(err => console.error("Audio play failed:", err));
        }
      } catch (err) {
        console.error("WebSocket message parse error:", err);
      }
    };
    
    ws.onclose = () => {
      setIsCallActive(false);
    };
    
    ws.onerror = (err) => {
      console.error("WebSocket error:", err);
    };
    
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SpeechRecognition) {
      alert("Speech recognition API is not supported in this browser. Please use Chrome or Edge.");
      return;
    }
    
    const recognition = new SpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = false;
    recognition.lang = 'en-US';
    
    recognition.onresult = (event: any) => {
      const resultText = event.results[event.results.length - 1][0].transcript.trim();
      if (resultText && ws.readyState === WebSocket.OPEN) {
        setMessages(prev => [...prev, { role: 'user', content: resultText }]);
        const encoder = new TextEncoder();
        const dataBytes = encoder.encode(resultText);
        ws.send(dataBytes);
      }
    };
    
    recognition.onend = () => {
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        try {
          recognition.start();
        } catch (e) {}
      }
    };
    
    recognitionRef.current = recognition;
    recognition.start();
    
  }, [sessionId, onSessionUpdate, intent, collectedData, endVoiceCall]);

  const toggleVoiceCall = useCallback(() => {
    if (isCallActive) {
      endVoiceCall();
    } else {
      startVoiceCall();
    }
  }, [isCallActive, startVoiceCall, endVoiceCall]);

  useEffect(() => {
    return () => {
      if (recognitionRef.current) {
        try { recognitionRef.current.onend = null; recognitionRef.current.stop(); } catch (e) {}
      }
      if (wsRef.current) {
        try { wsRef.current.close(); } catch (e) {}
      }
      if (audioRef.current) {
        try { audioRef.current.pause(); } catch (e) {}
      }
    };
  }, []);

  const handleStart = useCallback(async (type: string = 'unified') => {
    setLoading(true);
    try {
      let res;
      if (type === 'reschedule') res = await startRescheduleSession();
      else if (type === 'cancel') res = await startCancelSession();
      else res = await startSession(type);

      setSessionId(res.session_id);
      setMessages([{ role: 'assistant', content: res.assistant_message }]);
      setWorkflowState(res.workflow_state);
      setStatus('active');
      setIntent(type);
      setCollectedData(res.collected_data);
      onSessionUpdate?.({ sessionId: res.session_id, intent: type, collectedData: res.collected_data, workflowState: res.workflow_state, status: 'active' });
    } catch (err) {
      alert('Failed to start session: ' + (err as Error).message);
    } finally {
      setLoading(false);
      inputRef.current?.focus();
    }
  }, [onSessionUpdate]);

  const handleSend = useCallback(async () => {
    if (!input.trim() || !sessionId || loading) return;
    const msg = input.trim();
    setInput('');
    setLoading(true);
    setMessages(prev => [...prev, { role: 'user', content: msg }]);

    try {
      const res: SendMessageResponse = await sendMessage(sessionId, msg);
      setMessages(prev => [...prev, { role: 'assistant', content: res.assistant_message }]);
      setCollectedData(res.collected_data);
      setWorkflowState(res.workflow_state);
      setIntent(res.intent);

      const newStatus = res.completed ? 'completed' : 'active';
      if (res.completed) setStatus('completed');
      onSessionUpdate?.({ sessionId, intent: res.intent, collectedData: res.collected_data, workflowState: res.workflow_state, status: newStatus });
    } catch {
      setMessages(prev => [...prev, { role: 'assistant', content: 'Sorry, something went wrong. Please try again.' }]);
    } finally {
      setLoading(false);
    }
  }, [input, sessionId, loading, onSessionUpdate]);

  const handleReset = useCallback(() => {
    endVoiceCall();
    setSessionId(null);
    setMessages([]);
    setInput('');
    setStatus('idle');
    setIntent('unknown');
    setCollectedData({});
    setWorkflowState('—');
    onSessionUpdate?.({ sessionId: null, intent: 'unknown', collectedData: {}, workflowState: '—', status: 'idle' });
  }, [onSessionUpdate, endVoiceCall]);

  const sessionTypes: { key: string; label: string; icon: React.ElementType; style: string }[] = [
    { key: 'unified', label: 'Simulate Unified Call', icon: PhoneCall, style: 'bg-medical-50 text-medical-700 border-medical-200 hover:bg-medical-100' },
    { key: 'booking', label: 'Test Booking Flow', icon: CalendarPlus, style: 'bg-slate-50 text-slate-700 border-slate-200 hover:bg-slate-100' },
    { key: 'cancel', label: 'Test Cancellation Flow', icon: CalendarX, style: 'bg-red-50 text-red-700 border-red-200 hover:bg-red-100' },
  ];

  return (
    <div className="flex flex-col h-full bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
      <div className="px-5 py-3 border-b border-slate-100 flex items-center justify-between bg-slate-50">
        <h3 className="text-sm font-semibold text-slate-700 flex items-center gap-2">
          <PhoneCall className="w-4 h-4 text-medical-500" />
          Staff Test Playground
        </h3>
        {status !== 'idle' && (
          <div className="flex items-center gap-3">
            <button
              onClick={toggleVoiceCall}
              disabled={status === 'completed'}
              className={`flex items-center gap-1 px-2.5 py-1.25 rounded-full border text-[11px] font-semibold transition-all duration-200 ${
                isCallActive
                  ? 'bg-red-50 text-red-600 border-red-200 hover:bg-red-100'
                  : 'bg-emerald-50 text-emerald-600 border-emerald-200 hover:bg-emerald-100'
              } disabled:opacity-50`}
            >
              {isCallActive ? <MicOff className="w-3 h-3 text-red-500" /> : <Mic className="w-3 h-3 text-emerald-500" />}
              {isCallActive ? 'End Call' : 'Voice Call'}
            </button>
            <button onClick={handleReset} className="flex items-center gap-1 text-xs text-slate-500 hover:text-red-500 transition-colors">
              <RotateCcw className="w-3 h-3" /> Reset Simulator
            </button>
          </div>
        )}
      </div>

      {status === 'idle' ? (
        <div className="flex-1 flex flex-col items-center justify-center p-8 gap-5">
          <div className="w-16 h-16 bg-medical-50 rounded-2xl flex items-center justify-center mb-1">
            <Bot className="w-8 h-8 text-medical-500" />
          </div>
          <h4 className="text-lg font-semibold text-slate-800">Select a session type...</h4>
          <p className="text-sm text-slate-400 text-center max-w-sm">
            Choose a workflow to simulate patient interactions with the AI assistant.
          </p>
          <div className="flex flex-col sm:flex-row flex-wrap gap-3 mt-2 w-full max-w-lg justify-center">
            {sessionTypes.map(({ key, label, icon: Icon, style }) => (
              <button
                key={key}
                onClick={() => handleStart(key)}
                disabled={loading}
                className={`flex items-center justify-center gap-2 px-5 py-2.5 rounded-full border text-sm font-medium transition-all duration-200 ${style} disabled:opacity-50`}
              >
                <Icon className="w-4 h-4" /> {label}
              </button>
            ))}
          </div>
        </div>
      ) : (
        <>
          <div className="flex-1 overflow-y-auto p-4 space-y-3">
            {messages.map((m, i) => (
              <div key={i} className={`flex gap-3 ${m.role === 'user' ? 'flex-row-reverse' : ''}`}>
                <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${m.role === 'user' ? 'bg-slate-200' : 'bg-medical-100'}`}>
                  {m.role === 'user' ? <User className="w-4 h-4 text-slate-600" /> : <Bot className="w-4 h-4 text-medical-600" />}
                </div>
                <div className={`max-w-[80%] px-4 py-2.5 rounded-2xl text-sm leading-relaxed ${m.role === 'user' ? 'bg-slate-100 text-slate-800 rounded-br-md' : 'bg-medical-50 text-slate-800 rounded-bl-md'}`}>
                  {m.content}
                </div>
              </div>
            ))}
            {loading && (
              <div className="flex gap-3">
                <div className="w-8 h-8 rounded-full bg-medical-100 flex items-center justify-center flex-shrink-0">
                  <Bot className="w-4 h-4 text-medical-400 animate-pulse" />
                </div>
                <div className="px-4 py-2.5 bg-medical-50 rounded-2xl rounded-bl-md">
                  <div className="flex gap-1">
                    <span className="w-2 h-2 bg-medical-300 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                    <span className="w-2 h-2 bg-medical-300 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                    <span className="w-2 h-2 bg-medical-300 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          <div className="p-4 border-t border-slate-100 bg-white">
            <div className="flex gap-2">
              <input
                ref={inputRef}
                type="text"
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && handleSend()}
                disabled={loading || status === 'completed'}
                placeholder={status === 'completed' ? 'Session completed.' : "Type patient's spoken words here..."}
                className="flex-1 px-4 py-2.5 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-medical-200 focus:border-medical-500 transition-all"
              />
              <button
                onClick={handleSend}
                disabled={loading || !input.trim() || status === 'completed'}
                className="px-5 py-2.5 bg-medical-600 text-white rounded-lg text-sm font-medium hover:bg-medical-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-1.5"
              >
                <Send className="w-4 h-4" /> Send
              </button>
            </div>
            <div className="mt-2 flex justify-end">
              <button onClick={handleReset} className="text-xs text-slate-400 hover:text-red-500 transition-colors">
                Reset Simulator
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
