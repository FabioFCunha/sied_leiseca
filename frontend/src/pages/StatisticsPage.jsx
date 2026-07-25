import { useEffect, useMemo, useRef, useState } from "react";
import {
  Activity, AlertTriangle, ArrowRight, BarChart3, BookOpen, Building2,
  CalendarDays, Download, FileImage, FileSpreadsheet, Filter, Lightbulb,
  MapPin, Printer, TrendingDown, TrendingUp, Users, X,
} from "lucide-react";
import {
  Bar, CartesianGrid, ComposedChart, Legend, Line, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import { toPng } from "html-to-image";
import { api } from "../api/client.js";
import { formatLocalISODate } from "../utils/date.js";
import "./StatisticsPage.css";

const MIN_DATE = "2026-07-01";
const COLORS = ["#0048d7", "#059669", "#dc2626", "#7c3aed", "#ea580c", "#db2777", "#0891b2", "#ca8a04", "#64748b", "#16a34a"];
const number = (value) => Number(value || 0).toLocaleString("pt-BR", { maximumFractionDigits: 1 });
const integer = (value) => Number(value || 0).toLocaleString("pt-BR", { maximumFractionDigits: 0 });
const iso = (value) => value instanceof Date ? formatLocalISODate(value) : value;
const clampStart = (value) => !value || value < MIN_DATE ? MIN_DATE : value;
const queryString = (values) => new URLSearchParams(Object.entries(values).filter(([, value]) => value !== "" && value != null)).toString();

const KPI_DEFS = [
  ["AUDIENCE - Geral", "Público alcançado", Users, COLORS[0], "Realizado nos relatórios"],
  ["EXPECTED_PUBLIC", "Público previsto", Users, COLORS[1], "Demanda das solicitações"],
  ["REPORTS_WITHOUT_PUBLIC", "Relatórios sem público", AlertTriangle, COLORS[2], "Atenção para revisão"],
  ["ACTION - Geral", "Produção executada", CalendarDays, COLORS[3], "Ações educativas"],
  ["MATERIAL - Geral", "Materiais distribuídos", BookOpen, COLORS[5], "Total entregue"],
  ["MATERIAL - Soprinho", "Revistinhas distribuídas", BookOpen, COLORS[7], "Soprinho"],
];
const HISTORICAL_ROWS = [
  ["AUDIENCE - Geral", "1 - Público total"], ["AUDIENCE - PALESTRAS", "1.1 - Público em palestras"], ["AUDIENCE - ACOES", "1.2 - Público em ações"],
  ["LECTURES - Geral", "2 - Palestras realizadas"], ["ACTION - Escola", "2.1 - Escolas"], ["ACTION - Universidade", "2.2 - Universidades"], ["ACTION - Empresa", "2.3 - Empresas"],
  ["STREET_ACTIONS - Geral", "3 - Ações de rua"], ["ACTION - Bares", "3.1 - Bares"], ["ACTION - Pedágio", "3.2 - Pedágio"], ["ACTION - Praças Esportivas", "3.3 - Esportes"],
  ["ACTION - Praia", "3.4 - Praia"], ["ACTION - Eventos", "3.5 - Eventos"], ["ACTION - Shopping", "3.6 - Shopping/Centro Comercial"], ["ACTION - Ação Social", "3.7 - Ação Social"],
  ["ACTION - Outros", "3.8 - Outros"], ["ACTION - Praças/Parques Públicos", "3.9 - Praças/Parques Públicos"], ["ACTION - Pontos turísticos", "3.10 - Pontos turísticos"],
  ["ACTION - Ação conjunta com a fiscalização", "3.11 - Ação conjunta com a fiscalização"], ["MATERIAL - Geral", "4 - Materiais de divulgação"], ["MATERIAL - Soprinho", "Revistinha Soprinho"],
];

function Empty({ children = "Sem dados para os filtros selecionados." }) { return <div className="stats-empty">{children}</div>; }
function Section({ icon: Icon, title, subtitle, children, actions, className = "" }) {
  return <section className={`stats-panel ${className}`}><header className="stats-panel-header"><div className="stats-panel-title"><span className="stats-icon"><Icon size={17}/></span><div><h2>{title}</h2>{subtitle && <p>{subtitle}</p>}</div></div>{actions && <div className="stats-panel-actions">{actions}</div>}</header><div className="stats-panel-body">{children}</div></section>;
}
function MetricCard({ definition, summary, previous, comparison, totalActions }) {
  const [key, label, Icon, color, hint] = definition;
  const value = Number(summary?.[key] || 0);
  const prior = Number(previous?.[key] || 0);
  const pct = comparison?.[key]?.percentage;
  const Trend = pct < 0 ? TrendingDown : TrendingUp;
  const share = key === "ACTION - Geral" && totalActions ? `${number(summary?.["LECTURES - Geral"])} palestras • ${number(summary?.["STREET_ACTIONS - Geral"])} rua` : hint;
  return <article className="stats-kpi" style={{ "--kpi": color }}><div className="stats-kpi-top"><span className="stats-kpi-icon"><Icon size={18}/></span><span>{label}</span></div><div className="stats-kpi-value">{number(value)}</div><div className={`stats-kpi-delta ${pct < 0 ? "is-down" : "is-up"}`}><Trend size={14}/>{pct == null ? (value ? "Novo" : "0,0%") : `${pct >= 0 ? "+" : ""}${pct.toFixed(1)}%`} <span>vs. {number(prior)}</span></div>{share && <small>{share}</small>}</article>;
}
function MiniCard({ label, value, hint, icon: Icon = BarChart3, tone = COLORS[0] }) { return <div className="stats-mini-card"><span style={{ background: tone }}><Icon size={15}/></span><strong>{number(value)}</strong><small>{label}</small>{hint && <em>{hint}</em>}</div>; }
function ExecutiveBar({ rows, maxRows = 12 }) {
  const visible = rows.filter(row => Number(row.actions || 0) > 0 || Number(row.audience || 0) > 0).slice(0, maxRows);
  if (!visible.length) return <Empty/>;
  const total = visible.reduce((sum, row) => sum + Number(row.actions || 0), 0) || 1;
  const max = Math.max(...visible.map(row => Number(row.actions || 0)), 1);
  return <div className="stats-exec-bars">{visible.map((row, index) => { const pct = Number(row.actions || 0) / total * 100; return <button key={`${row.label}-${index}`} onClick={row.onClick} className="stats-exec-bar"><span className="stats-exec-label"><b>{row.label}</b><small>{integer(row.actions)} ações • {integer(row.audience)} pessoas • {pct.toFixed(1)}%</small></span><i><em style={{ width: `${Math.max(3, Number(row.actions || 0) / max * 100)}%`, background: row.color || COLORS[index % COLORS.length] }}/></i></button>; })}</div>;
}
function RankingTabs({ tabs }) { const [active, setActive] = useState(tabs[0]?.key); const tab = tabs.find(item => item.key === active) || tabs[0]; return <div><div className="stats-tabs">{tabs.map(item => <button key={item.key} className={item.key === active ? "active" : ""} onClick={() => setActive(item.key)}>{item.label}</button>)}</div><Ranking rows={tab.rows} nameKey={tab.nameKey}/></div>; }
function Ranking({ rows, nameKey }) { const visible = (rows || []).filter(row => Number(row.actions || 0) > 0 || Number(row.audience || 0) > 0); if (!visible.length) return <Empty/>; const max = Math.max(...visible.map(row => Number(row.actions || 0)), 1); return <div className="stats-ranking">{visible.map((row, index) => <div className="stats-rank-row" key={`${row[nameKey]}-${index}`}><b>{index + 1}</b><span>{row[nameKey] || "Não informado"}</span><div><i style={{ width: `${Number(row.actions || 0) / max * 100}%` }}/></div><strong>{number(row.actions)}</strong><small>{number(row.audience)} público</small></div>)}</div>; }
const parseExpected = (...values) => { for (const value of values) { const text = String(value ?? "").trim(); if (!text) continue; const nums = text.match(/\d+/g)?.map(Number); if (nums?.length) return Math.max(...nums); } return 0; };
const cleanLabel = (value) => String(value || "").trim() || "Não informado";
const groupBy = (items, getLabel) => Object.values(items.reduce((acc, item) => { const label = cleanLabel(getLabel(item)); acc[label] ||= { label, actions: 0, audience: 0 }; acc[label].actions += 1; acc[label].audience += parseExpected(item.audience, item.participant_range, item.quantity); return acc; }, {})).sort((a,b) => b.actions - a.actions);

export default function StatisticsPage() {
  const now = new Date(); const dashboardRef = useRef(null);
  const defaultFilters = { date_from: MIN_DATE, date_to: iso(now), municipality: "", team: "", action_type: "", entity: "", institution: "" };
  const [filters, setFilters] = useState(defaultFilters);
  const [pending, setPending] = useState(defaultFilters); const [options, setOptions] = useState({ municipalities: [], teams: [], action_types: [], entities: [], institutions: [] });
  const [data, setData] = useState(null); const [agendas, setAgendas] = useState([]); const [loading, setLoading] = useState(true); const [error, setError] = useState(""); const [drilldown, setDrilldown] = useState(null);
  useEffect(() => { api("/statistics/dashboard/filters/").then(setOptions).catch(() => {}); }, []);
  useEffect(() => { const safeFilters = { ...filters, date_from: clampStart(filters.date_from) }; setLoading(true); setError(""); Promise.all([
    api(`/statistics/dashboard/?${queryString(safeFilters)}`),
    api(`/agendas/?date_from=${safeFilters.date_from}&date_to=${safeFilters.date_to}&page_size=500`)
  ]).then(([stats, agendaResult]) => { setData(stats); setAgendas(agendaResult.results || agendaResult || []); }).catch(err => setError(err.message)).finally(() => setLoading(false)); }, [filters]);

  const annual = useMemo(() => (data?.annual || []).map(row => ({ year: row.year, ...row.values })), [data]);
  const dailySeries = useMemo(() => (data?.daily || []).map(row => ({ day: row.day_label || row.date, actions: Number(row.values["ACTION - Geral"] || 0), audience: Number(row.values["AUDIENCE - Geral"] || 0) })), [data]);
  const categoryData = useMemo(() => (data?.categories || []).map((row, index) => ({ ...row, value: Number(row.value || 0), actions: Number(row.value || 0), audience: Number(row.audience || 0), color: COLORS[index % COLORS.length] })).sort((a,b) => b.value - a.value), [data]);
  const totalActions = Number(data?.summary?.["ACTION - Geral"] || 0); const reached = Number(data?.summary?.["AUDIENCE - Geral"] || 0); const expected = Number(data?.summary?.EXPECTED_PUBLIC || 0);
  const demand = useMemo(() => { const total = agendas.length; const publicForm = agendas.filter(a => a.origin === "PUBLIC_FORM").length; const internal = agendas.filter(a => a.origin === "INTERNAL").length; const approved = agendas.filter(a => ["APPROVED", "COMPLETED"].includes(a.status)).length; const cancelled = agendas.filter(a => a.status === "CANCELLED").length; const refused = agendas.filter(a => ["REJECTED", "REFUSED"].includes(a.status)).length; return { total, publicForm, internal, approved, cancelled, refused, executed: totalActions, expected, reached, conversion: total ? totalActions / total * 100 : 0, realization: expected ? reached / expected * 100 : 0 }; }, [agendas, totalActions, expected, reached]);
  const sourceRows = useMemo(() => groupBy(agendas, a => a.origin === "PUBLIC_FORM" ? "Solicitação pública" : "Solicitação interna"), [agendas]);
  const ageRows = useMemo(() => groupBy(agendas, a => a.age_ranges), [agendas]);
  const requesterRows = useMemo(() => groupBy(agendas, a => a.requester_entity_type), [agendas]);
  const modalityRows = useMemo(() => groupBy(agendas, a => a.action_type), [agendas]);
  const municipalities = data?.municipalities || []; const teams = data?.teams || [];
  const bestTeam = teams[0] || {}; const topCategory = categoryData[0] || {};
  const insights = [
    `${topCategory.label || "Categoria principal"} concentra ${totalActions ? (Number(topCategory.value || 0) / totalActions * 100).toFixed(1) : "0,0"}% das ações.`,
    `${bestTeam.team || "Equipe"} lidera em volume com ${integer(bestTeam.actions)} ações.`,
    `Público realizado: ${demand.realization.toFixed(1)}% do público previsto.`,
    `${integer(data?.summary?.REPORTS_WITHOUT_PUBLIC)} relatórios aprovados estão sem público informado.`,
  ];
  const reset = () => { setPending(defaultFilters); setFilters(defaultFilters); };
  const apply = () => setFilters(current => ({ ...current, ...pending, date_from: clampStart(pending.date_from) }));
  const exportExcel = () => { const years = annual.map(row => row.year); const lines = [["Indicador", ...years], ...HISTORICAL_ROWS.map(([key, label]) => [label, ...annual.map(row => row[key] || 0)])]; const blob = new Blob(["\ufeff" + lines.map(line => line.join("\t")).join("\n")], { type: "application/vnd.ms-excel;charset=utf-8" }); const link = document.createElement("a"); link.href = URL.createObjectURL(blob); link.download = "estatisticas-sied.xls"; link.click(); URL.revokeObjectURL(link.href); };
  const exportCsv = async () => { const blob = await api(`/statistics/dashboard/export.csv?${queryString(filters)}`); const link = document.createElement("a"); link.href = URL.createObjectURL(blob); link.download = "estatisticas-sied.csv"; link.click(); URL.revokeObjectURL(link.href); };
  const exportImage = async () => { const dataUrl = await toPng(dashboardRef.current, { cacheBust: true, pixelRatio: 1.5, backgroundColor: "#f4f7fb" }); const link = document.createElement("a"); link.href = dataUrl; link.download = "dashboard-estatisticas-sied.png"; link.click(); };
  if (loading) return <section className="stats-dashboard"><div className="stats-loading">Carregando painel executivo...</div></section>; if (error) return <section className="stats-dashboard"><div className="alert">Não foi possível carregar o dashboard: {error}</div></section>;

  return <section className="stats-dashboard" ref={dashboardRef}>
    <header className="stats-hero"><div><span>Inteligência institucional</span><h1>Dashboard Executivo SIED</h1><p>Indicadores oficiais a partir de 01/07/2026, quando o sistema passou a operar.</p></div><div className="stats-export"><button onClick={() => window.print()}><Printer size={16}/>PDF</button><button onClick={exportExcel}><FileSpreadsheet size={16}/>Excel</button><button onClick={exportCsv}><Download size={16}/>CSV</button><button onClick={exportImage}><FileImage size={16}/>Imagem</button></div></header>
    <div className="stats-filters"><div className="stats-filter-title"><Filter size={17}/>Filtros globais</div><label>De<input min={MIN_DATE} type="date" value={pending.date_from} onChange={e => setPending(v => ({ ...v, date_from: clampStart(e.target.value) }))}/></label><label>Até<input min={MIN_DATE} type="date" value={pending.date_to} onChange={e => setPending(v => ({ ...v, date_to: e.target.value }))}/></label><label>Município<select value={pending.municipality} onChange={e => setPending(v => ({ ...v, municipality: e.target.value }))}><option value="">Todos</option>{options.municipalities.map(v => <option key={v}>{v}</option>)}</select></label><label>Equipe<select value={pending.team} onChange={e => setPending(v => ({ ...v, team: e.target.value }))}><option value="">Todas</option>{options.teams.map(v => <option key={v}>{v}</option>)}</select></label><label>Categoria<select value={pending.entity} onChange={e => setPending(v => ({ ...v, entity: e.target.value }))}><option value="">Todas</option>{options.entities.map(v => <option key={v}>{v}</option>)}</select></label><div className="stats-filter-actions"><button className="primary" onClick={apply}>Aplicar</button><button onClick={reset}>Limpar</button></div></div>
    <div className="stats-kpi-grid stats-kpi-grid-compact">{KPI_DEFS.map(def => <MetricCard key={def[0]} definition={def} summary={data.summary} previous={data.previous} comparison={data.comparisons} totalActions={totalActions}/>)}</div>
    <Section icon={ArrowRight} title="Produção x demanda" subtitle="Resumo do funil sem repetir os cards principais."><div className="stats-demand-grid"><MiniCard label="Solicitações recebidas" value={demand.total} hint={`${integer(demand.publicForm)} públicas • ${integer(demand.internal)} internas`}/><MiniCard label="Aprovadas" value={demand.approved}/><MiniCard label="Executadas" value={demand.executed}/><MiniCard label="Canceladas/recusadas" value={demand.cancelled + demand.refused} tone={COLORS[2]}/><MiniCard label="Conversão" value={demand.conversion} hint="executadas / recebidas" tone={COLORS[3]}/><MiniCard label="Realização" value={demand.realization} hint="público alcançado / previsto" tone={COLORS[1]}/></div></Section>
    <Section icon={TrendingUp} title="Evolução diária" subtitle="Ações e público por dia desde 01/07/2026."><div className="stats-chart-xl"><ResponsiveContainer><ComposedChart data={dailySeries}><CartesianGrid strokeDasharray="3 3"/><XAxis dataKey="day"/><YAxis yAxisId="left"/><YAxis yAxisId="right" orientation="right"/><Tooltip formatter={number}/><Legend/><Bar yAxisId="left" dataKey="actions" name="Ações" fill={COLORS[0]} radius={[6,6,0,0]}/><Line yAxisId="right" type="monotone" dataKey="audience" name="Público" stroke={COLORS[4]} strokeWidth={3}/></ComposedChart></ResponsiveContainer></div></Section>
    <div className="stats-three-columns"><Section icon={BarChart3} title="Distribuição por categoria" subtitle="Somente categorias com movimento."><ExecutiveBar rows={categoryData.map(row => ({ label: row.label, actions: row.value, audience: row.audience, color: row.color, onClick: () => setDrilldown(row) }))}/></Section><Section icon={Building2} title="Origem da demanda" subtitle="De onde vieram as solicitações."><ExecutiveBar rows={sourceRows}/></Section><Section icon={Users} title="Faixa etária do público" subtitle="Perfil informado na solicitação."><ExecutiveBar rows={ageRows}/></Section></div>
    <div className="stats-two-columns"><Section icon={Users} title="Perfil institucional" subtitle="Tipo de solicitante."><ExecutiveBar rows={requesterRows}/></Section><Section icon={Activity} title="Modalidade pretendida" subtitle="Palestra, educação/conscientização e ações de rua."><ExecutiveBar rows={modalityRows}/></Section></div>
    <div className="stats-two-columns"><Section icon={MapPin} title="Indicadores geográficos" subtitle="Municípios com produção no período."><Ranking rows={municipalities} nameKey="agenda__city"/></Section><Section icon={BarChart3} title="Ranking operacional" subtitle="Categorias, equipes e municípios."><RankingTabs tabs={[{ key:"cat", label:"Categorias", rows: categoryData.map(row => ({ label: row.label, actions: row.value, audience: row.audience })), nameKey:"label" }, { key:"teams", label:"Equipes", rows: teams, nameKey:"team" }, { key:"mun", label:"Municípios", rows: municipalities, nameKey:"agenda__city" }]}/></Section></div>
    <Section icon={Lightbulb} title="Insights automáticos" subtitle="Leitura rápida para gestão."><div className="stats-insights">{insights.map((insight, index) => <p key={index}>{insight}</p>)}</div></Section>
    <Section icon={BarChart3} title="Série histórica completa" subtitle="Tabela institucional preservada para auditoria e exportação."><div className="stats-table-wrap"><table className="stats-table stats-history-table"><thead><tr><th>Indicador</th>{annual.map(row => <th key={row.year}>{row.year}</th>)}</tr></thead><tbody>{HISTORICAL_ROWS.map(([key, label]) => <tr key={key}><td>{label}</td>{annual.map(row => <td key={row.year}>{number(row[key])}</td>)}</tr>)}</tbody></table></div></Section>
    {drilldown && <div className="stats-drilldown"><div><button onClick={() => setDrilldown(null)}><X size={18}/></button><span>Detalhamento</span><h3>{drilldown.label}</h3><p>Total no período: <strong>{number(drilldown.value)}</strong></p><p>Público: <strong>{number(drilldown.audience)}</strong></p></div></div>}
    <footer className="stats-methodology">Fonte: banco de dados SIED • demanda das agendas + produção dos relatórios aprovados.</footer>
  </section>;
}
