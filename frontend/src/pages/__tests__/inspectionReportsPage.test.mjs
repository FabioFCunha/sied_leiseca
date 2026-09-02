import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const source = readFileSync(new URL("../InspectionReportsPage.jsx", import.meta.url), "utf8");

assert.ok(source.includes('whiteSpace: "pre-wrap"'));
assert.ok(source.includes('label="Chefe da equipe civil"'));
assert.ok(source.includes('label="OPM de apoio"'));
assert.ok(source.includes('label="Efetivo PMERJ de apoio"'));
assert.ok(source.includes('label="Viaturas de apoio"'));
assert.ok(source.includes('label="Motivos para baixa abordagem"'));
assert.ok(source.includes('label="Autos de infração da equipe"'));
assert.ok(source.includes('label="Especifique os AI utilizados"'));
assert.ok(source.includes('label="Geral" value={selectedReport.miscellaneous_changes}'));
assert.ok(source.includes("generateInspectionReportPdf(selectedReport)"));

console.log("inspectionReportsPage.test.mjs: OK");
