const MONTHS = [
  "Jan", "Fev", "Mar", "Abr", "Mai", "Jun",
  "Jul", "Ago", "Set", "Out", "Nov", "Dez",
];

export function parseIsoDate(value) {
  const match = String(value || "").match(/^(\d{4})-(\d{2})-(\d{2})$/);
  if (!match) return null;
  return {
    year: Number(match[1]),
    month: Number(match[2]),
    day: Number(match[3]),
  };
}

export function formatDailyReportDate(value) {
  const parsed = parseIsoDate(value);
  if (!parsed) return "-";
  return `${String(parsed.day).padStart(2, "0")}/${String(parsed.month).padStart(2, "0")}/${parsed.year}`;
}

export function formatComparisonPeriod(period) {
  const from = parseIsoDate(period?.date_from);
  const to = parseIsoDate(period?.date_to);
  if (!from || !to) return "-";
  const start = from.month === 1 && from.day === 1
    ? "Jan"
    : `${String(from.day).padStart(2, "0")} ${MONTHS[from.month - 1]}`;
  return `${start}–${String(to.day).padStart(2, "0")} ${MONTHS[to.month - 1]} de ${to.year}`;
}

export function formatSignedNumber(value, options = {}) {
  if (value === null || value === undefined) return "-";
  const number = Number(value);
  const suffix = options.percentagePoints ? " p.p." : "";
  const formatted = number.toLocaleString("pt-BR", {
    minimumFractionDigits: options.decimals ?? 0,
    maximumFractionDigits: options.decimals ?? 0,
  });
  return `${number > 0 ? "+" : ""}${formatted}${suffix}`;
}
