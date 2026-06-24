import type { MessageEntry } from '../types';

interface Props {
  transcript: MessageEntry[];
}

export default function ChatPanel({ transcript }: Props) {
  return (
    <div className="chat-panel">
      <h3>Conversation</h3>
      <div className="chat-messages">
        {transcript.length === 0 && (
          <p className="chat-empty">Start a session to begin the conversation.</p>
        )}
        {transcript.map((entry, i) => (
          <div key={i} className={`chat-message chat-${entry.role}`}>
            <span className="chat-label">{entry.role === 'assistant' ? 'Clinic' : 'You'}</span>
            <p>{entry.content}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
