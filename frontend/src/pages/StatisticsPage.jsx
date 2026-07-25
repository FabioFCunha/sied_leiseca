import { useEffect, useMemo, useRef, useState } from "react";
import {
  Activity, AlertTriangle, ArrowRight, BarChart3, BookOpen, Building2,
  CalendarDays, Download, FileImage, FileSpreadsheet, Filter, Lightbulb,
  MapPin, Presentation, Printer, TrendingDown, TrendingUp, Users, X,
} from "lucide-react";
import {
  Bar, BarChart, CartesianGrid, Cell, ComposedChart, Legend, Line,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import { toPng } from "html-to-image";
import { api } from "../api/client.js";
import { formatLocalISODate } from "../utils/date.js";
import "./StatisticsPage.css";

const COLORS = ["#0048d7", "#7c3aed", "#059669", "#ea580c", "#db2777", "#0891b2", "#ca8a04", "#64748b", "#4f46e5", "#16a34a", "#dc2626"];
const MONTHS = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"];
const t = (value) => value;
const number = (value) => Number(value || 0).toLocaleString("pt-BR", { maximumFractionDigits: 1 });
const integer = (value) => Number(value || 0).toLocaleString("pt-BR", { maximumFractionDigits: 0 });
const iso = (value) => value instanceof Date ? formatLocalISODate(value) : value;
const queryString = (values) => new URLSearchParams(Object.entries(values).filter(([, value]) => value !== "" && value != null)).toString();

const KPI_DEFS = [
  ["AUDIENCE - Geral", "P\u00fablico alcan\u00e7ado", Users, COLORS[0]],
  ["EXPECTED_PUBLIC", "P\u00fablico previsto", Users, COLORS[2]],
  ["REPORTS_WITHOUT_PUBLIC", "Relat\u00f3rios sem p\u00fablico", AlertTriangle, COLORS[10]],
  ["ACTION - Geral", "A\u00e7\u00f5es educativas", CalendarDays, COLORS[2]],
  ["LECTURES - Geral", "Palestras", Presentation, COLORS[1]],
  ["STREET_ACTIONS - Geral", "A\u00e7\u00f5es de rua", Activity, COLORS[3]],
  ["MATERIAL - Geral", "Materiais distribu\u00eddos", BookOpen, COLORS[4]],
  ["MATERIAL - Soprinho", "Revistinhas distribu\u00eddas", BookOpen, COLORS[6]],
];
const HISTORICAL_ROWS = [
  ["AUDIENCE - Geral", "1 - P\u00fablico total"], ["AUDIENCE - PALESTRAS", "1.1 - P\u00fablico em palestras"], ["AUDIENCE - ACOES", "1.2 - P\u00fablico em a\u00e7\u00f5es"],
  ["LECTURES - Geral", "2 - Palestras realizadas"], ["ACTION - Escola", "2.1 - Escolas"], ["ACTION - Universidade", "2.2 - Universidades"], ["ACTION - Empresa", "2.3 - Empresas"],
  ["STREET_ACTIONS - Geral", "3 - A\u00e7\u00f5es de rua"], ["ACTION - Bares", "3.1 - Bares"], ["ACTION - Ped\u00e1gio", "3.2 - Ped\u00e1gio"], ["ACTION - Pra\u00e7as Esportivas", "3.3 - Esportes"],
  ["ACTION - Praia", "3.4 - Praia"], ["ACTION - Eventos", "3.5 - Eventos"], ["ACTION - Shopping", "3.6 - Shopping/Centro Comercial"], ["ACTION - A\u00e7\u00e3o Social", "3.7 - A\u00e7\u00e3o Social"],
  ["ACTION - Outros", "3.8 - Outros"], ["ACTION - Pra\u00e7as/Parques P\u00fablicos", "3.9 - Pra\u00e7as/Parques P\u00fablicos"], ["ACTION - Pontos tur\u00edsticos", "3.10 - Pontos tur\u00edsticos"],
  ["ACTION - A\u00e7\u00e3o conjunta com a fiscaliza\u00e7\u00e3o", "3.11 - A\u00e7\u00e3o conjunta com a fiscaliza\u00e7\u00e3o"], ["MATERIAL - Geral", "4 - Materiais de divulga\u00e7\u00e3o"], ["MATERIAL - Soprinho", "Revistinha Soprinho"],
];

function Empty({ children = "Sem dados para os filtros selecionados." }) { return <div className="stats-empty">{children}</div>; }
function Section({ icon: Icon, title, subtitle, children, actions, className = "" }) {
  return <section className={`stats-panel ${className}`}><header className="stats-panel-header"><div className="stats-panel-title"><span className="stats-icon"><Icon size={17}/></span><div><h2>{title}</h2>{subtitle && <p>{subtitle}</p>}</div></div>{actions && <div className="stats-panel-actions">{actions}</div>}</header><div className="stats-panel-body">{children}</div></section>;
}
function MetricCard({ definition, summary, previous, comparison, totalActions }) {
  const [key, label, Icon, color] = definition;
  const value = Number(summary?.[key] || 0);
  const prior = Number(previous?.[key] || 0);
  const pct = comparison?.[key]?.percentage;
  const Trend = pct < 0 ? TrendingDown : TrendingUp;
  const share = ["LECTURES - Geral", "STREET_ACTIONS - Geral"].includes(key) && totalActions ? (value / totalActions) * 100 : null;
  return <article className="stats-kpi" style={{ "--kpi": color }}><div className="stats-kpi-top"><span className="stats-kpi-icon"><Icon size={18}/></span><span>{label}</span></div><div className="stats-kpi-value">{number(value)}</div><div className={`stats-kpi-delta ${pct < 0 ? "is-down" : "is-up"}`}><Trend size={14}/>{pct == null ? (value ? "Novo" : "0,0%") : `${pct >= 0 ? "+" : ""}${pct.toFixed(1)}%`} <span>vs. {number(prior)}</span></div>{share != null && <small>{share.toFixed(1)}% do total</small>}</article>;
}
function MiniCard({ label, value, hint, icon: Icon = BarChart3, tone = COLORS[0] }) { return <div className="stats-mini-card"><span style={{ background: tone }}><Icon size={15}/></span><strong>{number(value)}</strong><small>{label}</small>{hint && <em>{hint}</em>}</div>; }
function ExecutiveBar({ rows }) {
  const total = rows.reduce((sum, row) => sum + Number(row.actions || 0), 0) || 1;
  const max = Math.max(...rows.map(row => Number(row.actions || 0)), 1);
  return <div className="stats-exec-bars">{rows.map((row, index) => { const pct = Number(row.actions || 0) / total * 100; return <button key={row.label} onClick={row.onClick} className="stats-exec-bar"><span className="stats-exec-label"><b>{row.label}</b><small>{integer(row.actions)} a\u00e7\u00f5es ? {integer(row.audience)} pessoas ? {pct.toFixed(1)}%</small></span><i><em style={{ width: `${Math.max(3, Number(row.actions || 0) / max * 100)}%`, background: row.color || COLORS[index % COLORS.length] }}/></i></button>; })}</div>;
}
function RankingTabs({ tabs }) { const [active, setActive] = useState(tabs[0]?.key); const tab = tabs.find(item => item.key === active) || tabs[0]; return <div><div className="stats-tabs">{tabs.map(item => <button key={item.key} className={item.key === active ? "active" : ""} onClick={() => setActive(item.key)}>{item.label}</button>)}</div><Ranking rows={tab.rows} nameKey={tab.nameKey}/></div>; }
function Ranking({ rows, nameKey }) { if (!rows?.length) return <Empty/>; const max = Math.max(...rows.map(row => Number(row.actions || 0)), 1); return <div className="stats-ranking">{rows.map((row, index) => <div className="stats-rank-row" key={`${row[nameKey]}-${index}`}><b>{index + 1}</b><span>{row[nameKey] || "N\u00e3o informado"}</span><div><i style={{ width: `${Number(row.actions || 0) / max * 100}%` }}/></div><strong>{number(row.actions)}</strong><small>{number(row.audience)} p\u00fablico</small></div>)}</div>; }
const parseExpected = (...values) => { for (const value of values) { const text = String(value ?? "").trim(); if (!text) continue; const nums = text.match(/\d+/g)?.map(Number); if (nums?.length) return Math.max(...nums); } return 0; };
const groupBy = (items, getLabel) => Object.values(items.reduce((acc, item) => { const label = getLabel(item) || "N\u00e3o informado"; acc[label] ||= { label, actions: 0, audience: 0 }; acc[label].actions += 1; acc[label].audience += parseExpected(item.audience, item.participant_range, item.quantity); return acc; }, {})).sort((a,b) => b.actions - a.actions);

export default function StatisticsPage() {
  const now = new Date(); const dashboardRef = useRef(null);
  const [filters, setFilters] = useState({ date_from: `${now.getFullYear()}-01-01`, date_to: iso(now), municipality: "", team: "", action_type: "", entity: "", institution: "" });
  const [pending, setPending] = useState(filters); const [options, setOptions] = useState({ municipalities: [], teams: [], action_types: [], entities: [], institutions: [] });
  const [data, setData] = useState(null); const [agendas, setAgendas] = useState([]); const [loading, setLoading] = useState(true); const [error, setError] = useState(""); const [drilldown, setDrilldown] = useState(null);
  useEffect(() => { api("/statistics/dashboard/filters/").then(setOptions).catch(() => {}); }, []);
  useEffect(() => { setLoading(true); setError(""); Promise.all([
    api(`/statistics/dashboard/?${queryString(filters)}`),
    api(`/agendas/?date_from=${filters.date_from}&date_to=${filters.date_to}&page_size=500`)
  ]).then(([stats, agendaResult]) => { setData(stats); setAgendas(agendaResult.results || agendaResult || []); }).catch(err => setError(err.message)).finally(() => setLoading(false)); }, [filters]);

  const annual = useMemo(() => (data?.annual || []).map(row => ({ year: row.year, ...row.values })), [data]);
  const visualMonthly = useMemo(() => (data?.visual_monthly || data?.monthly || []).map(row => ({ month: MONTHS[row.month - 1], actions: Number(row.values["ACTION - Geral"] || 0), audience: Number(row.values["AUDIENCE - Geral"] || 0), lectures: Number(row.values["LECTURES - Geral"] || 0), street: Number(row.values["STREET_ACTIONS - Geral"] || 0) })), [data]);
  const categoryData = useMemo(() => (data?.categories || []).map((row, index) => ({ ...row, value: Number(row.value || 0), actions: Number(row.value || 0), audience: Number(row.audience || 0), color: COLORS[index % COLORS.length] })).sort((a,b) => b.value - a.value), [data]);
  const totalActions = Number(data?.summary?.["ACTION - Geral"] || 0); const reached = Number(data?.summary?.["AUDIENCE - Geral"] || 0); const expected = Number(data?.summary?.EXPECTED_PUBLIC || 0);
  const demand = useMemo(() => { const total = agendas.length; const publicForm = agendas.filter(a => a.origin === "PUBLIC_FORM").length; const internal = agendas.filter(a => a.origin === "INTERNAL").length; const approved = agendas.filter(a => ["APPROVED", "COMPLETED"].includes(a.status)).length; const cancelled = agendas.filter(a => a.status === "CANCELLED").length; const refused = agendas.filter(a => ["REJECTED", "REFUSED"].includes(a.status)).length; return { total, publicForm, internal, approved, cancelled, refused, executed: totalActions, expected, reached, conversion: total ? totalActions / total * 100 : 0, realization: expected ? reached / expected * 100 : 0 }; }, [agendas, totalActions, expected, reached]);
  const demandOrigins = useMemo(() => groupBy(agendas, a => a.origin === "PUBLIC_FORM" ? "Solicita\u00e7\u00e3o p\u00fablica" : "Solicita\u00e7\u00e3o interna"), [agendas]);
  const requesterProfile = useMemo(() => groupBy(agendas, a => a.requester_entity_type || a.action_type || a.audience), [agendas]);
  const actionProfile = useMemo(() => groupBy(agendas, a => a.action_type || "N\u00e3o informado"), [agendas]);
  const municipalities = data?.municipalities || []; const teams = data?.teams || [];
  const bestTeam = teams[0] || {}; const bestAudienceTeam = [...teams].sort((a,b) => Number(b.audience||0)-Number(a.audience||0))[0] || {}; const topCategory = categoryData[0] || {};
  const insights = [
    `${topCategory.label || "Categoria principal"} representa ${totalActions ? (Number(topCategory.value || 0) / totalActions * 100).toFixed(1) : "0,0"}% das a\u00e7\u00f5es.`,
    `${bestTeam.team || "Equipe"} lidera em volume com ${integer(bestTeam.actions)} a\u00e7\u00f5es.`,
    `${bestAudienceTeam.team || "Equipe"} alcan\u00e7ou o maior p\u00fablico: ${integer(bestAudienceTeam.audience)} pessoas.`,
    `Existem ${integer(data?.summary?.REPORTS_WITHOUT_PUBLIC)} relat\u00f3rios aprovados sem p\u00fablico informado.`,
    `O p\u00fablico realizado corresponde a ${demand.realization.toFixed(1)}% da demanda prevista.`,
  ];
  const comparisonLabel = data?.period?.comparison_label || data?.metadata?.comparison_label || "per\u00edodo anterior";
  const reset = () => { const base = { date_from: `${now.getFullYear()}-01-01`, date_to: iso(now), municipality: "", team: "", action_type: "", entity: "", institution: "" }; setPending(base); setFilters(base); };
  const exportExcel = () => { const years = annual.map(row => row.year); const lines = [["Indicador", ...years], ...HISTORICAL_ROWS.map(([key, label]) => [label, ...annual.map(row => row[key] || 0)])]; const blob = new Blob(["\ufeff" + lines.map(line => line.join("\t")).join("\n")], { type: "application/vnd.ms-excel;charset=utf-8" }); const link = document.createElement("a"); link.href = URL.createObjectURL(blob); link.download = "estatisticas-sied.xls"; link.click(); URL.revokeObjectURL(link.href); };
  const exportCsv = async () => { const blob = await api(`/statistics/dashboard/export.csv?${queryString(filters)}`); const link = document.createElement("a"); link.href = URL.createObjectURL(blob); link.download = "estatisticas-sied.csv"; link.click(); URL.revokeObjectURL(link.href); };
  const exportImage = async () => { const dataUrl = await toPng(dashboardRef.current, { cacheBust: true, pixelRatio: 1.5, backgroundColor: "#f4f7fb" }); const link = document.createElement("a"); link.href = dataUrl; link.download = "dashboard-estatisticas-sied.png"; link.click(); };
  if (loading) return <section className="stats-dashboard"><div className="stats-loading">Carregando painel executivo...</div></section>; if (error) return <section className="stats-dashboard"><div className="alert">N\u00e3o foi poss\u00edvel carregar o dashboard: {error}</div></section>;

  return <section className="stats-dashboard" ref={dashboardRef}>
    <header className="stats-hero"><div><span>Intelig\u00eancia institucional</span><h1>Dashboard Executivo SIED</h1><p>Demanda recebida, produ\u00e7\u00e3o executada e resultados oficiais em uma vis\u00e3o de gest\u00e3o.</p></div><div className="stats-export"><button onClick={() => window.print()}><Printer size={16}/>PDF</button><button onClick={exportExcel}><FileSpreadsheet size={16}/>Excel</button><button onClick={exportCsv}><Download size={16}/>CSV</button><button onClick={exportImage}><FileImage size={16}/>Imagem</button></div></header>
    <div className="stats-filters"><div className="stats-filter-title"><Filter size={17}/>Filtros globais</div><label>De<input type="date" value={pending.date_from} onChange={e => setPending(v => ({ ...v, date_from: e.target.value }))}/></label><label>At\u00e9<input type="date" value={pending.date_to} onChange={e => setPending(v => ({ ...v, date_to: e.target.value }))}/></label><label>Munic\u00edpio<select value={pending.municipality} onChange={e => setPending(v => ({ ...v, municipality: e.target.value }))}><option value="">Todos</option>{options.municipalities.map(v => <option key={v}>{v}</option>)}</select></label><label>Equipe<select value={pending.team} onChange={e => setPending(v => ({ ...v, team: e.target.value }))}><option value="">Todas</option>{options.teams.map(v => <option key={v}>{v}</option>)}</select></label><label>Tipo<select value={pending.action_type} onChange={e => setPending(v => ({ ...v, action_type: e.target.value }))}><option value="">Todos</option>{options.action_types.map(v => <option key={v}>{v}</option>)}</select></label><label>Categoria<select value={pending.entity} onChange={e => setPending(v => ({ ...v, entity: e.target.value }))}><option value="">Todas</option>{options.entities.map(v => <option key={v}>{v}</option>)}</select></label><label>Institui\u00e7\u00e3o<select value={pending.institution} onChange={e => setPending(v => ({ ...v, institution: e.target.value }))}><option value="">Todas</option>{options.institutions.map(v => <option key={v}>{v}</option>)}</select></label><div className="stats-filter-actions"><button className="primary" onClick={() => setFilters(pending)}>Aplicar</button><button onClick={reset}>Limpar</button></div></div>
    <div className="stats-kpi-grid">{KPI_DEFS.map(def => <MetricCard key={def[0]} definition={def} summary={data.summary} previous={data.previous} comparison={data.comparisons} totalActions={totalActions}/>)}</div>
    <Section icon={ArrowRight} title="Produ\u00e7\u00e3o x demanda" subtitle="Fluxo gerencial entre solicita\u00e7\u00f5es recebidas e execu\u00e7\u00e3o realizada."><div className="stats-flow"><MiniCard label="Recebidas" value={demand.total} hint={`${integer(demand.publicForm)} p\u00fablicas ? ${integer(demand.internal)} internas`}/><ArrowRight/><MiniCard label="Aprovadas" value={demand.approved}/><ArrowRight/><MiniCard label="Executadas" value={demand.executed}/><ArrowRight/><MiniCard label="Pessoas alcan\u00e7adas" value={demand.reached}/></div><div className="stats-demand-grid"><MiniCard label="Canceladas" value={demand.cancelled} tone={COLORS[10]}/><MiniCard label="Recusadas" value={demand.refused} tone={COLORS[7]}/><MiniCard label="P\u00fablico previsto" value={demand.expected} tone={COLORS[2]}/><MiniCard label="Taxa de convers\u00e3o" value={demand.conversion} hint="execu\u00e7\u00f5es / recebidas" tone={COLORS[1]}/></div></Section>
    <Section icon={TrendingUp} title="Evolu\u00e7\u00e3o temporal" subtitle="A\u00e7\u00f5es e p\u00fablico alcan\u00e7ado por m\u00eas, no mesmo gr\u00e1fico."><div className="stats-chart-xl"><ResponsiveContainer><ComposedChart data={visualMonthly}><CartesianGrid strokeDasharray="3 3"/><XAxis dataKey="month"/><YAxis yAxisId="left"/><YAxis yAxisId="right" orientation="right"/><Tooltip formatter={number}/><Legend/><Bar yAxisId="left" dataKey="actions" name="A\u00e7\u00f5es" fill={COLORS[0]} radius={[6,6,0,0]}/><Line yAxisId="right" type="monotone" dataKey="audience" name="P\u00fablico" stroke={COLORS[3]} strokeWidth={3}/></ComposedChart></ResponsiveContainer></div></Section>
    <div className="stats-three-columns"><Section icon={BarChart3} title="Distribui\u00e7\u00e3o" subtitle="Categoria, quantidade, p\u00fablico e participa\u00e7\u00e3o."><ExecutiveBar rows={categoryData.map(row => ({ label: row.label, actions: row.value, audience: row.audience, color: row.color, onClick: () => setDrilldown(row) }))}/></Section><Section icon={Building2} title="Origem das solicita\u00e7\u00f5es" subtitle="Demanda recebida por canal."><ExecutiveBar rows={demandOrigins}/></Section><Section icon={Users} title="Perfil da demanda" subtitle="Tipo de solicitante e modalidade pretendida."><ExecutiveBar rows={[...requesterProfile.slice(0,5), ...actionProfile.slice(0,4)]}/></Section></div>
    <Section icon={Activity} title="Efici\u00eancia operacional" subtitle="Sinais r\u00e1pidos para tomada de decis\u00e3o."><div className="stats-demand-grid"><MiniCard label="Equipe com mais a\u00e7\u00f5es" value={bestTeam.actions} hint={bestTeam.team}/><MiniCard label="Maior p\u00fablico" value={bestAudienceTeam.audience} hint={bestAudienceTeam.team}/><MiniCard label="M\u00e9dia por a\u00e7\u00e3o" value={data.summary?.["AVERAGE_AUDIENCE"]}/><MiniCard label="Relat\u00f3rios sem p\u00fablico" value={data.summary?.REPORTS_WITHOUT_PUBLIC} tone={COLORS[10]}/><MiniCard label="Materiais" value={data.summary?.["MATERIAL - Geral"]}/><MiniCard label="Revistinhas" value={data.summary?.["MATERIAL - Soprinho"]}/></div></Section>
    <div className="stats-two-columns"><Section icon={MapPin} title="Indicadores geogr\u00e1ficos" subtitle="Munic\u00edpios com produ\u00e7\u00e3o no per\u00edodo."><Ranking rows={municipalities} nameKey="agenda__city"/></Section><Section icon={BarChart3} title="Ranking" subtitle="Categorias, equipes e munic\u00edpios no mesmo componente."><RankingTabs tabs={[{ key:"cat", label:"Categorias", rows: categoryData.map(row => ({ label: row.label, actions: row.value, audience: row.audience })), nameKey:"label" }, { key:"teams", label:"Equipes", rows: teams, nameKey:"team" }, { key:"mun", label:"Munic\u00edpios", rows: municipalities, nameKey:"agenda__city" }]}/></Section></div>
    <Section icon={Lightbulb} title="Insights autom\u00e1ticos" subtitle={`Compara\u00e7\u00e3o com ${comparisonLabel}.`}><div className="stats-insights">{insights.map((insight, index) => <p key={index}>{insight}</p>)}</div></Section>
    <Section icon={BarChart3} title="S\u00e9rie hist\u00f3rica completa" subtitle="Tabela institucional mantida para auditoria e exporta\u00e7\u00e3o."><div className="stats-table-wrap"><table className="stats-table stats-history-table"><thead><tr><th>Indicador</th>{annual.map(row => <th key={row.year}>{row.year}</th>)}</tr></thead><tbody>{HISTORICAL_ROWS.map(([key, label]) => <tr key={key}><td>{label}</td>{annual.map(row => <td key={row.year}>{number(row[key])}</td>)}</tr>)}</tbody></table></div></Section>
    {drilldown && <div className="stats-drilldown"><div><button onClick={() => setDrilldown(null)}><X size={18}/></button><span>Detalhamento</span><h3>{drilldown.label}</h3><p>Total no per\u00edodo: <strong>{number(drilldown.value)}</strong></p><p>P\u00fablico: <strong>{number(drilldown.audience)}</strong></p></div></div>}
    <footer className="stats-methodology">Fonte: banco de dados SIED ? demanda das agendas + produ\u00e7\u00e3o dos relat\u00f3rios aprovados.</footer>
  </section>;
}
