interface Props {
  label: string;
  value: number;
  color?: string;
}

export default function StatCard({ label, value, color }: Props) {
  return (
    <div className="stat-card" style={color ? { borderLeftColor: color } : undefined}>
      <div className="stat-value">{value}</div>
      <div className="stat-label">{label}</div>
    </div>
  );
}
