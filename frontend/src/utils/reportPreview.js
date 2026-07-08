import { formatDateBR } from "./date.js";

const numberFields = [
  "approach",
  "approached_actions",
];

export function reportName(report) {
  return `Relatório - ${report.team || "Equipe"}`;
}

export function chiefFromReport(report) {
  const match = String(report.education_agents || "").match(/Chefe(?: respons[áa]vel)?:\s*([^\n]+)/i);
  return match?.[1]?.trim() || "";
}

export function buildPreview(report) {
  const actions = report.actions || [];
  const selectedChief = chiefFromReport(report);
  const totals = actions.reduce(
    (acc, action) => {
      numberFields.forEach((field) => {
        acc[field] += Number(action[field] || 0);
      });
      return acc;
    },
    Object.fromEntries(numberFields.map((field) => [field, 0]))
  );

  const actionLines = actions.length
    ? actions.map((action, index) => (
        `${index + 1}. ${action.type_action || "Ação"} - ${action.institution_name || action.place_action || "local não informado"}\n` +
        `   Local: ${action.place_action || "não informado"}\n` +
        `   Público: ${action.type_audience || "não informado"}\n` +
        `   Horário: ${action.start_time || "--"} às ${action.final_hour || "--"}\n` +
        `   Público alcançado (Ação/Palestra): ${action.approach || 0}\n` +
        `   Número de abordagens: ${action.approached_actions || 0}\n` +
        `   Dinâmica retirada: ${action.equipment_materials_removed ? action.equipment_materials_removed.replace(/\\n/g, ", ") : "-"}\n` +
        `   Dinâmica distribuída: ${action.equipment_materials_distributed ? action.equipment_materials_distributed.replace(/\\n/g, ", ") : "-"}\n` +
        `   Material para distribuição retirado: ${action.distribution_materials_removed ? action.distribution_materials_removed.replace(/\\n/g, ", ") : "-"}\n` +
        `   Material para distribuição distribuído: ${action.distribution_materials_distributed ? action.distribution_materials_distributed.replace(/\\n/g, ", ") : "-"}`
      )).join("\n\n")
    : "Nenhuma ação registrada.";

  return (
    `${reportName(report).toUpperCase()}\n\n` +
    `Protocolo: ${report.agenda ? "#" + report.agenda : "não informado"}\n` +
    `Solicitação: ${report.agenda_title || "não informada"}\n` +
    `Data: ${report.operation_date ? formatDateBR(report.operation_date) : "não informada"}\n` +
    `Equipe: ${report.team || "não informada"}\n` +
    `Chefe responsável: ${selectedChief || "não informado"}\n` +
    "\n" +
    `EFETIVO E ESTRUTURA\n` +
    `Educação PCD: ${report.education_pcd || "não informado"}\n` +
    `Agentes de educação: ${report.education_agents || "não informado"}\n` +
    `Alterações de efetivo: ${report.changes_staff || "não informado"}\n` +
    `Etilômetros: ${report.breathalyzers || "não informado"}\n` +
    `Viaturas: ${report.cars || "não informado"}\n` +
    `Alterações gerais: ${report.changes_general || "não informado"}\n\n` +
    `AÇÕES\n${actionLines}\n\n` +
    `TOTAIS\n` +
    `Público alcançado (Ação/Palestra): ${totals.approach}\n` +
    `Número de abordagens: ${totals.approached_actions}\n\n` +
    `CONTATO/OCORRÊNCIAS\n` +
    `Contato recebido: ${report.contact_received || "não informado"}\n` +
    `Dados e Observações: ${report.general_observations || "não informado"}\n` +
    `Observação de ocorrência: ${report.occurrence_observation || "não informado"}\n` +
    `Coordenadas: ${report.lat || "-"}, ${report.lng || "-"}` +
    (report.satisfaction_survey ? (
      `\n\n========================================\n` +
      `PESQUISA DE SATISFAÇÃO (Respondida em: ${report.satisfaction_survey.answered_at ? formatDateBR(report.satisfaction_survey.answered_at.split("T")[0]) : "-"} ${report.satisfaction_survey.answered_at ? report.satisfaction_survey.answered_at.split("T")[1].slice(0, 5) : ""})\n` +
      `========================================\n` +
      `Avaliação geral: ${report.satisfaction_survey.overall_rating ? `${report.satisfaction_survey.overall_rating}/5` : "Não avaliado"}\n` +
      `Pontualidade da equipe: ${report.satisfaction_survey.punctuality ? `${report.satisfaction_survey.punctuality}/5` : "Não avaliado"}\n` +
      `Entusiasmo e dinamismo: ${report.satisfaction_survey.team_enthusiasm ? `${report.satisfaction_survey.team_enthusiasm}/5` : "Não avaliado"}\n` +
      `Domínio do palestrante: ${report.satisfaction_survey.speaker_knowledge ? `${report.satisfaction_survey.speaker_knowledge}/5` : "Não avaliado"}\n` +
      `Oficinas / Dinâmicas: ${report.satisfaction_survey.workshops ? `${report.satisfaction_survey.workshops}/5` : "Não avaliado"}\n` +
      `Recursos audiovisuais: ${report.satisfaction_survey.audiovisual_resources ? `${report.satisfaction_survey.audiovisual_resources}/5` : "Não avaliado"}\n` +
      `Material de apoio: ${report.satisfaction_survey.support_material ? `${report.satisfaction_survey.support_material}/5` : "Não avaliado"}\n` +
      `Sugestões / Comentários:\n"${report.satisfaction_survey.suggestion || "Nenhum comentário enviado."}"`
    ) : "")
  );
}
