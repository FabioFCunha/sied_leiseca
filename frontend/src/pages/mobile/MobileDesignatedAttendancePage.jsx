import { useState, useEffect, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { api } from "../../api/client.js";
import { ArrowLeft, Users } from "lucide-react";
import MobileLoadingState from "../../components/mobile/MobileLoadingState.jsx";
import MobileErrorState from "../../components/mobile/MobileErrorState.jsx";
import MobileAttendanceParticipantCard from "../../components/mobile/MobileAttendanceParticipantCard.jsx";
import MobileAttendanceSummaryCard from "../../components/mobile/MobileAttendanceSummaryCard.jsx";
import { formatDateBR } from "../../utils/date.js";

// Função de inferência isolada e testável, conforme requisito
function getDesignatedAttendanceStatus(userId, absentIdsSet) {
  if (userId == null) return "Situação não informada";
  
  const normalizedUserId = String(userId);
  if (absentIdsSet.has(normalizedUserId)) {
    return "Ausente";
  }
  return "Presente";
}

export default function MobileDesignatedAttendancePage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [agenda, setAgenda] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const abortControllerRef = useRef(null);

  const fetchAgenda = async () => {
    if (abortControllerRef.current) abortControllerRef.current.abort();
    abortControllerRef.current = new AbortController();
    
    setLoading(true);
    setError(null);
    try {
      const data = await api(`/agendas/${id}/`, { signal: abortControllerRef.current.signal });
      
      // Validação defensiva
      if (data.service_order_mode !== "DESIGNATED") {
        throw new Error("Esta Agenda não utiliza participantes selecionados.");
      }
      if (!data.designated_users_details) {
        throw new Error("Os dados desta frequência não estão disponíveis no formato esperado.");
      }

      setAgenda(data);
    } catch (err) {
      if (err.name !== "AbortError") {
        setError(err.message || "Não foi possível carregar a frequência.\n\nVerifique sua conexão e tente novamente.");
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAgenda();
    return () => {
      if (abortControllerRef.current) abortControllerRef.current.abort();
    };
  }, [id]);

  if (loading) return <MobileLoadingState message="Carregando frequência..." />;
  if (error) {
    if (error.includes("permissão") || error.includes("403")) return <MobileErrorState message="Você não possui permissão para consultar esta frequência." onRetry={() => navigate(-1)} />;
    if (error.includes("404")) return <MobileErrorState message="Não foi possível localizar os dados desta frequência." onRetry={() => navigate(-1)} />;
    return <MobileErrorState message={error} onRetry={error.includes("não utiliza") ? () => navigate(-1) : fetchAgenda} />;
  }

  // Prepara estrutura
  const rawAbsents = agenda.absent_designated_users || [];
  const absentIdsSet = new Set(rawAbsents.map(id => String(id)));
  
  const participantsList = (agenda.designated_users_details || []).map(member => {
    return {
      id: member.id,
      name: member.full_name || member.name,
      roleLabel: "Participante Selecionado",
      attendanceStatus: getDesignatedAttendanceStatus(member.id, absentIdsSet),
      absenceReason: null // Não existe justificativa detalhada no payload atual de Agenda para DESIGNATED
    };
  });

  const total = participantsList.length;
  const present = participantsList.filter(p => p.attendanceStatus === "Presente").length;
  const absent = participantsList.filter(p => p.attendanceStatus === "Ausente").length;
  const unknown = participantsList.filter(p => p.attendanceStatus === "Situação não informada").length;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', paddingBottom: '32px' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '4px' }}>
        <button onClick={() => navigate(-1)} style={{ background: 'none', border: 'none', padding: '8px', cursor: 'pointer', color: '#0a1e44', display: 'flex', alignItems: 'center', gap: '4px', fontWeight: '600' }}>
          <ArrowLeft size={20} /> Voltar
        </button>
      </div>

      <div>
        <h1 style={{ margin: '0 0 4px', fontSize: '22px', color: '#0f172a', lineHeight: '1.2' }}>
          Frequência da Agenda
        </h1>
        <p style={{ margin: 0, color: '#475569', fontSize: '14px' }}>
          {agenda.title || 'Sem título'} - {formatDateBR(agenda.date) || agenda.date} (ID: #{agenda.id})
        </p>
      </div>

      <MobileAttendanceSummaryCard
        mode="DESIGNATED"
        total={total}
        present={present}
        absent={absent}
        unknown={unknown}
      />

      {total === 0 ? (
        <MobileErrorState message="Nenhum participante foi informado para esta frequência." />
      ) : (
        <div className="mobile-card" style={{ padding: 0, overflow: 'hidden' }}>
          <h3 className="mobile-card-header" style={{ padding: '12px', display: 'flex', alignItems: 'center', gap: '6px' }}><Users size={18} /> Equipe Designada</h3>
          {participantsList.map((p, idx) => (
            <MobileAttendanceParticipantCard
              key={p.id || `fallback-${idx}`}
              name={p.name}
              roleLabel={p.roleLabel}
              attendanceStatus={p.attendanceStatus}
              absenceReason={p.absenceReason}
            />
          ))}
        </div>
      )}
      
    </div>
  );
}
