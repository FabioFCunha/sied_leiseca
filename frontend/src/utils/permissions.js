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

const AUDIT_ALLOWED_EMAILS = new Set([
  "madelon@pm.rj.gov.br",
  "fabiocunhaosp@gmail.com",
]);

const AUDIT_ALLOWED_CPFS = new Set([
  "05203737746",
  "08922040793",
]);

function onlyDigits(value) {
  return String(value || "").replace(/\D/g, "");
}

export function canAccessAudit(user) {
  if (!user) return false;
  if (isCreator(user)) return true;
  const email = String(user.email || "").toLowerCase();
  const cpf = onlyDigits(user.cpf);
  return AUDIT_ALLOWED_EMAILS.has(email) || AUDIT_ALLOWED_CPFS.has(cpf);
}

export function canAccessRoute(user, allowedRoles = [], moduleName = null) {
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
    if (sector === "OLS/CooAdm" && ["ESTATISTICAS", "CALENDARIO", "RELATORIOS", "FISCALIZACAO_RELATORIOS"].includes(moduleName)) {
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
