import { useState, useEffect, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { api } from "../../api/client.js";
import { ArrowLeft, Users, User, Shield, Briefcase, Calendar as CalendarIcon, UserMinus } from "lucide-react";
import MobileLoadingState from "../../components/mobile/MobileLoadingState.jsx";
import MobileErrorState from "../../components/mobile/MobileErrorState.jsx";
import { formatDateBR } from "../../utils/date.js";

export default function MobileShiftScheduleDetailsPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [schedule, setSchedule] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const abortControllerRef = useRef(null);

  const fetchSchedule = async () => {
    if (abortControllerRef.current) abortControllerRef.current.abort();
    abortControllerRef.current = new AbortController();
    const signal = abortControllerRef.current.signal;

    setLoading(true);
    setError(null);
    try {
      const data = await api(`/shift-schedules/${id}/`, { signal });
      setSchedule(data);
    } catch (err) {
      if (err.name !== "AbortError") {
        setError(err.message || "Não foi possível carregar os detalhes da escala.");
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSchedule();
    return () => {
      if (abortControllerRef.current) abortControllerRef.current.abort();
    };
  }, [id]);

  const handleBack = () => {
    navigate(-1);
  };

  if (loading) return <MobileLoadingState message="Carregando escala..." />;
  if (error) return <MobileErrorState message={error} onRetry={fetchSchedule} />;
  if (!schedule) return <MobileErrorState message="Escala não encontrada." />;

  const members = schedule.members || { chiefs: [], agents: [], supports: [] };

  const renderMember = (member) => (
    <li key={member.id} style={{ display: 'flex', flexDirection: 'column', padding: '8px 0', borderBottom: '1px solid #f1f5f9' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span style={{ fontSize: '14px', fontWeight: '500', color: '#1e293b' }}>
          {member.full_name || member.name || "Membro desconhecido"}
        </span>
        {member.is_absent && (
          <span style={{ display: 'flex', alignItems: 'center', gap: '4px', backgroundColor: '#fee2e2', color: '#991b1b', fontSize: '11px', fontWeight: 'bold', padding: '2px 6px', borderRadius: '8px', textTransform: 'uppercase' }}>
            <UserMinus size={12} /> Falta
          </span>
        )}
      </div>
      {member.absence_reason && (
        <span style={{ fontSize: '13px', color: '#991b1b', marginTop: '4px', fontStyle: 'italic' }}>
          Motivo: {member.absence_reason}
        </span>
      )}
    </li>
  );

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', paddingBottom: '32px' }}>
      
      {/* Topbar interna */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '4px' }}>
        <button onClick={handleBack} style={{ background: 'none', border: 'none', padding: '8px', cursor: 'pointer', color: '#0a1e44', display: 'flex', alignItems: 'center', gap: '4px', fontWeight: '600' }}>
          <ArrowLeft size={20} />
          Voltar
        </button>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
        <span style={{ backgroundColor: '#e2e8f0', color: '#334155', fontSize: '12px', fontWeight: 'bold', padding: '4px 10px', borderRadius: '12px', textTransform: 'uppercase', alignSelf: 'flex-start' }}>
          Equipe {schedule.team_name}
        </span>
        <h1 style={{ margin: '8px 0 0', fontSize: '22px', color: '#0f172a', lineHeight: '1.3' }}>
          Escala de {formatDateBR(schedule.date) || schedule.date}
        </h1>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#64748b', fontSize: '14px', marginTop: '4px' }}>
          <CalendarIcon size={16} /> ID da escala: #{schedule.id}
        </div>
      </div>

      <div style={{ marginBottom: '8px' }}>
        <button 
          onClick={() => navigate(`/app/frequencia/escala/${schedule.id}`)}
          className="mobile-btn mobile-btn-outline" 
          style={{ width: '100%', display: 'flex', justifyContent: 'center' }}
        >
          Ver frequência
        </button>
      </div>

      {/* Chefia */}
      <div className="mobile-card">
        <h3 className="mobile-card-header" style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <Shield size={18} /> Chefia
        </h3>
        {members.chiefs && members.chiefs.length > 0 ? (
          <ul style={{ margin: 0, padding: 0, listStyle: 'none' }}>
            {members.chiefs.map(renderMember)}
          </ul>
        ) : (
          <p style={{ margin: '8px 0 0', fontSize: '14px', color: '#94a3b8' }}>Nenhum chefe escalado.</p>
        )}
      </div>

      {/* Agentes */}
      <div className="mobile-card">
        <h3 className="mobile-card-header" style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <Users size={18} /> Agentes
        </h3>
        {members.agents && members.agents.length > 0 ? (
          <ul style={{ margin: 0, padding: 0, listStyle: 'none' }}>
            {members.agents.map(renderMember)}
          </ul>
        ) : (
          <p style={{ margin: '8px 0 0', fontSize: '14px', color: '#94a3b8' }}>Nenhum agente escalado.</p>
        )}
      </div>

      {/* Apoios */}
      <div className="mobile-card">
        <h3 className="mobile-card-header" style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <Briefcase size={18} /> Apoios
        </h3>
        {members.supports && members.supports.length > 0 ? (
          <ul style={{ margin: 0, padding: 0, listStyle: 'none' }}>
            {members.supports.map(renderMember)}
          </ul>
        ) : (
          <p style={{ margin: '8px 0 0', fontSize: '14px', color: '#94a3b8' }}>Nenhum apoio escalado.</p>
        )}
      </div>

      {/* Transferências */}
      {schedule.member_changes && schedule.member_changes.length > 0 && (
        <div className="mobile-card">
          <h3 className="mobile-card-header" style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <User size={18} /> Transferências
          </h3>
          <ul style={{ margin: 0, paddingLeft: '20px', fontSize: '14px', color: '#475569' }}>
            {schedule.member_changes.map(change => (
              <li key={change.id} style={{ marginBottom: '6px' }}>
                <strong>{change.member_name}</strong>: {change.action_display || change.action} 
                {change.reason && ` - Motivo: ${change.reason}`}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Observações da Escala */}
      {schedule.notes && (
        <div className="mobile-card">
          <h3 className="mobile-card-header">Observações da Escala</h3>
          <p style={{ margin: 0, fontSize: '14px', color: '#475569', whiteSpace: 'pre-wrap', lineHeight: '1.5' }}>
            {schedule.notes}
          </p>
        </div>
      )}

    </div>
  );
}
