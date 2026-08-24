import assert from "node:assert/strict";

import {
  filterOperationalEducationActionTypes,
  getAgendaOperationalActionTypeName,
} from "./actionTypeOptions.js";

const actionTypes = [
  { name: "Palestra Escola", is_active: false, category: "LECTURE" },
  { name: "Palestra Escola Pública", is_active: true, category: "LECTURE" },
  { name: "Palestra Escola Privada", is_active: true, category: "LECTURE" },
  { name: "Palestra Empresa", is_active: true, category: "LECTURE" },
  { name: "Ação Educativa", is_active: true, category: "EDUCATIONAL_ACTION" },
  { name: "Escola Nota 10", is_active: true, category: "PROGRAM_INDICATOR" },
  { name: "Escolinha Nota 10", is_active: true, category: "PROGRAM_INDICATOR" },
  { name: "Praia", is_active: true, category: "STREET_ACTION" },
  { name: "Outros", is_active: true, category: "OTHER" },
  { name: "Sem categoria", is_active: true, category: null },
];

const options = filterOperationalEducationActionTypes(actionTypes).map((item) => item.name);

assert.deepEqual(options, [
  "Palestra Escola Pública",
  "Palestra Escola Privada",
  "Palestra Empresa",
  "Ação Educativa",
]);
assert.equal(getAgendaOperationalActionTypeName({ action_type: "Palestra Escola Pública" }, actionTypes), "Palestra Escola Pública");
assert.equal(getAgendaOperationalActionTypeName({ action_type: "Palestra Escola" }, actionTypes), "");
assert.equal(getAgendaOperationalActionTypeName({ action_type: "Ação de educação/conscientização" }, actionTypes), "Ação Educativa");
assert.equal(getAgendaOperationalActionTypeName({ action_type: "Ação de educação/conscientização" }, actionTypes.filter((item) => item.name !== "Ação Educativa")), "");

console.log("actionTypeOptions.test.mjs: OK");
