import assert from "node:assert/strict";

import { getValidatableActions, isActionMeaningful } from "./technicalReportsActionHelpers.js";

assert.equal(isActionMeaningful({ __userCreated: false }), false, "a??o vazia com __userCreated false n?o deve ser significativa");
assert.equal(isActionMeaningful({ source_id: "abc-123" }), false, "source_id isolado n?o deve tornar a a??o significativa");
assert.equal(isActionMeaningful({ __userCreated: true }), false, "a\u00e7\u00e3o criada manualmente vazia n\u00e3o deve ser significativa");
assert.equal(isActionMeaningful({ place_action: "Pra?a XV" }), true, "campo operacional preenchido deve tornar a a??o significativa");

const validatable = getValidatableActions([
  { __userCreated: false },
  { source_id: "abc-123" },
  { __userCreated: true },
  { __userCreated: true, place_action: "Pra\u00e7a XV" },
  { final_hour: "18:00" },
]);

assert.equal(validatable.length, 2, "somente duas a\u00e7\u00f5es devem ser validadas");
assert.deepEqual(validatable.map(({ index }) => index), [3, 4], "devem permanecer apenas as a\u00e7\u00f5es reais");

console.log("technicalReportsActionHelpers.test.mjs: OK");
