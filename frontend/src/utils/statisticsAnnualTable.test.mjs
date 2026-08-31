import assert from "node:assert/strict";

import { ANNUAL_TABLE_GROUPS, ANNUAL_DISTRIBUTION_TOTAL_KEY, withAnnualDistributionTotal } from "./statisticsAnnualTable.js";
import { buildStatisticsViewModel } from "./statisticsViewModel.js";

assert.deepEqual(
  ANNUAL_TABLE_GROUPS.map((group) => group.title),
  ["PÚBLICO", "PALESTRAS", "AÇÕES", "MATERIAIS DE DISTRIBUIÇÃO"]
);
const annualLabels = ANNUAL_TABLE_GROUPS.flatMap((group) => group.rows).map(([, label]) => label);
assert.equal(annualLabels.includes("Palestras total"), false);
assert.equal(annualLabels.includes("Materiais de distribuição total"), false);
assert.ok(annualLabels.includes("Total de palestras"));
assert.ok(annualLabels.includes("Total de ações"));
assert.ok(annualLabels.includes("Total de materiais de distribuição"));
assert.ok(annualLabels.includes("Kit com 7 Revistinhas"));
assert.ok(annualLabels.includes("Ventarola Futebol"));
assert.equal(annualLabels.some((label) => label === "Materiais de divulgação"), false);
assert.deepEqual(
  withAnnualDistributionTotal({
    "MATERIAL - Soprinho": 5,
    "MATERIAL - Kit com 7 Revistinhas": 2,
    "MATERIAL - Ventarola Futebol": 3,
  }),
  {
    "MATERIAL - Soprinho": 5,
    "MATERIAL - Kit com 7 Revistinhas": 2,
    "MATERIAL - Ventarola Futebol": 3,
    [ANNUAL_DISTRIBUTION_TOTAL_KEY]: 10,
  }
);
assert.equal(withAnnualDistributionTotal({})[ANNUAL_DISTRIBUTION_TOTAL_KEY], 0);

const annual = buildStatisticsViewModel({
  dashboardData: { annual: [{ year: 2026, values: { "MATERIAL - Soprinho": 5, "MATERIAL - Kit com 7 Revistinhas": 2, "MATERIAL - Ventarola Futebol": 3 } }] },
  filteredAgendas: [],
  futureAgendas: [],
}).annual[0];
assert.equal(annual[ANNUAL_DISTRIBUTION_TOTAL_KEY], 10);

console.log("statisticsAnnualTable.test.mjs: OK");
