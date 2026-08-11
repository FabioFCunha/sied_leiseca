import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import {
  CalendarDays,
  ChevronRight,
  ClipboardList,
  MapPin,
  RefreshCw,
  User,
} from "lucide-react";
import { api } from "../../api/client.js";
import { useAuth } from "../../context/AuthContext.jsx";
import { formatDateBR } from "../../utils/date.js";
import MobileEmptyState from "../../components/mobile/MobileEmptyState.jsx";
import MobileErrorState from "../../components/mobile/MobileErrorState.jsx";
import MobileLoadingState from "../../components/mobile/MobileLoadingState.jsx";
import MobileReportCard from "../../components/mobile/MobileReportCard.jsx";

const STATUS_OPTIONS = [
  { value: "", label: "Todos" },
  { value: "DRAFT", label: "Rascunho" },
  { value: "PENDING_REVIEW", label: "Aguardando" },
  { value: "APPROVED", label: "Aprovado" },
  { value: "RETURNED", label: "Devolvido" },
];

function apiPathFromNext(next) {
  if (!next) return "";
  try {
    const url = new URL(next);
    const pathname = url.pathname.startsWith("/api/")
      ? url.pathname.slice(4)
      : url.pathname;
    return `${pathname}${url.search}`;
  } catch {
    return next;
  }
}

function accessMessageForRole(role) {
  if (role === "USER" || role === "SUPPORT") {
    return "Seu perfil não possui acesso aos Relatórios Técnicos nesta versão do sistema.";
  }
  return "";
}

function agendaLocation(agenda) {
  return (
    agenda.location ||
    agenda.institution_location ||
    agenda.address ||
    agenda.city ||
    ""
  );
}

function PendingReportCard({ agenda }) {
  const location = agendaLocation(agenda);

  return (
    <Link
      to={`/app/relatorios/novo/${agenda.id}`}
      style={{ textDecoration: "none", color: "inherit", display: "block" }}
    >
      <article
        className="mobile-card"
        style={{
          padding: "16px",
          display: "grid",
          gap: "10px",
          border: "1px solid var(--line)",
        }}
      >
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            gap: "12px",
            alignItems: "flex-start",
          }}
        >
          <div style={{ minWidth: 0 }}>
            <span
              style={{
                display: "inline-block",
                fontSize: "11px",
                fontWeight: 800,
                color: "#92400e",
                background: "#fef3c7",
                padding: "4px 8px",
                borderRadius: "999px",
                marginBottom: "8px",
              }}
            >
              PENDENTE
            </span>

            <h3
              style={{
                margin: 0,
                fontSize: "15px",
                lineHeight: 1.35,
                color: "#0f172a",
              }}
            >
              {agenda.service_order_number
                ? `OS ${agenda.service_order_number} - `
                : ""}
              {agenda.title || agenda.action_type || "Relatório técnico"}
            </h3>
          </div>

          <ChevronRight
            size={20}
            color="#94a3b8"
            style={{ flexShrink: 0, marginTop: "4px" }}
          />
        </div>

        <div
          style={{
            display: "grid",
            gap: "6px",
            fontSize: "13px",
            color: "#64748b",
          }}
        >
          {agenda.date && (
            <span style={{ display: "flex", alignItems: "center", gap: "6px" }}>
              <CalendarDays size={15} />
              {formatDateBR(agenda.date)}
            </span>
          )}

          {location && (
            <span style={{ display: "flex", alignItems: "flex-start", gap: "6px" }}>
              <MapPin size={15} style={{ flexShrink: 0, marginTop: "2px" }} />
              {location}
            </span>
          )}

          {agenda.chief_name && (
            <span style={{ display: "flex", alignItems: "center", gap: "6px" }}>
              <User size={15} />
              Chefe: {agenda.chief_name}
            </span>
          )}
        </div>

        <div
          style={{
            marginTop: "2px",
            color: "var(--primary)",
            fontWeight: 800,
            fontSize: "13px",
            display: "flex",
            alignItems: "center",
            gap: "6px",
          }}
        >
          <ClipboardList size={16} />
          Preencher relatório
        </div>
      </article>
    </Link>
  );
}

export default function MobileReportsPage() {
  const { user } = useAuth();
  const [searchParams] = useSearchParams();
  const agendaFilter = searchParams.get("agenda") || "";

  const [activeTab, setActiveTab] = useState("pending");

  const [pendingAgendas, setPendingAgendas] = useState([]);
  const [pendingLoading, setPendingLoading] = useState(false);
  const [pendingError, setPendingError] = useState("");
  const [pendingDateFilter, setPendingDateFilter] = useState("");
  const [pendingChiefFilter, setPendingChiefFilter] = useState("");
  const [pendingChiefQuery, setPendingChiefQuery] = useState("");

  const [reports, setReports] = useState([]);
  const [statusFilter, setStatusFilter] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [loading, setLoading] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState("");
  const [nextPageUrl, setNextPageUrl] = useState("");

  const requestSeq = useRef(0);
  const abortControllerRef = useRef(null);
  const pendingAbortControllerRef = useRef(null);

  const roleAccessMessage = accessMessageForRole(user?.role);

  const queryKey = useMemo(
    () => JSON.stringify({ statusFilter, dateFrom, dateTo, agendaFilter }),
    [statusFilter, dateFrom, dateTo, agendaFilter]
  );

  const filteredPendingAgendas = useMemo(() => {
    if (!pendingDateFilter) return pendingAgendas;
    return pendingAgendas.filter(
      (agenda) => String(agenda.date || "") === pendingDateFilter
    );
  }, [pendingAgendas, pendingDateFilter]);

  const buildPendingPath = () => {
    const params = new URLSearchParams({
      page_size: "50",
      reportable: "true",
      pending_report: "true",
    });

    if (pendingChiefQuery.trim()) {
      params.set("chief", pendingChiefQuery.trim());
    }

    return `/agendas/?${params.toString()}`;
  };

  const fetchPendingAgendas = async () => {
    if (roleAccessMessage) return;

    if (pendingAbortControllerRef.current) {
      pendingAbortControllerRef.current.abort();
    }

    pendingAbortControllerRef.current = new AbortController();

    setPendingLoading(true);
    setPendingError("");

    try {
      const response = await api(buildPendingPath(), {
        signal: pendingAbortControllerRef.current.signal,
        redirectOnUnauthorized: false,
      });

      const results = Array.isArray(response?.results)
        ? response.results
        : Array.isArray(response)
          ? response
          : [];

      setPendingAgendas(results);
    } catch (err) {
      if (err.name === "AbortError") return;

      const message = String(err.message || "");

      if (
        message.includes("permissao") ||
        message.includes("permiss") ||
        message.includes("403")
      ) {
        setPendingError(
          "Você não possui permissão para consultar as pendências de relatório."
        );
      } else if (message.includes("Sessao") || message.includes("401")) {
        setPendingError("Sessão expirada. Entre novamente.");
      } else {
        setPendingError(
          message || "Não foi possível carregar os relatórios pendentes."
        );
      }
    } finally {
      setPendingLoading(false);
    }
  };

  const buildListPath = () => {
    const params = new URLSearchParams({ page_size: "10" });

    if (statusFilter) params.set("status", statusFilter);
    if (dateFrom) params.set("date_from", dateFrom);
    if (dateTo) params.set("date_to", dateTo);

    if (agendaFilter && /^\d+$/.test(agendaFilter)) {
      params.set("protocol", agendaFilter);
    }

    return `/education-reports/?${params.toString()}`;
  };

  const fetchReports = async ({ loadMore = false } = {}) => {
    if (roleAccessMessage) {
      setReports([]);
      setNextPageUrl("");
      setError("");
      setLoading(false);
      setLoadingMore(false);
      return;
    }

    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    abortControllerRef.current = new AbortController();
    const signal = abortControllerRef.current.signal;

    const seq = requestSeq.current + 1;
    requestSeq.current = seq;

    if (loadMore) {
      setLoadingMore(true);
    } else {
      setLoading(true);
      setError("");
    }

    try {
      const path = loadMore
        ? apiPathFromNext(nextPageUrl)
        : buildListPath();

      const response = await api(path, {
        signal,
        redirectOnUnauthorized: false,
      });

      if (seq !== requestSeq.current) return;

      const results = Array.isArray(response?.results)
        ? response.results
        : Array.isArray(response)
          ? response
          : [];

      setReports((current) =>
        loadMore ? [...current, ...results] : results
      );

      setNextPageUrl(response?.next || "");
    } catch (err) {
      if (err.name === "AbortError" || seq !== requestSeq.current) return;

      const message = String(err.message || "");

      if (
        message.includes("permissao") ||
        message.includes("permiss") ||
        message.includes("403")
      ) {
        setError(
          "Você não possui permissão para consultar Relatórios Técnicos."
        );
      } else if (message.includes("Sessao") || message.includes("401")) {
        setError(
          "Sessão expirada. Entre novamente para consultar Relatórios Técnicos."
        );
      } else {
        setError(
          message || "Não foi possível carregar os Relatórios Técnicos."
        );
      }
    } finally {
      if (seq === requestSeq.current) {
        setLoading(false);
        setLoadingMore(false);
      }
    }
  };

  useEffect(() => {
    fetchPendingAgendas();

    return () => {
      if (pendingAbortControllerRef.current) {
        pendingAbortControllerRef.current.abort();
      }
    };
  }, [pendingChiefQuery, roleAccessMessage]);

  useEffect(() => {
    if (activeTab !== "history") return;

    fetchReports();

    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, [queryKey, roleAccessMessage, activeTab]);

  const clearHistoryFilters = () => {
    setStatusFilter("");
    setDateFrom("");
    setDateTo("");
  };

  const clearPendingFilters = () => {
    setPendingDateFilter("");
    setPendingChiefFilter("");
    setPendingChiefQuery("");
  };

  if (roleAccessMessage) {
    return (
      <div className="mobile-alert">
        <p>{roleAccessMessage}</p>
        <Link
          to="/app/inicio"
          className="mobile-btn mobile-btn-primary"
          style={{ textDecoration: "none" }}
        >
          Voltar ao início
        </Link>
      </div>
    );
  }

  return (
    <div className="mobile-reports-page">
      <div className="mobile-reports-header">
        <div>
          <h2>Relatórios Técnicos</h2>
          <p>
            {activeTab === "pending"
              ? "Atividades aguardando preenchimento"
              : "Consulta de relatórios registrados"}
          </p>
        </div>

        <button
          type="button"
          onClick={() =>
            activeTab === "pending"
              ? fetchPendingAgendas()
              : fetchReports()
          }
          disabled={activeTab === "pending" ? pendingLoading : loading}
          aria-label="Atualizar relatórios"
          className="mobile-icon-btn"
        >
          <RefreshCw
            size={20}
            className={
              activeTab === "pending"
                ? pendingLoading
                  ? "animate-spin"
                  : ""
                : loading
                  ? "animate-spin"
                  : ""
            }
          />
        </button>
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          gap: "8px",
          marginBottom: "16px",
        }}
      >
        <button
          type="button"
          className={
            activeTab === "pending"
              ? "mobile-btn mobile-btn-primary"
              : "mobile-btn mobile-btn-outline"
          }
          onClick={() => setActiveTab("pending")}
        >
          Pendentes ({pendingAgendas.length})
        </button>

        <button
          type="button"
          className={
            activeTab === "history"
              ? "mobile-btn mobile-btn-primary"
              : "mobile-btn mobile-btn-outline"
          }
          onClick={() => setActiveTab("history")}
        >
          Consultar relatórios
        </button>
      </div>

      {activeTab === "pending" ? (
        <>
          <div className="mobile-report-filters">
            <label>
              <span>Data</span>
              <input
                type="date"
                value={pendingDateFilter}
                onChange={(event) =>
                  setPendingDateFilter(event.target.value)
                }
              />
            </label>

            <label>
              <span>Chefe</span>
              <div style={{ display: "flex", gap: "8px" }}>
                <input
                  type="text"
                  value={pendingChiefFilter}
                  placeholder="Buscar chefe..."
                  onChange={(event) =>
                    setPendingChiefFilter(event.target.value)
                  }
                  onKeyDown={(event) => {
                    if (event.key === "Enter") {
                      setPendingChiefQuery(pendingChiefFilter);
                    }
                  }}
                  style={{ flex: 1 }}
                />

                <button
                  type="button"
                  className="mobile-btn mobile-btn-outline"
                  onClick={() =>
                    setPendingChiefQuery(pendingChiefFilter)
                  }
                  style={{ width: "auto" }}
                >
                  Buscar
                </button>
              </div>
            </label>

            {(pendingDateFilter || pendingChiefQuery) && (
              <button
                type="button"
                className="mobile-btn mobile-btn-outline"
                onClick={clearPendingFilters}
              >
                Limpar filtros
              </button>
            )}
          </div>

          <div
            style={{
              margin: "14px 0",
              fontSize: "13px",
              fontWeight: 800,
              color: "var(--text-soft)",
            }}
          >
            {filteredPendingAgendas.length}{" "}
            {filteredPendingAgendas.length === 1
              ? "relatório pendente"
              : "relatórios pendentes"}
          </div>

          {pendingLoading ? (
            <MobileLoadingState message="Carregando pendências..." />
          ) : pendingError ? (
            <MobileErrorState
              message={pendingError}
              onRetry={fetchPendingAgendas}
            />
          ) : filteredPendingAgendas.length === 0 ? (
            <MobileEmptyState message="Nenhum relatório pendente para os filtros selecionados." />
          ) : (
            <div className="mobile-report-list">
              {filteredPendingAgendas.map((agenda) => (
                <PendingReportCard
                  key={agenda.id}
                  agenda={agenda}
                />
              ))}
            </div>
          )}
        </>
      ) : (
        <>
          <div className="mobile-report-filters">
            <label>
              <span>Status</span>
              <select
                value={statusFilter}
                onChange={(event) =>
                  setStatusFilter(event.target.value)
                }
              >
                {STATUS_OPTIONS.map((option) => (
                  <option
                    key={option.value || "all"}
                    value={option.value}
                  >
                    {option.label}
                  </option>
                ))}
              </select>
            </label>

            <label>
              <span>Data inicial</span>
              <input
                type="date"
                value={dateFrom}
                onChange={(event) => setDateFrom(event.target.value)}
              />
            </label>

            <label>
              <span>Data final</span>
              <input
                type="date"
                value={dateTo}
                onChange={(event) => setDateTo(event.target.value)}
              />
            </label>

            {(statusFilter || dateFrom || dateTo) && (
              <button
                type="button"
                className="mobile-btn mobile-btn-outline"
                onClick={clearHistoryFilters}
              >
                Limpar filtros
              </button>
            )}
          </div>

          {loading ? (
            <MobileLoadingState message="Carregando relatórios..." />
          ) : error ? (
            <MobileErrorState
              message={error}
              onRetry={() => fetchReports()}
            />
          ) : reports.length === 0 ? (
            <MobileEmptyState message="Nenhum Relatório Técnico disponível com os filtros selecionados." />
          ) : (
            <div className="mobile-report-list">
              {reports.map((report) => (
                <MobileReportCard
                  key={report.id}
                  report={report}
                />
              ))}

              {nextPageUrl && (
                <button
                  type="button"
                  className="mobile-btn mobile-btn-outline"
                  disabled={loadingMore}
                  onClick={() => fetchReports({ loadMore: true })}
                >
                  {loadingMore ? "Carregando..." : "Carregar mais"}
                </button>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}
