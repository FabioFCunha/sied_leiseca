import assert from "node:assert/strict";
import test from "node:test";

import {
  getAgendaAgentNames,
  getAgendaChiefNames,
  getAgendaEffectiveStaff,
  getAgendaStaffWarning,
  getAgendaSupportNames,
} from "./agendaStaff.js";

test("getAgendaEffectiveStaff prioritizes effective_staff from API", () => {
  const agenda = {
    service_order_mode: "TEAM",
    effective_staff: {
      chiefs: [{ name: "Chefe Escala" }],
      agents: [{ name: "Agente Escala" }, { name: "Agente Escala" }],
      supports: [{ name: "Apoio Escala" }],
      manual: [],
    },
    chief_name: "Chefe Legado",
    agents: "Agente Legado",
  };

  assert.equal(getAgendaChiefNames(agenda).join(", "), "Chefe Escala");
  assert.equal(getAgendaAgentNames(agenda).join(", "), "Agente Escala");
  assert.equal(getAgendaSupportNames(agenda).join(", "), "Apoio Escala");
});

test("getAgendaEffectiveStaff falls back to legacy agenda fields when needed", () => {
  const agenda = {
    service_order_mode: "TEAM",
    chief_ref_name: "Chefe Legado",
    agents: "Agente Um - Agente Dois",
    support_1_ref_name: "Apoio Um",
    support_2: "Apoio Dois",
    effective_staff_warning: "Efetivo não localizado na Escala para esta data.",
  };

  assert.equal(getAgendaEffectiveStaff(agenda).chiefs.length, 1);
  assert.deepEqual(getAgendaAgentNames(agenda), ["Agente Um", "Agente Dois"]);
  assert.deepEqual(getAgendaSupportNames(agenda), ["Apoio Um", "Apoio Dois"]);
  assert.equal(getAgendaStaffWarning(agenda), "Efetivo não localizado na Escala para esta data.");
});

test("DESIGNATED does not expose team staff lists", () => {
  const agenda = {
    service_order_mode: "DESIGNATED",
    effective_staff: {
      chiefs: [{ name: "Nao deve aparecer" }],
      agents: [{ name: "Nao deve aparecer" }],
      supports: [{ name: "Nao deve aparecer" }],
    },
  };

  assert.deepEqual(getAgendaEffectiveStaff(agenda), {
    chiefs: [],
    agents: [],
    supports: [],
    manual: [],
  });
});
