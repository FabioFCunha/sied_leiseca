import assert from "node:assert/strict";
import fs from "node:fs";

import {
  DEFAULT_TERRITORIAL_RANKING_INDICATORS,
  buildDefaultOfficialFilters,
  buildDefaultTerritorialRankingFilters,
  buildDefaultTerritorialFilters,
  buildPdfMunicipalityLabel,
  buildTerritorialCoverageNote,
  clampTerritorialDateFrom,
  filterRankingRegions,
  filterRankingMunicipalities,
  formatMunicipalityDates,
  hasMunicipalityRain,
  isShortTerritorialPeriod,
  normalizeTerritorialRankingFilters,
  normalizeTerritorialFilters,
  OFFICIAL_FILTER_START,
  TERRITORIAL_FILTER_START,
} from "./inspectionTerritorialViewModel.js";

assert.equal(
  OFFICIAL_FILTER_START,
  "2009-01-01"
);

assert.equal(
  TERRITORIAL_FILTER_START,
  "2022-10-03"
);

assert.equal(
  clampTerritorialDateFrom(
    "2009-01-01"
  ),
  "2022-10-03"
);

assert.equal(
  clampTerritorialDateFrom(
    "2023-01-15"
  ),
  "2023-01-15"
);

assert.equal(
  clampTerritorialDateFrom(""),
  "2022-10-03"
);

assert.equal(
  clampTerritorialDateFrom(
    "2022-10-02"
  ),
  "2022-10-03"
);

assert.equal(
  clampTerritorialDateFrom(
    "2023-01-01"
  ),
  "2023-01-01"
);

assert.equal(
  clampTerritorialDateFrom(
    "2026-08-01"
  ),
  "2026-08-01"
);

assert.deepEqual(
  buildDefaultOfficialFilters(
    "2026-08-20"
  ),
  {
    date_from: "2009-01-01",
    date_to: "2026-08-20",
    team: "",
    region: "",
  }
);

assert.deepEqual(
  buildDefaultTerritorialFilters(
    "2026-08-20"
  ),
  {
    date_from: "2022-10-03",
    date_to: "2026-08-20",
    team: "",
    region: "",
  }
);

assert.equal(
  buildDefaultTerritorialFilters(
    "2026-08-20"
  ).date_from,
  "2022-10-03"
);

assert.deepEqual(
  DEFAULT_TERRITORIAL_RANKING_INDICATORS,
  [
    "operations",
    "approach",
    "alcohol_cases",
    "alcohol_percentage",
  ]
);

assert.deepEqual(
  buildDefaultTerritorialRankingFilters(
    "2026-08-20"
  ),
  {
    date_from: "2022-10-03",
    date_to: "2026-08-20",
    team: "",
    territorial_area: "all",
    region: "",
    municipality: "",
    indicators: [
      "operations",
      "approach",
      "alcohol_cases",
      "alcohol_percentage",
    ],
  }
);

assert.deepEqual(
  normalizeTerritorialFilters({
    date_from: "2020-01-01",
    date_to: "2026-08-20",
    team: "A1",
    region: "Metropolitana",
  }),
  {
    date_from: "2022-10-03",
    date_to: "2026-08-20",
    team: "A1",
    region: "Metropolitana",
  }
);

assert.deepEqual(
  normalizeTerritorialRankingFilters({
    date_from: "2020-01-01",
    date_to: "2026-08-20",
    team: "A1",
    territorial_area: "interior",
    region: "Metropolitana",
    municipality: "Niterói",
    indicators: ["fined", "towed", "fined"],
  }),
  {
    date_from: "2022-10-03",
    date_to: "2026-08-20",
    team: "A1",
    territorial_area: "interior",
    region: "Metropolitana",
    municipality: "Niterói",
    indicators: ["fined", "towed"],
  }
);

assert.deepEqual(
  filterRankingRegions(
    [
      {
        region: "Metropolitana",
        region_code: "METROPOLITANA",
        territorial_group: "metropolitan",
      },
      {
        region: "Costa Verde",
        region_code: "COSTA_VERDE",
        territorial_group: "interior",
      },
    ],
    "interior"
  ),
  [
    {
      region: "Costa Verde",
      region_code: "COSTA_VERDE",
      territorial_group: "interior",
    },
  ]
);

assert.deepEqual(
  filterRankingMunicipalities(
    [
      {
        municipality_id: 1,
        municipality: "Angra dos Reis",
        region: "Costa Verde",
        region_code: "COSTA_VERDE",
        territorial_group: "interior",
      },
      {
        municipality_id: 2,
        municipality: "Niterói",
        region: "Metropolitana",
        region_code: "METROPOLITANA",
        territorial_group: "metropolitan",
      },
    ],
    "metropolitan",
    "Metropolitana"
  ),
  [
    {
      municipality_id: 2,
      municipality: "Niterói",
      region: "Metropolitana",
      region_code: "METROPOLITANA",
      territorial_group: "metropolitan",
    },
  ]
);

const note =
  buildTerritorialCoverageNote({
    summary: {
      operations: 13887,
      unclassified_operations: 1898,
    },
  });

assert.match(
  note,
  /1\.898 fiscalizações sem classificação territorial histórica/
);

assert.match(note, /13,67%/);

assert.equal(
  hasMunicipalityRain({
    municipality: "Petrópolis",
    rain: 1,
  }),
  true
);

assert.equal(
  hasMunicipalityRain({
    municipality: "Petrópolis",
    rain: 0,
  }),
  false
);

assert.equal(
  isShortTerritorialPeriod({
    date_from: "2026-08-14",
    date_to: "2026-08-18",
  }),
  true
);

assert.equal(
  isShortTerritorialPeriod({
    date_from: "2026-08-14",
    date_to: "2026-08-19",
  }),
  false
);

assert.equal(
  formatMunicipalityDates([
    "2026-08-14",
    "2026-08-16",
  ]),
  "14 e 16/08/2026"
);

assert.equal(
  buildPdfMunicipalityLabel({
    municipality: "Petrópolis",
    rain: 1,
    dates: ["2026-08-14"],
  }, {
    date_from: "2026-08-14",
    date_to: "2026-08-18",
  }),
  "Chuva (Teve chuva) Petrópolis\n14/08/2026"
);

assert.equal(
  buildPdfMunicipalityLabel({
    municipality: "Petrópolis",
    rain: 0,
    dates: ["2026-08-14"],
  }, {
    date_from: "2026-08-14",
    date_to: "2026-08-20",
  }),
  "Petrópolis"
);

const pageSource = fs.readFileSync(
  new URL(
    "../pages/InspectionStatisticsPage.jsx",
    import.meta.url
  ),
  "utf8"
);

assert.equal(
  pageSource.includes(
    'min={\n              isTerritorialLikeTab\n                ? TERRITORIAL_FILTER_START'
  ),
  true
);

assert.equal(
  pageSource.includes(
    "setTerritorialDraftFilters("
  ),
  true
);

assert.equal(
  pageSource.includes(
    'disabled={\n              isTerritorialTab'
  ),
  false
);

assert.equal(
  pageSource.includes(
    "Ranking Territorial"
  ),
  true
);

assert.equal(
  pageSource.includes(
    "getInspectionTerritorialRanking"
  ),
  true
);

assert.equal(
  pageSource.includes(
    "Registros territoriais não classificados"
  ),
  false
);

assert.equal(
  pageSource.includes(
    "showMunicipalityPeriodSummary && formatMunicipalityDates(item.dates)"
  ),
  true
);

assert.equal(
  pageSource.includes(
    'title="Ocorrência de chuva"'
  ),
  true
);

assert.equal(
  pageSource.includes(
    'aria-label="Ocorrência de chuva"'
  ),
  true
);

assert.equal(
  pageSource.includes(
    "hasMunicipalityRain(item)"
  ),
  true
);

assert.equal(
  pageSource.includes(
    "(Teve chuva)"
  ),
  true
);

assert.equal(
  pageSource.includes(
    "Indicadores adicionais"
  ),
  false
);

assert.equal(
  pageSource.includes(
    "stats-filter-multiselect-trigger"
  ),
  true
);

assert.equal(
  pageSource.includes(
    "buildRankingIndicatorSummary("
  ),
  true
);

assert.equal(
  pageSource.includes(
    "setIsRankingIndicatorsOpen(false)"
  ),
  true
);

assert.equal(
  pageSource.includes(
    "formatRankingContextDate("
  ),
  true
);

const pdfSource = fs.readFileSync(
  new URL(
    "./inspectionTerritorialPdfGenerator.js",
    import.meta.url
  ),
  "utf8"
);

assert.equal(
  pdfSource.includes(
    "buildPdfMunicipalityLabel(\n          item,\n          filters"
  ),
  true
);
