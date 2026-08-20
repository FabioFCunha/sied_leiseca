import assert from "node:assert/strict";
import fs from "node:fs";

import {
  buildDefaultOfficialFilters,
  buildDefaultTerritorialFilters,
  buildTerritorialCoverageNote,
  clampTerritorialDateFrom,
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
    'disabled={\n              isTerritorialTab'
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
    "formatMunicipalityDates(item.dates)"
  ),
  false
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
    "formatMunicipalityDates(item.dates)"
  ),
  false
);
