export const OFFICIAL_FILTER_START =
  "2009-01-01";

export const TERRITORIAL_FILTER_START =
  "2022-10-03";

export function clampTerritorialDateFrom(
  value
) {
  if (
    !value ||
    value < TERRITORIAL_FILTER_START
  ) {
    return TERRITORIAL_FILTER_START;
  }

  return value;
}

export function buildDefaultOfficialFilters(
  today
) {
  return {
    date_from:
      OFFICIAL_FILTER_START,
    date_to: today,
    team: "",
    region: "",
  };
}

export function buildDefaultTerritorialFilters(
  today
) {
  return {
    date_from:
      TERRITORIAL_FILTER_START,
    date_to: today,
    team: "",
    region: "",
  };
}

export function normalizeTerritorialFilters(
  filters = {}
) {
  return {
    ...filters,
    date_from: clampTerritorialDateFrom(
      filters.date_from
    ),
  };
}

export function buildTerritorialCoverageNote(
  territorial = {}
) {
  const summary =
    territorial.summary || {};

  const unclassified =
    Number(
      summary.unclassified_operations || 0
    );

  if (unclassified <= 0) {
    return "";
  }

  const total = Number(
    summary.operations || 0
  );

  if (total <= 0) {
    return `${unclassified.toLocaleString(
      "pt-BR"
    )} fiscalizações sem classificação territorial histórica permanecem incluídas no total geral.`;
  }

  const percentage =
    (unclassified / total) * 100;

  return `${unclassified.toLocaleString(
    "pt-BR"
  )} fiscalizações sem classificação territorial histórica permanecem incluídas no total geral (${percentage.toLocaleString(
    "pt-BR",
    {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }
  )}%).`;
}
