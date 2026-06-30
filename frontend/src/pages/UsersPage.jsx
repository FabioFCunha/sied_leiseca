import { Mail, Save, Trash2 } from "lucide-react";
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

  const load = () => api("/users/").then((data) => setUsers(data.results || data));

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

  const renderUsersTable = (items, emptyMessage) => (
    <table>
      <thead>
        <tr><th>Nome</th><th>CPF</th><th>Telefone</th><th>E-mail</th><th>Ocupação</th><th>Equipe/Setor</th><th>Status</th><th className="actions-heading">Ações</th></tr>
      </thead>
      <tbody>
        {items.map((item) => (
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
                  <button className="secondary" onClick={() => toggleVacation(item)}>
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
        {!items.length && (
          <tr><td colSpan="8" className="empty-cell">{emptyMessage}</td></tr>
        )}
      </tbody>
    </table>
  );

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
          {renderUsersTable(operationalUsers, "Nenhum agente, apoio ou chefe cadastrado.")}
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
          {form.role !== "VISITOR" && (
            <>
              <label>
                Nome completo
                <input placeholder="Digite o nome completo" value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} required />
              </label>
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
              <input
                placeholder="Digite o nome do setor"
                value={form.sector_name || ""}
                onChange={(e) => setForm({ ...form, sector: "", sector_name: e.target.value })}
                required
              />
            </label>
          )}
          {operationalRoles.has(form.role) && (
            <label>
              Equipe
              <select
                value={form.team || ""}
                onChange={(e) => setForm({ ...form, team: e.target.value })}
              >
                <option value="">Sem equipe</option>
                {teams.map((team) => <option key={team.id} value={team.id}>{team.name}</option>)}
              </select>
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
    </section>
  );
}
