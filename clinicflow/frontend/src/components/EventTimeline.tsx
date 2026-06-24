import type { DashboardEvent } from '../types';

interface Props {
  events: DashboardEvent[];
}

export default function EventTimeline({ events }: Props) {
  if (events.length === 0) {
    return (
      <div className="event-timeline">
        <h3>Event Timeline</h3>
        <p className="empty">No events yet.</p>
      </div>
    );
  }

  return (
    <div className="event-timeline">
      <h3>Event Timeline</h3>
      <div className="timeline">
        {events.map((e) => (
          <div key={e.id} className="timeline-item">
            <div className="timeline-dot" />
            <div className="timeline-content">
              <span className="event-type">{e.event_type.replace(/_/g, ' ')}</span>
              {e.created_at && <span className="event-time">{new Date(e.created_at).toLocaleString()}</span>}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
