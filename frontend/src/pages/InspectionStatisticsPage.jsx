import {
  AlertCircle,
  CarFront,
  ClipboardCheck,
  CloudRain,
  Filter,
  Gauge,
  HelpCircle,
  MapPinned,
  ShieldAlert,
  TestTube2,
  Users,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  LabelList,
  Legend,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { getInspectionStatisticsDashboard } from "../api/inspectionStatistics.js";
import {
  TAXONOMY_STATUS,
  buildInspectionExecutiveCards,
  buildInspectionStatisticsTaxonomy,
} from "../utils/inspectionStatisticsTaxonomy.js";
import "./StatisticsPage.css";

const executiveCardMeta = {
  operations: { icon: ShieldAlert, color: "#0f766e" },
  approach: { icon: Users, color: "#1d4ed8" },
  refusal: { icon: TestTube2, color: "#b45309" },
  fined: { icon: CarFront, color: "#7c3aed" },
  cnh_collected: { icon: ClipboardCheck, color: "#0048d7" },
  alcohol_cases: { icon: TestTube2, color: "#c2410c" },
};

const categoryIconMap = {
  vehicles: CarFront,
  driver: Gauge,
  breathalyzer_results: TestTube2,
  taxi: MapPinned,
  events: AlertCircle,
};

function toIsoDate(value) {
  return value.toISOString().slice(0, 10);
}

function buildDefaultFilters() {
  const today = new Date();
  const historicalStart = new Date(2009, 0, 1);

  return {
    date_from: toIsoDate(historicalStart),
    date_to: toIsoDate(today),
    team: "",
  };
}

function integer(value) {
  return new Intl.NumberFormat("pt-BR", {
    maximumFractionDigits: 0,
  }).format(Number(value || 0));
}

function displayMetric(value) {
  return value === null || value === undefined
    ? "Não informado"
    : integer(value);
}

function statusClassName(status) {
  switch (status) {
    case TAXONOMY_STATUS.MAPPED:
      return "is-mapped";

    case TAXONOMY_STATUS.PARTIAL:
      return "is-partial";

    case TAXONOMY_STATUS.UNMAPPED:
      return "is-unmapped";

    default:
      return "is-needs-definition";
  }
}

function Section({ title, subtitle, children }) {
  return (
    <section className="stats-panel">
      <div className="stats-panel-header">
        <div className="stats-panel-title">
          <div>
            <h2>{title}</h2>
            <p>{subtitle}</p>
          </div>
        </div>
      </div>

      <div className="stats-panel-body">{children}</div>
    </section>
  );
}

function TaxonomyGrid({ category }) {
  const Icon = categoryIconMap[category.key] || HelpCircle;

  return (
    <section className="inspection-taxonomy">
      <div className="inspection-taxonomy-header">
        <div className="inspection-taxonomy-title">
          <span className="inspection-taxonomy-icon">
            <Icon size={18} />
          </span>

          <div>
            <h2>{category.title}</h2>
            <p>{category.subtitle}</p>
          </div>
        </div>
      </div>

      <div className="inspection-taxonomy-grid">
        {category.items.map((item) => (
          <article
            key={item.key}
            className="inspection-taxonomy-item"
          >
            <div className="inspection-taxonomy-item-top">
              <strong>{item.label}</strong>

              <span
                className={`inspection-taxonomy-badge ${statusClassName(
                  item.status
                )}`}
              >
                {item.status}
              </span>
            </div>

            <div className="inspection-taxonomy-value">
              {item.status === TAXONOMY_STATUS.UNMAPPED ||
              item.status === TAXONOMY_STATUS.NEEDS_DEFINITION
                ? item.status
                : displayMetric(item.value)}
            </div>

            {item.field && item.showField && (
              <div className="inspection-taxonomy-meta">
                <code>{item.field}</code>
              </div>
            )}

            {item.note && item.showNote && <p>{item.note}</p>}
          </article>
        ))}
      </div>
    </section>
  );
}

const historicalTableIndicators = [
  {
    key: "approached",
    label: "Abordados",
  },
  {
    key: "fined",
    label: "Multados",
  },
  {
    key: "towed",
    label: "Rebocados",
  },
  {
    key: "cnh_collected",
    label: "CNH Recolhidas",
  },
  {
    key: "refusal",
    label: "Recusas",
  },
  {
    key: "administrative_art_165",
    label: "Administrativo Art. 165 CTB",
  },
  {
    key: "criminal_art_306",
    label: "Criminal Art. 306 CTB",
  },
  {
    key: "criminal_art_306_other_evidence",
    label: "Por outros meios Art. 306 CTB",
  },
  {
    key: "alcohol_cases",
    label: "Casos de Alcoolemia",
  },
  {
    key: "alcohol_percentage",
    label: "Percentual de Alcoolemia",
    percentage: true,
  },
  {
    key: "art307",
    label: "Art. 307",
  },
];

function displayHistoricalValue(value, percentage = false) {
  if (value === null || value === undefined) {
    return "-";
  }

  if (percentage) {
    return `${Number(value).toLocaleString("pt-BR", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    })}%`;
  }

  return integer(value);
}

function ApproachedLineLabel({
  x,
  y,
  value,
}) {
  if (value === null || value === undefined) {
    return null;
  }

  const label = integer(value);
  const boxWidth = Math.max(48, String(label).length * 7 + 12);
  const boxHeight = 20;

  const labelY = Math.max(4, y - 30);

  return (
    <g>
      <rect
        x={x - boxWidth / 2}
        y={labelY}
        width={boxWidth}
        height={boxHeight}
        rx={4}
        fill="#1d4ed8"
      />

      <text
        x={x}
        y={labelY + boxHeight / 2}
        fill="#ffffff"
        textAnchor="middle"
        dominantBaseline="central"
        fontSize={11}
        fontWeight={700}
      >
        {label}
      </text>
    </g>
  );
}

function AlcoholBarLabel({
  x,
  y,
  width,
  height,
  value,
}) {
  if (value === null || value === undefined) {
    return null;
  }

  const label = integer(value);
  const boxWidth = Math.max(42, String(label).length * 7 + 12);
  const boxHeight = 20;

  const centerX = x + width / 2;
  const centerY = y + height / 2;

  return (
    <g>
      <rect
        x={centerX - boxWidth / 2}
        y={centerY - boxHeight / 2}
        width={boxWidth}
        height={boxHeight}
        rx={4}
        fill="#b45309"
      />

      <text
        x={centerX}
        y={centerY}
        fill="#ffffff"
        textAnchor="middle"
        dominantBaseline="central"
        fontSize={11}
        fontWeight={700}
      >
        {label}
      </text>
    </g>
  );
}

export default function InspectionStatisticsPage() {
  const [filters, setFilters] = useState(buildDefaultFilters);
  const [draftFilters, setDraftFilters] =
    useState(buildDefaultFilters);

  const [dashboard, setDashboard] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const loadDashboard = async (params = filters) => {
    setLoading(true);
    setError("");

    try {
      const response =
        await getInspectionStatisticsDashboard(params);

      setDashboard(response);
    } catch (err) {
      setError(err.message);
      setDashboard(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDashboard(filters);
  }, []);

  const cards = useMemo(() => {
    const summary = dashboard?.summary || {};

    const operations = Number(summary.operations || 0);

    const approached = Number(
      summary.approach_plus_reconductor ??
      summary.approach ??
      0
    );

    const refusal = Number(summary.refusal || 0);
    const fined = Number(summary.fined || 0);
    const cnhCollected = Number(summary.cnh_collected || 0);

    const alcoholCases = Number(
      dashboard?.alcohol_results?.alcohol_cases ??
      0
    );

    const percentage = (value, base) =>
      base > 0 ? (value / base) * 100 : 0;

    const baseCards =
      buildInspectionExecutiveCards(summary);

    return [
      ...baseCards.map((card) => {
        if (card.key === "approach") {
          return {
            ...card,
            secondary:
              operations > 0
                ? `Média de ${(approached / operations).toLocaleString("pt-BR", {
                    minimumFractionDigits: 1,
                    maximumFractionDigits: 1,
                  })} abordados por fiscalização em média`
                : null,
          };
        }

        if (card.key === "refusal") {
          return {
            ...card,
            secondary:
              `${percentage(refusal, approached).toLocaleString("pt-BR", {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2,
              })}% dos abordados recusaram o teste do etil?metro`,
          };
        }

        if (card.key === "fined") {
          return {
            ...card,
            secondary:
              `Média de ${(fined / Math.max(operations, 1)).toLocaleString("pt-BR", {
                minimumFractionDigits: 1,
                maximumFractionDigits: 1,
              })} multas aplicadas por fiscalização em média`,
          };
        }

        if (card.key === "cnh_collected") {
          return {
            ...card,
            secondary:
              `${percentage(
                cnhCollected,
                approached
              ).toLocaleString("pt-BR", {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2,
              })}% dos abordados tiveram a CNH recolhida`,
          };
        }

        return card;
      }),

      {
        key: "alcohol_cases",
        label: "Casos de alcoolemia",
        value: alcoholCases,
        secondary:
          `${percentage(
            alcoholCases,
            approached
          ).toLocaleString("pt-BR", {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
          })}% dos abordados foram classificados como casos de alcoolemia`,
      },
    ];
  }, [dashboard]);

  const taxonomy = useMemo(
    () => buildInspectionStatisticsTaxonomy(dashboard || {}),
    [dashboard]
  );

  const historicalYearlyTable =
    dashboard?.historical_yearly_table || null;
  const hasData = Boolean(dashboard?.meta?.has_data);

  const rainTotal =
    dashboard?.horus_cards?.rain?.value ??
    dashboard?.occurrences?.rain ??
    0;

  const inspectionsTotal =
    dashboard?.summary?.operations ??
    0;

  const rainPercentage =
    inspectionsTotal > 0
      ? (rainTotal / inspectionsTotal) * 100
      : 0;

  const handleApplyFilters = () => {
    setFilters(draftFilters);
    loadDashboard(draftFilters);
  };

  const handleClearFilters = () => {
    const next = buildDefaultFilters();

    setDraftFilters(next);
    setFilters(next);
    loadDashboard(next);
  };

  return (
    <section className="stats-dashboard">
      <div className="stats-hero">
        <div>
          <span>Fiscalização</span>

          <h1>Estatística Fiscalização</h1>

          <p>
            Indicadores oficiais consolidados da Fiscalização da
            Operação Lei Seca.
          </p>
        </div>

        <div
          style={{
            textAlign: "right",
            color: "#ffffff",
          }}
        >
          <div
            style={{
              fontSize: "12px",
              opacity: 0.85,
              marginBottom: "4px",
            }}
          >
            Operações interrompidas por chuva
          </div>

          <div
            style={{
              display: "flex",
              justifyContent: "flex-end",
              alignItems: "baseline",
              gap: "8px",
            }}
          >
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "6px",
              }}
            >
              <CloudRain size={22} strokeWidth={2.2} />

              <strong
                style={{
                  fontSize: "24px",
                  lineHeight: 1,
                }}
              >
                {integer(rainTotal)}
              </strong>
            </div>

            <span
              style={{
                fontSize: "14px",
                fontWeight: 700,
              }}
            >
              {rainPercentage.toLocaleString("pt-BR", {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2,
              })}%
            </span>
          </div>

          <div
            style={{
              fontSize: "11px",
              opacity: 0.82,
              marginTop: "4px",
            }}
          >
            do total de fiscalizações
          </div>
        </div>
      </div>

      <div className="stats-filters">
        <div className="stats-filter-title">
          <Filter size={16} />
          Filtros
        </div>

        <label>
          De

          <input
            type="date"
            value={draftFilters.date_from}
            onChange={(event) =>
              setDraftFilters((current) => ({
                ...current,
                date_from: event.target.value,
              }))
            }
          />
        </label>

        <label>
          Até

          <input
            type="date"
            value={draftFilters.date_to}
            onChange={(event) =>
              setDraftFilters((current) => ({
                ...current,
                date_to: event.target.value,
              }))
            }
          />
        </label>

        <label>
          Equipe

          <input
            placeholder="Ex.: A3"
            value={draftFilters.team}
            onChange={(event) =>
              setDraftFilters((current) => ({
                ...current,
                team: event.target.value,
              }))
            }
          />
        </label>

        <div className="stats-filter-actions">
          <button
            className="primary"
            onClick={handleApplyFilters}
          >
            Aplicar
          </button>

          <button
            type="button"
            onClick={handleClearFilters}
          >
            Limpar
          </button>
        </div>
      </div>

      {loading ? (
        <div className="stats-panel">
          <div className="stats-loading">
            Carregando estatísticas de Fiscalização...
          </div>
        </div>
      ) : error ? (
        <div className="stats-panel">
          <div
            className="stats-loading"
            style={{ color: "var(--danger)" }}
          >
            {error}
          </div>
        </div>
      ) : !hasData ? (
        <div className="stats-panel">
          <div
            className="stats-empty"
            style={{
              gap: "8px",
              padding: "28px",
            }}
          >
            <strong>
              Nenhum dado estatístico de Fiscalização para o
              período selecionado.
            </strong>

            <span>
              Verifique o período informado ou os filtros
              aplicados.
            </span>
          </div>
        </div>
      ) : (
        <>
          <div className="stats-kpi-grid inspection-kpi-grid">
            {cards.map((card) => {
              const meta =
                executiveCardMeta[card.key] ||
                executiveCardMeta.operations;

              const Icon = meta.icon;

              return (
                <div
                  key={card.key}
                  className="stats-kpi"
                  style={{
                    "--kpi": meta.color,
                  }}
                >
                  <div className="stats-kpi-top">
                    <span className="stats-kpi-icon">
                      <Icon size={18} />
                    </span>

                    {card.label}
                  </div>

                  <div className="stats-kpi-value">
                    {displayMetric(card.value)}
                  </div>

                  {card.secondary ? (
                    <div
                      style={{
                        marginTop: "6px",
                        fontSize: "10.5px",
                        lineHeight: 1.25,
                        fontWeight: 600,
                        color: "var(--muted)",
                      }}
                    >
                      {card.secondary}
                    </div>
                  ) : null}
                </div>
              );
            })}
          </div>

          <div className="inspection-taxonomy-stack">
            {taxonomy.map((category) => (
              <TaxonomyGrid
                key={category.key}
                category={category}
              />
            ))}
          </div>

          {historicalYearlyTable?.rows?.length ? (
            <Section
              title="Evolução da Fiscalização"
              subtitle="Comparativo anual entre fiscalizações, abordados e casos de alcoolemia."
            >
              <div
                className="stats-chart"
                style={{ height: "420px" }}
              >
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    data={historicalYearlyTable.rows}
                    margin={{
                      top: 34,
                      right: 8,
                      left: 8,
                      bottom: 0,
                    }}
                  >
                    <CartesianGrid strokeDasharray="3 3" />

                    <XAxis dataKey="year" />

                    <YAxis
                      yAxisId="approached"
                      tickFormatter={(value) => integer(value)}
                    />

                    <YAxis
                      yAxisId="other"
                      orientation="right"
                      tickFormatter={(value) => integer(value)}
                    />

                    <Tooltip
                      formatter={(value, name) => [
                        integer(value),
                        name,
                      ]}
                    />

                    <Legend />

                    <Bar
                      yAxisId="other"
                      dataKey="operations"
                      name="Fiscalizações"
                      fill="#0f766e"
                      radius={[5, 5, 0, 0]}
                    >
                      <LabelList
                        dataKey="operations"
                        position="top"
                        formatter={(value) => integer(value)}
                      />
                    </Bar>

                    <Bar
                      yAxisId="other"
                      dataKey="alcohol_cases"
                      name="Casos de alcoolemia"
                      fill="#b45309"
                      radius={[5, 5, 0, 0]}
                    >
                      <LabelList
                        dataKey="alcohol_cases"
                        content={<AlcoholBarLabel />}
                      />
                    </Bar>

                    <Line
                      yAxisId="approached"
                      type="monotone"
                      dataKey="approached"
                      name="Abordados"
                      stroke="#1d4ed8"
                      strokeWidth={3}
                      dot={{ r: 4 }}
                      activeDot={{ r: 6 }}
                    >
                      <LabelList
                        dataKey="approached"
                        content={<ApproachedLineLabel />}
                      />
                    </Line>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </Section>
          ) : null}

          {historicalYearlyTable?.rows?.length ? (
            <Section
              title="Série Histórica da Fiscalização"
              subtitle="Consolidado institucional anual. Em 2026, o histórico até 09/08 é continuado pela produção homologada a partir de 10/08."
            >
              <div
                className="stats-table-wrap"
                style={{ overflowX: "auto" }}
              >
                <table
                  className="stats-table"
                  style={{
                    minWidth: "2100px",
                    whiteSpace: "nowrap",
                  }}
                >
                  <thead>
                    <tr>
                      <th
                        style={{
                          position: "sticky",
                          left: 0,
                          zIndex: 2,
                          background: "var(--surface, #fff)",
                          minWidth: "245px",
                        }}
                      >
                        Indicador
                      </th>

                      {historicalYearlyTable.years.map((year) => (
                        <th key={year}>{year}</th>
                      ))}

                      <th>Total</th>
                    </tr>
                  </thead>

                  <tbody>
                    {historicalTableIndicators.map((indicator) => (
                      <tr key={indicator.key}>
                        <td
                          style={{
                            position: "sticky",
                            left: 0,
                            zIndex: 1,
                            background: "var(--surface, #fff)",
                            fontWeight: 600,
                          }}
                        >
                          {indicator.label}
                        </td>

                        {historicalYearlyTable.rows.map((row) => (
                          <td key={`${indicator.key}-${row.year}`}>
                            {displayHistoricalValue(
                              row[indicator.key],
                              indicator.percentage
                            )}
                          </td>
                        ))}

                        <td style={{ fontWeight: 700 }}>
                          {displayHistoricalValue(
                            historicalYearlyTable.total?.[
                              indicator.key
                            ],
                            indicator.percentage
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <div
                style={{
                  marginTop: "12px",
                  fontSize: "12px",
                  color: "var(--muted)",
                }}
              >
                Histórico consolidado até 09/08/2026. A coluna de 2026
                continua sendo atualizada com a produção estatística
                homologada a partir de 10/08/2026.
              </div>
            </Section>
          ) : null}
        </>
      )}
    </section>
  );
}
