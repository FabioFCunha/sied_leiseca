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

  const occurrences = dashboard.occurrences || {};
  const publicSecurity = dashboard.public_security || {};
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
          note:
            "Utiliza o indicador consolidado atual e preserva o campo histórico específico quando necessário.",
        },
        {
          key: "fake_cnh",
          label: "CNH falsa",
          status: TAXONOMY_STATUS.MAPPED,
          value: formatMetricValue(driver.fake_cnh),
          note: "Indicador histórico consolidado.",
        },
        {
          key: "suspended_cnh",
          label: "CNH suspensa",
          status: TAXONOMY_STATUS.MAPPED,
          value: formatMetricValue(driver.suspended_cnh),
          note: "Indicador histórico consolidado.",
        },
        {
          key: "canceled_cnh",
          label: "CNH cassada",
          status: TAXONOMY_STATUS.MAPPED,
          value: formatMetricValue(driver.canceled_cnh),
          note: "Indicador histórico consolidado.",
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
      key: "public_security",
      title: "SEGURANÇA PÚBLICA / CRIMINAL",
      subtitle:
        "Ocorrências de segurança pública e criminal consolidadas na série histórica.",
      items: [
        {
          key: "public_security_total",
          label: "Total de ocorrências",
          status: TAXONOMY_STATUS.MAPPED,
          value: formatMetricValue(publicSecurity.total),
          field: "public_security.total",
          note:
            "Somatório dos indicadores que compõem este bloco.",
        },
        {
          key: "fugitives",
          label: "Foragidos",
          status: TAXONOMY_STATUS.MAPPED,
          value: formatMetricValue(publicSecurity.fugitives),
          field: "public_security.fugitives",
          note: "Indicador histórico consolidado.",
        },
        {
          key: "flagrante",
          label: "Flagrantes",
          status: TAXONOMY_STATUS.MAPPED,
          value: formatMetricValue(publicSecurity.flagrante),
          field: "public_security.flagrante",
          note: "Indicador histórico consolidado.",
        },
        {
          key: "simulacrum",
          label: "Simulacros",
          status: TAXONOMY_STATUS.MAPPED,
          value: formatMetricValue(publicSecurity.simulacrum),
          field: "public_security.simulacrum",
          note:
            "Indicador disponível a partir do período em que passou a ser registrado.",
        },
        {
          key: "weapons",
          label: "Armas",
          status: TAXONOMY_STATUS.MAPPED,
          value: formatMetricValue(publicSecurity.weapons),
          field: "public_security.weapons",
          note: "Indicador histórico consolidado.",
        },
        {
          key: "recovered_vehicles",
          label: "Veículos recuperados",
          status: TAXONOMY_STATUS.MAPPED,
          value: formatMetricValue(publicSecurity.recovered_vehicles),
          field: "public_security.recovered_vehicles",
          note: "Indicador histórico consolidado.",
        },
        {
          key: "stolen_vehicles",
          label: "Veículos furtados",
          status: TAXONOMY_STATUS.MAPPED,
          value: formatMetricValue(publicSecurity.stolen_vehicles),
          field: "public_security.stolen_vehicles",
          note: "Indicador do Horus e produ??o operacional homologada.",
        },
        {
          key: "robbed_vehicles",
          label: "Veículos roubados",
          status: TAXONOMY_STATUS.MAPPED,
          value: formatMetricValue(publicSecurity.robbed_vehicles),
          field: "public_security.robbed_vehicles",
          note: "Indicador do Horus e produ??o operacional homologada.",
        },
        {
          key: "narcotics",
          label: "Entorpecentes",
          status: TAXONOMY_STATUS.MAPPED,
          value: formatMetricValue(publicSecurity.narcotics),
          field: "public_security.narcotics",
          note: "Indicador histórico consolidado.",
        },
        {
          key: "bribery",
          label: "Suborno",
          status: TAXONOMY_STATUS.MAPPED,
          value: formatMetricValue(publicSecurity.bribery),
          field: "public_security.bribery",
          note: "Indicador histórico consolidado.",
        },
        {
          key: "art311",
          label: "Art. 311 CP",
          status: TAXONOMY_STATUS.MAPPED,
          value: formatMetricValue(publicSecurity.art311),
          field: "public_security.art311",
          note:
            "Indicador disponível conforme período de registro da série histórica.",
        },
        {
          key: "art306",
          label: "Art. 306 CTB",
          status: TAXONOMY_STATUS.MAPPED,
          value: formatMetricValue(publicSecurity.art306),
          field: "public_security.art306",
          note:
            "Indicador disponível conforme período de registro da série histórica.",
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
          label: "Deliberações de remoção",
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
          key: "criminal_occurrences",
          label: "Ocorrências criminais",
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
      ],
    },
  ];
}