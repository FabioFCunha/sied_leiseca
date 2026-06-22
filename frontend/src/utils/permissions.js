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

export function canAccessRoute(user, allowedRoles = []) {
  if (!allowedRoles.length) {
    return true;
  }
  if (allowedRoles.includes("CREATOR") && isCreator(user)) {
    return true;
  }
  return allowedRoles.includes(user?.role);
}
