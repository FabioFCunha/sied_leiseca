import { TrendingUp, TrendingDown, Minus, BarChart3, CalendarDays, Activity, Filter, PieChart } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { api } from "../api/client.js";
import { DonutChart, HorizontalBarChart } from "../components/Charts.jsx";
import { formatLocalISODate } from "../utils/date.js";

function formatNumber(value) {
  return Number(value || 0).toLocaleString("pt-BR");
}

function VariationBadge({ value, status }) {
  if (status === "NEW_DATA") {
    return (
      <span style={{
        display: "inline-flex", alignItems: "center", gap: 4,
        padding: "4px 10px", borderRadius: 20, fontSize: 12, fontWeight: 700,
        background: "rgba(4, 120, 87, 0.1)", color: "#047857"
      }}>
        Novo
      </span>
    );
  }
  
  if (status === "NO_CHANGE" || value === null) {
    return (
      <span style={{
        display: "inline-flex", alignItems: "center", gap: 4,
        padding: "4px 10px", borderRadius: 20, fontSize: 12, fontWeight: 700,
        background: "rgba(82, 96, 109, 0.1)", color: "#52606d"
      }}>
        <Minus size={14} /> 0.0%
      </span>
    );
  }

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
    date_to: formatLocalISODate(today),
  };
}

export default function StatisticsPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [comparisonData, setComparisonData] = useState(null);
  const [historicalData, setHistoricalData] = useState([]);

  const [filters, setFilters] = useState(getDefaultFilters);
  const [pendingFilters, setPendingFilters] = useState(getDefaultFilters);

  const refDateTo = new Date(filters.date_to + "T00:00:00");
  const currentYear = refDateTo.getFullYear();
  const prevYear = currentYear - 1;

  const prevDateFrom = `${prevYear}-01-01`;
  const prevDateTo = `${prevYear}-12-31`;

  const elapsedMonths = useMemo(() => {
    const from = new Date(filters.date_from + "T00:00:00");
    const to = new Date(filters.date_to + "T00:00:00");
    return Math.max(Math.round((to - from) / (1000 * 60 * 60 * 24 * 30.44)), 1);
  }, [filters]);

  useEffect(() => {
    setLoading(true);
    setError("");

    const params = `date_from=${filters.date_from}&date_to=${filters.date_to}&prev_date_from=${prevDateFrom}&prev_date_to=${prevDateTo}`;
    
    Promise.all([
      api(`/statistics/comparison/?${params}`),
      api(`/statistics/historical-series/`),
    ])
      .then(([comp, hist]) => {
        setComparisonData(comp);
        setHistoricalData(hist);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [filters]);

  // Map Backend Category Keys to Frontend Labels
  const comparisonFields = [
    { key: "AUDIENCE - Geral", label: "Total de abordagens", icon: Activity, color: "#0048d7" },
    { key: "AUDIENCE - PALESTRAS", label: "1.1 - Abordados em palestras", icon: BarChart3, color: "#7c3aed" },
    { key: "AUDIENCE - ACOES", label: "1.2 - Abordados em ações", icon: TrendingUp, color: "#047857" },
    { key: "ACTION - Geral", label: "2 - Ações Educativas (Total Geral)", icon: CalendarDays, color: "#0ea5e9" },
    { key: "ACTION - Escola", label: "2.1 - Escolas", icon: Activity, color: "#f59e0b" },
    { key: "ACTION - Universidade", label: "2.2 - Universidades", icon: BarChart3, color: "#ec4899" },
    { key: "ACTION - Empresa", label: "2.3 - Empresas", icon: TrendingUp, color: "#8b5cf6" },
    { key: "MATERIAL - Certificados", label: "2.4 - Certificados entregues", icon: CalendarDays, color: "#14b8a6" },
    { key: "ACTION - Bares", label: "3.1 - Bares", icon: BarChart3, color: "#eab308" },
    { key: "ACTION - Pedágio", label: "3.2 - Pedágio", icon: TrendingUp, color: "#a855f7" },
    { key: "ACTION - Praças Esportivas", label: "3.3 - Esportes", icon: CalendarDays, color: "#3b82f6" },
    { key: "ACTION - Praia", label: "3.4 - Praia", icon: Activity, color: "#22c55e" },
    { key: "ACTION - Eventos", label: "3.5 - Eventos", icon: BarChart3, color: "#ec4899" },
    { key: "ACTION - Shopping", label: "3.6 - Shopping/Centro Comercial", icon: TrendingUp, color: "#f97316" },
    { key: "ACTION - Ação Social", label: "3.7 - Ação Social", icon: CalendarDays, color: "#6366f1" },
    { key: "ACTION - Outros", label: "3.8 - Outros", icon: Activity, color: "#64748b" },
    { key: "MATERIAL - Soprinho", label: "Revistinha Soprinho", icon: BarChart3, color: "#10b981" },
    { key: "MATERIAL - Geral", label: "4 - Materiais de Divulgação", icon: TrendingUp, color: "#8b5cf6" },
  ];

  const table1Data = useMemo(() => {
    if (!comparisonData) return [];
    
    return comparisonFields.map(field => {
      const current = comparisonData.current_period[field.key] || 0;
      const previous = comparisonData.previous_period[field.key] || 0;
      const diffData = comparisonData.variations[field.key] || { variation: 0, status: "NO_CHANGE" };
      const difference = current - previous;
      const projection = Math.round((current / elapsedMonths) * 12);
      
      return { 
        ...field, 
        current, 
        previous, 
        difference, 
        percentage: diffData.variation,
        status: diffData.status,
        projection 
      };
    });
  }, [comparisonData, elapsedMonths]);

  const historicalFields = [
    { key: "AUDIENCE - Geral", label: "1 - Público total" },
    { key: "AUDIENCE - PALESTRAS", label: "1.1 - Público em palestras" },
    { key: "AUDIENCE - ACOES", label: "1.2 - Público em ações" },
    { key: "LECTURES - Geral", label: "2 - Palestras realizadas" },
    { key: "ACTION - Escola", label: "2.1 - Escolas" },
    { key: "ACTION - Universidade", label: "2.2 - Universidades" },
    { key: "ACTION - Empresa", label: "2.3 - Empresas" },
    { key: "MATERIAL - Certificados", label: "2.4 - Certificados entregues" },
    { key: "STREET_ACTIONS - Geral", label: "3 - Ações" },
    { key: "ACTION - Bares", label: "3.1 - Bares" },
    { key: "ACTION - Pedágio", label: "3.2 - Pedágio" },
    { key: "ACTION - Praças Esportivas", label: "3.3 - Esportes" },
    { key: "ACTION - Praia", label: "3.4 - Praia" },
    { key: "ACTION - Eventos", label: "3.5 - Eventos" },
    { key: "ACTION - Shopping", label: "3.6 - Shopping/Centro Comercial" },
    { key: "ACTION - Ação Social", label: "3.7 - Ação Social" },
    { key: "ACTION - Outros", label: "3.8 - Outros" },
    { key: "ACTION - Praças/Parques Públicos", label: "3.9 - Praças/Parques Públicos" },
    { key: "ACTION - Pontos turísticos", label: "3.10 - Pontos turísticos" },
    { key: "ACTION - Fiscalização", label: "3.11 - Fiscalização" },
    { key: "MATERIAL - Geral", label: "4 - Materiais de divulgação" },
    { key: "MATERIAL - Soprinho", label: "Revistinha Soprinho" },
  ];

  const lectureCategoryKeys = [
    "ACTION - Escola", "ACTION - Universidade", "ACTION - Empresa",
  ];

  const streetActionCategoryKeys = [
    "ACTION - Bares", "ACTION - Pedágio", "ACTION - Praças Esportivas",
    "ACTION - Praia", "ACTION - Eventos", "ACTION - Shopping",
    "ACTION - Ação Social", "ACTION - Outros",
    "ACTION - Praças/Parques Públicos", "ACTION - Pontos turísticos",
    "ACTION - Fiscalização",
  ];

  // Aggregate the official historical series by year without percentage comparison.
  const table3Data = useMemo(() => {
    if (!historicalData) return [];

    const years = [...new Set(historicalData.map(d => d.year))].sort((a, b) => a - b);

    return years.map(year => {
      const yearData = historicalData.filter(item => item.year === year);
      const getValue = category => yearData
        .filter(item => item.category === category)
        .reduce((sum, item) => sum + Number(item.value || 0), 0);
      const values = Object.fromEntries(
        historicalFields.map(field => [field.key, getValue(field.key)])
      );
      values["LECTURES - Geral"] = lectureCategoryKeys.reduce(
        (sum, key) => sum + getValue(key), 0
      );
      const categorizedStreetActions = streetActionCategoryKeys.reduce(
        (sum, key) => sum + getValue(key), 0
      );
      values["STREET_ACTIONS - Geral"] = Math.max(
        getValue("ACTION - Geral") - values["LECTURES - Geral"],
        categorizedStreetActions,
        0
      );
      return { year, values };
    });
  }, [historicalData]);
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
          Painel de Gestão (Nova API)
        </span>
        <h1 style={{ margin: "8px 0 6px", fontSize: 28, fontWeight: 800, color: "#fff" }}>Estatísticas Oficiais SIED</h1>
        <p style={{ margin: 0, fontSize: 14, color: "rgba(255,255,255,0.65)", maxWidth: 500 }}>
          Indicadores consolidados (Histórico + Relatórios Operacionais).
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
          {/* KPI Cards (Macro Indicators) */}
          <div style={{ display: "flex", gap: 16, marginBottom: 32, flexWrap: "wrap" }}>
              <KpiCard
                icon={Activity}
                label="Público Alcançado"
                value={formatNumber(comparisonData?.macro_current?.AUDIENCE)}
                subtitle={formatPeriod(filters.date_from, filters.date_to)}
                color="#0048d7"
              />
              <KpiCard
                icon={CalendarDays}
                label="Ações Educativas"
                value={formatNumber(comparisonData?.macro_current?.ACTION)}
                subtitle={formatPeriod(filters.date_from, filters.date_to)}
                color="#047857"
              />
              <KpiCard
                icon={BarChart3}
                label="Materiais de Divulgação"
                value={formatNumber(comparisonData?.macro_current?.MATERIAL)}
                subtitle={formatPeriod(filters.date_from, filters.date_to)}
                color="#7c3aed"
              />
          </div>

          {/* Tabela 1: Comparativo Anual Detalhado */}
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
                  Comparativo Detalhado — {currentYear} vs {prevYear}
                </h2>
              </div>
              <p style={{ margin: 0, fontSize: 13, color: "var(--text-soft)" }}>
                Período: <strong>{refDateTo.toLocaleDateString("pt-BR")}</strong> comparado com o ano todo de <strong>{prevYear}</strong>
              </p>
            </div>
            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse" }}>
                <thead>
                  <tr>
                    <th style={tableHeaderStyle}>Indicador / Categoria</th>
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
                        <VariationBadge value={row.percentage} status={row.status} />
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



          {/* Tabela 3: Histórico Anual */}
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
                  background: "linear-gradient(135deg, #7c3aed, #5b21b6)", color: "#fff"
                }}>
                  <BarChart3 size={16} />
                </div>
                <h2 style={{ margin: 0, fontSize: 18, fontWeight: 800, color: "var(--text)" }}>
                  Série Histórica
                </h2>
              </div>
              <p style={{ margin: 0, fontSize: 13, color: "var(--text-soft)" }}>
                Série histórica com totais anuais agregados (Banco de Dados Otimizado).
              </p>
            </div>
            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse" }}>
                <thead>
                  <tr>
                    <th style={{ ...tableHeaderStyle, background: "linear-gradient(135deg, #3b0764 0%, #7c3aed 100%)" }}>Ano</th>
                    {historicalFields.map(field => (
                      <th
                        key={field.key}
                        style={{ ...tableHeaderStyle, textAlign: "right", background: "linear-gradient(135deg, #3b0764 0%, #7c3aed 100%)" }}
                      >
                        {field.label}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {table3Data.map((row, i) => (
                    <tr key={row.year} style={{ background: i % 2 === 0 ? "var(--surface)" : "var(--surface-2)", transition: "background 0.15s" }}
                      onMouseEnter={e => e.currentTarget.style.background = "rgba(124, 58, 237, 0.04)"}
                      onMouseLeave={e => e.currentTarget.style.background = i % 2 === 0 ? "var(--surface)" : "var(--surface-2)"}
                    >
                      <td style={{ ...cellStyle, fontWeight: 800, color: "var(--primary)" }}>{row.year}</td>
                      {historicalFields.map(field => (
                        <td key={field.key} style={cellNumStyle}>
                          {formatNumber(row.values[field.key])}
                        </td>
                      ))}
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
