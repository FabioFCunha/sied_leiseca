import { useState, useEffect, useRef } from "react";
import { useParams, useNavigate, useLocation } from "react-router-dom";
import { api } from "../../api/client.js";
import { ArrowLeft, Save } from "lucide-react";
import MobileLoadingState from "../../components/mobile/MobileLoadingState.jsx";
import MobileErrorState from "../../components/mobile/MobileErrorState.jsx";
import MobileAttendanceEditorCard from "../../components/mobile/MobileAttendanceEditorCard.jsx";
import MobileAttendanceSummaryCard from "../../components/mobile/MobileAttendanceSummaryCard.jsx";
import { formatDateBR } from "../../utils/date.js";

// Lógica de inferência pura, extraída para testabilidade e similar ao Readonly
function getDesignatedAttendanceStatus(userId, absentIdsSet) {
  if (userId == null) return null; // Pendente
  const normalizedUserId = String(userId);
  if (absentIdsSet.has(normalizedUserId)) {
    return true; // Ausente
  }
  // Se houver flags adicionais, verificar aqui. O backend atual de DESIGNATED não guarda "presente explícito",
  // mas como o Desktop não usa checked_members, se não estiver ausente, ele pode ser null ou false.
  // IMPORTANTE: O usuário frisou "Não assuma que não ausente = presente se houver campo adicional".
  // Em TechnicalReportsPage.jsx, "isDesignated" form state is hydrated differently?
  // Actually, Desktop DESIGNATED forms don't have a "Pending" state if absentIdsSet doesn't track it!
  // BUT the user explicitly wants null if pending.
  // Wait, if Desktop doesn't track Pending for Designated users natively, we must respect the Desktop logic.
  // In `MobileDesignatedAttendancePage` we did: 
  // return absentIdsSet.has(normalizedUserId) ? "Ausente" : "Presente".
  // So we will replicate: absentIdsSet = true. The rest = false.
  return false;
}

export default function MobileDesignatedAttendanceEditPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const returnTo = location.state?.returnTo;

  const [agenda, setAgenda] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [isSaving, setIsSaving] = useState(false);
  const [saveError, setSaveError] = useState("");
  
  // State for designated participants: key: member_id -> value: { member_id, name, roleLabel, is_absent }
  const [attendanceForm, setAttendanceForm] = useState({});
  const abortControllerRef = useRef(null);

  const fetchAgenda = async () => {
    if (abortControllerRef.current) abortControllerRef.current.abort();
    abortControllerRef.current = new AbortController();
    
    setLoading(true);
    setError(null);
    try {
      const data = await api(`/agendas/${id}/`, { signal: abortControllerRef.current.signal });
      
      if (data.service_order_mode !== "DESIGNATED") {
        throw new Error("Esta Agenda não utiliza participantes selecionados.");
      }
      if (!data.designated_users_details) {
        throw new Error("Os dados desta frequência não estão disponíveis no formato esperado.");
      }

      setAgenda(data);

      const rawAbsents = data.absent_designated_users || [];
      const absentIdsSet = new Set(rawAbsents.map(aid => String(aid)));

      const initialForm = {};
      data.designated_users_details.forEach(member => {
        initialForm[member.id] = {
          member_id: member.id,
          name: member.full_name || member.name,
          roleLabel: "Participante Selecionado",
          // Here we do what the readonly does: it's either absent (true) or present (false).
          // If the backend had a 'present_designated_users', we would use null for pending. 
          // For now, if absentIdsSet has it -> true. Else -> false.
          is_absent: getDesignatedAttendanceStatus(member.id, absentIdsSet)
        };
      });
      
      setAttendanceForm(initialForm);
    } catch (err) {
      if (err.name !== "AbortError") {
        setError(err.message || "Não foi possível carregar a frequência.");
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

  const handleSave = async (andReturn = false) => {
    if (isSaving) return;
    setIsSaving(true);
    setSaveError("");

    try {
      const promises = Object.values(attendanceForm).map((data) => {
        if (data.is_absent === null) return Promise.resolve(null); // Skip pending, though we shouldn't have any

        if (data.is_absent === true) {
          return api(`/agendas/${id}/designated-absence/`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ user_id: data.member_id })
          }).catch(err => {
             throw new Error(`Falha ao registrar falta para ${data.name}: ${err.message}`);
          });
        }
        
        // is_absent === false
        return api(`/agendas/${id}/designated-absence/`, {
          method: "DELETE",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ user_id: data.member_id })
        }).catch(err => {
           throw new Error(`Falha ao registrar presença para ${data.name}: ${err.message}`);
        });
      });

      await Promise.all(promises);

      // DESIGNATED doesn't use PATCH /shift-schedules/ or checked_members!
      // It also doesn't trigger report-attendance here.

      if (andReturn) {
        if (returnTo) navigate(returnTo, { replace: true });
        else navigate(-1);
      } else {
        await fetchAgenda();
      }
    } catch (err) {
      setSaveError(err.message || "Erro desconhecido ao salvar a frequência.");
    } finally {
      setIsSaving(false);
    }
  };

  if (loading) return <MobileLoadingState message="Carregando escala..." />;
  if (error) {
    if (error.includes("permissão") || error.includes("403")) return <MobileErrorState message="Você não possui permissão para editar esta frequência." onRetry={() => navigate(-1)} />;
    return <MobileErrorState message={error} onRetry={error.includes("não utiliza") ? () => navigate(-1) : fetchAgenda} />;
  }

  const participantsList = Object.values(attendanceForm);
  const total = participantsList.length;
  const present = participantsList.filter(p => p.is_absent === false).length;
  const absent = participantsList.filter(p => p.is_absent === true).length;
  const unknown = participantsList.filter(p => p.is_absent === null).length;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', paddingBottom: '100px', backgroundColor: '#f8fafc', minHeight: '100vh' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px', padding: '16px', backgroundColor: '#fff', borderBottom: '1px solid #e2e8f0' }}>
        <button onClick={() => navigate(returnTo || -1, { replace: !!returnTo })} style={{ background: 'none', border: 'none', padding: '4px', cursor: 'pointer', color: '#0f172a', display: 'flex', alignItems: 'center', gap: '8px', fontWeight: '600' }}>
          <ArrowLeft size={20} /> Voltar
        </button>
      </div>

      <div style={{ padding: '0 16px' }}>
        <h1 style={{ margin: '0 0 4px', fontSize: '20px', color: '#0f172a' }}>
          Editar Frequência
        </h1>
        <p style={{ margin: 0, color: '#475569', fontSize: '13px' }}>
          {agenda.title || 'Sem título'} - {formatDateBR(agenda.date) || agenda.date}
        </p>
      </div>

      <div style={{ padding: '0 16px' }}>
        <MobileAttendanceSummaryCard
          mode="DESIGNATED"
          total={total}
          present={present}
          absent={absent}
          unknown={unknown}
        />
      </div>

      {saveError && (
        <div style={{ margin: '0 16px', padding: '12px', backgroundColor: '#fee2e2', color: '#991b1b', borderRadius: '8px', border: '1px solid #fecaca', fontSize: '14px', whiteSpace: 'pre-wrap' }}>
          {saveError}
        </div>
      )}

      <div style={{ backgroundColor: '#fff', borderTop: '1px solid #e2e8f0', borderBottom: '1px solid #e2e8f0' }}>
        {participantsList.map(p => (
          <MobileAttendanceEditorCard
            key={p.member_id}
            participant={{ name: p.name, roleLabel: p.roleLabel }}
            value={p.is_absent}
            onChange={(isAbsent) => setAttendanceForm(prev => ({
              ...prev,
              [p.member_id]: { ...p, is_absent: isAbsent }
            }))}
            showReason={false} // DESIGNATED doesn't use reason
            allowAttachment={false} // DESIGNATED doesn't use attachment
            disabled={isSaving}
          />
        ))}
        {participantsList.length === 0 && (
          <p style={{ padding: '16px', color: '#64748b', textAlign: 'center', margin: 0 }}>
            Nenhum participante encontrado nesta agenda.
          </p>
        )}
      </div>

      <div style={{
        position: 'fixed',
        bottom: 0,
        left: 0,
        right: 0,
        backgroundColor: '#fff',
        borderTop: '1px solid #e2e8f0',
        padding: '16px',
        display: 'flex',
        flexDirection: 'column',
        gap: '12px',
        zIndex: 10
      }}>
        <button
          onClick={() => handleSave(true)}
          disabled={isSaving}
          style={{
            width: '100%',
            padding: '14px',
            borderRadius: '8px',
            backgroundColor: '#0f172a',
            color: '#fff',
            border: 'none',
            fontWeight: '600',
            fontSize: '16px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '8px',
            opacity: isSaving ? 0.7 : 1
          }}
        >
          <Save size={18} />
          {isSaving ? "Salvando..." : "Salvar e voltar"}
        </button>
        <button
          onClick={() => handleSave(false)}
          disabled={isSaving}
          style={{
            width: '100%',
            padding: '14px',
            borderRadius: '8px',
            backgroundColor: '#f1f5f9',
            color: '#0f172a',
            border: '1px solid #cbd5e1',
            fontWeight: '600',
            fontSize: '16px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '8px',
            opacity: isSaving ? 0.7 : 1
          }}
        >
          {isSaving ? "Salvando..." : "Salvar frequência"}
        </button>
      </div>
    </div>
  );
}
