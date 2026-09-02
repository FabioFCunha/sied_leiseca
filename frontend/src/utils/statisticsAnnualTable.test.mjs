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
assert.ok(annualLabels.includes("Ação Social"));
assert.ok(annualLabels.includes("Outros"));
assert.ok(annualLabels.includes("Ação conjunta com a Fiscalização"));
const actionRows = ANNUAL_TABLE_GROUPS.find((group) => group.title === "AÇÕES").rows;
assert.equal(actionRows[0][0], "STREET_ACTIONS - Geral");
assert.equal(actionRows[0][1], "Total de ações");
const final2026Values = {
  "ACTION - Ação Social": 1,
  "ACTION - Outros": 382,
  "ACTION - Ação conjunta com a fiscalização": 7,
};
const final2026 = buildStatisticsViewModel({
  dashboardData: { annual: [{ year: 2026, values: final2026Values }] },
  filteredAgendas: [],
  futureAgendas: [],
}).annual[0];
for (const [key] of actionRows) {
  if (key in final2026Values) assert.equal(final2026[key], final2026Values[key]);
}
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
