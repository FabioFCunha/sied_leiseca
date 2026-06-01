import { Save } from "lucide-react";
import { useEffect, useState } from "react";
import { api } from "../api/client.js";

const empty = { full_name: "", cpf: "", email: "", phone: "", role: "USER", sector: "", is_active: true };

const roleLabel = {
  ADMIN: "Administrador",
  SUPERVISOR: "Chefe",
  USER: "Agente",
};

export default function UsersPage() {
  const [users, setUsers] = useState([]);
  const [sectors, setSectors] = useState([]);
  const [form, setForm] = useState(empty);
  const [editing, setEditing] = useState(null);
  const [message, setMessage] = useState("");
  const [passwordLink, setPasswordLink] = useState("");

  const load = () => api("/users/").then((data) => setUsers(data.results || data));

  useEffect(() => {
    load();
    api("/sectors/").then((data) => setSectors(data.results || data));
  }, []);

  const submit = async (event) => {
    event.preventDefault();
    const payload = { ...form };
    try {
      const saved = editing
        ? await api(`/users/${editing}/`, { method: "PUT", body: JSON.stringify(payload) })
        : await api("/users/", { method: "POST", body: JSON.stringify(payload) });
      setPasswordLink(saved.password_setup_link || "");
      setForm(empty);
      setEditing(null);
      setMessage("Usuário salvo. Envie o link de senha para o e-mail do usuário.");
      load();
    } catch (err) {
      setMessage(err.message);
    }
  };

  const edit = (user) => {
    setEditing(user.id);
    setPasswordLink(user.password_setup_link || "");
    setForm({ ...user, cpf: user.cpf || "", sector: user.sector || "", is_active: user.is_active });
  };

  return (
    <section className="page two-column">
      <div className="main-column">
        <div className="page-title">
          <div>
            <h1>Usuários</h1>
            <p>Gerencie administradores, chefes e agentes do sistema.</p>
          </div>
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr><th>Nome</th><th>CPF</th><th>Telefone</th><th>E-mail</th><th>Ocupação</th><th>Equipe</th><th></th></tr>
            </thead>
            <tbody>
              {users.map((item) => (
                <tr key={item.id}>
                  <td>{item.full_name}</td>
                  <td>{item.cpf || "-"}</td>
                  <td>{item.phone || "-"}</td>
                  <td>{item.email}</td>
                  <td>{roleLabel[item.role] || item.role}</td>
                  <td>{item.sector_name}</td>
                  <td><button className="secondary" onClick={() => edit(item)}>Editar</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
      <aside className="side-panel">
        <h2>{editing ? "Editar usuário" : "Novo usuário"}</h2>
        <form className="stack-form" onSubmit={submit}>
          <input placeholder="Nome completo" value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} required />
          <input placeholder="CPF" value={form.cpf || ""} onChange={(e) => setForm({ ...form, cpf: e.target.value })} required />
          <input placeholder="Telefone" value={form.phone || ""} onChange={(e) => setForm({ ...form, phone: e.target.value })} />
          <input placeholder="E-mail" type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} required />
          <select value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })}>
            <option value="USER">Agente</option>
            <option value="SUPERVISOR">Chefe</option>
            <option value="ADMIN">Administrador</option>
          </select>
          <select value={form.sector || ""} onChange={(e) => setForm({ ...form, sector: e.target.value })}>
            <option value="">Sem equipe</option>
            {sectors.map((sector) => <option key={sector.id} value={sector.id}>{sector.name}</option>)}
          </select>
          <label className="checkbox"><input type="checkbox" checked={form.is_active} onChange={(e) => setForm({ ...form, is_active: e.target.checked })} /> Usuário ativo</label>
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
