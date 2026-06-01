import { Save, Trash2 } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { api } from "../api/client.js";

const lookupTypes = [
  { key: "teams", label: "Equipes", endpoint: "/teams/" },
  { key: "chiefs", label: "Chefes", endpoint: "/chiefs/", hasAddress: true, hasTeam: true, teamLabel: "Equipe" },
  { key: "agents", label: "Agentes", endpoint: "/agents/", hasAddress: true, teamLabel: "Equipe" },
  { key: "supports", label: "Apoios", endpoint: "/supports/", hasAddress: true, hasTeam: true, teamLabel: "Ala" },
  { key: "vehicles", label: "Viaturas", endpoint: "/vehicles/" },
  { key: "kits", label: "Kits", endpoint: "/kits/" },
];

const emptyForm = { name: "", phone: "", team: "", address: "", is_active: true };
const militaryTeams = ["ALFA", "BRAVO", "CHARLIE", "DELTA", "ECHO", "FOX", "GOLF", "HOTEL"];

export default function LookupsPage() {
  const [activeKey, setActiveKey] = useState("teams");
  const [rows, setRows] = useState([]);
  const [form, setForm] = useState(emptyForm);
  const [editing, setEditing] = useState(null);
  const [message, setMessage] = useState("");
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("active");
  const [teams, setTeams] = useState([]);

  const activeType = useMemo(
    () => lookupTypes.find((type) => type.key === activeKey),
    [activeKey]
  );

  const filteredRows = useMemo(() => {
    const term = search.trim().toLowerCase();
    return rows.filter((row) => {
      const matchesStatus =
        statusFilter === "all" ||
        (statusFilter === "active" && row.is_active) ||
        (statusFilter === "inactive" && !row.is_active);
      const matchesSearch = !term || `${row.name} ${row.phone || ""} ${row.address || ""} ${row.team_name || ""}`.toLowerCase().includes(term);
      return matchesStatus && matchesSearch;
    });
  }, [rows, search, statusFilter]);

  const loadRows = () => {
    const includeInactive = statusFilter !== "active" ? "&include_inactive=true" : "";
    api(`${activeType.endpoint}?page_size=1000${includeInactive}`).then((data) => setRows(data.results || data));
  };

  useEffect(() => {
    api("/teams/?page_size=1000").then((data) => setTeams(data.results || data));
  }, []);

  useEffect(() => {
    setForm(emptyForm);
    setEditing(null);
    setSearch("");
    setStatusFilter("active");
    loadRows();
  }, [activeType.endpoint]);

  useEffect(() => {
    loadRows();
  }, [statusFilter]);

  const submit = async (event) => {
    event.preventDefault();
    setMessage("");
    const payload = {
      name: form.name,
      is_active: form.is_active,
    };
    if (activeType.hasPhone) {
      payload.phone = form.phone || "";
    }
    if (activeType.hasAddress) {
      payload.address = form.address || "";
    }
    if (activeType.key === "agents" || activeType.hasTeam) {
      payload.team = form.team || null;
    }

    try {
      if (editing) {
        await api(`${activeType.endpoint}${editing}/`, { method: "PUT", body: JSON.stringify(payload) });
      } else {
        await api(activeType.endpoint, { method: "POST", body: JSON.stringify(payload) });
      }
      setForm(emptyForm);
      setEditing(null);
      setMessage("Cadastro salvo com sucesso.");
      loadRows();
    } catch (err) {
      setMessage(err.message);
    }
  };

  const edit = (row) => {
    setEditing(row.id);
    setForm({
      name: row.name || "",
      phone: row.phone || "",
      team: row.team || "",
      address: row.address || "",
      is_active: row.is_active,
    });
  };

  const remove = async (row) => {
    setMessage("");
    try {
      await api(`${activeType.endpoint}${row.id}/`, { method: "DELETE" });
      setMessage("Cadastro excluÃ­do.");
      loadRows();
    } catch (err) {
      setMessage(err.message);
    }
  };

  return (
    <section className="page two-column">
      <div className="main-column">
        <div className="page-title">
          <div>
            <h1>Cadastros</h1>
            <p>Gerencie listas usadas nos formulÃ¡rios de novas agendas.</p>
          </div>
        </div>

        <div className="lookup-tabs">
          {lookupTypes.map((type) => (
            <button
              key={type.key}
              className={type.key === activeKey ? "active" : ""}
              onClick={() => setActiveKey(type.key)}
            >
              {type.label}
            </button>
          ))}
        </div>

        <div className="table-wrap">
          <div className="table-tools">
            <h2>{activeType.label}</h2>
            <div className="lookup-filters">
              <input placeholder="Buscar cadastro..." value={search} onChange={(event) => setSearch(event.target.value)} />
              <select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}>
                <option value="active">Ativos</option>
                <option value="inactive">Inativos</option>
                <option value="all">Todos</option>
              </select>
            </div>
          </div>
          <table>
            <thead>
              <tr>
                <th>Nome</th>
                {activeType.hasPhone && <th>Telefone</th>}
                {(activeType.key === "agents" || activeType.hasTeam) && <th>{activeType.teamLabel || "Equipe"}</th>}
                {activeType.hasAddress && <th>Localização</th>}
                <th>Status</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {filteredRows.map((row) => (
                <tr key={row.id}>
                  <td>{row.name}</td>
                  {activeType.hasPhone && <td>{row.phone || "-"}</td>}
                  {(activeType.key === "agents" || activeType.hasTeam) && <td>{row.team_name || "-"}</td>}
                  {activeType.hasAddress && <td>{row.address || "-"}</td>}
                  <td><span className={`badge ${row.is_active ? "success" : "neutral"}`}>{row.is_active ? "Ativo" : "Inativo"}</span></td>
                  <td className="row-actions">
                    <button className="secondary" onClick={() => edit(row)}>Editar</button>
                    <button className="icon-button danger" onClick={() => remove(row)} aria-label="Excluir">
                      <Trash2 size={16} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="pagination-bar">
            <span>{filteredRows.length} cadastros</span>
          </div>
        </div>
      </div>

      <aside className="side-panel">
        <h2>{editing ? "Editar cadastro" : "Novo cadastro"}</h2>
        <form className="stack-form" onSubmit={submit}>
          {activeType.key === "teams" ? (
            <select value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} required>
              <option value="">Selecione {activeType.teamLabel?.toLowerCase() || "a equipe"}</option>
              {militaryTeams.map((team) => <option key={team} value={team}>{team}</option>)}
            </select>
          ) : (
            <input placeholder="Nome" value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} required />
          )}
          {activeType.hasPhone && (
            <input placeholder="Telefone" value={form.phone} onChange={(event) => setForm({ ...form, phone: event.target.value })} />
          )}
          {(activeType.key === "agents" || activeType.hasTeam) && (
            <select value={form.team} onChange={(event) => setForm({ ...form, team: event.target.value })} required>
              <option value="">Selecione {activeType.teamLabel?.toLowerCase() || "a equipe"}</option>
              {teams.map((team) => <option key={team.id} value={team.id}>{team.name}</option>)}
            </select>
          )}
          {activeType.hasAddress && (
            <input placeholder="Localização" value={form.address} onChange={(event) => setForm({ ...form, address: event.target.value })} />
          )}
          <label className="checkbox">
            <input type="checkbox" checked={form.is_active} onChange={(event) => setForm({ ...form, is_active: event.target.checked })} />
            Cadastro ativo
          </label>
          {message && <div className="alert">{message}</div>}
          <button><Save size={18} /> Salvar</button>
          {editing && (
            <button type="button" className="secondary" onClick={() => { setEditing(null); setForm(emptyForm); }}>
              Novo
            </button>
          )}
        </form>
      </aside>
    </section>
  );
}

