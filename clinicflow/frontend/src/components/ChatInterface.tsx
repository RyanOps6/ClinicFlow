import { useState, useRef, useCallback, useEffect } from 'react';
import { Send, RotateCcw, User, Bot, PhoneCall, CalendarPlus, CalendarX, Mic, MicOff } from 'lucide-react';
import type { SendMessageResponse } from '../types';
import { sendMessage, startRescheduleSession, startCancelSession, startSession } from '../api/client';
import AiOrb from './AiOrb';

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
  const [devWsInput, setDevWsInput] = useState('');
  const [isAiActive, setIsAiActive] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const recognitionRef = useRef<any>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => { scrollToBottom(); }, [messages]);

  const endVoiceCall = useCallback(() => {
    setIsCallActive(false);
    setIsAiActive(false);
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
    const wsBase = import.meta.env.PROD
      ? 'wss://clinicflow-backend-h4w4.onrender.com'
      : `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}`;
    const wsUrl = `${wsBase}/api/sessions/ws/${sessionId}`;
    
    let ws: WebSocket;
    try {
      ws = new WebSocket(wsUrl);
    } catch (e: any) {
      const errStr = e?.message || String(e);
      console.error(`WebSocket creation failed for URL ${wsUrl}:`, e);
      console.error(`CONNECTION_ERROR: ${errStr}`);
      alert("Failed to establish WebSocket connection.");
      return;
    }
    
    wsRef.current = ws;
    
    ws.onopen = () => {
      console.log("WebSocket connection established successfully on:", wsUrl);
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
          setIsAiActive(true);
          const audioUrl = `data:audio/wav;base64,${data.audio}`;
          if (audioRef.current) {
            audioRef.current.pause();
          }
          const audio = new Audio(audioUrl);
          audio.onended = () => setIsAiActive(false);
          audioRef.current = audio;
          audio.play().catch(err => {
            console.error("Audio play failed:", err);
            setIsAiActive(false);
          });
        }
      } catch (err) {
        console.error("WebSocket message parse error:", err);
      }
    };
    
    const handleWsClose = (event: CloseEvent) => {
      console.log(`WebSocket closed. code=${event.code}, reason=${event.reason || 'none'}, clean=${event.wasClean}`);
      if (!event.wasClean) {
        console.error(`CONNECTION_ERROR: WebSocket premature disconnect or abnormal closure. Code: ${event.code}, Reason: ${event.reason || 'none'}`);
      }
      setIsCallActive(false);
    };
    
    const handleWsError = (err: any) => {
      console.error("WebSocket connection error occurred:", err);
      const errStr = err?.message || (err instanceof Event ? "WebSocket error event triggered" : String(err));
      console.error(`CONNECTION_ERROR: ${errStr}`);
    };
    
    ws.onclose = handleWsClose;
    (ws as any).onClose = handleWsClose;
    ws.addEventListener('close', handleWsClose);
    
    ws.onerror = handleWsError;
    (ws as any).onError = handleWsError;
    ws.addEventListener('error', handleWsError);
    
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SpeechRecognition) {
      alert("Speech recognition API is not supported in this browser. Please use Chrome or Edge.");
      return;
    }
    
    const recognition = new SpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = false;
    recognition.lang = 'en-US';
    
    const handleSpeechStart = () => {
      console.log("Speech recognition service started (listening to microphone)...");
    };
    
    recognition.onstart = handleSpeechStart;
    (recognition as any).onStart = handleSpeechStart;
    recognition.addEventListener('start', handleSpeechStart);
    
    recognition.onresult = (event: any) => {
      const resultText = event.results[event.results.length - 1][0].transcript.trim();
      console.log(`Speech recognition result captured: "${resultText}"`);
      if (resultText && ws.readyState === WebSocket.OPEN) {
        setMessages(prev => [...prev, { role: 'user', content: resultText }]);
        const encoder = new TextEncoder();
        const dataBytes = encoder.encode(resultText);
        console.log("Streaming transcribed text bytes to backend...");
        ws.send(dataBytes);
      } else {
        console.warn("Speech captured, but WebSocket is not open. State:", ws.readyState);
      }
    };
    
    const handleSpeechError = (event: any) => {
      const errorMsg = event.error;
      console.error("Speech recognition error occurred:", errorMsg, event.message || "");
      if (errorMsg === 'not-allowed') {
        console.error("MICROPHONE_DENIED: Microphone access denied by user or system policy. Error code: not-allowed");
      } else {
        console.error(`SPEECH_RECOGNITION_ERROR: ${errorMsg}`);
      }
    };
    
    recognition.onerror = handleSpeechError;
    (recognition as any).onError = handleSpeechError;
    recognition.addEventListener('error', handleSpeechError);
    
    const handleSpeechEnd = () => {
      console.log("Speech recognition service stopped.");
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        console.log("Re-initiating speech recognition listener...");
        try {
          recognition.start();
        } catch (e) {
          console.error("Failed to restart speech recognition:", e);
        }
      }
    };
    
    recognition.onend = handleSpeechEnd;
    (recognition as any).onEnd = handleSpeechEnd;
    recognition.addEventListener('end', handleSpeechEnd);
    
    recognitionRef.current = recognition;
    try {
      recognition.start();
    } catch (e: any) {
      console.error("Failed to start speech recognition initial stream:", e);
      console.error(`SPEECH_RECOGNITION_START_ERROR: ${e?.message || String(e)}`);
    }
    
  }, [sessionId, onSessionUpdate, intent, collectedData, endVoiceCall]);

  const toggleVoiceCall = useCallback(() => {
    if (isCallActive) {
      endVoiceCall();
    } else {
      startVoiceCall();
    }
  }, [isCallActive, startVoiceCall, endVoiceCall]);

  const handleSendDevWs = useCallback(() => {
    if (!devWsInput.trim() || !wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      return;
    }
    const msg = devWsInput.trim();
    setDevWsInput('');
    setMessages(prev => [...prev, { role: 'user', content: msg }]);
    const encoder = new TextEncoder();
    const dataBytes = encoder.encode(msg);
    console.log("Streaming dev mock text bytes to backend...");
    wsRef.current.send(dataBytes);
  }, [devWsInput]);

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
    setDevWsInput('');
    setStatus('idle');
    setIntent('unknown');
    setCollectedData({});
    setWorkflowState('—');
    onSessionUpdate?.({ sessionId: null, intent: 'unknown', collectedData: {}, workflowState: '—', status: 'idle' });
  }, [onSessionUpdate, endVoiceCall]);

  const sessionTypes: { key: string; label: string; icon: React.ElementType; style: string }[] = [
    { key: 'unified', label: 'Simulate Unified Call', icon: PhoneCall, style: 'from-teal-50 to-indigo-50 border-teal-200 text-teal-750 hover:bg-teal-100/50' },
    { key: 'booking', label: 'Test Booking Flow', icon: CalendarPlus, style: 'from-slate-50 to-slate-100 border-slate-200 text-slate-700 hover:bg-slate-100/50' },
    { key: 'cancel', label: 'Test Cancellation Flow', icon: CalendarX, style: 'from-rose-50 to-red-50 border-rose-200 text-rose-700 hover:bg-rose-100/50' },
  ];

  return (
    <div className="flex flex-col h-full clinic-card-3d rounded-xl overflow-hidden text-slate-800">
      <div className="px-5 py-3 border-b border-slate-200 flex items-center justify-between bg-slate-50">
        <h3 className="text-sm font-semibold text-slate-700 flex items-center gap-2">
          {/* Obsidian Glass Badge containing the 3D AI Orb */}
          <div className="bg-slate-950/90 border border-slate-800 shadow-md p-1 pr-2.5 backdrop-blur-md rounded-lg flex items-center gap-2 select-none">
            <AiOrb isSpeaking={isAiActive} isProcessing={loading} />
            <span className="text-[10px] font-bold tracking-wider bg-gradient-to-r from-teal-400 via-indigo-300 to-sky-300 bg-clip-text text-transparent uppercase">
              Ava AI
            </span>
          </div>
          <span className="text-slate-350 font-light select-none">|</span>
          <span className="text-slate-600 font-bold">Receptionist Playground</span>
        </h3>
        {status !== 'idle' && (
          <div className="flex items-center gap-3">
            <button
              onClick={toggleVoiceCall}
              disabled={status === 'completed'}
              className={`flex items-center gap-1.5 px-3 py-1.25 rounded-full border text-[11px] font-semibold transition-all duration-200 btn-3d ${
                isCallActive
                  ? 'bg-rose-50 text-rose-700 border-rose-200 hover:bg-rose-100/80'
                  : 'bg-teal-50 text-teal-700 border-teal-200 hover:bg-teal-100/80'
              } disabled:opacity-50`}
            >
              {isCallActive ? <MicOff className="w-3 h-3 text-rose-600" /> : <Mic className="w-3 h-3 text-teal-650" />}
              {isCallActive ? 'End Call' : 'Voice Call'}
            </button>
            <button onClick={handleReset} className="flex items-center gap-1 text-xs text-slate-500 hover:text-rose-600 transition-colors">
              <RotateCcw className="w-3 h-3" /> Reset Simulator
            </button>
          </div>
        )}
      </div>

      {status !== 'idle' && (
        <div className="px-5 py-2 border-b border-amber-200 bg-amber-50/50 flex flex-wrap items-center gap-2">
          <span className="text-[10px] font-bold text-amber-700 tracking-wider uppercase">Dev WS Test:</span>
          <input
            type="text"
            value={devWsInput}
            onChange={e => setDevWsInput(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleSendDevWs()}
            disabled={!isCallActive || status === 'completed'}
            placeholder={
              status === 'completed'
                ? "Session completed."
                : isCallActive
                ? "Type mock patient phrase (e.g. My name is Aryan)..."
                : "Voice Call must be active to send text via WS..."
            }
            className="flex-1 min-w-[200px] px-2.5 py-1 text-xs border border-slate-200 rounded bg-white text-slate-800 focus:outline-none focus:ring-1 focus:ring-amber-500/40 focus:border-amber-500/60 disabled:bg-slate-100 disabled:border-slate-200 disabled:text-slate-400 transition-all font-mono"
          />
          <button
            onClick={handleSendDevWs}
            disabled={!isCallActive || !devWsInput.trim() || status === 'completed'}
            className="px-3 py-1 bg-amber-600 hover:bg-amber-700 text-white rounded text-xs font-semibold transition-colors disabled:opacity-50 disabled:cursor-not-allowed btn-3d"
          >
            Send text via WebSocket
          </button>
        </div>
      )}

      {status === 'idle' ? (
        <div className="flex-1 flex flex-col items-center justify-center p-8 gap-5">
          <div className="w-16 h-16 bg-teal-50 border border-teal-200 rounded-2xl flex items-center justify-center mb-1 animate-pulse">
            <Bot className="w-8 h-8 text-teal-600" />
          </div>
          <div className="text-center">
            <h4 className="text-base font-bold text-slate-850">Select a session type...</h4>
            <p className="text-xs text-slate-500 mt-1 max-w-xs mx-auto">
              Choose a workflow to simulate patient interactions with the AI assistant.
            </p>
          </div>
          <div className="flex flex-col sm:flex-row flex-wrap gap-3 mt-2 w-full max-w-lg justify-center">
            {sessionTypes.map(({ key, label, icon: Icon, style }) => (
              <button
                key={key}
                onClick={() => handleStart(key)}
                disabled={loading}
                className={`flex items-center justify-center gap-2 px-5 py-2.5 rounded-full border text-xs font-bold bg-gradient-to-br transition-all duration-300 btn-3d ${style} disabled:opacity-50`}
              >
                <Icon className="w-4 h-4" /> {label}
              </button>
            ))}
          </div>
        </div>
      ) : (
        <>
          <div className="flex-1 overflow-y-auto p-4 space-y-3 scrollbar-thin">
            {messages.map((m, i) => (
              <div key={i} className={`flex gap-3 ${m.role === 'user' ? 'flex-row-reverse' : ''}`}>
                <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 border ${
                  m.role === 'user'
                    ? 'bg-slate-100 border-slate-200'
                    : 'bg-teal-50 border-teal-200'
                }`}>
                  {m.role === 'user' ? <User className="w-4 h-4 text-slate-500" /> : <Bot className="w-4 h-4 text-teal-600" />}
                </div>
                <div className={`max-w-[80%] px-4 py-2.5 rounded-2xl text-xs leading-relaxed border ${
                  m.role === 'user'
                    ? 'bg-slate-50 border-slate-200 text-slate-800 rounded-br-md'
                    : 'bg-teal-50/50 border-teal-100/80 text-slate-850 rounded-bl-md'
                }`}>
                  {m.content}
                </div>
              </div>
            ))}
            {loading && (
              <div className="flex gap-3">
                <div className="w-8 h-8 rounded-full bg-teal-50 border border-teal-200 flex items-center justify-center flex-shrink-0">
                  <Bot className="w-4 h-4 text-teal-600 animate-pulse" />
                </div>
                <div className="px-4 py-2.5 bg-teal-50/50 border border-teal-100/80 rounded-2xl rounded-bl-md">
                  <div className="flex gap-1">
                    <span className="w-1.5 h-1.5 bg-teal-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                    <span className="w-1.5 h-1.5 bg-teal-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                    <span className="w-1.5 h-1.5 bg-teal-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          <div className="p-4 border-t border-slate-200 bg-slate-50">
            <div className="flex gap-2">
              <input
                ref={inputRef}
                type="text"
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && handleSend()}
                disabled={loading || status === 'completed'}
                placeholder={status === 'completed' ? 'Session completed.' : "Type patient's spoken words here..."}
                className="flex-1 px-4 py-2.5 border border-slate-200 bg-white text-slate-800 rounded-lg text-xs focus:outline-none focus:ring-2 focus:ring-teal-500/20 focus:border-teal-500 transition-all placeholder-slate-400"
              />
              <button
                onClick={handleSend}
                disabled={loading || !input.trim() || status === 'completed'}
                className="px-5 py-2.5 bg-teal-600 hover:bg-teal-700 text-white rounded-lg text-xs font-semibold disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-1.5 btn-3d"
              >
                <Send className="w-3.5 h-3.5" /> Send
              </button>
            </div>
            <div className="mt-2.5 flex justify-end">
              <button onClick={handleReset} className="text-[10px] text-slate-400 hover:text-rose-600 transition-colors">
                Reset Simulator
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
