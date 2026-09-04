import assert from "node:assert/strict";
import {
  formatComparisonPeriod,
  formatDailyReportDate,
  formatSignedNumber,
} from "./inspectionDailyReport.js";

assert.equal(formatDailyReportDate("2026-09-03"), "03/09/2026");
assert.equal(
  formatComparisonPeriod({ date_from: "2025-01-01", date_to: "2025-09-03" }),
  "Jan–03 Set de 2025"
);
assert.equal(formatSignedNumber(1250), "+1.250");
assert.equal(
  formatSignedNumber(-1.5, { decimals: 2, percentagePoints: true }),
  "-1,50 p.p."
);
assert.equal(formatSignedNumber(null), "-");

console.log("inspectionDailyReport tests passed");
