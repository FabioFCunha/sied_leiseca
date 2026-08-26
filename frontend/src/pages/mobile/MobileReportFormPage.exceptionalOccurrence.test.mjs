import assert from "node:assert/strict";
import fs from "node:fs";

const source = fs.readFileSync(new URL("./MobileReportFormPage.jsx", import.meta.url), "utf8");

assert.match(source, /\{ NONE: "NO_IMPACT", TOTAL: "INTERRUPTED" \}/);
assert.match(source, /<option value="NO_IMPACT">Sem prejuízo<\/option>/);
assert.match(source, /<option value="PARTIAL">/);
assert.match(source, /<option value="INTERRUPTED">/);
assert.match(source, /form\.exceptional_occurrence_impact\] \|\| form\.exceptional_occurrence_impact \|\| ""/);

console.log("MobileReportFormPage.exceptionalOccurrence.test.mjs: OK");
