import assert from "node:assert/strict";

import {
  agreementIndicatorLabel,
  buildAgreementFieldsFromAgenda,
  deriveEducationAgreementIndicator,
  getDisplayedAgreementIndicator,
} from "./agreementIndicators.js";

assert.equal(deriveEducationAgreementIndicator("SCHOOL", "PUBLIC", "AGE_05_10"), "ESCOLINHA_NOTA_10");
assert.equal(deriveEducationAgreementIndicator("SCHOOL", "PUBLIC", "AGE_11_14"), "ESCOLINHA_NOTA_10");
assert.equal(deriveEducationAgreementIndicator("SCHOOL", "PUBLIC", "AGE_15_17"), "ESCOLA_NOTA_10");
assert.equal(deriveEducationAgreementIndicator("SCHOOL", "PUBLIC", "AGE_ADULT"), "ESCOLA_NOTA_10");
assert.equal(deriveEducationAgreementIndicator("SCHOOL", "PRIVATE", "AGE_05_10"), "");
assert.equal(agreementIndicatorLabel("ESCOLA_NOTA_10"), "Escola Nota 10");
assert.equal(agreementIndicatorLabel("ESCOLINHA_NOTA_10"), "Escolinha Nota 10");

assert.deepEqual(
  buildAgreementFieldsFromAgenda({
    requester_entity_type: "Instituição de Ensino Público",
    age_ranges: "acima de 18 anos - Adultos",
  }),
  {
    requester_entity_kind: "SCHOOL",
    requester_entity_nature: "PUBLIC",
    age_range: "AGE_ADULT",
  }
);

assert.equal(
  getDisplayedAgreementIndicator(
    {
      requester_entity_kind: "SCHOOL",
      requester_entity_nature: "PUBLIC",
      age_range: "AGE_11_14",
    },
    null,
    1
  ),
  "ESCOLINHA_NOTA_10"
);

assert.equal(
  getDisplayedAgreementIndicator(
    {},
    {
      requester_entity_type: "Instituição de Ensino Público",
      age_ranges: "15 - 17 anos (ensino médio)",
    },
    0
  ),
  "ESCOLA_NOTA_10"
);

console.log("agreementIndicators.test.mjs: OK");
