export const TAXONOMY_STATUS = {
  MAPPED: "MAPEADO",
  PARTIAL: "PARCIAL",
  UNMAPPED: "NÃO MAPEADO",
  NEEDS_DEFINITION: "PRECISA DEFINIÇÃO",
};

const isPresent = (value) =>
  value !== null && value !== undefined;

function formatMetricValue(value) {
  return isPresent(value) ? value : null;
}

function firstPresent(...values) {
  for (const value of values) {
    if (isPresent(value)) {
      return value;
    }
  }

  return null;
}

export function buildInspectionExecutiveCards(summary = {}) {
  return [
    {
      key: "homologated_reports",
      label: "Relatórios homologados",
      value: summary.homologated_reports,
    },
    {
      key: "operations",
      label: "Operações",
      value: summary.operations,
    },
    {
      key: "approach",
      label: "Abordados + Recondutor",
      value: summary.approach_plus_reconductor,
    },
    {
      key: "fined",
      label: "Multados",
      value: summary.fined,
    },
  ];
}

export function buildInspectionStatisticsTaxonomy(
  dashboard = {}
) {
  const summary = dashboard.summary || {};
  const driver = dashboard.driver || {};
  const alcohol = dashboard.alcohol_results || {};
  const taxi = dashboard.taxi || {};
  const occurrences = dashboard.occurrences || {};
  const coverage = dashboard.coverage || {};

  return [
    {
      key: "vehicles",
      title: "VEÍCULOS",
      subtitle:
        "Indicadores relacionados à abordagem de veículos e às medidas adotadas nas operações.",
      items: [
        {
          key: "approached_reconductor",
          label: "Abordados + Recondutor",
          status:
            coverage[
              "summary.approach_plus_reconductor"
            ] === "PARTIAL"
              ? TAXONOMY_STATUS.PARTIAL
              : TAXONOMY_STATUS.MAPPED,
          value: formatMetricValue(
            summary.approach_plus_reconductor
          ),
          field: "summary.approach_plus_reconductor",
          note:
            coverage[
              "summary.approach_plus_reconductor"
            ] === "PARTIAL"
              ? "Indicador possui conceitos distintos entre a base histórica consolidada e a produção operacional; não é somado automaticamente em períodos cruzados."
              : "Indicador consolidado conforme a fonte utilizada no período selecionado.",
        },
        {
          key: "fined",
          label: "Multados",
          status: TAXONOMY_STATUS.MAPPED,
          value: formatMetricValue(summary.fined),
          field: "summary.fined",
          note:
            "Indicador consolidado entre histórico e produção operacional quando disponível.",
        },
        {
          key: "towed",
          label: "Rebocados",
          status: TAXONOMY_STATUS.MAPPED,
          value: formatMetricValue(summary.towed),
          field: "summary.towed",
          note:
            "Indicador consolidado entre histórico e produção operacional quando disponível.",
        },
      ],
    },

    {
      key: "driver",
      title: "MOTORISTA",
      subtitle:
        "Indicadores relacionados ao condutor, habilitação, testes e medidas administrativas.",
      items: [
        {
          key: "breathalyzer_test",
          label: "Teste com etilômetro",
          status: TAXONOMY_STATUS.PARTIAL,
          value: formatMetricValue(
            summary.passive_tests_performed
          ),
          field:
            "summary.passive_tests_performed",
          note:
            "O SIED possui o quantitativo de testes passivos. A nomenclatura histórica de teste com etilômetro pode representar conceito mais amplo.",
        },
        {
          key: "licensed_reconductors",
          label: "Recondutores habilitados",
          status: TAXONOMY_STATUS.PARTIAL,
          value: formatMetricValue(
            firstPresent(
              driver.reconductors_licensed,
              driver.reconductor
            )
          ),
          field:
            "driver.reconductors_licensed / driver.reconductor",
          note:
            "A base histórica possui recondutores habilitados. No operacional existe o campo recondutor, mantido separado por diferença de definição.",
        },
        {
          key: "refusal",
          label: "Recusa ao teste",
          status: TAXONOMY_STATUS.MAPPED,
          value: formatMetricValue(summary.refusal),
          field: "summary.refusal",
          note:
            "Indicador consolidado de recusas ao teste.",
        },
        {
          key: "cnh_collected",
          label: "CNH Recolhidas",
          status: TAXONOMY_STATUS.MAPPED,
          value: formatMetricValue(
            firstPresent(
              summary.cnh_collected,
              driver.historical_cnh_retained
            )
          ),
          field:
            "summary.cnh_collected / driver.historical_cnh_retained",
          note:
            "Utiliza o indicador consolidado atual e preserva o campo histórico específico quando necessário.",
        },
      ],
    },

    {
      key: "breathalyzer_results",
      title: "RESULTADO ETILÔMETRO",
      subtitle:
        "Resultados registrados nas faixas do etilômetro e prisões por outros meios de prova.",
      items: [
        {
          key: "four_ml",
          label: "De 0,00 a 0,04",
          status: TAXONOMY_STATUS.MAPPED,
          value: formatMetricValue(
            alcohol.four_ml
          ),
          field: "alcohol_results.four_ml",
          note:
            "Indicador consolidado entre histórico e produção operacional.",
        },
        {
          key: "thirtythree_ml",
          label: "De 0,05 a 0,33",
          status: TAXONOMY_STATUS.MAPPED,
          value: formatMetricValue(
            alcohol.thirtythree_ml
          ),
          field:
            "alcohol_results.thirtythree_ml",
          note:
            "Indicador consolidado entre histórico e produção operacional.",
        },
        {
          key: "thirtyfour_ml",
          label: "Mais de 0,33",
          status: TAXONOMY_STATUS.MAPPED,
          value: formatMetricValue(
            alcohol.thirtyfour_ml
          ),
          field:
            "alcohol_results.thirtyfour_ml",
          note:
            "Indicador consolidado entre histórico e produção operacional.",
        },
        {
          key: "arrests_means_evidence",
          label:
            "Presos por outros meios de prova",
          status: TAXONOMY_STATUS.MAPPED,
          value: formatMetricValue(
            alcohol.arrests_means_evidence
          ),
          field:
            "alcohol_results.arrests_means_evidence",
          note:
            "Indicador consolidado para prisões registradas por outros meios de prova.",
        },
      ],
    },

    {
      key: "taxi",
      title: "TÁXI",
      subtitle:
        "Indicadores disponíveis na base histórica consolidada.",
      items: [
        {
          key: "taxi_approached",
          label: "Abordados",
          status: TAXONOMY_STATUS.MAPPED,
          value: formatMetricValue(
            taxi.approached
          ),
          field: "taxi.approached",
          note:
            "Indicador histórico consolidado de táxis abordados. O operacional atual não possui equivalente direto.",
        },
        {
          key: "taxi_pirate",
          label: "Pirata",
          status: TAXONOMY_STATUS.MAPPED,
          value: formatMetricValue(taxi.illegal),
          field: "taxi.illegal",
          note:
            "Indicador histórico consolidado de transporte irregular/pirata. O operacional atual não possui equivalente direto.",
        },
      ],
    },

    {
      key: "events",
      title: "ACONTECIMENTOS",
      subtitle:
        "Ocorrências e acontecimentos consolidados conforme a cobertura disponível em cada período.",
      items: [
        {
          key: "planned_actions",
          label: "Ações planejadas",
          status: TAXONOMY_STATUS.MAPPED,
          value: formatMetricValue(
            occurrences.planned_actions
          ),
          field:
            "occurrences.planned_actions",
          note:
            "Indicador existente na base histórica consolidada.",
        },
        {
          key: "deliberations",
          label: "Deliberações",
          status: TAXONOMY_STATUS.MAPPED,
          value: formatMetricValue(
            firstPresent(
              occurrences.historical_deliberations,
              summary.removal_resolutions
            )
          ),
          field:
            "occurrences.historical_deliberations / summary.removal_resolutions",
          note:
            "A base histórica possui campo específico de deliberações. No operacional, o campo disponível corresponde às deliberações de remoção.",
        },
        {
          key: "towings",
          label: "Reboques",
          status: TAXONOMY_STATUS.MAPPED,
          value: formatMetricValue(summary.towed),
          field: "summary.towed",
          note:
            "Indicador consolidado de veículos rebocados.",
        },
        {
          key: "rain",
          label: "Chuva",
          status: TAXONOMY_STATUS.MAPPED,
          value: formatMetricValue(
            occurrences.rain
          ),
          field: "occurrences.rain",
          note:
            "Indicador disponível na base histórica consolidada.",
        },
        {
          key: "external_occurrence",
          label: "Ocorrência externa",
          status: TAXONOMY_STATUS.MAPPED,
          value: formatMetricValue(
            occurrences.external_occurrence
          ),
          field:
            "occurrences.external_occurrence",
          note:
            "Indicador disponível na base histórica consolidada.",
        },
        {
          key: "public_security_occurrence",
          label:
            "Ocorrência de segurança pública",
          status: TAXONOMY_STATUS.MAPPED,
          value: formatMetricValue(
            occurrences.public_security_occurrence
          ),
          field:
            "occurrences.public_security_occurrence",
          note:
            "Indicador histórico específico de ocorrência de segurança pública.",
        },
        {
          key: "criminal_occurrences",
          label: "Ocorrências criminais",
          status: TAXONOMY_STATUS.MAPPED,
          value: formatMetricValue(
            occurrences.criminal_occurrences
          ),
          field:
            "occurrences.criminal_occurrences",
          note:
            "Indicador criminal consolidado conforme os campos compatíveis das fontes histórica e operacional.",
        },
        {
          key: "operations",
          label: "Operações",
          status: TAXONOMY_STATUS.MAPPED,
          value: formatMetricValue(
            occurrences.operations
          ),
          field: "occurrences.operations",
          note:
            "Quantidade de operações disponível no serviço estatístico unificado.",
        },
        {
          key: "driving_canceled_license",
          label: "CNH cassada",
          status: TAXONOMY_STATUS.MAPPED,
          value: formatMetricValue(
            occurrences.driving_canceled_license
          ),
          field:
            "occurrences.driving_canceled_license",
          note:
            "Indicador consolidado de CNH cassada quando informado pela fonte.",
        },
      ],
    },
  ];
}