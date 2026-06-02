import {
  CalendarCheck,
  CalendarClock,
  CheckCircle2,
  Clock3,
  Download,
  FileSpreadsheet,
  PauseCircle,
  Search,
  Star,
  StarHalf,
  Users,
  XCircle,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { api, downloadUrl } from "../api/client.js";
import { formatDateBR } from "../utils/date.js";
import { statusClass, statusLabel } from "../utils/status.js";

const emptyFilters = {
  q: "",
  date_from: "",
  date_to: "",
  status: "",
  municipality: "",
};

const cardConfig = [
  { key: "approved", label: "Aprovadas", icon: CheckCircle2, tone: "green", status: "APPROVED" },
  { key: "pending", label: "Pendentes", icon: Clock3, tone: "amber", status: "PENDING" },
  { key: "cancelled", label: "Canceladas", icon: XCircle, tone: "red", status: "CANCELLED" },
  { key: "upcoming", label: "Próximas agendas", icon: CalendarClock, tone: "violet" },
  { key: "today_total", label: "Agendas de hoje", icon: CalendarCheck, tone: "blue" },
  { key: "today_agents", label: "Agentes escalados hoje", icon: Users, tone: "cyan" },
  { key: "in_progress", label: "Em andamento", icon: PauseCircle, tone: "teal" },
];

const chartFilters = ["Hoje", "Semana", "Mês", "Ano"];
const weekDays = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"];
const hourSlots = ["06:00", "08:00", "10:00", "12:00", "14:00", "16:00", "18:00", "20:00"];

function dateToInputValue(date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function DashboardCard({ active, config, data, onClick }) {
  const Icon = config.icon;
  return (
    <button className={`metric-card ${config.tone} ${active ? "active" : ""}`} onClick={onClick} type="button">
      <span className="metric-icon"><Icon size={18} /></span>
      <span>{config.label}</span>
      <strong>{data?.value ?? 0}</strong>
    </button>
  );
}

function LineChart({ data = [] }) {
  const max = Math.max(...data.map((item) => item.value), 1);
  const chartPoints = data.map((item, index) => {
    const x = data.length <= 1 ? 0 : (index / (data.length - 1)) * 100;
    const y = 100 - (item.value / max) * 86 - 7;
    return { ...item, x, y };
  });
  const points = chartPoints.map((item) => `${item.x},${item.y}`).join(" ");

  return (
    <div className="chart-card main-chart">
      <div className="section-heading">
        <div>
          <h2>Evolução das agendas</h2>
          <p>Comparativo diário do período selecionado.</p>
        </div>
      </div>
      <div className="line-chart-wrap">
      <svg viewBox="0 0 100 100" preserveAspectRatio="none" className="line-chart">
        <defs>
          <linearGradient id="lineFill" x1="0" x2="0" y1="0" y2="1">
            <stop offset="0%" stopColor="#0048d7" stopOpacity="0.24" />
            <stop offset="100%" stopColor="#0048d7" stopOpacity="0.02" />
          </linearGradient>
        </defs>
        <polyline points={`0,100 ${points} 100,100`} fill="url(#lineFill)" stroke="none" />
        <polyline points={points} fill="none" stroke="#0048d7" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.6" />
      </svg>
        {chartPoints.map((item, index) => (
          <span
            className="line-chart-value"
            data-tooltip={`${item.label}: ${item.value} agenda${item.value === 1 ? "" : "s"}`}
            key={`${item.label}-${index}`}
            style={{ left: `${item.x}%`, top: `${Math.max(4, item.y - 9)}%` }}
            title={`${item.label}: ${item.value}`}
          >
            {item.value}
          </span>
        ))}
      </div>
      <div className="chart-axis">
        {data.filter((_, index) => data.length <= 12 || index % 4 === 0).map((item) => <span key={item.label}>{item.label}</span>)}
      </div>
    </div>
  );
}

function BarList({ title, data = [] }) {
  const max = Math.max(...data.map((item) => item.value), 1);
  return (
    <div className="chart-card">
      <div className="section-heading">
        <h2>{title}</h2>
      </div>
      <div className="bar-list">
        {data.map((item) => (
          <div className="bar-row" key={item.label}>
            <span>{item.label}</span>
            <div><i style={{ width: `${(item.value / max) * 100}%` }} /></div>
            <strong>{item.value}</strong>
          </div>
        ))}
      </div>
    </div>
  );
}

function DonutChart({ data = [] }) {
  const total = Math.max(data.reduce((sum, item) => sum + item.value, 0), 1);
  let current = 0;
  const colors = ["#0048d7", "#0b3d9f", "#f6bd16", "#ef6b5a", "#64748b", "#7c3aed", "#0ea5e9", "#16a34a"];
  const stops = data.map((item, index) => {
    const start = current;
    current += (item.value / total) * 100;
    return `${colors[index % colors.length]} ${start}% ${current}%`;
  }).join(", ");
  return (
    <div className="chart-card donut-card">
      <div className="section-heading"><h2>Agendas por município</h2></div>
      <div className="donut" style={{ background: `conic-gradient(${stops})` }}>
        <div className="donut-center">
          <span>{total}</span>
          <small>agendas</small>
        </div>
      </div>
      <div className="donut-legend">
        {data.map((item, index) => (
          <span key={item.label}><i style={{ background: colors[index % colors.length] }} />{item.label} {Math.round((item.value / total) * 100)}%</span>
        ))}
      </div>
    </div>
  );
}

function Heatmap({ data = [] }) {
  const values = new Map(data.map((item) => [`${item.day}-${item.slot}`, item.total]));
  const max = Math.max(...data.map((item) => item.total), 1);
  return (
    <div className="chart-card heatmap-card">
      <div className="section-heading"><h2>Horários mais utilizados</h2></div>
      <div className="heatmap">
        <div className="heatmap-header">
          <strong>Dia</strong>
          {hourSlots.map((slot) => <small key={slot}>{slot}</small>)}
        </div>
        {weekDays.map((day, dayIndex) => (
          <div className="heatmap-row" key={day}>
            <strong>{day}</strong>
            {hourSlots.map((slot) => {
              const value = values.get(`${dayIndex}-${slot}`) || 0;
              return (
                <i
                  className={value ? "" : "is-empty"}
                  key={slot}
                  title={`${day} ${slot}: ${value}`}
                  style={{ backgroundColor: `rgba(0, 72, 215, ${0.14 + (value / max) * 0.72})` }}
                >
                  {value}
                </i>
              );
            })}
          </div>
        ))}
      </div>
    </div>
  );
}

function MiniCalendar({ days = [] }) {
  const max = Math.max(...days.map((item) => item.total), 1);
  const monthLabel = days[0]?.date
    ? new Intl.DateTimeFormat("pt-BR", { month: "long", year: "numeric", timeZone: "UTC" }).format(new Date(`${days[0].date}T00:00:00Z`))
    : "mês";
  return (
    <div className="chart-card mini-calendar-card">
      <div className="section-heading">
        <div>
          <h2>Calendário de {monthLabel}</h2>
          <p>Quantidade de agendas por dia.</p>
        </div>
      </div>
      <div className="mini-calendar">
        {days.map((day) => (
          <button key={day.date} title={`${formatDateBR(day.date)}: ${day.total} agendas`} type="button">
            <span>{day.day}</span>
            <strong>{day.total}</strong>
            <i style={{ height: `${Math.max(4, (day.total / max) * 22)}px` }} />
          </button>
        ))}
      </div>
    </div>
  );
}

function Stars({ rating, max = 5 }) {
  const stars = [];
  for (let i = 1; i <= max; i++) {
    if (rating >= i) {
      stars.push(<Star key={i} size={16} fill="#f59e0b" color="#f59e0b" />);
    } else if (rating >= i - 0.5) {
      stars.push(<StarHalf key={i} size={16} fill="#f59e0b" color="#f59e0b" />);
    } else {
      stars.push(<Star key={i} size={16} color="#d1d5db" />);
    }
  }
  return <div className="stars-container" style={{ display: "flex", gap: "2px" }}>{stars}</div>;
}

function SatisfactionSurveyPanel({ surveys = {} }) {
  const { overall_rating = 0, total_responses = 0, team_ratings = [], messages = [] } = surveys;
  
  return (
    <div className="chart-card satisfaction-panel">
      <div className="section-heading">
        <div>
          <h2>Indicadores de Satisfação</h2>
          <p>Avaliações baseadas nas pesquisas de satisfação respondidas.</p>
        </div>
      </div>
      <div className="satisfaction-grid" style={{ display: "grid", gap: "24px", gridTemplateColumns: "1fr 1fr" }}>
        <div className="satisfaction-ratings" style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
          <div className="overall-rating-card" style={{ background: "#f8fbff", padding: "16px", borderRadius: "12px", border: "1px solid var(--line)", display: "flex", alignItems: "center", gap: "16px" }}>
            <div style={{ fontSize: "42px", fontWeight: "900", color: "#17202a", lineHeight: 1 }}>{overall_rating.toFixed(1)}</div>
            <div>
              <Stars rating={overall_rating} />
              <div style={{ fontSize: "13px", color: "var(--text-soft)", marginTop: "4px" }}>Baseado em {total_responses} avaliações</div>
            </div>
          </div>
          
          <div className="team-ratings-list" style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
            <h3 style={{ fontSize: "14px", fontWeight: "800", color: "#17202a", margin: "8px 0 0" }}>Avaliações por equipe</h3>
            {team_ratings.length ? team_ratings.map((team, idx) => (
              <div key={idx} className="team-rating-row" style={{ display: "flex", alignItems: "center", justifyContent: "space-between", paddingBottom: "12px", borderBottom: "1px solid var(--line)" }}>
                <div style={{ display: "flex", flexDirection: "column" }}>
                  <strong style={{ fontSize: "14px", color: "#17202a" }}>{team.team}</strong>
                  <span style={{ fontSize: "12px", color: "var(--text-soft)" }}>{team.count} avaliações</span>
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                  <span style={{ fontSize: "14px", fontWeight: "800" }}>{team.avg.toFixed(1)}</span>
                  <Stars rating={team.avg} />
                </div>
              </div>
            )) : <p style={{ color: "var(--text-soft)", fontSize: "13px" }}>Nenhuma avaliação por equipe disponível.</p>}
          </div>
        </div>

        <div className="satisfaction-messages" style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
          <h3 style={{ fontSize: "14px", fontWeight: "800", color: "#17202a", margin: 0 }}>Mensagens recentes</h3>
          <div className="messages-list" style={{ display: "flex", flexDirection: "column", gap: "12px", maxHeight: "400px", overflowY: "auto", paddingRight: "8px" }}>
            {messages.length ? messages.map((msg, idx) => (
              <div key={idx} className="message-card" style={{ background: "#fff", padding: "12px", borderRadius: "8px", border: "1px solid var(--line)", display: "flex", flexDirection: "column", gap: "8px" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <Stars rating={msg.overall_rating} />
                  <span style={{ fontSize: "11px", color: "var(--text-soft)", fontWeight: "700" }}>{new Date(msg.created_at).toLocaleDateString("pt-BR")}</span>
                </div>
                <p style={{ margin: 0, fontSize: "13px", color: "var(--text)", lineHeight: 1.5 }}>"{msg.suggestion}"</p>
                {msg.team && <div style={{ fontSize: "11px", color: "var(--primary)", fontWeight: "800" }}>Equipe: {msg.team}</div>}
              </div>
            )) : <p style={{ color: "var(--text-soft)", fontSize: "13px" }}>Nenhuma mensagem recente.</p>}
          </div>
        </div>
      </div>
    </div>
  );
}

function ActivityPanel({ activity, advanced }) {
  return (
    <aside className="dashboard-side">
      <div className="chart-card">
        <div className="section-heading"><h2>Equipes em campo hoje</h2></div>
        <div className="field-team-list">
          {(activity?.field_teams || []).length ? (
            activity.field_teams.map((item) => (
              <span key={item.id}>
                <i>{item.time}</i>
                <strong>{item.team}</strong>
                <small>{item.title} · {statusLabel[item.status]}</small>
              </span>
            ))
          ) : (
            <p>Nenhuma equipe em campo hoje.</p>
          )}
        </div>
      </div>
      <div className="chart-card">
        <div className="section-heading"><h2>Indicadores avançados</h2></div>
        <div className="advanced-list">
          <span>Taxa de aprovação <strong>{advanced?.approval_rate ?? 0}%</strong></span>
          <span>Taxa de cancelamento <strong>{advanced?.cancellation_rate ?? 0}%</strong></span>
          <span>Tempo médio de aprovação <strong>{advanced?.approval_avg_hours ?? 0}h</strong></span>
          <span>Média por usuário <strong>{advanced?.avg_per_user ?? 0}</strong></span>
          <span>Dentro do prazo <strong>{advanced?.sla ?? 0}%</strong></span>
        </div>
      </div>
    </aside>
  );
}

export default function DashboardPage() {
  const [dashboard, setDashboard] = useState(null);
  const [filters, setFilters] = useState(emptyFilters);
  const [municipalities, setMunicipalities] = useState([]);
  const [chartRange, setChartRange] = useState("Mês");
  const [loading, setLoading] = useState(true);
  const [refreshTick, setRefreshTick] = useState(0);
  const [error, setError] = useState("");
  useEffect(() => {
    api("/municipalities/?page_size=500").then((data) => setMunicipalities(data.results || data));
  }, []);

  useEffect(() => {
    setLoading(true);
    setError("");
    const params = new URLSearchParams(Object.entries(filters).filter(([, value]) => value)).toString();
    api(`/agendas/dashboard/${params ? `?${params}` : ""}`)
      .then(setDashboard)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [filters, refreshTick]);

  useEffect(() => {
    const interval = setInterval(() => setRefreshTick((current) => current + 1), 60000);
    return () => clearInterval(interval);
  }, []);

  const updateFilter = (field, value) => {
    if (field === "date_from" || field === "date_to") {
      setChartRange("");
      setFilters((current) => ({ ...current, [field]: value, chart_group: "" }));
      return;
    }
    setFilters((current) => ({ ...current, [field]: value }));
  };

  const applyChartRange = (range) => {
    setChartRange(range);

    const today = new Date();
    const start = new Date(today);
    const end = new Date(today);

    if (range === chartFilters[1]) {
      start.setDate(today.getDate() - ((today.getDay() + 6) % 7));
    } else if (range === chartFilters[2]) {
      start.setDate(1);
    } else if (range === chartFilters[3]) {
      start.setMonth(0, 1);
      end.setMonth(11, 31);
    }

    setFilters((current) => ({
      ...current,
      date_from: dateToInputValue(start),
      date_to: dateToInputValue(end),
      chart_group: range === chartFilters[3] ? "month" : "",
    }));
  };

  const handleExport = async (format, e) => {
    e.preventDefault();
    try {
      const params = new URLSearchParams(Object.entries(filters).filter(([, value]) => value)).toString();
      const path = `/reports/export_${format}/${params ? `?${params}` : ""}`;
      const blob = await api(path);
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `relatorio-agendas.${format === "excel" ? "xlsx" : "pdf"}`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error(err);
      alert(err.message || "Erro ao exportar o relatório.");
    }
  };

  return (
    <section className="page dashboard-page">
      <div className="dashboard-hero">
        <div>
          <span>Visão operacional</span>
          <h1>Dashboard</h1>
          <p>Agenda OLS com indicadores, tendências, calendário e atividades recentes.</p>
        </div>
        <div style={{ display: "flex", gap: "12px", alignItems: "center" }}>
          <div className="hero-search">
            <Search size={18} />
            <input placeholder="Pesquisar agenda, local ou protocolo" value={filters.q} onChange={(event) => updateFilter("q", event.target.value)} />
          </div>
          <button className="secondary export-link" onClick={(e) => handleExport("pdf", e)} style={{ height: "42px", padding: "0 16px", display: "inline-flex", alignItems: "center", gap: "8px", borderRadius: "8px", fontWeight: "600", fontSize: "14px" }} type="button">
            <Download size={16} /> Exportar relatório
          </button>
        </div>
      </div>

      <div className="global-filters">
        <input type="date" value={filters.date_from} onChange={(event) => updateFilter("date_from", event.target.value)} />
        <input type="date" value={filters.date_to} onChange={(event) => updateFilter("date_to", event.target.value)} />
        <select value={filters.status} onChange={(event) => updateFilter("status", event.target.value)}>
          <option value="">Todos os status</option>
          <option value="PENDING">Pendente</option>
          <option value="APPROVED">Aprovada</option>
          <option value="CANCELLED">Cancelada</option>
        </select>
        <select value={filters.municipality} onChange={(event) => updateFilter("municipality", event.target.value)}>
          <option value="">Todos os municípios</option>
          {municipalities.map((municipality) => <option key={municipality.id} value={municipality.id}>{municipality.name}</option>)}
        </select>
        <button className="secondary" type="button" onClick={() => { setFilters(emptyFilters); setChartRange(chartFilters[2]); }}>Limpar</button>
      </div>

      {loading ? (
        <div className="dashboard-skeleton"><span /><span /><span /></div>
      ) : error ? (
        <div className="alert">Não foi possível carregar o Dashboard: {error}</div>
      ) : (
        <>
          <div className="metric-grid">
            {cardConfig.map((config) => (
              <DashboardCard
                active={filters.status === config.status}
                config={config}
                data={dashboard?.cards?.[config.key]}
                key={config.key}
                onClick={() => config.status && updateFilter("status", filters.status === config.status ? "" : config.status)}
              />
            ))}
          </div>

          <div className="dashboard-layout">
            <div className="dashboard-main">
              <div className="chart-card">
                <div className="chart-filter-tabs">
                  {chartFilters.map((item, index) => (
                    <button className={chartRange === item ? "active" : ""} key={item} onClick={() => applyChartRange(item)} type="button">{item}</button>
                  ))}
                </div>
                <LineChart data={dashboard?.series?.daily || []} />
              </div>
              <div className="analytics-grid">
                <BarList title="Ações feitas por equipe" data={dashboard?.bars?.by_team_actions || []} />
                <BarList title="Agendas por bairro" data={dashboard?.bars?.by_neighborhood || []} />
                <DonutChart data={dashboard?.donut || []} />
                <Heatmap data={dashboard?.heatmap || []} />
              </div>
              <div className="analytics-grid bottom">
                <MiniCalendar days={dashboard?.calendar || []} />
                <SatisfactionSurveyPanel surveys={dashboard?.surveys || {}} />
              </div>
            </div>
            <ActivityPanel activity={dashboard?.activity} advanced={dashboard?.advanced} />
          </div>
        </>
      )}
    </section>
  );
}
