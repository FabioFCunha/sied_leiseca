const OPERATIONAL_ROLES = new Set(["SUPERVISOR", "USER", "SUPPORT"]);

const ROLE_LABELS = {
  SUPERVISOR: "Chefe",
  USER: "Agente",
  SUPPORT: "Apoio",
};

function normalizeString(value) {
  return String(value || "").trim();
}

function extractUserId(option) {
  if (option == null) return "";
  if (option.id != null && normalizeString(option.id)) return normalizeString(option.id);
  const sourceId = normalizeString(option.source_id);
  if (sourceId.startsWith("user:")) {
    return sourceId.slice(5);
  }
  return "";
}

function isOperationalRole(role) {
  return OPERATIONAL_ROLES.has(String(role || "").toUpperCase());
}

function isOperationalActiveUser(option) {
  return Boolean(option && option.is_active && isOperationalRole(option.role));
}

function roleLabel(role) {
  return ROLE_LABELS[String(role || "").toUpperCase()] || role || "";
}

function mergeOperationalOption(base, extra) {
  return {
    id: base.id || extra.id,
    full_name: base.full_name || base.name || extra.full_name || extra.name || "",
    cpf: base.cpf || extra.cpf || "",
    registration: base.registration || extra.registration || "",
    role: base.role || extra.role || "",
    role_label: base.role_label || extra.role_label || "",
    team_name: base.team_name || extra.team_name || base.sector_name || extra.sector_name || "",
    sector_name: base.sector_name || extra.sector_name || base.team_name || extra.team_name || "",
    source_id: base.source_id || extra.source_id || "",
    is_active: true,
  };
}

export function buildActiveOperationalUserOptions({ users = [], chiefs = [], agents = [], supports = [] } = {}) {
  const merged = new Map();

  const register = (rawOption) => {
    const userId = extractUserId(rawOption);
    if (!userId || !isOperationalActiveUser(rawOption)) return;
    const normalized = {
      id: userId,
      full_name: rawOption.full_name || rawOption.name || "",
      cpf: rawOption.cpf || "",
      registration: rawOption.registration || "",
      role: rawOption.role || "",
      role_label: roleLabel(rawOption.role || ""),
      team_name: rawOption.team_name || rawOption.sector_name || rawOption.sector?.name || "",
      sector_name: rawOption.sector_name || rawOption.team_name || rawOption.sector?.name || "",
      source_id: rawOption.source_id || `user:${userId}`,
      is_active: true,
    };
    merged.set(userId, merged.has(userId) ? mergeOperationalOption(merged.get(userId), normalized) : normalized);
  };

  users.forEach(register);
  chiefs.forEach(register);
  agents.forEach(register);
  supports.forEach(register);

  return Array.from(merged.values()).sort((left, right) => (left.full_name || "").localeCompare(right.full_name || ""));
}

export function filterDesignatedCandidates(options = [], search = "") {
  const term = normalizeString(search).toLowerCase();
  if (!term) return options;
  return options.filter((option) => {
    const haystack = [
      option.full_name,
      option.registration,
      option.cpf,
      option.id,
      option.team_name,
      option.sector_name,
    ].filter(Boolean).map((value) => String(value).toLowerCase());
    return haystack.some((value) => value.includes(term));
  });
}

export function setSelectedUserChecked(currentIds = [], value, checked) {
  const id = normalizeString(value);
  const normalizedIds = currentIds.map((item) => normalizeString(item)).filter(Boolean);
  if (!id) return normalizedIds;
  if (checked) {
    return normalizedIds.includes(id) ? normalizedIds : [...normalizedIds, id];
  }
  return normalizedIds.filter((item) => item !== id);
}
