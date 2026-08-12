export const TAXONOMY_STATUS = {
  MAPPED: "MAPEADO",
  PARTIAL: "PARCIAL",
  UNMAPPED: "NÃO MAPEADO",
  NEEDS_DEFINITION: "PRECISA DEFINIÇÃO",
};

const isPresent = (value) => value !== null && value !== undefined;

function formatMetricValue(value) {
  return isPresent(value) ? value : null;
}

function formatPairValue(left, right) {
  if (!isPresent(left) && !isPresent(right)) {
    return null;
  }
  return `${isPresent(left) ? left : "Não informado"} + ${isPresent(right) ? right : "Não informado"}`;
}

export function buildInspectionExecutiveCards(summary = {}) {
  return [
    { key: "homologated_reports", label: "Relatórios homologados", value: summary.homologated_reports ?? 0 },
    { key: "operations", label: "Operações", value: summary.operations ?? 0 },
    { key: "approach", label: "Abordados", value: summary.approach },
    { key: "fined", label: "Multados", value: summary.fined },
  ];
}

export function buildInspectionStatisticsTaxonomy(dashboard = {}) {
  const summary = dashboard.summary || {};

  return [
    {
      key: "vehicles",
      title: "VEÍCULOS",
      subtitle: "Agrupamento institucional para abordagem de veículos e medidas imediatas.",
      items: [
        {
          key: "approached_reconductor",
          label: "Abordados + Recondutor",
          status: TAXONOMY_STATUS.PARTIAL,
          value: formatPairValue(summary.approach, summary.reconductor),
          field: "approach + reconductor",
          note: "O SIED separa `approach` e `reconductor`; a regra oficial de consolidação única da planilha ainda precisa definição.",
        },
        {
          key: "fined",
          label: "Multados",
          status: TAXONOMY_STATUS.MAPPED,
          value: formatMetricValue(summary.fined),
          field: "fined",
          note: "Correspondência direta com o quantitativo operacional homologado.",
        },
        {
          key: "towed",
          label: "Rebocados",
          status: TAXONOMY_STATUS.MAPPED,
          value: formatMetricValue(summary.towed),
          field: "towed",
          note: "Correspondência direta com o quantitativo operacional homologado.",
        },
      ],
    },
    {
      key: "driver",
      title: "MOTORISTA",
      subtitle: "Indicadores ligados ao condutor e às medidas diretamente associadas à habilitação.",
      items: [
        {
          key: "breathalyzer_test",
          label: "Teste com etilômetro",
          status: TAXONOMY_STATUS.NEEDS_DEFINITION,
          value: null,
          field: null,
          note: "A planilha histórica usa uma nomenclatura própria e não há correspondência comprovada no modelo atual sem redefinir a regra.",
        },
        {
          key: "licensed_reconductors",
          label: "Recondutores habilitados",
          status: TAXONOMY_STATUS.PARTIAL,
          value: formatMetricValue(summary.reconductor),
          field: "reconductor",
          note: "O campo `reconductor` é próximo semanticamente, mas a qualificação 'habilitados' ainda precisa validação institucional.",
        },
        {
          key: "refusal",
          label: "Recusa ao teste",
          status: TAXONOMY_STATUS.MAPPED,
          value: formatMetricValue(summary.refusal),
          field: "refusal",
          note: "Correspondência direta com o quantitativo de recusa.",
        },
        {
          key: "cnh_collected",
          label: "CNH Recolhidas",
          status: TAXONOMY_STATUS.MAPPED,
          value: formatMetricValue(summary.cnh_collected),
          field: "cnh_collected",
          note: "Correspondência direta. Permanece dentro da categoria MOTORISTA.",
        },
      ],
    },
    {
      key: "breathalyzer_results",
      title: "RESULTADO ETILÔMETRO",
      subtitle: "Faixas do etilômetro e prisões por outros meios de prova, sem recálculo derivado.",
      items: [
        {
          key: "four_ml",
          label: "De 0,00 a 0,04",
          status: TAXONOMY_STATUS.MAPPED,
          value: formatMetricValue(summary.four_ml),
          field: "four_ml",
          note: "Correspondência direta com a faixa já homologada.",
        },
        {
          key: "thirtythree_ml",
          label: "De 0,05 a 0,33",
          status: TAXONOMY_STATUS.MAPPED,
          value: formatMetricValue(summary.thirtythree_ml),
          field: "thirtythree_ml",
          note: "Correspondência direta com a faixa já homologada.",
        },
        {
          key: "thirtyfour_ml",
          label: "Mais de 0,33",
          status: TAXONOMY_STATUS.MAPPED,
          value: formatMetricValue(summary.thirtyfour_ml),
          field: "thirtyfour_ml",
          note: "Correspondência direta com a faixa já homologada.",
        },
        {
          key: "arrests_means_evidence",
          label: "Presos por outros meios de prova",
          status: TAXONOMY_STATUS.MAPPED,
          value: formatMetricValue(summary.arrests_means_evidence),
          field: "arrests_means_evidence",
          note: "Correspondência direta com o campo operacional homologado.",
        },
      ],
    },
    {
      key: "taxi",
      title: "TÁXI",
      subtitle: "Bloco reservado para a taxonomia histórica, sem inventar equivalências no modelo atual.",
      items: [
        {
          key: "taxi_approached",
          label: "Abordados",
          status: TAXONOMY_STATUS.UNMAPPED,
          value: null,
          field: null,
          note: "Não existe campo correspondente comprovado em `InspectionStatistic`.",
        },
        {
          key: "taxi_pirate",
          label: "Pirata",
          status: TAXONOMY_STATUS.UNMAPPED,
          value: null,
          field: null,
          note: "Não existe campo correspondente comprovado em `InspectionStatistic`.",
        },
      ],
    },
    {
      key: "events",
      title: "ACONTECIMENTOS",
      subtitle: "Indicadores institucionais da planilha histórica agrupados sem alterar o significado oficial atual.",
      items: [
        {
          key: "planned_actions",
          label: "Ações planejadas",
          status: TAXONOMY_STATUS.UNMAPPED,
          value: null,
          field: null,
          note: "Não existe campo correspondente comprovado no modelo atual.",
        },
        {
          key: "deliberations",
          label: "Deliberações",
          status: TAXONOMY_STATUS.PARTIAL,
          value: formatMetricValue(summary.removal_resolutions),
          field: "removal_resolutions",
          note: "O campo atual cobre deliberações de remoção; a planilha histórica pode incluir uma categoria mais ampla.",
        },
        {
          key: "towings",
          label: "Reboques",
          status: TAXONOMY_STATUS.MAPPED,
          value: formatMetricValue(summary.towed),
          field: "towed",
          note: "Correspondência direta com o quantitativo de reboques homologados.",
        },
        {
          key: "rain",
          label: "Chuva",
          status: TAXONOMY_STATUS.UNMAPPED,
          value: null,
          field: null,
          note: "Não existe campo correspondente comprovado no modelo atual.",
        },
        {
          key: "external_occurrence",
          label: "Ocorrência externa",
          status: TAXONOMY_STATUS.UNMAPPED,
          value: null,
          field: null,
          note: "Não existe campo correspondente comprovado no modelo atual.",
        },
        {
          key: "public_security_occurrence",
          label: "Ocorrência de segurança pública",
          status: TAXONOMY_STATUS.NEEDS_DEFINITION,
          value: null,
          field: null,
          note: "O modelo atual possui `criminal_occurrences`, mas a equivalência com a taxonomia histórica ainda não está comprovada.",
        },
        {
          key: "operations",
          label: "Operações",
          status: TAXONOMY_STATUS.MAPPED,
          value: formatMetricValue(summary.operations),
          field: "operations_count",
          note: "Correspondência direta com a soma de `operations_count`.",
        },
        {
          key: "cnh_overcome",
          label: "Superação CNH",
          status: TAXONOMY_STATUS.UNMAPPED,
          value: null,
          field: null,
          note: "Não existe campo correspondente comprovado no modelo atual.",
        },
        {
          key: "driving_canceled_license",
          label: "CNH cassada",
          status: TAXONOMY_STATUS.MAPPED,
          value: formatMetricValue(summary.driving_canceled_license),
          field: "driving_canceled_license",
          note: "Correspondência direta com o indicador operacional homologado.",
        },
      ],
    },
  ];
}
