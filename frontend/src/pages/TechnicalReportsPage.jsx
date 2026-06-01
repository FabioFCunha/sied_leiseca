import { Clipboard, MapPin, Plus, Save, Search, Trash2 } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { api } from "../api/client.js";
import { useAuth } from "../context/AuthContext.jsx";
import { formatDateBR } from "../utils/date.js";

import { buildPreview, chiefFromReport, reportName } from "../utils/reportPreview.js";

const emptyAction = {
  agenda: "",
  source_id: "",
  place_action: "",
  type_action: "",
  type_audience: "",
  institution_name: "",
  start_time: "",
  final_hour: "",
  approach: 0,
  tests: 0,
  used_caps: 0,
  available_caps: 0,
  distributed_folders: 0,
  cricris: 0,
  vetarolas: 0,
  used_adhesives: 0,
  sequence_certificates: 0,
  gibis: 0,
  distributed_certificates: 0,
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
  education_pcd: "",
  education_agents: "",
  changes_staff: "",
  breathalyzers: "",
  cars: "",
  changes_general: "",
  contact_received: "",
  occurrence_observation: "",
  lat: "",
  lng: "",
  status: "DRAFT",
  actions: [{ ...emptyAction }],
};

const numberFields = [
  "approach",
  "tests",
  "used_caps",
  "available_caps",
  "distributed_folders",
  "cricris",
  "vetarolas",
  "used_adhesives",
  "sequence_certificates",
  "gibis",
  "distributed_certificates",
];

const fieldLabels = {
  approach: "Abordagens",
  tests: "Testes",
  used_caps: "Bocais usados",
  available_caps: "Bocais disponíveis",
  distributed_folders: "Pastas",
  cricris: "Cricris",
  vetarolas: "Vetarolas",
  used_adhesives: "Adesivos",
  sequence_certificates: "Sequência certificados",
  gibis: "Gibis",
  distributed_certificates: "Certificados",
};

function nullable(value) {
  return value === "" ? null : value;
}

function chiefFromAgenda(agenda) {
  return agenda?.chief_name || agenda?.chief_ref_name || "";
}

function agendaSummary(agenda) {
  if (!agenda) return "";
  return `#${agenda.id} - ${agenda.title} - ${formatDateBR(agenda.date)}`;
}

function joinValues(values, fallback = "") {
  return values.filter(Boolean).join("\n") || fallback;
}

function materialsFromAgenda(agenda) {
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
      const name = item.kit_name || item.material_name;
      if (name) rows.push(`${name}${item.quantity ? ` - ${item.quantity}` : ""}`);
    });
  }
  return rows.join("\n");
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
      agenda.quantity ? `Quantidade prevista: ${agenda.quantity}` : "",
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

function normalizePayload(form) {
  return {
    ...form,
    source: "LOCAL",
    source_id: nullable(form.source_id),
    agenda: nullable(form.agenda),
    management_id: nullable(form.management_id),
    lat: nullable(form.lat),
    lng: nullable(form.lng),
    actions: form.actions.map((action) => ({
      ...action,
      agenda: nullable(action.agenda || form.agenda),
      source_id: nullable(action.source_id),
      ...Object.fromEntries(numberFields.map((field) => [field, Number(action[field] || 0)])),
    })),
  };
}

export default function TechnicalReportsPage() {
  const [agendas, setAgendas] = useState([]);
  const [protocolSearch, setProtocolSearch] = useState("");
  const [form, setForm] = useState(empty);
  const [editing, setEditing] = useState(null);
  const [message, setMessage] = useState("");
  const [locationMessage, setLocationMessage] = useState("");
  const [isGeocoding, setIsGeocoding] = useState(false);
  const { user } = useAuth();
  const isAdmin = user?.role === "ADMIN";

  const selectedAgenda = useMemo(
    () => agendas.find((agenda) => String(agenda.id) === String(form.agenda)),
    [agendas, form.agenda]
  );
  const preview = useMemo(() => buildPreview(form), [form]);

  const load = () => {
    api("/agendas/?page_size=1000&reportable=true").then((data) => setAgendas(data.results || data));
  };

  useEffect(load, []);

  const update = (field, value) => setForm((current) => ({ ...current, [field]: value }));

  const applyAgenda = (agenda) => {
    const details = protocolDetails(agenda);
    setForm((current) => ({
      ...current,
      agenda: agenda.id,
      agenda_title: agenda.title,
      agenda_date: agenda.date,
      agenda_location: agenda.institution_location || agenda.location,
      operation_date: agenda.date || current.operation_date,
      team: agenda.team_name || agenda.team_ref_name || agenda.sector_name || current.team,
      education_pcd: current.education_pcd || details.audience,
      education_agents: current.education_agents || details.agents,
      changes_staff: current.changes_staff || details.notes,
      breathalyzers: current.breathalyzers || details.resources,
      cars: current.cars || joinValues([agenda.vehicle, agenda.vehicle_name]),
      changes_general: current.changes_general || joinValues([
        agenda.image_authorization ? `Autorização de imagem: ${agenda.image_authorization}` : "",
        agenda.has_ramps || agenda.has_elevators || agenda.has_accessible_bathrooms
          ? `Acessibilidade: rampas ${agenda.has_ramps || "-"}, elevadores ${agenda.has_elevators || "-"}, banheiros adaptados ${agenda.has_accessible_bathrooms || "-"}`
          : "",
      ]),
      contact_received: current.contact_received || joinValues([
        agenda.external_responsible,
        agenda.external_responsible_phone,
        agenda.external_email,
      ], current.contact_received),
      occurrence_observation: current.occurrence_observation || agenda.notes || agenda.description || "",
      actions: current.actions.map((action) => ({
        ...action,
        agenda: agenda.id,
        place_action: action.place_action || agenda.institution_location || agenda.location || "",
        institution_name: action.institution_name || agenda.institution_location || "",
        type_action: action.type_action || agenda.action_type || agenda.action_type_ref_name || "",
        type_audience: action.type_audience || agenda.audience || "",
        start_time: action.start_time || agenda.start_time?.slice(0, 5) || "",
        final_hour: action.final_hour || agenda.end_time?.slice(0, 5) || "",
      })),
    }));
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

  const findProtocol = async () => {
    const protocol = protocolSearch.trim();
    if (!protocol) {
      setMessage("Informe o protocolo da solicitação.");
      return;
    }
    setMessage("");
    try {
      const data = await api(`/agendas/?q=${encodeURIComponent(protocol)}&page_size=20&reportable=true`);
      const list = data.results || data;
      const agenda = list.find((item) => String(item.id) === protocol) || list[0];
      if (!agenda) {
        setMessage("Nenhuma solicitação encontrada para esse protocolo.");
        return;
      }
      applyAgenda(agenda);
      const foundLocation = await fillCoordinatesFromAgenda(agenda);
      setMessage(foundLocation ? `Protocolo #${agenda.id} vinculado ao relatório com localização preenchida.` : `Protocolo #${agenda.id} vinculado ao relatório.`);
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

  const addAction = () => {
    setForm((current) => ({
      ...current,
      actions: [...current.actions, { ...emptyAction, agenda: current.agenda }],
    }));
  };

  const removeAction = (index) => {
    setForm((current) => ({
      ...current,
      actions: current.actions.length === 1
        ? [{ ...emptyAction, agenda: current.agenda }]
        : current.actions.filter((_, actionIndex) => actionIndex !== index),
    }));
  };

  const saveReport = async (status) => {
    const nextForm = { ...form, status };
    const saved = editing
      ? await api(`/education-reports/${editing}/`, { method: "PUT", body: JSON.stringify(normalizePayload(nextForm)) })
      : await api("/education-reports/", { method: "POST", body: JSON.stringify(normalizePayload(nextForm)) });
    setEditing(saved.id);
    setForm({ ...saved, actions: saved.actions.length ? saved.actions : [{ ...emptyAction, agenda: saved.agenda }] });
    setProtocolSearch(saved.agenda ? String(saved.agenda) : "");
    load();
  };

  const submit = async (event) => {
    event.preventDefault();
    setMessage("");
    try {
      await saveReport("DRAFT");
      setMessage("Rascunho salvo com sucesso.");
    } catch (err) {
      setMessage(err.message);
    }
  };

  const submitFinal = async () => {
    setMessage("");
    try {
      await saveReport("SUBMITTED");
      setMessage("Relatório enviado com sucesso.");
    } catch (err) {
      setMessage(err.message);
    }
  };

  const edit = (report) => {
    setEditing(report.id);
    setProtocolSearch(report.agenda ? String(report.agenda) : "");
    setForm({ ...report, actions: report.actions.length ? report.actions : [{ ...emptyAction, agenda: report.agenda }] });
    setMessage("");
  };

  const reset = () => {
    setEditing(null);
    setProtocolSearch("");
    setForm({ ...empty, actions: [{ ...emptyAction }] });
    setMessage("");
  };

  const copyPreview = () => {
    navigator.clipboard?.writeText(preview);
    setMessage("Relatório copiado para a área de transferência.");
  };

  return (
    <section className="page two-column report-editor">
      <div className="main-column">
        <div className="page-title">
          <div>
            <h1>Novo Relatório Técnico</h1>
            <p>Busque o protocolo da solicitação, vincule o relatório e registre a execução da equipe.</p>
          </div>
          <button type="button" className="secondary" onClick={reset}><Plus size={18} /> Novo</button>
        </div>

        <form className="table-wrap report-form" onSubmit={submit}>
          <h2>{reportName(form)}</h2>

          <div className="form-section">
            <h3>Protocolo da solicitação</h3>
            <div className="protocol-search">
              <input placeholder="Digite o protocolo" value={protocolSearch} onChange={(event) => setProtocolSearch(event.target.value)} />
              <button type="button" className="secondary" onClick={findProtocol}><Search size={18} /> Buscar</button>
            </div>
            {(selectedAgenda || form.agenda) && (
              <div className="report-context">
                <strong>{selectedAgenda ? agendaSummary(selectedAgenda) : `#${form.agenda} - ${form.agenda_title}`}</strong>
                <span>{form.agenda_location || "Local não informado"}</span>
                <span>Equipe: {form.team || "não informada"}</span>
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
                <input type="date" value={form.operation_date} onChange={(event) => update("operation_date", event.target.value)} required />
              </label>
              <label className="field-label">
                <span>Equipe</span>
                <input value={form.team} onChange={(event) => update("team", event.target.value)} required />
              </label>
            </div>
          </div>

          <div className="form-section">
            <h3>Efetivo e recursos</h3>
            <label className="field-label report-text-box">
              <span>Público e dados da solicitação</span>
              <textarea value={form.education_pcd || ""} onChange={(event) => update("education_pcd", event.target.value)} />
            </label>
            <label className="field-label report-text-box">
              <span>Efetivo escalado</span>
              <textarea value={form.education_agents || ""} onChange={(event) => update("education_agents", event.target.value)} />
            </label>
            <label className="field-label report-text-box">
              <span>Observações do protocolo</span>
              <textarea value={form.changes_staff || ""} onChange={(event) => update("changes_staff", event.target.value)} />
            </label>
            <label className="field-label report-text-box">
              <span>Recursos, kits e materiais</span>
              <textarea value={form.breathalyzers || ""} onChange={(event) => update("breathalyzers", event.target.value)} />
            </label>
            <label className="field-label report-text-box">
              <span>Viaturas</span>
              <textarea value={form.cars || ""} onChange={(event) => update("cars", event.target.value)} />
            </label>
            <label className="field-label report-text-box">
              <span>Complementos e alterações</span>
              <textarea value={form.changes_general || ""} onChange={(event) => update("changes_general", event.target.value)} />
            </label>
          </div>

          <div className="form-section">
            <h3>Ações</h3>
            {form.actions.map((action, index) => (
              <div className="horus-action-card" key={index}>
                <div className="action-card-header">
                  <strong>Ação {index + 1}</strong>
                  <button type="button" className="secondary icon-button" onClick={() => removeAction(index)} aria-label="Remover ação">
                    <Trash2 size={16} />
                  </button>
                </div>
                <div className="compact-grid">
                  <input placeholder="Local da ação" value={action.place_action || ""} onChange={(event) => updateAction(index, "place_action", event.target.value)} />
                  <input placeholder="Tipo da ação" value={action.type_action || ""} onChange={(event) => updateAction(index, "type_action", event.target.value)} />
                </div>
                <div className="compact-grid">
                  <input placeholder="Tipo de público" value={action.type_audience || ""} onChange={(event) => updateAction(index, "type_audience", event.target.value)} />
                  <input placeholder="Instituição" value={action.institution_name || ""} onChange={(event) => updateAction(index, "institution_name", event.target.value)} />
                </div>
                <div className="compact-grid">
                  <input placeholder="Hora inicial" value={action.start_time || ""} onChange={(event) => updateAction(index, "start_time", event.target.value)} />
                  <input placeholder="Hora final" value={action.final_hour || ""} onChange={(event) => updateAction(index, "final_hour", event.target.value)} />
                </div>
                <div className="compact-grid horus-count-grid">
                  {numberFields.map((field) => (
                    <label className="field-label" key={field}>
                      <span>{fieldLabels[field]}</span>
                      <input type="number" min="0" value={action[field] ?? 0} onChange={(event) => updateAction(index, field, event.target.value)} />
                    </label>
                  ))}
                </div>
              </div>
            ))}
            <button type="button" className="secondary" onClick={addAction}><Plus size={18} /> Adicionar ação</button>
          </div>

          <div className="form-section">
            <h3>Contato, ocorrências e localização</h3>
            <input placeholder="Contato recebido" value={form.contact_received || ""} onChange={(event) => update("contact_received", event.target.value)} />
            <textarea placeholder="Observação de ocorrência" value={form.occurrence_observation || ""} onChange={(event) => update("occurrence_observation", event.target.value)} />
            <div className="location-tools">
              <input type="number" step="0.00000001" placeholder="Latitude" value={form.lat || ""} onChange={(event) => update("lat", event.target.value)} />
              <input type="number" step="0.00000001" placeholder="Longitude" value={form.lng || ""} onChange={(event) => update("lng", event.target.value)} />
              <button type="button" className="secondary" onClick={() => fillCoordinatesFromAgenda()} disabled={!selectedAgenda || isGeocoding}>
                <MapPin size={18} /> {isGeocoding ? "Buscando" : "Obter pelo endereço"}
              </button>
            </div>
            {locationMessage && <small className="field-hint">{locationMessage}</small>}
          </div>

          {message && <div className="alert">{message}</div>}
          <div className="report-submit-actions">
            <button type="submit" className="secondary"><Save size={18} /> Salvar rascunho</button>
            <button type="button" onClick={submitFinal}><Save size={18} /> Enviar relatório</button>
          </div>
        </form>
      </div>

      <aside className="side-panel report-preview">
        <div className="modal-header">
          <h2>Resumo</h2>
          <button className="secondary" type="button" onClick={copyPreview}>
            <Clipboard size={16} /> Copiar
          </button>
        </div>
        <pre>{preview}</pre>
        {!isAdmin && <small>Chefes visualizam os relatórios criados por eles; administradores visualizam todos.</small>}
      </aside>
    </section>
  );
}
