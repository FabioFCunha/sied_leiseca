import { Inbox } from "lucide-react";

export default function MobileEmptyState({ message = "Nenhum dado encontrado." }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '48px 16px', color: '#94a3b8', textAlign: 'center' }}>
      <Inbox size={48} style={{ marginBottom: '16px', opacity: 0.5 }} />
      <p style={{ margin: 0, fontSize: '15px' }}>{message}</p>
    </div>
  );
}
