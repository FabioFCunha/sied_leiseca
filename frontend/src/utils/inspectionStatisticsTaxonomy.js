export const TAXONOMY_STATUS = {
  MAPPED: "MAPEADO",
  PARTIAL: "PARCIAL",
  UNMAPPED: "NÃƒO MAPEADO",
  NEEDS_DEFINITION: "PRECISA DEFINIÃ‡ÃƒO",
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
      label: "FiscalizaÃ§Ãµes",
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

  const approachedForAlcohol = summary.approach_plus_reconductor ?? summary.approach ?? 0;

  const calcPct = (val) => {
    if (!isPresent(val) || !approachedForAlcohol || approachedForAlcohol === 0) return null;
    return (val / approachedForAlcohol) * 100;
  };

  return [
    {
      key: "vehicles",
      title: "VEÃCULOS",
      subtitle:
        "Indicadores relacionados Ã  abordagem de veÃ­culos e Ã s medidas adotadas nas operaÃ§Ãµes.",
      items: [
        {
          key: "fined",
          label: "Multados",
          status: TAXONOMY_STATUS.MAPPED,
          value: formatMetricValue(summary.fined),
          field: "summary.fined",
          note:
            "Indicador consolidado entre histÃ³rico e produÃ§Ã£o operacional quando disponÃ­vel.",
        },
        {
          key: "towed",
          label: "Rebocados",
          status: TAXONOMY_STATUS.MAPPED,
          value: formatMetricValue(summary.towed),
          field: "summary.towed",
          note:
            "Indicador consolidado entre histÃ³rico e produÃ§Ã£o operacional quando disponÃ­vel.",
        },
        {
          key: "deliberations",
          label: "DeliberaÃ§Ãµes de remoÃ§Ã£o",
          status: TAXONOMY_STATUS.MAPPED,
          value: formatMetricValue(
            horusCards.removal_resolutions?.value
          ),
          note:
            "Registros disponÃ­veis no Horus desde 03/10/2022.",
        },
      ],
    },

    {
      key: "driver",
      title: "MOTORISTA",
      subtitle:
        "Indicadores relacionados ao condutor, habilitaÃ§Ã£o, testes e medidas administrativas.",
      items: [
        {
          key: "licensed_reconductors",
          label: "Recondutores",
          status: TAXONOMY_STATUS.MAPPED,
          value: formatMetricValue(
            horusCards.reconductor?.value
          ),
          note:
            "Registros disponÃ­veis no Horus desde 03/10/2022.",
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
            "Utiliza o indicador consolidado atual e preserva o campo histÃ³rico especÃ­fico quando necessÃ¡rio.",
        },
        {
          key: "fake_cnh",
          label: "CNH falsa",
          status: TAXONOMY_STATUS.MAPPED,
          value: formatMetricValue(driver.fake_cnh),
          note: "Indicador histÃ³rico consolidado.",
        },
        {
          key: "suspended_cnh",
          label: "CNH suspensa",
          status: TAXONOMY_STATUS.MAPPED,
          value: formatMetricValue(driver.suspended_cnh),
          note: "Indicador histÃ³rico consolidado.",
        },
        {
          key: "canceled_cnh",
          label: "CNH cassada",
          status: TAXONOMY_STATUS.MAPPED,
          value: formatMetricValue(driver.canceled_cnh),
          note: "Indicador histÃ³rico consolidado.",
        },
      ],
    },

    {
      key: "breathalyzer_results",
      title: "RESULTADO ETILÃ”METRO",
      subtitle:
        "Resultados registrados nas faixas do etilÃ´metro e prisÃµes por outros meios de prova.",
      items: [
        {
          key: "four_ml",
          label: "Resultado 0,00 a 0,04",
          status: TAXONOMY_STATUS.MAPPED,
          value: formatMetricValue(
            alcohol.four_ml
          ),
          percentage: calcPct(alcohol.four_ml),
          field: "0,00 a 0,04 mg/L",
          note:
            "Registros disponÃ­veis no Horus desde 03/10/2022.",
        },
        {
          key: "thirtythree_ml",
          label: "Resultado 0,05 a 0,33",
          status: TAXONOMY_STATUS.MAPPED,
          value: formatMetricValue(
            alcohol.thirtythree_ml
          ),
          percentage: calcPct(alcohol.thirtythree_ml),
          field: "0,05 a 0,33 mg/L",
          note:
            "Registros disponÃ­veis no Horus desde 04/10/2022.",
        },
        {
          key: "thirtyfour_ml",
          label: "Resultado acima de 0,33",
          status: TAXONOMY_STATUS.MAPPED,
          value: formatMetricValue(
            alcohol.thirtyfour_ml
          ),
          percentage: calcPct(alcohol.thirtyfour_ml),
          field: "0,34 mg/L ou mais",
          note:
            "Registros disponÃ­veis no Horus desde 04/10/2022.",
        },
        {
          key: "passive_tests_performed",
          label: "Testes passivos realizados",
          status: TAXONOMY_STATUS.MAPPED,
          value: formatMetricValue(
            driver.passive_tests_performed
          ),
          percentage: calcPct(driver.passive_tests_performed),
          note:
            "Registros disponÃ­veis no Horus desde 10/10/2022.",
        },
      ],
    },

    {
      key: "public_security",
      title: "SEGURANÃ‡A PÃšBLICA / CRIMINAL",
      subtitle:
        "OcorrÃªncias de seguranÃ§a pÃºblica e criminal consolidadas na sÃ©rie histÃ³rica.",
      items: [
        {
          key: "public_security_total",
          label: "Total de ocorrÃªncias",
          status: TAXONOMY_STATUS.MAPPED,
          value: formatMetricValue(publicSecurity.total),
          field: "public_security.total",
          note:
            "SomatÃ³rio dos indicadores que compÃµem este bloco.",
        },
        {
          key: "fugitives",
          label: "Foragidos",
          status: TAXONOMY_STATUS.MAPPED,
          value: formatMetricValue(publicSecurity.fugitives),
          field: "public_security.fugitives",
          note: "Indicador histÃ³rico consolidado.",
        },
        {
          key: "flagrante",
          label: "Flagrantes",
          status: TAXONOMY_STATUS.MAPPED,
          value: formatMetricValue(publicSecurity.flagrante),
          field: "public_security.flagrante",
          note: "Indicador histÃ³rico consolidado.",
        },
        {
          key: "simulacrum",
          label: "Simulacros",
          status: TAXONOMY_STATUS.MAPPED,
          value: formatMetricValue(publicSecurity.simulacrum),
          field: "public_security.simulacrum",
          note:
            "Indicador disponÃ­vel a partir do perÃ­odo em que passou a ser registrado.",
        },
        {
          key: "weapons",
          label: "Armas",
          status: TAXONOMY_STATUS.MAPPED,
          value: formatMetricValue(publicSecurity.weapons),
          field: "public_security.weapons",
          note: "Indicador histÃ³rico consolidado.",
        },
        {
          key: "recovered_vehicles",
          label: "VeÃ­culos recuperados",
          status: TAXONOMY_STATUS.MAPPED,
          value: formatMetricValue(publicSecurity.recovered_vehicles),
          field: "public_security.recovered_vehicles",
          note: "Indicador histÃ³rico consolidado.",
        },
        {
          key: "stolen_vehicles",
          label: "VeÃ­culos furtados",
          status: TAXONOMY_STATUS.MAPPED,
          value: formatMetricValue(publicSecurity.stolen_vehicles),
          field: "public_security.stolen_vehicles",
          note: "Indicador do Horus e produ??o operacional homologada.",
        },
        {
          key: "robbed_vehicles",
          label: "VeÃ­culos roubados",
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
          note: "Indicador histÃ³rico consolidado.",
        },
        {
          key: "bribery",
          label: "Suborno",
          status: TAXONOMY_STATUS.MAPPED,
          value: formatMetricValue(publicSecurity.bribery),
          field: "public_security.bribery",
          note: "Indicador histÃ³rico consolidado.",
        },
        {
          key: "art311",
          label: "Art. 311 CP",
          status: TAXONOMY_STATUS.MAPPED,
          value: formatMetricValue(publicSecurity.art311),
          field: "public_security.art311",
          note:
            "Indicador disponÃ­vel conforme perÃ­odo de registro da sÃ©rie histÃ³rica.",
        },
        {
          key: "art306",
          label: "Art. 306 CTB",
          status: TAXONOMY_STATUS.MAPPED,
          value: formatMetricValue(publicSecurity.art306),
          field: "public_security.art306",
          note:
            "Indicador disponÃ­vel conforme perÃ­odo de registro da sÃ©rie histÃ³rica.",
        },
      ],
    },

  ];
}
