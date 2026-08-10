import { useState, useEffect, useRef } from "react";
import { useParams, useNavigate, useLocation } from "react-router-dom";
import { api } from "../../api/client.js";
import { ArrowLeft, Save } from "lucide-react";
import MobileLoadingState from "../../components/mobile/MobileLoadingState.jsx";
import MobileErrorState from "../../components/mobile/MobileErrorState.jsx";
import MobileAttendanceEditorCard from "../../components/mobile/MobileAttendanceEditorCard.jsx";
import MobileAttendanceSummaryCard from "../../components/mobile/MobileAttendanceSummaryCard.jsx";
import { formatDateBR } from "../../utils/date.js";

export default function MobileShiftAttendanceEditPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const returnTo = location.state?.returnTo;

  const [schedule, setSchedule] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [isSaving, setIsSaving] = useState(false);
  const [saveError, setSaveError] = useState("");
  
  // State for all participants: key: `${member_type}_${member_id}` -> value: { member_type, member_id, name, roleLabel, is_absent, reason, attachment }
  const [attendanceForm, setAttendanceForm] = useState({});
  const abortControllerRef = useRef(null);

  const fetchSchedule = async () => {
    if (abortControllerRef.current) abortControllerRef.current.abort();
    abortControllerRef.current = new AbortController();
    
    setLoading(true);
    setError(null);
    try {
      const data = await api(`/shift-schedules/${id}/`, { signal: abortControllerRef.current.signal });
      
      if (!data || !data.members || typeof data.members !== 'object') {
        throw new Error("Os dados desta frequência não estão disponíveis no formato esperado.");
      }
      
      setSchedule(data);

      const initialForm = {};
      const processGroup = (group, member_type, roleLabel) => {
        if (!group || !Array.isArray(group)) return;
        group.forEach(member => {
          const key = `${member_type}_${member.id}`;
          if (!initialForm[key]) {
            initialForm[key] = {
              member_type,
              member_id: member.id,
              name: member.full_name || member.name,
              roleLabel,
              is_absent: member.is_absent, // can be true, false, or null
              reason: member.absence_reason || "",
              attachment: null
            };
          }
        });
      };

      processGroup(data.members.chiefs, "CHIEF", "Chefe");
      processGroup(data.members.agents, "AGENT", "Agente");
      processGroup(data.members.supports, "SUPPORT", "Apoio");
      
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
    fetchSchedule();
    return () => {
      if (abortControllerRef.current) abortControllerRef.current.abort();
    };
  }, [id]);

  const handleSave = async (andReturn = false) => {
    if (isSaving) return;
    setIsSaving(true);
    setSaveError("");

    try {
      const promises = Object.entries(attendanceForm).map(([key, data]) => {
        if (data.is_absent === null) return Promise.resolve(null); // Skip pending

        if (data.is_absent === true) {
          const body = new FormData();
          body.append("member_type", data.member_type);
          body.append("member_id", data.member_id);
          body.append("reason", data.reason || "Falta");
          if (data.attachment) body.append("attachment", data.attachment);
          
          return api(`/shift-schedules/${id}/absence/`, { method: "POST", body }).catch(err => {
             throw new Error(`Falha ao registrar falta para ${data.name}: ${err.message}`);
          });
        }
        
        // is_absent === false
        return api(`/shift-schedules/${id}/absence/`, {
          method: "DELETE",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ member_type: data.member_type, member_id: data.member_id }),
        }).catch(err => {
           throw new Error(`Falha ao registrar presença para ${data.name}: ${err.message}`);
        });
      });

      await Promise.all(promises);

      // Now PATCH checked_members
      const checkedMembersData = {};
      Object.entries(attendanceForm).forEach(([key, data]) => {
        if (data.is_absent !== null) {
          checkedMembersData[key] = true;
        }
      });

      await api(`/shift-schedules/${id}/`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ checked_members: checkedMembersData }),
      });

      if (andReturn) {
        if (returnTo) navigate(returnTo, { replace: true });
        else navigate(-1);
      } else {
        // Just reload schedule data to reflect saved state
        await fetchSchedule();
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
    return <MobileErrorState message={error} onRetry={fetchSchedule} />;
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
          Editar Frequência: {schedule.team_name}
        </h1>
        <p style={{ margin: 0, color: '#475569', fontSize: '13px' }}>
          Escala: {formatDateBR(schedule.date) || schedule.date}
        </p>
      </div>

      <div style={{ padding: '0 16px' }}>
        <MobileAttendanceSummaryCard
          mode="TEAM"
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
            key={`${p.member_type}_${p.member_id}`}
            participant={{ name: p.name, roleLabel: p.roleLabel }}
            value={p.is_absent}
            onChange={(isAbsent) => setAttendanceForm(prev => ({
              ...prev,
              [`${p.member_type}_${p.member_id}`]: { ...p, is_absent: isAbsent }
            }))}
            showReason={true}
            reason={p.reason}
            onReasonChange={(reason) => setAttendanceForm(prev => ({
              ...prev,
              [`${p.member_type}_${p.member_id}`]: { ...p, reason }
            }))}
            disabled={isSaving}
            allowAttachment={true}
            attachment={p.attachment}
            onAttachmentChange={(file) => setAttendanceForm(prev => ({
              ...prev,
              [`${p.member_type}_${p.member_id}`]: { ...p, attachment: file }
            }))}
          />
        ))}
        {participantsList.length === 0 && (
          <p style={{ padding: '16px', color: '#64748b', textAlign: 'center', margin: 0 }}>
            Nenhum participante encontrado nesta escala.
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
