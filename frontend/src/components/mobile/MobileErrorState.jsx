import { AlertTriangle, RefreshCw } from "lucide-react";

export default function MobileErrorState({ message = "Não foi possível carregar as informações. Verifique sua conexão e tente novamente.", onRetry }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '32px 16px', color: '#dc2626', textAlign: 'center' }}>
      <AlertTriangle size={40} style={{ marginBottom: '16px', opacity: 0.8 }} />
      <p style={{ margin: '0 0 24px', fontSize: '14px', lineHeight: '1.5', color: '#991b1b' }}>{message}</p>
      {onRetry && (
        <button onClick={onRetry} className="mobile-btn mobile-btn-outline" style={{ borderColor: '#dc2626', color: '#dc2626', width: 'auto', padding: '8px 24px' }}>
          <RefreshCw size={16} />
          Tentar novamente
        </button>
      )}
    </div>
  );
}
