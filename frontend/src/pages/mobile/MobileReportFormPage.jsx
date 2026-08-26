import React, { useState, useEffect } from "react";
import { useParams, useNavigate, useLocation } from "react-router-dom";
import { ArrowLeft, CheckCircle2, FileText, MessageCircle, Plus, Save, Trash2 } from "lucide-react";
import { api } from "../../api/client.js";
import { STREET_ACTION_ID } from "../../utils/constants";
import { STREET_ACTION_TYPE_OPTIONS, streetActionTypeLabel } from "../../utils/streetActionTypes.js";
import { filterOperationalEducationActionTypes, getAgendaOperationalActionTypeName } from "../../utils/actionTypeOptions.js";
import {
  EDUCATION_ACTION_AGE_RANGE_OPTIONS,
  REQUESTER_ENTITY_KIND_OPTIONS,
  REQUESTER_ENTITY_NATURE_OPTIONS,
  agreementIndicatorLabel,
  buildAgreementFieldsFromAgenda,
  getDisplayedAgreementIndicator,
} from "../../utils/agreementIndicators.js";
import MobileLoadingState from "../../components/mobile/MobileLoadingState.jsx";
import MobileErrorState from "../../components/mobile/MobileErrorState.jsx";
import MobileAttendanceSummaryCard from "../../components/mobile/MobileAttendanceSummaryCard.jsx";
import { getValidatableActions } from "../technicalReportsActionHelpers.js";
import { buildReportShareSummary } from "../../utils/reportShareSummary.js";
import { executeShare } from "../../utils/handleShareReport.js";
import { agendaPk } from "../../utils/reportPayload.js";

const numberFields = ["approach"];
const streetActionTypeOptions = STREET_ACTION_TYPE_OPTIONS;
const agreementFieldNames = new Set(["requester_entity_kind", "requester_entity_nature", "age_range"]);
const legacyStreetActionTypeMap = {
  BAR: "Bares",
  EMPRESA: "Empresas",
  ESCOLA: "Escolas",
  ESPORTES: "Praças Esportivas",
  EVENTO: "Eventos",
  FESTA_BAIRRO: "Eventos",
  PARQUE: "Praças/Parques Públicos",
  PEDAGIO: "Pedágio",
  PRAIA: "Praia",
  SHOPPING: "Shopping/Centro Comerciais",
  UNIVERSIDADE: "Universidades",
  PONTO_TURISTICO: "Pontos turísticos",
  SINDICATO: "Outros",
};

function nullable(value) {
  if (value === "" || value === undefined) return null;
  return value;
}

function normalizeStreetActionType(value) {
  const normalized = String(value || "").trim();
  if (!normalized) return "";
  return legacyStreetActionTypeMap[normalized] || normalized;
}

function buildActionPayload(action, formAgenda) {
  return {
    ...action,
    action_mode: action.action_mode || (
      streetActionTypeOptions.includes(normalizeStreetActionType(action.type_action))
        ? "STREET"
        : "LECTURE"
    ),
    agenda: agendaPk(action.agenda, formAgenda),
    type_action: normalizeStreetActionType(action.type_action),
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
    agenda: agendaPk(form.agenda),
    management_id: nullable(form.management_id),
    approximate_public: nullable(form.approximate_public),
    lat: nullable(form.lat),
    lng: nullable(form.lng),
    general_observations: form.general_observations || "",
    has_exceptional_occurrence: Boolean(form.has_exceptional_occurrence),
    exceptional_occurrence_type: form.has_exceptional_occurrence ? (form.exceptional_occurrence_type || "") : "",
    exceptional_occurrence_description: form.has_exceptional_occurrence ? (form.exceptional_occurrence_description || "") : "",
    exceptional_occurrence_actions_taken: form.has_exceptional_occurrence ? (form.exceptional_occurrence_actions_taken || "") : "",
    exceptional_occurrence_impact: form.has_exceptional_occurrence
      ? ({ NONE: "NO_IMPACT", TOTAL: "INTERRUPTED" }[form.exceptional_occurrence_impact] || form.exceptional_occurrence_impact || "")
      : "",
    actions: getValidatableActions(form.actions).map(({ action }) => buildActionPayload(action, form.agenda)),
  };
}

const emptyAction = {
  agenda: "",
  source_id: "",
  place_action: "",
  type_action: "",
  type_audience: "",
  requester_entity_kind: "",
  requester_entity_nature: "",
  age_range: "",
  agreement_indicator: "",
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

function actionMode(action, agenda, index) {
  if (index === 0) return isStreetActionAgenda(agenda) ? "STREET" : "LECTURE";
  if (action?.action_mode === "STREET" || action?.action_mode === "LECTURE") return action.action_mode;
  return streetActionTypeOptions.includes(normalizeStreetActionType(action?.type_action)) ? "STREET" : "LECTURE";
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


function parseMaterialRows(value = "") {
  return String(value || "")
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => {
      const normalized = line.replace(/\[\s*\]/g, "|").replace(/\s+-\s+/g, " | ");
      const [rawName, rawQuantity = ""] = normalized.split("|").map((part) => part.trim());
      const quantity = rawQuantity.match(/\d+/)?.[0] || "";
      return { name: rawName, quantity };
    })
    .filter((item) => item.name);
}

function serializeMaterialRows(rows = []) {
  return rows
    .filter((item) => item.name)
    .map((item) => {
      const quantity =
        item.quantity !== "" &&
        item.quantity !== undefined &&
        item.quantity !== null
          ? item.quantity
          : "";
      return `${item.name} | ${quantity}`;
    })
    .join("\n");
}

function serializeBlankMaterialRows(rows = []) {
  return rows
    .filter((item) => item.name)
    .map((item) => `${item.name} | `)
    .join("\n");
}

function extractMaterialCategories(agenda = {}) {
  const dynamics = [];
  const supports = [];
  const kits = [];

  const add = (list, name, quantity) => {
    if (!name) return;
    const normalizedName = String(name).trim();
    if (!normalizedName) return;

    const existing = list.find(
      (item) => String(item.name).trim().toLowerCase() === normalizedName.toLowerCase()
    );
    const validQuantity =
      quantity !== null && quantity !== undefined && quantity !== ""
        ? Number(quantity)
        : "";

    if (!existing) {
      list.push({ name: normalizedName, quantity: validQuantity });
    } else if (validQuantity !== "" && existing.quantity === "") {
      existing.quantity = validQuantity;
    }
  };

  for (let index = 1; index <= 7; index += 1) {
    add(supports, agenda[`kit_${index}`], agenda[`kit_${index}_quantity`]);
    add(kits, agenda[`material_${index}`], "");
  }

  if (agenda.materials?.length) {
    agenda.materials.forEach((item) => {
      add(dynamics, item.dynamic_name, item.quantity);
      add(kits, item.kit_name, item.quantity);
      add(supports, item.material_name, item.quantity);
    });
  }

  return { dynamics, supports, kits };
}

function sumActionDistributedMaterials(actions = [], materialRows = []) {
  const totals = {};

  materialRows.forEach((item) => {
    totals[item.name.toLowerCase()] = { name: item.name, quantity: 0 };
  });

  actions.forEach((action) => {
    const value =
      action.distribution_materials_distributed ||
      serializeBlankMaterialRows(materialRows);

    parseMaterialRows(value).forEach((item) => {
      const key = item.name.toLowerCase();
      const quantity = parseInt(item.quantity, 10) || 0;

      if (!totals[key]) {
        totals[key] = { name: item.name, quantity: 0 };
      }
      totals[key].quantity += quantity;
    });
  });

  return serializeMaterialRows(Object.values(totals));
}

function MobileMaterialQuantityEditor({ value, onChange }) {
  const rows = parseMaterialRows(value);

  const updateRow = (rowIndex, quantity) => {
    const nextRows = rows.map((row, index) =>
      index === rowIndex ? { ...row, quantity } : row
    );
    onChange(serializeMaterialRows(nextRows));
  };

  if (!rows.length) {
    return (
      <div
        style={{
          padding: "10px",
          borderRadius: "8px",
          border: "1px solid #e2e8f0",
          background: "#f8fafc",
          color: "#64748b",
          fontSize: "12px",
        }}
      >
        Nenhum material de distribuição vinculado a esta Ordem de Serviço.
      </div>
    );
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
      {rows.map((row, rowIndex) => (
        <label
          key={`${row.name}-${rowIndex}`}
          style={{
            display: "grid",
            gridTemplateColumns: "1fr 90px",
            alignItems: "center",
            gap: "10px",
            padding: "10px",
            borderRadius: "8px",
            border: "1px solid #e2e8f0",
            background: "#fff",
          }}
        >
          <span style={{ fontSize: "13px", fontWeight: "600", color: "#334155" }}>
            {row.name}
          </span>
          <input
            type="number"
            min="0"
            step="1"
            placeholder="0"
            value={row.quantity}
            onChange={(event) => updateRow(rowIndex, event.target.value)}
            style={{
              width: "100%",
              boxSizing: "border-box",
              padding: "8px",
              borderRadius: "7px",
              border: "1px solid #cbd5e1",
            }}
          />
        </label>
      ))}
    </div>
  );
}

function hydrateActionFromAgenda(action = {}, agenda = {}, actionTypes = [], isFirstAction = false) {
  const resolvedAgendaPk = agendaPk(action.agenda, agenda);
  const sourceAgendaPk = agendaPk(agenda);
  if (action.__userCreated) {
    return {
      ...emptyAction,
      ...action,
      agenda: resolvedAgendaPk || "",
      source_id: "",
      __userCreated: true,
    };
  }
  const inheritAgendaFields = isFirstAction;
  const isStreetAction = isStreetActionAgenda(agenda);
  const inheritedAgreementFields = !isStreetAction && inheritAgendaFields ? buildAgreementFieldsFromAgenda(agenda) : {};
  const inheritedStreetActionType = (agenda.street_action_details || [])
    .map((detail) => detail?.type)
    .find(Boolean) || agenda.action_type_ref_name || agenda.action_type || "";
  return {
    ...action,
    action_mode: isFirstAction ? (isStreetAction ? "STREET" : "LECTURE") : action.action_mode,
    agenda: resolvedAgendaPk || "",
    source_id: action.source_id || (sourceAgendaPk ? `agenda_action:${sourceAgendaPk}` : ""),
    place_action: action.place_action || (inheritAgendaFields ? getAgendaActionPlace(agenda) : ""),
    institution_name:
      action.institution_name ||
      (inheritAgendaFields ? (agenda.institution_location || agenda.location || "") : ""),
    type_action:
      normalizeStreetActionType(action.type_action) ||
      (inheritAgendaFields
        ? (isStreetAction
          ? normalizeStreetActionType(inheritedStreetActionType)
          : getAgendaOperationalActionTypeName(agenda, actionTypes))
        : ""),
    type_audience: action.type_audience || (inheritAgendaFields ? agenda.audience || "" : ""),
    requester_entity_kind: action.requester_entity_kind || inheritedAgreementFields.requester_entity_kind || "",
    requester_entity_nature: action.requester_entity_nature || inheritedAgreementFields.requester_entity_nature || "",
    age_range: action.age_range || inheritedAgreementFields.age_range || "",
    agreement_indicator: action.agreement_indicator || "",
    start_time:
      action.start_time ||
      (inheritAgendaFields ? agenda.start_time?.slice?.(0, 5) : "") ||
      "",
    final_hour:
      action.final_hour ||
      (inheritAgendaFields ? agenda.end_time?.slice?.(0, 5) : "") ||
      "",
    approach:
      action.approach !== undefined &&
      action.approach !== null &&
      action.approach !== ""
        ? action.approach
        : (inheritAgendaFields ? (agenda.quantity || 0) : ""),
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
  const [actionTypes, setActionTypes] = useState([]);
  const [isSaving, setIsSaving] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [message, setMessage] = useState("");
  const [sharePrompt, setSharePrompt] = useState({
    open: false,
    reportId: null,
    summary: "",
  });
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
          const [report, actionTypesResult] = await Promise.all([
            api(`/education-reports/${id}/`, { signal: controller.signal }),
            api("/action-types/?page_size=500", { signal: controller.signal }),
          ]);
          const loadedActionTypes = actionTypesResult.results || actionTypesResult || [];
          setActionTypes(loadedActionTypes);

          if (report.status !== "DRAFT" && report.status !== "RETURNED") {
            navigate(`/app/relatorios/${id}`, { replace: true });
            return;
          }

          const reportAgendaPk = agendaPk(report.agenda);
          const repAgenda = reportAgendaPk ? await api(`/agendas/${reportAgendaPk}/`, { signal: controller.signal }) : null;
          setAgenda(repAgenda);

          const resolvedDetails = report.street_action_details?.length
            ? report.street_action_details
            : (repAgenda?.street_action_details || []);

          setForm({
            ...report,
            agenda: reportAgendaPk || "",
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
                }, repAgenda || {}, loadedActionTypes, index === 0)
              );
            })()
          });
        } else {
          const [fetchedAgenda, actionTypesResult] = await Promise.all([
            api(`/agendas/${agendaId}/`, { signal: controller.signal }),
            api("/action-types/?page_size=500", { signal: controller.signal }),
          ]);
          const loadedActionTypes = actionTypesResult.results || actionTypesResult || [];
          setActionTypes(loadedActionTypes);

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
            }, fetchedAgenda, loadedActionTypes, true)],
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
            const detailSchedule = await api(
              `/shift-schedules/${scheduleInfo.id}/?agenda=${agenda.id}`
            );
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
    setForm((prev) => {
      const nextActions = [...prev.actions];
      nextActions[idx] = {
        ...nextActions[idx],
        [field]: value,
        ...(field === "action_mode" ? { type_action: "" } : {}),
        ...(agreementFieldNames.has(field) ? { agreement_indicator: "" } : {}),
      };

      const nextForm = { ...prev, actions: nextActions };

      if (field === "distribution_materials_distributed") {
        const categories = extractMaterialCategories(agenda || {});
        nextForm.distribution_materials_distributed =
          sumActionDistributedMaterials(nextActions, categories.kits);
      }

      return nextForm;
    });
  };

  const addAction = () => {
    setForm((current) => {
      const categories = extractMaterialCategories(agenda || {});
      const baseAction = current.actions?.[0] || emptyAction;

      let availableMaterials = categories.kits.filter(
        (item) => (parseInt(item.quantity, 10) || 0) > 0
      );

      if (!availableMaterials.length) {
        availableMaterials = parseMaterialRows(
          baseAction.distribution_materials_removed || ""
        ).filter((item) => (parseInt(item.quantity, 10) || 0) > 0);
      }

      return {
        ...current,
        actions: [
          ...(current.actions || []),
          {
            ...emptyAction,
            agenda: agendaPk(current.agenda) || "",
            source_id: "",
            __userCreated: true,
            action_mode: "STREET",
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

  const resetSharePrompt = () => {
    setSharePrompt({ open: false, reportId: null, summary: "" });
  };

  const closeSharePromptAndOpenReport = () => {
    const reportId = sharePrompt.reportId;
    resetSharePrompt();

    if (reportId) {
      navigate(`/app/relatorios/${reportId}`, { replace: true });
    }
  };

  const handleShareReport = async () => {
    const result = await executeShare(sharePrompt.summary, {
      navigatorShare:
        typeof navigator !== "undefined" && typeof navigator.share === "function"
          ? navigator.share.bind(navigator)
          : undefined,
      locationAssign: (url) => window.location.assign(url),
    });

    if (result.status === "shared") {
      closeSharePromptAndOpenReport();
      return;
    }

    if (result.status === "empty") {
      closeSharePromptAndOpenReport();
      return;
    }

    if (result.status === "cancelled") {
      // Usuário cancelou — modal permanece aberto
      return;
    }

    if (result.status === "redirected") {
      // Não executar navigate() depois de location.assign().
      // O redirecionamento externo já foi iniciado.
      return;
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
        const isStreetAction = actionMode(action, agenda, index) === "STREET";
        if (isStreetAction && (!action.type_action || action.type_action === "Selecione a ação")) {
          missingFields.push(`Ação ${index + 1}: Tipo da ação realizada *`);
        }
        if (!isStreetAction && !action.type_action) {
          missingFields.push(`Ação ${index + 1}: Tipo da palestra/ação realizada *`);
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
        throw err;
      }

      // 5. Submit for review
      try {
        await api(`/education-reports/${savedId}/submit-for-review/`, { method: "POST" });
      } catch (err) {
        throw err;
      }

      // 6. Confirmar envio e oferecer compartilhamento do resumo
      let submittedReport;

      try {
        submittedReport = await api(`/education-reports/${savedId}/`);
      } catch {
        submittedReport = {
          ...form,
          id: savedId,
          status: "PENDING_REVIEW",
        };
      }

      const summary = buildReportShareSummary(
        submittedReport,
        agenda || {},
        attendanceStats
      );

      setMessage("Relatório enviado para conferência com sucesso.");
      setSharePrompt({
        open: true,
        reportId: savedId,
        summary,
      });

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
  const operationalActionTypeOptions = filterOperationalEducationActionTypes(actionTypes);

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
            const scheduleReadOnly = sourceReadOnly && index !== 0;
            const actionIsStreet = actionMode(action, agenda, index) === "STREET";
            const displayedAgreementLabel = agreementIndicatorLabel(
              getDisplayedAgreementIndicator(action, agenda, index)
            );

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
                  {index > 0 && (
                    <label style={{ display: 'flex', flexDirection: 'column', gap: '4px', fontSize: '14px', fontWeight: '500', color: '#334155' }}>
                      Modalidade desta ação
                      <select value={actionIsStreet ? "STREET" : "LECTURE"} onChange={e => updateAction(index, "action_mode", e.target.value)} style={{ padding: '10px', borderRadius: '8px', border: '1px solid #cbd5e1', backgroundColor: '#fff' }}>
                        <option value="STREET">Ação de Rua</option>
                        <option value="LECTURE">Palestra/Ação Educativa</option>
                      </select>
                    </label>
                  )}
                  {!actionIsStreet && (
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
                        readOnly={scheduleReadOnly}
                        style={{ padding: '10px', borderRadius: '8px', border: '1px solid #cbd5e1', backgroundColor: scheduleReadOnly ? '#f1f5f9' : '#fff' }}
                      />
                    </label>
                    <label style={{ display: 'flex', flexDirection: 'column', gap: '4px', fontSize: '14px', fontWeight: '500', color: '#334155' }}>
                      Horário Final
                      <input
                        type="time"
                        value={action.final_hour || ""}
                        onChange={e => updateAction(index, "final_hour", e.target.value)}
                        readOnly={scheduleReadOnly}
                        style={{ padding: '10px', borderRadius: '8px', border: '1px solid #cbd5e1', backgroundColor: scheduleReadOnly ? '#f1f5f9' : '#fff' }}
                      />
                    </label>
                  </div>

                  {actionIsStreet && (
                    <label style={{ display: 'flex', flexDirection: 'column', gap: '4px', fontSize: '14px', fontWeight: '500', color: '#334155' }}>
                      Tipo da ação realizada *
                      <select
                        value={action.type_action || ""}
                        onChange={e => updateAction(index, "type_action", e.target.value)}
                        disabled={sourceReadOnly && Boolean(action.type_action) && index !== 0}
                        style={{ padding: '10px', borderRadius: '8px', border: '1px solid #cbd5e1', backgroundColor: sourceReadOnly && action.type_action && index !== 0 ? '#f1f5f9' : '#fff' }}
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

                  {!actionIsStreet && (
                    <label style={{ display: 'flex', flexDirection: 'column', gap: '4px', fontSize: '14px', fontWeight: '500', color: '#334155' }}>
                      Tipo da palestra/ação realizada *
                      <select
                        value={action.type_action || ""}
                        onChange={e => updateAction(index, "type_action", e.target.value)}
                        style={{ padding: '10px', borderRadius: '8px', border: '1px solid #cbd5e1', backgroundColor: '#fff' }}
                      >
                        <option value="">Selecione</option>
                        {operationalActionTypeOptions.map((opt) => (
                          <option key={opt.id || opt.name} value={opt.name}>{opt.name}</option>
                        ))}
                      </select>
                      {displayedAgreementLabel && (
                        <span style={{ color: '#64748b', fontSize: '12px' }}>
                          Indicador identificado: {displayedAgreementLabel}
                        </span>
                      )}
                    </label>
                  )}

                  {!actionIsStreet && (
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: '12px' }}>
                      <label style={{ display: 'flex', flexDirection: 'column', gap: '4px', fontSize: '14px', fontWeight: '500', color: '#334155' }}>
                        Tipo de solicitante
                        <select
                          value={action.requester_entity_kind || ""}
                          onChange={e => updateAction(index, "requester_entity_kind", e.target.value)}
                          style={{ padding: '10px', borderRadius: '8px', border: '1px solid #cbd5e1', backgroundColor: '#fff' }}
                        >
                          <option value="">Selecione</option>
                          {REQUESTER_ENTITY_KIND_OPTIONS.map((option) => (
                            <option key={option.value} value={option.value}>{option.label}</option>
                          ))}
                        </select>
                      </label>
                      <label style={{ display: 'flex', flexDirection: 'column', gap: '4px', fontSize: '14px', fontWeight: '500', color: '#334155' }}>
                        Público ou Privado?
                        <select
                          value={action.requester_entity_nature || ""}
                          onChange={e => updateAction(index, "requester_entity_nature", e.target.value)}
                          style={{ padding: '10px', borderRadius: '8px', border: '1px solid #cbd5e1', backgroundColor: '#fff' }}
                        >
                          <option value="">Selecione</option>
                          {REQUESTER_ENTITY_NATURE_OPTIONS.map((option) => (
                            <option key={option.value} value={option.value}>{option.label}</option>
                          ))}
                        </select>
                      </label>
                      <label style={{ display: 'flex', flexDirection: 'column', gap: '4px', fontSize: '14px', fontWeight: '500', color: '#334155' }}>
                        Faixa etária
                        <select
                          value={action.age_range || ""}
                          onChange={e => updateAction(index, "age_range", e.target.value)}
                          style={{ padding: '10px', borderRadius: '8px', border: '1px solid #cbd5e1', backgroundColor: '#fff' }}
                        >
                          <option value="">Selecione</option>
                          {EDUCATION_ACTION_AGE_RANGE_OPTIONS.map((option) => (
                            <option key={option.value} value={option.value}>{option.label}</option>
                          ))}
                        </select>
                      </label>
                    </div>
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
                    {!actionIsStreet ? "Abordados em Palestras" : "Número de Abordagens"}
                    <input
                      type="number"
                      min="0"
                      value={!actionIsStreet ? (action.approached_lectures ?? "") : (action.approached_actions ?? "")}
                      onChange={e => updateAction(index, !actionIsStreet ? "approached_lectures" : "approached_actions", e.target.value)}
                      style={{ padding: '10px', borderRadius: '8px', border: '1px solid #cbd5e1', background: '#fff' }}
                    />
                  </label>

                  <div style={{ paddingTop: '4px', borderTop: '1px solid #e2e8f0' }}>
                    <h5 style={{ margin: '10px 0 12px', color: '#334155', fontSize: '13px' }}>
                      Materiais desta ação
                    </h5>

                    {(() => {
                      const categories = extractMaterialCategories(agenda || {});
                      const baseAction = form.actions?.[0] || emptyAction;

                      let availableMaterials = categories.kits.filter(
                        (item) => (parseInt(item.quantity, 10) || 0) > 0
                      );

                      if (!availableMaterials.length) {
                        availableMaterials = parseMaterialRows(
                          baseAction.distribution_materials_removed || ""
                        ).filter((item) => (parseInt(item.quantity, 10) || 0) > 0);
                      }

                      const distributedValue =
                        action.distribution_materials_distributed ||
                        serializeBlankMaterialRows(availableMaterials);

                      return (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                          {availableMaterials.length > 0 && (
                            <div>
                              <div style={{ marginBottom: '6px', fontSize: '12px', fontWeight: '700', color: '#475569' }}>
                                Material retirado para esta Ordem de Serviço (OS)
                              </div>
                              <div style={{ border: '1px solid #e2e8f0', borderRadius: '8px', background: '#fff', overflow: 'hidden' }}>
                                {availableMaterials.map((row, rowIndex) => (
                                  <div
                                    key={`${row.name}-${rowIndex}`}
                                    style={{
                                      display: 'flex',
                                      justifyContent: 'space-between',
                                      gap: '12px',
                                      padding: '9px 10px',
                                      borderBottom: rowIndex === availableMaterials.length - 1 ? 'none' : '1px solid #e2e8f0',
                                      fontSize: '12px',
                                      color: '#334155'
                                    }}
                                  >
                                    <strong>{row.name}</strong>
                                    <span>{row.quantity}</span>
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}

                          <div>
                            <div style={{ marginBottom: '6px', fontSize: '12px', fontWeight: '700', color: '#475569' }}>
                              Material Distribuído nesta Ação
                            </div>
                            <MobileMaterialQuantityEditor
                              value={distributedValue}
                              onChange={(value) =>
                                updateAction(index, "distribution_materials_distributed", value)
                              }
                            />
                          </div>
                        </div>
                      );
                    })()}
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
                  <option value="NO_IMPACT">Sem prejuízo</option>
                  <option value="PARTIAL">Parcial (atividade continuou com restrições)</option>
                  <option value="INTERRUPTED">Total (atividade suspensa ou cancelada)</option>
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
          style={{ width: '100%', opacity: (isSaving || isSubmitting) ? 0.7 : 1, display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '8px', padding: '14px', borderRadius: '8px', backgroundColor: '#0a1e44', color: '#ffffff', border: '1px solid #0a1e44', fontWeight: '600', fontSize: '16px' }}
        >
          <Save size={18} />
          {isSubmitting ? "Enviando..." : "Enviar para validação"}
        </button>
      </div>

      {sharePrompt.open && (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="share-report-title"
          style={{
            position: "fixed",
            inset: 0,
            zIndex: 1000,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            padding: "20px",
            backgroundColor: "rgba(15, 23, 42, 0.58)",
          }}
        >
          <div
            style={{
              width: "100%",
              maxWidth: "420px",
              maxHeight: "88vh",
              overflowY: "auto",
              backgroundColor: "#ffffff",
              borderRadius: "16px",
              padding: "22px",
              boxShadow: "0 20px 50px rgba(15, 23, 42, 0.24)",
            }}
          >
            <div
              style={{
                width: "52px",
                height: "52px",
                borderRadius: "50%",
                margin: "0 auto 14px",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                backgroundColor: "#dcfce7",
                color: "#166534",
              }}
            >
              <CheckCircle2 size={30} />
            </div>

            <h3
              id="share-report-title"
              style={{
                margin: "0 0 8px",
                textAlign: "center",
                color: "#0f172a",
                fontSize: "19px",
              }}
            >
              Relatório enviado para conferência
            </h3>

            <p
              style={{
                margin: "0 0 18px",
                textAlign: "center",
                color: "#64748b",
                fontSize: "14px",
                lineHeight: "1.5",
              }}
            >
              O relatório foi enviado com sucesso. Deseja compartilhar um resumo pelo WhatsApp?
            </p>

            <div
              style={{
                padding: "12px",
                marginBottom: "18px",
                borderRadius: "10px",
                backgroundColor: "#f8fafc",
                border: "1px solid #e2e8f0",
                color: "#475569",
                fontSize: "12px",
                lineHeight: "1.5",
                whiteSpace: "pre-wrap",
                maxHeight: "260px",
                overflowY: "auto",
              }}
            >
              {sharePrompt.summary}
            </div>

            <div
              style={{
                display: "flex",
                flexDirection: "column",
                gap: "10px",
              }}
            >
              <button
                type="button"
                className="mobile-btn mobile-btn-primary"
                onClick={handleShareReport}
                style={{
                  width: "100%",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  gap: "8px",
                  backgroundColor: "#0a1e44",
                  color: "#ffffff",
                }}
              >
                <MessageCircle size={19} />
                Compartilhar relatório
              </button>

              <button
                type="button"
                className="mobile-btn mobile-btn-outline"
                onClick={closeSharePromptAndOpenReport}
                style={{ width: "100%" }}
              >
                Agora não
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
