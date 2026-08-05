import { formatDateBR } from "./date.js";


export function reportName(report) {
  return `Relatório - ${report.team || "Equipe"}`;
}

export function chiefFromReport(report) {
  const match = String(report.education_agents || "").match(/Chefe(?: respons[áa]vel)?:\s*([^\n]+)/i);
  return match?.[1]?.trim() || "";
}

export function getSupports(report, selectedAgenda) {
  const supportsList = [];
  
  // 1. Try structured fields from selectedAgenda if available
  if (selectedAgenda) {
    if (selectedAgenda.support_1 && selectedAgenda.support_1.trim()) {
      supportsList.push(selectedAgenda.support_1.trim());
    }
    if (selectedAgenda.support_2 && selectedAgenda.support_2.trim()) {
      supportsList.push(selectedAgenda.support_2.trim());
    }
  }
  
  // 2. Fallback to regex if we didn't find any structured supports
  if (supportsList.length === 0 && report && report.education_agents) {
    const lines = String(report.education_agents).split('\n');
    lines.forEach(line => {
      const match = line.match(/^(?:Apoio\s*[12]?|Apoios?)(?:\s*operacional)?:\s*(.+)$/i);
      if (match) {
        const val = match[1].trim();
        if (val) {
          supportsList.push(val);
        }
      }
    });
  }
  
  // Deduplicate
  const unique = [];
  const normalizedSeen = new Set();
  supportsList.forEach(name => {
    const normalized = name.toLowerCase().trim();
    if (normalized && !normalizedSeen.has(normalized)) {
      normalizedSeen.add(normalized);
      unique.push(name);
    }
  });
  
  return unique;
}

export function buildPreview(report) {
  const actions = report.actions || [];
  const selectedChief = chiefFromReport(report);
  
  const agentsMatch = report.education_agents ? report.education_agents.match(/Agentes?:\s*([^\n]+)/i)?.[1]?.trim() : "";
  const supportsList = getSupports(report, undefined);
  const supportsStr = supportsList.join(" - ");

  let totalsEstimado = 0;
  let totalsAlcancado = 0;

  actions.forEach((action, index) => {
    // Público Estimado: somente Ação 1
    if (index === 0) {
      totalsEstimado += Number(action.approach || 0);
    }
    // Público Alcançado: approached_lectures na Ação 1, approached_actions nas extras
    const alcVal = index === 0 ? action.approached_lectures : action.approached_actions;
    const alcNum = Number(alcVal);
    totalsAlcancado += (alcVal !== "" && alcVal !== null && alcVal !== undefined && Number.isFinite(alcNum)) ? alcNum : 0;
  });

  const taxaText = totalsEstimado > 0
    ? `${((totalsAlcancado / totalsEstimado) * 100).toFixed(1)}%`
    : "N/A";

  const actionLines = actions.length
    ? actions.map((action, index) => {
        const isFirstAction = index === 0;
        const alcVal = isFirstAction ? action.approached_lectures : action.approached_actions;
        const alcDisplay = (alcVal !== "" && alcVal !== null && alcVal !== undefined)
          ? alcVal
          : "Não informado";

        const estimadoLine = isFirstAction
          ? `   Público estimado: ${action.approach || 0}\n`
          : "";

        return (
          `${index + 1}. ${action.type_action || "Ação"} - ${action.institution_name || action.place_action || "local não informado"}\n` +
          `   Instituição/Local: ${action.institution_name || "não informado"}\n` +
          `   Endereço do Local: ${action.place_action || "não informado"}\n` +
          `   Público: ${action.type_audience || "não informado"}\n` +
          `   Horário: ${action.start_time || "--"} às ${action.final_hour || "--"}\n` +
          estimadoLine +
          `   Público alcançado: ${alcDisplay}\n` +
          `   Dinâmica retirada: ${action.equipment_materials_removed ? action.equipment_materials_removed.replace(/\\n/g, ", ") : "-"}\n` +
          `   Dinâmica distribuída: ${action.equipment_materials_distributed ? action.equipment_materials_distributed.replace(/\\n/g, ", ") : "-"}\n` +
          `   Material para distribuição retirado: ${action.distribution_materials_removed ? action.distribution_materials_removed.replace(/\\n/g, ", ") : "-"}\n` +
          `   Material para distribuição distribuído: ${action.distribution_materials_distributed ? action.distribution_materials_distributed.replace(/\\n/g, ", ") : "-"}`
        );
      }).join("\n\n")
    : "Nenhuma ação registrada.";

  return (
    `${reportName(report).toUpperCase()}\n\n` +
    `Protocolo: ${report.agenda ? "#" + report.agenda : "não informado"}\n` +
    `Solicitação: ${report.agenda_title || "não informada"}\n` +
    `Data: ${report.operation_date ? formatDateBR(report.operation_date) : "não informada"}\n` +
    `Equipe: ${report.team || "não informada"}\n` +
    `Chefe responsável: ${selectedChief || "não informado"}\n` +
    `Telefone do solicitante: ${report.agenda_phone || "não informado"}\n` +
    "\n" +
    `EFETIVO E ESTRUTURA\n` +
    `Agentes de educação: ${agentsMatch || "não informado"}\n` +
    `Apoios: ${supportsStr || "Não informado"}\n` +
    `Alterações de efetivo: ${report.changes_staff || "não informado"}\n` +
    `Etilômetros: ${report.breathalyzers || "não informado"}\n` +
    `Viaturas: ${report.cars || "não informado"}\n` +
    `Alterações gerais: ${report.changes_general || "não informado"}\n\n` +
    `AÇÕES\n${actionLines}\n\n` +
    `TOTAIS\n` +
    `Público estimado (total): ${totalsEstimado}\n` +
    `Público alcançado (total): ${totalsAlcancado}\n` +
    `Taxa de Alcance: ${taxaText}\n` +
    `Ações Realizadas: ${actions.length}\n\n` +
    `RELATO OPERACIONAL DO CHEFE\n` +
    `${report.general_observations || "Não informado"}\n\n` +
    `CONTATO/OCORRÊNCIAS\n` +
    `Contato recebido: ${report.contact_received || "não informado"}\n` +
    `Observação de ocorrência: ${report.occurrence_observation || "não informado"}\n` +
    `Coordenadas: ${report.lat || "-"}, ${report.lng || "-"}` +
    (report.satisfaction_survey ? (() => {
      const survey = report.satisfaction_survey;
      const scores = [
        Number(survey.overall_rating),
        Number(survey.punctuality),
        Number(survey.team_enthusiasm),
        Number(survey.speaker_knowledge),
        Number(survey.workshops),
        Number(survey.audiovisual_resources),
        Number(survey.support_material)
      ].filter(val => !isNaN(val) && val > 0);
      const avg = scores.length > 0 ? (scores.reduce((a, b) => a + b, 0) / scores.length).toFixed(1) : "Não avaliado";
      
      return `\n\n========================================\n` +
      `PESQUISA DE SATISFAÇÃO (Respondida em: ${survey.answered_at ? formatDateBR(survey.answered_at.split("T")[0]) : "-"} ${survey.answered_at ? survey.answered_at.split("T")[1].slice(0, 5) : ""})\n` +
      `========================================\n` +
      `Média de satisfação: ${avg === "Não avaliado" ? avg : `${avg}/5`}\n` +
      `Avaliação geral: ${survey.overall_rating ? `${survey.overall_rating}/5` : "Não avaliado"}\n` +
      `Pontualidade da equipe: ${survey.punctuality ? `${survey.punctuality}/5` : "Não avaliado"}\n` +
      `Entusiasmo e dinamismo: ${survey.team_enthusiasm ? `${survey.team_enthusiasm}/5` : "Não avaliado"}\n` +
      `Domínio do palestrante: ${survey.speaker_knowledge ? `${survey.speaker_knowledge}/5` : "Não avaliado"}\n` +
      `Oficinas / Dinâmicas: ${survey.workshops ? `${survey.workshops}/5` : "Não avaliado"}\n` +
      `Recursos audiovisuais: ${survey.audiovisual_resources ? `${survey.audiovisual_resources}/5` : "Não avaliado"}\n` +
      `Material de apoio: ${survey.support_material ? `${survey.support_material}/5` : "Não avaliado"}\n` +
      `Sugestões / Comentários:\n"${survey.suggestion || "Nenhum comentário enviado."}"`;
    })() : "")
  );
}

