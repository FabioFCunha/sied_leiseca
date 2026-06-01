export default function Filters({ filters, setFilters, sectors = [], municipalities = [], users = [], showUser = true }) {
  const update = (field, value) => setFilters((current) => ({ ...current, [field]: value }));

  return (
    <div className="filters">
      <input
        placeholder="Buscar protocolo, título, local, município..."
        value={filters.q || ""}
        onChange={(e) => update("q", e.target.value)}
      />
      <label className="filter-field">
        <span>Data exata</span>
        <input type="date" value={filters.date || ""} onChange={(e) => update("date", e.target.value)} />
      </label>
      <label className="filter-field">
        <span>De</span>
        <input type="date" value={filters.date_from || ""} onChange={(e) => update("date_from", e.target.value)} />
      </label>
      <label className="filter-field">
        <span>Até</span>
        <input type="date" value={filters.date_to || ""} onChange={(e) => update("date_to", e.target.value)} />
      </label>
      <select value={filters.status || ""} onChange={(e) => update("status", e.target.value)}>
        <option value="">Todos os status</option>
        <option value="PENDING">Pendente</option>
        <option value="APPROVED">Aprovada</option>
        <option value="CANCELLED">Cancelada</option>
      </select>
      <select value={filters.sector || ""} onChange={(e) => update("sector", e.target.value)}>
        <option value="">Todas as equipes</option>
        {sectors.map((sector) => (
          <option key={sector.id} value={sector.id}>
            {sector.name}
          </option>
        ))}
      </select>
      <select value={filters.municipality || ""} onChange={(e) => update("municipality", e.target.value)}>
        <option value="">Todos os municípios</option>
        {municipalities.map((municipality) => (
          <option key={municipality.id} value={municipality.id}>
            {municipality.name}
          </option>
        ))}
      </select>
      {showUser && (
        <select value={filters.responsible || ""} onChange={(e) => update("responsible", e.target.value)}>
          <option value="">Todos os responsáveis</option>
          {users.map((user) => (
            <option key={user.id} value={user.id}>
              {user.full_name}
            </option>
          ))}
        </select>
      )}
      <button className="secondary" onClick={() => setFilters({})}>
        Limpar
      </button>
    </div>
  );
}
