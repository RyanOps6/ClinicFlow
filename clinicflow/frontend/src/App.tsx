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

type TabKey = 'dashboard' | 'playground' | 'sessions' | 'appointments';

function DashboardContent() {
  const [activeTab, setActiveTab] = useState<TabKey>('dashboard');
  const [sessionData, setSessionData] = useState({
    sessionId: null as number | null,
    intent: 'unknown',
    collectedData: {} as Record<string, unknown>,
    workflowState: '—',
    status: 'idle',
  });

  return (
    <div className="min-h-screen text-slate-900 flex flex-col relative overflow-hidden font-sans">
      {/* Pristine Clinical Ambient background glows */}
      <div className="absolute top-[-10%] left-[-10%] w-[50%] h-[50%] rounded-full bg-teal-200/15 blur-[120px] pointer-events-none" />
      <div className="absolute bottom-[-10%] right-[-10%] w-[50%] h-[50%] rounded-full bg-sky-200/15 blur-[120px] pointer-events-none" />

      <GlobalNav />
      <TabBar activeTab={activeTab} onChange={setActiveTab} />

      <main 
        className="flex-1 p-6 max-w-[1440px] mx-auto w-full relative z-10 flex flex-col" 
        style={{ perspective: '1200px', transformStyle: 'preserve-3d' }}
      >
        {activeTab === 'dashboard' && <ClinicDashboard />}

        {activeTab === 'playground' && (
          <div 
            className="flex flex-col lg:flex-row gap-6 h-[calc(100vh-13rem)]"
            style={{ perspective: '1200px', transformStyle: 'preserve-3d' }}
          >
            <div className="flex-1 lg:flex-[3] min-h-0" style={{ transformStyle: 'preserve-3d' }}>
              <ChatInterface onSessionUpdate={setSessionData} />
            </div>
            <div className="flex-1 lg:flex-[3.5] min-h-0" style={{ transformStyle: 'preserve-3d' }}>
              <AuditLogPanel sessionId={sessionData.sessionId} />
            </div>
            <div className="flex-1 lg:flex-[3.5] min-h-0" style={{ transformStyle: 'preserve-3d' }}>
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
