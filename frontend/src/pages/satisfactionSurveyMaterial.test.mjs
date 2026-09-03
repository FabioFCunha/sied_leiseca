import assert from "node:assert/strict";
import fs from "node:fs";

const source = fs.readFileSync(new URL("./SatisfactionSurveyPage.jsx", import.meta.url), "utf8");

assert.match(source, /Material distribuído durante a atividade\./);
assert.match(source, /value="NOT_APPLICABLE"/);
assert.match(source, /<span>Não se aplica<\/span>/);
assert.match(source, /value === "NOT_APPLICABLE" \? null/);

console.log("satisfactionSurveyMaterial.test.mjs: OK");
