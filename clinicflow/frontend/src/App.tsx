import { useState } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import GlobalNav from './components/GlobalNav';
import TabBar from './components/TabBar';
import ChatInterface from './components/ChatInterface';
import LiveSessionMonitor from './components/LiveSessionMonitor';
import ClinicDashboard from './components/ClinicDashboard';
import HistoricalSessions from './components/HistoricalSessions';
import AppointmentsLedger from './components/AppointmentsLedger';
import AuditLogPanel from './components/AuditLogPanel';
import Login from './components/Login';

type TabKey = 'dashboard' | 'playground' | 'sessions' | 'appointments';

function DashboardContent() {
  const [token, setToken] = useState<string | null>(localStorage.getItem('auth_token'));
  const [activeTab, setActiveTab] = useState<TabKey>('dashboard');
  const [sessionData, setSessionData] = useState({
    sessionId: null as number | null,
    intent: 'unknown',
    collectedData: {} as Record<string, unknown>,
    workflowState: '—',
    status: 'idle',
  });

  return (
    <div className="min-h-screen text-slate-900 flex flex-col relative lg:overflow-hidden overflow-y-auto font-sans">
      {/* Pristine Clinical Ambient background glows */}
      <div className="absolute top-[-10%] left-[-10%] w-[50%] h-[50%] rounded-full bg-teal-200/15 blur-[120px] pointer-events-none" />
      <div className="absolute bottom-[-10%] right-[-10%] w-[50%] h-[50%] rounded-full bg-sky-200/15 blur-[120px] pointer-events-none" />

      <GlobalNav />

      {!token ? (
        <main className="flex-1 flex items-center justify-center p-6 relative z-10 animate-fadeIn">
          <Login onLoginSuccess={(tok) => {
            setToken(tok);
            window.location.reload();
          }} />
        </main>
      ) : (
        <>
          <TabBar activeTab={activeTab} onChange={setActiveTab} />

          <main 
            className="flex-1 p-6 max-w-[1440px] mx-auto w-full relative z-10 flex flex-col" 
            style={{ perspective: '1200px', transformStyle: 'preserve-3d' }}
          >
            {activeTab === 'dashboard' && <ClinicDashboard />}

            {activeTab === 'playground' && (
              <div 
                className="grid grid-cols-1 lg:grid-cols-3 gap-6 p-4 lg:p-8 h-auto lg:h-[calc(100vh-13rem)] animate-fadeIn"
                style={{ perspective: '1200px', transformStyle: 'preserve-3d' }}
              >
                <div className="h-[500px] lg:h-full min-h-0" style={{ transformStyle: 'preserve-3d' }}>
                  <ChatInterface onSessionUpdate={setSessionData} />
                </div>
                <div className="h-[350px] lg:h-full min-h-0" style={{ transformStyle: 'preserve-3d' }}>
                  <AuditLogPanel sessionId={sessionData.sessionId} />
                </div>
                <div className="h-[350px] lg:h-full min-h-0" style={{ transformStyle: 'preserve-3d' }}>
                  <LiveSessionMonitor
                    intent={sessionData.intent}
                    collectedData={sessionData.collectedData}
                    workflowState={sessionData.workflowState}
                    status={sessionData.status}
                  />
                </div>
              </div>
            )}

            {activeTab === 'sessions' && <HistoricalSessions />}
            {activeTab === 'appointments' && <AppointmentsLedger />}
          </main>
        </>
      )}
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/*" element={<DashboardContent />} />
      </Routes>
    </BrowserRouter>
  );
}
