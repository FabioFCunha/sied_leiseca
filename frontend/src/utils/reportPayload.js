function normalizePk(value) {
  const rawValue = value && typeof value === "object" ? value.id : value;
  if (rawValue === "" || rawValue === undefined || rawValue === null) return null;

  const numericValue = Number(rawValue);
  if (Number.isInteger(numericValue) && String(rawValue).trim() !== "") {
    return numericValue;
  }

  return rawValue;
}

export function agendaPk(value, fallback = null) {
  return normalizePk(value) ?? normalizePk(fallback);
}
