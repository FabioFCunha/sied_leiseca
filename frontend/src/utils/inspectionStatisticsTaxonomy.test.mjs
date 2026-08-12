import assert from "node:assert/strict";

import {
  TAXONOMY_STATUS,
  buildInspectionExecutiveCards,
  buildInspectionStatisticsTaxonomy,
} from "./inspectionStatisticsTaxonomy.js";

const dashboard = {
  summary: {
    homologated_reports: 2,
    operations: 3,
    approach: 93,
    reconductor: 10,
    refusal: 5,
    fined: 44,
    towed: 0,
    cnh_collected: 1,
    four_ml: 88,
    thirtythree_ml: 0,
    thirtyfour_ml: 0,
    arrests_means_evidence: 0,
    removal_resolutions: 270,
    driving_canceled_license: 1,
  },
};

const cards = buildInspectionExecutiveCards(dashboard.summary);
assert.equal(cards.length, 4, "a tela deve manter no maximo quatro cards executivos");
assert.deepEqual(
  cards.map((card) => card.key),
  ["homologated_reports", "operations", "approach", "fined"],
  "os quatro cards executivos devem seguir a ordem institucional definida"
);

const categories = buildInspectionStatisticsTaxonomy(dashboard);
assert.deepEqual(
  categories.map((category) => category.title),
  ["VEÍCULOS", "MOTORISTA", "RESULTADO ETILÔMETRO", "TÁXI", "ACONTECIMENTOS"],
  "a taxonomia oficial deve manter as cinco categorias esperadas"
);

const driverCategory = categories.find((category) => category.key === "driver");
assert.ok(driverCategory, "a categoria MOTORISTA deve existir");
assert.ok(
  driverCategory.items.some((item) => item.label === "CNH Recolhidas" && item.field === "cnh_collected"),
  "CNH Recolhidas deve permanecer dentro de MOTORISTA"
);

const vehiclesCategory = categories.find((category) => category.key === "vehicles");
assert.equal(
  vehiclesCategory.items.find((item) => item.key === "approached_reconductor").status,
  TAXONOMY_STATUS.PARTIAL,
  "Abordados + Recondutor deve permanecer parcial ate definicao institucional"
);
assert.equal(
  vehiclesCategory.items.find((item) => item.key === "approached_reconductor").value,
  "93 + 10",
  "o bloco parcial deve expor a composicao atual sem inventar soma consolidada"
);

const taxiCategory = categories.find((category) => category.key === "taxi");
assert.ok(
  taxiCategory.items.every((item) => item.status === TAXONOMY_STATUS.UNMAPPED),
  "os indicadores de taxi devem permanecer nao mapeados sem equivalencia comprovada"
);

const eventsCategory = categories.find((category) => category.key === "events");
assert.equal(
  eventsCategory.items.find((item) => item.key === "operations").status,
  TAXONOMY_STATUS.MAPPED,
  "Operacoes deve continuar mapeado em acontecimentos"
);
assert.equal(
  eventsCategory.items.find((item) => item.key === "deliberations").status,
  TAXONOMY_STATUS.PARTIAL,
  "Deliberacoes deve permanecer parcial enquanto o modelo atual cobre apenas remocoes"
);
assert.equal(
  eventsCategory.items.find((item) => item.key === "public_security_occurrence").status,
  TAXONOMY_STATUS.NEEDS_DEFINITION,
  "Ocorrencia de seguranca publica nao deve ser equiparada automaticamente a ocorrencia criminal"
);

console.log("inspectionStatisticsTaxonomy.test.mjs: OK");
