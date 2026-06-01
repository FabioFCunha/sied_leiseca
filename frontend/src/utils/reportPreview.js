import { formatDateBR } from "./date.js";

const numberFields = [
  "approach",
  "tests",
  "used_caps",
  "available_caps",
  "distributed_folders",
  "cricris",
  "vetarolas",
  "used_adhesives",
  "sequence_certificates",
  "gibis",
  "distributed_certificates",
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
        `   Abordagens: ${action.approach || 0} | Testes: ${action.tests || 0} | Pastas: ${action.distributed_folders || 0} | Certificados: ${action.distributed_certificates || 0}`
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
    `Abordagens: ${totals.approach}\n` +
    `Testes: ${totals.tests}\n` +
    `Bocais usados/disponíveis: ${totals.used_caps}/${totals.available_caps}\n` +
    `Pastas: ${totals.distributed_folders}\n` +
    `Cricris: ${totals.cricris}\n` +
    `Vetarolas: ${totals.vetarolas}\n` +
    `Adesivos: ${totals.used_adhesives}\n` +
    `Gibis: ${totals.gibis}\n` +
    `Certificados: ${totals.distributed_certificates}\n\n` +
    `CONTATO/OCORRÊNCIAS\n` +
    `Contato recebido: ${report.contact_received || "não informado"}\n` +
    `Observação de ocorrência: ${report.occurrence_observation || "não informado"}\n` +
    `Coordenadas: ${report.lat || "-"}, ${report.lng || "-"}`
  );
}
