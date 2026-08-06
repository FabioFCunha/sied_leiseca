import { CheckCircle, XCircle, AlertCircle, RefreshCw } from "lucide-react";

export default function MobileAttendanceParticipantCard({ 
  name, 
  roleLabel, 
  attendanceStatus, 
  absenceReason, 
  transferLabel 
}) {
  
  // Determinando cores e ícones baseados no status estrito
  let statusColor = "#64748b";
  let statusBg = "#f1f5f9";
  let Icon = AlertCircle;

  if (attendanceStatus === "Presente") {
    statusColor = "#15803d";
    statusBg = "#dcfce7";
    Icon = CheckCircle;
  } else if (attendanceStatus === "Ausente") {
    statusColor = "#b91c1c";
    statusBg = "#fee2e2";
    Icon = XCircle;
  } else if (attendanceStatus === "Transferido") {
    statusColor = "#0369a1";
    statusBg = "#e0f2fe";
    Icon = RefreshCw;
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', padding: '12px', borderBottom: '1px solid #e2e8f0', backgroundColor: '#fff' }}>
      
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '8px' }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', flex: 1 }}>
          <span style={{ fontSize: '15px', fontWeight: '600', color: '#0f172a', lineHeight: '1.2' }}>
            {name || "Nome não informado"}
          </span>
          {roleLabel && (
            <span style={{ fontSize: '13px', color: '#64748b' }}>{roleLabel}</span>
          )}
        </div>
        
        <div style={{ display: 'flex', alignItems: 'center', gap: '4px', backgroundColor: statusBg, color: statusColor, padding: '4px 8px', borderRadius: '12px', fontSize: '12px', fontWeight: 'bold' }}>
          <Icon size={14} />
          <span>Situação: {attendanceStatus}</span>
        </div>
      </div>

      {absenceReason && (
        <div style={{ marginTop: '8px', fontSize: '13px', color: '#b91c1c', backgroundColor: '#fef2f2', padding: '8px', borderRadius: '6px', fontStyle: 'italic' }}>
          <strong>Motivo da falta:</strong> {absenceReason}
        </div>
      )}

      {transferLabel && (
        <div style={{ marginTop: '8px', fontSize: '13px', color: '#0369a1', backgroundColor: '#f0f9ff', padding: '8px', borderRadius: '6px' }}>
          <strong>Detalhe:</strong> {transferLabel}
        </div>
      )}
      
    </div>
  );
}
