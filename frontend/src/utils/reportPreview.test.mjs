import assert from "node:assert/strict";
import fs from "node:fs";

import {
  buildEducationAgentsText,
  buildOperationalResponsibility,
  buildPreview,
  buildSupportsSummary,
  getSupports,
} from "./reportPreview.js";

const chief = "Elisangela Cunha Monteiro";
const agent1 = "Fernanda Carlos da Silva";
const agent2 = "Leonardo de Velasco Silva";
const agent3 = "Thayrone Amaral de Souza";
const support1 = "Fernanda Cristina Barreto Bustilho";
const support2 = "Apoio Extra Valido";
const ronaldo = "Ronaldo da Conceicao Ferreira Lima";

const selectedAgenda = {
  support_1: support1,
  support_2: ronaldo,
  team_phone: "(21) 99999-0000",
  service_order_number: 2598,
};

const legacyReport = {
  agenda: 5649,
  agenda_title: "Operacao Hotel",
  operation_date: "2026-08-05",
  team: "HOTEL",
  education_agents: [
    `Chefe responsavel: ${chief}`,
    "Telefone do chefe/equipe: (21) 11111-1111",
    `Agentes: ${agent1} - ${agent2} - ${ronaldo} - ${agent3}`,
    `Apoio 1: ${support1}`,
    `Apoio 2: ${ronaldo}`,
  ].join("\n"),
  actions: [],
  breathalyzers: "",
  cars: "",
  changes_general: "",
  general_observations: "",
  contact_received: "",
  occurrence_observation: "",
  lat: "",
  lng: "",
};

const effectiveMembers = {
  chiefs: [{ id: 1, name: chief }],
  agents: [
    { id: 10, name: agent1 },
    { id: 11, name: agent2 },
    { id: 12, name: agent3 },
  ],
  supports: [{ id: 20, name: support1 }],
};

assert.deepEqual(getSupports({}, undefined), [], "sem apoio deve retornar lista vazia");

assert.deepEqual(
  getSupports({}, { support_1: support1 }),
  [support1],
  "um apoio estruturado deve ser preservado"
);

assert.deepEqual(
  getSupports({}, { support_1: support1, support_2: support2 }),
  [support1, support2],
  "dois apoios estruturados devem ser preservados"
);

assert.deepEqual(
  getSupports(
    { education_agents: `Chefe responsavel: Fulano\nAgentes: Agente Legitimo\nApoio 1: ${support1}\nApoio 2: ${ronaldo}` },
    undefined
  ),
  [support1, ronaldo],
  "relatorios antigos sem escala devem usar fallback textual"
);

assert.deepEqual(
  getSupports(
    { education_agents: `Apoio 1: ${support1}\nApoio 2: ${support2}` },
    { support_1: support1, support_2: support1 }
  ),
  [support1, support2],
  "fallback textual complementa apoio estruturado sem repetir nome"
);

const responsibility = buildOperationalResponsibility(legacyReport, selectedAgenda, effectiveMembers);
assert.equal(responsibility.chief, chief, "TEAM com escala usa o chefe efetivo");
assert.equal(
  responsibility.agentsSummary,
  `${agent1} - ${agent2} - ${agent3}`,
  "TEAM com escala usa apenas agentes efetivos"
);
assert.equal(responsibility.supportsSummary, support1, "TEAM com escala usa apenas apoios efetivos");
assert.doesNotMatch(responsibility.agentsSummary, new RegExp(ronaldo), "Ronaldo removido nao reaparece em agentes");
assert.doesNotMatch(responsibility.supportsSummary, new RegExp(ronaldo), "Ronaldo removido nao reaparece em apoios");

const legacyRemovedAgentReport = {
  ...legacyReport,
  education_agents: `Chefe responsavel: ${chief}\nAgentes: ${agent1} - ${ronaldo} - ${agent2}\nApoio 1: ${support1}`,
};
const effectiveMembersWithoutRemovedAgent = {
  ...effectiveMembers,
  agents: [
    { id: 10, name: agent1 },
    { id: 11, name: agent2 },
  ],
};
const removedAgentResponsibility = buildOperationalResponsibility(
  legacyRemovedAgentReport,
  selectedAgenda,
  effectiveMembersWithoutRemovedAgent
);
assert.match(removedAgentResponsibility.agentsSummary, new RegExp(agent1), "removed_agent: agente valido 1 permanece");
assert.match(removedAgentResponsibility.agentsSummary, new RegExp(agent2), "removed_agent: agente valido 2 permanece");
assert.doesNotMatch(removedAgentResponsibility.agentsSummary, new RegExp(ronaldo), "removed_agent: texto legado nao reintroduz Ronaldo");

const legacyRemovedSupportReport = {
  ...legacyReport,
  education_agents: `Chefe responsavel: ${chief}\nAgentes: ${agent1} - ${agent2}\nApoio 1: ${support1}\nApoio 2: ${ronaldo}`,
};
const effectiveMembersWithoutRemovedSupport = {
  ...effectiveMembers,
  supports: [{ id: 20, name: support1 }],
};

const emptyResolvedMembers = {
  context_resolved: true,
  chiefs: [],
  agents: [],
  supports: [],
};
const emptyContextText = buildEducationAgentsText(legacyReport, selectedAgenda, emptyResolvedMembers);
assert.doesNotMatch(emptyContextText, new RegExp(chief), "OS TEAM sem referencias nao usa chefe textual legado");
assert.doesNotMatch(emptyContextText, new RegExp(agent1), "OS TEAM sem referencias nao usa agentes textuais legados");
assert.doesNotMatch(emptyContextText, new RegExp(ronaldo), "OS TEAM sem referencias nao usa apoios textuais legados");
const removedSupportResponsibility = buildOperationalResponsibility(
  legacyRemovedSupportReport,
  selectedAgenda,
  effectiveMembersWithoutRemovedSupport
);
assert.equal(removedSupportResponsibility.supportsSummary, support1, "removed_support: apoio efetivo permanece");
assert.doesNotMatch(removedSupportResponsibility.supportsSummary, new RegExp(ronaldo), "removed_support: Ronaldo nao reaparece em apoios");

const rebuiltEducationAgents = buildEducationAgentsText(legacyReport, selectedAgenda, effectiveMembers);
assert.match(rebuiltEducationAgents, new RegExp(`Chefe respons[a|á]vel: ${chief}`), "texto do formulario traz o chefe efetivo");
assert.match(rebuiltEducationAgents, new RegExp(`Agentes: ${agent1} - ${agent2} - ${agent3}`), "texto do formulario traz agentes efetivos");
assert.match(rebuiltEducationAgents, new RegExp(`Apoio 1: ${support1}`), "texto do formulario traz apoio efetivo");
assert.doesNotMatch(rebuiltEducationAgents, new RegExp(ronaldo), "texto do formulario nao reintroduz Ronaldo");

const effectiveWithExtras = {
  ...effectiveMembers,
  agents: [...effectiveMembers.agents, { id: 13, name: "Agente Extra Valido" }],
  supports: [...effectiveMembers.supports, { id: 21, name: support2 }],
};
const responsibilityWithExtras = buildOperationalResponsibility(legacyReport, selectedAgenda, effectiveWithExtras);
assert.match(responsibilityWithExtras.agentsSummary, /Agente Extra Valido/, "extra agent continua aparecendo quando a escala efetiva o inclui");
assert.equal(
  responsibilityWithExtras.supportsSummary,
  `${support1} - ${support2}`,
  "extra support continua aparecendo quando a escala efetiva o inclui"
);

const effectiveWithMemberChange = {
  ...effectiveMembers,
  agents: [{ id: "swap-1", name: "Agente Substituto" }, { id: 11, name: agent2 }],
};
assert.equal(
  buildOperationalResponsibility(legacyReport, selectedAgenda, effectiveWithMemberChange).agentsSummary,
  `Agente Substituto - ${agent2}`,
  "member_changes continua refletido pela composicao efetiva"
);

const previewWithEffectiveMembers = buildPreview(legacyReport, selectedAgenda, true, effectiveMembers);
assert.match(previewWithEffectiveMembers, /Agentes de educa\u00E7\u00E3o: Fernanda Carlos da Silva - Leonardo de Velasco Silva - Thayrone Amaral de Souza/i, "preview usa agentes efetivos");
assert.match(previewWithEffectiveMembers, /Apoios: Fernanda Cristina Barreto Bustilho/i, "preview usa apoios efetivos");
assert.doesNotMatch(previewWithEffectiveMembers, new RegExp(`Apoios: .*${ronaldo}`), "preview nao mostra Ronaldo em apoios");
assert.doesNotMatch(previewWithEffectiveMembers, new RegExp(`Agentes de educa\\u00E7\\u00E3o: .*${ronaldo}`, "i"), "preview nao mostra Ronaldo em agentes");

const legacyPreview = buildPreview(
  {
    ...legacyReport,
    education_agents: `Chefe responsavel: Fulano\nAgentes: Agente Legado\nApoio 1: ${support1}\nApoio 2: ${ronaldo}`,
  },
  { support_1: support1, support_2: ronaldo },
  true
);
assert.match(legacyPreview, new RegExp(`Apoios: ${support1} - ${ronaldo}`), "sem ShiftSchedule o preview preserva o fallback legado");

const designatedPreview = buildPreview(
  {
    ...legacyReport,
    education_agents: `Chefe responsavel: Fulano\nAgentes: Participante Designado\nApoio 1: ${support1}`,
  },
  { service_order_mode: "DESIGNATED", support_1: support1 },
  true
);
assert.match(designatedPreview, /Participante Designado/, "DESIGNATED permanece inalterado sem efetivo de escala");

assert.equal(
  buildSupportsSummary(
    { education_agents: `Apoio 1: ${support1}\nApoio 2: ${support2}\nApoio 3: ${support2}` },
    { support_1: support1, support_2: support1 }
  ),
  `${support1} - ${support2}`,
  "duplicidade de apoios nao gera nome repetido"
);

const previewOldSignature = buildPreview(legacyReport, true);
assert.match(previewOldSignature, /Protocolo: #5649/, "buildPreview continua compativel com a assinatura antiga");

const pdfSource = fs.readFileSync(new URL("./reportPdfGenerator.js", import.meta.url), "utf8");
const pageSource = fs.readFileSync(new URL("../pages/TechnicalReportsPage.jsx", import.meta.url), "utf8");
assert.match(pdfSource, /buildSupportsSummary/, "PDF continua consumindo helper compartilhado de apoios");
assert.match(pageSource, /generateTechnicalReportPdf\(form, selectedAgendaForPreview, attendanceForm, true, showEstimatedPublic\)/, "preview e PDF recebem a mesma agenda efetiva");
assert.match(pageSource, /buildPreview\(form, selectedAgendaForPreview, showEstimatedPublic, membersForPresentation\)/, "preview usa a mesma composicao efetiva da escala");

console.log("reportPreview.test.mjs: OK");
