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

  horus_cards: {
    stolen_recovered_vehicles: {
      value: 466,
    },
    passive_tests_performed: {
      value: 7,
    },
    reconductor: {
      value: 10,
    },
    four_ml: {
      value: 88,
    },
    thirtythree_ml: {
      value: 0,
    },
    thirtyfour_ml: {
      value: 0,
    },
    arrests_means_evidence: {
      value: 0,
    },
    removal_resolutions: {
      value: 270,
    },
    rain: {
      value: 1,
    },
    criminal_occurrences: {
      value: 2,
    },
    art307: {
      value: 0,
    },
    driving_canceled_license: {
      value: 1,
    },
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
    "Abordados e Recondutores",
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
    "SEGURANÇA PÚBLICA / CRIMINAL",
  ],
  "a taxonomia oficial deve manter as quatro categorias esperadas"
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

const fakeCnhItem = driverCategory.items.find(
  (item) => item.key === "fake_cnh"
);

const suspendedCnhItem = driverCategory.items.find(
  (item) => item.key === "suspended_cnh"
);

const canceledCnhItem = driverCategory.items.find(
  (item) => item.key === "canceled_cnh"
);

assert.ok(
  fakeCnhItem,
  "CNH falsa deve permanecer dentro de MOTORISTA"
);

assert.ok(
  suspendedCnhItem,
  "CNH suspensa deve permanecer dentro de MOTORISTA"
);

assert.ok(
  canceledCnhItem,
  "CNH cassada deve permanecer dentro de MOTORISTA"
);

const vehiclesCategory = categories.find(
  (category) => category.key === "vehicles"
);

const securityCategory = categories.find(
  (category) => category.key === "public_security"
);

assert.ok(
  securityCategory,
  "a categoria SEGURAN\u00c7A P\u00daBLICA / CRIMINAL deve existir"
);

assert.equal(
  categories.some(
    (category) => category.key === "taxi"
  ),
  false,
  "a categoria T\u00c1XI n\u00e3o deve mais ser exibida"
);

assert.deepEqual(
  securityCategory.items.map((item) => item.key),
  [
    "public_security_total",
    "fugitives",
    "flagrante",
    "simulacrum",
    "weapons",
    "recovered_vehicles",
    "narcotics",
    "bribery",
    "art311",
    "art306",
  ],
  "o bloco de Seguran\u00e7a P\u00fablica / Criminal deve manter os indicadores definidos"
);

assert.equal(
  securityCategory.items.find(
    (item) => item.key === "public_security_total"
  ).label,
  "Total de ocorr\u00eancias",
  "o bloco deve possuir Total de ocorr\u00eancias"
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
    (item) => item.key === "operations"
  ).status,
  TAXONOMY_STATUS.MAPPED,
  "Operações deve continuar mapeado em acontecimentos"
);

assert.equal(
  eventsCategory.items.some(
    (item) => item.key === "public_security_occurrence"
  ),
  false,
  "Ocorrencia de seguranca publica nao deve permanecer em ACONTECIMENTOS"
);

assert.equal(
  eventsCategory.items.some(
    (item) => item.key === "canceled_cnh"
  ),
  false,
  "CNH cassada nao deve permanecer em ACONTECIMENTOS"
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

console.log(
  "inspectionStatisticsTaxonomy.test.mjs: OK"
);