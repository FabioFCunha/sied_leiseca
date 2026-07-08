import { Mail, Save, Trash2, X } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { api } from "../api/client.js";
import { useAuth } from "../context/AuthContext.jsx";
import { roleLabel } from "../utils/permissions.js";

const empty = { full_name: "", cpf: "", email: "", phone: "", role: "USER", team: "", sector: "", sector_name: "", is_active: true, is_on_vacation: false, vacation_start: "", vacation_end: "" };

const adminRoles = new Set(["ADMIN", "MANAGER"]);
const visitorRoles = new Set(["VISITOR"]);
const operationalRoles = new Set(["USER", "SUPPORT", "SUPERVISOR"]);

function formatPhone(value) {
  const digits = String(value || "").replace(/\D/g, "").slice(0, 11);
  if (digits.length <= 10) {
    return digits
      .replace(/^(\d{2})(\d)/, "($1) $2")
      .replace(/(\d{4})(\d)/, "$1-$2");
  }
  return digits
    .replace(/^(\d{2})(\d)/, "($1) $2")
    .replace(/(\d{5})(\d)/, "$1-$2");
}

function isValidEmail(value) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(String(value || "").trim());
}

function normalizeSectorName(value) {
  return String(value || "").trim().replace(/\s+/g, " ");
}
function uniqueUppercaseTeams(rows) {
  const seen = new Set();
  return rows
    .map((team) => ({ ...team, name: String(team.name || "").trim().toUpperCase() }))
    .filter((team) => {
      if (!team.name || seen.has(team.name)) return false;
      seen.add(team.name);
      return true;
    })
    .sort((a, b) => a.name.localeCompare(b.name, "pt-BR"));
}

export default function UsersPage() {
  const { user: currentUser } = useAuth();
  const [users, setUsers] = useState([]);
  const [sectors, setSectors] = useState([]);
  const [teams, setTeams] = useState([]);
  const [form, setForm] = useState(empty);
  const [editing, setEditing] = useState(null);
  const [message, setMessage] = useState("");
  const [passwordLink, setPasswordLink] = useState("");
  const [transferModal, setTransferModal] = useState({ open: false, user: null, newTeam: "", date: "" });
  const [opFilters, setOpFilters] = useState({ name: "", cpf: "", phone: "", email: "", role: "", team: "", status: "" });

  const load = () => api("/users/?page_size=1000").then((data) => setUsers(data.results || data));

  const adminUsers = useMemo(() => users.filter((user) => adminRoles.has(user.role)), [users]);
  const visitorUsers = useMemo(() => users.filter((user) => visitorRoles.has(user.role)), [users]);
  const operationalUsers = useMemo(() => users.filter((user) => !adminRoles.has(user.role) && !visitorRoles.has(user.role)), [users]);

  useEffect(() => {
    load().catch((err) => setMessage(err.message));
    api("/sectors/").then((data) => setSectors(data.results || data)).catch((err) => setMessage(err.message));
    api("/teams/?page_size=1000").then((data) => setTeams(uniqueUppercaseTeams(data.results || data))).catch((err) => setMessage(err.message));
  }, []);

  const resolveSector = async (name) => {
    const normalizedName = normalizeSectorName(name);
    if (!normalizedName) {
      return "";
    }
    const existing = sectors.find((sector) => sector.name?.trim().toLowerCase() === normalizedName.toLowerCase());
    if (existing) {
      return existing.id;
    }
    const created = await api("/sectors/", {
      method: "POST",
      body: JSON.stringify({ name: normalizedName, description: "", is_active: true }),
    });
    setSectors((current) => [...current, created]);
    return created.id;
  };

  const submit = async (event) => {
    event.preventDefault();
    const phoneDigits = String(form.phone || "").replace(/\D/g, "");
    if (phoneDigits && (phoneDigits.length < 10 || phoneDigits.length > 11)) {
      setMessage("Informe um telefone válido com DDD.");
      return;
    }
    const sectorName = normalizeSectorName(form.sector_name);
    if (form.role === "VISITOR" && !sectorName) {
      setMessage("Informe o nome do setor do visitante.");
      return;
    }
    if (!isValidEmail(form.email)) {
      setMessage("Informe um e-mail válido.");
      return;
    }
    const isEditing = Boolean(editing);
    try {
      const sectorId = form.role === "VISITOR" ? await resolveSector(sectorName) : "";
      const payload = {
        full_name: form.role === "VISITOR" ? (form.full_name || `Visitante - ${sectorName || form.email}`) : form.full_name,
        cpf: form.role === "VISITOR" ? "" : form.cpf,
        email: form.email.trim().toLowerCase(),
        phone: form.role === "VISITOR" ? "" : phoneDigits,
        role: form.role,
        is_active: form.is_active,
        is_on_vacation: operationalRoles.has(form.role) ? form.is_on_vacation : false,
        vacation_start: (operationalRoles.has(form.role) && form.is_on_vacation && form.vacation_start) ? form.vacation_start : null,
        vacation_end: (operationalRoles.has(form.role) && form.is_on_vacation && form.vacation_end) ? form.vacation_end : null,
      };
      if (form.role === "VISITOR") {
        payload.sector = sectorId;
      }
      if (operationalRoles.has(form.role)) {
        payload.team = form.team || null;
      }
      const saved = isEditing
        ? await api(`/users/${editing}/`, { method: "PUT", body: JSON.stringify(payload) })
        : await api("/users/", { method: "POST", body: JSON.stringify(payload) });
      setPasswordLink(saved.password_setup_link || "");
      setForm(empty);
      setEditing(null);
      setMessage(isEditing ? "Usuário salvo." : (saved.password_setup_email_sent ? "Usuário salvo. Link de senha enviado por e-mail." : `Usuário salvo. Não foi possível enviar o e-mail; copie o link de senha manualmente.${saved.password_setup_email_error ? ` Erro: ${saved.password_setup_email_error}` : ""}`));
      load();
    } catch (err) {
      setMessage(err.message);
    }
  };

  const edit = (user) => {
    setEditing(user.id);
    setPasswordLink(user.password_setup_link || "");
    setForm({ ...user, cpf: user.cpf || "", team: user.team_id || "", sector: user.sector || "", sector_name: user.sector_name || "", is_active: user.is_active, is_on_vacation: user.is_on_vacation || false, vacation_start: user.vacation_start || "", vacation_end: user.vacation_end || "" });
  };

  const remove = async (user) => {
    if (user.id === currentUser?.id) {
      setMessage("Você não pode excluir o próprio usuário conectado.");
      return;
    }
    const label = user.full_name || user.email;
    if (!window.confirm(`Excluir o usuário ${label}? Esta ação apagará também agendas, relatórios, históricos e pesquisas vinculados a ele. Esta ação não pode ser desfeita.`)) {
      return;
    }
    try {
      await api(`/users/${user.id}/`, { method: "DELETE" });
      if (editing === user.id) {
        setEditing(null);
        setForm(empty);
        setPasswordLink("");
      }
      setMessage("Usuário excluído.");
      load();
    } catch (err) {
      setMessage(err.message);
    }
  };

  const sendPasswordLink = async (user) => {
    try {
      const data = await api(`/users/${user.id}/send-password-link/`, { method: "POST" });
      setPasswordLink(data.password_setup_link || "");
      setMessage(data.detail);
    } catch (err) {
      setMessage(err.message);
    }
  };

  const toggleVacation = async (user) => {
    try {
      const payload = {
        full_name: user.full_name,
        cpf: user.cpf || "",
        email: user.email,
        phone: user.phone ? String(user.phone).replace(/\D/g, "") : "",
        role: user.role,
        is_active: user.is_active,
        is_on_vacation: !user.is_on_vacation,
        vacation_start: null,
        vacation_end: null,
      };
      if (user.team_id) {
        payload.team = user.team_id;
      }
      await api(`/users/${user.id}/`, {
        method: "PUT",
        body: JSON.stringify(payload),
      });
      setMessage(`Férias de ${user.full_name || user.email} atualizadas.`);
      load();
    } catch (err) {
      setMessage(err.message);
    }
  };

  const renderTransferModal = () => {
    if (!transferModal.open || !transferModal.user) return null;
    return (
      <div className="modal-overlay">
        <div className="modal">
          <div className="modal-header">
            <h3>Transferir {transferModal.user.full_name || transferModal.user.email}</h3>
            <button className="icon-button" onClick={() => setTransferModal({ open: false, user: null, newTeam: "", date: "" })}><X size={20} /></button>
          </div>
          <div className="modal-body">
            <p style={{marginBottom: "10px", fontSize: "14px"}}>Selecione a nova equipe e a data de início. O histórico na equipe antiga será preservado para escalas anteriores à data.</p>
            <label style={{display: "flex", flexDirection: "column", gap: "5px", marginBottom: "10px"}}>
              Nova Equipe
              <select value={transferModal.newTeam} onChange={e => setTransferModal({ ...transferModal, newTeam: e.target.value })}>
                <option value="">Selecione...</option>
                {teams.filter(t => String(t.id) !== String(transferModal.user.team_id)).map(t => (
                  <option key={t.id} value={t.id}>{t.name}</option>
                ))}
              </select>
            </label>
            <label style={{display: "flex", flexDirection: "column", gap: "5px", marginBottom: "10px"}}>
              A partir de qual data?
              <input type="date" value={transferModal.date} onChange={e => setTransferModal({ ...transferModal, date: e.target.value })} />
            </label>
          </div>
          <div className="modal-footer">
            <button className="secondary" onClick={() => setTransferModal({ open: false, user: null, newTeam: "", date: "" })}>Cancelar</button>
            <button 
              className="primary" 
              onClick={async () => {
                if (!transferModal.newTeam || !transferModal.date) {
                  setMessage("Preencha a nova equipe e a data.");
                  return;
                }
                try {
                  await api(`/users/${transferModal.user.id}/transfer/`, {
                    method: "POST",
                    body: JSON.stringify({ new_team: transferModal.newTeam, effective_date: transferModal.date })
                  });
                  setMessage("Transferência realizada com sucesso.");
                  setTransferModal({ open: false, user: null, newTeam: "", date: "" });
                  load();
                } catch(err) {
                  setMessage(err.message);
                }
              }}
            >
              Transferir
            </button>
          </div>
        </div>
      </div>
    );
  };

  const renderUsersTable = (items, emptyMessage, filters = null, setFilters = null) => {
    const filteredItems = items.filter((item) => {
      if (!filters) return true;
      if (filters.name && !item.full_name?.toLowerCase().includes(filters.name.toLowerCase())) return false;
      if (filters.cpf && !item.cpf?.toLowerCase().includes(filters.cpf.toLowerCase())) return false;
      if (filters.phone && !item.phone?.toLowerCase().includes(filters.phone.toLowerCase())) return false;
      if (filters.email && !item.email?.toLowerCase().includes(filters.email.toLowerCase())) return false;
      if (filters.role && !(roleLabel[item.role] || item.role).toLowerCase().includes(filters.role.toLowerCase())) return false;
      const teamLabel = item.role === "VISITOR" ? (item.sector_name || "-") : String(item.team_name || item.sector_name || "-").toUpperCase();
      if (filters.team && !teamLabel.toLowerCase().includes(filters.team.toLowerCase())) return false;
      const statusLabel = item.is_on_vacation ? "férias" : (item.is_active ? "ativo" : "inativo");
      if (filters.status && !statusLabel.toLowerCase().includes(filters.status.toLowerCase())) return false;
      return true;
    });

    const filterStyle = { display: "block", width: "100%", padding: "4px", marginTop: "4px", fontSize: "12px", fontWeight: "normal", borderRadius: "4px", border: "1px solid var(--border-color, #ccc)", boxSizing: "border-box", backgroundColor: "var(--bg-color, #fff)", color: "inherit" };

    const getUniqueValues = (keyFn) => {
      const values = items.map(keyFn).filter(Boolean);
      return [...new Set(values)].sort();
    };

    const uniqueRoles = getUniqueValues(item => roleLabel[item.role] || item.role);
    const uniqueTeams = getUniqueValues(item => item.role === "VISITOR" ? (item.sector_name || "-") : String(item.team_name || item.sector_name || "-").toUpperCase());
    const uniqueStatuses = ["Ativo", "Inativo", "Férias"];

    return (
      <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
        <div style={{ overflowX: "auto" }}>
          <table>
            <thead>
              <tr>
                <th style={{ verticalAlign: "top" }}>Nome {filters && <input type="text" placeholder="Filtrar..." value={filters.name} onChange={(e) => setFilters({...filters, name: e.target.value})} style={filterStyle} />}</th>
                <th style={{ verticalAlign: "top" }}>CPF {filters && <input type="text" placeholder="Filtrar..." value={filters.cpf} onChange={(e) => setFilters({...filters, cpf: e.target.value})} style={filterStyle} />}</th>
                <th style={{ verticalAlign: "top" }}>Telefone {filters && <input type="text" placeholder="Filtrar..." value={filters.phone} onChange={(e) => setFilters({...filters, phone: e.target.value})} style={filterStyle} />}</th>
                <th style={{ verticalAlign: "top" }}>E-mail {filters && <input type="text" placeholder="Filtrar..." value={filters.email} onChange={(e) => setFilters({...filters, email: e.target.value})} style={filterStyle} />}</th>
                <th style={{ verticalAlign: "top" }}>
                  Ocupação 
                  {filters && (
                    <select value={filters.role} onChange={(e) => setFilters({...filters, role: e.target.value})} style={filterStyle}>
                      <option value="">Todas</option>
                      {uniqueRoles.map(role => <option key={role} value={role}>{role}</option>)}
                    </select>
                  )}
                </th>
                <th style={{ verticalAlign: "top" }}>
                  Equipe/Setor 
                  {filters && (
                    <select value={filters.team} onChange={(e) => setFilters({...filters, team: e.target.value})} style={filterStyle}>
                      <option value="">Todas</option>
                      {uniqueTeams.map(team => <option key={team} value={team}>{team}</option>)}
                    </select>
                  )}
                </th>
                <th style={{ verticalAlign: "top" }}>
                  Status 
                  {filters && (
                    <select value={filters.status} onChange={(e) => setFilters({...filters, status: e.target.value})} style={filterStyle}>
                      <option value="">Todos</option>
                      {uniqueStatuses.map(status => <option key={status} value={status}>{status}</option>)}
                    </select>
                  )}
                </th>
                <th className="actions-heading" style={{ verticalAlign: "top" }}>Ações</th>
              </tr>
            </thead>
            <tbody>
              {filteredItems.map((item) => (
                <tr key={item.id}>
                  <td>{item.full_name}</td>
                  <td>{item.cpf || "-"}</td>
                  <td>{item.phone || "-"}</td>
                  <td>{item.email}</td>
                  <td>{roleLabel[item.role] || item.role}</td>
                  <td>{item.role === "VISITOR" ? (item.sector_name || "-") : String(item.team_name || item.sector_name || "-").toUpperCase()}</td>
                  <td>{item.is_on_vacation ? <span className="badge warning">Férias</span> : <span className={`badge ${item.is_active ? "success" : "neutral"}`}>{item.is_active ? "Ativo" : "Inativo"}</span>}</td>
                  <td>
                    <div className="row-actions">
                      <button className="secondary" onClick={() => edit(item)}>Editar</button>
                      {operationalRoles.has(item.role) && (
                        <button className="secondary" onClick={() => setTransferModal({ open: true, user: item, newTeam: "", date: "" })}>
                          Transferir
                        </button>
                      )}
                      {operationalRoles.has(item.role) && (
                        <button className="secondary" onClick={() => {
                          if (item.is_on_vacation) {
                            toggleVacation(item);
                          } else {
                            setEditing(item.id);
                            setPasswordLink(item.password_setup_link || "");
                            setForm({ ...item, cpf: item.cpf || "", team: item.team_id || "", sector: item.sector || "", sector_name: item.sector_name || "", is_active: item.is_active, is_on_vacation: true, vacation_start: item.vacation_start || "", vacation_end: item.vacation_end || "" });
                            setMessage("Por favor, informe as datas de férias no formulário ao lado e salve.");
                          }
                        }}>
                          {item.is_on_vacation ? "Retirar Férias" : "Férias"}
                        </button>
                      )}
                      <button className="icon-button" onClick={() => sendPasswordLink(item)} aria-label={`Enviar link para ${item.full_name || item.email}`} title="Enviar link de senha">
                        <Mail size={18} />
                      </button>
                      <button className="icon-button danger" onClick={() => remove(item)} disabled={item.id === currentUser?.id} aria-label={`Excluir ${item.full_name || item.email}`} title={item.id === currentUser?.id ? "Você não pode excluir seu próprio usuário" : "Excluir usuário"}>
                        <Trash2 size={18} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
              {!filteredItems.length && (
                <tr><td colSpan="8" className="empty-cell">{emptyMessage}</td></tr>
              )}
            </tbody>
          </table>
        </div>
        {filters && (
          <div style={{ fontWeight: "600", fontSize: "14px", color: "var(--text-soft, #555)", textAlign: "right" }}>
            Total de valores: {filteredItems.length}
          </div>
        )}
      </div>
    );
  };

  return (
    <section className="page two-column">
      <div className="main-column">
        <div className="page-title">
          <div>
            <h1>Usuários</h1>
            <p>Gerencie Administração, gestores, chefes e agentes do sistema.</p>
          </div>
        </div>
        <div className="table-wrap users-table-wrap">
          <h2>Administração e gestores</h2>
          {renderUsersTable(adminUsers, "Nenhum usuário de Administração ou gestor cadastrado.")}
        </div>
        <div className="table-wrap users-table-wrap">
          <h2>Usuários operacionais</h2>
          {renderUsersTable(operationalUsers, "Nenhum agente, apoio ou chefe cadastrado.", opFilters, setOpFilters)}
        </div>
        <div className="table-wrap users-table-wrap">
          <h2>Visitantes</h2>
          {renderUsersTable(visitorUsers, "Nenhum visitante cadastrado.")}
        </div>
      </div>
      <aside className="side-panel">
        <h2>{editing ? "Editar usuário" : "Novo usuário"}</h2>
        <form className="stack-form" onSubmit={submit}>
          <label>
            Perfil
            <select value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value, team: "", sector: "", sector_name: "" })}>
              <option value="USER">Agente</option>
              <option value="SUPPORT">Apoio</option>
              <option value="SUPERVISOR">Chefe</option>
              <option value="MANAGER">Gestor</option>
              <option value="VISITOR">Visitante</option>
              <option value="ADMIN">Administração</option>
            </select>
          </label>
          <label>
            Nome completo
            <input placeholder="Digite o nome completo" value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} required />
          </label>
          {form.role !== "VISITOR" && (
            <>
              <label>
                CPF
                <input placeholder="Digite o CPF" value={form.cpf || ""} onChange={(e) => setForm({ ...form, cpf: e.target.value })} required />
              </label>
              <label>
                Telefone
                <input
                  placeholder="Digite o telefone"
                  value={formatPhone(form.phone)}
                  onChange={(e) => setForm({ ...form, phone: formatPhone(e.target.value) })}
                  inputMode="numeric"
                  autoComplete="tel"
                  maxLength="15"
                  pattern="\(\d{2}\) \d{4,5}-\d{4}"
                  title="Informe um telefone com DDD. Exemplo: (21) 99999-9999"
                />
              </label>
            </>
          )}
          <label>
            E-mail
            <input
              placeholder="Digite o e-mail"
              type="email"
              value={form.email}
              onChange={(e) => setForm({ ...form, email: e.target.value })}
              autoComplete="email"
              inputMode="email"
              pattern="[^\s@]+@[^\s@]+\.[^\s@]{2,}"
              title="Informe um e-mail válido. Exemplo: nome@dominio.com"
              required
            />
          </label>
          {form.role === "VISITOR" && (
            <label>
              Nome do setor
              <select
                value={form.sector_name || ""}
                onChange={(e) => setForm({ ...form, sector: "", sector_name: e.target.value })}
                required
              >
                <option value="" disabled>Selecione o setor</option>
                <option value="Subsecretaria">Subsecretaria</option>
                <option value="OLS/CooAdm">OLS/CooAdm</option>
                <option value="ASCOM">ASCOM</option>
              </select>
            </label>
          )}
          {operationalRoles.has(form.role) && (
            <label>
              Equipe
              {editing ? (
                <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
                  <select
                    value={form.team || ""}
                    onChange={(e) => setForm({ ...form, team: e.target.value })}
                    style={{ flex: 1 }}
                    title="Altere aqui apenas para correções de cadastro."
                  >
                    <option value="">Sem equipe</option>
                    {teams.map((team) => <option key={team.id} value={team.id}>{team.name}</option>)}
                  </select>
                  <button 
                    type="button" 
                    className="secondary" 
                    onClick={() => setTransferModal({ open: true, user: form, newTeam: "", date: "" })}
                    style={{ padding: "8px 12px", whiteSpace: "nowrap" }}
                  >
                    Transferir
                  </button>
                </div>
              ) : (
                <select
                  value={form.team || ""}
                  onChange={(e) => setForm({ ...form, team: e.target.value })}
                >
                  <option value="">Sem equipe</option>
                  {teams.map((team) => <option key={team.id} value={team.id}>{team.name}</option>)}
                </select>
              )}
              {editing && <small style={{color: "#666", marginTop: "4px"}}>Dica: Use "Transferir" em vez de apenas alterar a equipe, para não perder o histórico das escalas passadas.</small>}
            </label>
          )}
          <label className="checkbox">
            <input type="checkbox" checked={form.is_active} onChange={(e) => setForm({ ...form, is_active: e.target.checked })} />
            Usuário ativo
          </label>
          {operationalRoles.has(form.role) && (
            <>
              <label className="checkbox">
                <input type="checkbox" checked={form.is_on_vacation} onChange={(e) => setForm({ ...form, is_on_vacation: e.target.checked })} />
                Marcar como férias
              </label>
              {form.is_on_vacation && (
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px" }}>
                  <label>
                    Data Início
                    <input type="date" value={form.vacation_start || ""} onChange={e => setForm({ ...form, vacation_start: e.target.value })} required />
                  </label>
                  <label>
                    Data Fim
                    <input type="date" value={form.vacation_end || ""} onChange={e => setForm({ ...form, vacation_end: e.target.value })} required />
                  </label>
                </div>
              )}
            </>
          )}
          {message && <div className="alert">{message}</div>}
          {passwordLink && (
            <div className="copy-box">
              <span>Link para cadastrar senha</span>
              <input value={passwordLink} readOnly />
              <button type="button" className="secondary" onClick={() => navigator.clipboard?.writeText(passwordLink)}>
                Copiar link
              </button>
            </div>
          )}
          <button><Save size={18} /> Salvar</button>
        </form>
      </aside>
      {renderTransferModal()}
    </section>
  );
}
