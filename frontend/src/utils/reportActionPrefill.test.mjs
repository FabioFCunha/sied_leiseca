import assert from "node:assert/strict";

import { applyBlankActionPrefill, buildFirstActionAgendaPrefill } from "./reportActionPrefill.js";

const streetAgenda = {
  requester_entity_type: "6",
  institution_location: "Campo de São Bento",
  address: "Rua Gavião Peixoto, nº 0",
  neighborhood: "Icaraí",
  city: "Niterói",
  state: "RJ",
  start_time: "09:00:00",
  end_time: "12:00:00",
  street_action_details: [{ type: "Praças/Parques Públicos" }],
  requester_entity_nature: "Publico",
  age_ranges: "15 - 17 anos (ensino médio)",
  quantity: 99,
};

assert.deepEqual(
  buildFirstActionAgendaPrefill(streetAgenda),
  {
    action_mode: "STREET",
    place_action: "Rua Gavião Peixoto, nº 0, Icaraí, Niterói, RJ",
    institution_name: "Campo de São Bento",
    type_action: "Praças/Parques Públicos",
    type_audience: "",
    requester_entity_kind: "",
    requester_entity_nature: "PUBLIC",
    age_range: "AGE_15_17",
    start_time: "09:00",
    final_hour: "12:00",
    approach: "",
  },
  "ação de rua herda apenas os dados estruturados da OS e deixa abordagens vazias"
);

assert.equal(
  buildFirstActionAgendaPrefill({ ...streetAgenda, requester_entity_nature: "" }).requester_entity_nature,
  "",
  "não inventa Público/Privado quando a API não fornece o campo"
);

assert.equal(
  buildFirstActionAgendaPrefill({
    ...streetAgenda,
    requester_entity_type: "Ação de Rua Público",
    action_type_ref: "6",
    requester_entity_nature: "",
  }).requester_entity_nature,
  "",
  "não deduz Público/Privado do texto do tipo de entidade"
);

const schoolPrefill = buildFirstActionAgendaPrefill({
  requester_entity_type: "Instituição de Ensino Público",
  institution_location: "Escola Modelo",
  address: "Rua A",
  start_time: "08:30:00",
  end_time: "10:00:00",
  quantity: 120,
  age_ranges: "05 - 10 anos (ensino fundamental - anos iniciais)",
}, [{ name: "Palestra Escola" }]);

assert.equal(schoolPrefill.action_mode, "LECTURE");
assert.equal(schoolPrefill.institution_name, "Escola Modelo");
assert.equal(schoolPrefill.approach, 120);
assert.equal(schoolPrefill.requester_entity_kind, "SCHOOL");
assert.equal(schoolPrefill.requester_entity_nature, "PUBLIC");
assert.equal(schoolPrefill.age_range, "AGE_05_10");

assert.deepEqual(
  applyBlankActionPrefill(
    { institution_name: "Local editado", requester_entity_nature: "PRIVATE", approach: 0 },
    buildFirstActionAgendaPrefill(streetAgenda)
  ),
  {
    ...buildFirstActionAgendaPrefill(streetAgenda),
    institution_name: "Local editado",
    requester_entity_nature: "PRIVATE",
    approach: 0,
  },
  "rascunho e edições do chefe têm precedência sobre o pré-preenchimento"
);

console.log("reportActionPrefill.test.mjs: OK");
