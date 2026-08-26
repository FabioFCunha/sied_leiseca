import assert from "node:assert/strict";
import fs from "node:fs";

const source = fs.readFileSync(new URL("./MobileReportFormPage.jsx", import.meta.url), "utf8");

assert.match(source, /exceptional_occurrence_impact === "NONE" \? "NO_IMPACT"/);
assert.match(source, /<option value="NO_IMPACT">Sem prejuízo<\/option>/);
assert.match(source, /<option value="PARTIAL">/);
assert.match(source, /<option value="INTERRUPTED">/);
assert.match(source, /has_exceptional_occurrence[\s\S]*?\? \(form\.exceptional_occurrence_impact === "NONE" \? "NO_IMPACT" : \(form\.exceptional_occurrence_impact \|\| ""\)\)\s*:\s*""/);

console.log("MobileReportFormPage.exceptionalOccurrence.test.mjs: OK");
