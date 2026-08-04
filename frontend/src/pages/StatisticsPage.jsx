import { useEffect, useMemo, useRef, useState } from "react";
import { Activity, AlertTriangle, ArrowRight, BarChart3, BookOpen, Building2, CalendarDays, Download, FileImage, FileSpreadsheet, Filter, Lightbulb, MapPin, Printer, TrendingDown, TrendingUp, Users, X } from "lucide-react";
import { Bar, CartesianGrid, ComposedChart, LabelList, Legend, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { toPng } from "html-to-image";
import { api } from "../api/client.js";
import leiSecaLogo from "../assets/operacao-lei-seca-logo.png";
import { formatLocalISODate } from "../utils/date.js";
import "./StatisticsPage.css";
import { streetActionTypeLabel } from "../utils/streetActionTypes.js";

const MIN_DATE = "2026-07-01";
const COLORS = ["#0048d7", "#059669", "#dc2626", "#7c3aed", "#ea580c", "#db2777", "#0891b2", "#ca8a04", "#64748b", "#16a34a"];
const weekDays = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"];
const hourSlots = ["08:00", "09:00", "10:00", "11:00", "12:00", "13:00", "14:00", "15:00", "16:00", "17:00", "18:00", "19:00", "20:00", "21:00"];
const number = (value) => Number(value || 0).toLocaleString("pt-BR", { maximumFractionDigits: 1 });
const integer = (value) => Number(value || 0).toLocaleString("pt-BR", { maximumFractionDigits: 0 });
const iso = (value) => value instanceof Date ? formatLocalISODate(value) : value;
const clampStart = (value) => !value || value < MIN_DATE ? MIN_DATE : value;
const queryString = (values) => new URLSearchParams(Object.entries(values).filter(([, value]) => value !== "" && value != null)).toString();
const text = {
  publicReached: "Público alcançado", futurePublic: "Público previsto das próximas agendas", reportsApproved: "Realizado nos relatórios aprovados",
  futureHint: "Agendas ainda sem produção concluída", lectures: "Palestras", street: "Ações de rua", materials: "Materiais distribuídos",
  comics: "Revistinhas distribuídas", internal: "Solicitações internas", public: "Solicitações públicas", internalHint: "Agendas criadas pela equipe",
  publicHint: "Solicitações recebidas pelo formulário", noData: "Sem dados para os filtros selecionados.", notInformed: "Não informado",
};
const KPI_DEFS = [
  ["AUDIENCE - Geral", text.publicReached, Users, COLORS[0], text.reportsApproved],
  ["FUTURE_PUBLIC", text.futurePublic, Users, COLORS[1], text.futureHint],
  ["LECTURES - Geral", text.lectures, BarChart3, COLORS[3], "Relatórios aprovados de palestras"],
  ["STREET_ACTIONS - Geral", text.street, Activity, COLORS[4], "Relatórios aprovados de ações de rua"],
  ["MATERIAL - Geral", text.materials, BookOpen, COLORS[5], "Total entregue"],
  ["MATERIAL - Soprinho", text.comics, BookOpen, COLORS[7], "Soprinho"],
  ["INTERNAL_REQUESTS", text.internal, Building2, COLORS[0], text.internalHint],
  ["PUBLIC_REQUESTS", text.public, Users, COLORS[1], text.publicHint],
];
const HISTORICAL_ROWS = [
  ["AUDIENCE - Geral", "Público total"], ["AUDIENCE - PALESTRAS", "Público em palestras"], ["AUDIENCE - ACOES", "Público em ações"],
  ["LECTURES - Geral", "Palestra"], ["ACTION - Empresa", "Empresa"], ["ACTION - Escola", "Escola"], ["ACTION - Universidade", "Universidade"],
  ["STREET_ACTIONS - Geral", "Ações"], ["ACTION - Bares", "Bares/Restaurantes"], ["ACTION - Ped\u00e1gio", "Pedágio"], ["ACTION - Pra\u00e7as Esportivas", "Praças Esportivas"],
  ["ACTION - Praia", "Praia"], ["ACTION - Eventos", "Eventos"], ["ACTION - Shopping", "Shopping/Centro Comerciais"], ["ACTION - Pra\u00e7as/Parques P\u00fablicos", "Praças/Parques Públicos"], ["ACTION - Pontos tur\u00edsticos", "Pontos Tur\u00edsticos"],
  ["MATERIAL - Geral", "Materiais de divulgação"], ["MATERIAL - Soprinho", "Revistinha Soprinho"],
];
function Empty({ children = text.noData }) { return <div className="stats-empty">{children}</div>; }
function Section({ icon: Icon, title, subtitle, children, actions, className = "" }) { return <section className={`stats-panel ${className}`}><header className="stats-panel-header"><div className="stats-panel-title"><span className="stats-icon"><Icon size={17}/></span><div><h2>{title}</h2>{subtitle && <p>{subtitle}</p>}</div></div>{actions && <div className="stats-panel-actions">{actions}</div>}</header><div className="stats-panel-body">{children}</div></section>; }
function MetricCard({ definition, summary, previous, comparison }) { const [key, label, Icon, color, hint] = definition; const value = Number(summary?.[key] || 0); const prior = Number(previous?.[key] || 0); const pct = comparison?.[key]?.percentage; const Trend = pct < 0 ? TrendingDown : TrendingUp; return <article className="stats-kpi" style={{ "--kpi": color }}><div className="stats-kpi-top"><span className="stats-kpi-icon"><Icon size={18}/></span><span>{label}</span></div><div className="stats-kpi-value">{number(value)}</div><div className={`stats-kpi-delta ${pct < 0 ? "is-down" : "is-up"}`}><Trend size={14}/>{pct == null ? (value ? "Novo" : "0,0%") : `${pct >= 0 ? "+" : ""}${pct.toFixed(1)}%`} <span>vs. {number(prior)}</span></div>{hint && <small>{hint}</small>}</article>; }
function MiniCard({ label, value, hint, icon: Icon = BarChart3, tone = COLORS[0] }) { return <div className="stats-mini-card"><span style={{ background: tone }}><Icon size={15}/></span><strong>{number(value)}</strong><small>{label}</small>{hint && <em>{hint}</em>}</div>; }
function ExecutiveBar({ rows, maxRows = 12 }) { const visible = (rows || []).filter(row => Number(row.actions || 0) > 0 || Number(row.audience || 0) > 0).slice(0, maxRows); if (!visible.length) return <Empty/>; const total = visible.reduce((sum, row) => sum + Number(row.actions || 0), 0) || 1; const max = Math.max(...visible.map(row => Number(row.actions || 0)), 1); return <div className="stats-exec-bars">{visible.map((row, index) => { const pct = Number(row.actions || 0) / total * 100; return <button key={`${row.label}-${index}`} onClick={row.onClick} className="stats-exec-bar"><span className="stats-exec-label"><b>{row.label}</b><small>{`${integer(row.actions)} ${"ações"} ${"•"} ${integer(row.audience)} pessoas ${"•"} ${pct.toFixed(1)}%`}</small></span><i><em style={{ width: `${Math.max(3, Number(row.actions || 0) / max * 100)}%`, background: row.color || COLORS[index % COLORS.length] }}/></i></button>; })}</div>; }
function UsageHeatmap({ data = [] }) {
  const totals = data.reduce((acc, item) => {
    const key = `${item.day}-${item.slot}`;
    acc[key] = (acc[key] || 0) + Number(item.total || 0);
    return acc;
  }, {});
  const values = new Map(Object.entries(totals));
  const max = Math.max(...Object.values(totals), 1);
  const gridTemplateColumns = `34px repeat(${hourSlots.length}, minmax(34px, 1fr))`;
  return <div className="stats-dashboard-heatmap"><div className="heatmap"><div className="heatmap-header" style={{ gridTemplateColumns }}><strong>Dia</strong>{hourSlots.map(slot => <small key={slot}>{slot}</small>)}</div>{weekDays.map((day, dayIndex) => <div className="heatmap-row" key={day} style={{ gridTemplateColumns }}><strong>{day}</strong>{hourSlots.map(slot => { const value = values.get(`${dayIndex}-${slot}`) || 0; return <i className={value ? "" : "is-empty"} key={slot} title={`${day} ${slot}: ${value}`} style={{ backgroundColor: value ? `rgba(0, 72, 215, ${0.15 + (value / max) * 0.75})` : "var(--surface-2)" }}>{value || ""}</i>; })}</div>)}</div></div>;
}
function Ranking({ rows, nameKey }) { const visible = (rows || []).filter(row => Number(row.actions || 0) > 0 || Number(row.audience || 0) > 0).sort((a, b) => Number(b.actions || 0) - Number(a.actions || 0) || Number(b.audience || 0) - Number(a.audience || 0)); if (!visible.length) return <Empty/>; const max = Math.max(...visible.map(row => Number(row.actions || 0)), 1); return <div className="stats-ranking">{visible.map((row, index) => <div className="stats-rank-row" key={`${row[nameKey]}-${index}`}><b>{index + 1}</b><span>{row[nameKey] || text.notInformed}</span><div><i style={{ width: `${Number(row.actions || 0) / max * 100}%` }}/></div><strong>{number(row.actions)}</strong><small>{`${number(row.audience)} ${"público"}`}</small></div>)}</div>; }
const parseExpected = (...values) => { for (const value of values) { const raw = String(value ?? "").trim(); if (!raw) continue; const nums = raw.match(/\d+/g)?.map(Number); if (nums?.length) return Math.max(...nums); } return 0; };
const cleanLabel = (value) => String(value || "").trim() || text.notInformed;
const ageGroupLabel = (value) => {
  const label = String(value || "").trim();
  const normalized = label.toLowerCase();
  if (!label || normalized === "adulto" || normalized === "n\u00e3o informado" || normalized === "nao informado") return "";
  return label;
};
const ADMINISTRATIVE_DEMAND_LABELS = {
  TRAVEL: "Deslocamento de viagem",
  INTERVIEW: "Entrevista",
  MEETING: "Reunião",
};
const requesterTypeLabel = (value) => {
  const label = String(value || "").trim();
  const normalized = label.toLowerCase();
  if (!label) return "";
  let base = "";
  if (normalized.includes("institui")) base = "Institui\u00e7\u00e3o de Ensino";
  else if (normalized.includes("empresa") || normalized.includes("\u00f3rg\u00e3o") || normalized.includes("orgao")) base = "Empresa/\u00d3rg\u00e3o";
  else if (normalized.includes("organiza") && normalized.includes("evento")) base = "Organiza\u00e7\u00e3o de evento";
  else if (normalized.includes("a\u00e7\u00e3o de rua") || normalized.includes("acao de rua")) base = "A\u00e7\u00e3o de Rua";
  if (!base) return "";
  if (normalized.includes("privado")) return `${base} Privado`;
  if (normalized.includes("público") || normalized.includes("publico")) return `${base} P\u00fablico`;
  return base;
};
const norm = (value) => String(value || "").trim().toLowerCase();
const municipalityLabel = (value) => {
  const label = String(value || "").trim();
  const normalized = norm(label.replace(/,\s*rj$/i, ""));
  if (["rio de janeiro", "rj"].includes(normalized)) return "Rio de Janeiro";
  return label || text.notInformed;
};
const mergeRowsByLabel = (rows, nameKey, mapper = value => value) => Object.values((rows || []).reduce((acc, row) => {
  const label = mapper(row[nameKey]);
  acc[label] ||= { ...row, [nameKey]: label, actions: 0, audience: 0 };
  acc[label].actions += Number(row.actions || 0);
  acc[label].audience += Number(row.audience || 0);
  return acc;
}, {})).sort((a, b) => Number(b.actions || 0) - Number(a.actions || 0));

const formatReportDate = (value) => {
  const date = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  return date.toLocaleDateString("pt-BR");
};
const formatReportDateTime = (value) => {
  const date = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  return date.toLocaleString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
};
const escapeHtml = (value) => String(value ?? "")
  .replaceAll("&", "&amp;")
  .replaceAll("<", "&lt;")
  .replaceAll(">", "&gt;")
  .replaceAll('"', "&quot;")
  .replaceAll("'", "&#39;");
const buildTableRows = (rows) => rows.map((row) => `
  <tr>
    <td>${escapeHtml(row.label)}</td>
    <td class="value">${escapeHtml(row.value)}</td>
  </tr>
`).join("");
const buildFilterRows = (rows) => rows.map((row) => `
  <div class="filter-item">
    <span>${escapeHtml(row.label)}</span>
    <strong>${escapeHtml(row.value)}</strong>
  </div>
`).join("");
const buildExecutiveReportHtml = ({
  logoUrl,
  periodFrom,
  periodTo,
  issuedAt,
  appliedFilters,
  executiveSummary,
  summaryRows,
  productionRows,
  educationRows,
  publicRows,
  materialRows,
  analysis,
}) => `<!DOCTYPE html>
<html lang="pt-BR">
  <head>
    <meta charset="UTF-8" />
    <title>Relatório Estatístico Institucional</title>
    <style>
      @page {
        size: A4;
        margin: 20mm 16mm 22mm;
      }
      * {
        box-sizing: border-box;
      }
      body {
        margin: 0;
        font-family: "Segoe UI", Arial, sans-serif;
        color: #10213d;
        background: #ffffff;
      }
      .page {
        width: 100%;
      }
      .header {
        display: flex;
        align-items: center;
        gap: 18px;
        background: #0f2f67;
        color: #ffffff;
        padding: 18px 20px;
        border-radius: 14px;
        margin-bottom: 14px;
      }
      .header img {
        width: 86px;
        height: auto;
        object-fit: contain;
        flex: 0 0 auto;
      }
      .header-text {
        min-width: 0;
      }
      .eyebrow {
        display: block;
        font-size: 11px;
        font-weight: 700;
        letter-spacing: 0.14em;
        text-transform: uppercase;
        opacity: 0.86;
        margin-bottom: 6px;
      }
      h1 {
        margin: 0;
        font-size: 24px;
        line-height: 1.2;
      }
      .header-subtitle {
        margin: 6px 0 0;
        font-size: 13px;
        line-height: 1.5;
        opacity: 0.92;
      }
      .meta {
        margin-top: 8px;
        font-size: 12.5px;
        line-height: 1.6;
      }
      .filters-box {
        border: 1px solid #d4dce8;
        background: #f8fbff;
        border-radius: 12px;
        padding: 12px 14px;
        margin-bottom: 16px;
      }
      .filters-box h2 {
        margin: 0 0 10px;
        font-size: 14px;
        color: #0f2f67;
      }
      .filters-grid {
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 10px 16px;
      }
      .filter-item span {
        display: block;
        font-size: 11px;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: #51627f;
        margin-bottom: 3px;
      }
      .filter-item strong {
        display: block;
        font-size: 13px;
        color: #10213d;
      }
      .section {
        margin-bottom: 16px;
      }
      .section h2 {
        margin: 0 0 10px;
        font-size: 16px;
        color: #0f2f67;
      }
      .section h3 {
        margin: 14px 0 8px;
        font-size: 13px;
        color: #20447f;
      }
      .summary-text,
      .analysis {
        border: 1px solid #d4dce8;
        background: #f8fbff;
        border-radius: 12px;
        padding: 14px 16px;
        font-size: 13px;
        line-height: 1.65;
      }
      table {
        width: 100%;
        border-collapse: collapse;
        font-size: 12.5px;
      }
      thead {
        display: table-header-group;
      }
      tfoot {
        display: table-footer-group;
      }
      tr {
        break-inside: avoid;
        page-break-inside: avoid;
      }
      th, td {
        border: 1px solid #d4dce8;
        padding: 8px 10px;
        vertical-align: top;
      }
      th {
        background: #eef3fb;
        color: #0f2f67;
        text-align: left;
        font-weight: 700;
      }
      tbody tr:nth-child(even) {
        background: #f7f9fc;
      }
      .value {
        text-align: right;
        white-space: nowrap;
        font-variant-numeric: tabular-nums;
      }
      .observations-box {
        min-height: 96px;
        border: 1px solid #d4dce8;
        border-radius: 12px;
        background: linear-gradient(to bottom, #ffffff, #fafcff);
      }
      .signature {
        margin-top: 28px;
        padding-top: 12px;
        page-break-inside: avoid;
      }
      .signature-line {
        width: 260px;
        border-top: 1px solid #6b7b95;
        margin-bottom: 10px;
      }
      .signature div {
        font-size: 12px;
        line-height: 1.6;
        color: #31415f;
      }
      .footer {
        margin-top: 18px;
        padding-top: 10px;
        border-top: 1px solid #d4dce8;
        color: #51627f;
        font-size: 11px;
        line-height: 1.7;
      }
      .page-counter::after {
        content: counter(page);
      }
      @media print {
        .section,
        .filters-box,
        .signature {
          break-inside: avoid;
        }
      }
    </style>
  </head>
  <body>
    <main class="page">
      <header class="header">
        <img src="${logoUrl}" alt="Lei Seca" />
        <div class="header-text">
          <span class="eyebrow">LEI SECA – EDUCAÇÃO</span>
          <h1>RELATÓRIO ESTATÍSTICO INSTITUCIONAL</h1>
          <p class="header-subtitle">Sistema Integrado da Educação – SIED</p>
          <div class="meta">
            <div><strong>Período:</strong> ${escapeHtml(periodFrom)} a ${escapeHtml(periodTo)}</div>
            <div><strong>Data de emissão:</strong> ${escapeHtml(issuedAt)}</div>
          </div>
        </div>
      </header>

      <section class="filters-box">
        <h2>Filtros aplicados</h2>
        <div class="filters-grid">${buildFilterRows(appliedFilters)}</div>
      </section>

      <section class="section">
        <h2>Resumo executivo</h2>
        <div class="summary-text">${escapeHtml(executiveSummary)}</div>
      </section>

      <section class="section">
        <h2>1. Resumo Executivo</h2>
        <table>
          <thead>
            <tr><th>Indicador</th><th class="value">Valor</th></tr>
          </thead>
          <tbody>${buildTableRows(summaryRows)}</tbody>
        </table>
      </section>

      <section class="section">
        <h2>2. Produção Operacional</h2>
        <table>
          <thead>
            <tr><th>Etapa</th><th class="value">Quantidade</th></tr>
          </thead>
          <tbody>${buildTableRows(productionRows)}</tbody>
        </table>
      </section>

      <section class="section">
        <h2>3. Indicadores Institucionais</h2>
        <h3>Educação</h3>
        <table>
          <thead>
            <tr><th>Indicador</th><th class="value">Quantidade</th></tr>
          </thead>
          <tbody>${buildTableRows(educationRows)}</tbody>
        </table>
        <h3>Público</h3>
        <table>
          <thead>
            <tr><th>Indicador</th><th class="value">Quantidade</th></tr>
          </thead>
          <tbody>${buildTableRows(publicRows)}</tbody>
        </table>
        <h3>Materiais</h3>
        <table>
          <thead>
            <tr><th>Material</th><th class="value">Quantidade</th></tr>
          </thead>
          <tbody>${buildTableRows(materialRows)}</tbody>
        </table>
      </section>

      <section class="section">
        <h2>4. Análise automática</h2>
        <div class="analysis">${escapeHtml(analysis)}</div>
      </section>

      <section class="section">
        <h2>5. Observações</h2>
        <div class="observations-box"></div>
      </section>

      <section class="signature">
        <div class="signature-line"></div>
        <div>Operação Lei Seca</div>
        <div>Núcleo de Educação</div>
        <div>Sistema Integrado da Educação – SIED</div>
      </section>

      <footer class="footer">
        <div><strong>Sistema Integrado da Educação – SIED</strong></div>
        <div>Operação Lei Seca</div>
        <div>Documento gerado automaticamente</div>
        <div><strong>Data e hora da emissão:</strong> ${escapeHtml(issuedAt)}</div>
        <div><strong>Página:</strong> <span class="page-counter"></span></div>
      </footer>
    </main>
    <script>
      const waitForImages = async () => {
        const images = Array.from(document.images || []);
        await Promise.all(images.map((img) => {
          if (img.complete) return Promise.resolve();
          return new Promise((resolve) => {
            img.addEventListener("load", resolve, { once: true });
            img.addEventListener("error", resolve, { once: true });
          });
        }));
      };

      window.addEventListener("load", async () => {
        await waitForImages();
        window.focus();
        window.print();
      }, { once: true });
    </script>
  </body>
</html>`;
const agendaMatchesFilters = (agenda, filters) => {
  if (filters.municipality && ![agenda.municipality_ref_name, agenda.municipality, agenda.city].some(value => norm(value) === norm(filters.municipality))) return false;
  if (filters.team && ![agenda.team_ref_name, agenda.team_name, agenda.team].some(value => norm(value) === norm(filters.team))) return false;
  if (filters.entity && norm(agenda.requester_entity_type) !== norm(filters.entity)) return false;
  if (filters.action_type && ![agenda.action_type_ref_name, agenda.action_type].some(value => norm(value) === norm(filters.action_type))) return false;
  return true;
};
const groupBy = (items, getLabel) => Object.values(items.reduce((acc, item) => { const label = cleanLabel(getLabel(item)); acc[label] ||= { label, actions: 0, audience: 0 }; acc[label].actions += 1; acc[label].audience += parseExpected(item.audience, item.participant_range, item.quantity); return acc; }, {})).sort((a,b) => b.actions - a.actions);
export default function StatisticsPage() {
  const now = new Date(); const dashboardRef = useRef(null); const defaultFilters = { date_from: MIN_DATE, date_to: iso(now), municipality: "", team: "", action_type: "", entity: "", institution: "" };
  const [filters, setFilters] = useState(defaultFilters); const [pending, setPending] = useState(defaultFilters); const [options, setOptions] = useState({ municipalities: [], teams: [], action_types: [], entities: [], institutions: [] }); const [data, setData] = useState(null); const [agendas, setAgendas] = useState([]); const [futureAgendas, setFutureAgendas] = useState([]); const [pendingRequests, setPendingRequests] = useState(0); const [loading, setLoading] = useState(true); const [error, setError] = useState(""); const [drilldown, setDrilldown] = useState(null);
  useEffect(() => { api("/statistics/dashboard/filters/").then(setOptions).catch(() => {}); }, []);
  useEffect(() => { const safeFilters = { ...filters, date_from: clampStart(filters.date_from) };  setLoading(true); setError(""); Promise.all([api(`/statistics/dashboard/?${queryString(safeFilters)}`), api(`/agendas/?date_from=${safeFilters.date_from}&date_to=${safeFilters.date_to}&page_size=500`), api(`/agendas/?date_from=${safeFilters.date_from}&date_to=${safeFilters.date_to}&status=APPROVED&source=public&page_size=500`), api(`/agendas/?status=PENDING&source=requests&page_size=1`)]).then(([stats, agendaResult, futureResult, pendingResult]) => { setData(stats); setAgendas(agendaResult.results || agendaResult || []); setFutureAgendas(futureResult.results || futureResult || []); setPendingRequests(pendingResult.count ?? (pendingResult.results || pendingResult || []).length); }).catch(err => setError(err.message)).finally(() => setLoading(false)); }, [filters]);
  const annual = useMemo(() => (data?.annual || []).map(row => ({ year: row.year, ...row.values })), [data]); const dailySeries = useMemo(() => (data?.daily || []).map(row => ({ day: row.day_label || row.date, actions: Number(row.values["ACTION - Geral"] || 0), audience: Number(row.values["AUDIENCE - Geral"] || 0) })), [data]); const categoryData = useMemo(() => (data?.categories || []).map((row, index) => ({ ...row, label: streetActionTypeLabel(row.label), value: Number(row.value || 0), actions: Number(row.value || 0), audience: Number(row.audience || 0), color: COLORS[index % COLORS.length] })).sort((a,b) => b.value - a.value), [data]);
  const filteredAgendas = useMemo(() => agendas.filter(agenda => agendaMatchesFilters(agenda, filters)), [agendas, filters]); const filteredFutureAgendas = useMemo(() => futureAgendas.filter(agenda => agendaMatchesFilters(agenda, filters)), [futureAgendas, filters]);
  const totalActions = Number(data?.summary?.["ACTION - Geral"] || 0); const demand = useMemo(() => { const total = filteredAgendas.length; const publicForm = filteredAgendas.filter(a => a.origin === "PUBLIC_FORM").length; const internal = filteredAgendas.filter(a => a.origin !== "PUBLIC_FORM").length; const approved = filteredAgendas.filter(a => ["APPROVED", "COMPLETED"].includes(a.status)).length; const cancelled = filteredAgendas.filter(a => a.status === "CANCELLED").length; const refused = filteredAgendas.filter(a => ["REJECTED", "REFUSED"].includes(a.status)).length; return { total, publicForm, internal, approved, cancelled, refused, executed: totalActions }; }, [filteredAgendas, totalActions]);
  const publicRequests = filteredAgendas.filter(a => a.origin === "PUBLIC_FORM").length; const internalRequests = filteredAgendas.filter(a => a.origin !== "PUBLIC_FORM").length; const awaitingExecution = Math.max(0, demand.approved - demand.executed); const futurePublic = filteredAgendas.filter(a => !["COMPLETED", "CANCELLED"].includes(a.status)).reduce((sum, agenda) => sum + parseExpected(agenda.audience, agenda.participant_range), 0); const displaySummary = { ...(data?.summary || {}), FUTURE_PUBLIC: futurePublic, INTERNAL_REQUESTS: internalRequests, PUBLIC_REQUESTS: publicRequests }; const displayPrevious = { ...(data?.previous || {}), FUTURE_PUBLIC: 0, INTERNAL_REQUESTS: 0, PUBLIC_REQUESTS: 0 }; const displayComparisons = { ...(data?.comparisons || {}), FUTURE_PUBLIC: { percentage: null }, INTERNAL_REQUESTS: { percentage: null }, PUBLIC_REQUESTS: { percentage: null } };
  const ageRows = useMemo(() => groupBy(filteredAgendas.filter(a => ageGroupLabel(a.age_ranges)), a => ageGroupLabel(a.age_ranges)), [filteredAgendas]); const requesterRows = useMemo(() => groupBy(filteredAgendas.filter(a => requesterTypeLabel(a.requester_entity_type)), a => requesterTypeLabel(a.requester_entity_type)), [filteredAgendas]); const administrativeDemandRows = useMemo(() => { const items = data?.administrative_demands?.items || []; const itemByCode = Object.fromEntries(items.map(item => [item.code, item])); return ["TRAVEL", "INTERVIEW", "MEETING"].map((code, index) => ({ label: itemByCode[code]?.label || ADMINISTRATIVE_DEMAND_LABELS[code], actions: Number(itemByCode[code]?.value || 0), audience: 0, color: COLORS[index % COLORS.length] })); }, [data]); const heatmapRows = data?.heatmap || []; const municipalities = useMemo(() => mergeRowsByLabel(data?.municipalities || [], "agenda__city", municipalityLabel), [data]); const teams = useMemo(() => [...(data?.teams || [])].sort((a, b) => Number(b.actions || 0) - Number(a.actions || 0) || Number(b.audience || 0) - Number(a.audience || 0)), [data]); const bestTeam = teams[0] || {}; const leastTeam = [...teams].reverse().find(row => Number(row.actions || 0) > 0) || {}; const audienceLeader = [...teams].sort((a, b) => Number(b.audience || 0) - Number(a.audience || 0))[0] || {}; const averageLeader = [...teams].filter(row => Number(row.actions || 0) > 0).sort((a, b) => Number(b.average || 0) - Number(a.average || 0))[0] || {}; const insights = [`${bestTeam.team || "Equipe"} fez mais relatórios técnicos: ${integer(bestTeam.actions)} ações registradas.`, `${leastTeam.team || "Equipe"} teve o menor volume entre as equipes com produção: ${integer(leastTeam.actions)} a\u00e7\u00f5es.`, `${audienceLeader.team || "Equipe"} alcançou mais público: ${integer(audienceLeader.audience)} pessoas.`, `${averageLeader.team || "Equipe"} tem a maior m\u00e9dia por a\u00e7\u00e3o: ${number(averageLeader.average)} pessoas por registro.`, `${integer(data?.summary?.REPORTS_WITHOUT_PUBLIC)} relatórios aprovados estão sem público informado.`];
  const reset = () => { setPending(defaultFilters); setFilters(defaultFilters); };
  const apply = () => setFilters(current => ({ ...current, ...pending, date_from: clampStart(pending.date_from) }));
  const exportExcel = () => {
    const years = annual.map(row => row.year);
    const lines = [["Indicador", ...years], ...HISTORICAL_ROWS.map(([key, label]) => [label, ...annual.map(row => row[key] || 0)])];
    const blob = new Blob(["\ufeff" + lines.map(line => line.join("\t")).join("\n")], { type: "application/vnd.ms-excel;charset=utf-8" });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = "estatisticas-sied.xls";
    link.click();
    URL.revokeObjectURL(link.href);
  };
  const exportCsv = async () => {
    const blob = await api(`/statistics/dashboard/export.csv?${queryString(filters)}`);
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = "estatisticas-sied.csv";
    link.click();
    URL.revokeObjectURL(link.href);
  };
  const exportImage = async () => {
    const dataUrl = await toPng(dashboardRef.current, { cacheBust: true, pixelRatio: 1.5, backgroundColor: "#f4f7fb" });
    const link = document.createElement("a");
    link.href = dataUrl;
    link.download = "dashboard-estatisticas-sied.png";
    link.click();
    URL.revokeObjectURL(link.href);
  };
  const exportPdf = () => {
    const issuedAt = new Date();
    const expectedAudience = filteredAgendas.reduce((sum, agenda) => sum + parseExpected(agenda.audience, agenda.participant_range, agenda.quantity), 0);
    const reachedAudience = Number(displaySummary["AUDIENCE - Geral"] || 0);
    const lectures = Number(displaySummary["LECTURES - Geral"] || 0);
    const streetActions = Number(displaySummary["STREET_ACTIONS - Geral"] || 0);
    const distributedMaterials = Number(displaySummary["MATERIAL - Geral"] || 0);
    const distributedComics = Number(displaySummary["MATERIAL - Soprinho"] || 0);
    const totalDifference = reachedAudience - expectedAudience;
    const municipalityValue = filters.municipality || "Todos";
    const teamValue = filters.team || "Todos";
    const categoryValue = filters.entity || "Todos";
    const summaryRows = [
      { label: "Público alcançado", value: integer(reachedAudience) },
      { label: "Público previsto", value: integer(expectedAudience) },
      { label: "Palestras realizadas", value: integer(lectures) },
      { label: "Ações de rua", value: integer(streetActions) },
      { label: "Materiais distribuídos", value: integer(distributedMaterials) },
      { label: "Revistinhas distribuídas", value: integer(distributedComics) },
      { label: "Solicitações internas", value: integer(internalRequests) },
      { label: "Solicitações públicas", value: integer(publicRequests) },
    ];
    const productionRows = [
      { label: "Solicitações recebidas", value: integer(demand.total) },
      { label: "Solicitações aprovadas", value: integer(demand.approved) },
      { label: "Ações executadas", value: integer(demand.executed) },
      { label: "Aguardando execução", value: integer(awaitingExecution) },
      { label: "Aguardando aprovação", value: integer(pendingRequests) },
      { label: "Canceladas/Recusadas", value: integer(demand.cancelled + demand.refused) },
    ];
    const educationRows = [
      { label: "Palestras", value: integer(lectures) },
      { label: "Ações de Rua", value: integer(streetActions) },
      { label: "Solicitações Públicas", value: integer(publicRequests) },
      { label: "Solicitações Internas", value: integer(internalRequests) },
    ];
    const publicRows = [
      { label: "Público previsto", value: integer(expectedAudience) },
      { label: "Público alcançado", value: integer(reachedAudience) },
      { label: "Diferença", value: `${totalDifference > 0 ? "+" : ""}${integer(totalDifference)}` },
    ];
    const materialRows = [
      { label: "Materiais distribuídos", value: integer(distributedMaterials) },
      { label: "Revistinhas distribuídas", value: integer(distributedComics) },
    ];
    const executiveSummary = demand.total > 0
      ? `O período filtrado registrou ${integer(demand.executed)} ações executadas a partir de ${integer(demand.total)} solicitações, com ${integer(reachedAudience)} pessoas alcançadas e ${integer(distributedMaterials)} materiais distribuídos.`
      : `Não há dados suficientes para produção no período filtrado. O relatório foi gerado com base nos filtros aplicados e apresenta os totais atualmente disponíveis.`;
    const analysisParts = [];
    if (demand.total > 0) {
      analysisParts.push(`Durante o período analisado foram registradas ${integer(demand.total)} solicitações, das quais ${integer(demand.approved)} foram aprovadas, resultando em ${integer(demand.executed)} ações executadas.`);
    } else {
      analysisParts.push("Não houve produção consolidada para os filtros selecionados no período analisado.");
    }
    if (expectedAudience > 0) {
      analysisParts.push(
        reachedAudience > expectedAudience
          ? `As atividades alcançaram ${integer(reachedAudience)} pessoas, superando o público inicialmente previsto (${integer(expectedAudience)}).`
          : `As atividades alcançaram ${integer(reachedAudience)} pessoas, diante de um público inicialmente previsto de ${integer(expectedAudience)}.`
      );
    } else if (reachedAudience > 0) {
      analysisParts.push(`As atividades alcançaram ${integer(reachedAudience)} pessoas no período analisado, sem base válida de público previsto para comparação.`);
    } else {
      analysisParts.push("Não há público alcançado registrado para o período filtrado.");
    }
    if (lectures > 0 || streetActions > 0) {
      analysisParts.push(`Foram realizadas ${integer(lectures)} palestras e ${integer(streetActions)} ações de rua.`);
    }
    if (distributedMaterials > 0 || distributedComics > 0) {
      analysisParts.push(`Também houve a distribuição de ${integer(distributedMaterials)} materiais educativos, incluindo ${integer(distributedComics)} revistinhas.`);
    }

    const printWindow = window.open("", "_blank", "noopener,noreferrer");
    if (!printWindow) {
      window.alert("Não foi possível abrir a visualização de impressão do relatório.");
      return;
    }

    const logoUrl = new URL(leiSecaLogo, window.location.href).href;
    printWindow.document.open();
    printWindow.document.write(buildExecutiveReportHtml({
      logoUrl,
      periodFrom: formatReportDate(filters.date_from),
      periodTo: formatReportDate(filters.date_to),
      issuedAt: formatReportDateTime(issuedAt),
      appliedFilters: [
        { label: "Período", value: `${formatReportDate(filters.date_from)} a ${formatReportDate(filters.date_to)}` },
        { label: "Município", value: municipalityValue },
        { label: "Equipe", value: teamValue },
        { label: "Categoria", value: categoryValue },
      ],
      executiveSummary,
      summaryRows,
      productionRows,
      educationRows,
      publicRows,
      materialRows,
      analysis: analysisParts.join(" "),
    }));
    printWindow.document.close();
  };
  if (loading) return <section className="stats-dashboard"><div className="stats-loading">Carregando painel executivo...</div></section>; if (error) return <section className="stats-dashboard"><div className="alert">N\u00e3o foi poss\u00edvel carregar o dashboard: {error}</div></section>;
  return <section className="stats-dashboard" ref={dashboardRef}><header className="stats-hero"><div><span>{"Inteligência institucional"}</span><h1>Dashboard Executivo SIED</h1><p>{"Indicadores oficiais a partir de 09/07/2026, quando o sistema passou a operar."}</p></div><div className="stats-export"><button onClick={exportPdf}><Printer size={16}/>PDF</button><button onClick={exportExcel}><FileSpreadsheet size={16}/>Excel</button><button onClick={exportCsv}><Download size={16}/>CSV</button><button onClick={exportImage}><FileImage size={16}/>Imagem</button></div></header>
    <div className="stats-filters"><div className="stats-filter-title"><Filter size={17}/>{"Filtros globais"}</div><label>De<input min={MIN_DATE} type="date" value={pending.date_from} onChange={e => setPending(v => ({ ...v, date_from: clampStart(e.target.value) }))}/></label><label>{"Até"}<input min={MIN_DATE} type="date" value={pending.date_to} onChange={e => setPending(v => ({ ...v, date_to: e.target.value }))}/></label><label>{"Município"}<select value={pending.municipality} onChange={e => setPending(v => ({ ...v, municipality: e.target.value }))}><option value="">Todos</option>{options.municipalities.map(v => <option key={v}>{v}</option>)}</select></label><label>Equipe<select value={pending.team} onChange={e => setPending(v => ({ ...v, team: e.target.value }))}><option value="">Todas</option>{options.teams.map(v => <option key={v}>{v}</option>)}</select></label><label className="stats-category-filter">Categoria<select value={pending.entity} onChange={e => setPending(v => ({ ...v, entity: e.target.value }))}><option value="">Todas</option>{options.entities.map(v => <option key={v}>{v}</option>)}</select></label><div className="stats-filter-actions"><button className="primary" onClick={apply}>Aplicar</button><button onClick={reset}>Limpar</button></div></div>
    <div className="stats-kpi-grid stats-kpi-grid-compact">{KPI_DEFS.map(def => <MetricCard key={def[0]} definition={def} summary={displaySummary} previous={displayPrevious} comparison={displayComparisons}/>)}</div>
    <Section icon={ArrowRight} title={"Produção x demanda"} subtitle={"Funil operacional das solicitações no período."}><div className="stats-demand-grid"><MiniCard label={"Solicitações recebidas"} value={demand.total} hint={`${integer(demand.publicForm)} p\u00fablicas \u2022 ${integer(demand.internal)} internas`}/><MiniCard label="Aprovadas" value={demand.approved}/><MiniCard label="Executadas" value={demand.executed}/><MiniCard label={"Aguardando execução"} value={awaitingExecution} hint={"Aprovadas ainda sem execução registrada"} tone={COLORS[1]}/><MiniCard label={"Aguardando aprovação"} value={pendingRequests} hint={"Solicitações pendentes de avaliação"} tone={COLORS[8]}/><MiniCard label="Canceladas/recusadas" value={demand.cancelled + demand.refused} tone={COLORS[2]}/></div></Section>
    <Section icon={TrendingUp} title={"Evolução diária"} subtitle={"Ações e público por dia desde 01/07/2026."}><div className="stats-chart-xl"><ResponsiveContainer><ComposedChart data={dailySeries}><CartesianGrid strokeDasharray="3 3"/><XAxis dataKey="day"/><YAxis yAxisId="left"/><YAxis yAxisId="right" orientation="right"/><Tooltip formatter={number}/><Legend/><Bar yAxisId="left" dataKey="actions" name={"Ações"} fill={COLORS[0]} radius={[6,6,0,0]}><LabelList dataKey="actions" position="top" formatter={(value) => value ? integer(value) : ""}/></Bar><Line yAxisId="right" type="monotone" dataKey="audience" name={"P\u00fablico"} stroke={COLORS[4]} strokeWidth={3}><LabelList dataKey="audience" position="top" formatter={(value) => value ? integer(value) : ""}/></Line></ComposedChart></ResponsiveContainer></div></Section>
    <div className="stats-two-columns stats-street-admin-layout"><Section icon={BarChart3} title={"Ações de rua"} subtitle="Somente categorias com movimento." className="stats-street-panel"><ExecutiveBar rows={categoryData.map(row => ({ label: row.label, actions: row.value, audience: row.audience, color: row.color, onClick: () => setDrilldown(row) }))}/></Section><div className="stats-right-stack"><Section icon={Building2} title={"Demandas Administrativas"} subtitle={"Solicita\u00e7\u00f5es internas por subtipo."}><ExecutiveBar rows={administrativeDemandRows}/></Section><Section icon={Users} title={"Faixa etária do público"} subtitle={"Perfil informado na solicitação."}><ExecutiveBar rows={ageRows}/></Section></div></div>
    <div className="stats-two-columns"><Section icon={Users} title="Perfil institucional" subtitle="Tipo de solicitante."><ExecutiveBar rows={requesterRows}/></Section><Section icon={CalendarDays} title={"Horários das ações registradas"} subtitle={"Ações dos relatórios aprovados por dia e horário inicial da agenda."}><UsageHeatmap data={heatmapRows}/></Section></div>
    <div className="stats-two-columns"><Section icon={MapPin} title={"Indicadores geográficos"} subtitle={"Municípios com produção no período."}><Ranking rows={municipalities} nameKey="agenda__city"/></Section><Section icon={BarChart3} title="Ranking operacional" subtitle={"Equipes com produção no período."}><Ranking rows={teams} nameKey="team"/></Section></div>
    <Section icon={Lightbulb} title={"Insights automáticos"} subtitle={"Leitura rápida para gestão."}><div className="stats-insights">{insights.map((insight, index) => <p key={index}>{insight}</p>)}</div></Section>
    <Section icon={BarChart3} title={"Série histórica completa"} subtitle={"Tabela institucional preservada para auditoria e exportação."}><div className="stats-table-wrap"><table className="stats-table stats-history-table"><thead><tr><th>Indicador</th>{annual.map(row => <th key={row.year}>{row.year}</th>)}</tr></thead><tbody>{HISTORICAL_ROWS.map(([key, label]) => <tr key={key}><td>{label}</td>{annual.map(row => <td key={row.year}>{number(row[key])}</td>)}</tr>)}</tbody></table></div></Section>
    {drilldown && <div className="stats-drilldown"><div><button onClick={() => setDrilldown(null)}><X size={18}/></button><span>Detalhamento</span><h3>{drilldown.label}</h3><p>Total no período: <strong>{number(drilldown.value)}</strong></p><p>Público: <strong>{number(drilldown.audience)}</strong></p></div></div>}
    <footer className="stats-methodology">Fonte: banco de dados SIED • demanda das agendas + produção dos relatórios aprovados.</footer></section>;
}
