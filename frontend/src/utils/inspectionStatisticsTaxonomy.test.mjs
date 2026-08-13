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
    approach_plus_reconductor: 103,
    approach: 93,
    reconductor: 10,
    refusal: 5,
    fined: 44,
    towed: 0,
    cnh_collected: 1,
    passive_tests_performed: 7,
    removal_resolutions: 270,
    criminal_occurrences: 2,
    driving_canceled_license: 1,
  },

  driver: {
    reconductor: 10,
    recondutors_licensed: 8,
    cnh_collected: 1,
    historical_cnh_retained: null,
    historical_passive_tests: null,
  },

  alcohol_results: {
    four_ml: 88,
    thirtythree_ml: 0,
    thirtyfour_ml: 0,
    refusal: 5,
    arrests_means_evidence: 0,
  },

  taxi: {
    approached: 15,
    illegal: 2,
  },

  occurrences: {
    planned_actions: 4,
    historical_deliberations: 270,
    rain: 1,
    external_occurrence: 2,
    public_security_occurrence: 3,
    criminal_occurrences: 2,
    operations: 3,
    driving_canceled_license: 1,
  },

  coverage: {
    "summary.approach_plus_reconductor": "DIRECT",
    "taxi.approached": "HISTORICAL_ONLY",
    "taxi.illegal": "HISTORICAL_ONLY",
  },
};

const cards = buildInspectionExecutiveCards(
  dashboard.summary
);

assert.equal(
  cards.length,
  5,
  "a tela deve manter os cinco cards executivos principais"
);

assert.deepEqual(
  cards.map((card) => card.key),
  [
    "operations",
    "approach",
    "refusal",
    "fined",
    "cnh_collected",
  ],
  "os cinco cards executivos devem seguir a ordem institucional definida"
);

assert.deepEqual(
  cards.map((card) => card.label),
  [
    "Fiscalizações",
    "Abordados",
    "Recusas",
    "Multados",
    "CNH Recolhidas",
  ],
  "os cards executivos devem usar os nomes principais da Fiscalização"
);

assert.equal(
  cards.find((card) => card.key === "operations").value,
  3,
  "Fiscalizações deve usar summary.operations"
);

assert.equal(
  cards.find((card) => card.key === "approach").value,
  93,
  "Abordados deve usar summary.approach sem somar recondutor"
);

assert.equal(
  cards.find((card) => card.key === "cnh_collected").value,
  1,
  "CNH Recolhidas deve usar summary.cnh_collected"
);

const categories =
  buildInspectionStatisticsTaxonomy(dashboard);

assert.deepEqual(
  categories.map((category) => category.title),
  [
    "VEÍCULOS",
    "MOTORISTA",
    "RESULTADO ETILÔMETRO",
    "TÁXI",
    "ACONTECIMENTOS",
  ],
  "a taxonomia oficial deve manter as cinco categorias esperadas"
);

const driverCategory = categories.find(
  (category) => category.key === "driver"
);

assert.ok(
  driverCategory,
  "a categoria MOTORISTA deve existir"
);

const cnhItem = driverCategory.items.find(
  (item) => item.key === "cnh_collected"
);

assert.ok(
  cnhItem,
  "CNH Recolhidas deve permanecer dentro de MOTORISTA"
);

assert.equal(
  cnhItem.status,
  TAXONOMY_STATUS.MAPPED,
  "CNH Recolhidas deve permanecer mapeada"
);

assert.equal(
  cnhItem.value,
  1,
  "CNH Recolhidas deve usar o valor consolidado disponível"
);

const vehiclesCategory = categories.find(
  (category) => category.key === "vehicles"
);

assert.equal(
  vehiclesCategory.items.find(
    (item) => item.key === "approached_reconductor"
  ).status,
  TAXONOMY_STATUS.MAPPED,
  "Abordados + Recondutor deve ficar mapeado quando a cobertura for direta"
);

assert.equal(
  vehiclesCategory.items.find(
    (item) => item.key === "approached_reconductor"
  ).value,
  103,
  "Abordados + Recondutor deve usar o valor unificado entregue pela API"
);

const taxiCategory = categories.find(
  (category) => category.key === "taxi"
);

assert.ok(
  taxiCategory,
  "a categoria TÁXI deve existir"
);

assert.ok(
  taxiCategory.items.every(
    (item) => item.status === TAXONOMY_STATUS.MAPPED
  ),
  "os indicadores de táxi devem estar mapeados quando o backend fornecer os campos históricos"
);

assert.equal(
  taxiCategory.items.find(
    (item) => item.key === "taxi_approached"
  ).value,
  15,
  "Táxis abordados deve consumir taxi.approached"
);

assert.equal(
  taxiCategory.items.find(
    (item) => item.key === "taxi_pirate"
  ).value,
  2,
  "Táxi pirata deve consumir taxi.illegal"
);

const eventsCategory = categories.find(
  (category) => category.key === "events"
);

assert.ok(
  eventsCategory,
  "a categoria ACONTECIMENTOS deve existir"
);

assert.equal(
  eventsCategory.items.find(
    (item) => item.key === "planned_actions"
  ).status,
  TAXONOMY_STATUS.MAPPED,
  "Ações planejadas deve estar mapeada pela base histórica consolidada"
);

assert.equal(
  eventsCategory.items.find(
    (item) => item.key === "rain"
  ).value,
  1,
  "Chuva deve consumir occurrences.rain"
);

assert.equal(
  eventsCategory.items.find(
    (item) =>
      item.key === "public_security_occurrence"
  ).value,
  3,
  "Ocorrência de segurança pública deve consumir o campo histórico específico"
);

assert.equal(
  eventsCategory.items.find(
    (item) => item.key === "operations"
  ).status,
  TAXONOMY_STATUS.MAPPED,
  "Operações deve continuar mapeado em acontecimentos"
);

const partialDashboard = {
  ...dashboard,
  coverage: {
    ...dashboard.coverage,
    "summary.approach_plus_reconductor": "PARTIAL",
  },
  summary: {
    ...dashboard.summary,
    approach_plus_reconductor: null,
  },
};

const partialCategories =
  buildInspectionStatisticsTaxonomy(
    partialDashboard
  );

const partialVehicles =
  partialCategories.find(
    (category) => category.key === "vehicles"
  );

assert.equal(
  partialVehicles.items.find(
    (item) => item.key === "approached_reconductor"
  ).status,
  TAXONOMY_STATUS.PARTIAL,
  "Abordados + Recondutor deve permanecer parcial em períodos cruzados incompatíveis"
);

assert.equal(
  partialVehicles.items.find(
    (item) => item.key === "approached_reconductor"
  ).value,
  null,
  "Abordados + Recondutor deve permanecer nulo em período cruzado incompatível"
);

console.log(
  "inspectionStatisticsTaxonomy.test.mjs: OK"
);