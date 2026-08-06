import { streetActionTypeLabel } from "./streetActionTypes.js";

const text = {
  notInformed: "Não informado",
};

const number = (value) => Number(value || 0).toLocaleString("pt-BR", { maximumFractionDigits: 1 });
const integer = (value) => Number(value || 0).toLocaleString("pt-BR", { maximumFractionDigits: 0 });

const parseExpected = (...values) => {
  for (const value of values) {
    const raw = String(value ?? "").trim();
    if (!raw) continue;
    const nums = raw.match(/\d+/g)?.map(Number);
    if (nums?.length) return Math.max(...nums);
  }
  return 0;
};

const cleanLabel = (value) => String(value || "").trim() || text.notInformed;

const groupBy = (items, getLabel) =>
  Object.values(
    items.reduce((acc, item) => {
      const label = cleanLabel(getLabel(item));
      acc[label] ||= { label, actions: 0, audience: 0 };
      acc[label].actions += 1;
      acc[label].audience += parseExpected(
        item.audience,
        item.participant_range,
        item.quantity
      );
      return acc;
    }, {})
  ).sort((a, b) => b.actions - a.actions);

const ageGroupLabel = (value) => {
  const label = String(value || "").trim();
  const normalized = label.toLowerCase();
  if (!label || normalized === "adulto" || normalized === "não informado" || normalized === "nao informado") return "";
  return label;
};

const ADMINISTRATIVE_DEMAND_LABELS = {
  TRAVEL: "Deslocamento de viagem",
  INTERVIEW: "Entrevista",
  MEETING: "Reunião",
};

const requesterTypeLabel = (value) => {
  const label = String(value || "").trim();
  const normalized = label.toLowerCase();
  if (!label) return "";
  let base = "";
  if (normalized.includes("institui")) base = "Instituição de Ensino";
  else if (normalized.includes("empresa") || normalized.includes("órgão") || normalized.includes("orgao")) base = "Empresa/Órgão";
  else if (normalized.includes("organiza") && normalized.includes("evento")) base = "Organização de evento";
  else if (normalized.includes("ação de rua") || normalized.includes("acao de rua")) base = "Ação de Rua";
  if (!base) return "";
  if (normalized.includes("privado")) return `${base} Privado`;
  if (normalized.includes("público") || normalized.includes("publico")) return `${base} Público`;
  return base;
};

const norm = (value) => String(value || "").trim().toLowerCase();

const municipalityLabel = (value) => {
  const label = String(value || "").trim();
  const normalized = norm(label.replace(/,\s*rj$/i, ""));
  if (["rio de janeiro", "rj"].includes(normalized)) return "Rio de Janeiro";
  return label || text.notInformed;
};

const mergeRowsByLabel = (rows, nameKey, mapper = (value) => value) =>
  Object.values(
    (rows || []).reduce((acc, row) => {
      const label = mapper(row[nameKey]);
      acc[label] ||= { ...row, [nameKey]: label, actions: 0, audience: 0 };
      acc[label].actions += Number(row.actions || 0);
      acc[label].audience += Number(row.audience || 0);
      return acc;
    }, {})
  ).sort((a, b) => Number(b.actions || 0) - Number(a.actions || 0));

export function buildStatisticsViewModel({
  dashboardData,
  filteredAgendas,
  futureAgendas,
}) {
  const data = dashboardData || {};
  const agendas = filteredAgendas || [];
  const future = futureAgendas || [];

  const COLORS = ["#0048d7", "#059669", "#dc2626", "#7c3aed", "#ea580c", "#db2777", "#0891b2", "#ca8a04", "#64748b", "#16a34a"];

  // 1. Annual / Historical Series
  const annual = (data.annual || []).map((row) => ({
    year: row.year,
    ...row.values,
  }));

  // 2. Daily Evolution
  const dailySeries = (data.daily || []).map((row) => ({
    day: row.day_label || row.date,
    actions: Number(row.values?.["ACTION - Geral"] || 0),
    audience: Number(row.values?.["AUDIENCE - Geral"] || 0),
  }));

  // 3. Category Data (Street Actions)
  const categoryData = (data.categories || [])
    .map((row, index) => ({
      ...row,
      label: streetActionTypeLabel(row.label),
      value: Number(row.value || 0),
      actions: Number(row.value || 0),
      audience: Number(row.audience || 0),
      color: COLORS[index % COLORS.length],
    }))
    .sort((a, b) => b.value - a.value);
    
  // Pre-calculate percentages for Category Data
  const totalCategoryActions = categoryData.reduce((sum, row) => sum + row.actions, 0) || 1;
  const categoryDataWithPercentages = categoryData.map(row => {
      const pct = (row.actions / totalCategoryActions) * 100;
      return {
          ...row,
          percentageValue: pct,
          percentageLabel: `${pct.toFixed(1).replace('.', ',')}%`,
          actionsLabel: integer(row.actions),
          audienceLabel: integer(row.audience),
      }
  });

  // 4. Production vs Demand
  const totalActions = Number(data.summary?.["ACTION - Geral"] || 0);
  const total = agendas.length;
  const publicForm = agendas.filter((a) => a.origin === "PUBLIC_FORM").length;
  const internal = agendas.filter((a) => a.origin !== "PUBLIC_FORM").length;
  const approved = agendas.filter((a) => ["APPROVED", "COMPLETED"].includes(a.status)).length;
  const cancelled = agendas.filter((a) => a.status === "CANCELLED").length;
  const refused = agendas.filter((a) => ["REJECTED", "REFUSED"].includes(a.status)).length;

  const demand = {
    total,
    publicForm,
    internal,
    approved,
    cancelled,
    refused,
    cancelledOrRefused: Number(cancelled || 0) + Number(refused || 0),
    executed: totalActions,
  };

  const awaitingExecution = Math.max(0, demand.approved - demand.executed);

  // 5. Public and Internal Requests (Summary)
  const futurePublicValue = future
    .filter((a) => !["COMPLETED", "CANCELLED"].includes(a.status))
    .reduce(
      (sum, agenda) => sum + parseExpected(agenda.audience, agenda.participant_range),
      0
    );

  const displaySummary = {
    ...(data.summary || {}),
    FUTURE_PUBLIC: futurePublicValue,
    INTERNAL_REQUESTS: internal,
    PUBLIC_REQUESTS: publicForm,
  };

  const displayPrevious = {
    ...(data.previous || {}),
    FUTURE_PUBLIC: 0,
    INTERNAL_REQUESTS: 0,
    PUBLIC_REQUESTS: 0,
  };

  const displayComparisons = {
    ...(data.comparisons || {}),
    FUTURE_PUBLIC: { percentage: null },
    INTERNAL_REQUESTS: { percentage: null },
    PUBLIC_REQUESTS: { percentage: null },
  };

  // 6. Age Profile
  const ageRowsRaw = groupBy(
    agendas.filter((a) => ageGroupLabel(a.age_ranges)),
    (a) => ageGroupLabel(a.age_ranges)
  );
  const totalAgeActions = ageRowsRaw.reduce((sum, row) => sum + row.actions, 0) || 1;
  const ageRows = ageRowsRaw.map((row, index) => {
    const pct = (row.actions / totalAgeActions) * 100;
    return {
      ...row,
      color: COLORS[index % COLORS.length],
      percentageValue: pct,
      percentageLabel: `${pct.toFixed(1).replace('.', ',')}%`,
      actionsLabel: integer(row.actions),
      audienceLabel: integer(row.audience),
    };
  });

  // 7. Institutional Profile
  const requesterRowsRaw = groupBy(
    agendas.filter((a) => requesterTypeLabel(a.requester_entity_type)),
    (a) => requesterTypeLabel(a.requester_entity_type)
  );
  const totalRequesterActions = requesterRowsRaw.reduce((sum, row) => sum + row.actions, 0) || 1;
  const requesterRows = requesterRowsRaw.map((row, index) => {
    const pct = (row.actions / totalRequesterActions) * 100;
    return {
      ...row,
      color: COLORS[index % COLORS.length],
      percentageValue: pct,
      percentageLabel: `${pct.toFixed(1).replace('.', ',')}%`,
      actionsLabel: integer(row.actions),
      audienceLabel: integer(row.audience),
    };
  });

  // 8. Administrative Demands
  const adminItems = data.administrative_demands?.items || [];
  const adminItemByCode = Object.fromEntries(
    adminItems.map((item) => [item.code, item])
  );
  
  const adminRowsRaw = ["TRAVEL", "INTERVIEW", "MEETING"].map((code, index) => ({
    label: adminItemByCode[code]?.label || ADMINISTRATIVE_DEMAND_LABELS[code],
    actions: Number(adminItemByCode[code]?.value || 0),
    audience: 0,
    color: COLORS[index % COLORS.length],
  }));
  const totalAdminActions = adminRowsRaw.reduce((sum, row) => sum + row.actions, 0) || 1;
  const administrativeDemandRows = adminRowsRaw.map(row => {
      const pct = (row.actions / totalAdminActions) * 100;
      return {
          ...row,
          percentageValue: pct,
          percentageLabel: `${pct.toFixed(1).replace('.', ',')}%`,
          actionsLabel: integer(row.actions),
      }
  });

  // 9. Heatmap
  const heatmapRows = data.heatmap || [];
  const heatmapTotals = heatmapRows.reduce((acc, item) => {
      const key = `${item.day}-${item.slot}`;
      acc[key] = (acc[key] || 0) + Number(item.total || 0);
      return acc;
  }, {});
  const heatmapValues = new Map(Object.entries(heatmapTotals));

  // 10. Rankings (Municipalities & Teams)
  const municipalitiesRaw = mergeRowsByLabel(
    data.municipalities || [],
    "agenda__city",
    municipalityLabel
  );
  const municipalities = municipalitiesRaw.map(row => ({
      ...row,
      actionsLabel: integer(row.actions),
      audienceLabel: integer(row.audience)
  }));

  const teamsRaw = [...(data.teams || [])].sort(
    (a, b) =>
      Number(b.actions || 0) - Number(a.actions || 0) ||
      Number(b.audience || 0) - Number(a.audience || 0)
  );
  
  const teams = teamsRaw.map(row => ({
      ...row,
      actionsLabel: integer(row.actions),
      audienceLabel: integer(row.audience)
  }));

  const bestTeam = teams[0] || {};
  const leastTeam =
    [...teams].reverse().find((row) => Number(row.actions || 0) > 0) || {};
  const audienceLeader = [...teams].sort(
    (a, b) => Number(b.audience || 0) - Number(a.audience || 0)
  )[0] || {};
  const averageLeader = [...teams]
    .filter((row) => Number(row.actions || 0) > 0)
    .sort((a, b) => Number(b.average || 0) - Number(a.average || 0))[0] || {};
    
  const reportsWithoutPublic = Number(data.summary?.REPORTS_WITHOUT_PUBLIC || 0);

  const insights = [
    `${bestTeam.team || "Equipe"} fez mais relatórios técnicos: ${integer(
      bestTeam.actions
    )} ações registradas.`,
    `${leastTeam.team || "Equipe"} teve o menor volume entre as equipes com produção: ${integer(
      leastTeam.actions
    )} ações.`,
    `${audienceLeader.team || "Equipe"} alcançou mais público: ${integer(
      audienceLeader.audience
    )} pessoas.`,
    `${
      averageLeader.team || "Equipe"
    } tem a maior média por ação: ${number(
      averageLeader.average
    )} pessoas por registro.`,
    `${integer(
      reportsWithoutPublic
    )} relatórios aprovados estão sem público informado.`,
  ];

  return {
    annual,
    dailySeries,
    categoryData: categoryDataWithPercentages,
    demand,
    awaitingExecution,
    displaySummary,
    displayPrevious,
    displayComparisons,
    ageRows,
    requesterRows,
    administrativeDemandRows,
    heatmapRows,
    heatmapValues,
    municipalities,
    teams,
    insights,
    bestTeam,
    leastTeam,
    audienceLeader,
    averageLeader,
    reportsWithoutPublic,
  };
}
