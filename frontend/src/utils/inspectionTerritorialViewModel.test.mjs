import assert from "node:assert/strict";
import fs from "node:fs";

import {
  buildDefaultOfficialFilters,
  buildDefaultTerritorialFilters,
  buildPdfMunicipalityLabel,
  buildTerritorialCoverageNote,
  clampTerritorialDateFrom,
  formatMunicipalityDates,
  hasMunicipalityRain,
  isShortTerritorialPeriod,
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
    'min={\n              isTerritorialTab\n                ? TERRITORIAL_FILTER_START'
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
