import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { RefreshCw } from "lucide-react";
import { api } from "../../api/client.js";
import { useAuth } from "../../context/AuthContext.jsx";
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
    const pathname = url.pathname.startsWith("/api/") ? url.pathname.slice(4) : url.pathname;
    return `${pathname}${url.search}`;
  } catch {
    return next;
  }
}

function accessMessageForRole(role) {
  if (role === "USER" || role === "SUPPORT") {
    return "Seu perfil nao possui acesso aos Relatorios Tecnicos nesta versao do sistema.";
  }
  return "";
}

export default function MobileReportsPage() {
  const { user } = useAuth();
  const [searchParams] = useSearchParams();
  const agendaFilter = searchParams.get("agenda") || "";
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

  const roleAccessMessage = accessMessageForRole(user?.role);

  const queryKey = useMemo(
    () => JSON.stringify({ statusFilter, dateFrom, dateTo, agendaFilter }),
    [statusFilter, dateFrom, dateTo, agendaFilter]
  );

  const buildListPath = () => {
    const params = new URLSearchParams({ page_size: "10" });
    if (statusFilter) params.set("status", statusFilter);
    if (dateFrom) params.set("date_from", dateFrom);
    if (dateTo) params.set("date_to", dateTo);
    if (agendaFilter && /^\d+$/.test(agendaFilter)) params.set("protocol", agendaFilter);
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

    if (abortControllerRef.current) abortControllerRef.current.abort();
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
      const path = loadMore ? apiPathFromNext(nextPageUrl) : buildListPath();
      const response = await api(path, { signal, redirectOnUnauthorized: false });
      if (seq !== requestSeq.current) return;

      const results = Array.isArray(response?.results) ? response.results : Array.isArray(response) ? response : [];
      setReports((current) => (loadMore ? [...current, ...results] : results));
      setNextPageUrl(response?.next || "");
    } catch (err) {
      if (err.name === "AbortError" || seq !== requestSeq.current) return;
      const message = String(err.message || "");
      if (message.includes("permissao") || message.includes("permiss") || message.includes("403")) {
        setError("Voce nao possui permissao para consultar Relatorios Tecnicos.");
      } else if (message.includes("Sessao") || message.includes("401")) {
        setError("Sessao expirada. Entre novamente para consultar Relatorios Tecnicos.");
      } else {
        setError(message || "Nao foi possivel carregar os Relatorios Tecnicos.");
      }
    } finally {
      if (seq === requestSeq.current) {
        setLoading(false);
        setLoadingMore(false);
      }
    }
  };

  useEffect(() => {
    fetchReports();
    return () => {
      if (abortControllerRef.current) abortControllerRef.current.abort();
    };
  }, [queryKey, roleAccessMessage]);

  const clearFilters = () => {
    setStatusFilter("");
    setDateFrom("");
    setDateTo("");
  };

  if (roleAccessMessage) {
    return (
      <div className="mobile-alert">
        <p>{roleAccessMessage}</p>
        <Link to="/app/inicio" className="mobile-btn mobile-btn-primary" style={{ textDecoration: "none" }}>
          Voltar ao inicio
        </Link>
      </div>
    );
  }

  return (
    <div className="mobile-reports-page">
      <div className="mobile-reports-header">
        <div>
          <h2>Relatorios Tecnicos</h2>
          <p>Consulta em modo aplicativo</p>
        </div>
        <button
          type="button"
          onClick={() => fetchReports()}
          disabled={loading}
          aria-label="Atualizar relatorios"
          className="mobile-icon-btn"
        >
          <RefreshCw size={20} className={loading ? "animate-spin" : ""} />
        </button>
      </div>

      <div className="mobile-report-filters">
        <label>
          <span>Status</span>
          <select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}>
            {STATUS_OPTIONS.map((option) => (
              <option key={option.value || "all"} value={option.value}>{option.label}</option>
            ))}
          </select>
        </label>
        <label>
          <span>Data inicial</span>
          <input type="date" value={dateFrom} onChange={(event) => setDateFrom(event.target.value)} />
        </label>
        <label>
          <span>Data final</span>
          <input type="date" value={dateTo} onChange={(event) => setDateTo(event.target.value)} />
        </label>
        {(statusFilter || dateFrom || dateTo) && (
          <button type="button" className="mobile-btn mobile-btn-outline" onClick={clearFilters}>
            Limpar filtros
          </button>
        )}
      </div>

      {loading ? (
        <MobileLoadingState message="Carregando relatorios..." />
      ) : error ? (
        <MobileErrorState message={error} onRetry={() => fetchReports()} />
      ) : reports.length === 0 ? (
        <MobileEmptyState message="Nenhum Relatorio Tecnico disponivel com os filtros selecionados." />
      ) : (
        <div className="mobile-report-list">
          {reports.map((report) => (
            <MobileReportCard key={report.id} report={report} />
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
    </div>
  );
}
