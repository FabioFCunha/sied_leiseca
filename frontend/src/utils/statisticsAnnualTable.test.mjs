import assert from "node:assert/strict";

import { ANNUAL_TABLE_GROUPS, ANNUAL_DISTRIBUTION_TOTAL_KEY, withAnnualDistributionTotal } from "./statisticsAnnualTable.js";
import { buildStatisticsViewModel } from "./statisticsViewModel.js";

assert.deepEqual(
  ANNUAL_TABLE_GROUPS.map((group) => group.title),
  ["Público", "Palestras total", "Total de ações", "Materiais de distribuição total"]
);
assert.equal(ANNUAL_TABLE_GROUPS.flatMap((group) => group.rows).some(([, label]) => label === "Materiais de divulgação"), false);
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
