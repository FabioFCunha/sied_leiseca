import { Download } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { api } from "../api/client.js";
import { defaultGoalRows, flattenGoalRows } from "../utils/educationGoals.js";

const statusOptions = [
  { value: "", label: "Todos os relatórios" },
  { value: "DRAFT", label: "Rascunhos" },
  { value: "SUBMITTED", label: "Enviados" },
];

function formatNumber(value) {
  return Number(value || 0).toLocaleString("pt-BR");
}

function getCurrentYearFilters() {
  const today = new Date();
  const year = today.getFullYear();
  return {
    date_from: `${year}-01-01`,
    date_to: today.toISOString().slice(0, 10),
    status: "",
  };
}

function getReferenceDate(filters) {
  const fallback = new Date().toISOString().slice(0, 10);
  const rawDate = filters.date_to || fallback;
  const parsed = new Date(`${rawDate}T00:00:00`);
  return Number.isNaN(parsed.getTime()) ? new Date(`${fallback}T00:00:00`) : parsed;
}

function buildAnnualSeries(rows = [], field) {
  const totalsByYear = rows.reduce((accumulator, item) => {
    accumulator[item.year] = (accumulator[item.year] || 0) + Number(item[field] || 0);
    return accumulator;
  }, {});
  return Object.entries(totalsByYear)
    .map(([year, value]) => ({ label: year, value }))
    .sort((a, b) => Number(a.label) - Number(b.label));
}

function AnnualLineChart({ title, subtitle, data = [], color = "#0048d7" }) {
  const max = Math.max(...data.map((item) => item.value), 1);
  const chartPoints = data.map((item, index) => {
    const x = data.length <= 1 ? 50 : (index / (data.length - 1)) * 100;
    const y = 100 - (item.value / max) * 82 - 9;
    return { ...item, x, y };
  });
  const points = chartPoints.map((point) => `${point.x},${point.y}`).join(" ");

  return (
    <div className="chart-card statistics-line-chart year-comparison-chart">
      <div className="section-heading">
        <div>
          <h2>{title}</h2>
          <p>{subtitle}</p>
        </div>
      </div>
      <div className="line-chart-wrap">
        <svg viewBox="0 0 100 100" preserveAspectRatio="none" className="line-chart">
          {points && (
            <polyline
              fill="none"
              points={points}
              stroke={color}
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth="2.6"
            />
          )}
        </svg>
        {chartPoints.map((point) => (
          <span
            className="line-chart-value"
            data-tooltip={`${point.label}: ${formatNumber(point.value)}`}
            key={point.label}
            style={{ borderColor: color, color, left: `${point.x}%`, top: `${Math.max(4, point.y - 9)}%` }}
            title={`${point.label}: ${formatNumber(point.value)}`}
          >
            {formatNumber(point.value)}
          </span>
        ))}
      </div>
      <div className="chart-axis">
        {data.map((item) => <span key={item.label}>{item.label}</span>)}
      </div>
    </div>
  );
}

export default function StatisticsPage() {

  // ComparisonTable component to display year-over-year indicator comparison
  const ComparisonTable = ({ data }) => {
    const refYear  = data[0]?.ref_year  ?? "";
    const prevYear = data[0]?.prev_year ?? "Ano anterior";
    return (
      <div className="chart-card comparison-board-card">
        <div className="section-heading">
          <div>
            <h2>Comparação Ano a Ano</h2>
            <p>Indicadores do ano de referência ({refYear}) versus o ano anterior ({prevYear}) completo.</p>
          </div>
        </div>
        <div className="target-table-wrap">
          <table className="target-table comparison-table">
            <thead>
              <tr>
                <th>Indicador</th>
                <th>{refYear} (acumulado)</th>
                <th>{prevYear} (total)</th>
                <th>Diferença</th>
                <th>Variação %</th>
              </tr>
            </thead>
            <tbody>
              {data.map((row) => {
                const pct = row.percentage;
                const pctLabel = pct > 0 ? `+${pct}%` : `${pct}%`;
                const pctClass = pct > 0 ? "pct-up" : pct < 0 ? "pct-down" : "pct-neutral";
                return (
                  <tr key={row.key}>
                    <td>{row.label}</td>
                    <td>{formatNumber(row.current)}</td>
                    <td>{formatNumber(row.previous)}</td>
                    <td>{formatNumber(row.difference)}</td>
                    <td><span className={`pct-badge ${pctClass}`}>{pctLabel}</span></td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    );
  };

  const [stats, setStats] = useState(null);
  const [goals, setGoals] = useState([]);
  const [filters, setFilters] = useState(getCurrentYearFilters);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    setLoading(true);
    setError("");
    const params = new URLSearchParams(Object.entries(filters).filter(([, value]) => value)).toString();
    api(`/education-reports/statistics/${params ? `?${params}` : ""}`)
      .then(setStats)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [filters]);

  useEffect(() => {
    const referenceYear = getReferenceDate(filters).getFullYear();
    api(`/education-goals/?year=${referenceYear}&page_size=1000`)
      .then((data) => setGoals(data.results || data))
      .catch(() => setGoals([]));
  }, [filters.date_to]);

  const updateFilter = (field, value) => {
    setFilters((current) => ({ ...current, [field]: value }));
  };

  const visibleTotals = useMemo(
    () => (stats?.totals || [])
      .filter((item) => Number(item.value || 0) > 0)
      .sort((a, b) => Number(b.value || 0) - Number(a.value || 0)),
    [stats]
  );
  const referenceDate = getReferenceDate(filters);
  const referenceYear = referenceDate.getFullYear();
  const elapsedMonths = Math.max(referenceDate.getMonth() + 1, 1);
  const totalsByKey = useMemo(
    () => Object.fromEntries((stats?.totals || []).map((item) => [item.key, Number(item.value || 0)])),
    [stats]
  );
  const goalRows = useMemo(
    () => {
      const goalsByKey = Object.fromEntries(goals.map((goal) => [goal.key, goal]));
      return flattenGoalRows(defaultGoalRows).map((row) => {
        const savedGoal = goalsByKey[row.key];
      const accumulated = totalsByKey[row.key] || 0;
      return {
        ...row,
        average: Number(savedGoal?.average ?? row.average),
        target: Number(savedGoal?.target ?? row.target),
        accumulated,
        projection: Math.round((accumulated / elapsedMonths) * 12),
      };
      });
    },
    [goals, totalsByKey, elapsedMonths]
  );
  const lectureEvolution = useMemo(
    () => buildAnnualSeries(stats?.by_month_year || [], "approached_lectures"),
    [stats]
  );
  const actionEvolution = useMemo(
    () => buildAnnualSeries(stats?.by_month_year || [], "approached_actions"),
    [stats]
  );
  const exportReport = async () => {
    const params = new URLSearchParams(Object.entries(filters).filter(([, value]) => value)).toString();
    const blob = await api(`/education-reports/export-statistics/${params ? `?${params}` : ""}`);
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `relatorio-estatisticas-${referenceYear}.pdf`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  };

  return (
    <section className="page dashboard-page">
      <div className="dashboard-hero">
        <div>
          <span>Relatórios dos chefes</span>
          <h1>Estatísticas</h1>
          <p>Indicadores consolidados a partir dos relatórios técnicos enviados pelos chefes.</p>
        </div>
        <button type="button" onClick={exportReport}>
          <Download size={18} /> Exportar relatório
        </button>
      </div>

      <div className="global-filters">
        <label className="filter-field">
          <span>Data inicial</span>
          <input type="date" value={filters.date_from} onChange={(event) => updateFilter("date_from", event.target.value)} />
        </label>
        <label className="filter-field">
          <span>Data final</span>
          <input type="date" value={filters.date_to} onChange={(event) => updateFilter("date_to", event.target.value)} />
        </label>
        <label className="filter-field">
          <span>Status do relatório</span>
          <select value={filters.status} onChange={(event) => updateFilter("status", event.target.value)}>
            {statusOptions.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
          </select>
        </label>
        <button className="secondary" type="button" onClick={() => setFilters(getCurrentYearFilters())}>Limpar</button>
      </div>

      {loading ? (
        <div className="dashboard-skeleton"><span /><span /><span /></div>
      ) : error ? (
        <div className="alert">Não foi possível carregar as estatísticas: {error}</div>
      ) : (
        <>
          {!stats?.reports_count && (
            <div className="alert">Ainda não há relatórios técnicos lançados para gerar estatísticas.</div>
          )}

          <div className="chart-card">
            <div className="section-heading">
              <div>
                <h2>Materiais e resultados registrados</h2>
                <p>Soma de todos os indicadores preenchidos nas ações dos relatórios.</p>
              </div>
            </div>
            <div className="metric-grid">
              {visibleTotals.map((item) => (
                <div className="metric-card" key={item.key}>
                  <span>{item.label}</span>
                  <strong>{formatNumber(item.value)}</strong>
                </div>
              ))}
            </div>
          </div>

          {/* Comparação Ano a Ano — logo abaixo dos cards */}
          {stats?.comparison && stats.comparison.length > 0 && (
            <ComparisonTable data={stats.comparison} />
          )}

          <div className="analytics-grid">
            <AnnualLineChart
              title="Evolução de abordados em palestras"
              subtitle="Comparativo anual com os anos anteriores."
              data={lectureEvolution}
              color="#0048d7"
            />
            <AnnualLineChart
              title="Evolução de abordados em ações"
              subtitle="Comparativo anual com os anos anteriores."
              data={actionEvolution}
              color="#047857"
            />
          </div>

          {/* Quadro de Metas */}
          <div className="chart-card target-board-card">
            <div className="section-heading">
              <div>
                <h2>Quadro de metas {referenceYear}</h2>
                <p>Comparativo do acumulado com projeção anual, média histórica e meta definida.</p>
              </div>
            </div>
            <div className="target-table-wrap">
              <table className="target-table">
                <thead>
                  <tr>
                    <th>Indicador</th>
                    <th>{referenceYear} até {referenceDate.toLocaleDateString("pt-BR", { month: "long" })}</th>
                    <th>Projeção {referenceYear}</th>
                    <th>Média*</th>
                    <th>Meta {referenceYear}</th>
                  </tr>
                </thead>
                <tbody>
                  {goalRows.map((row) => (
                    <tr className={row.section ? "section-row" : ""} key={row.key}>
                      <td>{row.label}</td>
                      <td>{formatNumber(row.accumulated)}</td>
                      <td>{formatNumber(row.projection)}</td>
                      <td>{formatNumber(row.average)}</td>
                      <td>{formatNumber(row.target)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>


        </>
      )}
    </section>
  );
}
