import { CheckCircle2, ClipboardCheck, Copy, ExternalLink, History, Plus, Save, Trash2, XCircle, Edit, Star } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { api } from "../api/client.js";
import Filters from "../components/Filters.jsx";
import { useAuth } from "../context/AuthContext.jsx";
import { STREET_ACTION_TYPE_OPTIONS } from "../utils/streetActionTypes.js";
import { formatDateBR, normalizeTime, addHoursToTime } from "../utils/date.js";
import { STREET_ACTION_ID } from "../utils/constants.js";
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
  service_order_mode: "TEAM",
  designated_users: [],
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
  participant_range: "",
  street_action_details: [],
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
  accessibility_access: "",
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
  materials: [],
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

const lowerAgeRangeOptions = new Set([
  "04 até 8 anos",
  "09 até 13 anos",
  "05 - 10 anos (ensino fundamental - anos iniciais)",
  "11 - 14 anos (ensino fundamental - anos finais)",
]);

const teenAgeRangeOptions = new Set([
  "14 até 17 anos",
  "15 - 17 anos (ensino médio)",
]);

const adultAgeRangeOptions = new Set([
  "acima de 18 anos",
  "acima de 18 anos - Adultos",
]);

function normalizeAgeRanges(value) {
  if (Array.isArray(value)) {
    return value;
  }
  if (typeof value === "string" && value.trim()) {
    return value.split(",").map((item) => item.trim()).filter(Boolean);
  }
  return [];
}

function hasAnyAgeRange(ranges, allowedRanges) {
  return ranges.some((range) => allowedRanges.has(range));
}

function normalizeMaterialRows(rows = []) {
  return rows
    .filter((item) => item?.kit || item?.material || item?.dynamic)
    .map((item, index) => ({
      id: item.id,
      position: item.position || index + 1,
      kit: item.kit || null,
      kit_name: item.kit_name || "",
      material: item.material || null,
      material_name: item.material_name || "",
      dynamic: item.dynamic || null,
      dynamic_name: item.dynamic_name || "",
      quantity: item.quantity ?? "",
    }));
}

function valueForPayload(value) {
  return value === "" ? null : value;
}

function getDiffPayload(payload, original) {
  if (!original) return payload;
  const changes = {};
  for (const key of Object.keys(payload)) {
    let oldVal = original[key];
    let newVal = payload[key];
    if (oldVal === null || oldVal === undefined) oldVal = "";
    if (newVal === null || newVal === undefined) newVal = "";
    
    // Normalize time for comparison (e.g., "12:00:00" vs "12:00")
    if ((key === "start_time" || key === "end_time" || key === "time_2" || key === "time_3") && oldVal.length === 8 && newVal.length === 5) {
      oldVal = oldVal.slice(0, 5);
    }
    
    if (key === "materials") {
      changes[key] = payload[key]; // Always send materials on update to be safe
    } else if (String(oldVal) !== String(newVal)) {
      changes[key] = payload[key];
    }
  }
  return changes;
}

function normalizePayload(form) {
  const payload = { ...form };
  payload.materials = normalizeMaterialRows(form.materials).map((item, index) => ({
    position: index + 1,
    kit: item.kit || null,
    dynamic: item.dynamic || null,
    material: item.material || null,
    quantity: valueForPayload(item.quantity),
  }));
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

function selectedMaterialRow(form, type, id) {
  return (form.materials || []).find((item) => item[type] && String(item[type]) === String(id));
}

function selectedMaterialQuantity(form, type, id) {
  return selectedMaterialRow(form, type, id)?.quantity ?? "";
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
    regions: [],
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
  const [isReopenModalOpen, setIsReopenModalOpen] = useState(false);
  const [reopenReason, setReopenReason] = useState("");
  const [message, setMessage] = useState("");
  const [publicLinkMessage, setPublicLinkMessage] = useState("");
  const [availableDates, setAvailableDates] = useState([]);
  const [availableDatesLoading, setAvailableDatesLoading] = useState(false);
  const [pendingCount, setPendingCount] = useState(0);
  const [scheduledShifts, setScheduledShifts] = useState(null);
  const [designatedSearch, setDesignatedSearch] = useState("");
  const { user } = useAuth();

  const hasMaxAccess = user?.role === "ADMIN" || user?.role === "MANAGER";
  const canUseRequestShortcuts = hasMaxAccess || user?.role === "SUPERVISOR";
  const canDelete = hasMaxAccess;
  const canChangeStatus = hasMaxAccess;
  const canManageRequests = hasMaxAccess;

  const fetchPendingCount = () => {
    if (canManageRequests) {
      api("/agendas/?status=PENDING&source=requests&page_size=1")
        .then((data) => {
          const count = data.count || 0;
          setPendingCount(count);
          window.dispatchEvent(new CustomEvent("agenda-requests:changed", { detail: { count } }));
        })
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
      api("/regions/?page_size=200"),
      api("/neighborhoods/?page_size=500"),
      api("/kits/?page_size=1000"),
      api("/materials/?page_size=1000"),
      api("/dynamics/?page_size=1000"),
    ]).then(([vehicles, teams, chiefs, agents, supports, actionTypes, municipalities, regions, neighborhoods, kits, materials, dynamics]) => {
      setLookups({
        vehicles: vehicles.results || vehicles,
        teams: teams.results || teams,
        chiefs: chiefs.results || chiefs,
        agents: agents.results || agents,
        supports: supports.results || supports,
        actionTypes: actionTypes.results || actionTypes,
        municipalities: municipalities.results || municipalities,
        regions: regions.results || regions,
        neighborhoods: neighborhoods.results || neighborhoods,
        kits: kits.results || kits,
        materials: materials.results || materials,
        dynamics: dynamics.results || dynamics,
      });
    });
  }, [user]);

  useEffect(loadAgendas, [filters]);

  useEffect(() => {
    if (form.date) {
      api(`/shift-schedules/?date=${form.date}&page_size=1000`)
        .then((data) => setScheduledShifts(data.results || data))
        .catch(() => setScheduledShifts(null));
    } else {
      setScheduledShifts(null);
    }
  }, [form.date]);

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
  const activeUserOptions = useMemo(
    () => (users.length ? users : [user]).filter((option) => option && option.is_active).sort((left, right) => (left.full_name || "").localeCompare(right.full_name || "")),
    [users, user],
  );


  const update = (field, value) => setForm((current) => ({ ...current, [field]: value }));

  const clearOperationalComposition = () => ({
    team_ref: "",
    team_name: "",
    chief_ref: "",
    chief_name: "",
    team_phone: "",
    agents_ref: [],
    agents: "",
    support_1_ref: "",
    support_1: "",
    support_2_ref: "",
    support_2: "",
  });

  const clearDesignatedParticipants = () => ({ designated_users: [] });

  const handleServiceOrderModeChange = (value) => {
    const nextMode = value || "TEAM";
    setMessage("");
    setForm((current) => {
      if (nextMode === current.service_order_mode) {
        return current;
      }

      if (nextMode === "DESIGNATED") {
        const hasOperationalData = Boolean(
          current.team_ref || current.team_name || current.chief_ref || current.chief_name || current.team_phone || (current.agents_ref || []).length || current.agents || current.support_1_ref || current.support_1 || current.support_2_ref || current.support_2,
        );
        if (hasOperationalData && !window.confirm("Ao mudar para Participantes selecionados, a composi??o da equipe operacional ser? removida. Deseja continuar?")) {
          return current;
        }
        return { ...current, service_order_mode: nextMode, ...clearOperationalComposition() };
      }

      if ((current.designated_users || []).length && !window.confirm("Ao voltar para Equipe operacional, os participantes selecionados ser?o removidos. Deseja continuar?")) {
        return current;
      }
      return { ...current, service_order_mode: nextMode, ...clearDesignatedParticipants() };
    });
  };


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

  const toggleAgendaMaterial = (type, option, checked) => {
    setForm((current) => {
      const rows = normalizeMaterialRows(current.materials);
      const nextRows = checked
        ? [
            ...rows,
            {
              position: rows.length + 1,
              kit: type === "kit" ? option.id : null,
              kit_name: type === "kit" ? option.name : "",
              dynamic: type === "dynamic" ? option.id : null,
              dynamic_name: type === "dynamic" ? option.name : "",
              material: type === "material" ? option.id : null,
              material_name: type === "material" ? option.name : "",
              quantity: "",
            },
          ]
        : rows.filter((item) => String(item[type]) !== String(option.id));
      return { ...current, materials: nextRows };
    });
  };

  const updateAgendaMaterialQuantity = (type, id, quantity) => {
    setForm((current) => ({
      ...current,
      materials: normalizeMaterialRows(current.materials).map((item) => (
        String(item[type]) === String(id) ? { ...item, quantity } : item
      )),
    }));
  };

  const kitDetailsMap = {
    "PALESTRA": ["Notebook", "Cabo HDMI", "Data show (projetor)", "Microfone", "Caixa de som", "Pen drive com apresentação", "Totem Ball pequeno"],
    "CIRCUITO": ["Óculos simulador de embriaguez", "Cones pequenos", "03 cones grandes", "Baldinho", "Bolinha", "Torre de copos ou cubos", "04 metros de fita zebrada", "03 bichinhos sonoros"],
    "INFANTIL": ["01 carrinho elétrico", "02 carrinhos pedal", "02 motos elétricas grandes", "01 moto elétrica pequena", "Pista de lona", "Placas de trânsito", "Coletes infantis", "Chapéu de motorista", "CNH infantil educativa", "CRLV infantil educativo"],
    "LÚDICO": ["Fantasia do Soprinho", "Fantasia do Homem-Balão (necessita de reforma/manutenção)"],
    "GOL": ["Baliza inflável", "Óculos simulador", "Bola"],
    "BLITZ": ["Barraca com laterais", "Mesa", "02 cadeiras", "Totem Ball grande", "06 cones grandes"],
  };

  const getKitDetails = (name) => {
    const upper = (name || "").toUpperCase();
    for (const [key, items] of Object.entries(kitDetailsMap)) {
      if (upper.includes(key)) return items.join(" • ");
    }
    return "";
  };

  const filteredKits = lookups.kits.filter((kit) => {
    const upper = (kit.name || "").toUpperCase();
    if (!Object.keys(kitDetailsMap).some((key) => upper.includes(key))) {
      return false;
    }

    const ranges = normalizeAgeRanges(form.age_ranges);
    const isKids = hasAnyAgeRange(ranges, lowerAgeRangeOptions);
    const isTeens = hasAnyAgeRange(ranges, teenAgeRangeOptions);
    const isAdults = hasAnyAgeRange(ranges, adultAgeRangeOptions);
    const is14Plus = isTeens || isAdults;
    const isInfantilKit = upper.includes("CIRCUITO INFANTIL") || upper.includes("PALESTRA INFANTIL");
    const isJovensAdultosKit = upper.includes("PALESTRA JOVENS E ADULTOS") || upper.includes("CIRCUITO ÓCULOS");
    const isEmpresaKit = upper.includes("PALESTRA EMPRESA");

    if (ranges.length > 0) {
      if (isInfantilKit && !isKids) return false;
      if (isJovensAdultosKit && !is14Plus) return false;
      if (isEmpresaKit && !isAdults) return false;
    } else {
      if (isEmpresaKit && form.action_type !== "Palestra Empresa") return false;
    }

    return true;
  });

  const allowedMaterials = [
    "VENTAROLAS",
    "ADESIVOS",
    "FOLDERS",
    "REVISTINHAS EDUCATIVAS",
  ];

  const distributionKits = lookups.kits.filter((kit) => {
    const upper = (kit.name || "").toUpperCase();
    return allowedMaterials.some((allowed) => upper.includes(allowed));
  });

  const renderMaterialChecklist = (title, type, options) => (
    <div className="material-checklist">
      <h4>{title}</h4>
      <div className="material-checklist-list">
        {options.length ? options.map((item) => {
          const checked = Boolean(selectedMaterialRow(form, type, item.id));
          const details = type === "kit" ? getKitDetails(item.name) : "";
          return (
            <div className="material-checklist-row" key={`${type}-${item.id}`} style={{ alignItems: "flex-start", padding: "8px 0" }}>
              <label className="checkbox" style={{ alignItems: "flex-start", flex: 1 }}>
                <input
                  type="checkbox"
                  checked={checked}
                  onChange={(event) => toggleAgendaMaterial(type, item, event.target.checked)}
                  style={{ marginTop: "4px" }}
                />
                <div style={{ display: "flex", flexDirection: "column", gap: "2px" }}>
                  <span style={{ fontWeight: checked ? "600" : "normal" }}>{item.name}</span>
                  {details && (
                    <span style={{ fontSize: "11px", color: "var(--text-soft)", lineHeight: "1.3" }}>
                      • {details}
                    </span>
                  )}
                </div>
              </label>
              <input
                type="number"
                min="0"
                placeholder="Qtd"
                value={selectedMaterialQuantity(form, type, item.id)}
                onChange={(event) => updateAgendaMaterialQuantity(type, item.id, event.target.value)}
                disabled={!checked}
                style={{ width: "60px", padding: "4px 8px" }}
              />
            </div>
          );
        }) : <div className="empty-selection">Nenhum item cadastrado.</div>}
      </div>
    </div>
  );

  const belongsToTeam = (item, teamId, teamName) => {
    if (!teamId && !teamName) return true;
    return String(item.team || "") === String(teamId || "") || String(item.team_name || "").toUpperCase() === String(teamName || "").toUpperCase();
  };

  const isSupportRole = (item) => String(item.role || "").toUpperCase().includes("APOIO");

  const staffLabel = (item) => [item.name, item.role, item.address].filter(Boolean).join(" - ");

  const selectedTeam = lookups.teams.find((team) => String(team.id) === String(form.team_ref));
  const selectedTeamName = selectedTeam?.name || form.team_name;

  const availableTeams = useMemo(() => {
    if (scheduledShifts && form.date) {
      const ids = scheduledShifts.map((s) => String(s.team));
      return lookups.teams.filter((t) => ids.includes(String(t.id)));
    }
    return lookups.teams;
  }, [lookups.teams, scheduledShifts, form.date]);

  const selectedShift = useMemo(() => {
    return scheduledShifts?.find((s) => String(s.team) === String(form.team_ref));
  }, [scheduledShifts, form.team_ref]);

  const teamChiefs = useMemo(() => {
    if (selectedShift && selectedShift.members) {
      return selectedShift.members.chiefs.filter(m => !m.is_absent);
    }
    return lookups.chiefs.filter((chief) => belongsToTeam(chief, form.team_ref, selectedTeamName));
  }, [lookups.chiefs, form.team_ref, selectedTeamName, selectedShift]);

  const allAgents = useMemo(() => {
    let busyInOtherShifts = new Set();
    let currentShiftAbsents = new Set();
    if (scheduledShifts) {
      scheduledShifts.forEach(shift => {
        const isCurrentTeam = String(shift.team) === String(form.team_ref);
        if (shift.members && shift.members.agents) {
          shift.members.agents.forEach(a => {
            if (a.is_absent && isCurrentTeam) currentShiftAbsents.add(String(a.id));
            if (!a.is_absent && !isCurrentTeam) busyInOtherShifts.add(String(a.id));
          });
        }
      });
    }
    return lookups.agents.filter(agent => {
      if (isSupportRole(agent)) return false;
      
      const isHistoric = (form.agents_ref || []).map(String).includes(String(agent.id));
      if (!isHistoric && !belongsToTeam(agent, form.team_ref, selectedTeamName)) return false;
      
      const idStr = String(agent.id);
      return !busyInOtherShifts.has(idStr) && !currentShiftAbsents.has(idStr);
    });
  }, [lookups.agents, scheduledShifts, form.team_ref, selectedTeamName, form.agents_ref]);

  const teamAgents = useMemo(() => {
    if (selectedShift && selectedShift.members) {
       return selectedShift.members.agents.filter(m => !m.is_absent);
    }
    return lookups.agents.filter((agent) => belongsToTeam(agent, form.team_ref, selectedTeamName) && !isSupportRole(agent));
  }, [lookups.agents, form.team_ref, selectedTeamName, selectedShift]);

  const teamSupports = useMemo(() => {
    if (selectedShift && selectedShift.members) {
       return selectedShift.members.supports.filter(m => !m.is_absent);
    }
    return lookups.supports.filter((support) => belongsToTeam(support, form.team_ref, selectedTeamName));
  }, [lookups.supports, form.team_ref, selectedTeamName, selectedShift]);

  const supportOptions = useMemo(() => {
    let busyInOtherShifts = new Set();
    let currentShiftAbsents = new Set();
    if (scheduledShifts) {
      scheduledShifts.forEach(shift => {
        const isCurrentTeam = String(shift.team) === String(form.team_ref);
        if (shift.members && shift.members.supports) {
          shift.members.supports.forEach(a => {
            if (a.is_absent && isCurrentTeam) currentShiftAbsents.add(String(a.id));
            if (!a.is_absent && !isCurrentTeam) busyInOtherShifts.add(String(a.id));
          });
        }
      });
    }
    return lookups.supports.filter(support => {
      const isHistoric = String(support.id) === String(form.support_1_ref) || String(support.id) === String(form.support_2_ref);
      if (!isHistoric && !belongsToTeam(support, form.team_ref, selectedTeamName)) return false;
      
      const idStr = String(support.id);
      return !busyInOtherShifts.has(idStr) && !currentShiftAbsents.has(idStr);
    });
  }, [lookups.supports, scheduledShifts, form.team_ref, selectedTeamName, form.support_1_ref, form.support_2_ref]);

  const selectedAgentIds = (form.agents_ref || []).map(String);
  const selectedAgents = selectedAgentIds
    .map((id) => lookups.agents.find((agent) => String(agent.id) === id))
    .filter(Boolean);
  const availableAgents = allAgents.filter((agent) => !selectedAgentIds.includes(String(agent.id)));
  const selectedDesignatedIds = (form.designated_users || []).map(String);
  const selectedDesignatedUsers = selectedDesignatedIds
    .map((id) => activeUserOptions.find((option) => String(option.id) === id) || users.find((option) => String(option.id) === id))
    .filter(Boolean);
  const designatedCandidates = activeUserOptions.filter((option) => {
    const search = designatedSearch.trim().toLowerCase();
    if (!search) return true;
    return [option.full_name, option.role, option.sector_name].filter(Boolean).some((value) => String(value).toLowerCase().includes(search));
  });

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

  const toggleDesignatedUser = (value) => {
    const id = String(value);
    setForm((current) => {
      const currentIds = (current.designated_users || []).map(String);
      const nextIds = currentIds.includes(id)
        ? currentIds.filter((item) => item !== id)
        : [...currentIds, id];
      return { ...current, designated_users: nextIds };
    });
  };

  const removeDesignatedUser = (value) => {
    const id = String(value);
    setForm((current) => ({
      ...current,
      designated_users: (current.designated_users || []).map(String).filter((item) => item !== id),
    }));
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

    const isStreetAction =
      String(form.action_type_ref) === STREET_ACTION_ID ||
      String(form.requester_entity_type) === STREET_ACTION_ID;

    const normalizedStartTime = normalizeTime(form.start_time);
    if (!normalizedStartTime && form.start_time) {
      setMessage("Informe um horário válido no formato HH:mm.");
      return;
    }

    let normalizedEndTime = form.end_time;
    if (normalizedStartTime) {
      if (isStreetAction) {
        normalizedEndTime = addHoursToTime(normalizedStartTime, 4);
        if (!normalizedEndTime) {
          setMessage("Não foi possível calcular o horário final. Verifique o horário inicial.");
          return;
        }
      } else {
        if (form.end_time) {
          normalizedEndTime = normalizeTime(form.end_time);
          if (!normalizedEndTime) {
            setMessage("Informe um horário válido no formato HH:mm para a hora final.");
            return;
          }
        }
      }
    }

    const payloadForm = {
      ...form,
      start_time: normalizedStartTime || form.start_time,
      end_time: normalizedEndTime || form.end_time,
    };

    const payload = normalizePayload({ ...payloadForm, lookupVehicles: lookups.vehicles });
    try {
      if (editing) {
        const original = agendas.find((a) => String(a.id) === String(editing));
        const diffPayload = getDiffPayload(payload, original);
        await api(`/agendas/${editing}/`, { method: "PATCH", body: JSON.stringify(diffPayload) });
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
    setDesignatedSearch("");
    setIsModalOpen(true);
    let newForm = agendaFields.reduce((values, field) => {
      const value = field === "materials" ? normalizeMaterialRows(agenda.materials) : agenda[field] ?? "";
      values[field] = field === "responsible"
        ? (user?.id || value)
        : field === "service_order_mode" ? (value || "TEAM")
        : field === "designated_users" ? (Array.isArray(value) ? value.map(String) : [])
        : field.endsWith("_time") && value ? value.slice(0, 5) : value;
      return values;
    }, { responsible: user?.id || "" });

    if (newForm.materials.length === 0) {
      let kitToSelect = null;
      if (newForm.action_type === "Palestra Empresa") {
        kitToSelect = lookups.kits.find(k => (k.name || "").toUpperCase() === "PALESTRA EMPRESA");
      } else if (newForm.action_type === "Palestra Escola") {
        const ranges = normalizeAgeRanges(newForm.age_ranges);
        const hasKids = hasAnyAgeRange(ranges, lowerAgeRangeOptions);
        const hasAdults = hasAnyAgeRange(ranges, teenAgeRangeOptions) || hasAnyAgeRange(ranges, adultAgeRangeOptions);
        
        if (hasKids && !hasAdults) {
          kitToSelect = lookups.kits.find(k => (k.name || "").toUpperCase() === "PALESTRA INFANTIL");
        } else if (hasAdults && !hasKids) {
          kitToSelect = lookups.kits.find(k => (k.name || "").toUpperCase() === "PALESTRA JOVENS E ADULTOS");
        } else if (hasKids && hasAdults) {
          kitToSelect = lookups.kits.find(k => (k.name || "").toUpperCase() === "PALESTRA JOVENS E ADULTOS");
        }
      }
      if (kitToSelect) {
        newForm.materials = [{ kit: kitToSelect.id, kit_name: kitToSelect.name, quantity: "1", position: 1 }];
      }
    }
    setForm(newForm);
  };

  const reviewAndSchedule = (agenda) => {
    edit(agenda);
    setReviewStep("summary");
    setMessage("");
  };

  const editServiceOrder = (agenda) => {
    edit(agenda);
    setReviewStep("schedule");
    setMessage("");
  };

  const openNew = () => {
    if (!canManageRequests) return;
    setEditing(null);
    setDesignatedSearch("");
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
      const isDesignatedMode = (agenda.service_order_mode || "TEAM") === "DESIGNATED";
      const hasTeam = agenda.team_ref || agenda.team_name || agenda.sector;
      const hasChief = agenda.chief_ref || agenda.chief_name;
      const hasAgents = (agenda.agents_ref || []).length || agenda.agents;
      const hasDesignatedUsers = (agenda.designated_users || []).length;
      if ((!isDesignatedMode && (!hasTeam || !hasChief || !hasAgents)) || (isDesignatedMode && !hasDesignatedUsers)) {
        reviewAndSchedule(agenda);
        setMessage(isDesignatedMode ? "Antes de aprovar, selecione ao menos um participante." : "Antes de aprovar, informe equipe, chefe e agentes escalados.");
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

  const handleReopen = async () => {
    try {
      const response = await api(`/agendas/${editing}/reopen/`, {
        method: "POST",
        body: JSON.stringify({ reason: reopenReason }),
      });
      setMessage("Solicitação reaberta com sucesso.");
      setIsReopenModalOpen(false);
      setReopenReason("");
      
      const newStatus = response.status || "PENDING";
      setForm({ ...form, status: newStatus });
      setAgendas(agendas.map(a => String(a.id) === String(editing) ? { ...a, status: newStatus } : a));
      
      loadAgendas();
    } catch (err) {
      setMessage(err.message);
    }
  };

  const handleDelete = async (agenda) => {
    if (!canDelete) {
      setMessage("Seu perfil não tem permissão para excluir solicitações.");
      return;
    }
    if (!window.confirm("Tem certeza que deseja excluir esta solicitação permanentemente?")) return;
    try {
      await api(`/agendas/${agenda.id}/`, { method: "DELETE" });
      setMessage("Solicitação excluída com sucesso.");
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
      if (!hasSchedule || !hasResponsible || !hasLocation || !hasTeam || !hasChief || !hasAgents) {
        setMessage("Para aprovar, informe data, horário, responsável, local, equipe, chefe e agentes.");
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
      const payload = normalizePayload({ ...nextForm, lookupVehicles: lookups.vehicles });
      const original = agendas.find((a) => String(a.id) === String(editing));
      const diffPayload = getDiffPayload(payload, original);
      if (nextForm.status) diffPayload.status = nextForm.status; // Ensure status is sent
      if (nextForm.cancel_reason !== undefined) diffPayload.cancel_reason = nextForm.cancel_reason;
      await api(`/agendas/${editing}/`, { method: "PATCH", body: JSON.stringify(diffPayload) });
      setForm(emptyForm);
      setEditing(null);
      setIsModalOpen(false);
      setMessage(status === "APPROVED" ? "Solicitação aprovada e escalada." : status === "CANCELLED" ? "Solicitação recusada." : "Solicitação mantida como pendente.");
      loadAgendas();
    } catch (err) {
      setMessage(err.message);
    }
  };

  const saveWithoutEmail = async () => {
    if (!editing) return;
    if (!canManageRequests) {
      setMessage("Seu perfil pode visualizar solicitações, mas não aprovar ou recusar.");
      return;
    }
    setMessage("");
    try {
      const payload = normalizePayload({ ...form, lookupVehicles: lookups.vehicles });
      const original = agendas.find((a) => String(a.id) === String(editing));
      const diffPayload = getDiffPayload(payload, original);
      await api(`/agendas/${editing}/?skip_email=true`, { method: "PATCH", body: JSON.stringify(diffPayload) });
      setForm(emptyForm);
      setEditing(null);
      setIsModalOpen(false);
      setMessage("OS atualizada com sucesso (sem notificação ao solicitante).");
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
        if (data.url && /^https?:\/\//i.test(data.url)) {
          window.open(data.url, "_blank", "noreferrer");
        }
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
            <p style={{ margin: 0 }}>Avalie solicitações recebidas pelo formulário público e faça a ordem de serviço.</p>
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
                <th>Ordem de Serviço</th>
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
                  <td>{agenda.start_time?.slice(0, 5) || "-"}</td>
                  <td>{agenda.city || "-"}</td>
                  <td>{agenda.quantity || "-"}</td>
                  <td>
                    <span className={`badge ${statusClass[agenda.status]}`}>{statusLabel[agenda.status]}</span>
                    {agenda.satisfaction_survey_answered_at && (
                      <span className="badge warning" style={{ marginLeft: "8px", display: "inline-flex", alignItems: "center", gap: "4px" }} title="Avaliação respondida">
                        <Star size={12} fill="currentColor" /> {agenda.satisfaction_rating ? agenda.satisfaction_rating.toFixed(1) : "Resp."}
                      </span>
                    )}
                  </td>
                  <td className="row-actions" style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
                    <button className="secondary" onClick={() => reviewAndSchedule(agenda)}>
                      <ClipboardCheck size={16} /> Avaliar solicitação
                    </button>
                    {canManageRequests && agenda.status === "APPROVED" && (
                      <button className="secondary" onClick={() => editServiceOrder(agenda)}>
                        <Edit size={16} /> Editar OS
                      </button>
                    )}
                    {canDelete && (
                      <button
                        className="secondary"
                        style={{ color: "#d9534f", borderColor: "#d9534f" }}
                        onClick={() => handleDelete(agenda)}
                        title={agenda.can_delete === false ? agenda.delete_block_reason || "Não é possível excluir" : "Excluir"}
                        disabled={agenda.can_delete === false}
                      >
                        <Trash2 size={16} />
                      </button>
                    )}
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
              <h2>{editing ? (reviewStep === "form" ? "Editar solicitação" : "Avaliar solicitação") : "Nova agenda"}</h2>
              <button type="button" className="icon-button" onClick={() => setIsModalOpen(false)} aria-label="Fechar">×</button>
            </div>
            {reviewStep !== "form" && (
              <>
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
              <span><b>Participantes</b>{form.participant_range || form.quantity || "-"}</span>
              <span><b>Faixa etária</b>{form.age_ranges || "-"}</span>
              <span><b>Endereço</b>{[form.address, form.neighborhood, form.city, form.state].filter(Boolean).join(", ") || "-"}</span>
              <span><b>Acessibilidade</b>{form.accessibility_access ? "Acesso: " + form.accessibility_access : "Rampa: " + (form.has_ramps || "-") + " · Elevador: " + (form.has_elevators || "-")} · Banheiro: {form.has_accessible_bathrooms || "-"}</span>
              <span><b>Recursos</b>{form.media_equipment || "-"}</span>
              <span className="full"><b>Autorização de imagem</b>{form.image_authorization || "-"}</span>
              {form.notes && <span className="full"><b>Observações</b>{form.notes}</span>}
              {form.status === "CANCELLED" && (
                <span className="full" style={{ color: "var(--pico-del-color)" }}>
                  <b>Motivo do cancelamento</b>{form.cancel_reason || "-"}
                </span>
              )}
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

            </>
            )}
            {editing && reviewStep === "summary" && message && <div className="alert">{message}</div>}
            {editing && reviewStep === "summary" && canManageRequests && (
              <div className="review-actions">
                {form.status === "CANCELLED" ? (
                  <button type="button" className="approve-action" onClick={() => setIsReopenModalOpen(true)}>
                    Reabrir solicitação
                  </button>
                ) : (
                  <>
                    <button type="button" className="approve-action" onClick={() => setReviewStep("schedule")}>
                      <CheckCircle2 size={18} /> Aprovar
                    </button>
                    <button type="button" className="secondary" onClick={() => setReviewStep("form")}>
                      <Edit size={18} /> Editar solicitação
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
                  </>
                )}
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
                  <h3>Ordem de serviço</h3>
                  {(!agendas.find((a) => String(a.id) === String(editing))?.description) && (
                    <label className="field-label" style={{ marginBottom: "16px" }}>
                      <span style={{ color: "var(--color-danger)", fontWeight: "bold" }}>Descrição ausente (Preenchimento obrigatório)</span>
                      <textarea 
                        rows="3" 
                        value={form.description || ""} 
                        onChange={(e) => update("description", e.target.value)} 
                        placeholder="Esta agenda não possui descrição. Por favor, informe uma descrição detalhada para prosseguir com a aprovação." 
                        required 
                      />
                    </label>
                  )}
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
                      <span>Modo da Ordem de Servi?o</span>
                      <select value={form.service_order_mode || "TEAM"} onChange={(e) => handleServiceOrderModeChange(e.target.value)}>
                        <option value="TEAM">Equipe operacional</option>
                        <option value="DESIGNATED">Participantes selecionados</option>
                      </select>
                    </label>
                    <label className="field-label">
                      <span>Viatura</span>
                      <select value={form.vehicle_ref || ""} onChange={(e) => selectLookup("vehicle_ref", "vehicle", lookups.vehicles, e.target.value)}>
                        <option value="">Sem viatura</option>
                        {lookups.vehicles.map((item) => <option key={item.id} value={item.id} disabled={[String(form.vehicle_2_ref), String(form.vehicle_3_ref)].includes(String(item.id))}>{item.name}</option>)}
                      </select>
                    </label>
                  </div>
                  <div className="compact-grid">
                    <label className="field-label">
                      <span>Viatura 2</span>
                      <select value={form.vehicle_2_ref || ""} onChange={(e) => update("vehicle_2_ref", e.target.value)}>
                        <option value="">Sem segunda viatura</option>
                        {lookups.vehicles.map((item) => <option key={item.id} value={item.id} disabled={[String(form.vehicle_ref), String(form.vehicle_3_ref)].includes(String(item.id))}>{item.name}</option>)}
                      </select>
                    </label>
                    <label className="field-label">
                      <span>Viatura 3</span>
                      <select value={form.vehicle_3_ref || ""} onChange={(e) => update("vehicle_3_ref", e.target.value)}>
                        <option value="">Sem terceira viatura</option>
                        {lookups.vehicles.map((item) => <option key={item.id} value={item.id} disabled={[String(form.vehicle_ref), String(form.vehicle_2_ref)].includes(String(item.id))}>{item.name}</option>)}
                      </select>
                    </label>
                  </div>
                  {(form.service_order_mode || "TEAM") === "TEAM" ? (
                    <>
                      <div className="compact-grid">
                        <label className="field-label">
                          <span>Equipe</span>
                          <select value={form.team_ref || ""} onChange={(e) => handleTeamChange(e.target.value)} required>
                            <option value="">Selecione a equipe</option>
                            {availableTeams.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
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
                            <option value="">{availableAgents.length ? "Adicionar outro agente" : "Sem agentes dispon?veis para adicionar"}</option>
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
                    </>
                  ) : (
                    <div className="field-label" style={{ gap: "12px" }}>
                      <span>Participantes selecionados</span>
                      <input value={designatedSearch} onChange={(e) => setDesignatedSearch(e.target.value)} placeholder="Buscar por nome, fun??o ou equipe" />
                      <div className="alert" style={{ margin: 0 }}>Selecionados: {selectedDesignatedUsers.length}</div>
                      <div className="agent-select-list">
                        {selectedDesignatedUsers.length ? selectedDesignatedUsers.map((member) => (
                          <div className="agent-select-row" key={member.id}>
                            <div>
                              <strong>{member.full_name}</strong>
                              <div style={{ fontSize: "12px", color: "var(--text-soft)" }}>{[member.role, member.sector_name].filter(Boolean).join(" - ")}</div>
                            </div>
                            <button type="button" className="icon-soft danger" onClick={() => removeDesignatedUser(member.id)} aria-label={`Remover ${member.full_name}`}>
                              <XCircle size={16} />
                            </button>
                          </div>
                        )) : <div className="empty-selection">Nenhum participante selecionado.</div>}
                      </div>
                      <div className="material-checklist-list" style={{ maxHeight: "220px" }}>
                        {designatedCandidates.length ? designatedCandidates.map((member) => {
                          const checked = selectedDesignatedIds.includes(String(member.id));
                          return (
                            <label className="checkbox" key={member.id} style={{ justifyContent: "space-between", padding: "8px 0", borderBottom: "1px solid rgba(11, 37, 89, 0.08)" }}>
                              <div style={{ display: "flex", flexDirection: "column", gap: "2px" }}>
                                <span>{member.full_name}</span>
                                <span style={{ fontSize: "12px", color: "var(--text-soft)" }}>{[member.role, member.sector_name].filter(Boolean).join(" - ")}</span>
                              </div>
                              <input type="checkbox" checked={checked} onChange={() => toggleDesignatedUser(member.id)} />
                            </label>
                          );
                        }) : <div className="empty-selection">Nenhum usu?rio ativo encontrado.</div>}
                      </div>
                    </div>
                  )}
                  <div className="material-selection-grid">
                    {renderMaterialChecklist("Dinâmica", "dynamic", lookups.dynamics || [])}
                    {renderMaterialChecklist("Material para distribuição", "kit", lookups.kits || [])}
                    {renderMaterialChecklist("Material de Apoio", "material", lookups.materials || [])}
                  </div>
                </div>
                {message && <div className="alert">{message}</div>}
                <div className="review-actions">
                  <button type="button" className="secondary" onClick={() => setReviewStep("summary")}>Voltar</button>
                  <button type="button" className="secondary" onClick={checkAvailableDates}>Verificar datas disponíveis</button>
                  <button type="button" className="secondary" onClick={saveWithoutEmail} style={{ display: "inline-flex", alignItems: "center", gap: "6px" }}><Save size={16} /> Salvar sem notificar</button>
                  <button type="submit" className="approve-action"><CheckCircle2 size={18} /> Confirmar aprovação</button>
                </div>
              </form>
            )}
            {reviewStep === "form" && (
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
            <h3>{!editing ? "Equipe e local" : "Local"}</h3>
            {!editing && (
              <>
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
            </>
            )}
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
            {!editing && (
            <select value={form.sector} onChange={(e) => update("sector", e.target.value)} required>
              <option value="">Equipe</option>
              {sectors.map((sector) => <option key={sector.id} value={sector.id}>{sector.name}</option>)}
            </select>
            )}
          </div>

          <div className="form-section">
            <h3>Responsável e público</h3>
            {!editing && (
            <select value={form.responsible} onChange={(e) => update("responsible", e.target.value)} required>
              <option value="">Responsável interno</option>
              {responsibleOptions.map((option) => <option key={option.id} value={option.id}>{option.full_name}</option>)}
            </select>
            )}
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
            {(!form.requester_entity_type || form.requester_entity_type !== STREET_ACTION_ID) ? (
              <input placeholder="Faixa de participantes" value={form.participant_range} onChange={(e) => update("participant_range", e.target.value)} />
            ) : (
              <div style={{ marginTop: "12px", marginBottom: "12px", border: "1px solid var(--border)", padding: "12px", borderRadius: "8px" }}>
                <strong>Tipos de Ação (Locais)</strong>
                <p style={{ fontSize: "12px", color: "var(--text-soft)", marginBottom: "8px" }}>
                  Adicione os locais que serão visitados. O público será preenchido pelo Chefe de Equipe no relatório.
                </p>
                <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                  {(form.street_action_details || []).map((detail, idx) => (
                    <div key={idx} style={{ display: "flex", gap: "8px", alignItems: "center" }}>
                      <select
                        style={{ flex: 1 }}
                        value={detail.type}
                        onChange={(e) => {
                          const newDetails = [...(form.street_action_details || [])];
                          newDetails[idx].type = e.target.value;
                          update("street_action_details", newDetails);
                        }}
                        required
                      >
                        <option value="">Selecione o tipo</option>
                        {STREET_ACTION_TYPE_OPTIONS.map((option) => (
                          <option key={option} value={option}>{option}</option>
                        ))}
                      </select>
                      <button
                        type="button"
                        className="danger icon-only"
                        title="Remover"
                        onClick={() => {
                          const newDetails = (form.street_action_details || []).filter((_, i) => i !== idx);
                          update("street_action_details", newDetails);
                        }}
                      >
                        <Trash2 size={16} />
                      </button>
                    </div>
                  ))}
                  <button
                    type="button"
                    className="secondary"
                    onClick={() => update("street_action_details", [...(form.street_action_details || []), { type: "", public: "" }])}
                    style={{ alignSelf: "flex-start" }}
                  >
                    <Plus size={16} /> Adicionar Local
                  </button>
                </div>
              </div>
            )}
            <input placeholder="Acesso por rampa/elevador" value={form.accessibility_access} onChange={(e) => update("accessibility_access", e.target.value)} />
            <div className="compact-grid three-cols">
              <input placeholder="Rampa" value={form.has_ramps} onChange={(e) => update("has_ramps", e.target.value)} />
              <input placeholder="Elevador" value={form.has_elevators} onChange={(e) => update("has_elevators", e.target.value)} />
              <input placeholder="Banheiro adaptado" value={form.has_accessible_bathrooms} onChange={(e) => update("has_accessible_bathrooms", e.target.value)} />
            </div>
            <input placeholder="Equipamentos disponíveis" value={form.media_equipment} onChange={(e) => update("media_equipment", e.target.value)} />
            <textarea placeholder="Autorização de imagem" value={form.image_authorization} onChange={(e) => update("image_authorization", e.target.value)} />
            <textarea placeholder="Observação" value={form.notes} onChange={(e) => update("notes", e.target.value)} />
          </div>

          {!editing && (
          <div className="form-section">
            <h3>Kits e materiais</h3>
            {Array.from({ length: 7 }, (_, index) => {
              const number = index + 1;
              return (
                <div className="kit-row" key={number}>
                  <select value="" onChange={(e) => selectNameByValue(`kit_${number}`, filteredKits, e.target.value)}>
                    <option value="">{form[`kit_${number}`] || `Kit ${number}`}</option>
                    {filteredKits.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
                  </select>
                  <input type="number" min="0" placeholder={`QTD ${number}`} value={form[`kit_${number}_quantity`]} onChange={(e) => update(`kit_${number}_quantity`, e.target.value)} />
                  {number < 7 && (
                    <select value="" onChange={(e) => selectNameByValue(`material_${number}`, distributionKits, e.target.value)}>
                      <option value="">{form[`material_${number}`] || `Material ${number}`}</option>
                      {distributionKits.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
                    </select>
                  )}
                </div>
              );
            })}
          </div>
          )}
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
                    <strong>{item.action === "REOPENED" ? "REABERTURA" : item.action}</strong>
                    <span>{item.changed_by_name || "Sistema"} - {new Date(item.created_at).toLocaleString("pt-BR")}</span>
                    {item.action === "REOPENED" ? (
                      <>
                        <small>Status anterior: {statusLabel[item.snapshot?.previous_status] || item.snapshot?.previous_status}</small>
                        <small>Novo status: {statusLabel[item.snapshot?.new_status] || item.snapshot?.new_status}</small>
                        {item.snapshot?.observation && <small>Observação: {item.snapshot.observation}</small>}
                      </>
                    ) : (
                      <>
                        {item.snapshot?.status && <small>Status: {statusLabel[item.snapshot.status] || item.snapshot.status}</small>}
                        {item.snapshot?.cancel_reason && <small>Motivo: {item.snapshot.cancel_reason}</small>}
                      </>
                    )}
                  </div>
                ))
              ) : (
                <p>Nenhum histórico registrado.</p>
              )}
            </div>
          </article>
        </div>
      )}

      {isReopenModalOpen && (
        <div className="modal-backdrop" onClick={() => setIsReopenModalOpen(false)}>
          <article className="modal" onClick={(event) => event.stopPropagation()} style={{ maxWidth: "500px" }}>
            <div className="modal-header">
              <h2>Reabrir solicitação</h2>
              <button type="button" className="icon-button" onClick={() => setIsReopenModalOpen(false)} aria-label="Fechar">×</button>
            </div>
            <form onSubmit={(e) => { e.preventDefault(); handleReopen(); }} className="stack-form" style={{ marginTop: "1rem" }}>
              <label className="field-label">
                <span>Observação (opcional)</span>
                <textarea
                  rows="3"
                  value={reopenReason}
                  onChange={(e) => setReopenReason(e.target.value)}
                  placeholder="Informe o motivo da reabertura..."
                ></textarea>
              </label>
              <div className="review-actions" style={{ justifyContent: "flex-end", marginTop: "1.5rem" }}>
                <button type="button" className="secondary" onClick={() => setIsReopenModalOpen(false)}>
                  Cancelar
                </button>
                <button type="submit" className="approve-action">
                  Reabrir solicitação
                </button>
              </div>
            </form>
          </article>
        </div>
      )}
    </section>
  );
}
