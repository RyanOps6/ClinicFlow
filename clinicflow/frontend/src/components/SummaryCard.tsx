interface Props {
  summary?: string;
}

export default function SummaryCard({ summary }: Props) {
  if (!summary) {
    return (
      <div className="summary-card">
        <h3>Summary</h3>
        <p className="empty">No summary available yet.</p>
      </div>
    );
  }

  const lines = summary.split('\n').filter(Boolean);

  return (
    <div className="summary-card">
      <h3>Session Summary</h3>
      <div className="summary-content">
        {lines.map((line, i) => (
          <p key={i}>{line}</p>
        ))}
      </div>
    </div>
  );
}
