import { Save, Trash2 } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { api } from "../api/client.js";

const lookupTypes = [
  { key: "teams", label: "Equipes", endpoint: "/teams/" },
  { key: "chiefs", label: "Chefes", endpoint: "/chiefs/", hasCpf: true, hasAddress: true, hasTeam: true, teamLabel: "Equipe" },
  { key: "agents", label: "Agentes", endpoint: "/agents/", hasCpf: true, hasAddress: true, teamLabel: "Equipe" },
  { key: "supports", label: "Apoios", endpoint: "/supports/", hasCpf: true, hasAddress: true, hasTeam: true, teamLabel: "Ala" },
  { key: "vehicles", label: "Viaturas", endpoint: "/vehicles/" },
  { key: "kits", label: "Kits", endpoint: "/kits/" },
  { key: "accessibility-blocklist", label: "Bloqueios de Acessibilidade", endpoint: "/accessibility-blocklist/", isBlocklist: true },
];

const emptyForm = {
  name: "",
  cpf: "",
  phone: "",
  team: "",
  address: "",
  is_active: true,
  institution_location: "",
  external_responsible: "",
  external_responsible_phone: "",
  external_email: "",
  requester_cpf: "",
  reason: "",
};

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
      
      let matchesSearch = true;
      if (term) {
        if (activeType.isBlocklist) {
          matchesSearch = `${row.institution_location || ""} ${row.address || ""} ${row.external_responsible || ""} ${row.external_email || ""}`.toLowerCase().includes(term);
        } else {
          matchesSearch = `${row.name || ""} ${row.cpf || ""} ${row.phone || ""} ${row.address || ""} ${row.team_name || ""}`.toLowerCase().includes(term);
        }
      }
      return matchesStatus && matchesSearch;
    });
  }, [rows, search, statusFilter, activeType]);

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

    let payload = {};
    if (activeType.isBlocklist) {
      payload = {
        institution_location: form.institution_location || "",
        address: form.address || "",
        external_responsible: form.external_responsible || "",
        external_responsible_phone: form.external_responsible_phone || "",
        external_email: form.external_email || "",
        requester_cpf: String(form.requester_cpf || "").replace(/\D/g, "") || "",
        reason: form.reason || "",
        is_active: form.is_active,
      };
    } else {
      payload = {
        name: form.name,
        is_active: form.is_active,
      };
      if (activeType.hasPhone) {
        payload.phone = form.phone || "";
      }
      if (activeType.hasCpf) {
        payload.cpf = String(form.cpf || "").replace(/\D/g, "") || null;
      }
      if (activeType.hasAddress) {
        payload.address = form.address || "";
      }
      if (activeType.key === "agents" || activeType.hasTeam) {
        payload.team = form.team || null;
      }
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
    if (activeType.isBlocklist) {
      setForm({
        ...emptyForm,
        institution_location: row.institution_location || "",
        address: row.address || "",
        external_responsible: row.external_responsible || "",
        external_responsible_phone: row.external_responsible_phone || "",
        external_email: row.external_email || "",
        requester_cpf: row.requester_cpf || "",
        reason: row.reason || "",
        is_active: row.is_active,
      });
    } else {
      setForm({
        ...emptyForm,
        name: row.name || "",
        cpf: row.cpf || "",
        phone: row.phone || "",
        team: row.team || "",
        address: row.address || "",
        is_active: row.is_active,
      });
    }
  };

  const remove = async (row) => {
    setMessage("");
    try {
      await api(`${activeType.endpoint}${row.id}/`, { method: "DELETE" });
      setMessage("Cadastro excluído.");
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
            <p>Gerencie listas usadas nos formulários de novas agendas.</p>
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
                <option value="active">{activeType.isBlocklist ? "Restritos" : "Ativos"}</option>
                <option value="inactive">{activeType.isBlocklist ? "Liberados" : "Inativos"}</option>
                <option value="all">Todos</option>
              </select>
            </div>
          </div>
          <table>
            <thead>
              {activeType.isBlocklist ? (
                <tr>
                  <th>Local / Instituição</th>
                  <th>Endereço</th>
                  <th>Responsável</th>
                  <th>E-mail</th>
                  <th>Motivo</th>
                  <th>Status</th>
                  <th></th>
                </tr>
              ) : (
                <tr>
                  <th>Nome</th>
                  {activeType.hasCpf && <th>CPF</th>}
                  {activeType.hasPhone && <th>Telefone</th>}
                  {(activeType.key === "agents" || activeType.hasTeam) && <th>{activeType.teamLabel || "Equipe"}</th>}
                  {activeType.hasAddress && <th>Localização</th>}
                  <th>Status</th>
                  <th></th>
                </tr>
              )}
            </thead>
            <tbody>
              {filteredRows.map((row) => (
                <tr key={row.id}>
                  {activeType.isBlocklist ? (
                    <>
                      <td>{row.institution_location || "-"}</td>
                      <td>{row.address || "-"}</td>
                      <td>{row.external_responsible || "-"}</td>
                      <td>{row.external_email || "-"}</td>
                      <td style={{ maxWidth: "250px", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }} title={row.reason}>
                        {row.reason || "-"}
                      </td>
                    </>
                  ) : (
                    <>
                      <td>{row.name}</td>
                      {activeType.hasCpf && <td>{row.cpf || "-"}</td>}
                      {activeType.hasPhone && <td>{row.phone || "-"}</td>}
                      {(activeType.key === "agents" || activeType.hasTeam) && <td>{row.team_name || "-"}</td>}
                      {activeType.hasAddress && <td>{row.address || "-"}</td>}
                    </>
                  )}
                  <td>
                    <span className={`badge ${row.is_active ? "danger" : "success"}`}>
                      {activeType.isBlocklist
                        ? (row.is_active ? "Restrito" : "Liberado")
                        : (row.is_active ? "Ativo" : "Inativo")
                      }
                    </span>
                  </td>
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
          {activeType.isBlocklist ? (
            <>
              <input
                placeholder="Nome do local / instituição"
                value={form.institution_location || ""}
                onChange={(event) => setForm({ ...form, institution_location: event.target.value })}
                required
              />
              <input
                placeholder="Endereço"
                value={form.address || ""}
                onChange={(event) => setForm({ ...form, address: event.target.value })}
                required
              />
              <input
                placeholder="Nome do responsável"
                value={form.external_responsible || ""}
                onChange={(event) => setForm({ ...form, external_responsible: event.target.value })}
              />
              <input
                placeholder="E-mail do responsável"
                value={form.external_email || ""}
                onChange={(event) => setForm({ ...form, external_email: event.target.value })}
                type="email"
              />
              <input
                placeholder="Telefone do responsável"
                value={form.external_responsible_phone || ""}
                onChange={(event) => setForm({ ...form, external_responsible_phone: event.target.value })}
              />
              <input
                placeholder="CPF do solicitante"
                value={form.requester_cpf || ""}
                onChange={(event) => setForm({ ...form, requester_cpf: event.target.value.replace(/\D/g, "").slice(0, 11) })}
                inputMode="numeric"
                maxLength="11"
              />
              <textarea
                placeholder="Motivo da restrição"
                value={form.reason || ""}
                onChange={(event) => setForm({ ...form, reason: event.target.value })}
                rows={3}
                style={{ padding: "8px", borderRadius: "4px", border: "1px solid #ccc", width: "100%", fontFamily: "inherit" }}
              />
            </>
          ) : (
            <>
              <input
                placeholder={activeType.key === "teams" ? "Nome da equipe" : "Nome"}
                value={form.name}
                onChange={(event) => setForm({ ...form, name: event.target.value })}
                required
              />
              {activeType.hasCpf && (
                <input
                  placeholder="CPF"
                  value={form.cpf || ""}
                  onChange={(event) => setForm({ ...form, cpf: event.target.value.replace(/\D/g, "").slice(0, 11) })}
                  inputMode="numeric"
                  maxLength="11"
                />
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
            </>
          )}
          <label className="checkbox">
            <input type="checkbox" checked={form.is_active} onChange={(event) => setForm({ ...form, is_active: event.target.checked })} />
            {activeType.isBlocklist ? "Restrição ativa (Bloqueado)" : "Cadastro ativo"}
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

