import { useEffect, useMemo, useRef, useState } from "react";
import {
  Activity, Award, BarChart3, BookOpen, Building2, CalendarDays,
  Download, FileImage, FileSpreadsheet, Filter, MapPin, Presentation,
  Printer, TrendingDown, TrendingUp, Users, X,
} from "lucide-react";
import {
  Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, ComposedChart,
  Legend, Line, LineChart, Pie, PieChart, ResponsiveContainer, Tooltip,
  XAxis, YAxis,
} from "recharts";
import { toPng } from "html-to-image";
import { api } from "../api/client.js";
import { formatLocalISODate } from "../utils/date.js";
import "./StatisticsPage.css";

const COLORS = ["#2563eb", "#7c3aed", "#059669", "#ea580c", "#db2777", "#0891b2", "#ca8a04", "#64748b", "#4f46e5", "#16a34a", "#dc2626"];
const MONTHS = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"];
const SERIES = [
  ["audience", "Público total", "AUDIENCE - Geral", COLORS[0]],
  ["lectureAudience", "Público em palestras", "AUDIENCE - PALESTRAS", COLORS[1]],
  ["streetAudience", "Público em ações", "AUDIENCE - ACOES", COLORS[2]],
  ["actions", "Total de ações", "ACTION - Geral", COLORS[3]],
  ["materials", "Materiais", "MATERIAL - Geral", COLORS[4]],
  ["certificates", "Certificados", "MATERIAL - Certificados", COLORS[5]],
  ["comics", "Revistinhas", "MATERIAL - Soprinho", COLORS[6]],
];
const KPI_DEFS = [
  ["AUDIENCE - Geral", "Público alcançado", Users, COLORS[0]],
  ["ACTION - Geral", "Ações educativas", CalendarDays, COLORS[2]],
  ["LECTURES - Geral", "Palestras", Presentation, COLORS[1]],
  ["STREET_ACTIONS - Geral", "Ações de rua", Activity, COLORS[3]],
  ["MATERIAL - Geral", "Materiais distribuídos", BookOpen, COLORS[4]],
  ["MATERIAL - Certificados", "Certificados entregues", Award, COLORS[5]],
  ["MATERIAL - Soprinho", "Revistinhas distribuídas", BookOpen, COLORS[6]],
  ["AVERAGE_AUDIENCE", "Média de público por ação", BarChart3, COLORS[8]],
];
const HISTORICAL_ROWS = [
  ["AUDIENCE - Geral", "1 - Público total"],
  ["AUDIENCE - PALESTRAS", "1.1 - Público em palestras"],
  ["AUDIENCE - ACOES", "1.2 - Público em ações"],
  ["LECTURES - Geral", "2 - Palestras realizadas"],
  ["ACTION - Escola", "2.1 - Escolas"],
  ["ACTION - Universidade", "2.2 - Universidades"],
  ["ACTION - Empresa", "2.3 - Empresas"],
  ["MATERIAL - Certificados", "2.4 - Certificados entregues"],
  ["STREET_ACTIONS - Geral", "3 - Ações de rua"],
  ["ACTION - Bares", "3.1 - Bares"],
  ["ACTION - Pedágio", "3.2 - Pedágio"],
  ["ACTION - Praças Esportivas", "3.3 - Esportes"],
  ["ACTION - Praia", "3.4 - Praia"],
  ["ACTION - Eventos", "3.5 - Eventos"],
  ["ACTION - Shopping", "3.6 - Shopping/Centro Comercial"],
  ["ACTION - Ação Social", "3.7 - Ação Social"],
  ["ACTION - Outros", "3.8 - Outros"],
  ["ACTION - Praças/Parques Públicos", "3.9 - Praças/Parques Públicos"],
  ["ACTION - Pontos turísticos", "3.10 - Pontos turísticos"],
  ["ACTION - Fiscalização", "3.11 - Fiscalização"],
  ["MATERIAL - Geral", "4 - Materiais de divulgação"],
  ["MATERIAL - Soprinho", "Revistinha Soprinho"],
];

const number = value => Number(value || 0).toLocaleString("pt-BR", { maximumFractionDigits: 1 });
const iso = value => value instanceof Date ? formatLocalISODate(value) : value;
const queryString = values => new URLSearchParams(Object.entries(values).filter(([, value]) => value !== "" && value != null)).toString();

function Empty({ children = "Sem dados para os filtros selecionados." }) {
  return <div className="stats-empty">{children}</div>;
}

function Section({ icon: Icon, title, subtitle, children, actions }) {
  return (
    <section className="stats-panel">
      <header className="stats-panel-header">
        <div className="stats-panel-title"><span className="stats-icon"><Icon size={17} /></span><div><h2>{title}</h2>{subtitle && <p>{subtitle}</p>}</div></div>
        {actions && <div className="stats-panel-actions">{actions}</div>}
      </header>
      <div className="stats-panel-body">{children}</div>
    </section>
  );
}

function MetricCard({ definition, summary, previous, comparison, sparkline, totalActions }) {
  const [key, label, Icon, color] = definition;
  const value = Number(summary?.[key] || 0);
  const prior = Number(previous?.[key] || 0);
  const delta = comparison?.[key] || {};
  const pct = delta.percentage;
  const share = ["LECTURES - Geral", "STREET_ACTIONS - Geral"].includes(key) && totalActions ? (value / totalActions) * 100 : null;
  const monthlyAverage = key === "ACTION - Geral" ? value / Math.max(new Date().getMonth() + 1, 1) : null;
  const Trend = pct < 0 ? TrendingDown : TrendingUp;
  return (
    <article className="stats-kpi" style={{ "--kpi": color }}>
      <div className="stats-kpi-top"><span className="stats-kpi-icon"><Icon size={18} /></span><span>{label}</span></div>
      <div className="stats-kpi-value">{number(value)}</div>
      <div className={`stats-kpi-delta ${pct < 0 ? "is-down" : "is-up"}`}><Trend size={14} />{pct == null ? (value ? "Novo" : "0,0%") : `${pct >= 0 ? "+" : ""}${pct.toFixed(1)}%`} <span>vs. {number(prior)}</span></div>
      {share != null && <small>{share.toFixed(1)}% do total de ações</small>}
      {monthlyAverage != null && <small>Média mensal: {number(monthlyAverage)}</small>}
      {sparkline?.length > 1 && <div className="stats-spark"><ResponsiveContainer><LineChart data={sparkline}><Line dataKey={key} stroke={color} strokeWidth={2} dot={false} /></LineChart></ResponsiveContainer></div>}
    </article>
  );
}

function Heatmap({ rows }) {
  if (!rows?.length) return <Empty />;
  const max = Math.max(...rows.map(row => Number(row.actions || 0)), 1);
  return <div className="stats-heatmap">{rows.map(row => <div key={row.operation_date} className="stats-heat-cell" style={{ opacity: .18 + .82 * Number(row.actions || 0) / max }} title={`${row.operation_date}: ${number(row.actions)} ações · público ${number(row.audience)}`}><span>{new Date(`${row.operation_date}T12:00:00`).getDate()}</span></div>)}</div>;
}

function Ranking({ rows, nameKey }) {
  if (!rows?.length) return <Empty />;
  const max = Math.max(...rows.map(row => Number(row.actions || 0)), 1);
  return <div className="stats-ranking">{rows.map((row, index) => <div className="stats-rank-row" key={`${row[nameKey]}-${index}`}><b>{index + 1}</b><span>{row[nameKey] || "Não informado"}</span><div><i style={{ width: `${Number(row.actions || 0) / max * 100}%` }} /></div><strong>{number(row.actions)}</strong><small>{number(row.audience)} público</small></div>)}</div>;
}

export default function StatisticsPage() {
  const now = new Date();
  const dashboardRef = useRef(null);
  const [filters, setFilters] = useState({ date_from: `${now.getFullYear()}-01-01`, date_to: iso(now), municipality: "", team: "", action_type: "", entity: "", institution: "" });
  const [pending, setPending] = useState(filters);
  const [options, setOptions] = useState({ municipalities: [], teams: [], action_types: [], entities: [], institutions: [] });
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [seriesMode, setSeriesMode] = useState("quantity");
  const [activeSeries, setActiveSeries] = useState(Object.fromEntries(SERIES.map(([key]) => [key, true])));
  const [drilldown, setDrilldown] = useState(null);

  useEffect(() => { api("/statistics/dashboard/filters/").then(setOptions).catch(() => {}); }, []);
  useEffect(() => {
    setLoading(true); setError("");
    api(`/statistics/dashboard/?${queryString(filters)}`).then(setData).catch(err => setError(err.message)).finally(() => setLoading(false));
  }, [filters]);

  const annual = useMemo(() => (data?.annual || []).map(row => ({ year: row.year, ...row.values, ...Object.fromEntries(SERIES.map(([alias,, key]) => [alias, Number(row.values[key] || 0)])) })), [data]);
  const monthly = useMemo(() => (data?.monthly || []).map(row => ({ month: MONTHS[row.month - 1], ...row.values, audience: Number(row.values["AUDIENCE - Geral"] || 0), lectures: Number(row.values["LECTURES - Geral"] || 0), street: Number(row.values["STREET_ACTIONS - Geral"] || 0) })), [data]);
  const categoryData = useMemo(() => (data?.categories || []).map((row, index) => ({ ...row, value: Number(row.value || 0), audience: Number(row.audience || 0), color: COLORS[index % COLORS.length] })).sort((a, b) => b.value - a.value), [data]);
  const totalActions = Number(data?.summary?.["ACTION - Geral"] || 0);
  const latestYears = annual.slice(-5);
  const projection = useMemo(() => {
    const selectedMonth = new Date(filters.date_to + "T12:00:00").getMonth();
    const realizedTotal = monthly.slice(0, selectedMonth + 1).reduce((sum, row) => sum + Number(row.audience || 0), 0);
    const monthlyPace = realizedTotal / Math.max(selectedMonth + 1, 1);
    let cumulative = 0;
    return monthly.map((row, index) => {
      if (index <= selectedMonth) cumulative += Number(row.audience || 0);
      return { ...row, realized: index <= selectedMonth ? cumulative : null, projection: Math.round(monthlyPace * (index + 1)) };
    });
  }, [monthly, filters.date_to]);

  const reset = () => { const base = { date_from: `${now.getFullYear()}-01-01`, date_to: iso(now), municipality: "", team: "", action_type: "", entity: "", institution: "" }; setPending(base); setFilters(base); };
  const exportExcel = () => {
    const years = annual.map(row => row.year);
    const lines = [["Indicador", ...years], ...HISTORICAL_ROWS.map(([key, label]) => [label, ...annual.map(row => row[key] || 0)])];
    const blob = new Blob(["\ufeff" + lines.map(line => line.join("\t")).join("\n")], { type: "application/vnd.ms-excel;charset=utf-8" });
    const link = document.createElement("a"); link.href = URL.createObjectURL(blob); link.download = "estatisticas-sied.xls"; link.click(); URL.revokeObjectURL(link.href);
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
  };

  if (loading) return <section className="stats-dashboard"><div className="stats-loading">Carregando painel executivo…</div></section>;
  if (error) return <section className="stats-dashboard"><div className="alert">Não foi possível carregar o dashboard: {error}</div></section>;

  return (
    <section className="stats-dashboard" ref={dashboardRef}>
      <header className="stats-hero"><div><span>Inteligência institucional</span><h1>Estatísticas Oficiais SIED</h1><p>Indicadores históricos e operacionais consolidados pela metodologia oficial.</p></div><div className="stats-export"><button onClick={() => window.print()}><Printer size={16}/>PDF</button><button onClick={exportExcel}><FileSpreadsheet size={16}/>Excel</button><button onClick={exportCsv}><Download size={16}/>CSV</button><button onClick={exportImage}><FileImage size={16}/>Imagem</button></div></header>

      <div className="stats-filters"><div className="stats-filter-title"><Filter size={17}/>Filtros globais</div><label>De<input type="date" value={pending.date_from} onChange={e => setPending(v => ({ ...v, date_from: e.target.value }))}/></label><label>Até<input type="date" value={pending.date_to} onChange={e => setPending(v => ({ ...v, date_to: e.target.value }))}/></label><label>Município<select value={pending.municipality} onChange={e => setPending(v => ({ ...v, municipality: e.target.value }))}><option value="">Todos</option>{options.municipalities.map(v => <option key={v}>{v}</option>)}</select></label><label>Equipe<select value={pending.team} onChange={e => setPending(v => ({ ...v, team: e.target.value }))}><option value="">Todas</option>{options.teams.map(v => <option key={v}>{v}</option>)}</select></label><label>Tipo<select value={pending.action_type} onChange={e => setPending(v => ({ ...v, action_type: e.target.value }))}><option value="">Todos</option>{options.action_types.map(v => <option key={v}>{v}</option>)}</select></label><label>Categoria<select value={pending.entity} onChange={e => setPending(v => ({ ...v, entity: e.target.value }))}><option value="">Todas</option>{options.entities.map(v => <option key={v}>{v}</option>)}</select></label><label>Instituição<select value={pending.institution} onChange={e => setPending(v => ({ ...v, institution: e.target.value }))}><option value="">Todas</option>{options.institutions.map(v => <option key={v}>{v}</option>)}</select></label><div className="stats-filter-actions"><button className="primary" onClick={() => setFilters(pending)}>Aplicar</button><button onClick={reset}>Limpar</button></div></div>

      <div className="stats-kpi-grid">{KPI_DEFS.map(def => <MetricCard key={def[0]} definition={def} summary={data.summary} previous={data.previous} comparison={data.comparisons} sparkline={annual.slice(-6)} totalActions={totalActions}/>)}</div>

      <Section icon={TrendingUp} title="Série histórica institucional" subtitle="Ative ou desative os indicadores para comparar a evolução anual."><div className="stats-series-switches">{SERIES.map(([alias, label,, color]) => <label key={alias}><input type="checkbox" checked={activeSeries[alias]} onChange={() => setActiveSeries(v => ({ ...v, [alias]: !v[alias] }))}/><i style={{ background: color }}/>{label}</label>)}</div><div className="stats-chart-xl">{annual.length ? <ResponsiveContainer><LineChart data={annual} margin={{ top: 15, right: 25, bottom: 5, left: 10 }}><CartesianGrid strokeDasharray="3 3"/><XAxis dataKey="year"/><YAxis tickFormatter={number}/><Tooltip formatter={number}/><Legend/>{SERIES.map(([alias, label,, color]) => activeSeries[alias] && <Line key={alias} type="monotone" dataKey={alias} name={label} stroke={color} strokeWidth={3} dot={{ r: 3 }} connectNulls/>)}</LineChart></ResponsiveContainer> : <Empty>Importe a série histórica oficial para visualizar 2011–2026.</Empty>}</div></Section>

      <div className="stats-two-columns"><Section icon={CalendarDays} title="Evolução mensal" subtitle="Janeiro a dezembro no período selecionado." actions={<div className="stats-segmented"><button className={seriesMode === "quantity" ? "active" : ""} onClick={() => setSeriesMode("quantity")}>Quantidade</button><button className={seriesMode === "audience" ? "active" : ""} onClick={() => setSeriesMode("audience")}>Público</button></div>}><div className="stats-chart"><ResponsiveContainer><LineChart data={monthly}><CartesianGrid strokeDasharray="3 3"/><XAxis dataKey="month"/><YAxis tickFormatter={number}/><Tooltip formatter={number}/>{seriesMode === "audience" ? <Line type="monotone" dataKey="audience" name="Público" stroke={COLORS[0]} strokeWidth={3}/> : <><Line type="monotone" dataKey="lectures" name="Palestras" stroke={COLORS[1]} strokeWidth={3}/><Line type="monotone" dataKey="street" name="Ações de rua" stroke={COLORS[2]} strokeWidth={3}/></>}</LineChart></ResponsiveContainer></div></Section><Section icon={Activity} title="Palestras × ações de rua" subtitle="Comparativo mensal por modalidade."><div className="stats-chart"><ResponsiveContainer><BarChart data={monthly}><CartesianGrid strokeDasharray="3 3"/><XAxis dataKey="month"/><YAxis/><Tooltip formatter={number}/><Legend/><Bar dataKey="lectures" name="Palestras" fill={COLORS[1]} radius={[5,5,0,0]}/><Bar dataKey="street" name="Ações de rua" fill={COLORS[2]} radius={[5,5,0,0]}/></BarChart></ResponsiveContainer></div></Section></div>

      <div className="stats-two-columns"><Section icon={Activity} title="Distribuição das ações" subtitle="Participação percentual por categoria."><div className="stats-chart"><ResponsiveContainer><PieChart><Pie data={categoryData} dataKey="value" nameKey="label" innerRadius="52%" outerRadius="78%" paddingAngle={2} onClick={entry => setDrilldown(entry)}>{categoryData.map((entry, index) => <Cell key={entry.key} fill={COLORS[index % COLORS.length]}/>)}</Pie><Tooltip formatter={number}/><Legend layout="vertical" verticalAlign="middle" align="right"/></PieChart></ResponsiveContainer></div></Section><Section icon={Users} title="Público e volume por categoria" subtitle="Ranking operacional das categorias selecionadas."><div className="stats-chart"><ResponsiveContainer><BarChart data={categoryData.slice(0, 10)} layout="vertical" margin={{ left: 30 }}><CartesianGrid strokeDasharray="3 3"/><XAxis type="number"/><YAxis dataKey="label" type="category" width={125}/><Tooltip formatter={number}/><Bar dataKey="audience" name="Público" radius={[0,6,6,0]} onClick={entry => setDrilldown(entry)}>{categoryData.map((entry, index) => <Cell key={entry.key} fill={COLORS[index % COLORS.length]}/>)}</Bar></BarChart></ResponsiveContainer></div></Section></div>

      <div className="stats-two-columns"><Section icon={BarChart3} title="Evolução anual" subtitle="Total de ações educativas nos últimos anos."><div className="stats-chart"><ResponsiveContainer><BarChart data={latestYears}><CartesianGrid strokeDasharray="3 3"/><XAxis dataKey="year"/><YAxis/><Tooltip formatter={number}/><Bar dataKey="ACTION - Geral" name="Ações" fill={COLORS[0]} radius={[6,6,0,0]}/></BarChart></ResponsiveContainer></div></Section><Section icon={TrendingUp} title="Realizado × projeção" subtitle="Ritmo acumulado e tendência até dezembro."><div className="stats-chart"><ResponsiveContainer><ComposedChart data={projection}><CartesianGrid strokeDasharray="3 3"/><XAxis dataKey="month"/><YAxis/><Tooltip formatter={number}/><Area dataKey="realized" name="Realizado" fill={COLORS[0]} stroke={COLORS[0]} fillOpacity={.18}/><Line dataKey="projection" name="Projeção" stroke={COLORS[3]} strokeDasharray="7 5" strokeWidth={3}/></ComposedChart></ResponsiveContainer></div></Section></div>

      <div className="stats-two-columns"><Section icon={BarChart3} title="Ranking de categorias" subtitle="Ordenação automática pelo volume de ações."><Ranking rows={categoryData.map(row => ({ label: row.label, actions: row.value, audience: row.audience }))} nameKey="label"/></Section><Section icon={Building2} title="Ranking de equipes" subtitle="Ações, público e média por equipe."><Ranking rows={data.teams} nameKey="team"/></Section></div>
      <div className="stats-two-columns"><Section icon={MapPin} title="Indicadores por município" subtitle="Disponível para os relatórios operacionais do SIED."><Ranking rows={data.municipalities} nameKey="agenda__city"/></Section><Section icon={CalendarDays} title="Calendário de calor" subtitle="Intensidade diária de ações; passe o cursor para detalhes."><Heatmap rows={data.heatmap}/></Section></div>

      <Section icon={BarChart3} title="Comparativo de categorias" subtitle="Período selecionado × mesmo período do ano anterior."><div className="stats-table-wrap"><table className="stats-table"><thead><tr><th>Categoria</th><th>Anterior</th><th>Atual</th><th>Diferença</th><th>Variação</th><th>Projeção</th></tr></thead><tbody>{categoryData.map(row => { const diff = row.value - Number(row.previous || 0); const pct = row.previous ? diff / row.previous * 100 : null; return <tr key={row.key} onClick={() => setDrilldown(row)}><td>{row.label}</td><td>{number(row.previous)}</td><td>{number(row.value)}</td><td className={diff < 0 ? "negative" : "positive"}>{diff >= 0 ? "+" : ""}{number(diff)}</td><td>{pct == null ? (row.value ? "Novo" : "0,0%") : `${pct >= 0 ? "+" : ""}${pct.toFixed(1)}%`}</td><td>{number(row.value * 12 / Math.max(new Date(filters.date_to + "T12:00:00").getMonth() + 1, 1))}</td></tr>; })}</tbody></table></div></Section>

      <Section icon={BarChart3} title="Série histórica completa" subtitle="Todos os indicadores da metodologia institucional, sem comparação percentual."><div className="stats-table-wrap"><table className="stats-table stats-history-table"><thead><tr><th>Indicador</th>{annual.map(row => <th key={row.year}>{row.year}</th>)}</tr></thead><tbody>{HISTORICAL_ROWS.map(([key, label]) => <tr key={key}><td>{label}</td>{annual.map(row => <td key={row.year}>{number(row[key])}</td>)}</tr>)}</tbody></table></div></Section>

      {drilldown && <div className="stats-drilldown"><div><button onClick={() => setDrilldown(null)}><X size={18}/></button><span>Detalhamento</span><h3>{drilldown.label}</h3><p>Total no período: <strong>{number(drilldown.value)}</strong></p><p>Use os filtros globais para detalhar por município, equipe ou instituição.</p></div></div>}
      <footer className="stats-methodology">Fonte: banco de dados SIED · Série histórica oficial + relatórios operacionais aprovados · Dimensões de município e equipe disponíveis a partir do início operacional do SIED.</footer>
    </section>
  );
}
