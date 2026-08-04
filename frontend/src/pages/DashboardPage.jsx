import {
  AlertTriangle,
  CalendarCheck,
  CalendarClock,
  CheckCircle2,
  CheckCheck,
  Clock3,
  Download,
  FileText,
  Flag,
  MapPin,
  PauseCircle,
  Search,
  UserCheck,
  Users,
  Activity,
  Shield,
  XCircle,
} from "lucide-react";
import { useEffect, useState } from "react";
import { api } from "../api/client.js";
import { formatDateBR } from "../utils/date.js";
import { statusLabel } from "../utils/status.js";
import { useAuth } from "../context/AuthContext.jsx";
import { formatLocalISODate } from "../utils/date.js";
import { downloadUrl, getToken } from "../api/client.js";

const today = new Date();
const todayInput = formatLocalISODate(today);

const emptyFilters = {
  q: "",
  date: todayInput,
  institution: "",
  service_order: "",
};

const cardConfig = [
  { key: "approved", label: "Aguardando OS", tooltip: "Solicitações aprovadas que ainda aguardam a geração da Ordem de Serviço", icon: CheckCircle2, tone: "green", status: "APPROVED", color: "#00b894", gradient: "linear-gradient(135deg, #00b894, #009472)" },
  { key: "pending", label: "Aguardando análise", tooltip: "Solicitações ainda não avaliadas pelo Gestor ou Administrador", icon: Clock3, tone: "amber", status: "PENDING", color: "#fdcb6e", gradient: "linear-gradient(135deg, #fdcb6e, #e1b12c)" },
  { key: "cancelled", label: "Recusadas / Canceladas", tooltip: "Solicitações recusadas ou canceladas no período selecionado", icon: XCircle, tone: "red", status: "CANCELLED", color: "#d63031", gradient: "linear-gradient(135deg, #d63031, #b33939)" },
  { key: "completed", label: "Relatórios aprovados", tooltip: "Ações com relatório técnico conferido e aprovado", icon: CheckCheck, tone: "emerald", status: "COMPLETED", color: "#0984e3", gradient: "linear-gradient(135deg, #0984e3, #0762a8)" },
  { key: "upcoming", label: "Próximas agendas", icon: CalendarClock, tone: "violet", color: "#6c5ce7", gradient: "linear-gradient(135deg, #6c5ce7, #5345b5)" },
  { key: "today_total", label: "Agendas de hoje", icon: CalendarCheck, tone: "blue", color: "#74b9ff", gradient: "linear-gradient(135deg, #74b9ff, #5798d6)" },
  { key: "today_agents", label: "Agentes de hoje", icon: Users, tone: "cyan", color: "#00cec9", gradient: "linear-gradient(135deg, #00cec9, #00a4a1)" },
  { key: "in_progress", label: "Em andamento", icon: PauseCircle, tone: "teal", color: "#e84393", gradient: "linear-gradient(135deg, #e84393, #c23979)" },
];

const chartFilters = ["Hoje", "Semana", "Mês", "Ano"];
const weekDays = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"];
const hourSlots = ["08:00", "09:00", "10:00", "11:00", "12:00", "13:00", "14:00", "15:00", "16:00", "17:00", "18:00"];

const exceptionalOccurrenceTypeLabels = {
  VEHICLE_BREAKDOWN: "Quebra ou pane de viatura",
  WORK_ACCIDENT: "Acidente de trabalho",
  MEDICAL_ASSISTANCE: "Atendimento médico",
  EQUIPMENT_OR_MATERIAL: "Problema com equipamento ou material",
  ACTIVITY_INTERRUPTION: "Interrupção da atividade",
  SECURITY_INCIDENT: "Ocorrência de segurança",
  SEVERE_WEATHER: "Condição climática grave",
  OTHER: "Outro",
};

const exceptionalOccurrenceImpactLabels = {
  NO_IMPACT: "Sem prejuízo",
  PARTIAL: "Prejudicada parcialmente",
  INTERRUPTED: "Interrompida",
};

function getExceptionalOccurrenceStyle(impact) {
  const palette = {
    NO_IMPACT: {
      border: "1px solid #facc15",
      background: "#fefce8",
      color: "#854d0e",
    },
    PARTIAL: {
      border: "1px solid #fb923c",
      background: "#fff7ed",
      color: "#9a3412",
    },
    INTERRUPTED: {
      border: "1px solid #f87171",
      background: "#fef2f2",
      color: "#991b1b",
    },
  };

  return {
    borderRadius: 12,
    padding: "12px 14px",
    display: "grid",
    gap: 8,
    ...(palette[String(impact || "").toUpperCase()] || {
      border: "1px solid var(--line)",
      background: "var(--surface-2)",
      color: "var(--text)",
    }),
  };
}

function dateToInputValue(date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function DashboardCard({ active, config, data, onClick }) {
  const Icon = config.icon;
  return (
    <button
      title={config.tooltip || config.label}
      onClick={onClick}
      type="button"
      style={{
        background: active ? "var(--surface)" : "var(--surface)",
        borderRadius: "16px",
        padding: "20px",
        border: active ? `2px solid ${config.color}` : "1px solid var(--line)",
        boxShadow: active ? `0 8px 24px ${config.color}33` : "0 4px 12px rgba(0,0,0,0.02)",
        display: "flex",
        flexDirection: "column",
        gap: "12px",
        position: "relative",
        overflow: "hidden",
        transition: "all 0.2s cubic-bezier(0.4, 0, 0.2, 1)",
        transform: active ? "translateY(-4px)" : "none",
        cursor: "pointer",
        textAlign: "left",
      }}
      onMouseEnter={e => {
        if (!active) {
          e.currentTarget.style.transform = "translateY(-2px)";
          e.currentTarget.style.boxShadow = `0 8px 24px ${config.color}22`;
        }
      }}
      onMouseLeave={e => {
        if (!active) {
          e.currentTarget.style.transform = "none";
          e.currentTarget.style.boxShadow = "0 4px 12px rgba(0,0,0,0.02)";
        }
      }}
    >
      <div style={{ position: "absolute", top: -20, right: -20, width: 80, height: 80, borderRadius: "50%", background: config.color, opacity: active ? 0.1 : 0.04 }} />
      <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
        <div style={{ width: "36px", height: "36px", borderRadius: "10px", display: "flex", alignItems: "center", justifyContent: "center", background: config.gradient, color: "#fff", boxShadow: `0 4px 12px ${config.color}44`, flexShrink: 0 }}>
          <Icon size={18} />
        </div>
        <span style={{ fontSize: "12px", fontWeight: "700", color: "var(--text-soft)", textTransform: "uppercase", letterSpacing: "0.5px", whiteSpace: "normal", lineHeight: "1.2", textAlign: "left" }}>{config.label}</span>
      </div>
      <strong style={{ fontSize: "32px", fontWeight: "800", color: "var(--text)", lineHeight: "1" }}>{data?.value ?? 0}</strong>
    </button>
  );
}

const chiefComparisonConfig = [
  {
    key: "approaches",
    label: "Total de Abordagens",
    tooltip: "Total de pessoas abordadas em todas as ações enviadas",
    icon: Users,
    reported: "approaches",
    color: "#0048d7",
    gradient: "linear-gradient(135deg, #0048d7, #003299)",
  },
  {
    key: "actions",
    label: "Ações Realizadas",
    tooltip: "Ações executadas, independentemente da aprovação do relatório",
    icon: CalendarCheck,
    reported: "registered_actions",
    color: "#7c3aed",
    gradient: "linear-gradient(135deg, #7c3aed, #5b21b6)",
  },
  {
    key: "waiting",
    label: "Aguardando aprovação",
    tooltip: "Ações realizadas cujos relatórios ainda não foram aprovados",
    icon: Clock3,
    reported: "reports_waiting_approval",
    color: "#f59e0b",
    gradient: "linear-gradient(135deg, #f59e0b, #b45309)",
  },
  {
    key: "avg-action",
    label: "Média por Ação",
    tooltip: "Média de abordagens por ação realizada",
    icon: Activity,
    reported: "average_approaches_per_action",
    color: "#047857",
    gradient: "linear-gradient(135deg, #047857, #022c22)",
  },
  {
    key: "avg-team",
    label: "Média por Equipe",
    tooltip: "Média de abordagens dividida pelo número de equipes",
    icon: Shield,
    reported: "average_approaches_per_team",
    color: "#dc6b16",
    gradient: "linear-gradient(135deg, #dc6b16, #ea580c)",
  },
];

function formatMetric(value) {
  return Number(value || 0).toLocaleString("pt-BR");
}

function ChiefFillingsMetrics({ data = {} }) {
  return (
    <div className="chart-card chief-fillings-card" style={{ border: "1px solid var(--line)", borderRadius: "16px", padding: "24px", marginBottom: "32px", background: "var(--surface)" }}>
      <div className="section-heading" style={{ marginBottom: "20px" }}>
        <div>
          <h2 style={{ fontSize: "18px", fontWeight: "800", color: "var(--text)" }}>Painel de Desempenho Operacional</h2>
          <p style={{ fontSize: "13px", color: "var(--text-soft)", marginTop: "4px" }}>Visão direta e consolidada do resultado das equipes em campo.</p>
        </div>
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "20px" }}>
        {chiefComparisonConfig.map((item) => {
          const Icon = item.icon;
          return (
            <div key={item.key} title={item.tooltip} style={{
              background: "var(--surface)", borderRadius: "16px", padding: "24px",
              border: "1px solid var(--line)",
              boxShadow: "0 4px 24px rgba(0,0,0,0.04)",
              display: "flex", flexDirection: "column", gap: "12px", position: "relative",
              overflow: "hidden", transition: "transform 0.2s, box-shadow 0.2s"
            }}
            onMouseEnter={e => { e.currentTarget.style.transform = "translateY(-2px)"; e.currentTarget.style.boxShadow = "0 8px 32px " + item.color + "22"; }}
            onMouseLeave={e => { e.currentTarget.style.transform = ""; e.currentTarget.style.boxShadow = "0 4px 24px rgba(0,0,0,0.04)"; }}
            >
              <div style={{
                position: "absolute", top: -20, right: -20, width: 80, height: 80,
                borderRadius: "50%", background: item.color, opacity: 0.06
              }} />
              <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                <div style={{
                  width: "40px", height: "40px", borderRadius: "12px", display: "flex",
                  alignItems: "center", justifyContent: "center",
                  background: item.gradient, color: "#fff", flexShrink: 0,
                  boxShadow: "0 4px 12px " + item.color + "44"
                }}>
                  <Icon size={20} />
                </div>
                <span style={{ fontSize: "13px", fontWeight: "700", color: "var(--text-soft)", textTransform: "uppercase", letterSpacing: "0.5px", lineHeight: "1.2" }}>{item.label}</span>
              </div>
              <strong style={{ fontSize: "36px", fontWeight: "800", color: "var(--text)", lineHeight: "1.1", marginTop: "4px" }}>{formatMetric(data[item.reported])}</strong>
            </div>
          );
        })}
      </div>
    </div>
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
    <div className="chart-card main-chart" style={{ border: "1px solid var(--line)", borderRadius: "16px", padding: "20px" }}>
      <div className="section-heading" style={{ marginBottom: "20px" }}>
        <div>
          <h2 style={{ fontSize: "16px", fontWeight: "800" }}>Evolução das agendas</h2>
          <p style={{ fontSize: "12px", color: "var(--text-soft)" }}>Comparativo diário do período selecionado.</p>
        </div>
      </div>
      <div className="line-chart-wrap" style={{ position: "relative", height: "260px", padding: "10px 0" }}>
        <svg viewBox="0 0 100 100" preserveAspectRatio="none" className="line-chart" style={{ height: "100%", width: "100%" }}>
          <defs>
            <linearGradient id="lineFill" x1="0" x2="0" y1="0" y2="1">
              <stop offset="0%" stopColor="#0048d7" stopOpacity="0.25" />
              <stop offset="100%" stopColor="#0048d7" stopOpacity="0.01" />
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
            style={{
              position: "absolute",
              left: `${item.x}%`,
              top: `${Math.max(4, item.y - 9)}%`,
              transform: "translateX(-50%)",
              background: "var(--primary)",
              color: "white",
              padding: "2px 6px",
              borderRadius: "12px",
              fontSize: "10px",
              fontWeight: "800",
              boxShadow: "0 4px 6px rgba(0, 72, 215, 0.2)",
            }}
            title={`${item.label}: ${item.value}`}
          >
            {item.value}
          </span>
        ))}
      </div>
      <div className="chart-axis" style={{ display: "flex", justifyContent: "space-between", padding: "10px 0 0", fontSize: "11px", color: "var(--text-soft)" }}>
        {data.filter((_, index) => data.length <= 12 || index % 4 === 0).map((item) => <span key={item.label}>{item.label}</span>)}
      </div>
    </div>
  );
}

// REST OF FILE UNCHANGED...
function BarList({ title, data = [] }) {
  const max = Math.max(...data.map((item) => item.value), 1);
  return (
    <div className="chart-card" style={{ border: "1px solid var(--line)", borderRadius: "16px", padding: "20px" }}>
      <div className="section-heading" style={{ marginBottom: "16px" }}>
        <h2 style={{ fontSize: "15px", fontWeight: "800" }}>{title}</h2>
      </div>
      <div className="bar-list" style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
        {data.map((item) => (
          <div className="bar-row" key={item.label} style={{ display: "flex", alignItems: "center", gap: "12px" }}>
            <span style={{ flex: "1", fontSize: "13px", fontWeight: "500" }}>{item.label}</span>
            <div style={{ flex: "2", height: "8px", background: "var(--surface-2)", borderRadius: "4px", overflow: "hidden" }}>
              <i style={{ display: "block", height: "100%", width: `${(item.value / max) * 100}%`, background: "var(--primary)", borderRadius: "4px", transition: "width 0.6s ease" }} />
            </div>
            <strong style={{ width: "30px", textAlign: "right", fontSize: "13px", fontWeight: "700" }}>{item.value}</strong>
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
    <div className="chart-card donut-card" style={{ border: "1px solid var(--line)", borderRadius: "16px", padding: "20px", display: "flex", flexDirection: "column", alignItems: "center" }}>
      <div className="section-heading" style={{ alignSelf: "stretch", marginBottom: "16px" }}>
        <h2 style={{ fontSize: "15px", fontWeight: "800" }}>Agendas por município</h2>
      </div>
      <div className="donut" style={{ background: `conic-gradient(${stops})`, width: "160px", height: "160px", borderRadius: "50%", display: "flex", alignItems: "center", justifyContent: "center", position: "relative", boxShadow: "inset 0 0 10px rgba(0,0,0,0.1)" }}>
        <div className="donut-center" style={{ width: "110px", height: "110px", background: "var(--surface)", borderRadius: "50%", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", boxShadow: "0 4px 10px rgba(0,0,0,0.05)" }}>
          <span style={{ fontSize: "24px", fontWeight: "900", color: "var(--text)" }}>{total}</span>
          <small style={{ fontSize: "11px", color: "var(--text-soft)", fontWeight: "600", textTransform: "uppercase" }}>agendas</small>
        </div>
      </div>
      <div className="donut-legend" style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px 12px", width: "100%", marginTop: "20px" }}>
        {data.map((item, index) => (
          <span key={item.label} style={{ fontSize: "11px", display: "flex", alignItems: "center", gap: "6px", color: "var(--text-soft)" }}>
            <i style={{ display: "inline-block", width: "8px", height: "8px", borderRadius: "50%", background: colors[index % colors.length] }} />
            {item.label} {Math.round((item.value / total) * 100)}%
          </span>
        ))}
      </div>
    </div>
  );
}

function Heatmap({ data = [] }) {
  const values = new Map(data.map((item) => [`${item.day}-${item.slot}`, item.total]));
  const max = Math.max(...data.map((item) => item.total), 1);
  const gridTemplateColumns = `34px repeat(${hourSlots.length}, minmax(34px, 1fr))`;
  return (
    <div className="chart-card heatmap-card" style={{ border: "1px solid var(--line)", borderRadius: "16px", padding: "20px" }}>
      <div className="section-heading" style={{ marginBottom: "16px" }}>
        <h2 style={{ fontSize: "15px", fontWeight: "800" }}>Horários mais utilizados</h2>
      </div>
      <div className="heatmap" style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
        <div className="heatmap-header" style={{ display: "grid", gridTemplateColumns, gap: "3px", marginBottom: "6px", fontSize: "10px", fontWeight: "700", color: "var(--text-soft)", textAlign: "center" }}>
          <strong style={{ textAlign: "left" }}>Dia</strong>
          {hourSlots.map((slot) => <small key={slot}>{slot}</small>)}
        </div>
        {weekDays.map((day, dayIndex) => (
          <div className="heatmap-row" key={day} style={{ display: "grid", gridTemplateColumns, gap: "3px", alignItems: "center" }}>
            <strong style={{ fontSize: "12px", fontWeight: "600", color: "var(--text-soft)" }}>{day}</strong>
            {hourSlots.map((slot) => {
              const value = values.get(`${dayIndex}-${slot}`) || 0;
              return (
                <i
                  className={value ? "" : "is-empty"}
                  key={slot}
                  title={`${day} ${slot}: ${value}`}
                  style={{
                    height: "24px",
                    borderRadius: "6px",
                    cursor: "pointer",
                    transition: "all 0.2s ease",
                    backgroundColor: value ? `rgba(0, 72, 215, ${0.15 + (value / max) * 0.75})` : "var(--surface-2)",
                    color: value ? "#fff" : "transparent",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    fontSize: "10px",
                    fontWeight: "800",
                  }}
                >
                  {value || ""}
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
    <div className="chart-card mini-calendar-card" style={{ border: "1px solid var(--line)", borderRadius: "16px", padding: "20px" }}>
      <div className="section-heading" style={{ marginBottom: "16px" }}>
        <div>
          <h2 style={{ fontSize: "15px", fontWeight: "800" }}>Calendário de {monthLabel}</h2>
          <p style={{ fontSize: "12px", color: "var(--text-soft)" }}>Quantidade de agendas por dia.</p>
        </div>
      </div>
      <div className="mini-calendar" style={{ display: "grid", gridTemplateColumns: "repeat(7, 1fr)", gap: "8px" }}>
        {days.map((day) => (
          <button
            key={day.date}
            title={`${formatDateBR(day.date)}: ${day.total} agendas`}
            type="button"
            style={{
              background: "var(--surface-2)",
              border: "1px solid var(--line)",
              borderRadius: "10px",
              padding: "8px 4px",
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              gap: "4px",
              position: "relative",
              cursor: "pointer",
              transition: "transform 0.2s ease, border-color 0.2s ease",
            }}
          >
            <span style={{ fontSize: "12px", fontWeight: "700" }}>{day.day}</span>
            <strong style={{ fontSize: "11px", color: day.total ? "var(--primary)" : "var(--text-soft)" }}>{day.total}</strong>
            <i style={{ display: "block", width: "4px", height: "4px", borderRadius: "50%", background: day.total ? "var(--primary)" : "transparent" }} />
          </button>
        ))}
      </div>
    </div>
  );
}

function MiniCalendarWrap({ calendar }) {
  return <MiniCalendar days={calendar} />;
}

function ActivityPanel({ activity, advanced, materials }) {
  const distributedMaterials = materials?.distributed || { total: 0, items: [] };
  return (
    <aside className="dashboard-side" style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
      <div className="chart-card field-teams-card" style={{ border: "1px solid var(--line)", borderRadius: "16px", padding: "20px" }}>
        <div className="section-heading" style={{ marginBottom: "14px" }}><h2 style={{ fontSize: "15px", fontWeight: "800" }}>Equipes em campo hoje</h2></div>
        <div className="field-team-list" style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
          {(activity?.field_teams || []).length ? (
            activity.field_teams.map((item) => (
              <span key={item.id} style={{ display: "flex", flexDirection: "column", borderBottom: "1px solid var(--line)", paddingBottom: "8px" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <strong style={{ fontSize: "13px" }}>{item.team}</strong>
                  <i style={{ fontSize: "11px", fontStyle: "normal", color: "var(--primary)", fontWeight: "700" }}>{item.time}</i>
                </div>
                <small style={{ fontSize: "11.5px", color: "var(--text-soft)", marginTop: "2px" }}>{item.title} · <span style={{ color: "var(--success)", fontWeight: "600" }}>{statusLabel[item.status]}</span></small>
              </span>
            ))
          ) : (
            <p style={{ color: "var(--text-soft)", fontSize: "13px" }}>Nenhuma equipe em campo hoje.</p>
          )}
        </div>
      </div>
      <div className="chart-card materials-dashboard-card" style={{ border: "1px solid var(--line)", borderRadius: "16px", padding: "20px" }}>
        <div className="section-heading" style={{ marginBottom: "14px" }}>
          <div>
            <h2 style={{ fontSize: "15px", fontWeight: "800", textTransform: "uppercase" }}>Materiais distribuídos</h2>
            <p style={{ color: "var(--text-soft)", fontSize: "12px", fontWeight: "700", margin: "3px 0 0", textTransform: "uppercase" }}>Total consolidado dos relatórios enviados.</p>
          </div>
          <strong style={{ background: "#edf4ff", borderRadius: "10px", color: "#0048d7", fontSize: "20px", padding: "8px 12px" }}>{distributedMaterials.total}</strong>
        </div>
        <div className="advanced-list" style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
          {distributedMaterials.items?.length ? distributedMaterials.items.map((item) => (
            <span key={item.label} style={{ alignItems: "flex-start", display: "flex", justifyContent: "space-between", gap: "12px", fontSize: "13px", fontWeight: "800", lineHeight: 1.25, textTransform: "uppercase" }}>
              <span style={{ color: "var(--text)", flex: "1 1 auto", fontSize: "13px", fontWeight: "800", lineHeight: 1.25, overflowWrap: "anywhere", textTransform: "uppercase" }}>{item.label}</span>
              <strong style={{ color: "var(--primary)", flex: "0 0 auto", fontSize: "13px", fontWeight: "800", lineHeight: 1.25, textAlign: "right" }}>{item.value}</strong>
            </span>
          )) : (
            <p style={{ color: "var(--text-soft)", fontSize: "13px", fontWeight: "800", margin: 0, textTransform: "uppercase" }}>Nenhum material distribuído registrado.</p>
          )}
        </div>
      </div>
      <div className="chart-card advanced-indicators-card" style={{ border: "1px solid var(--line)", borderRadius: "16px", padding: "20px" }}>
        <div className="section-heading" style={{ marginBottom: "14px" }}><h2 style={{ fontSize: "15px", fontWeight: "800" }}>Indicadores avançados</h2></div>
        <div className="advanced-list" style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
          <span style={{ display: "flex", justifyContent: "space-between", fontSize: "13px" }}>Taxa de aprovação <strong style={{ color: "var(--success)" }}>{advanced?.approval_rate ?? 0}%</strong></span>
          <span style={{ display: "flex", justifyContent: "space-between", fontSize: "13px" }}>Taxa de cancelamento <strong style={{ color: "var(--danger)" }}>{advanced?.cancellation_rate ?? 0}%</strong></span>
          <span style={{ display: "flex", justifyContent: "space-between", fontSize: "13px" }}>Tempo médio de aprovação <strong>{advanced?.approval_avg_hours ?? 0}h</strong></span>
          <span style={{ display: "flex", justifyContent: "space-between", fontSize: "13px" }}>Média por usuário <strong>{advanced?.avg_per_user ?? 0}</strong></span>
          <span style={{ display: "flex", justifyContent: "space-between", fontSize: "13px" }}>Dentro do prazo <strong style={{ color: "var(--primary)" }}>{advanced?.sla ?? 0}%</strong></span>
        </div>
      </div>
    </aside>
  );
}

const operationalCardConfig = [
  { key: "estimated_public", title: "P\u00fablico estimado", hint: "Soma prevista das agendas", icon: Users, color: "#00a676", gradient: "linear-gradient(135deg, #00a676, #007a58)" },
  { key: "public_reached", title: "P\u00fablico alcan\u00e7ado", hint: "Informado nos relat\u00f3rios", icon: UserCheck, color: "#6c5ce7", gradient: "linear-gradient(135deg, #6c5ce7, #5345b5)" },
  { key: "scheduled_today", title: "A\u00e7\u00f5es do dia", hint: "Agenda operacional da data", icon: CalendarCheck, color: "#0048d7", gradient: "linear-gradient(135deg, #0048d7, #002d72)" },
  { key: "in_progress", title: "Em andamento", hint: "A\u00e7\u00f5es no hor\u00e1rio atual", icon: PauseCircle, color: "#00a676", gradient: "linear-gradient(135deg, #00a676, #007a58)" },
  { key: "pending_start", title: "Pr\u00f3ximas", hint: "Ainda v\u00e3o acontecer", icon: Clock3, color: "#f6a700", gradient: "linear-gradient(135deg, #f6bd16, #d98b00)" },
  { key: "completed", title: "Conclu\u00eddas", hint: "Com relat\u00f3rio enviado", icon: CheckCheck, color: "#0984e3", gradient: "linear-gradient(135deg, #0984e3, #0057a8)" },
  { key: "pending_reports", title: "Relat\u00f3rios pendentes", hint: "A\u00e7\u00f5es j\u00e1 report\u00e1veis", icon: AlertTriangle, color: "#dc6b16", gradient: "linear-gradient(135deg, #f97316, #c2410c)" },
  { key: "teams_active", title: "Equipes", hint: "Equipes escaladas", icon: Shield, color: "#0048d7", gradient: "linear-gradient(135deg, #0048d7, #002d72)" },
  { key: "chiefs_active", title: "Chefes", hint: "Chefes em opera\u00e7\u00e3o", icon: UserCheck, color: "#0048d7", gradient: "linear-gradient(135deg, #0048d7, #002d72)" },
  { key: "agents_scheduled", title: "Agentes", hint: "Agentes em campo", icon: Users, color: "#0048d7", gradient: "linear-gradient(135deg, #0048d7, #002d72)" },
  { key: "supports_scheduled", title: "Apoios", hint: "Apoios escalados", icon: Users, color: "#0048d7", gradient: "linear-gradient(135deg, #0048d7, #002d72)" },
  { key: "service_orders", title: "OS emitidas", hint: "Ordens de servi\u00e7o", icon: FileText, color: "#0048d7", gradient: "linear-gradient(135deg, #0048d7, #002d72)" },
];

const workforceConfig = [
  { key: "teams_active", label: "Equipes", icon: Shield },
  { key: "chiefs_active", label: "Chefes", icon: UserCheck },
  { key: "agents_scheduled", label: "Agentes", icon: Users },
  { key: "supports_scheduled", label: "Apoios", icon: Users },
  { key: "service_orders", label: "OS emitidas", icon: FileText },
];

const operationStatusStyle = {
  scheduled: { label: "Pr\u00f3xima", color: "#0048d7", bg: "#edf4ff" },
  in_progress: { label: "Em andamento", color: "#007a58", bg: "#e7f8f1" },
  completed: { label: "Conclu\u00edda", color: "#047857", bg: "#dcfce7" },
  cancelled: { label: "Cancelada", color: "#b91c1c", bg: "#fee2e2" },
  pending_report: { label: "Aguardando relat\u00f3rio", color: "#b45309", bg: "#fff7ed" },
  submitted: { label: "Relat\u00f3rio enviado", color: "#1d4ed8", bg: "#dbeafe" },
  pending_approval: { label: "Aguardando aprova\u00e7\u00e3o", color: "#92400e", bg: "#fef3c7" },
};


function SectionCard({ icon: Icon, title, subtitle, children }) {
  return (
    <section style={{ border: "1px solid var(--line)", borderRadius: "16px", background: "var(--surface)", overflow: "hidden", boxShadow: "0 4px 18px rgba(0,0,0,0.025)" }}>
      <header style={{ padding: "20px 22px", borderBottom: "1px solid var(--line)", display: "flex", alignItems: "center", gap: "12px" }}>
        {Icon && <span style={{ width: 36, height: 36, borderRadius: 10, background: "var(--primary)", color: "#fff", display: "inline-flex", alignItems: "center", justifyContent: "center" }}><Icon size={18} /></span>}
        <div>
          <h2 style={{ margin: 0, fontSize: 19, lineHeight: 1.2, fontWeight: 900, color: "var(--text)" }}>{title}</h2>
          {subtitle && <p style={{ margin: "4px 0 0", color: "var(--text-soft)", fontSize: 12.5 }}>{subtitle}</p>}
        </div>
      </header>
      <div style={{ padding: 22 }}>{children}</div>
    </section>
  );
}

function formatInsightCount(count, singular, plural) {
  return `${count} ${count === 1 ? singular : plural}`;
}

function buildOperationalInsights(operations = [], cards = {}) {
  const safeOperations = Array.isArray(operations) ? operations : [];
  if (!safeOperations.length) return [];

  const total = safeOperations.length;
  const completed = safeOperations.filter((item) => item?.operational_status === "completed").length;
  const inProgress = safeOperations.filter((item) => item?.operational_status === "in_progress").length;
  const upcoming = safeOperations.filter((item) => ["scheduled", "pending_approval"].includes(item?.operational_status)).length;
  const cancelled = safeOperations.filter((item) => {
    const status = String(item?.status || "").toUpperCase();
    const operationalStatus = String(item?.operational_status || "").toUpperCase();
    return ["CANCELLED", "CANCELED", "REJECTED", "REFUSED"].includes(status)
      || ["CANCELLED", "CANCELED"].includes(operationalStatus);
  }).length;

  const totalEstimated = safeOperations.reduce((sum, item) => {
    const value = Number(item?.estimated_public || 0);
    return Number.isFinite(value) && value > 0 ? sum + value : sum;
  }, 0);
  const totalReached = safeOperations.reduce((sum, item) => {
    const value = Number(item?.public_reached || 0);
    return Number.isFinite(value) && value > 0 ? sum + value : sum;
  }, 0);

  const withReport = safeOperations.filter((item) => item?.report).length;
  const withoutReport = Math.max(total - withReport, 0);
  const pendingReports = Number(cards?.pending_reports?.value || 0);

  const largestAction = safeOperations.reduce((currentLargest, item) => {
    const reached = Number(item?.public_reached || 0);
    if (!Number.isFinite(reached) || reached <= 0) return currentLargest;
    if (!currentLargest || reached > currentLargest.reached) {
      return {
        name: item?.location || item?.title || item?.type || "Ação sem identificação",
        reached,
      };
    }
    return currentLargest;
  }, null);

  const teamCounts = new Map();
  safeOperations.forEach((item) => {
    const team = String(item?.team || "").trim();
    if (!team || team === "Sem equipe") return;
    teamCounts.set(team, (teamCounts.get(team) || 0) + 1);
  });
  const rankedTeams = [...teamCounts.entries()].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0], "pt-BR"));
  const topTeamCount = rankedTeams[0]?.[1] || 0;
  const topTeams = rankedTeams.filter(([, value]) => value === topTeamCount).map(([team]) => team);

  const actionsWithoutEstimate = safeOperations.filter((item) => {
    const value = Number(item?.estimated_public || 0);
    return !Number.isFinite(value) || value <= 0;
  }).length;
  const actionsWithStaffChanges = safeOperations.filter((item) => Array.isArray(item?.report?.changes_staff) && item.report.changes_staff.length > 0).length;
  const actionsWithAbsences = safeOperations.filter((item) => Number(item?.absence_count || 0) > 0).length;

  const insights = [];

  if (pendingReports > 0) {
    insights.push({
      title: "Relatórios pendentes",
      body: `Existem ${formatInsightCount(pendingReports, "relatório pendente", "relatórios pendentes")} para o período selecionado.`,
    });
  }

  if (cancelled > 0) {
    insights.push({
      title: "Ações canceladas",
      body: `${formatInsightCount(cancelled, "ação foi cancelada e ficou fora da contagem de OS emitidas", "ações foram canceladas e ficaram fora da contagem de OS emitidas")}.`,
    });
  }

  if (actionsWithStaffChanges > 0) {
    insights.push({
      title: "Alterações de efetivo",
      body: `${formatInsightCount(actionsWithStaffChanges, "ação registrou alteração de efetivo", "ações registraram alterações de efetivo")} no período.`,
    });
  }

  if (actionsWithoutEstimate > 0) {
    insights.push({
      title: "Público estimado",
      body: `${formatInsightCount(actionsWithoutEstimate, "ação não informou público estimado", "ações não informaram público estimado")}.`,
    });
  }

  if (withoutReport > 0) {
    insights.push({
      title: "Cobertura de relatórios",
      body: `${formatInsightCount(withoutReport, "ação segue sem relatório", "ações seguem sem relatório")}.`,
    });
  }

  if (actionsWithAbsences > 0) {
    insights.push({
      title: "Faltas registradas",
      body: `${formatInsightCount(actionsWithAbsences, "ação teve falta registrada", "ações tiveram faltas registradas")} na frequência.`,
    });
  }

  if (totalEstimated > 0 && totalReached > 0) {
    const reachedPercentage = Math.round((totalReached / totalEstimated) * 100);
    if (reachedPercentage < 100) {
      insights.push({
        title: "Público alcançado",
        body: `Foram alcançadas ${Number(totalReached).toLocaleString("pt-BR")} pessoas, correspondendo a ${reachedPercentage}% do público estimado.`,
      });
    } else if (reachedPercentage > 100) {
      insights.push({
        title: "Público alcançado",
        body: `Foram alcançadas ${Number(totalReached).toLocaleString("pt-BR")} pessoas, acima do público estimado de ${Number(totalEstimated).toLocaleString("pt-BR")}.`,
      });
    }
  } else if (totalReached > 0) {
    insights.push({
      title: "Público alcançado",
      body: `As ações com relatório registraram ${Number(totalReached).toLocaleString("pt-BR")} pessoas alcançadas.`,
    });
  }

  if (largestAction) {
    insights.push({
      title: "Destaque",
      body: `A ação ${largestAction.name} teve o maior alcance, com ${Number(largestAction.reached).toLocaleString("pt-BR")} pessoas.`,
    });
  }

  if (topTeams.length === 1) {
    insights.push({
      title: "Equipe com maior atuação",
      body: `A equipe ${topTeams[0]} concentrou o maior número de ações do período, com ${formatInsightCount(topTeamCount, "ação", "ações")}.`,
    });
  } else if (topTeams.length > 1 && topTeamCount > 0) {
    insights.push({
      title: "Equipes em destaque",
      body: `Houve empate entre ${topTeams.join(", ")}, com ${formatInsightCount(topTeamCount, "ação", "ações")} cada.`,
    });
  }

  const summaryParts = [];
  if (completed > 0) summaryParts.push(`${formatInsightCount(completed, "concluída", "concluídas")}`);
  if (inProgress > 0) summaryParts.push(`${inProgress} em andamento`);
  if (upcoming > 0) summaryParts.push(`${formatInsightCount(upcoming, "próxima", "próximas")}`);
  insights.push({
    title: "Resumo do período",
    body: summaryParts.length
      ? `O período filtrado teve ${formatInsightCount(total, "ação", "ações")}, com ${summaryParts.join(", ")}.`
      : `O período filtrado teve ${formatInsightCount(total, "ação", "ações")}.`,
  });

  return insights.slice(0, 5);
}

function OperationalCard({ config, data }) {
  const Icon = config.icon;
  return (
    <div style={{ background: "var(--surface)", border: "1px solid var(--line)", borderRadius: "16px", padding: "18px", position: "relative", overflow: "hidden", minHeight: "126px", boxShadow: "0 4px 18px rgba(0,0,0,0.03)" }}>
      <div style={{ position: "absolute", top: -22, right: -22, width: 78, height: 78, borderRadius: "50%", background: config.color, opacity: 0.08 }} />
      <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "14px" }}>
        <span style={{ width: 36, height: 36, borderRadius: 10, display: "inline-flex", alignItems: "center", justifyContent: "center", background: config.gradient, color: "#fff", boxShadow: `0 6px 14px ${config.color}33` }}><Icon size={18} /></span>
        <strong style={{ fontSize: 12, color: "var(--text-soft)", textTransform: "uppercase", letterSpacing: 0.4, lineHeight: 1.2 }}>{config.title}</strong>
      </div>
      <strong style={{ display: "block", fontSize: 32, lineHeight: 1, fontWeight: 900, color: "var(--text)" }}>{Number(data?.value || 0).toLocaleString("pt-BR")}</strong>
      <small style={{ display: "block", marginTop: 8, color: "var(--text-soft)", fontSize: 12 }}>{config.hint}</small>
    </div>
  );
}

function StatusPill({ status }) {
  const style = operationStatusStyle[status] || operationStatusStyle.scheduled;
  return <span style={{ borderRadius: 999, padding: "5px 10px", background: style.bg, color: style.color, fontSize: 11, fontWeight: 900, whiteSpace: "nowrap" }}>{style.label}</span>;
}

function TextList({ label, value }) {
  if (!value || (Array.isArray(value) && !value.length)) return null;
  const values = Array.isArray(value) ? value : [value];
  return (
    <div style={{ display: "grid", gap: 3 }}>
      <strong style={{ fontSize: 12, color: "var(--text-soft)", textTransform: "uppercase" }}>{label}</strong>
      {values.map((item, index) => <span key={`${label}-${index}`} style={{ fontSize: 13, color: "var(--text)" }}>{item}</span>)}
    </div>
  );
}

function OperationDayPanel({ operations = [] }) {
  return (
    <SectionCard icon={MapPin} title={"Operação do dia"} subtitle={"Ações em ordem cronológica, com equipe, efetivo, materiais, público e relatório técnico."}>
      {operations.length ? (
        <div style={{ display: "grid", gap: 14 }}>
          {operations.map((item) => {
            const report = item.report;
            const materialsUsed = [
              ...(report?.materials_removed || []),
              ...(report?.materials_spent || []),
              ...(report?.equipment_materials_distributed || []),
            ];
            const materialsDistributed = [
              ...(report?.distribution_materials_distributed || []),
              ...((report?.actions || []).flatMap((action) => action.distribution_materials || [])),
            ];
            const accessibilityLabel = {
              YES: "Sim",
              NO: "Não",
              PARTIAL: "Parcial",
            }[String(report?.accessibility_conditions_met || "").toUpperCase()] || report?.accessibility_conditions_met;
            return (
              <article key={item.id} style={{ border: "1px solid var(--line)", borderRadius: 16, padding: "16px 18px", background: "var(--surface-2)", display: "grid", gap: 12 }}>
                <div style={{ display: "grid", gridTemplateColumns: "82px minmax(0, 1fr) auto", gap: 14, alignItems: "center" }}>
                  <strong style={{ color: "var(--primary)", fontSize: 16, fontWeight: 900 }}>{item.time || "--:--"}</strong>
                  <div style={{ minWidth: 0 }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
                      <strong style={{ color: "var(--text)", fontSize: 15, fontWeight: 900 }}>{item.type || item.title}</strong>
                      {item.service_order_number && <span style={{ color: "var(--text-soft)", fontSize: 12, fontWeight: 800 }}>OS {item.service_order_number}</span>}
                    </div>
                    <p style={{ margin: "4px 0 0", color: "var(--text)", fontSize: 13.5, fontWeight: 700 }}>{item.location} <span aria-hidden="true">-</span> {item.municipality}</p>
                    <small style={{ color: "var(--text-soft)", display: "block", marginTop: 4 }}>Equipe {item.team} <span aria-hidden="true">-</span> Chefe {item.chief}</small>
                  </div>
                  <StatusPill status={item.operational_status} />
                </div>

                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: 12, paddingTop: 8, borderTop: "1px solid var(--line)" }}>
                  <TextList label="Agentes em campo" value={item.agents_names} />
                  <TextList label="Apoios" value={item.supports_names} />
                  <TextList label={"P\u00fablico estimado"} value={item.estimated_public ? `${Number(item.estimated_public).toLocaleString("pt-BR")} pessoas` : "N\u00e3o informado"} />
                  <TextList label={"P\u00fablico alcan\u00e7ado"} value={item.public_reached ? `${Number(item.public_reached).toLocaleString("pt-BR")} pessoas` : "Aguardando relat\u00f3rio"} />
                </div>

                {item.absences?.length ? (
                  <div style={{ border: "1px solid #fecaca", background: "#fef2f2", color: "#7f1d1d", borderRadius: 12, padding: "12px 14px", display: "grid", gap: 8 }}>
                    <strong style={{ fontSize: 13, textTransform: "uppercase" }}>{"Faltas registradas na frequ\u00eancia"}</strong>
                    {item.absences.map((absence, index) => (
                      <div key={`${item.id}-absence-${index}`} style={{ fontSize: 13, display: "grid", gap: 3 }}>
                        <span><strong>{absence.name}</strong> {absence.role ? `(${absence.role})` : ""}</span>
                        {absence.reason && <span>Justificativa: {absence.reason}</span>}
                      </div>
                    ))}
                  </div>
                ) : null}

                {report ? (
                  <div style={{ display: "grid", gap: 12, padding: 12, borderRadius: 12, background: "var(--surface)", border: "1px solid var(--line)" }}>
                    <strong style={{ color: "var(--primary)", fontSize: 13, textTransform: "uppercase" }}>{"Informa\u00e7\u00f5es digitadas no relat\u00f3rio"}</strong>
                    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: 12 }}>
                      <TextList label="Efetivo PCD" value={report.education_pcd} />
                      <TextList label="Agentes informados" value={report.education_agents} />
                      <TextList label={"Altera\u00e7\u00f5es de efetivo"} value={report.changes_staff} />
                      <TextList label={"Materiais de apoio/din\u00e2micas utilizados"} value={materialsUsed} />
                      <TextList label={"Materiais distribu\u00eddos"} value={materialsDistributed} />
                      <TextList label="Viaturas" value={report.cars} />
                      <TextList label="Acessibilidade" value={accessibilityLabel} />
                      <TextList label="Contato recebido" value={report.contact_received} />
                      <TextList label={"Institui\u00e7\u00e3o/local informado"} value={report.occurrence_observation} />
                      <TextList label={"Observa\u00e7\u00f5es gerais"} value={report.general_observations} />
                    </div>
                    {report?.has_exceptional_occurrence === true ? (
                      <div style={getExceptionalOccurrenceStyle(report.exceptional_occurrence_impact)}>
                        <strong style={{ fontSize: 13, textTransform: "uppercase" }}>{"Ocorrência excepcional"}</strong>
                        <div style={{ fontSize: 13 }}>
                          <strong>Tipo:</strong>{" "}
                          {exceptionalOccurrenceTypeLabels[report.exceptional_occurrence_type]
                            || report.exceptional_occurrence_type
                            || "-"}
                        </div>
                        <div style={{ fontSize: 13 }}>
                          <strong>Impacto:</strong>{" "}
                          {exceptionalOccurrenceImpactLabels[report.exceptional_occurrence_impact]
                            || report.exceptional_occurrence_impact
                            || "-"}
                        </div>
                        {report.exceptional_occurrence_description ? (
                          <div style={{ display: "grid", gap: 4, fontSize: 13 }}>
                            <strong>Descrição:</strong>
                            <div style={{ whiteSpace: "pre-wrap" }}>{report.exceptional_occurrence_description}</div>
                          </div>
                        ) : null}
                        {report.exceptional_occurrence_actions_taken ? (
                          <div style={{ display: "grid", gap: 4, fontSize: 13 }}>
                            <strong>Providências adotadas:</strong>
                            <div style={{ whiteSpace: "pre-wrap" }}>{report.exceptional_occurrence_actions_taken}</div>
                          </div>
                        ) : null}
                      </div>
                    ) : null}
                    {report.actions?.length ? (
                      <div style={{ display: "grid", gap: 8 }}>
                        <strong style={{ fontSize: 12, color: "var(--text-soft)", textTransform: "uppercase" }}>{"A\u00e7\u00f5es relatadas"}</strong>
                        {report.actions.map((action, index) => (
                          <div key={`${item.id}-action-${index}`} style={{ border: "1px solid var(--line)", borderRadius: 10, padding: 10 }}>
                            <strong style={{ fontSize: 13 }}>{action.type || `A\u00e7\u00e3o ${index + 1}`}</strong>
                            <small style={{ display: "block", color: "var(--text-soft)", marginTop: 3 }}>{action.place || "Local n\u00e3o informado"} - {action.start_time || "--"} {"\u00e0s"} {action.final_hour || "--"} - {Number(action.reported_approaches || action.approached_actions || action.approach || 0).toLocaleString("pt-BR")} abordagens</small>
                                                        {action.support_materials?.length ? <small style={{ display: "block", color: "var(--text-soft)", marginTop: 3 }}>Materiais de apoio/dinâmicas: {action.support_materials.join(", ")}</small> : null}
                            {action.distribution_materials?.length ? <small style={{ display: "block", color: "var(--text-soft)", marginTop: 3 }}>Materiais distribuídos: {action.distribution_materials.join(", ")}</small> : null}
                          </div>
                        ))}
                      </div>
                    ) : null}
                  </div>
                ) : null}
              </article>
            );
          })}
        </div>
      ) : (
        <p style={{ margin: 0, color: "var(--text-soft)", fontWeight: 700 }}>{"Nenhuma a\u00e7\u00e3o programada para hoje."}</p>
      )}
    </SectionCard>
  );
}

function WorkforcePanel({ cards = {} }) {
  return (
    <SectionCard icon={Users} title="Efetivo do dia" subtitle="Recursos operacionais vinculados às ações de hoje.">
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(120px, 1fr))", gap: 12 }}>
        {workforceConfig.map((item) => {
          const Icon = item.icon;
          return (
            <div key={item.key} style={{ border: "1px solid var(--line)", borderRadius: 12, padding: "14px", background: "var(--surface-2)", display: "flex", flexDirection: "column", gap: 8 }}>
              <span style={{ width: 30, height: 30, borderRadius: 8, background: "var(--primary)", color: "#fff", display: "inline-flex", alignItems: "center", justifyContent: "center" }}><Icon size={15} /></span>
              <strong style={{ fontSize: 24, lineHeight: 1, color: "var(--text)", fontWeight: 900 }}>{Number(cards?.[item.key]?.value || 0).toLocaleString("pt-BR")}</strong>
              <small style={{ color: "var(--text-soft)", fontWeight: 800 }}>{item.label}</small>
            </div>
          );
        })}
      </div>
    </SectionCard>
  );
}


export default function DashboardPage() {
  const [dashboard, setDashboard] = useState(null);
  const [filters, setFilters] = useState(emptyFilters);
  const [municipalities, setMunicipalities] = useState([]);
  const [teams, setTeams] = useState([]);
  const [regions, setRegions] = useState([]);
  const [chartRange, setChartRange] = useState("Mês");
  const [loading, setLoading] = useState(true);
  const [refreshTick, setRefreshTick] = useState(0);
  const [error, setError] = useState("");
  
  useEffect(() => {
    Promise.all([
      api("/municipalities/?page_size=500"),
      api("/regions/?page_size=200"),
      api("/teams/?page_size=200")
    ]).then(([munData, regData, teamData]) => {
      setMunicipalities(munData.results || munData);
      setRegions(regData.results || regData);
      const uniqueTeams = Array.from(
        new Map(
          (teamData.results || teamData)
            .filter((item) => item.is_active !== false)
            .map((item) => {
              const normalizedName = String(item.name || "").trim().toUpperCase();
              return [
                normalizedName,
                {
                  ...item,
                  name: normalizedName,
                },
              ];
            })
            .filter(([name]) => name)
        ).values()
      ).sort((a, b) => a.name.localeCompare(b.name, "pt-BR"));

      setTeams(uniqueTeams);
    });
  }, []);

  const loadDashboardData = () => {
    setLoading(true);
    setError("");
    const params = new URLSearchParams(Object.entries(filters).filter(([, value]) => value)).toString();
    api(`/agendas/dashboard/${params ? `?${params}` : ""}`)
      .then(setDashboard)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadDashboardData();
  }, [filters, refreshTick]);

  useEffect(() => {
    const interval = setInterval(() => setRefreshTick((current) => current + 1), 60000);
    return () => clearInterval(interval);
  }, []);

  const updateFilter = (field, value) => {
    if (field === "date") {
      setChartRange("");
      setFilters((current) => ({ ...current, date: value, chart_group: "" }));
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
      const mondayOffset = (today.getDay() + 6) % 7;
      start.setDate(today.getDate() - mondayOffset);
      end.setTime(start.getTime());
      end.setDate(start.getDate() + 6);
    } else if (range === chartFilters[2]) {
      start.setDate(1);
      end.setTime(start.getTime());
      end.setMonth(start.getMonth() + 1, 0);
    } else if (range === chartFilters[3]) {
      start.setMonth(0, 1);
      end.setMonth(11, 31);
    }

    setFilters((current) => ({
      ...current,
      date: dateToInputValue(start),
      chart_group: "",
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

  const { user } = useAuth();
  const isModerator = user?.is_superuser || user?.role === "ADMIN" || user?.role === "MANAGER";

  return (
    <section className="page dashboard-page">
      <div className="dashboard-hero" style={{ background: "linear-gradient(135deg, #001338 0%, #002d72 100%)", padding: "28px", borderRadius: "16px", color: "#ffffff", marginBottom: "24px", display: "flex", justifyContent: "space-between", alignItems: "center", border: "1px solid rgba(255,255,255,0.08)", boxShadow: "0 8px 32px 0 rgba(0, 19, 56, 0.15)" }}>
        <div>
          <span style={{ fontSize: "11px", fontWeight: "800", textTransform: "uppercase", letterSpacing: "1.5px", color: "#f6bd16", opacity: 0.95, display: "block", marginBottom: "2px" }}>Visão operacional</span>
          <div style={{ display: "flex", alignItems: "center", gap: "12px", flexWrap: "wrap" }}>
            <h1 style={{ color: "#ffffff", fontSize: "38px", fontWeight: "900", margin: "4px 0", lineHeight: 1 }}>Dashboard</h1>
            {isModerator && dashboard?.pending_moderation_count > 0 && (
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
                {dashboard.pending_moderation_count} avaliações pendentes
              </span>
            )}
          </div>
          <p style={{ margin: 0, color: "#d2e1ff", opacity: 0.9, fontSize: "15px", marginTop: "8px" }}>SISTEMA INTEGRADO DA EDUCAÇÃO - OPERAÇÃO LEI SECA</p>
        </div>
        <div style={{ display: "flex", gap: "12px", alignItems: "center" }}>
          <div className="hero-search" style={{ background: "rgba(255,255,255,0.12)", border: "1px solid rgba(255,255,255,0.22)", borderRadius: "10px", display: "flex", alignItems: "center", padding: "0 12px" }}>
            <Search size={18} color="#ffffff" style={{ opacity: 0.85 }} />
            <input placeholder="Pesquisar agenda, local..." value={filters.q} onChange={(event) => updateFilter("q", event.target.value)} style={{ color: "#ffffff", background: "transparent", border: "none", outline: "none", minHeight: "40px", paddingLeft: "8px" }} />
          </div>
          <button className="secondary export-link" onClick={(e) => handleExport("pdf", e)} style={{ height: "42px", padding: "0 18px", display: "inline-flex", alignItems: "center", gap: "8px", borderRadius: "10px", fontWeight: "800", fontSize: "13px", background: "#ffffff", color: "#001338", border: "none", cursor: "pointer", boxShadow: "0 4px 12px rgba(0,0,0,0.15)", transition: "transform 0.2s ease" }} type="button">
            <Download size={16} /> Exportar
          </button>
        </div>
      </div>


      <div className="global-filters" style={{ border: "1px solid var(--line)", background: "var(--surface)", borderRadius: "14px", padding: "16px", display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))", gap: "16px", marginBottom: "24px", alignItems: "end" }}>
        <label className="filter-field" style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
          <span style={{ fontSize: "11px", fontWeight: "700", color: "var(--text-soft)", textTransform: "uppercase" }}>Data</span>
          <input type="date" value={filters.date} onChange={(event) => updateFilter("date", event.target.value)} style={{ borderRadius: "8px", border: "1px solid var(--line)", height: "36px", padding: "0 10px", fontSize: "12.5px", width: "100%" }} />
        </label>
        <label className="filter-field" style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
          <span style={{ fontSize: "11px", fontWeight: "700", color: "var(--text-soft)", textTransform: "uppercase" }}>{"Institui\u00e7\u00e3o"}</span>
          <input type="text" placeholder={"Nome da institui\u00e7\u00e3o"} value={filters.institution} onChange={(event) => updateFilter("institution", event.target.value)} style={{ borderRadius: "8px", border: "1px solid var(--line)", height: "36px", padding: "0 10px", fontSize: "12.5px", width: "100%" }} />
        </label>
        <label className="filter-field" style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
          <span style={{ fontSize: "11px", fontWeight: "700", color: "var(--text-soft)", textTransform: "uppercase" }}>Município</span>
          <select value={filters.municipality || ""} onChange={(event) => updateFilter("municipality", event.target.value)} style={{ borderRadius: "8px", border: "1px solid var(--line)", height: "36px", padding: "0 10px", fontSize: "12.5px", width: "100%" }}><option value="">Todos</option>{municipalities.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select>
        </label>
        <label className="filter-field" style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
          <span style={{ fontSize: "11px", fontWeight: "700", color: "var(--text-soft)", textTransform: "uppercase" }}>Equipe</span>
          <select value={filters.team || ""} onChange={(event) => updateFilter("team", event.target.value)} style={{ borderRadius: "8px", border: "1px solid var(--line)", height: "36px", padding: "0 10px", fontSize: "12.5px", width: "100%" }}><option value="">Todas</option>{teams.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select>
        </label>        <label className="filter-field" style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
          <span style={{ fontSize: "11px", fontWeight: "700", color: "var(--text-soft)", textTransform: "uppercase" }}>OS</span>
          <input type="text" placeholder="Ex: 2610" value={filters.service_order} onChange={(event) => updateFilter("service_order", event.target.value.replace(/\D/g, ""))} style={{ borderRadius: "8px", border: "1px solid var(--line)", height: "36px", padding: "0 10px", fontSize: "12.5px", width: "100%" }} />
        </label>
        <button className="secondary" type="button" onClick={() => { setFilters(emptyFilters); setChartRange(""); }} style={{ borderRadius: "8px", height: "36px", width: "100%", fontWeight: "600", fontSize: "13px" }}>Limpar</button>
      </div>

      {loading ? (
        <div className="dashboard-skeleton" style={{ minHeight: "400px", display: "flex", gap: "20px", alignItems: "center", justifyContent: "center" }}>
          <div className="spinner" style={{ width: "40px", height: "40px", border: "4px solid var(--surface-2)", borderTopColor: "var(--primary)", borderRadius: "50%", animation: "spin 1s linear infinite" }} />
          <span style={{ fontSize: "14px", color: "var(--text-soft)", fontWeight: "600" }}>Carregando dados operacionais...</span>
        </div>
      ) : error ? (
        <div className="alert">Não foi possível carregar o Dashboard: {error}</div>
      ) : (
        <>
          <div className="metric-grid operational-summary-grid" style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: "16px", marginBottom: "24px" }}>
            {operationalCardConfig.map((config) => (
              <OperationalCard config={config} data={dashboard?.operations?.cards?.[config.key]} key={config.key} />
            ))}
          </div>

          <div style={{ display: "grid", gap: "24px" }}>
            <SectionCard icon={Activity} title={"Insights autom\u00e1ticos"} subtitle={"Leitura r\u00e1pida para gest\u00e3o"}>
              {(() => {
                const operations = dashboard?.operations?.field_operations || [];
                const cards = dashboard?.operations?.cards || {};
                const insights = buildOperationalInsights(operations, cards);

                if (!insights.length) {
                  return (
                    <p style={{ margin: 0, color: "var(--text-soft)", fontWeight: 700 }}>
                      N\u00e3o h\u00e1 dados suficientes para gerar insights para os filtros selecionados.
                    </p>
                  );
                }

                return (
                  <div style={{ display: "grid", gap: "14px" }}>
                    {insights.map((insight) => (
                      <div key={insight.title} style={{ border: "1px solid var(--line)", borderRadius: 12, padding: "14px 16px", background: "var(--surface-2)", display: "grid", gap: 6 }}>
                        <strong style={{ fontSize: 12, color: "var(--text-soft)", textTransform: "uppercase" }}>{insight.title}</strong>
                        <p style={{ margin: 0, color: "var(--text)", fontSize: 14, lineHeight: 1.5 }}>{insight.body}</p>
                      </div>
                    ))}
                  </div>
                );
              })()}
            </SectionCard>
            <OperationDayPanel operations={dashboard?.operations?.field_operations || []} />
            <div style={{ marginTop: "24px" }}>
              <MiniCalendar days={dashboard?.calendar || []} />
            </div>
          </div>
        </>
      )}
    </section>
  );
}






