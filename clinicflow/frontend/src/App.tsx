import { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, useLocation } from 'react-router-dom';
import GlobalNav from './components/GlobalNav';
import ChatInterface from './components/ChatInterface';
import LiveSessionMonitor from './components/LiveSessionMonitor';
import HistoricalSessions from './components/HistoricalSessions';
import AppointmentsLedger from './components/AppointmentsLedger';
import AuditLogPanel from './components/AuditLogPanel';
import Login from './components/Login';
import Tilt3D from './components/Tilt3D';
import Home from './components/Home';
import gsap from 'gsap';

function DashboardContent() {
  const [token, setToken] = useState<string | null>(localStorage.getItem('auth_token'));
  const [sessionData, setSessionData] = useState({
    sessionId: null as number | null,
    intent: 'unknown',
    collectedData: {} as Record<string, unknown>,
    workflowState: '—',
    status: 'idle',
  });
  const location = useLocation();

  useEffect(() => {
    if (!token) return;

    // Build the GSAP timeline on mount and route change
    const tl = gsap.timeline({ defaults: { ease: 'power3.out' } });

    // 1. Sticky GlobalNav fades down
    tl.fromTo('#global-header', 
      { y: -60, opacity: 0 },
      { y: 0, opacity: 1, duration: 0.6 }
    );

    // 2. Animate the current route page wrapper: slide up and fade in
    const activePage = document.querySelector('.serene-page, #home-content');
    if (activePage) {
      tl.fromTo(activePage,
        { y: 30, opacity: 0 },
        { y: 0, opacity: 1, duration: 0.8, ease: 'power2.out' },
        '-=0.3'
      );
    }

    // 3. Grid cards slide up staggered with an 'expo.out' ease profile
    const cards = document.querySelectorAll('.clinic-card-3d');
    if (cards.length > 0) {
      tl.fromTo(cards,
        { y: 35, opacity: 0 },
        { y: 0, opacity: 1, duration: 1.0, ease: 'expo.out', stagger: 0.1 },
        '-=0.5'
      );
    }

    return () => {
      tl.kill();
    };
  }, [token, location.pathname]);

  return (
    <div className="w-full min-h-screen bg-white text-zinc-900 overflow-x-hidden flex flex-col relative font-sans">
      {/* Serene Editorial subtle ambient backgrounds wrapped to prevent overflow */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none z-0">
        <div className="absolute top-[-10%] left-[-10%] w-[50%] h-[50%] rounded-full bg-teal-150/10 blur-[150px]" />
        <div className="absolute bottom-[-10%] right-[-10%] w-[50%] h-[50%] rounded-full bg-sky-150/10 blur-[150px]" />
      </div>

      <GlobalNav />

      {!token ? (
        <main className="flex-1 flex items-center justify-center p-6 relative z-10 animate-fadeIn">
          <Login onLoginSuccess={(tok) => {
            setToken(tok);
            window.location.reload();
          }} />
        </main>
      ) : (
        <div className="flex-1 flex flex-col relative z-10">
          <Routes>
            <Route path="/" element={
              <div id="home-content" className="w-full">
                <Home />
              </div>
            } />
            <Route path="/playground" element={
              <div className="serene-page flex-1 p-6 lg:p-8 flex flex-col justify-start">
                <div 
                  className="grid grid-cols-1 lg:grid-cols-3 gap-6 h-auto lg:h-[calc(100vh-10rem)]"
                  style={{ perspective: '1200px', transformStyle: 'preserve-3d' }}
                >
                  <div className="h-[500px] lg:h-full min-h-0" style={{ transformStyle: 'preserve-3d' }}>
                    <ChatInterface onSessionUpdate={setSessionData} />
                  </div>
                  <div className="h-[350px] lg:h-full min-h-0" style={{ transformStyle: 'preserve-3d' }}>
                    <AuditLogPanel sessionId={sessionData.sessionId} />
                  </div>
                  <div className="h-[350px] lg:h-full min-h-0" style={{ transformStyle: 'preserve-3d' }}>
                    <Tilt3D className="h-full">
                      <LiveSessionMonitor
                        intent={sessionData.intent}
                        collectedData={sessionData.collectedData}
                        workflowState={sessionData.workflowState}
                        status={sessionData.status}
                      />
                    </Tilt3D>
                  </div>
                </div>
              </div>
            } />
            <Route path="/sessions" element={
              <div className="serene-page p-6 lg:p-10 max-w-[1440px] mx-auto w-full flex-1">
                <HistoricalSessions />
              </div>
            } />
            <Route path="/appointments" element={
              <div className="serene-page p-6 lg:p-10 max-w-[1440px] mx-auto w-full flex-1">
                <AppointmentsLedger />
              </div>
            } />
          </Routes>
        </div>
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
