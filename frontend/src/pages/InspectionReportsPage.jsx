import { AlertCircle, ChevronDown, ChevronRight, Download, Eye, RefreshCw, Search, X } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import {
  excludeInspectionReportFromStatistics,
  getInspectionReport,
  includeInspectionReportInStatistics,
  listInspectionReports,
  listInspectionReportsByPageUrl,
} from "../api/inspection.js";
import { useAuth } from "../context/AuthContext.jsx";
import { formatDateBR } from "../utils/date.js";
import { canReviewInspectionStatistics as canReviewInspectionStatisticsUser } from "../utils/permissions.js";
import { generateInspectionReportPdf } from "../utils/inspectionReportPdfGenerator.js";

const emptyStatisticsClassification = {
  fugitives: false,
  flagrante: false,
  simulacrum: false,
  weapons: false,
  recovered_vehicles: false,
  stolen_vehicles: false,
  robbed_vehicles: false,
  narcotics: false,
  bribery: false,
  art311: false,
  art306: false,
  rain: false,
};

const statisticsClassificationLabels = {
  fugitives: "Foragido",
  flagrante: "Flagrante",
  simulacrum: "Simulacro",
  weapons: "Arma",
  recovered_vehicles: "Veículo recuperado",
  stolen_vehicles: "Veículo furtado",
  robbed_vehicles: "Veículo roubado",
  narcotics: "Entorpecentes",
  bribery: "Suborno",
  art311: "Art. 311 CP",
  art306: "Art. 306 CTB",
  rain: "Chuva",
};

const emptyFilters = {
  date_from: "",
  date_to: "",
  team: "",
  statistics_status: "",
};

const syncStatusMeta = {
  SYNCED: { label: "Sincronizado", className: "neutral" },
  PENDING_REVIEW: { label: "Pendente de revisão", className: "warning" },
  APPROVED: { label: "Aprovado", className: "success" },
  RETURNED: { label: "Devolvido", className: "danger" },
};

const statisticsStatusMeta = {
  PENDING: { label: "Aguardando análise", className: "warning" },
  INCLUDED: { label: "Incluído na estatística", className: "success" },
  EXCLUDED: { label: "Não incluído", className: "danger" },
};

function formatDateTimeBR(value) {
  if (!value) return "Não informado";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return new Intl.DateTimeFormat("pt-BR", {
    dateStyle: "short",
    timeStyle: "short",
    timeZone: "America/Sao_Paulo",
  }).format(date);
}

function displayValue(value) {
  if (value === null || value === undefined || value === "") return "Não informado";
  return String(value);
}

function numberValue(value) {
  if (value === null || value === undefined) return null;
  return Number(value) || 0;
}

function buildOperationVisualSummary(operations = []) {
  return operations.reduce(
    (acc, operation) => ({
      approach: acc.approach + (numberValue(operation.approach) ?? 0),
      refusal: acc.refusal + (numberValue(operation.refusal) ?? 0),
      fined: acc.fined + (numberValue(operation.fined) ?? 0),
      cnhCollected: acc.cnhCollected + (numberValue(operation.cnh_collected) ?? 0),
      towed: acc.towed + (numberValue(operation.towed) ?? 0),
    }),
    { approach: 0, refusal: 0, fined: 0, cnhCollected: 0, towed: 0 }
  );
}

function DetailField({ label, value }) {
  return (
    <div style={{ display: "grid", gap: "4px" }}>
      <small style={{ color: "var(--pico-muted-color)", fontWeight: 700 }}>{label}</small>
      <span style={{ color: "var(--text-main)", wordBreak: "break-word", whiteSpace: "pre-wrap" }}>{displayValue(value)}</span>
    </div>
  );
}

function DetailSection({ title, children }) {
  return (
    <section
      style={{
        display: "grid",
        gap: "16px",
        border: "1px solid var(--line)",
        borderRadius: "16px",
        padding: "18px",
        background: "var(--surface)",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: "12px" }}>
        <h3 style={{ margin: 0, color: "var(--primary-strong)", fontSize: "18px" }}>{title}</h3>
      </div>
      {children}
    </section>
  );
}

function DecisionModal({ title, body, confirmLabel, onConfirm, onClose, confirmClassName = "", children, loading = false, disableConfirm = false }) {
  return (
    <div className="modal-overlay" onClick={() => !loading && onClose()}>
      <div className="premium-modal" style={{ maxWidth: "560px" }} onClick={(event) => event.stopPropagation()}>
        <div className="modal-header-premium">
          <div>
            <h2 style={{ margin: 0 }}>{title}</h2>
            {body ? <p style={{ margin: "8px 0 0", color: "var(--pico-muted-color)" }}>{body}</p> : null}
          </div>
          <button className="icon-button" onClick={onClose} disabled={loading} aria-label="Fechar modal">
            <X size={18} />
          </button>
        </div>
        <div className="modal-body-premium" style={{ display: "grid", gap: "16px" }}>
          {children}
          <div className="page-actions" style={{ justifyContent: "flex-end" }}>
            <button className="secondary" onClick={onClose} disabled={loading}>
              Cancelar
            </button>
            <button className={confirmClassName} onClick={onConfirm} disabled={loading || disableConfirm}>
              {loading ? "Processando..." : confirmLabel}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function InspectionReportsPage() {
  const { user } = useAuth();
  const [filters, setFilters] = useState(emptyFilters);
  const [draftFilters, setDraftFilters] = useState(emptyFilters);
  const [reports, setReports] = useState([]);
  const [pageInfo, setPageInfo] = useState({ count: 0, next: null, previous: null });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState("");
  const [selectedReport, setSelectedReport] = useState(null);
  const [expandedOperations, setExpandedOperations] = useState({});
  const [decisionError, setDecisionError] = useState("");
  const [actionLoading, setActionLoading] = useState(false);
  const [showIncludeModal, setShowIncludeModal] = useState(false);
  const [showExcludeModal, setShowExcludeModal] = useState(false);
  const [excludeReason, setExcludeReason] = useState("");
  const [statisticsClassification, setStatisticsClassification] = useState({
    ...emptyStatisticsClassification,
  });

  const canReviewStatistics = canReviewInspectionStatisticsUser(user);

  const loadReports = async (params = filters, pageUrl = null) => {
    setLoading(true);
    setError("");
    try {
      const response = pageUrl
        ? await listInspectionReportsByPageUrl(pageUrl)
        : await listInspectionReports({ page_size: 50, ...params });
      setReports(response.results || []);
      setPageInfo({
        count: response.count || 0,
        next: response.next || null,
        previous: response.previous || null,
      });
    } catch (err) {
      setError(err.message);
      setReports([]);
      setPageInfo({ count: 0, next: null, previous: null });
    } finally {
      setLoading(false);
    }
  };

  const refreshSelectedReport = async (reportId) => {
    const data = await getInspectionReport(reportId);
    setSelectedReport(data);
    setStatisticsClassification({
      ...emptyStatisticsClassification,
      ...(data.statistics_classification || {}),
    });
    setExpandedOperations(
      Object.fromEntries((data.operations || []).map((operation, index) => [operation.source_id || `${index}`, true]))
    );
    return data;
  };

  useEffect(() => {
    loadReports(filters);
  }, []);

  const handleApplyFilters = () => {
    setFilters(draftFilters);
    loadReports(draftFilters);
  };

  const handleClearFilters = () => {
    setDraftFilters(emptyFilters);
    setFilters(emptyFilters);
    loadReports(emptyFilters);
  };

  const openDetail = async (reportId) => {
    setSelectedReport(null);
    setDetailError("");
    setDecisionError("");
    setDetailLoading(true);
    try {
      await refreshSelectedReport(reportId);
    } catch (err) {
      setDetailError(err.message);
    } finally {
      setDetailLoading(false);
    }
  };

  const closeDetail = () => {
    if (actionLoading) return;
    setSelectedReport(null);
    setDetailError("");
    setDecisionError("");
    setShowIncludeModal(false);
    setShowExcludeModal(false);
    setExcludeReason("");
    setStatisticsClassification({ ...emptyStatisticsClassification });
  };

  const toggleOperation = (key) => {
    setExpandedOperations((current) => ({ ...current, [key]: !current[key] }));
  };

  const toggleStatisticsClassification = (key) => {
    if (!showReviewActions || actionLoading) return;

    setStatisticsClassification((current) => ({
      ...current,
      [key]: !current[key],
    }));
  };

  const handleInclude = async () => {
    if (!selectedReport) return;
    setActionLoading(true);
    setDecisionError("");
    try {
      const response = await includeInspectionReportInStatistics(
        selectedReport.id,
        statisticsClassification
      );
      setSelectedReport(response.report);
      setShowIncludeModal(false);
      await loadReports(filters);
    } catch (err) {
      setDecisionError(err.message);
    } finally {
      setActionLoading(false);
    }
  };

  const handleExclude = async () => {
    if (!selectedReport) return;
    setActionLoading(true);
    setDecisionError("");
    try {
      const response = await excludeInspectionReportFromStatistics(selectedReport.id, excludeReason.trim());
      setSelectedReport(response.report);
      setShowExcludeModal(false);
      setExcludeReason("");
      await loadReports(filters);
    } catch (err) {
      setDecisionError(err.message);
    } finally {
      setActionLoading(false);
    }
  };

  const visualSummary = useMemo(
    () => buildOperationVisualSummary(selectedReport?.operations || []),
    [selectedReport]
  );

  const statisticsMeta = statisticsStatusMeta[selectedReport?.statistics_status] || { label: selectedReport?.statistics_status, className: "neutral" };
  const syncMeta = syncStatusMeta[selectedReport?.status] || { label: selectedReport?.status, className: "neutral" };
  const showReviewActions = canReviewStatistics && selectedReport?.statistics_status === "PENDING";

  return (
    <section className="page">
      <div className="page-title">
        <div>
          <h1>Relatórios de Fiscalização</h1>
          <p>Consulta dos relatórios espelhados do Horus e homologação estatística pela OLS/CooAdm.</p>
        </div>
      </div>

      <div className="side-panel" style={{ position: "static" }}>
        <div style={{ display: "grid", gap: "14px", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))" }}>
          <label className="filter-field" style={{ display: "grid", gap: "6px" }}>
            <span>De</span>
            <input type="date" value={draftFilters.date_from} onChange={(event) => setDraftFilters((current) => ({ ...current, date_from: event.target.value }))} />
          </label>
          <label className="filter-field" style={{ display: "grid", gap: "6px" }}>
            <span>Até</span>
            <input type="date" value={draftFilters.date_to} onChange={(event) => setDraftFilters((current) => ({ ...current, date_to: event.target.value }))} />
          </label>
          <label className="filter-field" style={{ display: "grid", gap: "6px" }}>
            <span>Equipe</span>
            <input placeholder="Ex.: A3" value={draftFilters.team} onChange={(event) => setDraftFilters((current) => ({ ...current, team: event.target.value }))} />
          </label>
          <label className="filter-field" style={{ display: "grid", gap: "6px" }}>
            <span>Situação estatística</span>
            <select
              value={draftFilters.statistics_status}
              onChange={(event) => setDraftFilters((current) => ({ ...current, statistics_status: event.target.value }))}
            >
              <option value="">Todas</option>
              <option value="PENDING">Aguardando análise</option>
              <option value="INCLUDED">Incluído na estatística</option>
              <option value="EXCLUDED">Não incluído</option>
            </select>
          </label>
        </div>

        <div className="page-actions" style={{ justifyContent: "flex-start" }}>
          <button onClick={handleApplyFilters}>
            <Search size={16} />
            Pesquisar
          </button>
          <button className="secondary" onClick={handleClearFilters}>
            Limpar filtros
          </button>
          <button className="secondary" onClick={() => loadReports(filters)}>
            <RefreshCw size={16} />
            Atualizar
          </button>
        </div>
      </div>

      <div className="table-wrap premium-table-wrap">
        <h2>Listagem</h2>
        {loading ? (
          <div style={{ padding: "24px 16px" }}>Carregando relatórios de Fiscalização...</div>
        ) : error ? (
          <div style={{ padding: "24px 16px", color: "var(--danger)", display: "flex", alignItems: "center", gap: "10px" }}>
            <AlertCircle size={18} />
            <span>{error}</span>
          </div>
        ) : reports.length === 0 ? (
          <div style={{ padding: "24px 16px", display: "grid", gap: "6px" }}>
            {Object.values(filters).some(Boolean) ? (
              "Nenhum relatório encontrado para os filtros informados."
            ) : (
              <>
                <strong>Nenhum relatório de Fiscalização sincronizado até o momento.</strong>
                <span style={{ color: "var(--pico-muted-color)" }}>
                  Os relatórios aparecerão aqui após a sincronização dos dados do Horus.
                </span>
              </>
            )}
          </div>
        ) : (
          <>
            <table>
              <thead>
                <tr>
                  <th>Data da operação</th>
                  <th>Equipe</th>
                  <th>Situação estatística</th>
                  <th>Operações</th>
                  <th>Abordados</th>
                  <th>Recusas</th>
                  <th>Multados</th>
                  <th>Última sincronização</th>
                  <th>Ação</th>
                </tr>
              </thead>
              <tbody>
                {reports.map((report) => {
                  const meta = statisticsStatusMeta[report.statistics_status] || { label: report.statistics_status, className: "neutral" };
                  return (
                    <tr key={report.id}>
                      <td>{formatDateBR(report.operation_date)}</td>
                      <td><strong>{displayValue(report.team)}</strong></td>
                      <td><span className={`badge ${meta.className}`}>{meta.label}</span></td>
                      <td>{displayValue(report.operation_count)}</td>
                      <td>{displayValue(report.total_approach)}</td>
                      <td>{displayValue(report.total_refusal)}</td>
                      <td>{displayValue(report.total_fined)}</td>
                      <td>{formatDateTimeBR(report.synced_at)}</td>
                      <td>
                        <button className="secondary" onClick={() => openDetail(report.id)}>
                          <Eye size={15} />
                          Visualizar
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>

            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: "12px", padding: "16px" }}>
              <span>{pageInfo.count} registros</span>
              <div style={{ display: "flex", gap: "8px" }}>
                <button className="secondary" disabled={!pageInfo.previous || loading} onClick={() => pageInfo.previous && loadReports(filters, pageInfo.previous)}>
                  Anterior
                </button>
                <button className="secondary" disabled={!pageInfo.next || loading} onClick={() => pageInfo.next && loadReports(filters, pageInfo.next)}>
                  Próxima
                </button>
              </div>
            </div>
          </>
        )}
      </div>

      {(detailLoading || detailError || selectedReport) && (
        <div className="modal-overlay" onClick={closeDetail}>
          <div className="premium-modal" style={{ maxWidth: "1100px" }} onClick={(event) => event.stopPropagation()}>
            <div className="modal-header-premium">
              <div>
                <h2 style={{ margin: 0 }}>Relatório de Fiscalização</h2>
                {selectedReport ? (
                  <p style={{ margin: "6px 0 0", color: "var(--pico-muted-color)" }}>
                    Equipe: <strong>{displayValue(selectedReport.team)}</strong> • Data da operação: <strong>{formatDateBR(selectedReport.operation_date)}</strong>
                  </p>
                ) : null}
              </div>
              <button className="icon-button" onClick={closeDetail} aria-label="Fechar detalhe" disabled={actionLoading}>
                <X size={18} />
              </button>
            </div>

            <div className="modal-body-premium" style={{ display: "grid", gap: "20px" }}>
              {detailLoading ? (
                <div>Carregando detalhe do relatório...</div>
              ) : detailError ? (
                <div style={{ color: "var(--danger)", display: "flex", alignItems: "center", gap: "10px" }}>
                  <AlertCircle size={18} />
                  <span>{detailError}</span>
                </div>
              ) : selectedReport ? (
                <>
                  {decisionError ? (
                    <div style={{ padding: "14px 16px", borderRadius: "14px", border: "1px solid rgba(190,24,93,0.2)", background: "#fff1f2", color: "#9f1239" }}>
                      {decisionError}
                    </div>
                  ) : null}

                  <div className="page-actions" style={{ justifyContent: "flex-end" }}>
                    <button className="secondary" onClick={() => generateInspectionReportPdf(selectedReport)}>
                      <Download size={16} />
                      PDF
                    </button>
                  </div>

                  {selectedReport.has_source_update_after_statistics_review ? (
                    <div style={{ padding: "14px 16px", borderRadius: "14px", border: "1px solid rgba(180,83,9,0.2)", background: "#fff7ed", color: "#9a3412" }}>
                      O relatório recebeu uma atualização na origem após a homologação estatística.
                    </div>
                  ) : null}

                  <DetailSection title="Cabeçalho">
                    <div style={{ display: "grid", gap: "14px", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))" }}>
                      <DetailField label="Equipe" value={selectedReport.team} />
                      <DetailField label="Data da operação" value={formatDateBR(selectedReport.operation_date)} />
                      <DetailField label="Situação estatística" value={statisticsMeta.label} />
                      <DetailField label="Situação da sincronização" value={syncMeta.label} />
                      <DetailField label="Última sincronização" value={formatDateTimeBR(selectedReport.synced_at)} />
                      <DetailField label="Atualização da origem" value={formatDateTimeBR(selectedReport.source_updated_at)} />
                    </div>
                  </DetailSection>

                  <DetailSection title="Homologação estatística">
                    <div style={{ display: "grid", gap: "14px", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))" }}>
                      <DetailField label="Situação" value={statisticsMeta.label} />
                      <DetailField label="Responsável" value={selectedReport.statistics_reviewed_by_name} />
                      <DetailField label="Data da decisão" value={formatDateTimeBR(selectedReport.statistics_reviewed_at)} />
                      <DetailField label="Motivo da não inclusão" value={selectedReport.statistics_exclusion_reason} />
                    </div>
                    {showReviewActions ? (
                      <div className="page-actions" style={{ justifyContent: "flex-start" }}>
                        <button onClick={() => setShowIncludeModal(true)} disabled={actionLoading}>
                          Incluir na Estatística
                        </button>
                        <button className="secondary" onClick={() => setShowExcludeModal(true)} disabled={actionLoading}>
                          Não incluir na Estatística
                        </button>
                      </div>
                    ) : null}
                  </DetailSection>

                  <DetailSection title="Dados da operação">
                    <div style={{ display: "grid", gap: "14px", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))" }}>
                      <DetailField label="Chefe da equipe civil" value={selectedReport.civil_chief_name} />
                      <DetailField label="Chefe da equipe militar" value={selectedReport.military_chief_name} />
                      <DetailField label="Efetivo civil" value={selectedReport.segov_team_civil} />
                      <DetailField label="Efetivo militar" value={selectedReport.segov_team_military} />
                      <DetailField label="Agentes do Detran" value={selectedReport.agent_detran} />
                      <DetailField label="Reboques" value={selectedReport.number_trailers} />
                      <DetailField label="Viaturas OLS utilizadas na operação" value={selectedReport.cars} />
                    </div>
                  </DetailSection>

                  <DetailSection title="Complemento">
                    <div style={{ display: "grid", gap: "14px", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))" }}>
                      <DetailField label="OPM de apoio" value={selectedReport.support_opm} />
                      <DetailField label="Efetivo PMERJ de apoio" value={selectedReport.support_pmerj_staff} />
                      <DetailField label="Viaturas de apoio" value={selectedReport.support_vehicles} />
                      <DetailField label="Motivos para baixa abordagem" value={selectedReport.low_approach_reasons} />
                      <DetailField label="Autos de infração da equipe" value={selectedReport.team_violation_notices} />
                      <DetailField label="Especifique os AI utilizados" value={selectedReport.specified_violation_notices} />
                    </div>
                  </DetailSection>

                  <DetailSection title="Alterações">
                    <div style={{ display: "grid", gap: "14px", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))" }}>
                      <DetailField label="Efetivo OLS" value={selectedReport.change_ols} />
                      <DetailField label="Equipe de apoio" value={selectedReport.change_support} />
                      <DetailField label="Alterações de material/equipamento/viatura" value={selectedReport.changes_material} />
                      <DetailField label="Geral" value={selectedReport.miscellaneous_changes} />
                      <DetailField label="Observações gerais" value={selectedReport.changes_general} />
                    </div>
                  </DetailSection>

                  <DetailSection title="Classificação para Estatística">
                    <div style={{ display: "grid", gap: "12px" }}>
                      <p style={{ margin: 0, color: "var(--pico-muted-color)" }}>
                        Confira as Observações gerais do relatório e marque manualmente os itens identificados.
                      </p>

                      <div
                        style={{
                          display: "grid",
                          gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
                          gap: "10px 16px",
                        }}
                      >
                        {Object.entries(statisticsClassificationLabels).map(([key, label]) => (
                          <label
                            key={key}
                            style={{
                              display: "flex",
                              alignItems: "center",
                              gap: "9px",
                              padding: "10px 12px",
                              border: "1px solid var(--line)",
                              borderRadius: "10px",
                              cursor: showReviewActions ? "pointer" : "default",
                              margin: 0,
                            }}
                          >
                            <input
                              type="checkbox"
                              checked={Boolean(statisticsClassification[key])}
                              disabled={!showReviewActions || actionLoading}
                              onChange={() => toggleStatisticsClassification(key)}
                              style={{ margin: 0 }}
                            />
                            <span>{label}</span>
                          </label>
                        ))}
                      </div>

                      {!showReviewActions && selectedReport.statistics_status !== "PENDING" ? (
                        <small style={{ color: "var(--pico-muted-color)" }}>
                          Classificação registrada na homologação estatística.
                        </small>
                      ) : null}
                    </div>
                  </DetailSection>

                  <DetailSection title="Quantitativo">
                    <div style={{ display: "grid", gap: "14px", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))" }}>
                      <DetailField label="Abordados" value={visualSummary.approach} />
                      <DetailField label="Recusas" value={visualSummary.refusal} />
                      <DetailField label="Multados" value={visualSummary.fined} />
                      <DetailField label="CNH recolhidas" value={visualSummary.cnhCollected} />
                      <DetailField label="Rebocados" value={visualSummary.towed} />
                    </div>
                  </DetailSection>

                  <DetailSection title="Operações">
                    <div style={{ display: "grid", gap: "14px" }}>
                      {(selectedReport.operations || []).map((operation, index) => {
                        const opKey = operation.source_id || `${index}`;
                        const expanded = expandedOperations[opKey];
                        return (
                          <article key={opKey} style={{ border: "1px solid var(--line)", borderRadius: "14px", overflow: "hidden" }}>
                            <button
                              type="button"
                              onClick={() => toggleOperation(opKey)}
                              style={{
                                width: "100%",
                                display: "flex",
                                alignItems: "center",
                                justifyContent: "space-between",
                                gap: "12px",
                                padding: "16px 18px",
                                background: "#f8fbff",
                                border: 0,
                                cursor: "pointer",
                              }}
                            >
                              <span style={{ display: "flex", alignItems: "center", gap: "10px", fontWeight: 800, color: "var(--primary-strong)" }}>
                                {expanded ? <ChevronDown size={18} /> : <ChevronRight size={18} />}
                                Operação #{index + 1}
                              </span>
                              <small style={{ color: "var(--pico-muted-color)" }}>{displayValue(operation.address_operation || operation.locality || operation.city)}</small>
                            </button>

                            {expanded ? (
                              <div style={{ display: "grid", gap: "18px", padding: "18px" }}>
                                <div style={{ display: "grid", gap: "14px", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))" }}>
                                  <DetailField label="Endereço da operação" value={operation.address_operation} />
                                  <DetailField label="Outro endereço não listado" value={operation.another_not_listed} />
                                  <DetailField label="CEP" value={operation.cep} />
                                  <DetailField label="Logradouro" value={operation.street} />
                                  <DetailField label="Número" value={operation.number} />
                                  <DetailField label="Bairro" value={operation.district} />
                                  <DetailField label="Município" value={operation.city} />
                                  <DetailField label="Localidade" value={operation.locality} />
                                </div>

                                <div style={{ display: "grid", gap: "14px", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))" }}>
                                  <DetailField label="Saída do ponto de encontro" value={operation.departure_meeting_point} />
                                  <DetailField label="Montagem da operação" value={operation.operation_assembly} />
                                  <DetailField label="Primeira abordagem" value={operation.first_approach} />
                                  <DetailField label="Encerramento" value={operation.closing} />
                                </div>

                                <div style={{ display: "grid", gap: "14px", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))" }}>
                                  <DetailField label="Abordados" value={operation.approach} />
                                  <DetailField label="Recondutores" value={operation.reconductor} />
                                  <DetailField label="Recusas" value={operation.refusal} />
                                  <DetailField label="Celebridades / Autoridades" value={operation.celebrities_authorities} />
                                  <DetailField label="Resultado 0,00 a 0,04" value={operation.four_ml} />
                                  <DetailField label="Resultado 0,05 a 0,33" value={operation.thirtythree_ml} />
                                  <DetailField label="Resultado acima de 0,33" value={operation.thirtyfour_ml} />
                                  <DetailField label="Testes passivos realizados" value={operation.passive_tests_performed} />
                                  <DetailField label="CNH recolhidas" value={operation.cnh_collected} />
                                  <DetailField label="Multados" value={operation.fined} />
                                  <DetailField label="Rebocados" value={operation.towed} />
                                  <DetailField label="Deliberações de remoção" value={operation.removal_resolutions} />
                                  <DetailField label="Prisões por outros meios de prova" value={operation.arrests_means_evidence} />
                                  <DetailField label="Art. 307" value={operation.art307} />
                                  <DetailField label="Ocorrências criminais" value={operation.criminal_occurrences} />
                                  <DetailField label="Dirigir com CNH cassada" value={operation.driving_canceled_license} />
                                </div>

                                <div style={{ display: "grid", gap: "14px", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))" }}>
                                  <DetailField label="Alterações de material" value={operation.changes_material} />
                                  <DetailField label="Deliberações dos veículos" value={operation.vehicle_resolutions} />
                                  <DetailField label="Testes administrativos" value={operation.administrative_tests} />
                                </div>

                                <div style={{ display: "grid", gap: "10px" }}>
                                  <h4 style={{ margin: 0, color: "var(--primary-strong)" }}>Autos / Infrações</h4>
                                  {(operation.fines || []).length ? (
                                    <div className="table-wrap" style={{ paddingTop: 0 }}>
                                      <table>
                                        <thead>
                                          <tr>
                                            <th>Código</th>
                                            <th>Quantidade</th>
                                          </tr>
                                        </thead>
                                        <tbody>
                                          {operation.fines.map((fine) => (
                                            <tr key={fine.source_id}>
                                              <td>{displayValue(fine.art)}</td>
                                              <td>{displayValue(fine.quant)}</td>
                                            </tr>
                                          ))}
                                        </tbody>
                                      </table>
                                    </div>
                                  ) : (
                                    <p style={{ margin: 0 }}>Nenhuma infração detalhada informada.</p>
                                  )}
                                </div>
                              </div>
                            ) : null}
                          </article>
                        );
                      })}
                    </div>
                  </DetailSection>
                </>
              ) : null}
            </div>
          </div>
        </div>
      )}

      {showIncludeModal ? (
        <DecisionModal
          title="Confirmar inclusão deste Relatório de Fiscalização na Estatística?"
          body="Os dados atuais serão registrados como a versão homologada para uso estatístico."
          confirmLabel="Confirmar inclusão"
          onConfirm={handleInclude}
          onClose={() => setShowIncludeModal(false)}
          loading={actionLoading}
        />
      ) : null}

      {showExcludeModal ? (
        <DecisionModal
          title="Não incluir na Estatística"
          body="Informe o motivo da não inclusão deste relatório."
          confirmLabel="Confirmar não inclusão"
          onConfirm={handleExclude}
          onClose={() => setShowExcludeModal(false)}
          loading={actionLoading}
          disableConfirm={!excludeReason.trim()}
          confirmClassName="secondary"
        >
          <label style={{ display: "grid", gap: "6px" }}>
            <span>Motivo da não inclusão</span>
            <textarea
              rows={4}
              value={excludeReason}
              onChange={(event) => setExcludeReason(event.target.value)}
              placeholder="Possível inconsistência no quantitativo informado."
            />
          </label>
        </DecisionModal>
      ) : null}
    </section>
  );
}
