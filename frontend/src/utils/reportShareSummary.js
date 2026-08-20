import { STREET_ACTION_ID } from "./constants.js";
import { streetActionTypeLabel } from "./streetActionTypes.js";
import { getValidatableActions } from "../pages/technicalReportsActionHelpers.js";

function formatShareDate(value) {
  if (!value) return "";
  const [year, month, day] = String(value).slice(0, 10).split("-");
  if (!year || !month || !day) return String(value);
  return `${day}/${month}/${year}`;
}

function isStreetActionAgenda(agenda = {}) {
  const values = [agenda.action_type_ref, agenda.requester_entity_type, agenda.action_type_ref_name];
  return values.some((value) => {
    const normalized = String(value || "").trim().toLocaleLowerCase("pt-BR");
    return String(value) === STREET_ACTION_ID || normalized === "ação de rua" || normalized === "acao de rua";
  });
}

function getAgendaActionPlace(agenda = {}) {
  const fullAddress = [
    agenda.address,
    agenda.neighborhood || agenda.neighborhood_ref_name,
    agenda.city || agenda.municipality_ref_name,
    agenda.state,
  ].filter(Boolean).join(", ");
  return fullAddress || agenda.location || agenda.institution_location || "";
}

function summarizeDistributedMaterials(value = "") {
  return String(value || "")
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => {
      const [name, rawQuantity = ""] = line.replace(/\[\s*\]/g, "|").replace(/\s+-\s+/g, " | ").split("|").map((part) => part.trim());
      return { name, quantity: rawQuantity.match(/\d+/)?.[0] || "" };
    })
    .filter((item) => item.name && Number(item.quantity) > 0)
    .map((item) => `${item.name}: ${item.quantity}`)
    .join(", ");
}

const exceptionalOccurrenceTypeLabels = {
  VEHICLE_BREAKDOWN: "Quebra de Viatura",
  WORK_ACCIDENT: "Acidente de Trabalho (Efetivo)",
  WEATHER: "Condição Climática",
  MATERIAL_SHORTAGE: "Falta de Material",
  OTHER: "Outros",
};

const exceptionalOccurrenceImpactLabels = {
  NONE: "Nenhum",
  PARTIAL: "Parcial",
  TOTAL: "Total",
};

export function buildReportShareSummary(report = {}, agenda = {}, attendanceStats = {}) {
  const isStreetAction = isStreetActionAgenda(agenda);
  const lines = [
    "*RELATÓRIO TÉCNICO - OPERAÇÃO LEI SECA*",
    "",
    "Relatório enviado para conferência no SIED.",
    "",
  ];
  const operationDate = report.operation_date || report.agenda_date || agenda.date;
  const team = report.team || agenda.team_name || agenda.team_ref_name || agenda.sector_name;
  const location = report.agenda_location || agenda.institution_location || agenda.location || getAgendaActionPlace(agenda);

  if (operationDate) lines.push(`• Data: ${formatShareDate(operationDate)}`);
  if (team) lines.push(`• Equipe: ${team}`);
  if (location) lines.push(`• Local: ${location}`);
  lines.push(`• Modalidade: ${isStreetAction ? "Ação de Rua" : "Palestra"}`);
  if (attendanceStats?.loaded && attendanceStats.total > 0) {
    lines.push(`• Frequência: ${attendanceStats.present} presente(s), ${attendanceStats.absent} ausente(s)`);
  }

  const actions = getValidatableActions(report.actions || []).map(({ action }) => action);
  if (actions.length) {
    lines.push("", "*AÇÕES REALIZADAS*");
    actions.forEach((action, index) => {
      const actionTitle = isStreetAction
        ? streetActionTypeLabel(action.type_action || "")
        : (action.institution_name || `Ação ${index + 1}`);
      lines.push("", `*Ação ${String(index + 1).padStart(2, "0")}*${actionTitle ? ` - ${actionTitle}` : ""}`);
      if (action.place_action) lines.push(`• Endereço: ${action.place_action}`);
      if (action.start_time || action.final_hour) {
        const start = String(action.start_time || "").slice(0, 5);
        const end = String(action.final_hour || "").slice(0, 5);
        lines.push(`• Horário: ${start || "-"}${end ? ` às ${end}` : ""}`);
      }
      const reached = isStreetAction ? Number(action.approached_actions || 0) : Number(action.approached_lectures || 0);
      lines.push(`• ${isStreetAction ? "Abordagens" : "Abordados em palestras"}: ${reached}`);
      const distributed = summarizeDistributedMaterials(action.distribution_materials_distributed || "");
      if (distributed) lines.push(`• Material distribuído: ${distributed}`);
    });
  }

  if (report.has_exceptional_occurrence) {
    lines.push("", "*OCORRÊNCIA EXCEPCIONAL*");
    const type = exceptionalOccurrenceTypeLabels[report.exceptional_occurrence_type] || report.exceptional_occurrence_type;
    if (type) lines.push(`• Tipo: ${type}`);
    if (report.exceptional_occurrence_description) lines.push(`Descrição: ${report.exceptional_occurrence_description}`);
    if (report.exceptional_occurrence_actions_taken) lines.push(`Providências: ${report.exceptional_occurrence_actions_taken}`);
    const impact = exceptionalOccurrenceImpactLabels[report.exceptional_occurrence_impact] || report.exceptional_occurrence_impact;
    if (impact) lines.push(`Impacto: ${impact}`);
  }
  if (String(report.general_observations || "").trim()) lines.push("", `• Observações: ${String(report.general_observations).trim()}`);
  return lines.join("\n");
}
