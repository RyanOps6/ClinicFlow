import { LayoutDashboard, Bot, History, Calendar } from 'lucide-react';

type TabKey = 'dashboard' | 'playground' | 'sessions' | 'appointments';

interface Props {
  activeTab: TabKey;
  onChange: (tab: TabKey) => void;
}

const tabs: { key: TabKey; label: string; icon: React.ElementType }[] = [
  { key: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { key: 'playground', label: 'Receptionist Playground', icon: Bot },
  { key: 'sessions', label: 'Past Sessions', icon: History },
  { key: 'appointments', label: 'Appointments Manager', icon: Calendar },
];

export default function TabBar({ activeTab, onChange }: Props) {
  return (
    <nav className="backdrop-blur-md bg-white/40 border-b border-slate-200 px-6 relative z-10">
      <div className="flex gap-2">
        {tabs.map(({ key, label, icon: Icon }) => {
          const isActive = activeTab === key;
          return (
            <button
              key={key}
              onClick={() => onChange(key)}
              className={`flex items-center gap-2 px-5 py-4 text-xs font-bold uppercase tracking-wider transition-all duration-300 relative btn-3d
                ${isActive ? 'text-teal-600' : 'text-slate-500 hover:text-slate-800'}`}
            >
              <Icon className={`w-4 h-4 transition-transform duration-300 ${isActive ? 'scale-110 text-teal-600' : 'text-slate-500'}`} />
              <span>{label}</span>
              {isActive && (
                <span className="absolute bottom-0 left-0 right-0 h-[2.5px] bg-gradient-to-r from-teal-500 to-sky-500 rounded-t" />
              )}
            </button>
          );
        })}
      </div>
    </nav>
  );
}
