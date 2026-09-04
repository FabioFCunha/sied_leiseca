export const roleLabel = {
  ADMIN: "Administração",
  MANAGER: "Gestor",
  SUPERVISOR: "Chefe",
  SUPPORT: "Apoio",
  VISITOR: "Visitante",
  USER: "Agente",
  ALMOXARIFADO: "Almoxarifado",
};

export function isCreator(user) {
  return Boolean(user?.is_superuser);
}

export const ACCESS_AREAS = {
  EDUCATION: "EDUCATION",
  INSPECTION: "INSPECTION",
};

const INSPECTION_MODULES = new Set([
  "FISCALIZACAO_RELATORIOS",
  "FISCALIZACAO_ESTATISTICAS",
]);

const EDUCATION_MODULES = new Set([
  "DASHBOARD", "AGENDAS", "CALENDARIO", "ESCALA", "RELATORIOS",
  "ESTATISTICAS", "AVALIACOES", "METAS", "CADASTROS",
]);

const READ_ONLY_VIEWABLE_MODULES = new Set([
  ...INSPECTION_MODULES,
  ...EDUCATION_MODULES,
]);

export function userAccessAreas(user) {
  if (isCreator(user)) return new Set(Object.values(ACCESS_AREAS));
  const areas = Array.isArray(user?.access_areas)
    ? user.access_areas
    : Object.values(ACCESS_AREAS);
  return new Set(areas.map((area) => String(area).toUpperCase()));
}

export function canModify(user) {
  return Boolean(user && (isCreator(user) || !user.is_read_only));
}

function canAccessModuleArea(user, moduleName) {
  const areas = userAccessAreas(user);
  if (INSPECTION_MODULES.has(moduleName)) return areas.has(ACCESS_AREAS.INSPECTION);
  if (EDUCATION_MODULES.has(moduleName)) return areas.has(ACCESS_AREAS.EDUCATION);
  return true;
}

const AUDIT_ALLOWED_EMAILS = new Set([
  "madelon@pm.rj.gov.br",
  "fabiocunhaosp@gmail.com",
]);

const AUDIT_ALLOWED_CPFS = new Set([
  "05203737746",
  "08922040793",
]);

const INSPECTION_REPORT_REVIEWER_CPF = "08922040793";
const INSPECTION_REPORT_REVIEWER_EMAIL = "fabiocunhaosp@gmail.com";

function onlyDigits(value) {
  return String(value || "").replace(/\D/g, "");
}

function normalizeText(value) {
  return String(value || "").trim().toLowerCase();
}

export function canAccessAudit(user) {
  if (!user) return false;
  if (isCreator(user)) return true;
  const email = String(user.email || "").toLowerCase();
  const cpf = onlyDigits(user.cpf);
  return AUDIT_ALLOWED_EMAILS.has(email) || AUDIT_ALLOWED_CPFS.has(cpf);
}

export function canAccessRoute(user, allowedRoles = [], moduleName = null) {
  if (!user || !canAccessModuleArea(user, moduleName)) return false;
  if (isCreator(user)) return true;
  if (user.is_read_only) {
    return READ_ONLY_VIEWABLE_MODULES.has(moduleName);
  }
  if (!allowedRoles.length) {
    return true;
  }
  if (moduleName === "AUDITORIA") {
    return canAccessAudit(user);
  }
  if (allowedRoles.includes("CREATOR") && isCreator(user)) {
    return true;
  }

  if (user?.role === "VISITOR") {
    const sector = user?.sector_name;
    if (sector === "Subsecretaria") {
      const allowedModules = ["DASHBOARD", "CALENDARIO", "ESCALA", "RELATORIOS", "ESTATISTICAS", "AVALIACOES", "FISCALIZACAO_RELATORIOS"];
      if (allowedModules.includes(moduleName)) return true;
    }
    if (sector === "OLS/CooAdm" && ["ESTATISTICAS", "CALENDARIO", "RELATORIOS", "FISCALIZACAO_RELATORIOS", "FISCALIZACAO_ESTATISTICAS"].includes(moduleName)) {
      return true;
    }
    if (sector === "ASCOM" && moduleName === "CALENDARIO") {
      return true;
    }
  }

  if (user?.role === "ALMOXARIFADO" && moduleName === "CALENDARIO") {
    return true;
  }

  return allowedRoles.includes(user?.role);
}

export function canReviewInspectionStatistics(user) {
  if (!user) return false;
  const role = String(user.role || "").trim().toUpperCase();
  const sectorName = normalizeText(user.sector_name || user.sector?.name);
  if (role === "VISITOR" && sectorName === normalizeText("OLS/CooAdm")) {
    return true;
  }
  return (
    onlyDigits(user.cpf) === INSPECTION_REPORT_REVIEWER_CPF
    || onlyDigits(user.username) === INSPECTION_REPORT_REVIEWER_CPF
    || normalizeText(user.email) === INSPECTION_REPORT_REVIEWER_EMAIL
  );
}

export function canViewInspectionStatistics(user) {
  if (!user) return false;
  const role = String(user.role || "").trim().toUpperCase();
  if (["ADMIN", "MANAGER", "SUPERVISOR"].includes(role)) {
    return true;
  }
  return canReviewInspectionStatistics(user);
}
