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
      key: "operations",
      label: "Fiscalizações",
      value: summary.operations,
    },
    {
      key: "approach",
      label: "Abordados e Recondutores",
      value: summary.approach,
    },
    {
      key: "refusal",
      label: "Recusas",
      value: summary.refusal,
    },
    {
      key: "fined",
      label: "Multados",
      value: summary.fined,
    },
    {
      key: "cnh_collected",
      label: "CNH Recolhidas",
      value: summary.cnh_collected,
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
  const horusCards = dashboard.horus_cards || {};
  const coverage = dashboard.coverage || {};

  return [
    {
      key: "vehicles",
      title: "VEÍCULOS",
      subtitle:
        "Indicadores relacionados à abordagem de veículos e às medidas adotadas nas operações.",
      items: [
        {
          key: "stolen_recovered_vehicles",
          label: "Roubado/Furtado",
          status: TAXONOMY_STATUS.MAPPED,
          value: formatMetricValue(
            horusCards.stolen_recovered_vehicles?.value
          ),
          note:
            "35 recuperados + 33 roubados + 398 furtados. Fonte: Horus.",
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
          label: "Testes passivos",
          status: TAXONOMY_STATUS.MAPPED,
          value: formatMetricValue(
            horusCards.passive_tests_performed?.value
          ),
          note:
            "Registros disponíveis no Horus desde 03/10/2022.",
        },
        {
          key: "licensed_reconductors",
          label: "Recondutores",
          status: TAXONOMY_STATUS.MAPPED,
          value: formatMetricValue(
            horusCards.reconductor?.value
          ),
          note:
            "Registros disponíveis no Horus desde 03/10/2022.",
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
          label: "Resultado negativo",
          status: TAXONOMY_STATUS.MAPPED,
          value: formatMetricValue(
            horusCards.four_ml?.value
          ),
          field: "0,00 a 0,04 mg/L",
          note:
            "Registros disponíveis no Horus desde 03/10/2022.",
        },
        {
          key: "thirtythree_ml",
          label: "Infração administrativa",
          status: TAXONOMY_STATUS.MAPPED,
          value: formatMetricValue(
            horusCards.thirtythree_ml?.value
          ),
          field: "0,05 a 0,33 mg/L",
          note:
            "Registros disponíveis no Horus desde 04/10/2022.",
        },
        {
          key: "thirtyfour_ml",
          label: "Faixa criminal — etilômetro",
          status: TAXONOMY_STATUS.MAPPED,
          value: formatMetricValue(
            horusCards.thirtyfour_ml?.value
          ),
          field: "0,34 mg/L ou mais",
          note:
            "Registros disponíveis no Horus desde 04/10/2022.",
        },
        {
          key: "arrests_means_evidence",
          label: "Presos por outros meios de prova",
          status: TAXONOMY_STATUS.MAPPED,
          value: formatMetricValue(
            horusCards.arrests_means_evidence?.value
          ),
          note:
            "Registros disponíveis no Horus desde 10/10/2022.",
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
          label: "Delibera??es de remo??o",
          status: TAXONOMY_STATUS.MAPPED,
          value: formatMetricValue(
            horusCards.removal_resolutions?.value
          ),
          note:
            "Registros disponíveis no Horus desde 03/10/2022.",
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
            horusCards.rain?.value
          ),
          note:
            "Operações com registro explícito de chuva nas observações do Horus desde 03/10/2022.",
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
          label: "Ocorr?ncias criminais",
          status: TAXONOMY_STATUS.MAPPED,
          value: formatMetricValue(
            horusCards.criminal_occurrences?.value
          ),
          note:
            "Registros disponíveis no Horus desde 03/10/2022.",
        },
        {
          key: "art307",
          label: "Art. 307",
          status: TAXONOMY_STATUS.MAPPED,
          value: formatMetricValue(
            horusCards.art307?.value
          ),
          note:
            "Registros disponíveis no Horus desde 03/10/2022.",
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
            horusCards.driving_canceled_license?.value
          ),
          note:
            "Registros disponíveis no Horus desde 04/10/2022.",
        },
      ],
    },
  ];
}