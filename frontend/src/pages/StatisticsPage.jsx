import { TrendingUp, TrendingDown, Minus, BarChart3, CalendarDays, Activity } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { api } from "../api/client.js";

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

export default function StatisticsPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [annualData, setAnnualData] = useState(null);
  const [monthlyData, setMonthlyData] = useState(null);

  const today = new Date();
  const currentYear = today.getFullYear();
  const prevYear = currentYear - 1;
  const elapsedMonths = Math.max(today.getMonth() + 1, 1);

  useEffect(() => {
    setLoading(true);
    setError("");

    const ytdFilter = `date_from=${currentYear}-01-01&date_to=${today.toISOString().slice(0, 10)}`;
    const firstDayOfMonth = new Date(today.getFullYear(), today.getMonth(), 1).toISOString().slice(0, 10);
    const mtdFilter = `date_from=${firstDayOfMonth}&date_to=${today.toISOString().slice(0, 10)}`;

    Promise.all([
      api(`/education-reports/statistics/?${ytdFilter}`),
      api(`/education-reports/statistics/?${mtdFilter}`)
    ])
      .then(([ytdStats, mtdStats]) => {
        setAnnualData(ytdStats);
        setMonthlyData(mtdStats);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [currentYear]);

  const comparisonFields = [
    { key: "approach", label: "Total de abordagens", icon: Activity, color: "#0048d7" },
    { key: "approached_lectures", label: "Abordados em palestras", icon: BarChart3, color: "#7c3aed" },
    { key: "approached_actions", label: "Abordados em ações", icon: TrendingUp, color: "#047857" },
  ];

  const table1Data = useMemo(() => {
    if (!annualData?.comparison) return [];
    const comparisonMap = Object.fromEntries(annualData.comparison.map(item => [item.key, item]));

    return comparisonFields.map(field => {
      const cmp = comparisonMap[field.key] || { current: 0, previous: 0 };
      const current = cmp.current;
      const previous = cmp.previous;
      const difference = current - previous;
      const pct = previous > 0 ? (difference / previous) * 100 : (current > 0 ? 100 : 0);
      const projection = Math.round((current / elapsedMonths) * 12);
      return { ...field, current, previous, difference, percentage: pct, projection };
    });
  }, [annualData, elapsedMonths]);

  const table2Data = useMemo(() => {
    if (!monthlyData?.totals) return [];
    const totalsMap = Object.fromEntries(monthlyData.totals.map(item => [item.key, Number(item.value || 0)]));
    return comparisonFields.map(field => ({ ...field, total: totalsMap[field.key] || 0 }));
  }, [monthlyData]);

  const monthlyTotals = useMemo(() => {
    if (!monthlyData?.totals) return {};
    return Object.fromEntries(monthlyData.totals.map(item => [item.key, Number(item.value || 0)]));
  }, [monthlyData]);

  const currentMonthName = today.toLocaleDateString("pt-BR", { month: "long" });

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
          {/* KPI Cards - Mês Vigente */}
          <div style={{ display: "flex", gap: 16, marginBottom: 32, flexWrap: "wrap" }}>
            {comparisonFields.map(field => (
              <KpiCard
                key={field.key}
                icon={field.icon}
                label={field.label}
                value={formatNumber(monthlyTotals[field.key] || 0)}
                subtitle={`Mês de ${currentMonthName}`}
                color={field.color}
              />
            ))}
          </div>

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
                Análise de abordagens no período com projeção para o encerramento de {currentYear}.
              </p>
            </div>
            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse" }}>
                <thead>
                  <tr>
                    <th style={{ ...tableHeaderStyle, borderRadius: "0" }}>Indicador</th>
                    <th style={{ ...tableHeaderStyle, textAlign: "right" }}>{prevYear} (Total)</th>
                    <th style={{ ...tableHeaderStyle, textAlign: "right" }}>{currentYear} (Acumulado)</th>
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

          {/* Tabela 2: Resultados do Mês */}
          <div style={{
            background: "var(--surface)", borderRadius: 16,
            border: "1px solid var(--line)",
            boxShadow: "0 4px 24px rgba(0,0,0,0.04)",
            overflow: "hidden"
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
                  Resultados de {currentMonthName}
                </h2>
              </div>
              <p style={{ margin: 0, fontSize: 13, color: "var(--text-soft)" }}>
                Indicadores registrados exclusivamente no mês vigente.
              </p>
            </div>
            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse" }}>
                <thead>
                  <tr>
                    <th style={{ ...tableHeaderStyle, background: "linear-gradient(135deg, #022c22 0%, #047857 100%)" }}>Indicador</th>
                    <th style={{ ...tableHeaderStyle, textAlign: "right", background: "linear-gradient(135deg, #022c22 0%, #047857 100%)" }}>Total no Mês</th>
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
                      <td style={{ ...cellNumStyle, fontSize: 18, color: "#047857" }}>
                        {formatNumber(row.total)}
                      </td>
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
