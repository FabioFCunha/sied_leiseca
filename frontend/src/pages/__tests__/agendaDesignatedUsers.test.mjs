import test from "node:test";
import assert from "node:assert/strict";

import {
  buildActiveOperationalUserOptions,
  buildAvailableAgents,
  buildServiceOrderAgentOptions,
  buildSupportOptions,
  filterDesignatedCandidates,
  normalizeSelectedAgentIds,
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

test("slot vazio nao entra nos IDs selecionados e nao bloqueia agentes disponiveis", () => {
  const selectedAgents = [
    { id: 10, name: "Diogo" },
    { id: 20, name: "Leonardo" },
    null,
    "",
    undefined,
    { id: 30, name: "Marcio" },
  ];
  const allAgents = [
    { id: 10, name: "Diogo" },
    { id: 20, name: "Leonardo" },
    { id: 30, name: "Marcio" },
    { id: 40, name: "Agente Disponivel" },
  ];

  assert.deepEqual(normalizeSelectedAgentIds(selectedAgents), ["10", "20", "30"]);
  assert.deepEqual(buildAvailableAgents(allAgents, selectedAgents).map((agent) => agent.id), [40]);
});

test("agente ja selecionado nao aparece duplicado na lista disponivel", () => {
  const allAgents = [
    { id: 1, name: "Agente Um" },
    { id: 2, name: "Agente Dois" },
  ];

  assert.deepEqual(buildAvailableAgents(allAgents, [{ id: 1, name: "Agente Um" }]).map((agent) => agent.id), [2]);
});

test("IDs numericos e strings sao tratados como equivalentes", () => {
  const allAgents = [
    { id: 10, name: "Agente Numerico" },
    { id: "20", name: "Agente String" },
    { id: 30, name: "Agente Livre" },
  ];

  const available = buildAvailableAgents(allAgents, ["10", { id: 20, name: "Agente String" }]);

  assert.deepEqual(available.map((agent) => String(agent.id)), ["30"]);
});

test("agente removido volta a aparecer como disponivel", () => {
  const allAgents = [
    { id: 1, name: "Agente Um" },
    { id: 2, name: "Agente Dois" },
    { id: 3, name: "Agente Tres" },
  ];
  const selectedBeforeRemoval = [1, 2];
  const selectedAfterRemoval = selectedBeforeRemoval.filter((id) => String(id) !== "2");

  assert.deepEqual(buildAvailableAgents(allAgents, selectedBeforeRemoval).map((agent) => agent.id), [3]);
  assert.deepEqual(buildAvailableAgents(allAgents, selectedAfterRemoval).map((agent) => agent.id), [2, 3]);
});

test("apoios permanecem elegiveis na montagem operacional", () => {
  const options = buildActiveOperationalUserOptions({
    supports: [
      { source_id: "user:50", name: "Apoio Ativo", role: "SUPPORT", team_name: "HOTEL", is_active: true },
    ],
    agents: [
      { source_id: "user:60", name: "Agente Ativo", role: "USER", team_name: "HOTEL", is_active: true },
    ],
  });

  assert.deepEqual(options.map((item) => [item.id, item.role_label]), [["60", "Agente"], ["50", "Apoio"]]);
});
test("OS da equipe ECHO lista agentes ativos de HOTEL e SAO GONCALO", () => {
  const allAgents = buildServiceOrderAgentOptions([
    { id: 1, name: "Agente Echo", role: "AGENTE", team_name: "ECHO", is_active: true },
    { id: 2, name: "Agente Hotel", role: "AGENTE", team_name: "HOTEL", is_active: true },
    { id: 3, name: "Agente Sao Goncalo", role: "AGENTE", team_name: "SAO GONCALO", is_active: true },
  ]);

  assert.deepEqual(buildAvailableAgents(allAgents, []).map((agent) => agent.team_name), ["ECHO", "HOTEL", "SAO GONCALO"]);
});

test("agente ativo de outra equipe selecionado nao duplica e removido volta", () => {
  const allAgents = buildServiceOrderAgentOptions([
    { id: 1, name: "Agente Echo", role: "AGENTE", team_name: "ECHO", is_active: true },
    { id: 2, name: "Agente Hotel", role: "AGENTE", team_name: "HOTEL", is_active: true },
  ]);

  assert.deepEqual(buildAvailableAgents(allAgents, ["2"]).map((agent) => agent.id), [1]);
  assert.deepEqual(buildAvailableAgents(allAgents, []).map((agent) => agent.id), [1, 2]);
});

test("apoio ativo de outra equipe aparece em Apoio 1 e Apoio 2", () => {
  const supports = [
    { id: 10, name: "Apoio Hotel", role: "APOIO", team_name: "HOTEL", is_active: true },
    { id: 20, name: "Apoio Niteroi", role: "APOIO", team_name: "NITEROI", is_active: true },
  ];

  assert.deepEqual(buildSupportOptions(supports, [], "").map((support) => support.team_name), ["HOTEL", "NITEROI"]);
  assert.deepEqual(buildSupportOptions(supports, [], "").map((support) => support.id), [10, 20]);
});

test("apoio escolhido em Apoio 1 nao aparece em Apoio 2 mas permanece no proprio campo", () => {
  const supports = [
    { id: 10, name: "Apoio Hotel", role: "APOIO", team_name: "HOTEL", is_active: true },
    { id: 20, name: "Apoio Niteroi", role: "APOIO", team_name: "NITEROI", is_active: true },
  ];

  assert.deepEqual(buildSupportOptions(supports, [10, ""], 10).map((support) => support.id), [10, 20]);
  assert.deepEqual(buildSupportOptions(supports, [10, ""], "").map((support) => support.id), [20]);
});

test("usuarios inativos e funcoes erradas nao aparecem nos candidatos da OS", () => {
  const agents = buildServiceOrderAgentOptions([
    { id: 1, name: "Agente Ativo", role: "AGENTE", team_name: "ECHO", is_active: true },
    { id: 2, name: "Agente Inativo", role: "AGENTE", team_name: "HOTEL", is_active: false },
    { id: 3, name: "Apoio Indevido", role: "APOIO", team_name: "HOTEL", is_active: true },
  ]);
  const supports = buildSupportOptions([
    { id: 4, name: "Apoio Ativo", role: "APOIO", team_name: "HOTEL", is_active: true },
    { id: 5, name: "Apoio Inativo", role: "APOIO", team_name: "HOTEL", is_active: false },
    { id: 6, name: "Agente Indevido", role: "AGENTE", team_name: "ECHO", is_active: true },
  ]);

  assert.deepEqual(agents.map((agent) => agent.id), [1]);
  assert.deepEqual(supports.map((support) => support.id), [4]);
});
