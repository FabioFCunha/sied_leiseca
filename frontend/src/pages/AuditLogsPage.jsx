import { Eye, Filter, RotateCcw } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { api } from "../api/client.js";

const actionOptions = [
  ["", "Todas as ações"],
  ["LOGIN", "Login"],
  ["CREATE", "Criação"],
  ["UPDATE", "Alteração"],
  ["DELETE", "Exclusão"],
  ["STATUS_CHANGE", "Mudança de status"],
  ["PASSWORD_LINK", "Link de senha"],
  ["SET_PASSWORD", "Definição de senha"],
  ["EMAIL", "Envio de e-mail"],
  ["REPORT_EXPORT", "Exportação de relatório"],
];

const moduleOptions = [
  ["", "Todos os módulos"],
  ["Agendas", "Agendas"],
  ["Usuarios", "Usuários"],
  ["Autenticacao", "Autenticação"],
  ["Relatorios", "Relatórios"],
];

function formatDateTime(value) {
  if (!value) return "-";
  return new Intl.DateTimeFormat("pt-BR", {
    dateStyle: "short",
    timeStyle: "short",
  }).format(new Date(value));
}

function actionTone(action) {
  if (action === "DELETE") return "danger";
  if (action === "CREATE" || action === "LOGIN") return "success";
  if (action === "STATUS_CHANGE" || action === "REPORT_EXPORT") return "warning";
  return "neutral";
}

const initialFilters = {
  q: "",
  action: "",
  module: "",
  user: "",
  date_from: "",
  date_to: "",
};

export default function AuditLogsPage() {
  const [logs, setLogs] = useState([]);
  const [users, setUsers] = useState([]);
  const [filters, setFilters] = useState(initialFilters);
  const [selected, setSelected] = useState(null);
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);

  const query = useMemo(() => {
    const params = new URLSearchParams();
    Object.entries(filters).forEach(([key, value]) => {
      if (value) params.set(key, value);
    });
    return params.toString();
  }, [filters]);

  useEffect(() => {
    api("/users/")
      .then((data) => setUsers(data.results || data))
      .catch((err) => setMessage(err.message));
  }, []);

  useEffect(() => {
    setLoading(true);
    api(`/audit-logs/${query ? `?${query}` : ""}`)
      .then((data) => {
        const rows = data.results || data;
        setLogs(rows);
        setSelected((current) => current || rows[0] || null);
        setMessage("");
      })
      .catch((err) => setMessage(err.message))
      .finally(() => setLoading(false));
  }, [query]);

  const updateFilter = (field, value) => {
    setFilters((current) => ({ ...current, [field]: value }));
  };

  const clearFilters = () => {
    setFilters(initialFilters);
  };

  return (
    <section className="page two-column audit-page">
      <div className="main-column">
        <div className="page-title">
          <div>
            <h1>Auditoria</h1>
            <p>Acompanhe acessos, cadastros, alterações e exportações do sistema.</p>
          </div>
        </div>

        <div className="filters audit-filters">
          <label className="filter-field">
            <span>Buscar</span>
            <input placeholder="Usuário, descrição ou IP" value={filters.q} onChange={(event) => updateFilter("q", event.target.value)} />
          </label>
          <label className="filter-field">
            <span>Ação</span>
            <select value={filters.action} onChange={(event) => updateFilter("action", event.target.value)}>
              {actionOptions.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
            </select>
          </label>
          <label className="filter-field">
            <span>Módulo</span>
            <select value={filters.module} onChange={(event) => updateFilter("module", event.target.value)}>
              {moduleOptions.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
            </select>
          </label>
          <label className="filter-field">
            <span>Usuário</span>
            <select value={filters.user} onChange={(event) => updateFilter("user", event.target.value)}>
              <option value="">Todos os usuários</option>
              {users.map((user) => <option key={user.id} value={user.id}>{user.full_name || user.email}</option>)}
            </select>
          </label>
          <label className="filter-field">
            <span>De</span>
            <input type="date" value={filters.date_from} onChange={(event) => updateFilter("date_from", event.target.value)} />
          </label>
          <label className="filter-field">
            <span>Até</span>
            <input type="date" value={filters.date_to} onChange={(event) => updateFilter("date_to", event.target.value)} />
          </label>
          <div className="audit-filter-actions">
            <button className="secondary" type="button" onClick={clearFilters}><RotateCcw size={17} /> Limpar</button>
          </div>
        </div>

        {message && <div className="alert">{message}</div>}

        <div className="table-wrap audit-table">
          <table>
            <thead>
              <tr>
                <th>Data</th>
                <th>Usuário</th>
                <th>Ação</th>
                <th>Módulo</th>
                <th>Descrição</th>
                <th className="actions-heading">Detalhes</th>
              </tr>
            </thead>
            <tbody>
              {logs.map((log) => (
                <tr key={log.id}>
                  <td>{formatDateTime(log.created_at)}</td>
                  <td>{log.user_name || log.user_email || "-"}</td>
                  <td><span className={`badge ${actionTone(log.action)}`}>{log.action_label}</span></td>
                  <td>{log.module}</td>
                  <td>{log.description}</td>
                  <td>
                    <button className="icon-button" onClick={() => setSelected(log)} aria-label={`Ver log ${log.id}`} title="Ver detalhes">
                      <Eye size={18} />
                    </button>
                  </td>
                </tr>
              ))}
              {!logs.length && (
                <tr>
                  <td colSpan="6" className="empty-cell">{loading ? "Carregando logs..." : "Nenhum log encontrado."}</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      <aside className="side-panel audit-detail">
        <div className="detail-heading">
          <Filter size={18} />
          <h2>Detalhes</h2>
        </div>
        {selected ? (
          <>
            <dl>
              <dt>Data</dt>
              <dd>{formatDateTime(selected.created_at)}</dd>
              <dt>Usuário</dt>
              <dd>{selected.user_name || selected.user_email || "-"}</dd>
              <dt>Ação</dt>
              <dd>{selected.action_label}</dd>
              <dt>Módulo</dt>
              <dd>{selected.module}</dd>
              <dt>IP</dt>
              <dd>{selected.ip_address || "-"}</dd>
              <dt>Descrição</dt>
              <dd>{selected.description}</dd>
            </dl>
            <div className="metadata-box">
              <span>Metadados</span>
              <pre>{JSON.stringify(selected.metadata || {}, null, 2)}</pre>
            </div>
          </>
        ) : (
          <p>Selecione um registro para ver os detalhes.</p>
        )}
      </aside>
    </section>
  );
}
