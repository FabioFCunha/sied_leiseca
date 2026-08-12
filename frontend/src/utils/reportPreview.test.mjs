import assert from "node:assert/strict";

import { buildPreview, buildSupportsSummary, getSupports } from "./reportPreview.js";

const fernanda = "Fernanda Cristina Barreto Bustilho";
const ronaldo = "Ronaldo da Conceicao Ferreira Lima";

assert.deepEqual(getSupports({}, undefined), [], "sem apoio deve retornar lista vazia");

assert.deepEqual(
  getSupports({}, { support_1: fernanda }),
  [fernanda],
  "um apoio estruturado deve ser preservado"
);

assert.deepEqual(
  getSupports({}, { support_1: fernanda, support_2: ronaldo }),
  [fernanda, ronaldo],
  "dois apoios estruturados devem ser preservados"
);

assert.equal(
  buildSupportsSummary({}, { support_1: fernanda, support_2: ronaldo }),
  `${fernanda} - ${ronaldo}`,
  "Apoio 1 e Apoio 2 devem aparecer no resumo"
);

assert.deepEqual(
  getSupports(
    { education_agents: `Chefe respons\u00E1vel: Fulano\nAgentes: Agente Legitimo\nApoio 1: ${fernanda}\nApoio 2: ${ronaldo}` },
    undefined
  ),
  [fernanda, ronaldo],
  "relat\u00F3rios antigos devem usar fallback textual para recuperar ambos os apoios"
);

const preview = buildPreview(
  {
    agenda: 5649,
    agenda_title: "Operacao Hotel",
    operation_date: "2026-08-05",
    team: "HOTEL",
    education_agents: "Chefe respons\u00E1vel: Fulano\nAgentes: Agente Legitimo",
    actions: [],
    breathalyzers: "",
    cars: "",
    changes_general: "",
    general_observations: "",
    contact_received: "",
    occurrence_observation: "",
    lat: "",
    lng: "",
  },
  { support_1: fernanda, support_2: ronaldo },
  true
);

assert.match(preview, new RegExp(`Apoios: ${fernanda} - ${ronaldo}`), "o preview deve mostrar ambos os apoios");
assert.match(preview, /Agentes de educa\u00E7\u00E3o: Agente Legitimo/, "agentes devem permanecer intactos");
assert.doesNotMatch(preview, new RegExp(`Agentes de educa\u00E7\u00E3o: .*${ronaldo}`), "apoio n\u00E3o deve migrar para agentes");

console.log("reportPreview.test.mjs: OK");
