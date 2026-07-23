import { Clipboard, MapPin, Plus, Save, Search, Trash2, Eye, X, Check, Edit3 } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { api } from "../api/client.js";
import { STREET_ACTION_ID } from "../utils/constants.js";
import { useAuth } from "../context/AuthContext.jsx";
import { STREET_ACTION_TYPE_OPTIONS } from "../utils/streetActionTypes.js";
import { formatDateBR } from "../utils/date.js";

import { buildPreview, chiefFromReport, reportName } from "../utils/reportPreview.js";
import { getValidatableActions } from "./technicalReportsActionHelpers.js";

function memberRows(members = {}) {
  return [
    ...(members.chiefs || []).map((item) => ({ ...item, type: "CHIEF", typeLabel: "Chefe" })),
    ...(members.agents || []).map((item) => ({ ...item, type: "AGENT", typeLabel: "Agente" })),
    ...(members.supports || []).map((item) => ({ ...item, type: "SUPPORT", typeLabel: "Apoio" })),
  ];
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
  breathalyzers: "",
  cars: "",
  changes_general: "",
  contact_received: "",
  occurrence_observation: "",
  lat: "",
  lng: "",

  status: "DRAFT",
  general_observations: "",
  actions: [{ ...emptyAction }],
};

const numberFields = [
  "approach",
  "approached_actions",
];

const fieldLabels = {
  approach: "Público alcançado (Ação/Palestra)",
  approached_actions: "Número de abordagens",
};

const streetActionTypeOptions = STREET_ACTION_TYPE_OPTIONS;

function isStreetActionAgenda(agenda) {
  return String(agenda?.requester_entity_type || "").toLowerCase().includes("rua");
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
  return {
    agents: joinValues([
      chiefFromAgenda(agenda) ? `Chefe responsável: ${chiefFromAgenda(agenda)}` : "",
      agenda.team_phone ? `Telefone do chefe/equipe: ${agenda.team_phone}` : "",
      agenda.agents ? `Agentes: ${agenda.agents}` : "",
      agenda.support_1 ? `Apoio 1: ${agenda.support_1}` : "",
      agenda.support_2 ? `Apoio 2: ${agenda.support_2}` : "",
    ]),
    resources: joinValues([
      agenda.vehicle ? `Viatura: ${agenda.vehicle}` : "",
      agenda.vehicle_name ? `Viatura cadastrada: ${agenda.vehicle_name}` : "",
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
      agenda.requester_entity_type ? `Tipo de entidade: ${agenda.requester_entity_type}` : "",
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

function hydrateForm(report, agenda) {
  const hasAnySourceId = report.actions?.some((a) => a.source_id) ?? false;
  return {
    ...report,
    approximate_public: numericApproximatePublic(report?.approximate_public),
    request_details: buildRequestDetails(report, agenda),
    actions: report.actions?.length
      ? report.actions.map((action, idx) => ({
          ...action,
          __userCreated: hasAnySourceId ? !action.source_id : idx > 0,
        }))
      : [{ ...emptyAction, agenda: report.agenda, source_id: agenda ? `agenda_action:${agenda.id}` : "", __userCreated: false }],
  };
}

function buildActionPayload(action, formAgenda) {
  return {
    ...action,
    agenda: nullable(action.agenda || formAgenda),
    source_id: nullable(action.source_id),
    ...Object.fromEntries(numberFields.map((field) => [field, Number(action[field] || 0)])),
  };
}

function normalizePayload(form) {
  const { request_details, ...payloadForm } = form;
  return {
    ...payloadForm,
    source: "LOCAL",
    source_id: nullable(form.source_id),
    agenda: nullable(form.agenda),
    management_id: nullable(form.management_id),
    approximate_public: nullable(form.approximate_public),
    lat: nullable(form.lat),
    lng: nullable(form.lng),
    general_observations: form.general_observations || "",
    actions: getValidatableActions(form.actions).map(({ action }) => buildActionPayload(action, form.agenda)),
  };
}

export default function TechnicalReportsPage() {
  const [agendas, setAgendas] = useState([]);
  const [reports, setReports] = useState([]);
  const [techFilters, setTechFilters] = useState({ protocol: "", team: "", date: "" });
  const [pendingTechFilters, setPendingTechFilters] = useState({ protocol: "", team: "", date: "" });
  const [pendingDateFilter, setPendingDateFilter] = useState("");
  const [pendingChiefFilter, setPendingChiefFilter] = useState("");
  const [pendingChiefQuery, setPendingChiefQuery] = useState("");
  const [reportsPreviewModal, setReportsPreviewModal] = useState(null);
  const [activeTab, setActiveTab] = useState("pending");
  const [protocolSearch, setProtocolSearch] = useState("");
  const [form, setForm] = useState(empty);
  const [editing, setEditing] = useState(null);
  const [isEditingLoading, setIsEditingLoading] = useState(false);
  const [message, setMessage] = useState("");
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
  const { user } = useAuth();
  const isAdmin = user?.role === "ADMIN" || user?.role === "MANAGER";
  const requestFieldsReadOnly = Boolean(form.agenda);

  const selectedAgenda = useMemo(
    () => agendas.find((agenda) => String(agenda.id) === String(form.agenda)),
    [agendas, form.agenda]
  );
  const isStreetActionSelectedAgenda = Boolean(selectedAgenda && (selectedAgenda.action_type_ref === STREET_ACTION_ID || selectedAgenda.requester_entity_type === STREET_ACTION_ID));
  const predefinedStreetActionTypes = useMemo(
    () => [...new Set((form.street_action_details || []).map((detail) => String(detail?.type || "").trim()).filter(Boolean))],
    [form.street_action_details]
  );
  const isStreetAction = Boolean(isStreetActionSelectedAgenda || predefinedStreetActionTypes.length > 0);
  const shouldChooseStreetActionType = isStreetActionSelectedAgenda && predefinedStreetActionTypes.length > 1;
  const normalizeTypeLabel = (value) => String(value || "").trim().toLocaleLowerCase("pt-BR");
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
  const preview = useMemo(() => buildPreview(form), [form]);

  const completedAgendaIds = useMemo(() => new Set(reports.map(r => String(r.agenda))), [reports]);
  const pendingAgendas = useMemo(() => agendas.filter(a => !completedAgendaIds.has(String(a.id))), [agendas, completedAgendaIds]);

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

    const [agendasResult, reportsResult] = await Promise.allSettled([
      api(`/agendas/?page_size=50&reportable=true&pending_report=true${pendingChiefQuery ? `&chief=${encodeURIComponent(pendingChiefQuery)}` : ''}`),
      api(`/education-reports/?${params.toString()}`),
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

    const failures = [agendasResult, reportsResult]
      .filter((result) => result.status === "rejected")
      .map((result) => result.reason?.message)
      .filter(Boolean);
    if (failures.length) {
      setLoadError(failures.join(" "));
    }
  };
  useEffect(() => { load(); }, [techFilters, pendingChiefQuery]);

  const buildAttendanceForm = (detailSchedule) => {
    const formObj = {};
    const staffChanges = [];
    memberRows(detailSchedule.members).forEach((member) => {
      if (member.is_extra) staffChanges.push(`Extra: ${member.name}`);
      if (member.is_swap) staffChanges.push(`Troca: ${member.name} (no lugar de ${member.swap_for})`);

      const memberKey = `${member.type}_${member.id}`;
      const isChecked = detailSchedule.checked_members && detailSchedule.checked_members[memberKey] !== undefined;
      formObj[memberKey] = {
        is_absent: isChecked ? !!member.is_absent : null,
        reason: member.absence_reason || "",
        attachment: null,
        member,
      };
    });
    return { formObj, staffChanges };
  };

  const loadScheduleAttendance = async (scheduleId) => {
    const detailSchedule = await api(`/shift-schedules/${scheduleId}/`);
    setReportSchedule(detailSchedule);
    const { formObj, staffChanges } = buildAttendanceForm(detailSchedule);
    setAttendanceForm(formObj);
    if (staffChanges.length > 0) {
      setForm((current) => ({
        ...current,
        changes_staff: staffChanges.join("\n"),
      }));
    }
    return detailSchedule;
  };

  useEffect(() => {
    if (form.operation_date && form.team) {
      api(`/shift-schedules/?date=${form.operation_date}`).then(res => {
        const schedules = res.results || res;
        const scheduleInfo = schedules.find(s =>
          String(s.team) === String(form.team) ||
          String(s.team_name) === String(form.team) ||
          (selectedAgenda && String(s.team) === String(selectedAgenda.team_ref)) ||
          (selectedAgenda && String(s.team_name) === String(selectedAgenda.sector_name))
        );
        if (scheduleInfo) {
          loadScheduleAttendance(scheduleInfo.id).catch(() => {
            setReportSchedule(null);
            setAttendanceForm({});
          });
        } else {
           setReportSchedule(null);
           setAttendanceForm({});
        }
      }).catch(() => {
        setReportSchedule(null);
        setAttendanceForm({});
      });
    } else {
      setReportSchedule(null);
      setAttendanceForm({});
    }
  }, [form.operation_date, form.team, selectedAgenda]);

  const update = (field, value) => setForm((current) => ({ ...current, [field]: value }));

  const applyAgenda = (agenda) => {
    const details = protocolDetails(agenda);
    const selectedMaterials = extractMaterialCategories(agenda);
    const initialEquipment = serializeMaterialRows([...selectedMaterials.dynamics, ...selectedMaterials.supports]);
    const initialKits = serializeMaterialRows(selectedMaterials.kits);
    const blankKits = serializeBlankMaterialRows(selectedMaterials.kits);
    const buildAgendaAction = (currentAction = {}) => {
      const isUserCreated = currentAction.__userCreated;
      return {
        ...emptyAction,
        ...currentAction,
        agenda: agenda.id,
        source_id: isUserCreated ? "" : (currentAction.source_id || `agenda_action:${agenda.id}`),
        place_action: currentAction.place_action || ((agenda.action_type_ref === STREET_ACTION_ID || agenda.requester_entity_type === STREET_ACTION_ID) ? "" : (agenda.institution_location || agenda.location || "")),
        institution_name: currentAction.institution_name || agenda.institution_location || "",
        type_action: currentAction.type_action || agenda.action_type || agenda.action_type_ref_name || "",
        type_audience: currentAction.type_audience || agenda.audience || "",
        start_time: currentAction.start_time || agenda.start_time?.slice(0, 5) || "",
        final_hour: currentAction.final_hour || agenda.end_time?.slice(0, 5) || "",
        approach: currentAction.approach || agenda.quantity || 0,
        approached_actions: currentAction.approached_actions || agenda.quantity || 0,
        equipment_materials_removed: currentAction.equipment_materials_removed || initialEquipment,
        equipment_materials_distributed: currentAction.equipment_materials_distributed || initialEquipment,
        distribution_materials_removed: currentAction.distribution_materials_removed || initialKits,
        distribution_materials_distributed: currentAction.distribution_materials_distributed || blankKits,
      };
    };
    setForm((current) => ({
      ...current,
      agenda: agenda.id,
      agenda_title: agenda.title,
      agenda_date: agenda.date,
      agenda_location: agenda.institution_location || agenda.location,
      operation_date: agenda.date || current.operation_date,
      team: agenda.team_name || agenda.team_ref_name || agenda.sector_name || current.team,
      education_agents: current.education_agents || details.agents,
      changes_staff: current.changes_staff || "",
      approximate_public: current.approximate_public || numericApproximatePublic(agenda.quantity),
      request_details: current.request_details || details.audience,
      street_action_details: current.street_action_details?.length ? current.street_action_details : (agenda.street_action_details || []),
      materials_removed: current.materials_removed || materialsFromAgenda(agenda),
      breathalyzers: current.breathalyzers || details.resources,
      cars: current.cars || joinValues([agenda.vehicle, agenda.vehicle_name]),
      contact_received: current.contact_received || joinContactValues([
        agenda.external_responsible,
        agenda.external_responsible_phone,
        agenda.external_email,
      ], current.contact_received),
      occurrence_observation: current.occurrence_observation || agenda.notes || agenda.description || "",
      actions: (() => {
        const meaningfulCurrentActions = getValidatableActions(current.actions).map(({ action }) => action);
        if (agenda.action_type_ref === STREET_ACTION_ID || agenda.requester_entity_type === STREET_ACTION_ID) {
          return meaningfulCurrentActions.length
            ? meaningfulCurrentActions.map((action) => buildAgendaAction(action))
            : [buildAgendaAction({ place_action: "" })];
        }
        return current.actions.map((action) => buildAgendaAction(action));
      })(),
    }));

    // O carregamento da escala agora é feito pelo useEffect monitorando operation_date e team
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
      applyAgenda(agenda);
      const foundLocation = await fillCoordinatesFromAgenda(agenda);
      setMessage(foundLocation ? `${agendaReferenceLabel(agenda)} vinculada ao relatorio com localizacao preenchida.` : `${agendaReferenceLabel(agenda)} vinculada ao relatorio.`);
    } catch (err) {
      setMessage(err.message);
    }
  };

  const updateAction = (index, field, value) => {
    setForm((current) => ({
      ...current,
      actions: current.actions.map((action, actionIndex) => (
        actionIndex === index ? { ...action, [field]: value } : action
      )),
    }));
  };

  const updateAllActionsField = (field, value) => {
    setForm((current) => ({
      ...current,
      actions: current.actions.map((action) => ({ ...action, [field]: value })),
    }));
  };

  const addAction = () => {
    setForm((current) => {
      const baseAction = current.actions[0] || emptyAction;
      return {
        ...current,
        actions: [...current.actions, {
          ...emptyAction,
          agenda: current.agenda,
          __userCreated: true,
          approach: baseAction.approach || "",
          approached_actions: baseAction.approached_actions || "",
          equipment_materials_removed: baseAction.equipment_materials_removed || "",
          equipment_materials_distributed: baseAction.equipment_materials_distributed || "",
          distribution_materials_removed: baseAction.distribution_materials_removed || "",
          distribution_materials_distributed: baseAction.distribution_materials_distributed || "",
        }],
      };
    });
  };

  const removeAction = (index) => {
    setForm((current) => ({
      ...current,
      actions: current.actions.length === 1
        ? [{ ...emptyAction, agenda: current.agenda }]
        : current.actions.filter((_, actionIndex) => actionIndex !== index),
    }));
  };

  const saveAttendance = async ({ closeModal = true, markReported = false, successMessage = "Frequência salva com sucesso." } = {}) => {
    if (!reportSchedule || Object.keys(attendanceForm).length === 0) return;
    if (isSavingAttendance) return;
    if (Object.values(attendanceForm).some((data) => data.is_absent === null)) {
      throw new Error("Selecione a frequência de todos os integrantes antes de confirmar.");
    }

    setIsSavingAttendance(true);
    try {
      const promises = Object.entries(attendanceForm).map(([key, data]) => {
        const [memberType, memberId] = key.split("_");
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
      });
      await Promise.all(promises);

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
      if (closeModal) setIsAttendanceModalOpen(false);
      if (successMessage) setMessage(successMessage);
    } finally {
      setIsSavingAttendance(false);
    }
  };

  const saveReport = async (status) => {
    try {
      if (reportSchedule && Object.keys(attendanceForm).length > 0) {
        await saveAttendance({
          closeModal: false,
          markReported: status === "SUBMITTED",
          successMessage: status === "SUBMITTED" ? "Frequência salva com sucesso." : "",
        });
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
      const savedAgenda = agendas.find((agenda) => String(agenda.id) === String(saved.agenda));
      setForm(hydrateForm(saved, savedAgenda));
      setProtocolSearch(savedAgenda?.service_order_number ? serviceOrderLabel(savedAgenda) : saved.agenda ? String(saved.agenda) : "");
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
    const missingFields = [];

    if (!form.operation_date) missingFields.push({ name: "Data da Operação", id: "input-operation-date" });
    if (!form.team) missingFields.push({ name: "Equipe Executora", id: "input-team" });

    getValidatableActions(form.actions).forEach(({ action, index }) => {
      if (!action.type_action) missingFields.push({ name: `Ação ${index + 1}: Ação Definida pelo Chefe`, id: `select-type-action-${index}` });
    });

    if (!form.accessibility_conditions_met) missingFields.push({ name: "Condições de Acessibilidade", id: "select-accessibility" });

    if (reportSchedule && Object.values(attendanceForm).some((d) => d.is_absent === null)) {
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
    setIsSaving(true);
    try {
      const savedId = await saveReport("DRAFT");
      await api(`/education-reports/${savedId}/submit-for-review/`, { method: "POST" });
      setMessage("Relatório enviado para conferência com sucesso.");
      load();
    } catch (err) {
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
      if (!action.type_action) missingFields.push({ name: `Ação ${index + 1}: Ação Definida pelo Chefe`, id: `select-type-action-${index}` });
    });

    if (!form.accessibility_conditions_met) missingFields.push({ name: "Condições de Acessibilidade", id: "select-accessibility" });

    if (reportSchedule && Object.values(attendanceForm).some((d) => d.is_absent === null)) {
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
      setMessage("Relatório retificado com sucesso.");
      load();
    } catch (err) {
      setMessage(`⚠️ Não foi possível retificar o relatório\n\nMotivo:\n${err.message}`);
    } finally {
      setIsSaving(false);
    }
  };

  const edit = async (report) => {
    if (isEditingLoading) return;
    setIsEditingLoading(true);
    try {
      const reportAgendaLocal = agendas.find((agenda) => String(agenda.id) === String(report.agenda));
      let reportAgenda = reportAgendaLocal;

      const needsFetch = report.agenda && !reportAgendaLocal && (
        !report.street_action_details?.length ||
        !report.request_details
      );

      if (needsFetch) {
        try {
          reportAgenda = await api(`/agendas/${report.agenda}/`);
        } catch (err) {
          setMessage(`⚠ Não foi possível carregar os dados da agenda vinculada (Protocolo #${report.agenda}). O formulário não pôde ser aberto.`);
          setIsEditingLoading(false);
          return;
        }
      }

      setEditing(report.id);
      setProtocolSearch(reportAgenda?.service_order_number ? serviceOrderLabel(reportAgenda) : report.agenda ? String(report.agenda) : "");

      const resolvedDetails = report.street_action_details?.length
        ? report.street_action_details
        : (reportAgenda?.street_action_details || []);

      const hydrated = hydrateForm({
        ...report,
        street_action_details: resolvedDetails
      }, reportAgenda);

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

  return (
    <>
    <section className="page two-column report-editor">
      {activeTab !== "completed" && (
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
          <h2>{reportName(form)}</h2>

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
                <input value={selectedAgenda ? chiefFromAgenda(selectedAgenda) || chiefFromReport(form) : chiefFromReport(form)} readOnly />
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
                        <strong>{detail.type || `Ação ${idx + 1}`}</strong>
                        <small>{detail.public ? `Público estimado: ${detail.public}` : "Público estimado não informado"}</small>
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
                {numberFields.map((field) => (
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
                ))}
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
                      <div className="action-card-header">
                        <strong>{`Ação ${index + 1}`}</strong>
                        <button type="button" className="secondary icon-button" onClick={() => removeAction(index)} aria-label="Remover ação">
                          <Trash2 size={16} />
                        </button>
                      </div>
                      <div className="compact-grid chief-action-grid">
                        <label className={`field-label ${requestFieldsReadOnly && !action.__userCreated ? "" : "chief-highlight-field"}`.trim()}>
                          <span>Local da ação</span>
                          <input value={action.place_action || ""} onChange={(event) => updateAction(index, "place_action", event.target.value)} readOnly={requestFieldsReadOnly && !action.__userCreated} />
                        </label>
                        <label className={`field-label ${requestFieldsReadOnly && !action.__userCreated ? "" : "chief-highlight-field"}`.trim()}>
                          <span>Horário inicial</span>
                          <input value={action.start_time || ""} onChange={(event) => updateAction(index, "start_time", event.target.value)} readOnly={requestFieldsReadOnly && !action.__userCreated} />
                        </label>
                        <label className={`field-label ${requestFieldsReadOnly && !action.__userCreated ? "" : "chief-highlight-field"}`.trim()}>
                          <span>Horário final</span>
                          <input value={action.final_hour || ""} onChange={(event) => updateAction(index, "final_hour", event.target.value)} readOnly={requestFieldsReadOnly && !action.__userCreated} />
                        </label>
                        {isStreetAction ? (
                          <label className={`field-label chief-action-select ${shouldHighlightChiefTypeAction(action, index) ? "chief-highlight-field" : ""}`.trim()}>
                            <span>Ação Definida pelo Chefe</span>
                            <select
                              id={`select-type-action-${index}`}
                              value={action.type_action || ""}
                              onChange={(event) => updateAction(index, "type_action", event.target.value)}
                              disabled={requestFieldsReadOnly && !action.__userCreated}
                              required
                            >
                              <option value="">Selecione</option>
                              {streetActionTypeOptions.map((option) => (
                                <option key={option} value={option}>{option}</option>
                              ))}
                              {action.type_action && !streetActionTypeOptions.includes(action.type_action) && (
                                <option value={action.type_action}>{action.type_action}</option>
                              )}
                            </select>
                          </label>
                        ) : null}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {(() => {
                const safeAgenda = selectedAgenda || {};
                const cats = extractMaterialCategories(safeAgenda);
                const baseAction = form.actions[0] || emptyAction;
                const removedValue = baseAction.distribution_materials_removed || serializeMaterialRows(cats.kits);
                const distributedValue = baseAction.distribution_materials_distributed || serializeBlankMaterialRows(cats.kits);

                if (!cats.kits.length) return null;

                return (
                  <div className="chief-flow-group">
                    <div className="chief-flow-header chief-flow-header-inline">
                      <div>
                        <h5>Materiais para Distribuição</h5>
                        <p>Os itens retirados seguem a Ordem de Serviço. Informe apenas o que foi realmente distribuído.</p>
                      </div>
                    </div>
                    <div className="report-material-grid chief-material-grid">
                      <div className="field-label report-text-box">
                        <span>Material para Distribuição retirado</span>
                        <MaterialSummary value={removedValue} />
                      </div>
                      <div className="field-label report-text-box chief-highlight-field">
                        <span>Material distribuído</span>
                        <MaterialQuantityEditor value={distributedValue} onChange={(value) => updateAllActionsField("distribution_materials_distributed", value)} />
                      </div>
                    </div>
                  </div>
                );
              })()}
            </div>
          </div>

          {reportSchedule && (
            <div className="form-section attendance-highlight-section">
              <h3>Frequência da Equipe</h3>
              <p style={{ fontSize: "0.85rem", color: "var(--text-soft)", marginBottom: "12px" }}>
                Gerencie as presenças e faltas do efetivo lançado na escala para este evento.
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
            <textarea className="chief-highlight-input" placeholder="Dados e Observações" value={form.general_observations || ""} onChange={(event) => update("general_observations", event.target.value)} />
            <textarea className="chief-highlight-input" placeholder="Observação de ocorrência" value={form.occurrence_observation || ""} onChange={(event) => update("occurrence_observation", event.target.value)} />
          </div>

          {message && <div className="alert" style={{ whiteSpace: "pre-wrap" }}>{message}</div>}
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
                Gerenciar Frequência - {reportSchedule?.team}
              </h2>
              <button className="icon-btn" type="button" onClick={() => setIsAttendanceModalOpen(false)}>
                <X size={20} />
              </button>
            </header>
            <div className="modal-body attendance-modal-body">
              {reportSchedule && (
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
                <span>Protocolo</span>
                <input placeholder="Ex: 123" value={pendingTechFilters.protocol} onChange={(e) => setPendingTechFilters({ ...pendingTechFilters, protocol: e.target.value })} />
              </div>
              <div className="filter-field">
                <span>Equipe</span>
                <input placeholder="Ex: E1" value={pendingTechFilters.team} onChange={(e) => setPendingTechFilters({ ...pendingTechFilters, team: e.target.value })} />
              </div>
              <div className="filter-field">
                <span>Data</span>
                <input type="date" value={pendingTechFilters.date} onChange={(e) => setPendingTechFilters({ ...pendingTechFilters, date: e.target.value })} />
              </div>
              <div style={{ alignSelf: 'flex-end' }}>
                <button onClick={() => setTechFilters(pendingTechFilters)}>Pesquisar</button>
              </div>
            </div>

            <div className="premium-table-wrap">
              <h2>Relatórios Técnicos Registrados</h2>
              <table>
                <thead>
                  <tr>
                    <th>Protocolo</th>
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
                      <td><strong>{r.agenda ? `#${r.agenda}` : "-"}</strong></td>
                      <td>{reportName(r)}</td>
                      <td>{formatDateBR(r.operation_date)}</td>
                      <td>
                        <span style={{
                          background: r.status === "APPROVED" ? "var(--success)" :
                                      r.status === "PENDING_REVIEW" ? "var(--info)" :
                                      r.status === "RETURNED" ? "var(--danger)" : "var(--warning)",
                          color: "#fff", padding: "4px 8px", borderRadius: 4, fontSize: 11, fontWeight: "bold"
                        }}>
                          {r.status === "APPROVED" ? "APROVADO" :
                           r.status === "PENDING_REVIEW" ? "AGUARDANDO" :
                           r.status === "RETURNED" ? "DEVOLVIDO" : "RASCUNHO"}
                        </span>
                      </td>
                      <td>{r.actions_count || r.actions?.length || 0} ações</td>
                      <td style={{ display: "flex", gap: "4px", flexWrap: "wrap" }}>
                        <button className="secondary icon-button" onClick={() => { setReportsPreviewModal(r); }} title="Visualizar">
                          <Eye size={16} />
                        </button>
                        <button className="secondary icon-button" onClick={() => edit(r)} title="Editar" disabled={isEditingLoading}>
                          <Clipboard size={16} />
                        </button>
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
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {reportsPreviewModal && (
            <div className="modal-overlay" onClick={() => setReportsPreviewModal(null)}>
              <div className="premium-modal" onClick={e => e.stopPropagation()}>
                <div className="modal-header-premium">
                  <h2>Detalhes do Relatório</h2>
                  <button className="secondary icon-button" onClick={() => setReportsPreviewModal(null)}><X size={20} /></button>
                </div>
                <div className="modal-body-premium">
                  <pre>{buildPreview(reportsPreviewModal)}</pre>
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
      <aside className="side-panel report-sidebar">
        <div className="sidebar-tabs" style={{ display: "flex", gap: "8px", marginBottom: "16px", borderBottom: "1px solid var(--line)", paddingBottom: "12px" }}>
          <button type="button" className={activeTab === "pending" ? "active" : "secondary"} onClick={() => setActiveTab("pending")} style={{ flex: 1, fontSize: "12px", padding: "6px 4px", fontWeight: "700" }}>Pendentes ({pendingAgendas.length})</button>
          <button type="button" className={activeTab === "completed" ? "active" : "secondary"} onClick={() => setActiveTab("completed")} style={{ flex: 1, fontSize: "12px", padding: "6px 4px", fontWeight: "700" }}>Feitos ({reports.length})</button>
          <button type="button" className={activeTab === "preview" ? "active" : "secondary"} onClick={() => setActiveTab("preview")} style={{ flex: 1, fontSize: "12px", padding: "6px 4px", fontWeight: "700" }}>Resumo</button>
        </div>

        {activeTab === "preview" && (
          <div className="report-preview-content">
            <div className="modal-header" style={{ marginBottom: "12px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <h2 style={{ fontSize: "15px", margin: 0 }}>Resumo do Relatório</h2>
              <button className="secondary" type="button" onClick={copyPreview} style={{ padding: "4px 8px", fontSize: "12px" }}>
                <Clipboard size={14} /> Copiar
              </button>
            </div>
            <pre style={{ fontSize: "11px", padding: "12px", background: "var(--surface)", border: "1px solid var(--line)", borderRadius: "8px", whiteSpace: "pre-wrap" }}>{preview}</pre>
            {!isAdmin && <small style={{ display: "block", marginTop: "12px", color: "var(--text-soft)" }}>Chefes visualizam os relatórios criados por eles; administradores visualizam todos.</small>}
          </div>
        )}

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
                onClick={() => {
                  setProtocolSearch(serviceOrderLabel(agenda));
                  applyAgenda(agenda);
                  fillCoordinatesFromAgenda(agenda);
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
    </section>
    </>
  );
}

