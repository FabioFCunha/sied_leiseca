import assert from "node:assert/strict";
import fs from "node:fs";

const source = fs.readFileSync(new URL("./TechnicalReportsPage.jsx", import.meta.url), "utf8");

assert.match(source, /value: "NO_IMPACT", label: "Sem preju\\u00edzo"/);
assert.match(source, /value: "PARTIAL", label: "Prejudicada parcialmente"/);
assert.match(source, /value: "INTERRUPTED", label: "Interrompida"/);
assert.match(source, /exceptional_occurrence_type: form\.has_exceptional_occurrence \? \(form\.exceptional_occurrence_type \|\| ""\) : ""/);
assert.match(source, /exceptional_occurrence_impact: form\.has_exceptional_occurrence \? \(form\.exceptional_occurrence_impact \|\| ""\) : ""/);
assert.doesNotMatch(source, /value: "NONE"|value: "TOTAL"/);

console.log("TechnicalReportsPage.exceptionalOccurrence.test.mjs: OK");
