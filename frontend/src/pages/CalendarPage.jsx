import { ChevronLeft, ChevronRight, MapPin, Navigation, Users } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { api } from "../api/client.js";
import Filters from "../components/Filters.jsx";
import { formatDateBR } from "../utils/date.js";
import { statusClass, statusLabel } from "../utils/status.js";

function toISO(date) {
  return date.toISOString().slice(0, 10);
}

function serviceTeamLabel(agenda) {
  return agenda.team_name || agenda.sector_name || "Equipe não definida";
}

function fullAddress(agenda) {
  return [agenda.address, agenda.neighborhood, agenda.city, agenda.state].filter(Boolean).join(", ");
}

function mapsUrl(agenda) {
  const query = fullAddress(agenda) || agenda.location || agenda.institution_location;
  return `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(query)}`;
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
  const [cursor, setCursor] = useState(new Date());
  const [view, setView] = useState("month");
  const [filters, setFilters] = useState({});
  const [agendas, setAgendas] = useState([]);
  const [sectors, setSectors] = useState([]);
  const [selected, setSelected] = useState(null);
  const requestSeq = useRef(0);

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
    api("/sectors/").then((data) => setSectors(data.results || data));
  }, []);

  useEffect(() => {
    const scopedFilters = Object.fromEntries(
      Object.entries(filters).filter(([, value]) => value !== undefined && value !== "")
    );
    delete scopedFilters.date;
    const params = new URLSearchParams({
      ...scopedFilters,
      source: "requests",
      date_from: toISO(days[0]),
      date_to: toISO(days[days.length - 1]),
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
              {mode === "month" ? "Mes" : mode === "week" ? "Semana" : "Dia"}
            </button>
          ))}
        </div>
      </div>
      <Filters filters={filters} setFilters={setFilters} sectors={sectors} showUser={false} />
      <div className="calendar-toolbar">
        <button className="icon-button" onClick={() => move(-1)} aria-label="Anterior"><ChevronLeft size={18} /></button>
        <strong>{cursor.toLocaleDateString("pt-BR", { month: "long", year: "numeric" })}</strong>
        <button className="icon-button" onClick={() => move(1)} aria-label="Próximo"><ChevronRight size={18} /></button>
        <input
          className="jump-date"
          type="date"
          value={toISO(cursor)}
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
          const dayAgendas = agendas.filter((agenda) => agenda.date === toISO(day));
          return (
            <article key={day.toISOString()} className="day-cell">
              <span>{day.getDate()}</span>
              {dayAgendas.map((agenda) => (
                <button key={agenda.id} className={`event-pill ${statusClass[agenda.status]}`} onClick={() => setSelected(agenda)}>
                  <strong>{agenda.start_time.slice(0, 5)} · {serviceTeamLabel(agenda)}</strong>
                  <small>{agenda.title}</small>
                </button>
              ))}
            </article>
          );
        })}
      </div>
      {selected && (
        <div className="modal-backdrop" onClick={() => setSelected(null)}>
          <article className="modal" onClick={(event) => event.stopPropagation()}>
            <h2>{selected.title}</h2>
            <p>{selected.description}</p>
            <div className="calendar-detail-actions">
              <a className="secondary action-link" href={mapsUrl(selected)} target="_blank" rel="noreferrer">
                <Navigation size={16} /> Abrir GPS
              </a>
            </div>
            <dl>
              <dt>Protocolo</dt><dd>#{selected.id}</dd>
              <dt>Horário</dt><dd>{formatDateBR(selected.date)} das {selected.start_time.slice(0, 5)} às {selected.end_time.slice(0, 5)}</dd>
              <dt>Status</dt><dd>{statusLabel[selected.status]}</dd>
              <dt>Equipe de serviço</dt><dd><Users size={15} /> {serviceTeamLabel(selected)}</dd>
              <dt>Chefe</dt><dd>{selected.chief_name || selected.chief_ref_name || "-"}</dd>
              <dt>Agentes</dt><dd>{selected.agents || "-"}</dd>
              <dt>Responsável</dt><dd>{selected.responsible_name}</dd>
              <dt>Local</dt><dd>{selected.institution_location || selected.location}</dd>
              <dt>Endereço</dt><dd><MapPin size={15} /> {fullAddress(selected) || "-"}</dd>
              <dt>Viatura</dt><dd>{selected.vehicle || "-"}</dd>
              <dt>Município</dt><dd>{selected.city || "-"}</dd>
            </dl>
            <button onClick={() => setSelected(null)}>Fechar</button>
          </article>
        </div>
      )}
    </section>
  );
}
