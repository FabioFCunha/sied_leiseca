import React, { useState, useEffect } from "react";
import { useParams, useNavigate, useLocation } from "react-router-dom";
import { ArrowLeft, FileText, Plus, Save, Trash2 } from "lucide-react";
import { api } from "../../api/client.js";
import { STREET_ACTION_ID } from "../../utils/constants";
import MobileLoadingState from "../../components/mobile/MobileLoadingState.jsx";
import MobileErrorState from "../../components/mobile/MobileErrorState.jsx";
import MobileAttendanceSummaryCard from "../../components/mobile/MobileAttendanceSummaryCard.jsx";
import { getValidatableActions } from "../technicalReportsActionHelpers.js";

const numberFields = ["approach"];

function nullable(value) {
  if (value === "" || value === undefined) return null;
  return value;
}

function buildActionPayload(action, formAgenda) {
  return {
    ...action,
    agenda: nullable(action.agenda || formAgenda),
    source_id: nullable(action.source_id),
    ...Object.fromEntries(numberFields.map((field) => [field, Number(action[field] || 0)])),
    approached_lectures: Number(action.approached_lectures || 0),
    approached_actions: (action.approached_actions === "" || action.approached_actions === null || action.approached_actions === undefined) ? 0 : Number(action.approached_actions),
  };
}

function normalizePayload(form, status) {
  const { request_details, ...payloadForm } = form;
  return {
    ...payloadForm,
    status: status,
    source: "LOCAL",
    source_id: nullable(form.source_id),
    agenda: nullable(form.agenda),
    management_id: nullable(form.management_id),
    approximate_public: nullable(form.approximate_public),
    lat: nullable(form.lat),
    lng: nullable(form.lng),
    general_observations: form.general_observations || "",
    has_exceptional_occurrence: Boolean(form.has_exceptional_occurrence),
    exceptional_occurrence_type: form.has_exceptional_occurrence ? (form.exceptional_occurrence_type || "") : "",
    exceptional_occurrence_description: form.has_exceptional_occurrence ? (form.exceptional_occurrence_description || "") : "",
    exceptional_occurrence_actions_taken: form.has_exceptional_occurrence ? (form.exceptional_occurrence_actions_taken || "") : "",
    exceptional_occurrence_impact: form.has_exceptional_occurrence ? (form.exceptional_occurrence_impact || "") : "",
    actions: getValidatableActions(form.actions).map(({ action }) => buildActionPayload(action, form.agenda)),
  };
}

const emptyAction = {
  agenda: "",
  source_id: "",
  place_action: "",
  type_action: "",
  type_audience: "",
  institution_name: "",
  start_time: "",
  final_hour: "",
  approach: "",
  approached_lectures: "",
  approached_actions: "",
  equipment_materials_removed: "",
  equipment_materials_distributed: "",
  distribution_materials_removed: "",
  distribution_materials_distributed: ""
};

const streetActionTypeOptions = [
  "BAR", "EMPRESA", "ESCOLA", "ESPORTES", "EVENTO", "FESTA_BAIRRO",
  "PARQUE", "PEDAGIO", "PRAIA", "SHOPPING", "UNIVERSIDADE", "PONTO_TURISTICO", "SINDICATO"
];

function streetActionTypeLabel(type) {
  const map = {
    BAR: "Bares", EMPRESA: "Empresas", ESCOLA: "Escolas", ESPORTES: "Esportes",
    EVENTO: "Eventos", FESTA_BAIRRO: "Festa de Bairro", PARQUE: "Praças / Parques Púb.",
    PEDAGIO: "Pedágio", PRAIA: "Praia", SHOPPING: "Shopping / Centro Comercial",
    UNIVERSIDADE: "Universidades", PONTO_TURISTICO: "Pontos Turísticos", SINDICATO: "Sindicato"
  };
  return map[type] || type;
}

function normalizeTypeLabel(value) {
  return String(value || "").trim().toLocaleLowerCase("pt-BR");
}

function isStreetActionValue(value) {
  const normalized = normalizeTypeLabel(value);
  return String(value) === STREET_ACTION_ID || normalized === "ação de rua" || normalized === "acao de rua";
}

function isStreetActionAgenda(agenda) {
  return Boolean(
    isStreetActionValue(agenda?.action_type_ref) ||
    isStreetActionValue(agenda?.requester_entity_type) ||
    isStreetActionValue(agenda?.action_type_ref_name)
  );
}


function getAgendaActionPlace(agenda = {}) {
  const fullAddress = [
    agenda.address,
    agenda.neighborhood || agenda.neighborhood_ref_name,
    agenda.city || agenda.municipality_ref_name,
    agenda.state,
  ].filter(Boolean).join(", ");

  return fullAddress || agenda.location || agenda.institution_location || "";
}

function getAgendaContact(agenda = {}) {
  return [
    agenda.external_responsible,
    agenda.external_responsible_phone,
    agenda.external_email,
  ]
    .map((value) => String(value || "").trim())
    .filter(Boolean)
    .join(", ");
}

function hydrateActionFromAgenda(action = {}, agenda = {}) {
  return {
    ...action,
    agenda: action.agenda || agenda.id || "",
    source_id: action.source_id || (agenda.id ? `agenda_action:${agenda.id}` : ""),
    place_action: action.place_action || getAgendaActionPlace(agenda),
    institution_name:
      action.institution_name ||
      agenda.institution_location ||
      agenda.location ||
      "",
    type_action:
      action.type_action ||
      agenda.action_type ||
      agenda.action_type_ref_name ||
      "",
    type_audience: action.type_audience || agenda.audience || "",
    start_time:
      action.start_time ||
      agenda.start_time?.slice?.(0, 5) ||
      "",
    final_hour:
      action.final_hour ||
      agenda.end_time?.slice?.(0, 5) ||
      "",
    approach:
      action.approach !== undefined &&
      action.approach !== null &&
      action.approach !== ""
        ? action.approach
        : (agenda.quantity || 0),
  };
}

export default function MobileReportFormPage() {
  const { agendaId, id } = useParams();
  const navigate = useNavigate();

  const isEdit = Boolean(id);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [form, setForm] = useState(null);
  const [agenda, setAgenda] = useState(null);
  const [isSaving, setIsSaving] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [message, setMessage] = useState("");
  const location = useLocation();

  // Frequência state
  const [reportSchedule, setReportSchedule] = useState(null);
  const [attendanceStats, setAttendanceStats] = useState({ total: 0, present: 0, absent: 0, pending: 0, loaded: false });
  const [attendanceError, setAttendanceError] = useState("");

  useEffect(() => {
    const controller = new AbortController();
    const loadData = async () => {
      setLoading(true);
      setError("");
      try {
        if (isEdit) {
          const report = await api(`/education-reports/${id}/`, { signal: controller.signal });

          if (report.status !== "DRAFT" && report.status !== "RETURNED") {
            navigate(`/app/relatorios/${id}`, { replace: true });
            return;
          }

          const repAgenda = report.agenda ? await api(`/agendas/${report.agenda}/`, { signal: controller.signal }) : null;
          setAgenda(repAgenda);

          const resolvedDetails = report.street_action_details?.length
            ? report.street_action_details
            : (repAgenda?.street_action_details || []);

          setForm({
            ...report,
            agenda_title: report.agenda_title || repAgenda?.title || "",
            agenda_date: report.agenda_date || repAgenda?.date || "",
            agenda_location:
              report.agenda_location ||
              repAgenda?.institution_location ||
              repAgenda?.location ||
              "",
            operation_date: report.operation_date || repAgenda?.date || "",
            contact_received:
              report.contact_received ||
              getAgendaContact(repAgenda || {}),
            street_action_details: resolvedDetails,
            actions: (() => {
              const reportActions = report.actions?.length
                ? report.actions
                : [{ ...emptyAction }];
              const hasAnySourceId = reportActions.some((action) => action?.source_id);
              return reportActions.map((action, index) =>
                hydrateActionFromAgenda({
                  ...action,
                  __userCreated: action.__userCreated ?? (hasAnySourceId ? !action.source_id : index > 0),
                }, repAgenda || {})
              );
            })()
          });
        } else {
          const fetchedAgenda = await api(`/agendas/${agendaId}/`, { signal: controller.signal });

          const res = await api(`/education-reports/?protocol=${agendaId}`, { signal: controller.signal });
          const results = res.results || res;

          const agendaTeam = fetchedAgenda?.team_name || fetchedAgenda?.team_ref_name || fetchedAgenda?.sector_name || fetchedAgenda?.team_ref;
          const matchingReport = agendaTeam ? results.find(r => String(r.team) === String(agendaTeam)) : null;

          if (matchingReport) {
            if (matchingReport.status === "DRAFT" || matchingReport.status === "RETURNED") {
               navigate(`/app/relatorios/${matchingReport.id}/editar`, { replace: true });
            } else {
               navigate(`/app/relatorios/${matchingReport.id}`, { replace: true });
            }
            return;
          }

          setAgenda(fetchedAgenda);
          setForm({
            source: "LOCAL",
            source_id: "",
            agenda: fetchedAgenda.id || "",
            agenda_title: fetchedAgenda.title || "",
            agenda_date: fetchedAgenda.date || "",
            agenda_location:
              fetchedAgenda.institution_location ||
              fetchedAgenda.location ||
              "",
            management_id: "",
            management_name: "",
            education_agents: "",
            changes_staff: "",
            approximate_public: "",
            request_details: "",
            breathalyzers: "",
            cars: "",
            changes_general: "",
            contact_received: getAgendaContact(fetchedAgenda),
            occurrence_observation: "",
            general_observations: "",
            lat: "",
            lng: "",

            status: "DRAFT",
            operation_date: fetchedAgenda.date || "",
            team: agendaTeam || "",
            street_action_details: fetchedAgenda.street_action_details || [],
            actions: [hydrateActionFromAgenda({
              ...emptyAction,
              __userCreated: false,
              approach: fetchedAgenda.quantity || 0,
              type_audience: fetchedAgenda.audience || ""
            }, fetchedAgenda)],
            accessibility_conditions_met: "",
            has_exceptional_occurrence: false,
            exceptional_occurrence_type: "",
            exceptional_occurrence_description: "",
            exceptional_occurrence_actions_taken: "",
            exceptional_occurrence_impact: "",
            materials_removed: "",
            materials_spent: "",
            distribution_materials_removed: "",
            distribution_materials_distributed: ""
          });
        }
      } catch (err) {
        if (err.name !== "AbortError") {
          setError(err.message || "Erro ao carregar dados do formulário.");
        }
      } finally {
        setLoading(false);
      }
    };
    loadData();
    return () => controller.abort();
  }, [agendaId, id, isEdit, navigate]);

  // Carregar e revalidar frequência sempre que form (op date/team) ou location mudar (retorno)
  useEffect(() => {
    if (!form || !agenda) return;

    const loadAttendance = async () => {
      setAttendanceError("");
      try {
        if (agenda.service_order_mode === "DESIGNATED") {
          // Recarregar a agenda mais atualizada para garantir que ausências foram capturadas
          const updatedAgenda = await api(`/agendas/${agenda.id}/`);
          const designated = updatedAgenda.designated_users_details || [];
          const absents = new Set((updatedAgenda.absent_designated_users || []).map(String));

          setAttendanceStats({
            total: designated.length,
            present: designated.filter(u => !absents.has(String(u.id))).length,
            absent: designated.filter(u => absents.has(String(u.id))).length,
            pending: 0,
            loaded: true
          });
          setReportSchedule(null);
        } else {
          // TEAM
          if (!form.operation_date || !form.team) return;
          const res = await api(`/shift-schedules/?date=${form.operation_date}`);
          const schedules = res.results || res;
          const scheduleInfo = schedules.find(s =>
            String(s.team) === String(form.team) ||
            String(s.team_name) === String(form.team) ||
            String(s.team) === String(agenda.team_ref) ||
            String(s.team_name) === String(agenda.sector_name)
          );

          if (scheduleInfo) {
            const detailSchedule = await api(`/shift-schedules/${scheduleInfo.id}/`);
            setReportSchedule(detailSchedule);

            let total = 0, present = 0, absent = 0, pending = 0;
            const processMembers = (group, type) => {
              if (!group || !Array.isArray(group)) return;
              group.forEach(member => {
                total++;
                const isChecked = detailSchedule.checked_members && detailSchedule.checked_members[`${type}_${member.id}`] !== undefined;
                const is_absent = isChecked ? !!member.is_absent : null;
                if (is_absent === true) absent++;
                else if (is_absent === false) present++;
                else pending++;
              });
            };
            processMembers(detailSchedule.members?.chiefs, "CHIEF");
            processMembers(detailSchedule.members?.agents, "AGENT");
            processMembers(detailSchedule.members?.supports, "SUPPORT");

            setAttendanceStats({ total, present, absent, pending, loaded: true });
          } else {
            setReportSchedule(null);
            setAttendanceStats({ total: 0, present: 0, absent: 0, pending: 0, loaded: true });
          }
        }
      } catch (err) {
        setAttendanceError("Não foi possível carregar a frequência.");
      }
    };
    loadAttendance();
  }, [form?.operation_date, form?.team, agenda, location.key]);

  const updateAction = (idx, field, value) => {
    setForm(prev => {
      const nextActions = [...prev.actions];
      nextActions[idx] = { ...nextActions[idx], [field]: value };
      return { ...prev, actions: nextActions };
    });
  };

  const addAction = () => {
    setForm((current) => {
      const baseAction = current.actions?.[0] || emptyAction;
      return {
        ...current,
        actions: [
          ...(current.actions || []),
          {
            ...emptyAction,
            agenda: current.agenda,
            source_id: "",
            __userCreated: true,
            place_action: baseAction.place_action || "",
            institution_name: baseAction.institution_name || "",
            equipment_materials_removed: baseAction.equipment_materials_removed || "",
            distribution_materials_removed: baseAction.distribution_materials_removed || "",
          },
        ],
      };
    });
  };

  const removeAction = (index) => {
    if (index === 0) return;
    setForm((current) => ({
      ...current,
      actions: current.actions.filter((_, actionIndex) => actionIndex !== index),
    }));
  };

  const updateField = (field, value) => {
    setForm(prev => ({ ...prev, [field]: value }));
  };

  const handleToggleExceptionalOccurrence = (value) => {
    const isYes = value === "true";
    setForm(prev => ({
      ...prev,
      has_exceptional_occurrence: isYes,
    }));
  };

  const handleSaveDraft = async (e, silent = false) => {
    if (e) e.preventDefault();
    if (isSaving || isSubmitting) return;
    setIsSaving(true);
    if (!silent) {
      setMessage("");
      setError("");
    }

    try {
      if (form.has_exceptional_occurrence) {
        if (!form.exceptional_occurrence_type) throw new Error("Preencha o Tipo de ocorrência excepcional.");
        if (!String(form.exceptional_occurrence_description || "").trim()) throw new Error("Preencha a Descrição da ocorrência excepcional.");
        if (!String(form.exceptional_occurrence_actions_taken || "").trim()) throw new Error("Preencha as Providências adotadas.");
        if (!form.exceptional_occurrence_impact) throw new Error("Preencha o Impacto na atividade.");
      }

      const isExisting = isEdit || !!form.id;
      const targetId = form.id || id;
      const payload = normalizePayload(form, "DRAFT");
      let saved;

      if (isExisting) {
        saved = await api(`/education-reports/${targetId}/`, { method: "PUT", body: JSON.stringify(payload) });
      } else {
        saved = await api(`/education-reports/`, { method: "POST", body: JSON.stringify(payload) });
      }

      if (!silent) setMessage("Rascunho salvo com sucesso.");

      setForm(prev => ({
        ...prev,
        ...saved,
        actions: saved.actions?.length ? saved.actions : prev.actions
      }));

      if (!isExisting && !silent) {
        navigate(`/app/relatorios/${saved.id}/editar`, { replace: true });
      }
      return saved.id;
    } catch (err) {
      if (!silent) setError(`⚠️ Não foi possível salvar o rascunho\n\nMotivo:\n${err.message}`);
      throw err; // Re-throw to allow submitFinal to catch it
    } finally {
      setIsSaving(false);
    }
  };

  const handleSubmitForReview = async (e) => {
    e.preventDefault();
    if (isSubmitting || isSaving) return;
    setIsSubmitting(true);
    setMessage("");
    setError("");

    try {
      // 1. Validar relatório
      const missingFields = [];
      if (!form.operation_date) missingFields.push("Data da Operação");
      if (!form.team) missingFields.push("Equipe Executora");
      if (!form.accessibility_conditions_met) missingFields.push("Condições de Acessibilidade");

      getValidatableActions(form.actions).forEach(({ action, index }) => {
        if (isStreetActionAgenda(agenda) && (!action.type_action || action.type_action === "Selecione a ação")) {
          missingFields.push(`Ação ${index + 1}: Ação Definida pelo Chefe`);
        }
      });

      if (form.has_exceptional_occurrence) {
        if (!form.exceptional_occurrence_type) missingFields.push("Tipo de ocorrência excepcional");
        if (!String(form.exceptional_occurrence_description || "").trim()) missingFields.push("Descrição da ocorrência excepcional");
        if (!String(form.exceptional_occurrence_actions_taken || "").trim()) missingFields.push("Providências adotadas");
        if (!form.exceptional_occurrence_impact) missingFields.push("Impacto na atividade");
      }

      if (missingFields.length > 0) {
        throw new Error(`Existem campos obrigatórios não preenchidos:\n${missingFields.map(f => `- ${f}`).join('\n')}`);
      }

      // 2. Validar frequência
      if (agenda.service_order_mode !== "DESIGNATED") {
        if (attendanceStats.pending > 0) {
          throw new Error("Defina a frequência de todos os participantes antes de enviar o relatório.");
        }
      }

      // 3. Finalizar frequência TEAM com markReported=true
      if (agenda.service_order_mode !== "DESIGNATED" && reportSchedule) {
        try {
          await api(`/shift-schedules/${reportSchedule.id}/report-attendance/`, { method: "POST" });
        } catch (err) {
          throw new Error("Não foi possível registrar/finalizar a frequência.");
        }
      }

      // 4. Salvar como DRAFT
      let savedId;
      try {
        savedId = await handleSaveDraft(null, true); // silent save
      } catch (err) {
        throw new Error("Não foi possível salvar o relatório.");
      }

      // 5. Submit for review
      try {
        await api(`/education-reports/${savedId}/submit-for-review/`, { method: "POST" });
      } catch (err) {
        throw new Error("Relatório salvo, mas não foi possível enviá-lo para validação.");
      }

      // 6. Navegar para detalhe
      navigate(`/app/relatorios/${savedId}`, { replace: true });

    } catch (err) {
      setError(`⚠️ Não foi possível enviar o relatório\n\nMotivo:\n${err.message}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  if (loading) return <MobileLoadingState message="Carregando formulário..." />;
  if (error && !form) return <MobileErrorState message={error} onRetry={() => window.location.reload()} />;
  if (!form) return null;

  const isStreetAction = isStreetActionAgenda(agenda);
  const isPublicRequest = agenda?.origin === "PUBLIC_FORM";
  const showEstimatedPublic = !isStreetAction || isPublicRequest;

  const readOnlyIdentity = Boolean(agenda);

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

      <div className="mobile-card" style={{ padding: '20px' }}>
        <h3 style={{ margin: '0 0 16px', color: '#0f172a', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <FileText size={20} style={{ color: 'var(--brand-primary)' }}/>
          {isEdit ? "Editar Relatório Técnico" : "Novo Relatório Técnico"}
        </h3>

        {isEdit && form.status === "RETURNED" && (
          <div className="mobile-alert mobile-alert-warning" style={{ marginBottom: '16px' }}>
            <span style={{ fontWeight: '600', fontSize: '13px' }}>
              Status: Devolvido para Correção
            </span>
            {form.review_notes && (
              <div style={{ marginTop: '8px', padding: '10px', backgroundColor: '#fff', borderRadius: '6px', fontSize: '13px', color: '#b45309', border: '1px solid #fed7aa' }}>
                <strong>Motivo da devolução:</strong><br />
                {form.review_notes}
              </div>
            )}
          </div>
        )}

        {isEdit && form.status !== "RETURNED" && (
          <div className="mobile-alert mobile-alert-info" style={{ marginBottom: '16px' }}>
            <span style={{ fontWeight: '600', fontSize: '13px' }}>
              Status: Rascunho
            </span>
          </div>
        )}

        {message && (
          <div className="mobile-alert mobile-alert-success" style={{ marginBottom: '16px', backgroundColor: '#dcfce7', color: '#166534', border: '1px solid #bbf7d0' }}>
            {message}
          </div>
        )}

        {error && (
          <div className="mobile-alert mobile-alert-danger" style={{ marginBottom: '16px', backgroundColor: '#fee2e2', color: '#991b1b', border: '1px solid #fecaca', whiteSpace: 'pre-wrap' }}>
            {error}
          </div>
        )}

        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <label style={{ display: 'flex', flexDirection: 'column', gap: '4px', fontSize: '14px', fontWeight: '500', color: '#334155' }}>
            Protocolo/Agenda
            <input
              type="text"
              value={agenda ? agenda.id : form.agenda || ""}
              readOnly
              style={{ padding: '10px', borderRadius: '8px', border: '1px solid #cbd5e1', backgroundColor: '#f1f5f9', color: '#64748b' }}
            />
          </label>
          <label style={{ display: 'flex', flexDirection: 'column', gap: '4px', fontSize: '14px', fontWeight: '500', color: '#334155' }}>
            Data da Operação
            <input
              type="date"
              value={form.operation_date || ""}
              onChange={e => updateField("operation_date", e.target.value)}
              readOnly={readOnlyIdentity}
              style={{ padding: '10px', borderRadius: '8px', border: '1px solid #cbd5e1', backgroundColor: readOnlyIdentity ? '#f1f5f9' : '#fff' }}
            />
          </label>
          <label style={{ display: 'flex', flexDirection: 'column', gap: '4px', fontSize: '14px', fontWeight: '500', color: '#334155' }}>
            Equipe Executora
            <input
              type="text"
              value={form.team || ""}
              onChange={e => updateField("team", e.target.value)}
              readOnly={readOnlyIdentity}
              style={{ padding: '10px', borderRadius: '8px', border: '1px solid #cbd5e1', backgroundColor: readOnlyIdentity ? '#f1f5f9' : '#fff' }}
            />
          </label>
          <label style={{ display: 'flex', flexDirection: 'column', gap: '4px', fontSize: '14px', fontWeight: '500', color: '#334155' }}>
            Modalidade
            <input
              type="text"
              value={isStreetAction ? "Ação de Rua" : "Palestra"}
              readOnly
              style={{ padding: '10px', borderRadius: '8px', border: '1px solid #cbd5e1', backgroundColor: '#f1f5f9', color: '#64748b' }}
            />
          </label>
        </div>
      </div>

      <div className="mobile-card" style={{ padding: '20px' }}>
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '12px', marginBottom: '16px' }}>
          <div>
            <h4 style={{ margin: 0, color: '#0f172a' }}>Ações realizadas</h4>
            <p style={{ margin: '4px 0 0', fontSize: '12px', color: '#64748b' }}>
              Registre separadamente cada ação realizada nesta atividade.
            </p>
          </div>
          <button
            type="button"
            onClick={addAction}
            style={{ display: 'flex', alignItems: 'center', gap: '6px', padding: '9px 10px', borderRadius: '8px', border: '1px solid #cbd5e1', background: '#fff', color: '#0f172a', fontWeight: '700', cursor: 'pointer', whiteSpace: 'nowrap' }}
          >
            <Plus size={16} /> Adicionar
          </button>
        </div>

        {isStreetAction && (
          <div style={{ marginBottom: '16px' }}>
            <h5 style={{ fontSize: '13px', margin: '0 0 8px', color: '#64748b' }}>Detalhes da Ação de Rua (Ordem de Serviço)</h5>
            {(form.street_action_details || []).length > 0 ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {(form.street_action_details || []).map((detail, idx) => (
                  <div key={idx} style={{ padding: '8px 12px', background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: '6px', fontSize: '13px', color: '#334155' }}>
                    <strong>{detail.type ? streetActionTypeLabel(detail.type) : `Ação ${idx + 1}`}</strong>
                    {showEstimatedPublic && (
                      <div style={{ marginTop: '2px', color: '#64748b', fontSize: '12px' }}>
                        {detail.public ? `Público estimado: ${detail.public}` : "Público estimado não informado"}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <div style={{ padding: '8px 12px', background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: '6px', fontSize: '13px', color: '#64748b' }}>
                Nenhum tipo de ação pré-cadastrado na OS.
              </div>
            )}
          </div>
        )}

        <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
          {(form.actions || []).map((action, index) => {
            const isUserCreated = Boolean(action.__userCreated || index > 0);
            const sourceReadOnly = Boolean(agenda) && !isUserCreated;

            return (
              <div key={`${action.id || 'action'}-${index}`} style={{ padding: '16px', border: '1px solid #e2e8f0', borderRadius: '10px', background: '#f8fafc' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '12px', marginBottom: '14px' }}>
                  <div>
                    <strong style={{ color: '#0f172a' }}>{`AÇÃO ${String(index + 1).padStart(2, '0')}`}</strong>
                    <div style={{ marginTop: '2px', fontSize: '11px', color: '#64748b' }}>
                      {sourceReadOnly ? 'Dados principais carregados da Ordem de Serviço' : 'Ação adicionada pelo chefe'}
                    </div>
                  </div>
                  {index > 0 && (
                    <button
                      type="button"
                      onClick={() => removeAction(index)}
                      aria-label={`Remover ação ${index + 1}`}
                      style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', width: '36px', height: '36px', borderRadius: '8px', border: '1px solid #fecaca', background: '#fff', color: '#b91c1c', cursor: 'pointer' }}
                    >
                      <Trash2 size={17} />
                    </button>
                  )}
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                  {!isStreetAction && (
                    <label style={{ display: 'flex', flexDirection: 'column', gap: '4px', fontSize: '14px', fontWeight: '500', color: '#334155' }}>
                      Instituição / Local
                      <input
                        type="text"
                        value={action.institution_name || ""}
                        onChange={e => updateAction(index, "institution_name", e.target.value)}
                        readOnly={sourceReadOnly}
                        title={sourceReadOnly ? "Preenchido automaticamente pela Ordem de Serviço" : undefined}
                        style={{ padding: '10px', borderRadius: '8px', border: '1px solid #cbd5e1', backgroundColor: sourceReadOnly ? '#f1f5f9' : '#fff', color: '#475569' }}
                      />
                    </label>
                  )}

                  <label style={{ display: 'flex', flexDirection: 'column', gap: '4px', fontSize: '14px', fontWeight: '500', color: '#334155' }}>
                    Endereço do Local
                    <input
                      type="text"
                      value={action.place_action || ""}
                      onChange={e => updateAction(index, "place_action", e.target.value)}
                      readOnly={sourceReadOnly}
                      title={sourceReadOnly ? "Preenchido automaticamente pela Ordem de Serviço" : undefined}
                      style={{ padding: '10px', borderRadius: '8px', border: '1px solid #cbd5e1', backgroundColor: sourceReadOnly ? '#f1f5f9' : '#fff', color: '#475569' }}
                    />
                  </label>

                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                    <label style={{ display: 'flex', flexDirection: 'column', gap: '4px', fontSize: '14px', fontWeight: '500', color: '#334155' }}>
                      Horário Inicial
                      <input
                        type="time"
                        value={action.start_time || ""}
                        onChange={e => updateAction(index, "start_time", e.target.value)}
                        readOnly={sourceReadOnly}
                        style={{ padding: '10px', borderRadius: '8px', border: '1px solid #cbd5e1', backgroundColor: sourceReadOnly ? '#f1f5f9' : '#fff' }}
                      />
                    </label>
                    <label style={{ display: 'flex', flexDirection: 'column', gap: '4px', fontSize: '14px', fontWeight: '500', color: '#334155' }}>
                      Horário Final
                      <input
                        type="time"
                        value={action.final_hour || ""}
                        onChange={e => updateAction(index, "final_hour", e.target.value)}
                        readOnly={sourceReadOnly}
                        style={{ padding: '10px', borderRadius: '8px', border: '1px solid #cbd5e1', backgroundColor: sourceReadOnly ? '#f1f5f9' : '#fff' }}
                      />
                    </label>
                  </div>

                  {isStreetAction && (
                    <label style={{ display: 'flex', flexDirection: 'column', gap: '4px', fontSize: '14px', fontWeight: '500', color: '#334155' }}>
                      Ação Definida pelo Chefe
                      <select
                        value={action.type_action || ""}
                        onChange={e => updateAction(index, "type_action", e.target.value)}
                        disabled={sourceReadOnly && Boolean(action.type_action)}
                        style={{ padding: '10px', borderRadius: '8px', border: '1px solid #cbd5e1', backgroundColor: sourceReadOnly && action.type_action ? '#f1f5f9' : '#fff' }}
                      >
                        <option value="">Selecione</option>
                        {streetActionTypeOptions.map((opt) => (
                          <option key={opt} value={opt}>{streetActionTypeLabel(opt)}</option>
                        ))}
                        {action.type_action && !streetActionTypeOptions.includes(action.type_action) && (
                          <option value={action.type_action}>{streetActionTypeLabel(action.type_action)}</option>
                        )}
                      </select>
                    </label>
                  )}

                  {showEstimatedPublic && index === 0 && (
                    <label style={{ display: 'flex', flexDirection: 'column', gap: '4px', fontSize: '14px', fontWeight: '500', color: '#334155' }}>
                      Público Estimado (Solicitação)
                      <input
                        type="number"
                        value={action.approach ?? ""}
                        readOnly
                        title="Preenchido automaticamente a partir da solicitação"
                        style={{ padding: '10px', borderRadius: '8px', border: '1px solid #cbd5e1', backgroundColor: '#f1f5f9', color: '#64748b' }}
                      />
                    </label>
                  )}

                  <label style={{ display: 'flex', flexDirection: 'column', gap: '4px', fontSize: '14px', fontWeight: '500', color: '#334155' }}>
                    {!isStreetAction ? "Abordados em Palestras" : "Número de Abordagens"}
                    <input
                      type="number"
                      min="0"
                      value={!isStreetAction ? (action.approached_lectures ?? "") : (action.approached_actions ?? "")}
                      onChange={e => updateAction(index, !isStreetAction ? "approached_lectures" : "approached_actions", e.target.value)}
                      style={{ padding: '10px', borderRadius: '8px', border: '1px solid #cbd5e1', background: '#fff' }}
                    />
                  </label>

                  <div style={{ paddingTop: '4px', borderTop: '1px solid #e2e8f0' }}>
                    <h5 style={{ margin: '10px 0 12px', color: '#334155', fontSize: '13px' }}>Materiais desta ação</h5>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                      <label style={{ display: 'flex', flexDirection: 'column', gap: '4px', fontSize: '14px', fontWeight: '500', color: '#334155' }}>
                        Material Distribuído nesta Ação (Kits / Categorias)
                        <textarea
                          value={action.distribution_materials_distributed || ""}
                          onChange={e => updateAction(index, "distribution_materials_distributed", e.target.value)}
                          placeholder={'Ex:\nCATEGORIA 1 - ITEM: 10\nCATEGORIA 2 - ITEM: 5'}
                          style={{ padding: '10px', borderRadius: '8px', border: '1px solid #cbd5e1', minHeight: '100px', fontFamily: 'inherit', whiteSpace: 'pre-wrap', background: '#fff' }}
                        />
                      </label>

                      <label style={{ display: 'flex', flexDirection: 'column', gap: '4px', fontSize: '14px', fontWeight: '500', color: '#334155' }}>
                        Equipamentos (Opcional)
                        <textarea
                          value={action.equipment_materials_distributed || ""}
                          onChange={e => updateAction(index, "equipment_materials_distributed", e.target.value)}
                          style={{ padding: '10px', borderRadius: '8px', border: '1px solid #cbd5e1', minHeight: '60px', fontFamily: 'inherit', whiteSpace: 'pre-wrap', background: '#fff' }}
                        />
                      </label>
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        <label style={{ display: 'flex', flexDirection: 'column', gap: '4px', fontSize: '14px', fontWeight: '500', color: '#334155', marginTop: '16px' }}>
          Condições de Acessibilidade
          <select
            value={form.accessibility_conditions_met || ""}
            onChange={e => updateField("accessibility_conditions_met", e.target.value)}
            style={{ padding: '10px', borderRadius: '8px', border: '1px solid #cbd5e1', backgroundColor: '#fff' }}
          >
            <option value="">Selecione</option>
            <option value="YES">Sim</option>
            <option value="NO">Não</option>
          </select>
        </label>
      </div>

      <div className="mobile-card" style={{ padding: '20px' }}>
        <h4 style={{ margin: '0 0 16px', color: '#0f172a' }}>Ocorrência Excepcional</h4>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <label style={{ display: 'flex', flexDirection: 'column', gap: '4px', fontSize: '14px', fontWeight: '500', color: '#334155' }}>
            Teve ocorrência excepcional?
            <select
              value={form.has_exceptional_occurrence ? "true" : "false"}
              onChange={e => handleToggleExceptionalOccurrence(e.target.value)}
              style={{ padding: '10px', borderRadius: '8px', border: '1px solid #cbd5e1', backgroundColor: '#fff' }}
            >
              <option value="false">Não</option>
              <option value="true">Sim</option>
            </select>
          </label>

          {form.has_exceptional_occurrence && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', padding: '12px', background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: '8px' }}>
              <label style={{ display: 'flex', flexDirection: 'column', gap: '4px', fontSize: '14px', fontWeight: '500', color: '#334155' }}>
                Tipo de Ocorrência
                <select
                  value={form.exceptional_occurrence_type || ""}
                  onChange={e => updateField("exceptional_occurrence_type", e.target.value)}
                  style={{ padding: '10px', borderRadius: '8px', border: '1px solid #cbd5e1', backgroundColor: '#fff' }}
                >
                  <option value="">Selecione</option>
                  <option value="VEHICLE_BREAKDOWN">Quebra de Viatura</option>
                  <option value="WORK_ACCIDENT">Acidente de Trabalho (Efetivo)</option>
                  <option value="WEATHER">Condição Climática</option>
                  <option value="MATERIAL_SHORTAGE">Falta de Material</option>
                  <option value="OTHER">Outros</option>
                </select>
              </label>

              <label style={{ display: 'flex', flexDirection: 'column', gap: '4px', fontSize: '14px', fontWeight: '500', color: '#334155' }}>
                Descrição da Ocorrência
                <textarea
                  value={form.exceptional_occurrence_description || ""}
                  onChange={e => updateField("exceptional_occurrence_description", e.target.value)}
                  style={{ padding: '10px', borderRadius: '8px', border: '1px solid #cbd5e1', minHeight: '80px', fontFamily: 'inherit' }}
                />
              </label>

              <label style={{ display: 'flex', flexDirection: 'column', gap: '4px', fontSize: '14px', fontWeight: '500', color: '#334155' }}>
                Providências Adotadas
                <textarea
                  value={form.exceptional_occurrence_actions_taken || ""}
                  onChange={e => updateField("exceptional_occurrence_actions_taken", e.target.value)}
                  style={{ padding: '10px', borderRadius: '8px', border: '1px solid #cbd5e1', minHeight: '80px', fontFamily: 'inherit' }}
                />
              </label>

              <label style={{ display: 'flex', flexDirection: 'column', gap: '4px', fontSize: '14px', fontWeight: '500', color: '#334155' }}>
                Impacto na Atividade
                <select
                  value={form.exceptional_occurrence_impact || ""}
                  onChange={e => updateField("exceptional_occurrence_impact", e.target.value)}
                  style={{ padding: '10px', borderRadius: '8px', border: '1px solid #cbd5e1', backgroundColor: '#fff' }}
                >
                  <option value="">Selecione</option>
                  <option value="NONE">Nenhum</option>
                  <option value="PARTIAL">Parcial (atividade continuou com restrições)</option>
                  <option value="TOTAL">Total (atividade suspensa ou cancelada)</option>
                </select>
              </label>
            </div>
          )}
        </div>
      </div>

      <div className="mobile-card" style={{ padding: '20px' }}>
        <h4 style={{ margin: '0 0 16px', color: '#0f172a' }}>Observações</h4>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <label style={{ display: 'flex', flexDirection: 'column', gap: '4px', fontSize: '14px', fontWeight: '500', color: '#334155' }}>
            Dados e Observações Gerais
            <textarea
              value={form.general_observations || ""}
              onChange={e => updateField("general_observations", e.target.value)}
              placeholder="Digite suas observações gerais..."
              style={{ padding: '10px', borderRadius: '8px', border: '1px solid #cbd5e1', minHeight: '80px', fontFamily: 'inherit' }}
            />
          </label>
          <label style={{ display: 'flex', flexDirection: 'column', gap: '4px', fontSize: '14px', fontWeight: '500', color: '#334155' }}>
            Observação de Ocorrência (se houver)
            <textarea
              value={form.occurrence_observation || ""}
              onChange={e => updateField("occurrence_observation", e.target.value)}
              style={{ padding: '10px', borderRadius: '8px', border: '1px solid #cbd5e1', minHeight: '60px', fontFamily: 'inherit' }}
            />
          </label>
          <label style={{ display: 'flex', flexDirection: 'column', gap: '4px', fontSize: '14px', fontWeight: '500', color: '#334155' }}>
            Contato Recebido
            <textarea
              value={form.contact_received || ""}
              readOnly
              title="Preenchido automaticamente pela Ordem de Serviço"
              style={{ padding: '10px', borderRadius: '8px', border: '1px solid #cbd5e1', minHeight: '60px', fontFamily: 'inherit', backgroundColor: '#f1f5f9', color: '#475569' }}
            />
          </label>
        </div>
      </div>

      <div
        className="mobile-card"
        style={{
          padding: '20px',
          border: '1px solid #f59e0b',
          backgroundColor: '#fffbeb'
        }}
      >
        <h4
          style={{
            margin: '0 0 6px',
            color: '#0a1e44',
            fontSize: '14px',
            fontWeight: '800'
          }}
        >
          FREQUÊNCIA DA EQUIPE
        </h4>

        <p
          style={{
            margin: '0 0 14px',
            color: '#64748b',
            fontSize: '12px'
          }}
        >
          Gerencie as presenças e faltas do efetivo lançado para esta atividade.
        </p>

        {attendanceError ? (
          <div
            style={{
              padding: '10px',
              marginBottom: '12px',
              borderRadius: '8px',
              backgroundColor: '#fee2e2',
              color: '#991b1b',
              fontSize: '12px'
            }}
          >
            {attendanceError}
          </div>
        ) : null}

        {attendanceStats.loaded && (
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(2, 1fr)',
              gap: '8px',
              marginBottom: '14px'
            }}
          >
            <div style={{ padding: '10px', borderRadius: '8px', backgroundColor: '#fff' }}>
              <strong style={{ display: 'block', fontSize: '18px', color: '#0f172a' }}>
                {attendanceStats.total}
              </strong>
              <span style={{ fontSize: '11px', color: '#64748b' }}>Participantes</span>
            </div>

            <div style={{ padding: '10px', borderRadius: '8px', backgroundColor: '#fff' }}>
              <strong style={{ display: 'block', fontSize: '18px', color: '#166534' }}>
                {attendanceStats.present}
              </strong>
              <span style={{ fontSize: '11px', color: '#64748b' }}>Presentes</span>
            </div>

            <div style={{ padding: '10px', borderRadius: '8px', backgroundColor: '#fff' }}>
              <strong style={{ display: 'block', fontSize: '18px', color: '#991b1b' }}>
                {attendanceStats.absent}
              </strong>
              <span style={{ fontSize: '11px', color: '#64748b' }}>Ausentes</span>
            </div>

            <div style={{ padding: '10px', borderRadius: '8px', backgroundColor: '#fff' }}>
              <strong style={{ display: 'block', fontSize: '18px', color: '#92400e' }}>
                {attendanceStats.pending}
              </strong>
              <span style={{ fontSize: '11px', color: '#64748b' }}>Pendentes</span>
            </div>
          </div>
        )}

        <button
          type="button"
          className="mobile-btn mobile-btn-primary"
          style={{
            width: '100%',
            backgroundColor: '#fbbf24',
            color: '#0f172a',
            border: 'none',
            fontWeight: '800'
          }}
          disabled={
            agenda?.service_order_mode !== "DESIGNATED" &&
            !reportSchedule?.id
          }
          onClick={() => {
            if (!agenda?.id) return;

            if (agenda.service_order_mode === "DESIGNATED") {
              navigate(`/app/frequencia/agenda/${agenda.id}/editar`);
              return;
            }

            if (reportSchedule?.id) {
              navigate(`/app/frequencia/escala/${reportSchedule.id}/editar`);
            }
          }}
        >
          Gerenciar Frequência
        </button>

        {agenda?.service_order_mode !== "DESIGNATED" &&
          attendanceStats.loaded &&
          !reportSchedule?.id && (
            <p
              style={{
                margin: '10px 0 0',
                fontSize: '11px',
                color: '#92400e'
              }}
            >
              Não foi possível localizar a escala desta equipe.
            </p>
          )}
      </div>

      <div style={{ padding: '0 8px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
        <button
          className="mobile-btn mobile-btn-primary"
          disabled={isSaving || isSubmitting}
          onClick={handleSaveDraft}
          style={{ width: '100%', opacity: (isSaving || isSubmitting) ? 0.7 : 1, display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '8px', padding: '14px', borderRadius: '8px', backgroundColor: '#0f172a', color: '#fff', border: 'none', fontWeight: '600', fontSize: '16px' }}
        >
          <Save size={18} />
          {isSaving ? "Salvando..." : (isSubmitting ? "Enviando..." : "Salvar rascunho")}
        </button>

        <button
          className="mobile-btn mobile-btn-secondary"
          disabled={isSaving || isSubmitting}
          onClick={handleSubmitForReview}
          style={{ width: '100%', opacity: (isSaving || isSubmitting) ? 0.7 : 1, display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '8px', padding: '14px', borderRadius: '8px', backgroundColor: '#f1f5f9', color: '#0f172a', border: '1px solid #cbd5e1', fontWeight: '600', fontSize: '16px' }}
        >
          <Save size={18} />
          {isSubmitting ? "Enviando..." : "Enviar para validação"}
        </button>
      </div>
    </div>
  );
}
