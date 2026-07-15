import {
  CalendarCheck,
  CalendarClock,
  CheckCircle2,
  CheckCheck,
  Clock3,
  Download,
  PauseCircle,
  Search,
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
const firstDay = formatLocalISODate(new Date(today.getFullYear(), today.getMonth(), 1));
const lastDay = formatLocalISODate(new Date(today.getFullYear(), today.getMonth() + 1, 0));

const emptyFilters = {
  q: "",
  date_from: firstDay,
  date_to: lastDay,
  status: "APPROVED",
  municipality: "",
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

export default function DashboardPage() {
  const [dashboard, setDashboard] = useState(null);
  const [filters, setFilters] = useState(emptyFilters);
  const [municipalities, setMunicipalities] = useState([]);
  const [regions, setRegions] = useState([]);
  const [chartRange, setChartRange] = useState("Mês");
  const [loading, setLoading] = useState(true);
  const [refreshTick, setRefreshTick] = useState(0);
  const [error, setError] = useState("");
  
  useEffect(() => {
    Promise.all([
      api("/municipalities/?page_size=500"),
      api("/regions/?page_size=200")
    ]).then(([munData, regData]) => {
      setMunicipalities(munData.results || munData);
      setRegions(regData.results || regData);
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


      <div className="global-filters" style={{ border: "1px solid var(--line)", background: "var(--surface)", borderRadius: "14px", padding: "16px", display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(130px, 1fr))", gap: "16px", marginBottom: "24px" }}>
        <label className="filter-field" style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
          <span style={{ fontSize: "11px", fontWeight: "700", color: "var(--text-soft)", textTransform: "uppercase" }}>De</span>
          <input type="date" value={filters.date_from} onChange={(event) => updateFilter("date_from", event.target.value)} style={{ borderRadius: "8px", border: "1px solid var(--line)", height: "36px", padding: "0 10px", fontSize: "12.5px", width: "100%" }} />
        </label>
        <label className="filter-field" style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
          <span style={{ fontSize: "11px", fontWeight: "700", color: "var(--text-soft)", textTransform: "uppercase" }}>Até</span>
          <input type="date" value={filters.date_to} onChange={(event) => updateFilter("date_to", event.target.value)} style={{ borderRadius: "8px", border: "1px solid var(--line)", height: "36px", padding: "0 10px", fontSize: "12.5px", width: "100%" }} />
        </label>
        <label className="filter-field" style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
          <span style={{ fontSize: "11px", fontWeight: "700", color: "var(--text-soft)", textTransform: "uppercase" }}>Status</span>
          <select value={filters.status} onChange={(event) => updateFilter("status", event.target.value)} style={{ borderRadius: "8px", border: "1px solid var(--line)", height: "36px", padding: "0 10px", fontSize: "12.5px", width: "100%" }}>
            <option value="">Todos os status</option>
            <option value="PENDING">Pendente</option>
            <option value="APPROVED">Aprovada</option>
            <option value="CANCELLED">Cancelada</option>
          </select>
        </label>
        <label className="filter-field" style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
          <span style={{ fontSize: "11px", fontWeight: "700", color: "var(--text-soft)", textTransform: "uppercase" }}>Região</span>
          <select value={filters.region} onChange={(event) => updateFilter("region", event.target.value)} style={{ borderRadius: "8px", border: "1px solid var(--line)", height: "36px", padding: "0 10px", fontSize: "12.5px", width: "100%" }}>
            <option value="">Todas as regiões</option>
            {regions.map((region) => <option key={region.id} value={region.id}>{region.name}</option>)}
          </select>
        </label>
        <label className="filter-field" style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
          <span style={{ fontSize: "11px", fontWeight: "700", color: "var(--text-soft)", textTransform: "uppercase" }}>Município</span>
          <select value={filters.municipality} onChange={(event) => updateFilter("municipality", event.target.value)} style={{ borderRadius: "8px", border: "1px solid var(--line)", height: "36px", padding: "0 10px", fontSize: "12.5px", width: "100%" }}>
            <option value="">Todos os municípios</option>
            {municipalities.map((municipality) => <option key={municipality.id} value={municipality.id}>{municipality.name}</option>)}
          </select>
        </label>
        <div style={{ display: "flex", alignItems: "flex-end" }}>
          <button className="secondary" type="button" onClick={() => { setFilters(emptyFilters); setChartRange(chartFilters[2]); }} style={{ borderRadius: "8px", height: "36px", width: "100%", fontWeight: "600", fontSize: "13px" }}>Limpar</button>
        </div>
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
          <div className="metric-grid" style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(130px, 1fr))", gap: "16px", marginBottom: "24px" }}>
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
          <ChiefFillingsMetrics data={dashboard?.chief_fillings || {}} />

          <div className="dashboard-layout" style={{ display: "grid", gap: "24px" }}>
            <div className="dashboard-main" style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
              <div className="chart-card" style={{ border: "1px solid var(--line)", borderRadius: "16px", padding: "20px", position: "relative" }}>
                <div className="chart-filter-tabs" style={{ position: "absolute", top: "20px", right: "20px", display: "flex", gap: "4px", background: "var(--surface-2)", padding: "2px", borderRadius: "8px" }}>
                  {chartFilters.map((item) => (
                    <button
                      className={chartRange === item ? "active" : ""}
                      key={item}
                      onClick={() => applyChartRange(item)}
                      type="button"
                      style={{
                        padding: "6px 12px",
                        fontSize: "12.5px",
                        borderRadius: "6px",
                        border: "none",
                        background: chartRange === item ? "var(--surface)" : "transparent",
                        color: chartRange === item ? "var(--primary)" : "var(--text-soft)",
                        fontWeight: "700",
                        cursor: "pointer",
                        boxShadow: chartRange === item ? "0 2px 4px rgba(0,0,0,0.05)" : "none"
                      }}
                    >
                      {item}
                    </button>
                  ))}
                </div>
                <LineChart data={dashboard?.series?.daily || []} />
              </div>
              <div className="analytics-grid" style={{ display: "grid", gap: "24px" }}>
                <BarList title="Ações por equipe" data={dashboard?.bars?.by_team_actions || []} />
                <BarList title="Ações por bairro" data={dashboard?.bars?.by_neighborhood || []} />
                <DonutChart data={dashboard?.donut || []} />
                <Heatmap data={dashboard?.heatmap || []} />
              </div>
              <div className="analytics-grid bottom" style={{ display: "grid", gap: "24px" }}>
                <MiniCalendar days={dashboard?.calendar || []} />
              </div>
            </div>
            <ActivityPanel activity={dashboard?.activity} advanced={dashboard?.advanced} materials={dashboard?.materials} />
          </div>
        </>
      )}
    </section>
  );
}
