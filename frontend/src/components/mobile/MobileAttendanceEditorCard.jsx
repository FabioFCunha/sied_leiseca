import { User, Image as ImageIcon } from "lucide-react";

export default function MobileAttendanceEditorCard({
  participant,
  value, // true (Absent), false (Present), null (Pending)
  onChange,
  showReason = false,
  reason = "",
  onReasonChange,
  disabled = false,
  allowAttachment = false,
  attachment = null,
  onAttachmentChange
}) {
  const isPresent = value === false;
  const isAbsent = value === true;
  const isPending = value === null;

  return (
    <div style={{
      padding: '16px',
      borderBottom: '1px solid #e2e8f0',
      backgroundColor: isPending ? '#fff' : (isPresent ? '#f0fdf4' : '#fef2f2'),
      transition: 'background-color 0.2s'
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '16px' }}>
        <div style={{
          width: '40px',
          height: '40px',
          borderRadius: '20px',
          backgroundColor: isPending ? '#e2e8f0' : (isPresent ? '#dcfce7' : '#fee2e2'),
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: isPending ? '#64748b' : (isPresent ? '#166534' : '#991b1b')
        }}>
          <User size={20} />
        </div>
        <div>
          <h4 style={{ margin: 0, fontSize: '15px', color: '#0f172a', fontWeight: '600' }}>
            {participant.name}
          </h4>
          <span style={{ fontSize: '13px', color: '#475569' }}>
            {participant.roleLabel}
          </span>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', marginBottom: (isAbsent && showReason) ? '16px' : '0' }}>
        <button
          type="button"
          disabled={disabled}
          onClick={() => onChange(false)}
          style={{
            padding: '12px',
            borderRadius: '8px',
            border: isPresent ? '2px solid #22c55e' : '1px solid #cbd5e1',
            backgroundColor: isPresent ? '#dcfce7' : '#fff',
            color: isPresent ? '#166534' : '#475569',
            fontWeight: isPresent ? '600' : '500',
            fontSize: '14px',
            opacity: disabled ? 0.6 : 1,
            cursor: disabled ? 'not-allowed' : 'pointer',
            textAlign: 'center'
          }}
        >
          Presente
        </button>

        <button
          type="button"
          disabled={disabled}
          onClick={() => onChange(true)}
          style={{
            padding: '12px',
            borderRadius: '8px',
            border: isAbsent ? '2px solid #ef4444' : '1px solid #cbd5e1',
            backgroundColor: isAbsent ? '#fee2e2' : '#fff',
            color: isAbsent ? '#991b1b' : '#475569',
            fontWeight: isAbsent ? '600' : '500',
            fontSize: '14px',
            opacity: disabled ? 0.6 : 1,
            cursor: disabled ? 'not-allowed' : 'pointer',
            textAlign: 'center'
          }}
        >
          Ausente
        </button>
      </div>

      {isAbsent && showReason && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', marginTop: '16px', padding: '12px', backgroundColor: '#fff', borderRadius: '8px', border: '1px solid #fecaca' }}>
          <label style={{ display: 'flex', flexDirection: 'column', gap: '6px', fontSize: '13px', fontWeight: '500', color: '#334155' }}>
            Motivo da ausência
            <input
              type="text"
              value={reason}
              onChange={(e) => onReasonChange(e.target.value)}
              placeholder="Ex: Falta, Atestado, Férias..."
              disabled={disabled}
              style={{ padding: '10px', borderRadius: '6px', border: '1px solid #cbd5e1', fontFamily: 'inherit' }}
            />
          </label>
          
          {allowAttachment && (
            <label style={{ display: 'flex', flexDirection: 'column', gap: '6px', fontSize: '13px', fontWeight: '500', color: '#334155' }}>
              Comprovante (opcional)
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '8px 10px', borderRadius: '6px', border: '1px dashed #cbd5e1', backgroundColor: '#f8fafc', overflow: 'hidden' }}>
                <ImageIcon size={16} color="#64748b" />
                <input
                  type="file"
                  onChange={(e) => onAttachmentChange(e.target.files?.[0] || null)}
                  disabled={disabled}
                  style={{ fontSize: '12px' }}
                />
              </div>
            </label>
          )}
        </div>
      )}
    </div>
  );
}
