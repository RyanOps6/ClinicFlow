import { useState } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import GlobalNav from './components/GlobalNav';
import TabBar from './components/TabBar';
import ChatInterface from './components/ChatInterface';
import LiveSessionMonitor from './components/LiveSessionMonitor';
import SessionsLog from './components/SessionsLog';
import AppointmentsLedger from './components/AppointmentsLedger';
import AuditLogPanel from './components/AuditLogPanel';

type TabKey = 'conversation' | 'sessions' | 'appointments';

function DashboardContent() {
  const [activeTab, setActiveTab] = useState<TabKey>('conversation');
  const [sessionData, setSessionData] = useState({
    sessionId: null as number | null,
    intent: 'unknown',
    collectedData: {} as Record<string, unknown>,
    workflowState: '—',
    status: 'idle',
  });

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col">
      <GlobalNav />
      <TabBar activeTab={activeTab} onChange={setActiveTab} />

      <main className="flex-1 p-6 max-w-[1440px] mx-auto w-full">
        {activeTab === 'conversation' && (
          <div className="flex flex-col lg:flex-row gap-6 h-[calc(100vh-13rem)]">
            <div className="flex-1 lg:flex-[3] min-h-0">
              <ChatInterface onSessionUpdate={setSessionData} />
            </div>
            <div className="flex-1 lg:flex-[3.5] min-h-0">
              <AuditLogPanel sessionId={sessionData.sessionId} />
            </div>
            <div className="flex-1 lg:flex-[3.5] min-h-0">
              <LiveSessionMonitor
                intent={sessionData.intent}
                collectedData={sessionData.collectedData}
                workflowState={sessionData.workflowState}
                status={sessionData.status}
              />
            </div>
          </div>
        )}

        {activeTab === 'sessions' && <SessionsLog />}
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
