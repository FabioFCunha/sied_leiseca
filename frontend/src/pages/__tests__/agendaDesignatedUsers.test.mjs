import test from "node:test";
import assert from "node:assert/strict";

import {
  buildActiveOperationalUserOptions,
  filterDesignatedCandidates,
  setSelectedUserChecked,
} from "../agendaDesignatedUsers.js";

test("busca encontra usu?rio pelo nome e sele??o mant?m ID", () => {
  const options = buildActiveOperationalUserOptions({
    supports: [
      { source_id: "user:7", name: "Ronaldo Ferreira", role: "SUPPORT", team_name: "HOTEL", is_active: true },
    ],
  });

  const found = filterDesignatedCandidates(options, "ronaldo");
  assert.equal(found.length, 1);
  assert.equal(found[0].id, "7");

  const selected = setSelectedUserChecked([], found[0].id, true);
  assert.deepEqual(selected, ["7"]);
});

test("usu?rio selecionado n?o duplica", () => {
  assert.deepEqual(setSelectedUserChecked(["7"], "7", true), ["7"]);
});

test("usu?rios inativos ou n?o operacionais n?o aparecem na lista", () => {
  const options = buildActiveOperationalUserOptions({
    chiefs: [
      { source_id: "user:1", name: "Chefe Ativo", role: "SUPERVISOR", team_name: "HOTEL", is_active: true },
      { source_id: "user:2", name: "Chefe Inativo", role: "SUPERVISOR", team_name: "HOTEL", is_active: false },
      { source_id: "user:3", name: "Gestor", role: "MANAGER", team_name: "HOTEL", is_active: true },
    ],
    supports: [
      { source_id: "user:4", name: "Visitante", role: "VISITOR", team_name: "HOTEL", is_active: true },
    ],
  });

  assert.deepEqual(options.map((item) => item.id), ["1"]);
});

test("lookups operacionais entram por source_id e pesquisa encontra por equipe", () => {
  const options = buildActiveOperationalUserOptions({
    chiefs: [{ source_id: "user:11", name: "Eleni Martins", role: "SUPERVISOR", team_name: "HOTEL", is_active: true }],
    agents: [{ source_id: "user:12", name: "Aldo Silva", role: "USER", team_name: "GOLF", is_active: true }],
  });

  assert.deepEqual(options.map((item) => item.id), ["12", "11"]);

  const found = filterDesignatedCandidates(options, "hotel");
  assert.equal(found.length, 1);
  assert.equal(found[0].id, "11");
  assert.equal(found[0].role_label, "Chefe");
});
