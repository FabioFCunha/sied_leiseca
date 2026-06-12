import { CheckCircle2, ClipboardCheck, Copy, ExternalLink, History, Plus, Save, Trash2, XCircle } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { api } from "../api/client.js";
import Filters from "../components/Filters.jsx";
import { useAuth } from "../context/AuthContext.jsx";
import { formatDateBR } from "../utils/date.js";
import { statusClass, statusLabel } from "../utils/status.js";

const emptyForm = {
  service_order_number: "",
  title: "",
  description: "",
  date: "",
  start_time: "",
  end_time: "",
  location: "",
  vehicle: "",
  vehicle_ref: "",
  vehicle_2_ref: "",
  vehicle_3_ref: "",
  team_name: "",
  team_ref: "",
  chief_name: "",
  chief_ref: "",
  team_phone: "",
  agents: "",
  agents_ref: [],
  support_1: "",
  support_1_ref: "",
  support_2: "",
  support_2_ref: "",
  action_type: "",
  action_type_ref: "",
  institution_location: "",
  quantity: "",
  actions_count: "",
  schedule_text: "",
  time_2: "",
  time_3: "",
  address: "",
  neighborhood: "",
  neighborhood_ref: "",
  city: "",
  state: "",
  municipality_ref: "",
  external_responsible: "",
  external_responsible_phone: "",
  external_email: "",
  contact_email: "",
  requester_cpf: "",
  requester_role: "",
  requester_entity_type: "",
  audience: "",
  age_ranges: "",
  has_ramps: "",
  has_elevators: "",
  has_accessible_bathrooms: "",
  media_equipment: "",
  image_authorization: "",
  activity_type: "",
  responsible: "",
  sector: "",
  status: "PENDING",
  origin: "INTERNAL",
  cancel_reason: "",
  notes: "",
  kit_1: "",
  kit_1_quantity: "",
  material_1: "",
  kit_2: "",
  kit_2_quantity: "",
  material_2: "",
  kit_3: "",
  kit_3_quantity: "",
  material_3: "",
  kit_4: "",
  kit_4_quantity: "",
  material_4: "",
  kit_5: "",
  kit_5_quantity: "",
  material_5: "",
  kit_6: "",
  kit_6_quantity: "",
  material_6: "",
  kit_7: "",
  kit_7_quantity: "",
};

const agendaFields = Object.keys(emptyForm);

function valueForPayload(value) {
  return value === "" ? null : value;
}

function normalizePayload(form) {
  const payload = { ...form };
  const vehicles = [form.vehicle_ref, form.vehicle_2_ref, form.vehicle_3_ref]
    .map((id) => form.lookupVehicles?.find((vehicle) => String(vehicle.id) === String(id))?.name)
    .filter(Boolean);
  if (vehicles.length) {
    payload.vehicle = vehicles.join(" - ");
  }
  delete payload.service_order_number;
  delete payload.lookupVehicles;
  delete payload.vehicle_2_ref;
  delete payload.vehicle_3_ref;
  [
    "vehicle_ref",
    "team_ref",
    "chief_ref",
    "support_1_ref",
    "support_2_ref",
    "action_type_ref",
    "neighborhood_ref",
    "municipality_ref",
    "time_2",
    "time_3",
    "quantity",
    "actions_count",
    "kit_1_quantity",
    "kit_2_quantity",
    "kit_3_quantity",
    "kit_4_quantity",
    "kit_5_quantity",
    "kit_6_quantity",
    "kit_7_quantity",
  ].forEach((field) => {
    payload[field] = valueForPayload(payload[field]);
  });
  return payload;
}

function serviceOrderLabel(agenda) {
  const number = agenda?.service_order_number;
  return number ? `OS ${String(number).padStart(4, "0")}` : "-";
}

export default function AgendaPage() {
  const [agendas, setAgendas] = useState([]);
  const [pageInfo, setPageInfo] = useState({ count: 0, next: null, previous: null });
  const [sectors, setSectors] = useState([]);
  const [users, setUsers] = useState([]);
  const [lookups, setLookups] = useState({
    vehicles: [],
    teams: [],
    chiefs: [],
    agents: [],
    supports: [],
    actionTypes: [],
    municipalities: [],
    neighborhoods: [],
    kits: [],
    materials: [],
  });
  const [filters, setFilters] = useState({});
  const [form, setForm] = useState(emptyForm);
  const [editing, setEditing] = useState(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [historyAgenda, setHistoryAgenda] = useState(null);
  const [reviewStep, setReviewStep] = useState("summary");
  const [message, setMessage] = useState("");
  const [publicLinkMessage, setPublicLinkMessage] = useState("");
  const [availableDates, setAvailableDates] = useState([]);
  const [availableDatesLoading, setAvailableDatesLoading] = useState(false);
  const [pendingCount, setPendingCount] = useState(0);
  const { user } = useAuth();

  const hasMaxAccess = user?.role === "ADMIN" || user?.role === "MANAGER";
  const canUseRequestShortcuts = hasMaxAccess || user?.role === "SUPERVISOR";
  const canDelete = hasMaxAccess;
  const canChangeStatus = hasMaxAccess;
  const canManageRequests = hasMaxAccess;

  const fetchPendingCount = () => {
    if (canManageRequests) {
      api("/agendas/?status=PENDING&source=requests&page_size=1")
        .then((data) => setPendingCount(data.count || 0))
        .catch(() => {});
    }
  };

  const loadAgendas = () => {
    const params = new URLSearchParams({ page_size: "50", order: "latest", source: "requests", ...filters }).toString();
    api(`/agendas/?${params}`).then((data) => {
      setAgendas(data.results || data);
      setPageInfo({ count: data.count || (data.results || data).length, next: data.next, previous: data.previous });
    });
    fetchPendingCount();
  };

  useEffect(() => {
    api("/sectors/").then((data) => setSectors(data.results || data));
    api("/users/").then((data) => setUsers(data.results || data)).catch(() => setUsers(user ? [user] : []));
    Promise.all([
      api("/vehicles/?page_size=200"),
      api("/teams/?page_size=200"),
      api("/chiefs/?page_size=200"),
      api("/agents/?page_size=200"),
      api("/supports/?page_size=200"),
      api("/action-types/?page_size=200"),
      api("/municipalities/?page_size=200"),
      api("/neighborhoods/?page_size=500"),
      api("/kits/?page_size=1000"),
      api("/materials/?page_size=1000"),
    ]).then(([vehicles, teams, chiefs, agents, supports, actionTypes, municipalities, neighborhoods, kits, materials]) => {
      setLookups({
        vehicles: vehicles.results || vehicles,
        teams: teams.results || teams,
        chiefs: chiefs.results || chiefs,
        agents: agents.results || agents,
        supports: supports.results || supports,
        actionTypes: actionTypes.results || actionTypes,
        municipalities: municipalities.results || municipalities,
        neighborhoods: neighborhoods.results || neighborhoods,
        kits: kits.results || kits,
        materials: materials.results || materials,
      });
    });
  }, [user]);

  useEffect(loadAgendas, [filters]);

  const goToPage = (url) => {
    if (!url) return;
    const parsed = new URL(url);
    const params = parsed.search.replace("?", "");
    api(`/agendas/?${params}`).then((data) => {
      setAgendas(data.results || data);
      setPageInfo({ count: data.count || 0, next: data.next, previous: data.previous });
    });
  };

  const responsibleOptions = useMemo(() => (users.length ? users : [user]).filter(Boolean), [users, user]);

  const update = (field, value) => setForm((current) => ({ ...current, [field]: value }));

  const updateTime = (field, value) => {
    setForm((current) => {
      const next = { ...current, [field]: value };
      if (next.start_time && next.end_time) {
        next.schedule_text = `${next.start_time} - ${next.end_time}`;
      } else if (next.start_time) {
        next.schedule_text = next.start_time;
      } else {
        next.schedule_text = "";
      }
      return next;
    });
  };

  const selectLookup = (refField, textField, options, value, extra = () => ({})) => {
    const selected = options.find((option) => String(option.id) === String(value));
    setForm((current) => ({
      ...current,
      [refField]: value,
      [textField]: selected?.name || "",
      ...extra(selected),
    }));
  };

  const updateAgents = (selectedOptions) => {
    const ids = Array.from(selectedOptions).map((option) => option.value);
    const names = lookups.agents
      .filter((agent) => ids.includes(String(agent.id)))
      .map((agent) => agent.name);
    setForm((current) => ({ ...current, agents_ref: ids, agents: names.join(" - ") }));
  };

  const selectNameByValue = (field, options, value) => {
    const selected = options.find((option) => String(option.id) === String(value));
    update(field, selected?.name || "");
  };

  const belongsToTeam = (item, teamId, teamName) => {
    if (!teamId && !teamName) return true;
    return String(item.team || "") === String(teamId || "") || String(item.team_name || "").toUpperCase() === String(teamName || "").toUpperCase();
  };

  const isSupportRole = (item) => String(item.role || "").toUpperCase().includes("APOIO");

  const staffLabel = (item) => [item.name, item.role, item.address].filter(Boolean).join(" - ");

  const selectedTeam = lookups.teams.find((team) => String(team.id) === String(form.team_ref));
  const selectedTeamName = selectedTeam?.name || form.team_name;
  const teamChiefs = lookups.chiefs.filter((chief) => belongsToTeam(chief, form.team_ref, selectedTeamName));
  const allAgents = lookups.agents.filter((agent) => !isSupportRole(agent));
  const teamAgents = lookups.agents.filter((agent) => belongsToTeam(agent, form.team_ref, selectedTeamName) && !isSupportRole(agent));
  const teamSupports = lookups.supports.filter((support) => belongsToTeam(support, form.team_ref, selectedTeamName));
  const supportOptions = lookups.supports;
  const selectedAgentIds = (form.agents_ref || []).map(String);
  const selectedAgents = selectedAgentIds
    .map((id) => lookups.agents.find((agent) => String(agent.id) === id))
    .filter(Boolean);
  const availableAgents = allAgents.filter((agent) => !selectedAgentIds.includes(String(agent.id)));

  const setAgentSelection = (ids) => {
    const names = lookups.agents
      .filter((agent) => ids.includes(String(agent.id)))
      .map((agent) => agent.name);
    setForm((current) => ({ ...current, agents_ref: ids, agents: names.join(" - ") }));
  };

  const addAgent = (value) => {
    if (!value || selectedAgentIds.includes(String(value))) return;
    setAgentSelection([...selectedAgentIds, String(value)]);
  };

  const replaceAgent = (oldValue, newValue) => {
    if (!newValue) return;
    const nextIds = selectedAgentIds.map((id) => (id === String(oldValue) ? String(newValue) : id));
    setAgentSelection(Array.from(new Set(nextIds)));
  };

  const removeAgent = (value) => {
    setAgentSelection(selectedAgentIds.filter((id) => id !== String(value)));
  };

  const handleTeamChange = (value) => {
    const team = lookups.teams.find((option) => String(option.id) === String(value));
    const chiefs = lookups.chiefs.filter((chief) => belongsToTeam(chief, value, team?.name || ""));
    const chief = chiefs[0];
    const agents = lookups.agents.filter((agent) => belongsToTeam(agent, value, team?.name || "") && !isSupportRole(agent));
    const supports = lookups.supports.filter((support) => belongsToTeam(support, value, team?.name || ""));
    const support1 = supports[0];
    const support2 = supports[1];

    setForm((current) => ({
      ...current,
      team_ref: value,
      team_name: team?.name || "",
      chief_ref: chief?.id || "",
      chief_name: chief?.name || "",
      team_phone: chief?.phone || "",
      agents_ref: agents.map((agent) => String(agent.id)),
      agents: agents.map((agent) => agent.name).join(" - "),
      support_1_ref: support1?.id || "",
      support_1: support1?.name || "",
      support_2_ref: support2?.id || "",
      support_2: support2?.name || "",
    }));
  };

  const submit = async (event) => {
    event.preventDefault();
    setMessage("");
    const payload = normalizePayload({ ...form, lookupVehicles: lookups.vehicles });
    try {
      if (editing) {
        await api(`/agendas/${editing}/`, { method: "PUT", body: JSON.stringify(payload) });
      } else {
        await api("/agendas/", { method: "POST", body: JSON.stringify(payload) });
      }
      setForm(emptyForm);
      setEditing(null);
      setIsModalOpen(false);
      setMessage("Agenda salva com sucesso.");
      loadAgendas();
    } catch (err) {
      setMessage(err.message);
    }
  };

  const edit = (agenda) => {
    setEditing(agenda.id);
    setIsModalOpen(true);
    setForm(
      agendaFields.reduce((values, field) => {
        const value = agenda[field] ?? "";
        values[field] = field === "responsible"
          ? (user?.id || value)
          : field.endsWith("_time") && value ? value.slice(0, 5) : value;
        return values;
      }, { responsible: user?.id || "" })
    );
  };

  const reviewAndSchedule = (agenda) => {
    edit(agenda);
    setReviewStep("summary");
    setMessage("");
  };

  const openNew = () => {
    if (!canManageRequests) return;
    setEditing(null);
    setForm({ ...emptyForm, responsible: user?.id || "" });
    setReviewStep("form");
    setMessage("");
    setIsModalOpen(true);
  };

  const remove = async (id) => {
    await api(`/agendas/${id}/`, { method: "DELETE" });
    loadAgendas();
  };

  const changeStatus = async (agenda, status) => {
    if (!canChangeStatus) {
      setMessage("Seu perfil pode visualizar solicitações, mas não aprovar ou recusar.");
      return;
    }
    setMessage("");
    if (status === "APPROVED") {
      const hasTeam = agenda.team_ref || agenda.team_name || agenda.sector;
      const hasChief = agenda.chief_ref || agenda.chief_name;
      const hasAgents = (agenda.agents_ref || []).length || agenda.agents;
      if (!hasTeam || !hasChief || !hasAgents) {
        reviewAndSchedule(agenda);
        setMessage("Antes de aprovar, informe equipe, chefe e agentes escalados.");
        return;
      }
    }
    let cancelReason = agenda.cancel_reason || "";
    if (status === "CANCELLED") {
      cancelReason = window.prompt("Informe o motivo do cancelamento:", cancelReason);
      if (!cancelReason?.trim()) {
        setMessage("Informe o motivo do cancelamento.");
        return;
      }
    }
    try {
      await api(`/agendas/${agenda.id}/`, {
        method: "PATCH",
        body: JSON.stringify({ status, cancel_reason: status === "CANCELLED" ? cancelReason : "" }),
      });
      setMessage(`Agenda ${status === "APPROVED" ? "aprovada" : "cancelada"} com sucesso.`);
      loadAgendas();
    } catch (err) {
      setMessage(err.message);
    }
  };

  const decideReview = async (status) => {
    if (!editing) return;
    if (!canManageRequests) {
      setMessage("Seu perfil pode visualizar solicitações, mas não aprovar ou recusar.");
      return;
    }
    setMessage("");
    const nextForm = { ...form, status };
    if (status === "APPROVED") {
      const hasSchedule = nextForm.date && nextForm.start_time && nextForm.end_time;
      const hasResponsible = nextForm.responsible;
      const hasLocation = nextForm.location;
      const hasVehicle = nextForm.vehicle_ref || nextForm.vehicle;
      const hasTeam = nextForm.team_ref || nextForm.team_name || nextForm.sector;
      const hasChief = nextForm.chief_ref || nextForm.chief_name;
      const hasAgents = (nextForm.agents_ref || []).length || nextForm.agents;
      const hasKitQuantity = nextForm.kit_1_quantity;
      nextForm.kit_1 = nextForm.kit_1 || lookups.kits[0]?.name || "KIT PADRÃO";
      if (!hasSchedule || !hasResponsible || !hasLocation || !hasVehicle || !hasTeam || !hasChief || !hasAgents || !hasKitQuantity) {
        setMessage("Para aprovar, informe data, horário, responsável, local, viatura, equipe, chefe, agentes e quantidade de kits.");
        return;
      }
    }
    if (status === "CANCELLED") {
      const reason = window.prompt("Informe o motivo da recusa:", nextForm.cancel_reason || "");
      if (!reason?.trim()) {
        setMessage("Informe o motivo da recusa.");
        return;
      }
      nextForm.cancel_reason = reason;
    }
    try {
      await api(`/agendas/${editing}/`, { method: "PUT", body: JSON.stringify(normalizePayload({ ...nextForm, lookupVehicles: lookups.vehicles })) });
      setForm(emptyForm);
      setEditing(null);
      setIsModalOpen(false);
      setMessage(status === "APPROVED" ? "Solicitação aprovada e escalada." : status === "CANCELLED" ? "Solicitação recusada." : "Solicitação mantida como pendente.");
      loadAgendas();
    } catch (err) {
      setMessage(err.message);
    }
  };

  const publicRequestLink = `${window.location.origin}/solicitar-agenda`;
  const surveyLink = (agenda) => agenda?.satisfaction_survey_token ? `${window.location.origin}/pesquisa-satisfacao/${agenda.satisfaction_survey_token}` : "";
  const updateFilter = (field, value) => setFilters((current) => ({ ...current, [field]: value }));

  const copyPublicLink = async () => {
    try {
      await navigator.clipboard.writeText(publicRequestLink);
      setPublicLinkMessage("Link público copiado.");
    } catch {
      setPublicLinkMessage(publicRequestLink);
    }
  };

  const copySurveyLink = async (agenda) => {
    const link = surveyLink(agenda);
    if (!link) return;
    try {
      await navigator.clipboard.writeText(link);
      setMessage("Link da pesquisa copiado.");
    } catch {
      setMessage(link);
    }
  };

  const ensureSurveyLink = async (agenda, openLink = true) => {
    if (!canManageRequests) {
      setMessage("Seu perfil pode visualizar solicitações, mas não gerar links de pesquisa.");
      return "";
    }
    setMessage("");
    try {
      const data = await api(`/agendas/${agenda.id}/satisfaction-survey-link/`, { method: "POST", body: JSON.stringify({}) });
      const updatedAgenda = {
        ...agenda,
        satisfaction_survey_token: data.token,
        satisfaction_survey_answered_at: data.answered_at,
      };
      setAgendas((current) => current.map((item) => item.id === agenda.id ? updatedAgenda : item));
      if (String(form.id || editing) === String(agenda.id)) {
        setForm((current) => ({ ...current, ...updatedAgenda }));
      }
      setMessage("Link da pesquisa gerado.");
      if (openLink) {
        window.open(data.url, "_blank", "noreferrer");
      }
      return data.url;
    } catch (err) {
      setMessage(err.message);
      return "";
    }
  };

  const sendAvailableDates = async (id, month, days) => {
    if (!canManageRequests) {
      setMessage("Seu perfil pode visualizar solicitações, mas não sugerir datas.");
      return;
    }
    setMessage("");
    if (!month?.trim() || !days?.trim()) return;
    
    try {
      const response = await api(`/agendas/${id}/send-available-dates/`, {
        method: "POST",
        body: JSON.stringify({ month: month.trim(), days: days.trim(), message: form.available_message || "" }),
      });
      setMessage(response.detail || "E-mail com datas disponíveis enviado com sucesso.");
      setReviewStep("summary");
      loadAgendas();
    } catch (err) {
      setMessage(err.message);
    }
  };

  const checkAvailableDates = async () => {
    if (!editing) return;
    setReviewStep("suggest_dates");
    setAvailableDatesLoading(true);
    setMessage("");
    try {
      const data = await api(`/agendas/${editing}/available-dates/`);
      setAvailableDates(data.dates || []);
      setForm((current) => ({
        ...current,
        available_month: data.month || current.available_month || "",
        available_days: data.days || current.available_days || "",
        available_message: data.message || current.available_message || "",
      }));
    } catch (err) {
      setMessage(err.message);
    } finally {
      setAvailableDatesLoading(false);
    }
  };


  return (
    <section className="page">
      <div className="main-column">
        <div className="page-title">
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: "12px", flexWrap: "wrap", marginBottom: "4px" }}>
              <h1 style={{ margin: 0 }}>Solicitações</h1>
              {canManageRequests && pendingCount > 0 && (
                <span
                  style={{
                    background: "#f6bd16",
                    color: "#001338",
                    padding: "4px 10px",
                    borderRadius: "20px",
                    fontSize: "12px",
                    fontWeight: "800",
                    display: "inline-flex",
                    alignItems: "center",
                    boxShadow: "0 4px 10px rgba(246, 189, 22, 0.3)",
                    animation: "pulse 2s infinite"
                  }}
                >
                  {pendingCount} {pendingCount === 1 ? "PENDENTE" : "PENDENTES"}
                </span>
              )}
            </div>
            <p style={{ margin: 0 }}>Avalie solicitações recebidas pelo formulário público e faça a escala operacional.</p>
          </div>
          {canUseRequestShortcuts && <div className="page-actions">
            <a className="secondary action-link" href="/solicitacao-interna">
              <Plus size={18} /> Solicitação interna
            </a>
            <a className="secondary action-link" href="/solicitar-agenda" target="_blank" rel="noreferrer">
              <ExternalLink size={18} /> Link público
            </a>
            <button className="secondary" type="button" onClick={copyPublicLink}><Copy size={18} /> Copiar link</button>
          </div>}
        </div>
        {publicLinkMessage && <div className="alert">{publicLinkMessage}</div>}
        <div className="filters request-filters">
          <input
            placeholder="Buscar protocolo ou OS"
            value={filters.q || ""}
            onChange={(event) => updateFilter("q", event.target.value)}
          />
          <label className="filter-field">
            <span>Data</span>
            <input type="date" value={filters.date || ""} onChange={(event) => updateFilter("date", event.target.value)} />
          </label>
          <select value={filters.status || ""} onChange={(event) => updateFilter("status", event.target.value)}>
            <option value="">Todos os status</option>
            <option value="PENDING">Pendente</option>
            <option value="APPROVED">Aprovada</option>
            <option value="CANCELLED">Recusada</option>
          </select>
          <button className="secondary" onClick={() => setFilters({})}>
            Limpar
          </button>
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Protocolo</th>
                <th>O.S.</th>
                <th>Solicitante</th>
                <th>Instituição</th>
                <th>Data</th>
                <th>Horário</th>
                <th>Município</th>
                <th>Participantes</th>
                <th>Status</th>
                <th className="actions-heading">Ação</th>
              </tr>
            </thead>
            <tbody>
              {agendas.map((agenda) => (
                <tr key={agenda.id}>
                  <td><strong>#{agenda.id}</strong></td>
                  <td><strong>{serviceOrderLabel(agenda)}</strong></td>
                  <td>{agenda.external_responsible || "-"}</td>
                  <td>{agenda.institution_location || agenda.location || "-"}</td>
                  <td>{formatDateBR(agenda.date)}</td>
                  <td>{agenda.start_time.slice(0, 5)}</td>
                  <td>{agenda.city || "-"}</td>
                  <td>{agenda.quantity || "-"}</td>
                  <td><span className={`badge ${statusClass[agenda.status]}`}>{statusLabel[agenda.status]}</span></td>
                  <td className="row-actions">
                    <button className="secondary" onClick={() => reviewAndSchedule(agenda)}>
                      <ClipboardCheck size={16} /> Avaliar solicitação
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="pagination-bar">
            <span>{pageInfo.count} registros</span>
            <div>
              <button className="secondary" disabled={!pageInfo.previous} onClick={() => goToPage(pageInfo.previous)}>Anterior</button>
              <button className="secondary" disabled={!pageInfo.next} onClick={() => goToPage(pageInfo.next)}>Próxima</button>
            </div>
          </div>
        </div>
      </div>

      {isModalOpen && (
        <div className="modal-backdrop" onClick={() => setIsModalOpen(false)}>
          <article className="modal agenda-modal" onClick={(event) => event.stopPropagation()}>
            <div className="modal-header">
              <h2>{editing ? "Avaliar solicitação" : "Nova agenda"}</h2>
              <button type="button" className="icon-button" onClick={() => setIsModalOpen(false)} aria-label="Fechar">×</button>
            </div>
            <div className="review-card">
              <strong>Solicitação recebida pelo formulário</strong>
              <span>{form.external_responsible || "Solicitante não informado"} · {form.institution_location || form.location || "Local não informado"}</span>
              <small>Confira os dados enviados. Se aprovar, preencha a escala operacional antes de confirmar.</small>
            </div>
            <div className="request-summary-grid">
              <span><b>Protocolo</b>#{editing || "-"}</span>
              <span><b>Ordem de serviço</b>{serviceOrderLabel(form)}</span>
              <span><b>Solicitante</b>{form.external_responsible || "-"}</span>
              <span><b>E-mail</b>{form.external_email || "-"}</span>
              <span><b>Telefone</b>{form.external_responsible_phone || "-"}</span>
              <span><b>Instituição</b>{form.institution_location || "-"}</span>
              <span><b>Tipo de entidade</b>{form.requester_entity_type || "-"}</span>
              <span><b>Modalidade</b>{form.action_type || "-"}</span>
              <span><b>Data e horário</b>{form.date ? formatDateBR(form.date) : "-"} às {form.start_time || "-"}</span>
              <span><b>Ações</b>{form.actions_count || "-"}</span>
              <span><b>Participantes</b>{form.quantity || "-"}</span>
              <span><b>Faixa etária</b>{form.age_ranges || "-"}</span>
              <span><b>Endereço</b>{[form.address, form.neighborhood, form.city, form.state].filter(Boolean).join(", ") || "-"}</span>
              <span><b>Acessibilidade</b>Rampa: {form.has_ramps || "-"} · Elevador: {form.has_elevators || "-"} · Banheiro: {form.has_accessible_bathrooms || "-"}</span>
              <span><b>Recursos</b>{form.media_equipment || "-"}</span>
              <span className="full"><b>Autorização de imagem</b>{form.image_authorization || "-"}</span>
              {form.notes && <span className="full"><b>Observações</b>{form.notes}</span>}
            </div>
            {canManageRequests && form.satisfaction_survey_token && (
              <div className="review-actions">
                <a className="secondary action-link" href={surveyLink(form)} target="_blank" rel="noreferrer">
                  <ExternalLink size={18} /> Abrir pesquisa
                </a>
                <button type="button" className="secondary" onClick={() => copySurveyLink(form)}>
                  <Copy size={18} /> Copiar link da pesquisa
                </button>
                {form.satisfaction_survey_answered_at && <span className="badge success">Pesquisa respondida</span>}
              </div>
            )}
            {canManageRequests && !form.satisfaction_survey_token && (
              <div className="review-actions">
                <button type="button" className="secondary" onClick={() => ensureSurveyLink({ ...form, id: editing })}>
                  <ExternalLink size={18} /> Gerar link da pesquisa
                </button>
              </div>
            )}
            {editing && reviewStep === "summary" && message && <div className="alert">{message}</div>}
            {editing && reviewStep === "summary" && canManageRequests && (
              <div className="review-actions">
                <button type="button" className="approve-action" onClick={() => setReviewStep("schedule")}>
                  <CheckCircle2 size={18} /> Aprovar
                </button>
                <button type="button" className="danger" onClick={() => decideReview("CANCELLED")}>
                  <XCircle size={18} /> Recusar
                </button>
                <button type="button" className="secondary" onClick={checkAvailableDates}>
                  Verificar datas disponíveis
                </button>
                <a href="/calendario" target="_blank" rel="noreferrer" className="button secondary" style={{ display: "inline-flex", alignItems: "center", gap: "8px", textDecoration: "none", color: "inherit" }}>
                  Ver datas abertas
                </a>
              </div>
            )}
            {editing && reviewStep === "suggest_dates" && (
              <form
                onSubmit={(event) => {
                  event.preventDefault();
                  sendAvailableDates(editing, form.available_month, form.available_days);
                }}
                className="stack-form approval-form"
              >
                <div className="form-section">
                  <h3>Verificar datas disponíveis</h3>
                  <p>Confira as datas com vaga e envie uma resposta para o solicitante alterar a data no próprio formulário do protocolo.</p>
                  {availableDatesLoading && <div className="alert">Buscando datas disponíveis...</div>}
                  {!availableDatesLoading && availableDates.length > 0 && (
                    <div className="date-chip-list">
                      {availableDates.map((item) => (
                        <button
                          key={item.date}
                          type="button"
                          className="secondary"
                          onClick={() => update("available_days", item.label)}
                        >
                          {item.label}
                        </button>
                      ))}
                    </div>
                  )}
                  <label className="field-label">
                    <span>Mês com disponibilidade</span>
                    <input
                      placeholder="Ex: Julho"
                      value={form.available_month || ""}
                      onChange={(e) => update("available_month", e.target.value)}
                      required
                    />
                  </label>
                  <label className="field-label">
                    <span>Dias disponíveis</span>
                    <input
                      placeholder="Ex: 12, 15 e 20"
                      value={form.available_days || ""}
                      onChange={(e) => update("available_days", e.target.value)}
                      required
                    />
                  </label>
                  <label className="field-label">
                    <span>Resposta para o solicitante</span>
                    <textarea
                      rows="9"
                      value={form.available_message || ""}
                      onChange={(e) => update("available_message", e.target.value)}
                      required
                    />
                  </label>
                </div>
                {message && <div className="alert">{message}</div>}
                <div className="review-actions">
                  <button type="button" className="secondary" onClick={() => setReviewStep("summary")}>Voltar</button>
                  <button type="submit" className="approve-action"><CheckCircle2 size={18} /> Enviar sugestão de datas</button>
                </div>
              </form>
            )}
            {editing && reviewStep === "schedule" && (
              <form
                onSubmit={(event) => {
                  event.preventDefault();
                  decideReview("APPROVED");
                }}
                className="stack-form approval-form"
              >
                <div className="form-section">
                  <h3>Escala operacional</h3>
                  <div className="compact-grid">
                    <label className="field-label">
                      <span>Data</span>
                      <input type="date" value={form.date || ""} onChange={(e) => update("date", e.target.value)} required />
                    </label>
                    <label className="field-label">
                      <span>Responsável interno</span>
                      <select value={form.responsible || ""} onChange={(e) => update("responsible", e.target.value)} required>
                        <option value="">Selecione o responsável</option>
                        {responsibleOptions.map((option) => <option key={option.id} value={option.id}>{option.full_name}</option>)}
                      </select>
                    </label>
                  </div>
                  <div className="compact-grid">
                    <label className="field-label">
                      <span>Início</span>
                      <input type="time" value={form.start_time || ""} onChange={(e) => updateTime("start_time", e.target.value)} required />
                    </label>
                    <label className="field-label">
                      <span>Fim</span>
                      <input type="time" value={form.end_time || ""} onChange={(e) => updateTime("end_time", e.target.value)} required />
                    </label>
                  </div>
                  <label className="field-label">
                    <span>Instituição/local</span>
                    <input value={form.institution_location || ""} onChange={(e) => update("institution_location", e.target.value)} placeholder="Instituição/local" />
                  </label>
                  <label className="field-label">
                    <span>Local para checagem de conflito</span>
                    <input value={form.location || ""} onChange={(e) => update("location", e.target.value)} placeholder="Local" required />
                  </label>
                  <div className="compact-grid">
                    <label className="field-label">
                      <span>Equipe</span>
                      <select value={form.team_ref || ""} onChange={(e) => handleTeamChange(e.target.value)} required>
                        <option value="">Selecione a equipe</option>
                        {lookups.teams.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
                      </select>
                    </label>
                    <label className="field-label">
                      <span>Chefe</span>
                      <select value={form.chief_ref || ""} onChange={(e) => selectLookup("chief_ref", "chief_name", lookups.chiefs, e.target.value, (selected) => ({ team_phone: selected?.phone || form.team_phone }))} required>
                        <option value="">Selecione o chefe</option>
                        {teamChiefs.map((item) => <option key={item.id} value={item.id}>{staffLabel(item)}</option>)}
                      </select>
                    </label>
                  </div>
                  <div className="compact-grid">
                    <label className="field-label">
                      <span>Telefone do chefe</span>
                      <input value={form.team_phone} onChange={(e) => update("team_phone", e.target.value)} placeholder="Telefone" />
                    </label>
                    <label className="field-label">
                      <span>Viatura</span>
                      <select value={form.vehicle_ref || ""} onChange={(e) => selectLookup("vehicle_ref", "vehicle", lookups.vehicles, e.target.value)} required>
                        <option value="">Selecione a viatura</option>
                        {lookups.vehicles.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
                      </select>
                    </label>
                  </div>
                  <div className="compact-grid">
                    <label className="field-label">
                      <span>Viatura 2</span>
                      <select value={form.vehicle_2_ref || ""} onChange={(e) => update("vehicle_2_ref", e.target.value)}>
                        <option value="">Sem segunda viatura</option>
                        {lookups.vehicles.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
                      </select>
                    </label>
                    <label className="field-label">
                      <span>Viatura 3</span>
                      <select value={form.vehicle_3_ref || ""} onChange={(e) => update("vehicle_3_ref", e.target.value)}>
                        <option value="">Sem terceira viatura</option>
                        {lookups.vehicles.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
                      </select>
                    </label>
                  </div>
                  <label className="field-label">
                    <span>Agentes escalados</span>
                    <div className="agent-picker">
                      <div className="agent-select-list">
                        {selectedAgents.length ? selectedAgents.map((item) => (
                          <div className="agent-select-row" key={item.id}>
                            <select value={item.id} onChange={(e) => replaceAgent(item.id, e.target.value)}>
                              {allAgents.map((agent) => (
                                <option
                                  disabled={selectedAgentIds.includes(String(agent.id)) && String(agent.id) !== String(item.id)}
                                  key={agent.id}
                                  value={agent.id}
                                >
                                  {staffLabel(agent)}
                                </option>
                              ))}
                            </select>
                            <button type="button" className="icon-soft danger" onClick={() => removeAgent(item.id)} aria-label={`Remover ${item.name}`}>
                              <XCircle size={16} />
                            </button>
                          </div>
                        )) : <div className="empty-selection">Nenhum agente escalado.</div>}
                      </div>
                      <select value="" onChange={(e) => addAgent(e.target.value)} disabled={!availableAgents.length}>
                        <option value="">{availableAgents.length ? "Adicionar outro agente" : "Sem agentes disponíveis para adicionar"}</option>
                        {availableAgents.map((item) => <option key={item.id} value={item.id}>{staffLabel(item)}</option>)}
                      </select>
                    </div>
                  </label>
                  <div className="compact-grid">
                    <label className="field-label">
                      <span>Apoio 1</span>
                      <select value={form.support_1_ref || ""} onChange={(e) => selectLookup("support_1_ref", "support_1", lookups.supports, e.target.value)}>
                        <option value="">Sem Apoio</option>
                        {supportOptions.map((item) => <option key={item.id} value={item.id}>{staffLabel(item)}</option>)}
                      </select>
                    </label>
                    <label className="field-label">
                      <span>Apoio 2</span>
                      <select value={form.support_2_ref || ""} onChange={(e) => selectLookup("support_2_ref", "support_2", lookups.supports, e.target.value)}>
                        <option value="">Sem Apoio</option>
                        {supportOptions.map((item) => <option key={item.id} value={item.id}>{staffLabel(item)}</option>)}
                      </select>
                    </label>
                  </div>
                  <label className="field-label">
                    <span>Quantidade de kits</span>
                    <input type="number" min="1" placeholder="Informe a quantidade" value={form.kit_1_quantity} onChange={(e) => update("kit_1_quantity", e.target.value)} required />
                  </label>
                </div>
                {message && <div className="alert">{message}</div>}
                <div className="review-actions">
                  <button type="button" className="secondary" onClick={() => setReviewStep("summary")}>Voltar</button>
                  <button type="button" className="secondary" onClick={checkAvailableDates}>Verificar datas disponíveis</button>
                  <button type="submit" className="approve-action"><CheckCircle2 size={18} /> Confirmar aprovação</button>
                </div>
              </form>
            )}
            {!editing && (
            <form onSubmit={submit} className="stack-form">
          <div className="form-section">
            <h3>Dados da agenda</h3>
            <input placeholder="Título" value={form.title} onChange={(e) => update("title", e.target.value)} required />
            <textarea placeholder="Descrição" value={form.description} onChange={(e) => update("description", e.target.value)} required />
            <div className="split">
              <input type="date" value={form.date} onChange={(e) => update("date", e.target.value)} required />
              <input type="time" value={form.start_time} onChange={(e) => updateTime("start_time", e.target.value)} required />
              <input type="time" value={form.end_time} onChange={(e) => updateTime("end_time", e.target.value)} required />
            </div>
            <div className="compact-grid">
              <input placeholder="Horário descritivo" value={form.schedule_text} readOnly />
              <input type="number" min="0" placeholder="QTD" value={form.quantity} onChange={(e) => update("quantity", e.target.value)} />
            </div>
            <div className="compact-grid">
              <input type="number" min="1" max="3" placeholder="Nº de ações" value={form.actions_count} onChange={(e) => update("actions_count", e.target.value)} />
              <input type="time" value={form.time_2} onChange={(e) => update("time_2", e.target.value)} aria-label="Horário 2" />
            </div>
            <input type="time" value={form.time_3} onChange={(e) => update("time_3", e.target.value)} aria-label="Horário 3" />
            <div className="compact-grid">
              <select value={form.action_type_ref || ""} onChange={(e) => selectLookup("action_type_ref", "action_type", lookups.actionTypes, e.target.value)}>
                <option value="">Tipo de ação</option>
                {lookups.actionTypes.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
              </select>
              <input placeholder="Tipo" value={form.activity_type} onChange={(e) => update("activity_type", e.target.value)} />
            </div>
          </div>

          <div className="form-section">
            <h3>Equipe e local</h3>
            <div className="compact-grid">
              <select value={form.vehicle_ref || ""} onChange={(e) => selectLookup("vehicle_ref", "vehicle", lookups.vehicles, e.target.value)}>
                <option value="">Viatura</option>
                {lookups.vehicles.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
              </select>
              <select value={form.team_ref || ""} onChange={(e) => selectLookup("team_ref", "team_name", lookups.teams, e.target.value)}>
                <option value="">Equipe</option>
                {lookups.teams.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
              </select>
            </div>
            <div className="compact-grid">
              <select value={form.chief_ref || ""} onChange={(e) => selectLookup("chief_ref", "chief_name", lookups.chiefs, e.target.value, (selected) => ({ team_phone: selected?.phone || form.team_phone }))}>
                <option value="">Chefe</option>
                {lookups.chiefs.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
              </select>
              <input placeholder="Telefone" value={form.team_phone} onChange={(e) => update("team_phone", e.target.value)} />
            </div>
            <select multiple className="multi-select" value={(form.agents_ref || []).map(String)} onChange={(e) => updateAgents(e.target.selectedOptions)}>
              {lookups.agents.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
            </select>
            <textarea placeholder="Agentes" value={form.agents} onChange={(e) => update("agents", e.target.value)} />
            <div className="compact-grid">
              <select value={form.support_1_ref || ""} onChange={(e) => selectLookup("support_1_ref", "support_1", lookups.supports, e.target.value)}>
                <option value="">Apoio 1</option>
                {lookups.supports.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
              </select>
              <select value={form.support_2_ref || ""} onChange={(e) => selectLookup("support_2_ref", "support_2", lookups.supports, e.target.value)}>
                <option value="">Apoio 2</option>
                {lookups.supports.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
              </select>
            </div>
            <input placeholder="Instituição/local" value={form.institution_location} onChange={(e) => update("institution_location", e.target.value)} />
            <input placeholder="Local" value={form.location} onChange={(e) => update("location", e.target.value)} required />
            <input placeholder="Endereço" value={form.address} onChange={(e) => update("address", e.target.value)} />
            <div className="compact-grid">
              <select value={form.neighborhood_ref || ""} onChange={(e) => selectLookup("neighborhood_ref", "neighborhood", lookups.neighborhoods, e.target.value)}>
                <option value="">Bairro</option>
                {lookups.neighborhoods.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
              </select>
              <select value={form.municipality_ref || ""} onChange={(e) => selectLookup("municipality_ref", "city", lookups.municipalities, e.target.value)}>
                <option value="">Município</option>
                {lookups.municipalities.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
              </select>
            </div>
            <input placeholder="UF" value={form.state} onChange={(e) => update("state", e.target.value)} />
            <select value={form.sector} onChange={(e) => update("sector", e.target.value)} required>
              <option value="">Equipe</option>
              {sectors.map((sector) => <option key={sector.id} value={sector.id}>{sector.name}</option>)}
            </select>
          </div>

          <div className="form-section">
            <h3>Responsável e público</h3>
            <select value={form.responsible} onChange={(e) => update("responsible", e.target.value)} required>
              <option value="">Responsável interno</option>
              {responsibleOptions.map((option) => <option key={option.id} value={option.id}>{option.full_name}</option>)}
            </select>
            <input placeholder="Responsável no local" value={form.external_responsible} onChange={(e) => update("external_responsible", e.target.value)} />
            <div className="compact-grid">
              <input placeholder="Telefone do responsável" value={form.external_responsible_phone} onChange={(e) => update("external_responsible_phone", e.target.value)} />
              <input type="email" placeholder="E-mail" value={form.external_email} onChange={(e) => update("external_email", e.target.value)} />
            </div>
            <div className="compact-grid">
              <input placeholder="Cargo/função" value={form.requester_role} onChange={(e) => update("requester_role", e.target.value)} />
              <input placeholder="Tipo de entidade" value={form.requester_entity_type} onChange={(e) => update("requester_entity_type", e.target.value)} />
            </div>
            <input placeholder="Público" value={form.audience} onChange={(e) => update("audience", e.target.value)} />
            <input placeholder="Faixa etária" value={form.age_ranges} onChange={(e) => update("age_ranges", e.target.value)} />
            <div className="compact-grid three-cols">
              <input placeholder="Rampa" value={form.has_ramps} onChange={(e) => update("has_ramps", e.target.value)} />
              <input placeholder="Elevador" value={form.has_elevators} onChange={(e) => update("has_elevators", e.target.value)} />
              <input placeholder="Banheiro adaptado" value={form.has_accessible_bathrooms} onChange={(e) => update("has_accessible_bathrooms", e.target.value)} />
            </div>
            <input placeholder="Equipamentos disponíveis" value={form.media_equipment} onChange={(e) => update("media_equipment", e.target.value)} />
            <textarea placeholder="Autorização de imagem" value={form.image_authorization} onChange={(e) => update("image_authorization", e.target.value)} />
            <textarea placeholder="Observação" value={form.notes} onChange={(e) => update("notes", e.target.value)} />
          </div>

          <div className="form-section">
            <h3>Kits e materiais</h3>
            {Array.from({ length: 7 }, (_, index) => {
              const number = index + 1;
              return (
                <div className="kit-row" key={number}>
                  <select value="" onChange={(e) => selectNameByValue(`kit_${number}`, lookups.kits, e.target.value)}>
                    <option value="">{form[`kit_${number}`] || `Kit ${number}`}</option>
                    {lookups.kits.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
                  </select>
                  <input type="number" min="0" placeholder={`QTD ${number}`} value={form[`kit_${number}_quantity`]} onChange={(e) => update(`kit_${number}_quantity`, e.target.value)} />
                  {number < 7 && (
                    <select value="" onChange={(e) => selectNameByValue(`material_${number}`, lookups.materials, e.target.value)}>
                      <option value="">{form[`material_${number}`] || `Material ${number}`}</option>
                      {lookups.materials.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
                    </select>
                  )}
                </div>
              );
            })}
          </div>
          {message && <div className="alert">{message}</div>}
          <button><Save size={18} /> Salvar</button>
            </form>
            )}
          </article>
        </div>
      )}

      {historyAgenda && (
        <div className="modal-backdrop" onClick={() => setHistoryAgenda(null)}>
          <article className="modal" onClick={(event) => event.stopPropagation()}>
            <div className="modal-header">
              <h2>Histórico da agenda</h2>
              <button type="button" className="icon-button" onClick={() => setHistoryAgenda(null)} aria-label="Fechar">×</button>
            </div>
            <div className="history-list">
              {(historyAgenda.history || []).length ? (
                historyAgenda.history.map((item) => (
                  <div className="history-item" key={item.id}>
                    <strong>{item.action}</strong>
                    <span>{item.changed_by_name || "Sistema"} - {new Date(item.created_at).toLocaleString("pt-BR")}</span>
                    {item.snapshot?.status && <small>Status: {statusLabel[item.snapshot.status] || item.snapshot.status}</small>}
                    {item.snapshot?.cancel_reason && <small>Motivo: {item.snapshot.cancel_reason}</small>}
                  </div>
                ))
              ) : (
                <p>Nenhum histórico registrado.</p>
              )}
            </div>
          </article>
        </div>
      )}
    </section>
  );
}
