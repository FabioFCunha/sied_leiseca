import { CalendarDays, ChevronLeft, ChevronRight, Clock, MapPin, Navigation, Users, Package } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { api } from "../api/client.js";
import Filters from "../components/Filters.jsx";
import { useAuth } from "../context/AuthContext.jsx";
import { formatDateBR, formatLocalISODate } from "../utils/date.js";
import { statusClass, statusLabel } from "../utils/status.js";

function serviceTeamLabel(agenda) {
  return agenda.team_name || agenda.sector_name || "Equipe não definida";
}

function fullAddress(agenda) {
  return [agenda.address, agenda.neighborhood, agenda.city, agenda.state].filter(Boolean).map(cleanText).join(", ");
}

function supportTeamLabel(agenda) {
  const supports = [agenda.support_1, agenda.support_1_ref_name, agenda.support_2, agenda.support_2_ref_name]
    .map(cleanText)
    .filter(Boolean);
  return supports.length ? Array.from(new Set(supports)).join(" - ") : "-";
}

function mapsUrl(agenda) {
  const query = fullAddress(agenda) || agenda.location || agenda.institution_location;
  return `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(query)}`;
}

function valueOrDash(value) {
  return cleanText(value) || "-";
}

function cleanText(value) {
  if (value === undefined || value === null) return "";
  let text = String(value);
  if (!text) return "";

  if (/[ÃÂâ]/.test(text)) {
    try {
      const bytes = Uint8Array.from([...text].map((char) => char.charCodeAt(0) & 255));
      const decoded = new TextDecoder("utf-8").decode(bytes);
      if (decoded && !decoded.includes("�")) {
        text = decoded;
      }
    } catch {
      // Keep the original text if browser decoding is unavailable.
    }
  }

  return text;
}

function DetailItem({ label, children, className = "" }) {
  return (
    <div className={`detail-item ${className}`}>
      <span>{label}</span>
      <strong>{children}</strong>
    </div>
  );
}

async function loadAllAgendas(query) {
  let path = `/agendas/?${query}&page_size=200`;
  const rows = [];
  while (path) {
    const data = await api(path);
    rows.push(...(data.results || data));
    path = data.next ? `/agendas/?${new URL(data.next).searchParams.toString()}` : "";
  }
  return rows;
}

export default function CalendarPage() {
  const { user } = useAuth();
  const [cursor, setCursor] = useState(new Date());
  const [view, setView] = useState("month");
  const [filters, setFilters] = useState({});
  const [agendas, setAgendas] = useState([]);
  const [sectors, setSectors] = useState([]);
  const [municipalities, setMunicipalities] = useState([]);
  const [regions, setRegions] = useState([]);
  const [selected, setSelected] = useState(null);
  const requestSeq = useRef(0);
  const isVisitor = user?.role === "VISITOR";

  const days = useMemo(() => {
    if (view === "day") return [new Date(cursor)];
    if (view === "week") {
      const start = new Date(cursor);
      start.setDate(cursor.getDate() - cursor.getDay());
      return Array.from({ length: 7 }, (_, i) => new Date(start.getFullYear(), start.getMonth(), start.getDate() + i));
    }
    const first = new Date(cursor.getFullYear(), cursor.getMonth(), 1);
    const start = new Date(first);
    start.setDate(1 - first.getDay());
    return Array.from({ length: 42 }, (_, i) => new Date(start.getFullYear(), start.getMonth(), start.getDate() + i));
  }, [cursor, view]);

  useEffect(() => {
    if (!isVisitor) {
      api("/sectors/").then((data) => setSectors(data.results || data));
      Promise.all([
        api("/municipalities/?page_size=500"),
        api("/regions/?page_size=200")
      ]).then(([munData, regData]) => {
        setMunicipalities(munData.results || munData);
        setRegions(regData.results || regData);
      });
    }
  }, [isVisitor]);

  useEffect(() => {
    const scopedFilters = Object.fromEntries(
      Object.entries(filters).filter(([, value]) => value !== undefined && value !== "")
    );
    delete scopedFilters.date;
    const params = new URLSearchParams({
      ...scopedFilters,
      date_from: formatLocalISODate(days[0]),
      date_to: formatLocalISODate(days[days.length - 1]),
    }).toString();
    const seq = requestSeq.current + 1;
    requestSeq.current = seq;
    loadAllAgendas(params).then((rows) => {
      if (seq === requestSeq.current) {
        setAgendas(rows);
      }
    });
  }, [days, filters]);

  const move = (direction) => {
    const next = new Date(cursor);
    next.setDate(cursor.getDate() + direction * (view === "day" ? 1 : view === "week" ? 7 : 30));
    setCursor(next);
  };

  return (
    <section className="page">
      <div className="page-title">
        <div>
          <h1>Calendário</h1>
          <p>Visualize agendas importadas e novas por mês, semana ou dia.</p>
        </div>
        <div className="segmented">
          {["month", "week", "day"].map((mode) => (
            <button key={mode} className={view === mode ? "active" : ""} onClick={() => setView(mode)}>
              {mode === "month" ? "Mês" : mode === "week" ? "Semana" : "Dia"}
            </button>
          ))}
        </div>
      </div>
      {!isVisitor && <Filters filters={filters} setFilters={setFilters} sectors={sectors} municipalities={municipalities} regions={regions} showUser={false} />}
      <div className="calendar-toolbar">
        <button className="icon-button" onClick={() => move(-1)} aria-label="Anterior"><ChevronLeft size={18} /></button>
        <strong>{cursor.toLocaleDateString("pt-BR", { month: "long", year: "numeric" })}</strong>
        <button className="icon-button" onClick={() => move(1)} aria-label="Próximo"><ChevronRight size={18} /></button>
        <input
          className="jump-date"
          type="date"
          value={formatLocalISODate(cursor)}
          onChange={(event) => setCursor(new Date(`${event.target.value}T12:00:00`))}
        />
      </div>
      <div className="calendar-legend" aria-label="Legenda de status">
        <span><i className="legend-dot warning" /> Pendente / aguardando</span>
        <span><i className="legend-dot success" /> Aprovada / confirmada</span>
        <span><i className="legend-dot danger" /> Cancelada / não confirmada</span>
      </div>
      <div className={`calendar-grid ${view}`}>
        {days.map((day) => {
          const dayAgendas = agendas.filter((agenda) => agenda.date === formatLocalISODate(day));
          return (
            <article key={formatLocalISODate(day)} className="day-cell">
              <span>{day.getDate()}</span>
              {dayAgendas.map((agenda) => (
                <button key={agenda.id} className={`event-pill ${statusClass[agenda.status]}`} onClick={() => setSelected(agenda)}>
                  <strong>{agenda.start_time?.slice(0, 5) || ""}{!isVisitor && ` - ${serviceTeamLabel(agenda)}`}</strong>
                  <small>{valueOrDash(agenda.title)}</small>
                </button>
              ))}
            </article>
          );
        })}
      </div>
      {selected && (
        <div className="modal-backdrop" onClick={() => setSelected(null)}>
          <article className={`modal ${isVisitor ? "visitor-event-modal" : ""}`} onClick={(event) => event.stopPropagation()}>
            {isVisitor ? (
              <>
                <header className="visitor-event-header">
                  <div>
                    <span className={`status-chip ${statusClass[selected.status]}`}>{statusLabel[selected.status]}</span>
                    <h2>{valueOrDash(selected.title)}</h2>
                    <p>{valueOrDash(selected.description || "Detalhes da ação agendada para acompanhamento institucional.")}</p>
                  </div>
                </header>
                <div className="visitor-event-summary">
                  <span><CalendarDays size={17} /> {formatDateBR(selected.date)}</span>
                  <span><Clock size={17} /> {selected.start_time?.slice(0, 5) || ""} às {selected.end_time?.slice(0, 5) || ""}</span>
                  <span><MapPin size={17} /> {valueOrDash(selected.city || selected.municipality_ref_name || "Município não informado")}</span>
                </div>
              </>
            ) : (
              <>
                <h2>{valueOrDash(selected.title)}</h2>
                <p>{valueOrDash(selected.description)}</p>
              </>
            )}
            <div className="calendar-detail-actions" style={{ display: 'flex', gap: '16px', alignItems: 'flex-start', flexWrap: 'wrap' }}>
              <a className="secondary action-link" href={mapsUrl(selected)} target="_blank" rel="noreferrer">
                <Navigation size={16} /> Abrir GPS
              </a>
              {!isVisitor && selected.materials?.filter(m => m.kit_name || m.material_name || m.dynamic_name).length > 0 && (
                <div style={{ background: '#fff3cd', border: '1px solid #ffe69c', borderRadius: '8px', padding: '12px 16px', flex: 1, minWidth: '220px' }}>
                  <strong style={{ color: '#664d03', fontSize: '13px', textTransform: 'uppercase', marginBottom: '4px', display: 'flex', alignItems: 'center', gap: '6px' }}><Package size={16}/> Materiais para entrega</strong>
                  <ul style={{ margin: 0, paddingLeft: '22px', color: '#664d03', fontSize: '14px', fontWeight: '600' }}>
                    {selected.materials.map((m, i) => {
                      const name = m.kit_name || m.material_name || m.dynamic_name;
                      return name ? <li key={i} style={{ marginBottom: '4px' }}>{name} {m.quantity ? `(${m.quantity})` : ""}</li> : null;
                    })}
                  </ul>
                </div>
              )}
            </div>
            {isVisitor && (
              <div className="visitor-detail-sections">
                <section>
                  <h3>Dados do evento</h3>
                  <div className="detail-grid">
                    <DetailItem label="Tipo de atividade">{valueOrDash(selected.activity_type || selected.action_type || selected.action_type_ref_name)}</DetailItem>
                    <DetailItem label="Público">{valueOrDash(selected.audience)}</DetailItem>
                    <DetailItem label="Faixa etária">{valueOrDash(selected.age_ranges)}</DetailItem>
                    <DetailItem label="Tipo de solicitante">{valueOrDash(selected.requester_entity_type)}</DetailItem>
                  </div>
                </section>
                <section>
                  <h3>Local e acesso</h3>
                  <div className="detail-grid">
                    <DetailItem label="Local" className="full">{valueOrDash(selected.institution_location || selected.location)}</DetailItem>
                    <DetailItem label="Endereço" className="full">{fullAddress(selected) || "-"}</DetailItem>
                    <DetailItem label="Município">{valueOrDash(selected.city || selected.municipality_ref_name)}</DetailItem>
                  </div>
                </section>
              </div>
            )}
            {!isVisitor && (
            <dl>
              <dt>Protocolo</dt><dd>#{selected.id}</dd>
              <dt>Horário</dt><dd>{formatDateBR(selected.date)} das {selected.start_time?.slice(0, 5) || ""} às {selected.end_time?.slice(0, 5) || ""}</dd>
              <dt>Status</dt><dd>{statusLabel[selected.status]}</dd>
              {!isVisitor && (
                <>
                  <dt>Equipe de serviço</dt><dd><Users size={15} /> {serviceTeamLabel(selected)}</dd>
                  <dt>Chefe</dt><dd>{selected.chief_name || selected.chief_ref_name || "-"}</dd>
                  <dt>Agentes</dt><dd>{selected.agents || "-"}</dd>
                  <dt>Apoio</dt><dd>{supportTeamLabel(selected)}</dd>
                  <dt>Responsável</dt><dd>{selected.responsible_name}</dd>
                </>
              )}
              <dt>Local</dt><dd>{selected.institution_location || selected.location}</dd>
              <dt>Endereço</dt><dd><MapPin size={15} /> {fullAddress(selected) || "-"}</dd>
              {!isVisitor && <><dt>Viatura</dt><dd>{selected.vehicle || "-"}</dd></>}
              <dt>Município</dt><dd>{selected.city || "-"}</dd>
            </dl>
            )}
            <button onClick={() => setSelected(null)}>Fechar</button>
          </article>
        </div>
      )}
    </section>
  );
}
