import { useParams, useNavigate } from "react-router-dom";
import { ArrowLeft, FileText } from "lucide-react";

export default function MobileReportFormPage() {
  const { agendaId, id } = useParams();
  const navigate = useNavigate();

  const isEdit = Boolean(id);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', paddingBottom: '32px' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '8px' }}>
        <button 
          onClick={() => navigate(-1)} 
          style={{ background: 'none', border: 'none', padding: '8px', cursor: 'pointer', color: '#0a1e44', display: 'flex', alignItems: 'center', gap: '4px', fontWeight: '600' }}
        >
          <ArrowLeft size={20} />
          Voltar
        </button>
      </div>

      <div className="mobile-card" style={{ textAlign: 'center', padding: '32px 16px' }}>
        <FileText size={48} color="#cbd5e1" style={{ margin: '0 auto 16px' }} />
        <h2 style={{ margin: '0 0 8px', color: '#0f172a' }}>
          {isEdit ? "Editar Relatório" : "Novo Relatório"}
        </h2>
        <p style={{ margin: 0, color: '#64748b', fontSize: '14px' }}>
          O formulário móvel será implementado na próxima etapa (M3).
        </p>
        <div style={{ marginTop: '24px', fontSize: '12px', color: '#94a3b8' }}>
          {isEdit ? `ID do Relatório: ${id}` : `ID da Agenda: ${agendaId}`}
        </div>
      </div>
    </div>
  );
}
