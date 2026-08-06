import { useState, useEffect, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { api } from "../../api/client.js";
import { ArrowLeft, Users, Shield, Briefcase, User } from "lucide-react";
import MobileLoadingState from "../../components/mobile/MobileLoadingState.jsx";
import MobileErrorState from "../../components/mobile/MobileErrorState.jsx";
import MobileAttendanceParticipantCard from "../../components/mobile/MobileAttendanceParticipantCard.jsx";
import MobileAttendanceSummaryCard from "../../components/mobile/MobileAttendanceSummaryCard.jsx";
import { formatDateBR } from "../../utils/date.js";

// Função de inferência isolada e testável, conforme requisito
function getTeamAttendanceStatus(isAbsent) {
  if (isAbsent === true) return "Ausente";
  if (isAbsent === false) return "Presente";
  return "Situação não informada";
}

export default function MobileShiftAttendancePage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [schedule, setSchedule] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const abortControllerRef = useRef(null);

  const fetchSchedule = async () => {
    if (abortControllerRef.current) abortControllerRef.current.abort();
    abortControllerRef.current = new AbortController();
    
    setLoading(true);
    setError(null);
    try {
      const data = await api(`/shift-schedules/${id}/`, { signal: abortControllerRef.current.signal });
      
      // Validação de formato (falha segura se não for o esperado)
      if (!data || !data.members || typeof data.members !== 'object') {
        throw new Error("Os dados desta frequência não estão disponíveis no formato esperado.");
      }
      
      setSchedule(data);
    } catch (err) {
      if (err.name !== "AbortError") {
        setError(err.message || "Não foi possível carregar a frequência.\n\nVerifique sua conexão e tente novamente.");
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

  if (loading) return <MobileLoadingState message="Carregando frequência..." />;
  if (error) {
    if (error.includes("permissão") || error.includes("403")) return <MobileErrorState message="Você não possui permissão para consultar esta frequência." onRetry={() => navigate(-1)} />;
    if (error.includes("404")) return <MobileErrorState message="Não foi possível localizar os dados desta frequência." onRetry={() => navigate(-1)} />;
    return <MobileErrorState message={error} onRetry={fetchSchedule} />;
  }

  // Prepara membros de forma unificada para gerar cartões e totais
  const participantsList = [];
  
  const processGroup = (group, roleLabel) => {
    if (!group || !Array.isArray(group)) return;
    group.forEach(member => {
      // Ignora repetições por ID para os cálculos
      if (participantsList.some(p => p.id === member.id && p.id != null)) return;
      
      participantsList.push({
        id: member.id,
        name: member.full_name || member.name,
        roleLabel,
        attendanceStatus: getTeamAttendanceStatus(member.is_absent),
        absenceReason: member.is_absent === true && member.absence_reason ? member.absence_reason : null
      });
    });
  };

  processGroup(schedule.members.chiefs, "Chefe");
  processGroup(schedule.members.agents, "Agente");
  processGroup(schedule.members.supports, "Apoio");

  const total = participantsList.length;
  const present = participantsList.filter(p => p.attendanceStatus === "Presente").length;
  const absent = participantsList.filter(p => p.attendanceStatus === "Ausente").length;
  const unknown = participantsList.filter(p => p.attendanceStatus === "Situação não informada").length;

  let globalStatusText = "Frequência ainda não enviada";
  if (schedule.attendance_approved === true) {
    globalStatusText = "Frequência validada";
  } else if (schedule.attendance_reported === true) {
    globalStatusText = "Frequência enviada para validação";
  }

  const renderList = (items) => {
    if (!items || items.length === 0) return <p style={{ padding: '0 12px 12px', margin: 0, fontSize: '14px', color: '#64748b' }}>Nenhum participante nesta categoria.</p>;
    return items.map((p, idx) => (
      <MobileAttendanceParticipantCard
        key={p.id || `fallback-${idx}`}
        name={p.name}
        roleLabel={p.roleLabel}
        attendanceStatus={p.attendanceStatus}
        absenceReason={p.absenceReason}
      />
    ));
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', paddingBottom: '32px' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '4px' }}>
        <button onClick={() => navigate(-1)} style={{ background: 'none', border: 'none', padding: '8px', cursor: 'pointer', color: '#0a1e44', display: 'flex', alignItems: 'center', gap: '4px', fontWeight: '600' }}>
          <ArrowLeft size={20} /> Voltar
        </button>
      </div>

      <div>
        <h1 style={{ margin: '0 0 4px', fontSize: '22px', color: '#0f172a' }}>
          Frequência: Equipe {schedule.team_name}
        </h1>
        <p style={{ margin: 0, color: '#475569', fontSize: '14px' }}>
          Escala: {formatDateBR(schedule.date) || schedule.date} (ID: #{schedule.id})
        </p>
      </div>

      <MobileAttendanceSummaryCard
        mode="TEAM"
        globalStatusText={globalStatusText}
        total={total}
        present={present}
        absent={absent}
        unknown={unknown}
        reportedAt={schedule.attendance_reported_at}
        approvedAt={schedule.attendance_approved_at}
      />

      {total === 0 ? (
        <MobileErrorState message="Nenhum participante foi informado para esta frequência." />
      ) : (
        <>
          <div className="mobile-card" style={{ padding: 0, overflow: 'hidden' }}>
            <h3 className="mobile-card-header" style={{ padding: '12px', display: 'flex', alignItems: 'center', gap: '6px' }}><Shield size={18} /> Chefia</h3>
            {renderList(participantsList.filter(p => p.roleLabel === "Chefe"))}
          </div>

          <div className="mobile-card" style={{ padding: 0, overflow: 'hidden' }}>
            <h3 className="mobile-card-header" style={{ padding: '12px', display: 'flex', alignItems: 'center', gap: '6px' }}><Users size={18} /> Agentes</h3>
            {renderList(participantsList.filter(p => p.roleLabel === "Agente"))}
          </div>

          <div className="mobile-card" style={{ padding: 0, overflow: 'hidden' }}>
            <h3 className="mobile-card-header" style={{ padding: '12px', display: 'flex', alignItems: 'center', gap: '6px' }}><Briefcase size={18} /> Apoios</h3>
            {renderList(participantsList.filter(p => p.roleLabel === "Apoio"))}
          </div>
        </>
      )}

      {schedule.member_changes && schedule.member_changes.length > 0 && (
        <div className="mobile-card" style={{ padding: 0, overflow: 'hidden' }}>
          <h3 className="mobile-card-header" style={{ padding: '12px', display: 'flex', alignItems: 'center', gap: '6px' }}><User size={18} /> Transferências Registradas</h3>
          {schedule.member_changes.map(change => (
            <div key={change.id} style={{ padding: '12px', borderBottom: '1px solid #e2e8f0', backgroundColor: '#f8fafc' }}>
               <div style={{ fontWeight: '600', color: '#0f172a', marginBottom: '4px' }}>{change.member_name}</div>
               <div style={{ fontSize: '13px', color: '#475569' }}>
                 <strong>Ação:</strong> {change.action_display || change.action}
               </div>
               {change.reason && (
                 <div style={{ fontSize: '13px', color: '#475569', marginTop: '2px' }}>
                   <strong>Motivo:</strong> {change.reason}
                 </div>
               )}
            </div>
          ))}
        </div>
      )}
      
    </div>
  );
}
