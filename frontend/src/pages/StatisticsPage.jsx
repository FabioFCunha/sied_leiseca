import { TrendingUp, TrendingDown, Minus, BarChart3, CalendarDays, Activity, Filter, PieChart } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { api } from "../api/client.js";
import { DonutChart, HorizontalBarChart } from "../components/Charts.jsx";

function formatNumber(value) {
  return Number(value || 0).toLocaleString("pt-BR");
}

function VariationBadge({ value }) {
  const pct = Number(value || 0);
  const isUp = pct > 0;
  const isDown = pct < 0;
  const Icon = isUp ? TrendingUp : isDown ? TrendingDown : Minus;
  const label = isUp ? `+${pct.toFixed(1)}%` : `${pct.toFixed(1)}%`;
  const bg = isUp ? "rgba(4, 120, 87, 0.1)" : isDown ? "rgba(220, 38, 38, 0.1)" : "rgba(82, 96, 109, 0.1)";
  const color = isUp ? "#047857" : isDown ? "#dc2626" : "#52606d";

  return (
    <span style={{
      display: "inline-flex", alignItems: "center", gap: 4,
      padding: "4px 10px", borderRadius: 20, fontSize: 12, fontWeight: 700,
      background: bg, color
    }}>
      <Icon size={14} />
      {label}
    </span>
  );
}

function KpiCard({ icon: Icon, label, value, subtitle, color = "var(--primary)" }) {
  return (
    <div style={{
      background: "var(--surface)", borderRadius: 16, padding: "24px 28px",
      border: "1px solid var(--line)",
      boxShadow: "0 4px 24px rgba(0,0,0,0.04)",
      display: "flex", flexDirection: "column", gap: 6, position: "relative",
      overflow: "hidden", transition: "transform 0.2s, box-shadow 0.2s",
      flex: 1, minWidth: 200
    }}
    onMouseEnter={e => { e.currentTarget.style.transform = "translateY(-2px)"; e.currentTarget.style.boxShadow = "0 8px 32px rgba(0,72,215,0.12)"; }}
    onMouseLeave={e => { e.currentTarget.style.transform = ""; e.currentTarget.style.boxShadow = "0 4px 24px rgba(0,0,0,0.04)"; }}
    >
      <div style={{
        position: "absolute", top: -20, right: -20, width: 80, height: 80,
        borderRadius: "50%", background: color, opacity: 0.06
      }} />
      <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 4 }}>
        <div style={{
          width: 36, height: 36, borderRadius: 10, display: "flex",
          alignItems: "center", justifyContent: "center",
          background: `linear-gradient(135deg, ${color}, ${color}dd)`, color: "#fff"
        }}>
          <Icon size={18} />
        </div>
        <span style={{ fontSize: 12, fontWeight: 600, color: "var(--text-soft)", textTransform: "uppercase", letterSpacing: 0.5 }}>{label}</span>
      </div>
      <strong style={{ fontSize: 32, fontWeight: 800, color: "var(--text)", lineHeight: 1.1 }}>{value}</strong>
      {subtitle && <span style={{ fontSize: 12, color: "var(--text-soft)" }}>{subtitle}</span>}
    </div>
  );
}

/* Section wrapper for charts */
function ChartSection({ icon: Icon, title, subtitle, gradient = "linear-gradient(135deg, #0048d7, #003299)", children }) {
  return (
    <div style={{
      background: "var(--surface)", borderRadius: 16,
      border: "1px solid var(--line)",
      boxShadow: "0 4px 24px rgba(0,0,0,0.04)",
      overflow: "hidden", marginBottom: 32
    }}>
      <div style={{ padding: "24px 28px 16px", borderBottom: "1px solid var(--line)" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 6 }}>
          <div style={{
            width: 32, height: 32, borderRadius: 8, display: "flex",
            alignItems: "center", justifyContent: "center",
            background: gradient, color: "#fff"
          }}>
            <Icon size={16} />
          </div>
          <h2 style={{ margin: 0, fontSize: 18, fontWeight: 800, color: "var(--text)" }}>{title}</h2>
        </div>
        {subtitle && <p style={{ margin: 0, fontSize: 13, color: "var(--text-soft)" }}>{subtitle}</p>}
      </div>
      <div style={{ padding: "28px" }}>
        {children}
      </div>
    </div>
  );
}

function getDefaultFilters() {
  const today = new Date();
  const year = today.getFullYear();
  return {
    date_from: `${year}-01-01`,
    date_to: today.toISOString().slice(0, 10),
  };
}

function getMonthRange(dateStr) {
  const d = new Date(dateStr + "T00:00:00");
  const y = d.getFullYear();
  const m = d.getMonth();
  const first = new Date(y, m, 1);
  const last = new Date(y, m + 1, 0);
  return {
    from: first.toISOString().slice(0, 10),
    to: last.toISOString().slice(0, 10),
  };
}

function shiftYear(dateStr, delta) {
  const d = new Date(dateStr + "T00:00:00");
  d.setFullYear(d.getFullYear() + delta);
  return d.toISOString().slice(0, 10);
}

export default function StatisticsPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [annualData, setAnnualData] = useState(null);
  const [monthlyData, setMonthlyData] = useState(null);
  const [monthlyPrevData, setMonthlyPrevData] = useState(null);
  const [filters, setFilters] = useState(getDefaultFilters);
  const [pendingFilters, setPendingFilters] = useState(getDefaultFilters);

  const refDateTo = new Date(filters.date_to + "T00:00:00");
  const currentYear = refDateTo.getFullYear();
  const prevYear = currentYear - 1;

  const prevDateFrom = shiftYear(filters.date_from, -1);
  const prevDateTo = shiftYear(filters.date_to, -1);

  const monthRange = getMonthRange(filters.date_to);
  const prevMonthRange = {
    from: shiftYear(monthRange.from, -1),
    to: shiftYear(monthRange.to, -1),
  };

  const elapsedMonths = useMemo(() => {
    const from = new Date(filters.date_from + "T00:00:00");
    const to = new Date(filters.date_to + "T00:00:00");
    return Math.max(Math.round((to - from) / (1000 * 60 * 60 * 24 * 30.44)), 1);
  }, [filters]);

  useEffect(() => {
    setLoading(true);
    setError("");

    const curFilter = `date_from=${filters.date_from}&date_to=${filters.date_to}`;
    const prevFilter = `date_from=${prevDateFrom}&date_to=${prevDateTo}`;
    const mtdCurFilter = `date_from=${monthRange.from}&date_to=${monthRange.to}`;
    const mtdPrevFilter = `date_from=${prevMonthRange.from}&date_to=${prevMonthRange.to}`;

    Promise.all([
      api(`/education-reports/statistics/?${curFilter}`),
      api(`/education-reports/statistics/?${prevFilter}`),
      api(`/education-reports/statistics/?${mtdCurFilter}`),
      api(`/education-reports/statistics/?${mtdPrevFilter}`),
    ])
      .then(([curStats, prevStats, mtdCur, mtdPrev]) => {
        setAnnualData({ current: curStats, previous: prevStats });
        setMonthlyData(mtdCur);
        setMonthlyPrevData(mtdPrev);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [filters]);

  const comparisonFields = [
    { key: "approach", label: "Total de abordagens", icon: Activity, color: "#0048d7" },
    { key: "approached_lectures", label: "Abordados em palestras", icon: BarChart3, color: "#7c3aed" },
    { key: "approached_actions", label: "Abordados em ações", icon: TrendingUp, color: "#047857" },
  ];

  function extractTotals(stats) {
    if (!stats?.totals) return {};
    return Object.fromEntries(stats.totals.map(item => [item.key, Number(item.value || 0)]));
  }

  const table1Data = useMemo(() => {
    const curTotals = extractTotals(annualData?.current);
    const prevTotals = extractTotals(annualData?.previous);

    return comparisonFields.map(field => {
      const current = curTotals[field.key] || 0;
      const previous = prevTotals[field.key] || 0;
      const difference = current - previous;
      const pct = previous > 0 ? (difference / previous) * 100 : (current > 0 ? 100 : 0);
      const projection = Math.round((current / elapsedMonths) * 12);
      return { ...field, current, previous, difference, percentage: pct, projection };
    });
  }, [annualData, elapsedMonths]);

  const table2Data = useMemo(() => {
    const curTotals = extractTotals(monthlyData);
    const prevTotals = extractTotals(monthlyPrevData);

    return comparisonFields.map(field => {
      const current = curTotals[field.key] || 0;
      const previous = prevTotals[field.key] || 0;
      const difference = current - previous;
      const pct = previous > 0 ? (difference / previous) * 100 : (current > 0 ? 100 : 0);
      return { ...field, current, previous, difference, percentage: pct };
    });
  }, [monthlyData, monthlyPrevData]);

  const monthlyTotals = extractTotals(monthlyData);

  /* Chart data from API breakdown fields */
  const entityTypeData = annualData?.current?.by_entity_type || [];
  const modalityData = annualData?.current?.by_modality || [];
  const ageRangeData = annualData?.current?.by_age_range || [];

  const currentMonthName = refDateTo.toLocaleDateString("pt-BR", { month: "long", year: "numeric" });
  const prevMonthName = new Date(prevMonthRange.from + "T00:00:00").toLocaleDateString("pt-BR", { month: "long", year: "numeric" });

  const applyFilters = () => setFilters({ ...pendingFilters });
  const clearFilters = () => {
    const defaults = getDefaultFilters();
    setPendingFilters(defaults);
    setFilters(defaults);
  };

  const tableHeaderStyle = {
    padding: "14px 18px", fontWeight: 700, fontSize: 12, textTransform: "uppercase",
    letterSpacing: 0.5, color: "#fff", background: "linear-gradient(135deg, #001338 0%, #0048d7 100%)",
    borderBottom: "2px solid rgba(255,255,255,0.1)", whiteSpace: "nowrap", textAlign: "left"
  };

  const cellStyle = {
    padding: "14px 18px", fontSize: 14, fontWeight: 500, color: "var(--text)",
    borderBottom: "1px solid var(--line)", textAlign: "left"
  };

  const cellNumStyle = {
    ...cellStyle, fontWeight: 700, fontFamily: "Inter, monospace", textAlign: "right"
  };

  const formatPeriod = (from, to) => {
    const f = new Date(from + "T00:00:00");
    const t = new Date(to + "T00:00:00");
    return `${f.toLocaleDateString("pt-BR")} a ${t.toLocaleDateString("pt-BR")}`;
  };

  return (
    <section className="page" style={{ maxWidth: 1100, margin: "0 auto", padding: "0 24px 48px" }}>
      {/* Hero */}
      <div style={{
        background: "linear-gradient(135deg, #001338 0%, #003299 50%, #0048d7 100%)",
        borderRadius: 20, padding: "36px 40px", marginBottom: 32, position: "relative",
        overflow: "hidden", boxShadow: "0 12px 40px rgba(0, 72, 215, 0.2)"
      }}>
        <div style={{
          position: "absolute", top: -60, right: -60, width: 200, height: 200,
          borderRadius: "50%", background: "rgba(255,255,255,0.04)"
        }} />
        <div style={{
          position: "absolute", bottom: -40, right: 80, width: 120, height: 120,
          borderRadius: "50%", background: "rgba(255,255,255,0.03)"
        }} />
        <span style={{ fontSize: 11, fontWeight: 700, letterSpacing: 1.5, color: "rgba(255,255,255,0.5)", textTransform: "uppercase" }}>
          Painel de Gestão
        </span>
        <h1 style={{ margin: "8px 0 6px", fontSize: 28, fontWeight: 800, color: "#fff" }}>Estatísticas</h1>
        <p style={{ margin: 0, fontSize: 14, color: "rgba(255,255,255,0.65)", maxWidth: 500 }}>
          Indicadores consolidados de abordagens a partir dos relatórios técnicos.
        </p>
      </div>

      {/* Filtros */}
      <div style={{
        background: "var(--surface)", borderRadius: 16, padding: "20px 28px",
        border: "1px solid var(--line)", boxShadow: "0 4px 24px rgba(0,0,0,0.04)",
        marginBottom: 28, display: "flex", gap: 16, alignItems: "flex-end", flexWrap: "wrap"
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginRight: 8 }}>
          <Filter size={16} style={{ color: "var(--primary)" }} />
          <span style={{ fontSize: 13, fontWeight: 700, color: "var(--text)" }}>Período</span>
        </div>
        <label style={{ display: "flex", flexDirection: "column", gap: 4, fontSize: 12, fontWeight: 600, color: "var(--text-soft)" }}>
          Data inicial
          <input type="date" value={pendingFilters.date_from} onChange={e => setPendingFilters(f => ({ ...f, date_from: e.target.value }))}
            style={{ padding: "8px 12px", borderRadius: 8, border: "1px solid var(--line)", fontSize: 13 }} />
        </label>
        <label style={{ display: "flex", flexDirection: "column", gap: 4, fontSize: 12, fontWeight: 600, color: "var(--text-soft)" }}>
          Data final
          <input type="date" value={pendingFilters.date_to} onChange={e => setPendingFilters(f => ({ ...f, date_to: e.target.value }))}
            style={{ padding: "8px 12px", borderRadius: 8, border: "1px solid var(--line)", fontSize: 13 }} />
        </label>
        <button onClick={applyFilters} style={{ height: 38, padding: "0 20px", fontSize: 13, fontWeight: 700, borderRadius: 8 }}>
          Aplicar
        </button>
        <button onClick={clearFilters} className="secondary" style={{ height: 38, padding: "0 16px", fontSize: 13 }}>
          Limpar
        </button>
      </div>

      {loading ? (
        <div style={{ display: "flex", gap: 16 }}>
          {[1, 2, 3].map(i => (
            <div key={i} style={{ flex: 1, height: 120, borderRadius: 16, background: "var(--surface-2)", animation: "pulse 1.5s infinite" }} />
          ))}
        </div>
      ) : error ? (
        <div className="alert">Não foi possível carregar as estatísticas: {error}</div>
      ) : (
        <>
          {/* KPI Cards */}
          <div style={{ display: "flex", gap: 16, marginBottom: 32, flexWrap: "wrap" }}>
            {comparisonFields.map(field => (
              <KpiCard
                key={field.key}
                icon={field.icon}
                label={field.label}
                value={formatNumber(monthlyTotals[field.key] || 0)}
                subtitle={currentMonthName}
                color={field.color}
              />
            ))}
          </div>

          {/* ═══════════ TABLES SECTION (no topo) ═══════════ */}

          {/* Tabela 1: Comparativo Anual */}
          <div style={{
            background: "var(--surface)", borderRadius: 16,
            border: "1px solid var(--line)",
            boxShadow: "0 4px 24px rgba(0,0,0,0.04)",
            overflow: "hidden", marginBottom: 32
          }}>
            <div style={{ padding: "24px 28px 16px", borderBottom: "1px solid var(--line)" }}>
              <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 6 }}>
                <div style={{
                  width: 32, height: 32, borderRadius: 8, display: "flex",
                  alignItems: "center", justifyContent: "center",
                  background: "linear-gradient(135deg, #0048d7, #003299)", color: "#fff"
                }}>
                  <BarChart3 size={16} />
                </div>
                <h2 style={{ margin: 0, fontSize: 18, fontWeight: 800, color: "var(--text)" }}>
                  Comparativo Anual — {currentYear} vs {prevYear}
                </h2>
              </div>
              <p style={{ margin: 0, fontSize: 13, color: "var(--text-soft)" }}>
                Período: <strong>{formatPeriod(filters.date_from, filters.date_to)}</strong> comparado com <strong>{formatPeriod(prevDateFrom, prevDateTo)}</strong>
              </p>
            </div>
            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse" }}>
                <thead>
                  <tr>
                    <th style={tableHeaderStyle}>Indicador</th>
                    <th style={{ ...tableHeaderStyle, textAlign: "right" }}>{prevYear} (Período)</th>
                    <th style={{ ...tableHeaderStyle, textAlign: "right" }}>{currentYear} (Período)</th>
                    <th style={{ ...tableHeaderStyle, textAlign: "right" }}>Diferença</th>
                    <th style={{ ...tableHeaderStyle, textAlign: "center" }}>Variação</th>
                    <th style={{ ...tableHeaderStyle, textAlign: "right" }}>Projeção {currentYear}</th>
                  </tr>
                </thead>
                <tbody>
                  {table1Data.map((row, i) => (
                    <tr key={row.key} style={{ background: i % 2 === 0 ? "var(--surface)" : "var(--surface-2)", transition: "background 0.15s" }}
                      onMouseEnter={e => e.currentTarget.style.background = "rgba(0, 72, 215, 0.04)"}
                      onMouseLeave={e => e.currentTarget.style.background = i % 2 === 0 ? "var(--surface)" : "var(--surface-2)"}
                    >
                      <td style={{ ...cellStyle, fontWeight: 700 }}>
                        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                          <span style={{ width: 4, height: 24, borderRadius: 2, background: row.color, flexShrink: 0 }} />
                          {row.label}
                        </div>
                      </td>
                      <td style={cellNumStyle}>{formatNumber(row.previous)}</td>
                      <td style={{ ...cellNumStyle, color: "var(--primary)" }}>{formatNumber(row.current)}</td>
                      <td style={{ ...cellNumStyle, color: row.difference >= 0 ? "#047857" : "#dc2626" }}>
                        {row.difference >= 0 ? "+" : ""}{formatNumber(row.difference)}
                      </td>
                      <td style={{ ...cellStyle, textAlign: "center" }}>
                        <VariationBadge value={row.percentage} />
                      </td>
                      <td style={{ ...cellNumStyle, fontSize: 15 }}>
                        <span style={{
                          background: "rgba(0, 72, 215, 0.08)", padding: "4px 12px",
                          borderRadius: 8, color: "var(--primary)"
                        }}>
                          {formatNumber(row.projection)}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Tabela 2: Comparativo Mensal */}
          <div style={{
            background: "var(--surface)", borderRadius: 16,
            border: "1px solid var(--line)",
            boxShadow: "0 4px 24px rgba(0,0,0,0.04)",
            overflow: "hidden", marginBottom: 32
          }}>
            <div style={{ padding: "24px 28px 16px", borderBottom: "1px solid var(--line)" }}>
              <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 6 }}>
                <div style={{
                  width: 32, height: 32, borderRadius: 8, display: "flex",
                  alignItems: "center", justifyContent: "center",
                  background: "linear-gradient(135deg, #047857, #059669)", color: "#fff"
                }}>
                  <CalendarDays size={16} />
                </div>
                <h2 style={{ margin: 0, fontSize: 18, fontWeight: 800, color: "var(--text)", textTransform: "capitalize" }}>
                  Comparativo Mensal — {currentMonthName} vs {prevMonthName}
                </h2>
              </div>
              <p style={{ margin: 0, fontSize: 13, color: "var(--text-soft)" }}>
                Mês vigente comparado com o mesmo mês do ano anterior.
              </p>
            </div>
            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse" }}>
                <thead>
                  <tr>
                    <th style={{ ...tableHeaderStyle, background: "linear-gradient(135deg, #022c22 0%, #047857 100%)" }}>Indicador</th>
                    <th style={{ ...tableHeaderStyle, textAlign: "right", background: "linear-gradient(135deg, #022c22 0%, #047857 100%)" }}>{prevMonthName}</th>
                    <th style={{ ...tableHeaderStyle, textAlign: "right", background: "linear-gradient(135deg, #022c22 0%, #047857 100%)" }}>{currentMonthName}</th>
                    <th style={{ ...tableHeaderStyle, textAlign: "right", background: "linear-gradient(135deg, #022c22 0%, #047857 100%)" }}>Diferença</th>
                    <th style={{ ...tableHeaderStyle, textAlign: "center", background: "linear-gradient(135deg, #022c22 0%, #047857 100%)" }}>Variação</th>
                  </tr>
                </thead>
                <tbody>
                  {table2Data.map((row, i) => (
                    <tr key={row.key} style={{ background: i % 2 === 0 ? "var(--surface)" : "var(--surface-2)", transition: "background 0.15s" }}
                      onMouseEnter={e => e.currentTarget.style.background = "rgba(4, 120, 87, 0.04)"}
                      onMouseLeave={e => e.currentTarget.style.background = i % 2 === 0 ? "var(--surface)" : "var(--surface-2)"}
                    >
                      <td style={{ ...cellStyle, fontWeight: 700 }}>
                        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                          <span style={{ width: 4, height: 24, borderRadius: 2, background: row.color, flexShrink: 0 }} />
                          {row.label}
                        </div>
                      </td>
                      <td style={cellNumStyle}>{formatNumber(row.previous)}</td>
                      <td style={{ ...cellNumStyle, color: "#047857" }}>{formatNumber(row.current)}</td>
                      <td style={{ ...cellNumStyle, color: row.difference >= 0 ? "#047857" : "#dc2626" }}>
                        {row.difference >= 0 ? "+" : ""}{formatNumber(row.difference)}
                      </td>
                      <td style={{ ...cellStyle, textAlign: "center" }}>
                        <VariationBadge value={row.percentage} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* ═══════════ CHARTS SECTION ═══════════ */}

          {/* Row 1: Empresa/Órgão vs Escola (Donut) + Público vs Privado (Donut) */}
          <div className="stats-charts-grid" style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24, marginBottom: 32 }}>
            <ChartSection
              icon={PieChart}
              title="Empresa/Órgão ou Escola"
              subtitle="Distribuição dos relatórios por tipo de entidade solicitante"
              gradient="linear-gradient(135deg, #0048d7, #003299)"
            >
              <DonutChart
                data={entityTypeData.map(d => {
                  const labelStr = d.label || "";
                  const isEscola = labelStr.toLowerCase().includes("escola");
                  const isEmpresa = labelStr.toLowerCase().includes("empresa") || labelStr.toLowerCase().includes("órgão");
                  return {
                    label: isEscola ? "Escola" : isEmpresa ? "Empresa/Órgão" : (d.label || "Sem informação"),
                    value: d.value,
                    color: isEscola ? "#7c3aed" : isEmpresa ? "#0048d7" : "#64748b",
                  };
                })}
                size={200}
                thickness={26}
              />
            </ChartSection>

            <ChartSection
              icon={PieChart}
              title="Público ou Privado"
              subtitle="Distribuição dos relatórios por natureza da entidade"
              gradient="linear-gradient(135deg, #047857, #059669)"
            >
              <DonutChart
                data={entityTypeData.map(d => {
                  const labelStr = d.label || "";
                  const isPublico = labelStr.toLowerCase().includes("público");
                  const isPrivado = labelStr.toLowerCase().includes("privado");
                  return {
                    label: d.label || "Sem informação",
                    value: d.value,
                    color: isPublico ? "#047857" : isPrivado ? "#dc6b16" : "#64748b",
                  };
                })}
                size={200}
                thickness={26}
              />
            </ChartSection>
          </div>

          {/* Row 2: Modalidade Pretendida (Horizontal Bars) + Faixa Etária (Horizontal Bars) */}
          <div className="stats-charts-grid" style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24, marginBottom: 32 }}>
            <ChartSection
              icon={BarChart3}
              title="Modalidade Pretendida"
              subtitle="Quantidade de relatórios por modalidade de ação"
              gradient="linear-gradient(135deg, #7c3aed, #5b21b6)"
            >
              <HorizontalBarChart
                data={modalityData.map((d, i) => {
                  const colors = ["#0048d7", "#7c3aed", "#047857", "#dc6b16", "#0891b2"];
                  return { label: d.label, value: d.value, color: colors[i % colors.length] };
                })}
                height={32}
              />
            </ChartSection>

            <ChartSection
              icon={Activity}
              title="Faixa Etária do Público"
              subtitle="Distribuição dos relatórios por faixa etária atendida"
              gradient="linear-gradient(135deg, #dc6b16, #ea580c)"
            >
              <HorizontalBarChart
                data={ageRangeData.map((d, i) => {
                  const colors = ["#0891b2", "#0048d7", "#7c3aed", "#047857", "#dc6b16"];
                  return { label: d.label, value: d.value, color: colors[i % colors.length] };
                })}
                height={32}
              />
            </ChartSection>
          </div>

          {/* Row 3: Modalidade (Donut) + Faixa Etária (Donut) */}
          <div className="stats-charts-grid" style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24, marginBottom: 32 }}>
            <ChartSection
              icon={PieChart}
              title="Composição por Modalidade"
              subtitle="Proporção percentual de cada modalidade pretendida"
              gradient="linear-gradient(135deg, #0891b2, #0e7490)"
            >
              <DonutChart
                data={modalityData.map((d, i) => {
                  const colors = ["#0048d7", "#7c3aed", "#047857", "#dc6b16", "#0891b2"];
                  return { label: d.label, value: d.value, color: colors[i % colors.length] };
                })}
                size={200}
                thickness={26}
              />
            </ChartSection>

            <ChartSection
              icon={PieChart}
              title="Composição por Faixa Etária"
              subtitle="Proporção percentual de cada faixa etária atendida"
              gradient="linear-gradient(135deg, #6366f1, #4f46e5)"
            >
              <DonutChart
                data={ageRangeData.map((d, i) => {
                  const colors = ["#0891b2", "#0048d7", "#7c3aed", "#047857", "#dc6b16"];
                  return { label: d.label, value: d.value, color: colors[i % colors.length] };
                })}
                size={200}
                thickness={26}
              />
            </ChartSection>
          </div>
        </>
      )}
    </section>
  );
}
