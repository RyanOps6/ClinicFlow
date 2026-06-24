import { MessageSquare, Phone, Calendar } from 'lucide-react';

type TabKey = 'conversation' | 'sessions' | 'appointments';

interface Props {
  activeTab: TabKey;
  onChange: (tab: TabKey) => void;
}

const tabs: { key: TabKey; label: string; icon: React.ElementType }[] = [
  { key: 'conversation', label: 'Live Conversation', icon: MessageSquare },
  { key: 'sessions', label: 'Call Sessions', icon: Phone },
  { key: 'appointments', label: 'Appointments', icon: Calendar },
];

export default function TabBar({ activeTab, onChange }: Props) {
  return (
    <nav className="bg-white border-b border-slate-200 px-6">
      <div className="flex gap-0">
        {tabs.map(({ key, label, icon: Icon }) => {
          const isActive = activeTab === key;
          return (
            <button
              key={key}
              onClick={() => onChange(key)}
              className={`flex items-center gap-2 px-5 py-3.5 text-sm font-medium transition-colors relative
                ${isActive ? 'text-medical-600' : 'text-slate-500 hover:text-slate-700'}`}
            >
              <Icon className="w-4 h-4" />
              {label}
              {isActive && (
                <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-medical-500 rounded-t" />
              )}
            </button>
          );
        })}
      </div>
    </nav>
  );
}
