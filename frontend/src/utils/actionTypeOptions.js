const VALID_OPERATIONAL_CATEGORIES = new Set(["LECTURE", "EDUCATIONAL_ACTION"]);

export function isOperationalEducationActionType(actionType) {
  if (!actionType || typeof actionType !== "object") return false;
  const name = String(actionType.name || "").trim();
  if (!name) return false;
  if (actionType.is_active === false) return false;
  if (!VALID_OPERATIONAL_CATEGORIES.has(actionType.category)) return false;
  return name.toLocaleLowerCase("pt-BR") !== "palestra escola";
}

export function filterOperationalEducationActionTypes(actionTypes = []) {
  return (actionTypes || []).filter(isOperationalEducationActionType);
}

export function findOperationalEducationActionTypeName(value, actionTypes = []) {
  const normalized = String(value || "").trim().toLocaleLowerCase("pt-BR");
  if (!normalized) return "";
  const match = filterOperationalEducationActionTypes(actionTypes).find(
    (actionType) => String(actionType.name || "").trim().toLocaleLowerCase("pt-BR") === normalized
  );
  return match?.name || "";
}

export function getAgendaOperationalActionTypeName(agenda, actionTypes = []) {
  if (!agenda) return "";
  return (
    findOperationalEducationActionTypeName(agenda.action_type_ref_name, actionTypes) ||
    findOperationalEducationActionTypeName(agenda.action_type, actionTypes)
  );
}
