import { Loader2 } from "lucide-react";

export default function MobileLoadingState({ message = "Carregando..." }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '32px 16px', color: '#64748b' }}>
      <Loader2 size={32} className="animate-spin" style={{ animation: 'spin 1s linear infinite', marginBottom: '16px' }} />
      <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
      <p style={{ margin: 0, fontSize: '14px' }}>{message}</p>
    </div>
  );
}
