import { ClipboardCheck, Clock, CheckCircle } from "lucide-react";
import { formatDateBR } from "../../utils/date.js";

export default function MobileAttendanceSummaryCard({
  mode, // 'TEAM' | 'DESIGNATED'
  globalStatusText,
  total,
  present,
  absent,
  unknown,
  reportedAt,
  approvedAt
}) {
  
  return (
    <div className="mobile-card" style={{ marginBottom: '16px' }}>
      <h3 className="mobile-card-header" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
        <ClipboardCheck size={18} /> Resumo da Frequência
      </h3>
      
      <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
        
        {/* Status Global apenas para TEAM */}
        {mode === 'TEAM' && globalStatusText && (
          <div style={{ padding: '12px', backgroundColor: '#f8fafc', borderRadius: '8px', border: '1px solid #e2e8f0' }}>
            <span style={{ display: 'block', fontSize: '14px', fontWeight: 'bold', color: '#0f172a', marginBottom: '8px' }}>
              {globalStatusText}
            </span>
            {reportedAt && (
              <span style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '13px', color: '#475569', marginBottom: '4px' }}>
                <Clock size={14} /> Enviado: {formatDateBR(reportedAt)}
              </span>
            )}
            {approvedAt && (
              <span style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '13px', color: '#475569' }}>
                <CheckCircle size={14} /> Validado: {formatDateBR(approvedAt)}
              </span>
            )}
          </div>
        )}

        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
          <div style={{ flex: '1 1 45%', backgroundColor: '#f1f5f9', padding: '12px', borderRadius: '8px', textAlign: 'center' }}>
            <div style={{ fontSize: '20px', fontWeight: 'bold', color: '#334155' }}>{total}</div>
            <div style={{ fontSize: '12px', color: '#64748b', textTransform: 'uppercase' }}>Previstos</div>
          </div>
          
          <div style={{ flex: '1 1 45%', backgroundColor: '#dcfce7', padding: '12px', borderRadius: '8px', textAlign: 'center' }}>
            <div style={{ fontSize: '20px', fontWeight: 'bold', color: '#166534' }}>{present}</div>
            <div style={{ fontSize: '12px', color: '#15803d', textTransform: 'uppercase' }}>Presentes</div>
          </div>

          <div style={{ flex: '1 1 45%', backgroundColor: '#fee2e2', padding: '12px', borderRadius: '8px', textAlign: 'center' }}>
            <div style={{ fontSize: '20px', fontWeight: 'bold', color: '#991b1b' }}>{absent}</div>
            <div style={{ fontSize: '12px', color: '#b91c1c', textTransform: 'uppercase' }}>Ausentes</div>
          </div>

          {unknown > 0 && (
            <div style={{ flex: '1 1 45%', backgroundColor: '#fef9c3', padding: '12px', borderRadius: '8px', textAlign: 'center' }}>
              <div style={{ fontSize: '20px', fontWeight: 'bold', color: '#854d0e' }}>{unknown}</div>
              <div style={{ fontSize: '12px', color: '#a16207', textTransform: 'uppercase', lineHeight: '1.2' }}>Sem inf.</div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
