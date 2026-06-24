interface Props {
  workflowState?: string;
  collectedData: Record<string, unknown>;
  urgencyLevel: string;
  intent: string;
  status: string;
}

export default function SessionStateCard({
  workflowState,
  collectedData,
  urgencyLevel,
  intent,
  status,
}: Props) {
  const fields = [
    { label: 'Name', value: collectedData.full_name },
    { label: 'Phone', value: collectedData.phone },
    { label: 'Reason', value: collectedData.reason_for_visit },
    { label: 'Slot', value: collectedData.preferred_slot_or_date },
  ].filter((f) => f.value);

  return (
    <div className="session-state-card">
      <h3>Session State</h3>
      <div className="state-row">
        <span className="state-label">Status</span>
        <span className={`state-badge state-${status}`}>{status}</span>
      </div>
      <div className="state-row">
        <span className="state-label">Intent</span>
        <span>{intent}</span>
      </div>
      <div className="state-row">
        <span className="state-label">Step</span>
        <span>{(workflowState ?? '—').replace(/_/g, ' ')}</span>
      </div>
      {urgencyLevel !== 'none' && (
        <div className="state-row">
          <span className="state-label">Urgency</span>
          <span className={`state-badge urgency-${urgencyLevel}`}>{urgencyLevel}</span>
        </div>
      )}
      {fields.length > 0 && (
        <>
          <h4>Collected Data</h4>
          {fields.map((f) => (
            <div key={f.label} className="state-row">
              <span className="state-label">{f.label}</span>
              <span>{String(f.value)}</span>
            </div>
          ))}
        </>
      )}
    </div>
  );
}
