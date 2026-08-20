export const OFFICIAL_FILTER_START =
  "2009-01-01";

export const TERRITORIAL_FILTER_START =
  "2022-10-03";

export const DEFAULT_TERRITORIAL_RANKING_INDICATORS =
  [
    "operations",
    "approach",
    "alcohol_cases",
    "alcohol_percentage",
  ];

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

export function buildDefaultTerritorialRankingFilters(
  today
) {
  return {
    date_from:
      TERRITORIAL_FILTER_START,
    date_to: today,
    team: "",
    territorial_area: "all",
    region: "",
    municipality: "",
    indicators: [
      ...DEFAULT_TERRITORIAL_RANKING_INDICATORS,
    ],
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

export function normalizeTerritorialRankingFilters(
  filters = {}
) {
  return {
    ...filters,
    date_from: clampTerritorialDateFrom(
      filters.date_from
    ),
    territorial_area:
      filters.territorial_area ||
      "all",
    municipality:
      filters.municipality || "",
    indicators: Array.isArray(
      filters.indicators
    )
      ? [
          ...new Set(
            filters.indicators.filter(Boolean)
          ),
        ]
      : [],
  };
}

export function filterRankingRegions(
  regions = [],
  territorialArea = "all"
) {
  return regions.filter((item) => {
    if (territorialArea === "all") {
      return true;
    }

    return (
      item.territorial_group ===
      territorialArea
    );
  });
}

export function filterRankingMunicipalities(
  municipalities = [],
  territorialArea = "all",
  region = ""
) {
  const normalizedRegion = String(
    region || ""
  ).trim();

  return municipalities
    .filter((item) => {
      if (
        territorialArea !== "all" &&
        item.territorial_group !==
          territorialArea
      ) {
        return false;
      }

      if (!normalizedRegion) {
        return true;
      }

      return (
        item.region ===
          normalizedRegion ||
        item.region_code ===
          normalizedRegion.toUpperCase()
      );
    })
    .sort((left, right) =>
      String(
        left.municipality || ""
      ).localeCompare(
        String(
          right.municipality || ""
        ),
        "pt-BR"
      )
    );
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

export function hasMunicipalityRain(
  municipality = {}
) {
  return (
    Number(municipality.rain || 0) > 0
  );
}

export function isShortTerritorialPeriod(
  filters = {}
) {
  if (
    !filters?.date_from ||
    !filters?.date_to
  ) {
    return false;
  }

  const start = new Date(
    `${filters.date_from}T00:00:00`
  );
  const end = new Date(
    `${filters.date_to}T00:00:00`
  );

  if (
    Number.isNaN(start.getTime()) ||
    Number.isNaN(end.getTime()) ||
    end < start
  ) {
    return false;
  }

  const diffDays = Math.floor(
    (end - start) / 86400000
  );

  return diffDays <= 4;
}

export function formatMunicipalityDates(
  dates = []
) {
  if (!Array.isArray(dates) || dates.length === 0) {
    return "";
  }

  const uniqueDates = [
    ...new Set(dates.map(String)),
  ].sort();

  const parts = uniqueDates.map((value) => {
    const [year, month, day] = value.split("-");

    if (!year || !month || !day) {
      return null;
    }

    return {
      year,
      month,
      day,
      full: `${day}/${month}/${year}`,
    };
  });

  if (parts.some((item) => item === null)) {
    return uniqueDates.join(" · ");
  }

  if (parts.length === 1) {
    return parts[0].full;
  }

  const sameMonth = parts.every(
    (item) => item.month === parts[0].month
  );
  const sameYear = parts.every(
    (item) => item.year === parts[0].year
  );

  if (sameMonth && sameYear) {
    const days = parts.map((item) => item.day);

    if (days.length === 2) {
      return `${days[0]} e ${days[1]}/${parts[0].month}/${parts[0].year}`;
    }

    return `${days.slice(0, -1).join(", ")} e ${days.at(-1)}/${parts[0].month}/${parts[0].year}`;
  }

  return parts.map((item) => item.full).join(" · ");
}

export function buildPdfMunicipalityLabel(
  municipality = {},
  filters = {}
) {
  const name = String(
    municipality.municipality || ""
  );
  const prefix = hasMunicipalityRain(municipality)
    ? "Chuva (Teve chuva) "
    : "";
  const dateSummary =
    isShortTerritorialPeriod(filters)
      ? formatMunicipalityDates(
          municipality.dates
        )
      : "";

  if (dateSummary) {
    return `${prefix}${name}\n${dateSummary}`;
  }

  return `${prefix}${name}`;
}
