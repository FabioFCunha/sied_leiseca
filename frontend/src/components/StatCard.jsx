export default function StatCard({ active = false, label, onClick, tone, value }) {
  const Component = onClick ? "button" : "article";

  return (
    <Component
      className={`stat-card ${tone || ""} ${active ? "active" : ""}`}
      onClick={onClick}
      type={onClick ? "button" : undefined}
    >
      <span>{label}</span>
      <strong>{value ?? 0}</strong>
    </Component>
  );
}
