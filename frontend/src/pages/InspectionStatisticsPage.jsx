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

import { getInspectionTerritorialStatistics } from "../api/inspection.js";
import { getInspectionStatisticsDashboard } from "../api/inspectionStatistics.js";
import {
  TAXONOMY_STATUS,
  buildInspectionExecutiveCards,
  buildInspectionStatisticsTaxonomy,
} from "../utils/inspectionStatisticsTaxonomy.js";
import "./StatisticsPage.css";


const executiveCardMeta = {
  operations: {
    icon: ShieldAlert,
    color: "#0f766e",
  },
  approach: {
    icon: Users,
    color: "#1d4ed8",
  },
  refusal: {
    icon: TestTube2,
    color: "#b45309",
  },
  fined: {
    icon: CarFront,
    color: "#7c3aed",
  },
  cnh_collected: {
    icon: ClipboardCheck,
    color: "#0048d7",
  },
  alcohol_cases: {
    icon: TestTube2,
    color: "#c2410c",
  },
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


function percentage(value) {
  if (value === null || value === undefined) {
    return "-";
  }

  return `${Number(value).toLocaleString("pt-BR", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}%`;
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


function Section({
  title,
  subtitle,
  children,
}) {
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

      <div className="stats-panel-body">
        {children}
      </div>
    </section>
  );
}


function TaxonomyGrid({ category }) {
  const Icon =
    categoryIconMap[category.key] ||
    HelpCircle;

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
            {category.sourceNote && (
              <p
                style={{
                  fontSize: "12px",
                  color: "var(--t-gray-5)",
                  marginTop: "4px",
                }}
              >
                {category.sourceNote}
              </p>
            )}
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
              <strong>
                {item.label}
              </strong>

              <span
                className={`inspection-taxonomy-badge ${statusClassName(
                  item.status
                )}`}
              >
                {item.status}
              </span>
            </div>

            <div className="inspection-taxonomy-value">
              {item.status ===
                TAXONOMY_STATUS.UNMAPPED ||
              item.status ===
                TAXONOMY_STATUS.NEEDS_DEFINITION
                ? item.status
                : displayMetric(item.value)}
            </div>
            {item.percentage !== undefined && item.percentage !== null && (
              <div
                style={{
                  fontSize: "12px",
                  color: "var(--t-gray-5)",
                  marginTop: "2px",
                  fontWeight: 500,
                }}
              >
                {percentage(item.percentage)}
              </div>
            )}

            {item.field &&
            item.showField ? (
              <div className="inspection-taxonomy-meta">
                <code>
                  {item.field}
                </code>
              </div>
            ) : null}

            {item.note &&
            item.showNote ? (
              <p>{item.note}</p>
            ) : null}
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


function displayHistoricalValue(
  value,
  isPercentage = false
) {
  if (
    value === null ||
    value === undefined
  ) {
    return "-";
  }

  if (isPercentage) {
    return percentage(value);
  }

  return integer(value);
}


function ApproachedLineLabel({
  x,
  y,
  value,
}) {
  if (
    value === null ||
    value === undefined
  ) {
    return null;
  }

  const label = integer(value);

  const boxWidth = Math.max(
    48,
    String(label).length * 7 + 12
  );

  const boxHeight = 20;
  const labelY = Math.max(
    4,
    y - 30
  );

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
        y={
          labelY +
          boxHeight / 2
        }
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
  if (
    value === null ||
    value === undefined
  ) {
    return null;
  }

  const label = integer(value);

  const boxWidth = Math.max(
    42,
    String(label).length * 7 + 12
  );

  const boxHeight = 20;

  const centerX =
    x + width / 2;

  const centerY =
    y + height / 2;

  return (
    <g>
      <rect
        x={
          centerX -
          boxWidth / 2
        }
        y={
          centerY -
          boxHeight / 2
        }
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


function TerritorialSummaryCard({
  label,
  value,
  percentageValue = false,
}) {
  return (
    <div className="stats-kpi">
      <div className="stats-kpi-top">
        {label}
      </div>

      <div className="stats-kpi-value">
        {percentageValue
          ? percentage(value)
          : integer(value)}
      </div>
    </div>
  );
}


function TerritorialMunicipalityTable({
  municipalities,
}) {
  if (
    !municipalities ||
    municipalities.length === 0
  ) {
    return (
      <div
        className="stats-empty"
        style={{
          padding: "24px",
        }}
      >
        Nenhuma fiscalização classificada
        nesta região para o período
        selecionado.
      </div>
    );
  }

  return (
    <div
      className="stats-table-wrap"
      style={{
        overflowX: "auto",
      }}
    >
      <table className="stats-table">
        <thead>
          <tr>
            <th>Município</th>
            <th>Fiscalizações</th>
            <th>Abordados</th>
            <th>Multados</th>
            <th>Rebocados</th>
            <th>Alcoolemia</th>
            <th>% Alcoolemia</th>
          </tr>
        </thead>

        <tbody>
          {municipalities.map(
            (item) => {
              const highAlcohol =
                Number(
                  item.metrics
                    ?.alcohol_percentage ??
                    0
                ) >= 25;

              return (
                <tr
                  key={
                    item.municipality_id
                  }
                  style={
                    highAlcohol
                      ? {
                          background:
                            "#fff1f2",
                        }
                      : undefined
                  }
                >
                  <td
                    style={{
                      fontWeight: 700,
                    }}
                  >
                    {item.municipality}

                    {highAlcohol ? (
                      <span
                        style={{
                          display:
                            "inline-block",
                          marginLeft:
                            "8px",
                          padding:
                            "2px 7px",
                          borderRadius:
                            "999px",
                          background:
                            "#fee2e2",
                          color:
                            "#b91c1c",
                          fontSize:
                            "10px",
                          fontWeight:
                            800,
                        }}
                      >
                        ≥ 25%
                      </span>
                    ) : null}
                  </td>

                  <td>
                    {integer(
                      item.metrics
                        ?.operations
                    )}
                  </td>

                  <td>
                    {integer(
                      item.metrics
                        ?.approach
                    )}
                  </td>

                  <td>
                    {integer(
                      item.metrics
                        ?.fined
                    )}
                  </td>

                  <td>
                    {integer(
                      item.metrics
                        ?.towed
                    )}
                  </td>

                  <td>
                    {integer(
                      item.metrics
                        ?.alcohol_cases
                    )}
                  </td>

                  <td
                    style={
                      highAlcohol
                        ? {
                            color:
                              "#b91c1c",
                            fontWeight:
                              800,
                          }
                        : undefined
                    }
                  >
                    {percentage(
                      item.metrics
                        ?.alcohol_percentage
                    )}
                  </td>
                </tr>
              );
            }
          )}
        </tbody>
      </table>
    </div>
  );
}


function TerritorialRegionSummary({
  metrics,
}) {
  if (!metrics) {
    return null;
  }

  return (
    <div
      style={{
        display: "flex",
        flexWrap: "wrap",
        gap: "14px",
        marginBottom: "16px",
        padding: "12px 14px",
        borderRadius: "10px",
        background: "#f8fafc",
        border: "1px solid #e2e8f0",
        fontSize: "12px",
      }}
    >
      <span>
        <strong>
          Fiscalizações:
        </strong>{" "}
        {integer(metrics.operations)}
      </span>

      <span>
        <strong>
          Abordados:
        </strong>{" "}
        {integer(metrics.approach)}
      </span>

      <span>
        <strong>
          Multados:
        </strong>{" "}
        {integer(metrics.fined)}
      </span>

      <span>
        <strong>
          Alcoolemia:
        </strong>{" "}
        {integer(
          metrics.alcohol_cases
        )}
      </span>

      <span>
        <strong>
          Percentual:
        </strong>{" "}
        {percentage(
          metrics.alcohol_percentage
        )}
      </span>
    </div>
  );
}


function formatDate(isoStr) {
  if (!isoStr) return "-";
  const parts = isoStr.split("-");
  if (parts.length !== 3) return isoStr;
  return `${parts[2]}/${parts[1]}/${parts[0]}`;
}

function formatMunicipalityDates(dates) {
  if (!Array.isArray(dates) || dates.length === 0) {
    return "";
  }

  const sortedDates = [...dates].sort();

  const parts = sortedDates.map((value) => {
    const [year, month, day] = String(value).split("-");

    if (!year || !month || !day) {
      return null;
    }

    return {
      year,
      month,
      day,
      full: `${day}/${month}/${year}`,
    };
  });

  if (parts.some((item) => item === null)) {
    return sortedDates.map(formatDate).join(" · ");
  }

  if (parts.length === 1) {
    return parts[0].full;
  }

  const sameMonth = parts.every(
    (item) => item.month === parts[0].month
  );

  const sameYear = parts.every(
    (item) => item.year === parts[0].year
  );

  if (sameMonth && sameYear) {
    const days = parts.map((item) => item.day);

    if (days.length === 2) {
      return `${days[0]} e ${days[1]}/${parts[0].month}/${parts[0].year}`;
    }

    return `${days.slice(0, -1).join(", ")} e ${days.at(-1)}/${parts[0].month}/${parts[0].year}`;
  }

  return parts.map((item) => item.full).join(" · ");
}

function TerritorialContent({ territorial, loading, error, filters }) {
  if (loading) {
    return <div className="stats-panel"><div className="stats-loading">Carregando análise territorial...</div></div>;
  }
  if (error) {
    return <div className="stats-panel"><div className="stats-loading" style={{ color: "var(--danger)" }}>{error}</div></div>;
  }
  if (!territorial) {
    return <div className="stats-panel"><div className="stats-empty">Nenhum dado territorial carregado.</div></div>;
  }

  const regions = territorial.regions || [];
  const metropolitanRegion = regions.find(r => r.region_code === "METROPOLITANA");
  const interiorRegions = regions.filter(r => r.region_code !== "METROPOLITANA");
  const highlighted = territorial.highlighted_operations || [];
  const unclassified = territorial.unclassified || [];

  const summary = territorial.summary || {};

  return (
    <div className="territorial-report-area">
      <header className="territorial-header">
        <button className="btn-print no-print" onClick={() => window.print()} style={{ position: 'absolute', top: 32, right: 44, background: 'var(--t-gold)', color: 'var(--t-navy)', border: 'none', borderRadius: 6, padding: '7px 18px', fontSize: 11.5, fontWeight: 700, cursor: 'pointer', zIndex: 10 }}>
          Exportar PDF
        </button>
        <div className="territorial-header-top">
          <div className="territorial-logo-circle">OLS</div>
          <div className="territorial-header-text">
            <p className="territorial-header-institution">Governo do Estado do Rio de Janeiro &nbsp;·&nbsp; Operação Lei Seca</p>
            <h1 className="territorial-header-title">Análise Territorial da Fiscalização</h1>
            <p className="territorial-header-sub">Distribuição das ações de fiscalização por região e município</p>
          </div>
        </div>
        <div className="territorial-badges">
          <div className="territorial-badge"><small>Período selecionado</small><strong>{formatDate(filters?.date_from)} a {formatDate(filters?.date_to)}</strong></div>
          <div className="territorial-badge"><small>Emissão</small><strong>{new Date().toLocaleDateString('pt-BR')}</strong></div>
          <div className="territorial-badge"><small>Fonte</small><strong>HORUS / SIED</strong></div>
        </div>
      </header>
      <div className="territorial-stripe"></div>

      <section className="territorial-section">
        <h2 className="territorial-section-title">Acumulados · Período Selecionado</h2>
        <div className="territorial-kpi-grid">
          <div className="territorial-kpi k1">
            <div className="territorial-kpi-ico"><Users size={14} /></div>
            <p className="territorial-kpi-label">Abordados</p>
            <p className="territorial-kpi-val">{integer(summary.approach)}</p>
          </div>
          <div className="territorial-kpi k2">
            <div className="territorial-kpi-ico"><CarFront size={14} /></div>
            <p className="territorial-kpi-label">Multados</p>
            <p className="territorial-kpi-val">{integer(summary.fined)}</p>
          </div>
          <div className="territorial-kpi k3">
            <div className="territorial-kpi-ico"><TestTube2 size={14} /></div>
            <p className="territorial-kpi-label">Alcoolemia</p>
            <p className="territorial-kpi-val">{integer(summary.alcohol_cases)}</p>
          </div>
          <div className="territorial-kpi k4">
            <div className="territorial-kpi-ico"><AlertCircle size={14} /></div>
            <p className="territorial-kpi-label">Percentual</p>
            <p className="territorial-kpi-val">{percentage(summary.alcohol_percentage)}</p>
          </div>
          <div className="territorial-kpi k5">
            <div className="territorial-kpi-ico"><ShieldAlert size={14} /></div>
            <p className="territorial-kpi-label">Fiscalizações</p>
            <p className="territorial-kpi-val">{integer(summary.classified_operations)}</p>
          </div>
          <div className="territorial-kpi k6">
            <div className="territorial-kpi-ico"><TestTube2 size={14} /></div>
            <p className="territorial-kpi-label">Recusas</p>
            <p className="territorial-kpi-val">{integer(summary.refusal)}</p>
          </div>
        </div>

        <div className="territorial-alc-breakdown">
          <div className="territorial-alc-item">
            <div className="alc-num">{integer(summary.refusal)}</div>
            <div className="alc-lbl">Recusas</div>
            <div className="alc-sub">ao etilômetro</div>
          </div>
          <div className="territorial-alc-item">
            <div className="alc-num">{integer(summary.administrative_art_165)}</div>
            <div className="alc-lbl">ADM · Art. 165</div>
            <div className="alc-sub">infração administrativa</div>
          </div>
          <div className="territorial-alc-item">
            <div className="alc-num">{integer(summary.criminal_art_306)}</div>
            <div className="alc-lbl">Criminal · Art. 306</div>
            <div className="alc-sub">crime de trânsito</div>
          </div>
          <div className="territorial-alc-item">
            <div className="alc-num">{integer(summary.criminal_art_306_other_evidence)}</div>
            <div className="alc-lbl">Outros meios</div>
            <div className="alc-sub">sinais notórios / art. 306</div>
          </div>
        </div>
      </section>

      <div className="territorial-divider"></div>

      <section className="territorial-section">
        <h2 className="territorial-section-title">Fiscalização por Território</h2>

        <div className="territorial-tbl-wrap">
          <table>
            <thead>
              <tr>
                <th>Região / Município</th>
                <th>Abordados</th>
                <th>Multados</th>
                <th>Alcoolemia</th>
                <th>% Alc.</th>
                <th>Fiscalizações</th>
              </tr>
            </thead>

            {/* METROPOLITANA */}
            <tbody>
              <tr className="territorial-main-region-title"><td colSpan={6}>Região Metropolitana</td></tr>
              {metropolitanRegion?.municipalities?.map(item => {
                const isHigh = Number(item.metrics?.alcohol_percentage || 0) >= 25;
                return (
                  <tr key={item.municipality_id} className={isHigh ? "territorial-row-highlight" : ""}>
                    <td className="territorial-muni">
                      <strong>{item.municipality} {isHigh && <span className="territorial-badge-highlight">ALCOOLEMIA ≥ 25%</span>}</strong>
                      {formatMunicipalityDates(item.dates) ? (
                        <small>{formatMunicipalityDates(item.dates)}</small>
                      ) : null}
                    </td>
                    <td>{integer(item.metrics?.approach)}</td>
                    <td>{integer(item.metrics?.fined)}</td>
                    <td>{integer(item.metrics?.alcohol_cases)}</td>
                    <td><span className={isHigh ? "territorial-pill high" : "territorial-pill"}>{percentage(item.metrics?.alcohol_percentage)}</span></td>
                    <td>{integer(item.metrics?.operations)}</td>
                  </tr>
                );
              })}
              {metropolitanRegion && (
                <tr className="territorial-region-subtotal">
                  <td>Subtotal Região Metropolitana</td>
                  <td>{integer(metropolitanRegion.metrics?.approach)}</td>
                  <td>{integer(metropolitanRegion.metrics?.fined)}</td>
                  <td>{integer(metropolitanRegion.metrics?.alcohol_cases)}</td>
                  <td><span className="territorial-pill">{percentage(metropolitanRegion.metrics?.alcohol_percentage)}</span></td>
                  <td>{integer(metropolitanRegion.metrics?.operations)}</td>
                </tr>
              )}
            </tbody>

            {/* INTERIOR */}
            {interiorRegions.length > 0 && (
              <tbody>
                <tr className="territorial-main-region-title"><td colSpan={6}>Interior</td></tr>
              </tbody>
            )}
            {interiorRegions.map(region => (
              <tbody key={region.region_code}>
                <tr className="territorial-region-header"><td colSpan={6}>{region.region}</td></tr>
                {region.municipalities?.map(item => {
                  const isHigh = Number(item.metrics?.alcohol_percentage || 0) >= 25;
                  return (
                    <tr key={item.municipality_id} className={isHigh ? "territorial-row-highlight" : ""}>
                      <td className="territorial-muni">
                        <strong>{item.municipality} {isHigh && <span className="territorial-badge-highlight">ALCOOLEMIA ≥ 25%</span>}</strong>
                        {formatMunicipalityDates(item.dates) ? (
                          <small>{formatMunicipalityDates(item.dates)}</small>
                        ) : null}
                      </td>
                      <td>{integer(item.metrics?.approach)}</td>
                      <td>{integer(item.metrics?.fined)}</td>
                      <td>{integer(item.metrics?.alcohol_cases)}</td>
                      <td><span className={isHigh ? "territorial-pill high" : "territorial-pill"}>{percentage(item.metrics?.alcohol_percentage)}</span></td>
                      <td>{integer(item.metrics?.operations)}</td>
                    </tr>
                  );
                })}
                <tr className="territorial-region-subtotal">
                  <td>Subtotal {region.region}</td>
                  <td>{integer(region.metrics?.approach)}</td>
                  <td>{integer(region.metrics?.fined)}</td>
                  <td>{integer(region.metrics?.alcohol_cases)}</td>
                  <td><span className="territorial-pill">{percentage(region.metrics?.alcohol_percentage)}</span></td>
                  <td>{integer(region.metrics?.operations)}</td>
                </tr>
              </tbody>
            ))}

            <tfoot>
              {metropolitanRegion && (
                <tr>
                  <td>Total Região Metropolitana</td>
                  <td>{integer(metropolitanRegion.metrics?.approach)}</td>
                  <td>{integer(metropolitanRegion.metrics?.fined)}</td>
                  <td>{integer(metropolitanRegion.metrics?.alcohol_cases)}</td>
                  <td style={{color: "var(--t-gold)"}}>{percentage(metropolitanRegion.metrics?.alcohol_percentage)}</td>
                  <td>{integer(metropolitanRegion.metrics?.operations)}</td>
                </tr>
              )}
              {territorial.interior && (
                <tr>
                  <td>Total Interior</td>
                  <td>{integer(territorial.interior.approach)}</td>
                  <td>{integer(territorial.interior.fined)}</td>
                  <td>{integer(territorial.interior.alcohol_cases)}</td>
                  <td style={{color: "var(--t-gold)"}}>{percentage(territorial.interior.alcohol_percentage)}</td>
                  <td>{integer(territorial.interior.operations)}</td>
                </tr>
              )}
              <tr>
                <td>Total Geral</td>
                <td>{integer(summary.approach)}</td>
                <td>{integer(summary.fined)}</td>
                <td>{integer(summary.alcohol_cases)}</td>
                <td style={{color: "var(--t-gold)"}}>{percentage(summary.alcohol_percentage)}</td>
                <td>{integer(summary.classified_operations)}</td>
              </tr>
            </tfoot>
          </table>
        </div>

        <h3 style={{fontSize: 12.5, fontWeight: 800, color: "var(--t-navy)", textTransform: "uppercase", marginBottom: 10, borderBottom: "2px solid var(--t-danger)", display: "inline-block", paddingBottom: 4}}>Fiscalizações com índice de alcoolemia ≥ 25%</h3>
        {highlighted.length === 0 ? (
          <div className="territorial-nota" style={{marginBottom: 24}}>
            Não foram registradas fiscalizações com índice de alcoolemia igual ou superior a 25% no período selecionado.
          </div>
        ) : (
          <div className="territorial-tbl-wrap" style={{border: "1px solid var(--t-danger)", boxShadow: "0 2px 8px rgba(192,57,43,.15)"}}>
            <table className="territorial-sub-tbl">
              <thead>
                <tr>
                  <th>Data</th>
                  <th>Equipe</th>
                  <th style={{textAlign: "left"}}>Município</th>
                  <th style={{textAlign: "left"}}>Região</th>
                  <th>Abordados</th>
                  <th>Alcoolemia</th>
                  <th>Percentual</th>
                </tr>
              </thead>
              <tbody>
                {highlighted.map(item => (
                  <tr key={item.operation_id}>
                    <td style={{textAlign: "center"}}>{formatDate(item.date)}</td>
                    <td style={{textAlign: "center", fontWeight: 700}}>{item.team || "-"}</td>
                    <td style={{textAlign: "left"}}><strong>{item.municipality}</strong></td>
                    <td style={{textAlign: "left"}}>{item.region}</td>
                    <td>{integer(item.approach)}</td>
                    <td style={{fontWeight: 700}}>{integer(item.alcohol_cases)}</td>
                    <td><span className="territorial-badge-highlight" style={{fontSize: 11, padding: "3px 8px"}}>{percentage(item.alcohol_percentage)}</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {unclassified.length > 0 && (
        <>
          <div className="territorial-divider"></div>
          <section className="territorial-section">
            <h2 className="territorial-section-title" style={{color: "var(--t-gray-5)"}}>Registros territoriais não classificados</h2>
            <div className="territorial-tbl-wrap" style={{marginBottom: 0}}>
              <table>
                <thead>
                  <tr style={{background: "var(--t-gray-5)"}}>
                    <th>Município recebido</th>
                    <th>Nome normalizado</th>
                    <th>Fiscalizações</th>
                    <th>Abordados</th>
                  </tr>
                </thead>
                <tbody>
                  {unclassified.map((item, idx) => (
                    <tr key={`${item.normalized_city}-${idx}`}>
                      <td style={{textAlign: "left"}}>{item.source_city || "(vazio)"}</td>
                      <td style={{textAlign: "left"}}>{item.normalized_city || "-"}</td>
                      <td>{integer(item.operations)}</td>
                      <td>{integer(item.approach)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        </>
      )}

      <div className="territorial-divider"></div>

      <section className="territorial-section">
        <h2 className="territorial-section-title">Nota Metodológica</h2>
        <div className="territorial-nota">
          <p style={{margin: "0 0 6px 0"}}><strong>Alcoolemia:</strong> soma de recusas + infrações administrativas Art. 165 + crimes Art. 306 + outros meios/sinais notórios.</p>
          <p style={{margin: "0 0 6px 0"}}><strong>Percentual:</strong> total de casos de alcoolemia dividido pelo total de abordados.</p>
          <p style={{margin: "0 0 6px 0"}}><strong>Art. 307:</strong> contabilizado separadamente.</p>
          <p style={{margin: "0 0 6px 0"}}><strong>Fonte territorial:</strong> município registrado na operação e classificado pela tabela oficial InspectionMunicipality → InspectionRegion.</p>
          <p style={{margin: 0}}><strong>Fonte operacional:</strong> HORUS / SIED.</p>
        </div>
      </section>

      <footer className="territorial-footer">
        <p className="territorial-footer-note">
          Documento gerado automaticamente pelo sistema SIED com dados extraídos do banco HORUS.<br/>
          Para dúvidas ou retificações, contate a equipe técnica da Operação Lei Seca.
        </p>
        <div className="territorial-footer-stamp">
          <small>Gerado em</small>
          <strong>{new Date().toLocaleString('pt-BR', { day:'2-digit', month:'2-digit', year:'numeric', hour:'2-digit', minute:'2-digit' })}</strong>
          <small style={{display: 'block', marginTop: 4}}>SIED · DETRAN-RJ · Operação Lei Seca</small>
        </div>
      </footer>
    </div>
  );
}


export default function InspectionStatisticsPage() {
  const [
    filters,
    setFilters,
  ] = useState(
    buildDefaultFilters
  );

  const [
    draftFilters,
    setDraftFilters,
  ] = useState(
    buildDefaultFilters
  );

  const [
    activeTab,
    setActiveTab,
  ] = useState("official");

  const [
    dashboard,
    setDashboard,
  ] = useState(null);

  const [
    loading,
    setLoading,
  ] = useState(true);

  const [
    error,
    setError,
  ] = useState("");

  const [
    territorial,
    setTerritorial,
  ] = useState(null);

  const [
    territorialLoading,
    setTerritorialLoading,
  ] = useState(false);

  const [
    territorialError,
    setTerritorialError,
  ] = useState("");


  const loadDashboard = async (
    params = filters
  ) => {
    setLoading(true);
    setError("");

    try {
      const response =
        await getInspectionStatisticsDashboard(
          params
        );

      setDashboard(response);
    } catch (err) {
      setError(
        err?.message ||
          "Erro ao carregar estatísticas."
      );

      setDashboard(null);
    } finally {
      setLoading(false);
    }
  };


  const loadTerritorial = async (
    params = filters
  ) => {
    setTerritorialLoading(true);
    setTerritorialError("");

    try {
      const response =
        await getInspectionTerritorialStatistics(
          params
        );

      setTerritorial(response);
    } catch (err) {
      setTerritorialError(
        err?.message ||
          "Erro ao carregar análise territorial."
      );

      setTerritorial(null);
    } finally {
      setTerritorialLoading(
        false
      );
    }
  };


  useEffect(() => {
    loadDashboard(filters);
  }, []);


  const cards = useMemo(() => {
    const summary =
      dashboard?.summary || {};

    const operations = Number(
      summary.operations || 0
    );

    const approached = Number(
      summary.approach_plus_reconductor ??
        summary.approach ??
        0
    );

    const refusal = Number(
      summary.refusal || 0
    );

    const fined = Number(
      summary.fined || 0
    );

    const cnhCollected = Number(
      summary.cnh_collected || 0
    );

    const alcoholCases = Number(
      dashboard?.alcohol_results
        ?.alcohol_cases ?? 0
    );

    const calculatePercentage = (
      value,
      base
    ) =>
      base > 0
        ? (value / base) * 100
        : 0;

    const baseCards =
      buildInspectionExecutiveCards(
        summary
      );

    return [
      ...baseCards.map(
        (card) => {
          if (
            card.key ===
            "approach"
          ) {
            return {
              ...card,

              secondary:
                operations > 0
                  ? `Média de ${(
                      approached /
                      operations
                    ).toLocaleString(
                      "pt-BR",
                      {
                        minimumFractionDigits:
                          1,
                        maximumFractionDigits:
                          1,
                      }
                    )} abordados por fiscalização em média`
                  : null,
            };
          }

          if (
            card.key ===
            "refusal"
          ) {
            return {
              ...card,

              secondary: `${calculatePercentage(
                refusal,
                approached
              ).toLocaleString(
                "pt-BR",
                {
                  minimumFractionDigits:
                    2,
                  maximumFractionDigits:
                    2,
                }
              )}% dos abordados recusaram o teste do etilômetro`,
            };
          }

          if (
            card.key ===
            "fined"
          ) {
            return {
              ...card,

              secondary: `Média de ${(
                fined /
                Math.max(
                  operations,
                  1
                )
              ).toLocaleString(
                "pt-BR",
                {
                  minimumFractionDigits:
                    1,
                  maximumFractionDigits:
                    1,
                }
              )} multas aplicadas por fiscalização em média`,
            };
          }

          if (
            card.key ===
            "cnh_collected"
          ) {
            return {
              ...card,

              secondary: `${calculatePercentage(
                cnhCollected,
                approached
              ).toLocaleString(
                "pt-BR",
                {
                  minimumFractionDigits:
                    2,
                  maximumFractionDigits:
                    2,
                }
              )}% dos abordados tiveram a CNH recolhida`,
            };
          }

          return card;
        }
      ),

      {
        key: "alcohol_cases",
        label:
          "Casos de alcoolemia",
        value: alcoholCases,

        secondary: `${calculatePercentage(
          alcoholCases,
          approached
        ).toLocaleString(
          "pt-BR",
          {
            minimumFractionDigits:
              2,
            maximumFractionDigits:
              2,
          }
        )}% dos abordados foram classificados como casos de alcoolemia`,
      },
    ];
  }, [dashboard]);


  const taxonomy = useMemo(
    () =>
      buildInspectionStatisticsTaxonomy(
        dashboard || {}
      ),
    [dashboard]
  );


  const historicalYearlyTable =
    dashboard?.historical_yearly_table ||
    null;

  const hasData = Boolean(
    dashboard?.meta?.has_data
  );

  const rainTotal =
    dashboard?.occurrences?.rain ??
    dashboard?.public_security?.rain ??
    0;

  const inspectionsTotal =
    dashboard?.summary?.operations ??
    0;

  const rainPercentage =
    inspectionsTotal > 0
      ? (rainTotal /
          inspectionsTotal) *
        100
      : 0;


  const handleApplyFilters = () => {
    setFilters(draftFilters);

    if (
      activeTab ===
      "territorial"
    ) {
      loadTerritorial(
        draftFilters
      );
    } else {
      loadDashboard(
        draftFilters
      );
    }
  };


  const handleClearFilters = () => {
    const next =
      buildDefaultFilters();

    setDraftFilters(next);
    setFilters(next);

    if (
      activeTab ===
      "territorial"
    ) {
      loadTerritorial(next);
    } else {
      loadDashboard(next);
    }
  };


  const openOfficialTab = () => {
    setActiveTab("official");

    if (!dashboard) {
      loadDashboard(filters);
    }
  };


  const openTerritorialTab = () => {
    setActiveTab(
      "territorial"
    );

    if (!territorial) {
      loadTerritorial(filters);
    }
  };


  return (
    <section className="stats-dashboard">
      <div className="stats-hero">
        <div>
          <span>
            Fiscalização
          </span>

          <h1>
            Estatística Fiscalização
          </h1>

          <p>
            Indicadores oficiais e análise
            territorial da Fiscalização da
            Operação Lei Seca.
          </p>
        </div>

        {activeTab ===
        "official" ? (
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
              Operações interrompidas por
              chuva
            </div>

            <div
              style={{
                display: "flex",
                justifyContent:
                  "flex-end",
                alignItems:
                  "baseline",
                gap: "8px",
              }}
            >
              <div
                style={{
                  display: "flex",
                  alignItems:
                    "center",
                  gap: "6px",
                }}
              >
                <CloudRain
                  size={22}
                  strokeWidth={2.2}
                />

                <strong
                  style={{
                    fontSize:
                      "24px",
                    lineHeight: 1,
                  }}
                >
                  {integer(
                    rainTotal
                  )}
                </strong>
              </div>

              <span
                style={{
                  fontSize:
                    "14px",
                  fontWeight: 700,
                }}
              >
                {rainPercentage.toLocaleString(
                  "pt-BR",
                  {
                    minimumFractionDigits:
                      2,
                    maximumFractionDigits:
                      2,
                  }
                )}
                %
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
        ) : (
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
              Classificação territorial
            </div>

            <strong
              style={{
                fontSize: "18px",
              }}
            >
              Região Metropolitana ×
              Interior
            </strong>

            <div
              style={{
                fontSize: "11px",
                opacity: 0.82,
                marginTop: "4px",
              }}
            >
              Municípios e regiões do
              Estado do Rio de Janeiro
            </div>
          </div>
        )}
      </div>


      <div
        className="stats-tabs"
        style={{
          display: "flex",
          gap: "8px",
          margin:
            "18px 0",
          padding: "4px",
          background:
            "#f1f5f9",
          borderRadius:
            "10px",
          width:
            "fit-content",
        }}
      >
        <button
          type="button"
          onClick={
            openOfficialTab
          }
          style={{
            border: 0,
            borderRadius:
              "8px",
            padding:
              "10px 18px",
            cursor:
              "pointer",
            fontWeight: 700,

            background:
              activeTab ===
              "official"
                ? "#0f172a"
                : "transparent",

            color:
              activeTab ===
              "official"
                ? "#ffffff"
                : "#475569",
          }}
        >
          Estatística Oficial
        </button>

        <button
          type="button"
          onClick={
            openTerritorialTab
          }
          style={{
            border: 0,
            borderRadius:
              "8px",
            padding:
              "10px 18px",
            cursor:
              "pointer",
            fontWeight: 700,

            background:
              activeTab ===
              "territorial"
                ? "#0f172a"
                : "transparent",

            color:
              activeTab ===
              "territorial"
                ? "#ffffff"
                : "#475569",
          }}
        >
          Análise Territorial
        </button>
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
            value={
              draftFilters.date_from
            }
            onChange={(
              event
            ) =>
              setDraftFilters(
                (current) => ({
                  ...current,

                  date_from:
                    event.target
                      .value,
                })
              )
            }
          />
        </label>

        <label>
          Até

          <input
            type="date"
            value={
              draftFilters.date_to
            }
            onChange={(
              event
            ) =>
              setDraftFilters(
                (current) => ({
                  ...current,

                  date_to:
                    event.target
                      .value,
                })
              )
            }
          />
        </label>

        <label>
          Equipe

          <input
            placeholder="Ex.: A3"
            value={
              draftFilters.team
            }
            onChange={(
              event
            ) =>
              setDraftFilters(
                (current) => ({
                  ...current,

                  team:
                    event.target
                      .value,
                })
              )
            }
          />
        </label>

        <div className="stats-filter-actions">
          <button
            className="primary"
            onClick={
              handleApplyFilters
            }
          >
            Aplicar
          </button>

          <button
            type="button"
            onClick={
              handleClearFilters
            }
          >
            Limpar
          </button>
        </div>
      </div>


      {activeTab ===
      "territorial" ? (
        <TerritorialContent
          territorial={
            territorial
          }
          loading={
            territorialLoading
          }
          error={
            territorialError
          }
          filters={filters}
        />
      ) : loading ? (
        <div className="stats-panel">
          <div className="stats-loading">
            Carregando estatísticas de
            Fiscalização...
          </div>
        </div>
      ) : error ? (
        <div className="stats-panel">
          <div
            className="stats-loading"
            style={{
              color:
                "var(--danger)",
            }}
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
              Nenhum dado estatístico de
              Fiscalização para o período
              selecionado.
            </strong>

            <span>
              Verifique o período
              informado ou os filtros
              aplicados.
            </span>
          </div>
        </div>
      ) : (
        <>
          <div className="stats-kpi-grid inspection-kpi-grid">
            {cards.map(
              (card) => {
                const meta =
                  executiveCardMeta[
                    card.key
                  ] ||
                  executiveCardMeta.operations;

                const Icon =
                  meta.icon;

                return (
                  <div
                    key={
                      card.key
                    }
                    className="stats-kpi"
                    style={{
                      "--kpi":
                        meta.color,
                    }}
                  >
                    <div className="stats-kpi-top">
                      <span className="stats-kpi-icon">
                        <Icon
                          size={18}
                        />
                      </span>

                      {
                        card.label
                      }
                    </div>

                    <div className="stats-kpi-value">
                      {displayMetric(
                        card.value
                      )}
                    </div>

                    {card.secondary ? (
                      <div
                        style={{
                          marginTop:
                            "6px",
                          fontSize:
                            "10.5px",
                          lineHeight:
                            1.25,
                          fontWeight:
                            600,
                          color:
                            "var(--muted)",
                        }}
                      >
                        {
                          card.secondary
                        }
                      </div>
                    ) : null}
                  </div>
                );
              }
            )}
          </div>


          <div className="inspection-taxonomy-stack">
            {taxonomy.map(
              (category) => (
                <TaxonomyGrid
                  key={
                    category.key
                  }
                  category={
                    category
                  }
                />
              )
            )}
          </div>


          {historicalYearlyTable
            ?.rows?.length ? (
            <Section
              title="Evolução da Fiscalização"
              subtitle="Comparativo anual entre fiscalizações, abordados e casos de alcoolemia."
            >
              <div
                className="stats-chart"
                style={{
                  height:
                    "420px",
                }}
              >
                <ResponsiveContainer
                  width="100%"
                  height="100%"
                >
                  <BarChart
                    data={
                      historicalYearlyTable.rows
                    }
                    margin={{
                      top: 34,
                      right: 8,
                      left: 8,
                      bottom: 0,
                    }}
                  >
                    <CartesianGrid
                      strokeDasharray="3 3"
                    />

                    <XAxis
                      dataKey="year"
                    />

                    <YAxis
                      yAxisId="approached"
                      tickFormatter={(
                        value
                      ) =>
                        integer(
                          value
                        )
                      }
                    />

                    <YAxis
                      yAxisId="other"
                      orientation="right"
                      tickFormatter={(
                        value
                      ) =>
                        integer(
                          value
                        )
                      }
                    />

                    <Tooltip
                      formatter={(
                        value,
                        name
                      ) => [
                        integer(
                          value
                        ),
                        name,
                      ]}
                    />

                    <Legend />

                    <Bar
                      yAxisId="other"
                      dataKey="operations"
                      name="Fiscalizações"
                      fill="#0f766e"
                      radius={[
                        5,
                        5,
                        0,
                        0,
                      ]}
                    >
                      <LabelList
                        dataKey="operations"
                        position="top"
                        formatter={(
                          value
                        ) =>
                          integer(
                            value
                          )
                        }
                      />
                    </Bar>

                    <Bar
                      yAxisId="other"
                      dataKey="alcohol_cases"
                      name="Casos de alcoolemia"
                      fill="#b45309"
                      radius={[
                        5,
                        5,
                        0,
                        0,
                      ]}
                    >
                      <LabelList
                        dataKey="alcohol_cases"
                        content={
                          <AlcoholBarLabel />
                        }
                      />
                    </Bar>

                    <Line
                      yAxisId="approached"
                      type="monotone"
                      dataKey="approached"
                      name="Abordados"
                      stroke="#1d4ed8"
                      strokeWidth={
                        3
                      }
                      dot={{
                        r: 4,
                      }}
                      activeDot={{
                        r: 6,
                      }}
                    >
                      <LabelList
                        dataKey="approached"
                        content={
                          <ApproachedLineLabel />
                        }
                      />
                    </Line>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </Section>
          ) : null}


          {historicalYearlyTable
            ?.rows?.length ? (
            <Section
              title="Série Histórica da Fiscalização"
              subtitle="Consolidado institucional anual. Em 2026, o histórico até 09/08 é continuado pela produção homologada a partir de 10/08."
            >
              <div
                className="stats-table-wrap"
                style={{
                  overflowX:
                    "auto",
                }}
              >
                <table
                  className="stats-table"
                  style={{
                    minWidth:
                      "2100px",

                    whiteSpace:
                      "nowrap",
                  }}
                >
                  <thead>
                    <tr>
                      <th
                        style={{
                          position:
                            "sticky",
                          left: 0,
                          zIndex: 2,

                          background:
                            "var(--surface, #fff)",

                          minWidth:
                            "245px",
                        }}
                      >
                        Indicador
                      </th>

                      {historicalYearlyTable.years.map(
                        (year) => (
                          <th
                            key={
                              year
                            }
                          >
                            {year}
                          </th>
                        )
                      )}

                      <th>
                        Total
                      </th>
                    </tr>
                  </thead>

                  <tbody>
                    {historicalTableIndicators.map(
                      (
                        indicator
                      ) => (
                        <tr
                          key={
                            indicator.key
                          }
                        >
                          <td
                            style={{
                              position:
                                "sticky",

                              left: 0,

                              zIndex:
                                1,

                              background:
                                "var(--surface, #fff)",

                              fontWeight:
                                600,
                            }}
                          >
                            {
                              indicator.label
                            }
                          </td>

                          {historicalYearlyTable.rows.map(
                            (
                              row
                            ) => (
                              <td
                                key={`${indicator.key}-${row.year}`}
                              >
                                {displayHistoricalValue(
                                  row[
                                    indicator
                                      .key
                                  ],

                                  indicator.percentage
                                )}
                              </td>
                            )
                          )}

                          <td
                            style={{
                              fontWeight:
                                700,
                            }}
                          >
                            {displayHistoricalValue(
                              historicalYearlyTable
                                .total?.[
                                indicator
                                  .key
                              ],

                              indicator.percentage
                            )}
                          </td>
                        </tr>
                      )
                    )}
                  </tbody>
                </table>
              </div>

              <div
                style={{
                  marginTop:
                    "12px",
                  fontSize:
                    "12px",
                  color:
                    "var(--muted)",
                }}
              >
                Histórico consolidado até
                09/08/2026. A coluna de
                2026 continua sendo
                atualizada com a produção
                estatística homologada a
                partir de 10/08/2026.
              </div>
            </Section>
          ) : null}
        </>
      )}
    </section>
  );
}