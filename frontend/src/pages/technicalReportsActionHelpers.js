export function hasFilledValue(value) {
  if (value === null || value === undefined) return false;
  if (typeof value === "boolean") return value === true;
  if (typeof value === "string") return value.trim() !== "";
  if (Array.isArray(value)) return value.some(hasFilledValue);
  if (typeof value === "object") return Object.values(value).some(hasFilledValue);
  return true;
}

export function isActionMeaningful(action) {
  if (!action || typeof action !== "object") return false;
  return [
    action.type_action,
    action.place_action,
    action.type_audience,
    action.institution_name,
    action.start_time,
    action.final_hour,
  ].some(hasFilledValue);
}

export function getValidatableActions(actions = []) {
  return actions
    .map((action, index) => ({ action, index }))
    .filter(({ action }) => isActionMeaningful(action));
}
