import assert from "node:assert/strict";

import {
  agreementIndicatorLabel,
  buildAgreementFieldsFromAgenda,
  deriveAgreementIndicatorFromAgenda,
  deriveEducationAgreementIndicator,
  getDisplayedAgreementIndicator,
  normalizeRequesterEntityNature,
  normalizeRequesterEntityType,
} from "./agreementIndicators.js";

assert.equal(deriveEducationAgreementIndicator("SCHOOL", "PUBLIC", "AGE_05_10"), "ESCOLINHA_NOTA_10");
assert.equal(deriveEducationAgreementIndicator("SCHOOL", "PUBLIC", "AGE_11_14"), "ESCOLINHA_NOTA_10");
assert.equal(deriveEducationAgreementIndicator("SCHOOL", "PUBLIC", "AGE_15_17"), "ESCOLA_NOTA_10");
assert.equal(deriveEducationAgreementIndicator("SCHOOL", "PUBLIC", "AGE_ADULT"), "ESCOLA_NOTA_10");
assert.equal(deriveEducationAgreementIndicator("SCHOOL", "PRIVATE", "AGE_05_10"), "");
assert.equal(agreementIndicatorLabel("ESCOLA_NOTA_10"), "Escola Nota 10");
assert.equal(agreementIndicatorLabel("ESCOLINHA_NOTA_10"), "Escolinha Nota 10");
assert.equal(normalizeRequesterEntityNature("PUBLIC"), "PUBLIC");
assert.equal(normalizeRequesterEntityNature("Público"), "PUBLIC");
assert.equal(normalizeRequesterEntityNature("Pública"), "PUBLIC");
assert.equal(normalizeRequesterEntityNature("Publico"), "PUBLIC");
assert.equal(normalizeRequesterEntityNature("PRIVATE"), "PRIVATE");
assert.equal(normalizeRequesterEntityNature("Privado"), "PRIVATE");
assert.equal(normalizeRequesterEntityNature("Privada"), "PRIVATE");
assert.equal(normalizeRequesterEntityNature("Não se aplica"), "NOT_APPLICABLE");
assert.deepEqual(normalizeRequesterEntityType("SCHOOL PUBLIC"), { kind: "SCHOOL", nature: "PUBLIC" });
assert.deepEqual(normalizeRequesterEntityType("SCHOOL PRIVATE"), { kind: "SCHOOL", nature: "PRIVATE" });
assert.deepEqual(normalizeRequesterEntityType("Demanda Administrativa"), { kind: "ADMINISTRATIVE", nature: "NOT_APPLICABLE" });
assert.deepEqual(normalizeRequesterEntityType("Organização de Evento Público"), { kind: "EVENT_ORGANIZATION", nature: "PUBLIC" });
assert.deepEqual(normalizeRequesterEntityType("Organização de Evento Privado"), { kind: "EVENT_ORGANIZATION", nature: "PRIVATE" });

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

assert.deepEqual(
  buildAgreementFieldsFromAgenda({
    requester_entity_type: "SCHOOL PUBLIC",
    age_ranges: "acima de 18 anos - Adultos",
  }),
  {
    requester_entity_kind: "SCHOOL",
    requester_entity_nature: "PUBLIC",
    age_range: "AGE_ADULT",
  }
);

assert.equal(
  deriveAgreementIndicatorFromAgenda({
    requester_entity_type: "SCHOOL PUBLIC",
    age_ranges: "acima de 18 anos - Adultos",
  }),
  "ESCOLA_NOTA_10"
);

assert.equal(
  deriveAgreementIndicatorFromAgenda({
    requester_entity_type: "SCHOOL PRIVATE",
    age_ranges: "acima de 18 anos - Adultos",
  }),
  ""
);

assert.deepEqual(
  buildAgreementFieldsFromAgenda({
    requester_entity_type: "Demanda Administrativa",
    age_ranges: "15 - 17 anos (ensino médio)",
  }),
  {
    requester_entity_kind: "ADMINISTRATIVE",
    requester_entity_nature: "NOT_APPLICABLE",
    age_range: "AGE_15_17",
  }
);

assert.equal(
  deriveEducationAgreementIndicator("ADMINISTRATIVE", "NOT_APPLICABLE", "AGE_15_17"),
  ""
);

assert.deepEqual(
  buildAgreementFieldsFromAgenda({
    requester_entity_type: "SCHOOL",
    requester_entity_kind: "SCHOOL",
    requester_entity_nature: "PUBLIC",
    age_range: "AGE_15_17",
  }),
  {
    requester_entity_kind: "SCHOOL",
    requester_entity_nature: "PUBLIC",
    age_range: "AGE_15_17",
  }
);

assert.deepEqual(
  buildAgreementFieldsFromAgenda({
    requester_entity_type: "Instituição de Ensino Público",
    age_ranges: "05 - 10 anos (ensino fundamental - anos iniciais)",
  }),
  {
    requester_entity_kind: "SCHOOL",
    requester_entity_nature: "PUBLIC",
    age_range: "AGE_05_10",
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

assert.equal(
  getDisplayedAgreementIndicator(
    {},
    {
      requester_entity_kind: "SCHOOL",
      requester_entity_nature: "PUBLIC",
      age_range: "AGE_05_10",
    },
    0
  ),
  "ESCOLINHA_NOTA_10"
);

console.log("agreementIndicators.test.mjs: OK");
