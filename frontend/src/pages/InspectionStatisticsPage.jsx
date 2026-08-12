import {
  AlertCircle,
  BarChart3,
  CarFront,
  ClipboardCheck,
  Filter,
  Gauge,
  ShieldAlert,
  TestTube2,
  Users,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import {
  Bar,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { getInspectionStatisticsDashboard } from "../api/inspectionStatistics.js";
import { formatDateBR } from "../utils/date.js";
import "./StatisticsPage.css";

const CUTOFF_DATE = "2026-08-10";

function toIsoDate(value) {
  return value.toISOString().slice(0, 10);
}

function buildDefaultFilters() {
  const today = new Date();
  const monthStart = new Date(today.getFullYear(), today.getMonth(), 1);
  const cutoff = new Date(`${CUTOFF_DATE}T00:00:00`);
  const start = monthStart < cutoff ? cutoff : monthStart;
  return {
    date_from: toIsoDate(start),
    date_to: toIsoDate(today),
    team: "",
  };
}

function integer(value) {
  return new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 0 }).format(Number(value || 0));
}

function displayMetric(value) {
  return value === null || value === undefined ? "Não informado" : integer(value);
}

function buildCards(summary = {}) {
  return [
    { key: "homologated_reports", label: "Relatórios homologados", value: summary.homologated_reports, icon: ClipboardCheck, color: "#0048d7" },
    { key: "operations", label: "Operações", value: summary.operations, icon: ShieldAlert, color: "#0f766e" },
    { key: "approach", label: "Abordados", value: summary.approach, icon: Users, color: "#1d4ed8" },
    { key: "reconductor", label: "Recondutores", value: summary.reconductor, icon: Gauge, color: "#0369a1" },
    { key: "refusal", label: "Recusas", value: summary.refusal, icon: AlertCircle, color: "#b45309" },
    { key: "fined", label: "Multados", value: summary.fined, icon: ClipboardCheck, color: "#7c3aed" },
    { key: "towed", label: "Rebocados", value: summary.towed, icon: CarFront, color: "#0f766e" },
    { key: "cnh_collected", label: "CNH recolhidas", value: summary.cnh_collected, icon: ShieldAlert, color: "#be123c" },
    { key: "passive_tests_performed", label: "Testes passivos", value: summary.passive_tests_performed, icon: TestTube2, color: "#0891b2" },
  ];
}

function MetricGrid({ items }) {
  return (
    <div style={{ display: "grid", gap: "14px", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))" }}>
      {items.map((item) => (
        <div key={item.label} className="stats-kpi" style={{ "--kpi": item.color }}>
          <div className="stats-kpi-top">
            <span className="stats-kpi-icon">
              <item.icon size={18} />
            </span>
            {item.label}
          </div>
          <div className="stats-kpi-value">{displayMetric(item.value)}</div>
        </div>
      ))}
    </div>
  );
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

export default function InspectionStatisticsPage() {
  const [filters, setFilters] = useState(buildDefaultFilters);
  const [draftFilters, setDraftFilters] = useState(buildDefaultFilters);
  const [dashboard, setDashboard] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const loadDashboard = async (params = filters) => {
    setLoading(true);
    setError("");
    try {
      const response = await getInspectionStatisticsDashboard(params);
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

  const cards = useMemo(() => buildCards(dashboard?.summary || {}), [dashboard]);
  const timeSeries = dashboard?.time_series || [];
  const teamProduction = dashboard?.team_production || [];
  const hasData = Boolean(dashboard?.meta?.has_data);

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
          <p>Indicadores oficiais gerados a partir dos Relatórios de Fiscalização homologados no SIED.</p>
        </div>
        <div style={{ textAlign: "right", fontSize: "12px", color: "rgba(255,255,255,0.82)" }}>
          <div>Base operacional homologada</div>
          <div>Recorte disponível desde {formatDateBR(CUTOFF_DATE)}</div>
        </div>
      </div>

      <div className="stats-filters">
        <div className="stats-filter-title">
          <Filter size={16} />
          Filtros
        </div>
        <label>
          Data inicial
          <input
            type="date"
            min={CUTOFF_DATE}
            value={draftFilters.date_from}
            onChange={(event) => setDraftFilters((current) => ({ ...current, date_from: event.target.value }))}
          />
        </label>
        <label>
          Data final
          <input
            type="date"
            min={CUTOFF_DATE}
            value={draftFilters.date_to}
            onChange={(event) => setDraftFilters((current) => ({ ...current, date_to: event.target.value }))}
          />
        </label>
        <label>
          Equipe
          <input
            placeholder="Ex.: A3"
            value={draftFilters.team}
            onChange={(event) => setDraftFilters((current) => ({ ...current, team: event.target.value }))}
          />
        </label>
        <div className="stats-filter-actions">
          <button className="primary" onClick={handleApplyFilters}>Aplicar</button>
          <button type="button" onClick={handleClearFilters}>Limpar</button>
        </div>
      </div>

      {loading ? (
        <div className="stats-panel">
          <div className="stats-loading">Carregando estatísticas de Fiscalização...</div>
        </div>
      ) : error ? (
        <div className="stats-panel">
          <div className="stats-loading" style={{ color: "var(--danger)" }}>{error}</div>
        </div>
      ) : !hasData ? (
        <div className="stats-panel">
          <div className="stats-empty" style={{ gap: "8px", padding: "28px" }}>
            <strong>Nenhum dado estatístico de Fiscalização homologado para o período selecionado.</strong>
            <span>
              Os relatórios homologados entram nesta página apenas após a inclusão oficial na estatística.
            </span>
          </div>
        </div>
      ) : (
        <>
          <div className="stats-kpi-grid">
            {cards.map((card) => (
              <div key={card.key} className="stats-kpi" style={{ "--kpi": card.color }}>
                <div className="stats-kpi-top">
                  <span className="stats-kpi-icon">
                    <card.icon size={18} />
                  </span>
                  {card.label}
                </div>
                <div className="stats-kpi-value">{displayMetric(card.value)}</div>
              </div>
            ))}
          </div>

          <div className="stats-two-columns">
            <Section title="Resultados de Alcoolemia" subtitle="Totais oficiais consolidados no período filtrado.">
              <MetricGrid
                items={[
                  { label: "0,00 a 0,04", value: dashboard.alcohol_results?.four_ml, icon: TestTube2, color: "#0369a1" },
                  { label: "0,05 a 0,33", value: dashboard.alcohol_results?.thirtythree_ml, icon: TestTube2, color: "#0f766e" },
                  { label: "Acima de 0,33", value: dashboard.alcohol_results?.thirtyfour_ml, icon: TestTube2, color: "#be123c" },
                  { label: "Recusas", value: dashboard.alcohol_results?.refusal, icon: AlertCircle, color: "#b45309" },
                ]}
              />
            </Section>

            <Section title="Medidas Administrativas" subtitle="Sem ajuste manual dos quantitativos homologados.">
              <MetricGrid
                items={[
                  { label: "Multados", value: dashboard.administrative_measures?.fined, icon: ClipboardCheck, color: "#7c3aed" },
                  { label: "Rebocados", value: dashboard.administrative_measures?.towed, icon: CarFront, color: "#0f766e" },
                  { label: "CNH recolhidas", value: dashboard.administrative_measures?.cnh_collected, icon: ShieldAlert, color: "#be123c" },
                  { label: "Deliberações de remoção", value: dashboard.administrative_measures?.removal_resolutions, icon: BarChart3, color: "#1d4ed8" },
                ]}
              />
            </Section>
          </div>

          <div className="stats-two-columns">
            <Section title="Ocorrências" subtitle="Recorte consolidado das ocorrências homologadas.">
              <MetricGrid
                items={[
                  { label: "Ocorrências criminais", value: dashboard.occurrences?.criminal_occurrences, icon: AlertCircle, color: "#be123c" },
                  { label: "Art. 307", value: dashboard.occurrences?.art307, icon: ShieldAlert, color: "#b45309" },
                  { label: "Dirigir com CNH cassada", value: dashboard.occurrences?.driving_canceled_license, icon: CarFront, color: "#0f766e" },
                  { label: "Prisões por outros meios", value: dashboard.occurrences?.arrests_means_evidence, icon: ClipboardCheck, color: "#7c3aed" },
                ]}
              />
            </Section>

            <Section title="Outros indicadores" subtitle="Campos oficiais adicionais já disponíveis na estatística homologada.">
              <MetricGrid
                items={[
                  { label: "Celebridades/Autoridades", value: dashboard.summary?.celebrities_authorities, icon: Users, color: "#0f766e" },
                  { label: "Recondutores", value: dashboard.summary?.reconductor, icon: Gauge, color: "#0369a1" },
                  { label: "Testes passivos", value: dashboard.summary?.passive_tests_performed, icon: TestTube2, color: "#0891b2" },
                  { label: "Operações", value: dashboard.summary?.operations, icon: ShieldAlert, color: "#0048d7" },
                ]}
              />
            </Section>
          </div>

          <div className="stats-two-columns">
            <Section title="Série temporal operacional" subtitle="Evolução diária dos relatórios homologados no período selecionado.">
              <div className="stats-chart">
                <ResponsiveContainer>
                  <ComposedChart data={timeSeries}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis
                      dataKey="operation_date"
                      tickFormatter={(value) => formatDateBR(value)}
                    />
                    <YAxis yAxisId="left" />
                    <YAxis yAxisId="right" orientation="right" />
                    <Tooltip
                      formatter={(value) => integer(value)}
                      labelFormatter={(value) => formatDateBR(value)}
                    />
                    <Legend />
                    <Bar yAxisId="left" dataKey="approach" name="Abordados" fill="#0048d7" radius={[6, 6, 0, 0]} />
                    <Line yAxisId="right" type="monotone" dataKey="refusal" name="Recusas" stroke="#b45309" strokeWidth={3} />
                    <Line yAxisId="right" type="monotone" dataKey="fined" name="Multados" stroke="#7c3aed" strokeWidth={3} />
                  </ComposedChart>
                </ResponsiveContainer>
              </div>
            </Section>

            <Section title="Produção por Equipe" subtitle="Ordenação inicial por abordados em ordem decrescente.">
              <div className="stats-table-wrap">
                <table className="stats-table">
                  <thead>
                    <tr>
                      <th>Equipe</th>
                      <th>Relatórios</th>
                      <th>Operações</th>
                      <th>Abordados</th>
                      <th>Recusas</th>
                      <th>Multados</th>
                      <th>Rebocados</th>
                    </tr>
                  </thead>
                  <tbody>
                    {teamProduction.map((row) => (
                      <tr key={row.team || "sem-equipe"}>
                        <td>{row.team || "Não informado"}</td>
                        <td>{displayMetric(row.reports)}</td>
                        <td>{displayMetric(row.operations)}</td>
                        <td>{displayMetric(row.approach)}</td>
                        <td>{displayMetric(row.refusal)}</td>
                        <td>{displayMetric(row.fined)}</td>
                        <td>{displayMetric(row.towed)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Section>
          </div>

          <div className="alert">
            Regra de consolidação: a API usa apenas <strong>InspectionStatistic</strong>. Sem registros homologados no filtro, os indicadores ficam vazios. Com base homologada, o <strong>SUM</strong> ignora valores <strong>NULL</strong>; se todos os valores de um indicador forem <strong>NULL</strong>, o resultado permanece <strong>Não informado</strong>.
          </div>
        </>
      )}
    </section>
  );
}
