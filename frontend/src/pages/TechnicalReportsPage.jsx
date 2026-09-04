import { Clipboard, MapPin, Plus, Save, Search, Trash2, Eye, X, Check, Edit3, Share2 } from "lucide-react";
import logoUrl from "../assets/operacao-lei-seca-logo.png";
import { useEffect, useMemo, useState, useRef } from "react";
import { useSearchParams } from "react-router-dom";
import { api } from "../api/client.js";
import { useAuth } from "../context/AuthContext.jsx";
import { STREET_ACTION_TYPE_OPTIONS, streetActionTypeLabel } from "../utils/streetActionTypes.js";
import { formatDateBR } from "../utils/date.js";
import { filterOperationalEducationActionTypes } from "../utils/actionTypeOptions.js";
import {
  EDUCATION_ACTION_AGE_RANGE_OPTIONS,
  REQUESTER_ENTITY_KIND_OPTIONS,
  REQUESTER_ENTITY_NATURE_OPTIONS,
  agreementIndicatorLabel,
  ageRangeLabel,
  deriveAgreementIndicatorFromAgenda,
  getDisplayedAgreementIndicator,
  requesterEntityKindLabel,
  requesterEntityNatureLabel,
} from "../utils/agreementIndicators.js";
import {
  applyAgendaOwnedActionPrefill,
  applyBlankActionPrefill,
  buildFirstActionAgendaPrefill,
  isStreetActionAgenda,
} from "../utils/reportActionPrefill.js";

import { buildEducationAgentsText, buildOperationalResponsibility, buildPreview, chiefFromReport, reportName, getReachedAudienceForAction } from "../utils/reportPreview.js";
import { generateTechnicalReportPdf } from "../utils/reportPdfGenerator.js";
import { getValidatableActions } from "./technicalReportsActionHelpers.js";
import { buildStaffChanges } from "../utils/reportStaffChanges.js";
import { agendaPk } from "../utils/reportPayload.js";
import { buildReportShareSummary } from "../utils/reportShareSummary.js";
import { executeShare } from "../utils/handleShareReport.js";
import { assertReportConsistency } from "../utils/reportConsistencyValidation.js";

function memberRows(members = {}) {
  return [
    ...(members.chiefs || []).map((item) => ({ ...item, type: "CHIEF", typeLabel: "Chefe" })),
    ...(members.agents || []).map((item) => ({ ...item, type: "AGENT", typeLabel: "Agente" })),
    ...(members.supports || []).map((item) => ({ ...item, type: "SUPPORT", typeLabel: "Apoio" })),
  ];
}

const EMPTY_CONTEXT_MEMBERS = {
  context_resolved: true,
  chiefs: [],
  agents: [],
  supports: [],
};

function findMatchingScheduleInfo(schedules, teamValue, agenda) {
  return (schedules || []).find((schedule) =>
    String(schedule.team) === String(teamValue) ||
    String(schedule.team_name) === String(teamValue) ||
    (agenda && String(schedule.team) === String(agenda.team_ref)) ||
    (agenda && String(schedule.team_name) === String(agenda.sector_name))
  ) || null;
}

function buildAgendaForOperationalPreview(agenda, report, effectiveMembers) {
  if (!agenda) return agenda;
  const responsibility = buildOperationalResponsibility(report, agenda, effectiveMembers);
  return {
    ...agenda,
    support_1: responsibility.supports[0] || "",
    support_2: responsibility.supports[1] || "",
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
  distribution_materials_distributed: "",
};

const empty = {
  source: "LOCAL",
  source_id: "",
  agenda: "",
  agenda_title: "",
  agenda_date: "",
  agenda_location: "",
  operation_date: "",
  team: "",
  management_id: "",
  management_name: "",
  education_agents: "",
  changes_staff: "",
  approximate_public: "",
  request_details: "",
  street_action_details: [],
  accessibility_conditions_met: "",
  materials_removed: "",
  materials_spent: "",
  distribution_materials_removed: "",
  distribution_materials_distributed: "",
  breathalyzers: "",
  cars: "",
  changes_general: "",
  contact_received: "",
  occurrence_observation: "",
  lat: "",
  lng: "",

  status: "DRAFT",
  general_observations: "",
  has_exceptional_occurrence: false,
  exceptional_occurrence_type: "",
  exceptional_occurrence_description: "",
  exceptional_occurrence_actions_taken: "",
  exceptional_occurrence_impact: "",
  actions: [{ ...emptyAction }],
};

const numberFields = [
  "approach",
];

const fieldLabels = {
  approach: "Público estimado (Ação/Palestra)",
  approached_actions: "Número de abordagens",
};

const streetActionTypeOptions = STREET_ACTION_TYPE_OPTIONS;
const agreementFieldNames = new Set(["requester_entity_kind", "requester_entity_nature", "age_range"]);

const exceptionalOccurrenceTypeOptions = [
  { value: "VEHICLE_BREAKDOWN", label: "Viatura" },
  { value: "WORK_ACCIDENT", label: "Efetivo" },
];

const exceptionalOccurrenceImpactOptions = [
  { value: "NO_IMPACT", label: "Sem preju\u00edzo" },
  { value: "PARTIAL", label: "Prejudicada parcialmente" },
  { value: "INTERRUPTED", label: "Interrompida" },
];

function normalizeTypeLabel(value) {
  return String(value || "").trim().toLocaleLowerCase("pt-BR");
}

function actionMode(action, agenda, index) {
  if (index === 0) return isStreetActionAgenda(agenda) ? "STREET" : "LECTURE";
  if (action?.action_mode === "STREET" || action?.action_mode === "LECTURE") return action.action_mode;
  return streetActionTypeOptions.includes(String(action?.type_action || "").trim()) ? "STREET" : "LECTURE";
}

function nullable(value) {
  return value === "" ? null : value;
}

function chiefFromAgenda(agenda) {
  return agenda?.chief_name || agenda?.chief_ref_name || "";
}

function serviceOrderLabel(agenda) {
  const number = agenda?.service_order_number;
  return number ? `OS ${String(number).padStart(4, "0")}` : "Sem OS";
}

function agendaReferenceLabel(agenda) {
  if (!agenda) return "";
  return `${serviceOrderLabel(agenda)} - Protocolo #${agenda.id}`;
}

function agendaSummary(agenda) {
  if (!agenda) return "";
  return `${agendaReferenceLabel(agenda)} - ${agenda.title} - ${formatDateBR(agenda.date)}`;
}

function joinValues(values, fallback = "") {
  return values.filter(Boolean).join("\n") || fallback;
}

function uniqueVehicleValues(...values) {
  const seen = new Set();

  return values
    .flatMap((value) => String(value || "").split(/\r?\n/))
    .filter((value) => {
      const text = String(value || "").trim();
      if (!text) return false;

      const plate =
        text.toUpperCase().match(/[A-Z]{3}[-\s]?\d[A-Z0-9]\d{2}|[A-Z]{3}[-\s]?\d{4}/)?.[0]
          ?.replace(/[^A-Z0-9]/g, "")
        || "";

      const key = plate || text.toLocaleLowerCase("pt-BR");

      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    })
    .map((value) => String(value || "").trim());
}

function dedupeVehicleText(value = "") {
  return joinValues(
    uniqueVehicleValues(
      ...String(value || "").split(/\r?\n/)
    )
  );
}

function removeVehicleLinesFromResources(value = "") {
  return String(value || "")
    .split(/\r?\n/)
    .filter((line) => {
      const text = line.trim();
      return !/^Viatura(?: cadastrada)?:/i.test(text);
    })
    .join("\n")
    .trim();
}

function formatContactValue(value = "") {
  const text = String(value || "").trim();
  if (!text) return "";

  const normalized = text.replace(/\s*,\s*/g, ", ").replace(/\s+/g, " ");
  if (normalized.includes(",")) {
    return normalized.split(",").map((part) => part.trim()).filter(Boolean).join(", ");
  }

  const email = normalized.match(/[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/i)?.[0] || "";
  const withoutEmail = email ? normalized.replace(email, "").trim() : normalized;
  const phone = withoutEmail.match(/\+?\d[\d\s().-]{7,}\d/)?.[0]?.trim() || "";
  const name = phone ? withoutEmail.replace(phone, "").trim() : withoutEmail;
  const parts = [name, phone, email].filter(Boolean);

  return parts.length > 1 ? parts.join(", ") : normalized;
}

function joinContactValues(values, fallback = "") {
  return values.map((value) => String(value || "").trim()).filter(Boolean).join(", ") || fallback;
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
      const q = item.quantity !== "" && item.quantity !== undefined && item.quantity !== null ? item.quantity : "";
      return `${item.name} | ${q}`;
    })
    .join("\n");
}

function serializeBlankMaterialRows(rows = []) {
  return rows
    .filter((item) => item.name)
    .map((item) => `${item.name} | `)
    .join("\n");
}

function sumActionDistributedMaterials(actions, catsKits) {
  const map = {};
  catsKits.forEach(item => {
    map[item.name.toLowerCase()] = { name: item.name, quantity: 0 };
  });

  actions.forEach(action => {
    const distStr = action.distribution_materials_distributed || serializeBlankMaterialRows(catsKits);
    const parsed = parseMaterialRows(distStr);
    parsed.forEach(item => {
      const key = item.name.toLowerCase();
      const qty = parseInt(item.quantity, 10) || 0;
      if (!map[key]) {
        map[key] = { name: item.name, quantity: 0 };
      }
      map[key].quantity += qty;
    });
  });

  return serializeMaterialRows(Object.values(map));
}

function MaterialSummary({ title, value }) {
  const rows = parseMaterialRows(value);
  return (
    <div className="material-entry-card material-entry-card-readonly">
      {title && (
        <div className="material-entry-heading">
          <span>{title}</span>
          <small>{rows.length} {rows.length === 1 ? "item" : "itens"}</small>
        </div>
      )}
      <div className="material-entry-list">
        {rows.length ? rows.map((row, rowIndex) => (
          <div className="material-entry-row" key={`${row.name}-${rowIndex}`}>
            <strong>{row.name}</strong>
            <span>{row.quantity || "Quantidade não informada na OS"}</span>
          </div>
        )) : <p>Nenhum material vinculado.</p>}
      </div>
    </div>
  );
}

function MaterialQuantityEditor({ title, value, onChange }) {
  const rows = parseMaterialRows(value);
  const updateRow = (rowIndex, quantity) => {
    const nextRows = rows.map((row, index) => (
      index === rowIndex ? { ...row, quantity } : row
    ));
    onChange(serializeMaterialRows(nextRows));
  };

  return (
    <div className="material-entry-card">
      {title && (
        <div className="material-entry-heading">
          <span>{title}</span>
          <small>Preencha a quantidade distribuída</small>
        </div>
      )}
      <div className="material-entry-list">
        {rows.length ? rows.map((row, rowIndex) => (
          <label className="material-entry-row editable" key={`${row.name}-${rowIndex}`}>
            <strong>{row.name}</strong>
            <input
              type="number"
              min="0"
              placeholder="0"
              value={row.quantity}
              onChange={(event) => updateRow(rowIndex, event.target.value)}
            />
          </label>
        )) : <p>Nenhum material disponível nesta agenda.</p>}
      </div>
    </div>
  );
}

function materialsFromAgenda(agenda = {}) {
  const rows = [];
  for (let index = 1; index <= 7; index += 1) {
    const kit = agenda[`kit_${index}`];
    const quantity = agenda[`kit_${index}_quantity`];
    const material = agenda[`material_${index}`];
    if (kit) rows.push(`${kit}${quantity ? ` - ${quantity}` : ""}`);
    if (material) rows.push(material);
  }
  if (agenda.materials?.length) {
    agenda.materials.forEach((item) => {
      if (item.dynamic_name) rows.push(`${item.dynamic_name}${item.quantity ? ` - ${item.quantity}` : ""}`);
      if (item.kit_name) rows.push(`${item.kit_name}${item.quantity ? ` - ${item.quantity}` : ""}`);
      if (item.material_name) rows.push(`${item.material_name}${item.quantity ? ` - ${item.quantity}` : ""}`);
    });
  }
  return rows.join("\n");
}

function materialLine(name, quantity) {
  return name ? `${name}${quantity ? ` - ${quantity}` : ""}` : "";
}

function extractMaterialCategories(agenda) {
  const safeAgenda = agenda || {};
  const dynamics = [];
  const supports = [];
  const kits = [];

  const add = (list, name, quantity) => {
    if (!name) return;
    const normalizedName = String(name).trim();
    if (!normalizedName) return;

    const existing = list.find(item => String(item.name).trim().toLowerCase() === normalizedName.toLowerCase());
    const validQuantity = quantity !== null && quantity !== undefined && quantity !== "" ? Number(quantity) : "";

    if (!existing) {
      list.push({ name: normalizedName, quantity: validQuantity });
    } else if (validQuantity !== "" && existing.quantity === "") {
      existing.quantity = validQuantity;
    }
  };

  for (let index = 1; index <= 7; index += 1) {
    add(supports, safeAgenda[`kit_${index}`], safeAgenda[`kit_${index}_quantity`]);
    add(kits, safeAgenda[`material_${index}`], "");
  }

  if (safeAgenda.materials?.length) {
    safeAgenda.materials.forEach((item) => {
      add(dynamics, item.dynamic_name, item.quantity);
      add(kits, item.kit_name, item.quantity);
      add(supports, item.material_name, item.quantity);
    });
  }

  return { dynamics, supports, kits };
}

function protocolDetails(agenda) {
  const agendaVehicles = uniqueVehicleValues(
    agenda?.vehicle,
    agenda?.vehicle_name,
  );
  const requesterEntityTypeLabel =
    String(agenda?.requester_entity_type) === "6"
      ? "A\u00e7\u00e3o de Rua"
      : agenda?.requester_entity_type || "";

  return {
    agents: joinValues([
      chiefFromAgenda(agenda) ? `Chefe responsável: ${chiefFromAgenda(agenda)}` : "",
      agenda.team_phone ? `Telefone do chefe/equipe: ${agenda.team_phone}` : "",
      agenda.agents ? `Agentes: ${agenda.agents}` : "",
      agenda.support_1 ? `Apoio 1: ${agenda.support_1}` : "",
      agenda.support_2 ? `Apoio 2: ${agenda.support_2}` : "",
    ]),
    resources: joinValues([
      materialsFromAgenda(agenda) ? `Kits e materiais:\n${materialsFromAgenda(agenda)}` : "",
      agenda.media_equipment ? `Recursos do local:\n${agenda.media_equipment}` : "",
    ]),
    notes: joinValues([
      agenda.notes ? `Observações da solicitação:\n${agenda.notes}` : "",
      agenda.description ? `Descrição:\n${agenda.description}` : "",
      agenda.cancel_reason ? `Motivo registrado:\n${agenda.cancel_reason}` : "",
    ]),
    audience: joinValues([
      agenda.audience ? `Público: ${agenda.audience}` : "",
      requesterEntityTypeLabel ? `Tipo de entidade: ${requesterEntityTypeLabel}` : "",
      agenda.age_ranges ? `Faixa etária: ${agenda.age_ranges}` : "",
      agenda.participant_range
        ? `Quantidade prevista: ${agenda.participant_range}`
        : agenda.quantity ? `Quantidade prevista: ${agenda.quantity}` : "",
      agenda.external_responsible ? `Responsável no local: ${agenda.external_responsible}` : "",
      agenda.external_responsible_phone ? `Telefone: ${agenda.external_responsible_phone}` : "",
      agenda.external_email ? `E-mail: ${agenda.external_email}` : "",
    ]),
  };
}

function addressFromAgenda(agenda) {
  if (!agenda) return "";
  return [
    agenda.address,
    agenda.neighborhood || agenda.neighborhood_ref_name,
    agenda.city || agenda.municipality_ref_name,
    agenda.state,
    "Brasil",
  ].filter(Boolean).join(", ") || [
    agenda.institution_location,
    agenda.location,
    agenda.city || agenda.municipality_ref_name,
    agenda.state,
    "Brasil",
  ].filter(Boolean).join(", ");
}


function numericApproximatePublic(value) {
  if (value === null || value === undefined || value === "") return "";
  const digits = String(value).replace(/\D/g, "");
  return digits || "";
}

function buildRequestDetails(report, agenda) {
  if (report?.request_details) return report.request_details;
  return protocolDetails(agenda || report || {}).audience || "";
}

function hydrateForm(report, agenda, actionTypes = []) {
  const hasAnySourceId = report.actions?.some((a) => a.source_id) ?? false;
  const reportAgendaPk = agendaPk(report.agenda, agenda);
  const agendaPrefill = buildFirstActionAgendaPrefill(agenda, actionTypes);
  const inheritedAgreementIndicator = deriveAgreementIndicatorFromAgenda(agenda);
  return {
    ...report,
    agenda: reportAgendaPk || "",
    cars: dedupeVehicleText(report?.cars),
    breathalyzers: removeVehicleLinesFromResources(report?.breathalyzers),
    has_exceptional_occurrence: Boolean(report?.has_exceptional_occurrence),
    exceptional_occurrence_type: report?.exceptional_occurrence_type || "",
    exceptional_occurrence_description: report?.exceptional_occurrence_description || "",
    exceptional_occurrence_actions_taken: report?.exceptional_occurrence_actions_taken || "",
    exceptional_occurrence_impact: report?.exceptional_occurrence_impact || "",
    approximate_public: numericApproximatePublic(report?.approximate_public),
    request_details: buildRequestDetails(report, agenda),
    actions: report.actions?.length
      ? report.actions.map((action, idx) => {
          const actionPrefill = idx === 0 ? applyAgendaOwnedActionPrefill(action, agendaPrefill) : action;
          return {
          ...action,
          agenda: agendaPk(action.agenda, reportAgendaPk) || "",
          action_mode: actionPrefill.action_mode || action.action_mode,
          place_action: actionPrefill.place_action || "",
          institution_name: actionPrefill.institution_name || "",
          type_action: actionPrefill.type_action || "",
          type_audience: actionPrefill.type_audience || "",
          requester_entity_kind: actionPrefill.requester_entity_kind || "",
          requester_entity_nature: actionPrefill.requester_entity_nature || "",
          age_range: actionPrefill.age_range || "",
          start_time: actionPrefill.start_time || "",
          final_hour: actionPrefill.final_hour || "",
          approach: actionPrefill.approach,
          agreement_indicator: action.agreement_indicator || (idx === 0 ? inheritedAgreementIndicator : ""),
          __userCreated: hasAnySourceId ? !action.source_id : idx > 0,
        }; })
      : [{
          ...emptyAction,
          ...applyBlankActionPrefill(emptyAction, agendaPrefill),
          agenda: reportAgendaPk || "",
          source_id: reportAgendaPk ? `agenda_action:${reportAgendaPk}` : "",
          agreement_indicator: inheritedAgreementIndicator,
          __userCreated: false,
        }],
  };
}

function buildActionPayload(action, formAgenda) {
  return {
    ...action,
    action_mode: action.action_mode || (
      streetActionTypeOptions.includes(String(action.type_action || "").trim())
        ? "STREET"
        : "LECTURE"
    ),
    agenda: agendaPk(action.agenda, formAgenda),
    source_id: nullable(action.source_id),
    ...Object.fromEntries(numberFields.map((field) => [field, Number(action[field] || 0)])),
    approached_lectures: Number(action.approached_lectures || 0),
    approached_actions: (action.approached_actions === "" || action.approached_actions === null || action.approached_actions === undefined) ? 0 : Number(action.approached_actions),
  };
}

function normalizePayload(form) {
  const { request_details, ...payloadForm } = form;
  return {
    ...payloadForm,
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
    exceptional_occurrence_impact: form.has_exceptional_occurrence ? (form.exceptional_occurrence_impact || "") : "",
    actions: getValidatableActions(form.actions).map(({ action }) => buildActionPayload(action, form.agenda)),
  };
}

export default function TechnicalReportsPage() {
  const { user } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();
  const openReportId = searchParams.get("openReport");
  const processedOpenReport = useRef(false);
  const isVisitor = user?.role === "VISITOR";
  const [agendas, setAgendas] = useState([]);
  const [actionTypes, setActionTypes] = useState([]);
  const [reports, setReports] = useState([]);
  const [techFilters, setTechFilters] = useState({ q: "", team: "", date: "", status: isVisitor ? "APPROVED" : "" });
  const [pendingTechFilters, setPendingTechFilters] = useState({ q: "", team: "", date: "", status: isVisitor ? "APPROVED" : "" });
  const [pendingReviewCount, setPendingReviewCount] = useState(0);
  const [pendingDateFilter, setPendingDateFilter] = useState("");
  const [pendingChiefFilter, setPendingChiefFilter] = useState("");
  const [pendingChiefQuery, setPendingChiefQuery] = useState("");
  const [reportsPreviewModal, setReportsPreviewModal] = useState(null);
  const [resolvedHistoricalAgenda, setResolvedHistoricalAgenda] = useState(null);
  const [historicalScheduleMembers, setHistoricalScheduleMembers] = useState(null);
  const [isLoadingHistoricalAgenda, setIsLoadingHistoricalAgenda] = useState(false);
  const [historicalAgendaError, setHistoricalAgendaError] = useState("");
  const [activeTab, setActiveTab] = useState(isVisitor ? "completed" : "pending");
  const [showPreviewModal, setShowPreviewModal] = useState(false);
  const [protocolSearch, setProtocolSearch] = useState("");
  const [form, setForm] = useState(empty);
  const [editing, setEditing] = useState(null);
  const [isEditingLoading, setIsEditingLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [submittedShareSummary, setSubmittedShareSummary] = useState("");
  const [loadError, setLoadError] = useState("");
  const [locationMessage, setLocationMessage] = useState("");
  const [isGeocoding, setIsGeocoding] = useState(false);
  const [isAttendanceModalOpen, setIsAttendanceModalOpen] = useState(false);
  const [reportSchedule, setReportSchedule] = useState(null);
  const [attendanceForm, setAttendanceForm] = useState({});
  const [returnModalReportId, setReturnModalReportId] = useState(null);
  const [returnNotes, setReturnNotes] = useState("");
  const [isSaving, setIsSaving] = useState(false);
  const [isSavingAttendance, setIsSavingAttendance] = useState(false);
  const [isApproving, setIsApproving] = useState(false);
  const isAdmin = user?.role === "ADMIN" || user?.role === "MANAGER";
  const requestFieldsReadOnly = Boolean(form.agenda);
  const isEditableTechnicalReport = form.status === "DRAFT" || form.status === "RETURNED";

  const selectedAgenda = useMemo(
    () => agendas.find((agenda) => String(agenda.id) === String(form.agenda)),
    [agendas, form.agenda]
  );
  const operationalActionTypeOptions = useMemo(
    () => filterOperationalEducationActionTypes(actionTypes),
    [actionTypes]
  );
  const isStreetActionSelectedAgenda = Boolean(selectedAgenda && isStreetActionAgenda(selectedAgenda));
  const predefinedStreetActionTypes = useMemo(
    () => [...new Set((form.street_action_details || [])
      .map((detail) => String(detail?.type || "").trim())
      .filter((type) => streetActionTypeOptions.includes(type)))],
    [form.street_action_details]
  );
  const isStreetAction = Boolean(isStreetActionSelectedAgenda || predefinedStreetActionTypes.length > 0);
  const isPublicRequest = selectedAgenda?.origin === "PUBLIC_FORM";
  const isLecture = !isStreetAction;
  const showEstimatedPublic = isLecture || isPublicRequest;
  const shouldChooseStreetActionType = isStreetActionSelectedAgenda && predefinedStreetActionTypes.length > 1;
  const shouldRequireLegacyStreetActionType = isStreetActionSelectedAgenda && predefinedStreetActionTypes.length === 0;
  const hasValidStreetActionSubtype = (value) => streetActionTypeOptions.includes(value);
  const isMissingLegacyStreetSubtype = (value) => shouldRequireLegacyStreetActionType && !hasValidStreetActionSubtype(value || "");
  const originalTypeActionForIndex = (index) => {
    if (!selectedAgenda) return "";
    if (isStreetActionSelectedAgenda) {
      return form.street_action_details?.[index]?.type || selectedAgenda.street_action_details?.[index]?.type || selectedAgenda.action_type || selectedAgenda.action_type_ref_name || "";
    }
    return selectedAgenda.action_type || selectedAgenda.action_type_ref_name || "";
  };
  const shouldHighlightChiefTypeAction = (action, index) => {
    const originalType = originalTypeActionForIndex(index);
    if (!originalType) return false;
    return normalizeTypeLabel(action?.type_action) !== normalizeTypeLabel(originalType);
  };
  const membersForPresentation = reportSchedule?.members
    || (selectedAgenda?.service_order_mode === "TEAM" ? EMPTY_CONTEXT_MEMBERS : null);
  const selectedAgendaForPreview = useMemo(
    () => buildAgendaForOperationalPreview(selectedAgenda, form, membersForPresentation),
    [selectedAgenda, form, membersForPresentation]
  );
  const operationalResponsibility = useMemo(
    () => buildOperationalResponsibility(form, selectedAgendaForPreview, membersForPresentation),
    [form, selectedAgendaForPreview, membersForPresentation]
  );
  const preview = useMemo(
    () => buildPreview(form, selectedAgendaForPreview, showEstimatedPublic, membersForPresentation),
    [form, selectedAgendaForPreview, showEstimatedPublic, membersForPresentation]
  );
  const attendanceStats = useMemo(() => {
    const attendance = Object.values(attendanceForm || {});
    return {
      loaded: attendance.length > 0,
      total: attendance.length,
      present: attendance.filter((member) => member.is_absent === false).length,
      absent: attendance.filter((member) => member.is_absent === true).length,
    };
  }, [attendanceForm]);

  const reportShareSummary = useMemo(() => {
    return buildReportShareSummary(form, selectedAgendaForPreview || {}, attendanceStats);
  }, [form, selectedAgendaForPreview, attendanceStats]);
  const hasShareableReport = Boolean(
    form.operation_date && getValidatableActions(form.actions).length > 0 && reportShareSummary
  );

  const completedAgendaIds = useMemo(() => new Set(reports.map(r => String(agendaPk(r.agenda))).filter(Boolean)), [reports]);
  const pendingAgendas = useMemo(() => agendas.filter(a => !completedAgendaIds.has(String(a.id))), [agendas, completedAgendaIds]);
  const pendingReviewReportsCount = pendingReviewCount;

  const filteredPendingAgendas = useMemo(() => {
    let list = pendingAgendas;
    if (pendingDateFilter) {
      list = list.filter(a => a.date === pendingDateFilter);
    }
    return list;
  }, [pendingAgendas, pendingDateFilter]);


  const load = async () => {
    setLoadError("");
    const params = new URLSearchParams({ page_size: "50" });
    Object.entries(techFilters).forEach(([key, value]) => {
      if (value) params.set(key, value);
    });
    if (isVisitor) params.set("status", "APPROVED");

    const [agendasResult, reportsResult, pendingCountResult, actionTypesResult] = await Promise.allSettled([
      api(`/agendas/?page_size=50&reportable=true&pending_report=true${pendingChiefQuery ? `&chief=${encodeURIComponent(pendingChiefQuery)}` : ''}`),
      api(`/education-reports/?${params.toString()}`),
      isVisitor ? Promise.resolve({ count: 0 }) : api("/education-reports/?status=PENDING_REVIEW&page_size=1"),
      api("/action-types/?page_size=500"),
    ]);

    if (agendasResult.status === "fulfilled") {
      const data = agendasResult.value;
      setAgendas(data.results || data);
    }
    if (reportsResult.status === "fulfilled") {
      const data = reportsResult.value;
      const results = data?.results || data;
      setReports(Array.isArray(results) ? results : []);
    }
    if (pendingCountResult.status === "fulfilled") {
      setPendingReviewCount(pendingCountResult.value?.count || 0);
    }
    if (actionTypesResult.status === "fulfilled") {
      const data = actionTypesResult.value;
      const results = data?.results || data;
      setActionTypes(Array.isArray(results) ? results : []);
    }

    const failures = [agendasResult, reportsResult, actionTypesResult]
      .filter((result) => result.status === "rejected")
      .map((result) => result.reason?.message)
      .filter(Boolean);
    if (failures.length) {
      setLoadError(failures.join(" "));
    }
  };
  useEffect(() => { load(); }, [techFilters, pendingChiefQuery]);

  useEffect(() => {
    if (!openReportId || processedOpenReport.current) return;
    let active = true;
    const controller = new AbortController();

    const reportId = Number(openReportId);
    const removeOpenReportParam = () => {
      if (!active) return;
      setSearchParams((currentParams) => {
        const nextParams = new URLSearchParams(currentParams);
        nextParams.delete("openReport");
        return nextParams;
      }, { replace: true });
    };

    if (!Number.isInteger(reportId) || reportId <= 0 || String(reportId) !== String(openReportId).trim()) {
      processedOpenReport.current = true;
      setLoadError("Parâmetro openReport inválido.");
      removeOpenReportParam();
      return () => {
        active = false;
        processedOpenReport.current = false;
        controller.abort();
      };
    }

    const fetchDirectReport = async () => {
      processedOpenReport.current = true;
      try {
        setLoadError("");
        const report = await api(`/education-reports/${reportId}/`, {
          redirectOnUnauthorized: false,
          signal: controller.signal,
        });
        if (!active || !report?.id) return;

        if (isVisitor) {
          await viewReport(report);
        } else {
          await edit(report);
        }
      } catch (err) {
        if (!active) return;
        const message = String(err.message || "");
        const normalizedMessage = message.toLocaleLowerCase("pt-BR");
        if (
          message.includes("Sessão expirada") ||
          message.includes("Sessao expirada") ||
          message.includes("401") ||
          normalizedMessage.includes("token") ||
          normalizedMessage.includes("authentication") ||
          normalizedMessage.includes("credenciais")
        ) {
          setLoadError("Sessão expirada. Entre novamente para abrir o Relatório Técnico.");
        } else if (normalizedMessage.includes("permiss")) {
          setLoadError("Você não possui permissão para consultar este Relatório Técnico.");
        } else if (
          normalizedMessage.includes("não foi encontrado") ||
          normalizedMessage.includes("nao foi encontrado") ||
          normalizedMessage.includes("not found") ||
          message.includes("404")
        ) {
          setLoadError("Relatório Técnico não encontrado.");
        } else if (normalizedMessage.includes("conectar") || normalizedMessage.includes("online") || normalizedMessage.includes("conex")) {
          setLoadError("Não foi possível conectar à API. Verifique sua conexão e tente novamente.");
        } else {
          setLoadError("Não foi possível abrir o Relatório Técnico informado.");
        }
      } finally {
        if (active) {
          removeOpenReportParam();
        }
        processedOpenReport.current = false;
      }
    };

    fetchDirectReport();
    return () => {
      active = false;
      processedOpenReport.current = false;
      controller.abort();
    };
  }, [openReportId, setSearchParams, isVisitor]);

  const buildAttendanceForm = (detailSchedule) => {
    const formObj = {};
    memberRows(detailSchedule.members).forEach((member) => {
      const memberKey = `${member.type}_${member.id}`;
      const isChecked = detailSchedule.checked_members && detailSchedule.checked_members[memberKey] !== undefined;
      formObj[memberKey] = {
        is_absent: isChecked ? !!member.is_absent : null,
        reason: member.absence_reason || "",
        attachment: null,
        member,
      };
    });
    return { formObj, staffChanges: buildStaffChanges(detailSchedule) };
  };

  const loadScheduleAttendance = async (scheduleId, agendaContext = selectedAgenda) => {
    try {
      const agendaQuery = agendaContext?.id ? `?agenda=${agendaContext.id}` : "";
      const detailSchedule = await api(`/shift-schedules/${scheduleId}/${agendaQuery}`);
      setReportSchedule(detailSchedule);
      const { formObj, staffChanges } = buildAttendanceForm(detailSchedule);
      setAttendanceForm(formObj);
      setForm((current) => ({
        ...current,
        education_agents: buildEducationAgentsText(current, agendaContext, detailSchedule.members),
        changes_staff: staffChanges.join("\n"),
      }));
      return detailSchedule;
    } catch (error) {
      if (agendaContext?.service_order_mode === "TEAM") {
        setReportSchedule(null);
        setAttendanceForm({});
        setForm((current) => ({
          ...current,
          education_agents: buildEducationAgentsText(current, agendaContext, EMPTY_CONTEXT_MEMBERS),
          changes_staff: "",
        }));
      }
      throw error;
    }
  };

  const fetchScheduleMembersForContext = async (operationDate, teamValue, agendaContext) => {
    if (!operationDate || !teamValue || agendaContext?.service_order_mode === "DESIGNATED") {
      return null;
    }

    const res = await api(`/shift-schedules/?date=${operationDate}`);
    const schedules = res.results || res;
    const scheduleInfo = findMatchingScheduleInfo(schedules, teamValue, agendaContext);
    if (!scheduleInfo) {
      return null;
    }

    const detailSchedule = await api(
      `/shift-schedules/${scheduleInfo.id}/?agenda=${agendaContext.id}`
    );
    return detailSchedule?.members || null;
  };

  const buildDesignatedAttendanceForm = () => {
    if (!selectedAgenda || selectedAgenda.service_order_mode !== "DESIGNATED") return;
    const formObj = {};
    const absentIds = selectedAgenda.absent_designated_users || [];
    const isChecked = !!form.id;
    (selectedAgenda.designated_users_details || []).forEach(user => {
      const memberKey = `DESIGNATED_${user.id}`;
      const isAbsent = absentIds.includes(user.id);
      formObj[memberKey] = {
        is_absent: isChecked ? isAbsent : null,
        reason: "",
        attachment: null,
        member: {
          id: user.id,
          name: user.full_name || user.first_name || user.username || "Participante",
          typeLabel: "Participante Individual"
        }
      };
    });
    setAttendanceForm(formObj);
  };

  useEffect(() => {
    const isDesignated = selectedAgenda?.service_order_mode === "DESIGNATED";
    if (form.operation_date && form.team && !isDesignated) {
      api(`/shift-schedules/?date=${form.operation_date}`).then(res => {
        const schedules = res.results || res;
        const scheduleInfo = findMatchingScheduleInfo(schedules, form.team, selectedAgenda);
        if (scheduleInfo) {
          loadScheduleAttendance(scheduleInfo.id, selectedAgenda).catch(() => {
            setReportSchedule(null);
            setAttendanceForm({});
          });
        } else {
           setReportSchedule(null);
           setAttendanceForm({});
          if (selectedAgenda?.service_order_mode === "TEAM") {
            setForm((current) => ({
              ...current,
              education_agents: buildEducationAgentsText(current, selectedAgenda, EMPTY_CONTEXT_MEMBERS),
              changes_staff: "",
            }));
          }
        }
      }).catch(() => {
        setReportSchedule(null);
        setAttendanceForm({});
      });
    } else {
      setReportSchedule(null);
      if (isDesignated) {
        buildDesignatedAttendanceForm();
      } else {
        setAttendanceForm({});
      }
    }
  }, [form.operation_date, form.team, selectedAgenda, form.id]);

  const update = (field, value) => setForm((current) => ({ ...current, [field]: value }));

  const updateExceptionalOccurrence = (enabled) => {
    setForm((current) => ({
      ...current,
      has_exceptional_occurrence: enabled,
      exceptional_occurrence_type: enabled ? current.exceptional_occurrence_type : "",
      exceptional_occurrence_description: enabled ? current.exceptional_occurrence_description : "",
      exceptional_occurrence_actions_taken: enabled ? current.exceptional_occurrence_actions_taken : "",
      exceptional_occurrence_impact: enabled ? current.exceptional_occurrence_impact : "",
    }));
  };

  const getExceptionalOccurrenceMissingFields = () => {
    if (!form.has_exceptional_occurrence) return [];

    const missingFields = [];
    if (!form.exceptional_occurrence_type) missingFields.push({ name: "Tipo de ocorrência excepcional", id: "select-exceptional-occurrence-type" });
    if (!String(form.exceptional_occurrence_description || "").trim()) missingFields.push({ name: "Descrição da ocorrência excepcional", id: "input-exceptional-occurrence-description" });
    if (!String(form.exceptional_occurrence_actions_taken || "").trim()) missingFields.push({ name: "Providências adotadas", id: "input-exceptional-occurrence-actions" });
    if (!form.exceptional_occurrence_impact) missingFields.push({ name: "Impacto na atividade", id: "select-exceptional-occurrence-impact" });
    return missingFields;
  };

  const applyAgenda = (agenda, { preserveCurrent = true } = {}) => {
    const selectedAgendaPk = agendaPk(agenda);
    const details = protocolDetails(agenda);
    const selectedMaterials = extractMaterialCategories(agenda);
    const initialEquipment = serializeMaterialRows([...selectedMaterials.dynamics, ...selectedMaterials.supports]);
    const initialKits = serializeMaterialRows(selectedMaterials.kits);
    const blankKits = serializeBlankMaterialRows(selectedMaterials.kits);
    const buildAgendaAction = (currentAction = {}, isFirstAction = false) => {
      const isUserCreated = currentAction.__userCreated;
      const inheritAgendaFields = isFirstAction && !isUserCreated;
      const agendaPrefill = inheritAgendaFields ? buildFirstActionAgendaPrefill(agenda, actionTypes) : {};
      if (isUserCreated) {
        return {
          ...emptyAction,
          ...currentAction,
          agenda: selectedAgendaPk || "",
          source_id: "",
          __userCreated: true,
        };
      }
      const actionPrefill = inheritAgendaFields
        ? applyAgendaOwnedActionPrefill(currentAction, agendaPrefill)
        : currentAction;
      return {
        ...emptyAction,
        ...currentAction,
        action_mode: isFirstAction ? actionPrefill.action_mode : currentAction.action_mode,
        agenda: selectedAgendaPk || "",
        source_id: isUserCreated ? "" : (currentAction.source_id || (selectedAgendaPk ? `agenda_action:${selectedAgendaPk}` : "")),
        place_action: actionPrefill.place_action || "",
        institution_name: actionPrefill.institution_name || "",
        type_action: actionPrefill.type_action || "",
        type_audience: actionPrefill.type_audience || "",
        requester_entity_kind: actionPrefill.requester_entity_kind || "",
        requester_entity_nature: actionPrefill.requester_entity_nature || "",
        age_range: actionPrefill.age_range || "",
        agreement_indicator: currentAction.agreement_indicator || (inheritAgendaFields ? deriveAgreementIndicatorFromAgenda(agenda) : ""),
        start_time: actionPrefill.start_time || "",
        final_hour: actionPrefill.final_hour || "",
        approach: inheritAgendaFields ? actionPrefill.approach : currentAction.approach,
        approached_lectures: currentAction.approached_lectures ?? "",
        approached_actions: (currentAction.approached_actions === 0 || currentAction.approached_actions === "0" || !currentAction.approached_actions) ? "" : currentAction.approached_actions,
        equipment_materials_removed: currentAction.equipment_materials_removed || (inheritAgendaFields ? initialEquipment : ""),
        equipment_materials_distributed: currentAction.equipment_materials_distributed || (inheritAgendaFields ? initialEquipment : ""),
        distribution_materials_removed: currentAction.distribution_materials_removed || (inheritAgendaFields ? initialKits : ""),
        distribution_materials_distributed: currentAction.distribution_materials_distributed || (inheritAgendaFields ? blankKits : ""),
      };
    };
    setForm((current) => {
      const source = preserveCurrent ? current : { ...empty, actions: [{ ...emptyAction }] };
      return {
        ...source,
        agenda: selectedAgendaPk || "",
        agenda_title: agenda.title,
        agenda_date: agenda.date,
        agenda_location: agenda.institution_location || agenda.location,
        operation_date: agenda.date || source.operation_date,
        team: agenda.team_name || agenda.team_ref_name || agenda.sector_name || source.team,
        education_agents: agenda.service_order_mode === "TEAM" ? "" : (source.education_agents || details.agents),
        changes_staff: source.changes_staff || "",
        approximate_public: source.approximate_public || numericApproximatePublic(agenda.quantity),
        request_details: source.request_details || details.audience,
        street_action_details: source.street_action_details?.length ? source.street_action_details : (agenda.street_action_details || []),
        materials_removed: source.materials_removed || materialsFromAgenda(agenda),
        breathalyzers: removeVehicleLinesFromResources(source.breathalyzers) || details.resources,
        cars: dedupeVehicleText(source.cars) || joinValues(uniqueVehicleValues(agenda?.vehicle, agenda?.vehicle_name)),
        contact_received: source.contact_received || joinContactValues([
          agenda.external_responsible,
          agenda.external_responsible_phone,
          agenda.external_email,
        ], source.contact_received),
        occurrence_observation: source.occurrence_observation || agenda.notes || agenda.description || "",
        actions: (() => {
          const meaningfulCurrentActions = getValidatableActions(source.actions).map(({ action }) => action);
          if (isStreetActionAgenda(agenda)) {
            return meaningfulCurrentActions.length
              ? meaningfulCurrentActions.map((action, index) => buildAgendaAction(action, index === 0))
              : [buildAgendaAction({}, true)];
          }
          return source.actions.map((action, index) => buildAgendaAction(action, index === 0));
        })(),
      };
    });

    // O carregamento da escala agora e feito pelo useEffect monitorando operation_date e team
  };

  const loadAgendaDetails = async (agenda) => {
    const agendaId = agendaPk(agenda);
    if (!agendaId) return agenda;
    const detailedAgenda = await api(`/agendas/${agendaId}/`);
    setAgendas((current) => {
      const exists = current.some((item) => String(item.id) === String(detailedAgenda.id));
      return exists
        ? current.map((item) => String(item.id) === String(detailedAgenda.id) ? { ...item, ...detailedAgenda } : item)
        : [...current, detailedAgenda];
    });
    return detailedAgenda;
  };

  const selectAgendaForReport = async (agenda, options) => {
    const detailedAgenda = await loadAgendaDetails(agenda);
    applyAgenda(detailedAgenda, options);
    return detailedAgenda;
  };

  const fillCoordinatesFromAgenda = async (agenda = selectedAgenda) => {
    const query = addressFromAgenda(agenda);
    if (!query) {
      setLocationMessage("O protocolo não possui endereço suficiente para buscar a localização.");
      return false;
    }
    setIsGeocoding(true);
    setLocationMessage("");
    try {
      const params = new URLSearchParams({
        format: "jsonv2",
        limit: "1",
        countrycodes: "br",
        q: query,
      });
      const response = await fetch(`https://nominatim.openstreetmap.org/search?${params.toString()}`, {
        headers: { Accept: "application/json" },
      });
      if (!response.ok) throw new Error("Não foi possível consultar a localização.");
      const results = await response.json();
      const place = results[0];
      if (!place?.lat || !place?.lon) {
        setLocationMessage("Não encontrei coordenadas para o endereço do protocolo.");
        return false;
      }
      setForm((current) => ({ ...current, lat: place.lat, lng: place.lon }));
      setLocationMessage(`Localização preenchida pelo endereço: ${query}`);
      return true;
    } catch (err) {
      setLocationMessage(err.message || "Não foi possível buscar a localização.");
      return false;
    } finally {
      setIsGeocoding(false);
    }
  };

  const findServiceOrder = async () => {
    const search = protocolSearch.trim();
    const numericSearch = search.replace(/^os\s*/i, "").replace(/\D/g, "").replace(/^0+/, "") || search.replace(/^os\s*/i, "").replace(/\D/g, "");
    if (!search) {
      setMessage("Informe a OS da agenda realizada.");
      return;
    }
    setMessage("");
    try {
      const data = await api(`/agendas/?q=${encodeURIComponent(numericSearch || search)}&page_size=20&reportable=true`);
      const list = data.results || data;
      const agenda = list.find((item) => String(item.service_order_number) === numericSearch)
        || list.find((item) => String(item.id) === numericSearch)
        || list[0];
      if (!agenda) {
        setMessage("Nenhuma agenda realizada encontrada para essa OS.");
        return;
      }
      setEditing(null);
      const detailedAgenda = await selectAgendaForReport(agenda, { preserveCurrent: false });
      const foundLocation = await fillCoordinatesFromAgenda(detailedAgenda);
      setMessage(foundLocation ? `${agendaReferenceLabel(detailedAgenda)} vinculada ao relatorio com localizacao preenchida.` : `${agendaReferenceLabel(detailedAgenda)} vinculada ao relatorio.`);
    } catch (err) {
      setMessage(err.message);
    }
  };

  const updateAction = (index, field, value) => {
    setForm((current) => {
      const nextActions = current.actions.map((action, actionIndex) => (
        actionIndex === index
          ? { ...action, [field]: value, ...(field === "action_mode" ? { type_action: "" } : {}), ...(agreementFieldNames.has(field) ? { agreement_indicator: "" } : {}) }
          : action
      ));
      const nextForm = {
        ...current,
        actions: nextActions
      };
      if (field === "distribution_materials_distributed") {
        const safeAgenda = selectedAgenda || {};
        const cats = extractMaterialCategories(safeAgenda);
        nextForm.distribution_materials_distributed = sumActionDistributedMaterials(nextActions, cats.kits);
      }
      return nextForm;
    });
  };

  const updateAllActionsField = (field, value) => {
    setForm((current) => ({
      ...current,
      actions: current.actions.map((action) => ({ ...action, [field]: value })),
    }));
  };

  const addAction = () => {
    setForm((current) => {
      return {
        ...current,
        actions: [...current.actions, {
          ...emptyAction,
          agenda: agendaPk(current.agenda) || "",
          __userCreated: true,
          action_mode: "STREET",
        }],
      };
    });
  };

  const removeAction = (index) => {
    setForm((current) => {
      const nextActions = current.actions.length === 1
        ? [{ ...emptyAction, agenda: agendaPk(current.agenda) || "" }]
        : current.actions.filter((_, actionIndex) => actionIndex !== index);
      const safeAgenda = selectedAgenda || {};
      const cats = extractMaterialCategories(safeAgenda);
      return {
        ...current,
        actions: nextActions,
        distribution_materials_distributed: sumActionDistributedMaterials(nextActions, cats.kits)
      };
    });
  };

  const saveAttendance = async ({ closeModal = true, markReported = false, successMessage = "Frequência salva com sucesso." } = {}) => {
    const isDesignated = selectedAgenda?.service_order_mode === "DESIGNATED";
    if ((!reportSchedule && !isDesignated) || Object.keys(attendanceForm).length === 0) return;
    if (isSavingAttendance) return;
    if (Object.values(attendanceForm).some((data) => data.is_absent === null)) {
      throw new Error("Selecione a frequência de todos os integrantes antes de confirmar.");
    }

    setIsSavingAttendance(true);
    try {
      const promises = Object.entries(attendanceForm).map(([key, data]) => {
        const [memberType, memberId] = key.split("_");
        if (isDesignated) {
          if (data.is_absent) {
            return api(`/agendas/${selectedAgenda.id}/designated-absence/`, {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ user_id: memberId })
            });
          } else {
            return api(`/agendas/${selectedAgenda.id}/designated-absence/`, {
              method: "DELETE",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ user_id: memberId })
            });
          }
        } else {
          if (data.is_absent) {
            const body = new FormData();
            body.append("member_type", memberType);
            body.append("member_id", memberId);
            body.append("reason", data.reason || "Falta");
            if (data.attachment) body.append("attachment", data.attachment);
            return api(`/shift-schedules/${reportSchedule.id}/absence/`, { method: "POST", body });
          }
          return api(`/shift-schedules/${reportSchedule.id}/absence/`, {
            method: "DELETE",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ member_type: memberType, member_id: memberId }),
          });
        }
      });
      await Promise.all(promises);

      if (!isDesignated) {
        const checkedMembersData = {};
        Object.entries(attendanceForm).forEach(([key, data]) => {
          if (data.is_absent !== null) checkedMembersData[key] = true;
        });

        await api(`/shift-schedules/${reportSchedule.id}/`, {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            checked_members: checkedMembersData,
          }),
        });

        if (markReported) {
          await api(`/shift-schedules/${reportSchedule.id}/report-attendance/`, { method: "POST" });
        }
        await loadScheduleAttendance(reportSchedule.id);
      } else {
        const updatedAgenda = await api(`/agendas/${selectedAgenda.id}/`);
        const detailedAgenda = await loadAgendaDetails(updatedAgenda);
        applyAgenda(detailedAgenda);
      }

      if (closeModal) setIsAttendanceModalOpen(false);
      if (successMessage) setMessage(successMessage);
    } finally {
      setIsSavingAttendance(false);
    }
  };

  const saveReport = async (status) => {
    try {
      const isDesignated = selectedAgenda?.service_order_mode === "DESIGNATED";
      if ((reportSchedule || isDesignated) && Object.keys(attendanceForm).length > 0) {
        await saveAttendance({
          closeModal: false,
          markReported: status === "SUBMITTED",
          successMessage: status === "SUBMITTED" ? "Frequência salva com sucesso." : "",
        });
      }

      const occurrenceMissingFields = getExceptionalOccurrenceMissingFields();
      if (occurrenceMissingFields.length > 0) {
        throw new Error(`Preencha os campos obrigatórios da Ocorrência excepcional: ${occurrenceMissingFields.map((field) => field.name).join(", ")}.`);
      }

      const payload = normalizePayload({ ...form, status });
      let saved;
      try {
        saved = editing
          ? await api(`/education-reports/${editing}/`, { method: "PUT", body: JSON.stringify(payload) })
          : await api("/education-reports/", { method: "POST", body: JSON.stringify(payload) });
      } catch (err) {
        if (!editing && err.message?.includes("Já existe um relatório técnico")) {
          const existing = await api(`/education-reports/?agenda=${payload.agenda}&team=${payload.team}`);
          const existingReport = existing.results ? existing.results[0] : (existing[0] || null);
          if (existingReport && (existingReport.status === "DRAFT" || existingReport.status === "RETURNED")) {
            saved = await api(`/education-reports/${existingReport.id}/`, { method: "PUT", body: JSON.stringify(payload) });
          } else if (existingReport) {
            throw new Error("Já existe um relatório aguardando conferência ou já aprovado para este protocolo e equipe.");
          } else {
            throw err;
          }
        } else {
          throw err;
        }
      }
      setEditing(saved.id);
      const savedAgendaPk = agendaPk(saved.agenda);
      const savedAgenda = agendas.find((agenda) => String(agenda.id) === String(savedAgendaPk));
      setForm(hydrateForm(saved, savedAgenda, actionTypes));
      setProtocolSearch(savedAgenda?.service_order_number ? serviceOrderLabel(savedAgenda) : savedAgendaPk ? String(savedAgendaPk) : "");
      load();
      return saved.id;
    } catch (err) {
      throw err;
    }
  };

  const submit = async (event) => {
    event.preventDefault();
    if (isSaving) return;
    setIsSaving(true);
    setMessage("");
    try {
      await saveReport("DRAFT");
      setMessage("Rascunho salvo com sucesso.");
      load();
    } catch (err) {
      setMessage(`⚠ Não foi possível salvar o rascunho\n\nMotivo:\n${err.message}`);
    } finally {
      setIsSaving(false);
    }
  };

  const submitFinal = async () => {
    if (isSaving) return;
    setMessage("");
    setSubmittedShareSummary("");
    const missingFields = [];

    if (!form.operation_date) missingFields.push({ name: "Data da Operação", id: "input-operation-date" });
    if (!form.team) missingFields.push({ name: "Equipe Executora", id: "input-team" });

    getValidatableActions(form.actions).forEach(({ action, index }) => {
      const actionIsStreet = actionMode(action, selectedAgenda, index) === "STREET";
      if (actionIsStreet && (!action.type_action || isMissingLegacyStreetSubtype(action.type_action))) missingFields.push({ name: `Ação ${index + 1}: Ação Definida pelo Chefe`, id: `select-type-action-${index}` });
      if (!actionIsStreet && !action.type_action) missingFields.push({ name: `Ação ${index +1}: Tipo da palestra/ação realizada`, id: `select-type-action-${index}` });
    });

    if (!form.accessibility_conditions_met) missingFields.push({ name: "Condições de Acessibilidade", id: "select-accessibility" });

    const isDesignated = selectedAgenda?.service_order_mode === "DESIGNATED";
    if ((reportSchedule || isDesignated) && Object.values(attendanceForm).some((d) => d.is_absent === null)) {
      missingFields.push({ name: "Frequência da Equipe", id: "attendance-block" }); // assume attendance has this id or similar, I will add it
    }

    if (missingFields.length > 0) {
      setMessage(`⚠ Não foi possível enviar o relatório\n\nMotivo:\nExistem campos obrigatórios não preenchidos:\n${missingFields.map(f => `- ${f.name}`).join('\n')}`);

      const firstMissingId = missingFields[0].id;
      const el = document.getElementById(firstMissingId);
      if (el) {
        el.scrollIntoView({ behavior: "smooth", block: "center" });
        el.focus();
        el.classList.add("highlight-error");
        setTimeout(() => el.classList.remove("highlight-error"), 3000);
      }
      return;
    }
    const validatableActions = getValidatableActions(form.actions).map(({ action }) => action);
    try {
      assertReportConsistency(validatableActions, (action, index) => actionMode(action, selectedAgenda, index));
    } catch (err) {
      setMessage(`⚠ Não foi possível enviar o relatório\n\nMotivo:\n${err.message}`);
      return;
    }
    setIsSaving(true);
    try {
      const savedId = await saveReport("DRAFT");
      await api(`/education-reports/${savedId}/submit-for-review/`, { method: "POST" });
      setSubmittedShareSummary(buildReportShareSummary(form, selectedAgenda || {}, attendanceStats));
      setMessage("Relatório enviado para conferência com sucesso.");
      load();
    } catch (err) {
      setSubmittedShareSummary("");
      setMessage(`⚠ Não foi possível enviar o relatório\n\nMotivo:\n${err.message}`);
    } finally {
      setIsSaving(false);
    }
  };
  const submitRectify = async () => {
    if (isSaving) return;
    setMessage("");
    const missingFields = [];

    if (!form.operation_date) missingFields.push({ name: "Data da Operação", id: "input-operation-date" });
    if (!form.team) missingFields.push({ name: "Equipe Executora", id: "input-team" });

    getValidatableActions(form.actions).forEach(({ action, index }) => {
      const actionIsStreet = actionMode(action, selectedAgenda, index) === "STREET";
      if (actionIsStreet && (!action.type_action || isMissingLegacyStreetSubtype(action.type_action))) missingFields.push({ name: `Ação ${index + 1}: Ação Definida pelo Chefe`, id: `select-type-action-${index}` });
      if (!actionIsStreet && !action.type_action) missingFields.push({ name: `Ação ${index + 1}: Tipo da palestra/ação realizada`, id: `select-type-action-${index}` });
    });

    if (!form.accessibility_conditions_met) missingFields.push({ name: "Condições de Acessibilidade", id: "select-accessibility" });

    const isDesignated = selectedAgenda?.service_order_mode === "DESIGNATED";
    if ((reportSchedule || isDesignated) && Object.values(attendanceForm).some((d) => d.is_absent === null)) {
      missingFields.push({ name: "Frequência da Equipe", id: "attendance-block" });
    }

    if (missingFields.length > 0) {
      setMessage(`⚠️ Não foi possível salvar o relatório\n\nMotivo:\nExistem campos obrigatórios não preenchidos:\n${missingFields.map(f => `- ${f.name}`).join('\n')}`);

      const firstMissingId = missingFields[0].id;
      const el = document.getElementById(firstMissingId);
      if (el) {
        el.scrollIntoView({ behavior: "smooth", block: "center" });
        el.focus();
        el.classList.add("highlight-error");
        setTimeout(() => el.classList.remove("highlight-error"), 3000);
      }
      return;
    }
    setIsSaving(true);
    try {
      await saveReport(form.status);
      setMessage(form.status === "APPROVED"
        ? "Relat\u00f3rio aprovado atualizado com sucesso. A Estat\u00edstica Institucional foi reprocessada automaticamente."
        : "Relat\u00f3rio retificado com sucesso.");
      load();
    } catch (err) {
      setMessage(`⚠️ Não foi possível retificar o relatório\n\nMotivo:\n${err.message}`);
    } finally {
      setIsSaving(false);
    }
  };

  const loadAttendanceForReportContext = async (reportAgenda, hydratedReport) => {
    if (reportAgenda?.service_order_mode === "DESIGNATED") {
      const formObj = {};
      const absentIds = reportAgenda.absent_designated_users || [];
      (reportAgenda.designated_users_details || []).forEach((designatedUser) => {
        const memberKey = `DESIGNATED_${designatedUser.id}`;
        formObj[memberKey] = {
          is_absent: absentIds.includes(designatedUser.id),
          reason: "",
          attachment: null,
          member: {
            id: designatedUser.id,
            name: designatedUser.full_name || designatedUser.first_name || designatedUser.username || "Participante",
            typeLabel: "Participante Individual",
          },
        };
      });
      setReportSchedule(null);
      setAttendanceForm(formObj);
      return;
    }

    if (!hydratedReport.operation_date || !hydratedReport.team) {
      setReportSchedule(null);
      setAttendanceForm({});
      return;
    }

    try {
      const res = await api(`/shift-schedules/?date=${hydratedReport.operation_date}`);
      const schedules = res.results || res;
      const scheduleInfo = findMatchingScheduleInfo(schedules, hydratedReport.team, reportAgenda);

      if (scheduleInfo) {
        await loadScheduleAttendance(scheduleInfo.id, reportAgenda);
      } else {
        setReportSchedule(null);
        setAttendanceForm({});
        if (reportAgenda?.service_order_mode === "TEAM") {
          setForm((current) => ({
            ...current,
            education_agents: buildEducationAgentsText(current, reportAgenda, EMPTY_CONTEXT_MEMBERS),
            changes_staff: "",
          }));
        }
      }
    } catch {
      setReportSchedule(null);
      setAttendanceForm({});
    }
  };

  const viewReport = async (report) => {
    if (isEditingLoading) return;
    setIsEditingLoading(true);
    try {
      const completeReport = await api(`/education-reports/${report.id}/`);
      const reportAgendaPk = agendaPk(completeReport.agenda);
      const reportAgendaLocal = agendas.find((agenda) => String(agenda.id) === String(reportAgendaPk));
      const reportAgenda = reportAgendaPk ? await loadAgendaDetails(reportAgendaLocal || reportAgendaPk) : reportAgendaLocal;

      const resolvedDetails = completeReport.street_action_details?.length
        ? completeReport.street_action_details
        : (reportAgenda?.street_action_details || []);
      const hydrated = hydrateForm({ ...completeReport, street_action_details: resolvedDetails }, reportAgenda, actionTypes);

      setEditing(null);
      setProtocolSearch(reportAgenda?.service_order_number ? serviceOrderLabel(reportAgenda) : reportAgendaPk ? String(reportAgendaPk) : "");
      setForm(hydrated);
      setMessage("");
      await loadAttendanceForReportContext(reportAgenda, hydrated);
      setShowPreviewModal(true);
    } catch (err) {
      setMessage(`Nao foi possivel carregar o resumo do relatorio\n\nMotivo:\n${err.message}`);
    } finally {
      setIsEditingLoading(false);
    }
  };
  const edit = async (report) => {
    if (isEditingLoading) return;
    setIsEditingLoading(true);
    try {
      const completeReport = await api(`/education-reports/${report.id}/`);
      const reportAgendaPk = agendaPk(completeReport.agenda);
      const reportAgendaLocal = agendas.find((agenda) => String(agenda.id) === String(reportAgendaPk));
      let reportAgenda = reportAgendaLocal;

      if (reportAgendaPk) {
        try {
          reportAgenda = await loadAgendaDetails(reportAgendaLocal || reportAgendaPk);
        } catch (err) {
          setMessage(`⚠ Não foi possível carregar os dados da agenda vinculada (Protocolo #${reportAgendaPk}). O formulário não pôde ser aberto.`);
          setIsEditingLoading(false);
          return;
        }
      }

      setEditing(completeReport.id);
      setProtocolSearch(reportAgenda?.service_order_number ? serviceOrderLabel(reportAgenda) : reportAgendaPk ? String(reportAgendaPk) : "");

      const resolvedDetails = completeReport.street_action_details?.length
        ? completeReport.street_action_details
        : (reportAgenda?.street_action_details || []);

      const hydrated = hydrateForm({
        ...completeReport,
        street_action_details: resolvedDetails
      }, reportAgenda, actionTypes);

      setForm(hydrated);
      setMessage("");
      setActiveTab("pending");
    } finally {
      setIsEditingLoading(false);
    }
  };

  const approveReport = async (id) => {
    if (isApproving) return;
    setIsApproving(true);
    try {
      await api(`/education-reports/${id}/approve/`, { method: "POST" });
      setMessage("Relat\u00f3rio aprovado com sucesso. A Estat\u00edstica Institucional foi atualizada automaticamente.");
      load();
    } catch (err) {
      alert(`Erro ao aprovar: ${err.message}`);
    } finally {
      setIsApproving(false);
    }
  };

  const returnReport = (id) => {
    setReturnModalReportId(id);
    setReturnNotes("");
  };

  const confirmReturn = async () => {
    if (!returnNotes.trim()) {
      alert("A justificativa é obrigatória.");
      return;
    }
    try {
      await api(`/education-reports/${returnModalReportId}/return-for-correction/`, {
        method: "POST",
        body: JSON.stringify({ notes: returnNotes })
      });
      setReturnModalReportId(null);
      setReturnNotes("");
      load();
    } catch (err) {
      alert(`Erro ao devolver: ${err.message}`);
    }
  };

  const reset = () => {
    setEditing(null);
    setProtocolSearch("");
    setForm({ ...empty, actions: [{ ...emptyAction }] });
    setMessage("");
    setActiveTab("pending");
  };

  const copyPreview = () => {
    navigator.clipboard?.writeText(preview);
    setMessage("Relatório copiado para a área de transferência.");
  };

  const handleShareReport = async () => {
    if (!hasShareableReport) return;

    await executeShare(reportShareSummary, {
      navigatorShare:
        typeof navigator !== "undefined" && typeof navigator.share === "function"
          ? navigator.share.bind(navigator)
          : undefined,
      locationAssign: (url) => window.location.assign(url),
    });
  };

  const handleSubmittedReportShare = async () => {
    const result = await executeShare(submittedShareSummary, {
      navigatorShare:
        typeof navigator !== "undefined" && typeof navigator.share === "function"
          ? navigator.share.bind(navigator)
          : undefined,
      locationAssign: (url) => window.location.assign(url),
    });

    if (result.status === "shared") setSubmittedShareSummary("");
  };

  const openHistoricalReportPreview = async (r) => {
    setReportsPreviewModal(r);
    setResolvedHistoricalAgenda(null);
    setHistoricalScheduleMembers(null);
    setHistoricalAgendaError("");
    setIsLoadingHistoricalAgenda(false);

    const reportAgendaPk = agendaPk(r.agenda);
    const localAgenda = agendas.find((a) => String(a.id) === String(reportAgendaPk));
    const resolveHistoricalAgenda = async () => {
      if (localAgenda) {
        setResolvedHistoricalAgenda(localAgenda);
        return localAgenda;
      }
      if (!reportAgendaPk) {
        setHistoricalAgendaError("Relatório sem Agenda vinculada.");
        return null;
      }

      setIsLoadingHistoricalAgenda(true);
      try {
        const data = await api(`/agendas/${reportAgendaPk}/`);
        setResolvedHistoricalAgenda(data);
        return data;
      } catch (err) {
        setHistoricalAgendaError("Não foi possível carregar os dados da Agenda deste relatório.");
        return null;
      } finally {
        setIsLoadingHistoricalAgenda(false);
      }
    };

    const historicalAgenda = await resolveHistoricalAgenda();
    if (!historicalAgenda || historicalAgenda.service_order_mode === "DESIGNATED") {
      return;
    }

    try {
      const members = await fetchScheduleMembersForContext(r.operation_date, r.team, historicalAgenda);
      setHistoricalScheduleMembers(members);
    } catch {
      setHistoricalScheduleMembers(null);
    }
  };

  return (
    <>
    <section className="page two-column report-editor">
      {activeTab !== "completed" && !isVisitor && (
      <div className="main-column">
        <div className="page-title">
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: "12px", flexWrap: "wrap", marginBottom: "4px" }}>
              <h1 style={{ margin: 0 }}>Relatório Técnico</h1>
              {pendingAgendas.length > 0 && (
                <span
                  style={{
                    background: "#ef6b5a",
                    color: "#fff",
                    padding: "4px 10px",
                    borderRadius: "20px",
                    fontSize: "12px",
                    fontWeight: "800",
                    display: "inline-flex",
                    alignItems: "center",
                    boxShadow: "0 4px 10px rgba(239, 107, 90, 0.3)",
                    animation: "pulse 2s infinite"
                  }}
                >
                  {pendingAgendas.length} {pendingAgendas.length === 1 ? "PENDENTE" : "PENDENTES"}
                </span>
              )}
            </div>
            <p style={{ margin: 0 }}>Busque a OS da agenda realizada, vincule o relatório e registre a execução da equipe.</p>
          </div>
        </div>

        {loadError && <div className="alert">{loadError}</div>}

        <form className="table-wrap report-form" onSubmit={submit}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: "12px", flexWrap: "wrap" }}>
            <h2 style={{ margin: 0 }}>{reportName(form)}</h2>
            <button type="button" className="secondary" onClick={() => setShowPreviewModal(true)} style={{ padding: "8px 12px", fontSize: "12px", fontWeight: "800" }}>
              <Clipboard size={14} /> Consultar resumo
            </button>
          </div>

          <div className="form-section">
            <h3>Ordem de serviço da agenda</h3>
            <div className="protocol-search">
              <input placeholder="Digite a OS, ex: OS 0004" value={protocolSearch} onChange={(event) => setProtocolSearch(event.target.value)} />
              <button type="button" className="secondary" onClick={findServiceOrder}><Search size={18} /> Buscar</button>
            </div>
            {(selectedAgenda || form.agenda) && (
              <div className="report-context">
                <strong>{selectedAgenda ? agendaSummary(selectedAgenda) : `#${form.agenda} - ${form.agenda_title}`}</strong>
                <span>{form.agenda_location || "Local não informado"}</span>
                <span>Equipe: {form.team || "não informada"}</span>
                {form.status === "RETURNED" && form.review_notes && (
                  <div style={{ background: "var(--danger-dim)", color: "var(--danger)", padding: "8px 12px", borderRadius: "6px", marginTop: "8px", fontSize: "13px" }}>
                    <strong>Devolvido para correção:</strong> {form.review_notes}
                  </div>
                )}
              </div>
            )}
          </div>

          <div className="form-section">
            <h3>Identificação</h3>
            <div className="compact-grid three-cols">
              <label className="field-label">
                <span>Chefe responsável</span>
                <input value={operationalResponsibility.chief || (selectedAgenda ? chiefFromAgenda(selectedAgenda) || chiefFromReport(form) : chiefFromReport(form))} readOnly />
              </label>
              <label className="field-label">
                <span>Data</span>
                <input id="input-operation-date" type="date" value={form.operation_date} onChange={(event) => update("operation_date", event.target.value)} readOnly={requestFieldsReadOnly} required />
              </label>
              <label className="field-label">
                <span>Equipe</span>
                <input id="input-team" value={form.team} onChange={(event) => update("team", event.target.value)} readOnly={requestFieldsReadOnly} required />
              </label>
            </div>
          </div>



          <div className="form-section">
            <h3>Efetivo e recursos</h3>
            <label className="field-label">
              <span>Público aproximado</span>
              <input
                type="number"
                min="0"
                step="1"
                value={form.approximate_public || ""}
                onChange={(event) => update("approximate_public", event.target.value.replace(/\D/g, ""))}
                inputMode="numeric"
              />
            </label>
            <label className="field-label report-text-box">
              <span>Dados da solicitação</span>
              <textarea value={form.request_details || ""} readOnly />
            </label>
            <label className="field-label report-text-box">
              <span>Agentes de Educação</span>
              <textarea value={form.education_agents || ""} onChange={(event) => update("education_agents", event.target.value)} readOnly={requestFieldsReadOnly} />
            </label>
            <label className="field-label report-text-box">
              <span>Alterações de Efetivo</span>
              <textarea value={form.changes_staff || ""} onChange={(event) => update("changes_staff", event.target.value)} readOnly={requestFieldsReadOnly} />
            </label>
            <label className="field-label report-text-box">
              <span>Recursos, kits e materiais</span>
              <textarea value={form.breathalyzers || ""} onChange={(event) => update("breathalyzers", event.target.value)} readOnly={requestFieldsReadOnly} />
            </label>
            <label className="field-label report-text-box">
              <span>Viaturas</span>
              <textarea value={form.cars || ""} onChange={(event) => update("cars", event.target.value)} readOnly={requestFieldsReadOnly} />
            </label>
          </div>

          {isStreetAction && (
            <div className="form-section">
              <h3>Detalhes da Ação de Rua</h3>
              <p style={{ fontSize: "0.85rem", color: "var(--text-soft)", marginBottom: "12px" }}>
                Tipos definidos na Ordem de Serviço para referência do chefe durante o relatório.
              </p>
              <div className="street-action-list street-action-summary-list">
                {(form.street_action_details || []).length ? (
                  (form.street_action_details || []).map((detail, idx) => (
                    <div key={idx} className="street-action-summary-card">
                      <div>
                        <strong>{detail.type ? streetActionTypeLabel(detail.type) : `Ação ${idx + 1}`}</strong>
                        {showEstimatedPublic && (
                          <small>{detail.public ? `Público estimado: ${detail.public}` : "Público estimado não informado"}</small>
                        )}
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="street-action-summary-card">
                    <div>
                      <strong>Nenhum tipo de ação cadastrado na OS</strong>
                      <small>O chefe seguirá apenas com o preenchimento do relatório técnico.</small>
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          <div className="form-section chief-flow-section">
            <div className="chief-required-block chief-required-block-standalone">
              <h4>PREENCHIMENTO OBRIGATÓRIO</h4>
              <div className="compact-grid horus-count-grid">
                {numberFields.map((field) => {
                  if (field === "approach" && !showEstimatedPublic) {
                    return null;
                  }
                  return (
                    <label className={`field-label ${field === "approach" ? "" : "chief-highlight-field"}`.trim()} key={field}>
                      <span>{fieldLabels[field]}</span>
                      <input
                        type="number"
                        value={(form.actions[0] || emptyAction)[field] ?? ""}
                        className={field === "approach" ? "read-only-field" : ""}
                        readOnly={field === "approach"}
                        title={field === "approach" ? "Preenchido automaticamente a partir da solicitação" : ""}
                        onChange={(e) => updateAllActionsField(field, e.target.value)}
                      />
                    </label>
                  );
                })}
                <label className="field-label chief-highlight-field">
                  <span>O local atendeu às condições de acessibilidade para cadeirantes?</span>
                  <select
                    id="select-accessibility"
                    value={form.accessibility_conditions_met || ""}
                    onChange={(event) => update("accessibility_conditions_met", event.target.value)}
                    required
                  >
                    <option value="">Selecione</option>
                    <option value="YES">Sim</option>
                    <option value="NO">Não</option>
                  </select>
                </label>
              </div>
              <small>Bloco de preenchimento obrigatório pelo chefe. Se a resposta for não, a instituição ou solicitante entrará na lista de restrição para novas solicitações.</small>

              <div className="chief-flow-group">
                <div className="chief-flow-header">
                  <div>
                    <h5>Ações Definidas pelo Chefe</h5>
                    <p>Organize as ações realizadas em cards mais compactos e objetivos.</p>
                  </div>
                  <button type="button" className="secondary" onClick={addAction}><Plus size={18} /> Adicionar ação</button>
                </div>
                <div className="chief-actions-stack">
                  {form.actions.map((action, index) => (
                    <div className="horus-action-card chief-flow-action-card" key={index}>
                      {(() => {
                        const displayedAgreementIndicator = getDisplayedAgreementIndicator(action, selectedAgenda, index);
                        const displayedAgreementLabel = agreementIndicatorLabel(displayedAgreementIndicator);
                        const actionIsStreet = actionMode(action, selectedAgenda, index) === "STREET";
                        return (
                          <>
                      <div className="action-card-header">
                        <strong>{`Ação ${index + 1}`}</strong>
                        <button type="button" className="secondary icon-button" onClick={() => removeAction(index)} aria-label="Remover ação">
                          <Trash2 size={16} />
                        </button>
                      </div>
                      <div className="compact-grid chief-action-grid">
                        {index > 0 && (
                          <label className="field-label chief-highlight-field chief-action-select">
                            <span>Modalidade desta ação</span>
                            <select value={actionIsStreet ? "STREET" : "LECTURE"} onChange={(event) => updateAction(index, "action_mode", event.target.value)}>
                              <option value="STREET">Ação de Rua</option>
                              <option value="LECTURE">Palestra/Ação Educativa</option>
                            </select>
                          </label>
                        )}
                        <label className={`field-label ${requestFieldsReadOnly && !action.__userCreated ? "" : "chief-highlight-field"}`.trim()}>
                          <span>Instituição/Local</span>
                          <input value={action.institution_name || ""} onChange={(event) => updateAction(index, "institution_name", event.target.value)} readOnly={requestFieldsReadOnly && !action.__userCreated} />
                        </label>
                        <label className={`field-label ${requestFieldsReadOnly && !action.__userCreated ? "" : "chief-highlight-field"}`.trim()}>
                          <span>Endereço do Local</span>
                          <input value={action.place_action || ""} onChange={(event) => updateAction(index, "place_action", event.target.value)} readOnly={requestFieldsReadOnly && !action.__userCreated} />
                        </label>
                        <label className={`field-label ${requestFieldsReadOnly && !action.__userCreated ? "" : "chief-highlight-field"}`.trim()}>
                          <span>Horário inicial</span>
                          <input value={action.start_time || ""} onChange={(event) => updateAction(index, "start_time", event.target.value)} readOnly={requestFieldsReadOnly && !action.__userCreated && index !== 0} />
                        </label>
                        <label className={`field-label ${requestFieldsReadOnly && !action.__userCreated ? "" : "chief-highlight-field"}`.trim()}>
                          <span>Horário final</span>
                          <input value={action.final_hour || ""} onChange={(event) => updateAction(index, "final_hour", event.target.value)} readOnly={requestFieldsReadOnly && !action.__userCreated && index !== 0} />
                        </label>
                        {!actionIsStreet ? (
                          <label className="field-label chief-highlight-field chief-action-select">
                            <span>Tipo da palestra/ação realizada *</span>
                            <select
                              id={`select-type-action-${index}`}
                              value={action.type_action || ""}
                              onChange={(event) => updateAction(index, "type_action", event.target.value)}
                              required
                            >
                              <option value="">Selecione</option>
                              {operationalActionTypeOptions.map((option) => (
                                <option key={option.id || option.name} value={option.name}>{option.name}</option>
                              ))}
                          </select>
                            {displayedAgreementLabel && (
                              <small>Indicador identificado: {displayedAgreementLabel}</small>
                            )}
                          </label>
                        ) : null}
                        {!actionIsStreet ? (
                          <>
                            <label className="field-label chief-highlight-field">
                              <span>Tipo de solicitante</span>
                              <select
                                value={action.requester_entity_kind || ""}
                                onChange={(event) => updateAction(index, "requester_entity_kind", event.target.value)}
                              >
                                <option value="">Selecione</option>
                                {REQUESTER_ENTITY_KIND_OPTIONS.map((option) => (
                                  <option key={option.value} value={option.value}>{option.label}</option>
                                ))}
                              </select>
                            </label>
                            <label className="field-label chief-highlight-field">
                              <span>Público ou Privado?</span>
                              <select
                                value={action.requester_entity_nature || ""}
                                onChange={(event) => updateAction(index, "requester_entity_nature", event.target.value)}
                              >
                                <option value="">Selecione</option>
                                {REQUESTER_ENTITY_NATURE_OPTIONS.map((option) => (
                                  <option key={option.value} value={option.value}>{option.label}</option>
                                ))}
                              </select>
                            </label>
                            <label className="field-label chief-highlight-field">
                              <span>Faixa etária</span>
                              <select
                                value={action.age_range || ""}
                                onChange={(event) => updateAction(index, "age_range", event.target.value)}
                              >
                                <option value="">Selecione</option>
                                {EDUCATION_ACTION_AGE_RANGE_OPTIONS.map((option) => (
                                  <option key={option.value} value={option.value}>{option.label}</option>
                                ))}
                              </select>
                            </label>
                          </>
                        ) : null}
                        <label className="field-label chief-highlight-field">
                          <span>Número de abordagens</span>
                          <input
                            type="number"
                            min="0"
                            step="1"
                            value={action.approached_actions ?? ""}
                            onChange={(e) => updateAction(index, "approached_actions", e.target.value)}
                          />
                        </label>
                        {actionIsStreet ? (
                          <label className={`field-label chief-action-select ${shouldHighlightChiefTypeAction(action, index) ? "chief-highlight-field" : ""}`.trim()}>
                            <span>Ação Definida pelo Chefe</span>
                            <select
                              id={`select-type-action-${index}`}
                              value={isMissingLegacyStreetSubtype(action.type_action) ? "" : (action.type_action || "")}
                              onChange={(event) => updateAction(index, "type_action", event.target.value)}
                              disabled={requestFieldsReadOnly && !action.__userCreated && !shouldRequireLegacyStreetActionType && index !== 0}
                              required
                            >
                              <option value="">Selecione</option>
                              {streetActionTypeOptions.map((option) => (
                                <option key={option} value={option}>{streetActionTypeLabel(option)}</option>
                              ))}
                              {action.type_action && !isMissingLegacyStreetSubtype(action.type_action) && !streetActionTypeOptions.includes(action.type_action) && (
                                <option value={action.type_action}>{streetActionTypeLabel(action.type_action)}</option>
                              )}
                            </select>
                            {isMissingLegacyStreetSubtype(action.type_action) && (
                              <small>Selecione o tipo da ação de rua para classificar corretamente a estatística.</small>
                            )}
                          </label>
                        ) : null}
                      </div>
                          </>
                        );
                      })()}
                      {(() => {
                        const safeAgenda = selectedAgenda || {};
                        const cats = extractMaterialCategories(safeAgenda);

                        let removedItems = [];
                        if (cats.kits.length > 0) {
                          removedItems = cats.kits.filter(k => (parseInt(k.quantity, 10) || 0) > 0);
                        } else {
                          const baseAction = form.actions[0] || {};
                          const removedStr = baseAction.distribution_materials_removed || "";
                          removedItems = parseMaterialRows(removedStr).filter(k => (parseInt(k.quantity, 10) || 0) > 0);
                        }

                        if (!removedItems.length) return null;

                        const actionDistributedValue = action.distribution_materials_distributed || serializeBlankMaterialRows(removedItems);

                        return (
                          <div style={{ marginTop: 12, display: "flex", flexDirection: "column", gap: "10px" }}>
                            <div className="field-label report-text-box">
                              <span>Material retirado para esta Ordem de Serviço (OS)</span>
                              <div className="material-entry-card material-entry-card-readonly" style={{ background: "var(--surface)", border: "1px solid var(--line)" }}>
                                <div className="material-entry-list">
                                  {removedItems.map((row, rowIndex) => (
                                    <div key={`${row.name}-${rowIndex}`} style={{ padding: "6px 0", borderBottom: rowIndex === removedItems.length - 1 ? "none" : "1px solid var(--line-light)", display: "flex", justifyContent: "space-between", fontSize: "13px", fontWeight: "600" }}>
                                      <span>{row.name}</span>
                                      <span>{row.quantity}</span>
                                    </div>
                                  ))}
                                </div>
                              </div>
                            </div>

                            <div className="report-material-grid chief-material-grid">
                              <div className="field-label report-text-box chief-highlight-field">
                                <span>Material distribuído nesta ação</span>
                                <MaterialQuantityEditor
                                  value={actionDistributedValue}
                                  onChange={(value) => updateAction(index, "distribution_materials_distributed", value)}
                                />
                              </div>
                            </div>
                          </div>
                        );
                      })()}
                    </div>
                  ))}
                </div>
              </div>

              {(() => {
                const safeAgenda = selectedAgenda || {};
                const cats = extractMaterialCategories(safeAgenda);

                let removedItems = [];
                if (cats.kits.length > 0) {
                  removedItems = cats.kits.filter(k => (parseInt(k.quantity, 10) || 0) > 0);
                } else {
                  const baseAction = form.actions[0] || emptyAction;
                  const removedStr = baseAction.distribution_materials_removed || "";
                  removedItems = parseMaterialRows(removedStr).filter(k => (parseInt(k.quantity, 10) || 0) > 0);
                }

                if (!removedItems.length) return null;

                const removedValue = serializeMaterialRows(removedItems);
                const distributedValue = form.distribution_materials_distributed || serializeBlankMaterialRows(removedItems);
                const distributedItems = parseMaterialRows(distributedValue);

                return (
                  <div className="chief-flow-group">
                    <div className="chief-flow-header chief-flow-header-inline">
                      <div>
                        <h5>Materiais para Distribuição</h5>
                        <p>Visualização consolidada de materiais retirados e distribuídos nesta Ordem de Serviço.</p>
                      </div>
                    </div>
                    <div className="report-material-grid chief-material-grid">
                      <div className="field-label report-text-box">
                        <span>Material para Distribuição retirado</span>
                        <MaterialSummary value={removedValue} />
                      </div>
                      <div className="field-label report-text-box">
                        <span>Material distribuído (total retirado / OS)</span>
                        <MaterialSummary value={distributedValue} />
                      </div>
                    </div>

                    <div style={{ marginTop: 12, padding: "12px", background: "var(--surface)", border: "1px solid var(--line)", borderRadius: "8px" }}>
                      <strong style={{ fontSize: "11px", color: "var(--text-soft)", textTransform: "uppercase", display: "block", marginBottom: "8px", fontWeight: "700" }}>Indicadores de Distribuição</strong>
                      <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                        {removedItems.map((row, rowIndex) => {
                          const removedQty = parseInt(row.quantity, 10) || 0;
                          const distRow = distributedItems.find(item => item.name.toLowerCase() === row.name.toLowerCase());
                          const distributedQty = distRow ? (parseInt(distRow.quantity, 10) || 0) : 0;
                          const difference = removedQty - distributedQty;

                          return (
                            <div key={`${row.name}-${rowIndex}`} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", paddingBottom: "6px", borderBottom: "1px dashed var(--line-light)" }}>
                              <strong style={{ fontSize: "14px", color: "var(--text)" }}>{row.name}</strong>
                              <div style={{ display: "flex", gap: "12px", alignItems: "center" }}>
                                {distributedQty === removedQty ? (
                                  <span style={{ fontSize: "12px", color: "var(--success)", fontWeight: "700" }}>
                                    Distribuído: {distributedQty} / {removedQty} ✔
                                  </span>
                                ) : (
                                  <span style={{ fontSize: "12px", color: "var(--text-soft)", fontWeight: "600" }}>
                                    Distribuído: {distributedQty} / {removedQty}
                                  </span>
                                )}
                                {difference > 0 ? (
                                  <span style={{ fontSize: "12px", color: "var(--warning)", fontWeight: "700" }}>
                                    Restam: {difference}
                                  </span>
                                ) : null}
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  </div>
                );
              })()}
            </div>
          </div>

          {(reportSchedule || selectedAgenda?.service_order_mode === "DESIGNATED") && (
            <div className="form-section attendance-highlight-section">
              <h3>Frequência {reportSchedule ? "da Equipe" : "dos Participantes"}</h3>
              <p style={{ fontSize: "0.85rem", color: "var(--text-soft)", marginBottom: "12px" }}>
                Gerencie as presenças e faltas do efetivo lançado para este evento.
              </p>
              <button
                id="attendance-block"
                type="button"
                className="secondary attendance-highlight-button"
                onClick={() => setIsAttendanceModalOpen(true)}
              >
                <Clipboard size={18} /> Gerenciar Frequência
              </button>
            </div>
          )}



          <div className="form-section">
            <h3>Contato, ocorrências e localização</h3>

            <input
              placeholder="Contato recebido"
              value={form.contact_received || ""}
              onChange={(event) => update("contact_received", event.target.value)}
              onBlur={(event) => update("contact_received", formatContactValue(event.target.value))}
              readOnly={requestFieldsReadOnly}
            />
            <div style={{ display: "grid", gap: "8px", marginTop: "8px", marginBottom: "12px" }}>
              <label className="field-label" htmlFor="select-has-exceptional-occurrence">
                Ocorrência envolvendo viatura ou efetivo?
              </label>
              <select
                id="select-has-exceptional-occurrence"
                value={form.has_exceptional_occurrence ? "true" : "false"}
                onChange={(event) => updateExceptionalOccurrence(event.target.value === "true")}
                disabled={!isEditableTechnicalReport}
              >
                <option value="false">Não</option>
                <option value="true">Sim</option>
              </select>
              <small style={{ color: "var(--text-soft)", lineHeight: 1.4 }}>
                Preencher somente em situações excepcionais que tenham afetado ou colocado em risco a execução da atividade. Não utilizar para observações rotineiras.
              </small>
            </div>
            {form.has_exceptional_occurrence && (
              <div style={{ display: "grid", gap: "12px", marginBottom: "12px" }}>
                <label className="field-label">
                  Tipo de ocorrência
                  <select
                    id="select-exceptional-occurrence-type"
                    value={form.exceptional_occurrence_type || ""}
                    onChange={(event) => update("exceptional_occurrence_type", event.target.value)}
                    disabled={!isEditableTechnicalReport}
                  >
                    <option value="">Selecione</option>
                    {exceptionalOccurrenceTypeOptions.map((option) => (
                      <option key={option.value} value={option.value}>{option.label}</option>
                    ))}
                  </select>
                </label>
                <label className="field-label">
                  Descrição da ocorrência
                  <textarea
                    id="input-exceptional-occurrence-description"
                    className="chief-highlight-input"
                    value={form.exceptional_occurrence_description || ""}
                    onChange={(event) => update("exceptional_occurrence_description", event.target.value)}
                    readOnly={!isEditableTechnicalReport}
                  />
                </label>
                <label className="field-label">
                  Providências adotadas
                  <textarea
                    id="input-exceptional-occurrence-actions"
                    className="chief-highlight-input"
                    value={form.exceptional_occurrence_actions_taken || ""}
                    onChange={(event) => update("exceptional_occurrence_actions_taken", event.target.value)}
                    readOnly={!isEditableTechnicalReport}
                  />
                </label>
                <label className="field-label">
                  Impacto na atividade
                  <select
                    id="select-exceptional-occurrence-impact"
                    value={form.exceptional_occurrence_impact || ""}
                    onChange={(event) => update("exceptional_occurrence_impact", event.target.value)}
                    disabled={!isEditableTechnicalReport}
                  >
                    <option value="">Selecione</option>
                    {exceptionalOccurrenceImpactOptions.map((option) => (
                      <option key={option.value} value={option.value}>{option.label}</option>
                    ))}
                  </select>
                </label>
              </div>
            )}
            <textarea className="chief-highlight-input" placeholder="Dados e Observações" value={form.general_observations || ""} onChange={(event) => update("general_observations", event.target.value)} />
            <textarea className="chief-highlight-input" placeholder="Observação de ocorrência" value={form.occurrence_observation || ""} onChange={(event) => update("occurrence_observation", event.target.value)} />
          </div>

          {message && <div className="alert" style={{ whiteSpace: "pre-wrap" }}>{message}</div>}
          {submittedShareSummary && (
            <div className="alert" style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: "12px", flexWrap: "wrap" }}>
              <span><strong>Relatório enviado.</strong> Compartilhe o resumo estruturado pelo WhatsApp.</span>
              <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
                <button type="button" className="secondary" onClick={() => setSubmittedShareSummary("")}>Agora não</button>
                <button type="button" onClick={handleSubmittedReportShare}><Share2 size={16} /> Compartilhar relatório</button>
              </div>
            </div>
          )}
          <div className="report-submit-actions">
            {!["PENDING_REVIEW", "APPROVED"].includes(form.status) ? (
              <>
                <button type="submit" formNoValidate className="secondary" disabled={isSaving}><Save size={18} /> Salvar rascunho</button>
                <button type="button" onClick={submitFinal} disabled={isSaving}><Save size={18} /> Enviar para conferência</button>
              </>
            ) : (
              <button type="button" className="primary" disabled={isSaving} onClick={submitRectify}><Edit3 size={18} /> Retificar relatório</button>
            )}
          </div>
        </form>
      </div>
      )}

      {isAttendanceModalOpen && (
        <div className="modal-backdrop" style={{ zIndex: 9999 }}>
          <article className="modal attendance-modal" onClick={(e) => e.stopPropagation()}>
            <header className="modal-header attendance-modal-header">
              <h2 style={{ display: "flex", alignItems: "center", gap: "10px", margin: 0 }}>
                <Clipboard size={20} />
                Gerenciar Frequência - {reportSchedule ? reportSchedule.team : "Participantes Individuais"}
              </h2>
              <button className="icon-btn" type="button" onClick={() => setIsAttendanceModalOpen(false)}>
                <X size={20} />
              </button>
            </header>
            <div className="modal-body attendance-modal-body">
              {(reportSchedule || selectedAgenda?.service_order_mode === "DESIGNATED") && (
                <div className="attendance-manager-list attendance-modal-list">
                  {Object.entries(attendanceForm).map(([key, data]) => (
                    <div key={key} className="attendance-member-card">
                      <div className="attendance-member-head">
                        <div className="attendance-member-name">
                          {data.member.name} <small style={{ color: "var(--text-soft)" }}>({data.member.typeLabel})</small>
                        </div>
                        <div className="attendance-member-options">
                          <label className="attendance-option">
                            <input
                              type="radio"
                              name={`modal_status_${key}`}
                              checked={data.is_absent === false}
                              onChange={() => setAttendanceForm(prev => ({ ...prev, [key]: { ...prev[key], is_absent: false } }))}
                            />
                            <span style={{ color: data.is_absent === false ? "#15803d" : "inherit", fontWeight: data.is_absent === false ? "bold" : "normal" }}>Presente</span>
                          </label>
                          <label className="attendance-option">
                            <input
                              type="radio"
                              name={`modal_status_${key}`}
                              checked={data.is_absent === true}
                              onChange={() => setAttendanceForm(prev => ({ ...prev, [key]: { ...prev[key], is_absent: true } }))}
                            />
                            <span style={{ color: data.is_absent === true ? "#b91c1c" : "inherit", fontWeight: data.is_absent === true ? "bold" : "normal" }}>Falta</span>
                          </label>
                        </div>
                      </div>
                      {data.is_absent && (
                        <div className="attendance-absence-box">
                          <label style={{ display: "block", marginBottom: "10px" }}>
                            <span style={{ display: "block", fontSize: "0.85rem", marginBottom: "4px" }}>Justificativa</span>
                            <input
                              type="text"
                              value={data.reason}
                              onChange={(e) => setAttendanceForm(prev => ({ ...prev, [key]: { ...prev[key], reason: e.target.value } }))}
                              placeholder="Ex: Férias, Atestado, etc."
                              style={{ width: "100%", padding: "6px", border: "1px solid #ccc", borderRadius: "4px" }}
                            />
                          </label>
                          <label style={{ display: "block" }}>
                            <span style={{ display: "block", fontSize: "0.85rem", marginBottom: "4px" }}>Comprovante (opcional)</span>
                            <input
                              type="file"
                              onChange={(e) => setAttendanceForm(prev => ({ ...prev, [key]: { ...prev[key], attachment: e.target.files?.[0] || null } }))}
                              style={{ fontSize: "0.85rem" }}
                            />
                          </label>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}

            </div>
            <div className="modal-footer attendance-modal-footer">
              <button type="button" className="secondary" onClick={() => setIsAttendanceModalOpen(false)}>Cancelar</button>
              <button
                type="button"
                className="primary"
                onClick={async () => {
                  try {
                    await saveAttendance({ markReported: true, successMessage: "Presenças enviadas para validação." });
                  } catch (err) {
                    setMessage(`⚠ Não foi possível salvar a frequência\n\nMotivo:\n${err.message}`);
                  }
                }}
                disabled={isSavingAttendance || Object.values(attendanceForm).some(d => d.is_absent === null)}
                title={Object.values(attendanceForm).some(d => d.is_absent === null) ? "Selecione a frequência de todos os membros" : ""}
              >
                {isSavingAttendance ? "Salvando..." : "Salvar e enviar para validação"}
              </button>
            </div>
          </article>
        </div>
      )}


      {activeTab === "completed" && (
        <div className="main-column" style={{ maxWidth: "100%" }}>
          <div className="page-title">
            <div>
              <h1 style={{ margin: 0 }}>Relatórios Técnicos</h1>
              <p style={{ margin: 0 }}>Visão geral unificada dos relatórios e execuções técnicas.</p>
            </div>
          </div>
          <div style={{ animation: "fadeIn 0.4s ease" }}>
            <div className="filters glass-card" style={{ marginBottom: 24, display: 'flex', gap: 16 }}>
              <div className="filter-field">
                <span>OS</span>
                <input placeholder="Ex: 2610" value={pendingTechFilters.q} onChange={(e) => setPendingTechFilters({ ...pendingTechFilters, q: e.target.value })} />
              </div>
              <div className="filter-field">
                <span>Equipe</span>
                <input placeholder="Ex: E1" value={pendingTechFilters.team} onChange={(e) => setPendingTechFilters({ ...pendingTechFilters, team: e.target.value })} />
              </div>
              <div className="filter-field">
                <span>Data</span>
                <input type="date" value={pendingTechFilters.date} onChange={(e) => setPendingTechFilters({ ...pendingTechFilters, date: e.target.value })} />
              </div>
              {!isVisitor && (
                <div className="filter-field">
                  <span>Status</span>
                  <select value={pendingTechFilters.status} onChange={(e) => setPendingTechFilters({ ...pendingTechFilters, status: e.target.value })}>
                    <option value="">Todos</option>
                    <option value="PENDING_REVIEW">Pendente</option>
                    <option value="APPROVED">Aprovado</option>
                    <option value="DRAFT">Rascunho</option>
                    <option value="RETURNED">Devolvido</option>
                  </select>
                </div>
              )}
              <div style={{ alignSelf: 'flex-end' }}>
                <button onClick={() => setTechFilters(isVisitor ? { ...pendingTechFilters, status: "APPROVED" } : pendingTechFilters)}>Pesquisar</button>
              </div>
            </div>

            <div className="premium-table-wrap">
              <h2>Relatórios Técnicos Registrados</h2>
              <table>
                <thead>
                  <tr>
                    <th>OS</th>
                    <th>Nome da Equipe</th>
                    <th>Data</th>
                    <th>Status</th>
                    <th>Ações Realizadas</th>
                    <th style={{ width: 140 }}>Detalhes</th>
                  </tr>
                </thead>
                <tbody>
                  {reports.length === 0 && (
                    <tr><td colSpan="6" style={{ textAlign: "center", padding: 32 }}>Nenhum relatório encontrado.</td></tr>
                  )}
                  {reports.map((r) => (
                    <tr key={r.id}>
                      <td><strong>{r.agenda_service_order_number ? `OS ${r.agenda_service_order_number}` : r.agenda ? `#${r.agenda}` : "-"}</strong></td>
                      <td>{reportName(r)}</td>
                      <td>{formatDateBR(r.operation_date)}</td>
                      <td>
                        <span style={{
                          background: r.status === "APPROVED" ? "var(--success)" :
                                      r.status === "PENDING_REVIEW" ? "#f59e0b" :
                                      r.status === "RETURNED" ? "var(--danger)" : "var(--warning)",
                          color: "#fff", padding: "4px 8px", borderRadius: 4, fontSize: 11, fontWeight: "bold"
                        }}>
                          {r.status === "APPROVED" ? "APROVADO" :
                           r.status === "PENDING_REVIEW" ? "PENDENTE" :
                           r.status === "RETURNED" ? "DEVOLVIDO" : "RASCUNHO"}
                        </span>
                      </td>
                      <td>{r.actions_count || r.actions?.length || 0} ações</td>
                      <td style={{ display: "flex", gap: "4px", flexWrap: "wrap" }}>
                        {isVisitor ? (
                          <button className="secondary" onClick={() => viewReport(r)} title="Visualizar Resumo" disabled={isEditingLoading}>
                            <Eye size={16} /> Visualizar Resumo
                          </button>
                        ) : (
                          <>
                            <button className="secondary icon-button" onClick={() => viewReport(r)} title="Visualizar Resumo" disabled={isEditingLoading}>
                              <Eye size={16} />
                            </button>
                            {["DRAFT", "RETURNED"].includes(r.status) ? (
                              <button className="secondary" onClick={() => edit(r)} title="Corrigir relatório" disabled={isEditingLoading}>
                                <Edit3 size={16} /> Corrigir
                              </button>
                            ) : (
                              <button className="secondary icon-button" onClick={() => edit(r)} title="Editar" disabled={isEditingLoading}>
                                <Clipboard size={16} />
                              </button>
                            )}
                            {isAdmin && r.status === "PENDING_REVIEW" && (
                              <>
                                <button className="primary icon-button" onClick={() => approveReport(r.id)} title="Aprovar" disabled={isApproving}>
                                  <Check size={16} />
                                </button>
                                <button className="danger icon-button" onClick={() => returnReport(r.id)} title="Devolver para correção" style={{ background: "var(--danger)", color: "#fff", border: "none" }} disabled={isApproving}>
                                  <X size={16} />
                                </button>
                              </>
                            )}
                          </>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {reportsPreviewModal && (
            <div className="modal-overlay" onClick={() => {
              setReportsPreviewModal(null);
              setResolvedHistoricalAgenda(null);
              setHistoricalScheduleMembers(null);
              setIsLoadingHistoricalAgenda(false);
              setHistoricalAgendaError("");
            }}>
              <div className="premium-modal" onClick={e => e.stopPropagation()}>
                <div className="modal-header-premium">
                  <h2>Detalhes do Relatório</h2>
                  <button className="secondary icon-button" onClick={() => {
                    setReportsPreviewModal(null);
                    setResolvedHistoricalAgenda(null);
                    setHistoricalScheduleMembers(null);
                    setIsLoadingHistoricalAgenda(false);
                    setHistoricalAgendaError("");
                  }}><X size={20} /></button>
                </div>
                <div className="modal-body-premium">
                  {isLoadingHistoricalAgenda ? (
                    <div style={{ padding: "20px", textAlign: "center", color: "var(--text-soft)" }}>Carregando dados da Agenda...</div>
                  ) : historicalAgendaError ? (
                    <div style={{ padding: "20px", textAlign: "center", color: "var(--danger)" }}>{historicalAgendaError}</div>
                  ) : resolvedHistoricalAgenda ? (
                    (() => {
                      const isHistoricalPublicRequest = resolvedHistoricalAgenda?.origin === "PUBLIC_FORM";
                      const isHistoricalStreetAction = isStreetActionAgenda(resolvedHistoricalAgenda) || Boolean(reportsPreviewModal?.street_action_details?.length);
                      const showHistoricalEstimatedPublic = !isHistoricalStreetAction || isHistoricalPublicRequest;
                      const historicalAgendaForPreview = buildAgendaForOperationalPreview(resolvedHistoricalAgenda, reportsPreviewModal, historicalScheduleMembers);
                      return <pre>{buildPreview(reportsPreviewModal, historicalAgendaForPreview, showHistoricalEstimatedPublic, historicalScheduleMembers)}</pre>;
                    })()
                  ) : null}
                </div>
              </div>
            </div>
          )}

          {returnModalReportId && (
            <div className="modal-overlay" onClick={() => setReturnModalReportId(null)}>
              <div className="premium-modal" onClick={e => e.stopPropagation()} style={{ maxWidth: 500 }}>
                <div className="modal-header-premium">
                  <h2>Devolver Relatório para Correção</h2>
                  <button className="secondary icon-button" onClick={() => setReturnModalReportId(null)}><X size={20} /></button>
                </div>
                <div className="modal-body-premium" style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                  <p style={{ margin: 0, fontSize: 14 }}>Informe a justificativa detalhada para o chefe responsável corrigir:</p>
                  <textarea
                    value={returnNotes}
                    onChange={(e) => setReturnNotes(e.target.value)}
                    placeholder="Digite a justificativa aqui..."
                    rows={4}
                    style={{ width: "100%", padding: 12, borderRadius: 6, border: "1px solid var(--line)" }}
                  />
                  <div className="attendance-member-head">
                    <small style={{ color: "var(--text-soft)" }}>{returnNotes.length} caracteres</small>
                    <div style={{ display: "flex", gap: 8 }}>
                      <button type="button" className="secondary" onClick={() => setReturnModalReportId(null)}>Cancelar</button>
                      <button type="button" className="primary" onClick={confirmReturn} disabled={!returnNotes.trim()}>Confirmar</button>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
      {!isVisitor && (
      <aside className="side-panel report-sidebar">
        <div className="sidebar-tabs" style={{ display: "flex", flexDirection: "column", gap: "8px", marginBottom: "16px", borderBottom: "1px solid var(--line)", paddingBottom: "12px" }}>
          <button type="button" className={activeTab === "pending" ? "active" : "secondary"} onClick={() => setActiveTab("pending")} style={{ width: "100%", fontSize: "12px", padding: "8px 10px", fontWeight: "700" }}>Pendentes ({pendingAgendas.length})</button>
          <button
            type="button"
            className={activeTab === "completed" ? "active" : "secondary"}
            onClick={() => {
              const nextFilters = { ...pendingTechFilters, status: "PENDING_REVIEW" };
              setPendingTechFilters(nextFilters);
              setTechFilters(nextFilters);
              setActiveTab("completed");
            }}
            style={{ width: "100%", fontSize: "12px", padding: "8px 10px", fontWeight: "700" }}
          >{"Aguardando aprova\u00e7\u00e3o"} ({pendingReviewReportsCount})</button>
          <button
            type="button"
            className={activeTab === "completed" && techFilters.status !== "PENDING_REVIEW" ? "active" : "secondary"}
            onClick={() => {
              const nextFilters = { ...pendingTechFilters, status: "" };
              setPendingTechFilters(nextFilters);
              setTechFilters(nextFilters);
              setActiveTab("completed");
            }}
            style={{ width: "100%", fontSize: "12px", padding: "8px 10px", fontWeight: "700" }}
          >{"Consultar relat\u00f3rios"}</button>
        </div>

        {activeTab === "pending" && (
          <div className="report-list-content" style={{ display: "flex", flexDirection: "column", gap: "10px", maxHeight: "calc(100vh - 180px)", overflowY: "auto", paddingRight: "4px" }}>
            <div style={{ marginBottom: "12px", background: "var(--surface)", border: "1px solid var(--line)", borderRadius: "8px", padding: "10px", display: "flex", flexDirection: "column", gap: "6px" }}>
              <span style={{ fontSize: "11px", fontWeight: "700", color: "var(--text-soft)" }}>FILTRAR PENDENTES</span>
              <div style={{ display: "flex", gap: "8px" }}>
                <input
                  type="date"
                  value={pendingDateFilter}
                  onChange={(e) => setPendingDateFilter(e.target.value)}
                  style={{ minHeight: "32px", fontSize: "12.5px", padding: "4px 8px", flex: 1 }}
                />
              </div>
              <div style={{ display: "flex", gap: "8px" }}>
                <input
                  type="text"
                  placeholder="Buscar chefe na base..."
                  value={pendingChiefFilter}
                  onChange={(e) => setPendingChiefFilter(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      setPendingChiefQuery(pendingChiefFilter);
                    }
                  }}
                  style={{ minHeight: "32px", fontSize: "12.5px", padding: "4px 8px", flex: 1 }}
                />
                <button
                  type="button"
                  className="secondary"
                  onClick={() => setPendingChiefQuery(pendingChiefFilter)}
                  style={{ minHeight: "32px", padding: "0 10px", fontSize: "12px" }}
                >
                  Buscar
                </button>
                {(pendingDateFilter || pendingChiefQuery) && (
                  <button
                    type="button"
                    className="secondary"
                    onClick={() => { setPendingDateFilter(""); setPendingChiefFilter(""); setPendingChiefQuery(""); }}
                    style={{ minHeight: "32px", padding: "0 10px", fontSize: "12px" }}
                  >
                    Limpar
                  </button>
                )}
              </div>
            </div>
            {filteredPendingAgendas.length === 0 ? (
              <p style={{ fontSize: "13px", color: "var(--text-soft)" }}>Nenhum relatório pendente para esta data.</p>
            ) : filteredPendingAgendas.map(agenda => (
              <button
                key={agenda.id}
                type="button"
                onClick={async () => {
                  setEditing(null);
                  setMessage("");
                  setProtocolSearch(serviceOrderLabel(agenda));
                  try {
                    const detailedAgenda = await selectAgendaForReport(agenda, { preserveCurrent: false });
                    await fillCoordinatesFromAgenda(detailedAgenda);
                  } catch (err) {
                    setMessage(err.message || "Não foi possível carregar os dados completos da OS.");
                  }
                }}
                style={{ textAlign: "left", padding: "12px", borderRadius: "8px", border: "1px solid var(--line)", background: "var(--surface-2)", cursor: "pointer", transition: "all 0.2s", display: "flex", flexDirection: "column", alignItems: "flex-start", gap: "4px", width: "100%", wordBreak: "break-word", flexShrink: 0 }}
              >
                <strong style={{ display: "block", fontSize: "13px", color: "var(--primary)", marginBottom: "0", lineHeight: "1.3" }}>{agendaReferenceLabel(agenda)} - {agenda.title}</strong>
                <span style={{ display: "block", fontSize: "11.5px", color: "var(--text-soft)", lineHeight: "1.3" }}>{formatDateBR(agenda.date)} · {agenda.location || agenda.institution_location || "Local não informado"}</span>
                {agenda.chief_name && <span style={{ display: "block", fontSize: "11px", color: "var(--text-soft)", marginTop: "2px", fontWeight: "600", lineHeight: "1.3" }}>Chefe: {agenda.chief_name}</span>}
              </button>
            ))}
          </div>
        )}

        {activeTab === "completed" && (
          <div className="report-list-content" style={{ padding: "12px" }}>
            <p style={{ fontSize: "13px", color: "var(--text-soft)" }}>Utilize a busca na área principal da tela para encontrar e visualizar relatórios concluídos.</p>
          </div>
        )}
      </aside>
      )}
    </section>

    {showPreviewModal && (() => {
      const chief = operationalResponsibility.chief;
      const agentsMatch = operationalResponsibility.agentsSummary;
      const supportsStr = operationalResponsibility.supportsSummary;
      const absences = Object.values(attendanceForm || {}).filter(d => d.is_absent === true);
      const actions = form.actions || [];
      const hasStaffChanges = !!(form.changes_staff && form.changes_staff.trim());
      const staffOffset = hasStaffChanges ? 1 : 0;
      let totalsEstimado = 0;
      let totalsAlcancado = 0;
      actions.forEach((a, index) => {
        if (index === 0) {
          totalsEstimado += Number(a.approach || 0);
        }
        const alcVal = getReachedAudienceForAction(a, index);
        const alcNum = Number(alcVal);
        totalsAlcancado += (alcVal !== "" && alcVal !== null && alcVal !== undefined && Number.isFinite(alcNum)) ? alcNum : 0;
      });
      // Style tokens
      const NAVY = "#0a1e44";
      const NAVY_LIGHT = "#143770";
      const GOLD = "#b4963c";
      const GRAY_100 = "#f2f3f5";
      const GRAY_600 = "#646464";

      const sectionStyle = (num, title) => (
        <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "6px", marginTop: "16px" }}>
          <span style={{ background: NAVY, color: "#fff", fontWeight: 700, fontSize: "10px", borderRadius: "4px", padding: "2px 7px", minWidth: "22px", textAlign: "center" }}>{String(num).padStart(2, "0")}</span>
          <span style={{ fontWeight: 700, fontSize: "12px", color: NAVY, letterSpacing: "0.5px" }}>{title}</span>
        </div>
      );

      const tableRow = (label, value, idx) => (
        <div key={label} style={{ display: "flex", fontSize: "11px", padding: "5px 8px", background: idx % 2 === 0 ? GRAY_100 : "#fff" }}>
          <span style={{ fontWeight: 700, color: NAVY_LIGHT, minWidth: "140px", flexShrink: 0 }}>{label}</span>
          <span style={{ color: "#1e1e1e" }}>{value || "—"}</span>
        </div>
      );

      const identData = [
        ["Protocolo", form.agenda ? `#${form.agenda}` : null],
        ["Ordem de Serviço", selectedAgendaForPreview?.service_order_number],
        ["Data da Operação", form.operation_date ? formatDateBR(form.operation_date) : null],
        ["Horário Programado", selectedAgendaForPreview ? `${selectedAgendaForPreview.start_time?.slice(0,5) || "--"} às ${selectedAgendaForPreview.end_time?.slice(0,5) || "--"}` : null],
        ["Natureza da Atividade", form.agenda_title],
        ["Instituição / Local", form.agenda_location],
        ["Endereço", selectedAgendaForPreview?.address],
        ["Município", selectedAgendaForPreview?.city || selectedAgendaForPreview?.municipality_ref_name],
      ].filter(r => r[1] && r[1] !== "-" && r[1] !== "null" && r[1] !== "undefined");

      const respData = [];
      if (form.team) respData.push(["Equipe Designada", form.team]);
      if (chief) respData.push(["Chefe Responsável", chief]);
      if (agentsMatch) respData.push(["Agentes de Educação", agentsMatch]);
      if (supportsStr) respData.push(["Apoios", supportsStr]);

      const recursos = [];
      if (form.cars) recursos.push(["Viaturas", form.cars.split(",").map(c => c.trim()).filter((v,i,a) => a.indexOf(v)===i).join(", ")]);


      return (
      <div className="modal-backdrop">
        <article className="modal" style={{ maxWidth: "760px", width: "min(760px, 95vw)", padding: 0, overflow: "hidden" }}>
          {/* Modal close button */}
          <button type="button" className="icon-button" onClick={() => setShowPreviewModal(false)} aria-label="Fechar resumo" style={{ position: "absolute", top: "8px", right: "8px", zIndex: 10, background: "rgba(255,255,255,0.15)", color: "#fff", borderRadius: "50%" }}>
            <X size={18} />
          </button>

          {/* Scrollable content */}
          <div style={{ maxHeight: "75vh", overflow: "auto" }}>
            {/* ── HEADER BANNER ── */}
            <div style={{ background: NAVY, padding: "14px 0", textAlign: "center" }}>
              <img src={logoUrl} alt="Logo" style={{ height: "36px", objectFit: "contain" }} />
            </div>
            <div style={{ height: "3px", background: GOLD }} />

            {/* ── TITLE ── */}
            <div style={{ textAlign: "center", padding: "12px 16px 4px" }}>
              <div style={{ fontWeight: 700, fontSize: "16px", color: GOLD, letterSpacing: "1px" }}>EDUCAÇÃO</div>
              <div style={{ fontWeight: 400, fontSize: "12px", color: "#1e1e1e", marginTop: "2px" }}>RELATÓRIO TÉCNICO DE ATIVIDADE</div>
            </div>

            {/* Double rule */}
            <div style={{ margin: "0 16px", borderTop: `2px solid ${NAVY}` }} />
            <div style={{ margin: "2px 16px 0", borderTop: `1px solid ${GOLD}` }} />

            {/* Meta line */}
            <div style={{ textAlign: "center", padding: "6px 16px 2px", fontSize: "10px", color: GRAY_600, letterSpacing: "0.3px" }}>
              {[
                form.agenda ? `Protocolo #${form.agenda}` : null,
                selectedAgendaForPreview?.service_order_number ? `OS ${selectedAgendaForPreview.service_order_number}` : null,
                `Data: ${form.operation_date ? formatDateBR(form.operation_date) : "--"}`,
              ].filter(Boolean).join("   |   ")}
            </div>

            <div style={{ padding: "0 16px 16px" }}>
              {/* SECTION 1 */}
              {sectionStyle(1, "IDENTIFICAÇÃO DA ATIVIDADE")}
              <div style={{ borderTop: `1.5px solid ${NAVY_LIGHT}`, marginBottom: "4px" }} />
              <div style={{ borderRadius: "6px", overflow: "hidden", border: "1px solid #e5e5e5" }}>
                {identData.map((r, i) => tableRow(r[0], r[1], i))}
              </div>

              {/* SECTION 2 */}
              {respData.length > 0 && (<>
                {sectionStyle(2, "RESPONSABILIDADE OPERACIONAL")}
                <div style={{ borderTop: `1.5px solid ${NAVY_LIGHT}`, marginBottom: "4px" }} />
                <div style={{ borderRadius: "6px", overflow: "hidden", border: "1px solid #e5e5e5" }}>
                  {respData.map((r, i) => tableRow(r[0], r[1], i))}
                </div>
              </>)}

              {/* ALTERAÇÕES DE EFETIVO */}
              {hasStaffChanges && (
                <>
                  {sectionStyle(respData.length > 0 ? 3 : 2, "ALTERAÇÕES DE EFETIVO")}
                  <div style={{ borderTop: `1.5px solid ${NAVY_LIGHT}`, marginBottom: "4px" }} />
                  <div style={{ fontSize: "10.5px", color: "#1e1e1e", lineHeight: "1.55", padding: "4px 8px", whiteSpace: "pre-wrap" }}>
                    {form.changes_staff}
                  </div>
                </>
              )}

              {/* SECTION 3 */}
              {sectionStyle((respData.length > 0 ? 3 : 2) + staffOffset, "FREQUÊNCIA DOS PARTICIPANTES")}
              <div style={{ borderTop: `1.5px solid ${NAVY_LIGHT}`, marginBottom: "4px" }} />
              {absences.length === 0 ? (
                <div style={{ fontSize: "11px", fontStyle: "italic", color: GRAY_600, padding: "4px 8px" }}>Nenhuma ausência registrada.</div>
              ) : (
                <div style={{ borderRadius: "6px", overflow: "hidden", border: "1px solid #e5e5e5" }}>
                  <div style={{ display: "flex", fontSize: "10px", fontWeight: 700, padding: "6px 8px", background: NAVY, color: "#fff" }}>
                    <span style={{ flex: 2 }}>Participante Ausente</span>
                    <span style={{ flex: 1 }}>Função</span>
                    <span style={{ flex: 2 }}>Justificativa</span>
                  </div>
                  {absences.map((a, i) => (
                    <div key={i} style={{ display: "flex", fontSize: "10px", padding: "5px 8px", background: i % 2 === 0 ? GRAY_100 : "#fff" }}>
                      <span style={{ flex: 2 }}>{a.member?.name || "Desconhecido"}</span>
                      <span style={{ flex: 1 }}>{a.member?.typeLabel || "N/I"}</span>
                      <span style={{ flex: 2 }}>{(a.reason || "").trim() || "Não informada"}</span>
                    </div>
                  ))}
                </div>
              )}

              {/* SECTION 4 — AÇÕES */}
              {actions.length > 0 && (<>
                {sectionStyle((respData.length > 0 ? 4 : 3) + staffOffset, "AÇÕES EXECUTADAS")}
                <div style={{ borderTop: `1.5px solid ${NAVY_LIGHT}`, marginBottom: "4px" }} />
                {actions.map((action, index) => {
                  const isFirstAction = index === 0;
                  const actionData = [
                    ["Tipo da Ação", action.type_action],
                    ["Instituição / Local", action.institution_name],
                    ["Endereço", action.place_action],
                    ["Horário", `${action.start_time || "--"} às ${action.final_hour || "--"}`],
                  ].filter(r => r[1] && r[1] !== "—" && r[1] !== "-- às --" && r[1] !== "0" && r[1] !== "-");
                  const kindLabel = requesterEntityKindLabel(action.requester_entity_kind);
                  const natureLabel = requesterEntityNatureLabel(action.requester_entity_nature);
                  const ageLabel = ageRangeLabel(action.age_range);
                  const agreementLabel = agreementIndicatorLabel(action.agreement_indicator);
                  if (kindLabel) actionData.push(["Tipo de solicitante", kindLabel]);
                  if (natureLabel) actionData.push(["Público ou Privado?", natureLabel]);
                  if (ageLabel) actionData.push(["Faixa etária", ageLabel]);
                  if (agreementLabel) actionData.push(["Indicador", agreementLabel]);

                  if (isFirstAction && showEstimatedPublic) {
                    if (action.approach !== undefined && action.approach !== null && action.approach !== "" && action.approach !== "0" && action.approach !== 0 && action.approach !== "-") {
                      actionData.push(["Público Estimado", action.approach]);
                    } else {
                      actionData.push(["Público Estimado", "Não informado"]);
                    }
                  }
                  const alcVal = getReachedAudienceForAction(action, index);
                  const alcDisplay = (alcVal !== "" && alcVal !== null && alcVal !== undefined) ? String(alcVal) : "Não informado";
                  actionData.push(["Público Alcançado", alcDisplay]);

                  // Parse materials
                  const materials = [];
                  if (action.distribution_materials_distributed) {
                    action.distribution_materials_distributed.split("\n").forEach(line => {
                      const parts = line.split("|");
                      if (parts.length >= 2) {
                        const name = parts[0].trim();
                        const qty = parseInt(parts[1].replace(/\D/g, ""), 10);
                        if (name && !isNaN(qty) && qty > 0) materials.push([name, qty]);
                      }
                    });
                  }

                  return (
                    <div key={index} style={{ marginBottom: "10px" }}>
                      <div style={{ background: NAVY_LIGHT, color: "#fff", fontWeight: 700, fontSize: "10px", padding: "5px 10px", borderRadius: "5px", letterSpacing: "0.5px" }}>
                        AÇÃO {String(index + 1).padStart(2, "0")} — {(action.type_action || "AÇÃO").toUpperCase()}
                      </div>
                      <div style={{ borderRadius: "0 0 6px 6px", overflow: "hidden", border: "1px solid #e5e5e5", borderTop: "none" }}>
                        {actionData.map((r, i) => tableRow(r[0], r[1], i))}
                      </div>
                      {materials.length > 0 && (
                        <div style={{ marginTop: "4px", borderRadius: "6px", overflow: "hidden", border: "1px solid #e5e5e5" }}>
                          <div style={{ display: "flex", fontSize: "10px", fontWeight: 700, padding: "5px 8px", background: GRAY_100, color: NAVY }}>
                            <span style={{ flex: 3 }}>Material Distribuído</span>
                            <span style={{ flex: 1, textAlign: "center" }}>Qtd.</span>
                          </div>
                          {materials.map((m, i) => (
                            <div key={i} style={{ display: "flex", fontSize: "10px", padding: "4px 8px", background: i % 2 === 0 ? "#fafafe" : "#fff" }}>
                              <span style={{ flex: 3 }}>{m[0]}</span>
                              <span style={{ flex: 1, textAlign: "center", fontWeight: 600 }}>{m[1]}</span>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  );
                })}
              </>)}

              {/* SECTION 5 — PÚBLICO E RESULTADOS */}
              {sectionStyle((respData.length > 0 ? (actions.length > 0 ? 5 : 4) : (actions.length > 0 ? 4 : 3)) + staffOffset, "PÚBLICO E RESULTADOS CONSOLIDADOS")}
              <div style={{ borderTop: `1.5px solid ${NAVY_LIGHT}`, marginBottom: "4px" }} />
              <div style={{ borderRadius: "6px", overflow: "hidden", border: "1px solid #e5e5e5" }}>
                <div style={{ display: "flex", fontSize: "10px", fontWeight: 700, padding: "6px 8px", background: NAVY, color: "#fff" }}>
                  <span style={{ flex: 3 }}>Indicador</span>
                  <span style={{ flex: 1, textAlign: "center" }}>Valor</span>
                </div>
                {[
                  ...(showEstimatedPublic ? [["Público Estimado (total)", totalsEstimado]] : []),
                  ["Público Alcançado (total)", totalsAlcancado],
                  ["Ações Realizadas", actions.length],
                ].map((r, i) => (
                  <div key={i} style={{ display: "flex", fontSize: "11px", padding: "5px 8px", background: i % 2 === 0 ? GRAY_100 : "#fff" }}>
                    <span style={{ flex: 3, color: "#1e1e1e" }}>{r[0]}</span>
                    <span style={{ flex: 1, textAlign: "center", fontWeight: 700, color: NAVY }}>{r[1]}</span>
                  </div>
                ))}
              </div>

              {/* SECTION 6 — RECURSOS */}
              {recursos.length > 0 && (<>
                {sectionStyle((respData.length > 0 ? (actions.length > 0 ? 6 : 5) : (actions.length > 0 ? 5 : 4)) + staffOffset, "RECURSOS OPERACIONAIS")}
                <div style={{ borderTop: `1.5px solid ${NAVY_LIGHT}`, marginBottom: "4px" }} />
                <div style={{ borderRadius: "6px", overflow: "hidden", border: "1px solid #e5e5e5" }}>
                  {recursos.map((r, i) => tableRow(r[0], r[1], i))}
                </div>
              </>)}

              {/* SECTION 7 — OCORRÊNCIAS */}
              {(() => {
                const secNum = (respData.length > 0 ? 3 : 2) + (actions.length > 0 ? 1 : 0) + 1 + (recursos.length > 0 ? 1 : 0) + 1 + staffOffset;
                return (<>
                  {sectionStyle(secNum, "REGISTRO DE OCORRÊNCIAS")}
                  <div style={{ borderTop: `1.5px solid ${NAVY_LIGHT}`, marginBottom: "4px" }} />
                  {form.has_exceptional_occurrence ? (
                    <div style={{ borderRadius: "6px", overflow: "hidden", border: "1px solid #e5e5e5" }}>
                      {[
                        ["Tipo da Ocorrência", form.exceptional_occurrence_type === "VEHICLE_BREAKDOWN" ? "Viatura" : form.exceptional_occurrence_type === "WORK_ACCIDENT" ? "Efetivo" : form.exceptional_occurrence_type],
                        ["Descrição", form.exceptional_occurrence_description],
                        ["Providências Adotadas", form.exceptional_occurrence_actions_taken],
                        ["Impacto na Atividade", form.exceptional_occurrence_impact],
                      ].map((r, i) => tableRow(r[0], r[1], i))}
                    </div>
                  ) : (
                    <div style={{ fontSize: "11px", fontStyle: "italic", color: GRAY_600, padding: "4px 8px" }}>Nenhuma ocorrência envolvendo viatura ou efetivo registrada.</div>
                  )}
                </>);
              })()}

              {/* SECTION — RELATO OPERACIONAL DO CHEFE */}
              {form.general_observations ? (() => {
                const relatoSecNum = (respData.length > 0 ? 3 : 2) + (actions.length > 0 ? 1 : 0) + 1 + (recursos.length > 0 ? 1 : 0) + 2 + staffOffset;
                return (<>
                  {sectionStyle(relatoSecNum, "RELATO OPERACIONAL DO CHEFE")}
                  <div style={{ borderTop: `1.5px solid ${NAVY_LIGHT}`, marginBottom: "4px" }} />
                  <div style={{ fontSize: "10.5px", color: "#1e1e1e", lineHeight: "1.55", padding: "4px 8px", whiteSpace: "pre-wrap" }}>
                    {form.general_observations}
                  </div>
                </>);
              })() : null}

              {/* SECTION — CONCLUSÃO */}
              {(() => {
                const secNum = (respData.length > 0 ? 3 : 2) + (actions.length > 0 ? 1 : 0) + 1 + (recursos.length > 0 ? 1 : 0) + 2 + (form.general_observations ? 1 : 0) + staffOffset;
                return (<>
                  {sectionStyle(secNum, "CONCLUSÃO INSTITUCIONAL")}
                  <div style={{ borderTop: `1.5px solid ${NAVY_LIGHT}`, marginBottom: "4px" }} />
                  <div style={{ fontSize: "10.5px", color: "#1e1e1e", lineHeight: "1.55", padding: "4px 8px" }}>
                    O presente documento consolida as informações registradas no Sistema Integrado da Educação – SIED referentes à atividade identificada, incluindo execução operacional, frequência dos participantes, ações realizadas, {showEstimatedPublic ? "público estimado, " : ""}público alcançado, materiais distribuídos e eventuais ocorrências. Este relatório possui caráter técnico-institucional e integra o acervo documental do programa Lei Seca Educação.
                  </div>
                </>);
              })()}

              {/* Final rules */}
              <div style={{ marginTop: "12px", borderTop: `2px solid ${NAVY}` }} />
              <div style={{ marginTop: "2px", borderTop: `1px solid ${GOLD}` }} />

              {/* Footer */}
              <div style={{ textAlign: "center", padding: "8px 0 2px", fontSize: "8px", color: GRAY_600 }}>
                SIED — Sistema Integrado da Educação  |  Uso institucional — Lei Seca Educação
              </div>
            </div>
          </div>

          {/* Modal actions */}
          <div className="modal-actions" style={{ borderTop: "1px solid #e5e5e5", padding: "12px 16px" }}>
            <button
              className="secondary"
              type="button"
              onClick={handleShareReport}
              disabled={!hasShareableReport}
              title="Compartilhar resumo do relatório"
            >
              <Share2 size={14} /> Compartilhar relatório
            </button>
            {isVisitor ? (
              <>
                <button type="button" onClick={() => setShowPreviewModal(false)}>Fechar</button>
                <button
                  className="primary"
                  type="button"
                  onClick={() =>
                    generateTechnicalReportPdf(form, selectedAgendaForPreview, attendanceForm, true, showEstimatedPublic)
                  }
                >
                  Visualizar PDF
                </button>
              </>
            ) : (
              <>
                <button
                  className="primary"
                  type="button"
                  onClick={() =>
                    generateTechnicalReportPdf(form, selectedAgendaForPreview, attendanceForm, false, showEstimatedPublic)
                  }
                >
                  Baixar PDF técnico
                </button>
                <button className="secondary" type="button" onClick={copyPreview}>
                  <Clipboard size={14} /> Copiar
                </button>
                <button type="button" onClick={() => setShowPreviewModal(false)}>Voltar ao preenchimento</button>
              </>
            )}
          </div>
        </article>
      </div>
      );
    })()}
    </>
  );
}
