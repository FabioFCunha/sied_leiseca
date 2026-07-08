export const roleLabel = {
  ADMIN: "Administração",
  MANAGER: "Gestor",
  SUPERVISOR: "Chefe",
  SUPPORT: "Apoio",
  VISITOR: "Visitante",
  USER: "Agente",
};

export function isCreator(user) {
  return Boolean(user?.is_superuser);
}

export function canAccessRoute(user, allowedRoles = [], moduleName = null) {
  if (!allowedRoles.length) {
    return true;
  }
  if (allowedRoles.includes("CREATOR") && isCreator(user)) {
    return true;
  }

  if (user?.role === "VISITOR") {
    const sector = user?.sector_name;
    if (sector === "Subsecretaria") {
      const allowedModules = ["DASHBOARD", "AGENDAS", "CALENDARIO", "ESCALA", "RELATORIOS", "ESTATISTICAS", "AVALIACOES"];
      if (allowedModules.includes(moduleName)) return true;
    }
    if (sector === "OLS/CooAdm" && ["ESTATISTICAS", "CALENDARIO"].includes(moduleName)) {
      return true;
    }
    if (sector === "ASCOM" && moduleName === "CALENDARIO") {
      return true;
    }
  }

  return allowedRoles.includes(user?.role);
}
